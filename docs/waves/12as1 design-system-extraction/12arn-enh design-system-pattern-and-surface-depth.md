# Design-system pattern and surface depth

Change ID: `12arn-enh design-system-pattern-and-surface-depth`
Change Status: `done`
Owner: Engineering
Status: done
Last verified: 2026-05-01
Wave: `12as1 design-system-extraction`

## Rationale

The core extraction contract from `12akr-enh design-system-directory-structure-extraction` lands the tree, tokens, and component spec but intentionally defers deep UI surface coverage. Target repos still lack first-class extraction slots for navigation/shell, feedback, data-heavy UI, trust-sensitive flows, state/validation patterns, content depth, asset handling, deep accessibility, and motion choreography. Without this layer, agents implementing UI have no deterministic source for "what does a toast look like here?" or "how does this app handle empty states?" and fall back to inventing patterns.

This change depends on `12akr-enh` being admitted and implemented (or at least the tree contract and `manifest.json` core schema being pinned). It extends the contract rather than rewriting it.

## Requirements

1. **Patterns subtree.** Seed `patterns/` as a required subtree with `_index.json` and four required first-level pattern groups:
   - `patterns/navigation/` — primary/secondary nav, drawers vs tabs vs rails, breadcrumbs, command palette / global search entry.
   - `patterns/feedback/` — toast, snackbar, banner, modal, inline messaging; cross-link `tokens/z-index.tokens.json` for overlay stacking.
   - `patterns/data/` — tables, lists, pagination vs infinite scroll, skeleton/empty states for data, chart/series semantic colors with a11y expectations.
   - `patterns/trust/` — auth, session/security messaging, masked fields, destructive/irreversible actions, confirmation flows.

   Each group must have `_index.json` and `README.md`; per-pattern subdirectories (`patterns/navigation/<pattern-name>/`) are optional and contain `README.md` + `visuals/`.
2. **State-patterns subtree.** `state-patterns/` must cover `loading/`, `empty/`, `error/`, `success/` with `_index.json` and `README.md`. Components' `spec.json` `states` section must reference these patterns by ID when applicable.
3. **Validation-patterns subtree.** `validation-patterns/` must include `required-field.md`, `format-validation.md`, `async-validation.md`, `error-display.md`, `success-confirmation.md`, plus `_index.json` and `README.md`.
4. **Content subtree (depth).** `content/` must include `voice.md`, `microcopy.json` (centralized repeated labels/messages), `formatting.md`, `i18n.md`, `rtl-layout.md` (layout mirroring, logical properties, directional motion), `locale-formats.md` (date/time/number/currency formatting ownership or gaps), `brand-legal.md` (clear space, min size, on-photo/on-dark rules, co-branding, trademark line) when brand evidence exists, and `README.md`. Inferred microcopy entries must be marked and listed in `gaps.md`.
5. **Extended foundations.** `foundations/` must add: `shell.md` (app shell, safe areas, min window sizes where relevant, density posture), `density.md`, `responsive.md`, `grid.md`, `z-index.md`, `iconography.md`, `data-visualization.md`, `media-motion.md` (Lottie/video/haptics with reduced-motion fallbacks). Extend `foundations/typography.md` with type roles (display/title/body/caption/mono), tabular figures, truncation/line-clamp rules, link states (default/visited/hover), font delivery (system vs webfont stacks, fallbacks, weight limits). Extend `foundations/motion.md` with enter/exit pairing, stagger rules, scroll-linked vs time-based motion.
6. **Deep accessibility.** `accessibility/` must add `focus.md` (focus ring treatment, offset, cross-link to `tokens/focus.tokens.json`), `keyboard.md` (shortcuts policy, roving tabindex, escape from overlays, focus traps), `screen-reader.md` (heading order, live regions polite vs assertive, form error announcement patterns). Dark mode verification must include readability/contrast, visual hierarchy, component/state distinguishability, and interaction affordances — not just a background swap.
7. **Extended token files.** Add required `tokens/borders.tokens.json` (border width, divider, hairline semantic roles), `tokens/focus.tokens.json` (focus ring color, width, offset), `tokens/z-index.tokens.json`, and `tokens/motion.tokens.json`. All must follow the DTCG two-tier contract from `12akr-enh`. Missing source → explicit `null` + `gaps.md` entry per the core extract-don't-invent rule.
8. **Asset contract.** Seed `icons/`, `illustrations/`, `logos/`, `images/` with:
   - `icons/` — `_index.json` (aliases/tags, `rtlMirror` metadata), `README.md`, `svg/`, `sprite.svg`, `exports/{react,tokens.json}`. Icon exports must enforce square `viewBox`, `currentColor` (unless multicolor), and metadata stripping.
   - `illustrations/` — `_index.json`, `README.md`, per-illustration folders with `source.svg` / `source.png` + `meta.json`.
   - `logos/` — `_index.json`, `README.md`, per-variant folders.
   - `images/` — `_index.json`, `README.md`, `REVIEW.md`, `raw/<hash>.<ext>` for hash-based dedup.
