# 010 - Init Wave Framework (Shortcut)

**Primary:** **`Init wave framework`**. **Backwards-compatible:** **`Install Wavefoundry`**, **`Install wave framework`**, **`Init wave context`**, **`Install wave context`** — identical behavior; keep accepting them from operators and older docs.

Use this when you want a single command-style request such as:

- `Init wave framework` (legacy: `Init wave context`)
- `Install wave framework` (legacy: `Install wave context`; bootstrap alias when the repository has not yet been seeded into any wave-context state)

Intent:

- Initialize a project in the target repository with the Wave Framework prompt operating system.
- Treat init as the first-phase detector for installed wave-context state in the repository before any upgrade handoff happens.
- When legacy pre-wave corpora are present, capture them directly into `wave-0` (reserved prefix `00000 wave-zero-plans-and-specs`) and close it as the baseline anchor before proceeding.
- Establish the project's first installed wave layer as `wave-0` (recorded in the repository).
- For `wave-0` (the first installed wave anchor), use the reserved baseline prefix: `00000 wave-zero-plans-and-specs`.
- Plant a repo-local Wave Framework layer that can later be upgraded, extended, and re-synthesized from evidence in the repository.
- Generate repo-local outputs that support wave planning, agent journals, project-specific persona agents, and prompt-surface evolution.
- If the repository starts from a legacy `project-context` install, OpenSpec material, or other custom spec/change corpora, capture that footing in a closed `00000 wave-zero-plans-and-specs` baseline.

Init expectations:

- treat **project understanding** as a first-class bootstrap output: inventory manifests and tree structure for cheaply rediscoverable facts, capture only **non-obvious** constraints and routing in `AGENTS.md`, and label genuine unknowns explicitly instead of guessing
- treat this as a full bootstrap of the project's canonical docs, topical refreshable artifact homes, prompt surface, agent entry surface, and wave-aware collaboration policy (checked into the repository under `docs/` and related roots)
- backfill missing repo-local outputs instead of leaving them for a later run
- generate the repo-local system in a way that can later be refreshed by **`Upgrade wave framework`** (legacy: **`Upgrade wave context`**)
- inspect whether the repository has no prior context, legacy `project-context` artifacts, OpenSpec-style corpora, other custom spec/change folders, or an installed Wave Framework layer
- treat the following as legacy in-flight corpora when they exist: `docs/plans/active/`, `docs/plans/completed/`, `docs/specs/changes/`, `docs/exec-plans/`, `docs/product-specs/changes/`; these are the old execution-plan and spec-package workspaces and should be captured in the baseline legacy wave; after baseline capture, remove the empty legacy workspace directories (`docs/exec-plans/`, `docs/product-specs/`, `docs/gaps/`, `docs/performance/`) rather than leaving them as empty shells
- if a `docs/tasks.md` pre-wave scratch backlog exists with no wave admission, note it in the `## Wave Summary` and remove it after baseline capture; if items in it are worth preserving, promote them to `docs/references/tech-debt-tracker.md` first
- if any active plans excluded from the baseline are explicitly superseded by the wave-context migration itself (e.g. a plan whose goal was to validate the old framework), record them with `Change Status: \`superseded\`` in wave-0 rather than `deferred`; do not require superseded plans to be "admitted into a future wave" — record the supersession rationale in the change description and update the plan file status to `superseded` before removing it
- do NOT treat `docs/specs/*.md` durable behavior contracts as legacy corpora — these are canonical long-lived reference docs that describe stable system boundaries and should remain in place after init
- after the legacy baseline wave is captured and closed, clear in-flight plan docs from `docs/plans/` (leaving `docs/plans/plan-template.md` in place) and ensure `docs/plans/plan-template.md` is seeded with the consolidated change document template so it is available for future use
- for repositories with no prior context (no docs, no plans, no specs), skip baseline wave creation and proceed directly to the bootstrap steps; the result should be the same required output set minus the baseline wave artifacts
- if legacy pre-wave corpora are detected, execute the full baseline capture and closure sequence:
 1. Create the baseline wave folder using `00000 wave-zero-plans-and-specs` as the `wave-id`
 2. Give it a `Title` that starts with `Legacy` (for example `Legacy` or `Legacy plans and specs`)
 3. Write `docs/waves/00000 wave-zero-plans-and-specs/wave.md` as the single artifact holding all baseline content — keep everything in this one file; do not create subdirectories like `legacy/` or `evidence/` inside the wave folder
 4. `wave.md` must include: all required wave anchors, a `## Corpus` section with a table of captured plans (change ID, file path, kind, title), a `## Wave Summary` that records what was detected, what was seeded, and which in-flight plans were excluded, one `Change ID` per captured plan/change all at `complete` status, explicit review checkpoints with real findings, and journal refs
 5. **Physically move** completed plan files from `docs/plans/completed/` into `docs/waves/00000 wave-zero-plans-and-specs/` and record their new paths in the `## Corpus` table; `docs/plans/completed/` must be empty after baseline capture; do not merely index them at their original location; also capture any spec/change packages from `docs/specs/changes/` the same way
 6. Any active in-flight plans that are not yet complete must stay in `docs/plans/` and be explicitly excluded from the baseline with a note in `## Wave Summary`
 7. For each applicable change type in the baseline, run the appropriate agent review lane (architecture, QA, docs-contract, security, performance) and document actual findings — not pass/fail placeholders — as review checkpoint entries in `wave.md`
 8. Synthesize journal lessons from the baseline corpus into agent and persona journal files; each journal must have real `## Observations` and `## Distillation` bullets drawn from the captured plans, not generic placeholders
 9. Update core memory files with durable lessons that recur across the baseline corpus:
 - `docs/references/project-context-memory.md` — reusable workflow guidance discovered during baseline
 - `docs/RELIABILITY.md` — reliability patterns, catch-up policies, recovery behaviors introduced by baseline changes
 - `docs/ARCHITECTURE.md` — any architectural decisions or module boundaries established by baseline changes
 - `docs/QUALITY_SCORE.md` — quality posture changes introduced by baseline changes
 10. Promote persona agent guidance from baseline evidence when the corpus reveals user-facing patterns; refresh escalation conditions and review triggers for agent roles when the corpus establishes new operating patterns
 11. Archive all reports from `docs/reports/` that were generated during the pre-wave period into the wave folder alongside the plan files. Move each report file into `docs/waves/00000 wave-zero-plans-and-specs/`, add a `## Reports` section to `wave.md` summarizing key findings from each archived report, and leave `docs/reports/` empty. The wave folder is the permanent archive; `docs/reports/` is a staging area only.
 12. Mark the wave `Status: completed` only after all of the above steps are done; do not treat baseline capture as complete until reviews, journals, core-doc promotions, and report archival are explicitly recorded
