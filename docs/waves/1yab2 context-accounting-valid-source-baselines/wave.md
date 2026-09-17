# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-17
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1yab2 context-accounting-valid-source-baselines`
Title: Context Accounting Valid Source Baselines

## Objective

Prevent binary databases and runtime artifacts from inflating context estimates, and label the whole-file proxy honestly. Preserve legitimate text accounting and historical readability; no history correction machinery.

## Changes

Change ID: `1y8hb-bug context-accounting-valid-source-baselines`
Change Status: `complete`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer (accounting), technical-writer (disjoint documentation)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-09-17

## Wave Summary

Wave `1yab2` (Context Accounting Valid Source Baselines) delivered one change: Exclude Invalid Sources From Context Estimates. Notable adjustments during implementation: Exclude Invalid Sources From Context Estimates: Operator narrowed scope: remove history correction requirements, AC-4, task and correction machinery; retain the completed one-off audit only; Exclude Invalid Sources From Context Estimates: Independent code/QA review repaired incomplete UTF-8 at exact 4096-byte EOF using existing stat size. Docs review removed stale captured-only fallback wording. Final focused review: 10 tests, zero skips; known-bad real producer bypass produces two expected failures (2048 versus zero).; Exclude Invalid Sources From Context Estimates: Final validation: 59 accounting, 96 public accounting and 125 renderer tests pass in the full runner. Full docs lint passed with no errors or warnings; diff whitespace check clean. All scoped ACs met..

**Changes delivered:**

- **Exclude Invalid Sources From Context Estimates** (`1y8hb-bug context-accounting-valid-source-baselines`) — 4 ACs completed. Key decisions: Select source eligibility plus honest labels; Preserve legacy field readability; no historical correction feature
## Watchpoints

- Watchpoint: do not modify closed waves. Keep exact legacy-render validation while retaining numeric tamper detection. Framework and seed gates required. Operator explicitly requested the simple forward fix.

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
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 31 | 601,545 |
| implement | 87 | 1,108,357 |
| review | 28 | 68,183 |
| **Total** | **146** | **1,778,085** |

<!-- wave:context-efficiency-state {"generation":128,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":87,"content_source_credit":1227043,"derived_artifact_credit":1199,"direct_net":1108357,"estimated_tokens_saved":1108357,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6103,"response_debit":116635,"source_credit_count":80,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2853},"plan":{"calls":31,"content_source_credit":626710,"derived_artifact_credit":1378,"direct_net":601545,"estimated_tokens_saved":601545,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2269,"response_debit":32463,"source_credit_count":13,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8189},"review":{"calls":28,"content_source_credit":102384,"derived_artifact_credit":2491,"direct_net":68183,"estimated_tokens_saved":68183,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6519,"response_debit":32175,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2002}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":146,"content_source_credit":1956137,"derived_artifact_credit":5068,"direct_net":1778085,"estimated_tokens_saved":1778085,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14891,"response_debit":181273,"source_credit_count":117,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":13044},"wave_id":"1yab2 context-accounting-valid-source-baselines"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

- Allocation: coordinator owns the small accounting/rendering change; independent red-team and policy-selected council seat review readiness. Source and documentation checks use MCP-first retrieval; targeted shell census is Gapfill when hidden-framework MCP keyword results omit known files. Operator acknowledged prepare/review/implementation with no history correction.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: prefix inspection cannot prove arbitrary whole-file type; strongest-alternative: shared conservative check with no classifier subsystem; agreement: bounded recognition and exact legacy rendering preserve simplicity). Red-team executed registered code_read: 8192-byte SQLite earned2048 invalid source tokens; text3041 bytes earned761 and repeat0 with19/259 request/response debits. Docs seat parsed archived1y9sv and rejected an in-memory call-count tamper93 to94, preserving original bytes. No repaired implementation claimed by readiness evidence.

- **Refreshed readiness council — 2026-09-17: PASS.** Receipt `review-policy-0f790dfff14afbf96877`; standard red-team primer followed by docs-contract seat answers. Bounded prefix recognition and the counterfactual limitation remain explicit; exact old rendering does not relax numeric validation. Unanimous, no findings or deferrals. Removing all accounting would lose the qualified signal; caps would conceal invalid credits.
- **Delivery code and QA — 2026-09-17: PASS.** Independent context `accounting_close_code`: 36 targeted tests, zero failures/errors/skips; all 13 focused mutants caught. Real registered SQLite and renamed SQLite produce zero credit, valid text credits once, debits persist. EOF and exact legacy tamper checks pass. Frozen source/test hashes unchanged. AC-1/2/3/5 verified; no AC deferrals.
- **Architecture and docs-contract — 2026-09-17: PASS.** Independent context `accounting_close_docs_arch`: seven tests and real first-party SQLite probe; zero source credit with 7/11 debits, bypass produces 2048. Qualification, numeric validation and prefix-cap mutations detected. Source/seed/carrier/reference/spec hashes unchanged. No schema/key migration, historical rewrite or native-platform qualification claimed.

| Mutation boundary | Observed detection |
| --- | --- |
| Runtime, suffix, Lance and SQLite-sidecar exclusions | Each removed branch fails invalid-source fixtures |
| UTF-8/NUL and EOF handling | Invalid source or split-boundary control fails |
| Prefix bound | Increasing the read cap fails the bounded-read assertion |
| Error handling | Awarding credit on classification errors fails uncertainty control |
| Registered producer eligibility | SQLite and renamed SQLite each fail at 2048 versus zero |
| Qualification and legacy validation | Missing disclaimer or accepted numeric tampering fails contract controls |

## Retrospective and memory

The non-obvious lesson is that source version/size evidence does not establish text eligibility or an avoided read. The shared bounded classifier and honest baseline are documented in `docs/references/context-efficiency.md`; no duplicate memory is needed. `memory_propose(mode='create')` returned zero candidates and zero pending validations. Keep the actual server-loaded module as the mutation target when testing registered tools, since import-time module replacement can leave a stale test-module reference.

Scope remains the simple forward fix. No history correction, deferrals, or additional features were introduced. Native Windows/Linux execution remains outside this wave's evidence.
