# Consolidate dashboard coordination files (rename lock + make start.lock transient)

Change ID: `1p5ya-enh consolidate-dashboard-lock-files`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Completed At: 2026-06-16
Last verified: 2026-06-16
Wave: `1p5xt mcp-index-freshness-monitor`

## Rationale

The dashboard keeps three coordination files in `.wavefoundry/`: `dashboard-server.json` (metadata: pid/port/url), `dashboard-process.lock` (lifetime singleton flock), and `dashboard-start.lock` (spawn-race flock). Two cleanups:

1. **One dedicated lifetime lock named `dashboard-server.lock`.** Rename `dashboard-process.lock` → `dashboard-server.lock` so the lock pairs by name with `dashboard-server.json`. The lock stays a **dedicated, never-rewritten `.lock` file** — not the metadata JSON — so its inode is rock-stable and can never be orphaned by a future metadata rewrite or atomic-rename. `dashboard-server.json` remains pure metadata (no flock on it; free to rewrite anytime).
2. **Make `dashboard-start.lock` transient — delete it after the server is up.** It only needs to exist during the launch window; once the child holds `dashboard-server.lock`, every newcomer is gated by the liveness check. So it no longer lingers in the directory.

End state (dashboard running): **`dashboard-server.json` + `dashboard-server.lock`**. `dashboard-start.lock` appears only for the instant of a launch, then is unlinked. (Down from three persistent files to two, with consistent `dashboard-server.*` naming.)

## Requirements

