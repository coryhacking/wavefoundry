# Timed Helpers That Start Children Leave Process Trees

Change ID: `1z8qm-bug timed-helpers-leave-process-trees`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-27
Wave: 1z8tr timed-helper-tree-kills

## Rationale

Wave `1z822` (change `1z824`, RFC finding B5) added `subprocess_util.run_with_tree_kill` and routed the two sites the RFC named: `server_impl._mcp_subprocess_run` and `sensor_runner.run_sensor`. Timed calls elsewhere still use `subprocess_util.isolated_run(timeout=...)` or `subprocess.run(timeout=...)`, which kill only the direct child. Where that child starts its own children, a timeout leaves them running, and on Windows the call can then wait on pipes a surviving grandchild holds, so the timeout does not return.

A census on 2026-09-27 (every call passing `timeout=` to `isolated_run`, `subprocess.run`, `communicate` or `wait` outside `tests/`) found about 35 timed calls. Most run a single short-lived program (`git` status, diff, config and `ls-files`; `sysctl`; `nvidia-smi`; `ldconfig`; `lsof`; `ps`; PowerShell process or hardware queries; interpreter version probes) and are out of scope. The sites below start a program that itself starts children, or run long enough that a hang matters.

## Requirements

1. These timed calls go through `subprocess_util.run_with_tree_kill`, with their current arguments, timeouts, result handling and exception handling unchanged:
   - `setup_index.py`: the venv creation (`python -m venv`, which runs `ensurepip`), the `pip install uv` step, and the dependency install (`uv`/`pip`, which start build and resolver subprocesses);
   - `upgrade_wavefoundry.py`: the extension-hook runner (arbitrary distribution commands), the delegated primary-summary child, and the graph-builder probe;
   - `techdocs_audit_lib.py`: the `--worker-json` audit worker, which runs `git` through `index_state_store`.
2. A timed call that returns in time behaves exactly as before: the same `CompletedProcess` (return code, captured output and its decoding) and the same `check` behavior. Stdin stays as it is today: every routed site already gets `DEVNULL` from `isolated_run`, and `run_with_tree_kill` applies the same default, so no site passes `stdin`.
3. On timeout each site raises or handles `TimeoutExpired` as it does today, and no descendant in the child's process group survives.
4. An interrupt in the parent still stops the child promptly on POSIX and Windows. `run_with_tree_kill` starts the child in its own session or process group, so a terminal's Ctrl-C no longer reaches it directly, and on Windows a single long `communicate`/`wait` does not return to the interpreter to raise `KeyboardInterrupt`. When no `input` is given, the helper therefore waits in short slices (at most 0.5 seconds each) until the child exits or the caller's timeout passes (with no timeout it keeps slicing until exit), so a parent `KeyboardInterrupt` is raised within a slice and its `BaseException` branch ends the group. The slicing does not change the effective timeout, the captured output or the exceptions, and a `TimeoutExpired` carries the caller's timeout, not the slice. When `input` is given the helper keeps a single wait as today, because a retried `communicate` cannot resume writing input (CPython registers stdin for writing only when input is passed, and refuses input after communication starts); the only such routed site is the techdocs worker, which sends a small JSON request and is not interactive.
5. `setup_index` looks the helper up with a fallback, `getattr(subprocess_util, "run_with_tree_kill", None) or subprocess_util.isolated_run`: a 1.27.0 upgrade runner imports the new `setup_index` lazily in `phase_index_update` while its own old `subprocess_util` (without the helper) is already loaded.
6. The out-of-scope timed calls are listed below with the reason each stays, and a static check keeps that list current.

## Scope

**Problem statement:** timed helpers that start children can leave them running after a timeout, and on Windows can hang instead of timing out.

**In scope:**

- the sites in Requirement 1, the slicing in `run_with_tree_kill`, the `setup_index` fallback, and their tests;
- repointing existing tests that patch `subprocess.run` or `subprocess_util.isolated_run` for these sites (`test_setup_index`, `test_upgrade_wavefoundry`, `test_techdocs_audit_lib`), keeping them from reaching real pip, uv, venv or the network.

**Out of scope, with the reason each stays:**

