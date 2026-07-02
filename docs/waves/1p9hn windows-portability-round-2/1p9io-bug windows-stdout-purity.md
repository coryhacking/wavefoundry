# Windows stdout purity: in-process print() corrupts MCP JSON-RPC channel

Change ID: `1p9io-bug windows-stdout-purity`
Change Status: `implemented`
Owner: implementer
Status: implemented
Last verified: 2026-07-02
Wave: 1p9hn windows-portability-round-2

## Rationale

`server.py:_isolate_native_stdout_from_protocol` makes `sys.stdout` the private fd the MCP stdio transport writes JSON-RPC frames through. Any `print()` call in the in-process call set reachable from a tool handler injects raw text into the frame, corrupting or hanging the call. The prior stdio-hardening waves (1p8vc/1p88t) isolated native fd-1 writes (onnxruntime/DirectML) and MCP-helper subprocess stdout — but never scanned the in-process call set for plain Python `print()`.

Three unguarded sites were identified (severity HIGH/MEDIUM):

- `indexer.py:2763` — "finished graph" summary sits **after** the `if verbose:` block (ends 2760), so `verbose=False` does not suppress it. Fired unconditionally by the graph auto-rebuild path.
- `indexer.py:3210` — "rebuilding {label} index" gated only by `if full:`, not verbose. Same trigger path.
- `indexer.py:850` — oversized-file skip notice; unconditional; fired from `walk_repo` which runs in-process from every `code_*` navigation tool and `wave_index_health`/`wave_audit`.
- `graph_indexer.py:1811/1813` — missing tree-sitter grammar warning; no `file=sys.stderr`, no verbose gate; de-duped per language but fires on first encounter.

The graph auto-rebuild trigger (`graph_query.py:220`) runs `build_index(full=True, verbose=False)` **in-process** (via `importlib.exec_module`) on the first graph query after any builder-version bump — i.e. guaranteed once per upgrade. The native-Windows MCP host is least tolerant of a corrupted first-call frame.

No guard currently exists for Python-level stdout purity across the in-process call set. An AST-level guard analogous to `FrameworkWideSubprocessIsolationGuard` is the durable fix.

## Requirements

1. `indexer.py:2763` print must be gated behind `if verbose:` or redirected to `file=sys.stderr`.
2. `indexer.py:3210` print must be gated behind `if verbose:` or redirected to `file=sys.stderr`.
3. `indexer.py:850` print must be redirected to `file=sys.stderr` (it is shared between in-process server calls and build-subprocess callers, so it must never assume stdout is safe).
4. `graph_indexer.py:1811` and `:1813` prints must be redirected to `file=sys.stderr`.
5. The in-process `build_index` call at `graph_query.py:220` must be wrapped in `contextlib.redirect_stdout(sys.stderr)` combined with `cli_stdio.isolated_stdout_fd()` as defense-in-depth (catches any further undetected prints inside the rebuild path).
6. A framework-wide print-purity guard must AST-scan the transitive in-process call set reachable from registered MCP tool handlers for `print()` calls lacking `file=sys.stderr` (or an explicit isolation wrapper), analogous to `FrameworkWideSubprocessIsolationGuard`. The guard must fail the test suite if a new unguarded `print()` is added on a server-reachable path.
7. A targeted regression test must run the stale-version auto-rebuild path against a captured `sys.stdout` and assert zero bytes reach it.

## Scope

**Problem statement:** In-process Python `print()` calls on code paths reachable from MCP tool handlers write to `sys.stdout`, which is the JSON-RPC protocol channel on the MCP server, corrupting or hanging tool calls on Windows (and any host using stdio transport).

**In scope:**

- Fix the four identified print sites (3 in `indexer.py`, 1 in `graph_indexer.py`)
- Add `redirect_stdout` + `isolated_stdout_fd` defense-in-depth at `graph_query.py:220`
- Add an AST-based print-purity guard covering the server-reachable in-process call set
- Add a regression test for the graph auto-rebuild stdout-capture path

**Out of scope:**

- Subprocess stdout isolation (already covered by prior waves and `subprocess_util`)
- Native fd-1 isolation from C extensions (already covered by `isolated_stdout_fd` at startup)
- Fixing `print()` calls in scripts that are only invoked as subprocesses (safe; they have their own stdout)

## Acceptance Criteria

