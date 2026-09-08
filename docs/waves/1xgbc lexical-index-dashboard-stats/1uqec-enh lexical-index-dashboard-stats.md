# Lexical Index Dashboard Statistics

Change ID: `1uqec-enh lexical-index-dashboard-stats`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-09-08
Wave: 1xgbc lexical-index-dashboard-stats

## Rationale

The Index dialog currently describes the semantic and graph indexes but gives no
operator-visible indication that lexical retrieval is available, which engine
serves it, or whether its corpus is populated. Operators need a small,
read-only summary that matches the existing Semantic and Graph sections and
does not require inspecting the SQLite store or invoking a search tool.

## Requirements

1. The Index dialog SHALL render a peer **Lexical** section below the existing
   Semantic and Graph sections whenever the lexical state-store capability is
   observable.
2. When FTS is available and populated, the section SHALL identify the engine
   and ranking with a single FTS5 BM25 ranking label. It SHALL
   display total indexed entries, total indexed term occurrences, and distinct
   indexed terms.
3. The displayed lexical counts SHALL be derived from the FTS corpus and cached
   with index-build metadata; dashboard snapshots SHALL read those cached values
   and SHALL NOT enumerate the vocabulary on each refresh.
4. When FTS5 is unavailable or its corpus has not been built, the section SHALL
   render a concise unavailable/not-built state rather than misleading zero
   statistics.
5. Lexical statistics SHALL contain aggregate counts and configuration only;
   they SHALL NOT retain user query text, query history, or per-query telemetry.

## Design

Publish one versioned aggregate JSON record in existing state-store metadata. Entries are the sum of actual rows in fts_docs and fts_code; term occurrences sum FTS5 row-vocabulary cnt; distinct terms count the UNION of both vocabularies, not the sum of per-table distinct counts. Only indexed text contributes terms. Configuration identifies SQLite FTS5, BM25 and the existing unicode61 tokenizer with underscore token characters; no tokenizer or search behavior changes.

Invalidate cached statistics atomically with each supported FTS delta/rebuild and capability reset. Refresh at successful epoch finalization, including the staged-parent finalizer, in the same publication transaction; reuse valid unchanged-corpus aggregates on graph-only builds rather than scanning again. Bind the published cache to the completed generation. Failed/in-progress epochs, missing/invalid cache, disabled FTS, and an empty/unbuilt corpus do not expose fabricated ready counts. A statistics-computation error leaves an explicit unavailable state without turning this observational feature into a new indexing failure gate. Existing installations gain statistics at a subsequent successful build/finalization; until then the panel explains that statistics are not built. No schema-version reset or vocabulary persistence is needed.

Expose a bounded read-only lexical_statistics reader using metadata/build-state only in one consistent read transaction. It must not create or repair a store, enumerate FTS rows or vocabulary, retain terms, or record user queries. Add health.lexical.project to the existing snapshot, and a peer LexicalIndexSection below Graph using current index-section/metric styles. Ready payload includes status, engine, ranking, tokenizer, entries, term_occurrences, distinct_terms; non-ready payload has a concise reason and no metrics. Per operator refinement, show only the FTS5 BM25 ranking label using the same index-meta-pill index-meta-pill--model styling as Semantic and Graph; omit tokenizer identification and underscore explanation from the UI. Add ready distinct terms to the home Index tile using its existing metric-subnote style.

Verification uses a known overlapping docs/code vocabulary, repeated tokens, unindexed metadata, replacement/deletion, failed/interrupted epochs, old/malformed/missing cache, disabled FTS, both finalizers, unchanged-corpus reuse, and snapshot SQL tracing that rejects corpus/vocabulary access. Execute rendered JavaScript section controls for ready/unavailable/empty states, plus a disposable browser smoke test if the available host permits. Measure build aggregation on a representative synthetic corpus; no new per-query telemetry or retrieval-quality claim.

Files: index_state_store.py and its existing test file, dashboard_lib.py, dashboard.js and existing dashboard tests; update the index/dashboard architecture explanation and concise 1.22.0 changelog entry. Prior closed-wave edits stay intact. One backend implementer owns store and producer tests; coordinator owns dashboard integration/presentation and docs, with independent QA computation checks.

## Scope

**Problem statement:** The dashboard has no basic lexical-index observability,
even though code and documentation retrieval use a SQLite FTS5 corpus.

**In scope:**

- Add derived, build-cached FTS corpus statistics for all lexical tables.
- Surface a compact Lexical section in the Index dialog using the existing
  section and metric-card visual language, and ready distinct terms on the home Index tile.
- Add focused server/dashboard tests for available, missing, and unpopulated
  FTS states.

**Out of scope:**

- Search relevance analytics (latency, zero-result rate, fusion attribution,
  or query history).
- Per-language, per-kind, or per-token drill-down views.
- Changing the tokenizer, BM25 configuration, search ranking, or retrieval
  behavior.

## Acceptance Criteria

