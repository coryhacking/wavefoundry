# Setup Leaks Framework Tests Into the Docs Index

Change ID: `2038p-bug setup-leaks-framework-tests-into-docs-index`
Change Status: `implemented`
Owner: framework-operator
Status: planned
Last verified: 2026-10-07
Wave: 204jj docs-index-eligibility-consistency

## Rationale

`wf setup` and every caller of `setup_index.py` compute a different docs-index corpus from every other index build. Setup forwards the workflow include prefixes to the indexer as an explicit override. Under that override, the docs layer treats every file under the configured code prefix `.wavefoundry/framework/scripts` as docs-eligible, framework tests included. Their docstring and comment chunks are written to `chunks_docs`. The next ordinary incremental (post-edit hook, MCP quiet-period monitor, mutation refresh, `index_build`) runs the indexer without the override, finds those rows ineligible and reaps them. The next setup then sees about 245 eligible files with zero rows, reports them as drifted and re-embeds them. No file changed, yet each setup pays about 55 to 60 s of embedding plus about 10 s of graph merge. Between a setup and the next incremental, `code_ask` and `docs_search` return `test_indexer.py` docstrings and `docs_lint` fixture prompts as documentation.

The leak contradicts stated intent. `AGENTS.md` says framework internals under `.wavefoundry/framework/scripts/tests/` are never in the semantic code index. The 1sek8 comment in `_build_index_locked` says code-ineligible test files must not flag. ADR `1p4xx` folds only the seeds and the framework README into the docs index. `docs/workflow-config.json` sets the docs prefixes to `[]`.

Brief: goal is that every launcher computes the same per-layer corpus, so setup and incremental builds stop undoing each other. Consumers are operators running `wf setup`, `wf update-indexes` and upgrades, and agents whose retrieval should not surface test docstrings as docs. Success means no `.wavefoundry/framework/scripts/tests/**` path is ever docs-eligible, a setup after an incremental reports zero drift, and the seed fold is unchanged.

Code-grounded facts (verified against the working tree on 2026-10-07, HEAD `2ebce84e`):

- `setup_index.build_index` (content `all`) calls `_merge_project_include_prefixes(docs, code)` and passes the union to `_run_indexer`, which appends `--project-include-prefix <p>` per prefix (`setup_index.py`, `_run_indexer` command build). Content `docs` forwards the docs prefixes; content `code` forwards the code prefixes. `main`'s `--graph-only` branch forwards the docs and code union for content `graph`.
- `indexer._effective_project_include_prefixes(root, index_dir, content, override)` returns `override` plus `FRAMEWORK_FOLD_DOCS_PREFIXES` for `docs` and `all` whenever `override` is non-empty. Without an override it reads `docs/workflow-config.json` itself, and `docs` gets only the workflow docs prefixes plus the fold.
- In `_build_index_locked`, `docs_eligible_rel` is built from `_effective_project_include_prefixes(..., "docs", project_include_prefixes)` with no test or extension filter. `_filter_code_files` and `include_tests` apply only to `code_eligible_rel`. `docs_prefix_eligible_rel` (the pre-union copy) is the drift candidacy set for docs builds.
- `_reap_stranded_vector_rows` deletes rows whose path is outside the current eligible set. `_detect_vector_drift` flags an eligible `file_meta` path with no canonical rows unless its entry records `chunks_emitted == 0`. The leaked entries record a non-zero count, so they flag.
- `project_layer_freshness` (index health) and `preflight_rebuild_sources` already compute eligibility with no override, so health and receipt-owned rebuilds agree with the incremental, not with setup.
- Graph and `file_meta` scope: `_merged_project_include_prefixes_for_graph` and `_project_meta_include_prefixes` return the override unchanged when one is given, and fall back to the workflow docs and code union when none is. Dropping the forward therefore leaves graph and `file_meta` scope unchanged for content `all` and `--graph-only` (setup forwards the union there). For `--docs-only` and `--code-only` when both the docs and code prefix lists are non-empty, setup forwards only one layer's list today, so graph and `file_meta` scope widens from that one list to the union. That matches what every bare launcher already computes and is an incidental fix of a pre-existing narrowing; `test_docs_only_graph_includes_workflow_code_prefixes_without_cli_args` already pins the union for a bare docs-only build.
- Two workflow-prefix readers exist with different coercion. `setup_index._workflow_project_include_prefixes` uses `_coerce_prefix_list` (accepts only lists, skips non-string items, normalizes backslashes). `indexer._workflow_project_include_prefixes` uses `tuple(configured.get("docs") or ())` and `_normalize_prefixes`, so a string value yields per-character prefixes and a non-string list item raises on `.strip()`. Once setup stops forwarding, the indexer's reader is the only one that decides eligibility, so its weaker coercion becomes load-bearing.
- A third, narrower reader exists in `indexer.project_index_inputs_stale` (code list only, `str(p)` coercion, no legacy boolean). It feeds a staleness check, not eligibility, and is out of scope here; recorded as a watchpoint.
- A repository-wide search for `project-include-prefix` finds exactly one forwarding site, `setup_index._run_indexer`. `tests/test_server_tools_retrieval.py::test_project_code_rebuild_does_not_forward_prefixes_indexer_self_reads` asserts `run_index_rebuild` does not forward. `tests/test_setup_index.py::test_build_index_can_forward_project_include_prefixes_for_code_pass` pins the defective forward and must be inverted.
- `indexer.parse_args` help for `--project-include-prefix` says it "applies to content=code", which is wrong: an override drives docs eligibility, `file_meta` and graph scope too. That inaccuracy is part of what made the forward look safe.
- Read-only check on 2026-10-07: `chunks_docs` and `chunks_code` hold 0 rows under `.wavefoundry/framework/scripts/tests/`. That matches the reaped half of the cycle, since an incremental has run since the last setup. The 246-path and about 4453-row figures come from the 2026-10-07 investigation taken right after a setup. The top-level tests directory holds 188 `.py` files plus subdirectory fixtures.

