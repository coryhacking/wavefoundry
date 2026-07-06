# FTS5 Hybrid Lexical Retrieval and SQLite Index Internals

Change ID: `1rrr0-enh sqlite-fts5-and-index-internals`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-04
Wave: `1rsh9 sqlite-index-substrate`

## Rationale

With the index-state store landed (`1rq4h-enh sqlite-index-state-store`), the semantic index gains a general-purpose relational substrate — and two long-standing internals become cheap to fix on top of it.

**Lexical retrieval.** The project's own retrieval-quality findings are consistent: the lever is hybrid lexical + reranking, not a better embedder. Dense retrieval is weakest exactly where agents need precision — exact identifiers, rare tokens, error strings — and today the only lexical option is `code_keyword`'s live grep, which never participates in ranked retrieval fusion. Doing lexical scoring inside LanceDB would be clunky: it has no BM25, so it would mean hand-rolled term scoring bolted onto a vector store. SQLite FTS5 ships in Python's bundled SQLite, provides real BM25, and lives in the store this wave already establishes. Fusing BM25 candidates into `search_combined`'s candidate pool costs one extra fetch and rides the existing rerank-first architecture, which already normalizes heterogeneous candidate sources.

**Bookkeeping.** `meta.json` is a whole-file JSON snapshot of per-path state, rewritten and atomically swapped every build — with dedicated Windows-contention retry machinery (wave 1p9iw) because other processes hold it open mid-swap. It works, but it scales badly in both rewrite and parse cost, and the incremental-update path separately re-reads Lance rows to compare `chunk_hash` values. Moving per-path working state (hashes, mtimes, chunk registry, drift/eligibility state) into the store makes builds transactional and incremental lookups index-backed, while `meta.json` continues to be written as an exported snapshot so every existing reader (dashboard, build status, freshness checks) keeps its contract unchanged.

Both halves follow the store's derived-only rule: FTS tables and bookkeeping rebuild from Lance/repo/git; losing the store is a rebuild, never data loss. And both are evidence-gated: the lexical layer must prove it helps on the known weak query patterns before it defaults on, and each internal optimization is audit-and-adopt with measured timings — no silent adoption.

## Requirements

