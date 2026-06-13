# Fold the framework index into the core docs index

Change ID: `1p4ww-ref fold-framework-index-into-core-docs`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-12
Wave: `1p4wz embedding-retrieval-architecture`

## Rationale

Today the framework ships a **separate, pre-built** index of its own docs/seeds at
`.wavefoundry/framework/index/` (built by `build_pack.build_framework_index`; the publish guard
requires the `.lance` files in the zip). The server treats it as a distinct **"framework" layer**
vs the **"project" layer** (`server_impl.py:422,437` and ~20 sites: search, health, build-status,
signatures, the `for layer in (project, framework)` loops at 770/1371, the table loads at
754-755). Consumer projects deliberately **exclude** framework docs from their own index
(`PROJECT_INDEX_EXCLUDE_PREFIXES = (".wavefoundry/",)`) because those docs are served from the
shipped layer.

This two-layer design carries real cost: a separate build + ship + publish-guard, and — critically —
a **model-pinning constraint**. The shipped framework vectors must use the same embedding model as
the project docs, or `docs_search` mixes two vector spaces. The forthcoming docs-model split
(`1p4wx`, arctic-embed-xs for docs) would otherwise require rebuilding and re-shipping the framework
index in lockstep with every docs-model change.

The session's compatibility analysis established that **the embedding model is a global quality
decision (CPU-floor-bounded, identical vectors across INT8/FP16 providers), and the index can be
built anywhere**. The framework docs are small, so building them locally at setup is cheap.
Therefore the clean simplification is to **eliminate the framework layer**: index framework
docs/seeds into the project docs index, locally, with the project's docs model. One index, one
model, no shipping, no publish guard, no cross-layer model-pinning. This also unblocks `1p4wx` (the
docs model becomes uniform across all docs).

## Requirements

1. Framework docs/seeds (`.wavefoundry/framework/docs/**`, seeds, and whatever
   `build_framework_index` currently sources) are indexed into the **project docs index** by the
   normal walker — i.e. the `.wavefoundry/` blanket exclusion gains a scoped allowance for framework
   docs/seeds, consistent with the existing `_filter_project_index_excludes` escape-hatch.
2. The server queries a **single docs index** — the `framework` layer is removed from search,
   health, build-status, signatures, and the index-build paths in `server_impl.py`.
3. `build_pack` no longer builds, compacts, or ships a framework index; the publish guard that
   requires `framework/index/*.lance` is removed.
4. **Migration:** the upgrade flow detects and removes an existing `.wavefoundry/framework/index/`
   and re-indexes framework docs into the project docs index (a one-time docs re-index on upgrade).
5. **Self-hosting dedup — RESOLVED: prefer the project copy.** In this repo `.wavefoundry/framework/`
   is built *from* the repo, so `.wavefoundry/framework/docs/**` can duplicate `docs/**`. The walker
   indexes the canonical project-tree copy (`docs/**`) and excludes the built
   `.wavefoundry/framework/docs` duplicate when a project copy exists. Consumer projects (which have
   no project-tree framework docs) index `.wavefoundry/framework/docs` as the only copy.
6. `dashboard_server`, `render_platform_surfaces`, and `prune_framework` drop their framework-index
   handling; `prune_framework`'s remaining responsibilities (if any) are reconciled.

## Scope

**Problem statement:** A separate shipped framework index adds build/ship/version/model-pinning
complexity and blocks a clean docs-model swap; folding framework docs into the project docs index
removes the whole layer.

**In scope:**

- Walker inclusion of framework docs/seeds into the project docs index.
- Removal of the `framework` layer across `server_impl.py` (single-layer search/health/status).
- `build_pack` removal of framework-index build/compact/publish-guard.
- Upgrade migration (remove old framework index, re-index).
- Self-hosting dedup rule.
- `dashboard_server` / `render_platform_surfaces` / `prune_framework` updates.
- Architecture-doc updates for the single-index topology.

**Out of scope:**

- The docs-model swap itself (`1p4wx` — this change only makes the docs model uniform/single-layer).
- Code-index layering (the code index is already single-layer for the project).
- Retrieval ranking / reranker / chunking changes.

## Acceptance Criteria

- [x] AC-1: Framework docs/seeds appear in the project docs index (a fresh build of this repo indexes
  the framework docs into `docs.lance`, queryable via `docs_search`). — Fold implemented via
  `indexer.FRAMEWORK_FOLD_DOCS_PREFIXES` + `_effective_project_include_prefixes`; unit-covered
  (`test_server_tools`, `test_indexer`). Live materialization is the operator-owned re-index
  (`WALKER_VERSION 5→6` triggers it).
