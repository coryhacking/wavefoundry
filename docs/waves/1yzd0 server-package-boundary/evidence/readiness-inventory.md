# 1yzd0 server-package-boundary: readiness inventory and demonstration

Owner: Engineering
Status: active
Last verified: 2026-09-24

Baseline: HEAD `902f7edc4d34d113a03ca93eba99da5a53988b69` (branch `main`). `git status` shows no tracked changes under `.wavefoundry/framework/scripts/`. The only untracked paths are `docs/waves/1yzd0 server-package-boundary/` and, from another session, `docs/waves/1yzj9 sensor-advisory-decisions/`. 1yzj9 is at status `planned`, and its docs mention no server modules. The overlapping waves the plan names are closed and committed: 1yv9l (`27ab7a95`, `3acafdeb`) and 1yzcz (`0d302ee3`). `.wavefoundry/framework/VERSION` is `1.27.0+ps9e`, and no `v1.27.0` tag exists. Released tags `v1.25.0` and `v1.26.0` are the supported older runners analysed below.

No repository file was edited. Every script and output is under `scratchpad/1yzd0/`:

| Artifact | Purpose |
| --- | --- |
| `scan_imports.py`, `scan.json` | AST reference census, with the predicate in the docstring |
| `analyze.py`, `summary.txt` | Importer tables per module |
| `classify.py`, `classification.json`, `classification.txt` | A1 classification |
| `consumers_prod.txt`, `test_path_refs.txt` | A2 consumers (production; tests) |
| `path_uses.py`, `path_uses.txt` | A3 path and identity census inside the moved set |
| `state_census.py`, `state_census.txt` | A4 module state ownership |
| `runner_attr_census.py`, `runner_attr_census.txt` | Old-runner attribute census |
| `demo/` | B demonstration: `build_tree.py`, `probe.py`, `run_all.py`, `results-py313.{json,txt}`, `results-py311.{json,txt}`, `packaging_probe.py` (+`.out.json`), `prefix_purge_probe.py` (+`.out.json`), `main_alias/` |

Interpreter: `~/.wavefoundry/venv/bin/python -B` (CPython 3.13.5). The demo matrix was re-run on `/opt/homebrew/bin/python3.11`. All 28 runs agreed on every observation, excluding ids and temp paths.

---


> **Rename (2026-09-25):** this inventory and `demo/` were produced under the package name `wavefoundry_server`. The operator later renamed it `wf_server` (change doc Decision Log). The findings are unaffected; only the name differs.

## A1. Moved set and module classification

**Universe predicate.** Every `*.py` directly in `.wavefoundry/framework/scripts/`: 112 files, plus the `wave_lint_lib` package counted as one module, for 113 in total. Tests and benchmarks are consumers, not members.

**Importer predicate** (`scan_imports.py`). A production file references `m` when its AST contains any of:

- `import m`, `from m import ...`, or a call whose first argument is the string `"m"` (`importlib.import_module`, `_load_script`, and similar);
- a string constant equal to `m` (purge sets, reserved names), or a dotted `"m.attr"` (patch targets);
- a `"m.py"` path literal.

Non-Python files are grep-scanned for the literal `m.py`.

**Class rule** (`classify.py`), applied in order:

1. Member of the moved set → *moved*.
2. `mcp_tool_extensions`, `mcp_tool_roster` or `record_paths` → *downstream declaration*. Requirement 2 names all three, and distributions edit them.
3. Has an `if __name__ == "__main__"` guard → *executable/CLI entry point*.
4. Otherwise → *retained shared substrate*.

A non-moved module is flagged **borderline** when every production importer is a moved module or `server`.

| Class | Count |
| --- | --- |
| moved | 12 |
| retained shared substrate | 59 |
| executable/CLI entry point | 39 |
| downstream declaration | 3 |

### Moved (12): source → destination `scripts/wavefoundry_server/<same basename>`

| Module | Reason (derivation) | Production importers outside the moved set |
| --- | --- | --- |
| `server_impl.py` | Composition root. Owns `register_mcp_surface`, `MIDDLEWARE`, the reload purge block and `_load_script`. | `server.py:74` (top), `memory_eval.py:726,861`, `retrieval_eval.py:2284` (local), `upgrade_extensions.py:342`, `upgrade_wavefoundry.py:5849` (local), and string/path identities (A3) |
| `mcp_tool_registry.py` | Registration support: the registry plus `apply_middleware` (ADR 1ye5y) | Only the string in `mcp_tool_extensions.RESERVED_MODULE_NAMES` (`:54`) |
| `codenav_handlers.py` | Handler roster (domain-map "Handler ownership") | `retrieval_eval.py:144` (identity path) |
| `graph_handlers.py` | Handler roster | none |
| `techdocs_handlers.py` | Handler roster | none |
| `memory_handlers.py` | Handler roster | `memory_cli.py:9` (`import memory_handlers`, module top) |
| `index_handlers.py` | Handler roster | `retrieval_eval.py:147` (identity path) |
| `upgrade_handlers.py` | Handler roster | none |
| `edit_gate_handlers.py` | Handler roster | none |
| `dashboard_handlers.py` | Handler roster | `upgrade_extensions.py:339`, `upgrade_wavefoundry.py:3196` (local imports) |
| `docs_handlers.py` | Handler roster | none |
| `context_efficiency_handlers.py` | Handler roster (projection and crediting extractors) | `project_context_efficiency.py:19` (local import; turn-end hook entry) |

### Borderline: flagged mechanically, recommended to stay retained

