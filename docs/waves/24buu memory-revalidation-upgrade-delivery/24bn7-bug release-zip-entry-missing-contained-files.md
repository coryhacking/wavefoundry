# Release zip entry fails on a missing module

Spec ID: `24bn7-bug release-zip-entry-missing-contained-files`
Spec Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-24
Wave: 24buu memory-revalidation-upgrade-delivery

## Rationale

Seed 160 and `docs/prompts/package-wavefoundry.prompt.md` ("Upgrade Path Coverage") tell an older (protocol-1) installation to upgrade by running the release zip directly: `python3 <combined.zip> --root <repo> --confirm-hosts-stopped`. `build_pack.build_upgrade_bundle` writes only `__main__.py`, `install-wavefoundry.md`, `upgrade_bridge_bootstrap.py`, `subprocess_util.py` and `embedded_model_bundle.py` at the zip's top level, and `upgrade_bundle._materializer` accepts only those runner members (`allowed_runner`). `embedded_model_bundle.retain` imports `contained_files`, which is not among them.

Verified 2026-11-24: the 1.51.0 release zip `wavefoundry-1.51.0.q5hc.zip` has no top-level `contained_files.py`, and the 24buu upgrade rehearsal (`.wavefoundry/work/24buu/upgrade-rehearsal.md`, item 1) ran a 1.52.0 candidate's entry and got `ModuleNotFoundError: No module named 'contained_files'` before any work. The import was added in commit `2452c73f`. The documented direct-entry path fails for every installation that uses it.

## Product Intent

**Beneficiaries:** operators of older installations who upgrade through the release zip's direct entry.

**Before:** the documented command fails at once with `ModuleNotFoundError`.

**After:** the documented command runs through retention and materialization, and a test runs it end to end from an isolated interpreter.

**Boundaries:** the zip keeps its current top-level members, so existing runners' member checks still accept it. No change to the upgrade protocol or the model companion.

AC-1 establishes the intent.

## Requirements

1. Framework modules that the zip's entry code imports at any reachable point, including imports inside functions such as `contained_files` in `retain`, resolve from the zip's own framework scripts (the feature members under `.wavefoundry/framework/scripts/` in the same zip, through zipimport), before the first call into `embedded_model_bundle.retain`. The path entry is inserted immediately after the zip's own root entry (`sys.path` index 1), so the zip's top-level runner members still win over the scripts copies of the same names and a `PYTHONPATH` entry cannot shadow the zip's scripts. It is built from the zip path with `os.path.join`. The zip's top-level member set does not change.
2. A test builds the combined zip, and the combined zip with the model companion, into a temporary directory, and runs the documented direct-entry command from `python3 -I`, with a working directory and path outside the framework tree, against a protocol-2 fixture installation (the 1.51.0 layout including `UPGRADE-PROTOCOL.json`). The run is not a dry run, so `retain` executes. The bridge's next step is replaced by a stub that records the `next_argv` it was given and exits, so the run is bounded and changes nothing beyond the fixture.
3. Platform behavior: zipimport and the path entry behave the same on Windows, macOS, Linux and WSL2; the path entry is built with the zip's own path, not a separator literal.

## Scope

**Problem statement:** the release zip's direct entry is missing a module it imports.

**In scope:** the import path set-up in the zip's entry code, the end-to-end test, and a changelog entry.

**Out of scope:** the bridge protocol, the top-level member list, model companion handling, and `build_pack.py` release checks.

## Acceptance Criteria

- [x] AC-1: The test of requirement 2 passes for both zips: the documented command gets past `retain` and `_materializer` with no `ModuleNotFoundError` and no `upgrade_protocol_invalid`, and the stub records the expected `next_argv`. Known bad: the current zip fails with `No module named 'contained_files'`; adding `contained_files.py` as a top-level member instead fails with `bundle contains an unexpected member`.
- [x] AC-2: The zip's top-level member set equals today's, checked against the existing member pins in `tests/test_upgrade_protocol.py`.
- [x] AC-3: A function-level import of another framework module added to `embedded_model_bundle.retain` in a test copy still resolves in the AC-1 run, showing the fix covers future imports.
- [x] AC-4: `CHANGELOG.md` has an `[Unreleased]` entry under a new `### Fixed` heading naming this wave and change, and `docs/architecture/data-and-control-flow.md` no longer calls the direct entry a stdlib-only zipapp.

## Tasks

- [x] The zip entry's path set-up (`__main__.py` or the bridge bootstrap, as the code shows), resolving the zip's own framework scripts.
- [x] Tests for AC-1 to AC-3 beside the existing bundle tests.
- [x] Changelog entry; per-file `--profile second` on touched tests.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| zip-imports | implementer | — | AC-1 to AC-4 |

## Serialization Points

