# Behaviour Harness: Test Generation Feedback Loop

Change ID: `12ecs-enh behaviour-harness-test-generation`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-06
Wave: `12ecs agent-feedback-harness`

## Rationale

Böckeler identifies the behaviour harness as "the weakest category" — functional correctness depends almost entirely on human review, with no automated feedback loop. Wavefoundry's `180-implement-feature.prompt.md` already asks agents to write tests, but there is no guidance on running them, reporting coverage, or using results to verify ACs before the operator review step. Closing this loop — generate tests, run them, report results back against change doc ACs — would make the behaviour harness as deliberate as the existing docs-lint feedback loop.

## Requirements

1. The implement-feature workflow must instruct agents to run tests after generating them (not just write them) and report pass/fail counts.
2. The finalize-feature workflow must include a test-results summary as a prerequisite for requesting operator review.
3. Where a project has coverage tooling registered, agents must include a coverage summary in the finalize-feature output.
4. The AC checklist in the change doc must be referenced when reporting test results — each AC should be traceable to at least one test.
5. Guidance must be pragmatic: if the project has no test runner registered, agents note this and proceed rather than blocking.

## Scope

**Problem statement:** Agents write tests but results are never fed back into the wave lifecycle — ACs are not verified by tests before operator review.

**In scope:**

- Updates to `180-implement-feature.prompt.md`: run tests after writing them; report results
- Updates to `190-finalize-feature.prompt.md`: include test results + AC traceability in pre-review summary
- A convention for mapping test output back to AC IDs (naming convention or comment annotation)
- Seed documentation on the behaviour harness and AC traceability pattern
- Optional coverage reporting when tooling is available (integrates with sensors config from `12ecs-feat post-edit-computational-sensors`)

**Out of scope:**

- Test generation itself — agents already do this; this change closes the feedback loop
- Mutation testing or property-based testing
- CI/CD integration

## Acceptance Criteria

- AC-1: `180-implement-feature.prompt.md` instructs agents to run tests and report pass/fail before moving to finalize.
- AC-2: `190-finalize-feature.prompt.md` requires a test-results summary as part of the operator review request.
- AC-3: The pre-review summary includes a per-AC check noting which ACs have test coverage and which do not.
- AC-4: Projects with no test runner proceed without error — the summary notes "no test runner configured."
- AC-5: Seed documentation explains AC traceability and the behaviour harness pattern.

## Tasks

- [ ] Update `180-implement-feature.prompt.md` to include test-run step with structured output
- [ ] Update `190-finalize-feature.prompt.md` to require test-results + AC coverage summary
- [ ] Define AC traceability convention (naming or annotation pattern)
- [ ] Add seed doc section on behaviour harness and AC traceability
- [ ] Coordinate with `12ecs-feat post-edit-computational-sensors` for test runner config integration

## Agent Execution Graph

| Workstream      | Owner       | Depends On   | Notes |
| --------------- | ----------- | ------------ | ----- |
| seed updates    | implementer | —            | can start before sensors config finalizes |
| AC traceability | implementer | seed updates |       |

## Serialization Points

- AC traceability convention should be agreed before seed updates are finalized

## Affected Architecture Docs

N/A — confined to seed surface and workflow guidance.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority         | Rationale |
| ---- | ---------------- | --------- |
| AC-1 | required         | Running tests is the minimum viable feedback loop; writing without running is no loop at all |
| AC-2 | required         | Test results must reach the operator review step or the loop never closes |
| AC-3 | important        | Per-AC coverage check is the highest-value output; adds traceability without blocking |
| AC-4 | required         | Must not break projects without test runners — adoption blocker if it does |
| AC-5 | important        | Seed documentation embeds the pattern into agent memory for future waves |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| AC traceability is hard to enforce without tooling | Make it a convention (naming + seed guidance) first; tooling can follow |
| Test results vary in format by stack | Report exit code + summary line; agent adapts per stack |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
