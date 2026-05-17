# Two-Hop Symbol Expansion for Multi-Layer Call Chains

Change ID: `12n0e-enh two-hop-symbol-expansion`
Change Status: `complete`
Status: complete
Owner: Engineering
Last verified: 2026-05-15

## Context

Documented in `docs/waves/12mns code-ask-retrieval-quality/12mns-enh dynamic-vector-top-k.md` Decision Log (2026-05-15) as a follow-on to the dynamic `VECTOR_TOP_K` change. The `VECTOR_TOP_K_EXPLANATORY = 60` wider pool improves recall for multi-hop questions at the cost of 50% higher rerank latency. Two-hop symbol expansion is a complementary, more targeted approach.

## Rationale

Field testing on a TypeScript/CDK monorepo revealed that multi-hop explanatory questions ("how does a new tenant get created?") require tracing 4+ layers: API route → handler → service → repository → SQL schema. The dynamic `VECTOR_TOP_K_EXPLANATORY = 60` wider candidate pool improves recall at the first hop but is query-blind — all 60 candidates are drawn by the original question, not by what was actually found. Two-hop expansion is targeted: it extracts symbol names from the first-hop citations and runs a secondary keyword retrieval pass for their definitions, reaching layers the original query vocabulary cannot reach.

## Problem Statement

For explanatory questions that trace a call chain across multiple layers ("how does a new tenant get created?", "how does billing handle a failed charge?"), the vector search may miss the deepest layers. Typical failure mode: the API handler and service layer surface in the top-5 vector candidates, but the repository layer and SQL schema do not — because those files share less lexical overlap with the query than the shallower layers.

The current mitigation (wider `VECTOR_TOP_K`) helps but is uniform: all 60 candidates per index are drawn by the original query, not by what was actually found at the first retrieval hop.

## Proposed Approach

Two-hop expansion: after the first rerank pass produces top citations, extract **referenced symbol names** from those citations using regex over the plain-text excerpts already in memory, then run a secondary keyword retrieval pass for their definitions.

**Pipeline order** (slots into `search_combined` between first rerank and `_partition_infra`):

1. **First hop**: vector fetch → definition-boost injection → first rerank → top results
2. **Symbol extraction**: parse the top-3 reranked non-infra citation texts for function calls, method invocations, imported names, and SQL EXEC/CALL references; use tree-sitter (already a runtime dependency) when the language is supported, regex otherwise; filter and cap at `MAX_SYMBOLS_EXTRACTED = 5`
3. **Second hop**: for each extracted symbol, call `code_keyword_response(root, symbol)` and collect up to `DEFINITION_BOOST_CANDIDATES` (5) results per symbol, globally capped at `MAX_SECOND_HOP_CANDIDATES = 10`; inject as candidates with `score=0.0`
4. **Deduplicate**: remove second-hop candidates whose `(path, lines[0])` is already present in the first-hop pool before combining
5. **Second rerank**: re-run `self._rerank(query, combined_pool, top_n)` — cross-encoder scores second-hop candidates against the original query
6. **`_partition_infra`**: runs after the second rerank, as today — infra-layer files demoted regardless of which hop they arrived from
7. **Return**: final merged result set bounded by `top_n`; `second_hop_symbols` carries the symbols that triggered retrieval

**Gate condition**: steps 2–6 are skipped when `question_type != "explanatory"` or the cross-encoder reranker is unavailable (RRF fallback path). Two-hop without a reranker produces unpredictable ordering and is not useful.

## Why This Is Better Than Wider TOP_K

| Dimension | Wider TOP_K | Two-hop expansion |
|---|---|---|
| Mechanism | Uniform widening | Query-directed, content-driven |
| Latency cost | Fixed (~50% rerank increase) | Variable (depends on citation density) |
| Precision | Same query, more noise possible | Second-hop is targeted to extracted symbols |
| Complexity | Trivial (one constant) | Requires citation-text extraction + secondary retrieval |

The approaches are complementary. Wider TOP_K casts a broader net on the first hop; two-hop expansion follows the specific references found.

## Acceptance Criteria

- AC-1: For `question_type == "explanatory"` with the cross-encoder reranker available, `search_combined` extracts symbol names from the top-3 non-infra reranked citations and performs a second `code_keyword_response` retrieval pass for each extracted symbol. For all other question types or when the reranker is unavailable, the second hop is skipped entirely.
- AC-2: Second-hop candidates (injected with `score=0.0`) are deduplicated against the first-hop pool by `(path, lines[0])`, combined into a single pool, and re-ranked by the cross-encoder against the original query before top-N selection. The second pass is a full rerank, not a positional append.
- AC-3: Symbol extraction is bounded by `MAX_SYMBOLS_EXTRACTED = 5` (per invocation); second-hop keyword retrieval is bounded by `MAX_SECOND_HOP_CANDIDATES = 10` (total across all symbols, regardless of per-symbol `DEFINITION_BOOST_CANDIDATES` cap). Both constants are defined at module level in `server.py`.
- AC-4: When regex extraction yields no symbols from the top citations (e.g. purely prose excerpts with no callable syntax), `search_combined` returns first-hop results unchanged — no second retrieval pass, no change to `second_hop_symbols` (empty list).
- AC-5: `search_combined` return tuple is extended to include `second_hop_symbols: list[str]` — the deduplicated list of symbol names that triggered second-hop retrieval. Emitted in `code_ask` response payload alongside `definition_boosted`. Empty list when the second hop was skipped or produced no candidates.
- AC-6: `search_combined` return tuple includes `symbol_extraction_method: str` — the extraction method used for the second-hop symbol pass. Values: `"ast"` (Python stdlib AST or tree-sitter produced at least one symbol), `"regex"` (no TS-eligible language present; regex is the expected extractor), `"regex_fallback"` (TS-eligible language present but tree-sitter unavailable or failed; regex ran as degradation), `"none"` (second-hop gate not triggered, or all citations were infra-filtered before extraction). `"regex_fallback"` on a TS-eligible codebase surfaces silent grammar degradation. Emitted in `code_ask` response when not `"none"`.

