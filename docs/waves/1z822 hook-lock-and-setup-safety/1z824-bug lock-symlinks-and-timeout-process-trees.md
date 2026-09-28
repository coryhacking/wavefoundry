# Lock Files Follow Symlinks and Timeouts Leave Process Trees

Change ID: `1z824-bug lock-symlinks-and-timeout-process-trees`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-27
Wave: 1z822 hook-lock-and-setup-safety

## Rationale

**Lock files follow symlinks (B4).** `runtime_lock.RuntimeFileLock.acquire` opens its carrier with `path.open("a+b")`, and `write_metadata` then seeks to zero and truncates it; `write_json_in_place` opens with `r+b` and truncates the same way. All three follow a symlink at the lock path. A repository can commit a symlink at a lock location (for example under `.wavefoundry/locks/`), so running a Wavefoundry command in a cloned repository could truncate and overwrite any file the user can write. `RuntimeFileLock` backs the lifecycle, dashboard, index-build and review-evidence publication locks.

**Timeouts leave process trees (B5).** `server_impl._mcp_subprocess_run` calls `subprocess.run(timeout=…)` directly and `sensor_runner.run_sensor` calls `subprocess_util.isolated_run(timeout=…)`, which wraps `subprocess.run`. Neither starts the child in its own session or process group (only `isolated_popen` sets `start_new_session`). On timeout `subprocess.run` kills only the direct child. A grandchild, such as a test runner a sensor starts, keeps running, and on Windows `subprocess.run` then waits on pipes the grandchild still holds, so the call does not return. Found by an external review of `v1.27.0` (RFC section 7, B4, B5), verified against the code on 2026-09-27.

## Requirements

1. **Lock carriers never follow a symlink.** `RuntimeFileLock.acquire` and `write_json_in_place` open the carrier without following a final-component symlink. On POSIX: `os.open` with `O_NOFOLLOW` plus flags equivalent to the current mode (`O_RDWR|O_CREAT|O_APPEND` for the lock's `a+b`; `O_RDWR|O_CREAT` for `write_json_in_place`, which must not create a dangling symlink's target), wrapped by `os.fdopen`. On Windows, where `O_NOFOLLOW` does not exist, refuse only on a positive finding: `os.lstat` shows a symlink or a reparse point; otherwise open as today (with `O_BINARY`). A refusal raises `RuntimeLockError` naming the path and saying it is a symlink. A missing carrier is still created. Behavior for an ordinary file is unchanged.
2. **Timed subprocesses kill their tree.** `subprocess_util` gains `run_with_tree_kill`, which behaves like `isolated_run` (same isolation, capture and encoding defaults, same `CompletedProcess` result and `TimeoutExpired` on timeout). It starts the child in its own group (`start_new_session=True` on POSIX, `CREATE_NEW_PROCESS_GROUP` on Windows) so that the kill can never reach the caller's own group. On timeout, and on any other exception or interrupt while waiting, it terminates the child's tree before re-raising: on POSIX it signals exactly the process group whose id is the child's pid, ignoring `ProcessLookupError` when the group is already empty; on Windows it runs `taskkill /PID <pid> /T /F` through `isolated_run` with a short timeout. After the kill, a second output drain is bounded so a surviving pipe holder cannot hang the call. It is used by the timed calls whose command can start arbitrary descendants: `run_sensor` (operator-declared commands) and `_mcp_subprocess_run` (framework helper children). Timed calls to fixed short probes (`git`, `nvidia-smi`) and calls without a timeout are unchanged. Descendants that start their own session, or whose intermediate parent has already exited on Windows, can escape; that is a known limit.

## Scope

**Problem statement:** a committed symlink can redirect a lock write, and a timed-out helper can leave work running or hang the server.

**In scope:**

- `runtime_lock.py` carrier opening;
- `subprocess_util.run_with_tree_kill` and its use in `_mcp_subprocess_run` and `run_sensor`;
- tests.

**Out of scope:**

- symlinked parent directories of a lock (the carrier directories are created by Wavefoundry; a later wave can adopt `path_containment` for the parent chain);
- the other timed `isolated_run` and `_mcp_subprocess_run`-style calls whose commands are fixed short probes (a readiness census found 31 timed `isolated_run` and 8 timed `_mcp_subprocess_run` calls; the probes among them do not start long-lived descendants);
- Windows Job Objects (a more complete tree kill than `taskkill /T`).

## Acceptance Criteria