- if the repository already has an installed Wave Framework layer, hand off to **`Upgrade wave framework`** (legacy: **`Upgrade wave context`**) after detection rather than bypassing init-phase classification
- synthesize repo-local policies and procedures from evidence in the repository with enough operational detail that the seeded docs are usable without reopening the shared pack for routine execution

Execution flow:

1. Read and apply `seed-020`.
2. Build the evidence base from the repository using `seed-030`.
3. Detect whether baseline legacy-corpus capture is required and, when it is, create and close the reserved legacy baseline wave.
4. Bootstrap docs and topical artifact structure using `seed-040`.
5. Create agent entry files and native role surfaces using `seed-050`.
6. Run `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py` immediately after step 5 so tracked platform hook/config surfaces are materialized before verification.
7. Map architecture, boundaries, trust/data seams, integration contracts, build seams, hotspots, and safe wave partitions using `seed-060` (see that prompt’s required outputs under `docs/architecture/` and `docs/ARCHITECTURE.md` hub).
8. Seed design language artifacts when `design_evidence.detected` is `true` in `docs/repo-profile.json` (populated by step 2 / `030`): create `docs/design-system/design-language.md` using the canonical structure defined in `seed-040` task 13; ensure `docs/design-system/index.md` exists; update `docs/README.md` `docs/design-system/` row to include "design language system". When `design_evidence.detected` is `false` (CLI-only, no UI roots found), create `docs/design-system/index.md` with a stub noting no UI surface was detected and skip seeding `design-language.md`.

 **Design-system extraction contract backfill (always run, regardless of `design_evidence.detected`).** After step 8, run the following merge-safe backfill. For each path, create it with an empty placeholder only when it does not already exist — never delete or overwrite existing operator files. Completing this step means all boxes below are checked:

 ```
 - [ ] docs/design-system/README.md
 - [ ] docs/design-system/DESIGN.md
 - [ ] docs/design-system/AGENTS.md (see content contract in seed-040 task 14)
 - [ ] docs/design-system/manifest.json (stub: sourceStrategy "repo-evidence-only", empty artifactCounts)
 - [ ] docs/design-system/VALIDATION.md
 - [ ] docs/design-system/gaps.md (stub header + empty category sections + summary counts)
 - [ ] docs/design-system/tokens/primitives.tokens.json
 - [ ] docs/design-system/tokens/semantic.tokens.json
 - [ ] docs/design-system/tokens/components.tokens.json
 - [ ] docs/design-system/tokens/modes/light.tokens.json
 - [ ] docs/design-system/tokens/modes/dark.tokens.json
 - [ ] docs/design-system/tokens/README.md
 - [ ] docs/design-system/exports/README.md (explain subdirs + link to plan 12atj-feat design-token-build-pipeline)
 - [ ] docs/design-system/exports/css/
 - [ ] docs/design-system/exports/tailwind/
 - [ ] docs/design-system/exports/ts/
 - [ ] docs/design-system/exports/json/
 - [ ] docs/design-system/components/_index.json
 - [ ] docs/design-system/foundations/color.md
 - [ ] docs/design-system/foundations/typography.md
 - [ ] docs/design-system/foundations/spacing.md
 - [ ] docs/design-system/foundations/radius.md
 - [ ] docs/design-system/foundations/elevation.md
 - [ ] docs/design-system/foundations/motion.md
 - [ ] docs/design-system/accessibility/contrast-report.json
 - [ ] docs/design-system/accessibility/README.md
 - [ ] docs/design-system/version.json
 - [ ] docs/design-system/source-map.json
 - [ ] docs/design-system/proposed-additions.md
 ```

 **Split B paths** (create when wave `12arn-enh design-system-pattern-and-surface-depth` is admitted; same merge-safe rule):
 ```
 - [ ] docs/design-system/patterns/navigation/_index.json + README.md
 - [ ] docs/design-system/patterns/feedback/_index.json + README.md
 - [ ] docs/design-system/patterns/data/_index.json + README.md
 - [ ] docs/design-system/patterns/trust/_index.json + README.md
 - [ ] docs/design-system/state-patterns/_index.json + README.md + {loading,empty,error,success}/_index.json + README.md
 - [ ] docs/design-system/validation-patterns/_index.json + README.md + five .md files
 - [ ] docs/design-system/content/README.md + voice.md + microcopy.json + formatting.md + i18n.md + rtl-layout.md + locale-formats.md + brand-legal.md
 - [ ] docs/design-system/foundations/{shell,density,responsive,grid,z-index,iconography,data-visualization,media-motion}.md
 - [ ] docs/design-system/accessibility/{focus,keyboard,screen-reader}.md
 - [ ] docs/design-system/tokens/{borders,focus,z-index,motion}.tokens.json
 - [ ] docs/design-system/icons/_index.json + README.md + svg/
 - [ ] docs/design-system/illustrations/_index.json + README.md
 - [ ] docs/design-system/logos/_index.json + README.md
 - [ ] docs/design-system/images/_index.json + README.md + REVIEW.md + raw/
 - [ ] docs/design-system/skills/README.md + nine SKILL.md files
 ```

 **Split C paths** (create when wave `12arn-enh design-system-bootstrap-and-governance` is admitted):
 ```
 - [ ] docs/design-system/platforms/README.md
 ```
 Also extend `manifest.json` with: `targetSurfaces` (infer from `docs/repo-profile.json` ui_roots; unknown → gap), `platformStandards[]` per surface (with `referenceVersion` required), `deprecations` (optional). See `seed-040` task 14 Split C section for full field shapes.

 After backfill, apply coexistence rules (idempotent):
 - Append a cross-link row to `docs/design-system/index.md` for extraction artifacts (status: `generated`) — only if not already present.
 - Add `> See extracted contract: docs/design-system/manifest.json` at the top of `design-language.md` — only if that pointer does not already exist and `design-language.md` is present.
