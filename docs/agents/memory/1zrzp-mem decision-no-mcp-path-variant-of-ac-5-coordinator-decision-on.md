# Decision: No MCP-path variant of AC-5 (coordinator decision: only if…

Owner: Engineering
Status: rejected
Last verified: 2026-10-04

Memory ID: `1zrzp-mem decision-no-mcp-path-variant-of-ac-5-coordinator-decision-on`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-04
Updated: 2026-10-04
Source exploration cost: 470529
Source event: `decision-log:1zrah-bug old-runner-stale-vocabulary-profile-at-lifecycle-policy:7de5d54972c4af2e`
Validation: reject
Validated by: agent
Action delta: No durable action: a one-off test-scope choice for one AC, already recorded in the 1zrah Decision Log.
Validation rationale: The decision only scoped one acceptance test (no MCP-driven upgrade run); it does not change future behavior and the change doc already carries it.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates

## Summary

Decision (wave 1zqe4): No MCP-path variant of AC-5 (coordinator decision: only if cheap).. Rationale: The 1.28.0 `wf_upgrade` tool runs the installed `upgrade_wavefoundry.py` as a child script with the same runner code, pre-extraction imports and pack-loaded hook (Requirement 8). Driving it needs a running 1.28.0 MCP server on the fixture, which is not cheap, and it would exercise no code the CLI run does not..

## Evidence

- `1zrah-bug old-runner-stale-vocabulary-profile-at-lifecycle-policy`
- `1zqe4`

## Targets

- `upgrade_wavefoundry.py`
