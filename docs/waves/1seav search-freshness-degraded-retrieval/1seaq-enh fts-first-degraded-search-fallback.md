# FTS-First Degraded Search: Serve Lexical Results When the Semantic Path Is Unavailable

Change ID: `1seaq-enh fts-first-degraded-search-fallback`
Change Status: `implementing`
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

1. **FTS-first degraded fallback for `code_search` — inside the epoch contract:** when query embedding is unavailable AND the wave-`1sed7` epoch gate holds (the tool's single captured `(attempt_id, status, generation)` state token has `status == "complete"`, and the post-operation compare passes), serve BM25 results from `fts_code` (the `code_lexical` machinery), preserving `kind` (FTS in-query), `language` (row-carried post-filter at the shared serving path), `max_per_file` (post-group at the shared serving path), and `tags` (row-carried post-filter) semantics; the response is `status: ok` with degraded-mode signals. **FTS may serve ONLY from a captured complete epoch — mid-build/interrupted/uninitialized FTS is mixed state and is never a fallback source.** The strict code-tool lockout from `1sed7` is preserved unchanged: a non-complete epoch refuses with `index_not_ready` regardless of model availability.
2. **FTS-first degraded fallback for `docs_search` — per epoch state:** replace the per-call live walk with `fts_docs` (tag filter preserved) when the captured epoch token is complete. The live filesystem walk remains ONLY for the states where no published FTS exists, per the explicit state table in Requirement 2a, and says so.
2a. **Epoch-state behavior table (P0 repair — every state defined, per tool):**

   | Captured epoch state | `docs_search` | `code_search` / `code_ask` / `code_lexical` |
   | -------------------- | ------------- | ------------------------------------------- |
   | `complete` + model OK | semantic/hybrid | semantic/hybrid |
   | `complete` + model unavailable | FTS fallback (`lexical_fallback`, `model_unavailable`) | FTS fallback (`lexical_fallback`, `model_unavailable`) |
   | absent (no store) | live walk (`live_fallback`, `store_absent`) | refuse (`index_not_ready`) |
   | `uninitialized` | live walk (`live_fallback`, `index_not_ready`) | refuse (`index_not_ready`) |
   | `building` (stable across the operation) | live walk (`live_fallback`, `index_not_ready`) | refuse (`index_not_ready`) |
   | interrupted (`building`, no live builder) | live walk (`live_fallback`, `index_not_ready`) | refuse (`index_not_ready`) |
   | unreadable/corrupt store | live walk (`live_fallback`, `store_absent`) | refuse (`index_not_ready`) |
   | token CHANGED across the operation (any transition) | discard → `index_not_ready` error (1sed7 seqlock, unchanged) | discard → `index_not_ready` error (unchanged) |

   The single-capture token discipline from `1sed7` applies verbatim: one `_epoch_state` capture before the operation, the completeness/serve decision made on the CAPTURED token, the same token compared after. The fallback must not introduce a second read.
3. **Typed degradation contract, uniform across `docs_search`/`code_search`/`code_ask`:** `search_mode` (`semantic` | `hybrid` | `exact` | `lexical_fallback` | `live_fallback`), `fallback_reason` (ALWAYS present: `null` on the healthy path, else `model_unavailable` | `index_missing` | `store_absent` | `index_not_ready` | `query_failed`), plus coverage status (reuse the 1sbfj `chunk_index` compare) and recovery guidance in a diagnostic. `search_mode: exact` classifies `code_ask`'s existing exact-first `code_keyword` short-circuit (which returns before semantic retrieval) — it is a healthy mode, `fallback_reason: null`. The shared serving path returns a TYPED result object carrying `{available, failure_reason, results, coverage}` so a caught exception maps to `query_failed` and is distinguishable from a genuine zero-hit (`_fts5_lexical_search`'s collapse-to-`[]` is replaced at this seam). Fail-soft posture unchanged — degraded results flow where the state table allows; the reason is in-band FIRST (response diagnostic); store-log persistence is deduplicated (log once per `(tool, fallback_reason)` transition, not per query) so an outage cannot flood the bounded log.
4. **`code_ask` degrades too (plan-review addition):** when query embedding is unavailable, `code_ask` constructs its citations from FTS docs+code results (the same serving path) rather than returning empty results with a generic gap — the current behavior (`server_impl.py` ~17322: all search exceptions collapse to "search index unavailable") is replaced by the typed contract. The `answer` pointer and confidence semantics reflect the degraded mode (confidence capped, `search_mode: lexical_fallback`).
5. **Tool-docstring contract parity (council amendment):** the `docs_search`/`code_search`/`code_ask` registration docstrings carry the new `search_mode`/`fallback_reason` (and three-state `index_freshness`) wording in the same change — docstrings are public contract.
6. **Zero-hit honesty:** a lexical-fallback zero-hit response carries the token-semantics note (compound identifiers, `code_pattern`/`code_keyword` routing) mirroring `code_lexical`.
7. **Regression tests:** model-unavailable → lexical results with preserved filters (both tools); store-absent → live fallback (docs) / structured unavailable (code); tag/kind/language/max_per_file preservation fixtures — asserted independently for the FTS fallback AND the live-walk fallback; contract-field assertions; a pin that the live walk is NOT reachable while the store is healthy; **epoch-transition fixtures (P0 repair): a build fencing BEFORE the fallback query (building pre-state → per the state table), DURING it (token change → discard), and AFTER it (next query serves current) — for both docs_search's degraded path and the strict tools' refusal**; a `query_failed` fixture (injected FTS exception → typed reason, not silent zero-hit); a store-log dedup fixture (N degraded queries → one persisted event per reason transition).

