# Generic Project Dashboard Framework

Change ID: `12g47-enh generic-project-dashboard`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-10
Wave: `12g47 dashboard-framework`

## Rationale

Wavefoundry currently gives operators strong read access through docs, lifecycle records, and MCP tools, but it does not provide a generic local dashboard surface that turns that project state into an always-on visual control panel. The referenced dashboard prompt asks for a local-only, read-only web UI that can show real progress, active work, tests, blockers, and recent activity without requiring the operator to keep querying an agent.

For Wavefoundry, this should become a **framework feature**, not a one-off app. The same page shell, server contract, and card system should seed into any Wave Framework repository and adapt to that repository's local sources of truth. Because Wavefoundry is already Python-first and the MCP server is stdio-based, the dashboard should not talk to MCP directly from the browser. Instead, it should reuse the same underlying Python domain logic and expose a loopback-only HTTP JSON surface for a basic React frontend.

## Requirements

1. Wavefoundry must define a **generic local dashboard feature** that can be seeded into any Wave Framework repository through install/upgrade.
2. The dashboard must use a **basic React frontend** with reusable cards/pages and a **Python loopback-only HTTP server** for data access and static-asset serving.
3. The dashboard must be **local-only**, **read-only**, and **no-auth** by default: bind only to `127.0.0.1` / `::1`, never write project state, never push actions, and never require an external service.
4. The architecture must avoid direct browser-to-MCP transport. Instead, it must **reuse shared Python state readers** so the MCP server and dashboard read from the same source-of-truth functions where practical.
5. The generic dashboard must support **graceful degradation**: if a repository lacks tests, task files, logs, or progress data, the UI must render explicit `no data yet` / `unknown` states instead of fake numbers or crashes.
6. The framework must define a **generic dashboard data contract** covering at least wave state, change status, review state, recent activity, optional tests, optional task/progress files, and optional process/log health.
7. The framework must define how repositories declare **dashboard data sources and behavior** in project-visible config, including port preferences, terminology register, polling interval, and optional repo-specific adapters or file paths.
8. The framework must support **multiple Wave Framework repositories running dashboards concurrently** on one machine by separating configured port preference from resolved runtime port selection.
9. The resolved dashboard port must be stored in an **untracked repo-local dashboard metadata file** under `.wavefoundry/` so branch switching and parallel project work do not require committing host-specific port state.
10. The frontend must default to **2-second polling**, with no persistent cache and no fabricated values.
11. The packaged feature must be deployable in a way that survives **branch switching** and other repo-local changes when necessary, including a documented sibling-directory runtime option.
12. The framework must document a generic **dashboard adapter model** so target repos can map their own sources of truth, such as `TASKS.md`, `PROGRESS.md`, test reports, logs, or lifecycle docs, without forking the core UI.
13. The seed pack, install/upgrade paths, packaging flow, and local docs must all describe the dashboard consistently.
14. Tests must cover the dashboard server contract, read-only guarantees, loopback binding, graceful degradation, runtime port allocation, and any shared state-reader extraction from existing MCP logic.
15. The operator-facing `Start dashboard` command must open the browser by default, while the low-level Python server script remains usable in startup-only mode; both paths must always print the final bound URL including port.
16. The framework must define a **basic dashboard design system** for seeded repositories: shell layout, typography, color roles, spacing scale, card/table/status components, state treatments, and responsive behavior, aligned with the existing `docs/design-system/` contract rather than ad hoc CSS.

## Scope

**Problem statement:** Wave Framework repositories can expose rich local state, but today that state is scattered across docs, git history, and MCP tools. Operators who want a visual dashboard must build a custom app or keep asking an agent. There is no generic, framework-backed dashboard architecture that can be reused across projects.

**In scope:**

- Generic dashboard architecture for all Wave Framework repositories
- Basic React frontend with reusable layout/cards
- Python loopback-only HTTP server for JSON + static assets
- Shared domain/state-reader layer reused by MCP server and dashboard where practical
- Generic config contract for dashboard behavior and repo-specific data sources
- Runtime port-allocation metadata under `.wavefoundry/` for concurrent local dashboard sessions
- Default cards for framework-aware repos: wave status, change progress, review state, recent activity, optional tests/logs/task-file progress
- A basic dashboard design system shared across seeded repositories
- Packaging/install/upgrade support for the dashboard feature
- Documentation for adapter patterns and graceful degradation
- Test coverage for server contract, loopback binding, read-only posture, and missing-data handling

**Out of scope:**

