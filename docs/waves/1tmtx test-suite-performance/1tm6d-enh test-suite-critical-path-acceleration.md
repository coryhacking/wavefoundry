# Canonical Test Suite Critical-Path Acceleration

Change ID: `1tm6d-enh test-suite-critical-path-acceleration`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-26
Wave: `1tmtx test-suite-performance`

## Rationale

At planning time, the canonical framework suite had 6,235 tests across 59
independently isolated test files, recent cache-disabled runs on the development
host took roughly 290 seconds, and `test_server_tools.py` contained 1,433 tests
and 26,123 lines. Those figures are a historical planning snapshot, not the
implementation baseline: `1tmb1` is actively changing the same corpus, and the
current runner records only aggregate worker-phase wall time. The module's size
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

1. After `1tmb1` finishes and the test corpus is stable, the first implementation
   checkpoint MUST freeze the framework input digest, relevant runner/test-file
   digests, exact discovered test identity set, per-class normalized-AST
   fingerprints, file/test/skip counts, Python/OS/CPU environment, and worker
   count. Before any runner edit, record one uncounted warm-up and at least three
   external invocation-to-exit samples as the original-source baseline. No
   scheduling or shard edit may precede that checkpoint.
2. The canonical runner MUST measure child-subprocess elapsed time for every test
   file, report aggregate worker service time, and print a bounded top-10
   slowest-file summary in addition to total worker-phase wall time. The result
   model MUST also aggregate per-file skip counts; a forced-skip fixture proves a
   nonzero skip reaches the complete-run summary and inventory comparison.
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
   duration. Source-size/name fallback remains a production resilience behavior
   for ordinary runs, but cannot authorize the schedule winner. Submission-order
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
   prove no `test_*.py` imports or dynamically executes another `test_*.py`;
   both known consumers import pure support callables while the discovered
   `TestCase` wrapper remains in a shard. No generalized sharding framework is
   in scope.
7. Test preservation MUST be proven by exact equality of the frozen unique
   `(class_name, test_method)` set and normalized `ast.dump(...,
   include_attributes=False)` fingerprints of every moved whole class, with an
   explicit exception map that is empty by default. Reject duplicate identities,
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
   hash/cache/timing seams.
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
    behavior without making the cache or timing file a public compatibility API.

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

- [ ] AC-1: Runner tests prove per-file child elapsed measurements, aggregate service time, bounded top-10 output, safe byte-size/name proxy ordering, and exact executor submission order for each deterministic schedule candidate.
- [ ] AC-2: Successful complete runs attempt to persist the optional validated `durations_s` map; ordinary full runs read the cache once and may reuse valid timings on hash mismatch or `--no-cache`, while malformed containers/entries and stale keys degrade independently, cache write failure remains nonfatal, and only matching hash/result can authorize a skip.
- [ ] AC-3: The frozen pre-change identity set and normalized whole-class AST fingerprints exactly equal the post-move set, the exception map is empty unless separately reviewed, skip count is unchanged, each shard discovers and executes its exact nonempty expected subset in focused isolation, the shard union equals the frozen set, no test module imports/executes another test module, both known consumers use pure support, and delete-plus-padding, duplicate/omit, assertion-to-`pass`, and new-skip mutants are caught. If measurement rejects sharding, this AC records that disposition and the unchanged frozen inventory instead.
- [ ] AC-4: Repeatable `--file <basename>` selection is fully validated before hashing/cache/timing access, runs only requested valid files, rejects every invalid selector class and `--file`+`--no-cache`, labels output as focused, calls no hash/cache/timing seams, leaves the cache byte-identical, and positive call-order spies prove every named canonical lock/index/cleanup/subprocess/artifact/release seam executes.
- [ ] AC-5: Existing cache-hit, cache-miss, `--no-cache`, locking, index exclusion, timeout, environment, artifact, and failure-reporting regressions remain green for the unchanged canonical invocation.
- [ ] AC-6: External invocation-to-exit evidence records the frozen original-source baseline plus the instrumented pre-optimization and post-change series, each with one warm-up and at least three samples and the applicable environment, digest, count, skip, internal timing, and service-time fields; a forced-skip control proves nonzero skip aggregation, all post-change runs are green with no new skips, and the median meets 25% or carries the bounded operator disposition from Requirement 12.
- [ ] AC-7: A post-layout alphabetical bootstrap emits a complete digest-bound timing manifest only after a green artifact-clean run; counterbalanced alphabetical and timing-guided controls then run through one unchanged source artifact with that byte-identical read-only manifest and no production cache calls. Missing current-file durations invalidate the comparison; the measured faster deterministic schedule is selected and the result includes makespan and aggregate worker service time.
- [ ] AC-8: Testing architecture and contributor verification docs state when focused runs are appropriate and preserve one full canonical isolated run as the delivery authority.
- [ ] AC-9: Docs lint and `git diff --check` pass, and no bytecode, runner state, dashboard process, or index artifact is left in the tracked tree.

