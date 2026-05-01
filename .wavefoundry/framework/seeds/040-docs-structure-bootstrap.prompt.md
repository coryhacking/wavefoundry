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
   - `docs/design/`
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
11. Seed `docs/plans/plan-template.md` as the consolidated change document template. The template must use the new single-document model:
    - `Change ID:` using the `<id-prefix>-change <slug>` format from the MCP `wave_new_change` tool when available, with `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind change --slug <slug>` as the CLI fallback
    - `## Rationale` — why the change is needed; must state a specific motivation a reviewer can understand without additional context
    - `## Requirements` — numbered behavioral requirements; each must be specific enough for an implementer to act on unambiguously
    - `## Scope` — problem statement, in-scope, out-of-scope
    - `## Acceptance Criteria` — testable outcomes
    - `## Tasks` — inline implementation checklist
    - `## Agent Execution Graph` — workstream table with owners and dependencies
    - `## Serialization Points` — shared files and integration gates
    - `## Affected architecture docs` — which hub or `docs/architecture/*` children this change may update (or `N/A` with rationale); names should align with `domain-map.md` when that file exists
    - `## Progress Log` — date/update/evidence table
    - `## Decision Log` — date/decision/reason/alternatives table
    - `## Session Handoff` — pointer to `docs/agents/session-handoff.md`
    - `## Risks` — risk and mitigation list
    - do NOT include a `## Spec Refs` section pointing at a separate `docs/specs/changes/` package
12. Ensure `docs/architecture/decisions/template.md` exists as a copy-paste skeleton for new `DEC-*` decision records, with sections aligned to `docs/architecture/decisions/README.md`; link the template from README when README is seeded or refreshed.
13. Seed `docs/design/design-language.md` when `docs/repo-profile.json` `design_system.design_evidence.detected` is `true`. The file must use the following stack-neutral canonical structure:
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
   Ensure `docs/design/index.md` exists and lists `design-language.md` with its status and purpose. Update `docs/README.md` to include a `docs/design/` row referencing "design language system" in its purpose field when `docs/design/design-language.md` is seeded.
   When seeding `docs/design/design-language.md`, also ensure `docs/workflow-config.json` includes a `design_review_triggers` list (with at least: `ui-surface-change`, `new-color-token`, `new-component-pattern`, `typography-change`, `hig-departure`) and a `require_design_review_for_ui_surface_changes: true` flag so the trigger contract is machine-readable without opening the design doc. When `docs/workflow-config.json` does not yet exist, these fields will be added during the `010` workflow-config seeding step; record them as required additions in the current assumptions of the active wave or session handoff so they are not forgotten.
14. Keep `docs/specs/` for durable long-lived behavior contracts that describe stable system boundaries. These are canonical reference docs consulted by implementation and review, not in-flight change tracking artifacts.
15. Do not create `docs/specs/changes/` as part of the new structure. In-flight change work belongs in the consolidated change document under `docs/plans/`.
16. Ensure seeded workflow and policy docs have canonical homes that distinguish durable operating policy from refreshable state snapshots.
17. When creating or refreshing `docs/contributing/build-and-verification.md`, include a **Wave framework pack upgrade verification** section (use that exact heading or an equivalent clearly titled subsection under **Verification**). The section must be actionable for any repository that vendors `.wavefoundry/framework/` and must document, at minimum:
    - **Bring the pack in:** either (a) place dated `wavefoundry-*.zip` at the **repository root** (from **Package Wavefoundry** — `docs/prompts/package-wavefoundry.md` when that prompt exists) and run **Upgrade wave framework** (legacy: **Upgrade wave context**) so `seed-160` **step 0** unpacks the lexicographically greatest zip, stages it under `.wavefoundry/framework/`, runs `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py`, and continues full reconciliation; or (b) merge or copy into `.wavefoundry/framework/` then run **Upgrade wave framework** (legacy: **Upgrade wave context**) without relying on a root zip.
    - **What step 0 ignores:** other archive names (for example `agent-workflows.zip`) and zips outside the repository root do not trigger automatic unpack — manual steps required when those are used.
    - **Framework tests:** `python3 -B .wavefoundry/framework/scripts/run_tests.py` (adapt the path only if the repo relocates the pack; keep **Framework Script Hygiene** alignment from `seed-050`).
    - **Docs gate:** **Agents:** prefer MCP **`wave_garden`** (when metadata needs refresh) then **`wave_validate`**. **Operators / CI / no MCP:** `.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint` (or the repo’s equivalent docs verification commands discovered from checked-in scripts).
    - **Review:** diff review of pack, hooks (`.claude/`, `.cursor/`, `.github/hooks/`, etc.), `docs/prompts/`, manifests — then commit.
    - **Cross-links:** point to `docs/prompts/upgrade-wavefoundry.md` and `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` for full behavior, edge cases (multiple zips, POSIX `ls|sort|tail` selection), and version guard; point to `docs/prompts/package-wavefoundry.md` when packaging is in scope.
    - **Product build scope:** state that product compile/format gates (for example `./debug`, `./reformat`) are not required solely for pack-only adoption unless implementation sources changed.
    - **`scripts/build_pack.py` semantics** (must match the checked-in script; document in `docs/prompts/package-wavefoundry.md` when that prompt exists): the zip filename uses **today’s local calendar date** in ISO form unless `--date` is passed; the single-letter suffix is the **successor of the highest letter already used** for that date among `wavefoundry-<date><letter>.zip` files in the **output** directory (first pack of the day is `a`; if only `…b.zip` already exists, the next is `…c.zip` — never choose a lower missing letter before the max); immediately before writing the archive, the script overwrites `framework/VERSION` with one line `<date><letter>` identical to the date+letter token in the zip basename.
    - **Bidirectional linking:** when seeding or refreshing `docs/prompts/upgrade-wavefoundry.md`, include a **Verification checklist** (or equivalent) subsection pointing back to this **Wave framework pack upgrade verification** section so operators have one ordered command list in `build-and-verification.md` and narrative detail in the upgrade prompt.
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
- `docs/design/design-language.md` seeded from `design_evidence` when `docs/repo-profile.json` `design_system.design_evidence.detected` is `true` (task 13)
- `docs/design/index.md` listing design artifacts with status and purpose (task 13)

Guardrails:

- Durable seeded docs should live in the topical folder that matches their role under `docs/`.
- Place refreshable artifacts in the topical folder that matches their role instead of a dedicated generated directory.
- Make regeneration expectations explicit in the artifact doc or nearby canonical docs when a file is refreshed by tooling.
- Do not encode project behavior only in refreshable artifacts when it should live in canonical docs.
- The seeded `docs/references/project-overview.md` should explain the project workflow, the major canonical docs, the generic agents or roles in use, any synthesized project personas, and how those participants collaborate across planning, implementation, review, and handoff.
- Do not treat docs seeding as satisfied by folder creation alone; ensure canonical policy/procedure docs are expected to hold actionable project-specific guidance.
- Do not create `docs/specs/changes/` — it is the old in-flight spec workspace and is superseded by the consolidated change document model. If it already exists in the repository, treat it as legacy material for baseline capture.
- The plan-template is the single source of truth for new change documents; do not seed any template that requires a separate spec package alongside the plan.
