# Dashboard: Use Shared Log Helper for Access Logs Too

Change ID: `12jnf-bug dashboard-log-helper-unified-format`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-12
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

Dashboard indexing diagnostics now use the shared timestamped dashboard log helper, but HTTP access logs still write their own client-first format. That leaves mixed log shapes in the same stderr stream and makes timeline scanning harder during troubleshooting.

## Requirements

1. Dashboard access logs must use the same shared log helper as index-builder and watcher diagnostics.
2. The shared helper must preserve useful access-log context such as the client address.
3. All dashboard stderr lines must keep a consistent timestamp-first prefix.
4. Verification must cover the access-log format.

## Scope

**Problem statement:** dashboard stderr output currently mixes two different formats because `DashboardHandler.log_message()` bypasses the shared helper.

**In scope:**

- `.wavefoundry/framework/scripts/dashboard_server.py`
  - Extend the shared dashboard log helper for optional context
  - Route `DashboardHandler.log_message()` through the shared helper
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
  - Add regression coverage for access-log formatting

**Out of scope:**

- Changing the content of the HTTP request message itself
- Changing dashboard UI behavior

## Acceptance Criteria

- AC-1: Access logs use the shared dashboard log helper.
- AC-2: Dashboard stderr output uses one timestamp-first format for both access and indexing logs.
- AC-3: Client address context remains present on access logs.
- AC-4: Verification passes.

## Tasks

- Extend shared dashboard log helper to support contextual prefixes
- Route `log_message()` through the helper
- Add regression for access-log format
- Run targeted tests and docs lint

## Affected Architecture Docs

N/A - operational log formatting only.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | The helper only pays off if the access-log path uses it too |
| AC-2 | required | Consistent logs are the operator-facing goal |
| AC-3 | important | Client context is still useful for request tracing |
| AC-4 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-12 | Change doc created after observing mixed access-log and index-log formats in live dashboard output. | Dashboard stderr log excerpt |
| 2026-05-12 | Routed HTTP access logs through the shared dashboard log helper so both request and indexing diagnostics now use the same timestamp-first format while preserving client address context. | `.wavefoundry/framework/scripts/dashboard_server.py`; `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'`; `./.wavefoundry/bin/docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-12 | Extend the shared dashboard log helper with optional context instead of keeping a separate access-log formatter | One helper enforces one log shape while still preserving client address context | Leave `log_message()` bespoke and merely copy the timestamp format (rejected: still duplicates formatting logic) |

## Risks

| Risk | Mitigation |
|------|------------|
| Refactoring the helper could break recent timestamp-log regressions | Keep the existing helper regression and add access-log coverage around the new context path |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
