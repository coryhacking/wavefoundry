# Design Token Build Pipeline

Change ID: `12atj-feat design-token-build-pipeline`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-05-01
Wave: TBD

## Rationale

Wave `12as1 design-system-extraction` lands DTCG token source files (`primitives.tokens.json`, `semantic.tokens.json`, mode files) and stubs `docs/design/exports/{css,tailwind,ts,json}/` as empty placeholders. Those stub directories only become useful once a token transformation step reads the DTCG source and emits framework-specific outputs. Without this pipeline, agents cannot reference `var(--color-action-primary-background)` in CSS, or `theme.colors.primary[500]` in Tailwind, or the typed `tokens.color.action.primary.background` constant in TypeScript — they are forced to hard-code values, which the `docs/design/AGENTS.md` contract explicitly forbids. This change closes that gap by adding a Stack Dictionary-based (or equivalent) build pipeline that is configured by the operator and executed during extraction or on-demand.

This change depends on `12akr-enh design-system-directory-structure-extraction` being implemented first.

## Requirements

1. **Tool-agnostic config contract.** The pipeline must be driven by a config file at `docs/design/.design-system/build.config.json` that declares: `tool` (enum: `style-dictionary`, `token-pipeline`, `custom`), `version`, `targets` (array of `{ format, outputDir, options }`). When `tool: "custom"`, a `command` field holds the shell invocation. This keeps the build contract machine-readable without hard-coding one tool.
2. **Default targets.** When `target` includes `css`, the pipeline emits CSS custom properties to `docs/design/exports/css/tokens.css` covering all semantic tokens and mode overrides. When `target` includes `tailwind`, it emits a Tailwind v3/v4-compatible `docs/design/exports/tailwind/theme.config.js` (or `.ts`). When `target` includes `ts`, it emits typed token constants to `docs/design/exports/ts/tokens.ts`. When `target` includes `json`, it emits a flat resolved token map to `docs/design/exports/json/tokens.json`.
3. **Mode-aware outputs.** CSS output must emit a base (light) rule-set plus a `@media (prefers-color-scheme: dark)` / `[data-theme="dark"]` override block. TypeScript output must export per-mode token maps. Tailwind output must include dark-mode variants where dark tokens differ from light.
4. **Idempotent and diff-friendly.** Re-running the pipeline on an unchanged token source must produce byte-identical output (modulo timestamp comments). Generated files must carry a `/* generated — do not edit directly */` header comment so operators know not to hand-edit them. No random ordering in output.
5. **Install and upgrade hooks.** `seed-010` and `seed-160` must describe the pipeline setup step: detect `build.config.json`; when absent, emit a stub with `tool: "style-dictionary"` and the standard four targets so the operator has a starting point. The stub must work out-of-the-box for a Style Dictionary install (`npm install -D style-dictionary`).
6. **Run command via `wavefoundry/bin/`.** Add a `docs/design/bin/build-tokens` wrapper script that reads `build.config.json` and invokes the configured tool. The wrapper must exit non-zero on transformation errors and print actionable messages (missing dependency, broken token reference at build time).
7. **`manifest.json` export parity field.** After a successful build, `manifest.json` `validationSummary` must record `exportsGenerated: true` and a `exportsAt` ISO-8601 timestamp. When exports are stale (token source newer than exports), `manifest.json` must record `exportsStale: true`. A lint validator must warn when `exportsStale` is `true`.
8. **AGENTS.md update.** `docs/design/AGENTS.md` (seeded by `12akr-enh`) must be extended to document: use `var(--<token-name>)` for CSS, import from `exports/ts/tokens.ts` for TypeScript, reference `exports/tailwind/theme.config.js` for Tailwind — never hard-code values; run `bin/build-tokens` after editing token source files.
9. **`docs_search` discoverability of exports.** The chunker routing added by `12akr-enh` covers `docs/design/**/*.json`. Ensure `exports/ts/tokens.ts` and `exports/css/tokens.css` are either indexed as doc chunks or explicitly excluded with a note — agents should find token names via docs search, not by parsing generated source files.
10. **Framework test.** A framework test must: (a) write minimal valid DTCG token files to a temp directory; (b) invoke the build pipeline; (c) assert the four output files are generated with correct structure; (d) assert re-running produces identical output; (e) assert a broken token ref at build time exits non-zero.

