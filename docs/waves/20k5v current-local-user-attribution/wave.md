# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-13
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20k5v current-local-user-attribution`
Title: Current Local User Attribution

## Objective

Record the current operating-system account as review provenance without adding authentication or approval gates.

## Changes

Change ID: `20k5u-enh verified-approver-identity-design`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-10-13

## Wave Summary

Wave `20k5v` (Current Local User Attribution) delivered one change: Current local user attribution. Notable adjustments during implementation: Current local user attribution: After focused readiness currency and recorded repair start, added only operator_identity and subprocess_util to the miniature packaging fixture. The unchanged isolated import/inert-guard test passes. Production packaging and source were unchanged by the fixture repair; fresh QA/release reverification and final qualification subsequently passed.

**Changes delivered:**

- **Current local user attribution** (`20k5u-enh verified-approver-identity-design`) — 4 ACs completed. Key decisions: Record current local OS account as separate optional provenance.; Preserve attribution on replay and keep it outside semantic identity.

All admitted ACs and tasks are complete; none are deferred. Required independent reviews, repair reverification and operator approval are recorded. Final integrated qualification passed 12,471 tests across 185 files with 12 reported skips and a matching green framework receipt. Native Windows, live-host and exact new-archive qualification are not claimed. Timing investigation remains deferred while concurrent reviews run.

Retrospective and memory: the code-boundary lessons and negative controls are retained in canonical tests, architecture/spec documentation and this record. Close-time memory proposals found no eligible durable candidate; no duplicate memory file was created. Cleanup retains only wave.md, the admitted change and authoritative events.jsonl in this folder. Cited temporary review evidence remains at its recorded paths; no permanent evidence folder or duplicate readiness artifact is needed.

## Watchpoints

- Watchpoint: Serialize after earlier review_evidence repairs; preserve original attribution on replay.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| QA-20K5V-PACK-FIXTURE | do_now | no | completed | qa-reviewer |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 235 | 1,952,829 |
| implement | 69 | 946,417 |
| review | 6 | 0 |
| **Total** | **310** | **2,899,246** |

<!-- wave:context-efficiency-state {"generation":144,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":69,"content_source_credit":1047573,"derived_artifact_credit":0,"direct_net":946417,"estimated_tokens_saved":946417,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2620,"response_debit":101296,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2760},"plan":{"calls":235,"content_source_credit":2503637,"derived_artifact_credit":2224,"direct_net":1952829,"estimated_tokens_saved":1952829,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":48528,"response_debit":511007,"source_credit_count":131,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6503},"review":{"calls":6,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-10508,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":59,"response_debit":13380,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2931}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":310,"content_source_credit":3551210,"derived_artifact_credit":2224,"direct_net":2888738,"estimated_tokens_saved":2899246,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":51207,"response_debit":625683,"source_credit_count":149,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12194},"wave_id":"20k5v current-local-user-attribution"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 13 | 0 | 13 | 6,244,188 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":13,"estimated_exploration_avoided":6244188,"surfaced_events":13} -->
<!-- wave:exploration-avoided end -->
## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-13 | Implementation and required independent delivery reviews complete. All three batch findings are repaired and independently cleared; all ACs/tasks are checked. Combined canonical qualification passes 12,471 tests across 185 files, 12 reported skips. Wave remains paused for operator signoff and closure. | Current typed approvals; green test receipt 83e8456ae65b35e56e2409ee1f48216471edb27552d52272329cd7bcbfc7c520; wave Review checkpoints |
| 2026-10-13 | After focused readiness currency and recorded repair start, added only operator_identity and subprocess_util to the miniature packaging fixture. The unchanged isolated import/inert-guard test passes. Production packaging and source were unchanged by the fixture repair; fresh QA/release reverification and final qualification subsequently passed. | Canonical targeted controls; recorded cycle-1 repair; no release/closure claim |
| 2026-10-13 | Final focused integration is green. The broad lifecycle run exposed four outdated expectations and one mock signature; eight targeted controls now pass with original historical digests preserved, deterministic account attribution, the exact callback advisory site and the original replacement-refusal oracle. No production repair was needed. All five implementations are paused; canonical combined qualification and independent delivery are next. | test_server_tools_lifecycle named failed methods and LocalUserReviewEventTests; git diff --check clean |
| 2026-10-13 | Implemented bounded native local-account lookup, optional canonical metadata, escaped labeled projection and new-event-only attribution. All 232 focused tests pass; 65 council-policy controls pass. A real readiness receipt and approval stay identical across account changes. Known-bad unsafe-name, omitted-propagation and caller-injection controls fail as intended. Full docs validation passes; final combined qualification and independent delivery remain pending. | test_operator_identity; test_review_evidence; LocalUserReviewEventTests; test_review_operator_integration; WaveCouncilPolicyTests; native Windows API mocked, native execution unrun |
| 2026-10-13 | Operator clarified scope and authorized preparation, review and implementation. Capable high-reasoning independent contexts assess boundary correctness; actual runtime identity unknown. Source writes serialize; focused checks per change, final canonical qualification on the combined tree, then final delivery authority. | Admitted change and current operator direction |

## Review checkpoints

Readiness, all five specialist delivery approvals and council-delivery are current. Fresh QA verified OS-account lookup, metadata validation/display, registered publication/replay and unchanged approval identity. The miniature packaging fixture now includes its existing dependencies; fresh QA/release checks passed and detected the old omission. Canonical qualification passed 12,471 tests across 185 files with 12 reported skips.

Council used a full independent red-team primer and closing, architecture/security/QA/reality fixed seats, a rotating docs-contract seat and chair synthesis. Related specialist remits shared disclosed contexts. Each seat formed its own assessment, addressed the primer and weighed the alternative; bounded repairs received fresh affected-lane verification. A separate provenance module was considered unnecessary for this scope, with no unresolved material disagreement or automatic backlog. Attribution identifies the local process account, not an authenticated human. Native Windows remains mocked. All ACs/tasks are complete; paused for operator signoff and closure.
