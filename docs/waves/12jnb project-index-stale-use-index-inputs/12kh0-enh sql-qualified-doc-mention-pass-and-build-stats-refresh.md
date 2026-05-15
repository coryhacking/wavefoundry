# SQL Qualified Doc/Mention Pass and Build Stats Refresh

Change ID: `12kh0-enh sql-qualified-doc-mention-pass-and-build-stats-refresh`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The SQL follow-up tests showed two remaining issues that are worth solving together:

1. Schema-qualified SQL lookups should stay precise for structural navigation, but docs and plain mentions should still be found when they only reference the bare object name.
2. `wave_index_health` should surface the most recent finished MCP-triggered build stats instead of perpetually reporting the last CLI build snapshot.

This change keeps the SQL navigation signal split by intent and refreshes build stats when the latest rebuild has completed.

## Requirements

1. Schema-qualified SQL object names should continue to resolve structurally, with the qualified form retained in chunk names where available.
2. `code_references` should merge doc and mention hits from the schema-stripped SQL symbol when the qualified form is used, without broadening call-site filtering.
3. `wave_index_health` should refresh `previous_build_stats` from the latest finished build so MCP-triggered rebuilds are reflected without a restart.
4. Existing broad navigation and build-status behavior should remain intact for other languages and for SQL call-site searches.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/tests/test_chunker.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`

**Out of scope:**

- Changing SQL alias routing
- Changing the index file format
- Changing dashboard rendering or wave lifecycle behavior

## Acceptance Criteria

- Schema-qualified SQL definitions continue to resolve structurally, and the qualified chunk name is preserved when a schema prefix exists.
- Qualified SQL reference searches retain structural call-site precision while also surfacing doc and mention hits from the bare symbol.
- `wave_index_health` reports current `previous_build_stats` after a finished MCP-triggered rebuild without requiring a restart.
- Regression tests cover the qualified SQL doc/mention merge and the refreshed build-stats behavior.

## Tasks

- Emit schema-qualified SQL chunk names when a schema prefix is present
- Merge unqualified SQL doc/mention matches into qualified reference searches
- Refresh build stats from finished MCP rebuilds before reporting index health
- Add regressions for the qualified SQL and build-stats behaviors

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Qualified SQL chunks should stay structurally precise |
| AC-2 | required | Docs and mentions should remain discoverable via the bare symbol |
| AC-3 | required | Health output should reflect the latest finished MCP rebuild |
| AC-4 | required | Existing search and build-status behavior must remain stable |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Qualified chunk names reduce compatibility with older bare-name expectations | Keep structural matching tolerant of both qualified and bare forms |
| Broadening docs/mentions could introduce extra noise | Restrict the unqualified merge to doc/mention buckets only |
| Stats refresh could race a still-running build | Only refresh from a finished log state, never while the build is active |
