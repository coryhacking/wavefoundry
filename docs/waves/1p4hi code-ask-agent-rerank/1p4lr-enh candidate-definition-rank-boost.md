# Candidate-Side Definition/Constant Rank Boost

Change ID: `1p4lr-enh candidate-definition-rank-boost`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-11
Wave: `1p4hi code-ask-agent-rerank`

## Rationale

`1p4hj`'s AC-10 gate surfaced one query class where agent-mode loses to the cross-encoder: **"what value / model / flag is X"** questions whose answer is a short *constant/definition declaration* the query does not name. Concretely, `code_ask("what cross-encoder reranker model does local mode use?")` ranked the literal `RERANKER_MODEL = "BAAI/bge-reranker-base"` at **rank 11** (local cross-encoder: rank 3). Root cause: a short declaration chunk has little text surface, so raw `bge-small` cosine ranks it *below* verbose chunks that merely *discuss* the topic — and because the query is natural language and never names `RERANKER_MODEL`, the existing query-side symbol injection / `definition_boosted` never fires.

The cross-encoder handles this because it judges query→document relevance directly; agent-mode can't lean on that (it skips the cross-encoder by design). A **candidate-side** boost — recognizing that a candidate *is* a declaration whose declared name matches the query's terms — restores the signal in the cosine path without reintroducing the cross-encoder. This is the query-layer lever; the complementary structural fix (constant nodes + reference edges in the graph) is the sibling change `1p4ls` (sequenced before `1p4hu`).

## Requirements

1. **Candidate-side definition/constant boost (agent mode):** in `search_combined`'s agent branch, before per-index selection, multiply the cosine `score` of *declaration* candidates whose declared-name tokens strongly overlap the query's content terms by a bounded, tunable factor `CONST_DEFINITION_BOOST`.
2. **Multi-language declaration detection:** detect, from a candidate chunk's defining line(s), constant/variable assignments (`NAME = …`), function/method definitions, and class/type/interface/enum declarations, for at least Python, JS/TS, and Go, and extract the declared name. Conservative patterns; **fail-open** (no boost) on no match.
3. **Strict name↔query match:** split the declared name on snake_case/camelCase boundaries and lowercase (`RERANKER_MODEL` → `{reranker, model}`); the boost fires **only** when the name has **≥2 tokens AND all of them appear in the query's content terms** (stopwords removed). The strict-subset rule prevents over-boosting on common single-word names (`data`, `config`).
4. **Bounded + tunable + gated:** the boost is a single multiplier (`CONST_DEFINITION_BOOST`, small — order 1.25–1.4), applied to the score the relevance drop-off / per-index floor / budget operate on, so a matching short declaration surfaces *alongside* verbose chunks without distorting the rest of the order. The default value is set by the AC-5 value gate.
5. **Agent-mode only:** the cosine path is where short declarations under-rank. `"local"` (cross-encoder) already ranks declarations well and is unchanged. `rrf_fallback` (rank-based) is out of scope.

## Scope

**Problem statement:** Agent-mode (raw `bge-small` cosine) under-ranks short constant/definition declarations for natural-language "what value/model/flag is X" queries that don't name the symbol — the one query class where `1p4hj` AC-10 measured agent losing to the cross-encoder (rank 11 vs 3).

**In scope:**

- A `_definition_match_boost` helper (declaration detection + name extraction + tokenization + strict query-term overlap) and the `CONST_DEFINITION_BOOST` constant in `server_impl.py`.
- Applying the boost in `search_combined`'s **agent branch**, before `_agent_candidate_select`, on the candidate `score`.
- Per-language declaration patterns: Python (const `NAME =`, `def`, `class`), JS/TS (`const`/`let`/`var`/`function`/`class`/`interface`/`type`/`enum`), Go (`const`/`func`/`type`).
- Unit tests (per-language detection, strict-match boundaries, bounded interaction with drop-off/floor) + an AC-5 value eval on the `1p4hj` AC-10 query set plus the `RERANKER_MODEL` query.

