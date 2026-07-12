# Operational Docs Refresh + Docs-vs-Code Constants Lint

Change ID: `1seau-doc ops-docs-refresh-and-constants-lint`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-12
Wave: TBD

## Rationale

External code review (2026-07-12), validated: two operational contracts are materially stale. `docs/RELIABILITY.md` (~30) still frames the MCP semantic index as future work; `docs/architecture/performance-budget.md` (~18) claims "None currently; all operations are local file I/O with small data volumes" and refers to a future SQLite index — written before embedding builds, GPU/CoreML sessions, cross-encoder reranking, ~100MB Lance tables, the index-state store, and the measured hot paths (hook builds, heal passes, FTS rebuilds) existed. Stale contracts mislead both agents (who read them as tier-1 context) and reviewers (the external review itself burned time on them).

Second half: the review's suggestion of lint assertions binding documented facts to code constants is a cheap, high-leverage docs-lint extension — the same declarative-check pattern as `check_deprecated_role_references` — so drifted claims fail the docs gate instead of waiting for the next external review.

## Requirements

1. **RELIABILITY.md refresh:** current failure modes and postures — derived-only stores with drop-and-rebuild, the build lock + `lock.held` contract, fail-soft search degradation, the persisted store log, per-layer freshness and the heal, secrets-scan cache posture. Remove future-work framing for shipped systems.
2. **performance-budget.md refresh:** real budgets from measured evidence — full rebuild (~6 min documented elsewhere), incremental hook build (zero-change ~1.2s / docs ~4s / code-edit ~12s measured in 1sc7c), heal pass (38s/1,330 files), FTS derived rebuild (~3.4s), `code_ask` latency components (vector/rerank ms), reranker cold-load; identify the ACTUAL hotspots (embedding, reranker session init, O(corpus) walks) and their guards.
3. **Docs-constants lint check:** a declarative docs-lint check asserting named documented facts match code constants — model names (`DOCS_MODEL`/`CODE_MODEL`/`RERANKER_MODEL`), `CHUNKER_VERSION`/`WALKER_VERSION`/`GRAPH_BUILDER_VERSION`/`STATE_STORE_SCHEMA_VERSION` mentions in operational docs, `wave_index_build` content values, and the `index_freshness` state set. Declarative mapping (doc pattern → constant), same shape as existing config-driven checks; failures name the doc line and the constant.
4. **Scope discipline:** docs-only plus the lint check — no behavior changes; the lint check lands with the mappings for the two refreshed docs plus the spec's content values (extensible later).

## Scope

**Problem statement:** two tier-1 operational contracts describe a pre-index-era system, and nothing detects documented-fact drift.

**In scope:** the two docs; one docs-lint check + its declarative mapping; lint fixtures.
**Out of scope:** architecture docs already refreshed by recent waves; seed content.

## Acceptance Criteria

- [ ] AC-1: RELIABILITY.md describes the shipped reliability posture (stores, locks, degradation, logs, heal) with no future-work framing for shipped systems.
- [ ] AC-2: performance-budget.md carries measured budgets and the real hotspot list with guards.
- [ ] AC-3: The docs-constants lint check fails on a seeded drift fixture (wrong model name in a doc) and passes on the refreshed docs; wired into the standard docs gate.
- [ ] AC-4: Full docs validation + framework tests pass (the lint check's own unit fixtures included).

## Tasks

- [ ] Rewrite the two docs from current evidence (cite measurements, not aspirations).
- [ ] Declarative docs-constants check + mapping + fixtures in docs-lint.
- [ ] Suite + validate.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| docs-refresh | implementer | — | Evidence-based rewrite |
| constants-lint | implementer | — | Declarative check |
| verify | qa-reviewer | both | Fixtures + gate |


## Serialization Points

- None; independent of the other review-derived waves.

## Affected Architecture Docs

- The two named docs ARE the deliverable; `docs/architecture/testing-architecture.md` gains a line for the new lint tier if needed.

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Tier-1 contract accuracy. |
| AC-2 | required | Same. |
| AC-3 | required | The drift-prevention mechanism, not just a one-time fix. |
| AC-4 | required | Standard gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-12 | Drafted from the external code review (P2), staleness validated by direct read ("None currently; all operations are local file I/O with small data volumes"). Measured budget inputs already exist from the 1sc7c design pass and 1sbfk/1seiz live probes. | Review report; doc reads; 1sc7c hook-cost measurements. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-12 | Constants lint is declarative (pattern → constant mapping), scoped initially to the two refreshed docs + spec content values. | Same proven shape as existing declarative lint checks; small first mapping avoids a brittle whole-corpus assertion sweep. | **Whole-corpus fact extraction:** brittle, high false-positive cost. **No lint:** the docs drift again by the next review. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Lint mapping itself drifts (constant renamed) | The check fails loudly on a missing constant — self-announcing. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
