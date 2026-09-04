# Scope the Secrets Scan to Content Changes on a Graph Rebuild

Change ID: `1x4oj-bug graph-rebuild-forces-full-secrets-scan`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-04
Wave: 1x4ol index-build-cost-and-scanner-bounds

## Rationale

`index_build(content='graph', mode='rebuild')` takes about 203 seconds on this
repository, and 198.5 of them are a secrets scan that the graph rebuild has no
reason to trigger.

The build passes its own `full` flag straight into `_build_secrets_artifacts`.
`full` means "rebuild the graph index from scratch" -- it says nothing about
whether any file's CONTENT changed, which is the only thing secret detection
depends on. The scanner reads that flag as a real full scan, bypasses its
per-file content-hash skip cache, and re-reads every tracked file. The build log
records the reason in its own words: `secrets scan — full (full rebuild)`, then
`secrets scan complete (full) — 0 finding(s), 0 cache-skipped, in 198.5s`.

The graph phase itself is healthy. It finished at 17:29:19 in 46.6 s, inside the
40-60 s band `docs/architecture/performance-budget.md` records for a build after
a builder-version bump. The command did not return until 17:31:47, because the
secrets future was still running. An operator waiting on a graph rebuild is
waiting on the scanner, not on the graph.

The saving is measured rather than projected. Against the warm cache, an
incremental pass over the same 2,368 candidates skips 2,364 and scans 4 -- and
those 4 are exactly the files edited in the session that produced this
measurement.

Nothing about secret coverage weakens. The scanner keeps its own escalations to
a real full scan: a changed rules hash (framework or project), a changed
`SCANNER_VERSION`, or a missing findings ledger. Those are the conditions under
which a previously-scanned file can yield a NEW finding, and each one still
forces the full pass on its own.

Wave `1wpih` did not introduce this; it made it frequent. That wave bumped the
graph builder twice, and every bump forces a full graph rebuild, which drags a
full secrets scan behind it.

## Requirements

1. A build whose `content` is `graph` SHALL NOT pass `full=True` to the secrets
   scanner on the strength of the graph rebuild alone. The scanner's own
   escalation triggers SHALL continue to force a full scan when they fire.
2. The graph rebuild SHALL still submit the secrets scan with its complete
   candidate set, so a file whose content changed is scanned. Correctness comes
   from the per-file content-hash and rules-fingerprint cache, not from
   narrowing the candidate list.
3. A docs or code rebuild SHALL retain its current behaviour. This change scopes
   the graph-only path and nothing else.
4. The build log SHALL continue to state which scan type ran and how many files
   the cache skipped, so the distinction between a skipped scan and a scanned
   file stays readable after the change.
5. `docs/architecture/performance-budget.md` SHALL record the wall-clock cost of
   the graph rebuild COMMAND beside the existing graph-phase rows, because the
   two existing rows measure a phase an operator never waits on alone and that
   gap is what let a 198.5 s tax sit unnoticed against a 52 s budget row.
6. The graph-only path SHALL pass a NON-EMPTY candidate set to the scanner, and
   that property SHALL be pinned by a test. The incremental branch returns early
   on an empty `changed` and `removed` with `up_to_date: True`, emitting no
   "scan complete" line at all, so a later narrowing of the candidate set would
   turn the scan into a silent no-op that still reports success. The full-rebuild
   branch populates the candidate set with every file today, which is what makes
   this change safe; nothing currently states that dependency.

## Scope

**Problem statement:** A graph-only rebuild forces a full secrets re-scan of
every tracked file, which costs about 198.5 seconds and dominates the command.

**In scope:**

- The `full` argument passed to the secrets future in `indexer.py`.
- Tests pinning the graph-only path to an incremental scan and the docs/code
  paths to their current behaviour.
- Tests pinning that each scanner escalation trigger still forces a full scan
  from a graph-only build.
- The performance-budget rows for the graph rebuild.

**Out of scope:**

