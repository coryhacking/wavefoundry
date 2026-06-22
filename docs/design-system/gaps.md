# Design System Gaps

Owner: Engineering
Status: active
Last verified: 2026-06-22

Recorded during the `1p6z6-enh` token-extraction pass from `.wavefoundry/framework/dashboard/dashboard.css`. Each CSS-code gap below is scoped to **`1p72v-ref`** (design-system primitive abstraction refactor), which owns all stylesheet/code edits. This change is `docs/design-system/`-only and does **not** fix them here.

## Summary

- Critical: 1
- Important: 2
- Nice-to-have: 1

## Critical

### G1 — Undefined-but-referenced token family `--text` / `--border` / `--surface` / `--surface-raised`  ·  scope: `1p72v-ref`  ·  **RESOLVED (1p72v-ref)**

`dashboard.css` referenced CSS custom properties that were **never defined** in any `:root` or `html[data-theme]` block:

- `var(--border)` — referenced at lines 787, 1899, 1994, 2019, 2713, 3607, 3616, 3643, 3670 (and more).
- `var(--text)` — referenced at lines 3588, 3608, 3617, 3624, 3629.
- `var(--surface)` / `var(--surface-raised)` — referenced at lines 784, 3642, 3675 (`var(--surface-raised, var(--surface))`).

These resolved to nothing (or to the `var(..., fallback)` second arg where one exists), so the affected rules silently rendered with no color/border or an inherited value.

**Resolution:** `1p72v-ref` defined the family in `:root` as aliases to the canonical tokens — `--surface: var(--panel-bg)`, `--surface-raised: var(--neutral-soft)`, `--border: var(--panel-border)`, `--text: var(--ink)`. Aliasing (rather than new primitives) means the family re-themes automatically in dark mode (the aliased tokens carry dark overrides) and the doc-dialog code/pre/table surfaces now resolve to the same values the sibling agent-dialog surfaces already use. Grep-verified: no `var(--…)` reference is undefined except the deliberately inline-set `--kind-bg` / `--kind-color` per-element props, which always carry a `var(…, fallback)`.

## Important

### G2 — Hardcoded agent-role brand palette + per-component hardcoded-hex dark overrides bypass tokens  ·  scope: `1p72v-ref`  ·  **PARTIALLY RESOLVED (1p72v-ref)**

The lifecycle-stage brand palette was committed as inline hex comments / values, not tokens:

- `dashboard.css` lines 2335–2387: Build `#FF9100`, Review `#4844C5`, Coordinate `#40A3E9`, Operate `#D7271E`, Specialist `#53AC04` (labelled by color name).
- The `html[data-theme="dark"]` section (lines ~3125 onward) contains roughly 120 per-component rules that hardcode hex values rather than re-theme through tokens — e.g. `.hero-card { background: #212428; border-color: #30353c }`, framework-process step/flow-card palettes, `#4ade80` / `#f87171` diff colors, `--checkpoint-accent` stage tints (`#b8b5f0`, `#f3b26d`, `#a5d46a`, `#c5b3ff`, `#b0bec5`), etc.

**Resolution (brand palette + agent-role category colors — done):** `1p72v-ref` tokenized the full agent-role brand palette and all eight agent-role category colors. `:root` now defines a theme-invariant brand accent per category (`--agent-build` … `--agent-persona`) plus per-category light tint tokens (`-border`, `-text`, `-hover-border`, `-hover-text`, `-label`); `html[data-theme="dark"]` redefines the tint tokens with the exact prior dark hex. Every `.hero-agent-pill--*` / `.hero-agent-label--*` rule (light + dark, pill + hover + label) now consumes these tokens. Values are byte-for-byte the prior hardcoded hex — no color drift. The brand accents are also routed through the `color-mix()` hover bases.

**Remaining (recorded, not resolved — the "where feasible" boundary):**

- The per-category `rgba(brand, 0.07 / 0.12 / 0.18 / 0.20)` background fills and box-shadows stay as literal `rgba()`: there is no clean drift-free way to express an exact `rgba` of a brand color at an arbitrary alpha through a CSS custom property without `color-mix`/`rgb(from …)` rewrites that would risk subtle rounding drift on this no-regression refactor. They remain literal, scoped to the brand-color RGB.
- The remaining general per-component dark overrides (e.g. `.hero-card` surface hexes, framework-process step/flow-card palettes, the `#4ade80`/`#f87171` diff colors, `--checkpoint-accent` stage tints) are **component-scoped one-offs**, not part of the brand/agent-role palette or the global `:root` vocabulary. Tokenizing them would mint many single-use tokens with no reuse value and increase drift risk on a 3,800-line stylesheet. Left as recorded dark overrides; revisit only if a reusable semantic role emerges (e.g. a shared `--diff-added` / `--diff-removed` pair, or a `--checkpoint-accent` semantic family).
- **Dark-mode sidebar rail surface (operator-directed nav polish, 1p72v-ref) — RESOLVED:** the rail needs an elevated dark surface so it separates from the near-identical content bg (`--page-bg #111214`). Rather than hardcode the hex in the rule, it was tokenized: `--rail-surface` / `--rail-border` are defined in `:root` (light = `var(--panel-bg)` / `var(--panel-border)`) and redefined in the `html[data-theme="dark"]` token block (`#1b1e23` / `#2f3744`); `.sidebar` consumes the vars. The DTCG contract mirrors this — `color.rail.surface` / `color.rail.border` primitives, `modes/{light,dark}` overrides, and `color.surface.rail` / `color.surface.railBorder` semantics — and the exports were regenerated (`--ds-color-surface-rail` carries the dark override).

### G3 — Layout / branding tokens absent from the prior `12as1` extraction contract  ·  scope: `1p72v-ref`

The following custom properties are fully defined in `dashboard.css` `:root` but were absent from the prior (empty) extraction contract. They are now extracted as `primitive-only` tokens (`layout.*`, `color.footer.accent`) but carry no semantic role yet:

- `--footer-accent` (L10) → `color.footer.accent` — branding accent; light `#2B6CB0`, dark `#7FB2F0`.
- `--rail-w` (L35) → `layout.rail.w` (`56px`).
- `--view-max` (L36) → `layout.view.max` (`1760px`).
- `--view-max-wide` (L37) → `layout.view.maxwide` (`1760px`).

`1p72v-ref` should decide whether these get semantic roles or stay primitive-only layout constants.

**Decision (1p72v-ref):** keep them **primitive-only** layout/branding constants. `--rail-w`, `--view-max`, `--view-max-wide` are single-use shell-layout dimensions with no reuse beyond the sidebar/view-width chrome (already marked `primitive-only` in `primitives.tokens.json`); promoting them to semantic roles would add vocabulary without consumers. `--footer-accent` (`color.footer.accent`) already has a semantic alias (`color.accent.footer` in `semantic.tokens.json`) and stays a branding accent. No source change required.

## Nice-to-have

### G4 — `--header-h` named in plan but not present in source  ·  scope: `1p72v-ref`

AC-6 lists `--header-h` among the layout tokens to record. It is **neither defined nor referenced** anywhere in `dashboard.css` (the top header was removed in wave `1p6nl`). Recorded here as a no-op so the audit trail is explicit: there is no value to extract; `--footer-accent` / `--rail-w` / `--view-max` / `--view-max-wide` are the real layout tokens (see G3). No action required unless a header is reintroduced.

## Meta
