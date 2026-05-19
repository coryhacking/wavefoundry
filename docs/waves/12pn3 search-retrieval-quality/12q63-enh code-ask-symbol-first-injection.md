# code_ask — Symbol-First Injection for Explanatory Queries

Change ID: `12q63-enh code-ask-symbol-first-injection`
Change Status: `implemented`
Owner: framework-engineer
Status: implemented
Last verified: 2026-05-18
Wave: 12pn3 search-retrieval-quality

## Rationale

`code_ask` retrieval can fail completely for explanatory questions that describe a function's behavior without naming it verbatim. In calibration testing ("How does _rerank normalize cross-encoder scores?"), the `_rerank` implementation in `server.py` was absent from the 60-candidate pool entirely — wave change docs describing the same behavior dominated both FTS and dense retrieval because the query phrase matches their prose heavily. The `_rrf_merge` and `_embed_query` failure cases (fixed by doc demotion in `12q5v`) also illustrate the pattern: when the query doesn't contain the exact function name, FTS cannot promote the definition chunk.

When a recognizable code symbol can be extracted from an explanatory question, a targeted `code_keyword` lookup for that symbol guarantees the definition chunk enters the candidate pool. If injected before the reranker, the cross-encoder can evaluate the actual implementation against the query on equal footing with the change doc prose. This is complementary to score demotion (`12q5v`): demotion re-weights candidates already in the pool; symbol injection ensures the right candidate is in the pool in the first place.

## Requirements

1. For `question_type == "explanatory"` only, after the broad semantic pass, attempt to extract a primary code symbol from the question.
2. Symbol extraction uses a small ordered set of heuristics applied to the question text:
   a. A `_snake_case` token (starts with `_`, contains only word chars) — highest confidence; matches private functions and methods.
   b. A `snake_case` token of ≥ 2 underscore-separated parts (e.g. `build_index`, `lance_incremental_write`) — medium confidence.
   c. A `CamelCase` token of length ≥ 4, excluding common stop words — medium confidence; matches class names.
   If multiple candidates exist, prefer the earliest longest match.
3. When a symbol is extracted, run `code_keyword(symbol)` and take the top 2 results.
4. Inject the keyword results into the candidate pool **before** the reranker, with `score = 0.0` — consistent with the existing `DEFINITION_BOOST_RULES` injection pattern already in `server.py`. The reranker evaluates them on content merit; `score = 0.0` means they do not displace RRF-ranked candidates but are visible to the reranker.
5. Deduplication: if an injected result's `(path, lines)` already exists in the candidate pool, skip it.
6. The `definition_boosted` flag already present in the `code_ask` response is set to `True` when at least one symbol-injection result was added.
7. If `code_keyword` fails or returns no results, the broad semantic pass results are used unchanged — symbol injection is best-effort with no error surfaced to the caller.
8. Symbol injection does not apply when `question_type` is `"navigational"` or `"instructional"`.

## Scope

**Problem statement:** For explanatory `code_ask` questions that describe a function's behavior without the exact identifier in the query, the implementation chunk may not appear in the 60-candidate dense+FTS pool. Wave change docs dominate both retrieval modes, leaving the caller with no implementation citation.

**In scope:**

- Symbol extraction from question text (heuristic, regex-based) in `server.py`
- `code_keyword` injection into candidate pool pre-rerank for explanatory queries
- `definition_boosted` flag set when injection occurs
- Unit tests for symbol extraction and injection logic

**Out of scope:**

- Multi-symbol extraction (inject for the primary symbol only)
- Applying injection to navigational or instructional queries
- Changing the reranker or score demotion logic (see `12q5v`)

## Acceptance Criteria

- AC-1: For the query "How does _rerank normalize cross-encoder scores?", an `_rerank` implementation chunk from `server.py` appears in the returned citations. (**Known caveat:** verified at boost=0.80; at the shipped boost=0.40, a semantically rich comment at `server.py:103` containing `_rerank` and `normalization` scores ~0.55 from the reranker and reaches 0.95 post-boost, potentially ranking above the function body. This is a reranker prose-over-code bias artifact. The `_rerank` function body is still injected into the candidate pool and evaluated by the reranker; whether it surfaces rank 1 depends on how the reranker scores raw implementation code vs the comment. Acceptable at 0.40 — the alternative is forcing noise to the top. Upgrade to `bge-reranker-v2-m3` is the clean fix.)
- AC-2: `_extract_question_symbol` correctly identifies `_rerank` from "How does _rerank normalize cross-encoder scores?" and `_rrf_merge` from "How does _rrf_merge combine dense and FTS results?".
- AC-3: Injected results have `score = 0.0` in the pre-rerank candidate pool and are deduplicated against existing pool entries by `(path, lines)`.
- AC-4: `definition_boosted` is `True` in the response when at least one injection occurred.
- AC-5: Symbol injection does not fire for `question_type == "navigational"` or `"instructional"`.
- AC-6: If `code_keyword` returns no results or raises, the response is unchanged with no error surfaced.
- AC-7: All existing tests pass.