| Module | Production importers | Reason to retain |
| --- | --- | --- |
| `lifecycle_gates` | `server_impl` | Docstring: "Named lifecycle checks; sequencing and writes remain in the orchestrator." This is lifecycle validation, which Requirement 2 lists as shared substrate. |
| `sensor_runner` (not flagged; also imported by `lifecycle_gates`) | `lifecycle_gates`, `server_impl` | "Bounded project sensor execution, shared by explicit and lifecycle calls." |
| `operator_identity` | `server_impl` | Review-event attribution substrate |
| `install_log_lib` | `server_impl`, `upgrade_handlers` | "Shared library consumed by `wf_audit_install` ... and any other tooling" |
| `tree_sitter_cache` | `codenav_handlers`, `server_impl` | Shared parse cache (a substrate, not response computation) |
| `commit_provenance`, `exploration_avoided`, `memory_supply` | Moved modules, reached only through `_load_script` | Domain libraries loaded through the flat `_load_script`. Moving them would need a package-aware loader, which Requirement 4 excludes. |
| `memory_eval`, `score_context_efficiency_pairs` | `_load_script` from memory and context-efficiency handlers | Also CLI entry points (main guard) |

### The rest, by class (from `classification.txt`)

- **Executable/CLI (39):** ann_reference_eval, build_pack, build_scan_allowlist, check_version, dashboard_server, docs_gardener, docs_lint, eval_chunker, gen_codebase_map, gpu_doctor, graph_call_census, graph_quality_eval, indexer, lexical_ranking_eval, lifecycle_id, memory_backfill, memory_cli, memory_eval, project_context_efficiency, prune_framework, render_agent_surfaces, render_platform_surfaces, repair_ppol_memory_staging, retrieval_eval, run_secrets_scan, run_tests, score_context_efficiency_pairs, **server** (the supported entry; stays flat), setup_index, setup_wavefoundry, sqlite_storage_migration, techdocs_audit, techdocs_audit_lib, techdocs_baseline, upgrade_bridge_bootstrap, upgrade_bundle, upgrade_wavefoundry, wave_gate, wf_cli.
- **Retained shared substrate (59):** _tag_utils, accel_embedder, agent_surface_integrity, chunker, cli_stdio, commit_provenance, context_efficiency, dashboard_lib, design_token_build, exploration_avoided, gardener_metadata, graph_cluster, graph_di_signals, graph_indexer, graph_query, graph_snapshot, graph_store, index_compatibility, index_paths, index_source_guard, index_state_store, install_log_lib, lifecycle_gate_support, lifecycle_gates, lifecycle_lock, machine_authority, marker_namespaces, memory_records, memory_supply, model_bundle, operator_identity, path_containment, provider_policy, public_contract, publication_control, reconcile_scan, repo_root, review_evidence, review_policy, review_policy_reconcile, review_policy_upgrade, runtime_advisory, runtime_lock, scan_secrets, scanner_skips, sensor_runner, setup_readiness, setup_reconciliation, setup_requirements, sqlite_runtime, sqlite_vector_store, storage_identity, subprocess_util, tree_sitter_cache, upgrade_extensions, upgrade_lib, upgrade_protocol, venv_bootstrap, wave_lint_lib.
- **Downstream declaration (3):** mcp_tool_extensions, mcp_tool_roster, record_paths.

**Note on `server_impl.py`.** It carries a legacy `if __name__ == "__main__": raise SystemExit(main())` at `server_impl.py:21709`. `git grep` finds no documented `python server_impl.py` invocation. A flat alias would not run this main, so decide whether to keep it in the package.

---

## A2. Consumers of moved modules

### Production consumers outside the moved set (`consumers_prod.txt`)

- `server.py:74`: `import server_impl` at module top, plus attribute use throughout. The v1.25.0 and v1.26.0 runners read the same 17 attributes (`runner_attr_census.txt`). All of them are bound in HEAD's `server_impl` namespace; `_SETUP_STARTUP_*` are runner writes.
- `memory_cli.py:9`: `import memory_handlers`. Its handler bodies do a function-local `import server_impl`.
- `memory_eval.py:726,861`: `import server_impl as srv` (loaded via `_load_script("memory_eval")`).
- `retrieval_eval.py:2284`: `import server_impl as loaded_server`, then `production_scripts_dir = Path(server_file).resolve().parent` (`:2289-2293`). Identity uses are covered in A3 and D.
- `project_context_efficiency.py:19`: `import context_efficiency_handlers` (turn-end hook).
- `upgrade_extensions.py:339,342`: `import dashboard_handlers`, with a fallback `import server_impl`. This runs from the new archive, before extraction, against the installed tree.
- `upgrade_wavefoundry.py:3196` (in `phase_cleanup`): `import dashboard_handlers`. `upgrade_wavefoundry.py:5849` (in `main`, after extraction): `import server_impl` for `_memory_backfill_batch_locked`.
- String-only references:
  - `mcp_tool_extensions.py:50-57` `RESERVED_MODULE_NAMES` (`"mcp_tool_registry"`, `"server"`, `"server_impl"`);
  - `lifecycle_gate_support.py:789` (`"server_impl"`, a seat-routing keyword over wave text);
  - `setup_readiness.py:43` `SOURCE_FILES`;
  - `retrieval_eval.py:143-148` `PRODUCTION_RETRIEVAL_MODULES`.
- Docstrings and comments only: `render_platform_surfaces.py:269,1633`, and the rendered hooks under `.claude/.cursor/.github/.windsurf/hooks/*.py:273` (comment).
- Distribution extension modules (not in the tree). Per `docs/specs/mcp-tool-surface.md:115-116`: "extension may import `server_impl` by module name and use its helpers; underscore-prefixed helpers such as `server_impl._ensure_no_extra_args` are reachable". The alias must therefore expose private names too.
- No `runpy` use and no `subprocess` invocation of any moved file path exists in production. Direct execution of `server_impl.py` was not found anywhere.

### What is not a consumer

- `build_pack` has no moved names; `collect_files` is recursive (A5).
- `wf_cli`, `render_agent_surfaces`, `render_platform_surfaces` and `setup_wavefoundry` import no moved module. `render_platform_surfaces` imports `mcp_tool_roster`, which imports `mcp_tool_extensions`, and both stay flat and stdlib-only.
- `setup_readiness` names `server_impl.py` only in `SOURCE_FILES`.

