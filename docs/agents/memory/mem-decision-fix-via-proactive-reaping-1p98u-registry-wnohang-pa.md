# Decision: Fix via proactive reaping (1p98u registry+WNOHANG pattern)…

Owner: Engineering
Status: superseded
Last verified: 2026-07-18

Memory ID: `mem-decision-fix-via-proactive-reaping-1p98u-registry-wnohang-pa`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1rswx-bug dashboard-zombie-child-reaping:96dc5b5f8d5980d8`
Validation: rewrite
Validated by: agent
Action delta: Retain server-owned PID registration and nonblocking reaping before changing dashboard or background-process liveness logic.
Validation rationale: The current POSIX process model still needs explicit child reaping, and a generic liveness probe cannot distinguish a zombie from a running process.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `mem-reap-server-owned-posix-children-before-liveness-checks`
## Summary

Decision (wave 1rtnn): Fix via proactive reaping (1p98u registry+WNOHANG pattern) + a zombie-safe stop-path liveness check, keeping the current `start_new_session` spawn model.. Rationale: Reuses two already-proven patterns in this codebase (1p98u reaping, 1p654 cmdline-verified liveness), is contained to `server_impl.py`, fixes both the accumulation and the tool-failure symptoms, and avoids reworking the spawn/detach model..

## Evidence

- `1rswx-bug dashboard-zombie-child-reaping`
- `1rtnn`

## Targets

- `server_impl.py`