- `run_tests.py` per-file `unittest` workers: they run in worker threads, and a main-thread Ctrl-C cannot reach a thread's wait, so a new session would stop Ctrl-C from ending the suite; today the children share the terminal's group and die with it;
- single-program probes with no descendants: `git` calls in `dashboard_lib`, `docs_gardener`, `graph_indexer`, `graph_quality_eval`, `index_state_store`, `operator_identity`, `render_platform_surfaces`, `retrieval_eval` and `server_impl`; `sysctl` in `graph_indexer`, `run_secrets_scan` and `scan_secrets`; `nvidia-smi` and `ldconfig` in `provider_policy`; `lsof`, `ps` and PowerShell process queries in `sqlite_storage_migration`; PowerShell hardware queries in `dashboard_lib` and `indexer`; the interpreter version probes in `venv_bootstrap` and `upgrade_protocol`;
- the `accel_embedder` CoreML reranker probe: a single Python process that loads a model and exits, with no children, bounded by its own timeout;
- `subprocess_util`'s own `taskkill` call and the post-kill drain inside the helper;
- `Popen`-based background builds and their `.wait` calls (`setup_index`), and `threading.Event.wait` (`dashboard_server`), which are not subprocess timeouts;
- untimed calls.

## Acceptance Criteria

- [x] AC-1: each site in Requirement 1 calls `run_with_tree_kill` (checked by patching it and driving the site), and an AST-based check lists every timed `subprocess.run`, `isolated_run`, `run_with_tree_kill`, `communicate` and `wait` call outside `tests/`, keyed by file, enclosing function and callee with counts (never line numbers), against the in-scope and out-of-scope lists, so a new timed call must be classified.
- [x] AC-2: for the dependency install in `setup_index` and the extension-hook runner, a command that starts a long-lived grandchild and exceeds the timeout leaves no grandchild running (checked by its recorded pid), and the site reports its existing timeout outcome.
- [x] AC-3: a call that finishes in time returns the same result as before at every routed site; the sliced wait returns the same output as an unsliced one for a child that writes more than a pipe buffer, still times out at the caller's timeout, and reports that timeout; a call given `input` larger than a pipe buffer to a child that reads it slowly completes (it takes the unsliced path).
- [x] AC-4: a `KeyboardInterrupt` raised in the parent while `run_with_tree_kill` waits (delivered by a timer during the sliced wait) ends the child group, and a routed `setup_index` install propagates it.
- [x] AC-5: `setup_index` imported against a `subprocess_util` without `run_with_tree_kill` still runs its installs through `isolated_run`.
- [x] AC-6: the change's own suites and every test it adds pass, and the documents this change edits validate.

## Tasks

- [x] Slice the wait in `run_with_tree_kill`.
- [x] Route the Requirement 1 sites; add the `setup_index` fallback.
- [x] Repoint the existing tests that patch `subprocess.run` or `isolated_run` for these sites.
- [x] Classification check, grandchild-survival tests, in-time and slicing equivalence tests, the interrupt test and the fallback test.
- [x] CHANGELOG `[Unreleased]` Fixed bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Routing | implementer | readiness | Mechanical per site; keep each site's exception handling |
| Review | combined reviewer | Routing | Code and QA; include a Windows reading of the helper's group kill |

## Serialization Points

- `.wavefoundry/framework/scripts/setup_index.py`, `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/techdocs_audit_lib.py`, `.wavefoundry/framework/scripts/subprocess_util.py`, `.wavefoundry/framework/scripts/tests/`
- `CHANGELOG.md`

## Affected Architecture Docs