Caller census (every path that launches an index build, and whether it forwards an override today):
- Reader callers kept working by the delegation contract: `wf_server/server_impl.py` and `wf_server/index_handlers.py` call `indexer._workflow_project_include_prefixes(root).get("code", ())`; `tests/test_server_tools_lifecycle.py` patches that attribute; indexer's own `_effective_project_include_prefixes` and graph helpers call it by name.

- `setup_index.main` to `build_index` content `all` (default `wf setup`, `setup_wavefoundry` install and upgrade, upgrade Phase 4 `--update-index` and `--rebuild-index`): forwards the docs and code union. This is the defect site.
- `setup_index.main` to `build_index` content `docs` (`--docs-only`, the foreground half of `--background-code` and `wf update-indexes`): forwards the docs prefixes (`[]` here, so no flag; a project with docs prefixes gets a narrower graph and `file_meta` scope than the bare path).
- `setup_index.main` to `build_index` content `code` (`--code-only`, and the detached child spawned by `_spawn_background_semantic_build` for `--background-code` and `wf update-indexes`): forwards the code prefixes. No docs rows are written (`build_docs` false), but docs eligibility widens, so this pass cannot reap leaked rows. The background child re-enters `setup_index.py` with `--code-only` or `--docs-only`, so it reaches `_run_indexer` and is covered by the same fix.
- `setup_index.main --graph-only` (upgrade Phase 4b) to `_run_indexer` content `graph`: forwards the union. No semantic writes; graph scope equals the bare fallback.
- `setup_index.main --prewarm-only` (`setup_reconciliation`, upgrade storage recovery) and `--deps-only` (`setup_wavefoundry`): no index build.
- Rendered hook spawns in `render_platform_surfaces` (the `hook_helpers` and `claude_stop_source` bodies spawn `indexer.py --content all`): bare.
- `wf_server/index_handlers.run_index_rebuild` (MCP `index_build`, and the index-handler rebuild path that calls it with `full=True`): bare. Already pinned.
- `wf_server/index_handlers._start_background_index_refresh` (`--content all`), reached from the quiet-period monitor (`server_impl._maybe_refresh_if_stale`), the mutation refresh (`_trigger_background_index_refresh_for_paths`) and the FTS heal scheduler (`server_impl._fts_schedule_heal`): bare. Distinct from `run_index_rebuild`.
- `wf_server/index_handlers._index_is_up_to_date` dry-run spawn (`indexer.py --dry-run`): bare; reads no rows.
- `graph_query` graph-builder refresh: in-process `indexer.build_index(content="graph")` with no prefixes. Bare.
- `indexer.watch_index` (`indexer.py --watch`): in-process `build_index(root, verbose=...)` with no prefixes. Bare.
- `indexer.main` CLI: passes `--project-include-prefix` through when a caller supplies it. No in-tree caller does after this change. The flag stays for manual and test use.
- `--include-tests` and `--include-generated`: forwarded as their own flags, independent of the prefix forward. Removing the forward does not change what they select.

