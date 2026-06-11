# Graph-Signal Retrieval Fusion for `code_ask` (Structural Proximity as a Candidate Source)

Change ID: `1p4hu-enh graph-signal-retrieval-fusion`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-11
Wave: 1p4hi code-ask-agent-rerank

## Rationale

Embedding similarity is **blind to code structure**. A chunk that sits on the call path to the query's target, or is a high-fan-in chokepoint the change would ripple through, can be far more relevant than a lexically-similar but structurally-peripheral chunk — yet pure vector retrieval ranks them only by text similarity. The framework **already builds a code graph** (calls / imports / community / fan-in / betweenness) and `code_ask` already does a limited two-hop symbol expansion (extract symbols from the top citations, keyword-retrieve their definitions). This change blends a **structural signal** into agent-mode candidate selection — generalizing two-hop into a graph-aware candidate source — so the agent sees structurally-relevant candidates that semantic retrieval alone misses. It is the framework's real differentiator over generic vector RAG: almost no retrieval stack can answer "what breaks if I change X" by *following the call graph* rather than guessing from text.

This change **consumes** the existing graph (no builder change, no `GRAPH_BUILDER_VERSION` bump) and **extends `1p4hj`'s agent-mode candidate pipeline** — it adds a graph-derived source/lane to the per-index allocation `1p4hj` establishes. It sequences after `1p4hj`.

## Requirements

1. Agent-mode candidate selection incorporates a **graph signal**: when the query resolves to a symbol (or the top semantic hits resolve to symbols), candidates reachable by 1-hop graph edges (direct callers/callees, importers, same-community members) are surfaced — even when their embedding similarity is below the semantic cutoff.
2. The graph signal participates as a **labeled source** in the per-index allocation `1p4hj` defines (e.g. `source="graph"`), deduped against the semantic candidates — so the agent knows a candidate came from *structure*, not text, and can weigh it. (Source-lane vs. score-boost is a Decision-Log choice during implementation.)
3. **Generalize the existing two-hop** symbol expansion: the explanatory-question second hop follows **graph edges** from the resolved symbols (calls/imports), not only a keyword re-retrieval pass.
4. **Bounded:** the graph expansion is capped (max graph candidates, max hops = 1 by default) within the shared token budget; deduped; it cannot pull the whole call graph or blow the budget.
5. **Graceful fallback:** when the graph index is absent or empty (initial setup, non-code projects), agent-mode degrades to `1p4hj`'s semantic-only candidate set with no error.
6. Gated on a **quality check** (AC-5): the graph signal must surface a structurally-relevant answer that semantic retrieval missed, with no regression on lexical queries.

## Scope

**Problem statement:** semantic retrieval ranks by text similarity and is blind to the call/import/community structure the framework already indexes — so structurally-load-bearing code (callers of the changed symbol, chokepoints) is under-surfaced for exactly the questions where it matters most.

**In scope:**

- A graph-derived candidate source/boost in agent-mode candidate selection, labeled and deduped against semantic candidates.
- Generalizing the two-hop expansion to follow graph edges (calls/imports) from resolved symbols.
- Bounding (cap hops/candidates within the budget) + graceful fallback when no graph.
- A real-query quality check.
- Docstring + `mcp-tool-surface.md` notes on the graph signal + `source` label.

**Out of scope:**

- Any **graph-builder** change — this consumes the existing graph (no `GRAPH_BUILDER_VERSION` bump).
- A full learned graph+semantic ranker / weighting model — start with a bounded, labeled graph source; tuning is follow-up.
- The cross-encoder / RRF / per-index pipeline mechanics — that is `1p4hj`.
- Multi-hop (>1) traversal — 1-hop by default; deeper traversal is a follow-up if AC-5 shows value.

## Acceptance Criteria

