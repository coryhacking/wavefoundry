# Journal — Wave Coordinator

Owner: Engineering
Status: active
Last verified: 2026-05-10

Actor: wave-coordinator
Schema version: 1.0
Last distilled: 2026-04-30

## Operating Identity

- Role: wave-coordinator — the agent role responsible for running wave lifecycle commands (Plan feature, Create wave, Add change to wave, Prepare wave, Implement wave, Review wave, Close wave) on the Wavefoundry repository.
- Responsibilities include: stage gate enforcement before implementation, AC priority recording at Prepare wave, complete closure including journal distillation and memory promotion.

## Salience Triggers

- **High:** Stage gate violated — implementation attempted without a clean Prepare wave pass. Stop, re-sequence.
- **High:** AC priority not recorded at Prepare wave — Review wave reconciliation cannot verify required ACs.
- **Medium:** Closure incomplete — journal distillation skipped or memory not promoted at Close wave.
- **Medium:** Operator requests a lifecycle step that conflicts with the current wave state (e.g., Close wave before Review wave completes).
- **Low:** Shortcut phrase ambiguity — coordinator invokes the wrong prompt due to similar-sounding command names.

## Distillation

- **Self-hosting path invariant:** `.wavefoundry/framework/` contains the canonical framework content. If scripts behave unexpectedly, verify with `ls .wavefoundry/framework/`.
- **Lifecycle ID epoch is fixed:** `epoch_utc: "2022-04-28T00:00:00Z"` was set at init from the greenfield fallback. Do not re-anchor this value — it invalidates all existing wave and change IDs.
- **Stage gate must precede all framework edits:** Any edit to `.wavefoundry/framework/scripts/` or `.wavefoundry/framework/seeds/` requires a clean Prepare wave pass as the immediately preceding lifecycle step.
- **`wave_current` envelope is a list:** `data.waves[]` — not `data.wave`. Every call site reading the current wave must use the list form; the old single-key form no longer exists.

## Active Signals

wave-id: `12cv4 prompt-indexing-quality`

- Closed: prompt indexing quality improvements, `.prompt.md` file extension rename, docs-first index onboarding guidance.

wave-id: `12d4b codebase-qa`

- Closed: Code Insight Agent (CIA) — codebase QA agent, knowledge extraction, code search result diversity, CIA seed distribution and agent guidance.

wave-id: `12bc4 journal-upgrade-coverage-gaps`

- Active: extending journal upgrade and distillation seeds to catch non-standard activity-log sections, missing Distillation sections, and dangling cross-references.

wave-id: `12ec2 index-build-stats-persistence`

- Closed 2026-05-06: persisted index build stats to `index-build-stats.json`; timing estimates in `wave_index_build` notices, `wave_index_build_status`, and `wave_index_health` responses. Fixed placeholder signoff bypass bug (`<approved...>` no longer counts as real signoff). Fixed `build_pack.py` excluding nested `.wavefoundry` dirs.

## Promotion Evidence

- Lessons about self-hosting path resolution and lifecycle ID epoch have been promoted to `docs/references/project-context-memory.md` at init.
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

- **Watchpoint:** Self-hosting mode — `.wavefoundry/framework/` is a real directory containing the canonical framework content. If this directory is missing or corrupted, all framework scripts fail. Check `ls .wavefoundry/framework/` if scripts behave unexpectedly; restore with `git checkout HEAD -- .wavefoundry/framework` if needed.
- **Watchpoint:** Stage gate must be enforced before any code edit to `.wavefoundry/framework/scripts/` or `.wavefoundry/framework/seeds/`. The coordinator must verify Prepare wave passed before delegating to an implementer.
- **Follow-up:** When MCP server scaffolding begins, update `docs/architecture/current-state.md` and re-evaluate factor 07 (port binding) and factor 09 (disposability) in `docs/repo-profile.json`.
