# Spool Failed Context-Efficiency Writes Instead of Opening a Gap

Change ID: `1z2m9-enh context-efficiency-failed-write-spool`
Change Status: `review`
Owner: Engineering
Status: active
Last verified: 2026-09-26
Wave: 1z2ma context-efficiency-spool

## Rationale

Today a context-efficiency event whose write fails (after the busy retry added in wave `1z2m4`) writes the store-wide accounting gap at once, and every later wave shows `accounting_gap` until an operator runs `wf clear-accounting-gap`. A failed write is usually transient. The operator asked to keep the event and keep trying rather than give up on the first failure.

Holding the event only in process memory would lose it on a hard kill (host closed, MCP reload, machine sleep) and leave totals that look complete but are not, which is what the gap exists to prevent. A spool of small per-event files survives a crash, and event-ID deduplication already makes a replay exact.

## Requirements

1. **Spool one file per failed event.** When `_commit_event` fails for a reason other than the store-wide gap already being set, the event is written to `.wavefoundry/logs/context-efficiency-spool/<utc-timestamp>-<event_id>.json` (temp file, then an exclusive link or create, the pattern `_write_gap_sentinel` uses) and the call reports `persistence: "spooled"`, which is not fatal. The file holds only what a commit needs: event id, producer id and reclaimable flag, focus, the failure-time open wave and stage when the focus has no wave, tool name, event kind, the four token fields, and `_source_credits` restricted to `source_id`, `version_id`, `tokens` and `credit_kind`. It never holds exception text or call content. The gap is written only when the spool file cannot be written, or the spool already holds its cap of files (Requirement 5).
2. **Replay.** `replay_spool(root)` lists spool files oldest first and commits each with a single attempt through `_commit_event_once` (no busy retry, never spooling or poisoning itself), passing the recorded failure-time open wave into `resolve_attribution` so attribution does not drift. A file is removed after a `durable` or `duplicate` result and kept otherwise (including `poisoned` while a gap is set, so it replays after a clear). Replay runs from the existing context-efficiency projection monitor tick (covering startup and periodic retry without blocking `ImplHandler` construction or a tool call) and at the top of the close path. Concurrent replayers need no lock: event-id deduplication makes a double commit a `duplicate`. A file that cannot be parsed (not expected, since files are published atomically) is renamed aside and writes the gap with a reason naming it.
3. **Close never publishes an undercount as healthy.** The close path replays the spool at the top of `_flush_context_efficiency`, before `flush(transfer_general_to=...)` adopts general-bucket rows. If any spool file then remains whose recorded wave is the closing wave, or whose event has no wave (it would have landed in the general bucket that the close adopts), the closing wave's `measurement_status` becomes `accounting_gap` before the snapshot is sealed. A later replay into an already sealed wave follows the existing live rule (`sealed_redirect` to the general bucket); it cannot occur for an event the close saw, because such an event already marked the wave.
4. **Visibility without changing health status.** `read_store_health` keeps its status (`healthy` stays `healthy`) and adds `spooled_events` and `oldest_spooled_at`, so `pending_wave_ids`, automatic projection and `wf_upgrade` are unaffected by a waiting spool.
5. **Bounded.** The spool holds at most `SPOOL_MAX_EVENTS` files (module constant, patchable in tests). Past the cap the failing event writes the gap as today, with the reason naming the full spool.
6. **Documentation.** `docs/specs/mcp-tool-surface.md` (both `persistence` value lists and the health fields), `docs/architecture/data-and-control-flow.md` step 9, `docs/references/context-efficiency.md` (gap and poison lifecycle), the `clear_accounting_gap` docstring and CLI note (a spooled event can replay after a clear), and a `CHANGELOG.md` `[Unreleased]` bullet.

## Scope

**Problem statement:** one failed telemetry write blanks accounting for every later wave, although the event could simply be written later.

**In scope:**

- per-event spooling and replay of failed event commits (retrieval, tool-cost and workflow events share `_commit_event`), the close rule, health fields, the cap, tests and docs.

**Out of scope:**

- instrumentation failures that never produce an event (metric construction raising): nothing exists to spool, so they still write the gap;
- the general-row transfer in `ProcessTelemetry.flush`: its rows stay in the general bucket and are not lost, so it keeps today's behaviour;
- rewriting a closed `wave.md` after close.

## Acceptance Criteria

- [x] AC-1: an event whose commit fails with a non-busy error is written as one spool file, reported `spooled`, and writes no gap; a replay commits it, removes the file, and the wave's totals include it exactly once.
- [x] AC-2: replay from the projection-monitor entry point (a fresh process standing in for a restart) commits a spooled event with its recorded focus-less attribution even when the open wave has since changed; two concurrent replays of the same file yield one `durable` commit and no double count.
- [x] AC-3: closing a wave replays the spool before the general-bucket transfer; a spool file for the closing wave, or a wave-less file, that cannot be replayed marks the closing wave `accounting_gap` in the sealed checkpoint.
- [x] AC-4: with spool files waiting, `read_store_health` stays `healthy` and reports `spooled_events` and `oldest_spooled_at`, and `pending_wave_ids` stays `ok`; a full spool, an unwritable spool, and an unparseable spool file each write the gap with a reason naming it.
- [x] AC-5: The change's own tests pass and the documents this change edits validate.

