# 1p6q5-adr — Dashboard navigation shell (collapsible sidebar + section registry)

Owner: Engineering
Status: accepted
Last verified: 2026-06-21

## Context

The local dashboard (`.wavefoundry/framework/dashboard/`) was a single scrolling page — no build step, React via `React.createElement`. The graph index visualization (`GraphPanel`) rendered as a ~85vh band inside the home hero card, competing for space with the operator's primary focus: waves, changes, ACs, tasks. The dashboard is also growing beyond a "dashboard" — configuration, secret-scan results, and eventually operator document editing should be reachable. A single scroll does not scale to multiple top-level surfaces.

## Decision

Introduce a navigable shell: a **collapsible left sidebar (default-collapsed to a ~56px icon rail)** + **hash routing** (`#/work`, `#/graph`) + a **data-driven section registry** (`{id, label, icon, group}`) that decouples nav chrome from views. The graph relocates off the home page into its own `#/graph` view; "Work" (waves/changes) is the default home. A new section is added by registering one registry entry — which drives **both** the nav and the router — plus a view branch in the `Dashboard` view-switch. Nav and routing are fully registry-driven (no hard-coded per-view nav); the view *body* is currently dispatched by a small `view === …` switch in `Dashboard` rather than a per-entry `render` field (an acceptable simplification at two sections — promoting to a `render`-field lookup is a clean later step once the set grows). The nav renderer is a thin layer over the registry, so the chrome (a sidebar today) is swappable without touching sections or routing. No build step is introduced.

All views conform to a shared **View Layout Standard** (centered container with a contained/wide width cap by token + theme-aware top-level card chrome) so they read as sibling pages — see `docs/design-system/foundations/dashboard.md`.

## Consequences

**Positive:**
- The graph no longer competes with the home focus and gets a full-width view.
- The framework surface can grow (Config / Secrets / Docs are drop-in: register an entry + a view).
- Hash routing makes views deep-linkable and back/forward-navigable.
- Collapse state is persisted (localStorage); default-collapsed keeps the home content-first.

**Negative / tradeoffs:**
- More shell chrome than a single scroll; the permanent rail costs a little width.
- Frontend is manual-verification-heavy (no JS test harness); structural changes rely on `node --check`, a served-asset smoke test, and careful review rather than automated UI tests.
- Adding the 3rd section edits the `Dashboard` view-switch (not purely additive) until/unless it is promoted to a registry `render` field — nav + routing remain additive.
- `GraphPanel` mounts only on `#/graph`, so its internal drill-in breadcrumb stack resets to overview when the operator leaves and returns to the Graph view. This is benign (correct view, no crash) and is the same per-mount behavior that keeps the graph's History-*state* channel isolated from page routing; preserving the stack across view switches is a later-increment option.

**Constraints imposed:**
- New sections MUST register in `NAV_SECTIONS` and provide a view; nav + routing derive from the registry — do not hard-code per-view navigation.
- `GraphPanel` keeps its own History-*state* breadcrumbs, guarded on `e.state.wfGraph`; page routing MUST stay hash-based (URL `location.hash`) so the two history mechanisms stay isolated.
- The `group` field is carried in the registry from the start; grouped-section rendering switches on later (~5+ sections) — a render change, not a data migration.

## Alternatives Considered

| Alternative | Reason rejected |
|-------------|----------------|
| Top-nav tabs | Doesn't scale or group as sections grow; would need a later renderer swap. Viable only because the registry is chrome-agnostic — but a second pass. |
| Static (always-expanded) sidebar | Permanently eats content width; the graph (and home) want that width back. |
| Keep the single scroll | Doesn't address the graph-vs-focus space tension or the growing surface. |
| Introduce a build step (JSX/bundler) | Out of scope; a separate, larger decision. The shell works in the existing no-build model. |

## References

- Change `1p6nl-enh dashboard-nav-shell-and-graph-view`, wave `1p6nm dashboard-ui-navigation`
- `.wavefoundry/framework/dashboard/dashboard.js` — `NAV_SECTIONS`, `Sidebar`, `useHashRoute`, `useSidebarCollapsed`, `Dashboard`
- `.wavefoundry/framework/dashboard/dashboard.css` — `.app-body`, `.sidebar`, `.app-main`, `.app-graph`
