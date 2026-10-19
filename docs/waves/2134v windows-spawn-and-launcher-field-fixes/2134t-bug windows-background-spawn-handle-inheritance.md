# Background spawns inherit handles on Windows

Change ID: `2134t-bug windows-background-spawn-handle-inheritance`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-19
Wave: `2134v windows-spawn-and-launcher-field-fixes`

## Rationale

Waveforge reported (2026-10-19, against `v1.32.0`) that a team on native Windows saw `MCP error -32000: Connection closed` during or right after write-mutation tool calls, which trigger the background index refresh. The refresh spawn in `wf_server/index_handlers.py` (the `subprocess.Popen` in the background refresh launcher, after `_background_refresh_active`) passes `close_fds=os.name != "nt"`, so on Windows `close_fds` is `False`. That enables handle inheritance: every inheritable handle of the server process, including the stdio transport's pipe ends, passes to the detached indexer. `DETACHED_PROCESS` and `CREATE_NEW_PROCESS_GROUP` do not prevent it. Waveforge confirmed that spawning through `subprocess_util.isolated_popen`, which keeps Python's default `close_fds=True`, stopped the disconnects.

The same `close_fds=os.name != "nt"` appears in three rendered hook-helper spawns in `render_platform_surfaces.py`, and `tests/test_render_platform_surfaces.py` pins it with an assertion (`'close_fds=os.name != "nt"'`). A hook child that inherits the hook process's pipes to the agent host can keep those pipes open after the hook returns. The per-OS form dates from Python before 3.7, where `close_fds=True` could not be combined with redirected standard handles on Windows. The framework requires Python 3.11, and all four spawns already redirect stdin, stdout and stderr to `DEVNULL`, so the exception has no remaining purpose.

## Product Intent

Windows operators stop losing the MCP connection when write tools trigger a background refresh, and rendered hooks stop handing the host's pipes to their detached children. Boundaries: detach behaviour, process groups, window suppression and the POSIX path are unchanged; no new dependency. AC-1 and AC-2 test the outcome as far as a non-Windows test run can, and AC-4 records what remains a Windows field confirmation.

## Requirements

1. Every `subprocess` call (`Popen`, `run`, `call`, `check_call`, `check_output`, or `subprocess_util.isolated_popen`/`isolated_run`) in `.wavefoundry/framework/scripts/` outside `tests/`, and in the hook-helper source that `render_platform_surfaces.py` renders, either omits `close_fds` or passes `close_fds=True`, on every OS. The set is derived by that rule; implementation records the census.
2. The four known spawns (the background index refresh and the three rendered hook helpers) keep their current `stdin`/`stdout`/`stderr` redirection, `cwd`, and detach arguments.
3. The rendered hook surfaces in this repository are re-rendered so the committed hook files carry the change: every rendered hook body under `.claude/hooks/`, `.cursor/hooks/`, `.github/hooks/` and `.windsurf/hooks/` that contains a hook-helper spawn.
4. A test enforces requirement 1 across the framework scripts and the rendered hook-helper source, replacing the per-OS `close_fds` pin in `test_render_platform_surfaces.py`.

## Scope

**Problem statement:** On Windows, background spawns pass `close_fds=False`, so detached children inherit the server's or hook's handles, including stdio pipes.

**In scope:** `wf_server/index_handlers.py`, `render_platform_surfaces.py` (the three hook-helper spawns), the rendered hook files in this repository, `tests/test_render_platform_surfaces.py` and a census test, one CHANGELOG bullet, and the Windows support note in `docs/references/native-windows-support.md` if it describes spawn handles.

