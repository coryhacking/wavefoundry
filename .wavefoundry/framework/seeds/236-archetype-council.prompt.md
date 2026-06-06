# Archetype Council

**Applicable when:** any project. The Archetype Council is operator-invoked, not default-required; this role doc exists so the surface is discoverable.

Owner: Engineering
Status: active
Lane: archetype-council
Last verified: 2026-06-03

**Shortcut phrases:** `Archetype review` · `Archetype council`

Run a stance-based council review on any artifact — plans, design documents, code, prose drafts, decision narratives, naming choices, AC formulations — where role-specialist seats are overkill or the wrong shape, and where orthogonal thinking-stance lenses (strategy, logic, durability, first-principles, wisdom, prose-craft, inversion) are what the artifact actually rewards. The archetypes are general-purpose lenses, not text-only critics; they apply equally to a system design, a refactor plan, a function diff, or a README section.

> **Note:** Archetype Council is **optional** and **operator-invoked**. It does not gate Prepare wave, Review wave, or Close wave. It complements the mandatory Wave Council; it does not replace it. The Wave Council remains required when `wave_review.enabled` is true.

---

## When To Use This Vs. Other Review Surfaces

| Surface | Shape | When |
|---|---|---|
| **`red-team`** alone | Single adversarial stance, in isolation | A focused artifact needs one sharp challenge before commit; or as Phase 1 primer to Wave Council |
| **Wave Council** | Role-based seats (architecture, security, qa, reality-checker + rotating fifth), mandatory at Prepare and Review | Code, architecture, trust-boundary, or implementation-shaped work; integrates with the wave lifecycle |
| **Archetype Council** | Stance-based seats (orthogonal axes, not specialist roles), optional | Any artifact where orthogonal thinking-stance lenses are what the work rewards — plans, design docs, code review passes, decision narratives, prose drafts, AC formulations, naming decisions. Especially valuable when role-specialist seats would be overkill or in the wrong shape (e.g., a refactor plan benefits from Sun Tzu's positioning lens and Marcus's durability lens more than from another architecture-reviewer pass). |

Archetype Council is **complementary**, not a replacement. For a wave whose primary work is a public-facing README rewrite, the Wave Council still runs at Prepare and Review; the Archetype Council is invoked on the AC table, the prose draft, *and on the surrounding plan or implementation* to round out the lens coverage. The choice of which artifacts to send through Archetype Council is operator-discretion — there is no fixed "this artifact type only" rule.

---

## Protocol

The phase shape mirrors the Wave Council: a primer-then-seats-then-synthesis structure. What differs is the seat composition — stance-based archetypes rather than role-based specialists — and the optionality (no lifecycle gate consumes the verdict in v1).

### Phase 0 — Moderator Declaration

`wave-council` chairs the Archetype Council (same role as for the Wave Council) and declares the seat composition before Phase 1:

- **Default five seats:** Sun Tzu, Yoda, Spock, Marcus Aurelius, Feynman.
- **Swap protocol:** the fifth seat (Feynman) may be swapped for an alternative archetype when the artifact rewards a different stance. Declare the swap up front (e.g., *"Archetype review with Hemingway swapped in for Feynman"*) so the recorded verdict reflects the actual axes exercised.
- **Documented swap-in candidates:**
  - **Hemingway** — prose-craft / cut-every-sentence-that-doesn't-move-the-story. Use for prose-heavy artifacts (README, getting-started guides, conceptual overviews).
  - **Charlie Munger** — invert / "how would this fail?". Use for decision narratives and option-comparison ADRs.

### Phase 1 — Primer Pass (optional)

Phase 1 is **optional** for the Archetype Council. The stance-based seats are themselves adversarial-leaning, so a separate `red-team` primer is not always load-bearing. Use a Phase 1 primer when:

- The artifact has multiple structural alternatives in tension (then a `red-team` `council-adversarial-primer` is the natural primer)
- The wave's prepare-phase already ran a Wave Council with a `red-team` primer that the Archetype Council can cite directly

Otherwise, Phase 1 is skipped; Phase 2 stances pick up the primer's adversarial-load themselves.

### Phase 2 — Seats In Isolation

Each archetype runs in isolation, applying its stance against the artifact, in this exact sequence:

**Step 1 — Declare axis (before reading the artifact).** State the axis you will apply before reading the artifact. Do not read the artifact yet. Format: `Axis: [axis name] — [one sentence describing what this axis looks for]` (e.g. `Axis: logical precision — looks for claims that cannot be tested or falsified`). This commits the lens before the artifact's framing can shape it.

**Step 2 — Apply axis against artifact.** Now read the artifact through the declared lens and produce:

