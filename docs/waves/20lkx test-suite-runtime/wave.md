# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-14
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20lkx test-suite-runtime`
Title: Test Suite Runtime

## Objective

Reduce avoidable qualification work by removing duplicated inherited tests and bounding ordinary scanner fixtures, preserving unique assertions and an explicit whole-checkout diagnostic audit.

## Changes

Change ID: `20lgv-debt bounded-test-suite-work`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer

Completed At: 2026-10-14

## Wave Summary

Wave `20lkx` (Test Suite Runtime) delivered one change: Bounded Test Suite Work. Notable adjustments during implementation: Bounded Test Suite Work: Final canonical qualification green: 11,609 tests / 187 files / 12 existing skips, 627.384 seconds wall and 2,907.103 worker-seconds. Before: 12,504 / 187 / 12, 763.799 wall and 3,701.111 worker-seconds. Count delta is exactly 896 inherited repeats removed plus one audit-dispatch control. Docs-lint 448.8 to 52.444 seconds; prefix-collapse 267.0 to 16.038; no controlled causal speedup claim under varying host load.; Bounded Test Suite Work: Fresh focused code/QA independently cleared the fixture finding: original historical path and existing exception retained, exact census and stale-entry controls pass, bounded audit has zero skips/writes under default and nondefault declared roots. Reintroduced literal, inappropriate historical relocation and removed write containment are detected.

**Changes delivered:**

- **Bounded Test Suite Work** (`20lgv-debt bounded-test-suite-work`) — 4 ACs completed. Key decisions: Remove proven duplicates and bound ordinary scanner work; retain explicit real-checkout audit.; Use the just-completed canonical run as baseline and compare deterministic work counts plus subsequent focused/full results.
## Watchpoints

- Watchpoint: preserve all distinct test bodies and intentional fixture variants; no ordinary skips introduced.
- Machine contention is a timing confounder, not permission to weaken assertions.
- No runner, production scanner, model, seed, configuration, commit or package changes.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 20lkx-profile-literal-census | do_now | no | completed | qa-reviewer, code-reviewer |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| performance-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: explicit closure and commit instruction received 2026-10-14.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review checkpoints

- Operator requested closing completed 20lul first, then improving test runtime; 20lul closed before this wave was planned.
- Readiness: approved with no findings by isolated red-team primer; fixed architecture, security, QA and reality seats; rotating docs-contract seat; council-chair synthesis. Code/architecture shared one disclosed independent context; QA/performance shared another. Strongest challenge was silently omitted no-keyword files; exact literal eligibility and real completion observations address it. The alternative retained the same narrow scope and explicit audit.
- Delivery allocation: two fresh independent contexts cover code/architecture and QA/performance; targeted policy requires no delivery council. Requested gpt-6.1-sol/high for bounded test topology, coverage and containment work; actual runtime model identity is not exposed. Reports stay temporary; durable outcomes stay here and in typed evidence.

- Delivery evidence: code/architecture and QA/performance independently verified unique method identities, helper resolution, exact scanner accounting and audit containment. Known-bad controls detect removed unique methods, omitted eligibility/processing, unknown skip reasons, absent cost rows and disabled write containment. One introduced profile-census finding was repaired and independently reverified by a fresh QA/code context; no delivery council was required.
- Final qualification: default six-worker run passed 11,609 tests / 187 files / 12 skips in 627.384 seconds. The earlier red run took 625.671 seconds and is not green evidence. Docs-lint fell from 1,226 executions / 448.8 seconds to 330 / 52.444; prefix module from 17 / 267.0 to 18 / 16.038. Timings are observational; the structural work reduction is deterministic. Largest remaining file durations were indexer 314.372, server lifecycle 269.551 and server tools 220.814 seconds.
- Durable evidence anchors: `.wavefoundry/framework/scripts/tests/test_docs_lint.py` helper-only bases and original test methods; `NothingNewIsSkippedTests`, `CheckoutAuditDispatchTests`, `_checkout_audit_suite`, and `CostReportNamesTheExpensiveRuleTests` in `test_secrets_prefix_collapse.py`; existing `ProfileLiteralCensusTests` and its unchanged historical-input exception. Raw execution/reviewer reports remain temporary, with no new evidence folder.

- Final handoff: all required code, QA, architecture and performance delivery approvals are current; every AC/task is complete; the single finding is terminal. Paused pending operator closure, with gates closed. No commit, push, package or permanent evidence folder was created.

- Closure reconciliation: all four ACs and four tasks complete; no intentionally deferred ACs. Docs-contract review: not applicable because this wave changes testing architecture, not docs/specs. Operator authorized closure and commit on 2026-10-14.
- Retrospective/memory: helper-only fixture bases and bounded default scanner inputs are documented in testing architecture. The proposed profile-census repair memory was not selected: its historical-input constraint is already expressed by the unchanged census exception and shared historical-path regression. No new wave-linked candidates were created.
- Cleanup: retain wave.md, the admitted change and authoritative events.jsonl only; no evidence folder or disposable scratch output was created.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 74 | 0 |
| implement | 61 | 79,655 |
| review | 60 | 138,287 |
| **Total** | **195** | **217,942** |

<!-- wave:context-efficiency-state {"generation":148,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":61,"content_source_credit":339867,"derived_artifact_credit":0,"direct_net":79655,"estimated_tokens_saved":79655,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2356,"response_debit":260686,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2830},"plan":{"calls":74,"content_source_credit":242111,"derived_artifact_credit":2472,"direct_net":-138071,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7678,"response_debit":378781,"source_credit_count":26,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":60,"content_source_credit":289235,"derived_artifact_credit":1056,"direct_net":138287,"estimated_tokens_saved":138287,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":15057,"response_debit":139878,"source_credit_count":30,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2931}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":195,"content_source_credit":871213,"derived_artifact_credit":3528,"direct_net":79871,"estimated_tokens_saved":217942,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25091,"response_debit":779345,"source_credit_count":76,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9566},"wave_id":"20lkx test-suite-runtime"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 7 | 0 | 4 | 4,876,090 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":4876090,"surfaced_events":7} -->
<!-- wave:exploration-avoided end -->
