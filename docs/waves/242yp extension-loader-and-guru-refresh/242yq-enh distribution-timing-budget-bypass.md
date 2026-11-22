# Distribution timing-budget bypass

Change ID: `242yq-enh distribution-timing-budget-bypass`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-22
Wave: 242yp extension-loader-and-guru-refresh

## Rationale

The Waveforge distribution reports that `test_server_context_efficiency.py::test_repeated_warm_estimator_and_projection_budgets` fails 5 of 6 full runs on its machines, which blocks its release gate. The failing row is the lifecycle flush/projection loop: p95 32 to 34 ms against an effective budget of about 25.2 ms. Quiet runs reach 21.3 ms of the 25 ms nominal budget. That loop makes durable SQLite writes, but the test's contention factor comes from `_contention_probe`, a CPU-only busy loop, so disk contention is invisible to it. With 4 background fsync writers, Waveforge measured flush p95 at 91 to 101 ms while the factor stayed at about 1.01. Upstream has not reproduced the failure; these figures are the distribution's reported observations.

On 2026-11-22 the operator decided to keep the timing-budget test in core Wavefoundry, unchanged in the default run, and to let a distribution disable timing-budget tests, because distributions run on varied machines with different performance criteria. The coordinator declined an I/O-calibrated probe and declined raising the budget.

## Product Intent

A distribution maintainer whose machines cannot meet upstream throughput budgets can commit one reviewable declaration in the distribution's own tree. After it, every throughput-budget assertion in the suite reports as SKIPPED with a reason that names that declaration, while every other assertion in the same tests still runs, and the distribution's release qualification still produces complete reports. Before this change the maintainer's only options are a red release gate or a local edit to upstream test files.

Upstream behavior does not change. The upstream default run executes every budget. The framework's own profile assets cannot declare the bypass, and a test fails if any profile asset in this repository declares it. Release qualification compares skips exactly as it does today. Complexity, hang and denial-of-service guards stay on in every tree. AC-2 and AC-7 test the intended outcome (each throughput bound skips with the named reason, and qualification accepts the resulting reports); AC-1, AC-3 and AC-4 test the boundaries.

## Requirements

