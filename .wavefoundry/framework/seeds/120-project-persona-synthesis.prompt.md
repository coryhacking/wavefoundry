# 120 - Project Persona Synthesis

Intent:

- Identify and generate persona agents that represent the users, operators, administrators, and deployers of the software system being built.
- Ground persona synthesis in project evidence. When evidence is insufficient, ask the user targeted questions before generating personas.

Persona agents are distinct from agent roles. Agent roles (planner, implementer, reviewer, wave-coordinator) represent the AI participants who build the software. Persona agents represent the humans who use, operate, deploy, or administer it. Both are invocable agents in the workflow, but personas give the user perspective during design, spec authoring, and acceptance.

Evidence sources to inspect:

1. Architecture docs (`docs/ARCHITECTURE.md`, `docs/architecture/`) — who interacts with each layer of the system? What roles does the architecture assume (end user, admin, API consumer, background operator)?
2. Behavior contracts (`docs/specs/*.md`) — who triggers the behaviors described? What configurations, schedules, or preferences do they manage?
3. Deployment and platform docs — who installs, configures, and updates the software? Is there a difference between an end user and an administrator?
4. UI or interaction surface — what user-facing workflows exist? What does daily use look like?
5. Reliability and failure docs (`docs/RELIABILITY.md`) — what failure modes exist? Who experiences them and how do they notice?
6. Closed baseline wave corpus (`docs/waves/00000 wave-zero-plans-and-specs/wave.md`) — what usage patterns or user-facing bugs were addressed? Do they imply distinct user types?
7. Any existing user documentation, onboarding, or support material in the repository.

Tasks:

1. Scan the evidence sources above and list candidate persona types with a one-line rationale for each.
2. If evidence clearly supports a persona (distinct configuration, workflow, or failure mode), proceed to generate it.
3. If evidence is ambiguous or thin for a candidate, **ask the user** before generating:
   - "The codebase suggests [X usage pattern]. Is there a meaningfully distinct type of user or operator this represents? What are their goals and how do they interact with the system?"
   - "Does anyone other than the primary end user install, configure, or administer this software? If so, what do they do?"
   - "Are there users with significantly different usage patterns — for example, users in specific time zones, schedules, or device configurations that stress the system differently?"
4. For each confirmed persona, generate a doc under `docs/agents/personas/` with:
   - **Who** — role, relationship to the software, usage context
   - **Goals** — what outcomes they rely on the system to deliver
   - **Workflows** — how they set up, configure, and use the system day-to-day; when `docs/architecture/domain-map.md` (and `data-and-control-flow.md` when present) name deployable domains, reference those **same names** for touchpoints (for example which app, daemon, or API surface the persona interacts with)
   - **Failure modes** — what goes wrong for them and how they recognize it
   - **Invocation signals** — which phases and change types should invoke this persona (spec authoring, design review, acceptance, edge-case analysis)
   - **Operating identity** — the persona's stance, priorities, decision pressure, success criteria, and what they are responsible for noticing during software delivery
   - **Salience triggers** — persona-specific signals that should cause an agent to stop and journal before context is lost, such as repeated workflow friction, trust-risk, operator-signal, confidence-shift, or a hard-to-rediscover domain constraint
   - **Associated journal** — path to their journal under `docs/agents/journals/`
5. Generate persona journals when personas are created. Persona journals use the same operating-memory schema as role journals defined in `seed-130` — they must include operating identity, salience triggers, recent captures or evidence-based observations, and distillation sections populated from evidence, not placeholder text. When no incidents exist yet, write a brief evidence-based observation about the persona's primary workflows and failure modes as a seed entry rather than leaving the sections empty.
6. **Persona coverage checklist.** Before declaring done, answer each of the following four questions explicitly with `yes — <persona-name>` or `no — <one-line evidence-grounded reason>`. A silent skip is not a valid answer; "no, this project has no admin role because <evidence>" is. The checklist exists because the install retrospective surfaced agents satisficing on the primary end-user persona and missing admin / operator / configurator / integrator usage patterns even when evidence existed for them.
   1. **Elevated-privilege user.** Is there a user with elevated privilege — admin, superuser, `ROLE_ADMIN`, or equivalent? Look for: role-gated routes, `is_admin` flags, admin panels, separate auth flows, RBAC tables.
   2. **Installer / deployer / operator.** Is there someone who installs, deploys, configures, or operates the system — distinct from the end user? Look for: deployment docs, infra-as-code, ops runbooks, CI/CD configuration, on-call rotations referenced in code or docs.
   3. **Structure-creating user.** Is there a user who creates or configures the structure (organizations, projects, leagues, tenants, schemas) that other users then consume? Look for: create-*.tsx, "owner of" relationships, tenant-bootstrap flows, schema-creation surfaces.
   4. **API / integration consumer.** Is there an API or integration consumer distinct from the end user — a partner system, SDK consumer, webhook receiver, or programmatic caller? Look for: public OpenAPI/GraphQL schemas, webhook surfaces, OAuth client registration, API key management.
