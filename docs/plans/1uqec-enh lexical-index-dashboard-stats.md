# Lexical Index Dashboard Statistics

Change ID: `1uqec-enh lexical-index-dashboard-stats`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-07
Wave: [wave-id or TBD]

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
   as SQLite FTS5, the ranking as BM25, and the configured tokenizer. It SHALL
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

## Scope

**Problem statement:** The dashboard has no basic lexical-index observability,
even though code and documentation retrieval use a SQLite FTS5 corpus.

**In scope:**

- Add derived, build-cached FTS corpus statistics for all lexical tables.
- Surface a compact Lexical section in the Index dialog using the existing
  section and metric-card visual language.
- Add focused server/dashboard tests for available, missing, and unpopulated
  FTS states.

**Out of scope:**

- Search relevance analytics (latency, zero-result rate, fusion attribution,
  or query history).
- Per-language, per-kind, or per-token drill-down views.
- Changing the tokenizer, BM25 configuration, search ranking, or retrieval
  behavior.

## Acceptance Criteria

- [ ] AC-1: The Index dialog presents a Lexical section that visually matches
  the existing Semantic and Graph sections and, when ready, displays entries,
  indexed-term occurrences, and distinct indexed terms.
- [ ] AC-2: A ready lexical section identifies SQLite FTS5, BM25 ranking, and
  the active tokenizer; the configured `unicode61` tokenizer makes the
  underscore-preservation behavior legible.
- [ ] AC-3: Lexical statistics are persisted or recoverably derived at index
  build/rebuild time, and snapshot reads use the cached values without walking
  the FTS vocabulary.
- [ ] AC-4: Missing, disabled, or not-yet-populated FTS renders an honest
  unavailable/not-built state with no fabricated zero metrics.
- [ ] AC-5: Automated tests cover the statistics producer and the dashboard
  presentation states; the existing framework test suite passes.

## Tasks

- [ ] Define the aggregate FTS statistics contract and build-time computation
  in the index state-store layer.
- [ ] Thread the lexical-health payload through the dashboard snapshot reader.
- [ ] Add the Lexical dialog section and its unavailable state using existing
  index-section styles.
- [ ] Add focused regression tests and run the framework test suite.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| FTS statistics contract | implementer | — | Build-time aggregate counts and availability state. |
| Dashboard presentation | implementer | FTS statistics contract | Read-only snapshot and dialog section. |
| Verification | qa-reviewer | Dashboard presentation | Producer, state, and UI regression coverage. |


## Serialization Points

- `.wavefoundry/framework/scripts/index_state_store.py`, `.wavefoundry/framework/scripts/dashboard_lib.py`, `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A — this is a read-only observability addition within the existing local
index/dashboard boundary. It creates no new integration, ownership, or
primary control-flow contract.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | The visible Lexical section is the requested operator outcome. |
| AC-2 | required | Availability, type, ranking, and tokenizer are the core identification signals. |
| AC-3 | required | Cached snapshot reads protect dashboard responsiveness. |
| AC-4 | required | An unavailable engine must not appear healthy or populated. |
| AC-5 | important | Regression coverage protects the presentation and derived-state contract. |


## Progress Log


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
