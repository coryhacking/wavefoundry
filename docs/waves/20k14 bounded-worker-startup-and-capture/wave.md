# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-13
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20k14 bounded-worker-startup-and-capture`
Title: Bounded Worker Startup And Capture

## Objective

Preserve predictable worker imports and publication refusals while bounding captured upgrade-child output. Keep ordinary pruning counts and recovery semantics intact and correct the stdlib-only portability test without weakening its import rule.

## Changes

Change ID: `20j75-bug bounded-worker-bootstrap-and-child-capture`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, performance-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, performance-reviewer, security-reviewer

Completed At: 2026-10-13

## Wave Summary

Wave `20k14` (Bounded Worker Startup And Capture) delivered one change: Bounded worker bootstrap and child capture.

**Changes delivered:**

- **Bounded worker bootstrap and child capture** (`20j75-bug bounded-worker-bootstrap-and-child-capture`) — 7 ACs completed. Key decisions: Repair existing boundaries with local compatibility controls; Preserve marker enforcement and translate errors at publication

All admitted ACs and tasks are complete; none are deferred. Required independent reviews, repair reverification and operator approval are recorded. Final integrated qualification passed 12,471 tests across 185 files with 12 reported skips and a matching green framework receipt. Native Windows, live-host and exact new-archive qualification are not claimed. Timing investigation remains deferred while concurrent reviews run.

Retrospective and memory: the code-boundary lessons and negative controls are retained in canonical tests, architecture/spec documentation and this record. Close-time memory proposals found no eligible durable candidate; no duplicate memory file was created. Cleanup retains only wave.md, the admitted change and authoritative events.jsonl in this folder. Cited temporary review evidence remains at its recorded paths; no permanent evidence folder or duplicate readiness artifact is needed.

## Watchpoints

- Watchpoint: serialize review_evidence, changelog and shared architecture edits with other waves; no source writes before readiness.
- Capture is capped at 1 MiB per stream including elision. Truncated stderr makes pruning unproven and preserves the snapshot; intact stderr remains usable when stdout is truncated.
- Source-only guard loading is not source authentication or universal import protection. Marker enforcement remains active even without site initialization.
- Keep concise review rationale and verification results here with typed evidence. No additional evidence folder; no timing-threshold changes or new review gates.

## Readiness Review Packet

The chosen repair reuses existing module and subprocess boundaries. Alternatives were documentation-only, broader isolation and a new streaming result protocol; each either leaves the defect or increases scope. Reviewers should challenge worker startup failure handling, protected-root refusal without lock acquisition, byte accounting and redaction before capture truncation, and pruning's incomplete-evidence recovery. The selected lanes cover code correctness, QA negative controls, cross-module contracts, trust boundaries, bounded memory and accurate documentation. Existing Python 3.11.17 passing behavior is not evidence of every patch release. Inherited capable model allocation is used for this cross-process planning and review scope.

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
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| performance-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 247 | 1,987,515 |
| implement | 209 | 2,091,329 |
| review | 5 | 0 |
| **Total** | **461** | **4,078,844** |

<!-- wave:context-efficiency-state {"generation":273,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":209,"content_source_credit":2515326,"derived_artifact_credit":0,"direct_net":2091329,"estimated_tokens_saved":2091329,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7957,"response_debit":419384,"source_credit_count":65,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3344},"plan":{"calls":247,"content_source_credit":2461987,"derived_artifact_credit":2353,"direct_net":1987515,"estimated_tokens_saved":1987515,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":36582,"response_debit":444048,"source_credit_count":115,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":5,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-8360,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":49,"response_debit":11242,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2931}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":461,"content_source_credit":4977313,"derived_artifact_credit":2353,"direct_net":4070484,"estimated_tokens_saved":4078844,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":44588,"response_debit":874674,"source_credit_count":180,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10080},"wave_id":"20k14 bounded-worker-startup-and-capture"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 23 | 0 | 19 | 13,315,921 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":19,"estimated_exploration_avoided":13315921,"surfaced_events":23} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

Readiness, all seven specialist delivery approvals and council-delivery are current. Worker startup/search-path, source-only guard, bounded output capture, conservative pruning, publication refusal and restricted-import behavior have executed positive and meaningful negative controls. Fresh release review confirmed the repaired miniature archive and actual source inventory preserve inert imports and exclude the startup shim. Canonical qualification passed 12,471 tests across 185 files with 12 reported skips.

Council used a full independent red-team primer and closing, architecture/security/QA/reality fixed seats, a rotating docs-contract seat and chair synthesis. Related specialist remits shared disclosed contexts. Each seat formed its own assessment, addressed the primer and weighed the alternative; bounded repairs received fresh affected-lane verification. A dedicated pruning completion protocol was considered unnecessary for the admitted conservative behavior, with no unresolved material disagreement or automatic backlog. Native Windows, live-host, release-archive and performance qualification remain unclaimed. All ACs/tasks are complete; paused for operator signoff and closure.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-13 | Implementation and required independent delivery reviews complete. All three batch findings are repaired and independently cleared; all ACs/tasks are checked. Combined canonical qualification passes 12,471 tests across 185 files, 12 reported skips. Wave remains paused for operator signoff and closure. | Current typed approvals; green test receipt 83e8456ae65b35e56e2409ee1f48216471edb27552d52272329cd7bcbfc7c520; wave Review checkpoints |
