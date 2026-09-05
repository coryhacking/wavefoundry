# Surface Reap Deferral and Preservation Through index_build_status and index_health

Change ID: `1x551-debt index-health-surfaces-reap-deferral-and-preservation`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-05
Wave: 1x6ti reap-state-visibility-and-dangling-edges

## Rationale

Recorded during the delivery review of wave `1x54z` (SEC-DEL-1 and
SEC-RV1-1). Since that wave a build that defers a mass-absent Lance reap or
preserves a walk-shadowed subtree says so in the `build_index` result
(`stranded_reap_deferred`, `stranded_reap_preserved`), on stderr, and in the
index-state log. That result is the Python return value only. The registered
`index_build` tool (`run_index_rebuild`) spawns the build detached and
returns a spawn acknowledgement; `index_build_status_response` composes its
finished summary from the build-state file, the completion line of the build
log and `index-build-stats.json`; `index_health_response` composes its
readout from `docs_health()`, the lock, the same stats file, the graph
summary and `_state_store_health_summary`. `index-build-stats.json` is
server-owned: `_refresh_index_build_stats_from_finished_log` derives it from
the log's "done" line, so nothing the indexer returns reaches either tool.
Under an MCP-driven or hook-driven build an operator cannot see that the
index is knowingly serving rows as of the last readable build, nor that a
deferral has persisted across builds, without opening the logs.

The mechanism this change uses already exists. The index-state store carries
a `meta` key-value table (`IndexStateStore.set_meta` / `get_meta` /
`meta_all`); `set_meta` is a plain upsert with no epoch or compare-and-set,
and the true no-epoch precedents on the zero-change path are the drift clear
(`reconcile_non_git_drift` reaching `clear_attribution_and_drift` before the
`up_to_date` return) and the best-effort failure record
(`_record_drift_failure`, which catches every exception and returns a count).
The FTS digest and heal-marker writers also live in `meta` but run inside an
epoch. A `dry_run=True` build reaches the zero-change preflight without the
build lock and without `ensure_current`; the dry run's no-write contract is
documented, not enforced on that branch (the drift reconcile and the
idle-maintenance epoch are reachable there, parked as plan `1x81w`), so the
writer must skip dry runs itself. The two summaries are computed at
exactly two places in `_build_index_locked`: the zero-change preflight
(`_reap_deferred_summary` / `_reap_preserved_summary`, derived from the
plan-only reap) and the build path (`_reap_deferred_build` /
`_reap_preserved_build`, popped from the executed reap). Persisting them
there and reading them in the two response functions closes the gap with no
new file and no log parsing.

## Requirements

1. At every summary-carrying return of `_build_index_locked` (the
   zero-change `up_to_date` return, the idle-maintenance return, and the
   build-path return) the indexer SHALL persist the deferred and preserved
   summaries in the state store's `meta` table under one fixed key, stamped
   with the store's published generation at the time of the write and a
   timestamp, replacing the record on every non-dry-run build and removing
   it when neither summary applies. On the build path the write lands after
   `finalize_build_epoch` succeeds, so the stamp is the generation that
   published the state it describes; at the zero-change seam a deferral
   opens no epoch, so the stamp is the last completed build's generation. A
   full rebuild defers and preserves nothing, so the full path removes the
   record too (both reap seams sit behind `not full`, and the diagnostic's
   own remedy is the rebuild). The write SHALL be skipped on `dry_run`
   builds, SHALL be epoch-free, and SHALL never fail the build: the writer
   takes `_record_fts_heal_marker`'s shape (open the store, `set_meta`,
   close, no `ensure_current`, which could reset a version-mismatched store)
   with `_record_drift_failure`'s posture (every exception caught, a store
   log line, the build result still carrying the summaries); a locked store
   stalls the seam for at most the store open timeout before the wrapper
   sees the error.
2. `index_build_status` SHALL carry a `reap` block (`deferred`, `preserved`,
   `recorded_generation`, `recorded_at`) in every response state (finished,
   idle, running beside `previous_stats`, and interrupted) whenever a record
   exists, read from the store and never from the log, and SHALL omit the
   block when no record exists.
