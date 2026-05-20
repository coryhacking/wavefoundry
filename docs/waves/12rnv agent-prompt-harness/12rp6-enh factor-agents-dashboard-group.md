# Dashboard: Factor as a Separate Group

Change ID: `12rp6-enh factor-agents-dashboard-group`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-20
Wave: `12rnv agent-prompt-harness`

## Rationale

The dashboard currently groups agent docs by broad buckets such as agent, persona, specialist, and journal. Factor agents are a distinct routing surface in this repo:

- they live under `.claude/agents/`
- they have their own factor taxonomy and invocation rules
- they are not the same thing as specialists

This is a new top-level dashboard group, not a specialist subtype.

Today that distinction is only visible in docs, not as a separate dashboard section. That makes the factor agents easy to miss and encourages people to mentally lump them in with specialists, which is the wrong mental model.

This change adds a dedicated dashboard group for factor agents so they are visible as a separate category.

## Requirements

1. Collect factor agents into their own dashboard group separate from specialists.
2. Preserve the existing specialist group behavior for `docs/agents/specialists/`.
3. Keep the factor group label stable and explicit, such as `Factor` or `factor-review`.
4. Expose the factor group in the dashboard data model and display order.
5. Keep factor docs in `.claude/agents/` or the repo-local factor surface that already exists.

## Scope

**Problem statement:** Factor agents are currently documented separately but visually indistinguishable from the specialist surface when people inspect the dashboard-oriented agent taxonomy.

**In scope:**

- dashboard data collection for factor agents
- dashboard grouping / ordering for the new factor section
- tests that verify factor docs appear in a separate group
- any small supporting docs updates needed to describe the new grouping

**Out of scope:**

- changing the meaning of specialist, persona, or journal groups
- renaming the factor agents
- changing factor routing policy or review policy semantics

## Acceptance Criteria

- AC-1: Factor agent files appear in a dedicated dashboard group separate from specialists.
- AC-2: Specialist agents continue to appear in the specialist group unchanged.
- AC-3: Persona and journal grouping behavior is unaffected.
- AC-4: The new factor group is visible in the dashboard snapshot data and rendered UI.
- AC-5: The factor group ordering is stable and documented.

## Tasks

- [x] Extend dashboard collection to read factor agent files from `.claude/agents/`.
- [x] Add a separate `Factor` group to the dashboard data model.
- [x] Update the UI/rendering path so factor agents appear under their own heading.
- [x] Add tests that verify factor docs are not folded into the specialist group.
- [x] Update the relevant docs surface to explain the factor-agent section.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|-----------|-------|------------|-------|
| factor-grouping | implementer | — | Dashboard data model + rendering + tests |

## Serialization Points

- Dashboard grouping order should be decided before the UI and snapshot tests are updated.

## Affected Architecture Docs

Likely `docs/agents/platform-mapping.md` and possibly `docs/agents/README.md` to describe the new dashboard grouping; otherwise `N/A` if the change remains purely dashboard-local.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | This is the core user-visible change |
| AC-2 | required | Must not disturb existing specialist grouping |
| AC-3 | required | No regressions to other agent groupings |
| AC-4 | required | The dashboard needs a visible separate section |
| AC-5 | important | Stable ordering makes the grouping understandable |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-20 | Change doc admitted into wave `12rnv agent-prompt-harness` from dashboard taxonomy review. | user request |
| 2026-05-20 | Implemented dedicated `Factor` dashboard group with factor discovery from `.claude/agents/`. | dashboard tests + docs-lint |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-20 | Treat factor agents as a distinct dashboard group rather than a specialist subtype. | The repo already treats factor agents as a separate routing surface, so the dashboard should reflect that taxonomy. | Fold factors into specialists — rejected because it obscures the taxonomy. |

## Risks

| Risk | Mitigation |
|------|------------|
| Factor docs are sparse or inconsistent | Add tests and explicit collection rules for the factor surface |
| UI order becomes confusing with another group | Document the order and keep it stable |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