## AC Priority

| AC   | Priority  | Rationale |
|------|-----------|-----------|
| AC-1 | required  | Gate condition and trigger logic — the core deliverable; wrong gate means wrong queries get expanded or expansion is skipped entirely |
| AC-2 | required  | Full re-rerank (not positional append) — without this, second-hop candidates are always ranked below first-hop regardless of relevance |
| AC-3 | required  | Bounded extraction and retrieval caps must be constants in `server.py`; without them latency is unbounded |
| AC-4 | required  | No-op path — must not modify results when no symbols are extracted; regression risk |
| AC-5 | required  | `second_hop_symbols` field in response — enables observability and testing; without it AC-1 and AC-3 cannot be verified by callers |
| AC-6 | required  | `symbol_extraction_method` surfaces extraction quality — `"ast"` confirms structured parse succeeded; `"regex_fallback"` on a TS-eligible codebase signals grammar degradation; `"regex"` is expected when no TS-eligible language present; `"none"` when no extraction was attempted |

## Scope

**In scope:**
- `_extract_symbols_from_citations(citations: list[dict], max_symbols: int) -> tuple[list[str], str]` — module-level helper in `server.py`, returns `(symbols, method)`, alongside `_classify_question` and `_partition_infra`
- `MAX_SYMBOLS_EXTRACTED = 5` and `MAX_SECOND_HOP_CANDIDATES = 10` constants in `server.py`
- Second-hop retrieval and second rerank inside `search_combined()`
- `second_hop_symbols` and `symbol_extraction_method` fields in `search_combined` return tuple and `code_ask` response
- Tests in `test_server_tools.py`

**Out of scope:**
- Tree-sitter language support beyond the chunker's existing parser stack (Python, JS/TS, Java, C#) — no new tree-sitter grammars added
- Two-hop for navigational or instructional questions
- Two-hop in the RRF fallback path (reranker unavailable)
- Per-language symbol extraction tuning beyond the baseline regex patterns

## Implementation Notes

**Symbol extraction** (applied to raw `r["text"]` from result dicts, not truncated citation excerpts):

