# MCP Implementation Hot Reload

Change ID: `12rb9-enh mcp-impl-hot-reload`
Change Status: `admitted`
Owner: wave-coordinator
Status: admitted
Last verified: 2026-05-19
Wave: `12rbc mcp-impl-hot-reload`

## Implementation status

**Implemented.** Full suite green (1479 tests). Split complete, all ACs shipped. See Progress Log.

## Rationale

The MCP server (`server.py`) is a monolithic ~10K-line file. When the framework upgrades ship changes to tool logic, the operator must fully restart the MCP server and reconnect the client to pick up the new implementation. This is disruptive and makes the `wave_upgrade` flow feel incomplete — the upgrade script finishes but the running server still executes old code until a manual restart.

The fix is to split `server.py` into a thin runner that owns the stdio transport and fixed tool registrations, and a separate `server_impl.py` that contains all business logic. The runner can `importlib.reload(server_impl)` to swap in new implementation without closing the MCP connection. A `wave_mcp_reload` tool performs the reload and returns version fields so operators can confirm the running impl matches disk; `wave_upgrade` cleanup triggers the same in-process reload path.

## Requirements

1. `server.py` remains the sole entry point (`python3 server.py --root .`) — no changes to `.mcp.json` or operator launch commands.
2. All business logic (tool handler implementations, `WaveIndex`, `McpRepoCache`, response functions, constants) lives in `server_impl.py` and is imported by `server.py`.
3. `server.py` registers all `@mcp.tool()` stubs with the existing signatures. Each stub calls through to a reloadable dispatch layer in `server_impl`.
4. A `wave_mcp_reload` MCP tool reloads `server_impl` via `importlib.reload`, closes the old index/cache state, and instantiates fresh state from the new module code. It returns structured version fields (see requirement 9).
5. After `wave_upgrade(phase="cleanup")` completes successfully, the **in-process** server path invokes hot reload (same semantics as `wave_mcp_reload`). `upgrade_wavefoundry.py` updates the operator summary to reflect reload instead of "restart MCP server" — it does **not** spawn an MCP client (the cleanup subprocess is not attached to the live stdio server).
6. On reload, clear `_script_cache` (see `server.py` `_load_script`) so dynamically loaded sibling scripts do not stay stale.
7. New tools added in an upgrade are not visible to an existing client session until reconnect — this is an accepted limitation; `wave_mcp_reload` handles logic/index changes only.
8. All existing tests continue to pass; `server.py` still exports `build_server`, `main`, and **re-exports** implementation symbols tests import today (`WaveIndex`, `*_response` helpers, etc.) — either via explicit imports from `server_impl` or a compatibility shim.
9. **Dual module versions** — queryable over MCP to confirm an upgrade was applied to the **running** process:
   - `server.py` defines `SERVER_RUNNER_VERSION` (thin-runner protocol; bump only when transport/stub wiring changes; **not** updated by hot reload).
   - `server_impl.py` sets `SERVER_IMPL_VERSION` at module load from `.wavefoundry/framework/VERSION` beside the scripts tree (refreshed on each successful `importlib.reload`).
   - `wave_server_info` includes in `data`: `framework_version` (VERSION on disk at target `root`), `server_runner_version`, `server_impl_version` (loaded in memory), and `impl_matches_disk` (`true` when impl version equals disk VERSION, else `false`; `null` when either side is unreadable).
   - `wave_mcp_reload` returns the same version fields on success so operators and agents can verify reload without a separate call:

```json
{
  "status": "ok",
  "data": {
    "ok": true,
    "framework_version": "<disk VERSION at root>",
    "server_runner_version": "<SERVER_RUNNER_VERSION>",
    "server_impl_version": "<SERVER_IMPL_VERSION after reload>",
    "impl_matches_disk": true
  }
}
```

   On failure, return `status: "error"` with diagnostics; do not claim `impl_matches_disk: true` unless reload completed and versions were read.
10. **`wave_help` discoverability** — tool name is `wave_mcp_reload` (not `wave_hot_reload`). Update `_help_catalog()` in `server_impl.py` (or `server.py` until split):
    - Add `wave_mcp_reload` to `core_tools` (near `wave_server_info` / upgrade tools).
    - Add workflow goal `reload_mcp` with `recommended_chain`: `["wave_mcp_reload", "wave_server_info"]`, rationale for post-upgrade verification, `usage`: `wave_mcp_reload()`.
    - `wave_help(goal="reload_mcp")` returns that workflow; `wave_help()` catalogue lists the tool in `core_tools`.

## Scope

**Problem statement:** Upgrading the framework requires a full MCP server restart to pick up new tool logic, breaking the otherwise-automated `wave_upgrade` flow.

**In scope:**

