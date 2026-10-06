# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-05
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zyc3 attested-approvals-and-profile-goldens`
Title: Attested Approvals And Profile Goldens

## Objective

Close two Waveforge Part 3 requests before 1.29.0: self-attested person names on review-ledger approvals, and a tool-surface golden fixture per declaration profile.

## Changes

Change ID: `1zyc1-enh self-attested-approval-names`
Change Status: `implemented`

Change ID: `1zyc2-enh tool-surface-golden-per-profile`
Change Status: `implemented`

## Participants

- Coordinator: main session
- Write-owning roles: implementer (sequential: 1zyc1 then 1zyc2)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-10-06

## Wave Summary

Wave `1zyc3` (Attested Approvals And Profile Goldens) delivered two changes: Approvals Carry No Person Name and The Tool-Surface Golden Covers Only The Shipped Declaration. Notable adjustments during implementation: Approvals Carry No Person Name: Readiness review folded in: no default name (B1, B3); request-time validation before replay, with `Cc`/`Cf`, bidi, zero-width, line separators and markdown-breaking characters refused (B2, N4); keyword-argument path and evidence-key protection (N3); handle-only rendering unchanged (N2); pinned schema tests added to serialization (N1); older-version read noted (N5); The Tool-Surface Golden Covers Only The Shipped Declaration: Readiness review folded in: tuple coercion of JSON lists (N6); each golden boots shipped-empty plus that asset alone with layout parts ignored; separate test class with a subtest per asset (N7); "plus the active asset" removed as redundant.

**Changes delivered:**

- **Approvals Carry No Person Name** (`1zyc1-enh self-attested-approval-names`) — 4 ACs completed. Key decisions: Record a name only when the caller supplies `attested_by`; no default; Delivery review: also refuse lone surrogates (`Cs`), `[`, `]` and a backslash, beyond Requirement 2's minimum set
- **The Tool-Surface Golden Covers Only The Shipped Declaration** (`1zyc2-enh tool-surface-golden-per-profile`) — 4 ACs completed. Key decisions: Full per-profile surface, not a delta against the shipped golden; Iterate declaring profile assets in the default suite
## Watchpoints

- Watchpoint: 1zyc1 adds a `wf_review_event` parameter, which changes the shipped tool-surface golden; implement 1zyc1 first and regenerate all goldens after it so 1zyc2's profile fixtures include the new parameter.
- Watchpoint: both changes add a CHANGELOG Added bullet; one owner edits it.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1 | do_now | no | completed | — |
| DEL-2 | do_now | no | completed | — |
| DEL-3 | do_now | no | pending | — |
| DEL-4 | do_now | no | pending | — |
| DEL-5 | do_now | no | pending | — |
| DEL-6 | do_now | no | pending | — |

*Machine review state — 6 findings; current: do_now 6, maybe_later 0, dont_do_later 0, not_issue 0*
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
| plan | 52 | 2,311,395 |
| implement | 42 | 992,038 |
| review | 35 | 226,818 |
| **Total** | **129** | **3,530,251** |

<!-- wave:context-efficiency-state {"generation":94,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":42,"content_source_credit":1002734,"derived_artifact_credit":288,"direct_net":992038,"estimated_tokens_saved":992038,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2024,"response_debit":10096,"source_credit_count":9,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1136},"plan":{"calls":52,"content_source_credit":2413596,"derived_artifact_credit":3621,"direct_net":2311395,"estimated_tokens_saved":2311395,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3077,"response_debit":106554,"source_credit_count":78,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":35,"content_source_credit":294866,"derived_artifact_credit":3046,"direct_net":226818,"estimated_tokens_saved":226818,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8809,"response_debit":64601,"source_credit_count":46,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":129,"content_source_credit":3711196,"derived_artifact_credit":6955,"direct_net":3530251,"estimated_tokens_saved":3530251,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13910,"response_debit":181251,"source_credit_count":133,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7261},"wave_id":"1zyc3 attested-approvals-and-profile-goldens"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
