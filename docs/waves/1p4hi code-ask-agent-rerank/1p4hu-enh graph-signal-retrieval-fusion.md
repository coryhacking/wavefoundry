# Graph-Signal Retrieval Fusion for `code_ask` (Structural Proximity as a Candidate Source)

Change ID: `1p4hu-enh graph-signal-retrieval-fusion`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-09
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

- [ ] AC-1: For a query resolving to a symbol, agent-mode surfaces graph-reachable candidates (1-hop callers/callees/importers) **even when their embedding similarity is below the semantic cutoff**, labeled by graph `source` and deduped against semantic candidates. Verified by a synthetic fixture where a structurally-relevant chunk has low text similarity but appears via the graph signal.
- [ ] AC-2: The explanatory-question two-hop expansion follows **graph edges** from the resolved symbols (calls/imports), not only keyword re-retrieval. Verified by a test asserting a callee/caller surfaced via a graph edge.
- [ ] AC-3: **Bounded** — the graph expansion is capped (max candidates, hops=1 default) within the shared token budget, deduped; it never exceeds the budget or pulls an unbounded subgraph. Verified by a high-fan-in-symbol test asserting the cap holds.
- [ ] AC-4: **Graceful fallback** — with no graph index (absent/empty), agent-mode returns the `1p4hj` semantic-only candidate set with no error. Verified by a no-graph test.
- [ ] AC-5 (quality — **gates this change**): on **≥3 real queries** whose answer is structurally-related but lexically-dissimilar (e.g. "what breaks if I change X" → callers of X; "where is this config consumed" → importers), the graph signal surfaces the right candidates that semantic retrieval missed; **no regression** on lexical queries. Recorded in the Progress Log with the query set and outcome.
- [ ] AC-6: The `code_ask` docstring + `docs/specs/mcp-tool-surface.md` document the graph signal + `source` label. No `GRAPH_BUILDER_VERSION` bump (consumes the existing graph). docs-lint green.

## Tasks

- [ ] Resolve the query/top-hits to graph node(s); fetch 1-hop neighbors (callers/callees/importers, same-community) from the existing graph (`graph_query.py` / the in-memory graph index).
- [ ] Emit them as labeled graph-`source` candidates into `1p4hj`'s per-index allocation; dedup against semantic candidates; cap count/hops within the budget.
- [ ] Generalize the two-hop expansion to follow graph edges from resolved symbols.
- [ ] Graceful fallback when the graph index is absent/empty.
- [ ] Tests: AC-1 (graph candidate below cutoff), AC-2 (edge-followed two-hop), AC-3 (cap), AC-4 (no-graph fallback).
- [ ] Quality check (AC-5) on ≥3 structural queries; record.
- [ ] Docstring + `mcp-tool-surface.md` (AC-6).

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
