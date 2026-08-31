# Make Retrieval Candidate Generation Honor Filters and ANN Tuning

Change ID: `1wpah-bug retrieval-candidate-generation-correctness`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-31
Wave: 1wpif index-content-and-retrieval-correctness

## Rationale

Healthy semantic search and lexical fallback retrieve a bounded global candidate window and apply language or per-file constraints afterward. A selected-language result just outside that window becomes an incorrect zero; skewed per-file results underfill even when enough eligible files exist. Separately, production declares Lance `nprobes=20` and `refine_factor=10` but never applies either setting, so runtime recall and latency do not match the documented tuning.

## Requirements

1. Single-language filters SHALL constrain Lance and FTS candidate generation before bounded top-k selection.
2. Category and per-file limits SHALL continue bounded retrieval until the requested result count is filled or an honest safety ceiling is reached. For constraints that cannot be pushed down, each source/table SHALL use monotonic candidate windows `30 → 60 → 120 → 240`, at most four queries and 240 examined rows per public call; dense and lexical work SHALL expose their individual accounting within the shared public-call budget.
3. Underfill diagnostics SHALL distinguish exhausted eligible results from a bounded-retrieval ceiling. A ceiling exit SHALL return typed `bounded_ceiling_reached` with rounds and examined-row counts; substrate exhaustion SHALL use a distinct reason.
4. Production Lance queries SHALL apply supported ANN tuning explicitly, or remove unsupported constants and document the actual defaults.
5. ANN settings SHALL be retained only after comparison with exact/flat search on the frozen `1sear` holdout demonstrates Recall@10 at least 0.98 overall, no applicable query below 0.90, and at least 10% warm-p95 improvement. Otherwise production SHALL use exact/default behavior and retire the inert constants. The comparison SHALL also satisfy the standing evaluator's baseline-relative tolerance and absolute ceilings: 3,000 ms for `code_search`, 1,000 ms for `code_lexical`, 5,000 ms for `code_ask`, envelope growth no greater than `max(15%, 4 KiB)`, and an absolute 256 KiB envelope.
6. Public tool descriptions and internal comments SHALL match the resulting candidate windows, rerank order, and filter behavior.

## Scope

**Problem statement:** Post-window filtering loses eligible matches, and declared ANN tuning is inert.

**In scope:** Lance/FTS predicates, bounded refill, per-file diversity, ANN query-builder integration, diagnostic and description consistency, and adversarial tests.

**Out of scope:** Embedding/reranker replacement, unbounded scans, general relevance tuning, and golden-suite creation already owned by `1sear`.

## Acceptance Criteria

- [ ] AC-1: A selected-language candidate below 30 higher-ranked other-language rows remains retrievable in healthy semantic search and lexical fallback.
- [ ] AC-2: With matches in at least five files, `limit=5,max_per_file=1` returns five files or an explicit bounded-ceiling diagnostic within the frozen four-round/240-row-per-source limit; hostile-skew tests prove termination and exact accounting.
- [ ] AC-3: Category filters preserve eligible recall without unbounded corpus scans.
- [ ] AC-4: Lance query-builder tests prove the selected `nprobes` and `refine_factor` behavior is invoked, or prove and document why defaults replace those constants.
- [ ] AC-5: The frozen `1sear` holdout comparison meets the exact Recall@10, per-query, warm-p95, standing-tool, and envelope thresholds in Requirement 5; a below-floor or no-speedup candidate setting is rejected.
- [ ] AC-6: Public MCP descriptions, comments, architecture docs, healthy and degraded tests all agree with runtime behavior; full tests pass.

## Tasks

- [ ] Define shared language/category predicates for Lance and FTS candidates.
- [ ] Implement bounded refill or ranked SQL/window behavior for per-file caps.
- [ ] Add typed refill termination/accounting diagnostics and hostile-skew ceiling fixtures.
- [ ] Confirm the installed Lance API and apply or retire ANN tuning constants.
- [ ] Add exact-search comparison and adversarial skew fixtures.
- [ ] Align tool descriptions, comments, and search architecture documentation.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Filter generation | implementer | — | Healthy and degraded paths |
| ANN integration | implementer | — | API and measured tradeoff |
| Verification/contracts | qa-reviewer | Both | Skew, exact comparison, descriptions |

## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py`, `.wavefoundry/framework/scripts/index_state_store.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`, `.wavefoundry/framework/scripts/tests/test_fts_lexical_layer.py`, `docs/architecture/search-architecture.md`

## Affected Architecture Docs

- `docs/architecture/search-architecture.md`

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Public language filtering must not produce false absence. |
| AC-2 | required | Per-file caps promise result diversity. |
| AC-3 | important | Category filters need the same bounded correctness. |
| AC-4 | required | Declared tuning must control runtime or be removed. |
| AC-5 | required | ANN changes require measured recall and latency evidence. |
| AC-6 | important | Consumers must receive an accurate retrieval contract. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-30 | Planned from semantic and FTS audit findings. | Rank-31 language and per-file skew probes; recording query-builder probe showing unused ANN methods. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-30 | Push exact filters into candidate sources and use bounded refill only for constraints that cannot be pushed down. | Preserves recall while keeping work bounded and diagnostics honest. | **Increase oversampling globally:** still fails under larger skew. **Post-filter only:** retains false zeroes. **Unbounded refill:** protects recall but risks uncontrolled latency. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Filter predicates diverge across Lance and FTS. | Centralize normalization/partition mapping and run parity fixtures. |
| ANN tuning improves latency but lowers recall. | Gate settings against exact-search Recall@k and retain measured defaults only. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
