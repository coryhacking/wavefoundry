# Stable Community Identifier — Survive Graph Rebuilds via Hub-Anchor

Change ID: `1316r-enh stable-community-identifier`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

Aceiss round-trip report on `1.2.1+315o` (2026-06-01): community ids like `project:c12` are Leiden iteration artifacts — they change every time the graph is regenerated. The "JSON" community moved from `project:c12` to `project:c237` between sessions. Agents cache community ids from `wave_graph_report` responses, then drill in later with `code_graph_community(community_id="project:c12")` and hit `not_found`.

Within a session: works fine.
Across sessions, after an upgrade, after any wave that rebuilds the graph: cached ids stale.

Seed-211 currently tells agents to call `wave_graph_report`, capture community ids, and follow up with `code_graph_community`. The pattern is right; the id is the wrong anchor.

## Approach

Add a **stable community identifier** to every community-bearing response: a `community_hub_node_id` field that identifies the community by its highest-degree member. Hub node ids are stable across rebuilds (graph nodes have stable ids derived from file path + qname; only the Leiden community numbering churns).

`code_graph_community` accepts a new parameter `hub_node_id: str | None = None` (in addition to the existing `community_id`). When `hub_node_id` is provided, the tool resolves it to the current Leiden community containing that node and returns the members. This gives operators a stable anchor:

- First call: `wave_graph_report` → response includes `community_id` (current Leiden) AND `community_hub_node_id` (stable). Operator stores `community_hub_node_id`.
- Future call: `code_graph_community(hub_node_id="path/JSON.java::JSON")` → resolves to whatever community contains that hub today.

The existing `community_id` parameter continues to work for in-session use. Cross-session/cross-rebuild flows use `hub_node_id`.

Seed-211 updates: agents should prefer `hub_node_id` for any cached or persisted reference; `community_id` is fine for the immediate-followup case within one investigation.

## Requirements

1. **Every response surface that returns a `community_id`** also returns `community_hub_node_id`:
   - `wave_graph_report.communities`
   - `code_graph_community` (the queried community)
   - Per-node `community_id` fields on `code_callhierarchy` / `code_impact` / `code_callgraph` carry a sibling `community_hub_node_id`
2. **`code_graph_community` accepts a new `hub_node_id: str | None = None` parameter.** When provided:
   - The tool looks up the node's current community via the cluster artifact.
   - Returns the community's members as if `community_id` were provided.
   - If both `community_id` and `hub_node_id` are provided, `community_id` wins; the response notes the override in diagnostics for clarity.
3. **MCP wrapper exposes `hub_node_id`.** Add to `TestMcpWrapperParameterExposure` regression test.
4. **Seed-211 verification guidance updated** to recommend `hub_node_id` for cached / persisted references.
5. **Tests** cover (a) `wave_graph_report.communities` entries carry `community_hub_node_id`; (b) `code_graph_community(hub_node_id=...)` resolves correctly; (c) MCP wrapper exposure; (d) Per-node community sibling field on `code_callhierarchy`.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py` — surface additions on five responses; `code_graph_community` `hub_node_id` parameter.
- `.wavefoundry/framework/seeds/211-guru.prompt.md` — caching guidance update.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` — 4 regression tests + wrapper exposure test.

**Out of scope:**

