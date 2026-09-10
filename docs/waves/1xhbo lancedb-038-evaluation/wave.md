# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-09
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1xhbo lancedb-038-evaluation`
Title: LanceDB vs SQLite Vector Evaluation

## Objective

Choose the simplest reliable local vector backend by comparing current LanceDB, latest stable LanceDB, and SQLite with sqlite-vec. Preserve current capabilities and establish whether dependency savings justify migration; deliver the evidenced focused implementation, a scoped follow-up, or a no-change decision.

## Changes

Change ID: `1xhdh-maint evaluate-lancedb-038-upgrade`
Change Status: `complete`

Change ID: `1xj6n-bug cpu-reranker-batch-stability`
Change Status: `complete`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (evaluation harness), data-engineer (conditional SQL integration)
- Requested review lanes: code-reviewer, architecture-reviewer, qa-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, release-reviewer, performance-reviewer

Completed At: 2026-09-08

## Wave Summary

Wave `1xhbo` (LanceDB vs SQLite Vector Evaluation) delivered two changes: Evaluate LanceDB Upgrade vs SQLite Vector Storage and Stabilize CPU Reranker Scores Without Hiding Relevance Loss. Notable adjustments during implementation: Evaluate LanceDB Upgrade vs SQLite Vector Storage: Expanded on operator request to latest LanceDB vs SQLite vectors.

**Changes delivered:**

- **Evaluate LanceDB Upgrade vs SQLite Vector Storage** (`1xhdh-maint evaluate-lancedb-038-upgrade`) — 3 ACs completed. Key decisions: Operator requested a thorough latest-capabilities and long-term comparison; Operator revised vector retrieval acceptance to below 100 ms; assess latency with reranking included
- **Stabilize CPU Reranker Scores Without Hiding Relevance Loss** (`1xj6n-bug cpu-reranker-batch-stability`) — 4 ACs completed. Key decisions: Strength; Same model/precision, peer-independent in initial probe, similar sampled CPU cost
## Current Evaluation Result

The bounded shared-SQLite transaction study passed and favors the unified layout: steady DB storage
248.04 → 164.31 MiB, combined retrieval p95 38.53 → 33.56 ms, 1,000 prepared chunk update/publication
p95 260.11 → 159.65 ms. Same tested results; full-row rollback and crash-window proof, keyed integrity,
file-hash guards, ten delete/reinsert cycles/four readers and backup/reopen passed. Changed epochs
were rejected (4 accepted / 40 discarded attempts per lane), so continuous availability is not proven.
Independent transaction review passed with explicit prepared-fixture limits. Evidence and reviewer
findings are in 1xhdh and existing vector-screen-results.json. AC-6 is complete for this bounded study;
live adapter/migration, platform delivery and broader filters/scale continue in conversion wave 1xjmm; final evaluation-wave review passed.
No production vector backend/dependency change or packaging. Operator authorized closure; no commit requested.

## Earlier Evaluation Revisions

Carried-forward tuning and bounded int8 screen completed; see change doc and `vector-screen-results.json`. Leading configuration is float32 scalar + mmap256 + selective metadata indexes. Int8 reduced experimental DB storage 41.9% and median query times about 10–12%, with roughly 94% self-query top100 neighbor overlap; labeled relevance is still unproven. No Stage2 or production migration. Bounded council readiness refreshed, but expanded-scope specialist readiness remains pending; activation withheld.

Quantization amendment (2026-09-08): operator confirmed SQLite. Added a separate Stage 1B native int8-first comparison, candidate-pool and final relevance checks, true implementation/kernel identity and fully costed optional rescoring. Int16 is unsupported in tested sqlite-vec 0.1.9; apparent float16 declaration uses float32 storage. AC-8/new benchmark tasks pending; only in-memory capability probes ran. Stage 2 remains the conditional data-layout study, not quantization. Re-Prepare required; no backend/default changes.

Operator addendum (2026-09-08): the existing change now includes a bounded 50K–1M scale ladder (2M+ optional), measured crossover bounds, configuration controls, exact implementation/runtime identities and verified patched SQLite WAL qualification. Transactional consolidation remains Stage 2 only. AC-2/4/5 and final review are reopened; AC-7 and new tasks are pending. Prior reviewed results below remain evidence for their original scope; expanded scope requires re-Prepare before code edits. No new benchmarks or production changes ran.

2026-09-08 full-query evaluation completed under the operator's 100 ms vector ceiling. Four
lanes each executed 165 measured calls on the same generation1028 snapshot. Latest Lance ANN
preserved every fixture metric. Exact Lance and SQLite scalar share one repeated loss of a
secondary relevant source; the primary answer remains first. The trace locates the difference
after successful vector retrieval, with CPU reranker batch-composition sensitivity independently
reproduced. SQLite latency/resources/lifecycle and public filter contracts pass, but strict Stage1
relevance does not. Stage2 was not started; AC-3 carries the explicit integrated-publication scope note.

Current outcome: retain installed LanceDB0.33.0; investigate backend-independent CPU reranker
stability, rerun the unchanged relevance gate, then resume conditional layout evaluation. Latest
Lance0.38 ANN still needs destination/platform qualification. Production dependency/storage behavior
is unchanged. Existing change doc and development-only public JSON receipt hold current evidence.
The prior delivery review passed for its original scope; the operator addendum now requires renewed preparation and review. No close, commit or release is authorized.

## Watchpoints

- No live index mutation during evaluation; remain local-only.
- Block SQLite combined-data evaluation until the isolated vector store passes; then require measured layout comparisons and end-to-end parity before adoption.
- Block adoption on any required capability gap; freeze versions and numeric acceptance budgets before candidate results. Roadmap promises do not satisfy parity.
- Preserve standard wf_upgrade; re-prepare materially larger migration scope.
- Existing IDs remain stable despite the expanded comparison; this wave is not assigned to 1.22.0.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-001 | do_now | no | completed | architecture-reviewer, wave-council-delivery |
| VP-NaN | do_now | no | completed | code-reviewer, qa-reviewer, wave-council-delivery |
| VP-Phase | do_now | no | completed | code-reviewer, qa-reviewer, wave-council-delivery |

*Machine review state — 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
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
| release-reviewer | approved | current executed approval follows every affected repair | none |
| performance-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review checkpoints

Final readiness/delivery council (2026-09-08): PASS. Standard primer ran first; actual seats
red-team and docs-contract-reviewer, rotating seat docs-contract-reviewer, moderator wave-council.
Five specialist lanes cleared; substantive agreement unanimous, maximum remaining severity none.
Initial code/QA context is separate from fresh QA/architecture/performance/release reassessment;
red-team seat and final docs/moderation sessions are separately fresh. Shared perspectives are not
counted as extra independent votes. Initial QA and council REVISE reports remain historical evidence.

`tree_moved_under_review` briefing discrepancy reconciled: Prepare gardening changed only the
performance document's Last verified date after the earlier manifest was prepared. Fresh reviewer
reconstructed exact old/current Git blobs, rejected stale snapshot, and verified25/25 before/after
at fingerprint f5e3bb75ebde3bc2a6790e9715fe43b99ace83a798a5bd4444f35e5d31d58454.
Current performance contract is CPU1/GPU40; no implementation change occurred in this correction.
Eight final known-bad contract/snapshot controls rejected; measurement JSON equality preserved.
After that review, only report retention, completion/status checkboxes and closure bookkeeping changed.

All AC/task checkboxes reconciled, change statuses complete, chronological completion recorded;
intentional AC deferrals are listed in Wave Summary. Retrospective/canonical documentation complete;
memory proposal zero candidates. Docs-contract performed, no specs changed. Docs validation passes;
framework green receipt current8,580tests, no rerun needed for documentation-only closure repair.
Operator requested close then prepare/review/implement conversion1xjmm; commit remains unrequested.

Final closure review round (2026-09-08): fresh code/QA reviewed the frozen24-file tree; code
PASS with23 focused tests/no skips and four killed implementation mutants. QA initially withheld
receipt/source-model provenance. Independent architecture/performance/release reproduced the results
and found ARCH-001: performance docs still said CPU40. Initial council correctly withheld approval.
The coordinator recorded repair cycle2, corrected only that paragraph, then fresh independent
reassessment cleared ARCH-001 and QA provenance using actual comparator CLI/ONNX parser boundaries.
It verified165calls per corrected lane,47 unchanged/5 improved/exactly3 accepted original-baseline
losses, source/cache hashes and CPU1/GPU40. Its attempted cache-build test was sandbox-unavailable;
no credit is taken for it. Initial code review independently passed cache construction/reuse.

| Final perspective | Verdict/evidence | Context |
| --- | --- | --- |
| Code | PASS:23 focused tests; CPU40, GPU1, wrong builder shape and dynamic-source mutants killed | fresh code/QA session |
| QA | PASS after focused reassessment: real CLI trace/identity validation, exact exceptions, source and ONNX cache hashes | fresh reassessment session |
| Architecture | ARCH-001 independently cleared; corrected prose and old-prose negative control; CPU1/GPU40 property executed | same reassessment session |
| Performance / release | PASS within recorded experimental scope; runtime/platform/scale/availability/migration remain conversion gates | same reassessment session |
| Red-team seat | PASS on bounded merit: shared fourth regression rejected even with clean backend parity; gate/claim omissions rejected | separate fresh seat session |
| Docs-contract / council | Initial REVISE retained; final synthesis pending after clearance | separate council session required |

Full reviewer reports, fingerprints, limitations, mutation tables and reusable control sources are
retained in existing `vector-screen-results.json` under `closure_review`. Shared perspectives are
explicitly one context each. No extra Markdown report files. Framework source remains unchanged
since its8,580-test green receipt; docs lint passes after the correction. Final council, typed
approval refresh and close remain pending. Operator now requests conversion preparation/review/
implementation after this evaluation closes; no conversion code has been edited.

Closure primer (2026-09-08), red-team `conversion_primer`, retained context disclosed; no fresh
approval claimed. Strongest challenge: bounded SQLite evaluation closure cannot substitute for final
independent approval of the actual CPU runtime repair. Best alternative: certify CPU actual-source
identity and its exactly three accepted exceptions, preserve conversion G1–G5 obligations, and leave
INT8 unselected. Reviewer questions: (1) Does final CPU static1 match recorded source/model and relevance
proof? (2) Are all scale/platform/adapter/migration/availability omissions retained in mandatory gates?
(3) Do typed approvals cover this reconciled surface instead of earlier no-Stage2/dynamic1 snapshots?
Five stances applied; no new plan-level blocker. No source probe or executable approval performed.

Close dry-run after reconciliation: docs/gardening PASS; current framework receipt proven (8,580 tests).
Remaining unchecked tasks are only the two final-review tasks. Fresh council readiness and final
independent delivery review are pending; operator closure instruction received but typed operator
signoff will be recorded after review. No close mutation or commit performed. Built-in fresh-agent
limit reached; external CLI review authorization remains pending after automatic approval rejection.

Current continuation checkpoint (2026-09-08): CPU static1 repair passed bounded independent source
and evidence review; original-baseline losses match exactly the three operator-accepted exceptions.
Corrected SQLite/Lance parity passes55pairs x3reps,165 measuredcalls/lane. Current-corpus SQLite
vectorcallp95 docs30.40ms/code9.65ms fits100ms. Detailed mutation, cache/source provenance, rejected
dynamic attempt and reporting corrections are recorded in bug1xj6n and vector-screen-results.json.
Static-repair full suite passed8580 tests/79files/3skips in239.257s on retry; earlier unrelated
TechDocs timing failure is retained in the bug evidence. This is not
full-wave delivery approval; conditional consolidation/runtime/scale qualification remains open.
SQLiteAI sqlite-vector deferred by operator due licensing. No close/commit/package requested.

The earlier report-only/delivery checkpoints below are historical and do not approve the subsequent
CPU repair or consolidation scope.


Final report-only authority refresh: `review-policy-49f4545817aedca79210` is current. The independent reviewer checked final change hash `370463fde230743432ab006923c60612bee3f456`; implementation/test/receipt hashes are unchanged. This preserves the original fresh review evidence and is not a new independent vote. All specialist/council approvals are current; operator signoff remains unrequested.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-08: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: shared exact-path regression does not prove a SQLite storage defect; strongest-alternative: retain 0.33 and investigate reranker stability before Stage 2). Refreshed receipt `review-policy-98de8aa0da53bf1c5bc6`; typed readiness approvals current.
- **Delivery council and required lanes — 2026-09-08: PASS for evaluation/no-production-change.** Isolated red-team primer preceded docs-contract synthesis; five specialist perspectives passed. VP-NaN and VP-Phase repaired in cycle 1 and independently cleared by fresh `vector_final_reverification`; retained-context rechecks were not used as fresh clearance. Shared reviewer perspectives are disclosed in the change doc, not counted as independent votes. No material disagreement remains. Detailed mutation table, fingerprints, limits and reviewer reports are in the existing change doc.
- **Final verification — 2026-09-08: PASS.** Eleven focused tests; four repaired real-storage public filter CLIs; unchanged actual four-lane comparison; full canonical suite 8,578 tests / 79 files / three skips in 207.949 s. A preceding unchanged TechDocs timing failure passed in isolation and on the full rerun; no threshold changed. Memory proposal produced zero candidates. AC-3 is explicitly `[~]` for unexecuted engine-specific/integration probes. Wave stays open; operator signoff, closure and commit are not requested.


Preparation/readiness reviews completed before `wf_implement_wave` opened the wave. Typed readiness
evidence remains in events.jsonl. The original isolated implementation selected no production change under the now-superseded relative budget:
Under the superseded timing rule, both SQLite paths failed and LanceDB 0.38.0 remained uncertified.
Historical budget-revision checkpoint: AC-2/3 originally carried `[~]` no-go notes and were then reopened `[ ]` under the operator's revised
budget. No SQLite Stage 2 work ran in that original evaluation.

2026-09-08 bounded implementation verification by independent `vector_readiness/primer` found no
actionable issue; oracle mutants, fresh-directory refusal, distribution exclusions, 180 sample
summaries and driver hashes verified. The mutation table is in the existing change doc. Full framework
suite passed 8,565 tests / 76 files / 3 skips; full docs validation passed. These checks do not replace
required delivery lanes/council, which remain pending. Wave stays implementing; no closure or commit.

## Dependencies

- No external wave dependencies.

## Context Efficiency

## Context Efficiency

## Context Efficiency

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 225 | 3,545,778 |
| implement | 331 | 4,016,446 |
| review | 414 | 5,936,091 |
| **Total** | **970** | **13,498,315** |

<!-- wave:context-efficiency-state {"generation":848,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":331,"content_source_credit":4675124,"derived_artifact_credit":3926,"direct_net":4016446,"estimated_tokens_saved":4016446,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12399,"response_debit":657650,"source_credit_count":130,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7445},"plan":{"calls":225,"content_source_credit":4366445,"derived_artifact_credit":2666,"direct_net":3545778,"estimated_tokens_saved":3545778,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9086,"response_debit":833083,"source_credit_count":111,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":18836},"review":{"calls":414,"content_source_credit":7047315,"derived_artifact_credit":16435,"direct_net":5936091,"estimated_tokens_saved":5936091,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":88801,"response_debit":1040747,"source_credit_count":257,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":970,"content_source_credit":16088884,"derived_artifact_credit":23027,"direct_net":13498315,"estimated_tokens_saved":13498315,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":110286,"response_debit":2531480,"source_credit_count":498,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":28170},"wave_id":"1xhbo lancedb-038-evaluation"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 29 | 0 | 17 | 13,475,461 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":17,"estimated_exploration_avoided":13475461,"surfaced_events":29} -->
<!-- wave:exploration-avoided end -->
