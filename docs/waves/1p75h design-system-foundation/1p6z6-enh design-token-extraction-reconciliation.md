# Design Token Extraction + Reconciliation

Change ID: `1p6z6-enh design-token-extraction-reconciliation`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-20
Wave: `1p75h design-system-foundation`

## Rationale

The `docs/design-system/` extraction contract was scaffolded by wave `12as1 design-system-extraction` but the extraction pass **never ran**: every `tokens/*.json` file is `{}`, `components/_index.json` is `{"components": []}`, `source-map.json` is `[]`, and `manifest.json` records `extractedAt: null` with `validationSummary {passed: 0, failed: 0}`. The contract's governing rule is **"extract, don't invent"** (`docs/architecture/design-system.md`), and the live dashboard stylesheet `.wavefoundry/framework/dashboard/dashboard.css` is the de-facto source of truth: 59 fully-defined custom properties with light + dark values.

Two problems block every downstream consumer:

1. **No populated token contract.** Agents that follow `docs/design-system/AGENTS.md` ("never use raw hex/px"; "reference semantic tokens") cannot, because no semantic tokens exist. The token-build pipeline (`12atj`) has no input. The primitive abstraction (`1p72v`) has no token vocabulary to bind components to.
2. **Drifted narrative.** `foundations/dashboard.md` (the one non-stub foundation doc) documents a warm-parchment / teal / serif palette that the dashboard **no longer ships** — live is cool-gray (`--page-bg: #F8F9FA`), blue accent (`--accent: #1976d2`), system-sans. Its value tables and "warm neutral palette" principles are wrong and will actively mislead agents.

This change runs the deferred extraction from the live CSS evidence and reconciles the drifted narrative, producing the populated, validated token contract the rest of the foundation wave depends on. It is intentionally scoped to `docs/design-system/` only — all stylesheet/code edits (defining missing token vars, tokenizing the brand palette, consuming token vars) are owned by `1p72v-ref` so this change carries no behavioral-code blast radius.

## Requirements

1. **Primitives extraction.** Extract every `:root` custom property in `dashboard.css` into `tokens/primitives.tokens.json` as DTCG tokens with raw resolved values, grouped by category (color, space, radius, shadow, typography, layout).
2. **Semantic layer.** Author `tokens/semantic.tokens.json` mapping usage roles to primitives via the dot-path convention (`category.subcategory.scale.variant`) — e.g. `color.action.primary` → accent, `color.feedback.danger`, `color.surface.panel`, `space.*`, `radius.*`, `elevation.*`, `font.*`. Semantic tokens reference primitives by alias, never raw values.
3. **Mode coverage.** Populate `tokens/modes/light.tokens.json` and `tokens/modes/dark.tokens.json` with the per-mode overrides extracted from `:root` (light) and `html[data-theme="dark"]` (dark). Record every token whose dark value differs from light; record tokens **not** re-themed in dark (e.g. `--neutral`) explicitly as intentional or as a `gaps.md` entry.
4. **Reconcile the drifted narrative.** Rewrite `foundations/dashboard.md` value tables and design-principles prose to the shipped palette (cool-neutral / blue accent / system-sans), removing the stale warm-parchment/teal/serif content. Preserve operator-authored structure; correct only what conflicts with live evidence.
5. **Fill stub foundations.** Populate `foundations/{color,typography,spacing,radius,elevation,motion}.md` from extracted evidence. Where evidence is absent, record `null` + a matching `gaps.md` entry — do not invent.
6. **Record known CSS gaps (do not fix here).** Log as `gaps.md` entries, scoped to `1p72v-ref`: (a) the undefined-but-referenced token family `--text` / `--border` / `--surface` / `--surface-raised`; (b) the hardcoded "Aceiss" brand palette and the ~120 per-component hardcoded-hex dark overrides that bypass tokens; (c) the layout tokens `--footer-accent` / `--header-h` / `--rail-w` absent from the prior contract.
7. **Manifest + source map.** Update `manifest.json` (`extractedAt` ISO-8601, `sourceStrategy: "repo-evidence-only"`, `evidenceTypes`, `artifactCounts`, `validationSummary`) and populate `source-map.json` mapping each extracted token to its `dashboard.css` evidence location with a confidence value.
8. **Validation clean.** `docs-lint` / `wave_validate` pass; design-system Split B/C semantic validators (`design_system_surface_validators.py`, `design_system_governance_validators.py`) pass for the populated surfaces, or any failure is a recorded gap with rationale.

## Scope