`N/A`: routes existing calls through an existing helper.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The routing, and keeping the census honest |
| AC-2 | required | The defect itself |
| AC-3 | required | No change for calls that finish in time |
| AC-4 | required | Interactive setup must stay interruptible, including on Windows |
| AC-5 | required | An upgrade from 1.27.0 must not break |
| AC-6 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-27 | Delivery review: red-team, code and QA approved; release and docs-contract requested a CHANGELOG fix (D1: extension-module hooks run in-process, not as subprocesses, so only convention hook scripts are covered), now corrected. Also taken: D2, the helper reaps the killed child after an interrupt (bounded wait; the `ResourceWarning` is gone); D3, the census counts `_mcp_subprocess_run` callers (eight, routed since `1z822`) and states its predicate and limits (timeouts forwarded through `**kwargs`, rendered hook bodies); D4, the CHANGELOG says the Windows behavior is designed but not exercised on a Windows host | delivery review; `test_tree_kill_routing` 14 OK with `-W always::ResourceWarning` showing no unreaped child |
| 2026-09-27 | Implemented. `subprocess_util.run_with_tree_kill` waits through `_communicate_sliced` (0.5 s slices when no input; one wait with input; `TimeoutExpired` carries the caller's timeout). Routed: `setup_index` venv, `pip install uv` and dependency install through `_run_install_step` (call-time lookup with the `isolated_run` fallback); `upgrade_wavefoundry._run_hook`, `_delegated_summary_payload` and `_read_installed_graph_builder_version`; `techdocs_audit_lib.run_techdocs_audit`. Existing fakes in `test_setup_index`, `test_upgrade_wavefoundry` and `test_techdocs_audit_lib` keep intercepting through a module-level shim (`tests/tree_kill_support.py`) that routes the helper back through `isolated_run`, so no test reaches a real install; the real routing and tree kill are pinned without it in `tests/test_tree_kill_routing.py` | `test_tree_kill_routing` (14 tests: census of 40 timed calls keyed by file, function and callee; spies; real grandchild kills for a setup step and a convention hook; parent interrupt; sliced output, timeout and large input); scratch mutations (hook back to `isolated_run`, no slicing, no fallback, slice timeout reported) each fail a named test; `test_setup_index` 165, `test_upgrade_wavefoundry` 542, `test_techdocs_audit_lib` 86, `test_subprocess_util` 28 OK |
| 2026-09-27 | Readiness recheck: F1 and F2 resolved; two new blocking findings adopted. R1: a retried `communicate` cannot resume writing input, so calls given `input` keep a single wait and only input-free calls are sliced; AC-3 adds a large input to a slow reader. R2: the routed sites already use `DEVNULL` stdin, so the `stdin=None` change is dropped. Notes adopted: slice with no timeout, report the caller's timeout | readiness recheck (scratch probe `slice_probe.py`: 10 MB input with 0.2 s slices timed out) |
| 2026-09-27 | Readiness review requested changes; adopted. F1: a 1.27.0 runner imports the new `setup_index` with its old `subprocess_util`, so `setup_index` falls back to `isolated_run` (Requirement 5, AC-5). F2: `run_tests.py` moved out of scope (worker-thread waits cannot see Ctrl-C). F3: the helper waits in slices so an interrupt is seen on Windows too (Requirement 4). F4 test repointing, F5 (stdin; corrected at recheck: the sites already use `DEVNULL`), F6 hard kill, F7 out-of-scope labels, F8 the check's key | readiness review |
| 2026-09-27 | Planned at the operator's request as the follow-up to `1z824` (B5); census of timed calls taken with the scratch AST scan used for `1z824` | census of `timeout=` calls outside `tests/` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-27 | Keep `run_tests.py` out of scope | Its per-file waits run in worker threads; moving the children to new sessions would stop a terminal Ctrl-C from ending the suite, and tracking every live group across threads is more than the risk warrants | Route it and kill tracked groups on a main-thread interrupt |
| 2026-09-27 | Route only helpers that start children or run long; leave single-program probes | A `git status` or `sysctl` has no descendants to leak, and routing every call would change process-group behavior for no gain | Route every timed call |

## Risks

| Risk | Mitigation |
| --- | --- |
| The new session changes how Ctrl-C reaches the child | The sliced wait raises the parent's `KeyboardInterrupt` promptly and the helper ends the group (AC-4); `run_tests.py` stays out of scope because its waits are in worker threads |
| Windows: `CREATE_NEW_PROCESS_GROUP` disables Ctrl-C in the child and a long `WaitForSingleObject` does not return to the interpreter | The sliced wait returns to the interpreter at least every 0.5 seconds; not verified on a Windows host in this wave, so the review includes a Windows reading of the helper |
| Old-code window: a 1.27.0 runner imports the new `setup_index` with its own old `subprocess_util` loaded | `setup_index` falls back to `isolated_run` (AC-5). The hook runner, summary child and graph-builder probe run in whichever runner is installed, so an upgrade to this release gets the protection only from the following upgrade on |
| A group kill ends pip or uv without a SIGINT first, so a partial install is not rolled back | Accepted: the timeout path already treats the install as failed and setup can be rerun |
| A child that prompts through `/dev/tty` (a pip credential prompt for a private index, an extension hook) loses the controlling terminal in its new session | Stdin is already `DEVNULL` at every routed site, so only a `/dev/tty` prompt is affected; accepted and documented |
| Output or input handling changes under the sliced wait | Calls with `input` are not sliced; AC-3 checks more than a pipe buffer of output, and a large input to a slow reader |
| A call given `input` still waits in one piece, so on Windows an interrupt during it is seen only when it ends | Accepted: the only such site is the non-interactive techdocs worker, bounded by its own timeout |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