1. **Declaration seam.** The bypass is declared by a top-level key `skip_timing_budgets` in the distribution's active profile asset. That asset is the single `tests/fixtures/profiles/<name>.json` marked `"active": true`, which `expected_profile` in `tests/record_layout_support.py` already reads. The value must be a one-line string of at most 200 characters that states the distribution's reason. A one-line string is non-empty and contains no line break: `value.splitlines() == [value]`. The existing asset rules stay unchanged, including the non-empty `modules` object.
2. **Active asset only.** `load_profile` in `tests/record_layout_support.py` must refuse, with `ProfileInvalid` naming `skip_timing_budgets`, an asset that carries the key without `"active": true`, and an asset whose value is not a valid reason string. The reader takes the reason from the base layer (the active asset) only and never from the run-mode layer named by `WAVEFOUNDRY_TEST_PROFILE`. It propagates `ProfileInvalid` and never turns a load error, such as an inactive asset carrying the key, into `None`. As a consequence, a run-mode layer and the framework's own `second.json`, `declared.json` and `prompt-names.json` cannot declare the bypass.
3. **No environment variable.** No environment variable enables the bypass. Reason: a stray shell value would silently skip budgets in the upstream default run, the hazard for which `run_tests.py` already refuses a receipt-writing run while `WAVEFOUNDRY_TEST_PROFILE` is set. An environment variable would also not be reviewable in the distribution's tree, and the committed asset already gives the distribution its switch.
4. **One shared helper with unique labels.** `tests/perf_budget_policy.py` provides the one shared timing-budget helper. Every census bound in Requirement 6 asserts through it, with a label. Each call's label must be unique within its test: the helper must refuse, at call time and with or without a declaration, a label already used in the same test, so no two bypass skips in one worker share an identity. Without a declaration the helper asserts the bound exactly as the site does today (same comparison, same bound, same message content). With a declaration it does not evaluate the bound. Instead it records a unittest subtest skip for that label (for example `subTest(timing_budget=<label>)` plus `skipTest`), so the test continues and its other assertions still run. Unittest records a skip raised inside `subTest` and continues the test body. The planner executed this on Python 3.14.8, and the red-team confirmed it on Python 3.11.17 (`execution_status: executed`).
5. **Skip reason.** The skip reason is exactly `timing-budget bypass: declared by tests/fixtures/profiles/<name>.json: <declared reason>`, with `/` separators on every platform.
6. **Census rule and set.** A timing budget in this change's sense is a throughput budget. It compares a measured wall-clock duration of code under test on ordinary input, which completes by doing its work, against a fixed upper bound. The derived set governs. It excludes:
   1. liveness bounds, where the path under test ends by a deadline, timeout, kill, cancellation or a fail-fast refusal on a busy resource;
   2. complexity, hang and denial-of-service guards, where the bound proves that pathological or maximum-size input cannot cause a super-linear or unbounded slowdown;
   3. lower bounds and relative bounds (a ratio of two timings measured in the same run);
   4. assertions on synthetic elapsed values, such as the `test_perf_budget_policy.py` threshold tests, which must run against the assertion core with no bypass;
   5. operator-run eval scripts (`sqlite_*_eval.py`, `vector_*_eval.py`) that report budgets but assert none in the suite.

   The planner ran the census as an AST scan of every `.py` under `.wavefoundry/framework/scripts/` (`execution_status: executed`). The scan found assertions over values derived from `time.perf_counter`, `time.monotonic` or `time.time`. It also found every `_contention_probe`, `p95`, `budget` and `perf_budget_policy` call site. The census has 8 throughput tests with 11 bounds. Each bound's label is the subtest label of its bypass skip:

   | # | Test | Labels (one bypass skip each) |
   | - | ---- | ----------------------------- |
   | 1 | `tests/test_server_context_efficiency.py::test_repeated_warm_estimator_and_projection_budgets` | `10-source warm`, `50-source warm`, `lifecycle flush/projection warm` |
   | 2 | `tests/test_server_context_efficiency.py::test_idle_projection_poll_is_bounded_and_does_not_scan_docs` | `1000 idle projection polls` |
   | 3 | `tests/test_memory_eval.py::test_lexical_evaluation_has_registered_contention_safe_budget` | `1000-record memory lexical evaluation` |
   | 4 | `tests/test_indexer.py::test_10k_rows_sub_second` (through `_scale`) | `100K-row drift detection` |
   | 5 | `tests/test_indexer.py::test_100k_rows_contention_safe_budget` (through `_scale`) | `100K-row drift detection` |
   | 6 | `tests/test_graph_indexer.py::test_line_scan_cost_bound_and_build_log` | `20000-def line scan` |
   | 7 | `tests/test_lexical_ranking_eval.py::test_the_whole_calibration_pass_stays_inside_the_runtime_budget` | `calibration pass runtime` |
   | 8 | `tests/test_memory_records.py::test_warm_path_call_counts_and_latency_are_bounded` | `first advisory call`, `warm advisory call` |

   Tests 4 and 5 share a label, but each label is unique within its own test, so their skip identities differ. The implementer re-runs the census against the tree at implementation time. A site added or removed since planning is reconciled with the rule and recorded in the Progress Log.
