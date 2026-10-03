# Test Isolation After Module Eviction and a Full Core Schema Golden

Change ID: `1zltu-debt test-isolation-and-core-schema-golden`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-02
Wave: 1zls7 waveforge-defect-fixes

## Rationale

Two test defects Waveforge reported, both reproduced on 2026-10-02.

**(a) A test-order leak after module eviction.** `wf_server/server_impl.py` runs an eviction block at import (and on every `wf_reload_mcp`): it deletes `record_paths`, `vocabulary_profile`, `change_doc_checklist`, `lifecycle_lock` and the other listed modules from `sys.modules` so the next import loads current code. Any test that calls `load_server()` (`tests/server_tools_support.py`) therefore replaces those module objects. `tests/test_profile_support.py` `LocalizationHelperTests.test_waves_dir_and_rel_follow_the_loaded_layout` patches the `record_paths` object its module bound at import time (`mock.patch.object(record_paths, "WAVES_ROOT", ...)`), while `tests/record_layout_support.py` `waves_dir` and `waves_rel` import `record_paths` at call time. After `test_retired_change_kinds` (which calls `load_server()`) has run in the same process, the test patches a stale object, the helpers read the fresh one, and the assertion fails. In the default runner the two files usually run in different processes, so the failure depends on scheduling.

**(b) The core schema golden compares only names.** `tests/test_record_layout_lifecycle.py` `SchemaPinAndReloadTests.test_eight_lifecycle_tool_schemas_match_the_golden_fixture` compares only the sorted property names of eight lifecycle tools against `tests/fixtures/tool-surface-golden.json`. A changed type, a changed default, or a parameter that became required passes. The fixture already records full `inputSchema` objects (property schemas with `type`, `default` and `title`, and a `required` list).

Operator decision (2026-10-02) for (b): compare the core's parameters fully (types, defaults, required) and ignore extra OPTIONAL parameters an override adds; an added required parameter still fails.

## Requirements

1. **Patch through `sys.modules`.** `test_waves_dir_and_rel_follow_the_loaded_layout` patches the module the helpers will read at call time (for example `mock.patch("record_paths.WAVES_ROOT", ...)`, which resolves `record_paths` through `sys.modules` when the patch starts), not the object bound when the test module was imported.
2. **Census of the same pattern.** The implementer classifies every candidate site and records the predicate, counts and result in the Progress Log. Predicate: a `patch.object(<name>, ...)` or `mock.patch.object(<name>, ...)` call in a file under `.wavefoundry/framework/scripts/tests/` whose first argument `<name>` is bound, by `import X`, `import X as <name>` or `from <package> import X as <name>` (at module level or inside the test), to a module X that `server_impl` evicts: a module on its eviction list or a handler module named by `_PACKAGE_PURGE_KEYS` (the flat and `wf_server.` keys of `_FLAT_ALIASES` and `_RETIRED_FLAT_NAMES`, for example `memory_handlers` in `test_memory_records.py` around line 1451, `index_handlers` in `test_server_tools_retrieval.py` around lines 3547 and 3763, `upgrade_handlers` in `test_upgrade_reload_runner.py` around line 56). Aliased imports such as `import lifecycle_gates as gates` in `test_lifecycle_gates.py` count under the alias. The eviction list is `record_paths`, `vocabulary_profile`, `review_evidence`, `review_policy`, `lifecycle_lock`, `publication_control`, `context_efficiency`, `public_contract`, `gardener_metadata`, `change_doc_checklist`, `operator_identity`, `marker_namespaces`, `lifecycle_gate_support`, `lifecycle_gates`, `sensor_runner`, `index_source_guard`, `path_containment`, `mcp_tool_extensions`, `wave_lint_lib.*`. A planning grep on 2026-10-02 found 44 such sites in 14 files under the narrower name-only predicate; the widened count is recorded at implementation. A site is affected when the code under test resolves that module through `sys.modules` (an import at call time, or a module imported after an eviction) rather than through the same object the test patched. Each affected site is fixed the Requirement 1 way; unaffected sites are left alone with the reason recorded.
3. **Single-process regression.** A test runs the leaking pair in one interpreter: it calls `load_server()` and then `importlib.reload(srv)` (which runs the eviction block, as `test_record_layout_lifecycle.py` `test_record_paths_is_evicted_on_reload` does), asserts the precondition that `sys.modules["record_paths"]` is not the object `test_profile_support.py` bound at module level, and then exercises the Requirement 1 assertion, so the old `patch.object` form fails it and the fixed form passes. The Progress Log also records one run of `test_retired_change_kinds` followed by `test_profile_support` in a single `python3 -B -m unittest` process, before and after.
4. **Full core schema comparison.** For each of the eight tools, every property in the golden `inputSchema.properties` exists in the live schema with an identical property schema (type or `anyOf`, `default` presence and value, `title`), and the live `required` set equals the golden `required` set. A live property absent from the golden is allowed only when it is not in the live `required` list (an optional parameter an override adds); an added required parameter fails with a message naming the tool and parameter.
5. **The comparison is tested on synthetic schemas.** The comparison is a small helper in the test module, and a test drives it with a golden-shaped schema and four live variants: identical (passes), an extra optional parameter (passes), an extra required parameter (fails), and a changed type or default on a core parameter (fails).
6. **No fixture rewrite.** `tests/fixtures/tool-surface-golden.json` is not regenerated by this change; if the full comparison fails against today's live schemas, the implementer stops and reports the drift to the operator rather than updating the fixture.

