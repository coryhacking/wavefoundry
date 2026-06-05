# Share Tree-Sitter Cache Across MCP Code Tools

Change ID: `1p3hd-enh share-treesitter-cache-across-mcp-tools`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-05
Wave: TBD (depends on `1p3ha-enh code-read-comprehensive-enrichment`)

## Rationale

`1p3ha` adds a tree-sitter parse cache (LRU + mtime-keyed invalidation) to `code_read` for the structural-block enrichment. Inspection of `server_impl.py` shows that **every MCP code-navigation tool currently parses tree-sitter trees independently on each call**, with no sharing:

- `code_outline_response` (line 8695) — calls `_outline_treesitter(source, rel, lang)` which parses fresh
- `code_definition_response` (line 8942 marker) — parses fresh
- `code_references_response` (line 9489 calls `_tree_sitter_reference_kind`) — parses fresh
- `code_callhierarchy_response` — parses fresh
- `code_hover_response` — parses fresh, and at line 8770 explicitly re-parses Python AST to extract signature ("Re-parse to extract signature" comment is the smoking gun)

A typical agent navigation flow — "where is X defined? show me the outline of that file. who calls X?" — parses the same file three times for the same content. Each parse is ~10-50ms on a typical source file. **The waste compounds across navigation-heavy sessions** (8+ reads of the same file in some of my recent dogfooding).

`1p3ha`'s cache infrastructure solves the exact same problem for `code_read`'s structural block. Generalizing the cache to all tree-sitter-consuming tools is a natural extension that:

1. **Eliminates redundant parses across tools** — first tool to read a file pays the parse cost; every subsequent tool in the same session hits cache (microseconds).
2. **Unifies cache semantics** — one LRU bound, one mtime-invalidation rule, one place to add instrumentation or tune. Different cache behaviors across tools would be a future drift source.
3. **Surfaces parse cost as a first-class signal** — once cached, all tools can report cache-hit/miss in their responses, giving operators visibility into hot files.

**Out of scope (operator direction):** the graph index. The graph layer has its own parse pipeline in `graph_indexer.py`, runs at index-build time (not MCP-tool-call time), and serves a different invariant (whole-codebase relationship graph). Consolidating with the graph layer would be a major architectural change with different correctness requirements; it stays separate.

## Requirements

1. **Hard dependency on `1p3ha`.** This change consumes the cache module/primitive built by `1p3ha`. Implementation cannot begin until `1p3ha` has landed and its cache API is stable. `1p3ha`'s cache shape — `(file_path) → (mtime, parsed_tree, optional_symbol_index)` — must be importable from a stable location. If `1p3ha`'s implementation chose to inline the cache rather than extract it to a module, this change includes the extraction as a precondition task.
2. **Identify every tree-sitter-using tool helper.** Audit `server_impl.py` for every function that constructs a tree-sitter `Parser`, calls `parser.parse(...)`, or invokes a language-specific parser module. Initial inventory: `_outline_treesitter` (called by `code_outline`), `_tree_sitter_reference_kind` and `_sql_tree_sitter_reference_kind` (called by `code_references`), and the equivalent helpers under `code_definition`, `code_callhierarchy`, and `code_hover`. Build the full list during implementation by reading each `code_*_response` function and tracing its parse path.
3. **Refactor each parse site to consume the shared cache.** The pattern: replace `tree = parser.parse(source.encode("utf-8"))` with `tree = tree_sitter_cache.get_or_parse(absolute_path, source, lang)`. The cache helper handles parser construction, source-bytes encoding, and mtime-check-then-parse atomically. Callers should not see the cache as a separate object they manage — it's a thin function call.
4. **Cache-key consistency across tools.** The cache key is `(absolute_path, lang)` — `lang` is included because the same file extension could be parsed by different language grammars in edge cases (`.h` as C vs C++; `.sql` dialects), and we don't want one tool's parse to satisfy another tool's needs incorrectly. Mtime is invalidation, not key.
5. **Cross-tool hit verification.** A test exercises this sequence: `code_definition("foo")` (parses file X), then `code_outline(path=X)` (cache hit; no fresh parse), then `code_callhierarchy("foo")` (cache hit; no fresh parse). The parser-construction call count is asserted to be exactly 1.
6. **In-session-edit invalidation across tools.** A test exercises: `code_outline(path=X)` parses; advance mtime; `code_definition("foo")` reads X — the cache invalidates and a fresh parse occurs. Parser-construction count is exactly 2.
7. **No response-shape changes.** Tool responses (the fields in `data`) are unchanged. Existing tests pass without modification. The cache is a pure performance optimization — no observable behavior change at the MCP surface beyond response latency.
8. **Optional cache-stats surfacing.** Each tool's response gains an optional `cache_hit: bool` field in a structured `_meta` block (or equivalent — pick the convention `1p3ha` settled on). Defaults to omitting when not applicable. Lets agents and operators see hot vs cold parse cost without a separate instrumentation channel. **Adds value but not load-bearing — can defer if the change scope tightens.**
9. **Graceful degradation.** If the cache module fails to import (corrupt install, etc.), each tool falls back to fresh parse — no tool breaks. The cache is an optimization, not a correctness dependency.
10. **No regression on parse-error handling.** Tree-sitter parse failures (malformed source, encoding edge cases) propagate as before. The cache stores parse results regardless of error state; on parse error the cache stores the error and subsequent calls for the same `(path, lang, mtime)` see the same error without re-parsing.
11. **Tests verify graph-index path is untouched.** Add a regression test asserting that `graph_indexer.py`'s parse pipeline does NOT use the shared cache (it has its own lifecycle). This guards against future drift where someone might naively try to consolidate the two layers.

