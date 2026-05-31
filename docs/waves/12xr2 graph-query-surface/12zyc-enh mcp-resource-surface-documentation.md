# MCP Resource Surface Documentation and Expansion

Change ID: `12zyc-enh mcp-resource-surface-documentation`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-30
Wave: 12xr2 graph-query-surface

## Rationale

The MCP server exposes 10 resources and resource templates (`wavefoundry://seed/{slug}`, `wavefoundry://architecture/{slug}`, etc.) that are already implemented in `server_impl.py` but are invisible to agents working from the primary MCP reference. `docs/specs/mcp-tool-surface.md` has zero mention of resources — agents reading the spec have no way to discover they exist. `AGENTS.md` documents them, but subagents spawned with focused role prompts (guru, implement-feature) do not load `AGENTS.md` and therefore never learn to use resources instead of equivalent tool calls. Three high-value resources are also absent from the implementation: combined index status, the AGENTS guide, and a wave-list summary.

The problem is documentation placement, not documentation existence. The fix is to put the resource catalog where agents actually look, add the three missing resources, and compact `AGENTS.md` so it is lean enough to serve as a useful attached resource itself.

`AGENTS.md` pass 1 (deleting five dead planning sections totalling ~85 lines) was completed before this change was implemented. Pass 2 — collapsing inline MCP tool-detail prose to pointers to `docs/specs/mcp-tool-surface.md` — is included here as a sequenced step that must follow AC-1 so the pointer destination exists before the source is removed.

## Requirements

1. `docs/specs/mcp-tool-surface.md` must contain a dedicated "MCP Resources" section listing all stable resources and resource templates with their URIs, content, and when-to-use guidance relative to equivalent tools.
2. The guru seed (`211-guru.prompt.md`) must reference resources at the point where it directs agents to read seeds and architecture docs, with a clear use-case split: use `wavefoundry://seed/{slug}` or `wavefoundry://architecture/{slug}` when attaching raw content as context; use `seed_get()` or `wave_get_change()` when a structured envelope with `diagnostics` and `next_tools` is needed for error recovery.
3. The implement-feature seed (`180-implement-feature.prompt.md`) must reference the resource surface at the session-orientation step so implementers know stable context is attachable without tool calls.
4. `wavefoundry://index/status` must be registered as a stable resource returning a markdown summary of combined semantic + graph index health (present/absent, counts, builder version, last-modified) by reading index artifact headers — no embedding traversal or edge computation.
5. `wavefoundry://agents` must be registered as a stable resource returning the content of `AGENTS.md` (the primary agent operating guide).
6. `wavefoundry://waves` must be registered as a stable resource returning a markdown summary of all wave records and their statuses, equivalent to `wave_list_waves()` formatted as markdown.
7. `AGENTS.md` "MCP Resources and Resource Templates" section must be updated to include the three new resources and to note that full resource documentation lives in `docs/specs/mcp-tool-surface.md`.
8. After AC-1 is complete, the inline MCP tool-detail prose in `AGENTS.md` — specifically the `code_ask` retrieval signal notes, `wave_new_*` tool docs, session handoff tool descriptions, edit gate tool descriptions, Codex server selection notes, search mode transparency note, and the Code Navigation per-tool listing — must be replaced with pointer lines to `docs/specs/mcp-tool-surface.md`; the MCP Server setup command, per-host registration table, stdio entry, graph index note, and quick-chooser list must be retained.

## Scope

**Problem statement:** MCP resources are implemented but undiscovered. Agents reading the tool surface spec find no mention of resources; subagents with role-scoped prompts miss them entirely because they don't load `AGENTS.md`. Three useful ambient-status resources are also absent from the implementation.

**In scope:**

- `docs/specs/mcp-tool-surface.md` — new "MCP Resources" section with full URI table, content descriptions, and when-to-use vs. tools guidance
- `.wavefoundry/framework/seeds/211-guru.prompt.md` — add resource preference note at seed/arch-doc read steps
- `.wavefoundry/framework/seeds/180-implement-feature.prompt.md` — add resource note at session-orientation step
- `AGENTS.md` — add three new resources to the existing list; add cross-reference to mcp-tool-surface.md; collapse inline tool-detail prose to pointers (pass 2, after AC-1)
- `server_impl.py` — register `wavefoundry://index/status`, `wavefoundry://agents`, `wavefoundry://waves`
- `docs/architecture/current-state.md` and `data-and-control-flow.md` — add three new resources to the resource lists already present there

