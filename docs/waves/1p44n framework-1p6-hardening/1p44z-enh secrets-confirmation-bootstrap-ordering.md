# Materialize Project Secrets Policy Before The First Upgrade Gate

Change ID: `1p44z-enh secrets-confirmation-bootstrap-ordering`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-08
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

- [ ] AC-1: When `wave_upgrade` runs `preflight_to_docs_gate` against a project with no `docs/scan-rules.toml`, the project policy is materialized (or confirmation-count enforcement is deferred) BEFORE the first gate scan executes.
- [ ] AC-2: There is no window in which the framework default of 2 confirmations blocks a fresh project on the first gate scan (a fresh single-committer project is not HARD-failed for unconfirmed false positives on first upgrade).
- [ ] AC-3: If materialization is chosen, the committer-count mapping (0–1 → 1, 2–6 → 2, 7+ → 3) is applied and an existing `docs/scan-rules.toml` or existing `false_positive_confirmations_required` value is never overwritten.
- [ ] AC-4: An automated test covers the preflight materialization (or deferral) path — asserting the policy file is created with the correct threshold (or that enforcement is deferred) before the gate scan and that operator values are preserved.
- [ ] AC-5 (regression): Existing `wave_upgrade` and `run_secrets_scan.py` tests still pass; a project that already has `docs/scan-rules.toml` upgrades with no change to its policy file.
- [ ] AC-6 (MCP wrapper-layer test): A test at the MCP wrapper layer asserts that the `wave_upgrade` tool surface reports the preflight materialization/deferral in its phase result so a caller can observe it.

## Tasks

- [ ] Confirm the exact `preflight_to_docs_gate` phase boundary in `server_impl.py:6268+` and where `run_secrets_scan.py` is invoked relative to it.
- [ ] Decide materialization vs. deferral; record the decision in the Decision Log.
- [ ] Implement the committer auto-detect + threshold-mapping helper (24-month window, all-time fallback on 0) reused by the preflight phase.
- [ ] Wire the helper into `preflight_to_docs_gate` so the project policy is materialized (or enforcement deferred) before the first gate scan, with no overwrite of existing files/values.
- [ ] Update `upgrade_wavefoundry.py` ordering if needed so the policy exists before the scan runs.
- [ ] Reconcile `seed-160` step 8 and `seed-012` step 2.3a with the new preflight behavior (no double-write / no overwrite).
- [ ] Add the preflight materialization/deferral test and the MCP wrapper-layer test; run the framework test suite.

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
|      |        |          |


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
