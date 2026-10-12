# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-11
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20gx0 bounded-upgrade-diagnostics`
Title: Bounded Upgrade Diagnostics

## Objective

Bound retained child logs and clean returned upgrade display text without disrupting pipe draining or machine protocol decisions.

## Changes

Change ID: `20gfh-bug bounded-upgrade-child-diagnostics`
Change Status: `implemented`

## Participants

- Coordinator: main session
- Write-owning roles: implementer; coordinator owns lifecycle records and integration
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-10-12

## Wave Summary

Wave `20gx0` (Bounded Upgrade Diagnostics) delivered one change: Bound retained child logs and clean returned upgrade output. Notable adjustments during implementation: Bound retained child logs and clean returned upgrade output: Readback: reserve marker and final 64 KiB tail within each 1 MiB UTF-8 child-log budget on the existing owned append handle; keep small bytes exact and both pipes draining; finalize before reporting log errors. Clean returned display with the known publisher token after raw summary/status interpretation and before the display cap. Before: a noisy child grows beyond 1 MiB and returned display keeps controls. After: retained head/elision/tail fits the byte cap and display is scrubbed. Raw capture and primary upgrade.log are outside scope.; Bound retained child logs and clean returned upgrade output: Final implementation and required independent delivery review completed; all admitted ACs are supported. Paused for operator closure. See `wave.md` Review Checkpoints for consolidated findings, limits, source identity and reviewer roster.

**Changes delivered:**

- **Bound retained child logs and clean returned upgrade output** (`20gfh-bug bounded-upgrade-child-diagnostics`) — 5 ACs completed. Key decisions: Use one fixed per-child byte cap with retained head/final tail and explicit elision.; Clean presentation after raw protocol interpretation, before display bounding.
Retrospective and memory: Interpret raw protocol output before cleaning the displayed result; retained-log bounds do not imply bounded full process capture. The spec and regression tests preserve this distinction. Bounded memory proposal returned no eligible candidates; no duplicate memory record was created. No AC or task was deferred.

Cleanup disposition: Only wave.md, the admitted change document and the authoritative ledger are retained. Routine probes and logs remain temporary; no permanent evidence folder or duplicate readiness file was created.

## Watchpoints

- Watchpoint: Operator authorized implementation and pause after review; no closure, commit or push. Use generic repository examples and existing wave/change records only. Qualify the combined source tree before final delivery approvals; intermediate pauses may carry pending combined qualification.

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

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 30 | 27,074 |
| implement | 44 | 172,629 |
| review | 9 | 9,221 |
| **Total** | **83** | **208,924** |

<!-- wave:context-efficiency-state {"generation":86,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":44,"content_source_credit":188629,"derived_artifact_credit":0,"direct_net":172629,"estimated_tokens_saved":172629,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1543,"response_debit":17356,"source_credit_count":6,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2899},"plan":{"calls":30,"content_source_credit":82504,"derived_artifact_credit":1843,"direct_net":27074,"estimated_tokens_saved":27074,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14655,"response_debit":46423,"source_credit_count":26,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":9,"content_source_credit":29663,"derived_artifact_credit":0,"direct_net":9221,"estimated_tokens_saved":9221,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":239,"response_debit":23134,"source_credit_count":7,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2931}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":83,"content_source_credit":300796,"derived_artifact_credit":1843,"direct_net":208924,"estimated_tokens_saved":208924,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16437,"response_debit":86913,"source_credit_count":39,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9635},"wave_id":"20gx0 bounded-upgrade-diagnostics"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 5 | 0 | 5 | 7,169,846 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":5,"estimated_exploration_avoided":7169846,"surfaced_events":5} -->
<!-- wave:exploration-avoided end -->
## Review Checkpoints

- Work allocation: focused implementation and routine independent reviews request gpt-6.1-sol/high; the ambiguous bookkeeping boundary requests gpt-6-astra/high. These are requested settings; runtime identity beyond host reporting is unknown. Tasks are scoped per role with independent review contexts, shared source reads and serialized writes.

- Readiness specialist review: independent code, QA and architecture approved all four plans; security approved the three runtime/qualification waves and participated in all councils. Required docs-contract and release lanes approved their assigned scopes. Current-tree controls only; no future delivery execution is claimed. Review working reports stay in temporary storage.

- Readiness council: pass; fixed architecture, security, QA and reality seats plus rotating docs-contract, preceded by isolated red-team primer and anonymous-first synthesis. Agreement unanimous; maximum severity none; no challenge round needed. Primer depth standard. Red-team closing confirmed all original questions addressed and the admitted plan unchanged. Assert exact UTF8 filesystem cap-1/cap/cap+1 bytes including marker/newlines, exact small bytes and final head/tail. Exercise both drains and normal/failure/timeout finalization plus registered success/error/restart output without modifying raw sentinel decisions. Final implementation qualification and delivery approval remain pending.

- Delivery complete (2026-10-12): independent code, QA, architecture, security and docs-contract reviewers approved; no unresolved findings. Real child processes prove the 1 MiB UTF-8 filesystem cap, exact small logs, explicit elision, retained opening/final diagnostics and both-pipe draining across success, nonzero exit, timeout and final log I/O failure. Registered upgrade controls prove display cleaning precedes display capping while raw summary/recovery interpretation remains unchanged.

- Negative controls and limits: cap loosening, omitted tail/finalization and removed display cleaning were detected by named tests. The bound covers retained per-child logs, not full parser capture or the separate primary upgrade log. Redaction covers the existing known token/control cleaning contract, not a general secret scanner. Native Windows newline accounting was simulated; native Windows execution and live upgrade were not qualified.

- Final default qualification (2026-10-12): canonical `python3 -B .wavefoundry/framework/scripts/run_tests.py --qualification-report .wavefoundry/cache/qualification/default.json` with bytecode disabled, CPU provider and reranker disabled passed **12,402 tests across 185 files**, **12 existing skips**, in **798.065 seconds**. All 185 exact worker records are complete and green; skip IDs/reasons match the pre-repair baseline. The existing green receipt and exact report both match current framework inputs `d1ab96d12d77d992c99b700656f18ac2044068c89188efa82e531f416816d5ce`. Recording routine typed reviews during the run did not invalidate qualification. No additional suite was run solely for ledger/progress recording.

- Evidence retention: final outcomes and limits are consolidated here and in the admitted change record; the existing typed `events.jsonl` is machine authority. Routine reviewer reports, raw logs and disposable probes stay outside the repository. The wave remains paused for operator review/closure; no closure, commit, push or new package build was performed.