### Tests (`test_path_refs.txt`: 380 non-import references across 43 test files; 58 import sites of `server_impl`)

Load seams:

- `server_tools_support.load_server` (`:55-78`) spec-loads `server.py` as `"server"` and returns `sys.modules["server_impl"]`.
- `test_memory_records.load_independent_server` (`:56-68`) calls `spec_from_file_location("server_impl_proc2", SCRIPTS_ROOT / "server_impl.py")`.
- `test_lifecycle_mutation_lock.py:89` does the same in a child process.
- `test_handler_modules` imports via `importlib.import_module`.
- String patch targets such as `"index_handlers._index_is_up_to_date"` appear 63× for index, 57× for dashboard, 3× for upgrade and 2× for docs.

Test censuses tied to flat paths:

- `test_lifecycle_gates_structure._direct_local_imports` (`:201-213`) keeps only names where `(SCRIPTS / (name + '.py')).is_file()`. A canonical `from wavefoundry_server.graph_handlers import` maps to `wavefoundry_server`, which is not a `.py` file. The census would **silently drop every handler**.
- `test_reload_picks_up_every_added_module` (`:368-389`) asserts `Path(module.__file__) == SCRIPTS / (name + ".py")` for every purge entry.
- There are 139 `server_impl.py` path literals, mostly `(SCRIPTS / "server_impl.py").read_text()` source censuses. Once that file becomes an alias, any `assertNotIn` or absence check over it passes vacuously.
- `test_lifecycle_gates.py:284` computes `Path(srv.__file__).resolve().parents[3]`.
- `test_server_tools_retrieval.py:15650` resolves `index_state_store.py` beside `srv.__file__`.

---

## A3. Path and identity uses (`path_uses.txt`), classified

`server_impl.py`:

| Line(s) | Use | Classification |
| --- | --- | --- |
| 33-66 | Purge block over `sys.modules` (flat names plus a `wave_lint_lib` prefix) | **Must change.** It must also evict `wavefoundry_server.<handler>` keys. It must never evict the parent package or itself (demo). |
| 72-74 | `SCRIPTS_DIR = Path(__file__).resolve().parent`, then `sys.path.insert(0, SCRIPTS_DIR)` | **Must change** to the scripts root (`.parent.parent`). The naive move puts the package dir on `sys.path`, which yields duplicate top-level module instances (demo). |
| 4431 | `_read_chunker_version`: `chunker.py` beside `__file__` | Must change to the scripts root. Silent `""` on miss. |
| 4483-4484 | `_load_script`: `Path(__file__).resolve().parent / f"{name}.py"` | **Must change** to the scripts root (demo: FileNotFoundError) |
| 4671, 4744 | `docs_lint.py` beside `__file__` | Must change |
| 8962-8963 | `_audit_harness_coherence` reads `server.py` and `server_impl.py` beside `__file__`, with `if not src_path.is_file(): continue` | Must change. Moved as-is, it silently drops `server.py` from the live-tool census. |
| 12009 | `_default_template`: `Path(__file__).parent.parent / "install"` | Must change (silent fallback miss) |
| 12045-12046 | `_indexer_module` spec-loads `indexer.py` beside `__file__` | Must change |
| 13031-13042 | `_get_chunker_module` spec-loads `chunker.py` and temporarily inserts its dir on `sys.path` | Must change |
| 15102, 15118 | `SERVER_IMPL_VERSION = _read_framework_pack_version()` reads `scripts_dir.parent / "VERSION"` | **Must change.** Moved as-is, it silently reads `scripts/VERSION`, returns `""`, and `impl_matches_disk` becomes null. |
| 17066 | `Path(mcp_tool_extensions.__file__)`, declaration provenance | Keep (declaration stays flat) |
| 17135-17164 | `_load_extension_module` uses `SCRIPTS_DIR` and `PathFinder.find_spec(name, [scripts_dir])` | **Must keep the scripts root.** Correct once `SCRIPTS_DIR` is fixed; the extension location rule requires flat. |
| 21709 | `__name__ == "__main__"` legacy main | Provenance/legacy; decision needed |

Handlers:

| Location | Use | Classification |
| --- | --- | --- |
| `index_handlers.py:375`, `802`, `990-992` | `Path(server_impl.__file__).parent` for `indexer.py` (dry-run), `setup_index.py`, and the lock-owner spec-load | **Must change.** Use `server_impl.SCRIPTS_DIR` or equivalent. |
| `upgrade_handlers.py:387`, `401` | Insert `Path(server_impl.__file__).parent` on `sys.path` | **Must change** (sys.path contamination). `:401` silently falls back to a literal sentinel. |
| `upgrade_handlers.py:1145` | `upgrade_wavefoundry.py` beside `server_impl.__file__` | **Must change**, else a `script_not_found` error |
| `dashboard_handlers.py:124-125` | `dashboard_server.py` | Must change |
| `docs_handlers.py:32` (`docs_gardener.py`), `96` (`render_platform_surfaces.py`), `273-275` (sys.path insert), `288` (`run_secrets_scan.py`) | Scripts-root lookups | Must change |
| `index_handlers.py:1298` | `root/.wavefoundry/framework/scripts/indexer.py` | Keep (root-relative, correct) |
| `index_handlers.py:1135` | `index_dir.parent.parent` | Not a scripts path |
| `mcp_tool_registry.py:131` | `source_module=getattr(fn, "__module__", None)` | Provenance only: `"server_impl"` becomes `"wavefoundry_server.server_impl"`. Not published in any response (`grep source_module` shows only the registry). `test_mcp_tool_registry.py:78` compares dynamically. |
| codenav/graph `'.py'` literals | Language suffix checks | n/a |

Identity-bearing uses outside the moved set:

