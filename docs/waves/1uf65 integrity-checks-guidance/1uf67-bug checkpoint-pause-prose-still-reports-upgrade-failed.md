# Routine Memory-Checkpoint Pause Still Prints "ERROR: Upgrade failed" Prose Despite Correct Typed State

Change ID: `1uf67-bug checkpoint-pause-prose-still-reports-upgrade-failed`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-04
Wave: `1uf65 integrity-checks-guidance`

## Rationale

Target-repo field report (2026-08-04, on 1.15.2+pgt9): the historical-memory checkpoint pause
now carries correct typed state (wave 1ua8t's fix: `awaiting_memory_publication`,
`failed_phase: null`, a structured action-required block, exit 4), but the human-readable
prose still prints `ERROR: Upgrade failed during phase 'index_update'` for what is a routine,
designed checkpoint. Structured fields right, wording wrong: an operator or agent reading the
console sees a failure report for a non-failure, which is exactly the false-signal class the
1ua8t wave existed to remove.

Root cause located exactly (council, 2026-08-04, code-grounded): the publication pause raises
`SystemExit(4)` from `_pause_for_memory_action` (`upgrade_extensions.py:873-876`, via the
`pre_index_update` hook), which `main` runs one line after setting
`current_phase = "index_update"` (:4865-4866). The exit propagates into `main`'s
`except SystemExit` (:4901), which calls `_finalize_failed_upgrade(root, True, "index_update")`
(:3415-3464): that prints the field-observed sentence (:3457-3462) AND stamps
`failed_phase="index_update"` plus `failed_at` into the lock (:3435-3439), overwriting the
checkpoint's typed state. The reporter saw clean typed state only because the server layer
masks `failed_phase` to null whenever a typed `action_required` block is present
(`server_impl.py:13110`); the on-disk lock stamp is WRONG. The 1ua8t suppression is a legacy
bridge installed ONLY for `from_version` pghn/pgi7 (`upgrade_extensions.py:837-870`, gate at
:839), so every current-lineage runner routes its own pause through the failure reporter; the
existing pins (`test_upgrade_wavefoundry.py:7265-7664`) cover only the archived legacy parents.

## Requirements

1. **Red-first reproduction on the reported path:** a test drives the current-lineage
   checkpoint pause (exit 4, typed `action_required` in the lock) through `main`'s exception
   handling and asserts BOTH that the console output contains no "Upgrade failed" phrasing AND
   that the lock keeps `failed_phase: null` with no `failed_at` stamp. It must fail on the
   current tree before the fix.
2. **An action-required exit is not finalized as a failure:** at the caller (`main`'s
   `except SystemExit`, :4901), an exit whose code is the action-required code AND whose lock
   carries a typed `action_required` block skips `_finalize_failed_upgrade` entirely, printing
   action-required wording instead (what paused, then the memory work and
   `resume_after_memory`). This mirrors the legacy bridge's own recipe
   (`upgrade_extensions.py:852-865`: code check plus token/run-id match) and fixes the wrong
   lock stamp, not just the wording. Genuine failures keep the existing reporter unchanged.
3. **The existing 1ua8t suppression pins stay green** (the :7468 assertion and the
   `ArchivedLegacyMemoryCheckpointCompatibilityTests` siblings); the fix extends coverage to
   the current-lineage path rather than rewriting the reporter.

## Scope

**Problem statement:** one remaining console path reports a designed checkpoint pause as an
upgrade failure, contradicting its own typed state.

**In scope:** `main`'s `except SystemExit` handling (:4901 region) in `upgrade_wavefoundry.py`
and its tests. Serialization note: 1uf66 also edits `test_upgrade_wavefoundry.py`; implement
the two changes serially in one workstream.

**Out of scope:** checkpoint semantics and exit codes; the server-layer mask
(`server_impl.py:13110`, correct as a defense and untouched); `_finalize_failed_upgrade`'s
behavior for genuine failures; the legacy pghn/pgi7 bridge.

## Acceptance Criteria

- [x] AC-1: The current-lineage checkpoint-pause path prints action-required prose with no
  "Upgrade failed" phrasing AND leaves the lock unstamped (`failed_phase: null`, no
  `failed_at`) (red-first, both assertions).
- [x] AC-2: Genuine failure paths and the existing 1ua8t suppression pins are unchanged and
  green.
- [x] AC-3: Full framework suite passes.

