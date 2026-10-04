# Dashboard Done Statuses From The Lint Constants

Change ID: `1zody-bug dashboard-done-statuses-from-lint-constants`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-03
Wave: 1zoju session-follow-ups

## Rationale

Wave `1zls7` change `1zlu0` made `DONE_CHANGE_STATUSES` in `wave_lint_lib/constants.py` the one definition of a done change (`TERMINAL_CHANGE_STATUSES` plus `implemented`), read by wave close and the docs-lint dependency rule. Its Decision Log left the dashboard's own lists as a follow-up. They still disagree with that set and with each other:

- `dashboard_lib._TERMINAL_CHANGE_STATUSES = {"complete", "completed", "closed"}`, read by `_is_terminal_change_status`. It lacks `implemented`, `done`, `deferred`, `moved` and `superseded`, and includes `closed`, which is a wave status, not a change status (no `ALLOWED_CHANGE_STATUS_TRANSITIONS` key). Its three callers: `_parse_tasks` and `_parse_ac_items` (an item with no checkbox mark is done when its change is terminal), and `_wave_only_metric_counts` (`change_done`, where changes of closed waves are counted done separately through `closed_wave_ids`).
- `dashboard/dashboard.js` `DONE_STATUSES = new Set(["complete", "completed", "done", "implemented", "approved", "closed"])`, read by `isDone(status)` at every change-progress site (dialog scope ordering, `computeProgress`, the progress totals and the pending counts). It lacks `deferred`, `moved` and `superseded` and carries `approved` and `closed`, neither a change status.

The practical effect is wrong progress. A census of member statuses over every `docs/waves/*/wave.md` on 2026-10-03 finds 654 records in `implemented`, the most common status in the corpus; in an open wave each would read as not done in the Python metrics. A `deferred` or `superseded` change reads as pending in both the Python and the JavaScript progress, although close treats it as done. No change record in the corpus carries `approved` or `closed`, so dropping them changes no current display.

`dashboard/ds/wfds.js` `badgeClass(status)` was named in the follow-up, but it is a tone map, not a done classification: its `status-ok` list mixes in-progress statuses (`active`, `implementing`, `ready`) with finished ones, and it also serves wave and review statuses. Deriving it from the done set would recolour in-progress badges. It stays as it is (Decision Log).

## Requirements

1. `dashboard_lib` drops `_TERMINAL_CHANGE_STATUSES` and `_is_terminal_change_status` judges a status as `status.strip().lower() in constants.DONE_CHANGE_STATUSES`, with the module imported (`from wave_lint_lib import constants`) and the attribute read at call time, not bound by a from-import, so patching the constant (AC-2) changes the predicate. No status list remains in `dashboard_lib`.
2. `collect_dashboard_snapshot` adds `config.done_change_statuses`, the sorted list of `DONE_CHANGE_STATUSES`.
3. `dashboard.js` keeps the declaration `const DONE_STATUSES = new Set()` (the `test_dashboard_terminology.py` harness slices the source from the literal `const DONE_STATUSES`), now empty, and refills it in place. An `updateDoneStatuses(list)` function, defined immediately after `isDone` so it falls inside the harness slice (`'const DONE_STATUSES'` to `'function FrameworkProcessDiagram('`), clears the set and adds each value lower-cased. It is called in the `App` render body beside `updateTerminology(snapshot?.config?.terminology)` as `updateDoneStatuses(snapshot?.config?.done_change_statuses)`, so no status literal remains in the JavaScript and every `isDone` call in the same render sees the current set.
4. `wfds.js` `badgeClass` is unchanged.
5. Platform behaviour: data and display only; the dashboard is a local HTTP server and browser page with no platform-specific path, identical on Windows, macOS, Linux and WSL2.

## Scope

**Problem statement:** the dashboard judges change completion with two hand-kept lists that disagree with the framework's done set.

**In scope:**

- `dashboard_lib.py` (Requirement 1, 2) and `dashboard/dashboard.js` (Requirement 3).
- Tests: `tests/test_dashboard*.py` cases for the Python predicate and the payload key, and the JavaScript harness in `tests/test_dashboard_terminology.py` (or a sibling) for `isDone` reading the payload.
- A CHANGELOG bullet.

**Out of scope:**

- `wfds.js` `badgeClass` tone colours.
- Wave status classification in the dashboard (`activeWaves`, `pendingWaves`, `closed_wave_ids`).

## Acceptance Criteria

- [x] AC-1: Reproducer, failing first: `_is_terminal_change_status("implemented")` and `("deferred")` are true and `("closed")` is false; each assertion fails on the current tree.
- [x] AC-2: A test asserts the Python predicate agrees with `DONE_CHANGE_STATUSES` for every key of `ALLOWED_CHANGE_STATUS_TRANSITIONS` plus `closed` and `approved`, and patching `DONE_CHANGE_STATUSES` changes the predicate (it reads the constant, not a copy).
- [x] AC-3: `collect_dashboard_snapshot(...)["config"]["done_change_statuses"]` equals `sorted(DONE_CHANGE_STATUSES)`.
- [x] AC-4: The JavaScript harness loads a snapshot whose `config.done_change_statuses` is `["complete", "implemented"]` and shows `isDone("implemented")` true, `isDone("approved")` false and `isDone("done")` false (the payload decides); the existing terminology harness still passes.
- [x] AC-5: A census test asserts `dashboard.js` contains no change-status string literal inside the `DONE_STATUSES` definition and `dashboard_lib.py` defines no status set.
- [x] AC-6: The change's own test files and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Write the AC-1 reproducer and confirm it fails.
- [x] Rewire `dashboard_lib` (Requirement 1) and add the payload key (Requirement 2).
- [x] Rewire `dashboard.js` (Requirement 3); update the terminology harness if its slice needs the payload.
- [x] Add the AC-2 to AC-5 tests.
- [x] Add the CHANGELOG bullet; run the full suite in a scratch copy and docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| python | implementer | none | AC-1 to AC-3 |
| javascript | implementer | python | AC-4, AC-5; needs the payload key |