| Use | Classification |
| --- | --- |
| `retrieval_eval.PRODUCTION_RETRIEVAL_MODULES` (`:143-148`), `_production_identity` (`:1488-1511`, hashes `scripts_dir / name`), and `production_scripts_dir = Path(server.__file__).parent` (`:2288-2293`) | **Must change** (see D) |
| `retrieval_eval._evaluator_identity` (`:1420-1429`), `sha256(retrieval_eval.py)` | Unaffected by the move itself, but any edit to `retrieval_eval.py` changes it |
| `docs/evals/retrieval-quality-golden.json` | 14 relevance rows in 10 of 35 fixtures target moved files: server_impl ×11 (10 symbol, 1 content), index_handlers ×2, codenav_handlers ×1. These are path plus fixture digest (see D). |
| `setup_readiness.SOURCE_FILES` (`:40-46`) includes `'server_impl.py'`, hashed relative to `setup_readiness.SCRIPTS` by `capture_loaded_identity` (`:140-148`) and `assessment_signature` | **Must change.** Otherwise edits to the package implementation never raise `loaded_code_stale`, and the flat alias bytes stand in for the implementation. |
| `context_efficiency` source credit (`:744`, `sha256(relative path)`) | Provenance only: a moved path is a new source identity mid-wave |
| `lifecycle_gate_support:789` keyword `server_impl` | Heuristic; keep (optionally add `wavefoundry_server`) |
| `mcp_tool_extensions.RESERVED_MODULE_NAMES` | Keep. The parent `wavefoundry_server` is refused anyway through the `sys.modules` collision check in `_load_extension_module` (`:17135-17139`). |
| `tests/fixtures/register-surface-handler-digests.json` | Body digests, path-independent. The test reads `SCRIPTS_DIR / "server_impl.py"` (`test_mcp_tool_registry.py:287,324,333`) and must read the package file. |
| `tests/fixtures/vector_backend_eval_1xhbo_public.json` (keys `"server_impl.py"`) and `benchmarks/model_swap_code_queries.json` | Historical/benchmark data; provenance only |

---

## A4. Reload machinery today

**`wf_reload_mcp`** is registered by the runner, inside `server.build_server`, as a survivor tool (`server.py:205` `_RELOAD_SURVIVOR_TOOLS`). It refuses when durable context-efficiency projection fails, then calls `perform_mcp_reload(notify="defer")` (`:616`).

**`perform_mcp_reload`** (`server.py:360-547`), under `_reload_lock`:

1. `old = _get_handler()`, then `old.close()`; failures become warnings.
2. `server_impl._script_cache.clear()` (`:395`).
3. Evict every `sys.modules` key starting with `wave_lint_lib` (`:399-402`).
4. `server_impl = importlib.reload(server_impl)` (`:403`). This is **not wrapped in try**, so an import-time failure propagates after the handler has already closed. The hazard exists today and is unchanged.
5. The re-executed module top of `server_impl` runs the **purge block** (`server_impl.py:33-66`). It deletes `wave_lint_lib*` and 27 named flat keys:
   - `review_evidence`, `review_policy`, `lifecycle_lock`, `publication_control`, `context_efficiency`, `public_contract`, `gardener_metadata`, `operator_identity`, `record_paths`, `marker_namespaces`;
   - `lifecycle_gate_support`, `lifecycle_gates`, `sensor_runner`, `index_source_guard`, `path_containment`;
   - `mcp_tool_registry`, `mcp_tool_extensions`;
   - the ten `*_handlers`.

   The module-top imports then re-import them fresh.
6. `_record_runner_identity()` (`:113-171`) writes `server_impl._SETUP_LOADED_IDENTITY/_SETUP_STARTUP_ROOT/_SETUP_STARTUP_RESULT` and calls `set_server_runner_version(SERVER_RUNNER_VERSION, runner_files=...)`.
7. `build_handler(old.root)`, then `_set_handler`. On failure it restores the old handler.
8. `_refresh_mcp_tool_surface(_mcp)`: remove every non-survivor tool, then `server_impl.register_mcp_surface(mcp, _get_handler)`. That call re-installs extensions from exact bytes (`_install_extension_tools`) and applies `MIDDLEWARE` through `mcp_tool_registry.apply_middleware`. The step then diffs descriptions.
9. Notification dispatch, `version_payload`, and the `runner_stale` diagnostic.

**Not reloaded.** The bootstrap exclusions `repo_root`, `setup_readiness`, `venv_bootstrap` and `subprocess_util` (`test_lifecycle_gates_structure.py:220-222`), plus any module imported only lazily. The runner files `server.py` and `venv_bootstrap.py` are never reloaded. `SERVER_RUNNER_FILES` and `SERVER_RUNNER_VERSION` (`server.py:89-107`) are a content hash captured at launch, and `wf_server_info` recomputes it for `runner_stale`.

**`setup_readiness.capture_loaded_identity`** hashes every flat basename in `SOURCE_FILES`, including `server.py` and `server_impl.py`. The runner captures it once at import (`server.py:32`). Because `server_impl.py:412-413` only captures when the name is absent from `globals()`, the value survives in-place reloads.

**State ownership** (`state_census.txt`):

- **Runner (`server.py`):** `_handler` (the ImplHandler instance), `_mcp` (the FastMCP instance), `_reload_lock`, `_root`, `_SETUP_LOADED_IDENTITY`, `_STARTUP_*`, and the global `server_impl` reference.
- **`server_impl`:**
  - rebound via `global`: `_MCP_INSTANCE`, `_TOOL_REGISTRY`, `_EXTENSION_PROVENANCE`, `_runner_version`, `_runner_files`, `_CHUNKER_MOD`, `_chunker_version_cache`, `_LANGUAGE_VOCABULARY_CACHE`;
  - mutable containers, including `_script_cache`, `_RETRIEVAL_LEDGER`, `_DEGRADED_LOG_STATE/LOCK`, `_FTS_SERVE_LOCK/STATE`, and 37 in total.
