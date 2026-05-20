# Agent Pill Counter Removal

Change ID: `12rqs-enh agent-pill-counter-removal`
Change Status: `implemented`
Owner: Engineering

Status: implemented
Last verified: 2026-05-20
Wave: `12rnv agent-prompt-harness`

## Rationale

The dashboard currently shows a usage-count badge inside each agent pill. That badge does not carry enough value to justify the extra visual noise in the main agent surface, and it competes with the agent label itself. Removing it keeps the agent section cleaner while preserving the same underlying grouping and selection behavior.

## Requirements

1. Remove the visible usage-count badge from the agent pills in the dashboard home view.
2. Keep agent grouping, filtering, and click behavior unchanged.
3. Preserve any accessible labeling needed for agent selection without surfacing the count visually.
4. Update tests so the dashboard no longer expects a visible pill counter.

## Scope

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/dashboard/dashboard.css` if any supporting style cleanup is needed
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

## Acceptance Criteria

- AC-1: Agent pills render without a visible usage-count badge.
- AC-2: Agent pill click behavior remains unchanged.
- AC-3: The dashboard test suite covers the no-counter rendering path.
- AC-4: `docs-lint` passes after the change.

## Tasks

- [x] Remove the visible usage-count badge from agent pills
- [x] Update tests to assert the pill counter is no longer rendered
- [x] Run docs validation and relevant dashboard tests

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|-----------|-------|------------|-------|
| agent-pill-counter-removal | implementer | Prepare wave | dashboard UI edit |

## Serialization Points

- None beyond the standard dashboard edit/test flow.

## Affected Architecture Docs

N/A — dashboard presentation only.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Core visible change |
| AC-2 | required | Must not regress agent selection |
| AC-3 | required | Prevents the badge from returning silently |
| AC-4 | required | Standard docs gate |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-20 | Change doc created in response to dashboard cleanup request. | operator request |
| 2026-05-20 | Implemented: agent pill usage-count badge removed from the dashboard and tests updated to cover the no-counter state. | implementer |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
