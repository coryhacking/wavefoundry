# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-15
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20ppj rerun-reliability-review-follow-ups`
Title: Rerun Reliability Review Follow Ups

## Objective

Repair the regressions and leftovers that the code review of commit `43621e07` (wave `20oqx`, upgrade rerun reliability and distribution inference integration) found before that build ships to any consumer. When this wave closes, retired-graph cleanup completes on every host and for pre-existing receipts, an old parent's recovered index publication is no longer recorded as failure, the memory reranker fallback cannot raise `UnboundLocalError`, extension declaration problems are reported where every other declaration problem is, and redundant walks are removed while reachable recovery and compatibility paths are protected.

## Changes

Change ID: `20og5-bug storage-graph-cleanup-retained-never-completes`
Change Status: `implemented`

Change ID: `20p5j-bug memory-reranker-except-unbound-import`
Change Status: `implemented`

Change ID: `20p5k-bug post-index-update-old-parent-false-failure`
Change Status: `implemented`

Change ID: `20p5l-bug extension-declaration-validation-placement`
Change Status: `implemented`

Change ID: `20pph-debt open-scope-repeated-wave-walk`
Change Status: `implemented`

Change ID: `20ppi-debt dead-paths-after-rerun-reliability`
Change Status: `implemented`

## Participants

- Coordinator: Coordinator
- Write-owning roles: Implementer after readiness; coordinator owns lifecycle records
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer, release-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, performance-reviewer, security-reviewer

Completed At: 2026-10-15

## Wave Summary

Wave `20ppj` (Rerun Reliability Review Follow Ups) delivered 6 changes: Retired graph cleanup: retain and complete instead of refusing forever, Memory reranker selection: except clause references an unbound import, post_index_update reports an old parent's recovered publication as failure, Extension declaration validation: report at declaration time, validate once, Single-OPEN guard re-walks the waves tree once per open wave, and Preserve recovery and compatibility paths after rerun reliability. Notable adjustments during implementation: Retired graph cleanup: retain and complete instead of refusing forever: Scope held to the reviewed receipt: the post-readiness addendum (zero-`st_ino` volumes as a fifth retained population; a `phase_cleanup` handler for refusals that escape `cleanup_legacy`) was withdrawn rather than re-readied. Zero-identity volumes already complete under requirement 2 because capture records no ownership and the plan reports retained; add that case as one regression under AC-1/AC-2 at implementation, no new code. The `phase_cleanup` handler addresses pre-existing tamper refusals (artifact identity, staging), not a regression of `43621e07`; plan it separately if a field report shows the traceback.; Memory reranker selection: except clause references an unbound import: Focused controls passed: root follow-ups, rerun, retained docs-gate retry, scope and container-status controls: 44 tests / 0 skips. In-memory mutants restored the unbound import, repeated discovery and missing extraction guard; each targeted test detected its defect. Final combined qualification remains pending.; Single-OPEN guard re-walks the waves tree once per open wave: Readback: pass one discovered wave-directory list into optional scope lookup; preserve canonical parent/repository guard answers. AC-1/2; server_impl, record_paths and discovery-count regression. Before: N extra discoveries; after: one per uncached/cached guard call.

**Changes delivered:**

- **Retired graph cleanup: retain and complete instead of refusing forever** (`20og5-bug storage-graph-cleanup-retained-never-completes`) — 5 ACs completed. Key decisions: Retain and complete: retained graph plans record a reason and let cleanup finish; Old receipts stay retained rather than lazily capturing ownership
- **Memory reranker selection: except clause references an unbound import** (`20p5j-bug memory-reranker-except-unbound-import`) — 3 ACs completed. Key decisions: Bind the module before the `try`
- **post_index_update reports an old parent's recovered publication as failure** (`20p5k-bug post-index-update-old-parent-false-failure`) — 4 ACs completed. Key decisions: Resolve an unobserved outcome through the current checkpoint-bound memory run and existing authorized publication reconciler
- **Extension declaration validation: report at declaration time, validate once** (`20p5l-bug extension-declaration-validation-placement`) — 5 ACs completed. Key decisions: One change for both items; Cache the verdict keyed by `tc._generation`
- **Single-OPEN guard re-walks the waves tree once per open wave** (`20pph-debt open-scope-repeated-wave-walk`) — 3 ACs completed. Key decisions: Pass the discovered list into the scope resolver
- **Preserve recovery and compatibility paths after rerun reliability** (`20ppi-debt dead-paths-after-rerun-reliability`) — 4 ACs completed. Key decisions: One debt change for both leftovers; Readiness correction: retain the reachable extraction guard and explicit ignored keyword
## Watchpoints

- Watchpoint: Graph ownership remains explicit: unowned or unsupported folders are retained with a terminal outcome. Actual historical-parent recovery and negative proof controls passed. Reachable extraction/signoff compatibility is retained. All required delivery reviewers approved; gates remain closed.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| PPJ-R1 | do_now | no | completed | architecture-reviewer, security-reviewer, qa-reviewer, code-reviewer, docs-contract-reviewer, release-reviewer, council-readiness |
| PPJ-R2 | do_now | no | completed | architecture-reviewer, code-reviewer, docs-contract-reviewer, release-reviewer, council-readiness |
| QA-PPJ-RESIDUE | do_now | no | completed | qa-reviewer, code-reviewer, docs-contract-reviewer |

*Machine review state — 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
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
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| performance-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 164 | 2,253,512 |
| implement | 65 | 1,676,163 |
| review | 88 | 961,506 |
| **Total** | **317** | **4,891,181** |

<!-- wave:context-efficiency-state {"generation":245,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":65,"content_source_credit":1740407,"derived_artifact_credit":0,"direct_net":1676163,"estimated_tokens_saved":1676163,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2251,"response_debit":65441,"source_credit_count":35,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3448},"plan":{"calls":164,"content_source_credit":2672564,"derived_artifact_credit":16045,"direct_net":2253512,"estimated_tokens_saved":2253512,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":33880,"response_debit":405485,"source_credit_count":112,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4268},"review":{"calls":88,"content_source_credit":1110801,"derived_artifact_credit":0,"direct_net":961506,"estimated_tokens_saved":961506,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2689,"response_debit":152242,"source_credit_count":29,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5636}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":317,"content_source_credit":5523772,"derived_artifact_credit":16045,"direct_net":4891181,"estimated_tokens_saved":4891181,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":38820,"response_debit":623168,"source_credit_count":176,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":13352},"wave_id":"20ppj rerun-reliability-review-follow-ups"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 28 | 0 | 21 | 9,553,943 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":21,"estimated_exploration_avoided":9553943,"surfaced_events":28} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

2026-10-15 final delivery: Six rerun follow-ups are implemented: terminal retained graph cleanup, safe reranker fallback, actual historical-parent publication proof, shared declaration validation, one scope discovery and preserved compatibility/recovery paths. Original full isolated red-team primer preceded separate architecture, security, QA and reality seats plus rotating docs. Chair grouped code/release/performance in one disclosed independent context. Six test/doc integration findings were collected, repaired in one bounded pass and independently reverified by fresh QA/code/docs contexts (39, 9 and 7 selected passing tests respectively, each with known-bad controls and zero skips). Original architecture/security source judgments were retained against unchanged production hashes; no second full council is claimed. Council agreed on scoped delivery with no remaining material finding or disagreement. The alternative of extra cleanup hashing/session markers was rejected in favor of existing proof and fresh identity controls. Final 47-path binding: 3090aafeb2c958ac40e3f6997800ba241f9f5f50c32cdbcc847307618ed9524f. These are implementation and review results, not release or native-platform qualification.

2026-10-15: operator requested preparation and review only. Six admitted plans are under independent readiness council review, with isolated adversarial primer before fixed seats and rotating docs coverage. Code, release and performance remits cover exception flow, old-parent compatibility and deterministic call-count controls. Inherited capable reviewers are used for cross-module reasoning; actual runtime model identity is not exposed. Source is frozen; only plan repairs and typed readiness records are authorized. No implementation, full suite, close, commit or push is requested.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Full readiness council found two plan blockers. One bounded repair specifies existing run-bound publication authority in 20p5k and corrects the dead-path premise in 20ppi. No source edits. | PPJ-R1/R2 typed ledger; amended Requirements and ACs |
| 2026-10-15 | Implementation and independent repair review complete; leave paused for operator closure. Full shared qualification ran 11,816 tests / 200 files / 12 skips in 736.347 seconds. It was red from the repaired test-integration failures and the unrelated deferred checklist scaling ratio (8.47 versus limit 8); no timing waiver, benchmark pass or fresh green full-suite receipt is claimed. After the bounded test/doc repairs, the stable protected focused run passed 420 tests / 11 modules / zero skips, including the repository-state guard, and the exact identity census separately passed with its three existing mutation controls. Unchanged production coverage comes from the full run plus earlier focused and independent guard controls; the entire full suite was not repeated merely for a timing pass. | Typed terminal findings: QA-PPJ-RESIDUE; shipped test modules and native-support probe notes. No new evidence folder, close, commit, push or package. |
| 2026-10-15 | Closure retrospective and cleanup: reviewed concrete memory proposals without creating candidates. Drafts duplicate canonical contracts/tests or infer source fragility from readiness findings; no distinct durable action was justified. Keep rationale here and current support guidance. Folder contains only wave.md, admitted change docs and immutable events.jsonl; no redundant evidence folder or scratch artifact needs deletion. Operator authorized close, commit and push; a fresh repaired-tree full suite is required for the stale receipt. Timing investigation stays deferred, without a new waiver. | memory_propose dry-runs; existing regression controls; current close dry-runs. |
| 2026-10-15 | Operator authorized close, commit and push. Final repaired-tree canonical run completed 11,816 tests / 200 files / 12 skips in 841.468 seconds; every check except test_indexer.SQLiteDriftDetectionScaleTests.test_100k_rows_contention_safe_budget passed (1.063578 seconds versus 1.000 seconds). Timing investigation remains deferred; no threshold change, waiver, unchanged retry or green receipt was produced. Closure stays paused because the existing close tool requires a current green receipt and has no exception path. Commit/push the reviewed implementation with this explicit limitation. | python .wavefoundry/framework/scripts/run_tests.py; exact result in this record; temporary full log /private/tmp/three-wave-close-qualified-default.log. |


## Readiness outcome

2026-10-15: all seven required lanes and council approve the current repaired packet. Full-depth isolated red-team primer ran adversarial, constructive, simplicity, first-principles and analogical stances before architecture, security, QA and reality seats. The rotating reviewer covered code, docs, release and performance in one disclosed shared context. The reality seat contributed plan claim discipline only, not an executed runtime approval. Council initially agreed to revise two medium plan defects; one bounded repair and one focused verification cleared both, with red-team closing confirmation and no remaining blocker.

PPJ-R1 now binds recovered publication to the current validated checkpoint's memory run and existing authorized publication/reconciliation proof, rejecting missing, stale or mismatched evidence. PPJ-R2 corrects the false dead-path premise: keep the reachable extraction guard and explicit ignored compatibility keyword. Earlier deletion language in the Risks narrative is historical; amended Requirements, ACs and tasks govern preservation. Strongest alternative was letting implementation discover these choices; rejected because the plan would otherwise leave publication authority unspecified and direct unsafe removal.

Executed readiness evidence: eight existing incoming-outcome/graph-ownership tests; six actual-source manifest/preflight reachability controls; explicit keyword state matrices; generation and unknown-publication mutants detected; provider validation call counts (five and seven calls) plus invalid-mode controls. Focused chair replayed two outcome tests, nine keyword cells and unknown-keyword rejection; other seats disclosed which unchanged original controls they reused. This is plan readiness, not completion of unimplemented repairs, an end-to-end historical upgrade, native Windows/service qualification or a performance benchmark. Timing investigation remains deferred.

Required delivery evidence remains the admitted actual historical-parent recovery fixture, current-run negative proof matrix, retain-and-complete cleanup controls, reranker failure-path tests and deterministic validation/discovery counts. No full suite is needed for these documentation-only readiness changes. No implementation, closure, commit or push was performed.

## Implementation allocation

2026-10-15: operator authorized implementing all three readied waves and pausing each for continuation. Coordinator owns lifecycle, small server/scope/compatibility changes and integration. Independent implementers own storage cleanup and old-parent publication/declaration validation respectively, with disjoint files. Use inherited capable model for source/guard reasoning; actual runtime identity is not exposed. One combined canonical suite after source settles; no repeated suite for bookkeeping. Closure, commits and release are not requested.

## Implementation checkpoint

2026-10-15: admitted implementation and focused regressions are complete. Storage: 133 tests / 1 skip, 12 graph controls; root server/scope/recovery compatibility: 44 tests; declaration/provider and historical-parent controls passed. Named guard mutants reproduced unsafe alternatives. Pause frees the OPEN slot for 20qrv; final shared canonical qualification and independent delivery review remain pending after all source edits settle. No closure or commit authorized.
