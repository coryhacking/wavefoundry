# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-19
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `212ym graph-build-progress-logging`
Title: Graph Build Progress Logging

## Objective

Operators and agents polling a graph build see which extraction or finalize phase is running and how far through it the build is, instead of a log line minutes old. Lines appear in verbose mode only, and the build behaviour and tool contracts are unchanged.

## Changes

Change ID: `212yl-enh graph-build-progress-logging`
Change Status: `implemented`

## Participants

- Coordinator: Engineering
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer

Completed At: 2026-10-19

## Wave Summary

Wave `212ym` (Graph Build Progress Logging) delivered one change: Graph build progress lines in the index build log. Notable adjustments during implementation: Graph build progress lines in the index build log: Readiness red-team primer: no blocker. Repaired before any approval: named the finalize phases (AC-2 could not fail on an open set), first line before the merge-state load, added the `mp_ctx is None` serial path.; Graph build progress lines in the index build log: Readiness focused repair: code-reviewer and architecture-reviewer both found Requirement 3 contradictory, because the merge state is read before the zero-change fast path. Added a `merge state load` phase before those reads, renamed the old phase `merge state acquire`, and changed AC-2's zero-change clause. Implementation notes kept: interval read at call time; AC-2 hard-codes the expected list and pins the line format by regex; the fallback test asserts its stub raised; AC-1 stays on thread and serial paths (the existing `_SpyExecutor` has no `submit`).; Graph build progress lines in the index build log: Implemented. Delivery: code-reviewer and qa-reviewer approved (QA killed 19 of 21 mutants; code-reviewer's placement mutant M5 survived). Added three tests after those approvals to close the survivors: process-pool failure fallback, `merge state load` before finalize's `paths_with_hashes()` read, and the phase count suffixes; all three mutants now fail in a scratch copy. architecture-reviewer blocked on the CHANGELOG claim that setup graph passes are verbose (setup adds `--verbose` only when asked); bullet corrected. Red-team and security seats passed. Gapfill: shell reads and edits used because auto mode prefers Bash for file work.

**Changes delivered:**

- **Graph build progress lines in the index build log** (`212yl-enh graph-build-progress-logging`) — 5 ACs completed. Key decisions: Plain verbose lines: count-based progress in extraction loops plus phase-start lines in finalize.
## Watchpoints

- Watchpoint: waves 212yk (OPEN), 2136j, 2136r, 2136s and 2124l are uncommitted in the same tree. This wave shares only CHANGELOG.md with them; add one bullet and leave their hunks intact.
- Watchpoint: AC-4 needs a real graph rebuild of this repository, which takes several minutes and holds the index build lock.

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
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
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
| plan | 15 | 5,637 |
| implement | 21 | 0 |
| review | 25 | 1,893,003 |
| **Total** | **61** | **1,898,640** |

<!-- wave:context-efficiency-state {"generation":61,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":21,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-1348,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":789,"response_debit":4139,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3580},"plan":{"calls":15,"content_source_credit":26198,"derived_artifact_credit":1622,"direct_net":5637,"estimated_tokens_saved":5637,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2953,"response_debit":23658,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4428},"review":{"calls":25,"content_source_credit":1947348,"derived_artifact_credit":1600,"direct_net":1893003,"estimated_tokens_saved":1893003,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3256,"response_debit":55903,"source_credit_count":42,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3214}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":61,"content_source_credit":1973546,"derived_artifact_credit":3222,"direct_net":1897292,"estimated_tokens_saved":1898640,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6998,"response_debit":83700,"source_credit_count":56,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11222},"wave_id":"212ym graph-build-progress-logging"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
