# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-11
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20gfk bounded-runtime-reads`
Title: Bounded Runtime Reads

## Objective

Bound configuration, migration-prompt and gap-marker reads while preserving old-runner compatibility and diagnostic refusal semantics.

## Changes

Change ID: `20gfg-bug bounded-config-prompt-and-gap-reads`
Change Status: `implemented`

## Participants

- Coordinator: main session
- Write-owning roles: implementer; coordinator owns lifecycle records and integration
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer

Completed At: 2026-10-12

## Wave Summary

Wave `20gfk` (Bounded Runtime Reads) delivered one change: Bound Runtime Configuration, Prompt and Gap Reason Reads. Notable adjustments during implementation: Bound Runtime Configuration, Prompt and Gap Reason Reads: Readback: bound setup config and standalone prompt observations to 8 MiB and gap reasons to 64 KiB; preserve setup defaults, prompt classifications/old-loader ABI and explicit-clear accounting authority. A stock prompt behind a linked parent currently passes; afterward it refuses without mutation. AC-1–AC-6 cover the three reader modules, five owning test files and architecture note; shared containment, loaders, timeout algorithms and gap transactions stay outside scope.; Bound Runtime Configuration, Prompt and Gap Reason Reads: Six disposable known-bad variants were rejected by named tests; scratch module variants were removed without altering live source.; Bound Runtime Configuration, Prompt and Gap Reason Reads: Exact existing skip identities confirmed by selected verbose execution; no added test skipped on this macOS host.

**Changes delivered:**

- **Bound Runtime Configuration, Prompt and Gap Reason Reads** (`20gfg-bug bounded-config-prompt-and-gap-reads`) — 6 ACs completed. Key decisions: Reuse shared bounded containment for setup/gap reads; keep a small standard-library descriptor observer in the standalone checker.; Bound bytes and verify descriptor/type/path before parsing; preserve established conservative fallbacks.
Retrospective and memory: Invalid deadline values fall back per key without discarding valid neighboring values; regression tests preserve this boundary. The change record preserves contained-read and standalone compatibility limits. Bounded memory proposal returned no eligible candidates; no duplicate memory record was created. No AC or task was deferred.

Cleanup disposition: Only wave.md, the admitted change document and the authoritative ledger are retained. Routine probes and logs remain temporary; no permanent evidence folder or duplicate readiness file was created.

## Watchpoints

- Watchpoint: Operator authorized implementation and pause after review; no closure, commit or push. Use generic repository examples and existing wave/change records only. Qualify the combined source tree before final delivery approvals; intermediate pauses may carry pending combined qualification.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-PER-KEY-OVERFLOW | do_now | no | completed | qa-reviewer, code-reviewer, council-delivery |

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
| plan | 566 | 3,135,440 |
| implement | 90 | 968,312 |
| review | 54 | 411,963 |
| **Total** | **710** | **4,515,715** |

<!-- wave:context-efficiency-state {"generation":194,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":90,"content_source_credit":1109774,"derived_artifact_credit":0,"direct_net":968312,"estimated_tokens_saved":968312,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3392,"response_debit":141307,"source_credit_count":41,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3237},"plan":{"calls":566,"content_source_credit":4433694,"derived_artifact_credit":1582,"direct_net":3135440,"estimated_tokens_saved":3135440,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":40778,"response_debit":1262863,"source_credit_count":203,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":54,"content_source_credit":544032,"derived_artifact_credit":0,"direct_net":411963,"estimated_tokens_saved":411963,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5853,"response_debit":129147,"source_credit_count":21,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2931}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":710,"content_source_credit":6087500,"derived_artifact_credit":1582,"direct_net":4515715,"estimated_tokens_saved":4515715,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":50023,"response_debit":1533317,"source_credit_count":265,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9973},"wave_id":"20gfk bounded-runtime-reads"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 23 | 0 | 20 | 16,358,996 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":20,"estimated_exploration_avoided":16358996,"surfaced_events":23} -->
<!-- wave:exploration-avoided end -->
## Review Checkpoints

- Work allocation: focused implementation and routine independent reviews request gpt-6.1-sol/high; the ambiguous bookkeeping boundary requests gpt-6-astra/high. These are requested settings; runtime identity beyond host reporting is unknown. Tasks are scoped per role with independent review contexts, shared source reads and serialized writes.

- Readiness specialist review: independent code, QA and architecture approved all four plans; security approved the three runtime/qualification waves and participated in all councils. Required docs-contract and release lanes approved their assigned scopes. Current-tree controls only; no future delivery execution is claimed. Review working reports stay in temporary storage.

- Readiness council: pass; fixed architecture, security, QA and reality seats plus rotating docs-contract, preceded by isolated red-team primer and anonymous-first synthesis. Agreement unanimous; maximum severity none; no challenge round needed. Primer depth full. Red-team closing confirmed all original questions addressed and the admitted plan unchanged. Preserve conservative ENOTDIR/refusal return shapes and cause-only diagnostics; test actual or injected recursion/resource failures rather than universal nesting depth. Bound live and .clearing reasons while retaining explicit-clear and concurrent-new-marker authority. Final implementation qualification and delivery approval remain pending.

- Delivery complete (2026-10-12): independent code, QA, architecture and security reviewers approved, and the required delivery council approved. The bounded config reader, standalone incoming prompt observer and conservative gap-reason readers passed real carrier, legacy-loader, restricted-import, publication and explicit-clear controls. Removed-bound, removed-identity, followed-parent and removed-resource-handler variants were detected.

- Council record: full primer, all five thinking stances and three questions; fixed architecture, security, QA and reality seats, rotating docs-contract best-alternative seat, then fresh chair anonymous-first merit synthesis and identity reattachment. Final agreement unanimous; maximum reviewed severity medium, now resolved. No challenge round was needed after focused convergence. Requested delivery models were gpt-6-astra/high for code, architecture, security and chair; gpt-6.1-sol/high for QA, reality, rotating docs-contract and primer. Actual runtime model identity beyond host reporting was not independently observable.

- Resolved disagreement: several initial seats treated the huge-integer deadline defect as preserved historical behavior; reality and the rotating seat correctly tied it to Requirement 1’s explicit independent per-key promise. The required code/QA lanes confirmed the counterexample. `DEL-PER-KEY-OVERFLOW` and cycle-1 repair start preceded the narrow per-key OverflowError fix. Distinct independent code/QA replay cleared both lanes; every fixed seat explicitly weighed the selected alternative. A parseable `10**400` value now retains only its own default while later valid `7` survives. Each-key/boolean/nonfinite/cap controls and removed-catch variants prove the repair; no requirement or approval authority was weakened.

- Limits: accounting poison claims retain the existing recognized live-marker authority; the reproduced dangling-marker diagnostic/snapshot mismatch remains explicitly outside this change. The standalone checker keeps its old-runner standard-library ABI. Fallback component-swap risk, same-inode content changes, total filesystem deadlines and native Windows race closure are not newly guaranteed. No live upgrade or external model download was performed.

- Final default qualification (2026-10-12): canonical `python3 -B .wavefoundry/framework/scripts/run_tests.py --qualification-report .wavefoundry/cache/qualification/default.json` with bytecode disabled, CPU provider and reranker disabled passed **12,402 tests across 185 files**, **12 existing skips**, in **798.065 seconds**. All 185 exact worker records are complete and green; skip IDs/reasons match the pre-repair baseline. The existing green receipt and exact report both match current framework inputs `d1ab96d12d77d992c99b700656f18ac2044068c89188efa82e531f416816d5ce`. Recording routine typed reviews during the run did not invalidate qualification. No additional suite was run solely for ledger/progress recording.

- Evidence retention: final outcomes and limits are consolidated here and in the admitted change record; the existing typed `events.jsonl` is machine authority. Routine reviewer reports, raw logs and disposable probes stay outside the repository. The wave remains paused for operator review/closure; no closure, commit, push or new package build was performed.