- [x] AC-1: with a symlink at a lock path pointing at another file, `RuntimeFileLock(...).acquire()` refuses with `RuntimeLockError` and the target's bytes are unchanged; `write_json_in_place` refuses for a symlink to an existing file and for a dangling symlink, and creates no file at the dangling target; with an ordinary or missing carrier both behave as before; on Windows (by patching) a reparse-point `lstat` is refused and an ordinary file is not.
- [x] AC-2: `run_with_tree_kill` on a command that starts a long-lived grandchild and exceeds its timeout raises `TimeoutExpired`, returns within a bounded time after the timeout, and leaves no grandchild running (checked by the grandchild's recorded pid); the caller's own process group is never signalled; a command that finishes in time returns the same `CompletedProcess` as `isolated_run`.
- [x] AC-3: `_mcp_subprocess_run` and `run_sensor` route timed calls through `run_with_tree_kill`, and a sensor that times out still reports `Sensor timed out after …`.
- [x] AC-4: the change's own suites and every test it adds pass, and the documents this change edits validate.

## Tasks

- [x] Non-following carrier open in `runtime_lock.py` (POSIX and Windows branches).
- [x] `run_with_tree_kill` in `subprocess_util.py`; route `_mcp_subprocess_run` and `run_sensor`.
- [x] Tests for AC-1 to AC-3 (Windows branch tested by patching); CHANGELOG `[Unreleased]` Fixed bullets.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Locks and trees | implementer | readiness | Single write owner; MCP code tools for reads |
| Review | combined reviewer | Locks and trees | One combined reviewer |

## Serialization Points

- `.wavefoundry/framework/scripts/runtime_lock.py`, `.wavefoundry/framework/scripts/subprocess_util.py`, `.wavefoundry/framework/scripts/sensor_runner.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/tests/test_runtime_lock.py`, `.wavefoundry/framework/scripts/tests/test_subprocess_util.py`, `.wavefoundry/framework/scripts/tests/test_sensor_runner.py`
- `CHANGELOG.md` (shared by all three changes in this wave)

## Affected Architecture Docs

`N/A`: no boundary or flow changes; both fixes harden existing helpers behind their current interfaces.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | A committed symlink can overwrite a user file |
| AC-2 | required | A timed-out helper can hang the MCP server on Windows |
| AC-3 | required | The fix must reach the callers that set timeouts |
| AC-4 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-27 | Delivery review blocked on B1: routing timed `_mcp_subprocess_run` calls through `run_with_tree_kill` bypassed five tests that stub `subprocess.run` (`PreferredPythonSubprocessTests`, `RunValidateTests`, `RunGardenTests`); they now stub `subprocess_util.run_with_tree_kill`. A scratch census made `run_with_tree_kill` raise whenever `subprocess.run` is mocked (the probe fires under a mock) and ran the four server and dashboard test modules: zero other tests bypass their stub. N2: Windows now refuses only name-surrogate reparse points (symlink and junction tags), so OneDrive placeholders and deduplicated files still lock; the test covers all four tags | delivery review, scratch census |
| 2026-09-27 | Implemented: `runtime_lock._open_carrier` opens with `O_NOFOLLOW` (POSIX) or refuses a positive symlink or reparse-point `lstat` (Windows), used by `RuntimeFileLock.acquire` and `write_json_in_place`. `subprocess_util.run_with_tree_kill` starts the child in its own session or process group, kills the group (or `taskkill /T /F`) on timeout or any exception while waiting, and bounds the post-kill drain; `run_sensor` and timed `_mcp_subprocess_run` calls use it. Tests use real symlinks, a real grandchild pid, a `killpg` spy and a real timed-out sensor; scratch mutants (lock follows links, no `killpg`) each fail a test | `test_runtime_lock`, `test_subprocess_util`, `test_sensor_runner`, `test_server_tools.McpSubprocessHelperTests` |
| 2026-09-27 | Readiness round 1 blocked on F1: the plan claimed `isolated_run` starts children in a new session; it does not (only `isolated_popen` does), and `_mcp_subprocess_run` calls `subprocess.run` directly, so a `killpg` on that premise could signal the server's own group. Amended: `run_with_tree_kill` creates the group itself and signals only `pgid == child pid`. Notes folded in: kill on any exception while waiting, the timed-call scope stated as a rule with the census, Windows refusal only on a positive reparse finding, `O_APPEND`/`O_BINARY` semantics, and AC-1 covering the dangling-symlink case instead of a vacuous `write_metadata` check | readiness review |
| 2026-09-27 | Planned from RFC section 7 (B4, B5). Verified: `RuntimeFileLock.acquire` uses `path.open("a+b")`, `write_metadata` and `write_json_in_place` truncate; `_mcp_subprocess_run` and `run_sensor` use `subprocess.run(timeout=…)` semantics with no tree kill, and `subprocess_util` has no tree-kill helper | `code_read`, `code_outline`, `code_keyword` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-27 | Refuse a symlinked carrier rather than resolve it | A lock path is Wavefoundry-owned; a symlink there is never legitimate | Follow the link inside the repository only (needs containment checks for no benefit) |
| 2026-09-27 | New `run_with_tree_kill`, applied to the two timed call sites | Smallest change that fixes the hang; `isolated_run` has many untimed callers that need no change | Change `isolated_run` for everyone (wider blast radius) |

## Risks

| Risk | Mitigation |
| --- | --- |
| A user who symlinked `.wavefoundry/` locks elsewhere on purpose | Refusal names the path; that setup was never supported |
| Killing a process group also kills the caller | `run_with_tree_kill` itself starts the child in a new session and signals only the group whose id equals the child's pid (readiness F1: the earlier premise that the child already had its own session was false) |
| A real Windows `stat`/`fstat` difference bricks every lock | Refuse only on a positive symlink or reparse-point finding; never on an identity mismatch |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
