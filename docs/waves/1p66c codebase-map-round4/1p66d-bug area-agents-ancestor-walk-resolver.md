# Per-area AGENTS.md resolution walks up to the nearest ancestor (map link + area resource)

Change ID: `1p66d-bug area-agents-ancestor-walk-resolver`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-17
Wave: `1p66c codebase-map-round4`

## Rationale

`1p661`/`1p662` made per-area `AGENTS.md` an agent-drafted, indexed artifact, and the codebase map "links each area to its `AGENTS.md` when one exists" — but both surfaces resolve the file **only at the area's exact representative path**:

- `gen_codebase_map._area_context_rel_path(area)` (`gen_codebase_map.py:1253`) returns `<representative_path>/AGENTS.md` (or repo-root `AGENTS.md` for the synthetic `(root)` area). No walk-up.
- The `wavefoundry://area/{area}` resource (`server_impl.py:17822` `resource_area_context`) resolves via the same `gen._area_context_rel_path(match)` and checks only that exact path.

Field validation (teton, TS/Nx monorepo, round 4 on `1.7.0+p664`): the team authored 11 evidence-grounded per-area `AGENTS.md` at the conventional **Nx project roots** (`libs/backend/AGENTS.md`, `libs/ui/AGENTS.md`, `apps/aceiss/AGENTS.md`, …). None are linked by the map and none are served by the resource, because the areas' representative paths are deep subdirectories of those projects:

- area `buttons` → rep path `libs/ui/src/components/buttons` → looks for `libs/ui/src/components/buttons/AGENTS.md` (absent)
- area `packages` → rep path `libs/backend/.../opt/packages` → `wavefoundry://area/packages` returns "has no `AGENTS.md` yet at `libs/backend/src/lib/function/aceissCorePackages/opt/packages/AGENTS.md`"

The files **are** indexed and surface via `code_ask`/`docs_search` (verified — `libs/backend/AGENTS.md` is the top hit for a backend query), so the content lever works; only the map's routing link and the resource read miss it. Two structural facts make exact-path resolution wrong for real repos: (1) a single project (e.g. `libs/ui`) spawns several areas at different deep paths, so there is no single representative path at which to place one project-level `AGENTS.md`; (2) representative paths **churn between rebuilds** (round-4 `#4`), so requiring the file at the exact rep-path is a moving target. Walking up to the nearest ancestor `AGENTS.md` fixes both surfaces at once and is robust to rep-path churn.

## Requirements

1. A single shared resolver computes the per-area `AGENTS.md` location by walking **up** from the area's representative-path directory toward the repo root, returning the repo-root-relative path of the **nearest existing** `AGENTS.md` (filesystem-checked), or `None` when none is found in that ancestor chain.
2. Both surfaces consume the shared resolver: the map's `Area context:` link (`render_markdown`) and the `wavefoundry://area/{area}` resource (`resource_area_context`). No second copy of the resolution rule.
3. The synthetic `(root)` area resolves to the repo-root `AGENTS.md` exactly as today (no regression).
4. For a non-root area, the repo-root `AGENTS.md` is **not** used as the per-area fallback: the global root guide is already surfaced by the `(root)` area and as `wavefoundry://agents`, and linking it from every unrelated area is noise. The walk-up therefore searches ancestors strictly between the rep-path directory and the repo root (inclusive of intermediate project roots, exclusive of the repo root itself for non-root areas). This bound is the key behavioral decision (see Decision Log) — record it for prepare-council.
5. Resolution is **deterministic** (nearest-ancestor-first; no dependence on dict/set iteration order) so it is stable across rebuilds even while rep-paths churn (round-4 `#4`).
6. The resource's not-found / "author one" message still points at a sensible conventional location (the area's owning project root or representative path) so the authoring affordance is preserved; fail-safe behavior (unknown id → graceful not-found, codebase-map-unavailable → graceful) is unchanged.
7. Generic and vendor-neutral (no project-specific paths); seed-first only if a seed documents the exact-path rule (audit `030`/`050`/`160` and the resource catalog prose); docs updated where the resolution rule is described (`docs/specs/mcp-tool-surface.md` area-resource entry, `AGENTS.md` MCP Resources block); tests cover walk-up hit, nearest-wins, root-area, and not-found.

## Scope

**Problem statement:** Per-area `AGENTS.md` placed at the conventional project-root location (the documented, indexed convention) is invisible to both the map's area link and the `wavefoundry://area/{id}` resource, because both resolve only the area's exact (and churning) representative path.

**In scope:**

- A shared, root-aware, ancestor-walking resolver in `gen_codebase_map.py` (e.g. `_resolve_area_context_rel_path(root, area) -> str | None`) and the `_area_context_exists` / `_area_context_link_href` call sites updated to use it.
- `resource_area_context` in `server_impl.py` updated to resolve via the shared resolver (it already imports `gen_codebase_map` via `_load_script`).
- Not-found / authoring-hint message wording in the resource adjusted to remain helpful under walk-up.
- Tests in `test_gen_codebase_map.py`, `test_per_area_agents_context.py`, and `test_server_tools.py`.
- Docs/seed audit for any place that states the exact-rep-path rule.

**Out of scope:**

