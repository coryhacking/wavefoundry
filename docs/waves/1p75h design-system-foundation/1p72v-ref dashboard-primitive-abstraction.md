# Dashboard Primitive Abstraction + Token Consumption

Change ID: `1p72v-ref dashboard-primitive-abstraction`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-22
Wave: `1p75h design-system-foundation`

## Rationale

The dashboard ships as a single self-mounting React app: `.wavefoundry/framework/dashboard/dashboard.js` (~4,825 lines, React via UMD globals, `React.createElement` aliased `h`, no exports) plus `dashboard.css` (~3,819 lines). Repo analysis identified ~45 components — but only a thin reusable layer (~8 true primitives + ~6 composites) is buried as internal functions, while the styling has three structural debts the design-system architecture explicitly warns against ("assets should align with the design-system token surfaces rather than accreting ad hoc styling rules in isolation", `docs/architecture/design-system.md`):

1. **No reusable component surface.** Primitives (`StateBadge`, `ProgressRow`, `DialogFrame`, `Sidebar`, icons, …) are not exported or named in `components/_index.json`, so nothing — neither the dashboard's own future code nor the claude.ai/design sync — can consume them as a library.
2. **Tokens bypassed in code.** Dark mode is implemented with ~120 hardcoded-hex `html[data-theme="dark"] .selector` rules; the "Aceiss" brand palette and the 8 agent-role category colors are hardcoded, not tokenized; a token family (`--text/--border/--surface/--surface-raised`) is **referenced but never defined** (latent rendering bug). These are recorded as gaps by `1p6z6-enh`.
3. **A real bug:** `_graphEdgeLineOpacity` is defined twice (the second shadows the first) — dead code that should be removed.

This change abstracts the reusable layer into a maintained, exportable primitive module the dashboard consumes, binds styling to the semantic tokens produced by `1p6z6-enh`, records each primitive in the contract (`components/`), and fixes the recorded CSS gaps. It is the "library" half of the operator's "library first, sync from it" direction; the claude.ai/design sync (a follow-on wave) will consume this module's build + the `12atj` token exports.

## Requirements

1. **Primitive module.** Create a maintained, exportable primitive module under `.wavefoundry/framework/dashboard/` (e.g. `ds/`) exposing the ~16 abstracted primitives — `Icon` (Sun/Moon/Nav/WaveMark + graph icons), `ThemeToggle`, `Badge` (unifies `StateBadge` + `.status-badge` variants), `Pill` (unifies meta/git/index/handoff pills), `Chip`, `ProgressBar` (from `ProgressRow`), `Sparkline` (from `MiniGraph`), `Card` (unifies panel/hero/table-card surfaces), `Dialog` (from `DialogFrame`), `Table`, `FileTree`, `DiffView`, `EmptyState`, `SectionLabel`/`Eyebrow`, `NavSidebar` (from `Sidebar`), `Prose`/`Markdown` (from `renderMarkdownish`). The module must be esbuild-bundlable and expose primitives on a global for downstream (sync) consumption while remaining UMD-React-compatible for the dashboard.
2. **Dashboard consumes the module.** Refactor `dashboard.js` to import/use the shared primitives in place of the inlined functions, with **no behavioral or visual regression** to the running dashboard.
3. **Token consumption (close `1p6z6` gaps).** In `dashboard.css`: define the undefined `--text/--border/--surface/--surface-raised` family (alias to existing tokens or add primitives); tokenize the "Aceiss" brand palette and the agent-role category colors; route the per-component hardcoded-hex dark overrides through token vars where feasible. Remaining un-tokenizable cases stay as recorded gaps with rationale.
4. **Contract specs.** Populate `components/_index.json` and per-component `spec.json` for each abstracted primitive (props, variants, states, token bindings, accessibility), per the contract shape. Genuinely new abstractions (e.g. unified `Badge`) are recorded as extracted-from-usage, not invented; net-new proposals go to `proposed-additions.md`.
5. **Bug fix.** Remove the duplicate `_graphEdgeLineOpacity` definition; confirm the surviving definition is the intended one.
6. **Visual parity verification.** Demonstrate the refactored dashboard renders identically pre/post (light + dark) for the affected surfaces — screenshot comparison or an equivalent reviewer check.
7. **Framework hygiene.** All `.wavefoundry/framework/` edits performed under the `framework_edit_allowed` gate (open before, close immediately after). Framework tests run bytecode-free and pass.

## Scope

**Problem statement:** The dashboard's reusable UI is locked inside a monolith, its styling bypasses the token contract, and there is no library surface for the dashboard or the design sync to build on.

