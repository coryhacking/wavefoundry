# Stray framework bytecode during test qualification

Change ID: `22qoy-bug stray-framework-bytecode-during-qualification`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-11-06
Wave: TBD

## Rationale

The framework policy (changes `1zyv1`, `206fi`) keeps Python bytecode in `.wavefoundry/cache/pycache/` and treats any `__pycache__` under `.wavefoundry/framework/` as a defect. During wave 22qky, `.wavefoundry/framework/scripts/__pycache__/setup_commands.cpython-314.pyc` appeared twice beside the framework sources. On 2026-11-06 it was written at 18:10:13 local time, about a minute after a previous session's focused repair test runs. It was written again at 19:07:39, about one minute into `run_tests.py --qualify-profile second` (started 19:06:35). Only `setup_commands` was written, so one process that imports that module runs with bytecode writes enabled and no cache prefix.

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

- Root-cause trace across the profile-qualification setup in `run_tests.py`, test fixtures that clear `PYTHONDONTWRITEBYTECODE` (for example `tests/test_session_start_hook.py` line 143) and rendered hooks or launchers that import `setup_commands`.
- The source fix and one regression control.

**Out of scope:**

- Changing the bytecode cache location or policy.
- Unrelated `.claude/hooks/__pycache__` and historical wave-evidence `__pycache__` files reported in scanner skips.

## Acceptance Criteria

- [ ] AC-1: The writing process and code path are identified, with a reproduction that recreates the `.pyc` beside the framework sources before the fix.
- [ ] AC-2: After the fix, the reproduction and a full default and `second` profile qualification leave no `__pycache__` or `.pyc` under `.wavefoundry/framework/`.
- [ ] AC-3: A maintained test fails on a known-bad variant that reintroduces the unguarded import.

## Tasks

- [ ] Reproduce with the framework `__pycache__` absent and per-process tracing, for example a temporary `sitecustomize` audit hook in a scratch copy, or the macOS `fs_usage` tool.
- [ ] Fix the writing path at its source.
- [ ] Add the regression control and run the default and `second` profile qualifications.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| trace      | implementer | —          |       |
| fix-test   | implementer | trace      |       |


## Serialization Points

- `.wavefoundry/framework/scripts/run_tests.py`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A unless the root cause changes the documented bytecode cache flow in `docs/contributing/build-and-verification.md` **Framework Script Hygiene**.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Without the writer identified, a fix is a guess. |
| AC-2 | required  | Policy outcome. |
| AC-3 | important | Prevents silent recurrence; the current suite misses it. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
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
