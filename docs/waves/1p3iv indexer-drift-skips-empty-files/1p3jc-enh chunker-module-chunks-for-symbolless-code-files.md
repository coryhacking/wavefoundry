# Chunker emits module-summary chunk for code files with no extractable symbols

Change ID: `1p3jc-enh chunker-module-chunks-for-symbolless-code-files`
Change Status: `implemented`
Owner: framework-maintainer
Status: implemented
Last verified: 2026-06-05

## Rationale

The chunker walks each code file's AST (Python via `ast`, other languages via tree-sitter) and emits chunks only for symbol-defining nodes — `FunctionDef`, `AsyncFunctionDef`, `ClassDef`, and equivalents. Files with no extractable symbols emit zero chunks. This is correct for genuinely empty files (the 1p3iw fix handles those) but produces a coverage gap for files with real content:

- Python `__init__.py` re-export points: `from .cli import main; __all__ = ["main"]`
- TypeScript/JavaScript barrel files (`index.ts`): `export * from "./foo"; export { Bar } from "./bar"`
- Go single-file packages: package declaration + imports + a couple of constants, no funcs
- Rust `mod.rs` re-exports: `pub mod foo; pub use foo::Bar`
- Java/Kotlin `package-info.java` style files
- Configuration constants modules in any language (a file that's just `MAX_X = 100; MAX_Y = 200; ...`)

These files are SEMANTICALLY MEANINGFUL — they declare a package's public surface, route exports between modules, or hold project-wide constants. Today `code_search` (semantic, chunk-backed) misses them entirely; only `code_keyword` (text-backed via ripgrep) and `code_read` (path-direct) can surface them. An agent asking "what does the wave_lint_lib package re-export?" or "where are our re-export points?" gets zero useful semantic-search results.

Surfaced as a dogfood observation during 1p3iv close: `wave_lint_lib/__init__.py` was correctly recorded as `chunks_emitted: 0` per the new 1p3iw schema, but the operator noted the file has a real import statement — confirming the chunker's symbol-only design is a deliberate gap, not a bug, but worth closing for semantic-search coverage of re-export idioms.

## Requirements

1. When the chunker processes a code file (Python or tree-sitter-supported) and would otherwise emit zero chunks AND the file has non-whitespace content, emit one "module summary" chunk.
2. Module-summary chunk content includes: import / `use` / `import` statements (the import block), module-level constants and assignments (e.g., `__all__`, `MAX_X = ...`), and any re-export / public-surface declarations (`pub use`, `export *`, `export { ... } from`).
3. Chunk is tagged `kind="code"`, language-tagged for the file's language, with `section="<file_stem>"` and `id="<path>::__module__"`.
4. Multi-language scope: the implementation walks each language's relevant top-level node kinds via per-language tree-sitter queries (Python uses `ast` per existing convention). At minimum: Python, TypeScript, JavaScript, Go, Rust, Java, Kotlin, C#. Other languages get the same treatment if their tree-sitter parser is already loaded.
5. Compatibility with 1p3iw `chunks_emitted` tracking: a file emitting only the module-summary chunk records `chunks_emitted: 1` in `meta.json`; the drift check no longer flags it as drifted. Files that genuinely emit zero chunks (truly empty, all-whitespace, all-comments, marker-region-dominated) still record `chunks_emitted: 0` and stay skipped.
6. `CHUNKER_VERSION` bumps so `indexer.py` auto-escalates to a full rebuild on the version mismatch — consumer indexes regenerate to include the new module-summary chunks transparently on upgrade.
7. Test coverage: per-language fixtures verifying (a) a re-export file emits exactly one module-summary chunk, (b) a file with both symbols AND module-level content emits the symbol chunks but NOT a module-summary (the symbols are the searchable surface), (c) a truly empty file still emits zero chunks, (d) a file dominated by `<!-- waveframework:* begin --> ... <!-- end -->` marker regions emits zero chunks (operator-visible vs not).

## Scope

**Problem statement:** Code files with no extractable symbols but real content are invisible to `code_search`, the agent's primary semantic-navigation tool. The chunker's symbol-only design excludes a real class of files (re-exports, barrel files, constants modules) that agents would benefit from finding via intent queries.

**In scope:**

- Chunker emits module-summary chunk in the symbolless-code-file case.
- Multi-language coverage (Python + tree-sitter-supported languages).
- `CHUNKER_VERSION` bump.
- Per-language tests + a cross-language integration test.
- CHANGELOG bullet under the version this change ships in.

**Out of scope:**

- Refactoring the chunker's symbol-walking logic. The module-summary chunk is a fallback path that fires only when symbol extraction yields zero chunks.
- Embedding-model / reranker work. The module-summary chunk uses the existing chunk schema and feeds the existing embedder pipeline.
- Doc-file (`.md`, etc.) handling. Doc chunkers already handle their own "empty section" cases.
- Backporting the chunk to older `CHUNKER_VERSION` consumers. The version bump triggers consumer rebuild automatically.

## Acceptance Criteria

- [x] AC-1: Python `__init__.py` containing only `from .x import y; __all__ = ["y"]` emits exactly one chunk with `kind="code"`, `id` matching `*::__module__`, text containing the import line and `__all__`.
- [x] AC-2: TypeScript `index.ts` containing only `export * from "./foo"; export { Bar } from "./bar"` emits exactly one chunk with `kind="code"`, language="typescript", text containing both export lines.
- [x] AC-3: A Python file with at least one `FunctionDef` AND module-level imports emits the function chunk(s) but NOT a separate module-summary chunk (the function is the searchable surface).
- [x] AC-4: A truly empty file (zero bytes or all-whitespace) emits zero chunks. Verified by parity with 1p3iw test fixtures.
- [x] AC-5: A file dominated by marker regions (`<!-- waveframework:* begin --> ... <!-- end -->`) with no other content emits zero chunks. Marker-region content is renderer-owned and should not be semantically searchable.
- [x] AC-6: `chunks_emitted` recorded in `meta.json` reflects the new emission count (1 for symbolless-with-content files, 0 for truly empty).
- [x] AC-7: `CHUNKER_VERSION` bumped; `indexer.py` auto-escalates incremental updates to full rebuild on the mismatch (existing behavior unchanged; just verified here).
- [x] AC-8: Multi-language test coverage spans Python + at least 4 tree-sitter languages from the supported set (TypeScript, JavaScript, Go, Rust, Java, Kotlin, C#).
- [x] AC-9: Existing chunker tests pass without modification.
- [x] AC-10: `docs-lint` returns clean.

## Tasks

- [x] Audit existing chunker per-language code paths (Python `ast` + tree-sitter queries) to identify the "zero symbol chunks emitted" branch in each.
- [x] Add module-summary fallback emission after the symbol-extraction pass per language.
- [x] Identify the right text content per language (Python: imports + `__all__` + top-level constants; TS/JS: export statements + imports; Go: package decl + imports; Rust: `mod` / `use` declarations; etc.). Reasonable approach: take all non-comment top-level lines.
- [x] Bump `CHUNKER_VERSION` and update the regression test that asserts the value.
- [x] Add per-language test fixtures + tests for the AC scenarios.
- [x] Add CHANGELOG bullet under the version this change ships in.

## Affected Architecture Docs

N/A — confined to chunker internals; no domain map / layering / cross-cutting impact. The change is an emission-rate improvement, not a contract change.

## AC Priority


| AC    | Priority   | Rationale |
| ----- | ---------- | --------- |
| AC-1  | required   | Python is the largest re-export use case in this repo; the load-bearing test. |
| AC-2  | required   | TypeScript barrel files are the most common cross-language case for the same idiom. |
| AC-3  | required   | Symbol-path regression guard — files with symbols must not produce noise from the new fallback. |
| AC-4  | required   | Compatibility with 1p3iw drift convergence. |
| AC-5  | required   | Marker-region content stays renderer-owned and out of semantic search. |
| AC-6  | required   | Drift-detection field stays accurate after the new emission. |
| AC-7  | required   | Consumer indexes pick up the new behavior on upgrade without manual reindex. |
| AC-8  | important  | Multi-language coverage; degenerates to "non-comment top-level lines" fallback so unscoped languages still benefit. |
| AC-9  | required   | No regression in the existing 2688-test suite. |
| AC-10 | required   | docs-lint clean. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Module-summary chunks duplicate content already covered by function/class chunks → noise in semantic search results. | Strict "only emit when zero symbol chunks were produced" gate. A file with even one function/class gets no module-summary chunk. |
| Multi-language coverage is uneven — Python + tree-sitter ts/js/go/rust covered well, exotic languages (Erlang, Lisp, Haskell) may have parsers but no module-summary heuristic. | The fallback is "take all non-comment top-level lines"; works as a degenerate case even when language-specific heuristics aren't tuned. Per-language refinement can come incrementally. |
| `CHUNKER_VERSION` bump forces a full reindex for every consumer on upgrade — cost spike on large repos. | Existing behavior; consumer indexes regenerate transparently via the auto-escalate path in `indexer.py:build_index`. Acceptable per the existing chunker-bump pattern. |


## Progress Log


| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-06-05 | Implementation-review fixes landed: symbolless fallback chunks now use the admitted module chunk shape (`kind="code"`, `id="<path>::__module__"`, `section="<file_stem>"`) and marker-region-only content now emits zero chunks before dispatch. | `test_chunker.py SymbolessCodeFileSummaryTests` passes; `test_indexer.py LanceDriftDetectionTests` passes; `python3 .wavefoundry/framework/scripts/run_tests.py` passes (2702 tests). |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
