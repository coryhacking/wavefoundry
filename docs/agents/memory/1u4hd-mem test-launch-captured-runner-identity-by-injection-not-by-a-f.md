# Test launch-captured runner identity by injection, not by a fresh-subprocess probe

Owner: Engineering
Status: active
Last verified: 2026-07-31

Memory ID: `1u4hd-mem test-launch-captured-runner-identity-by-injection-not-by-a-f`
Kind: `decision`
Confidence: 0.8
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 777948
Source event: `decision-log:1u2ay-bug server-runner-version-never-distinguishes-stale-runner:3c87c60838c7e12b`
Validation: promote
Validated by: agent
Action delta: To test launch-captured runner state, inject a compute_runner_identity pair over temp copies of the real runner files (RunnerIdentityTests in tests/test_server_tools.py) instead of spawning an MCP subprocess probe; reserve fresh-process probes for changes to which TOOLS the runner registers.
Validation rationale: The decision is durable but the draft states it as one-time AC bookkeeping ("AC-1 test shape") with a truncated title and a bare `server.py` basename target, so it would never surface to someone editing the test module that actually holds the technique. Verified in the current tree: server.py:51-70 computes SERVER_RUNNER_FILES and SERVER_RUNNER_VERSION once at import, and tests/test_server_tools.py:9086-9191 (RunnerIdentityTests) exercises the seam by calling server_impl.compute_runner_identity over temp copies and mutating them. Evidence chain followed in the 1u2b0 ledger. Rewritten to name the reusable mechanism (a launch-captured value cannot be re-captured in-process, so inject the pair) and its boundary against the existing reload-survivor record 1t38p-mem, which requires a fresh-process probe for tool-registration changes.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

server.py captures the pair (SERVER_RUNNER_VERSION, SERVER_RUNNER_FILES) exactly once at process launch, so no in-process test can re-run the capture. The comparison wf_server_info reports is precisely that captured pair against a query-time re-read of the same paths, so tests reproduce it by computing a captured identity with server_impl.compute_runner_identity over temp copies of the real runner files, injecting it, then mutating a copy. That covers both stale directions and both runner members (server.py and venv_bootstrap.py) deterministically with no MCP-subprocess flake. Boundary: injection is correct for launch-captured VALUES only. A change to which TOOLS the runner registers still requires a fresh-process tools/list probe, because reload survivors keep their old definitions in a live session (see the reload-survivor record).

## Evidence

- `1u2ay-bug server-runner-version-never-distinguishes-stale-runner`
- `1u2b0`
- `.wavefoundry/framework/scripts/server.py:51-70`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py:9051 RunnerIdentityTests`

## Targets

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