- Remote access, auth, multi-user features, or cloud sync
- Write actions such as marking work complete, rerunning tasks, or mutating git state
- A browser talking directly to stdio MCP transport
- Project-specific visual customization beyond configuration and generic theming hooks
- A complex frontend stack beyond basic React needs
- A single globally fixed dashboard port across all repositories
- A full bespoke product-brand redesign for each repository

## Acceptance Criteria

- [x] AC-1: The framework defines a reusable dashboard architecture suitable for all seeded repositories, not just Wavefoundry.
- [x] AC-2: The chosen architecture explicitly uses **React for UI** and **Python for server/data access**, with a clear rationale for why runtime browser-to-MCP is not the transport.
- [x] AC-3: The dashboard server exposes a documented local JSON contract for generic cards such as wave status, change status, review evidence, recent activity, and optional repo signals.
- [x] AC-3a: The dashboard runtime uses a deterministic local port-selection strategy that allows multiple repositories to run concurrently without requiring committed host-specific port changes.
- [x] AC-4: Shared Python state readers are factored so the dashboard does not duplicate Wavefoundry's lifecycle parsing logic unnecessarily.
- [x] AC-5: The dashboard remains read-only, loopback-only, and resilient when data sources are missing, malformed, or mid-write.
- [x] AC-5a: The resolved runtime port is persisted in an untracked `.wavefoundry` dashboard metadata file and reused when possible, while safely falling back when the recorded port is unavailable.
- [x] AC-6: Install/upgrade/package flows can seed or refresh the dashboard feature in target repositories.
- [x] AC-7: The framework documents how a target repo can declare dashboard sources such as task files, test reports, logs, or custom adapters.
- [x] AC-7a: The framework defines a reusable basic dashboard design system with explicit tokens/rules for layout, typography, spacing, color/status semantics, and empty/error/loading states.
- [x] AC-8: The architecture docs are updated to cover the new frontend/server/shared-data topology, trust boundaries, and dashboard design-system relationship.
- [x] AC-9: Tests cover the server contract, read-only posture, loopback binding, and graceful degradation behavior.

## Tasks

- [x] Define the dashboard product boundary and generic feature contract
- [x] Decide the runtime architecture and transport split between React, Python, and shared readers
- [x] Design the shared dashboard JSON contract and adapter model
- [x] Define the config surface for preferred ports, polling, terminology, themes, and repo-local sources
- [x] Define the runtime port-allocation file format and collision-handling strategy under `.wavefoundry/`
- [x] Define the `Start dashboard` command and low-level script startup contract, including open-by-default operator UX and always-print URL behavior
- [x] Define the basic dashboard design system and its relationship to `docs/design-system/`
- [x] Decide how generic dashboard assets are packaged and seeded into target repos
- [x] Identify which existing MCP/lifecycle readers should be extracted into shared Python modules
- [x] Update framework docs and architecture docs for the dashboard topology (AC-8)
- [x] Write tests for server contract, loopback binding, read-only posture, graceful degradation (AC-9)
- [x] Define adapter model for target repos to declare dashboard sources (AC-7)
- [x] Create a wave and admit this change for implementation
- [x] Implement React frontend with client-side UMD React (no build toolchain)

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| dashboard architecture | planner | — | Select frontend/server/shared-reader boundaries and transport model |
| shared state-reader design | architecture-reviewer | dashboard architecture | Avoid duplicating MCP lifecycle parsing |
| packaging + seeding contract | planner | dashboard architecture | Must work for all target repos, not only Wavefoundry |
| implementation plan | implementer | shared state-reader design | Converts architecture into concrete framework work |

## Serialization Points

- The runtime transport decision must be fixed before any dashboard server or frontend scaffolding begins.
- Shared state-reader extraction boundaries must be defined before MCP and dashboard code can evolve in parallel.
- Packaging/install/upgrade expectations must be fixed before any dashboard asset layout is committed into the framework pack.

## Affected Architecture Docs

