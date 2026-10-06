# The Hook Timeout Test Fails Under Load

Change ID: `1zybz-bug hook-timeout-test-flakes-under-load`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-05
Wave: 1zyc0 tree-kill-test-load-flake

## Rationale

`test_tree_kill_routing.GrandchildTests.test_convention_hook_timeout_ends_the_tree_and_aborts` patches `upgrade_wavefoundry._HOOK_TIMEOUT_S` to 1.5 s. On a loaded machine the hook's `/bin/sh` can be killed before it writes the grandchild's pid, so the test fails with "grandchild never recorded its pid". It failed in two full scratch suites during wave 1zv8c and on the pre-wave tree under the same load, and passes on a quiet machine. A red full suite blocks the framework test receipt that wave close requires.

## Requirements

1. Every test that races a child's startup (the child must record a grandchild pid) against a short production deadline uses one shared test constant with headroom for a loaded machine (5 s), defined once per test module with a comment saying why: in `tests/test_tree_kill_routing.py`, `GrandchildTests.test_setup_install_step_timeout_ends_the_tree` (1.5 s; its `timeout` assertion uses the constant), `GrandchildTests.test_convention_hook_timeout_ends_the_tree_and_aborts` (patched `_HOOK_TIMEOUT_S` 1.5 s; exit code 3 unchanged), `RoutedGitSiteTests.test_gitignored_paths_timeout_ends_the_fake_gits_descendant` (patched 1.5 s; elapsed bound unchanged) and `ExitedUnreapedChildTests.test_exited_child_with_a_descendant_holding_the_pipe_ends_the_group` (1.5 s); in `tests/test_subprocess_util.py`, `RunWithTreeKillTests.test_timeout_kills_the_grandchild_and_returns_promptly` (1.5 s; its prompt-return bound is adjusted to stay meaningful). Each still asserts that the deadline ends the whole tree.
2. `GrandchildTests.test_parent_interrupt_ends_the_tree_through_a_setup_install_step` does not race a deadline: its interrupt fires from a thread that waits for the pid file (capped at 20 s) instead of a fixed 1.0 s timer, so the interrupt still ends the tree and the 30 s step timeout never fires.
3. When the pid is missing, the failure message says the child may have been ended by the deadline before it recorded the pid.
4. No production code changes.

## Scope

**Problem statement:** a timing test fails under load.

**In scope:**

- `tests/test_tree_kill_routing.py` and `tests/test_subprocess_util.py`.

**Out of scope:**

- Other timing tests.

## Acceptance Criteria

- [x] AC-1: `test_tree_kill_routing.py` and `test_subprocess_util.py` pass ten consecutive runs while a full suite runs in parallel in another scratch copy, and each of the six tests still fails when the tree kill it covers is removed (mutation; for the interrupt test, the kill in the `KeyboardInterrupt` branch of `run_with_tree_kill`).

## Tasks

- [x] Shared 5 s deadline constant for the five deadline tests; pid-gated interrupt; clearer missing-pid message
- [x] Load and mutation check

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| test-fix | implementer | — | |


## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_tree_kill_routing.py`, `.wavefoundry/framework/scripts/tests/test_subprocess_util.py`

## Affected Architecture Docs

N/A: test-only.

## Platform Behavior

POSIX test (`/bin/sh` hook); unchanged on Windows, where the class is skipped as before.

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | a red suite blocks close |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-05 | Implemented: `_TREE_DEADLINE_S = 5.0` in `test_tree_kill_routing.py` for the four deadline tests there and a local 5 s deadline in `test_subprocess_util` (prompt-return bound kept at deadline + 13.5 s); the interrupt test waits for the pid file and installs `signal.default_int_handler` for its duration, because `_thread.interrupt_main` does nothing while SIGINT is ignored (any run started with `&`, nohup or a CI runner that ignores SIGINT; found when the load suite run that way failed this test); missing-pid messages name the deadline. Mutation (tree kill disabled) first left two tests passing because the helper waits for the 60 s child and the 60 s grandchild ended with it; every grandchild now sleeps 300 s so it outlives its parent, and all six tests fail with the kill disabled. Gapfill: shell reads and probes in scratch copies; the work was executed load and mutation runs on two test files | rep88: 10 of 10 runs of both files OK while a full suite ran in parallel (load average up to 27); load suite 11277 OK; mutation: 6 of 6 fail |
| 2026-10-05 | Readiness review folded in: `ExitedUnreapedChildTests` and `test_subprocess_util` share the race (six tests in all); the interrupt test waits for the pid file instead of a timer; clearer missing-pid message; real suite-time figure. Census of short deadlines across test files: the `test_setup_index` probe-timeout test and the 0.5 s killpg test have no pid handoff and are unaffected | readiness review; grep census |
| 2026-10-05 | Widened to the three sibling tests with the same startup race (1.5 s install step, 1.0 s interrupt timer, 1.5 s fake git); every observed failure was `grandchild never recorded its pid` in the hook test | fullsuite11-13 tracebacks |
| 2026-10-05 | Planned after failures in fullsuite11 and fullsuite12 of wave 1zv8c, reproduced on the pre-wave tree under load | `fullsuite11.log`, `fullsuite12.log` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-05 | Separate change, not folded into 1zv8c | outside the admitted scope | late admission |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A longer deadline slows the suite | about +17 s serial within `test_tree_kill_routing.py` and +3.5 s in `test_subprocess_util.py`; files run in parallel, so wall time grows by at most the larger file's increase |
| A fixed margin is still a bet on load | 5 s matches the existing 5 s pid poll; the interrupt test no longer depends on a margin |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
