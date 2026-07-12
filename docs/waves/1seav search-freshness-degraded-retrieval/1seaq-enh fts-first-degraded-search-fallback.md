# FTS-First Degraded Search: Serve Lexical Results When the Semantic Path Is Unavailable

Change ID: `1seaq-enh fts-first-degraded-search-fallback`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-12
Wave: `1seav search-freshness-degraded-retrieval`

## Rationale

External code review (2026-07-12), validated against `2952df8f`. Two related gaps, both predating the FTS5 lexical layer becoming trustworthy (1sbfk backfill repair) and always-fresh (1sc7c per-layer detection):

1. **`code_search` errors instead of degrading:** `search_code` embeds the query FIRST (`server_impl.py` ~1670: `self._embed_query(query, CODE_MODEL)`); when the embedding model is unavailable (offline, uncached, provider failure) the tool returns an error — while a fully-populated, coverage-verified `fts_code` table sits unused. The lexical half already exists inside the hybrid path; it is simply unreachable when the semantic half throws.
2. **`docs_search`'s fallback predates the FTS layer:** it falls back to `_live_docs_chunks` (~766), which walks and re-chunks the ENTIRE docs corpus on every call (its own docstring: "not suitable for the search hot path in large repos") and drops the requested tag filter (~836). `fts_docs` (18k+ rows on this repo) is the obvious modern fallback.

Also folds in the valid kernel of the review's exception-handling finding: callers cannot distinguish a genuine zero-hit from infrastructure failure — a typed degradation contract fixes that without abandoning the house fail-soft posture.

## Requirements

1. **FTS-first degraded fallback for `code_search`:** when query embedding is unavailable, serve BM25 results from `fts_code` (the `code_lexical` machinery), preserving `kind` (in-query), `language` (row-carried post-filter), `max_per_file`, and `tags` semantics; the response is `status: ok` with degraded-mode signals, never an error, whenever the derived store can serve.
2. **FTS-first degraded fallback for `docs_search`:** replace the per-call live walk with `fts_docs`, preserving the tag filter; the live filesystem walk remains ONLY as the last resort when the derived store is absent/corrupt (fresh clone before first build), and says so.
3. **Typed degradation contract, uniform across `docs_search`/`code_search`/`code_ask`:** `search_mode` (`semantic` | `hybrid` | `lexical_fallback` | `live_fallback`), `fallback_reason` (`model_unavailable` | `index_missing` | `store_absent` | `query_failed` | none), plus coverage status (reuse the 1sbfj `chunk_index` compare) and recovery guidance in a diagnostic. Fail-soft posture unchanged — degraded results flow, but the reason is in-band and persisted where the store log applies.
4. **`code_ask` degrades too (plan-review addition):** when query embedding is unavailable, `code_ask` constructs its citations from FTS docs+code results (the same serving path) rather than returning empty results with a generic gap — the current behavior (`server_impl.py` ~17322: all search exceptions collapse to "search index unavailable") is replaced by the typed contract. The `answer` pointer and confidence semantics reflect the degraded mode (confidence capped, `search_mode: lexical_fallback`).
5. **Tool-docstring contract parity (council amendment):** the `docs_search`/`code_search`/`code_ask` registration docstrings carry the new `search_mode`/`fallback_reason` (and three-state `index_freshness`) wording in the same change — docstrings are public contract.
6. **Zero-hit honesty:** a lexical-fallback zero-hit response carries the token-semantics note (compound identifiers, `code_pattern`/`code_keyword` routing) mirroring `code_lexical`.
7. **Regression tests:** model-unavailable → lexical results with preserved filters (both tools); store-absent → live fallback (docs) / structured unavailable (code); tag/kind/language/max_per_file preservation fixtures; contract-field assertions; a pin that the live walk is NOT reachable while the store is healthy.

## Scope

**Problem statement:** semantic-path failure currently disables search entirely (`code_search`) or triggers a corpus re-chunk with silently narrowed filters (`docs_search`), despite a trustworthy lexical layer built for exactly this.