9. Establish quality, reliability, security, performance, and debt posture using `seed-070`.
10. Create docs gate and related mechanics using `seed-080` and `seed-090`.
11. Generate the repo-local prompt surface using `seed-100`.
12. Bootstrap wave artifacts using `seed-110`.
13. Synthesize project-specific personas using `seed-120`.
14. Bootstrap journals and memory policy using `seed-130`.
15. Register ongoing drift and reindex expectations using `seed-140`.

Execution contract (complete seed, not partial):

- Run steps **1→15 in order** unless early classification in steps **1–3** determines the repository **already has an installed Wave Framework layer** — then **hand off to `Upgrade wave framework`** (legacy: **`Upgrade wave context`**) (`seed-160`) instead of re-running bootstrap as init.
- When **legacy baseline capture** applies, finish **Init expectations** steps for `00000 wave-zero-plans-and-specs` **before** declaring init complete; for greenfield repos, skip baseline creation but still execute **4→13** so the full output set exists.
- **Authoritative detail per artifact class** lives in the numbered pack prompt for that step (for example `seed-040` for topical `docs/` layout, `plan-template.md` section model, **Wave framework pack upgrade verification** and **Git commits** inside `docs/contributing/build-and-verification.md` (task 16), `seed-050` for `AGENTS.md` (including **Git commits (operator-owned)**), thin pointers / `.claude/settings.json` hook, `seed-080` / `seed-090` for wrappers and gate contract, `seed-100` for prompt semantics and manifest registration). If `010` and a step prompt disagree on a file, **follow the step prompt** for that file.
- **Mechanical completeness when the pack includes `scripts/docs_lint.py`:** init is **not finished** until the docs gate passes: **agents with MCP attached must get a successful `wave_validate`** (use `wave_garden` first when metadata timestamps need refresh); **hosts without MCP** must run **`.wavefoundry/bin/docs-lint` exit 0** from the repository root after **`.wavefoundry/bin/`** launchers exist. Seed **`docs/prompts/prompt-surface-manifest.json`** and **`docs/workflow-config.json`** so they satisfy the gate:
 - **Manifest** must include at least `schema_version`, `seed_framework_source` (must match `prompt_generation.seed_framework_source` in workflow config — both typically `.wavefoundry/framework`), **`framework_revision`** (string equal to `.wavefoundry/framework/VERSION` for the pack that seeded or last upgraded the repo — required by the docs gate, whether checked via MCP **`wave_validate`** or **`.wavefoundry/bin/docs-lint`**, and by `seed-160` **version guard**), `generated_artifacts` listing refreshable roots the gate tracks (at minimum the manifest path, `docs/agents/session-handoff.md`, `docs/waves/`, `docs/agents/journals/`, `docs/agents/personas/`), and `public_prompt_surface` with a **shortcut and `doc` path for every public Wave Framework prompt file** under `docs/prompts/` that corresponds to an **`AGENTS.md` shortcut phrase** (keep duplicates out; align with `docs/prompts/index.md`).
 - **Workflow config** must include top-level sections **`wave_implement`**, **`agent_memory`**, **`project_persona_generation`**, **`prompt_generation`** (nested `seed_framework_source` aligned with the manifest), **`factor_review_policy`**, and **`persona_review_policy`** — plus **`lifecycle_id_policy`** (see required outputs below) so lifecycle ID epoch and optional hour offset are project-owned in `docs/workflow-config.json` and match `lifecycle_id.py` — plus whatever additional keys this project needs (`lifecycle_mode`, `enabled_agent_roles`, `agent_platform_generation`, `review_policies`, module roots, `indexing`, etc.) so wave execution, reviews, and optional indexing extensions are configurable without forking prompts.
