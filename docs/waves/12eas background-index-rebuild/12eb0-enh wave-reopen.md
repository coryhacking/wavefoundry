# Wave Reopen MCP Tool

Change ID: `12eb0-enh wave-reopen`
Change Status: `done`
Owner: Engineering
Status: done
Last verified: 2026-05-06
Wave: `12eas background-index-rebuild`

## Rationale

When a wave is closed prematurely (e.g., by mistake), there is no MCP tool to reopen it — the operator must manually edit `wave.md` and understand the internal state format. A `wave_reopen` MCP tool makes recovery a single, safe, idempotent call.

## Requirements

1. `wave_reopen(wave_id)` must set the wave `Status` back to `active` in `wave.md`.
2. If the wave record contains a `Completed At` stamp added by `wave_close`, it must be removed.
3. The tool must return an error if the wave is not currently in `closed` status.
4. The tool must return the updated wave state on success.

## Scope

**Problem statement:** Closed waves cannot be reopened without manual file edits.

**In scope:**

- New `wave_reopen` MCP tool in `server.py`
- Removing `Completed At` from the wave record on reopen
- Resetting `Status: closed` → `Status: active`

**Out of scope:**

- Reopening individual changes within a wave
- Audit trail / closure history preservation

## Acceptance Criteria

- AC-1: `wave_reopen(wave_id)` on a closed wave sets `Status: active` in `wave.md`.
- AC-2: Any `Completed At` line in `## Changes` is removed on reopen.
- AC-3: `wave_reopen` on a non-closed wave returns `status: error` with a clear message.
- AC-4: `wave_reopen` on a non-existent wave returns `status: error`.
- AC-5: `wave_review` passes after a reopen.

## Tasks

- [x] Add `wave_reopen` handler in `server.py` (reads wave.md, validates status=closed, rewrites with status=active, strips `Completed At`)
- [x] Register `wave_reopen` as an MCP tool with `wave_id` parameter
- [x] Add tests in `test_server_tools.py`: success path, already-active error, not-found error
- [x] Update `docs/prompts/index.md` with `wave_reopen` entry

## Agent Execution Graph

| Workstream   | Owner         | Depends On | Notes |
| ------------ | ------------- | ---------- | ----- |
| server impl  | implementer   | —          |       |
| tests        | implementer   | server impl |      |
| docs update  | implementer   | server impl |      |

## Serialization Points

- `server.py` is shared with other wave tool changes; coordinate with any concurrent framework edits.

## Affected Architecture Docs

N/A — confined to MCP tool surface with no boundary or data-flow impact.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Core behavior — reopen must restore active status correctly |
| AC-2 | required  | Completed At stamp makes the wave record malformed if left in place |
| AC-3 | required  | Non-closed wave must fail clearly to prevent accidental state clobber |
| AC-4 | required  | Non-existent wave must fail clearly |
| AC-5 | important | wave_review passing post-reopen confirms the restored state is valid |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Reopening a wave that was intentionally closed could confuse the journal | Tool only operates on `closed` status; operator intent is explicit |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
