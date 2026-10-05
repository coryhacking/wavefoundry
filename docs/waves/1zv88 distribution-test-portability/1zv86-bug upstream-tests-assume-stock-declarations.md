# Upstream Tests Fail On A Distribution's Valid Extension Declarations

Change ID: `1zv86-bug upstream-tests-assume-stock-declarations`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-05
Wave: 1zv88 distribution-test-portability

## Rationale

Downstream requests (Waveforge R1, R2, R4; confirmed at `fdd8de15`): four upstream tests encode the stock declarations, so a distribution whose behavior is correct fails them. (R1) `test_tool_surface_golden.WrapperOrderTests.test_every_other_permutation_is_distinguishable` swaps the middleware wrappers but each slot still passes its own kwargs (`_lock_pass_kwargs`, `_cost_pass_kwargs`, `_guard_pass_kwargs`), which are non-empty once `EXTENSION_LIFECYCLE_TOOLS` or `EXTENSION_ARTIFACT_PATH_FIELDS` is declared, so permutations raise `TypeError`. (R2) `test_tree_kill_routing.ClassificationTests.test_every_timed_call_is_routed_or_classified` requires an exact match with upstream's `ROUTED`/`EXCLUDED` tables, so an extension module's correctly routed `run_with_tree_kill(..., timeout=5)` fails it. (R4a) `test_extension_tool_modules.HelperModuleDeclarationTests.test_the_framework_script_census_matches_the_scripts_directory` counts every module in `scripts/` against the framework list. (R4b) `test_upgrade_wavefoundry.PostExtractStaleLeafRefreshTests.test_ac9_invalid_replacement_profile_stops_before_phase_2c` replaces the literal `CONTAINER_NAME = "Wave"`, which fails under another container name.

## Requirements

1. R1: in `_observe`, the three kwargs providers (`_cost_pass_kwargs`, `_lock_pass_kwargs`, `_guard_pass_kwargs`, looked up by global name) are patched so each slot passes the kwargs of the wrapper actually bound there (a map from wrapper name to its kwargs, for example lock -> `{"extension_tools": frozenset({"acme_record"})}`); the variant feeds non-empty kwargs through those providers (not through `apply_base_declaration`, which would require planting a registered extension tool); `setUp` applies `apply_base_declaration(self)` so the stock case is deterministic.
2. R2: in files that are not upstream framework modules (a file directly under `scripts/`, `len(rel.parts) == 1`, whose stem is not in `FRAMEWORK_SCRIPT_MODULE_NAMES`; every file in `wf_server/`, `wave_lint_lib/`, `benchmarks/` or other subfolders stays upstream and exact), a call to `subprocess_util.run_with_tree_kill` passing `timeout=` counts as routed without a table row; a raw timed call (`subprocess.run`, `.wait`, `.communicate`) in such a file still fails. Upstream files keep the exact census; the runner-binding census (`BINDING_ALLOWED`) is unchanged (out of scope).
3. R4a: the module census reads the extension declaration from `mcp_tool_extensions.py` on disk (the test runs under the base declaration, which hides it) and asserts every listed module exists. On the stock declaration it stays exact: the flat scripts on disk equal `FRAMEWORK_SCRIPT_MODULE_NAMES`. On a declared distribution, a flat module that `server.py`, `wf_server/` or a listed framework script imports (AST) must be listed or declared in `EXTENSION_MODULES` or `EXTENSION_HELPER_MODULES`. A distribution module nothing upstream imports (a renderer helper) no longer fails it; a new server-imported module missing from the list still does. An exact import-closure comparison is not possible: 36 listed scripts are command-line entry points or loaded by name, so no static closure reaches them. A declaration value that is not a plain literal (computed or augmented) fails the census rather than dropping the exact check; `()` and `[]` both count as the stock empty value.
4. R4b: the invalid-profile test corrupts whichever `CONTAINER_NAME = "..."` assignment is present with `re.subn(r'^CONTAINER_NAME = "([^"]*)"', ..., count=1, flags=re.M)` (a leading space makes any name invalid; `CONTAINER_NAME_PLURAL` does not match) and asserts the substitution count is 1 instead of `assertNotEqual`.
5. No production behavior changes; CHANGELOG gets one bullet under `## [1.29.0]` `### Fixed`.

## Scope

**Problem statement:** upstream tests assume the stock extension declarations and vocabulary.

**In scope:**

- The four tests and the census helpers they use; CHANGELOG.

