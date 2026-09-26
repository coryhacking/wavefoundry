# Retry, Explain and Clear the Context-Efficiency Accounting Gap

Change ID: `1z1vu-bug context-efficiency-gap-permanent-and-unexplained`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-25
Wave: 1z2m4 context-efficiency-gap-recovery

## Rationale

On 2026-09-25 at 15:50:01 one context-efficiency telemetry write failed, and the fail-closed barrier wrote `.wavefoundry/logs/context-efficiency.gap`. From then on every wave's `## Context Efficiency` showed `accounting_gap` with zero calls (waves `1yzj9` partly, `1z1vs`, `1z1vt`), and every tool response carried `"persistence": "poisoned"`. The operator cleared the sentinel and the `meta.accounting_gap` row by hand.

Three defects made one transient failure permanent and invisible:

- **No retry of the transaction.** `_open_write_store` retries a locked open for about 0.4 seconds, but everything after the open runs under a 50 ms lock wait (`sqlite3.connect(path, timeout=0.05)` and `PRAGMA busy_timeout=50` in `_open_write_store_once`). Several MCP servers were attached to this repository at once, so a lock held longer than 50 ms at `BEGIN IMMEDIATE` or at commit becomes `database is locked`, and the `except Exception` in `_commit_event` (and the one in `ProcessTelemetry.flush`) calls `_write_gap_sentinel` on the first error.
- **No reason recorded.** `_write_gap_sentinel` creates an empty file; the exception text reaches only the one failing response. Nobody can tell afterwards why the gap exists.
- **No way out.** Nothing deletes the sentinel or the `meta` flag; `read_store_health` reports `accounting_gap` forever, and the only recovery is a manual file delete plus a SQLite edit.

## Requirements

1. **Retry transient errors.** A telemetry write transaction (`_commit_event`, and the transfer transaction in `ProcessTelemetry.flush`) that fails with a busy or locked SQLite error (`sqlite3.OperationalError` whose `sqlite_errorcode` is `SQLITE_BUSY` or `SQLITE_LOCKED`, falling back to the message when no code is present) is rolled back, closed and retried as a whole attempt with bounded backoff, within one budget of 10 seconds per write (operator decision: a lock is a timing issue, so wait long enough for it to clear). The existing open-retry loop in `_open_write_store` counts against the same budget rather than adding to it. Replay is safe because events are deduplicated by `event_id`. The budget and backoff are module constants so tests can shorten them. Any other error is not retried and poisons as today; a write that still fails after the budget writes the barrier.
2. **Record why.** When the barrier is written, the sentinel file holds one JSON line: UTC timestamp, operation (`event_commit`, `flush` or `instrumentation`), exception type and message. It never contains request or response content: the message is kept only for SQLite errors (an instrumentation exception can echo response values), and the sentinel is linked into place from a private temp file so a reader never sees it half-written. The first writer wins: the sentinel is linked into place (an `O_EXCL` create where hard links are unavailable), so a later failure never overwrites the original cause, and an existing sentinel still counts as poisoned (not failed). The server instrumentation path (`server_impl._poisoned_or_fatal_telemetry_failure`) involves no SQLite write, so it is not retried; its callers pass the caught exception, or `metric_not_captured` when the metric reported `captured` false without raising. `read_store_health` returns the recorded reason and time with the `accounting_gap` status; a legacy empty or unparseable sentinel still reports `accounting_gap` with the reason unknown. The `accounting_gap` diagnostic names the clear command.
3. **Clear on purpose.** A documented operator action, `python3 -B .wavefoundry/framework/scripts/context_efficiency.py --root <repo> --clear-gap`, clears the store-wide barrier without hiding the undercount it caused:
   - Waves that saw the gap stay marked. In one `BEGIN IMMEDIATE` transaction on the existing store, every unsealed `wave_state` row, and a new row for every wave folder whose `Status:` is not `closed` (found with `record_paths.discover_wave_dirs`, keyed by folder name as `resolve_open_wave` does; an unreadable `wave.md` counts as not closed), gets `measurement_status='accounting_gap'`, with `pending=1` and `generation` bumped so a checkpoint already published is re-projected. Upserting rows matters because `_commit_event` returns `poisoned` before `_touch_wave` while the gap is in effect, so a wave whose first telemetry fell inside the gap has no row. The per-wave status is read by `_snapshot_from_conn` and is not reset by `_touch_wave`, so these waves still publish `accounting_gap` at close. Only waves created after the clear report healthy totals.
   - The sentinel is renamed aside, then the `meta.accounting_gap` row is deleted, within the same transaction. The sentinel-to-meta copy in `_open_write_store_once` re-checks the sentinel after taking its write lock, so an open that saw the sentinel before the clear cannot copy the flag back after it. A failure that happens after the rename writes a fresh sentinel, and that sentinel survives the clear.
   - The command does not create or migrate a store that is absent, handles a meta-only gap and a sentinel-only gap, and uses the same busy retry.
   - It reports what it found before opening the store for writing (`found.gap_file`, and `found.store_flag` read through a read-only connection, because the write open copies the file into the flag), the recorded reason, the waves it marked, and `new_gap_recorded` when a failure during the clear left a fresh gap; with no gap present it reports that nothing was cleared and changes nothing. Gap-period events are not backfilled.
