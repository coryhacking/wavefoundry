# Dashboard: Ignore Packaging Artifacts in Framework Stale Detection

Change ID: `12j8w-bug framework-stale-ignore-packaging-artifacts`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-11
Wave: `12hsd dashboard-completed-wave-pending-filter`

## Rationale

The framework stale detector now uses the framework index `file_meta` snapshot as its primary source of truth, which correctly avoids git-dirty false positives in packaged target repositories. However, the comparison still includes framework packaging artifacts such as `MANIFEST` and `VERSION`, which are not semantic framework-doc inputs. That leaves a latent path where package-time artifact rewrites can make the shipped framework docs index appear stale immediately after upgrade even though the actual indexed framework content is unchanged.

## Requirements

1. Framework stale detection must ignore framework packaging artifacts that do not affect the semantic framework docs index contents.
2. Real framework docs inputs must still mark the framework layer stale when they change after the last build.
3. The wave record must include refreshed review evidence for the expanded admitted scope after this follow-up fix.
4. Verification must cover the packaging-artifact exclusion and the retained true-positive stale path.

## Scope

**Problem statement:** the framework file-meta stale path is the right mechanism, but it still compares a few pack-only framework files that can change independently of semantic framework docs content.

**In scope:**

- `.wavefoundry/framework/scripts/dashboard_server.py`
  - Exclude packaging-only framework artifacts from the framework file-meta stale comparison
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
  - Add regressions for ignored packaging artifacts and preserved real stale detection
- `docs/waves/12hsd dashboard-completed-wave-pending-filter/wave.md`
  - Refresh review evidence so the current wave record reflects the expanded reviewed scope

**Out of scope:**

- Redesigning package layout
- Changing project-layer stale detection

## Acceptance Criteria

- AC-1: `_index_is_stale(..., "framework")` returns `False` when only `MANIFEST` or `VERSION` differs from the stored framework `file_meta`.
- AC-2: `_index_is_stale(..., "framework")` still returns `True` for real framework docs input changes.
- AC-3: Wave review evidence reflects the refreshed full-scope review.
- AC-4: Verification passes.

## Tasks

- Exclude packaging artifacts from framework file-meta stale comparison
- Add regressions for `MANIFEST` / `VERSION`
- Refresh wave review evidence after the fixes land
- Run targeted dashboard tests, full suite, and docs lint

## Affected Architecture Docs

N/A - stale-input filtering and review-record refresh only.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Prevents stale-on-arrival packaged framework indexes |
| AC-2 | required | Preserves the intended stale signal |
| AC-3 | important | Closes the review-traceability gap identified in formal review |
| AC-4 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-11 | Change doc created to address the formal review findings about packaging-artifact stale signals and missing refreshed wave-level review evidence. | Formal review findings; `dashboard_server.py`; `wave.md` |
| 2026-05-11 | Framework stale detection now ignores `MANIFEST` and `VERSION`, preserving real framework-input stale signals without treating packaging artifacts as semantic index inputs. Full dashboard tests, the full framework suite, and docs lint passed. | `dashboard_server.py`; `test_dashboard_server.py`; `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'`; `python3 -B .wavefoundry/framework/scripts/run_tests.py`; `./.wavefoundry/bin/docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-11 | Exclude pack-only artifacts from framework file-meta stale comparison instead of rebuilding the framework index a second time during packaging | `MANIFEST` and `VERSION` are not semantic framework-doc inputs, so the stale detector should not care about them | Double-build the framework index during packaging (rejected: more expensive and fixes the symptom in a narrower place) |

## Risks

| Risk | Mitigation |
|------|------------|
| Excluding too many files could hide real stale inputs | Restrict the exclusion to packaging-only filenames with dedicated regressions |
| Review evidence could still be ambiguous about approval scope | Refresh the wave review section explicitly after the fixes and verification complete |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
