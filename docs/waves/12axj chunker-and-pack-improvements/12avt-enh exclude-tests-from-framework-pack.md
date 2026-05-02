# Exclude Tests From Framework Pack

Change ID: `12avt-enh exclude-tests-from-framework-pack`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-05-01
Wave: TBD

## Rationale

The Wavefoundry framework test suite (`scripts/tests/`, `scripts/run_tests.py`) exists to verify the framework during development in this repository. Downstream repositories that vendor the pack via `wavefoundry-*.zip` have no use for these files — they contain no production code, and the seeds currently instruct downstream `AGENTS.md` and `build-and-verification.md` to run `run_tests.py` as a verification step, which fails silently or confusingly when the files are absent. Excluding tests from the distribution zip and correcting the seed guidance eliminates a class of misleading instructions in every seeded repo.

## Requirements

1. The packaged `wavefoundry-*.zip` must not include `scripts/tests/` or `scripts/run_tests.py`.
2. The Framework Script Hygiene Rule in `seed-050` (copied verbatim into downstream `AGENTS.md`) must not reference `run_tests.py` — it should note that tests are a development-only artifact in the Wavefoundry source repo.
3. The `build-and-verification.md` checklist template seeded by `seed-040` task 17 must not include a "Framework tests" step pointing at `run_tests.py`.
4. The upgrade verification checklist seeded into downstream `docs/prompts/upgrade-wavefoundry.md` by `seed-100` must not reference `run_tests.py`.
5. The install seed (`seed-010`) must not tell downstream repos to set up framework test hygiene for Python tests.
6. `seed-160` must list `scripts/tests/` (whole directory) and `scripts/run_tests.py` in its retire-stale-paths step so old-pack recipients clean them up on next upgrade.
7. `build_pack.py` exclusion list must be updated to match the new intent (tests excluded by design, not incidentally).

## Scope

**Problem statement:** Framework tests are a development artifact for this repo only. The pack currently ships them, and seeds instruct downstream repos to run them as part of upgrade verification — which is wrong once the files are excluded.

**In scope:**

- `build_pack.py` — add `scripts/tests` to `EXCLUDED_REL_PATHS`; add `scripts/run_tests.py` to a new per-rel-path exclusion
- `seed-050` Framework Script Hygiene Rule — reframe: no `run_tests.py` reference; downstream repos have no framework test suite
- `seed-040` task 17 — remove "Framework tests" step from `build-and-verification.md` checklist template
- `seed-100` upgrade verification checklist rule — remove `run_tests.py` from ordered steps
- `seed-010` install seed — remove Python test hygiene setup step
- `seed-160` retire-stale-paths — add `scripts/tests/` directory and `scripts/run_tests.py` as paths to delete on next upgrade

**Out of scope:**

- `seed-240` (package) — correctly tells the *Wavefoundry developer* to run tests before packaging; no change needed
- `wave_lint_lib/` — production code, never excluded
- pycache cleanup hook — not test-specific; no change needed
- AGENTS.md and build-and-verification.md in *this* repo — those correctly describe running tests here; no change needed

## Acceptance Criteria

- AC-1: `python3 .wavefoundry/framework/scripts/build_pack.py` produces a zip that contains no files under `framework/scripts/tests/` and no `framework/scripts/run_tests.py`.
- AC-2: A freshly seeded downstream `AGENTS.md` (from `seed-050`) contains no instruction to run `run_tests.py`.
- AC-3: A freshly seeded `docs/contributing/build-and-verification.md` (from `seed-040`) contains no "Framework tests" step.
- AC-4: A freshly seeded `docs/prompts/upgrade-wavefoundry.md` (from `seed-100`) contains no `run_tests.py` reference.
- AC-5: `seed-160` retire-stale-paths list includes `scripts/tests/` and `scripts/run_tests.py`.
- AC-6: Existing test infrastructure in this repo is unaffected — `run_tests.py` and `scripts/tests/` still exist and pass locally.

## Tasks

- [ ] Edit `build_pack.py`: add `scripts/tests` to `EXCLUDED_REL_PATHS`; add `scripts/run_tests.py` to exclusion logic
- [ ] Edit `seed-050`: reframe Framework Script Hygiene Rule — remove `run_tests.py`; note tests are Wavefoundry-dev-only
- [ ] Edit `seed-040` task 17: remove "Framework tests: `run_tests.py`" bullet from `build-and-verification.md` checklist
- [ ] Edit `seed-100`: remove `run_tests.py` from upgrade verification ordered steps
- [ ] Edit `seed-010`: remove Python test hygiene setup line from install seed
- [ ] Edit `seed-160`: add `scripts/tests/` dir and `scripts/run_tests.py` to retire-stale-paths block
- [ ] Verify: build a test zip and confirm `scripts/tests/` and `run_tests.py` are absent
- [ ] Run framework tests locally to confirm nothing was broken

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| build_pack.py exclusion | implementer | — | Single file, no deps |
| Seed edits (050, 040, 100, 010, 160) | implementer | — | All seeds independent; `seed_edit_allowed` guard required |
| Verification | implementer | both above | Build zip + test suite |

## Serialization Points

- `seed_edit_allowed` guard must be open for all seed edits; flip once, do all five, restore after.
- `build_pack.py` and seed edits are independent of each other and may proceed in parallel.

## Affected Architecture Docs

N/A — this change is confined to the framework packaging script and seed guidance. No module boundaries, control flows, or test topology changes. `docs/architecture/testing-architecture.md` documents the testing strategy for this repo, which is unchanged.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | | |
| AC-2 | | |
| AC-3 | | |
| AC-4 | | |
| AC-5 | | |
| AC-6 | | |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-05-01 | Change created | — |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-05-01 | Exclude `scripts/tests/` and `scripts/run_tests.py` from zip | Tests are Wavefoundry-dev-only; no downstream value; seeds currently mislead about their presence | Keep tests in pack (ruled out: adds ~15 files of zero value to every adoption; seeds reference them incorrectly) |
| 2026-05-01 | No change to `seed-240` or this repo's AGENTS.md | Both correctly describe running tests in the Wavefoundry source context | |

## Risks

| Risk | Mitigation |
| --- | --- |
| Old-pack recipients still have `scripts/tests/` on disk after upgrading | `seed-160` retire-stale-paths list will clean them on next upgrade (Req 6) |
| Downstream repos that somehow depend on `run_tests.py` existing | No downstream repo has any production code that imports or calls the test suite; the only reference is in operator-facing docs, which the seed fixes correct |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
