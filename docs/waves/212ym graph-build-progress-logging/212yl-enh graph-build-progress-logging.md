# Graph build progress lines in the index build log

Change ID: `212yl-enh graph-build-progress-logging`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-19
Wave: `212ym graph-build-progress-logging`

## Rationale

An operator watching a graph rebuild cannot tell whether it is working or stuck. Detached index builds always run with `--verbose` and write to `.wavefoundry/logs/project-index-build.log`, and `index_build_status` reports the last log line as `progress`. During graph extraction, though, most of the work prints nothing:

- the only per-file counter (every 250 files) is a `[parallel-debug]` line carrying a thread list, and only the parallel paths print it; the serial path (fewer than `_PARALLEL_EXTRACTION_THRESHOLD` code files, or the fallback after a parallel failure) and the serial document loop print nothing;
- `GraphIndexSession.finalize` (merge, document rescans, cross-file resolution, edge assembly) prints nothing until resolution ends.

In this repository's last full build (2026-10-19), the log was silent for 5 minutes 26 seconds, from `[parallel-debug] pool drained: 554 task results consumed` at 00:06:48 to `graph cross-file resolution ran for 276061 edges` at 00:12:14. Throughout that window `index_build_status` kept reporting the "pool drained" line as progress. Which finalize phase used the time was never measured; the new lines will show it.

## Product Intent

An operator or agent polling a graph build (`index_build_status`, or the log file) sees which extraction or finalize phase is running and how far through it the build is, instead of a line minutes old. Boundaries: lines are printed only in verbose mode, the counts are plain text in the existing log, and `index_build_status` and the build itself are unchanged. AC-4 tests whether the intent was met on a real rebuild.

## Requirements

1. In verbose mode, code-file extraction prints a plain progress line every `_GRAPH_PROGRESS_INTERVAL` files (250, the existing cadence) and once at the end, in the form `build_index: graph extraction progress (<layer> layer): <done>/<total> code files`. The line is the same on the thread, process and serial paths, including each serial fallback: after a thread or process pool failure, and when the process backend has no multiprocessing context (`mp_ctx is None`). It has no `[parallel-debug]` label and no thread list. The existing `[parallel-debug]` progress counter is replaced by this line; every other `[parallel-debug]` line is unchanged.
2. In verbose mode, the serial document loop in `build_graph_layer` prints the same form with `doc files`.
3. In verbose mode, `GraphIndexSession.finalize` prints `build_index: graph finalize (<layer> layer): <phase>` when each phase starts, with ` (<count> <unit>)` appended where the phase has an item count at hand. The first phase, `merge state load`, prints immediately before the store reads that precede the zero-change fast path (`store.paths_with_hashes()` and the summary-blob read). The remaining phases are the `# ---` sections of `finalize` after the fast path, plus the document rescans. The full order is `merge state load`, `merge state acquire`, `delta bookkeeping`, `doc rescans`, `merge entries`, `node map`, `DI resolution`, `resolution context`, `symbol delta`, `fragment resolution`, `edge assembly`, `publication prepare`. A phase that does not execute on a build prints no line, so a zero-change build prints only `merge state load`. Within the fragment-resolution loop a progress line follows the interval rule of requirement 1 (unit `files`).
4. Without verbose mode, the build prints nothing it did not print before.
5. Every new line is a single `print(..., flush=True)` from the parent process, so the existing log writer timestamps it. Elapsed time per phase is the difference between consecutive timestamps; no timing code is added.
6. `index_build_status`, the build-state file, the lock and the MCP tool contracts are unchanged.

## Scope

**Problem statement:** A verbose graph build is silent for minutes at a time, so the last log line (and `index_build_status.progress`) cannot distinguish progress from a hang.

**In scope:**

