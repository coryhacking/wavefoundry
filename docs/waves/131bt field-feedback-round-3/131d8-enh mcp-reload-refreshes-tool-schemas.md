# `wave_mcp_reload` Re-Registers Tool Schemas to Eliminate FastMCP Wrapper-Signature Cache

Change ID: `131d8-enh mcp-reload-refreshes-tool-schemas`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 131bt field-feedback-round-3

## Rationale

Every parameter or description change to an MCP tool currently requires a full server restart to be visible to clients. The existing `wave_mcp_reload` reloads `server_impl` so response-shape changes work in-process, but it does NOT re-run `register_mcp_surface()` — FastMCP's tool registry retains the schemas it captured at startup via `@mcp.tool` introspection.

This recurring friction has now manifested three times in wave 131bt alone:

- `1312h` carryover: adding `collapse_class_module_pairs` to `wave_graph_report` required a full restart in wave 13129.
- `1319m`: adding `collapse_package_to_directory` to `wave_graph_report` required a restart this wave.
- `131ar`: tool description string updates (`wave_index_build`, `wave_index_health`, `code_impact`, `code_callhierarchy`, `code_graph_community`, `wave_graph_report`) all require a full restart even though they're pure description-string changes.

Every future wave that touches an MCP tool's signature or description string will hit the same restart ceremony. The constraint isn't load-bearing for any contract — FastMCP exposes public `add_tool` / `remove_tool` / `list_tools` methods. The problem is that `wave_mcp_reload` doesn't use them.

Operator value: a single `wave_mcp_reload` call (or the existing `wave_upgrade` flow that already invokes it) becomes the complete refresh story. No restart instruction in changelog entries; no journal watchpoints about FastMCP wrapper-signature cache.

## Approach

Extend `perform_mcp_reload()` in `server.py` to refresh the FastMCP tool registry alongside the existing `server_impl` module reload:

1. **Snapshot current tool names** via `mcp.list_tools()` (or `_registered_mcp_tool_names()` already in `server_impl`) before reload.
2. **Reload `server_impl`** (existing behavior preserved).
3. **Remove all first-party tools** via `mcp.remove_tool(name)` for each snapshot entry whose name starts with the first-party prefix (already enforced via `first_party_tool_names_violating_prefix`).
4. **Re-register tools** by calling `server_impl.register_mcp_surface(mcp, _get_handler)` with the reloaded module. FastMCP re-introspects each function and stores fresh schemas.
5. **Notify clients** via the MCP protocol's `notifications/tools/list_changed` so connected clients re-fetch the tool list. FastMCP exposes this through its session manager; if the notification isn't auto-sent on `add_tool`, call the underlying primitive explicitly.

