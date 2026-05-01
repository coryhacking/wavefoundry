# Wave Framework

This folder is Wavefoundry's canonical Wave Framework source for initializing, upgrading, and running an adaptive wave-based context framework for other projects.

- Canonical source folder in Wavefoundry: `framework/`
- Friendly shorthand: `Wave Framework`
- Scope: shared prompt pack, shared script implementations, and framework-local migration helpers
- Boundary rule: project-specific outputs belong in the target repository's `docs/`, root agent entry files, and platform-native agent folders, not in this shared pack
- Core upgrade model: this source tree should be renderable or packageable into another project's repository, then used to initialize or upgrade that project's local context system

## Public Commands

Use these public phrases in a target project's repository:

- `Init wave framework` (legacy: `Init wave context`)
- `Upgrade wave framework` (legacy: `Upgrade wave context`)
- `Plan feature`
- `Create wave`
- `Add change to wave`
- `Remove change from wave`
- `Prepare wave`
- `Implement wave`
- `Implement feature`
- `Pause wave`
- `Review wave`
- `Close wave`
- `Finalize feature`

Packaging (maintainer / cross-repo distribution) uses **`Package Wavefoundry`** -> `framework/seeds/240-package-wavefoundry.prompt.md`. From the Wavefoundry repository root, run `python3 framework/scripts/build_pack.py`. The script writes `wavefoundry-YYYY-MM-DDx.zip` using today's date by default and a letter `x` that is the successor of the highest existing suffix for that date in the output directory. It stamps `framework/VERSION` to the same `<date><letter>` before writing the archive. Every zip entry begins with `framework/`, so extracting at a Wavefoundry repository root restores the canonical framework source layout. Legacy phrases such as **`Package wave framework`** and **`Package wave context`** remain accepted only as migration aliases.

**`Install wave framework`** (legacy: **`Install wave context`**) may be accepted as a convenience alias, but it is not a new primary public command:

- route it to **`Init wave framework`** / **`Init wave context`** when the repository has not yet been seeded into any wave-context state
- route it to **`Upgrade wave framework`** / **`Upgrade wave context`** when the repository already contains legacy project-context artifacts or an installed Wave Framework layer
- prefer **`Init wave framework`** / **`Upgrade wave framework`** in durable prompt surfaces, docs, and handoffs (legacy **context** phrases remain valid)

## Framework Identity

The Wave Framework replaces the older project-context framework model with a wave-native operating model:

- **WAVE** stands for **Workflow, Agents, Verification, Engineering**.
- **WAVE** is the project's docs-first engineering system for organizing workflow, coordinating agent roles, enforcing verification, and guiding delivery through canonical project context.
- Tagline: **Docs-first engineering for agent-driven software delivery.**
- `wave-0` is the project's first installed Wave Framework layer in the repository, whether it comes from fresh init or from legacy project-context migration

- **waves are the primary delivery unit** — each wave is a bounded, reviewable container for one or more changes that are planned, implemented, reviewed, and committed together
- changes with stable `Change ID` anchors are admitted into a wave; the wave is the umbrella, not the change
- individual changes do not ship independently — everything is delivered through a wave
- `wave-0` designates the first active wave layer; the reserved `00000` prefix is used only for the legacy baseline wave created during init
- journals capture role- and persona-specific learning over time
- user/operator personas are synthesized from evidence in the repository
- output contracts replace rigid human-oriented templates

## Design Principles

- **Seeded, not mirrored:** generate a repo-local prompt system derived from this pack and current evidence from the repository
- **Waves over flat concurrency:** do not fan work out until shared assumptions and interfaces are stable enough for a wave
- **Contracts over templates:** require semantic completeness and stable anchors, not shallow uniform formatting
- **Agent-first artifacts:** optimize artifacts for downstream agent continuation, review, challenge, and retrieval
- **No artificial output limits:** agents should not compress useful reasoning, caveats, dependencies, or handoff detail just to fit a fixed format
- **No artificial list limits:** tasks, requirements, guardrails, and review points should include every useful and important item for the current context rather than being trimmed to a neat fixed count
- **Preserve growth:** upgrades should preserve repo-grown personas, journals, and prompt behavior when they remain supported by evidence from the repository
- **Prefer additive migration:** migration and upgrade flows should backfill and reconcile before deleting or retiring legacy artifacts

## Numbering Policy

The Wave Framework reserves the `000` slot for a future top-of-folder insertion and then uses zero-padded insertion-friendly numbering so the highest-level shared overviews stay visible before the prompt pack itself.

