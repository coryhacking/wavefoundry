# CIA Research and Documentation Role

Change ID: `12dhh-enh cia-research-role`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-05
Wave: `12dhh cia-research-role`

## Rationale

The CIA as shipped in wave 12d4b is a read-only retrieval agent. It answers questions but makes no claims about completeness and has no mechanism for validating whether an answer is evidence-grounded vs. pattern-inferred. There is also no path for the CIA to surface ambiguity to the operator, record durable discoveries for future queries, or contribute to the architecture/spec documentation it uses as a source.

Four gaps need closing:

1. **Assumption discipline** — the CIA currently has no rule against stating inferred conclusions as facts. Every answer needs to be either code-validated or explicitly qualified.
2. **Operator interaction** — complex architectural questions often can't be fully answered from the index alone. The CIA should be able to ask the operator (who may be an architect) rather than guessing.
3. **Discovery documentation** — when the CIA finds something worth preserving (an undocumented pattern, an architectural gap, a spec divergence, an edge case), it should write it down. Its journal and the architecture/spec docs are the right surfaces.
4. **External validation** — the codebase index alone cannot validate behavior against framework contracts, language specs, or library documentation. The CIA should use web lookup to cross-reference external sources when internal evidence is ambiguous or incomplete.

## Requirements

1. The CIA must never state a conclusion as fact unless it is validated by at least one indexed chunk citation. Pattern-inferred conclusions must be explicitly flagged.
2. The CIA may ask the operator clarifying questions when the index evidence is insufficient to answer confidently — particularly for architectural scope, intent, or correctness questions.
3. The CIA must maintain a journal (`docs/agents/journals/code-insight-agent.md`) for durable discoveries — undocumented patterns, architectural gaps, spec divergences, and retrieval dead-ends that recur.
4. The CIA is permitted to write to `docs/architecture/`, `docs/specs/`, and its own journal (`docs/agents/journals/code-insight-agent.md`) when it makes discoveries worth preserving. All other write-paths remain prohibited.
5. During discovery, the CIA must actively look for edge cases and non-obvious constraints an implementer would need to know when working in the relevant area of code — not just answer the immediate question.
6. The CIA may use web fetch / web search to consult framework documentation, library references, and language specs when internal evidence is ambiguous or incomplete, or when an edge case needs external validation.
7. `## Purpose` must reflect the research, edge-case detection, and documentation role, not just retrieval.
8. CIA answers must not be artificially truncated or kept brief unless the operator explicitly requests a short answer. Depth and completeness are the default; brevity is opt-in.

## Scope

**In scope:**
- Update `docs/prompts/agents/code-insight-agent.prompt.md` and `seed-211`:
  - Reframe `## Purpose` to include research, edge-case detection, and documentation
  - Add `## Assumption Discipline` section (no unvalidated claims)
  - Add `## Operator Q&A` section (when and how to ask questions)
  - Add `## Edge Case Detection` section (what to look for, when to record)
  - Add `## External Lookup` section (web fetch/search for framework docs, specs, library references)
  - Add `## Discovery Documentation` section (journal + arch/spec write paths)
  - Revise `## Read-Only Constraint` to carve out `docs/architecture/`, `docs/specs/`, and journal writes
- Create `docs/agents/journals/code-insight-agent.md` — CIA journal with operating identity, salience triggers, and initial observation sections
- Update `seed-050` journal bootstrap rule to include the CIA journal in the set of role journals seeded during init

**Out of scope:**
- Changing the retrieval loop mechanics (those are correct as-is)
- Updating the fallback section (no-MCP path remains grep-only, no write carve-out)
- Editing `docs/architecture/` or `docs/specs/` content (the CIA does that at discovery time, not at seed time)

## Affected Architecture Docs

N/A — seed and prompt surface changes only.

## Acceptance Criteria