1. **FTS5 availability detection:** setup/build probes FTS5 support in the running interpreter's SQLite once and records the result; absence degrades cleanly — no lexical tables, no errors, response metadata reflects vector-only retrieval. No new dependencies and no loadable extensions.
2. **FTS tables in the index-state store, ordered-consistency model (readiness-council amendment):** FTS5 tables over docs and code chunk text, keyed by chunk id, maintained in the same build pass as chunk upserts/deletes. Cross-engine atomicity between Lance and SQLite is explicitly **not** claimed: Lance is authoritative for chunk existence; the store's FTS rows commit in a single SQLite transaction ordered after the corresponding Lance writes; and a cheap reconciliation pass (chunk-id set comparison, derived-only rebuild on mismatch, loud diagnostic) repairs any crash window between the engines. FTS table mode (contentless vs contentful) is chosen at implementation against the bundled SQLite version's delete-support and recorded in the Decision Log; chunk text for display always comes from Lance.
3. **Query-path fusion:** `search_combined` fetches top-K BM25 candidates (named constant) alongside vector candidates and merges them into the candidate pool **before** the cross-encoder rerank, respecting the existing candidate-count and text-budget constants; when the reranker is unavailable, lexical candidates join the existing RRF fallback with an explicit weight constant. Citations gained via the lexical path carry a source marker (extend the existing `source`/`sources` convention). User query text reaches FTS5 only through parameterized statements with FTS-syntax escaping/quoting (readiness-council amendment); a query FTS5 rejects degrades that call to vector-only with no error. A kill-switch env var disables lexical fusion entirely.
4. **`code_keyword` unchanged:** live grep remains the exactness contract for exact-token queries; FTS is a ranked-retrieval candidate source, not a keyword-tool replacement.
5. **Quality gate before default-on:** evaluate hybrid fusion against the documented weak query patterns (exact identifiers, rare tokens, error strings) on this repository using a **fixed query set recorded in this change doc** (readiness-council amendment — prevents eval drift between before/after runs); record before/after findings here. If fusion degrades quality, it ships default-off behind the kill switch with the evidence recorded — mirroring the census-gate pattern from `1ro43`.
6. **Per-path bookkeeping migration:** the store becomes the working source of truth for per-path build state — content hashes, mtimes, chunk counts, chunk registry (path → chunk ids + `chunk_hash`), and drift/eligibility state — written transactionally per build.
7. **`meta.json` becomes an exported snapshot:** generated from the store at the end of each build, **reader-contract compatible** (readiness-council amendment): existing reader tests pass unmodified and parsed content is semantically identical; byte-level equality is not the contract (key order and formatting may differ). The atomic-swap and Windows-retry machinery is retained for the snapshot write. Reader migration (dashboard, build status, drift checks reading the store directly) is explicitly deferred to a later change.
8. **Chunk-registry incremental path:** incremental updates consult the registry instead of re-reading Lance rows for `chunk_hash` comparison, adopted only where a differential audit proves equivalence with the current Lance-read path — including the drift/eligibility semantics from the lance-drift gating work — and never weakening drift detection.
9. **Audit-and-adopt internals list:** additional internal optimizations (e.g. repeated `meta.json` parse elimination, build-stats aggregation through the store) are audited individually; each adopted item records measured build-timing evidence in this doc, each skipped item records why. Silent adoption or silent skipping is prohibited.
10. **Local-only and mechanical:** no network, no LLM in tools; all new query-path work is deterministic candidate fetch + existing fusion machinery.
11. **Secret posture is inherited, not weakened (documented control):** the FTS tables store chunk text that is already materialized in the Lance store — the same content, under the same gitignored `.wavefoundry/index/` path, excluded from packaging (`build_pack` ships source only). This change introduces no new secret *source*, no new distribution path, and no new redaction obligation; the existing controls remain the origin gate (build-time source scan in `indexer.py` + the `wave_close` secrets gate). This is a stated, tested assertion rather than an implicit assumption.
12. **FTS5 segment maintenance (the SQLite analog of Lance compaction):** FTS5 external-content tables accumulate b-tree segments on incremental insert/delete exactly as Lance accumulates fragments on append churn. Contribute an FTS `optimize`/`merge` step (`INSERT INTO <fts>(<fts>) VALUES('optimize')`, or bounded `'merge'`) into the unified `wave_index_optimize` maintenance path that `1rq4h` establishes — not a parallel maintenance surface. A threshold (segment/churn count, a named constant mirroring `LANCEDB_COMPACT_THRESHOLD`) gates the in-build incremental merge; the full `optimize` runs on the on-demand/at-setup/at-upgrade path alongside the store's WAL/vacuum maintenance. Skipped cleanly when FTS is unavailable (Requirement 1).
13. **FTS5 integrity-check contributed to the `1rq4h` probe:** wire FTS5's internal-consistency check (`INSERT INTO <fts>(<fts>) VALUES('integrity-check')`) into the shared integrity probe that `1rq4h` Requirement 11 establishes — not a parallel path. It runs where the probe runs (store open + `wave_index_optimize`), a failure routes to the same derived-only drop-and-rebuild (rebuilding the FTS tables from Lance chunk text), and it is skipped cleanly when FTS is unavailable. The FTS tables also participate in logical-staleness detection by binding to the same chunk-set fingerprint the ordered-consistency reconciliation (Requirement 2) already tracks.

## Scope

**Problem statement:** Ranked retrieval has no lexical signal despite hybrid-lexical being the documented quality lever, and per-path build bookkeeping lives in a whole-file JSON with growing rewrite/parse costs plus a Lance-row-scan incremental path — both now trivially better-served by the index-state store.

**In scope:**

