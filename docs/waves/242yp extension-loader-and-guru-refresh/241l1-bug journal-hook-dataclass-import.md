# Journal hook modules that use dataclasses fail to import during upgrade

Change ID: `241l1-bug journal-hook-dataclass-import`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-22
Wave: 242yp extension-loader-and-guru-refresh

## Rationale

The Waveforge distribution reported this against v1.47.0, and it is still present at v1.49.0. A distribution can declare a journal pre-migration hook as `module:function` in `mcp_tool_extensions.py`. During upgrade, `upgrade_extensions._load_journal_hook` loads that module through `_exec_module_from_file`, which executes the file without registering it in `sys.modules`. When the hook module combines `from __future__ import annotations` with `@dataclass`, the class decorator calls `dataclasses._is_type`, which reads `sys.modules.get(cls.__module__).__dict__`. The lookup returns `None`, so the import raises `AttributeError: 'NoneType' object has no attribute '__dict__'`. The upgrade then refuses with "journal pre-migration hook ...: module ... could not be imported (AttributeError)".

Observed failure (reproduced 2026-11-22 by the coordinator and again by the planner):

1. Input: a module file containing `from __future__ import annotations`, `from dataclasses import dataclass` and one `@dataclass` class with an annotated field, loaded by calling `upgrade_extensions._exec_module_from_file("_wf_upgrade_journal_hook_hookmod", path)`.
2. Actual result: `AttributeError: 'NoneType' object has no attribute '__dict__'` on CPython 3.14.8 (`python3`) and on CPython 3.11 (`/opt/homebrew/bin/python3.11`).
3. Expected result: the module loads and the dataclass is defined, as it would be under an ordinary import.

Operator decision (2026-11-22): fix it upstream, under ordinary review.

## Product Intent

A distribution maintainer whose journal hook module uses ordinary Python (dataclasses with postponed annotations) gets an upgrade that loads and runs the hook, instead of a refusal that names an import failure in code that imports fine anywhere else. The boundary is unchanged: the loaded module still leaves no entry in `sys.modules` after the load, so a stale or later copy is never answered from the cache. AC-1 and AC-2 together establish the intent; AC-3 establishes the boundary.

## Why the module is never left registered

Wave `1zyb3` (change `1zxnv`, Requirement 3) loads `mcp_tool_extensions.py` and the hook's helper module by file path from the extracted tree "under a private module name, so a stale copy in `sys.modules` never answers." The upgrade runs in the older runner's process, which may already hold the old `mcp_tool_extensions` or helper in `sys.modules`. The private names (`_JOURNAL_DECLARATION_MODULE`, `_JOURNAL_HOOK_MODULE_PREFIX`) keep the incoming code from colliding with those entries, and leaving nothing registered keeps the older runner's import state unchanged and makes a retry (preview then apply, or a second attempt) execute the file afresh. The comment above those constants in `upgrade_extensions.py` states the same intent.

None of this needs the module to be absent while it executes. Registering it under its private name only for the duration of `exec_module`, then removing the entry and restoring any prior entry with that name, keeps both properties. The private names cannot match any module the runner imported under a public name.

## Requirements

1. `upgrade_extensions._exec_module_from_file(name, path)` must register the new module object in `sys.modules[name]` immediately before `exec_module` runs.
2. After `exec_module` returns or raises, the helper must restore `sys.modules[name]` to its state before the call: the prior object re-inserted when one existed, and no entry when none existed. The absent case uses `sys.modules.pop(name, None)`, never `del`, so a module that removed its own entry during execution does not break the restore. The restoration runs on success and on any exception, including `BaseException`.
3. The helper must keep its other behavior: it raises `ImportError(name)` when no spec or loader exists, executes the file afresh on every call, and returns the module object.
4. The helper's docstring must state the new contract: registered only while the file executes, never left registered. It must also state the limit: the module is unregistered when the hook function is called, so a hook that resolves its own annotations (`typing.get_type_hints`) or pickles its own classes at call time still fails.
5. The change is confined to the shared helper. Both of its callers, the declaration load (`_load_journal_declaration`) and the hook load (`_load_journal_hook`), gain the fix because both execute distribution-authored files.

