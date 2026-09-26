# Retry the Setup Baseline When Cleanup Races the Reindex

Change ID: `1z1vr-bug upgrade-baseline-skipped-during-reindex`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-09-25
Wave: `1z1vs upgrade-baseline-retry`

## Rationale

Field report (a consumer upgrade to 1.27.0+psfj, 2026-09-25): `--cleanup` logged "Setup baseline not recorded (setup readiness: indeterminate)". `_record_setup_baseline` in `upgrade_wavefoundry.py` makes one `setup_readiness.assess_setup` call. While the post-upgrade index update is still writing, `assess_setup` sees its inputs change mid-assessment and returns `indeterminate` with reason `inputs_changed`. Three manual retries a moment later returned `ready`. The server records a missing baseline at the next start, so nothing is lost, but a clean upgrade ends with a misleading warning.

## Requirements

1. `_record_setup_baseline` retries the assessment when its status is `indeterminate` and every reason code is transient: `inputs_changed` or `probe_timeout`. It makes at most 4 attempts in total, waiting 2, 5 and 10 seconds between them.
2. Any other result is handled as today, with no retry: `ready` records the baseline, `action_required` or an `indeterminate` result with any non-transient reason logs the existing message.
3. If the last attempt is still transient-indeterminate, the existing "Setup baseline not recorded (setup readiness: indeterminate)" message is logged. The upgrade never fails on the baseline, as today.
4. `CHANGELOG.md` `[Unreleased]` gains a Fixed bullet.

## Scope

**Problem statement:** a transient readiness result at cleanup skips the setup baseline and warns on an otherwise clean upgrade.

**In scope:** the bounded retry in `_record_setup_baseline`, its tests, the changelog bullet.

**Out of scope:** waiting on the index build lock; changing `assess_setup`; the evaluator's stale-index refusal.

## Acceptance Criteria

- [x] AC-1: With `assess_setup` returning transient-indeterminate and then `ready`, cleanup records the baseline after retrying, and the waits requested are 2 then 5 seconds.
- [x] AC-2: A non-transient `indeterminate` result, or `action_required`, is not retried; a persistently transient result stops after 4 attempts and logs the existing message.
- [x] AC-3: The change's own tests pass, and the changelog entry validates.

## Tasks

- [x] Add the bounded retry to `_record_setup_baseline` with an injectable sleep.
- [x] Add tests for AC-1 and AC-2 in `test_upgrade_wavefoundry.py`.
- [x] Add the changelog bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Retry and tests | implementer | readiness | Single write owner |
| Review | code and qa reviewers | implementation | One combined reviewer |

## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`

## Affected Architecture Docs

N/A: a retry inside one function with no boundary, flow or contract change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The field symptom |
| AC-2 | required | Retries must stay bounded and never mask real problems |
| AC-3 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-25 | Implemented. `_record_setup_baseline` retries `assess_setup` while the result is `indeterminate` with at least one reason and every reason in `_TRANSIENT_SETUP_REASONS` (`inputs_changed`, `probe_timeout`), waiting 2, 5 and 10 s; `identity` is captured once before the loop; `time.sleep` resolves at call time (module imports unchanged). Tests in `PhaseCleanupSetupBaselineTests`: transient then ready records the baseline after waits [2, 5]; persistently transient stops after 4 attempts with the existing message; unproven, mixed, empty-reasons and `action_required` results are not retried. `test_upgrade_wavefoundry.py` 542 OK. Mutants killed by assertions: the non-empty-reasons guard dropped, the loop removed, the transient-code check removed. CHANGELOG `[Unreleased]` Fixed bullet added | tests/test_upgrade_wavefoundry.py |
| 2026-09-25 | Planned from the 1.27.0+psfj consumer upgrade report | operator-pasted upgrade transcript |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-25 | Retry only on transient reasons, bounded at 4 attempts | Matches the field recovery (a retry a moment later was ready) and cannot hide a real setup problem | Wait on the index build lock (couples cleanup to indexing internals); retry all indeterminate results (could mask real failures) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Cleanup takes up to about 17 seconds longer | Only on a transient result, which otherwise ends in a warning |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
