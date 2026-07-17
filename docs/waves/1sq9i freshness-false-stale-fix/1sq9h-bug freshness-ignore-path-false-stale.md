# Freshness reports permanent false-stale for ignore-listed recorded layer-state paths

Change ID: `1sq9h-bug freshness-ignore-path-false-stale`
Change Status: `implemented`
Owner: framework
Status: implemented
Last verified: 2026-07-16

Wave: `1sq9i freshness-false-stale-fix`

## Rationale

`project_layer_freshness` (`indexer.py`, wave 1seav/1sbxq — **new in unreleased 1.13.0**) applies `_PROJECT_STALE_IGNORE_PATHS` to the walk (`walk_files`) and to the stored snapshot (`filtered_file_meta`), but **not** to the recorded per-layer hash state it compares them against. The build stamps `docs/references/codebase-map.md` (a `_PROJECT_STALE_IGNORE_PATHS` entry — deliberately ignored because the map regenerates every build) into the docs layer state. The per-layer loop iterates that recorded state, looks each path up in the two *ignore-filtered* maps, finds no entry for the ignored path, and takes the `layer_stale = True` "recorded path gone" branch → reason `"layer behind broad snapshot"` → envelope `index_freshness: "stale"`.

The asymmetry is one-sided filtering: state paths are compared against ignore-filtered maps, so any ignored-but-recorded path reads as "gone" forever.

**Field impact (Aceiss team, 1.13.0+pcni):** every `code_ask` reports `index_freshness: "stale"` while `wave_index_health` reports fully current (0 stale paths). The prescribed remediation `wave_index_build(content="docs", mode="update")` is a no-op ("index is up to date") and never clears the verdict — so agents burn a build round-trip per session that cannot help, and a real stale verdict becomes indistinguishable from this false one. Default-hitting: any repo with a generated codebase map (the default).

**Confirmed on this repo:** `docs/references/codebase-map.md` is present in the docs layer state (1,386 entries) and in `_PROJECT_STALE_IGNORE_PATHS`, and is filtered out of `filtered_file_meta` — the exact false-stale trigger (masked here only because the dirty working tree currently sets `walk_stale=True`).

## Requirements

1. Apply `_PROJECT_STALE_IGNORE_PATHS` **uniformly** to every comparison input in `project_layer_freshness`: the recorded per-layer `state` iteration AND the per-layer `eligible` sets — mirroring the filtering already applied to `walk_files` and `filtered_file_meta`. An ignore-listed path must not drive a staleness verdict from any direction.
2. The fix must be **read-side** so it heals existing (already-built) indexes in place, with no rebuild and no re-embedding required.
3. A regression probe: after a full build that stamps an ignore-listed path (`docs/references/codebase-map.md`) into layer state, `project_layer_freshness` returns `stale: False` / `reason: "current"` with no intervening edits — and the probe must fail against the pre-fix code.

## Scope

**Problem statement:** One-sided ignore filtering in `project_layer_freshness` makes every repo with a generated codebase map report a permanent, unrecoverable false `index_freshness: "stale"`.

**In scope (edited under `framework_edit_allowed`):**
- `.wavefoundry/framework/scripts/indexer.py` — `project_layer_freshness`: filter `_PROJECT_STALE_IGNORE_PATHS` from the `state` iteration loop and from the `docs_eligible`/`code_eligible` sets.
- `.wavefoundry/framework/scripts/tests/test_indexer.py` — `ProjectLayerFreshnessTests`: add the ignore-path regression probe.

**Out of scope:**
- Removing `docs/references/codebase-map.md` from `_PROJECT_STALE_IGNORE_PATHS` (it is correctly ignored; the bug is the comparison, not the membership).
- Build-side change to stop stamping ignore-listed paths into layer state — the read-side fix heals in place and is sufficient; a build-side change would only take effect after a rebuild and is deferred.
- Surfacing the freshness `reason`/`layers` in the `code_ask` envelope (the downstream agent had to call the underlying check to see the reason) — a real observability improvement, but a separate enhancement, not this correctness fix.
- The per-citation `freshness.drifted` / `commits_since_verified` fields — verified working-as-designed by the field report; unaffected.

## Acceptance Criteria

