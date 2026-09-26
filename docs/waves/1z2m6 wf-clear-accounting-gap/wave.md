# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-26
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1z2m6 wf-clear-accounting-gap`
Title: Wf Clear Accounting Gap

## Objective

Operators clear the Context Efficiency accounting gap with `wf clear-accounting-gap` instead of a raw script path, from any folder of the repository. Added before the 1.27.0 release.

## Changes

Change ID: `1z2m5-enh wf-clear-accounting-gap-command`
Change Status: `review`

## Participants

- Coordinator: operator session
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-09-26

## Wave Summary

Wave `1z2m6` (Wf Clear Accounting Gap) delivered one change: Add `wf clear-accounting-gap`. Notable adjustments during implementation: Add `wf clear-accounting-gap`: Operator asked for a Windows review; added `_replace_with_retry` for the clear's gap-file renames (2-second budget, Windows only). Three tests; a mutant that drops the retry fails one.

**Changes delivered:**

- **Add `wf clear-accounting-gap`** (`1z2m5-enh wf-clear-accounting-gap-command`) — 5 ACs completed. Key decisions: Name it `wf clear-accounting-gap` (operator); Supersede the `1z2m4` decision to keep the clear off the `wf` dispatcher
## Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

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
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 16 | 4,454 |
| implement | 2 | 0 |
| review | 15 | 75,071 |
| **Total** | **33** | **79,525** |

<!-- wave:context-efficiency-state {"generation":33,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":2,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-337,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2,"response_debit":335,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":16,"content_source_credit":16706,"derived_artifact_credit":3601,"direct_net":4454,"estimated_tokens_saved":4454,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1903,"response_debit":20461,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":15,"content_source_credit":101014,"derived_artifact_credit":2922,"direct_net":75071,"estimated_tokens_saved":75071,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3729,"response_debit":27452,"source_credit_count":26,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":33,"content_source_credit":117720,"derived_artifact_credit":6523,"direct_net":79188,"estimated_tokens_saved":79525,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5634,"response_debit":48248,"source_credit_count":38,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8827},"wave_id":"1z2m6 wf-clear-accounting-gap"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
