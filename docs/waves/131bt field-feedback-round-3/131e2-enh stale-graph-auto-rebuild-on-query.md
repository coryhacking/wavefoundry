# Synchronously Rebuild Stale Graph on First Query After `GRAPH_BUILDER_VERSION` Bump

Change ID: `131e2-enh stale-graph-auto-rebuild-on-query`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 131bt field-feedback-round-3

## Rationale

When `GRAPH_BUILDER_VERSION` bumps (this wave: 14 → 15 from `1319s`), repositories with the dashboard's `auto_index: true` enabled rebuild the graph automatically the next time the dashboard sees a file change (per the existing `_build_graph_artifacts` always-runs + `_load_state` version-mismatch + fresh-state-expansion chain). But repositories that:

- Don't run the dashboard, OR
- Run it with `auto_index: false`, OR
- Don't trigger a file change before querying the graph (e.g., an agent runs `code_callhierarchy` immediately after upgrade)

continue to see stale graph results — `code_callhierarchy`, `code_impact`, `code_graph_path`, `code_graph_community`, and `wave_graph_report` all read the on-disk graph payload without triggering a rebuild.

This change adds a synchronous rebuild on the first query that loads the graph after a `builder_version` mismatch is detected. One ~10 s wait per upgrade; subsequent queries are instant and accurate.

## Approach

In `graph_query.py`, the `GraphQueryIndex.from_root()` / equivalent loader reads the persisted graph payload. Add a version check immediately after loading:

1. Read the graph state file (`<index_dir>/graph/<layer>-graph-state.json`).
2. Compare `state.builder_version` against the runtime `graph_indexer.GRAPH_BUILDER_VERSION`.
3. If mismatched, synchronously invoke `graph_indexer.update_graph_index(...)` with the full project file set as `changed`. The existing fresh-state-expansion logic handles the "rebuild from scratch" case naturally.
4. After rebuild completes, re-load the payload and continue.
5. Emit a structured diagnostic on the response carrying `auto_rebuild_triggered: true` + the from/to versions so operators can see the rebuild fired.

The check is layered behind a cache: re-checking on every query would be wasteful. Track the last-checked builder_version per layer in process memory; only re-check when the on-disk state file's mtime changes.

When the rebuild fails (e.g., source files moved, partial repo), surface a structured error with `recovery_tools: ["wave_index_build"]` and let the query return stale results with a clear diagnostic — the operator can investigate and run a manual rebuild.

## Requirements

1. `graph_query.py` loader checks `state.builder_version` on graph load.
2. On mismatch, synchronously rebuilds the graph via `graph_indexer.update_graph_index(...)` with the full file set.
3. After rebuild, re-loads the payload — query proceeds against the fresh graph.
4. Response includes a structured diagnostic identifying the auto-rebuild event (from/to builder versions, rebuild duration).
5. Per-layer in-process cache prevents redundant version checks within a single MCP session.
6. Rebuild failure surfaces a structured error diagnostic with `recovery_tools: ["wave_index_build"]` and `recovery_usage: "wave_index_build(content='graph', mode='rebuild')"`; stale results return with the diagnostic rather than throwing.
7. Compatible with the dashboard auto-index path — if the dashboard already rebuilt the graph, the version check passes and no second rebuild fires.

## Scope

**Problem statement:** Upgrades that bump `GRAPH_BUILDER_VERSION` only auto-rebuild the graph when the dashboard's auto-index is running. Repositories without the dashboard see stale results from `code_callhierarchy` / `code_impact` / `code_graph_*` / `wave_graph_report` until the operator manually runs `wave_index_build(content='graph')`. The manual-rebuild instruction in seed-160 covers operators going through the upgrade workflow, but agent-driven workflows that query the graph directly after upgrade don't see the instruction.

**In scope:**

