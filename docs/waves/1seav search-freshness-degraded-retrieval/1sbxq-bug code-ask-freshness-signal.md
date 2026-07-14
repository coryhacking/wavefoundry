# `code_ask` Freshness Is Hot-Path-Expensive and Wrong (Ignores Stale Paths, Maps Errors to "current")

Change ID: `1sbxq-bug code-ask-freshness-signal`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-14
Wave: `1seav search-freshness-degraded-retrieval`

## Rationale

External code review (2026-07-12), validated against `2952df8f` — three defects in one block (`server_impl.py` `code_ask_response`, ~17303–17311):

1. **Hot-path contract violation:** every `code_ask` calls `index._layer_health("project")`, whose OWN docstring says "This is an O(total-indexed-bytes) operation — call it only via the explicit `wave_index_health` MCP tool, never on the search hot path." Every question pays a full walk-and-hash of the indexed corpus (~1,400 files on this repo; worse on field repos) before retrieval even starts.
2. **Wrong signal:** freshness is derived ONLY from chunker-version mismatch (`indexed_chunker_versions` vs `current_chunker_version`); the `stale_paths` that `_layer_health` just paid to compute are discarded. Live repro from the review session: `code_ask` reported `index_freshness: "current"` while `wave_index_health` reported two stale paths.
3. **Errors read as fresh:** `except Exception: is_stale = False` — any health failure silently reports `current`.

The cheap correct substrate now exists (wave 1sc7c): per-layer last-embedded hashes (`layer_path_state`) and `project_index_inputs_stale()` (the stat-fast-path check the staleness monitor already uses).

## Requirements

0. **(Reconciliation with wave `1sed7`, operator-directed 2026-07-12) Store-first, meta.json-free:** this change implements AFTER wave `1sed7 sqlite-only-index-state` and consumes ONLY the index-state store — per-layer hashes (`layer_path_state`), the canonical build-state row (chunker/model versions), and the build GENERATION as the cache-invalidation key. No `meta.json` reads: `1sed7` retires that file entirely, and any meta-based helper written here would be dead on arrival.
1. **Cheap freshness signal with the CORRECT authority:** replace the per-call `_layer_health` with a check that combines the stat-fast-path walk with **each layer's last-embedded hashes** (`layer_path_state`) — NOT `project_index_inputs_stale()` alone, which compares against broad `meta.json` `file_meta` and therefore reads `current` while a layer is stale (broad meta is stamped by ANY build; that cross-layer distinction is exactly what 1sc7c introduced per-layer state to preserve). Keep the chunker-version-mismatch check (a valid distinct staleness cause) via a cheap meta read. No per-call corpus hashing.
2. **Three honest states:** `index_freshness ∈ {"current", "stale", "unknown"}` — an exception or undeterminable state returns `"unknown"`, never silently `"current"`. Consumers (seed-211 guidance documents `index_freshness`) updated for the third state.
3. **Short-lived cache — BOTH invalidation axes required (P0 plan repair):** the cached verdict must carry (a) a root-scoped, seconds-scale TTL bounding edit-detection latency — the build GENERATION advances only when a build finalizes, so generation-only invalidation would cache `current` indefinitely between an edit and the next build — AND (b) epoch/generation invalidation (the `1sed7` build-state token) for immediate refresh the moment a build publishes, without waiting out the TTL. Neither axis alone is acceptable: TTL-only re-pays the check after every build for no reason; generation-only is blind to source edits.
4. **Regression tests:** modified-path staleness (touch a file → `stale`), missing/unreadable metadata (→ `unknown`), health-check exception (→ `unknown`), chunker-mismatch (existing case, kept), and freshness-cache invalidation on build completion. The existing test coverage is chunker-mismatch ONLY (`test_server_tools.py` ~10281).
5. **Latency evidence:** before/after `code_ask` timing on this repo demonstrating the removed per-call walk (the fixed cost should drop out of `total_ms − vector_ms − rerank_ms`).

## Scope