- [x] AC-1: For a query resolving to a symbol, agent-mode returns graph-reachable structural matches in a **dedicated `graph_related` response section** (operator-directed redesign), NOT mixed into the textual `citations` with a fake 0.0 score. **Why the section:** a graph hit's *relationship* to the query symbol — `caller` / `reader` / `importer` — IS the answer to "what calls/reads X", and a 0.0-scored citation row both throws that away and buries the answer at the citation tail. The section groups matches by relationship (`callers`/`readers`/`importers`/`related`), carries a `seed`, each entry's `symbol`/`path`/`lines`/`kind`/`confidence`, and is bounded by `AGENT_GRAPH_SIGNAL_CAP`. **Semantic dedup (text, not entry):** a structural match that is ALSO a semantic citation keeps its relationship entry (the structural answer stays complete + labeled) but drops the duplicate `excerpt` and is flagged `also_cited` — the chunk text is never sent twice (matched on `(path, START line)`, the cross-source identity). Citation selection (`_agent_candidate_select`) is now purely semantic. Verified by `test_graph_related_section_groups_callers`, `test_graph_related_reader_bucket`, `test_graph_related_text_deduped_against_citations`. Live: `what calls resolve_symbol` → `callers: [callgraph, graph_impact, shortest_path]`; `what reads LANCEDB_COMPACT_THRESHOLD` → `readers: [_delete_lance_chunks, _lance_incremental_write, _update_lance_table]`.
- [x] AC-2: The expansion follows **graph edges** from the resolved symbols — `calls`, `imports`, and the 1p4ls `reads` edge — not keyword re-retrieval; `symbol_extraction_method="graph"`. **(Delivery follow-up — DIRECTION-AWARE, fixes the D1 direction-blindness):** `one_hop_neighbors` now takes a `direction`, and the signal scopes seeds + direction by query intent: a "what calls/reads/uses X" / "where is X used" question expands ONLY the named symbol with edges INTO it (`direction="in"` → callers / readers / importers), so it no longer answers a *callers* question with the seed's *callees*. "How does X work" / behavioral NL queries (no user-finding verb) expand the named symbol AND the top semantic hits, both directions (the mechanism — where the wins are). Generic words are excluded from seed resolution (a stoplist — "main"/"root" no longer mis-resolve to `server.py::main`), and test-file neighbors + whole-file `module` nodes are suppressed (poor structural answers). Verified by `test_caller_surfaced_via_calls_edge`, `test_reader_surfaced_via_reads_edge`, `test_direction_aware_what_calls_surfaces_callers_not_callees`, `test_test_file_neighbor_suppressed`.
- [x] AC-3: **Bounded** — capped at `AGENT_GRAPH_SIGNAL_CAP` (1-hop default) within the budget, deduped; never pulls an unbounded subgraph. Verified by `test_graph_signal_bounded` (a 20-reader high-fan-in symbol returns ≤cap). `one_hop_neighbors` is also called with `max_neighbors` (the 1p4ls degree bound).
- [x] AC-4: **Graceful fallback** — no graph index (absent/empty) or no resolvable symbol → the graph lane is simply absent (semantic-only) with no error. Verified by `test_no_graph_fallback` (returns `[]`).
- [x] AC-5 (quality — **gates this change**): **empirically measured + tightened (delivery follow-up).** A live **17-query sweep** across 5 classes (reads-edge, callers/callees, constant-value, behavioral, mis-resolution) — each probed graph-ON vs graph-OFF and verified against the live graph (`code_callhierarchy`/`code_references`/source) — showed the ORIGINAL signal was mostly noise (~3/14 wins, direction-blind, 2 relevant-displacement cases; the original 4-query gate set was the favorable band). After the direction-aware + seed-scoping + test/module-suppression tightening (and moving structural matches to the dedicated `graph_related` section so they can never affect citation ranking at all), the SAME sweep is **6 clean wins, 5 correct no-fires (a wrong answer became honest silence), and 2 mild behavioral cases** (displacement is now impossible — citations are pure semantic): "what calls resolve_symbol" → its 3 real callers (`callgraph`/`graph_impact`/`shortest_path`); "what calls build_index" → `main`/`on_created`/`on_deleted` (4 real callers exist — `main` + the 3 `on_*` watchdog handlers; the `cap`=3 section shows the top 3); "what reads LANCEDB_COMPACT_THRESHOLD" → its 3 reader functions; "how does the chunker split markdown" → `H3_SPLIT_THRESHOLD_CHARS`/`MAX_CHUNK_CHARS`; "how does change detection decide…" → `_stat_matches`/`_stat_entry`/`_sha256`; while "what calls update_graph_clusters" / "who calls search_combined" / "what reads RERANKER_MODEL" / "what reads CHUNKER_VERSION" / "what is the main purpose of the chunker" correctly **NO-FIRE** instead of injecting wrong-direction or plumbing noise. **(Re-review E2, honest framing):** these no-fires are graph-EXTRACTOR coverage gaps — the answer often DOES exist in source (a cross-module call, a method-on-instance call, a string-keyed `_indexer_constant("RERANKER_MODEL")` dynamic read) but not as a `calls`/`reads`/`imports` graph edge — so the silence is correct given current graph coverage, not proof no caller exists; they are addressable by a future graph-coverage wave, not settled. The 2 remaining mild cases are constant-value/build-intent behavioral queries that add tail clutter only — never displacing; the agent re-ranks. Full suite **3100 green**; AC-5 recall eval **11/11** (no boost/retrieval regression). Recorded in the Progress Log + the wave delivery sign-off.
- [x] AC-6: The `search_combined` docstring, `docs/specs/mcp-tool-surface.md`, and `docs/architecture/data-and-control-flow.md` document the graph signal + `source="graph"` label + `symbol_extraction_method="graph"`. No `GRAPH_BUILDER_VERSION` bump (consumes the existing graph). docs-lint green.