4. **Documentation.** `docs/specs/mcp-tool-surface.md` and `docs/architecture/data-and-control-flow.md` describe the retry, the recorded reason and the clear action; `CHANGELOG.md` `[Unreleased]` gains a Fixed bullet.

## Scope

**Problem statement:** one transient lock error permanently blanks context-efficiency accounting for every later wave, with no recorded cause and no supported recovery.

**In scope:** retry of busy/locked writes, the reason line in the sentinel and its surfacing, the clear action, docs and changelog.

**Out of scope:** backfilling gap-period waves; changing what is credited; per-wave (rather than store-wide) gaps, which is a larger redesign of the barrier.

## Acceptance Criteria

- [x] AC-1: A write whose `BEGIN IMMEDIATE` meets a lock held by a second connection that is released during the retries is recorded as `durable` and writes no sentinel; one that stays locked past the (test-shortened) budget writes the sentinel; a non-transient error writes it on the first attempt. This holds for both the event commit and the flush transfer.
- [x] AC-2: A written sentinel carries the timestamp, operation, exception type and message and no call content; a second failure does not overwrite it; `read_store_health` returns the reason with the `accounting_gap` status, tolerates a legacy empty sentinel, and its diagnostic names the clear command; the server instrumentation path records the caught exception or `metric_not_captured`.
- [x] AC-3: The clear action removes the sentinel and the `meta` flag and marks every unsealed wave as `accounting_gap`. After it, a new event records as `durable`, a wave first touched after the clear reports healthy totals, a wave open across the gap still reports `accounting_gap`, and so does a non-closed wave that had no telemetry row before the clear. With no gap present it reports that nothing was cleared, and it never creates an absent store.
- [x] AC-4: The change's own tests pass and the edited docs validate.

## Tasks

- [x] Add whole-transaction retry for busy/locked errors on the event commit and flush paths, sharing one budget with the open retry.
- [x] Write the first-writer-wins reason line in `_write_gap_sentinel`, pass reasons from the server instrumentation path, and surface them through `read_store_health`.
- [x] Add the `--clear-gap` command with per-wave marking.
- [x] Tests for AC-1 to AC-3; docs and changelog.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Retry, reason and clear | implementer | readiness | Single write owner |
| Review | code and qa reviewers | implementation | One combined reviewer |

## Serialization Points

