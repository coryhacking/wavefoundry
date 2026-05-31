# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-30

wave-id: `1305t dashboard-graph-polish-and-dark-mode-fixes`
Title: Dashboard Graph Polish and Dark Mode Fixes

## Objective

Fix three operator-reported dashboard issues surfaced after wave `1304x` closed: the Graph card SVG doesn't switch to dark mode correctly because of a duplicate light-mode-styled rule under the dark-mode selector; the graph mode-switch filter pills (Communities / Focus / Files / Clear) are redundant with the implicit selection-driven mode logic and add visual noise; and the section separator lines are invisible in dark mode because the `--panel-border` token has insufficient contrast against the dark backgrounds.

## Changes

Change ID: `1305u-bug dashboard-graph-dark-mode-broken`
Change Status: `implemented`

Change ID: `1305v-enh dashboard-remove-graph-mode-switch`
Change Status: `implemented`

Change ID: `1305w-bug dashboard-section-separators-invisible-in-dark-mode`
Change Status: `implemented`

Change ID: `130ec-bug dashboard-graph-svg-wrap-dark-mode`
Change Status: `implemented`

Completed At: 2026-05-31

## Wave Summary

Wave `1305t` (Dashboard Graph Polish and Dark Mode Fixes) delivered 4 changes: Dashboard: Graph Card Doesn't Switch to Dark Mode Properly, Dashboard: Remove the Graph Mode-Switch Filter Pills, Dashboard: Section Separator Lines Invisible in Dark Mode, and Dashboard: `.graph-svg-wrap` Container Has No Dark-Mode Background Override.

**Changes delivered:**

- **Dashboard: Graph Card Doesn't Switch to Dark Mode Properly** (`1305u-bug dashboard-graph-dark-mode-broken`) — 3 ACs completed. Key decisions: Delete the broken block entirely rather than fix its values
- **Dashboard: Remove the Graph Mode-Switch Filter Pills** (`1305v-enh dashboard-remove-graph-mode-switch`) — 6 ACs completed. Key decisions: Keep `viewMode` React state; Don't touch shared CSS classes
- **Dashboard: Section Separator Lines Invisible in Dark Mode** (`1305w-bug dashboard-section-separators-invisible-in-dark-mode`) — 4 ACs completed. Key decisions: Single token bump rather than per-element overrides; Target ~`#3a4150` rather than something brighter
- **Dashboard: `.graph-svg-wrap` Container Has No Dark-Mode Background Override** (`130ec-bug dashboard-graph-svg-wrap-dark-mode`) — 3 ACs completed. Key decisions: Transparent background in dark mode rather than mirroring the light gradient with dark colors; Keep the light-mode gradient untouched
## Acceptance Criteria

- The Graph card SVG in dark mode has no residual light-mode background gradient (`1305u`).
- The Graph card header no longer renders the four-button mode-switch row; node-click and cluster-click still drive view mode implicitly (`1305v`).
- Section separator lines are visible in dark mode across all cards (`1305w`).
- All framework tests pass; docs-lint clean.

## Journal Watchpoints

- **Watchpoint:** `framework_edit_allowed` gate required before editing `dashboard.js` (`1305v`) and `dashboard.css` (`1305u`, `1305w`). Blocking concern if any edit slips outside the gate.
- **Follow-up:** Operator should manually verify each fix after dashboard restart; all three ACs include a manual smoke step. Flag as blocking if any visual regression appears in light mode after the dark-mode token bump.

## Coordinator

- `wave-coordinator`

## Participants

| Role | Lane | Scope |
|------|------|-------|
| implementer | implement | dashboard.css, dashboard.js |
| code-reviewer | review | the three small dashboard edits |
| qa-reviewer | review | manual smoke confirms each fix |

## Review Evidence

- wave-council-readiness: approved — 2026-05-30; three small dashboard fixes (10-line CSS deletion, 12-line JSX deletion, single token bump). Inline council with red-team and code-reviewer seats: each change has explicit AC priority and a decision log capturing why the fix was chosen over alternatives; risk profile is low across all three. PASS.
- code-reviewer: approved — 2026-05-30; close-review covered all four changes including the mid-wave-added `130ec`. `1305u` deletion clean; `1305v` JSX block removed with the existing test guard updated to assert the new contract (`assertNotIn`); `1305w` single-token bump documented in decision log; `130ec` two-line dark-mode override placed directly after the light-mode declaration so the cascade is locally readable. Wave Summary was updated mid-wave to describe `130ec`. Zero in-session fixes recommended at close.
- qa-reviewer: approved — 2026-05-30; test guard updated to codify the new contract (`assertIn` → `assertNotIn` for the mode-switch block) with a wave-citation comment; 1878/1878 tests pass after each fix; operator-verified all four manual-smoke ACs via "looks good now" after dashboard restart.
- wave-council-delivery: approved — 2026-05-30; PASS (architecture-reviewer, code-reviewer, qa-reviewer, security-reviewer, performance-reviewer, red-team, reality-checker). Four small dashboard fixes, all verified visually by operator. The wave validates the `1305d` fix-now-not-later principle: when `1305u`'s scoping missed the root selector (`.graph-svg-wrap` instead of `.graph-svg`), operator's smoke-test feedback surfaced the gap and `130ec` was added in-session to fix it — same wave, not a follow-on. Zero open quality issues at close. PASS.
- operator-signoff: approved — 2026-05-30; operator confirmed "looks good now" after dashboard restart, covering all four manual-smoke ACs (graph card dark-mode background, mode-switch removal, section separator visibility, graph viewport background)..

## Prepare Review Evidence

- code-reviewer: approved — 2026-05-30; three change docs reviewed ahead of implementation. Each describes a small surgical edit (CSS rule deletion, JSX block deletion, single token bump). AC priority set on all three. No code review concerns ahead of implementation.
- qa-reviewer: approved — 2026-05-30; each change carries an AC for `tests/test_dashboard_server.py` passing plus a manual smoke verification. No automated test changes required since all three are visual-CSS/JSX edits.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-05-30: PASS** (moderator: council-moderator; primer-depth: standard; seats: red-team, code-reviewer; rotating-seat: code-reviewer; strongest-challenge: the duplicate dark-mode `.graph-svg` rule in `1305u` could have a load-bearing cascade interaction we're missing; strongest-alternative: edit the broken values rather than deleting (rejected because the second block already provides the intended dark-mode styling and deletion is cleaner))

## Dependencies

- No external wave dependencies. Companion to wave `1304x` dashboard work (`1304w`, `13047`) closed earlier 2026-05-30.
