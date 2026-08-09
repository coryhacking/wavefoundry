# [Change Title]

Change ID: `<id-prefix>-<kind> <slug>` — **mint via the MCP `wf_new_*` tool** (e.g. `wf_new_bug`, `wf_new_enhancement`, `wf_new_change`). The MCP path borrows from future buckets when the natural prefix collides with existing IDs, so concurrent minting stays unique. Avoid the CLI for new IDs unless the MCP server is unavailable; if you must, use `wf lifecycle-id --kind <kind> --slug <slug>` (venv-aware dispatcher subcommand) rather than invoking `python3` against `lifecycle_id.py` directly. The subcommand is named `lifecycle-id` because the same prefix system is used for wave IDs and change IDs.
Change Status: `planned`
Owner: [role or person]
Status: planned
Last verified: 2026-08-08
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

[Declare review targets in either form below, then delete this bracketed note.]

Declare a target with a bullet whose content is entirely repo-relative paths, for example `` - `src/app/handler.py`, `docs/specs/` ``. When a target contains a space, declare it inside an explicit block instead:

```
**Review targets (repo-relative paths):**

- `docs/waves/1abc some slug/wave.md`
```

Prepare uses declared paths—not Scope, Rationale, or other narrative—to select automatic review lanes, and prose declares nothing in either form: a bullet containing one stray English word is prose (including inside the block, so a sentence there that merely quotes a path declares no target), a wrapped bullet is prose in its entirety, and a fenced example declares nothing. Adoption is per document, so declaring targets here never suppresses a sibling change doc's scoring, and declaring none keeps this document's whole-document coverage rather than emptying it. Path scoring is a floor, not a ceiling: ANY lane may also be requested by judgment through the wave's `Requested review lanes` field, and the coordinator is expected to use it. Architecture review especially is usually a judgment call, since an ownership shift or a protocol change can live entirely in files whose paths recruit only the code lane. A requested lane is always honored and costs no receipt churn.

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
