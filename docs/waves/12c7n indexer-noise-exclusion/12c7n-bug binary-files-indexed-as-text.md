# Binary Files Indexed as Text

Change ID: `12c7n-bug binary-files-indexed-as-text`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-03
Wave: `12c7n indexer-noise-exclusion`

## Rationale

`walk_repo()` passes binary files (ELF executables, PPTX, EPS vector graphics, compiled artifacts) to the chunker, which processes them as line-based text. On a real project: a single ELF binary generated 3,537 chunks (20%), a PPTX generated 2,343 chunks (13%), and `.eps` PostScript brand asset files generated 2,960 chunks (17%) — together consuming 50%+ of the index. Unlisted binary extensions like `.acorn` contributed a further 272 chunks. Binary chunks contain garbage byte sequences that actively pollute cosine similarity scores: any query that embeds near a binary pattern will surface those chunks. The `language` field is `null` on all binary chunks — this is a useful diagnostic signal but not a sufficient filter at query time.

## Requirements

1. `walk_repo()` must detect binary files and exclude them before they reach the chunker. Detection must be extension-based for known binary types and byte-sniffing for unknown files.
2. The binary extension exclusion list must cover at minimum: compiled binaries (no extension or `.so`, `.dylib`, `.dll`, `.exe`, `.a`, `.o`, `.elf`), archive formats (`.zip`, `.tar`, `.gz`, `.tgz`, `.bz2`, `.xz`, `.7z`, `.rar`), office/presentation formats (`.pptx`, `.docx`, `.xlsx`, `.pdf`), image formats (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.ico`, `.bmp`, `.tiff`), vector/graphics formats (`.eps`, `.ai`, `.sketch`), font formats (`.ttf`, `.otf`, `.woff`, `.woff2`), media (`.mp4`, `.mp3`, `.wav`, `.mov`).
3. SVG files (`.svg`) must be excluded from the code index. They are XML but contain no semantic code content useful for search.
4. For files with extensions not on either list, a null-byte sniff of the first 8KB must be used to detect binary content; such files must be excluded.
5. Exclusion must happen in `walk_repo()` before files are yielded, not in the chunker.
6. A test must assert that a real ELF binary, a PNG, and a PPTX are excluded from `walk_repo()` output.
7. Existing text file types (`.py`, `.ts`, `.md`, `.json`, `.yaml`, etc.) must not be affected.

## Scope

**Problem statement:** Binary and non-text files are not excluded by `walk_repo()`, causing them to be chunked as text and indexed. A single ELF binary can generate thousands of garbage chunks that consume index space and corrupt similarity scores.

**In scope:**

- `indexer.py` `walk_repo()`: extension-based binary exclusion list + null-byte fallback
- `indexer.py`: `BINARY_EXTENSIONS` constant (or equivalent) as the exclusion set
- Tests: `walk_repo()` excludes known binary extensions; null-byte sniff catches unlisted binaries

**Out of scope:**

- Generated/lock file exclusion — separate change `12c7n-bug generated-lock-files-indexed`
- SVG indexing for docs search (SVG files may be legitimately referenced in docs; this change excludes them from code index only)
- Decompiling or parsing binary formats to extract text content

## Acceptance Criteria

- AC-1: ELF/compiled binaries, PPTX, EPS, PNG, JPEG, PDF, and ZIP files are not yielded by `walk_repo()`.
- AC-2: SVG files are not yielded by `walk_repo()` when `content="code"`.
- AC-3: A file with no known extension containing null bytes is not yielded by `walk_repo()`.
- AC-4: Known text files (`.py`, `.ts`, `.md`, `.json`) are unaffected.
- AC-5: Tests assert AC-1, AC-3, and AC-4 with concrete fixtures.
- AC-6: All pre-existing framework tests continue to pass.

## Tasks

- [ ] Add `BINARY_EXTENSIONS` frozenset to `indexer.py` covering the requirement list
- [ ] Add null-byte sniff helper in `walk_repo()` for files with unrecognized extensions
- [ ] Apply exclusion in `walk_repo()` before yielding files
- [ ] Add tests to `test_indexer.py` covering binary exclusion (ELF, PNG, null-byte)

## Agent Execution Graph

| Workstream   | Owner       | Depends On | Notes                                  |
| ------------ | ----------- | ---------- | -------------------------------------- |
| indexer-excl | Engineering | —          | `walk_repo()` extension list + sniff   |
| tests        | Engineering | indexer-excl | Binary exclusion test cases          |

## Serialization Points

- `walk_repo()` in `indexer.py` is the single-author surface; no parallelism needed.

## Affected Architecture Docs

N/A — implementation confined to `walk_repo()` internals. No boundary or data-flow impact beyond what is already described in Path 5 of `data-and-control-flow.md`.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Core correctness — binary chunks corrupt index |
| AC-2 | required | SVG chunks are noise in code index |
| AC-3 | required | Unlisted binaries must not slip through |
| AC-4 | required | Non-regression gate |
| AC-5 | required | Test coverage for the fix |
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
| Null-byte sniff adds file I/O per unknown-extension file | Only triggered for files not on the known text or binary list; most repos have few such files |
| Over-broad exclusion hides legitimate source files | Extension list is additive to the existing text allowlist; unknown extensions go through sniff, not blanket exclusion |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
