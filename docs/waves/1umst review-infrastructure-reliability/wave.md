# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-06
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1umst review-infrastructure-reliability`
Title: Review Infrastructure Reliability

## Objective

Restore trustworthy review operations by making policy receipts reflect their
actual inputs, making lifecycle review requests recoverable, and preserving
review-evidence semantics and wave-scoped retrieval posture.

## Changes

Change ID: `1ujtt-bug review-policy-receipt-integrity`
Change Status: `implemented`

Change ID: `1ullt-bug review-lifecycle-input-affordances`
Change Status: `implemented`

Change ID: `1ulls-bug review-evidence-semantics-and-posture-scope`
Change Status: `implemented`

Change ID: `1uo2w-bug background-refresh-reaper-test-race`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer, wave-coordinator
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-08-07

## Wave Summary

Wave `1umst` (Review Infrastructure Reliability) delivered 4 changes: Review Policy Receipt Integrity, Review Lifecycle Input Affordances, Review Evidence Semantics and Retrieval-Posture Scope, and Deterministic Background Refresh Reaper Test. Notable adjustments during implementation: Review Policy Receipt Integrity: **Undisclosed governance change found by independent delivery review and now made deliberate.** `normalize_review_tracking_status` made `Change Status` digest-neutral, which reversed a rule two tests pinned on purpose: advancing a change to `complete` previously superseded the receipt and lapsed the readiness roster. The reversal shipped with no disclosure and both tests red, while three ACs claimed the suites pass. Operator decision recorded below: keep the new behavior. Tests rewritten to pin it, not deleted, plus a new test naming the rule directly with a Scope-edit negative control.; Review Evidence Semantics and Retrieval-Posture Scope: Preserved submitted repair judgments, clarified repaired-vs-unresolved approvals, and scoped posture counts to admitted targets.

**Changes delivered:**

- **Review Policy Receipt Integrity** (`1ujtt-bug review-policy-receipt-integrity`) — 7 ACs completed. Key decisions: Use one canonical body for both lane scoring and digesting.; Retain corrected legacy fallback rather than remove it.
- **Review Lifecycle Input Affordances** (`1ullt-bug review-lifecycle-input-affordances`) — 7 ACs completed. Key decisions: Parse a logical verdict, not one physical line.; Derive caller guidance from validation registries.
- **Review Evidence Semantics and Retrieval-Posture Scope** (`1ulls-bug review-evidence-semantics-and-posture-scope`) — 6 ACs completed. Key decisions: Preserve valid caller judgment rather than silently derive replacements.; Separate unresolved-work blocking from repaired-finding acceptance.
- **Deterministic Background Refresh Reaper Test** (`1uo2w-bug background-refresh-reaper-test-race`) — 3 ACs completed. Key decisions: Use `waitid(..., WNOWAIT)` in the POSIX test.
## Watchpoints

- Watchpoint: `1ullt` must serialize its status-transition formatter integration with the
  separately planned `1ul77` allowed-values work.
- Watchpoint: policy evaluator changes require both direct regression coverage and a public
  prior-receipt convergence test.

## Review Checkpoints

- Prepare review is pending: code-reviewer, qa-reviewer, docs-contract-reviewer,
  and the Wave Council readiness synthesis.
- **Prepare-phase Wave Council [prepare-council] — 2026-08-06: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, code-reviewer, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: receipt binding must change for real policy scope changes while council rotation and lifecycle bookkeeping do not lapse valid approvals; strongest-alternative: remove legacy fallback scoring entirely)

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| false-independence-delivery-approvals | do_now | no | completed | code-reviewer, qa-reviewer, docs-contract-reviewer, wave-council-delivery, operator-signoff |
| legacy-extension-boundary-false-positive | do_now | no | completed | code-reviewer, qa-reviewer, wave-council-delivery |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 69 | 1,455,467 |
| implement | 105 | 851,509 |
| review | 261 | 6,894,549 |
| **Total** | **435** | **9,201,525** |

<!-- wave:context-efficiency-state {"generation":433,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":105,"content_source_credit":926514,"derived_artifact_credit":251,"direct_net":851509,"estimated_tokens_saved":851509,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4180,"response_debit":74999,"source_credit_count":13,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3923},"plan":{"calls":69,"content_source_credit":1646406,"derived_artifact_credit":3283,"direct_net":1455467,"estimated_tokens_saved":1455467,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3720,"response_debit":198001,"source_credit_count":52,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7499},"review":{"calls":261,"content_source_credit":7943030,"derived_artifact_credit":3646,"direct_net":6894549,"estimated_tokens_saved":6894549,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":28184,"response_debit":1025289,"source_credit_count":218,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":435,"content_source_credit":10515950,"derived_artifact_credit":7180,"direct_net":9201525,"estimated_tokens_saved":9201525,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":36084,"response_debit":1298289,"source_credit_count":283,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12768},"wave_id":"1umst review-infrastructure-reliability"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 53 | 0 | 7 | 28,132,180 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":7,"estimated_exploration_avoided":28132180,"surfaced_events":53} -->
<!-- wave:exploration-avoided end -->
