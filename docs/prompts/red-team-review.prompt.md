# Red-Team Review

Owner: Engineering
Status: active
Last verified: 2026-08-14

**Shortcut phrases:** `Red-team review` · `Red team this`

Run the `red-team` specialist in isolation against one artifact — a plan, code change, ADR, design, prose document, workflow, or decision narrative — producing a single sharp adversarial challenge with named failure modes and a strongest-alternative, without convening a council and without recording any review authority.

This is the standalone form of the capability `docs/agents/specialists/red-team.md` already defines. Reach for **Council review** when the artifact needs multiple specialist seats, **Archetype review** when it needs multiple stance-based seats, and **Interrogate this plan** when the artifact is a change doc heading for wave admission; the chooser table in `docs/prompts/archetype-council.prompt.md` routes among them.

---

## Contract

### Input

Any single artifact the operator names or supplies. If the artifact is ambiguous, ask one clarifying question before running; a red-team pass against the wrong artifact is confident noise.

### Mode selection

Choose the standalone mode from `docs/agents/specialists/red-team.md` that fits the artifact:

| Artifact shape | Mode |
|----------------|------|
| "How can this be better / any gaps?" (default when no sharper fit) | `improvement-review` |
| Security-sensitive surface, input path, trust boundary | `abuse-path-review` |
| Implementation about to ship | `failure-pressure-test` |
| A chosen option or approach | `option-challenge` |
| Library / framework / tool / service commitment | `technology-evaluation` |
| Process or workflow design | `workflow-challenge` |
| Feature definition or requirements | `feature-definition-challenge` |
| Design or architecture proposal | `design-provocation` |

The specialist doc's mode list is not an exhaustive ceiling: when a better-grounded challenger lens exists for the specific artifact, apply that lens and name it. The council-bound modes (`council-adversarial-primer`, `council-seat`) are out of scope here — they run inside **Council review**, not standalone.

### Execution

Follow the specialist doc's Operating Invariants and produce its Output Shape unchanged — this command adds no schema of its own. Ground every challenge in the artifact and the tree (use the code and documentation retrieval tools); a challenge argued from memory of the artifact is not a red-team output.

### Recording

- Run against a wave artifact (an admitted change doc, a wave record, an implementation under an open wave): record the outcome as a dated entry in that wave's `## Review Checkpoints` section.
- Run against anything else: the output is conversation-level. No record is required to invoke this command.

### Authority boundary

This command records **no signoffs** and satisfies **no gate**. It is not a substitute for the Wave Council at Prepare wave or Review wave, and it never writes lane approvals, council verdicts, or `wave-council-*` signoffs. Hand credible security findings to `security-reviewer` per the specialist doc's Role Boundaries — red-team does not issue security verdicts.