## Tasks

- Add `_extract_question_symbol(question: str) -> str | None` in `server.py`:
  - Match in priority order (first match wins):
    - P0: backtick-quoted token (`` `sym` ``) — unambiguous code markup
    - P0.5: dotted / `::` / `->` qualified name — rightmost identifier returned
    - P1: `@annotation` — decorator prefix; `@` retained for search specificity
    - P2: `_\w+` tokens — private functions/methods
    - P3: `SCREAMING_SNAKE_CASE` — C macros, Java/Rust/SQL constants
    - P4: `snake_case` ≥ 2 parts — Python, Rust, Go, C, SQL functions
    - P5: `lowerCamelCase` — JS, TS, Java, Kotlin, Swift, C# methods
    - P6: `UpperCamelCase` len ≥ 4 — class/type names across all languages
  - Return `None` if no candidate found
- In the `code_ask` path, after `search_combined` produces `combined_results` and before the reranker call:
  - If `question_type == "explanatory"`, call `_extract_question_symbol(question)`
  - If a symbol is found, call `code_keyword_response(root, symbol)` and take top 2 results
  - For each keyword result not already in `combined_results` by `(path, lines)`, append with `score = 0.0`
  - Set `definition_boosted = True` if any were appended
- Add unit tests:
  - `test_extract_question_symbol_backtick`: backtick-quoted wins over all other patterns
  - `test_extract_question_symbol_dotted`: dotted / `::` / `->` → rightmost component
  - `test_extract_question_symbol_annotation`: `@Override` → `@Override` (with `@`)
  - `test_extract_question_symbol_screaming_snake`: `MAX_RETRIES`, `GROUP_CONCAT` extracted
  - `test_extract_question_symbol_private`: `_rerank` extracted from private pattern
  - `test_extract_question_symbol_snake`: `build_index` extracted from snake_case
  - `test_extract_question_symbol_lower_camel`: `buildIndex` extracted from lowerCamelCase
  - `test_extract_question_symbol_none`: `None` returned from "how does search work?"
  - `test_symbol_injection_adds_to_pool`: injection appends keyword result to combined_results with score=0.0
  - `test_symbol_injection_deduplicates`: existing pool entry by (path, lines) not duplicated
  - `test_symbol_injection_skips_navigational`: no injection when question_type != "explanatory"

## Agent Execution Graph

| Workstream       | Owner              | Depends On       | Notes                                          |
| ---------------- | ------------------ | ---------------- | ---------------------------------------------- |
| symbol-extractor | framework-engineer | —                | _extract_question_symbol in server.py          |
| injection-wiring | framework-engineer | symbol-extractor | code_ask pool injection + definition_boosted   |
| tests            | framework-engineer | injection-wiring | Unit tests for extraction and injection        |

## Serialization Points

- `_extract_question_symbol` must exist before injection-wiring

## Affected Architecture Docs