**Problem statement:** the per-question freshness check is simultaneously the most expensive and least accurate part of `code_ask`'s response envelope.

**In scope:** `server_impl.py` `code_ask_response` freshness block + a shared cheap-freshness helper; seed-211/spec wording for the `unknown` state; tests.
**Out of scope:** retrieval/ranking changes; `wave_index_health` itself (already correct and explicitly-invoked).

## Acceptance Criteria

- [x] AC-1: `code_ask` no longer calls `_layer_health` (or any O(corpus) walk) per invocation — source-pinned, plus before/after timing evidence on this repo.
- [x] AC-2: The LAYER-CROSSING regression is fixture-pinned in BOTH directions (`code_ask` searches both layers): (a) edit a code file; run a docs-only build that also processes a docs change → `stale`; rebuild docs only → still `stale`; rebuild code/all → `current`; (b) the INVERSE — edit a docs file; run a code-only build → `stale` until a docs/all build. Plus the simple case (modified file → `stale`), chunker mismatch → `stale`, an ADDED path → `stale`, a DELETED path → `stale`, and a legitimately EMPTY layer (zero eligible files) reading `current`, never `stale`/`unknown`.
- [x] AC-3: Freshness-check exceptions and undeterminable states report `unknown` — never `current` — fixture-pinned.
- [x] AC-4: BOTH cache axes are fixture-pinned: `current` → source edit → `stale` after the TTL elapses (generation unchanged — proves the TTL axis); and `stale` → completed build → `current` IMMEDIATELY on the generation change, without waiting out the TTL (proves the epoch axis); both without server restart.
- [x] AC-5: Full suite bytecode-free + docs validation; seed-211/spec document the three-state contract.

## Tasks

- [x] Shared cheap-freshness helper (stat-fast-path + per-layer `layer_path_state` + chunker-version store read; cache with BOTH axes — root-scoped seconds-scale TTL and 1sed7 build-generation invalidation). (`indexer.project_layer_freshness` + `server_impl._index_freshness_verdict`, TTL 5 s + `_epoch_state` token.)
- [x] Wire into `code_ask_response`; remove the `_layer_health` call. (Source-pinned; docstring three-state contract updated.)
- [x] Fixtures per AC-2 (both layer-crossing directions + added/deleted/empty-layer) /3/4 (both cache axes); keep the chunker-mismatch case. (`ProjectLayerFreshnessTests` 9 fixtures; `FreshnessCacheAxesTests` 4; CodeAsk envelope tests migrated.)
- [x] Seed-211 + `mcp-tool-surface.md` three-state wording; suite + validate. (Suite 4,940 OK; wave_validate green; rendered guru.md synced.)

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| helper+wiring | implementer | — | The fix |
| tests-docs | qa-reviewer | helper+wiring | Fixtures + contract docs |


## Serialization Points

