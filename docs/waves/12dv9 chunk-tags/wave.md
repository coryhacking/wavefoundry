# Wave Record

Owner: Engineering
Status: active
Last verified: 2026-05-10

wave-id: `12dv9 chunk-tags`
Title: Chunk Tags — Multi-Label Retrieval Axis

## Objective

Add a `tags: list[str]` field to Chunk for multi-label retrieval, populated at index time from path-pattern heuristics, with a `tags` filter parameter on `docs_search` and `code_search`.

## Changes

Change ID: `12dv9-enh chunk-tags`
Change Status: `complete`

## Participants

| Role | Lane | Scope |
|------|------|-------|
| code-reviewer | review | 12dv9 — tag inference logic, Chunk dataclass change, search filter correctness |
| qa-reviewer | review | 12dv9 — AC coverage, no regressions, framework tests pass |

## Wave Summary

Adds a `tags` list field to the `Chunk` dataclass, populated at index time from path-pattern heuristics (no LLM required). Tags give search results a second classification axis beyond `kind` — a chunk can be reachable as both `kind="prompt"` and `tags=["lifecycle"]`, for example. `docs_search` and `code_search` gain an optional `tags` filter parameter. Inspired by the "virtual nodes / multi-ancestor" pattern from PageIndex's filesystem research (2025), adapted to work entirely within Wavefoundry's offline, embedding-based model. `CHUNKER_VERSION` is incremented to trigger a full index rebuild.

## Journal Watchpoints

- **Watch: CHUNKER_VERSION bump** — incrementing forces a full index rebuild on next `setup_index.py` run; coordinate with any other in-flight chunker changes to avoid double-bumping unnecessarily.
- **Watch: Chunk.to_dict / from_dict symmetry** — `tags` must round-trip cleanly through JSON serialization; verify that `search_docs` and `search_code` deserialization handles missing `tags` key (for indexes built before this wave).
- **Watch: tag vocabulary stability** — the controlled vocabulary is part of the public tool contract once shipped; additions are safe, removals are breaking. Define the initial set conservatively.
- **CIA prompt update** — resolved: seed-211 `### Tags Filter` section documents the full vocabulary, OR semantics, `kind`+`tags` AND composition, and usage examples.

## Dependencies

- Depends on: wave `12dkb doc-summary-frontmatter` (closed) — Chunk dataclass familiarity; CHUNKER_VERSION = "18" is the baseline.