- **Handler-owned containers re-exported by name into `server_impl`** (shared object until the next reload):
  - `index_handlers`: `_FRESHNESS_CACHE`, `_BACKGROUND_BUILD_PIDS`, `_DASHBOARD_CHILD_PIDS`;
  - `memory_handlers`: `_MEMORY_RECORDS_CACHE`, `_MEMORY_BETWEENNESS_CACHE`;
  - `context_efficiency_handlers`: `_STATE_SOURCE_EXTRACTORS`;
  - `edit_gate_handlers`: `_VALID_GATES`;
  - `upgrade_handlers`: `UPGRADE_SUMMARY_TERMINAL_KEYS`.
- **Private `sys.modules` keys:** `_wavefoundry_<name>` from `_load_script`, and `wf_server_chunker`. Extension modules sit under their declared public names with `__wf_extension__`.

**Pre-existing finding, not caused by this migration.** `upgrade_handlers.py:1511-1512` runs `import server as _srv; _srv.perform_mcp_reload()`. In production the runner is `__main__` (`.mcp.json` launches `server.py`), and nothing aliases `sys.modules["server"]`, so this import creates a second runner module with `_handler=None, _root=None`. The model in `demo/main_alias/` shows exactly that: `'import server -> perform': 'handler_not_ready'`. Only the test seam registers `sys.modules["server"]` (`server_tools_support.py:65`). So the automatic post-upgrade in-process reload most likely reports `handler_not_ready`, and the explicit `wf_reload_mcp` (the `__main__` closure) is the path that actually reloads. This was not executed against the real server.

---

## A5. Packaging and upgrade

**`build_pack.collect_files`** (`build_pack.py:211-237`) is `os.walk` with in-place directory filtering. `demo/packaging_probe.py` ran the real `collect_files` and `write_manifest` on a temp tree:

- `scripts/wavefoundry_server/{__init__,server_impl,graph_handlers}.py` are included with correct arcnames.
- `__pycache__`/`.pyc` and `scripts/tests` are excluded.

**The plan's claim holds; no change is needed.**

**Archive reads by flat path:**

- `upgrade_protocol._pack_module_names` (`:96-102`) counts only flat modules: `"/" not in name[len(prefix):]`.
- `_validate_imports` (`:105-118`) uses `ast.walk`, so it also checks **function-local** imports of every `MANIFEST`-listed mandatory module (`MANDATORY_FEATURE_MODULES`, `:23-32`: upgrade_wavefoundry, upgrade_extensions, upgrade_protocol, lifecycle_lock, publication_control, review_policy, review_policy_reconcile, review_policy_upgrade) against that flat set.
- These three functions are byte-identical (AST digests) in v1.25.0, v1.26.0 and HEAD. The **installed** runner validates the **new** pack (`upgrade_wavefoundry.py:1513` in both tags).

The probe executed three cases against the real functions:

| Case | Result |
| --- | --- |
| Mandatory module does a local `import server_impl`, flat alias present | accepted |
| `import wavefoundry_server.server_impl` | **refused**: "mandatory module upgrade_wavefoundry.py has unavailable import wavefoundry_server" |
| `import server_impl` with the flat alias absent | **refused** |

**Consequence:** the flat `server_impl.py` and `dashboard_handlers.py` are *required* for a 1.25 or 1.26 runner to accept the pack, and mandatory upgrade modules must never spell a package import, not even function-locally. Another check hits the same constraint: `_load_extension_module` (upgrade side, `upgrade_wavefoundry.py:1074-1110`) execs the new `upgrade_extensions.py` inside the old process, with the **installed** scripts on `sys.path`.

**Other upgrade and packaging paths:**

- `_validate_mandatory_imports_in_subprocess` (`:130-194`) extracts nested members too (`destination.parent.mkdir`). Package files are therefore available to the isolated child, but the AST gate above runs first.
- Extraction (`_extract_feature_members`, `:899-914`) is prefix-based (`.wavefoundry/`), so the package is extracted.
- `prune_framework.prune` (`:91-155`) deletes old-MANIFEST-minus-new-MANIFEST entries and empty directories. Retained flat aliases stay in the new MANIFEST, so nothing is pruned.
- `upgrade_bundle`/`upgrade_bridge_bootstrap` use prefix-based members and launch `scripts/upgrade_wavefoundry.py` (retained flat).

**`upgrade_handlers` subprocess launches:**

- `wf_upgrade_response` (`:1145`) launches `<python> Path(server_impl.__file__).parent/"upgrade_wavefoundry.py"`. The path must come from the scripts root after the move. For an old in-memory implementation it is the flat path, which is correct.
- `_load_upgrade_lib` and `_upgrade_summary_sentinel` insert that directory into `sys.path`.

**Old-runner window** (code reading; see C for the matrix). The installed `upgrade_wavefoundry.py` (P1) extracts the new pack and then, in the same process:

- execs the new `upgrade_extensions` hooks;
- spawns new flat CLIs: `render_platform_surfaces.py`, `prune_framework.py`, docs gate, `setup_index.py`/`indexer.py`;
- imports the **new flat** `memory_backfill` and `server_impl` (`:5849`) in-process.

`--update-index` and `--cleanup` run as new-code processes; `--cleanup` imports the new flat `dashboard_handlers` (`:3196`).

---

## B. Alias-strategy demonstration (scratch fixtures)

`demo/build_tree.py` writes a disposable tree with these parts:

- a runner whose reload code has the **same shape as HEAD, v1.25 and v1.26**: `server_impl._script_cache.clear()`, the `wave_lint_lib` eviction, `server_impl = importlib.reload(server_impl)`, then `_record_runner_identity()`-style attribute writes;
- a flat shared substrate;
- a retained script loaded through `_load_script`;
- `wavefoundry_server/{__init__, server_impl, graph_handlers}.py`. The canonical `server_impl` has the purge block, `SCRIPTS_DIR`, a `global`-rebound `_runner_version`, the `_SETUP_LOADED_IDENTITY` globals guard, `_CACHE`, `_script_cache`/`_load_script`, and `from wavefoundry_server.graph_handlers import graph_response`. The handler does a function-local `import server_impl` exactly like the real handlers.

