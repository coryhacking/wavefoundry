# Materialize Project Secrets Policy Before The First Upgrade Gate

Change ID: `1p44z-enh secrets-confirmation-bootstrap-ordering`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-06-09
Wave: 1p44n framework-1p6-hardening

## Rationale

During an upgrade, the first secrets gate enforces the framework-shipped default confirmation threshold before the operator's committer-count-derived threshold is ever written. The committer-count backfill of `docs/scan-rules.toml` is agent-only and runs late: `seed-160` step 8 (`.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md:153-158`) and `seed-012` step 2.3a (`.wavefoundry/framework/seeds/012-install-wavefoundry-phase-2.prompt.md:37-73`) instruct the agent to count committers and write `docs/scan-rules.toml` during the EDITING PASS — which executes AFTER the automated phase-3 gate (`wave_upgrade` phase `preflight_to_docs_gate`, `.wavefoundry/framework/scripts/server_impl.py:6268+`, driving `run_secrets_scan.py`). Neither the upgrade phase nor the scan materializes `docs/scan-rules.toml`.

Because the project policy file does not yet exist, `load_merged_ruleset` (`.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py:65`) loads only the framework base policy, and the project merge branch at `:69` is skipped entirely. So the first gate enforces `false_positive_confirmations_required = 2` — the framework-shipped `[policy]` DEFAULT (`.wavefoundry/framework/scan-rules.toml:93-94`), not the `dict.get` fallback literal at `secrets_validators.py:699` (that literal is dead because the framework toml always sets the key). The result is a window where a fresh project is blocked by the framework default of 2 before the agent backfill can lower it to the team-size-appropriate threshold.

## Requirements

1. The `preflight_to_docs_gate` phase of `wave_upgrade` MUST ensure the operator's project-level secrets policy is in effect before the first gate scan runs, via one of the two approaches below.
2. Primary approach — materialization: when `docs/scan-rules.toml` is absent, the preflight phase MUST auto-detect the committer count (last 24 months, with all-time fallback on 0), map it to a threshold (0–1 → 1, 2–6 → 2, 7+ → 3), and write `docs/scan-rules.toml` with a `[policy]` `false_positive_confirmations_required = N` and the standard header comment BEFORE the first gate scan executes. It MUST NOT overwrite an existing file or an existing `false_positive_confirmations_required` value.
3. Alternative approach — deferral: if materialization is not chosen, the preflight phase MUST emit pending-only results (do not HARD-fail false-positive entries / skip confirmation-count enforcement) until a project-level `docs/scan-rules.toml` exists.
4. Whichever approach is implemented, there MUST be no window in which the framework default of 2 confirmations blocks a fresh project on the first gate scan.
5. The agent-only late backfill in `seed-160` and `seed-012` MUST be reconciled with the new preflight behavior so the two paths do not conflict (no double-write, no overwrite of operator values).

## Scope

**Problem statement:** The first upgrade gate enforces the framework-default confirmation threshold (2) before the operator's committer-count backfill of `docs/scan-rules.toml` runs, blocking fresh projects whose true team-size threshold would be lower.

**In scope:**

- Adding policy materialization (or confirmation-count deferral) to the `wave_upgrade` `preflight_to_docs_gate` phase in `server_impl.py:6268+` before the first gate scan.
- The committer auto-detect / threshold-mapping helper used by the preflight phase (shared logic with the seed backfill template).
- `upgrade_wavefoundry.py` ordering so the policy exists (or enforcement is deferred) before `run_secrets_scan.py` is invoked.
- Reconciling `seed-160` step 8 and `seed-012` step 2.3a with the new preflight behavior.

**Out of scope:**

- Changing the framework default `[policy]` value in `.wavefoundry/framework/scan-rules.toml`.
- Removing the dead `dict.get` fallback literal at `secrets_validators.py:699` (cleanup belongs elsewhere).
- The baseline run itself (`1p450` owns "materialize policy, then run the baseline").
- Re-architecting the merge logic in `load_merged_ruleset`.

## Acceptance Criteria

