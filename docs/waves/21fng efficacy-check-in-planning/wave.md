# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-23
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21fng efficacy-check-in-planning`
Title: Efficacy Check In Planning

## Objective

Planners and reviewers test whether a plan's mechanism will achieve its goal, not only whether the plan is internally consistent: a short, proportional efficacy check in every new plan, a standing replay-and-failure question for readiness and plan reviews, and a success measure carried to close. Boundaries: guidance and template only; no new gate, lane, signoff or blocking lint.

## Changes

Change ID: `21fnf-enh efficacy-check-in-planning-and-review`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator (Claude Code primary)
- Write-owning roles: implementer
- Requested review lanes: qa-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-10-23

## Wave Summary

Wave `21fng` (Efficacy Check In Planning) delivered one change: Efficacy Check in Planning and Review. Notable adjustments during implementation: Efficacy Check in Planning and Review: Readiness round 1 redesign: the plan's own efficacy check failed review. Seed 170 already required code-grounded execution that planners skipped; the self-hosted plan-change prompt lacks that block; Review plan is optional; AC-5 could not fail. Redesigned to the reviewer's cheaper path: one bullet in the existing block, carry the block into the prompt agents read, a fixed primer replay, the close measure; template section, Review plan and seed 209 edits dropped; AC-5 rebuilt with a held-out case, a false-flag control, two runs per arm and a pre-stated negative reading; 21bzn removed from the Rationale; harness review recorded in `evidence/`.

Intent outcome: partial. The guidance is delivered and pinned: the plan-change prompt agents read now carries the Code-grounded authoring block with the Mechanism efficacy bullet and a pointer to it before selection, every primer carrier carries the efficacy replay and each seat's duty to engage with it, and close asks for the plan's measure of success (EfficacyCheckCarrierTests; 28 and 51 independent mutants killed; full suite 12080 tests OK). The behaviour change is not established. The plan's measure of success was AC-5 now and mechanism-class readiness amendments per change later. AC-5 was inconclusive: a safety classifier stopped every baseline run for the held-out and control cases, and the new arm's 2 of 2 detection has no comparison. It was marked complete by operator direction. The later measure cannot be read yet, because its before-figure has not been taken. Limitations: rote replays are unenforced by design, waves without `wave_review.enabled` never run the primer, and no test pins a target's rendered copy.

**Changes delivered:**

- **Efficacy Check in Planning and Review** (`21fnf-enh efficacy-check-in-planning-and-review`) — 6 ACs completed. Key decisions: One efficacy bullet in the existing Code-grounded authoring block, carried into the plan-change prompt agents read, plus a fixed replay in the red-team primer and a close measure
## Watchpoints

- Watchpoint: seed edits need `seed_edit_allowed` opened and closed around them.
- Follow-up: the harness items (session brief, failure fingerprints, sandbox guidance) and the ledger-metrics report are planned separately as the first users of the new section.

## Review Checkpoints

Intent outcome: partial. The guidance is delivered and pinned: the plan-change prompt agents read now carries the Code-grounded authoring block with the Mechanism efficacy bullet and a pointer to it before selection, every primer carrier carries the efficacy replay and each seat's duty to engage with it, and close asks for the plan's measure of success (EfficacyCheckCarrierTests; 28 and 51 independent mutants killed; full suite 12080 tests OK). The behaviour change is not established. The plan's measure of success was AC-5 now and mechanism-class readiness amendments per change later. AC-5 was inconclusive: a safety classifier stopped every baseline run for the held-out and control cases, and the new arm's 2 of 2 detection has no comparison. It was marked complete by operator direction. The later measure cannot be read yet, because its before-figure has not been taken. Limitations: rote replays are unenforced by design, waves without `wave_review.enabled` never run the primer, and no test pins a target's rendered copy.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| CODE-DEL-1 | do_now | no | completed | code-reviewer, qa-reviewer |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
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
| plan | 16 | 852,135 |
| implement | 47 | 0 |
| review | 34 | 2,673,352 |
| **Total** | **97** | **3,525,487** |

<!-- wave:context-efficiency-state {"generation":97,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":47,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-6280,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1659,"response_debit":8507,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3886},"plan":{"calls":16,"content_source_credit":869725,"derived_artifact_credit":2387,"direct_net":852135,"estimated_tokens_saved":852135,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1859,"response_debit":22546,"source_credit_count":23,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4428},"review":{"calls":34,"content_source_credit":2760072,"derived_artifact_credit":1304,"direct_net":2673352,"estimated_tokens_saved":2673352,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5126,"response_debit":86133,"source_credit_count":61,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3235}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":97,"content_source_credit":3629797,"derived_artifact_credit":3691,"direct_net":3519207,"estimated_tokens_saved":3525487,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8644,"response_debit":117186,"source_credit_count":84,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11549},"wave_id":"21fng efficacy-check-in-planning"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 3 | 0 | 3 | 3,786,982 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":3,"estimated_exploration_avoided":3786982,"surfaced_events":3} -->
<!-- wave:exploration-avoided end -->
