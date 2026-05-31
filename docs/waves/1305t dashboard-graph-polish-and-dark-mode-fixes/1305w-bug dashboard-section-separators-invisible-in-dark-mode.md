# Dashboard: Section Separator Lines Invisible in Dark Mode

Change ID: `1305w-bug dashboard-section-separators-invisible-in-dark-mode`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-30
Wave: 1305t dashboard-graph-polish-and-dark-mode-fixes

## Rationale

The horizontal lines that separate sections within dashboard cards use `border-top: 1px solid var(--panel-border)` (and similar). In dark mode the `--panel-border` token is set to `#242830` (`dashboard.css:2966`) — only slightly lighter than the dark-mode page background `#111214` and panel background `#151719`. The contrast is below the threshold for visible 1px borders, so operators see no separator at all where light mode shows a clean divider.

Source: operator report 2026-05-30.

## Requirements

1. The dark-mode `--panel-border` token must be increased in luminance to produce a visible 1px border against the dark page/panel backgrounds. Target: contrast ratio against `#151719` (panel-bg) of at least ~1.5:1, which is the threshold at which a 1px line becomes visible on most displays.
2. No other dark-mode tokens are touched — only `--panel-border`.
3. Light-mode `--panel-border` (`#DEE2E6`) is unchanged.

## Scope

**Problem statement:** `--panel-border: #242830` in dark mode is invisible against the dark backgrounds because the contrast is too low.

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.css` — change the dark-mode `--panel-border` value to a lighter gray (target around `#3a4150` or similar — a value chosen to be visible without being harsh).

**Out of scope:**

- Defining the undefined `--border` CSS variable used elsewhere in the file — separate concern (border falls back to text color, which is usually readable in both themes; if the operator reports specific elements with `var(--border)` as broken, file as follow-on)
- Restructuring divider semantics (e.g., switching to `<hr>` elements)
- Touching the `.wavefoundry/framework/dashboard/dashboard.html` markup

## Acceptance Criteria

- [x] AC-1: The dark-mode `--panel-border` value was changed from `#242830` to `#3a4150`.
- [x] AC-2: No other dark-mode token values are modified.
- [x] AC-3: `tests/test_dashboard_server.py` continues to pass — 138/138.
- [x] AC-4: Manual smoke verification — operator confirmed "looks good now" after dashboard restart; section separators visible in dark mode at the new `#3a4150` value.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Update `--panel-border` value in the dark-mode token block in `dashboard.css`
- [x] Close gate
- [x] Run framework tests
- [ ] Manual smoke verification — pending
- [ ] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The single token change is the fix |
| AC-2 | required | Scope guard |
| AC-3 | required | Tests must not regress |
| AC-4 | important | Manual verification confirms the visual outcome |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-30 | Single token bump rather than per-element overrides | One change fixes all borders that use `--panel-border`; per-element overrides would scatter the fix and create drift | Add explicit dark-mode `border-color` declarations on every divider rule (rejected — high-volume, error-prone, drift risk) |
| 2026-05-30 | Target ~`#3a4150` rather than something brighter | Brighter (e.g. `#4a5060`) would be visible but too prominent; subtle is the right register for separator lines | Use the same `#DEE2E6` as light mode (rejected — way too bright on dark bg) |

## Risks

| Risk | Mitigation |
|---|---|
| The new value still doesn't have enough contrast on some displays | Manual smoke covers the operator's setup; can iterate up if reported |
| Other elements that used `--panel-border` in light mode for soft fills (e.g., dividers within accent panels) now look slightly heavier in dark mode | The variable's primary use is structural borders; soft fill usage is incidental |

## Related Work

- Companion to `1305u` (graph dark mode) and `1305v` (filter pill removal).

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
