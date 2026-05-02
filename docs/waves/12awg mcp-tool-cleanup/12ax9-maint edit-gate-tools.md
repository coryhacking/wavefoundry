# Edit Gate MCP Tools and Auto-Close

Change ID: `12ax9-maint edit-gate-tools`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-01
Wave: `12awg mcp-tool-cleanup`

## Rationale

The `seed_edit_allowed` and `framework_edit_allowed` guards in `.wavefoundry/guard-overrides.json` are currently managed by direct JSON edits. This is fragile: the guard can be left open across session boundaries (as happened during wave `12ahv` — the `seed_edit_allowed` gate was left open after 12aj7 seed edits and only caught during AC review). There is no MCP-visible operation for opening or closing a gate, no diagnostic when a gate is open at a wave boundary, and no automatic enforcement at natural stopping points.

Two complementary mechanisms fix this:

1. **Dedicated gate tools** — `wave_open_gate` / `wave_close_gate` replace direct JSON edits with a discoverable, self-documenting MCP interface. Tool descriptions carry the open-must-pair-with-close contract that JSON edits cannot express.
2. **Automatic gate close at wave boundaries** — `wave_pause` and `wave_close` force both gates closed before the wave boundary is recorded, with an advisory diagnostic if either gate was open when called.

A companion CLI script gives operators the same control outside MCP sessions, consistent with the `bin/` wrapper pattern.

## Requirements

1. **`wave_open_gate(gate)`** sets the named guard to `enabled: true` in `.wavefoundry/guard-overrides.json`. Returns an error if the gate is already open (prevents silent double-opens). Valid gate names: `seed_edit_allowed`, `framework_edit_allowed`.
2. **`wave_close_gate(gate)`** sets the named guard to `enabled: false`. Returns an advisory (not an error) if the gate was already closed.
3. Both tools are annotated as mutating (`readOnlyHint: false`, `destructiveHint: false`, `idempotentHint: false`).
4. **`wave_pause`** reads the current gate states before writing the pause record; if either gate is open, forces both closed and includes a `diagnostics` entry with `code: "gates_forced_closed"` naming which gates were open.
5. **`wave_close`** (dry-run and create modes) applies the same gate-close-and-warn logic as `wave_pause`, but only forces the close in create mode — dry-run emits the diagnostic without writing.
6. **`.wavefoundry/bin/gate`** CLI script: `gate open <gate-name>` and `gate close <gate-name>` with the same validation (error on double-open, advisory on double-close). Prints the gate state after the operation.
7. Tests cover: open a closed gate (ok), open an already-open gate (error), close an open gate (ok), close an already-closed gate (advisory), `wave_pause` with open gate (forced close + diagnostic), `wave_close` dry-run with open gate (diagnostic only, no write), `wave_close` create with open gate (forced close + diagnostic).
8. `AGENTS.md` documents `wave_open_gate` / `wave_close_gate` and notes that `wave_pause` / `wave_close` auto-close both gates.
9. All existing direct-JSON-edit instructions in `AGENTS.md` and `CLAUDE.md` are updated to reference the new tools instead.

## Scope

**Problem statement:** The edit guard mechanism is a raw JSON file with no MCP surface, no enforcement at wave boundaries, and no protection against gates being left open across sessions.

**In scope:**

- `wave_open_gate` and `wave_close_gate` tool registrations and handlers in `server.py`
- Gate auto-close logic in `wave_pause` and `wave_close` handlers
- `.wavefoundry/bin/gate` CLI script
- Tests for all new behaviors
- `AGENTS.md` and `CLAUDE.md` updates replacing direct-JSON instructions with tool references

**Out of scope:**

- Time-based or session-scoped auto-expiry of gates (deferred; advisory diagnostic at boundary is sufficient for now)
- Gate history or audit log (deferred)
- Adding additional gate types beyond `seed_edit_allowed` and `framework_edit_allowed`
- Changing what the gates actually protect (scope of allowed edits is unchanged)

## Acceptance Criteria

- AC-1: `wave_open_gate(gate="seed_edit_allowed")` sets the guard to `enabled: true` and returns `status: "ok"`.
- AC-2: Calling `wave_open_gate` when the gate is already open returns `status: "error"` with a clear message.
- AC-3: `wave_close_gate(gate="seed_edit_allowed")` sets the guard to `enabled: false` and returns `status: "ok"`.
- AC-4: Calling `wave_close_gate` when the gate is already closed returns `status: "ok"` with an advisory diagnostic (not an error).
- AC-5: Both tools work identically for `gate="framework_edit_allowed"`.
- AC-6: `wave_pause` with an open gate forces the gate(s) closed and includes a `gates_forced_closed` diagnostic naming which gates were open.
- AC-7: `wave_close` in dry-run mode with an open gate emits a `gates_forced_closed` diagnostic but does not write the gate file.
- AC-8: `wave_close` in create mode with an open gate forces the gate(s) closed and includes a `gates_forced_closed` diagnostic.
- AC-9: After `wave_pause` or `wave_close` (create), both gates are `enabled: false` regardless of prior state.
- AC-10: `.wavefoundry/bin/gate open seed_edit_allowed` and `.wavefoundry/bin/gate close seed_edit_allowed` work correctly.
- AC-11: `python3 .wavefoundry/framework/scripts/run_tests.py` passes.
- AC-12: `.wavefoundry/bin/docs-lint` is clean.
- AC-13: `AGENTS.md` and `CLAUDE.md` reference `wave_open_gate` / `wave_close_gate` instead of direct JSON edits.

