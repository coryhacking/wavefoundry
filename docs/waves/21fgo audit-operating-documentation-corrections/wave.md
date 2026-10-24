# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-22
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21fgo audit-operating-documentation-corrections`
Title: Audit Operating Documentation Corrections

## Objective

Agents and maintainers receive consistent current review, memory and tool guidance in the two active project references. Correct audit findings A3-A5 without changing executable policy.

## Changes

Change ID: `21evy-doc reconcile-review-memory-and-overview-guidance`
Change Status: `implemented`

## Participants

- Coordinator: Engineering coordinator
- Write-owning roles: implementer
- Requested review lanes: qa-reviewer, docs-contract-reviewer
- Required review lanes: qa-reviewer, docs-contract-reviewer

Completed At: 2026-10-24

## Wave Summary

Wave `21fgo` (Audit Operating Documentation Corrections) delivered one change: Reconcile review, memory and overview guidance. Notable adjustments during implementation: Reconcile review, memory and overview guidance: Independent delivery QA and docs-contract approvals recorded from one disclosed fresh context. Eight checks reject HEAD originals and pass current text; canonical policy, generated regions and unrelated content verified. All ACs/tasks met; no runtime behavior changed and no framework suite needed for prose-only scope.

**Changes delivered:**

- **Reconcile review, memory and overview guidance** (`21evy-doc reconcile-review-memory-and-overview-guidance`) — 4 ACs completed. Key decisions: Correct two owning project docs
## Watchpoints

- Watchpoint: preserve canonical lifecycle policy and unrelated documentation.
- Follow-up: pause after implementation/review; closure and commits remain operator-owned.

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
| plan | 60 | 270,934 |
| implement | 49 | 454,735 |
| review | 86 | 1,201,433 |
| **Total** | **195** | **1,927,102** |

<!-- wave:context-efficiency-state {"generation":161,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":49,"content_source_credit":565352,"derived_artifact_credit":0,"direct_net":454735,"estimated_tokens_saved":454735,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1710,"response_debit":111817,"source_credit_count":17,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2910},"plan":{"calls":60,"content_source_credit":462292,"derived_artifact_credit":3123,"direct_net":270934,"estimated_tokens_saved":270934,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6248,"response_debit":192661,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4428},"review":{"calls":86,"content_source_credit":1459890,"derived_artifact_credit":278,"direct_net":1201433,"estimated_tokens_saved":1201433,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6622,"response_debit":255348,"source_credit_count":48,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3235}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":195,"content_source_credit":2487534,"derived_artifact_credit":3401,"direct_net":1927102,"estimated_tokens_saved":1927102,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14580,"response_debit":559826,"source_credit_count":85,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10573},"wave_id":"21fgo audit-operating-documentation-corrections"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 18 | 0 | 11 | 13,629,651 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":11,"estimated_exploration_avoided":13629651,"surfaced_events":18} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

Readiness: standard red-team primer, independent architecture/security/QA/reality fixed seats and rotating docs-contract seat; all fixed seats explicitly weighed the alternative of replacing the whole checklist. Unanimous approval, no blocker. Kept the bounded correction with a canonical link and affirmative obligations: every actual pending memory candidate reviewed, zero new memories allowed with rationale, delivery Council selected by receipt/mode. Baseline probes detected the original universal table, forced journals, contradictory synthesis and obsolete ZIP. These are source-text checks, not runtime gate qualification.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-22 | Corrected the two declared docs; current full docs validation passes. Independent delivery review is running on frozen source. | Three baseline-fail/current-pass predicates; generated blocks unchanged; git blobs 8b690c275f724a5101ff3dea0de2813d58263ad7 and c2b84696fb2563ddb6c9630514a765430aa033e9 |

Delivery: fresh independent QA and docs-contract lanes shared one worker context (disclosed), separately approved after eight original-fail/current-pass textual controls and current canonical comparison. Two target fingerprints unchanged. No runtime/full-suite claim. All ACs and tasks are complete; implementation is done and this wave is paused pending operator-owned closure.
