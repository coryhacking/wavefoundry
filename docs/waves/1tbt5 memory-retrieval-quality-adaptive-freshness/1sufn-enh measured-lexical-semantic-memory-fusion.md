# Measured lexical+semantic memory fusion (relevance separated from policy)

Change ID: `1sufn-enh measured-lexical-semantic-memory-fusion`
Change Status: `implemented`
Owner: framework
Status: active
Last verified: 2026-07-25

Wave: `1tbt5 memory-retrieval-quality-adaptive-freshness`

> **REACTIVATED (2026-07-24 readiness review).** This was deferred from wave
> `1sufo` because the corpus was sparse and the standing evaluation was
> synthetic. The minimal correctness defect was fixed by `1svuj`
> (semantic-as-tie-break), so this change is no longer a bug fix. Wave `1tbt5`
> now reconsiders fusion strictly as an optional measured relevance improvement:
> it expands the hermetic corpus, adds an aggregate-only curated real-corpus
> pass, and keeps fusion default-off unless the explicit adoption gate passes.

## Rationale

`memory_search` now correctly keeps policy primary and uses semantic rank only
as a tie-break within the rounded effective-confidence tier (`1svuj`). Its
query candidate set is still the union of docs-index semantic hits and a
full-token Python containment match. The open question is therefore quality,
not correctness: does a real lexical rank plus the semantic rank improve
ordering over the shipped tie-break without weakening policy constraints?
A record matching neither relevance stream remains filtered out; fusion does
not make unrelated high-trust memories surface.

The candidate design keeps that separation: fuse only lexical and semantic
relevance rankings, apply exact-target matches as deterministic filters or
priority, retain status/decay/confidence/fragile-file as policy, and use
centrality only as a final tie-break. Confidence, decay, freshness, and
centrality never enter the RRF score. The design ships default-on only if the
expanded `1t7ab` evaluation gate passes.

## Requirements

1. **Relevance fusion for `memory_search`.** After status/kind/history and any
   exact-target filters, produce two rankings over the remaining records:
   lexical (deterministic in-process BM25 over normalized
   summary/title/evidence/targets/keywords) and semantic (the docs-index
   embedding hits for memory records). Fuse the positive-match union with
   Reciprocal Rank Fusion. The lexical stream reuses the documented FTS token
   semantics but does not query or mutate the shared FTS tables and creates no
   new index.
2. **Exact-target as deterministic priority/filter.** A `target=`/`symbol=` exact match is applied deterministically (filter or top-priority), never diluted by fusion scores.
3. **Policy as constraints, not fused relevance.** Status
   (surfaced-status filter), the existing confidence/freshness policy key,
   `briefing_included` behavior where applicable, and the `fragile_file`
   always-surface rule are applied as constraints or ordering policy layered on
   top of the fused relevance order — never blended into the RRF score. The
   final search order is policy partition, adaptive freshness/effective
   confidence, RRF rank, centrality, then memory id; RRF cannot move a record
   across a policy partition.
4. **Centrality as tie-break only.** Betweenness centrality is used only to break ties in the final order, not as a relevance stream.
5. **No graph stream.** Graph-proximity relevance remains out of this wave even
   if the evaluation suggests future value; adding a third stream requires a
   separately planned contract.
6. **Adoption gated on measured improvement.** Ship fusion default-on only when
   the expanded `1t7ab` harness satisfies its explicit gate: every hermetic
   invariant passes, hermetic recall@3 does not regress, curated-corpus MRR
   strictly improves over the shipped baseline, curated recall@3 does not
   regress, and lexical-only plus semantic-only controls are recorded against
   the same sample fingerprint frozen before candidate scoring. Evaluate the
   candidate through the shared pure ranking helpers before changing the
   product path. A tie, unavailable curated pass, or any regression records the
   measurements but leaves shipped retrieval unchanged — no dormant product
   flag or unreachable fusion branch.
7. **Determinism + degradation.** RRF is deterministic; with no semantic index the path degrades to lexical-only (still fused-shaped, single stream) with the same policy constraints, never worse than today's text-containment fallback.
   The lexical pass is a single linear traversal of already-loaded surfaced
   records, performs no additional store or FTS calls, and is covered by a
   registered representative-corpus performance budget with contention
   headroom.
8. **`memory_brief` remains queryless.** Do not add lexical/semantic fusion or a
   query parameter to `memory_brief`. It consumes the shared adaptive
   policy/freshness order from `1t7ab` and retains exact-target promotion.

## Scope

**Problem statement:** memory search now preserves trust/decay policy through
the `1svuj` semantic tie-break, but it has no measured lexical rank. Determine
whether relevance fusion improves that correct shipped baseline without
weakening policy, and adopt it only on measured evidence.

