# Dashboard Design System

Owner: Engineering
Status: active
Last verified: 2026-06-22

Reference doc for the local dashboard's shared UI contract. Covers CSS custom property tokens, shell layout, typography scale, spacing, status-color semantics, component rules, and state treatments. Assets live under `.wavefoundry/framework/dashboard/`; this doc is the governance home for seeded-repo UI consistency.

## Design Principles

- **Cool neutral palette.** Light cool-gray backgrounds (`--page-bg: #F8F9FA`, `--panel-bg: #FFFFFF`) keep the dashboard calm and legible; the blue accent (`--accent: #1976d2`) signals action and health without competing with status colors.
- **Graceful degradation first.** Every card and section has an explicit empty-state treatment. No tile ever shows a fabricated number.
- **Read-only posture visible in the UI.** No interactive controls that imply write access. The state badge (`LIVE / IDLE`) conveys server health rather than edit capability.
- **Loopback aesthetics.** Glassmorphism effects (frosted header, translucent card backgrounds) signal a local surface, not a cloud product.

## Token Reference

### Color

All color values are CSS custom properties on `:root`.

| Token | Value | Role |
|---|---|---|
| `--page-bg` | `#F8F9FA` | Page background (cool neutral gray) |
| `--panel-bg` | `#FFFFFF` | Panel / card surface |
| `--panel-border` | `#DEE2E6` | Card borders, dividers |
| `--ink` | `#212529` | Primary text |
| `--muted` | `#6C757D` | Secondary text, labels, footnotes |
| `--accent` | `#1976d2` | Primary action color, healthy / active state |
| `--accent-soft` | `#E3F0FC` | Accent fill for badges, progress track |
| `--accent-mid` | `#91C2F2` | Hover border accent |
| `--footer-accent` | `#2B6CB0` | Footer / branding accent |
| `--warn` | `#C25800` | Warning text |
| `--warn-soft` | `#FEF3E8` | Warning fill |
| `--danger` | `#C62828` | Danger / blocked text |
| `--danger-soft` | `#FFEBEE` | Danger fill |
| `--neutral` | `#495057` | Neutral text (informational) — not re-themed in dark |
| `--neutral-soft` | `#F1F3F5` | Neutral fill |
| `--draft-color` | `#1565C0` | Draft / planned state text |
| `--draft-soft` | `#E3F2FD` | Draft state fill |

Dark-mode overrides live in `html[data-theme="dark"]`; per-token light/dark values are in `tokens/modes/{light,dark}.tokens.json`. `--neutral` is intentionally **not** re-themed in dark (the light value carries forward).

### Shadow

| Token | Value | Use |
|---|---|---|
| `--shadow-sm` | `0 1px 3px rgba(33,37,41,.10)` | Hover lift on metrics and wave cards |
| `--shadow` | `0 1px 4px rgba(33,37,41,.12), 0 2px 8px rgba(33,37,41,.07)` | Default panel elevation |
| `--shadow-lg` | `0 4px 16px rgba(33,37,41,.14), 0 1px 4px rgba(33,37,41,.08)` | Modal / dialog overlay |

### Border Radius

| Token | Value | Use |
|---|---|---|
| `--radius-sm` | `4px` | Chips, code badges, table cells, focus ring |
| `--radius-md` | `6px` | Metric tiles, timeline items, wave cards, mini-graphs |
| `--radius-lg` | `8px` | Hero card, full panels, agent dialog |

### Spacing Scale

Seven-step rem-based scale. Use tokens rather than raw values so the dashboard can be reseeded with a different density without touching component files.

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
| `--font-body` | `-apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif` | Body text, meta labels |
| `--font-heading` | `-apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif` | Panel h2, metric values, dialog title (same system-sans stack as body) |
| `--font-mono` | `ui-monospace, "SF Mono", "Cascadia Code", "Fira Code", "Consolas", monospace` | IDs, version strings, progress fractions, framework label |

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
  width: min(1360px, calc(100vw - 2rem))
  margin: 0 auto
  padding: var(--space-3) 0 var(--space-4)
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

### Header (removed in 1p6nl)

The dashboard no longer renders a top header. The brand (logo + repo name) and the light/dark toggle moved into the sidebar; the former `.site-header` / `.header-*` rules are unused. (Historic note: it was a sticky frosted bar at `z-index: 100` — keep any modal layer above 100 if a header is ever reintroduced.)

### Navigation shell (sidebar + views)

Wave `1p6nl` made the dashboard a navigable shell rather than one long scroll and removed the separate top header. The app is `.app-body` (a flex row: sidebar + `.app-main`); the brand and theme toggle live in the sidebar, and the main content is **view-switched by hash route**.