- **Stance applied** — name the axis the seat exercises (must match the Step 1 declaration)
- **Findings** — what the stance surfaces (must-fix / recommended / advisory)
- **Distinct contribution** — what this stance found that the others would not have caught
- **Verdict** — `ready` / `ready pending fixes` / `not ready`

**Step 3 — Null-finding declaration.** If no findings surface under the declared axis, state **"No findings under [axis name]"** with a one-line explanation of what was checked. Silence is not a valid seat output.

### Phase 3 — Synthesis

`wave-council` synthesizes across the seats. Synthesis must include:

- Seat roster with declared swap (if any) and stance each seat owned
- **Axes-covered** — which orthogonal axes were actually exercised; flag any axis-overlap between seats (if two seats clustered on the same axis, the protocol operated on fewer effective axes than seats)
- Aggregated must-fix list (deduplicated, with finding IDs preserved by seat)
- Aggregated advisory / recommended list
- **Strongest axis** — which seat's findings bound the most must-fixes
- **Strongest challenge surviving review** — the challenge that did not collapse into a fixable finding
- **Strongest alternative not taken** — the path the artifact did not take, worked out enough to be actionable
- Verdict: **PASS** (no must-fixes), **PASS WITH IN-SESSION FIXES** (must-fixes applied during the review), **NOT READY** (must-fixes routed to a follow-on or back-to-author pass)

**Recommendations verdict with red-team closing reconciliation.** Produce a single `### Recommendations Verdict` table that combines the initial verdict for each finding with the red-team's adversarial challenge and final status — all in one list. Do not produce two separate sections. The red-team challenges each row in place: (1) is `fix now` correctly scoped; (2) is `defer` genuine or a punt; (3) is `accept` appropriate or lazy; (4) are there new findings the seats missed. New findings from the red-team are added as rows. The final table is the single authoritative output. Note: in sequential execution the moderator has full context of all findings — the table's value is visibility and accountability, not structural enforcement of honest verdicts.

| Finding | Verdict | Rationale | Red-team |
|---|---|---|---|
| [finding ID or short name] | fix now / defer / accept | [one line] | [challenge + held / updated / new] |

**Falsification check.** As the penultimate step before finalizing the verdict: state the working verdict in one sentence, name the strongest argument against it sourced from any seat output or the red-team closing pass, and state why that argument does not change the conclusion. If the argument does change the conclusion, revise the verdict before finalizing. Record this under a `### Falsification Check` heading in the synthesis output.

---

## The Five Canonical Seats

Each seat owns one orthogonal axis. The personas are mnemonic shells over the axes — if a future operator picks different mnemonics, the axes carry the protocol.

### Sun Tzu — strategic positioning / unforced losses / pre-positioning

> *"Victorious warriors win first, then go to war. Defeated warriors go to war, then seek to win."*

**Stance:** Every step a reader has to discover on their own is an unforced loss. What ground is undefended? What loss is preventable here?

**Best at:** Coverage gaps, missing prerequisites, undefended flanks (e.g., a prerequisite that should be stated before the first commitment-requiring step).

**Example questions:**
- What position is undefended in this artifact?
- What can a reader assume from this that we don't intend?
- Which step is preventable by stating the requirement earlier?

### Yoda — cognitive readiness / commitment threshold / reader orientation

> *"Do or do not. There is no try."*

**Stance:** Many readers will read the artifact, but commitment is the bar. What does the reader bring to this? What state must they be in to commit? Where do they stand on the path?

**Best at:** Reader-state mismatches, commitment-threshold gaps, abandoned-branch handling (what happens when a reader hits a prerequisite-fail branch and has nowhere to return to).

**Example questions:**
- Which reader state does this address — evaluating, or trying?
- What does the reader need before this step makes sense?
- When the reader cannot proceed, do they know how to come back?

### Spock — logical precision / testable propositions / falsification conditions

> *"That is illogical."*

**Stance:** A proposition that cannot be falsified does not bind. Every AC, every claim, every prerequisite must specify what evidence would falsify it. Where is the proposition under-defined?

**Best at:** Imprecise ACs ("expected output snippets" — what kind?), unbound imperatives ("stop here if older" — stop how?), implicit scope boundaries (one host shown inline + link for others — where does the document hand-off and where does the reader resume?).

**Example questions:**
- What evidence would falsify this proposition?
- What is the named signal that confirms each step worked?
- Where is scope implicit when it should be declared?

### Marcus Aurelius — durability / dichotomy of control / time-axis / scope-of-self

> *"What stands in the way becomes the way."*

**Stance:** Will this still be right in 18 months? What is within our control, and what are we pretending to control? Is this the duty of the role, or wishful work?

**Best at:** ACs that bind to ephemeral specifics (a vendor UI label, a current release-page layout) when they could bind to durable invariants; scope-creep into trying to control externals (reader reception, market timing); moralized framing overlaying neutral facts.

