# Scan Findings Format Reference Doc

Change ID: `1p455-doc scan-findings-format-reference-doc`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-08
Wave: 1p44n framework-1p6-hardening

## Rationale

The secrets-scan subsystem now writes and consumes a structured findings file (`docs/scan-findings.json`) and a rules/policy file (`docs/scan-rules.toml`), but there is **no format reference doc** for either. A `grep` across `docs/references/` and `docs/specs/` returns no `scan-findings-format.md` or `scan-rules-format.md`. The schema is instead scattered across four unrelated sources that a reader must stitch together:

- The finding-record fields are emitted in code at `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py:603-612` (`id`, `file`, `line`, `line_hash`, `context_hash`, `rule_id`, `matched_text`, `status`).
- The status lifecycle and `confirmations[]` semantics live only in `.wavefoundry/framework/seeds/213-security-reviewer.prompt.md:17-55` (pending → false-positive / suspected-secret / confirmed-secret, plus `acknowledged_for_wave`).
- The `[policy] false_positive_confirmations_required` threshold contract is referenced in passing at `213-security-reviewer.prompt.md:31` and applied at install/backfill time (`160-upgrade-wavefoundry.prompt.md:153-158`).
- The policy template skeleton appears at `012-install-wavefoundry-phase-2.prompt.md:60-67`.

Without a single canonical reference, future agents and operators cannot reason about the findings file's schema, its commit-and-self-scan behavior, or the allowlist self-exclusion. This change adds that doc and wires the two install/upgrade seeds to it.

This change also **corrects a false sub-claim** in the originating report: the report claims `docs/references/install-log-format.md` is "missing." It is not. `docs/references/install-log-format.md` exists with 100 lines of real content and is correctly referenced by `011-install-wavefoundry-phase-1.prompt.md:11` and `010-install-wavefoundry.md:22/35/37`. That sub-task is not-applicable and must NOT result in a "create install-log-format.md" action.

## Requirements

1. Create `docs/references/scan-findings-format.md` as the canonical format reference for `docs/scan-findings.json`.
2. Document the finding-record schema with every field emitted at `secrets_validators.py:603-612`: `id`, `file`, `line`, `line_hash`, `context_hash`, `rule_id`, `matched_text`, `status`, and the `confirmations[]` array (with `git_user_name`, `git_user_email`, `verdict`, `reason`, UTC ISO-8601 datetime per `213-security-reviewer.prompt.md:49`).
3. Document the status lifecycle exactly as defined in `213-security-reviewer.prompt.md:17-55`: `pending` → `false-positive` / `suspected-secret` / `confirmed-secret`, plus the wave-scoped `acknowledged_for_wave` (and `override_reason`) acknowledgment fields.
4. Document the `[policy] false_positive_confirmations_required` threshold contract (default 2; single-committer = 1 per `213-security-reviewer.prompt.md:53`) and how it gates clearing a `false-positive` entry and `wave_close` soft-blocks.
5. Include an explicit warning that `docs/scan-findings.json` is **itself committed and self-scanned**, and document the framework `[allowlist].paths` self-exclusion that prevents the findings file (and matched text it records) from re-triggering as new findings.
6. Wire `160-upgrade-wavefoundry.prompt.md` (step 8, ~line 153) to reference the new doc.
7. Wire `012-install-wavefoundry-phase-2.prompt.md` (step 2.3a, ~line 37) to reference the new doc.
8. Explicitly record in this change that `docs/references/install-log-format.md` already exists and requires no action.
9. Keep `docs-lint` clean.

## Scope

**Problem statement:** The scan-findings.json schema, status lifecycle, confirmation-threshold policy contract, and self-scan/allowlist behavior are undocumented and scattered across four sources; meanwhile the originating report falsely flags an already-existing reference doc (`install-log-format.md`) as missing.

**In scope:**

- A new `docs/references/scan-findings-format.md` covering record schema, status lifecycle, `[policy]` threshold contract, and the self-scanned/allowlist warning.
- Two seed wiring edits: `160-upgrade-wavefoundry.prompt.md` step 8 and `012-install-wavefoundry-phase-2.prompt.md` step 2.3a, each adding a pointer to the new doc.
- An explicit, recorded confirmation that `install-log-format.md` already exists and is correctly referenced (no creation).

**Out of scope:**

- Creating or modifying `install-log-format.md` (it already exists — confirmed).
- A separate `scan-rules-format.md` for `docs/scan-rules.toml` (the `[policy]` and `[allowlist]` contracts are summarized in the findings doc; a full rules-format reference is not this scope).
- Any change to scanner code, validators, rule definitions, or the schema itself — this is a documentation-only change.
- Changes to seed-213 lifecycle behavior (it remains the authoritative source; the new doc references it, not the reverse).

## Acceptance Criteria

- [ ] AC-1: `docs/references/scan-findings-format.md` exists and documents the full finding-record schema (`id`, `file`, `line`, `line_hash`, `context_hash`, `rule_id`, `matched_text`, `status`, `confirmations[]`) consistent with `secrets_validators.py:603-612`.
- [ ] AC-2: The new doc documents the status lifecycle `pending` → `false-positive` / `suspected-secret` / `confirmed-secret` plus `acknowledged_for_wave` / `override_reason`, consistent with `213-security-reviewer.prompt.md:17-55`.
- [ ] AC-3: The new doc documents the `[policy] false_positive_confirmations_required` threshold contract (default 2, solo-repo 1) and its role in clearing false-positives and `wave_close` soft-blocks.
- [ ] AC-4: The new doc includes an explicit warning that `docs/scan-findings.json` is committed and self-scanned, and documents the `[allowlist].paths` self-exclusion that prevents it from re-triggering.
- [ ] AC-5: `160-upgrade-wavefoundry.prompt.md` (step 8) and `012-install-wavefoundry-phase-2.prompt.md` (step 2.3a) each contain a reference to `docs/references/scan-findings-format.md`.
- [ ] AC-6: This change doc explicitly records that `docs/references/install-log-format.md` already exists (100 lines, real content, referenced by seed-011:11 and 010:22/35/37) and requires no action.
- [ ] AC-7 (regression / lint): `docs-lint` (`.wavefoundry/bin/docs-lint`) runs clean over the new doc and the two edited seeds; a doc-cross-reference check verifies the new doc path resolves and is reachable from both seeds (e.g., `grep` for `scan-findings-format.md` in both seed files returns a hit).

