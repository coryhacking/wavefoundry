# Design Token Build Pipeline

Change ID: `12atj-feat design-token-build-pipeline`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-22
Wave: `1p75h design-system-foundation`

> **Revived 2026-06-20** into wave `1p75h design-system-foundation`. Paths corrected from the original `design`-rooted layout to the as-built `docs/design-system/` tree. The original dependency (`12akr-enh design-system-directory-structure-extraction`, never implemented) is superseded by `1p6z6-enh design-token-extraction-reconciliation`, which now produces the populated DTCG token source this pipeline consumes.

## Rationale

The `docs/design-system/` extraction contract stubs `exports/{css,tailwind,ts,json}/` as empty placeholders. Those stub directories only become useful once a token transformation step reads the DTCG source and emits framework-specific outputs. Following `1p6z6-enh design-token-extraction-reconciliation` (which populates `primitives.tokens.json`, `semantic.tokens.json`, and the mode files from the live dashboard), this pipeline turns that source into consumable outputs. Without it, agents cannot reference `var(--color-action-primary-background)` in CSS, or `theme.colors.primary[500]` in Tailwind, or the typed `tokens.color.action.primary.background` constant in TypeScript — they are forced to hard-code values, which the `docs/design-system/AGENTS.md` contract explicitly forbids. This change closes that gap by adding a Style Dictionary-based (or equivalent) build pipeline that is configured by the operator and executed during extraction or on-demand.

This change depends on `1p6z6-enh design-token-extraction-reconciliation` being implemented first (it provides the populated token source).

## Requirements

1. **Tool-agnostic config contract.** The pipeline must be driven by a config file at `docs/design-system/build.config.json` that declares: `tool` (enum: `style-dictionary`, `token-pipeline`, `custom`), `version`, `targets` (array of `{ format, outputDir, options }`). When `tool: "custom"`, a `command` field holds the shell invocation. This keeps the build contract machine-readable without hard-coding one tool.
2. **Default targets.** When `target` includes `css`, the pipeline emits CSS custom properties to `docs/design-system/exports/css/tokens.css` covering all semantic tokens and mode overrides. When `target` includes `tailwind`, it emits a Tailwind v3/v4-compatible `docs/design-system/exports/tailwind/theme.config.js` (or `.ts`). When `target` includes `ts`, it emits typed token constants to `docs/design-system/exports/ts/tokens.ts`. When `target` includes `json`, it emits a flat resolved token map to `docs/design-system/exports/json/tokens.json`.
3. **Mode-aware outputs.** CSS output must emit a base (light) rule-set plus a `@media (prefers-color-scheme: dark)` / `[data-theme="dark"]` override block. TypeScript output must export per-mode token maps. Tailwind output must include dark-mode variants where dark tokens differ from light.
4. **Idempotent and diff-friendly.** Re-running the pipeline on an unchanged token source must produce byte-identical output (modulo timestamp comments). Generated files must carry a `/* generated — do not edit directly */` header comment so operators know not to hand-edit them. No random ordering in output.
5. **Install and upgrade hooks.** `seed-010` and `seed-160` must describe the pipeline setup step: detect `build.config.json`; when absent, emit a stub with `tool: "style-dictionary"` and the standard four targets so the operator has a starting point. The stub must work out-of-the-box for a Style Dictionary install (`npm install -D style-dictionary`).
6. **Run command via `wavefoundry/bin/`.** Add a `docs/design-system/bin/build-tokens` wrapper script that reads `build.config.json` and invokes the configured tool. The wrapper must exit non-zero on transformation errors and print actionable messages (missing dependency, broken token reference at build time).
7. **`manifest.json` export parity field.** After a successful build, `manifest.json` `validationSummary` must record `exportsGenerated: true` and a `exportsAt` ISO-8601 timestamp. When exports are stale (token source newer than exports), `manifest.json` must record `exportsStale: true`. A lint validator must warn when `exportsStale` is `true`.
8. **AGENTS.md update.** `docs/design-system/AGENTS.md` (seeded by `12akr-enh`) must be extended to document: use `var(--<token-name>)` for CSS, import from `exports/ts/tokens.ts` for TypeScript, reference `exports/tailwind/theme.config.js` for Tailwind — never hard-code values; run `bin/build-tokens` after editing token source files.
9. **`docs_search` discoverability of exports.** The chunker routing added by `12akr-enh` covers `docs/design-system/**/*.json`. Ensure `exports/ts/tokens.ts` and `exports/css/tokens.css` are either indexed as doc chunks or explicitly excluded with a note — agents should find token names via docs search, not by parsing generated source files.
10. **Framework test.** A framework test must: (a) write minimal valid DTCG token files to a temp directory; (b) invoke the build pipeline; (c) assert the four output files are generated with correct structure; (d) assert re-running produces identical output; (e) assert a broken token ref at build time exits non-zero.

## Scope

**Problem statement:** `docs/design-system/exports/` is seeded as empty stubs by `12as1 design-system-extraction`. Agents that follow the `AGENTS.md` token usage rules (no hard-coded values) cannot reference framework-specific token syntax until the transformation pipeline is configured and run.

