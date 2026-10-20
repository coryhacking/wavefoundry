# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-19
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `216g7 precision-reguard-test-and-readme-stage-names`
Title: Precision Reguard Test And Readme Stage Names

## Objective

Maintainers get a failing test if either graph-only precision re-guard is removed, and distribution readers see lifecycle stage names instead of renameable shortcut phrases in the framework README. Test and documentation only; no product behaviour changes.

## Changes

Change ID: `216g6-debt precision-reguard-test-and-readme-stage-names`
Change Status: `implemented`

## Participants

- Coordinator: main session
- Write-owning roles: implementer
- Requested review lanes: qa-reviewer
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-19

## Wave Summary

Wave `216g7` (Precision Reguard Test And Readme Stage Names) delivered one change: Test the unprovenanced-escalation precision re-guard; drop shortcut names from the README diagrams. Notable adjustments during implementation: Test the unprovenanced-escalation precision re-guard; drop shortcut names from the README diagrams: Implemented. Added `test_graph_only_unprovenanced_escalation_keeps_the_guard` (completed store, docs chunks and vectors deleted, `docs` kept in `content`, docs dropped from `model_versions`; code recorded full, int8 predicted). Scratch mutants: removing the re-guard after the `_unprovenanced` escalation fails only the new test; removing the model-set re-guard fails only `test_graph_only_model_name_change_still_widens_and_keeps_the_guard`. README diagrams, one-line flow and stage list now use stage names, with a pointer to `docs/prompts/index.md`; case-insensitive grep for each Requirement 3 phrase finds nothing. Gapfill: shell grep/sed used for helper lookup, README rewrite and mutant setup.

**Changes delivered:**

- **Test the unprovenanced-escalation precision re-guard; drop shortcut names from the README diagrams** (`216g6-debt precision-reguard-test-and-readme-stage-names`) — 3 ACs completed. Key decisions: Test the second re-guard site; leave the code as it is.; Reword the README rather than render it from the profile.
## Watchpoints

- Watchpoint: open `framework_edit_allowed` before framework edits, whatever the edit tool, and close it after.
- Watchpoint: the re-guard mutant must be the only change in its scratch copy; a fixture that trips the 1sed6 escalation alone proves nothing.

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

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 15 | 47,067 |
| implement | 20 | 192,516 |
| review | 7 | 21,456 |
| **Total** | **42** | **261,039** |

<!-- wave:context-efficiency-state {"generation":42,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":20,"content_source_credit":211082,"derived_artifact_credit":0,"direct_net":192516,"estimated_tokens_saved":192516,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":628,"response_debit":18418,"source_credit_count":4,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":480},"plan":{"calls":15,"content_source_credit":65673,"derived_artifact_credit":2425,"direct_net":47067,"estimated_tokens_saved":47067,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2031,"response_debit":23428,"source_credit_count":27,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4428},"review":{"calls":7,"content_source_credit":30698,"derived_artifact_credit":1084,"direct_net":21456,"estimated_tokens_saved":21456,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1697,"response_debit":11843,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3214}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":42,"content_source_credit":307453,"derived_artifact_credit":3509,"direct_net":261039,"estimated_tokens_saved":261039,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4356,"response_debit":53689,"source_credit_count":41,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8122},"wave_id":"216g7 precision-reguard-test-and-readme-stage-names"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 2 | 0 | 2 | 850,395 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":850395,"surfaced_events":2} -->
<!-- wave:exploration-avoided end -->
