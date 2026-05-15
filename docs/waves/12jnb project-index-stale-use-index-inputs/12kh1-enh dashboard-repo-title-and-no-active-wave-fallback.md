# Dashboard Repo Title and No-Active-Wave Metric Fallback

Change ID: `12kh1-enh dashboard-repo-title-and-no-active-wave-fallback`
Change Status: `complete`
Owner: Engineering
Status: ready
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The dashboard tab title should include the repository name first so multiple open dashboards are easy to distinguish. The active-wave metric tiles should also stay useful when there is no active wave by widening to all pending changes, ACs, and tasks across waves and planning items instead of collapsing to zero.

## Requirements

1. The browser tab title should include the repository name first, followed by the Wavefoundry dashboard label.
2. When at least one wave is active, the Changes / ACs / Tasks tiles should keep their current active-wave-scoped behavior.
3. When no wave is active, the Changes / ACs / Tasks tiles should summarize all pending changes, ACs, and tasks across planned waves plus staged planning changes.
4. The fallback should not affect the existing Waves tile, progress bars, or active-wave dialogs.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/dashboard/dashboard.html` if a static default title is still useful
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- `docs/waves/12jnb project-index-stale-use-index-inputs/wave.md`

**Out of scope:**

- Changing progress-bar semantics
- Changing wave lifecycle status calculations
- Changing the dashboard footer or theme controls

## Acceptance Criteria

- The dashboard tab title shows the repository name first, then the Wavefoundry dashboard label.
- With an active wave, the Changes / ACs / Tasks tiles continue to reflect only active-wave work.
- With no active wave, the Changes / ACs / Tasks tiles reflect all pending changes across waves and planning.
- Regression coverage verifies both the title format and the no-active-wave fallback behavior.

## Tasks

- Add repository-first dashboard title handling
- Add no-active-wave fallback metrics for Changes / ACs / Tasks
- Add regression tests for both behaviors

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Tabs need a repo-first identifier to distinguish multiple dashboards |
| AC-2 | required | Active-wave behavior must remain unchanged when a wave is open |
| AC-3 | required | No-active-wave fallback should still surface meaningful work |
| AC-4 | required | Regression tests should lock the new behavior in place |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The fallback could blur the meaning of the tiles | Keep the active-wave scoped behavior unchanged when a wave is open |
| Repo-first titles may be truncated in narrow tabs | Put the repository name first because that is the unique identifier operators need |
