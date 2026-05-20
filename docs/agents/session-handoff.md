# Session Handoff

Owner: wave-coordinator
Status: active
Last verified: 2026-05-19

## Last Closed Wave

**Wave:** `12rbc mcp-impl-hot-reload` — closed 2026-05-20  
**Shipped:** `server.py` thin runner + `server_impl.py` split; `wave_mcp_reload` tool; in-process upgrade hook; version fields (`framework_version`, `server_runner_version`, `server_impl_version`, `impl_matches_disk`) on `wave_server_info` and `wave_mcp_reload`; dashboard browser suppression; 1482 tests green; package `2026-05-19h`.

## Planned (not active)

**Wave:** `12rnv agent-prompt-harness` — changes `12rbe` (security reviewer seeds) + `12rnv` (harness core and specialists) + `12rcp` (prompt preflight rubric). Review docs, then **Prepare wave**.

## Open Questions / Deferred Decisions

- `close_warnings` path in `perform_mcp_reload` (when `ImplHandler.close()` raises) is not tested — advisory only; add test if close-error reporting becomes load-bearing.
- `wave_mcp_reload` does not add new tools to a live session (accepted limitation — requires client reconnect); revisit if FastMCP gains live tool-registration support.
