# Dashboard: Project Stale Detection Uses Git History Instead of Indexed Inputs

Change ID: `12jnb-bug project-stale-use-index-inputs-not-git-history`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-12
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The dashboard server now uses framework index `file_meta` as the primary source of truth for framework-layer staleness, but the project layer still falls back directly to git commit/status checks. That leaves a path where successful project index rebuilds can loop indefinitely: the current project tree may already match the indexed project inputs while post-build commit history or host-local `.wavefoundry` runtime files still make `_index_is_stale(..., "project")` return `True`.

## Requirements

1. Project-layer stale detection must prefer the project index `file_meta` snapshot when available, mirroring framework-layer behavior.
2. Host-local operational files that are not semantic project inputs must not make the project index look stale.
3. Real project docs/code input changes must still mark the project layer stale.
4. Verification must cover the false-positive loop and the retained true-positive path.

## Scope

**Problem statement:** project-layer periodic stale checks can keep scheduling auto-index rebuilds even after successful project index updates because git-history/runtime-state signals are broader than the actual indexed project inputs.

**In scope:**

- `.wavefoundry/framework/scripts/dashboard_server.py`
  - Add project-layer `file_meta`-based stale detection
  - Exclude host-local runtime artifacts from project input comparison
- `.wavefoundry/framework/scripts/indexer.py`
  - Exclude host-local operational artifacts from project index inputs if needed for parity with stale detection
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
  - Add regressions for project-layer false positives and retained real stale detection

**Out of scope:**

- Reworking framework-layer stale detection
- Changing dashboard UI behavior

## Acceptance Criteria

- AC-1: `_index_is_stale(..., "project")` returns `False` when current indexed project inputs match `file_meta`, even if git history after `built_at` exists.
- AC-2: Host-local `.wavefoundry` runtime files do not by themselves keep the project layer stale.
- AC-3: Real project input changes still return `True` for project-layer staleness.
- AC-4: Verification passes.

## Tasks

- Add project-layer `file_meta` stale path
- Exclude project runtime artifacts from semantic project-input comparisons
- Add regressions for idle-loop false positives and real project changes
- Run targeted dashboard tests and full verification

## Affected Architecture Docs

N/A - stale detector implementation alignment only.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Stops repeated idle rebuilds after successful project updates |
| AC-2 | required | Prevents operational `.wavefoundry` state from polluting semantic project freshness |
| AC-3 | required | Preserves the intended stale signal |
| AC-4 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-12 | Change doc created after confirming the project layer was still using git-history stale detection while the framework layer already preferred `file_meta`. | `dashboard_server.py`; `.wavefoundry/index/meta.json`; local stale-check repro |
| 2026-05-12 | Project-layer stale detection now prefers project index `file_meta`, excludes host-local `.wavefoundry` runtime artifacts from semantic project inputs, and preserves true-positive stale detection for real project changes. | `.wavefoundry/framework/scripts/dashboard_server.py`; `.wavefoundry/framework/scripts/indexer.py`; `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'`; `python3 -B .wavefoundry/framework/scripts/run_tests.py`; `./.wavefoundry/bin/docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-12 | Align project-layer stale detection with the framework-layer `file_meta` model | Indexed inputs are the actual semantic source of truth; git history and host-local runtime files are too broad | Keep git-history primary and add more ad hoc exclusions (rejected: brittle and still broader than indexed inputs) |

## Risks

| Risk | Mitigation |
|------|------------|
| Excluding too much from project input comparison could hide real stale inputs | Limit exclusions to host-local operational files and preserve true-positive tests for real project docs/code changes |
| Older project indexes may not have `file_meta` | Retain git-based logic as a fallback when `file_meta` is absent |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
