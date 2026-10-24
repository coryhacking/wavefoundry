# Skip Upstream-Only Fixture Tests Outside the Source Repository

Change ID: `21ile-enh skip-upstream-only-fixture-tests-outside-source-repo`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-24
Wave: 21ilf waveforge-1-36-follow-ups

## Rationale

Some framework tests read content that exists only in this repository: evaluation corpora under `docs/evals/`, history records under `docs/waves/` and `docs/agents/history/`, and report artifacts under `docs/reports/`. A distribution that ships the framework without that content runs the same suite. These tests then fail although nothing in the framework is wrong.

A downstream distribution reports 27 test IDs, plus 2 report-path subtests, failing for this reason alone (listed under Scope). They are in seven files:

- `tests/test_graph_quality_eval.py`
- `tests/test_handler_modules.py`
- `tests/test_events_only_residue_census.py`
- `tests/test_lifecycle_gates_structure.py`
- `tests/test_render_agent_surfaces.py`
- `tests/test_review_policy.py`
- `tests/test_server_tools_lifecycle.py`

A plain skip-when-absent would also turn an accidental deletion in this repository into a silent pass.

## Product Intent

Distributions get a suite that skips, with a stated reason, the tests whose subject is this repository's own content, while this repository keeps failing loudly when such content goes missing. Before: those tests fail in every distribution. After: they skip there with `upstream-only fixture absent: <path>`, and here a missing fixture still fails. Boundaries: tests that build their own fixtures are unchanged; no test is deleted.

## Requirements

1. A shared test helper takes the fixture path the test already computes (including paths built from `record_paths` roots) and, if it exists, returns it.
2. The source-repository opt-in is a new explicit boolean, `testing.upstream_fixtures_required: true`, in this repository's `docs/workflow-config.json`. It is separate from `docs_lint.framework_internal_constants`, because a distribution that rebrands the framework source may check its own internal constants without hosting this repository's corpora and history. The key is added to the config's accepted keys if validation has a known-key set.
3. If the path is absent: with the key `true`, or with `docs/workflow-config.json` missing, unreadable, malformed or carrying a non-boolean value, the helper fails the test, naming the path and the cause; with the key absent or `false`, it calls `skipTest("upstream-only fixture absent: <path>")`. Distributions always ship the config, so a missing config fails closed.
4. The derived test set is mechanical: run the framework suite in a temporary copy of the framework and its tests with a `docs/workflow-config.json` that lacks the key and no upstream-only content; every test that fails there because a file under `docs/evals/`, `docs/waves/`, `docs/agents/history/` or `docs/reports/` (or the configured record roots) is missing is in the set. The distribution's 27 IDs are the set as found at planning. Each test in the set routes that read through the helper.
5. Platforms: paths resolve through `pathlib` with forward-slash relative inputs, so Windows, macOS, Linux and WSL2 behave the same.

## Scope

**Problem statement:** upstream-only fixture tests fail in distributions and would pass silently here if a plain skip were added.

**In scope:**

- The helper module under `tests/`.
- The census.
- Routing each test in the set through the helper.
- Tests of the helper.

**Out of scope:**

- Shipping corpora or history docs to distributions.
- A distribution that sets the new key `true` without hosting the content; the reply tells them the key means "this repository hosts the upstream fixtures".

The reported IDs, by file:

- `tests/test_graph_quality_eval.py`: `ClassificationControlScorerTests.test_the_control_directory_matches_the_files_on_disk`; all twelve `GraphParityBaselineFixtureTests` methods; all four `MoveRenameInvarianceTests` methods; `ReportSelfContaminationTests.test_the_shipped_report_paths_are_ignored`.
- `tests/test_handler_modules.py`: `HandlerPackagingAndEvaluatorTests.test_golden_symbol_and_content_anchors_resolve_and_stale_path_fails`, `test_memory_is_outside_measured_retrieval_closure`.
- `tests/test_events_only_residue_census.py`: `LocalRoleHistoryCensusTests.test_journal_payload_only_in_bounded_history`.
- `tests/test_lifecycle_gates_structure.py`: `LifecycleGateStructureTests.test_statements_this_change_leaves_alone_survive`.
- `tests/test_render_agent_surfaces.py`: `ReviewProtocolCarrierRegistryTests.test_self_host_ownership_contracts_cover_every_registry_destination`.
- `tests/test_review_policy.py`: `ReviewLoopFrictionPolicyTests.test_the_explicit_block_declares_a_target_containing_spaces`.
- `tests/test_server_tools_lifecycle.py`: the three `ImplementDependencyProducerTests` methods.
- The distribution's other host-specific failures.
- A known-failure list for the test receipt (declined, and answered in the reply).

