# Wave Implement MCP Tool

Change ID: `12sqb-enh wave-implement-mcp-tool`
Change Status: `implemented`
Owner: software-engineer
Status: implemented
Last verified: 2026-05-21
Wave: 12sq2 enterprise-role-seeds-and-lint

## Rationale

`wave_prepare`, `wave_review`, and `wave_close` all have MCP tools, but there is no `wave_implement` tool, and `wave_review` has no concept of phase. The full wave lifecycle has two review points — a prepare-phase review of the plan and an implementation-phase review of the delivered code — but currently `wave_review` is only called once (implementation phase) with no mechanism to distinguish the two. Adding a `phase` parameter to `wave_review` and a `wave_implement` gate tool closes both gaps: the prepare-phase review reviews the change docs before any code is touched, `wave_implement` enforces that review is complete before implementation begins, and the implementation-phase review reviews the delivered implementation.

## Requirements

1. `wave_review` must accept a `phase` parameter: `"prepare"` or `"implementation"` (default, for backwards compatibility).
2. `wave_review(phase="prepare")` must record prepare-phase lane signoffs in a dedicated `## Prepare Review Evidence` section in wave.md, entirely separate from `## Review Evidence` used by implementation signoffs. This eliminates any substring collision between the two sets of signoffs.
3. A `wave_implement` MCP tool must exist and be callable against an active wave.
4. `wave_implement` must verify that both the automated Wave Council prepare-phase verdict (`12sp5`) and the full prepare-phase lane review (`wave_review(phase="prepare")`) are recorded and clean before proceeding.
5. If either check fails, `wave_implement` must return an error describing what must be resolved before implementation can begin.
6. On success, `wave_implement` must return: the ordered list of admitted changes with their implementation dependencies, the Journal Watchpoints from wave.md, and active serialization points.
7. `wave_implement(mode="create")` must transition the wave status to `implementing` in wave.md.
8. `wave_implement(mode="dry_run")` must validate readiness and return the implementation context without writing to disk.
9. All tools that check wave status must handle `implementing` gracefully — audit `wave_current`, `wave_validate`, and the dashboard for status handling before implementation.
10. A successful `wave_add_change` call must include `wave_add_change` in its `next_tools` list so operators can immediately add another change in the same session.

## Scope

**Problem statement:** `wave_review` has no phase concept so prepare-phase and implementation-phase reviews cannot be distinguished; `wave_implement` does not exist so there is no formal gate between the two review cycles.

**In scope:**

- `phase` parameter on `wave_review`: `"prepare"` and `"implementation"` (default)
- Dedicated `## Prepare Review Evidence` section in wave.md for prepare-phase lane signoffs — avoids any substring collision with `## Review Evidence`
- `wave_implement` MCP tool in `server_impl.py` with `dry_run` and `create` modes
- `wave_implement` gate checks: automated Council verdict (from `12sp5`) + prepare-phase lane review complete
- Returns: ordered change list with dependencies, Journal Watchpoints, serialization points
- Wave status transition to `implementing` on `create` mode success
- Audit and fix any status-handling gaps for `implementing` in `wave_current`, `wave_validate`, dashboard
- MCP tool registration and surface exposure
- `wave_add_change` next_tools fix

**Out of scope:**

- Per-change implementation progress tracking (separate concern)
- Automatic change doc assignment to agent roles
- Changes to `wave_prepare` tooling

## Acceptance Criteria

- [x] AC-1: `wave_review(phase="prepare")` records prepare-phase lane signoffs in `## Prepare Review Evidence`; does not write to or conflict with `## Review Evidence`
- [x] AC-2: `wave_review(phase="implementation")` (or default) behaves identically to current `wave_review` behavior; writes to `## Review Evidence` as before
- [x] AC-3: `wave_implement` returns an error when the automated Council verdict (`12sp5`) is missing or has unresolved issues
- [x] AC-4: `wave_implement` returns an error when the prepare-phase lane review is incomplete
- [x] AC-5: `wave_implement` returns ordered changes, Journal Watchpoints, and serialization points when both checks pass
- [x] AC-6: `wave_implement(mode="create")` transitions wave status to `implementing` in wave.md
- [x] AC-7: `wave_implement(mode="dry_run")` validates readiness and returns context without writing
- [x] AC-8: `wave_current`, `wave_validate`, `wave_pause`, and dashboard handle `implementing` status gracefully
- [x] AC-9: Tool is registered in the MCP surface and callable via `mcp__wavefoundry__wave_implement`
- [x] AC-10: At least one passing and one failing test cover each gate check
- [x] AC-11: A successful `wave_add_change` call includes `wave_add_change` in its `next_tools` list, so operators can chain sequential change admissions in a single session

## Tasks

