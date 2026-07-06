# Upgrade log: surface the GRAPH_BUILDER_VERSION transition (fix dead-path pre-extract read)

Change ID: `1rvfx-bug upgrade-graph-version-transition-log`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-06
Wave: `1rvfy release-1p11-preship-hardening`

## Rationale

The upgrade flow logs an operator-visible "Framework version transitions detected: GRAPH_BUILDER_VERSION X → Y" line so an operator knows a graph re-extract will run (`upgrade_wavefoundry.py`, `_detect_version_transitions` + the Phase-0b transition log). Detecting the graph transition needs the INSTALLED (pre-extract) graph builder version, read by `_snapshot_pre_extract_versions`. That helper reads it from `.wavefoundry/framework/index/graph/framework-graph-state.json` (`upgrade_wavefoundry.py:647`) — a **dead path**: the framework-graph index layer was retired (ADR fold-framework-index-into-project-docs); the project graph state now lives at `.wavefoundry/index/graph/project-graph-state.sqlite` (with a legacy `project-graph-state.json` fallback). So in production the pre-extract snapshot never finds a `graph_builder` value, `_detect_version_transitions` never emits a `GRAPH_BUILDER_VERSION` transition, and the operator never sees the line — **even on a real graph-builder bump like 1.10.x → 1.11.0 (40 → 43)**. The existing tests pass only because their `_write_graph_state` helper writes to the same dead path.

This is cosmetic (log-only) — it does NOT affect the rebuild: the graph is materialized correctly during upgrade Phase 4b via `GraphStateStore.ensure_current()` regardless (verified in the `1rtvf` re-scope). But the transition line is exactly the signal that pairs with 1.11.0's new "reload MCP after a builder-version bump or the graph downgrades" guidance, so surfacing it is most valuable in this release. The fix is to read the installed builder version from the real project graph state.

## Requirements

1. **Read the installed graph builder version from the real location.** In `_snapshot_pre_extract_versions`, replace the dead `framework-graph-state.json` read with a read of the project graph state under `.wavefoundry/index/graph/` — the SQLite store `project-graph-state.sqlite` (`meta` table, `key='builder_version'`) with a fallback to the legacy monolithic `project-graph-state.json` (`builder_version` key) — mirroring `graph_indexer.read_state_builder_version`. Populate `out["graph_builder"]` with the value, or omit it when the state is absent/unreadable.
2. **Keep the upgrade module import-light.** Do NOT import `graph_indexer` (a heavy, tree-sitter-dependent module) into `upgrade_wavefoundry.py` at upgrade time — inline a tiny stdlib-`sqlite3` read (read-only URI open, no file creation) + a stdlib JSON fallback, consistent with the module's existing regex-based version reading (`_read_version_constant`, which deliberately avoids imports). Reference `read_state_builder_version` as the canonical implementation in a comment so the two stay conceptually linked.
3. **Read pre-extract; survives extraction.** The read must happen before zip extraction (it already does — `_snapshot_pre_extract_versions` is called pre-extract). The project index dir `.wavefoundry/index/` is not touched by extraction (only `.wavefoundry/framework/` is replaced), so the pre-extract read yields the OLD installed builder version and `_read_graph_builder_version_from_pack` (post-extract) yields the NEW one — the comparison then fires.
4. **Fail safe.** A missing/never-indexed project graph state, a corrupt store, or a locked DB yields no `graph_builder` entry (empty), never an exception — the upgrade must not fail because the graph-version probe could not read state (matches the historical missing-state contract of `read_state_builder_version`, which returns `""`).
5. **Update the tests to the real location.** The `_write_graph_state` test helper (and the `GRAPH_BUILDER_VERSION` transition tests) must write the installed builder version to the real project graph state path, not the dead framework path, so the tests exercise the production read path.

## Scope

**Problem statement:** The upgrade's pre-extract graph-builder snapshot reads a retired path, so the "GRAPH_BUILDER_VERSION X → Y" transition line never appears in a real upgrade log, even on a genuine builder bump.

**In scope:**

- `_snapshot_pre_extract_versions` graph-builder branch (`upgrade_wavefoundry.py`): read the real project graph state (sqlite + legacy JSON fallback) via an inlined stdlib reader.
- The `_write_graph_state` test helper + the `GRAPH_BUILDER_VERSION` transition tests in `test_upgrade_wavefoundry.py`: retarget to the real path.
- A test covering both the sqlite primary path and the legacy-JSON fallback path, plus the fail-safe (absent/corrupt state → no transition, no exception).

**Out of scope:**

- The graph rebuild mechanism itself (already correct via Phase 4b `ensure_current`; verified in `1rtvf`).
- `_detect_version_transitions` comparison logic (unchanged — it already compares `graph_builder` old vs pack; only the snapshot source is wrong).
- Chunker/walker snapshot reads (they read `.wavefoundry/index/meta.json`, which is correct).

## Acceptance Criteria