## Acceptance Criteria

- [x] AC-1: In requirement 4's temporary copy, every test in the set reports skipped with the stated reason, and no test fails because an upstream-only file is missing. The skip count and any remaining failures, with their causes, are recorded in the Progress Log.
- [x] AC-2: Helper unit tests: present path returns it; absent with the key `true` fails; absent with the key absent or `false` skips; absent with the config missing, malformed or non-boolean fails. In this repository, with one fixture made absent to the helper's own existence probe, the routed test fails rather than skipping. Known-bad: a helper that skips unconditionally passes AC-1 and fails AC-2.
- [x] AC-3: This repository's `docs/workflow-config.json` sets the key `true`, and a test fails if it does not. A source-repository test cannot detect its own identity otherwise, so this pin is what keeps a removed key from turning every routed test into a silent skip here.
- [x] AC-4: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Write the helper and its tests (present, absent with opt-in, absent without opt-in, malformed config).
- [x] Re-run the census; route each test in the set through the helper.
- [x] Add the opt-in key, its config acceptance and the AC-3 pin.
- [x] Run AC-1 in a temporary copy and record the skip count in the Progress Log.
- [x] CHANGELOG Unreleased entry (Changed).

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| helper     | implementer | —          |       |
| routing    | implementer | helper     |       |


## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_graph_quality_eval.py`, `.wavefoundry/framework/scripts/tests/test_handler_modules.py`, `.wavefoundry/framework/scripts/tests/test_events_only_residue_census.py`, `.wavefoundry/framework/scripts/tests/test_lifecycle_gates_structure.py`, `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`, `.wavefoundry/framework/scripts/tests/test_review_policy.py`, `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `docs/workflow-config.json`, `docs/architecture/testing-architecture.md`

## Affected Architecture Docs

`docs/architecture/testing-architecture.md`: one paragraph on upstream-only fixtures and the source-repository opt-in.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | the distribution's request |
| AC-2 | required | protects this repository from silent skips |
| AC-3 | important | keeps new reads routed |
| AC-4 | required | change-local suites and docs |


## Progress Log


