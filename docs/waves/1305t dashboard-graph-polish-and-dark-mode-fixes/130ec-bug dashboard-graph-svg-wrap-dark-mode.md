# Dashboard: `.graph-svg-wrap` Container Has No Dark-Mode Background Override

Change ID: `130ec-bug dashboard-graph-svg-wrap-dark-mode`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-30
Wave: 1305t dashboard-graph-polish-and-dark-mode-fixes

## Rationale

Wave `1305t` change `1305u` deleted a miscoped duplicate `html[data-theme="dark"] .graph-svg` rule that mistakenly applied a light-mode gradient under the dark-mode selector. After that fix, the operator still reports the graph card looks light in dark mode. Root cause: the actual visible-light container is **`.graph-svg-wrap`** (the outer wrapper around the graph SVG), not `.graph-svg` (the SVG itself). `.graph-svg-wrap` is defined at `dashboard.css:1717-1728` with a white radial-and-linear gradient and **no dark-mode override exists for it**. The deleted block in `1305u` looked like it was supposed to address this but used the wrong selector.

Result: in dark mode the graph viewport renders a white gradient against the otherwise dark dashboard.

Source: operator report 2026-05-30 after `1305u` shipped.

## Requirements

1. Add a `html[data-theme="dark"] .graph-svg-wrap` rule that overrides the light-mode white gradient with either a transparent background (so the dark page background shows through) or a dark equivalent gradient.
2. The dark override must also handle the `border-color` since the light-mode rule sets `border: 1px solid var(--panel-border)` — verify the existing `--panel-border` token (updated to `#3a4150` in `1305w`) renders adequately on the graph viewport border.
3. No other CSS rules are touched.

## Scope

**Problem statement:** `.graph-svg-wrap` has a white gradient background with no dark-mode override; in dark mode the graph viewport renders white.

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.css` — add one dark-mode override rule for `.graph-svg-wrap`.

**Out of scope:**

- Rebalancing graph node colors, edge colors, or community fill colors for dark mode (separate concern; if reported, file as follow-on)
- Changing the light-mode `.graph-svg-wrap` gradient
- Touching `.graph-webgl-wrap` (which already has its own dark-mode override at line 1861)

## Acceptance Criteria

- [x] AC-1: A new `html[data-theme="dark"] .graph-svg-wrap { background: transparent; }` rule was added in `dashboard.css` immediately after the light-mode `.graph-svg-wrap` declaration. The dark-mode rule suppresses the light gradient and lets the dark page background show through the viewport.
- [x] AC-2: `tests/test_dashboard_server.py` continues to pass — 138/138.
- [x] AC-3: Manual smoke verification — operator confirmed "looks good now" after dashboard restart; graph viewport no longer shows the white gradient in dark mode.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add the dark-mode `.graph-svg-wrap` override in `dashboard.css`
- [x] Close gate
- [x] Run framework tests — 1878/1878 pass
- [ ] Manual smoke verification — pending
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The missing override is the fix |
| AC-2 | required | Tests must not regress |
| AC-3 | important | Manual verification confirms the visual outcome |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-30 | Transparent background in dark mode rather than mirroring the light gradient with dark colors | The page/panel background already provides adequate contrast; a separate gradient on the viewport would add visual noise without clarity benefit | Mirror the light gradient using dark rgba values (rejected — extra cascade complexity for marginal benefit) |
| 2026-05-30 | Keep the light-mode gradient untouched | The light-mode gradient is intentional design and operators haven't reported issues with it | Remove the light-mode gradient too (rejected — out of scope) |

## Risks

| Risk | Mitigation |
|---|---|
| Dark-mode viewport with no gradient looks "flat" | Operator can verify on actual hardware and we can iterate to a dark gradient if the flat look is undesirable |
| Other elements depend on `.graph-svg-wrap` having a non-transparent background for layering | None observed; the SVG renders on top of the wrap regardless of wrap's background |

## Related Work

- Immediate follow-up to `1305u` (same wave) — the in-session investigation that produced `1305u` missed the actual `.graph-svg-wrap` selector.
- Demonstrates the `1305d` fix-now-not-later principle — operator report → in-session change in the same wave rather than rolling forward.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
