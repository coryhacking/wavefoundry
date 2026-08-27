# Canonical Test Suite Critical-Path Acceleration

Change ID: `1tm6d-enh test-suite-critical-path-acceleration`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-08-27
Wave: `1tmtx test-suite-performance`

## Rationale

At planning time, the canonical framework suite had 6,235 tests across 59
independently isolated test files, recent cache-disabled runs on the development
host took roughly 290 seconds, and `test_server_tools.py` contained 1,433 tests
and 26,123 lines. Those figures are a historical planning snapshot, not the
implementation baseline: the corpus kept changing after `1tmb1` closed (64 test
files and a 37,610-line, roughly 1,742-test `test_server_tools.py` by
2026-08-27), and the current runner records only aggregate worker-phase wall
time. The module's size
makes it a plausible critical-path constraint, but does not prove that physical
sharding or timing-based scheduling will improve end-to-end time.

The suite's isolation model is valuable: each test file runs in its own Python
subprocess, avoiding the shared-`sys.modules` collisions observed under
monolithic discovery. This change shortens the critical path without weakening
that contract. It first adds measurement, then selects the faster deterministic
schedule under a controlled comparison. It divides the oversized server-tool
module only if the measured distribution and an Amdahl-style feasibility check
show that sharding can plausibly meet the target. It also gives repair loops a
canonical focused-file mode. One complete canonical run remains mandatory
delivery evidence.

## Requirements

1. The first implementation checkpoint after wave activation MUST confirm no
   concurrent writer to the runner or test corpus remains, then freeze the
   framework input digest, relevant runner/test-file
   digests, exact discovered test identity set, per-class normalized-AST
   fingerprints, file/test/skip counts, Python/OS/CPU environment, and worker
   count. Before any runner edit, record one uncounted warm-up and at least three
   external invocation-to-exit samples as the original-source baseline. No
   scheduling or shard edit may precede that checkpoint.
2. The canonical runner MUST measure child-subprocess elapsed time for every test
   file, report aggregate worker service time, and print a bounded top-10
   slowest-file summary in addition to total worker-phase wall time. The result
   model MUST also aggregate per-file skip counts; a forced-skip fixture,
   exercised outside the benchmark and delivery series, proves a nonzero skip
   reaches the complete-run summary and inventory comparison.
3. A successful complete run MUST attempt to atomically persist an optional
   `durations_s` object beside the existing last-green cache entry. Its keys are
   current discovered test-file basenames; values are finite, non-boolean,
   nonnegative seconds no greater than the per-file timeout. Malformed containers
   and entries, and unknown/stale keys, are ignored independently without
   invalidating an otherwise valid last-green result. Cache persistence failure
   remains nonfatal. After mode validation, an ordinary complete run reads the
   existing cache once: only matching `inputs_hash` and successful `result`
   authorize a skip, while an independently validated `durations_s` map may
   schedule work on a hash mismatch and under `--no-cache`. Absent, malformed,
   invalid, or stale values fall back per file. Timing data is advisory only and
   MUST never authorize a test skip or pass.
4. Full-suite scheduling MUST use the faster measured deterministic winner
   between the current alphabetical control and timing-guided longest-first
   candidate. The benchmark-only interface is
   `--schedule-control bootstrap|alphabetical|timing --timings-file <path>` and is
   mutually exclusive with `--file` and `--no-cache`. After the final file layout
   is frozen, one uncounted `bootstrap` run executes alphabetically and, only
   after a fully green run and artifact guard, atomically writes a complete JSON
   manifest containing the source digest and a `durations_s` object using
   Requirement 3's schema. It never reads or writes production cache state.
   `alphabetical` and `timing` validate and read that manifest without modifying
   it or calling production cache seams. Both counterbalanced candidates MUST use
   its byte-identical content, one unchanged runner source, and a fixed worker
   count; the comparison is invalid if any discovered file lacks a measured
   duration. When timing data is absent or invalid, ordinary runs fall back to
   the existing alphabetical name ordering; that fallback cannot authorize the
   schedule winner. Submission-order
   tests MUST observe the actual executor calls.
5. The existing six-worker cap, per-file subprocess boundary, UTF-8 environment,
   CPU-only test posture, reranker disablement, timeout, suite/index mutual
   exclusion, stray-artifact guard, stable failure output, and last-green cache
   semantics MUST remain intact.