Overview docs use the first reserved block:

- `001-009`: shared framework overview docs and subsystem explainer docs

Prompt files then continue with zero-padded insertion-friendly numbering:

- `010-090`: bootstrap, discovery, and generation
- `100-149`: prompt surface generation, memory bootstrap, and reindex
- `150-169`: update and upgrade flows
- `170-199`: feature lifecycle
- `200-249`: wave, journal, and migration helpers

This leaves room to insert prompts later without renumbering the whole pack.

## Prompt Map

- `010-install-wavefoundry.prompt.md` — end-to-end first-time initialization
- `020-run-contract.prompt.md` — execution contract and precedence rules for all later prompts
- `030-inventory-and-map.prompt.md` — evidence from the repository and archetype discovery
- `031-tech-stack-detection-catalog.md` — reference appendix: detection catalog consumed by `030` task 6 (stack, toolchain, CI/CD, framework, and testing-tool detection) and task 7 (design-surface detection); not a standalone prompt — loaded only when `030` needs the exhaustive catalog for disambiguation
- `040-docs-structure-bootstrap.prompt.md` — docs, generated artifacts, and lifecycle folder structure
- `050-agent-entry-surface-bootstrap.prompt.md` — `AGENTS.md`, thin pointers, and native role surfaces
- `060-domain-boundaries.prompt.md` — architecture, boundaries, shared hotspots, and safe wave partitions
- `070-quality-and-debt.prompt.md` — quality, reliability, security, performance, and debt posture
- `080-mechanical-enforcement.prompt.md` — docs gate, wrappers, CI hooks, and tracking rules
- `090-doc-gardening-harness.prompt.md` — canonical gardener/lint harness behavior
- `100-project-prompt-surface-bootstrap.prompt.md` — generate the repo-local prompt surface
- `110-wave-memory-bootstrap.prompt.md` — wave artifacts, wave status rules, and handoff contracts
- `120-project-persona-synthesis.prompt.md` — evidence-driven project-specific SME persona generation
- `130-agent-journal-bootstrap.prompt.md` — journal scaffolding, distillation, and promotion contracts
- `140-reindex-ongoing.prompt.md` — ongoing drift detection across docs, prompts, personas, and memory
- `150-refresh-wavefoundry.prompt.md` — internal targeted/full refresh helper
- `160-upgrade-wavefoundry.prompt.md` — public upgrade and legacy-to-Wavefoundry migration entrypoint
- `170-plan-feature.prompt.md` — wave-aware feature planning
- `175-interrogate-plan.prompt.md` — plan interrogation and stress-test helper
- `180-implement-feature.prompt.md` — wave execution and coordination
- `190-finalize-feature.prompt.md` — closure, promotion, and archival
- `200-wave-reconciliation.prompt.md` — internal helper for starting, updating, and completing waves
- `210-agent-journal-distillation.prompt.md` — internal helper for journal cleanup and promotion candidates
- `220-legacy-framework-migration.prompt.md` — internal helper for migrating from legacy non-wave context footprints
- `230-author-spec.prompt.md` — spec authoring and behavior-contract refresh helper
- `240-package-wavefoundry.prompt.md` — maintainer packaging entrypoint for Wavefoundry source distributions
- `250-migrate-existing-wave-project.prompt.md` — explicit migration from legacy vendored framework layout to Wavefoundry layout

## Cross-Prompt Citations (`seed-NNN` short-name convention)

When one seed prompt cites another, prefer the short-name alias `seed-NNN` (e.g. `seed-050`, `seed-160`) over the full filename. The mapping is 1-to-1 with the `Prompt Map` above: `seed-030` means `030-inventory-and-map.prompt.md`, `seed-100` means `100-project-prompt-surface-bootstrap.prompt.md`, and so on. The convention also resolves reference appendices in the pack that share the `NNN-<slug>` naming (e.g. `seed-031` → `031-tech-stack-detection-catalog.md`); the `Prompt Map` entry is the authoritative filename resolver regardless of whether the target is a prompt or an appendix.

Rules:

