# Anchor the historical-wave fixture to its own checkout

Change ID: `208v6-bug historical-wave-fixture-root`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-10
Wave: 20asl historical-wave-fixture-root

## Rationale

Local package qualification passes every second-profile worker but exact comparison fails because SignoffLatestStateTests.test_live_wave_records_parse_correctly skips by missing-path reason in the default worker and by its explicit default-profile-only marker in the renamed worker. The default fixture incorrectly treats server_impl.py parents[3] as the repository root. Its relative fallback happens to work from the repository root, but not the runner's tests-directory cwd. All three historical records exist. A disposable in-memory correction using the test file's root runs the existing assertions with zero skips; source remains unchanged. The operator's existing preference is to repair packaging failures through a wave rather than waive them; an optional local exception question remains pending and no exception is inferred.

## Requirements

1. Derive the fixture checkout from the test file's known framework/scripts/tests layout, independently of the loader's returned implementation-module location and current working directory.
2. Retain the same three historical records and all council/operator signoff expectations. Preserve the default_profile_only marker, relative fallback and genuinely-missing-corpus skip behavior; add no skips or reason exception to the comparator.
3. Prove the existing positive assertions execute from the real worker cwd and an unrelated cwd. Independently ensure an incorrect signoff fails the existing assertion rather than being skipped. Scope is test-only; no runtime, report, concurrency or upgrade policy changes.

## Scope

**Problem statement:** A loader-relative fixture root silently skips available historical evidence.

**In scope:** `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`, only the named historical-corpus method and directly necessary regression checks.

**Out of scope:** Production loader/layout changes, replacing historical records, qualification-reader exceptions, new profile markers/skips, weakened assertions, performance budgets and consumer upgrade work.

## Acceptance Criteria

- [x] AC-1: The existing historical-corpus method executes all three record comparisons with no unintended skip from the runner's tests cwd and from an unrelated cwd. Oracle: actual unittest execution and independent path/read observation.
- [x] AC-2: Incorrect council/operator evidence is caught by the existing assertions; a genuinely absent corpus retains the documented skip, and the explicit default-only marker still governs a renamed profile. Oracle: bounded negative controls and real profile worker output.
- [x] AC-3: Every existing signoff expectation remains unchanged, and the change's own suites and added checks pass. Oracle: assertion comparison and affected lifecycle test execution.

## Tasks

- [x] Correct only the named fixture's root and add directly useful cwd/negative controls if needed.
- [x] Verify both cwd cases and realistic non-vacuous negative controls.
- [x] Obtain independent code/QA delivery evidence and record profile qualification without an unapproved waiver.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Fixture repair | implementer/root | Current typed readiness | One writer, one test file |
| Verification | code-reviewer, qa-reviewer | Frozen repair | Independent executed controls |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`

## Affected Architecture Docs

N/A: this corrects one fixture's existing checkout lookup; production ownership and verification policy are unchanged.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Restore execution of already-available historical assertions |
| AC-2 | required | Preserve negative and honest-skip behavior |
| AC-3 | required | Preserve the signoff oracle and local regression protection |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-10 | Readback: anchor the one historical-corpus fixture to its test file; execute all three records and six unchanged signoff comparisons from worker and unrelated cwd, preserving missing-corpus fallback and default-only marker. One-line test-only edit; coordinator implementation avoids delegation overhead for this coupled lookup. | AC-1–AC-3; named fixture |
| 2026-10-10 | Default worker cwd reproduces one false missing-record skip; an in-memory test-root correction passes the same method with zero skips. Root-cwd control already passes through relative fallback. No source edit. | SignoffLatestStateTests.test_live_wave_records_parse_correctly; existing three records |

| 2026-10-10 | One-line repair implemented. Current decorated method passes from worker cwd; independent code lane observes all three actual reads and six unchanged comparisons from both cwd values. Separate council/operator withdrawals fail original assertions; absence and renamed marker skip explicitly; restoring old root exposes the false available-corpus skip. Existing class 2 tests/0 skips. No redundant new test or permanent evidence folder. | Frozen file blob `37d47e085e61cfb083b8450cfd88179c3ec21690`; lifecycle named method; code lane |

| 2026-10-10 | Affected lifecycle worker executes all 620 tests with 2 expected skips and no test failures, but runner exits red because coordinator updated this Progress Log during the run. It is not a green qualification or receipt. Final qualification runs in the owned isolated checkout with a quiet tree. | `run_tests.py --file test_server_tools_lifecycle.py`; quiet-tree diagnostic |

| 2026-10-10 | Operator explicitly confirms “just fix it.” The proposed fixture repair is implemented and independently approved; fresh exact-profile qualification is running, with no local exception selected. | Operator direction; current frozen test file |

| 2026-10-10 | Fresh isolated default qualification passes: 12,134 tests across 181 files, 12 skips, exit 0; affected lifecycle worker passes all 620 tests. Independent code/QA controls retain the six original assertions and reject current council/operator withdrawals. AC-3 complete; real-profile marker and exact comparisons still pending. | Frozen framework hash `c8d6a4134e202a505142cdd7ac3958048682eec85fad6207da27ac3671ffc88e`; named historical-corpus method |
| 2026-10-10 | Fresh isolated second-profile qualification passes: 12,126 tests across all 181 files, 28 skips, 1253.143s, exit 0. Exact comparator passes with 12 baseline skips and 16 explicitly marked default-only extras; no reason exception. Together with both independent withdrawal/absence controls, this completes AC-2. Declared-profile qualification remains a package gate, not an unexecuted claim of these scoped controls. | Same frozen framework hash; actual callback-origin default/second reports and `qualification_report.py --compare --profile second` |

## Decision Log

| Date | Decision | Reason and alternatives |
| --- | --- | --- |
| 2026-10-10 | Anchor this fixture to its own test file | Independent of loader refactoring and cwd. Rejected shifting the loader-relative parent by one: remains coupled to loader module layout. Rejected accepting the changed reason in the reader: retains a false skip and weakens exact proof. Rejected manufacturing duplicate corpus paths: makes qualification depend on artificial repository state. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Correct lookup exposes invalid historical expectations | Execute the actual unchanged three-record assertions before implementation; preserve failures rather than loosening them |
| A default-only census is mistaken for broad distribution coverage | Keep the existing marker and document its finite corpus boundary |

## Session Handoff

Prepare and independently review before source edit. Pause after verified delivery; packaging is blocked by exact reason comparison until this repair or an explicit local exception. No closure or commit requested.
