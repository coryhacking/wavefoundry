# Dashboard: Ignore Collapsed Untracked Directory Entries in Framework Stale Detection

Change ID: `12j7e-bug framework-stale-ignore-untracked-directory-entries`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-11
Wave: `12hsd dashboard-completed-wave-pending-filter`

## Rationale

The prior `__pycache__` / `.pyc` exclusion fixed one idle framework-index rebuild loop, but the dashboard can still rebuild the framework layer continuously in post-upgrade repositories where the unpacked framework is not yet committed to git. In that state, `git status --porcelain` may collapse untracked framework content into directory entries such as `.wavefoundry/framework/`. `_index_is_stale()` currently stats that directory path directly, and its mtime moves whenever the dashboard rewrites `.wavefoundry/framework/index/` during a rebuild. That makes the framework layer appear stale again on the next periodic check even when no framework source files changed.

## Requirements

1. Framework stale detection must not treat collapsed untracked directory entries as evidence that framework source changed after the last build.
2. The stale detector must still detect real untracked or modified framework source files that postdate `built_at`.
3. Dashboard regression coverage must include an untracked framework directory entry that would otherwise self-trigger after an index rebuild.
4. Dashboard verification must pass.

## Scope

**Problem statement:** the framework stale detector still has a self-triggering path when git reports untracked directories instead of file-level entries, because directory mtimes change when excluded framework index outputs are rewritten beneath them.

**In scope:**

- `.wavefoundry/framework/scripts/dashboard_server.py`
  - Change git-status stale detection to avoid directory-mtime false positives from collapsed untracked entries
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
  - Add regressions for collapsed untracked framework directories and retained real-file stale detection

**Out of scope:**

- Redesigning the auto-index scheduling cadence
- Changing project/framework layer boundaries beyond the git-status path granularity fix

## Acceptance Criteria

- AC-1: `_index_is_stale(..., "framework")` returns `False` when git status reports only an untracked framework directory entry whose mtime is advanced by framework index writes.
- AC-2: `_index_is_stale(..., "framework")` still returns `True` for real untracked or modified framework source files newer than `built_at`.
- AC-3: Dashboard verification passes.

## Tasks

- Change framework/project stale detection to use file-level untracked paths instead of directory mtimes
- Add a regression for the collapsed untracked framework directory case
- Reconfirm real-file stale detection still works
- Run dashboard verification and docs lint

## Affected Architecture Docs

N/A - stale detection granularity fix within the existing dashboard/index flow.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Stops the remaining idle rebuild loop |
| AC-2 | required | Preserves the stale detector's intended signal |
| AC-3 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-11 | Change doc created for the remaining idle framework-index rebuild loop caused by collapsed untracked framework directory entries from `git status --porcelain`. | Operator log; `dashboard_server.py` |
| 2026-05-11 | Switched stale detection to request file-level untracked entries from git status, ignored any remaining directory placeholder paths before mtime comparison, and added regressions for collapsed untracked framework directories plus retained real-file stale detection. | `dashboard_server.py`; `test_dashboard_server.py`; `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'`; `./.wavefoundry/bin/docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-11 | Prefer file-level untracked path reporting over directory-mtime checks | Directory mtimes are noisy and can advance when excluded index outputs change underneath them | Add another special-case directory exclusion (rejected: symptom-level and incomplete) |

## Risks

| Risk | Mitigation |
|------|------------|
| Expanding untracked directories to file-level entries may slightly increase git-status parsing cost | The stale check already runs infrequently, and correctness is more important than the small extra output volume |
| Parsing changes could miss legitimate stale files | Add regressions for both the false-positive directory case and the retained true-positive file case |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