- Shares `server_impl.py` response-envelope territory with `1seaq` (same wave) — coordinate the envelope fields once.
- DEPENDS on wave `1sed7 sqlite-only-index-state` (operator-decided order 2026-07-12): the freshness helper consumes its store API (build-state row, generation signal); implement after 1sed7 lands.

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
| 2026-07-13 | CLOSE-READINESS REVIEW (external, executed): AC-2/AC-3 reopened and re-met. Reproduced false-current: (a) full build → ADD code file → docs-only build (the broad snapshot stamps the new file; my layer compare only iterated recorded paths) and (b) unreadable `layer_hashes` → current. FIXED: `project_layer_freshness` rewritten around ONE walk with the build's own per-layer eligibility sets — the layer compare is now SYMMETRIC (recorded-path drift/deletion AND eligible-path-never-processed), layer hashes compare against the CURRENT walk hashes, and an unreadable REQUIRED layer (non-empty eligible set) reads unknown. Fixtures: `test_added_code_file_survives_docs_only_build` (the reviewer's exact reproduction + recovery), `test_unreadable_required_layer_state_reads_unknown`, exception-seam fixtures updated to the real seams. AC-5 gap closed: `mcp-tool-surface.md` now defines the three-state `index_freshness` contract. | Reviewer relay; indexer diff; ProjectLayerFreshnessTests 12/12. |
| 2026-07-13 | INDEPENDENT DELIVERY VERIFICATION (fresh-context adversarial agent, executed probes on scratch stores): epoch discipline, cache axes (no stale-after-finalize window — verdict flipped 0.12 s after a real build inside the TTL), root isolation, 8-thread concurrency hammer, symlink/permission/missing-config edge cases all CLEAN. ONE finding (MEDIUM, executed repro): a modified-but-unreadable file (perm change/AV lock mid-walk) made the walk pass return None, which the verdict coerced to `current` via the determinable layer-hash pass — the honesty rule violated one level below the caller's unknown-mapping. FIXED same-session: `current` now requires the walk pass to have POSITIVELY determined no changes (`walk_stale is False`); an undeterminable walk reads unknown. Regression fixture `test_unreadable_modified_file_reads_unknown_not_current` (chmod-000 repro + truth-after-restore). | Verifier report; indexer diff; ProjectLayerFreshnessTests 10/10. |
| 2026-07-13 | IMPLEMENTED (helper + wiring + cache + fixtures): `indexer.project_layer_freshness` combines the stat-fast-path walk (edits since any build) with per-layer `layer_path_state` hash compare against the broad snapshot (the layer-crossing signal — pure store reads) plus the chunker-version check; store-only, meta.json-free (Req 0). `server_impl._index_freshness_verdict` caches with BOTH axes (5 s root-scoped TTL + `_epoch_state` token). `code_ask_response` freshness = the verdict's three-state; `_layer_health` call removed (source-pinned) and docstring updated. Fixtures: `ProjectLayerFreshnessTests` (current-after-build, simple edit, BOTH layer-crossing directions with the second-scoped-build persistence check, added+deleted paths, empty-layer control, chunker mismatch, no-store→unknown, exception→unknown) 9/9; `FreshnessCacheAxesTests` (TTL axis with generation pinned unchanged; epoch axis without TTL wait; unknown passthrough; exception→unknown) 4/4; envelope passthrough + hot-path source pin in CodeAskTests. AC-1 latency evidence (live, this repo): OLD per-call `_layer_health` walk 457.1 ms → NEW 292.8 ms cold (at most once per TTL window/build transition) and 0.32 ms cached median — and the cold verdict honestly read `stale` against the uncommitted working tree. | Diffs; fixture runs; timing transcript. |
| 2026-07-13 | PRE-IMPLEMENTATION PLAN REVIEW (external) — P0 repair: Requirement 3's "TTL OR generation-keyed" wording permitted generation-only invalidation, which cannot detect source edits (the generation advances only at build finalization — an edit between builds would read `current` indefinitely). Now BOTH axes are required: root-scoped seconds-scale TTL (bounds edit-detection latency) AND build-generation invalidation (immediate post-build refresh); AC-4 rewritten to pin both sides independently. P1 repair: AC-2 freshness coverage was asymmetric — added the inverse docs-edit/code-only-build regression (code_ask searches both layers), added/deleted-path cases, and the legitimately-empty-layer control. | Plan review relay; `finalize_build_epoch` (sole generation advance) source ref. |
| 2026-07-12 | Reconciled with wave `1sed7` (operator-directed): Requirement 0 added — store-first, zero meta.json reads, cache keyed on 1sed7's build generation; this change now implements AFTER 1sed7. | Operator ordering decision; 1sed6 store API (build-state row + generation). |
| 2026-07-12 | Plan-review revision (external, validated): `project_index_inputs_stale()` DISALLOWED as the sole signal — it compares broad `meta.json` `file_meta` (verified `indexer.py:1215`), which any build stamps; the helper must consult per-layer `layer_path_state`. AC-2 rewritten to the exact layer-crossing regression (code edit → docs-only build stamps meta → must still read stale until a code/all build). | Plan review; `project_index_inputs_stale` source read. |
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
