# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-24
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21ilj uv-bootstrap-pin-0-12-22`
Title: uv Bootstrap Pin 0.12.22

## Objective

A fresh `wf setup` on a machine without uv installs uv 0.12.22, verified against its 18 PyPI hashes. Boundary: an existing uv of any version is still used as-is.

## Changes

Change ID: `21ili-maint bump-uv-bootstrap-pin-0-12-22`
Change Status: `implemented`

## Participants

- Coordinator: implementer
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer

Completed At: 2026-10-24

## Wave Summary

Wave `21ilj` (uv Bootstrap Pin 0.12.22) delivered one change: Bump the uv Bootstrap Pin to 0.12.22.

Intent outcome: achieved. `wf setup` without uv now installs uv 0.12.22: the table matches PyPI's 18 wheel hashes (two independent comparisons), a real hash-verified install in a scratch venv on macOS arm64 installed `uv 0.12.22`, and the same line with wrong hashes was refused. An existing uv is untouched (discovery code unchanged). Full suite 12113 tests OK. Limitation: the real install was exercised on macOS arm64 only; other platforms rest on the matching PyPI hashes.

**Changes delivered:**

- **Bump the uv Bootstrap Pin to 0.12.22** (`21ili-maint bump-uv-bootstrap-pin-0-12-22`) — 2 ACs completed. Key decisions: Pin 0.12.22
## Watchpoints

- Watchpoint: framework edits need `framework_edit_allowed`.
- Watchpoint: the version and the hash table change in the same edit.

## Review Checkpoints

Intent outcome: achieved. `wf setup` without uv now installs uv 0.12.22: the table matches PyPI's 18 wheel hashes (two independent comparisons), a real hash-verified install in a scratch venv on macOS arm64 installed `uv 0.12.22`, and the same line with wrong hashes was refused. An existing uv is untouched (discovery code unchanged). Full suite 12113 tests OK. Limitation: the real install was exercised on macOS arm64 only; other platforms rest on the matching PyPI hashes.

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
| plan | 9 | 914 |
| implement | 20 | 225,982 |
| review | 13 | 233,643 |
| **Total** | **42** | **460,539** |

<!-- wave:context-efficiency-state {"generation":43,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":20,"content_source_credit":241223,"derived_artifact_credit":0,"direct_net":225982,"estimated_tokens_saved":225982,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":652,"response_debit":14875,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":286},"plan":{"calls":9,"content_source_credit":6648,"derived_artifact_credit":1892,"direct_net":914,"estimated_tokens_saved":914,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1293,"response_debit":10790,"source_credit_count":6,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4457},"review":{"calls":13,"content_source_credit":259373,"derived_artifact_credit":825,"direct_net":233643,"estimated_tokens_saved":233643,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1801,"response_debit":27989,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3235}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":42,"content_source_credit":507244,"derived_artifact_credit":2717,"direct_net":460539,"estimated_tokens_saved":460539,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3746,"response_debit":53654,"source_credit_count":46,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7978},"wave_id":"21ilj uv-bootstrap-pin-0-12-22"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 2 | 0 | 2 | 162,905 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":162905,"surfaced_events":2} -->
<!-- wave:exploration-avoided end -->
