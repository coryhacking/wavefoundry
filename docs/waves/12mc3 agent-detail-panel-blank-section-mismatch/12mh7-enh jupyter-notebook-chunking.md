# Chunker: Jupyter Notebook Support

Change ID: `12mh7-enh jupyter-notebook-chunking`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-14
Wave: `12mc3 agent-detail-panel-blank-section-mismatch`

## Rationale

`.ipynb` files are not currently indexed — they fall through to the line-window fallback, which treats the raw JSON as plain text. Jupyter notebooks are a common artifact in data-science and ML projects; indexing their cells as typed chunks (doc for markdown, code for code) makes their content searchable and retrievable by the CIA exactly like any other source file.

## Requirements

1. `chunk_file()` must route `.ipynb` files to a dedicated `chunk_jupyter()` handler.
2. `chunk_jupyter()` must parse the notebook JSON and iterate `cells`; malformed JSON must fall back gracefully to `chunk_line_window()`.
3. Each `markdown` cell must produce a `doc` chunk.
4. Each `code` cell must produce a `code` chunk. The language is taken from `metadata.kernelspec.language` or `metadata.language_info.name` at the notebook level; defaults to `"python"` when absent.
5. Empty cells (blank or whitespace-only `source`) must be skipped — no chunk emitted.
6. The `section` breadcrumb for each chunk must be `"notebook > Cell {n}"` where `n` is the 1-based cell index (counting all non-empty cells in order). When a markdown cell's first non-empty line is a `#` heading, use the heading text instead: `"notebook > {heading}"`.
7. `lines` must use virtual cumulative offsets derived from cell source length (not raw JSON file lines), so chunk line ranges are stable and non-overlapping.
8. `.ipynb` must be added to `_EXT_TO_LANGUAGE` with value `"jupyter"` so `code_search(language="jupyter")` filters work.
9. No new external dependencies — `json` is stdlib.

## Scope

**Problem statement:** `.ipynb` files fall through to the line-window fallback, producing low-quality chunks from raw JSON rather than structured cell content.

**In scope:**

- `IPYNB_EXTENSIONS = {".ipynb"}` constant in `chunker.py`
- `".ipynb": "jupyter"` entry in `_EXT_TO_LANGUAGE`
- Dispatch branch in `chunk_file()` before the `CODE_EXTENSIONS` fallback
- `chunk_jupyter()` handler function
- Tests in `test_chunker.py`

**Out of scope:**

- Cell output blocks (stdout, display_data, error outputs) — not indexed; noise-to-signal ratio too high
- Per-cell language override (multi-language notebooks) — notebook-level language only
- `code-summary` chunk for notebooks — not applicable without a top-level symbol structure
- `raw` cell type — skipped with no chunk emitted; raw cells are non-executing annotation content with no retrieval value

## Acceptance Criteria

- AC-1: A `.ipynb` file with markdown and code cells produces separate `doc` and `code` chunks (not raw JSON line-window chunks).
- AC-2: Empty cells produce no chunk.
- AC-3: The `language` field on code chunks reflects the notebook kernel language (defaulting to `"python"`).
- AC-4: Section breadcrumbs follow the `"notebook > Cell {n}"` pattern; markdown cells with a `#` heading use the heading text.
- AC-5: Malformed JSON (invalid `.ipynb`) falls back to `chunk_line_window()` without raising.
- AC-6: `code_search(language="jupyter")` matches chunks from `.ipynb` files.

## Tasks

- [ ] Add `IPYNB_EXTENSIONS = {".ipynb"}` after `OBJC_EXTENSIONS` in `chunker.py` (after line 205)
- [ ] Add `".ipynb": "jupyter"` to `_EXT_TO_LANGUAGE` in `chunker.py`
- [ ] Add dispatch branch in `chunk_file()`: `if suffix in IPYNB_EXTENSIONS: return chunk_jupyter(source, normalized)` (before the `CODE_EXTENSIONS` fallback, around line 3817)
- [ ] Implement `chunk_jupyter(source, path)`:
  - `json.loads(source)` — catch `JSONDecodeError`, fall back to `chunk_line_window()`
  - Extract kernel language from `metadata.kernelspec.language` or `metadata.language_info.name`, default `"python"`
  - Iterate `cells`; skip cell types other than `"markdown"` and `"code"` (skip `"raw"` and any unknown types silently)
  - Normalize `source` field: `"".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]`
  - Skip cells where joined source is blank/whitespace
  - Compute virtual `lines` using cumulative offset (start = previous end + 1, end = start + line count - 1)
  - Emit `Chunk` with `kind="doc"` for markdown, `kind="code"` for code; `language` on code chunks; `section` breadcrumb per requirement 6
- [ ] Add tests to `test_chunker.py`: markdown cell → doc chunk, code cell → code chunk, empty cell skipped, heading-based breadcrumb, JSON fallback, language detection from kernelspec, default language fallback, dispatch routing

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| chunker | implementer | — | chunker.py + test_chunker.py; framework_edit_allowed gate |

## Serialization Points

- `framework_edit_allowed` gate required for `chunker.py` and `test_chunker.py`.

## Affected Architecture Docs

N/A — confined to the chunker dispatch table and a new handler; no boundary or flow changes.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Core fix — cells must produce typed chunks |
| AC-2 | required | Empty cells must not produce noise chunks |
| AC-3 | important | Language metadata enables `code_search` language filtering |
| AC-4 | important | Readable breadcrumbs are key for CIA citation quality |
| AC-5 | required | Malformed files must not crash the indexer |
| AC-6 | important | Language filter usability |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-14 | Change scoped | Feasibility assessed against chunker.py dispatch table (lines 169–240, 3698–3822) |
| 2026-05-14 | Wave Council readiness review — 1 blocking finding resolved | `raw` cell type added to out-of-scope; task updated to skip `raw` and unknown cell types silently |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-14 | Skip cell outputs | Output blocks are noisy (stdout, tracebacks, display data); hurt retrieval quality | Index outputs — too much noise |
| 2026-05-14 | Virtual cumulative line offsets | `.ipynb` is JSON; real file lines map to JSON structure, not cell content; virtual offsets give stable, readable ranges | Raw JSON line numbers — confusing and fragile |
| 2026-05-14 | Notebook-level language only | Per-cell language overrides rare; adds complexity for minimal gain | Per-cell language detection — scope creep |

## Risks

| Risk | Mitigation |
|------|------------|
| Notebooks with no `cells` key | Guard with `.get("cells", [])` |
| `source` field as string vs list | Normalize with `isinstance` check before joining |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
