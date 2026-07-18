# Council Review

Owner: Engineering
Status: active
Last verified: 2026-07-17

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
- **Verify code-grounded:** check the artifact's load-bearing claims against the actual tree, not against the artifact's own prose — cited `file:line` sites and symbols must resolve, "X already does Y" claims must hold in the code, and "no other caller/site" censuses must be complete. Do not approve an artifact whose claims were checked only against its own text. (A readiness review answerable purely from plan prose is how nonexistent symbols, wrong caller censuses, and no-op mechanisms pass review.)

Default fixed seats: `architecture-reviewer`, `security-reviewer`, `qa-reviewer`, `reality-checker`.

### Rotating Fifth Seat

Run after the fixed seats with full briefing including primer. Primary job: surface the strongest alternative the artifact did not take, worked out enough to be actionable. If no stronger alternative exists, say why.

Select from wave/artifact evidence: `docs-contract-reviewer` for prompt/seed/contract work, `performance-reviewer` for indexing/search/hot-path work, `release-reviewer` for packaging, or an applicable persona when operator-facing behavior is central.

### Challenge Round (optional)

Trigger at most one targeted challenge round when the `seat_agreement_aggregate` is `split` — or when `max_severity` is `high`/`critical` and seats disagree on whether it blocks. `red-team` may run in `council-seat` mode here if a second adversarial pass is warranted.

### Synthesis

`wave-council` synthesizes across primer + all seat outputs. See `docs/agents/specialists/wave-council.md`.

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

When the review is used for `Prepare wave`, the recorded verdict must be written back into `## Review Checkpoints` as a structured `prepare-council` line containing `moderator`, `primer-depth`, `seats`, `rotating-seat`, `strongest-challenge`, and `strongest-alternative`. The lifecycle gate only accepts that structured verdict, not a freeform marker.

**Roster honesty:** the `seats:` field lists the seats *actually run*, each at most once — never paste the template's example roster verbatim. A rotating pick that is also a fixed seat appears once in `seats:` and is identified by the `rotating-seat:` field. Every listed seat (other than the `red-team` primer and the `wave-council` moderator) must have recorded evidence in the wave record — a finding or an explicit no-findings note in `## Prepare Review Evidence`, `## Review Evidence`, or a `## Review Checkpoints` entry other than the verdict line itself. docs-lint flags rostered seats with no recorded evidence: a seat named only inside its own verdict line does not self-certify.

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
| **Framework config review** | Removal-biased audit of the agent operating surface (config/seeds/prompts/constraints/docs) — not an artifact review |

<!-- wave:executable-review-evidence begin — generated by render_agent_surfaces.py; preserve project-authored content outside this region -->
## Executable review evidence

Follow the canonical **Executable Review Evidence Protocol** in
`.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md` for material
approval claims and blocking findings. Exercise the public or registered
path when one exists; keep state/interleaving probes within the protocol's
finite risk-selected budget; record expected versus observed evidence and
honest limitations; and never broaden task authority to run destructive,
external, credential-bearing, or cost-bearing probes.

Do not hand-author canonical JSONL when the lifecycle coordinator exposes
the typed review-evidence authoring surface. Reviewers supply the
load-bearing judgment facts to that coordinator; the authoring surface
derives only bookkeeping, appends the fixed sibling
`docs/waves/<wave>/events.jsonl` authority, and rebuilds the compact
Markdown current-state projection in `wave.md`. A role without lifecycle
mutation authority returns those facts to its coordinator instead of
writing wave state.

After validation, apply the ordered four-way actionability gate:
`do_now`, `maybe_later`, `dont_do_later`, or `not_issue`. Complete bounded
`do_now`/`maybe_later` work before closure, create no backlog for rejected
states, and use focused repair replay unless a load-bearing boundary change
objectively requires a full council.
<!-- wave:executable-review-evidence end -->