## Tasks

- [x] Red-first test: current-lineage pause through main's handler, asserting prose AND lock
- [x] Skip finalization on typed action-required exits at :4901; print action-required wording
- [x] Suite + CHANGELOG bullet (current unreleased section)

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| fix        | implementer | —          |       |


## Serialization Points

- `upgrade_wavefoundry.py` and `test_upgrade_wavefoundry.py`

## Affected Architecture Docs

Candidates at Prepare: CHANGELOG only (message-wording fix).

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The false failure report and the wrong lock stamp are the defect; both assertions must hold |
| AC-2 | required | Genuine failures must keep failing loudly; over-suppression would hide real breakage |
| AC-3 | required | The handler sits on every upgrade exit path; the full suite is the regression guard |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-04 | Filed from the target-repo 1.15.2+pgt9 field report (typed state correct, prose wrong); composition site verified at upgrade_wavefoundry.py:3457-3462 with the partial 1ua8t suppression pinned at test_upgrade_wavefoundry.py:7468. | Field report 2026-08-04; code_read this session |
| 2026-08-04 | Red-first reproduction on the reported path: new CurrentLineageMemoryCheckpointPauseTests drives main's full-upgrade flow to the pre_index_update pause (typed action_required block, exit 4). Pre-fix it printed the field-observed "ERROR: Upgrade failed during phase 'index_update'" and would stamp the lock; the untyped-exit-4 control already passed. | Red run: 1 failure of 2 tests (typed-pause test failed on "Upgrade failed" prose) |
| 2026-08-04 | Fix landed at the caller: main's `except SystemExit` now recognizes the typed action-required pause via `_memory_action_required_pause` (exit code equals ACTION_REQUIRED_EXIT plus token/run-id presence in the lock's typed block, mirroring the legacy bridge recipe), skips `_finalize_failed_upgrade` entirely, and prints checkpoint wording via `_report_action_required_pause` (what paused, the memory work, resume_after_memory). Genuine failures (any other exit, missing/untyped block) keep the existing reporter byte-unchanged. | upgrade_wavefoundry.py `_memory_action_required_pause` / `_report_action_required_pause` + handler edit; green run 2/2 |
| 2026-08-04 | 1ua8t suppression pins and genuine-failure paths reverified: ArchivedLegacyMemoryCheckpointCompatibilityTests + HistoricalMemoryUpgradeExtensionBootstrapTests green (16/16); full test_upgrade_wavefoundry module green (442 tests). | `unittest tests.test_upgrade_wavefoundry` OK (442 tests) |
| 2026-08-04 | Delivery release lane WITHHELD on a missing class-b transition-run disclosure (the upgrade installing this fix still runs the pre-fix parent, which may print the old prose one final time). Repaired: the CHANGELOG bullet now carries the residue disclosure including the sentence that stops the false bug report; typed state and resume are unaffected on that run. | CHANGELOG 1uf67 bullet transition-run sentences; release lane report 2026-08-04 |
| 2026-08-04 | Full framework suite green after both wave changes landed: 6805 tests across 62 files, OK. Docs gate green (`wf_validate_docs` passed). | `run_tests.py` OK (6805 tests); wf_validate_docs ok |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-04 | Recognition keys on token/run-id PRESENCE in the typed block, not on a value match against the raising site | The caller (main's handler) has no access to the pause's token/run_id locals the way the legacy bridge closure does; presence of a fully formed typed block plus the action-required exit code is the same evidence the server layer already trusts for its failed_phase mask, and only `_arm_memory_action_required` writes that shape | Threading token/run_id from the pause into main (rejected: the pause is raised from an extension hook across a module boundary; the lock IS the designed channel); matching on `kind == "historical_memory"` only (rejected: weaker than the bridge recipe the change doc mandates mirroring) |
| 2026-08-04 | Checkpoint wording prints via `_log` (stdout plus upgrade log), not `_err` | The pause is designed behavior; `_err` prefixes `ERROR:` which is exactly the false signal this change removes, and the wording must land in the upgrade log before `_close_log` runs | Reusing `_err` without the prefix (rejected: `_err` hard-codes the prefix); print-only (rejected: loses the upgrade-log record) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Suppressing too broadly hides a genuine index_update failure | Requirement 2 keys the wording on the typed action-required state, not on the phase name; genuine failures pinned unchanged |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
