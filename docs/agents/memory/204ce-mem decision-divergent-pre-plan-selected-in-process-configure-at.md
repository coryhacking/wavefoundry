# Decision: Divergent pre-plan, selected: in-process `configure()` at e…

Owner: Engineering
Status: rejected
Last verified: 2026-10-07

Memory ID: `204ce-mem decision-divergent-pre-plan-selected-in-process-configure-at`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-07
Updated: 2026-10-07
Source exploration cost: 184122
Source event: `decision-log:1zyv1-enh project-local-bytecode-cache:e1b6423fe2cd1103`
Validation: reject
Validated by: agent
Action delta: No separate action: covered by the rewritten child-process bytecode record.
Validation rationale: The design choice (in-process configure at entry points) is captured by the rewritten fragile_file record and the AGENTS.md hygiene paragraph; the drafted target wf.cmd is not the seam.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates

## Summary

Decision (wave 200xy): Divergent pre-plan, selected: in-process `configure()` at entry points with a library guard. Critique: touches 22 modules, mitigated by a derived census test.. Rationale: Cross-platform with one source of truth; works for hooks, `wf`, MCP and children through the inherited variable; fixes the import-order leak.

## Evidence

- `1zyv1-enh project-local-bytecode-cache`
- `200xy`

## Targets

- `wf.cmd`
