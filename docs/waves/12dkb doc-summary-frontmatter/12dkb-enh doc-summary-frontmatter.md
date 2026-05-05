# Doc-Summary Frontmatter, Title Capture, and Heading-Level Detection

Change ID: `12dkb-enh doc-summary-frontmatter`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-05
Wave: `12dkb doc-summary-frontmatter`

## Rationale

The `_chunk_doc_summary` function in `chunker.py` emits one orientation chunk per markdown doc: a "first paragraph" plus a section heading list. For most Wavefoundry docs this produces a weak orientation signal because:

1. **The `#` title is not captured.** The heading extractor (`_DOC_HEADING_RE`) only matches `##` and below. The document title — the single most useful piece of text for orientation — is silently dropped.

2. **Frontmatter fields are joined into a run-on string.** Docs open with key-value metadata (`Owner:`, `Status:`, `Last verified:`, identity fields, etc.) between the `#` title and the first `##` section. The current code captures these as the "first paragraph" by joining them into a single space-separated string: `Owner: Engineering Status: active Last verified: 2026-05-05`. This makes field-specific queries brittle — exact field values may not match because of token adjacency issues in the embedding.

3. **The first substantive section body is not captured.** For agent prompts the most search-relevant content is in the first `##` section body (e.g., `## Purpose`). The doc-summary lists the section name only — a query for "research agent that validates claims" won't match unless the full-doc chunks are also scored, reducing the value of the orientation pass.

4. **The content chunker hardcodes `##` as the primary split boundary.** This is correct for Wavefoundry's own docs, but a project whose docs use `###` as their primary structural level (with `##` as top-level grouping) would produce one giant preamble chunk with no section splits. The split boundary should be detected from the document rather than hardcoded, making the chunker adaptive to project conventions without requiring configuration.

The result is that `kind="doc-summary"` orientation queries for wave docs, agent prompts, and spec docs often require fallback to Pass 2 (broad semantic) before the right file is surfaced. Better doc-summary chunks and an adaptive split boundary would let the CIA and other agents orient on the first pass more reliably across a wider range of project doc conventions.

## Requirements

1. The `#` title line must be included in the doc-summary chunk text.
2. Frontmatter key-value lines (lines between the `#` title and the first `##` section that match `Key: value` or `` Key: `value` `` patterns) must be preserved as individual lines, not joined into a paragraph.
3. The opening sentence (up to the first `.` or end of first line, max ~150 chars) of the first substantive section body must be included in the doc-summary chunk text.
4. The heading list (`Sections: ...`) must be preserved as-is.
5. Existing doc-summary behavior for docs that have no frontmatter or no `#` title must be unchanged or improved — no regressions.
6. `chunk_markdown` must detect the primary heading level from the document itself: count `##` vs `###` occurrences and use the more frequent depth as the split boundary. When counts are equal or both are zero, default to `##` (current behavior).
7. The detected primary heading level must also be used consistently in `_chunk_doc_summary` when building the heading list and extracting the first section opening — so the summary and content chunks agree on structure.
8. `suppress_h3_split` behavior for prompt files is unaffected — the suppression applies after split-boundary detection.
9. `CHUNKER_VERSION` must be incremented to trigger a full index rebuild.
10. Existing tests that assert specific doc-summary or chunk-split text must be updated to match new behavior where affected. New tests must cover title capture, frontmatter capture, first-section-body capture, and heading-level detection.

## Scope

**In scope:**
- `_chunk_doc_summary` in `.wavefoundry/framework/scripts/chunker.py` — title, frontmatter, first-section opening
- `chunk_markdown` in `chunker.py` — heading-level auto-detection
- `_DOC_HEADING_RE` or equivalent — update to participate in level detection
- `CHUNKER_VERSION` increment
- Update/add tests in `.wavefoundry/framework/scripts/tests/test_chunker.py`

**Out of scope:**
- Changes to `_chunk_code_summary` (code file orientation — separate concern)
- Changes to the `doc` chunk kind (line-window content chunks) beyond split-boundary adjustment
- Changes to how `docs_search` filters or ranks results
- YAML front-matter (`---` fenced) parsing — not used in Wavefoundry docs
- Reindexing existing projects (happens automatically on next `setup_index.py` run due to `CHUNKER_VERSION` bump)

## Affected Architecture Docs

N/A — chunker implementation only.

## Acceptance Criteria

