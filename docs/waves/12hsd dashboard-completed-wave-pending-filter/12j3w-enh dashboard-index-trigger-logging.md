# Dashboard: Log Index Rebuild Triggers

Change ID: `12j3w-enh dashboard-index-trigger-logging`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-11
Wave: `12hsd dashboard-completed-wave-pending-filter`

## Rationale

The dashboard can auto-rebuild the project and framework indexes in the background, but the current stderr output does not tell an operator which layer is being updated or why a rebuild was scheduled. That makes it hard to distinguish expected stale-driven updates from noisy or accidental rebuild loops when the dashboard is left running.

## Requirements

1. Dashboard index rebuild logging must identify which index layer is being updated (`project`, `framework`, or both).
2. The log must record the trigger reason for each scheduled rebuild.
3. Startup stale rebuilds and periodic stale-check rebuilds must emit distinct, understandable reasons.
4. The emitted log messages must reflect the actual scheduled layers rather than a generic default.
5. Dashboard verification must cover the new logging behavior.

## Scope

**Problem statement:** dashboard auto-indexing currently lacks enough observability to explain rebuild behavior during normal operation or debugging.

**In scope:**

- `.wavefoundry/framework/scripts/dashboard_server.py`
  - Track pending rebuild reasons by layer
  - Log scheduled and started index updates with layer + reason detail
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
  - Add regression coverage for log emission and trigger labeling

**Out of scope:**

- Adding new dashboard UI for index logs
- Changing index rebuild policy or cadence

## Acceptance Criteria

- AC-1: When the dashboard schedules an auto-index rebuild, stderr indicates the target layer(s) and trigger reason.
- AC-2: When a rebuild starts, stderr indicates the layer(s) and the accumulated trigger reason(s).
- AC-3: Framework-only rebuild scheduling is logged as framework-only, not as a generic project rebuild.
- AC-4: Dashboard verification passes.

## Tasks

- Add per-layer rebuild reason tracking to `IndexBuilder`
- Emit scheduling/start log lines with layer and reason detail
- Add tests covering stale-trigger scheduling and framework-only labeling
- Run dashboard verification and docs lint

## Affected Architecture Docs

N/A — observability improvement inside the existing dashboard server flow.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Core operator-visible outcome |
| AC-2 | required | Needed to correlate scheduled vs actual execution |
| AC-3 | important | Prevents misleading logs during framework-only events |
| AC-4 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-11 | Change doc created to add dashboard auto-index trigger logging so operators can tell which layer is updating and why. | Operator request; `dashboard_server.py` |
| 2026-05-11 | Added per-layer trigger reason tracking to `IndexBuilder`, emitted schedule/start/completion log lines with layer + reason detail, and added regressions covering framework-only startup logging plus stale-trigger logging. | `dashboard_server.py`; `test_dashboard_server.py`; `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'`; `./.wavefoundry/bin/docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-11 | Log at schedule time and at build start rather than only after completion | Operators need to see both trigger cause and the actual build that followed | Completion-only logging (rejected: too late to explain why a build started) |

## Risks

| Risk | Mitigation |
|------|------------|
| Log noise could become hard to scan | Keep messages concise and structured around layer + reason only |
| Reason tracking could drift from actual scheduled layers | Store reasons alongside pending layers and snapshot them when the build starts |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