| Date       | Update  | Evidence |
| ---------- | ------- | -------- |
| 2026-10-24 | Planned | Waveforge 1.36.0 follow-up listing 27 IDs |
| 2026-10-24 | Readiness round 1 amendments: dedicated opt-in key; missing config fails closed; the set derived by a temporary-copy run; the census test replaced by the opt-in pin (AC-3); helper takes the computed path so `record_paths` roots work; the 27 IDs listed; Serialization Points narrowed. | readiness qa-reviewer, code-reviewer, security-reviewer, red-team, docs-contract-reviewer |
| 2026-10-24 | Readiness round 2 clarifications (Progress Log only): Requirement 4's temporary copy is the full working tree, including uncommitted edits and a `.git` (a `git worktree` or a copied checkout), with only `docs/evals/`, `docs/waves/`, `docs/agents/history/`, `docs/reports/` and the configured record roots removed, and a `docs/workflow-config.json` lacking the key. The set is the tests that fail in that copy and pass in the same copy with the content present (a differenced pair of runs), so membership is mechanical. The Decision Log's "reviewed per test" wording is superseded by this. `check_workflow_config` has no known-key check, so the key needs no acceptance edit. A `testing` value that is present but not an object fails closed like a non-boolean. The helper tests pin that a missing config fails closed, the deliberate opposite of `_framework_internal_constants_enabled`. The helper resolves the config from the repository root the tests use, not the current directory. The AC-3 priority rationale reads "pins the source-repository opt-in". | readiness code-reviewer, qa-reviewer and security-reviewer recheck |
| 2026-10-24 | Readiness architecture note: a test pins that `.wavefoundry/framework/install/workflow-config.defaults.json` never carries a `testing` key, so a future defaults edit cannot seed the source-repository opt-in into consumers. | readiness architecture-reviewer |
| 2026-10-24 | Readback: a test helper returns an upstream-only fixture path when present; when absent it fails (key true, config missing, unreadable, malformed, `testing` non-object, key non-boolean) or skips with `upstream-only fixture absent: <path>` (key absent or false). ACs 1-4. Scope: helper module, routing of the differenced-run set only, the opt-in key in `docs/workflow-config.json`, helper unit tests, AC-2 known-bad, AC-3 pin, defaults no-`testing` pin, one testing-architecture paragraph; no CHANGELOG, no files owned by sibling changes. Expected files: `tests/upstream_fixture_support.py`, `tests/test_upstream_fixture_support.py`, the seven routed test files, `docs/workflow-config.json`, `docs/architecture/testing-architecture.md`. | implementer |
| 2026-10-24 | Census (differenced pair): two rsync copies of the full working tree with `.git` (index, cache and logs excluded). Copy A unchanged; copy B with `docs/evals/`, `docs/reports/`, `docs/agents/history/` removed, `docs/waves/` emptied except `README.md`, `docs/plans/` emptied except `plan-template.md`, and a config lacking `testing`. `run_tests.py --no-cache` in each: A failed only `test_setup_index.py` (2 `NameError: READER_REQUIREMENT`, a sibling change mid-edit); B added 32 test IDs. The set is those 32: the 26 listed IDs other than `ReportSelfContaminationTests.test_the_shipped_report_paths_are_ignored` (it passes here: our ignore rules cover the report paths, so it is not in the set), plus 6 the distribution did not report because it hosts its own records: `IsChangeIdTests.test_accepts_every_admitted_id_in_this_repository`, `ScaffoldDeclaresNothingTests.test_an_authored_change_doc_never_blocks`, `DeclaredWaveTreeSweepTests.test_closed_declared_waves_match_committed_topology_snapshot`, `ReviewLoopFrictionPolicyTests.test_declaration_change_loses_no_lane_anywhere_in_the_corpus`, `DefaultProfileOnlyMarkerTests.test_repository_corpus_runs_under_declared_tools`, `FixturesYieldNoFindingsTests.test_scanning_the_fixtures_records_nothing`. Corpus reads route only when the corpus is short (a distribution with its own records still runs them); the profile test passes a helper skip on; the secrets test routes each ledger finding's file. | implementer |
| 2026-10-24 | AC-1: copy B re-run after routing (`run_tests.py --no-cache`, 12037 tests across 207 files): skipped 82 (59 before); `unittest -v` over the 12 routed files and the helper tests shows 23 skips reading `upstream-only fixture absent: <path>`: 20 routed methods, the `GraphParityBaselineFixtureTests` class skip (its 12 methods) and the 2 source-repository pins. No failure from a missing upstream-only file. Remaining failures: `test_setup_index.py` (2, the sibling change, also in copy A) and `test_profile_literal_census.py` (2 new record-root literals of mine, since replaced by `record_paths.WAVES_ROOT`; the census then passes in B). AC-2 known-bad in copy A: a helper that skips unconditionally, and one that skips whenever absent, each fail `test_upstream_fixture_support.py`. | implementer |
| 2026-10-24 | Gapfill: retrieval mostly via shell (`grep`, `sed`) over the known test files, because the census was a run, not a search, and the edits needed exact local context. | implementer |
| 2026-10-24 | Delivery notes: the derivation also routed `test_change_id_path_guard.py`, `test_docs_lint.py`, `test_secrets_prefix_collapse.py` and `test_profile_support.py`, and added `test_upstream_fixture_support.py` and `upstream_fixture_support.py`, beyond the Serialization Points; Requirement 4's differenced run governs membership. The opt-in key also gates 21ild's carrier census (noted in `docs/architecture/testing-architecture.md`). Corpus routes that apply only when the distribution's own corpus is short are a stated heuristic. | delivery review |
| 2026-10-24 | Final full suite after delivery repairs: `run_tests.py --no-cache` ran 12100 tests across 208 files, OK; the framework test receipt is current. | `scratchpad/21ilf-full-2.log`; `.wavefoundry/framework/test-cache.json` |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-10-24 | A dedicated explicit opt-in key, pinned true here | Explicit opt-in as wave 1yp0y chose; separate from `framework_internal_constants` because a source-rebranding distribution may enable that key without hosting our corpora (readiness primer question) | Reuse `framework_internal_constants` (would make such a distribution fail instead of skip); an environment variable (forgotten in CI, so silent skips); detect by file layout (the heuristic 1yp0y rejected); skip unconditionally (silent pass here) |
| 2026-10-24 | Derive the set by a temporary-copy run, not a literal-path census | 45 test files touch these roots and every target file also builds its own fixtures, so a grep census cannot tell them apart; the run finds exactly the reads that break | Literal-root grep with per-file exemption (exempts the files it guards); per-read allowlist (line-fragile) |
| 2026-10-24 | Mechanism efficacy | Replay: in the distribution the 27 IDs reach the helper, find their fixture absent and no opt-in, and skip. Here a deleted fixture fails. Control: the helper decides the outcome. Wrong flags: a test whose subject is framework behaviour but which happens to read history could be skipped there; the census rule limits the set to tests whose subject is this repository's content, reviewed per test. Cheaper path: the distribution's per-test fork edits, which they asked to drop. Measure: the distribution's next run reports these IDs skipped and drops its edits. | — |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The key is removed here and routed tests skip silently | AC-3 pins the key `true` in this repository; a malformed value or missing config fails rather than skips |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
