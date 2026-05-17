# External Definition File Boosting: SQL, Schema Languages, and String-Literal Cross-References

Change ID: `12mns-enh sql-candidate-window-boosting`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-05-15
Wave: `12mns code-ask-retrieval-quality`

## Rationale

In any project that separates definitions from call sites via string literals rather than imports, semantic search cannot bridge the gap. A TypeScript file that executes `query.text = "select schema.generate_record($1)"` shares no embedding overlap with the SQL file that defines `generate_record`. A GraphQL client that sends `query GetUser { ... }` shares no embedding overlap with the `.graphql` schema file that defines `User`. A gRPC client using a message type by string name shares no overlap with the `.proto` file that defines it. In each case the definition file is invisible to vector search regardless of how relevant it is — the reranker cannot compensate for candidates not in the pool.

The fix is an extensible vocabulary-triggered candidate augmentation step. When query terms indicate a definition-file language is relevant, inject candidates from those file types via keyword search before reranking. The mechanism is defined as a rule table — each rule maps a vocabulary set to a set of file extensions — so new language families (GraphQL, protobuf, OpenAPI) can be added without changing the logic. SQL is the first rule.

## Requirements

1. Define `DEFINITION_BOOST_RULES` as a module-level list of rule dicts, each with keys `vocabulary` (frozenset of trigger terms), `extensions` (list of file extensions to search), and `label` (string for response field). SQL rule: `vocabulary={"sql", "stored procedure", "proc", "migration", "schema", "insert", "query", "database", "db", "routine", "table", "column", "function"}`, `extensions=[".sql"]`, `label="sql"`. The list is ordered; all matching rules fire for a given query.
2. Define `DEFINITION_BOOST_CANDIDATES = 5` as a module-level constant — the maximum candidates injected per rule per query.
3. In `search_combined()`: after the vector fetch, lowercase the query and check intersection with each rule's `vocabulary`. For each matching rule, run `code_keyword_response` using the most specific matching vocabulary term (longest term > 3 characters that appears in the lowercased query, or the full query if none qualify), filtered to the rule's `extensions`. Inject up to `DEFINITION_BOOST_CANDIDATES` results into the candidate pool with `score=0.0` so the reranker evaluates them on content merit only.
4. Injected candidates are subject to normal reranking alongside vector candidates — no special post-rerank treatment.
5. When any rule fires, `search_combined` must include `"definition_boosted": [list of labels that fired]` in its return value (e.g. `["sql"]`). `code_ask_response` must propagate this to the response payload as `definition_boosted`. When no rule fires, the field must be absent.
6. Final result count must not exceed `top_n` regardless of how many candidates were injected.

## Scope

**Problem statement:** Definition files for schema languages (SQL, GraphQL, protobuf, OpenAPI) are referenced from application code via string literals rather than imports, creating a semantic distance gap that prevents them from entering the vector candidate window. The reranker cannot compensate for missing candidates.

**In scope:**

- `DEFINITION_BOOST_RULES` rule table and `DEFINITION_BOOST_CANDIDATES` constant in `server.py`
- SQL rule as the first entry (`.sql` files, proc/table/schema vocabulary)
- Vocabulary-triggered keyword pass and candidate pool injection in `search_combined()`
- `definition_boosted` flag (list of fired rule labels) in `code_ask` response
- Tests in `test_server_tools.py`

**Out of scope:**

- GraphQL, protobuf, OpenAPI rules — architecture supports them; first implementation is SQL only
- Citation-text identifier extraction (scanning citation excerpts for referenced identifiers and searching for their definitions by name) — this is a higher-precision follow-on approach; current change uses vocabulary-triggered query-level search
- Symbol cross-reference index at build time — separate future change
- Applying definition boosting to `docs_search` or `code_search` single-index paths

## Acceptance Criteria

- AC-1: A query containing "stored procedure", "SQL", "schema", or other SQL vocabulary triggers the SQL rule and injects up to 5 `.sql` candidates into the pool with `score=0.0`.
- AC-2: Injected candidates are reranked alongside vector candidates.
- AC-3: `definition_boosted: ["sql"]` appears in the `code_ask` response when the SQL rule fired.
- AC-4: A query with no vocabulary match for any rule does not trigger augmentation; `definition_boosted` is absent from the response.
- AC-5: Final result count does not exceed `top_n`.
- AC-6: Adding a second rule to `DEFINITION_BOOST_RULES` does not require changes to the augmentation logic — only the rule table.

