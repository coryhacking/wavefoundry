# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-30

wave-id: `1304x graph-mcp-parity-and-dashboard-polish`
Title: Graph MCP Parity and Dashboard Polish

## Objective

Generalize the refresh-and-instruct pattern established by wave `12xr3` change `1301h` (`code_definition`) across all remaining graph-using MCP tools so operators see consistent miss behavior, plus a small dashboard reorder that puts Agents above Graph in the main column.

## Changes

Change ID: `1304r-enh graph-tool-refresh-and-instruct-parity`
Change Status: `implemented`

Change ID: `1304w-enh dashboard-agents-above-graph`
Change Status: `implemented`

Change ID: `13047-enh dashboard-remove-graph-project-pill`
Change Status: `implemented`

Change ID: `1305d-enh review-rigor-fix-now-not-later`
Change Status: `implemented`

Completed At: 2026-05-30

## Wave Summary

Wave `1304x` (Graph MCP Parity and Dashboard Polish) delivered 4 changes: Graph-Tool Refresh-and-Instruct Parity, Dashboard: Move Agents Panel Above Graph Panel, Dashboard: Remove the Standalone "project" Layer Pill from the Graph Card, and Review Rigor: Fix-Now-Not-Later as Standing Practice.

**Changes delivered:**

- **Graph-Tool Refresh-and-Instruct Parity** (`1304r-enh graph-tool-refresh-and-instruct-parity`) — 9 ACs completed. Key decisions: Single helper, called by each tool at its miss site; Synchronous refresh inline (not background)
- **Dashboard: Move Agents Panel Above Graph Panel** (`1304w-enh dashboard-agents-above-graph`) — 4 ACs completed. Key decisions: Single line swap, no component changes; Preserve the `agents.length ?` conditional
- **Dashboard: Remove the Standalone "project" Layer Pill from the Graph Card** (`13047-enh dashboard-remove-graph-project-pill`) — 4 ACs completed. Key decisions: Delete the entire `graph-layer-switch` wrapping div, not just the button; Don't delete the `.graph-layer-pill` CSS class
- **Review Rigor: Fix-Now-Not-Later as Standing Practice** (`1305d-enh review-rigor-fix-now-not-later`) — 6 ACs completed. Key decisions: Encode the principle as seed prompt guidance, not as a lifecycle gate; ~20 LOC threshold for "in-session"
## Acceptance Criteria

- Every graph-using MCP tool attempts a single incremental graph refresh when its initial graph query returns no result, then returns the existing not-found / suggestions response if the refresh didn't produce a hit (`1304r`).
- Diagnostic codes used across the graph-using MCP tools are limited to `graph_index_missing_degraded`, `graph_not_ready`, and `graph_symbol_not_found`, each carrying `recovery_tools` and `recovery_usage` (`1304r`).
- The dashboard renders `Agents` directly after `FrameworkFlow` and before `GraphPanel` in the main column (`1304w`).
- All framework tests pass; docs-lint clean.

## Journal Watchpoints

- **Watchpoint:** `framework_edit_allowed` gate required before editing `server_impl.py` (for `1304r`) and `dashboard.js` (for `1304w`). Blocking concern if either edit slips outside the gate.
- **Follow-up:** `1304r` adds inline graph refresh on miss paths — confirm that the existing `_index_build_lock` correctly serializes concurrent callers; flag as a blocking issue if any test regression appears around concurrent index builds.
- **Watchpoint:** `1304r` must not regress `code_definition` (already implements this pattern via wave 12xr3 change 1301h); the helper extraction should be a refactor with no behavior change. Treat any 1301h test failure as a blocking issue.

## Coordinator

- `wave-coordinator`

## Participants

| Role | Lane | Scope |
|------|------|-------|
| implementer | implement | server_impl.py, dashboard.js |
| code-reviewer | review | all — `.wavefoundry/framework/scripts/server_impl.py`, dashboard JS |
| qa-reviewer | review | parity tests for 7 tools + dashboard order verification |

## Review Evidence

