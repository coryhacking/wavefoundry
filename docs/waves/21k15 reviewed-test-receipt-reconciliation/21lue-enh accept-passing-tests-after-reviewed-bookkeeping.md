# Accept passing tests after reviewed bookkeeping

Change ID: `21lue-enh accept-passing-tests-after-reviewed-bookkeeping`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-25
Wave: 21k15 reviewed-test-receipt-reconciliation

## Rationale

During 21j63, all 209 canonical test files completed successfully (12,131 tests, 12 existing skips, 635.267 seconds), but the repository-change guard refused qualification. The only reported paths were `.wavefoundry/guard-overrides.json` (the coordinator closed the edit gates) and `docs/prompts/review-wave.prompt.md` (the coordinator corrected a source-of-truth list from 1,3,4 to 1,2,3). An independent reviewer confirmed the exact editorial correction. The operator stopped an unnecessary repeat and requested an allowance for accepting results invalidated by recordkeeping. The repeat was cancelled before execution; no green receipt was manufactured.

Existing `run_tests._bookkeeping_changes` already accepts validated canonical wave/change records and append-only review publication. Other paths fail the repository guard. `run_tests._main` writes the last-green cache only on success; its default detailed report is also published only on success, although an explicitly requested qualification report can preserve a failed run. These are current-source observations; the incident itself executed the refusal. There is no claimed successful reconciliation path today.

## Product Intent

Operators can reuse a completed, passing canonical run when the only invalidation is verified non-behavioral bookkeeping, without rerunning its workers or weakening detection of real test failures and changed test inputs. Accepted results visibly identify the original run and the reviewed exception. AC-1 and AC-2 test that avoided rerun and truthful qualification boundary together. This is separate from 21j63's guidance correction.

## Requirements

1. Preserve enough structured evidence from a complete run whose workers all passed but whose repository guard refused publication to distinguish that case from worker failure, timeout, incomplete execution, stray test artifacts, or unverifiable snapshots. Reuse the existing ignored qualification-report storage and snapshot machinery; do not add per-wave evidence directories or a new review stage. Record the original framework input identity and the exact guard reasons/changed paths.
2. Continue accepting the canonical bookkeeping already recognized by the runner. Add a bounded reconciliation operation for the remaining case: inspect the preserved result, current input identity, and exact changed-path evidence without launching test workers. Return eligibility and reasons before writing anything. Missing or ambiguous evidence is ineligible, not assumed harmless.
3. Acceptance requires a complete passing worker set, unchanged qualified framework inputs, and a disposition for every guard-invalidating change. Closing an existing edit gate may qualify only when the change is true-to-false on known gates and all other configuration is preserved. Opening gates, code/test/config behavior changes, stray artifacts, failed or unfinished workers, and unexplained edits never qualify through this allowance.
4. Editorial changes outside the framework, such as the motivating Markdown list numbering correction, require explicit review of the exact before/after difference and operator acceptance bound to that run and difference. Do not infer semantic equivalence from a whole-docs exclusion or an agent's bare label of bookkeeping. Use existing review/checkpoint conventions rather than a new lifecycle approval type. The final CLI/API shape is a focused readiness design choice; it must remain one inspect/accept operation, not another full review ceremony.
5. Successful acceptance publishes a truthful receipt with the original execution identity and an explicit reconciliation annotation naming the allowed differences and acceptance basis. Preserve the failed original attempt report. Reject changed inputs between inspection and acceptance, and make an identical acceptance retry safe. Do not relabel the original process exit as success or synthesize a run from console text.
6. Preserve ordinary green receipts, cache reuse, test-failure behavior and close/package consumers. A runner implementation change itself changes framework inputs and cannot use this allowance to qualify its own unexecuted code. Older runs lacking the required evidence are not automatically recoverable. Document that limitation instead of promising this mechanism will retroactively qualify the 21j63 run.

## Readiness design

The existing runner owns a single CLI operation: `python3 .wavefoundry/framework/scripts/run_tests.py --reconcile REPORT` returns an inspection and exact differences; adding `--accept TOKEN --operator-reviewed TEXT` accepts that inspected result on the operator's explicit instruction. The text records the operator's attestation that the displayed documentation changes are editorial; an agent's label is not authorization or automated semantic proof. This branch runs before worker execution and bytecode warming. No new MCP tool, reviewer role or lifecycle gate is introduced.

Eligible editorial paths are pre-existing regular UTF-8 Markdown documentation under `docs/`, including rendered `docs/prompts/`, excluding canonical wave/change/ledger authority carriers. Newly added/deleted documents, symlinks, code/config changes and framework changes are ineligible. Known gate closures require only boolean true-to-false transitions with all remaining configuration unchanged. The gate rule classifies eligibility; it does not automatically accept a run. Unknown or ambiguous differences remain refused.