## Tasks

- [ ] After `1tmb1` finishes, freeze source/file digests, exact test identities and class fingerprints, skips, and environment; record the original-source external baseline before any runner edit.
- [ ] Extend `_run_file` and the result model with elapsed time; add bounded slow-file reporting.
- [ ] Freeze the telemetry-only runner and record the instrumented pre-optimization per-file distribution before any scheduling or shard edit.
- [ ] Extend the existing last-green cache with advisory successful-full-run timing data and safe parsing.
- [ ] Add a benchmark-only deterministic schedule control, compare alphabetical and timing-guided candidates on identical source/fixed timing input, and select the measured winner.
- [ ] Add repeatable `--file <basename>` focused selection with pre-hash validation and complete hash/cache/timing isolation.
- [ ] Run the critical-path/Amdahl feasibility gate; only if it passes, census external consumers, extract pure non-discovered support, and partition `test_server_tools.py` into the minimum measured 2–6 domain shards.
- [ ] Add inventory, scheduling, cache, selector, mutation/falsification, and safety-path regressions.
- [ ] Freeze the final file layout, run the uncounted alphabetical manifest bootstrap, then run the counterbalanced schedule controls and select the measured faster ordering.
- [ ] Run and record at least three frozen post-change full-suite benchmarks.
- [ ] Update testing architecture and contributor verification documentation.
- [ ] Run the canonical suite, docs lint, diff check, and stray-artifact/bytecode checks.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Original baseline and runner telemetry | performance-reviewer | `1tmb1` complete and shared test corpus settled | Freeze original source/inventory and external baseline, then instrument only and capture the pre-optimization distribution. |
| Scheduling and focused mode | framework-engineer | Baseline and runner telemetry | Shared ownership of `run_tests.py`; serialize edits. |
| Server-tool shard decomposition | test-engineer | Baseline, runner telemetry, and feasibility gate | Starts only if measurement authorizes it; then use the minimum bounded shard count. |
| Contract and regression review | qa-reviewer | Scheduling; shard decomposition | Prove cache isolation, inventory, safety-path parity, and mutant detection. |
| Post-change benchmark and docs | performance-reviewer, docs-contract-reviewer | All implementation work | Benchmark before claiming improvement; reconcile canonical evidence wording. |


## Serialization Points

- Do not capture evidence or edit the runner/test corpus until `1tmb1` finishes and no concurrent writer remains. Freeze the original source/inventory and external baseline before the telemetry edit; after telemetry only, freeze and capture the pre-optimization per-file distribution before moving any test body or changing scheduling.
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


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-26 | Deliver telemetry and focused mode; select scheduling and physical sharding only after controlled measurement. | The original plan inferred a serial-tail cause from size/count and contradicted its own measured-winner AC. Measurement is the authority. | Mandating longest-first and sharding up front was rejected as premature optimization. |
| 2026-07-26 | Preserve file-level subprocess isolation and the six-worker cap. | Isolation prevents shared-module-state collisions; the cap already encodes observed CPU/I/O saturation above six. | Monolithic discovery and simply adding workers were rejected as correctness/performance regressions without new evidence. |
| 2026-07-26 | Defer dependency-aware per-file result caching. | Dynamic imports, generated assets, seeds, and shared fixtures make invalidation materially harder to prove than scheduling and physical sharding. | A per-file cache could be reconsidered only with an explicit dependency authority and false-hit probes. |
| 2026-07-26 | Target a measured 25% median improvement; after the one permitted rebalance, any miss requires explicit operator disposition accepting the measured gain, narrowing the target, or reverting performance-only complexity. | The benefit must be observable on the real suite without turning an infeasible target into an endless correction loop. | A fixed 2× promise was rejected as unjustified; a no-threshold benchmark and unbounded correction were rejected because either could ship unjustified complexity. |
| 2026-07-26 | Bound correction to one shard rebalance and then an explicit operator decision. | Prevent an optimization wave from expanding indefinitely when the measured target is infeasible. | Repeated unbounded reshaping was rejected. |
| 2026-07-26 | Bootstrap the schedule-control timing manifest after the final file layout. | Pre-shard timings name the monolith and cannot fairly compare a post-shard timing-guided schedule; the fixed control input must cover every current file. | Reusing pre-shard timings or allowing source-size proxy values to decide the schedule was rejected as circular/vacuous evidence. |


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
