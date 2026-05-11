# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-04

wave-id: `12cv4 prompt-indexing-quality`
Title: Prompt Indexing Quality

## Objective

Improve prompt indexing quality, rename prompt file extensions to `.prompt.md`, and add docs-first index onboarding guidance.

## Changes

Change ID: `12cv3-enh prompt-indexing-quality`
Change Status: `implemented`

Change ID: `12cvs-enh prompt-file-extension-rename`
Change Status: `implemented`

Change ID: `12d2j-enh docs-first-index-onboarding`
Change Status: `implemented`

Completed At: 2026-05-04

## Wave Summary

Improves prompt retrieval quality by introducing `kind="prompt"` as a distinct chunk kind for all files under `docs/prompts/`, suppressing H3 re-splitting and fenced code extraction for prompt content, excluding the machine-generated manifest artifact from indexing, extending `docs_search` to filter by `kind="prompt"`, and adding routing guidance for agents choosing between `seed_get` and `docs_search`.

## Journal Watchpoints

- **Watchpoint — CHUNKER_VERSION bump**: any change to kind assignment or chunking behavior for prompts must increment `CHUNKER_VERSION` to force a full index rebuild on next setup. Block merge if version is not bumped.
- **Watchpoint — `chunk_file` single-author surface**: H3/code-extraction flag changes and kind assignment must land together in one pass — do not split across parallel agents. Block parallelization of chunker workstream.
- **Watchpoint — kind filter non-regression**: extending `docs_search` to accept `kind="prompt"` must not break existing `kind="doc"` and `kind="seed"` filter behavior. Verify both in tests before closing.

## Participants

| Role | Lane | Notes |
| ---- | ---- | ----- |
| architecture-reviewer | architecture-review | chunker kind taxonomy, indexer routing, docs_search kind filter contract |
| docs-reviewer | docs-review | prompt file rename convention, routing guidance in index.md |
| code-reviewer | code-review | chunker.py suppress flags, chunk_file dispatch, indexer _is_docs_kind, server _doc_matches_kind |
| qa-reviewer | qa-review | 10 new tests, AC coverage, no regression on existing kinds |

## Review Checkpoints

**Prepare wave — readiness verdict (2026-05-04): READY**

- Change docs complete: Rationale, Requirements, Scope, ACs, Tasks, Affected architecture docs — all present
- AC priority populated (all required)
- Review lanes: architecture-reviewer, docs-reviewer, code-reviewer, qa-reviewer

## Review Evidence

- signoff: architecture-reviewer — kind taxonomy consistent across chunker/indexer/server; _is_docs_kind correct; blocking _doc_matches_kind early-exit fixed; Chunk.kind comment updated
- signoff: docs-reviewer — routing note accurate and agent-actionable; agents/README.md filenames corrected; wave change statuses updated; no remaining broken references; seed changes (008, 100, 160) reviewed and fixed: 008 naming convention section placed after layer 5 with accurate positive-case description, 100 cross-surface rule clarifies path vs extension detection, 160 step 9 shows agents/ git mv command separately
- signoff: code-reviewer — _doc_matches_kind restructured (prompt branch before doc guard); suppress flags threaded correctly through both preamble and section paths; CHUNKER_VERSION=14 confirmed; test updated for new kind="prompt" chunk contract
- signoff: qa-reviewer — 815 tests pass; AC coverage complete; preamble suppression test added; kind="doc" non-regression test added; manifest exclusion test added; CHUNKER_VERSION threshold tightened to 14

## Dependencies

- No external wave dependencies.
