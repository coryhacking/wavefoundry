# Decision: Launch automatic project refresh with explicit `--content a…

Owner: Engineering
Status: superseded
Last verified: 2026-07-29

Memory ID: `1twmx-mem decision-launch-automatic-project-refresh-with-explicit-cont`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-29
Updated: 2026-07-29
Source exploration cost: 367113
Source event: `decision-log:1txzt-bug mcp-index-monitor-stale-child-recovery:ab84c0e667026a16`
Validation: rewrite
Validated by: agent
Action delta: When adding or changing an automatic index refresh launcher, pass an explicit `--content all` and test the final child arguments; do not rely on indexer.py's docs-only default.
Validation rationale: The decision is durable, but the generated target `indexer.py` alone is misleading: the repaired behavior lives in the MCP and rendered-hook launchers, while indexer.py owns the default that makes explicit content selection necessary.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1tz74-mem automatic-index-refresh-launchers-select-all-semantic-conten`
## Summary

Decision (wave 1tskc): Launch automatic project refresh with explicit `--content all`.. Rationale: `indexer.py` defaults to docs-only; a bare launch can report activity while code embeddings remain stale, which matches the operator's broader field symptom..

## Evidence

- `1txzt-bug mcp-index-monitor-stale-child-recovery`
- `1tskc`

## Targets

- `indexer.py`
