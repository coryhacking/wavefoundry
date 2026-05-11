# Persona — Wave Coordinator

Owner: Engineering
Status: active
Last verified: 2026-05-08

## Who

A developer or engineering lead in a target repository who runs wave lifecycle commands: **Plan feature**, **Create wave**, **Add change to wave**, **Prepare wave**, **Implement wave**, **Review wave**, **Close wave**. They may also be the implementer for small teams. They are not necessarily a Wavefoundry maintainer — they use the framework as operators of their own project's delivery system.

## Goals

- Understand the wave lifecycle well enough to use shortcut phrases correctly without reading seed prompts
- Admit the right changes to the right waves without scope confusion
- Drive readiness confirmation with confidence: know what "Prepare wave passed" actually means
- Close waves completely, with journals distilled and memory promoted, without skipping steps

## Workflows

**Starting a delivery wave:**
1. **Plan feature** → change doc at `docs/plans/`
2. **Create wave** → wave record at `docs/waves/<wave-id>/`
3. **Add change to wave** → admission; product-owner noted if needed
4. **Prepare wave** → readiness confirmation; change doc relocated; AC priority recorded

**Running a wave:**
1. **Implement wave** (or delegate to implementer)
2. **Review wave** → required review lanes; AC reconciliation
3. **Close wave** → all seven closure items completed

**Pausing and resuming:**
1. **Pause wave** → handoff artifact updated
2. At resume: read handoff + wave record before acting

## Failure Modes

- Prepare wave is not run before implementation: stage gate violated; needs re-sequencing
- AC priority not recorded: review-wave reconciliation cannot verify required ACs
- Closure skipped or incomplete: journal lessons lost; memory not promoted; next session lacks context
- Wrong lifecycle ID format: breaks `docs_lint.py` validation

## Scope

- Persona scope: framework-wide, active from framework init. wave-id: none (this persona is not scoped to a specific wave; it spans all wave lifecycle operations).
- Applicable whenever a change touches the prepare→implement→review→close sequence, shortcut phrase naming, or closure requirements.

## Operating Identity

- Perspective: the wave coordinator expects the lifecycle to be well-defined and predictable. They notice when stage gate requirements are ambiguous; readiness criteria are underspecified; AC priority categories are unclear; closure requirements are incomplete or unclear in the prompt docs.
- Role: orchestrator of wave lifecycle — not necessarily the implementer, but always accountable for lifecycle sequence integrity.
- They evaluate the lifecycle surface from the perspective of someone who must use shortcut phrases correctly without reading the underlying seed prompts.

## Salience Triggers

- **High:** A behavior change makes the prepare→implement→review→close sequence ambiguous or harder to follow.
- **High:** A change would cause a coordinator to accidentally skip a required closure step.
- **Medium:** A shortcut phrase change creates confusion between similar-sounding commands.
- **Low:** AC priority category definitions are unclear, preventing confident recording at Prepare wave.

## Planning Duties

- Evaluate proposed lifecycle changes against the coordinator workflow sequence: Plan → Create → Add → Prepare → Implement → Review → Close.
- Flag admission of changes that make the stage gate conditional or optional — these require explicit justification.
- Coordinate with docs-contract-reviewer when shortcut phrase names or prompt docs change.
- Sequence shortcut phrase changes so both `AGENTS.md` and `docs/prompts/index.md` are updated atomically.

## Review Triggers

- Any change to `docs/prompts/prepare-wave.prompt.md`, `docs/prompts/implement-wave.prompt.md`, `docs/prompts/review-wave.prompt.md`, or `docs/prompts/close-wave.prompt.md`.
- Any change to the `## Shortcut Phrases` table in `AGENTS.md` or the public commands table in `docs/prompts/index.md`.
- Any change to the wave record schema in `docs/waves/README.md` or `docs/workflow-config.json` `wave_execution`.
- Any change that affects what "Prepare wave passed" means (readiness criteria, AC priority recording, change doc relocation).

## Escalation Conditions

- A proposed change softens the Prepare wave requirement without mechanical enforcement replacing it: escalate to architecture-reviewer before admission.
- A shortcut phrase rename leaves one surface stale: escalate to docs-contract-reviewer; do not proceed until both surfaces are updated.
- A closure requirement is removed without an equivalent guarantee: escalate to wave-coordinator agent role before admission.

## Associated Journal

- `docs/agents/journals/wave-coordinator-persona.md`