## Requirements

1. **Setup launches the indexer bare.** No `setup_index.py` path passes `--project-include-prefix` to `indexer.py`: not content `all`, `docs` or `code`, not the `_spawn_background_semantic_build` child, and not `--graph-only`. The indexer resolves include prefixes from `docs/workflow-config.json` itself, exactly as the incremental launchers do. `_merge_project_include_prefixes` and the prefix parameters of `build_index` and `_run_indexer` are removed once unused, and their test call sites are updated. `main` keeps its informational "Workflow policy" line, read through the single reader in Requirement 2.
2. **One workflow-prefix reader.** `indexer._workflow_project_include_prefixes` adopts setup's fail-safe coercion (`_coerce_prefix_list` semantics): accept only lists, skip non-string items, a string or dict value yields no prefixes, normalize backslashes, strip whitespace and leading or trailing `/`, drop empty tokens, dedupe in order, apply the top-level list shorthand to both layers, yield empty for both layers when the file is missing or malformed or `indexing` is not a dict, and map the legacy `include_framework_code_for_code_search` boolean to the scripts prefix only when the code list is empty. The reader lives in a new stdlib-only module `workflow_include_prefixes.py` (no framework imports, nothing run at import). `indexer` keeps `_workflow_project_include_prefixes` as a module-level callable returning the keys `docs` and `code`, delegating to the new module, and indexer's own callers keep going through that name, so `wf_server/server_impl.py`, `wf_server/index_handlers.py` and the test patch in `tests/test_server_tools_lifecycle.py` keep working. `setup_index` deletes `_workflow_project_include_prefixes` and `_coerce_prefix_list` and resolves workflow prefixes only through the new module for its "Workflow policy" line, adding no module-level import of `indexer` (its existing by-path loads of `indexer.py` for model and optimize helpers are unrelated and stay).
3. **One corpus per layer across launchers.** For a given tree and flags, a setup-launched build and a bare incremental compute identical docs and code eligibility. No path under `.wavefoundry/framework/scripts/tests/` is docs-eligible or code-eligible under default flags in either shape.
4. **Seed fold and self-hosting scope preserved.** The framework seeds and README stay in the docs index after a setup-launched build. `.wavefoundry/framework/scripts` and `.wavefoundry/framework/dashboard` non-test sources keep their code rows and their docstring rows in the docs table through the 1sek8 dual-output union. Graph and `file_meta` scope are unchanged for content `all` and `--graph-only`; for `--docs-only` and `--code-only` with both prefix lists non-empty they widen from one layer's list to the union, matching every bare launcher (an incidental fix of a pre-existing narrowing).
5. **Regression test from the real launcher.** A test drives `setup_index.main(["--root", <fixture>])`, patching only the process boundary: `subprocess.Popen` in `setup_index` is replaced by a shim that runs `indexer.main(cmd[2:])` in process and returns a fake process with `returncode` 0 and an empty `stdout` iterable, plus the prewarm, dependency and GPU hooks. It must NOT patch `_run_indexer` or the workflow reader. The fixture's workflow config names `.wavefoundry/framework/scripts` as a code prefix and holds a docstring-bearing file under `.wavefoundry/framework/scripts/tests/`. The test runs that setup build, then a bare incremental (`indexer.build_index` with no prefixes), then a second setup build. "Reaps zero rows" and "zero drift" are observed with `wraps=` spies on `indexer._reap_stranded_vector_rows` and `indexer._detect_vector_drift` plus an embedder call count. A test that calls `setup_index.build_index` directly would leave the mutant alive (it bypasses `main`'s prefix read and can be called with any prefixes), so it does not qualify. The forward-pinning test in `tests/test_setup_index.py` is inverted.
6. **Mutant kill.** Restoring the forward in `setup_index` (either the merge for content `all` or the per-content forward) makes the Requirement 5 integration test fail. The probe is run in a scratch copy and recorded in the Progress Log.
7. **One-off cleanup needs no rebuild.** After the fix, an ordinary incremental or the next `wf setup` reaps any leaked rows still present, and the setup after that reports no drift for test paths. No full rebuild, rechunk or manual SQL is required.
8. **Stale descriptions corrected.** The `_effective_project_include_prefixes` docstring stops describing setup as forwarding an override. The `indexer.parse_args` `--project-include-prefix` help says it overrides the workflow-config prefixes for every layer the run builds (docs eligibility, `file_meta`, graph), for manual and test use. The `test_fold_survives_forwarded_non_empty_override_prefixes` docstring says "a caller that passes an explicit override" instead of naming setup. `docs/architecture/data-and-control-flow.md` items 4 and 9 say the indexer reads `docs/workflow-config.json` itself and no launcher forwards prefixes.
9. **Proposed CHANGELOG bullet.** Recorded in the Progress Log for `## [1.29.0]` (Fixed).