## Tasks

- [x] Resolve the query/top-hits to graph node(s); fetch 1-hop neighbors (callers/callees/importers, same-community) from the existing graph (`graph_query.py` / the in-memory graph index).
- [x] Emit them as labeled graph-`source` candidates into `1p4hj`'s per-index allocation; dedup against semantic candidates; cap count/hops within the budget.
- [x] Generalize the two-hop expansion to follow graph edges from resolved symbols.
- [x] Graceful fallback when the graph index is absent/empty.
- [x] Tests: AC-1 (graph candidate below cutoff), AC-2 (edge-followed two-hop), AC-3 (cap), AC-4 (no-graph fallback).
- [x] Quality check (AC-5) on ≥3 structural queries; record.
- [x] Docstring + `mcp-tool-surface.md` (AC-6).

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| graph-candidate-source | Engineering | `1p4hj` agent-candidate-pipeline | resolve symbol → 1-hop neighbors → labeled graph-source candidates, deduped + capped |
| two-hop-on-edges | Engineering | graph-candidate-source | follow calls/imports from resolved symbols |
| fallback | Engineering | graph-candidate-source | no-graph degrade to semantic-only |
| tests + quality | Engineering | graph-candidate-source | AC-1–AC-4 tests + AC-5 structural-query check |
| docs | Engineering | graph-candidate-source | docstring + `mcp-tool-surface.md` |


## Serialization Points

