# Index Builds Lose A Race Against The Server's Own Document Writes

Change ID: `1yjof-bug index-build-races-server-doc-writes`
Change Status: `complete`
Owner: Engineering
Status: completed
Last verified: 2026-09-19
Wave: 1yj14 index-build-write-races

## Rationale

**Brief.** Goal: an index build started while the MCP server is running reliably completes, and a build that does fail leaves the index queryable instead of dark. Audience: framework maintainers, and every operator whose repository is edited while it is indexed. Approach: stop the server writing indexed documents underneath its own builder, and stop a single changed file discarding a whole build and the previously published epoch with it. Constraints: the unified publication transaction stays unified, and the source-stability guarantee is not weakened. Success: a build running concurrently with normal server activity publishes, and a verified precommit refusal restores the intact prior snapshot; unsafe failures remain fail-closed.

Observed on this repository on 2026-09-19, while recovering the index after the storage-identity defect (`1yhhs-bug`). Four consecutive builds were attempted. Two failed at publication with `Atomic semantic publication failed: Source changed during embedding: docs/waves/1yja8 stable-storage-identity/wave.md`, one was left interrupted, and one succeeded. The file named in both failures was not being edited by a person: the operator had stopped work on that wave, and its modification time moved at 05:04:59, forty-six seconds into a build, with no other repository write in the window. That file carries a `<!-- wave:context-efficiency-state ... -->` marker block, and `index_health` reports a `context_efficiency_projection` background monitor configured with a 120-second quiet period and pending work. The build that finally succeeded was run from the CLI after a deliberate 160-second settle, during which the monitor flushed; across that build the file's modification time did not move.

The second failure is the more expensive one. It was a `content='graph'` rebuild, which performs no embedding. It completed its work -- 130 communities via Leiden, 63,047 nodes, 182,951 edges, 189 seconds of merge -- and then discarded all of it because an unrelated markdown file had changed. Publication is deliberately unified: one writer transaction publishes vectors, text, FTS, graph, extraction and community rows together (wave `1xny6`). So a docs write invalidating a graph rebuild is a consequence of that design rather than an oversight in it, and the repair must respect the unified transaction rather than carve the graph out of it.

Each failure also left `build_state` at `building` with the epoch interrupted, so every reader failed closed until a human noticed and ran recovery, even though a complete and valid previous epoch existed. During that window `index_health` reported the graph absent, which is indistinguishable from the storage-identity symptom that had just been fixed. The two defects masked each other, and the second was only visible once the first was repaired.

## Requirements

1. Automatic server-owned writers of indexed documents acquire and hold mutual exclusion with index builds across the entire write. The context-efficiency projector defers and re-arms on contention. Cover same-process threads and separate processes, both acquisition orders, and persistent unlocked files. A check of the existing held predicate is insufficient: it races build startup and POSIX record-lock inspection does not detect the caller's own lock. Operator-triggered edits remain unrestricted.
2. Caught source drift triggers at most one complete re-preparation/retry (two attempts total) under build ownership. Recompute all coupled semantic, extraction, graph and community participants; retain the unified publication transaction and all source guards. Repeated drift refuses with an actionable diagnostic. Partial per-path publication and embedding reuse are not required.
3. A caught precommit refusal may restore reader availability only when the previous snapshot was complete and verified, every canonical mutation has rolled back, and attempt ownership still matches. Use a distinct reader attempt token to prevent ABA while preserving the previous content generation. Independently committed resident changes must either be eliminated from the recoverable path or make recovery ineligible. No prior valid snapshot, crash, uncertain commit, postcommit failure or superseded attempt remains fail-closed. Previously completed content may be stale relative to current sources; report that distinction rather than declaring freshness.
4. Source-drift diagnostics name the changed path, retry/refusal disposition and whether readers can serve a previous completed snapshot or fail closed. Never describe a restored snapshot as a successfully published new build.
5. Remove the graph rebuild notice's unsupported “typically completes in ~10 seconds” estimate.

