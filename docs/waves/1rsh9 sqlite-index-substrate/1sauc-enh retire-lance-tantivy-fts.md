# Retire the Lance/Tantivy FTS — code_search Lexical Half Moves to the FTS5 Layer

Change ID: `1sauc-enh retire-lance-tantivy-fts`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-11
Wave: `1rsh9 sqlite-index-substrate`

## Rationale

Operator-directed late admission into wave `1rsh9` (2026-07-11), rolling a follow-up discovered during the wave's delivery Q&A into the wave itself so the lexical-retrieval story ships coherent.

With the FTS5 lexical layer landed (`1rrr0`), the repository carries **two** lexical engines. Verification of the old one's consumers found:

- The **docs-table** Lance/Tantivy FTS has **zero query-path consumers** — `docs_search`'s lexical fallback is token-overlap over live chunks, and `_lance_fts_search` has exactly one call site, scoped to the code table. Yet the docs FTS is rebuilt **whole** (`create_fts_index(replace=True)`) on every changed docs build, and it produced the measured `_indices/` version leak: **83 MB across 18 stale copies** on this repo (superseded Tantivy copies cannot be GC'd by the fragment-gated optimize), the single largest waste in the index directory and the class the `1rycf` close-time optimize was band-aiding.
- The **code-table** Lance FTS backs one consumer: `search_code`'s hybrid dense+FTS RRF merge (wave 12pn3). The FTS5 layer is a strict upgrade for that role: identifier-preserving tokenizer (`unicode61 tokenchars '_'` vs Tantivy's `simple`, which fragments `SORT_WINDOW_SIZE` into noise tokens), incrementally maintained per-chunk deltas (never a whole-index rebuild), no version accumulation, and one maintenance/integrity surface (`wave_index_optimize` + the shared probe) instead of the leak-prone Tantivy lifecycle.

Retiring Tantivy entirely removes the rebuild cost from every build, removes the `_indices/` FTS-bloat class at its source, and leaves ONE lexical engine with one set of semantics.

## Requirements

1. **Stop building the Lance FTS for both tables:** remove `_create_fts_index` and all call sites (`_StreamingLayerWriter`, `_compact_by_rewrite`, incremental create-table branch, incremental post-change rebuild). No Lance FTS index is created or refreshed anywhere.
2. **`search_code`'s lexical half moves to the FTS5 layer:** `_lance_fts_search` is replaced by an FTS5-backed candidate fetch over `fts_code` that preserves the existing hybrid contract — candidates enter the same per-layer dense+FTS RRF merge, best-first, shaped like `_lance_search` output. `docs_search` is untouched (its lexical fallback never used Lance FTS).
3. **Filter parity:** `search_code`'s `language`, `kind`, and `tags` filters apply to the FTS5 half with the same semantics as the Lance `where` clause they replace. The FTS tables gain `language` and `tags` UNINDEXED columns to support this (populated from the same chunk rows).
4. **Store schema version bump (sequenced):** the FTS column addition bumps `STATE_STORE_SCHEMA_VERSION` `"3"` → `"4"` — the whole-store drop-and-rebuild converges existing stores (derived-only; the reconcile backfills). No migration code.
5. **Legacy index cleanup (field migration):** the reclaim path (`reclaim_lance_table`, which runs via `wave_index_optimize` on demand and automatically at setup/upgrade) drops any existing Lance FTS index (`drop_index`) and reclaims its `_indices/` versions, so field repos shed the legacy Tantivy artifacts on their first upgrade without manual steps.
6. **Query safety unchanged:** FTS5-hostile queries degrade the lexical half to empty (dense-only hybrid) with no error; the FTS-absent/FTS5-unavailable store degrades the same way — `search_code` must never error because the lexical half is missing.
7. **Behavior gate:** the `code_search` weak-pattern evaluation (before/after on the recorded query set) must show no regression; results recorded in this doc.

## Scope

**Problem statement:** Two lexical engines coexist; the older one is consumer-less on the docs table (pure build cost + an un-GC-able 83 MB version leak) and inferior on the code table (whole rebuilds, identifier-fragmenting tokenizer), while its replacement already ships in the same wave.

**In scope:**

- `indexer.py`: remove `_create_fts_index` + call sites; legacy FTS `drop_index` cleanup in the reclaim path.
- `index_state_store.py`: `language`/`tags` UNINDEXED columns on `fts_docs`/`fts_code`; schema version 3→4; filtered `fts_search` variant for the code_search contract.
- `server_impl.py`: `_lance_fts_search` → FTS5-backed lexical fetch in `search_code`'s hybrid merge, filter parity included.
- Tests: removal wiring locks, filter parity, degrade paths, legacy-cleanup fixture; existing FTS-creation tests updated.
- Before/after `code_search` eval on the recorded query set.

**Out of scope:**

