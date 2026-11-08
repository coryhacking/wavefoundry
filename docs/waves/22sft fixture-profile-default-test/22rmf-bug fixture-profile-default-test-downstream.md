# Fixture profile default test fails downstream

Change ID: `22rmf-bug fixture-profile-default-test-downstream`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-07
Wave: 22sft fixture-profile-default-test

## Rationale

Waveforge merged `f489ba0a` and ran its full suite under its profile with its own arguments in `tests/container_fixture_profile.py`. One test failed: `tests/test_container_fixture_profile.py` `ContainerFixtureHelperTests.test_default_profile_adds_nothing`. It asserts that the live `container_fixture_profile.container_fixture_args` returns `{}` for both tools, and that the helpers pass the test's arguments through unchanged. The module is fork-editable so that a distribution fills it in, so every distribution that uses it fails this test (Waveforge's fails with `{'feature': 'fixture', 'kind': 'enh'} != {}`).

## Product Intent

A distribution that fills in the fork-editable fixture profile runs the fixture-helper tests unchanged and keeps the merge checks, while upstream still proves its shipped default adds nothing.

## Requirements

1. The helper pass-through check patches `container_fixture_profile.container_fixture_args` to return `{}` inside the test, so it verifies that the helpers pass the test's arguments through unchanged on any tree, whatever the distribution's profile returns.
2. The check that the shipped `container_fixture_args` returns `{}` for both tools moves to its own test marked `@default_profile_only` (from `record_layout_support`), so it runs upstream and skips under a renamed profile.

## Scope

**In scope:** `tests/test_container_fixture_profile.py` and the changelog bullet for the fixture profile.

**Out of scope:** the profile module, the helpers and every other test.

## Acceptance Criteria

- [x] AC-1: With `container_fixture_args` replaced by a profile returning extra arguments for both tools (as a distribution would edit it), the pass-through test passes and the shipped-default test fails, while under the default profile both pass. On the current code the single combined test fails under such a profile.
- [x] AC-2: The shipped-default test carries the `default_profile_only` marker, and the change's own suite and every test it touches pass, the documents it edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Split the test into a patched pass-through test and a default-only shipped-default test.
- [x] Demonstrate the known-bad on the current test with a simulated distribution profile.
- [x] Note the change in the changelog's fixture-profile bullet.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| tests      | implementer | —          |       |


## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_container_fixture_profile.py`

## Affected Architecture Docs

N/A: a test-only split with no boundary change.

## Platform Behavior

Pure Python test code; identical on Windows, macOS, Linux and WSL2.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The downstream failure Waveforge reported. |
| AC-2 | required | Change-local verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-07 | Planned from Waveforge's follow-up on `f489ba0a`; the failing assertion confirmed in `test_default_profile_adds_nothing`. The operator chose to fix it before tagging 1.40.0 and to keep the uv pin at 0.12.22. | Waveforge follow-up 2026-11-07; read of `tests/test_container_fixture_profile.py` |
| 2026-11-07 | Split `test_default_profile_adds_nothing` into `test_an_empty_profile_passes_the_test_arguments_through_unchanged`, which patches `container_fixture_profile.container_fixture_args` to the empty default and keeps the exact `self.calls` equality, and `test_shipped_profile_adds_nothing`, marked `@default_profile_only`. Changelog fixture-profile bullet updated. | `run_tests.py --file test_container_fixture_profile.py`: 8 tests OK |
| 2026-11-07 | Known-bad in a scratch copy of the scripts: with the profile returning Waveforge-style arguments (`feature`, `kind`, `scope`), the HEAD test fails, the new pass-through test passes and the shipped-default test fails (default vocabulary; it skips under a renamed profile). With `close_container` dropping its keyword arguments, the pass-through test fails. Gapfill: shell edits and probes on a single known test file. | Scratch `kb-22sft` probe output |
| 2026-11-07 | Full suite green after the change. | `run_tests.py`: 12,591 tests / 231 files / 12 skips OK; no framework bytecode |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-07 | Patch the profile inside the pass-through test and keep a separate default-only check. | Keeps the merge checks running downstream, which Waveforge preferred, while upstream still proves its default. | Mark the whole test `@default_profile_only`. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A distribution that keeps the default vocabulary profile still fails the default check | Such a distribution has not renamed anything and can leave the profile empty; Waveforge renames and skips. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