**Out of scope:**

- The structural graph fix (constant nodes + reference edges) — that is `1p4ls`.
- Changing `"local"` / `rrf_fallback` ranking.
- Re-deriving the cross-encoder or any query-side symbol injection change (the existing `definition_boosted` is untouched).

## Acceptance Criteria

- [x] AC-1: **Boost applied in agent mode.** A short constant-declaration candidate (`NAME = …`) whose declared-name tokens are all present in the query ranks **above** a longer non-declaration candidate with a slightly higher raw cosine, after the boost — in agent mode. Verified by a unit test asserting the post-boost order.
- [x] AC-2: **Strict match only.** The boost does NOT fire when the declared name has <2 tokens, when not all name tokens appear in the query, or when the candidate is not a declaration. Verified by no-boost unit tests (single-token name; partial overlap; non-declaration chunk).
- [x] AC-3: **Bounded + composes with selection.** The applied factor never exceeds `CONST_DEFINITION_BOOST`; the per-index floor, relevance drop-off, and text budget still hold (a boosted declaration can enter the set but does not bypass the floor or breach the budget). Verified by a unit test.
- [x] AC-4: **Multi-language detection.** `_definition_match_boost` (generalized from the constant-only boost) detects + name-extracts any DEFINITION chunk — a constant (1p4mf `[const]` marker) OR a `kind="code"` chunk whose `path::Qname` id / `stem > Qname` breadcrumb is a declared symbol (function/method, class/interface/type/enum). Detection is **language-agnostic** (the chunker emits this shape for every chunked language) + the camel/snake tokenizer + camel-split query terms (`_query_content_terms`) make camelCase/PascalCase names match. Imports/summaries/dunder pseudo-symbols excluded. Verified by `RerankerTests.test_lr_definition_boost_fires_on_function_class_method` (Python def/class/method), `test_lr_definition_boost_multilanguage` (JS const, Go func, Java class), and `test_lr_definition_boost_skips_non_definition_and_strict_misses` (doc/imports/partial/single-token no-boost).
- [x] AC-5 (**VALUE GATE — gates the change**) — **PASS (11/11; `RERANKER_MODEL` 14→1, zero symbol-query regression)**: on the `1p4hj` AC-10 known-answer query set **plus** the `RERANKER_MODEL` "what model" query, the boost **raises the target declaration's rank for the "what value/model is X" class** (e.g. `RERANKER_MODEL` moves materially toward the top) **without regressing any other query's answer rank** (no known answer drops out of the returned set or falls in rank beyond a small tolerance). Recorded in the Progress Log with before/after ranks. If it cannot lift the target class without regressing others, the boost does not ship.
- [x] AC-6: Code comments document `_definition_match_boost` + the `DEFINITION_MATCH_BOOST` tunable + the strict-match rationale (over-boost guard). `docs/specs/mcp-tool-surface.md`'s `code_ask` entry notes the definition-match boost behavior; the boost only nudges fill order (no distinct response field — the agent re-ranks regardless), stated explicitly. docs-lint green.

## Tasks

- [x] Add `CONST_DEFINITION_BOOST` constant + `_definition_match_boost(query, candidate)` helper (declaration detect → name extract → tokenize → strict overlap → factor) in `server_impl.py`.
- [x] Apply the boost on candidate `score` in `search_combined`'s agent branch (before `_agent_candidate_select`, alongside the navigational weight / demotion logic).
- [x] Per-language declaration patterns (Python/JS-TS/Go) with fail-open behavior.
- [x] Unit tests: AC-1–AC-4.
- [x] AC-5 value eval (reuse the `1p4hj` AC-10 recall harness): before/after ranks across the known-answer set + the `RERANKER_MODEL` query; record and set `CONST_DEFINITION_BOOST`.
- [x] Run framework tests + docs-lint; reload MCP; live smoke on the `RERANKER_MODEL` query.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| boost-helper + constant | Engineering | — | `_definition_match_boost`, patterns, tokenization |
| wire-into-agent-branch | Engineering | boost-helper | apply on `score` before selection; shared-file with `1p4hj`/`1p4hu` |
| tests + AC-5 value eval | Engineering | wire-into-agent-branch | per-language + value gate |