6. Physical decomposition of `test_server_tools.py` is conditional: proceed only
   when the frozen per-file distribution shows it materially owns the critical
   path and the theoretical removable time, after duplicated startup/setup cost,
   can plausibly meet the 25% target. If proven, move whole test classes into the
   smallest useful set of 2–6 cohesive, independently runnable shards, with at
   most one measured rebalance. A consumer census MUST include
   `test_graph_query.py` and `test_render_platform_surfaces.py`; cross-file
   contracts move to a non-discovered support module containing no `TestCase`,
   `test_*`, or module-level mutable/cache/singleton server state. Helpers may
   mutate process-local state only when explicitly called. The final census MUST
   prove no `test_*.py` imports or dynamically executes another `test_*.py`, and
   MUST enumerate and re-point every path/basename-literal coupling to the
   server-tool test files in executable assertions and allowance tables (today:
   the `TEST_ALLOWANCES` path pins and the scope non-vacuity assertion in
   `test_events_only_residue_census.py`, and the self-referential basename
   filter inside `test_server_tools.py`) without weakening any census predicate;
   both known consumers import pure support callables while the discovered
   `TestCase` wrapper remains in a shard. No generalized sharding framework is
   in scope.
7. Test preservation MUST be proven by exact equality of the frozen unique
   `(class_name, test_method)` set and normalized `ast.dump(...,
   include_attributes=False)` fingerprints of every moved whole class, with an
   explicit exception map that is empty by default. One candidate entry is
   pre-identified at prepare: the reader-census test in `test_server_tools.py`
   that filters its grep hits by its own basename. On the sharding branch, one
   shard retains the `test_server_tools.py` basename and hosts that class
   together with the discovered `TestCase` wrapper; only if a measured rebalance
   moves the class does the one-line filter retarget become the recorded,
   separately reviewed exception-map entry. Reject duplicate identities,
   missing classes, assertion-to-`pass` mutation, delete-plus-padding, and new
   skips. Each shard has a nonempty exact expected identity subset, must discover
   and execute that subset in focused isolation, and the shard union must equal
   the frozen set. New runner tests are accounted separately; total count is
   secondary.
8. The canonical runner MUST accept a repeatable `--file <basename>` selector for focused
   implementation and repair loops. Selected files MUST still execute through
   the same lock, subprocess, environment, timeout, and artifact-guard path as a
   full run. Invalid, duplicate, non-test, missing, or escaping selectors MUST
   fail clearly and deterministically.
9. Focus selectors MUST be parsed and fully validated before any input hashing,
   cache, or timing-map read. They are exact direct-child discovered `test_*.py`
   basenames; missing values, duplicates, path separators, absolute/path-like or
   escaping values, absent/non-test files, positional arguments, unknown options,
   and combining `--file` with `--no-cache` MUST fail clearly. Valid focused runs
   call none of the hash/cache/timing read or write seams, identify themselves as
   focused, and leave the full-suite cache byte-identical. Positive call-order
   spies MUST prove the focused path traverses `_wait_for_index_build`,
   `_acquire_run_lock`, `_probe_index_build_lock`, `_clean_pycache`, `_run_file`,
   `_stray_artifact_failure`, and `_release_run_lock`; zero-call spies cover all
   hash/cache/timing seams. A prepare-time caller census (2026-08-27) found
   every in-tree invocation passes either no arguments or `--no-cache` only, so
   rejecting positionals and unknown options strands no current caller.
10. The unchanged invocation `python3 .wavefoundry/framework/scripts/run_tests.py`
   MUST retain its current cache-hit and cache-miss behavior. `--no-cache` MUST
   continue to force a complete run and MUST not be forwarded to `unittest`.
11. Performance evidence MUST use external invocation-to-exit monotonic time as
   the primary metric. After telemetry-only edits (no scheduling or sharding),
   freeze the instrumented source and collect one uncounted warm-up plus at least
   three pre-optimization samples to establish the per-file distribution and
   aggregate service time. Then record the same post-change series. All series
   use the same host with dashboard/index activity settled and an unchanged
   digest within the series. Record individual times and median, exit code,
   file/test/skip counts, Python/OS/architecture/CPU, worker count, relevant
   environment, internal worker-phase time, and aggregate worker service time.
   The 25% end-to-end comparison uses the original-source baseline from
   Requirement 1; feasibility and schedule controls use the instrumented
   pre-optimization evidence. Schedule controls are counterbalanced on identical
   source after the separately recorded uncounted post-layout bootstrap, using
   the byte-identical complete timing manifest from Requirement 4.
