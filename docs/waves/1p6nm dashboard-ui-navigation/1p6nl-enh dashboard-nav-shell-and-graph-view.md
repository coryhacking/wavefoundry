# Dashboard UI — collapsible-sidebar nav shell + graph relocation (increment 1)

Change ID: `1p6nl-enh dashboard-nav-shell-and-graph-view`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-21
Wave: TBD

## Rationale

The dashboard is a single-page scroll. The graph index visualization (`GraphPanel`, ~730 lines, `dashboard.js:3211`) renders as a **~85vh band inside the hero card** (`dashboard.css:1742`), competing for space with the operator's primary focus — **waves, changes, ACs, tasks, activity**. The graph is great for search/navigation (mostly for agents), but it shouldn't own the home page.

The dashboard is also outgrowing "dashboard": we want to expose more of the framework over time — **configuration, secret-scan results, and eventually operator document editing**. That needs a navigable shell, not a single scroll.

This change establishes that shell — a **collapsible left sidebar (default-collapsed to a slim icon rail)** + **hash routing** + a **data-driven section registry** that decouples nav chrome from views so the surface can grow without rework — and uses it for the **first move: relocate the graph off the home page into its own Graph view.** "Work" (waves/changes) becomes the focused home.

## Design — target information architecture

**Shell:** keep the existing sticky top header (`Header`, `dashboard.js:427`: brand + theme toggle) and add a **collapse toggle**. Add a **left sidebar**, default-collapsed to a ~56px icon rail; expands to labeled, groupable nav. Collapse state persisted (localStorage). Responsive: auto-collapse / off-canvas on narrow widths.

**Section registry (the "framework"):** a data-driven list of entries `{ id, label, icon, group?, render }`. Both the nav renderer and the router read the registry. Adding a section later = register one entry + a view component. Nav chrome (sidebar vs any future top-bar) is a thin renderer over this registry — the registry + routing are chrome-agnostic, so the look is swappable without touching sections.

**Routing:** hash-based (`#/work` default, `#/graph`). Deep-linkable, back/forward works. `GraphPanel`'s **internal** breadcrumb `pushState` (`dashboard.js:3610`) must be isolated from / namespaced under page-level routing so they don't collide.

**Views:** `<main>` renders the active section's view.

| Section | Holds | This increment |
| --- | --- | --- |
| **Work** (home, default) | active wave, pending waves, changes table, ACs/tasks, framework flow, metrics, activity timeline, agents — *graph removed* | ✅ built |
| **Graph** | the relocated `GraphPanel` (search/navigate) | ✅ built (moved) |
| **Config** | `workflow-config.json`, gates, framework settings (view → later edit) | roadmap |
| **Secrets** | `scan-findings.json` results + finding lifecycle | roadmap |
| **Docs** | doc viewer → later operator editing | roadmap (deferred) |

**Grouping:** the registry carries a `group` field **from day one**, but grouping is **rendered flat for now** (only Work + Graph). Grouped section headers (e.g. *Work / Inspect / Configure*) switch on when the set grows (~5+ sections) — a render change, not a data migration.

**Graph benefit:** in its own view the graph runs full-width and **gains width when the sidebar is collapsed** — better than today's boxed hero-card band.

## Requirements

