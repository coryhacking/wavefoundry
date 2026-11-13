# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-12
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `237ei tool-reference-and-guru-description-follow-ups`
Title: Tool Reference And Guru Description Follow Ups

## Objective

Close the three follow-ups from wave `237ef`. Upgraded projects receive the current Guru subagent description without a manual edit. Every registered tool outside the `wf_new_<kind>` family has a checked parameter list in the tool reference. Tool descriptions sent to the model carry no wave or change IDs. No tool behavior changes.

## Changes

Change ID: `237ej-enh refresh-shipped-guru-subagent-description`
Change Status: `implemented`

Change ID: `237ek-enh signatures-for-every-tool-entry`
Change Status: `implemented`

Change ID: `237el-enh drop-lifecycle-ids-from-tool-descriptions`
Change Status: `implemented`
Depends On: `237ek-enh signatures-for-every-tool-entry`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-11-12

## Wave Summary

Wave `237ei` (Tool Reference And Guru Description Follow Ups) delivered 3 changes: Refresh Shipped Guru Subagent Description, Signatures For Every Tool Entry, and Drop Lifecycle IDs From Tool Descriptions.

**Changes delivered:**

- **Refresh Shipped Guru Subagent Description** (`237ej-enh refresh-shipped-guru-subagent-description`) — AC-1, AC-2, AC-3 and AC-4 completed. Key decisions: Replace only a description the renderer or seed 050 previously shipped; Keep the known-set design over a framework-owned description with an opt-out key (red-team's strongest alternative).
- **Signatures For Every Tool Entry** (`237ek-enh signatures-for-every-tool-entry`) — AC-1, AC-2, AC-3 and AC-4 completed. Key decisions: Convert bullets in place to signature bullets; Remove the redundant rules, keeping one only if a control needs it.
- **Drop Lifecycle IDs From Tool Descriptions** (`237el-enh drop-lifecycle-ids-from-tool-descriptions`) — AC-1, AC-2, AC-3 and AC-4 completed. Key decisions: Clean every description, not only Tool Index summaries.

## Watchpoints

- Watchpoint: `237ek` and `237el` both edit `test_server_tools.py` and the tool spec; implement `237ek` first.
- `237ej` edits seed 160 and needs `seed_edit_allowed` as well as `framework_edit_allowed`.
- Description docstring edits change the handler digests pinned in `tests/fixtures/register-surface-handler-digests.json`.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| GURU-REFRESH-DEL-1 | do_now | no | completed | code-reviewer, qa-reviewer |

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

## Review Checkpoints

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 28 | 23,674 |
| implement | 69 | 0 |
| review | 51 | 714,839 |
| **Total** | **148** | **738,513** |

<!-- wave:context-efficiency-state {"generation":151,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":69,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-13041,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2302,"response_debit":13027,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2288},"plan":{"calls":28,"content_source_credit":65034,"derived_artifact_credit":5692,"direct_net":23674,"estimated_tokens_saved":23674,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5844,"response_debit":46710,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5502},"review":{"calls":51,"content_source_credit":811631,"derived_artifact_credit":2065,"direct_net":714839,"estimated_tokens_saved":714839,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12456,"response_debit":90177,"source_credit_count":29,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3776}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":148,"content_source_credit":876665,"derived_artifact_credit":7757,"direct_net":725472,"estimated_tokens_saved":738513,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":20602,"response_debit":149914,"source_credit_count":45,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11566},"wave_id":"237ei tool-reference-and-guru-description-follow-ups"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 6 | 0 | 5 | 5,050,825 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":5,"estimated_exploration_avoided":5050825,"surfaced_events":6} -->
<!-- wave:exploration-avoided end -->
