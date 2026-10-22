# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-21
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21bzn tensorwell-digest-ctime-and-1-36-0`
Title: Tensorwell Digest Ctime And 1 36 0

## Objective

The last cross-kind stat comparison that includes ctime (the Tensorwell controller digest) follows the 21alh rule, so it cannot refuse an unchanged controller on Windows once the client runs there. Boundaries: no other client behaviour changes; the ReFS/Dev Drive device-and-inode probe is separate.

## Changes

Change ID: `21bzm-bug tensorwell-controller-digest-cross-kind-ctime`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator (Claude Code primary)
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-21

## Wave Summary

Wave `21bzn` (Tensorwell Digest Ctime And 1 36 0) delivered one change: Tensorwell Controller Digest Ignores ctime Across Stat Kinds.

**Changes delivered:**

- **Tensorwell Controller Digest Ignores ctime Across Stat Kinds** (`21bzm-bug tensorwell-controller-digest-cross-kind-ctime`) — 3 ACs completed. Key decisions: Apply the 21alh rule to the one remaining cross-kind ctime comparison
## Watchpoints

- Follow-up: the ReFS/Dev Drive/SMB device-and-inode probe is planned separately and is not part of this wave.

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
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
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
| plan | 15 | 0 |
| implement | 15 | 0 |
| review | 8 | 14,670 |
| **Total** | **38** | **14,670** |

<!-- wave:context-efficiency-state {"generation":36,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":15,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-641,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":518,"response_debit":2881,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2758},"plan":{"calls":15,"content_source_credit":24595,"derived_artifact_credit":2103,"direct_net":-30924,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1408,"response_debit":60642,"source_credit_count":9,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4428},"review":{"calls":8,"content_source_credit":24548,"derived_artifact_credit":1054,"direct_net":14670,"estimated_tokens_saved":14670,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1496,"response_debit":12650,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3214}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":38,"content_source_credit":49143,"derived_artifact_credit":3157,"direct_net":-16895,"estimated_tokens_saved":14670,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3422,"response_debit":76173,"source_credit_count":19,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10400},"wave_id":"21bzn tensorwell-digest-ctime-and-1-36-0"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
