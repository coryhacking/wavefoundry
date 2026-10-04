# Unhandled Tool Exception Text Is Path-Free

Change ID: `1zodw-bug unhandled-tool-exception-text-is-path-free`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-03
Wave: 1zoju session-follow-ups

## Rationale

Red-team finding R3 from wave `1zls7` (change `1zlts`, recorded there as out of scope): an exception raised inside a tool body that no handler catches reaches the MCP client as raw exception text, and that text can carry absolute filesystem paths (an `OSError` names its file; a `RuntimeLockBusy` carries the absolute lock path in its message).

The path is verified against the installed SDK (`mcp` 1.28.1 in the tool venv): `Tool.run` in `mcp/server/fastmcp/tools/base.py` catches every `Exception` from the tool callable and re-raises `ToolError(f"Error executing tool {self.name}: {e}")`, and the low-level `call_tool` handler in `mcp/server/lowlevel/server.py` turns any exception into `_make_error_result(str(e))`, a `CallToolResult` with `isError=True` whose only content is that text. Nothing in the Wavefoundry chain intercepts it: `_wrap_lifecycle_mutation_lock` lets every non-lock body exception propagate by design (its docstring and `test_non_lock_body_exception_propagates_and_releases` pin that), and `_configured_phase_envelope` only adds `configured_gates` to a returned response; it catches nothing.

The rendering helpers already exist. Wave `1zls7` change `1zodv` added `lifecycle_lock.path_free_exception_text(exc, root, prefix_class=True)`, which renders an `OSError` as its class and errno name plus a repository-relative `filename` when the file lies under the root, and any other exception as `Class: text` only when `path_free_text` finds neither the root nor any absolute path in the text, else the class name alone. They are used today only at handled sites (`server_impl` around the lifecycle lock status, `memory_handlers` purge and consolidate, `context_efficiency_handlers`). This change applies them once, centrally, to the unhandled case, so the client keeps the diagnostic value (class, errno, relative filename) without the path, and the operator keeps the full traceback on stderr.

## Requirements

