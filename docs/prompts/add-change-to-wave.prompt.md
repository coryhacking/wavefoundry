# Add Change to Wave

Owner: Engineering
Status: active
Last verified: 2026-05-04

Shortcut: **`Add change to wave`**

## Purpose

Admit a consolidated change document into the active wave. Admission is a hard stage gate — implementation must not begin until the change is admitted and **Prepare wave** has passed.

## Steps

1. Confirm the change doc exists at `docs/plans/<change-id>.md` or is already located at `docs/waves/<wave-id>/<change-id>.md`, and that only one active copy exists.
2. Update the wave record (`docs/waves/<wave-id>/wave.md`) to add the change to `## Changes` with `Change Status: planned`.
3. Relocate the admitted change doc into `docs/waves/<wave-id>/<change-id>.md` immediately. If the doc is already in that location, keep it there; if duplicate staged and wave copies exist, stop and resolve the conflict instead of silently choosing one.
4. Record product-owner review of the admission delta when the admitted work is a feature or otherwise shifts product behavior, UX, or acceptance expectations — or record `product-owner: N/A` with rationale for non-product admissions.
5. Note that the next **Prepare wave** must validate admitted-doc placement, reconcile the expanded admit set per `docs/contributing/agent-team-workflow.md`, and repair placement if drift somehow remains.

## After Admission

The change is admitted. Before implementation begins, **Prepare wave** must pass cleanly:
- Confirms readiness
- Confirms admitted change docs are already wave-owned and repairs placement if needed
- Records AC priority
- Selects required review lanes
