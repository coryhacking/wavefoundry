# Dashboard: Add Timestamps to Indexing Logs

Change ID: `12jne-enh dashboard-log-timestamps`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-12
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

Dashboard request logs already include timestamps, but index-builder and watcher diagnostics still emit bare `[dashboard] ...` lines. That makes it harder to correlate scheduled, started, completed, and failed index events during troubleshooting.

## Requirements

1. Dashboard index-builder diagnostic logs must include an explicit timestamp.
2. Related dashboard watcher/stale-check diagnostics should use the same timestamped format for consistency.
3. Existing log content should remain readable and preserve layer/reason details.
4. Verification must cover the emitted format.

## Scope

**Problem statement:** dashboard operational logs for indexing events are missing timestamps, making it difficult to correlate auto-index triggers and rebuild durations.

**In scope:**

- `.wavefoundry/framework/scripts/dashboard_server.py`
  - Add a shared timestamped dashboard log writer
  - Route index-builder and nearby operational diagnostics through it
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
  - Add regression coverage for timestamped indexing logs

**Out of scope:**

- Changing HTTP access log formatting
- Changing dashboard UI behavior

## Acceptance Criteria

- AC-1: IndexBuilder scheduled/start/completed log lines include timestamps.
- AC-2: Stale/startup and watcher diagnostics use the same timestamped format.
- AC-3: Existing reason/layer context is preserved.
- AC-4: Verification passes.

## Tasks

- Add shared timestamped dashboard log helper
- Migrate indexing and watcher diagnostics to the helper
- Add regression for timestamped log output
- Run targeted tests and docs lint

## Affected Architecture Docs

N/A - operational log formatting only.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Operators need timestamps on the main indexing lifecycle logs |
| AC-2 | important | Consistent formatting reduces troubleshooting ambiguity |
| AC-3 | required | The existing trigger detail must remain intact |
| AC-4 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-12 | Change doc created to add timestamps to dashboard indexing diagnostics after operator review of repeated stale-check logs. | Dashboard stderr log excerpt |
| 2026-05-12 | Added a shared timestamped dashboard log helper and routed index-builder, startup-stale, watcher, and bind-warning diagnostics through it while preserving layer/reason details. | `.wavefoundry/framework/scripts/dashboard_server.py`; `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'`; `./.wavefoundry/bin/docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-12 | Use one shared dashboard stderr helper for timestamped diagnostics | Keeps operational log formatting consistent across index-builder and watcher paths | Add timestamps piecemeal at each call site (rejected: brittle and inconsistent) |

## Risks

| Risk | Mitigation |
|------|------------|
| Touching all log call sites could break existing string-based tests | Add focused regression coverage around emitted format while preserving message bodies |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
