# Index Build Status MCP Tool

Change ID: `12ebh-enh wave-index-build-status`
Change Status: `done`
Owner: Engineering
Status: done
Last verified: 2026-05-06
Wave: `12eas background-index-rebuild`

## Rationale

After `wave_index_build` spawns a background rebuild, there is no dedicated way to check whether it is still running or has finished. The operator or agent must either wait and ask, or tail the log file manually. A `wave_index_build_status` tool provides an unambiguous, purpose-built status query — safe to call at any time, from `/loop` polling or a one-shot check, without cluttering unrelated response contexts.

## Requirements

1. `wave_index_build_status(layer)` must return the current state of the index build for the given layer (`project` or `framework`).
2. When a build is **running**: return `state: "running"`, `pid`, `started_at`, elapsed seconds, and the last non-empty line of the log file as `progress`.
3. When a build has **finished** (process exited, state file present): return `state: "finished"`, `started_at`, `finished_at` (mtime of state file or detected from log), elapsed seconds, and a summary parsed from the log (files indexed, doc chunks, code chunks).
4. When **no build has been run** (no state file): return `state: "idle"`.
5. The tool must default `layer` to `"project"`.
6. The tool must not modify any files or trigger any side effects.

## Scope

**Problem statement:** No way to check background index rebuild progress without manually tailing the log.

**In scope:**

- New `wave_index_build_status` MCP tool in `server.py`
- State detection via the existing `index-build.json` state file and `index-build.log`
- Log tail parsing for progress line (running) and completion summary (finished)
- `/loop` usage guidance in `docs/prompts/index.md`

**Out of scope:**

- Modifying the state file format (read-only tool)
- Surfacing status on unrelated MCP calls (e.g., `wave_review`)
- Multi-layer status in a single call

## Acceptance Criteria

- AC-1: `wave_index_build_status()` returns `state: "running"` with `pid`, `elapsed_seconds`, and `progress` while a build is active.
- AC-2: `wave_index_build_status()` returns `state: "finished"` with elapsed time and log-parsed summary (files, doc_chunks, code_chunks) after a build completes.
- AC-3: `wave_index_build_status()` returns `state: "idle"` when no state file exists.
- AC-4: The tool is read-only — calling it never writes files or spawns processes.
- AC-5: `wave_index_build_status(layer="framework")` returns status for the framework layer.
- AC-6: `docs/prompts/index.md` documents `wave_index_build_status` and notes it is suitable for `/loop` polling.

## Tasks

- [x] Add `wave_index_build_status_response(root, layer)` in `server.py`: read state file, check PID, tail log, parse completion summary
- [x] Register `wave_index_build_status` as a read-only MCP tool with optional `layer` parameter
- [x] Add log-tail parser: extract last progress line for running state; extract `files indexed`, `doc chunks`, `code chunks` from `"done —"` line for finished state
- [x] Add tests: running state, finished state, idle state, framework layer
- [x] Update `docs/prompts/index.md` with `wave_index_build_status` entry and `/loop` polling note

## Agent Execution Graph

| Workstream  | Owner       | Depends On | Notes |
| ----------- | ----------- | ---------- | ----- |
| server impl | implementer | —          |       |
| tests       | implementer | server impl |      |
| docs update | implementer | server impl |      |

## Serialization Points

- `server.py` shared with other wave tool changes in this wave; coordinate edits.

## Affected Architecture Docs

N/A — confined to MCP tool surface; read-only query against existing state files.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required / important / nice-to-have / not-this-scope |           |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-06 | Dedicated tool rather than surfacing on existing calls | Avoids confusing agents that receive unexpected completion notices in unrelated responses | Piggyback on wave_index_health; poll in background |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| State file or log absent after a crash | Tool returns `idle` on any missing/unparseable state — safe no-op |
| Log format changes break parser | Parser is defensive; falls back to raw last-line if summary pattern not found |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
