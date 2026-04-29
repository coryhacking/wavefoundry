# Pause Wave

Owner: Engineering
Status: active
Last verified: 2026-04-28

Shortcut: **`Pause wave`**

## Purpose

Park current session state in `docs/agents/session-handoff.md` when work must be interrupted. Enables safe resumption in a new session.

## Steps

1. Update `docs/agents/session-handoff.md`:
   - Current session date
   - Active wave ID and change ID
   - Last completed action
   - Next actions (ordered)
   - Blockers (if any)
   - Working-memory notes that would be lost by compaction
2. Update wave record progress log with current state.
3. Commit the handoff artifact (operator-owned commit).

## Resume Instructions

At next session start, read `docs/agents/session-handoff.md` and the wave record at `docs/waves/<wave-id>/wave.md` before taking any action.

## What Belongs in Handoff vs Journals

- **Session handoff:** active blockers, next actions, temporary working-memory state
- **Journals:** lessons, constraints, observations that survive beyond the current session
- **Wave record:** coordination truth, admitted changes, review checkpoints