1. **Collapsible sidebar shell.** A left sidebar renders alongside the retained top header; it is **default-collapsed** to a ~56px icon rail with a toggle to expand; collapse state persists across reloads (localStorage); narrow widths auto-collapse / go off-canvas.
2. **Data-driven section registry.** Sections are entries `{id, label, icon, group?, render}`; both the nav renderer and the router read the registry; adding a section is one entry + a view (no shell edits). The `group` field exists from day one (rendered flat this increment).
3. **Hash routing.** `#/work` (default) and `#/graph`; deep-linkable; browser back/forward works; `GraphPanel`'s internal breadcrumb `pushState` is isolated from / namespaced under page routing so the two don't collide.
4. **Work view.** Renders the current home content **minus `GraphPanel`** (hero meta, metrics, progress, framework flow, agents, waves, changes, activity); the graph is removed from the hero-card; home fits ~1 viewport.
5. **Graph view.** Renders the relocated `GraphPanel` with **no change to its internal logic or `/api/graph` fetch**; it relayouts to available width when the sidebar collapses/expands.
6. **Styling / no build.** Sidebar/rail/collapse + content reflow built with the existing CSS tokens; no CSS framework added; no build step (`React.createElement`, CDN deps unchanged).
7. **No server change.** Existing `/api/*` endpoints suffice; `/api/graph` continues to feed the Graph view.
8. **ADR.** Record the nav architecture (collapsible sidebar, decoupled registry, hash routing) under `docs/architecture/decisions/`.
9. **No regression.** Modals, SSE live updates, theme toggle, metric cards, and agent dialogs continue to work.

## Scope

**In scope (increment 1):** the collapsible sidebar shell + persisted collapse (default-collapsed) + responsive behavior; the data-driven section registry; hash routing; the **Work** view (current home minus `GraphPanel`); the **Graph** view (relocated `GraphPanel`, no internal logic/data changes); the nav-architecture ADR.

**Out of scope (roadmap / later increments):**

- **Config**, **Secrets**, **Docs** views and any **document-editing** capability.
- **Rendering** grouped sections (registry carries `group`; flat render for now).
- Any **new server endpoints** (existing `/api/*` suffice; `/api/graph` still feeds the Graph view).
- Any **build-step** change — stays no-build (`React.createElement`, CDN React/ELK).

## Acceptance Criteria