| AC | Description |
|----|-------------|
| AC-1 | `code-insight-agent.prompt.md` `## Purpose` describes research and documentation as part of the CIA role |
| AC-2 | `code-insight-agent.prompt.md` includes an `## Assumption Discipline` section requiring code validation or explicit qualification for every claim |
| AC-3 | `code-insight-agent.prompt.md` includes an `## Operator Q&A` section permitting clarifying questions to the operator when index evidence is insufficient |
| AC-4 | `code-insight-agent.prompt.md` includes a `## Discovery Documentation` section covering the journal and the `docs/architecture/`, `docs/specs/`, and journal write carve-out |
| AC-5 | `code-insight-agent.prompt.md` includes an `## Edge Case Detection` section describing what to look for and when to record findings |
| AC-6 | `code-insight-agent.prompt.md` includes an `## External Lookup` section covering web fetch/search for framework docs, language specs, and library references |
| AC-7 | `## Read-Only Constraint` is updated to reflect the write carve-out for architecture and spec docs |
| AC-7b | `code-insight-agent.prompt.md` includes a rule that answers are complete by default and brevity is only applied when the operator requests it |
| AC-8 | `seed-211` matches the updated `code-insight-agent.prompt.md` |
| AC-9 | `docs/agents/journals/code-insight-agent.md` exists with operating identity, salience triggers, and initial observation sections |
| AC-10 | `seed-050` journal bootstrap rule includes the CIA journal |
| AC-11 | All pre-existing framework tests pass |

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Purpose statement is the entry point; must reflect the full role |
| AC-2 | required | Core behavioral rule — prevents the CIA from presenting guesses as facts |
| AC-3 | required | Operator Q&A is an explicit user requirement |
| AC-4 | required | Discovery documentation is an explicit user requirement |
| AC-5 | required | Edge case detection is an explicit user requirement |
| AC-6 | required | External lookup is an explicit user requirement |
| AC-7 | required | Read-only constraint must be accurate or agents will over-restrict |
| AC-7b | required | Truncation default is wrong for a research agent; completeness is the correct default |
| AC-8 | required | Seed must match source |
| AC-9 | required | Journal must exist for the CIA to use it |
| AC-10 | required | Install flow must create the journal in target repos |
| AC-11 | required | Non-regression |

## Tasks

1. Open `seed_edit_allowed` gate
2. Update `docs/prompts/agents/code-insight-agent.prompt.md` — Purpose, Assumption Discipline, Operator Q&A, Edge Case Detection, External Lookup, Discovery Documentation, Read-Only Constraint
3. Update `seeds/211-code-insight-agent.prompt.md` to match
4. Create `docs/agents/journals/code-insight-agent.md`
5. Update `seed-050` journal bootstrap to include CIA journal
6. Close `seed_edit_allowed` gate
7. Run framework tests

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-05 | Write carve-out scoped to `docs/architecture/` and `docs/specs/` only | CIA is a research agent, not an implementer; code writes are out of scope | Could allow any `docs/` write — too broad; could restrict to a CIA-specific subfolder — unnecessary overhead |
| 2026-05-05 | CIA gets its own journal, not a shared research log | Journals are role-specific in the wave framework; the CIA has a distinct operating identity and discovery surface | Could use a shared `docs/references/research-log.md` — doesn't fit the journal system |
| 2026-05-05 | Operator Q&A is permitted but not required | CIA should make a best-effort answer before asking; questions are a fallback for genuine ambiguity, not a shortcut | Could make questions mandatory for low-confidence answers — too disruptive for simple queries |
| 2026-05-05 | External lookup scoped to framework/library/spec docs, not general web search | CIA is a research agent for a specific codebase; general web search risks hallucination laundering; scoped lookup keeps citations traceable | Could block all web access — loses the ability to validate edge cases against authoritative sources |
| 2026-05-05 | Edge case detection is active, not passive | CIA should proactively surface gotchas relevant to the area being researched, not just answer the narrow question asked | Could make it opt-in per query — but the user's intent is that this is always part of discovery |