- Filenames themselves do **not** change — `seed-NNN` is citation shorthand only. The `Prompt Map` remains the authoritative filename resolver and must continue to carry every prompt's full `NNN-<slug>.prompt.md` name.
- Use `seed-NNN` only for citations to files within this shared framework source (`framework/seeds/`). Repo-local artifacts (`docs/prompts/<name>.md`, `docs/agents/<role>.md`, `docs/waves/<wave-id>/wave.md`, etc.) keep their full paths -- `seed-NNN` is not a generic alias system.
- Top-of-file headings (`# 030 - Inventory And Map`) and `## Prompt Map` entries keep their long forms; only inline citations in prose use the short form.
- Downstream repos inherit the convention on their next **`Upgrade wave framework`** (legacy: **`Upgrade wave context`**) run; nothing in an already-seeded repo breaks because long-form filenames continue to resolve.

## Numbered Overview Docs

- `001-feature-wave-framework-overview.md` — primary conceptual overview of the Wave Framework lifecycle and operating model
- `002-wave-framework-seeding-overview.md` — init, upgrade, migration, and seeded-output mechanics
- `003-prompt-numbering-philosophy.md` — numbering ranges, insertion strategy, and how to place new shared docs vs prompts
- `004-wave-memory-overview.md` — shared model for wave state, handoffs, carry-forward, and durable workflow memory
- `005-persona-system-overview.md` — how project-specific personas are synthesized and used alongside generic roles
- `006-agent-journal-system-overview.md` — how journals capture low-noise lessons and promotion candidates over time
- `007-review-system-overview.md` — shared review lanes, gates, and how repo-local policies specialize them
- `008-framework-map.md` — maintainer-facing map of package layers, prompt tiers, repo-local outputs, and shared-to-local boundaries
- `009-framework-maintenance-contract.md` — completeness criteria, repo-generation contract, golden-path examples, and prompt-to-doc maintenance rules

## Seeding Overview

For the canonical package-local explanation of how the framework operates from feature planning through wave closure, see `framework/seeds/001-feature-wave-framework-overview.md`.

For the canonical package-local explanation of how seeding works, how init differs from upgrade, what `wave-0` means, and what gets generated into a project's repository, see `framework/seeds/002-wave-framework-seeding-overview.md`.

For the maintainer-facing package structure and hardening contracts, see `framework/seeds/008-framework-map.md` and `framework/seeds/009-framework-maintenance-contract.md`.

Those overview docs also define the requirement for seeded repo-local orientation docs such as `docs/references/project-overview.md` and a repo-specific lifecycle companion at `docs/contributing/feature-wave-lifecycle-overview.md`, which should explain the local workflow, reviewer roles, synthesized personas, and artifact paths.

## Minimal Required Repo-Local Outputs

After planting this pack into another project's repository and running init or upgrade, the target should have:

- a canonical `docs/` knowledge layer
- a repo-local orientation overview at `docs/references/project-overview.md`
- a repo-local prompt surface under `docs/prompts/`
- supporting agent-oriented prompt bodies under `docs/prompts/agents/` when the seeded project keeps checked-in planning/context prompt bodies
- `docs/workflow-config.json` with wave, memory, persona, and prompt-generation settings
- refreshable artifacts in topical homes such as `docs/prompts/prompt-surface-manifest.json`, `docs/waves/`, `docs/agents/journals/`, and `docs/agents/session-handoff.md`
- `docs/agents/personas/`
- root agent entry files and thin platform-native pointers when enabled
- `.wavefoundry/bin/docs-lint` and `.wavefoundry/bin/docs-gardener` launchers (no repo-root shims in this repository)

Seeded docs should live in the topical folder that matches their role under `docs/`, including refreshable artifacts. Make regeneration expectations explicit in the topical artifact docs and surrounding canonical docs instead of routing checked-in outputs through `docs/generated/`.

The more explicit create/refresh/preserve rules, final review checklist, and golden-path examples live in `framework/seeds/009-framework-maintenance-contract.md`.

## Suggested Workflow Config Anchors

When this pack initializes or upgrades another project, the generated `docs/workflow-config.json` should explicitly include sections for:

- `wave_execution`
- `agent_memory`
- `project_persona_generation`
- `prompt_generation`
- `factor_review_policy`
- `persona_review_policy`

Suggested `wave_execution` anchors:

- whether waves are required for non-trivial work
- wave root path
- wave activation and closure requirements
- whether readiness review is required before implementation and rerun before closure
- contract freeze policy before parallelism

Suggested `agent_memory` anchors:

- journal root path
- promotion behavior
- distillation behavior
- entry schema version
- retention and cleanup policy
- sensitivity and access expectations

Suggested `project_persona_generation` anchors:

- enablement
- persona root path
- evidence sources
- maximum persona count
- retirement policy

Suggested `factor_review_policy` anchors:

