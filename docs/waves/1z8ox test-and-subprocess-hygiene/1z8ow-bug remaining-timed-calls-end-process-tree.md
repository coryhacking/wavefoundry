# Remaining Timed Calls End the Process Tree

Change ID: `1z8ow-bug remaining-timed-calls-end-process-tree`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-29
Wave: 1z8ox test-and-subprocess-hygiene

## Rationale

Waves `1z822` and `1z8tr` routed the timed sensor, setup, upgrade, audit and MCP-helper subprocess calls through `subprocess_util.run_with_tree_kill`. That helper starts a process group and ends the whole group on timeout. The census in `tests/test_tree_kill_routing.py` excludes 36 other timed calls (the `EXCLUDED` table), which still use a plain timeout, so a timeout there ends only the direct child. Most are git commands and system probes (`sysctl`, `ldconfig`, `nvidia-smi`, `lsof`, `ps`, PowerShell). Git can itself start child processes (hooks, credential helpers), so a timeout can leave them running, and on Windows can hang on inherited pipes.

The census also misses timed calls made through callees it does not name. Nine timed git calls go through `index_state_store._run_git` (`_git_head`, `_git_authority` twice, `_collect_git_freshness`, `_collect_git_history`, `_batch_git_blobs`, `_gardener_only_pairs`), `commit_provenance._git`, or `techdocs_audit_lib._baseline_text`, and none of them appears in `EXCLUDED` or the routed set.

A downstream validation also notes that `subprocess_util._kill_process_tree` signals the child's process group without checking whether the child was already reaped. While the child is unreaped (running or a zombie) its pid, which is also the group id, cannot be reused, so the signal is safe. Once the child is reaped the id is free, and signalling it could reach an unrelated group.

## Requirements

1. **Route every timed external command through the helper.** Every timed call that runs an external command (git, the system probes, the process queries, the interpreter and import probes) goes through `run_with_tree_kill`, with its current timeout and output handling. The census counts calls through `index_state_store._run_git` too: `_run_git` is added to the census callees and routed inside `_run_git` itself, which keeps `_sanitized_git_env` in one place. `commit_provenance._git` and `techdocs_audit_lib._baseline_text` already call `_run_git`, so they stay on it and appear in `ROUTED` as `(file, function, "_run_git")`; they are not rerouted around it.
2. **Keep only named exceptions.** The census exclusions shrink to these, each with its reason:
   - `threading.Event.wait`;
   - the helper's own internal waits and `taskkill`;
   - `run_tests._run_file`, whose waits run in worker threads, where a new session would stop Ctrl-C ending the suite;
   - `setup_index`'s background build waits, which own their lifecycle;
   - `venv_bootstrap._probe_interpreter`: `venv_bootstrap` is pinned to stdlib-only imports (`test_venv_bootstrap.StdlibOnlyTests`), and the probe (`python -I -S -B -c`) starts no descendants;
   - `graph_quality_eval._git_value`: the shipped graph-quality reports (`docs/reports/graph-quality-baseline.json`, `graph-quality-post.json`) pin this evaluator's source hash, and re-measuring needs the builder-45 production rebuilt from history, which is disproportionate for a manual measurement CLI's provenance probes (`git rev-parse HEAD` and `git status --porcelain` through one helper), so the file is not edited; route it at the next evaluator change that re-measures.
3. **Resolve the helper at call time, through a named resolver.** Every routed site outside `subprocess_util` resolves the helper when it runs, as `setup_index._run_install_step` does: `getattr(subprocess_util, "run_with_tree_kill", None) or subprocess_util.isolated_run`. During an upgrade the old runner may have an older `subprocess_util` already loaded while it imports new modules, and a missing attribute must not become an `AttributeError`. This is a uniform rule, with no per-module judgement about upgrade reachability.
   - Each routed module does this in one named, module-level resolver (for example `_run_tree_kill(cmd, **kwargs)`; `_run_git` in the store). Sites call the resolver with a literal `timeout=`.
   - The census reads callees by name, so an inline `(getattr(...) or ...)(...)` call is invisible to it and a bound local `run = ...` looks like `subprocess.run`. Each resolver name is therefore added to `CALLEES`, `ROUTED` is keyed on it, and the census fails on any call that passes `timeout=` to a callee it cannot name.
   - A spy test pins each resolver to the helper, as `RoutingSpyTests.test_setup_install_step_calls_the_helper` does, `_run_git` included.