- Copy or keep the **entire** `.wavefoundry/framework/scripts/` tree (including `docs_lint.py`, `docs_gardener.py`, `lifecycle_id.py`, and supporting modules) in the target repository whenever the repo vendors the pack; **`lifecycle_id.py` must exist** before relying on scripted IDs.
- Init must explicitly run `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py` after the agent-entry bootstrap so tracked platform hook/config surfaces are rendered deterministically rather than being left implicit.
- Hook rendering may create Copilot agent files under `.github/hooks/`, but it must not create or modify GitHub Actions workflows under `.github/workflows/` and must not touch local git hooks under `.git/hooks/`.
- **Final step — restart MCP and update indexes:** After init is complete and the docs gate passes, instruct the operator to restart the MCP server so the newly installed server picks up all rendered surfaces, then run `wave_index_build(content="docs", mode="update")` (or both project and framework layers when self-hosting) to ensure the semantic index reflects the installed docs. Present this as a required handoff step, not optional cleanup.

Operator summary (required handoff):

After init completes successfully, deliver a concise **high-level overview** to the human operator (chat summary or short follow-up doc). This is not a dump of every file path; it orients them to **what was installed**, **how to work next**, and **where configuration lives**.

Include the following topics in plain language:

1. **What was seeded** (see **Required outputs** below for exact paths)
 - Canonical `docs/` tree mapped by `docs/README.md` (architecture, plans, contributing, specs index when applicable, waves, agent roles, journals, personas, refreshable artifacts).
 - Entry surfaces: `AGENTS.md` (shortcut table, stage gate, **Git commits (operator-owned)** per `seed-050`, implementation guard when product code exists) plus thin pointers that route to canonical docs.
 - Whether a **legacy baseline wave** was created at `docs/waves/00000 wave-zero-plans-and-specs/`; normal delivery waves use new IDs from `lifecycle_id.py`.
 - Native agent affordances when generated (e.g. `.codex/skills/agent-role-<role>/`, `.claude/agents/`) aligned with `docs/agents/platform-mapping.md` and `docs/workflow-config.json`.

2. **High-level workflow**
 - Default change path: `docs/contributing/change-workflow.md` and, for non-trivial product work, the **stage gate** and **Implementation guard** in `AGENTS.md` (consolidated change doc + readiness before first product-code edit unless waived).
 - Typical public phrase sequence for delivery: **Plan feature** → **Create wave** → **Add change to wave** → **Prepare wave** → **Implement wave** / **Implement feature** → **Review wave** → **Close wave** / **Finalize feature**; **Pause wave** when context must be parked in `docs/agents/session-handoff.md`.
 - Pointer to the repo-local lifecycle companion: `docs/contributing/feature-wave-lifecycle-overview.md` (and shared model `.wavefoundry/framework/seeds/001-feature-wave-framework-overview.md`).

3. **Commands and trigger phrases**
 - The operator uses natural-language shortcuts listed in `AGENTS.md` and `docs/prompts/index.md` (for example **`Init wave framework`** / **`Init wave context`**, **`Upgrade wave framework`** / **`Upgrade wave context`**, **`Start dashboard`**, **`Stop dashboard`**, **`Restart dashboard`**, `Plan feature`, `Prepare wave`, `Close wave`).
 - **`Install wave framework`** (legacy: **`Install wave context`**) is a convenience alias: init runs detection first; if the repo is already seeded, hand off to **`Upgrade wave framework`** (legacy: **`Upgrade wave context`**).
 - Lifecycle IDs: `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind wave --slug <slug>` (and change IDs per seeded policy).

4. **Agents and personas**
 - **Generic roles**: canonical specs under `docs/agents/README.md` and individual role files (planner, implementer, wave-coordinator, code-reviewer, architecture-reviewer, qa-reviewer, security-reviewer, docs-contract-reviewer, performance-reviewer, release-reviewer, and `council-moderator` when `wave_review` is enabled, plus factor-review agents only when factors are `applicable` in `docs/repo-profile.json` and seeded canonically under `docs/agents/factor-<nn>-<name>.md` with `Role:` plus `Category: factor` and thin host wrappers rendered for enabled platforms).
 - **Personas**: `docs/agents/personas/` when synthesized; review triggers and gating from `persona_review_policy` in `docs/workflow-config.json` and `docs/contributing/agent-team-workflow.md`.
 - **Journals**: `docs/agents/journals/` for durable lessons; link from waves at close per `docs/prompts/close-wave.prompt.md` and `docs/contributing/review-and-evals.md`.

