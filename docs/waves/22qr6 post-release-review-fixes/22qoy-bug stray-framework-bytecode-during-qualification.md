# Stray framework bytecode during test qualification

Change ID: `22qoy-bug stray-framework-bytecode-during-qualification`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-06
Wave: 22qr6 post-release-review-fixes

## Rationale

The framework policy (changes `1zyv1`, `206fi`) keeps Python bytecode in `.wavefoundry/cache/pycache/` and treats any `__pycache__` under `.wavefoundry/framework/` as a defect. During wave 22qky, `.wavefoundry/framework/scripts/__pycache__/setup_commands.cpython-314.pyc` appeared three times beside the framework sources (18:10, 19:07:39 and 19:37 local time). On 2026-11-06 it was written at 18:10:13 local time, about a minute after a previous session's focused repair test runs. It was written again at 19:07:39, about one minute into `run_tests.py --qualify-profile second` (started 19:06:35). Only `setup_commands` was written, so one process that imports that module runs with bytecode writes enabled and no cache prefix.

The full suite stays green while this happens. `run_tests.py` deletes every framework `__pycache__` before each run (`_clean_pycache`), which hides the file between runs. The existing bytecode census and stray-artifact checks do not detect it. The file is ignored by `.wavefoundry/framework/scripts/.gitignore` and cannot be committed. It still breaks the stated policy, and a packaged or downstream checkout could carry it.

## Product Intent

Maintainers and downstream distributions can trust that no framework process, including test qualification, writes bytecode beside the framework sources. A regression is caught by the suite, not by chance inspection.

## Requirements

1. Identify the process that writes `setup_commands.cpython-*.pyc` beside the framework sources and the code path that leaves bytecode writes enabled without a cache prefix.
2. Prevent the write at its source, without changing the bytecode cache policy.
3. Add a regression control that fails when a qualification or test run leaves bytecode under `.wavefoundry/framework/`.

## Scope

**Problem statement:** a process started during test qualification (observed in the renamed `second` profile run, and earlier during focused runs) imports `setup_commands` with bytecode writes on and no prefix, which writes a `.pyc` beside the framework sources.

**In scope:**

- A root-cause trace across every process that can write under the real checkout's `.wavefoundry/framework/`: test and qualification runs (including `run_tests.py` profile setup and fixtures that clear `PYTHONDONTWRITEBYTECODE`, for example `tests/test_session_start_hook.py` line 143), the rendered `.claude/hooks/*.py` hooks that import `setup_commands`, long-lived MCP `server.py` processes rooted in the checkout (including in-process reload), and the `wf` launchers. Two of the three observed writes (18:10 and 19:37) happened outside any test run.
- The source fix and one regression control.

**Out of scope:**

- Changing the bytecode cache location or policy.
- Unrelated `.claude/hooks/__pycache__` and historical wave-evidence `__pycache__` files reported in scanner skips.

## Acceptance Criteria

- [~] AC-1: The writing process and code path are identified, with a reproduction that recreates the `.pyc` beside the framework sources before the fix. The trace must use a method that observes writes to the real tree from any process: macOS `fs_usage` filtered to the real path (it needs sudo, so only with operator approval), or audit hooks installed into each candidate entry point in the real checkout. AC-1 may be marked `[~]` with the trace evidence only after that whole process scope has been traced; AC-2 and AC-3 still apply. *Operator decision 2026-11-06: the required real-tree any-process trace (fs_usage or in-checkout audit hooks) was not run. The root cause was reproduced and fixed instead, using a static census of every entry script, a direct reproduction (HEAD import order in indexer.py, setup_index.py and upgrade_wavefoundry.py recreates the pyc) and a scratchpad audit-hook wrapper. The live writer path is the post-edit hook's indexer.py spawn. The three historical writes (18:10, 19:07:39, 19:37) are not attributed to a specific process. AC-2 and AC-3 still apply.*
- [x] AC-2: After the fix, the reproduction and a full default and `second` profile qualification leave no `__pycache__` or `.pyc` under `.wavefoundry/framework/`.
- [x] AC-3: The outer runner takes a census of the real checkout's `.wavefoundry/framework/` tree at the end of a default full run (after the worker pool finishes, before the exit `_clean_pycache`) and at the end of `_run_profile` (which never cleans the real tree). The census fails when a `.pyc` or `__pycache__` exists there. A file planted after the start clean is the known-bad control. This works whatever the root cause turns out to be.

## Tasks

- [~] Trace the full process scope with the framework `__pycache__` absent, using a method that sees real-tree writes from any process (see AC-1).
- [x] Fix the writing path at its source.
- [x] Add the regression control and run the default and `second` profile qualifications.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| trace      | implementer | —          |       |
| fix-test   | implementer | trace      |       |


## Serialization Points

- `.wavefoundry/framework/scripts/run_tests.py`, `.wavefoundry/framework/scripts/tests/`

## Platform Behavior

Bytecode placement differs by interpreter, not by operating system; the census is path-based and identical on Windows, macOS, Linux and WSL2. A trace with `fs_usage` is macOS-only; the audit-hook trace is portable.

## Affected Architecture Docs

