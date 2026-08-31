# Heal FTS State and Report Honest Query Failures

Change ID: `1wpag-bug fts-reconciliation-query-honesty`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-31
Wave: 1wpif index-content-and-retrieval-correctness

## Rationale

FTS reconciliation can declare the lexical layer synchronized when registry IDs match Lance even if an FTS virtual table is missing, recreated empty, or internally corrupt. Direct lexical search then reports a healthy zero-result query instead of an infrastructure failure. This makes exact-token recall silently unavailable on a supported path and gives operators and agents incorrect diagnostics.

## Requirements

1. Reconciliation SHALL verify registry-to-FTS liveness, row parity, and keyed payload integrity before taking the in-sync early return. Equal-count substitution or payload corruption SHALL not pass as synchronized.
2. Missing, empty, or corrupt FTS derived state SHALL heal from authoritative rows during the next ordinary reconcile/build path.
3. Public lexical and hybrid retrieval SHALL distinguish query failure or undercoverage from a genuine zero-hit corpus result.
4. Lexical health SHALL report per-table Lance, registry, and FTS parity plus the last keyed-integrity result without scanning corpus-sized state on each query. Healthy public retrieval SHALL perform only an O(1) completed-epoch/cache lookup; full probes run at reconcile/open/epoch change or after a serving error.
5. Documentation SHALL consistently identify SQLite FTS5 as the active lexical engine.
6. When semantic retrieval remains healthy but lexical state is unavailable, hybrid tools SHALL return successful semantic results plus a typed lexical-undercoverage diagnostic. Lexical-only or degraded requests that cannot serve their promised path SHALL return `query_failed` rather than a healthy zero.
7. Healing SHALL remain build-lock and epoch owned, run at most once per damaged table per epoch, and never be triggered by a read-only public query.

## Scope

**Problem statement:** Derived lexical state can be absent while reconciliation and public search claim it is healthy.

**In scope:** FTS probes, reconcile/heal decisions, public query diagnostics, parity health, corruption fixtures, and stale Tantivy documentation.

**Out of scope:** Tokenizer changes, ranking changes, query history, dashboard presentation already covered by `1uqec`, and replacing SQLite FTS5.

## Acceptance Criteria

- [ ] AC-1: Dropping either FTS virtual table is detected by ordinary reconciliation and rebuilt from authoritative rows.
- [ ] AC-2: Corrupting or removing an FTS shadow row, or substituting one keyed row/payload while preserving every relevant count, is detected and repaired without requiring a manual rebuild command.
- [ ] AC-3: Before repair, every affected public query returns a typed failure/undercoverage diagnostic and never a healthy zero-result explanation.
- [ ] AC-4: Healthy zero-result queries remain distinguishable and preserve current response contracts.
- [ ] AC-5: Health exposes per-table FTS parity and the epoch-cached keyed-integrity result; tests cover cold open, interrupted publication, missing table, empty table, corrupt row, equal-count substitution, and healthy controls.
- [ ] AC-6: FTS architecture documentation names SQLite FTS5 consistently; the full framework test suite and docs validation pass.
- [ ] AC-7: Hybrid requests preserve healthy semantic results with a lexical-undercoverage diagnostic, while lexical-only/degraded requests return typed `query_failed`; adjacent healthy-zero controls remain unchanged.
- [ ] AC-8: A warmed healthy public query executes no FTS/registry/shadow `COUNT(*)` or corpus-sized integrity scan; an epoch transition or serving error performs one bounded probe/heal sequence, caches the result, and leaves subsequent reads non-healing.

## Tasks

- [ ] Integrate `fts_probe` into reconcile and derived-state healing decisions.
- [ ] Route direct lexical and hybrid lexical candidates through shared probed serving behavior.
- [ ] Extend health payloads with cheap per-table parity state.
- [ ] Add a keyed FTS integrity digest/check at publication boundaries and cache its result by completed epoch.
- [ ] Add injected-failure and recovery tests.
- [ ] Remove stale Tantivy references from current architecture documentation.
- [ ] Add hybrid-success and lexical-only/degraded-failure response-contract fixtures.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| State reconciliation | implementer | — | Probe and healing contract |
| Serving diagnostics | implementer | State reconciliation | Shared public behavior |
| Verification/docs | qa-reviewer | Both | Fault injection and current engine docs |

## Serialization Points

- `.wavefoundry/framework/scripts/index_state_store.py`, `.wavefoundry/framework/scripts/indexer.py`, `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/`, `docs/architecture/chunking-and-indexing-pipeline.md`, `docs/architecture/search-architecture.md`

## Affected Architecture Docs

- `docs/architecture/chunking-and-indexing-pipeline.md`
- `docs/architecture/search-architecture.md`

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Missing FTS state must not publish as healthy. |
| AC-2 | required | Ordinary recovery is the reliability outcome. |
| AC-3 | required | False healthy zeroes mislead every retrieval consumer. |
| AC-4 | required | Honest failure reporting must not break genuine misses. |
| AC-5 | required | Fault-state coverage guards the complete recovery contract. |
| AC-6 | important | Documentation and full validation prevent contract drift. |
| AC-7 | required | Graceful degradation must preserve available results without disguising lexical failure. |
| AC-8 | required | Correctness checks must not turn every lexical query into a corpus-sized health scan or mutation path. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-30 | Planned from the FTS audit lane. | Bounded missing-table and corrupt-state probes; source validation of reconcile early return and public lexical diagnostics. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-30 | Make the existing FTS probe part of normal reconciliation and serving. | Reuses the current integrity primitive and repairs the authoritative lifecycle boundary. | **Trust registry/Lance counts:** reproduces the defect. **Always rebuild FTS:** correct but imposes unnecessary cost on every healthy open/build. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Per-query probes add latency. | Cache build-bound health and reserve direct probes for reconcile/open or suspected failure. |
| Healing races a build publication. | Preserve the existing epoch fence and test interrupted-build states. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
