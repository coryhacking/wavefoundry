# Profile Source History Censuses

Change ID: `21szl-bug profile-source-history-censuses`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-27

## Rationale

Packaging's renamed-profile diagnostic reproduces two assertion failures in 18 tests: credible-threat carrier census includes nine old wave documents and the intent ledger census finds zero ledgers. The second profile configures live records at docs/delivery/sets and read-only ARCHIVE_ROOT at docs/waves; both tests currently account only for live roots. Default qualification passes. Production behavior is unchanged.

## Product Intent

Framework maintainers can qualify the renamed profile without skipping valid source-history checks: historical records are not active policy carriers, and historical ledgers are still validated. AC-1 and AC-2 establish the intended outcome; AC-3 protects the negative oracles. No cross-platform runtime claim is made.

## Requirements

1. Carrier exclusions include configured live waves, plans and the optional read-only archive, using slash-delimited root boundaries; absent archive adds no exclusion. Active policy carriers outside record roots remain checked.
2. Ledger census includes configured live and optional archive roots, deduplicates discovered paths, preserves the non-vacuity threshold and validates every selected ledger exactly as before.
3. Focused regressions exercise nondefault archive names and no archive, active malformed carriers, and malformed archived ledger content. No skip, profile-only waiver or lowered assertion replaces execution.

## Scope

In scope: .wavefoundry/framework/scripts/tests/test_credible_threat_unknown_factor.py and .wavefoundry/framework/scripts/tests/test_intent_fit_approvals.py only, plus this wave's docs. Existing test-only helpers may be refactored locally in those files.

Out of scope: production modules, profile definitions, skip policies, framework seeds, version stamps, root changelog and packaging mechanism.

## Acceptance Criteria

- [x] AC-1: A renamed-profile carrier census excludes live/planned/archive records while still reporting a malformed active carrier; root-prefix siblings are not accidentally excluded.
- [x] AC-2: Ledger discovery includes archived and live ledgers without duplicates, retains the >100 corpus assertion and detects malformed archived ledger content.
- [x] AC-3: Both reported profile failures pass after repair, and restoring each old root assumption causes a meaningful assertion failure.
- [x] AC-4: The change's own suites and every test it adds pass; the documents this change authors or edits validate; no failure elsewhere is attributable to this change.

## Tasks

- [x] Repair carrier exclusions and regression controls.
- [x] Repair ledger discovery and regression controls.
- [x] Run focused default/renamed checks and known-bad controls.
- [x] Run canonical qualification and independent delivery review.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes false active-carrier classification |
| AC-2 | required | Restores real historical-ledger coverage |
| AC-3 | required | Repairs the motivating failures without vacuity |
| AC-4 | required | Change-local quality |

## Affected Architecture Docs

N/A: test-only root census repair; existing record_paths live/archive contract is unchanged.

## Agent Execution Graph

Coordinator implements the two coupled tests. Fresh independent code/QA and required council review assess execution and negative controls.

## Serialization Points

Review targets: `.wavefoundry/framework/scripts/tests/test_credible_threat_unknown_factor.py`, `.wavefoundry/framework/scripts/tests/test_intent_fit_approvals.py`.

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-27 | Use configured live plus archive roots in the existing local censuses | second.json explicitly preserves default history under ARCHIVE_ROOT, so root enumeration directly controls both failures; assertions remain meaningful. Measure by focused profile checks and malformed input controls. | Hardcode docs/waves: ignores custom archives. Skip source-history tests in renamed profiles: drops coverage and hides corruption. |

## Progress Log

2026-10-27: Observe: canonical12,290tests/214files/12skips/554.293s passed receiptf861fea905b8721e19ccbe8ff7a3249a7f6dd84957264a7ec9977de9e9d36f29; defaultreportexported. Maintained mutant reproduction: import each test module in tool-venv Python -B; patch carrier excluded to original live/plans-only predicate and run test_archive_exclusion_keeps_active_and_prefix_sibling_carriers; patch repository_ledgers to original live-only glob and run test_live_and_archive_corpus_keeps_corruption_detection. Each must record one assertion failure, no errors/skips; no shared-source mutation. Default source and second focused tests pass both regressions. Fresh independent delivery now checks frozen two-file hashes; no sourceedit after qualification.

2026-10-27: Observe: default focused20 tests/2.837s and renamed focused20/2.905s pass, zero errors/skips. Both old-assumption runtime mutants independently fail their named new regression with exactly one assertion failure and no errors/skips. Initial new fixture patch.object keyword typo caused one error; corrected before final runs. Source frozen: carrier730e7d6363852eedfcb93c2d129635b565a5d015; intentc6b56fa7ea78c3167a158ef51b969cc39160caeb. Framework gate closed. Thought: canonical suite on frozen source, then fresh independent delivery.

2026-10-27: Readback: both censuses must account for configured archive history. Carrier scope excludes wave/plan/archive record trees but still catches malformed active carriers and prefix siblings; ledger discovery unions live/archive roots without duplicates, keeping the actual corpus threshold and each ledger validation. Only the two test files change. Before: renamed profile sees nine historical false positives and zero ledgers; after: active carriers remain checked and real historical ledgers remain validated. Coordinator owns both narrow edits, focused controls and qualification; independent delivery code/QA and Council follow on frozen source. No code change before readiness.

2026-10-27: Failure reproduced before edits: 18 tests, two assertion failures, no skips/errors in renamed-profile diagnostic. MCP code_read verified profile/record_paths contract and both test seams. No production-source change intended.

## Session Handoff

See docs/agents/session-handoff.md.
