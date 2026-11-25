# 1sk58-adr — Local Typed Agent Memory Records (Hosted and Graph-Only Memory Rejected)

Owner: Engineering
Status: accepted
Last verified: 2026-11-24
Amended: 2026-11-24, wave `249ar`, change `246to`

## Context

Wavefoundry preserves rich project context (wave records, journals, handoff, semantic index, structural graph), but agents still lost operational memory at the moment of action: prior failed approaches, operator preferences, fragile files, and review lessons lived in long prose and surfaced only when an agent happened to search the right words. External MCP memory systems point at the useful shape — typed, temporal, evidence-backed records with pre-action warnings — but hosted services violate the local-only contract and generic entity graphs lose evidence, lifecycle, and code-target attachment.

## Decision

A local, typed **agent memory layer**: repo-visible markdown records under `docs/agents/memory/` (eight kinds; status/supersession lifecycle; evidence and target refs required; docs-lint is the schema contract incl. forbidden-content rules), served by four MCP tools (`memory_add`/`search`/`brief`/`reconcile`) and surfaced as capped, cited advisories on hot read tools (`code_read`/`code_impact`/`code_callhierarchy`) and lifecycle tools (`wf_prepare_wave`/`wf_review_wave`/`wf_audit`). Record files are the source of truth; the semantic docs index is an optional retrieval assist; the graph gains typed `memory` nodes with `memory_targets` edges riding the incremental delta path (zero-edge-prune exempt). Confidence decays kind-awarely through the per-path freshness primitive — churn for reproduction-bound kinds, elapsed time for environment kinds, never for operator preferences and decisions, and `fragile_file` gains a needs-reverification flag instead of attenuating (churn on a fragile file is ambiguous evidence). Decay orders and gates briefings; status and supersession are the only lifecycle mechanisms. Lifecycle prompts capture candidates at pause/review and require a promote/reject/defer decision on every candidate at close. The established framework term "Wave Memory" keeps naming the continuity model (handoff/journals); this layer is consistently the "agent memory layer" in shipped surfaces.

## Consequences

- Prior learning appears when it changes the next action, not only when searched for; absence of a record is not absence of risk (tools say so).
- Records are diffable, reviewable, packaged/upgraded like any operating-surface doc, and lint-enforced against secrets/transcripts/personal facts before write.
- Memory writes stay cheap (per-file graph delta, background index refresh) so lifecycle capture is viable.

## Alternatives Considered

- **Hosted memory service** (Mem0/Zep-style): strong retrieval but violates local-only/no-network-by-default and adds trust burden. Rejected.
- **Generic MCP knowledge graph only**: loses evidence refs, lifecycle capture, and code-target attachment — the parts that make memory actionable in a coding harness. Rejected.
- **Journal-only improvements**: low cost, but still depends on agents searching prose and creates no action-time warnings. Rejected.

## Amendment (wave 249ar, 2026-11-24)

Churn now flags a record instead of attenuating it, for every kind. The Decision's "churn for reproduction-bound kinds" and the `fragile_file` exception are replaced by one rule:

- **Flag, never attenuate.** Commits on a target's canonical path since the record's last recorded check that reach its adaptive halving count set the derived `target_churn` revalidation reason. Confidence and briefing inclusion do not change. Elapsed-time decay for environment and dependency gotchas stays, measured from the last recorded check.
- **Other signals.** A target that no longer resolves in the working tree sets `target_unresolved`; a target named by a bare suffix sets `target_not_canonical`. All three are derived on each read and never written. The memory review's audit order lists flagged records first.
- **Recorded check.** The last check is the `Checked at:` timestamp a `memory_reconcile` call with a `check_note` writes, else `Updated:`, else `Created:`. A keep of an active record requires a `check_note` and is refused while a target is unresolved. Reading a record never resets its decay.

Reason: a silent confidence cut hid records that needed a check; the flag queues them for review. Change `246to-enh memory-revalidation-by-signal`.
