# The Framework Test Suite Runs Under a Distribution's Vocabulary and Layout Profile

Change ID: `1zim1-debt profile-portable-test-fixtures`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-30
Wave: 1zim5 profile-portable-test-suite

## Rationale

A downstream validation of v1.28.0 (request 7) found that with a second vocabulary and layout profile the production readers, lint, archive and dashboard behave correctly, but much of the suite fails because fixtures assume the default profile. A census on 2026-09-30 measured it: a clone at `92f46ba0` with the profile container Set/Sets, item Task/Tasks, record file `set.md`, live root `docs/delivery/sets` (nested, `MAX_DEPTH` 4) and archive root `docs/waves` (both validators accept it) went from green (3 load flakes that pass alone) to 1,477 failures and errors in 48 of 146 files. Causes: about 740 from no `README.md` in the configured waves root (lint's required file), most of them in `test_docs_lint`, including fixtures copied by `copy_fixture` in default vocabulary; about 650 to 700 from records written as `wave.md` or placed in `docs/waves`, which is the archive under that layout; about 50 from assertions on default names, labels and paths; about 30 flaky or timing-sensitive. No confirmed production defect; four results need classification (archive chunk tags in `test_chunker`, a secrets-scan candidate in `test_secret_scan_cache`, a memory backfill state in `test_sqlite_storage_migration`, the repo-guard snapshot in `test_run_tests_repo_guard`). All 13 files that already use `record_layout_support` still fail somewhere, because they hard-code `docs/waves` and `wave.md` outside the helper.

## Requirements

1. **Profile-aware fixture builders.** `tests/record_layout_support.py` (or a sibling) gains builders that write records the way the active profile expects: the waves root with its required `README.md`, a container record at the profile's filename and markers (via `vocabulary_profile`, including `localize_template` for template-shaped text), member blocks, plans, and the archive root when one is configured. Copied static fixtures (the docs-lint fixture tree) are localized to the active profile when copied.
2. **Derivation rule for tests.** A test that exercises framework behaviour takes record paths, filenames and markers from `record_paths` and `vocabulary_profile` (or the builders), never literal `docs/waves`, `wave.md` or default labels. A test whose subject IS the default profile (golden outputs, stock-surface pins, census of this repository's own documents, the default-path constants) is marked default-profile-only with a one-line reason, through one decorator, and skips under another profile. The marker is the only allowed form of skip for this reason.
3. **A second-profile run.** `run_tests.py` gains a mode that copies the framework scripts and a minimal repository scaffold to a temporary root, applies a checked-in second profile (the census profile, kept as a test asset), and runs the suite there. It is a release-time and on-demand check, not part of the default run. The repository's own documents are not linted under the second profile.
4. **Classify the four open results.** Each of the four results named in the Rationale is shown to be a fixture assumption (then fixed with the rest) or a production defect (then planned separately); the classification and evidence are recorded in this change's Progress Log.
5. **Migration order.** Files migrate in the order of the census table (largest first), so the second-profile run turns green area by area; the change closes when that run is green apart from default-profile-only skips.
6. **Docs.** `docs/architecture/testing-architecture.md` describes the builders, the default-profile-only marker and the second-profile run; `docs/prompts/package-wavefoundry.prompt.md` adds the second-profile run to the release checklist.
7. **Platforms.** Windows, macOS, Linux and WSL2 behave the same; the second-profile run uses temporary directories and the same runner.
8. **Transition.** Test infrastructure only; no CHANGELOG entry beyond one line under `### Changed` noting that distributions can run the suite under their own profile.

## Scope

**Problem statement:** the framework suite cannot verify a distribution's own vocabulary and layout profile, because its fixtures and assertions assume the default profile.

**In scope:**

- Test builders and the default-profile-only marker; migration of the 48 failing files; the second-profile runner mode and its checked-in profile; testing-architecture and release checklist.

**Out of scope:**

- Production code changes (none needed by the census; any found by Requirement 4 are planned separately).
- Test portability under a distribution's tool declarations (`1zim4`).
- Linting this repository's own documents under another profile.

## Acceptance Criteria

- [ ] AC-1: the builders write a valid record tree for the default profile and for the second profile (docs-lint passes on each), and a localized copy of the docs-lint fixture passes lint under the second profile.
- [ ] AC-2: the second-profile run passes, with every skip coming from the default-profile-only marker and carrying a reason; a census test fails if a test file outside the marked set contains a literal `docs/waves` or `wave.md` used as a fixture path (stating its predicate and allowlist).
- [ ] AC-3: the default run is unchanged in count and still green (the marker only skips under a non-default profile).
- [ ] AC-4: the four open results are classified with evidence in the Progress Log.
- [ ] AC-5: the testing-architecture doc and release checklist describe the builders, marker and run.
- [ ] AC-6: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [ ] Builders and fixture localization.
- [ ] Default-profile-only marker.
- [ ] Second-profile runner mode and profile asset.
- [ ] Classify the four open results.
- [ ] Migrate test files, largest first.
- [ ] Literal-path census test.
- [ ] Docs.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Builders and runner | implementer | readiness | |
| Migration | implementer | builders | parallel by file group, one owner per file |
| Review | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/record_layout_support.py`, `.wavefoundry/framework/scripts/run_tests.py`, `.wavefoundry/framework/scripts/tests/` (the 48 files in the census)
- `docs/architecture/testing-architecture.md`, `docs/prompts/package-wavefoundry.prompt.md`

## Affected Architecture Docs

`docs/architecture/testing-architecture.md`.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Fixtures follow the profile |
| AC-2 | required | The suite verifies a second profile |
| AC-3 | required | No regression in the default run |
| AC-4 | required | Open results resolved |
| AC-5 | important | Discoverability |
| AC-6 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-30 | Planned from request 7 with a census: clone at `92f46ba0`, second profile Set/Task, `set.md`, `docs/delivery/sets` nested, archive `docs/waves`; default run 10204 tests with 3 load flakes (pass alone); second-profile run 1477 failures and errors in 48 files (largest: test_docs_lint 750, test_server_tools_lifecycle 304, test_dashboard_server 99, test_server_context_efficiency 37, test_memory_records 29, test_memory_backfill 26); no confirmed production defect; four results to classify. Logs in the census clone, not in the repository | Census run |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | A second-profile run on demand and at release, not on every run | It doubles suite time; release-time catches drift before distributions see it | Run both profiles every time |
| 2026-09-30 | One default-profile-only marker for tests whose subject is the default profile | Golden and stock-surface pins are legitimately default-specific; one marker keeps the exemption visible and countable | Rewrite every golden per profile |

## Risks

| Risk | Mitigation |
| --- | --- |
| The migration is large (48 files, about 1,500 failures) | Builders first, then file groups in census order with one owner per file; the literal-path census prevents backsliding |
| The marker becomes a dumping ground | Each use needs a reason; review checks the marked set against the rule |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
