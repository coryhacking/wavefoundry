# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-19
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `23td0 downstream-lifecycle-compatibility`
Title: Downstream Lifecycle Compatibility

## Objective

Downstream teams can use commented plan templates without losing visible review targets or tasks, keep their established planning vocabulary when rendering an upgrade, and identify open work whose older delivery approvals lack a criterion-status baseline. Dashboard readers can scan numbered requirements and progress counts and recognize their planning workflow in the lifecycle diagram.

## Changes

Change ID: `23tcx-bug ignore-commented-lifecycle-headings`
Change Status: `implemented`

Change ID: `23tcy-bug preserve-distribution-planning-names`
Change Status: `implemented`

Change ID: `23tcz-enh report-legacy-delivery-approval-coverage`
Change Status: `implemented`

Change ID: `23td1-bug render-numbered-dashboard-requirements`
Change Status: `implemented`

## Participants

- Coordinator: Lifecycle coordinator
- Write-owning roles: One implementer per admitted spec, with shared files edited sequentially
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-11-19

## Wave Summary

Wave `23td0` (Downstream Lifecycle Compatibility) delivered 4 changes: Ignore hidden headings when reading lifecycle documents, Preserve distribution planning names, Flag legacy delivery approvals during upgrade, and Make dashboard requirements and lifecycle progress readable.

Intent outcome: Achieved on the tested public paths. Independent QA verified all 14 required criteria across the four changes. Prepare restored a target-driven reviewer after a commented heading, Close retained visible blockers, and a single process resolved checkout A, B and A to their own planning routes. Registered upgrade returned 100 affected records and counted 10 omitted. Its real log contained all 110 records and both signoff keys for each. Chrome displayed four numbered requirements with inline code. The four progress rows cleared their bars at 375 and 1440 pixels, and Tab exposed each row’s own breakdown. The shipped Plan spec dialog opened. The implementation replay exercised the custom stage dialog, and independent tests verified its selected-root shortcut. An actual Waveforge deployment and native Windows browser were outside the verification.

**Changes delivered:**

- **Ignore hidden headings when reading lifecycle documents** (`23tcx-bug ignore-commented-lifecycle-headings`) — AC-1, AC-2, AC-3 and AC-4 completed. Key decisions: Share comment visibility among lifecycle readers while retaining original source positions.
- **Preserve distribution planning names** (`23tcy-bug preserve-distribution-planning-names`) — AC-1, AC-2 and AC-3 completed. Key decisions: Preserve established registrations and derive defaults only where a fresh custom profile has no established name.
- **Flag legacy delivery approvals during upgrade** (`23tcz-enh report-legacy-delivery-approval-coverage`) — AC-1, AC-2 and AC-3 completed. Key decisions: Identify affected open records at upgrade and explain when to renew approval.
- **Make dashboard requirements and lifecycle progress readable** (`23td1-bug render-numbered-dashboard-requirements`) — AC-1, AC-2, AC-3 and AC-4 completed. Key decisions: Extend the shared renderer.

## Watchpoints

- Watchpoint: preserve machine identifiers, existing review authority and generated HTML marker regions. Coordinate edits to shared lifecycle, review and upgrade files.
- Waveforge also asked about two existing contracts. Explicit operator direction governs retained-work deletion. A specialist security readiness approval may use a scoped known-bad rationale when that lane has no affected surface. Both behaviors remain in force.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| delivery-commented-status | do_now | no | completed | qa-reviewer, code-reviewer, release-reviewer, council-delivery |
| delivery-inline-block-boundary | do_now | no | completed | qa-reviewer, code-reviewer, council-delivery |
| delivery-record-status-authority | do_now | no | completed | docs-contract-reviewer, architecture-reviewer, council-delivery |
| delivery-selected-root-manifest | do_now | no | completed | security-reviewer, architecture-reviewer, code-reviewer, council-delivery |
| readiness-upgrade-boundaries | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer, council-readiness |

*Machine review state — 5 findings; current: do_now 5, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

The current policy assigns a standard-depth red-team primer and a rotating documentation-contract seat. Six specialist lanes check their respective obligations. The chair synthesizes their findings.

Prepare wave passed focused verification on receipt `review-policy-34776e3b562321ecb8fb`. The initial review found missing upgrade controls for old receipts, per-checkout prompt names and incomplete coverage reporting. The author amended the three specs once. Fresh reviewers verified the old evaluator transition, A/B/A name resolution and mixed affected, clean and unreadable records. The six required lanes and council approved readiness. Delivery remains pending.

2026-11-19: Intent outcome: Achieved on the tested public paths. Independent QA verified all 14 required criteria across the four changes. Prepare restored a target-driven reviewer after a commented heading, Close retained visible blockers, and a single process resolved checkout A, B and A to their own planning routes. Registered upgrade returned 100 affected records and counted 10 omitted. Its real log contained all 110 records and both signoff keys for each. Chrome displayed four numbered requirements with inline code. The four progress rows cleared their bars at 375 and 1440 pixels, and Tab exposed each row’s own breakdown. The shipped Plan spec dialog opened. The implementation replay exercised the custom stage dialog, and independent tests verified its selected-root shortcut. An actual Waveforge deployment and native Windows browser were outside the verification.

2026-11-19: Delivery council approved after a standard-depth red-team primer and the rotating documentation-contract seat. Six specialist lanes approved the final tree. The reviewers initially withheld approval for the H3 inline-code boundary, external prompt manifest reads, a hidden status that concealed an open wave, and prose or ambiguous status that suppressed approval guidance. Registered Prepare, current-wave discovery, upgrade cleanup, Review and Close dry-run and the dashboard snapshot replayed the respective repairs. The release reviewer verified evaluator 8 from the candidate ZIP and its extracted installation. Two final fixture corrections passed independent negative controls on the frozen 42-file fingerprint `5948fff1219bfbcf8a394ab287bc73ee32a34f74`. The full framework run passed 13,079 tests across 251 files with 12 skips in 662.437 seconds.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 57 | 1,193,663 |
| implement | 43 | 349,648 |
| review | 292 | 5,717,435 |
| **Total** | **392** | **7,260,746** |

<!-- wave:context-efficiency-state {"generation":385,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":43,"content_source_credit":357444,"derived_artifact_credit":1272,"direct_net":349648,"estimated_tokens_saved":349648,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1582,"response_debit":13642,"source_credit_count":7,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6156},"plan":{"calls":57,"content_source_credit":1311712,"derived_artifact_credit":5630,"direct_net":1193663,"estimated_tokens_saved":1193663,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6734,"response_debit":127169,"source_credit_count":48,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10224},"review":{"calls":292,"content_source_credit":6666319,"derived_artifact_credit":4161,"direct_net":5717435,"estimated_tokens_saved":5717435,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":35445,"response_debit":924162,"source_credit_count":168,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6562}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":392,"content_source_credit":8335475,"derived_artifact_credit":11063,"direct_net":7260746,"estimated_tokens_saved":7260746,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":43761,"response_debit":1064973,"source_credit_count":223,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":22942},"wave_id":"23td0 downstream-lifecycle-compatibility"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 56 | 0 | 25 | 17,557,214 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":25,"estimated_exploration_avoided":17557214,"surfaced_events":56} -->
<!-- wave:exploration-avoided end -->