## Scope

**Problem statement:** a distribution-authored journal hook module (or `mcp_tool_extensions.py` itself) that defines a dataclass under postponed annotations cannot be loaded by the upgrade, because the loader never registers it in `sys.modules`.

**In scope:**

- `_exec_module_from_file` in `.wavefoundry/framework/scripts/upgrade_extensions.py`.
- A regression test in `.wavefoundry/framework/scripts/tests/test_upgrade_protocol.py`, beside the existing journal hook coverage (`JournalIncomingRunnerTests`).
- A CHANGELOG `[Unreleased]` entry.

**Out of scope:**

- Other file-based loaders. The census below found no other non-test loader that executes distribution-authored code.
- `_incoming_history_paths` and `_incoming_framework_module`. They load Wavefoundry-owned modules, never distribution code, and `history_paths` is pinned free of dataclasses by `tests/test_history_paths.py`. Their docstrings keep their current statements.
- The server's extension loader `_load_extension_module` in `wf_server/server_impl.py`. It already registers the module before `exec` (with a `__wf_extension__` marker) and is unaffected.
- A permanent Python 3.11 lane in `run_tests.py`.
- Call-time introspection by the hook. The fix covers import time only: once the helper returns, the module is unregistered, so `typing.get_type_hints` on the hook's dataclass or pickling one of its instances inside the hook function still fails. Keeping the module registered across the call is not in scope (Decision Log, 2026-11-22).

### Census of file-based loaders

Run on 2026-11-22: `code_keyword("spec_from_file_location", glob=".wavefoundry/framework/**/*.py", limit=0)` returned 207 hits; the non-test hits are in 18 files. Each was read at its call site.

| Site | What it loads | Distribution code? |
| --- | --- | --- |
| `upgrade_extensions.py` `_exec_module_from_file` | `mcp_tool_extensions.py` and the declared hook helper | Yes (this change) |
| `upgrade_extensions.py` `_incoming_history_paths`, `_incoming_framework_module` | Wavefoundry `history_paths` and stdlib-only framework modules | No |
| `upgrade_extensions.py` index-guard and storage migration loads, `_installed_upgrade_module` | Wavefoundry `sqlite_storage_migration.py`, `upgrade_wavefoundry.py` | No |
| `upgrade_wavefoundry.py` (2 sites) | `index_state_store.py`, `gen_codebase_map.py` | No |
| `wf_server/server_impl.py` (3 sites) | routing modules, `_load_script` siblings, chunker | No; the routing load and `_load_script` already register |
| `lifecycle_gate_support.py` | `run_tests.py` for the close receipt | No |
| `gen_codebase_map.py`, `eval_chunker.py` | sibling framework scripts; both already register | No |
| `dashboard_lib.py`, `dashboard_server.py` (3 sites), `graph_indexer.py` (1 call, 1 docstring), `graph_query.py` (2), `indexer.py` (4), `render_platform_surfaces.py` (2), `repair_ppol_memory_staging.py`, `setup_index.py` (4), `setup_wavefoundry.py`, `sqlite_storage_migration.py` (2), `benchmarks/embed_bench.py`, `test_worker_bootstrap/sitecustomize.py` | framework scripts beside the caller | No |

Distribution-declared MCP tool extensions load through the server's `_load_extension_module`, which uses `exec` on a `types.ModuleType`, not `spec_from_file_location`; it registers the module first and is out of scope as stated above.

## Acceptance Criteria

