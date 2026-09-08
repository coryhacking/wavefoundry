# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-08
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1xgbc lexical-index-dashboard-stats`
Title: Lexical Index Dashboard Stats

## Objective

Show cached lexical corpus counts and a single FTS5 BM25 ranking label in the Index dialog, plus ready distinct terms on the home Index tile, without adding work to search or scanning vocabulary during dashboard refreshes.

## Changes

Change ID: `1uqec-enh lexical-index-dashboard-stats`
Change Status: `implemented`

## Participants

- Coordinator: wave coordinator
- Write-owning roles: implementer (state store/tests), coordinator (dashboard/docs)
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer

Completed At: 2026-09-08

## Wave Summary

Wave `1xgbc` (Lexical Index Dashboard Stats) delivered one change: Lexical Index Dashboard Statistics.

**Changes delivered:**

- **Lexical Index Dashboard Statistics** (`1uqec-enh lexical-index-dashboard-stats`) — 5 ACs completed. Key decisions: Cache aggregate FTS statistics at build time and display them in a third Index-dialog section.
The Index dialog includes one FTS5 BM25 ranking label with matching styling, and the home Index tile shows ready distinct terms. AC-2 was revised and implemented; all five ACs are complete, with no deferrals. Included in CHANGELOG 1.22.0.

Closure reconciliation: code, QA, architecture and performance delivery reviews passed; current green receipt proves 8,558 tests with three skips. Docs-contract review is not applicable: no specs or seed contracts changed. Memory proposal returned no candidates. Retrospective: completed publication identity and current runtime FTS capability both govern cache validity; the existing architecture page and tests preserve that lesson without duplicate memory. All edit gates are closed; no open questions or deferred decisions. Handoff is idle. Changes remain uncommitted.

## Watchpoints

- Watchpoint: preserve the previous closed wave's uncommitted changes.
- Compute distinct terms by cross-table vocabulary union; no corpus scans in dashboard reads.
- Cache validity follows completed publication and mutation invalidation; no false ready metrics during failed/partial builds.
- Product-owner acknowledgment: operator explicitly selected change1uqec for preparation, review and implementation.
- Operator authorized closure after delivery review; no commit requested.

## Review checkpoints

Final delivery review (2026-09-08): PASS, no actionable findings. Fresh independent code and QA contexts plus one fresh paired architecture/performance context reviewed the frozen implementation. Code and QA each independently executed 16 selected store/dashboard tests with zero skips; architecture/performance did likewise. No full-suite rerun was needed because source stayed unchanged and close verifies the current green 8,558-test receipt. Operator visual confirmation is separate from Node component verification; no agent browser/CSS computation pass is claimed.

Readiness refreshed for final operator scope under receipt review-policy-692b03d5bdf3080699f6: standard red-team primer and rotating architecture seat, unanimous PASS, no disagreements. The stale-tile challenge was tested with real production JS; existing-payload reuse was the strongest alternative and is implemented. A readiness-safe negative control rejected omission of staged-parent publication from the writer census. AC-2 is revised and implemented, not deferred. The earlier architecture fingerprint was corrected after Prepare gardening changed only its Last verified date; reviewers verified the corrected blob2036ab4cda5b957ff77a2f073e3ae4386a4ec833. No source moved under review.

Reviewer evidence: code independently compared the public publication/reader chain with a six-entry ASCII oracle (6 entries, 10 occurrences, 5 distinct terms), then moved all entries into one table and observed unchanged counts. QA mapped all five revised ACs to real producer/snapshot/component tests. Architecture verified text-only indexing, both finalizers, atomic invalidation and nonfatal statistics errors. Performance verified SQL-traced bounded metadata reads and unchanged-corpus reuse; the earlier 50,000-entry timings were not independently remeasured. No ranking or retrieval-quality claim. All selected controls ran without unintended skips; each lane supplied five true evidence-integrity fields based on its own execution.

| Focused mutation | Detecting test (test_index_state_store.LexicalStatisticsTests unless noted) | Lanes / result |
| --- | --- | --- |
| Remove delta/rebuild invalidation | test_replacement_delete_and_rebuild_invalidate_atomically | Code, QA, architecture/performance: detected |
| Remove capability reset invalidation | test_staged_parent_computes_new_cache_and_capability_change_removes_it | Code: detected |
| Loosen version type/value, bool/negative counts, distinct upper bound, generation binding | test_in_progress_stale_and_malformed_cache | Code; QA bool control: detected |
| Force aggregation instead of cache reuse | test_both_finalizers_reuse_unchanged_cache_and_reject_cas_miss | Code, architecture/performance: detected |
| Sum per-table distinct terms | test_overlap_repetitions_underscore_and_unindexed_fields | All lanes: detected |
| Remove runtime FTS guard | test_current_runtime_without_fts_cannot_advertise_published_cache | All lanes: detected |
| Remove coherent read transaction / inject FTS census | test_snapshot_reads_only_metadata_and_build_state | Code transaction; QA census; architecture/performance both: detected |
| Let statistics SQLite error escape | test_both_finalizers_isolate_statistics_error_without_reset | Code, architecture/performance: injected database error escaped as expected |
| Remove normal/staged finalizer publication | test_overlap_repetitions_underscore_and_unindexed_fields; test_staged_parent_computes_new_cache_and_capability_change_removes_it; test_both_finalizers_reuse_unchanged_cache_and_reject_cas_miss | QA, architecture/performance: detected |
| Show stale/malformed tile or dialog counts, hide zero, drop dialog, remove shared label color class | test_dashboard_server.LexicalDashboardTests.test_lexical_section_executes_ready_unavailable_and_dialog_states | QA: detected |
| Remove snapshot lexical wiring | test_dashboard_server.LexicalDashboardTests.test_snapshot_publishes_real_cached_lexical_counts_and_hides_incomplete_build | QA: detected |

Code ran 14 targeted mutants, QA 15, architecture/performance 10. No survivors required whole-file mutation sweeps. Limits: finite selected cases, no exhaustive Unicode oracle, concurrency census or browser rendering. QA excluded an artificial AssertionError experiment from evidence. Reports are recorded here and in typed events.jsonl, with no extra Markdown files.


Implementation checkpoint: architecture/performance independently inspected transactional cache publication, both finalizers, savepoint isolation, mutation invalidation and bounded read paths. ARCH-CP-1 (runtime FTS availability could differ from persisted capability) was repaired and independently rechecked; deleting the runtime guard fails its named regression. Detailed controls and timings are recorded in the existing change Progress Log. No delivery-lane approval is claimed from this checkpoint; required delivery review remains pending.


Readiness Council PASS, receipt review-policy-81b344fdb434f25723a7: standard red-team primer, architecture rotating seat, with code/QA and architecture/performance in two independent paired contexts. Actual FTS writer verified overlap, underscore, unindexed-field, one-table, replacement/deletion controls. Actual epoch probe rejected generation-only readiness (building retains generation1); SQL trace caught an injected vocabulary poll. Merit-first synthesis found no disagreement or blocker: seat_agreement unanimous, max_severity none. Both publication finalizers, writer invalidation, strict cache shapes and unavailable states remain delivery checks; no future implementation behavior is claimed yet. Existing performance policy calls for bounded polling and measured aggregation, not a retrieval-eval run solely from module identity membership.

Standard red-team primer completed before readiness seats. It challenged stale ready counts after partial/interrupted publication and specified cross-table union semantics. SQLite probe: docs alpha alpha beta / beta gamma and code alpha delta give3entries7occurrences4distinctterms; summing per-table distinct counts wrongly gives5. Synthetic50,000-entry aggregation took38.36ms in memory, a feasibility observation rather than disk/WAL guarantee. Revised Design names both finalizers, writer invalidation, coherent bounded reads, nonfatal aggregation errors and upgrade-era missing caches. Seats must assess these seams and honest disabled/empty/stale states. No source edits yet.

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
| performance-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 48 | 1,010,163 |
| implement | 85 | 763,326 |
| review | 67 | 80,309 |
| **Total** | **200** | **1,853,798** |

<!-- wave:context-efficiency-state {"generation":148,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":85,"content_source_credit":891515,"derived_artifact_credit":0,"direct_net":763326,"estimated_tokens_saved":763326,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3026,"response_debit":127586,"source_credit_count":25,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2423},"plan":{"calls":48,"content_source_credit":1102130,"derived_artifact_credit":1221,"direct_net":1010163,"estimated_tokens_saved":1010163,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5671,"response_debit":93213,"source_credit_count":32,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5696},"review":{"calls":67,"content_source_credit":258462,"derived_artifact_credit":931,"direct_net":80309,"estimated_tokens_saved":80309,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7578,"response_debit":173395,"source_credit_count":21,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":200,"content_source_credit":2252107,"derived_artifact_credit":2152,"direct_net":1853798,"estimated_tokens_saved":1853798,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16275,"response_debit":394194,"source_credit_count":78,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10008},"wave_id":"1xgbc lexical-index-dashboard-stats"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 4 | 0 | 2 | 3,330,090 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":3330090,"surfaced_events":4} -->
<!-- wave:exploration-avoided end -->
