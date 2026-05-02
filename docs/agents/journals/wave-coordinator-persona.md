# Journal — Wave Coordinator Persona

Owner: Engineering
Status: active
Last verified: 2026-05-02

Actor: wave-coordinator (persona)
Schema version: 1.0
Last distilled: 2026-04-28

## Operating Identity

- Persona: wave-coordinator — represents the developer or engineering lead in a target repository who runs wave lifecycle commands and drives readiness confirmation.
- Perspective: the coordinator expects the lifecycle to be well-defined and predictable. They notice when stage gate requirements are ambiguous, readiness criteria are underspecified, or closure requirements are unclear.

## Salience Triggers

- **High:** A behavior change makes the prepare→implement→review→close sequence ambiguous or harder to follow — record before accepting the change.
- **High:** A change would cause a coordinator to accidentally skip a required closure step — this is a persona-level regression.
- **Medium:** A shortcut phrase change creates confusion between similar-sounding commands — test phrase distinctiveness before accepting.
- **Low:** AC priority category definitions are unclear — coordinator cannot confidently record required vs. recommended ACs at Prepare wave.

## Distillation

- **Shortcut phrase surface must stay in sync:** The coordinator learns shortcut phrases from `AGENTS.md`. The prompt docs live in `docs/prompts/`. If these diverge, the coordinator will invoke the wrong prompt. Any shortcut phrase name change must update both surfaces atomically.
- **Prepare wave is not optional:** Any change to the lifecycle that softens the Prepare wave requirement (makes it conditional, adds an override path, or makes the stage gate ambiguous) must be reviewed against this persona. Skipping Prepare wave produces an unreviewed implementation.

## Active Signals

- None. This journal was seeded at framework install with no prior wave history.

## Promotion Evidence

- No lessons promoted yet at init. Future promotions: reference `docs/references/project-context-memory.md` when coordinator-facing regressions recur across waves (e.g., shortcut phrase divergence being a recurring stumbling block).

## Retirement And Supersession

- No entries are retired at init.
- Retire the shortcut phrase sync lesson if a formal sync validation is added to docs-lint.
- Retire the Prepare wave lesson if the stage gate is mechanically enforced by a CI check rather than relying on coordinator discipline.

## Governance

- No secrets, credentials, or PII in journals.
- Sensitive coordinator observations (e.g., security-relevant lifecycle gaps): redact and note the secure channel.
- Review: distill at wave closure; promote repeated coordinator pain points to `docs/references/project-context-memory.md`.
- Delete retired entries after one wave cycle.

## Active Watchpoints

- **Watchpoint:** The coordinator-facing shortcut phrase surface (`AGENTS.md` `## Shortcut Phrases` table and `docs/prompts/index.md` public commands table) must stay in sync. If a shortcut phrase is renamed in one location, both must be updated in the same change.
- **Watchpoint:** The prepare→implement→review→close sequence is the core contract for the coordinator. Any change that makes this sequence ambiguous is a coordinator-facing regression.
- **Watchpoint:** AC priority recording happens at Prepare wave. If the prepare-wave prompt doc does not explicitly require AC priority to be recorded in the change doc, the reviewer cannot verify required ACs at Review wave.