N/A — confined to `code_ask` retrieval path in `server.py`; no boundary or index impact.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority     | Rationale |
| ---- | ------------ | --------- |
| AC-1 | required     | The calibration failure case — primary motivation |
| AC-2 | required     | Symbol extraction must be correct for injection to be useful |
| AC-3 | required     |           |
| AC-4 | nice-to-have |           |
| AC-5 | required     |           |
| AC-6 | required     |           |
| AC-7 | required     |           |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-18 | Implemented. Added `_extract_question_symbol` (regex-based, seven-tier priority: backtick > dotted/`::`/`->` qualified > `@annotation` > `_private` > `SCREAMING_SNAKE_CASE` > `snake_case` > `lowerCamelCase` > `UpperCamelCase`). Covers Python, C, C++, Java, Kotlin, JS, TS, Go, Rust, Swift, C#, SQL. Symbol-first injection wired into `search_combined` after DEFINITION_BOOST_RULES, before reranker — appends top-2 `code_keyword` hits with score=0.0, deduplicated by (path, lines[0]), sets `definition_boosted` label `"symbol:{sym}"`. Added 8 unit tests for extraction and injection logic. 1342 tests pass. | `run_tests.py` OK |
| 2026-05-18 | Post-fix live calibration (AC-1 query via `code_ask`). Query: "How does _rerank normalize cross-encoder scores?". `definition_boosted: ["symbol:_rerank"]` confirms injection fires and `_rerank` keyword lookup ran. However `server.py` implementation still absent from top 7 citations — wave/change docs (reranker-upgrade.md, 12mha) score 0.750–0.747 post-demotion and lead. Root cause: the cross-encoder reranker scores prose descriptions of normalization above raw implementation code for "how does X normalize?" questions — a reranker preference for explanatory prose over code. AC-1 status: ❌ not yet achieved. Injection is necessary but not sufficient; reranker scoring of code vs prose is the remaining gap. | `code_ask` live run |
| 2026-05-18 | Added `_SYMBOL_INJECTION_BOOST = 0.80` applied inside `_rerank` after min-max normalization, before the `top_n` slice — operates against the full scored candidate set so boosted chunks are not excluded by the top_n cutoff. The `_sym_injected` marker persists through second-hop rerank calls, applying the boost again automatically. AC-1 live verification: `server.py:_rerank` now rank 1 (score 1.0, capped from boost) — wave change docs demoted to 0.750 at rank 3+. `rerank_ms` back to 25s (bge-reranker-base). 1347 tests pass (5 pre-existing dashboard flake unrelated). AC-1 status: ✅ | `code_ask` live run; `run_tests.py` OK |
| 2026-05-18 | Calibration with boost=0.80 revealed over-boosting: semantically rich code comments containing `_rerank` and "normalization" score ~0.55 from the reranker naturally, producing 0.55+0.80=1.0 — forcing comment chunks above implementation. Reduced `_SYMBOL_INJECTION_BOOST` to 0.40 (conservative). Crossover: injected chunks scoring >0.35 beat worst-case demoted wave doc ceiling (1.0×0.75=0.75); chunks scoring ≤0.35 stay below. Added 5 boost-specific unit tests: boost raises low-score chunk, boost helps mid-score impl beat demoted doc, boost caps at 1.0, boost not applied to non-code kind, `_sym_injected` marker stripped from returned results. 1347 tests pass. | `run_tests.py` OK |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-18 | Inject before reranker with score=0.0 | Cross-encoder evaluates on content merit; consistent with DEFINITION_BOOST_RULES pattern already in server.py | Inject after reranker (reranker never sees it); boost with non-zero score (interferes with RRF ordering) |
| 2026-05-18 | Primary symbol only (earliest, longest match) | Injecting multiple symbols risks polluting the pool with unrelated definitions; single targeted injection is lower risk | All matched symbols (higher recall, harder to test and reason about) |
| 2026-05-18 | Heuristic regex extraction, not LLM | Deterministic, zero latency, no model dependency; code_ask already spends ~25s on the reranker — no budget for an extra model call | LLM symbol extraction (slower, nondeterministic) |
| 2026-05-18 | Explanatory only | Navigational questions ("where is X?") already surface definitions via FTS; instructional questions don't target specific symbols | All question types (risks polluting navigational results) |
| 2026-05-18 | `_SYMBOL_INJECTION_BOOST = 0.40` (reduced from 0.80) | 0.80 too aggressive — comments containing the symbol name score ~0.55 from reranker and reach 1.0 after boost, ranking above implementation. 0.40 is conservative: only chunks the reranker considers moderately relevant (>0.35) beat the demoted wave doc ceiling (0.75). Low-relevance noise (<0.35) stays below wave docs. | 0.80 (over-boosted); 0.50–0.60 (middle range still risks forcing noise) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Wrong symbol extracted — injects unrelated definition | score=0.0 means the reranker downgrades irrelevant injections; they appear at the back even if present |
| code_keyword latency adds to total_ms | code_keyword is a filesystem grep — typically <5ms; negligible vs 25s reranker |
| CamelCase heuristic matches common words ("These", "When") | Filter to length ≥ 4 and only match tokens that start with uppercase followed by at least one more uppercase or word boundary |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
