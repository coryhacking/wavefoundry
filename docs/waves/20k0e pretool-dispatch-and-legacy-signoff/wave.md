# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-13
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20k0e pretool-dispatch-and-legacy-signoff`
Title: Pretool Dispatch And Legacy Signoff

## Objective

Make generated pre-edit dispatch reach supported unfamiliar-tool checks and prevent lane names from satisfying legacy prose approvals.

## Changes

Change ID: `20k0d-bug pretool-dispatch-and-legacy-signoff`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-10-13

## Wave Summary

Wave `20k0e` (Pretool Dispatch And Legacy Signoff) delivered one change: Pretool dispatch and legacy signoff.

**Changes delivered:**

- **Pretool dispatch and legacy signoff** (`20k0d-bug pretool-dispatch-and-legacy-signoff`) — 4 ACs completed. Key decisions: Omit only the pre-edit matcher and reuse existing classification.; Exclude matched lane text from legacy prose token search.

All admitted ACs and tasks are complete; none are deferred. Required independent reviews, repair reverification and operator approval are recorded. Final integrated qualification passed 12,471 tests across 185 files with 12 reported skips and a matching green framework receipt. Native Windows, live-host and exact new-archive qualification are not claimed. Timing investigation remains deferred while concurrent reviews run.

Retrospective and memory: the code-boundary lessons and negative controls are retained in canonical tests, architecture/spec documentation and this record. Close-time memory proposals found no eligible durable candidate; no duplicate memory file was created. Cleanup retains only wave.md, the admitted change and authoritative events.jsonl in this folder. Cited temporary review evidence remains at its recorded paths; no permanent evidence folder or duplicate readiness artifact is needed.

## Watchpoints

- Watchpoint: Serialize review_evidence.py changes before the worker-publication wave. No timing reassessment or new evidence folder.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DOCS-20K0E-STALE-PREHOOK-COVERAGE | do_now | no | completed | docs-contract-reviewer |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
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
| plan | 352 | 3,935,804 |
| implement | 115 | 1,857,281 |
| review | 21 | 704,535 |
| **Total** | **488** | **6,497,620** |

<!-- wave:context-efficiency-state {"generation":188,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":115,"content_source_credit":2053478,"derived_artifact_credit":0,"direct_net":1857281,"estimated_tokens_saved":1857281,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3789,"response_debit":195184,"source_credit_count":65,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2776},"plan":{"calls":352,"content_source_credit":4798011,"derived_artifact_credit":2114,"direct_net":3935804,"estimated_tokens_saved":3935804,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":35952,"response_debit":832174,"source_credit_count":162,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":21,"content_source_credit":746497,"derived_artifact_credit":1146,"direct_net":704535,"estimated_tokens_saved":704535,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":554,"response_debit":45485,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2931}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":488,"content_source_credit":7597986,"derived_artifact_credit":3260,"direct_net":6497620,"estimated_tokens_saved":6497620,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":40295,"response_debit":1072843,"source_credit_count":237,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9512},"wave_id":"20k0e pretool-dispatch-and-legacy-signoff"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 13 | 0 | 13 | 10,515,653 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":13,"estimated_exploration_avoided":10515653,"surfaced_events":13} -->
<!-- wave:exploration-avoided end -->
## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-13 | Implementation and required independent delivery reviews complete. All three batch findings are repaired and independently cleared; all ACs/tasks are checked. Combined canonical qualification passes 12,471 tests across 185 files, 12 reported skips. Wave remains paused for operator signoff and closure. | Current typed approvals; green test receipt 83e8456ae65b35e56e2409ee1f48216471edb27552d52272329cd7bcbfc7c520; wave Review checkpoints |
| 2026-10-13 | Corrected both stale threat-model pre-hook claims after recorded repair start. Fresh independent docs verification passed generated registration and an MCP-named protected-path denial; original unsupported-schema, selective-post and live-host limits retained. Final qualification and remaining delivery authority pending. | Canonical targeted controls; recorded cycle-1 repair; no release/closure claim |
| 2026-10-13 | Implemented hook registration, lane masking and matching guidance. Focused suite: 168 tests passed in 59.103s; full docs lint passed. Restoring the finite pre-matcher makes the registered dispatch regression fail; removing lane masking makes nine negative subtests fail. Final combined qualification and independent delivery review pending. | test_render_platform_surfaces; test_server_tools_lifecycle.SignoffLatestStateTests and TypedExclusiveGateDerivationTests; wf_validate_docs |
| 2026-10-13 | Operator authorized planning, preparation, review and implementation. Coordinator owns this narrow implementation; independent council/readers verify readiness and delivery. Task-fit allocation uses capable high-reasoning contexts for gate/authority correctness; actual runtime identity unknown. | Admitted change; current request |

## Review checkpoints

Readiness and all five required specialist delivery approvals are current. The two false threat-model claims were corrected and independently reverified against generated hook dispatch, including a meaningful old-behavior control. The combined canonical suite passed 12,471 tests across 185 files with 12 reported skips. No delivery council is required for this wave. All ACs/tasks are complete; paused for operator signoff and closure.