- Removing the existing `community_id` field. Kept for in-session backward compat.
- Guaranteeing Leiden numeric id stability across rebuilds (Aceiss's option 2). Leiden communities are an emergent property of the graph; renumbering reflects real membership changes. The hub-anchor is the right abstraction.
- A persistent community name registry (`"JSON Community"` → stable name). Operator-friendly labels exist on the entries; the hub_node_id is the machine-stable handle.

## Acceptance Criteria

- [x] AC-1: `wave_graph_report.communities` entries carry `community_hub_node_id` alongside the existing `community_id`/`label`/`hub_node_id` fields.
- [x] AC-2: `code_graph_community` response carries `community_hub_node_id` for the queried community.
- [x] AC-3: `code_callhierarchy` / `code_impact` / `code_callgraph` per-node entries carry `community_hub_node_id` alongside the existing `community` (label) / `community_id` fields.
- [x] AC-4: `code_graph_community` accepts `hub_node_id` parameter. When provided, resolves to the current community containing that node.
- [x] AC-5: When both `community_id` and `hub_node_id` are provided to `code_graph_community`, the explicit `community_id` wins; a diagnostic notes the override.
- [x] AC-6: MCP wrapper exposes `hub_node_id` — verified in `TestMcpWrapperParameterExposure`.
- [x] AC-7: Seed-211 guidance updated to recommend `hub_node_id` for cached / persisted references.
- [x] AC-8: 4 regression tests cover the surface; all existing tests pass. **Explicit cross-clustering test required:** write two cluster artifacts with the SAME nodes but DIFFERENT Leiden ids for the same community (simulating a rebuild), then assert `code_graph_community(hub_node_id="…")` resolves to the correct (current-cluster-artifact) community in both states. This proves the "stable across rebuilds" claim rather than just "resolves in one snapshot". (Council action item: qa-reviewer.)
- [x] AC-9: docs-lint passes.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add `community_hub_node_id` to five response surfaces
- [x] Add `hub_node_id` parameter to `code_graph_community_response`
- [x] Update MCP wrapper signature
- [x] Open `seed_edit_allowed` gate
- [x] Update seed-211 caching guidance
- [x] Run docs-lint
- [x] Close `seed_edit_allowed` gate
- [x] Add 4 regression tests + wrapper exposure test
- [x] Run framework tests
- [x] Close `framework_edit_allowed` gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The stable anchor on wave_graph_report.communities |
| AC-2 | required | The stable anchor on code_graph_community response |
| AC-3 | required | Per-node consistency on the navigation tools |
| AC-4 | required | The lookup-by-hub flow |
| AC-5 | required | Explicit-wins for backward compat |
| AC-6 | required | MCP wrapper exposure — lesson from prior FastMCP cache rounds |
| AC-7 | required | Operator guidance |
| AC-8 | required | Regression coverage |
| AC-9 | required | docs-lint hygiene |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Hub-anchor (node_id) over guaranteed-stable Leiden numbering | Leiden community ids are emergent; trying to preserve numbering across rebuilds requires diffing community memberships, which has its own edge cases (community split/merge). Hub-anchor is mechanically simple and matches how operators think ("the community containing JSON.java") | Guarantee stable numeric ids (rejected — complex; community split/merge has no clean stable mapping); persistent community name registry (rejected — adds a new artifact + operator-defined mapping) |
| 2026-06-01 | Keep `community_id` alongside `hub_node_id` | In-session use is the common case; `community_id` is shorter and unambiguous within a session. The hub-anchor is for cross-session/rebuild scenarios | Replace `community_id` (rejected — breaks in-session flows that don't need stability) |
| 2026-06-01 | Both parameters: `community_id` wins when conflict | Operators passing `community_id` are explicitly choosing the in-session id; the hub_node_id is a fallback / cross-session path. Conflict resolution should prefer the explicit | hub_node_id wins (rejected — surprises in-session callers who pass both) |
| 2026-06-01 | Hub = highest-degree member of the community | The hub is the most-connected member; semantically the "public API" of the community. Picking it deterministically via degree-sort makes the hub stable as long as that node's connectivity is dominant (typical for healthy communities) | First-by-name (rejected — name-sort doesn't match operator intuition); manually-assigned community labels (rejected — adds maintenance burden) |

## Risks

| Risk | Mitigation |
|---|---|
| Hub node id changes when the community's top-degree member shifts (e.g. a refactor moves the dominant code away from the original hub) | This is a "community shape genuinely changed" signal; the hub change reflects reality. Operators querying by old hub get `not_found` + the existing `suggestions` list (cluster_lookup recovery, wave-130rj) routes to the current community |
| Multiple communities could share the same hub if a node ranks top-degree in two communities (unlikely but possible in pathological cases) | Hub is per-community; lookup resolves to the community containing the hub. If a node is in two communities (impossible with Leiden hard-clustering but defensive) the first match wins |
| Operators forget to migrate from `community_id` to `hub_node_id` for cached references | Seed-211 update + diagnostic on `code_graph_community(community_id=...)` not_found cases pointing at hub_node_id as the stable alternative |

## Related Work

- Direct response to Aceiss field feedback on `1.2.1+315o` (Finding 3).
- Builds on wave 130rj's `code_graph_community` shape (community_id dual return + suggestions on not_found) — adds the cross-rebuild dimension.
- Same wave: companion to `1316j` / `1316l` / `1316n` / `1316p` / `1316t`.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