12. Before sharding, the baseline MUST calculate whether the measured dominant
   tail contains enough removable time to reach a 25% improvement after expected
   duplicate startup/setup work. If it does not, retain telemetry and focused
   mode, do not shard, and require operator direction on narrowing the target.
   The post-change median full-suite wall time SHOULD improve by at least 25%
   without reducing test count or introducing new skips. If it does not, the
   wave permits at most one measured shard rebalance, then requires explicit
   operator choice to accept the measured gain, narrow the target, or revert
   performance-only complexity. The implementation MUST NOT claim a speedup
   from scheduling theory alone.
13. Testing documentation MUST distinguish focused diagnostic evidence from the
    authoritative complete canonical run and document the timing/scheduling
    behavior, including the explicit disclosure that `--no-cache` still reads
    the cache file for the advisory `durations_s` scheduling map while never
    accepting a cached pass, without making the cache or timing file a public
    compatibility API.

## Scope

**Problem statement:** File-level parallelism is preserved, but the runner lacks
per-file timing evidence needed to identify its real critical path and compare
schedules. The historical size of `test_server_tools.py` makes it a plausible
tail, not a proven one. The runner also lacks a safe focused mode, so agents
either repeat the complete suite or bypass canonical runner guards.

**In scope:**

- `.wavefoundry/framework/scripts/run_tests.py`
- `.wavefoundry/framework/scripts/tests/test_run_tests_cache.py`
- `.wavefoundry/framework/scripts/tests/test_graph_query.py` and
  `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py` where
  they consume server-tool test support
- measurement-gated domain-oriented decomposition of
  `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_events_only_residue_census.py`,
  narrowly: allowance re-pointing and scope-pin updates when shards land, with
  no census-predicate weakening
- `.wavefoundry/framework/scripts/tests/__init__.py`, narrowly: re-point the
  per-class invocation examples in its docstring on the sharding branch
- a narrowly scoped shared support module for the server-tool shards if required
- tests that prove scheduling, selector validation, cache isolation, inventory
  preservation, and runner output
- `docs/architecture/testing-architecture.md` and contributing/verification
  guidance that owns the canonical runner contract
- reproducible before/after performance measurements
- preservation of the existing package exclusion for framework tests, the test
  runner, benchmark evidence, and cache state; no install/upgrade migration is
  required because none of these surfaces ship to target projects

**Out of scope:**

- weakening per-file subprocess isolation or switching to monolithic discovery
- increasing the worker cap above six without a separate saturation study
- skipping, deleting, or replacing substantive tests to meet the speed target
- dependency-aware or per-test-result caching
- pytest migration, distributed execution, remote executors, or CI-provider work
- production-code performance changes unrelated to the test harness
- treating focused runs as delivery, release, or close-gate evidence

## Acceptance Criteria

- [x] AC-1: Runner tests prove per-file child elapsed measurements, aggregate service time, bounded top-10 output, safe alphabetical-name fallback ordering when timing data is absent or invalid, and exact executor submission order for each deterministic schedule candidate.
- [x] AC-2: Successful complete runs attempt to persist the optional validated `durations_s` map; ordinary full runs read the cache once and may reuse valid timings on hash mismatch or `--no-cache`, while malformed containers/entries and stale keys degrade independently, cache write failure remains nonfatal, and only matching hash/result can authorize a skip.
- [x] AC-3: The frozen pre-change identity set and normalized whole-class AST fingerprints exactly equal the post-move set, the exception map is empty unless separately reviewed, skip count is unchanged, each shard discovers and executes its exact nonempty expected subset in focused isolation, the shard union equals the frozen set, no test module imports/executes another test module, both known consumers use pure support, and delete-plus-padding, duplicate/omit, assertion-to-`pass`, and new-skip mutants are caught. If measurement rejects sharding, this AC records that disposition and the unchanged frozen inventory instead.
- [x] AC-4: Repeatable `--file <basename>` selection is fully validated before hashing/cache/timing access, runs only requested valid files, rejects every invalid selector class and `--file`+`--no-cache`, labels output as focused, calls no hash/cache/timing seams, leaves the cache byte-identical, and positive call-order spies prove every named canonical lock/index/cleanup/subprocess/artifact/release seam executes.
- [x] AC-5: Existing cache-hit, cache-miss, `--no-cache`, locking, index exclusion, timeout, environment, artifact, and failure-reporting regressions remain green for the unchanged canonical invocation.
- [x] AC-6: External invocation-to-exit evidence records the frozen original-source baseline plus the instrumented pre-optimization and post-change series, each with one warm-up and at least three samples and the applicable environment, digest, count, skip, internal timing, and service-time fields; a fixture-scoped forced-skip control, excluded from the benchmark and delivery series, proves nonzero skip aggregation, all post-change runs are green with no new skips, and the median meets 25% or carries the bounded operator disposition from Requirement 12.
- [x] AC-7: A post-layout alphabetical bootstrap emits a complete digest-bound timing manifest only after a green artifact-clean run; counterbalanced alphabetical and timing-guided controls then run through one unchanged source artifact with that byte-identical read-only manifest and no production cache calls. Missing current-file durations invalidate the comparison; the measured faster deterministic schedule is selected and the result includes makespan and aggregate worker service time.
- [x] AC-8: Testing architecture and contributor verification docs state when focused runs are appropriate, preserve one full canonical isolated run as the delivery authority, and document the timing/scheduling behavior, including the `--no-cache` advisory-read disclosure, without making the cache or timing file a public compatibility API.
- [x] AC-9: Docs lint and `git diff --check` pass, and no bytecode, runner state, dashboard process, or index artifact is left in the tracked tree.