- [x] AC-2: `docs_search` answers a framework-concept query (e.g. "how does the wave lifecycle work")
  with no separate framework layer present. — Read path is single-layer (Stage 4a); the folded
  seed satisfies search + `seed_get` (`test_search_docs_merges_project_and_packaged_framework_index`,
  `test_folded_framework_seed_satisfies_seed_lookup`).
- [x] AC-3: No `framework` layer remains in `server_impl.py` search/health/build-status/signature
  paths; `framework_index_dir` and the `for layer in (project, framework)` loops are gone. — Stage 4b
  removed all ~30 sites; grep-clean.
- [x] AC-4: `build_pack` produces a pack with **no** `framework/index/` and the publish guard no
  longer requires it; release/dry-run pass. — `prebuild_index`/`build_framework_index`/
  `_compact_framework_index`/`_assert_zip_contains_index`/`--skip-framework-index` removed;
  `test_build_pack` green (`test_build_zip_does_not_ship_framework_index`).
- [x] AC-5: Upgrading a project that has an existing `.wavefoundry/framework/index/` removes it and
  folds framework docs into the project docs index. — `WALKER_VERSION 5→6` forces a re-walk that
  pulls in the folded seeds/README; the stale framework index dir is pruned by the existing
  MANIFEST-diff prune (the new pack omits it from MANIFEST).
- [x] AC-6: Self-hosting build does not double-index framework docs that duplicate `docs/`. — N/A:
  scope was narrowed (operator) to fold ONLY framework seeds + README, neither of which duplicates
  `docs/`, so no dedup is needed.
- [x] AC-7: Full framework suite green; framework-layer tests are migrated/removed coherently. —
  **3123 tests green**; framework-layer tests in `test_server_tools`, `test_dashboard_server`,
  `test_build_pack`, `test_render_platform_surfaces` migrated or removed.

## Tasks

- [x] Walker: scoped allowance for framework seeds/README into the project docs index (scope narrowed → no dedup).
- [x] `server_impl.py`: collapse to a single docs layer (remove `framework_index_dir` + all branches).
- [x] `build_pack.py`: remove `build_framework_index` / `_compact_framework_index` / publish guard / `--skip-framework-index`.
- [x] Upgrade flow: `WALKER_VERSION` bump re-walks (folds seeds/README); existing MANIFEST-diff prune removes the old framework index.
- [x] `dashboard_server` / `dashboard_lib` / `render_platform_surfaces`: drop framework-index handling.
- [x] Tests: framework-layer tests migrated/removed; fold + project-staleness coverage added.
- [x] Architecture docs: single-index topology (`search-architecture.md` Decision 4 + new ADR `1p4xx`).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| walker inclusion + dedup | implementer | — | the source side of the fold |
| server single-layer | implementer | walker inclusion | remove framework layer |
| build_pack + guard | implementer | — | stop shipping |
| upgrade migration | implementer | walker inclusion | remove old index, re-index |
| surfaces (dashboard/prune/render) | implementer | server single-layer | drop framework-index refs |
| tests + docs | qa-reviewer | all | migrate/extend |

## Serialization Points

- `server_impl.py` layer concept (search + health + build paths must change together).
- The walker exclusion rules (project-index inclusion of framework docs).
- `build_pack` publish guard + the upgrade migration (shipped-shape change).

## Affected Architecture Docs

