# Dashboard: Detail Dialogs Drop Plain-Bullet AC and Task Items

Change ID: `12j27-bug dashboard-dialog-details-parser`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-11
Wave: `12hsd dashboard-completed-wave-pending-filter`

## Rationale

The dashboard's Active ACs and Active Tasks dialogs are populated from parsed change-doc detail arrays (`ac_items`, `tasks_items`). In Wavefoundry, most wave-owned change docs record Acceptance Criteria and Tasks as plain bullet lists rather than checkbox lists. The current parser only extracts checkbox items, so the summary tiles may still show wave/change counts while the detail dialogs render empty cards or no cards at all for active changes.

## Requirements

1. The dashboard parser must extract Acceptance Criteria items from both checkbox bullets and plain bullets inside the `## Acceptance Criteria` section.
2. The dashboard parser must extract Task items from both checkbox bullets and plain bullets inside the `## Tasks` section.
3. Checkbox semantics must remain intact:
   - `[x]` marks the item done
   - `[ ]` marks the item open
4. For plain-bullet AC/task items, the parser must preserve the text and infer completion conservatively:
   - when the change status is terminal (`complete`, `completed`, `closed`), plain-bullet items are treated as done
   - otherwise plain-bullet items are treated as open
5. The dialogs must show the parsed item details for active-wave changes without requiring any change-doc rewrite.

## Scope

**Problem statement:** `dashboard_lib.py` assumes checkbox-only AC/task syntax even though the repository's wave change docs are predominantly plain-bullet lists.

**In scope:**

- `.wavefoundry/framework/scripts/dashboard_lib.py`
  - Parse AC items from plain bullets as well as checkbox bullets
  - Parse task items from the `## Tasks` section rather than scanning the whole document
  - Infer plain-bullet completion from terminal change status only
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
  - Add regression coverage for plain-bullet AC/task parsing and snapshot payload details

**Out of scope:**

- Rewriting historical change docs into checkbox format
- UI layout or styling changes for the dialogs

## Acceptance Criteria

- AC-1: A wave-owned change doc with plain-bullet Acceptance Criteria yields non-empty `ac_items` in the dashboard snapshot.
- AC-2: A wave-owned change doc with plain-bullet Tasks yields non-empty `tasks_items` in the dashboard snapshot.
- AC-3: Checkbox-formatted AC/task sections continue to parse with the same done/open semantics as before.
- AC-4: Plain-bullet AC/task items on terminal changes are marked done in the snapshot payload.
- AC-5: Plain-bullet AC/task items on non-terminal changes are marked open in the snapshot payload.
- AC-6: The relevant dashboard test suite passes.

## Tasks

- Update AC item parsing to accept both checkbox and plain bullet rows within `## Acceptance Criteria`
- Update task parsing to read only `## Tasks` and to accept both checkbox and plain bullet rows
- Infer done/open state for plain bullets from terminal change status
- Add regression tests for plain-bullet and checkbox formats
- Run the dashboard test suite

## Affected Architecture Docs

N/A — parser compatibility fix only; no topology or boundary change.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Root correctness issue behind the empty Active ACs dialog |
| AC-2 | required | Root correctness issue behind the empty Active Tasks dialog |
| AC-3 | required | Regression guard for already-supported checkbox docs |
| AC-4 | important | Keeps terminal changes consistent in detail dialogs |
| AC-5 | important | Prevents false-complete detail rows on active work |
| AC-6 | required | Non-regression verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-11 | Root cause confirmed: active dashboard dialogs are empty because `dashboard_lib.py` only parses checkbox-style AC/task items, while the active wave change doc uses plain bullets. | Local snapshot output from `collect_dashboard_snapshot()` for `12hsc-bug completed-wave-appears-in-pending-section` |
| 2026-05-11 | Updated `dashboard_lib.py` to parse real markdown section headings, support plain-bullet AC/task rows, infer plain-bullet completion from terminal change status, and added dashboard snapshot regressions for checkbox and plain-bullet formats. `test_dashboard_server.py` passes and the live Wavefoundry snapshot now includes dialog detail items for active-wave changes. | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'`; live `collect_dashboard_snapshot()` output |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-11 | Infer plain-bullet completion from terminal change status | Historical docs often omit per-item checkboxes; status-level inference restores useful detail without rewriting docs | Require checkbox migration (rejected: too much historical churn), treat all plain bullets as open (rejected: terminal changes would look unfinished forever) |
| 2026-05-11 | Restrict task parsing to the `## Tasks` section | Whole-document bullet scanning risks counting bullets from Scope, Risks, or other sections as tasks | Keep scanning whole document minus AC section (rejected: too error-prone) |

## Risks

| Risk | Mitigation |
|------|------------|
| Mixed-format sections could parse unexpectedly | Tests cover both checkbox and plain-bullet formats; parser stays section-scoped |
| Terminal-status inference misses a future status string | Helper uses a small explicit terminal set that can be extended if new statuses appear |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