5. **Documentation setup and quality gates**
 - How to navigate docs: start with `docs/README.md`, `docs/references/project-overview.md`, and `docs/prompts/index.md`.
 - After init, run project verification from `docs/contributing/build-and-verification.md` (includes docs gate): **prefer MCP `wave_garden` (if needed) then `wave_validate`**; **CLI fallback** when MCP is not attached: **`.wavefoundry/bin/docs-gardener`** and **`.wavefoundry/bin/docs-lint`** (launchers under `.wavefoundry/bin/` pointing at `.wavefoundry/framework/scripts/`).
 - Framework script hygiene: `__pycache__` cleanup after framework script runs (the test suite is a development-only artifact in the Wavefoundry source repo and is not included in the distribution pack).

6. **Important configuration**
 - **`docs/workflow-config.json`**: lifecycle mode, `lifecycle_id_policy` (epoch and optional offset for `lifecycle_id.py`), `wave_implement` (readiness before implement, auto-run when missing), `review_policies`, `factor_review_policy`, `persona_review_policy`, `wave_review` when the framework-standard council model is enabled, memory and prompt-generation settings—this is the primary machine- and human-readable policy knob for waves and reviews.
 - **`docs/repo-profile.json`**: project archetype and traits, supported agent platforms, `factor_review` applicability—drives which factor agents exist and how reviews are scoped.
 - Change documents: `docs/plans/plan-template.md` and staging plans under `docs/plans/`; canonical admitted change docs become wave-owned under `docs/waves/<wave-id>/` during `Add change to wave`, and `Prepare wave` validates that placement alongside `wave.md`.

7. **First-time operators (non-negotiable rules of the road)**
 - **Reading order**: point at **`AGENTS.md` → Start Here** so operators follow the canonical doc order rather than guessing from shortcuts.
 - **Plans vs waves**: new work starts as a consolidated change doc under `docs/plans/` (via **Plan feature**); **Create wave** / **Add change to wave** admits it into `docs/waves/<wave-id>/`. **Repository code** must not be edited until the **`AGENTS.md` Stage gate** (plan + admitted + **Prepare wave**) passes; **Ready wave** is the alias.
 - **Git commits**: operator-owned per **`AGENTS.md`** and **`docs/contributing/build-and-verification.md`** — agents hand off diff + suggested message unless the operator asks to commit in the **current** request.
 - **Product implementation**: when product code ships, **`AGENTS.md` Implementation guard** requires **Prepare wave** immediately before the first product-code edit unless an in-session, named-scope waiver is recorded.
 - **Implement wave vs Implement feature**: **Implement wave** coordinates all admitted changes (auto-runs **Prepare wave** if needed); **Implement feature** is the docs-first single-change path. Purposes also live in **`docs/prompts/index.md`**.
 - **More shortcuts**: phrase→doc table is in **`AGENTS.md`**; **`docs/prompts/index.md` Usage Notes** cover alias handling and concurrency via **`docs/prompts/agent-routing-concurrency.prompt.md`**.
 - **Closing a wave**: **Close wave** / **Finalize feature** must record **docs-contract review** (or **not applicable** + rationale) when `docs/specs/*.md` changed — see **`docs/contributing/review-and-evals.md` (Wave closure)** and **`docs/prompts/close-wave.prompt.md`**.
 - **Background reading**: `docs/references/wave-framework.md`, `002-wave-framework-seeding-overview.md`, **`docs/PLANS.md`** / **`docs/specs/index.md`**.

Tailor every bullet with **this project's** actual paths, generated personas, and whether baseline wave-0 was created or skipped—avoid generic filler that ignores detection results.

Required outputs:

- `docs/README.md` and canonical `docs/` structure
- canonical top-level docs such as:
 - `docs/ARCHITECTURE.md`
 - `docs/PLANS.md`
 - `docs/QUALITY_SCORE.md`
 - `docs/RELIABILITY.md`
 - `docs/SECURITY.md`
- inventory and architecture grounding docs such as:
 - `docs/repo-index.md` (includes structured **architecture handoff** per `seed-030` task 9 for `060` to consume)
 - `docs/architecture/current-state.md`
 - `docs/architecture/domain-map.md`
 - `docs/architecture/layering-rules.md`
 - `docs/architecture/cross-cutting-concerns.md`
 - `docs/architecture/data-and-control-flow.md`
 - `docs/architecture/testing-architecture.md`
 - `docs/missing-docs.md`
- reference and orientation docs such as:
 - `docs/references/project-overview.md`
 - `docs/references/roles.md` — meaning of `Owner:` / doc metadata fields used across `docs/*` (keep aligned with `docs/contributing/docs-maintenance.md` when that doc exists)
- contributing docs and workflow docs such as:
 - `docs/contributing/change-workflow.md`
 - `docs/contributing/feature-workflow.md`
 - `docs/contributing/feature-wave-lifecycle-overview.md`
 - `docs/contributing/agent-team-workflow.md`
 - `docs/contributing/review-and-evals.md`
 - `docs/contributing/build-and-verification.md`
 - `docs/contributing/discovery-delivery-workflow.md`
- decision and execution scaffolding such as:
 - `docs/architecture/decisions/README.md`
 - `docs/architecture/decisions/template.md`
 - `docs/plans/plan-template.md`
 - `docs/references/tech-debt-tracker.md`