1. **Dedicated lifetime lock `dashboard-server.lock`.** The dashboard server process holds an advisory `flock` (POSIX `fcntl.flock` / Windows `msvcrt`, via the existing `dashboard_lock` abstraction) on `.wavefoundry/dashboard-server.lock` for its entire life. This replaces `dashboard-process.lock` (rename of `DASHBOARD_PROCESS_LOCK_NAME` and its helper). The lock file is never rewritten — it is a pure lock token.
2. **`dashboard-server.json` stays pure metadata.** pid/port/url only; **no flock on the JSON**. Readers read it freely for connection info.
3. **Liveness via flock-try on `dashboard-server.lock`.** Callers determine "running" by a non-blocking flock-try on `dashboard-server.lock`: **busy → alive**, **acquired → not running** (release immediately). Stale `server.json` content after a crash is authoritatively overridden by the flock-try (same semantics as today's `process.lock`).
4. **`dashboard-start.lock` stays an `flock`, NOT existence/`O_EXCL`.** The spawn gate is the OS `flock` on `dashboard-start.lock` — never file-existence-as-lock. This preserves crash-safety: process death auto-releases the lock, so a leftover `start.lock` is harmless and the next start re-acquires it.
5. **Correct startup ordering (race-safe).** (a) flock-try `dashboard-server.lock` → busy → already running, abort; (b) acquire `dashboard-start.lock` flock (wait/abort if busy); (c) **re-check** flock-try `dashboard-server.lock` (double-check — preserve the existing post-acquire re-check); (d) spawn the server child, which acquires `dashboard-server.lock` for life and writes `dashboard-server.json`; (e) **wait until `dashboard-server.lock` is observably flocked by the child**; (f) **only then** release + `unlink` `dashboard-start.lock`.
6. **Delete is best-effort, never load-bearing.** Because `start.lock` is an `flock`, correctness must not depend on the unlink. If a crash skips step (f), the leftover file is unlocked and the next start re-acquires it.
7. **No double-spawn window.** The unlink in (f) happens strictly after the child holds `dashboard-server.lock`, so there is never a moment where neither file gates a concurrent start. A starter blocked at (b) re-checks at (c) and bails.
8. **Watch-exclusions preserved.** `dashboard-server.json` keeps its reindex watch-exclusion (`indexer.py:372`, `dashboard_server.py:38`); `dashboard-server.lock` is covered by the existing `.lock` ignore/exclude patterns (verify it is excluded so the lock never triggers a reindex).

## Scope

**In scope:**

- Rename `dashboard-process.lock` → `dashboard-server.lock` (the dedicated lifetime flock; rename `DASHBOARD_PROCESS_LOCK_NAME` + `dashboard_process_lock` → `..._server_lock`).
- Repoint all liveness checks (`wave_dashboard_*` in `server_impl.py`, `upgrade_wavefoundry.py:140`, `dashboard_server.py`) to flock-try `dashboard-server.lock`; `server.json` stays metadata-only.
- Make `dashboard-start.lock` transient: keep the flock gate, add the post-startup `unlink` with the (a)→(f) ordering.
- Update dashboard/server tests for the new file set + flock-try liveness + transient start.lock; full suite green.

**Out of scope:**

- Flocking the metadata JSON (rejected — a dedicated `.lock` inode is more robust).
- Removing `dashboard-start.lock` entirely / inherited-fd flock handoff (rejected — fragile, Windows-hostile).
- Switching to `O_EXCL`/existence locks (rejected — loses crash auto-release).
- Any change to dashboard UI behavior or HTTP/health response shapes; the staleness-watch removal (that is `1p5xw`).

## Acceptance Criteria

- [x] AC-1: The dashboard holds a lifetime `flock` on `dashboard-server.lock`; `dashboard-process.lock` no longer exists. `dashboard-server.json` carries metadata only (no flock). Liveness checks across the codebase use a non-blocking flock-try on `dashboard-server.lock` (busy=alive, acquired=dead); verified incl. a "stale `server.json` after the process exits → flock-try shows not-running" case.
- [x] AC-2: `dashboard-start.lock` is an `flock` gate (not existence/`O_EXCL`) and is `unlink`ed after the server holds `dashboard-server.lock`; steady-state running directory shows `dashboard-server.json` + `dashboard-server.lock` only. A simulated crash before the unlink leaves a harmless leftover that the next start re-acquires (tested).
- [x] AC-3: No double-spawn under concurrent starts — the (a)→(f) ordering + post-acquire re-check verified by a concurrency test (two starts → exactly one server; the loser aborts).
- [x] AC-4: Watch-exclusions hold for both `dashboard-server.json` and `dashboard-server.lock` (neither triggers a reindex); readers still read pid/port/url freely; full suite + docs-lint clean. Coordinated with `1p5xw` edits to `dashboard_server.py`.

## Tasks

- [x] Rename the lifetime lock to `dashboard-server.lock` (`DASHBOARD_PROCESS_LOCK_NAME` → `DASHBOARD_SERVER_LOCK_NAME`, `dashboard_process_lock` → `dashboard_server_lock`); the server holds it for life.
- [x] Repoint all liveness checks to flock-try `dashboard-server.lock`; keep `server.json` metadata-only.
- [x] Keep `start.lock` as an flock; add the post-startup `unlink` with the (a)→(f) ordering + retain the double-check.
- [x] Add/confirm the `dashboard-server.lock` watch-exclusion; update tests (liveness flock-try, stale-after-exit, transient start.lock + crash-leftover-harmless, concurrent-start no-double-spawn).
- [x] Full suite + docs-lint.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| rename-lock | Engineering | —        | process.lock → dashboard-server.lock; repoint liveness flock-try |
| transient-start | Engineering | rename-lock | start.lock flock + ordered unlink after child locks |


## Serialization Points

- Shares `dashboard_server.py` with `1p5xw` — coordinate same-file edits. The lock rename + liveness rework spans `dashboard_lib.py`, `server_impl.py` (`wave_dashboard_*`), and `upgrade_wavefoundry.py`; land the helper rename before its callers.

## Affected Architecture Docs

A short note wherever dashboard coordination is described (e.g. `docs/architecture/graph-index-system.md` dashboard/runtime section, if present): the three-file model (`server.json` + `process.lock` + `start.lock`) becomes `dashboard-server.json` (metadata) + `dashboard-server.lock` (lifetime flock) with a transient `dashboard-start.lock`.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The dedicated `dashboard-server.lock` + flock-try liveness is the core consolidation. |
| AC-2 | required | Transient start.lock with crash-safe leftover is the second cleanup + safety property. |
| AC-3 | required | No-double-spawn under concurrent starts is the correctness guarantee the locks exist for. |
| AC-4 | required | Both files must stay watch-excluded; reader access preserved. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-16 | Scoped from the lock-files discussion. Operator-directed naming: the dedicated lifetime lock is `dashboard-server.lock` (rename of `dashboard-process.lock`), NOT a flock on the metadata JSON — a dedicated never-rewritten `.lock` inode is more robust (no orphan-on-rewrite risk). `start.lock` made transient (deleted after the child holds the lock). | `dashboard_lib.py:29,159,207`, `dashboard_server.py:1002,1028` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-16 | Dedicated lifetime lock `dashboard-server.lock` (rename of `process.lock`); JSON stays metadata-only | A dedicated, never-rewritten `.lock` inode is rock-stable — future metadata rewrites/atomic-renames can't orphan the lock; consistent `dashboard-server.*` naming; locks stay `.lock` files | Flock the metadata JSON (rejected by operator — unusual + fragile to future JSON rewrites); keep `process.lock` name (rejected — rename pairs it with server.json) |
| 2026-06-16 | `start.lock` stays an `flock`; delete it after the child locks `dashboard-server.lock` | flock = crash auto-release, so the delete is cosmetic, never load-bearing; tidy steady-state dir without losing crash-safety | Existence/`O_EXCL` lock (rejected — strands a stale lock on crash); never delete (rejected — operator wants the tidy dir) |
| 2026-06-16 | Keep `start.lock` rather than collapse start + lifetime into one lock | The spawn coordinator and the running child are different processes; the inherited-fd handoff to share one lock is fragile + Windows-hostile | Inherited-fd single flock (rejected — fragile); O_EXCL gate (rejected — stale-file races) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Deleting `start.lock` opens a double-spawn window | Unlink strictly after the child holds `dashboard-server.lock` (step f); post-acquire double-check (step c); concurrency test (AC-3) |
| Liveness check breaks during the rename | Rename the helper + all call sites together; AC-1 tests flock-try liveness + stale-after-exit |
| Stale `server.json` content after a crash misread as running | Liveness is the flock-try on `dashboard-server.lock`, not `server.json` content presence; AC-1 tests stale-after-exit |
| `dashboard-server.lock` triggers a reindex | Confirm it's covered by the existing `.lock` watch/ignore exclusions; AC-4 |
| Cross-platform flock differences (msvcrt) | Reuse the existing `dashboard_lock` abstraction (handles posix + nt); test both code paths |
| Conflict with `1p5xw` edits to `dashboard_server.py` | Coordinate as same-file changes within the wave; land the shared helper rename first |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
