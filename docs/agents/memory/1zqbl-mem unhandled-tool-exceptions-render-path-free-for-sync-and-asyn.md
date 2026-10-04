# Unhandled tool exceptions render path-free for sync and async tools through one pass

Owner: Engineering
Status: active
Last verified: 2026-10-04

Memory ID: `1zqbl-mem unhandled-tool-exceptions-render-path-free-for-sync-and-asyn`
Kind: `decision`
Confidence: 0.9
Created: 2026-10-04
Updated: 2026-10-04
Source exploration cost: 470529
Source event: `decision-log:1zqe3-bug reload-tool-exception-text-is-path-free:5f2d4fb2a2c92a15`
Validation: promote
Validated by: agent
Action delta: When adding or changing a served tool, rely on the single render pass (sync and async) and reach it from the runner only through server_impl._apply_render_pass looked up with getattr.
Validation rationale: Generated candidate targeted server.py only and described the pre-repair shape (runner re-applying _RENDER_PASS through server_impl.mcp_tool_registry), which DEL-F1 replaced. Current tree: _wrap_unhandled_tool_exceptions has an async branch, and build_server calls server_impl._apply_render_pass via getattr.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Decision (wave 1zqe4, 1zqe3): _wrap_unhandled_tool_exceptions in wf_server/server_impl.py wraps synchronous and coroutine tool callables (an async def wrapper catching Exception only, so CancelledError, KeyboardInterrupt and SystemExit propagate), marked _wf_rendered so a second application is a no-op. server.py build_server re-applies the pass after registering wf_reload_mcp by calling server_impl._apply_render_pass looked up with getattr, skipping when absent so a runner paired with an older server_impl still starts. Reload diagnostics go through path-free rendering with the original text on stderr only.

## Evidence

- `1zqe3-bug reload-tool-exception-text-is-path-free`
- `1zqe4`
- `DEL-F1`

## Targets

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/server.py`
