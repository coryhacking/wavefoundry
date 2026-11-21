# Pause reviewed deliveries for operator closure

Change ID: `23xo6-enh pause-reviewed-deliveries-for-closure`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-21
Wave: 23xo7 awaiting-closure

## Rationale

A team can prepare several waves but implement only one at a time. Today a paused delivery points the operator to Resume even after all specialist reviews pass. Closing that delivery can clear the handoff and edit gates used by a newer open wave.

## Product Intent

An engineer can finish and review one wave, pause it for operator closure, and implement the next. The operator can distinguish delivered work from interrupted work and close a specific delivery while the active engineer keeps their working context.

## Requirements

1. Keep the persisted status `paused`. Derive the presentation label **Awaiting closure** from current delivery evidence. Check a nonempty admitted scope, implemented or completed members, readable aligned records and settled criteria and tasks, current policy-required delivery approvals, and resolved required findings. Missing, invalid, stale or ambiguous evidence yields the ordinary paused presentation. Use existing vocabulary, record discovery and authority readers.
2. Show the distinction in wave discovery, the dashboard and pause guidance. Offer Close for a qualifying paused delivery and Resume for other paused work. State that operator authorization and the ordinary close checks still apply. The current repository-wide suite receipt and operator signoff belong to Close. Reads and pause never authorize closure. Preserve the single open slot and existing status filters and totals.
3. Closing paused A while B is open must preserve B’s handoff reference, current focus and gates on success, refusal and a repeated close. Resolve repository-wide ownership under lifecycle serialization, including when A and B occupy different configured parent activation scopes. Preserve shared state when ownership is ambiguous. Normal close still cleans A’s owned work and preserves existing close behavior when A owns the active workspace.
4. Teach the sequence in the shipped guidance and project workflow. Name the target when operating on multiple waves. Give the operator a single reproducible example.

## Scope

The change covers the lifecycle readers, dashboard presentation, close-side shared state and the guidance that routes operators. Existing pause, review, implement and close commands provide the workflow.

## Acceptance Criteria

- [x] AC-1: A public pause followed by discovery reports a delivered, reviewed wave as paused and awaiting closure. The dashboard agrees. An unfinished paused wave still offers Resume. Removing required delivery evidence, reopening a checklist item or making a member unreadable removes the hint without changing status.
- [x] AC-2: With paused reviewed A and implementing B, a refused and then authorized successful Close A preserve B’s handoff, focus and gates. A is closed only on success. Retrying the close preserves B’s context. Exercise repository-wide activation and separate configured parent activation scopes. Verify ambiguous ownership preserves shared state. Existing single-wave close and single-OPEN behavior still pass their tests.
- [x] AC-3: Shipped and local guidance shows Review, Pause, Implement next, and operator-authorized Close by ID. The two existing reviewed, paused waves and this wave can be inspected under the same model. Docs validation and the framework suite pass.

## Tasks

- [x] Derive and present the delivery hint using shared validated evidence.
- [x] Protect another open wave’s shared resources on every close outcome and test with two waves.
- [x] Update shipped and local workflow instructions, exercise normal entry points and validate the delivery.

## Agent Execution Graph

| Workstream | Owner | Depends on |
| --- | --- | --- |
| Delivery evidence and presentation | Implementer and frontend developer | Readiness |
| Close ownership and workflow | Implementer and coordinator | Readiness |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/lifecycle_gates.py`
- `.wavefoundry/framework/scripts/dashboard_lib.py`
- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/seeds/190-close-wave.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/review-wave.prompt.md`

## Affected Architecture Docs

Update the lifecycle contract in `docs/specs/mcp-tool-surface.md` and relevant shared-state flow in `docs/architecture/data-and-control-flow.md`.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Route the operator correctly. |
| AC-2 | required | Preserve another engineer’s active work. |
| AC-3 | required | Make the sequence discoverable in installed projects. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-21 | Planned the operator’s multi-wave workflow. | Paused deliveries 23zbf and 23zbg and the two-wave fixture from the design review. |

2026-11-21: Readback: derive the close hint from settled delivery records in discovery, Pause and the dashboard. An unfinished record still offers Resume. Close must preserve a different active owner’s handoff, gates and focus, including on refusal and retry. Test the registered entry points and document the sequence.

2026-11-21: Registered lifecycle and dashboard tests distinguish reviewed and interrupted deliveries, and preserve another owner’s handoff, focus and gates on refused, successful and repeated close. The first full run identified five test failures. The repaired tree passed 13,193 tests across 253 files, with 12 skips. Full docs validation passed.

## Decision Log

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-11-21 | Reuse paused and derive the next action. | Delivery evidence already distinguishes operator closure from interrupted work. |

## Risks

Existing legacy or damaged records may lack verifiable delivery evidence. Give those records the ordinary paused route. Keep evidence reads scoped to paused candidates.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
