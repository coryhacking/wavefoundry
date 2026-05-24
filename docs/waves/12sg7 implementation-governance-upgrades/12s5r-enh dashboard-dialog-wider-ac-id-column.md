# Dashboard dialogs wider + AC ID no-wrap column + pending wave ordering

Change ID: `12s5r-enh dashboard-dialog-wider-ac-id-column`
Change Status: `complete`
Owner: coryhacking
Status: complete
Last verified: 2026-05-21
Wave: `12sg7 implementation-governance-upgrades`

## Rationale

The wave and change dialog boxes are too narrow — content feels cramped and long AC text wraps aggressively. The AC table's first column (AC-1, AC-2, …) wraps onto two lines, making it hard to scan. Date columns in Progress Log and Decision Log tables also wrap (e.g. `2026-05-08` splits across lines). The pending waves list should also show the newest waves first so recent planning work is visible at the top instead of being buried by older pending records. Widening the dialogs, applying `white-space: nowrap` to dialog table first columns, and sorting pending waves newest-to-oldest fixes these dashboard usability issues.

## Requirements

1. The `agent-dialog` max-width must increase from `800px` to at least `1000px` so wave and change dialogs use more available space.
2. Every AC row in `AcsDialog` must render the `ac.id` value (e.g. `AC-1`) as a dedicated first column with `white-space: nowrap` so it never wraps.
3. The AC ID column must be visually distinct (muted, monospace or small caps) and flex-shrink 0 so it never collapses.
4. All first-column `td` elements in dialog body tables must have `white-space: nowrap` so Date columns in Progress Log / Decision Log and AC columns in AC Priority tables never wrap.
5. The pending waves list in the dashboard must be sorted newest-to-oldest by wave ID so the most recently created pending wave appears first.
6. Change is confined to `dashboard.css` and `dashboard.js` inside `.wavefoundry/framework/dashboard/`; no other files are touched.

## Scope

**Problem statement:** Dialogs are `min(800px, 92vw)` wide. AC rows show only ✓/○, text, and priority — the AC ID (AC-1, AC-2) is available in the data but never displayed. The pending waves list does not explicitly sort newest-first.

**In scope:**

- Increase `agent-dialog` width in `dashboard.css`
- Add `.metric-dialog-ac-id` CSS class with `white-space: nowrap; flex-shrink: 0`
- Render `ac.id` span in `AcsDialog` in `dashboard.js`
- Sort pending waves newest-to-oldest in `dashboard.js`

**Out of scope:**

- TasksDialog, FilesDialog, ChangesDialog row layouts beyond pending-wave ordering
- Server-side data changes

## Acceptance Criteria

- [x] AC-1: The dialog element has CSS `width: min(1000px, 92vw)` or wider.
- [x] AC-2: Each AC row in the ACs dialog shows the AC ID (e.g. `AC-1`) as the first visible element.
- [x] AC-3: The AC ID element has `white-space: nowrap` in its CSS so it cannot wrap to a second line.
- [x] AC-4: Date values in Progress Log and Decision Log tables do not wrap (first column `td` has `white-space: nowrap`).
- [x] AC-5: The AC column in the AC Priority table does not wrap.
- [x] AC-6: The pending waves list is sorted newest-to-oldest by wave ID.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Widen `.agent-dialog` `width` in `dashboard.css`
- [x] Add `.metric-dialog-ac-id` CSS class
- [x] Add `ac.id` span as first child of each `metric-dialog-ac-item` in `AcsDialog` in `dashboard.js`
- [x] Sort pending waves newest-to-oldest in `dashboard.js`
- [x] Close `framework_edit_allowed` gate
- [x] Validate with `wave_validate`

## Agent Execution Graph

| Workstream     | Owner        | Depends On | Notes |
| -------------- | ------------ | ---------- | ----- |
| css-width      | coryhacking  | —          |       |
| js-ac-id       | coryhacking  | css-width  |       |

## Serialization Points

- `dashboard.css` and `dashboard.js` are edited sequentially.

## Affected Architecture Docs

N/A — change is confined to dashboard presentation layer; no boundary, flow, or verification architecture is affected.

## AC Priority

| AC   | Priority    | Rationale |
| ---- | ----------- | --------- |
| AC-1 | required    | Core ask  |
| AC-2 | required    | Core ask  |
| AC-3 | required    | Core ask  |
| AC-4 | required    | Date columns should stay readable in dialog tables |
| AC-5 | required    | AC Priority table should remain scannable |
| AC-6 | important   | Recent pending planning work should surface first in the dashboard |

## Progress Log

| Date       | Update  | Evidence |
| ---------- | ------- | -------- |
| 2026-05-20 | Created |          |
| 2026-05-21 | Prepare wave completed; change marked ready for implementation in `12sg7`. | `docs/waves/12sg7 implementation-governance-upgrades/wave.md` |
| 2026-05-21 | Implementation complete. Widened `.agent-dialog` from `min(800px, 92vw)` to `min(1000px, 92vw)`. Added `.metric-dialog-ac-id` CSS class. Rendered `ac.id` span in `AcsDialog`. Added `white-space: nowrap` to agent-dialog-body first-column `td`. Sorted pending waves newest-to-oldest in `WavesCard` and `WavesDialog`. 1501 tests pass, docs-lint clean. | `dashboard.css`, `dashboard.js` |

## Decision Log

| Date       | Decision                        | Reason                            | Alternatives |
| ---------- | ------------------------------- | --------------------------------- | ------------ |
| 2026-05-20 | Widen to min(1000px, 92vw)      | Fits most laptop screens          | 960px        |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Very wide dialogs clip on small screens | `92vw` cap keeps it safe |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
