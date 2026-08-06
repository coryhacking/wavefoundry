# [Change Title]

Change ID: `<id-prefix>-<kind> <slug>` — **mint via the MCP `wf_new_*` tool** (e.g. `wf_new_bug`, `wf_new_enhancement`, `wf_new_change`). The MCP path borrows from future buckets when the natural prefix collides with existing IDs, so concurrent minting stays unique. Avoid the CLI for new IDs unless the MCP server is unavailable; if you must, use `wf lifecycle-id --kind <kind> --slug <slug>` (venv-aware dispatcher subcommand) rather than invoking `python3` against `lifecycle_id.py` directly. The subcommand is named `lifecycle-id` because the same prefix system is used for wave IDs and change IDs.
Change Status: `planned`
Owner: [role or person]
Status: planned
Last verified: 2026-08-06
Wave: [wave-id or TBD]

## Rationale

Why this change is needed. State a specific motivation a reviewer can understand without additional context.

## Requirements

1. [Numbered behavioral requirement — specific enough for an implementer to act on unambiguously]
2. …

## Scope

**Problem statement:** [What is broken, missing, or improving?]

**In scope:**

- …

**Out of scope:**

- …

## Acceptance Criteria

- [ ] AC-1: [Testable outcome — verifiable by QA, automated test, or manual check]
- [ ] AC-2: …

## Tasks

- [ ] [Concrete implementation step]
- [ ] …

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| [workstream-1] | [role] | —            |       |
| [workstream-2] | [role] | workstream-1 |       |


## Serialization Points

- [Explicit repo-relative file or integration path that this change will touch]

List real repository-relative paths here. Prepare uses these paths—not Scope, Rationale, or other narrative—to select automatic review lanes. Path scoring is a floor, not a ceiling: ANY lane may also be requested by judgment through the wave's `Requested review lanes` field, and the coordinator is expected to use it. Architecture review especially is usually a judgment call, since an ownership shift or a protocol change can live entirely in files whose paths recruit only the code lane. A requested lane is always honored and costs no receipt churn.

## Affected Architecture Docs

Which of `docs/ARCHITECTURE.md`, `docs/architecture/{current-state,domain-map,layering-rules,cross-cutting-concerns,data-and-control-flow,testing-architecture}.md`, or `docs/architecture/decisions/`* need updates, or `N/A` with rationale when the change is confined to a single module with no boundary/flow/verification impact.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required / important / nice-to-have / not-this-scope |           |


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
|      |            |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