- [x] AC-1: A test in `tests/test_upgrade_protocol.py` writes a hook helper module that uses `from __future__ import annotations` and a `@dataclass` with an annotated field, declares it as the journal pre-migration hook, and asserts that the hook loads and its function is called. Under the current helper the load refuses with `JournalDeclarationError` naming "could not be imported (AttributeError)", so the test fails.
- [x] AC-2: The same dataclass module, loaded by calling the real `upgrade_extensions._exec_module_from_file` from a stdlib-only probe run with `/opt/homebrew/bin/python3.11 -B`, defines the dataclass without error. Under the current helper the probe prints `AttributeError 'NoneType' object has no attribute '__dict__'`. The implementer records the probe command and its before/after output in the Progress Log.
- [x] AC-3: A test asserts that after `_exec_module_from_file(name, path)` returns, `name` is absent from `sys.modules` when it was absent before. A second case seeds `sys.modules[name]` with a sentinel object and asserts the sentinel is restored, by identity, both after a successful load and after a load whose module raises, once with an ordinary `Exception` and once with `SystemExit` (a `BaseException` that is not an `Exception`), so a restore written as `except Exception` without `finally` fails the test. Under the current helper the restoration case passes vacuously, so the test also asserts, from inside the executing module, that `sys.modules[name]` is the module being executed; that assertion fails under the current helper.
- [x] AC-4: The change's own suites and every test it adds pass on the running interpreter (CPython 3.14); the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Change `_exec_module_from_file` to save any prior `sys.modules[name]`, register the module, run `exec_module` in `try`, and restore the saved state in `finally`: re-insert the prior entry when one existed, otherwise `sys.modules.pop(name, None)`.
- [x] Update the helper's docstring and the comment above `_JOURNAL_DECLARATION_MODULE` to say the module is registered only while it executes, and that call-time `typing.get_type_hints` or pickling of the hook's own classes still fails.
- [x] Add the AC-1 integration test and the AC-3 helper tests to `tests/test_upgrade_protocol.py`, and confirm each fails before the fix.
- [x] Run the AC-2 probe on Python 3.11 before and after the fix, and record both outputs in the Progress Log.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py --file test_upgrade_protocol.py`, then the full suite last.
- [x] Add a CHANGELOG `[Unreleased]` Fixed entry: a journal pre-migration hook module, or `mcp_tool_extensions.py`, that defines a dataclass under `from __future__ import annotations` now loads during upgrade. The bullet also states the limit: the module is unregistered when the hook is called, so resolving its own annotations or pickling its own classes at call time is still unsupported.

## Agent Execution Graph

1. Write the failing tests and the 3.11 probe.
2. Change the helper.
3. Rerun the tests and the probe, then add the CHANGELOG entry.

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| fix-and-tests | implementer | none | One file of code and one test file |

## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_protocol.py`

## Affected Architecture Docs