## Scope

**Problem statement:** Automatic document writes can invalidate an expensive build. A caught source refusal currently leaves readers unavailable even where the prior snapshot remains intact.

**In scope:** shared exclusion for automatic writers and builders; one bounded coherent retry for source drift; verified precommit snapshot recovery; truthful diagnostics and graph duration notice; deterministic concurrency and publication fault tests.

**Out of scope:** per-path partial publication; weakening source checks; splitting unified publication; interlocking operator edits; crash/postcommit recovery protocol; embedding reuse; storage identity; ranking, chunking, scheduling cadence.

## Acceptance Criteria

- [x] AC-1: A real due projection monitor defers while a real build owns exclusion and flushes after release. In the reverse ordering, a build cannot read sources until the projection write finishes. Cover same-process threads and separate processes; removal of the interlock fails the regression.
- [x] AC-2: A persistent unlocked file does not block the automatic writer. Unknown/error acquisition does not authorize a write; deferral retains pending work.
- [x] AC-3: Mutating a source during a real build triggers one coherent re-preparation and then publishes the updated content. Repeated mutations stop after two attempts, with no partial publication or unbounded loop.
- [x] AC-4: A verified precommit refusal with a previous complete snapshot preserves its payloads and mandatory bookkeeping and restores retrieval under a distinct complete token. Health distinguishes availability from source freshness. No prior snapshot, postcommit failure, uncertain commit and superseded attempt remain fail-closed. Fault tests pin these boundaries.
- [x] AC-5: Emitted source-drift diagnostics name the path, retry/refusal disposition and actual reader availability; assertions inspect emitted output/result text.
- [x] AC-6: The graph rebuild notice and its tests contain no unsupported duration estimate.
- [x] AC-7: Re-prepared semantic and graph participants publish atomically only after their existing source checks pass; a mutation after preparation never publishes stale prepared content as a new epoch. Retaining a historical snapshot is explicitly distinct from accepting it as current-source publication.
- [x] AC-8: All change-local suites pass, changed documentation validates, and the full framework suite has no failures attributable to this change.

## Tasks

- [x] Confirm the mechanism with a real monitor and real held build lock: marker generation advanced 1→2 and bytes changed while the lock remained held. Historical incident attribution remains circumstantial. Evidence: `/tmp/projection-build-race-evidence.json`, independently executed discovery probe.
- [x] Census automatic indexed-document writers and distinguish them from operator-triggered mutations. Evidence: concrete concurrency boundary below and `/tmp/index-writer-census.md`.
- [x] Implement acquire-and-hold exclusion and deferred writer re-arm with a consistent lock order.
- [x] Implement one bounded coherent source-drift retry, including graph/community re-preparation.
- [x] Implement verified precommit snapshot recovery and distinct reader token, retaining fail-closed for ineligible states.
- [x] Update failure diagnostics and graph duration notice.
- [x] Prove the original concurrent monitor/build mechanism now completes, and exercise reverse ordering and repeated drift.
- [x] Update architecture documentation and decision record; run the full framework runner last and record its receipt.

## Agent Execution Graph


| Workstream    | Owner       | Depends On  | Notes |
| ------------- | ----------- | ----------- | ----- |
| confirmation  | implementer | —           | prove the writer before designing against it |
| interlock     | implementer | confirmation | writer defers while the lock is held |
| publication   | implementer | —           | bounded retry and verified precommit recovery |
| messaging     | implementer | publication | operator-facing text |
| verification  | qa          | interlock, publication | concurrency proofs against real builds |


## Serialization Points

- `.wavefoundry/framework/scripts/indexer.py`, `.wavefoundry/framework/scripts/server_impl.py`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

