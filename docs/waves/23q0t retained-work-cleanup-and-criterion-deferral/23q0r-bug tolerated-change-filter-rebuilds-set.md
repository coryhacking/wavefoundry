# Tolerated-change filter rebuilds its set for every path

Change ID: `23q0r-bug tolerated-change-filter-rebuilds-set`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-17
Wave: 23q0t retained-work-cleanup-and-criterion-deferral

## Rationale

Change `23nqu` made the framework test runner tolerate documentation changes during a run. In `_stray_artifact_failure`, the step that removes tolerated paths from the changed list is `[rel for rel in changed if rel not in set(tolerated)]`: the set is rebuilt for every changed path, so the step is quadratic in the number of changed paths. The operator reported it after wave `23p89` closed. Confirmed by reading the line; not measured.

## Product Intent

A test run that overlaps a large documentation update finishes its repository check in time linear in the number of changed paths. Which paths are tolerated and which refuse the run does not change.

## Requirements

1. The tolerated paths are collected into one set before the filter, and the filter tests membership in that set.
2. The resulting changed list, the tolerated list, the refusal message and the receipt field are identical to today for every input.

## Scope

**Problem statement:** a per-path set rebuild in the runner's repository check.

**In scope:**

- The one filtering statement in `_stray_artifact_failure`.

**Out of scope:**

- Any change to which paths are tolerated, to `_tolerated_changes`, to the receipt or to documentation.

## Acceptance Criteria

AC-1 establishes the intent.

- [x] AC-1: The filter in `_stray_artifact_failure` builds the tolerated set once; the existing runner guard and reconciliation suites pass unchanged, with no test edited.
- [x] AC-2: The framework test suite passes after the edit.

## Tasks

- [x] Open `framework_edit_allowed`, make the edit, close the gate.
- [x] Run the runner guard and reconciliation suites, then the framework test suite last.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| filter-fix | implementer | (none) | One statement |


## Serialization Points

- `.wavefoundry/framework/scripts/run_tests.py`

## Affected Architecture Docs

N/A: one statement inside one function; no boundary, flow or verification change.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The reported defect, with behaviour held by the existing suites |
| AC-2 | required | Verification |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-17 | Planned from the operator's report. The statement was read at `_stray_artifact_failure`; the cost was not measured. No changelog entry is planned: the behaviour it touches is unreleased and unchanged. | `.wavefoundry/framework/scripts/run_tests.py` |
| 2026-11-18 | Implemented: `_stray_artifact_failure` now builds `tolerated_set = set(tolerated)` once and the filter tests membership in it; nothing else changed and no test was edited. Focused run `run_tests.py --file test_run_tests_repo_guard.py --file test_run_tests_reconciliation.py`: "Ran 93 tests across 2 files", OK. Full suite and the second profile ran after both owned changes (see `23phc`'s row). Located with `code_keyword`. | `.wavefoundry/framework/scripts/run_tests.py` |
| 2026-11-18 | Platform statement, added in the readiness repair pass: Windows, macOS, Linux and WSL2 behave identically; the change is platform-neutral (a set membership test inside one function). | Readiness repair pass, context `23q0t-readiness-repair-1` |
| 2026-11-18 | Coordinator check against the tree: the single statement is present in `run_tests._stray_artifact_failure`; covered by the full run of 2026-11-18 (12,968 tests, OK) and again by the final run below. Criteria and tasks ticked by the coordinator. |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-17 | Operator: "Building the set once before the comprehension fixes it without changing which paths pass." | The fix the operator named is the smallest one. | None considered. |
| 2026-11-17 | No new test. Planner's choice, not separately confirmed by the operator. | The change is behaviour-preserving and the existing suites pin the outputs; a timing test would be flaky. | A test counting set constructions, which would pin the implementation. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The edit changes which paths pass. | Requirement 2; the existing guard and reconciliation suites pass with no test edited. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