7. **Excluded sites stay as they are.** These sites stay outside the helper, unchanged, and are never skipped by the bypass. Line numbers are as of planning.
   1. Complexity, hang and denial-of-service guards (9 tests): `test_navigation_glob.py::test_many_double_star_segments_stay_fast`, `test_extension_tool_modules.py::test_call_parsing_is_bounded`, `test_techdocs_audit_lib.py::test_the_backtracking_ceiling_is_measured_at_its_own_boundary`, `test_techdocs_audit_lib.py::test_adjacent_floating_prefixes_collapse_without_reducing_source_budget`, `test_techdocs_audit_lib.py::test_a_subject_that_cannot_name_a_file_is_never_matched`, `test_techdocs_audit_lib.py::test_a_pathological_pattern_cannot_wedge_the_matcher`, `test_techdocs_audit_lib.py::test_a_symlink_cycle_terminates_in_bounded_time`, `test_scanner_input_limits.py::test_decoded_size_just_under_cap_scans_completely_with_full_ruleset` and `test_upgrade_wavefoundry.py::test_free_text_placeholders_use_bounded_quantifiers`.
   2. Liveness bounds (27 sites): `test_betterleaks_engine.py` (129), `test_child_tee.py` (451, 575), `test_context_efficiency.py` (672), `test_lifecycle_mutation_lock.py` (698, 869), `test_mcp_lifecycle.py` (226, 281, 498), `test_model_download_deadline.py` (77, 169, 323), `test_review_evidence.py` (2725, 2753), `test_sensor_runner.py` (80), `test_setup_index.py` (3381), `test_startup_install.py` (238), `test_subprocess_util.py` (343), `test_techdocs_audit_lib.py` (1292), `test_tensorwell_client.py` (557, 1061, 1138, 1271), `test_tree_kill_routing.py` (720, 822) and `test_upgrade_wavefoundry.py` (9842, 9868).
8. **Census enforcement.** A pin test lists the 8 census test ids. For each, it asserts by AST that the test body, or a helper the body calls (`_scale`), calls the shared helper. For each of the 9 guard tests in Requirement 7, it asserts that the body does not call the helper. It does not detect a new, unrouted budget elsewhere (see Decision Log).
9. **Upstream accident guard.** A test fails if any profile asset in this repository's `tests/fixtures/profiles/` declares `skip_timing_budgets`. It runs through `upstream_fixture_support.source_repository_fixture` (or the same `fixtures_required` check). That check is true only where `docs/workflow-config.json` sets `testing.upstream_fixtures_required`, which is this repository. In a distribution's tree the test skips with the existing upstream-only reason, and both of the distribution's qualification runs skip it alike.
10. **Qualification.** `qualification_report.py` and `qualification_worker.py` do not change. A distribution's default and profile runs read the same committed active asset, so both reports carry the same bypass skips and compare equal under the existing rule. Requirement 4 keeps every skip identity in a worker unique, so `worker_detail` accepts the worker as complete. Upstream has no active asset, so upstream reports carry no bypass skip. A candidate carrying a bypass skip that its default baseline lacks is refused by the existing "unexpected second-profile skip" rule.
11. **Platforms.** Windows, macOS, Linux and WSL2 behave identically: the change is pure-Python test support with no process, path-separator or filesystem dependence beyond reading one JSON asset, and the reason always uses `/`.

## Scope

**Problem statement:** a distribution has no reviewable way to stop upstream throughput budgets from failing its release gate on machines with different performance characteristics.

**In scope:**

- The `skip_timing_budgets` key, its validation and its reader in `tests/record_layout_support.py`.
- The shared helper in `tests/perf_budget_policy.py`, with `assert_within_budget` and `assert_operation_within_budget` routed through it, and its duplicate-label refusal.
- Routing the 8 census tests (11 bounds) through the helper.
- The census pin test (Requirement 8) and the upstream accident guard (Requirement 9).
- Tests for the helper, the declaration rules and the qualification boundary, including one routed census worker run through the real qualification path.
- Distribution documentation in `docs/architecture/testing-architecture.md`: the Expected profile and Default-profile-only entries under "Profile-Aware Fixtures and the Second-Profile Run", and the "Performance-Test Budget Policy" section.
- Distribution documentation in `docs/contributing/build-and-verification.md` (Packaging profile qualification).
- A CHANGELOG `[Unreleased]` entry under a new `### Added` heading.

**Out of scope:**

- Changing any budget value, the `_contention_probe` calibration, or adding an I/O-calibrated probe (declined by the coordinator).
- Skipping or scaling complexity, hang and denial-of-service guards, or liveness bounds (Requirement 7).
- Any change to `qualification_report.py`, `qualification_worker.py` or `run_tests.py`.
- A guard that detects a new, unrouted wall-clock bound anywhere in the suite (see Decision Log).
- Production code under `.wavefoundry/framework/scripts/` outside `tests/`.

