# Dashboard Process Identity and Lifecycle Honesty

Change ID: `1xpo1-bug dashboard-process-identity-and-lifecycle-honesty`
Change Status: `review`
Owner: Engineering
Status: active
Last verified: 2026-09-11
Wave: 1xq4f dashboard-lifecycle-integrity

## Rationale

A dashboard started through the documented CLI fallback cannot be stopped or restarted by the MCP lifecycle tools, and the restart tool reports success when it fails. Both were observed together on 2026-09-11 while restarting this repository's dashboard.

The chain is short and mechanical. `wf_cli._SUBCOMMANDS["dashboard"]` launches with the prefix `["--daemon", "--open"]` and no `--root`, because `dashboard_server.main` resolves the root itself through `dashboard_lib.discover_root`. `_daemonize` then builds the detached child's argv as `[a for a in argv if a != "--daemon"]`, so it receives the resolved root as a parameter but never passes it on. Meanwhile `dashboard_lib.dashboard_cmdline_pids` matches, in its own words, only processes whose `--root` resolves to this exact root. A CLI-launched dashboard therefore serves correctly but is invisible to every consumer of that scan.

The consequences land on the lifecycle tools. `wf_stop_dashboard` finds no verifiable target, correctly refuses to signal the recorded PID under the wave `1rswx` control, and returns `status: "ok"` carrying `stopped: false` with a `dashboard_pid_unverified` diagnostic. `wf_restart_dashboard_response` gates only on `stop_env.get("status") != "ok"`, so that honest report passes the guard untouched; it then spawns a replacement that exits immediately against the still-held start lock, and finally sets `data["restarted"] = True` unconditionally. The observed response claimed `stopped: false` and `restarted: true` in the same object, named the exited child as the new PID, and left it `<defunct>`. The operator is told the dashboard restarted while the original process keeps the port and keeps running the pre-edit code.

The identity defect is the root cause and the reporting defects are what make it silent. Fixing only the launcher would leave the tools willing to claim a restart that did not happen the next time a process is unverifiable for any other reason.

## Requirements

1. Every managed launcher path (CLI daemon and MCP start) must produce a dashboard process whose command line carries a `--root` that resolves to its repository root, so `dashboard_lib.dashboard_cmdline_pids` identifies it.
2. `wf_stop_dashboard` and `wf_restart_dashboard` must be able to stop a dashboard launched through the CLI daemon entry.
3. `wf_restart_dashboard` must not report a restart that did not happen. When the stop lane leaves a live process it could not verify, the response must say so and must carry that lane's diagnostic.
4. `wf_start_dashboard` must not report a started dashboard when the process it spawned exited without binding, and must not leave that child unreaped.
5. The wave `1rswx` control must survive unchanged: when a successful scan cannot verify an `os.kill`-alive PID, it is never signalled, because a recycled PID is indistinguishable from a scan-missed dashboard without the cmdline check. The established scan-unavailable fallback is unchanged and tested separately.
6. Explicit `--root` invocation and root auto-discovery keep their current behavior, including the daemon re-spawn marker that prevents an infinite loop.

## Scope

**Problem statement:** the CLI launcher omits the argument that the process scan uses as identity, and the MCP lifecycle tools report success regardless of whether the work happened.

**In scope:**

- Normalizing the detached child's argv in `dashboard_server._daemonize` to exactly one absolute resolved `--root` pair, including discovery and explicit split/equal forms. Preserve the selected repository rather than the literal relative argument after changing child cwd.
- Making existing root-token matching platform-faithful for actual process output, including unquoted spaced paths on POSIX, in `dashboard_lib.dashboard_cmdline_pids`. Keep command-line identity, exact repository isolation, and conservative refusal when identity is ambiguous; do not add a new signalling authority.
- Deriving `restarted` in `wf_restart_dashboard_response` from the stop and start outcomes rather than asserting it.
- Confirming the spawned child is serving before `wf_start_dashboard_response` claims a started dashboard, and reaping it when it is not.
- Regression tests for CLI-launch identity, CLI-launch stop, and both reporting paths, each with a named mutation proof. Use isolated temporary repositories, disable browser opening, bound waits and tear down every spawned process; native Windows process-handle cleanup replaces POSIX zombie assertions where appropriate.
- Correct the obsolete endpoint-metadata path in `docs/architecture/threat-model.md`; this is documentation only and changes no trust boundary.
- Updating the dashboard launch flow in `docs/architecture/data-and-control-flow.md` to record that process identity depends on the `--root` token.

**Out of scope:**

- Replacing command-line matching with a different identity channel such as lock-record or start-time comparison.
- Making a manually launched foreground server without `--root` manageable by MCP; foreground operators retain the existing explicit `--root` invocation contract.
- Any change to the `1rswx` signalling control, to port selection and the recorded-port preference, or to the upgrade pause behavior.
- Surfacing the upgrade pause in the browser UI, which currently consumes neither the snapshot field nor the SSE event.

## Acceptance Criteria

