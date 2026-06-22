# Dashboard Primitive Abstraction + Token Consumption

Change ID: `1p72v-ref dashboard-primitive-abstraction`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-20
Wave: `1p6xb design-system-foundation`

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

- [ ] AC-1: A primitive module exists under `.wavefoundry/framework/dashboard/`, exports the ~16 named primitives, and builds via esbuild exposing them on a global.
- [ ] AC-2: `dashboard.js` consumes the shared primitives (no duplicated inline copies of the abstracted components remain) and the dashboard renders with no behavioral regression.
- [ ] AC-3: The `--text/--border/--surface/--surface-raised` family is defined in `dashboard.css`; no dangling `var(--…)` references remain (grep-verified).
- [ ] AC-4: The "Aceiss" brand palette and agent-role category colors are tokenized; per-component dark hex overrides route through tokens where feasible; remaining cases recorded as gaps with rationale.
- [ ] AC-5: `components/_index.json` and per-primitive `spec.json` are populated (props, variants, states, token bindings, a11y); net-new abstractions recorded appropriately.
- [ ] AC-6: The duplicate `_graphEdgeLineOpacity` definition is removed; surviving behavior confirmed intended.
- [ ] AC-7: Visual parity demonstrated pre/post in light and dark for affected surfaces.
- [ ] AC-8: All framework edits done under `framework_edit_allowed`; framework tests pass bytecode-free; `docs-lint`/`wave_validate` clean for contract files.

## Tasks

- [ ] Open `framework_edit_allowed` gate.
- [ ] Scaffold the primitive module (`ds/`) + esbuild build exposing a global.
- [ ] Extract primitives incrementally (icons → Badge/Pill/Chip → ProgressBar/Sparkline → Card/Dialog/Table → FileTree/DiffView/EmptyState/SectionLabel/NavSidebar/Prose), verifying render per step.
- [ ] Define `--text/--border/--surface/--surface-raised` in `dashboard.css`; grep for dangling refs.
- [ ] Tokenize Aceiss palette + agent-role category colors; route dark overrides through tokens where feasible.
- [ ] Refactor `dashboard.js` to consume the module; remove inlined duplicates.
- [ ] Remove duplicate `_graphEdgeLineOpacity`.
- [ ] Populate `components/_index.json` + `spec.json`; `proposed-additions.md` for net-new.
- [ ] Visual-parity check (light + dark) on affected surfaces.
- [ ] Run framework tests; close `framework_edit_allowed` gate.

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

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required / important / nice-to-have / not-this-scope |           |


## Progress Log


| Date       | Update                                                                 | Evidence                          |
| ---------- | --------------------------------------------------------------------- | --------------------------------- |
| 2026-06-20 | Plan created — abstract dashboard reusable layer into a token-bound module | Operator direction; repo analysis |


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
