# Record accepted-not-repaired findings through the review-event tool

Change ID: `22r95-enh review-event-accepted-not-repaired`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-11-06
Wave: TBD

## Rationale

In wave 22qr6, the council chair needed to record a real but accepted residual gap (`22qr6-chair-22qoy-writer-exhaustiveness`) as accepted and not repaired. The review-evidence validator requires a `promotion_trigger` field for that classification, but the `wf_review_event` MCP schema does not expose it. The finding therefore had to carry a "cheap read-only follow-up" judgment and stays open with its repair pending. That misstates its real state in the ledger and in every later readout.

## Product Intent

Reviewers can record an accepted residual risk with its trigger for re-evaluation, so the ledger shows accepted findings as terminal and honestly classified instead of as pending repairs.

## Requirements

1. `wf_review_event` accepts every field that the review-evidence validator requires for each legal disposition, including `promotion_trigger`, and passes it through.
2. The tool description and the exported vocabulary list the field, and contract tests compare them with the validator registry.

## Scope

**In scope:** the `wf_review_event` input schema and pass-through, the tool description, and contract tests.

**Out of scope:** changing disposition semantics or the close gate.

## Acceptance Criteria

- [ ] AC-1: A `maybe_later` / accepted finding with a `promotion_trigger` can be recorded through `wf_review_event` and reads back as terminal with that trigger; on the current code the tool cannot express it.
- [ ] AC-2: A contract test fails if the MCP schema omits a field the validator requires for any disposition.
- [ ] AC-3: The change's own suites and every test it adds pass, the documents it edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [ ] Expose and pass through `promotion_trigger`.
- [ ] Add a schema-versus-validator contract test.
- [ ] Update the tool description and spec.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| tool       | implementer | —          |       |


## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/`, `.wavefoundry/framework/scripts/review_evidence.py`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: a tool-surface addition with no boundary change. Update `docs/specs/mcp-tool-surface.md`.

## Platform Behavior

Platform-neutral.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | important | Honest ledger state for accepted risks. |
| AC-2 | important | Prevents recurrence of schema drift. |
| AC-3 | required  | Change-local verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-06 | Filed from the wave 22qr6 readiness-chair observation at operator request. | 22qr6 ledger finding `22qr6-chair-22qoy-writer-exhaustiveness` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A handler change requires the digest pin refresh | Refresh the pin as part of the change. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
