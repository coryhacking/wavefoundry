# Review System Overview

## Purpose

Explain the shared Wave Framework review model: what review is for, how it fits into a wave, and where project-specific gate logic belongs.

## Shared Review Model

- Review begins with a readiness evaluation before implementation and continues with implementation-time and final review passes as the wave progresses.
- Required review depth depends on change type, risk, and project policy.
- The shared framework supplies generic review lanes and expects seeded repositories to define exact triggers and local reviewer surfaces.
- A wave is not complete until required review outputs are collected and addressed.
- The same readiness evaluation used before implementation should be rerun during final review before closure.

## Wave Council Meta-Review

Projects may enable **Wave Council** as a universal meta-review for every wave. Wave Council does **not** replace specialist review lanes. It adds two required synthesis checkpoints:

- **`wave-council-readiness`** — before implementation begins
- **`wave-council-delivery`** — after implementation and before closure

Wave Council uses a structured protocol:

1. A fixed briefing packet is assembled for the relevant phase.
2. Each council seat reviews that packet in isolation.
3. The **council-moderator** synthesizes the seat outputs into a single verdict.
4. When seats materially disagree, the council-moderator may run **one targeted challenge round** on the disputed claims only.

The council-moderator is distinct from the wave-coordinator. The wave-coordinator owns lifecycle routing, readiness, and closure state. The council-moderator owns council synthesis and council verdict text.

### Default seat model

The framework default is **five seats**:

- `architecture-reviewer`
- `security-reviewer`
- `qa-reviewer`
- `reality-checker`
- one rotating domain seat selected from repo-local evidence, such as `performance-reviewer`, `docs-contract-reviewer`, `release-reviewer`, or an applicable persona

Projects may adapt the rotating-seat policy locally, but the non-waiver rule is framework-wide: **Wave Council may summarize or escalate specialist findings, but it may not waive blocking required lanes by itself.**

## Generic Review Lanes

The framework commonly expects some combination of these lanes in seeded repositories:

- **operator review** — mandatory for all waves; the operator must explicitly approve before `wave_close` is called (see below)
- code correctness and maintainability review
- QA / verification review
- architecture and boundary review
- security review
- performance review
- docs-contract review
- release / packaging review

## Inferential Sensor Lanes

Inferential sensors are LLM-run reviewer agents that assess semantic quality. The framework ships three canonical inferential sensor seeds:

| Lane name (= `required_review_lanes` key) | Seed |
|---|---|
| `architecture-review` | `214-architecture-reviewer.prompt.md` |
| `security-review` | `213-security-reviewer.prompt.md` |
| `performance-review` | `212-performance-reviewer.prompt.md` |

### Declaring required lanes

Projects declare which lanes are required in `docs/workflow-config.json`:

```json
{
  "required_review_lanes": ["security-review", "architecture-review"]
}
```

`wave_review` reads this config and includes all declared lanes in `required_lanes` alongside the always-required operator lane. `wave_close` blocks if any declared lane lacks a recorded signoff.

Projects that enable Wave Council should also declare an explicit council policy in `docs/workflow-config.json`, for example:

```json
{
  "wave_council_policy": {
    "enabled": true,
    "required_for_all_waves": true,
    "evidence_section": "## Review Evidence",
    "transition_policy": "applies-from-next-prepare",
    "phases": {
      "prepare": {
        "signoff_key": "wave-council-readiness",
        "moderator_role": "council-moderator"
      },
      "review": {
        "signoff_key": "wave-council-delivery",
        "moderator_role": "council-moderator"
      }
    }
  }
}
```

`transition_policy` controls rollout for waves already in flight. The framework default, `applies-from-next-prepare`, means:

- the next `Prepare wave` pass must record `wave-council-readiness`
- waves already past readiness still require the delivery-phase council pass before closure
- closure does not retroactively require a missing readiness signoff for a wave that never re-entered `Prepare wave`

### Recording signoff

After running an inferential sensor, record its verdict in the `## Review Evidence` section of `wave.md` using this format:

```
- security-review: approved
- architecture-review: approved-with-notes (medium — no boundary violations; layering-rules.md absent)
- performance-review: needs-revision (high — O(n²) loop in chunker.py:142)
```

The format is: `- <lane-name>: <verdict> [(<severity> — <one-line summary>)]`. The severity annotation is required when severity is `medium` or above.

When Wave Council is enabled, record the machine-readable council signoffs in the **same** `## Review Evidence` section:

