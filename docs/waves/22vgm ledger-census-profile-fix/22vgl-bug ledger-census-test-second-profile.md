# Run the Repository Ledger Census Test in the Default Profile Only

Change ID: `22vgl-bug ledger-census-test-second-profile`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-09
Wave: 22vgm ledger-census-profile-fix

## Rationale

The 1.41.0 release qualification failed under the second vocabulary and layout profile. One test, `CompatibilityTests.test_every_repository_ledger_lints_and_every_summary_line_re_renders` in `test_security_unsettled_disposition.py` (wave 22upa), errored with `FileNotFoundError`. The test surveys this repository's own wave ledgers, which are written in the default profile and named `wave.md`. It builds the record name from `vocabulary_profile.RECORD_FILENAME`, which is `set.md` under the second profile, so it looks for a file that does not exist. Shipped behavior is not affected; the release gate refuses the second report.

## Product Intent

Release maintainers get a passing second-profile qualification for 1.41.0 without a qualification exception. The test keeps checking every repository ledger in the default profile, and the second profile skips it with a recorded reason, the same treatment as the existing census in `test_review_policy.py`.

## Requirements

1. The census test is marked with `default_profile_only` from `record_layout_support`, with a one-line reason saying it surveys this repository's own records, written in the default profile.
2. The test's assertions are unchanged in the default profile.

## Scope

**Problem statement:** a test that reads this repository's real records resolves their file name through the active test profile, so it errors under the second profile.

**In scope:**

- The marker on the one test in `test_security_unsettled_disposition.py`.

**Out of scope:**

- Any change to shipped framework code.
- Other tests; the second-profile run reported no other failure.

**Platform behavior:** test-only and path-neutral; identical on Windows, macOS, Linux and WSL2.

## Acceptance Criteria

- [x] AC-1: Under the second profile, the test is skipped with the recorded reason and the second-profile qualification of the whole suite passes, and `qualification_report.py --compare` accepts it against the default report (the skip comes from a test marked `default_profile_only`).
- [x] AC-2: In the default profile the test still runs and passes, and the full suite passes with a fresh receipt.

## Tasks

- [x] Add the `default_profile_only` marker and its reason to the test.
- [x] Run the full suite, then the second and declared qualifications and both comparisons.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| marker | implementer | — | one decorator |
| qualification | implementer | marker | full suite, then profiles |


## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_security_unsettled_disposition.py`

## Affected Architecture Docs

N/A: a single test gains an existing marker; no boundary, flow or verification design changes.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The release gate needs a passing second-profile report. |
| AC-2 | required | The census must keep running where its subject exists. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-09 | Planned after the 1.41.0 second-profile qualification failed on this one test. | `.wavefoundry/cache/qualification/second.log` |
| 2026-11-09 | Implemented: `default_profile_only` on the census test plus its import. Default `--file` run: 32 tests, 0 skips. Full suite 12656 OK, receipt written (a first run was refused only because the coordinator edited CHANGELOG.md during it; rerun clean). Second and declared qualifications: 0 of 238 files failed; `--compare` equal for both (second: 22 default-only skips, all marked). | `.wavefoundry/cache/qualification/{default,second,declared}.json` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-09 | Mark the test `default_profile_only` | Its subject is this repository's default-profile records, the marker's documented use. | Hard-code `wave.md` (the tests avoid literal record names); release with a qualification exception (operator chose the fix). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The marker hides a real profile defect | The test reads repository records only; profile behavior of the code under test is covered by the file's other tests, which pass under both profiles. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