- [x] AC-1: With an installed project graph state at `.wavefoundry/index/graph/project-graph-state.sqlite` recording `builder_version = "42"` and a pack `GRAPH_BUILDER_VERSION = "43"`, `_snapshot_pre_extract_versions` returns `graph_builder = "42"` and `_detect_version_transitions` reports a `GRAPH_BUILDER_VERSION` transition. Deterministic test against the real path. Evidence: `_read_installed_graph_builder_version` (sqlite primary + JSON fallback); `test_snapshot_reads_sqlite_graph_state`.
- [x] AC-2: The legacy fallback works — an installed `.wavefoundry/index/graph/project-graph-state.json` with `builder_version` (no sqlite store) is read the same way. Evidence: `_write_graph_state` (test helper) now writes the legacy JSON path exercised by `test_snapshot_collects_all_version_constants` + the transition tests; `test_snapshot_sqlite_takes_precedence_over_legacy_json` confirms sqlite wins when both exist.
- [x] AC-3: Fail-safe — no project graph state present (fresh/never-indexed), or an unreadable/corrupt store, yields no `graph_builder` entry and no `GRAPH_BUILDER_VERSION` transition, and never raises. Evidence: `test_snapshot_graph_builder_absent_is_fail_safe`, `test_snapshot_graph_builder_corrupt_store_is_fail_safe`.
- [x] AC-4: No `graph_indexer` import is added to `upgrade_wavefoundry.py` (import-light preserved); the reader uses stdlib `sqlite3` + `json` only. Evidence: `_read_installed_graph_builder_version` uses a local `import sqlite3` + the module's existing `json`; no `graph_indexer` import.
- [x] AC-5: Full framework tests run bytecode-free and docs validation passes; the retargeted transition tests exercise the real production path. Evidence: full suite re-run at wave close; docs-lint clean.

## Tasks

- [x] Replace the dead-path graph-builder read in `_snapshot_pre_extract_versions` with an inlined stdlib reader of `.wavefoundry/index/graph/project-graph-state.sqlite` (`meta.builder_version`) + legacy `project-graph-state.json` fallback; fail-safe to no-entry.
- [x] Retarget `_write_graph_state` (test helper) + the transition tests to the real project graph state path; add sqlite-primary + legacy-JSON + fail-safe coverage.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| pre-extract-read | implementer | — | Inlined sqlite+json reader in `upgrade_wavefoundry.py` |
| tests | qa-reviewer | pre-extract-read | Retarget helper + primary/fallback/fail-safe coverage |


## Serialization Points

- Single-file production change in `upgrade_wavefoundry.py` (`_snapshot_pre_extract_versions`); no shared surface with `1rvfw` (dashboard). Both land in the same wave for the 1.11.0 ship.

## Affected Architecture Docs

- N/A — confined to the upgrade module's pre-extract version snapshot; no boundary/flow/contract change. It only corrects which on-disk file the installed graph builder version is read from so an existing operator-visible log line fires.

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The core fix — the transition must be detected from the real installed state. |
| AC-2 | important | Legacy `.json` state exists on pre-1p9q2 repos; the fallback keeps them covered. |
| AC-3 | required | The probe must never fail the upgrade; fail-safe is mandatory. |
| AC-4 | required | Import-lightness is a deliberate upgrade-module property; a heavy graph_indexer import at upgrade time is a regression risk. |
| AC-5 | required | Standard framework verification gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-06 | Split from the `1rtvf` "latent issue discovered" flag, to land before the official 1.11.0 ship (operator direction) so a 40 → 43 graph-builder bump surfaces in the upgrade log alongside the new reload guidance. | `1rtvf` Progress Log; `upgrade_wavefoundry.py:647` dead path; `graph_indexer.read_state_builder_version` (`:1414`) canonical read; `GRAPH_STORE_FILENAMES`/`GRAPH_STATE_FILENAMES`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-06 | Inline a small stdlib `sqlite3` + `json` reader in `upgrade_wavefoundry.py` rather than import `graph_indexer.read_state_builder_version`. | The upgrade module deliberately avoids imports of framework code that gets replaced during extraction (and `graph_indexer` is heavy / tree-sitter-dependent, and may not import cleanly in a minimal upgrade context). The state files + `meta` schema (`builder_version` key) are stable; the inline reader mirrors the canonical function and is stdlib-only. | Import `graph_indexer` and call `read_state_builder_version` (rejected — heavy import, dep-fragile at upgrade time). Import only the filename constants (rejected — still an import of the replaced module; the two constants are stable and greppable inline). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The inlined reader drifts from `read_state_builder_version` if the store schema/filename changes | Mirror the canonical function exactly (read-only sqlite URI, `meta` key `builder_version`, legacy JSON fallback) and reference it in a comment; a store-schema change is a major, coordinated event that would update both. |
| Reading the sqlite store creates/locks a file during upgrade | Use a read-only URI open (`?mode=ro`) with a short timeout, exactly as `read_state_builder_version` does — no file creation, sub-ms, never blocks. |
| A corrupt/locked store raises and aborts the upgrade | Catch `sqlite3.Error`/`OSError` → return no entry (fail-safe), matching the historical missing-state contract; AC-3 locks this. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
