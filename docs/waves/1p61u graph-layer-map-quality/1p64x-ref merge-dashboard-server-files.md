# Merge the two dashboard-server files into one (lock holds startup info)

Change ID: `1p64x-ref merge-dashboard-server-files`
Change Status: `planned`
Owner: Engineering
Status: implemented
Completed At: 2026-06-17
Last verified: 2026-06-17
Wave: `1p61u graph-layer-map-quality`

> Operator-directed addition (2026-06-17), acknowledged as unrelated to the codebase-map theme of this wave. Folded in at operator request to do it now.

## Rationale

The local dashboard maintains TWO sidecar files under `.wavefoundry/`:
- `dashboard-server.lock` — the lifetime `flock` file. Acquiring it writes `{pid, started_at, lock}` (`dashboard_lib.py:185`); the server process holds the lock for its whole life.
- `dashboard-server.json` — `dashboard_metadata_path`, the richer startup info (`host, port, url, entrypoint, pid, started_at`), written after the port binds and read by `running_meta` (`server_impl.py`), `read_dashboard_metadata`, and `upgrade_wavefoundry`.

The two overlap (both carry `pid`/`started_at`) and the split is unnecessary: `flock` is advisory and tied to the open file description, so the lock holder can rewrite the lock file's *content* in place without releasing the lock. Collapsing to one file (the lock, carrying the startup info) removes a redundant sidecar.

## Requirements

1. A single file — `dashboard-server.lock` — is both the OS lock and the startup-metadata store (`host/port/url/entrypoint/pid/started_at`). `dashboard-server.json` is no longer written or read anywhere.
2. **Lock semantics preserved.** The server keeps its lifetime `flock` while the file's content is updated. The metadata write MUST be an in-place truncate-write (`write_text`), NOT an atomic temp+rename — a rename would point the path at a new inode and orphan the held lock, letting a second server acquire it. (`flock` is per-open-file-description; in-place truncate keeps the holder's lock intact.)
3. Writing the merged lock file must not drive index staleness (`.lock` is already a transient artifact; add the explicit path to the ignore lists, mirroring the old `.json` entries).
4. No behavior change otherwise: "already running" detection (lock-busy + url echo), upgrade meta read, and stop/cleanup all work off the one file. Generic; framework-script change.

## Scope

**In scope:**

- `dashboard_lib.py`: `dashboard_metadata_path(root)` returns the `dashboard-server.lock` path; document the in-place-write/no-rename requirement on `write_dashboard_metadata`.
- `server_impl.py`: the hardcoded `dashboard-server.json` literal (`~:6482`) uses `dashboard_lib.dashboard_metadata_path(root)`; the other two sites already route through the helper.
- `upgrade_wavefoundry.py`: the hardcoded `dashboard-server.json` meta path (`~:140`) routes through the helper / lock name.
- `indexer.py`: drop `.wavefoundry/dashboard-server.json` from `HARDCODED_EXCLUDE_PATHS` + `_PROJECT_STALE_IGNORE_PATHS`; add `.wavefoundry/dashboard-server.lock` to both.
- Tests: repoint `dashboard-server.json` references to the lock file.

**Out of scope:**

- `dashboard-start.lock` (the transient start lock) — unchanged.
- Any change to the lock acquisition / port selection / SSE behavior.

## Acceptance Criteria

- [x] AC-1: One file (`dashboard-server.lock`) holds both the lock and the full startup metadata; no `dashboard-server.json` is written or read anywhere (repo-wide grep clean in non-historical source).
- [x] AC-2: Lock integrity preserved — a test shows the server holds `flock` while its content carries the metadata, a second start is rejected as "already running" and reads the url from the lock file; the metadata write is in-place (no temp+rename).
- [x] AC-3: The merged lock file does not drive index staleness (explicit ignore-list entries + `.lock` transient handling); full suite + docs-lint clean.

## Tasks

- [x] Point `dashboard_metadata_path` at `dashboard-server.lock`; document the in-place-write requirement.
- [x] Route the `server_impl.py` + `upgrade_wavefoundry.py` hardcoded `.json` paths through the helper.
- [x] Swap the `.json` ignore-list entries for `.lock` in `indexer.py` (both lists).
- [x] Update tests; full suite + docs-lint.

## Affected Architecture Docs

`N/A` — internal dashboard sidecar consolidation; no boundary/flow/verification change.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The consolidation itself — one file, no `.json`. |
| AC-2 | required | Lock correctness is load-bearing; an orphaned lock would let two servers run. |
| AC-3 | important | The merged file must not churn the index. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-17 | Operator: combine the two dashboard-server files into one — the lock file holds the extra startup info. | `dashboard_lib.py:151,185,216`; `server_impl.py:6482`; `upgrade_wavefoundry.py:140`; `indexer.py:372,404` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-17 | The lock file carries the metadata; metadata write stays an in-place truncate-write. | `flock` is per-open-file-description — in-place truncate preserves the held lock; temp+rename would orphan it and break mutual exclusion. | Keep two files (rejected — operator wants one); atomic rename write (rejected — orphans the lock). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Truncate-write briefly empties the lock file → a concurrent reader sees `{}`. | Readers default to `{}` (`_read_json`) and the `running_meta` url-gate treats that as "starting"; identical to the prior `.json` write_text non-atomicity. |
| A future change switches the metadata write to temp+rename and orphans the lock. | AC-2 test + an explicit code comment on `write_dashboard_metadata` documenting the no-rename requirement. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