3. `index_health` SHALL carry the same `reap` block and SHALL raise
   `stranded_reap_deferred` while the record's `deferred` map is non-empty
   (the tables with `would_reap` and `table_paths`, mirroring the indexer's
   message: the rows stay searchable until newly indexed files dilute the
   fraction under the breaker, and if the paths really are gone rebuild once
   every directory and volume is readable again, `recovery_usage`
   `index_build(content='all', mode='rebuild')`) and `stranded_reap_preserved`
   while its `preserved` map is non-empty (the tables and counts; the subtree
   is served as of the last readable build and the first readable build
   reconciles it, `recovery_usage` `index_build(content='all', mode='update')`).
   Both carry `recovery_tools` `index_build` and `index_build_status` and
   neither sets the `advisory` flag, matching the neighbouring health
   diagnostics (the word advisory in this plan means non-blocking prose, not
   the flag). A store without a record SHALL raise neither.
4. The record SHALL be readable through one read-only helper in the state
   store module, shared by both response functions, so the two surfaces
   cannot disagree.
5. Tests SHALL pin the indexer side in `EligibilityReapAbsenceGuardTests`
   (a deferred zero-change build writes the record stamped with the
   pre-build generation; a walk-shadowed build-path run writes the preserved
   counts stamped with the published generation; the next clean build and a
   full rebuild each remove it; a dry run leaves the meta untouched; a
   write failure injected by patching
   `self.bi._get_index_state_store().IndexStateStore.set_meta` to raise,
   because the indexer holds its own store module object, leaves the build
   result intact and writes the store log line) and the server side through
   `index_build_status_response` and `index_health_response` with a seeded
   store in every status state (the block and the diagnostics appear, then
   clear), and each guard SHALL fail a named behavioural test when deleted,
   recorded as mutations before review.

## Scope

**Problem statement:** the deferred and preserved states of the eligibility
reap are visible only in the Python build result and the logs; the registered
tool surface an agent or operator uses shows neither.

**In scope:**

- Epoch-free persistence of the two summaries in the state store's `meta`
  table at both reap seams, with a read-only helper beside the store's other
  meta readers.
- The `reap` block in `index_build_status_response` (finished, idle, running
  and interrupted) and `index_health_response`, plus the two advisory
  diagnostics in health.
- Tests on both sides; `docs/specs/mcp-tool-surface.md` and item 15 of
  `docs/architecture/data-and-control-flow.md`.

**Out of scope:**

- The reap's classification and breaker policy (wave `1x54z`).
- Relaying the whole `build_index` result through `index_build`; the tool is
  a detached spawn by design.
- The explicit `files=` build seam never walks but does run the build-path
  reap over its one-file eligible set, so the build-path writer runs there
  too and records what that reap decided; the seam's deletion of every
  unlisted row is pre-existing, unreachable from any registered tool, and
  parked as plan `1x81v`.
- The dashboard's stats merge (`dashboard_lib`), which reads the stats file
  and can adopt the store record in its own change.

## Acceptance Criteria

