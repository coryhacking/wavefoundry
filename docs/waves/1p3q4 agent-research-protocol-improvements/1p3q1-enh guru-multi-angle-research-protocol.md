# Guru multi-angle research protocol

Change ID: `1p3q1-enh guru-multi-angle-research-protocol`
Change Status: `implemented`
Owner: framework-maintainer
Status: planned
Last verified: 2026-06-06
Wave: 1p3q4 agent-research-protocol-improvements

## Rationale

Guru's current retrieval protocol is single-hypothesis: classify the question, run tool passes, form a hypothesis, gather confirming evidence, return. Three failure modes appear in practice:

- **Tunnel vision** — Guru investigates one code path and misses an equally plausible alternative (e.g. answers "configured in `workflow-config.json`" without checking env vars, CLI flags, or hardcoded defaults in the same call path).
- **Confirmation bias** — Guru forms a hypothesis after the first retrieval pass and collects evidence that confirms it, without attempting to falsify it. The answer can be confidently wrong.
- **Silent coverage gaps** — Guru returns "I didn't find it" when a different search angle — different query phrasing, different entry symbol, different tool — would have found it. The miss is invisible to the operator.

These are seed/protocol failures, not tool failures. The wavefoundry MCP tools (`code_ask`, `code_search`, `code_definition`, `code_graph_path`, etc.) can already cover multiple angles; the seed just doesn't instruct Guru to use them that way.

This change adds a **multi-angle research discipline** to `seed-211` as a protocol layer inserted before the existing retrieval passes: decompose the question into independent angles, investigate each before converging, explicitly attempt falsification of the primary hypothesis, and surface disagreement explicitly rather than silently resolving it.

This is independent of — and a prerequisite for — any future dynamic-workflows implementation of Guru (`1p3ao` T1.3). The sequential multi-angle protocol lands value now; the parallel execution of those angles is a workflow-era addition.

## Requirements

1. `seed-211` gains a **Question Decomposition** step that runs before the existing retrieval pass. For explanatory and navigational questions, Guru must enumerate 2–3 independent angles the answer could come from (e.g. config file, env var, code default, CLI flag, runtime override) before issuing the first tool call.
2. The decomposition step is **question-type gated**: required for `explanatory` and `navigational` questions; skipped for `instructional` questions (docs-first path is already well-scoped and parallel angles add noise, not signal).
3. After the initial retrieval pass, Guru must run an explicit **Hypothesis Check**: state the working hypothesis, identify one retrieval action that would falsify it, run that action, and incorporate the result. If the falsification attempt produces contradicting evidence, surface the contradiction rather than discarding it.
4. When two or more angles produce **contradicting findings** (e.g. angle 1 says "configured in X", angle 2 says "defaults to Y in code"), Guru must surface the contradiction explicitly in the answer — both findings, the conditions under which each applies, and the confidence level of each — rather than resolving it silently.
5. When an angle produces **null results** (nothing found via that angle), that null must be stated in the answer as explicit negative evidence ("found no env-var path for this setting") rather than omitted.
6. The Question Decomposition step must emit a visible **"Investigating from N angles"** note before retrieval begins, so operators understand why multiple tool passes are occurring.
7. Existing retrieval-pass structure (Pass 1 orientation, Pass 2 targeted retrieval, Pass 3 structural confirmation) is **preserved and not replaced** — the angle decomposition and hypothesis check are a framing layer around those passes, not a replacement of the pass structure.
8. The `## Quick-question shortcut` path (single-word lookups, "where is X defined") is **exempt** from decomposition — routing to `code_definition` or `code_callhierarchy` directly is still correct for pure navigational single-symbol questions where the angle is unambiguous.

## Scope

**Problem statement:** Guru's single-hypothesis retrieval protocol produces tunnel vision, confirmation bias, and silent coverage gaps on multi-source questions — the most common and highest-stakes questions operators ask.

**In scope:**

- `seed-211` (`211-guru.prompt.md`): add Question Decomposition step, Hypothesis Check step, and contradiction/null-result surfacing rules.
- `docs/agents/guru.md`: regenerate from updated seed (standard post-seed-edit artifact refresh).
- CHANGELOG bullet under `[Unreleased]` → `### Changed`.

**Out of scope:**

- Parallel angle execution — requires dynamic workflows (`1p3ao` T1.3). The angles in this change are investigated sequentially.
- Modifying tool routing guidance, pass structure, question classification table, or any other seed section beyond the decomposition and hypothesis-check additions.
- Changes to `code_ask`, `code_search`, or any MCP tool implementation — this is a seed-level protocol change only.
- Adding decomposition discipline to other agents (code-reviewer, red-team, reality-checker). Each has its own review protocol; guru's Q&A pattern is distinct.

## Acceptance Criteria

- [x] AC-1: `seed-211` contains a `### Question Decomposition` step that appears before the existing retrieval pass guidance and is gated on `explanatory` / `navigational` question types.
- [x] AC-2: The decomposition step instructs Guru to enumerate 2–3 independent angles with concrete examples of what "an angle" means (config file, env var, code default, CLI flag, runtime override, etc.).
- [x] AC-3: `seed-211` contains a `### Hypothesis Check` step that runs after the initial retrieval pass: state working hypothesis → identify one falsifying action → run it → incorporate result.
- [x] AC-4: `seed-211` instructs Guru to surface contradicting angle findings explicitly — both findings, conditions, confidence — rather than silently resolving.
- [x] AC-5: `seed-211` instructs Guru to state null results as explicit negative evidence, not omit them.
- [x] AC-6: `seed-211` instructs Guru to emit an "Investigating from N angles" note before beginning multi-angle retrieval.
- [x] AC-7: The `## Quick-question shortcut` path is explicitly exempted from decomposition in the seed text.
- [x] AC-8: `instructional` questions are explicitly exempted from decomposition in the seed text.
- [x] AC-9: Existing pass structure, tool routing table, question classification table, and all other seed sections remain unchanged (verified by diff review).
- [x] AC-10: `docs/agents/guru.md` regenerated and matches updated seed.
- [x] AC-11: `docs-lint` returns clean.

