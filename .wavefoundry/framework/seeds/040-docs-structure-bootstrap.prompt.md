# 040 - Docs Structure Bootstrap

Intent:

- Create or normalize the canonical docs and generated-artifact structure needed by the Wave Framework.

Tasks:

1. Create or update the canonical `docs/` structure.
2. Ensure architecture, plans, specs, references, reports, wave artifacts, agent journals, prompt manifests, and contributing docs have clear topical homes.
3. Ensure the target project has the expected canonical folder set in the repository, including as applicable:
   - `docs/architecture/`
   - `docs/architecture/decisions/`
   - `docs/contributing/`
   - `docs/design-system/`
   - `docs/plans/`
   - `docs/specs/`
   - `docs/references/`
   - `docs/agents/`
   - `docs/waves/`
   - `docs/agents/journals/`
4. Create or update machine-generated folders used by the Wave Framework:
   - `docs/waves/`
   - `docs/agents/journals/`
5. Ensure `docs/prompts/prompt-surface-manifest.json` exists as the machine-readable prompt-surface artifact.
6. Ensure `docs/agents/session-handoff.md` exists as the paused-work snapshot artifact.
7. Ensure `docs/agents/personas/` exists for synthesized persona docs.
8. Ensure `docs/references/project-overview.md` exists as the seeded project-orientation doc.
9. Ensure `docs/references/roles.md` exists and defines how canonical docs use metadata fields such as `Owner:`, `Status:`, and `Last verified:` (so `AGENTS.md` **Start Here** and `docs/contributing/docs-maintenance.md`, when seeded, can point at one definition).
10. Ensure `docs/references/project-context-memory.md` and other refreshable docs live in topical homes with clear regeneration semantics.
10a. Note `docs/references/codebase-map.md` as a generated orientation artifact (wave 1p5tl): a graceful-scaling, read-only map of the target project's own codebase, produced offline by `.wavefoundry/framework/scripts/gen_codebase_map.py` from the persisted graph + community-cluster artifacts and refreshed with the index build. It is the **index to the index** — it routes agents to the right area, then hands off to the `code_*` tools (`code_graph_community` via a stable `hub_node_id`, `code_outline` on key files) for depth. The seeded `docs/references/project-overview.md` orientation section and `AGENTS.md` **Start Here** should point at it so agents consult the map first. Do not hand-edit the generated file; it regenerates on index build (and on demand via `python3 .wavefoundry/framework/scripts/gen_codebase_map.py --root .`).
11. Seed `docs/plans/plan-template.md` as the consolidated change document template. The template must use the new single-document model:
    - `Change ID:` using the `<id-prefix>-change <slug>` format from the MCP `wave_new_change` tool when available, with `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind change --slug <slug>` as the CLI fallback
    - `## Rationale` — why the change is needed; must state a specific motivation a reviewer can understand without additional context
    - `## Requirements` — numbered behavioral requirements; each must be specific enough for an implementer to act on unambiguously
    - `## Scope` — problem statement, in-scope, out-of-scope
    - `## Acceptance Criteria` — testable outcomes written as stable checkbox items (`- [ ] AC-1: ...`)
    - `## AC Priority` — one row per Acceptance Criteria item with required / important / nice-to-have / not-this-scope
    - `## Tasks` — inline implementation checklist written as checkboxes (`- [ ] step`)
    - `## Agent Execution Graph` — workstream table with owners and dependencies
    - `## Serialization Points` — shared files and integration gates
    - `## Affected architecture docs` — which hub or `docs/architecture/*` children this change may update (or `N/A` with rationale); names should align with `domain-map.md` when that file exists
    - `## Progress Log` — date/update/evidence table
    - `## Decision Log` — date/decision/reason/alternatives table
    - `## Session Handoff` — pointer to `docs/agents/session-handoff.md`
    - `## Risks` — risk and mitigation list
    - do NOT include a `## Spec Refs` section pointing at a separate `docs/specs/changes/` package