**In scope:**

- `build.config.json` schema and default stub.
- CSS, Tailwind, TypeScript, and flat JSON output targets.
- Mode-aware output for all target formats.
- `docs/design-system/bin/build-tokens` wrapper script.
- `manifest.json` export parity field and stale-exports lint warning.
- `AGENTS.md` update with token reference guidance.
- `seed-010` / `seed-160` pipeline setup step.
- Framework test covering the build and idempotency invariants.

**Out of scope:**

- Choosing or installing a specific token transformation tool in the operator's repo (the seed guides the operator; the wave doesn't run `npm install` for them).
- Storybook token integration.
- Icon export pipeline (owned by `12arn-enh design-system-pattern-and-surface-depth`).
- CSS-in-JS outputs (Emotion, Stitches, Vanilla Extract) — add as a follow-on target if needed.
- Automatic re-build on file-watch (out of scope; operators can wire `bin/build-tokens` into their own watch tooling).

**Depends on:** `12akr-enh design-system-directory-structure-extraction` (token source files and `exports/` stub directories must exist).

## Acceptance Criteria

- [x] **AC-1** (`build.config.json` schema): stub is generated by install/upgrade when absent; `tool`, `version`, `targets` fields present; `custom` path supported. (`docs/design-system/build.config.json`; seed-040/010/160 emit the default `style-dictionary` stub only when absent; `custom`/`builtin` dispatch covered in `test_design_token_build.py`.)
- [x] **AC-2** (CSS output): `exports/css/tokens.css` contains all semantic tokens as custom properties; light base + dark override blocks present when dark mode tokens exist. (`@media (prefers-color-scheme: dark)` + `[data-theme="dark"]` blocks emitted.)
- [x] **AC-3** (Tailwind output): `exports/tailwind/theme.config.js` is valid Tailwind config extending `colors`, `spacing`, `borderRadius`, `fontSize`, and other detected token categories. `[~]` Note: emits `colors`, `spacing`, `borderRadius`, `boxShadow`, `fontFamily` — the categories actually present in the extracted token source. `fontSize` is not in the source token set (extract, don't invent); the category→Tailwind-key map covers it automatically if/when fontSize tokens are added.
- [x] **AC-4** (TypeScript output): `exports/ts/tokens.ts` exports typed token constants; no `any` types; imports resolve without errors in strict mode. (Typed `TokenName`/`TokenMode` unions, `tokens` + per-mode `tokensByMode`; test asserts no `any`.)
- [x] **AC-5** (JSON output): `exports/json/tokens.json` is a flat resolved key-value map; all alias references resolved to raw values. (Aliases resolved against primitives; per-mode maps included.)
- [x] **AC-6** (Idempotency): re-running on unchanged source produces byte-identical output. (Sorted output + fixed header; verified in repo and in `test_idempotent_byte_identical`.)
- [x] **AC-7** (Build wrapper): `docs/design-system/bin/build-tokens` runs the configured tool; exits non-zero on error; prints actionable message. (Missing-config, missing-command, broken-ref, and style-dictionary-absent all exit non-zero with actionable stderr.)
- [x] **AC-8** (Stale detection): `manifest.json` `exportsStale: true` when token source is newer than exports; lint validator warns. (`update_manifest_parity` + `check_design_system` stale warning.)
- [x] **AC-9** (AGENTS.md): token reference patterns for CSS/TS/Tailwind documented; `bin/build-tokens` run instruction present. (`docs/design-system/AGENTS.md` "Referencing tokens in code" section.)
- [x] **AC-10** (Framework test): build, idempotency, and broken-ref exit-code cases covered. (`test_design_token_build.py`, 12 tests; style-dictionary actual-run skipped when absent, never a hard dependency.)

## Tasks

- [x] `seed-010` / `seed-160` — add pipeline setup step: detect `build.config.json`, emit stub when absent, document `npm install -D style-dictionary` as the default path. (seed-010 routes/notes; seed-040 task 14 carries the full install contract; seed-160 step 4 carries the merge-safe upgrade backfill.)
- [x] `seed-040` — document `build.config.json` schema; describe the four default targets; note that `exports/` contents are generated and must not be hand-edited.
- [x] `seed-050` — extend AGENTS guidance with token reference syntax for each target format.
- [x] `docs/design-system/bin/build-tokens` — wrapper script; reads `build.config.json`; invokes tool; reports errors.
- [x] `docs/design-system/build.config.json` seed stub — emitted by install/upgrade when absent. (Default stub `style-dictionary` documented in seeds; this repo's committed config uses `builtin` because there is no Node toolchain — see note in the file.)
- [x] `manifest.json` stale-exports logic — add `exportsGenerated`, `exportsStale`, `exportsAt` fields; update after successful build. (`design_token_build.update_manifest_parity`.)
- [x] `wave_lint_lib` — add stale-exports validator; register in lint CLI. (Warning added to `check_design_system`, already wired into `cli.py`.)
- [x] `docs/design-system/AGENTS.md` — extend with token reference patterns and `bin/build-tokens` instruction.
- [x] Framework tests — build pipeline test covering AC-10 cases. (`tests/test_design_token_build.py`.)
- [x] Framework edit guard: flip `framework_edit_allowed.enabled: true` before editing scripts; restore after. (Opened/closed `framework_edit_allowed` for scripts/tests and `seed_edit_allowed` for seed prompts; both closed.)

## Agent Execution Graph


| Workstream            | Owner       | Depends On              | Notes                                                    |
| --------------------- | ----------- | ----------------------- | -------------------------------------------------------- |
| config-schema         | planner     | —                       | `build.config.json` shape and stub                       |
| output-targets        | implementer | config-schema           | CSS, Tailwind, TS, JSON transformations                  |
| build-wrapper         | implementer | config-schema           | `bin/build-tokens` script                                |
| stale-detection       | implementer | output-targets          | `manifest.json` fields + lint validator                  |
| seed-integrations     | implementer | config-schema           | `seed-010/040/050/160` updates                           |
| agents-md-update      | implementer | output-targets          | Token reference syntax in `AGENTS.md`                    |
| tests                 | implementer | output-targets, stale   | Framework test suite                                     |
| review                | reviewer    | all above               | docs-contract + framework-code lanes                     |


## Serialization Points

- `manifest.json` schema changes must coordinate with any concurrent changes adding fields to `validationSummary`.
- `docs/design-system/AGENTS.md` is shared with `12akr-enh`; edits must not remove or rename the rules landed there.

## Affected Architecture Docs

- **Updated:** `docs/architecture/design-system.md` (seeded by `12akr-enh`) — add token build pipeline section: how `exports/` is generated, when to re-run, stale detection.
- No other architecture docs expected to change.

## AC Priority

(Populated at Prepare wave.)


| AC    | Priority     | Rationale                                                                  |
| ----- | ------------ | -------------------------------------------------------------------------- |
| AC-1  | required     | Config schema is the foundation of the pipeline contract.                  |
| AC-2  | required     | CSS output is the most widely used format.                                 |
| AC-3  | important    | Tailwind output needed for Tailwind-stack repos.                           |
| AC-4  | important    | TypeScript output enables type-safe token usage.                           |
| AC-5  | important    | Flat JSON output is the simplest interop format.                           |
| AC-6  | required     | Idempotency prevents spurious diffs in version-controlled output.          |
| AC-7  | required     | Build wrapper is the operator's entry point.                               |
| AC-8  | important    | Stale detection prevents agents from using outdated token syntax.          |
| AC-9  | required     | AGENTS.md update closes the gap that motivated this wave.                  |
| AC-10 | required     | Framework test is the enforcement layer.                                   |


## Progress Log


| Date       | Update                                                                                  | Evidence                    |
| ---------- | --------------------------------------------------------------------------------------- | --------------------------- |
| 2026-05-01 | Plan created to track token-build pipeline work deferred from `12as1 design-system-extraction` | Operator direction |
| 2026-06-20 | Revived into wave `1p75h design-system-foundation`; paths corrected to `docs/design-system/`; dependency re-pointed to `1p6z6-enh` | Operator direction; repo analysis |
| 2026-06-22 | Implemented: `build.config.json`, `bin/build-tokens`, bundled pure-Python transform (`design_token_build.py`), manifest export-parity + stale lint, seed-010/040/050/160 pipeline setup, AGENTS.md token-reference guidance, framework test (12 cases). Real `exports/` generated for this repo via the `builtin` transform (no Node/Style-Dictionary install). | Full suite green (3347 tests); `docs-lint: ok`; `exportsGenerated: true`, `exportsStale: false` |


## Decision Log


| Date       | Decision                                                                     | Reason                                                                           | Alternatives                                  |
| ---------- | ---------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | --------------------------------------------- |
| 2026-05-01 | Tool-agnostic config contract (`build.config.json`) rather than hard-coding Style Dictionary | Not every target repo uses the same stack; keeps the pipeline swappable | Hard-code Style Dictionary |
| 2026-05-01 | Deferred from `12as1` wave rather than included                              | Installing build tooling is a separate concern from defining the token contract  | Include in `12as1`                            |
| 2026-06-20 | Revive in `1p75h` and depend on `1p6z6-enh` rather than the never-built `12akr-enh` | `12as1`/`12akr` extraction never ran; `1p6z6` now produces the populated token source from the live dashboard | Keep depending on `12akr-enh` (a plan that was never implemented) |


## Risks


| Risk                                                         | Mitigation                                                                          |
| ------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| Operators skip build step and reference stale exports        | Stale-exports lint validator warns; AGENTS.md documents the run instruction         |
| Style Dictionary v3 vs v4 API incompatibility               | `build.config.json` `version` field; seed documents both API shapes                |
| Generated exports get hand-edited and drift from source     | `/* generated */` header comment; lint validator flags manual edits via hash check  |
| CSS output conflicts with existing CSS custom property names | Seed documents namespace strategy (`--ds-` prefix by default); operator-configurable |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
