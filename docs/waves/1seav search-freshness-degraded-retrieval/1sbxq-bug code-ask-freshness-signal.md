# `code_ask` Freshness Is Hot-Path-Expensive and Wrong (Ignores Stale Paths, Maps Errors to "current")

Change ID: `1sbxq-bug code-ask-freshness-signal`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-12
Wave: TBD

## Rationale

External code review (2026-07-12), validated against `2952df8f` — three defects in one block (`server_impl.py` `code_ask_response`, ~17303–17311):

1. **Hot-path contract violation:** every `code_ask` calls `index._layer_health("project")`, whose OWN docstring says "This is an O(total-indexed-bytes) operation — call it only via the explicit `wave_index_health` MCP tool, never on the search hot path." Every question pays a full walk-and-hash of the indexed corpus (~1,400 files on this repo; worse on field repos) before retrieval even starts.
2. **Wrong signal:** freshness is derived ONLY from chunker-version mismatch (`indexed_chunker_versions` vs `current_chunker_version`); the `stale_paths` that `_layer_health` just paid to compute are discarded. Live repro from the review session: `code_ask` reported `index_freshness: "current"` while `wave_index_health` reported two stale paths.
3. **Errors read as fresh:** `except Exception: is_stale = False` — any health failure silently reports `current`.

The cheap correct substrate now exists (wave 1sc7c): per-layer last-embedded hashes (`layer_path_state`) and `project_index_inputs_stale()` (the stat-fast-path check the staleness monitor already uses).

## Requirements

1. **Cheap freshness signal:** replace the per-call `_layer_health` with a stat-fast-path check (`project_index_inputs_stale()` or an equivalent read over per-layer state) — no per-call corpus hashing. Keep the chunker-version-mismatch check (it is a valid *distinct* staleness cause) via a cheap meta read, not the full health walk.
2. **Three honest states:** `index_freshness ∈ {"current", "stale", "unknown"}` — an exception or undeterminable state returns `"unknown"`, never silently `"current"`. Consumers (seed-211 guidance documents `index_freshness`) updated for the third state.
3. **Short-lived cache:** the freshness verdict may be cached briefly (seconds-scale TTL or invalidation keyed on the index meta signature / build `ended_at`) so bursts of `code_ask` calls don't repeat even the cheap check; the cache must invalidate on build completion.
4. **Regression tests:** modified-path staleness (touch a file → `stale`), missing/unreadable metadata (→ `unknown`), health-check exception (→ `unknown`), chunker-mismatch (existing case, kept), and freshness-cache invalidation on build completion. The existing test coverage is chunker-mismatch ONLY (`test_server_tools.py` ~10281).
5. **Latency evidence:** before/after `code_ask` timing on this repo demonstrating the removed per-call walk (the fixed cost should drop out of `total_ms − vector_ms − rerank_ms`).

## Scope

**Problem statement:** the per-question freshness check is simultaneously the most expensive and least accurate part of `code_ask`'s response envelope.

**In scope:** `server_impl.py` `code_ask_response` freshness block + a shared cheap-freshness helper; seed-211/spec wording for the `unknown` state; tests.
**Out of scope:** retrieval/ranking changes; `wave_index_health` itself (already correct and explicitly-invoked).

## Acceptance Criteria

- [ ] AC-1: `code_ask` no longer calls `_layer_health` (or any O(corpus) walk) per invocation — source-pinned, plus before/after timing evidence on this repo.
- [ ] AC-2: A modified indexed file makes `index_freshness` report `stale` (the review's live-repro case, fixture-pinned); chunker mismatch still reports `stale`.
- [ ] AC-3: Freshness-check exceptions and undeterminable states report `unknown` — never `current` — fixture-pinned.
- [ ] AC-4: The cached verdict invalidates on build completion (fixture: stale → build → current without server restart).
- [ ] AC-5: Full suite bytecode-free + docs validation; seed-211/spec document the three-state contract.

## Tasks

- [ ] Shared cheap-freshness helper (stat-fast-path + chunker-version meta read + TTL/meta-signature cache).
- [ ] Wire into `code_ask_response`; remove the `_layer_health` call.
- [ ] Fixtures per AC-2/3/4; keep the chunker-mismatch case.
- [ ] Seed-211 + `mcp-tool-surface.md` three-state wording; suite + validate.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| helper+wiring | implementer | — | The fix |
| tests-docs | qa-reviewer | helper+wiring | Fixtures + contract docs |


## Serialization Points

- Shares `server_impl.py` response-envelope territory with `1seaq` (same wave) — coordinate the envelope fields once.

## Affected Architecture Docs

- `docs/specs/mcp-tool-surface.md` (`code_ask` response fields); seed-211 `index_freshness` guidance. N/A otherwise.

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The hot-path contract violation. |
| AC-2 | required | The live-reproduced wrong answer. |
| AC-3 | required | Silent-fresh-on-error is the 1sbfj lesson repeated. |
| AC-4 | required | A cache that never invalidates recreates defect 2. |
| AC-5 | required | Standard gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-12 | Drafted from the external code review (P0-1), every claim validated against `2952df8f`: `_layer_health` per call at ~17305 (contradicting its own docstring), chunker-only staleness at ~17306-08, `except → current` at ~17309-11; reviewer live-reproduced `current`-while-stale. Fix substrate (per-layer state, `project_index_inputs_stale`) shipped in wave 1sc7c. | Review report; source reads; `_layer_health` docstring (~639). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-12 | Freshness = stat-fast-path + chunker meta, three states, short cache — NOT a per-call hash walk and NOT dropping the check entirely. | The signal is genuinely useful to agents (seed-211 routes on it) but must cost microseconds, and honesty requires `unknown`. | **Drop `index_freshness`:** loses a documented, consumed signal. **Keep `_layer_health` but cache long:** still pays the walk sometimes, still ignores staleness causes between walks. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Stat-fast-path misses content-only changes with unchanged stats | Same trade the staleness monitor already accepts; the per-layer build path (1sc7c) is the authority — this is an advisory signal, and `unknown` covers indeterminacy. |
| Cache staleness window | Seconds-scale TTL + build-completion invalidation; fixture-pinned. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
