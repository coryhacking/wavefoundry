# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-03

wave-id: `12c7n indexer-noise-exclusion`
Title: Indexer Noise Exclusion

## Changes

Change ID: `12c7n-bug binary-files-indexed-as-text`
Change Status: `implemented`

Change ID: `12c7n-bug generated-lock-files-indexed`
Change Status: `implemented`

Change ID: `12c7n-enh line-window-chunker-boundary-improvement`
Change Status: `implemented`

Change ID: `12c7r-bug ts-export-const-body-truncated`
Change Status: `implemented`

Change ID: `12c86-enh chunker-minimum-chunk-size`
Change Status: `implemented`

Completed At: 2026-05-03

## Wave Summary

Fixes five indexer quality issues discovered from real-project evaluation: binary and vector files (ELF, PPTX, EPS) being chunked as text consuming ~50% of a 17k-chunk index; generated lock files, snapshots, and diagram files contributing further noise; the TypeScript chunker dropping all content after the import block in `export const`-only files; the 60-line hard cap firing on 77.5% of code chunks; and single-expression AST nodes (`super(scope, id)`, one-line stubs) emitted as standalone micro-chunks with no retrieval value.

## Journal Watchpoints

- After this wave ships, existing indexes must be rebuilt — the exclusion bugs remove previously-indexed content and all chunker changes affect chunk boundaries.
- The two `walk_repo()` exclusion bugs can be implemented in parallel; the TS chunker fix, line-window enhancement, and minimum chunk size enhancement are each independent.
- `CHUNK_MIN_LINES = 5` and `_merge_small_chunks()` from `12c86-enh chunker-minimum-chunk-size` must be reused by the tree-sitter chunker wave (`12c86 tree-sitter-chunker`) — define them as public API in `chunker.py`.
- **Next wave:** `12c86 tree-sitter-chunker` replaces regex-based structured chunkers with tree-sitter AST chunking. Depends on this wave shipping first.

## Review Evidence

- Implementation complete and approved: binary file exclusion, generated/lock file exclusion, TS export const fix, line-window boundary improvement, minimum chunk size. 758 framework tests pass. Docs lint clean. Package built `wavefoundry-2026-05-03b.zip`.

## Dependencies

- No external wave dependencies.