- [x] AC-1: A dashboard launched through the CLI daemon entry is identified by `dashboard_lib.dashboard_cmdline_pids` for its repository root. A test drives that entry, asserts the detached child's PID appears in the scan, and fails when the root injection is removed from `_daemonize`.
- [x] AC-2: `wf_stop_dashboard` stops a dashboard launched through the CLI daemon entry and clears its metadata. A test launches through that entry, calls the tool, asserts the process is gone, and fails when the root injection is removed.
- [x] AC-3: `wf_restart_dashboard` reports that no restart occurred, and carries the stop lane's diagnostic, when the stop lane leaves a live process it could not verify. A test injects that condition, asserts the response does not claim a restart, and fails when the unconditional `restarted` assignment is restored.
- [x] AC-4: `wf_start_dashboard` reports that no dashboard was started, rather than naming the spawned PID, when that child exits without binding; the child is reaped. A test spawns an immediately-exiting child, asserts the response claims no started dashboard and leaves no zombie, and fails when the readiness confirmation is removed.
- [x] AC-5: An `os.kill`-alive but cmdline-unverified PID is still never signalled. The existing `1rswx` security assertions remain unchanged (including the established distinction between a successful scan with no match and a scan that is unavailable), and a mutation that adds the unverified PID back to the kill targets fails a named test.
- [x] AC-6: Explicit `--root` invocation and root auto-discovery are unchanged. Tests cover discovered roots, explicit absolute and relative roots, `--root=value`, and paths with spaces; the detached child receives exactly one absolute resolved root and selects the same repository as its parent. The daemon re-spawn marker still prevents a second detach. Process-scan tests must use real platform command-line output where available, not only artificially quoted fixtures.

## Lifecycle outcome contract

- A successful stop (`stopped: true`) or confirmed absence (`already_stopped: true`) permits the start lane. A live-unverified response, stop error or partial termination does not; retain its diagnostics and return `restarted: false`. Restarting an absent dashboard remains supported.
- `started: true` requires a serving dashboard confirmed within the existing bounded wait. Exited children are polled/waited and reaped before returning failure; no dead spawned PID is returned as the running dashboard. A still-live child at timeout is reported as pending/unconfirmed (`started: false`, `starting: true`), retained for later reconciliation, and is not killed merely for missing the readiness deadline.
- A concurrently serving, repository-verified instance is returned as `already_running` with its actual PID and URL, not attributed to an exited replacement. Preserve the existing no-duplicate/recorded-port behavior. A responding URL alone is not authorization to signal its recorded PID.
- AC-3/AC-4 tests cover stop success, confirmed absence, unverified-live refusal, stop error/partial failure, immediate child exit, live timeout, and adoption of a competing verified instance. A pending start or adoption alone must not produce a positive claim that this operation restarted a process.


## Tasks

- [x] Normalize child root arguments in `dashboard_server._daemonize` to one `--root <absolute resolved root>` pair, preserving parent-selected repository semantics for discovery and explicit split/equal/relative forms.
- [x] Repair root-token matching for platform-faithful process output; test spaced roots against real native output where available, exact repository isolation, prefix/suffix lookalikes, malformed/ambiguous arguments and scan-unavailable behavior. Never turn an ambiguous match into signal authority.
- [x] Derive `restarted` in `wf_restart_dashboard_response` from the stop and start outcomes, and distinguish a successful stop or confirmed `already_stopped` from an unverified live process. Never invoke start after stop failure or unverified-live refusal.
- [x] Confirm the spawned child is serving in `wf_start_dashboard_response` before reporting a started dashboard, and reap a child that exited.
- [x] Add the CLI-launch identity and CLI-launch stop tests to `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`.
- [x] Add the restart-honesty and start-honesty tests to `.wavefoundry/framework/scripts/tests/test_server_tools.py`.
- [x] Record the mutation proof for each new guard, naming the test that fails when the guard is deleted or loosened.
- [x] Update the dashboard launch flow in `docs/architecture/data-and-control-flow.md` so the `--root` token is documented as the identity channel rather than an optional convenience.
- [x] Confirm the `1rswx` control tests pass unchanged.
- [x] Correct the dashboard endpoint-metadata path in `docs/architecture/threat-model.md`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| L1 launcher identity | implementer | — | `_daemonize` injection plus the CLI-launch identity and stop tests (AC-1, AC-2, AC-6). |
| L2 lifecycle reporting | implementer | — | Restart and start truthfulness plus their tests (AC-3, AC-4, AC-5). Independent of L1 by file and by AC. |
| L3 docs | implementer | L1 | Launch-flow documentation once the injected argv is settled. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/dashboard_server.py`, `.wavefoundry/framework/scripts/dashboard_lib.py`, `.wavefoundry/framework/scripts/server_impl.py`, `.wavefoundry/framework/scripts/wf_cli.py`, `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`, `.wavefoundry/framework/scripts/tests/test_server_tools.py`, `docs/architecture/data-and-control-flow.md`, `docs/architecture/threat-model.md`

L1 owns `dashboard_server.py`, the bounded root-matching change in `dashboard_lib.py`, and `test_dashboard_server.py`. L2 owns `server_impl.py` and `test_server_tools.py`. Within this change, no file is written by two lanes. Across the expanded wave, compatibility C2 in `1xoye` shares dashboard/server files and tests: serialize those edits with one owner per file. Its C4 documentation work also shares `data-and-control-flow.md` with L3. `wf_cli.py` is a read-only review target under the selected approach.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` documents the dashboard startup and lifecycle flow, and its step 1 shows the launch as `dashboard_server.py --root . [--open]`, which is precisely the invariant the CLI path violates. That document needs the identity role of `--root` stated.

