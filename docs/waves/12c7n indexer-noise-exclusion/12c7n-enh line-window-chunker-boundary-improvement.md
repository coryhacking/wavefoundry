# Line-Window Chunker Boundary Improvement

Change ID: `12c7n-enh line-window-chunker-boundary-improvement`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-03
Wave: `12c7n indexer-noise-exclusion`

## Rationale

The line-window chunker (`chunk_line_window`) splits files into fixed 60-line windows with no awareness of code structure. On a real project, 77.5% of all code chunks hit the 60-line hard cap — meaning most chunks are split mid-function, mid-block, or mid-comment rather than at logical boundaries. This produces two problems: (1) context is lost at every boundary, so a function body may span two chunks with neither containing the full signature + body; (2) embedding quality degrades because the model sees truncated, incomplete units of meaning.

The fix is to make the chunker attempt to break at logical boundaries — blank lines, dedent resets, and comment/decorator starts — before falling back to the hard line cap. The cap itself should also be raised from 60 to a value that accommodates typical function sizes (120–150 lines).

## Requirements

1. `chunk_line_window` must prefer breaking at blank lines over the hard line cap when a blank line appears within the last 20% of the window (e.g. within lines 48–60 of a 60-line window).
2. `chunk_line_window` must prefer breaking before a line that decreases indentation to column 0 (a top-level definition boundary) when one appears within the last 20% of the window.
3. The default maximum chunk size must be raised from 60 lines to 120 lines.
4. The minimum chunk size (to avoid tiny orphan chunks) must remain at least 10 lines.
5. Overlap between adjacent chunks (currently 0) must remain 0 — no sliding window overlap needed for the line-window chunker; structured chunkers (Python AST, JS/TS) already produce clean boundaries.
6. A test must assert that a file with a blank line at line 52 of a 120-line window produces a chunk break at the blank line rather than at line 120.
7. A test must assert that a file with a top-level `def` or `class` keyword at line 55 of a 120-line window produces a chunk break before that line.
8. The chunk `lines` field must correctly reflect the actual line range of each produced chunk.
9. All pre-existing line-window chunker tests must continue to pass.

## Scope

**Problem statement:** The 60-line hard cap fires on 77.5% of code chunks in real projects, splitting functions mid-body. The chunker has no awareness of logical structure and no preference for natural break points.

**In scope:**

- `chunker.py` `chunk_line_window()`: blank-line break preference, dedent-to-zero break preference, cap increase to 120 lines
- Tests for new boundary behavior

**Out of scope:**

- AST-aware chunking for non-Python languages via `chunk_line_window` — that is a separate, larger effort requiring per-language parsers
- Overlap/sliding window — adds complexity and doubles chunk count; not justified without evidence of quality improvement
- Changing the structured chunkers (`chunk_python`, `chunk_js_ts`, etc.) — those already produce symbol-level chunks and are not affected by this change

## Acceptance Criteria

- AC-1: A file with a blank line at line 52 of a 120-line window is chunked at the blank line, not at line 120.
- AC-2: A file with a top-level `def`/`class`/`function` keyword at line 55 is chunked before that line.
- AC-3: Default max chunk size is 120 lines (not 60).
- AC-4: No chunk is smaller than 10 lines unless the file itself is shorter.
- AC-5: `chunk["lines"]` reflects the actual line range of each chunk.
- AC-6: All pre-existing `chunk_line_window` tests pass.
- AC-7: All pre-existing framework tests pass.

## Tasks

- [ ] Raise default `max_lines` from 60 to 120 in `chunk_line_window()`
- [ ] Add blank-line break scan: when approaching the cap, scan backward for a blank line within the last 20% of the window and break there if found
- [ ] Add dedent-to-zero break scan: when approaching the cap, scan backward for a line at column 0 indentation (and not a blank line) and break before it if found
- [ ] Update `chunk_line_window` tests to reflect the new cap
- [ ] Add tests for blank-line break and dedent-break behavior

## Agent Execution Graph

| Workstream   | Owner       | Depends On | Notes                                  |
| ------------ | ----------- | ---------- | -------------------------------------- |
| chunker-enh  | Engineering | —          | `chunk_line_window` boundary logic     |
| tests        | Engineering | chunker-enh | New boundary test cases               |

## Serialization Points

- `chunk_line_window` in `chunker.py` is the single-author surface.

## Affected Architecture Docs

N/A — enhancement confined to `chunk_line_window` internals. The chunking strategy description in `data-and-control-flow.md` (Path 5, step 6) says "others → line-window" which remains accurate.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority    | Rationale |
| ---- | ----------- | --------- |
| AC-1 | required    | Core behavior — blank-line break is the primary improvement |
| AC-2 | important   | Secondary improvement — less common but high value for Python/JS |
| AC-3 | required    | Cap increase is the enabling change |
| AC-4 | required    | Prevents orphan chunks degrading embedding quality |
| AC-5 | required    | Metadata correctness — callers depend on `lines` |
| AC-6 | required    | Non-regression gate |
| AC-7 | required    | Non-regression gate |

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
| Raising cap to 120 lines may push some chunks over the 512-token model limit | 512-token truncation rate was 1.7% at 60 lines; at 120 lines it may increase — acceptable given the quality benefit of complete context; truncation is silent but the alternative (splitting mid-function) is worse |
| Blank-line break logic may produce very uneven chunk sizes | Minimum size guard (10 lines) prevents tiny orphan chunks; 20% lookback window limits how far below cap we break |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
