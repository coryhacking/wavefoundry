# Dashboard: Ignore Runtime Cache Artifacts in Framework Stale Detection

Change ID: `12j3g-bug framework-stale-ignore-pycache`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-11
Wave: `12hsd dashboard-completed-wave-pending-filter`

## Rationale

The dashboard framework-layer stale monitor currently treats Python runtime cache artifacts as framework-source edits. In post-upgrade repositories where the framework files are unpacked from the Wavefoundry zip but not committed, `git status --porcelain` can surface `.wavefoundry/framework/scripts/__pycache__/` as an untracked framework path. Because `_index_is_stale()` compares matching dirty-path mtimes against the last framework index build time, normal Python imports keep the cache directory newer than `built_at`, and the dashboard rebuilds the framework docs index repeatedly while idle.

## Requirements

1. Framework stale detection must ignore runtime cache artifacts such as `__pycache__/` directories and `.pyc` files.
2. The exclusion must apply before path-to-layer routing so cache artifacts never count as project or framework source changes.
3. The packaged framework should include a local ignore rule that suppresses framework script cache artifacts from downstream `git status` output where possible.
4. Existing framework-source stale detection must continue to work for real framework edits.
5. Dashboard framework staleness tests must cover the cache-artifact exclusion.

## Scope

**Problem statement:** the framework index stale detector is operationally correct for real source edits but over-broad for Python runtime cache outputs, causing endless framework index rebuilds in idle dashboard sessions.

**In scope:**

- `.wavefoundry/framework/scripts/dashboard_server.py`
  - Exclude runtime cache artifacts from stale-path matching before layer routing
- `.wavefoundry/framework/scripts/.gitignore`
  - Ignore script-local `__pycache__/` and `.pyc` artifacts for downstream repos consuming the pack
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
  - Add regressions proving cache artifacts do not mark the framework layer stale

**Out of scope:**

- Changing project-layer stale semantics beyond the shared cache-artifact exclusion
- Redesigning dashboard auto-index cadence or polling intervals

## Acceptance Criteria

- AC-1: `_index_is_stale(..., "framework")` returns `False` when the only dirty framework path is `__pycache__/` or `.pyc`.
- AC-2: Real dirty framework source files still mark the framework layer stale when newer than `built_at`.
- AC-3: The packaged framework scripts tree includes a local ignore rule for cache artifacts.
- AC-4: Dashboard verification passes.

## Tasks

- Exclude cache artifacts from stale-path matching
- Add a framework-local ignore file for script caches
- Add regression coverage for ignored cache artifacts
- Run dashboard verification and docs lint

## Affected Architecture Docs

N/A — stale-path filtering fix within the existing dashboard/index flow.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Stops the infinite rebuild loop |
| AC-2 | required | Preserves the original monitor purpose |
| AC-3 | important | Reduces downstream false positives before code reaches mtime checks |
| AC-4 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-11 | Change doc created for the idle framework-index rebuild loop caused by `__pycache__/` and `.pyc` artifacts appearing as dirty framework paths. | Operator report; `dashboard_server.py` |
| 2026-05-11 | Excluded `__pycache__/` directories and `.pyc` files from shared index-layer stale matching, added a packaged scripts-local `.gitignore` for the same artifacts, and added framework stale regressions proving cache-only dirty paths do not trigger rebuilds. | `dashboard_server.py`; `.wavefoundry/framework/scripts/.gitignore`; `test_dashboard_server.py`; `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'`; `./.wavefoundry/bin/docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-11 | Filter cache artifacts in shared layer matching rather than only inside the framework branch of `_index_is_stale()` | Keeps project/framework behavior consistent and prevents these paths from ever counting as source changes | Filter only in the framework status loop (rejected: narrower than the actual invariant) |

## Risks

| Risk | Mitigation |
|------|------------|
| Over-broad filtering could hide legitimate source files | Restrict the exclusion to `__pycache__/` path segments and `.pyc` suffixes only |
| Downstream repos may still have other cache files in status output | Add a local ignore file for the known Python cache artifacts while keeping the code-level exclusion authoritative |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