**Out of scope:**

- Changing the resource implementation pattern (all new resources follow the existing `@mcp.resource` + return-string convention)
- Adding resources for individual wave changes, journal entries, or ADRs — existing templates cover parameterized reads
- Deprecating or replacing existing tool equivalents — resources and tools coexist; resources are not wrappers

## Acceptance Criteria

- [x] AC-1: `docs/specs/mcp-tool-surface.md` contains a "MCP Resources" section that lists all 13 resources (10 existing + 3 new) with URI, content summary, MIME type, equivalent tool (if any), and a "prefer resources when / prefer tools when" guidance block.
- [x] AC-2: The guru seed references `wavefoundry://seed/{slug}` and `wavefoundry://architecture/{slug}` at the point where it describes how to read seed and architecture content; the guidance includes the use-case split: resource = ambient content attachment (no structured envelope needed); tool = query requiring `diagnostics`/`next_tools` for error recovery.
- [x] AC-3: The implement-feature seed references the resource surface at the session-orientation step, naming at least `wavefoundry://overview`, `wavefoundry://wave/current`, and `wavefoundry://agents` as attachable context.
- [x] AC-4: `wavefoundry://index/status` is listed by `ListResources` and returns a markdown block with semantic index present/absent, graph index present/absent, graph node/edge/file counts, GRAPH_BUILDER_VERSION, and graph artifact path; no tool call or traversal is required.
- [x] AC-5: `wavefoundry://agents` is listed by `ListResources` and returns the full text of `AGENTS.md`; returns a `# Not Found` message if the file is absent.
- [x] AC-6: `wavefoundry://waves` is listed by `ListResources` and returns a markdown summary formatted as: one `##` heading per wave (wave ID as heading text), wave status on the first line, followed by a bullet list of admitted changes each showing change ID and status.
- [x] AC-7: `AGENTS.md` "MCP Resources and Resource Templates" section lists all 13 resources and includes a one-line cross-reference to `docs/specs/mcp-tool-surface.md` for full documentation.
- [x] AC-8: `AGENTS.md` inline MCP tool-detail sections are replaced with pointer lines to `docs/specs/mcp-tool-surface.md`; retained sections are: MCP Server setup command, per-host registration table, stdio entry, graph index note, quick-chooser list; removed sections are: `code_ask` retrieval signal notes, `wave_new_*` docs, session handoff tool descriptions, edit gate tool descriptions, Codex server selection notes, search mode transparency note, Code Navigation per-tool listing; resulting file is ≤ 320 lines.

## Tasks

- [x] Add "MCP Resources" section to `docs/specs/mcp-tool-surface.md` covering all 10 existing resources + 3 new ones; include URI table, MIME type, content, equivalent tool, and when-to-prefer-resource guidance
- [x] Open `seed_edit_allowed` gate; add resource preference note to guru seed (211) with resource-vs-tool use-case split (resource = content attachment, tool = structured recovery); add resource orientation note to implement-feature seed (180) at session-start step; close gate; run `wave_mcp_reload` to pick up seed changes
- [x] Open `framework_edit_allowed` gate; register `wavefoundry://index/status` in `server_impl.py` — read graph payload header + check semantic index presence; format as markdown; close gate
- [x] Open `framework_edit_allowed` gate; register `wavefoundry://agents` in `server_impl.py` — read `AGENTS.md` from repo root; close gate
- [x] Open `framework_edit_allowed` gate; register `wavefoundry://waves` in `server_impl.py` — call `list_waves(root)` and format result as markdown; close gate
- [x] Update `AGENTS.md` stable-resources list to include the three new URIs; add cross-reference line to mcp-tool-surface.md
- [x] Update `docs/architecture/current-state.md` and `data-and-control-flow.md` resource lists to include the three new URIs
- [x] After AC-1 is complete: remove inline MCP tool-detail prose from `AGENTS.md` (code_ask retrieval notes, wave_new_* docs, session handoff tool descriptions, edit gate tool descriptions, Codex server selection notes, search mode transparency note, Code Navigation per-tool listing); replace each removed block with a one-line pointer to `docs/specs/mcp-tool-surface.md`; verify file is ≤ 320 lines
- [x] Run `docs-lint` and framework tests; verify `ListResources` response includes all 13 entries

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| mcp-tool-surface.md docs | implementer | — | Pure doc; no gate needed; do first so spec is complete before seeds reference it |
| AGENTS.md resource list + arch doc updates | implementer | mcp-tool-surface.md docs | Adds cross-reference and new resources after spec exists |
| Seed updates (guru + implement-feature) | implementer | mcp-tool-surface.md docs | Both seeds in one gate window; seed_edit_allowed |
| server_impl.py: all three resources | implementer | — | One framework_edit_allowed gate window for all three registrations |
| AGENTS.md pass 2 compaction | implementer | mcp-tool-surface.md docs | Depends on spec being complete; pointer destination must exist before source is removed |
| Tests + lint | qa | all workstreams | Run after all implementation tasks |

