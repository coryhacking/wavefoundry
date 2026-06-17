# Project codebase map — hierarchical, scales gracefully at any size

Change ID: `1p5tl-enh project-codebase-map`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Completed At: 2026-06-16
Last verified: 2026-06-16
Wave: `1p5x8 large-codebase-map`

## Rationale

The large-codebase best-practices guidance recommends giving agents a **codebase map** so they orient by scanning structure before opening files, instead of grep-thrashing. This is the framework's core job — wavefoundry already indexes the **destination project's** code (chunker, indexer, graph_indexer) and exposes it via the `code_*` tools — but there is no single at-a-glance *map* of the project an agent can read at session start to know "what lives where" before issuing queries.

This applies to a project of **any size** — small, medium, or large. The map generates for whatever is indexed (no size gate) and is **right-sized**: a small repo yields a compact, near-flat map; a large one yields a bounded top-level view with drill-down. The design requirement is therefore not "a map," it is a **compact, hierarchical orientation layer that scales gracefully**: a small top-level view of domains/areas and their entry points, with **leveled drill-down** into scoped sub-maps on demand, and an explicit handoff to the `code_*` tools for depth. The map is the *index to the index* — it routes the agent to the right community/area; the existing tools provide the detail. Built offline from the persisted graph + `graph_cluster` artifacts, it inherits multi-language support and is a genuine, defensible asset (the persisted graph is something Claude Code / Cursor do not have).

The value is *highest* — and the design hardest — in **extra-large enterprise repositories** that don't fit in context, where a naive flat dump of every package/symbol recreates the haystack one level up. So XL is the **stress case the design must survive**, not the exclusive audience: the same generator must produce a useful small map and a bounded large one.

## Requirements

1. **Target = the destination project's code.** The map describes the codebase the framework is indexing (the consuming project), across whatever languages the index supports — never the framework internals.
2. **Generated offline from the persisted index/graph.** Derived from artifacts the framework already builds — the graph and the `graph_cluster` cluster artifact (communities + labels + degree-ranked hubs + boundary nodes), plus file inventory and symbol outlines — without a live server and without a separate re-parse. No hardcoded project-specific paths/names. Read-only consumer → no `GRAPH_BUILDER_VERSION` bump; track `CLUSTER_BUILDER_VERSION` for staleness.
3. **Hierarchical + bounded (the load-bearing requirement).** The top-level map is **compact and size-bounded** regardless of repo size — top-level domains/areas (from the cluster hierarchy / package-to-directory collapse), each with a one-line responsibility and its key entry-point symbols. Lower detail is reached by **leveled drill-down** (scoped per-area sub-maps generated/retrievable on demand), with caps and paging. A monorepo with hundreds of communities must still yield a top-level map an agent can read in one screen.
4. **Drill-via-tools handoff.** Each area names the concrete next step to go deeper — e.g. the `community_id` / `hub_node_id` to pass to `code_graph_community`, or files to open with `code_outline` — so the map deliberately stops at orientation and routes to the tools for depth (no per-function summaries in the map).
5. **Ranking from real signals.** "Key" areas and symbols are ordered by signals already in the index (graph degree/centrality, hub nodes, boundary counts), not an ad-hoc heuristic.
6. **Refreshed with the index, throttled, not gated per-commit.** Regenerates as part of the index build/refresh lifecycle and on demand; freshness tracks the index. On huge repos, regeneration is throttled/bounded. It is a generated artifact bounded by index freshness — **not** a hard per-commit parity gate (noise for live project code).
7. **Generic + seed-rooted + discoverable.** Generator ships in the framework; output lands at a conventional, project-agnostic location (e.g. `docs/references/codebase-map.md` in the consuming project); discoverability woven into the seed-rendered orientation surface so agents consult it first. Generated artifact must be docs-lint-clean and inherit the index file-scoping (no gitignored/secret files mapped).

## Scope