`docs/architecture/chunking-and-indexing-pipeline.md` and `docs/architecture/data-and-control-flow.md` both describe the projection quiet period and the index build triggers as independent; they gain the interlock and the epoch-rollback behavior. `docs/contributing/build-and-verification.md` describes the projection trigger hierarchy and needs the same. A decision record will describe coherent retry and the safe precommit recovery boundary without weakening unified publication.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The race is the defect |
| AC-2 | required  | Acquire-and-hold exclusion must distinguish contention from a persistent unlocked file |
| AC-3 | required  | A transient source edit should recover without requiring operator intervention |
| AC-4 | required  | Going dark when a good epoch exists is the operator-visible harm |
| AC-5 | important | Determines whether an operator can act without reading source |
| AC-6 | important | A misleading estimate gets healthy builds killed |
| AC-7 | required  | The repair must preserve source validation and atomic publication |
| AC-8 | required  | Standard change-local verification |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-20 | Cycle 2 repairs independently reverified; producer-key and reload-omission mutants killed. Full runner GREEN: 9,409 tests/113 files, 12 skips, 294.799s. Docs validation passed; readiness renewed and affected delivery approvals restored. Framework gate closed; wave left open | /tmp/operator-repairs-framework.log; receipt 23c3ccf2c3101ddfb73b048970e605a882ad6e2ada36043d674a879bcbe38c07; typed cycle 2 convergence and approvals |
| 2026-09-20 | Operator review reopened delivery repair cycle 2: restore optimize error contract, include source guard in reload with independent import coverage, and narrow recovery provenance to lexical cache while retaining historical layer stamps. Earlier green receipt and delivery verdict do not prove these repairs | Typed findings B-1-optimize-error-contract, reload-source-guard-omission, recovery-provenance-doc-overclaim; Scope clarifications below |
| 2026-09-19 | Observe: final full runner GREEN, 9,402 tests across 112 files in 279.973s; 12 aggregate skips. Focused wave tests and independent mutation controls had zero skips. Full documentation validation passed. Framework edit gate closed; no commit/closure requested | /tmp/race-framework-final.log; .wavefoundry/framework/test-cache.json; wf_validate_docs |
| 2026-09-19 | Observe: full runner exercised 9,402 tests/112 files; sole failure was the exact handler-source digest for the intentionally changed index_build timing description (AC-6). Regenerated only that fixture entry after asserting the changed-handler set equals [index_build]; no schema/name/parameter or other handler digest changed. Full runner will be repeated for a green receipt | test_mcp_tool_registry.HandlerDigestTests; tests/fixtures/register-surface-handler-digests.json |
| 2026-09-19 | Observe: independent council clarified ADR wording to distinguish uncertain publication from an error during recovery COMMIT. The latter can leave the already verified historical snapshot available; existing two-ordering diagnostic tests cover it. No implementation boundary changed. Memory proposal produced zero durable candidates | test_recovery_error_emits_refusal_and_actual_reader_state_without_retry; memory_propose |
| 2026-09-19 | Observe: nine end-to-end native SQLite retry tests pass, including real build plus due monitor, graph-only rebuild drift, actual health/FTS availability with stale-source reporting, both uncertain-recovery message states. Same-stat source-guard deletion mutant is killed. Four old single-attempt/outage expectations in 367-test indexer run were updated; all three affected methods now pass | /tmp/race-final-retry-tests.log; /tmp/race-fixed-tests.log; /tmp/retry-mutant.log |
| 2026-09-19 | Reflect: recovery errors must compose their full diagnostic before emission, not append only to a returned dictionary. Recorded delivery finding uncertain-recovery-diagnostic, opened cycle 1 before repair, and added two fault orderings. Source/test tree frozen for final independent review; full runner started | Typed finding and repair_start; test_recovery_error_emits_refusal_and_actual_reader_state_without_retry |
| 2026-09-19 | Observe: two-file native SQLite fixture normal 0.2655s/one scan; one drift 0.3827s/two scans. This measures bounded fixture work, not production timing or a wall-time upper bound | /tmp/retry-performance.json |
| 2026-09-19 | Observe: source guard implemented; seven real lock/monitor/map cases and 96 existing CE cases passed. Removing guard in memory fails the monitor test with forbidden bytes changed. Recovery API: 10 dedicated plus 100 existing store tests pass; data_version, token-reuse and own-commit mutants all killed | test_index_source_guard.py; test_build_epoch_recovery.py; test_index_state_store.py |
| 2026-09-19 | Gapfill: indexed code_ask became unavailable while source/index changed; live code_read remained usable. Shell reads used for current mechanical diffs/test edits and docs locations; no stale semantic answer used | code_ask index_not_ready; live MCP source reads |
| 2026-09-19 | Thought: complete readiness, then implement in order: recovery API and automatic-writer guard in disjoint files; integrate bounded retry and unified sidecar cleanup in indexer; execute concurrency/publication fault and mutation tests; update architecture and run full verification | Reviewed concrete boundaries above |
| 2026-09-19 | Readback: a monitor flush that previously rewrote wave.md during a build will defer; a one-time operator edit will cause one coherent retry. A repeated edit may leave the verified old snapshot queryable, while postcommit/uncertain failures remain unavailable. AC-1–8 apply; files: indexer, index_state_store, server_impl, shared source guard and focused tests | No partial publication, no crash recovery, no commits or wave closure authorized |
| 2026-09-19 | Defect observed while recovering the index after `1yhhs-bug`. Four builds: two failed at publication naming a wave record no person was editing, one interrupted, one succeeded after a deliberate settle. The graph rebuild completed 130 communities over 63,047 nodes and 182,951 edges and discarded all of it. Each failure left readers failing closed despite a valid previous epoch, which masked the defect behind the storage-identity symptom | `.wavefoundry/logs/project-index-build.log`; `index_build_status` showing `building`/`interrupted` with the lock unheld; guard at `indexer.py:5571-5574`; unified-transaction comment at `indexer.py:5548` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-19 | Original proposal (superseded by reviewed contract below): interlock the writer rather than make the build tolerate concurrent writes | The server writing files it is concurrently indexing is the avoidable half; the lock and its held predicate already exist, so the interlock is small and local | Only loosen the publication guard: leaves the server fighting itself and relies on the looser guard for correctness |
| 2026-09-19 | Original proposal (superseded): also loosen refusal to per-path exclusion, rather than relying on the interlock alone | An operator edit during a build is legitimate and cannot be interlocked, so the build must survive it; the two repairs cover different writers | Interlock only: simpler, but a human editing during a long build still discards it |
| 2026-09-19 | Keep the unified publication transaction; do not carve the graph out of it | It is a deliberate invariant from wave `1xny6` that several validator paths depend on, and the observed harm is repairable without splitting it | Exempt graph-scope builds from semantic source validation: directly addresses the observed failure, but undoes a design decision on the strength of one incident |
| 2026-09-19 | Original proposal (narrowed below): roll back to the last good epoch instead of leaving `building` | Failing closed is right when nothing valid exists, but discarding a known-good epoch converts a retryable failure into an outage that needs a human | Keep fail-closed everywhere: simplest, and what produced a day of silent degradation here |