- **Sidebar** (`.sidebar`) — a full-height sticky left rail (`top: 0`, `height: 100vh`), **default-collapsed** to `--rail-w` (56px, icons only), expanding to 232px (labels). The Wavefoundry mark (`WaveMark` — a sine wave between `< >` brackets with an AI node) + repo name sit at the top and **double as the collapse/expand toggle**. The sidebar **footer** (`.sidebar-footer`) holds the project footer meta (`.sidebar-footer-meta`: Wavefoundry version + `Live`/next-refresh + last-updated — shown only when expanded) above the always-visible light/dark toggle; the dashboard no longer renders a footer bar under the main content. Collapse state persists in `localStorage` (`wf-sidebar-collapsed`). Nav items **and** routing derive from the `NAV_SECTIONS` registry (`{id, label, icon, group}`) — add a section by registering an entry + a view branch; do not hard-code per-view nav. `group` is carried for future grouped rendering (~5+ sections).
- **Routing** — hash-based (`#/work` default, `#/graph`). `GraphPanel` keeps its own History-*state* breadcrumbs (guarded on `e.state.wfGraph`); page routing stays on `location.hash`, so the two history mechanisms don't collide.
- **Work view** (`.app-main-inner`, contained) — hero (metrics, progress, flow, agents) + the two-column content grid. **The graph is no longer here.**
- **Graph view** (`.app-graph`, wide) — the relocated `GraphPanel`. The tree-nav + canvas **flow to natural height** (no fixed scroll band); the page scrolls as one. The WebGL render path keeps its own tall `min-height` (a GL canvas can't size to content).

See ADR `1p6q5-adr dashboard-navigation-shell.md`.

### View Layout Standard

Every section view (Work, Graph, and future Config/Secrets/Docs) is composed the same way so the views read as sibling pages regardless of their width or content. Conform new views to this contract rather than styling each one ad hoc.

1. **View container.** A view's content lives in a centered container with a shared top offset — `padding: var(--space-3) var(--space-4) var(--space-4)` and `margin: 0 auto`. Two width caps, by token:
   - **Contained** — `width: min(var(--view-max), 100%)` (`--view-max` = 1760px). Default; use for content-dense views (`.app-main-inner`: Work, and later Config/Secrets/Docs).
   - **Wide** — `width: min(var(--view-max-wide), 100%)` (`--view-max-wide` = 1760px). Opt-in for canvas-style views (`.app-graph`: the Graph node visualization). Same top padding and centering as contained.

   Both caps are **1760px** today (kept as two tokens so a future content-dense view could narrow `--view-max` without touching the graph). The cap was raised from 1360px so that collapsing the icon rail on a wide display doesn't leave large dead margins around centered content — on a 1920px screen the content fills to 1760px with small symmetric margins instead of sitting at 1360px with ~250px gutters. On laptop widths the content is ~100% either way.

2. **Top-level card chrome (theme-aware).** A view's primary content sits in a **framed panel** that matches `.hero-card` in **both** themes — a visible surface with a border, radius, shadow, and `var(--space-6)` padding, so the content reads as enclosed:
   - **Light:** `background: var(--panel-bg)`, `border: 1px solid var(--panel-border)`, `border-radius: var(--radius-lg)`, `box-shadow: var(--shadow)`, `padding: var(--space-6)`.
   - **Dark:** a solid dark panel — `background: #212428`, `border-color: #30353c`, `box-shadow: 0 8px 32px rgba(0,0,0,.45), 0 1px 4px rgba(0,0,0,.3)` (the dark theme does **not** redefine `--panel-bg`/`--panel-border`, so panels hardcode this palette; `.hero-card` and `.app-graph .graph-card` both use it). Do **not** leave a view's top-level card transparent in dark mode — it must frame its content the same as Work.

3. **View header.** Each view opens with a consistent header — either the hero meta-pill row (Work) or an `h2` panel-heading title plus a `--muted` subtitle/meta line (Graph: "Graph" + node/edge counts). Same type scale across views; don't introduce per-view heading sizes.

The result: switching sections changes the content, not the surface. A new view is a registry entry (`NAV_SECTIONS`) + a view branch that drops its content into a contained-or-wide container with the card chrome above.

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

Two-part bar: track is `--accent-soft` (pill-shaped, `border-radius: 999px`), fill is a `to right` linear gradient from `#40A3E9` to `#53AC04` (lifecycle brand blue → green; see the brand-palette gap G2). Fill uses `transition: width 0.6s cubic-bezier(0.4,0,0.2,1)`.

Mini-graph (used in wave cards) follows the same gradient for the done-segment; remainder is `--accent-soft`.

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

`border-collapse: collapse`, `font-size: 0.92rem`. Column headers: `0.75rem / 600 / uppercase / var(--muted)`. Row hover: `rgba(25,118,210,0.04)` background on `td` (blue accent tint). Last `td` in `tbody` has no bottom border.

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