- The scanner's per-file cost and the regex blowup behind it (`1x4ok`).
- Graph extraction worker sizing and the incremental merge cost.
- Any change to the ruleset, the findings ledger format, or the close-time
  secrets gate.

## Acceptance Criteria

- [x] AC-1: A graph-only rebuild runs the secrets scan on its incremental path
      against a warm cache, reporting a nonzero `cache-skipped` count and a
      `scan_type` of `incremental`, while a docs or code full rebuild still
      reports `full`.
- [x] AC-2: Each scanner escalation still forces a full scan from a graph-only
      build, asserted separately for a changed rules hash, a changed
      `SCANNER_VERSION`, and a missing findings ledger.
- [x] AC-3: A file whose content changed since the last scan is scanned by the
      graph-only path, proven by mutating a file's content and asserting it
      appears in the scanned set rather than the skipped set.
- [x] AC-4: Deleting the scoping change makes a named test fail, recorded as a
      mutation before review.
- [x] AC-5: `docs/architecture/performance-budget.md` carries a command-level
      wall-clock row for the graph rebuild beside the existing phase rows, with
      the before and after figures and the date each was measured.
- [x] AC-6: The graph-only path passes a non-empty candidate set, asserted
      directly, and a scan handed an empty set is shown to return early with
      `up_to_date` and no completion line, so the silent-no-op shape is visible
      in the test rather than only in the source.
- [x] AC-7: This change's own suites and every test it adds pass, the documents
      it authors or edits validate, and no failure elsewhere is attributable to
      it.

## Tasks

- [x] Scope the `full` argument passed to the secrets future to non-graph builds.
- [x] Add the graph-only incremental assertion and the docs/code control.
- [x] Add the three escalation-trigger assertions.
- [x] Add the changed-content assertion so the cache cannot skip a real edit.
- [x] Pin the non-empty candidate set and characterise the empty-set early return.
- [x] Record the mutation that kills the scoping change.
- [x] Measure the graph rebuild command before and after, and update the
      performance budget.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| scope-the-flag | implementer | — | One argument in `indexer.py`. |
| coverage | implementer | scope-the-flag | Escalation and changed-content controls. |
| measure-and-document | implementer | coverage | Budget rows come from a measured pair. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `docs/architecture/performance-budget.md`

## Affected Architecture Docs

