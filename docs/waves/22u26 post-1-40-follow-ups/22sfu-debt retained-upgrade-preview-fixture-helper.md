# Route the upgrade-preview close calls through the container fixture helper

Change ID: `22sfu-debt retained-upgrade-preview-fixture-helper`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-07
Wave: 22u26 post-1-40-follow-ups

## Rationale

Wave 22r99 added `close_container` and `create_container` in `tests/server_tools_support.py`, so a distribution can supply its required container arguments through the fork-editable `tests/container_fixture_profile.py`. It converted the 18 calls Waveforge reported. `tests/test_server_tools_lifecycle.RetainedUpgradePreviewTests` still calls the served `wf_close_wave` directly at three sites: two `(name, mode)` loops shared with `wf_prepare_wave`, and one direct default-mode call. Waveforge's run on `f489ba0a` passed them, so nothing fails today. A distribution whose profile requires a close argument would see those three sites fail on its next merge, and the guard test does not catch them because the loops pass the tool name through a variable.

## Product Intent

A distribution that fills in its container fixture profile sees every upstream `wf_close_wave` fixture call carry its arguments, with no exceptions to patch on merge. Upstream behaviour and the tests' assertions are unchanged.

## Requirements

1. Each `wf_close_wave` call in `RetainedUpgradePreviewTests` goes through `close_container`, with the same wave id, mode and result handling as today. The `call` adapter forwards `wave_id` and `mode` positionally, so `test_registered_actual_lint_previews_are_read_only_for_default_and_positional_modes` keeps its positional coverage.
2. The `wf_prepare_wave` and `wf_pause_wave` calls in the shared loops stay direct, and `"wf_close_wave"` no longer appears in those loop tuples.
3. `ConvertedFixtureCallGuardTests` covers the class and counts its helper calls.

## Scope

**Problem statement:** three close calls bypass the profile hook.

**In scope:**

- `tests/test_server_tools_lifecycle.py` (`RetainedUpgradePreviewTests` only) and `tests/test_container_fixture_profile.py` (the guard's scope table).

**Out of scope:**

- Other test classes, the helpers themselves, and any framework source.

## Acceptance Criteria

- [x] AC-1: With `container_fixture_args` patched to return `{"extra": 1}` for `wf_close_wave` and the served tool replaced by a recording spy (the real tool would reject `extra`), each of the three converted sites passes `extra=1`, and the positional site still passes `wave_id` and `mode` positionally; on the current code none passes `extra`.
- [x] AC-2: The guard's scope table includes `RetainedUpgradePreviewTests` with an exact helper count of 3, so a site reverting through a loop variable the guard cannot read by name still fails the count, and a reintroduced direct `self.mcp._tool_manager._tools["wf_close_wave"].fn(...)` call in that class fails the direct-call check.
- [x] AC-3: The change's own suites and every test it adds pass, the documents it edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Convert the three close sites, keeping prepare and pause direct.
- [x] Add the class to the guard scope table.
- [x] Probe AC-1 and AC-2 with the patched profile and a reintroduced direct call.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| tests      | implementer | —          |       |


## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`, `.wavefoundry/framework/scripts/tests/test_container_fixture_profile.py`

## Affected Architecture Docs

N/A: test-only. `docs/architecture/testing-architecture.md` (Profile-Aware Fixtures) already describes the helper; its text is unchanged.

## Platform Behavior

Test-only Python; identical on Windows, macOS, Linux and WSL2.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | important | The point of the change: profile arguments reach every close site. |
| AC-2 | important | Keeps the class converted. |
| AC-3 | required  | Change-local verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-07 | Planned at operator request ("let's do all of these"). Three direct sites found in `RetainedUpgradePreviewTests`. | `tests/test_server_tools_lifecycle.py` |
| 2026-11-07 | Readiness code and QA suggestions applied: positional adapter, recording spy for AC-1, close removed from the loop tuples, exact count in AC-2. | readiness review |
| 2026-11-07 | Implemented. A `positional_call` adapter on `RetainedUpgradePreviewTests` forwards wave id and mode positionally; the three close sites call `server_tools_support.close_container`, and the loop tuples name `close` instead of `wf_close_wave`. Guard scope `(LIFECYCLE, RetainedUpgradePreviewTests, 3)` added; `RetainedUpgradePreviewProfileTests` runs the three tests with a profile returning `extra=1` and a recording spy and asserts the exact four positional calls. `test_container_fixture_profile.py` 9 and `test_server_tools_lifecycle.py` 666 OK. Known-bad in a scratch copy: the original file fails 3 (spy, direct-call check, count); a loop-variable direct-call mutant fails the count and the spy. | implementation |
| 2026-11-07 | Full suite `run_tests.py --no-cache`: 12612 tests in 235 files OK, 12 expected skips, no framework bytecode (second run). The first run failed two files from this wave's own edits, both fixed before the second: `test_lifecycle_golden` (the 22r95 `conditional_fields` schema entry; golden regenerated through `check_golden` with both overwrite flags, diff exactly the three expected fixture paths, and the addition declared with its exact value in `test_only_declared_observability_additions_since_extraction_golden`) and `test_server_package` (22u24's new filesystem test read producers by path; now `framework_files.source_path`). | full suite |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-07 | Convert now rather than wait for a Waveforge report | Operator asked; the conversion is small and preventive | Wait for a downstream failure |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The read-only preview assertions change behaviour under the helper | With the shipped empty profile the helper passes arguments through unchanged; the existing assertions run as before |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