The tree path contains a space. `demo/probe.py` runs every scenario in a **fresh interpreter** and records the observed values.

Strategies:

- **(a)** Flat module does `sys.modules[__name__] = importlib.import_module("wavefoundry_server.X")`.
- **(b)** Flat stub does `from wavefoundry_server.X import *`.
- **(b2)** Stub plus a module `__getattr__` forwarding to the package module.
- **(c)** A meta-path `AliasFinder`/loader whose `create_module` returns the package module. The runner installs it; flat files are absent.

| Observation | (a) sys.modules alias | (b) star stub | (b2) star + `__getattr__` | (c) meta-path finder |
| --- | --- | --- | --- | --- |
| `import server_impl` is `wavefoundry_server.server_impl` | **True** | False | False | True |
| `import graph_handlers` is the package module | **True** | False (2 live module objects) | False (2) | True |
| private names via flat (`_load_script`, `_script_cache`, `_CACHE`, `_runner_version`) | all present | **missing** | present (forwarded) | present |
| mutable global shared | True | AttributeError | True | True |
| package `global` rebinding visible through flat | yes | missing | yes | yes |
| runner attribute write (`server_impl._SETUP_LOADED_IDENTITY = ...`) seen by package code | **runner-captured** | lost (`captured-from-disk`) | lost | runner-captured |
| `patch.object(flat graph_handlers, "helper")` affects the package call | **PATCHED** | no effect | no effect | PATCHED |
| `patch.object(flat server_impl, "shared_helper")` affects the handler | PATCHED | PATCHED | PATCHED | PATCHED |
| `inspect.getsourcefile(flat.respond)` and `respond.__module__` | package file / `wavefoundry_server.server_impl` | same | same | same |
| `flat.__file__` / `__spec__.name` | package / package | flat / flat | flat / flat | package file / **`server_impl` (spec overwritten)** |
| Reload with the runner after editing the package to v2, purge evicting flat **and** package keys | **served v2**, handler v2, parent attribute is the `sys.modules` entry, 1 live handler module, runner identity preserved, 2nd reload serves v3 | **reload raises** AttributeError `_script_cache` | reload runs but **serves stale v1** (two instances) | **reload is a no-op, serves stale v1**; module `__name__` rewritten to `server_impl` |
| Same, purge evicting **flat keys only** (a naive transplant of today's list) | **stale handler v1** while the implementation is v2 (canonical internal imports), or with flat-spelled internal imports (`from graph_handlers import`) | n/a | n/a | n/a |
| Old runner: tree installed as a flat monolith (v0), then replaced by the new layout, then the unchanged runner reload | **serves v2**; `reload()` returns the package module and the runner rebinds; identity preserved; next reload serves v3 | serves v2, but on the old stub object with runner identity lost (and in real code, underscore helpers missing) | same as (b) | **`ModuleNotFoundError: spec not found for 'server_impl'`**; the old runner cannot install the finder |
| `spec_from_file_location("_private", flat server_impl.py)` | returns a **hollow** object (no `respond`); the private `sys.modules` key is swapped to the package module | object with public names only | object | file absent |
| Consumer without the runner (memory_cli-like: `import graph_handlers` first) | works; flat is the package module | works, second instance | works, second instance | **ModuleNotFoundError** |
| Package initializer eager imports | none (`__init__` imports nothing) | same | same | n/a |

Additional executed probes:

- **Naive root** (`SCRIPTS_DIR = Path(__file__).parent` in the package). The package dir lands on `sys.path`, and `_load_script` fails with FileNotFoundError at `wavefoundry_server/retained_tool.py`. With flat-spelled internal imports, the handler loads as a *top-level* `graph_handlers` from the package file, and `wavefoundry_server.graph_handlers` is absent. With canonical imports, **two** live handler modules exist, and patching the flat name does not reach the package call.
- **Prefix purge including the parent** (`prefix_purge_probe.py`) produces `ImportError: module wavefoundry_server.server_impl not in sys.modules` on reload.

### Recommendation: strategy (a)

Flat compatibility files contain only `sys.modules[__name__] = importlib.import_module("wavefoundry_server.<name>")`, and the package holds canonical internal imports. Evidence:

- It is the only strategy that yields one module object per implementation under import, reload and old-runner reload.
- It keeps private names, `patch.object` on flat names and runner attribute writes working.
- It needs no runner change for the old-runner transition, because `importlib.reload` returns `sys.modules[name]`, which the alias replaced.
- It is identical on 3.11 and 3.13.

**Required companions, each demonstrated as load-bearing:**

1. **The purge must cover both keys.** The package `server_impl` purge evicts both the flat alias keys and `wavefoundry_server.<handler>` keys, and never evicts `wavefoundry_server` or `wavefoundry_server.server_impl`. Deriving both key sets from one alias table keeps them consistent.
2. **Scripts-root resolution.** `SCRIPTS_DIR` must be the scripts root, and every `Path(__file__)`/`Path(server_impl.__file__).parent` lookup listed in A3 goes through it.
3. **Hollow-object seams.** Loaders that `spec_from_file_location` a moved *flat* file get a hollow object. The two test seams must load the package file instead: `test_memory_records.load_independent_server` and `test_lifecycle_mutation_lock.py:89`.
4. **Eager alias registration (recommended).** Because canonical internal imports leave `sys.modules["graph_handlers"]` unset until some flat import happens (observed `modules_before: graph_handlers None`), consider registering the aliases eagerly from the alias table. This keeps the extension-name collision refusal in `_load_extension_module` and the purge census meaningful.

Rejected strategies:

- **(b)** loses private names (which the extension contract relies on), runner attribute writes and patching, and breaks reload outright.
- **(b2)** still creates second instances and cannot refresh on reload.
- **(c)** overwrites `__spec__`, making reload a silent no-op, and is unreachable for old runners and plain CLIs.

---

## C. Old-runner upgrade matrix (code reading plus scratch models)

Installed runner facts:

- v1.25.0 has no handler modules; its `server_impl` is a monolith.
- v1.26.0 has all ten handler modules plus `mcp_tool_registry`.
- Both have `UPGRADE_PROTOCOL_VERSION = MINIMUM_RUNNER_PROTOCOL = 2`.
- Both have identical `_pack_module_names`, `_validate_imports` and `validate_feature_pack`.
- Both runners use `server_impl = importlib.reload(server_impl)`.

| Step (who runs which code) | 1.25 installed | 1.26 installed | Works with retained flat paths + (a)? |
| --- | --- | --- | --- |
| `wf_upgrade` MCP tool (old in-memory impl) spawns `…/scripts/upgrade_wavefoundry.py` from `Path(server_impl.__file__).parent` | 1.25 monolith → flat dir | 1.26 `upgrade_handlers` → flat dir | Yes; the old in-memory modules are flat |
| P1 = **installed** `upgrade_wavefoundry.py` runs `validate_feature_pack(new zip)` with the **installed** `upgrade_protocol` | old rules | old rules | Yes **only if** the new mandatory modules import flat names only and the flat `server_impl.py` and `dashboard_handlers.py` exist (demonstrated) |
| P1 execs the **new** `upgrade_extensions` pre_extract hook against the installed tree: `import dashboard_handlers`, else `import server_impl` | ImportError, then the 1.25 `server_impl.wf_stop_dashboard_response` | flat `dashboard_handlers` | Yes (unchanged). The new `upgrade_extensions` must not import the package at module top, or P1 logs "load error — skipping" and loses its hooks. |
| P1 extracts every `.wavefoundry/` member (package included), then runs new flat CLIs as subprocesses (render, prune, docs gate) | new code | new code | Yes |
| P1 in-process: `import memory_backfill`, then `import server_impl` (new flat alias → package), then `_memory_backfill_batch_locked` | 1.25 `upgrade_wavefoundry:5797` | 1.26 `:5809` | Yes. The name is bound in HEAD's namespace (`runner_attr_census`). Failure is already caught (fallback recovery path). Mixed old and new substrates in P1 are pre-existing. |
| `--update-index` / `--cleanup` processes (new code) import the new flat `dashboard_handlers` | 1.25 cleanup ran in-process `import server_impl`; the new cleanup process is new code | same | Yes |
| MCP process after upgrade: `import server as _srv; perform_mcp_reload()` in the old `upgrade_handlers` | n/a (1.25 code path similar) | second `server` module | Pre-existing `handler_not_ready`, unaffected by the move |
| Operator `wf_reload_mcp`: old runner reloads the old flat module object; spec found by name leads to the new flat alias | old runner | old runner | **Yes (demonstrated in the model).** It serves the new package, the runner rebinds to the package module, identity is preserved and later reloads work. Every attribute the old runner reads is bound (`runner_attr_census`). If the new pack changes `server.py`/`venv_bootstrap.py`, `runner_stale` asks for the existing restart. |
| Old runner `setup_readiness` (not reloaded) keeps the old `SOURCE_FILES` | flat names | flat names | New bytes of the flat alias `server_impl.py` differ, so `loaded_code_stale` asks for a restart (expected). A new package-aware `SOURCE_FILES` takes effect only after a restart. |

Not executed:

- A real archive build (`build_pack` writes VERSION/MANIFEST into the repo, which is forbidden here).
- A real 1.25 or 1.26 install upgraded to a package-layout pack: no such pack exists yet. Only the old-runner reload was modelled, in scratch.
- The live MCP host reload.
- The `__main__`/`import server` split against the real `server.py`; it was modelled only.
- Native Windows, and any interpreter other than CPython 3.11/3.13 on macOS.
- Torn and partial extraction. By reading: the alias present without the package makes `import server_impl` raise ImportError. The runner's startup catch reports "run `wf setup`", and a reload raises after the handler closed. That is the same class as a SyntaxError reload today.

---

## D. Evaluator identity and required sequencing

**Retrieval evaluator (`retrieval_eval.py`).** The file paths of moved modules are bound in three ways:

1. **Production identity.** `PRODUCTION_RETRIEVAL_MODULES` names `server_impl.py`, `codenav_handlers.py` and `index_handlers.py` by flat basename. `_production_identity(scripts_dir)` hashes `scripts_dir / name`, and `scripts_dir = Path(server.__file__).parent`.
   - Under (a), `server_impl.__file__` becomes `wavefoundry_server/server_impl.py`, so the evaluator would read `wavefoundry_server/indexer.py` and fail with `EvaluationInvalid("production_unreadable")`. That is a **hard failure: the evaluator cannot run after the move without an edit**.
   - Under a stub strategy it would silently hash alias bytes instead of the implementation.
   - `_git_binding` uses `PRODUCTION_MODULE_PREFIX + name`.
2. **Evaluator identity.** It is `sha256(retrieval_eval.py)` plus schemas. Any edit needed for item 1 changes it. `_validate_baseline_compatibility` then refuses every existing baseline with "baseline evaluator identity differs" (`:2022-2024`). That includes the current reference `docs/reports/retrieval-quality-1ymzq-after.json`, per `docs/contributing/review-and-evals.md`.
3. **Golden fixture.** `docs/evals/retrieval-quality-golden.json` has 14 relevance rows in 10 of 35 fixtures pointing at moved files, 12 of them symbol anchors (for example `_classify_question` in `server_impl.py`).
   - After the move, left unedited, the symbol anchors resolve through `code_outline_response(root, ".../server_impl.py")` on the alias and become unresolved, which invalidates the run (`_resolve_declaration`). Results returned under `wavefoundry_server/...` never match.
   - Edited, `fixture_digest` changes, and baseline comparison is refused ("baseline fixture digest differs"). Worse, the edited fixture cannot run on the pre-move tree: `load_fixture_corpus` refuses nonexistent relevance paths with `stale_corpus` (`:713-716`).

Other evaluators contain no moved paths:

- `graph_quality_eval` binds `graph_indexer.py`.
- `lexical_ranking_eval._mechanism_identity` binds `index_state_store` function sources.
- `memory_eval` binds fixtures only, reaching `server_impl` by name.
- `ann_reference_eval` has no moved references.

**Sequence required before any source move:**

- **E0: evaluator-only change, its own reviewed step, before the move.**
  - Make production identity layout-independent: keep logical keys (`server_impl.py`, and so on), resolve each to the file that actually implements it (the package file when present, else flat), and take the scripts root from the evaluator's own location or `server.SCRIPTS_DIR` instead of `server.__file__`.
  - Resolve golden relevance paths through the same explicit, reviewed moved-path table, both for anchor resolution and for result-path matching, so the fixture and its digest stay unchanged.
  - This change moves the evaluator identity once, on purpose.
- **E1: approved common baseline.** Record R_before with the E0 evaluator on the pre-move tree, at a stable complete generation on a quiet machine, and get it approved. By the current doc there is no reference receipt after an evaluator edit, so this is mandatory.
- **M: move** under (a), followed by an ordinary incremental index update (a new generation).
- **E2: R_after** with the same evaluator. Expect a `cross_generation` comparison, a changed production digest (implementation bytes changed by import and root adaptations), and unchanged `evaluator_identity`/`fixture_digest`, so it is a valid signed comparison.

**Alternative** (weaker, and honest about it): keep the evaluator byte-identical until after the move. Then accept a new post-move baseline plus a `computed` disclosure through `benchmarks/compare_retrieval_receipts.py`, which is not a signed receipt. That repeats the 1ymzq R2 precedent and does not meet the plan's "approved common evaluator baseline" wording.

`setup_readiness.SOURCE_FILES` is not an evaluation identity, but it must gain the package implementation files (A3). Old runners keep their captured `SOURCE_FILES` until restart.

---

## Contradictions and corrections to the change doc

- **`_load_script` and every other `__file__`-relative lookup need edits.** The plan says `_load_script` "continues resolving retained shared scripts from the actual scripts root". Its intent is right, but today the function resolves `Path(__file__).resolve().parent` (`server_impl.py:4484`), so moving it *requires* an edit. By `path_uses.txt`, the same holds for all ten `__file__`-relative sites in `server_impl` (lines 72, 4431, 4484, 4671, 4744, 8963, 12009, 12045, 13031, 15102; `_load_script` is one of them) and the ten `Path(server_impl.__file__)` sites in handlers (index ×3, upgrade ×3, dashboard ×1, docs ×3). Five of these insert that directory on `sys.path`, which the demo shows creates duplicate module instances: `server_impl` `SCRIPTS_DIR` (`:72-74`), `_get_chunker_module` temporarily (`:13034`), `upgrade_handlers:387,401` and `docs_handlers:273-275`.
- **Parts of ADR 1ye5y's 1yv9l section are accurate, and the constraint is stricter than stated.** `_load_script` is flat-by-filename (confirmed). "The upgrade path reads framework scripts by flat path from the archive" is accurate for `upgrade_protocol._pack_module_names`/`_validate_imports`. The stricter constraint: *old runners* enforce it on the *new* pack, so mandatory upgrade modules can never spell a package import, and the flat aliases for `server_impl` and `dashboard_handlers` are mandatory, not only compatibility niceties.
- **`build_pack.collect_files` needs no change**, as the plan claims (executed).
- **The existing reload-coverage census would go vacuous.** `_direct_local_imports` drops package imports, and `test_reload_picks_up_every_added_module` asserts flat `__file__`. Requirement 5's "derive coverage independently" needs a rewritten census, not an updated list.
- **`SERVER_IMPL_VERSION` and `setup_readiness.SOURCE_FILES` degrade silently** when moved naively. These are not named in the plan's identity list.

## Top risks

1. **Stale handlers after reload.** A naive transplant of the purge list serves stale handlers after reload (demonstrated).
2. **Duplicate instances.** Package-dir `sys.path` insertion via a naive `SCRIPTS_DIR` or a handler's `Path(server_impl.__file__).parent` creates duplicate handler instances and splits patch targets (demonstrated).
3. **Pack refusal by old runners.** A mandatory upgrade module importing `wavefoundry_server` makes 1.25/1.26 refuse the pack (demonstrated with the identical validation code).
4. **Evaluator cannot run after the move.** Without E0/E1 no signed before/after comparison is possible (code reading, with exact refusal messages).
5. **Hollow objects.** Spec-loaders of flat moved files get empty modules (demonstrated), which affects two test seams and any undiscovered distribution code that does the same.
6. **Vacuous source tests.** 139 test path literals read `server_impl.py` source, and absence checks over the alias pass vacuously. Route them through one canonical-path helper, plus a census that no test reads a moved flat path.
7. **Silent degradations in moved code.** `SERVER_IMPL_VERSION`, `_audit_harness_coherence` (drops `server.py`), `_default_template`, `_read_chunker_version` and `_upgrade_summary_sentinel` degrade silently rather than failing.

## Could not verify

- A real archive build, and a real 1.25→package or 1.26→package upgrade: no package pack exists, and building one in the repo is forbidden. The old-runner reload was modelled in scratch.
- The live MCP reload through a real host (runner as `__main__`). The `import server` second-instance effect on `upgrade_handlers:1511` is modelled, not observed on the real server.
- Native Windows, and Pythons other than CPython 3.11.x/3.13.5 on macOS.
- Semantic intent of each of the 139 test source-reading sites. They were counted and located (`test_path_refs.txt`), not individually classified.
- Whether memory-record basename targets and `benchmarks/model_swap_code_queries.json` basename matching still match a moved implementation (basenames are preserved, so likely, but not executed).
- Distribution (Waveforge) code outside this repository that may import moved modules by path.