9. **Component `spec.json` behavioral fields.** The reserved keys from `12akr-enh` (`states`, `responsive`, `motion`, `accessibility`, `content`) — emitted with `null` values in the core seed — must now be populated when source evidence exists. This change specifies each field's shape:
   - `states` — array of state references (`loading`/`empty`/`error`/`success`) resolving to `state-patterns/<state>/` entries, plus per-state overrides.
   - `responsive` — breakpoint behavior per variant (token refs from `tokens/z-index.tokens.json` and `foundations/responsive.md`).
   - `motion` — enter/exit/stagger references to `tokens/motion.tokens.json` keys; reduced-motion fallback required when any entry is non-null.
   - `accessibility` — aria roles, keyboard map references, focus-token ID, screen-reader announcements (cross-link `accessibility/keyboard.md` and `screen-reader.md`).
   - `content` — microcopy key references into `content/microcopy.json`, voice/tone tag.

   Missing-source fields stay `null` and produce a matching `gaps.md` entry per the extract-don't-invent rule. Keys are never removed — only populated or left `null`.
10. **`spec.json` references to other subtrees.** `states` entries may reference `state-patterns/<state>/` by ID. `accessibility.focus` may reference `accessibility/focus.md`. `content.microcopy` entries may reference `content/microcopy.json` keys. These cross-references must resolve at validation time.
11. **Skills subtree.** `skills/` must include: `implement-component/SKILL.md`, `audit-against-design-system/SKILL.md`, `add-new-component/SKILL.md`, `add-new-icon/SKILL.md`, `theme-and-mode/SKILL.md`, `implement-form/SKILL.md`, `implement-state/SKILL.md`, `navigation-and-shell/SKILL.md`, `sensitive-flows/SKILL.md`. Each SKILL.md must reference the relevant subtrees it consumes.
12. **`gaps.md` extended categories.** Extend the core category list with: `patterns`, `navigation`, `shell`, `feedback`, `data`, `trust`, `i18n`, `locale`. Severity model unchanged.
13. **Semantic validators.** Extend `wave_lint_lib` validators to cover (note: broken token refs, orphan primitives, mode parity for `light`/`dark`, and `components/_index.json` ↔ folder parity are owned by `12akr-enh` and must already be passing before this change runs):
    - WCAG contrast check from `accessibility/contrast-report.json` when present.
    - Extended mode parity: when this change adds new extended token files (`borders`, `focus`, `z-index`, `motion`), each extended file's keys must also be present in both light and dark mode files where a mode override exists.
    - State coverage: component `spec.json` `states` references resolve to `state-patterns/` entries.
    - Reduced-motion presence check when `tokens/motion.tokens.json` has non-null duration tokens.
    - Microcopy consistency: repeated literal strings flagged as candidates for `content/microcopy.json`.
    - Icon sanity: `viewBox` is square, stroke/fill uses `currentColor` unless flagged multicolor.
    - Focus-token usage: components that declare keyboard interactions reference focus tokens.
    - Keyboard pattern: `accessibility/keyboard.md` exists when any component `spec.json` declares keyboard shortcuts.
    - Overlay stacking: `patterns/feedback/` entries that declare layering cross-reference `tokens/z-index.tokens.json` values.