- [x] AC-1: `project_layer_freshness` filters `_PROJECT_STALE_IGNORE_PATHS` from the recorded-state iteration, so an ignore-listed recorded path never triggers the "recorded path gone" branch. (required) — evidence: skip added at the top of the `state.items()` loop (indexer.py).
- [x] AC-2: `project_layer_freshness` filters `_PROJECT_STALE_IGNORE_PATHS` from the `eligible` sets, so an ignore-listed path never triggers the symmetric "eligible path not in state" branch. (required) — evidence: `docs_eligible`/`code_eligible -= _PROJECT_STALE_IGNORE_PATHS` after the union.
- [x] AC-3: A regression test seeds `docs/references/codebase-map.md`, runs a full build, and asserts `project_layer_freshness` returns `stale: False` / `reason: "current"` with no intervening edits. The test fails against the pre-fix code (non-vacuous). (required) — evidence: `test_ignore_listed_recorded_state_path_stays_current`; non-vacuity proven by source mutation (disabled skip → `AssertionError: True is not False : layer behind broad snapshot`).
- [x] AC-4: The fix is read-side only — no build/stamping change, no rebuild required to heal an already-built index. (required) — evidence: only `project_layer_freshness` (a read-time computation) changed; no build/stamp path touched.
- [x] AC-5: Full framework suite green; docs-lint clean. (required) — evidence: full suite 5,644 OK (test_indexer 267); docs-lint clean.

## Tasks

- [x] Add `_PROJECT_STALE_IGNORE_PATHS` skip at the top of the `state.items()` loop in `project_layer_freshness`.
- [x] Subtract `_PROJECT_STALE_IGNORE_PATHS` from `docs_eligible` and `code_eligible`.
- [x] Add the ignore-path regression probe to `ProjectLayerFreshnessTests`; confirm it fails pre-fix (source mutation) and passes post-fix.
- [x] Correct the misleading `_PROJECT_STALE_IGNORE_PATHS` comment (it claimed "resource-read" regenerates the map; a normal read only regenerates when the file is missing — verified against `resource_codebase_map`).
- [x] Run the full suite + docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| fix | framework | — | `indexer.py` project_layer_freshness under `framework_edit_allowed` |
| regression | framework | fix | test_indexer.py probe; prove non-vacuity by source mutation |


## Serialization Points

- `.wavefoundry/framework/scripts/indexer.py` — edited under `framework_edit_allowed`.

## Affected Architecture Docs

`N/A` — localized fix to one function's filter discipline; no boundary/flow/verification-topology change. (`docs/architecture/chunking-and-indexing-pipeline.md` describes the freshness signal but requires no update for this correctness fix.)

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The load-bearing fix — the observed false-stale branch |
| AC-2 | required | Closes the symmetric variant so the same bug can't regrow |
| AC-3 | required | Non-vacuous regression pinning the field-reported failure |
| AC-4 | required | Must heal existing stuck indexes without a rebuild |
| AC-5 | required | No regression to the broader freshness/indexer contract |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-16 | Field bug report (Aceiss team) root-caused + confirmed on this repo | `docs/references/codebase-map.md` in docs state ∩ `_PROJECT_STALE_IGNORE_PATHS`, absent from `filtered_file_meta` |
| 2026-07-16 | Implemented: state-loop skip + eligible subtraction; regression probe proven non-vacuous by source mutation; corrected the misleading ignore-list comment (reads regenerate the map only when it is missing, not on every read — verified vs `resource_codebase_map`) | Full suite 5,644 OK; disabled-fix run fails with `layer behind broad snapshot` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-16 | Read-side uniform ignore filter (state loop + eligible) | Heals existing indexes in place; closes both directions of the asymmetry | Build-side stop-stamping (rejected as primary — needs rebuild to heal) |
| 2026-07-16 | Fold into unreleased 1.13.0 | The freshness signal is new in 1.13.0; do not ship a cry-wolf verdict | Ship 1.13.0 and fast-follow (rejected — default-hitting, degrades the signal's trust on first release) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Filtering eligible masks a genuine ignore-path staleness | Ignore-listed paths are by definition excluded from staleness (they regenerate every build); that is the intended contract |
| Regression test vacuously passes | AC-3 requires it to fail against pre-fix code (source mutation) |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
