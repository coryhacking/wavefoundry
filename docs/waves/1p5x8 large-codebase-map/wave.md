# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-16

wave-id: `1p5x8 large-codebase-map`
Title: Codebase Map

## Objective

Give agents a navigable map of the **destination project's own codebase**, generated from the index/graph the framework already builds — for a project of **any size**. The map is a **compact, hierarchical orientation layer** (domains → sub-areas → key entry points) that tells an agent *which* part of the codebase to drill into via the `code_*` tools, and it **scales gracefully**: a small repo yields a small, near-flat map; a large monorepo yields a bounded top-level view with leveled drill-down rather than a monolithic dump. Extra-large enterprise repositories are the **stress case the design must not break at** (and where the value is highest, since the repo can't fit in context and wavefoundry's persisted graph is a defensible advantage Claude Code / Cursor lack) — not the exclusive audience. When this wave closes, an agent landing cold in any repo — five files or fifty thousand — can orient from a right-sized map and descend on demand instead of grep-thrashing.

## Changes

Change ID: `1p5tl-enh project-codebase-map`
Change Status: `implemented`

Change ID: `1p5xc-enh per-area-agents-context`
Change Status: `implemented`

Change ID: `1p5zr-enh codebase-map-ranking-quality`
Change Status: `implemented`

Change ID: `1p5zy-enh code-reviewer-dead-code-mode`
Change Status: `implemented`

Change ID: `1p601-enh codebase-map-mcp-surface`
Change Status: `implemented`

Change ID: `1p607-enh simulate-hooks-session-capture`
Change Status: `implemented`

Change ID: `1p608-enh prompt-surface-naming-fixes`
Change Status: `implemented`

Change ID: `1p60k-enh reality-checker-scope-guard-precision`
Change Status: `implemented`

Change ID: `1p60q-bug map-name-responsibility-consistency`
Change Status: `implemented`

Completed At: 2026-06-16

## Wave Summary

Wave `1p5x8 large-codebase-map` (Codebase Map) delivered 9 changes: Project codebase map — hierarchical, scales gracefully at any size, Per-area AGENTS.md context (vendor-neutral, no per-folder bridge files), Codebase map ranking quality + feed repo-index (Option A), Code-reviewer: maintainability & dead-code mode (generic, all projects), Codebase map MCP surface (resource + index-build refresh), simulate-hooks: include the session-capture (Stop) hook, Prompt-surface naming fixes (concrete bugs) + convergence plan, reality-checker: precise scope-guard (silent creep yes, approved scope no), and Codebase map: area name ↔ Responsibility consistency. Notable adjustments during implementation: Codebase map ranking quality + feed repo-index (Option A): Scoped from the operator's evaluation of the rendered map: dominant `scripts` blob (1612 nodes), degree-ranking surfaces utilities (`_response`/`_diagnostic`), config JSON keys shown as "(class)" entry points, weak labels. Plus Option A (map feeds `repo-index`) and the `1p5xc` map-link broken-link bug.; Code-reviewer: maintainability & dead-code mode (generic, all projects): Scoped from operator request: add a dead-code/maintainability review to the code-reviewer seed because it is already the close-wave council seat. Generic for all wavefoundry projects (not this repo). Leans on the framework's own `code_*` graph tools + review discipline; reuses the existing empty-graph-corroboration rule and EXTRACTED-edge confidence caution.; reality-checker: precise scope-guard (silent creep yes, approved scope no): Operator: reality-checker keeps flagging operator-directed scope changes as "sprawl" — noise. Keep the silent-creep guardrail; remove the approved-scope commentary.

**Changes delivered:**