Operator decision, 2026-09-19: use bounded coherent retry and verified precommit rollback. Dependency-aware partial exclusion was rejected for this scope because graph resolution and community outputs cross file boundaries. Crash, uncertain-commit and postcommit failures remain fail-closed. Automatic writer serialization uses held exclusion, not a check-then-write predicate.

### Plan review outcome

Self-answered: the monitor can reproduce the race; lock observation is insufficient; semantic and graph publication are coupled; postcommit marker restoration is unsafe. Operator answered: bounded retry replaces partial publication, and only verified precommit rollback may restore availability. Stop condition: these behavioral branches are resolved; readiness must still validate the concrete locking and mutation-boundary design before code edits.

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Lock observation races startup or disrupts POSIX own-process locks | Use acquire-and-hold exclusion; test threads and processes in both orders without polling the record-lock predicate |
| Retry repeats expensive work indefinitely | One retry maximum; re-prepare all coupled participants and report exhaustion |
| Recovery relabels committed new rows as an old snapshot | Prove rollback before recovery; reject uncertain or postcommit states and superseded attempts; change the complete attempt token without advancing content generation |
| A restored snapshot is mistaken for current-source content | Diagnostics distinguish availability and freshness; no new stale prepared publication |
| Deferral loses telemetry | Preserve pending state and re-arm after contention |
| Historical cause is overstated | Deterministic reproduction proves the current mechanism, not the historical writer identity |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

