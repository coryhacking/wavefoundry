# Codebase map MCP surface (resource + index-build refresh)

Change ID: `1p601-enh codebase-map-mcp-surface`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Wave: `1p5x8 large-codebase-map`
Last verified: 2026-06-16

## Rationale

The codebase map already stays fresh through normal flows (auto-regen on `setup_index.build_index`; refreshed via the freshness monitor / git hooks / `wave_index_build`) and is readable as a doc. But there is no MCP-native way to (a) **force a map-only refresh** without a full index rebuild, or (b) get the map **served fresh as a resource** — agents otherwise drop to `python gen_codebase_map.py`, which is inconsistent with the framework's MCP-first posture. Add a thin MCP surface for both, without duplicating the `code_*` graph tools (which already do per-area depth).

Deliberately **not** a heavy new query tool (`code_map(area=…)` would overlap `code_graph_community`). Two thin additions only.

## Requirements

1. **Resource `wavefoundry://codebase-map`.** Read-only, served from the generated `docs/references/codebase-map.md` (regenerating on demand if missing/stale, fail-safe), mirroring the existing `wavefoundry://graph/*` resource pattern. Agents get the orientation map without knowing the file path.
2. **Map-only refresh via the existing `wave_index_build`.** Add a `content="map"` option that runs `gen_codebase_map.generate_safe` (the ~0.09 s map-only regen) without a full index rebuild — fail-safe (never raises), reuses the existing tool surface (no new tool).
3. **Decouple map regen from the index build; trigger at lifecycle + on-demand + on-read (revised — was "relocate the hook into the build").** The map lives in the **indexed** `docs/references/` tree, so regenerating it on every index build creates a self-referential write→reindex loop (and forced `_settle()` scaffolding across 9 indexer tests). The map structure also changes slowly. So **remove the index-build hook entirely** (out of `indexer.py::build_index` and `setup_index.py`) and regenerate at the moments that matter: (a) **prepare-wave and close-wave** (lifecycle checkpoints — fresh map + committed artifact), (b) **on upgrade** (one explicit regen so a fresh install has it — fixes teton's "not generated on upgrade"), (c) **on-demand** via `wave_index_build(content="map")` + the CLI, (d) **on-read, lazily** — the `wavefoundry://codebase-map` resource regenerates-if-stale (fingerprint-gated). All fail-safe. Revert the `_settle()` indexer-test scaffolding added for the removed hook.
4. **No heavy query tool.** Do not add a per-area query tool; the map is the overview, `code_graph_community`/`code_outline` provide depth.
5. **Generic + seed-rooted docs + reconnect caveat.** Document the resource + the `content="map"` option in the relevant seed/prompt surfaces (the MCP tool catalog), and note that **new MCP tools/resources require a server reconnect** to appear (FastMCP limitation).
6. **Change-only / idempotent — no-op when nothing changed.** A regeneration on an unchanged codebase must NOT write the file, bump its `Last verified` date, or dirty git. Two-level guard: (a) **skip the render** when the inputs are unchanged since the last generation — cheap fingerprint over the graph + cluster artifacts **and** the per-area `AGENTS.md` (a Tier-2 input: renaming an area must trigger an update); (b) **skip the write** when the rendered content (ignoring the volatile date line) matches the existing file — **preserve the existing date** in that case. The same change-only rule applies to the `repo-index` marker block (rewrite only when its structural content changes) and to `AGENTS.md` scaffolding (already never-overwrite). Net: a build with no relevant change is a true no-op.

## Scope

**In scope:** the `wavefoundry://codebase-map` resource; the `wave_index_build` `content="map"` refresh path; tests; seed/catalog doc updates (incl. the reconnect note).

**Out of scope:** a per-area query tool; changing the generator's output (that is `1p5tl`/`1p5zr`); changing index/retrieval contracts.

## Acceptance Criteria

- [x] AC-1: `wavefoundry://codebase-map` resource returns the current map (served fresh; regenerates fail-safe if missing); registered alongside the existing graph resources.
- [x] AC-2: `wave_index_build(content="map")` regenerates the map only (fast, fail-safe, no full rebuild); other `content` values unchanged.
- [x] AC-2b: Map regen is **decoupled from the index build** (no hook in `indexer.py`/`setup_index.py`; `_settle()` test scaffolding reverted) and instead fires at **prepare-wave + close-wave**, **on upgrade**, **on-demand** (`content="map"`/CLI), and **lazily on resource read** (regenerate-if-stale). Verified: a prepare and a close regenerate the map; an `indexer.py` build does NOT (no write→reindex loop); upgrade produces it. All fail-safe.
- [x] AC-3b: Change-only / idempotent — a regeneration with unchanged inputs writes nothing (no file write, no `Last verified` bump, no git churn): render is skipped when the graph/cluster/area-`AGENTS.md` fingerprint is unchanged, and the write is skipped when content (modulo the date line) matches, preserving the existing date. Verified by a test that a second back-to-back generate produces a byte-identical file and no write. The repo-index marker block follows the same rule.
- [x] AC-3: Docs/catalog updated (resource + option + the reconnect caveat); tests cover the resource + the refresh path; full suite + docs-lint clean.

## Tasks

- [x] Register the `wavefoundry://codebase-map` resource (mirror `resource_graph_communities`).
- [x] Add `content="map"` to `wave_index_build` → `gen_codebase_map.generate_safe`, fail-safe.
- [x] Update the MCP tool/resource catalog docs + reconnect note; add tests; full suite + docs-lint.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The served resource is the MCP-native read path. |
| AC-2 | required | Map-only refresh is the "don't run python" gap closer. |
| AC-2b | required | Without the hook relocation the map silently drifts stale on the common refresh paths (monitor/git-hooks) — this is the real freshness fix. |
| AC-3b | required | Without change-only writes, regen-on-every-build-path would churn the file/date/git constantly — idempotence is what makes "regenerate everywhere" safe. |
| AC-3 | required | Discoverability + reconnect caveat + tests. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-16 | Operator approved adding an MCP surface so the map doesn't require running python directly. Chose the thin form (resource + `wave_index_build content="map"`), not a heavy query tool (would overlap `code_graph_community`). | this session |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-16 | Resource + `content="map"` refresh, not a new query tool | The map already auto-regens + is readable; the real gaps are served-fresh access + map-only refresh; reuse existing surfaces | A `code_map(area=…)` tool (rejected — overlaps `code_graph_community`); CLI-only (rejected — not MCP-first) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| New resource/tool option not visible until reconnect | Documented reconnect caveat (FastMCP limitation) |
| Map-only refresh raises into the tool | `generate_safe` is fail-safe; wrap the tool path |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