- `.wavefoundry/framework/scripts/build_pack.py`, `.wavefoundry/framework/scripts/upgrade_bundle.py`, `.wavefoundry/framework/scripts/upgrade_bridge_bootstrap.py`, `.wavefoundry/framework/scripts/embedded_model_bundle.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_protocol.py`
- `docs/architecture/data-and-control-flow.md`
- The root `CHANGELOG.md` entry.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md`: its description of the release zip's direct entry as a stdlib zipapp becomes inaccurate once the entry imports framework modules from its own scripts.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The documented path must run. |
| AC-2 | required | Existing runners keep accepting the zip. |
| AC-3 | required | Prevents the same defect on the next import. |
| AC-4 | required | Release notes. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-24 | Planned from the 24buu upgrade rehearsal. | `.wavefoundry/work/24buu/upgrade-rehearsal.md` item 1 |
| 2026-11-24 | Revised before readiness approval from the red-team primer: adding members fails the materializer's allowlist (F3), and the zip writer is `build_pack.build_upgrade_bundle` (F11). | `.wavefoundry/work/24buu/readiness/red-team.md` |
| 2026-11-24 | Bounded readiness repair (cycle 1) for QA-3, AR-3 and DC-4: a protocol-2 fixture, a non-dry run with a stubbed next step, both zips, the path entry at index 1, the architecture doc named, and a Fixed heading. | `.wavefoundry/work/24buu/readiness/repair-1.md` |
| 2026-11-24 | Readback: the release zip's direct entry must resolve framework modules imported inside functions (`contained_files` in `embedded_model_bundle.retain`) from the zip's own `.wavefoundry/framework/scripts/`, inserted at `sys.path` index 1 before the first `retain` call, with the top-level member set unchanged (AC-1 to AC-4). Scope: the entry's path set-up, end-to-end tests, the architecture doc and changelog; no protocol, member list or model companion change. Expected files: `upgrade_bundle.py` (zip `__main__.py`), `tests/test_upgrade_protocol.py`, `docs/architecture/data-and-control-flow.md`, `CHANGELOG.md`. The readback was written after the first code edit; the brief asks for it before. | memory_brief(pre_implementation) on the five serialization files: five `target_churn` advisories, none contradicts the change (1umf9: upgrade-time code imports only what the pack ships; the zip ships `contained_files.py` under its feature scripts). |
| 2026-11-24 | Implemented: `upgrade_bundle._add_bundle_scripts_path`, called from `main()` before `run()`, inserts `os.path.join(<zip>, ".wavefoundry", "framework", "scripts")` at `sys.path` index 1 when `sys.argv[0]` is a zip; a standalone copied bridge gets no entry. Zipimport accepts the native separator on Windows, macOS, Linux and WSL2. | `.wavefoundry/framework/scripts/upgrade_bundle.py` |
| 2026-11-24 | Tests: `test_direct_zip_entry_resolves_framework_imports_from_the_zip` builds the plain and with-models zips (feature zip built with a stub `upgrade_wavefoundry.py`, so selection hashes match; companion verification patched only at build time), runs `python3 -I <zip> --root <protocol-2 1.51.0 fixture> --confirm-hosts-stopped` non-dry from a cwd outside the framework tree, asserts no `ModuleNotFoundError` or `upgrade_protocol_invalid`, the stub's recorded `--root`, `--pack` under `.wavefoundry/upgrade-assets/`, `--expected-pack-sha256` and `--yes`, and the exact top-level member set (AC-1, AC-2). `test_direct_zip_entry_resolves_a_future_function_level_import` adds `import index_paths` to `retain` in a copied `embedded_model_bundle.py` and asserts it loads from the zip (AC-3). `test_direct_zip_scripts_entry_follows_the_zip_root_and_skips_non_zips` pins index 1, the joined path, idempotence and the non-zip branch. Results: `run_tests.py --file test_upgrade_protocol.py` 54 OK; `--profile second --file test_upgrade_protocol.py` 0 of 1 failed. | `.wavefoundry/work/24buu/impl/24bn7/` |
| 2026-11-24 | Mutants: removing the `_add_bundle_scripts_path` call fails both end-to-end tests on both zips with `No module named 'contained_files'` (the known bad); `insert(0, ...)`, dropping the `is_zipfile` check, and dropping the `entry not in sys.path` check each fail the unit test. Adding `contained_files.py` as a member was not built: `_materializer`'s fixed `allowed_runner` set refuses any extra top-level member, which the AC-2 assertion also pins. | Mutant runs, `python3 -m unittest -k test_direct_zip` |
| 2026-11-24 | AC-4 deviation: `## [Unreleased]` already had a `### Fixed` heading (committed in `cbc69fb8`), so the entry goes under that heading rather than a second `### Fixed` heading, which Keep a Changelog does not use. `data-and-control-flow.md` now says the entry is not stdlib-only and resolves framework modules from its own scripts. | `CHANGELOG.md`, `docs/architecture/data-and-control-flow.md` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-24 | Plan this in wave 24buu. | Operator: "Make sure that the upgrade installs everything correctly with as little intervention as possible." | — |
| 2026-11-24 | Selected: resolve framework imports from the zip's own framework scripts, keeping the member set. Efficacy: replaying the rehearsal, `contained_files` imports from the zip and the materializer still sees today's members, so the documented command proceeds; it also covers future imports. | Planner default after red-team F3. | Add `contained_files.py` as a member: rejected by `_materializer` and by older runners' member checks. Remove the lazy import: drops the containment it enforces. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A module imported from the zip needs a compiled extension or data file zipimport cannot load. | The end-to-end test runs the real path; `contained_files` is pure Python. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
