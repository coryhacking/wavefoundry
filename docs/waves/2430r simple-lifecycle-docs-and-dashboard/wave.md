# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-22
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `2430r simple-lifecycle-docs-and-dashboard`
Title: Simple Lifecycle Docs And Dashboard

## Objective

A new reader, including one coming from Spec Kit, sees one accurate and simple wave and spec lifecycle in the README, the docs and the dashboard. The dashboard tiles stay simple, and each dialog says what you do, what runs automatically, when the councils run and which gates block. Text and presentation only; no behavior changes.

## Changes

Change ID: `2430q-enh simple-lifecycle-model-and-dashboard-dialogs`
Change Status: `implemented`

## Participants

- Coordinator: main session
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-11-22

## Wave Summary

Wave `2430r` (Simple Lifecycle Docs And Dashboard) delivered one change: One simple lifecycle model across the docs and the dashboard.

**Changes delivered:**

- **One simple lifecycle model across the docs and the dashboard** (`2430q-enh simple-lifecycle-model-and-dashboard-dialogs`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-10 and AC-11 completed. AC-9 deferred: Status: Legibility, layout, text-token and no-network clauses met in all eight captures (Prepare and Close dialogs, light and dark, 1280 and 390 px; evidence .wavefoundry/work/2430r/ac9/). The dark-theme background clause is not met: every .agent-dialog uses the pre-existing hardcoded #21242a (dashboard.css), which this change did not add; switching it to --panel-bg would restyle every dialog and is outside this text-and-presentation scope (coordinator decision, 2026-11-22). Key decisions: One spec covers docs and dashboard; Five stages, with Create wave and Add spec to wave inside Prepare.

## Watchpoints

- Watchpoint: wave 242ys is paused with uncommitted edits to `test_server_context_efficiency.py`, `CHANGELOG.md` and its spec; do not touch them except the shared CHANGELOG `[Unreleased]` section.
- Watchpoint: no framework edits while a full test suite run is in progress.
- Watchpoint: open `framework_edit_allowed` and `seed_edit_allowed` around the edits and close them after.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 2430r-cr-council-name-from-tier-label | do_now | no | completed | — |
| 2430r-docs-contract-dialog-facts-wrong-under-profiles | do_now | no | completed | — |
| 2430r-docs-contract-gates-overstated-for-target-repos | do_now | no | completed | — |
| 2430r-docs-contract-lifecycle-overview-non-trivial-residue | do_now | no | completed | — |
| 2430r-docs-contract-readiness-not-rerun-contradicts-seed-007 | do_now | no | completed | — |
| 2430r-qa-ac9-ac8-oracle-not-concrete | do_now | no | completed | — |

*Machine review state — 6 findings; current: do_now 6, maybe_later 0, dont_do_later 0, not_issue 0*
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
| docs-contract-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
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
| plan | 48 | 84,562 |
| implement | 57 | 488,501 |
| review | 59 | 300,281 |
| **Total** | **164** | **873,344** |

<!-- wave:context-efficiency-state {"generation":162,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":57,"content_source_credit":500519,"derived_artifact_credit":0,"direct_net":488501,"estimated_tokens_saved":488501,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2722,"response_debit":15994,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6698},"plan":{"calls":48,"content_source_credit":209434,"derived_artifact_credit":1662,"direct_net":84562,"estimated_tokens_saved":84562,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":26061,"response_debit":106771,"source_credit_count":31,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6298},"review":{"calls":59,"content_source_credit":466622,"derived_artifact_credit":1319,"direct_net":300281,"estimated_tokens_saved":300281,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":28826,"response_debit":145612,"source_credit_count":31,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6778}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":164,"content_source_credit":1176575,"derived_artifact_credit":2981,"direct_net":873344,"estimated_tokens_saved":873344,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":57609,"response_debit":268377,"source_credit_count":76,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":19774},"wave_id":"2430r simple-lifecycle-docs-and-dashboard"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