- `docs/workflow-config.json` with:
 - **`lifecycle_id_policy`** — required for wave-context installs that ship `lifecycle_id.py`: include `epoch_utc` as a UTC ISO-8601 string, `hour_offset` as a non-negative integer (default `0`), and optional contract metadata (`prefix_width` `5`, `time_unit` `hours`, `minute_bucket` `half-minute-step`) so operators and agents can read the ID scheme without opening the script; **epoch selection rule**: run `git log --reverse --format="%aI" | head -1` to get the timestamp of the first commit on the default branch, convert to UTC midnight of that date (`YYYY-MM-DDT00:00:00Z`), and use that as `epoch_utc`; fall back to UTC midnight of 4 years before the current date when the repository has no commits (pure greenfield with no git history) — this ensures the first IDs generated have exactly one leading zero (`0xxxx`) rather than starting at `00000`, which is reserved for the baseline wave prefix; repositories with existing issued IDs must preserve their effective epoch and offset and must not re-anchor
 - lifecycle settings
 - wave execution settings
 - agent memory settings
 - project persona generation settings
 - prompt generation settings
 - factor review policy (`factor_review_policy`), including:
 - which factors are applicable, partial, or not-applicable for this project (sourced from `docs/repo-profile.json` under `factor_review`)
 - whether factor review should use subagents by default when supported
 - how factor review falls back to review lanes when subagents are not supported
 - whether factor findings are advisory or gating
 - persona review policy (`persona_review_policy`), including:
 - when user/operator persona agents are invoked (wave readiness review, spec authoring, design review, acceptance)
 - whether persona findings are advisory or gating for behavioral changes
 - Wave Council policy (`wave_review`) when the framework-standard council model is enabled, including:
 - required phases (`prepare`, `review`)
 - machine-readable signoff keys in `## Review Evidence`
 - council-moderator role
 - default seat template and rotating-seat policy
 - transition policy for waves already in flight at adoption time
 - review policy flags (`review_policies`), including at minimum booleans aligned with `docs/contributing/agent-team-workflow.md` — for example `require_qa_reviewer_for_bug_fixes` when **product bug fixes** must include **`qa-reviewer`** in readiness and **Review checkpoints**
 - optional indexing policy (`indexing`) when the repo needs additional project index roots beyond the default:
 - use `project_include_prefixes` with explicit `docs` and/or `code` lists of repo-relative prefixes
 - keep the default empty for normal product repos
 - use this for self-hosting or atypical layouts where excluded roots should still participate in semantic search
- refreshable artifacts in topical homes such as:
 - `docs/prompts/prompt-surface-manifest.json`
 - `docs/agents/session-handoff.md`
 - `docs/waves/README.md`
 - `docs/agents/journals/README.md`
 - `docs/references/project-context-memory.md`
 - `docs/waves/00000 wave-zero-plans-and-specs/wave.md` when legacy pre-wave corpora exist (single file, no subdirectories required)
- `docs/repo-profile.json`
- canonical generic role docs under `docs/agents/`
- `docs/agents/platform-mapping.md`
- `docs/agents/personas/` when persona agents are synthesized, including `docs/agents/personas/README.md` as the directory index (create even when no persona files yet so topical roots stay navigable)
- `docs/architecture/threat-model.md`
- `docs/architecture/performance-budget.md`
- generic role journals
- persona agent docs and journals when evidence supports them
- factor-review agent files (`docs/agents/factor-<nn>-<name>.md`) only for factors marked `applicable` in the inventory; render host wrappers such as `.claude/agents/factor-<nn>-<name>.md` where enabled; record skipped factors with rationale in `docs/repo-profile.json`
- root wrappers (hooks / CI / CLI; **agents** prefer MCP **`wave_validate`** / **`wave_garden`** — `seed-050`):
 - `.wavefoundry/bin/docs-lint`
 - `.wavefoundry/bin/docs-gardener`
 - `.wavefoundry/bin/wave-dashboard` — persistent-process launcher for `dashboard_server.py`; opens the browser by default (`--open` baked in); logs to `.wavefoundry/logs/dashboard.log`; see `seed-152` task 2 for the full creation contract
- agent entry files and thin pointers:
 - `AGENTS.md` (includes **Git commits (operator-owned)** per `seed-050` — agents must not `git commit` unless the operator explicitly instructs them in the **current** request; includes **Implementation guard (product code)** when the project ships product implementation source in the repository, per `050`; otherwise a short note that the guard can be added when implementation directories appear)
 - `CLAUDE.md`
 - `.cursor/rules/project-context.mdc`
 - `.junie/guidelines.md`
 - `.github/copilot-instructions.md`
 - `WARP.md`
- repo-local public prompt docs including:
 - `docs/prompts/index.md` — public catalog of shortcut phrases, purposes, and **Usage Notes** (must stay consistent with `AGENTS.md` and `prompt-surface-manifest.json`)
 - `docs/prompts/install-wavefoundry.prompt.md`
 - `docs/prompts/start-dashboard.prompt.md`
 - `docs/prompts/stop-dashboard.prompt.md`
 - `docs/prompts/restart-dashboard.prompt.md`
 - `docs/prompts/upgrade-wavefoundry.prompt.md`
 - `docs/prompts/plan-feature.prompt.md`
 - `docs/prompts/create-wave.prompt.md`
 - `docs/prompts/add-change-to-wave.prompt.md`
 - `docs/prompts/remove-change-from-wave.prompt.md`
 - `docs/prompts/prepare-wave.prompt.md`
 - `docs/prompts/implement-wave.prompt.md`
 - `docs/prompts/implement-feature.prompt.md`
 - `docs/prompts/pause-wave.prompt.md`
 - `docs/prompts/review-wave.prompt.md`
 - `docs/prompts/close-wave.prompt.md`
 - `docs/prompts/finalize-feature.prompt.md`
 - `docs/prompts/agent-routing-concurrency.prompt.md`