Primary — tree-sitter where the language is supported (Python, JS/TS, Java, C# — languages already handled by the chunker's parser stack). Extract: function call targets, method invocations, import names. Tree-sitter gives accurate parse boundaries and avoids false positives from string literals or comments.

Fallback — regex for unsupported languages or when tree-sitter parse fails:
- Function/method calls: `r'\b([A-Za-z_][A-Za-z0-9_]{3,})\s*\('`
- SQL EXEC/CALL: `r'\b(?:EXEC|EXECUTE|CALL)\s+([A-Za-z_][A-Za-z0-9_.]{3,})\b'`
- Imports: `r'\bimport\s+([A-Za-z_][A-Za-z0-9_]+)'`

Post-filter (both paths): deduplicate, enforce minimum length ≥ 4, remove common built-in names (`get`, `set`, `run`, `init`, `main`, `self`, `this`, `true`, `false`, `null`, `new`, `return`, `create`, `update`, `delete`, `list`, `find`), cap at `MAX_SYMBOLS_EXTRACTED`.

**Extract from non-infra citations only**: filter the top-3 reranked results through `INFRASTRUCTURE_PATH_SEGMENTS` before extracting — infra-layer files import many application symbols and would bias second-hop expansion toward wiring/routing files.

**Naming**: place `_extract_symbols_from_citations` at module level alongside `_classify_question` (~line 7083) and `_partition_infra`.

## Dependencies

- Requires `12mns-enh question-type-aware-retrieval` (complete — `question_type` param in `search_combined`)
- Requires `12mns-enh sql-candidate-window-boosting` (complete — establishes the `score=0.0` injection and `DEFINITION_BOOST_CANDIDATES` pattern this extends)
- Tree-sitter parser stack (Python, JS/TS, Java, C#) used at query time for primary symbol extraction — already a runtime dependency via the chunker; `docs/architecture/domain-map.md` must be updated to document the new query-time coupling from the MCP Server domain to the chunker subsystem

## Risks

| Risk | Mitigation |
|---|---|
| Duplicate candidates waste reranker slots | Deduplicate by `(path, lines[0])` before second rerank — implemented in AC-2 |
| Infra-citation extraction bias | Extract from non-infra citations only — filter by `INFRASTRUCTURE_PATH_SEGMENTS` before extracting symbols |
| Additive latency on explanatory path | Explanatory path is already 50% heavier from dynamic TOP_K; second rerank on up to 10 extra candidates adds further. GPU is the assumed execution environment (consistent with `12mns-enh dynamic-vector-top-k` deferral note). CPU timing will be logged via `rerank_ms`; if unacceptable, gate second hop behind a config flag. |
| Symbol names too generic → broad keyword matches | Blocklist of common built-ins + minimum length ≥ 4; cap at `MAX_SECOND_HOP_CANDIDATES = 10` globally |
| Second-hop candidates dominate results | All candidates scored by cross-encoder against original query; `score=0.0` injection means content merit determines promotion |

## Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-05-14 | Defer two-hop expansion; ship wider TOP_K first | TOP_K increase is uniform and simple; two-hop requires citation-text parsing and secondary retrieval pass — validate TOP_K approach first, then add two-hop as a precision layer |
| 2026-05-15 | Document as follow-on plan | Both approaches are complementary; two-hop is the next iteration after TOP_K is validated on GPU hardware |
| 2026-05-15 | Tree-sitter as primary, regex as fallback | Tree-sitter (already a runtime dependency) gives accurate parse boundaries and avoids false positives from string literals/comments. Regex covers unsupported languages. Architecture-reviewer required documenting the new query-time coupling in `domain-map.md` — added as a task. |
| 2026-05-15 | Extract from top-3 non-infra citations, not all `top_n` | First-hop precision falls off after position 3; infra-layer citations import too many application symbols and bias expansion toward wiring files (design feasibility review finding) |
| 2026-05-15 | Second pass is a full re-rerank, not positional append | Cross-encoder must evaluate second-hop candidates against the original query to score them on content merit; positional append would always rank them below first-hop results regardless of relevance |
| 2026-05-15 | `second_hop_symbols` is a new field, not an alias for `definition_boosted` | `definition_boosted` has a defined meaning (vocabulary-triggered schema file injection); conflating would confuse callers and make telemetry ambiguous |
| 2026-05-15 | Two values: `"ast"` / `"regex"` (plus `"none"` for no extraction) | Collapses tree-sitter vs Python AST distinction — callers only need to know whether structured parsing succeeded, not which engine; `"ast"` covers both; `"regex"` remains the degradation signal; `"none"` distinguishes infra-filtered-all-citations from the other two | Three values (`"treesitter"` / `"python_ast"` / `"regex"`) — over-specified; callers rarely need the engine distinction, and `python_found=True` even on regex fallback made `"python_ast"` semantically inaccurate |
| 2026-05-15 | `"none"` returned by `_extract_symbols_from_citations` when `top = []` (all citations infra-filtered) | Prevents false `"regex"` emission when no extraction ran; callers see field absent in response (matches gate-not-triggered semantics) | `"regex"` on empty top — bug: implies regex ran when it did not; misleads callers about extraction quality |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-15 | Pre-implementation review completed | Architecture: approved-with-notes (medium — tree-sitter coupling risk resolved); Design feasibility: needs-refinement — ACs tightened, missing risks added, blocking tree-sitter dependency dropped; change doc updated to reflect all findings |
| 2026-05-15 | Implemented AC-6: `symbol_extraction_method` field added | `_extract_symbols_from_citations` returns `(list[str], str)`; `search_combined` return extended to 7-tuple; `code_ask` response emits field when not `"none"`; new test `test_symbol_extraction_method_regex_when_treesitter_unavailable` verifies degradation detection; 1252 tests pass |
| 2026-05-15 | Simplified to `"ast"` / `"regex"` / `"none"`; fixed two bugs from council red-team review | Collapsed `"treesitter"` / `"python_ast"` into `"ast"` (callers need structured-vs-regex, not engine identity); fixed `top = []` → `"none"` (was incorrectly `"regex"`); fixed Python AST fallback tracking (`ast_succeeded` only flips on actual AST output, not citation presence); new test `test_symbol_extraction_method_none_when_all_citations_infra_filtered` verifies empty-top path; 1253 tests pass |
| 2026-05-15 | Refined to `"ast"` / `"regex"` / `"regex_fallback"` / `"none"`; addressed low-severity follow-ons | Split `"regex"` into `"regex"` (no TS-eligible language; expected path) and `"regex_fallback"` (TS-eligible present but grammar unavailable — actionable degradation signal); added `ts_eligible_seen` tracking flag in `_extract_symbols_from_citations`; narrowed `"find"` / `"locate"` in `_classify_question` navigational signals to multi-word phrases (`"find the"`, `"find where"`, `"locate the"`) to prevent false navigational classification; added `test_symbol_extraction_method_ast_when_python_extraction_succeeds` and renamed `test_symbol_extraction_method_regex_when_treesitter_unavailable` → `test_symbol_extraction_method_regex_fallback_when_treesitter_unavailable`; 1300 tests pass |
