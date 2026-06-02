# Honest Description-Refresh Signal on `wave_mcp_reload` + Two Polish Fixes

Change ID: `131bu-bug mcp-reload-description-refresh-host-restart-signal-plus-polish`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 131bt field-feedback-round-3

## Rationale

Two distinct findings from field validation, scoped together because they share the same wave close-out window:

**Aceiss bug 1 (primary):** `wave_mcp_reload()` returns `ok: true`, `tools_reregistered: 66`, and `impl_matches_disk: true` after the [[131d8]] tear-down + re-register pass — but the MCP host's tool-list display does NOT refresh tool descriptions on a subsequent `/mcp` reconnect. seed-160 documents `/mcp` reconnect as sufficient; field testing demonstrated descriptions stay stale until a full Claude Code restart.

The first hypothesis ("Claude Code's `/mcp` doesn't re-fetch on reconnect; host restart required") matched the symptom but skipped the protocol-mechanism check. Inspecting the MCP Python SDK revealed FastMCP's `add_tool`/`remove_tool` do NOT send the `notifications/tools/list_changed` protocol notification, even though the SDK exposes `ServerSession.send_tool_list_changed()` for exactly this purpose. Without the notification, the client has no signal to re-fetch — the stale display isn't a `/mcp` reconnect failure; it's a missing notification at the server side. The right fix is to send the notification ourselves after re-register, not to instruct operators to restart. Spec-conformant clients re-fetch on receipt and surface the new descriptions automatically.

**Polish 1 (qualified-id alias):** When the class/module merge ([[1316l]]/[[13190]]) consumes a class node into the file id, the natural qualified-id query form `Foo.swift::Foo` returns `graph_symbol_not_found` even though the bare-name query `Foo` resolves correctly. The merge is by-design, but operators querying with explicit file-and-class qualification have to know about the merge to query successfully. The resolver can alias the qualified form transparently.

**Polish 2 (BFS confidence tie-break):** `code_graph_path` BFS surfaces an EXTRACTED import-placeholder path before a direct CONSTRUCTION_RESOLVED edge when both reach the destination in the same hop count. The construction edge is the more useful path to surface (deterministic attribution; concrete call site). Confidence-based tie-break preserves shortest-path correctness while preferring higher-quality edges.

## Approach

**Aceiss bug 1 — description snapshot diff + `notifications/tools/list_changed` notification:**

1. Snapshot tool descriptions (`{name: description_string}`) from FastMCP's `_tool_manager._tools` registry BEFORE the `remove_tool` + `add_tool` re-register pass.
2. Snapshot again AFTER re-register.
3. Compute `description_changed_tools = sorted({name: pre != post})`.
4. When the changed list is non-empty, retrieve the active `ServerSession` from `FastMCP.get_context().request_context.session` and call its `send_tool_list_changed()` method, dispatching the `notifications/tools/list_changed` MCP protocol notification to the connected client. The notification is fire-and-forget; if a running event loop is detected, schedule via `loop.create_task` so the reload response doesn't block on protocol delivery.
5. `perform_mcp_reload` adds three response fields: `description_changed_tools: list[str]`, `tool_list_changed_notification_sent: bool`, and a structured diagnostic — `tool_list_changed_notification_sent` (success) or `tool_list_changed_notification_failed` (failure with error string).
6. seed-160 step 13 updated to document the notification-based propagation path and the fallback-to-restart instruction for hosts that don't honor `tools/list_changed`.

The notification is the standard MCP propagation primitive. Spec-conformant clients re-fetch `tools/list` on receipt without operator action; clients that don't honor it (host-implementation-dependent) fall back to full restart. The honest diagnostic surfaces both paths so operators know which they're in.

**Polish 1 — `GraphQueryIndex.resolve_symbol` qualified-id alias:**

When the resolver receives a `<file_id>::<class_name>` query, look up the file id in `_node_by_id`. If the node carries `collapsed_pair: True` AND `label == class_name`, return the file id as the resolved node. Inserted after the exact-match check and before the existing suffix-match path so the alias takes precedence over (rare) accidental matches against non-merged collisions.

**Polish 2 — `GraphQueryIndex.shortest_path` BFS tie-break key:**