**In scope (edited under `framework_edit_allowed`):**
- Add shared pure in-process BM25/RRF helpers over the already-loaded surfaced
  record set, using documented FTS token semantics. Do not query the global FTS
  tables and do not add an index. Evaluate them before changing the response
  path.
- `.wavefoundry/framework/scripts/server_impl.py` — only when the adoption gate
  passes, replace the current semantic-tie-break branch in
  `memory_search_response` with the lexical+semantic RRF candidate order while
  preserving policy as the primary ordering contract.
- Docs — memory README ranking section documenting relevance-vs-policy separation.
- Tests — RRF determinism, relevance/policy separation for records that both
  pass the relevance candidate union, degraded lexical-only path, queryless
  brief invariance, and the expanded `1t7ab` gate assertions.

**Out of scope:**
- **The base eval harness** — the completed `1sufm` harness is reused and
  expanded by companion change `1t7ab`; this change consumes that result.
- **A graph relevance stream** — separately planned even if evaluation suggests
  it may help.
- **Reranker over memory** — out of scope (a small typed corpus does not need a cross-encoder; and it would reintroduce score-blending with policy).
- **Brief count-cap → token-budget** — separate deferred item.
- **Query/relevance changes to `memory_brief`** — it has no query relevance
  input; only the shared freshness-policy changes from `1t7ab` apply.

## Acceptance Criteria

- [~] AC-1: Memory search fuses only the lexical and semantic relevance rankings via RRF; confidence/decay/centrality are NOT folded into the fused score. (required) — intentionally not met: the measured adoption gate failed, so RRF remains evaluation-only and the product path is unchanged.
- [~] AC-2: Exact target/symbol matches are applied as a deterministic filter/priority, not diluted by fusion. (required) — intentionally not met in a fused product path because fusion was not adopted; the shipped exact-target filter/brief priority remains pinned.
- [~] AC-3: Status, the existing confidence/freshness policy key,
  briefing-inclusion behavior, and `fragile_file` visibility remain policy
  constraints layered on the fused order; among records admitted by the
  relevance candidate union, fusion cannot move a record across its policy
  partition. (required) — intentionally not met in product fusion because the gate failed; the evaluation candidate applies the shared policy sort and the shipped path retains its policy constraints.
- [~] AC-4: Centrality is used only as a final tie-break; no graph relevance
  stream is added in this wave. (required) — intentionally not met as a fused product-path contract because no fusion path shipped; the evaluation candidate uses shared centrality tie-breaking and no graph stream was added.
- [x] AC-5: Fusion is adopted as default ONLY when the expanded `1t7ab` gate
  passes every hermetic invariant, non-regresses hermetic and curated recall@3,
  strictly improves curated MRR, and records lexical-only plus semantic-only
  controls against the frozen sample; otherwise measurements are recorded and
  the shipped response path remains unchanged, with no dormant product fusion
  flag or branch.
  (required)
- [x] AC-6: Deterministic RRF; no-semantic-index degrades to lexical-only with
  the same policy, never worse than today's fallback. The lexical pass is one
  linear traversal of loaded surfaced records, adds no store/FTS calls, and
  passes a registered representative-corpus performance budget with contention
  headroom. (required)
- [x] AC-7: `memory_brief` remains queryless and receives no lexical/semantic
  fusion; target priority and shared policy/freshness ordering are
  regression-pinned. (required)
- [x] AC-8: Full framework suite green; docs-lint clean. (required)

## Tasks

- [x] Build shared pure lexical + semantic candidate rankings over surfaced
  records; RRF fuse for evaluation (relevance only).
- [x] Apply exact-target as filter/priority; layer
  status/confidence/freshness/fragile behavior as policy constraints;
  centrality tie-break.
- [x] Gate adoption on the expanded `1t7ab` harness; record measurements and
  leave the shipped path unchanged on a tie or any incomplete/regressed gate.
- [~] Only after a passing gate, replace the `memory_search` semantic tie-break;
  keep `memory_brief` queryless and on shared policy/freshness ordering. — intentionally not met: the curated pass was unavailable, so the gate failed and product wiring was forbidden.
- [x] Tests: RRF determinism, relevance/policy separation, degraded
  lexical-only, queryless brief invariance, and gate assertions.
- [x] Memory README ranking section; full suite + docs-lint. *(Documentation and targeted tests complete; full-suite/docs-lint evidence is recorded at the wave gate.)*

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| candidate helpers | framework | — | shared pure lexical+semantic RRF over records |
| policy evaluation | framework | candidate helpers | exact-target + decay/confidence/fragile invariants |
| gate | framework | policy evaluation | apply the explicit `1t7ab` adoption gate |
| product wiring | framework | gate | only on pass; otherwise no shipped-path edit |
| verify | framework | product wiring or recorded gate failure | tests + docs |


## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py`
  (`memory_search_response`, `_memory_ranked`) — edited under
  `framework_edit_allowed` only after a passing gate.
  `memory_brief_response` is a regression boundary, not a fusion edit site.