- `docs/ARCHITECTURE.md`
- `docs/architecture/current-state.md`
- `docs/architecture/domain-map.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/cross-cutting-concerns.md`
- `docs/architecture/testing-architecture.md`
- `docs/architecture/threat-model.md`

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | This must be a framework capability, not a local custom app. |
| AC-2 | required | The transport/runtime split is the core architecture decision the user asked for. |
| AC-3 | required | Without a stable JSON contract, the UI cannot be reused generically. |
| AC-3a | required | Same-host multi-repo operation is a first-class usage mode for this feature. |
| AC-4 | required | Shared readers prevent drift between MCP and dashboard views of project state. |
| AC-5 | required | Read-only, local-only, resilient behavior is the safety baseline. |
| AC-5a | required | Port reuse and fallback behavior must remain host-local rather than leaking into committed project docs. |
| AC-6 | important | Packaging and seeding are necessary for cross-project reuse. |
| AC-7 | important | Repos need a visible way to map their own state sources into the dashboard. |
| AC-7a | important | Shared UI rules prevent every seeded repo from drifting into a one-off dashboard look and interaction model. |
| AC-8 | important | This changes topology and trust boundaries, so architecture docs must reflect it. |
| AC-9 | important | The feature spans UI, server, and shared readers; regression coverage matters. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-08 | Created initial dashboard framework change plan from the referenced dashboard prompt and Wavefoundry architecture review. | `docs/references/project-overview.md`, `docs/ARCHITECTURE.md`, `/Users/coryhacking/Downloads/dashboard-project-prompt_v1.0.md` |
| 2026-05-08 | Created wave `12g47 dashboard-framework` and admitted this change into it for framework planning. | `docs/waves/12g47 dashboard-framework/wave.md` |
| 2026-05-08 | Prepared the wave for implementation by completing AC priority coverage, confirming review lanes, and fixing the dashboard runtime-state contract to use browser state plus host-local endpoint metadata. | `docs/waves/12g47 dashboard-framework/wave.md`, `docs/prompts/prepare-wave.prompt.md` |
| 2026-05-08 | Expanded the dashboard plan to require a basic reusable design system aligned with the existing `docs/design-system/` contract. | `docs/architecture/design-system.md`, `docs/design-system/README.md` |
| 2026-05-08 | Implemented React frontend using client-side UMD React 18 (shipped as local static files — no build toolchain, no CDN). Rewrote `dashboard.js` with `React.createElement` throughout; all existing logic, CSS classes, data shapes, and polling behaviour preserved. Added `react.production.min.js` and `react-dom.production.min.js` to `dashboard/` and MANIFEST. Resolves AC-2. | `.wavefoundry/framework/dashboard/`, `.wavefoundry/framework/MANIFEST` |
| 2026-05-08 | Extended dashboard with: agent/persona/specialist discovery from `docs/agents/` tree with detail dialog (native `<dialog>`, `showModal()`); graduated backoff polling (2→5→8→13→21→30 s, resets on snapshot hash change); `files_updated_today` and `files_updated_week` metrics via mtime scan; full progress log collection (all entries per change doc, not just latest); activity timeline grouped by date. Fixed dialog translucency (`--panel-bg` token) and click registration (dynamic DOM creation). Proper pluralization via `p(n, singular, plural)` helper throughout. | `.wavefoundry/framework/dashboard/dashboard.js`, `.wavefoundry/framework/dashboard/dashboard.css`, `.wavefoundry/framework/scripts/dashboard_lib.py` |
| 2026-05-08 | Added 4 new test classes (DashboardReadOnlyTests, DashboardGracefulDegradationTests, DashboardActivityTests, DashboardAgentCollectionTests); total suite now 1033 tests, all passing. Covers path-traversal rejection, read-only posture, loopback default host, full progress-log iteration, files_updated_week ≥ today, persona prefix stripping, README exclusion, inactive agents collected. Resolves AC-9. | `.wavefoundry/framework/scripts/tests/test_dashboard_server.py` |
| 2026-05-08 | Updated `docs/architecture/data-and-control-flow.md` Path 7 to document React pre-built assets, graduated backoff polling, agents collector, full snapshot data sources including `docs/agents/` tree and file mtime scan, and "browser never speaks to MCP or git directly" trust boundary. Resolves AC-8. | `docs/architecture/data-and-control-flow.md` |
| 2026-05-09 | Wrote design system doc for dashboard (AC-7a): `docs/design-system/foundations/dashboard.md` covers all CSS custom property tokens, layout breakpoints, typography scale, status-color semantics, component rules (panels, progress bar, metric tiles, wave cards, agent pills, dialog, tables, timeline), and empty/loading/error state treatments. | `docs/design-system/foundations/dashboard.md` |
| 2026-05-09 | Wrote adapter model doc (AC-7): `docs/references/dashboard-adapter-model.md` documents the full `docs/workflow-config.json` dashboard config surface, data source reader table, `include_dirs` usage, graceful degradation guarantees, and target-repo extension approaches (config-driven, include_dirs, fork, framework request). | `docs/references/dashboard-adapter-model.md` |
| 2026-05-09 | Wrote install/upgrade/package flows doc (AC-6): `docs/references/dashboard-install-upgrade.md` documents packaging via `build_pack.py`, install via `seed-010` (config seeding, gitignore entry), upgrade via `seed-160` (asset replacement, config backfill), sibling-directory runtime option, and post-install verification steps. | `docs/references/dashboard-install-upgrade.md` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-08 | Use basic React for the frontend | The user explicitly requested React, and a reusable card/grid UI is easier to evolve in a component model | Vanilla DOM-only UI (rejected for this framework feature because the user asked for React and generic page reuse matters more than zero-framework purity) |
| 2026-05-08 | Use Python for the dashboard server and shared readers | Wavefoundry is already Python-first and its lifecycle/state logic already lives in Python | Node backend (rejected: duplicates runtime surface and state readers) |
| 2026-05-08 | Do not use MCP as the browser transport | The current MCP server is stdio-oriented and not browser-native; an HTTP bridge is simpler and safer | Browser-to-MCP transport or embedding MCP in the frontend (rejected: poor fit for local loopback dashboard) |
| 2026-05-08 | Reuse MCP-adjacent domain logic rather than duplicating parsers | Dashboard and MCP should agree on wave/change/review state | Separate parsers for dashboard only (rejected: drift risk) |
| 2026-05-08 | Separate configured port preference from resolved runtime port | Multiple Wave Framework repositories may run dashboards concurrently on one workstation; committed fixed ports would collide or create merge churn | Single fixed port in `docs/workflow-config.json` only (rejected: collision-prone), ephemeral random port with no persistence (rejected: poor operator ergonomics) |
| 2026-05-08 | Keep canonical dashboard policy in `docs/workflow-config.json` and reserve `.wavefoundry/` for runtime state | Matches the existing Wave Framework contract where project-visible behavior lives in docs config, while host-local mutable state stays out of committed docs | Move canonical dashboard config into `.wavefoundry/dashboard-config.json` (rejected for v1: weaker alignment with current project-visible config conventions) |
| 2026-05-08 | Use `dashboard.html` as the seeded browser entrypoint name | Short, explicit, and generic across projects without implying a full frontend framework layout | `index.html` (acceptable but less feature-specific), framework-specific asset naming (rejected: less portable) |
| 2026-05-08 | Keep actual dashboard UI state in browser memory and reserve any `.wavefoundry/` dashboard metadata file for host-local endpoint discovery only | The dashboard's real state is the live API response plus browser interaction state; persisting that state to repo files would create drift and unnecessary artifacts | Persist full dashboard state to `dashboard.json` (rejected: stale snapshot risk), no metadata file at all (acceptable fallback if deterministic porting alone is sufficient) |
| 2026-05-08 | Make the operator-facing `Start dashboard` command open the browser by default, while the low-level Python script remains composable and startup-only unless told to open | Good operator UX without forcing browser launch side effects on automation, tests, or headless runs; both paths always print the final URL for copy/paste and diagnostics | Make the raw script auto-open by default (rejected: worse for automation/headless use), never auto-open anywhere (rejected: weaker operator ergonomics) |
| 2026-05-08 | Use a deterministic preferred-port strategy with fallback scanning | Stable defaults improve bookmarks and operator memory, while fallback scanning handles real conflicts | Purely random free-port selection every start (rejected: unstable UX) |
| 2026-05-08 | Ship React 18 UMD production builds as local static files (`react.production.min.js`, `react-dom.production.min.js`) rather than loading from a CDN | Preserves local-only, no-network-dependency contract from AGENTS.md and the change doc risk register; target repos receive prebuilt files via install/upgrade with no Node/npm requirement | CDN reference (rejected: violates local-only principle); build toolchain with JSX (rejected: adds npm dependency to target repos at install time) |
| 2026-05-08 | Reuse the existing Wavefoundry design-system contract as the dashboard's UI governance surface | The dashboard needs intentional shared UI rules, but it should extend the existing design-system architecture instead of inventing a second parallel styling contract | Ad hoc component CSS only (rejected: too much drift risk), a dashboard-specific standalone design-system format (rejected: duplicates existing design-system surface) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Dashboard becomes Wavefoundry-specific instead of generic | Define adapter/config model before implementation and keep core cards source-agnostic |
| Browser UI and MCP views drift apart | Extract shared Python readers and keep both transports on the same state functions |
| React toolchain adds friction to target repos | Ship prebuilt assets in the framework pack; avoid requiring npm in target repos at runtime |
| Generic progress cannot be computed for every repo | Design explicit graceful degradation and repo-declared source mapping |
| Local-only guarantees erode over time | Test loopback binding, no-write behavior, and no-auth assumptions explicitly |
| Multiple repos compete for the same dashboard port | Store preferred port in config, persist resolved port in untracked `.wavefoundry` dashboard metadata, and fall back to the next free port in a bounded range |
| Dashboard UI drifts into one-off per-repo styling and semantics | Define a small shared design system for shell, tokens, status colors, density, states, and responsive behavior, then seed it consistently across repos |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
