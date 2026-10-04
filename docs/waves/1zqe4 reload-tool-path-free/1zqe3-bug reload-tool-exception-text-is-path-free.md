# Reload Tool Exception Text Is Path-Free

Change ID: `1zqe3-bug reload-tool-exception-text-is-path-free`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-03
Wave: 1zqe4 reload-tool-path-free

## Rationale

Wave `1zoju` (change `1zodw-bug unhandled-tool-exception-text-is-path-free`) made every exception that escapes a served tool reach the client as a path-free `tool_unhandled_exception` envelope. It did that with one `render` pass, `_wrap_unhandled_tool_exceptions` in `wf_server/server_impl.py`, applied once at the end of `register_mcp_surface` through `_RENDER_PASS`. That pass skips coroutine functions, and the only coroutine tool is the runner tool `wf_reload_mcp`, defined inside `build_server` in `server.py` and registered after `register_mcp_surface` returns. The 1zodw Progress Log records this as an open follow-up.

The gap is real on the one tool most likely to fail on a broken tree. `perform_mcp_reload` calls `importlib.reload(server_impl)` outside any `try`, so a module that raises on re-execution (or any other uncaught exception in the reload body) escapes `wf_reload_mcp`. FastMCP's `Tool.run` then raises `ToolError(f"Error executing tool {self.name}: {e}")`, and the client receives the raw exception text. An `OSError` there names its absolute file path, which is exactly the leak 1zodw closed for every other tool.

The reload tool's handled diagnostics have the same leak in a smaller form. `_refresh_mcp_tool_surface` builds `tool_remove_warning` and `register_surface_failed` with `{exc}`, and `perform_mcp_reload` and the `wf_reload_mcp` body build `handler_close_warning`, `reload_failed`, `setup_readiness_unavailable` and `tool_list_changed_notification_failed` from the exception's text, and `perform_mcp_reload` forwards the reason string `_record_runner_identity` returns as `runner_identity_unrecorded`, which embeds `{type(exc).__name__}: {exc}`. These reach the same client through the same tool, so they are in scope. The same reload also runs inside `wf_upgrade`: `upgrade_handlers._reload_live_runner` calls `perform_mcp_reload`, forwards its handled diagnostics, and turns any exception it raises into `mcp_reload_skipped` with `f"In-process MCP reload skipped: {exc}"`, so the same `OSError` reaches the `wf_upgrade` client with its absolute path.

Brief: the consumer is an MCP client calling `wf_reload_mcp`, or `wf_upgrade` when it reloads in process; the outcome is that no exception-derived text in that tool's responses carries an absolute path, while the operator still gets the full text on stderr. Exclusions: argument-validation errors raised by FastMCP before the callable runs, the stderr-only startup messages, the `setup_readiness` object a successful reload returns (it legitimately names the root), and the `context_efficiency_projection_failed` refusal, whose `projection` payload can embed sqlite error text.

## Requirements