## Tasks

- [ ] Open the `seed_edit_allowed` gate: `wave_gate_open(gate="seed_edit_allowed")` (coordinate with 1p450/1p453 — shared seed edits).
- [ ] Read `secrets_validators.py:595-620` and `213-security-reviewer.prompt.md:11-55` to confirm field names and lifecycle wording before authoring.
- [ ] Author `docs/references/scan-findings-format.md`: header block, file locations, record schema table, `confirmations[]` schema, status lifecycle section, `[policy]` threshold contract section, and the self-scanned/`[allowlist].paths` warning section.
- [ ] Edit `160-upgrade-wavefoundry.prompt.md` step 8 (~line 153) to point at the new doc.
- [ ] Edit `012-install-wavefoundry-phase-2.prompt.md` step 2.3a (~line 37) to point at the new doc.
- [ ] Record the `install-log-format.md` already-exists confirmation in the Decision Log and Progress Log of this change.
- [ ] Run `.wavefoundry/bin/docs-lint` (or `wave_validate`) and fix any failures.
- [ ] Grep both seeds for `scan-findings-format.md` to confirm the cross-references landed.
- [ ] Close the gate: `wave_gate_close(gate="seed_edit_allowed")`.

## Agent Execution Graph


| Workstream                | Owner       | Depends On    | Notes                                                                 |
| ------------------------- | ----------- | ------------- | --------------------------------------------------------------------- |
| author-reference-doc      | Engineering | —             | Write `docs/references/scan-findings-format.md`; grounded in code+seed |
| wire-seeds                | Engineering | author-reference-doc | Edit seed-160 step 8 and seed-012 step 2.3a; needs `seed_edit_allowed` |
| verify-and-lint           | Engineering | wire-seeds    | `docs-lint` + cross-reference grep gate (AC-7)                        |


## Serialization Points

- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` — shared seed edit with 1p450/1p453; coordinate under `seed_edit_allowed` to avoid clobbering concurrent edits.
- `.wavefoundry/framework/seeds/012-install-wavefoundry-phase-2.prompt.md` — shared seed edit with 1p450/1p453; same gate coordination.
- `docs/references/scan-findings-format.md` — new file; no concurrent writer, but its path is the cross-reference target both seed edits depend on (land the doc first).

## Affected Architecture Docs

N/A — this change adds a single reference doc under `docs/references/` and adds pointer text to two existing seeds. There is no module boundary, control-flow, layering, or verification-architecture change. The new doc joins the existing `docs/references/` family (alongside `install-log-format.md`) and documents already-shipped behavior.

## AC Priority


| AC   | Priority   | Rationale                                                                                  |
| ---- | ---------- | ------------------------------------------------------------------------------------------ |
| AC-1 | required   | The record schema is the core deliverable; without it the doc has no purpose.              |
| AC-2 | required   | The status lifecycle is the second core contract operators and agents must understand.     |
| AC-3 | required   | The confirmation-threshold contract gates false-positive clearing and `wave_close`.        |
| AC-4 | required   | The self-scan/allowlist warning prevents real confusion; it is the highest-risk omission.  |
| AC-5 | important  | Wiring makes the doc discoverable from install/upgrade flows; the doc is weaker unwired.   |
| AC-6 | important  | Recording the `install-log-format.md` non-action corrects the report's false claim on record. |
| AC-7 | required   | Lint-clean + reachable cross-references is the regression gate proving the change is sound. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date       | Decision                                                                                          | Reason                                                                                                          | Alternatives                                                                                       |
| ---------- | ------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| 2026-06-08 | Document the schema in one new `scan-findings-format.md`; keep seed-213 authoritative for lifecycle. | Single canonical reference removes the four-source scatter; seed-213 stays the source of truth for agent behavior, and the doc references it to avoid duplication drift. | Inline the schema into each seed (rejected: duplication); a combined findings+rules format doc (deferred: rules-format is out of scope). |
| 2026-06-08 | Treat `install-log-format.md` as already-existing; record the non-action instead of creating it.   | The originating report's "missing" claim is false — the file exists with 100 lines and is referenced by seed-011:11 and 010:22/35/37; creating it would duplicate/overwrite real content. | "Create install-log-format.md" per the report (rejected: would clobber existing, correct content). |


## Risks


| Risk                                                                                          | Mitigation                                                                                                   |
| --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Doc drifts from `secrets_validators.py` if record fields change later.                          | Cite `secrets_validators.py:603-612` and seed-213 inline as the authoritative sources so reviewers can diff. |
| Seed edits collide with concurrent 1p450/1p453 edits to seeds 160/012.                          | Coordinate via `seed_edit_allowed` gate; land the new doc first, then make minimal pointer-only seed edits.  |
| Documenting the self-scan/allowlist behavior incorrectly could mislead operators into editing the allowlist by hand. | Describe `[allowlist].paths` as framework-managed self-exclusion and point to the rules file, not hand-editing. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
