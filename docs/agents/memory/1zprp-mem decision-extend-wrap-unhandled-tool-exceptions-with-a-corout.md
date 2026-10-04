# Decision: Extend `_wrap_unhandled_tool_exceptions` with a coroutine b…

Owner: Engineering
Status: superseded
Last verified: 2026-10-04

Memory ID: `1zprp-mem decision-extend-wrap-unhandled-tool-exceptions-with-a-corout`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-04
Updated: 2026-10-04
Source exploration cost: 470529
Source event: `decision-log:1zqe3-bug reload-tool-exception-text-is-path-free:5f2d4fb2a2c92a15`
Validation: rewrite
Validated by: agent
Action delta: When adding or changing a served tool, rely on the single render pass (sync and async) and reach it from the runner only through server_impl._apply_render_pass looked up with getattr.
Validation rationale: Generated candidate targeted server.py only and described the pre-repair shape (runner re-applying _RENDER_PASS through server_impl.mcp_tool_registry), which DEL-F1 replaced. Current tree: _wrap_unhandled_tool_exceptions has an async branch, and build_server calls server_impl._apply_render_pass via getattr.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1zqbl-mem unhandled-tool-exceptions-render-path-free-for-sync-and-asyn`

## Summary

Decision (wave 1zqe4): Extend `_wrap_unhandled_tool_exceptions` with a coroutine branch and have `build_server` re-apply `_RENDER_PASS` after registering `wf_reload_mcp`. Rationale: One pass and one marker serve both kinds, the wrapper stays in `server_impl` where every other tool rebinding lives, and the marker makes the extra application a no-op for synchronous entries and for the survivor on reload. As a side effect, a host still running the old runner gets the reload tool rendered by its first reload of the new `server_impl`.

## Evidence

- `1zqe3-bug reload-tool-exception-text-is-path-free`
- `1zqe4`

## Targets

- `server.py`
