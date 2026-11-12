# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-11
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `231kh explainable-project-statistics`
Title: Explainable Project Statistics

## Objective

Operators of multi-language projects can explain what the statistics count, which files and scan work remain unobserved, where open lifecycle work sits, and what the context-saving estimate means. Add explicit code roles, inline-test precision and optional directory views while retaining shared collectors, compatible fields, downstream vocabulary and read-only reporting. Implementation is complete; closure is authorized by the operator.

## Changes

Change ID: `231kf-enh explain-statistics-coverage-and-health`
Change Status: `implemented`

Change ID: `231kg-enh classify-project-code-and-inline-tests`
Change Status: `implemented`
Depends On: `231kf-enh explain-statistics-coverage-and-health`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (serial ownership of shared files)
- Requested review lanes: code-reviewer, architecture-reviewer, qa-reviewer, security-reviewer, performance-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer, security-reviewer

Completed At: 2026-11-11

## Wave Summary

Wave `231kh` (Explainable Project Statistics) delivered two changes: Explain statistics coverage and health and Classify project code and inline tests.

Intent outcome: implemented technical outcomes are supported by exact fixture and public-route tests: 231kf exposes observed omissions, dated local scan history versus outstanding coverage, memory populations, literal checklist work and inspectable accounting; 231kg separates declared roles and syntax-bounded test extents without changing legacy counts or exclusions. Fresh profiling replay retained all operator mappings. The pre-repair full suite passed 12,813 tests across 248 files with 12 reported skips. Docs-contract found missing CLI path examples; one bounded repair is independently reverified by docs, code and QA, restoring the technical intent assessment. Final reviewed-tree qualification passes 12,814 tests across 248 files with 12 reported skips; human comprehension, Tensorwell live counts and native Windows execution are not established. QA and council independently confirm this assessment within those limits.

Closure qualification: the current framework receipt proves 12,822 passing tests across 249 files, with 12 reported skips, in 604.553 seconds; the earlier counts above describe the statistics review boundary. Canonical close reported no diagnostics and removed the owned disposable work area.

**Changes delivered:**

- **Explain statistics coverage and health** (`231kf-enh explain-statistics-coverage-and-health`) — AC-1, AC-2, AC-3, AC-4, AC-5 and AC-6 completed. Key decisions: Operator accepted policy-excluded evidence, opt-in per-wave token detail and execution-only per-edit scan observations; Extend existing collectors and producer-owned observations, then format them.
- **Classify project code and inline tests** (`231kg-enh classify-project-code-and-inline-tests`) — AC-1, AC-2, AC-3, AC-4 and AC-5 completed. Key decisions: Remove inferred lifecycle evidence roles; retain explicit evidence roles for eligible files and preserve role mappings during re-profiling; Explicit literal path roles plus bounded Rust syntax spans; retain compatibility counters.

## Watchpoints

- Watchpoint: Operator authorized closure, commit and push; release remains held. Preserve unrelated local 1.42.0+q2u7 build metadata. Scanner history is observation, not a new clean guarantee; stats must not run scans. Existing production/test JSON meanings stay compatible while improved views are additive.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 231kh-docs-cli-path-examples | do_now | no | completed | code-reviewer, qa-reviewer, docs-contract-reviewer |
| 231kh-profile-label-fixture | do_now | no | completed | qa-reviewer, code-reviewer |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| performance-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-11: Intent outcome: both statistics changes are implemented and independently approved. Maintained public-route, collector, human-output and profile controls support explainable coverage, explicit roles, bounded inline-test classification and compatible reporting. The final current repository suite passes 12,822 tests / 249 files / 12 skips in 604.553 seconds, including the later 237ee guidance tests; this is current qualification, not an attribution of all tests to this wave. Native Windows, live Tensorwell results, human comprehension and measured token savings remain unverified.

2026-11-11: Closure retrospective and evidence disposition: literal output must be tested alongside JSON, and profile-specific expectations must use the active vocabulary. Maintained test_project_stats.py, test_stats_explainability.py, test_stats_roles.py, test_stats_scan_observations.py and their exact negative controls preserve those lessons and reproduce the relevant defects. Existing project rules cover the broader ownership and profile principles; no additional memory candidate is needed. memory_propose dry-run returned zero eligible drafts and wrote nothing. Typed ledger and change Progress Logs retain the review outcomes, boundaries and test evidence; disposable reports, source copies and green logs under .wavefoundry/work/231kh contain no unique proof requiring retention. Canonical closure may clean that owned area. Wave 237ee and its work remain untouched.

