# TypeScript export const Body Truncated After Import Block

Change ID: `12c7r-bug ts-export-const-body-truncated`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-03
Wave: `12c7n indexer-noise-exclusion`

## Rationale

The TypeScript/JSX chunker (`chunk_js_ts`) stops after the import block on files that mix `styled()` calls and `export const` declarations at the top level with no wrapping class or function. On a real project, `icons.tsx` (134 lines) produced only an 18-line import chunk — the 116 lines of icon constant definitions and exports were not indexed at all. This means icon queries surface consumer import sites rather than the definitions themselves. It is the direct cause of the "consumers ranked above definitions" pattern observed in retrieval evaluation.

## Requirements

1. `chunk_js_ts` must index top-level `export const` declarations, including those that use tagged template literals (`styled(Component)\`...\``) or call expressions as initializers.
2. A file consisting of an import block followed by `export const` declarations at the top level must produce: one imports chunk and one or more body chunks covering the declarations.
3. The chunk covering a `export const Foo = styled(...)` pattern must include the full expression as its text, not be split mid-expression.
4. Files that already chunk correctly (class bodies, named function declarations, arrow function components) must not regress.
5. A test must assert that a synthetic `export const`-style file with an import block and multiple top-level declarations produces chunks covering the full file content.

## Scope

**Problem statement:** `chunk_js_ts` does not recognize top-level `export const` + `styled()` patterns as named symbols to chunk. The import block is chunked, then chunking stops and the remainder of the file is dropped from the index.

**In scope:**

- `chunker.py` `chunk_js_ts()`: extend symbol recognition to cover top-level `export const <Name> =` patterns at column 0
- Tests: file with import block + multiple `export const` declarations produces full-file coverage

**Out of scope:**

- Full TypeScript AST parsing — extending the existing regex-based heuristics is sufficient
- Handling destructured or dynamically computed export names (e.g. `export const [a, b] = ...`)
- Other chunker languages

## Acceptance Criteria

- AC-1: A file with an import block (lines 1–18) followed by `export const` declarations (lines 19–134) produces chunks covering lines 19–134, not just lines 1–18.
- AC-2: Each `export const Foo = ...` at column 0 produces its own named chunk with `section` containing `Foo`.
- AC-3: Files with named function declarations and class bodies continue to chunk correctly (no regression).
- AC-4: Test covers a synthetic file with mixed `styled()` and plain `export const` declarations.
- AC-5: All pre-existing `chunk_js_ts` tests pass.
- AC-6: All pre-existing framework tests pass.

## Tasks

- [ ] Inspect `chunk_js_ts` in `chunker.py` to identify where symbol detection stops after the import block
- [ ] Extend symbol regex / heuristic to match `export const <Identifier> =` at the start of a line
- [ ] Ensure chunk boundary captures the full expression (through the next `export const` at column 0 or end of file)
- [ ] Add test in `test_chunker.py` for the `export const` + `styled()` pattern
- [ ] Verify no regression on existing JS/TS chunker tests

## Agent Execution Graph

| Workstream  | Owner       | Depends On  | Notes                                       |
| ----------- | ----------- | ----------- | ------------------------------------------- |
| chunker-fix | Engineering | —           | `chunk_js_ts` symbol detection extension    |
| tests       | Engineering | chunker-fix | Synthetic icons.tsx-style test case         |

## Serialization Points

- `chunk_js_ts` in `chunker.py` is the single-author surface.

## Affected Architecture Docs

N/A — bug fix confined to `chunk_js_ts` internals. No boundary or data-flow impact.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Core correctness — file body must be indexed |
| AC-2 | required | Named chunks enable precise retrieval |
| AC-3 | required | Non-regression gate |
| AC-4 | required | Test coverage for the fix |
| AC-5 | required | Non-regression gate |
| AC-6 | required | Non-regression gate |

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
| Regex extension for `export const` may over-match and split template literal bodies mid-expression | Require the pattern to match only at column 0; use chunk boundary at the next column-0 `export const` or end of file |
| Styled component template literals span multiple lines and may cause off-by-one in chunk end detection | Test with a multi-line `styled()` expression to verify the closing backtick is included in the chunk |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