- FTS5 probe + graceful degrade; FTS tables synced in build transactions.
- BM25 candidate fetch and fusion in `search_combined` (rerank-first pool merge, RRF fallback weight, source markers, kill switch).
- Weak-pattern retrieval evaluation and the default-on/default-off decision with recorded evidence.
- Per-path bookkeeping tables + chunk registry in the store; `meta.json` generated as a byte-compatible exported snapshot.
- Registry-backed incremental path behind a differential equivalence audit.
- Audit-and-adopt internals list with measured evidence.
- Secret-posture assertion for the store: gitignored index-dir residency + packaging exclusion, tested.
- FTS5 segment `optimize`/`merge` maintenance contributed into the `1rq4h` `wave_index_optimize` path (threshold-gated in-build merge + full optimize on-demand/setup/upgrade).
- FTS5 `integrity-check` and chunk-set fingerprint binding contributed into the `1rq4h` integrity probe (physical + logical), routing to FTS rebuild from Lance.
- Tests: FTS sync atomicity, degrade path, fusion behavior with/without reranker, kill switch, snapshot byte-compatibility, registry differential, drift-detection non-regression, store secret-posture (gitignore + packaging exclusion), FTS segment count bounded after churn, FTS integrity-check detects a corrupted FTS table and rebuilds.

**Out of scope:**

- The store substrate itself (schema versioning, recovery, freshness tables) — owned by `1rq4h`.
- Replacing `code_keyword`, `code_pattern`, or any exact-navigation tool.
- Migrating `meta.json` readers to the store (deferred; snapshot preserves all contracts this change).
- Vector storage changes, embedder changes, or reranker changes.
- New Python dependencies or SQLite loadable extensions.

## Acceptance Criteria

- [ ] AC-1: On an FTS5-capable interpreter, builds maintain FTS rows under the ordered-consistency model — the store transaction commits after the corresponding Lance writes, and a crash-window fixture (interrupt between Lance write and store commit) is repaired by the reconciliation pass on the next build with a loud diagnostic; on an FTS5-less interpreter, builds and queries succeed vector-only with a recorded diagnostic and no errors.
- [ ] AC-2: `search_combined` merges top-K BM25 candidates before rerank within the existing candidate/text-budget constants; lexically-sourced citations carry the source marker; with the reranker unavailable, RRF applies the named lexical weight; FTS-hostile query strings (operators, quotes, malformed syntax) are escaped or degrade that call to vector-only without error; the kill switch removes all lexical participation.
- [ ] AC-3: The weak-pattern evaluation (exact identifiers, rare tokens, error strings) is recorded in this doc with before/after results, and the default-on vs default-off decision follows the evidence.
- [ ] AC-4: `meta.json` written post-migration is reader-contract compatible — existing dashboard and build-status tests pass unmodified against the snapshot and parsed content is semantically identical to the pre-migration writer — and the store is the working source of truth for per-path state during the build.
- [ ] AC-5: The registry-backed incremental path is proven equivalent to the Lance-read path by a differential harness across add/modify/delete/rename fixtures, including drift/eligibility cases, before it replaces the Lance reads; any non-equivalent case keeps the Lance-read path and is documented.
- [ ] AC-6: Each audit-and-adopt internals item is dispositioned in this doc — adopted with measured timing evidence or skipped with rationale; none are silent.
- [ ] AC-7: Index/builder version bumps follow convention for the schema and snapshot changes; incremental updates across the version boundary rebuild cleanly rather than mixing formats.
- [ ] AC-8: A test asserts the FTS/state store artifacts live under gitignored `.wavefoundry/index/` and are excluded from the packaged distribution (`build_pack`), and that FTS stores no chunk text not already present in Lance — the secret posture matches the existing Lance store, with no new redaction path introduced.
- [ ] AC-9: FTS5 segment maintenance runs through `wave_index_optimize` (and at setup/upgrade), with a threshold-gated in-build merge; a fixture shows FTS segment count stays bounded after repeated incremental insert/delete churn, and the step is skipped without error when FTS is unavailable.
- [ ] AC-10: FTS5 `integrity-check` runs inside the `1rq4h` integrity probe (store open + `wave_index_optimize`); a fixture that corrupts an FTS table is detected and rebuilt from Lance chunk text with no query-path error, and the check is skipped cleanly when FTS is unavailable.
- [ ] AC-11: Full framework tests run bytecode-free and docs validation passes.

## Tasks