4. **Reap guard.** `_kill_process_tree` never calls `poll()` or `wait()` before the group signal: reaping first frees the id and skips the kill, so a descendant still holding the pipe would leak. It signals the group when `process.returncode is None`, since an unreaped child, whether running or a zombie, keeps the id pinned. It skips the group signal only when `returncode is not None`, meaning the helper already reaped the child. That case is reachable only when an interrupt lands after the internal wait, and descendants can escape there. The Windows branch (`taskkill /PID`) follows the same rule. This is documented beside the existing note about descendants that call `setsid`.
5. **Sanitized git environment stays pinned.** `run_with_tree_kill` is added to `_RUNNER_ATTRS` in `tests/test_doc_drift.py`, so a direct call to the helper cannot bypass the sanitized-environment pin. The pin also flags a `getattr(subprocess_util, ...)` runner used outside `_run_git` and `_git_strip_vars` in the store.
6. **CHANGELOG.** A Fixed line.

## Scope

**Problem statement:** timed git and probe calls can leave descendants running after a timeout.

**In scope:**

- The listed call sites, and `index_state_store._run_git`, which covers its callers including `commit_provenance._git` and `techdocs_audit_lib._baseline_text`.
- `subprocess_util._kill_process_tree`.
- `tests/test_tree_kill_routing.py` and `tests/test_doc_drift.py`.
- Test fakes that stop intercepting a site once it is routed.

**Out of scope:**

- Untimed calls.
- Calls inside rendered hook bodies, which the census already scopes out.
- Descendants that exit the group with `setsid`, and the interrupt-after-wait case in Requirement 4; both are documented limits.

## Acceptance Criteria

- [x] AC-1: the census counts calls through `_run_git` and each named resolver, and fails on a timed call to an unnamed callee (a planted inline `getattr(...)` call proves it). Its exclusion table contains only the entries named in Requirement 2, each with a reason, and the census still passes. A spy test pins each resolver to the helper.
- [x] AC-2: a named routed site, `graph_indexer._gitignored_paths`, run with a fake `git` placed first on `PATH` that starts a sleeping descendant and outlives the timeout, ends the descendant when the timeout expires. The site's literal 30-second timeout becomes a module constant that the test patches to a short value. The test runs without the test shim.
- [x] AC-3: `_kill_process_tree` on a child that has already been reaped (`returncode` set) does not signal its old group id; the test uses a stubbed `killpg`.
- [x] AC-3b: a child that exited but has not been reaped, while a descendant still holds its output pipe, times out and has its group signalled, and the descendant ends. A guard based on `poll()` fails this test.
- [x] AC-4: call sites keep their output handling and error behaviour, and the existing tests for git stats, the probes and the process queries pass. Every existing fake of a routed site still intercepts, which each test asserts by checking the fake was called.
- [x] AC-5: one routed module, run against a `subprocess_util` stub that has no `run_with_tree_kill`, falls back to `isolated_run` rather than raising `AttributeError`.
- [x] AC-6: the change's own suites pass, and the documents it edits validate.

## Tasks

- [x] Add `_run_git` to the census callees and route inside it; key `commit_provenance._git` and `techdocs_audit_lib._baseline_text` in `ROUTED` on `_run_git`.
- [x] Add a named resolver per routed module; route the remaining `EXCLUDED` call sites through it; add the resolvers to `CALLEES`; make the census fail on unnamed timed callees; shrink the exclusion table.
- [x] Add `run_with_tree_kill` to `_RUNNER_ATTRS` in `tests/test_doc_drift.py`.
- [x] Reap guard, following the rule in Requirement 4.
- [x] Keep test fakes working, by installing `tests/tree_kill_support.ModuleShim` in each affected module or retargeting the fakes. The affected tests are derived by census (every test that patches `subprocess.run` or `isolated_run` in a routed module); known ones include `test_dashboard_server`, `test_sqlite_storage_migration`, `test_indexer`, `test_server_tools*`, `test_operator_identity`, `test_render_platform_surfaces`, `test_secret_scan_cache`, `test_runtime_advisory` and `test_memory_backfill`.
- [x] Tests for AC-2, AC-3, AC-3b and AC-5.
- [x] CHANGELOG.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Routing | implementer | readiness | Mechanical per site; `_run_git` first |
| Review | combined reviewer | Routing | Code, QA |

## Serialization Points

- The routed modules, all under `.wavefoundry/framework/scripts/` and `.wavefoundry/framework/scripts/wf_server/`, derived from the census (every module with an `EXCLUDED` or `_run_git` site). They include:
  - `subprocess_util.py`, `index_state_store.py`, `commit_provenance.py`, `techdocs_audit_lib.py`;
  - `dashboard_lib.py`, `graph_indexer.py`, `provider_policy.py`, `indexer.py`, `sqlite_storage_migration.py`;
  - `accel_embedder.py`, `docs_gardener.py`, `graph_quality_eval.py`, `operator_identity.py`, `render_platform_surfaces.py`, `retrieval_eval.py`, `run_secrets_scan.py`, `scan_secrets.py`, `upgrade_protocol.py`, `wf_server/server_impl.py`.
