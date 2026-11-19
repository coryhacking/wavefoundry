# Identify the first useful outcome in Plan spec

Change ID: `23rgx-enh identify-first-useful-outcome`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-19
Wave: 23tct first-feature-workflow

## Rationale

In change 231kg, identifying packaging scripts as tooling could help a maintainer before inline Rust test counting was available. All five acceptance criteria were required for delivery. Their priority alone could not tell a team which outcome was useful first.

## Product Intent

A team planning a feature can identify its first useful outcome, demonstrate what the change delivers, and tell which result it must observe later in use. AC-2 checks this on a planning example.

## Requirements

1. Add the operator's guidance alongside Product Intent in the canonical Plan spec seed and the local Plan spec prompt:

   > When a change serves several user outcomes, identify the first outcome worth delivering on its own. Say who benefits, why it comes first, and how they could demonstrate it. Connect each outcome to the acceptance criteria that establish it. If the outcomes must ship together, explain the dependency. When success can only be observed after delivery, record what to observe and when.

2. Use the existing Product Intent and AC sections. Preserve the rule that a delivery criterion must be verifiable from evidence the change controls.

## Scope

Generic Plan spec guidance for any project. The implementer owns the two prompt edits. Reviewers inspect them read-only. Preserve skill routing, templates, readiness and close policies, and historical specs.

## Acceptance Criteria

- [x] AC-1: Both prompts contain the approved paragraph at the Product Intent instruction. A comparison confirms their wording agrees.
- [x] AC-2: On a multi-outcome planning example, a reader can identify who benefits first, why, the demonstration and the ACs for each outcome. A field-only result has an observation and a time to check it. If outcomes must ship together, the plan names the dependency.

## Tasks

- [x] Update both prompts.
- [x] Check wording and exercise the planning example. Record what the exercise showed.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Plan spec wording | Implementer | Readiness | One writer for both prompts |
| Verification | Reviewer | Wording | Read-only comparison and planning example |

## Serialization Points

- `.wavefoundry/framework/seeds/170-plan-spec.prompt.md`, `docs/prompts/plan-spec.prompt.md`

## Affected Architecture Docs

The prompt uses existing sections and evidence rules. No architecture edit is needed.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Installed and self-hosted projects receive the same instruction |
| AC-2 | required | The planning example checks the intended behavior |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-19 | Observe: Exact approved text occurs once per planning prompt. An independent reader planned latest-export recovery first (AC-1), coupled permission and audit for sensitive downloads (AC-2), and after the operator specified retention and the comparison metric, mapped row-count comparison to AC-3. Four weeks of support-call observations before/after rollout were proposed for follow-up. | Source comparison and disposable independent exercises. |
| 2026-11-19 | Readback: Add the approved paragraph to both Product Intent instructions; check the first demo, outcome-to-AC mapping and later field observation in a fresh planning example. | Readied scope. |
| 2026-11-19 | Recorded the operator's selected guidance for the official workflow. | Plan spec seed and local prompt both currently ask for at least one intent AC. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-19 | Extend the existing Product Intent instruction. | Applies at the point where authors choose outcomes and evidence. | A migration guide alone misses native users. Mandatory story records add work to single-outcome changes. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A field measure becomes an unverifiable close condition. | Record when to observe it separately from the AC proving delivery. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
