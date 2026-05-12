# Dashboard: Normalize Progress And Agent Label Typography

Change ID: `12j2w-bug normalize-progress-agent-label-typography`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-11
Wave: `12hsd dashboard-completed-wave-pending-filter`

## Rationale

The Progress labels (`WAVES`, `CHANGES`, `ACS`, `TASKS`) and the Agent pills (`BUILD`, `REVIEW`, `COORDINATE`, `OPERATE`, `SPECIALIST`) look inconsistent because they use different font sizes and weight treatment. This reads as accidental drift rather than intentional hierarchy. The typography should be normalized while preserving the agent category colors and pill affordance.

## Requirements

1. Agent pill labels must match the Progress label typography size.
2. Agent pill labels must match the Progress label weight and tracking closely enough that they read as the same typographic family.
3. Agent pill category colors and pill styling must remain intact.
4. Dashboard verification must pass.

## Scope

**Problem statement:** Progress labels and Agent pill labels use different typography values, creating inconsistent visual hierarchy.

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.css`
  - Align `.hero-agent-pill` typography with `.progress-row-label`

**Out of scope:**

- Changing category colors
- Removing pill styling
- Reworking the Progress card layout

## Acceptance Criteria

- AC-1: Agent pills use the same font size as Progress labels.
- AC-2: Agent pills use matching weight/tracking treatment.
- AC-3: Agent pill color categories remain unchanged.
- AC-4: Dashboard JS syntax and docs lint verification pass.

## Tasks

- Align Agent pill typography to Progress label typography
- Preserve pill colors and hover behavior
- Run dashboard verification

## Affected Architecture Docs

N/A — typography polish only.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Core mismatch called out by the operator |
| AC-2 | required | Size-only alignment would still look off |
| AC-3 | important | Preserve category signal |
| AC-4 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-11 | Confirmed Progress labels and Agent pills use different font sizes in CSS (`0.78rem` vs `0.88rem`). | `dashboard.css` |
| 2026-05-11 | Aligned Agent pill typography to the Progress label treatment by matching font size, weight, and tracking while preserving category colors and pill styling. | `dashboard.css`; `./.wavefoundry/bin/docs-lint` |
| 2026-05-11 | Dialed back the Agent pill typography to keep the normalized `0.78rem` size but remove the added bold/tracking treatment, restoring the lighter feel while preserving the size match. | `dashboard.css`; `./.wavefoundry/bin/docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-11 | Normalize Agent pills to Progress labels instead of enlarging Progress labels | The Progress treatment already fits the compact card layout; agent pills are the outlier | Increase Progress label size (rejected: would change the denser Progress card rhythm) |

## Risks

| Risk | Mitigation |
|------|------------|
| Smaller agent pill text could feel cramped | Keep existing pill padding and color treatment so the pills remain legible and distinct |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