- `docs_search` behavior (never consumed Lance FTS; token-overlap fallback unchanged).
- `code_ask` fusion (already FTS5-backed via `1rrr0`).
- `code_keyword`/`code_pattern` (live grep exactness contract, untouched).
- Removing the `1rycf` close-time bloat gate (harmless once the leak source is gone; retiring it is a separate cleanup once field data confirms).

## Acceptance Criteria

- [x] AC-1: No code path creates or refreshes a Lance FTS index — `_create_fts_index` is gone from `indexer.py` and a source-assertion test locks `create_fts_index` out of the build paths; builds and incremental updates succeed without it. — function deleted + all 4 call sites (streaming finalize, compact-by-rewrite, create-table branch, incremental rebuild + its 1p95j gating block); `test_no_lance_fts_created_anywhere` (source lock) + `test_incremental_change_creates_no_lance_fts` (live lancedb assertion after real builds).
- [x] AC-2: `search_code` hybrid results merge dense + FTS5 lexical candidates with filter parity — `language`, `kind`, and `tags` filters constrain the lexical half identically to the dense half (fixture coverage per filter), and lexically-found results surface for exact-identifier queries that dense fetch misses. — `_fts5_lexical_search` in the hybrid RRF merge (scores = −bm25, higher-better); kind exact / tags any-of inside the FTS5 query, language via the existing post-filter on row-carried `language`; `Fts5CodeSearchLexicalTests` (per-filter fixtures, shape, live language-filter parity confirmed in the eval run).
- [x] AC-3: The store schema bump (3→4) converges an existing v3 store via the standard drop-and-rebuild + reconcile backfill (fixture proves an old-schema store self-heals and serves the new columns). — `test_v3_store_converges_to_v4_via_drop_and_rebuild`; proven live on this repo (v3 store reset → reconcile backfilled 19,942 docs + 14,389 code rows). Cold-provisioning flag added so the backfill logs calmly (install/upgrade/schema-bump) while a warm-store divergence stays loud; `test_cold_flag_covers_partial_deltas_then_clears`.
- [x] AC-4: The reclaim path drops legacy Lance FTS indices and reclaims their `_indices/` versions — proven live on this repo (before/after `_indices/` sizes recorded) and by a fixture asserting `drop_index` fires when an FTS index exists. — `_drop_legacy_fts_indices` wired before the tier-1 optimize in `reclaim_lance_table`; `test_reclaim_drops_legacy_fts_indices`; LIVE: docs.lance 163→51 MB (`_indices/` 112→9.6 MB), code.lance 73→37 MB (`_indices/` 22→7.1 MB) — 148 MB reclaimed, remaining `_indices/` is pure vector index.
- [x] AC-5: FTS5-hostile queries and an absent/FTS5-less store degrade `search_code` to dense-only with no error (tests for both). — `_fts5_lexical_search` returns `[]` on every degrade path; `test_server_lexical_half_shapes_and_degrades` (hostile query + absent store).
- [x] AC-6: The before/after `code_search` evaluation on the recorded query set shows no rank regressions; results in this doc. — 10-query set: 0 improved / 0 regressed / 10 unchanged (9× rank 1, 1× rank 2 — identical to the Tantivy baseline); language=python filter returns only python rows. The engine swap is behaviorally transparent.
- [x] AC-7: Full framework tests run bytecode-free and docs validation passes. — full suite 4,818 tests OK bytecode-free (run_tests.py, 2026-07-11); `wave_validate` clean.

## Tasks