## Scope

**Problem statement:** semantic-path failure currently disables search entirely (`code_search`) or triggers a corpus re-chunk with silently narrowed filters (`docs_search`), despite a trustworthy lexical layer built for exactly this.

**In scope:** `server_impl.py` search paths + response envelopes; tests; spec/seed-211 wording for the degradation contract.
**Out of scope:** ranking changes (wave `1seas`/`1sear` territory); correlation IDs (rejected — enterprise machinery a local tool doesn't need); the staleness monitor's None→not-stale posture (deliberate, documented).

## Acceptance Criteria

- [x] AC-1: With the embedder patched unavailable, `code_search` returns BM25 results from `fts_code` (`search_mode: lexical_fallback`, `fallback_reason: model_unavailable`) with `kind`/`language`/`max_per_file`/`tags` semantics preserved — fixture-pinned.
- [x] AC-2: With the embedder patched unavailable, `docs_search` serves from `fts_docs` with the tag filter preserved; the live walk fires only when the derived store is absent (both fixture-pinned).
- [x] AC-3: `docs_search`/`code_search`/`code_ask` responses carry the uniform `search_mode` + `fallback_reason` contract in every mode — `fallback_reason` is ALWAYS present (`null` on healthy paths); `code_ask`'s exact-first short-circuit is classified `search_mode: exact`; fixture-pinned across semantic, exact, lexical-fallback, and live-fallback modes.
- [x] AC-4: Degraded zero-hit responses are distinguishable from healthy zero-hits (typed reason + coverage block + note) — fixture-pinned.
- [x] AC-6: With the embedder patched unavailable, `code_ask` returns FTS-built citations (`search_mode: lexical_fallback`, confidence capped) instead of empty results + a generic gap — fixture-pinned.
- [x] AC-7: Epoch-state behavior matches the Requirement 2a table exactly — FTS never serves from a non-complete captured epoch, the strict code-tool lockout is unchanged, `index_not_ready` appears in the typed reason vocabulary, and the before/during/after build-transition fixtures pass; the shared serving path's typed result distinguishes `query_failed` from zero hits.
- [ ] AC-5: Full suite bytecode-free + docs validation; spec + seed-211 document the contract; live probe on this repo with the embedder disabled serves real lexical results.

## Tasks

- [x] Extract the shared FTS-serving path (from `code_lexical_response`) for reuse by both search tools' fallbacks — returning the typed `{available, failure_reason, results, coverage}` result and implementing the full filter contract (`kind` FTS in-query; `language`/`tags` row-carried post-filters; `max_per_file` post-group) that `code_lexical_response` alone does not carry today.
- [x] `code_search`: catch embed-unavailable → lexical fallback with filter preservation.
- [x] `docs_search`: FTS-first fallback; live walk demoted to the no-published-FTS states per the Requirement 2a table.
- [x] Uniform envelope fields across the three tools; zero-hit note.
- [x] Fixtures per AC-1..4, AC-6, and AC-7 (epoch-transition + query_failed + log-dedup); live disabled-embedder probe; spec/seed updates. (Suite + validate at wave close.)

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
| AC-6 | required | `code_ask` degrading is the wave objective applied to its highest-value consumer. |
| AC-7 | required | The 1sed7 epoch contract must not be weakened by the fallback (P0 plan repair). |
| AC-5 | required | Standard gate + live proof. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-13 | IMPLEMENTED: shared typed serving path `_fts_degraded_serve` (typed `{available, failure_reason, results, coverage}`; full filter contract — `kind` FTS in-query, `tags` any-of, `language` single-or-category post-filter, `max_per_file` post-group; epoch decisions stay with callers). All three tools rewired per the Requirement 2a state table with the CAPTURED 1sed7 token threaded from the registrations (single-capture discipline preserved — response fns take `epoch_state`, computed once only for direct callers): complete+model-unavailable → FTS (`lexical_fallback`/`model_unavailable`); complete+unservable-tables → FTS (`index_missing`); docs with no published epoch → live walk (`live_fallback`, `store_absent`/`index_not_ready` per state — its ONLY reachable states, pinned); code tools refuse on non-complete states (1sed7 lockout unchanged). `code_ask` degrades with FTS-built citations (confidence capped to low), classifies the exact-first artifact pass as `search_mode: exact`, and types generic search exceptions as `query_failed`. `fallback_reason` ALWAYS present (null healthy) across all three envelopes; lexical zero-hits carry the token-semantics note; degradation persists to the store log once per `(tool, reason)` transition with a recovery event (fixture-proven: 5 queries → 1 event, recovery → 2nd). Docstrings updated (Req 5). Fixtures: contract tests migrated to the state table + `DegradedFtsFallbackTests` (13: filter preservation per filter, epoch refusal matrix, live-walk-unreachable pin, typed query_failed, zero-hit note, code_ask citations + typed generic failure, null-reason healthy shape, before/during/after build-transition matrix, log dedup+recovery). Live disabled-embedder probe on this repo: docs/code/ask all served real BM25 results (`lexical_fallback`/`model_unavailable`, language filter honored, confidence low, freshness honestly `stale` against the uncommitted tree). Spec/seed/architecture docs updated (mcp-tool-surface degradation contract, search-architecture ladder, data-and-control-flow Path 6, seed-211 + rendered guru.md interpretation guidance). | Diffs; DegradedFtsFallbackTests 13/13; seqlock 13/13; live probe transcript. |
| 2026-07-13 | PRE-IMPLEMENTATION PLAN REVIEW (external) — P0 repair: the fallback plan predated wave `1sed7`'s reader contract and left incomplete-epoch behavior undefined (live walk was "store absent/corrupt" only; no `index_not_ready` reason; FTS serving not bound to a complete epoch). Added Requirement 2a (full per-state behavior table for absent/uninitialized/building/interrupted/unreadable/transition, per tool), bound FTS serving to the CAPTURED complete token under 1sed7's single-capture discipline, preserved the strict code-tool lockout verbatim, added `index_not_ready` + always-present `fallback_reason: null` + `search_mode: exact` (code_ask's exact-first short-circuit) to the typed contract, required the shared serving path to return a typed `{available, failure_reason, results, coverage}` result (replacing the `_fts5_lexical_search` exception collapse), made the filter contract concrete per layer with independent FTS/live-walk preservation fixtures, added AC-6 and new AC-7 to the priority table and tasks (AC-6 was missing from both), and required store-log dedup for degraded-query persistence (P2). | Plan review relay with source refs; 1sed7 reader contract (`server_impl.py` seqlock registrations). |
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
