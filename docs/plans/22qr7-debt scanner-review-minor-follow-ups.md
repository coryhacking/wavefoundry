# Scanner review minor follow-ups

Change ID: `22qr7-debt scanner-review-minor-follow-ups`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-11-06
Wave: TBD

## Rationale

Wave 22qr6's delivery reviewers recorded three low-impact, non-blocking observations about the newly delivered scanner code. The operator chose to track them rather than fix them before closing:

1. **Test isolation.** `tests/test_scanner_input_limits.py` calls `load_server()`, which reloads the `wave_lint_lib` worker module. When `tests/test_scanner_worker_config.py` runs later in the same `unittest` process, it patches a stale module object: 1 failure and 2 errors. `run_tests.py` runs each file in its own process, so the canonical suite is green.
2. **Guidance undercount.** `scanner_skips.incomplete_guidance` counts fixed-limit files from the completion `incomplete` list, which is truncated to 50 rows. Beyond 50 such files, its "N of them" figure undercounts. Each row's remedy is still correct.
3. **Trailing-newline anchor.** In the non-upstream (Python `re`) path matcher, `$` also matches before a trailing newline. The suggested anchored entry for path `x` therefore also excludes a path named `x` followed by a newline. The upstream translator emits `\Z` and is exact. The security reviewer judged this not a defect.

## Product Intent

Maintainers can run the scanner tests in any runner without false failures, operators see accurate counts, and suggested allowlist entries match exactly one path on every matcher. Detection and completion policy are unchanged.

## Requirements

1. The two scanner test modules pass when run together in one `unittest` process.
2. The fixed-limit count in `incomplete_guidance` reflects every outstanding fixed-limit file, not only the truncated rows.
3. A suggested allowlist entry matches exactly its own path on both the Python and the upstream path matchers.

## Scope

**In scope:** the two test modules' module handling, `scanner_skips.incomplete_guidance` counting, and the allowlist anchor or Python path-matcher end-anchoring.

**Out of scope:** scanner policy, worker protocol and limits.

## Acceptance Criteria

- [ ] AC-1: Running `test_scanner_input_limits` and then `test_scanner_worker_config` in one `unittest` process passes; on the current code it gives 1 failure and 2 errors.
- [ ] AC-2: With more than 50 fixed-limit files outstanding, the guidance reports the full count; on the current code it reports at most 50.
- [ ] AC-3: The suggested entry for `x` does not exclude `x` followed by a newline on the Python matcher; on the current code it does.
- [ ] AC-4: The change's own suites and every test it adds pass, the documents it edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [ ] Make the worker-config tests resolve the worker module at test time, or isolate the reload.
- [ ] Count fixed-limit files from the untruncated outstanding set.
- [ ] Use an end anchor that is exact on the Python matcher.
- [ ] Add regression tests with known-bad controls.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| scanner    | implementer | —          |       |


## Serialization Points

- `.wavefoundry/framework/scripts/scanner_skips.py`, `.wavefoundry/framework/scripts/wave_lint_lib/`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: confined to the scanner module and its tests, with no boundary change.

## Platform Behavior

Pure Python; identical on Windows, macOS, Linux and WSL2.

## AC Priority


| AC   | Priority     | Rationale |
| ---- | ------------ | --------- |
| AC-1 | important    | Prevents false failures under alternate runners. |
| AC-2 | nice-to-have | Cosmetic count accuracy. |
| AC-3 | nice-to-have | Edge case with no realistic filenames. |
| AC-4 | required     | Change-local verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-06 | Filed from wave 22qr6 delivery review notes at operator request. | 22qr6 code, QA and security delivery approvals (limitations) |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-06 | Deferred from 22qr6. | Low impact; fixing would have required a fresh qualification and recheck before close. | Fix in 22qr6 |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Changing the anchor alters existing allowlist semantics | Apply only to newly suggested entries, and test both matchers. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
