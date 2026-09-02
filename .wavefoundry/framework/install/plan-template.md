# [Change Title]

Change ID: `<id-prefix>-<kind> <slug>`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: {{generated_at}}
Wave: TBD

## Rationale

Why this change is needed. State a specific motivation a reviewer can understand without additional context.

## Requirements

1. [Numbered behavioral requirement]

## Scope

**Problem statement:** [What is broken, missing, or improving?]

**In scope:**

- …

**Out of scope:**

- …

## Acceptance Criteria

- [ ] AC-1: [Testable outcome]

## Tasks

- [ ] [Concrete implementation step]

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| [workstream] | [role] | — | |

## Serialization Points

(Replace this note with review targets. These examples are fenced so the scaffold declares nothing.)

```
- `src/app/handler.py`, `docs/specs/`
```

When a target contains a space, use an explicit block; keep examples fenced:

```
**Review targets (repo-relative paths):**

- `docs/waves/1abc some slug/wave.md`
```

Prepare selects automatic review lanes from declared paths, not from narrative prose. Any example retained in this template must remain fenced. Verify this scaffold declares no targets before use.

A declared path token has at least one `/`, so a root-level file (a changelog, a readme) is never a token in either form, and a bullet declares all or nothing in either form, so one such token turns the whole bullet into prose and every other path in it goes undeclared with it. In a bullet a `*` disqualifies the token too; inside the explicit block a span is kept only when its last segment carries an extension or the span ends in `/`, so there a `*` span is accepted as a phantom (a `*.json`, a `dir/*/`) that matches no file and recruits a lane only through a trigger token it happens to carry (a directory prefix, an extension, or a trigger basename), a block holding only phantoms leaves the document declared with whatever roster those triggers recruit (empty when none is a trigger), and any other `*` span turns its bullet into prose. Put a root-level file in its own prose bullet, and declare the directory that holds globbed files.

## Affected Architecture Docs

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses its approvals.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required / important / nice-to-have / not-this-scope | |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| | | |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| | | | |

## Risks

| Risk | Mitigation |
| --- | --- |
| | |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
