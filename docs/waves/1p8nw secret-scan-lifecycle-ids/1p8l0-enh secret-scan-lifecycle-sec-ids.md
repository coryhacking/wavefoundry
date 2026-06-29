# Secret scan lifecycle `sec` IDs

Change ID: `1p8l0-enh secret-scan-lifecycle-sec-ids`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-28
Wave: `1p8nw secret-scan-lifecycle-ids`

## Rationale

Secret-scan findings currently use local sequential IDs such as `exc-001` in `docs/scan-findings.json`. That format predates the broader lifecycle ID convention and now stands out from Wavefoundry's normal machine-usable IDs (`<prefix>-<kind> <slug>` for changes, `<prefix> <slug>` for waves). It is also scoped only to the findings file, so it does not carry creation-time ordering or the same collision-avoidance semantics as lifecycle IDs.

This enhancement changes secret-scan finding IDs to use the lifecycle prefix with a `sec` suffix, for example `1p8l0-sec`. New findings use the format immediately, and existing `exc-###` findings are migrated once with a deterministic compatibility map so operator classifications, confirmations, and references remain traceable. The scanner continues to re-bind findings by file, rule, line hash, and context hash. The ID change is cosmetic and operational: it makes scan findings follow the same naming family as other Wavefoundry artifacts without changing the security gate semantics.

## Requirements

1. Replace new `exc-###` secret-scan finding IDs with lifecycle-backed IDs in the form `<prefix>-sec`.
2. Add `sec` as a supported lifecycle artifact kind for scanner-created security findings, without making `sec` appear as a normal change-doc kind in `wave_new_*` tools or plan scaffolding unless explicitly intended later.
3. Do not generate a slug for scanner-created IDs. Finding context remains in the existing structured fields (`file`, `line`, `rule_id`, `line_hash`, `context_hash`, `matched_text`) rather than being duplicated into the ID.
4. Deduplicate generated lifecycle prefixes against existing wave/change/ADR IDs and existing `docs/scan-findings.json` IDs so a finding cannot collide with an existing lifecycle artifact or finding, including multiple findings created during the same scan.
5. Migrate existing `exc-###` IDs in `docs/scan-findings.json` to `sec` IDs, preserving all other record fields exactly unless the migration adds explicit compatibility metadata.
6. Record a legacy compatibility mapping, either inline per record (for example `legacy_id: "exc-001"`) or in a migration metadata block/file, so old IDs can still be traced after conversion.
7. Make migration idempotent: running it repeatedly must not keep changing already-migrated IDs or duplicate compatibility metadata.
8. Continue to match existing findings by file, line, rule, line hash, and context hash so line drift updates the existing record instead of minting a new `sec` ID.
9. Update `docs/references/scan-findings-format.md`, seed/security-reviewer guidance, and any tests/fixtures that document the finding ID format.
10. Keep scanner output deterministic in tests by allowing timestamp/policy injection or by testing the helper with fixed lifecycle inputs.
11. Maintain secrets-gate behavior exactly: `pending` and `suspected-secret` still block close, `confirmed-secret` still produces the standing reminder, and cleared false positives still clear.

## Scope

**Problem statement:** Secret-scan finding IDs use `exc-###`, which is inconsistent with Wavefoundry's lifecycle ID conventions and lacks lifecycle ordering/collision semantics. New and existing findings should look like first-class Wavefoundry artifacts while preserving the existing finding lifecycle and compatibility with already-classified ledgers.

**In scope:**

- Secret-scan finding ID generation for new records in `wave_lint_lib/secrets_validators.py`.
- Lifecycle ID support for a `sec` artifact kind or scanner-specific helper that reuses lifecycle prefix generation.
- Collision detection against existing scan finding IDs and existing lifecycle prefixes.
- Idempotent migration of existing `exc-###` entries with legacy ID traceability.
- Tests for new ID shape, collision behavior, legacy ID tolerance, line-drift rebinding, and unchanged gate semantics.
- Documentation updates for `docs/scan-findings.json` schema and security-reviewer guidance.