## Tasks

- [x] Spool writer (per-event files, whitelist, cap); `_commit_event` spools instead of poisoning.
- [x] `replay_spool` (single attempt, no spool or poison), wired into the projection monitor tick and the top of `_flush_context_efficiency`.
- [x] Close rule for remaining files; health fields.
- [x] Tests for AC-1 to AC-4; docs, clear docstring and changelog.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Spool and replay | implementer | readiness | Single write owner; reads through the MCP code tools |
| Review | combined reviewer | Spool and replay | One combined reviewer |

## Serialization Points

- `.wavefoundry/framework/scripts/context_efficiency.py`, `.wavefoundry/framework/scripts/wf_server/context_efficiency_handlers.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/tests/test_context_efficiency.py`, `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py`, `docs/specs/mcp-tool-surface.md`, `docs/architecture/data-and-control-flow.md`, `docs/references/context-efficiency.md`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` step 9 (failure semantics of the context-efficiency flow).

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The requested behaviour |
| AC-2 | required | A crash must not lose a spooled event or misattribute it |
| AC-3 | required | Fail-closed: a closed wave must never show an undercount as healthy |
| AC-4 | required | A stuck or full spool must be visible and bounded |
| AC-5 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-26 | Delivery review approved (no blocking findings). Repairs: the spec lists every gap operation and reason (N2); an unwritable spool records `spool_unwritable` instead of the commit error (N3), pinned by a test. Full suite green: 9726 tests across 129 files | `run_tests.py --no-cache` |
| 2026-09-26 | Implemented with every code read through the MCP tools (`code_read`, `code_keyword`, `code_references`, `code_outline`); edits applied by script. `_spool_event`, `replay_spool`, `spooled_events_affecting`, `mark_wave_accounting_gap`, spool health fields; `_commit_event_once(open_wave=...)`; replay at the monitor tick and the top of `_flush_context_efficiency`; close marks the wave. Three existing poison tests updated to the new contract (a failure spools; a full spool poisons). 12 new tests; six mutants (never spool, drop failure-time open wave, no close replay, no close mark, no monitor replay, no health fields) each fail | `SpoolTests`, `SpoolAtCloseTests` |
| 2026-09-26 | Readiness: first review found five blocking design flaws in a shared JSONL spool (B1 to B5); the plan was rewritten around per-event files and re-reviewed with no blocking findings. Implementation notes adopted: colon-free timestamps and a skipped `.tmp` suffix; tolerate `FileNotFoundError`/`PermissionError` on a raced unlink; replay before the monitor's `authority_unavailable` return; upsert `wave_state` when marking and only on the sealing boundary; health fields on the gap and absent-store paths too | Readiness review |
| 2026-09-26 | Planned at the operator's request after wave `1z2m8`, before the 1.27.0 release. Code facts checked with the MCP tools: both record paths call `_commit_event`; the server treats only `failed` as fatal; `_project_context_efficiency_wave` seals at close | `code_read`, `code_references` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-26 | One file per event, replayed without a lock, status kept `healthy` (readiness findings B1 to B5) | Per-event files avoid append/truncate races and Windows sharing violations; event-id dedupe makes concurrent replay harmless; a non-healthy status would stop publication and block upgrade | One shared JSONL spool under a lock |
| 2026-09-26 | A late replay into a sealed wave follows the live general-bucket rule | The close replays first and marks the wave for any event it could not replay, so a sealed wave never silently lacks an event the close saw; rewriting a closed `wave.md` is avoided | Re-open the closed checkpoint at the next hard boundary |
| 2026-09-26 | Spool to a file, not process memory | A memory-only queue is lost on a hard kill, leaving an undercount that looks complete | In-memory queue with a gap on clean exit |
| 2026-09-26 | Keep instrumentation failures and the flush transfer out of the spool | The first has no event to keep; the second loses no rows | Spool everything |

## Risks

| Risk | Mitigation |
| --- | --- |
| A replay attributes an event differently from the original | The spool line records the focus and the failure-time open wave; replay uses them |
| A permanently broken store grows the spool | The cap turns a full spool into today's gap, with the reason stated |
| Replay adds latency to tool calls | Replay runs from the monitor thread and the close path, never inside a tool call |
| A replay lands after a phase filled its source-credit cap, or reuses a re-minted phase id after compaction and reopen | Accepted edge cases: event totals stay exact; only which credits a full phase keeps can differ |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