- which factors are `applicable`, `partial`, or `not-applicable` for this project (sourced from `docs/repo-profile.json` under `factor_review`)
- whether factor-review findings are advisory or gating for this project
- whether factor-specific review uses native subagents (`.claude/agents/factor-<nn>-<name>.md`) or falls back to review lanes
- when factor-review agents should activate for a wave

Suggested `persona_review_policy` anchors:

- whether persona review is required when selected by readiness evaluation or is advisory only
- which change types should invoke persona agents (spec changes, UX-affecting changes, acceptance criteria)
- persona root path
- whether persona findings are gating or advisory

Suggested `prompt_generation` anchors:

- public prompt root
- prompt-surface manifest path
- upgrade merge behavior
- whether repo-grown adaptations should be preserved
- output-contract schema or generation version

## Suggested Prompt Manifest Anchors

`docs/prompts/prompt-surface-manifest.json` should make prompt regeneration and upgrades auditable. It should normally include:

- schema version
- seed framework source
- seed framework revision or generation marker
- generated-at timestamp
- public prompt files
- enabled internal features
- generated personas
- journal root
- wave root
- upgrade merge notes

## Output Contract Philosophy

The framework should enforce required semantics and stable anchors, but it should not force shallow or overly rigid templates.

Artifacts should be:

- richly detailed when needed
- compact when the work is simple
- easy for other agents to continue
- explicit about uncertainty, dependencies, and handoffs

Every major artifact should have stable anchors such as:

- identity (`Change ID`, `wave-id`, persona name, etc.)
- status
- scope
- dependencies
- evidence refs
- next actions or handoffs

Everything beyond that should be allowed to expand naturally based on the work.
Lists of tasks, guardrails, required semantics, and review checks should be treated as minimum anchors and illustrative categories, not as a ceiling on how much detail or how many items an agent may include when the work warrants more.

Output contracts should also be version-aware enough that later prompts and tooling can detect missing anchors or stale semantics and report clear diagnostics.

## Wave Model

Waves are execution and knowledge-transfer phases, not merely concurrency buckets.

### Canonical Wave Goals

A wave artifact exists to preserve the minimum durable truth needed for multi-agent execution and continuation:

- **Operational truth:** what work is in scope for this wave, what state it is in, and what outputs are expected or already produced.
- **Coordination truth:** who is coordinating, which participants and lanes are active, how work is allocated, and which dependencies or checkpoints gate progress.
- **Assumption truth:** which assumptions and interfaces are frozen, tentative, confirmed, or invalidated, and which changes or tasks they affect.
- **Disposition truth:** which changes or tasks completed, blocked, deferred, moved, retried, or were superseded, and why.
- **Carry-forward truth:** what remains part of the same `Change ID`, what must move into the next wave, and what conditions make the next wave ready or not ready.
- **Handoff truth:** enough state, rationale, findings, and review status that another agent can continue or challenge the wave without reconstructing missing context from scratch.

These goals define the contract for wave artifacts and reconciliation helpers. Section layouts may vary, but these truths must remain recoverable.

- a wave can contain one small fix or many compatible feature slices
- a wave can contain multiple workstreams when their assumptions are compatible
- only one wave should normally be active per `change-id` at a time
- the wave coordinator owns execution order, agent allocation, review checkpoints, and wave completion
- small waves and large waves should use the same scalable artifact model: the `## Changes` section can stay compact for a one-line fix or the change docs can expand into nested workstreams for a large feature bundle
- waves should make partial failure, retries, deferred changes, and moved changes explicit so downstream agents can tell what actually completed

### Wave Orchestration Contract

Wave collaboration should be explicit enough that multiple agents can run the same wave consistently rather than improvising different coordination models.

Each active wave should make the following orchestration concerns explicit:

- **Coordinator:** the role or owner that admits work into the wave, allocates work, enforces dependencies, and declares the wave complete
- **Roster:** which generic roles and project personas are participating, and whether they are implementing, reviewing, challenging, or approving
- **Allocation:** which changes, tasks, or workstreams belong to which participant and what dependencies must clear before they start
- **Synchronization:** when participants report findings, blockers, invalidated assumptions, and outputs back to the coordinator
- **Escalation:** what conditions force replanning, reassignment, added review, or wave supersession
- **Closure:** what must be true for the wave to close and what happens to incomplete, deferred, moved, or retried work

The intended lifecycle for an active wave is:

