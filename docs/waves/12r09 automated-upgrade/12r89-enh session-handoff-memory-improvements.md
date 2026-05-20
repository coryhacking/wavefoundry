# Session Handoff and Auto-Memory Improvements

Change ID: `12r89-enh session-handoff-memory-improvements`
Change Status: `implemented`
Owner: wave-coordinator
Status: implemented
Last verified: 2026-05-19
Wave: 12r09 automated-upgrade

## Rationale

Session handoff and auto-memory are underutilized as knowledge-persistence mechanisms. The handoff file is nearly empty at idle (just "No active wave remains"), losing recent history between sessions. The memory index has only 3 entries despite significant project work — it only captures corrections, not validated approaches. There is no structured prompt to capture learnings at wave-close time, which is the most natural knowledge-capture moment in the workflow.

## Requirements

1. The idle session handoff must include the last closed wave ID and a one-line summary of what it shipped, so a fresh session has recent history without running `wave_list_waves`.
2. The session handoff must include a **Open Questions / Deferred Decisions** section for recording intent that doesn't belong in a change doc.
3. The `wave_pause` handoff structure must be standardized: what's done, what's next, files touched, test state, open questions.
4. The auto-memory system must capture positive confirmations (validated approaches) in addition to corrections — not only save when something went wrong.
5. The wave-close workflow must include a lightweight retrospective prompt: "what was non-obvious that a future session should know?" — any answer feeds into auto-memory.
6. Architectural decisions made during a wave (why an approach was chosen) must be captured in auto-memory when they are non-obvious and not recoverable from git history.

## Scope

**Problem statement:** Session handoff and auto-memory lose useful context at two key moments — when a wave closes (no retrospective step) and between sessions when idle (handoff is nearly empty). The memory index skews toward corrections only, missing validated patterns that should carry forward.

**In scope:**

- Update the `pause-wave` seed prompt to emit a standardized handoff structure (done / next / files / test state / open questions)
- Update the `close-wave` seed prompt to include a retrospective prompt that surfaces memory candidates
- Update agent guidance (`docs/agents/session-handoff.md` template, AGENTS.md startup notes) to document the richer idle handoff format
- Add guidance to auto-memory instructions to capture positive confirmations, not just corrections
- Add architectural-decision memory as a recognized memory category to capture during wave close

**Out of scope:**

- MCP tooling changes to `wave_set_handoff` / `wave_get_handoff` (format is free-text; no schema change needed)
- Automated memory writing — retrospective remains human-confirmed, not agent-autonomous
- Changes to the memory file structure or MEMORY.md format

## Acceptance Criteria

- AC-1: The `pause-wave` prompt produces a handoff with clearly labeled sections for: done, next, files touched, test state, and open questions.
- AC-2: The `close-wave` prompt includes a retrospective step that asks for non-obvious learnings and explicitly prompts the agent to write memory candidates.
- AC-3: The idle session handoff format documented in agent guidance includes last-closed-wave summary and open questions sections.
- AC-4: Auto-memory guidance explicitly calls out capturing positive confirmations (validated approaches) with the same priority as corrections.
- AC-5: After wave close on this project, at least one architectural-decision memory entry exists that would not have been written under the old guidance.

## Tasks

- Update `pause-wave` seed prompt with standardized handoff structure
- Update `close-wave` seed prompt with retrospective + memory-candidate step
- Update `docs/agents/session-handoff.md` to document the richer idle format
- Update auto-memory guidance (AGENTS.md or memory system instructions) to emphasize positive confirmations and architectural decisions
- Write any memory entries that emerge from closing this wave as a concrete demonstration

## Agent Execution Graph


| Workstream          | Owner            | Depends On | Notes |
| ------------------- | ---------------- | ---------- | ----- |
| seed-prompt updates | wave-coordinator | —          | pause-wave and close-wave seeds |
| agent-guidance docs | wave-coordinator | —          | session-handoff.md, AGENTS.md memory section |
| retrospective demo  | wave-coordinator | seed-prompt updates | write memory entries when closing this wave |


## Serialization Points

- Seed edits require `seed_edit_allowed` gate open/close per edit session

## Affected Architecture Docs

N/A — change is confined to seed prompts and agent guidance docs with no impact on framework boundaries, data flow, or verification architecture.

## AC Priority


| AC   | Priority     | Rationale |
| ---- | ------------ | --------- |
| AC-1 | required     | Core deliverable — standardized pause handoff is the primary fix for context loss between sessions |
| AC-2 | required     | Core deliverable — close-wave retrospective is the primary knowledge-capture improvement |
| AC-3 | required     | Idle handoff format closes the gap where fresh sessions have no recent history |
| AC-4 | important    | Positive-confirmation memory prevents skew toward avoidance-only; high value but not a gate |
| AC-5 | nice-to-have | Demonstrates the retrospective in practice; useful validation but not a gate for the seed changes |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-19 | All deliverables confirmed complete: pause-wave standardized sections, close-wave retrospective step (#8) and idle handoff format (#9), project-context-memory.md auto-memory categories (architectural decisions + validated approaches). Status updated to implemented. | close-wave.prompt.md, pause-wave.prompt.md, project-context-memory.md, session-handoff.md |


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