# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-27
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21s6f operator-signoff-checks-not-applicable`
Title: Operator Signoff Checks Not Applicable

## Objective

An operator sign-off records "not applicable" (`null`) for integrity checks the operator never ran, and agents never ask the operator for check values. An operator who did check can still record `true` or `false`. Specialist and council attestation, the close gate and every historical record are unchanged.

## Changes

Change ID: `21s53-enh operator-signoff-checks-not-applicable`
Change Status: `implemented`

## Participants

- Coordinator: main session
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-10-27

## Wave Summary

Wave `21s6f` (Operator Signoff Checks Not Applicable) delivered one change: Operator sign-off integrity checks read as not applicable. Notable adjustments during implementation: Operator sign-off integrity checks read as not applicable: Implemented under `framework_edit_allowed`, with seed 209 under `seed_edit_allowed`; both gates are closed. `review_evidence.py`: `OPERATOR_APPROVAL_INTEGRITY_DEFAULT` booleans are `None`. `_validated_integrity_checks` gains `allow_not_applicable`, passed only for an operator sign-off request. Elsewhere a `null` value gets the specific refusal "must be boolean: null (not applicable) is accepted only on an operator-signoff approval". `_validate_evidence_shape` splits the five integrity fields out of the boolean loop and allows `null` only under `_accepts_not_applicable_integrity` (`claim_kind == "approval"` and `is_operator_approval_record`). Its executed-integrity message now says "false or null (not applicable)". `review_action_input_schema` marks each integrity boolean with `null_allowed_for: ["operator-signoff"]` and `null_meaning: "not applicable"`, and both lifecycle golden fixtures were re-pinned for exactly those 15 entries. `normalize_review_event_request` takes the `null` default from the same constant. Contract text: seed 209 (five field-table rows, the integrity paragraph with "Do not ask the operator for check values", the approval-evidence bullet), both `wf_review_event` docstring sites, and the spec integrity bullet. The handler-digest pin was refreshed for `wf_review_event` only. The frozen ledger pin did not move. Its fixture supplies all-true checks, as the QA readiness reviewer predicted. Tests in `OperatorApprovalHonestAttestationTests`: AC-1 null default, AC-2 stated true/false/null plus string and missing-field refusals, AC-3 write time (specialist, council, operator-actor finding, wrong-actor `operator-signoff`; null-specific message asserted) and read time (actor, claim, `claim_kind` alone), AC-4 `false` and `true` operator records, AC-5 fingerprint with `None`, AC-6 seed and docstring text. Eight scratch-copy mutants were all killed: request predicate drops actor, record predicate drops `claim_kind`, record allows all, write allows all, default back to `False`, findings allow `null`, schema back to plain boolean, seed sentence reverted. The unmutated scratch baseline passes. AC-4: fresh-process `wf docs-lint` over every committed ledger is ok. Canonical suite: 12,270 tests, 12 existing skips, OK, fresh receipt.; Operator sign-off integrity checks read as not applicable: Readiness repair after the red-team primer. No blocking findings. Added: the two lifecycle golden fixtures that pin the input schema (scope, R7, Serialization Points); every seed 209 and docstring site (R6, AC-6); the operator-actor finding and non-operator `operator-signoff` request cases (AC-3); `claim_kind == "approval"` in the read-time allowance (R3); a Risks row for retry of a `21sld`-default record; AC-4 labelled a regression guard. Declined: defaulting the method on supplied checks, and refusing supplied `null` (Decision Log). Serialization verified by the primer: `canonical_review_event_bytes` and `parse_review_event_bytes` round-trip `null`. No prompt or skill tells agents to collect operator check values.

**Changes delivered:**

- **Operator sign-off integrity checks read as not applicable** (`21s53-enh operator-signoff-checks-not-applicable`) — 6 ACs completed. Key decisions: Store `null` per boolean as "not applicable" on operator sign-offs, and allow `true`/`false`/`null` when supplied.; Agents never ask the operator for check values; omit `integrity_checks` unless the operator states them.
## Watchpoints

- Watchpoint: framework edits need `framework_edit_allowed`, and the seed 209 sentence needs `seed_edit_allowed`; close each gate after use.
- Watchpoint: run the canonical suite last; any framework edit after it rotates the receipt.
- Watchpoint: the live MCP server runs pre-change code until a `/mcp` reconnect; the operator should reconnect before the sign-off so the new `null` default is exercised.

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
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
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
| plan | 14 | 50,646 |
| implement | 42 | 327,796 |
| review | 26 | 246,531 |
| **Total** | **82** | **624,973** |

<!-- wave:context-efficiency-state {"generation":83,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":42,"content_source_credit":397957,"derived_artifact_credit":1041,"direct_net":327796,"estimated_tokens_saved":327796,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3032,"response_debit":69106,"source_credit_count":59,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":936},"plan":{"calls":14,"content_source_credit":69243,"derived_artifact_credit":2338,"direct_net":50646,"estimated_tokens_saved":50646,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2434,"response_debit":23554,"source_credit_count":25,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5053},"review":{"calls":26,"content_source_credit":345624,"derived_artifact_credit":1432,"direct_net":246531,"estimated_tokens_saved":246531,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2946,"response_debit":101268,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3689}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":82,"content_source_credit":812824,"derived_artifact_credit":4811,"direct_net":624973,"estimated_tokens_saved":624973,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8412,"response_debit":193928,"source_credit_count":104,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9678},"wave_id":"21s6f operator-signoff-checks-not-applicable"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 6 | 0 | 6 | 3,315,940 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":6,"estimated_exploration_avoided":3315940,"surfaced_events":6} -->
<!-- wave:exploration-avoided end -->