N/A unless the root cause changes the documented bytecode cache flow in `docs/contributing/build-and-verification.md` **Framework Script Hygiene**.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Without the writer identified, a fix is a guess. |
| AC-2 | required  | Policy outcome. |
| AC-3 | required | Prevents silent recurrence regardless of the cause; the current suite misses it. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-06 | Coordinator: the root-cause fix also touches `indexer.py`, `setup_index.py`, `upgrade_wavefoundry.py` and `qualification_worker.py`. These are recorded here rather than in Serialization Points so the post-readiness review receipt is preserved; the code lane is already required for these `.py` paths. | Implementer report; `git diff` |
| 2026-11-06 | AC-3: `run_tests.py` gains `framework_bytecode_paths`/`_framework_bytecode_failure`. `_execute_files` (full, focused and schedule runs) takes the census after the pool and before the exit `_clean_pycache`, failing passing and failing runs alike; `_run_profile` takes it after the receipt check, over `_SCRIPT_DIR.parent`. Static census (`test_bytecode_cache.census_problems`) now also rejects an entry importing any framework module before its flag. Known-bad: a pyc planted from `_run_file` after the start clean fails the run (rc 1, path named) and the exit clean still removes it; one planted from `_profile_run_in` fails the profile run and stays in place; the HEAD-ordering mutant in the scratchpad reports `indexer.py:5` and `qualification_worker.py:9`, while the real tree reports none. | `tests/test_run_tests_cache.py` `FrameworkBytecodeCensusTests` (5 tests) and seam-order test; `tests/test_bytecode_cache.py` `test_a_framework_import_before_the_flag_is_reported`; focused runs 104 ok and 68 ok |
| 2026-11-06 | Fix (Requirement 2): the `setup_commands` import moved below the bytecode guard and `configure()` in `indexer.py`, `setup_index.py` and `upgrade_wavefoundry.py`; `qualification_worker.py` got the same change for `test_worker_guard` (it is launched with `-B`, but a direct run would write). The cache policy is unchanged. After the fix, direct runs of all three and the audit-hook trace record no write beside the sources. Serialization Points widened to the four scripts (implementer edit to that section only). Long-lived MCP servers need no restart, because each refresh spawns a fresh `indexer.py` process from the on-disk source. | `.wavefoundry/work/22qr6/22qoy-audit-trace.tsv` (fixed-tree sections empty) |
| 2026-11-06 | AC-1 trace: the writer is any direct run of `indexer.py`, `setup_index.py` or `upgrade_wavefoundry.py`. Since commit `b33211eb` (2026-11-06 02:21) each has `from setup_commands import ...` as its first statement, before `if __name__ == "__main__" ...: sys.dont_write_bytecode = True` and `bytecode_cache.configure()`. As `__main__` the script itself is not cached, so only `setup_commands` compiles while writes are on and no prefix is set. Then the guard turns writes off, which explains why it was the only file. Live spawners: the post-edit hook `_spawn_reindex` (`[python, indexer.py, --root, ..., --content, all]`), MCP `index_handlers` refresh and build children (`indexer.py`), and direct script runs. This covers the two writes outside test runs. Scope covered: an AST census of every non-test script found no other entry that imports a framework module before its flag. The rendered hooks set the flag before any framework import (`HOOK_BOOTSTRAP`, `wf-session-start.py`). `server.py` and `wf_cli.py` guard and configure before importing, `wf_cli` imports subcommand modules in-process, and test workers get `PYTHONDONTWRITEBYTECODE=1`. The 19:37 pyc header carried the current `setup_commands.py` source stamp (mtime 2026-11-05 23:48:33, 2121 bytes). The file was removed by a concurrent `_clean_pycache` before it could be moved aside. Reproduction: `env -u PYTHONPYCACHEPREFIX -u PYTHONDONTWRITEBYTECODE python3 .wavefoundry/framework/scripts/indexer.py --help` recreated `scripts/__pycache__/setup_commands.cpython-314.pyc` (3624 bytes, the same size as the stray), and `setup_index.py --help` and `upgrade_wavefoundry.py --help` did the same. A scratchpad audit-hook wrapper (event, path, pid only; nothing in the checkout) recorded exactly one `open` and `os.rename` of `setup_commands.cpython-314.pyc` for the HEAD ordering. Method note: the trace used the audit-hook wrapper, direct reproduction and a static census, not `fs_usage`, so the individual historical writes are not attributed to a particular spawn. | `.wavefoundry/work/22qr6/22qoy-audit-trace.tsv`; scratchpad `impl-bytecode/audit_wrap.py`, `impl-bytecode/mutant/` |
| 2026-11-06 | Readiness repair (QA-1, `22qr6-qa-22qoy-trace-scope`): the trace scope and the `[~]` condition now cover hooks, long-lived servers and launchers, with a method that sees real-tree writes; the AC-3 census targets the real tree from the outer runner, including `_run_profile`. | Readiness finding `ev-22qr6-qa-22qoy-trace-scope` |
| 2026-11-06 | Filed from wave 22qky observation. Single-method runs of `test_session_start_hook` with the file absent did not recreate it. | Wave 22qky session; `.wavefoundry/work/22qky/profile-second.log` timing |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The writer is intermittent or depends on the interpreter, so a single reproduction misses it | Trace across a full `second` profile run, not isolated tests |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