- wave-council-readiness: approved — 2026-05-30; two-change wave with a focused theme (graph MCP parity + dashboard panel reorder). Inline council with red-team and code-reviewer seats: helper extraction in `1304r` is a structural transform with no behavior change on the established `code_definition` path (1301h tests guard the no-op); dashboard swap in `1304w` is one line with no markup or CSS changes. Both decision logs are appropriately sized; AC priority is set. Suggested implementation order: `1304w` first (trivial, validates the implement-phase pipeline after the long 12xr3 close), then `1304r` (mechanical but substantial). PASS.
- code-reviewer: approved — 2026-05-30; close-review covered the four changes (`1304r`, `1304w`, `13047`, `1305d`). Initial close-review surfaced four findings (A1 — `code_graph_path` doesn't refresh both symbols; missing per-tool refresh tests; AC-6 diagnostic vocab not consolidated; AC-9 arch doc not generalized) plus three code-review observations (closure-smuggle `holder` dict, missing `Callable` type hint, broad `except Exception`). All seven fixed in-session per the new `1305d` fix-now-not-later default. Second-pass review found one additional in-session fix (Wave Summary in `wave.md` only described the original 2-change scope) — applied. Zero findings routed to follow-on.
- qa-reviewer: approved — 2026-05-30; test landscape: `TestGraphRefreshThenRecheck` (4), `TestGraphRefreshAndResolve` (3), `TestGraphToolRefreshOnMiss` (8 — one per tool plus A1 regression). 1301h test suite continues to pass, confirming `code_definition` was not regressed by the helper extraction. Total: 1878/1878 tests pass. Dashboard tests cover the JS render-tree unchanged. Per-tool refresh tests verify `wave_index_build_response` is called exactly once on miss by patching and asserting `call_count == 1`. Operator-verified the dashboard smoke ("dashboard looks good"); `1304w` and `13047` AC-4 manual smoke marked complete.
- wave-council-delivery: approved — 2026-05-30; PASS WITH IN-SESSION FIXES (architecture-reviewer, code-reviewer, qa-reviewer, security-reviewer, performance-reviewer, red-team, reality-checker). The wave demonstrated the `1305d` fix-now-not-later principle in real time: initial council synthesis defaulted to filing four findings as follow-on; operator pushback redirected all four to in-session fixes; second-pass council found one additional in-session fix (Wave Summary). Final state: 1878 tests pass, docs-lint clean, four changes implemented, zero open quality issues from the review. Latency wins confirmed live: `code_callhierarchy` 304ms (with refresh), `code_callgraph` 149ms, `code_impact` 24ms, `code_graph_path` 24ms (either-direction), `code_references` 230ms, `wave_graph_report` 131ms, `code_graph_community` 25ms. PASS.
- operator-signoff: approved — 2026-05-30; operator authorized all four changes in this session: `1304r` (graph MCP parity), `1304w` (dashboard Agents-above-Graph), `13047` (graph project pill removal), and `1305d` (review rigor fix-now principle). Operator explicitly directed the in-session fix policy ("We're letting too many things go through review without recommending fixes... fix them now") which both encoded as `1305d` and applied to close out this wave's findings.

## Prepare Review Evidence

- code-reviewer: approved — 2026-05-30; reviewed both change docs ahead of implementation. `1304r` extracts an established pattern (`_graph_refresh_then_recheck`) and applies it uniformly across 6 graph-using tools — structural transform with the 1301h test suite guarding `code_definition` from regression. `1304w` is a one-line component swap in a render tree. Decision logs capture the four important calls in `1304r` and the two scope guards in `1304w`. AC priority is set on both. No code review concerns ahead of implementation.
- qa-reviewer: approved — 2026-05-30; both change docs specify test coverage: `1304r` AC-8 requires per-tool refresh-on-miss tests plus helper unit tests; `1304w` AC-3 requires `test_dashboard_server.py` continues passing. The 1301h test suite (which `1304r` must preserve) is already comprehensive. Implementation will land tests alongside the structural changes per the task list.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-05-30: PASS** (moderator: council-moderator; primer-depth: standard; seats: red-team, code-reviewer; rotating-seat: code-reviewer; strongest-challenge: helper extraction in `1304r` could regress `code_definition` if the signature diverges from the inline pattern; strongest-alternative: leave `code_definition` inline and only add the helper for the six new sites — rejected because uniform implementation is the entire goal and the 1301h test suite guards against regression)

## Dependencies

- Depends on wave `12xr3 graph-augmentation-promotion` being closed (this wave generalizes a pattern introduced there). 12xr3 was closed 2026-05-30.