## Scope

**Problem statement:** setup and incremental index builds disagree about which files belong in the docs layer. Framework test files oscillate in and out of the docs index on every setup and are re-embedded each time with no source change.

**In scope:**

- Requirements 1 to 9 in `setup_index.py`, `indexer.py` (reader, docstring, help text), their tests, and the data-and-control-flow architecture doc.

**Out of scope:**

- Changing `_effective_project_include_prefixes` semantics for an explicit override (alternative (b), see Decision Log).
- Hardening `_detect_vector_drift`. It is correct given consistent eligibility, and the fault is the inconsistent input.
- Persisting `--include-tests` or `--include-generated` across launchers (see Decision Log).
- The narrower reader in `indexer.project_index_inputs_stale` (watchpoint).
- Retrieval ranking changes. The pollution disappears with the rows.

## Acceptance Criteria

- [x] AC-1: `setup_index.main` with a fixture config holding non-empty docs and code lists, in default, `--docs-only`, `--code-only` and `--graph-only` modes, spawns no indexer argv containing `--project-include-prefix`, including the `_spawn_background_semantic_build` child argv; the inverted `tests/test_setup_index.py` test asserts this.
- [x] AC-2: The Requirement 5 test passes: `main` setup build, bare incremental whose `_reap_stranded_vector_rows` spy reaps zero rows, second `main` setup build whose `_detect_vector_drift` spy reports zero drifted paths and whose embedder is called for no files.
- [x] AC-3: In that test no `.wavefoundry/framework/scripts/tests/` path is docs-eligible or present in `chunks_docs` after any of the three builds; fails today on the first build.
- [x] AC-4: Restoring the forward in a scratch copy makes the AC-2 and AC-3 test fail; the probe and result are recorded in the Progress Log.
- [x] AC-5: After a setup-shaped build the fixture's seeds and README are in `chunks_docs`, its non-test framework script is in `chunks_code` with its docstring rows in `chunks_docs`, and `test_fold_survives_forwarded_non_empty_override_prefixes` still passes.
- [x] AC-6: On this repository after the fix, `wf setup` then an ordinary incremental leaves 0 rows under `.wavefoundry/framework/scripts/tests/` in `chunks_docs`, and a second `wf setup` log reports no drifted test paths; counts and log lines are recorded in the Progress Log.
- [x] AC-7: A live `docs_search` for a phrase from a `test_indexer.py` docstring returns no `.wavefoundry/framework/scripts/tests/` citation after a fresh `wf setup`.
- [x] AC-8: The `_effective_project_include_prefixes` docstring, the `--project-include-prefix` help text, the fold test docstring and `docs/architecture/data-and-control-flow.md` items 4 and 9 no longer describe setup forwarding prefixes or a code-only flag.
- [x] AC-9: The proposed CHANGELOG bullet is recorded in the Progress Log and present under `## [1.29.0]` after the wave's CHANGELOG pass.
- [x] AC-10: The change's own suites and every test it adds pass, the documents it edits validate, and no failure elsewhere is attributable to this change.
- [x] AC-11: Neither `setup_index` nor `indexer` defines its own prefix coercion (both use `workflow_include_prefixes.py`, which imports only the standard library; `setup_index` resolves workflow prefixes only through it and adds no module-level import of `indexer`), and a test over list, dict, legacy boolean, non-string items and a string value shows the reader never raises and never yields per-character prefixes.
- [x] AC-12: A hermetic test seeds leaked state with `indexer.build_index(project_include_prefixes=(".wavefoundry/framework/scripts",))`, runs the fixed setup-shaped build, and asserts the leaked `chunks_docs` test rows are reaped and the next build reports zero drift with no embedder calls.

