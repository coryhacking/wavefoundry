# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-11
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20e38 rust-cross-module-binding`
Title: Rust Cross Module Binding

## Objective

Bind explicit Rust crate-relative free-function calls to unique indexed definitions while preserving call-site truth and conservative unresolved results.

## Changes

Change ID: `20e13-bug rust-cross-module-call-binding`
Change Status: `implemented`

## Participants

- Coordinator: repository coordinator
- Write-owning roles: implementer, coordinator
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer

Completed At: 2026-10-11

## Wave Summary

Delivered explicit crate-qualified and visible, unique, unshadowed Rust free-function alias binding to indexed crate/module definitions. Stored invocation sites and repeated occurrences survive publication; ambiguous/unsupported calls remain external. Topology and callee changes re-resolve untouched callers with full/incremental parity. Graph builder 56 follows existing refresh invalidation without eager upgrade or reporting work.

All four required ACs and all tasks are implemented; no `[~]` ACs or admitted work was deferred. Cargo/dependency discovery, general Rust resolution, generic turbofish extraction, native Windows and live consumer qualification remain outside admitted scope. Four fresh required delivery lanes approved; no delivery Council was selected. Canonical qualification passed 12,352 tests across 185 files with 12 existing skips; the current matching receipt was proven by the close tool. Closed on 2026-10-11 with explicit operator approval.

Retrospective: complete target paths and unique caller ownership also require per-invocation alias visibility/shadow proof. The graph architecture documentation and named negative/incremental tests retain that decision. Existing quiet-run guidance covers bookkeeping before qualification; temporary checkouts also need a populated Git index. Memory proposal dry-run yielded no eligible durable candidates; no additional memory files were needed. Earlier failed qualification attempts remain distinguished from the successful receipt in Review Checkpoints.

Cleanup: wave.md, admitted change and immutable events.jsonl retain authority. No routine evidence folder was created. The owned temporary qualification checkout was removed; unique cited source baselines, reproducible probes and logs remain in temporary storage. No private consumer identifiers or reporting details were added.

## Watchpoints

- Previous memory wave 20e12 is closed; its uncommitted edits remain intact. Current request authorizes closure, commit/push and a new local test pack.
- No live consumer qualification, Cargo resolution, global receiver-guard relaxation or private downstream provenance in public artifacts.
- Watchpoint: loaded MCP implementation is stale; current-file navigation and fresh CLI probes only.

## Review Checkpoints

- Readiness allocation: standard isolated red-team primer first, four fixed seats and the receipt-selected docs-contract-reviewer rotating seat, with separate code and performance lanes. Independent role contexts; one complete readiness round, bounded focused repair protocol if necessary. Temporary captures only; final outcomes inline here and in the change record.
- First readiness round: unanimous needs revision on ARCH-R1 (visible/unshadowed alias invocation proof), required code/QA/architecture blocked; performance approved feasibility. One bounded Req2/AC2 plan repair recorded before edits. Fresh focused verification must clear all required lanes and current Council readiness; any remaining blocker escalates, without another automatic round.
- Delivery allocation follows the current targeted receipt: fresh code/QA/architecture/performance lanes; no delivery Council required. Standard readiness Council authority remains unchanged.
- Focused readiness completed: ARCH-R1 plan repair independently cleared; four current required lanes and Council approved, Prepare succeeded and implementation opened. One generic implementer owns the declared source/tests and architecture/changelog; coordinator owns lifecycle records and integration. Model choice favors frontier reasoning for scoped AST and incremental identity; no extra delivery Council.
- Delivery round completed on nine frozen paths: fresh code, QA, architecture and performance contexts independently approved; no findings. Code ran five parser/publication tests and a deleted lexical guard mutant; QA ran 13 controls and a compile-valid fixture plus one shadow mutant; architecture ran five tests, its own published topology/ambiguity probe and an ownership mutant; performance proved context counts 1/1/0 for full/changed/idle builds and a duplicate-build mutant. Each mutant failed an assertion with zero errors/skips. Typed approvals are current; no delivery Council was required. No full-suite receipt, live consumer, complete Rust, native Windows or timing claim is supplied by these lanes.
- Qualification coordination: live canonical run passed 12,352 tests/185 files but exited 1 because coordinator appended this wave ledger during execution. No green receipt was recorded. A verified byte-identical isolated copy is running the canonical command so review bookkeeping cannot collide again; current framework inputs match before launch.
- Model allocation: frontier/high requested for code and architecture identity ambiguity; workhorse/high requested for bounded QA and performance controls. Actual runtime identity unknown. Docs-contract delivery review is not applicable: no specs changed. No new durable evidence folder was created.
- Isolated harness correction: the first copy had no populated Git index, causing the tracked-Python census to fail while the other 184 files passed. Only the temporary index was initialized; the affected eight-test canonical control passed with zero skips and source hashes stayed identical. Final qualification rerun is in wf-20e38-canonical-qualified.log; neither failed full run provides a green receipt.
- Final qualification: canonical isolated run exited 0; 12,352 tests across 185 files passed, 12 existing skips, 986.642s. Receipt ran_at 2026-10-11T23:43:56.000809+00:00, inputs 92477e9a685cbfdde55d993ecdc933318202b093bbd357d66f9c0a5c481dee3c; original, isolated and receipt hashes matched before copying the unchanged green receipt locally. All admitted AC/task checkboxes are done and the change is implemented. Required delivery lanes approved with no findings. Full current-docs validation and diff check passed; all edit gates are closed and the owned qualification checkout was removed after receipt verification. Operator approved closure and source publication after the implementation/review handoff; a new local test pack follows.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-R1 | do_now | no | completed | architecture-reviewer, qa-reviewer, code-reviewer, performance-reviewer, council-readiness |

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
| performance-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- Operator closure approval is recorded in the authoritative ledger.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 387 | 0 |
| implement | 43 | 1,282,439 |
| review | 251 | 3,408,248 |
| **Total** | **681** | **4,690,687** |

<!-- wave:context-efficiency-state {"generation":301,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":43,"content_source_credit":1333464,"derived_artifact_credit":0,"direct_net":1282439,"estimated_tokens_saved":1282439,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1317,"response_debit":53027,"source_credit_count":9,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3319},"plan":{"calls":387,"content_source_credit":1312011,"derived_artifact_credit":1543,"direct_net":-107572,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":26429,"response_debit":1398502,"source_credit_count":64,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":251,"content_source_credit":4247883,"derived_artifact_credit":684,"direct_net":3408248,"estimated_tokens_saved":3408248,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16802,"response_debit":845261,"source_credit_count":91,"source_credit_drop_count":0,"structural_source_credit":18888,"workflow_prompt_credit":2856}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":681,"content_source_credit":6893358,"derived_artifact_credit":2227,"direct_net":4583115,"estimated_tokens_saved":4690687,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":44548,"response_debit":2296790,"source_credit_count":164,"source_credit_drop_count":0,"structural_source_credit":18888,"workflow_prompt_credit":9980},"wave_id":"20e38 rust-cross-module-binding"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 10 | 0 | 7 | 7,436,564 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":7,"estimated_exploration_avoided":7436564,"surfaced_events":10} -->
<!-- wave:exploration-avoided end -->