2026-11-11: Delivery council PASS, intent establishes for 231kf, 231kg and Objective. Actual roster: six required specialist lanes (code, QA, architecture, docs-contract, performance, security), standard red-team primer/closing, docs-contract rotating best-alternative seat and fresh council-chair. One medium CLI path-display finding was repaired once and independently cleared by docs/code/QA; no unresolved findings. Strongest alternative retained the additive collector design while testing qualifications in actual human output; no new walk, classifier or automatic scan. Chair independently executed QA-authored zero/one/twelve-file CLI replay and rejected the exact old formatter, with source hashes unchanged. Same-host/model-family evidence is correlated; identities were visible before chair synthesis, so blind first-pass synthesis is not claimed. Final canonical receipt passes 12,814 tests across 248 files with 12 reported skips in 863.764 seconds.

2026-11-11: Intent outcome: implemented technical outcomes are supported by exact fixture and public-route tests: 231kf exposes observed omissions, dated local scan history versus outstanding coverage, memory populations, literal checklist work and inspectable accounting; 231kg separates declared roles and syntax-bounded test extents without changing legacy counts or exclusions. Fresh profiling replay retained all operator mappings. The pre-repair full suite passed 12,813 tests across 248 files with 12 reported skips. Docs-contract found missing CLI path examples; one bounded repair is independently reverified by docs, code and QA, restoring the technical intent assessment. Final reviewed-tree qualification passes 12,814 tests across 248 files with 12 reported skips; human comprehension, Tensorwell live counts and native Windows execution are not established. QA and council independently confirm this assessment within those limits.

2026-11-11: Operator-directed plan amendment: lifecycle evidence stays policy-excluded; eligible evidence uses explicit roles; per-wave token detail is opt-in; only executed per-edit scanning updates latest scan; history is machine-local; re-profiling preserves roles. Requirements and ACs changed. Earlier readiness approvals are historical for the previous plan; focused re-Prepare and current lane/council approvals are required before implementation. No source was edited.

- 2026-11-11: Prepare wave — readiness verdict PASS, intent establishes for both changes and Objective, current receipt review-policy-8ead4b8bedd04cbf47c3. Actual six required specialist lanes independently approve; standard red-team primer and closing plus docs-contract rotating best-alternative seat feed a fresh council-chair synthesis. Unanimous, max severity none, no findings, no repair or challenge round. Chair independently passed empty-section/fixed-error controls and rejected the legacy Production headline with the intended Non-test oracle. Falsification check: correct additive fields could still mislead, but existing presentation ACs require effective-first values and adjacent qualifications. Human comprehension/native Windows remain unverified. Synthesis limitation: anonymous summaries read first, but written merit assessment followed a batch exposing role mapping; perfectly blind recorded synthesis is not claimed. Required lane independence remains as recorded.

- 2026-11-11: Docs-contract and performance readiness PASS on current receipt. Docs collector/presenter control preserved four record statuses and rejected the misleading Production headline for tooling while retaining legacy JSON. Performance control observed one shared collection for code/TODO and zero for empty selection; baseline Rust oracle rejected unchanged counts. All six required lanes approve. Red-team closing found no unresolved primer contradiction; no repair or challenge round ran. Same-host/model-family evidence is correlated; repeated baseline controls are corroboration, not additional field samples.
- Implementation notes: attach Rust attributes to their following sibling items; retain the configured file cap (zero means explicitly unlimited today); bound stored path examples as well as rendered output; analyze each eligible Rust file at most once across main/role/directory views. Existing ACs own these checks. The strongest cheaper alternative, presentation-only clarification, cannot recover missing full history, omitted size paths or inline spans; the two changes remain justified.

- 2026-11-11: QA readiness PASS: real scratch public collector/CLI parity retained unique totals while the current Rust path-only result (7 production/0 test) and Production label fail the proposed improved oracles. Canonical scanner-owner full then incremental dropped full identity; injected save failure preserved prior bytes. Security readiness PASS: malformed findings and secret-bearing exceptions expose only fixed unavailable reasons; empty coverage history does not establish full/current clean state, and malformed history stays incomplete. All four first lanes found no blocker; future behavior, native execution and field usefulness remain unqualified.
- 2026-11-11: Optional Review plan self-answered branches: preserve legacy fields because current schema consumers exist; use explicit role roots rather than interpreting AGENTS.md; retain lexical counting rather than introduce compiler semantics; no source evidence supports reconciling Tensorwell proposals with recorded memories, so distinguish populations; scan state is historical observation and missing history stays unknown; request/response accounting is not provider billing. These choices are explicit in Requirements and ACs. No unresolved operator strategy or authority branch remains in the admitted scope. Stop condition: all planning branches resolved; implementation awaits separate direction.