**Out of scope:** the MCP launcher command (Waveforge's W2, `python3` resolving to the Store alias on Windows: declined by operator decision, since the committed MCP config is shared across operating systems and setup already catches the alias), other Windows creation flags, and switching spawns to `isolated_popen` wholesale beyond what requirement 1 needs.

**Platform behaviour:** Windows: detached children no longer inherit handles other than the redirected standard ones (Python passes those through `STARTUPINFO` with a handle list). macOS, Linux and WSL2: unchanged, since `close_fds` was already `True` there.

## Acceptance Criteria

- [x] AC-1: A census test fails if any framework script outside `tests/`, or the rendered hook-helper source, passes `close_fds` with any value other than the literal `True`; it passes on the changed tree. Oracle: the test, with a scratch mutant restoring `close_fds=os.name != "nt"` in one spawn.
- [x] AC-2: The four spawns, called with `subprocess.Popen` patched, receive `close_fds=True` or no `close_fds` argument, and their other arguments are unchanged. Oracle: a test per spawn on the current OS.
- [x] AC-3: The rendered hook files committed in this repository contain no per-OS `close_fds` form after re-rendering. Oracle: a grep recorded in the Progress Log.
- [x] AC-4: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change. The Windows disconnect itself is confirmed in the field (Waveforge's reporter) and recorded when reported; this repository has no Windows runner.

## Tasks

- [x] Census the framework's `close_fds` uses and record them.
- [x] Change the refresh spawn and the three hook-helper spawns.
- [x] Re-render the platform surfaces and check the hook files.
- [x] Replace the per-OS pin with the census test; add the per-spawn argument tests.
- [x] Add the CHANGELOG bullet; update the Windows support note if it covers spawns.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| spawns | implementer | none | scripts and tests |
| render | implementer | spawns | rendered hooks |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/index_handlers.py`, `.wavefoundry/framework/scripts/render_platform_surfaces.py`, `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`

## Affected Architecture Docs

N/A: argument change inside existing spawns; no boundary, flow or contract change.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Prevents the per-OS form from returning anywhere. |
| AC-2 | required  | The reported spawn and its siblings are fixed without other drift. |
| AC-3 | important | The committed hooks are what hosts run. |
| AC-4 | required  | Standard change-local verification; field confirmation recorded honestly. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-19 | Planned from Waveforge's W1 report against v1.32.0. | Four spawns with `close_fds=os.name != "nt"`: `index_handlers.py` background refresh, `render_platform_surfaces.py` three hook helpers; all redirect stdio to `DEVNULL`. |
| 2026-10-19 | Readiness red-team primer: no blocker; census confirmed complete (no `os.spawn*`, `os.exec*` or `os.fork` in non-test scripts; multiprocessing on Windows does not inherit). Repaired before any approval: requirement 1 covers every `subprocess` call form, requirement 3 names `.windsurf/hooks/` (12 rendered hook files carry the form). Implementation notes: AC-2 for the three rendered spawns may exec the rendered helper source with `Popen` patched or use an AST check; say which. The `render_platform_surfaces.py` post-edit spawn sits outside a try/except, so a pre-3.7 host Python would now raise rather than degrade; 3.6 is end-of-life and the framework requires 3.11. | Red-team primer report; receipt `review-policy-be2317c48088bbada744` superseded. |
| 2026-10-19 | Readiness complete (code, QA, council). Implementation notes: the three rendered spawns live in three template functions (`hook_helpers`, `claude_context_efficiency_source`, `claude_stop_source`), so the census must scan raw source text or every rendered hook body, not an AST of the renderer, and the AC-1 mutant runs once in a template other than `hook_helpers`; AC-2 execs the rendered sources with `Popen` patched and asserts stdin/stdout/stderr, `cwd` and the detach arguments for both `os.name` branches; 15 committed hook files carry the form (`.claude/hooks` 4, `.cursor/hooks` 4, `.github/hooks` 2, `.windsurf/hooks` 2, plus 3 stale `.pyc` files in `.claude/hooks/__pycache__`); AC-4's Windows field confirmation is not a close condition. | Readiness reports; receipt `review-policy-20d9335943906f19a533`. |
| 2026-10-19 | Implemented. Census (requirement 1): the only `close_fds` arguments in framework scripts outside `tests/` were the four `close_fds=os.name != "nt"` spawns (`index_handlers._start_background_index_refresh`; `render_platform_surfaces` `hook_helpers`, `claude_context_efficiency_source`, `claude_stop_source`); all four now pass `close_fds=True`, with stdio, `cwd` and detach arguments unchanged. Re-rendered: 12 committed hook files changed, each only on that line (`.claude/hooks` 4, `.cursor/hooks` 4, `.github/hooks` 2, `.windsurf/hooks` 2); grep finds no per-OS form left. Tests: `test_no_spawn_passes_close_fds_other_than_true` (AST census of every non-test framework script plus every rendered `*_source`/`hook_helpers` body, at least three rendered bodies reached); `test_background_index_refresh_never_inherits_handles` (patched `Popen`, both `os.name` branches, asserts close_fds, stdio, cwd and detach arguments); the per-OS pin in `test_post_edit_reindex_spawn_has_per_os_detach_branch` now requires `close_fds=True`. AC-2 for the three rendered spawns uses the AST census of the rendered bodies rather than exec with a patched `Popen` (the hook bodies are full programs reading stdin), recorded as the readiness note allowed. Scratch mutants: per-OS form restored in the refresh spawn (2 failures), in `claude_context_efficiency_source` (census fails), `close_fds=False` in `hook_helpers` (2 failures); control passes. `docs/references/native-windows-support.md` detached-jobs bullet gains one sentence. Gapfill: shell edits used because auto mode prefers Bash for file work; the edit gate was opened for the framework edits and closed after. | `run_tests.py --file test_render_platform_surfaces.py --file test_server_tools.py`: render file 150 OK; server_tools new test OK. |
| 2026-10-19 | Delivery repair (red-team note): the census matched only `close_fds=` keywords, so a value passed through a mapping (`**{"close_fds": ...}`, `kwargs["close_fds"] = ...`) was invisible; it now also flags any `"close_fds"` string in the scanned sources (none exist today). A scratch mutant with `**{"close_fds": os.name != "nt"}` in `claude_stop_source` now fails the census; the repository passes. Security note applied: the Windows support sentence says the spawns use `close_fds=True` "passed explicitly or as Python's default" (the dashboard daemon relies on the default). | `HookReindexDetachTests` OK; scratch mutant run. |
| 2026-10-19 | Delivery repair (QA blocker on AC-2): the census checked only `close_fds`, so the rendered spawns' other arguments were unguarded (mutants `cwd=None` in `claude_stop_source` and `stdin` removed in `claude_context_efficiency_source` survived). Added `test_rendered_background_spawns_keep_their_isolation_arguments`: for `hook_helpers`, `claude_context_efficiency_source` and `claude_stop_source`, exactly one background `Popen` with `stdin`/`stdout`/`stderr` = `subprocess.DEVNULL`, a non-literal `cwd`, the detach `**` splat and `close_fds=True`; both mutants now fail it. Not covered (accepted): a positional `close_fds` argument (the eighth positional `Popen` parameter; no framework call passes it positionally). | `HookReindexDetachTests` OK; scratch mutants A1, A2 fail. |
| 2026-10-19 | Implemented; all ACs and tasks done. Windows field confirmation from Waveforge's reporter is still pending (not a close condition). | Whole suite `Ran 11948 tests across 201 files in 722.182s OK` (12 skipped), green receipt. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-19 | `close_fds=True` on every OS at these spawns, enforced by a census test. | Smallest change; the per-OS form is a pre-3.7 workaround and the framework requires 3.11. | Switch to `isolated_popen` everywhere: larger diff and it changes creation-flag handling for callers that pass their own. Keep per-OS and document: leaves the reported disconnect. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A Windows Python rejects `close_fds=True` with redirected handles. | Supported since Python 3.7; the framework requires 3.11. |
| The fix cannot be exercised here. | AC-4 records the field confirmation as pending until the reporter confirms. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