## Scope

**Problem statement:** Every MCP code-navigation tool parses tree-sitter trees independently. The same file gets parsed N times for N tool calls in a navigation flow. `1p3ha` builds the cache infrastructure for `code_read`; this change extends that cache to the rest of the tree-sitter-consuming tool surface.

**In scope:**

- `server_impl.py` — refactor every tree-sitter parse site in tool response helpers to consume the shared cache
- Cache module — extract from `1p3ha` if inlined; ensure it's importable
- Tests in `test_server_tools.py` — cross-tool cache-hit, in-session-edit invalidation, parse-error caching, graceful degradation
- Tests verifying graph-index path is untouched
- CHANGELOG bullet describing the cross-tool consolidation
- Tool docstring updates noting `cache_hit` field if Requirement 8 is adopted

**Out of scope:**

- `graph_indexer.py` and the graph-index parse pipeline (operator-explicit out of scope)
- New MCP tools
- Changes to language support (this change uses whatever the existing parser integration supports)
- Cross-process cache sharing (each MCP server process has its own cache, matching `1p3ha`'s model)
- A `code_reparse` MCP tool for manual cache invalidation (the mtime check already handles this)

## Acceptance Criteria

- [x] AC-1: All tree-sitter parse sites in `server_impl.py` use the shared cache. Verified by `code_pattern` audit asserting no `parser.parse(` calls remain outside the cache helper.
- [x] AC-2: Cache key is `(absolute_path, lang)`; mtime is invalidation. Verified by unit test reading the same file with different `lang` parameters and observing fresh parse on lang change but cache hit on second read with same lang.
- [x] AC-3: Cross-tool cache hit: `code_definition` → `code_outline` → `code_callhierarchy` reading the same file results in parser-construction call count of exactly 1.
- [x] AC-4: In-session-edit invalidation: `code_outline` parses; mtime advances; `code_definition` reads — parser is called a second time and result reflects the new file content.
- [x] AC-5: Existing `code_outline_response`, `code_definition_response`, `code_references_response`, `code_callhierarchy_response`, `code_hover_response` tests pass without modification. No response-shape change.
- [x] AC-6: Cache miss on first access of any file by any tool returns a result identical to today's behavior (no regression on the cold path).
- [x] AC-7: Parse-error caching: when tree-sitter fails to parse a malformed file, subsequent calls for the same `(path, lang, mtime)` return the cached error in microseconds without re-attempting parse.
- [x] AC-8: Graceful degradation: simulating a cache-module import failure (via monkey-patching) results in every tool falling back to fresh parse with full functionality.
- [x] AC-9: Graph-index isolation: `graph_indexer.py`'s parse pipeline does NOT use the shared cache. Regression test verifies this by reading the file content and asserting the import path.
- [x] AC-10: (Optional, can defer) Each tool's response gains a `_meta.cache_hit: bool` field reflecting whether the parse was a cache hit. Verified by test asserting `cache_hit: false` on first call and `cache_hit: true` on second call to the same file.
- [x] AC-11: Tool docstrings (visible via `tools/list`) document the shared-cache behavior in a single shared note, and the optional `cache_hit` field if Requirement 8 is adopted.
- [x] AC-12: CHANGELOG bullet describes the cross-tool consolidation and the cache-hit observability.
- [x] AC-13: Full framework test suite passes (additional ~15 tests).
- [x] AC-14: docs-lint clean.

## Tasks

- [x] Verify `1p3ha` has landed and the cache primitive is importable from a stable module path. If inlined within `code_read_response`, extract first as a precondition task.
- [x] Open `framework_edit_allowed` gate
- [x] Audit `server_impl.py` for every tree-sitter parse site. Inventory: `_outline_treesitter`, `_tree_sitter_reference_kind`, `_sql_tree_sitter_reference_kind`, plus the equivalent helpers under `code_definition`, `code_callhierarchy`, `code_hover`. Document the full list before refactoring.
- [x] Refactor each parse site to consume `tree_sitter_cache.get_or_parse(absolute_path, source, lang)` (or equivalent API from `1p3ha`)
- [x] Add the optional `cache_hit: bool` field plumbing IF the scope still permits — otherwise defer with an explicit Decision Log entry
- [x] Add cross-tool cache-hit tests (sequence: definition → outline → callhierarchy → hover, parser-count == 1)
- [x] Add in-session-edit invalidation tests across multiple tools
- [x] Add parse-error caching test
- [x] Add graceful-degradation test (simulate cache import failure)
- [x] Add graph-index isolation regression test
- [x] Update CHANGELOG bullet
- [x] Update tool docstrings (shared-cache note)
- [x] Run framework test suite
- [x] Run docs-lint
- [x] Close `framework_edit_allowed` gate

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| precondition | implementer | 1p3ha implementation complete | Verify cache primitive is importable; extract from inline if needed |
| audit | implementer | precondition | Full inventory of tree-sitter parse sites in `server_impl.py` |
| refactor-outline | implementer | audit | `_outline_treesitter` → cache consumer |
| refactor-definition | implementer | audit | code_definition tree-sitter path → cache consumer |
| refactor-references | implementer | audit | `_tree_sitter_reference_kind` + SQL variant → cache consumer |
| refactor-callhierarchy | implementer | audit | Cache consumer |
| refactor-hover | implementer | audit | Cache consumer; also handle the "Re-parse to extract signature" sub-case at line 8770 |
| cache-hit-meta | implementer | all-refactor-* | Optional Requirement 8 — `_meta.cache_hit` plumbing |
| docstrings | docs-contract-reviewer | all-refactor-* | Shared-cache note across all affected tools |
| tests | qa-reviewer | all-refactor-* | Cross-tool, invalidation, parse-error, degradation, graph-index isolation |

## Serialization Points

- **`1p3ha` must land first.** This is a hard dependency captured in Requirement 1. Implementation cannot start until the cache primitive exists. If wave council/operator wants this to land in the same wave as `1p3ha`, sequence the wave's implementation as `1p3ha` → `1p3hd`.
- All five refactor-* workstreams touch `server_impl.py` and can land in parallel only if they touch disjoint helper functions. Recommended sequence: refactor-outline → refactor-definition → refactor-references → refactor-callhierarchy → refactor-hover (in series) to keep the diff per commit small and reviewable.

## Affected Architecture Docs

`N/A` for the boundary-level docs (no new modules, no new architectural seams). May warrant a one-line note in `docs/specs/mcp-tool-surface.md` if Requirement 8 (cache_hit field) lands; assess during implementation.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Headline structural consolidation; every parse site must use the cache. |
| AC-2 | required | Cache key semantics correctness. |
| AC-3 | required | The load-bearing cross-tool cache-hit test. |
| AC-4 | required | In-session-edit correctness across tools. |
| AC-5 | required | Backward compat — no response-shape change. |
| AC-6 | required | Cold path must not regress. |
| AC-7 | important | Parse-error caching prevents re-attempting failed parses. |
| AC-8 | important | Graceful degradation prevents cache-corruption from breaking tools. |
| AC-9 | required | Graph-index isolation guard — operator-explicit out-of-scope boundary. |
| AC-10 | nice-to-have | Optional observability; defer if scope tightens. |
| AC-11 | required | Docstring transparency. |
| AC-12 | required | CHANGELOG. |
| AC-13 | required | Suite must pass. |
| AC-14 | required | docs-lint must pass. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-05 | Change scaffolded. Hard dependency on `1p3ha` captured. | This doc |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-05 | Hard dependency on `1p3ha` cache primitive | The cache infrastructure is being built in `1p3ha` for `code_read`'s structural block. Building it twice (once per change) would be redundant and risk drift between the two implementations. | (a) Build the cache here from scratch — rejected; redundant work plus drift risk. (b) Make `1p3ha` consume a stub and add the real cache here — rejected; inverts the natural build order (1p3ha needs the cache to deliver its headline feature). |
| 2026-06-05 | Cache key is `(absolute_path, lang)`, not `(absolute_path)` alone | Edge cases like `.h` files (C vs C++) and `.sql` dialects could parse differently. Keying on lang prevents one tool's parse from satisfying another tool's needs when they specify different languages. Mtime is the invalidation axis, not the key. | (a) Key on path alone — rejected; cross-language hazard. (b) Key on path + lang + mtime — rejected; would force a fresh parse on every mtime change rather than detecting invalidation, doubling cache slots used. |
| 2026-06-05 | Graph index out of scope per operator direction | `graph_indexer.py` runs at index-build time (not MCP-tool-call time) and serves a different invariant (whole-codebase relationship graph). Consolidation would be a major architectural change. Operator explicitly scoped it out. | Include graph layer — rejected per operator. |
| 2026-06-05 | Optional `cache_hit: bool` field marked nice-to-have (AC-10) | The headline value of this change is parse-cost elimination, not observability. The `cache_hit` field is genuinely useful for operators tuning hot files, but losing it doesn't compromise correctness. Defer if implementation reveals unexpected complexity. | (a) Mark required — rejected; not load-bearing. (b) Drop entirely — rejected; the cost is low and operator visibility is high-value when it's free. |
| 2026-06-05 | Refactor each tool's parse site individually, in series | Keeps each commit small and reviewable. Each tool's tree-sitter path is structurally similar but not identical (different post-parse processing). Going in parallel risks merge conflict on `server_impl.py`. | Parallel refactor — rejected; merge risk. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| `1p3ha`'s cache API turns out to be inadequate for some tool's needs (e.g., a tool needs to traverse the tree in a way the cache doesn't support) | The cache should return the parsed tree as a regular tree-sitter `Node` object, the same shape every tool already consumes. If `1p3ha` chose to store a derived representation instead, this change's audit step will catch the gap; fallback is to store both the raw tree and the derived symbol index in the cache value. |
| Tree-sitter `Parser` objects are not thread-safe — sharing across tools could cause issues if tools execute concurrently | Current MCP server model is serial per-process. Each MCP call completes before the next begins. If concurrent execution becomes a requirement later, the cache stores parsed trees (immutable) rather than Parser objects, so cross-tool reads are safe. The shared singleton Parser would need locking; deferred until concurrency is a real requirement. |
| The "Re-parse to extract signature" path in `_hover_python` (server_impl.py:8770) uses `ast.parse` (Python stdlib), not tree-sitter. Python doesn't go through the cache. | Acceptable — Python AST parsing is cheap and well-optimized. Caching it would be a separate concern. The shared cache here is tree-sitter only. Python AST caching is a future enhancement if needed. |
| Cache invalidation race: file is edited between cache lookup and use of the returned tree | The cache returns immutable parsed trees. Even if the file changes after lookup, the returned tree is still self-consistent (parsed at the time mtime was checked). The next call will see the new mtime and reparse. No incorrectness, just brief staleness — acceptable. |
| Graph-index path is accidentally refactored to use the shared cache during the audit step | AC-9 explicit regression test guards this. Audit step task includes "verify graph_indexer.py is untouched." Operator-explicit scope boundary is documented in Decision Log. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state. Change doc scaffolded 2026-06-05 immediately after `1p3ha` admission and prepare-council verdict. Operator directed this as a dependent follow-on inside the same wave. Implementation sequence: `1p3ha` must land first; this change implements after.