## Acceptance Criteria

- [x] AC-1: In this repository's default run, with no declaration, each of the 11 census bounds executes through the shared helper, and no test reports a `timing-budget bypass:` skip. Oracle: for each census label in turn, a focused run with the helper's comparison forced to fail for that label only makes its test fail with an assertion error at that label, not a skip. Under current code the sites do not call a shared helper, so forcing it fails none of them.
- [x] AC-2: With an active profile asset declaring `skip_timing_budgets`, the bypass skips are exactly the 11 in the Requirement 6 table: test 1 reports three, test 8 reports two, and each other census test reports one. Each skip's id is `<test id> (timing_budget='<label>')` with that row's label, and its reason is exactly `timing-budget bypass: declared by tests/fixtures/profiles/<name>.json: <declared reason>`. A missing, extra or relabelled skip fails, so an implementation that leaves the `lifecycle flush/projection warm` bound unrouted fails. The other assertions still run: in `test_warm_path_call_counts_and_latency_are_bounded`, a forced failure of a non-budget assertion still fails the test under the bypass. Under current code no skip is reported.
- [x] AC-3: Under the same declared bypass, a non-budget test is unaffected. Oracle:
   1. `test_perf_budget_policy.py`'s threshold tests, the guard tests `test_techdocs_audit_lib.py::test_a_pathological_pattern_cannot_wedge_the_matcher` and `test_navigation_glob.py::test_many_double_star_segments_stay_fast`, and the liveness tests `test_review_evidence.py::test_automatic_publication_probe_fails_fast_on_same_process_thread` and `test_subprocess_util.py::test_timeout_kills_the_grandchild_and_returns_promptly` run and report no skip;
   2. the census pin test (Requirement 8) passes, and fails when one census test stops calling the helper or one guard test starts calling it;
   3. a second helper call with a label already used in the same test raises at call time, with and without a declaration.

   Under current code there is no helper and no pin test, so points 2 and 3 fail.
- [x] AC-4: Upstream qualification is unchanged. Oracle:
   1. `load_profile` refuses, with `ProfileInvalid` naming `skip_timing_budgets`, a non-active asset that carries the key, so neither `--qualify-profile second` nor `--qualify-profile declared` nor a `WAVEFOUNDRY_TEST_PROFILE` run-mode layer can declare it, and the reader raises rather than returning `None` when such an asset is present;
   2. the upstream accident guard (Requirement 9) passes in this repository and fails when any asset in `tests/fixtures/profiles/` declares the key;
   3. `qualification_report.compare` refuses a candidate whose bypass skip is absent from its default baseline, and accepts a pair where both reports carry the same bypass skips.

   Under current code, point 1 fails because an unknown top-level key is accepted silently, and the guard in point 2 does not exist.
- [x] AC-5: `docs/architecture/testing-architecture.md` (the Expected profile and Default-profile-only entries, and the "Performance-Test Budget Policy" section) and `docs/contributing/build-and-verification.md` state the declaration key and its active-asset-only rule. They also state the unique-label rule, the skip reason format and the census rule with its exclusions. They state that no environment variable exists and that the framework's own assets never declare the key. CHANGELOG `[Unreleased]` records the change under `### Added`, following the existing entry style. The documents this change edits validate with `wf_validate_docs`.
- [x] AC-6: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.
- [x] AC-7: A routed census worker run through the real qualification path produces a complete report. Oracle: in a scratch copy of the scripts tree with an active asset declaring `skip_timing_budgets`, `test_server_context_efficiency.py` and `test_memory_records.py` run under `qualification_worker`. The test may instead use `run_tests.py --qualify-profile` on that copy. Their skip detail then passes `qualification_report.worker_detail` with `complete` true and no issues. With the duplicate-label refusal removed and a label repeated, the same run reports `duplicate skipped-test identity`. Under current code the census tests produce no bypass skips, so the oracle fails.

## Tasks