14. **Discovery globs in `seed-030`.** Extend repository evidence scan with globs covering: patterns (nav/sidebar/drawer/breadcrumb/shell), auth/login/signin/mfa/oauth, charts (chart/graph/d3/recharts/data-viz), keyboard a11y (a11y/accessibility/contrast), motion (animation/transition), breakpoints/responsive/grid, forms/validation/schema/zod/yup, states (loading/empty/error/success/skeleton). Record discovered evidence in `source-map.json`.
15. **Voice/tone extraction beyond Figma.** Seeded guidance must extract voice/tone from repository evidence (content style guides, localization message catalogs, high-frequency UI copy, support/help UX copy) when Figma lacks explicit copy guidelines. No strong source → `critical` or `important` gap.
16. **Two-phase gap policy.** Phase 1 is strict extraction. Phase 2 is guided remediation: each gap may include source-first fix, best-practice bootstrap option (clearly labeled proposal), validation target, and dark-mode quality target. Proposals must never merge silently into `semantic.tokens.json`.
17. **Best-practice risks section in `gaps.md`.** A separate section lists observed patterns that violate modern design-system best practices (raw hex values in components, missing reduced-motion, weak contrast, dark mode as background-only swap, inconsistent validation timing, ad-hoc microcopy, raw z-index escalation, chart colors not distinguishable for common color-vision deficiencies, missing keyboard escape from overlays). Advisory unless directly blocking ACs.

## Scope

**Problem statement:** The core extraction contract landed by `12akr-enh` gives a tree and token/component schema but no slots for navigation, feedback, data UI, trust flows, state/validation patterns, content depth, assets, deep a11y, or motion choreography. Without this layer, agents cannot extract the patterns that drive most UI implementation work, and `gaps.md` has no categories for the most common missing items.

**In scope:**

- `patterns/{navigation,feedback,data,trust}/` subtrees with `_index.json` + `README.md`.
- `state-patterns/` and `validation-patterns/` subtrees.
- `content/` depth (`voice.md`, `microcopy.json`, `formatting.md`, `i18n.md`, `rtl-layout.md`, `locale-formats.md`, `brand-legal.md`).
- Extended `foundations/` (`shell.md`, `density.md`, `responsive.md`, `grid.md`, `z-index.md`, `iconography.md`, `data-visualization.md`, `media-motion.md`; typography and motion deepened).
- Deep `accessibility/` (`focus.md`, `keyboard.md`, `screen-reader.md`; dark-mode verification beyond background swap).
- Extended tokens: `borders.tokens.json`, `focus.tokens.json`, `z-index.tokens.json`, `motion.tokens.json`.
- Asset contract: `icons/`, `illustrations/`, `logos/`, `images/` with dedup and integrity rules.
- Component `spec.json` behavioral fields (`states`, `responsive`, `motion`, `accessibility`, `content`) with cross-references.
- `skills/` subtree.
- Semantic validators in `wave_lint_lib` covering the checks in Requirement 13.
- `seed-030` evidence-scan globs for the new surfaces.
- `gaps.md` extended categories and best-practice risks section.

**Out of scope:**

- Core tree and schema (owned by `12akr-enh`).
- Multi-surface recording, HIG reference versions, no-DS visual-bootstrap, deprecation/lineage (owned by `12arn-enh design-system-bootstrap-and-governance`).
- Storybook metadata.
- Framework-specific code generation.

**Depends on:** `12akr-enh design-system-directory-structure-extraction` must be implemented first (or the two waves run in sequence with A ahead of B).

## Acceptance Criteria

