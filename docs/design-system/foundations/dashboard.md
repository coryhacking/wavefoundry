# Dashboard Design System

Owner: Engineering
Status: active
Last verified: 2026-05-09

Reference doc for the local dashboard's shared UI contract. Covers CSS custom property tokens, shell layout, typography scale, spacing, status-color semantics, component rules, and state treatments. Assets live under `.wavefoundry/framework/dashboard/`; this doc is the governance home for seeded-repo UI consistency.

## Design Principles

- **Warm neutral palette.** Parchment backgrounds (`--page-bg`, `--panel-bg`) prevent the dashboard from feeling like a dev-tool; the teal accent (`--accent`) signals action and health without competing with status colors.
- **Graceful degradation first.** Every card and section has an explicit empty-state treatment. No tile ever shows a fabricated number.
- **Read-only posture visible in the UI.** No interactive controls that imply write access. The state badge (`LIVE / IDLE`) conveys server health rather than edit capability.
- **Loopback aesthetics.** Glassmorphism effects (frosted header, translucent card backgrounds) signal a local surface, not a cloud product.

## Token Reference

### Color

All color values are CSS custom properties on `:root`.

| Token | Value | Role |
|---|---|---|
| `--page-bg` | `#f4efe7` | Page background (warm parchment) |
| `--panel-bg` | `#fbf8f2` | Panel / card surface |
| `--panel-border` | `#d8cfc2` | Card borders, dividers |
| `--ink` | `#17201f` | Primary text |
| `--muted` | `#5b665f` | Secondary text, labels, footnotes |
| `--accent` | `#0d6c59` | Primary action color, healthy / active state |
| `--accent-soft` | `#d8efe8` | Accent fill for badges, progress track |
| `--accent-mid` | `#b0ddd0` | Hover border accent |
| `--warn` | `#b66818` | Warning text |
| `--warn-soft` | `#f8e6d0` | Warning fill |
| `--danger` | `#a24034` | Danger / blocked text |
| `--danger-soft` | `#f6ddd8` | Danger fill |
| `--neutral` | `#4a5568` | Neutral text (informational) |
| `--neutral-soft` | `#edf0f4` | Neutral fill |
| `--draft-color` | `#3b6fa0` | Draft / planned state text |
| `--draft-soft` | `#ddeaf6` | Draft state fill |

### Shadow

| Token | Value | Use |
|---|---|---|
| `--shadow-sm` | `0 2px 8px rgba(23,32,31,.06)` | Hover lift on metrics and wave cards |
| `--shadow` | `0 8px 24px rgba(23,32,31,.08), 0 1px 3px rgba(23,32,31,.05)` | Default panel elevation |
| `--shadow-lg` | `0 20px 48px rgba(23,32,31,.10), 0 2px 8px rgba(23,32,31,.06)` | Modal / dialog overlay |

### Border Radius

| Token | Value | Use |
|---|---|---|
| `--radius-sm` | `8px` | Chips, code badges, table cells, close button |
| `--radius-md` | `12px` | Metric tiles, timeline items, wave cards, mini-graphs |
| `--radius-lg` | `18px` | Hero card, full panels, agent dialog |

### Spacing Scale

Eight-step rem-based scale. Use tokens rather than raw values so the dashboard can be reseeded with a different density without touching component files.

| Token | Value | Typical use |
|---|---|---|
| `--space-1` | `0.25rem` | AC chip gap, smallest padding |
| `--space-2` | `0.5rem` | Badge padding, small gap |
| `--space-3` | `0.75rem` | Timeline item padding, section gap |
| `--space-4` | `1rem` | Card internal padding (compact), wave card padding |
| `--space-5` | `1.5rem` | Panel padding (default), section gap |
| `--space-6` | `2rem` | Hero card padding, header padding |
| `--space-7` | `3rem` | Page bottom margin |

### Typography

| Token | Stack | Use |
|---|---|---|
| `--font-body` | `"Avenir Next", "Segoe UI", sans-serif` | Body text, meta labels |
| `--font-heading` | `"Iowan Old Style", "Georgia", serif` | Panel h2, metric values, dialog title |
| `--font-mono` | `"SF Mono", "Fira Code", "Consolas", monospace` | IDs, version strings, progress fractions, framework label |

Type scale (no additional tokens — use these raw values for consistency):

| Role | Size | Weight | Font |
|---|---|---|---|
| Panel heading (h2) | `1.1rem` | 700 | heading |
| Dialog title | `1.3rem` | — (normal) | heading |
| Metric value | `2rem` | 800 | heading |
| Hero progress pct | `2.6rem` | 800 | heading |
| Body / table cell | `0.92rem` | 400 | body |
| Secondary body | `0.88rem` | 400 | body |
| Small label | `0.85rem` | 400 | body |
| Badge / pill | `0.82rem` | 600 | body |
| Eyebrow / section label | `0.72rem` | 700 | body, uppercase, tracked |
| Mono badge | `0.72rem–0.85rem` | 600–800 | mono |
| Header framework string | `0.78rem` | 400 | mono |

## Layout

### Page Shell

```
.shell
  max-width: min(1360px, calc(100vw - 2rem))
  margin: 0 auto
  padding: var(--space-6) 0 var(--space-7)
```

### Two-Column Content Grid

Below the hero, content splits into left (waves + changes) and right (activity) columns. The right column is slightly wider (`1.05fr`) to balance the denser activity timeline against card width.

```
.content-grid
  display: grid
  grid-template-columns: 1fr 1.05fr
  gap: var(--space-5)
```

Collapses to single column at `≤ 1080px`.

### Responsive Breakpoints