- supporting agent-oriented prompt bodies under `docs/prompts/agents/` when project-context/planning helpers are seeded locally:
 - `docs/prompts/agents/README.md`
 - `docs/prompts/agents/init-wave-context.prompt.md`
 - `docs/prompts/agents/upgrade-wave-context.prompt.md`
 - `docs/prompts/agents/plan-feature.prompt.md`
 - `docs/prompts/agents/create-wave.md`
 - `docs/prompts/agents/add-change-to-wave.md`
 - `docs/prompts/agents/remove-change-from-wave.md`
 - `docs/prompts/agents/prepare-wave.prompt.md`
 - `docs/prompts/agents/implement-wave.prompt.md`
 - `docs/prompts/agents/implement-feature.prompt.md`
 - `docs/prompts/agents/pause-wave.md`
 - `docs/prompts/agents/review-wave.prompt.md`
 - `docs/prompts/agents/close-wave.prompt.md`
 - `docs/prompts/agents/finalize-feature.prompt.md`
 - `docs/agents/guru.md (retired prompt path)` (Guru / `code_ask` retrieval agent — `seed-211`)
 - `docs/prompts/agents/performance-reviewer.prompt.md` (`performance-reviewer` lane — `seed-212`)
 - `docs/prompts/agents/security-reviewer.prompt.md` (`security-reviewer` lane — `seed-213`)

Required bootstrap behaviors:

- write or normalize the full repo-local output set required by the wave context framework rather than leaving essential docs/config/artifacts partially seeded
- ensure `.wavefoundry/framework/scripts/lifecycle_id.py` exists in the target repository; if it does not, copy or bootstrap it from the framework source so that wave and change ID generation stays co-located with `docs_lint.py` and `docs_gardener.py`
- use init as the classifier for no-context, legacy-corpus, and already-installed-wave states instead of forcing users to pick migration semantics up front
- reserve `00000 wave-zero-plans-and-specs` baseline IDs for captured historical corpora, keep the final title legacy-prefixed, and close the baseline only after the full capture-and-closure sequence is complete: plan files physically moved into the wave folder, reviews documented with real findings, journals populated with distilled lessons, and core memory files updated
- execute the close-wave follow-through for the legacy baseline instead of treating baseline capture as a shortcut: reconcile journal refs, distill the seeded journal lessons, promote reusable memory/core-doc updates, refresh persona agent guidance when the corpus changes operating advice, and leave the wave record explicitly `completed`
- place every seeded artifact in the topical folder that matches its role under `docs/` instead of routing anything through `docs/generated/`; if `docs/generated/` exists and contains durable artifacts, migrate each to its topical home and then **remove the `docs/generated/` directory entirely** — do not leave it as an empty shell
- keep refreshable artifacts in their topical homes while making their regeneration semantics explicit in nearby canonical docs
- ensure `docs/workflow-config.json` is seeded with `factor_review_policy` (applicable factors, gating vs advisory, subagent vs review lane) and `persona_review_policy` (when user/operator personas are invoked) so later upgrades can regenerate consistently
- ensure `docs/workflow-config.json` is seeded with explicit readiness-review behavior in `wave_implement` and persona gating behavior in `persona_review_policy` so later upgrades can regenerate consistently
- ensure `docs/workflow-config.json` includes **`lifecycle_id_policy`** whenever `lifecycle_id.py` is vendored so new projects inherit an explicit epoch contract; set `epoch_utc` to UTC midnight of the first commit date (`git log --reverse --format="%aI" | head -1`, then convert to `YYYY-MM-DDT00:00:00Z`), falling back to UTC midnight of 4 years before the current date for repositories with no git history (producing `0xxxx`-prefixed IDs from day one, visually distinct from the `00000` baseline wave prefix); do not re-anchor for projects that already have issued wave/change IDs—preserve the effective values already in use
- ensure the public prompt surface only exposes the intended wave-context commands while internal helper prompts remain internal
- keep supporting agent-oriented prompt bodies under `docs/prompts/agents/` instead of mixing them into the public prompt index or legacy agent-prompt folders
- generate tracked platform hook/config surfaces via `.wavefoundry/framework/scripts/render_platform_surfaces.py` so `.claude/settings.json`, `.cursor/hooks.json`, `.github/hooks/hooks.json`, and any generated Python hook entrypoints are present before verification
- ensure the repo-local docs include a project overview that introduces the canonical documentation map, workflow, generic roles, synthesized persona agents when present, and how agent roles and persona agents work together
- generate a repo-local `docs/contributing/feature-wave-lifecycle-overview.md` from `.wavefoundry/framework/seeds/001-feature-wave-framework-overview.md`, then adapt it with the project's actual reviewer roles, persona agents, and artifact paths
- generate policy and procedure docs with project-specific triggers, prerequisites, commands, review gates, fallback paths, and artifact locations instead of leaving them as generic placeholders
- ensure `docs/contributing/build-and-verification.md` includes a **Git commits** section (operator-owned policy) consistent with `seed-050` whenever that file is created or refreshed during init — same contract as **Git commits** in `AGENTS.md`
- seed `docs/contributing/review-and-evals.md` with a **Wave closure** subsection that requires **Docs-contract review** (spec review) when behavioral specs under `docs/specs/*.md` changed during a wave, consistent with `seed-190` and seeded `docs/prompts/close-wave.prompt.md`
- seed `docs/prompts/close-wave.prompt.md`, `docs/prompts/agents/close-wave.prompt.md`, and `docs/contributing/review-and-evals.md` with explicit closure-reconciliation requirements (not status flip only): block closure until chronology metadata is reconciled (`Status`, `Current state`, change states, `Completed at`), required reviewer lanes from readiness are reconciled in `Review checkpoints`, closure artifacts are reconciled (journal distillation, durable memory promotion, and `docs/agents/session-handoff.md` clear/refresh), and docs-contract disposition is recorded (reviewed or not applicable with rationale)
- seed close-wave guidance so reviewer-journal capture is expected for important implementation/review lessons when role journals exist, while absence of role-specific journal files is not itself a closure blocker (record lessons in canonical existing journals instead)
- keep generated project-specific outputs outside this shared pack

