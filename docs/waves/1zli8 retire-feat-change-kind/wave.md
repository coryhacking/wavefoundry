# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-01
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zli8 retire-feat-change-kind`
Title: Retire Feat Change Kind

## Objective

New change docs can no longer be created with the `feat` kind: `wf_new_feature`, `change_doc_response` and the lifecycle-id CLI refuse it and point at `wf_new_enhancement`, while every existing `-feat` id keeps linting. A feature is larger than one change doc, so features are planned as several changes.

## Changes

Change ID: `1zlhx-change retire-feat-change-kind`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-10-02

## Wave Summary

Wave `1zli8` (Retire Feat Change Kind) delivered one change: Retire the Feat Change Kind for New Change Docs. Notable adjustments during implementation: Retire the Feat Change Kind for New Change Docs: Implemented. `vocabulary_profile` gains `RETIRED_CHANGE_KINDS = ("feat",)`, derived `MINTABLE_CHANGE_KINDS` and `retired_kind_message` in the fixed section; `_change_create_response` refuses a retired normalized kind before the slug check and before `change_create` (`change_kind_retired`, recovery and `next_tools` `wf_new_enhancement`); `lifecycle_id.main` raises the same message inside its existing try (exit 2), `KIND_CHOICES` unchanged; `wf_help` `plan_feature`, `wf_list_plans` `next_tools` and the `wf_new_feature` / `wf_new_change` docstrings updated, with the two handler digests refreshed. Seeds 001, 110 and 170 (under `seed_edit_allowed`), both Plan feature prompts, `docs/PLANS.md`, the lifecycle overview, the enterprise delivery model, the tool-surface spec, `AGENTS.md` (note placed after the Tool Detail pointer, outside the census-parsed Available tools block), layering-rules and the CHANGELOG updated. Tests: new `test_retired_change_kinds.py` (AC-1, AC-2, AC-4) and `test_change_kinds.py` additions (`ExistingFeatIdsTests` AC-3, `RetiredKindsSingleSourceTests` AC-6 with `RETIRED_CHANGE_KINDS = ("bug",)`, frozen retired assertion, `DeclaredKindTests` core case now `enh` plus a `feat` refusal). Failing first: 14 of 15 new tests and 3 `test_change_kinds` cases failed before implementation. Full suite in a scratch copy 10590 tests OK (34 skipped); `--profile second` 10587 OK (44 skipped); `--profile declared` 10590 OK (34 skipped). Mutations (drop the server check, drop the CLI refusal, hardcode `feat` instead of `RETIRED_CHANGE_KINDS`, revert `wf_list_plans` `next_tools`, revert the `wf_help` chain) each failed named tests. Gapfill: the docs `feat` census used shell grep because the MCP `code_keyword` index does not cover the prose kind-list forms across seeds and `docs/` in one pass.

**Changes delivered:**

- **Retire the Feat Change Kind for New Change Docs** (`1zlhx-change retire-feat-change-kind`) — 7 ACs completed. Key decisions: Retire `feat` for creation only; keep it in the grammar; Keep `wf_new_feature` registered as a refusing tool
## Watchpoints

- Watchpoint: seed edits (001, 110, 170) need `seed_edit_allowed` and script edits need `framework_edit_allowed`; the Plan feature prompts are not rendered from seed 170, so edit both directly.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1ZLI8-FEAT-GUIDANCE-RESIDUE | do_now | no | completed | — |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-10-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: narrowing the CLI kind choices gives an unexplained argparse error while the MCP refusal names the replacement, so one rule had two refusal shapes; resolved by one shared retired_kind_message on every surface; strongest-alternative: a CHANGELOG instruction for consuming repositories to drop the feat row from their own Plan feature prompts, adopted)
- Prepare council seat evidence (2026-10-01): one independent reviewer ran both seats and the code, qa, architecture and docs-contract lanes; round one found no build-blocking defect and nine plan amendments (D1 to D9), all applied; the scoped recheck approved every lane and seat.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 23 | 59,465 |
| implement | 16 | 665,755 |
| review | 19 | 339,215 |
| **Total** | **58** | **1,064,435** |

<!-- wave:context-efficiency-state {"generation":57,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":16,"content_source_credit":671166,"derived_artifact_credit":0,"direct_net":665755,"estimated_tokens_saved":665755,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2096,"response_debit":3315,"source_credit_count":9,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":23,"content_source_credit":70864,"derived_artifact_credit":2653,"direct_net":59465,"estimated_tokens_saved":59465,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2151,"response_debit":18412,"source_credit_count":25,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":19,"content_source_credit":381942,"derived_artifact_credit":1466,"direct_net":339215,"estimated_tokens_saved":339215,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3872,"response_debit":42637,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":58,"content_source_credit":1123972,"derived_artifact_credit":4119,"direct_net":1064435,"estimated_tokens_saved":1064435,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8119,"response_debit":64364,"source_credit_count":58,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8827},"wave_id":"1zli8 retire-feat-change-kind"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
