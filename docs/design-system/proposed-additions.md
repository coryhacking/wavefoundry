# Proposed Additions

Owner: Engineering
Status: active
Last verified: 2026-06-22

Net-new abstractions proposed during the `1p72v-ref` dashboard primitive
abstraction. These are **codified from existing usage conventions**, not
invented designs — but they unify what were previously inline className patterns
(not extracted functions), so they are recorded here as proposals pending full
call-site adoption rather than treated as already-canonical extracted components.

The reusable functions that existed as real components in the dashboard monolith
(Icon glyphs, ThemeToggle, ProgressBar←ProgressRow, Sparkline←MiniGraph,
Dialog←DialogFrame, FileTree, DiffView, NavSidebar←Sidebar, Prose←renderMarkdownish)
were extracted directly and are recorded in `components/_index.json` as stable,
extracted-from-usage — they are consumed by the dashboard today and are not
"proposals".

## Unified-from-convention (available in `ds/wfds.js`, adoption ongoing)

| Proposed primitive | Unifies (inline convention) | Status |
| --- | --- | --- |
| `Badge` | `badgeClass(status)` + inline `h(span,{className:"status-badge …"})` | Implemented in `ds/wfds.js`; `badgeClass` is consumed by the dashboard, the `Badge` wrapper component is available for new call sites. |
| `Pill` | inline `meta-pill` / `git-*-pill` / `dialog-meta-pill` spans | Implemented; available for adoption. Existing inline pills left in place this wave (no-regression scope). |
| `Chip` | inline `ac-chip` and similar tags | Implemented; available for adoption. |
| `Card` | inline `panel-card` / `hero-card` / `metric-dialog-card` surfaces | Implemented as a thin surface wrapper; existing inline surfaces left in place. |
| `Table` | inline `<table>` structures + markdown-table rendering | Implemented as a structural shell; the dashboard's rich domain tables (ChangesTable, markdown tables) keep their own cell rendering. |
| `EmptyState` | inline `empty-state` blocks | Implemented; available for adoption. |
| `SectionLabel` / `Eyebrow` | inline `wip-section-label` and uppercase eyebrows | Implemented; available for adoption. |

### Why these were not ripped through every call site this wave

The dashboard is a ~4,500-line single-file React app with **no UI test harness**;
the regression guard is structural (`node --check`), the served-asset smoke test,
and operator visual parity (AC-7). Replacing every inline `meta-pill` /
`status-badge` / `empty-state` span across the app in the same wave that
introduces the module would multiply the blast radius with no test coverage to
catch a regression. The library surface (these primitives on `window.WFDS`) and
the contract specs (`components/`) are the deliverable; incremental call-site
adoption of the unified wrappers is a low-risk follow-on, one surface at a time.

These remain **proposals** until an operator confirms the unified markup is the
desired canonical form and adoption proceeds; they must not be treated as
mandatory until then.
