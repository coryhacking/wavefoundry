# MCP Protocol Surface Phase 1b + Phase 2 — Progress Notifications and Prompt/Completion Experiments

Change ID: `1p310-enh mcp-protocol-surface-phase-1b-2`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-03
Wave: TBD (UX-polish wave, follow-on to 1p2q3 field-feedback-round-4)

## Rationale

Continuation of `1p2q3/131hh-enh mcp-protocol-surface-opportunities`. The parent change shipped Phase 1a (`session.send_resource_updated` after every graph rebuild path) and explicitly deferred Phase 1b and Phase 2 with reasons:

- **Phase 1b (`ctx.report_progress` checkpoints):** deferred because surfacing progress requires threading a `Context` parameter through every rebuild-triggering tool handler. The surface-area of that wiring was too large to bundle with Phase 1a's fire-and-forget pattern.
- **Phase 2 (`@mcp.prompt()` + `@mcp.completion()` experiments):** held back behind a host-behavior verification gate. Before committing to a full migration of `docs/prompts/*.md` to the `@mcp.prompt()` primitive or to a `@mcp.completion()` surface across tools with completable arguments, we need to verify whether the host (Claude Code, Cursor, Codex) actually surfaces these primitives in its UI. The parent doc captured the open question explicitly and gated the full migration on a one-tool pilot.

This change picks up that work. The bar to clear is small: implement Phase 1b's progress wiring once, and ship the Phase 2 pilots behind a documented experimental flag with a Decision Log entry recording the host-behavior result.

## Requirements

1. The graph auto-rebuild path emits at least three `ctx.report_progress` checkpoints (parse phase, edge-resolution phase, cluster phase) when invoked inside a tool-handler context with a `Context` parameter wired.
2. `wave_index_build(mode='rebuild')` inline path emits `ctx.report_progress` checkpoints during the embedding-rebuild phase.
3. Phase 2 experiment: one `@mcp.prompt()` registration AND one `@mcp.completion()` handler on a single tool, deployed behind a documented experimental flag.
4. Phase 2 ship gate: a Decision Log entry records the host-behavior verification result (Claude Code surfaces prompts/completion: yes/no, observed evidence) before scoping the full migration of either surface.
5. No latency regression on the rebuild paths — `report_progress` must be fire-and-forget via `loop.create_task` matching the existing `send_resource_updated` pattern.
6. No regression on existing framework tests.
7. The Phase 2 experimental flag is documented (env var or workflow-config key) with a follow-up checkpoint date so the flag does not rot.

## Scope