## Tasks

- [x] Edit `seed-211`: insert `### Question Decomposition` section after question classification table, before Pass 1 guidance.
- [x] Edit `seed-211`: insert `### Hypothesis Check` section after Pass 2 guidance, before Pass 3.
- [x] Edit `seed-211`: add contradiction-surfacing and null-result rules to the answer synthesis guidance.
- [x] Add "Investigating from N angles" emit instruction adjacent to the decomposition step.
- [x] Verify exemptions (quick-question shortcut, instructional type) are stated explicitly.
- [x] Diff review: confirm no existing sections modified beyond the insertion points.
- [x] Regenerate `docs/agents/guru.md`.
- [x] Run `docs-lint`.
- [x] Add CHANGELOG bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| seed-211 edit | framework-maintainer | — | Three insertion points; no other files touched in this step. |
| guru.md regeneration | framework-maintainer | seed-211 edit | Standard artifact refresh after seed change. |
| Verification | framework-maintainer | guru.md regeneration | diff review + docs-lint. |

## Serialization Points

- `seed-211` is a single file touched by one agent. No parallelism concerns.

## Affected Architecture Docs

N/A — change is confined to the Guru seed and its rendered agent doc. No boundary, flow, layering, or cross-cutting impact. The protocol change does not alter the MCP tool surface, the retrieval index, or any inter-agent contract.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The decomposition step IS the change. |
| AC-2 | required | Concrete examples prevent the "enumerate vague angles" failure — Guru must know what counts as an independent angle. |
| AC-3 | required | Hypothesis check addresses confirmation bias directly. |
| AC-4 | required | Contradiction surfacing is the operator-facing value of multi-angle research. Silent resolution defeats the purpose. |
| AC-5 | important | Null results as evidence prevents the "I didn't find it" gap from being invisible. |
| AC-6 | important | Visibility note lets operators understand why multiple passes are running and reduces perceived latency anxiety. |
| AC-7 | required | Quick-question exemption prevents decomposition overhead on single-symbol lookups where it adds noise. |
| AC-8 | required | Instructional exemption: docs-first path is already scoped; angle decomposition adds noise not signal. |
| AC-9 | required | Existing sections are validated protocol — do not drift them. |
| AC-10 | required | Rendered doc must stay in sync with seed. |
| AC-11 | required | docs-lint clean is a pre-merge gate. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-06-06 | Change doc created following council review of `1p3ao` and operator Q&A. | `wave_new_enhancement` → `1p3q1`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-06-06 | Sequential multi-angle protocol (not parallel) | Parallel execution requires dynamic workflows (`1p3ao` T1.3), which is research-preview and unvalidated. Sequential angles deliver the main quality wins (tunnel vision, confirmation bias, gap visibility) without any new infrastructure. | (a) Wait for workflows — defers real value; the protocol improvement is independent. (b) Full workflow implementation now — premature; `1p3ao` explicitly sequences this as a workflow-era addition. |
| 2026-06-06 | Exempt `instructional` question type from decomposition | Instructional questions ("how do I…") have a well-scoped docs-first retrieval path. Angle decomposition on instructional questions (e.g. "angle: config approach, angle: API approach, angle: SDK approach") adds retrieval breadth but produces an answer that is harder to act on, not easier. The operator asking "how do I do X" wants a path, not a survey. | (a) Apply decomposition to all question types — produces answer-quality regression for instructional. (b) Make decomposition opt-in via a "deep" mode — adds operator friction; decomposition on explanatory is almost always the right call and shouldn't require an explicit flag. |
| 2026-06-06 | Framing layer around existing passes, not a pass replacement | The existing 3-pass structure is well-validated and maps cleanly to tool capabilities. Replacing it would widen scope and risk regressions on the passes that already work. Adding decomposition and hypothesis-check as a framing layer is additive and surgically scoped. | (a) Redesign the full retrieval protocol — over-scope for this change; existing passes are not the problem. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Multi-angle retrieval increases token cost per Guru call | Decomposition adds 1–2 extra tool calls per question. For most questions this is 1-2 targeted keyword searches or a second `code_search` with a different query — low cost. The exemptions (quick-question, instructional) handle the cases where decomposition would be wasteful. |
| "Investigating from N angles" note creates operator confusion about what Guru is doing | The note is a single-line emit ("Investigating from 3 angles: config file, env var, code default") before retrieval begins. It's informative, not alarming. |
| Hypothesis falsification finds contradicting evidence on every question, making answers longer and harder to act on | Hypothesis check is a single targeted falsification attempt, not an exhaustive adversarial search. If the falsification attempt confirms rather than contradicts the hypothesis, the answer is the same length as today. Contradiction surfacing only fires when real contradictions exist — which is exactly the case where the operator needs to know. |
| Seed edit drifts adjacent sections accidentally | Diff review AC (AC-9) and docs-lint (AC-11) catch this. Insertion-point editing (not rewrite) reduces risk. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