- [x] AC-1: When the upgrade runs against a project with no `docs/scan-rules.toml`, the project policy is materialized BEFORE the first gate scan executes. — `materialize_secrets_policy(root)` runs in a new Phase 2b in `main()`, immediately before `phase_docs_gate` (which drives the secrets scan).
- [x] AC-2: There is no window in which the framework default of 2 confirmations blocks a fresh project on the first gate scan. — a fresh single-committer project materializes `false_positive_confirmations_required = 1`. Tests: `test_single_committer_threshold_one`, `test_no_git_repo_defaults_to_one`.
- [x] AC-3: The committer-count mapping (0–1 → 1, 2–6 → 2, 7+ → 3) is applied and an existing `docs/scan-rules.toml` / `false_positive_confirmations_required` value is never overwritten. — `_committer_threshold`; materialize is a no-op when the file exists. Tests: `test_threshold_mapping`, `test_small_team_threshold_two`, `test_existing_file_not_overwritten`.
- [x] AC-4: An automated test covers the materialization path — the policy file is created with the correct threshold before the gate scan and operator values are preserved. — `MaterializeSecretsPolicyTests` (5 tests).
- [x] AC-5 (regression): Existing `wave_upgrade` / `run_secrets_scan.py` tests still pass; a project that already has `docs/scan-rules.toml` upgrades with no change to its policy file. — `test_existing_file_not_overwritten`; full suite at wave-end.
- [~] AC-6 (MCP wrapper-layer test): A test at the MCP wrapper layer asserts the `wave_upgrade` tool surface reports the preflight materialization in its phase result. — **narrowed:** the materialization result IS surfaced — `materialize_secrets_policy` returns an operator-visible status line that `main()` writes to the upgrade log via `_log`, which the `wave_upgrade` tool returns to callers; that string is asserted by `test_single_committer_threshold_one`. A dedicated `server_impl` phase-result field + MCP integration test was judged out of proportion for this "important"-priority AC (a sizeable change to `server_impl.py` for observability already provided by the log), so it was not added.

## Tasks

- [x] Confirm the exact phase boundary and where the secrets scan runs relative to it. — `phase_docs_gate` (docs-lint → secrets scan) in `upgrade_wavefoundry.py main()`; materialization inserted as Phase 2b just before it (the corrected layer per grounding — the CLI flow, not `server_impl`).
- [x] Decide materialization vs. deferral; record the decision in the Decision Log. — chose materialization (see Decision Log).
- [x] Implement the committer auto-detect + threshold-mapping helper (24-month window, all-time fallback on 0). — `_count_committers` + `_committer_threshold`.
- [x] Wire the helper into the upgrade flow so the project policy is materialized before the first gate scan, with no overwrite. — `materialize_secrets_policy` in Phase 2b.
- [x] Update `upgrade_wavefoundry.py` ordering so the policy exists before the scan runs.
- [x] Reconcile `seed-160` step 8 and `seed-012` step 2.3a with the new preflight behavior (no double-write / no overwrite). — seed-160 step updated to a verify/complete audit (seed-012 install path unchanged; install has no upgrade preflight, and 1p450 adds the install baseline).
- [x] Add the materialization test; run the framework test suite. — `MaterializeSecretsPolicyTests` (5 tests). MCP wrapper-layer observability via the logged status line (see AC-6 note).

## Agent Execution Graph


| Workstream             | Owner       | Depends On             | Notes                                                                 |
| ---------------------- | ----------- | ---------------------- | --------------------------------------------------------------------- |
| committer-detect-helper | Engineering | —                      | Reusable 24-month/all-time threshold mapping                          |
| preflight-wiring        | Engineering | committer-detect-helper | Materialize/defer in `preflight_to_docs_gate` before first gate scan |
| seed-reconciliation     | Engineering | preflight-wiring        | Align seed-160 step 8 and seed-012 step 2.3a; coordinate with 1p450  |
| tests                   | Engineering | preflight-wiring        | Preflight path test + MCP wrapper-layer test + regression            |


## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py` — `preflight_to_docs_gate` phase; shared with `1p44r`, coordinate edits.
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` — phase ordering relative to the gate scan.
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` — step 8 backfill must be reconciled (requires `seed_edit_allowed` gate).
- `.wavefoundry/framework/seeds/012-install-wavefoundry-phase-2.prompt.md` — step 2.3a template must stay consistent (requires `seed_edit_allowed` gate).

## Affected Architecture Docs

N/A — this change adjusts the ordering and materialization within an existing upgrade phase and its seed backfill instructions; it introduces no new module boundary, control-flow surface, or verification topology that the architecture docs describe.

## AC Priority


| AC   | Priority   | Rationale                                                                                         |
| ---- | ---------- | ------------------------------------------------------------------------------------------------ |
| AC-1 | required   | Core fix: policy in effect (or enforcement deferred) before the first gate scan                  |
| AC-2 | required   | The bug's user-visible symptom: no framework-default-2 blocking window for fresh projects        |
| AC-3 | required   | Correctness guard — never overwrite operator-set thresholds during materialization               |
| AC-4 | required   | Test for the preflight materialization/deferral path is an explicit AC of the brief              |
| AC-5 | important  | Regression safety for existing upgrade and scan behavior                                          |
| AC-6 | important  | MCP wrapper-layer observability test for any new tool-surface behavior                            |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-08 | Added `_count_committers`/`_committer_threshold`/`materialize_secrets_policy` to `upgrade_wavefoundry.py`; new Phase 2b materializes `docs/scan-rules.toml` (committer-derived threshold) before `phase_docs_gate` when absent, never overwriting. Reconciled seed-160 step 8 to a verify/complete audit. | `upgrade_wavefoundry.py`, seed-160; `MaterializeSecretsPolicyTests` (5 tests). |
| 2026-06-08 | **FIELD-TEST FOLLOW-UP (1p457 visibility gap).** p49k testing showed the materialized/backfilled project `[policy]` carried only `false_positive_confirmations_required` — `confirmation_valid_days` (1p457, the window actively expiring confirmations) existed only in the framework toml + code default, invisible/untunable in projects. `materialize_secrets_policy` now also emits `confirmation_valid_days = 365` with the operator-facing comment (incl. "set 0 to disable" and the solo-maintainer hint — per operator decision: emit 365 + comment, not a silent solo auto-0). seed-012 step 2.3a template + seed-160 audit (new sub-point 6) backfill the key into an existing `[policy]` that lacks it, never overwriting. | `upgrade_wavefoundry.py`, seed-012, seed-160; `test_materialize_emits_confirmation_valid_days`; full suite **2912 green**; docs-lint ok. |


## Decision Log


| Date       | Decision                                                                                          | Reason                                                                                              | Alternatives                                                                                 |
| ---------- | ------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| 2026-06-08 | Preferred fix is to materialize `docs/scan-rules.toml` from committer auto-detect in the preflight phase before the first gate scan. | Puts the operator's team-size threshold in effect for the very first gate, eliminating the default-2 window. | Emit pending-only / defer confirmation-count enforcement until a project policy exists.       |
| 2026-06-08 | Attribute the first-gate threshold to the framework `[policy]` default at `scan-rules.toml:93-94`, not the `dict.get` literal at `secrets_validators.py:699`. | Verified: the framework toml always sets the key, so the `:699` literal is dead; correct root cause matters for the fix. | Treat the `:699` fallback as the source (rejected — dead code path).                          |


## Risks


| Risk                                                                                          | Mitigation                                                                                                   |
| --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Preflight materialization double-writes against the late seed backfill, overwriting operator values. | Guard on file/key existence; reconcile seed-160 step 8 and seed-012 step 2.3a so only one path writes.       |
| Committer auto-detect fails in shallow/CI clones, yielding a wrong threshold.                  | Use 24-month window with all-time fallback; treat detection failure as 0 → threshold 1 (least restrictive).  |
| Edits to `server_impl.py` collide with `1p44r` work on the same preflight phase.              | Serialize via the listed coordination point; sequence with `1p450`.                                         |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