- [x] AC-1: After a zero-change build whose reap deferred, the store's meta holds the deferral summary stamped with the store's published generation and a timestamp; after the next build where nothing is deferred or preserved, and after a full rebuild, the record is gone; a `dry_run` build leaves the meta untouched.
- [x] AC-2: After a walk-shadowed build-path run, the store's meta holds the preserved per-table counts; after recovery, the record is gone.
- [x] AC-3: `index_build_status_response` carries the `reap` block in its finished, idle, running and interrupted responses when a record exists and omits it when none exists.
- [x] AC-4: `index_health_response` carries the `reap` block and raises `stranded_reap_deferred` while the deferred map is non-empty and `stranded_reap_preserved` while the preserved map is non-empty (a one-sided record raises one), with the remedy text and recovery tools, and neither block nor diagnostic when no record exists.
- [x] AC-5: A store write failure at the persistence seam does not fail the build: the result still carries both summaries and the store log records the failure.
- [x] AC-6: Each guard (the write at each seam, the clear, the shared reader, each tool's block, each diagnostic) fails a named test when deleted, recorded as mutations before review.
- [x] AC-7: `docs/specs/mcp-tool-surface.md` (the tool table rows and the `index_health` block), the two registered tool docstrings in `server_impl.py`, and item 15 describe the `reap` block and the two diagnostics, and the CHANGELOG carries the addition under Unreleased.
- [x] AC-8: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the meta keys and the read-only reader (`reap_state_for_index`) beside the store's other meta readers; add the writer helper in the indexer, guarded by `not dry_run`, and call it at both seams (write or clear).
- [x] Red first: a failing test that a deferred zero-change build leaves a record, before the writer exists.
- [x] Add the `reap` block in the `index_build_status_response` wrapper (which already attaches `lock` and `epoch` on every return path and is the only place `interrupted` is minted) and in `index_health_response` with the two diagnostics.
- [x] Tests: indexer side (write with the stamp, preserve, clear on a clean build and on a full rebuild, dry-run untouched, write-failure tolerance) and server side (appear-then-clear through the response functions in every status state, `interrupted` seeded through `begin_build_epoch` with the lock reported unheld).
- [x] Mutations in scratch copies, each killed by a named test; record the table.
- [x] Docs: `mcp-tool-surface.md` (table rows and the `index_health` block), the two registered tool docstrings in `server_impl.py`, item 15, CHANGELOG (an addition under Unreleased).

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                                  |
| ---------- | ----------- | ---------- | ------------------------------------------------------ |
| persist    | implementer | —          | Both reap seams; epoch-free meta write; never fails.   |
| surface    | implementer | persist    | Two response functions, one shared reader.             |
| pin        | implementer | surface    | Appear-then-clear on both sides; mutations.            |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/index_state_store.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/data-and-control-flow.md`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` item 15 (the follow-on sentence
becomes the shipped behaviour: the record lives in the store's meta table and
both tools read it) and `docs/specs/mcp-tool-surface.md` for the two tool
responses. No layering change: the indexer already writes the store's meta
outside the epoch, and the server already reads the store read-only.

## AC Priority


| AC   | Priority  | Rationale                                                        |
| ---- | --------- | ---------------------------------------------------------------- |
| AC-1 | required  | The deferral is the state an operator must act on.               |
| AC-2 | required  | The preservation is the state an operator must know is served.   |
| AC-3 | required  | The status surface is where a build's outcome is read.           |
| AC-4 | required  | The health surface is where a persisting condition is read.      |
| AC-5 | required  | A visibility aid must never turn a preserved build into a failed one. |
| AC-6 | required  | A guard that survives its own deletion is not landed.            |
| AC-7 | important | The tool contract is documented where agents read it.            |
| AC-8 | required  | Standard delivery gate.                                          |


## Progress Log


| Date       | Update                                                                                                   | Evidence                                            |
| ---------- | -------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| 2026-09-04 | Filed from the `1x54z` delivery review (SEC-DEL-1 second half; SEC-RV1-1 confirmed no registered tool relays the result). | Wave `1x54z` events ledger, findings SEC-DEL-1 and SEC-RV1-1. |
| 2026-09-05 | Delivery review cycle 2 reverification: the QA lane verified the strict reader by execution and killed four reader mutants with the malformed-value test; note recorded without repair: QA-RV2-2 (`recorded_generation` and `recorded_at` are display-only and still coerced, while the only writer emits an int and a float). | QA lane report in the session scratchpad (`rv2_qa_1x6ti`); full suite 8,462 OK on the cycle-2 tree. |
| 2026-09-05 | Delivery review cycle 2. QA-RV1-3 (QA reverification lane): the reader's coercion was looser than stated (deferred bools served as 1 and 0, JSON floats truncated, a missing `table_paths` defaulting under a surviving mutant); `reap_state_for_index` now accepts a value only through `_is_count` (an int, not a bool, non-negative; no coercion, no default), and the malformed-value test covers bools, floats, a float string, a missing key and a zero count. DOCS-RV1-1: the Decision Log's misplaced fifth cell moved back to row 1's Alternatives (4 cells per row). Mutations (scratch, `mut_r2/`): missing key defaulted, bools accepted, floats coerced; each killed by `test_malformed_per_table_entries_are_dropped_by_the_reader`. | `ReapStateSurfaceTests` 6 OK; mutant trees under `mut_r2/` in the session scratchpad, killing test named in this row. |
| 2026-09-05 | Delivery review cycle 1. QA-DEL-3 (QA lane): the reader validated only the outer shape, so a hand-edited or future-schema value with odd per-table entries was served verbatim; `reap_state_for_index` now coerces each entry (a deferred entry must be a dict of two non-negative integers, a preserved entry a non-negative integer count; anything else is dropped, and a record with no well-formed entry reads as none), pinned by `test_malformed_per_table_entries_are_dropped_by_the_reader`. DOCS-DEL-3: the Scope bullet names all four status states. DOCS-DEL-5: the parked plan is named (`1x81v`). ARCH-DEL-1: the Risks row names the three production-identity modules and the gate's trigger. The Decision Log header rows were narrowed for the coordinate census (see the `1x5pc` row and plan `1x81x`). QA-DEL-1 and QA-DEL-2 recorded as equivalent mutants (the source-side check is unreachable on real inputs; widening the exemption to known paths is equivalent by construction). CODE-DEL-2 (a second write-open of the store on every zero-change build) accepted as designed. | Repaired tree: `ReapStateSurfaceTests` 6 OK. |
| 2026-09-05 | Mutations before review (scratch copies, `mut_1x551/run.py`), each a clean removal, all killed by named tests: A zero-change write removed (6 tests, led by `test_deferred_zero_change_build_records_the_reap_state`); B build-path write removed (`test_shadowed_build_path_run_records_preserved_counts_stamped_with_the_published_generation`, `test_full_rebuild_clears_the_reap_state_record`); C idle-maintenance write removed (first SURVIVED, because no test reached the idle return with a deferral; `test_deferred_idle_maintenance_pass_records_the_reap_state_after_its_finalize` added, dirtying the epoch through `begin_build_epoch` so the zero-change build takes the idle path, then killed); D clear removed (first SURVIVED, because the reader hides an empty record; the three clear tests now also assert the raw meta key is absent through `IndexStateStore.get_meta`, then killed by `test_reap_state_record_clears_on_the_next_clean_build`, `test_full_rebuild_clears_the_reap_state_record` and the shadowed recovery); E dry-run guard removed (`test_dry_run_leaves_the_reap_state_record_untouched`); F exception re-raised (`test_reap_state_write_failure_never_fails_the_build`); G generation stamp zeroed (the two stamp tests); H shared reader returns None (4 of 5 server tests); I status block removed (`test_status_carries_the_reap_block_in_every_state_and_omits_it_without_a_record`, `test_status_and_health_read_the_same_record`); J health block removed (2 tests); K deferred diagnostic removed, L preserved diagnostic removed, M diagnostics not attached (`test_health_carries_the_block_and_one_diagnostic_per_non_empty_map`, `test_health_one_sided_record_raises_one_diagnostic` each). Two survivors surfaced two test gaps, both closed before review. | Mutation table: 13 mutants, 13 killed after the two test repairs; all named tests pass on the unmutated tree (`EligibilityReapAbsenceGuardTests` 28, `ReapStateSurfaceTests` 5). |
| 2026-09-05 | Implemented. Red first: `test_deferred_zero_change_build_records_the_reap_state` (in `EligibilityReapAbsenceGuardTests`) failed on the unrepaired tree because no reader or record existed. Store: `META_REAP_STATE` (`reap_state`, one JSON value), `IndexStateStore.delete_meta`, `write_reap_state` (heal-marker shape: open, write or delete, close, no `ensure_current`; stamps `read_build_state` generation and `time.time()`), and the shared reader `reap_state_for_index` (read-only connection, `None` for absent, malformed or empty records). Indexer: `_record_reap_state` (skips `dry_run`, catches every exception, logs through `_store_log_safe`) called at the three summary-carrying returns: the zero-change `up_to_date` return, the idle-maintenance return after its finalize, and the build path after `finalize_build_epoch` (the full path therefore clears). Server: `_reap_state_block` (one reader) and `_reap_state_diagnostics`; the block attaches in the `index_build_status_response` wrapper on every state and in `index_health_response` beside `state_store` with the two diagnostics (no advisory flag). Six indexer tests and five server tests (`ReapStateSurfaceTests`); the server tests were authored before the implementation but their first run came after it, so their discriminating power rests on the mutation table below. | `EligibilityReapAbsenceGuardTests` 27 tests + `ReapStateSurfaceTests` 5 tests: 32 OK. |
| 2026-09-05 | Prepare lane repairs on admission (code CODE-PREP-1, 2; architecture ARCH-PREP-1, 3, 4; QA QA-PREP-1, 3, 4): the writer runs at all three summary-carrying returns and the build-path write lands after the epoch finalize; a full rebuild removes the record (both reap seams sit behind `not full`, executed by the QA lane: a meta key survived a full rebuild); the `reap` block attaches in the `index_build_status_response` wrapper; the write-failure injection names its patch target (the indexer holds its own store module object); the council decisions recorded in the Decision Log with alternatives and the superseded precedent claim marked; the dry-run contract described as documented, not enforced, and its pre-existing hole parked as plan `1x81w`. | Lane reports in the session scratchpad (`prep_qa/probe_meta_identity.py`, `prep_code/probe_baseline.py`). |
| 2026-09-04 | Prepare council repairs on admission (red-team RED-PREP-3, 4, 5; docs-contract DOCS-PREP-5, 6, 7, 8, 9): the writer skips `dry_run` builds, which reach the zero-change preflight without the lock; the generation stamp is the store's published generation at the write; the no-epoch precedents corrected to the drift clear and `_record_drift_failure`; the `files=` seam sentence corrected (it runs the build-path reap; its unlisted-row deletion parked separately); the status block covers running and interrupted; the diagnostics fire per non-empty map, mirror the indexer's two-half message and match the neighbours' flag; the tool docstrings and spec rows added to the docs task. | Council seat reports in the session scratchpad (`prep_redteam/probe_b_meta.py`, `probe_b2_files_seam.py`). |
| 2026-09-04 | Plan feature: mechanism grounded in the tree. The two summaries are computed at the zero-change preflight and the build path in `_build_index_locked`; the store's `meta` table is a plain upsert (the precedent claim first written here, that the FTS digest and heal-marker writers are epoch-free, was corrected by RED-PREP-4: the no-epoch precedents are the drift clear and `_record_drift_failure`); `index-build-stats.json` is server-derived from the log's done line, so the tools cannot see the build result today; `index_build_status_response_inner` and `index_health_response` are the two read sites. Divergent pre-plan recorded in the Decision Log. | `code_keyword` and `code_read` over `indexer.py`, `index_state_store.py`, `server_impl.py`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-04 | Persist the two summaries in the state store's `meta` table at both reap seams and read them in the two response functions through one shared reader (divergent pre-plan, selected). | The store already offers an epoch-free key-value surface that the indexer writes and the server reads today; no new file, no log parsing, one reader so the two tools cannot disagree. Its weakness, that a record can outlive the condition it describes (the seam that wrote it is not the seam that resolves it), is bounded by writing at every summary-carrying return including the full-rebuild path and by stamping the generation and timestamp. | **Parse the indexer's stderr lines from the build log into `index-build-stats.json`:** log parsing is fragile, the zero-change seam's lines can be rotated away, and the stats file is rewritten from the done line only. **A sidecar JSON file written by the indexer:** a third state file with its own atomicity and cleanup rules where the store already provides the surface. |
| 2026-09-04 | The writer skips `dry_run` builds; the stamp is the store's published generation at the write (after the epoch finalize on the build path); the no-epoch precedents are the drift clear and `_record_drift_failure` (readiness council RED-PREP-3, RED-PREP-4, DOCS-PREP-7; lanes ARCH-PREP-3, CODE-PREP-1). | A dry run reaches the preflight unlocked and by contract must not write; a record stamped mid-epoch would read one behind the generation that published the state it describes, so a stale record could not be told from a fresh one; the FTS digest and heal-marker writers run inside an epoch and cannot serve as the precedent. | **Write under dry run behind a flag:** violates the documented contract for no benefit. **Stamp the in-flight epoch's generation before finalize:** a failed finalize would leave a record claiming a generation that never published. |


## Risks


| Risk                                                                                                     | Mitigation                                                                                                              |
| -------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| A persisted record outlives the condition after a manual rebuild or a walk-free `files=` build.         | Every walk build replaces or removes it; the record carries the recording generation so a stale one is identifiable.   |
| A store write at the zero-change seam fails the build that used to return `up_to_date`.                 | The write never raises into the build; failures go to the store log and AC-5 pins it; a locked store stalls for at most the open timeout. |
| A `dry_run` build reaches the preflight without the lock and writes the record unlocked.                | The writer is guarded by `not dry_run`; AC-1 pins that a dry run leaves the meta untouched.                             |
| `index_state_store.py`, `indexer.py` and `server_impl.py` are `PRODUCTION_RETRIEVAL_MODULES` members, so a same-generation retrieval-eval comparison across this change reads as a production change. | Expected and disclosed; the gate's trigger is a change to ranking, question classification, chunking relevance, hybrid candidate selection or result demotion, none of which this change makes, so no receipt is owed by this wave. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
