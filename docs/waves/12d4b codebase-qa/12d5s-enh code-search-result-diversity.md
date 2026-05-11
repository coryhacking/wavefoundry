# Code Search Result Diversity

Change ID: `12d5s-enh code-search-result-diversity`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-04
Wave: `12d4b codebase-qa`

## Rationale

`code_search` with `top_n=5` can return multiple chunks from the same file when that file is highly relevant — e.g., a large Python module can fill all 5 slots with line-window chunks from different sections. This leaves other relevant files unrepresented and makes the result set less useful for orientation. The Code Insight Agent's broad retrieval pass is designed to identify distinct entry points across the codebase; duplicate-file results undermine this by collapsing coverage into one file.

## Requirements

1. `search_code()` must accept an optional `max_per_file` parameter (default: no limit, preserving current behavior). When set, results are capped to `max_per_file` chunks per unique file path after cosine ranking, before the final `top_n` slice.
2. The cap must be applied after ranking so that the highest-scoring chunks from each file are retained (not arbitrary).
3. Default behavior (`max_per_file` omitted or `None`) must be identical to current behavior — no regression for existing callers.
4. The CIA prompt must document the recommended call pattern for the orientation pass: `code_search(query, kind="code-summary", max_per_file=1)`.

## Scope

**Problem statement:** High-relevance files monopolize `code_search` results, reducing file diversity and limiting the CIA's ability to identify multiple entry points in a single broad pass.

**In scope:**

- `server.py` `search_code()` — add `max_per_file: Optional[int] = None` parameter; apply per-file cap after ranking
- `docs/prompts/agents/code-insight-agent.prompt.md` — document recommended `max_per_file=1` call pattern for orientation pass

**Out of scope:**

- Diversity across `docs_search` — doc chunks are typically more distinct by nature; not needed
- Global deduplication across `code_search` + `docs_search` combined results
- Score-based diversity (e.g., MMR) — simple per-file cap is sufficient for v1

## Acceptance Criteria

- AC-1: `search_code(query, max_per_file=1)` returns at most one chunk per file path
- AC-2: `search_code(query, max_per_file=2)` returns at most two chunks per file path
- AC-3: `search_code(query)` (no `max_per_file`) returns results identical to current behavior
- AC-4: With `max_per_file=1`, the retained chunk per file is the highest-scoring one
- AC-5: CIA prompt documents `max_per_file=1` for the orientation pass

## Tasks

- [ ] `server.py` `search_code()`: add `max_per_file: Optional[int] = None` parameter; apply filters in order: (1) cosine rank, (2) `kind` filter (added in 12d4h), (3) per-file cap — keep top `max_per_file` chunks per path in ranked order, (4) `top_n` slice; this ordering ensures kind-filter runs before cap so no non-matching chunks waste cap slots
- [ ] `docs/prompts/agents/code-insight-agent.prompt.md`: add `max_per_file=1` to orientation pass call pattern (coordinate with CIA prompt task in 12d4b-feat)
- [ ] `docs/architecture/search-architecture.md`: document `max_per_file` parameter in `code_search` contract (coordinate with 12d4h architecture doc task — land in same pass)

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| `search_code` diversity filter | Engineering | — | server.py — independent of chunker and CIA prompt |
| CIA prompt update | Engineering | `search_code` diversity filter | Documents the call pattern after the parameter exists |

## Serialization Points

- `server.py` is a single-author surface — implement alongside other server.py changes in 12d4h (kind filter, `code_references`/`code_definition` fallbacks, `code_dependencies`).
- CIA prompt update depends on the parameter existing — coordinate with 12d4b-feat CIA prompt task.

## Affected Architecture Docs

- `docs/architecture/search-architecture.md` — note `max_per_file` parameter in `code_search` contract description.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Core behavior — single-file cap must work |
| AC-2 | required  | Configurable cap must work |
| AC-3 | required  | Non-regression — existing callers must be unaffected |
| AC-4 | required  | Highest-scoring chunk retained, not arbitrary |
| AC-5 | important | CIA prompt adoption; not a code correctness gate |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-04 | Change doc created | Design discussion: orientation pass quality |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-04 | `max_per_file` as an optional parameter with `None` default | Preserves backward compatibility; callers opt in; no behavior change for existing code_search calls | Always-on diversity (rejected: changes existing behavior, breaks callers relying on current ranking) |
| 2026-05-04 | Per-file cap applied after ranking, not before | Ensures best chunk per file is retained; if applied before ranking, arbitrary chunks would be kept | Pre-rank deduplication (rejected: loses signal) |
| 2026-05-04 | Simple per-file count cap rather than MMR | Sufficient for v1; MMR is more complex and harder to test deterministically | Maximal marginal relevance (deferred) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| `top_n` slots unfilled when few files match | Acceptable — fewer diverse results is better than repeated same-file chunks; CIA can fall back to targeted pass |
| Cap of 1 loses secondary entry points within a large file | CIA targeted pass (`code_keyword_search`, `code_references`) recovers these after orientation identifies the file |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