- `.wavefoundry/framework/scripts/context_efficiency.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/tests/test_context_efficiency.py`, `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py`, `docs/specs/mcp-tool-surface.md`, `docs/architecture/data-and-control-flow.md`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` (step 9 and the failure semantics of the context-efficiency flow).

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes the observed cause |
| AC-2 | required | The next gap must be diagnosable |
| AC-3 | required | Recovery must not need a hand-edited database |
| AC-4 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-25 | Implemented: `_with_busy_retry` (budget `BUSY_RETRY_BUDGET_SECONDS`) wraps `_commit_event_once`, the flush `_transfer_once` and `_open_write_store`; `_write_gap_sentinel` writes a first-writer JSON reason; `read_store_health` adds `gap_*` fields and a diagnostic naming the clear command; `clear_accounting_gap` and `main()` add `--clear-gap`; the open fast path re-checks the sentinel under its lock; the server instrumentation path passes the caught exception or `metric_not_captured`. 9 new tests plus one updated; five mutants (no retry, no flush retry, no upsert, no mark, no O_EXCL) each fail a test | `tests/test_context_efficiency.py` `GapRecoveryTests`; `tests/test_server_context_efficiency.py` `test_instrumentation_failure_records_its_reason_in_the_gap` |
| 2026-09-26 | Operator follow-up: budget 10 seconds; clear reports `found` (file-only, store-flag-only and both cases tested; a mutant that reports the file as the store flag fails two tests) | `GapRecoveryTests` |
| 2026-09-25 | Full framework suite green after the repairs: 9694 tests across 128 files; focused suites 168 OK; docs validate | `run_tests.py --no-cache` |
| 2026-09-25 | Delivery review (no blocking findings) repairs: a `.clearing` file left by a committed clear no longer marks healthy waves (N1); instrumentation exception text is dropped from the sentinel (N2); the clear reports `new_gap_recorded` (N3); docs say the marking and set-aside share one transaction (N5); flush non-transient test added (N6); the sentinel is linked from a temp file (N7). A mutant that restores the N1 defect fails `test_clear_ignores_a_set_aside_file_left_by_a_committed_clear` | `tests/test_context_efficiency.py` `GapRecoveryTests` |
| 2026-09-25 | Planned after the operator found empty Context Efficiency sections in waves `1yzj9`, `1z1vs` and `1z1vt`. The sentinel (written 15:50:01) and `meta.accounting_gap` were cleared by hand at the operator's request; those three waves keep their gap projection | `.wavefoundry/logs/context-efficiency.gap` (removed) |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-25 | The clear action is a command-line entry on `context_efficiency.py`, not an MCP tool or `wf` subcommand | Smallest surface; the MCP tool roster and the `wf` dispatcher are pinned elsewhere; it runs without MCP | A new MCP tool; a `wf` subcommand |
| 2026-09-25 | Clearing marks every unsealed wave `accounting_gap` rather than refusing while waves are open (readiness finding F4) | Keeps fail-closed per wave with the existing `wave_state.measurement_status` column; the clear is never blocked by an abandoned wave | Refuse while unpublished waves exist, with `--force`; a new per-wave taint table |
| 2026-09-26 | The clear reports what it found (`found.gap_file`, `found.store_flag`) instead of `sentinel_removed`/`meta_flag_removed` | The write open copies the file into the store flag, so the old report always showed the flag as set; a store-flag-only gap (reason lost) was indistinguishable | Keep the removal fields |
| 2026-09-26 | Busy-retry budget raised from about 5 to 10 seconds (operator) | Only busy/locked errors are retried, and those are timing; 10 seconds is ample for a lock to clear | 5 seconds |
| 2026-09-25 | Retry only busy/locked SQLite errors, bounded at about 5 seconds (operator; raised to 10 seconds on 2026-09-26) | Matches the likely cause (a 50 ms lock wait with several MCP servers attached) without weakening fail-closed for real failures | Raise the busy timeout alone (still permanent on the first longer hold); retry every error (could mask real corruption) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Retries block the stdio server, not just one call: FastMCP runs sync tools on the event loop, and one call can commit twice (tool cost, then retrieval or workflow context), so the worst case is about twice the 10-second budget | Accepted by the operator for a rare contention path; the retry runs only on a busy/locked error |
| The general (no-wave) running total undercounts after a clear | Accepted: it is a running total, not a wave checkpoint; the clear output says so |
| The cause was not a lock | The recorded reason makes the next occurrence diagnosable |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
