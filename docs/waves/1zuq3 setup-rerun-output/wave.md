# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-04
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zuq3 setup-rerun-output`
Title: Setup Rerun Output

## Objective

Make a routine `wf setup` rerun quiet and truthful before 1.29.0 ships: no first-install instructions on installed repositories, no exit 2 from `wf setup --check` on a transient, and no rewriting of unchanged rendered files that re-indexes `.gitattributes` on every run.

## Changes

Change ID: `1zuq1-bug setup-closing-text-assumes-first-install`
Change Status: `implemented`

Change ID: `1zuq2-bug setup-check-gives-up-on-transient`
Change Status: `implemented`

Change ID: `1zuq4-bug render-rewrites-unchanged-surfaces`
Change Status: `implemented`

## Participants

- Coordinator: wave-council
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-05

## Wave Summary

Wave `1zuq3` (Setup Rerun Output) delivered 3 changes: Setup's Closing Message Gives First-Install Instructions On Every Run, `wf setup --check` Gives Up On A Transient Readiness Result, and Platform Surface Rendering Rewrites Unchanged Files On Every Setup.

**Changes delivered:**

- **Setup's Closing Message Gives First-Install Instructions On Every Run** (`1zuq1-bug setup-closing-text-assumes-first-install`) — 6 ACs completed. Key decisions: First install means a live install log with Phase 1 pending
- **`wf setup --check` Gives Up On A Transient Readiness Result** (`1zuq2-bug setup-check-gives-up-on-transient`) — 5 ACs completed. Key decisions: Leave upgrade cleanup's copy of the rule in place
- **Platform Surface Rendering Rewrites Unchanged Files On Every Setup** (`1zuq4-bug render-rewrites-unchanged-surfaces`) — 5 ACs completed. Key decisions: Fix the rewrite, not the indexer's handling of zero-chunk files
## Watchpoints

- Watchpoint: framework edits need `framework_edit_allowed`; full suites run in scratch copies; the receipt run is last, in the repo.
- Follow-up: the indexer labels a changed zero-chunk file as drifted; cosmetic once mtimes are stable.

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
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 39 | 1,634,044 |
| implement | 3 | 0 |
| review | 6 | 10,834 |
| **Total** | **48** | **1,644,878** |

<!-- wave:context-efficiency-state {"generation":24,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":3,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-159,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19,"response_debit":140,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":39,"content_source_credit":1677084,"derived_artifact_credit":4495,"direct_net":1634044,"estimated_tokens_saved":1634044,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2349,"response_debit":48995,"source_credit_count":36,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":6,"content_source_credit":19001,"derived_artifact_credit":784,"direct_net":10834,"estimated_tokens_saved":10834,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1271,"response_debit":9996,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":48,"content_source_credit":1696085,"derived_artifact_credit":5279,"direct_net":1644719,"estimated_tokens_saved":1644878,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3639,"response_debit":59131,"source_credit_count":44,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6125},"wave_id":"1zuq3 setup-rerun-output"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