N/A. The `upgrade_extensions.py` row in `docs/architecture/layering-rules.md` describes the journal import context and its restoration of prior module identities; it makes no claim that the private modules are absent during execution, and this change keeps the module absent afterwards. No boundary or flow changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Proves the reported failure is fixed through the real hook path |
| AC-2 | required | Covers the 3.11 floor, which the field report runs on |
| AC-3 | required | Proves the never-left-registered property still holds |
| AC-4 | required | Change-local verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-22 | Planned. Failure reproduced on 3.14.8 and 3.11 through the real helper. | Planner probe in a scratch directory |
| 2026-11-22 | Folded in readiness advisories (wave `242yp`): documented the import-time-only limit in Requirement 4, Scope, Risks and the CHANGELOG task; restore uses `pop(name, None)` and re-inserts a prior entry; AC-3 adds a `SystemExit` case. | `.wavefoundry/work/242yp/review/red-team-primer.md` item 1.4, `code-reviewer-readiness.md`, `qa-reviewer-readiness.md` |
| 2026-11-22 | Implemented. `_exec_module_from_file` registers the module only while it executes and restores the prior state in `finally` (re-insert, else `pop(name, None)`). Added `JournalIncomingRunnerTests.test_dataclass_hook_module_with_postponed_annotations_loads_and_is_called` and `ExecModuleFromFileTests` (6 tests); before the fix 5 of the 7 new tests failed, including the AC-1 refusal "could not be imported (AttributeError)". After: `python3 -B -m unittest discover -s tests -p test_upgrade_protocol.py` ran 51 tests, OK; the `Journal` tests in `test_upgrade_wavefoundry.py` ran 103, OK (1 skipped). AC-2 probe `python3.11 -B -I probe/probe.py <scripts> probe/hookmod.py`: before `AttributeError 'NoneType' object has no attribute '__dict__'` on 3.11.17 and 3.14.8; after `OK Row(x=1) registered_after: False` on both. The coordinator's `python3 -B -m unittest tests.test_upgrade_protocol` form fails to import `framework_files` from `tests/`, so the discover form was used. The full suite and the CHANGELOG bullet are left to the coordinator. | `.wavefoundry/work/242yp/impl/probe-before.txt`, `.wavefoundry/work/242yp/impl/probe-after.txt` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-22 | Fix upstream under ordinary review | Operator decision: "DO. Fix it upstream. Ordinary review." | Small-change lane (not selected by the operator) |
| 2026-11-22 | Register the module under its private name only while `exec_module` runs, then restore the prior state, in the shared helper | Planner default. Replaying the reported module through this mechanism: `dataclasses._is_type` finds the module and the import succeeds, and both distribution-authored loads gain the fix. The fix controls the outcome directly. What it could break: code that relies on the private name being absent during execution; none exists, since the names are private constants. Success after release: the distribution's hook loads on upgrade to the fixed version. | (a) Leave the module registered after the load: breaks the never-left-registered property and leaves the older runner's cache changed. (b) Document that hook modules must avoid dataclasses with postponed annotations, as `history_paths` does: pushes a CPython constraint onto distribution authors for code they do not control and leaves the defect. (c) Fix only `_load_journal_hook`: the declaration module has the same exposure through the same helper. |
| 2026-11-22 | Cover 3.11 with a stdlib-only probe of the real helper, not a full 3.11 suite run | Coordinator default (2026-11-22, reversible): the probe is enough, because the defect reproduces identically on 3.14, so the `test_upgrade_protocol.py` regression tests cover the mechanism and the 3.11 probe confirms the reported version. `docs/contributing/` has no 3.11 run recipe; the suite under 3.11 needs a separate pinned venv (`WAVEFOUNDRY_TOOL_VENV`), and the test module refuses to import against the 3.14 tool venv. The probe imports `upgrade_extensions` directly on 3.11 and reproduces the failure. | Full suite on a 3.11 venv (heavier, needs pinned dependencies) |
| 2026-11-22 | Keep registration per call; state the import-time-only limit rather than widening registration to the hook call | Coordinator default (2026-11-22, reversible). The red-team probed a stand-in fix on 3.14 and 3.11: import succeeds, but `typing.get_type_hints` raised `NameError` and `pickle.dumps` raised `PicklingError` inside the hook function. The reported defect is the import failure; the limit is stated in the docstring, Scope, Risks and CHANGELOG. | Keep each private module registered while `_journal_incoming_imports` is active and remove it in that context's `finally`: covers call time, but the preview path (`load_hook=False`) runs outside that context and still needs the per-call restore |

## Risks

| Risk | Mitigation |
| --- | --- |
| The fix lives in the incoming `upgrade_extensions`, which the older runner loads from the pack for `pre_docs_gate` (`inferred` from the `JournalIncomingRunnerTests` older-runner fixture, not executed for this plan). If that holds, the fix applies to any upgrade to the fixed version, whatever the from-version. | AC-1 exercises the older-runner dispatch path that the existing test class uses |
| A hook module that recursively loads itself by its private name would now find itself registered | No supported pattern does this; the name is a private constant |
| A hook that calls `typing.get_type_hints` on its own dataclass, or pickles one of its instances, still fails at call time because the module is unregistered by then | Stated in the docstring and the CHANGELOG bullet; widening registration to the call is the recorded alternative if a distribution needs it |

Windows, macOS, Linux and WSL2: the change touches only in-process `sys.modules` state, with no path, process or file-system behavior, so it behaves the same on all four.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
