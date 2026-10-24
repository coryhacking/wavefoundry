# Pyproject Build Backend and License Metadata

Change ID: `21ij7-bug pyproject-build-backend-and-license-metadata`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-24
Wave: 21ilf waveforge-1-36-follow-ups

## Rationale

The root `pyproject.toml` cannot be built.

- `build-backend = "setuptools.backends.legacy:build"` names a module that no setuptools release ships, so PEP 517 fails at backend import.
- With the backend corrected, setuptools refuses the file. It has both the SPDX `license = "Apache-2.0"` string and the `License :: OSI Approved :: Apache Software License` classifier, which PEP 639 forbids together.
- The SPDX string needs setuptools 77 or later, but `requires = ["setuptools>=68"]` allows older.
- Automatic package discovery would ship the repository's `experiments/` scripts as a top-level `experiments` directory in the wheel.

A downstream distribution reported all four, built offline with setuptools 79.0.1 and Python 3.11.15. Nothing in the framework builds this file today. Only `tests/test_setup_index.py` reads its dependency list.

## Product Intent

Anyone who builds the repository with standard Python tooling gets a valid, empty metadata wheel instead of an import error or a wheel carrying experiment scripts. Before: the build fails at backend import. After: an offline PEP 517 build succeeds and the wheel holds only its `dist-info`. Boundaries: no change to how Wavefoundry is distributed (the zip pack) or to its declared dependencies.

## Requirements

1. `build-backend` is `setuptools.build_meta`.
2. `requires` is `["setuptools>=77"]`.
3. The license classifier is removed; the SPDX `license` string stays.
4. `[tool.setuptools]` declares `packages = []`, so the wheel ships no code.
5. A test pins requirements 1 to 4 by reading the file.

## Scope

**Problem statement:** the build metadata is invalid and would package experiment scripts.

**In scope:**

- `pyproject.toml` at the repository root.
- A metadata test in `tests/test_setup_index.py`.

**Out of scope:**

- Making Wavefoundry pip-installable.
- Changing the dependency list or the version field.

## Acceptance Criteria

- [x] AC-1: An offline PEP 517 wheel build of a copy that includes the working-tree `pyproject.toml` (a `git archive` of `git stash create`, or a committed-tree archive with the edited file overlaid) succeeds, run with `pip wheel --no-build-isolation --no-index --no-deps --check-build-dependencies` in a Python 3.11 venv with setuptools 77 or later. The wheel's file list holds only `*.dist-info/` entries. Known-bad: the same command on the committed file fails with `BackendUnavailable: Cannot import 'setuptools.backends.legacy'`.
- [x] AC-2: The metadata test fails if the backend, the floor, the classifier removal or the empty package list regresses.
- [x] AC-3: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Edit `pyproject.toml` (four fields).
- [x] Add the metadata test.
- [x] Run the offline build and record the wheel listing in the Progress Log.
- [x] CHANGELOG Unreleased entry (Fixed).

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| metadata   | implementer | —          |       |


## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_setup_index.py`
- pyproject.toml at the repository root (a root-level file, declared here as prose)

## Affected Architecture Docs

N/A: build metadata only; no runtime boundary, flow or verification seam changes.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | the reported build failure |
| AC-2 | important | keeps the fix from regressing |
| AC-3 | required | change-local suites and docs |


## Progress Log


| Date       | Update  | Evidence |
| ---------- | ------- | -------- |
| 2026-10-24 | Planned | Waveforge 1.36.0 follow-up; backend and classifier confirmed in `pyproject.toml` lines 2-3 and 20 |
| 2026-10-24 | Readiness round 1 amendment: AC-1 builds a copy carrying the uncommitted fix (a plain `git archive HEAD` would rebuild the known-bad) and quotes pip's actual `BackendUnavailable` line. Readiness replayed both: known-bad fails, the four edits build a dist-info-only wheel. | readiness qa-reviewer, code-reviewer |
| 2026-10-24 | Readiness round 2 note: `tests/test_setup_index.py` is shared with 21goe; the metadata test is a separate test from 21goe's pin assertions. | readiness code-reviewer recheck |
| 2026-10-24 | Readback: `pyproject.toml` gets `setuptools.build_meta`, `setuptools>=77`, no license classifier and `[tool.setuptools] packages = []`; a metadata test in `tests/test_setup_index.py`, separate from 21goe's tests, pins the four fields (AC-2); the offline build of a copy carrying the edit yields a dist-info-only wheel (AC-1). Files: `pyproject.toml`, `tests/test_setup_index.py`. | implementation |
| 2026-10-24 | Implemented. AC-1: offline `pip wheel --no-build-isolation --no-index --no-deps --check-build-dependencies` in a Python 3.11 venv with setuptools 84: the committed file (`git archive HEAD`) fails with `BackendUnavailable: Cannot import 'setuptools.backends.legacy'`; the archive with the edited file overlaid builds `wavefoundry-1.0.0-py3-none-any.whl` holding only `wavefoundry-1.0.0.dist-info/` entries (licenses/LICENSE, licenses/NOTICE, METADATA, WHEEL, top_level.txt, RECORD). AC-2: `test_pyproject_builds_a_metadata_only_wheel` pins the four fields; each assertion fails against the committed file. | implementation |
| 2026-10-24 | Delivery note: the wheel reports version `1.0.0` from `pyproject.toml` while `VERSION` is 1.36.x; the wheel carries metadata only and is not the distribution, so aligning the version is out of scope. | delivery review |
| 2026-10-24 | Final full suite after delivery repairs: `run_tests.py --no-cache` ran 12100 tests across 208 files, OK; the framework test receipt is current. | `scratchpad/21ilf-full-2.log`; `.wavefoundry/framework/test-cache.json` |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-10-24 | Fix the four fields and declare no packages | Smallest change that builds; the zip pack stays the distribution | Delete `pyproject.toml` (loses the dependency list `test_setup_index` checks); package the scripts (a distribution model change) |
| 2026-10-24 | Mechanism efficacy | Replay: the reported build fails at backend import and then on the classifier; both fixes are in the file, and AC-1 replays the build. Control: the file decides the build outcome. Wrong flags: none. Cheaper path: none. Measure: the distribution drops its local fix. | — |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Hosts with setuptools older than 77 can no longer build | The floor reflects the SPDX string's real requirement; older setuptools could not build it correctly before either |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
