# Decision: reach the serving runner through _live_runner, never `import server`

Owner: Engineering
Status: active
Last verified: 2026-09-25

Memory ID: `1z2sf-mem decision-reach-the-serving-runner-through-live-runner-never-`
Kind: `decision`
Confidence: 0.9
Created: 2026-09-25
Updated: 2026-09-25
Source event: `decision-log:1yxnc-bug post-upgrade-reload-imports-second-runner:225762d571e55f6c`
Validation: promote
Validated by: agent
Action delta: To reach the serving MCP runner from handler code, never `import server` (in production server.py is `__main__`, so the import runs it a second time with no handler); use `upgrade_handlers._live_runner`, which accepts a loaded `server` or `__main__` module only when `vars()` shows a callable `perform_mcp_reload` and a built `_mcp`.
Validation rationale: Verified in the 1yxnc Decision Log and the delivered code: `_live_runner` and `_reload_live_runner` in wf_server/upgrade_handlers.py; the production-shape subprocess test fails with handler_not_ready and a second server module when `import server` is restored. The drafted target server.py is where the hazard lives, not where the decision is implemented, so targets are rewritten.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Decision (wave 1z1vt): in production `server.py` runs as `__main__`, so `import server` from handler code executes it a second time as a module with no handler and its `perform_mcp_reload` reports handler_not_ready. `wf_server/upgrade_handlers._live_runner` finds the serving runner without importing: it checks `sys.modules["server"]` then `sys.modules["__main__"]` and accepts a module only when `vars()` (bypassing the runner's `__getattr__` re-export of server_impl) shows a callable `perform_mcp_reload` and a non-None `_mcp`, which only `build_server` sets. No runner means an `mcp_reload_skipped` diagnostic naming `wf_reload_mcp`.

## Evidence

- `1yxnc-bug post-upgrade-reload-imports-second-runner`
- `1z1vt`

## Targets

- `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_reload_runner.py`
