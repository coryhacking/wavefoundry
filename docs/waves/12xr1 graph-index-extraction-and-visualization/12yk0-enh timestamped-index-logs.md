# Timestamped Index Logs

Change ID: `12yk0-enh timestamped-index-logs`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-28
Wave: `12xr1 graph-index-extraction-and-visualization`

## Rationale

Index and dashboard logs under `.wavefoundry/logs/` are difficult to read during long rebuilds because many entries do not carry an absolute timestamp. Operators can see that work happened, but not when it happened or how long gaps between phases were.

Incremental semantic indexing is also opaque at the file level. The indexer reports aggregate added/updated/removed counts, but not which changed file wrote, removed, or reused how many semantic chunks. That makes it hard to verify that chunk-delta embedding is reducing work on large files.

## Requirements

1. Log lines emitted to `.wavefoundry/logs/` by index build paths must include a date-time stamp.
2. The indexer must emit a semantic file-level log entry for each indexed file during incremental writes.
3. Each per-file semantic log entry must report the file path, table/kind, chunks written, chunks removed, and chunks not changed/reused.
4. Existing progress parsing must continue to recognize terminal build markers such as `done — N files indexed, N doc chunks, N code chunks` and `index is up to date`.
5. The implementation should use the existing `.wavefoundry/logs/` directory; `.wavefoundry/log/` is not a current repository path.

## Scope

**Problem statement:** Long-running index logs lack timestamps and incremental semantic updates lack per-file chunk accounting.

**In scope:**

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/dashboard_server.py` only if it owns index-build log redirection
- `.wavefoundry/framework/scripts/server_impl.py` only if log parsing or build-status display must tolerate timestamp prefixes
- Focused tests for timestamped log output and semantic per-file chunk accounting

**Out of scope:**

- Reworking dashboard UI presentation of logs
- Changing the semantic search schema
- Renaming `.wavefoundry/logs/` to `.wavefoundry/log/`
- Adding persistent structured metrics beyond the existing log files

## Acceptance Criteria

- [x] AC-1: Index build log lines written under `.wavefoundry/logs/` include an absolute date-time prefix.
- [x] AC-2: Terminal build-status parsing still recognizes completed and up-to-date logs after timestamp prefixes are added.
- [x] AC-3: Incremental semantic indexing logs one entry per stale indexed file per semantic table with written, removed, and unchanged chunk counts.
- [x] AC-4: The per-file log distinguishes docs and code table updates for paths that produce both kinds of chunks.
- [x] AC-5: Existing console behavior remains readable and existing full rebuild behavior remains intact.
- [x] AC-6: Tests cover timestamp prefixing and per-file chunk accounting.

## Tasks

- [x] Remove noisy intermediate log lines from the incremental write path (`embedding N changed`, `embedded N in Xs`, `reused N chunk vector(s)`).
- [x] Add elapsed time to `finished docs` and `finished code` summary lines.
- [x] Remove "This may take several minutes to complete." from incremental update logs (kept for full rebuilds).
- [x] Add a shared timestamping path for index-build log lines: `indexer.py` always enables `_TimestampedWriter` unconditionally in `main()`; no env-var gate needed.
- [x] Fix alternating 93-added/93-removed cycling bug: compute `current_file_meta` from broad pre-filter walk so `meta.json` is consistent across docs and code runs with different include-prefix scopes.
- [x] Switch `_run_indexer` from `capture_output=True` to real-time `subprocess.Popen` streaming so each line is stamped when emitted, not when the process exits.
- [x] Write streamed child lines to raw underlying stdout in `_run_indexer` to prevent double-stamping.
- [x] Emit per-file semantic chunk accounting logs during incremental updates (`build_index: semantic file update path=… table=… written=… removed=… unchanged=…`).
- [x] Run framework tests and docs validation. All 1713 tests pass.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| logging contract | implementer | — | Define timestamp format and parsing compatibility |
| semantic accounting | implementer | logging contract | Track written/removed/unchanged per file/table |
| tests | qa-reviewer | implementation | Verify logs without making tests timing-fragile |


## Serialization Points

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- Index build log parsing and dashboard progress display

## Affected Architecture Docs

Update `docs/architecture/chunking-and-indexing-pipeline.md` or `docs/architecture/cross-cutting-concerns.md` if the log contract changes materially. Otherwise N/A because this is a small observability improvement to existing index-build logs.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Timestamped logs are the core operator request |
| AC-2 | required | Build status must not regress |
| AC-3 | required | Per-file chunk accounting is the core semantic-index observability request |
| AC-4 | important | Mixed docs/code paths are a known indexer shape |
| AC-5 | required | Existing progress output and full rebuild behavior must remain usable |
| AC-6 | required | Log formatting and accounting are easy to regress without tests |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-28 | Planned timestamped index logs and per-file semantic chunk accounting. | Operator request |
| 2026-05-28 | Removed noisy embedding/reused intermediate lines from incremental write path; added elapsed time to `finished docs` and `finished code` summary lines. All 1713 framework tests pass. | `indexer.py` `_embed_chunks_for_incremental`, `_plan_lance_delta_rows`, concurrent worker closures |
| 2026-05-28 | Removed "This may take several minutes" from incremental logs. Fixed alternating 93-added/93-removed cycling bug (docs/code runs had different file-scope filters, each overwriting shared `meta.json`). Fixed timestamps: `indexer.py` now always enables `_TimestampedWriter` unconditionally; `_run_indexer` switched to real-time `Popen` streaming writing to raw stdout to avoid double-stamping. All 1713 tests pass. | `indexer.py` `build_index` `files_for_meta` split, `main()` unconditional timestamping; `setup_index.py` `_run_indexer` Popen streaming |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-28 | Use `.wavefoundry/logs/`, the existing canonical log directory. | All current scripts and tests reference `.wavefoundry/logs/`; adding `.wavefoundry/log/` would create split observability. | Rename to `.wavefoundry/log/` — rejected as unrelated migration |
| 2026-05-28 | Keep terminal markers parseable after timestamping. | Dashboard and MCP build-status code parse text logs for completion state. | Store separate structured status only — out of scope |
| 2026-05-28 | Always enable `_TimestampedWriter` in `indexer.py` unconditionally (no env-var gate). | Timestamps belong at the print site, not in a parent wrapper that stamps all lines at flush time. Env var was only needed to prevent double-stamping; bypassing the parent wrapper in `_run_indexer` solves that instead. | Pass `TIMESTAMP_LOGS_ENV` through to child — rejected; simpler to always stamp in the worker |
| 2026-05-28 | Compute `current_file_meta` from broad pre-filter walk (`files_for_meta`) rather than the content-type-filtered walk. | Docs and code runs use different include-prefix filters; each was overwriting `meta.json` with a different file set, causing files to cycle between added and removed on every alternating run. | Separate per-content-type meta files — rejected; broader meta solves the problem without file proliferation |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Timestamp prefixes break existing build-status parsing | Preserve terminal marker substrings and add tests around parser behavior |
| Per-file logging is too noisy on full rebuilds | Scope detailed accounting to incremental semantic updates where unchanged/removed counts matter |
| Chunk counts disagree with table writes | Compute counts from the same delta plan used to delete/add LanceDB rows |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