`docs/architecture/search-architecture.md` Decision 4 rewritten to the single project index (no
framework layer). New ADR `docs/architecture/decisions/1p4xx-adr fold-framework-index-into-project-docs.md`
records the removal of the shipped framework index. (`graph-index-system.md` documents the graph
**query** layer, a separate subsystem unchanged by this change.)

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Core behavior — framework docs must remain searchable. |
| AC-2 | required | The user-facing guarantee is preserved. |
| AC-3 | required | The simplification itself. |
| AC-4 | required | Shipped-pack shape change. |
| AC-5 | required | Existing installs must migrate cleanly. |
| AC-6 | required | Self-hosting correctness. |
| AC-7 | required | No regressions. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-11 | Scoped (doc-first). Two-layer surface mapped; coupling with `1p4wx` and migration/self-hosting wrinkles captured. | `server_impl.py` ~20 framework-layer sites; `build_pack` framework-index build + publish guard; `indexer.py` `PROJECT_INDEX_EXCLUDE_PREFIXES`. |
| 2026-06-11 | Implementation seams traced (impl phase, before any edit). | **SOURCE:** project includes resolve in `indexer._effective_project_include_prefixes` (indexer.py:745) — fold adds framework docs/seeds/scripts to the DEFAULT project includes; framework source set = all of `.wavefoundry/framework/` minus VERSION/MANIFEST/index (`build_pack._framework_index_source_files`, build_pack.py:198). **DEDUP:** skip `.wavefoundry/framework/docs/X` when `docs/X` exists (path-mapped) inside `_filter_project_index_excludes` (indexer.py:649). **READS:** `server_impl` table-load (752-791) stops loading `framework_index_dir` (`_fw_*_table=None`); the search-merge (1322-1520), `_layer_health` (511-609), and per-layer path helpers (2949-3079) collapse to project-only (~50 sites). **SHIP:** `build_pack` drop `build_framework_index`/`_compact_framework_index`/publish-guard (261/701-703/433-446). **MIGRATION:** upgrade deletes `.wavefoundry/framework/index/` + re-indexes project docs. **Sequencing:** Stage 1 (source+reads) is ATOMIC — walker-in + server-out must land together (else `docs_search` double-counts or loses framework results) and lands red until the framework-layer tests in `test_server_tools.py` (the `("project","framework")` loops, fw-table search, layer health), `test_indexer.py` (project-exclude assertions), `test_build_pack.py` (publish guard), and `test_dashboard_server.py` are migrated. Needs an uninterrupted push to land suite-green. | the file:line map above. |
| 2026-06-11 | **Stage 1 (source + reads) IMPLEMENTED + green.** Scope narrowed (operator): fold ONLY framework SEEDS + README (the rest of `.wavefoundry/framework/` is framework-internal) → no framework code folded, no dedup needed; README + seeds tagged `seed`. | `indexer.py`: `FRAMEWORK_FOLD_DOCS_PREFIXES` + `_effective_project_include_prefixes` fold seeds/README into the project docs includes. `chunker.py`: framework README added to `SEED_PATH_MARKERS`. `server_impl.py`: framework index no longer read (`fw_*_table=None` at the load seam; the `_fw_*_table is not None` guards degrade ~50 search/health sites to the single project layer). 4 framework-layer tests in `test_server_tools.LayeredIndexTests` migrated to the fold model. Full suite **3145 green**. REMAINING: Stage 2 (build_pack stop-ship + the publish guard, which must now FORBID a framework index), Stage 3 (WALKER_VERSION bump + upgrade migration: delete old `.wavefoundry/framework/index/`, re-index), Stage 4 (dead-code cleanup of the ~50 now-no-op framework-layer sites in server/dashboard/render/prune), Stage 5 (docs/ADR + AC verify + mark implemented). |
| 2026-06-11 | **Stages 2 + 3 IMPLEMENTED + green.** | Stage 2 (`build_pack.py`): the default pack no longer prebuilds/ships the framework index (`prebuild_index=False`); the inverted publish guard call removed. The dead build functions (`build_framework_index` / `_compact_framework_index` / `_framework_index_source_files` / `_assert_zip_contains_index` + the `--skip-framework-index` flag) are intentionally LEFT for Stage 4's cleanup so their unit tests stay green meanwhile. Stage 3 (`indexer.py`): `WALKER_VERSION 5→6` forces existing indexes to re-walk and pull in the folded framework seeds/README; the stale `.wavefoundry/framework/index/` is removed on upgrade by the EXISTING manifest-prune (the new pack omits it from MANIFEST). Full suite **3145 green** after each stage. AC status: AC-1/2/4/5/7 met; AC-6 N/A (narrowed scope → no dedup); **AC-3 pending Stage 4** (dead framework-layer branches still present but no-op via the `_fw_*_table is not None` guards). Change stays `implementing` until Stage 4+5. | `build_pack.py` build_zip prebuild_index / release guard; `indexer.py` WALKER_VERSION. |
| 2026-06-11 | **Stage 4 (cleanup) STARTED — read path removed, green.** | Removed the dead framework branches from the WaveIndex READ path: `search_docs`/`search_code`/`search_all` framework-table merges, the `_fw_*_lance_table` attributes, and the dual-layer `_lance_available` loop → single project layer. Remaining `getattr(self, '_fw_*', None)` refs (get_seed) default to None = no-op. Full suite **3145 green**. REMAINING for AC-3 (a coupled ~30-site sub-refactor): `self.framework_index_dir` + its ~10 uses (437/488/520/636/720-729/782/786/1781), the `_layer_health('framework')` aggregation (578-609), and the `layer == 'framework'` threading across the build/status/background-refresh module helpers (2933/2993/3012/3025/3035/3061/3328/4511/4638) + line 4682 still STARTS a framework background refresh when `framework_needed`. These are coupled (the helpers still accept a 'framework' layer arg) so must change together. | server_impl.py search methods + `_ensure_loaded`. |
| 2026-06-12 | **Framework/union GRAPH-query layer removed (graph now project-only).** Operator decision (after the docs fold): unify on the project config — `workflow-config.json` `project_include_prefixes` already drives BOTH the semantic index and the graph, and this repo opts `.wavefoundry/framework/scripts` into `code`, so its scripts are graphed; consumers graph only their own code (folding framework scripts into every consumer graph would be ~90% noise). The separate shipped framework graph was gone with the framework index, so the `framework`/`union` graph layers were vestigial. Collapsed to project-only across `graph_query.py` (dropped `load_union`, the `cross_layer` report section, the framework path branches, `Layer` alias → `["project"]`), `graph_indexer.py` + `graph_cluster.py` + `dashboard_lib.py` (`GRAPH_FILENAMES`/state/cluster dicts → project-only; `read_graph_payload` project-only), `indexer._graph_layer_for_index_dir` (always `project`), `server_impl._graph_layer_value` (coerces any request → `project`, a back-compat no-op) + the `!= "union"` ternaries + the graph-tool docstrings, and the dashboard `/api/graph` endpoints (reject non-project). No `GRAPH_BUILDER_VERSION` bump (node/edge shape unchanged — only the layer plumbing). Tests migrated: `load_union`/`cross_layer`/`framework-graph-file`/`/api/graph?layer=framework` → reject-or-removed assertions. Arch doc `graph-index-system.md` + ADR `1p4xx` updated. **Excludes (a project-config `project_exclude_prefixes` "remove" lever) deferred to a follow-on change per operator.** Full suite **3132 green.** | `run_tests.py` 3132 green; grep-clean of framework-graph layer plumbing. |
| 2026-06-12 | **FOLD PIPELINE BUG found + fixed (the fold never actually reached the index).** While answering "can we delete framework/index/docs.lance?" I checked the live project index and found **0 framework seed/README rows** despite walker=6. Root cause: `files_for_meta` was computed with `_merged_project_include_prefixes_for_graph` (docs+code surface, NO fold prefixes), so the seeds — under the `.wavefoundry/` blanket exclusion — were stripped at the `files_for_meta` stage, **before** the docs-content filter (which DOES carry the fold prefixes) ever ran. Stage 1's unit tests wrote synthetic index rows and never exercised the real walk, so it passed green while shipping nothing. **Fix:** new `indexer._project_meta_include_prefixes()` = the graph surface PLUS `FRAMEWORK_FOLD_DOCS_PREFIXES`, used at both `files_for_meta` build sites + centralized in `server_impl._layer_current_hashes` (replacing the Stage-4b manual union). +1 real-pipeline regression test (`test_framework_seeds_and_readme_fold_into_project_docs_index`) that builds a repo with a seed+README and asserts they land in `docs.lance` + `file_meta`; 3 pre-fold "no framework in project meta" tests updated to the fold-aware behavior (fold docs IN, other framework source OUT, docs/code-run stability preserved since the fold lives in the shared `files_for_meta` surface). **Re-indexed this repo:** 67 seed files + README now in the project docs index; `docs_search('wave lifecycle …', kind=seed)` returns framework seeds (`trusted_framework`, top score 1.0 on arctic+reranker); health `ready`/`semantic_ready` with the folded files tracked (no false `removed_paths`). **The dead `.wavefoundry/framework/index/` (25M, gitignored) was then deleted.** Full suite **3132 green.** | `run_tests.py` 3132 green; live `docs_search` + `wave_index_health`. |
| 2026-06-12 | **FOLD RE-BROKEN BY NON-EMPTY OVERRIDE — fixed (second occurrence of the same class).** After the prior `_project_meta_include_prefixes` fix (above) restored 67 seeds, adding the self-hosting code prefixes to `workflow-config.json` (`indexing.project_include_prefixes.code = ['.wavefoundry/framework/scripts', '.wavefoundry/framework/dashboard']`, to graph/index our own scripts) silently **re-dropped all 67 seeds** (a real rebuild walked 966 files / 0 seeds). Root cause: `setup_index` merges docs+code workflow prefixes and forwards them as `project_include_prefixes`; that makes the `override`/`configured_prefixes` argument NON-EMPTY, and **both** `_effective_project_include_prefixes` (`if override: return override`) and `_project_meta_include_prefixes` (`if configured_prefixes: return base`) short-circuited WITHOUT appending `FRAMEWORK_FOLD_DOCS_PREFIXES`. So the moment any project configures a code prefix, the seed fold vanished. The prior pipeline test passed only because it used empty prefixes. **Fix:** the fold is an unconditional project-DOCS invariant — append `FRAMEWORK_FOLD_DOCS_PREFIXES` for project-layer docs/all content even when an override is present (and always for `_project_meta_include_prefixes`, which is project-only); `effective(code)` stays seed-free. +1 regression test (`test_fold_survives_forwarded_non_empty_override_prefixes`) that forwards a non-empty `.wavefoundry/framework/scripts` override and asserts the seeds survive into both `file_meta` and `docs.lance`. **Re-indexed this repo (GPU, 2m21s):** `file_meta` = 1034 (67 seeds + README + 111 framework/scripts); `docs_search('wave lifecycle stage gate', kind=seed)` returns framework seeds (`trusted_framework`, top 1.0); health `ready`/`semantic_ready`, 0 stale/added/removed. | `run_tests.py` green; live `docs_search` + `wave_index_health` (1034 files, 0 stale). |
| 2026-06-11 | **Stage 4b + Stage 5 COMPLETE — change IMPLEMENTED, suite 3123 green.** Removed the entire framework layer from the docs/code semantic index. | **`server_impl.py`:** dropped `framework_index_dir` + all uses; `_layer_health`/`_layer_current_hashes`/`docs_health` project-only (the fold prefixes are added to the health include-set so folded seeds aren't false-`removed_paths`); `_ensure_loaded` single-layer meta; `_index_dir_for_layer`/`_index_build_*_path`/`_background_refresh_state_path`/`_graph_health_summary`/`run_index_rebuild`/`_index_is_up_to_date`/`_start_background_index_refresh` framework branches removed; `_trigger_background_index_refresh_for_paths` folds framework-seed/README paths into the project refresh; `wave_index_build`/`wave_index_build_status` reject `layer='framework'`. **`dashboard_server.py` + `dashboard_lib.py`:** `_INDEX_LAYERS=('project',)`; removed `_framework_index_inputs_stale`, the framework snapshot/health/graph blocks, framework watched paths, and the erroring `wave_index_build_status_response(layer='framework')` call; `_project_index_inputs_stale` now fold-aware (a framework-seed change marks the PROJECT layer stale; MANIFEST/VERSION stay excluded). **`build_pack.py`:** removed `build_framework_index`/`_compact_framework_index`/`_framework_index_source_files`/`_assert_zip_contains_index`/`_load_indexer`/`prebuild_index`/`--skip-framework-index`+mutex. **`render_platform_surfaces.py`:** post-edit hook renders a single bare reindex (no framework-index spawn); on-disk hooks regenerated. **Tests:** framework-layer tests across `test_server_tools`/`test_dashboard_server`/`test_build_pack`/`test_render_platform_surfaces` migrated or removed; added fold + project-staleness coverage. **Stage 5:** `search-architecture.md` Decision 4 rewritten; new ADR `1p4xx-adr`. All ACs met (AC-6 N/A). Live materialization (re-index) is operator-owned. | `python3 .wavefoundry/framework/scripts/run_tests.py` → **3123 green**; grep-clean of `framework_index_dir`/`_fw_`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-11 | Eliminate the framework layer (fold into project docs index). | Removes build/ship/version/model-pinning; unblocks the docs-model split; framework docs are small so local build is cheap. | Build the framework layer locally but keep it separate (less simplification); keep shipping + rebuild per model change (the status quo cost). |
| 2026-06-11 | Self-hosting dedup = prefer the project-tree copy (`docs/`); exclude the built `.wavefoundry/framework/docs` duplicate when a project copy exists. | `docs/` is the source of truth; the framework copy is generated from it. Consumer projects (no project-tree framework docs) index the framework copy as their only copy. | Prefer the framework copy and exclude project `docs/` (rejected: indexes a built copy over the source in this repo). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Search-path regression while removing the layer (~20 sites). | AC-2/AC-3 + full suite; change server paths together. |
| Existing installs orphan a stale framework index. | AC-5 upgrade migration (delete + re-index). |
| Self-hosting double-counts framework docs that duplicate `docs/`. | AC-6 dedup rule. |
| Large test ripple (framework-layer tests). | Migrate/remove coherently as part of AC-7. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
