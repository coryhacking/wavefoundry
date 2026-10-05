# The Isolated CoreML Probe Child Never Activates The Tool Venv

Change ID: `1zu52-bug coreml-probe-child-skips-tool-venv`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-04
Wave: 1zu53 post-upgrade-setup-truthfulness

## Rationale

Field report (1.29.0+puha, macOS, Apple Silicon): every terminal run of `wf setup` printed `isolated CoreML embedder probe failed` and `... reranker probe failed` with `ModuleNotFoundError: No module named 'numpy'`, then used the CPU path, while setup ended `ready` with only the WARNING line to show for it.

Cause, in `accel_embedder._coreml_static_probe_passes` (since 1.16.0): the probe child runs `[windowless_pythonw() or sys.executable, "-c", probe_code, ...]`, and `probe_code` imports `numpy` first. By design (`venv_bootstrap`, ADR 1p7pb tier 3) the framework runs on the system `python3` with the tool venv activated in-process, so `sys.executable` is the system interpreter and every spawned child must activate the venv itself. Framework scripts do so on their first line; this inline `-c` child does not, so on a system Python without numpy (the normal case) the probe always fails and GPU acceleration is silently lost. On Windows the child is the tool venv's `pythonw.exe`, already inside the venv, so the defect does not occur there.

## Requirements

1. The probe child activates the tool venv (`venv_bootstrap.activate_tool_venv()`) before importing anything outside the standard library. The probe source is split into a prelude (activation) and the existing body, and the child command is built by one function, `_coreml_static_probe_command(workload, model_name)`.
2. Activation failure behaves as today: the child exits non-zero, the parent logs the WARNING and uses the CPU path.
3. Setup states the fallback in its closing output: `setup_index._prewarm_gpu_accel` returns the `(workload, model)` pairs whose entry in `accel_embedder._coreml_static_probe_cache` is `False` after prewarm (the only failure signal: `make_embedder` and `make_reranker` swallow the probe failure, and a CPU provider alone also means the normal INT8 path on machines without a GPU). `setup_index.main` normalises that return (anything other than a list, such as a test `MagicMock` or `None`, counts as no failures) and prints one line per failed pair just before the final `Done. Project index update complete.` (the early deps-only and models-only returns never reach the prewarm), naming the CPU fallback and `wf setup --check-gpu`. Setup readiness is unchanged (`ready`): the CPU path is a valid state.
4. No change to the probe body, its parity checks, the cache, or the indexer's fallback handling.
5. CHANGELOG gets a bullet under `## [1.29.0]` `### Fixed` (1.29.0 is unreleased).

## Scope

**Problem statement:** a GPU safety probe fails for a reason unrelated to the GPU, on every terminal setup run, and setup reports success without saying acceleration was lost.

**In scope:**

- `accel_embedder` probe command and prelude; `setup_index._prewarm_gpu_accel` return value and the closing notice; tests; CHANGELOG.

**Out of scope:**

- Changing the in-process activation model (ADR 1p7pb).
- Making setup readiness non-ready on a GPU fallback.
- The other items from the same field report.

## Acceptance Criteria

- [x] AC-1: Running the production probe command, with only its interpreter replaced by the test interpreter under `-S` and `WAVEFOUNDRY_TOOL_VENV` pointing at a fake tool venv whose `numpy` prints a marker and exits 0, reaches that fake `numpy`; without the prelude the same run fails with `ModuleNotFoundError`.
- [x] AC-2: A failing probe still downgrades: `_coreml_static_probe_passes` returns False and logs the WARNING when the child exits non-zero (existing behavior kept).
- [x] AC-3: `setup_index.main` prints the fallback notice when a prewarm probe failed (cache entry `False`) and prints nothing extra when none failed, including a CPU-only machine using INT8 and existing tests that mock `_prewarm_gpu_accel`.
- [x] AC-4: Removing the prelude, or dropping the notice, fails the new tests (shown in a scratch copy).
- [x] AC-5: CHANGELOG describes the fix; docs validate.

## Tasks

- [x] Split the probe source and add `_coreml_static_probe_command`
- [x] Return failed workloads from `_prewarm_gpu_accel` and print the closing notice
- [x] Add tests for the prelude (fake venv) and the notice
- [x] Show the mutants fail in a scratch copy
- [x] CHANGELOG bullet

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                              |
| ---------- | ----------- | ---------- | ---------------------------------- |
| probe      | implementer | —          | accel_embedder, setup_index, tests |


## Serialization Points

- `.wavefoundry/framework/scripts/accel_embedder.py`, `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_accel_embedder.py`, `.wavefoundry/framework/scripts/tests/test_setup_index.py`

## Affected Architecture Docs

N/A: restores the documented tier-3 rule (children self-activate) for one child; no boundary or flow change.

## Platform Behavior

macOS: the fix restores CoreML acceleration for terminal `wf setup` runs. Windows: the child is the tool venv's `pythonw.exe`, so activation is a no-op and behavior is unchanged. Linux and WSL2: the CoreML probe does not run (no CoreML provider); the prelude is never reached. The notice prints only when a probe failed, on any platform.

## AC Priority


| AC   | Priority | Rationale                                  |
| ---- | -------- | ------------------------------------------ |
| AC-1 | required | the root-cause fix                         |
| AC-2 | required | failure must still downgrade safely        |
| AC-3 | required | the fallback must be visible               |
| AC-4 | required | the pins must catch a revert               |
| AC-5 | required | release notes                              |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-04 | Gapfill: implementation edits in both changes used shell reads and scripted replacements because the running MCP server serves pre-change code for the files being edited (`index_runtime_stale`), and investigation before the wave opened already used `code_keyword` and `code_read`; reviewers read through their own scratch copies | retrieval_posture_gap advisory at close dry run |
| 2026-10-04 | Implemented: `_COREML_STATIC_PROBE_PRELUDE` (activate the tool venv) and `_COREML_STATIC_PROBE_BODY`, joined by `_coreml_static_probe_command`; `_prewarm_gpu_accel` returns the `(workload, model)` pairs whose probe-cache entry is `False`; `main` prints one line per pair before the final `Done.`, treating a non-list return as none. Tests: real probe command under `-S` reaches a fake tool-venv numpy, body-only control fails with `No module named 'numpy'`; notice before `Done.`; no notice for `[]`, `None` or the default `MagicMock`; prewarm ignores the CPU-INT8 path. Existing probe tests kept (AC-2). 3.13: the new probe test passes; `main`-driven tests error on 3.13 before and after (the 3.14 tool venv refuses a 3.13 interpreter) | `test_accel_embedder`, `test_setup_index`, `test_indexer`, `test_server_package` OK on 3.14; scratch mutants M3 (no prelude), M4 (no notice), M5 (CPU provider instead of probe cache) killed against a green baseline |
| 2026-10-04 | Readiness review folded in: failure signal is the probe cache, `main` normalises mocked returns, notice placement named; AC-1 experiment reproduced (fake numpy reached with activation, `ModuleNotFoundError` without) | readiness reviewer F1, F2, note |
| 2026-10-04 | Planned from the 1.29.0+puha field report; reproduces on every terminal `wf setup` run | `/opt/homebrew/bin/python3` and `/usr/bin/python3` lack numpy; `venv_bootstrap` tier 3 requires children to self-activate |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-04 | Activate inside the child rather than launching it with `tool_venv_python()` | matches the tier-3 rule every other child follows, and keeps the Windows pythonw choice | launch with the venv interpreter (diverges from the rule and from the Windows path) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The test passes vacuously because the test interpreter already has numpy | `-S` removes site-packages, and the negative control (no prelude) must fail |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