- [x] Read `wave_review` and `wave_close` implementations in `server_impl.py` for pattern reference
- [x] Audit `wave_current`, `wave_validate`, and dashboard for `implementing` status handling gaps
- [x] Add `phase` parameter to `wave_review`; implement prepare-phase signoff writing to `## Prepare Review Evidence`
- [x] Implement `wave_implement` handler: Council verdict check, prepare-phase lane check, context extraction, status transition
- [x] Register `wave_implement` in MCP surface
- [x] Add `wave_add_change` to `next_tools` in the `wave_add_change` handler response
- [x] Write tests: phase parameter (prepare vs implementation), missing Council verdict (fail), incomplete prepare-phase review (fail), both checks pass, dry_run (no write), implementing status handling
- [x] Run full test suite; confirm no regressions

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Read existing tool patterns + status audit | software-engineer | — | Reference wave_review / wave_close; audit wave_current, wave_validate, dashboard |
| Add phase parameter to wave_review | software-engineer | — | Needs `framework_edit_allowed` gate |
| Implement wave_implement handler | software-engineer | 12sp5 verdict format, phase parameter | Same gate pass |
| Fix implementing status handling (if gaps found) | software-engineer | Status audit | Same gate pass |
| MCP registration | software-engineer | Handler | |
| next_tools fix for wave_add_change | software-engineer | — | Same gate pass |
| Tests | software-engineer | All above | |
| Full test suite pass | qa-reviewer | Tests | |

## Serialization Points

- `framework_edit_allowed` gate: single open/close around all `server_impl.py` and dashboard edits
- Must implement after `12sp5` — `wave_implement` depends on the Council verdict format (`prepare-council` marker) defined there
- `## Prepare Review Evidence` section format must be agreed before implementing `wave_review` phase support and `wave_implement` gate check — both depend on the same section
- MCP surface changes require server reconnect to pick up new tool (FastMCP limitation)

## Affected Architecture Docs

N/A — change is confined to `server_impl.py`, dashboard files, and their tests. No boundary, flow, or architectural impact beyond the review phase distinction and implement-stage entry point.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Core — prepare-phase review must be in a dedicated section to avoid signoff collision |
| AC-2 | required | Backwards compatibility — existing wave_review behavior must not regress |
| AC-3 | required | Council verdict gate |
| AC-4 | required | Prepare-phase lane review gate |
| AC-5 | required | Implementation context is the primary value of wave_implement |
| AC-6 | required | State transition makes implementation status observable |
| AC-7 | required | Dry-run parity with other lifecycle tools |
| AC-8 | required | implementing status must not break existing tooling |
| AC-9 | required | Must be callable via MCP |
| AC-10 | required | Test coverage gate |
| AC-11 | important | Improves agent UX when admitting multiple changes sequentially |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-05-21 | Change created | Gap identified: wave_prepare/review/close have MCP tools; wave_implement does not |
| 2026-05-21 | Scope expanded to include wave_review phase parameter | Dual-phase review requirement: prepare-phase (plan) + implementation-phase (code) |
| 2026-05-21 | Renamed pre-implementation to post-prepare throughout | Naming is more precise and pairs symmetrically with post-implementation |
| 2026-05-21 | Namespace fix: dedicated Prepare Review Evidence section instead of -pre suffix | Council blocking finding: -pre suffix causes substring collision with implementation signoff detection |
| 2026-05-21 | Added AC-8: implementing status audit | Council advisory: new status value must be handled by all existing tools |
| 2026-05-21 | Renamed post-prepare → prepare, post-implementation → implementation | Operator: phase names should be the phase they belong to, not what they follow |
| 2026-05-21 | `wave_review` phase parameter implemented; `## Prepare Review Evidence` section added | `_prepare_review_evidence` helper added to server_impl.py |
| 2026-05-21 | `wave_implement_response` implemented; `implementing` status audit complete | `wave_current`, `wave_validate`, `wave_pause`, dashboard all handle `implementing`; 1566 tests pass |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-05-21 | Implement after 12sp5 — depends on Council verdict format | Cannot check verdict without knowing the prepare-council marker format | Define verdict format in this change |
| 2026-05-21 | Transition to `implementing` status on create | Makes wave state observable; consistent with other lifecycle tools that write status | Leave status as `active` throughout implementation |
| 2026-05-21 | Default phase="implementation" for backwards compatibility | Existing waves and tooling that call wave_review without phase must not break | Require explicit phase always |
| 2026-05-21 | Dedicated `## Prepare Review Evidence` section instead of -pre suffix keys | Eliminates substring collision: architecture-reviewer appears in architecture-reviewer-pre, breaking implementation signoff detection | Separate signoff key namespace with -pre suffix |
| 2026-05-21 | phase="prepare" and phase="implementation" (not "post-prepare"/"post-implementation") | Names the phase the review belongs to; cleaner and symmetric | post-prepare / post-implementation |

## Risks

| Risk | Mitigation |
| --- | --- |
| MCP reconnect required after adding new tool (FastMCP limitation) | Document in implementation notes; user must reconnect after server restart |
| Verdict format dependency on 12sp5 creates sequencing risk | Agree prepare-council marker as part of 12sp5 implementation before touching this change |
| implementing status breaks undiscovered tool paths | Status audit task explicitly required before other implementation work |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