- [x] AC-1: The Index dialog presents a Lexical section that visually matches
  the existing Semantic and Graph sections and, when ready, displays entries,
  indexed-term occurrences, and distinct indexed terms.
- [x] AC-2: A ready lexical section displays one FTS5 BM25 ranking label
  using the same font color and pill styling as the Semantic and Graph labels.
- [x] AC-3: Lexical statistics are persisted or recoverably derived at index
  build/rebuild time, and snapshot reads use the cached values without walking
  the FTS vocabulary.
- [x] AC-4: Missing, disabled, or not-yet-populated FTS renders an honest
  unavailable/not-built state with no fabricated zero metrics.
- [x] AC-5: Automated tests cover the statistics producer and the dashboard
  presentation states; the existing framework test suite passes.

## Tasks

- [x] Define the aggregate FTS statistics contract and build-time computation
  in the index state-store layer.
- [x] Thread the lexical-health payload through the dashboard snapshot reader.
- [x] Add the Lexical dialog section and its unavailable state using existing
  index-section styles.
- [x] Add focused regression tests and run the framework test suite.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| FTS statistics contract | implementer | — | Build-time aggregate counts and availability state. |
| Dashboard presentation | implementer | FTS statistics contract | Read-only snapshot and dialog section. |
| Verification | qa-reviewer | Dashboard presentation | Producer, state, and UI regression coverage. |


## Serialization Points

- `.wavefoundry/framework/scripts/index_state_store.py`, `.wavefoundry/framework/scripts/dashboard_lib.py`, `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/`

- `docs/architecture/`
- `CHANGELOG.md`

## Affected Architecture Docs

Update the existing index/dashboard architecture explanation with the additive cached aggregate contract and publication/read boundaries; no new integration or ownership boundary.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | The visible Lexical section is the requested operator outcome. |
| AC-2 | required | The operator-revised engine/ranking label must match the existing index labels. |
| AC-3 | required | Cached snapshot reads protect dashboard responsiveness. |
| AC-4 | required | An unavailable engine must not appear healthy or populated. |
| AC-5 | important | Regression coverage protects the presentation and derived-state contract. |


## Progress Log

Operator correction (2026-09-08): AC-2 was modified and implemented, not deferred. Replaced the original criterion with the delivered single FTS5 BM25 ranking label and matching style, and marked it [x]. Earlier [~]/deferral descriptions below are superseded historical bookkeeping. No delivery scope or source change; all five current ACs are complete.

Observe / final UI refinements: operator refreshed the dashboard and reported “Refresh looks great.” Final canonical framework suite passed 8,558 tests across 75 files in 221.034 seconds, three skips, after the home-tile and label/style changes. Documentation validation and diff whitespace checks passed. Framework edit gate closed; delivery review remains pending.

Observe / tile verification: all three LexicalDashboardTests passed. The existing test_lexical_section_executes_ready_unavailable_and_dialog_states now executes Metrics and checks ready count, metric-subnote style, zero and absent/unavailable/updating/malformed counts. Temporary mutants show_stale_tile_count, accept_negative_or_fractional_tile_count and hide_zero_tile_count each fail assertions in that test. An initial overbroad numeric-guard removal instead raised a production TypeError on undefined; the corrected bounded numeric mutant confirms the assertion pin.

Thought / operator tile addition: add cached distinct terms to the home Index tile using the existing metric-subnote style. Only a ready, nonnegative safe-integer count is displayed; missing, updating or unavailable statistics are omitted. Reuse the existing health payload without new reads. Extend the existing executed JavaScript coverage to the actual Metrics component. This is the operator-authorized display extension to the admitted dashboard work; no publication or retrieval contract changes.

Observe / styling correction: the first single-label edit reused only the base pill class and missed the model modifier used by both Semantic and Graph. Apply the identical index-meta-pill index-meta-pill--model classes to FTS5 BM25 ranking; the existing render assertion now checks that exact shared styling. The preceding full run passed 8,558 tests with three skips; rerun verification for this correction.

Gapfill / bookkeeping: wf_mark_ac failed with an import error for scanner_skips.is_recordable_path; recorded the operator-directed AC-2 narrowing directly in this document. Delivery review must use this revised UI scope.

Thought / operator UI refinement (2026-09-08): replace the three metadata tags with one “FTS5 BM25 ranking” tag using the existing index-meta-pill styling. Operator explicitly removed tokenizer identification and explanation from the UI; cached configuration remains in the payload. AC-2 tokenizer-display portion is intentionally not met by operator direction. Update the existing render test, architecture description and changelog to match.

Thought / operator UI refinement (2026-09-08): remove the sentence “Underscores stay within tokens.” from both the visible Lexical section and its tooltip, as requested. The tokenizer configuration remains visible. This supersedes the explanatory-sentence detail in Design; update the existing render assertion accordingly. No indexing behavior changes.