```
- wave-council-readiness: approved (moderator: council-moderator — seats aligned on scope, lane selection, and protected surfaces)
- wave-council-delivery: approved-with-notes (moderator: council-moderator — ship path accepted; follow-up docs-contract work noted)
```

Keep the detailed narrative synthesis in `## Review checkpoints`. At minimum, record:

- the full seat roster for the phase, including the rotating fifth seat
- the moderator's synthesis summary
- any material disagreements between seats
- how those disagreements were resolved, or why they remain unresolved

This preserves a single machine-readable evidence location while leaving tradeoff reasoning in the wave narrative.

### Severity levels

Each inferential sensor verdict includes a `severity` field. Levels and their meaning:

| Level | Meaning |
|---|---|
| `critical` | Exploitable vulnerability, data loss, or structural architecture break — must be resolved before closure |
| `high` | Significant regression or boundary violation — requires operator attention before closure |
| `medium` | Suboptimal pattern with no immediate impact — should be addressed but does not block |
| `low` | Minor drift or style issue — advisory only |
| `none` | No findings |

When `max_severity` is `critical` or `high`, `wave_review` emits a `high_severity_finding` advisory diagnostic to direct operator attention before closure.

## Operator Review Lane

The operator review lane is required for every wave. It gives the operator an opportunity to do manual testing, spot-checks, or any other review before the wave is permanently sealed. Approval is satisfied by either of two paths:

1. **Operator-initiated close** — the operator explicitly asks to close the wave (e.g., "close the wave", "yes, close it") in the current session. This constitutes implicit approval.
2. **Agent-prompted approval** — the agent asks the operator for review approval before calling `wave_close`. The prompt should invite the operator to do any manual tests or review they want. The operator's positive confirmation is the approval.

When the agent is about to call `wave_close(mode="create")` and the operator has not already issued a close request in the current session, the agent **must** pause and ask for operator approval before proceeding.

The machine-readable marker for this lane is the line `operator-signoff: approved` in the `## Review Evidence` section of `wave.md`. `wave_review` returns a lint error if this line is absent, and `wave_close` blocks until it is present.

## Stateful Logic And Re-Entrant Review (Shared Heuristic)

Seeded closure and review prompts (`190-finalize-feature.prompt.md`, `docs/prompts/review-wave.prompt.md`) should steer `code-reviewer` and `qa-reviewer` toward bugs that only appear across **repeated calls** or **incomplete branches**:

- **Per-key mutable state** (dictionaries, caches, grace timestamps): reviewers should verify **set / clear / leave unchanged** on **every** exit from the control-flow region that references the state, including `else` arms when a boolean gate (for example `powerStateChanged`) splits mismatch vs match paths.
- **Re-entrancy**: if a function runs every step, tick, or timer fire, reviewers should ask what happens to that state when the **same** external condition holds on consecutive calls (stale timestamps, leaked entries).
- **Parallel helpers**: when two functions implement the same policy (for example `*WithDelays` vs a simpler checker), reviewers should compare them for **symmetry** unless the change doc records an intentional difference.

This complements **docs-contract review** (spec vs code): contract review catches documented invariants; **code review** catches branch gaps the spec did not yet encode.

## Relationship To Personas

- Personas may add specialized domain context to a review, but they do not replace the repository's generic review gates.
- Repo-local policy should decide when persona participation is selected during readiness evaluation and whether those persona findings are gating.
- Shared framework guidance assumes persona lanes can be required both before implementation and again at final review when the delivered behavior warrants it.
- An applicable persona may also serve as the rotating fifth Wave Council seat when the repo-local council policy says persona evidence is part of the decision.

## Seeded Repository Expectations

Init and upgrade should generate or refresh review docs in the repository that define:

- the actual reviewer roles available in the repository
- whether Wave Council is enabled and, if so, which phases and seat templates are required
- which change types trigger which review lanes
- how the readiness evaluation selects implementer lanes, reviewer lanes, and persona lanes before implementation begins
- how the readiness evaluation selects or confirms the rotating fifth Wave Council seat
- what evidence each reviewer should inspect
- which reviewer, council, and persona outputs are gating for readiness and closure

In a seeded project, that local source of truth lives in `docs/contributing/review-and-evals.md` plus related agent-role docs.

## Related Docs

- `.wavefoundry/framework/seeds/001-feature-wave-framework-overview.md`
- `docs/contributing/review-and-evals.md`
- `docs/contributing/agent-team-workflow.md`
