# Protect MCP stdout at both Python and file-descriptor boundaries

Owner: Engineering
Status: active
Last verified: 2026-07-18

Memory ID: `mem-protect-mcp-stdout-at-both-python-and-file-descriptor-bounda`
Kind: `environment_gotcha`
Confidence: 0.98
Created: 2026-07-18
Updated: 2026-07-18
Source event: `decision-log:1p9io-bug windows-stdout-purity:e4f5e70483942e76`
Validation: promote
Validated by: agent
Action delta: Protect both Python stdout and OS file descriptor 1 around any in-process work reached from MCP stdio.
Validation rationale: Current graph rebuild and model paths still cross the JSON-RPC stdout boundary, and Python-only redirection cannot capture native extension writes.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

When MCP stdio invokes in-process rebuilds or native libraries, redirect Python stdout and isolate OS file descriptor 1 at the boundary; Python redirect_stdout alone cannot prevent native extension writes from corrupting JSON-RPC frames.

## Evidence

- `1p9io-bug windows-stdout-purity`
- `1p9hn`
- `.wavefoundry/framework/scripts/graph_query.py:258`
- `.wavefoundry/framework/scripts/cli_stdio.py:32`
- `.wavefoundry/framework/scripts/tests/test_graph_query.py:829`

## Targets

- `.wavefoundry/framework/scripts/graph_query.py`
- `.wavefoundry/framework/scripts/cli_stdio.py`
- `.wavefoundry/framework/scripts/server_impl.py`