**Problem statement:** The parent change `1p2q3/131hh` shipped Phase 1a (resource-updated notifications on graph rebuild) and explicitly deferred Phase 1b and Phase 2 with reasons. This change picks up the deferred work and either ships the Phase 2 pilots cleanly with verification evidence or formally documents host-behavior limitations that prevent the full migration.

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` — accept an optional progress-callback in `update_graph_index` so callers can wire `report_progress`.
- `.wavefoundry/framework/scripts/graph_query.py` — wire `ctx.report_progress` into the auto-rebuild path (parse / edge-resolution / cluster checkpoints).
- `.wavefoundry/framework/scripts/server_impl.py` — wire `ctx.report_progress` into the `wave_index_build` rebuild path; thread `Context` through the affected tool handlers.
- One pilot `@mcp.prompt()` registration against an existing `docs/prompts/*.md` entry, behind a documented experimental flag.
- One pilot `@mcp.completion()` handler on a tool with completable arguments (e.g., `code_definition(symbol_or_path_position=...)`), behind the same flag.
- Decision Log entries recording phase outcomes (Phase 1b ship + Phase 2 verification gate).

**Out of scope:**

- Full `@mcp.prompt()` migration of `docs/prompts/*.md` (depends on Phase 2 verification outcome — would be a separate change).
- Full `@mcp.completion()` surface across every tool with completable arguments (same gating).
- `ctx.log()` / `send_resource_list_changed` (parent's Phase 3 — opportunistic, no scheduled work).
- `ctx.elicit*`, `ctx.create_message`, `mcp.custom_route`, alternative transports — documented as not-relevant in the parent audit.

## Acceptance Criteria

Inherited from parent `1p2q3/131hh` (numbered per the parent doc for traceability):

**Phase 1b — progress notifications:**

- [ ] AC-2 (parent): The graph auto-rebuild path emits at least three `ctx.report_progress` checkpoints (parse phase, edge-resolution phase, cluster phase) when invoked inside a tool-handler context with a `Context` parameter wired.
- [ ] AC-3 (parent): `wave_index_build(mode='rebuild')` inline path emits `ctx.report_progress` checkpoints during the embedding-rebuild phase.

**Phase 2 — exploratory pilots:**

- [ ] AC-6 (parent): One `@mcp.prompt()` registration deployed against an existing `docs/prompts/*.md` entry, behind a documented experimental flag. The resource registration for the same markdown is preserved during verification (both surfaces coexist).
- [ ] AC-7 (parent): One `@mcp.completion()` handler deployed on a single tool with completable arguments, behind a documented experimental flag.
- [ ] AC-8 (parent): **Phase 2 ship gate** — a Decision Log entry records the host-behavior verification result (Claude Code surfaces prompts/completion: yes/no, observed evidence) before scoping the full migration. Without this entry, Phase 2 does not proceed past the experiment.

**Regression / hygiene:**

- [ ] No latency regression on the rebuild paths verified via framework test wall-time delta (within ±5% of pre-change baseline).
- [ ] Existing framework tests pass without modification.

## Tasks

- [ ] Open `framework_edit_allowed` gate
- [ ] **Phase 1b (a):** thread an optional `progress_callback` through `update_graph_index` (graph_indexer) so callers can wire `report_progress`
- [ ] **Phase 1b (b):** thread `Context` through the rebuild-triggering tool handlers (graph_query auto-rebuild + server_impl `wave_index_build`)
- [ ] **Phase 1b (c):** emit at least three checkpoints per rebuild path (parse / edge-resolution / cluster)
- [ ] Regression coverage: assert progress notifications fire during rebuild via FastMCP test harness
- [ ] **Phase 2 (a):** pilot `@mcp.prompt()` registration against one existing `docs/prompts/*.md` behind an experimental flag
- [ ] **Phase 2 (b):** pilot `@mcp.completion()` handler on a single tool behind the same flag
- [ ] **Phase 2 ship gate:** verify host behavior in Claude Code (and any other host in active use); record Decision Log entry with the result
- [ ] Based on Decision Log outcome: scope a follow-on change for the full migration (if positive) or document why we are not migrating (if negative)
- [ ] Run framework tests
- [ ] Close gate; mark change `implemented`

## Affected Architecture Docs

`N/A` — extends an existing MCP server module. No architectural boundary change. The `Context`-threading change in `graph_query.py` and `server_impl.py` is contained.

## Open Questions

(Carried forward from parent's Open Questions; re-verify during implementation.)

1. **Does Claude Code's UI actually render `@mcp.prompt()` registrations?** Verify empirically via the Phase 2 pilot.
2. **Does Claude Code's tool-arg input surface `@mcp.completion()` results?** Same — empirical verification required.
3. **Does the `Context` parameter survive across the `importlib.reload` in `perform_mcp_reload`?** The reload re-imports `server_impl` but the FastMCP instance's request_context binding may need re-validation.

## Related Work

- Parent: `1p2q3/131hh-enh mcp-protocol-surface-opportunities` (Phase 1a portion of this surface).
- Related sibling: `1p30y-enh dashboard-rendering-fidelity-phase-2` (Phase 2 of `1p2q3/131es` dashboard rendering, splitting from the same field-feedback round).
- Patterned after: `1p2q3/131bu` (`wave_mcp_reload` description-refresh via `send_tool_list_changed`) — same "adopt an existing MCP protocol primitive we weren't using" template.

## Session Handoff

Unattached future-wave plan. Admit when a Wave Council readiness review accepts the follow-on UX-polish wave. Phase 1b should be scoped together; Phase 2 pilots can ship in the same change if Context-threading work is bounded, otherwise split.
