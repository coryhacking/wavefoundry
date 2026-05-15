# AC Priority Order Mapping

Change ID: `12jva-enh ac-priority-order-mapping`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The dashboard currently classifies AC bullets by matching explicit AC IDs in the bullet text. Several active change docs omit those IDs even though the bullets and AC priority rows are already in order. That creates hidden `unknown` classifications and makes the summary tiles disagree with the visible AC list.

## Requirements

1. AC bullets should inherit priority from the AC Priority table in document order when the bullet text does not carry an explicit AC ID.
2. The dashboard summary should count every AC bullet rather than silently dropping uncategorized items.
3. The active wave tiles should continue to reflect the actual visible AC bullets below them.
4. Existing well-formed docs with explicit AC IDs must continue to parse correctly.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/dashboard_lib.py`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- related dashboard docs only if a snapshot or guidance note needs to explain the behavior

**Out of scope:**

- Changing wave lifecycle behavior
- Renaming the AC Priority table format

## Acceptance Criteria

- AC items without explicit IDs still receive a priority when the AC Priority table has the same number of rows in the same order.
- Dashboard AC summary counts line up with the visible AC list for the active wave.
- Unknown AC priority is no longer required for docs that already provide ordered AC bullets and priority rows.
- Regression coverage proves the order-based fallback works.

## Tasks

- Update AC parsing to use AC Priority row order when IDs are absent
- Add regression coverage for order-based AC parsing

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The summary must match the visible AC bullets |
| AC-2 | required | Counting actual bullets is the user-visible behavior |
| AC-3 | required | Existing explicit-ID docs must continue to work |
| AC-4 | required | Regression coverage keeps the fallback honest |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| AC row order diverges from bullet order in some docs | Keep explicit AC ID matching as the primary path when IDs are present |
| Order-based fallback hides doc quality issues | Add regression coverage and keep the parser conservative |
