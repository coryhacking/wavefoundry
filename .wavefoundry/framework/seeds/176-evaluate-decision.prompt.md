# 176 - Evaluate Decision (Shortcut)

Use this when you want a single command-style request such as:

- `Evaluate decision`
- `Evaluate option`
- `Compare options`
- `Architecture evaluation`

Intent:

- Run a structured multi-seat evaluation of an architectural decision, technology comparison, or build-vs-buy question. Combine a red-team adversarial pass with a Wave Council review, follow up with an operator interview, and produce an Architecture Decision Record (ADR) capturing the settled conclusion, its bounds, and conditions under which it should be revisited.

---

## Evaluation Contract

### Phase 1 — Frame the Question

Before running any evaluation:

1. Identify what is being evaluated — two specific options, not abstract categories.
2. Characterize what already exists — the current implementation, its capabilities, and its known limits.
3. Establish what triggered the re-evaluation — new information, a capability gap, a prior deferred decision.
4. Define what the evaluation does NOT cover — scope boundaries prevent drift.

If the operator has not provided sufficient context, ask before proceeding. A poorly framed question produces a confident but useless evaluation.

### Phase 1b — Guru: Current-State Grounding

Before the red-team argues, use available code and documentation search tools to characterize what is actually built. Do not rely on memory or general knowledge for this step.

Ask: *"How is [the thing being evaluated] currently implemented, and what are the relevant entry points or integration points?"*

Use the results to correct any framing assumptions before the evaluation starts. A red-team arguing from an accurate description of the current implementation produces better findings than one arguing from a summary.

### Phase 2 — Red-Team Evaluation

Run the `red-team` seat. The red-team is adversarial toward both options — not an advocate for either.

Structure the evaluation as:

1. **Where Option A wins** — genuine advantages, stated without hedging. Argue from the strongest version of this option.
2. **Where Option B wins** — genuine advantages, stated without hedging. Argue from the strongest version of this option.
3. **Net assessment** — which option is better under what conditions, and what the decision actually hinges on.

The red-team must:
- Name specific failure modes, not generic "complexity" or "risk"
- State what would have to be true for the currently-losing option to win
- Not declare a winner without stating the conditions under which that verdict holds

### Phase 3 — Wave Council Review

Run all three council seats in sequence. Each seat reads the red-team evaluation and responds to it.

**Reality-checker** — challenges the red-team's framing:
- Is the evaluation stress-testing the losing option only at its worst case?
- Are there problems being treated as fatal constraints that are actually solvable?
- Does the capability gap or complexity concern actually matter for this project's real use case?
- What is the red-team underweighting or glossing over?

**Red-team (second pass)** — challenges its own first-pass evaluation:
- What assumptions in the first pass could be wrong?
- Does the winning option have weaknesses the first pass understated?
- What would a critic of the recommendation say, and is that criticism fair?

**Council-moderator** — synthesizes across all seats:
- Where do the seats agree? That is the settled ground.
- What nuances did the council surface that the red-team evaluation alone would not have captured?
- What should the ADR record that the red-team output alone would miss?
- What are the explicit bounds of this decision — when does it hold, when should it be revisited?

### Phase 4 — Operator Interview

After the council synthesis, invite the operator to ask follow-up questions. This is the most important phase. The operator holds context the agents do not: prior discussions, organisational constraints, scope intentions, and domain knowledge that can change the framing entirely.

The operator should ask until the framing feels settled. Productive question types:

- **Scope clarification** — "Are you sure you're not proposing X?" Confirms what the recommendation is and is not.
- **Missing dimension** — "What about Y?" Introduces a factor the evaluation missed.
- **Availability check** — "Does Z actually exist today?" Probes whether the agents assumed something that requires build work.
- **Historical context** — "We looked at this before and the issue was…" Surfaces prior decisions that reframe the evaluation.
- **Scope boundary** — "Does this apply to all of it or just [specific part]?" Ensures the decision is scoped correctly.

Respond to each operator question by updating the analysis, not by treating it as Q&A. If the operator's question changes the recommendation, say so directly.

### Phase 4b — Guru: Implementation Feasibility Check

After the operator interview and before writing the ADR, use code search tools to ground the council's recommendation in the current code or system structure.

Ask: *"Given [the recommended approach], where would this land in the existing code, and is the change additive or does it require restructuring?"*

This either confirms the future path is low-friction, or surfaces hidden coupling that changes the revisit calculus. If the future path is more invasive than the council assumed — touching more files, requiring refactoring, or breaking existing patterns — record that in the ADR's consequences section.

### Phase 5 — ADR

Write the ADR after the operator interview and feasibility check, not before. The interview frequently changes the framing materially.

A complete ADR from this process includes:

- **Context** that distinguishes what the decision covers from what it explicitly does not cover
- **Decision** stated as a single declarative sentence
- **Consequences** — positive, negative, and constraints imposed
- **Alternatives Considered** — including options that are "not yet, but the right path when conditions X are met"; do not mark these as rejected
- **Revisit Conditions** — named explicitly; a decision without revisit conditions is one that will be ignored when circumstances change
- **What will not be built** — if a future path should leverage existing ecosystem rather than new implementation, state this explicitly so future implementers do not build what already exists

---

## Guardrails

- Do not write the ADR before the operator interview. The interview regularly introduces dimensions that change the alternatives section and revisit guidance.
- Do not treat the red-team evaluation as the final word. The council's job is to challenge it, and the council reliably surfaces nuances the red-team missed.
- Do not omit the feasibility check. An ADR that recommends a "simple future enhancement" without verifying current code structure may be recommending a rewrite without knowing it.
- Do not declare "it depends" in the ADR without naming exactly what it depends on.
- Do not scope the decision broader than the operator interview confirms. If the interview narrows the scope, the ADR should reflect the narrower scope.
- Keep project-specific details out of the evaluation framing — evaluate the options on their own merits before applying project constraints.
