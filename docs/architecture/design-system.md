# Design System Architecture

Owner: Engineering
Status: active
Last verified: 2026-06-22

Hub doc for the design-system extraction contract seeded under `docs/design-system/`. Explains the extraction philosophy, where each artifact type lives, what is regeneratable versus operator-owned, and how the semantic index relates to the design surface.

## Extraction Philosophy

The design system extraction contract follows a single governing rule: **extract, don't invent.** When source evidence is absent, the framework records `null` and a matching `gaps.md` entry rather than silently defaulting to a value. This makes every design decision auditable and prevents agents from drifting from the actual evidence.

For the local dashboard feature, the design-system surface is also the governance home for the dashboard's small shared UI contract: shell layout, typography, spacing, status-color semantics, card/table structure, and loading/empty/error states. The dashboard may ship browser assets under `.wavefoundry/framework/dashboard/`, but those assets should still align with the checked-in design-system narrative and token surfaces rather than accreting ad hoc styling rules in isolation.

Two artifact classes coexist under `docs/design-system/` and must never be conflated:

| Artifact class | Owner | Examples | Regeneratable? |
|---|---|---|---|
| **Machine-readable extraction contract** | Framework (via seed) | `manifest.json`, `tokens/*.json`, `components/*/spec.json`, `gaps.md`, `source-map.json` | Yes — seeded structure; values populated from extraction evidence |
| **Operator-owned narrative** | Engineering team | `design-language.md`, `index.md` body | No — manual authoring; never overwritten by extraction |

Extraction may only cross the boundary in two idempotent ways: append a cross-link row to `index.md`, and add a "See extracted contract" pointer at the top of `design-language.md`. Both operations must not repeat if already present.

## Three Modes: Bootstrap, Extract-Mirror, Adopt (wave `1p799`)

The contract supports three modes plus an ambiguity escape hatch, selected from `docs/repo-profile.json` `design_system.mode` (set by `seed-030` from the deterministic `classify_design_system_mode(design_evidence)` classifier in `design_system_governance_validators.py` — code-derived and unit-tested, not agent judgment):

| Mode | When | What is emitted |
|---|---|---|
| **bootstrap** | No design system found (no evidence) | The nulls skeleton — the no-design-system path. |
| **extract-mirror** | In-repo design *evidence* (CSS custom properties, stylesheet tokens, in-repo theme files) but **no** maintained external system with its own build | The full DTCG extraction tree under `docs/design-system/` (the original behavior). |
| **adopt / `external-reference`** | A **declared source of truth with its own build** — a published/packaged token package, a Style-Dictionary/DTCG source dir + build, or Figma library links | A **thin reference index** that points at the existing system; no parallel mirror. |
| **ambiguous** | Genuinely weak / mixed signals | Install/upgrade asks the operator — never silently adopt or mirror. |

### The evidence boundary

The boundary between **extract-mirror** and **adopt** is the load-bearing decision. Adopt requires a *declared external source of truth with its own build* — CSS custom properties, a stray `tailwind.config`, or in-repo theme files do **not** qualify; they are in-repo evidence and route to extract-mirror. This prevents a stray Tailwind config from being read as a maintained system. When signals are weak or mixed (something detected but no concrete in-repo evidence and no external source-of-truth), the verdict is `ambiguous` and the seeds ask the operator.

### Adopt-in-place philosophy

The framework is strong at **bootstrapping** a system that does not exist. Adopt-in-place makes it equally able to **defer to** one that does. Under `external-reference` the contract *indexes* the existing system — it does not convert (importing the external tokens into our DTCG tree would re-introduce the exact parallel-mirror drift this mode removes). The thin reference index is:

