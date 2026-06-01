# Sync MCP Tool Descriptions with 1.2.x Shipped Capabilities

Change ID: `131ar-doc mcp-tool-descriptions-sync-with-shipped-capabilities`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: TBD

## Rationale

Field report from Solaris on 1.2.1+319y: every feature shipped in the 1.2.x line for the original feedback writeup made it into the implementation and into seed-211, but **not into the per-tool MCP descriptions**. Agents that read seeds get the current guidance; agents that lean on tool descriptions (and operators querying schemas directly via MCP discovery) see a pre-1.2 surface.

Concrete drift inventory (verified on 1.2.1+319y):

| Tool | Drift |
|---|---|
| `wave_index_build` | Description still says `content: One of docs, code, or all`. The `graph` value shipped in 1.2.1+3192 and works. Response now includes `graph_rebuilt`, `graph_node_count`, `graph_edge_count`, `graph_last_built_at` — none in the response-field listing. |
| `wave_index_health` | Description lists `readiness`, `readiness_overview`, `compatible_chunks`, `stale_layers`, `missing_layers`, `semantic_ready`. The new `graph.<layer>.last_built_at` / `node_count` / `edge_count` block — the reason for the recent release — isn't mentioned. |
| `wave_graph_report` | Description doesn't mention the new per-entry collision diagnostics (`same_name_node_count`, `cross_file_collision`, `external_name_collision_count`, deprecated `name_collision_count` alias). Doesn't mention `*_candidates_total` / `*_threshold` empty-section diagnostics. Parameters `exclude_external`, `exclude_generated`, `collapse_generated_files`, `collapse_class_module_pairs` exist in the params block but aren't explained in the prose. |
| `code_impact` | Response field `affected` listed as `{node_id, label, kind, source_file, community}` — missing `hop` and `community_id`. Edges now carry `confidence: "RECEIVER_RESOLVED"` — significant precision indicator, undocumented. |
| `code_callhierarchy` | Response items now carry `community_id` (not documented). AOP/advice empty-incoming exception described in seed-211 has no surface on the tool description. |
| `code_graph_community` | Doesn't mention the new `community_size_class` (small/medium/large) or `large_community_advisory` diagnostic — both shipped in 1.2.1+315o. |

Two structural problems in seed-211 itself:

- The `wave_graph_report` bullet is ~600 words covering section descriptions, migration notes, three new collision fields with sub-explanations, wave history, allowlist examples for 5 languages, verification trigger formula, and follow-up tool recommendation. That's a section, not a bullet.
- The `code_graph_community` bullet is heading the same direction with `community_size_class` + `large_community_advisory`.

One missing operator-facing signal: `wave_index_build`'s description says only "Run a synchronous semantic index build" — no mention of the graph layer at all. An operator running it ad-hoc gets no hint that `content="graph"` is the right call for refreshing the call/edge graph.

One missing agent-facing signal: `confidence: RECEIVER_RESOLVED` (and its peer `EXTRACTED`, soon-to-be peer `CONSTRUCTION_RESOLVED` from `1319s`) is the precision indicator that makes the receiver-type fix usable. Agents see the tag on every edge but seed-211 says nothing about what each level means or whether to filter by confidence for high-stakes questions (refactor safety, security review).

**Closed without action (verified during scoping):** Finding 5 in the field report asked whether `RELEASE_NOTES.md` is actually shipping in the dist zip. Verified on 1.2.1+319y: `unzip -l ~/.wavefoundry/dist/wavefoundry-1.2.1.319y.zip | grep RELEASE` returns `.wavefoundry/framework/RELEASE_NOTES.md`. Artifact ships correctly; seed-240 process step is honored.

## Approach

Three coordinated workstreams, all touching docs / seeds / tool surface:

### Workstream A — Tool description sync (per-tool)

For each tool in the drift inventory above, update the tool description in its FastMCP registration to match the actual shipped behavior. The description string is what agents read at tool-invocation time and what operators see via MCP discovery; it's the agent-discoverable contract.

Per-tool edits:

1. **`wave_index_build`** —
   - Update `content` enumeration to `docs`, `code`, `graph`, `all`.
   - Add response fields: `graph_rebuilt`, `graph_node_count`, `graph_edge_count`, `graph_last_built_at`.
   - Add the operator hint: "For the call/edge graph (used by `wave_graph_report`, `code_impact`, `code_callhierarchy`), pass `content='graph'` — distinct from the semantic embedding indexes."