## Serialization Points

- **`server_impl.py` `search_combined` agent branch** — shared with `1p4hj` (landed) and `1p4hu` (planned). This change adds a pre-selection score pass; `1p4hu` adds a candidate source. Land `1p4lr` before `1p4hu` so the graph-signal candidates also benefit from / coexist with the boost. Coordinate the one agent-branch region.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` (the `code_ask` retrieval/ranking description) — a one-line note that agent-mode applies a candidate-side definition boost. No layering/boundary change. Otherwise N/A.

## AC Priority


| AC   | Priority      | Rationale |
| ---- | ------------- | --------- |
| AC-1 | required      | Core behavior — the candidate-side boost must apply in agent mode. |
| AC-2 | required      | The strict-match guard (≥2 tokens, all-in-query) is what prevents over-boosting — safety-critical. |
| AC-3 | required      | The boost must not break the per-index floor / relevance drop-off / text-budget invariants. |
| AC-4 | important     | Python is required; JS/TS + Go broaden coverage but Python alone demonstrates + gates the mechanism. |
| AC-5 | required      | The value gate — the boost does NOT ship if it regresses any other query's answer rank. |
| AC-6 | nice-to-have  | Doc/comment note; only if the boost is observable in the response contract (else N/A). |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-10 | **Delivery-review fix (C1+C3): the generalized boost was INERT on real chunks — now it actually fires.** The adversarial council found the prior row's claim "the function now boosts too" was FALSE on the live index: (C1) an oversized symbol is split into chunks whose id carries a `:L<start>-L<end>` suffix and breadcrumb ` (part N/M)` tail, injecting junk tokens (`l1274`, `part`) that can never match a query → the all-tokens gate always failed → the boost was dead for EVERY large symbol (incl. `WaveIndex.search_combined`); (C2) consequently the boost fired on **0** candidates for the marquee queries — it ranked them on raw cosine. **Fix:** `_definition_qname` now strips the `:L…` / `(part N/M)` suffixes (C1); `_definition_match_boost` now matches on the **leaf name** (≥2 tokens) when the qualified-name match misses, so a natural-language method query (`how does search_combined work`) that names only the method boosts (C3) — a single-token leaf still needs its class. **Live-verified:** instrumented `_definition_match_boost` now FIRES on `server_impl.py::WaveIndex.search_combined:L1283-L1298` for both `how does search_combined work` and `where is search_combined defined?` (was 0 before); `what reranker model is used` → `RERANKER_MODEL`. AC-5 recall eval **11/11 PASS** (search_combined rank 1; no regression). +2 boost tests (`..._strips_split_chunk_suffix`, `..._fires_on_leaf_method_query`); suite 3097 green. **Residual (documented):** a single-token-leaf method (`Config.connect`) without its class named, and a broad compound-symbol query, are bounded-narrow (pool-gated) — not fixed here. | `server_impl.py` (`_definition_qname` suffix-strip; `_definition_match_boost` leaf-or-qualified match); `tests/test_server_tools.py` (+2 RerankerTests); live probe `/tmp/probe_boost_live.py`; `tests/eval/run_recall_eval.py` 11/11. |
| 2026-06-10 | **AC-4 + AC-6 closed — boost GENERALIZED const → all definitions (operator directive); 1p4lr now `implemented`.** _(Superseded in part by the delivery-review row above — the "function now boosts too" claim here was aspirational and only became true after the C1+C3 fix.)_ `_const_definition_boost`→`_definition_match_boost` (+ `_definition_qname`): detects a constant (1p4mf `[const]`) OR any `kind="code"` definition chunk (function/method/class/interface/type/enum) by its `path::Qname` id / `stem > Qname` breadcrumb, excluding imports/summaries/dunders; same strict ≥2-token all-in-query gate. `_query_content_terms` now camel-splits so camelCase/PascalCase symbol names match; `CONST_DEFINITION_BOOST`→`DEFINITION_MATCH_BOOST`. **AC-5 value gate RE-RUN: 11/11 PASS, no regression** (the 6 symbol-recall queries hold — "where is search_combined defined?" rank 1, the function now boosts too; all 5 constant queries pass). +2 boost tests (def/class/method + multi-language); full framework suite 3091 green. AC-6: `_definition_match_boost` documented + `mcp-tool-surface.md` note. | `server_impl.py` (`_definition_match_boost`/`_definition_qname` + `_query_content_terms` camel-split + `DEFINITION_MATCH_BOOST`); `tests/test_server_tools.py` (RerankerTests); `docs/specs/mcp-tool-surface.md`. |
| 2026-06-10 | Scoped from the `1p4hj` AC-10 finding (`RERANKER_MODEL` rank 11 vs local 3). Candidate-side boost on declaration chunks whose name tokens match the query — the query-layer lever for the "what value/model is X" class. Sibling structural change `1p4ls` (graph constants). | `1p4hj` AC-10 verdict (`wf_0e43fa6a-7ae`); [[project-mcp-code-tool-quality-log]] session 8. |
| 2026-06-10 | **Prepare-council BLOCKER (VERIFIED) — design is mis-targeted; AWAITING operator direction.** `chunk_python` (chunker.py:457,484-492) emits chunks ONLY for func/class/docstring — module-level constants like `RERANKER_MODEL = "BAAI/bge-reranker-base"` are NEVER chunked. Verified live: the motivating query returns `_get_reranker`/`_warm_reranker`/`_indexer_reranker_model` function bodies + tests; NO declaration chunk; the value literal `bge-reranker-base` appears only in a TEST chunk. So a candidate-side "this chunk IS a declaration" boost has nothing to fire on for Python/Go (only JS/TS `export const` is chunked as a top-level declaration) — **`1p4lr` as scoped cannot move its own motivating query; `1p4ls` (structural constant node, value captured) is the real fix.** Second must-fix: top_w cutoff inflation — a boost that becomes the new max raises the 0.85×top drop-off bar for ALL candidates and can re-trim relevant answers; compute the cutoff from the UN-boosted top. Options pending operator: (a) re-scope to declaration-LINES-within-a-chunk (JS/TS export-const + in-body) with AC-5 gated on a query it can actually move; (b) drop `1p4lr` in favor of `1p4ls`+`1p4hu`. | prepare-council `wf_c657bb0e-791` (moderator-verified); `/tmp/verify_blocker.py` live top-12. |
| 2026-06-10 | **UN-BLOCKED — REVIVED by `1p4mf`** (operator decided to chunk constants). The blocker (no constant chunk to fire on) is resolved upstream: `1p4mf` emits module-level `UPPER_SNAKE` constants as chunks, so `1p4lr`'s **original "candidate IS a declaration chunk" design now has a real target** — the `declaration-line-within-chunk` workaround is unnecessary; the Requirements stand as written (they assumed declaration chunks exist, which `1p4mf` now provides). Coupling: a bare `NAME = value` chunk is the short/low-context rank-11 shape that still under-ranks, so `1p4mf` makes the constant *retrievable* and `1p4lr` makes it *rank* — ship **coupled**, and run `1p4lr`'s **AC-5 value gate AFTER `1p4mf` lands** (against real constant chunks). Still-open must-fix from the council: **top_w cutoff inflation** — compute the drop-off cutoff from the UN-boosted top score so a boosted declaration does not raise the 0.85×top bar for other candidates (add an AC-3 sub-assertion: the boost only adds/raises the declaration, doesn't change which OTHERS are selected). Sequence: `1p4mf` → `1p4lr`. | feasibility workflow `wf_3440c624-5f9`; sibling `1p4mf`. |
| 2026-06-10 | **IMPLEMENTED + value-gated (11/11).** Candidate-side constant boost in `search_combined`'s agent branch: `_const_definition_boost` fires when a candidate is a constant-declaration chunk (`1p4mf`'s `" [const]"` section marker) AND its declared-name tokens (snake/camel-split, ≥2) ALL appear in the query content terms (function-word stopwords removed) → bounded `CONST_DEFINITION_BOOST`=1.3 stored as `_boost`. `_agent_candidate_select` applies it to the fill ORDER (`_wscore`) but computes the drop-off cutoff from `_wscore_base` (UN-boosted top) — so a boosted declaration ranks in WITHOUT raising the bar for / re-trimming others (the council top_w must-fix). Marker-based detection is **language-agnostic** (no per-language regex; the camel/snake tokenizer is casing-agnostic). **AC-10 recall eval: 11/11 — `RERANKER_MODEL` lifted rank 14→1; all 6 symbol queries still pass (no re-trim).** 4 new `RerankerTests` (fires / skips-non-decl / strict-partial+single-token / no-re-trim invariant); RerankerTests 95 green. **AC-1/AC-2/AC-3/AC-5 satisfied.** | `server_impl.py` (`CONST_DEFINITION_BOOST`+`_QUERY_STOPWORDS`, `_tokenize_identifier`/`_query_content_terms`/`_const_definition_boost`, agent-branch boost, `_agent_candidate_select` `_wscore`/`_wscore_base`/un-boosted cutoff); `tests/test_server_tools.py` (+4); `tests/eval/run_recall_eval.py` 11/11. |
| 2026-06-10 | **Per-language scoping correction (`wf_46ef0708-bc6`) confirmed COMPATIBLE.** The boost KEY is casing-agnostic — Req-3 splits on snake AND camel (`MaxRetries`→{max,retries}, `apiURL`→{api,url}, `StatusOK`→{status,ok}), so the broader **non-`UPPER_SNAKE`** constant set `1p4mf` now chunks is fully boostable (in fact MORE valid targets). Req-2 declaration detection must stay **keyword/structure-based + fail-open** — do NOT re-impose `UPPER_SNAKE` on the candidate line, so it matches the same set `1p4mf` chunks. Accepted limitation: genuinely single-token constants (`timeout`, `Version`) won't fire the ≥2-token boost (the intended precision guard — they stay retrievable via the `1p4mf` chunk + `1p4ls` node, just un-boosted). Implementation check: confirm the camel-splitter splits trailing/embedded acronyms (URL/OK/API) into usable tokens. | per-language workflow `wf_46ef0708-bc6`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-10 | **Candidate-side** boost (on the chunk), not query-side. | The existing symbol injection requires the query to NAME the symbol; "what model is X" never does. Firing on declared-name↔query-term overlap catches the natural-language case. | Query-side only (rejected — doesn't fire when the query doesn't name the symbol, which is the whole failure). |
| 2026-06-10 | **Strict subset match** (name ≥2 tokens, all in query). | A single common token (`data`, `config`) would over-boost unrelated declarations on most queries. Requiring the full multi-token name to appear keeps it precise. | Any-token overlap (rejected — over-boosts); embedding similarity of name vs query (rejected — adds a model call + tuning for marginal gain). |
| 2026-06-10 | **Bounded multiplier + AC-5 regression gate; agent-mode only.** | A relevance nudge, not an override; must not regress the other queries (the cross-encoder is the escape hatch if it can't). `"local"` already ranks declarations well. | Unbounded/large boost (rejected — distorts order); apply to local too (rejected — cross-encoder already handles it). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Over-boosting distorts ranking for queries that mention a declaration's name terms but want something else | Strict subset match (≥2 tokens, all-in-query) + bounded multiplier + **AC-5 regression gate** (no other answer regresses) |
| Multi-language declaration regex fragility / false matches | Conservative per-language patterns; per-language tests; **fail-open** (no boost) on no match |
| Interaction with drop-off/floor/budget (a boost pushes a marginal chunk in) | Boost is bounded and applied to the same score the floor/drop-off use; AC-3 asserts the selection invariants still hold |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
