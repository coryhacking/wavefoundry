# Architecture — Current State

Owner: Engineering
Status: active
Last verified: 2026-05-01

## Runtime Topology

**Development-time topology:**

```
Developer/agent
  │
  ├── python3 .wavefoundry/framework/scripts/lifecycle_id.py  →  docs/workflow-config.json (read)
  ├── python3 .wavefoundry/framework/scripts/docs_lint.py      →  docs/ tree (read)
  ├── python3 .wavefoundry/framework/scripts/docs_gardener.py  →  docs/ tree (read/write metadata)
  ├── python3 .wavefoundry/framework/scripts/build_pack.py     →  .wavefoundry/framework/VERSION (write), .wavefoundry/framework/index/ (write), wavefoundry-*.zip (write)
  ├── python3 .wavefoundry/framework/scripts/render_platform_surfaces.py  →  .claude/, .cursor/, .github/hooks/, .junie/mcp/, .mcp.json (write)
  └── python3 .wavefoundry/framework/scripts/setup_index.py    →  local model cache (write/verify), .wavefoundry/index/ (write)
```

**MCP topology (active):**

```
MCP client (Claude Code, Cursor, Copilot, etc.)
  │
  └── stdio transport
        └── .wavefoundry/framework/scripts/server.py  (FastMCP)
              ├── wave_help
              ├── docs_search / code_search / seed_get
              │       └── .wavefoundry/index/ (read: *.npy, *.json)
              ├── wave_current / wave_list_waves / wave_list_plans / wave_get_change / wave_get_prompt
              │       └── docs/waves/ (read), docs/plans/ (read), docs/prompts/ (read)
              │       [wave_current: returns data.waves[] of all non-closed waves (active→planned→paused), advisory drift detection on active; wave_get_change: supports bulk wave_id mode; wave_prepare: single-active-wave guard via another_wave_active diagnostic; wave_pause: transitions active→paused]
              ├── wave_get_handoff / wave_set_handoff
              │       └── docs/agents/session-handoff.md (read/write; wave_set_handoff triggers background refresh)
              │       [wave_close/wave_pause: targeted handoff update (Active wave line + Last verified only); close summary includes Owner/Status/Last verified metadata]
              ├── wave_open_gate / wave_close_gate
              │       └── .wavefoundry/guard-overrides.json (read/write); error on double-open, advisory on double-close
              │       [wave_pause/wave_close create: auto-close all open gates + gates_forced_closed advisory; wave_close dry-run: advisory only, no write]
              ├── code_list_files / code_read / code_keyword_search
              │       └── repo files (read-only; respects gitignore/aiignore/hardcoded excludes)
              ├── code_definition / code_references
              │       └── Python AST navigation; unsupported-language responses for non-Python
              ├── wave_new_* convenience tools
              │       └── docs/plans/ (write), lifecycle_id.py (import), background index refresh request
              ├── wave_add_change / wave_remove_change / wave_prepare
              │       └── docs/waves/ (read/write), docs/plans/ (read/write), background index refresh request
              ├── wave_index_health / wave_index_build
              │       └── .wavefoundry/index/ (read/write), .wavefoundry/framework/index/ (read/write), indexer.py (subprocess)
              ├── wave_validate / wave_garden / wave_sync_surfaces
              │       └── docs_lint.py / docs_gardener.py / render_platform_surfaces.py (subprocess)
              ├── [resources] wavefoundry://overview, wavefoundry://prompts, wavefoundry://architecture/current-state
              │       wavefoundry://wave/current, wavefoundry://session-handoff
              │       └── docs/ (read-only, raw markdown; no-write guarantee)
              └── [resource templates] wavefoundry://change/{id}, wavefoundry://wave/{id}
                      wavefoundry://prompt/{slug}, wavefoundry://seed/{slug}, wavefoundry://architecture/{slug}
                      └── docs/ + .wavefoundry/framework/seeds/ (read-only, raw markdown)
```

**Index build flow:**

```
setup_index.py --root .
  ├── dependency check → fastembed, numpy, mcp[cli] in current Python
  ├── prewarm docs/code embedding models in local cache
  ├── verify cached models in offline-only mode
  ├── indexer.py --root . --content docs   (default; docs/seeds only)
  ├── or with --include-code: indexer.py --root . --content all  (single subprocess, docs + code)
  ├── walk_repo()      →  respects .gitignore, .aiignore, hardcoded excludes
  ├── chunker.py       →  chunk_python / chunk_markdown / chunk_line_window
  ├── fastembed        →  BAAI/bge-small-en-v1.5 (docs/seeds and optional code)
  └── .wavefoundry/index/
        ├── docs.npy / docs.json
        ├── code.npy / code.json
        └── meta.json  (file hashes, model versions for incremental rebuild)

build_pack.py
  ├── stamps .wavefoundry/framework/VERSION
  ├── rebuilds .wavefoundry/framework/index/ for packaged framework docs/seeds
  └── writes wavefoundry-YYYY-MM-DDx.zip including framework/index/
```

## Current Risk Areas

| Risk | Details | Mitigation |
|------|---------|-----------|
| Framework dir accidentally deleted | `.wavefoundry/framework/` is tracked in git; restore with `git checkout HEAD -- .wavefoundry/framework` | Covered by normal git recovery |
| No CI/CD | No automated test runs on push | Framework tests run manually: `python3 .wavefoundry/framework/scripts/run_tests.py` |
| Index not built on first install | `fastembed`, `numpy`, and `mcp[cli]` must be available in the Python runtime; index built manually before server is useful | `setup_index.py` checks dependencies, prewarms/verifies the embedding model cache, and prints isolated tool-venv setup commands when missing |
| Search index drift or missing cache | Hook-driven indexing is not guaranteed in every agent environment, and query embedding must remain offline-safe | `docs_search` falls back to lexical search with structured diagnostics when the index is not ready or the semantic model is unavailable offline; per-query repo hash walks were removed to avoid O(repo) latency on every search; mutating MCP doc tools now request background incremental refresh for affected docs in non-hook environments; additional project index roots are explicit in `docs/workflow-config.json` `indexing.project_include_prefixes` rather than hidden repo-specific toggles |
| Lifecycle mutation drift between docs and files | Admitted change docs can drift between `docs/plans/` and wave folders when operators or tools bypass the normal lifecycle path | `wave_add_change`, `wave_remove_change`, and `wave_prepare` now relocate or repair placement and emit explicit diagnostics for duplicates or mismatched wave ownership |
| MCP contract migration complete for initial surface | Discovery, `wave_map`, envelopes, consolidated creation, prefix checks, `docs_search` kind validation, per-process caches (wave/plan lists, prompt resolution, `wave_help` catalogue snapshot, index reload on mutation), `resolve_path_under_root`, server-side rejection of unexpected tool kwargs, MCP resources/templates, and code navigation tools (`code_keyword_search`, `code_list_files`, `code_read`, `code_definition`, `code_references`) are all in place. Symbol navigation (milestone 2) supports Python only; future tree-sitter/LSP integration deferred. | `docs/specs/mcp-tool-surface.md` is the governing contract for follow-on MCP work |

## Verification Sources

This doc was verified from direct inspection of: `.wavefoundry/framework/scripts/`, `.wavefoundry/framework/seeds/`, repository root file listing, `docs/repo-index.md`.
