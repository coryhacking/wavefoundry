# Measured lexical+semantic memory fusion (relevance separated from policy)

Change ID: `1sufn-enh measured-lexical-semantic-memory-fusion`
Change Status: `planned`
Owner: framework
Status: planned
Last verified: 2026-07-20

Wave: `1sufo memory-retrieval-eval-and-fusion`

> **DEFERRED (2026-07-17, council review).** Split out of wave `1sufo` and returned to `docs/plans/`. Both the red-team and reality-checker seats found full lexical+semantic RRF disproportionate for an empty/sparse typed corpus (RRF's benefit needs many candidates with divergent rankings; a handful of short records will largely agree, so it most likely evaluates to "do not adopt", and only against synthetic fixtures). The real defect is a ~2-line wholesale-`sort()` override, fixed by change `1svuj` (semantic-as-tie-break). Revisit this full-RRF apparatus only once a real corpus exists and the `1sufm` eval can prove fusion beats a *real* baseline. Two corrections to carry when revisited: (1) the framing below is imprecise — a non-matching high-trust record is *filtered out entirely* by the pre-filter (records must be a semantic hit OR a full-token `_text_match`), not "pushed down"; (2) the "reuse the FTS layer" claim is overstated — the current memory path uses `search_docs` + a Python token-match and does NOT touch FTS, so the lexical stream is genuinely new (in-process BM25 over the small loaded set, which is actually better for the hermetic/degraded path).

## Rationale

`memory_search` today conflates relevance and policy: it computes the decay/centrality order (`_memory_ranked`) and then re-sorts wholesale by semantic rank when a query has semantic hits (`memory_search_response`, semantic re-sort ~`server_impl.py:8008-8010`, anchor by symbol under concurrent edits). Among the records that pass the pre-filter, a high-trust `operator_preference`, `decision`, or `fragile_file` advisory can be outranked by a lower-trust one on pure text relevance — backwards for advisory memory. (Note: a record matching *neither* the query semantically nor by full-token text is filtered out by the pre-filter, not merely demoted.)

The fix, validated in design against the agentmemory review, is to separate relevance from policy: fuse only the lexical and semantic relevance rankings (RRF), apply exact-target matches as deterministic filters/priority, apply status/decay/confidence/fragile-file as policy constraints, and use centrality only as a final tie-break. We do NOT fold confidence/decay/centrality into the fused score (they are not relevance engines), and we add a graph stream only if the memory eval proves incremental benefit. This change adopts fusion ONLY if it beats the `1sufm` baseline without regressing the exact-target, decay, or supersession invariants.

## Requirements

1. **Relevance fusion.** Produce two candidate rankings over the surfaced records — lexical (exact-token / FTS-style over summary/title/evidence/targets, reusing the existing lexical infrastructure) and semantic (the docs-index embedding over the record text) — and fuse the two RANKINGS with Reciprocal Rank Fusion. Only these two relevance signals are fused.
2. **Exact-target as deterministic priority/filter.** A `target=`/`symbol=` exact match is applied deterministically (filter or top-priority), never diluted by fusion scores.
3. **Policy as constraints, not fused relevance.** Status (surfaced-status filter), decay/`briefing_included` floor, confidence floor, and the `fragile_file` always-surface rule are applied as constraints/ordering policy layered on top of the fused relevance order — never blended into the RRF score.
4. **Centrality as tie-break only.** Betweenness centrality is used only to break ties in the final order, not as a relevance stream.
5. **No graph stream initially.** Add a graph-proximity relevance stream only if `1sufm` demonstrates incremental benefit on the memory eval; default is lexical+semantic.
6. **Adoption gated on measured improvement.** Ship fusion only when the `1sufm` harness shows it beats the recorded baseline (and lexical-only / semantic-only) on the required metrics WITHOUT regressing any policy-invariant case (exact-target, decay, supersession, degraded no-index). If it does not, this change lands the fusion behind a default-off flag with the measurements recorded, and the current order stays default.
7. **Determinism + degradation.** RRF is deterministic; with no semantic index the path degrades to lexical-only (still fused-shaped, single stream) with the same policy constraints, never worse than today's text-containment fallback.

## Scope

**Problem statement:** memory search lets semantic relevance override the trust/decay policy; we need a principled fusion that keeps relevance and policy separate, adopted only on measured evidence.

**In scope (edited under `framework_edit_allowed`):**
- `.wavefoundry/framework/scripts/server_impl.py` — replace the `memory_search` semantic-override (`:8002-8004`) with: lexical+semantic RRF for relevance, exact-target as filter/priority, policy constraints layered on top, centrality tie-break. Apply the same relevance/policy separation to `memory_brief` ordering where the semantic path applies.
- Reuse the existing lexical/FTS infrastructure (the `code_lexical`/1.12.0 lexical layer) for the lexical stream over memory-record text, and the docs semantic index for the semantic stream — no new index.
- Docs — memory README ranking section documenting relevance-vs-policy separation.
- Tests — RRF determinism, relevance/policy separation (a high-trust low-text-overlap record is not demoted below its policy position), degraded lexical-only path, and the `1sufm` gate assertions.

**Out of scope:**
- **The eval harness itself** — companion `1sufm` (this change consumes it).
- **A graph relevance stream** — only if `1sufm` proves benefit; not in this change by default.
- **Reranker over memory** — out of scope (a small typed corpus does not need a cross-encoder; and it would reintroduce score-blending with policy).
- **Brief count-cap → token-budget** — separate deferred item.

## Acceptance Criteria

- [ ] AC-1: Memory search fuses only the lexical and semantic relevance rankings via RRF; confidence/decay/centrality are NOT folded into the fused score. (required)
- [ ] AC-2: Exact target/symbol matches are applied as a deterministic filter/priority, not diluted by fusion. (required)
- [ ] AC-3: Status, decay/briefing floor, confidence floor, and `fragile_file` always-surface are applied as policy constraints layered on the fused order; a high-trust low-text-overlap record is not demoted below its policy position (test). (required)
- [ ] AC-4: Centrality is used only as a final tie-break. No graph stream unless `1sufm` proves benefit. (required)
- [ ] AC-5: Fusion is adopted as default ONLY when the `1sufm` harness shows it beats baseline + lexical-only + semantic-only without regressing exact-target/decay/supersession/no-index; otherwise it lands default-off with measurements recorded. (required)
- [ ] AC-6: Deterministic RRF; no-semantic-index degrades to lexical-only with the same policy, never worse than today's fallback. (required)
- [ ] AC-7: Full framework suite green; docs-lint clean. (required)

## Tasks

- [ ] Build lexical + semantic candidate rankings over surfaced records; RRF fuse (relevance only).
- [ ] Apply exact-target as filter/priority; layer status/decay/confidence/fragile as policy constraints; centrality tie-break.
- [ ] Replace the `memory_search` semantic-override; apply separation to `brief` semantic ordering.
- [ ] Gate adoption on the `1sufm` harness (default-off if it does not beat baseline); record measurements.
- [ ] Tests: RRF determinism, relevance/policy separation, degraded lexical-only, gate assertions.
- [ ] Memory README ranking section; full suite + docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| fusion | framework | — | lexical+semantic RRF relevance over records |
| policy | framework | fusion | exact-target filter + decay/confidence/fragile constraints + centrality tie-break |
| gate | framework | policy | adopt only if `1sufm` beats baseline; else default-off + measurements |
| verify | framework | gate | tests + docs |


## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py` (`memory_search`/`brief`) — edited under `framework_edit_allowed`. Depends on `1sufm` (eval) as the adoption gate.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` note (ranking semantics of memory search); memory README ranking section. No new boundary — a ranking rewrite within the existing tools, reusing existing indices.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | RRF fuses relevance only — the core correction |
| AC-2 | required | Exact-target is deterministic, not fusion-diluted |
| AC-3 | required | Policy as constraints; trust records not demoted by text relevance |
| AC-4 | required | Centrality is a tie-break, not a relevance engine |
| AC-5 | required | Adopt only on measured improvement (the gate) |
| AC-6 | required | Deterministic + safe degradation |
| AC-7 | required | No regression |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-17 | Change doc authored; separation design validated against the agentmemory review | `server_impl.py:8002-8004` (semantic override); enhancement plan retrieval design |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-17 | Fuse only lexical+semantic relevance; policy as constraints | Confidence/decay/centrality are not relevance engines; blending demotes trust records | RRF over all signals incl. confidence/centrality (rejected — conflates relevance and policy) |
| 2026-07-17 | Reranker out of scope | Small typed corpus; reranker would reintroduce score-blending with policy | Cross-encoder rerank (rejected per the RRF-vs-reranker analysis) |
| 2026-07-17 | Graph stream only if eval proves it | Do not assume graph traversal helps a small typed corpus | Include graph stream now (rejected — unproven) |
| 2026-07-17 | Adopt only if it beats the `1sufm` baseline | Measured, not assumed | Ship unconditionally (rejected) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Fusion regresses a policy invariant | AC-3/AC-5 gate on the `1sufm` invariant cases; default-off if it regresses |
| RRF nondeterminism | Fixed k, stable input orders, determinism test |
| Reintroducing relevance/policy conflation | Policy applied strictly as post-fusion constraints; test that a low-text-overlap trust record holds position |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