- **AC-1** (Patterns tree): `patterns/{navigation,feedback,data,trust}/` each seeded with `_index.json` + `README.md`.
- **AC-2** (State + validation patterns): `state-patterns/` with four required subdirs and `validation-patterns/` with five required files are seeded.
- **AC-3** (Content depth): `content/` includes all files from Requirement 4; inferred microcopy entries are flagged.
- **AC-4** (Foundations depth): `foundations/` contains all files from Requirement 5; typography and motion sections include the extended topics listed.
- **AC-5** (Deep a11y): `accessibility/focus.md`, `keyboard.md`, `screen-reader.md` exist; dark-mode verification expectations documented beyond contrast ratio.
- **AC-6** (Extended tokens): `borders.tokens.json`, `focus.tokens.json`, `z-index.tokens.json`, `motion.tokens.json` seeded; mode parity enforced by validator.
- **AC-7** (Asset contract): `icons/`, `illustrations/`, `logos/`, `images/` seeded with the structure from Requirement 8; image raw dir uses hash-based naming.
- **AC-8** (Spec behavioral fields): components' `spec.json` populates the `null` behavioral keys seeded by `12akr-enh` with the shapes from Requirement 9 where source evidence exists; missing fields remain `null` with matching gap. No keys are added or removed — only populated.
- **AC-9** (Cross-references resolve): validator confirms `spec.json` references to `state-patterns/`, `accessibility/`, and `content/microcopy.json` keys resolve.
- **AC-10** (Skills): all nine SKILL.md files from Requirement 11 exist and reference consumed subtrees.
- **AC-11** (Extended gaps): `gaps.md` category list extended; "Best-practice risks" section scaffolded.
- **AC-12** (Semantic validators): each validator from Requirement 13 is implemented in `wave_lint_lib` with tests covering a passing case, a failing case, and a missing-evidence case. Validators for broken token refs, orphan primitives, and base mode parity are owned by `12akr-enh` and are a prerequisite — this change extends, never replaces them.
- **AC-13** (Evidence-scan globs): `seed-030` globs from Requirement 14 discover the new surfaces; hits land in `source-map.json`.
- **AC-14** (Voice/tone from repo): when Figma lacks voice/tone, seeded guidance extracts from repository evidence per Requirement 15.
- **AC-15** (Two-phase gap policy): Phase-1/Phase-2 behavior is documented in seed guidance; proposal fills stay out of `semantic.tokens.json`.

## Tasks

- `seed-040` — extend the `docs/design/` tree with all subtrees from Requirements 1–8; specify the `spec.json` behavioral field shapes (Requirement 9); state the cross-reference contract (Requirement 10).
- `seed-030` — add discovery globs from Requirement 14; extend `source-map.json` schema to record match source per evidence group.
- `seed-010` / `seed-160` — extend install/upgrade backfill checklists (owned by `12akr-enh`) with the additional required paths from this change.
- `seed-050` — extend AGENTS guidance to list the new subtrees agents may consult for component work.
- `seed-040` — extend the validator contract section (not `seed-070` / `seed-090`, which are the quality-and-debt and doc-gardening prompts unrelated to design extraction) to document the semantic validator rules from Requirement 13 so agents know what the design lint checks enforce.
- `seed-100` — add voice/tone repo-evidence extraction guidance from Requirement 15.
- Framework scripts:
  - `.wavefoundry/framework/scripts/wave_lint_lib/` — new module(s) or extensions for each validator in Requirement 13. Register in lint CLI. Each validator gets a test under `.wavefoundry/framework/scripts/tests/` covering pass, fail, and missing-evidence cases.
  - Flip `framework_edit_allowed` and `seed_edit_allowed` guards as needed; restore after.
- Docs:
  - `docs/architecture/design-system.md` (seeded by `12akr-enh`) — extend with the patterns/a11y/assets layer.
  - `docs/design/README.md` seed — document cross-reference rules between `spec.json` and pattern subtrees.

## Agent Execution Graph


| Workstream              | Owner       | Depends On            | Notes                                                                 |
| ----------------------- | ----------- | --------------------- | --------------------------------------------------------------------- |
| patterns-subtree        | planner     | —                     | `patterns/{nav,feedback,data,trust}/`                                 |
| state-validation-depth  | planner     | patterns-subtree      | `state-patterns/`, `validation-patterns/`                             |
| content-depth           | planner     | —                     | `content/*` incl. rtl/locale/brand-legal                              |
| foundations-depth       | planner     | —                     | Extended `foundations/` files                                         |
| a11y-depth              | planner     | foundations-depth     | `focus.md`, `keyboard.md`, `screen-reader.md`                         |
| extended-tokens         | planner     | foundations-depth     | `borders`, `focus`, `z-index`, `motion` token files                   |
| asset-contract          | planner     | —                     | Icons/illustrations/logos/images                                      |
| spec-behavioral-fields  | planner     | state-validation-depth, a11y-depth, content-depth | Reserved fields now populated            |
| skills-subtree          | planner     | all above             | Nine SKILL.md files                                                   |
| semantic-validators     | implementer | all above             | `wave_lint_lib` checks from Requirement 13                            |
| evidence-globs          | implementer | —                     | `seed-030` globs + `source-map.json` schema                           |
| seed-integrations       | implementer | patterns, content, foundations, a11y, tokens, assets | `seed-040/050/070/090/100/150/160` updates |
| tests                   | implementer | semantic-validators   | Framework tests                                                       |
| review                  | reviewer    | all above             | docs-contract + framework-code review lanes                           |