1. `_wrap_unhandled_tool_exceptions` renders coroutine callables too. For a coroutine function it installs an `async def` wrapper (built with `functools.wraps`, so `inspect.iscoroutinefunction` stays true and FastMCP's stored `is_async` stays correct) that awaits the original and, on `Exception`, returns `_unhandled_tool_exception_response(tool_name, exc, get_handler)`: the same envelope, the same `tool_unhandled_exception` code, the same path-free text and the same traceback to stderr through `_wf_log` as the synchronous wrapper.
2. The async wrapper catches `Exception` only. `asyncio.CancelledError`, `KeyboardInterrupt` and `SystemExit` (all `BaseException` but not `Exception` on Python 3.8 and later) propagate unchanged.
3. The async wrapper carries the existing `_wf_rendered` marker, so the pass never wraps an entry twice. A plain alias sharing a coroutine callable shares its one rendered wrapper, as for synchronous entries.
4. `build_server` in `server.py` applies the render pass once more after `wf_reload_mcp` is registered and normalized, before the prefix check, through the `server_impl` helper `_apply_render_pass(mcp, get_handler)`, which owns the `mcp_tool_registry.apply_middleware(mcp, get_handler, _RENDER_PASS)` call. The runner looks the helper up with `getattr(server_impl, "_apply_render_pass", None)` and skips the call when it is missing or not callable, so the runner never names the retired flat `mcp_tool_registry` module (delivery repair DEL-F1). This keeps the runner's launch-on-a-torn-tree, never-crash contract: a runner paired with an older `server_impl` that has no `_apply_render_pass` still starts, unrendered as today. The runner adds no new import. Every synchronous entry is already rendered and is skipped by the marker, so only `wf_reload_mcp` is wrapped there. On reload, `register_mcp_surface` keeps runner tools (`_strip_to_runner_tools`, `_RELOAD_SURVIVOR_TOOLS`), so the survivor keeps its one rendered wrapper and the reload's own render pass skips it by the marker. This covers startup and every reload.
5. `wf_reload_mcp` keeps every existing behaviour: its argument contract, its `context_efficiency_projection_failed` refusal shape, the `perform_mcp_reload` error envelopes (`handler_not_ready`, `reload_failed`), the deferred notification handoff and its `completed`/`failed`/`not_needed` dispatch values, its cancellation behaviour, its membership in `RUNNER_TOOLS` and `_RELOAD_SURVIVOR_TOOLS`, and the extension refusals that protect a runner tool (override, alias, hidden name, replacement, parameter mapping).
6. In `perform_mcp_reload`, `_refresh_mcp_tool_surface` and the `wf_reload_mcp` body, every diagnostic message built from an exception object's text uses path-free text instead: `path_free_exception_text(exc, root)` from `lifecycle_lock` (reached as `server_impl._lifecycle_lock_authority`), with `root` the runner's served root (`_root`, or `old.root` where that is in hand). The helper call is wrapped in `try`: on any exception (including the `TypeError` that `path_free_exception_text(exc, None)` raises while `_root` is still `None` before `build_server` has run) it falls back to `_lifecycle_lock_authority._cause_label(exc)`, or to `type(exc).__name__` when that is unavailable, so the handled and unhandled fallbacks match. The rule also covers exception text embedded in a reason string those functions forward into a diagnostic, which brings in `_record_runner_identity` (Requirement 9). The derived set today is `handler_close_warning`, `reload_failed`, `tool_remove_warning`, `register_surface_failed`, `setup_readiness_unavailable`, both `tool_list_changed_notification_failed` sites, `runner_identity_unrecorded`, and `mcp_reload_skipped` in `upgrade_handlers._reload_live_runner` (Requirement 10); the rule governs if the census finds more. Codes and the fixed text around the exception are unchanged, except that `reload_failed`, today bare `str(exc)`, now starts with the exception class (`ValueError: bad id`, or `PermissionError EACCES on docs/x.md` for an `OSError`, which has no colon) (Decision Log).
7. For each diagnostic in Requirement 6, the original exception text goes to stderr once, so the operator loses nothing.
8. The runner identity, tool-surface golden and handler digests are not edited by hand: `server.py` is a runner file, so a consuming host loads the runner part only after a restart (`runner_stale` reports it), and the published name, tier, input schema and annotations of `wf_reload_mcp` do not change.
9. `_record_runner_identity` in `server.py` keeps its never-raises contract and its `Optional[str]` return, but each reason it builds from a caught exception (the setup-identity assignment branch, the keyword-setter branch and the single-argument retry branch) uses `path_free_exception_text(exc, root)` over the served root (`_root`), inside the same `try` and with the same `_cause_label` then class-name fallback as Requirement 6 (so a `None` root before `build_server` cannot raise), in place of `{type(exc).__name__}: {exc}`. It writes the full original exception text to stderr itself, once per caught exception, so the detail the startup message carried today is not lost. Its callers are unchanged: census predicate "every call of `_record_runner_identity` in a non-test module under `.wavefoundry/framework/scripts/`" finds exactly two, `build_server` (prints the returned reason to stderr) and `perform_mcp_reload` (forwards it as `runner_identity_unrecorded`). The restart guidance for runner files covers this change too.
10. `upgrade_handlers._reload_live_runner` renders its caught exception for `mcp_reload_skipped` with the same helper and fallback, reached through the `server_impl` it already imports (`server_impl._lifecycle_lock_authority`), over the root `wf_upgrade_response` already holds, passed as a new optional `root` argument (`None` takes the fallback, so existing callers and tests that pass only `resp` keep working), and writes the original text to stderr. The prefix `In-process MCP reload skipped: ` and the code are unchanged. Because `wf_upgrade` forwards the handled reload diagnostics from `perform_mcp_reload`, the Requirement 6 path-free text reaches its client too.

## Scope

**Problem statement:** an exception escaping `wf_reload_mcp`, or one interpolated into its handled diagnostics, reaches the MCP client as raw text that can name an absolute path.

**In scope:**

- The coroutine branch of `_wrap_unhandled_tool_exceptions` and its docstring.
- Applying the render pass to `wf_reload_mcp` in `build_server`.
- Path-free text for the handled reload diagnostics in Requirement 6, with stderr logging of the original.
- The `_record_runner_identity` reason strings (Requirement 9).
- `mcp_reload_skipped` in `upgrade_handlers._reload_live_runner` (Requirement 10).
- Tests for each, updates to the pins that assert coroutines are skipped, the `docs/specs/mcp-tool-surface.md` paragraph on unhandled tool exceptions, and a CHANGELOG `Unreleased` entry.

**Out of scope:**

- Argument-validation errors raised by FastMCP before the callable runs (unchanged for every tool, as in 1zodw).
- Stderr-only messages such as the `--dry-run` failure line and `_adopt_setup_baseline`.
- The `setup_readiness` object of a successful reload, which legitimately names the root, and the `context_efficiency_projection_failed` refusal's `projection` payload, which can embed sqlite error text.
- Allowing extension handlers to be coroutines: `_install_extension_tools` still refuses them, so `wf_reload_mcp` stays the only coroutine served.

## Acceptance Criteria

- [x] AC-1: Calling the real `wf_reload_mcp` through FastMCP's `Tool.run` (from `build_server`) while `perform_mcp_reload` raises an `OSError` whose filename lies under the served root returns a `tool_unhandled_exception` error envelope with `data.tool == "wf_reload_mcp"`, a repository-relative filename and no form of the root in the serialized response, instead of raising `ToolError`; on HEAD the same call raises `ToolError` carrying the absolute path.
- [x] AC-2: A unit test of `_wrap_unhandled_tool_exceptions` over a table holding a coroutine shows the wrapper is a coroutine function carrying `_wf_rendered`, awaits to the same envelope and message as the synchronous wrapper for the same exception (path withheld, plain text kept, root-lookup failure falls back to class and errno), and logs the traceback to stderr.
- [x] AC-3: `asyncio.CancelledError`, `KeyboardInterrupt` and `SystemExit` raised inside a rendered coroutine propagate out of the wrapper, and the existing `test_cancellation_drops_awaited_send_but_not_scheduled_control` passes unchanged.
- [x] AC-4: After `build_server`, the served `wf_reload_mcp` carries `render` exactly once as the last `__wf_middleware__` label; after a real `perform_mcp_reload` it is the identical callable with the same single label, and a second application of the pass leaves every entry's callable unchanged.
- [x] AC-5: The existing reload tests in `WaveMcpReloadTests` (`test_server_tools.py`), the runner-tool extension refusals in `test_extension_tool_modules.py`, `test_skips_runner_async_and_index_health_tools_and_never_nests` and the tool-surface golden and handler-digest tests pass without regenerating either fixture.
- [x] AC-6: For each diagnostic in Requirement 6, a test that raises an exception naming an absolute path under the root (and one naming a path outside it) gets the same diagnostic code with no absolute path in its message, while the original text appears on stderr; the two notification-failure tests that assert the class name in the message still pass.
- [x] AC-7: With the impl setter or the setup-identity assignment raising an exception whose text names an absolute path under the root, `_record_runner_identity` returns a reason with no absolute path that still names the exception class, writes the original text to stderr, and never raises; `perform_mcp_reload` then reports that path-free reason as `runner_identity_unrecorded`; the existing runner identity tests (`test_non_typeerror_setter_failure_degrades_instead_of_raising` and its siblings) pass unchanged.
- [x] AC-8: The `docs/specs/mcp-tool-surface.md` unhandled-exception paragraph no longer says coroutine tools are not wrapped and names the reload tool's path-free handled diagnostics, and the CHANGELOG `Unreleased` section carries one entry for this change; both say that no exception-derived text in the reload tool's responses carries an absolute path, that the path-free reload diagnostics also reach `wf_upgrade`, and that a `reload_failed` message now starts with the exception class.
- [x] AC-9: The change's own test files and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.
- [x] AC-10: A test through `upgrade_handlers._reload_live_runner` with a live runner whose `perform_mcp_reload` raises an `OSError` naming a file under the root gets `mcp_reload_skipped` with the `In-process MCP reload skipped: ` prefix, a repository-relative filename and no absolute path, with the original text on stderr; on HEAD the message carries the absolute path.
- [x] AC-11: A runner paired with a `server_impl` that lacks `_apply_render_pass` still completes `build_server` and serves `wf_reload_mcp` (unrendered), with no exception from the extra pass.
- [x] AC-12: With the served root `None` (before `build_server` has run), the runner helper and `_record_runner_identity` return the `_cause_label` text (class and errno name) instead of raising, matching the unhandled envelope's fallback.

## Tasks

- [x] Failing-first: on HEAD, add the AC-1 reproducer and the AC-6 reproducers and record that they fail.
- [x] Add the coroutine branch to `_wrap_unhandled_tool_exceptions` (async wrapper, `_wf_rendered`, shared alias wrapper) and update its docstring and the `_RENDER_PASS` comment.
- [x] In `build_server`, apply the render pass after registering and normalizing `wf_reload_mcp`, before the prefix check, through the `server_impl._apply_render_pass` helper looked up with `getattr` (DEL-F1), with no new runner import; add the AC-11 test.
- [x] Add a runner helper that renders an exception path-free over the served root inside `try`, falling back to `_cause_label` then the class name, and writes the original text to stderr; use it at every site in Requirement 6; add the AC-12 test.
- [x] Render `mcp_reload_skipped` in `upgrade_handlers._reload_live_runner` per Requirement 10, pass `root` from `wf_upgrade_response`, and add the AC-10 test.
- [x] Change `_record_runner_identity` per Requirement 9 (path-free reasons, full text to stderr) and add the AC-7 tests, including one through `perform_mcp_reload`.
- [x] Re-run the census of `_record_runner_identity` callers and record it in the Progress Log.
- [x] Re-run the census of exception-text interpolations in `perform_mcp_reload`, `_refresh_mcp_tool_surface` and the `wf_reload_mcp` body (`limit=0`) and record the result in the Progress Log.
- [x] Update `test_coroutines_and_rendered_callables_are_skipped` (coroutines are now rendered, still once) and `test_the_render_pass_is_last_and_wraps_each_entry_once` (the runner tool now ends in `render`); leave the closed 1zodw change doc untouched.
- [x] Add the AC-2, AC-3 and AC-4 tests.
- [x] Update the spec paragraph and add the CHANGELOG entry: state that no exception-derived text in the reload tool's responses carries an absolute path, that the path-free reload diagnostics also reach `wf_upgrade` (which forwards the handled diagnostics), and that `reload_failed` messages now start with the exception class.
- [x] Run the touched test files and the golden and digest tests; run `wf_validate_docs`.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| reproducers | implementer | none | AC-1 and AC-6 failing on HEAD, in a scratch copy |
| render-pass | implementer | reproducers | `_wrap_unhandled_tool_exceptions` coroutine branch and `build_server` application |
| handled-diagnostics | implementer | reproducers | runner helper, the Requirement 6 sites and `_record_runner_identity` in `server.py`; `mcp_reload_skipped` in `upgrade_handlers.py` |
| tests-and-pins | implementer | render-pass, handled-diagnostics | AC-2 to AC-7 and AC-10 to AC-12 tests and the two updated pins |
| docs | implementer | tests-and-pins | spec paragraph and CHANGELOG |

## Serialization Points

- `.wavefoundry/framework/scripts/server.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_reload_runner.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`, `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
- `docs/specs/mcp-tool-surface.md`
- The CHANGELOG at the repository root is edited too.

## Affected Architecture Docs

N/A: the existing `render` pass gains a coroutine branch and is applied once more where the runner registers its survivor tool. No boundary, ownership or data flow moves; the tool surface spec carries the behaviour.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The defect itself, through the real client path |
| AC-2 | required | The async wrapper must render exactly as the synchronous one |
| AC-3 | required | Catching cancellation would break request cancellation |
| AC-4 | required | Coverage at startup and across every reload, with no double wrap |
| AC-5 | required | The reload tool's special behaviour and published surface must not change |
| AC-6 | required | The handled diagnostics carry the same leak on the same tool |
| AC-7 | required | The runner identity reason reaches the same client through `runner_identity_unrecorded` |
| AC-8 | important | The spec currently states the gap as behaviour |
| AC-9 | required | Change-scoped verification |
| AC-10 | required | The same reload exception reaches the `wf_upgrade` client through `mcp_reload_skipped` |
| AC-11 | required | The runner must keep launching on a torn tree |
| AC-12 | required | A `None` root must take the fallback rather than raise inside a never-raise path |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-04 | Delivery repair DEL-F1: `build_server` named the retired flat module in `getattr(server_impl, "mcp_tool_registry", None)`, which `test_server_package`'s retired-flat-name census refuses. `server_impl` now owns `_apply_render_pass(mcp, get_handler)`, which calls `mcp_tool_registry.apply_middleware(mcp, get_handler, _RENDER_PASS)` (the call shape `register_mcp_surface` already used; it now calls the helper too). `build_server` looks it up with `getattr(server_impl, "_apply_render_pass", None)` and calls it only when callable, so a torn tree without the helper still launches unrendered (AC-11). The AC-11 test now deletes `_apply_render_pass` instead of `_RENDER_PASS`, since the runner no longer reads the tuple; AC-11 and the build task still name `_RENDER_PASS` and `server_impl.mcp_tool_registry`, which the coordinator may reword. | `run_tests.py --file`: `test_server_package` 31, `test_extension_tool_modules` 214, `test_server_tools` 385, `test_upgrade_reload_runner` 8, all OK. Mutation in a scratch copy (`apply_render_pass(...)` replaced by `pass` in `build_server`) is killed by `test_extension_tool_modules`: `test_the_reload_tool_keeps_its_one_render_across_a_reload`, `test_the_reload_tool_renders_an_exception_path_free`, `test_the_render_pass_is_last_and_wraps_each_entry_once` (AC-1, AC-4). |
| 2026-10-04 | Implemented. `_wrap_unhandled_tool_exceptions` gains an `async` wrapper for coroutine functions (same envelope, `_wf_rendered`, shared alias wrapper, `Exception` only); `build_server` re-applies `_RENDER_PASS` through `server_impl.mcp_tool_registry` after normalizing `wf_reload_mcp`, guarded by `getattr`, with no new import; a new runner helper `_reload_exception_text(exc, context, root=None)` renders path-free over `root` or `_root`, falls back to `_cause_label` then the class name (a `None` root goes straight to `_cause_label`), writes the original text to stderr and never raises; used at all eight Requirement 6 sites and the three `_record_runner_identity` reason branches. `upgrade_handlers._reload_live_runner(resp, root=None)` renders `mcp_reload_skipped` the same way and `wf_upgrade_response` passes `root`. Spec paragraph and CHANGELOG entry updated. Census of `_record_runner_identity` callers (predicate: every call in a non-test module under `.wavefoundry/framework/scripts/`, `code_keyword` `limit=0`): exactly two, `build_server` and `perform_mcp_reload` in `server.py`. Census of exception-text interpolations (`{exc}`, `str(exc)`, `limit=0`) in `perform_mcp_reload`, `_refresh_mcp_tool_surface` and the `wf_reload_mcp` body: none remain; the remaining `server.py` hits are the helper's own stderr line and startup or `--dry-run` stderr messages (out of scope); in `upgrade_handlers.py` the `mcp_reload_skipped` stderr line plus `spawn_failed` and two `status_error` sites outside the reload. Gapfill: one shell `grep` over `server.py` for `exc!r`, `repr(exc`, `{e}` and the function line ranges, because `code_keyword` returns no enclosing function and its full result exceeded the response limit; it found nothing more | Failing first (unfixed tree, new tests only): 31 failures and 3 errors across `UnhandledToolExceptionRenderTests`, `UnhandledToolExceptionUnitTests`, `ReloadDiagnosticsPathFreeTests` and `test_upgrade_reload_runner`; AC-1 on HEAD: `{'escaped': 'ToolError'}`; AC-6 on HEAD: `Removing tool 'wf_close_gate' during reload raised: [Errno 13] Permission denied: '/private/var/.../docs/x.md'`; AC-11 passes on HEAD by design (it pins the torn-tree launch). After the fix the same 32 tests pass. `run_tests.py --file` on `test_server_tools.py` (385), `test_extension_tool_modules.py` (214), `test_upgrade_reload_runner.py` (8), `test_setup_readiness_integration.py` (17), `test_tool_surface_golden.py` (13), `test_mcp_tool_registry.py` (27): all ok, no fixture regenerated; and `test_server_tools_lifecycle.py` (612), `test_handler_modules.py` (13), `test_startup_install.py` (61), `test_lifecycle_gates_structure.py` (10), `test_path_containment.py` (23), `test_review_operator_integration.py` (7): all ok. Both runs ended with the repository-change guard naming `test_sqlite_storage_migration.py` and `test_setup_reconciliation.py`, files the parallel `1zrag` implementer was editing, not this change |
| 2026-10-03 | Planned from the 1zodw follow-up. Verified against `c805b3c0`: `wf_reload_mcp` is `async def` in `build_server` (`server.py`), registered after `register_mcp_surface`, kept on reload by `_RELOAD_SURVIVOR_TOOLS` and `_strip_to_runner_tools`; `_wrap_unhandled_tool_exceptions` skips `inspect.iscoroutinefunction`; FastMCP 1.x `Tool.run` turns an escaping exception into `ToolError(f"Error executing tool {name}: {e}")` and computes `is_async` and the argument model at registration; extension handlers must be synchronous (`_install_extension_tools` refuses async ones); the tool-surface golden serializes name, tier, input schema and annotations only, and handler digests cover only `register_mcp_surface` handlers in `server_impl.py` | Read of `server.py` (`_refresh_mcp_tool_surface`, `perform_mcp_reload`, `build_server`), `server_impl.py` (`_unhandled_tool_exception_response`, `_wrap_unhandled_tool_exceptions`, `register_mcp_surface`), `mcp_tool_registry.apply_middleware`, `tests/test_tool_surface_golden.py`, `tests/test_mcp_tool_registry._handler_digests`, and the installed `mcp/server/fastmcp/tools/base.py`. Not executed: the golden and digest claims are `inferred` until AC-5 runs. Census of `_record_runner_identity` callers (predicate: every call in a non-test module under `.wavefoundry/framework/scripts/`, exhaustive): `build_server` and `perform_mcp_reload` in `server.py`; tests call it directly in `test_server_tools.py` and assert only the class name and fixed text |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-03 | Extend `_wrap_unhandled_tool_exceptions` with a coroutine branch and have `build_server` re-apply `_RENDER_PASS` after registering `wf_reload_mcp` | One pass and one marker serve both kinds, the wrapper stays in `server_impl` where every other tool rebinding lives, and the marker makes the extra application a no-op for synchronous entries and for the survivor on reload. As a side effect, a host still running the old runner gets the reload tool rendered by its first reload of the new `server_impl` | (a) A separate runner-only async wrapper in `server.py`: duplicates the envelope logic outside the module that owns it and drifts from it. (b) A `try`/`except` inside the `wf_reload_mcp` body: covers only the body, not a wrapper around it, and re-implements the envelope. (c) Leave the pass as is and wrap at reload time only: misses failures on the first call before any reload |
| 2026-10-03 | Operator decision: keep the default class prefix of `path_free_exception_text` for every handled reload diagnostic, including `reload_failed` | Consistency with the unhandled envelope and the other reload diagnostics; the two notification-failure tests already expect the class name. Wording change: a `reload_failed` message changes from the bare exception text (for example `bad id`) to text that starts with the exception class (`ValueError: bad id`; for an `OSError`, `PermissionError EACCES on docs/x.md` with no colon), or the class alone when the text names a path; the CHANGELOG entry says so | Keep `prefix_class=False` for `reload_failed` only, to preserve its old shape |
| 2026-10-03 | Operator decision: include `runner_identity_unrecorded` by changing `_record_runner_identity`'s contract to return path-free reasons and write the full text to stderr itself | The reason string reaches the client through `perform_mcp_reload`, so leaving it would keep one leak on the same tool; both callers take the string as is, so the contract change stays inside the helper | Leave it out of scope; or render path-free at the `perform_mcp_reload` call site, which cannot recover the exception from an already composed string |
| 2026-10-03 | Operator decision: keep the rule-based handled-diagnostic set rather than only `register_surface_failed` and `tool_remove_warning` | Every listed code reaches the same client on the same tool, and a rule keeps a later added site covered | Narrow to the two named codes |
| 2026-10-03 | F1, operator decision: include `mcp_reload_skipped` from `upgrade_handlers._reload_live_runner`, with the root passed in as a new optional argument | `wf_upgrade` runs the same `perform_mcp_reload`, so the same `OSError` reached its client with an absolute path; `wf_upgrade_response` already holds the root and `server_impl` is already imported there | Leave `wf_upgrade` out of scope; or read the root from the live runner's `_root` |
| 2026-10-03 | F2: guard the extra render pass with `getattr(server_impl, "_RENDER_PASS", None)`, reach the registry as `server_impl.mcp_tool_registry`, and add no runner import | The runner must launch on a torn tree and never crash; an older `server_impl` without `_RENDER_PASS` must still start | Import `mcp_tool_registry` in the runner and reference `_RENDER_PASS` directly |
| 2026-10-03 | F3: wrap every path-free helper call in `try` and fall back to `_cause_label(exc)`, then `type(exc).__name__` | `path_free_exception_text(exc, None)` raises `TypeError`, and `_root` is `None` before `build_server`; the unhandled envelope already falls back to `_cause_label`, so both fallbacks now match | Fall back to the class name only |
| 2026-10-03 | F4: narrow the Brief and spec wording to exception-derived text; the successful reload's `setup_readiness` and the `context_efficiency_projection_failed` payload are out of scope | `setup_readiness` names the root by design, and the projection payload's sqlite text is a separate surface | Promise that no response of the tool carries an absolute path |
| 2026-10-03 | F5: describe `reload_failed` as starting with the exception class, not as gaining a `Class: ` prefix | For an `OSError` the helper returns `Class ERRNO on rel` with no colon | Keep the `Class: ` wording |
| 2026-10-03 | F6: wave record filled (Objective, Wave Summary, Coordinator, Write-owning roles, Watchpoints) | Readiness approval requested the wave record be completed | None |

## Risks

| Risk | Mitigation |
| --- | --- |
| The async wrapper swallows cancellation | Catch `Exception` only; AC-3 pins `CancelledError`, and the existing cancellation test stays unchanged |
| `importlib.reload` raises partway, leaving `server_impl` partly re-executed when the wrapper renders | The wrapper looks up `_unhandled_tool_exception_response` in the module dict at call time, and a failed reload leaves the prior bindings in that dict; AC-1 raises from the reload path itself |
| Replacing `fn` after registration changes the published schema | FastMCP builds the argument model and `is_async` at registration and `functools.wraps` keeps the signature; AC-5 runs the golden without regeneration |
| `server.py` is a runner file, so a consuming host needs a restart to load the `build_server` part | Expected and reported by `runner_stale`; until restart, the first reload of the new `server_impl` renders the survivor through the coroutine branch |
| A runner paired with an older `server_impl` (torn tree) crashes on the extra pass | Guarded by `getattr`; AC-11 pins it |
| Windows, macOS, Linux and WSL2 differ | The path-free helper already handles POSIX, drive-letter and backslash paths; asyncio cancellation and `functools.wraps` behave the same on every platform under Python 3.11 or newer; no filesystem or process behaviour changes |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
