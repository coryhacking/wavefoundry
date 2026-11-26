# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-25
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `24a51 memory-validate-single-line`
Title: Memory Validate Single Line

## Objective

Anyone reading or editing a memory record sees each `Action delta:`, `Validation rationale:` and `Validated by:` value on one line, whichever tool wrote it: `memory_validate` adopts the same single-line rule `memory_add` and `memory_consolidate` already use. All three tools also refuse an `action_delta` or rationale over 5,000 characters. Other `memory_validate` behavior is unchanged.

## Changes

Spec ID: `24a50-enh memory-validate-single-line-rule`
Spec Status: `implemented`

## Participants

- Coordinator: coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-11-25

## Wave Summary

Wave `24a51` (Memory Validate Single Line) delivered one change: memory_validate Uses the Single-Line Rule, and Rationale Lines Get a Size Cap.

Intent outcome: All three tools reject oversized stripped explanations, and validation refuses line separators before writing. The registered tools accept exactly 5,000 stripped characters and report both violations when an oversized field also contains a line break. Reviewers verified byte-identical records after refusal.

**Changes delivered:**

- **memory_validate Uses the Single-Line Rule, and Rationale Lines Get a Size Cap** (`24a50-enh memory-validate-single-line-rule`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6 and AC-7 completed. Key decisions: Fold a 5,000-character cap on `action_delta` and the rationale field into this change, at all three tools; Use `memory_single_line` on the raw value in both `memory_validate` checks and keep their existing messages.

## Watchpoints

- Watchpoint: framework script edits need `framework_edit_allowed`; this change flips `RationaleInputTests.test_ac8_memory_validate_rewrite_still_accepts_its_own_values` delivered by closed wave `24bik`.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| CR-D1 | do_now | no | completed | code-reviewer |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | Phase | State | Why | Next action |
| --- | --- | --- | --- | --- |
| council-readiness | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

Readiness confirmed the existing council and four specialist approvals. The implementer owns the validation rule, contract entries and focused tests. Delivery uses a full-depth adversarial primer on input validation, then independent role reviews and council synthesis.

2026-11-25: Intent outcome: All three tools reject oversized stripped explanations, and validation refuses line separators before writing. The registered tools accept exactly 5,000 stripped characters and report both violations when an oversized field also contains a line break. Reviewers verified byte-identical records after refusal.

The red-team primer raised overlapping failures. Code review showed that reporting only the line error required a second correction. After CR-D1, architecture, QA, security and reality-checker verified the repair. Security also considered alternatives as the rotating seat. Docs-contract verified the registered tools against their three entries. The chair judged that delivery establishes the intent after the qualifying suite passed.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 26 | 693,425 |
| implement | 35 | 386,933 |
| review | 28 | 711,776 |
| **Total** | **89** | **1,792,134** |

<!-- wave:context-efficiency-state {"generation":90,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":35,"content_source_credit":449606,"derived_artifact_credit":0,"direct_net":386933,"estimated_tokens_saved":386933,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1054,"response_debit":65042,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3423},"plan":{"calls":26,"content_source_credit":768036,"derived_artifact_credit":2610,"direct_net":693425,"estimated_tokens_saved":693425,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4581,"response_debit":88261,"source_credit_count":34,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":15621},"review":{"calls":28,"content_source_credit":761977,"derived_artifact_credit":1546,"direct_net":711776,"estimated_tokens_saved":711776,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4156,"response_debit":54520,"source_credit_count":29,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6929}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":89,"content_source_credit":1979619,"derived_artifact_credit":4156,"direct_net":1792134,"estimated_tokens_saved":1792134,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9791,"response_debit":207823,"source_credit_count":75,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":25973},"wave_id":"24a51 memory-validate-single-line"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 3 | 0 | 3 | 3,658,858 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":3,"estimated_exploration_avoided":3658858,"surfaced_events":3} -->
<!-- wave:exploration-avoided end -->