- [x] AC-1: `indexer.py:2763` print is gated behind `if verbose:` or routes to `file=sys.stderr` — routed to `file=sys.stderr`
- [x] AC-2: `indexer.py:3210` print is gated behind `if verbose:` or routes to `file=sys.stderr` — routed to `file=sys.stderr` (both the `full` and `else` branches, same statement, for consistency)
- [x] AC-3: `indexer.py:850` print routes to `file=sys.stderr` — done (walk_repo oversized-file skip)
- [x] AC-4: `graph_indexer.py:1811` and `:1813` prints route to `file=sys.stderr` — done (both grammar-unavailable branches)
- [x] AC-5: `graph_query.py:220` `build_index` call is wrapped in `redirect_stdout(sys.stderr)` + `isolated_stdout_fd()` — done via `with cli_stdio.isolated_stdout_fd(), contextlib.redirect_stdout(sys.stderr):`
- [x] AC-6: A print-purity AST guard exists in the test suite and fails on any new unguarded `print()` reachable from a tool handler — `FrameworkInProcessStdoutPurityGuard` in `test_server_tools.py` (Check 1: in-process `build_index` call sites must be wrapped; Check 2: `walk_repo` prints must carry `file=`). Scoped to the two real in-process boundaries; all other index builds are subprocesses.
- [x] AC-7: A regression test confirms zero bytes reach `sys.stdout` during the stale-graph-version auto-rebuild path — `test_auto_rebuild_writes_no_bytes_to_stdout` in `test_graph_query.py` (noisy fake `build_index` prints to stdout; captured stdout asserted empty)

## Tasks

- [x] Fix `indexer.py:2763` — add `if verbose:` guard or `file=sys.stderr`
- [x] Fix `indexer.py:3210` — add `if verbose:` guard or `file=sys.stderr`
- [x] Fix `indexer.py:850` — add `file=sys.stderr` to the oversized-file skip print
- [x] Fix `graph_indexer.py:1811/1813` — add `file=sys.stderr` to grammar-unavailable prints
- [x] Wrap `graph_query.py:220` call in `redirect_stdout(sys.stderr)` + `isolated_stdout_fd()` (added `import contextlib`, `import cli_stdio`)
- [x] Implement print-purity AST guard in test suite (`FrameworkInProcessStdoutPurityGuard`)
- [x] Add regression test for graph auto-rebuild stdout isolation (`test_auto_rebuild_writes_no_bytes_to_stdout`)

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| fix-print-sites | implementer | — | indexer.py + graph_indexer.py print fixes |
| fix-graph-query-wrapper | implementer | — | graph_query.py defense-in-depth wrapper |
| add-purity-guard | implementer | fix-print-sites | AST guard must pass after fixes are applied |
| add-regression-test | implementer | fix-graph-query-wrapper | stdout-capture test |

## Serialization Points

- The AST guard (workstream `add-purity-guard`) must be written after the print-site fixes are applied, so it passes from day one.

## Affected Architecture Docs

N/A — the change is confined to individual function bodies in `indexer.py`, `graph_indexer.py`, and `graph_query.py`, with a new test guard. No boundary, flow, or verification architecture changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Directly fixes the high-severity auto-rebuild corruption |
| AC-2 | required | Directly fixes the high-severity auto-rebuild corruption |
| AC-3 | required | Directly fixes medium-severity navigation/health corruption |
| AC-4 | required | Directly fixes medium-severity missing-grammar corruption |
| AC-5 | required | Defense-in-depth for the same trigger path |
| AC-6 | required | Durable guard so the class cannot regress |
| AC-7 | required | Regression test for the guaranteed-once-per-upgrade trigger |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-02 | Change doc created from 10-dimension Windows audit | audit workflow wf_51bd40fe-082 |
| 2026-07-02 | Implemented: 4 print sites routed to stderr, graph_query.py:223 wrapped in isolated_stdout_fd+redirect_stdout, AST guard + regression test added | 4 targeted tests pass (`FrameworkInProcessStdoutPurityGuard` x2, `test_auto_rebuild_writes_no_bytes_to_stdout`, `test_callback_fires_after_successful_auto_rebuild`) |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-02 | Route prints to `file=sys.stderr` rather than fully removing them | Progress output is still useful during CLI invocations; stderr is safe in both server and CLI contexts | Remove prints entirely (loses progress visibility in CLI mode) |
| 2026-07-02 | Add defense-in-depth wrapper at `graph_query.py:220` even after fixing print sites | Future undetected prints in the rebuild path will be caught at the boundary | Rely solely on fixing known sites |

## Risks

| Risk | Mitigation |
| --- | --- |
| Additional undetected `print()` sites exist on server-reachable paths | The AST guard (AC-6) catches any missed sites and prevents regression |
| `contextlib.redirect_stdout` is not reentrant-safe if called concurrently | `_ensure_graph_builder_current` already holds `_VERSION_REBUILD_INFLIGHT_LOCK`; only one thread does the rebuild; safe |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