**In scope:**

- New primitive module under `.wavefoundry/framework/dashboard/` (extractable, bundlable, token-bound).
- `dashboard.js` refactor to consume the module; duplicate-function bug fix.
- `dashboard.css` edits: define missing token family, tokenize brand/category palettes, route dark overrides through tokens.
- `components/_index.json` + `spec.json` population; `proposed-additions.md` for net-new.
- Visual-parity verification (light + dark).

**Out of scope:**

- Token extraction / semantic layer / narrative reconciliation — owned by `1p6z6-enh`.
- Token-build exports pipeline — owned by `12atj-feat`.
- Abstracting the heavy app-domain components (`GraphPanel`, `Dashboard`, `App`) into the library — they stay app-coupled; only the reusable layer is extracted this wave.
- The claude.ai/design sync upload — follow-on wave (this change produces the consumable build it will use).

**Depends on:** `1p6z6-enh` (token vocabulary + gap log), `12atj-feat` (token export targets the module/CSS should align to — soft dependency; coordinate naming).

## Acceptance Criteria

- [x] AC-1: A primitive module exists under `.wavefoundry/framework/dashboard/` (`ds/wfds.js`), exports the ~16 named primitives on `window.WFDS`, and is esbuild-bundlable (single `defineWFDS(React)` factory) for downstream sync. Per locked operator decision the consumption model is no-build script-tag global — esbuild bundling is available for the future sync but **not** required for the dashboard to run.
- [x] AC-2: `dashboard.js` consumes the shared primitives from `window.WFDS`; inlined copies of every abstracted function were removed (icons, ThemeToggle, MiniGraph, ProgressRow body, DialogFrame, FileTree/buildFileTree, DiffView core, NavIcon, WaveMark, Sidebar body, renderInline/renderMarkdownish, badgeClass). `node --check` passes; full suite green (3347).
- [x] AC-3: The `--text/--border/--surface/--surface-raised` family is defined in `dashboard.css` (aliased to `--ink`/`--panel-border`/`--panel-bg`/`--neutral-soft`); grep-verified no dangling token-family `var(--…)` remain (only the deliberately inline-set `--kind-bg`/`--kind-color` per-element props with fallbacks).
- [x] AC-4: The Aceiss brand palette and all 8 agent-role category colors are tokenized (light `:root` + dark override block, exact prior hex, no drift); every `.hero-agent-pill--*` / `.hero-agent-label--*` rule routes through tokens. Remaining un-tokenizable `rgba(brand, α)` fills/shadows and the general component-scoped dark overrides recorded in `gaps.md` G2 with rationale.
- [x] AC-5: `components/_index.json` (16 entries) and per-primitive `spec.json` (full identity + behavioral schema) populated with props/variants/states/token-bindings/a11y; real extracted functions recorded as extracted-from-usage, unified-from-convention abstractions recorded in `proposed-additions.md`.
- [x] AC-6: The duplicate (dead, shadowed) `_graphEdgeLineOpacity` definition was removed; the surviving higher-contrast definition (the one actually in effect at the call site via hoisting) is confirmed intended.
- [x] AC-7: Visual parity demonstrated pre/post in light and dark for affected surfaces. **OPERATOR-CONFIRMED 2026-06-22** — the operator reviewed the running dashboard in both themes ("sidebar looks great", "looks good otherwise") and approved the affected surfaces plus the follow-on nav-shell refinements (dark-rail separation, theme-toggle sizing/placement, footer version/Live layout, dark nav-active highlight) across several review rounds. Self-verification (node --check + served-asset 200 smoke + structural equivalence) also complete.
- [x] AC-8: All framework edits done under `framework_edit_allowed`; framework tests pass bytecode-free (3347, unchanged); `wave_validate` clean (docs-lint: ok) for contract files.

## Tasks