## Tasks

- [x] At wave activation, confirm no concurrent runner/test-corpus writer remains, then freeze source/file digests, exact test identities and class fingerprints, skips, and environment; record the original-source external baseline before any runner edit.
- [x] Extend `_run_file` and the result model with elapsed time; add bounded slow-file reporting.
- [x] Freeze the telemetry-only runner and record the instrumented pre-optimization per-file distribution before any scheduling or shard edit.
- [x] Extend the existing last-green cache with advisory successful-full-run timing data and safe parsing.
- [x] Add a benchmark-only deterministic schedule control, compare alphabetical and timing-guided candidates on identical source/fixed timing input, and select the measured winner.
- [x] Add repeatable `--file <basename>` focused selection with pre-hash validation and complete hash/cache/timing isolation.
- [x] Run the critical-path/Amdahl feasibility gate; only if it passes, census external consumers, extract pure non-discovered support, and partition `test_server_tools.py` into the minimum measured 2–6 domain shards.
- [x] Add inventory, scheduling, cache, selector, mutation/falsification, and safety-path regressions.
- [x] Freeze the final file layout, run the uncounted alphabetical manifest bootstrap, then run the counterbalanced schedule controls and select the measured faster ordering.
- [x] Run and record at least three frozen post-change full-suite benchmarks.
- [x] Update testing architecture and contributor verification documentation.
- [x] Run the canonical suite, docs lint, diff check, and stray-artifact/bytecode checks.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Original baseline and runner telemetry | performance-reviewer | Wave activation with no concurrent runner/test-corpus writer | Freeze original source/inventory and external baseline, then instrument only and capture the pre-optimization distribution. |
| Scheduling and focused mode | framework-engineer | Baseline and runner telemetry | Shared ownership of `run_tests.py`; serialize edits. |
| Server-tool shard decomposition | test-engineer | Baseline, runner telemetry, and feasibility gate | Starts only if measurement authorizes it; then use the minimum bounded shard count. |
| Contract and regression review | qa-reviewer | Scheduling; shard decomposition | Prove cache isolation, inventory, safety-path parity, and mutant detection. |
| Post-change benchmark and docs | performance-reviewer, docs-contract-reviewer | All implementation work | Benchmark before claiming improvement; reconcile canonical evidence wording. |


## Serialization Points

- Do not capture evidence or edit the runner/test corpus while any concurrent writer remains; the freeze is the first implementation checkpoint after activation. Freeze the original source/inventory and external baseline before the telemetry edit; after telemetry only, freeze and capture the pre-optimization per-file distribution before moving any test body or changing scheduling.
- Serialize all edits to `run_tests.py` and `test_run_tests_cache.py` through the runner workstream.
- Measure before authorizing decomposition; if the feasibility gate fails, stop the shard workstream and request the bounded operator decision.
- Census `test_graph_query.py`, `test_render_platform_surfaces.py`, and all other consumers, then freeze the pure shared server-test-support interface before moving the second shard.
- Complete the shard inventory comparison before deleting the original monolithic file.
- Freeze the implementation and stop dashboard/index activity before the post-change benchmark series.
- After any final shard layout, bootstrap one complete timing manifest before the schedule controls; controls must not update that manifest or production cache state.
- Do not record delivery approval until the benchmark threshold, complete canonical suite, and focused-vs-full evidence distinction are all independently verified.

## Affected Architecture Docs