- **Project codebase map — hierarchical, scales gracefully at any size** (`1p5tl-enh project-codebase-map`) — 5 ACs completed. Key decisions: --------; Map the destination project's code, generated from the existing index/graph
- **Per-area AGENTS.md context (vendor-neutral, no per-folder bridge files)** (`1p5xc-enh per-area-agents-context`) — 4 ACs completed. Key decisions: --------; Vendor-neutral `AGENTS.md` per area; `@import` only at root
- **Codebase map ranking quality + feed repo-index (Option A)** (`1p5zr-enh codebase-map-ranking-quality`) — 7 ACs completed. Key decisions: --------; Quality fixes first → operator re-eval → then wire the repo-index feed
- **Code-reviewer: maintainability & dead-code mode (generic, all projects)** (`1p5zy-enh code-reviewer-dead-code-mode`) — 4 ACs completed. Key decisions: --------; Add to the code-reviewer seed (`221`), not a new standalone agent
- **Codebase map MCP surface (resource + index-build refresh)** (`1p601-enh codebase-map-mcp-surface`) — 5 ACs completed. Key decisions: --------; Resource + `content="map"` refresh, not a new query tool
- **simulate-hooks: include the session-capture (Stop) hook** (`1p607-enh simulate-hooks-session-capture`) — 2 ACs completed
- **Prompt-surface naming fixes (concrete bugs) + convergence plan** (`1p608-enh prompt-surface-naming-fixes`) — 3 ACs completed
- **reality-checker: precise scope-guard (silent creep yes, approved scope no)** (`1p60k-enh reality-checker-scope-guard-precision`) — 2 ACs completed
- **Codebase map: area name ↔ Responsibility consistency** (`1p60q-bug map-name-responsibility-consistency`) — 2 ACs completed. Key decisions: --------; Fix only the generator-owned mismatch in this wave; defer all graph/index-layer defects to a separate graph-extractor wave.
## Journal Watchpoints

- **Works at any size; scales gracefully (a first-class requirement).** The map generates for any indexed project — no size gate. It is right-sized: a small repo gets a compact, near-flat map; a monorepo with hundreds of graph communities gets a bounded top-level view (domains/areas + entry points) with leveled drill-down (scoped sub-maps on demand), caps/paging, and an explicit "drill in via `code_graph_community` / `code_outline`" handoff. XL is the stress case, not the audience: a flat, monolithic map that recreates the haystack at the map level is the blocking failure mode to avoid — treat unbounded top-level output as a release blocker. Verify both ends (small → compact; synthetic-large → bounded).
- **Map the destination project, not the framework** — targets whatever project wavefoundry is installed into; generated from that project's persisted graph + `graph_cluster` artifact (reuse the index; never re-parse). Read-only consumer → no `GRAPH_BUILDER_VERSION` bump; track `CLUSTER_BUILDER_VERSION` for staleness.
- **Generic + seed-rooted** — generator ships in `.wavefoundry/framework/scripts/`; output lands at a conventional, project-agnostic location; discoverability woven into the seed-rendered orientation surface so agents consult it first. No project-specific hardcoding. Open `framework_edit_allowed` for the generator, `seed_edit_allowed` for the orientation pointer.
- **Refresh model** — regenerates with the index build/refresh lifecycle and on demand; freshness tracks the index (throttle on huge repos). Not a hard per-commit parity gate (noise for live project code). Generated artifact must be docs-lint-clean and inherit the index file-scoping (no gitignored/secret files mapped).
- **The map is the index to the index** — its job is to route the agent to the right community/area, where the existing `code_*` tools provide depth. Keep it anchors + entry points, not per-function summaries.
- **`1p5xc` AGENTS.md context is vendor-neutral, with `@import` only at root** — per-area `AGENTS.md` (major areas only, human-authored content) reached on demand via the map link + a root `AGENTS.md` convention line + the doc index. No `CLAUDE.md` bridge files in subdirectories and no nested `@import` (operator constraint). Scaffolding creates stubs idempotently and must never overwrite or auto-author content. `1p5xc` scaffolding + map-linking depend on `1p5tl`'s area model; the root-bridge render is independent.

## Review Evidence

