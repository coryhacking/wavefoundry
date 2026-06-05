# Config-key rename converges via bounded removal window

Change ID: `1p3j7-enh config-key-rename-convergence`
Change Status: `implemented`
Owner: framework-maintainer
Status: implemented
Last verified: 2026-06-05
Wave: 1p3iv indexer-drift-skips-empty-files

## Rationale

Wave `1p337` (1.4.0) shipped the alias-tuple back-compat that lets `workflow-config.json` use either `wave_council_policy` or `wave_review` (and the parallel `wave_execution` / `wave_implement`). The framework runtime accepts both indefinitely. Wave `1p3dk` (1.5.0 prep) added a `docs-lint` warning when the legacy spelling is in use — but the warning was open-ended ("the framework accepts both for now") with no convergence date. This change closes the convergence loop: bounded deprecation window with a `removed_in` semver, `wave_upgrade` auto-rewrites the key in `workflow-config.json` during upgrade, and `docs-lint` errors at the removal version.

The `removed_in` is "2.0.0" — semver-major convention for breaking-change removal. Until 2.0.0 ships, operators get warnings + auto-rewrite; from 2.0.0 onward, the legacy spelling fails `docs-lint`.

## Requirements

1. `canonical-names.json` sets `removed_in: "2.0.0"` for both `wave_council_policy` → `wave_review` and `wave_execution` → `wave_implement` (no role-rename change in this scope).
2. `upgrade_extensions.py` `post_extract` runs `_run_convergence_migration(ctx)` at the top of the hook — UNCONDITIONAL (no `from_version` gate). The migration reads the canonical-names manifest and rewrites legacy config keys in `docs/workflow-config.json`.
3. Rewrite behavior: legacy-only → rename to canonical in-place (preserves on-disk key ordering for diffability); legacy + canonical both present → drop legacy (canonical is operator-explicit); no legacy keys → no-op.
4. Dry-run path: planned-action strings printed to stderr instead of file mutation.
5. Idempotent: a second invocation against an already-rewritten file is a no-op.
6. New `check_workflow_config_removed_keys` in `core_validators.py` returns ERROR (not warning) when the current framework version `>= removed_in` AND the legacy key is still in `workflow-config.json`. Wired into `cli.py` `failures.extend(...)` so the gate fails.
7. Version comparison uses `MAJOR.MINOR.PATCH` from `.wavefoundry/framework/VERSION`, stripping `+build` suffix. Missing/unparseable VERSION → degraded mode (no escalation; uncertain → don't flip green to red).
8. Existing `check_workflow_config_legacy_aliases` warning text updated to include "will be removed in `<version>`" when the manifest declares a removal version; falls back to "the framework accepts both for now" when `removed_in` is null.
9. Tests cover: rewrite happy path, both-present-prefer-canonical, idempotence, dry-run no-disk-mutation, removed_in error at-version, removed_in error past-version, no error below-version, degraded modes (no VERSION, garbage VERSION, no manifest).

## Scope

**Problem statement:** The `wave_council_policy` / `wave_execution` deprecations have no end date. Today, a config on legacy spelling lint-warns indefinitely; the framework runtime accepts both forever; convergence to a single canonical name never happens by design.

**In scope:**

- `canonical-names.json` `removed_in` populated for config-key renames.
- `upgrade_extensions.py` convergence migration (helpers + call site).
- `core_validators.py` removed-version error escalation.
- `cli.py` wire-in.
- Tests for upgrade rewrite + lint removal-version error.
- CHANGELOG bullet under `[1.5.0]` `### Changed`.

**Out of scope:**

- Convergence for ROLE renames (`council-moderator` → `wave-council`, `code-insight-agent` → `guru`). These remain at `removed_in: null` per the candidate description ("config-key rename" specifically). Role renames affect hand-authored doc references, not config-file parsing; their convergence is a different design (rewriting prose across many files).
- Schema bump for the canonical-names manifest. The `removed_in` field already existed in schema v1; this change populates values without touching the loader.
- Bumping the framework version to anything past `1.5.0+<build>`. The lint error escalation is dormant until the consumer upgrades to a 2.0.0 pack; the rewrite migration runs starting now.

## Acceptance Criteria

- [x] AC-1: `canonical-names.json` `config_key_renames["wave_council_policy"].removed_in == "2.0.0"` and same for `wave_execution`.
- [x] AC-2: `upgrade_extensions._rewrite_legacy_config_keys(root)` renames legacy → canonical in `workflow-config.json`, returns `(legacy, canonical)` performed list. (Verified by `test_rewrite_renames_legacy_to_canonical`.)
- [x] AC-3: When both legacy and canonical are present, canonical wins; legacy is dropped. (Verified by `test_rewrite_drops_legacy_when_canonical_already_present`.)
- [x] AC-4: Rewrite is idempotent — second invocation returns empty performed list. (Verified by `test_rewrite_is_idempotent`.)
- [x] AC-5: Preview helper returns planned-action strings without touching disk. (Verified by `test_preview_plans_renames_without_touching_disk`.)
- [x] AC-6: `post_extract` invokes the convergence migration BEFORE the `from_version` gate, so the migration runs on 1.5.0 → 1.5.0+x upgrades too. (Verified by inspecting the `post_extract` code path; the call site is unconditional.)
- [x] AC-7: `check_workflow_config_removed_keys` errors when current version ≥ `removed_in` AND legacy key present; silent below. (Verified by `test_error_at_removal_version_exactly`, `test_error_past_removal_version`, `test_no_error_below_removal_version`.)
- [x] AC-8: Degraded modes don't escalate (missing VERSION, unparseable VERSION, no manifest, `removed_in: null`). (Verified by the four corresponding tests.)
- [x] AC-9: `check_workflow_config_legacy_aliases` warning text mentions removal version when present. (Verified — modified inline; existing legacy-alias tests still pass.)
- [x] AC-10: All framework tests pass (2683 / +18 new).
- [x] AC-11: `docs-lint` returns clean.

## Tasks

- [x] Update `canonical-names.json` with `removed_in: "2.0.0"` for both config-key renames.
- [x] Add convergence-migration helpers (`_preview_legacy_config_key_rewrite`, `_rewrite_legacy_config_keys`, `_load_config_key_renames`, `_run_convergence_migration`) to `upgrade_extensions.py`.
- [x] Wire `_run_convergence_migration(ctx)` at the top of `post_extract` (unconditional).
- [x] Update `check_workflow_config_legacy_aliases` warning text to include removal version.
- [x] Add `check_workflow_config_removed_keys` + helpers (`_current_framework_version`, `_semver_parse`, `_current_version_is_at_or_past`) to `core_validators.py`.
- [x] Wire the new check into `cli.py` `failures.extend(...)`.
- [x] Add `ConvergenceMigrationTests` in `test_upgrade_wavefoundry.py` (9 tests).
- [x] Add `WorkflowConfigRemovedKeysUnitTests` in `test_docs_lint.py` (9 tests).
- [x] Run framework tests.
- [x] Run docs-lint.
- [x] Add CHANGELOG bullet under `[1.5.0]` `### Changed`.

## Affected Architecture Docs

N/A — change is confined to `upgrade_extensions.py` + `wave_lint_lib/` internals and a data-file update. No domain map / layering / cross-cutting impact.

## AC Priority


| AC    | Priority     | Rationale |
| ----- | ------------ | --------- |
| AC-1  | required     | Manifest is the upstream of all the downstream behavior. |
| AC-2  | required     | The rewrite IS the convergence half. |
| AC-3  | required     | Both-present resolution is a real edge case for operators in mid-rename. |
| AC-4  | required     | Non-idempotent migrations corrupt on second invocation. |
| AC-5  | required     | Dry-run support so operators can preview before committing. |
| AC-6  | required     | Migration must fire on every upgrade, not just 1.4 → 1.5. |
| AC-7  | required     | Error escalation is the gate that closes the deprecation window. |
| AC-8  | required     | Degraded modes are the realistic upgrade scenarios (partial state). |
| AC-9  | important    | Warning text discoverability for the in-between period. |
| AC-10 | required     | No regressions. |
| AC-11 | required     | docs-lint clean. |


## Progress Log


| Date       | Update                                                       | Evidence |
| ---------- | ------------------------------------------------------------ | -------- |
| 2026-06-05 | Change admitted and implemented in-session. | Manifest update; `upgrade_extensions.py` helpers + call site; `core_validators.py` removed-keys check; `cli.py` wire-in; 18 new tests. |
| 2026-06-05 | Post-prepare-council fixes landed: drop-case log fidelity (`_rewrite_legacy_config_keys` returns 4-tuples with action discriminator + dropped value; stderr line distinguishes rename from drop) + dry-run report-file parity (`_write_convergence_preview_report` + `_write_convergence_report` write dedicated log files mirroring the 1.5.0 migration shape). 5 new tests added; 2688 total pass. Addresses prepare-council advisory findings. |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-05 | `removed_in: "2.0.0"` for both config-key renames. | Semver convention — major-version bump is where breaking removals belong. Operators have 1.5.0 / 1.6.x / 1.7.x to converge; 2.0.0 is the gate. | (a) `removed_in: "1.7.0"` — rejected; collapses the window too aggressively for consumers on 1.4.x who upgrade slowly. (b) `removed_in` per-key with different versions — rejected; uniform deadline is simpler to communicate. |
| 2026-06-05 | Convergence migration runs UNCONDITIONALLY at the top of `post_extract`, not gated by `from_version`. | The rename rewrite needs to fire for ANY upgrade that lands a manifest with config-key renames — including 1.5.0 → 1.5.0+x where the existing version gate would short-circuit. Idempotent design (no-op when no legacy keys) means firing on every upgrade is safe. | (a) Gate on `from_version < 2.0.0` — rejected; cleaner to keep version-gating out of convergence entirely since the migration is self-gating via the manifest content. (b) Use a separate hook — rejected; `post_extract` is the right phase; no need for a new hook signature. |
| 2026-06-05 | Both-present resolution: canonical wins, legacy dropped. | The canonical entry is operator-explicit (they wrote it directly); the legacy is presumably leftover from a partial migration. Trust the operator's most-recent intention. | (a) Merge values — rejected; values are typically objects with overlapping schemas, merge is ambiguous. (b) Refuse to rewrite when both present — rejected; leaves the duplication on disk indefinitely. |
| 2026-06-05 | Error escalation degrades to no-escalation when VERSION is missing or unparseable. | A `docs-lint` that flips green to red because the operator is mid-build or in a development tree without VERSION is more annoying than valuable. Better to defer escalation in uncertain conditions and warn instead. | (a) Treat missing VERSION as "past removal" and escalate — rejected; punishes operators in dev environments. (b) Treat missing VERSION as "version 0" and never escalate — rejected; would require special-case handling forever. |
| 2026-06-05 | Role renames keep `removed_in: null` (out of scope for this change). | Candidate #4 description was explicit: "convergence half of the config-key rename." Role rename convergence requires rewriting prose across many hand-authored docs — different design pattern (text substitution + diff review), separate change. | (a) Roll role-rename convergence into this change — rejected; bloats scope and produces a much larger diff for review. (b) Block role renames from EVER converging — rejected; role-rename convergence is a known future need, just not now. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Migration loses operator-customized data when both legacy and canonical are present. | Test `test_rewrite_drops_legacy_when_canonical_already_present` verifies canonical value is preserved unchanged. Operators with intentional duplication aren't a known use case. |
| Future role-rename convergence (out of scope here) finds the manifest mechanism awkward. | The manifest schema is symmetric — `role_renames` already carries a `removed_in` field. Future role-convergence change can reuse the same field; only the migration mechanism (text rewrite vs JSON rewrite) is different. |
| Operators on 1.5.0+ skip the upgrade with the migration and hit the 2.0.0 error escalation without prior warning. | The warning fires from 1.5.0+ already (existing `check_workflow_config_legacy_aliases`). Operators reading docs-lint output will see "will be removed in 2.0.0" before they hit the error. Multiple upgrade opportunities precede 2.0.0. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