2. **`wave_index_health`** — add the `graph.<layer>.last_built_at` / `node_count` / `edge_count` block to the response-field listing with a one-line summary of what the block surfaces.

3. **`wave_graph_report`** —
   - Add per-entry collision-diagnostic fields: `same_name_node_count`, `cross_file_collision`, `external_name_collision_count`, plus a note that `name_collision_count` is a deprecated alias.
   - Add `*_candidates_total` / `*_threshold` empty-section diagnostics.
   - Add prose for the four parameters: `exclude_external`, `exclude_generated`, `collapse_generated_files`, `collapse_class_module_pairs`.

4. **`code_impact`** —
   - Update `affected` field listing to include `hop` and `community_id`.
   - Add `confidence` to the edge field listing with a one-line summary of its semantics.

5. **`code_callhierarchy`** —
   - Add `community_id` to the response-item listing.
   - Add the AOP/advice empty-incoming exception note from seed-211 (one line; full guidance stays in the seed).

6. **`code_graph_community`** — add `community_size_class` and `large_community_advisory` to the response-field listing.

### Workstream B — seed-211 restructure

Promote the two overloaded bullets out of "Tool Selection Quick Rules" into their own subsections:

- **"`wave_graph_report` — using the collision diagnostics"** — section descriptions, three new fields, wave history, allowlist examples, verification trigger formula (callout-formatted for scanability), follow-up tool recommendation.
- **"`code_graph_community` — interpreting community size signals"** — `community_size_class`, `large_community_advisory`, when each signal fires, what action it implies.

The "Tool Selection Quick Rules" bullet for each tool becomes a one-line pointer into its new subsection.

### Workstream C — Confidence-level guidance

Add explicit agent guidance for the `confidence` edge field. Lives in seed-211 under each of `code_impact`, `code_callhierarchy`, `code_graph_path`. Covers:

- **Levels currently shipping:** `RECEIVER_RESOLVED` (type-resolved at graph-builder per `1312l`/`13194`/`1319a`/`1319g`), `EXTRACTED` (heuristic fallback). Future: `CONSTRUCTION_RESOLVED` (from `1319s` if/when it lands).
- **Semantics per level:** what evidence each level represents and how confident an agent should be.
- **Filtering guidance for high-stakes questions:** refactor safety / security review — prefer `RECEIVER_RESOLVED` edges; treat `EXTRACTED` as needing corroboration via `code_references`.
- **`min_confidence` parameter:** clarify whether one exists, is planned, or won't ship — decide in Decision Log before writing the guidance.

## Requirements

1. Each of the 6 tools in the drift inventory has its description string updated in the FastMCP registration in `.wavefoundry/framework/scripts/server_impl.py`.
2. Tool descriptions retain operator-readable prose (not just bullet-listed field names) for any new parameter or response field.
3. seed-211 (`.wavefoundry/framework/seeds/<seed-211-path>`) restructures the `wave_graph_report` and `code_graph_community` bullets into their own subsections per Workstream B.
4. seed-211 adds confidence-level guidance under `code_impact`, `code_callhierarchy`, `code_graph_path` per Workstream C.
5. `wave_index_build` tool description adds the semantic-vs-graph orientation line.
6. All tool description changes pass MCP discovery — running an MCP `list_tools` shows the updated descriptions.
7. seed-160 unchanged — semantic-vs-graph split documentation for the upgrade workflow stays there; this change adds only the operator-facing one-line hint to the tool description itself.

## Scope

