# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-11
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20e12 memory-backfill-exhaustion`
Title: Memory Backfill Exhaustion

## Objective

Finish a historical memory backfill wave when all its draftable sources are already handled. Correct the empty create response so upgrades advance rather than re-claiming the same wave; preserve pending-candidate validation and publication gates.

## Changes

Change ID: `20e63-bug backfill-empty-create-omits-exhausted`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (coordinator executes the tightly coupled payload fix and regression tests)
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer

Completed At: 2026-10-11

## Wave Summary

Wave `20e12` (Memory Backfill Exhaustion) delivered one change: Memory Backfill Never Completes A Wave Whose Sources All Already Exist. Notable adjustments during implementation: Memory Backfill Never Completes A Wave Whose Sources All Already Exist: Added four real-handler regression tests before changing production code. Pre-fix run: 4 tests, one assertion failure (`10 != 1`), two subtest errors (missing `records_remaining`), zero skips; exact-fit and overflow controls passed. Adding only the two fields makes all four pass. The all-covered test also preserves the seeded candidate and its validation gate.; Memory Backfill Never Completes A Wave Whose Sources All Already Exist: Added one Unreleased changelog bullet. The installing upgrade imports `server_impl` in Phase 3 after extraction, then calls the same producer through `_memory_backfill_batch_locked`; no runner edit, additional upgrade scan or qualification step was introduced.

**Changes delivered:**

- **Memory Backfill Never Completes A Wave Whose Sources All Already Exist** (`20e63-bug backfill-empty-create-omits-exhausted`) — 6 ACs completed. Key decisions: Set the flag at the empty create return
## Watchpoints

- Watchpoint: only the create-mode empty-unique response gains completion metadata; remaining candidates and failed writes must not be declared exhausted.
- Scratch fixtures only; no consumer framework patch or live upgrade/index mutation. The earlier pvyg pack remains unfixed until a later build.
- No closure, commit, push or packaging authorized by this implementation request.
- Routine probes/reviewer working files remain temporary; durable evidence belongs in this wave and its change document.

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
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review checkpoints

- Work allocation: keep the one-return production fix and related tests with the coordinator; use fresh independent contexts for required review and Council. Available inherited model/effort is retained for this narrow Python change and judged review. Actual per-worker model identity is unknown; no model override requested.
- Readiness plan: standard isolated red-team primer, fixed architecture/security/QA/reality seats and rotating framework-operator seat; council-chair synthesis, plus code-reviewer.
- Readiness complete: all seven independent reviewers approved with no findings. The strongest challenge was false completion bypassing unfinished work; real pre-fix reproduction, page-size invariant and exact-fit/overflow controls answered it. The strongest alternative was equivalent sibling arithmetic; constants were retained for the empty branch.
- Implementation: one return gains two fields; four focused tests failed on the original bug and now pass. The existing candidate remains pending validation. The closed sibling-return census and exact durable test identities are consolidated in the change Progress Log; routine captures stay temporary.
- Delivery Council PASS: isolated standard red-team primer/closing reconciliation; fresh architecture, security, QA and reality-checker fixed seats; framework-operator rotating fifth; independent council-chair synthesis and separate code lane. All approved, no material findings or disagreements. Anonymized merit review corroborated truthful producer completion, preserved candidate validation and unchanged upgrade work. The strongest alternative was a separate repeated-claim guard, which cannot replace correct metadata and remains outside this change.
- Code and QA each independently ran the four baseline tests and both isolated actual-producer mutants. Architecture independently ran the baseline and removal mutant. Chair and QA additionally passed committed-before-checkpoint retry recovery. No registered transport, live consumer upgrade or native Windows result is claimed.
- Canonical qualification: 12,340 tests across 185 files, 12 skips; 285 focused memory tests with zero skips; current genuine framework receipt `5ed1b9307eb4afdd8d269742ef9721b91caf8523c5a76a7712a00a186071a17b`. Source remains frozen; no extra upgrade scans, consumer qualification files or persistent evidence folder were added.
- Editorial follow-up: AC-2 now accurately separates completion fields from its pending-candidate control. A fresh focused red-team primer, code/QA/architecture/docs-contract reviewers and council-chair approved the updated readiness receipt; Prepare passed. This was a focused clarification, not another full Council or source repair. Earlier full delivery approvals remain current.

| Mutant / control | Named canonical test | Observed |
| --- | --- | --- |
| Remove empty completion metadata | `test_all_handled_wave_completes_once_without_bypassing_validation`; `test_empty_create_reports_exhaustion_for_already_handled_sources` | `10 != 1` and two missing-field subtest errors |
| Force normal-create exhaustion true | `test_nonempty_overflow_page_remains_unexhausted` | Fails `True is not False` |
| Unchanged repair | All four new `HistoricalMemoryBackfillTests` methods | Four pass, zero skips |
| Retry after committed candidate / interrupted checkpoint | `test_candidate_committed_before_checkpoint_is_recovered_on_retry` | Pass; candidate remains pending validation |

Durable test source: `.wavefoundry/framework/scripts/tests/test_memory_backfill.py`. Working captures and mutation scripts remain temporary; their relevant observations are consolidated here and in the authoritative ledger.

## Completion criteria

- Every admitted AC/task reconciled with executable evidence; code, QA and architecture delivery approvals current, plus delivery Council if selected by the receipt. Current canonical suite receipt and final full docs validation.

## Handoff or next-wave notes

- Closure authorized on 2026-10-11; next work is the separate Rust cross-module binding repair. No commit, push or new package is authorized in this request.
- Closure retrospective: empty extraction is not validation or publication. The real seeded-candidate control and two-sided paging tests preserve that distinction; the bounded return census found no additional producer repair. These lessons are already captured in the implementation, regression tests and this record, so no new memory record is warranted. `memory_propose` dry-run returned no eligible candidates; none was created or left pending.
- Docs-contract review: no spec changed; fresh docs-contract review of the AC-2 wording clarification approved. All AC/tasks are met, with no intentional deferrals.
- Cleanup: only the wave/change records and authoritative ledger were generated in this wave folder. Routine captures remain temporary; cited unique pre-fix and mutation proof is retained. No supporting evidence folder or disposable repository output remains.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 95 | 121,375 |
| implement | 41 | 240,736 |
| review | 104 | 304,510 |
| **Total** | **240** | **666,621** |

<!-- wave:context-efficiency-state {"generation":157,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":41,"content_source_credit":276269,"derived_artifact_credit":0,"direct_net":240736,"estimated_tokens_saved":240736,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1474,"response_debit":37288,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3229},"plan":{"calls":95,"content_source_credit":307733,"derived_artifact_credit":794,"direct_net":121375,"estimated_tokens_saved":121375,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6737,"response_debit":186918,"source_credit_count":33,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6503},"review":{"calls":104,"content_source_credit":514499,"derived_artifact_credit":2603,"direct_net":304510,"estimated_tokens_saved":304510,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12034,"response_debit":203414,"source_credit_count":39,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2856}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":240,"content_source_credit":1098501,"derived_artifact_credit":3397,"direct_net":666621,"estimated_tokens_saved":666621,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":20245,"response_debit":427620,"source_credit_count":82,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12588},"wave_id":"20e12 memory-backfill-exhaustion"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 4 | 0 | 3 | 3,372,671 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":3,"estimated_exploration_avoided":3372671,"surfaced_events":4} -->
<!-- wave:exploration-avoided end -->
