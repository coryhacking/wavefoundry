# Explain a delivered change to its next maintainer

Change ID: `23ve5-enh explain-delivered-work`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-19
Wave: 23ve6 developer-delivery-walkthrough

## Rationale

Developers report that a green delivery review leaves practical questions unanswered. A maintainer might know that a retry test passed yet have no idea whether a later request succeeded or the test merely counted retries.

## Product Intent

After review, the engineer taking responsibility for the work can trace a changed behavior from its entry point to the check that proves it, explain a consequential choice and identify what remains untested. This extends the handoff in the project vision. AC-1 through AC-3 exercise that outcome. The team’s later experience maintaining the change remains a field observation.

## Requirements

1. Provide the standalone `/wf-explain` skill. Review wave offers that same skill once before Close. An engineer may also invoke it directly with a wave or spec, including a closed record, without rerunning review. Support an explicit request such as “Explain this wave” or “Walk me through spec <id>.” Use the reviewed wave by default. For a named change, limit the explanation to that change and dependencies needed to understand it. Ask which record the developer means if the reference is ambiguous.
2. Lead with what users or maintainers experience differently. Trace one representative path through the actual implementation. Link to the relevant files and symbols. Explain the reason for the design and any consequential alternative the team considered. Attribute decisions to a spec, decision log or review finding. If the record gives no rationale, say so. For a wave with several changes, explain how they fit together and where to drill down.
3. Connect each material claim to a named test, check or observation. Explain the condition it exercises, what result distinguishes success from failure and what actually ran. Distinguish test source from run evidence. Identify deferred coverage, limits, open findings and changes since review. Give a reproducible check when the project records support one. Adapt this to docs-only and configuration changes.
4. Offer “test my understanding” as an opt-in conversation. Ask one practical question at a time about the actual work, wait for the engineer’s answer, explain any gap using the evidence and allow a retry or stop. For example, ask which assertion proves that the listener served a fresh request after a failure. Never answer for the engineer or require a score.
5. Treat the walkthrough as read-only. Skipping, stopping or answering incorrectly leaves close eligibility and approvals untouched. If a question uncovers a real discrepancy, identify the evidence and direct it to the normal review/repair path. Completing a walkthrough never closes the wave or grants signoff.

## Scope

Register wf-explain in the shared skill renderer as a thin pointer to one Explain prompt. Deliver the prompt to fresh and upgraded projects and link it from Review wave and the prompt catalog. Reuse the maintained project vocabulary and existing retrieval tools. Keep the explanation in the conversation unless the operator requests a saved copy. No new tool, dashboard, lifecycle phase, test execution, comprehension ledger or required artifact.

## Acceptance Criteria

- [x] AC-1: On a completed multi-change wave, a reader traces one observable behavior to implementation and verification from the walkthrough. Asking about one admitted change returns the relevant references without attributing sibling work to it.
- [x] AC-2: On a case with a recorded tradeoff and incomplete test evidence, the walkthrough explains the actual choice, distinguishes the test’s assertion from its execution and identifies the gap. A second case with no recorded alternative produces no invented rationale.
- [x] AC-3: In a teach-back trial, the agent waits for an answer, responds to a plausible misunderstanding using the actual assertion, and accepts a stop. An independent reader can locate the evidence and explain why a weaker check would miss the failure. Report who participated and whether the reader was an agent or a human.
- [x] AC-4: A rendered wf-explain skill opens the same prompt as the ordinary review handoff on supported skill hosts. Direct invocation works on a named closed record. An ordinary delivery review offers the walkthrough once. Decline, unanswered offer and completed teach-back all leave review authority, closure and project artifacts unchanged. A trial using renamed lifecycle nouns retains the project’s terms.

## Tasks

- [x] Confirm the authoring, installation and existing-project reconciliation paths for Review wave and its catalog entry. Identify the source record and evidence used for the walkthrough trials.
- [x] Implement the skill registry entry and backing Explain prompt. Render the active skill surfaces and route the post-review offer and direct requests to that prompt. Carry it into the shipped template and self-hosted instructions.
- [x] Exercise AC-1 through AC-4. Compare the explanation with the actual diff, decisions, tests and review record. Record coverage limits and validate documentation.

