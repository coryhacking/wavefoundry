# Dashboard UI Polish

Change ID: `12hjp-enh dashboard-ui-polish`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-10
Wave: `12g47 dashboard-framework`

## Rationale

The initial dashboard implementation established a functional UI but left several visual consistency gaps that became apparent during day-to-day use: bold/non-bold formatting was applied inconsistently across IDs and titles, the Recent Changes activity section omitted the change title entirely, dark mode had two invisible-or-clashing element categories (AC chips and neutral status badges), dark mode progress bars for ACs and Tasks rendered identical gradients, and all metric tiles shared the same solid accent border with no visual differentiation between them. These issues were cosmetic but eroded the readability and polish expected of a shared framework surface.

## Requirements

1. Wave IDs and wave titles must be bold everywhere they appear in the dashboard; change IDs must not be bold; change titles must be bold and immediately follow the change ID.
2. The Recent Changes activity section must display the change title (bold) between the change ID and the update text.
3. Dark mode AC chips (`14/14 required`) and neutral status badges (`planned`) must be visible against dark card backgrounds.
4. The ACs and Tasks mini progress bars must use distinct gradients in dark mode; the base dark-mode override must not collapse variant gradients.
5. Each metric tile must have a distinct color-gradient top border that reflects its content category.

## Scope

**Problem statement:** The dashboard lacked visual consistency in ID/title formatting, omitted change titles from the activity log, had dark-mode visibility failures for several element types, and used a single undifferentiated accent border across all metric tiles.

**In scope:**

- `dashboard.js` — ID/title bold conventions in `OpenWaveCard`, `PendingWaveRow`, `ChangesTable`, `Activity`; change title added to `Activity`; metric tile `variant` field and `className` builder
- `dashboard.css` — `.open-wave-title`, `.pending-wave-title`, `.td .wave-change-id` (non-bold), dark mode `.ac-chip`, `.status-neutral`, `.mini-graph-done` dark-mode override removal, `.metric::before` gradient border system, per-tile gradient variant rules
- `wave_validators.py` — wave doc must declare `Title:` and `## Objective`; wave-owned change docs must have H1 title, `## Rationale`, `## Acceptance Criteria`, `## AC Priority`
- Docs-lint fixture files — updated to comply with new validation rules

**Out of scope:**

- Dashboard data model or server changes
- New dashboard cards or sections
- Any change to the dark mode color palette beyond fixing invisible elements

## Acceptance Criteria

- [x] AC-1: Wave ID and title are bold in the Waves card (open and pending rows); change ID is not bold; change title is bold and follows the change ID in all contexts.
- [x] AC-2: The Recent Changes activity section displays the change title in bold between the change ID and the update text.
- [x] AC-3: In dark mode, AC chips are legible against dark card backgrounds.
- [x] AC-4: In dark mode, the `planned` status badge is legible against dark card backgrounds.
- [x] AC-5: In dark mode, the ACs mini progress bar uses a green→yellow gradient and the Tasks bar uses an orange→yellow gradient (distinct from each other and from the base blue→green).
- [x] AC-6: Each metric tile has a distinct gradient top border: Waves (blue→green), Changes (purple→blue), ACs (green→yellow), Tasks (orange→yellow), Files (rose→orange), Index (teal→blue).
- [x] AC-7: Wave-owned change docs that exist on disk are validated by docs-lint for H1 title, `## Rationale`, `## Acceptance Criteria`, and `## AC Priority`.
- [x] AC-8: Wave docs are validated by docs-lint for `Title:` metadata and `## Objective` section.
- [x] AC-9: Framework test suite passes (1087 tests).

## Tasks