**Problem statement:** Agents working in a consuming project of any size have powerful per-query `code_*` tools but no compact structural map to orient from at session start — so they grep-thrash; and at XL scale they can't hold the repo in context at all (where the map matters most and a naive map would itself become a haystack).

**In scope:**

- A generator (framework script) that builds a **hierarchical, bounded** map of the consuming project from its persisted graph + cluster artifacts, language-agnostic.
- Leveled drill-down: a compact top-level map + scoped per-area sub-maps (generated and/or retrievable on demand), with caps/paging.
- The drill-via-tools handoff (area → `community_id`/`hub_node_id`/key files for `code_*`).
- Output at a conventional location + refresh during the index build/refresh lifecycle (throttled) and on demand.
- Discoverability via the seed-rendered orientation surface; tests across sizes (small → compact map; large → bounded top-level output + drill-down; fail-safe on empty/partial index).

**Out of scope:**

- Mapping the framework's own `.wavefoundry/framework/scripts/` (explicitly not the target).
- A separate full re-parse independent of the index (reuse the index).
- Per-function summaries / full call-graph rendering in the map — the `code_*` tools serve depth; the map orients and routes.
- LLM-generated prose summaries of each area (the map uses cluster labels + ranked anchors; richer summaries are a possible later enhancement).
- A hard per-commit parity gate (freshness tracks the index instead).

## Acceptance Criteria

- [x] AC-1: Running the generator against an indexed project emits a **compact, hierarchical** top-level map of that project — domains/areas (from cluster hierarchy / package collapse) with one-line responsibilities and key entry-point symbols — derived offline from the persisted graph + cluster artifacts, across the languages the index supports.
- [x] AC-2 (**graceful scaling, required**): The map is right-sized at both ends — a **small** project yields a compact, near-flat map (no needless drill-down), and a **large** project (many communities) yields a top-level map that stays **size-bounded and readable** (caps/paging) with deeper detail via leveled drill-down (scoped sub-maps) + a named `code_*` drill-in step per area. Verified at both a small fixture and a synthetic large-graph fixture (no size gate; the same generator handles both).
- [x] AC-3: The map regenerates as part of the index build/refresh lifecycle (throttled) and on demand; freshness tracks the index (no hard per-commit parity gate). Output is deterministic for a fixed index/cluster artifact.
- [x] AC-4: The map lands at a conventional, project-agnostic location, is docs-lint-clean, inherits the index file-scoping (no gitignored/secret files), and is referenced from a seed-rendered orientation surface so agents consult it first; no project-specific values hardcoded.
- [x] AC-5: Generator tests cover area/hierarchy extraction, ranking from graph signals, right-sized output at both small and synthetic-large fixtures (+ drill-down), deterministic output, and fail-safe behavior on empty/partial/missing index/cluster artifact; full suite + docs-lint clean (tests run under `~/.wavefoundry/venv` python).

## Tasks

- [x] Implement the generator consuming the persisted graph + `graph_cluster` artifact: top-level areas + one-line responsibilities + ranked entry-point symbols + drill-in handles.
- [x] Implement leveled drill-down (scoped per-area sub-maps) with caps/paging so the top-level stays bounded at XL scale.
- [x] Wire regeneration into the index build/refresh lifecycle (throttled) + an on-demand entry point.
- [x] Choose the conventional output location; ensure docs-lint-clean + file-scoping inheritance; add seed-rendered discoverability (orientation surface).
- [x] Add generator tests incl. a synthetic large-graph fixture (bounded output, drill-down, ranking, determinism, empty/partial fail-safe); full suite + docs-lint.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| generator  | Engineering | —          | top-level map from graph+cluster artifacts + ranking |
| drilldown  | Engineering | generator  | leveled sub-maps + caps/paging (XL-scaling) |
| lifecycle  | Engineering | generator  | throttled regenerate on index build/refresh + on demand |
| discovery  | Engineering | generator  | output location + docs-lint/scoping + seed orientation pointer |


## Serialization Points

- Drill-down, lifecycle, and discovery all depend on the generator's output contract (hierarchy shape + location + format), so they follow the generator.