## Scope

**Problem statement:** `docs/design/exports/` is seeded as empty stubs by `12as1 design-system-extraction`. Agents that follow the `AGENTS.md` token usage rules (no hard-coded values) cannot reference framework-specific token syntax until the transformation pipeline is configured and run.

**In scope:**

- `build.config.json` schema and default stub.
- CSS, Tailwind, TypeScript, and flat JSON output targets.
- Mode-aware output for all target formats.
- `docs/design/bin/build-tokens` wrapper script.
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

- **AC-1** (`build.config.json` schema): stub is generated by install/upgrade when absent; `tool`, `version`, `targets` fields present; `custom` path supported.
- **AC-2** (CSS output): `exports/css/tokens.css` contains all semantic tokens as custom properties; light base + dark override blocks present when dark mode tokens exist.
- **AC-3** (Tailwind output): `exports/tailwind/theme.config.js` is valid Tailwind config extending `colors`, `spacing`, `borderRadius`, `fontSize`, and other detected token categories.
- **AC-4** (TypeScript output): `exports/ts/tokens.ts` exports typed token constants; no `any` types; imports resolve without errors in strict mode.
- **AC-5** (JSON output): `exports/json/tokens.json` is a flat resolved key-value map; all alias references resolved to raw values.
- **AC-6** (Idempotency): re-running on unchanged source produces byte-identical output.
- **AC-7** (Build wrapper): `docs/design/bin/build-tokens` runs the configured tool; exits non-zero on error; prints actionable message.
- **AC-8** (Stale detection): `manifest.json` `exportsStale: true` when token source is newer than exports; lint validator warns.
- **AC-9** (AGENTS.md): token reference patterns for CSS/TS/Tailwind documented; `bin/build-tokens` run instruction present.
- **AC-10** (Framework test): build, idempotency, and broken-ref exit-code cases covered.

## Tasks

- `seed-010` / `seed-160` — add pipeline setup step: detect `build.config.json`, emit stub when absent, document `npm install -D style-dictionary` as the default path.
- `seed-040` — document `build.config.json` schema; describe the four default targets; note that `exports/` contents are generated and must not be hand-edited.
- `seed-050` — extend AGENTS guidance with token reference syntax for each target format.
- `docs/design/bin/build-tokens` — wrapper script; reads `build.config.json`; invokes tool; reports errors.
- `docs/design/.design-system/build.config.json` seed stub — emitted by install/upgrade when absent.
- `manifest.json` stale-exports logic — add `exportsGenerated`, `exportsStale`, `exportsAt` fields; update after successful build.
- `wave_lint_lib` — add stale-exports validator; register in lint CLI.
- `docs/design/AGENTS.md` — extend with token reference patterns and `bin/build-tokens` instruction.
- Framework tests — build pipeline test covering AC-10 cases.
- Framework edit guard: flip `framework_edit_allowed.enabled: true` before editing scripts; restore after.

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
- `docs/design/AGENTS.md` is shared with `12akr-enh`; edits must not remove or rename the rules landed there.

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


## Decision Log


| Date       | Decision                                                                     | Reason                                                                           | Alternatives                                  |
| ---------- | ---------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | --------------------------------------------- |
| 2026-05-01 | Tool-agnostic config contract (`build.config.json`) rather than hard-coding Style Dictionary | Not every target repo uses the same stack; keeps the pipeline swappable | Hard-code Style Dictionary |
| 2026-05-01 | Deferred from `12as1` wave rather than included                              | Installing build tooling is a separate concern from defining the token contract  | Include in `12as1`                            |


## Risks


| Risk                                                         | Mitigation                                                                          |
| ------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| Operators skip build step and reference stale exports        | Stale-exports lint validator warns; AGENTS.md documents the run instruction         |
| Style Dictionary v3 vs v4 API incompatibility               | `build.config.json` `version` field; seed documents both API shapes                |
| Generated exports get hand-edited and drift from source     | `/* generated */` header comment; lint validator flags manual edits via hash check  |
| CSS output conflicts with existing CSS custom property names | Seed documents namespace strategy (`--ds-` prefix by default); operator-configurable |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