7. After generating personas, confirm coverage: are there usage patterns in the evidence that no generated persona represents? If so, either generate an additional persona or record the gap as a watchpoint.
8. **Update `docs/agents/platform-mapping.md` with the newly-generated personas.** Append rows under the Personas section for each persona doc generated in step 4 (one row per persona; `<persona-name> | `Role:` <slug>, `Category: persona` | `docs/agents/personas/<slug>.md` `). If a Personas section does not yet exist in `platform-mapping.md`, add it under the Canonical Factor Docs section using the same table shape used elsewhere in the file. The persona is invisible at the platform-mapping surface until this step runs, even though the docs exist on disk — the file is the availability matrix the framework consults for "who can be invoked on this project."

Guardrails:

- When evidence is thin, record explicit **unknown** gaps in journal or wave watchpoints instead of inventing operators or workflows.
- Do not generate personas without evidence or user confirmation. Speculative personas produce misleading acceptance signals.
- Do not conflate persona agents with agent roles. Personas live in `docs/agents/personas/`, agent roles live in `docs/agents/`.
- Start with the smallest well-grounded set. A single well-defined persona is more useful than five vague ones.
- Personas should challenge designs and surface edge cases, not rubber-stamp them. Ground their feedback in their specific workflows and failure modes.
- Persona salience triggers must be job-specific and evidence-based. Do not invent emotional states; record operational impact signals that affect software delivery, acceptance, trust, or supportability.
- Do not promote repeated historical guidance into persona docs unless it is specifically about the user's experience — system-level lessons belong in core memory and agent journals.


## Persona Doc Structure

Persona docs-lint contract (exact structure the docs gate enforces — author to these literally):

- **`Role:` / `Category:` metadata is required.** Every persona doc must carry, near the top, a `Role:` line whose value exactly matches the filename slug (`Role: <slug>` for `docs/agents/personas/<slug>.md`) and `Category: persona`. A missing `Role:` makes the persona invisible to the dashboard; the `Category:` must be exactly `persona`. Template:

  ```
  Role: <slug>
  Category: persona
  ```

- **Required `##` headings, verbatim and case-sensitive** — every persona file must contain each of these exactly (note the lowercase after the first word in `Failure modes`, `Invocation signals`, `Operating identity`, `Salience triggers`):
  - `## Who`
  - `## Goals`
  - `## Workflows`
  - `## Failure modes`
  - `## Invocation signals`
  - `## Operating identity`
  - `## Salience triggers`
  - `## Associated journal`
- **Bullets, not prose or numbered lists.** Each of those eight sections must contain at least one `-` bullet — lead every content line with `- `.
- **`## Operating identity`** must describe the persona perspective or role (one of: persona, perspective, role, evaluate, protect).
- **`## Salience triggers`** must contain at least one salience-marker word: `critical`, `high`, `medium`, `low`, `operator`, `compaction`, `restart`, `regression`, `security`, `release`, or `trust`.
- **`## Associated journal`** must reference an existing journal file as a bullet in the exact path form `- docs/agents/journals/<slug>.md` — and that file must exist on disk (generate the persona journal per step 5 first).

**Do not add a `## Scope` section.** `## Scope` is a plan/change doc concept — it describes what a wave or change covers. It has no meaning in a persona doc, which defines a user or operator role, not a delivery boundary. The docs gate rejects any persona doc that contains `## Scope`.

Persona docs use only these sections (short reference):

**Who** · **Goals** · **Workflows** · **Failure modes** · **Invocation signals** · **Operating identity** · **Salience triggers** · **Associated journal**

**Do not include wave-id references in persona doc content.** A wave-id records when a persona was synthesized — it is synthesis metadata, not part of the persona's definition. Wave-id references belong in wave records and change docs, not in persona docs. A persona's evidence should be embedded inline in the **Who** and **Goals** sections where it is contextually useful (e.g. "Evidence: E2E fixtures distinguish admin vs. non-admin users in `apps/web/e2e/...`").
