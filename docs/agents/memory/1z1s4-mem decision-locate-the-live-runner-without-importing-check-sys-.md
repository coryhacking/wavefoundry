# Decision: Locate the live runner without importing: check `sys.module…

Owner: Engineering
Status: superseded
Last verified: 2026-09-25

Memory ID: `1z1s4-mem decision-locate-the-live-runner-without-importing-check-sys-`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-25
Updated: 2026-09-25
Source event: `decision-log:1yxnc-bug post-upgrade-reload-imports-second-runner:225762d571e55f6c`
Validation: rewrite
Validated by: agent
Action delta: To reach the serving MCP runner from handler code, never `import server` (in production server.py is `__main__`, so the import runs it a second time with no handler); use `upgrade_handlers._live_runner`, which accepts a loaded `server` or `__main__` module only when `vars()` shows a callable `perform_mcp_reload` and a built `_mcp`.
Validation rationale: Verified in the 1yxnc Decision Log and the delivered code: `_live_runner` and `_reload_live_runner` in wf_server/upgrade_handlers.py; the production-shape subprocess test fails with handler_not_ready and a second server module when `import server` is restored. The drafted target server.py is where the hazard lives, not where the decision is implemented, so targets are rewritten.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1z2sf-mem decision-reach-the-serving-runner-through-live-runner-never-`

## Summary

Decision (wave 1z1vt): Locate the live runner without importing: check `sys.modules["server"]` then `sys.modules["__main__"]`, and accept a module only when its own namespace (read with `vars()`, bypassing the runner's `__getattr__` re-export) defines `perform_mcp_reload` and holds a built `_mcp`. Rationale: `_mcp` is set only by `build_server` in the process that serves; `vars()` avoids the module-level forwarding to `server_impl`; no import means `server.py` never runs twice.

## Evidence

- `1yxnc-bug post-upgrade-reload-imports-second-runner`
- `1z1vt`

## Targets

- `server.py`
