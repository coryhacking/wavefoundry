# Migrate the Framework Tests to Profile-Aware Fixtures

Change ID: `1zim6-debt migrate-tests-to-profile-builders`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-30
Wave: 1zim5 profile-portable-test-suite

## Rationale

Follows `1zim1`. A census on 2026-09-30 measured it: a full git clone at `82d6342a` with the profile container Set/Sets, item Task/Tasks, record file `set.md`, live root `docs/delivery/sets` (nested, `MAX_DEPTH` 4) and archive root `docs/waves` (both validators accept it; `ARCHIVE_PROFILE` unset) went from green (3 load flakes that pass alone) to 1,477 failures and errors in 47 of 146 files. Causes: about 740 from no `README.md` in the configured waves root (lint's required file), most of them in `test_docs_lint` including fixtures copied by `copy_fixture` in default vocabulary; about 650 to 700 from records written as `wave.md` or placed in `docs/waves`, the archive under that layout; about 50 from assertions on default names, labels and paths; about 30 flaky or timing-sensitive. No confirmed production defect; four results need classification. This change migrates the failing tests onto `1zim1`'s builders and marker until the second-profile run is green.

## Requirements

1. **Re-measure first.** Run `1zim1`'s second-profile run with the shared asset and record the per-file failures in the Progress Log; that list, not the census, is the migration scope.
2. **Derivation rule.** A test that exercises framework behaviour takes record paths, filenames and markers from `record_paths`, `vocabulary_profile` or the builders, never literal `docs/waves`, `wave.md` or default labels. A test whose subject is the default profile carries the default-profile-only marker with a reason. Configured values in layout tests (for example an archive root of `docs/waves`) remain legitimate literals.
3. **Classify the four open results.** The census's archive chunk tags (`test_chunker`), secrets-scan candidate (`test_secret_scan_cache`), memory backfill state (`test_sqlite_storage_migration`) and repo-guard snapshot (`test_run_tests_repo_guard`) are each shown, with evidence in the Progress Log, to be a fixture assumption (fixed here) or a production defect (planned separately).
4. **Literal-path census.** A test scans `tests/test_*.py` for `docs/waves` and `wave.md` literals (line-based, docstrings excluded) and fails on any outside marked tests and an allowlist keyed by file and snippet with a typed reason; it fails on stale allowlist entries; a planted literal proves it can fail.
5. **Migration order.** File groups in the order of the re-measured list (largest first), one owner per file.
6. **Docs and release.** `docs/prompts/package-wavefoundry.prompt.md` adds the second-profile run to the release checklist; CHANGELOG under `### Changed`: "The test suite can run under a second vocabulary and layout profile, and a distribution's suite skips only tests marked default-profile-only."
7. **Platforms.** Windows, macOS, Linux and WSL2 behave the same.
8. **Transition.** Test changes only, plus the checklist and CHANGELOG line.

## Scope

**Problem statement:** most failing tests under a second profile assume the default profile's paths, filenames and labels.

**In scope:**

- The failing test files; the literal-path census test; release checklist; CHANGELOG.

**Out of scope:**

- Production code changes (any defect found by Requirement 3 is planned separately).
- Declarations portability (`1zim4`).

## Acceptance Criteria

- [x] AC-1: the second-profile run passes, and every skip beyond those the default run takes comes from the default-profile-only marker with a reason.
- [x] AC-2: the literal-path census passes, fails on a planted literal and on a stale allowlist entry, and reports the count of marked tests.
- [x] AC-3: the four open results are classified with evidence in the Progress Log.
- [x] AC-4: the default run has no test removed or newly skipped; its count changes only by the tests this change adds.
- [x] AC-5: the release checklist and CHANGELOG describe the run and the marker.
- [x] AC-6: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Re-measure with the asset.
- [x] Classify the four open results.
- [x] Migrate file groups, largest first.
- [x] Literal-path census with planted control.
- [x] Release checklist; CHANGELOG.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Migration | implementer | 1zim1 | parallel by file group, one owner per file |
| Review | code-reviewer, qa-reviewer, docs-contract-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/`
- The test files are those the re-measured second-profile run lists.
- `docs/prompts/package-wavefoundry.prompt.md`

## Affected Architecture Docs

`docs/architecture/testing-architecture.md` (only if the derivation rule needs a line).

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The suite verifies a second profile |
| AC-2 | required | Backsliding is caught |
| AC-3 | required | Open results resolved |
| AC-4 | required | No regression in the default run |
| AC-5 | important | Release discipline |
| AC-6 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-01 | Literal-path census (Requirement 4): new `tests/test_profile_literal_census.py` reads each `tests/test_*.py` AST, so comments are never seen and docstrings (first string statement of a module, class or function) are dropped; it reports, once per source line, `docs/waves` inside a string constant or as adjacent `"docs"`, `"waves"` constants in a `/` chain or call arguments, and `wave.md` as a whole file name. Occurrences inside a `@default_profile_only` method or class are allowed; the rest must match an allowlist entry keyed by file and snippet (the source line, or the start of the enclosing module-level binding line for census tables) with one of seven typed reasons: configured-layout-value, opaque-fixture-path, production-source-census, planted-control, repository-input-prose, historical-old-runner-layout, shipped-template-text. First scan of the tree: 308 occurrences. Missed migrations fixed in the test files (record paths now from `waves_dir`, `waves_rel`, `localize_record_text`, `vocabulary_profile.RECORD_FILENAME`): `test_memory_backfill`, `test_lifecycle_id`, `test_chunk_tags` (fixture wave record), `test_graph_indexer` (wave refs never become edges), `test_build_pack`, `test_agent_surface_integrity`, `test_upgrade_wavefoundry` (memory-backfill roots, lifecycle-policy scans, historical sentinels, legacy-lock target, and the sidecar acquirer, which observed `docs/waves` while the sidecars were written under the live root and so passed vacuously under the second profile), `test_reconcile_scan`, `test_setup_wavefoundry`, `test_storage_upgrade_resume`, `test_wf_cli`, `test_server_tools_retrieval` (three wave-class prior tests). Remaining 235 occurrences, all allowlisted by 82 entries; 11 tests carry the marker | `run_tests.py --file test_profile_literal_census.py`: 8 tests ok, reporting 11 marked tests and 235 occurrences; planted source, planted literal in a copied real test file, and a planted stale entry each fail the census; focused default and `--profile second` runs of every touched file pass; whole-suite `run_tests.py --profile second`: 149 of 149 files pass, 10,316 tests, 44 skipped (the first run failed one test in `test_events_only_residue_census`, whose tests-tree scan flagged a census snippet naming a retired sidecar file; the snippet was shortened) |
| 2026-10-01 | Migration evidence. Re-measured second-profile baseline after `1zim1`'s own fixes: 1,417 failures and errors in 42 files. After the per-group migration every assigned file passes under `--profile second`, apart from the tests marked default-profile-only (11 marked tests at census time). Requirement 3 classifications, all fixture assumptions: `test_chunker` archive chunk tags (the root-less `infer_tags` default covers only the live root by design; callers that have a root pass the archive prefix); `test_secret_scan_cache` (the nested `MAX_DEPTH` over-exclusion is documented behaviour); `test_sqlite_storage_migration` (passed by archive-vocabulary coincidence, now built from the live layout); `test_run_tests_repo_guard` (the matcher uses the live root; the archive is read-only by `1z827`). Two production defects found and fixed in `1zim7`. Open question left to the operator: archived records are not demoted in retrieval, and drift, the graph scan exclusion and retrieval-eval treat the archive root as living docs | Per-group migration reports; `1zim7` |
| 2026-10-01 | Implementation notes from readiness: the allowlist reason types include configured layout values; the release checklist names the exact runner flag | Readiness review |
| 2026-09-30 | Split out of `1zim1` at readiness (red-team suggestion) so the migration closes on a green second-profile run | Prepare council |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | Scope from a fresh measurement with the shared asset | The census profile differs slightly (Tasks vs Members, archive vocabulary) | Census list |

## Risks

| Risk | Mitigation |
| --- | --- |
| Large mechanical change | One owner per file, builders first, census prevents backsliding |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