## Serialization Points

- Seed edits share the `seed_edit_allowed` gate — open once, make both seed edits, close once
- All three `server_impl.py` resource registrations can be done in a single `framework_edit_allowed` gate window
- AGENTS.md pass 2 compaction must follow AC-1 completion — do not remove inline tool-detail prose before the pointer destination (`docs/specs/mcp-tool-surface.md` MCP Resources section) is written

## Affected Architecture Docs

- `docs/architecture/current-state.md` — resource list in MCP topology diagram needs three new entries
- `docs/architecture/data-and-control-flow.md` — "Stable resources" list in MCP control-flow section needs three new entries

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | mcp-tool-surface.md is the canonical MCP reference; absence of resources there is the root discoverability failure |
| AC-2 | required | Guru subagents are the most frequent consumers of seed and arch doc content; teaching them to use resources reduces tool-call overhead |
| AC-3 | important | Implementers benefit from knowing resources exist at session start; lower priority than guru since orientation is lighter-weight |
| AC-4 | important | Index status is the most-needed ambient check at session start; agents currently must call wave_index_health() as a tool |
| AC-5 | important | AGENTS.md is the primary operating guide; exposing it as a resource makes it directly attachable without a file read tool |
| AC-6 | nice-to-have | Wave list as a resource is convenient but wave_list_waves() already works well |
| AC-7 | required | AGENTS.md must stay consistent with the spec once AC-1 lands |
| AC-8 | required | AGENTS.md compaction makes the resource usable — a 420-line file as an attached resource is marginal; ≤ 320 lines is the target |

## Progress Log

| Date | Update | Evidence |
|---|---|---|
| 2026-05-30 | Change doc created; root cause identified: mcp-tool-surface.md has zero resource mentions despite 10 resources implemented in server_impl.py | `grep -n "resource" docs/specs/mcp-tool-surface.md` returned no matches; AGENTS.md lines 312–336 have full list that role-scoped subagents never see |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-30 | Document resources in mcp-tool-surface.md rather than creating a separate spec | Single canonical MCP reference is better than split docs; resources and tools are the same server contract | Separate mcp-resource-surface.md (more files, more cross-link maintenance) |
| 2026-05-30 | wavefoundry://index/status reads headers only, no traversal | Resources must be cheap to read; wave_graph_report / wave_index_health are the right tools for full metrics | Call wave_index_health() implementation inline (would duplicate tool behavior inside a resource) |
| 2026-05-30 | AGENTS.md pass 2 compaction sequenced after AC-1, not as a separate change | The pointer destination must exist before the source is removed; same change keeps the two in sync; splitting risks a broken-pointer window | Separate maintenance change for AGENTS.md compaction |

## Risks

| Risk | Mitigation |
|---|---|
| Seed edits change agent behavior; could cause prompt regressions | Edits are additive only — new guidance block appended to existing section; no existing text removed; run smoke tests after |
| wavefoundry://waves calls list_waves() which reads the filesystem | list_waves() already used by wave_current and wave_list_waves tools; no performance complaints at current repo scale |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
