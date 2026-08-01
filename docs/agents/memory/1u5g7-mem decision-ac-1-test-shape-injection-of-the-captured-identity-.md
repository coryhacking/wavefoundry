# Decision: AC-1 test shape: injection of the captured identity (the al…

Owner: Engineering
Status: superseded
Last verified: 2026-07-31

Memory ID: `1u5g7-mem decision-ac-1-test-shape-injection-of-the-captured-identity-`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 777948
Source event: `decision-log:1u2ay-bug server-runner-version-never-distinguishes-stale-runner:3c87c60838c7e12b`
Validation: rewrite
Validated by: agent
Action delta: To test launch-captured runner state, inject a compute_runner_identity pair over temp copies of the real runner files (RunnerIdentityTests in tests/test_server_tools.py) instead of spawning an MCP subprocess probe; reserve fresh-process probes for changes to which TOOLS the runner registers.
Validation rationale: The decision is durable but the draft states it as one-time AC bookkeeping ("AC-1 test shape") with a truncated title and a bare `server.py` basename target, so it would never surface to someone editing the test module that actually holds the technique. Verified in the current tree: server.py:51-70 computes SERVER_RUNNER_FILES and SERVER_RUNNER_VERSION once at import, and tests/test_server_tools.py:9086-9191 (RunnerIdentityTests) exercises the seam by calling server_impl.compute_runner_identity over temp copies and mutating them. Evidence chain followed in the 1u2b0 ledger. Rewritten to name the reusable mechanism (a launch-captured value cannot be re-captured in-process, so inject the pair) and its boundary against the existing reload-survivor record 1t38p-mem, which requires a fresh-process probe for tool-registration changes.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1u4hd-mem test-launch-captured-runner-identity-by-injection-not-by-a-f`
## Summary

Decision (wave 1u2b0): AC-1 test shape: injection of the captured identity (the allowed alternative), not a fresh-subprocess MCP probe. Rationale: The comparison seam is exactly the (identity, runner_files) pair `server.py` records at launch; injecting it over temp copies of the real runner files exercises the same code path deterministically and lets both stale directions and both files be covered without subprocess flake.

## Evidence

- `1u2ay-bug server-runner-version-never-distinguishes-stale-runner`
- `1u2b0`

## Targets

- `server.py`
