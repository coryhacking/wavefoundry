# Upgrade Script Review Fixes

Change ID: `12r1z-maint upgrade-script-review-fixes`
Change Status: `implemented`
Owner: framework-engineer
Status: implemented
Last verified: 2026-05-19
Wave: `12r09 automated-upgrade`

## Rationale

Wave council review of `12r09 automated-upgrade` found six defects:

1. **AC-5 not met (12r1b)**: `Seeds changed: n/a` was never printed when no zip is present. `phase_preflight` passed `seed_diffs=[]` instead of `None`, so `_print_change_plan`'s `is None` branch never fired.
2. **`_bin_path` dead code with broken fallback**: The helper returned a bare string (not a list) in the non-bin fallback path, making it uncallable as a subprocess command. No phase actually used it, so it was safe to remove.
3. **`--cleanup` always showed `Files pruned: 0`**: The prune count from phase 2 was never persisted; the standalone `--cleanup` path always passed `pruned_count=0` to `phase_cleanup`.
4. **Extension module zip identity in standalone paths**: `--rebuild-index` and `--cleanup` used `_find_zip(root)` at call time, which would load the wrong extension module if a new zip arrived after the original upgrade.
5. **No timeout on convention hook subprocess**: A blocking or hung convention hook would stall the upgrade indefinitely.
6. **Exec of zip content not documented**: The security implication of `exec()`-ing arbitrary Python from the zip was not documented.

Additionally, the R7 `wave_dashboard_restart` guard was found in `server.py` unchanged from the original implementation, even though the previous session's change doc recorded it as revised (allow restart during upgrade). The edit was never applied to disk.

## Requirements

1. Fix `phase_preflight` to pass `seed_diffs=None` (not `[]`) when no zip is present, so `_print_change_plan` prints `Seeds changed: n/a`.
2. Remove `_bin_path` from `upgrade_wavefoundry.py`.
3. Add `zip_path: Path | None = None` to `write_upgrade_lock` in `upgrade_lib.py`. Record the zip path in the lock at write time.
4. Add `update_upgrade_lock(root, **fields)` to `upgrade_lib.py`. After phase 2, call `update_upgrade_lock(root, pruned_count=N)` so the count is available to `--cleanup`.
5. In standalone `--rebuild-index` and `--cleanup` paths, prefer the `zip_path` field from the lock file over `_find_zip(root)`, via a `_zip_from_lock(lock)` helper.
6. Add `timeout=_HOOK_TIMEOUT_S` (300 s) to the convention hook `subprocess.run` call. On `TimeoutExpired`, log a clear message and exit 3.
7. Add a `HOOK_NAMES` constant listing all 13 hook names (used by dry-run) and a `_HOOK_TIMEOUT_S = 300` constant.
8. Add a security note to `upgrade_extensions.py` docstring explaining that the extension module runs with operator privileges.
9. Remove the blocking upgrade guard from `wave_dashboard_restart_response` in `server.py` (R7 revised: allow restart; dashboard enters `upgrade_paused` automatically).
10. Add an `_ensure_scripts_on_path()` helper called at the start of any phase function that deferred-imports `upgrade_lib` or `check_version`, so phase functions are callable directly (e.g. from tests) without relying on `main()` having set up sys.path.

## Scope

**In scope:**

- `scripts/upgrade_wavefoundry.py` — AC-5 fix, `_bin_path` removal, `_zip_from_lock`, timeout, `HOOK_NAMES`, `_HOOK_TIMEOUT_S`, `_ensure_scripts_on_path`
- `scripts/upgrade_lib.py` — `write_upgrade_lock` zip_path param, `update_upgrade_lock`
- `scripts/upgrade_extensions.py` — security note in docstring
- `scripts/server.py` — remove blocking restart guard (R7 revised)
- `tests/test_upgrade_wavefoundry.py` — regression tests for AC-5, `update_upgrade_lock`, `_zip_from_lock`

**Out of scope:**

- Terminating timed-out convention hook subprocesses (sends SIGKILL after `TimeoutExpired` is caught — `subprocess.run` already does this for non-background commands)
- Storing pruned file names (just the count)