- Split `server.py` into `server.py` (thin runner, ~300 lines) and `server_impl.py` (fat impl, ~10K lines)
- `server_impl.py` exposes `build_handler(root) -> ImplHandler` where `ImplHandler` provides `call(tool_name, args)` and `close()`
- `server.py` tool stubs delegate to a module-level `_handler` that is replaceable at runtime
- `wave_mcp_reload` tool implementation in `server.py` (mutating annotations; version payload on success)
- `SERVER_RUNNER_VERSION` / `SERVER_IMPL_VERSION` constants and `server_identity()` version fields for `wave_server_info`
- `wave_upgrade_response` invokes in-process reload after successful `cleanup` subprocess; `upgrade_wavefoundry.py` operator summary text updated (no MCP client from subprocess)
- `test_server_tools.py` updated to assert `wave_mcp_reload` in the registered-tool list and version fields in responses
- `_help_catalog()`: `core_tools` + `reload_mcp` workflow for `wave_help` discoverability

**Out of scope:**

- Hot-adding new tools to a live session (requires client reconnect; not addressable without FastMCP changes)
- Hot-reloading `server.py` itself (the thin runner never changes during an upgrade)
- Changes to the MCP transport or `.mcp.json`

## Acceptance Criteria

- AC-1: `python3 server.py --root .` launches and behaves identically to today; `.mcp.json` unchanged.
- AC-2: `wave_mcp_reload` returns `ok: true` plus `framework_version`, `server_runner_version`, `server_impl_version`, and `impl_matches_disk`; the next tool call executes code from the freshly loaded `server_impl.py`.
- AC-3: After `wave_upgrade(phase="cleanup")` succeeds, the in-process server invokes hot reload (same as `wave_mcp_reload`); `wave_server_info` then shows `impl_matches_disk: true` when the upgraded pack is loaded (no manual MCP restart).
- AC-4: All existing `test_server_tools.py` and `test_upgrade_wavefoundry.py` tests pass.
- AC-5: `wave_mcp_reload` is present in the registered-tool assertion in `test_server_tools.py`.
- AC-6: Old `WaveIndex`/`McpRepoCache` resources are closed before the new ones are instantiated (no LanceDB double-open).
- AC-7: `wave_server_info` returns `framework_version`, `server_runner_version`, `server_impl_version`, and `impl_matches_disk` in `data` alongside existing identity fields.
- AC-8: `wave_help()` includes `wave_mcp_reload` in `core_tools`; `wave_help(goal="reload_mcp")` returns a workflow whose `recommended_chain` starts with `wave_mcp_reload`.

## Tasks

- Read `server.py` `build_server` section (lines 8928–10302) to map which closures capture `index`, `cache`, `root` — these are the state the `ImplHandler` must own
- Extract all code above `build_server` into `server_impl.py`; expose `build_handler(root) -> ImplHandler`
- Rewrite `server.py` as thin runner: imports `server_impl`, registers stubs, dispatches via `_handler`
- Add `SERVER_RUNNER_VERSION` (`server.py`) and `SERVER_IMPL_VERSION` (`server_impl.py`, from pack `VERSION` at import/reload); extend `server_identity()` for `wave_server_info`
- Implement `wave_mcp_reload` in `server.py` (`_MUTATING_TOOL`; reload lock; clear `_script_cache`; return version payload per requirement 9)
- Wire `wave_upgrade_response` to invoke in-process reload after successful `cleanup` subprocess; update `upgrade_wavefoundry.py` operator summary only
- Add `wave_mcp_reload` to registered-tool assertion in `test_server_tools.py`
- Update `_help_catalog()`: `core_tools` + `reload_mcp` workflow; test `wave_help` lists tool and goal resolves
- Test `wave_mcp_reload` response includes version fields and `impl_matches_disk` after reload; test `wave_server_info` version fields
- Add behavioral tests: post-reload smoke tool call uses reloaded module; reload with open index does not LanceDB double-open (AC-6); optional `wave_upgrade` cleanup → reload integration test
- Implement `ImplHandler.close()` (WaveIndex Lance teardown, cache invalidate, reranker/background download cleanup as needed)
- Clear `_script_cache` inside `wave_mcp_reload` before `importlib.reload(server_impl)`
- Re-export test-facing symbols from `server.py` per requirement 8
- Run full test suite; fix any import path breakage

## Agent Execution Graph

| Workstream          | Owner            | Depends On    | Notes |
| ------------------- | ---------------- | ------------- | ----- |
| server split        | wave-coordinator | —             | Extract impl, rewrite thin runner |
| wave_mcp_reload     | wave-coordinator | server split  | Tool impl + close/reload logic |
| upgrade integration | wave-coordinator | wave_mcp_reload | in-process reload from `wave_upgrade_response`; summary text in upgrade script |
| test updates        | wave-coordinator | server split  | registered-tool assertion + any broken imports |

## Serialization Points

- `server_impl.py` must exist and export `build_handler` before `server.py` stub rewrites can be tested
- Version helpers (`_read_framework_pack_version`, `_read_framework_version_at_root`) must exist before `wave_mcp_reload` / `wave_server_info` version ACs

## Affected Architecture Docs

N/A — change is confined to the framework scripts layer (`server.py` → `server.py` + `server_impl.py`). No boundary, data-flow, or verification architecture changes; the MCP surface is identical post-split.

