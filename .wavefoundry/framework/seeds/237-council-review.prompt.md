# Council Review

**Applicable when:** `wave_review.enabled` is true (framework default) and a council review is being run.

Owner: Engineering
Status: active
Lane: council-review
Last verified: 2026-05-24

**Shortcut phrases:** `Council review` · `Run council` · `Wave Council review`

Run a full Wave Council review on any artifact — a plan, implementation, decision, change doc, design, or approach. Use this whenever you want the structured two-phase adversarial review outside the normal wave lifecycle.

> **Note:** Standalone council reviews are advisory. They do not record `wave-council-readiness` or `wave-council-delivery` lifecycle signoffs in `## Review Evidence`. Those signoffs require the prepare-wave and review-wave lifecycle paths respectively.

---

## Protocol

### Phase 1 — Red-Team Adversarial Primer

Run `red-team` in `council-adversarial-primer` mode in isolation before any other seat. See `docs/agents/specialists/red-team.md`.

The wave-council declares a **primer depth tier** before Phase 1 runs:

| Tier | Stances | `primer_questions` | When |
|---|---|---|---|
| `lightweight` | 1 (most relevant) | 1 | Doc/style/minor config; no trust boundary; single-module |
| `standard` | 3 | 2 | Implementation changes; clear scope; no trust boundary crossing |
| `full` | All 5 | 3 | Trust boundary, architectural, data-path, security, or cross-cutting changes |

The five thinking stances:
- *Adversarial*: how can this be broken, bypassed, or exploited?
- *Constructive*: what alternative design or approach produces a better outcome?
- *Simplicity*: is this over-engineered — what minimal version delivers most of the value?
- *First-principles*: starting fresh with current knowledge, what would we build instead?
- *Analogical*: what would a different domain, framework, or pattern do here?

Produce: `strongest_challenge`, `best_alternative`, `thinking_stances_applied`, `consequence_of_current_path`, `primer_questions` (count per tier above).

Add the primer output to the briefing packet. Every subsequent seat receives it.

### Phase 2 — Fixed Seats

Run each fixed seat in isolation. Each seat receives the standard briefing plus the Phase 1 primer and must:
- Explicitly address the red-team's `strongest_challenge`
- Answer the `primer_questions` from their lane's perspective
- Contribute lane-specific findings independent of the primer

Default fixed seats: `architecture-reviewer`, `security-reviewer`, `qa-reviewer`, `reality-checker`.

### Rotating Fifth Seat

Run after the fixed seats with full briefing including primer. Primary job: surface the strongest alternative the artifact did not take, worked out enough to be actionable. If no stronger alternative exists, say why.

Select from wave/artifact evidence: `docs-contract-reviewer` for prompt/seed/contract work, `performance-reviewer` for indexing/search/hot-path work, `release-reviewer` for packaging, or an applicable persona when operator-facing behavior is central.

### Challenge Round (optional)

Trigger at most one targeted challenge round when the `seat_agreement_aggregate` is `split` — or when `max_severity` is `high`/`critical` and seats disagree on whether it blocks. `red-team` may run in `council-seat` mode here if a second adversarial pass is warranted.

### Synthesis

`wave-council` synthesizes across primer + all seat outputs. See `docs/agents/wave-council.md`.

The first synthesis pass runs on **anonymized** seat outputs (seat/role identity stripped, labeled `Seat 1..N` in randomized order) so findings are weighed on merit before identity is re-attached. **Non-waiver guard:** anonymization governs only the convergence/agreement assessment — a finding carrying blocking authority from a required specialist lane keeps its lane attribution and blocking status at all times and is never merit-weighted below blocking.

Synthesis must include:
- Red-team primer summary: what it surfaced and how seats responded
- Seat roster and rotating seat "best alternative" brief
- `seat_agreement_aggregate`: `seat_agreement` (`unanimous` / `majority` / `split`) and `max_severity` (`critical`/`high`/`medium`/`low`/`none`) — the triage signal that drives the challenge-round trigger
- Strongest points of agreement
- Material disagreements and how they were resolved or left unresolved
- `strongest_alternative`: the best alternative surfaced, with "this would be better because..." reasoning
- `improvements_recommended`: concrete improvements regardless of verdict
- Final verdict: **pass**, **pass with conditions**, or **blocked**

When this review is used to satisfy `Prepare wave`, the verdict must be recorded in `## Review Checkpoints` as a structured `prepare-council` line containing `moderator`, `primer-depth`, `seats`, `rotating-seat`, `strongest-challenge`, and `strongest-alternative`. A freeform marker is not sufficient for the lifecycle gate.

---

## Inputs

Provide any of the following as context before saying "Council review":
- A change doc, wave record, or plan
- A block of code or implementation
- A design, decision, or approach described in plain language
- A specific question ("Is this the right approach?")

The council reviews what you give it. If the artifact is ambiguous, the red-team primer will surface the ambiguity as a `primer_question`.

---

## Relationship to Other Commands

| Command | When to use |
|---|---|
| **Council review** | Any artifact, any time — standalone adversarial + council pass |
| **Archetype review** | Optional stance-based supplement when the artifact's load-bearing surface is AC text precision, prose, decision narrative, or naming. Wave Council remains required; Archetype Council runs *in addition*, not in place of. Does not record `wave-council-readiness`. Seed: `236-archetype-council.prompt.md` |
| **Prepare wave** | Lifecycle gate — council readiness pass is embedded; records `wave-council-readiness` signoff |
| **Review wave** | Lifecycle gate — council delivery pass is embedded; records `wave-council-delivery` signoff |
| **Evaluate decision** | Architecture/technology decision specifically — produces an ADR |
| **Interrogate this plan** | Stress-test a plan's unresolved decision branches before admission |
| **Framework config review** | Removal-biased audit of the agent operating surface (config/seeds/prompts/constraints/docs) — not an artifact review. Seed: `238-framework-config-review.prompt.md` |

## Project Harness Extensions

<!-- Fill from target repository evidence during upgrade render. Never add product-specific content to this seed body. -->

## Moderator Synthesis: Fix-Now-or-Justify (wave 1304x / 1305d)

**The default verdict format distinguishes two pass modes:**

1. **PASS WITH IN-SESSION FIXES** — small findings (≤20 LOC, no contract change) were applied during the review pass. List each fix with a one-line description. The wave can close after the fixes land and tests re-run green.

2. **PASS WITH FOLLOW-ON** — one or more findings were genuinely outside the in-session-fix threshold. For each finding routed to follow-on, the synthesis **must** include a one-line justification explaining *why* it isn't fixable in-session. Acceptable justifications: "exceeds ~20 LOC", "changes the response shape contract", "requires a new design decision not made by the wave", "requires measurement that hasn't been done".

**Unacceptable justifications:** "small but worth doing later", "could be addressed in a follow-on plan", "honest AC partial". These are the silent-defer patterns that produce long-tail technical debt across waves. If the moderator finds itself writing one of these, the correct move is to route the finding back to the relevant lane for in-session fix.

A wave that ships with three findings — two fixed in-session, one genuinely deferred with justification — is a healthier outcome than the same wave shipping with all three filed as follow-on plans. The cumulative effect over many waves is the difference between rising and falling code quality.

