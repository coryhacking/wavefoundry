# Test Infrastructure for Running the Suite Under a Vocabulary and Layout Profile

Change ID: `1zim1-debt profile-portable-test-fixtures`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-01
Wave: 1zim5 profile-portable-test-suite

## Rationale

A downstream validation of v1.28.0 (request 7) found that with a second vocabulary and layout profile the production readers, lint, archive and dashboard behave correctly, but much of the suite fails because fixtures assume the default profile. A census on 2026-09-30 measured it: a full git clone at `82d6342a` with the profile container Set/Sets, item Task/Tasks, record file `set.md`, live root `docs/delivery/sets` (nested, `MAX_DEPTH` 4) and archive root `docs/waves` (both validators accept it; `ARCHIVE_PROFILE` unset) went from green (3 load flakes that pass alone) to 1,477 failures and errors in 47 of 146 files. Causes: about 740 from no `README.md` in the configured waves root (lint's required file), most of them in `test_docs_lint` including fixtures copied by `copy_fixture` in default vocabulary; about 650 to 700 from records written as `wave.md` or placed in `docs/waves`, the archive under that layout; about 50 from assertions on default names, labels and paths; about 30 flaky or timing-sensitive. No confirmed production defect; four results need classification. This change builds the infrastructure (builders, a shared profile asset, a default-profile-only marker and a second-profile run); `1zim6` migrates the failing tests onto it.

## Requirements

1. **One profile asset and apply function.** A data file under `tests/fixtures/profiles/` (record layout and vocabulary fields, plus `ARCHIVE_PROFILE`) defines the second profile: the existing `test_vocabulary_second_profile` profile (Set/Sets, Member/Members, `set.md`, `## Members`, `Member ID`) with a nested live root and the default vocabulary as the archive profile at `docs/waves`, the realistic distribution case. One shared function applies a profile to a copied tree the way a fork does (editing the constants in `vocabulary_profile.py` and `record_paths.py`, each replacement matching exactly once, then importing both to validate). `test_vocabulary_second_profile` uses the same asset and function.
2. **Profile-aware builders.** Test support gains builders that write records the way the active profile expects: the waves root with its required `README.md` (content that passes the corpus lints), a container record with the profile's filename and markers (via `vocabulary_profile`, including `localize_template`), member blocks, plans, and the archive root and archive-profile records when configured; and a localizing copy of the docs-lint fixture tree. Test support imports production constants and is never imported by production code.
3. **Default-profile-only marker.** One decorator marks tests whose subject is the default profile (golden outputs, stock-surface pins, censuses of this repository's own documents, the default-path constants), each with a one-line reason. It compares the loaded constants with a frozen snapshot of the shipped defaults kept in test support (not with `vocabulary_profile`, which a distribution edits), and skips when they differ.
4. **Second-profile run.** `run_tests.py` gains a mode, exclusive with the schedule-control options, that copies the git-tracked tree (`git ls-files -co --exclude-standard`) into a temporary git repository, applies a named profile asset, writes the configured waves-root README, and runs the suite there as a focused run: it never writes the framework test receipt, and it reports its result as not delivery evidence. It is on-demand and at release, not part of the default run.
5. **Platforms.** Windows, macOS, Linux and WSL2 behave the same; temporary directories and the same runner.
6. **Transition.** Test infrastructure only; the CHANGELOG line ships with `1zim6`.

## Scope

**Problem statement:** the framework suite has no way to build profile-correct fixtures, mark default-subject tests, or run under a second profile.

**In scope:**

- The profile asset and apply function; builders; the marker; the runner mode; adopting the asset in `test_vocabulary_second_profile`; testing-architecture.

**Out of scope:**

- Migrating failing tests (`1zim6`).
- Declarations portability (`1zim4`).
- Production code changes.

## Acceptance Criteria

- [x] AC-1: the builders write a valid record tree under the default profile and under the second profile (docs-lint passes on each), including the archive in the default vocabulary; a localized copy of the docs-lint fixture passes lint under the second profile.
- [x] AC-2: the marker skips its test when the loaded constants differ from the frozen shipped defaults and runs it when they match, including when `vocabulary_profile` itself has been edited to the second profile.
- [x] AC-3: the second-profile run copies the git-tracked tree into a temporary git repository, applies the asset, runs, and reports a per-file result; the real `test-cache.json` is byte-identical afterwards; its result is reported as not delivery evidence.
- [x] AC-4: the default run has no test removed or newly skipped; its count changes only by the tests this change adds; `test_vocabulary_second_profile` passes using the shared asset.
- [x] AC-5: `docs/architecture/testing-architecture.md` describes the asset, builders, marker and run beside the canonical runner.
- [x] AC-6: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Profile asset and apply function.
- [x] Builders and fixture localization.
- [x] Marker with frozen defaults.
- [x] Runner mode.
- [x] Adopt the asset in `test_vocabulary_second_profile`.
- [x] Record the second-profile run's per-file result in this change's Progress Log.
- [x] Docs.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Infrastructure | implementer | readiness | |
| Review | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/record_layout_support.py`, `.wavefoundry/framework/scripts/tests/fixtures/profiles/`, `.wavefoundry/framework/scripts/tests/test_vocabulary_second_profile.py`, `.wavefoundry/framework/scripts/run_tests.py`
- `docs/architecture/testing-architecture.md`

## Affected Architecture Docs

`docs/architecture/testing-architecture.md`.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Builders work under both profiles |
| AC-2 | required | The marker works inside a distribution |
| AC-3 | required | A run that matches what the census measured, without touching the receipt |
| AC-4 | required | No regression in the default run |
| AC-5 | important | Discoverability |
| AC-6 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-01 | DEL-1ZIM5-PROFILE-SYMLINK-WRITE reverification follow-ups (coordinator): the independent reverifier confirmed the repair (end-to-end runs with tracked symlinks to outside targets left them byte-identical) and found one residual path of the same class: `_copy_listed_tree` itself could copy a listed file through a tracked directory replaced on disk by a relative symlink, landing outside the copy. Now a listed file beneath a directory the copy already holds as a symlink is skipped (`_beneath_copied_symlink`), since the link carries what the working tree shows. Tests: `test_the_copy_never_writes_through_a_directory_replaced_by_a_link` (fails with the skip removed: the file landed in the outside directory) and `test_a_sibling_that_shares_the_root_prefix_is_outside` (fails when confinement is a string prefix check). Both mutations run in a scratch framework copy | `run_tests.py _copy_listed_tree`; `tests/test_profile_support.py` 53 OK |
| 2026-10-01 | DEL-1ZIM5-PROFILE-SYMLINK-WRITE repair. `_copy_listed_tree` keeps tracked symlinks as symlinks (fidelity), so the writers changed instead: new `record_layout_support.replace_file_in(root, path, data)` writes a temporary file in the same directory and `os.replace`s it over the path, which replaces a symlink itself (its target is never opened for writing), and refuses a path whose directory resolves (`os.path.realpath`) outside `root` before creating anything. `apply_profile` writes the three profile modules (`vocabulary_profile`, `record_paths`, the `mcp_tool_extensions` declaration) through it, contained in `repo_root` or else `scripts_dir`; `RecordTreeBuilder.waves_readme` keeps an existing regular README and otherwise writes through it contained in the builder root (a symlinked README becomes a regular file; the README is now written with LF line endings on every platform). `run_tests._profile_run_in` reports a refused README as a profile that does not apply (rc 1). Platforms: `os.replace` renames over the link on Windows as on POSIX, so macOS, Linux, WSL2 and Windows behave the same; the new symlink-creation tests skip with a reason only when `os.symlink` raises (Windows without the symlink privilege). No timed call moved, so `test_tree_kill_routing` needed no pin change | Five new tests in `test_profile_support.py` (modules symlinked outside the copy, a scripts directory symlinked outside, a symlinked README to an existing and a dangling target, a README under a symlinked waves root and a symlinked ancestor, and a full `_run_profile` on a tiny repository with a symlinked `vocabulary_profile.py`) produced 9 failures before the fix (outside targets rewritten to the profile, no refusal) and pass after; `test_profile_support`, `test_declaration_support`, `test_vocabulary_second_profile`, `test_run_tests_cache` and `test_tree_kill_routing` pass (200 tests, 0 skipped) in the default run and under `--profile second` and `--profile declared` |
| 2026-10-01 | Delivery-review repairs. CR-1: the run's temporary tree is removed with a read-only retry (entry and parent made writable; git objects are read-only on Windows) on every exit; SIGTERM raises an interrupt during the run (not on Windows) and the previous handler is restored; on any exit the copy's runner group is ended and reaped before removal; the child runner gets no `GIT_*` variables and runs in its own process group; temp-repository git commands pass `gc.auto=0` and `maintenance.auto=false`; malformed `--file` selectors are refused before copying. Red-team: the canonical-tree refusal test patches `SCRIPTS_DIR` to a copy, so it can never write the repository. QA: `test_loaded_constants_are_shipped_or_a_declared_profile` (loaded constants equal `SHIPPED_DEFAULTS` or it overlaid with an asset in `tests/fixtures/profiles/`); tests for the receipt-change check, `GIT_*` stripping, every loaded module copy, back-reference localization; the method-form marker now skips before `setUp`. `apply_profile` keeps CRLF line endings. The localized fixture's README follows the profile. New helpers `localize_record_text` (used by the fixture), `waves_dir`, `waves_rel`, `declared_profile_match`. Testing-architecture: plan count dropped, a distribution adds its asset, cleanup described. `test_tree_kill_routing` pin renamed to the git loop's new enclosing function `_profile_run_in`. 13 scratch-copy mutations each failed the new tests (the SIGTERM one killed the test process); the gc and maintenance flags have no test | `test_profile_support` (39 tests), `test_vocabulary_second_profile`, `test_run_tests_cache`, `test_run_tests_repo_guard` and `test_tree_kill_routing` pass in the default run and under `--profile second` (receipt unchanged, no temporary tree left) |
| 2026-10-01 | Second-profile run against the real tree (`run_tests.py --profile second`, all 147 files, 3,160 files copied): 1,429 failures and errors in 44 of 147 files (103 passed, 34 skipped), copy of the tree at this change's implementation. Largest: `test_docs_lint` 750 (732 failures, 18 errors), `test_server_tools_lifecycle` 299, `test_dashboard_server` 104, `test_server_context_efficiency` 37, `test_server_tools` 22, `test_lifecycle_gates` 20, `test_memory_records` 19, `test_record_paths` 14, `test_review_evidence` 14, `test_upgrade_wavefoundry` 13, `test_review_policy` 12, `test_dashboard_terminology` 8, `test_phase_gates` 8, `test_server_tools_retrieval` 8, `test_vocabulary_profile` 8, `test_archive_root` 7, `test_indexer` 7; 27 more files with 1 to 6 each. 12 of the 1,429 were this change's own two files, which built from the running tree rather than the shipped defaults; fixed (copies now reset to the shipped defaults first) and both files pass under the profile run, so the migration scope is 1,417 in 42 files. This tree's receipt was byte-identical before and after (SHA-1 `f230d8a3`). Separately, this repository's own documents do not lint clean under the profile (12 plans in the default vocabulary lack `Member ID:`; the prompt-surface manifest names `docs/waves/`) | Run output saved outside the repository (`second-profile-baseline.txt` in the session scratchpad); `shasum` of `test-cache.json` before and after |
| 2026-10-01 | Implemented: asset `tests/fixtures/profiles/second.json`; `apply_profile`, `RecordTreeBuilder`, `localized_docs_lint_fixture`, `write_waves_readme`, `default_profile_only` and the frozen `SHIPPED_DEFAULTS` in `tests/record_layout_support.py`; `run_tests.py --profile NAME [--file NAME ...]` and `--help`; `test_vocabulary_second_profile` on the shared asset (control tree is the asset's layout with the default vocabulary); `tests/test_profile_support.py` (26 tests, AC-1 to AC-3). Nine mutations in a scratch copy each failed the new tests (no manifest localization, shipped record name, marker blind to differences, no exactly-once check, run in place, tracked files only, progress read from failure blocks, no README, no `localize_template`). Deviation: `localized_docs_lint_fixture` also rewrites the fixture's prompt-surface manifest waves root, which lint requires. Two dependents adjusted: `test_vocabulary_writers` (it reused the second-profile helpers; now the asset with its nested root, the census scanning the configured roots, which also clears its setUpClass error under the profile run) and `test_tree_kill_routing` (the runner's two new timed git calls are routed through `_run_tree_kill` and pinned); the builder's record declaration carries a `producer-fixture` classification for `test_declared_wave_fixtures` | Focused runs; mutation script output |
| 2026-10-01 | Implementation notes from readiness: AC-2's marker phrasing means the verdict comes from the frozen snapshot, so an edited `vocabulary_profile` makes the marker skip; the copy uses `git ls-files -co --exclude-standard` (tracked plus untracked non-ignored files); testing-architecture must state whether the run lints this repository's own documents; the exactly-once replacement and import validation are required | Readiness review |
| 2026-09-30 | Readiness round 1: red-team blocked (AC-2 unpassable with 30 existing default-run skips; AC-3 contradicted added tests; a minimal scaffold is not what the census measured, and about 33 test files read repository-level content). Lanes approved with notes. Repaired: split into infrastructure (this change) and migration (`1zim6`); the run copies the git-tracked tree into a temporary git repository and never writes the receipt; the marker compares against frozen shipped defaults; one profile asset shared with `test_vocabulary_second_profile`, archive in the default vocabulary; facts corrected (clone at `82d6342a`, 47 failing files) | Prepare council and lane review |
| 2026-09-30 | Planned from request 7 with a census (see Rationale); logs in the census clone, not in the repository | Census run |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | Split infrastructure from migration | Each change gets ACs it can close; `1zim4` depends only on the infrastructure | One change |
| 2026-09-30 | Full git-tracked copy for the run | It reproduces the measured environment and keeps repository-content tests meaningful | Minimal scaffold |
| 2026-09-30 | Archive in the default vocabulary | The usual distribution keeps its pre-adoption records unchanged | Archive in the second vocabulary (the census) |

## Risks

| Risk | Mitigation |
| --- | --- |
| The chosen profile differs from the census (Members vs Tasks, archive vocabulary) | `1zim6` starts by re-measuring with the asset |
| The marker becomes a dumping ground | Each use needs a reason; `1zim6`'s census counts marked tests |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