Observe / final computational verification: canonical run_tests.py passed 8,558 tests across 75 files in 198.246 seconds, with three skips, writing a green framework receipt. Backend mutation pins: double_count_shared_terms fails LexicalStatisticsTests.test_overlap_repetitions_underscore_and_unindexed_fields; skip_delta_invalidation fails test_replacement_delete_and_rebuild_invalidate_atomically; accept_boolean_counts fails two subtests in test_in_progress_stale_and_malformed_cache. All were assertion failures, not harness errors. All ACs and tasks are implemented; required delivery review remains pending. Framework and seed edit gates are closed. No commit or new-wave closure performed.


Observe / checkpoint repair recheck: independent original checkpoint reviewer confirmed ARCH-CP-1 resolved. Removing the runtime capability guard makes test_current_runtime_without_fts_cannot_advertise_published_cache fail with “capability rejection needs no store read.” Store/test blobs remained b6ccd2b37024ff4858a4e1afcce6f99630c28c16 / 7275b1ea5b2eb6cd3c2fe93e317e89b420105932 across recheck. This is independent of the repair author, not a fresh-context delivery approval. Complete dashboard test file passed 201 tests with one skip, warning-strict. Full documentation validation passed without warnings.


Observe (2026-09-08): backend cache publication, dashboard payload and Lexical section implemented. Actual overlapping docs/code corpus yields 3 entries, 7 occurrences and 4 global terms. Executed production JavaScript component and IndexDialog confirm ready metrics/configuration, section ordering, valid zero term counts, and metric omission for missing/empty/updating/disabled/invalid states. Existing styles reused; no CSS, tokenizer, ranking or telemetry changes. Architecture and 1.22.0 changelog updated.

Thought / named checkpoint: epoch publication and cache validity are the high-risk boundary. Independent architecture/performance checkpoint inspected both finalizers, transactional invalidation, savepoint isolation, strict numeric cache validation and bounded readers. ARCH-CP-1 reproduced stale runtime capability: a cache published with FTS5 still advertised ready when the current runtime lacked FTS5. Reflect: persisted capability is not current runtime capability; use the existing cached in-memory capability check before reading stored statistics. Bounded repair landed with a regression that changes runtime capability without reopening a writer. No scope expansion or re-prepare required.

Observe / computational verification: 65 state-store tests passed. Real file/WAL synthetic corpus of 50,000 entries produced 300,000 occurrences and 50,003 distinct terms; finalization aggregation took 36.60 ms, unchanged graph-only reuse 1.42 ms, and 100 bounded readers averaged 0.345 ms. These are local synthetic observations, not a performance guarantee. SQL tracing verifies metadata/build-state-only snapshot reads. Three dashboard integration/render tests passed warning-strict. Four JavaScript mutants (show_stale_counts, accept_bad_counts, hide_zero_terms, drop_dialog_section) each fail test_lexical_section_executes_ready_unavailable_and_dialog_states.

Observe / smoke-test limit: disposable production dashboard fixture published 2 entries, 7 occurrences and 4 distinct terms, and its HTTP server started successfully. Browser visual inspection could not run because the computer-use service reported “Sky Computer Use native pipe startup failed.” The fixture server was stopped. Executed production JavaScript and real snapshot tests provide functional coverage; no browser screenshot or visual pass is claimed.


Readback / Thought: replace the absent lexical panel with a peer section displaying real cached FTS corpus counts and configuration, while non-ready states omit metrics. AC-1/2 govern UI, AC-3 publication/invalidation/read cost, AC-4 honest states, AC-5 regression verification. Sequence: backend implementer adds cache lifecycle/reader and producer tests; coordinator adds dashboard wiring/section/render tests and concise architecture/changelog; merge, run focused controls and full suite. Source ownership is disjoint. Preserve all prior closed-wave changes. Memory advisories applied: never reset on stats/lock errors, validate numeric metadata without bool/float coercion, preserve publisher authorization. No seeds or ranking changes.

Thought / planning refinement (2026-09-08): current store indexes text only with unicode61 underscore preservation; both normal and staged-parent finalizers publish generations. Primer demonstrated shared terms must be counted by UNION. Scope now names writer invalidation, generation-bound publication, bounded read-only snapshots, old-install behavior, and nonfatal statistics failure before readiness. User requested this enhancement and acknowledges its dashboard UX/admission. Requirements/AC priorities remain unchanged.


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-07 | Planned Lexical Index dashboard statistics enhancement. | Operator request and current Index dialog review. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-07 | Cache aggregate FTS statistics at build time and display them in a third Index-dialog section. | Provides stable, low-cost operator visibility without adding query telemetry or refresh-time vocabulary scans. | Static metadata-only panel: cannot confirm corpus population. Live vocabulary scan on every dashboard snapshot: adds recurring read cost and inconsistent timing. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Vocabulary aggregation may cost too much on a large corpus. | Measure it in the build path; persist the result and avoid dashboard-time scans. |
| Cached statistics could lag after interrupted lexical synchronization. | Bind statistics to successful build/reconcile state and render not-built/unknown when that state is absent. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
