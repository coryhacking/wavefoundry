# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-25
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `24bik memory-add-rationale-lines`
Title: Memory Add Rationale Lines

## Objective

An agent running Review memories can rewrite an active record through `memory_add`, or consolidate records through `memory_consolidate(mode="create")`, and keep the `Action delta:` and `Validation rationale:` lines, so the replacement no longer counts as `no_rationale`. Existing `memory_add` and `memory_consolidate` calls are unchanged; the 53 records already rewritten without the lines are out of scope.

## Changes

Spec ID: `24bij-enh memory-add-carries-action-delta-and-rationale`
Spec Status: `implemented`

## Participants

- Coordinator: coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-11-25

## Wave Summary

Wave `24bik` (Memory Add Rationale Lines) delivered one change: memory_add Carries Action Delta and Validation Rationale.

Intent outcome: achieved (independently checked by qa-reviewer). The documented Review memories rewrite call `memory_add(..., status="active", supersedes=..., action_delta=...)` and `memory_consolidate(mode="create", ..., action_delta=...)` now write an `Action delta:` line, and `memory_eval.uncoverable_records` no longer reports such a record as `no_rationale` (RationaleInputTests AC-1 and AC-7, with control records that are still reported). All three prompt copies name the input inside both calls and say what the line must state (AC-4, with known-bad controls). `memory_validate` is unchanged (AC-8). The plan's measure of success, the next Review memories pass lowering `no_rationale` instead of raising it, can only be read after release; the 53 records already rewritten without the line still count, and the evaluation checks only that a line is present, so the line's quality remains a review judgment. The qa-reviewer's independent check confirmed this outcome and added two limitations, both incorporated: consolidation's `validation_rationale` write had no test (repaired, see the spec Progress Log), and the proof is at the handler level, so agents can send the new inputs only after the MCP server reloads and the host reconnects (the coordinator reconnected the host in this session and observed both new inputs in the served `memory_add` and `memory_consolidate` schemas; the wrapper-level test added in repair covers the registered tools).

**Changes delivered:**

- **memory_add Carries Action Delta and Validation Rationale** (`24bij-enh memory-add-carries-action-delta-and-rationale`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7 and AC-8 completed. Key decisions: Add optional `action_delta` and `validation_rationale` inputs to `memory_add` and tell the Review memories rewrite step to pass `action_delta`; Validate in the public entry points, strip before the single-line check, and leave `_memory_add_response_locked` unchanged.

## Watchpoints

- Watchpoint: the seed 240 edit needs `seed_edit_allowed`, and framework script edits need `framework_edit_allowed`. Follow-up: backfilling the 53 existing rewrites is an operator decision outside this wave.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 24bik-r-cr1-validate-path-check | do_now | no | completed | code-reviewer |
| 24bik-r-q1-template-copy-omitted | do_now | no | completed | qa-reviewer, docs-contract-reviewer |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
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

2026-11-25: Intent outcome: achieved (independently checked by qa-reviewer). The documented Review memories rewrite call `memory_add(..., status="active", supersedes=..., action_delta=...)` and `memory_consolidate(mode="create", ..., action_delta=...)` now write an `Action delta:` line, and `memory_eval.uncoverable_records` no longer reports such a record as `no_rationale` (RationaleInputTests AC-1 and AC-7, with control records that are still reported). All three prompt copies name the input inside both calls and say what the line must state (AC-4, with known-bad controls). `memory_validate` is unchanged (AC-8). The plan's measure of success, the next Review memories pass lowering `no_rationale` instead of raising it, can only be read after release; the 53 records already rewritten without the line still count, and the evaluation checks only that a line is present, so the line's quality remains a review judgment. The qa-reviewer's independent check confirmed this outcome and added two limitations, both incorporated: consolidation's `validation_rationale` write had no test (repaired, see the spec Progress Log), and the proof is at the handler level, so agents can send the new inputs only after the MCP server reloads and the host reconnects (the coordinator reconnected the host in this session and observed both new inputs in the served `memory_add` and `memory_consolidate` schemas; the wrapper-level test added in repair covers the registered tools).

2026-11-25: Delivery Wave Council PASS, intent_fit establishes. Seats: red-team (fixed, adversarial primer at standard depth) and docs-contract-reviewer (rotating fifth seat), with council-chair synthesizing; required lanes code-reviewer, qa-reviewer, architecture-reviewer and docs-contract-reviewer. Round 1: every seat and lane approved with nonblocking findings. Repaired before any delivery approval: QA-1, CR-2, CR-3/QA-2, D-1, D-2, AR-2/D-3, then CR-4 after the focused re-review; all four lanes approved the repaired tree with every mutant they tried killed. Declined: RT-2/CR-1 (merging the pre-check problems into one refusal), RT-3 (`preview_data` on the consolidate refusal) and option (d) (advisory on a replacement with neither line). The only disagreement was the red-team and docs-contract preference for option (d), resolved by the recorded Decision Log reasoning. Operator follow-up candidate: AR-1, aligning `memory_validate` with `memory_single_line`. Final framework suite: 13621 tests across 261 files OK.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 65 | 1,776,009 |
| implement | 44 | 0 |
| review | 97 | 2,728,551 |
| **Total** | **206** | **4,504,560** |

<!-- wave:context-efficiency-state {"generation":177,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":44,"content_source_credit":1988,"derived_artifact_credit":0,"direct_net":-6587,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1506,"response_debit":12046,"source_credit_count":5,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4977},"plan":{"calls":65,"content_source_credit":1925408,"derived_artifact_credit":4131,"direct_net":1776009,"estimated_tokens_saved":1776009,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8621,"response_debit":151207,"source_credit_count":75,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6298},"review":{"calls":97,"content_source_credit":3064041,"derived_artifact_credit":1698,"direct_net":2728551,"estimated_tokens_saved":2728551,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5385,"response_debit":338732,"source_credit_count":72,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6929}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":206,"content_source_credit":4991437,"derived_artifact_credit":5829,"direct_net":4497973,"estimated_tokens_saved":4504560,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":15512,"response_debit":501985,"source_credit_count":152,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":18204},"wave_id":"24bik memory-add-rationale-lines"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 7 | 0 | 6 | 8,740,274 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":6,"estimated_exploration_avoided":8740274,"surfaced_events":7} -->
<!-- wave:exploration-avoided end -->
