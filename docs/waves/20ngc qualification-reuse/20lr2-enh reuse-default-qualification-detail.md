# Reuse default qualification detail

Change ID: `20lr2-enh reuse-default-qualification-detail`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-14
Wave: `20ngc qualification-reuse`

## Rationale

Final wave qualification already executes every default test. run_tests._main currently collects callback detail only when --qualification-report is supplied, so a later green cache hit cannot recover absent skip identities. Packaging then repeats the same work. Retain one bounded execution-detail cache from the actual full run and reuse it under the existing source receipt checks.

## Requirements

1. Capture the existing compact worker/skip detail during a complete top-level default qualifying run and retain one owned last-successful report in the ignored qualification cache. No transcript, source copy, timestamp-named history or wave evidence folder is created.
2. Reuse detail only with a current matching green framework receipt, complete passing report, exact framework input identity and discovered worker inventory. Preserve the runner's current authority boundary; a report alone never grants close or release authority.
3. An explicit packaging report request can reuse the matching retained report even when its requested output path differs. Missing, invalid, failed, partial or stale detail is unavailable and never reconstructed from aggregate counts. Cache hits never silently launch tests.
4. Focused, profile, schedule-control and failed runs cannot replace the last successful default detail or grant a default receipt. Source changes during execution invalidate qualification as today. Report-publication failure is surfaced separately without forging detail.
5. Update source-repository qualification and packaging guidance to consume one successful default run for wave and pack. Ordinary consumers/upgrades gain no tests, reports, downloads or new required files. Keep the fixed bounded report outside framework hashing and pack contents.

## Scope

run_tests and qualification_report integration, focused regression tests, source-project build/packaging guidance. No profile selection changes, new receipt type, copied qualification checkout, review-policy change or interpreter/dependency upgrade.

## Acceptance Criteria

- [x] AC-1: A complete controlled default run emits reusable exact worker/skip detail, and a subsequent packaging request for identical inputs invokes no worker; a subprocess trap verifies zero repeat execution.
- [x] AC-2: Changed source or worker inventory, absent detail, failed/partial workers and malformed reports cannot yield reused passing detail; existing cache-hit behavior remains explicit.
- [x] AC-3: Focused/profile/schedule-control and unsuccessful runs preserve the previous eligible default report and cannot create default qualification authority.
- [x] AC-4: Retained detail is capped, safely published at one owned ignored location, excluded from the pack, and the authored docs describe reuse and its limits without creating a consumer-upgrade requirement.

## Tasks

- [x] Integrate existing callback capture and bounded last-successful publication; preserve receipt sequencing and input-change guards.
- [x] Exercise real runner/report reuse with successful and rejecting controls; test alternative requested paths and output failure.
- [x] Update qualification and packaging instructions, record observed invocation savings and limitations in wave.md.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation | implementer | Readiness approval | Sole source write owner |
| Independent review | Required specialist lanes | Reviewable implementation | Read-only; report findings to coordinator |

## Serialization Points

Only the implementer edits the declared targets after readiness. Reviewers are read-only; the coordinator owns lifecycle records. Shared runner, server, policy, seed and prompt changes serialize with adjacent waves. Seed/default/prompt changes require existing edit guards and renderer ownership; do not hand-edit generated regions.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/run_tests.py`
- `.wavefoundry/framework/scripts/qualification_report.py`
- `.wavefoundry/framework/scripts/tests/test_run_tests_cache.py`
- `.wavefoundry/framework/scripts/tests/test_qualification_report.py`
- `docs/contributing/build-and-verification.md`
- `docs/prompts/package-wavefoundry.prompt.md`
- `docs/architecture/testing-architecture.md`

## Affected Architecture Docs

docs/architecture/testing-architecture.md and docs/contributing/build-and-verification.md: detail retention/reuse versus the unchanged receipt authority; docs/prompts/package-wavefoundry.prompt.md: consumption order.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-2 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-3 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-4 | required | Establishes the scoped behavior or preserves its boundary. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-14 | Planned from current source inspection; implementation and qualification pending. | Requirements and declared review targets above. |
| 2026-10-14 | Thought: Independent standard-depth readiness council reviews both shared runner/report changes, with isolated primer and fixed seats; architecture/code and QA/release remits may share a disclosed seat. Current available reasoning model retained for source-grounded boundary analysis; at most two council children run concurrently. | Coordinator is the writing hand; chair and seats are read-only, with finite existing-contract controls and no full suite. |
| 2026-10-14 | Observe: Required lanes and council approved readiness with no blockers; Prepare passed and Implement opened the wave. Readback: a complete default run will retain one bounded exact-detail report, and a later identical packaging request will reuse it without launching workers. A stale, partial or absent report remains unavailable; receipt authority does not change. | Shared run_tests/qualification_report owner, focused runner/report tests and build/packaging guidance. Memory brief: sandbox CLI-main fixtures, preserve real runner status, and keep unittest entry at EOF. |

| 2026-10-14 | Observe: Default retention/reuse and guidance implemented. Focused report tests passed 38 tests in 33.046s; cache tests passed 97 in 0.893s. Controlled repeat request exported the same run identity to a different path without launching a worker; stale, malformed, partial and absent detail refused. Nonqualifying/failed runs preserved last-successful detail. | test_qualification_report.py and test_run_tests_cache.py via project tool Python. Initial retained/requested run-ID mismatch was found by the new test and repaired before this pass. Canonical suite and independent delivery review remain pending for the combined wave. |

| 2026-10-14 | Guard-removal evidence: deleting the retained report source-identity comparison in an owned scratch runner caused QualificationCLITests.test_bad_or_absent_retained_detail_never_becomes_a_passing_report to fail its stale-source assertion; zero errors/skips. | Live source unchanged. The unmutated public CLI reuse control also proves a deliberate focused invocation trips the worker trap while cache export does not. |
| 2026-10-14 | Observe: Canonical default retry passed 11,621 tests across 187 files with 12 skips in 703.160s. A subsequent requested report exported all 187 workers with the same execution identity as last-default.json and printed exact-detail reuse without executing workers. | run_tests.py --qualification-report .wavefoundry/cache/qualification/20ngc-default.json; run identity 2e83eb33f0b545bdb530b5ff52715d77, framework input 476f7794c9adbbe1808ce6278e8fa56451520a642bb679506d5b983357bfb217. A separate profile-comparison repair will require qualification of the resulting source. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-14 | Select bounded automatic detail retention for qualifying default runs: it removes dependence on agents remembering an extra flag. | Avoid repeating the default suite solely to obtain packaging skip detail from an already qualified source tree. | Only document an optional flag: cheapest but repeats recur when final qualification omits it. Merge detail into the authoritative receipt: couples optional diagnostic schema to close authority and enlarges the trusted contract. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Contract regression or scope expansion | Stale detail could appear green or optional evidence could become a new authority gate. Require current receipt and exact identities; reuse the existing bounded report validator and safe publisher. |

## Session Handoff

Planned only. Prepare/readiness must pass before code edits. Keep durable decisions and final command/results in wave.md; compact execution detail stays in ignored cache or temporary storage. No new permanent evidence folder. See docs/agents/session-handoff.md for sequencing.