- 2026-11-11: Round 1 code readiness PASS: existing Rust parser accepted whitespace-equivalent cfg(test), with sibling attribute nodes and bounded module span excluding later live code. Six-line current collector returned production=6/test=0 and failed the intended five-test-line oracle; empty-section public collector control passed. Architecture readiness PASS: AST census found seven calls across run_secrets_scan, scan_secrets (two), indexer, build_scan_allowlist and wave_lint_lib/cli (two); deliberate omission of docs validation was rejected. Latest-only scan-state overwrite confirmed. No future implementation/native execution claim. Typed lane approvals retain scoped integrity attestations.
- Implementation note: build_scan_allowlist temporarily changes the allowlist; the shared observation publisher must preserve that scope/rules identity and never present it as current-clean health. Human formatting must prioritize effective counts and adjacent unknown/partial/history qualifiers over legacy compatibility counters. These clarify existing obligations without new scope. Durable proof is the named source census/control and retained typed evidence; disposable reviewer reports are aids.

- 2026-11-11: Brief: implement the nine accepted Tensorwell feedback themes in two serialized changes, improving report usefulness without automatic scans, build execution or scope expansion. Product-owner acknowledgment: the operator requested this wave and preparation/review; adoption and implementation remain separate. Current Prepare receipt selects standard primer depth and targeted council seats red-team plus docs-contract-reviewer; all six required independent specialist lanes still review. Docs-contract is the rotating best-alternative seat. Shared scanner observations and path classification are explicitly reviewed by security, architecture and performance.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-11 | Observe: focused profile-label repair independently passes code and QA review. Default and second-profile runs each pass 18 tests, zero skips. Hardcoded renderer and JSON-mutating controls both fail the retained assertions. Finding terminal; affected approvals restored; other lanes/council unchanged because no product boundary changed. | Cycle-2 typed reverification and approvals. Only test_project_stats baseline expectation line changed; parent moved existing changelog bullet into 1.42.0 without wording changes. Release qualification remains parent-owned and pending. |
| 2026-11-11 | Observe: release second-profile qualification exposed a default-only test expectation, while the actual Sets/Waves human output was correct. Recorded finding/repair_start cycle 2; one test line now derives baseline labels from active vocabulary, retaining explicit alternate-profile and unchanged-JSON assertions. Default and second focused runs each pass 18 tests with zero skips. | 231kh-profile-label-fixture; test_project_stats.test_profile_changes_only_human_labels. No production/schema/policy change. Fresh affected code/QA verification pending; parent owns renewed full release qualification. |
| 2026-11-11 | Observe: final Review reports current technical approvals; close dry-run accepts green framework receipt and docs/garden checks. Operator signoff is pending; memory-validation readiness cannot be established because persisted indexer runtime is stale. No closure or index recovery performed. | Dry-run diagnostics missing_operator_signoff and memory_validation_check_failed/index_runtime_stale. Existing index preserved; no setup authorization inferred. Review also advises historical high-severity finding, whose single current head is repaired/terminal. |
| 2026-11-11 | Observe: final reviewed tree passes canonical qualification, 12,814 tests / 248 files / 12 skips / 863.764 seconds. All eleven ACs and tasks done; six specialist approvals and council current, one repaired finding terminal. Both edit gates closed. | Successful framework test receipt and full-suite-reviewed.log; final source frozen through qualification. Wave stays OPEN pending operator close; no commit, push or package. |
| 2026-11-11 | Observe: scalar-list repair clears independently. Docs runs six tests and exact original/bounded examples; code proves the exact two-line source delta and rejects the old formatter; QA independently checks zero, one and twelve oversized files. All affected approvals restored and AC-1 marked complete. | Typed cycle-1 reverification and current code/docs/QA approvals; exact old formatter fails filename oracle while count/omitted survive. Red-team closing finds no unresolved challenge. Final full receipt pending; no scope or authority boundary changed. |
| 2026-11-11 | Observe: docs-contract found human CLI omitted scalar path-list entries despite correct JSON. Recorded finding and repair_start before a two-line formatter repair; new actual CLI/real-walker regression checks ten of twelve oversized filenames and omitted=2. 21 targeted tests pass; fresh affected code/docs/QA checks and replacement full receipt remain. | 231kh-docs-cli-path-examples, cycle 1; test_human_cli_keeps_bounded_skipped_paths_and_omitted_count. Collection/schema/bounds unchanged; performance approval remains applicable. No edit landed during a review round. |
| 2026-11-11 | Observe: fresh QA and architecture delivery lanes approve without findings. QA maps all 11 required ACs and confirms Intent outcome with field limits; 32 targeted tests include populated registered MCP/CLI parity. Architecture runs nine ownership/transition controls and an independent mixed CLI oracle. | Typed approvals; old Rust path-only mutant rejected by independently hand-counted test-line oracles. One walk and fixture byte equality verified. All frozen paths unchanged; no host reload or native Windows claim. |
| 2026-11-11 | Observe: fresh code and security delivery lanes approve without findings. Code ran 28 targeted tests plus mixed Rust/Swift CLI oracle; security ran 15 tests plus disclosure/no-execution controls. All 25 frozen paths stayed unchanged. | Typed delivery approvals; old path-only Rust and unsafe-history disclosure injections detected. Audit serialization remained in scratch, no-work history unchanged. Evidence covers local fixtures, not native Windows/live Tensorwell. |
| 2026-11-11 | Observe: canonical qualification passes 12,813 tests across 248 files in 663.886 seconds, with 12 reported skips. Source frozen for fresh independent delivery review; no native Windows or live Tensorwell claim. | Successful framework receipt; `.wavefoundry/work/231kh/full-suite-final.log`; exact reviewed source/doc blobs in disposable delivery-fingerprint.json. Prior red run and bounded integration repairs recorded above. |
| 2026-11-11 | Reflect: canonical qualification ran 12,809 tests across 248 files in 612.855 seconds (12 skips), with five failing files. Real integration gaps: new parser/scan imports escaped reload closure, and a checkout audit wrote scan-history artifacts despite its read-only contract. Repair these boundaries without weakening controls; also update intentional wf_stats signature goldens/digest and profile-aware test literals. No green receipt or delivery approval claimed. | `.wavefoundry/work/231kh/full-suite.log`; `ReloadClosureGuardTests`, `CheckoutAuditDispatchTests`, handler/schema golden tests and profile literal census. Salience: shared publication must honor every existing read-only caller, and new imports extend hot-reload obligations. |
| 2026-11-11 | Observe: focused readiness refresh passed all six required lanes and council on amended receipt; canonically readied then activated. Independent retained readiness contexts authored no repair; no new independent-sample claim. Corrected earlier inferred-evidence judgment explicitly. | `review-policy-227ab1d6223cabaca5db`; typed approvals retain observations and limitations. Shared-source implementation split into disjoint producer and report lanes; registry integration owned by coordinator. |
| 2026-11-11 | Thought: refresh affected readiness after operator-approved amendments before opening the wave; no source edit until all current approvals exist. Then implement 231kf report/scan observations before 231kg roles/parser/directory reporting, serializing shared statistics/API files. Use implementer for the cross-cutting report and scanner-owner work; required independent delivery lanes follow focused tests and full qualification. | Current receipt `review-policy-227ab1d6223cabaca5db`; exact prior/current snapshots and independent delta reviews. |

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 178 | 1,690,458 |
| implement | 158 | 2,513,768 |
| review | 237 | 2,506,845 |
| **Total** | **573** | **6,711,071** |