- `.wavefoundry/framework/scripts/tests/`, including `tests/test_tree_kill_routing.py` and `tests/test_doc_drift.py`.
- `CHANGELOG.md`.

## Affected Architecture Docs

`N/A`: no architecture doc lists the excluded calls. This was checked at readiness.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The routing |
| AC-2 | required | Observable outcome |
| AC-3 | important | Id-reuse safety |
| AC-3b | required | Stops the reap guard regressing the group kill |
| AC-4 | required | No regression; fakes still intercept |
| AC-5 | required | Upgrade old-code window |
| AC-6 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-28 | Planned from a downstream validation report; the `EXCLUDED` table in `tests/test_tree_kill_routing.py` lists the 36 calls | `tests/test_tree_kill_routing.py` |
| 2026-09-28 | Readiness review folded in: `_run_git` census gap (9 calls), `venv_bootstrap` exclusion, call-time resolution, reap rule without `poll()` (a scratch probe showed a zombie child with a live grandchild), `_RUNNER_ATTRS` pin, fake interception | readiness review B1 to B4, N3, N4 |
| 2026-09-28 | Confirmation round folded in: named per-module resolvers the census can count, and a census failure on unnamed timed callees (an inline call-time resolution was invisible to it); `_run_git` callers stay on it; the store pin also flags `getattr` runners; AC-2 timeout becomes a constant | confirmation review B6, N-A to N-C |
| 2026-09-28 | Delta readiness review: census re-derived on the current tree (33 EXCLUDED entries, 36 calls; 9 `_run_git` timed calls; no new timed subprocess calls from waves 1z8ot or 1z8ou). N5: serialization and affected-test lists derived by census and completed; N6: the Windows reap branch follows the same rule | delta readiness review |
| 2026-09-28 | Implemented. `_run_git` and `_git_strip_vars` resolve the helper at call time; 15 modules gained a `_run_tree_kill` resolver (accel_embedder, dashboard_lib, docs_gardener, graph_indexer, graph_quality_eval, indexer, operator_identity, provider_policy, render_platform_surfaces, retrieval_eval, run_secrets_scan, scan_secrets, sqlite_storage_migration, upgrade_protocol, wf_server/server_impl); `graph_indexer._GITIGNORED_PATHS_TIMEOUT_S`; reap guard on `returncode is None` in both branches. Census: EXCLUDED 33 keys (36 calls) to 9 keys (11 calls); ROUTED 16 keys (16 calls) to 48 keys (50 calls); CALLEES 7 to 9, plus `<unnamed>` for a timed call to an unnamed callee. Affected fakes derived by a scratch spy runner (a routed resolver reached while `subprocess.run` or `isolated_run` was faked) over the 75 test files that mention them: shim installed and fake-called assertions added in test_accel_embedder, test_dashboard_server, test_doc_drift, test_operator_identity, test_render_platform_surfaces, test_review_operator_integration, test_sqlite_storage_migration, test_indexer (Windows branch); two test_server_tools isolation guards retargeted to the `Popen` spawn; shim added to test_runtime_advisory and test_memory_backfill so their "must not run" guards still cover routed sites; test_subprocess_util's Windows fake gained `returncode = None`. Scratch mutants: a `poll()` guard fails AC-3b, an unconditional kill fails AC-3, a direct `subprocess_util.run_with_tree_kill` lookup fails AC-5, a plain `isolated_run` resolver fails AC-2, an inline getattr call fails the census, and a helper call or getattr lookup outside `_run_git` fails the store pin. Gapfill: grep and a scratch AST census for the timed-call sites, because `code_pattern` with `**/*.py` skips top-level modules and `server_impl.py` is over 1 MB | `tests/test_tree_kill_routing.py`, `tests/test_doc_drift.py`, focused runs |
| 2026-09-28 | Implementation found that routing `graph_quality_eval._git_value` changes the evaluator's source hash that the shipped graph-quality reports pin (`ShippedReportPairTests`); the baseline was measured at graph builder 45 and cannot be re-measured. The site stays on `isolated_run` as a named exclusion rather than re-stamping reports with a hash they were not measured under | `test_graph_quality_eval` 102 OK; `test_tree_kill_routing` 25 OK |
| 2026-09-28 | Delivery repair DEL-F2. `run_tests` gained a `_run_tree_kill` resolver (call-time `getattr(subprocess_util, "run_with_tree_kill", None) or subprocess_util.isolated_run`); `repo_state_snapshot`'s `git ls-files` goes through it with `timeout=60` and `stdin=subprocess.DEVNULL`. A timeout at the before-snapshot, or a `subprocess_util` with no runner, skips the guard with a stated message; at the end-of-run snapshot it fails the run with the cause. `tests/test_tree_kill_routing.py`: `("run_tests.py", "repo_state_snapshot", "_run_tree_kill"): 1` in `ROUTED`, `run_tests` in `RESOLVER_MODULES` (so the per-resolver spy covers it), `check_output`, `check_call` and `call` added to `CALLEES` (no existing timed call used them), and `runner_binding_census`: any Assign, AnnAssign or NamedExpr whose value refers to `subprocess_util.isolated_run`, `subprocess_util.run_with_tree_kill`, `subprocess.run`, `subprocess.Popen` or `getattr(subprocess_util, ...)` as a value (not as the callee) must sit in a named resolver, `index_state_store._run_git` or `_git_strip_vars`; the one other existing binding is `setup_index._run_install_step` (setup's resolver, pinned by its spy), allowlisted with that reason. New tests: `test_census_sees_a_planted_timed_check_output`, `test_runners_are_bound_to_names_only_in_the_resolvers`, `test_binding_census_sees_a_planted_runner_alias`, `test_binding_census_ignores_direct_calls`; in `test_run_tests_repo_guard.GitListingTimeoutTests` the spy, fallback and timeout tests. Scratch mutant: planting `runner = subprocess_util.isolated_run; runner([...], timeout=5)` and `subprocess.check_output([...], timeout=5)` in a copy of `docs_gardener.py` fails `test_every_timed_call_is_routed_or_classified` and `test_runners_are_bound_to_names_only_in_the_resolvers`. The CHANGELOG git bullet now lists every routed git site and names the single exception, the graph-quality evaluator's `git rev-parse` probe | focused `test_tree_kill_routing` 29 OK; scratch mutant |
| 2026-09-29 | Delivery repair DEL-F5 (operator review, nonblocking). `runner_binding_census` missed aliases of `subprocess.check_output`, `check_call` and `call`; all three are now in `_RUNNER_ATTRS`, and `test_binding_census_sees_planted_aliases_of_every_subprocess_api` plants an alias of each of the five APIs. No affected production caller was found. The census docstring states the remaining known limits (import alias, module alias, default argument). | independent-delivery-review.md; events.jsonl DEL-F5 |
| 2026-09-29 | Correction (wave `1za2y`, change `1za2x`). The baseline could be re-measured after all: the evaluator runs against the scripts at commit `f6790333` extracted with `git archive`, as the original baseline was produced, so no builder had to be rebuilt from history. `_git_value` is now routed through a `_run_tree_kill` resolver and both reports were re-measured with every measured field unchanged. The 2026-09-28 implementation row also listed `graph_quality_eval` among the modules that gained a resolver; it had none until `1za2x` (`run_tests` gained its resolver in DEL-F2) | `docs/architecture/testing-architecture.md` (Graph Fidelity Corpus); `tests/test_tree_kill_routing.py`; `tests/test_graph_quality_eval.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-28 | Route git and probe calls too | Git starts its own helpers; a single rule is easier to keep than per-site judgement | Leave git and probes on a plain timeout |
| 2026-09-28 | Route inside `_run_git` rather than at its callers | It is the single sanctioned git wrapper; one edit covers its callers and keeps the sanitized environment | Route each caller |
| 2026-09-28 | Decide the reap guard on `returncode is None` with no `poll()` | The stdlib cannot distinguish our remaining group members from a reused id once the child is reaped; an unreaped child pins the id | `poll()` then skip, which leaks the grandchild |
| 2026-09-28 | Exclude `graph_quality_eval._git_value` | Editing the evaluator invalidates the shipped reports; re-measuring needs builder 45 rebuilt from history, disproportionate for a manual CLI's two provenance git commands | Re-stamp the reports' evaluator identity (records a hash they were not measured under); re-measure both reports |

## Risks

| Risk | Mitigation |
| --- | --- |
| A probe's output handling differs under the helper (sliced output, text mode) | AC-4; route each site with its existing arguments |
| New process groups change Ctrl-C behaviour for short probes | The helper already handles interrupts (wave `1z8tr`); sites run in the foreground |
| Existing fakes of `subprocess.run` or `isolated_run` stop intercepting and real git or `ps` runs while the test still passes | AC-4 asserts each fake was called |
| An upgrade runner with an older `subprocess_util` loads a routed module | Requirement 3 and AC-5 |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
