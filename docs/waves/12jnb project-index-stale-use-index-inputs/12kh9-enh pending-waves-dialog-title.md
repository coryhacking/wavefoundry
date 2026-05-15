# Pending Waves Dialog Title

Change ID: `12kh9-enh pending-waves-dialog-title`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The Waves detail dialog currently uses the active-wave title even when the dashboard is in pending mode. That creates a mismatch between the tile label and the dialog copy.

## Requirements

1. The Waves dialog should say `Pending Waves` when the dashboard is in pending scope.
2. The Waves dialog should preserve `Active Waves` when there are active waves.
3. The empty-state copy should continue to match the current scope.
4. Regression coverage should lock the title behavior in place.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- `docs/waves/12jnb project-index-stale-use-index-inputs/wave.md`

**Out of scope:**

- Changing the wave counts themselves
- Changing pending-scope detection
- Changing other metric dialog titles

## Acceptance Criteria

- Waves dialog shows `Active Waves` only when there is at least one active wave.
- Waves dialog shows `Pending Waves` when there are no active waves.
- Empty-state copy remains aligned with the active/pending mode.
- Regression coverage locks the title behavior in place.

## Tasks

- Update the Waves dialog title to follow the current scope
- Keep the empty-state copy aligned with the dialog scope
- Add a regression for pending-scope Waves dialog rendering

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Dialog title must reflect the current dashboard mode |
| AC-2 | required | Existing active-wave behavior must remain unchanged |
| AC-3 | required | Empty-state copy should stay consistent |
| AC-4 | required | Tests should prevent regressions |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Title drift could recur after other dashboard changes | Add a regression that checks the rendered source contract |
| Pending mode could accidentally inherit active wording | Keep the title selection derived from the same `active.length` check as the empty state |