- Pure cadence/comparability and lexical/RRF ranking helpers are shared by the
  eval runner and response orchestration; neither consumer reimplements the
  ordering formula.

## Affected Architecture Docs

- `docs/specs/mcp-tool-surface.md`
- `docs/agents/memory/README.md`
- `docs/architecture/search-architecture.md`
- `docs/architecture/testing-architecture.md`
- `docs/references/memory-retrieval-eval.md`

No new public tool or index boundary.

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
| AC-7 | required | Brief has no query stream and must not acquire one accidentally |
| AC-8 | required | No regression |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-17 | Change doc authored; separation design validated against the agentmemory review | `server_impl.py:8002-8004` (semantic override); enhancement plan retrieval design |
| 2026-07-24 | Readiness review reconciled the plan to the shipped `1svuj` tie-break, the queryless brief path, in-process lexical ranking, and the expanded `1t7ab` gate. | `memory_search_response`; `memory_brief_response`; `run_memory_eval.py` |
| 2026-07-24 | Evaluation-only BM25/RRF candidate completed with deterministic controls and a registered 1,000-record budget. The gate rejected adoption: candidate hermetic MRR `0.8485` vs baseline `1.0000`, and the frozen curated semantic pass was unavailable. No product fusion branch or flag was added. | `run_memory_eval.py`; `test_memory_eval.py`; `perf_budget_policy.py`; product-path source pin. |
| 2026-07-24 | Delivery-review repair (blocking P2, code-reviewer): the eval candidate's `_policy_order` treated an empty relevance union as unrestricted (`not relevance_order or ...`), so a query matching neither the lexical nor the semantic stream surfaced every record, violating the positive-match-union and lexical-degradation contract. Fixed: the query path now admits only the relevance union (empty -> zero); `_shipped_baseline_order` opts into a new `prefiltered=True` so its containment union is not double-restricted. Added `test_empty_relevance_union_yields_zero_candidates` covering candidate, lexical-only, semantic-only, and the prefiltered baseline. Shipped `memory_search` unaffected (fusion stays evaluation-only). Ledger chain terminal (repair_start + fresh independent code-reviewer reverification); delivery re-approved post-repair. | `run_memory_eval.py::_policy_order`; `test_memory_eval.py::test_empty_relevance_union_yields_zero_candidates`; full suite 6,194 OK; eval fingerprint `72ead292…d23f4a4` unchanged |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-17 | Fuse only lexical+semantic relevance; policy as constraints | Confidence/decay/centrality are not relevance engines; blending demotes trust records | RRF over all signals incl. confidence/centrality (rejected — conflates relevance and policy) |
| 2026-07-17 | Reranker out of scope | Small typed corpus; reranker would reintroduce score-blending with policy | Cross-encoder rerank (rejected per the RRF-vs-reranker analysis) |
| 2026-07-17 | Graph stream only if eval proves it | Do not assume graph traversal helps a small typed corpus | Include graph stream now (rejected — unproven) |
| 2026-07-17 | Adopt only if it beats the `1sufm` baseline | Measured, not assumed | Ship unconditionally (rejected) |
| 2026-07-24 | Treat `1svuj` as the correct shipped baseline, not an unfixed defect. | The wholesale semantic override is already gone; fusion must justify itself as quality improvement. | Reopen the old bug framing: rejected as stale. |
| 2026-07-24 | Use in-process BM25 over loaded records and keep `memory_brief` queryless. | The memory path does not use shared FTS today, and brief has no query relevance signal. | Query global FTS or add a brief query: rejected as needless boundary expansion. |
| 2026-07-24 | Require strict curated-MRR improvement and recall/invariant non-regression. | Makes default-on adoption falsifiable; a tie remains evidence to keep the simpler shipped order. | "Looks better" council judgment: rejected as non-repeatable. |
| 2026-07-24 | Evaluate shared pure helpers against a pre-frozen corpus before product wiring. | Failed optional experiments should produce evidence, not dormant production branches, and the adoption sample must not be tuned after results are visible. | Land a default-off product flag first: rejected as unnecessary maintenance surface. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Fusion regresses a policy invariant | AC-3/AC-5 gate on the expanded `1t7ab` invariant cases; default-off if it regresses |
| RRF nondeterminism | Fixed k, stable input orders, determinism test |
| Reintroducing relevance/policy conflation | Policy applied strictly as post-fusion constraints; test that a low-text-overlap trust record holds position |
| Lexical helper drifts from degraded behavior | One pure tokenizer/BM25 helper shared by default-on and lexical-only paths |
| Fusion leaks into queryless briefing | `memory_brief` no-query and ordering invariance regression |
| Linear lexical scoring becomes a hot-path regression | Score only loaded surfaced records, add no store/FTS calls, and enforce a registered representative-corpus budget with contention headroom |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
