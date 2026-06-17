# Per-area AGENTS.md MCP resource (convenience read layer over the files)

Change ID: `1p662-enh per-area-agents-mcp-resource`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Completed At: 2026-06-17
Last verified: 2026-06-17
Wave: `1p65k codebase-map-round3`

> Operator-directed addition (with `1p661`). A resource template that serves a per-area `AGENTS.md` on demand — a convenience layer OVER the on-disk files, NOT a replacement (the file stays the indexed, vendor-neutral, human-editable source of truth; see `1p661` + memory `project-codebase-map-roi`).

## Rationale

The on-disk per-area `AGENTS.md` is the source of truth (indexed → surfaces ambiently in `code_ask`/`docs_search`; vendor-neutral; human-editable). A read-only MCP **resource** that returns a given area's `AGENTS.md` content is a useful additive affordance for MCP hosts that prefer an explicit context attach — mirroring how `wavefoundry://codebase-map` serves the generated map and `wavefoundry://change/{id}` serves a change doc. It does NOT replace the file (resource-only would lose indexing, vendor-neutrality, and the non-MCP/human audience — the file's whole value).

## Requirements

1. A read-only resource template (e.g. `wavefoundry://area/{area}` where `{area}` is the area's representative path or stable `area_id`) returns the on-disk `AGENTS.md` at that area's representative path, as raw markdown. Resolved from the codebase-map area model so `{area}` matches what the map exposes (`area_id` / `representative_path` from `gen_codebase_map.compute_areas`).
2. **File is source of truth.** The resource READS the on-disk file; it never synthesizes/auto-authors content (synthesized content would be redundant with `code_ask`/`code_outline` — the explicit non-goal). A missing/un-authored area returns a clear `# Not Found`-style markdown message (matching the existing missing-resource convention), never an error.
3. Optionally, a companion stable resource or the existing map already lists areas; if helpful, surface the area→`AGENTS.md` availability in the map/`wavefoundry://codebase-map` (read first to discover area keys). Keep it minimal — reuse the map for discovery rather than a new catalog if the map already carries the links.
4. Mirror the existing resource/template registration + envelope conventions (`server_impl.py`, alongside `wavefoundry://codebase-map` and the `wavefoundry://change/{id}` template); read-only; fail-safe; reconnect caveat noted (new resources need an MCP reconnect, per the hot-reload limitation).
5. Generic; docs updated (MCP tool/resource catalog in `AGENTS.md` MCP section + `docs/specs/mcp-tool-surface.md` MCP Resources + the framework seeds for those surfaces, seed-first); tests cover the resolve + the not-found path.

## Scope

**In scope:** `server_impl.py` resource template `wavefoundry://area/{area}` (resolve area → representative path → read `AGENTS.md`; fail-safe not-found); catalog/docs updates (seed-first: the seed that renders the MCP surface lists, plus `docs/specs/mcp-tool-surface.md` and the `AGENTS.md` MCP Resources block); tests.

**Out of scope:** authoring the content (sibling `1p661`); changing the on-disk-file model or indexing; any auto-synthesis of area context.

## Acceptance Criteria

- [x] AC-1: `wavefoundry://area/{area}` returns the on-disk `AGENTS.md` for the resolved area (by `area_id` or representative path) as raw markdown; resolution uses the codebase-map area model so keys match the map.
- [x] AC-2: An area with no authored `AGENTS.md` returns a clear `# Not Found`-style markdown message (not an error); the resource never synthesizes content. Read-only; fail-safe.
- [x] AC-3: Catalog/docs updated (MCP Resources section in `docs/specs/mcp-tool-surface.md` + `AGENTS.md` MCP block + the rendering seed, seed-first) including the reconnect caveat; tests cover resolve + not-found; full suite + docs-lint clean.

## Tasks

- [x] Register the `wavefoundry://area/{area}` resource template in `server_impl.py` (mirror `wavefoundry://codebase-map` / `wavefoundry://change/{id}`); resolve via the area model; read the on-disk `AGENTS.md`; fail-safe not-found.
- [x] Update the MCP resource catalog: `docs/specs/mcp-tool-surface.md` MCP Resources + the `AGENTS.md` MCP Resources block + the seed that renders those surfaces (seed-first).
- [x] Tests (resolve to an authored file; not-found path).
- [x] docs-lint + full suite.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` — add the `wavefoundry://area/{area}` resource template to the MCP Resources section.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The resource itself — explicit per-area context read for MCP hosts. |
| AC-2 | required | Fail-safe + never-synthesize (synthesized = redundant with live tools). |
| AC-3 | important | Discoverability + the reconnect caveat; tests lock the contract. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-17 | Operator: add a per-area MCP resource alongside the authoring instructions, as a convenience layer over the on-disk files (file stays source of truth + indexed). | memory `project-codebase-map-roi`; `wavefoundry://codebase-map` resource (1p601) as the pattern |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-17 | Resource COMPLEMENTS the on-disk file (reads it); does not replace it or synthesize content. | Resource-only loses indexing (ambient `code_ask`/`docs_search` retrieval — the delivery mechanism), vendor-neutrality, and the non-MCP/human audience; synthesized content is redundant with the live code tools. | Resource-instead-of-file (rejected — worse on every axis except file count); synthesize area context on read (rejected — redundant with `code_ask`/`code_outline`). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| New resource not visible until MCP reconnect (FastMCP hot-reload limitation). | Documented reconnect caveat in the catalog (consistent with prior new-tool/resource changes). |
| Area-key resolution drift (slug vs path). | Resolve via the same area model the map exposes (`area_id`/`representative_path`); not-found is fail-safe. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
