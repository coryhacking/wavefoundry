# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-13
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20lul tensorwell-memory-reranking`
Title: Tensorwell Memory Reranking

## Objective

Use the qualified Tensorwell reranker for memory retrieval so MCP does not construct a duplicate local model while the service is available. Preserve memory relevance, bounded failure and optional local fallback through separate memory-specific qualification.

## Changes

Change ID: `20l7y-enh tensorwell-memory-reranking`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer

Completed At: 2026-10-13

## Wave Summary

Wave `20lul` (Tensorwell Memory Reranking) delivered one change: Tensorwell Memory Reranking. Notable adjustments during implementation: Tensorwell Memory Reranking: Readback: memory retrieval will select the qualified Tensorwell adapter before any local cache or constructor; explicit disable and absent-service CPU fallback remain. The combined integration control covers embeddings, normal reranking and memory reranking without local session creation. Existing cached fallback sessions are not evicted by this narrowly scoped change. Before: qualified service plus memory search constructs CPU model; after: memory scores arrive through the same service adapter.

**Changes delivered:**

- **Tensorwell Memory Reranking** (`20l7y-enh tensorwell-memory-reranking`) — 5 ACs completed. Key decisions: Reuse the qualified adapter first, preserving CPU fallback and the unchanged relevance gate; qualify memory separately.; Separate follow-up wave from 20nju.
## Watchpoints

- The original 20nju remains implemented and reviewed; pause it only when activating this follow-up.
- Preserve the raw-score cutoff and established quality bar; native qualification failure requires plan reconciliation.
- No service lifecycle operations, live memory mutations, downloads, commit or closure.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| D1 | do_now | no | completed | code-reviewer, qa-reviewer |
| D2 | do_now | no | completed | code-reviewer, qa-reviewer |

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
| performance-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: pending explicit closure instruction.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 29 | 396,779 |
| implement | 106 | 1,214,371 |
| review | 84 | 911,382 |
| **Total** | **219** | **2,522,532** |

<!-- wave:context-efficiency-state {"generation":221,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":106,"content_source_credit":1537138,"derived_artifact_credit":0,"direct_net":1214371,"estimated_tokens_saved":1214371,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3923,"response_debit":321776,"source_credit_count":28,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2932},"plan":{"calls":29,"content_source_credit":452191,"derived_artifact_credit":1493,"direct_net":396779,"estimated_tokens_saved":396779,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4741,"response_debit":55969,"source_credit_count":23,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":84,"content_source_credit":1100043,"derived_artifact_credit":1771,"direct_net":911382,"estimated_tokens_saved":911382,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":18119,"response_debit":175244,"source_credit_count":49,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2931}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":219,"content_source_credit":3089372,"derived_artifact_credit":3264,"direct_net":2522532,"estimated_tokens_saved":2522532,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":26783,"response_debit":552989,"source_credit_count":100,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9668},"wave_id":"20lul tensorwell-memory-reranking"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 4 | 0 | 4 | 2,923,309 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":2923309,"surfaced_events":4} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

- Product-owner acknowledgment: operator requested the memory reranker use Tensorwell to avoid a duplicate local model.
- Work allocation: coordinator owns narrowly coupled source/tests/docs; independent discovery handles corpus feasibility. Independent readiness and delivery use task-fit available model settings and actual isolated contexts; do not count one context as several independent votes. No permanent per-seat report folder.
- Delivery council: full isolated red-team primer; fixed architecture/code (one context), QA, security and reality/docs (one context); rotating performance; council-chair synthesis. Fixed seats weighed releasing a previously cached local model, retained the admitted no-new-construction boundary, and found no material design disagreement. Fresh code and QA independently cleared the two fixture-only findings. Required performance review executed the constructor-trap test and killed its memory-only service-removal mutant; no RSS or latency claim.
- Qualification: canonical six-worker suite passed 12,504 tests across 187 files, 12 existing skips, 763.799 seconds; full docs validation passed. Native memory results: useful queries 15 to 16, all eight negatives empty, direct-support precision 15/21 to 16/22. Reviewers checked supplied native evidence and labels; they did not repeat native inference.
- Retrospective/memory: inspected both proposed repair memories. No new candidate selected: explicit fixture controls and exact handler-digest coupling are retained in the regression tests; the proposal text adds no durable action beyond those controls. No wave-linked candidates were created.
- Cleanup: retained only wave.md, the admitted change doc and authoritative events.jsonl. Raw logs and reviewer working reports remain temporary; no permanent evidence folder was created.
- Follow-up authorized by operator: remove proven inherited duplicate test executions, bound ordinary scanner fixtures that grow with checkout history, and measure runtime while preserving unique coverage. Current timing is affected by host CPU/memory contention; neither a return to the historical 135.9-second median nor a causal speedup is claimed.