## Agent Execution Graph

The implementer owns the skill registry, rendering tests and generated surfaces. The documentation implementer owns the prompt and template edits. QA and docs-contract reviewers inspect the trial, source fidelity and authority boundaries read-only. Run trials after the guidance is available.

## Serialization Points

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `docs/prompts/explain.prompt.md`

- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/review-wave.prompt.md`
- `docs/prompts/review-wave.prompt.md`
- `docs/prompts/index.md`

## Affected Architecture Docs

N/A. The change uses the existing conversational workflow and review evidence. It adds no runtime, storage or authority boundary.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Demonstrates useful wave and change scope. |
| AC-2 | required | Protects factual accuracy. |
| AC-3 | required | Exercises interactive understanding. |
| AC-4 | required | Protects existing workflow and downstream names. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-19 | Planned the handoff after delivery review. | Review wave describes recording findings and approvals and reserves closure for the operator. Walkthrough efficacy awaits a trial. |
| 2026-11-19 | Operator selected the exact post-review question: “Would you like a walkthrough of the changes?” Ask it once and wait. | Operator direction during preparation. |
| 2026-11-19 | Readback: maintainers trace a delivered behavior to code and executed evidence, ask about one spec and optionally practice explaining it. | Coordinator owns guidance and trials. Renderer implementer owns distribution and host checks. AC-1 through AC-4 cover scope, evidence, interaction and delivery. |
| 2026-11-19 | A source-grounded agent delivered a closed-wave walkthrough of 23tcw and a narrower walkthrough of 23tcu. A separate reader located seed 209 via the builder and QA guides, explained why the fresh reply proves recovery, and kept the sibling technology work outside 23tcu. | The 23tcu Progress Log distinguishes five retries from a successful fresh connection. In three controls the explainer credited retries on the older matched pass, recovery on the later matched HTTP 200 pass and no recovery on an unversioned green result. It reported the missing design rationale. |
| 2026-11-19 | A separate conversational trial used “batch” and “task doc.” The agent asked the review question once and waited. After acceptance and explicit teach-back opt-in, it asked one question, corrected the claim that a unit assertion proved deployment, and accepted a stop. Decline and silence ended the offer. | These read-only trials called no lifecycle writers. The reader and the conversational participants were agents. Human comprehension and subsequent maintenance remain unobserved. |
| 2026-11-19 | The renderer installed Explain on three active hosts, preserved customized bytes on rerender and produced an empty second manifest. | Default renderer and vocabulary modules: 274 tests passed. Renamed profile renderer: 221 tests with three skips. Focused package and upgrade checks passed. |
| 2026-11-20 | Refined the operator handoff after its first use. The walkthrough now traces architectural and dependency changes, named algorithms, implementation issues, accepted compromises, performance and security considerations, and outstanding work. | Explain asks for the reviewed diff and decision evidence. It distinguishes expected performance from a benchmark, an implemented safeguard from an exercised check, and a resolved issue from an inherited workaround. |
| 2026-11-20 | The operator asked the walkthrough to explain why the team chose an algorithm and how a performance change improved the outcome. | The prompts separate suitability from a documented selection decision, and compare the same workload before and after when recorded. An intermediate metric supports only the improvement it measures. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-19 | Offer a source-linked walkthrough and optional teach-back through the review handoff. | A developer can follow up on the actual test or design decision while the evidence is current. A generic summary could still miss the developer’s question, so test the explanation with a fresh reader. | A mandatory quiz could reward memorization and delay closure. A standalone generated report adds upkeep and cannot respond to a misunderstanding. |
| 2026-11-19 | Name the standalone skill wf-explain. | The operator selected direct access alongside the post-review offer. | Restricting the walkthrough to review would make prior deliveries harder to explain. |

## Risks

A polished explanation may hide missing evidence. Require source references and explicit unknowns. A quiz may feel like employee assessment. Keep questions practical and voluntary and store no individual scores. After release, ask a willing maintainer whether the walkthrough helped them explain or change the implementation without reconstructing the review.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
