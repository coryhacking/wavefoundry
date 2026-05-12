# Dashboard: Use Framework Index Inputs Instead of Git Dirty State

Change ID: `12j7k-bug framework-stale-use-index-inputs-not-git-dirty`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-11
Wave: `12hsd dashboard-completed-wave-pending-filter`

## Rationale

The framework-layer auto-index stale detector still rebuilds continuously in post-upgrade repositories even after excluding `__pycache__`, `.pyc`, and collapsed untracked directory placeholders. The deeper issue is that the framework docs index is packaged into target repositories as an untracked framework tree, so git dirtiness is not a reliable source of truth for that layer. The dashboard keeps treating untracked framework files as stale candidates even when the actual framework index inputs are unchanged and already reflected in the latest framework `meta.json`.

## Requirements

1. When framework index `meta.json` includes `file_meta`, framework stale detection must compare the current framework index inputs against that stored file snapshot instead of using git dirty state.
2. The framework stale detector must still return `True` when a real framework index input file changes after the last build.
3. Legacy framework indexes without `file_meta` must retain a safe fallback path.
4. Dashboard regression coverage must prove the framework layer does not retrigger solely because git reports an untracked framework tree.
5. Dashboard verification must pass.

## Scope

**Problem statement:** git-status-based stale detection is a poor fit for the packaged framework docs layer because the packaged framework tree is intentionally untracked in target repositories, so “dirty” does not imply “newer than the last framework docs index build.”

**In scope:**

- `.wavefoundry/framework/scripts/dashboard_server.py`
  - Use framework `file_meta` snapshot comparison when available
  - Keep a legacy fallback for old indexes that do not have `file_meta`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
  - Add regressions for file-meta-based framework freshness and real file-meta-detected framework staleness

**Out of scope:**

- Replacing project-layer git-based stale detection
- Redesigning the framework docs index contents or package layout

## Acceptance Criteria

- AC-1: `_index_is_stale(..., "framework")` returns `False` when framework `file_meta` matches the current framework inputs, even if git would report the framework tree as untracked.
- AC-2: `_index_is_stale(..., "framework")` returns `True` when a framework index input differs from the stored framework `file_meta`.
- AC-3: Legacy framework indexes without `file_meta` still behave safely.
- AC-4: Dashboard verification passes.

## Tasks

- Add a file-meta-based framework stale path
- Preserve a fallback path for legacy framework indexes
- Add regressions for matching and changed framework file_meta cases
- Run dashboard verification and docs lint

## Affected Architecture Docs

N/A - framework stale-source selection fix within the existing dashboard/index flow.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Stops the remaining idle rebuild loop in packaged target repos |
| AC-2 | required | Preserves real framework stale detection |
| AC-3 | important | Keeps older framework indexes from regressing |
| AC-4 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-11 | Change doc created after operator logs showed the framework layer still rebuilding every periodic stale cycle even after cache-artifact and collapsed-directory exclusions. | Operator dashboard log; `dashboard_server.py` |
| 2026-05-11 | Switched the framework stale detector to compare current framework index inputs against the framework index `file_meta` snapshot when available, with git-based detection retained only as a legacy fallback, and added regressions covering both the matching and changed framework-file-meta cases. | `dashboard_server.py`; `test_dashboard_server.py`; `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'`; `./.wavefoundry/bin/docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-11 | Use framework `file_meta` snapshot comparison when available instead of git dirty state | The packaged framework tree is intentionally untracked in target repos, so git dirtiness is not the right stale signal | Keep adding git-path exclusions (rejected: symptom-level and brittle) |

## Risks

| Risk | Mitigation |
|------|------------|
| File-meta comparison could diverge from the actual framework build input set | Reuse the same framework-prefix walker/filter path the framework index build uses |
| Legacy indexes may not carry `file_meta` yet | Retain a safe fallback path when `file_meta` is absent or malformed |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