**In scope:** `server_impl.py` search paths + response envelopes; tests; spec/seed-211 wording for the degradation contract.
**Out of scope:** ranking changes (wave `1seas`/`1sear` territory); correlation IDs (rejected — enterprise machinery a local tool doesn't need); the staleness monitor's None→not-stale posture (deliberate, documented).

## Acceptance Criteria

- [ ] AC-1: With the embedder patched unavailable, `code_search` returns BM25 results from `fts_code` (`search_mode: lexical_fallback`, `fallback_reason: model_unavailable`) with `kind`/`language`/`max_per_file`/`tags` semantics preserved — fixture-pinned.
- [ ] AC-2: With the embedder patched unavailable, `docs_search` serves from `fts_docs` with the tag filter preserved; the live walk fires only when the derived store is absent (both fixture-pinned).
- [ ] AC-3: `docs_search`/`code_search`/`code_ask` responses carry the uniform `search_mode` + `fallback_reason` contract in every mode (semantic path included: `search_mode: semantic|hybrid`, `fallback_reason` absent/none).
- [ ] AC-4: Degraded zero-hit responses are distinguishable from healthy zero-hits (typed reason + coverage block + note) — fixture-pinned.
- [ ] AC-6: With the embedder patched unavailable, `code_ask` returns FTS-built citations (`search_mode: lexical_fallback`, confidence capped) instead of empty results + a generic gap — fixture-pinned.
- [ ] AC-5: Full suite bytecode-free + docs validation; spec + seed-211 document the contract; live probe on this repo with the embedder disabled serves real lexical results.

## Tasks

- [ ] Extract the shared FTS-serving path (from `code_lexical_response`) for reuse by both search tools' fallbacks.
- [ ] `code_search`: catch embed-unavailable → lexical fallback with filter preservation.
- [ ] `docs_search`: FTS-first fallback; demote the live walk to store-absent-only.
- [ ] Uniform envelope fields across the three tools; zero-hit note.
- [ ] Fixtures per AC-1..4; live disabled-embedder probe; suite + validate; spec/seed updates.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| code-fallback | implementer | — | Embed-catch + FTS serve |
| docs-fallback | implementer | — | FTS-first, walk demoted |
| contract-tests-docs | qa-reviewer | both | Envelope + fixtures + spec |


## Serialization Points

- Shares `server_impl.py` envelope territory with `1sbxq` (same wave): land the envelope field names once, together.

## Affected Architecture Docs

- `docs/specs/mcp-tool-surface.md` (search tool contracts); `docs/architecture/search-architecture.md` (degradation ladder); seed-211 (fallback interpretation). `data-and-control-flow.md` Path 6 search notes.

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The review's core finding: usable search disabled by a missing model. |
| AC-2 | required | Per-call corpus re-chunk + silent filter loss. |
| AC-3 | required | Zero-hit vs infrastructure-failure distinguishability. |
| AC-4 | required | Same honesty rule as `code_lexical`'s zero-hit note. |
| AC-5 | required | Standard gate + live proof. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-12 | Plan-review revision (external, validated): `code_ask` was envelope-only in the original plan — inconsistent with the wave objective; Requirement 4 + AC-6 now require FTS-built citations on model-unavailable (replacing the ~17322 generic-gap collapse). Council amendment added Requirement 5 (docstring contract parity). | Plan review; `code_ask` exception-collapse source read. |
| 2026-07-12 | Drafted from the external code review (P1 degraded-search + the valid kernel of P1 exception-typing), validated against `2952df8f`: embed-first at ~1670 (error path ~4411), `_live_docs_chunks` per-call walk at ~766 with its own hot-path warning, tag-filter loss at ~836. Enabled by 1sbfk (FTS trustworthy) + 1sc7c (FTS fresh) + `code_lexical` (the serving machinery already exists). Correlation IDs explicitly rejected during validation. | Review report; source reads; `code_lexical_response` as the reusable serving path. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-12 | Degrade FTS-first; live filesystem walk only when the derived store is absent/corrupt. | The FTS layer is now coverage-verified, always-fresh, and serves in milliseconds; the live walk is O(corpus) per call and loses filters. | **Keep walk-first:** the status quo the review flagged. **Remove the walk entirely:** breaks the fresh-clone-before-first-build case docs_search legitimately serves today. |
| 2026-07-12 | Typed `search_mode`/`fallback_reason`, NOT correlation IDs or a failure-taxonomy framework. | The need is distinguishing zero-hit from infrastructure failure in-band; two fields + existing store-log persistence achieve it inside the fail-soft posture. | **Correlation IDs + typed exception hierarchy:** machinery without a consumer in a local stdio tool. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Lexical-only results mislead agents expecting semantic recall | `search_mode` is explicit, seed-211 documents interpretation, and the zero-hit note routes to alternatives. |
| Envelope field additions break response-shape pins | Additive fields only; existing tests updated in the same change. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
