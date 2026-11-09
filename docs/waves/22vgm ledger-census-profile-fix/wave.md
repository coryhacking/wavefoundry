# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-09
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `22vgm ledger-census-profile-fix`
Title: Ledger Census Profile Fix

## Objective

Release maintainers get a passing second-profile qualification for 1.41.0: the repository ledger census test from wave 22upa runs only in the default profile, where this repository's records exist. No shipped code changes.

## Changes

Change ID: `22vgl-bug ledger-census-test-second-profile`
Change Status: `implemented`

## Participants

- Coordinator: coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-11-09

## Wave Summary

Wave `22vgm` (Ledger Census Profile Fix) delivered one change: Run the Repository Ledger Census Test in the Default Profile Only.

**Changes delivered:**

- **Run the Repository Ledger Census Test in the Default Profile Only** (`22vgl-bug ledger-census-test-second-profile`) — 2 ACs completed. Key decisions: Mark the test `default_profile_only`
## Watchpoints

- Watchpoint: run the full suite last, then the second and declared qualifications, before the release build; block the release on any failure.

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

## Review Checkpoints

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 35 | 750,044 |
| implement | 10 | 0 |
| review | 11 | 17,284 |
| **Total** | **56** | **767,328** |

<!-- wave:context-efficiency-state {"generation":35,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":10,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-1725,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":330,"response_debit":1679,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":284},"plan":{"calls":35,"content_source_credit":803317,"derived_artifact_credit":2412,"direct_net":750044,"estimated_tokens_saved":750044,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5934,"response_debit":55253,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5502},"review":{"calls":11,"content_source_credit":34199,"derived_artifact_credit":1221,"direct_net":17284,"estimated_tokens_saved":17284,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4110,"response_debit":17802,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3776}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":56,"content_source_credit":837516,"derived_artifact_credit":3633,"direct_net":765603,"estimated_tokens_saved":767328,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10374,"response_debit":74734,"source_credit_count":30,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9562},"wave_id":"22vgm ledger-census-profile-fix"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