## Serialization Points

- `seed-040` is shared with `12akr-enh` and `12arn-enh design-system-bootstrap-and-governance` — sequence edits.
- `wave_lint_lib` validator additions may collide with `12akr-enh` core validators; coordinate module naming.
- `manifest.json` and `source-map.json` schemas must stay compatible with `12akr-enh` reservations.

## Affected Architecture Docs

- **Updated:** `docs/architecture/design-system.md` — add patterns/a11y/assets/content depth sections.
- **Updated:** `docs/ARCHITECTURE.md` cross-reference row is sufficient; no other hub docs expected.

## AC Priority

(Populated at Prepare wave.)


| AC    | Priority  | Rationale                                                          |
| ----- | --------- | ------------------------------------------------------------------ |
| AC-1  | required  | Patterns tree is the largest single extension to the contract.     |
| AC-2  | required  | State + validation patterns are directly consumed by `spec.json`.  |
| AC-3  | required  | Content depth prevents microcopy drift across components.          |
| AC-4  | required  | Foundations depth unblocks consistent layout and typography decisions. |
| AC-5  | required  | Deep a11y is the main gap in the core contract.                    |
| AC-6  | required  | Extended tokens are referenced by focus/border/motion checks.      |
| AC-7  | required  | Asset contract prevents icon/logo drift.                           |
| AC-8  | required  | Spec behavioral fields are what agents read during implementation. |
| AC-9  | important | Cross-reference validation catches orphan patterns early.          |
| AC-10 | important | Skills orient agents to the new surfaces.                          |
| AC-11 | important | Extended gap categories keep the gap log useful.                   |
| AC-12 | required  | Validators are the enforcement layer for everything above.         |
| AC-13 | important | Evidence-scan globs drive discovery rather than guessing.          |
| AC-14 | important | Voice/tone extraction path keeps `content/voice.md` trustworthy.   |
| AC-15 | important | Two-phase gap policy prevents silent invention.                    |


## Progress Log


| Date       | Update                                                                                                       | Evidence                   |
| ---------- | ------------------------------------------------------------------------------------------------------------ | -------------------------- |
| 2026-05-01 | Change split off from `12akr-enh` to carry patterns, foundations depth, deep a11y, assets, spec behavior, and semantic validators | Reviewer pre-admission notes |
| 2026-05-01 | Req 9 refined: behavioral keys are populated (not added) — core seed emits them as `null`, this change fills in shapes per field | Operator decision during plan interrogation |


## Decision Log


| Date       | Decision                                                                                   | Reason                                                                                  | Alternatives                           |
| ---------- | ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------- | -------------------------------------- |
| 2026-05-01 | Depend on `12akr-enh` rather than duplicate tree/schema                                    | Keeps the core schema single-owner; this change is a pure extension                      | Bundle everything back into `12akr-enh` |
| 2026-05-01 | Pattern subtrees use `_index.json` + `README.md` minimum, per-pattern dirs optional        | Lets greenfield teams ship a stub; evidence-rich teams add detail                        | Require per-pattern dirs always        |
| 2026-05-01 | Validators live in `wave_lint_lib` alongside existing docs validators                      | Reuses lint CLI and test harness                                                         | Separate CLI for design checks         |


## Risks


| Risk                                                        | Mitigation                                                                          |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Validator false positives on legitimate ad-hoc microcopy    | Microcopy validator is advisory (not blocking); listed under best-practice risks    |
| Tree sprawl overwhelms small teams                          | Required subtrees stub acceptable (`_index.json` empty, README placeholder)          |
| Cross-reference validation breaks on partial extractions    | Validator treats unresolved refs as `important` gaps, not lint failures               |
| Icon/logo integrity checks reject multicolor assets         | Multicolor flag in `_index.json` skips `currentColor` rule                           |
| Dark-mode verification subjective                           | Require contrast-report entries per mode; best-practice risks flag background-only dark |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