Capture full content-hash observations of guard-covered paths and bounded optional pre-run documentation bytes (256 KiB per document, 32 MiB aggregate in memory); persist only changed before/after bytes with original guard reasons and execution identity in a write-once per-run report under the existing ignored qualification cache. Keep the existing 8 MiB persisted report bound. Capture failure or an uncaptured changed document leaves recovery unavailable, never bypasses the guard or fails an otherwise ordinary green run. No snapshot of arbitrary credentials or ignored files is added.

Inspection binds its token to the original report/run, exact differences, dispositions and current repository observation. Acceptance holds the runner and existing publication locks, rechecks the framework hash, worker inventory, original report and current observations immediately before writing, and refuses a changed binding. This coordinates supported writers; it does not claim isolation against arbitrary native filesystem mutation by the same user. The original red report/exit remains intact; a separately annotated accepted detail and ordinary receipt keep the original run identity and execution time. Deterministic acceptance identity permits an identical retry and partial-publication recovery without workers; refuse to replace a newer unrelated receipt. Report success only after verifying publication. Existing qualification consumers must preserve the reconciliation annotation when reusing detail.

Source ownership stays in `run_tests.py` and `qualification_report.py`. Use existing guard/qualification/cache fixtures, adding a focused reconciliation test file only if that improves isolation. No normalizer, review authority or profile-selection change is intended. The implementation itself changes framework inputs and requires one ordinary complete qualification after sources settle.

## Scope

In scope: the canonical test runner's guard-only failed-run evidence and explicit reconciliation, existing qualification report/cache integration, focused regression fixtures, verification documentation and minimal supporting guidance.

Out of scope: rerunning the 21j63 suite for an unchanged tree; modifying its cached receipt by hand; waiving failed tests; arbitrary prompt or code equivalence; broad directory exemptions; new Council/signoff types; automatic acceptance of uncertain changes; release or wave closure.

## Acceptance Criteria

- [x] AC-1: A disposable complete passing run invalidated only by proven gate closure and an explicitly reviewed non-behavioral document change can be inspected and accepted against unchanged inputs. A worker-launch sentinel proves reconciliation starts zero tests; the published receipt identifies the original run and accepted exception, and the original failed-attempt report remains intact.
- [x] AC-2: The same path refuses a failed/incomplete worker set, changed framework inputs, an opened gate, unknown changed content, missing before/after evidence and stray test artifacts. Each refusal leaves the existing receipt unchanged. Include an otherwise-eligible adjacent control so failure cannot be explained by an earlier unrelated gate.
- [x] AC-3: An edit after inspection invalidates acceptance; an identical acceptance retry preserves the same execution/acceptance identity without rerunning workers or duplicating authority.
- [x] AC-4: Existing canonical bookkeeping tolerance and ordinary green-run/cache/close behavior retain their meanings. Verification guidance explains prospective recovery, preserved failures and why missing historical proof cannot be reconstructed from a log.

## Tasks

- [x] During readiness, settle the smallest inspect/accept interface and evidence carrier, using the existing report and snapshot owners; reproduce the incident shape in a disposable fixture.
- [x] Implement guard-only result preservation and bounded reconciliation without changing ordinary worker execution.
- [x] Add focused public-path positive/negative and retry controls; independently verify AC-1 through AC-4.
- [x] Update verification/architecture documentation and qualify the changed runner once after its source settles.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| runner-reconciliation | implementer | readiness | One writer for the runner and report seam |
| independent-verification | qa-reviewer | implementation | No worker rerun during reconciliation probes |

## Serialization Points

- `.wavefoundry/framework/scripts/run_tests.py`, `.wavefoundry/framework/scripts/qualification_report.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/contributing/build-and-verification.md`, `docs/architecture/testing-architecture.md`

Read-only review lanes: code, QA, architecture, security and docs-contract; the implementation writer owns only admitted paths. Re-derive the exact affected test files during readiness; no blanket test rewrite is implied.

## Affected Architecture Docs