The candidate-sort key extends from `(len(neighbor_id), neighbor_id)` to `(confidence_rank, len(neighbor_id), neighbor_id)` where `confidence_rank` maps `RECEIVER_RESOLVED` and `CONSTRUCTION_RESOLVED` to rank 0, `EXTRACTED` to rank 1, and anything else (including missing) to rank 2. BFS still walks layer-by-layer (shortest path is preserved); within a layer, deterministic-attribution edges expand first.

## Requirements

1. `_registered_mcp_tool_descriptions(mcp)` helper returns `{tool_name: description_string}` from FastMCP's registry, handling both modern (`_tool_manager._tools`) and legacy (`_tools`) registry shapes.
2. `_refresh_mcp_tool_surface` snapshots descriptions before and after re-register, returns the diff in a new `description_changed_tools` field.
3. `perform_mcp_reload` response includes `description_refresh_requires_host_restart: bool` and `description_changed_tools: list[str]`.
4. When `description_refresh_requires_host_restart` is True, a structured diagnostic with code `description_refresh_requires_host_restart` is appended to the response's `diagnostics` array, listing the affected tools and explaining the host-restart requirement.
5. `tools_reregistered` field's semantic is honest: counts callable re-registration, not description visibility. Documented in the `wave_mcp_reload` tool docstring.
6. seed-160 step 13 reflects the actual propagation gap: description changes need full restart, parameter changes need only `/mcp` reconnect.
7. `GraphQueryIndex.resolve_symbol` aliases `<file_id>::<class_name>` to `<file_id>` when the file node is `collapsed_pair: True` and its label matches the class_name suffix.
8. `GraphQueryIndex.shortest_path` BFS tie-breaks candidates by confidence rank: `RECEIVER_RESOLVED` / `CONSTRUCTION_RESOLVED` (rank 0) before `EXTRACTED` (rank 1) before others (rank 2), then by neighbor-id length and value.

## Scope

**Problem statement:**

