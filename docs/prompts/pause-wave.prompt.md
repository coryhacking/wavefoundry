# Pause Wave

Owner: Engineering
Status: active
Last verified: 2026-05-19

Shortcut: **`Pause wave`**

## Purpose

Park current session state and transition the wave to `paused` when work must be interrupted. Enables safe resumption in a new session and frees the active slot so another wave can be prepared.

## Steps

1. Run `wave_pause(wave_id=..., mode='create')`. This:
   - Transitions wave.md `Status: active` → `Status: paused` (idempotent on already-paused; advisory diagnostic when the wave is not active).
   - Writes a session-handoff entry to `docs/agents/session-handoff.md`.
   - Returns `data.status_transition: {"from": ..., "to": ...}` so you can see what changed.
2. Update `docs/agents/session-handoff.md` with a standardized structure beyond what `wave_pause` recorded. Use these labeled sections:
   - **Done** — changes/tasks completed this session
   - **Next** — ordered next actions
   - **Files touched** — key files modified
   - **Test state** — passing/failing/untested at pause time
   - **Open questions / Deferred decisions** — unresolved intent that doesn't belong in a change doc but must survive the context reset
   - Blockers (if any)
3. Update wave record progress log with current state.
4. Commit the handoff artifact (operator-owned commit).

## Dry-Run Preview

`wave_pause(..., mode='dry_run')` reports the intended `status_transition` without writing anything. Use this to preview the effect before committing.

## Status Transition Semantics

| Current status | After `wave_pause(mode='create')` | Handoff written? | Diagnostic                      |
| -------------- | --------------------------------- | ---------------- | ------------------------------- |
| `active`       | `paused`                          | yes              | none                            |
| `paused`       | `paused` (no-op)                  | yes              | none                            |
| `planned` / other | unchanged                      | yes              | `pause_on_non_active_wave` (advisory) |

## Resume Instructions

At next session start, read `docs/agents/session-handoff.md` and the wave record at `docs/waves/<wave-id>/wave.md` before taking any action. To transition the paused wave back to `active`, run `wave_prepare(wave_id=..., mode='create')` on it. The single-active-wave guard in `wave_prepare` will block this if any other wave is currently `active`; pause that one first.

## Paused Waves in `wave_current`

`wave_current` returns paused waves in its `data.waves[]` response alongside active and planned waves. Paused entries carry `next_action: "resume_wave"` — a hint that maps to calling `wave_prepare` on that wave.

## What Belongs in Handoff vs Journals

- **Session handoff:** active blockers, next actions, temporary working-memory state
- **Journals:** lessons, constraints, observations that survive beyond the current session
- **Wave record:** coordination truth, admitted changes, review checkpoints
