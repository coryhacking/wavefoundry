# Remove pre-v1.0.0 legacy compatibility code

Change ID: `12wsd-debt remove-pre-v1-legacy-compat`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-25
Wave: `12wsj framework-cleanup`

## Rationale

All downstream repositories have been upgraded to v1.0.0. The 0.9.0 bridge
release path and pre-semver date-shaped version string support are dead code.
Keeping them adds noise to scripts, seeds, and docs without providing any
protection — no install in the wild is running a version that needs these paths.

## Requirements

1. Remove the `_BRIDGE_VERSION = "0.9.0"` constant and `_legacy_bridge_artifact_name()`
   function from `build_pack.py`, along with all branch logic that produces
   `wavefoundry-YYYY-MM-DDx.zip` bridge artifacts.
2. Remove the date-shaped version string handling (`YYYY-MM-DDx → 0.0.0`) from
   `check_version.py`. Version strings that are not valid semver should raise
   `ValueError` — no silent mapping to `0.0.0`.
3. Remove the two bridge-specific tests from `test_build_pack.py`
   (`test_bridge_zip_filename_uses_legacy_date_shape`,
   `test_bridge_zip_filename_uses_next_legacy_suffix_for_same_day`). Update any
   remaining tests that use `"0.9.0"` as a placeholder version to use `"1.0.0"`.
4. Remove pre-semver date-string comparison tests from `test_check_version.py`.
5. Remove all "one-time `0.9.0` bridge release" language from seeds, replacing
   with plain semver-only descriptions. Remove `agent-workflows.zip` references
   from seeds where only mentioned for legacy context.
6. Remove `YYYY-MM-DDx` zip format references from `.wavefoundry/README.md` and
   `.wavefoundry/framework/README.md`.
7. Remove or simplify any legacy discovery / handling in `upgrade_wavefoundry.py`
   that specifically deals with date-shaped zip filenames.
8. All framework tests must pass after removal.

## Scope

**Problem statement:** Pre-v1.0.0 compatibility shims are live in scripts, tests,
seeds, and docs. They add maintenance surface and mislead new contributors about
what the framework actually supports.

**In scope:**

- `build_pack.py` — bridge artifact function and constant
- `check_version.py` — date-shaped version string handling
- `upgrade_wavefoundry.py` — date-shaped zip discovery/handling (if any)
- `tests/test_build_pack.py` — bridge-specific tests and 0.9.0 version references
- `tests/test_check_version.py` — pre-semver comparison tests
- `.wavefoundry/README.md` — `YYYY-MM-DDx` zip format references
- `.wavefoundry/framework/README.md` — same
- Seeds (`.wavefoundry/framework/seeds/`) — bridge release language, `agent-workflows.zip` legacy context
- Project docs under `docs/` referencing the 0.9.0 bridge or date-style artifacts

**Out of scope:**

- Generic upgrade instructions (keep these — they apply to all semver versions)
- The `YYYY-MM-DD` date format used in doc headers (`Last verified:`) and
  `docs_gardener.py` date arguments — these are unrelated to versioning
- Any `0.9.0` references that appear in closed wave records as historical fact

## Acceptance Criteria

- [x] AC-1: `python3 .wavefoundry/framework/scripts/run_tests.py` passes with no failures
- [x] AC-2: `grep -r "0\.9\.0\|bridge release\|YYYY-MM-DDx\|date-shaped\|date-style.*zip\|agent-workflows\.zip" .wavefoundry/framework/` returns no matches outside of closed wave records and this change doc
- [x] AC-3: `build_pack.py --version 0.9.0` raises an error or is blocked (0.9.0 is no longer a valid packaging target)
- [x] AC-4: `check_version.py` raises `ValueError` for a date-shaped string instead of silently returning `0.0.0`
- [x] AC-5: Docs gate passes (`wave_validate`, `wave_garden`)

## Tasks

- [x] Audit `build_pack.py` for bridge logic; remove `_BRIDGE_VERSION`, `_legacy_bridge_artifact_name()`, and all bridge-conditional branches
- [x] Audit `check_version.py`; remove date-shaped mapping; harden `ValueError` path
- [x] Audit `upgrade_wavefoundry.py`; remove date-shaped zip filename handling if present
- [x] Update `test_build_pack.py`: remove two bridge tests; replace `"0.9.0"` fixtures with `"1.0.0"`
- [x] Update `test_check_version.py`: remove pre-semver date-string tests
- [x] Grep seeds for "0.9.0 bridge", "date-style artifact", "agent-workflows.zip" legacy context; rewrite affected passages to semver-only
- [x] Update `.wavefoundry/README.md` and `.wavefoundry/framework/README.md`
- [x] Sweep `docs/` for bridge/date-style references outside closed wave records
- [x] Run full test suite; run docs gate

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| Scripts | Implementer | — | `build_pack.py`, `check_version.py`, `upgrade_wavefoundry.py` |
| Tests | Implementer | Scripts | Update after script changes to avoid chasing moving target |
| Seeds | Implementer | — | Independent of script changes; can run in parallel |
| Docs | Implementer | — | Independent sweep |

## Serialization Points

- Run `run_tests.py` only after both Scripts and Tests workstreams are complete

## Affected Architecture Docs

`docs/architecture/current-state.md` — references the bridge release and date-style
artifact naming; update to semver-only description.
`docs/architecture/data-and-control-flow.md` — same.
All other architecture docs: N/A — the change is removal of dead compatibility
paths, not a boundary or flow change.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Tests must pass |
| AC-2 | required | Confirms removal is complete |
| AC-3 | required | Prevents accidental bridge re-creation |
| AC-4 | required | Confirms the silent-swallow behavior is gone |
| AC-5 | required | Docs gate is always required |

## Progress Log

| Date | Update | Evidence |
|---|---|---|
| 2026-05-25 | Removed pre-v1 packaging/upgrade compatibility from runtime code, tests, seeds, and active operator docs. `build_pack.py` now blocks `<1.0.0`, `check_version.py` rejects non-semver strings, and semver-only zip discovery is enforced in `upgrade_wavefoundry.py`. | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_build_pack.py'`; `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_check_version.py'`; `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_upgrade_wavefoundry.py'`; `python3 .wavefoundry/framework/scripts/docs_lint.py`; `rg -n "0\\.9\\.0|bridge release|YYYY-MM-DDx|date-shaped|date-style.*zip|agent-workflows\\.zip" .wavefoundry/framework` returned no matches |
| 2026-05-25 | Full framework-suite proof completed after the earlier reranker baseline issue was cleared; docs gate remained green. | `python3 .wavefoundry/framework/scripts/run_tests.py` — 1620 tests, 0 failures; `python3 .wavefoundry/framework/scripts/docs_lint.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-25 | Remove all pre-v1.0.0 compat | All repos upgraded to 1.0.0; no installs need the bridge path | Keep bridge code — rejected, pure dead code |

## Risks

| Risk | Mitigation |
|---|---|
| Missed reference in a seed restores confusing instructions | AC-2 grep check catches any remaining matches |
| `check_version.py` ValueError breaks an unexpected caller | Audit all callers before removing the silent mapping |
