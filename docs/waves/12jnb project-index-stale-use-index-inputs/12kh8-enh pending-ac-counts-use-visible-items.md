# Pending AC Counts Use Visible Items

Change ID: `12kh8-enh pending-ac-counts-use-visible-items`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The dashboard summary tiles currently count ACs from the priority table, while the AC dialog renders the visible AC bullet items directly. That lets a change show ACs in the dialog but still report `0` ACs in the tile when the priority table is absent or incomplete.

## Requirements

1. The dashboard AC summary should count the same visible AC items that the dialog renders.
2. AC metrics should no longer depend on the presence of a populated AC priority table to show pending counts.
3. The new counting rule should preserve existing dialog behavior and keep `not-this-scope` items out of the visible summary.
4. Regression coverage should lock the visible-item counting behavior in place.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- `docs/waves/12jnb project-index-stale-use-index-inputs/wave.md`

**Out of scope:**

- Changing AC dialog rendering
- Changing change-doc parsing behavior
- Changing task counting semantics

## Acceptance Criteria

- AC summary tiles count visible AC items, not priority-table rows.
- Pending AC totals are non-zero when a change has visible AC items with no AC priority table.
- The AC dialog continues to render the same visible items as before.
- Regression coverage locks the tile/dialog alignment in place.

## Tasks

- Update AC summary counting to use visible AC items
- Keep the `not-this-scope` filter aligned between tile summaries and dialog rendering
- Add regression coverage for visible AC counting

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The tile summary must match the dialog's visible AC items |
| AC-2 | required | Pending counts should not collapse to zero when the priority table is missing |
| AC-3 | required | Existing dialog behavior should remain stable |
| AC-4 | required | Tests should prevent regressions |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Counting from different sources reintroduces tile/dialog drift | Derive both from the same visible AC item filter |
| Changes with `not-this-scope` ACs could inflate counts | Reuse the dialog's existing filter for the summary path |
| Priority-table-only assumptions could remain elsewhere in the UI | Keep the change scoped to the AC summary path first |
