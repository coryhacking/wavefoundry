# Disable onnxruntime Telemetry

Change ID: `1z8or-bug disable-onnxruntime-telemetry`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-28
Wave: 1z8ot edit-gate-and-lock-hardening

## Rationale

onnxruntime 1.29.0, which fastembed resolves to on a fresh install because onnxruntime is not pinned, creates telemetry state on a bare `import onnxruntime`:

- a persistent device id and an event store under the user's home (`~/Library/Application Support/Microsoft/DeveloperTools/.onnxruntime/` on macOS);
- `:memory:.ses` in the working directory when that home location is not writable.

onnxruntime 1.27.0 creates neither. The fix differs by platform:

- On macOS and Linux, setting `ORT_DISABLE_TELEMETRY=1` before the import prevents it.
- On Windows the variable has no effect; `onnxruntime.disable_telemetry_events()` must be called after the import.

Nothing in the framework sets either today. A downstream validation report found this; Wavefoundry is local-only by principle.

## Requirements

1. **Environment default.** `venv_bootstrap` sets `ORT_DISABLE_TELEMETRY=1` at import when the variable is unset or empty. An empty string re-enables telemetry on onnxruntime 1.29, so empty counts as unset. Any other value, including `"0"`, is treated as the operator's explicit choice and kept. Every entry point imports `venv_bootstrap` before any onnxruntime import (verified at readiness: `server.py` through `setup_readiness`, `setup_index`, `indexer`, `run_tests`, `gpu_doctor`, `setup_wavefoundry`, `server_impl` and the rendered hooks), and child processes inherit the environment.
2. **Disable telemetry at every import site.** A shared helper in `venv_bootstrap` (stdlib-only and already imported everywhere) calls `onnxruntime.disable_telemetry_events()` right after each onnxruntime or fastembed import, on every platform. It is harmless where the variable already works, and on Windows it is the only control. A missing function is tolerated. The import sites are:
   - `accel_embedder` (six sites);
   - `provider_policy` (two);
   - `setup_index` (two);
   - `indexer`;
   - `wf_server/server_impl` (two);
   - `benchmarks/embed_bench.py`, which also gains the `venv_bootstrap` import, after putting the scripts directory on `sys.path`.

   `gpu_doctor` and `retrieval_eval` reach onnxruntime through `provider_policy` and `indexer` and are covered there.
3. **Scan test.** A standing test fails on any new non-test onnxruntime or fastembed import site that does not call the helper.
4. **CHANGELOG.** Note the change, and that setting `ORT_DISABLE_TELEMETRY=0` opts back in.

## Scope

**Problem statement:** a Wavefoundry process can create onnxruntime telemetry state on the user's machine.

**In scope:**

- `venv_bootstrap.py`, the helper, the import sites (including `embed_bench`), the scan test.

**Out of scope:**

- Pinning onnxruntime, which is a separate supply decision.

## Acceptance Criteria

- [x] AC-1: after importing `venv_bootstrap`, `ORT_DISABLE_TELEMETRY` is `"1"` when it was unset or empty, and unchanged when it was set to anything else. A child process started afterwards inherits it.
- [x] AC-2: evidence recorded at review on onnxruntime 1.29 or later, in a scratch venv (installing needs the network, so this cannot run in the suite): importing `venv_bootstrap` and then onnxruntime with a scratch home creates nothing under that home, and nothing in an unwritable-home working directory. A pass on an older onnxruntime does not count.
- [x] AC-3: each import site calls the helper (a stubbed onnxruntime records the call), and a missing `disable_telemetry_events` does not raise.
- [x] AC-4: the scan test fails on a planted import site without the helper.
- [x] AC-5: the change's own suites pass, and the documents it edits validate.

## Tasks

- [x] The `venv_bootstrap` default (unset or empty); the helper; the import-site calls, including `embed_bench`.
- [x] Scan test; stubbed-onnxruntime tests; CHANGELOG.
- [x] Review evidence on onnxruntime 1.29 in a scratch venv.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Telemetry | implementer | readiness | Small |
| Review | combined reviewer | Telemetry | Code, QA; 1.29 evidence |

## Serialization Points

- `.wavefoundry/framework/scripts/venv_bootstrap.py`, `.wavefoundry/framework/scripts/setup_index.py`, `.wavefoundry/framework/scripts/accel_embedder.py`, `.wavefoundry/framework/scripts/provider_policy.py`, `.wavefoundry/framework/scripts/indexer.py`, `.wavefoundry/framework/scripts/benchmarks/embed_bench.py`, `.wavefoundry/framework/scripts/wf_server/`, `.wavefoundry/framework/scripts/tests/`
- `CHANGELOG.md`

## Affected Architecture Docs