- [x] Re-run the census against the current tree with the Requirement 6 rule; record any difference in the Progress Log.
- [x] Add the `skip_timing_budgets` validation to `_profile_errors` and a reader in `tests/record_layout_support.py` that returns the active asset's reason (or `None` when no active asset declares it) and propagates `ProfileInvalid`.
- [x] Add the shared helper to `tests/perf_budget_policy.py` with the duplicate-label refusal; route `assert_within_budget` and `assert_operation_within_budget` through it; keep the `test_perf_budget_policy.py` threshold tests on the assertion core with no bypass.
- [x] Route each of the 11 census bounds through the helper with its Requirement 6 label, without changing any bound, comparison or message content.
- [x] Add the census pin test and the upstream accident guard.
- [x] Add tests for AC-1 to AC-4 and AC-7 (helper with and without a declaration, duplicate labels, declaration validation, the compare pair, the qualification worker run).
- [x] Update `docs/architecture/testing-architecture.md` and `docs/contributing/build-and-verification.md`.
- [x] Add the CHANGELOG `[Unreleased]` entry under a new `### Added` heading.
- [x] Run the change's own suites and `wf_validate_docs`.

## Agent Execution Graph

A sequence: declaration and helper first, then the census routing and tests, then docs and CHANGELOG.

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| declaration-and-helper | implementer | none | `record_layout_support.py`, `perf_budget_policy.py` |
| census-routing | implementer | declaration-and-helper | the 8 census tests |
| tests | implementer | declaration-and-helper | AC-1 to AC-4, AC-7, pin and accident guard |
| docs-and-changelog | implementer | census-routing | AC-5 |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/record_layout_support.py`
- `.wavefoundry/framework/scripts/tests/perf_budget_policy.py`
- `.wavefoundry/framework/scripts/tests/test_perf_budget_policy.py`
- `.wavefoundry/framework/scripts/tests/test_profile_support.py`
- `.wavefoundry/framework/scripts/tests/test_qualification_report.py`
- `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py`
- `.wavefoundry/framework/scripts/tests/test_memory_eval.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_lexical_ranking_eval.py`
- `.wavefoundry/framework/scripts/tests/test_memory_records.py`
- `docs/architecture/testing-architecture.md`
- `docs/contributing/build-and-verification.md`
- CHANGELOG.md at the repository root, shared with sibling specs 241l1 and 241l2 in wave 242yp.

No other file overlaps the sibling specs: 241l1 owns `upgrade_extensions.py` and `tests/test_upgrade_protocol.py`, and 241l2 owns `render_agent_surfaces.py` and `tests/test_render_agent_surfaces.py`.

## Affected Architecture Docs

`docs/architecture/testing-architecture.md` changes in two places:

1. The Expected profile and Default-profile-only entries under "Profile-Aware Fixtures and the Second-Profile Run" gain the declaration key, its active-asset-only rule and the reader's error handling.
2. The "Performance-Test Budget Policy" section gains the shared helper, the unique-label rule, the throughput census rule and the always-on guards.

No other architecture doc changes; the change is confined to test support with no production boundary or data-flow impact.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Upstream default behavior must not change. |
| AC-2 | required  | The intended outcome for distributions, bound by bound. |
| AC-3 | required  | The switch must mean throughput budgets only. |
| AC-4 | required  | Release qualification must not be broken or laundered. |
| AC-5 | important | Distributions need the contract written down. |
| AC-6 | required  | Change-local verification. |
| AC-7 | required  | The distribution's qualification must accept the bypassed reports. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-22 | Spec planned; census executed by AST scan. | 17 timing-budget tests, 27 liveness sites excluded. |
| 2026-11-22 | Readiness repair r3 (cycle 2) for `242yq-qa-r3-per-bound-skip-oracle`, `242yq-CR-R3-1-duplicate-subtest-skip-identity` and `242yq-bypass-skip-identity-collision`: unique labels with a call-time refusal, an exact per-bound skip table in AC-2, and AC-7 through the real qualification path. The census is narrowed to throughput budgets. The repair adds the census pin, the upstream accident guard and the reader's error handling. The implementer rechecked each of the 17 earlier items against the narrowed rule. | 8 throughput tests with 11 bounds; 9 guard tests and 27 liveness sites excluded. `repair_start` events recorded in cycle 2, because cycle 1 was already aggregate-complete. |
| 2026-11-22 | Implemented. `record_layout_support.py` validates the key (active asset only, one-line reason of at most 200 characters) and adds `timing_budget_bypass_reason`, which reads only the active asset and propagates `ProfileInvalid`. `perf_budget_policy.py` adds `timing_budget` with the duplicate-label refusal and the never-bypassed cores `check_within_budget` and `check_operation_within_budget`, which the threshold tests now call. The 11 bounds are routed with their table labels. New tests cover the helper, the census run in a child (AC-1 forced failure at each call, AC-2 exact skip set), the census pin, declaration validation, the accident guard, the compare pair and the AC-7 worker run. Docs and CHANGELOG are updated. Re-running the census found no site added or removed since planning. | Focused runs with `run_tests.py --file`: `test_perf_budget_policy.py` 16 ok, `test_profile_support.py` 88 ok, `test_qualification_report.py` 45 ok, `test_memory_eval.py` 26 ok, `test_memory_records.py` 235 ok, `test_lexical_ranking_eval.py` 19 ok, `test_graph_indexer.py` 572 ok, `test_indexer.py` 424 ok. `test_server_context_efficiency.py` failed once in the 9-file parallel run, on the unchanged `lifecycle flush/projection warm` bound (p95 30.9 ms against an effective 25.95 ms, factor 1.038). That is the reported Waveforge failure, executing upstream as designed. The file then passed 147 of 147 in two isolated runs. AC-3 point 1 was executed ad hoc through the census child runner under a declared bypass: the two guard tests, the two liveness tests and one threshold test reported no skip, and the bypass reader was never consulted. |
| 2026-11-22 | Gapfill: retrieval mixed tools. MCP `code_read`, `code_keyword` and `code_search` were loaded and used, but `code_search` returned no results for test files (the code index excludes tests by default). Most reads of test files and the census therefore used shell `grep`, `sed` and an AST script in the session scratchpad. | Not applicable. |
| 2026-11-22 | The coordinator's full suite failed in `test_profile_literal_census.ProfileLiteralCensusTests.test_every_literal_is_marked_or_allowlisted`: the new fixtures in `test_profile_support.py` and `test_qualification_report.py` used the default-layout literal `"docs/waves"` as their asset constant. Both fixtures now name `record_paths.MAX_DEPTH` at its shipped value, taken from `SHIPPED_DEFAULTS` in `test_profile_support.py`. The constant's value has no effect on these tests. | `run_tests.py --file`: `test_profile_literal_census.py` 8 ok, `test_profile_support.py` 88 ok, `test_qualification_report.py` 45 ok. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-22 | Keep the budget test unchanged in the default run and let a distribution disable timing-budget tests. | Operator decision (2026-11-22), relayed by the coordinator: distributions run on varied machines with different performance criteria. | I/O-calibrated contention probe (declined by the coordinator); raising the budget (declined by the coordinator). |
| 2026-11-22 | Declare the bypass in the distribution's active profile asset. | Planner default. The active asset is the existing committed, distribution-owned seam that the test suite already reads, and a distribution adds it without editing an upstream file, so the bypass is reviewable in its tree. Efficacy: replaying the Waveforge failure, the `lifecycle flush/projection warm` bound skips with the named reason, so the release gate no longer fails on it; the skip is reported, never silent. | A constant in `vocabulary_profile.py` or `mcp_tool_extensions.py`: weakness, those modules carry product vocabulary and tool declarations, and editing them changes upstream files. A fork-editable test module like `container_fixture_profile.py`: weakness, the distribution edits an upstream file and merges conflict on every upgrade. An environment variable: weakness, not reviewable, and a stray value silently skips upstream budgets. |
| 2026-11-22 | Skip at the assertion through one shared helper with a subtest skip, not at the test with a decorator. | Planner default. Several census tests mix a budget with correctness assertions (call counts, sample checks); a test-level skip would drop those checks on the distribution's machines. A subtest skip keeps them and still reports SKIPPED. | A `@timing_budget` test decorator like `default_profile_only`: weakness, it skips every other assertion in the census tests. |
| 2026-11-22 | Timing budgets exclude liveness bounds. | Coordinator decision (2026-11-22, reversible default): "no. Keep the bypass to the 17 timing-budget tests." Liveness bounds (timeout, kill and fail-fast bounds) check that something completes or fails promptly. Skipping them could hide a hang, which is a correctness signal, not a performance criterion. A tight liveness bound that flakes on slow machines gets a wider bound instead. | Skip every wall-clock upper bound: weakness, a distribution would lose timeout and kill coverage. |
| 2026-11-22 | The bypass covers throughput budgets only. The complexity, hang and denial-of-service guards stay always on and unchanged: pathological pattern, symlink cycle, backtracking ceiling, adjacent floating prefixes, unrepresentable subject, glob, scanner, parser and bounded quantifiers. | Operator decision (2026-11-22): "agreed in your scope change ... that's the right call". The coordinator proposed it from the red-team's strongest challenge in round 3. These guards protect correctness against exponential or unbounded slowdowns, like the liveness bounds already excluded, and Waveforge reported no failure in them. The implementer rechecked each earlier item. The red-team's throughput list names the same 8 tests that this census keeps. | Skip all 17 earlier census tests: weakness, a distribution loses hang and ReDoS guards. Scale those guards' bounds 10x under the bypass (red-team alternative): declined by the coordinator, because nobody asked for it and it adds a new rule. |
| 2026-11-22 | Each helper call carries a label unique within its test, and the helper refuses a repeated label at call time. | Coordinator repair instruction for the three r3 findings. Repeated labels give repeated skip identities, and `qualification_report.worker_detail` then reports `duplicate skipped-test identity`, so the distribution's qualification would fail. Refusing at call time also catches the mistake in the upstream default run. | Derive a unique label automatically (for example from a call counter): weakness, labels would depend on call order, and the AC-2 table could not name them. |
| 2026-11-22 | Adopt the code-reviewer's cheap census pin (8 census tests call the helper; 9 guard tests do not) and decline detection of new, unrouted budgets. | Planner default, from `code-reviewer-readiness-r3.md` advisory 2. The pin is one AST test with fixed lists, and it catches unrouting, removal and accidental routing of a guard. Detecting new budgets needs an allowlist of 27 liveness sites and every new liveness bound, or a second helper for liveness bounds. That is ongoing upkeep the operator's reduced-work preference does not justify. A new unrouted budget fails loudly in a distribution rather than skipping silently. | An AST guard over all of `tests/` with a `(file, test function)` allowlist, or an `assert_liveness_bound` sibling marker: weakness, upkeep and a wider change. |
| 2026-11-22 | Add an upstream accident guard gated by `testing.upstream_fixtures_required`. | Coordinator repair instruction, from the red-team's Question 1. Without it, a new upstream asset marked active and declaring the key would skip the same budgets in every upstream run and launder qualification. The existing seam keeps the guard from failing in distributions. | Rely on review of any new active asset: weakness, nothing fails on the accident. |
| 2026-11-22 | Leave `qualification_report.py` unchanged. | Planner default. Both runs in a distribution read the same active asset, so their skip sets match under the existing rule; upstream has no active asset. | A bypass-skip count in the compare output: weakness, a new field with no reader. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Tight liveness bounds and complexity guards (for example `test_review_evidence.py` 0.25 s, `test_techdocs_audit_lib.py` 0.05 s) can still fail on slow distribution machines, because the bypass does not skip them. | Excluded by decision (Decision Log); a bound that flakes gets a wider bound in a separate change. |
| A new throughput budget added later without the helper is not skipped by the bypass. | The helper and census rule are documented in the "Performance-Test Budget Policy" section; the census pin covers only the listed tests (Decision Log). |
| A distribution with no edited constants must still give its active asset a non-empty `modules` object. | It can name one constant at its shipped value; the existing rule is unchanged. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