- `.wavefoundry/framework/scripts/graph_query.py` — version-check + synchronous rebuild in `GraphQueryIndex.from_root()` (or equivalent loader entry point).
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` — regression test for the auto-rebuild path with a synthetic stale graph fixture.
- Diagnostic surface on `code_callhierarchy`, `code_impact`, `code_graph_path`, `code_graph_community`, `wave_graph_report` when the auto-rebuild fires.

**Out of scope:**

- Background async rebuild (Option 2 from the design discussion — rejected for hiding partial-staleness windows).
- Per-tool opt-out flags. The auto-rebuild is mandatory when the version mismatch is detected.
- Rebuilding when `walker_version` / `chunker_version` change. Those bumps fire less often and the existing dashboard path handles them.
- Bumping `GRAPH_BUILDER_VERSION` to test the rebuild — this change verifies behavior; the next graph-builder change does the bump.

## Acceptance Criteria

- [x] AC-1: When the on-disk graph state's `builder_version` differs from runtime `GRAPH_BUILDER_VERSION`, `GraphQueryIndex.from_root()` (or equivalent loader) synchronously rebuilds before returning.
- [x] AC-2: After auto-rebuild, the loaded payload reflects the new builder version; the persisted graph state file shows the matching version.
- [x] AC-3: A subsequent query (same process, same layer) does NOT re-trigger the rebuild — the version check uses an in-process cache keyed on state-file mtime.
- [x] AC-4: When the rebuild fails (`update_graph_index` raises), the loader returns the stale payload with a structured diagnostic `recovery_tools: ["wave_index_build"]` rather than crashing the query.
- [x] AC-5: The auto-rebuild diagnostic surfaces in the response from every graph-consumer tool (`code_callhierarchy`, `code_impact`, `code_callgraph`, `wave_graph_report`, `code_graph_path`, `code_graph_community`) as a structured `graph_auto_rebuilt` diagnostic with `from_builder_version`, `to_builder_version`, and `rebuild_duration_ms`. Plumbed via `GraphQueryIndex.auto_rebuild_diagnostic` slot + `_attach_auto_rebuild_diag` envelope wrapper.
- [x] AC-6: When the dashboard auto-index has already rebuilt the graph (state matches runtime), no second rebuild fires.
- [x] AC-7: Regression test simulates a stale graph (write a state file with an older `builder_version`), invokes a graph-reading tool, and verifies the rebuild fired.
- [x] AC-8: All existing 2143 tests pass without modification.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add version-check + synchronous rebuild in `graph_query.py` `GraphQueryIndex.from_root()`
- [x] Add per-process state-file mtime cache to skip redundant checks
- [x] Add structured diagnostic surface
- [x] Add regression test for stale-graph auto-rebuild
- [x] Add regression test for already-fresh graph (no-op)
- [x] Run framework tests
- [x] Close gate; mark change `implemented`

## Affected Architecture Docs

- N/A — this change strengthens the upgrade lifecycle without changing the architecture. `wave_index_health` already surfaces graph staleness for explicit checks; this change adds the implicit safety net.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Core trigger |
| AC-2 | required | Correctness of rebuild outcome |
| AC-3 | required | Performance — avoid rebuild-per-query overhead |
| AC-4 | required | Graceful degradation when rebuild fails |
| AC-5 | required | Operator-facing visibility into the rebuild |
| AC-6 | required | No-double-rebuild when dashboard already handled it |
| AC-7 | required | Stale-graph fixture coverage |
| AC-8 | required | No baseline regression |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Synchronous rebuild on first query (~10 s once per upgrade) | Once-per-upgrade wait is unambiguously attributable to the upgrade; subsequent queries are instant and accurate. Avoids partial-stale results during background rebuild | Background rebuild + serve stale (rejected — hides partial-staleness windows that earlier waves explicitly added diagnostics to surface); diagnostic-only (rejected — requires operator action, doesn't help agent-driven workflows) |
| 2026-06-01 | Per-process mtime cache to avoid re-checking the version on every query | Loading the state file on every query adds measurable overhead; checking only when the state file changes (rebuild happened externally) is enough | Check every query (rejected — wasteful); long TTL cache (rejected — could miss external rebuilds longer than necessary) |
| 2026-06-01 | Surface the auto-rebuild in tool responses via diagnostic, not a separate notification | Operators see the rebuild fired in the response of the tool that triggered it; consistent with the existing diagnostic pattern (`recovery_tools` / `recovery_usage`) | Side-channel notification (rejected — operators query tools, not subscriptions) |
| 2026-06-01 | Stale results returned with diagnostic when rebuild fails, not query error | Hard error would break agent-driven workflows on transient rebuild failures; structured diagnostic lets the agent see what happened and try `wave_index_build` manually | Hard error on rebuild failure (rejected — too brittle for agent workflows) |

## Risks

| Risk | Mitigation |
|---|---|
| First query after upgrade takes 10–30 s — could surprise operators expecting fast graph queries | Diagnostic surfaces the from/to version + duration so operators understand why; once-per-upgrade. The semantic-vs-graph callout in `131ar`'s description sync sets the expectation that graph operations may rebuild |
| Concurrent queries during the rebuild window could trigger duplicate rebuilds | Use a process-level lock (similar to the dashboard's IndexBuilder pattern) so concurrent stale-detections share a single rebuild |
| Rebuild fails because source files moved or the repo is in a partial state | AC-4 — surface structured diagnostic; query returns stale results; operator runs `wave_index_build` manually after fixing the underlying issue |
| `update_graph_index` imports are heavy; loading them at query time adds startup cost | Lazy import inside the version-mismatch branch — only loaded when actually needed |
| Test repos in CI may have stale `builder_version` after pulling a new framework, triggering unexpected rebuilds | Tests run against synthetic graphs; the rebuild path is invoked deliberately in a controlled fixture |

## Related Work

- Directly addresses the gap identified during wave 131bt close-out: dashboard auto-index covers most repos, but operator-direct query paths leave stale graphs unrefreshed.
- Companion to `1316n` (graph rebuild discoverability) — `1316n` surfaces staleness; this change resolves it automatically.
- Companion to `131d8` (MCP reload re-registers tool schemas) — both are upgrade-lifecycle safety nets eliminating manual ceremony.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