**Out of scope:**

- Changing statuses, confirmation policy, false-positive thresholds, redaction, allowlists, or the secrets gate.
- Adding a general public `wave_new_security` / `wave_new_secret` planning tool.
- Changing reviewer finding IDs such as `SEC-1` from the generic harness finding schema unless a separate plan covers reviewer-output IDs.
- Changing rule IDs in `scan-rules.toml`.

## Acceptance Criteria

- [x] AC-1: New scanner-created entries in `docs/scan-findings.json` use IDs matching `^[0-9a-z]{5}-sec$`. (`_next_secret_finding_id`; `TestSecretFindingIdShape.test_new_finding_id_matches_sec_regex`)
- [x] AC-2: Existing `exc-###` entries in `docs/scan-findings.json` are converted to `sec` IDs by an explicit migration path, preserving status, confirmations, override reasons, line hashes, context hashes, redacted matched text, and all security-reviewer fields. (`migrate_legacy_finding_ids`; `TestLegacyFindingIdMigration.test_migration_is_lossless` / `test_scanner_migrates_legacy_ledger_in_place`)
- [x] AC-3: Migrated findings retain traceability to their old IDs through a documented compatibility field or mapping, and scanner/security-reviewer output can surface the legacy ID when useful. (`legacy_id` field; seed-213 surfaces it; `test_migration_records_legacy_id`)
- [x] AC-4: The migration is idempotent: running it twice leaves IDs and compatibility metadata unchanged after the first successful migration. (`test_migration_is_idempotent` / `test_migration_skips_already_sec_records`)
- [x] AC-5: A re-scan of an existing finding, including a line-drift case matched by `line_hash` / `context_hash`, updates the migrated `sec` record and does not mint a duplicate finding. (`_find_exception` unchanged; `TestLineDriftAfterMigration.test_drift_rebinds_migrated_record`)
- [x] AC-6: New and migrated `sec` IDs are collision-safe against existing scan finding IDs and existing lifecycle prefixes from plans, waves, and ADRs. (dedup via `next_available_prefix` + `_existing_finding_ids` loop; `TestSecretFindingIdCollision`, `test_multiple_findings_in_one_scan_get_distinct_sec_ids`, `test_migration_no_collision_between_records`)
- [x] AC-7: The lifecycle ID generator or a scanner-specific wrapper supports `sec` without exposing `sec` as a normal change-doc kind in plan/wave creation tools. (`sec` kept scanner/lib-scoped; `test_sec_not_a_public_change_doc_kind` asserts `VALID_CHANGE_KINDS` and lifecycle CLI `--kind` choices exclude `sec`)
- [x] AC-8: The ID contains no generated slug; file/rule/context readability comes from the structured finding fields and scanner/reviewer output, not from the ID string. (`test_new_finding_id_has_no_slug`)
- [x] AC-9: `docs/references/scan-findings-format.md` documents the `sec` ID shape, migration behavior, legacy ID traceability, and rationale for omitting slugs. (new "Finding ID format" section; shipped copy synced)
- [x] AC-10: Security reviewer seed/prompt guidance no longer implies scanner ledger IDs are only `exc-###`; reviewer lane finding IDs such as `SEC-1` remain distinct unless explicitly changed. (seed-213 Pre-Scope note added; rendered role doc `docs/agents/security-reviewer.md` mentions no finding ids, so no re-render needed)
- [x] AC-11: Secrets-gate behavior is unchanged for `pending`, `suspected-secret`, `confirmed-secret`, and cleared `false-positive` records before and after migration. (`_check_secrets_gate` / `_confirmed_secret_notice` UNCHANGED; `TestGateSemanticsUnchanged.*` incl. `test_gate_equivalent_across_migration`)
- [x] AC-12: Framework tests run bytecode-free and docs validation passes. (`run_tests.py` 3646 ok bytecode-free; `wave_validate` passed; `__pycache__` cleaned)

