# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-08
Completed at: 2026-09-05
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1x5tq later-created-doc-link-targets`
Title: Incremental Graph Recovery and Dry-Run Safety

## Objective

Restore incremental/full graph equivalence when an unchanged document links to a file created after its first scan, and enforce the zero-change build's dry-run no-write contract. Coordinate selective graph recovery with idle-maintenance planning so real builds repair pending work while dry runs report it without mutation.

## Changes

Change ID: `1x8e1-bug doc-link-into-later-created-target-never-gains-edge`
Change Status: `complete`

Change ID: `1x81w-bug dry-run-reaches-zero-change-writes-unlocked`
Change Status: `complete`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer, security-reviewer
- Readiness council: red-team primer; architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; rotating performance-reviewer; wave-council synthesis.

Completed At: 2026-09-05

## Wave Summary

Delivered selective recovery of links to later-created files (`1x8e1`) and read-only zero-change maintenance previews (`1x81w`). Builder 51 preserves per-document unresolved targets through failed reads, and successful recovery stops rescanning. Delivery repair ARCH-DEL-1 shares the existing payload-binding proof with idle planning so interrupted publication recovers before epoch completion.

All six required ACs and all tasks are complete. No deferred changes, `[~]` ACs, open questions or removed requirements. Existing locked publication ordering and graph ownership are preserved; no additional retry ledger was introduced.

Retrospective: an obligation disappearing from durable merge state does not prove its graph payload was published. Idle planning must check the publication binding used by the consumer; this decision and the failure/retry regression are retained in the change doc, architecture documentation and delivery report. Review memory capture rejected the temporary-probe duplicate; close-time proposal is exhausted with zero new candidates, so no memory promotion is warranted.

Changelog audit: the five latest committed waves (`1x6ti`, `1x54z`, `1x4ol`, `1wpig`, `1wpih`) already cover all eleven admitted changes. Current-wave entries cover both fixes and ARCH-DEL-1. Their historical records were left intact.

## Watchpoints

- Watchpoint: preserve zero-edge document fragments' unresolved targets without exposing a document node until a real edge exists.
- Newly current paths must include node-less targets; unrelated builds must not read unaffected documents.
- Fragment shape changes require a graph builder version bump and matching pins.
- This request refreshes combined readiness and then implements both changes; no closure or commit is authorized.
- Watchpoint: `1x81w` must establish the dry-run return before idle-maintenance mutations; graph-recovery integration must preserve that boundary and plan-only reporting.

## Current assumptions

- Product-owner: N/A for the `1x81w` admission delta; the operator authorized adding a bug fix that restores the existing no-write contract, with no new feature or UX acceptance.
- Existing symbol-triggered rescans and delete-side behavior remain regression controls.

## Outputs produced or expected

- Two wave-owned change documents, refreshed combined readiness evidence, and required delivery lane assignments.
- At implementation: zero-change dry-run guard and reporting tests; unresolved-path metadata, selective rescan trigger, differential tests, affected architecture updates, and CHANGELOG entry.

## Review checkpoints

- Close reconciliation — 2026-09-05: operator explicitly authorized closure and commit after the delivery report. Both change statuses finalized as complete; all six ACs and tasks checked; required readiness, five delivery lanes and council approvals current; ARCH-DEL-1 independently repaired, no waiver. Docs-contract review: not applicable — no `docs/specs/*.md` changed; affected architecture docs were verified by architecture and QA. Memory validation and retrospective complete; no durable candidate pending. Closure chronology and idle handoff are finalized with the close checkpoint. Changelog audit covers this wave and the five latest committed waves.

- Delivery review — 2026-09-05: PASS after repair cycle 2. Full primer and isolated architecture/security/QA/reality seats, rotating performance alternative, one challenge and independent anonymous initial synthesis found ARCH-DEL-1 (high correctness). Shared read-only payload binding restores interrupted-publication recovery. Fresh architecture/QA cleared the defect; code, security, performance, architecture, QA and wave-council-delivery approvals are current. Historical initial split is preserved; focused repair evidence resolves the disagreement. Final 8,480 tests/74 files pass with 3 skips; docs lint and diff check clean. [Delivery report](delivery-review.md). All six required ACs verified, no scope/priority deferrals, no blocker waived. Operator signoff remains pending.

- Implementation verification — 2026-09-05: PASS. Final frozen tree: 8,478 tests across 74 files, 3 skips; fresh green framework receipt; full docs lint and diff check clean. Fifteen scratch mutation checks rejected known-bad variants. Both changes are implemented; no delivery-phase approval is claimed. Framework edit gate closed.

- Combined Prepare — 2026-09-05: PASS. Fresh full-depth council unanimous with no mandatory gap; all five specialist readiness approvals recorded to satisfy activation. [Combined readiness evidence](combined-readiness-review.md). `wf_prepare_wave(mode=ready)` and `wf_implement_wave(mode=create)` passed.

- Admission delta — 2026-09-05: operator authorized adding `1x81w`. The earlier council approval reviewed `1x8e1` alone; it does not approve this expanded packet. Re-Prepare is required before implementation. Existing code, QA, architecture, and performance lanes remain requested; the next readiness pass reconciles the combined scope.
- Initial readiness council: changes requested, `COUNCIL-READY-1`; full primer and isolated architecture, security, QA, reality seats with rotating performance. Initial seat agreement: split; maximum severity: high. One targeted challenge resolved the difference as approval timing; all seats require the same bounded clarifications. No blocker was waived.
- Readiness repair cycle 1 complete: requirements and AC evidence now specify retained per-doc unresolved/current eligibility before zero-change, retry through read failures, both persisted representations, direct node/edge assertions, negative/cost controls, and actual index-build reachability verification before delivery. Fresh independent QA and reality-checker cleared their own lanes; fresh final council approved the revised plan. No product implementation is claimed.
- **Prepare-phase Wave Council [prepare-council] — 2026-09-05: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, performance-reviewer; rotating-seat: performance-reviewer; strongest-challenge: a consumed target-creation transition loses retry after skipped reads; strongest-alternative: assembly-time raw-candidate resolution reduces text reads but broadens edge ownership and outage handling beyond this bounded repair). Original independent aggregate remains split/high; the focused final approval follows repaired-plan verification, not a fabricated second unanimous council.
- Evidence and reproducible baseline fixtures: [readiness review](readiness-review.md). Current-tree noded/node-less and unchanged-recovery probes reject incremental/full equality; explicit doc rescan restores equality and absent-target controls perform zero rescans. These establish the defect and plan feasibility, not delivery completion.

## Completion criteria

- Every required AC and task has evidence; required delivery reviews are current; operator authorizes closure.

## Handoff or next-wave notes

- Wave closed on operator instruction after all technical and operator signoffs. Both changes complete; ARCH-DEL-1 independently cleared. No deferred decisions; commit authorized in the closure request.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-DEL-1 | do_now | no | completed | architecture-reviewer, qa-reviewer, wave-council-delivery |
| COUNCIL-READY-1 | do_now | no | completed | wave-council-readiness |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| performance-reviewer | approved | current executed approval follows every affected repair | none |
| security-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- Operator approved closure and commit on 2026-09-05; typed operator-signoff is recorded above.

## Dependencies

- No external wave dependencies.
- Implementation order: `1x81w` dry-run guard and its no-write/reporting controls, then `1x8e1` graph recovery and entry-path verification. One implementer owns shared `indexer.py` orchestration; the graph caller integration is explicitly admitted in the combined readiness packet. Generic implementer lanes suit these bounded Python changes; no new senior-specialist domain is required.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 246 | 1,020,387 |
| implement | 27 | 724,556 |
| review | 204 | 1,116,015 |
| **Total** | **477** | **2,860,958** |

<!-- wave:context-efficiency-state {"generation":332,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":27,"content_source_credit":762742,"derived_artifact_credit":0,"direct_net":724556,"estimated_tokens_saved":724556,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1263,"response_debit":38522,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1599},"plan":{"calls":246,"content_source_credit":1950523,"derived_artifact_credit":637,"direct_net":1020387,"estimated_tokens_saved":1020387,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":24961,"response_debit":913698,"source_credit_count":88,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7886},"review":{"calls":204,"content_source_credit":2155477,"derived_artifact_credit":743,"direct_net":1116015,"estimated_tokens_saved":1116015,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":28565,"response_debit":1013529,"source_credit_count":48,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":477,"content_source_credit":4868742,"derived_artifact_credit":1380,"direct_net":2860958,"estimated_tokens_saved":2860958,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":54789,"response_debit":1965749,"source_credit_count":144,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11374},"wave_id":"1x5tq later-created-doc-link-targets"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 6 | 0 | 3 | 2,135,868 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":3,"estimated_exploration_avoided":2135868,"surfaced_events":6} -->
<!-- wave:exploration-avoided end -->
