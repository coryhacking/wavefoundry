# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-03

wave-id: `12c86 tree-sitter-chunker`
Title: Tree-Sitter Chunker

## Changes

Change ID: `12c87-feat tree-sitter-structured-chunker`
Change Status: `implemented`

Completed At: 2026-05-03

## Wave Summary

Replaces the regex-based structured chunkers (JS/TS, Go, Rust, Java, C/C++, C#, Shell) with tree-sitter-backed AST chunking — the approach used by production code intelligence tools (Continue.dev, Cursor). Keeps Python's existing `ast`-based chunker (already accurate) and Swift/ObjC on regex fallback until `tree-sitter-swift` reaches 1.0. Reuses `CHUNK_MIN_LINES` from wave `12c7n` for consistent minimum chunk size enforcement across all chunkers.

## Journal Watchpoints

- **Watchpoint — dependency risk**: Grammar packages pin different `tree-sitter` minor versions (`tree-sitter-rust` ~0.22, `tree-sitter-typescript` ~0.23, `tree-sitter-go` ~0.24). Pin `tree-sitter~=0.24` and verify ABI compatibility with each grammar package before implementation begins. This is the primary pre-implementation gate; block work until verified.
- **Watchpoint — `tree-sitter-language-pack` ruled out**: Uses on-demand parser downloads at first parse — incompatible with offline-first MCP constraint. Use individual `tree-sitter-{language}` packages only.
- **Watchpoint — `tree-sitter-swift` pre-1.0** (0.0.1): retain current regex chunker as fallback for Swift and ObjC. Do not add `tree-sitter-swift` as a dependency.
- **Watchpoint — `setup_index.py` surface change**: tree-sitter packages must be added to `REQUIRED_IMPORTS` and installation guidance. Agents running setup will need to install `tree-sitter` + grammar packages.
- **Watchpoint — symbol-identity-aware merging**: `_merge_small_chunks` (from wave `12c7n`) merges sub-minimum code chunks into the preceding code chunk without checking whether they belong to the same parent symbol. With regex chunkers this is acceptable at `CHUNK_MIN_LINES=2` (only 1-line expressions hit the merge path). Tree-sitter chunkers may emit more fine-grained nodes — a 1-line method in one class should not merge into a method in a different class. When implementing tree-sitter chunkers, make the merge symbol-aware: only merge into a predecessor that shares the same parent scope (same class/impl/interface), which tree-sitter AST parent context makes straightforward.
- **Defer — embedding model**: Research (2026-05-03) shows `BAAI/bge-base-en-v1.5` remains the best fastembed offline option. Best code-specific alternative (`SFR-Embedding-Code-400M_R`, CoIR 61.9) has no official INT8 ONNX and is not in fastembed. `nomic-embed-text-v1.5-Q` is fragile on macOS. `Qwen3-Embedding-0.6B` hardcodes `batch_size=1`. Revisit when a code-specific INT8 ONNX model in fastembed outperforms bge-base on our ground truth set.
- **Watchpoint — post-ship index rebuild required**: tree-sitter produces different chunk boundaries than regex chunkers — all existing indexes must be rebuilt after this wave ships.

## Review Checkpoints

**Prepare wave — readiness verdict (2026-05-03): READY**

- Change doc complete: Rationale, Requirements, Scope, ACs, Tasks, Affected architecture docs — all present
- AC priority populated (all required)
- Review lanes: architecture-reviewer, code-reviewer, qa-reviewer
- Pre-implementation gate cleared: ABI verification dry-run passed — `tree-sitter==0.25.2` resolves cleanly with all grammar packages; no version conflicts
- Resolved versions: tree-sitter 0.25.2, typescript 0.23.2, javascript 0.25.0, go 0.25.0, rust 0.24.2, java 0.23.5, c 0.24.2, cpp 0.23.4, c-sharp 0.23.5, bash 0.25.1
- Pin updated to `tree-sitter>=0.24,<0.26` to allow 0.25.x
- Dependency on wave 12c7n confirmed closed (`CHUNK_MIN_LINES`, `_merge_small_chunks` in place)

**Review wave — findings and resolution (2026-05-03): APPROVED**

Architecture findings — all resolved:
- `_TS_LANGS` type annotation corrected to `dict[str, Optional[object]]`
- Parser now cached per language (`_TS_PARSERS`) — one `_TSParser(lang)` per language key, not per call
- Fallback contract confirmed clean: all tree-sitter chunkers return `None` → `chunk_file` falls back to regex

Code findings — all resolved:
- **Blocking fix**: missing `return` after `lexical_declaration` block in `export_statement` handler — fixed; duplicate chunks no longer possible
- Req 7 warning log: `_ts_parse` now emits `logging.warning` on first grammar miss and `logging.debug` when tree-sitter itself is absent
- `_ts_collapse_body`: no-brace fallback now preserves first `max_lines` of signature instead of silently truncating mid-content
- Bash `_name`: removed dead `variable_name` branch (function names are `word` nodes in bash grammar)

QA findings — all resolved:
- **Symbol-identity-aware merge** (watchpoint addressed in this wave, not deferred): `_merge_small_chunks` extended with `scoped=True` parameter; all tree-sitter chunkers use `scoped=True`; `_parent_scope` helper extracts class prefix from breadcrumb section; cross-class 1-line methods no longer merge; same-class merging still works
- **Kotlin implemented (not deferred)**: `chunk_kotlin_treesitter` added; `KOTLIN_EXTENSIONS = {".kt", ".kts"}` carved out of `CODE_EXTENSIONS`; `chunk_file` dispatches to tree-sitter Kotlin with `chunk_line_window` fallback; `tree-sitter-kotlin` added to `REQUIRED_IMPORTS`; decision log updated
- 7 new tests: `test_parent_scope_extracts_class_prefix`, `test_scoped_merge_does_not_merge_across_classes`, `test_scoped_merge_merges_within_same_class`, `test_unscoped_merge_still_merges_across_classes`, `test_chunk_file_kotlin_fallback`, `test_ts_kotlin_chunker_extracts_functions_and_classes`, `test_ts_kotlin_scoped_merge_does_not_merge_across_classes`

787 framework tests pass (9 skipped — tree-sitter positive extraction tests require grammars installed).

## Review Evidence

- signoff: architecture-reviewer — findings resolved (type annotation, parser caching, fallback contract)
- signoff: code-reviewer — blocking fix merged (missing return in export_statement handler), warning log and debug log in place, collapse fallback corrected, dead bash branch removed
- signoff: qa-reviewer — symbol-identity-aware merge implemented, Kotlin tree-sitter chunker added, 7 new tests, 787 framework tests pass

## Dependencies

- Depends on wave `12c7n indexer-noise-exclusion` — `CHUNK_MIN_LINES` constant and `_merge_small_chunks` helper must land first; tree-sitter chunkers reuse both.
