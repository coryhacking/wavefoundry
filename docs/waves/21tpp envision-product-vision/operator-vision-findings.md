# Operator vision findings — evaluation source

Owner: Engineering
Status: active
Last verified: 2026-10-28

These are verbatim excerpts from the operator-provided review, retained as the independent rubric's source. Historical recommendations below are not new implementation authority. The operator subsequently clarified that overall product vision, greatest financial and nonfinancial value, staged realization, endurance and adaptability are the purpose, and removed the word ceiling and fixed trial budget.

## Original ten findings

1. The goal of the document was dropped. Your original skill said: "Make the document useful both as a long-term direction and as a guide for selecting the next bounded investment." That sentence is gone. The new prompt says what to include but never what the finished document has to let a reader do. Every review then has nothing to judge success against except completeness.
- Suggest adding a short test near the top: "A finished vision lets its reader: (a) say why this destination matters and to whom; (b) name the next investment and why it comes first; (c) say what evidence would show a horizon has failed or the vision is wrong." Give the reviewers that same test.

2. The reviews tend to shrink the ambition, and nothing protects it. The red-team review looks for "simpler or stronger alternatives". The Archetype Council favours simplicity. The repair step says to "correct … unsupported claims". Together they will reliably pull a bold vision down to a safe one. Only the architecture row says "preserve the requested ambition".
- Suggest adding to step 5: "A finding that the destination is too ambitious, or should be narrower, is a strategic choice for the operator. Record it as an open decision; don't resolve it by shrinking the vision. Repair factual errors, broken sequencing and claims about the starting point, not the size of the ambition."

3. Nothing checks the draft against what you actually asked for. The reviews judge whether the draft is any good, not whether it is the vision you meant. Elsewhere in Wavefoundry a plan is read back before work starts, and the final report is judged on whether it does what was intended. Envision has neither, so a misread brief can go through the full set of reviews unnoticed.
- Suggest two things:
  - In step 1, state the brief back in a few sentences before drafting when key parts of it were inferred.
  - In the final report, say how the vision meets each part of the brief, and what the operator should check first.

4. Putting the review record inside the vision conflicts with the vision lasting. Your original said to keep the vision focused on enduring purpose, "not a duplicate task backlog or session log". The new default puts the reviews, verdicts and dispositions inside VISION.md, where they will go stale and dominate the document. Your own VISION.md and relay.md are better without such a section.
- Suggest making the default a sibling file next to the vision, such as VISION-review.md, or the response itself. The vision would keep only a one-line status naming the review date and linking to its open decisions.

5. "Substantially revised" decides whether about seven reviewer agents run, but it isn't defined. The full set is architecture, red-team, a council chair and five Archetype Council seats. The test for running it is unclear. The cost is also never stated to the operator.
- Suggest a test: changes to purpose, beneficiary, the set of horizons or their order are substantial; anything else is minor. And: "Before starting the full review set, state its scope and let the operator narrow it."

6. Guidance for revising an existing vision was weakened. Two lines from the original are missing:
- "explain substantive directional changes, and reconcile contradictions"
- "Do not overwrite unrelated operator edits"

The new prompt only says to preserve valid content, so a revision can quietly rewrite the direction.
- Suggest restoring both, plus: "List what changed in direction and why in the response."

7. Other guidance lost in the generic version. Each is small, but together they are much of what made the original guide good:
- "Avoid a generic feature wishlist". Only partly kept, as "how each foundation enables what follows".
- "Do not equate more workers with proportional progress". This matters for exactly the unlimited-resources briefs the prompt mentions.
- Repeated attempts and held-out evaluations in the evaluation section.
- "State what the system cannot yet justify, simulate, measure, or guarantee".
- Showing human decision points and feedback paths in the architecture section.
- Stating the assumptions behind timing.

8. Nothing says when to revisit the vision. Neither version does. A vision that claims to be enduring should name its own review triggers, such as a horizon reaching or missing its exit criteria, a hard question being answered, or the brief changing. Otherwise it quietly becomes wrong.

9. A detail from your situation leaked into the shipped text. "Do not import a personal skill's founding narrative" only makes sense to you; for other users it's noise. Suggested wording: "Use only the target project's brief and sources; do not reuse another project's vision."

10. Each horizon must cover nine elements, which risks form-filling. The page structure is flexible, but the per-horizon list isn't. With four horizons the reviewers check that 36 boxes are filled rather than whether the argument holds.
- Suggest: "Cover these where they bear on the argument. Every horizon needs a demonstration, exit criteria, a failure condition and intermediate value."

## Original six strategy practices

1. A strategic interview as the brief step. Replace "establish the brief" with about eight high-leverage questions, asked only where the context doesn't already answer them:
   - Who is struggling, and with what?
   - What do they use today?
   - What have you seen that others miss?
   - Why now?
   - What will you not do?
   - Who pays, and why?
   - What would make this a failure even if it ships?
   - How ambitious should this be?

   This is the discovery phase, compressed.
2. A diagnosis section before the destination. It names the problem, why it's hard, the insight and why now. Everything else should follow from it. Reviewers can then test whether the destination actually answers the diagnosis.
3. Labelled evidence of need. Mark each claim about users as evidenced (with its source) or hypothesised. Name the cheapest research that would test the riskiest one, such as five customer interviews, a fake-door test or a concierge pilot. This parallels how the prompt already separates verified capabilities from proposals.
4. The four-risk lens on the destination and each horizon. Value, usability, feasibility and viability. Each horizon says which risk it retires first. This replaces vague "research bets" with a recognised discipline and covers viability explicitly.
5. Positioning against the real alternatives, plus non-goals. List the status quo, do-it-yourself and competing products. Say where to play and how to win, what the advantage is, and why it lasts. List explicit non-goals. A scan of competing products needs network access, which conflicts with the no-network default. So it should be operator-approved, or the operator supplies the landscape, as with the Relay market check.
6. Optional working-backwards check, plus a north-star metric. The author drafts a short future press release and the three hardest customer FAQ questions as a test of how compelling the vision is. It doesn't have to go in the document. Pair it with one outcome metric and its guardrail metrics.