12. Ensure `docs/architecture/decisions/template.md` exists as a copy-paste skeleton for new ADR files, with sections aligned to `docs/architecture/decisions/README.md`; link the template from README when README is seeded or refreshed. ADR files use the naming convention `<id>-adr <slug>.md` where `<id>` is a lifecycle ID from the same base-36 system as wave and change IDs (generate with `.wavefoundry/bin/lifecycle-id` or `lifecycle_id.py --prefix-only`).
13. Seed `docs/design-system/design-language.md` when `docs/repo-profile.json` `design_system.design_evidence.detected` is `true`. The file must use the following stack-neutral canonical structure:
   - **Title and metadata** — `# Design Language` header; `Owner:`, `Status:`, `Last verified:` metadata fields
   - **Overview** — one-paragraph project design philosophy statement; note the HIG fallback rule: when the project design language is silent on a decision, the platform's authoritative standard governs (Apple HIG for macOS/iOS, Material Design for Android, Material Design 3 for Flutter, for web: WCAG 2.1 AA + the detected component library's own design principles when a library is detected, or the project's own Component Patterns conventions documented in this file when no library is detected; platform-specific accessibility guidelines otherwise); intentional departures from the platform standard must be documented in the Platform/Framework Conventions section with explicit rationale
   - **Color Palette** — semantic color tokens grouped by role (primary, surface, state, accent, status); reference token files if `has_design_tokens` is `true`; for each color, include name, hex/RGB/semantic value, and usage context
   - **Typography Scale** — type ramp defining each role (heading, body, secondary, label, detail, monospaced) with size, weight, and usage guidance; derived from `typography_source` when `has_typography_system` is `true`
   - **Spacing and Layout** — spacing units, grid or layout rules, breakpoints (web) or safe-area / density-independent units (native); infer from the detected component library or project conventions
   - **Component Patterns** — if `has_storybook` is `true`, reference the Storybook catalog rather than enumerating components inline; otherwise enumerate key reusable component patterns with visual description, variant matrix, and usage notes; each pattern must include an HIG alignment note ("Follows HIG: [principle]") or a departure note ("Departure from HIG: [rationale]")
   - **Motion and Animation** — easing curves, duration scale, reduced-motion behavior; omit section (or stub with `N/A`) when the project has no animation system
   - **Platform/Framework Conventions** — one subsection per detected platform or framework (macOS/iOS, Android, Web, Flutter, etc.); each subsection must include:
     - the authoritative platform standard applied (e.g. "Apple Human Interface Guidelines 2024")
     - any documented departures from that standard with rationale
     - this is where intentional HIG departures are recorded — the HIG fallback rule makes this section mandatory whenever design language guidance is present
   - **Accessibility** — baseline accessibility contracts (color contrast target, minimum tap/click target size, VoiceOver/TalkBack support level); for web, state WCAG conformance level
   - **Document Maintenance** — when to update this file, who owns it, how it relates to `docs/repo-profile.json` `design_system` block
   When seeding, populate each section from the `design_evidence` output produced by `seed-030` and from direct inspection of the detected `ui_roots` source files. Record discovered values rather than generic placeholders wherever evidence exists. When evidence is absent for a section, write `TBD` with a one-line note explaining where to find the information.
   When `has_storybook` is `true`, add a cross-reference from the Component Patterns section to the Storybook catalog path and do not enumerate individual component specifications inline — the Storybook catalog is the single source of truth for component details; design-language.md documents design intent and token usage, not implementation details.
   Ensure `docs/design-system/index.md` exists and lists `design-language.md` with its status and purpose. Update `docs/README.md` to include a `docs/design-system/` row referencing "design language system" in its purpose field when `docs/design-system/design-language.md` is seeded.
   When seeding `docs/design-system/design-language.md`, also ensure `docs/workflow-config.json` includes a `design_review_triggers` list (with at least: `ui-surface-change`, `new-color-token`, `new-component-pattern`, `typography-change`, `hig-departure`) and a `require_design_review_for_ui_surface_changes: true` flag so the trigger contract is machine-readable without opening the design doc. When `docs/workflow-config.json` does not yet exist, these fields will be added during the `010` workflow-config seeding step; record them as required additions in the current assumptions of the active wave or session handoff so they are not forgotten.