`docs/architecture/threat-model.md` needs only the operator-approved metadata path correction. `docs/architecture/cross-cutting-concerns.md` needs no update: the trust boundary, the loopback bind, and the metadata write boundary are all unchanged by this change.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The root cause; without it the lifecycle tools remain unable to see a CLI-launched dashboard. |
| AC-2 | required  | The operator-visible consequence of AC-1 and the reason the gap matters. |
| AC-3 | required  | A false restart report is how the defect stayed silent. |
| AC-4 | required  | A start report naming a dead child misdirects any recovery attempt that follows. |
| AC-5 | required  | Preserves an existing security control that this change works next to. |
| AC-6 | important | Guards the unchanged paths against regression from the injection. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-11 | Planned from a live observation during wave `1xny6` delivery: a dashboard started with the CLI could not be restarted through MCP, and the tool reported success anyway. Root cause traced to the `_daemonize` child argv and confirmed against the scan's own matching rule. | Observed response carried `stopped: false` with `restarted: true`; the named PID was `<defunct>`; the log line `Dashboard already running for this repository.` shows the replacement child exiting. Scan behavior confirmed by calling `dashboard_lib.dashboard_cmdline_pids` against the running process, which returned it only after a relaunch through MCP. |
| 2026-09-11 | Readback: CLI/MCP managed children carry one resolved root last; distinguish serving own child, adopted competitor, pending and failed outcomes. Preserve verified-PID signalling authority and port policy. Thought: implement dashboard L1/L2 with one owner, then reconcile documentation. | Current readiness receipt and typed lane approvals; implementation now authorized. |
| 2026-09-11 | AC-1–AC-6 complete: real CLI/MCP lifecycle checks, truthful outcome matrix and unchanged signalling controls pass; eight falsifying mutants fail. Full server module: 343; dashboard: 207 with one skip; final parser-focused pass: 37. | `implementation-evidence.json`: dashboard. Canonical full suite remains pending. |

| 2026-09-11 | Implementation complete and ready for delivery review: canonical suite green, 8,898 tests across 86 files, 12 skips; receipt recomputed against the final source. Docs gate and whitespace check pass. | `implementation-evidence.json`: canonical_validation. |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-11 | Tag the child process with its resolved root, and pair that with honest restart and start reporting. | The gap closes at its source with a local change in the launcher that already holds the resolved root, the existing signalling control is untouched, and the reporting fixes keep a future unverifiable process from being reported as restarted. | Rejected: replacing command-line identity with the lock record or process start time, because it rewrites a lifecycle path carrying an explicit security control and would need a fresh PID-recycling proof for a defect that a launcher argument already fixes. Rejected: fixing only the reporting and telling the operator to stop strays by hand, because the documented CLI fallback would still produce an unmanageable dashboard. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The child root duplicates an explicitly supplied one, or a relative root resolves differently after child cwd changes. | AC-6 pins one normalized root, preservation of the selected repository, split/equal syntax and the re-spawn marker. |
| Confirming readiness before reporting a start adds latency, or flakes on a slow bind. | Reuse the existing bounded readiness wait and URL-reachability helper rather than adding a new timing path; report honestly on timeout instead of extending the wait. |
| Tightening `restarted` breaks a caller that reads it as a liveness signal. | The review targets include every consumer of the restart response, and the field only becomes false in the case that previously reported a restart that did not occur. |
| Hosts where the command-line scan is unavailable still cannot identify any dashboard. | Out of scope and unchanged: the scan already returns `None` there and callers fall back to bare liveness, so this change neither improves nor regresses those hosts. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

## Plan Review

2026-09-11: Code-grounded review clarified parent-selected root preservation across daemon cwd changes (`dashboard_server._daemonize`), restart of a confirmed-absent dashboard (`wf_stop_dashboard_response`), and distinct failed/pending/adopted startup outcomes (`wf_start_dashboard_response`). These resolve implementation branches within the existing identity and reporting requirements. Product-owner intent is the admitted bug repair and the operator's request to prepare and review this wave; no new identity authority, port policy, or upgrade behavior is proposed.

The security readiness probe also confirmed that native macOS `ps` emits spaced root arguments without quotes, which the current whitespace-terminated matcher misses. L1 therefore includes the bounded command-line matcher and exact-root isolation tests; retaining it as read-only would make the managed-launch identity requirement unachievable. This changes parsing coverage, not signalling authority.