- `docs/architecture/testing-architecture.md` — record file-level isolation, measured scheduling, focused diagnostic mode, and complete-run authority.
- `docs/contributing/build-and-verification.md` — document the focused invocation for repair loops and retain the canonical delivery command.
- On the sharding branch, re-point every live-doc reference to the monolith's basename: the `test_server_tools.py` tier rows in `docs/architecture/testing-architecture.md`, plus `docs/architecture/embedding-model.md`, `docs/architecture/layering-rules.md`, `docs/architecture/graph-index-system.md`, `docs/agents/software-engineer.md` (the new-MCP-tool test guidance line), and the per-class invocation examples in `.wavefoundry/framework/scripts/tests/__init__.py`.
- `docs/ARCHITECTURE.md` does not require a new child doc; this changes the existing testing seam rather than introducing a new subsystem.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Without timing and deterministic scheduling evidence, the optimization is not testable. |
| AC-2 | required | Advisory timing data must not become false skip authority. |
| AC-3 | required | The critical-path split must preserve the complete test inventory. |
| AC-4 | required | Focused loops must use canonical safety mechanics without contaminating delivery evidence. |
| AC-5 | required | Existing isolation and safety contracts are load-bearing. |
| AC-6 | required | The wave exists to produce a measured speedup, not an architectural claim. |
| AC-7 | required | Scheduling authority must be the measured control winner, not a preselected theory. |
| AC-8 | important | Agents need an unambiguous focused-versus-authoritative rule. |
| AC-9 | required | Repository hygiene and docs validity remain release gates. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-26 | Planned from a live runner assessment: 6,235 tests / 59 files, six workers, roughly 290-second recent wall time; `test_server_tools.py` is the 1,433-test/26,123-line outlier. | `run_tests.py` scheduling/cache inspection; current test-file census. |
| 2026-07-26 | Readiness council marked those figures historical while `1tmb1` changes the shared corpus; no tests or benchmarks were run during prepare by operator direction. The plan now freezes its authority after `1tmb1`, measures before selecting scheduling or sharding, and uses exact identity/AST preservation. | Read-only runner/cache/consumer census; architecture, security, QA, reality, and performance readiness reviews. |
| 2026-08-27 | Re-prepare after the review-policy receipt lapsed (evaluator v7; targeted council: red-team primer, docs-contract-reviewer). Fresh census: 64 test files; `test_server_tools.py` at 37,610 lines and roughly 1,742 tests; the only import-level consumers remain `test_graph_query.py` and `test_render_platform_surfaces.py`; path-literal couplings found in `test_events_only_residue_census.py` and the self-referential basename filter. Eight prose repairs applied: census-predicate extension, residue-census scope addition, exception-map pre-identification, activation-checkpoint trigger replacing the stale `1tmb1` condition, alphabetical-fallback tense fix, `--no-cache` advisory-read disclosure, forced-skip control scoping, and the caller census supporting Requirement 9. | Council seat reports (red-team, docs-contract-reviewer); `run_tests.py` caller census: every in-tree invocation is bare or `--no-cache`. |
| 2026-08-27 | Thought: wave opened (implementing). Requirement 1 checkpoint first: no concurrent writer confirmed (single-OPEN slot held by this wave, index build lock free and last build clean, framework tree unmodified in git). Freezing digests, executed test identities, per-class AST fingerprints, skips, and environment, then capturing the original-source external baseline (one uncounted warm-up plus three timed `--no-cache` complete runs) before any runner edit. | `index_build_status` lock.held=false; evidence to be written under `docs/waves/1tmtx test-suite-performance/evidence/`. |
| 2026-08-27 | Observe: Requirement 1 checkpoint complete and green. Frozen: 64 files, 963 class fingerprints, 6,750 static identities, inputs_hash `2afaa2e9…`, HEAD `29da370e`. Executed census: 7,494 ran / 3 skipped / 0 failures, no stray artifacts. Original-source baseline: samples 217.9 / 216.0 / 216.7 s, median 216.665 s external; internal worker phase within 0.2 s of external. Distribution: `test_server_tools.py` 162.0 s dominates (next `test_docs_lint.py` 102.4 s, `test_indexer.py` 65.3 s, `test_graph_indexer.py` 63.0 s); aggregate service roughly 620 s across 6 workers. | `evidence/freeze.json`, `evidence/census.json`, `evidence/baseline.json`, `evidence/logs/baseline-*.log`. |
| 2026-08-27 | Thought then Observe: telemetry (Task 2) implemented as `FileResult` (name, returncode, output, test_count, elapsed_s, skip_count), child-elapsed measured around the worker invocation, skip counts parsed from the unittest result tail, bounded top-10 and worker-service-time summary added on both success and failure paths; existing summary lines byte-identical. Eight regressions added in `test_run_tests_cache.py` (focused run 45/45 green). Level 1 finding on the first instrumented series: all four runs failed with one error, the pre-existing 4-tuple unpack of `_run_file` in `test_run_tests_lock.RunFileEncodingTests` (a runner-API consumer the plan census, scoped to `test_server_tools` couplings, did not cover). Fixed to consume `FileResult`; focused lock file green; failed series archived at `evidence/logs/attempt1/`; instrumented series re-running on the corrected frozen source. Reflect: internal-API shape changes need a callers grep across the whole tests tree, not only the census scoped to the file being decomposed. | `run_tests.py` `FileResult`/`_run_file`/`main`; `test_run_tests_cache.py` `RunFileTelemetryTests`, `TelemetrySummaryTests`; `test_run_tests_lock.py` `RunFileEncodingTests`; `evidence/logs/attempt1/`. |
| 2026-08-27 | Observe: instrumented pre-optimization series complete on frozen source (inputs_hash `edd7844e…`). Three samples green: 218.8 / 216.7 / 216.7 s external, median 216.701 s; service-time median 617.973 s. The uncounted warm-up carried one failure, a pre-existing load-sensitive wall-clock assertion in `test_techdocs_audit_lib.TechdocsAuditBoundaryAgreementTests.test_a_segment_local_pattern_skips_the_ancestor_walk` (0.181 s against a 0.15 s bound under 6-worker load); it passed in all three samples and every prior run, is untouched by this wave, and is noted as a follow-up candidate and a rerun risk for the post-change benchmark series. Per-file medians: `test_server_tools.py` 182.1 s, `test_docs_lint.py` 99.8 s, `test_indexer.py` 67.8 s, `test_graph_indexer.py` 59.0 s. Requirement 12 feasibility arithmetic: the 25% target is 162.5 s or less; the dominant file's 182.1 s median alone exceeds that, so scheduling cannot reach the target and physical decomposition is measurement-authorized; post-shard makespan floor is roughly max(99.8 s second-longest, 618/6 = 103 s service bound) plus bounded startup duplication, leaving wide margin. Tasks 2 and 3 marked complete. | `evidence/instrumented.json`, `evidence/logs/instrumented-*.log`, `evidence/capture_instrumented.log`. |
| 2026-08-27 | Observe: Tasks 4 and 6 landed (advisory `durations_s` persistence with independent validation and single cache read; strict argv parsing; benchmark-only `--schedule-control` interface; focused `--file` mode with complete hash/cache/timing isolation and canonical-seam call-order proofs); 47 new regressions, focused file 92/92 green, end-to-end smoke of focused/usage/exclusivity passed, full canonical suite green. Level 2 finding while verifying: the runner's per-file count parse took the FIRST unanchored "Ran N tests" match from merged output, so `test_run_tests_cache.py`'s mock main() output ("Ran 42 tests across 1 files", the default `tests_run=42`) had been read as the file's count, inflating the suite total by 5 (reported 7,499 versus the census-true 7,494). Repaired in `_run_file` by anchoring count and skip parsing to the LAST unittest summary ("Ran N tests? in X.XXXs") and the tail after it; two known-bad regressions added; focused file 94/94 green. Post-fix totals are true counts and will differ from historical runner-reported totals. | `run_tests.py` `_run_file` tail parse; `test_run_tests_cache.py` `test_run_file_count_ignores_runner_style_lines_printed_by_tests`, `test_run_file_skip_count_binds_to_final_summary_only`; `evidence/census.json` total 7,494 versus pre-fix runner total 7,499. |
| 2026-08-27 | Observe: sharding executed and proven. Per-class measurement (223 classes, all green in isolation, 1,737 tests) drove a cohesion-first 3-shard manifest; `shard_split.py` regenerates the layout mechanically from the pristine git HEAD source with four pre-write gates. Layout: retained `test_server_tools.py` (46 classes, core/infra, hosts the Guard wrapper and the reader-census class), `test_server_tools_retrieval.py` (111), `test_server_tools_lifecycle.py` (66), plus non-discovered `server_tools_support.py` (17 names: 8 shared fixtures, `SCRIPTS_ROOT`/`SERVER_PATH`, `SPAWN_ATTRS`, and the six Guard scan seams; the Guard rebinds them via `staticmethod`, the one Requirement 7 exception-map entry, mechanically proven by AST-comparing each support function against the rename-mapped HEAD original). Two splitter iterations: a support-to-shard leak (`_append_typed_approval` reaching `WaveLifecycleMutationTests._approval_record`) moved four lifecycle-only ledger helpers into the lifecycle shard and added a support-leak gate; the residue-census allowance pins re-pointed to the lifecycle shard. Both consumers now import pure support callables. The original module's MID-FILE `__main__` guard (line 33882, the latent 1t018 hazard) is fixed: every shard carries an EOF main block. `verify_shards.py` PASSES: exact identity-set equality, all 222 fingerprints frozen-equal, census predicate clean with one disclosed pre-existing exclusion (`test_render_agent_surfaces.py` imports `test_upgrade_wavefoundry`, predates this wave, out of scope, follow-up candidate), and all five mutants caught (delete-class, delete-plus-padding, assertion-to-pass, duplicate-class, new-skip). Focused shard runs green: 336+891+510=1,737 tests, 0 skips; in-file shard times 90.3/37.4/79.6 s, every shard under the `test_docs_lint.py` ceiling, so the single permitted rebalance is not exercised (it could not improve the makespan floor). | `evidence/shard_manifest.json`, `evidence/class_timings.json`, `evidence/shard_split.py`, `evidence/verify_shards.py`, `evidence/verify_shards.json`; `evidence/logs/focused-shards.log` (archived during delivery review after qa-reviewer finding F1 flagged the unarchived citation); census pins in `test_events_only_residue_census.py`. |
| 2026-08-27 | Observe: first full canonical run over the sharded tree, still alphabetical: 119.1 s wall, 7,551 tests across 66 files, green, 3 skips; new critical path `test_docs_lint.py` 105.8 s; shards at 85.2/73.7/31.6 s. Level 2 finding while running the first schedule-control comparison: the framework digest was unstable across runs because the old `parts[0]`-only exclusion missed NESTED `scripts/__pycache__` bytecode (created when an external process imports `run_tests` before its `dont_write_bytecode` takes effect and deleted mid-run by `_clean_pycache`) and because `test-run.lock` carries a per-run pid write. Repaired in `_hash_inputs` (any-component dir exclusion; `test-run.lock` added to the name exclusions) with two regressions; focused file 96/96 green. | full-suite log; digest diff diagnostic; `test_run_tests_cache.py` `test_nested_pycache_excluded`, `test_run_lock_content_excluded`. |
| 2026-08-27 | Observe: Requirement 4 settled by measurement. Uncounted bootstrap (green, 117.7 s) wrote the digest-bound manifest; counterbalanced candidates ran A-T-T-A on byte-identical manifest and unchanged source, all green: alphabetical 119.0/142.0 (mean 130.5 s), timing 124.5/149.0 (mean 136.8 s). Winner: ALPHABETICAL, which also won both adjacent pairs; the prepare watchpoint (starting all heavy files together saturates the host) is confirmed by measurement, so production scheduling stays alphabetical and no production wiring change is needed. Requirement 11/12 verdict: post-change series on frozen final source, warm-up plus three samples all green with no new skips (7,553 tests, 3 skips), samples 124.5/135.9/141.3 s, MEDIAN 135.9 s versus the original-source baseline median 216.665 s: a 37.3% improvement, exceeding the 25% target; the worst single sample still improves 34.8%. | `evidence/schedule_controls.json`, `evidence/timings-manifest.json`, `evidence/benchmark_final.json`, `evidence/logs/control-*.log`, `evidence/logs/final-*.log`. |
| 2026-08-27 | Observe: implementation complete. Documentation landed (canonical-runner/measured-scheduling/shard-family section plus tier-row re-points in `testing-architecture.md`; focused-run and `--no-cache` advisory-read guidance in `build-and-verification.md`; re-points in `embedding-model.md`, `graph-index-system.md`, `software-engineer.md`, and the `tests/__init__.py` docstring examples). Final gates: canonical suite on the complete delivery tree 7,553 tests across 66 files in 120.7 s, green, 3 skips; `wf_garden_docs` stamped five docs; full `wf_validate_docs` passed (one advisory warning on the July council roster resolved with a pointer entry in the wave record); `git diff --check` clean; no stray artifacts or bytecode. All tasks and AC-1 through AC-9 marked complete; `framework_edit_allowed` gate closed. Next lifecycle step: Review wave (delivery lanes code-reviewer, qa-reviewer, architecture-reviewer). | final suite log; `wf_validate_docs` result; git status handoff. |
| 2026-08-27 | Observe: initial delivery review complete, all three required lanes APPROVE (typed approvals `ev-approval-code-reviewer-2`, `ev-approval-architecture-reviewer-2`, `ev-approval-qa-reviewer-2`/`-3`). Nine lane findings total, none blocking: six repaired in-cycle and independently re-verified by their originating lanes (archived focused-shard log plus citation re-point; census predicate widened to package-qualified `tests.test_*` with the second pre-existing cross-test import disclosed; `test_review_policy.py` docstring re-point; evidence bytecode deleted; `Guard._SPAWN_ATTRS` aliased to the support set object; `_cache_hit` non-dict guard with regression, focused file 97 green), two recorded `dont_do_later` (post-summary stderr telemetry-corruption residual; in-tree timings manifest fails closed with a misleading digest message), one `not_issue` (pre-existing empty-directory executor edge). Post-repair verifier pass with both disclosed exclusions and all five mutants caught; post-repair canonical suite 7,554 tests across 66 files in 120.7 s, green, 3 skips (count amended by the new regression: 7,494 + 60). Remaining before close: operator-signoff. | wave.md Review Checkpoints delivery entry; `events.jsonl` records 10-14; `evidence/verify_shards.json`; suite log `full_suite_post_review.log`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-26 | Deliver telemetry and focused mode; select scheduling and physical sharding only after controlled measurement. | The original plan inferred a serial-tail cause from size/count and contradicted its own measured-winner AC. Measurement is the authority. | Mandating longest-first and sharding up front was rejected as premature optimization. |
| 2026-07-26 | Preserve file-level subprocess isolation and the six-worker cap. | Isolation prevents shared-module-state collisions; the cap already encodes observed CPU/I/O saturation above six. | Monolithic discovery and simply adding workers were rejected as correctness/performance regressions without new evidence. |
| 2026-07-26 | Defer dependency-aware per-file result caching. | Dynamic imports, generated assets, seeds, and shared fixtures make invalidation materially harder to prove than scheduling and physical sharding. | A per-file cache could be reconsidered only with an explicit dependency authority and false-hit probes. |
| 2026-07-26 | Target a measured 25% median improvement; after the one permitted rebalance, any miss requires explicit operator disposition accepting the measured gain, narrowing the target, or reverting performance-only complexity. | The benefit must be observable on the real suite without turning an infeasible target into an endless correction loop. | A fixed 2× promise was rejected as unjustified; a no-threshold benchmark and unbounded correction were rejected because either could ship unjustified complexity. |
| 2026-07-26 | Bound correction to one shard rebalance and then an explicit operator decision. | Prevent an optimization wave from expanding indefinitely when the measured target is infeasible. | Repeated unbounded reshaping was rejected. |
| 2026-07-26 | Bootstrap the schedule-control timing manifest after the final file layout. | Pre-shard timings name the monolith and cannot fairly compare a post-shard timing-guided schedule; the fixed control input must cover every current file. | Reusing pre-shard timings or allowing source-size proxy values to decide the schedule was rejected as circular/vacuous evidence. |
| 2026-08-27 | Keep physical sharding as the measurement-gated path; class-level unittest dispatch of the dominant file's `TestCase` classes into the existing worker pool was evaluated at re-prepare and not selected. | Class-level job identity depends on runtime discovery rather than a stable filesystem artifact, stretches the one-subprocess-per-file invariant the lock/cache/artifact machinery assumes, and leaves the 37,610-line module's maintainability liability unaddressed. | Class-level dispatch may be revisited by operator direction if the feasibility gate rejects physical sharding. |


## Risks


| Risk | Mitigation |
| --- | --- |
| Starting all heavy files first saturates the host and lengthens individual jobs. | Keep the six-worker cap and compare longest-first with the prior schedule under a frozen load shape before selecting it. |
| Moving tests silently drops, duplicates, or weakens cases. | Freeze exact test identities and whole-class AST fingerprints, preserve skips, reject named mutants, and treat total count as secondary. |
| Shared support extraction changes test behavior or adds hidden process state. | Extract only pure callables, forbid module-level mutable server/cache state and test-to-test imports/exec, migrate both known consumers, and execute every shard independently. |
| Focused runs are mistaken for delivery evidence. | Label them explicitly, keep them out of the full cache, document the distinction, and retain the complete-run close requirement. |
| Stale/malformed timing data affects correctness. | Treat timings as ordering hints only; validate them, fall back deterministically, and never use them for selection or skipping. |
| Performance evidence is distorted by concurrent dashboard/index activity. | Use the existing lifecycle locks, settle those processes before benchmarks, record environment limits, and repeat runs. |
| Sharding duplicates interpreter/import/setup work without enough removable tail. | Require the measured feasibility gate, select the minimum measured 2–6 shard design, record aggregate service time, and allow one rebalance only. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
