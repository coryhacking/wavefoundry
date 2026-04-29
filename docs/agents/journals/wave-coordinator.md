# Journal — Wave Coordinator

Owner: Engineering
Status: active
Last verified: 2026-04-28

Actor: wave-coordinator
Schema version: 1.0
Last distilled: 2026-04-28

## Operating Identity

- Role: wave-coordinator — the agent role responsible for running wave lifecycle commands (Plan feature, Create wave, Add change to wave, Prepare wave, Implement wave, Review wave, Close wave) on the Wavefoundry repository.
- Responsibilities include: stage gate enforcement before implementation, AC priority recording at Prepare wave, complete closure including journal distillation and memory promotion.

## Salience Triggers

- **High:** Stage gate violated — implementation attempted without a clean Prepare wave pass. Stop, re-sequence.
- **High:** AC priority not recorded at Prepare wave — Review wave reconciliation cannot verify required ACs.
- **Medium:** Closure incomplete — journal distillation skipped or memory not promoted at Close wave.
- **Medium:** Operator requests a lifecycle step that conflicts with the current wave state (e.g., Close wave before Review wave completes).
- **Low:** Shortcut phrase ambiguity — coordinator invokes the wrong prompt due to similar-sounding command names.

## Recent Captures

- None at init. This journal was seeded at framework install with no prior wave history.

## Distillation

- **Self-hosting symlink invariant:** `.wavefoundry/framework` is a symlink to `../framework`. All canonical script paths resolve through the symlink. If scripts behave unexpectedly, verify with `ls -la .wavefoundry/framework`.
- **Lifecycle ID epoch is fixed:** `epoch_utc: "2022-04-28T00:00:00Z"` was set at init from the greenfield fallback. Do not re-anchor this value — it invalidates all existing wave and change IDs.
- **Stage gate must precede all framework edits:** Any edit to `framework/scripts/` or `framework/seeds/` requires a clean Prepare wave pass as the immediately preceding lifecycle step.

## Promotion Evidence

- Lessons about self-hosting symlink and lifecycle ID epoch have been promoted to `docs/references/project-context-memory.md` at init.
- Future promotions: record incident here with reference to the target doc (e.g., `docs/references/project-context-memory.md`).

## Retirement And Supersession

- No entries are retired at init.
- Retire an entry when: its root cause is structurally resolved, the constraint no longer applies, or the context has been superseded by a wave decision. Mark as superseded with a note referencing the superseding wave.

## Governance

- No secrets, credentials, or PII in journals.
- Sensitive coordinator findings (e.g., trust boundary violations, security-relevant decisions): redact detail; note that the full record is in a secure channel.
- Review: distill at every wave closure; promote repeated, validated lessons to `docs/references/project-context-memory.md`.
- Retire entries when the constraint is no longer load-bearing. Delete retired entries after one wave cycle.

## Active Watchpoints

- **Watchpoint:** Self-hosting mode — `.wavefoundry/framework` is a symlink; scripts using the path via the symlink resolve correctly, but if the symlink is broken, all framework scripts fail silently. Check `ls -la .wavefoundry/framework` if scripts behave unexpectedly.
- **Watchpoint:** Stage gate must be enforced before any code edit to `framework/scripts/` or `framework/seeds/`. The coordinator must verify Prepare wave passed before delegating to an implementer.
- **Follow-up:** When MCP server scaffolding begins, update `docs/architecture/current-state.md` and re-evaluate factor 07 (port binding) and factor 09 (disposability) in `docs/repo-profile.json`.