## Concrete concurrency boundary

Use a persistent `index-source-mutation.lock` with the existing `RuntimeFileLock` default flock backend. The builder acquires its existing build lock first, then the source guard before reading sources, and retains both across the bounded retry. Automatic CE projection (quiet monitor and detached hook) acquires the source guard nonblocking before its existing nonblocking project publication lock. Missing-map resource fallback acquires the source guard before generation and its map lock. Contention preserves pending projection or missing-map state. Operator-triggered mutations remain outside this interlock.

The safety boundary is the builder's source-read lifetime, not the earlier instant its build-lock metadata becomes held. A writer that acquired source exclusion first may finish before the builder begins reading. No automatic projector waits for project publication while holding the source guard, avoiding a lifecycle-publication/build deadlock. Test both ordering directions and persistent unlocked carriers.

Discovery census: automatic indexed-document writers are CE quiet projection, detached automatic CE hook projection, and missing-codebase-map resource generation (including the repo-index block). Lifecycle/memory/gardening/map/evaluation/TechDocs/upgrade commands are operator-driven. Other background monitors write index, logs or caches rather than indexed documents. Existing public build calls will receive a fresh `PreparedUpdates` per attempt; graph preparation is inside `_build_index_locked` and must run again. Retry classification must be typed source drift, never arbitrary runtime/configuration/model/commit failure.

## Concrete recovery proof

Keep one owned SQLite connection through the guarded build. Under `BEGIN IMMEDIATE`, capture the prior complete epoch and `PRAGMA data_version`, then commit the durable building fence on that same connection. Before publication the only allowed independently committed owned mutation in the recoverable window is this fence. Move orphan sidecar deletion into the unified transaction; run the separately committing secrets scan outside the recovery window. Schema initialization precedes the capture.

After a caught typed source refusal, restoration requires confirmed rollback before any publication COMMIT attempt, unchanged external `data_version`, an originally complete snapshot, and exact attempt ownership checked inside a new writer transaction. External commits, rollback uncertainty or a changed attempt disqualify restoration. Restore availability with a distinct reader token while retaining the previous content generation; do not claim that old content was newly indexed. The data-version check is conservative: even an unrelated external commit can prevent restoration. This avoids whole-corpus snapshots or digest scans.

Tests must prove external resident mutation prevents recovery, superseded attempts cannot be overwritten, no previous snapshot remains unavailable, and a restored token never equals the original token. The one-retry wrapper owns the build/source locks throughout and allocates fresh staging and graph preparations each time. Postcommit cleanup failures never enter snapshot restoration.

Recovery checks `data_version` and attempt ownership inside the same restoration `BEGIN IMMEDIATE`. Preserve the original eligible snapshot baseline across both attempts, rather than treating an incomplete first attempt as the only prior state. When assigning a distinct restored reader attempt token, rebind only a valid lexical-statistics cache whose attempt and generation match the retained snapshot, in the recovery transaction. Preserve `build_layer_state` as historical per-layer publication bookkeeping, including its original attempt IDs and generations; recovery does not republish those layers. Verify retrieval and health against the retained snapshot rather than checking only the build-state row.
