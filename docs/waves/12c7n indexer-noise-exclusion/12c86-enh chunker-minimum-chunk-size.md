# Chunker Minimum Chunk Size

Change ID: `12c86-enh chunker-minimum-chunk-size`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-03
Wave: `12c7n indexer-noise-exclusion`

## Rationale

Structured chunkers (Python AST, JS/TS, Go, Rust, etc.) emit one chunk per AST node — but many AST nodes are trivially small. In a real CDK codebase, `super(scope, id)` appeared as a standalone chunk 103 times. These micro-chunks have no standalone semantic value: a single-expression constructor call, a one-line import alias, a bare `pass` statement. They dilute retrieval scores for infrastructure queries, waste embedding compute and index space, and never surface as useful search results. Production code search tools (Continue.dev's CodeSplitter, moatless-tools EpicSplitter) universally implement a minimum chunk size threshold, merging sub-minimum nodes into their enclosing parent or the preceding sibling.

## Requirements

1. All structured chunkers (`chunk_python`, `chunk_js_ts`, `chunk_c_cpp`, `chunk_go`, `chunk_rust`, `chunk_java`, `chunk_csharp`, `chunk_swift`, `chunk_shell`) must apply a minimum line threshold before emitting a chunk.
2. The default minimum must be **5 lines**. Chunks below this threshold must be merged into the preceding chunk in the output list, not discarded — the text must be preserved in the merged chunk.
3. If a file produces only one chunk and it is below the minimum, it must be emitted as-is (no merge target available).
4. The minimum must be configurable via a module-level constant `CHUNK_MIN_LINES = 5` so the tree-sitter wave can reuse it.
5. The imports chunk (where emitted) is exempt from the minimum — import blocks are always emitted regardless of line count, as they carry dependency signal even when short.
6. A test must assert that a Python file with a one-line function produces a chunk merged into its predecessor, not a standalone sub-minimum chunk.
7. A test must assert that a single-function file below the minimum is emitted as-is (no merge target).
8. All pre-existing structured chunker tests must pass.

## Scope

**Problem statement:** Structured chunkers emit AST-sized chunks with no floor. Single-expression nodes (`super(scope, id)`, `pass`, one-line stubs) become standalone chunks that dilute index quality.

**In scope:**

- `chunker.py`: add `CHUNK_MIN_LINES = 5` constant
- Post-processing merge pass applicable to all structured chunker outputs: if chunk line count < `CHUNK_MIN_LINES`, merge text into preceding chunk (update preceding chunk's `lines[1]` to the merged chunk's end line)
- Tests in `test_chunker.py` for the merge behavior and the single-chunk edge case
- The imports chunk exemption

**Out of scope:**

- `chunk_line_window` and `chunk_markdown` — these are window-based, not AST-based; minimum size is handled by the window size floor in `12c7n-enh line-window-chunker-boundary-improvement`
- Merging into the *following* chunk (always merge into preceding for simplicity)
- Tree-sitter chunkers — those land in wave `12c86 tree-sitter-chunker` and must reuse `CHUNK_MIN_LINES`

## Acceptance Criteria

- AC-1: A Python file with a 1-line function body produces a merged chunk, not a standalone sub-minimum chunk.
- AC-2: A file with only one chunk below the minimum emits that chunk as-is.
- AC-3: An imports chunk below 5 lines is emitted as a standalone chunk (not merged).
- AC-4: `CHUNK_MIN_LINES = 5` is defined at module level in `chunker.py`.
- AC-5: Tests cover AC-1, AC-2, and AC-3.
- AC-6: All pre-existing chunker tests pass.
- AC-7: All pre-existing framework tests pass.

## Tasks

- [ ] Add `CHUNK_MIN_LINES = 5` to `chunker.py`
- [ ] Implement `_merge_small_chunks(chunks: list[Chunk]) -> list[Chunk]` helper that merges sub-minimum chunks into their predecessor, exempting imports chunks
- [ ] Call `_merge_small_chunks` at the end of each structured chunker before returning
- [ ] Add tests for merge behavior and edge cases

## Agent Execution Graph

| Workstream  | Owner       | Depends On | Notes                                    |
| ----------- | ----------- | ---------- | ---------------------------------------- |
| chunker-enh | Engineering | —          | `CHUNK_MIN_LINES` + merge helper         |
| tests       | Engineering | chunker-enh | Merge behavior + edge case tests        |

## Serialization Points

- `CHUNK_MIN_LINES` must be defined before any chunker uses it; define it near the top of `chunker.py` alongside other constants.

## Affected Architecture Docs

N/A — enhancement confined to chunker post-processing. No boundary or data-flow impact.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Core behavior — sub-minimum chunks must be merged |
| AC-2 | required  | Edge case must not crash or discard content |
| AC-3 | required  | Imports exemption is load-bearing for dependency queries |
| AC-4 | required  | Constant must be reusable by tree-sitter wave |
| AC-5 | required  | Test coverage |
| AC-6 | required  | Non-regression gate |
| AC-7 | required  | Non-regression gate |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Merging into predecessor can produce oversized chunks if many small nodes follow a large function | In practice the predecessor is the function body — merging a 1-line stub into it adds minimal size; no cap needed for this wave |
| Imports exemption requires identifying the imports chunk | Use `chunk.section == "imports"` or check `chunk.kind` — imports chunks already carry a distinguishable section label |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