- **Admission** — choose the work that belongs in the wave and verify assumptions, dependencies, and entry criteria
- **Allocation** — assign changes, tasks, and review lanes to agents and personas
- **Execution** — run the admitted work while preserving explicit status, blockers, and assumptions
- **Reconciliation** — consolidate outputs, record invalidated assumptions, and decide whether the wave should continue, split, or close
- **Closure** — mark the disposition of all wave changes, produce the next-wave handoff, and update journals and promotion candidates

### Implement Loop Execution Model

The coordinator's execution loop during the implement phase follows a ReAct-derived model — explicit Reasoning, Action, and Observation at every lane boundary. Key properties:

- **Thought before action:** the coordinator records a `Thought:` entry in the Progress Log before each lane invocation, stating why this action now.
- **Wave plan:** before the first edit, the coordinator produces an ordered lane sequence with scoped inputs per serialization unit; deviations are named events, not silent reorderings.
- **Parallel lane merge:** reviewer and persona lanes with no shared dependencies run concurrently; the coordinator synthesizes a merged `Observe:` before the next `Thought:`.
- **Finding classification (CRITIC):** after each review cycle, findings are evaluated against the change doc's acceptance criteria before a loop level is chosen — "reviewer clean" alone is not the exit condition.
- **Root cause capture (Reflexion):** after a blocking finding, the coordinator records a `Reflect:` entry identifying the pattern and updating remaining tasks proactively.
- **Three loop levels:** Level 1 (micro — internal to implementer, no log entry), Level 2 (reviewer loop — fix and re-run, no re-Prepare), Level 3 (wave lifecycle — scope or plan invalidation, stop and re-Prepare or re-plan). Finding type — not severity — determines the level.

See `001-feature-wave-framework-overview.md` section 3a for the full loop model, finding classification table, and escalation reference.

### Wave Artifact Contract

Wave artifacts should be machine-usable without becoming rigid fill-in-the-blank templates. The goal is to preserve stable anchors and relationship semantics so other agents can read, continue, challenge, and reconcile the wave reliably.

Each wave artifact must expose stable identifiers and state anchors sufficient to recover operational, coordination, assumption, disposition, and handoff truth, such as:

- `Change ID`
- `wave-id`
- `Status`
- `Coordinator`
- `Objective`
- `Participants`
- `Changes`
- `Dependencies`
- `Assumptions`
- `Review Checkpoints`
- `Journal Refs`
- `Next-Wave Handoff`

For machine usability, each wave should make these relationships explicit when they exist:

- which participants own or review which changes or tasks
- which changes depend on which other changes
- which assumptions are frozen, tentative, invalidated, or newly discovered
- which review checkpoints gate progress or closure
- which incomplete changes or tasks were deferred, moved, retried, blocked, or superseded

Changes should support variable depth while preserving stable anchors. A change may be atomic or composite, and optional tasks/subtasks may be tracked inside the change document when finer execution state is useful. A normal wave record should expose:

- `Change ID`
- `Change Status`
- optional `Previous Change Status`
- title or scope
- owner
- dependencies
- expected outputs
- review requirements
- blockers or risks
- child tasks, subtasks, or workstreams when the change is composite

Wave artifacts should also preserve time-sequenced operational state when useful, for example:

- coordinator decisions
- new findings
- invalidated assumptions
- review outcomes
- state transitions for changes or tasks

This does not require a rigid event log template, but it does require enough explicit state that another agent can reconstruct what happened and why the wave is in its current condition.

### Change Carry-Forward Policy

Waves are operational containers. Changes are the durable units of scope and intent tracked inside waves.

- a wave may contain one or more changes
- a change may appear in more than one wave
- a wave should close even when some change work remains incomplete, as long as the disposition of that remaining work is explicit

Default policy:

- when a change is not finished at wave closure, keep the same `Change ID` and carry its unfinished work into a later wave
- move, defer, retry, or rescope the unfinished change work explicitly rather than inventing a new change identifier by default

Split a change into a new change only when:

- the remaining work has become materially different in purpose or scope
- the unfinished work now needs separate planning, review, or decision treatment
- the original change is effectively complete and the remainder is follow-on work rather than continuation
- keeping the same `Change ID` would hide a real shift in intent, risk, or accountability

## Persona Model

Persona agents represent the **users, operators, administrators, and deployers** of the software system being built — not the agents who build it. They are invoked to give the user perspective during spec authoring, design review, and acceptance.

