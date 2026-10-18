# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-18
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `210eb setup-readiness-config-notes`
Title: Setup Readiness Config Notes

## Objective

Setup readiness stops reporting `setup_inputs_changed` when only the `notes` prose in a hashed `docs/workflow-config.json` section changes. Real setting changes, framework sources and `VERSION` still trigger it.

## Changes

Change ID: `210ea-bug setup-readiness-ignores-config-notes`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-18

## Wave Summary

Wave `210eb` (Setup Readiness Config Notes) delivered one change: Setup readiness ignores configuration notes. Notable adjustments during implementation: Setup readiness ignores configuration notes: Implemented under `framework_edit_allowed`: `_configuration_identity` drops the top-level `notes` key of each dict section; the comparison text in `assess_setup` is unchanged. New test `test_setup_notes_edit_after_stamp_does_not_request_setup`. AC-2: with the filter removed in a scratch copy the test fails (`'action_required' != 'ready'`). Delivery code and QA lanes approved; QA mutants: filter removed, whole `setup` dropped and `setup` dropped beside the filter were caught, while a drop-all-strings filter and a non-dict section set to `None` were missed. The test then gained a string-valued setting and a list section, and both mutants are now caught. Gapfill: shell and scratch copies for mutants.

**Changes delivered:**

- **Setup readiness ignores configuration notes** (`210ea-bug setup-readiness-ignores-config-notes`) — 3 ACs completed. Key decisions: Drop only the top-level `notes` key per section.
## Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

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
| plan | 10 | 497 |
| implement | 16 | 0 |
| review | 8 | 15,178 |
| **Total** | **34** | **15,675** |

<!-- wave:context-efficiency-state {"generation":34,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":16,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-2484,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":461,"response_debit":2301,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":278},"plan":{"calls":10,"content_source_credit":9806,"derived_artifact_credit":1994,"direct_net":497,"estimated_tokens_saved":497,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1347,"response_debit":14224,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4268},"review":{"calls":8,"content_source_credit":24719,"derived_artifact_credit":1063,"direct_net":15178,"estimated_tokens_saved":15178,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1494,"response_debit":12164,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3054}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":34,"content_source_credit":34525,"derived_artifact_credit":3057,"direct_net":13191,"estimated_tokens_saved":15675,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3302,"response_debit":28689,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7600},"wave_id":"210eb setup-readiness-config-notes"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