The existing `_reload_lock` serializes concurrent reload calls; in-flight tool calls during the swap are an acceptable risk for the framework-owner-driven reload (the lock prevents two reloads from interleaving, and tool calls hold their function reference for the duration of execution, so a remove during execution doesn't crash the in-flight call).

The `wave_mcp_reload` response surface stays the same: the existing `payload["ok"] = True` and version fields remain. Add a `tools_reregistered: int` field reporting the count of tools refreshed.

## Requirements

1. `perform_mcp_reload()` in `server.py` tears down and re-registers the first-party FastMCP tool set after reloading `server_impl`.
2. The MCP protocol's `notifications/tools/list_changed` is sent to connected clients (or verified to be auto-sent by FastMCP after `add_tool`/`remove_tool`).
3. The `wave_mcp_reload` response includes `tools_reregistered: int`.
4. Existing tests (`test_server_tools.py`) pass without modification — the response builders and tool surface stay binary-compatible.
5. A new test confirms that adding a parameter to a tool function definition + calling `perform_mcp_reload()` produces a tool with the new signature in `mcp.list_tools()`.
6. seed-160 (upgrade) and seed-240 (packaging) language about "MCP server restart required for description-string changes" is removed or updated — the restart is no longer required.
7. The wave 131bt journal watchpoint about "MCP server restart required for description changes" is updated to reflect that `wave_mcp_reload` now covers signature changes.

## Scope

**Problem statement:** Every MCP tool parameter or description change requires a full server restart because `wave_mcp_reload` doesn't refresh FastMCP's introspected schemas. Operators see this as a restart ceremony for every MCP-surface evolution.

**In scope:**

- `.wavefoundry/framework/scripts/server.py` — `perform_mcp_reload()` extension to tear down + re-register tools.
- `.wavefoundry/framework/scripts/server_impl.py` — `register_mcp_surface()` if any changes needed to support re-registration (idempotency check).
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` (or new test file) — re-registration test using a temporary tool definition.
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` and `240-package-wavefoundry.prompt.md` — language updates removing the restart-required caveat.

**Out of scope:**

- A general-purpose hot-reload framework for other long-running services. This change addresses the MCP wrapper-signature cache only.
- Live notification propagation if FastMCP doesn't expose the primitive. If `notifications/tools/list_changed` can't be sent without internals access, document the workaround (operator calls `/mcp` after `wave_mcp_reload`).
- Replacing the `@mcp.tool` decorator-introspection model with explicit JSON schemas. The decorator pattern stays.
- In-flight tool execution preservation across the reload. Acceptable to let in-flight calls complete normally; tearing down the registry only affects future calls.

## Acceptance Criteria

- [x] AC-1: `perform_mcp_reload()` reloads `server_impl` AND re-registers the FastMCP tool set with fresh signatures.
- [x] AC-2: After `perform_mcp_reload()`, `mcp.list_tools()` reflects the current source-file function signatures (including any parameters added since startup).
- [x] AC-3: After `perform_mcp_reload()`, calling a tool with a newly-added parameter (one that didn't exist at server startup) does NOT raise `NameError` or `unknown parameter`.
- [x] AC-4: `wave_mcp_reload` response includes `tools_reregistered: int` ≥ 1.
- [x] AC-5: `notifications/tools/list_changed` is sent to connected clients after the re-registration (or, if FastMCP doesn't expose the primitive directly, documented as a known gap with the `/mcp` workaround).
- [x] AC-6: Existing 851 `test_server_tools.py` tests pass without modification.
- [x] AC-7: New test: simulate adding a parameter to a tool function definition, call `perform_mcp_reload()`, verify the new parameter appears in `mcp.list_tools()` output.
- [x] AC-8: seed-160 and seed-240 updated to remove "MCP server restart required for description-string changes" language.
- [x] AC-9: Wave 131bt journal watchpoint about FastMCP wrapper-signature cache is updated.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Extend `perform_mcp_reload()` in `server.py` with tear-down + re-register loop
- [x] Investigate FastMCP `notifications/tools/list_changed` propagation; wire if accessible
- [x] Add `tools_reregistered` to the response payload
- [x] Add regression test for parameter-addition hot-reload
- [x] Run framework tests
- [x] Open `seed_edit_allowed` gate; update seed-160 and seed-240 language; close gate
- [x] Update wave 131bt journal watchpoint
- [x] Close framework gate; mark change `implemented`

## Affected Architecture Docs

- N/A — this change strengthens an existing operator-facing mechanism (`wave_mcp_reload`); no architectural boundary or data flow change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Core re-registration |
| AC-2 | required | Schema-refresh observability |
| AC-3 | required | Operator-facing outcome (new params usable without restart) |
| AC-4 | important | Diagnostic surface |
| AC-5 | required | Client-side refresh propagation |
| AC-6 | required | No regression on existing tool surface |
| AC-7 | required | Parameter-addition test pin |
| AC-8 | required | Documentation alignment |
| AC-9 | required | Journal watchpoint resolution |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Extend `wave_mcp_reload` rather than replace the decorator-introspection model with explicit JSON schemas | Lowest-disruption fix — preserves the `@mcp.tool` decorator ergonomics while resolving the root cause. FastMCP already exposes `add_tool`/`remove_tool` as public API; we just need to call them | Replace decorators with explicit schemas (rejected — large refactor, loses type safety); document + automate process restart (rejected — papers over root cause, restart still required) |
| 2026-06-01 | Re-register all first-party tools rather than tracking per-tool dirty state | Simplest correct implementation; full re-register is fast (sub-millisecond per tool) and avoids dirty-tracking bookkeeping | Track which tools changed since last reload (rejected — premature optimization; benchmarking suggests no real cost) |
| 2026-06-01 | Accept in-flight calls without preservation | The `_reload_lock` serializes reloads; in-flight tool calls hold their function reference for the call duration and complete normally. Only NEW calls after reload see the refreshed registry | Drain-then-reload (rejected — adds complexity for no operator-visible benefit) |

## Risks

| Risk | Mitigation |
|---|---|
| FastMCP `notifications/tools/list_changed` doesn't have a public API path | Document as a known gap with `/mcp` workaround in seed-160; AC-5 explicitly allows this fallback |
| In-flight tool call during reload causes inconsistent behavior | `_reload_lock` already serializes concurrent reload calls. Tool execution holds the function reference until return; removing a tool from the registry doesn't affect an in-flight call. Document if a specific edge case emerges |
| Re-registering tools introduces a duplicate-registration error if `add_tool` rejects existing names | Tear-down step (`remove_tool`) precedes re-registration; ensures clean slate. Per `_registered_mcp_tool_names`, the prefix contract guarantees first-party tools are identifiable |
| Existing 851 server_tools tests assume the decorator-registration happens once at startup and might fail on re-registration | AC-6 requires they pass without modification. If any fail, investigate whether the test is testing initialization assumptions vs runtime contract |
| FastMCP version drift breaks `add_tool` / `remove_tool` surface | Pin the FastMCP version in pyproject.toml / requirements; document the dependency |

## Related Work

- Resolves the FastMCP wrapper-signature cache limitation flagged in wave 13129, wave 130rj's `exclude_external` rollout, and wave 131bt's own `1319m` rollout.
- Pairs with `131ar` (MCP tool description sync) — `131ar` updated description strings; this change makes future description updates land via `wave_mcp_reload` instead of restart.
- Pairs with `1319m` (directory aggregation) — `1319m`'s `collapse_package_to_directory` parameter was the most recent restart-required addition. After this change, future parameters land without restart.
- Direct extension of the existing `wave_mcp_reload` infrastructure shipped in earlier waves.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
