# Decision: Add defense-in-depth wrapper at `graph_query.py:220` even a…

Owner: Engineering
Status: superseded
Last verified: 2026-07-18

Memory ID: `mem-decision-add-defense-in-depth-wrapper-at-graph-query-py-220-`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1p9io-bug windows-stdout-purity:e4f5e70483942e76`
Validation: rewrite
Validated by: agent
Action delta: Protect both Python stdout and OS file descriptor 1 around any in-process work reached from MCP stdio.
Validation rationale: Current graph rebuild and model paths still cross the JSON-RPC stdout boundary, and Python-only redirection cannot capture native extension writes.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `mem-protect-mcp-stdout-at-both-python-and-file-descriptor-bounda`
## Summary

Decision (wave 1p9hn): Add defense-in-depth wrapper at `graph_query.py:220` even after fixing print sites. Rationale: Future undetected prints in the rebuild path will be caught at the boundary.

## Evidence

- `1p9io-bug windows-stdout-purity`
- `1p9hn`

## Targets

- `graph_query.py`
