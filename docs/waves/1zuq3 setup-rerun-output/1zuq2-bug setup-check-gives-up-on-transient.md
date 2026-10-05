# `wf setup --check` Gives Up On A Transient Readiness Result

Change ID: `1zuq2-bug setup-check-gives-up-on-transient`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-04
Wave: 1zuq3 setup-rerun-output

## Rationale

Field report (1.29.0+puha): right after `wf setup` finished, `wf setup --check` returned `indeterminate` with `inputs_changed` ("Setup-relevant inputs changed during assessment; retry.") and exited 2; a manual retry a moment later was `ready`. `inputs_changed` fires when a watched file (the index database or its WAL, the setup stamp, launch surfaces) changes during the assessment, typically an MCP server refreshing the index just after setup. Upgrade cleanup already retries this case (wave 1z1vs: `inputs_changed` and `probe_timeout`, waits 2, 5 and 10 s), but `wf setup --check` assesses once.

## Requirements

1. `setup_readiness` owns the transient rule: `TRANSIENT_REASONS` (`inputs_changed`, `probe_timeout`), `TRANSIENT_RETRY_WAITS` (2.0, 5.0, 10.0), `is_transient(result)` (indeterminate and every reason transient; no reasons is not transient) and `assess_setup_settled(root, *, sleep=None, notify=None, **kwargs)`, which retries a transient result after each wait and returns the last result. `sleep` resolves to `time.sleep` at call time (so tests can patch it), only the given `kwargs` are forwarded to `assess_setup` (the existing `assert_called_once_with(root)` pin in `test_setup_readiness_integration` holds), and `notify`, when given, is called with the wait before each retry.
2. The `--check` branch of `setup_wavefoundry.main` uses `assess_setup_settled` with a `notify` that prints one line per wait to stderr (for example `setup readiness is settling (inputs changed during the check); retrying in 2s`); stdout, the JSON and exit codes are unchanged.
3. A non-transient result is returned after one assessment (no added delay).
4. Out of scope and unchanged: upgrade cleanup's own copy of the rule (`upgrade_wavefoundry._setup_result_is_transient`, wave 1z1vs), the session-start hook (its short deadline must not grow), and `index_health` (an MCP tool should not block for up to 17 s; it already reports the retry reason).
5. CHANGELOG gets a bullet under `## [1.29.0]` `### Fixed`.

## Scope

**Problem statement:** a read-only check reports a transient as a failure with exit 2.

**In scope:**

- `setup_readiness` helper; `setup_wavefoundry` `--check`; tests; CHANGELOG.

**Out of scope:**

- Upgrade cleanup, the session-start hook, `index_health`, the stamp-after-Done ordering in setup.

## Acceptance Criteria

- [x] AC-1: `assess_setup_settled` with a transient then a ready result returns ready after one wait of 2.0 s; with a persistent transient it stops after four assessments with waits 2.0, 5.0, 10.0 and returns the transient result.
- [x] AC-2: A non-transient indeterminate, an action_required result, and an indeterminate with no reasons are returned after one assessment with no wait; a mixed transient and non-transient reason set is not retried.
- [x] AC-3: `wf setup --check` (through `setup_wavefoundry.main`) uses the settled assessment: a planned transient-then-ready sequence exits 0.
- [x] AC-4: Removing the retry from `--check`, or treating an empty reason list as transient, fails the tests (scratch copy).
- [x] AC-5: CHANGELOG describes the fix; docs validate.

## Tasks

- [x] Add the transient rule and `assess_setup_settled` to `setup_readiness`
- [x] Use it in `setup_wavefoundry` `--check`
- [x] Add tests
- [x] Show the mutants fail in a scratch copy
- [x] CHANGELOG bullet

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                  |
| ---------- | ----------- | ---------- | -------------------------------------- |
| check      | implementer | —          | setup_readiness, setup_wavefoundry     |


## Serialization Points

- `.wavefoundry/framework/scripts/setup_readiness.py`, `.wavefoundry/framework/scripts/setup_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_setup_readiness.py`, `.wavefoundry/framework/scripts/tests/test_setup_wavefoundry.py`

## Affected Architecture Docs

N/A: a retry inside one read-only command; no boundary or flow change.

## Platform Behavior

Identical on Windows, macOS, Linux and WSL2: `time.sleep` and the existing assessment. Worst case adds 17 s only while the result stays transient.

## AC Priority


| AC   | Priority | Rationale                              |
| ---- | -------- | -------------------------------------- |
| AC-1 | required | the retry itself                        |
| AC-2 | required | no delay or masking for real states     |
| AC-3 | required | the field-reported command              |
| AC-4 | required | the pins must catch a revert            |
| AC-5 | required | release notes                           |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-04 | Delivery review nits applied: CHANGELOG says the check retries before reporting (a still-transient result exits 2), and the stderr note reads `(a transient result)` instead of naming one reason | delivery reviewer; tests rerun OK |
| 2026-10-04 | Gapfill: edits used shell reads and scripted replacements because the running MCP server serves pre-change code for the edited files (`index_runtime_stale`); investigation before the wave used `code_keyword` and `code_read`, and reviewers read their own scratch copies | retrieval_posture_gap advisory |
| 2026-10-04 | Implemented: `setup_readiness.TRANSIENT_REASONS`, `TRANSIENT_RETRY_WAITS`, `is_transient`, `assess_setup_settled` (sleep resolved at call time, kwargs forwarded as given, notify per wait); `--check` uses it with a stderr note. The `PublicBootstrapTests` stub `setup_readiness` gained a delegating `assess_setup_settled` (the modules ship together). Tests: six retry cases and `--check` settling through `main` | `test_setup_readiness_integration` OK; scratch mutants D-F killed |
| 2026-10-04 | Readiness review folded in: `sleep=None` resolved at call time, kwargs forwarded as given, stderr note per wait | readiness reviewer findings 3-4 |
| 2026-10-04 | Planned from the 1.29.0+puha field report | `setup_wavefoundry.main` `--check` calls `assess_setup` once; `upgrade_wavefoundry._TRANSIENT_SETUP_REASONS`, `_SETUP_BASELINE_RETRY_WAITS`, `_setup_result_is_transient` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-04 | Leave upgrade cleanup's copy of the rule in place | it was just changed and pinned in wave 1zu53, and its tests spy on its own frames; consolidating it is a separate refactor | point upgrade at the new helper now (touches settled code for no behavior change) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A check takes up to 17 s longer | only while every reason is transient; real states return at once |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