## Acceptance Criteria

- AC-1: When no zip is present, `_print_change_plan` emits `Seeds changed: n/a (no zip — current tree already applied)`.
- AC-2: `write_upgrade_lock` writes a `zip_path` field (`str | null`) in the lock file.
- AC-3: After phase 2, the lock file contains a `pruned_count` field matching the number of pruned files.
- AC-4: `--cleanup` reads `pruned_count` from the lock and shows it in the operator summary.
- AC-5: `--rebuild-index` and `--cleanup` use the zip recorded in the lock, not whatever zip is currently on disk.
- AC-6: A convention hook that exceeds 300 s is killed and the upgrade exits with code 3.
- AC-7: `wave_dashboard_restart_response` proceeds normally when the upgrade lock is present.
- AC-8: All existing tests pass; new regression tests added.

## Tasks

- Fix `seed_diffs = ... if zip_path else None` in `phase_preflight`
- Remove `_bin_path`
- Add `zip_path` param to `write_upgrade_lock`; add `update_upgrade_lock`
- Add `_zip_from_lock` helper; update `--rebuild-index` and `--cleanup` paths
- Add `timeout=_HOOK_TIMEOUT_S` with `TimeoutExpired` handler
- Add `HOOK_NAMES`, `_HOOK_TIMEOUT_S`, `_ensure_scripts_on_path` to `upgrade_wavefoundry.py`
- Add security note to `upgrade_extensions.py`
- Remove blocking guard from `wave_dashboard_restart_response` in `server.py`
- Add regression tests

## Agent Execution Graph

| Workstream    | Owner              | Depends On | Notes                                  |
| ------------- | ------------------ | ---------- | -------------------------------------- |
| lib-fixes     | framework-engineer | —          | upgrade_lib changes                    |
| script-fixes  | framework-engineer | lib-fixes  | upgrade_wavefoundry fixes              |
| server-fix    | framework-engineer | —          | server.py R7 guard removal             |
| tests         | framework-engineer | all        | regression + lock field tests          |

## Serialization Points

- `upgrade_lib.py` changes must precede `upgrade_wavefoundry.py` changes that call `update_upgrade_lock`.
- `server.py` R7 fix is independent.

## Affected Architecture Docs

N/A — no boundary or MCP surface change. Lock file schema gains `zip_path` and `pruned_count` fields (additive, old locks without them still work via `.get()` with defaults).

## AC Priority

| AC   | Priority  | Rationale                                           |
| ---- | --------- | --------------------------------------------------- |
| AC-1 | required  | AC-5 of 12r1b was not met                           |
| AC-2 | required  | Enables AC-5 (correct zip in standalone paths)      |
| AC-3 | required  | Enables AC-4                                        |
| AC-4 | required  | Operator summary accuracy                           |
| AC-5 | required  | Wrong extension module = wrong migration hooks      |
| AC-6 | required  | Prevents indefinite hang on blocked hook            |
| AC-7 | required  | R7 was documented as revised but not implemented    |
| AC-8 | required  | No regression                                       |

## Progress Log

| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-05-19 | Implemented. All 7 defects fixed; R7 guard removed from server.py; `update_upgrade_lock` added; `zip_path`/`pruned_count` in lock; convention hook timeout 300 s; AC-5 one-line fix; `_bin_path` removed; security note added. 5 new regression tests. 1418 tests pass. | `python3 .wavefoundry/framework/scripts/run_tests.py` — 1418 OK |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-19 | `_zip_from_lock` falls back to `_find_zip` for old locks | Backward compatibility — locks written before `zip_path` field existed still work | Require new lock field (breaks existing in-flight upgrades) |
| 2026-05-19 | `pruned_count` initialised to `null` in lock, updated after phase 2 | Only one write needed; `--cleanup` reads it once at startup | Write entire lock again after pruning (equivalent but more I/O) |
| 2026-05-19 | 300 s convention hook timeout | Covers any realistic migration script; gives clear error before the MCP call times out | User-configurable timeout (adds CLI complexity) |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