| AC | Description |
|----|-------------|
| AC-1 | Doc-summary chunk text includes the `#` title of the document |
| AC-2 | Doc-summary chunk text includes frontmatter key-value fields as individual lines (not joined into a run-on string) |
| AC-3 | Doc-summary chunk text includes the opening sentence of the first primary-level section body |
| AC-4 | Doc-summary chunk text preserves the `Sections: ...` heading list |
| AC-5 | Docs with no `#` title, no frontmatter, and no sections still produce a valid doc-summary chunk (no regression) |
| AC-6 | `chunk_markdown` detects primary heading level from document: uses `##` split when `##` count ≥ `###` count, uses `###` split when `###` count > `##` count |
| AC-7 | A doc with only `###` sections (no `##`) is split at `###` boundaries, not returned as a single preamble chunk |
| AC-8 | `suppress_h3_split` behavior for prompt files is unaffected by heading-level detection |
| AC-9 | `CHUNKER_VERSION` is incremented |
| AC-10 | All existing doc-summary and chunk-split tests pass (updated where format changed) |
| AC-11 | New tests cover: title capture, frontmatter capture, first-section body capture, `##`-dominant doc, `###`-dominant doc, mixed doc defaults to `##` |
| AC-12 | Framework test suite passes (902+ tests) |

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Title is the highest-signal text for orientation; its absence is the primary gap |
| AC-2 | required | Frontmatter field queries fail due to run-on joining; structured lines fix this |
| AC-3 | required | First-section body is the main retrieval gap for agent prompts |
| AC-4 | required | Heading list is already working; must be preserved |
| AC-5 | required | Non-regression for simpler docs |
| AC-6 | required | Core heading-level detection behavior |
| AC-7 | required | Verifies detection actually changes split behavior, not just detects |
| AC-8 | required | Prompt suppression must survive the refactor |
| AC-9 | required | Without version bump, existing indexes won't rebuild |
| AC-10 | required | Existing tests must pass |
| AC-11 | required | New behavior must be explicitly covered |
| AC-12 | required | Full suite non-regression |

## Tasks

1. Update `_chunk_doc_summary` in `chunker.py`:
   a. Capture `#` title
   b. Detect and preserve frontmatter lines as individual key-value entries
   c. Accept detected primary heading level to find first section opening
   d. Assemble chunk text in order: title → frontmatter → first-section opening → headings
2. Add `_detect_primary_heading_level(source) -> int` helper in `chunker.py` — returns 2 (`##`) or 3 (`###`)
3. Update `chunk_markdown` to call `_detect_primary_heading_level` and use the result as the split boundary (replacing the hardcoded `##` pattern)
4. Pass detected level into `_chunk_doc_summary` call so summary and content chunks agree
5. Increment `CHUNKER_VERSION`
6. Update existing doc-summary and chunk-split tests in `test_chunker.py`
7. Add new tests for title, frontmatter, first-section body, and heading-level detection cases
8. Run `python3 .wavefoundry/framework/scripts/run_tests.py`

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-05 | Include only the opening sentence of first section, not the full body | Doc-summary is an orientation chunk; a sentence is enough to make queries match; full body would duplicate line-window content chunks | Could include full first section — over-embeds content already in line chunks; could skip entirely — loses the primary retrieval gap for agent prompts |
| 2026-05-05 | Preserve frontmatter as individual lines, not as a structured object | Embedding text is most effective when key-value pairs are natural-language-adjacent; individual lines preserve query-matching while remaining readable | Could parse into structured metadata — not how the embedding model sees it; could drop frontmatter — loses status, owner, and identity field retrieval |
| 2026-05-05 | Cap first-section opening at ~150 chars | Keeps the chunk focused; prevents a very long Purpose section from dominating the embedding | Could use first sentence up to `.` only — may be too short for single-sentence paragraphs with no period |
| 2026-05-05 | Detect heading level by frequency count, default to `##` on tie | Frequency is the most reliable signal for "what is the primary structure of this doc" without requiring frontmatter; defaulting to `##` preserves current behavior for all existing Wavefoundry docs | Could make it configurable per project — adds setup friction; could use first-occurrence rather than frequency — fragile for docs with a single top-level `##` grouping followed by many `###` |
| 2026-05-05 | Scope detection to `##` vs `###` only | These are the only two depths used as primary section boundaries in practice; supporting `#` as split boundary would conflict with the title convention | Could detect any depth — over-general; `#` as split boundary is not a real pattern for our use case |