## Tasks

- [x] Add lifecycle support for `sec` IDs, either by adding a lifecycle helper for suffix-only artifact IDs or by adding a scanner helper that calls `next_available_prefix` and formats `<prefix>-sec`. (scanner wrapper `_next_secret_finding_id` calls `lifecycle_id.next_available_prefix`)
- [x] Extend lifecycle prefix deduplication or scanner-side deduplication to include `docs/scan-findings.json` IDs. (`_existing_finding_ids` + advance-on-collision loop)
- [x] Replace `_next_exception_id` with a new helper such as `_next_secret_finding_id(root, exceptions)` that returns `<prefix>-sec`. (removed `_next_exception_id`; sole call site updated)
- [x] Add an explicit migration helper for `docs/scan-findings.json` that rewrites `exc-###` IDs to `sec` IDs while preserving all other record fields. (`migrate_legacy_finding_ids`, invoked in `check_hardcoded_secrets` after load)
- [x] Add legacy ID traceability via `legacy_id` or a documented equivalent, and ensure reports/searches can display it when present. (`legacy_id` field; never stripped by `_strip_empty_fields`; seed-213 surfaces it)
- [x] Keep legacy `exc-###` parsing/tolerance for imported or not-yet-migrated target repositories. (`_check_secrets_gate` keys on `status` only; `TestLegacyExcIdTolerance`; `test_server_tools.py` `exc-###` fixtures still green)
- [x] Update tests in `test_secrets_validators.py` and lifecycle ID tests for `sec` support/collision behavior. (`TestSecretFindingIdShape`, `TestSecretFindingIdCollision` — lifecycle collision is exercised through the scanner wrapper, which reuses `next_available_prefix`)
- [x] Add migration tests covering classified findings, confirmations, override reasons, idempotence, collisions, and line-drift rebinding after migration. (`TestLegacyFindingIdMigration`, `TestLineDriftAfterMigration`)
- [x] Update fixtures and expected `docs/scan-findings.json` examples. (test fixtures now exercise `exc-###`→`sec` migration; live `docs/scan-findings.json` is `[]`, no example file change needed)
- [x] Update `docs/references/scan-findings-format.md`. (+ shipped `.wavefoundry/framework/docs/` copy synced)
- [x] Update seed/prompt references in `213-security-reviewer.prompt.md` and rendered security-reviewer docs if they mention the old scanner ID shape. (seed-213 updated; rendered role doc mentions no finding ids — no re-render)
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`. (3646 tests ok; docs-lint ok)

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| id-contract | implementer | - | Decide library-level `sec` support vs scanner wrapper |
| scanner | implementer | id-contract | Replace `_next_exception_id`, add collision handling |
| validation-tests | implementer | scanner | Legacy tolerance, line drift, gate semantics, lifecycle collisions |
| docs-seeds | implementer | id-contract | Schema reference and security-reviewer guidance |
| qa | qa-reviewer | all | Bytecode-free suite and docs validation |


## Serialization Points

- The ID contract must be settled before scanner and docs updates.
- Tests for legacy `exc-###` tolerance must land with the scanner change to avoid breaking existing repositories.
- Documentation updates should land after the exact ID regex and migration rules are final.

## Affected Architecture Docs

