# Wave Close: Mandatory Operator Review Lane

Change ID: `12eb2-enh wave-close-operator-review`
Change Status: `done`
Owner: Engineering
Status: done
Last verified: 2026-05-06
Wave: `12eas background-index-rebuild`

## Rationale

`wave_close` can currently be called by an agent without any operator signoff, allowing a wave to be closed without the operator ever approving the work. A mandatory operator review lane blocks closure until the operator explicitly approves — either by asking to close the wave (implicit approval) or by responding to an explicit agent prompt for review (giving the operator an opportunity for manual testing and inspection before the wave is sealed).

## Requirements

1. `wave_review` must enforce an `operator` review lane that is required before a wave can be closed.
2. `wave_close(mode="create")` must fail if the operator lane is not satisfied.
3. Operator approval is satisfied by **either** of two paths:
   a. The operator explicitly asks to close the wave (e.g., "close the wave", "yes close it") in the current session — this constitutes implicit signoff.
   b. The agent explicitly asks the operator for review approval and receives a positive confirmation — this gives the operator an opportunity for manual testing, spot-checks, or any review they want to do before sealing.
4. When the agent is about to call `wave_close`, if the operator has not already issued a close request, the agent must pause and ask for operator review approval before proceeding.
5. The agent's review approval prompt should invite the operator to do manual tests or any other review they want before sealing.
6. `wave_review` must return a lint error with recovery guidance when the operator lane is not yet satisfied.
7. The signoff line format (`operator-signoff: approved`) must be documented in the wave record template and serve as the machine-readable marker for `wave_review` to check.
8. Seed prompts (`190-finalize-feature.prompt.md`, `007-review-system-overview.md`) must document the operator review lane and both approval paths so the behavior is implemented consistently in all seeded repositories.

## Scope

**Problem statement:** Agents can close waves without operator knowledge, review, or approval.

**In scope:**

- New required review lane `operator` enforced by `wave_review` and `wave_close`
- Two approval paths: operator-initiated close request (implicit) or agent-prompted explicit confirmation
- `## Review Evidence` signoff line: `operator-signoff: approved`
- Update to wave record template (`docs/waves/template/wave.md` or equivalent)
- Update to `wave_review` lane validation logic in `server.py`
- Update to seed prompts: `007-review-system-overview.md`, `190-finalize-feature.prompt.md`

**Out of scope:**

- Multi-operator approval workflows
- Role-based access control
- Asynchronous or out-of-band approval (approval must happen in the current session)

## Acceptance Criteria

- AC-1: `wave_review` returns a lint error when `operator-signoff: approved` is absent from `## Review Evidence`.
- AC-2: `wave_close(mode="create")` returns an error when the operator lane has not been signed off.
- AC-3: Adding `operator-signoff: approved` to `## Review Evidence` causes `wave_review` to pass the operator lane.
- AC-4: The wave record template includes `operator-signoff: approved` as a placeholder under `## Review Evidence`.
- AC-5: `wave_review` response includes `operator` in its `required_lanes` list.
- AC-6: `190-finalize-feature.prompt.md` documents the operator review lane with both approval paths and instructs the agent to ask for approval (with an invitation to do manual tests) before calling `wave_close`.
- AC-7: `007-review-system-overview.md` lists `operator review` as a generic review lane with a note on the two approval paths.

## Tasks

- [x] Identify where `wave_review` lane validation runs in `server.py` and add `operator` as a required lane
- [x] Add signoff-line check: scan `## Review Evidence` for `operator-signoff: approved`
- [x] Propagate lane failure into `wave_close` pre-check
- [x] Update wave record template to include `operator-signoff: approved` placeholder under `## Review Evidence`
- [x] Update `190-finalize-feature.prompt.md`: upgrade guardrail to formal operator review lane with both approval paths and agent ask behavior
- [x] Update `007-review-system-overview.md`: add `operator review` to Generic Review Lanes
- [x] Add tests: missing signoff → review fails, signoff present → review passes, close blocked without signoff

## Agent Execution Graph

| Workstream       | Owner       | Depends On  | Notes |
| ---------------- | ----------- | ----------- | ----- |
| server impl      | implementer | —           |       |
| template update  | implementer | server impl |       |
| tests            | implementer | server impl |       |

## Serialization Points

- `server.py` is shared with `12eb0-enh wave-reopen`; coordinate edits.

## Affected Architecture Docs

N/A — confined to wave lifecycle enforcement with no boundary or data-flow impact.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | wave_review must enforce the lane — no signoff means no close |
| AC-2 | required  | wave_close must be blocked without signoff |
| AC-3 | required  | Adding signoff must unblock review and close |
| AC-4 | required  | Template placeholder ensures new waves are aware of the requirement |
| AC-5 | important | required_lanes in response makes the lane machine-discoverable |
| AC-6 | required  | Seed prompt is the source of truth for all seeded repos |
| AC-7 | important | Overview seed surfaces the lane to agents reading framework docs |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-06 | Signoff line is `operator-signoff: approved` in `## Review Evidence` | Simple text scan, no new schema; consistent with existing review evidence convention | Separate signoff file; wave metadata field |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Existing closed waves lack signoff lines — retroactive lint failures | Only enforce for waves opened after this change ships; existing waves are unaffected |
| Operator forgets to sign off, blocking closure indefinitely | `wave_review` response includes clear recovery guidance pointing to the exact line to add |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
