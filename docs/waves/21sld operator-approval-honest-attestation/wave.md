# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-27
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21sld operator-approval-honest-attestation`
Title: Operator Approval Honest Attestation

## Objective

Operator sign-offs record an approval of the reviewed scope without asserting test evidence the operator never produced. Specialist and council attestation, the close gate and historical ledgers are unchanged.

## Changes

Change ID: `21qbb-bug operator-approval-forced-integrity-claims`
Change Status: `implemented`

## Participants

- Coordinator: main session
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-10-27

## Wave Summary

Wave `21sld` (Operator Approval Honest Attestation) delivered one change: Operator approvals stop asserting checks nobody ran. Notable adjustments during implementation: Operator approvals stop asserting checks nobody ran: Implemented under `framework_edit_allowed`, with seed 209 under `seed_edit_allowed`; both gates are closed. `review_evidence.py`: `OPERATOR_APPROVAL_INTEGRITY_DEFAULT` and `is_operator_approval_record` (actor `operator` AND `claim_id == approval:operator-signoff`). The approval branch of `build_compact_review_event` takes optional checks for operator sign-off, validated with `executed=False`, and gives operator approvals their own `expected` and failure text. The `_validate_evidence_shape` executed-integrity rule exempts only `is_operator_approval_record`. The approval-action operator filter also strips `integrity_checks`, and `REVIEW_ACTION_CALLER_INPUTS` is unchanged. `normalize_review_event_request` defaults are deliberately unchanged: they only feed the replay digest, so an identical retry of an existing operator approval still replays. Docs: `wf_review_event` docstring (two sentences) with only that handler's digest refreshed, `docs/specs/mcp-tool-surface.md`, and seed 209 narrowed in place plus field-table and approval-evidence clauses. Tests: `OperatorApprovalHonestAttestationTests` (7) build the delivery run and approvals through `build_identified_review_event`. Mutants: dropping the actor half, dropping the claim half, `executed=True` in the builder, the old expected text, the reverted action filter, removing the validator exemption and the reverted seed sentence each fail. Owning files `test_review_evidence`, `test_lifecycle_gates`, `test_council_signoff_keys`, `test_mcp_tool_registry`, `test_intent_fit_approvals` and `test_server_package` ran 344 tests, OK. AC-4: full docs validation passes via MCP and as a fresh-process `wf docs-lint`, which validates every committed ledger, including about 670 old-shape operator approvals. The spec text is under `docs/`, not the packaged framework, so the AC-6 text assertions cover the seed and docstring and the spec is left to docs review.; Operator approvals stop asserting checks nobody ran: Readiness repair after the red-team primer. The primer found two gaps: operator records kept default text claiming independent verification, and the seed 209 "do not approve" sentence, the docstring and `mcp-tool-surface.md` contract text would become false. Both are now in R2/R6, AC-1/AC-6 and scope. AC-5 now targets the existing operator filter in the approval-action builder. AC-3 names the operator-actor finding known-bad. The primer census found no reader of the integrity booleans or `execution_status` outside `review_evidence.py` (dashboard follows the validator), and 670 committed operator approvals, all old shape.

**Changes delivered:**

- **Operator approvals stop asserting checks nobody ran** (`21qbb-bug operator-approval-forced-integrity-claims`) — 6 ACs completed. Key decisions: Keep `execution_status: "executed"` for operator approvals and store honest `false` checks under a narrow operator predicate.
## Watchpoints

- Watchpoint: framework edits need `framework_edit_allowed`, and the seed 209 sentence needs `seed_edit_allowed`; close each gate after use.
- Watchpoint: run the canonical suite last; any framework edit after it rotates the receipt.

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
| plan | 19 | 466,868 |
| implement | 33 | 1,061,209 |
| review | 22 | 0 |
| **Total** | **74** | **1,528,077** |

<!-- wave:context-efficiency-state {"generation":70,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":33,"content_source_credit":1075542,"derived_artifact_credit":0,"direct_net":1061209,"estimated_tokens_saved":1061209,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":863,"response_debit":17258,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3788},"plan":{"calls":19,"content_source_credit":495520,"derived_artifact_credit":2547,"direct_net":466868,"estimated_tokens_saved":466868,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4424,"response_debit":31828,"source_credit_count":19,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5053},"review":{"calls":22,"content_source_credit":65308,"derived_artifact_credit":1762,"direct_net":-7074,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6096,"response_debit":71737,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3689}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":74,"content_source_credit":1636370,"derived_artifact_credit":4309,"direct_net":1521003,"estimated_tokens_saved":1528077,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11383,"response_debit":120823,"source_credit_count":53,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12530},"wave_id":"21sld operator-approval-honest-attestation"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 6 | 0 | 6 | 2,462,368 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":6,"estimated_exploration_avoided":2462368,"surfaced_events":6} -->
<!-- wave:exploration-avoided end -->