**Example questions:**
- Will this AC still be right in 18 months?
- What is within our control here, and what are we pretending to control?
- Is this the duty of the role, or wishful work?
- Strip the moralized labels — what is the neutral fact?

### Feynman — essentiality / simplicity from understanding / curse-of-knowledge

> *"If you can't explain it simply, you don't understand it."*

**Stance:** What is the simplest version that still does the job? What are we doing that isn't earning its place? Can a reader without our context reconstruct the *why*?

**Best at:** Over-engineered ACs (binding text doing the work of one sentence), curse-of-knowledge framing (jargon that assumes the reader is already on the path), clauses that don't earn their place.

**Example questions:**
- What is the simplest version of this that still does the job?
- Can a reader without our context reconstruct the why?
- Which clauses are we including only because we already said them?

### Swap-In Candidates (documented; operator may invoke others)

- **Hemingway** — *prose craft.* "Cut every sentence that doesn't move the story." Best for prose-heavy artifacts (README, getting-started guides). Replaces Feynman or Yoda on rewrites where prose discipline is more load-bearing than essentiality or commitment-state.
- **Charlie Munger** — *invert, always invert.* "What would guarantee this fails? Avoid those things." Best for decision narratives, ADR comparisons, and "is this the right shape?" questions where conceptual failure modes are more load-bearing than positional unforced losses. Replaces Sun Tzu or Feynman on decision artifacts.

Operators may invoke other archetypes ad hoc (Da Vinci, Hemingway, Munger, Rickover, etc.). The seed names two canonical swap-ins to surface the pattern; the canonical-set expansion happens in a future change if a third common swap-in emerges from real usage.

---

## Verdict Format

Record the verdict in the reviewed artifact's review section (`## Review Evidence` for change docs, `## Review Checkpoints` for wave docs). The verdict line is structurally consistent with the existing `prepare-council` verdict shape so future validator integration is straightforward — but no validator consumes the line in v1.

```
- **Archetype Council [archetype-review] — <date>: PASS** (moderator: wave-council; seats: sun-tzu, yoda, spock, marcus-aurelius, feynman; rotating-seat: feynman; strongest-axis: <which seat's findings bound the most must-fixes>; must-fix-count: <n>; advisory-count: <n>)
```

When the fifth seat is swapped, name the swap-in:

```
- **Archetype Council [archetype-review] — <date>: PASS** (moderator: wave-council; seats: sun-tzu, yoda, spock, marcus-aurelius, hemingway; rotating-seat: hemingway; strongest-axis: spock; must-fix-count: 3; advisory-count: 2)
```

Verdict values: **PASS**, **PASS WITH IN-SESSION FIXES**, **NOT READY**.

---

## Worked Example — `1p318` AC-20 / AC-21 Precision Pass

The Archetype Council was first run during wave `1p31b` against `1p318-enh public-launch-surface-doc-rewrite`'s AC-20 (install walkthrough) and AC-21 (Python prerequisite). The seats were Sun Tzu, Yoda, Spock; Marcus Aurelius and Feynman were added in a subsequent expansion that the operator approved before the protocol was formalized.

The three-stance pass produced findings the prior role-based reviews had not surfaced:

- **Sun Tzu (ST-1, ST-2):** Add agent-host MCP-support precheck to the prerequisite block alongside Python/OS; specify "latest stable release zip" with disqualifying patterns (pre-release tags, branch-zip downloads) named explicitly.
- **Yoda (Y-1, Y-2):** 30-second walkthrough preview line above the install block to convert evaluator-state into informed go/no-go; "Return to step (b) when ready" line on prerequisite-fail branches to close the abandoned-reader loop.
- **Spock (SP-1, SP-2, SP-3, SP-4):** AC-20 must name the operator-visible signal at each step (not "expected output snippets" — name them: `Python 3.11.x` from `python3 --version`, agent confirms unpack, index-ready summary, `semantic_ready: true`, `ready: true`); AC-21 imperative must be testable ("Do not proceed past this block until..."); MCP-register step scope must declare the inline-vs-handoff boundary and resume signal.

Synthesis routed five findings as must-fix (MF-1..MF-5) and four as advisory (AD-1..AD-3, plus one already-addressed). The must-fixes landed in-session in the `1p318` change doc Decision Log and AC text. The advisories were noted for the maintainer's discretion during drafting.

The pass is preserved in `1p318`'s Decision Log under "Three-persona review (Sun Tzu, Yoda, Spock) applied to Req-16 / Req-17 / AC-20 / AC-21" and the individual must-fix decision entries.

This worked example is the protocol's audit trail. Future protocol drift is detectable by comparing the seed's seat-stance descriptions against the actual ST-/Y-/SP- findings in `1p318`.

---

## Output Shape

