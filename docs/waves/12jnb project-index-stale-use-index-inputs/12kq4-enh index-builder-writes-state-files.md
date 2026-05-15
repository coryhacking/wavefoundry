# Dashboard: IndexBuilder Writes State Files for External Visibility

Change ID: `12kq4-enh index-builder-writes-state-files`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

When the dashboard's `IndexBuilder` fires an auto-index rebuild (triggered by file-change detection or startup stale check), it spawns `indexer.py` but writes no `index-build.json` state file and routes stderr to DEVNULL. This means external `wave_index_build_status` MCP queries return `state: "idle"` while the build is running, and there is no log for progress. The MCP `wave_index_build` path already writes these files; auto-index builds should too, so both paths are consistent and any in-progress rebuild is visible to all observers.

## Requirements

1. Before spawning `indexer.py`, `IndexBuilder._execute()` must write `index-build.json` with PID, `started_at`, `content`, `layer`, and `full` fields — matching the schema written by `run_index_rebuild`.
2. `IndexBuilder._execute()` must route `indexer.py` stderr to `index-build.log` (the canonical log path for the layer) rather than DEVNULL, and clear the file before each build.
3. After the build completes, `IndexBuilder._execute()` must remove `index-build.json` (or leave it with a sentinel so `wave_index_build_status_response` treats the build as finished) so stale PIDs do not persist.
4. `wave_index_build_status_response` for the framework layer must return `state: "running"` when an `IndexBuilder`-triggered framework build is active.
5. The existing `IndexBuilder` status machine (`build_status: "running"` → `"done"`) must continue working as before for the dashboard's own snapshot overlay.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/dashboard_server.py` — `IndexBuilder._execute()`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py` — regression tests

**Out of scope:**

- Changing `run_index_rebuild` in `server.py` (already correct)
- Changing `wave_index_build_status_response` logic (no changes needed if state file schema matches)
- Changing `indexer.py`

## Acceptance Criteria

- AC-1: While an `IndexBuilder`-triggered framework build is running, `wave_index_build_status_response(root, "framework")` returns `state: "running"`.
- AC-2: After an `IndexBuilder`-triggered build completes, `index-build.json` is absent or non-running so subsequent status queries return `state: "finished"` or `"idle"`.
- AC-3: `index-build.log` for the layer is written during an `IndexBuilder` build and contains indexer output.
- AC-4: The dashboard snapshot's `build_status` for the layer remains correct during and after the build (existing behavior preserved).
- AC-5: Regression tests cover AC-1 and AC-2.

## Tasks

- Update `IndexBuilder._execute()` to write `index-build.json` before spawn and route stderr to `index-build.log`
- Remove or overwrite `index-build.json` after build completes
- Add regression tests for external status visibility during/after an `IndexBuilder` build

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | External status queries must see running builds |
| AC-2 | required | Stale PIDs must not persist and confuse status |
| AC-3 | important | Log output aids debugging; not critical to status display |
| AC-4 | required | Existing dashboard behavior must not regress |
| AC-5 | required | Tests protect the contract |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| `proc.communicate()` blocks until done — state file written with final PID, but communicate() finishes synchronously so no race with removal | Remove state file in finally block after communicate() returns |
| `index-build.log` open handle conflicts if two builds overlap | `IndexBuilder` serializes builds; only one runs at a time |

## Implementation Verification

`IndexBuilder._execute()` now writes `index-build.json` (with PID, `started_at`, `content`, `layer`, `full`) before `communicate()` runs, routes `indexer.py` stdout+stderr to `index-build.log`, and removes the state file in a `finally` block after `communicate()` returns. Two helper methods `_index_state_path` and `_index_log_path` expose the canonical file locations. Regression tests verify the state file is present during the build and absent after it completes. Verified with `python3 .wavefoundry/framework/scripts/run_tests.py` (1159 tests, OK) and `./.wavefoundry/bin/docs-lint` (ok).