Recommended init verification checks:

- verify every required prompt doc exists
- verify every required topical artifact root exists
- verify root wrappers point to `.wavefoundry/framework/scripts/`
- verify agent entry files route to canonical docs and public prompt docs
- verify `AGENTS.md` contains **Git commits (operator-owned)** per `050` (agents do not run `git commit` unless the operator explicitly instructs in the current request)
- verify `docs/contributing/build-and-verification.md` contains a **Git commits** section aligned with that policy when the file is in scope for init
- verify `AGENTS.md` contains an **Implementation guard** section iff the repo profile / repo-index indicates shipped product code, and thin pointers mention the guard when that section exists
- verify `factor_review_policy` is explicit in `docs/workflow-config.json` even when no factor-review agents were generated; verify `persona_review_policy` is explicit when user/operator personas exist; verify wave-execution readiness gates are explicit when non-trivial waves are enabled
- verify refreshable files are referenced where expected
- verify seeded workflow/policy docs are grounded in evidence from the repository and contain actionable procedures rather than generic shared-pack restatements
- verify any generated legacy baseline wave has a single `wave.md` (no subdirectories), carries a legacy-prefixed final title, includes a `## Corpus` table with plan files at their new paths inside the wave folder, that `docs/plans/completed/` is empty after baseline capture, that review checkpoints contain actual findings per applicable review lane, that journal files have real distilled lessons not placeholder text, that `docs/references/project-context-memory.md` has at least one promoted entry, and that the baseline record links to promoted journal/persona/memory/core-doc outputs
- verify `docs/plans/plan-template.md` exists and uses the consolidated change document format after init completes
- for new projects with no prior context, verify baseline wave creation was skipped and all other required outputs were still seeded
- verify `docs/prompts/index.md` exists and references align with `docs/prompts/prompt-surface-manifest.json` and `AGENTS.md` shortcut table
- verify `docs/references/roles.md` exists and matches how seeded docs use `Owner:` / metadata
- verify `docs/workflow-config.json` contains the top-level sections `wave_implement`, `agent_memory`, `project_persona_generation`, `prompt_generation`, `factor_review_policy`, and `persona_review_policy`
- verify `docs/workflow-config.json` contains **`lifecycle_id_policy`** when the repository vendors `lifecycle_id.py` (typical wave-context install), with valid `epoch_utc` and non-negative integer `hour_offset`
- verify `docs/prompts/prompt-surface-manifest.json` contains `schema_version` and `seed_framework_source`, and that `prompt_generation.seed_framework_source` matches the manifest’s `seed_framework_source`
- when framework scripts are present, confirm the docs gate passes (**`wave_validate`** over MCP when available; otherwise **`.wavefoundry/bin/docs-lint`**) and resolve failures before declaring init complete
- verify `docs/ARCHITECTURE.md` indexes the seeded `docs/architecture/*.md` child docs and that **domain-map**, **layering-rules**, **cross-cutting-concerns**, **data-and-control-flow**, and **testing-architecture** are populated from evidence in the repository (or explicitly scoped as N/A for trivial repos); verify **decisions/template.md** exists and is linked from **decisions/README.md**

Guardrails:

- Do not copy project-specific guidance back into this shared pack.
- Do not artificially constrain generated artifacts to shallow templates.
- Generate stable anchors and cross-links, then allow artifacts to expand as needed for execution and review.
- When generating tasks, requirements, guardrails, or review points, include every item that is materially useful to the target project instead of trimming the list to a small fixed count.
- Keep legacy non-wave vocabulary only as a migration aid, not as the primary identity of the wave context framework.
- Record factor-review applicability in `docs/repo-profile.json` under `factor_review`; generate canonical `docs/agents/factor-<nn>-<name>.md` files only for applicable factors, not for partial or non-applicable ones, and render the matching host wrappers where enabled.
- Do not leave critical repo-local outputs for a later manual pass when they can be seeded during init.