- `manifest.json` — with a required `externalReference` block (`tokenSource`, optional `buildCommand`, `namingConvention`/`varPrefix`, `consumptionDoc`, `notes`).
- `source-map.json` — entries of `sourceType: "external"` pointing at `externalReference.tokenSource`.
- `AGENTS.md` — consumption guidance **derived from** `externalReference` (the project's real `varPrefix`/`consumptionDoc`), never the `--ds-*` namespace and never a prescribed mechanism.
- `gaps.md`, `README.md`.

`tokens/` and `exports/` are **declined** (not an error) — but only when a **resolvable** `externalReference.tokenSource` is present: a path must exist in the repo, a URI must be well-formed. An unresolvable/absent pointer keeps the full requirement set so `external-reference` cannot silence a genuinely-missing token tree.

**`canonicalRoot` stays fixed** at `docs/design-system` for all modes. It names *where the contract/index lives* — consumers (the validator, the `AGENTS.md` docs-map pointer, the semantic index) rely on it. The external source location is expressed *only* via `externalReference.tokenSource`; `canonicalRoot` is never relaxed to name the external root.

**`hybrid` vs `external-reference`:** `external-reference` is the pure-adopt case (point-only, thin tree). `hybrid` is adopt-plus-extract — when a project adopts an external source for most of its system but also has in-repo evidence the framework extracts, record `sourceStrategy: "hybrid"`, list all active sources in `evidenceTypes`, and both the extracted tree and an `externalReference` pointer may be present.

### Upgrade-stability guarantee

Upgrade (`seed-160`) **never converts an adopted reference back into a mirror.** It reads the existing `manifest.json` `sourceStrategy` first; when it is `external-reference`, the upgrade backfills only the thin reference index, never creates `tokens/`/`exports/` or the token-build pipeline, never treats their absence as a gap, and never changes `sourceStrategy`.

**Extract→adopt migration** is operator-initiated only. Migrating an existing extract-mirror project to `external-reference` moves the orphaned `tokens/` (and other extracted subtrees) to `docs/design-system/.backup/<ISO-date>/` with a `meta`-category `gaps.md` entry — never a silent delete. Auto-migrating a mirror to adopt is out of scope.

### Self-hosting note

Wavefoundry's own dashboard design system stays **extract-mirror**, never adopt. Its only design evidence is an in-repo `dashboard.css` (no external token package, no Style-Dictionary build, no Figma library links), which is in-repo evidence — below the adopt bar. The classifier is unit-tested with a Wavefoundry-shaped fixture asserting this verdict (the self-hosting guard).

## Dashboard Primitive Module (WFDS)

Wave `1p75h` / change `1p72v-ref` extracted the dashboard's reusable UI layer
into a maintained primitive module so the dashboard's own code and the future
claude.ai/design sync can consume it as a library rather than re-deriving it from
the monolith.

**Where it lives.** `.wavefoundry/framework/dashboard/ds/wfds.js` — plain,
no-build JavaScript. It defines the primitives inside a `defineWFDS(React)`
factory and attaches the result to `window.WFDS`.

**How the dashboard consumes it (no-build script-tag global).** `dashboard.html`
loads `/ds/wfds.js` via a `<script>` tag **before** `/dashboard.js`. The module
is UMD-React-compatible: it reads the same `React` UMD global the dashboard uses
and aliases `createElement` to `h`, so no bundler or build step is introduced to
run the dashboard. `dashboard.js` consumes the primitives from `window.WFDS`
(destructuring the subset it references directly; the rest via `WFDS.*` or thin
local delegators — e.g. `ProgressRow → WFDS.ProgressBar`, `Sidebar →
WFDS.NavSidebar`). The dashboard server serves `/ds/wfds.js` through the same
static-asset path that serves `dashboard.js`/`dashboard.css` (path-traversal
guarded by `is_relative_to`).

**esbuild bundlability (for downstream sync; not required for the dashboard).**
The module body is a single `defineWFDS(React)` factory referencing React only
through the injected parameter, so a downstream sync can esbuild-bundle the file
(wrap as an ESM/IIFE entry that calls `defineWFDS(React)` and re-exports) without
touching the dashboard. **No build dependency or build step is added here** — the
dashboard runs purely from the script-tag global.

**Relationship to the `components/` contract.** Each primitive on `window.WFDS`
has a contract entry under `docs/design-system/components/` (an `_index.json`
entry + a per-primitive `spec.json` recording props, variants, states, token
bindings, and accessibility). The real extracted functions (Icon, ThemeToggle,
ProgressBar, Sparkline, Dialog, FileTree, DiffView, NavSidebar, Prose) are
recorded as stable / extracted-from-usage. The unified-from-convention
abstractions (Badge, Pill, Chip, Card, Table, EmptyState, SectionLabel) are
implemented in the module and tracked in `proposed-additions.md` pending full
call-site adoption. Primitive styling binds to the semantic tokens (the
`--text` / `--border` / `--surface` family is now defined; the agent-role brand
palette and agent-role category colors are tokenized — see `gaps.md` G1/G2).

## Where `design-language.md` Fits

`docs/design-system/design-language.md` is seeded by `seed-040` task 13. It is the narrative design document: intent, rationale, and explicit departures from reference conventions. It is written and maintained by the engineering team, not regenerated by the framework.

`docs/design-system/DESIGN.md` is the agent-optimized distillation in Google Labs DESIGN.md format. It is generated from the extraction contract (under 400 lines, YAML front-matter holds token references, markdown body holds distilled rationale). `DESIGN.md` is regeneratable; `design-language.md` is not.

## When Extraction Regenerates vs Operator Edits

**Regeneration** applies to the machine-readable contract tree: JSON token files, `manifest.json`, `components/*/spec.json`, `gaps.md`, `source-map.json`, `DESIGN.md`. Regeneration is triggered by the install and upgrade lifecycle (see `seed-010` step 8 and `seed-160` upgrade backfill). Regeneration is always merge-safe: it creates missing paths and never overwrites existing files.

**Operator edits** apply to narrative docs (`design-language.md`, `index.md` body, `foundations/*.md`, `accessibility/README.md`). These are checked in as authored text and are not touched by regeneration.

The clean re-extraction path (when a full extraction refresh is needed):

1. Move the existing `docs/design-system/<subtree>` to a timestamped backup: `docs/design-system/.backup/<ISO-date>/`.
2. Regenerate using the install/upgrade seed contract.
3. Diff against the backup and review operator-authored content before discarding the backup.
4. Record a `meta`-category entry in `gaps.md` when a backup is created.

Never auto-delete operator artifacts without the backup step. The `.backup/` directory should be gitignored or cleaned up manually after review.

## Relationship Between `docs/design-system/` and the Semantic Index

`docs/design-system/**/*.json` files are routed through the doc-chunker branch in `chunker.py` so they produce `doc`-kind chunks and are discoverable via `docs_search` on a docs-only index build. This means token files, `manifest.json`, `components/_index.json`, and `spec.json` files appear in semantic search results alongside markdown docs.

Non-JSON design files (`.md`) are already indexed as doc chunks through the standard markdown path.

The chunker falls back to line-window chunking for malformed JSON so a broken token file cannot crash the indexer.

## Backup Directory Cleanup

`.backup/` directories under `docs/design-system/` grow unbounded if not cleaned up. Recommended practice:

- After reviewing a backup diff and deciding the new extraction is correct, delete the backup directory.
- Do not gitignore the entire `.backup/` directory tree — back up to a working branch or external copy first if the backup contains operator-authored content that may not be in the new extraction.
- `gaps.md` `meta`-category entries for backups serve as the audit trail even after the directory is removed.

## Core Tree

See `seed-040` task 14 for the full required-path list. The top-level shape:

```
docs/design-system/
├── README.md
├── DESIGN.md                 # agent-optimized distillation (regeneratable)
├── AGENTS.md                 # agent contract for this subtree
├── manifest.json
├── VALIDATION.md
├── gaps.md
├── tokens/
│   ├── primitives.tokens.json
│   ├── semantic.tokens.json
│   ├── components.tokens.json  (optional)
│   ├── modes/
│   │   ├── light.tokens.json
│   │   └── dark.tokens.json
│   └── README.md
├── exports/
│   ├── README.md             # explains each subdir; links to token-build pipeline
│   ├── css/
│   ├── tailwind/
│   ├── ts/
│   └── json/
├── components/
│   └── _index.json
├── foundations/
│   └── (color, typography, spacing, radius, elevation, motion)
├── accessibility/
└── docs/design-system/
    ├── version.json
    ├── source-map.json
    └── proposed-additions.md
```

Generating token-build outputs (`exports/css/`, `exports/tailwind/`, etc.) is implemented by wave `12atj-feat design-token-build-pipeline` (see **Token Build Pipeline** below).

## Token Build Pipeline

Wave `12atj-feat design-token-build-pipeline` turns the DTCG token source under `tokens/` into framework-specific outputs under `exports/`. The contract is tool-agnostic:

- **`build.config.json`** declares `tool` (`style-dictionary` | `token-pipeline` | `custom` | `builtin`), `version`, and `targets[]` of `{format, outputDir, options}`. When `tool: "custom"`, a `command` field holds the shell invocation. The seed-emitted default stub is `style-dictionary` + the four standard targets (css/tailwind/ts/json).
- **`bin/build-tokens`** reads the config and dispatches to the configured tool. It exits non-zero with actionable messages on a missing dependency or a broken token reference at build time. A bundled pure-Python transform (`tool: "builtin"`, ships at `.wavefoundry/framework/scripts/design_token_build.py`) generates all four outputs with no Node dependency.

**How `exports/` is generated.** The transform flattens the DTCG trees, resolves `{alias}` references against `primitives.tokens.json`, and emits: CSS custom properties (light base + `@media (prefers-color-scheme: dark)` / `[data-theme="dark"]` override block), a Tailwind `theme.extend` config (with `theme.extendDark` dark variants), typed TypeScript constants (`tokens` plus per-mode `tokensByMode`), and a flat resolved JSON map. Output is sorted by token path and carries a `/* generated — do not edit directly */` header, so re-running on an unchanged source is byte-identical (idempotent + diff-friendly).

**When to re-run.** After editing any `tokens/*.json` source file, run `docs/design-system/bin/build-tokens`.

**Stale detection.** After a successful build, `manifest.json` `validationSummary` records `exportsGenerated`, `exportsAt` (ISO-8601), and `exportsStale` (true when the token source is newer than the exports, or when no exports exist). The design-system lint validator warns when `exportsStale` is `true`.

## Pattern and Surface Depth (Split B)

Wave `12arn-enh design-system-pattern-and-surface-depth` adds the following layers on top of the core contract:

- **`patterns/`** — navigation, feedback, data, trust pattern groups (`_index.json` + `README.md` per group; per-pattern subdirs optional).
- **`state-patterns/`** — loading, empty, error, success with `_index.json` + `README.md` per state.
- **`validation-patterns/`** — required-field, format-validation, async-validation, error-display, success-confirmation.
- **`content/`** — voice, microcopy, formatting, i18n, rtl-layout, locale-formats, brand-legal.
- **Extended `foundations/`** — shell, density, responsive, grid, z-index, iconography, data-visualization, media-motion.
- **Extended `accessibility/`** — focus, keyboard, screen-reader.
- **Extended tokens** — `borders.tokens.json`, `focus.tokens.json`, `z-index.tokens.json`, `motion.tokens.json`.
- **Asset contract** — `icons/`, `illustrations/`, `logos/`, `images/` with dedup and integrity rules.
- **`skills/`** — nine SKILL.md files for agent-facing design system tasks.
- **`spec.json` behavioral fields** — `states`, `responsive`, `motion`, `accessibility`, `content` are populated (not added) from source evidence; fields emitted as `null` by the core seed and filled additively by Split B.

Split B also adds semantic validators (`design_system_surface_validators.py`): WCAG contrast from `contrast-report.json`, extended mode parity, reduced-motion check, icon sanity, keyboard pattern presence, and state coverage.

## Bootstrap and Governance (Split C)

Wave `12arn-enh design-system-bootstrap-and-governance` adds governance and multi-surface tracking:

- **No-design-system bootstrap path.** When no formal design system source is found, substitute evidence (screenshots, reference URLs, brand PDFs) is collected and the skeleton is emitted with all semantic files as explicit `null`. Non-normative proposals land in `gaps.md` tagged `proposed-from-best-practices` — never in `semantic.tokens.json` until explicit operator promotion.
- **`sourceStrategy` full semantics.** `figma-extract`, `repo-evidence-only`, `visual-bootstrap`, `hybrid`, `external-reference` (adopt-in-place — see **Three Modes** above).
- **`targetSurfaces` + `platformStandards[]`.** Multi-surface recording with per-surface `standard`, `referenceVersion` (for HIG drift tracking), and `departures`. Unknown surfaces → gaps.
- **Per-surface deltas.** `platforms/` subtree holds narrative + token overrides per surface; `manifest.json.platformStandards[].overrides` is the machine index pointer.
- **Deprecation/lineage.** `manifest.json.deprecations` and `components/_index.json` `deprecated`/`supersedes`/`sunset` fields.
- **Conditional product-class extensions.** Email, print/PDF, offline-first, and notification-heavy subtrees under `patterns/` — seeded only when inventory signals the product class.

Split C adds governance validators (`design_system_governance_validators.py`): `sourceStrategy` enum (incl. `external-reference`), `targetSurfaces` non-empty, `platformStandards[].referenceVersion` presence, visual-bootstrap proposal guard, deprecated component `supersededBy`/`sunset` requirement, overrides path existence. The module also exposes the pure, tested `classify_design_system_mode(design_evidence)` helper (wave `1p799`). The surface/manifest validator (`design_system_validators.py`) accepts the thin tree under `external-reference`, requires the `externalReference` block, rejects an unresolvable `tokenSource`, and keeps the `canonicalRoot` invariant across all modes.

## Cross-Links

- `docs/design-system/` — extraction contract root
- `docs/design-system/design-language.md` — operator-owned narrative
- `docs/design-system/AGENTS.md` — agent rules for the design subtree
- `docs/ARCHITECTURE.md` — architecture hub
- `seed-040` task 14 — extraction contract spec and required paths
- `seed-010` step 8 — install backfill checklist
- `seed-160` upgrade backfill — schema-version reconciliation and merge-safe backfill
- `docs/plans/12atj-feat design-token-build-pipeline.md` — follow-on token-build pipeline plan
