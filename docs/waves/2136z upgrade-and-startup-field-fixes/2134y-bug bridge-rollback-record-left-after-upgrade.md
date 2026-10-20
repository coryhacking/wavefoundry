# Remove the bridge rollback record after a successful upgrade

Change ID: `2134y-bug bridge-rollback-record-left-after-upgrade`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-19
Wave: `2136z upgrade-and-startup-field-fixes`

## Rationale

Waveforge reported that after an upgrade, `BRIDGE-ROLLBACK.json` is neither tracked nor ignored and holds an absolute path. Verified: `upgrade_bridge_bootstrap.install` writes `.wavefoundry/framework/BRIDGE-ROLLBACK.json` with `rollback` set to `str(rollback)` (an absolute path to `.wavefoundry/framework.rollback-<build_id>/`) and stringified `quiescence_locks`; nothing deletes it, the manifest prune never sees it, and the rendered ignore block (`.wavefoundry/upgrade-assets/`, `.wavefoundry/framework.rollback-*/`) has no rule for it. Change 212b9's security note S-1 treats the file as evidence of an interrupted bridge, so leaving it after success also blurs that signal. (`upgrade-ledger/` is not ours: nothing in this repository writes it.)

## Product Intent

After a successful upgrade the target repository has no stray rollback record to commit by accident, and the record's presence again means an upgrade was interrupted. Boundaries: an interrupted or failed upgrade keeps the record for recovery. AC-1 tests the outcome.

## Requirements

1. When the upgrade completes successfully, the upgrade removes `.wavefoundry/framework/BRIDGE-ROLLBACK.json` (and only on success; a failed or interrupted run leaves it).
2. The rendered ignore block also lists `.wavefoundry/framework/BRIDGE-ROLLBACK.json`, so a record left by an interrupted run is not committed by accident.
3. The removal runs in `phase_cleanup` after the upgrade lock is released successfully, tolerates a missing record (same-protocol upgrades never write one), and goes through the framework's contained file operations so a symlink at the record path is not followed. No recovery path reads the record today (only a test does); the orphaned `framework.rollback-*` directory stays as it is (already ignored).

## Scope

**Problem statement:** A rollback record with an absolute path survives a successful upgrade, untracked and unignored.

**In scope:**

- The upgrade success path in `upgrade_wavefoundry.py` (or the bridge completion step), the rendered ignore block in `render_platform_surfaces.py`, this repository's rendered `.gitignore`, tests, one CHANGELOG bullet.

**Out of scope:**

- Making the record's paths relative.
- `upgrade-ledger/` (a distribution's runner).

**Platform behaviour:** the same on Windows, macOS, Linux and WSL2: removal uses the existing contained file operations; Windows file locks on the record are not expected because it is written and closed by the bridge.

## Acceptance Criteria

- [x] AC-1: A simulated successful upgrade leaves no `BRIDGE-ROLLBACK.json`; a simulated interrupted or failed upgrade leaves it. Oracle: tests on the upgrade fixtures, with a mutant that skips the removal.
- [x] AC-2: The rendered ignore block contains the record's path, and this repository's `.gitignore` is re-rendered with it. Oracle: renderer test and grep.
- [x] AC-3: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Find the success point and remove the record there.
- [x] Add the ignore rule; re-render.
- [x] Add tests.
- [x] Add the CHANGELOG bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| upgrade | implementer | none | success path, ignore rule |

## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/upgrade_bridge_bootstrap.py`, `.wavefoundry/framework/scripts/render_platform_surfaces.py`

## Affected Architecture Docs

N/A: an artefact's lifetime; no flow change.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required | The reported defect. |
| AC-2 | important | Defence for interrupted runs. |
| AC-3 | required | Standard verification. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-19 | Planned. | Waveforge carried-forward note; investigation of `upgrade_bridge_bootstrap.install` and the ignore block. |
| 2026-10-19 | Readiness red-team: success point identified (`phase_cleanup` after `remove_upgrade_lock`; every failure path exits before it with the lock retained, so an interrupted run keeps the record by placement); the old requirement 3 was vacuous (no recovery path reads the record) and is replaced by the placement, missing-file and containment rule. | Readiness red-team primer; receipt `review-policy-0b4525186c4d8166a8f7` superseded. |
| 2026-10-19 | Implemented: `_remove_bridge_rollback_record` in `upgrade_wavefoundry.py`, called in `phase_cleanup` after the lock-release branches (beside the "Upgrade lock removed" log); lstat, missing record tolerated, `contained_files.unlink_contained` with the lstat identity, any refusal or OS error only warns and leaves the entry. Ignore rule added to `_GITIGNORE_BLOCK`; repo `.gitignore` re-rendered with `render_platform_surfaces.render_gitignore_block` (one added line). Seed 050's verbatim copy of the block still needs the same line under `seed_edit_allowed` (left to the coordinator), so `test_seed_050_canonical_block_matches_the_renderer_constant` fails until then. Old-code window: a 1.32 runner will not remove the record; the next successful upgrade on new code does. Windows/macOS/Linux/WSL2: same path through the contained file operations; the symlink test skips where symlinks are unavailable. | Five new `PhaseCleanupLockStateTests` pass; focused run of the two files: 892 tests, the single failure is the seed binding test. Scratch-copy mutants all killed: skip removal (2 fail), remove before lock release (unreleased-lock test fails), plain `os.unlink` (symlink test fails). |
| 2026-10-19 | Coordinator: added `.wavefoundry/framework/BRIDGE-ROLLBACK.json` to seed 050's canonical gitignore block (seed gate opened and closed around the one-line edit) so `test_seed_050_canonical_block_matches_the_renderer_constant` matches the renderer list; CHANGELOG bullet added. Combined focused run (test_upgrade_wavefoundry, test_render_platform_surfaces, test_indexer, test_startup_install, test_inference_provider, test_upgrade_protocol): 1430 OK. | `scratchpad/2136z-focused.log`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-19 | Delete on success and ignore. | Keeps S-1's meaning and stops accidental commits. | Only ignore: leaves stale records with absolute paths. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Removing the record before recovery finishes. | Remove only at the final success point; test the interrupted case. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
