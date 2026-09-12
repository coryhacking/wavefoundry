# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-11
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1xny3 sqlite-graph-consolidation-evaluation`
Title: SQLite graph consolidation evaluation

## Objective

Determine whether native SQLite graph tables and shared publication can reduce memory and operational complexity without losing graph behavior. Evaluate graph expansion before reranking and Cypher independently; produce measured decisions and a safe proposed conversion path.

## Changes

Change ID: `1xny2-task evaluate-sqlite-graph-consolidation`
Change Status: `complete`

## Participants

- Coordinator: Engineering
- Write-owning roles: coordinator (plan/results/ADR), implementer (isolated wave-local harness after readiness)
- Requested review lanes: architecture-reviewer, code-reviewer, qa-reviewer, performance-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer

Completed At: 2026-09-10

## Wave Summary

Completed the SQLite graph evaluation, with reproducible isolated harnesses, paired graph/query measurements, lifecycle/recovery probes, benchmark and review records, and proposed ADR 1xny4. The result supports unified persistence with the existing resident graph cache; production conversion is separately planned in readied wave 1xny6. No production source or live storage changed.

The operator accepted the measured timings. General memory/disk savings and complete production publication/cache integration were not demonstrated; prior failures and qualification limits remain recorded.

Intentional deferral — `1xny2-task evaluate-sqlite-graph-consolidation`:

- AC-4: Paired ranking/quality qualification intentionally deferred after the clean baseline API exceeded the frozen five-second deadline in its first warm-up. Thirty source-grounded questions and independent QA are frozen; CPU fallback and 119+3 successful reranks are recorded. Neither variant ran; current ordering is retained without an adoption claim.
- Associated graph-expansion/reranking task: deferred with AC-4 after the clean baseline screening stop; zero paired observations, no ranking-quality claim.

Retrospective: keep storage and serving-cache decisions separate, distinguish isolated parity from production generation guarantees, and preserve failed observations rather than replacing them with later passes. These lessons are retained in ADR 1xny4 and the benchmark/review records. The close-time memory proposal produced zero candidates; no additional promotion was warranted.

## Watchpoints

- Watchpoint: evaluation only; no live index conversion, production changes, shared dependency installation or packaging.
- Normalize first; evaluate shared publication only after native graph parity passes. Keep retrieval ordering independent.
- Existing warm adjacency cache and graph algorithms are the baseline; Cypher adoption is not presumed.
- Freeze performance/quality thresholds at readiness and record unexecuted platforms honestly.

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
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| performance-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- Operator authorized closure in the current request; typed operator-signoff records that authorization.

## Dependencies

- Builds on closed wave `1xjmm unified-sqlite-vector-storage`; no open-wave dependency.

## Current assumptions

Local-only deployment and preservation of existing graph APIs/semantics. Retain/defer is a valid evaluation outcome.

## Outputs produced or expected

One consolidated change doc, minimal reproducible harness/fixtures, one benchmark receipt, one decision ADR and the typed review ledger.

## Review checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-09: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, performance-reviewer; rotating-seat: performance-reviewer; strongest-challenge: differential agreement can hide shared graph defects and vague budgets can predetermine a winner; strongest-alternative: retain compact persistence with addressable storage and a bounded hot-neighbor cache)
- Council agreement: unanimous; unresolved severity: none. The actual full council exceeded the tool receipt's minimal red-team/security roster. Fixed seats weighed the rotating alternative; anonymized synthesis and closing red-team reconciliation found no blocker.

| Readiness seat | Verdict and load-bearing evidence |
| --- | --- |
| red-team | PASS after explicit numeric gates, independent oracle and bounded sampling; five in-memory clause-deletion mutants were rejected. Incomplete metrics remain unqualified. |
| architecture-reviewer | PASS; source-grounded store/adjacency/weighted-path boundaries match the plan. Preserve public edge projection and revisit semantics while separately checking mathematical graph expectations. |
| security-reviewer | PASS; scratch ownership, epoch-bound snapshots, isolated crash targets and no shared-environment mutations constrain experiments. Actual harness enforcement remains delivery evidence. |
| qa-reviewer | PASS; ACs distinguish parity, judged relevance, optional scaled stops and mandatory sample completion. Independent hand-derived fixtures address shared-baseline defects. |
| reality-checker | PASS; source checks support baseline claims; plan/negative-control checks do not imply benchmarks or platform qualification occurred. |
| code-reviewer | PASS; baseline source anchors and scratch-only experimental boundaries verified, including graph loading that can auto-rebuild. Five in-memory boundary mutants rejected. |
| docs-contract-reviewer | PASS; brief/AC/scope and sampling/stop conditions align. Original nine-boundary check passed; a production-write-authorization mutant was rejected. |
| performance-reviewer | PASS; real-corpus-first ordering, three paired rebuild medians with retained durations/maxima, pooled fast-operation samples and explicit limits make the evaluation bounded. Retaining compact storage/cache remains a valid alternative. |

Readiness plan reviewed at SHA-256 `fc8098571ede0db0bca01621d0d49a9cd4763574b15f898512c76c0af961b53c`. Typed authority is `events.jsonl`: `run-readiness` and `ev-approval-wave-council-readiness`, with individual readiness lane approvals recorded separately. These are plan approvals, not delivery approvals. No benchmarks, production changes or native platform qualification were performed.

Optional plan review: self-answered all scope/decision branches using current graph/semantic boundaries; no operator-only question remains. Added fixed evaluation gates, independent structural expectations, sample/resource-limit rules and a separately gated production conversion. Native parity gates shared-store evaluation; retrieval ordering and Cypher remain independent decisions.

### Focused re-Prepare — AC-4 deferral, 2026-09-10

- **Prepare-phase Wave Council [prepare-council] — 2026-09-10: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, performance-reviewer; rotating-seat: performance-reviewer; strongest-challenge: a bounded stop must not become a comparative winner; strongest-alternative: separately authorized paired CPU evaluation after baseline and deadline prerequisites)
- Full isolated primer preceded the four isolated fixed seats and rotating performance seat. Randomized anonymous synthesis: unanimous, maximum severity none; all fixed seats explicitly weighed the rotating alternative and reaffirmed. The task mismatch surfaced by the primer was resolved to `[~]` and security confirmed its note resolved.
- architecture-reviewer: no findings; harness stop/aggregation and matching hash support zero pairs, not query latency or strict cancellation qualification.
- security-reviewer: no findings; inspected scratch/cache/owned-child boundaries; historical absence of writes remains a runtime evidence limitation.
- qa-reviewer: no findings; AC-4/task deferrals and frozen protocol align; false-completion, threshold-relaxation and promoted-history controls rejected.
- reality-checker: no findings; source/receipt reject winner, warm-p95 and exhaustive-relevance claims.
- performance-reviewer: no findings; fabricated percentile/completed-AC/removed-protocol controls rejected. Future paired CPU work can answer efficacy only after its prerequisites; it cannot repair this run retrospectively.
- Supplemental code-reviewer and docs-contract-reviewer: no findings for this narrowed readiness contract. Both ran in the independent moderator context, not separate contexts from each other; false completion, production authority and protocol-retuning controls rejected.
- Scope: only unqualified AC-4/task deferral and preservation of original evaluation/production boundaries. No delivery approval, performance/quality winner, strict five-second cancellation proof or production conversion is implied. Configuration elapsed is not query latency. Detailed compact record: `/tmp/graph-1xny3-scope-review.json`; typed current approvals bind receipt `review-policy-8644cc3e3cab4b9bbbe2`.

### Focused re-Prepare — continued graph evaluation, 2026-09-10

- **Prepare-phase Wave Council [prepare-council] — 2026-09-10: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, performance-reviewer; rotating-seat: performance-reviewer; strongest-challenge: passing fresh graph timing and partial transactions must not imply complete lifecycle consolidation; strongest-alternative: actual shared-file cached screen followed by one real cross-file publication mutation before repeated rebuilds)
- Full isolated five-stance primer preceded four isolated fixed seats and the rotating performance seat. Randomized anonymous synthesis was unanimous, maximum severity none; no blocking finding was downgraded. All four fixed seats explicitly weighed the final rotating alternative and reaffirmed.
- architecture-reviewer: PASS; source-verified extraction-store, graph-file and binding publication remain separate today. Require explicit semantic, extraction, graph, community, generation and cache participants; excluded state retains its fences.
- security-reviewer: approved with notes, no blocker; propagate scratch ownership through every real producer and output path, preserve vector provenance and limit crash probes to owned children. Inspected helpers are not fresh runtime confinement evidence.
- qa-reviewer: PASS; fresh 500 ms graph screen, original complete-tool allowances, rebuild/startup gates, historical measurements and AC4 deferral remain distinct. False completion, history promotion and omitted integration-gap controls were rejected.
- reality-checker: PASS; source confirms sequential graph finalization today. Prepared rows cannot qualify full source rebuilds; its in-memory false-complete-rebuild control was rejected.
- performance-reviewer: PASS; measure H on the actual shared file, then one real changed-file transaction with unchanged-caller invalidation, old/new readers and rollback before costly rebuild pairs. Seven omission controls and positive budget arithmetic checks passed. One successful mutation cannot replace mandatory sampling.
- Supplemental code-reviewer and docs-contract-reviewer: PASS for continued readiness; seven boundary-deletion controls rejected. These roles share the independent moderator context, not separate contexts from each other. Existing H public measurements use the separate graph database; fresh shared-file evidence remains required.
- Execution improvement: record a producer/state participation and retained-fence matrix per probe; distinguish preserved vectors from genuine regeneration. A provider rename/removal with an unchanged caller and later reversal is the preferred first lifecycle probe. Retain A whenever integration or qualification remains incomplete.
- Frozen plan SHA-256: `e9d1338161ffe1d3c275b8b71309bf8b881e19eed41e21e301b15e360dd7de71`. Compact review fragment: `/tmp/graph-1xny3-round2-readiness.json`; current typed approvals bind `review-policy-c3409797274a80e698fc`. This is readiness only: no fresh benchmark, production conversion, delivery qualification, closure or commit.

### Final evaluation review — 2026-09-10

- **Prepare-phase Wave Council [prepare-council] — 2026-09-10: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: isolated atomic publication must not become production adoption approval; strongest-alternative: separate immutable store generations with atomic manifest activation and response-wide pinning)
- Final result text changed the policy input digest. The independent council approved a final-scope readiness rebind to `review-policy-03aa9b2945691d73e22c`; original readiness authorized the experiments. This rebind introduces no new implementation scope. Required lanes separately attest readiness and delivery in `events.jsonl`.
- Delivery council: PASS for evaluation only. Full primer, four isolated fixed seats, rotating docs-contract seat and supplemental code/performance lanes reported no actionable findings. Fixed seats explicitly weighed the separate-generation alternative; neither it nor a compact shared snapshot is a measured production winner. Closing red-team agreed. No production adoption approval follows.
- All required lanes passed with their scope limits. Code exercised the real CLI scratch guard and owned-child monitoring; QA exercised source rename/remove/rebind and pinned publication; security checked owned scratch, offline-cache refusal and rollback; reality checked real participant omissions. Architecture's fresh final pass checked the actual ADR contract, with original runtime probes separately attributed. Docs and performance independently reproduced raw metrics and rejected corrupted report claims. Known-bad mutation tables and per-seat limitations are retained in [the consolidated review reports](review-results.json).
- Agreement is partly correlated through shared evidence and primer. Initial synthesis used randomized anonymous extracts, with partially identifiable technical content disclosed. The original architecture pass lacked a recorded pre-primer concern; a fresh final architecture pass supplied it without inventing prior process facts. No disagreement or blocking finding remains.
- Preserved exclusions: failed full-report adoption screen, the original unexplained maintenance assertion, AC4's legitimate `[~]` stop, historical/source cohort differences, and unimplemented production epoch/cache/whole-response boundaries. No general memory reduction, end-to-end retrieval quality or cross-platform qualification is claimed.
- Reviewed fingerprint: `b33bd36dd5654e0ec2c6f36dbcd25c271d4cd16fd94f06c124f4fdac262a5a1e`. After review, only completion/status bookkeeping changed the reviewed change doc; the reviewed source and results remain unchanged. Full reports are consolidated in one JSON artifact; typed authority remains `events.jsonl`. Memory proposal produced zero candidates; no memory promotion was needed.

Closure reconciliation: admitted change complete; all ACs/tasks are `[x]` or explicitly `[~]`; required readiness/delivery approvals current; docs-contract review performed with no actionable findings; no specs changed. Retrospective and memory checkpoint completed above. Session handoff will record no active implementation and readied conversion wave 1xny6. Framework source did not change during closure; the close tool verifies its existing current test receipt.

## Completion criteria

Reconcile every admitted AC/task with evidence, including explicit prerequisite stops; record separate decisions and required reviews.

## Handoff or next-wave notes

Evaluation and required reviews are complete; operator-authorized closure is recorded through the close tool. Production stores and framework source remain unchanged. Proposed ADR 1xny4 recommends evaluating shared persistence with serving-cache choice kept independent. Any production conversion requires its own admitted and readied implementation change.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 68 | 631,005 |
| implement | 455 | 2,373,696 |
| review | 151 | 3,413,570 |
| **Total** | **674** | **6,418,271** |

<!-- wave:context-efficiency-state {"generation":639,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":455,"content_source_credit":3624272,"derived_artifact_credit":5072,"direct_net":2373696,"estimated_tokens_saved":2373696,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":28222,"response_debit":1233191,"source_credit_count":110,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5765},"plan":{"calls":68,"content_source_credit":760243,"derived_artifact_credit":1638,"direct_net":631005,"estimated_tokens_saved":631005,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8291,"response_debit":134851,"source_credit_count":29,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12266},"review":{"calls":151,"content_source_credit":3880570,"derived_artifact_credit":2613,"direct_net":3413570,"estimated_tokens_saved":3413570,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9255,"response_debit":462247,"source_credit_count":87,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":674,"content_source_credit":8265085,"derived_artifact_credit":9323,"direct_net":6418271,"estimated_tokens_saved":6418271,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":45768,"response_debit":1830289,"source_credit_count":226,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":19920},"wave_id":"1xny3 sqlite-graph-consolidation-evaluation"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 19 | 0 | 9 | 12,879,301 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":9,"estimated_exploration_avoided":12879301,"surfaced_events":19} -->
<!-- wave:exploration-avoided end -->
