# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-15

wave-id: `12mns code-ask-retrieval-quality`
Title: Code Ask Retrieval Quality

## Changes

Change ID: `12mns-enh question-type-aware-retrieval`
Change Status: `complete`

Change ID: `12mns-enh code-ask-timing-instrumentation`
Change Status: `complete`

Change ID: `12mns-enh retrieval-agent-guidance`
Change Status: `complete`

Change ID: `12mns-enh sql-candidate-window-boosting`
Change Status: `complete`

Change ID: `12mns-enh dynamic-vector-top-k`
Change Status: `complete`

Change ID: `12n0e-enh two-hop-symbol-expansion`
Change Status: `complete`

Change ID: `12n5x-enh code-keyword-search-multi-query`
Change Status: `complete`

Change ID: `12n5x-enh code-constants-search`
Change Status: `complete`

Change ID: `12n63-maint code-keyword-rename`
Change Status: `complete`

Change ID: `12n63-enh code-pattern`
Change Status: `complete`

Change ID: `12n63-enh code-outline`
Change Status: `complete`

## Objective

Improve `code_ask` retrieval quality based on real-world observations from a TypeScript/CDK monorepo. Five targeted changes: question-type-aware candidate weighting (CDK construct path penalties for explanatory questions), per-query timing instrumentation, agent guidance for layer recognition and call-chain tracing, SQL/migration file candidate boosting, and dynamic VECTOR_TOP_K scaling.

Completed At: 2026-05-15

## Wave Summary

Five changes derived from post-ship field feedback on `12mha-enh semantic-search-reranker`. Scoped to be framework-agnostic: infrastructure path patterns generalized beyond CDK to cover Terraform, Spring, Express/NestJS; SQL boosting redesigned as an extensible definition-file rule table (SQL first, GraphQL/protobuf/OpenAPI addable without logic changes); agent guidance covers the general string-literal cross-reference pattern. **Phase 1 (P1):** (1) question-type-aware retrieval — scaffolding-layer post-rerank partition for explanatory questions + RRF weight bias for navigational questions; (2) timing instrumentation — `vector_ms`, `rerank_ms`, `total_ms` in `code_ask` response and server log; (3) retrieval agent guidance — layer recognition heuristic (framework-agnostic), call-chain obligation, confidence interpretation note, definition-file follow-up pattern in `code-insight-agent.md` and `AGENTS.md`. **Phase 2 (P2):** (4) definition file boosting — extensible rule table; SQL rule injects `.sql` candidates on schema/proc vocabulary match; (5) dynamic VECTOR_TOP_K — scale candidate window to 60 per index for explanatory/flow questions; requires timing data from change 2 before delivery.

## Journal Watchpoints

- **Watchpoint:** `framework_edit_allowed` gate required for all code changes: `server.py`, `test_server_tools.py`.
- **Watchpoint:** Phase 1 changes (1, 2, 3) are independent and can be implemented in parallel. Phase 2 depends on timing data from change 2 to validate latency impact.
- **Sequencing:** Implement `12mns-enh question-type-aware-retrieval` before `12mns-enh dynamic-vector-top-k` — TOP_K scaling interacts with the same `search_combined` call path.

## Review Evidence

- wave-council-readiness: approved (2026-05-15 — full coverage of 8 feedback issues confirmed; 3 blocking findings resolved: `INFRASTRUCTURE_PATH_SEGMENTS` generalized to framework-agnostic scaffolding-layer frozenset; `sql-candidate-window-boosting` redesigned as extensible `DEFINITION_BOOST_RULES` rule table with SQL as first instance; agent guidance Problems 1 and 4 generalized to scaffolding-layer concept and string-literal cross-reference pattern; two-hop expansion documented in `dynamic-vector-top-k` Decision Log)
- architecture-reviewer: approved-with-notes (2026-05-15 — severity: low; no layer, boundary, or ADR violations; one low-severity finding on `definition_boosted` label firing when zero candidates injected — fixed in post-review pass; all arch docs consulted)
- code-reviewer: approved-with-notes (2026-05-15 — severity: medium finding on `definition_boosted` label always appended regardless of injection success — fixed; infra partition uses dict equality instead of index-based partition — flagged low, follow-on; `"where"` classifier too broad — flagged low, follow-on; `"function"` in SQL vocab causes false positives — flagged low, follow-on; RRF fallback skips explanatory partition — flagged low, follow-on; vacuous test assertion on infra partition — fixed; 1237/1237 tests pass after fixes)
- qa-reviewer: approved (2026-05-15 — 27/28 ACs verified; 26 by passing tests, 7 by doc verification, 1 hardware-gated with CPU benchmark; one non-blocking gap: timing AC-4 server log line unverified by test, priority "important"; 1237/1237 tests pass)
- wave-council-delivery: approved (2026-05-15 — all required ACs covered; required fix applied and verified; reranker model swapped to MiniLM-L6 post-review; live MCP benchmark confirms 5–6× rerank speedup with equivalent quality)
- wave-council-delivery-2: approved-with-notes (2026-05-15 — session 2 changes: `12n63-maint code-keyword-rename`, `12n63-enh code-pattern`, `12n63-enh code-outline`, `12n5x-enh code-keyword-search-multi-query` (AC gaps), `12n5x-enh code-constants-search` (AC gaps); one blocker resolved: AGENTS.md named `code_keyword` while server.py still registered `code_keyword_search` — fixed by implementing rename immediately; medium advisories recorded: ReDoS risk in `code_pattern` requires concrete mitigation before implementation, silent tree-sitter fallback in `code_outline` is undetectable by callers, explanatory classifier default causes two-hop to fire on most queries; all required ACs covered; 1251 tests pass; AC-3a and AC-3b grep clean)
- wave-council-delivery-3: approved (2026-05-15 — `symbol_extraction_method` field on `12n0e`; architecture: approved-with-notes (low — 7-tuple shape is precedent-consistent; `"regex"` ambiguity between degradation and non-TS-eligible noted as follow-on); QA: approved-with-notes (low — `"regex"` degradation path and `"none"` gate path well-covered; `"ast"` pin follow-on); reality-checker: two bugs identified and fixed before merge — `top=[]` emitted `"regex"` when no extraction ran (fixed: now `"none"`), Python `python_found` flag flipped on citation presence not AST output (fixed: `ast_succeeded` tracks actual output); user-directed simplification to `"ast"`/`"regex"`/`"none"` resolved all three findings; 1253 tests pass)
- follow-on-fixes: complete (2026-05-15 — addressed 3 low-severity findings from code-reviewer and council delivery-3: (1) narrowed `"find"`/`"locate"` in `_classify_question` to multi-word phrases to prevent false navigational classification; (2) split `"regex"` into `"regex"` vs `"regex_fallback"` in `_extract_symbols_from_citations` — `"regex_fallback"` signals TS-eligible language present but grammar unavailable, `"regex"` means no TS-eligible language; (3) added `test_symbol_extraction_method_ast_when_python_extraction_succeeds` test pinning `"ast"` path; findings #1, #3, #4 from code-reviewer confirmed already resolved in current code; 1300 tests pass)
- operator-signoff: approved (2026-05-15)

## Dependencies

- Depends on `12mha-enh semantic-search-reranker` (wave `12mc3`) — complete.
