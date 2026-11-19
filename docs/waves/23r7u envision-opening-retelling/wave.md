# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-18
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `23r7u envision-opening-retelling`
Title: Envision Opening Retelling

## Objective

An Envision author learns whether a fresh reader can explain who benefits and what becomes possible after reading the opening once. The existing reviewer supplies that evidence within the existing review and repair pass. Across project writing, readers can identify the specific outcome, whose evidence supports it and what remains to decide or do.

## Changes

Change ID: `23r7t-doc envision-opening-retelling`
Change Status: `implemented`

Change ID: `23ruk-doc concrete-claims-in-general-writing`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: documentation implementer
- Requested review lanes: qa-reviewer, docs-contract-reviewer
- Required review lanes: qa-reviewer, docs-contract-reviewer

Completed At: 2026-11-18

## Wave Summary

Wave `23r7u` (Envision Opening Retelling) delivered two changes: Check whether a reader can retell the vision and Make claims specific, attributable and useful.

**Changes delivered:**

- **Check whether a reader can retell the vision** (`23r7t-doc envision-opening-retelling`) — AC-1 completed.
- **Make claims specific, attributable and useful** (`23ruk-doc concrete-claims-in-general-writing`) — AC-1 and AC-2 completed.

## Watchpoints

- Watchpoint: The candidate prompt edits preceded formal readiness. Review the current wording prospectively for local testing. Human comprehension remains unmeasured.

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

## Review Checkpoints

### 23ruk implementation evidence

- 2026-11-18 — Readback: AC-1 and AC-2 apply the four checks in the shared writing guide to memory and handoff examples, preserving confidentiality, uncertainty, reusable requirements and meaningful endings.

- AC-2 memory exercise. Input: “Users want fewer reviews. Keep respondent identities private.” Edited: “One operator preferred a single vision document. Other operators’ preferences are unknown. Keep respondent identities private.” The edit narrows both the audience and the subject while retaining the reusable confidentiality instruction.
- AC-2 handoff exercise. Input: “Our framework improves delivery. The runner saves a receipt, ensuring reliable delivery. The release owner must check it before close. This is a great improvement.” Edited: “The runner records the suite result and framework input hash. Before close, the release owner must check that the suite passed for the current inputs.” The edited handoff drops the interchangeable claim, unsupported benefit and praise while retaining the owner and action.


## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 18 | 0 |
| implement | 42 | 0 |
| review | 34 | 41,210 |
| **Total** | **94** | **41,210** |

<!-- wave:context-efficiency-state {"generation":94,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":42,"content_source_credit":17822,"derived_artifact_credit":2544,"direct_net":-12022,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1131,"response_debit":34272,"source_credit_count":17,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3015},"plan":{"calls":18,"content_source_credit":10395,"derived_artifact_credit":841,"direct_net":-7608,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1712,"response_debit":26711,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9579},"review":{"calls":34,"content_source_credit":101321,"derived_artifact_credit":2236,"direct_net":41210,"estimated_tokens_saved":41210,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3864,"response_debit":64662,"source_credit_count":32,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6179}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":94,"content_source_credit":129538,"derived_artifact_credit":5621,"direct_net":21580,"estimated_tokens_saved":41210,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6707,"response_debit":125645,"source_credit_count":57,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":18773},"wave_id":"23r7u envision-opening-retelling"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