- [ ] Implement the FTS5 probe with recorded capability state and degrade path.
- [ ] Add FTS tables + same-transaction sync to the build path; atomicity fixtures.
- [ ] Implement BM25 candidate fetch + pool merge in `search_combined`, source markers, RRF weight, kill switch.
- [ ] Build and run the weak-pattern evaluation; record findings and the default decision.
- [ ] Implement per-path bookkeeping tables + chunk registry; make the build write them transactionally.
- [ ] Generate `meta.json` as an exported snapshot from the store; keep swap/retry machinery; byte-compatibility tests.
- [ ] Build the registry-vs-Lance differential harness; flip the incremental path only on proven equivalence.
- [ ] Work the audit-and-adopt internals list; record dispositions with timings.
- [ ] Wire FTS5 `optimize`/`merge` into the `1rq4h` `wave_index_optimize` maintenance path (threshold-gated in-build merge; full optimize on-demand/setup/upgrade); FTS-segment-bounded fixture.
- [ ] Wire FTS5 `integrity-check` + chunk-set fingerprint into the `1rq4h` integrity probe (rebuild FTS from Lance on failure); FTS-corruption fixture.
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| fts-layer | implementer | — (store from 1rq4h) | Probe, tables, transaction sync |
| fusion | implementer | fts-layer | Pool merge, markers, RRF weight, kill switch |
| retrieval-eval | qa-reviewer | fusion | Weak-pattern evaluation, default decision |
| bookkeeping | implementer | — (store from 1rq4h) | Per-path tables, registry, snapshot export |
| incremental-flip | implementer | bookkeeping | Differential harness, path switch |
| tests-docs | qa-reviewer | all implementation streams | Atomicity, compat, non-regression, validation |


## Serialization Points

- Hard dependency within the wave: `1rq4h` store substrate (schema versioning, recovery, helpers) lands first; this change adds resident schemas to it.
- The incremental-path flip (Requirement 8) is blocked until the differential harness passes; the Lance-read path is retained as the fallback until then.
- The fusion default-on decision is blocked until the retrieval evaluation (Requirement 5) is recorded — same evidence-gate discipline as `1ro43`'s census.
- `meta.json` snapshot byte-compatibility must be proven before the store becomes the working source of truth (readers keep their contract throughout).
- FTS segment maintenance (Requirement 12) contributes into the `wave_index_optimize` extension that `1rq4h` (Requirement 10) establishes — it must plug into that path, not create a second maintenance surface; sequence after the `1rq4h` maintenance primitive lands.

## Affected Architecture Docs

