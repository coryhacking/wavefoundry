# Architecture Reviewer Agent

Change ID: `12ecv-feat architecture-reviewer`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-06
Wave: `12ecs agent-feedback-harness`

## Rationale

Wavefoundry ships performance (`212`) and security (`213`) reviewer agents but has no architecture reviewer. Architecture drift is among the most costly semantic issues an agent can introduce — wrong layer coupling, boundary violations, misapplied patterns — and it is the dimension Böckeler names explicitly as the "Architecture Fitness Harness." Without a dedicated reviewer prompt, architecture review is entirely ad hoc and not available as a declarable required review lane in the pattern established by `12ecs-enh inferential-sensors-as-required-review-lanes`.

## Requirements

1. A seed prompt `214-architecture-reviewer.prompt.md` must guide an agent to assess a set of code changes against the host project's architecture documentation and domain boundaries.
2. The reviewer must check for: layer violations (calling across boundaries), coupling introduced where interfaces were expected, domain entities leaking across bounded contexts, and changes that conflict with recorded architecture decisions.
3. The reviewer must produce a structured verdict: `approved`, `approved-with-notes`, or `needs-revision` with specific findings.
4. The seed must instruct the reviewer to read `docs/architecture/` (current-state, layering-rules, domain-map, cross-cutting-concerns) and `docs/architecture/decisions/` before assessing.
5. The canonical lane name for `required_review_lanes` config must be `architecture-review`, consistent with `security-review` and `performance-review`.

## Scope

**Problem statement:** No architecture reviewer exists — architecture fitness is the most important semantic harness dimension and the only one with no dedicated inferential sensor.

**In scope:**

- `214-architecture-reviewer.prompt.md` seed prompt
- Integration with `007-review-system-overview.md` as a documented canonical lane
- Integration with `190-finalize-feature.prompt.md` to invoke when declared
- Canonical lane name `architecture-review` documented in the sensor lanes config guidance

**Out of scope:**

- Automated architecture fitness functions (ArchUnit-style) — those are computational sensors for a future wave
- Architecture documentation generation — the reviewer reads existing docs; if docs are absent it notes this as a finding
- Enforcement of architecture rules at commit time

## Acceptance Criteria

- AC-1: `214-architecture-reviewer.prompt.md` exists and guides an agent through a structured architecture review referencing project architecture docs.
- AC-2: The reviewer produces a structured verdict (`approved`, `approved-with-notes`, `needs-revision`) with specific findings.
- AC-3: `007-review-system-overview.md` documents `architecture-review` as a canonical inferential sensor lane.
- AC-4: `190-finalize-feature.prompt.md` invokes the architecture reviewer when `architecture-review` is declared in `required_review_lanes`.
- AC-5: The reviewer handles absent architecture docs gracefully — notes the gap as a finding rather than failing.

## Tasks

- [ ] Author `214-architecture-reviewer.prompt.md`
- [ ] Update `007-review-system-overview.md` to include `architecture-review` as a canonical lane
- [ ] Update `190-finalize-feature.prompt.md` to invoke architecture reviewer when declared
- [ ] Coordinate canonical lane name with `12ecs-enh inferential-sensors-as-required-review-lanes`

## Agent Execution Graph

| Workstream          | Owner       | Depends On                                        | Notes |
| ------------------- | ----------- | ------------------------------------------------- | ----- |
| seed authoring      | implementer | —                                                 |       |
| seed surface update | implementer | seed authoring + inferential-sensors lane changes |       |

## Serialization Points

- Canonical lane name (`architecture-review`) must align with `12ecs-enh inferential-sensors-as-required-review-lanes` before `007` and `190` are updated

## Affected Architecture Docs

N/A — the reviewer reads architecture docs but does not modify them; no boundary or data-flow impact.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority         | Rationale |
| ---- | ---------------- | --------- |
| AC-1 | required         | The seed prompt is the entire deliverable for this change |
| AC-2 | required         | Structured verdict is what makes the reviewer's output actionable and recordable as a lane signoff |
| AC-3 | required         | Lane must be documented to be declarable; undocumented canonical names create config drift |
| AC-4 | required         | finalize-feature integration closes the loop; without it the reviewer is ad hoc |
| AC-5 | important        | Graceful handling of absent docs ensures the reviewer works on any project, not just well-documented ones |

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
| Architecture docs may not exist in many projects | Reviewer notes absence as a finding; does not block |
| Architecture review is highly context-dependent — generic prompt may miss project-specific rules | Seed instructs reviewer to read project-specific decision records before assessing |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
