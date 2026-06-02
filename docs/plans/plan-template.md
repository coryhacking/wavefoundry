# [Change Title]

Change ID: `<id-prefix>-<kind> <slug>` — **mint via the MCP `wave_new_*` tool** (e.g. `wave_new_bug`, `wave_new_enhancement`, `wave_new_change`). The MCP path borrows from future buckets when the natural prefix collides with existing IDs, so concurrent minting stays unique. Avoid the CLI for new IDs unless the MCP server is unavailable; if you must, use `.wavefoundry/bin/lifecycle-id --kind <kind> --slug <slug>` (venv-aware launcher) rather than invoking `python3` against `lifecycle_id.py` directly. The launcher is named `lifecycle-id` because the same prefix system is used for wave IDs and change IDs.
Change Status: `planned`
Owner: [role or person]
Status: planned
Last verified: 2026-06-02
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

- [Shared file or integration gate that requires coordination before parallel work proceeds]

## Affected Architecture Docs

Which of `docs/ARCHITECTURE.md`, `docs/architecture/{current-state,domain-map,layering-rules,cross-cutting-concerns,data-and-control-flow,testing-architecture}.md`, or `docs/architecture/decisions/`* need updates, or `N/A` with rationale when the change is confined to a single module with no boundary/flow/verification impact.

## AC Priority

(Populated at Prepare wave.)


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
