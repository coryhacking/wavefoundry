# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-05-03

wave-id: `12c86 tree-sitter-chunker`
Title: Tree-Sitter Chunker

## Changes

Change ID: `12c87-feat tree-sitter-structured-chunker`
Change Status: `planned`

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

## Dependencies

- Depends on wave `12c7n indexer-noise-exclusion` — `CHUNK_MIN_LINES` constant and `_merge_small_chunks` helper must land first; tree-sitter chunkers reuse both.