**Problem statement:** The design-system token contract is empty and its one real narrative doc is drifted from the shipped design, blocking the token-build pipeline, the primitive abstraction, and any agent trying to use semantic tokens.

**In scope:**

- `docs/design-system/tokens/{primitives,semantic}.tokens.json` and `tokens/modes/{light,dark}.tokens.json`.
- `docs/design-system/foundations/dashboard.md` reconciliation + stub foundations population.
- `docs/design-system/{manifest.json,source-map.json,gaps.md}` updates.
- Validation pass against the populated contract.

**Out of scope:**

- Any edit to `.wavefoundry/framework/dashboard/dashboard.css` or `dashboard.js` (owned by `1p72v-ref`).
- Token-build exports (`exports/{css,ts,tailwind,json}`) — owned by `12atj-feat`.
- Component specs (`components/*/spec.json`) — owned by `1p72v-ref`.
- The claude.ai/design sync — follow-on wave.

**Depends on:** nothing (foundation of the wave).
**Blocks:** `12atj-feat` (needs populated tokens), `1p72v-ref` (needs token vocabulary + gap log).

## Acceptance Criteria

- [x] AC-1: `tokens/primitives.tokens.json` contains every `dashboard.css` `:root` custom property as a DTCG token with the correct resolved value; a diff check against the CSS shows no missing or mismatched value. (Evidence: scripted diff — 36 `:root` props ↔ 36 primitive leaves, 0 mismatches.)
- [x] AC-2: `tokens/semantic.tokens.json` defines semantic tokens for color (surface, ink, accent, feedback danger/warn/draft/neutral), spacing, radius, elevation, and typography, each aliasing a primitive (no raw values). (29 semantic tokens, all `{primitive.path}` aliases; CORE validator: 0 broken aliases, 0 orphans.)
- [x] AC-3: `tokens/modes/light.tokens.json` and `dark.tokens.json` capture all per-mode overrides; light/dark parity report exists and every divergence is intentional or a recorded gap. (19 themed keys each; mode-parity validator passes; scripted diff confirms 19 dark CSS overrides match exactly; `--neutral` confirmed not re-themed — carried forward + noted in modes/dark + color.md + gaps.)
- [x] AC-4: `foundations/dashboard.md` value tables and principles match the live `dashboard.css` palette; no warm-parchment/teal/serif values remain. (Color/shadow/radius/typography tables + principles reconciled to cool-gray/blue/system-sans; stale-palette grep returns only `sans-serif` substring matches.)
- [x] AC-5: `foundations/{color,typography,spacing,radius,elevation,motion}.md` are populated from evidence or carry explicit `null` + `gaps.md` entries. (All six populated; `motion.md` records null — no motion tokens in source.)
- [x] AC-6: `gaps.md` records the undefined `--text/--border/--surface` family, the hardcoded Aceiss palette / dark hex overrides, and the `--footer-accent/--header-h/--rail-w` tokens, each scoped to `1p72v-ref`. (G1 undefined family · G2 Aceiss palette + ~120 dark hex overrides · G3 `--footer-accent/--rail-w/--view-max/--view-max-wide` · G4 `--header-h` recorded absent — not in source since header removed in 1p6nl.)
- [x] AC-7: `manifest.json` has a non-null `extractedAt`, `sourceStrategy: "repo-evidence-only"`, populated `evidenceTypes`/`artifactCounts`/`validationSummary`; `source-map.json` maps tokens to evidence with confidence. (`extractedAt: 2026-06-21`; 36 source-map entries with CSS line evidence + confidence.)
- [x] AC-8: `docs-lint` / `wave_validate` pass; applicable design-system validators pass or failures are recorded gaps. (`docs-lint: ok`; CORE/SURFACE/GOVERNANCE validators: 0 failures, 0 warnings; 118 design-system unit tests pass.)

## Tasks

- [x] Extract `:root` custom properties → `primitives.tokens.json` (DTCG), grouped by category.
- [x] Author `semantic.tokens.json` dot-path mappings to primitives.
- [x] Populate `modes/light.tokens.json` + `modes/dark.tokens.json`; produce light/dark parity report.
- [x] Rewrite `foundations/dashboard.md` to the shipped palette; remove drifted content.
- [x] Populate stub `foundations/*.md` from evidence; null + gap where absent.
- [x] Write `gaps.md` entries for the three CSS gap classes, scoped to `1p72v-ref`.
- [x] Update `manifest.json` + `source-map.json`.
- [x] Run `docs-lint` / design-system validators; resolve or record findings.

## Agent Execution Graph


