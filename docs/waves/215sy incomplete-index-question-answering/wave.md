# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-19
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `215sy incomplete-index-question-answering`
Title: Incomplete Index Question Answering

## Objective

Agents and operators keep getting cited answers from `code_ask`, `code_search` and `docs_search` while the index is stale, building or interrupted, with every such response saying the index needs updating and coverage may be incomplete. Index health, publication and lifecycle gates still report actual readiness.

## Changes

Change ID: `213yb-enh incomplete-index-question-answering`
Change Status: `implemented`

## Participants

- Coordinator: Engineering
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-10-19

## Wave Summary

Wave `215sy` (Incomplete Index Question Answering) delivered one change: Keep questions available with an incomplete index. Notable adjustments during implementation: Keep questions available with an incomplete index: Delivery repair RT-DEL-1 (test only, no product change): added `test_publication_between_two_dense_reads_is_not_combined`. A real producer thread commits its publication after the first `dense_rows` read (docs) of one degraded `code_ask` and before its later code dense read; the later read and the citations must not contain the new file, and the next call must.; Keep questions available with an incomplete index: Delivery review: code-reviewer, architecture-reviewer, docs-contract-reviewer and qa-reviewer approved; red-team and security seats passed. RT-DEL-1 (red-team: AC-3 evidence covered only the lexical side) repaired test-only with `test_publication_between_two_dense_reads_is_not_combined` and reverified by qa-reviewer; council-delivery recorded. CHANGELOG bullet added by the coordinator. Review outcomes are carried by the ledger projection in wave.md.

**Changes delivered:**

- **Keep questions available with an incomplete index** (`213yb-enh incomplete-index-question-answering`) — 4 ACs completed. Key decisions: Query compatible available SQLite data with explicit incomplete coverage.
## Watchpoints

- Watchpoint: open `framework_edit_allowed` before framework edits, whatever the edit tool, and close it after.
- Watchpoint: the serving path (`server_impl.Index`, vector and FTS readers) is shared by every retrieval tool; test publication transitions and the healthy path, not only the degraded one.
- Watchpoint: planned by another session on 2026-10-19; verify its claims against the tree before relying on them.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| RT-DEL-1 | do_now | no | completed | qa-reviewer |
| SUITE-DEL-1 | do_now | no | completed | qa-reviewer |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 29 | 1,045,491 |
| implement | 26 | 0 |
| review | 48 | 970,632 |
| **Total** | **103** | **2,016,123** |

<!-- wave:context-efficiency-state {"generation":92,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":26,"content_source_credit":5410,"derived_artifact_credit":0,"direct_net":-1882,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":754,"response_debit":9550,"source_credit_count":2,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3012},"plan":{"calls":29,"content_source_credit":1092551,"derived_artifact_credit":2765,"direct_net":1045491,"estimated_tokens_saved":1045491,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3824,"response_debit":50429,"source_credit_count":23,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4428},"review":{"calls":48,"content_source_credit":1086749,"derived_artifact_credit":1958,"direct_net":970632,"estimated_tokens_saved":970632,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9684,"response_debit":111605,"source_credit_count":49,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3214}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":103,"content_source_credit":2184710,"derived_artifact_credit":4723,"direct_net":2014241,"estimated_tokens_saved":2016123,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14262,"response_debit":171584,"source_credit_count":74,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10654},"wave_id":"215sy incomplete-index-question-answering"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 7 | 0 | 7 | 5,695,868 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":7,"estimated_exploration_avoided":5695868,"surfaced_events":7} -->
<!-- wave:exploration-avoided end -->