14. **Design-system extraction contract.** Seed the machine-readable extraction contract under `docs/design-system/` as part of any install or upgrade that touches `docs/design-system/`. This is distinct from the narrative `design-language.md` (task 13): that file is operator-owned narrative; the extraction contract is a machine-readable surface agents read during UI implementation. The extraction contract must coexist with `design-language.md` — never overwrite its body.

    **Role of `DESIGN.md`:** `docs/design-system/DESIGN.md` is the agent-optimized Google Labs DESIGN.md distillation — under 400 lines, YAML front-matter holds token references, markdown body holds rationale distilled for agents. It is regeneratable. `design-language.md` is the operator-owned narrative and is never regenerated.

    **Core tree (create these paths during install/upgrade when absent; never overwrite if present):**
    ```text
    docs/design-system/
    ├── README.md                        # human entry; explains extraction tree and Storybook exclusion
    ├── DESIGN.md                        # agent-optimized distillation (regeneratable); NOT design-language.md
    ├── AGENTS.md                        # agent contract (see content rules below)
    ├── manifest.json                    # machine-readable extraction index
    ├── VALIDATION.md                    # checks run / outcomes
    ├── gaps.md                          # required gap log
    ├── tokens/
    │   ├── primitives.tokens.json       # DTCG raw values
    │   ├── semantic.tokens.json         # DTCG intent → primitive references
    │   ├── components.tokens.json       # optional convenience layer (label clearly)
    │   ├── modes/
    │   │   ├── light.tokens.json
    │   │   └── dark.tokens.json
    │   └── README.md
    ├── exports/
    │   ├── README.md                    # generated; explains subdirs + links to token-build pipeline plan
    │   ├── css/                         # stub — populated by token-build pipeline (out of scope this wave)
    │   ├── tailwind/                    # stub
    │   ├── ts/                          # stub
    │   └── json/                        # stub
    ├── components/
    │   ├── _index.json
    │   └── <component-name>/
    │       ├── spec.json
    │       ├── README.md
    │       ├── anatomy.md
    │       ├── tokens.json
    │       └── visuals/
    ├── foundations/
    │   ├── color.md
    │   ├── typography.md
    │   ├── spacing.md
    │   ├── radius.md
    │   ├── elevation.md
    │   └── motion.md
    ├── accessibility/
    │   ├── contrast-report.json
    │   └── README.md
    ├── version.json
    ├── source-map.json
    └── proposed-additions.md           # agent escape valve for new component proposals
    ```

    **Token naming convention (mandatory).** All token names must follow the `{category}.{subcategory}.{scale}.{variant}` dot-path schema (e.g. `color.primary.500`, `color.action.primary.background`, `spacing.4`, `radius.button`). First segment must start with a letter; numeric-only scale segments are allowed (e.g. `.500`, `.4`). When a source name must be normalized, record both in `source-map.json` under `normalizedFrom`.

    **`manifest.json` core schema.** Required fields: `schemaVersion` (semver string, e.g. `"1.0.0"`), `extractionVersion`, `extractedAt` (ISO-8601), `canonicalRoot` (must equal `"docs/design-system"`), `sourceStrategy` (enum: `figma-extract`, `repo-evidence-only`, `visual-bootstrap`, `hybrid`), `evidenceTypes` (array), `artifactCounts`, `modes` (must include `"light"` and `"dark"`), `validationSummary`. Reserved for Split C (accept but not require): `targetSurfaces`, `platformStandards`, `deprecations`.

    **Component `spec.json` schema.** Identity fields (required): `id`, `name`, `category`, `status`, `description`, `figma`, `codeConnect`, `anatomy`, `variants`, `props`, `slots`, `tokens`, `doNotUse`, `preferOver`. Behavioral fields (reserved for Split B; emit as `null`): `states`, `responsive`, `motion`, `accessibility`, `content`. Never omit behavioral fields — Split B populates them additively.

    **`gaps.md` contract.** Required at install. Categories (core): `tokens`, `components`, `assets`, `content`, `accessibility`, `responsive`, `motion`, `states`, `meta`. Severities: `critical`, `important`, `nice-to-have`. Summary count block at the top of the file is required (one line per severity). Each entry must include: category, severity, source searched, missing item, recommended action.

    **`source-map.json` core schema.** Each entry: `id` (dot-path token name or `<category>/<item-id>`), `sourceType` (`figma`|`code`|`visual`|`inferred`), `confidence` (`high`|`medium`|`low`), `sourceRef` (URI, path, or null), `normalizedFrom` (omit if unchanged), `platformHint` (optional, for Split C).

    **Extract, don't invent.** Missing-source values must be explicit `null` plus a `gaps.md` entry. Low-confidence items must also produce a `gaps.md` entry.

    **Two-phase gap policy.** Gaps are addressed in two phases — never in one undifferentiated pass:

    - **Phase 1 — strict extraction.** Record the real state of evidence. Every missing value becomes a `null` plus a `gaps.md` entry. No invented values; no best-practice substitutions. Low-confidence inferences are flagged. The output of Phase 1 is an honest extraction skeleton.
    - **Phase 2 — guided remediation.** Each `gaps.md` entry may include: (a) a *source-first fix* describing where the missing value could be found or authored (e.g. "Figma library — define primary color token"); (b) a *best-practice bootstrap option*, clearly labeled `proposed-from-best-practices`, that an operator can choose to adopt; (c) a *validation target* (WCAG AA contrast, 4.5:1 minimum for body text) when a gap has a testable quality bar; (d) a *dark-mode quality target* when the gap affects a token that has both light and dark variants.

    **Proposal guard.** Proposals from Phase 2 must never be silently merged into `semantic.tokens.json` or `components/_index.json`. They live in `gaps.md` or `docs/design-system/proposed-additions.md` until an operator explicitly promotes them. The `source-map.json` entry for any promoted item must record `confidence: low` until the operator raises it after verification.

    **`AGENTS.md` content contract.** The seeded `docs/design-system/AGENTS.md` must contain — not just exist:
    - Before building any UI component: check `components/_index.json`; use existing; if no match, append to `proposed-additions.md`.
    - Before writing any hard-coded value: reference semantic tokens only; never primitives, raw hex, raw px, raw z-index, raw duration.
    - Token naming follows dot-path convention.
    - Under 200 lines. Mark which sections Split B will extend (microcopy, icon lookup).

    **`docs/design-system/README.md` must state** that Storybook-specific outputs (`stories.meta.json`, MDX catalogs) are not part of this contract and are opt-in follow-ups.

    **`exports/README.md` must state** that the subdirectory contents are generated by a token-build pipeline (plan `12atj-feat design-token-build-pipeline`) and must not be hand-edited. Subdirectories are stubs until the pipeline is configured.

    **Coexistence rules (idempotent, apply on both install and upgrade):**
    - Append a cross-link row to `docs/design-system/index.md` listing new extraction artifacts with status `generated` — only when the row is not already present.
    - Add a `> See extracted contract: docs/design-system/manifest.json` pointer at the top of `design-language.md` when it does not already exist.
    - Never rewrite `design-language.md` or `docs/design-system/index.md` body content.

    **Rollback / clean re-extract path** (document in `docs/architecture/design-system.md` and in seed guidance):
    - Move existing `docs/design-system/<subtree>` to `docs/design-system/.backup/<ISO-date>/` before re-extracting.
    - Never auto-delete operator artifacts; always create the backup first.
    - Diff against the backup for operator review.
    - Write a `meta`-category gap entry when a backup is created.
    - Document backup cleanup guidance (backups are not auto-deleted; operators remove when satisfied).

    **`docs/workflow-config.json` extension.** When `design_review_triggers` is already present (seeded by task 13 for `design-language.md` changes), extend it to also include `token-file-change`, `manifest-change`, `spec-json-change` so that agent writes to `docs/design-system/**` trigger the same design-review gate.

    **Architecture doc.** Seed `docs/architecture/design-system.md` describing: extraction philosophy (machine-readable vs narrative), where `design-language.md` fits, when extraction regenerates vs operator edits, relationship between `docs/design-system/` and the semantic index, token-build pipeline stub and follow-on plan, rollback path, backup cleanup. Cross-link from `docs/ARCHITECTURE.md` and from `docs/design-system/index.md`.

    **Storybook exclusion statement** must appear in both `seed-040` guidance and in the generated `docs/design-system/README.md`.

    **Split B — pattern and surface depth (wave `12arn-enh design-system-pattern-and-surface-depth`).** Adds the following to the core tree. Create these paths when the Split B wave is admitted and implemented; all are merge-safe stubs:

    ```text
    docs/design-system/
    ├── patterns/
    │   ├── navigation/   _index.json + README.md
    │   ├── feedback/     _index.json + README.md
    │   ├── data/         _index.json + README.md
    │   └── trust/        _index.json + README.md
    ├── state-patterns/
    │   ├── _index.json + README.md
    │   └── {loading,empty,error,success}/  _index.json + README.md
    ├── validation-patterns/
    │   ├── _index.json + README.md
    │   └── required-field.md, format-validation.md, async-validation.md,
    │       error-display.md, success-confirmation.md
    ├── content/
    │   ├── README.md, voice.md, microcopy.json, formatting.md, i18n.md,
    │   │   rtl-layout.md, locale-formats.md, brand-legal.md
    ├── foundations/   (extend; add)
    │   └── shell.md, density.md, responsive.md, grid.md, z-index.md,
    │       iconography.md, data-visualization.md, media-motion.md
    ├── accessibility/ (extend; add)
    │   └── focus.md, keyboard.md, screen-reader.md
    ├── tokens/        (extend; add)
    │   └── borders.tokens.json, focus.tokens.json, z-index.tokens.json, motion.tokens.json
    ├── icons/         _index.json + README.md + svg/ + exports/
    ├── illustrations/ _index.json + README.md
    ├── logos/         _index.json + README.md
    ├── images/        _index.json + README.md + REVIEW.md + raw/
    └── skills/        README.md + {nine SKILL.md files}
    ```

    `spec.json` behavioral fields (`states`, `responsive`, `motion`, `accessibility`, `content`) are populated — not added — by Split B. The core seed emits them as `null`; Split B populates shapes where source evidence exists; keys are never removed.

    `gaps.md` extended categories (Split B adds): `patterns`, `navigation`, `shell`, `feedback`, `data`, `trust`, `i18n`, `locale`. A **Best-practice risks** section is also required — list patterns that violate design-system best practices (raw hex in components, missing reduced-motion, weak contrast, dark-mode as background-only swap, inconsistent validation timing, ad-hoc microcopy, raw z-index escalation, chart colors inaccessible for color-vision deficiencies, missing keyboard escape from overlays). Advisory unless directly blocking ACs.

    **Split B semantic validators** (implemented in `wave_lint_lib/design_system_surface_validators.py`): WCAG contrast check from `accessibility/contrast-report.json`; extended mode parity for new extended token files; reduced-motion check when `motion.tokens.json` has non-null duration tokens; icon sanity (square viewBox, `currentColor` unless multicolor); keyboard pattern presence check; state coverage check.

    **Split C — bootstrap and governance (wave `12arn-enh design-system-bootstrap-and-governance`).** Adds the following to the core tree:

    ```text
    docs/design-system/
    └── platforms/   README.md + per-surface subdirectories
    ```

    **`sourceStrategy` full semantics (Split C):** `figma-extract` — primary evidence is Figma variables/styles/components. `repo-evidence-only` — primary evidence is checked-in code. `visual-bootstrap` — primary evidence is screenshots/reference URLs/decks (no-DS path; outputs are non-normative until explicit operator promotion). `hybrid` — combination; `evidenceTypes` lists all active sources.

    **`manifest.json` Split C fields:** `targetSurfaces` (required; infer from `docs/repo-profile.json` ui_roots + native folder inspection; unknown surfaces → gaps); `platformStandards[]` (required per declared surface; fields: `surface`, `standard`, `referenceVersion` (required — freeform string for HIG drift tracking), `departures`); `deprecations` (optional array of `{kind, id, supersededBy?, sunset?, reason}`); `productClasses` (records not-applicable classes explicitly).

    **No-design-system bootstrap path (Split C):** when inventory finds no coherent design-system source, collect substitute evidence (screenshots, brand PDFs, reference URLs) under `docs/design-system/images/raw/` or referenced in `manifest.json.provenance`. Emit the standard skeleton with all semantic files as explicit `null`. Non-normative proposals appear in `gaps.md` or an appendix, clearly tagged `proposed-from-best-practices`. Never merge proposals into `semantic.tokens.json` without explicit operator promotion. `docs/design-system/README.md` must state that visual-bootstrap outputs require human sign-off before implementation waves treat tokens as normative.

    **Bootstrap evidence confidence:** all items from `visual-bootstrap` sources default to `low` confidence in `source-map.json`. Low-confidence items require a `gaps.md` entry. To present bootstrap items as higher-trust, the operator must add an acknowledgment line in `manifest.json.provenance.acknowledgments`.

    **Per-surface deltas:** token or component differences by surface live in `platforms/<surface>/` with markdown + optional token overrides. `manifest.json.platformStandards[].overrides` points to the per-surface path. The subtree holds narrative; the manifest entry is the machine index.

    **Deprecation fields — `components/_index.json`:** each entry may include `deprecated: true`, `supersedes: <id>`, `sunset: <ISO-8601 date>`. Extraction must preserve these across runs — never strip them.

    **Conditional product-class extensions (Split C; only when inventory signals the class):**
    - Email-heavy: `patterns/email/_index.json` with `maxWidth`, `safeFonts`, `darkModeStrategy`, `supportedClients`, `imageHandling`.
    - Print/PDF: `patterns/print/_index.json` with `pageSize`, `margins`, `colorMode`, `bleed`, `fontEmbedding`.
    - Offline-first: `patterns/offline/_index.json` with `offlineIndicator`, `conflictResolution`, `syncStates`, `cacheStrategy`.
    - Notification-heavy: `patterns/notifications/_index.json` with `channels`, `priorityLevels`, `groupingRules`, `sounds`, `badgeBehavior`.

    **Split C governance validators** (implemented in `wave_lint_lib/design_system_governance_validators.py`): `sourceStrategy` enum; `targetSurfaces` non-empty; `platformStandards[].referenceVersion` present per surface; visual-bootstrap proposal guard (no `proposed-from-best-practices` in `semantic.tokens.json`); deprecated component must have `supersededBy` or `sunset`; `platformStandards[].overrides` paths exist.