<!-- wave:context-efficiency-state {"generation":460,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":158,"content_source_credit":1693357,"derived_artifact_credit":2856,"direct_net":2513768,"estimated_tokens_saved":2513768,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5041,"response_debit":224565,"source_credit_count":90,"source_credit_drop_count":0,"structural_source_credit":1040552,"workflow_prompt_credit":6609},"plan":{"calls":178,"content_source_credit":1696804,"derived_artifact_credit":6564,"direct_net":1690458,"estimated_tokens_saved":1690458,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10911,"response_debit":417944,"source_credit_count":122,"source_credit_drop_count":0,"structural_source_credit":406358,"workflow_prompt_credit":9587},"review":{"calls":237,"content_source_credit":3107030,"derived_artifact_credit":5548,"direct_net":2506845,"estimated_tokens_saved":2506845,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":24671,"response_debit":584838,"source_credit_count":147,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3776}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":573,"content_source_credit":6497191,"derived_artifact_credit":14968,"direct_net":6711071,"estimated_tokens_saved":6711071,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":40623,"response_debit":1227347,"source_credit_count":359,"source_credit_drop_count":0,"structural_source_credit":1446910,"workflow_prompt_credit":19972},"wave_id":"231kh explainable-project-statistics"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 32 | 0 | 20 | 20,469,191 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":20,"estimated_exploration_avoided":20469191,"surfaced_events":32} -->
<!-- wave:exploration-avoided end -->
