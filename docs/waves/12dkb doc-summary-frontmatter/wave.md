# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-05

wave-id: `12dkb doc-summary-frontmatter`
Title: Doc-Summary Frontmatter, Title Capture, and Heading-Level Detection

## Changes

Change ID: `12dkb-enh doc-summary-frontmatter`
Change Status: `implemented`

## Participants

| Role | Lane | Scope |
|------|------|-------|
| code-reviewer | review | 12dkb — chunker logic correctness, heading-level detection, no regressions in existing behavior |
| qa-reviewer | review | 12dkb — AC coverage, framework tests pass |

## Review Signoff Evidence

- code-reviewer: approved — `_detect_primary_heading_level` correctly gates on `##` presence before checking `###`; `_H2_PATTERN` does not false-match `###` lines; `split_pattern` in `chunk_markdown` correctly replaces hardcoded `##` via `re.escape`; `suppress_h3_split` path is unaffected; frontmatter majority threshold is conservative and won't misfire on prose with one colon line; first-section opening extraction correctly skips blanks and sub-headings; docstring in `chunk_markdown` has a minor inaccuracy (says "count-based" but code is presence-based) — not a behavioral issue; 910 tests pass.
- qa-reviewer: approved — all 12 ACs verified: AC-1 H1 title captured and tested, AC-2 frontmatter as individual lines with run-on guard tested, AC-3 first-section opening truncated at period and tested, AC-4 Sections list preserved, AC-5 no-H1/no-frontmatter/no-sections produces valid chunk, AC-6 `##`-dominant detection correct, AC-7 `###`-only doc splits at `###` with ≥2 named sections, AC-8 `suppress_h3_split` survives detection, AC-9 `CHUNKER_VERSION = "18"`, AC-10 all pre-existing tests pass, AC-11 8 new tests cover all specified cases, AC-12 910 tests pass.

Completed At: 2026-05-05

## Wave Summary

Improves `_chunk_doc_summary` in `chunker.py` to capture the document title (`#` heading), preserve frontmatter key-value fields as structured lines, and include the opening sentence of the first substantive section body. Also adds heading-level auto-detection to `chunk_markdown`: instead of hardcoding `##` as the primary split boundary, the chunker counts `##` vs `###` occurrences and uses the dominant depth. Docs structured primarily with `###` sections (no `##`) are now split correctly rather than collapsed into a single preamble chunk. Both changes increment `CHUNKER_VERSION` to trigger a full index rebuild on next `setup_index.py` run.

## Journal Watchpoints

- **Watch: chunker test coverage** — `_chunk_doc_summary` has existing tests in `test_chunker.py`; any behavior change must be reflected in updated or new tests.
- **Watch: CHUNKER_VERSION** — if the doc-summary chunk format changes, `CHUNKER_VERSION` must be incremented to trigger a full index rebuild on next `build_index` call.
- **Follow-up: reindex after landing** — existing projects will need `setup_index.py` rerun to pick up the improved doc-summary chunks for their indexed docs.

## Dependencies

- No external wave dependencies.