## Tasks

- In `server.py`: add `wave_open_gate` and `wave_close_gate` handlers with guard-overrides read/write and error/advisory logic.
- In `server.py`: extract a `_force_gates_closed(mode)` helper that reads current gate state, closes any open gates, and returns a diagnostic list; wire it into `wave_pause_response` and `wave_close_response`.
- Add `.wavefoundry/bin/gate` script with `open` / `close` subcommands.
- Add tests for all AC-1 through AC-10 behaviors in `test_server_tools.py`.
- Update `AGENTS.md`: document `wave_open_gate` / `wave_close_gate`; note auto-close on pause/close; replace direct JSON edit instructions.
- Update `CLAUDE.md` Key Guardrails section to reference `wave_open_gate` / `wave_close_gate` instead of direct JSON edit. (Requires `framework_edit_allowed` guard open; restore immediately after.)
- Run tests and docs-lint.

## Agent Execution Graph

| Workstream        | Owner       | Depends On        | Notes                                                          |
| ----------------- | ----------- | ----------------- | -------------------------------------------------------------- |
| server-gate-tools | implementer | —                 | `wave_open_gate`, `wave_close_gate`, `_force_gates_closed` helper |
| server-boundary   | implementer | server-gate-tools | Wire `_force_gates_closed` into `wave_pause` and `wave_close`  |
| bin-script        | implementer | server-gate-tools | `bin/gate` wraps same guard-overrides logic                    |
| tests             | implementer | server-boundary, bin-script | Cover all AC-1 through AC-10 behaviors               |
| docs              | implementer | server-gate-tools | AGENTS.md and CLAUDE.md updates                                |

## Serialization Points

- `_force_gates_closed()` helper should land before `wave_pause` and `wave_close` wiring.
- `CLAUDE.md` edit requires `framework_edit_allowed` guard open; this is the last use of the old JSON pattern — restore immediately after.

## Affected Architecture Docs

- `docs/architecture/current-state.md` — add `wave_open_gate` / `wave_close_gate` to the MCP tool list; note gate auto-close at wave boundaries.
- No other architecture docs require changes; this is an additive safety mechanism with no new domain boundaries.

## AC Priority

(Populated at Prepare wave.)

| AC    | Priority       | Rationale |
| ----- | -------------- | --------- |
| AC-1  | required       | Core deliverable — open gate must succeed |
| AC-2  | required       | Double-open guard is the safety property; without it a forgotten open is undetectable |
| AC-3  | required       | Core deliverable — close gate must succeed |
| AC-4  | required       | Advisory-only on double-close; blocking would make cleanup harder |
| AC-5  | required       | Both gates must be covered; `framework_edit_allowed` is equally important |
| AC-6  | required       | Auto-close on pause is the primary safety net for gate-left-open incidents |
| AC-7  | required       | dry-run must remain read-only — gate write in dry-run would be a contract violation |
| AC-8  | required       | Auto-close on wave_close (create) completes the boundary enforcement |
| AC-9  | required       | Both gates must be closed after any wave boundary; partial close is a bug |
| AC-10 | required       | CLI script gives operators gate control outside MCP sessions |
| AC-11 | required       | Tests are the verification gate |
| AC-12 | required       | docs-lint is the docs verification gate |
| AC-13 | required       | AGENTS.md and CLAUDE.md are the primary operator and agent references |

## Progress Log

| Date       | Update         | Evidence |
| ---------- | -------------- | -------- |
| 2026-05-01 | Change doc authored. Gate-left-open incident during 12ahv confirmed as motivation. | 12aj7 AC-8 violation found during 12ahv wave review |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-01 | Auto-close at `wave_pause` / `wave_close` rather than hard-blocking | Hard block would prevent closing a wave if an operator forgot to close the gate; advisory + force-close is safer and less disruptive | Hard block (deferred — can promote if the advisory is repeatedly ignored) |
| 2026-05-01 | Error on double-open, advisory on double-close | Double-open likely means a bug (two concurrent edit windows); double-close is harmless and common during cleanup | Advisory on both (rejected: masks double-open bugs) |
| 2026-05-01 | dry-run mode for `wave_close` emits diagnostic but does not write gate file | dry-run must remain fully read-only; gate state write would be a side effect inconsistent with dry-run semantics | Force-close in dry-run too (rejected: violates dry-run contract) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| `CLAUDE.md` edit requires the old JSON gate pattern one last time | Document explicitly in task; restore guard immediately after the single edit |
| `_force_gates_closed` called in dry-run mode accidentally writes | Pass `mode` parameter through; assert no file write when `mode == "dry_run"` in tests |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