1. A new registration-time wrapper pass renders an `Exception` raised by a served tool's callable as a standard error envelope (`_response("error", ...)`, which sets `isError: True`) instead of letting it reach FastMCP. The envelope's `data` carries `{"tool": <served canonical name>}` and one diagnostic `tool_unhandled_exception` whose message is `lifecycle_lock.path_free_exception_text(exc, root)`.
2. The pass is structurally OUTERMOST. `MIDDLEWARE` and `_CORE_BEHAVIOUR_MIDDLEWARE` stay unchanged. Instead, one `("render", ...)` pass is applied through `mcp_tool_registry.apply_middleware` as the final step of `register_mcp_surface`, after `_install_served_names`, inside the same fail-closed `try` block, over the whole served table. Each wrapped callable carries an idempotence marker (`_wf_rendered`), so each served entry is wrapped exactly once. The pass therefore wraps everything served: core tools, extension tools, overrides, replacements and their `alias_for_core`, plain aliases, and mapped aliases, whose translator (`_mapped_alias_tool`'s `translated`) wraps `canonical_tool.fn` from outside the main chain. An exception raised by any inner wrapper (cost, lock, guard, setup notice, hint rewrite, omitted-parameter refusal, alias translation) is rendered too.
3. Only `Exception` is caught. `BaseException` subclasses that are not `Exception` (`KeyboardInterrupt`, `SystemExit`, `asyncio.CancelledError`) propagate unchanged.
4. The root comes from `get_handler().root`. When that lookup itself raises, the message falls back to the exception class name plus the errno name when the exception has one (the `_cause_label` shape), so no text of either exception is echoed.
5. Before returning, the pass writes the full traceback to stderr through `_wf_log` (the stdio transport owns stdout), so local diagnosis is unchanged.
6. Coroutine functions are skipped, as `_wrap_setup_notice` already skips them, so the runner-registered async tools (`RUNNER_TOOLS`, today only `wf_reload_mcp`) are untouched.
7. Argument-validation errors raised by FastMCP before the callable runs are out of this pass's reach and stay as they are; they echo caller input, not server paths.
8. Platform behaviour: `path_free_text` already recognises POSIX absolute paths, Windows drive paths (`C:\`, `C:/`) and backslash-led UNC-style paths, and `_root_forms` compares the root in raw, resolved, JSON-escaped and slash-swapped forms, so a Windows path in a native or JSON-escaped message is withheld exactly as a POSIX one is. Behaviour is identical on Windows, macOS, Linux and WSL2; on WSL2 a `/mnt/c/...` path is a POSIX path and is withheld.

## Scope

**Problem statement:** an unhandled tool exception's text, possibly holding an absolute path, is sent to the client verbatim.

**In scope:**

- A render pass in `wf_server/server_impl.py`, placed per Requirement 2, reusing `lifecycle_lock.path_free_exception_text`.
- Updating the `__wf_middleware__` label pins, each of which gains the final `render` label: in `tests/test_extension_tool_modules.py`, the comparisons of `stock + ["rewrite"]` (for example for `wf_close_wave` and for each alias), the literal `["cost", "lock", "guard", "setup", "rewrite"]`, and `["cost"] + stock + ["omitted"]`. Because the stock markers also end in `render`, each pin is restated as the stock chain without `render`, then the added label, then `render`. The tuples pinned in `tests/test_mcp_tool_registry.py` `test_marker_records_the_wrappers_that_applied` (`("cost", "lock", "guard", "setup")` and `("lock", "guard", "setup")`) come from a full `register_mcp_surface` build, so each gains a final `render`.
- A note in `docs/specs/mcp-tool-surface.md` naming the diagnostic, and a CHANGELOG bullet.

**Out of scope:**

- Handled exception text that handlers already put into diagnostics with `str(exc)` or `{exc}`: 128 such renderings exist across `wf_server/*.py` (predicate: `str(exc)` or `{exc}` in those files, tests excluded), 48 of them on the same line as a `_diagnostic(` call (predicate: `_diagnostic\(.*(\{exc\}|str\(exc\))` over `wf_server/*.py`, re-derived 2026-10-03). Each is a deliberate handler choice; sweeping them is a separate change.
- MCP resource handlers (`wavefoundry://` reads) and the async runner tool `wf_reload_mcp`.
- The dashboard HTTP server, which is not served through FastMCP.

## Acceptance Criteria

- [x] AC-1: Reproducer, failing first: a served tool whose callable raises `OSError(errno.EACCES, "Permission denied", str(root / "docs" / "x.md"))` returns a response with `status == "error"`, `isError is True`, and a `tool_unhandled_exception` diagnostic reading `PermissionError EACCES on docs/x.md`; no part of the serialized response contains the absolute root. The same call fails before the change (the exception escapes the wrapper).
- [x] AC-2: An exception whose message names an absolute path outside the root (for example a `RuntimeError("cannot open /tmp/elsewhere/lock")`, and a Windows form `RuntimeError("cannot open C:\\elsewhere\\lock")`) renders as the class name alone; a message with no path (`ValueError("bad id")`) renders as `ValueError: bad id`.
- [x] AC-3: Placement: after a full server build with a declaration that adds an alias, a mapped alias, an override and a replacement, every served synchronous tool's `__wf_middleware__` ends with the `render` label and no callable is wrapped twice. An exception raised by an extension tool, by the plain alias, by the replaced core's `alias_for_core`, and inside a mapped alias's translator path (`_rewrite_served_names`, `copy.deepcopy(fixed)`, `_rename_response_keys`, each made to raise in turn) is rendered. Each case is asserted through the served table, not by calling the pass directly.
- [x] AC-4: An exception raised by an inner wrapper is rendered, proving the pass is outermost: the test makes the upgrade-publication guard raise and asserts the envelope. (The cost wrapper cannot serve as the example: it swallows its own recording errors by design.)
- [x] AC-5: `KeyboardInterrupt` raised by a body propagates out of the served callable unchanged.
- [x] AC-6: When `get_handler()` raises, the envelope carries the class (and errno name where present) only, asserted with a message that contains an absolute path.
- [x] AC-7: The full traceback, including the original message, is written to stderr (captured with `contextlib.redirect_stderr` or a patched `_wf_log`).
- [x] AC-8: `wf_reload_mcp` (coroutine) carries no render label; existing lock-wrapper propagation tests (`test_non_lock_body_exception_propagates_and_releases`, `test_body_lock_refusals_that_are_not_reentry_propagate`) still pass unchanged, because they exercise the lock wrapper alone.
- [x] AC-9: The change's own test files and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Write the AC-1 reproducer against the served table and confirm it fails on the current tree.
- [x] Implement the render pass and apply it as the final step of `register_mcp_surface`, after `_install_served_names` (Requirement 2).
- [x] Update the middleware label pins in `tests/test_mcp_tool_registry.py` and any label expectation in `tests/test_extension_tool_modules.py`.
- [x] Add the AC-2 through AC-8 tests.
- [x] Document the diagnostic in `docs/specs/mcp-tool-surface.md`; add the CHANGELOG bullet.
- [x] Run the full suite in a scratch copy and docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| reproducer | implementer | none | AC-1, failing first |
| render-pass | implementer | reproducer | Requirements 1-6 |
| placement-tests | implementer | render-pass | AC-3 to AC-8 |
| docs | implementer | render-pass | spec note and CHANGELOG |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/lifecycle_lock.py`
- `.wavefoundry/framework/scripts/tests/test_mcp_tool_registry.py`, `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`, `.wavefoundry/framework/scripts/tests/test_lifecycle_mutation_lock.py`
- `docs/specs/mcp-tool-surface.md`
- The CHANGELOG at the repository root is edited too.

## Affected Architecture Docs

N/A: one wrapper pass is added to the existing registration-time middleware chain; no boundary, ownership or data flow moves. The tool surface spec gains the diagnostic name.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The defect itself, failing first |
| AC-2 | required | The non-OSError branch is where most crash text lands |
| AC-3 | required | A pass that misses extension tools or aliases leaves the leak open |
| AC-4 | important | Proves the outermost placement |
| AC-5 | required | Catching interrupts would change server shutdown behaviour |
| AC-6 | important | The fallback must not echo the second exception |
| AC-7 | required | Operators lose the traceback otherwise |
| AC-8 | important | Guards the async runner tool and the existing lock contract |
| AC-9 | required | Suite and lint gate |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-03 | Delivery repair F3 to F5: AC-4 reworded to name the upgrade-publication guard and state that the cost wrapper swallows its own recording errors by design (Decision Log row added; still `[x]`); the spec note now says a plain alias shares the canonical's rendered callable, so `data.tool` names the canonical tool, while a mapped alias names itself; spec and CHANGELOG say a crash is now a normal result whose JSON envelope carries `isError: true`, so the protocol-level `isError` reads false, as for every other error envelope. Follow-up: `wf_reload_mcp`, the only coroutine tool, is not rendered; it needs an async render variant | Documentation only; no code or test changed for this change in the repair. Full suite `--no-cache` in a fresh scratch copy, plus `--profile second` and `--profile declared`: 10,930 tests across 157 files OK (34 skipped); second 10,927 OK; declared 10,930 OK. The first repaired run failed only `test_label_reader_census` (its allowlist entry for the old `wf_current_wave` message became stale and was removed) |
| 2026-10-03 | Implemented: `_wrap_unhandled_tool_exceptions` (`render`, `_wf_rendered` marker, coroutines skipped, `Exception` only) applied through `apply_middleware` as the last step of `register_mcp_surface` after `_install_served_names`; `_unhandled_tool_exception_response` renders `path_free_exception_text` over `get_handler().root`, falls back to `_cause_label` and logs the traceback through `_wf_log`. A plain alias that serves its canonical callable keeps sharing one rendered wrapper, so `data.tool` there is the canonical name. Pins updated: the marker tuples in `test_mcp_tool_registry`, the label lists in `test_extension_tool_modules` (stock chain without `render`, then the added label, then `render`), the mapped-alias `__wrapped__` identity pins (now one level deeper), the keyless-response set in `test_lifecycle_gates`, and `test_omitted_purpose_is_rejected_before_the_tool_body_runs` (a direct call now gets the envelope); spec note and CHANGELOG updated | Tests: `test_extension_tool_modules.UnhandledToolExceptionRenderTests` (AC-1 through FastMCP's client path and the table, AC-3, AC-4, AC-5, AC-8) and `UnhandledToolExceptionUnitTests` (AC-2, AC-5, AC-6, AC-7, AC-8). AC-4 deviation: the cost wrapper swallows its own recording errors (`except Exception: pass`), so the inner-wrapper case raises from the upgrade-publication guard instead. Failing-first on HEAD: AC-1 escaped as `ToolError`, every case escaped, no tool carried `render`. Mutations M34 to M40 all killed. full suite `run_tests.py --no-cache` in a scratch copy: 10,925 tests, 157 files, OK; `--profile second` and `--profile declared` OK (second 10,922 tests, declared 10,925; the final run, after every code change; 34 tests skipped in the full run). Gapfill: retrieval used grep and sed over the scripts tree instead of the MCP code tools, because the edits needed exact multi-line anchors in a 25,000-line module and the attached MCP server runs the pre-change code |
| 2026-10-03 | Planned from `1zls7` red-team R3 | FastMCP error path read in the tool venv's `mcp` 1.28.1 |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-03 | Delivery repair F3: AC-4 names the upgrade-publication guard as the inner wrapper whose exception the test renders | The cost wrapper catches every exception from its own recording (`except Exception: pass`), so it can never raise past the body; the guard calls `publication_block_reason` outside any handler, so it does | Keep the cost-wrapper wording (rejected: false); make the cost wrapper re-raise (rejected: recording is observational by design) |
| 2026-10-03 | Render centrally as a registration-time wrapper pass | One place covers every served callable, including extension tools, overrides and replacements, through the chain that already wraps them | Patch each handler (rejected: hundreds of bodies, and every new tool would need it); subclass FastMCP's `Tool.run` or `call_tool` (rejected: couples to private SDK internals that changed across `mcp` releases, and the 1z822 pin `mcp[cli]<2` would still let it move) |
| 2026-10-03 | Recheck N4: the `test_mcp_tool_registry.py` marker pins gain `render` unconditionally, and the pass wraps each served entry exactly once | Those pins come from a full `register_mcp_surface` build | Leave the pins conditional (rejected: they do change) |
| 2026-10-03 | Readiness amendment F1: apply the render pass once, as the final step of `register_mcp_surface` after `_install_served_names`, over the whole served table with an idempotence marker; `MIDDLEWARE` and `_CORE_BEHAVIOUR_MIDDLEWARE` stay unchanged | The first draft put `render` last in both tuples, which left the install-time `rewrite` and `omitted` passes and the mapped-alias translator outside it, contradicting the outermost claim. This was the strongest alternative, and it is now adopted | Last entry of each tuple plus re-application after the appended passes (rejected: misses `_mapped_alias_tool`'s `translated`, and every future appended pass would need remembering) |
| 2026-10-03 | Return a standard error envelope rather than raise a sanitized `ToolError` | The client gets the same envelope shape as every handled error, with a stable diagnostic code it can branch on | Re-raise `ToolError(path_free_text)` (rejected: still unstructured text, and FastMCP prefixes it) |
| 2026-10-03 | Reuse `path_free_exception_text` unchanged | It was built for this (1zodv) and already handles OSError errno labels, repo-relative filenames and Windows path forms | A new renderer (rejected: a second definition of "path-free") |
| 2026-10-03 | Catch `Exception` only | Interrupts and cancellation must keep their control-flow meaning | Catch `BaseException` (rejected) |
| 2026-10-03 | Leave handled `str(exc)` renderings out of scope | Each is a handler decision with its own message contract; a sweep is a separate, larger change | Fold the sweep in (rejected: size) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A test or caller relies on an exception escaping a served tool | Census `assertRaises` around served-table calls during implementation; the existing propagation tests target single wrappers and are unaffected (AC-8) |
| Withholding text hides a useful message | The full traceback goes to stderr (AC-7); a path-free message is kept verbatim |
| The pass misses a chain appended later | The pass runs last over the whole served table (Requirement 2); AC-3 asserts the label on every served synchronous tool after a full build with every declaration kind |
| Platform behaviour | Pure string and identity work; identical on Windows, macOS, Linux and WSL2 (Requirement 8) |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