- [x] Open `framework_edit_allowed` gate.
- [x] Scaffold the primitive module (`ds/wfds.js`) exposing a `window.WFDS` global; esbuild-bundlable factory (no build step for the dashboard per locked decision).
- [x] Extract primitives (Icon glyphs, ThemeToggle, Badge/Pill/Chip, ProgressBar/Sparkline, Card/Dialog/Table, FileTree/DiffView/EmptyState/SectionLabel/NavSidebar/Prose); wired `dashboard.html` to load `/ds/wfds.js` before `/dashboard.js`.
- [x] Define `--text/--border/--surface/--surface-raised` in `dashboard.css`; grep-verified no dangling token-family refs.
- [x] Tokenize Aceiss palette + agent-role category colors (light + dark, exact hex); remaining rgba/component one-offs recorded in gaps.md G2.
- [x] Refactor `dashboard.js` to consume the module; removed inlined duplicates (ProgressRow/Sidebar kept as thin delegators — ProgressRow signature preserved for the pinned test).
- [x] Remove duplicate `_graphEdgeLineOpacity` (dead shadowed copy).
- [x] Populate `components/_index.json` + 16 `spec.json`; `proposed-additions.md` for unified-from-convention abstractions.
- [~] Visual-parity check (light + dark) on affected surfaces — **deferred to operator** (AC-7 pending; self-check via node --check + 200 smoke + structural equivalence done).
- [x] Run framework tests (3347, green, bytecode-free); gate close pending end-of-session.
- [x] Nav-shell visual refinements (operator-directed, post-parity review): dark-mode sidebar separation (elevated rail surface + brighter border — the rail no longer reads as flat black); moved the theme toggle from the footer to the top-right of the project title when expanded (drops to the footer when collapsed so it stays reachable); footer meta now shows version on the left + `Live`/refresh on the right; version displays `major.minor` with the full build in the tooltip.

## Agent Execution Graph


| Workstream         | Owner       | Depends On                | Notes                                                       |
| ------------------ | ----------- | ------------------------- | ---------------------------------------------------------- |
| module-scaffold    | implementer | —                         | `ds/` module + esbuild global                              |
| css-tokenization   | implementer | `1p6z6` tokens            | define missing family; tokenize palettes; dark via tokens  |
| primitive-extract  | implementer | module-scaffold, css      | incremental per-primitive extraction + render check        |
| dashboard-refactor | implementer | primitive-extract         | consume module; remove inlined copies; bug fix             |
| contract-specs     | implementer | primitive-extract         | `components/_index.json` + `spec.json`                      |
| parity-verify      | reviewer    | dashboard-refactor        | visual parity light + dark                                  |
| review             | reviewer    | all above                 | framework-code + docs-contract lanes                       |


## Serialization Points

- `dashboard.css` and `dashboard.js` are single large shared files — extraction and CSS tokenization must coordinate edits to avoid clobbering (sequence: CSS token-var definitions land before JS refactor consumes them).
- `gaps.md` (owned by `1p6z6-enh`) is resolved here; coordinate so closed gaps are marked, not deleted.
- `components/_index.json` shape must match what the follow-on claude.ai/design sync expects to consume.

## Affected Architecture Docs

- **Update:** `docs/architecture/design-system.md` — add a "primitive module" subsection describing where the extractable component module lives under `.wavefoundry/framework/dashboard/`, how the dashboard consumes it, and how it relates to the `components/` contract surface. Crosses a module boundary (introduces a consumed shared module + build), so an architecture-doc update is required. Confirm exact scope at Prepare.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The exportable primitive module is the deliverable. |
| AC-2 | required  | The dashboard must consume the module with no behavioral/visual regression. |
| AC-3 | required  | Defines the referenced-but-undefined `--text/--border/--surface` family (latent rendering bug). |
| AC-4 | important | Tokenize the brand + agent-role palettes and route dark overrides where feasible; remainder recorded as gaps. |
| AC-5 | important | Component contract specs (`_index.json` + `spec.json`) — supporting documentation of the module. |
| AC-6 | required  | Removes a real duplicate-`_graphEdgeLineOpacity` definition (dead-code bug). |
| AC-7 | required  | Visual-parity (light + dark) is the no-regression guard for this large refactor. |
| AC-8 | required  | `framework_edit_allowed` gate + bytecode-free framework tests + clean validation. |


## Progress Log


