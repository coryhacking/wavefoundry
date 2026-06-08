# Recent-Changes Change IDs Wrap At Dashes, Not Panel Width

Change ID: `1p459-bug recent-changes-id-dash-wrap`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-06-08
Wave: 1p458 dashboard-progress-rendering-fixes

## Rationale

In the dashboard's Activity "recent changes" timeline, a long change ID (e.g. `1p3q2-enh council-protocol-null-findings-primer-independence-moderator-falsification`) forces the entire panel wider. The id is rendered as a plain string inside a `.wave-change-id` span (`dashboard.js:4188`). Because that span is NOT inside a `<td>`, it inherits the base rule `.wave-change-id { white-space: nowrap }` (`dashboard.css:633`) — the override that relaxes wrapping only targets `td .wave-change-id` (`dashboard.css:636-640`). So the id cannot break and stretches its container.

`nowrap` was applied to stop the id breaking at the single space between the kind and the slug (`…enh␣council-…`), which looked wrong. The fix is not to forbid all breaks but to break at sensible points: after each dash. The table view already does exactly this (`dashboard.js:4133`):

```js
c.change_id.split("-").flatMap((part, i) => i === 0 ? [part] : ["-", h("wbr", { key: i }), part])
```

That pattern works there because the `<td>` context supplies `white-space: normal`. The recent-changes list needs the same dash-break treatment plus a wrapping context, while still preventing a break at the kind↔slug space.

## Requirements

1. In the Activity timeline (`dashboard.js` `Activity`, the `.wave-change-id` span at `:4188`), the change ID must render so it can wrap, breaking only **after dashes**, never at the single space between the kind and the slug.
2. The kind↔slug space (`…enh␣council-…`) must be made non-breaking (e.g. converted to ` `) so the only wrap opportunities are the dash boundaries.
3. The wrapping must be scoped to the recent-changes / timeline context; the existing `nowrap` behavior of `.wave-change-id` in the metric-dialog cards (`dashboard.js:946`, `:970`, `:1015`) must be unchanged.
4. Long IDs must no longer force the Activity panel wider than its column; the id wraps within the available width.
5. Reuse the established dash-break approach (`<wbr>` after each dash) rather than introducing a divergent mechanism; the table view at `dashboard.js:4133` is the reference.

## Scope

**Problem statement:** The recent-changes list renders change IDs `nowrap` (inherited base `.wave-change-id` rule, `dashboard.css:633`) with no `<wbr>` markup, so long IDs widen the panel instead of wrapping at dashes.

**In scope:**

