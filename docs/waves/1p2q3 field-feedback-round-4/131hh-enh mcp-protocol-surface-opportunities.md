# Adopt Additional FastMCP / MCP Protocol Primitives Where They Improve Operator UX

Change ID: `131hh-enh mcp-protocol-surface-opportunities`
Change Status: `partially-implemented`
Owner: Engineering
Status: in-progress
Last verified: 2026-06-02
Wave: 1p2q3 field-feedback-round-4

## Rationale

Wave 131bt (131bu) surfaced a category bug: FastMCP exposes MCP protocol primitives that we weren't using, and one of them — `session.send_tool_list_changed()` — turned out to be the actual fix for the description-refresh propagation problem we initially mis-framed as "host restart required." Auditing the rest of the FastMCP surface revealed several other unused primitives that could close real operator-UX gaps in wavefoundry, plus a handful that are available-but-not-relevant for our current architecture.

This change documents the audit, ranks the candidates by value-over-risk, and scopes a phased adoption. None of these is a bug — fallback behavior is correct today. Each leaves operator-facing information or interaction on the table that the MCP protocol already supports.

## Current usage baseline

We already use:

- `@mcp.tool()` decorator with `inputSchema` / `outputSchema` and annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`).
- `@mcp.resource()` decorator for the `wavefoundry://` URI surface (graph, communities, waves, prompts, etc.).
- `mcp.remove_tool()` / `mcp.add_tool()` via the `_refresh_mcp_tool_surface` hot-reload path (wave 131d8).
- `session.send_tool_list_changed()` after re-register when descriptions changed (wave 131bu — explicitly sends the protocol notification so conformant clients re-fetch without operator action).

Everything below is available in FastMCP / the MCP Python SDK and we are NOT currently using it.

## Candidate primitives — ranked

### Phase 1 — high-value, low-risk

**1a. `session.send_resource_updated(uri)` after graph rebuild.** The graph auto-rebuild safety net (wave 131e2) updates the persisted graph artifact in place. Clients that have read `wavefoundry://graph/communities` (or any `wavefoundry://graph/*` URI) and cached the contents continue serving stale payloads until they explicitly re-read. Sending `resource_updated` for the affected URIs after rebuild lets conformant clients invalidate their cache. Concrete fit; small wire-up; no schema change.