- `docs/architecture/search-architecture.md` — hybrid lexical layer, fusion placement, capability degrade, bookkeeping/source-of-truth shift.
- `docs/architecture/data-and-control-flow.md` — build transaction covering Lance + FTS + bookkeeping; snapshot export flow.
- `docs/architecture/testing-architecture.md` — differential harness tier for the incremental flip.
- ADR recommended: FTS5-in-state-store vs LanceDB-side lexical vs external lexical dependency.

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Transactional FTS/Lance consistency and clean degrade are the correctness contract of the lexical layer. |
| AC-2 | required | Fusion mechanics with markers and kill switch are the shippable behavior. |
| AC-3 | required | Evidence-gated default is the discipline that keeps retrieval quality from regressing on faith. |
| AC-4 | required | Reader contracts must survive the source-of-truth shift; byte-compatibility is the proof. |
| AC-5 | required | The incremental flip touches the index's integrity path; equivalence must be proven, not assumed. |
| AC-6 | important | Disposition discipline for the internals list; value is auditability, not shipped behavior. |
| AC-7 | required | Version-boundary hygiene is a standing convention for index format changes. |
| AC-8 | required | The FTS store adds a second on-disk copy of chunk text; the inherited-posture claim must be a tested control, not an assumption. |
| AC-9 | required | Without segment maintenance FTS degrades under churn exactly as an uncompacted Lance table does; it must ride the unified maintenance verb, not a parallel one. |
| AC-10 | required | FTS has its own corruption surface (segment b-trees); the FTS integrity-check must ride the shared probe so a bad FTS table is caught and rebuilt, not silently returning wrong lexical hits. |
| AC-11 | required | Standard framework verification gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-04 | Drafted from operator direction: combine FTS5 hybrid lexical and meta.json/bookkeeping internals into one change on the `1rq4h` store substrate, with lexical-in-LanceDB explicitly rejected as clunky. | Retrieval-quality findings (hybrid-lexical lever, dense weak patterns); `meta.json` swap/retry machinery (wave 1p9iw); `chunk_hash` Lance-read incremental path in `indexer.py`. |
| 2026-07-04 | Readiness-council amendments applied: cross-engine atomicity claim replaced with the ordered-consistency + crash-reconciliation model (Req 2, AC-1); FTS query sanitization and malformed-query degrade added (Req 3, AC-2); meta.json compatibility restated as reader-contract, not byte equality (Req 7, AC-4); retrieval eval pinned to a fixed recorded query set (Req 5). | Prepare-council synthesis in wave record Review Checkpoints. |
| 2026-07-05 | Added secret-posture control (Req 11, AC-8) after operator raised the FTS-stores-a-second-copy-of-chunk-text question: inherited Lance posture stated as a tested assertion (gitignored residency, packaging exclusion, no new secret source). Old AC-8 verification gate renumbered to AC-9. | `indexer.py` build-time secrets scan; `wave_close` secrets gate; build_pack source-only packaging. |
| 2026-07-05 | Added FTS5 segment maintenance (Req 12, AC-9) after operator asked whether SQLite needs Lance-style maintenance: FTS `optimize`/`merge` contributed into the unified `wave_index_optimize` path that `1rq4h` extends, threshold-gated in-build merge mirroring `LANCEDB_COMPACT_THRESHOLD`. Verification gate renumbered to AC-10. | FTS5 `'optimize'`/`'merge'` segment-merge semantics; `_optimize_lance_table` / `LANCEDB_COMPACT_THRESHOLD` precedent; `1rq4h` Req 10 unified maintenance verb. |
| 2026-07-05 | Added FTS5 integrity-check (Req 13, AC-10) after operator asked about corruption verification: FTS `integrity-check` + chunk-set fingerprint contributed into the shared `1rq4h` integrity probe (Req 11), routing a bad FTS table to rebuild-from-Lance. Verification gate renumbered to AC-11. | FTS5 `'integrity-check'` command; `1rq4h` Req 11 two-layer integrity probe; ordered-consistency chunk-set fingerprint (Req 2). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-04 | Lexical layer via SQLite FTS5 in the index-state store, fused pre-rerank in `search_combined`. | Real BM25 with zero new dependencies in a store this wave already ships; the rerank-first architecture already normalizes mixed candidate sources, so fusion is one fetch + pool merge. | **Lexical inside LanceDB:** weakness — no BM25; hand-rolled term scoring bolted onto a vector store, poor fit and high maintenance. **External lexical engine (tantivy/whoosh):** weakness — new dependency and index lifecycle for capability FTS5 already provides. **Grep-at-query-time fusion:** weakness — unranked, unbounded latency on large repos, no incremental index to score against. |
| 2026-07-04 | `meta.json` becomes an exported snapshot generated from the store; readers migrate in a later change, not here. | Shifts the working store without breaking a single consumer; byte-compatibility is testable; risk is contained to the writer side where the differential/compat harnesses live. | **Migrate readers now:** weakness — multiplies blast radius across dashboard/status/drift consumers in the same change that changes the writer. **Keep meta.json as working store and add SQLite beside it:** weakness — two writable sources of truth for the same state, the exact divergence this wave exists to avoid. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| FTS5 absent in some field interpreters | One-time probe with recorded capability; vector-only degrade is a first-class tested path, not an error. |
| Lexical fusion degrades precision on non-weak queries | Pre-rerank merge lets the cross-encoder arbitrate; evaluation gate (AC-3) before default-on; kill switch always available. |
| Snapshot drifts from store state under crash mid-build | Snapshot is generated inside the same build completion path that today writes meta.json; store transactions + derived-only rule make any mismatch a rebuild, not corruption. |
| Registry equivalence audit misses an edge and weakens drift detection | Differential harness includes drift/eligibility fixtures; non-equivalent cases keep the Lance-read path (AC-5 explicitly allows partial adoption). |
| Scope creep through the "other internals" list | Audit-and-adopt with mandatory per-item disposition and timing evidence; the list is bounded in this doc, not open-ended. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
