# 1sk58-adr — Local Typed Agent Memory Records (Hosted and Graph-Only Memory Rejected)

Owner: Engineering
Status: accepted
Last verified: 2026-07-13

## Context

Wavefoundry preserves rich project context (wave records, journals, handoff, semantic index, structural graph), but agents still lost operational memory at the moment of action: prior failed approaches, operator preferences, fragile files, and review lessons lived in long prose and surfaced only when an agent happened to search the right words. External MCP memory systems point at the useful shape — typed, temporal, evidence-backed records with pre-action warnings — but hosted services violate the local-only contract and generic entity graphs lose evidence, lifecycle, and code-target attachment.

## Decision

A local, typed **agent memory layer**: repo-visible markdown records under `docs/agents/memory/` (eight kinds; status/supersession lifecycle; evidence and target refs required; docs-lint is the schema contract incl. forbidden-content rules), served by four MCP tools (`wave_memory_add`/`search`/`brief`/`reconcile`) and surfaced as capped, cited advisories on hot read tools (`code_read`/`code_impact`/`code_callhierarchy`) and lifecycle tools (`wave_prepare`/`wave_review`/`wave_audit`). Record files are the source of truth; the semantic docs index is an optional retrieval assist; the graph gains typed `memory` nodes with `memory_targets` edges riding the incremental delta path (zero-edge-prune exempt). Confidence decays kind-awarely through the per-path freshness primitive — churn for reproduction-bound kinds, elapsed time for environment kinds, never for operator preferences and decisions, and `fragile_file` gains a needs-reverification flag instead of attenuating (churn on a fragile file is ambiguous evidence). Decay orders and gates briefings; status and supersession are the only lifecycle mechanisms. Lifecycle prompts capture candidates at pause/review and require a promote/reject/defer decision on every candidate at close. The established framework term "Wave Memory" keeps naming the continuity model (handoff/journals); this layer is consistently the "agent memory layer" in shipped surfaces.

## Consequences

- Prior learning appears when it changes the next action, not only when searched for; absence of a record is not absence of risk (tools say so).
- Records are diffable, reviewable, packaged/upgraded like any operating-surface doc, and lint-enforced against secrets/transcripts/personal facts before write.
- Memory writes stay cheap (per-file graph delta, background index refresh) so lifecycle capture is viable.

## Alternatives Considered

- **Hosted memory service** (Mem0/Zep-style): strong retrieval but violates local-only/no-network-by-default and adds trust burden. Rejected.
- **Generic MCP knowledge graph only**: loses evidence refs, lifecycle capture, and code-target attachment — the parts that make memory actionable in a coding harness. Rejected.
- **Journal-only improvements**: low cost, but still depends on agents searching prose and creates no action-time warnings. Rejected.