- Progress and phase lines in `graph_indexer.py` (`build_graph_layer` extraction loops, `GraphIndexSession.finalize`), plus a module constant for the interval.
- Tests in `test_graph_indexer.py` that capture verbose stdout.
- One sentence in `docs/architecture/chunking-and-indexing-pipeline.md` and an Unreleased CHANGELOG bullet.

**Out of scope:**

- Structured progress (JSON, percentages, ETA) and MCP progress notifications (plan `1p310`).
- Semantic (docs/code embedding) phase logging, and graph clustering, which already logs its phases.
- Performance work on whichever phase turns out to be slow.
- Removing or rewording the other `[parallel-debug]` lines.

**Platform behaviour:** the same on Windows, macOS, Linux and WSL2. Each line is a flushed `print` from the parent process to stdout, which the detached launcher already redirects to the build log on every platform. Process-backend workers (spawn start method on every platform) print nothing new; the parent counts their returned results.

## Acceptance Criteria

- [x] AC-1: A verbose graph build of a fixture above the parallel threshold (thread backend) and one below it (serial path) each print the plain code-file progress line, with a final `<done>/<total>` equal to the fixture's code-file count and no `[parallel-debug]` text on any progress line. Further tests run the serial fallback after a forced thread-pool failure, raised before the first result is consumed, and the `mp_ctx is None` serial path, and check the same final line. Oracle: captured stdout in `test_graph_indexer.py`, with the interval patched small.
- [x] AC-2: A verbose build with changed code and document files prints exactly the requirement 3 phase names that execute on that fixture, in the requirement 3 order, all before `graph extraction wrote`; a phase that executes but prints no line fails the test, plus at least one fragment-resolution progress line when the interval is patched below the file count. A verbose zero-change build prints `merge state load` and no other finalize phase line. Oracle: captured stdout.
- [x] AC-3: A non-verbose build of the same fixtures prints no `graph extraction progress` or `graph finalize` line. Oracle: captured stdout.
- [x] AC-4: On a real `index_build(content='graph', mode='rebuild')` of this repository, the log between the first extraction line and `graph extraction wrote` contains progress and finalize phase lines. The longest gap between consecutive lines in that span is recorded in the Progress Log, before and after this change. Oracle: the build log timestamps. This is the intent check; it records a measurement and sets no threshold.
- [x] AC-5: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add `_GRAPH_PROGRESS_INTERVAL = 250` and a small parent-side progress helper in `graph_indexer.py`.
- [x] Route the thread, process and serial (including fallback) code-extraction loops through the helper, and replace the `[parallel-debug]` progress counter.
- [x] Add the progress line to the serial document loop.
- [x] Add phase-start lines and the fragment-resolution counter to `GraphIndexSession.finalize`.
- [x] Add the AC-1, AC-2 and AC-3 tests in `test_graph_indexer.py`.
- [x] Update `docs/architecture/chunking-and-indexing-pipeline.md` and the CHANGELOG.
- [x] Run the AC-4 rebuild and record the before and after gaps.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| progress-lines | implementer | none | `graph_indexer.py` and tests |
| docs | implementer | progress-lines | architecture sentence, CHANGELOG |
| live-check | coordinator | progress-lines | AC-4 rebuild, Progress Log |

## Serialization Points

- `.wavefoundry/framework/scripts/graph_indexer.py`, `.wavefoundry/framework/scripts/tests/test_graph_indexer.py`, `docs/architecture/chunking-and-indexing-pipeline.md`

## Affected Architecture Docs