- Apply the dash-split `<wbr>` rendering to the change ID in the `Activity` timeline (`dashboard.js:4188`), with the kind↔slug space converted to a non-breaking space.
- A small shared helper (e.g. `renderChangeIdParts(id)`) that performs the dash-split-with-`<wbr>` and nbsp-protects the space, usable by the timeline (and optionally adopted by the table at `:4133` for consistency, without changing the table's observable behavior).
- A scoped CSS rule so the timeline's `.wave-change-id` wraps (`white-space: normal` + `overflow-wrap: break-word`), without altering the metric-dialog-card `.wave-change-id` usages.
- Dashboard test coverage asserting the recent-changes id renders break opportunities and the metric-dialog usage is untouched.

**Out of scope:**

- Changing change-ID format or length.
- Restyling other `.wave-change-id` consumers (metric dialog cards, wave list) beyond leaving them as-is.
- The deferred-progress accounting change (sibling `1p45a`).

## Acceptance Criteria

- [x] AC-1: In the Activity "recent changes" list, a long change ID wraps onto multiple lines breaking only after dashes; it no longer forces the panel/column wider than its available width.
- [x] AC-2: No break occurs at the space between the kind and the slug (the space is non-breaking).
- [x] AC-3: The `.wave-change-id` usages in the metric-dialog cards (`dashboard.js:946`, `:970`, `:1015`) keep their current `nowrap` behavior — the wrap change is scoped to the timeline/recent-changes context only.
- [x] AC-4: The dash-break is implemented with the existing `<wbr>`-after-dash approach (reference `dashboard.js:4133`), not a new mechanism; if a shared helper is introduced it is used by the timeline and does not change the table view's rendered output.
- [x] AC-5: Dashboard tests cover the recent-changes id rendering (break opportunities present, space non-breaking) and a regression guard that the metric-dialog id rendering is unchanged; `python3 .wavefoundry/framework/scripts/run_tests.py` is green.

## Tasks

- [x] Add a `renderChangeIdParts(id)` helper in `dashboard.js` that splits on `-`, inserts `<wbr>` after each dash, and replaces the kind↔slug space with ` `.
- [x] Use the helper for the change ID in the `Activity` timeline span (`dashboard.js:4188`).
- [x] Add a scoped CSS rule (e.g. `.timeline .wave-change-id`) in `dashboard.css` setting `white-space: normal; overflow-wrap: break-word;`, leaving the base `.wave-change-id` and metric-dialog usages intact.
- [~] (Optional, low-risk) Switch the table view (`dashboard.js:4133`) to the shared helper — intentionally not adopted: the table already wraps inside its `<td>` (`white-space: normal`) and AC-4 requires its rendered output stay unchanged, so adopting the nbsp-protecting helper there would change table behavior.
- [x] Add/extend dashboard tests (`test_dashboard_server.py`) for AC-1..AC-4 and the metric-dialog regression guard.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py`; run `.wavefoundry/bin/docs-lint` on this plan.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| id-render-helper | Engineering | — | `renderChangeIdParts` helper (dash `<wbr>` + nbsp space) in `dashboard.js`. |
| timeline-wire-and-css | Engineering | id-render-helper | Use helper at `:4188`; add scoped `.timeline .wave-change-id` wrap rule in `dashboard.css`. |
| tests | Engineering | timeline-wire-and-css | Recent-changes wrap tests + metric-dialog regression guard. |


## Serialization Points

- `.wavefoundry/framework/dashboard/dashboard.js` — shared with sibling `1p45a` (deferred progress). Coordinate edits; the two touch different functions (`Activity` vs the progress-stats/`ProgressRow`) but the same file.
- `.wavefoundry/framework/dashboard/dashboard.css` `.wave-change-id` rules — keep the base `nowrap` (metric-dialog cards depend on it); add a scoped timeline override rather than changing the base.

## Affected Architecture Docs

N/A — a confined dashboard rendering fix (markup + scoped CSS) with no module-boundary, data-flow, or verification-surface change.

## AC Priority

_Confirmed at Prepare wave 1p458 (2026-06-08) — required/important classifications interrogated by the readiness council and stand as below._


| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | The reported defect — long IDs must wrap, not widen the panel. |
| AC-2 | required   | Preserves the original intent behind the `nowrap` (no space-break). |
| AC-3 | required   | Must not regress the metric-dialog `nowrap` usages. |
| AC-4 | important  | Reuse the existing `<wbr>` pattern for consistency/maintainability. |
| AC-5 | required   | Test coverage + green suite. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-08 | Added `renderChangeIdParts` (dash-split `<wbr>` + nbsp-protected kind/slug space), wired it into the Activity timeline span, and added the scoped `.timeline .wave-change-id` wrap rule. Table view left unchanged (AC-4). | `run_tests.py` green (2782); `test_activity_timeline_change_id_renders_dash_break_parts` + metric-dialog regression guard pass. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-08 | Break after each dash via `<wbr>`; make the kind↔slug space non-breaking; scope the wrap to the timeline. | Gives reasonable break points (the original `nowrap` was only meant to stop the space-break), reuses the table view's proven pattern, and avoids regressing the metric-dialog `nowrap` cards. | Remove base `nowrap` globally (regresses metric-dialog cards and re-introduces the space-break); CSS-only hyphen wrapping (cannot keep the space non-breaking without markup). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Relaxing `.wave-change-id` wrapping leaks into metric-dialog cards. | Scope the override to the timeline selector; AC-3 regression test guards the metric-dialog usage. |
| `<wbr>` ignored under an inherited `nowrap`. | Pair the `<wbr>` markup with the scoped `white-space: normal` rule so break opportunities are honored. |
| Edit collides with sibling `1p45a` in `dashboard.js`. | Serialization point; the two touch different functions — sequence and re-verify after both land. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
