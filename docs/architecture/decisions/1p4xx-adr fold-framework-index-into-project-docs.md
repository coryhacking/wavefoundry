# 1p4xx-adr — Fold the framework index into the project docs index

Owner: Engineering
Status: accepted
Last verified: 2026-07-20

## Context

Historically the framework shipped a **separate, pre-built** semantic index of its own
docs/seeds at `.wavefoundry/framework/index/`, built by `build_pack.build_framework_index` and
required in the release zip by a publish guard. The MCP server treated it as a distinct
**"framework" layer** versus the **"project" layer** across ~30 sites in `server_impl.py`
(table loads, search merges, `_layer_health`, build/status/background-refresh helpers), and the
dashboard mirrored the two-layer model. Consumer projects deliberately **excluded** framework
docs from their own index because those docs were served from the shipped layer.

This two-layer design carried real cost:

- A separate build + ship + publish-guard step at release time.
- A **model-pinning constraint**: the shipped framework vectors had to use the same embedding
  model as the project docs, or `docs_search` mixed two vector spaces. The forthcoming
  docs-model split (`1p4wx`, arctic-embed-xs for docs) would otherwise require rebuilding and
  re-shipping the framework index in lockstep with every docs-model change.

The session's compatibility analysis established that the embedding model is a **global quality
decision** (CPU-floor-bounded, identical vectors across INT8/FP16 providers) and that the index
can be built anywhere. The framework docs are small, so building them locally at setup is cheap.

## Decision

Eliminate the framework index layer. Index the framework **seeds + README** into the **project
docs index**, locally, with the project's docs model. One index, one model — no shipping, no
publish guard, no cross-layer model-pinning.

- The walker appends `indexer.FRAMEWORK_FOLD_DOCS_PREFIXES`
  (`.wavefoundry/framework/seeds`, `.wavefoundry/framework/README.md`) to the project docs
  include-prefixes, scoped past the `.wavefoundry/` blanket exclusion.
- `server_impl.py`, `dashboard_server.py`, and `dashboard_lib.py` collapse to a single project
  layer; `framework_index_dir`, `_layer_health("framework")`, the `(project, framework)` loops,
  and the `layer == "framework"` build/status/refresh branches are removed. `index_build`
  and `index_build_status` reject `layer="framework"`.
- `build_pack` no longer builds, compacts, or ships a framework index; the `--skip-framework-index`
  flag and the publish guard are removed. The pack ships framework **source** only.
- `render_platform_surfaces` renders a single bare reindex spawn in the post-edit hook (the
  separate framework-index spawn is gone).
- Migration: `WALKER_VERSION` bumped (5→6) forces existing project indexes to re-walk and pull in
  the folded framework seeds/README; the stale `.wavefoundry/framework/index/` is pruned on
  upgrade by the existing MANIFEST-diff prune (the new pack omits it from MANIFEST).

## Consequences

**Positive:**
- One index, one embedding model — `docs_search` never mixes vector spaces.
- No separate framework-index build/ship/compact/publish-guard at release time.
- Unblocks a per-project / per-docs embedding-model choice (`1p4wx`) without re-shipping vectors.
- ~Fewer moving parts: the entire "framework layer" concept is gone from server + dashboard.

**Negative / tradeoffs:**
- The framework docs are (re-)embedded locally at each project's setup/upgrade instead of once at
  release. Cheap because the seed/README corpus is small, but no longer amortized across installs.

**Constraints imposed:**
- Framework docs reachable by `docs_search` must live under the folded prefixes
  (`.wavefoundry/framework/seeds`, `.wavefoundry/framework/README.md`). Other framework files
  (MANIFEST, VERSION, scripts) are not folded and stay out of the docs index.
- The graph **query** layer was collapsed to project-only in the same wave (a follow-up to this
  ADR): the `framework` and `union` (merged) graph layers were removed along with the shipped
  framework graph. The `layer` argument on the graph tools (`code_impact`, `wf_graph_report`,
  `code_graph_path`, `code_graph_community`, `graph_neighbors`, …) is retained as a back-compat
  no-op that always resolves to `project`. Whatever a project wants in its graph is controlled by
  the same `workflow-config.json` `project_include_prefixes` that drives the semantic index — this
  repo opts `.wavefoundry/framework/scripts` into its `code` prefixes, so its own framework scripts
  are graphed; consumer projects graph only their own code.

## Alternatives Considered

| Alternative | Reason rejected |
|-------------|----------------|
| Build the framework layer locally but keep it separate | Keeps the two-layer search/health/build complexity and the cross-layer model-pinning; less simplification. |
| Keep shipping + rebuild the framework index per docs-model change | The status-quo cost — a separate ship step plus lockstep rebuilds that block the docs-model split. |
| Prefer the built `.wavefoundry/framework/docs` copy over the project `docs/` tree (self-host) | Indexes a generated copy over the source of truth in this repo. Scope was narrowed to seeds+README, so no dedup is needed. |

## References

- `docs/waves/1p4wz embedding-retrieval-architecture/1p4ww-ref fold-framework-index-into-core-docs.md`
- `docs/architecture/search-architecture.md` (Decision 4)
- `indexer.FRAMEWORK_FOLD_DOCS_PREFIXES`, `indexer._effective_project_include_prefixes`