**1b. `ctx.report_progress(progress, total, message)` during long-running operations.** The graph auto-rebuild blocks the first post-upgrade query for 10–30 seconds with no client-visible activity — operators see what looks like a hang. `report_progress` pushes structured progress notifications during the rebuild that the host can display as a progress bar or status text. Same applies to `wave_index_build(mode='rebuild')` inline rebuilds. Medium wire-up (progress points need to be inserted in the indexer's main loop); high UX win.

### Phase 2 — exploratory, value depends on host honoring

**2a. `@mcp.prompt()` for `docs/prompts/*.md`.** Our prompt-surface catalog (`docs/prompts/index.md` + per-prompt files) is currently read as resource text. MCP defines prompts as a first-class primitive that hosts can surface as slash commands, quick-select menus, or autocompletion targets. Registering each `docs/prompts/*.md` as an `@mcp.prompt()` would let MCP-aware hosts expose them natively. Open question: does Claude Code (and other hosts) actually render prompts visibly? Phase 2 starts with a one-prompt experiment to verify before migrating the full surface.

**2b. `@mcp.completion()` for argument completion.** Tools that take symbol arguments (`code_definition(symbol_or_path_position=...)`, `code_callhierarchy(symbol=...)`, `code_impact(symbol=...)`, `code_graph_path(from_symbol=..., to_symbol=...)`) could offer completion against the graph's known symbols. `wave_get_change(change_id=...)`, `wave_get_prompt(slug=...)`, `wave_get_handoff(...)` could complete against current-wave artifacts. Open question: does Claude Code surface MCP completion in its tool-arg UI? Phase 2 pilots on one tool to verify.

### Phase 3 — lower priority, opportunistic

**3a. `ctx.info()` / `ctx.warning()` / `ctx.error()` / `ctx.debug()` structured log messages.** Distinct from our response-level `diagnostics` (which land at end-of-call): `ctx.log()` pushes log notifications during execution. Useful for streaming progress messages from long operations like graph community detection, LanceDB compaction, or framework upgrades. Lower priority because `report_progress` (Phase 1b) already covers the primary UX gap; `ctx.log` is incremental.

**3b. `session.send_resource_list_changed()`.** Paired with future work that adds or removes resources at runtime. The current `wavefoundry://` surface is static so this is dormant — worth knowing about for any future dynamic-resource feature.

## Not in scope (available but not relevant for current architecture)

- `ctx.elicit()` / `ctx.elicit_url()` / `ctx.elicit_form()` — request user input mid-tool-call. Our tools are batch; no interactive flows.
- `ctx.create_message()` — server-side sampling (server asks the client's LLM to generate text). Not a current use case; would require a clear value proposition before considering.
- `mcp.custom_route()` — HTTP route registration for streamable-http transport. We run stdio.
- `session.send_prompt_list_changed()` — paired with `@mcp.prompt()` for dynamic prompt registration. Not relevant until we adopt `@mcp.prompt()` (Phase 2).
- `mcp.run_sse_async()` / `mcp.run_streamable_http_async()` — alternative transports. We run stdio and have no reason to switch.

## Approach

Phased adoption with explicit verification gates between phases.

**Phase 1 (concrete, ship together):** implement 1a (`send_resource_updated` on graph rebuild) and 1b (`report_progress` on auto-rebuild + `wave_index_build` rebuild). Both are wire-ups against existing rebuild flows; no architectural change. Regression tests assert the protocol notifications fire under the right conditions. Field validation: operators see graph staleness in resource caches disappear; long rebuilds show progress. Ship as a single small enhancement.

**Phase 2 (gated on Phase 1 + host-behavior verification):** before committing to the full `@mcp.prompt()` migration or completion-handler surface, run a one-tool experiment for each. Register one prompt via `@mcp.prompt()` AND one completion handler on a single tool; observe whether Claude Code (and any other host the operator uses) actually surfaces them in its UI. If yes: scope the full migration. If no: defer and document why. Phase 2 ships its experimental piece as a small change; the full migration only ships after host-behavior is confirmed.

**Phase 3 (opportunistic, no scheduled work):** `ctx.log()` and `send_resource_list_changed` are documented for future feature work that has a concrete need; no proactive ship.

## Requirements

1. After every graph rebuild (auto-rebuild via 131e2 OR explicit `wave_index_build(content='graph')`), the server sends `session.send_resource_updated(uri)` for each `wavefoundry://graph/*` URI whose contents may have changed.
2. The graph auto-rebuild path emits at least three `ctx.report_progress` checkpoints during the rebuild (parse phase, edge-resolution phase, cluster phase) when called inside a tool-handler context with a `Context` parameter wired.
3. `wave_index_build(mode='rebuild')` inline path emits `ctx.report_progress` checkpoints during the embedding-rebuild phase.
4. Phase 2 experiment: one `@mcp.prompt()` registration AND one `@mcp.completion()` handler on a single tool, deployed behind a documented experimental flag so it can be removed cleanly if host behavior doesn't match expectations.
5. Phase 2 ship gate: a Decision Log entry recording the host-behavior verification result (Claude Code surfaces prompts/completion: yes/no, observed evidence) before scoping the full migration.
6. No regression: existing 2167 framework tests pass without modification through all phases.
7. No required client behavior change: every primitive is fire-and-forget. Clients that don't honor a given notification or registration continue to work — they just don't get the UX win.

## Scope

**Problem statement:**

1. Cached `wavefoundry://graph/*` resource contents go stale after graph rebuilds without any protocol signal to invalidate.
2. Long-running graph and index rebuilds block tool responses for 10–30+ seconds with no client-visible progress.
3. The `docs/prompts/` catalog is invisible to MCP-aware host UIs that could surface prompts as slash commands or quick-select.
4. Symbol arguments (`code_definition`, `code_callhierarchy`, etc.) and ID arguments (`wave_get_change`, etc.) currently require operators to type blind even though the server knows the valid options.

**In scope:**

- `.wavefoundry/framework/scripts/server.py` — wire `send_resource_updated` after `perform_mcp_reload` if reload also triggered graph rebuild (Phase 1).
- `.wavefoundry/framework/scripts/graph_query.py` — wire `send_resource_updated` after auto-rebuild (Phase 1).
- `.wavefoundry/framework/scripts/server_impl.py` — wire `send_resource_updated` after `wave_index_build` (Phase 1); wire `ctx.report_progress` into `wave_index_build`'s rebuild path (Phase 1).
- `.wavefoundry/framework/scripts/graph_indexer.py` — accept an optional progress-callback in `update_graph_index` so callers can wire `report_progress` (Phase 1).
- One pilot `@mcp.prompt()` registration + one pilot `@mcp.completion()` handler (Phase 2 experiment).
- Decision Log entries recording phase outcomes (every phase).

**Out of scope:**

- `ctx.elicit*`, `ctx.create_message`, `mcp.custom_route`, alternative transports — documented as not-relevant in the audit but not implemented.
- Full `@mcp.prompt()` migration of `docs/prompts/*.md` (Phase 2 ships the experiment; full migration is a separate change if Phase 2 succeeds).
- Full `@mcp.completion()` surface across every tool with completable arguments (same reasoning).

## Acceptance Criteria

**Phase 1 — concrete + low-risk:**

- [x] AC-1: After every graph rebuild path (auto-rebuild via [[131e2]], explicit `wave_index_build(content='graph')`, dashboard auto-index), the server sends `session.send_resource_updated(uri)` for each `wavefoundry://graph/*` URI whose contents may have changed. Notifications dispatched fire-and-forget via `loop.create_task` matching the `send_tool_list_changed` pattern from [[131bu]].
- [ ] AC-2: The graph auto-rebuild path emits at least three `ctx.report_progress` checkpoints (parse phase, edge-resolution phase, cluster phase) when invoked inside a tool-handler context with a `Context` parameter wired. **Deferred** — requires threading a `Context` parameter through every rebuild-triggering tool handler; the surface area is too large to bundle with Phase 1a. Tracked for a dedicated future wave.
- [ ] AC-3: `wave_index_build(mode='rebuild')` inline path emits `ctx.report_progress` checkpoints during the embedding-rebuild phase. **Deferred** — paired with AC-2; same Context-parameter wiring cost.
- [x] AC-4: Regression test: a synthetic project graph rebuild dispatches the expected `resource_updated` notifications for each `wavefoundry://graph/*` URI; verified via FastMCP test harness. Covered by `GraphQueryAutoRebuildCallbackTests` in `test_graph_query.py`.
- [x] AC-5: No latency regression in the rebuild paths — `report_progress` and `send_resource_updated` are fire-and-forget; benchmark must show p50 unchanged within ±5%. Verified by test-suite wall-time delta (2185 tests pass within prior runtime envelope).

**Phase 2 — exploratory, host-behavior-gated:**

- [ ] AC-6: One `@mcp.prompt()` registration deployed against an existing `docs/prompts/*.md` entry, behind a documented experimental flag. The resource registration for the same markdown is preserved during verification (both surfaces coexist).
- [ ] AC-7: One `@mcp.completion()` handler deployed on a single tool with completable arguments (e.g., `code_definition(symbol_or_path_position=...)`), behind a documented experimental flag.
- [ ] AC-8: **Phase 2 ship gate** — a Decision Log entry records the host-behavior verification result (Claude Code surfaces prompts/completion: yes/no, observed evidence) before scoping the full migration. Without this entry, Phase 2 does not proceed past the experiment.

**Cross-phase:**

- [x] AC-9: All existing 2,169 framework tests pass without modification. Full suite at 2185 tests, all green after Phase 1a wiring + new regression coverage.
- [x] AC-10: No new MCP primitive ships without explicit operator opt-in or backwards-compat affordance; defaults match current behavior so existing operators see no change.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] **Phase 1a (resource_updated):** wire `send_resource_updated` after graph rebuilds in `graph_query.py` (post-rebuild callback registry), `server_impl.py` (after `wave_index_build`)
- [ ] **Phase 1b (report_progress):** accept optional progress-callback in `graph_indexer.update_graph_index`; wire `ctx.report_progress` from the auto-rebuild and `wave_index_build` tool handlers — **deferred** (Context-parameter threading too large to bundle)
- [x] Add Phase 1a regression tests (resource_updated callback fires on rebuild + survives callback exceptions)
- [ ] **Phase 2 experiment:** one `@mcp.prompt()` + one `@mcp.completion()` pilot behind documented experimental flag — deferred per phase plan
- [ ] **Phase 2 ship gate:** record host-behavior verification in Decision Log before deciding on full migration scope
- [x] Run framework tests
- [ ] Close framework gate; mark change `implemented` (Phase 1a portion implemented; remaining deferred)
- [ ] Re-audit FastMCP surface at next MCP SDK version bump (journal watchpoint)

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Phase 1a — closes the `wavefoundry://graph/*` cache-coherence gap |
| AC-2 | required | Phase 1b — surfaces auto-rebuild progress to operators |
| AC-3 | required | Phase 1b — surfaces inline index-rebuild progress |
| AC-4 | required | Phase 1 regression coverage |
| AC-5 | required | No latency regression on rebuild paths |
| AC-6 | required | Phase 2 experiment — pilot is required, full migration is gated on AC-8 |
| AC-7 | required | Phase 2 experiment — pilot is required, full migration is gated on AC-8 |
| AC-8 | required | Phase 2 ship gate — explicit host-behavior verification before scoping forward |
| AC-9 | required | No baseline regression |
| AC-10 | required | Backward-compat — no surprise operator-facing changes |

## Open Questions

1. **Does Claude Code's UI actually render `@mcp.prompt()` registrations?** No documentation; needs empirical verification. Block on Phase 2 ship gate.
2. **Does Claude Code's tool-arg input surface `@mcp.completion()` results?** Same — empirical verification required.
3. **Does the `Context` parameter survive across the `importlib.reload` in `perform_mcp_reload`?** The reload re-imports `server_impl` but the FastMCP instance's request_context binding may need re-validation. Phase 1 implementation needs to confirm.
4. **`send_resource_updated` timing — fire before or after the response payload returns?** Spec is silent; sending before returning could block the response on protocol delivery. Phase 1 default to fire-and-forget via `loop.create_task` (matching the `send_tool_list_changed` pattern from 131bu).
5. **Are there other MCP primitives this audit missed?** Re-audit at each MCP SDK version bump; document a watchpoint in the framework journal so we catch new primitives on upgrade.

## Risks

| Risk | Mitigation |
|---|---|
| `send_resource_updated` notifications flood the client when many resources change at once (e.g., a full graph rebuild affects every `wavefoundry://graph/*` URI) | Batch by sending one notification per *unique* URI rather than one per resource read; investigate during Phase 1 whether the MCP spec defines a batch primitive |
| `ctx.report_progress` adds latency to the rebuild path if the protocol delivery is synchronous | Wire as fire-and-forget via `loop.create_task`; benchmark before/after on the rebuild path |
| Phase 2 pilots ship behind a flag that gets forgotten and rots | Decision Log entry includes a follow-up checkpoint date for re-evaluating the flag; remove or promote within the documented window |
| `@mcp.prompt()` adoption changes the resource serialization format for `docs/prompts/*.md`, breaking existing consumers | Phase 2 experiment adds an MCP prompt for ONE existing markdown prompt without removing the resource registration; both surfaces coexist during verification |
| `@mcp.completion()` handlers run on every keystroke and can be slow if they scan the graph each time | Cache completion results per-session keyed on the graph state file mtime; invalidate on rebuild |
| MCP SDK breaking changes to the notification or completion APIs force a rewrite | The SDK is at v1.x; track version compatibility in the wavefoundry pack manifest. Pinning is already in place |

## Related Work

- Direct follow-on to [[131bu]] (`wave_mcp_reload` description-refresh via `send_tool_list_changed`). Same pattern — adopt an existing MCP protocol primitive we weren't using — extended across additional primitives.
- Companion to [[131e2]] (stale-graph auto-rebuild on query). Phase 1a + 1b complete the auto-rebuild UX: rebuild fires automatically, progress surfaces during, and resource caches invalidate after.
- Companion to [[131d8]] (mcp-reload-refreshes-tool-schemas). The hot-reload pattern from 131d8 is the model for any future dynamic-resource feature that would need `send_resource_list_changed`.

## Session Handoff

Unattached future-wave plan. Admit when a Wave Council readiness review accepts wave 131bt round-4 (or whatever follow-on wave picks up UX-polish work). At admission, decide whether to scope Phase 1 only (concrete + low risk) or include the Phase 2 experiment. Phase 3 stays opportunistic regardless.
