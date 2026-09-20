# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-09-20

## Current Session

**Active wave:** *(none)*
**Last closed wave:** `1yj14 index-build-write-races`

Shipped shared server/build source exclusion, bounded fresh retry, verified historical-snapshot restoration, truthful optimize failures, and reload coverage. Wave closed on 2026-09-20 after all review findings were repaired and independently verified. Current framework receipt: 9,409 tests/113 files, 12 skips; docs validation passed. No commit made.

Memory checkpoint completed through a fresh stdio MCP process. Two malformed temporary-target candidates were explicitly rejected; their verified testing lessons are preserved in `docs/references/project-context-memory.md`.

## Open questions / Deferred decisions

- Loaded MCP code may be stale after these edits; restart the host before relying on new server/index behavior. Tests use fresh processes. No destructive production-index recovery is part of this wave.
- Crash, uncertain publication COMMIT and postcommit recovery remain fail-closed. Historical snapshot availability is explicitly distinct from current-source freshness.
- `1y0h2 handler-module-split` remains readied and unopened; `1y0h1 tool-registry-dispatch` and `1yja8 stable-storage-identity` are closed. Preserve their uncommitted changes.
- Previous storage fix's replacement-volume/reused-inode limitation remains accepted; no restamping.

### Notes for the next session

- Leave `docs/waves/1ycrj task-fit-agent-model-policy/` and `docs/waves/1yfzu readiness-convergence/` alone; another session owns them.
- Use `/Users/coryhacking/.wavefoundry/venv/bin/python -B` for framework tests; system Python lacks MCP. The full runner needs host process visibility for dashboard lifecycle tests.
- Framework edit gate is closed.