## Serialization Points

- `.wavefoundry/framework/scripts/dashboard_lib.py`, `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/test_dashboard_terminology.py`
- The CHANGELOG at the repository root is edited too.

## Affected Architecture Docs

N/A: the dashboard reads an existing constant and passes it to its own page; no boundary or flow changes.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The defect, failing first |
| AC-2 | required | Keeps the predicate on the single source |
| AC-3 | required | The payload the page depends on |
| AC-4 | required | The page reads the payload, not a list |
| AC-5 | important | Stops a list from coming back |
| AC-6 | required | Suite and lint gate |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-03 | Implemented: `_TERMINAL_CHANGE_STATUSES` removed; `_is_terminal_change_status` reads `DONE_CHANGE_STATUSES` at call time through `_lint_constants()`, a function-level `from wave_lint_lib import constants` (a module-level import broke the upgrade path, which imports `dashboard_lib` to stop the dashboard from a tree without `wave_lint_lib`; `test_upgrade_protocol` caught it); snapshot `config.done_change_statuses`; `dashboard.js` `DONE_STATUSES` starts empty and `updateDoneStatuses` (after `isDone`) refills it in the `App` render body; CHANGELOG updated | Tests: `test_dashboard_terminology.DashboardDoneStatusTests` (AC-1 to AC-5, the page harness under Node); the existing terminology harness passes. Failing-first on HEAD: all five failed. Mutations M28 to M33 all killed. full suite `run_tests.py --no-cache` in a scratch copy: 10,925 tests, 157 files, OK; `--profile second` and `--profile declared` OK (second 10,922 tests, declared 10,925; the final run, after every code change; 34 tests skipped in the full run). Gapfill: retrieval used grep and sed over the scripts tree instead of the MCP code tools, because the edits needed exact multi-line anchors in a 25,000-line module and the attached MCP server runs the pre-change code |
| 2026-10-03 | Planned from `1zlu0`'s Decision Log follow-up | Corpus census: 654 `implemented` member records; zero `approved` or `closed` change statuses |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-03 | Python imports `DONE_CHANGE_STATUSES`; JavaScript receives it in the snapshot | One source; the page already reloads the snapshot on every poll or server-sent event | Generate a JS constant at build time (rejected: a second copy in a shipped file); hard-code the corrected list in JS (rejected: drifts again) |
| 2026-10-03 | Use the done set, not the terminal set | Close and the dependency rule treat `implemented` as done; the dashboard's progress should agree with close | `TERMINAL_CHANGE_STATUSES` (rejected: `implemented` would read pending while close accepts it) |
| 2026-10-03 | Leave `wfds.js` `badgeClass` alone | It is a tone map spanning in-progress, wave and review statuses, not a done test | Derive it from the done set (rejected: recolours `active` and `ready` badges) |
| 2026-10-03 | Drop `closed` and `approved` from the change done set | Neither is a change status; the census finds no member record carrying either | Keep them as legacy (rejected: nothing uses them) |
| 2026-10-03 | Readiness amendment F9: accept that the drop also affects documents read through the dashboard's fallback status form | `dashboard_lib` reads a change document's status as `server._CHANGE_STATUS_PATTERN.search(text) or server._STATUS_PATTERN.search(text)`, so a target repository whose change documents carry only a plain `Status: approved` or `Status: closed` line now reads those changes as not done in open-wave progress. Measured here on 2026-10-03 (recheck N3) over the files `dashboard_lib.collect_changes` actually reads (each member's `wave_md.parent / f"{change['id']}.md"` plus the listed plans), the fallback yields `approved` for 0 and `closed` for 0. The 2 `Status: approved` files an earlier count found are review evidence documents (`delivery-qa-review.md` and `delivery-code-review.md` in wave `1yq6a`), not change documents, and the dashboard never reads them as changes. Target repositories are not measured. Accepted because neither value is a change status the framework defines, and a closed wave's changes are still counted done through `closed_wave_ids` | Keep `approved` and `closed` for the fallback form only (rejected: reintroduces a dashboard-only list) |
| 2026-10-03 | Readiness amendment F8: define `updateDoneStatuses` inside the harness slice and call it in the `App` render body; read `constants.DONE_CHANGE_STATUSES` at call time | Mirrors `updateTerminology`, keeps the terminology harness working, and makes AC-2's patch effective | Refill in the fetch callback (rejected: outside the render path the harness exercises); from-import the constant (rejected: a patch would not reach the bound copy) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A deferred or superseded change now counts as done in open-wave progress | Intended: close already counts it done; the progress bar now agrees |
| The page renders before the first snapshot with an empty set | `updateDoneStatuses` runs in the `App` render body before any child that calls `isDone`, so the set is filled in the same render |
| Target repositories using the fallback `Status:` form with `approved` or `closed` | Accepted (Decision Log F9); closed-wave changes still count done |
| An older cached page meets a newer server, or the reverse | Missing key leaves the set empty (nothing reads as done) rather than wrong; a page reload fixes it |
| Platform behaviour | Data only; identical on Windows, macOS, Linux and WSL2 (Requirement 5) |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
