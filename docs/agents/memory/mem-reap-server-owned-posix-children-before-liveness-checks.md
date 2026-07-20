# Reap server-owned POSIX children before liveness checks

Owner: Engineering
Status: active
Last verified: 2026-07-18

Memory ID: `mem-reap-server-owned-posix-children-before-liveness-checks`
Kind: `successful_pattern`
Confidence: 0.95
Created: 2026-07-18
Updated: 2026-07-18
Source event: `decision-log:1rswx-bug dashboard-zombie-child-reaping:96dc5b5f8d5980d8`
Validation: promote
Validated by: agent
Action delta: Retain server-owned PID registration and nonblocking reaping before changing dashboard or background-process liveness logic.
Validation rationale: The current POSIX process model still needs explicit child reaping, and a generic liveness probe cannot distinguish a zombie from a running process.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

When changing server-launched dashboard or background processes, register only PIDs the server spawned, reap them with waitpid and WNOHANG before liveness decisions, and avoid a SIGCHLD handler that could steal synchronous subprocess waits.

## Evidence

- `1rswx-bug dashboard-zombie-child-reaping`
- `1rtnn`
- `.wavefoundry/framework/scripts/server_impl.py:5947`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py:1854`

## Targets

- `.wavefoundry/framework/scripts/server_impl.py`
