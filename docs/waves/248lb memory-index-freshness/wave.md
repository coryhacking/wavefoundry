# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-23
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `248lb memory-index-freshness`
Title: Memory Index Freshness

## Objective

Agents get semantic memory search while the MCP server refreshes the index, because memory search reads the last published docs layer as one snapshot instead of falling back to lexical. `index_health` reports memory vector coverage, with stale and missing sources counted apart. Ranking, the reranker threshold and admission are unchanged.

## Changes

Change ID: `2475t-bug memory-search-falls-back-during-index-build`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-11-23

## Wave Summary

Wave `248lb` (Memory Index Freshness) delivered one change: Memory search keeps the published index while a build runs.

**Changes delivered:**

- **Memory search keeps the published index while a build runs** (`2475t-bug memory-search-falls-back-during-index-build`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11 and AC-12 completed. Key decisions: Read the memory path through `sqlite_vector_store.read_snapshot`, the snapshot `docs_search` uses during builds; Rely on the existing index monitor for edits outside the tools; add no memory-specific trigger.

## Watchpoints

- Watchpoint: AC-9 counts only when a background build completes during the `wf_memory_eval` run; record both build generations.
- Watchpoint: the MCP host must be restarted before AC-9 and AC-10, or it serves the old memory path.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 248lb-arch-arc-track2-row-stale | maybe_later | no | completed | — |
| 248lb-arch-health-complete-stale-only-unpinned | do_now | no | completed | — |
| 248lb-arch-partial-read-contract-docs | do_now | no | completed | — |
| 248lb-code-embed-inside-snapshot-repair-constraint | do_now | no | completed | — |
| 248lb-qa-class-wide-null-snapshot-masks-hermetic-path | do_now | no | completed | — |
| 248lb-qa-existing-mock-tests | do_now | no | completed | qa-reviewer |
| 248lb-sec-query-embed-inside-snapshot | do_now | no | completed | — |

*Machine review state — 7 findings; current: do_now 6, maybe_later 1, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | Phase | State | Why | Next action |
| --- | --- | --- | --- | --- |
| council-readiness | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking); known-bad control not applicable: Inspected the spec doc-contract sections, the arc row, and the three cited architecture and tool-surface passages. The change is unimplemented, and no docs-contract surface is affected beyond the planned edits; the only issue found is a non-blocking wording advisory, so no known-bad control applies. | none |
| docs-contract-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 72 | 1,302,052 |
| implement | 55 | 19,778 |
| review | 74 | 780,050 |
| **Total** | **201** | **2,101,880** |

<!-- wave:context-efficiency-state {"generation":192,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":55,"content_source_credit":29568,"derived_artifact_credit":0,"direct_net":19778,"estimated_tokens_saved":19778,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2793,"response_debit":15081,"source_credit_count":2,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8084},"plan":{"calls":72,"content_source_credit":1504236,"derived_artifact_credit":2783,"direct_net":1302052,"estimated_tokens_saved":1302052,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":40080,"response_debit":171185,"source_credit_count":70,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6298},"review":{"calls":74,"content_source_credit":974938,"derived_artifact_credit":1709,"direct_net":780050,"estimated_tokens_saved":780050,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25547,"response_debit":177828,"source_credit_count":36,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6778}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":201,"content_source_credit":2508742,"derived_artifact_credit":4492,"direct_net":2101880,"estimated_tokens_saved":2101880,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":68420,"response_debit":364094,"source_credit_count":108,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":21160},"wave_id":"248lb memory-index-freshness"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