`docs/architecture/chunking-and-indexing-pipeline.md`: one sentence saying verbose graph builds log extraction progress and finalize phases to the build log. No boundary, flow or contract change; the other architecture docs are N/A.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Extraction progress on every path is the core of the change. |
| AC-2 | required  | The measured 5.5-minute silence falls in finalize; without phase lines the problem remains. |
| AC-3 | important | Keeps non-verbose callers (tests, direct API use) quiet. |
| AC-4 | important | The only evidence the operator-visible outcome changed on a real build. |
| AC-5 | required  | Standard change-local verification. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-19 | Planned. | Silent window 00:06:48 to 00:12:14 in `.wavefoundry/logs/project-index-build.log`. |
| 2026-10-19 | Readiness red-team primer: no blocker. Repaired before any approval: named the finalize phases (AC-2 could not fail on an open set), first line before the merge-state load, added the `mp_ctx is None` serial path. | Red-team primer report, receipt `review-policy-ba275e3c8897f18dc4ea` superseded. |
| 2026-10-19 | Readiness focused repair: code-reviewer and architecture-reviewer both found Requirement 3 contradictory, because the merge state is read before the zero-change fast path. Added a `merge state load` phase before those reads, renamed the old phase `merge state acquire`, and changed AC-2's zero-change clause. Implementation notes kept: interval read at call time; AC-2 hard-codes the expected list and pins the line format by regex; the fallback test asserts its stub raised; AC-1 stays on thread and serial paths (the existing `_SpyExecutor` has no `submit`). | code-reviewer, architecture-reviewer, qa-reviewer and security-reviewer readiness reports, receipt `review-policy-cf02583a8c5c1209460f` superseded. |
| 2026-10-19 | Implemented. Delivery: code-reviewer and qa-reviewer approved (QA killed 19 of 21 mutants; code-reviewer's placement mutant M5 survived). Added three tests after those approvals to close the survivors: process-pool failure fallback, `merge state load` before finalize's `paths_with_hashes()` read, and the phase count suffixes; all three mutants now fail in a scratch copy. architecture-reviewer blocked on the CHANGELOG claim that setup graph passes are verbose (setup adds `--verbose` only when asked); bullet corrected. Red-team and security seats passed. Gapfill: shell reads and edits used because auto mode prefers Bash for file work. | `GraphBuildProgressLoggingTests` 10 OK; `run_tests.py --file test_graph_indexer.py --file test_indexer.py` 977 OK before the added tests. |
| 2026-10-19 | AC-4 measurement. Before (build log of 2026-10-19 00:04 to 00:12): graph extraction span 7:38, 10 lines, longest gap 5:26 (`[parallel-debug] pool drained` to `graph cross-file resolution ran for`). After (forced `indexer.py --content graph --full --verbose` with the new code; the MCP server refused `index_build` with `index_runtime_stale` until a host restart): span 7:26, 38 lines, longest gap 5:10, from `graph finalize (project layer): doc rescans (489 changed docs)` to `merge entries (1043 files)`. Every other finalize phase took under 7 seconds. The silent window is now attributed to the document rescan loop, which has no per-item counter; adding one, and looking at why 489 doc rescans take 5 minutes, are follow-ups outside this change. The forced run printed two full graph passes back to back; not investigated. | Scratch log `212ym-graph-rebuild.log`; `.wavefoundry/logs/project-index-build.log`. |
| 2026-10-19 | Implemented; all ACs and tasks done. | Whole suite `Ran 11924 tests across 200 files in 716.149s OK` (12 skipped), green framework receipt. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-19 | Plain verbose lines: count-based progress in extraction loops plus phase-start lines in finalize. | Uses the existing log and `index_build_status` last-line path; no new mechanism or contract. | (a) Only promote the existing `[parallel-debug]` counter: misses the serial paths and the finalize window where the measured silence is. (b) Structured progress file read by `index_build_status`: a new contract and writer for a problem plain lines solve. (c) Time-throttled heartbeat thread: adds a thread to the build and says nothing about which phase is running. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A finalize phase is a single long call with no loop to count in, so it still goes silent after its start line. | The phase-start line still names the running phase; AC-4 records the remaining longest gap for a follow-up. |
| Extra printing in hot loops slows the build. | Lines print only at the interval and only in verbose mode; the per-item cost is one integer modulo. |
| Tests pin the old `[parallel-debug] progress` text. | Implementation greps the tests for that text and updates any pins. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
