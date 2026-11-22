# Show each recently updated spec once

Change ID: `2423a-bug dashboard-recent-changes-unique-specs`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-21
Wave: 2423b correct-dashboard-recent-changes

## Rationale

The dashboard shows several cards for spec `1x8e1` under mutation names. Its Progress Log includes a mutation-results table below the dated updates. The dashboard reads that table with the preceding progress table's column names and sorts the mutation names as dates.

## Product Intent

An operator opening Recent changes sees up to ten distinct specs ordered by their most recent dated progress update. Each card opens the record behind it.

## Requirements

1. Recognize genuine dated updates in the documented Progress Log tables. Associate cells with their own table header. Ignore unrelated tables, examples and malformed dates.
2. Select the newest valid update per spec before applying the ten-card limit. Resolve ties within one spec by the last recorded row for that date. Keep distinct documents navigable through their existing paths.
3. Keep the existing recent progress event feed for callers that consume multiple legitimate updates. Preserve full progress history in the spec.

## Scope

Fix the dashboard activity collector, its cards and their regression coverage. Historical spec content stays authoritative.

## Acceptance Criteria

- [x] AC-1: A dashboard snapshot from a spec with a progress table and a later three-column evidence table excludes the evidence rows, including an evidence row whose first cell looks like a date.
- [x] AC-2: With more than ten valid updates from one spec alongside other specs, the Recent changes list includes each eligible spec once, honors chronological order and shows the last same-day row. The existing event feed still includes individual dated updates.
- [x] AC-3: On the running dashboard, displayed dates come from progress entries, cards identify distinct specs, and opening a card targets the underlying document. The regression covers the screenshot's false headings and multiple legitimate updates.

## Tasks

- [x] Correct progress table parsing and collect recent distinct specs.
- [x] Connect the dashboard cards to the summary and preserve document navigation.
- [x] Exercise regressions and verify the live dashboard.

## Agent Execution Graph

One builder updates the collector and the card together. Independent reviewers check the result.

## Serialization Points

- `.wavefoundry/framework/scripts/dashboard_lib.py`
- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

## Affected Architecture Docs

The existing dashboard snapshot gains a distinct-spec summary beside its event feed.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Prevents evidence from posing as activity. |
| AC-2 | required | Establishes the operator-visible outcome. |
| AC-3 | required | Checks the actual read path. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-21 | Readback: The panel summarizes one document per card. Its existing event feed keeps dated updates. | The live snapshot had ten cards for two specs. |
| 2026-11-21 | Traced the false headings to mutation rows in the historical spec. | Spec 1x8e1 and the dashboard activity collector. |
| 2026-11-21 | The live dashboard returned ten distinct spec paths in date order. Opening the first card returned the exact source document. The separate progress feed still includes repeat updates. | Live dashboard and document endpoints, activity regression tests. |
| 2026-11-21 | Delivery review identified an escaped pipe that hid an implementation update in spec 1p9bn. The activity reader now shares the existing Markdown row parser. | Historical record replay and regression with escaped and inline-code pipes. |
| 2026-11-21 | A repository-wide comparison retained all 5,984 previously recognized dated updates in 1,278 Progress Logs and recovered 35 more. A width check preserves entries that quote a lone backtick. | Independent code review compared the old and final readers on wave and plan documents. |
| 2026-11-22 | All ten live cards opened their matching source files. The full framework run passed 13,196 tests with 12 skips in 13 minutes 59 seconds. | Dashboard and document endpoints, framework test receipt. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-21 | Preserve the event feed and add a distinct-spec summary. | An existing dashboard test explicitly requires repeated valid progress events. | Filtering ten already-truncated events in the browser would hide other recent specs. |

## Risks

A valid-looking date in a later evidence table defeats date-only filtering. Exercise that case.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
