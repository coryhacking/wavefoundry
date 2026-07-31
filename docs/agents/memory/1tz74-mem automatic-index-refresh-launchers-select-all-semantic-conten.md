# Automatic index refresh launchers select all semantic content explicitly

Owner: Engineering
Status: active
Last verified: 2026-07-29

Memory ID: `1tz74-mem automatic-index-refresh-launchers-select-all-semantic-conten`
Kind: `decision`
Confidence: 0.9
Created: 2026-07-29
Updated: 2026-07-29
Source exploration cost: 367113
Source event: `decision-log:1txzt-bug mcp-index-monitor-stale-child-recovery:ab84c0e667026a16`
Validation: promote
Validated by: agent
Action delta: When adding or changing an automatic index refresh launcher, pass an explicit `--content all` and test the final child arguments; do not rely on indexer.py's docs-only default.
Validation rationale: The decision is durable, but the generated target `indexer.py` alone is misleading: the repaired behavior lives in the MCP and rendered-hook launchers, while indexer.py owns the default that makes explicit content selection necessary.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Wavefoundry automatic refresh launchers must pass `--content all` explicitly because indexer.py defaults to docs-only. This keeps both documentation and code embeddings convergent and prevents a successful background activity signal from masking a stale code layer.

## Evidence

- `1txzt-bug mcp-index-monitor-stale-child-recovery`
- `1tskc`

## Targets

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/indexer.py`
