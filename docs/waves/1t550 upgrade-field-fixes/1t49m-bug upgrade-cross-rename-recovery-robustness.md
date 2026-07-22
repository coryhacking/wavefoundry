# Upgrade Robustness: Cross-Rename Hooks and Recovery-Phase Failure Markers

Change ID: `1t49m-bug upgrade-cross-rename-recovery-robustness`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-07-21
Wave: `1t550 upgrade-field-fixes`

## Rationale

Operator field report from live 1.14.0 pre-release upgrade testing in target repositories: three pack bugs required manual workarounds, so unassisted field upgrades would fail on them. All three are verified against the source:

1. `_stop_dashboard_for_lock_cutover` (upgrade_extensions.py:171) executes from the NEW archive during `pre_extract` but imports the INSTALLED (pre-extraction) `server_impl` and calls `wf_stop_dashboard_response` unconditionally. On a from-version that predates the tool rename, only `wave_dashboard_stop_response` exists, so the lock cutover raises before extraction ever runs — exactly the from-versions the lock cutover targets.
2. `pre_docs_gate` (upgrade_extensions.py:275) runs after extraction, but the docs-gate path resolves `review_evidence` through the pre-extraction `sys.modules` cache, so a projection/validator written for the new record format runs against the old module's code.
3. A failed `--resume-after-memory` records `failed_phase="index_update"` in the upgrade lock (upgrade_wavefoundry.py, standalone resume block); a subsequent SUCCESSFUL resume never clears the marker, so cleanup keeps refusing and the operator is forced into a full re-run despite a recovered state.

## Requirements

1. **Cross-rename dashboard stop:** `_stop_dashboard_for_lock_cutover` resolves the stop entry point by fallback — `wf_stop_dashboard_response` when present, else the retired `wave_dashboard_stop_response` — and raises the existing legible RuntimeError only when NEITHER exists. No behavior change on current-name installs.
2. **Fresh modules after extraction:** the post-extraction hook path (`pre_docs_gate` and any sibling that consumes framework modules the pre-upgrade runner may have cached) reloads `review_evidence` (and its stale cached dependents on the same path) via `importlib.reload` before invoking the projection/validation, so the newly extracted code is what runs. Loading by file path where already done stays; the reload covers the named-import seam.
3. **Recovery phases clear their own failure markers:** a successful `--resume-after-memory` (both the publication path and the already-complete/ready paths) clears `failed_phase` in the upgrade lock when the marker names the phase it just recovered (`index_update`), so cleanup proceeds without a full re-run. Failure still sets the marker exactly as today; markers for phases the resume did not recover are never cleared.
4. **Hermetic regression tests for all three:** (a) a stub installed `server_impl` exposing only the retired symbol passes the cutover; one exposing neither raises the legible error; (b) a cached stale `review_evidence` module is demonstrably replaced before the projection call; (c) a lock carrying `failed_phase="index_update"` is cleared by a successful resume and retained by a failed one and by markers naming other phases.
5. **No scope growth:** no changes to phase ordering, lock schema, or the memory-gate semantics; the three seams only.

## Scope

**Problem statement:** field upgrades crossing the tool rename fail at pre-extract lock cutover; post-extraction validation can run stale cached code; and a recovered resume leaves a permanent failure marker.

**In scope:**

- `upgrade_extensions.py` (`_stop_dashboard_for_lock_cutover`, `pre_docs_gate` and the module-cache seam)
- `upgrade_wavefoundry.py` (standalone `--resume-after-memory` success paths)
- `tests/test_upgrade_wavefoundry.py` additions

**Out of scope:**

- The 1.14.0 release mechanics themselves (a fresh pack build follows this wave)
- Upgrade phase ordering, lock file schema, memory backfill semantics

## Acceptance Criteria

- [x] AC-1: lock cutover succeeds against an installed `server_impl` exposing only the retired stop symbol; neither-symbol raises the legible RuntimeError; current-name behavior unchanged.
- [x] AC-2: the post-extraction docs-gate path runs the newly extracted `review_evidence`, proven by a test that plants a poisoned stale module in `sys.modules` and observes the fresh module's behavior.
- [x] AC-3: a successful `--resume-after-memory` clears `failed_phase="index_update"`; a failed resume and unrelated markers are retained; cleanup proceeds after the cleared marker without a full re-run.
- [x] AC-4: full framework test suite and docs validation pass.

