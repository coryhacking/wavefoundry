# Journal — Framework Operator Persona

Owner: Engineering
Status: active
Last verified: 2026-04-28

Actor: framework-operator (persona)
Schema version: 1.0
Last distilled: 2026-04-28

## Operating Identity

- Persona: framework-operator — represents the developer or engineering lead who installs, upgrades, and operates the Wave Framework in a target repository, consuming it as a dependency rather than as a maintainer.
- Perspective: the operator trusts the framework to handle complexity correctly and is not reading seed prompts directly — they read the rendered local surface and expect it to be self-contained.

## Salience Triggers

- **High:** A change makes the install or upgrade experience confusing for a first-time operator — record before accepting the change.
- **High:** A change could cause an operator to overwrite their own project-specific customizations unknowingly during upgrade — this is a regression.
- **Medium:** A change breaks the generated operator summary or makes it incomplete — the summary is a first-class deliverable.
- **Low:** Docs-lint failure after upgrade has an unclear fix path — the operator needs a clear error message pointing to `framework_revision` alignment.

## Recent Captures

- None at init. This journal was seeded at framework install with no prior operator interaction history.

## Distillation

- **Operator summary is a first-class deliverable:** The operator does not read seed prompts. The init output is the primary orientation artifact. Any change to seed-010 that reduces information density of the operator summary is a breaking change from the operator's perspective.
- **Upgrade overwrites risk:** Operator-customized prompt docs in `docs/prompts/` may be overwritten during upgrade if the upgrade seed does not distinguish framework-owned from operator-owned files. This risk is tracked in `docs/references/tech-debt-tracker.md` (DEBT-03 / DEBT-04).

## Promotion Evidence

- No lessons promoted yet at init. Future promotions: reference `docs/references/project-context-memory.md` when operator-facing regressions recur across waves (e.g., `framework_revision` mismatch being a recurring stumbling block).

## Retirement And Supersession

- No entries are retired at init.
- Retire the upgrade overwrites lesson once the upgrade seed implements a clear operator-owned vs. framework-owned file distinction.
- Retire the operator summary lesson if the init output format is formally specified in `docs/specs/`.

## Governance

- No secrets, credentials, or PII in journals.
- Operator-specific configuration details (e.g., epoch values from operator installations): do not record in this shared journal — these belong in the operator's own project journal.
- Review: distill at install-wave or upgrade-wave closure; promote recurring operator pain points to `docs/references/project-context-memory.md`.
- Delete retired entries after one wave cycle.

## Active Watchpoints

- **Watchpoint:** The operator-facing upgrade workflow depends on `wavefoundry-framework-<date><letter>.zip` being placed at the repository root. If the zip filename format changes, the **Upgrade wave framework** prompt doc must be updated simultaneously.
- **Watchpoint:** The operator summary (output of Init wave framework) must tell the operator: what files were installed, what the lifecycle looks like, how to generate IDs, and where config lives.
- **Watchpoint:** Docs-lint failure after upgrade is the most common operator failure mode. The fix path (`framework_revision` must match `.wavefoundry/framework/VERSION`) should be surfaced clearly in any upgrade error output.