## Tasks

- [ ] Add `DEFINITION_BOOST_RULES` (list of rule dicts) and `DEFINITION_BOOST_CANDIDATES = 5` constants to `server.py`; define the SQL rule as the first entry
- [ ] Add vocabulary detection loop in `search_combined()`: for each rule, check query intersection with rule vocabulary; on match, run `code_keyword_response`, filter to rule extensions, take top `DEFINITION_BOOST_CANDIDATES`, assign `score=0.0`, inject into candidate pool
- [ ] Collect fired rule labels; return `definition_boosted: list[str]` from `search_combined()`; propagate to `code_ask` response
- [ ] Update tests: SQL vocabulary triggers SQL rule; candidates injected with score 0.0; reranker sees augmented pool; `definition_boosted` flag correct; non-matching query produces no augmentation; count ≤ top_n; second rule addition requires no logic change

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| constants | implementer | — | `DEFINITION_BOOST_RULES` and `DEFINITION_BOOST_CANDIDATES` in `server.py` |
| search-combined-augmentation | implementer | constants | vocabulary loop + keyword pass + pool injection |
| code-ask-propagation | implementer | search-combined-augmentation | `definition_boosted` in response |
| tests | implementer | code-ask-propagation | `test_server_tools.py` |

## Serialization Points

- `framework_edit_allowed` gate required for `server.py` and `test_server_tools.py`.
- Coordinate with `12mns-enh question-type-aware-retrieval` and `12mns-enh code-ask-timing-instrumentation` — all three modify `search_combined()` return signature.

## Affected Architecture Docs

`docs/architecture/search-architecture.md` — document the definition-file boosting step in the `search_combined` pipeline; describe the rule table as the extension point for new language families.

## AC Priority

| AC   | Priority  | Rationale |
|------|-----------|-----------|
| AC-1 | required  | SQL vocabulary trigger and `.sql` candidate injection is the core deliverable |
| AC-2 | required  | Injected candidates must enter reranking — score=0.0 without reranking would bypass content evaluation |
| AC-3 | important | `definition_boosted` flag is observability; useful for validation and debugging but not a retrieval correctness gate |
| AC-4 | required  | Non-matching queries must not trigger augmentation — correctness and performance boundary |
| AC-5 | required  | Result count cap at `top_n` is a hard contract — violation breaks downstream consumers |
| AC-6 | required  | Extensibility without logic change is the architecture point — second rule must be addable by table-only edit |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-14 | Change scoped as SQL-specific boost | SQL migration files not surfacing; proc call site and definition have large semantic distance |
| 2026-05-15 | Redesigned as extensible rule table; SQL is first instance | Same semantic distance pattern applies to GraphQL, protobuf, OpenAPI; `DEFINITION_BOOST_RULES` architecture makes future rules additive |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-14 | Vocabulary-triggered keyword pass, not always-on | Adds one keyword search per matching rule; overhead bounded by `DEFINITION_BOOST_CANDIDATES`; only fires when relevant | Always augment with definition file candidates — unnecessary overhead for queries with no schema-language context |
| 2026-05-14 | Synthetic `score=0.0` for injected candidates | Reranker evaluates on content merit without vector proximity bias; 0.0 is below any real cosine score | Fixed mid-range score — arbitrary, would over- or under-represent injected candidates relative to vector results |
| 2026-05-15 | Rule table (`DEFINITION_BOOST_RULES`) over single-language implementation | GraphQL, protobuf, OpenAPI have identical semantic distance problem; designing the extension point now avoids a refactor later | SQL-only constants — simpler now, requires refactor to generalize |
| 2026-05-15 | Query-vocabulary trigger, not citation-text identifier extraction | Vocabulary trigger is simpler and does not require reading citation content; identifier extraction (scanning citations for referenced proc/table names) is higher-precision but a follow-on approach | Citation-text scan — more precise, finds the exact referenced identifier; deferred as follow-on |

## Risks

| Risk | Mitigation |
|------|------------|
| Vocabulary terms too broad (e.g. "function" matches non-schema queries) | Injected candidates receive `score=0.0`; reranker will suppress irrelevant ones; final count capped at `top_n`; latency bounded by `DEFINITION_BOOST_CANDIDATES = 5` |
| Definition file candidates irrelevant to the specific query | Reranker naturally demotes low-relevance candidates; partition to end of results is the worst case, not exclusion |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
