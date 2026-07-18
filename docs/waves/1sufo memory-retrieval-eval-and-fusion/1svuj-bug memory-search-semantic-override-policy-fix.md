# Memory search: semantic rank should tie-break within policy, not override it

Change ID: `1svuj-bug memory-search-semantic-override-policy-fix`
Change Status: `planned`
Owner: framework
Status: planned
Last verified: 2026-07-17

Wave: `1sufo memory-retrieval-eval-and-fusion`

## Rationale

`wave_memory_search_response` computes the trust/decay policy order via `_memory_ranked`, then, when a query has semantic hits, **wholesale re-sorts the result by semantic rank** (`server_impl.py` ~8008-8010: `ranked = _memory_ranked(...)` then `ranked.sort(key=lambda pair: semantic_hit_order.get(...))`). That discards the policy order entirely, so among the returned records a decayed or lower-confidence record can outrank a high-trust one purely on text relevance.

Two seats (red-team + reality-checker) confirmed this is the real defect and that the full lexical+semantic RRF rewrite (deferred change `1sufn`) is disproportionate machinery for it, especially over a corpus that is empty today and sparse by design. This change is the minimal, correct fix: make semantic rank a **secondary key layered under the policy order** (a tie-break within policy tiers), not a wholesale override.

Scope clarification the red-team surfaced: the pre-filter just above (records must be a semantic hit OR a full-token `_text_match`) already excludes records that match neither, so a non-matching record is filtered out of search results, not demoted. That filtering is acceptable for an explicit query; the defect is only the wholesale re-sort among the records that DID match. This change touches only that re-sort. `wave_memory_brief` is context-driven (no free-text query re-sort) and is unaffected.

## Requirements

1. In `wave_memory_search_response`, replace the wholesale semantic re-sort with a stable ordering where the policy order from `_memory_ranked` is primary and semantic rank is a secondary tie-break, so a high-trust record is never demoted below a lower-trust one by text relevance alone.
2. Anchor by symbol (`wave_memory_search_response`), not line number: a concurrent session is editing `server_impl.py`, so the semantic re-sort has drifted (was ~8002-8004, now ~8008-8010) and will keep moving.
3. Behavior otherwise unchanged: the surfaced-status filter, the no-index text-containment fallback, and the result cap are untouched; with no semantic index the path behaves exactly as today.

## Scope

**Problem statement:** memory search lets text relevance wholesale override the trust/decay policy order among matched records; the minimal fix is semantic-as-tie-break within policy, not a fusion rewrite.

**In scope (edited under `framework_edit_allowed`):**
- `.wavefoundry/framework/scripts/server_impl.py` — the semantic re-sort in `wave_memory_search_response` only.
- Tests — a high-trust decayed/low-text-overlap record retains its policy position ahead of a lower-trust strong-text-match record; no-index path unchanged.

**Out of scope:**
- **Lexical+semantic RRF fusion** — deferred change `1sufn` (revisit once a real corpus exists and the eval proves fusion beats a real baseline).
- **The pre-filter** (semantic-hit-or-full-token-match) — acceptable for an explicit query; not changed here.
- **`wave_memory_brief` ordering** — no free-text query re-sort applies.

## Acceptance Criteria

- [ ] AC-1: In `wave_memory_search_response`, the policy order (`_memory_ranked`) is primary and semantic rank is only a secondary tie-break; the wholesale override is removed. (required)
- [ ] AC-2: A test shows a high-trust record (e.g. `operator_preference`/`fragile_file` or a fresh higher-confidence record) is not demoted below a lower-trust strong-text-match record by the semantic path. (required)
- [ ] AC-3: With no semantic index, search behavior is byte-identical to today (text-containment fallback + policy order); the change is anchored by symbol, not line. (required)
- [ ] AC-4: Full framework suite green; docs-lint clean. (required)

## Tasks

- [ ] Replace the wholesale semantic re-sort with policy-primary + semantic-tie-break in `wave_memory_search_response`.
- [ ] Test: high-trust record not demoted by text relevance; no-index path unchanged.
- [ ] Full suite + docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| fix | framework | — | ~2-line change to the search re-sort |
| verify | framework | fix | policy-primary test + no-index invariance |


## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py` (`wave_memory_search_response`) — edited under `framework_edit_allowed`.

## Affected Architecture Docs

`N/A` — localized ordering fix within one function; no boundary/contract change.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The minimal correct fix — policy primary, semantic tie-break |
| AC-2 | required | Proves trust records are not demoted by text relevance |
| AC-3 | required | No-index invariance; anchor by symbol under concurrent edits |
| AC-4 | required | No regression |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-17 | Split out of `1sufo`: the minimal defect fix, replacing the deferred full RRF fusion | Red-team + reality-checker: RRF over-built for the corpus; ~2-line override is the real fix |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-17 | Semantic-as-tie-break, not full RRF fusion | Minimal correct fix; RRF is disproportionate for an empty/sparse typed corpus | Full lexical+semantic RRF (deferred as `1sufn` until a real corpus + eval justify it) |
| 2026-07-17 | Leave the pre-filter as-is | Filtering non-matching records is acceptable for an explicit query | Change the pre-filter (out of scope; separate concern) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Fix changes no-index behavior | AC-3 no-index invariance test |
| Line drift under concurrent edits mis-targets the fix | AC-3: anchor by symbol `wave_memory_search_response` |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