- [x] AC-1: collapsible left sidebar (`Sidebar`), **default-collapsed** to a 56px icon rail, toggle button, collapse state persisted in `localStorage` (`useSidebarCollapsed`), top header retained. Narrow widths: the 56px rail is viable at all widths; a dedicated mobile off-canvas drawer is deferred (open question #2).
- [x] AC-2: `NAV_SECTIONS` registry (`{id, label, icon, group}`) drives the nav (`Sidebar` maps it) and the router (`useHashRoute(NAV_SECTION_IDS)`); a new section = one registry entry + a view branch in `Dashboard`. (View rendering is a `view`-switch in `Dashboard` rather than a `render` field on the entry — equivalent "one entry + a view".)
- [x] AC-3: hash routing (`#/work` default, `#/graph`) via `useHashRoute`; deep-linkable, back/forward works. Isolated by construction: `GraphPanel`'s breadcrumbs use the History *state* API guarded on `e.state.wfGraph` (`dashboard.js` popstate handler), while page routing keys off `location.hash` — separate channels, no collision.
- [x] AC-4: the **Work** view (`#/work`) renders the hero + content-grid **without `GraphPanel`**; the graph is removed from the hero-card.
- [x] AC-5: the **Graph** view (`#/graph`) renders the relocated `GraphPanel` unchanged (same `/api/graph` fetch). Width: the flex `.app-main` reflows on sidebar expand/collapse and `GraphPanel`'s SVG scales to the container via its `viewBox` (ELK re-layout-on-resize not added — the graph fits the new width). **Known accepted limitation (increment 1):** `GraphPanel` mounts only on `#/graph`, so leaving the Graph view via the nav and returning resets its internal drill-in breadcrumb stack to overview (the remount re-stamps `navIndex:0`). Benign — correct view, no crash, and this per-mount reset is exactly what keeps the graph History-state channel isolated from page routing. Preserving the drill-in stack across view switches is a later-increment enhancement.
- [x] AC-6: roadmap sections (Config/Secrets/Docs) documented in the registry comment + the IA; entries carry `group`; rendered flat this increment.
- [x] AC-7: no regression — full suite **3335 green** + **161 dashboard tests** green; served-asset smoke returns 200 for `/dashboard.{html,css,js}` + `/api/dashboard` + `/api/graph`; all Work components, modals, SSE/polling (App untouched), theme toggle preserved. No build step, no server change. (Browser visual confirmation is the remaining manual step — no JS test harness.)
- [x] AC-8: ADR `1p6q5-adr dashboard-navigation-shell.md` added under `docs/architecture/decisions/` and linked from the index.
- [x] AC-9: **View Layout Standard** — Work and Graph render through a shared view contract: a centered container with shared top padding and a width cap by token (contained `--view-max` 1360px / wide `--view-max-wide` 1760px), plus a top-level card that adopts `.hero-card`'s **framed-panel** chrome in **both** themes (light: `--panel-bg`/border/shadow; dark: the `#212428`/`#30353c`/shadow panel `.hero-card` uses — *not* transparent). The relocated Graph view had inherited the old *in-hero-card* transparent `.graph-card` treatment and a full-width, lower-top container, so it read as a different surface than Work; it was brought into the standard. Standard documented in `docs/design-system/foundations/dashboard.md` (**View Layout Standard**); dead `--header-h` token removed. Operator-directed (2026-06-21) after a visual review. Verified: served-asset smoke (assets + `/api/*` 200), CSS tokens/selectors present, CSS brace-balanced.

## Tasks

- [x] `Sidebar` + collapse toggle + persisted default-collapsed state (`useSidebarCollapsed`). (Top `Header` later **removed** — brand + theme toggle consolidated into the sidebar per the 2026-06-20 Decision Log. Off-canvas/mobile drawer deferred — open Q#2.)
- [x] `NAV_SECTIONS` registry + `Sidebar` nav renderer + `useHashRoute` router, both registry-driven.
- [x] Hash routing; `GraphPanel` `pushState` isolated structurally (its popstate is guarded on `e.state.wfGraph`; page routing is `location.hash`).
- [x] Work view = hero + content-grid minus `GraphPanel`.
- [x] Graph view = relocated `GraphPanel` (internals untouched); SVG scales to width via `viewBox` on reflow.
- [x] CSS: `.app-body`/`.sidebar`/rail/collapse + `.app-main`/`.app-graph` reflow, existing tokens, no framework (`--rail-w`, `--view-max`, `--view-max-wide` added; a `--header-h` token was briefly added then removed — see AC-9).
- [x] ADR `1p6q5-adr dashboard-navigation-shell.md` (+ index link).
- [x] No-regression verified (full suite **3335** + **161** dashboard tests + served-asset smoke); updated the dashboard design doc (`docs/design-system/foundations/dashboard.md`).
- [x] View Layout Standard: shared contained/wide view container (`--view-max` / `--view-max-wide`) + theme-aware top-level card chrome; relocated Graph view conformed to it; standard recorded in the dashboard design-system doc; dead `--header-h` token removed.
- [x] Graph/shell UX polish (operator-directed): (1) zeroed the graph `h2` UA top margin so the Graph title aligns with Work's top; (2) moved the footer (version + live/refresh + updated) out of `app-main` into `.sidebar-footer` (`.sidebar-footer-meta`, hidden when collapsed) and removed the now-dead `.site-footer` bar rules; (3) removed the fixed `min(85vh,920px)` graph scroll band so the tree-nav + canvas flow to natural height (WebGL viewport given its own tall `min-height`); (4) tightened the Communities breadcrumb-to-list gap. Updated the `test_dashboard_js_includes_readable_graph_overview_controls` CSS contract to assert the natural-height layout (`--graph-band-height` removed, `align-items: start`) instead of the old fixed band.
- [x] Raised the contained-view cap `--view-max` 1360px → 1760px (operator-directed): collapsing the icon rail on a wide display left ~250px dead margins around the centered Work content; at 1760px it fills the wide screen with small symmetric margins (matching the Graph view) and is unchanged on laptops. Both view caps are 1760px now.
- [x] Sidebar-footer + Neighbors tweaks (operator-directed): reordered the sidebar footer to a row — **theme toggle → `Live`/refresh → version** — and moved the last-updated timestamp from an always-visible line into a **hover tooltip on the status** (removed the dead `.site-footer-updated` selector); made the Neighbors tree-nav items single-line with **horizontal scroll** (`overflow-x: auto`) so long identifiers stay inside the panel instead of spilling out.
- [x] Delivery-review cleanup: removed the dead-code island orphaned by the operator-directed `Header` removal — `StateBadge` + `computeState` (JS) and the `.site-header` / `.header-*` / `.state-*` blocks + `@keyframes pulse` + their dark-mode/`@media` variants (CSS). Deletion-only; live `.shell` / `.site-footer` / `.status-*` / `metric-pulse` / `sse-pulse` / `--rail-w` preserved. Also: brand `aria-label` now carries repo name + toggle action; doc drifts reconciled (open-Q#4, token list, `Header`-retained task line). Re-verified: `node --check` OK, full suite **3335** green, served-asset smoke 200s.

## Open questions (resolve at prepare)

1. **Icons** for the collapsed rail — one per section (inline SVG set?), source/style.
2. **Mobile/narrow** behavior — off-canvas drawer vs auto-collapse-to-rail (and the breakpoint).
3. **Work view contents** — confirm metrics bar + agents stay on Work (vs a future "System"/"Index" section).
4. **Default route + brand click** — `#/work` default. **Resolved/superseded (2026-06-20 Decision Log):** the brand/logo doubles as the **collapse/expand toggle**, not a Work link; Work is reached via the Work nav-item.
5. **Persist scope** — collapse state in localStorage (per-browser); confirm acceptable.

## Affected Architecture Docs

Update the dashboard architecture description; add a new ADR under `docs/architecture/decisions/` for the nav shell.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The collapsible shell is the deliverable. |
| AC-2 | required | The registry is what "establish the framework" means. |
| AC-3 | required | Routing + GraphPanel pushState isolation (correctness). |
| AC-4 | required | Moving the graph off home is the stated goal. |
| AC-5 | required | Graph must keep working, relocated. |
| AC-6 | important | Roadmap captured; registry future-proofed. |
| AC-7 | required | No regression. |
| AC-8 | important | Decision record for the new architecture. |
| AC-9 | required | Operator-flagged that Graph read as a different surface than Work; the shared view standard is what keeps sections coherent as the surface grows. |


## Risks


| Risk | Mitigation |
| --- | --- |
| `GraphPanel`'s internal `pushState` breadcrumbs collide with page hash routing. | AC-3: isolate/namespace graph history from page routes; test back/forward across both. |
| The SVG/ELK graph doesn't reflow cleanly when the sidebar collapses/expands. | AC-5: recompute/relayout on container resize; verify on collapse. |
| Scope creep into Config/Secrets/Docs. | Explicitly out of scope; registry-ready but unbuilt this increment. |
| 4.7k-line `dashboard.js` makes the shell change risky. | Shell change is additive (wrap `<main>` in a view-switch, move one component); `GraphPanel` itself is untouched. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-06-19 | Collapsible left sidebar, **default-collapsed** to an icon rail. | Resolves the graph-vs-focus space tension (collapse reclaims width) and scales/groups for the growing framework surface; collapsed state gives the lightweight top-nav feel the operator also liked. | Top-nav tabs (doesn't scale/group; would need a later renderer swap) — viable only because the registry is chrome-agnostic, but a second pass; static sidebar (permanently eats content width). |
| 2026-06-19 | Decouple nav chrome from a data-driven section registry + hash routing. | "Establish the framework" so future sections are drop-in and the nav look is swappable without rework. | Hard-coded per-view nav (the current no-pattern state). |
| 2026-06-19 | Stay no-build (`React.createElement`). | Matches the existing dashboard; a build step is a separate, larger decision. | Introduce JSX/bundler (out of scope). |
| 2026-06-20 | Consolidate brand (logo + repo name) + theme toggle into the sidebar; the **logo is the collapse/expand toggle**; remove the top `Header`. | Operator-directed refinement — a cleaner app-shell; everything lives in the rail, content gets the full top. | Keep the separate top header + a dedicated hamburger toggle (rejected — redundant chrome). |
| 2026-06-20 | New Wavefoundry mark (`WaveMark`): a sine wave between code brackets `< >` with an AI node on the crest. | Represents wave + software-engineering + AI in one legible small mark; replaces the generic rotated-square logo. | Keep the abstract square (rejected — no meaning); external/found asset (rejected — no-build, inline SVG fits). |
| 2026-06-21 | Define a **View Layout Standard** (shared container with contained `--view-max` / wide `--view-max-wide` caps + theme-aware top-level card chrome) and conform the relocated Graph view to it; remove the dead `--header-h` token. | The relocated Graph view inherited the in-hero-card transparent `.graph-card` treatment and a full-width, lower-top container, so it read as a different surface than Work (operator-flagged on visual review). A documented standard keeps Work / Graph / future Config-Secrets-Docs coherent. | Bespoke per-view styling (rejected — drifts again as views grow); contain Graph to the exact 1360px Work width (rejected — the Graph canvas benefits from width; the wide cap is identical on laptops and only wider on large displays). |
| 2026-06-21 | **Dark-mode framing correction** (operator-flagged on screenshot): the Graph view's top-level card must be the **framed dark panel** (`#212428`/`#30353c`/shadow), matching `.hero-card`, not transparent. | The first View Layout Standard pass mistakenly made `.app-graph .graph-card` transparent in dark, modeled on the *earlier* `html[data-theme="dark"] .hero-card { transparent }` rule — but a **later** dark rule (`#212428` panel) overrides it, so Work actually renders a framed panel in dark. Graph read as flat/borderless next to a framed Work. Verified by headless screenshot of both views. | Leave Graph transparent in dark (rejected — it was the bug); redefine `--panel-bg` for dark globally (rejected — out of scope; the codebase hardcodes dark panel colors per-component). |
| 2026-06-21 | Graph/shell UX polish (operator-directed, post-visual-review): move the footer into the sidebar; let the graph view flow to natural height (no fixed scroll band); tighten Graph top spacing and the Communities breadcrumb gap. | Operator feedback on the rendered pages: the footer reads better pinned under the sidebar; the graph reads better flowing to the page bottom than boxed in an 85vh scroll band; the Graph title had extra top space and the breadcrumb sat too far from the list. | Keep the footer as a full-width bar under main (rejected — operator moved it to the sidebar); keep the fixed graph band (rejected — operator wants natural height). The WebGL path keeps an explicit tall `min-height` since a GL canvas can't size to content. |
| 2026-06-21 | Delivery review (lanes + Wave Council delivery pass + adversarial verify): fold the **dead-code island** cleanup into this change rather than a follow-up — delete `StateBadge`/`computeState` (JS) and the `.site-header`/`.header-*`/`.state-*` + `@keyframes pulse` + dark/`@media` residue (CSS). | The operator-directed `Header` removal orphaned a connected island; fix-now-not-later applies (deletion-only, no contract/behavior change, fully covered by the green 3335-test suite + `node --check` + smoke). Council unanimously recommended folding it in; the `Header` removal is the trigger and this is its direct residue. | Track as a follow-up wave (rejected — pure dead code with the removal as its trigger; a follow-up carries inert residue through every downstream upgrade). Note: the `.state-*`/`StateBadge` portion was already dead pre-wave and was swept opportunistically alongside the `Header` residue (transparent, deletion-only). |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