## Affected Architecture Docs

A short note in `docs/architecture/graph-index-system.md` describing the map as a generated, hierarchical, read-only consumer of the graph/cluster artifacts, plus a pointer in `docs/references/project-overview.md` (orientation). No change to index/retrieval contracts.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The hierarchical top-level map is the deliverable. |
| AC-2 | required | The map must be right-sized at every scale; one that doesn't stay bounded at scale fails exactly where it matters most. |
| AC-3 | required | Index-tracked, throttled refresh keeps it current without per-commit gate noise. |
| AC-4 | required | Undiscoverable / lint-failing / secret-leaking map is unusable; location + scoping + pointer are load-bearing. |
| AC-5 | required | Correctness, XL-bounded output, determinism, and fail-safe must be tested. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-16 | Prepare spike: `graph_cluster.py` already persists a cluster artifact (communities with `label`/`node_ids`/`node_count`/`boundary_node_count`; degree-ranked `community_hub_node_id` + top members), and `wave_graph_report` already supports `collapse_package_to_directory` (package/namespace aggregation). Map generator consumes these offline — top-level areas ← communities/packages, key symbols ← hubs/top-degree, key files ← members' `source_file`, drill-in handle ← `community_id`/`hub_node_id`. Read-only → no `GRAPH_BUILDER_VERSION` bump; track `CLUSTER_BUILDER_VERSION`. | `graph_cluster.py`, `server_impl.py` (graph report), `docs/architecture/graph-index-system.md` |
| 2026-06-16 | Split out of `1p5tg` into its own wave (`1p5x8`) after the archetype value-council; XL-scaling (hierarchical, bounded, drill-via-tools) promoted to a first-class requirement (AC-2). | archetype council, this session |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-15 | Map the destination project's code, generated from the existing index/graph | The framework's job is the consuming project; reusing the index avoids a second parser and inherits multi-language support | Map the framework's own scripts (rejected — wrong target per operator); a standalone AST parse (rejected — duplicates the indexer, loses graph signal) |
| 2026-06-16 | Hierarchical + bounded top-level map with leveled drill-down, not one flat artifact | A flat map of an XL monorepo recreates the haystack at the map level; the map must route, not dump. This is the reason for the standalone wave | Single monolithic map (rejected — fails at XL, the case that justifies the feature); no map, lean on `code_*` only (rejected — no at-a-glance entry point for orientation) |
| 2026-06-16 | Source areas/symbols from the persisted `graph_cluster` artifact (communities + degree hubs) + package collapse, not an ad-hoc heuristic | The cluster artifact already provides labeled communities + ranked hubs offline; reuse beats re-deriving and keeps ranking principled | Recompute clustering in the generator (rejected — duplicates `graph_cluster`); directory-only grouping (kept as fallback when no cluster artifact exists) |
| 2026-06-16 | Refresh with the index (throttled); no hard per-commit parity gate | Project code changes constantly; a parity gate would be perpetual noise. Freshness tracking the index is the right bound | Per-commit regenerate-and-diff gate (rejected — noisy for live project code) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Map is unreadable / unbounded at XL scale (the core risk) | Hierarchical, size-bounded top-level + leveled drill-down + caps/paging; AC-2 verifies bounded output on a synthetic large-graph fixture |
| `graph_cluster` communities are too coarse/fine or labels weak on a real enterprise repo | Use package-to-directory collapse + cluster hierarchy together; degrade to directory grouping when labels/communities are poor; treat labels as hints, not authoritative |
| Regeneration too costly on huge repos | Throttle to the index lifecycle; bound work; reuse persisted artifacts (no re-parse, no live model) |
| Map goes stale vs the code | Regenerate on index build/refresh; surface freshness with the index's own staleness signals |
| Generator fails on a partial/missing index/cluster artifact | Fail-safe: degrade to whatever exists (directory grouping) or skip with a clear note; tested on empty/partial inputs |
| Map leaks gitignored/secret paths | Inherit the index file-scoping (the index already excludes gitignored); never read outside it |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