| Date       | Update                                                                 | Evidence                          |
| ---------- | --------------------------------------------------------------------- | --------------------------------- |
| 2026-06-20 | Plan created — abstract dashboard reusable layer into a token-bound module | Operator direction; repo analysis |
| 2026-06-22 | Implemented. Created `ds/wfds.js` (no-build `window.WFDS` global, esbuild-bundlable factory) with 16 primitives; wired `dashboard.html` to load it before `dashboard.js`; refactored `dashboard.js` to consume WFDS and removed all inlined copies (ProgressRow/Sidebar kept as thin delegators to preserve the pinned ProgressRow test signature). Defined the `--text/--border/--surface/--surface-raised` family (AC-3); tokenized the Aceiss brand palette + 8 agent-role category colors light+dark with exact hex (AC-4); populated `components/_index.json` + 16 `spec.json` + `proposed-additions.md` (AC-5); removed the dead duplicate `_graphEdgeLineOpacity` (AC-6); updated architecture `design-system.md` and `gaps.md` (G1 resolved, G2 partially resolved, G3/G4 decisions). Verified: `node --check` (both files), full framework suite 3347 green bytecode-free (unchanged), `wave_validate` clean, served-asset 200 smoke on `/dashboard.html` `/dashboard.js` `/dashboard.css` `/ds/wfds.js`, grep-verified no dangling token-family `var(--…)`. **AC-7 (light+dark visual parity) pending operator visual check** — not self-verifiable; screenshots flaky here. Set to `implemented`. | `node --check`; `run_tests.py` (3347 OK); `wave_validate` (docs-lint: ok); urllib 200 smoke |
| 2026-06-22 | Delivery review (operator-directed) — tokenized the dark-rail surface instead of leaving it hardcoded: added `--rail-surface`/`--rail-border` to `dashboard.css` `:root` (light = panel) + the dark token block (`#1b1e23`/`#2f3744`), `.sidebar` consumes the vars (dropped the one-off `html[data-theme="dark"] .sidebar` override); extended the DTCG contract (`color.rail.*` primitives, `modes/{light,dark}` overrides, `color.surface.rail`/`railBorder` semantics); regenerated exports via `bin/build-tokens` (`--ds-color-surface-rail` carries the dark override); `gaps.md` G2 marked RESOLVED. Verified: suite 3347 green, `wave_validate` clean, served CSS markers confirmed. | `dashboard.css`; `tokens/*.json`; `exports/*`; `run_tests.py`; `wave_validate` |
| 2026-06-22 | Operator-directed nav-shell polish during the visual-parity review (`NavSidebar` in `ds/wfds.js` + `dashboard.css`): (1) dark-mode sidebar separation — the rail bg `--panel-bg #151719` was nearly identical to content `--page-bg #111214`, so it read as flat black; gave the dark rail an elevated `#1b1e23` surface + brighter `#2f3744` border (knowingly hardcoded — candidate to tokenize as a rail surface); (2) moved `ThemeToggle` from the footer to a new `.sidebar-brand-row` at the top-right of the project title when expanded (drops to the footer centered when collapsed so it stays reachable); (3) footer `.sidebar-footer-meta` is now `space-between` with version on the left + `Live`/refresh on the right; (4) version shows `v{major.minor}` with the full build in the `title` tooltip. Verified: `node --check` both files, suite 3347 green bytecode-free, served markers live on `:8821`. | `node --check`; `run_tests.py` (3347 OK); urllib served-marker smoke |


## Decision Log


| Date       | Decision                                                                                       | Reason                                                                                                                                                | Alternatives                                                                                                                                              |
| ---------- | --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-06-20 | **Divergent pre-plan — selected: single shared primitive module consumed by the dashboard**    | Only option that yields a real maintained library AND aligns with the arch rule that dashboard assets align with the DS surface rather than accrete in isolation; visual-parity tests + incremental per-primitive extraction guard regressions. | (B) Parallel library duplicating component code for the sync → two sources of truth, drift — the exact anti-pattern the arch doc forbids. (C) Mechanical build-time slicing of `dashboard.js` at sync time → fragile, throwaway, no maintained library. |
| 2026-06-20 | Extract only the reusable layer; leave `GraphPanel`/`Dashboard`/`App` app-coupled              | Those depend on fetch/SSE/ELK/history and are integration roots, not primitives; abstracting them is high-risk, low-reuse this wave.                  | Extract all ~45 components → much larger blast radius, many won't render standalone, low reuse value.                                                     |
| 2026-06-20 | CSS token-var definitions land before the JS refactor consumes them                            | Avoids dangling `var()` refs and clobbering on the two large shared files.                                                                           | Interleave freely → higher chance of broken intermediate states on a 4,800-line file.                                                                    |


## Risks


| Risk                                                            | Mitigation                                                                          |
| ------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Refactoring a 4,825-line monolith introduces visual regressions | Incremental per-primitive extraction with a render check each step; pre/post parity |
| Tokenizing dark hex overrides changes rendered colors          | Tokenize to the exact current values first; visual parity gate catches drift        |
| Module/global shape mismatches what the sync later needs       | Coordinate `components/_index.json` + global naming with the follow-on sync wave    |
| Framework-asset edits bypass the gate                          | `framework_edit_allowed` opened/closed around all `.wavefoundry/framework/` edits   |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
