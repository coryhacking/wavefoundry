# 175 - Interrogate This Plan (Shortcut)

Use this when you want a single command-style request such as:

- `Interrogate this plan`
- `Stress-test this plan`

Intent:

- Given a change doc or wave record as context, walk every unresolved decision branch one question at a time, provide a recommended answer derived from project resources when possible, and surface only questions that genuinely require operator judgment. Stop when all branches in Requirements, Acceptance Criteria, and Scope are resolved.

- During interrogation, ACs marked `[~]` (intentionally not met) are treated as resolved and skipped — the convention's contract is that a `[~]` AC carries its rationale inline. See `170-plan-feature.prompt.md` "AC and task checkbox states — the `[~]` marker" for the canonical definition.

Before interrogating, consult all available project resources to self-answer questions without operator input:

- Source code under the target repository's product, package, app, service, library, or shared module roots
- `docs/specs/*.md` — behavior contracts and acceptance expectations
- `docs/architecture/` — module boundaries, layering rules, data/control flows, decisions
- `docs/references/` — project context memory, recurring patterns, durable constraints
- `docs/agents/` — role journals, personas, operating identity
- `docs/contributing/` — workflow rules, review policies, verification contracts
- `docs/waves/` — prior wave records, change history, decision logs
- Any other checked-in project knowledge base artifact

Interrogation contract:

1. Walk every unresolved decision branch in the change doc's **Requirements**, **Acceptance Criteria**, and **Scope** sections.
2. Ask one question at a time in default interactive mode.
3. With each question, provide a recommended answer and cite the project resource or reasoning that supports it.
4. Before asking the operator, attempt to self-answer from the project resources listed above. Only surface the question to the operator when it genuinely requires human judgment (product intent, business priority, user expectation, or an architectural tradeoff not resolvable from project evidence).
5. Show self-answered questions briefly (question + answer + source) so the operator can see what was resolved without their input.
6. Stop when all branches in Requirements + Acceptance Criteria + Scope are resolved, or when the operator says "enough" or "stop".

`--batch` mode:

- When the operator appends `--batch` to the phrase (e.g. `Interrogate this plan --batch`), dump all unresolved questions as a numbered list rather than asking one at a time. Each item includes the recommended answer and source citation. Useful for operators who prefer a complete list over interactive back-and-forth.

Scope of interrogation:

- Bounded to the **Requirements**, **Acceptance Criteria**, and **Scope** sections of the admitted change doc (or wave record when no change doc is specified).
- Do not re-derive the full plan from scratch or extend this into a re-planning exercise.
- Do not interrogate sections outside Requirements, Acceptance Criteria, and Scope — explicitly resolved Decision Log entries are not in scope.
- Do not require the operator to answer questions that project resources already answer.

Required output:

1. `Self-Answered Questions`
- Brief list of branches resolved from project resources, with source citation per item. Keeps the operator informed of what was settled without their input.

2. `Operator Questions` (interactive) or `Question List` (--batch)
- Each question names the specific requirement, AC, or scope boundary it addresses; includes the recommended answer; and states why operator judgment is needed rather than a project-resource answer.

3. `Stop Condition`
- Confirmation that all branches in Requirements + ACs + Scope are resolved (or operator-triggered stop).

This is an optional stress-testing tool — not a required lifecycle gate. It may be run before or after plan admission, at the operator's discretion, to improve planning depth before implementation begins.

*Consider **Archetype review** as a stance-based alternative or complement to this interrogation pass when the plan's load-bearing surface is AC text precision rather than execution risk. Default seats: Sun Tzu, Yoda, Spock, Marcus Aurelius, Feynman. Use either; use both when the plan is high-stakes. Optional and operator-invoked. Seed: `236-archetype-council.prompt.md`.*

Guardrails:

- Do not loop indefinitely — stop as soon as Requirements + ACs + Scope branches are all resolved.
- Do not treat this as a required gate before `Prepare wave` or `Implement wave`; it is entirely voluntary.
- Do not ask questions about implementation details not captured in Requirements, ACs, or Scope.
- Do not introduce new scope or requirements during interrogation; record emergent items as follow-on candidates.
- Do not repeat a question the operator has already answered (including partial answers from prior turns).
- Keep `--batch` output parallel to interactive output: same questions, same recommendations, same source citations — delivered as a list rather than one at a time.