`docs/architecture/testing-architecture.md`: distinguish executed test results, guard failure and reviewed acceptance while retaining the existing receipt authority.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Reuse the passing work without a worker rerun |
| AC-2 | required | Preserve genuine failure and input-integrity boundaries |
| AC-3 | required | Acceptance cannot race newer changes or duplicate authority |
| AC-4 | required | Existing qualification remains understandable and compatible |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-25 | Final canonical qualification passed once after source/gates settled: 12,220 tests across 212 files, 12 existing skips, 635.226 seconds, exit 0. All five reviewed hashes unchanged. All ACs/tasks complete and six specialist delivery approvals current. | run_tests.py canonical default run; current test-cache.json; maintained 25-test reconciliation suite; typed review ledger |
| 2026-10-25 | All six delivery lanes approve. Promoted newer-detail test passes independently; bypassing only its guard produces actual acceptance instead of refusal. Final focused suite now contains 25 tests. Production/docs hashes unchanged; canonical qualification pending on frozen source. | Typed delivery approvals; ReconciliationCLITests.test_newer_unrelated_detail_is_preserved and focused mutation |
| 2026-10-25 | Before test-only promotion: independent architecture confirmed newer retained detail is protected even without a newer receipt, and its isolated guard-removal mutant overwrites that detail. Preserve this unique adjacent control in the maintained reconciliation suite; all delivery readers have finished and production remains unchanged. | Proposed test_newer_unrelated_detail_is_preserved; architecture independent probe |
| 2026-10-25 | Implemented and frozen for delivery review. Reconciliation24, existing guard47, qualification42, cache98, lock6, profile census8 and vocabulary census5 pass. Nine behavioral guard mutants detected; token and publication-lock controls were corrected after initial diagnostics proved only wording/fixture behavior, then both current controls passed and both unsafe variants actually accepted when they should refuse. Canonical qualification and independent verification remain pending. | ReconciliationCLITests named controls; original runner/report suites; token, typed-gate, failed-worker, stale-observation, capture-bound, publication-verification, canonical-proof, publication-lock and newer-receipt variants |
| 2026-10-25 | Implementation integration check identified the ordinary green-publication lock gap: worker execution released the runner lock before receipt/detail writes. The same existing runner lock now covers ordinary publication with a current-input recheck, so reconciliation can serialize with that writer. No new lock or authority. Explicit py_compile wrote two source-adjacent bytecode files despite -B; the implementer reported and relocated only those generated files to owned work and switched syntax checks to ast.parse. | run_tests._publish_default_success; maintained publication-interleaving regression pending final verification; owned work baselines |
| 2026-10-25 | Readback: before, one passing worker plus gate closure/editorial numbering correction ends red with no reusable receipt. After, preserved exact evidence can be inspected and explicitly accepted with zero worker launches, while changed framework inputs/failed workers/unknown differences remain refused. AC-1–4; runner/report/test implementation only, coordinator owns two verification docs. Ready on current receipt; no closure/commit authorized. | Independent readiness controls and typed approvals; one runner/report writer |
| 2026-10-25 | Readiness design grounded in runner execution, observation, receipt and report owners. Disposable real worker passed one test but gate closure plus rendered Markdown numbering edit produced exit 1 naming both paths and no receipt/detail. Settled inspect/accept interface and bounded evidence before review. | RepoGuardTestBase._external_main disposable fixture; run_tests._execute_files/_main; qualification_report output/read/write/validate |
| 2026-10-25 | Planned separately from 21j63 after the operator requested bookkeeping acceptance and prohibited an unnecessary full-suite repeat. No runner code, receipt or qualification policy was changed. | `/private/tmp/21j63-ir1-vgdgjrnv/framework-suite.log`; `run_tests._bookkeeping_changes`, `_main` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-25 | Select bounded post-run inspection and explicit acceptance using existing evidence/report storage | Replays the motivating case when sufficient run/difference proof exists; directly permits reuse rather than merely advising it. Measure success by an eligible refusal resolved with zero worker launches, retaining rejected adjacent controls. | Ignore all docs/gates: hides behavior changes. Rerun every guard failure: discards valid work. Automatic prose-equivalence classification: broader machinery and unreliable semantics. |
| 2026-10-25 | Preserve the original failed result and annotate acceptance separately | An approved exception is not the same fact as an unmodified successful process; missing snapshots or changed framework inputs remain ineligible. | Overwrite the old receipt or infer success from stdout: loses provenance and can accept incomplete work. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Bookkeeping becomes a label for substantive changes | Exact run/difference binding, narrow gate closure, explicit editorial review, fail closed on uncertainty |
| Recovery becomes more expensive than a rerun | One inspect/accept operation using existing report data; no new review stage or per-wave artifact collection |
| Historical run lacks sufficient evidence | Report ineligible; do not promise retrospective acceptance or manufacture original identities |

## Session Handoff

Admitted to 21k15 for preparation, independent review and implementation. No implementation before readiness. Historical 21j63 is not recoverable without prospective evidence; no unchanged rerun is authorized.
