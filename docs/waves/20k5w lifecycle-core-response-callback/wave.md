# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-13
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20k5w lifecycle-core-response-callback`
Title: Lifecycle Core Response Callback

## Objective

Provide an opt-in lifecycle completion callback before accounting inside the existing mutating publication hold.

## Changes

Change ID: `20kd8-enh declared-core-response-callback`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-10-13

## Wave Summary

Wave `20k5w` (Lifecycle Core Response Callback) delivered one change: Declared lifecycle core response callback. Notable adjustments during implementation: Declared lifecycle core response callback: Added the shared shipped-declaration fixture to review targets: its exact declaration census and profile resets must include the new empty callback mapping. This supports the already admitted loader/profile contract; callback semantics are unchanged. The focused readiness currency check preceded the completed implementation.

**Changes delivered:**

- **Declared lifecycle core response callback** (`20kd8-enh declared-core-response-callback`) — 4 ACs completed. Key decisions: Lifecycle-first completion seam for four existing mutating handlers.; One callback per tool in an existing declared helper, additive response namespace, diagnostic-on-failure.

All admitted ACs and tasks are complete; none are deferred. Required independent reviews, repair reverification and operator approval are recorded. Final integrated qualification passed 12,471 tests across 185 files with 12 reported skips and a matching green framework receipt. Native Windows, live-host and exact new-archive qualification are not claimed. Timing investigation remains deferred while concurrent reviews run.

Retrospective and memory: the code-boundary lessons and negative controls are retained in canonical tests, architecture/spec documentation and this record. Close-time memory proposals found no eligible durable candidate; no duplicate memory file was created. Cleanup retains only wave.md, the admitted change and authoritative events.jsonl in this folder. Cited temporary review evidence remains at its recorded paths; no permanent evidence folder or duplicate readiness artifact is needed.

## Watchpoints

- Watchpoint: Run after earlier server edits; only the four selected completion callers are supported.

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
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: operator explicitly authorized closure, commit and push on 2026-10-13; typed approval records that instruction.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 93 | 905,722 |
| implement | 66 | 2,036,593 |
| review | 8 | 132,795 |
| **Total** | **167** | **3,075,110** |

<!-- wave:context-efficiency-state {"generation":165,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":66,"content_source_credit":2132540,"derived_artifact_credit":0,"direct_net":2036593,"estimated_tokens_saved":2036593,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2559,"response_debit":96206,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2818},"plan":{"calls":93,"content_source_credit":1105599,"derived_artifact_credit":684,"direct_net":905722,"estimated_tokens_saved":905722,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":38038,"response_debit":169026,"source_credit_count":73,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6503},"review":{"calls":8,"content_source_credit":145386,"derived_artifact_credit":0,"direct_net":132795,"estimated_tokens_saved":132795,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":134,"response_debit":15388,"source_credit_count":5,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2931}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":167,"content_source_credit":3383525,"derived_artifact_credit":684,"direct_net":3075110,"estimated_tokens_saved":3075110,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":40731,"response_debit":280620,"source_credit_count":102,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12252},"wave_id":"20k5w lifecycle-core-response-callback"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 9 | 0 | 9 | 2,330,177 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":9,"estimated_exploration_avoided":2330177,"surfaced_events":9} -->
<!-- wave:exploration-avoided end -->
## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-13 | Implementation and required independent delivery reviews complete. All three batch findings are repaired and independently cleared; all ACs/tasks are checked. Combined canonical qualification passes 12,471 tests across 185 files, 12 reported skips. Wave remains paused for operator signoff and closure. | Current typed approvals; green test receipt 83e8456ae65b35e56e2409ee1f48216471edb27552d52272329cd7bcbfc7c520; wave Review checkpoints |
| 2026-10-13 | Final focused integration is green. The broad lifecycle run exposed four outdated expectations and one mock signature; eight targeted controls now pass with original historical digests preserved, deterministic account attribution, the exact callback advisory site and the original replacement-refusal oracle. No production repair was needed. All five implementations are paused; canonical combined qualification and independent delivery are next. | test_server_tools_lifecycle named failed methods and LocalUserReviewEventTests; git diff --check clean |
| 2026-10-13 | Callback implementation and focused controls are complete: 39 context/accounting/focus tests pass, all 10 new tests pass by direct-file execution, and 21 extension tests pass in the existing tool environment after system-Python MCP import setup errors. Six known-bad callback/limit/declaration controls are detected. Full lifecycle module is still running with failures awaiting final traces; combined qualification and independent delivery remain pending. | LifecycleResponseCallbackTests; LifecycleCallbackServingTests; LifecycleCallbackDeclarationTests; no native Windows execution |
| 2026-10-13 | Readied and opened after the shared declaration fixture received focused readiness review. Readback: four canonical lifecycle completion paths invoke a declared synchronous helper once, with detached input, before accounting and inside the existing mutating publication hold; bounded additive output cannot veto or replace core outcome. Defaults perform only a lookup. | Current typed readiness; AC-1..AC-4; local_user source preserved; pre-implementation memory brief |
| 2026-10-13 | Operator clarified scope and authorized preparation, review and implementation. Capable high-reasoning independent contexts assess boundary correctness; actual runtime identity unknown. Source writes serialize; focused checks per change, final canonical qualification on the combined tree, then final delivery authority. | Admitted change and current operator direction |

## Review checkpoints

Readiness and all five required specialist delivery approvals are current. Registered lifecycle completion, publication-hold/accounting order, detached inputs, output limits and advisory failure behavior were verified with meaningful negative controls. Canonical qualification passed 12,471 tests across 185 files with 12 reported skips. No delivery council is required for this wave. Callbacks remain trusted synchronous code, without rollback or execution-deadline guarantees. All ACs/tasks are complete; paused for operator signoff and closure.