- [x] Update `OpenWaveCard` wave title class to `open-wave-title` (bold, ink color)
- [x] Update `PendingWaveRow` wave title class to `pending-wave-title` (bold, ink color)
- [x] Remove bold from change ID in `ChangesTable` and `Activity`
- [x] Add bold change title to `Activity` component between ID and update text
- [x] Add `.open-wave-title` and update `.pending-wave-title` CSS rules
- [x] Remove `font-weight: 700` from `td .wave-change-id`
- [x] Add dark mode `.ac-chip` rule (rgba background, ink text, subtle border)
- [x] Add dark mode `.status-neutral` rule (ink text, rgba background)
- [x] Delete redundant `html[data-theme="dark"] .mini-graph-done` override that collapsed AC/Tasks gradient variants
- [x] Replace `.metric { border-top: 3px solid var(--accent) }` with `::before` pseudo-element gradient system
- [x] Add `variant` field to metrics array entries and `metric--${variant}` class to tile `className` builder
- [x] Add per-tile gradient CSS rules: `--waves`, `--changes`, `--acs`, `--tasks`, `--files`, `--index`
- [x] Clean up now-unused `border-top-color` dark-mode metric overrides
- [x] Add `import re` and `_H1_TITLE_RE`, `_CHANGE_DOC_REQUIRED_SECTIONS` constants to `wave_validators.py`
- [x] Add wave doc `Title:` and `## Objective` checks to `check_wave_docs()`
- [x] Add change doc content validation (H1, Rationale, AC, AC Priority) to `check_wave_docs()`
- [x] Update docs-lint fixture files to comply with new validation rules
- [x] Verify framework test suite passes

## Affected Architecture Docs

N/A — change is confined to dashboard frontend assets and the docs-lint validator; no topology, boundary, or data-flow changes.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Visual consistency contract for ID/title formatting across all dashboard contexts |
| AC-2 | required | Activity section was missing a core piece of context (the change title) |
| AC-3 | required | Invisible UI elements break dark mode usability |
| AC-4 | required | Invisible UI elements break dark mode usability |
| AC-5 | required | Identical gradients made ACs and Tasks indistinguishable in dark mode |
| AC-6 | important | Per-tile gradients improve scannability; not a correctness issue |
| AC-7 | required | Dashboard-required fields in change docs were unvalidated, creating silent drift risk |
| AC-8 | required | Dashboard-required fields in wave docs were unvalidated, creating silent drift risk |
| AC-9 | required | Non-regression gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-10 | Implemented all tasks: bold/non-bold ID-vs-title conventions applied across all dashboard contexts; change title added to Activity section; dark mode AC chip and status-neutral badge visibility fixed; dark-mode gradient collapse bug fixed by removing redundant override rule; metric tile `::before` gradient border system added with six per-tile gradient variants; docs-lint extended to validate wave doc `Title:`/`## Objective` and wave-owned change doc H1/Rationale/AC/AC Priority; fixture files updated; 1087 tests passing. | `dashboard.js`, `dashboard.css`, `wave_validators.py`, test fixtures |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-10 | Use `::before` pseudo-element for gradient tile borders instead of `border-top` | CSS `border-top` cannot render gradients; `::before` with `inset` positioning gives a clean 3px gradient stripe without changing the element's box model | SVG background, `background-image` on border area (both more complex) |
| 2026-05-10 | Gradient palette chosen to match existing Progress section row colors | Reusing the same color stops (blue, purple, green, yellow, orange) keeps the design system internally consistent without introducing new hues | Independent tile colors (rejected: would diverge from established palette) |
| 2026-05-10 | Files tile: rose→orange (#FF5C8D→#FF9100); Index tile: teal→blue (#00C6A7→#40A3E9) | Completes the color-wheel coverage without repeating any stop already used by the first four tiles | Other combinations (all functionally equivalent; chosen for visual balance) |
| 2026-05-10 | Docs-lint change doc validation scoped to wave-owned change docs only (not plan-stage docs) | Wave-owned change docs have a stable path and confirmed format; plan-stage docs may be mid-draft; validating only wave-owned docs avoids false failures during planning | Validate all change docs regardless of stage (rejected: too many false positives during active planning) |

## Risks

| Risk | Mitigation |
|------|------------|
| `::before` gradient border clipped by `overflow: hidden` on parent | `overflow: hidden` is set on `.metric` itself, which is the `::before` host — no parent clips it |
| Docs-lint new rules break existing wave-owned change docs | New rules only trigger when the change doc file exists on disk; missing file still passes (existence is separately checked by the wave doc validator) |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