- Authoring `AGENTS.md` content (`1p661`); changing the scaffold location logic (still suggests rep-path / project root).
- The `#4` rep-path churn root cause itself — handled by sibling `1p66e` (this change is *robust to* the churn, it does not fix it).
- Any change to indexing of `AGENTS.md` files (already indexed; unchanged).
- "Owning project root" detection via `project.json`/`package.json` markers — the ancestor-walk by filesystem `AGENTS.md` presence subsumes it without a language/build-system dependency (kept generic). Revisit only if walk-up proves insufficient downstream.

## Acceptance Criteria

- [x] AC-1: An area whose representative path is a deep subdirectory of a directory that has an `AGENTS.md` resolves (link + resource) to that ancestor `AGENTS.md` (nearest-ancestor-wins when several ancestors have one). Verified by test with a fixture mirroring `libs/ui/src/components/buttons` → `libs/ui/AGENTS.md`. (`test_resolves_to_ancestor_when_not_at_rep_path`, `test_nearest_ancestor_wins`, `test_render_links_ancestor_file`, resource `test_area_resource_walks_up_to_ancestor_agents_md`.)
- [x] AC-2: Both the map's `Area context:` link and the `wavefoundry://area/{area}` resource return the **same** resolved file for the same area (single shared resolver `_resolve_area_context_rel_path`; the resource calls `gen._resolve_area_context_rel_path`).
- [x] AC-3: The synthetic `(root)` area still resolves to the repo-root `AGENTS.md`; a non-root area whose only ancestor `AGENTS.md` is the repo root does **not** link/serve it (per Requirement 4) and returns the graceful not-found/author-one message. (`test_root_area_resolves_repo_root_agents`, `test_repo_root_excluded_for_non_root_area`.)
- [x] AC-4: Resolution is deterministic and independent of representative-path churn — given a fixed tree, the resolved path does not depend on dict/set iteration order; covered by a test that asserts a stable result. (`test_deterministic_repeat`; resolver is a pure nearest-first path walk.)
- [x] AC-5: Fail-safe paths unchanged: unknown area id → graceful not-found; codebase-map-unavailable → graceful; resource never synthesizes content. Docs/seed prose describing the resolution rule updated (`AGENTS.md`, `docs/specs/mcp-tool-surface.md`, seed `030`); full suite + docs-lint clean. (`test_none_when_no_ancestor_has_one`, `test_area_resource_not_found_when_unauthored_or_unknown`.)

## Tasks

- [x] Add `_resolve_area_context_rel_path(root, area) -> str | None` in `gen_codebase_map.py` (ancestor walk, nearest-existing-wins, bounded per Requirement 4).
- [x] Route `_area_context_exists` and the `render_markdown` link block through the resolver; `_area_context_link_href` now takes the resolved rel path.
- [x] Route `resource_area_context` (`server_impl.py`) through the resolver; not-found/author-one hint updated for walk-up.
- [x] Audit seeds + `docs/specs/mcp-tool-surface.md` / `AGENTS.md`: only seed `030` (authoring location) stated the rep-path convention — broadened to "representative directory or owning project root" (seed-first, `seed_edit_allowed`); `050`/`160` had no exact-path rule. Docs updated to describe walk-up resolution.
- [x] Tests: walk-up hit, nearest-ancestor-wins, root-area unchanged, repo-root-not-used-for-non-root, not-found, exact-rep-path still resolves, end-to-end render link, resource walk-up, determinism.
- [x] docs-lint + full suite. (Targeted suites green; full suite pending after `1p66e`.)

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` — update the `wavefoundry://area/{area_id}` resource entry to describe ancestor-walk resolution. No boundary/flow change otherwise (single-module + resource-handler behavior).

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The fix — conventional project-root placement resolves. |
| AC-2 | required | Single shared resolver; link and resource must not diverge. |
| AC-3 | required | No regression on root area; no repo-root noise on non-root areas. |
| AC-4 | important | Determinism + churn-robustness is the durability rationale. |
| AC-5 | important | Fail-safe + docs/seed parity. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-17 | Planned from teton round-4 `#6`: per-area AGENTS.md at conventional project roots invisible to map link + resource (exact-rep-path only). | round-4 feedback; `_area_context_rel_path` `gen_codebase_map.py:1253`; `resource_area_context` `server_impl.py:17822` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-17 | Resolve by walking up the directory tree to the nearest existing `AGENTS.md`, not by detecting an "owning project root" via `project.json`/`package.json`. | Filesystem `AGENTS.md` presence is language/build-system agnostic (generic); subsumes project-root detection without a marker dependency. | Project-root marker detection (rejected — per-ecosystem marker list, less generic). |
| 2026-06-17 | For non-root areas, exclude the repo-root `AGENTS.md` from the walk-up fallback. | Repo-root guide is the global operating doc (surfaced by the `(root)` area + `wavefoundry://agents`); linking it from every unrelated area is noise. | Include repo root (rejected — every area would link the same global file). Flag for prepare-council. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Walk-up links a too-broad ancestor `AGENTS.md` to an only-loosely-related area. | Nearest-ancestor-wins keeps it as specific as the authored files allow; repo-root excluded for non-root areas; council reviews the bound. |
| New resolution path diverges between the two surfaces over time. | Single shared resolver consumed by both; AC-2 parity test locks it. |
| Resource reconnect needed for the (already-registered) resource — behavior change only. | No new resource registered; behavior-only change, no reconnect required. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