## AC Priority

| AC   | Priority     | Rationale |
| ---- | ------------ | --------- |
| AC-1 | required     | Compatibility gate — entry point and launch must be unchanged |
| AC-2 | required     | Core deliverable — hot reload must actually work |
| AC-3 | required     | Integration with upgrade flow is the stated motivation |
| AC-4 | required     | No regressions |
| AC-5 | required     | Registered-tool assertion is the standard verification pattern |
| AC-6 | required     | Resource leak / LanceDB double-open would cause runtime failures |
| AC-7 | required     | Operators/agents need MCP-visible proof that upgrade + reload applied |
| AC-8 | required     | Reload tool must be discoverable via `wave_help` without reading change docs |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-19 | Change doc created from design discussion in wave 12r09 close session. | conversation |
| 2026-05-19 | Prepare wave — admitted, AC priority confirmed, wave active. | `wave_prepare` create |
| 2026-05-18 | Pre-implementation council — approved-with-notes; AC-3 path, `_script_cache`, behavioral tests | wave council code-grounded pass |
| 2026-05-19 | Dual versions via `wave_mcp_reload` + `wave_server_info` | Operator verifies upgrade without restart; runner vs impl distinguishes hot-reload scope | Single `version` string only (rejected: ambiguous after split) |
| 2026-05-19 | Plan-only until Implement wave | Operator requested no early framework edits | Partial server.py / test landing (reverted) |
| 2026-05-19 | Rename tool to `wave_mcp_reload`; require `wave_help` entry | Clearer name; discoverability via `reload_mcp` goal | `wave_hot_reload` (rejected: ambiguous with index “hot” paths) |
| 2026-05-20 | Implement wave: `_split_mcp_server.py` → `server.py` thin runner + `server_impl.py`; `wave_mcp_reload` tool; `ImplHandler`; upgrade hook; version fields; `wave_help` discoverability | AC-1–AC-8 complete | — |
| 2026-05-20 | Dashboard browser suppression: `WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER=1` in test env; `dashboard_browser_open_enabled()`; `--open` and `webbrowser.open` gated | Prevented ~5 browser windows per test run | — |
| 2026-05-20 | Fix test patch namespace: `load_server()` returns `server_impl` so patches reach internal call sites; `load_thin_runner()` for runner-specific tests | 1479/1479 green; 35 split-related failures resolved | — |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-19 | Keep entry point as `server.py`, impl in `server_impl.py` | Preserves `.mcp.json` compatibility and all existing launch paths | `server_runner.py` + `server_impl.py` (rejected: breaks entry point) |
| 2026-05-19 | Hot reload covers impl changes only; new tools require reconnect | FastMCP caches `tools/list` at client init; adding tools to a live session is not supported without FastMCP changes | Full restart (rejected: defeats the purpose); FastMCP patch (out of scope) |
| 2026-05-18 | AC-3 reload runs in `wave_upgrade_response`, not MCP client from upgrade script | `upgrade_wavefoundry.py` runs as subprocess; only the live server can reload itself | Subprocess MCP client (rejected: no stdio attachment) |
| 2026-05-18 | Clear `_script_cache` on reload | `_load_script` caches indexer/chunker modules outside `server_impl` | Reload impl only (rejected: stale sibling modules) |
| 2026-05-19 | Version fields on `wave_mcp_reload` and `wave_server_info` | Primary upgrade verification path; reload response avoids extra round-trip | Disk-only VERSION in upgrade log (rejected: does not prove in-memory reload) |
| 2026-05-19 | Tool name `wave_mcp_reload` | MCP-scoped reload; distinct from index rebuild / dashboard restart | `wave_hot_reload` (rejected per operator) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Tool handler closures capture `index`/`cache` directly — naive reload won't swap them | `ImplHandler.call()` must be the sole dispatch path; stubs must not close over impl state directly |
| `importlib.reload` on a module with circular imports or side-effectful top-level code can fail silently | Audit `server_impl.py` top-level for side effects before enabling reload; add a smoke-call after reload to verify |
| LanceDB does not support concurrent opens on the same table | `ImplHandler.close()` must complete before `build_handler` is called; reload is synchronous within the tool handler |
| `_script_cache` survives `importlib.reload(server_impl)` | Clear cache at start of `wave_mcp_reload` | |
| Reload fails mid-flight | Keep previous `_handler` until reload succeeds; return structured error | |
| Tests import symbols from `server` module | Re-export from `server.py` after split | |
| `impl_matches_disk` false after upgrade | Operator calls `wave_mcp_reload` or completes `wave_upgrade` cleanup path; check `wave_mcp_reload` return payload | |
| Reload mid-request | Serialize reload on a module lock inside `wave_mcp_reload` | |
| Background model download during reload | `ImplHandler.close()` stops or waits for in-flight downloads | |
| Partial reload failure | Keep previous `_handler`; return error without `impl_matches_disk: true` | |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