## Tasks

- [x] Open `framework_edit_allowed`.
- [x] Create `workflow_include_prefixes.py` with the reader and `_coerce_prefix_list` semantics; make `indexer._workflow_project_include_prefixes` delegate to it; delete setup's reader and coercion helper and route the "Workflow policy" line through the new module; update every test that patches or calls the deleted reader (`tests/test_setup_index.py` patch sites and its direct reader tests, which move to the new module, and the `setup._workflow_project_include_prefixes` patch in `tests/test_indexer.py`); repoint the `_setup_deadlines` docstring that names the deleted function (Requirement 2, AC-11).
- [x] Add the reader coercion test over list, dict, legacy boolean, non-string items and a string value (AC-11).
- [x] Remove the prefix forward from every `setup_index` indexer launch, then remove the unused merge helper and parameters (Requirement 1, AC-1).
- [x] Invert `test_build_index_can_forward_project_include_prefixes_for_code_pass` as a four-mode `main` test covering the background child argv, and update the `_run_indexer` test call sites (AC-1).
- [x] Add the `main`-driven integration test with the in-process `indexer.main` shim and `wraps=` spies, and confirm it fails against the unfixed code in a scratch copy (Requirement 5, AC-2, AC-3, AC-5).
- [x] Add the hermetic leaked-state cleanup test (Requirement 7, AC-12).
- [x] Run the mutant-kill probe and record it (Requirement 6, AC-4).
- [x] Update the `_effective_project_include_prefixes` docstring, the `--project-include-prefix` help text and the architecture doc (Requirement 8, AC-8).
- [x] Reword the `test_fold_survives_forwarded_non_empty_override_prefixes` docstring to "a caller that passes an explicit override" (Requirement 8, AC-8).
- [x] Close `framework_edit_allowed`.
- [x] Live check on this repository: setup, incremental, setup, `docs_search` probe; record counts (Requirement 7, AC-6, AC-7).
- [x] Record the proposed CHANGELOG bullet in the Progress Log (AC-9).
- [x] Run `wf_validate_docs`, then the full suite last (`python3 .wavefoundry/framework/scripts/run_tests.py`) (AC-10).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws-1 reader, launcher and tests | implementer | - | Requirements 1, 2, 5, 6, 7 |
| ws-2 docs and live check | implementer | ws-1 | Requirements 7, 8, 9 |