`docs/architecture/performance-budget.md` gains a command-level row for the
graph rebuild. No boundary, layering, or data-flow document changes: the scan
still runs, still covers the same files, and still writes the same ledger.

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The behaviour the change exists to deliver. |
| AC-2 | required | Coverage must not weaken; each escalation is a separate way a new finding can appear. |
| AC-3 | required | Guards the one real risk, that the cache skips a file that genuinely changed. |
| AC-4 | required | A guard that survives its own deletion is not landed. |
| AC-5 | important | The missing command-level row is why the cost hid behind a healthy budget. |
| AC-6 | required | Without it the change's safety rests on an undocumented property of a different branch. |
| AC-7 | required | Standard delivery gate. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-04 | Root-caused from a build log rather than inferred. | Graph phase complete at 17:29:19 in 46.6 s; command returned 17:31:47; `secrets scan complete (full) — 0 finding(s), 0 cache-skipped, in 198.5s`. An earlier build's incremental scan took 0.2 s. |
| 2026-09-04 | **Readiness review repaired the plan: the safety of this change rests on an unstated property.** | The incremental branch of `update_secrets_scan` returns early when `changed` and `removed` are both empty, reporting `up_to_date: True` and printing no completion line. This change is safe only because the full-rebuild branch sets the candidate set to every file, which nothing stated. Requirement 6 and AC-6 added so a later narrowing cannot turn the scan into a silent no-op. |
| 2026-09-04 | **Isolated baseline taken BEFORE the edit, on the unmodified engine.** | `fullscan_measure.py`: 2,373 files, 8 workers, no concurrent graph build, 198.81 s. The earlier 198.5 s from the build log was therefore not inflated by contention; the scan is simply that slow, and the pool cannot help because the 173.6 s outlier is one file on one worker. A stdin-fed first attempt lost its spawn pool (`<stdin>` cannot be re-imported by a spawned worker) and fell back to serial; it was discarded and re-run from a file so the figure matches production's parallel path. |
| 2026-09-04 | **Landed: one expression, `_secrets_full = bool(full) and content != "graph"`, forwarded as the scanner's `full`.** | `test_indexer_secrets_scope.py`, 9 tests across two layers. Indexer layer patches `_build_secrets_artifacts` to capture what `build_index` hands it: graph-only full rebuild passes `full=False` with a non-empty candidate set naming every file (AC-1, AC-6); a docs full rebuild still passes `full=True` (control). Scanner layer runs the REAL scanner against a REAL state store with the cache fixture's two-rule ruleset, no mocks: warm cache then `full=False` reports nonzero `files_skipped`, zero `files_scanned`, and `scan_type: incremental` (AC-1); an edited file is scanned while the rest skip (AC-3); a rules edit, a stale `SCANNER_VERSION`, and a deleted findings ledger each still force `scan_type: full` from the incremental call (AC-2); an empty candidate set returns `up_to_date` with no completion line, characterising the silent-no-op shape the indexer pin prevents (AC-6). |
| 2026-09-04 | **After-fix command measurement, same machine, MCP reloaded.** | `index_build(content='graph', mode='rebuild')` at graph builder 49: `rebuilding graph index` 20:52:31, `secrets scan — incremental (1 to scan, 2069 cache-skipped, 0 removed)` complete in 6.4 s at 20:52:38, `graph phase complete` 20:53:19, `Done.` 20:53:23. Command wall clock 52 s against 203 s before; secrets 6.4 s against 198.5 s. The one file scanned was the change document being edited. The graph phase itself (40.2 s incl. a 21.7 s merge) is unchanged, as expected: this change never touched it. Recorded in `docs/architecture/performance-budget.md` as a new command-level row beside the two phase rows that could not show this cost. |
| 2026-09-04 | Landing rule: mutation recorded before review. | Mutant: `_secrets_full = bool(full)` (scoping removed). Fails exactly `test_graph_only_full_rebuild_does_not_request_a_full_scan`; the other eight pass, which is correct because the scanner-layer tests do not depend on the indexer flag. Restored; 9 of 9 pass. |
| 2026-09-04 | Saving measured against the warm cache before planning the fix. | `secret_scan_filter` over the same 2,368 candidates: 2,364 skipped, 4 to scan, and those 4 are exactly the session's edited files. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-04 | Scope the `full` flag rather than skip the scan for graph builds. | The incremental pass costs about 0.2 s and keeps the findings ledger current, so there is nothing to buy by skipping it and a coverage gap to lose. | **Skip secrets entirely on graph-only builds:** leaves the ledger stale for genuinely changed files at no measurable saving. **Exclude the expensive artifacts from the scan set:** narrows coverage over committed files to work around a cost that belongs to `1x4ok`. |


## Risks


| Risk | Mitigation |
| --- | --- |
| The cache skips a file that genuinely changed, so a new secret goes unreported. | AC-3 mutates a file's content and asserts it is scanned, not skipped. The cache keys on content hash plus rules fingerprint, so a content change cannot match a cached row. |
| An escalation stops firing from the graph-only path, silently downgrading a scan that should have been full. | AC-2 asserts all three triggers separately from a graph-only build. |
| A later change narrows the candidate set, and the scan silently becomes a no-op that still reports success. | Requirement 6 and AC-6 pin the non-empty set directly and characterise the early return, so the failure mode is asserted rather than reasoned about. |
| The measured saving does not reproduce on a cold cache. | The first graph rebuild after this change still pays a full scan if the cache is empty; the budget row records both the warm and cold cases. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
