# Phase 4b background code re-embed silently fails (status `idle`, no trace)

Change ID: `1p4uq-bug phase4b-background-build-reliability`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-11
Wave: `1p4u5 hardware-aware-embedding-providers`

## Rationale

`wave_upgrade` builds the docs index synchronously, then launches the **code** re-embed in a detached background process (Phase 4b) so MCP is usable immediately. The JS-TS team (p4su, and again on p4g3) reported the code layer was still on the old chunker ~30 min later and `wave_index_build_status` returned `state: "idle"` ("no build has been run") — the background build silently died with **no diagnosable trace**. Root cause: `upgrade_wavefoundry.py` `Popen`s `setup_index.py --background-code` (process A) with **stdout/stderr → DEVNULL**; A does a synchronous docs build, then spawns the detached code build (process B) and only then writes B's pid. If A crashes during that docs build, **no pid is ever written** → status reports `idle` (absent pid), and A's error went to DEVNULL.

## Requirements

1. `wave_index_build_status` must distinguish "launched but failed" from "never run": a crash before the code build is spawned must leave a record so status reports `completed` (attempted), not `none`/`idle`.
2. A Phase 4b launcher crash must be **diagnosable** (logged, not DEVNULL'd).
3. `wave_upgrade(phase='cleanup')` must **warn** when the code layer's chunker version is still behind the docs layer (a silently-failed background build must not look like a finished upgrade).

## Scope

**Problem statement:** the background code re-embed can fail silently with no status signal and no log, leaving a stale code index that looks like a completed upgrade.

**In scope:** the three reliability fixes (early pid stamp, launcher logging, cleanup mismatch warning). **Out of scope:** redesigning the two-level spawn or the background build engine itself.

## Acceptance Criteria

- [x] AC-1: **Early pid record.** `setup_index.py --background-code` stamps its own pid into `background-build.pid` BEFORE the synchronous docs build, so a crash there yields a dead-pid record → `_background_build_status` returns `completed`, not `none`. Verified by reading the code path.
- [x] AC-2: **Launcher logged.** `upgrade_wavefoundry.py` redirects the Phase 4b launcher's output to `project-upgrade-bgcode.log` instead of DEVNULL (both `phase_index_update` and `phase_index_rebuild`). Verified.
- [x] AC-3: **Cleanup mismatch warning.** `phase_cleanup` warns (with the log paths + the rebuild command) when `meta.json` `chunker_versions.code != .docs`. Verified by `BackgroundCodeIncompleteWarningTests` (warns on mismatch, silent on match, silent when meta absent).
- [x] AC-4: full `run_tests.py` green (incl. `test_upgrade_wavefoundry` + `test_setup_index`).

## Tasks

- [x] `setup_index.py`: stamp `os.getpid()` to `background-build.pid` at the start of the `--background-code` path (before prewarm/docs build).
- [x] `upgrade_wavefoundry.py`: open `project-upgrade-bgcode.log` and pass it as stdout/stderr to the Phase 4b `Popen` (both launch sites).
- [x] `upgrade_wavefoundry.py`: `_warn_if_background_code_incomplete(root)` in `phase_cleanup` + 3 tests.

## Affected Architecture Docs

`N/A` — confined to the upgrade-flow scripts; no boundary/flow/verification-architecture change.

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-11 | Implemented from the JS-TS team's p4su validation (H1). Three contained fixes across `setup_index.py` + `upgrade_wavefoundry.py`; +3 `BackgroundCodeIncompleteWarningTests`. Full suite green. Verified against current source (the broader teton p3zo upgrade-state cluster — `from_version`, `pruned_count`, docs-gate lock-destroy — was already fixed in waves 1p44o/etc.). | `setup_index.py`, `upgrade_wavefoundry.py`, `tests/test_upgrade_wavefoundry.py`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-11 | Stamp the launcher's own pid early (overwritten by the real code-build pid on success). | Closes the window where a docs-build crash leaves no pid → `idle`; minimal, no engine change. | Capture `Popen().pid` in the parent — wrong pid (parent A exits after spawning B). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Dedicated launcher log diverges from the code-build log the operator watches | Both logs named in the cleanup warning + the running-in-background message. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