## Scope

**Problem statement:** one test fails depending on test order because it patches a module object that the eviction block replaced, and the core schema golden misses type, default and required drift.

**In scope:**

- `tests/test_profile_support.py` (Requirement 1 and the regression test).
- Other test files the Requirement 2 census finds affected.
- `tests/test_record_layout_lifecycle.py` (Requirements 4 and 5).

**Out of scope:**

- The eviction block itself and `load_server()`.
- `tests/test_tool_surface_golden.py` and the golden fixture's content and generator.
- Product code: this change edits tests only.

## Acceptance Criteria

- [x] AC-1: `test_waves_dir_and_rel_follow_the_loaded_layout` passes when run after `load_server()` in the same process, and the new single-process regression test fails when the test is reverted to `mock.patch.object(record_paths, ...)` (mutation evidence recorded in the Progress Log).
- [x] AC-2: The Requirement 2 census is recorded with its predicate, the candidate count, the affected count and each affected site's fix; every affected site is fixed.
- [x] AC-3: The eight-tool golden test compares types, defaults, titles and the required set; the synthetic-schema test shows identical and extra-optional pass, extra-required and changed type or default fail.
- [x] AC-4: The full comparison passes against the live server and the unchanged `tool-surface-golden.json` (or, per Requirement 6, the drift is reported to the operator and this AC is held). A readiness probe on 2026-10-02 found the full core comparison already passes against today's golden, so no fixture rewrite is expected.
- [x] AC-5: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Reproduce the leak in one process (`test_retired_change_kinds` then `test_profile_support`) and record it.
- [x] Fix `test_waves_dir_and_rel_follow_the_loaded_layout` and add the single-process regression test; record the mutation result.
- [x] Run and record the Requirement 2 census; fix affected sites.
- [x] Add the schema comparison helper, its synthetic-schema test, and switch the eight-tool golden test to it.
- [x] Run the change's suites and docs validation.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| test-isolation | implementer | none | test_profile_support.py and census fixes |
| schema-golden | implementer | none | test_record_layout_lifecycle.py |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/tests/test_profile_support.py`
- `.wavefoundry/framework/scripts/tests/test_record_layout_lifecycle.py`
- `.wavefoundry/framework/scripts/tests/record_layout_support.py`

## Affected Architecture Docs

N/A: test-only change; no boundary, flow or product behaviour change. `docs/architecture/testing-architecture.md` is not edited unless the census finds the pattern widespread enough to warrant a note, which the implementer raises with the operator first.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The order-dependent failure is the reported defect. |
| AC-2 | important | The same pattern elsewhere would fail the same way. |
| AC-3 | required | Operator decision on the golden comparison. |
| AC-4 | required | The tightened test must hold against today's surface. |
| AC-5 | required | Standard verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-02 | Implemented. Requirement 1: `test_waves_dir_and_rel_follow_the_loaded_layout` now patches `mock.patch("record_paths.WAVES_ROOT", ...)`. Requirement 3: new `test_waves_helpers_follow_the_patch_after_the_server_evicts_record_paths` calls `load_server()`, `importlib.reload(srv)`, asserts `sys.modules["record_paths"]` is not the module-level object, then runs the Requirement 1 assertion. Requirements 4 and 5: `core_schema_drift(tool, golden, live)` in `test_record_layout_lifecycle.py` (every golden property identical live, live `required` equals golden, an extra live property allowed only when optional), driven by new `test_core_schema_drift_on_synthetic_schemas` (identical and extra-optional pass; extra-required, changed type, changed default, dropped default and a dropped required entry fail); the eight-tool golden test now asserts `core_schema_drift(...) == []`. Requirement 6: the full comparison passes against the live server and the unchanged `tool-surface-golden.json` (no drift, fixture untouched). Census (Requirement 2), predicate exactly as stated (a `patch.object`/`mock.patch.object` call under `tests/` whose first argument is a name bound by `import X`, `import X as name` or `from P import X as name`, at any scope, to a module on the eviction list, a `wave_lint_lib` module, or a `_PACKAGE_PURGE_KEYS` flat or `wf_server.` handler key): 111 candidate sites in 28 files before the fix (110 after; the narrower name-only planning grep found 44). Affected test (each candidate file run whole in one process twice, once as is and once with `load_server()` plus `importlib.reload(srv)` between import and run; affected = a site-holding test that fails only after the eviction): 5 sites in 3 files, all fixed by resolving the module at call time: `test_profile_support.py` (the Requirement 1 site); `test_secrets_validators.py` `test_failed_publication_keeps_guard_skipped_files_out_of_the_scan_cache` and `test_failed_publication_of_a_clear_does_not_pin_the_stale_row` (`patch.object(_sv, "update_scanner_skips")` while `scan_secrets` imports the scanner at call time; the two tests now bind `from wave_lint_lib import secrets_validators as sv` in the test body); `test_server_context_efficiency.py` `test_automatic_pass_does_not_starve_later_waves_after_retryable_failure` (two `patch.object(ce_handlers, "_project_context_efficiency_wave")` sites, now `patch("wf_server.context_efficiency_handlers._project_context_efficiency_wave")`). Unaffected, left alone: the other 106 sites (in 27 of the 28 files) pass identically with and without the eviction, because the code under test reaches the same object the test patched (both bound before the eviction, as in `test_docs_lint.py`, `test_context_efficiency.py`, `test_phase_gates.py`, `test_review_evidence.py`, `test_lifecycle_gates.py` `gates`/`review_evidence`), or the name is bound by an import inside the test or helper at call time (`test_indexer.py` `record_paths`, `record_layout_support.py` `vocabulary_profile`), or the test deliberately patches the old object (`test_upgrade_wavefoundry.py` `test_names_imported_from_the_old_record_paths_still_catch_what_it_raises`); `test_server_tools_lifecycle.py` (5 `review_policy` sites) was classified by running its three site-holding tests both ways after the whole-file run hit the 900 s harness timeout under parallel load. Outside the predicate, follow-up only (not fixed): the eviction run also failed `test_secrets_validators.py` `TestExceptionStatus.test_false_positive_below_threshold_user_already_in_list`, the inverse shape (`_run_check` patches `wave_lint_lib.secrets_validators.get_current_git_user_email` by string while calling the module-level-bound `check_hardcoded_secrets`). Base-mode failures seen identically in both modes under 8-way parallel load (lock and timing tests in `test_review_evidence.py`, `test_upgrade_wavefoundry.py`, `test_secrets_validators.py` `test_real_workers_publish_all_guards_without_serial_fallback`) are not eviction effects. Failing-first: before the fix, `test_retired_change_kinds` then `test_profile_support.LocalizationHelperTests` in one `python3 -B -m unittest` process failed `test_waves_dir_and_rel_follow_the_loaded_layout` (`/r/docs/waves != /r/docs/delivery/sets`); after the fix, `test_retired_change_kinds test_profile_support` in one process ran 88 tests OK. The secrets and context-efficiency tests failed after the eviction before their fix and pass both ways after it. Mutations (scratch copy, each fails a named test): M1 revert to `mock.patch.object(record_paths, ...)` fails `test_waves_helpers_follow_the_patch_after_the_server_evicts_record_paths`; M2 drop the required-set checks, M3 drop property-schema equality, M4 reject extra optional parameters each fail `test_core_schema_drift_on_synthetic_schemas`. Focused runs: `test_profile_support` 71 OK (with the pair 88 OK), `test_record_layout_lifecycle.SchemaPinAndReloadTests` OK, `test_secrets_validators` 157 OK; `test_server_context_efficiency` 101 with one failure, `test_repeated_warm_estimator_and_projection_budgets` (warm p95 timing budget under machine load, not this change). Gapfill: `code_keyword` reaches `tests/` but cannot resolve import bindings or aliases, so the census used an AST script over `tests/*.py` and the classification used a scratch-copy run harness. Coordinator suite run (scratch copy of the whole wave tree): `run_tests.py --no-cache` 10689 tests across 156 files OK (34 skipped); `--profile declared` 10689 OK; `--profile second` 10686 run, its one failure was a 1zltr fixture (fixed, the file then passed under the second profile). | Scratchpad `1zls7-1zltu-before-single-process.txt`, `1zls7-1zltu-after-single-process.txt`, `1zls7-1zltu-mutations.txt`, `1zls7-1zltu-census/` (`census.py`, `sites.json`, `harness.py`, `out/`), 2026-10-02 |
| 2026-10-02 | Planned. Verified: the eviction block in `server_impl.py` lists `record_paths` and the other modules named in Requirement 2; `record_layout_support.waves_dir` and `waves_rel` import `record_paths` at call time; `test_profile_support.py` imports `record_paths` at module level and patches it with `mock.patch.object`; `test_retired_change_kinds.py` calls `load_server()`; the golden test compares `sorted(live["properties"])` only, while the fixture records full `inputSchema` objects (for example `wf_add_change` has `mode` with `default "dry_run"` and `required ["change_id", "wave_id"]`). Candidate census grep: 44 `patch.object(<evicted module>` sites in 14 test files. | Planning read, 2026-10-02 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-02 | Compare core parameters fully and allow extra optional parameters only | Operator decision: an override may add an optional parameter, but the core contract (types, defaults, required) must not drift | Exact schema equality (breaks legitimate overrides); names only (today) |
| 2026-10-02 | Readiness amendments: the regression test uses `importlib.reload(srv)` (as `test_record_paths_is_evicted_on_reload` does) and asserts the precondition that `sys.modules["record_paths"]` is not the module-level object; the census predicate is restated exactly and widened to the `_PACKAGE_PURGE_KEYS` handler modules (`memory_handlers`, `index_handlers`, `upgrade_handlers`, ...) and aliased imports (`import lifecycle_gates as gates`); AC-4 notes the reviewer probe showing the full comparison already passes today's golden | Readiness review: a bare `load_server()` may not evict a module the test already holds, and the name-only predicate missed handler modules and aliases | Keep the narrower predicate (rejected: misses known sites) |
| 2026-10-02 | Fix the tests, not the eviction block | The eviction is required for `wf_reload_mcp` to pick up current code | Stop evicting `record_paths` |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The full comparison exposes real drift in the eight tools | Requirement 6: stop and report; never rewrite the fixture to pass |
| The census misses a site that patches through an alias name | The Requirement 2 predicate binds names through aliased imports and covers the `_PACKAGE_PURGE_KEYS` handler modules |
| Platform behaviour | Pure in-process Python and JSON comparison; identical on Windows, macOS, Linux and WSL2 |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