| Breakpoint | Change |
|---|---|
| `≤ 1080px` | Hero and content-grid go single-column; metrics → 3 columns |
| `≤ 720px` | Shell padding reduced; panels use `--radius-md`; metrics → 2 columns; status-row stacks vertically; footer stacks |
| `≤ 480px` | Metrics → 2×1fr grid; header framework string hidden |

### Sticky Header

`.site-header` is sticky at `z-index: 100` with frosted glass (`backdrop-filter: blur(16px) saturate(1.2)`) and 92% opacity on the panel-bg background. Do not increase `z-index` past 100 unless creating a modal layer above it.

## Status Semantics

Status badge classes map lifecycle states to a consistent color vocabulary:

| Class | Color pair | Wave Framework state |
|---|---|---|
| `.status-ok` | accent / accent-soft | `active`, `complete`, healthy |
| `.status-neutral` | neutral / neutral-soft | closed, informational |
| `.status-warn` | warn / warn-soft | `paused`, attention needed |
| `.status-draft` | draft-color / draft-soft | `planned`, not yet started |
| `.status-blocked` | danger / danger-soft | blocked, error |
| `.status-unknown` | muted / neutral-soft | missing data, unknown |

State badge (header) semantics:

| Class | State | Meaning |
|---|---|---|
| `.state-live` | LIVE | Server returned data within last poll |
| `.state-idle` | IDLE | No recent poll success |
| `.state-blocked` | BLOCKED | Server or data error |

`.state-live .state-dot` animates with a `pulse` keyframe (2.4 s, accent color).

## Component Rules

### Panels

Base rule shared by `.hero-card`, `.panel`, `.metric`, `.table-card`, `.timeline-card`, `.progress-card`:
- Background `var(--panel-bg)`, border `1px solid var(--panel-border)`, radius `var(--radius-lg)`, shadow `var(--shadow)`.
- Default padding: `var(--space-5)`. Hero card uses `var(--space-6)`.

### Progress Bar

Two-part bar: track is `--accent-soft` (8 px, pill-shaped), fill is a `90deg` linear gradient from `--accent` to `#14937a`. Fill uses `transition: width 0.6s cubic-bezier(0.4,0,0.2,1)`.

Mini-graph (6 px, used in wave cards) follows the same gradient for done-segment; remainder is `--accent-soft`. Gap of `2px` between segments.

### Metric Tiles

`.metric` uses `--radius-md` and `--shadow` (shadow-on-hover). Metric value is `2rem / 800 / heading` with `letter-spacing: -0.03em` and `font-variant-numeric: tabular-nums`.

### Wave Cards

`.open-wave-card` uses a translucent background (`rgba(255,255,255,0.42)`) to nest visually inside the panel. On hover: border shifts to `--accent-mid`, shadow to `--shadow-sm`. Pending wave rows use `.pending-wave-row` with a lighter translucent treatment.

### Agent Pills

`.hero-agent-pill` defaults to a semi-opaque white background with `--panel-border` border. On hover: background shifts to 8% accent tint (`color-mix`), border to `--accent`, text to `--accent`, adds `--shadow-sm`. Use `cursor: pointer`; pill is a `<button>` for keyboard accessibility.

### Agent Dialog

Native `<dialog>` element with class `.agent-dialog`. Width `min(640px, 92vw)`, max-height `82vh`. Backdrop: `rgba(23,32,31,0.35)` with `backdrop-filter: blur(4px)`. Dialog uses `box-shadow: var(--shadow-lg)`.

Dialog is created dynamically (appended to `<body>`, removed on close) to avoid DOM readiness issues with `showModal()`.

### Tables

`border-collapse: collapse`, `font-size: 0.92rem`. Column headers: `0.75rem / 600 / uppercase / var(--muted)`. Row hover: `rgba(13,108,89,0.03)` background on `td`. Last `td` in `tbody` has no bottom border.

### Timeline / Activity

Items grouped by date with `.activity-date` label (ruled line after). Each item is a `<li>` inside `.timeline` with `padding: var(--space-3) var(--space-4)`, translucent white background, hover to a slightly more opaque white.

## Empty, Loading, and Error States

### Empty State

`.empty-state`: centered, muted text, `0.92rem`. Background `rgba(255,255,255,0.35)`, border `rgba(216,207,194,0.5)`, radius `var(--radius-md)`. Must be present in every card that can have zero items.

### Loading State

During the initial fetch (before first poll succeeds), the dashboard renders a minimal skeleton: state badge shows `IDLE`, metric values show `—`. Do not show spinners inside individual cards — the poll interval and state badge are sufficient feedback.

### Error / Graceful Degradation

When `/api/dashboard` returns a non-200 or parse error: state badge transitions to `BLOCKED`; any metric or card that depends on the failed data shows the `.status-unknown` badge or `.empty-state` rather than an exception. The React ErrorBoundary wrapping each card section catches rendering errors and displays a neutral empty-state fallback.

## Accessibility

- Focus ring: `2px solid var(--accent)`, `outline-offset: 3px`, `border-radius: var(--radius-sm)` applied via `:focus-visible`.
- All interactive elements (agent pills, dialog close button) are `<button>` elements with implicit keyboard activation.
- Dialog uses native `<dialog>` with `showModal()` for correct focus trapping and `Escape` key closure.
- Color-alone status indication always pairs with text (badge label or status class label).

## Cross-Links

- `docs/architecture/design-system.md` — extraction philosophy and regeneration semantics
- `docs/architecture/data-and-control-flow.md` — Path 7: dashboard server and frontend topology
- `.wavefoundry/framework/dashboard/dashboard.css` — canonical token and rule implementation
- `.wavefoundry/framework/dashboard/dashboard.js` — React component layer consuming these tokens
- `docs/design-system/index.md` — design system artifact index