**Out of scope:**

- The skill extension seam (R3, separate).
- The golden fixture per declaration profile (earlier request).

## Acceptance Criteria

- [x] AC-1: R1: the permutation test passes on stock declarations and in a variant with one extension lifecycle tool and one artifact field declared, and it still distinguishes every wrong order.
- [x] AC-2: R2: a planted extension module with one `run_with_tree_kill(..., timeout=5)` call passes the census and one raw `subprocess.run(..., timeout=5)` call fails it; upstream files keep exact matching.
- [x] AC-3: R4a: a planted undeclared module the server does not import no longer fails the census; a server-imported module missing from the list fails it, and a listed module missing from disk fails it.
- [x] AC-4: R4b: the invalid-profile test corrupts the assignment under a non-default container name and still stops before Phase 2c.
- [x] AC-5: CHANGELOG Fixed bullet; the four changed test files and every test this change adds pass; the documents this change edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] R1 permutation kwargs and declared-variant test
- [x] R2 census rule for non-upstream files with routed calls
- [x] R4a census assertion
- [x] R4b regex corruption
- [x] CHANGELOG bullet

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| test-fixes | implementer | — | tests only |


## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_tool_surface_golden.py`, `.wavefoundry/framework/scripts/tests/test_tree_kill_routing.py`, `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`, `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`

## Affected Architecture Docs

N/A: test-only.

## Platform Behavior

Platform-neutral (tests).

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | R1 |
| AC-2 | required | R2 |
| AC-3 | required | R4a |
| AC-4 | required | R4b |
| AC-5 | required | release notes |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-05 | Second delivery review (fresh reviewer) PASS for code and qa; 874 tests across the four files, mutation probes M1-M4 killed, a planted unlisted script caught by the stock census. Its finding 1 fixed: a declaration name not assigned at top level by a plain name (inside an `if`, by unpacking) now fails closed too. Finding 2 accepted (R2 matches the callee by attribute name; a raw timed call in the same file is still counted). Full scratch suite 11195 OK | fullsuite10; focus88 251 OK after the fix |
| 2026-10-05 | Delivery review (code and qa) PASS with non-blocking findings, all fixed: the census now fails closed on a non-literal or augmented declaration and normalizes `()`/`[]`; `literal_eval` errors of any type read as non-literal; `wf_server/` is scanned recursively; the identity-order run asserts what each wrapper received; Requirement 2 reworded (any `timeout=` keyword, as the upstream rows). Requirement 3 gained the fail-closed sentence. Mutation probes killed the three new guards | focused run 905 OK (scratch focus88) |
| 2026-10-05 | Implemented. R1: per-slot provider patching plus a recorder proving each wrapper receives its own declared keywords in every permutation; `setUp` applies the base declaration. R2: `classified_census` drops `run_with_tree_kill` rows only in flat modules outside `FRAMEWORK_SCRIPT_MODULE_NAMES`. R4a amended (Requirement 3): an exact server import closure cannot work because 36 listed scripts are entry points or loaded by name; the census reads the on-disk declaration, stays exact when it is stock, and on a declared distribution requires listing only for modules the server or a listed script imports. R4b: anchored `subn` with count 1, plus a renamed-container test. Mutation probes killed every guard (the first R1 version survived removal of the provider patch; the recorder fixed it). A simulated distribution (extension module plus undeclared helper on disk) passes both censuses, and a raw timed call in its helper fails. Gapfill: AST and grep reads of the four test files and the census inputs were done with shell tools because the work is test-local and mechanical | focused run 903 OK (scratch focus88); mutation script mut88.py |
| 2026-10-05 | Readiness review folded in: R1 per-slot provider patching and deterministic stock declaration; R2 path-aware upstream predicate; R4a import-closure census; R4b `re.subn` with a count assertion | readiness review |
| 2026-10-05 | Planned from the Waveforge requests R1, R2, R4 | verification reviewer confirmed all four by reading |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-05 | R4a keeps the exact census on a stock declaration and relaxes it only for a declared distribution | upstream keeps its regression net; a static import closure misses entry-point scripts | an exact import-closure comparison (does not hold on the stock tree) |
| 2026-10-05 | R2 by rule (routed callee in non-upstream files), not a new declaration | smaller, no new validated declaration field; raw timed calls still fail | an `EXTENSION_TIMED_CALLS` declaration |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Loosening a census hides an upstream regression | upstream files keep exact matching; only non-upstream files get the routed-callee rule |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