**Problem statement:** The MCP tool descriptions are roughly 3 releases behind the implementation. Agents reading the tool surface see a pre-1.2.x contract; only agents that explicitly read seed-211 get current guidance. Operators querying via MCP discovery see the same stale surface.

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py` — FastMCP tool description strings for the 6 tools in the drift inventory.
- `.wavefoundry/framework/seeds/` — seed-211 restructure (Workstream B) + confidence guidance (Workstream C).
- `.wavefoundry/framework/RELEASE_NOTES.md` — note the doc-sync release under the next semver section.

**Out of scope:**

- New tool surface (parameters, response fields) — this is a docs sync, not a feature add. If a description-sync reveals a parameter that should exist but doesn't, file a separate change.
- Migrating away from string-based descriptions to schema-driven generation. The current FastMCP pattern is description-as-string; structural refactor is out of scope.
- Cross-language extension of the `CONSTRUCTION_RESOLVED` confidence tag — depends on `1319s`; if `1319s` lands first, fold its tag into the guidance; if not, leave the guidance with the two current levels and `CONSTRUCTION_RESOLVED` as "future."
- seed-160 changes. The upgrade-workflow surface stays where it is; this change adds only the one-line operator hint to `wave_index_build`'s tool description.
- Hot-reload requirement: description-string changes likely require an MCP server restart (full restart, not `/mcp` reconnect) to expose, per the `wave_graph_report` carryover note from wave 13129. Document the restart requirement in Decision Log; no implementation work for hot reload.

## Acceptance Criteria

**Tool description sync (Workstream A):**

- [ ] AC-1: `wave_index_build` description lists `content` values as `docs`, `code`, `graph`, `all` and includes the four new response fields (`graph_rebuilt`, `graph_node_count`, `graph_edge_count`, `graph_last_built_at`).
- [ ] AC-2: `wave_index_build` description includes the operator hint about `content="graph"` for the call/edge graph.
- [ ] AC-3: `wave_index_health` description includes the `graph.<layer>.last_built_at` / `node_count` / `edge_count` block.
- [ ] AC-4: `wave_graph_report` description documents the three new collision-diagnostic fields + the deprecated alias.
- [ ] AC-5: `wave_graph_report` description documents the empty-section `*_candidates_total` / `*_threshold` diagnostics.
- [ ] AC-6: `wave_graph_report` description has prose for the four parameters (`exclude_external`, `exclude_generated`, `collapse_generated_files`, `collapse_class_module_pairs`).
- [ ] AC-7: `code_impact` description's `affected` field listing includes `hop` and `community_id`; edge listing includes `confidence`.
- [ ] AC-8: `code_callhierarchy` description's response items include `community_id`; the AOP/advice empty-incoming pointer is present.
- [ ] AC-9: `code_graph_community` description includes `community_size_class` and `large_community_advisory`.

**seed-211 restructure (Workstream B):**

- [ ] AC-10: seed-211 has a dedicated `wave_graph_report` subsection (not a bullet); the "Tool Selection Quick Rules" entry is a one-line pointer.
- [ ] AC-11: seed-211 has a dedicated `code_graph_community` subsection (not a bullet); the "Tool Selection Quick Rules" entry is a one-line pointer.
- [ ] AC-12: The verification trigger formula for collision diagnostics is callout-formatted (visually scannable).

**Confidence-level guidance (Workstream C):**

- [ ] AC-13: seed-211 documents `RECEIVER_RESOLVED` and `EXTRACTED` semantics under `code_impact`, `code_callhierarchy`, and `code_graph_path`.
- [ ] AC-14: seed-211 includes filtering guidance for high-stakes questions (refactor safety / security review) — prefer `RECEIVER_RESOLVED`.
- [ ] AC-15: seed-211 documents `min_confidence` parameter status (exists / planned / won't ship) per Decision Log resolution.

**Process / packaging:**

- [ ] AC-16: MCP `list_tools` after a server restart returns the updated descriptions (manual verification via `wave_mcp_reload` + spot-check).
- [ ] AC-17: `RELEASE_NOTES.md` notes the doc-sync release.
- [ ] AC-18: `docs-lint` passes via post-edit hook.

## Tasks

- [ ] Phase 0 — decide `min_confidence` parameter status (exists / planned / won't ship); record in Decision Log
- [ ] Open `seed_edit_allowed` gate
- [ ] Workstream B: restructure seed-211 — promote `wave_graph_report` and `code_graph_community` to subsections
- [ ] Workstream C: add confidence-level guidance to seed-211 under `code_impact` / `code_callhierarchy` / `code_graph_path`
- [ ] Close `seed_edit_allowed` gate
- [ ] Open `framework_edit_allowed` gate
- [ ] Workstream A: update FastMCP tool description strings in `server_impl.py` for all 6 tools
- [ ] Update `RELEASE_NOTES.md`
- [ ] Close `framework_edit_allowed` gate
- [ ] Restart MCP server; verify `list_tools` reflects updates
- [ ] Mark change `implemented`
- [ ] Repackage; field-verify via tool-description spot-check from a fresh agent context

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| seed-211-restructure (B) | Engineering | — | Pure docs; independent |
| confidence-guidance (C) | Engineering | phase-0 (`min_confidence` decision) | Pure docs; independent of A |
| tool-description-sync (A) | Engineering | — | Code edits to `server_impl.py`; can land in parallel with B/C |
| release-notes | Engineering | A + B + C | Last; describes what shipped |

## Serialization Points

- seed-211 file — both Workstream B and C edit the same file; serialize or coordinate edits.
- `server_impl.py` — single file holding all tool descriptions; all six per-tool edits in Workstream A coordinate here.

## Affected Architecture Docs

- N/A — this is documentation sync, not architectural change. The shipped behavior is already documented in seed-211 and verified; this change closes the gap between seed and tool surface.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Most-impactful single drift — `graph` value invisible to agents |
| AC-2 | required | Operator-facing graph orientation |
| AC-3 | required | Health surface for the graph layer |
| AC-4 | required | Collision-diagnostic operator interpretation |
| AC-5 | required | Empty-section diagnostics |
| AC-6 | required | Parameter prose — currently missing |
| AC-7 | required | Confidence + community surface on `code_impact` |
| AC-8 | required | Community surface on `code_callhierarchy` |
| AC-9 | required | Community size diagnostics |
| AC-10 | required | seed-211 scanability |
| AC-11 | required | seed-211 scanability |
| AC-12 | important | Callout formatting — scannability win |
| AC-13 | required | Confidence semantics — direct agent guidance |
| AC-14 | required | Filtering guidance for high-stakes questions |
| AC-15 | required | `min_confidence` parameter clarity |
| AC-16 | required | Verification — descriptions actually reach the MCP surface |
| AC-17 | required | Release-notes hygiene |
| AC-18 | required | Lint gate |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Bundle Workstreams A + B + C in one change | All touch the same agent-discoverable contract; splitting would leave the surface partially-current for the period between ships | Separate changes per workstream (rejected — partial-current state is worse than batched ship) |
| 2026-06-01 | Field 5 (RELEASE_NOTES in dist) closed without action | Verified `RELEASE_NOTES.md` is in `wavefoundry-1.2.1.319y.zip` at the expected path; seed-240 step is honored | (no alternative — already correct) |
| 2026-06-01 | Tool description hot-reload not in scope | Description-string changes likely need full MCP server restart per FastMCP wrapper-signature cache (same limitation observed in wave 130rj and 13129) | Implement description hot-reload (out of scope — separate feature) |
| 2026-06-01 | seed-160 unchanged | Upgrade-workflow surface stays at seed-160; only the one-line operator hint goes to `wave_index_build`'s description | Move semantic-vs-graph orientation entirely to the tool description (rejected — over-fragments documentation) |
| TBD (Phase 0) | `min_confidence` parameter status | (to be filled at Phase 0) | exists / planned / won't ship |

## Risks

| Risk | Mitigation |
|---|---|
| Description-string changes don't hot-reload — operators on a long-running session don't see updates until restart | Document restart requirement in `RELEASE_NOTES.md`; `wave_mcp_reload` covers most cases but not signature/description changes |
| seed-211 restructure breaks anchors / inbound links from other seeds | Audit references to the restructured bullets before promoting to subsections; preserve old anchor IDs if links exist |
| Confidence-level guidance commits to a model (`RECEIVER_RESOLVED` semantics) that shifts when `1319s` lands and introduces `CONSTRUCTION_RESOLVED` | Write the guidance as extensible — describe the current two levels with a "future levels may include..." note |
| Tool description strings exceed FastMCP's display-friendly length, getting truncated in some clients | Keep description prose tight; reference seed-211 subsections for full guidance rather than inlining |
| `min_confidence` clarification commits to a parameter that doesn't ship and creates a wait-for-it expectation | Phase 0 decides the status before guidance is written; mark "planned" only if there's intent to ship within 2 waves |

## Related Work

- Direct response to Solaris field feedback dated 2026-06-01 (this conversation).
- Companion to `1319s` (construction-call edges to class node) — once `1319s` lands, the `CONSTRUCTION_RESOLVED` confidence level adds to the guidance written here. Decide whether to ship docs before or after `1319s`:
  - Before: confidence guidance includes "future levels may include `CONSTRUCTION_RESOLVED` when construction-edge attribution lands"
  - After: confidence guidance includes `CONSTRUCTION_RESOLVED` as a shipped level
- Closes the structural gap where 1.2.x features shipped to implementation + seed-211 but not to tool descriptions. Establishes the convention that tool description = agent-discoverable contract.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