`N/A`: a process-environment default and import-site calls.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Covers macOS and Linux |
| AC-2 | required | Observable outcome on the affected version |
| AC-3 | required | Covers Windows |
| AC-4 | required | New import sites cannot forget it |
| AC-5 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-28 | Delivery repair DEL-F5. `venv_bootstrap.disable_onnxruntime_telemetry` returns without calling the API when `ORT_DISABLE_TELEMETRY` stripped equals `0`, the documented opt back in; unset, empty (defaulted to `1` at bootstrap import) and every other value keep the call. The module stays stdlib-only; the docstring says the call disables API-controlled telemetry events, a control upstream documents as distinct from the variable. CHANGELOG bullet now states that setting `0` opts back in to both and no longer implies the API call covers initialization telemetry. Existing helper and import-site tests pin the variable to `1`. Scratch mutation: removing the check fails the `0` and ` 0 ` unit subtests and the `0` subprocess subtest | `OptInTests` (`test_unset_empty_and_one_call_the_api`, `test_zero_opts_back_in_and_skips_the_api`, `test_a_real_caller_honours_the_opt_in` through `provider_policy.available_onnx_providers` with a recording stub package first on `sys.path`: 1 call each for unset, empty, `1`; 0 for `0`); `test_onnxruntime_telemetry.py` 24 OK, `test_venv_bootstrap.py` 38 OK |
| 2026-09-28 | AC-2 evidence on onnxruntime 1.30.0 (scratch venv, Python 3.13.5, macOS). Scratch HOME, variable unset, no bootstrap (control): 4 files under `Library/Application Support/Microsoft/DeveloperTools/.onnxruntime/` (`deviceid`, `onnxruntime.db`, `-wal`, `-shm`). Importing `venv_bootstrap` first, variable unset or empty: 0 files under the home, 0 in the cwd. Unwritable home (mode 555), control: `:memory:.ses` in the cwd; with the bootstrap (unset or empty): 0 files in the cwd. Explicit `0` with the bootstrap: 4 files (the opt back in works) | scratch-venv runs under the session scratchpad |
| 2026-09-28 | Implemented Requirements 1 to 3. `venv_bootstrap` sets `ORT_DISABLE_TELEMETRY=1` when unset or empty and adds `disable_onnxruntime_telemetry(ort=None)` (uses the given module or `sys.modules["onnxruntime"]`, imports nothing, tolerates a missing module, a missing function and any exception). Helper calls at all 14 import sites; `accel_embedder` and `provider_policy` now import `venv_bootstrap`; `embed_bench` puts the scripts directory on `sys.path` and imports it. Census predicate: AST `Import`/absolute `ImportFrom` whose top-level module is `onnxruntime` or `fastembed`, plus `import_module`/`__import__` with such a string constant, in non-test `.py` under `.wavefoundry/framework/scripts` (excluding `venv_bootstrap.py`); result matches the plan: accel_embedder 6, provider_policy 2, setup_index 2, indexer 1, server_impl 2, embed_bench 1. New `tests/test_onnxruntime_telemetry.py` (21 tests): AC-1 subprocess env tests, AC-3 per-site stubbed-onnxruntime tests (recording stub and stub without the function give the same outcome), AC-4 AST scan pinned to the census plus a planted scratch module. Mutation check: removing one site call in a scratch copy fails both the per-site test and the scan. Gapfill: `grep -l` over `tests/` to find suites touching the changed functions | `test_onnxruntime_telemetry`, `test_venv_bootstrap`, `test_accel_embedder`, `test_setup_index`, `test_indexer`, `test_model_bundle`, `test_setup_readiness_integration` focused runs OK |
| 2026-09-28 | Readiness confirmation: all findings resolved; R3 adopted (the helper lives in `venv_bootstrap`; `embed_bench` adds the scripts directory to `sys.path`) | readiness confirmation |
| 2026-09-28 | Readiness review. On a scratch onnxruntime 1.29.0 venv: 9 files under the home without the variable; nothing with `1`; telemetry with `0` or an empty string; no effect when set after import. `disable_telemetry_events` exists in 1.27 and 1.29. The tool venv has 1.27.0, so AC-2 needs recorded 1.29 evidence (N9). Adopted N10 (empty counts as unset) and N11 (`embed_bench` added, scan test, helper on every platform) | readiness review |
| 2026-09-28 | Planned from a downstream validation report. Confirmed nothing in the scripts sets `ORT_DISABLE_TELEMETRY` or calls `disable_telemetry_events` | grep of `.wavefoundry/framework/scripts` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-28 | Set the variable in `venv_bootstrap`; call the helper on every platform | Every entry point imports it first; the helper call is harmless where unneeded and removes a Windows-only branch | Windows-only helper call |
| 2026-09-28 | Treat an empty value as unset and keep any other value | An empty string re-enables telemetry on 1.29; `"0"` is an explicit opt-in | `setdefault` |

## Risks

| Risk | Mitigation |
| --- | --- |
| An entry point imports onnxruntime before `venv_bootstrap` | Readiness census of entry points; the helper call at each import site covers it anyway |
| Windows emits an event at import, before the helper runs | Unverified; the variable is set first and the helper runs immediately after; recorded as a residual |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