## Tasks

- [x] Implement the getattr fallback in the lock-cutover dashboard stop.
- [x] Add the post-extraction module reload at the docs-gate seam.
- [x] Clear the recovered failure marker on successful resume paths.
- [x] Hermetic tests for all three; full suite + docs gate.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| three-seams | implementer | — | Disjoint edits in two files |
| tests | qa-reviewer | three-seams | Stub-module and lock-state fixtures from canonical shapes |

## Serialization Points

- None; the three seams are independent.

## Affected Architecture Docs

N/A: recovery-behavior bug fixes within the documented upgrade flow; `docs/prompts/upgrade-wavefoundry.prompt.md` and the spec's `wf_upgrade` phase table already describe the intended (now actual) behavior.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Blocks every field upgrade crossing the rename. |
| AC-2 | required | Stale-code validation can corrupt or falsely fail the docs gate. |
| AC-3 | required | Forces unnecessary full re-runs after successful recovery. |
| AC-4 | required | Standard gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-21 | Drafted from the operator's live cross-project 1.14.0 upgrade test report; all three sites verified against source (upgrade_extensions.py:171/:275; the standalone resume block's failure marker with no success-path clear). | Operator field report; code_keyword/sed verification reads. |
| 2026-07-21 | All three seams implemented: getattr fallback (retired symbol verified against git history as `wave_dashboard_stop_response`, present v1.9.1 through the rename), `_reload_cached_review_evidence` before the pre-docs-gate projection, `upgrade_lib.clear_failed_phase` called on both resume success paths. Seven hermetic tests added; module suite 339 OK; two known-bad mutation probes (neutered clear, neutered reload) both detected. | test_upgrade_wavefoundry.py: RuntimeLockCutoverMigrationTests (3 new), HistoricalMemoryUpgradeGateTests (3 new), HistoricalMemoryUpgradeExtensionBootstrapTests (1 new); in-process mutation probes. |
| 2026-07-21 | Requirement 2 sibling seam: `_installed_memory_backfill` had the identical stale-cache defect (its docstring promises the just-extracted coordinator, but a cached pre-extraction `memory_backfill` short-circuited the import); fixed with the same in-place reload plus a poisoned-cache test. Module suite 340 OK. | test_installed_memory_backfill_reloads_stale_cached_module_in_place |
| 2026-07-21 | AC-4 met: full framework suite 6,113/6,113 OK on the final tree (run_tests.py, 59 files); docs lint clean. | run_tests.py output; wf_validate_docs |
| 2026-07-21 | Gapfill: the retrieval_posture_gap advisory at close dry-run is a stage-attribution artifact, not a posture gap. Implementation exploration ran through the instrumented MCP tools (code_read, code_keyword, code_definition; 10 credited calls, 48,860 estimated tokens saved) but the wave was activated via wf_prepare_wave(mode='create') without wf_implement_wave, so context-efficiency focus never advanced past the plan stage and every call was attributed there. Harness shell was used only for executed probes (git-history oracle greps, test runs, mutation probes) and bulk doc-section writes, which the posture directive assigns to shell. | wave.md Context Efficiency block (plan: 10 calls; no implement row) |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-21 | getattr fallback at the call site, not a shim module. | One seam, self-documenting, dies naturally when pre-rename from-versions age out. | A compatibility shim exporting old names (broader surface than the one cross-version call needs). |
| 2026-07-21 | Clear only the marker naming the phase the resume recovered. | A recovery phase must not launder unrelated failures. | Clear failed_phase unconditionally on any success (masks unrecovered damage). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Reload breaks a consumer holding old module references. | Reload in place (importlib.reload preserves module identity); test observes the fresh behavior through the real call path. |
| Marker clear races a concurrent writer. | The upgrade lock is single-writer by design; the clear rides the existing update_upgrade_lock path. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