- `docs/references/scan-findings-format.md` must be updated because it is the canonical schema for `docs/scan-findings.json`.
- `docs/architecture/data-and-control-flow.md` may need a small update if it documents scan finding creation or lifecycle ID generation.
- `docs/architecture/cross-cutting-concerns.md` may need a small update if lifecycle ID policy is described as applying only to waves/changes/ADRs.
- No new ADR expected unless implementation chooses to expand lifecycle IDs into a general artifact-kind registry.

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The new ID shape is the requested behavior. |
| AC-2 | required | Existing operator-classified ledgers must be converted without losing decisions. |
| AC-3 | required | Old IDs may exist in discussion, commits, and operator notes; conversion needs traceability. |
| AC-4 | required | Migration must be safe to rerun during setup/upgrade and tests. |
| AC-5 | required | Rebinding is what prevents duplicate findings after line drift. |
| AC-6 | required | The reason to use lifecycle IDs is collision-safe, time-ordered consistency. |
| AC-7 | required | `sec` should not accidentally become a normal change-doc kind. |
| AC-8 | required | The scanner should not invent redundant slug content when structured fields already carry context. |
| AC-9 | required | The schema reference is the operator contract. |
| AC-10 | important | Avoid conflating scanner ledger IDs with reviewer finding IDs. |
| AC-11 | required | The security gate semantics must not change. |
| AC-12 | required | Standard framework verification gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-28 | Drafted from operator request to make secret-scan IDs follow lifecycle ID patterns with a `sec` suffix. | Current `_next_exception_id` emits `exc-###`; scan findings schema documents `id` as `exc-001`; lifecycle IDs use `<prefix>-<kind> <slug>`. |
| 2026-06-28 | Expanded scope to convert existing `exc-###` IDs as well, with legacy traceability and idempotent migration. | Operator clarification: "I actually want to convert existing id's to the new format as well." |
| 2026-06-28 | Removed generated slugs from the target ID shape; use `<prefix>-sec` only. | Scanner IDs are generated by code, and scan findings already carry structured context in `file`, `line`, `rule_id`, `line_hash`, and `context_hash`. |
| 2026-06-28 | Implemented: lifecycle-backed `_next_secret_finding_id` + idempotent/lossless `migrate_legacy_finding_ids` (records `legacy_id`) in `secrets_validators.py`; migration wired into `check_hardcoded_secrets`; `_check_secrets_gate`/`_confirmed_secret_notice` left UNCHANGED; docs (`scan-findings-format.md` + shipped copy) and seed-213 updated; +21 secrets tests. All 12 ACs met. | `run_tests.py` 3646 ok (secrets 126→147), bytecode-free; `wave_validate` ok; new IDs e.g. `1p8l0-sec` match `^[0-9a-z]{5}-sec$`; `sec` absent from `VALID_CHANGE_KINDS` and lifecycle CLI `--kind`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-28 | Select lifecycle-backed scanner IDs in the form `<prefix>-sec` for new findings and migrate existing `exc-###` entries with legacy traceability. | The scanner, not an agent, creates the ID; generated slugs duplicate already-structured context and add avoidable collision/determinism work. | **Keep `exc-###`:** simplest but keeps the inconsistency. **Use `<prefix>-sec <slug>`:** closer to change IDs, but the slug is synthetic and redundant for scanner records. **New findings only:** lower migration risk, but leaves a mixed-format ledger indefinitely and does not meet operator preference. **Use reviewer-style `SEC-1`:** familiar for findings and follows AC/task-style ordinals, but it does not use lifecycle ordering and collides conceptually with reviewer lane finding IDs. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Existing classified findings lose reviewer decisions during conversion | Migration preserves every non-ID field byte-for-byte where possible and tests classified findings with confirmations and override reasons. |
| External references to old `exc-###` IDs become hard to trace | Store `legacy_id` or an equivalent mapping and document it in the scan findings format. |
| Migration keeps changing IDs on repeated runs | Make migration idempotent and test repeated runs. |
| A `sec` helper makes `sec` available as a normal change-doc kind | Keep `sec` in scanner/lifecycle-library scope only, or explicitly test `wave_new_*` kind lists remain unchanged. |
| Same scan creates multiple findings in one lifecycle bucket | Deduplicate against current in-memory exceptions and consume the next available lifecycle prefix for each finding. |
| Line drift creates duplicate findings with new IDs | Preserve `_find_exception` hash fallback behavior and add a line-drift regression test. |
| Docs confuse scanner ledger IDs with reviewer finding IDs | Update scan-format docs and security-reviewer guidance to name the distinction. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
