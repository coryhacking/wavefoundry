# Council Review

Owner: Engineering
Status: active
Last verified: 2026-05-23

**Shortcut phrases:** `Council review` · `Run council` · `Wave Council review`

Run a full Wave Council review on any artifact — a plan, implementation, decision, change doc, design, or approach. Use this whenever you want the structured two-phase adversarial review outside the normal wave lifecycle.

> **Note:** Standalone council reviews are advisory. They do not record `wave-council-readiness` or `wave-council-delivery` lifecycle signoffs in `## Review Evidence`. Those signoffs require the prepare-wave and review-wave lifecycle paths respectively.

---

## Protocol

### Phase 1 — Red-Team Adversarial Primer

Run `red-team` in `council-adversarial-primer` mode in isolation before any other seat. See `docs/agents/specialists/red-team.md`.

The council-moderator declares a **primer depth tier** before Phase 1 runs:

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

Trigger at most one targeted challenge round when fixed seats materially disagree. `red-team` may run in `council-seat` mode here if a second adversarial pass is warranted.

### Synthesis

`council-moderator` synthesizes across primer + all seat outputs. See `docs/agents/council-moderator.md`.

Synthesis must include:
- Red-team primer summary: what it surfaced and how seats responded
- Seat roster and rotating seat "best alternative" brief
- Strongest points of agreement
- Material disagreements and how they were resolved or left unresolved
- `strongest_alternative`: the best alternative surfaced, with "this would be better because..." reasoning
- `improvements_recommended`: concrete improvements regardless of verdict
- Final verdict: **pass**, **pass with conditions**, or **blocked**

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
| **Prepare wave** | Lifecycle gate — council readiness pass is embedded; records `wave-council-readiness` signoff |
| **Review wave** | Lifecycle gate — council delivery pass is embedded; records `wave-council-delivery` signoff |
| **Evaluate decision** | Architecture/technology decision specifically — produces an ADR |
| **Interrogate this plan** | Stress-test a plan's unresolved decision branches before admission |
