# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-05
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zv88 distribution-test-portability`
Title: Distribution Test Portability

## Objective

Make four upstream tests hold for a distribution with valid extension declarations and its own vocabulary profile, so Waveforge stops carrying local edits to them.

## Changes

Change ID: `1zv86-bug upstream-tests-assume-stock-declarations`
Change Status: `implemented`

## Participants

- Coordinator: wave-council
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-05

## Wave Summary

Wave `1zv88` (Distribution Test Portability) delivered one change: Upstream Tests Fail On A Distribution's Valid Extension Declarations. Notable adjustments during implementation: Upstream Tests Fail On A Distribution's Valid Extension Declarations: Implemented. R1: per-slot provider patching plus a recorder proving each wrapper receives its own declared keywords in every permutation; `setUp` applies the base declaration. R2: `classified_census` drops `run_with_tree_kill` rows only in flat modules outside `FRAMEWORK_SCRIPT_MODULE_NAMES`. R4a amended (Requirement 3): an exact server import closure cannot work because 36 listed scripts are entry points or loaded by name; the census reads the on-disk declaration, stays exact when it is stock, and on a declared distribution requires listing only for modules the server or a listed script imports. R4b: anchored `subn` with count 1, plus a renamed-container test. Mutation probes killed every guard (the first R1 version survived removal of the provider patch; the recorder fixed it). A simulated distribution (extension module plus undeclared helper on disk) passes both censuses, and a raw timed call in its helper fails. Gapfill: AST and grep reads of the four test files and the census inputs were done with shell tools because the work is test-local and mechanical.

**Changes delivered:**

- **Upstream Tests Fail On A Distribution's Valid Extension Declarations** (`1zv86-bug upstream-tests-assume-stock-declarations`) — 5 ACs completed. Key decisions: R4a keeps the exact census on a stock declaration and relaxes it only for a declared distribution; R2 by rule (routed callee in non-upstream files), not a new declaration
## Watchpoints

- Watchpoint: test-only; no production behavior change. Opens after `1zv87` closes (one OPEN wave at a time).

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 23 | 2,277 |
| implement | 9 | 17,144 |
| review | 5 | 2,147 |
| **Total** | **37** | **21,568** |

<!-- wave:context-efficiency-state {"generation":37,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":9,"content_source_credit":26397,"derived_artifact_credit":1263,"direct_net":17144,"estimated_tokens_saved":17144,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1600,"response_debit":9018,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":102},"plan":{"calls":23,"content_source_credit":16267,"derived_artifact_credit":1033,"direct_net":2277,"estimated_tokens_saved":2277,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1561,"response_debit":22675,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9213},"review":{"calls":5,"content_source_credit":6563,"derived_artifact_credit":30,"direct_net":2147,"estimated_tokens_saved":2147,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":166,"response_debit":6596,"source_credit_count":2,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":37,"content_source_credit":49227,"derived_artifact_credit":2326,"direct_net":21568,"estimated_tokens_saved":21568,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3327,"response_debit":38289,"source_credit_count":22,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11631},"wave_id":"1zv88 distribution-test-portability"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