15. Keep `docs/specs/` for durable long-lived behavior contracts that describe stable system boundaries. These are canonical reference docs consulted by implementation and review, not in-flight change tracking artifacts.
15. Do not create `docs/specs/changes/` as part of the new structure. In-flight change work belongs in the consolidated change document under `docs/plans/`.
16. Ensure seeded workflow and policy docs have canonical homes that distinguish durable operating policy from refreshable state snapshots.
17. When creating or refreshing `docs/contributing/build-and-verification.md`, include a **Wave framework pack upgrade verification** section (use that exact heading or an equivalent clearly titled subsection under **Verification**). The section must be actionable for any repository that vendors `.wavefoundry/framework/` and must document, at minimum:
    - **Bring the pack in:** either (a) place a semver `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` at the **repository root**, in `~/.wavefoundry/`, or in `~/.wavefoundry/dist/` (from **Package Wavefoundry** — `docs/prompts/package-wavefoundry.prompt.md` when that prompt exists) and run **Upgrade wave framework** (legacy: **Upgrade wave context**) so `seed-160` **step 0** adopts the highest semver zip, stages it under `.wavefoundry/framework/`, runs `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py`, and continues full reconciliation; or (b) merge or copy into `.wavefoundry/framework/` then run **Upgrade wave framework** (legacy: **Upgrade wave context**) without relying on an adopted zip.
    - **What step 0 ignores:** archives with non-matching names and zips outside the repository root / `~/.wavefoundry/` / `~/.wavefoundry/dist/` search paths do not trigger automatic unpack — manual steps required when those are used.

    - **Docs gate:** **Agents:** prefer MCP **`wave_garden`** (when metadata needs refresh) then **`wave_validate`**. **Operators / CI / no MCP:** `.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint` (or the repo’s equivalent docs verification commands discovered from checked-in scripts).
    - **Review:** diff review of pack, hooks (`.claude/`, `.cursor/`, `.github/hooks/`, etc.), `docs/prompts/`, manifests — then commit.
    - **Cross-links:** point to `docs/prompts/upgrade-wavefoundry.prompt.md` and `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` for full behavior, edge cases (multiple zips and multi-location semver selection), and version guard; point to `docs/prompts/package-wavefoundry.prompt.md` when packaging is in scope.
    - **Product build scope:** state that product compile/format gates (for example `./debug`, `./reformat`) are not required solely for pack-only adoption unless implementation sources changed.
    - **`scripts/build_pack.py` semantics** (must match the checked-in script; document in `docs/prompts/package-wavefoundry.prompt.md` when that prompt exists): `--version MAJOR.MINOR.PATCH` is required and packaging is blocked below `1.0.0`; the zip filename is `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` in `~/.wavefoundry/dist/` by default unless `--output` is passed; `<build>` is the rightmost 4 characters of the lifecycle prefix; immediately before writing the archive, the script overwrites `framework/VERSION` with `MAJOR.MINOR.PATCH+<build>`, requires manifest `framework_revision` consistency unless `--skip-manifest-check` is used, then updates and compacts `framework/index/` before zipping.
    - **Bidirectional linking:** when seeding or refreshing `docs/prompts/upgrade-wavefoundry.prompt.md`, include a **Verification checklist** (or equivalent) subsection pointing back to this **Wave framework pack upgrade verification** section so operators have one ordered command list in `build-and-verification.md` and narrative detail in the upgrade prompt.
    - **`Git commits` policy:** include a **Git commits** subsection (operator-owned; agents do not run `git commit` unless the operator explicitly instructs in the **current** request) aligned with `seed-050` (**Operator-owned `git commit`**) and the **Git commits** section in `AGENTS.md`; the subsection must state that agents do not infer commit approval from broad implementation approval and must present or confirm the exact commit scope before finalizing a reviewed commit. Backfill when the file exists but omits this contract.