## Serialization Points

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/workflow_include_prefixes.py`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `docs/architecture/data-and-control-flow.md`

## Platform Behavior

- macOS, Linux and WSL2: the change removes argv entries from the indexer command; the indexer already reads `docs/workflow-config.json` on these platforms for every bare launch.
- Windows: the setup launcher keeps its `pythonw.exe` preference and no-window flags; only the prefix arguments are dropped. The hardened reader normalizes backslashes to forward slashes, so bare resolution matches what setup forwarded. Behavior is inferred from the shared code path, not run on Windows.
- The integration test runs `indexer.main` in process through the `Popen` shim, with no subprocess or console, so it behaves the same on Windows. It uses repository-relative POSIX paths and temporary directories, so it runs unchanged on every platform.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md`: items 4 and 9 describe `setup_index.py` forwarding a merged `--project-include-prefix` policy; both are corrected to say the indexer resolves prefixes from workflow config for every launcher. No other architecture doc names the forward (`docs/architecture/chunking-and-indexing-pipeline.md` describes the config keys only and stays accurate).

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The root cause. |
| AC-2 | required | The oscillation and wasted re-embedding. |
| AC-3 | required | The corpus leak itself. |
| AC-4 | required | Proves the test guards the fix. |
| AC-5 | required | No regression of the seed fold or self-hosting scope. |
| AC-6 | important | Confirms cleanup needs no rebuild on a real index. |
| AC-7 | important | User-visible retrieval effect. |
| AC-8 | important | Stale descriptions would invite the forward back. |
| AC-9 | important | Release notes. |
| AC-10 | required | Change-local health. |
| AC-11 | required | One shared reader becomes the sole eligibility authority, so its coercion must be fail-safe and setup must resolve prefixes without importing the indexer. |
| AC-12 | required | Proves the leaked rows clean up hermetically, independent of the live check. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-07 | Planned from a read-only investigation the same day; every code anchor re-verified against the working tree; caller census taken by repository-wide search for the forwarding flag and every `setup_index` and indexer launch site. No parked plan in `docs/plans/` covers this. | Rationale facts and census. |
| 2026-10-07 | Proposed CHANGELOG bullet (under `## [1.29.0]`, Fixed): "`wf setup` no longer adds framework test files to the documentation index. Setup now resolves include prefixes the same way as every other index build, so setup and incremental refreshes agree on the corpus and a setup that follows a refresh no longer re-embeds unchanged files. A docs-only or code-only setup now gives the graph the same docs and code scope as every other build. The first index build after upgrading removes the framework test-file rows an earlier setup added; this is expected. Wave 204jj / 2038p." | AC-9 text. |
| 2026-10-07 | Readiness round 1 findings 1-11 applied; reader home moved to a stdlib-only module (coordinator); readiness round 2 items 1-7 applied (final round). | Rationale, census, Requirements 1 to 9, AC-1 to AC-12, Decision Log. |
| 2026-10-07 | Implemented (ws-1, ws-2 docs). New stdlib-only `workflow_include_prefixes.py` (`normalize_prefixes`, `coerce_prefix_list`, `read_project_include_prefixes`); `indexer._workflow_project_include_prefixes` and `indexer._normalize_prefixes` delegate to it; setup deleted `_workflow_project_include_prefixes`, `_coerce_prefix_list`, `_merge_project_include_prefixes`, its prefix key constants and every prefix parameter of `_run_indexer` and `build_index`, and reads the "Workflow policy" line through the new module (module-level import of the stdlib module only; no `indexer` import). Caller census as implemented: no `setup_index` launch forwards `--project-include-prefix` (content `all`, `docs`, `code`, `--graph-only`, and the background child, which re-enters setup and reaches the same bare `_run_indexer`); indexer callers, `wf_server/server_impl.py`, `wf_server/index_handlers.py` and the `tests/test_server_tools_lifecycle.py` patch still go through `indexer._workflow_project_include_prefixes`; the only remaining `--project-include-prefix` producer is `indexer.main`'s pass-through for manual and test use. Docstring, help text, fold-test docstring and `docs/architecture/data-and-control-flow.md` items 4 and 9 corrected; CHANGELOG bullet added under `## [1.29.0]` Fixed. | `setup_index.py`, `indexer.py`, `workflow_include_prefixes.py`, `docs/architecture/data-and-control-flow.md`, `CHANGELOG.md`. |
| 2026-10-07 | Tests: `test_setup_index.SetupIndexTests.test_main_never_forwards_project_include_prefixes_in_any_mode` (replaces the forward-pinning test; default, `--docs-only`, `--code-only`, `--graph-only`, `--background-code`, `--background-docs`, asserting both indexer and background-child argv); `test_indexer.SetupLaunchedCorpusParityTests.test_setup_and_incremental_builds_agree_on_the_corpus` (AC-2, AC-3, AC-5) and `test_leaked_rows_from_an_override_build_are_reaped_by_the_next_setup` (AC-12); `test_workflow_include_prefixes` (13 tests: coercion over list, dict, legacy boolean, non-string items, string and other malformed values, plus AST ownership checks for AC-11). Focused run in the repository: `test_setup_index`, `test_indexer`, `test_workflow_include_prefixes`, `test_bytecode_cache`, `test_server_tools_lifecycle`, `test_server_tools_retrieval`, `test_tree_kill_routing`: 2355 tests OK. `wf_validate_docs` passed. | Focused `run_tests.py --file` output. |
| 2026-10-07 | Probes in a scratch copy of the tree (rsync, fresh `git init`). Unfixed HEAD `setup_index.py` with the new tests: both `SetupLaunchedCorpusParityTests` tests FAIL, the corpus test on the first build ("setup build: framework test rows in chunks_docs", `.../tests/test_tools.py`). Mutant A (restore the union forward for content `all` in `_run_indexer`): killed by both parity tests and the four-mode test (`default`). Mutant B (restore the per-content forward: code list for `code`, docs list for `docs`, union otherwise): killed by both parity tests and all six four-mode subtests. Mutant C (revert `coerce_prefix_list` to the old indexer coercion): killed by `test_non_string_items_are_skipped` (error) and `test_malformed_values_never_raise_or_split_into_characters` (string and dict layer values). Mutant D (restore indexer's own legacy reader instead of delegating): killed by `test_indexer_reader_delegates_to_the_module`. Scratch sources restored and diffed equal to the repository afterwards. | AC-4 probe output. |
| 2026-10-07 | Deviation for review: (1) the moved reader tests live in a new file `tests/test_workflow_include_prefixes.py`, not in a Serialization Points file. (2) The parity tests also substitute `model_bundle` in `sys.modules` (so `main` never discovers or materializes a real model bundle from `~/Downloads` or `~/.wavefoundry`) and `setup_index._indexer_models` (the model list fed to the GPU prewarm hook); `_run_indexer`, the workflow reader and `_optimize_after_build` stay real. `subprocess.Popen` is replaced only in `setup_index`'s view of `subprocess` (a proxy), so the shim cannot reach other modules' subprocess use. The `wraps=` spies wrap a recording function around the real `_reap_stranded_vector_rows` and `_detect_vector_drift`. (3) `indexer._normalize_prefixes` (the override normalizer) also delegates to the module, so an override tuple now skips non-string items instead of raising. (4) The reader catches `ValueError` rather than only `json.JSONDecodeError`, so an undecodable file also yields empty layers. AC-6 and AC-7 live checks are left to the coordinator. | Implementer notes. |
| 2026-10-07 | Full suite in the scratch copy, run 1: 11713 tests, FAILED in 3 files, two attributable to this change and fixed: `test_extension_tool_modules` (the stock framework script census `mcp_tool_extensions.FRAMEWORK_SCRIPT_MODULE_NAMES` did not list `workflow_include_prefixes`; added) and `test_server_package` (the new test file read sources through `SCRIPTS_ROOT`; now uses `framework_files.source_path`). The third, `test_python_parse_diagnostics` ("git ls-files returned no Python files"), came from the scratch copy's empty `git init` and passes in the repository. Run 2 (scratch re-synced, files staged): 11713 tests, FAILED only in `test_setup_readiness` (readiness verdicts `indeterminate` under load: 79.5 s in the suite against 5.6 s alone); rerun alone in the scratch copy: 49 tests OK. No failure is attributable to this change. Deviation for review: the census registration in `mcp_tool_extensions.py` is a file outside the Serialization Points. The receipt-writing full suite in the repository is left to the coordinator. | Scratch `run_tests.py` logs; focused reruns OK. |
| 2026-10-07 | Coordinator live checks (AC-6, AC-7) on this repository after the fix: `wf setup` updated 1 file (this wave's record) and reported no drifted paths; a bare `indexer.py --root . --content all` incremental exited 0 with no reap or drift output; a second `wf setup` made 0 semantic file updates; `chunks_docs` and `chunks_code` hold 0 paths under `.wavefoundry/framework/scripts/tests/` after each step; `docs_search` for test docstring and docs-lint fixture phrases returned no tests citation. The setup run also completed the pending memory backfill run (no validation-pending notice). Delivery review nit fixed: the fold-test docstring no longer carries em-dashes. | wfsetup4.log, incr1.log, wfsetup5.log; read-only index query; docs_search |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-07 | Selected (a): `setup_index` stops forwarding prefixes and launches the indexer bare on every path. | Makes setup identical to the launchers that already agree (hooks, monitor, mutation refresh, `index_build`, health, rebuild preflight). Graph and `file_meta` scope are unchanged for content `all` and `--graph-only`; for `--docs-only` and `--code-only` with both lists non-empty they widen to the union every bare launcher already uses, an incidental fix of a pre-existing narrowing. | (b) Make `_effective_project_include_prefixes("docs")` ignore the code portion of an override: fixes setup but needs the override split by layer (the CLI flag carries one flat list) and changes a public seam that existing tests drive with docs-scoped overrides. Both (a) and (b): defense in depth, but widens scope. |
| 2026-10-07 | Do not add (b) in this change. | The corrected `--project-include-prefix` help text is the guard against a manual invocation leaking tests; no in-tree caller forwards after (a). A follow-up change can add (b) if wanted. | Land (b) now as defense in depth. |
| 2026-10-07 | ONE workflow-prefix reader with `_coerce_prefix_list` semantics (home decided in the next row); `setup_index` deletes its reader and coercion helper. | After (a) the indexer's reader alone decides eligibility, and today it is the weaker of the two (per-character prefixes from a string value, a crash on a non-string item). One reader removes the divergence instead of testing for it. | Keep both readers with a parity test: still two implementations to drift. Leave the difference as an implementer check before removing the forward: no lasting guard. |
| 2026-10-07 | Coordinator decision: the single reader lives in a new stdlib-only module `workflow_include_prefixes.py`, not in `indexer`. | A module-level `import indexer` would run `activate_tool_venv()` and `register_loaded_source()` at setup import time, before `ensure_deps`; a stdlib module keeps the reader free of those side effects for both consumers. | Lazy by-path load of `indexer` in `main` after `ensure_deps` (setup already does this for model helpers): workable, but ties a pure config read to the heaviest module. Keep two readers with a parity test: leaves two authorities. |
| 2026-10-07 | Persisting `--include-tests` and `--include-generated` stays out of scope. | A setup run with those flags followed by a bare incremental is the same oscillation class but a separate, opt-in, pre-existing divergence. Recorded as a watchpoint. | Persist them in workflow config in this change: widens scope beyond the reported defect. |
| 2026-10-07 | Do not harden `_detect_vector_drift`. | Drift detection is correct for consistent eligibility. Teaching it to ignore rows a different launcher would reap would hide real holes. | Skip drift for paths whose rows were reaped by a prior build: needs persisted reap provenance for a symptom that disappears with the root cause. |
| 2026-10-07 | Drive the regression test through `setup_index.main`, patching only `subprocess.Popen` (in-process `indexer.main` shim) and the prewarm, dependency and GPU hooks; observe reap and drift with `wraps=` spies. | A test through `setup_index.build_index` or a hand-written override kwarg tests a seam below the defect and leaves the restored-forward mutant alive. | Call `indexer.build_index(project_include_prefixes=...)` directly: passes against the fix and the defect alike (kept only to seed leaked state in AC-12). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The shared reader module gains a framework import and drags indexer or venv side effects into setup. | `workflow_include_prefixes.py` imports only the standard library; AC-11 asserts setup resolves prefixes only through it with no module-level `indexer` import. |
| A project relied on setup's coercion of a malformed prefix value. | The indexer's reader adopts setup's coercion exactly (AC-11), so a malformed value resolves the same way it did in setup. |
| `index_compatibility._SOURCE_NAMES` does not cover the new module, so a long-lived host that loaded it does not report itself stale when it changes. | Watchpoint only: registering would break the stdlib-only rule; reader changes are rare and a host restart picks them up. |
| The first setup after upgrade reaps the leaked rows and the operator reads the reap count as data loss. | The reaped paths are all under `.wavefoundry/framework/scripts/tests/`; the CHANGELOG bullet names the effect. |
| Existing tests pin the forward, the removed parameters or the deleted setup reader. | Census of `_run_indexer`, `build_index` and `_workflow_project_include_prefixes` patch sites in `tests/test_setup_index.py`; each is updated in the same change. |

## Open Questions

None. The (b) and include-flag persistence questions are decided in the Decision Log.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
