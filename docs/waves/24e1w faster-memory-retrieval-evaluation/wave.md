# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-26
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `24e1w faster-memory-retrieval-evaluation`
Title: Faster Memory Retrieval Evaluation

## Objective

Maintainers spend less inference work on a full memory evaluation while retaining comparable retrieval results. Measure how much local vector reuse saves and whether bounded query batches improve elapsed time on a qualified provider.

## Changes

Spec ID: `24e1v-enh reuse-and-batch-memory-evaluation-query-vectors`
Spec Status: `implemented`

## Participants

- Coordinator: wave coordinator
- Write-owning roles: implementer
- Requested review lanes: qa-reviewer
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-11-26

## Wave Summary

Wave `24e1w` (Faster Memory Retrieval Evaluation) delivered one change: Reuse query embeddings and evaluate bounded batching.

Intent outcome: Achieved. The evaluator reuses each comparison query vector and batches qualified direct and service inference. Keep evidence/tensorwell-benchmark.md, evidence/direct-model-comparison.json and evidence/direct-gpu-comparison.json for the measured timings and ranking parity. Native GPU verification covered Apple CoreML. Code and QA approved delivery.

**Changes delivered:**

- **Reuse query embeddings and evaluate bounded batching** (`24e1v-enh reuse-and-batch-memory-evaluation-query-vectors`) — AC-1, AC-2, AC-3, AC-4 and AC-5 completed. Key decisions: Share a vector within the evaluator first, then measure bounded batching independently.

## Watchpoints

- Evaluate persistent provider caching as a Tensorwell follow-up only if repeated requests remain material. Preserve real production calls and measure experimental work independently.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | Phase | State | Why | Next action |
| --- | --- | --- | --- | --- |
| council-readiness | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

Intent outcome: Achieved. The evaluator reuses each comparison query vector and batches qualified direct and service inference. Keep evidence/tensorwell-benchmark.md, evidence/direct-model-comparison.json and evidence/direct-gpu-comparison.json for the measured timings and ranking parity. Native GPU verification covered Apple CoreML. Code and QA approved delivery.

The council approved amended AC-5 following independent code and QA checks on the old CPU opt-in, unsupported GPU selection, scalar parity, and refusal to build a rejected CoreML graph. The operator selected supported direct batching as the default. The GPU benchmark distinguishes changing device from changing batch size.

Readiness approved. Code and QA independently tested case association, tie ordering and fallback eligibility. The chair replayed the four-case production control. Architecture, security and reality-checker seats agreed on scalar reuse as the alternative if batching fails parity or timing. The red-team identified swapped case vectors as a failure hidden by aggregate scores. Only run-local vectors and aggregate evidence are in scope.

Independent QA prediction before receiving the primer: “with 5 distinct cases, batch limit 2, healthy cold providers, comparison requests are 10 vectors/10 calls baseline, 5/5 scalar reuse and 5/3 qualified batching (2,2,1). All yield identical ordered per-arm IDs including ties. Real production handler still runs 5 times with same qualification/fallback counts; switching provider recomputes. Unqualified batch provider uses scalar reuse; partial/invalid/observable reordered outputs fail visibly. Batching enabled only with qualified semantics and repeatable time advantage.”

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 226 | 0 |
| implement | 41 | 574,918 |
| review | 30 | 2,779,780 |
| **Total** | **297** | **3,354,698** |

<!-- wave:context-efficiency-state {"generation":91,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":41,"content_source_credit":593685,"derived_artifact_credit":0,"direct_net":574918,"estimated_tokens_saved":574918,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1140,"response_debit":21760,"source_credit_count":13,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4133},"plan":{"calls":226,"content_source_credit":177444,"derived_artifact_credit":2272,"direct_net":-183187,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":20401,"response_debit":353659,"source_credit_count":71,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11157},"review":{"calls":30,"content_source_credit":2839673,"derived_artifact_credit":2102,"direct_net":2779780,"estimated_tokens_saved":2779780,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3714,"response_debit":65210,"source_credit_count":34,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6929}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":297,"content_source_credit":3610802,"derived_artifact_credit":4374,"direct_net":3171511,"estimated_tokens_saved":3354698,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25255,"response_debit":440629,"source_credit_count":118,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":22219},"wave_id":"24e1w faster-memory-retrieval-evaluation"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 5 | 0 | 2 | 429,051 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":429051,"surfaced_events":5} -->
<!-- wave:exploration-avoided end -->