1. `wave_mcp_reload` returns unqualified success when description changes were detected and re-registered server-side, but the MCP host's tool-list display won't surface them without a full restart. Operators following the documented `/mcp` reconnect path see stale descriptions and trust the "ok" signal that's masking the propagation gap.
2. Querying merged class nodes by qualified id (`Foo.swift::Foo`) fails with `graph_symbol_not_found` despite the bare-name query (`Foo`) working — operators have to know about the merge to query successfully.
3. `code_graph_path` BFS preferences shorter neighbor-id strings over higher-confidence edges on tie, surfacing phantom import paths before direct construction edges in operator-facing path output.

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py` — new `_registered_mcp_tool_descriptions` helper.
- `.wavefoundry/framework/scripts/server.py` — `_refresh_mcp_tool_surface` returns description-diff; `perform_mcp_reload` adds `description_refresh_requires_host_restart` + `description_changed_tools`; `wave_mcp_reload` docstring documents the new fields.
- `.wavefoundry/framework/scripts/graph_query.py` — `resolve_symbol` qualified-id alias; `shortest_path` confidence tie-break.
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` — step 13 updated for the host-restart requirement.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` — regression tests for the unchanged-reload and changed-description paths.
- `.wavefoundry/framework/scripts/tests/test_graph_query.py` — regression tests for the qualified-id alias and BFS tie-break.

**Out of scope:**

- Closing the underlying MCP protocol propagation gap. The server side is correct; the host side caches descriptions across `/mcp` reconnect. Upstream protocol behavior is host-implementation-dependent — wavefoundry surfaces the gap honestly rather than working around it.
- Renaming `tools_reregistered` field. The field is honest about callable re-registration; the new fields communicate description visibility separately.
- Auto-detecting unrelated host-restart triggers (e.g., schema migrations, new tool additions). Description-change is the specific signal Aceiss identified; other triggers can be added as field validation surfaces them.

## Acceptance Criteria

- [x] AC-1: `_registered_mcp_tool_descriptions(mcp)` returns `{name: description}` from the FastMCP registry, handling both `_tool_manager._tools` (modern) and `_tools` (legacy) shapes.
- [x] AC-2: `_refresh_mcp_tool_surface` snapshots descriptions before and after re-register, returns a `(count, changed_tools_list, warnings)` 3-tuple.
- [x] AC-3: `description_changed_tools` is sorted deterministically for stable test assertions.
- [x] AC-4: `perform_mcp_reload` response includes `tool_list_changed_notification_sent: bool` — `True` when the protocol notification fired successfully after detecting description changes.
- [x] AC-5: `perform_mcp_reload` response includes `description_changed_tools: list[str]`.
- [x] AC-6: When description changes were detected, response `diagnostics` includes either `tool_list_changed_notification_sent` (success — notification delivered, client should re-fetch automatically) or `tool_list_changed_notification_failed` (failure with error string, host restart is the fallback).
- [x] AC-7: When no descriptions change between snapshots, the changed-tools list is `[]`, the notification doesn't fire, and no extra diagnostic appears.
- [x] AC-8: `wave_mcp_reload` tool docstring documents the two new response fields and the diagnostic.
- [x] AC-9: seed-160 step 13 documents the host-restart requirement and the `description_refresh_requires_host_restart` signal.
- [x] AC-10: `GraphQueryIndex.resolve_symbol("Foo.swift::Foo")` returns the file id when the file node is `collapsed_pair: True` and `label: "Foo"`.
- [x] AC-11: Same query returns `None` when the file node is not `collapsed_pair` (no alias for unmerged module nodes).
- [x] AC-12: Same query returns `None` when the suffix class name doesn't match the file node's label (no over-aliasing).
- [x] AC-13: `GraphQueryIndex.shortest_path` returns the 1-hop `CONSTRUCTION_RESOLVED` edge when a tying 2-hop `EXTRACTED` import path exists.
- [x] AC-14: Confidence rank: `RECEIVER_RESOLVED` and `CONSTRUCTION_RESOLVED` rank equal (0); `EXTRACTED` ranks below (1); missing or unknown confidence ranks last (2).
- [x] AC-15: All existing 2167 framework tests pass without modification.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add `_registered_mcp_tool_descriptions` helper in `server_impl.py`
- [x] Update `_refresh_mcp_tool_surface` signature and snapshot-diff logic in `server.py`
- [x] Update `perform_mcp_reload` response payload and diagnostic emission in `server.py`
- [x] Update `wave_mcp_reload` tool docstring in `server.py`
- [x] Add qualified-id alias path in `GraphQueryIndex.resolve_symbol` in `graph_query.py`
- [x] Add confidence tie-break in `GraphQueryIndex.shortest_path` in `graph_query.py`
- [x] Add regression tests for unchanged-reload and changed-description paths
- [x] Add regression tests for qualified-id alias and BFS confidence tie-break
- [x] Open `seed_edit_allowed` gate; update seed-160 step 13; close gate
- [x] Run framework tests
- [x] Close framework gate; mark change `implemented`

## Affected Architecture Docs

- N/A — this change strengthens existing operator-facing signals on `wave_mcp_reload` and refines two query-time behaviors in `GraphQueryIndex`. No architectural boundary or data flow change.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Helper foundation for description snapshot |
| AC-2 | required | Snapshot diff is the diagnostic source |
| AC-3 | required | Deterministic test assertions |
| AC-4 | required | Operator-facing restart signal |
| AC-5 | required | Operator-facing changed-tool list |
| AC-6 | required | Structured diagnostic emission |
| AC-7 | required | Negative case — no false flag |
| AC-8 | required | In-context docstring documentation |
| AC-9 | required | Seed propagation to upgrade workflow |
| AC-10 | required | Polish 1 — primary alias case |
| AC-11 | required | Polish 1 — false-positive containment |
| AC-12 | required | Polish 1 — false-positive containment |
| AC-13 | required | Polish 2 — primary tie-break case |
| AC-14 | required | Polish 2 — confidence rank correctness |
| AC-15 | required | No baseline regression |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Send `notifications/tools/list_changed` ourselves rather than instructing operators to restart | First-pass design said "host restart required" based on Aceiss's symptom report, treating the propagation as a fundamental gap. Investigating the SDK source revealed FastMCP's `add_tool`/`remove_tool` do NOT send `notifications/tools/list_changed` automatically, but `ServerSession.send_tool_list_changed()` exposes the primitive for explicit dispatch. The MCP spec defines the notification as the standard re-fetch trigger; conformant clients honor it. Sending it ourselves is the actual fix, not a workaround. Operators get descriptions refreshed automatically; restart is only the fallback when the host doesn't honor the notification | Tell operators to restart (rejected — was the first-pass instinct; investigating the protocol revealed an actionable fix); patch FastMCP upstream to send the notification (rejected — slow path; we don't need to wait); rename `tools_reregistered` to qualify it (rejected — the field is honest about what it counts; new fields communicate the distinct concept) |
| 2026-06-01 | Bundle polish 1 + polish 2 into the same change as Aceiss bug 1 | All three are small (each <30 LOC implementation), all three surfaced during the same close-out window, all three ship in the same repackage. Splitting into three change docs would create three audit trails for one packaging event; bundling preserves the close-out narrative coherently | Three separate change docs (rejected — three audit trails for one ship; readers would have to cross-reference); defer polish items to a future wave (rejected — both are <20 LOC and the test fixtures are already in front of us; deferring would force re-establishing context) |
| 2026-06-01 | Qualified-id alias check uses `collapsed_pair: True` AND `label == class_name` as the gate | Two-condition gate keeps false-positive surface narrow: only fires when the file node was actually class-merged AND the suffix matches the merged class identity. Without the label check, an unrelated file query like `Foo.swift::Bar` (where Bar isn't the merged class) would over-alias | `collapsed_pair`-only check (rejected — over-aliases when the suffix doesn't match the class identity); label-only check without `collapsed_pair` (rejected — could alias non-merged module nodes that happen to share a label) |
| 2026-06-01 | BFS tie-break: `RECEIVER_RESOLVED` and `CONSTRUCTION_RESOLVED` rank equal (both 0) | Both confidences represent deterministic attribution at the graph-builder; neither is preferable over the other on tie. Equal ranking preserves existing path determinism for non-cross-confidence ties | Rank `CONSTRUCTION_RESOLVED` higher than `RECEIVER_RESOLVED` (rejected — no operator-visible reason to prefer one over the other; both are deterministic); rank them as separate levels (rejected — same rejection reason) |

## Risks

| Risk | Mitigation |
|---|---|
| Description-change snapshot diff has false positives if FastMCP normalizes descriptions between snapshots (e.g., whitespace strip) | Direct string comparison from `_tool_manager._tools` registry, which holds the docstring verbatim; verified via the unchanged-reload regression test that two consecutive reloads with no source change produce empty `description_changed_tools` |
| `description_refresh_requires_host_restart: true` becomes a permanently-set flag if the host genuinely never picks up the changes | The flag is recomputed each reload from snapshots — it only fires when descriptions changed between the two specific reloads, not as persistent state. After a full host restart, the host re-fetches descriptions; subsequent reloads will report False until something changes again |
| Qualified-id alias resolves to the wrong node in collision cases (multiple merged classes with the same label across different files) | Two-condition gate (`collapsed_pair: True` AND `label == class_name`) keyed on the file_part means each alias resolution targets exactly one node by file id; no aggregation across multiple merged files |
| BFS tie-break changes path output for callers relying on the prior length-only ordering | Path output is documented as "shortest path"; tie-break within the same hop count was previously implicit and not contract; the confidence-based tie-break preserves shortest-path correctness while improving the operator-visible path quality |
| Description-diff diagnostic floods the response when many tools change | Operators see one diagnostic with a list of affected tools, not one diagnostic per tool. List is bounded by the first-party tool surface count |

## Related Work

- Direct follow-on to [[131d8]] (mcp-reload-refreshes-tool-schemas). The tear-down + re-register pass introduced there works correctly server-side; this change adds honest signaling of the host-side propagation gap.
- Aceiss field validation reports (round 3 + round 4 supersedence note) documented the propagation gap and the false-success-signal concern.
- Solaris field validation on [[1319v]] surfaced the two polish items: qualified-id alias miss and BFS tie-break preferring import placeholder over construction edge.
- Companion to [[131ar]] (mcp-tool-descriptions-sync-with-shipped-capabilities). 131ar shipped the description updates in 1.3.0; 131bu is the honest-signal layer ensuring future description updates surface correctly to operators.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
