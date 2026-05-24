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

Wave Council uses a two-phase structured protocol:

1. The council-moderator declares a **primer depth tier** based on trust boundaries touched, files in scope, and change type:

   | Tier | Stances | `primer_questions` | When |
   |---|---|---|---|
   | `lightweight` | 1 (most relevant) | 1 | Doc/style/minor config; no trust boundary; single-module |
   | `standard` | 3 | 2 | Implementation changes; clear scope; no trust boundary crossing |
   | `full` | All 5 | 3 | Trust boundary, architectural, data-path, security, or cross-cutting changes |
2. **Phase 1 — Red-team adversarial primer**: `red-team` runs in `council-adversarial-primer` mode in isolation at the declared depth. Its output — `strongest_challenge`, `best_alternative`, `thinking_stances_applied`, `primer_questions` — is added to the briefing packet.
3. **Phase 2 — Fixed seats**: each fixed seat runs in isolation and receives the standard briefing *plus* the Phase 1 primer. Each seat must explicitly address the primer's `strongest_challenge` and answer `primer_questions` from its lane's perspective.
4. The rotating fifth seat runs after fixed seats and surfaces the strongest alternative the wave did not take.
5. The **council-moderator** synthesizes across primer and all seat outputs into a single verdict. The primer is first-class evidence in synthesis.
6. When seats materially disagree, the council-moderator may run **one targeted challenge round** on the disputed claims only.

The council-moderator is distinct from the wave-coordinator. The wave-coordinator owns lifecycle routing, readiness, and closure state. The council-moderator owns council synthesis and council verdict text.

### Default seat model

The framework default is a two-phase structure:

**Phase 1 — Adversarial primer (universal):**
- `red-team` — always runs first in `council-adversarial-primer` mode; not a configured fixed seat but a protocol-defined universal role present in every Wave Council regardless of `fixed_seats` configuration

**Phase 2 — Fixed seats (run after receiving the Phase 1 primer):**
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

## Agent Harness Core

All review lane participants share a common grounding contract defined in `209-agent-harness-core.prompt.md`. This seed defines:
- Evidence grounding table (repository evidence over memory; stricter project rules win; missing docs = gap to record)
- Briefing packet required fields: `wave_id`, `phase`, `change_ids`, `trust_boundaries_touched`, `files_in_scope`
- Finding record schema including `reachability` and `confidence` fields
- Reachability labels and coordination behaviors (narrow scope, no self-approval, split questions, parallel merge and deduplicate, gapfill pointer)

All participants must reference `209-agent-harness-core.prompt.md` for the briefing packet format and finding record schema.

## Inferential Sensor Lanes

Inferential sensors are LLM-run reviewer agents that assess semantic quality. The framework ships these canonical inferential sensor seeds:

| Lane name (= `required_review_lanes` key) | Seed |
|---|---|
| `architecture-review` | `214-architecture-reviewer.prompt.md` |
| `security-review` | `213-security-reviewer.prompt.md` |
| `performance-review` | `212-performance-reviewer.prompt.md` |
| `code-review` | `221-code-reviewer.prompt.md` |

## Harness Specialist Table

Harness specialists are invoked by the coordinator or council-moderator for targeted analysis. They are not required review lanes by default — they are activated by policy or coordinator decision.

| Specialist | Seed | Modes |
|---|---|---|
| `senior-engineering-challenger` | `217-senior-engineering-challenger.prompt.md` | `plan-challenge`, `delivery-challenge` |
| `environment-auditor` | `218-environment-auditor.prompt.md` | (single mode) |
| `operating-surface-gardener` | `219-operating-surface-gardener.prompt.md` | (single mode) |
| `reality-checker` | `216-reality-checker.prompt.md` | `assumption-audit`, `finding-validation`, `implementation-challenge` |
| `red-team` | `225-red-team.prompt.md` | `abuse-path-review`, `failure-pressure-test`, `option-challenge`, `technology-evaluation`, `workflow-challenge`, `feature-definition-challenge`, `design-provocation`, `council-adversarial-primer`, `council-seat` (non-exhaustive) |

## Question Ownership

Use this table to route questions to the correct lane:

| Question type | Assigned lane |
|---|---|
| Is this code correct? Does it satisfy the AC? | `code-review` |
| Can an attacker reach this code? What is the reachability? | `security-reviewer` |
| Is this assumption evidenced or fabricated? | `reality-checker` (`finding-validation` mode) |
| Is this plan internally consistent and pressure-tested? | `senior-engineering-challenger` (`plan-challenge` mode) |
| Is the delivered result genuinely complete? | `senior-engineering-challenger` (`delivery-challenge` mode) |
| What is the operating surface health? | `environment-auditor` |
| Is the project's agent-operating surface drifted? | `operating-surface-gardener` |
| How can this design/decision/workflow be broken, bypassed, or improved by a competing alternative? | `red-team` (mode depends on artifact: `abuse-path-review`, `failure-pressure-test`, `option-challenge`, `workflow-challenge`, etc.) |
| Which library/framework/tool is the best fit before we commit? | `red-team` (`technology-evaluation` mode) |
| Is this the right feature to build? | `red-team` (`feature-definition-challenge` mode) |

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

## Security Reachability Labels

When recording security findings, use the generic reachability labels defined in `209-agent-harness-core.prompt.md`:

| Label | Meaning |
|-------|---------|
| `reachable-from-caller-input` | An attacker or untrusted caller can reach this code through normal API or tool inputs |
| `reachable-from-untrusted-content` | The vulnerable behavior is triggered by content read from an untrusted source (e.g. user files, repository content, config) |
| `not-externally-reachable` | The code path is only reachable from internal or trusted caller contexts |

Example exploit-chain: a finding rated `low` for unsafe regex and a finding rated `medium` for missing escape together compose to `high` if an attacker can supply a crafted file name that reaches the regex via the untrusted-content path.

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
