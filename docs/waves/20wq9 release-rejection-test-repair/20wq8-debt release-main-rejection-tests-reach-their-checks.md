# Release rejection tests reach their checks

Change ID: `20wq8-debt release-main-rejection-tests-reach-their-checks`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-17
Wave: 20wq9 release-rejection-test-repair

## Rationale

Two release tests in `tests/test_build_pack.py` pass without reaching the code they are named for. `test_release_main_rejects_extra_current_build_public_package` should prove that `_enforce_single_public_package` refuses an extra public file left by the upgrade-bundle step, and `test_release_main_rejects_preexisting_special_upgrade_artifact` should prove that `_reject_stale_public_build_artifacts` refuses a stale upgrade `.pyz` already in the output folder. Both call `main()` with `--release-dry-run` but without `--with-models`, so `main()` exits 1 at its `--with-models` refusal before preflight, and both tests assert only exit code 1 plus a call that never happens. `_reject_stale_public_build_artifacts` has no other test. Wave 20wq7 noted this as a follow-up.

## Requirements

1. Both tests pass `--with-models`, so `main()` reaches the check each test names.
2. The model step never runs a real model build. The extra-package test stubs `model_bundle.build_bundle` with a function that writes a small placeholder companion zip into the output folder and returns its path, so the release's own existence check is satisfied. The stale-artifact test refuses before the model step; it also patches `model_bundle.build_bundle` and asserts it was not called, so a regression that moves the stale check later fails fast instead of starting a real model build.
3. Each test captures stderr and asserts the refusal names its cause: the extra-package test asserts `unexpected current-build package(s)` and both extra file names; the stale-artifact test asserts `stale public bridge/composition artifact(s)` and the stale file name. Each also asserts the patched qualification gate ran once, which proves preflight completed, and the extra-package test asserts the model stub ran once with the output folder. The extra-package test also asserts that stderr carries exactly one `error:` line and that it does not name the declared model companion, so a release that refused its own model asset would fail the test. The existing assertions stay.
4. Python allows at most 20 statically nested blocks per function, counting the outer `TemporaryDirectory`, each `with` item and the inner `assertRaises`. The extra-package test is already at 20, so it cannot take both additions inline. Both tests register the stderr capture and the model stub through `self.enterContext` for consistency, an idiom other framework test files already use.
5. Test-only change. No product code changes. Behaviour is the same on Windows, macOS, Linux and WSL2: the tests use temporary folders, `pathlib` paths and in-process stubs, with no subprocess or platform-specific path.

## Scope

**Problem statement:** two release rejection tests exit at an earlier refusal and so never test the checks they name.

**In scope:** Requirements 1 to 5 in `tests/test_build_pack.py`.

**Out of scope:** any change to `build_pack.py`, other release tests, and the 1.32.0 release itself.

## Acceptance Criteria

- [x] AC-1: Both tests pass. In a scratch clone each of these mutants fails the named test: `_enforce_single_public_package` returns immediately (extra-package test); `_reject_stale_public_build_artifacts` returns immediately (stale-artifact test, without calling the model step); the refusal text changes while the exit stays 1 (extra-package test); the `--with-models` refusal fires again (both tests); `_enforce_single_public_package` ignores `extra_expected` so the declared model companion is refused (extra-package test).
- [x] AC-2: Neither test calls the real model build. The evidence is the asserted stub: called once with the output folder in the extra-package test, and not called in the stale-artifact test.
- [x] AC-3: `test_build_pack` passes under the default profile, and one whole-suite `--no-cache` run passes with a fresh green receipt.

## Tasks

- [x] Add `--with-models`, the stderr capture, the model stub and the assertions to both tests.
- [x] Run the two mutants in a scratch clone.
- [x] Run `test_build_pack`, then the whole suite once.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| tests | implementer | none | Requirements 1 to 5 |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_build_pack.py`

## Affected Architecture Docs

N/A: a test-only repair inside one test file, with no boundary, flow or verification-architecture change.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The point of the change is that each test detects its own check failing. |
| AC-2 | required | The operator does not want the slow model build in these tests. |
| AC-3 | required | The receipt must be current before close. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-17 | Planned after a scratch prototype: both tests passed with the fix, and each named mutant failed only its own test. | scratchpad fixprobe |
| 2026-10-17 | Implemented by copying the reviewed prototype file, byte-identical to the scratch tree, under `framework_edit_allowed`. Focused `test_build_pack` 152/152. Delivery: code and QA lanes passed with fresh scratch mutants, five AC-1 mutants plus a stale-check-moved-later mutant. Follow-up, not taken (smaller work wins): red-team mutants R1 (stale check limited to `.pyz`), R2 (an old model companion over-flagged as stale), R3 (stray `.zip` extras ignored) and R4 (removed-package check disabled) pass both tests. The Decision Log's "extra-package test catches over-flagging" holds for normal release zips only. Direct unit cases of `_reject_stale_public_build_artifacts` over a mixed before-mapping would close R1 and R2. Gapfill: scratch-copy shell edits and runs, because the prototype lived outside the indexed tree. | scratchpad 20wq9-delivery.diff, qa20wq9, cr20wq9 |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-17 | Make the tests work rather than remove them. | `_reject_stale_public_build_artifacts` has no other test, and the fix is small. | Remove both tests, leaving the stale-artifact refusal untested. |
| 2026-10-17 | Readiness review folded in: model stub in the stale-artifact test, the single error-line assertion, the block-limit wording, and the mutant list in AC-1. | Code and QA reviewers. | Add an older allowed asset to the stale-artifact test to catch over-flagging; not taken, because the extra-package test already catches that mutant and smaller work wins. A direct unit test of `_enforce_single_public_package`; not taken, the `main()` tests already prove the wiring. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A later preflight change makes the tests exit early again. | The message assertions fail if the named refusal is not the one reached. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
