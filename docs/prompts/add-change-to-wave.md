# Add Change to Wave

Owner: Engineering
Status: active
Last verified: 2026-04-28

Shortcut: **`Add change to wave`**

## Purpose

Admit a consolidated change document into the active wave. Admission is a hard stage gate — implementation must not begin until the change is admitted and **Prepare wave** has passed.

## Steps

1. Confirm the change doc exists at `docs/plans/<change-id>.md` and is complete.
2. Update the wave record (`docs/waves/<wave-id>/wave.md`) to add the change to `## Changes` with `Change Status: planned`.
3. Record product-owner review of the admission delta when the admitted work is a feature or otherwise shifts product behavior, UX, or acceptance expectations — or record `product-owner: N/A` with rationale for non-product admissions.
4. Note that the next **Prepare wave** must reconcile the expanded admit set per `docs/contributing/agent-team-workflow.md`.

## After Admission

The change is admitted. Before implementation begins, **Prepare wave** must pass cleanly:
- Confirms readiness
- Relocates the change doc from `docs/plans/` into `docs/waves/<wave-id>/`
- Records AC priority
- Selects required review lanes