- [x] Add `language`/`tags` UNINDEXED columns to the FTS tables; bump store schema to "4"; extend `fts_search` with filter support. — done (`_row_tags` normalizer; parameterized kind/tags filters).
- [x] Remove `_create_fts_index` and all call sites from `indexer.py`. — function + 4 call sites removed.
- [x] Add legacy Lance-FTS `drop_index` + version reclaim to the reclaim path (`reclaim_lance_table`). — `_drop_legacy_fts_indices` before tier-1 optimize.
- [x] Replace `_lance_fts_search` with the FTS5-backed lexical fetch in `search_code` (filter parity, degrade paths). — `_fts5_lexical_search`.
- [x] Update/extend tests: removal locks, filter parity, schema convergence, legacy cleanup, degrade paths. — test_indexer reclaim/finalize/removal updates + `Fts5CodeSearchLexicalTests` + cold-flag tests; 290 green across affected suites.
- [x] Run the before/after `code_search` eval; record results. — 0 regressed / 10 unchanged (AC-6).
- [x] Live migration on this repo: rebuild store (v4), run `wave_index_optimize`, record `_indices/` reclaim. — v3→v4 converged; 148 MB reclaimed (AC-4 evidence).
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`. — full suite 4,818 tests OK bytecode-free (run_tests.py, 2026-07-11); `wave_validate` clean.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| fts5-columns | implementer | — | Schema v4, filtered fts_search |
| lance-fts-removal | implementer | fts5-columns | Creation call sites + legacy drop/reclaim |
| code-search-switch | implementer | fts5-columns | Hybrid lexical half → FTS5, filter parity |
| eval-and-tests | qa-reviewer | all implementation streams | Before/after eval, fixtures, suite |


## Serialization Points

- Schema v4 lands before the `search_code` switch (the new columns are its filter substrate).
- The `code_search` eval gates completion: a rank regression on the recorded query set blocks (fix or revert the switch; the kill isn't an env var here — the old path is deleted — so the eval runs BEFORE the removal is declared done).

## Affected Architecture Docs

- `docs/architecture/search-architecture.md` — one lexical engine; `search_code` hybrid now FTS5-backed; Lance FTS retired.
- `docs/architecture/current-state.md` — `_indices/` no longer carries FTS artifacts.
- ADR `1s5u9-adr` — consequences note: Tantivy retirement completes the single-lexical-engine consolidation.

## AC Priority

(Proposed; operator-directed late admission — confirmed by the in-wave readiness extension.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The retirement itself — no Lance FTS creation anywhere. |
| AC-2 | required | `code_search`'s lexical half must survive the engine swap with filter parity. |
| AC-3 | required | Existing stores must converge without migration code (derived-only discipline). |
| AC-4 | required | Field repos must shed the legacy 83 MB leak automatically at upgrade. |
| AC-5 | required | The lexical half must never make `search_code` error. |
| AC-6 | required | The behavior gate — no regression on the recorded query set. |
| AC-7 | required | Standard framework verification gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-11 | Drafted and admitted late into wave `1rsh9` by operator direction ("let's roll that into this wave"), from the delivery-Q&A finding: docs-table Lance FTS has zero consumers (only `search_code._lance_fts_search` reads Lance FTS, code table only) while producing the 83 MB `_indices/` version leak (18 stale copies; code table +15 MB/6). BEFORE `code_search` snapshot recorded on the 10-query set: 9× rank 1, 1× rank 2 (`store unreadable or corrupt`). | Consumer grep (`query_type="fts"` — one site); `_indices/` decomposition (docs: 83 MB FTS / 9 MB vector; code: 15 MB FTS / 6 MB vector); `code_search_before.json`. |
| 2026-07-11 | Implemented: Lance FTS creation removed (function + 4 call sites), `_drop_legacy_fts_indices` on the reclaim path, `search_code` lexical half switched to FTS5 (`_fts5_lexical_search`, filter parity, degrade paths), store schema v4 with `language`/`tags` columns + cold-provisioning flag. Live migration: v3 store converged via drop-and-rebuild; legacy Tantivy indices dropped on both tables; **148 MB reclaimed** (docs.lance 163→51 MB, code.lance 73→37 MB; `_indices/` now pure vector index at 9.6/7.1 MB). AFTER eval: 0 regressed / 10 unchanged vs the Tantivy baseline; language filter parity confirmed live. | `indexer.py`, `index_state_store.py`, `server_impl.py`; `test_indexer.py` reclaim/finalize updates; `Fts5CodeSearchLexicalTests`; live reclaim + eval transcripts. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-11 | Retire Tantivy fully (both tables) rather than only dropping the consumer-less docs FTS. | One lexical engine, one semantics, one maintenance/integrity surface; the FTS5 tokenizer is strictly better for the identifier queries `search_code`'s lexical half exists for; keeping code-table Tantivy keeps the whole-rebuild cost and leak class alive for half the benefit. | **Docs-only removal:** weakness — retains the rebuild cost + leak on the code table and two engines' semantics indefinitely. **Keep both:** weakness — pays double storage and build cost for a strictly-worse engine. |
| 2026-07-11 | Filter parity via `language`/`tags` UNINDEXED columns on the FTS tables (schema 3→4), not via post-join. | The columns are tiny relative to text, filtering happens in the one query, and the drop-and-rebuild version gate converges old stores for free; a registry join would add a per-query join for data the row can simply carry. | **Join registry/Lance for filters:** weakness — extra query complexity; the registry doesn't carry language/tags either. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| `code_search` quality regresses without the Tantivy half | Before/after eval on the recorded query set gates completion (AC-6); the FTS5 half is expected to be stronger on identifiers (tokenizer) and the dense half + reranker are unchanged. |
| Legacy `_indices/` versions survive the cleanup on some lancedb versions | `drop_index` + the existing tiered reclaim (rewrite path drops everything by construction); the live migration on this repo records actual reclaim (AC-4). |
| Old v3 stores error on the new columns | Version gate: unknown/older schema → whole-store drop-and-rebuild; reconcile backfills from Lance (AC-3 fixture). |
| A field repo queries mid-migration (store rebuilt, FTS empty) | Same degrade contract as FTS5-unavailable: lexical half returns empty, dense half serves; reconcile backfills at next build end. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