Every Archetype Council seat output must include:

- `archetype`: the seat invoked (e.g., `spock`, `sun-tzu`)
- `stance`: the axis the seat owns (e.g., `logical precision / testable propositions`)
- `findings`: list of findings, each with `id` (e.g., `SP-1`), `severity` (`must-fix` / `recommended` / `advisory`), `text` (the finding), `paired_action` (the concrete fix — must be actionable, not "consider X")
- `distinct_contribution`: what this stance found that the other seats would not have caught
- `verdict`: `ready` / `ready pending fixes` / `not ready`

Every moderator synthesis must include:

- `seats`: roster with declared swap-in noted
- `axes_covered`: which orthogonal axes were actually exercised; overlap flagged
- `must_fix_aggregate`: deduplicated must-fix list with finding IDs preserved
- `advisory_aggregate`: deduplicated advisory list
- `recommendations_verdict_table`: single table combining initial verdict and red-team closing reconciliation for every advisory and recommended finding — `fix now` / `defer` / `accept`, rationale, red-team challenge and final status. Never leave advisories unverdicted or unchallenged.
- `strongest_axis`: which seat's findings bound the most must-fixes
- `strongest_challenge_surviving`: the challenge that did not collapse into a fixable finding
- `strongest_alternative_not_taken`: the path the artifact did not take
- `verdict`: `PASS` / `PASS WITH IN-SESSION FIXES` / `NOT READY`

## Output Verbosity

Present council output at summary level — seat step details stay internal; the operator sees seat summaries, the recommendations verdict table, and the falsification check. Do not narrate every step of every seat.

**Seat summaries:** One short paragraph per seat — axis declared, findings summary, verdict. Steps 1–3 are execution structure, not output structure.

**Recommendations verdict table:** Always shown in full — this is the primary operator-facing output.

**Falsification check:** Condense when the verdict is a clean PASS with no must-fix findings: one line stating the working verdict, the strongest counter-argument in a phrase, and "does not change verdict." Show in full when the verdict is PASS WITH IN-SESSION FIXES or NOT READY, or when must-fix findings are present.

---

## Role Boundaries

**vs. `red-team`:** `red-team` runs a single adversarial stance in isolation (or applies all five adversarial-leaning stances inside one mode). Archetype Council runs multiple stance-based seats in isolation and synthesizes across them — the axes are orthogonal rather than overlapping. Invoke `red-team` when one sharp challenge is the right shape; invoke Archetype Council when multiple orthogonal axes need to fire simultaneously.

**vs. Wave Council:** Wave Council uses role-based specialist seats (architecture, security, qa, reality-checker + rotating fifth) and is mandatory at Prepare and Review when `wave_review.enabled` is true. Archetype Council uses stance-based seats and is optional. Wave Council remains required regardless of whether Archetype Council also runs.

**vs. `senior-engineering-challenger`:** `senior-engineering-challenger` pressure-tests technical claims inside a plan or delivered artifact (are the claims internally consistent, are the ACs reachable, is the delivered result complete?). Archetype Council pressure-tests the artifact's prose, structure, AC formulation, and decision narrative from orthogonal stances. Use `senior-engineering-challenger` for plan/delivery pressure-testing; use Archetype Council for text-precision and stance-coverage passes.

---

## Operating Invariants

These apply in every Archetype Council pass. A pass that violates them is not an Archetype Council pass:

1. **Each seat runs in isolation.** Do not synthesize across seats during Phase 2. The whole value of the orthogonal-axis design is that each seat is unblemished by the others' findings. Synthesis happens in Phase 3 only.
2. **Stances must be orthogonal.** If two seats cluster on the same axis (e.g., two adversarial-leaning seats both producing positional-defense findings), the protocol operated on fewer effective axes than seats. The moderator flags this in `axes_covered`.
3. **Every finding has a paired action.** A finding without an actionable fix is a complaint, not a finding. The Wave Council's invariant 2 applies here too.
4. **Stay grounded.** Findings must be tied to the artifact under review, not generic hypotheticals.
5. **The non-mandate property is load-bearing.** This protocol is optional by design. The recommendation pointers in other seeds are *recommendations*, not gates. Anywhere this seed's invocation is woven into the lifecycle, the "removable without breaking the existing protocol" test must pass.

---

## Do Not

- Do not invoke Archetype Council as a replacement for the Wave Council when `wave_review.enabled` is true
- Do not run seats outside isolation in Phase 2
- Do not produce findings without paired actions
- Do not record an Archetype Council verdict against a `wave-council-readiness` or `wave-council-delivery` lifecycle slot — those signoffs belong to the Wave Council and the lifecycle gates that consume them

---

## Project Harness Extensions

<!-- Fill from target repository evidence during upgrade render. Never add product-specific content to this seed body. -->