- personas are distinct from agent roles: roles build the software; personas speak as the people who use or operate it
- persona creation should be evidence-driven; do not invent personas for style or symmetry
- ground each persona in usage patterns, behavior contracts, and user-facing failure modes found in the project (from evidence in the repository)
- when evidence is sparse, ask the user who operates or uses the system before generating persona docs
- persona count should stay justified by evidence; start small and expand only when a meaningfully distinct usage pattern requires it
- personas participate in spec authoring, design review, edge-case analysis, and acceptance — not in implementation or coordination

Factor-review agents are a separate concern from user personas. See the `## Factor Review Model` section below.

## Factor Review Model

Factor review agents are specialized AI reviewer subagents that evaluate a wave's changes against one specific operational concern. They complement — not replace — the generic `architecture-reviewer`, `security-reviewer`, and `performance-reviewer` roles.

The canonical reference is the 15-factor model: the original Twelve-Factor App methodology plus three IBM extensions. Factor review is not limited to cloud-native services — individual factors apply whenever the project evidence supports them.

**Threshold for creating a factor-review agent:** a factor warrants a dedicated subagent when it introduces at least 2–3 concrete review questions that the generic reviewer roles would not naturally ask. If a factor overlaps entirely with an existing reviewer's scope, skip it.

**Implementation:** generate a `.claude/agents/factor-<nn>-<name>.md` file for each applicable factor (zero-padded number keeps directory listings sorted). Each agent file should describe: what this factor means, what evidence in this project makes it relevant, what questions it asks when reviewing a wave, and whether its findings are gating or advisory for this project.

### The 15 Factors and Applicability Signals

| # | Factor | Create a review agent when |
|---|---|---|
| 01 | **Codebase** | Project has multiple deploy targets, environment-per-branch patterns, or a monorepo with shared app code |
| 02 | **Dependencies** | Project uses a package manager with declared dependencies and isolation requirements |
| 03 | **Config** | Project reads configuration values that differ by environment, user, or deployment context |
| 04 | **Backing services** | Project connects to external services — databases, caches, IoT bridges, APIs, message brokers — as attached resources |
| 05 | **Build / release / run** | Project has a formal build pipeline, distributable artifact, or CI/CD with strictly separated build and run stages |
| 06 | **Processes** | Project is designed to run as stateless processes with explicit scaling or worker-pool requirements |
| 07 | **Port binding** | Project binds to a network port or exposes an HTTP, gRPC, or WebSocket interface |
| 08 | **Concurrency** | Project is designed to scale by adding concurrent instances or workers |
| 09 | **Disposability** | Project runs as a daemon, service, or long-running process with graceful startup and shutdown requirements |
| 10 | **Dev / prod parity** | Project has meaningfully distinct development, staging, and production environments |
| 11 | **Logs** | Project has structured logging, event-stream observability, or operational output contracts |
| 12 | **Admin processes** | Project has CLI tools, one-off operational commands, or management scripts run alongside the main process |
| 13 | **API first** *(IBM)* | Project exposes an API as a first-class integration contract consumed by other systems or services |
| 14 | **Telemetry** *(IBM)* | Project has monitoring, alerting, distributed tracing, or operational dashboard requirements |
| 15 | **Auth and security** *(IBM)* | Project has authentication, authorization, multi-user access control, or externally-facing trust boundaries |

**When to skip a factor:** if the project provides no concrete evidence for the applicability signal, record the factor as `not-applicable` with a one-line rationale in `docs/repo-profile.json` under `factor_review`. Do not generate an agent file for skipped factors. Re-evaluate skipped factors during **`Upgrade wave framework`** (legacy: **`Upgrade wave context`**) when project scope changes.

**Relation to generic reviewers:** factor agents are narrow specialists. They ask factor-specific questions that the general reviewer pool would otherwise miss. When a factor overlaps closely with an existing reviewer (e.g., factor 15 auth/security overlaps with `security-reviewer`), keep both but define non-overlapping scope in each agent's instructions.

## Journal Model

Journals are structured episodic memory for roles and personas.

- journals are advisory, not source of truth
- repeated, validated lessons can be promoted
- journals should stay bounded over time through distillation, archival, and retention policy rather than unbounded accumulation
- promotion targets include repo-local workflow memory, prompt docs, persona docs, or canonical docs

## Migration Model

Older non-wave context footprints should be treated as legacy source material during migration.

- `160-upgrade-wavefoundry.prompt.md` should be able to initialize missing wave-context artifacts in repos that already use the legacy framework
- `220-legacy-framework-migration.prompt.md` defines the migration helper behavior
- delete the legacy framework only after the migration path is validated