- wave-council-readiness: READY — prepare-council passed 2026-06-16. Two generic, seed-rooted, size-agnostic capabilities: a graceful-scaling project codebase map (`1p5tl`) and per-area `AGENTS.md` context (`1p5xc`). Reframed this session from XL-only to any-size (no size gate; right-sized output; XL is the stress case, verify both small + large fixtures). Grounded against the code: `graph_cluster` persists labeled communities with stable `hub_node_id`s (consume offline; read-only → no `GRAPH_BUILDER_VERSION` bump); `setup_index.build_index` is the lifecycle hook for regen; `render_platform_surfaces` manages agent surfaces. Conditions carried into implement, not blockers: (1p5tl) the cluster artifact is FLAT Leiden communities — the bounded TOP tier at XL must come from package-to-directory collapse over communities (`wave_graph_report` `collapse_package_to_directory`), not the raw community list (hundreds of communities are themselves a haystack); use the stable `hub_node_id` for drill-in handles, NOT `community_id` (Leiden renumbers on re-cluster); verify both a small fixture (compact) and a synthetic-large fixture (bounded); generated artifact must be docs-lint-clean + inherit index file-scoping. (1p5xc) confirm where the root `CLAUDE.md` is managed (install seed vs hand-maintained) before wiring the root `@AGENTS.md` import; scaffold area stubs idempotently (never auto-author prose); discoverability via the map link + root convention + the doc index; `1p5xc` scaffolding/map-linking depend on `1p5tl`'s area model. Strongest challenge: at XL, communities themselves can be too many for a flat top tier — answered by the package/directory collapse as the higher tier. Strongest alternative: an LLM-summarized map — rejected (unreliable/self-updating-docs problem; the map uses cluster labels + ranked anchors, humans author per-area `AGENTS.md`).
- wave-council-delivery: READY — delivery-council passed 2026-06-16. Both changes implemented + tested; full suite 3211 OK (+24 over the wave start), docs-lint clean (incl. the generated map). Verified against the delivered code: (1p5tl) `gen_codebase_map.compute_areas`/`render_markdown` split (reusable area model); top tier is directory-collapsed over communities and **bounded at `MAX_TOP_AREAS=24`** with an overflow→`code_graph_report` handoff (small fixture → near-flat, synthetic-60-dir fixture → capped+truncated); drill-in uses the stable `hub_node_id` (asserted never a `community_id`); regen hooks `setup_index.build_index` via a fail-safe `_regenerate_codebase_map` (generator error can't fail the index build); read-only → no `GRAPH_BUILDER_VERSION` bump, tracks `CLUSTER_BUILDER_VERSION`; output `docs/references/codebase-map.md` is docs-lint-clean. (1p5xc) root `CLAUDE.md` is a `waveframework:root-bridge` `@AGENTS.md` block (replacing only the prose pointer — all guardrails preserved); repo invariant test asserts **no `@AGENTS.md` outside root + no subdirectory `CLAUDE.md`**; opt-in `--scaffold-area-contexts` is idempotent, never overwrites, stub-only; `render_markdown` links areas to existing `AGENTS.md`; the operating instruction is woven into the `020-run-contract` + `050` seed prompts (seed-first); subdir `AGENTS.md` is index-picked-up. No in-session fixes required. Two non-blocking notes recorded for follow-up: `CodebaseArea.boundary_node_count` is present but unpopulated (0) — not used by `1p5xc`; and a PRE-EXISTING auto-guru duplicate-marker-on-first-insert bug (live repo unaffected — single block) surfaced during testing, out of this wave's scope. Security/runtime: no new network surface; the map inherits index file-scoping (no secret/gitignored files mapped); `@import` root-only. Closeable on merits.
- wave-council-delivery (coverage update 2026-06-16): the wave grew from 2 to 9 changes after the delivery-council line above. The added changes — `1p5zy` (code-reviewer dead-code/maintainability mode), `1p5zr` (ranking-quality + teton-defect fixes: cross-file-fanin entry ranking, config demotion, oversized subdivision, tiered labels + carry-forward, repo-index marker feed, accurate kind tags, same-package collapse, hub-membership, non-code exclusion), `1p601` (MCP map surface: `wavefoundry://codebase-map` resource + `content="map"`, regen decoupled from index build and fired at prepare/close/upgrade/on-read, change-only fingerprint idempotence), `1p607` (simulate-hooks session-capture via shared `CLAUDE_HOOKS` registry + parity test), `1p608` (prompt-surface naming fixes + `package-wave-framework` retirement), `1p60k` (reality-checker scope-guard precision — silent-creep guardrail preserved), `1p60q` (map name↔Responsibility consistency + 2 regression tests) — are all implemented; every AC/task reconciled against verified code artifacts (resource/`content="map"`/decoupled-regen/fingerprint, `CLAUDE_HOOKS`/parity, install-prompt pointer, ranking/config/subdivision/tiered-label/teton-defect functions + tests). Full suite 3251 OK; docs-lint clean (incl. the regenerated map). One in-session fix: added the generated `docs/references/codebase-map.md` to indexer `_PROJECT_STALE_IGNORE_PATHS` to prevent a write→reindex loop. Secrets gate clean. Graph/index-layer defects from teton's p60n trace (TS type-fields-as-function, garbage symbols, clustering granularity/contamination/stability) are deferred to wave `1p61u` (Bucket B), out of this wave's scope. Coverage extended by artifact verification + green suite, not a fresh full council seating.
- operator-signoff: approved — operator directed closure of 1p5x8 on 2026-06-16 after reviewing the regenerated map (Solaris, teton, and this repo) and the name↔Responsibility fix.

## Review Checkpoints

- **Delivery-phase Wave Council [delivery-council] — 2026-06-16: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; verified: 1p5tl top tier directory-collapsed + bounded at MAX_TOP_AREAS=24 (small→near-flat, synthetic-large→capped+truncated), stable `hub_node_id` drill-in (never `community_id`), fail-safe `build_index` regen hook, read-only/no GRAPH_BUILDER_VERSION bump, generated map docs-lint-clean; 1p5xc root-only `@AGENTS.md` bridge preserving all CLAUDE.md guardrails + repo-invariant test (no `@import` outside root, no subdir CLAUDE.md), idempotent stub-only scaffolding, map-linking, operating instruction woven into `020`/`050` seed prompts seed-first, subdir AGENTS.md indexed; strongest-challenge (flat communities → unbounded top tier at XL) resolved by directory collapse + cap; no in-session fixes needed; non-blocking follow-ups noted: `boundary_node_count` unpopulated (unused) + a pre-existing auto-guru duplicate-marker bug out of scope; security/runtime: no new network surface, file-scoping inherited, `@import` root-only; full suite 3211 OK, docs-lint clean)

- **Prepare-phase Wave Council [prepare-council] — 2026-06-16: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the cluster artifact is flat Leiden communities, so at XL the raw community list is itself too large for a bounded top tier — answered by deriving the top tier from package-to-directory collapse over communities (`wave_graph_report` `collapse_package_to_directory`), with communities/members as drill-down; strongest-alternative: an LLM-summarized map — rejected (self-updating-docs unreliability; the map uses cluster labels + graph-ranked anchors and humans author per-area `AGENTS.md`); key conditions: use stable `hub_node_id` not renumbering `community_id` for drill-in handles, verify both small + synthetic-large fixtures (no size gate), regen hooks `setup_index.build_index`, read-only consumer so no `GRAPH_BUILDER_VERSION` bump, generated map docs-lint-clean + inherits index file-scoping; 1p5xc confirms root-`CLAUDE.md` management before the root `@AGENTS.md` bridge and scaffolds area stubs idempotently with no auto-authored prose; security/runtime: no new network surface, no secret/gitignored files mapped)

## Dependencies

- No external wave dependencies.