| Workstream            | Owner       | Depends On       | Notes                                            |
| --------------------- | ----------- | ---------------- | ------------------------------------------------ |
| primitives-extraction | implementer | —                | `:root` → `primitives.tokens.json`               |
| semantic-mapping      | implementer | primitives       | dot-path semantic layer                          |
| mode-extraction       | implementer | primitives       | light/dark mode files + parity report            |
| narrative-reconcile   | implementer | primitives       | `foundations/dashboard.md` + stub foundations    |
| manifest-sourcemap    | implementer | all extraction   | `manifest.json`, `source-map.json`, `gaps.md`    |
| validation            | reviewer    | all above        | docs-lint + design-system validators             |


## Serialization Points

- `gaps.md` is shared with `1p72v-ref` (which closes the gaps); entries here must use the agreed scope tags so `1p72v` can resolve them without renumbering.
- `manifest.json` `validationSummary` shape must stay compatible with the `12atj` export-parity fields added later.

## Affected Architecture Docs

- **No change.** `docs/architecture/design-system.md` already specifies the extraction philosophy and contract shape this change populates. This change is the first real execution of that contract; it does not alter the architecture. (Confirm at Prepare; update only if extraction reveals a contract-shape gap.)

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Primitives extraction is the core token contract; diff-verified against the live CSS. |
| AC-2 | required  | The semantic layer is what consumers reference — the whole point of populating the contract. |
| AC-3 | required  | Dark mode ships, so mode coverage + the light/dark parity report are core, not optional. |
| AC-4 | required  | The drifted `foundations/dashboard.md` actively misleads agents; reconciliation is load-bearing. |
| AC-5 | important | Stub-foundation population; `null` + recorded gaps is an acceptable floor where evidence is absent. |
| AC-6 | required  | `gaps.md` is the explicit handoff that scopes `1p72v`; without it that change has no gap list. |
| AC-7 | important | `manifest.json` / `source-map.json` provenance — valuable traceability, not a blocker on token use. |
| AC-8 | required  | Validation gate: docs-lint + the design-system validators. |


## Progress Log


| Date       | Update                                                        | Evidence                          |
| ---------- | ------------------------------------------------------------ | --------------------------------- |
| 2026-06-20 | Plan created — token extraction/reconciliation from live CSS | Operator direction; repo analysis |
| 2026-06-21 | Implemented — extracted 36 primitives + 29 semantic tokens + light/dark modes from `dashboard.css`; reconciled `foundations/dashboard.md`; populated 6 foundation docs; recorded 4 gaps (G1–G4); updated manifest + 36-entry source-map | docs-lint ok; CORE/SURFACE/GOVERNANCE validators 0 fail/0 warn; 118 unit tests pass; scripted CSS↔token diff 0 mismatches |


## Decision Log


| Date       | Decision                                                                                  | Reason                                                                                                                  | Alternatives                                                                                              |
| ---------- | ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| 2026-06-20 | **Divergent pre-plan — selected: curated extraction grounded in `dashboard.css` evidence** | The semantic layer requires human naming judgment the contract explicitly wants ("extract, don't invent"); a CSS-diff check guards against transcription error. | (A) Pure auto-parse of `:root` → produces primitives only, no semantic layer. (C) Defer until pipeline exists → circular (pipeline needs tokens as input). |
| 2026-06-20 | Scope this change to `docs/design-system/` only; all CSS/code edits owned by `1p72v-ref`  | Keeps the extraction a documentation change with no behavioral-code blast radius; isolates code risk in the refactor.   | Fold CSS token-var fixes into this change (couples docs extraction to framework-asset edits + gate).      |
| 2026-06-20 | Treat `dashboard.css` as source of truth; reconcile (not preserve) `foundations/dashboard.md` | Token files are all empty — nothing real to preserve; the narrative doc is provably drifted from shipped CSS.          | Build on the documented (warm-parchment) values → reproduces the drift; reconcile both ways → no second real source exists. |


## Risks


| Risk                                                              | Mitigation                                                                       |
| ---------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Manual transcription error in token values                       | Automated diff check of `primitives.tokens.json` against `dashboard.css` `:root` |
| Semantic naming diverges from later component bindings (`1p72v`) | Name semantic tokens against the dashboard's actual usage roles, not abstractly  |
| Reconciling `foundations/dashboard.md` loses operator intent     | Correct only conflicting values/principles; preserve authored structure + notes  |
| Dark-mode token gaps under-recorded                              | Produce an explicit light/dark parity report; every non-themed token accounted   |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
