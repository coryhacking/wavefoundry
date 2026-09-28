# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-28
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1z8tv manifest-garden-date`
Title: Manifest Garden Date

## Objective

The prompt-surface manifest stops changing every gardening day: the unread `last_gardened_at` date is removed.

## Changes

Change ID: `1z8tu-debt drop-manifest-garden-date`
Change Status: `complete`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-09-28

## Wave Summary

Wave `1z8tv` (Manifest Garden Date) delivered one change: Drop the Manifest's Last-Gardened Date.

**Changes delivered:**

- **Drop the Manifest's Last-Gardened Date** (`1z8tu-debt drop-manifest-garden-date`) — 3 ACs completed. Key decisions: Remove the field rather than stamp it only on real content changes
## Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| keyless-nothing-stamped-subtest-stamps | do_now | no | completed | — |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 19 | 293,932 |
| implement | 23 | 427,008 |
| review | 11 | 34,376 |
| **Total** | **53** | **755,316** |

<!-- wave:context-efficiency-state {"generation":53,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":23,"content_source_credit":473471,"derived_artifact_credit":0,"direct_net":427008,"estimated_tokens_saved":427008,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":660,"response_debit":46307,"source_credit_count":22,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":504},"plan":{"calls":19,"content_source_credit":340178,"derived_artifact_credit":2181,"direct_net":293932,"estimated_tokens_saved":293932,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3221,"response_debit":49015,"source_credit_count":26,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":11,"content_source_credit":54621,"derived_artifact_credit":977,"direct_net":34376,"estimated_tokens_saved":34376,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3781,"response_debit":19757,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":53,"content_source_credit":868270,"derived_artifact_credit":3158,"direct_net":755316,"estimated_tokens_saved":755316,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7662,"response_debit":115079,"source_credit_count":64,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6629},"wave_id":"1z8tv manifest-garden-date"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