- Touches `server_impl.py` `code_ask` candidate selection — the **same path** `1p4hj` reworks. Land `1p4hj` first (it establishes the per-index allocation + `source` labels + dedup this change plugs into); then `1p4hu` adds the graph source. See the wave's shared-file watchpoint. Reads the graph via `graph_query.py`. No `GRAPH_BUILDER_VERSION` bump. Edit gate: `framework_edit_allowed`.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` — the retrieval flow gains a graph-derived candidate source alongside semantic retrieval. No module-boundary or graph-builder change.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The core capability — structural candidates the semantic cutoff misses. |
| AC-2 | important | Generalizing two-hop to edges is the existing-feature upgrade. |
| AC-3 | required | Bound — an uncapped graph expansion blows the budget / pulls the whole subgraph. |
| AC-4 | required | No-graph fallback — must not error on setup / non-code projects. |
| AC-5 | required | **Gates this change** — the graph signal must demonstrably surface answers semantic retrieval missed, not just add noise. |
| AC-6 | required | Discoverability of the `source` label; no builder bump. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-10 | **Dedicated `graph_related` response section (operator-directed redesign).** Operator Q: graph cands always score 0.0 and sit at the citation tail — should they be a separate "related graph results" section? Yes: the 0.0 score buries genuinely-relevant structural answers and the undifferentiated `source="graph"` tag throws away the *relationship* (caller/reader/importer) that IS the answer to "what calls/reads X". Moved structural matches OUT of `citations` into a `graph_related` section grouped by relationship (`callers`/`readers`/`importers`/`related`), each carrying `symbol`/`path`/`lines`/`kind`/`confidence`; `_agent_candidate_select` is now purely semantic. **Semantic dedup kept (operator follow-up "we should still dedup right?") as text-dedup:** a match that is also a citation keeps its relationship entry (structural answer stays complete) but is flagged `also_cited` with the duplicate `excerpt` dropped — the chunk text is never sent twice. `search_combined` returns an 8th tuple element (`graph_related`); `_build_graph_related` assembles it. Live: `what calls resolve_symbol` → `callers:[callgraph,graph_impact,shortest_path]`; `what reads LANCEDB_COMPACT_THRESHOLD` → `readers:[_delete_lance_chunks,_lance_incremental_write,_update_lance_table]` (all 3, vs 2 that fit in citations before). Suite **3100 green** (GraphSignalTests reworked: section grouping + reader bucket + text-dedup). | `server_impl.py` (`_build_graph_related`, `_graph_signal_candidates` relationship labeling via `_GRAPH_REL_LABEL`/`_GRAPH_REL_BUCKET`, agent-branch wiring, `search_combined` 8-tuple, response `data["graph_related"]`); `tests/test_server_tools.py`; `mcp-tool-surface.md` + `data-and-control-flow.md`. |
| 2026-06-10 | **Empirically measured + TIGHTENED (delivery follow-up, operator-directed).** A 17-query live sweep (graph-ON vs OFF, verified against the live graph) showed the as-shipped signal was ~3/14 wins, direction-blind, with 2 relevant-displacement cases — the AC-5 4-query gate was the favorable band. Operator: "tighten it; add to the results, don't kick anything out — we have room (24k→16k)." Implemented: (1) **direction-aware** `one_hop_neighbors(direction=…)` — "what calls/reads/uses X" expands only the named symbol's edges INTO it (callers/readers/importers), no longer answering a callers question with the seed's callees; (2) **seed-scoped** — targeted queries seed only the named symbol (not co-location-noisy semantic breadcrumbs), behavioral keep both; (3) **additive** — graph cands appended after the full semantic selection, no floor slot, not budget-charged → can NEVER evict a semantic cite; (4) **noise gates** — generic-word seed stoplist + test-file + whole-file-module suppression. **Re-measured: 6 clean wins, 5 correct no-fires (wrong answer → honest silence), 2 mild additive-tail, 0 displacement.** Suite **3100 green**; AC-5 eval 11/11 (no regression). +4 graph regression tests. | `server_impl.py` (`_graph_signal_candidates`, `_agent_candidate_select` additive, `_GRAPH_SEED_STOPWORDS`/`_GRAPH_USER_INTENT_RE`/`_GRAPH_OUTGOING_INTENT_RE`/`_GRAPH_SIGNAL_CAND_KINDS`); `graph_query.py` (`one_hop_neighbors` `direction`); `tests/test_server_tools.py` (+4 GraphSignalTests); `/tmp/graph_signal_probe.py` (sweep harness); `mcp-tool-surface.md` + `data-and-control-flow.md`. |
| 2026-06-10 | **IMPLEMENTED + tested (all 6 ACs). Full framework suite 3089 green.** Added `_graph_signal_candidates` + `_node_def_candidate` to `WaveIndex` and wired a `source="graph"` lane into the agent branch of `search_combined`: the query's symbol(s) (top-hit breadcrumb leaves + identifier tokens in the query) → `resolve_symbol` → `one_hop_neighbors(relations=["calls","imports","reads"], max_neighbors=cap×6)` → each neighbor's definition (read from source, bounded window) as a score-0.0 candidate. They enter `_agent_candidate_select` as a third source, surfaced via the **per-index floor** so they appear below the semantic cutoff (AC-1). Bounded by `AGENT_GRAPH_SIGNAL_CAP=3` (AC-3); graceful no-graph/no-symbol fallback to semantic-only (AC-4); follows graph EDGES incl. the 1p4ls `reads` edge, not keyword re-retrieval (AC-2, `symbol_extraction_method="graph"`). **AC-5 (gate) PASS** on 4 live-project queries: "what reads LANCEDB_COMPACT_THRESHOLD" → its 3 reader functions via `reads`; "where is GRAPH_BUILDER_VERSION used" → the graph_query functions; "what calls update_graph_clusters" → structural neighbors; lexical control unaffected (graph adds 3 via the floor, no displacement). Docs: docstring + `mcp-tool-surface.md` + `data-and-control-flow.md` (AC-6); no `GRAPH_BUILDER_VERSION` bump (consumes the existing graph). **+5 `GraphSignalTests`.** | `server_impl.py` (`_graph_signal_candidates`/`_node_def_candidate` + agent-branch wiring + `AGENT_GRAPH_*` consts); `tests/test_server_tools.py` (+5); `docs/specs/mcp-tool-surface.md`; `docs/architecture/data-and-control-flow.md`. |
| 2026-06-09 | Scoped. Split from `1p4hj` at operator request (graph/structural signal deserves its own change + eval, not a rider). Consumes the existing graph (`graph_query.py`); extends `1p4hj`'s agent-mode per-index allocation with a labeled graph source; generalizes today's keyword two-hop to graph edges. No `GRAPH_BUILDER_VERSION` bump. | This change doc. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-09 | Graph signal as a candidate **source/lane** in `1p4hj`'s per-index allocation (vs. a score boost on semantic candidates). | Source-lane keeps it labeled + deduped + budget-allocated like the other modalities, and lets the agent weigh structure explicitly; the boost-vs-lane choice is finalized at implementation. | Score boost on semantic candidates only (deferred — doesn't surface a structural candidate that had NO semantic hit). |
| 2026-06-09 | 1-hop default, capped. | Bounds cost + noise; AC-5 decides whether deeper traversal earns its keep. | Unbounded multi-hop (rejected — pulls the subgraph, blows the budget). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Graph candidates add structurally-near but irrelevant noise. | Labeled + bounded (AC-3); the agent ranks/discards; AC-5 gates that it improves quality, not just volume. |
| Graph index absent (setup / non-code project) → error or empty. | Graceful fallback to semantic-only (AC-4). |
| Graph traversal cost per query. | 1-hop default, capped candidate count (AC-3); the graph is in-memory. |
| Same-path coordination with `1p4hj` (both touch candidate selection). | `1p4hj` lands first; this plugs into its allocation; wave shared-file watchpoint sequences the edits. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