Required target-repo outputs:

- canonical docs index structure
- wave, journal, prompt-manifest, and other refreshable artifact homes
- persona directory
- project overview reference doc
- `docs/references/roles.md` for doc metadata conventions
- `docs/architecture/decisions/template.md` when decisions/README is in scope
- execution-plan and refreshable-artifact anchor files
- canonical homes for project-specific workflow, review, verification, and operational procedure docs
- `docs/contributing/build-and-verification.md` including **Git commits** (operator-owned policy per task 17) and **Wave framework pack upgrade verification** when the repository vendors the wave-context framework pack (task 17)
- `docs/design-system/design-language.md` seeded from `design_evidence` when `docs/repo-profile.json` `design_system.design_evidence.detected` is `true` (task 13)
- `docs/design-system/index.md` listing design artifacts with status and purpose (task 13)
- `docs/design-system/` extraction contract tree (task 14): `manifest.json`, `AGENTS.md`, `DESIGN.md`, `gaps.md`, `VALIDATION.md`, `README.md`, token files, exports stubs + README, component index, foundations, accessibility, `docs/design-system/` meta files
- `docs/architecture/design-system.md` hub doc (task 14)

Guardrails:

- Durable seeded docs should live in the topical folder that matches their role under `docs/`.
- Place refreshable artifacts in the topical folder that matches their role instead of a dedicated generated directory.
- Make regeneration expectations explicit in the artifact doc or nearby canonical docs when a file is refreshed by tooling.
- Do not encode project behavior only in refreshable artifacts when it should live in canonical docs.
- The seeded `docs/references/project-overview.md` should explain the project workflow, the major canonical docs, the generic agents or roles in use, any synthesized project personas, and how those participants collaborate across planning, implementation, review, and handoff.
- Do not treat docs seeding as satisfied by folder creation alone; ensure canonical policy/procedure docs are expected to hold actionable project-specific guidance.
- Do not create `docs/specs/changes/` — it is the old in-flight spec workspace and is superseded by the consolidated change document model. If it already exists in the repository, treat it as legacy material for baseline capture.
- The plan-template is the single source of truth for new change documents; do not seed any template that requires a separate spec package alongside the plan.
