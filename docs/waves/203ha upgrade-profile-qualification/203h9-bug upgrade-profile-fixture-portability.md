# Make upgrade integration fixtures portable across vocabulary profiles

Change ID: `203h9-bug upgrade-profile-fixture-portability`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-08
Wave: 203ha upgrade-profile-qualification

## Rationale

Waveforge's October 7 addendum A1–A3 is addressed in the closed containment wave and its predecessor, but qualification still reports two failures under `second` and three under `prompt-names` in `test_upgrade_wavefoundry.py`. The remaining tests encode Python quote style or shipped prompt names and omit a manifest now required by the real profile migration. Repair these fixtures so the upgrade suite verifies the same contracts in renamed distributions. Prepare a factual handoff of the resolved requests and the qualification results.

## Requirements

1. Corrupt the actual container-name assignment whether its literal uses single or double quotes; retain rejection before phase 2c and exception identity checks.
2. Derive destination prompt paths, labels, and skill names from the active vocabulary profile while preserving literal historical migration inputs.
3. Positive review-protocol integration fixtures must provide the readable manifest required for profile migration and keep real rendering, byte-preservation, idempotence, and before-index checks.
4. Retain meaningful negative controls. Do not skip failures, reset the tested profile, weaken assertions, or change production upgrade behavior.
5. Report verified request coverage and limitations, including the unchanged old runner's final-line wording.

## Scope

**Problem statement:** Five upgrade tests fail under supported non-default test profiles because their fixtures or assertions assume shipped naming or source formatting.

**In scope:** The upgrade test owner, bounded regression controls, qualification under shipped/second/prompt-names profiles, and a Waveforge handoff under docs.

**Out of scope:** Production migration changes, broader feature-named filenames, held unknown hook-tool names, memory backfill, publishing a new pack, wave closure, and committing or pushing this new work.

## Acceptance Criteria

- [x] AC-1: Invalid replacement profiles are rejected before phase 2c under both Python quote styles and an alternate container name, preserving the exception class identity checks.
- [x] AC-2: Historical prompt rename integration validates active-profile destinations, exact prompt bytes, exact manifest entries, new skills, and removal of legacy artifacts under shipped and prompt-names profiles.
- [x] AC-3: Review-protocol integration succeeds with the manifest precondition under shipped and prompt-names profiles, preserving extensions, idempotence, and required carriers before indexing; a missing-precondition or unwired-render negative control remains detecting.
- [x] AC-4: The complete upgrade test owner passes under second and prompt-names with no new skips, and the handoff cites the verified request coverage, qualification evidence, and limitations.

## Tasks

- [x] Reproduce and investigate the profile failures without changing repository code.
- [x] Implement quote-tolerant fixture mutation and profile-derived assertions/preconditions.
- [x] Execute bounded regression and negative-control checks.
- [x] Run both focused profile qualifications and the full canonical framework suite.
- [x] Write the Waveforge request handoff and complete independent delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Fixture diagnosis | Guru investigator | — | Fresh read-only diagnosis of profile migration; root reproduces owner runs |
| Readiness review | Council chair and independent seats | Fixture diagnosis | Standard depth, receipt-selected docs-contract-reviewer rotating seat |
| Test repair | Implementer coordinator | Readiness review | Single test owner, serial edits |
| Qualification | Coordinator and independent QA | Test repair | Profile diagnostics plus canonical receipt |
| Delivery review and handoff | Independent reviewers and coordinator | Qualification | No closure or commit implied |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`

Only the coordinator edits the test owner. Profile runs are serialized through the canonical runner. Reviewers use bounded temporary probes and read-only inspection.

## Affected Architecture Docs

N/A: fixture and oracle repair within one existing upgrade test owner. No production boundary, protocol, runtime flow, or testing architecture changes; existing profile qualification machinery remains authoritative.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The invalid-profile guard must remain exercised |
| AC-2 | required | Migration must preserve content and use active naming |
| AC-3 | required | Real protocol rendering must remain exercised |
| AC-4 | required | Downstream qualification and a precise handoff are the requested outcome |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-08 | Second profile reproduces two failures in 681 tests, two existing skips; both quote-specific substitution counts are zero. Independent real-render probes confirm profile destinations and missing-manifest refusal. | Canonical focused runner; Guru profile_diagnosis temporary renderer probes |

| 2026-10-08 | Prompt-names baseline reproduces the other three failures: historical prompt rename destination, positive surface reconciliation, and full upgrade carrier checks before indexing. 681 tests, two existing skips. | `/tmp/wf-prompt-names-baseline.log`; real renderer probes distinguish missing-manifest precondition from destination-name assertions. |

| 2026-10-08 | Readback: AC-1–4 repair only the upgrade test owner and handoff. Historical inputs and exact bytes/manifest assertions remain independent; destinations follow the active profile (for example plan-feature migrates to plan-task under prompt-names). Thought: fixture assumptions cause all five failures. Action: decode the assigned literal independent of quote style, localize readable manifests, and add downstream nonexecution assertion. Memory playbook rechecked: real subprocess surface rendering and main-before-index checks remain; no runtime phase changes or moved-module reads. | Typed readiness approved; only `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` is code scope. |

| 2026-10-08 | Observe: six targeted shipped-profile checks pass with zero skips, including unchanged unwired-before-index detection. Three injected defects each fail the intended assertion: omitted profile refresh, premature downstream call, and changed migrated prompt bytes. | `/tmp/wf-profile-repair-focused.log`; `/tmp/wf-profile-repair-controls.py`. Implementer evidence is not independent delivery review. |

| 2026-10-08 | Both repaired profile qualifications pass the whole upgrade owner: second 681 tests / two existing skips / 43.810s; prompt-names 681 / two existing skips / 43.741s. AC-1–3 implementation verified; independent missing-manifest refusal probe and final canonical run underway. | `/tmp/wf-second-repaired.log`, `/tmp/wf-prompt-names-repaired.log`; source blob `f89d39d7dd3bea415852c8d8f7b7a802bc110925`. |

| 2026-10-08 | Independent QA: five prompt-name scratch tests pass with zero skips; missing manifest yields the expected notice and leaves renamed carriers absent. Independent code verifier: real migration passes; wrong shortcut, extra manifest entry, and missing generated plan skill each fail exact assertions. Both start/end source fingerprints match. | Fresh `qa_qualification` and `code_qualification` contexts; reports under this wave. Canonical run and typed delivery approval still pending. |

| 2026-10-08 | First canonical run executed 11,885 tests across 173 files, all test owners green, 20 existing skips, 432.531s; overall result FAILED because coordinator handoff/checkbox edits and reviewer report creation changed five docs during the run. No new receipt was written. Those exact docs are accounted for; freeze all repository writes and rerun. No source repair is needed. | `/tmp/wf-203ha-canonical.log`; repository-change guard names session-handoff, change doc, code-delivery, qa-delivery, and waveforge-handoff. |

| 2026-10-08 | Quiet-tree canonical run passed: 11,885 tests, 173 files, 20 existing skips, 431.917s. Fresh green receipt written; framework tree unchanged after execution. Handoff now contains all public R1–R9/A1–A3 mappings, both green profile runs and limits. Formal delivery review started. | `/tmp/wf-203ha-canonical-quiet.log`; `.wavefoundry/framework/test-cache.json`, input hash `dde11ab2ef7918216ee07fa1ab0244033acfd6bc8f590157818322a084e17c2f`. |

| 2026-10-08 | Independent code and QA delivery approvals recorded; all ACs/tasks complete, change status implemented. Closure dry-run validates docs and proves the current framework receipt; only operator signoff remains. No commit or push performed. | Typed ledger; `code-delivery.md`, `qa-delivery.md`, `waveforge-handoff.md`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-08 | Repair fixtures and derive expectations from the active profile. | Matches existing production contracts and keeps assertions exact. | Resetting fixtures to shipped names would stop testing distribution portability; relaxing production manifest guards would change trust behavior unnecessarily. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Dynamic expectations could hide incorrect migration | Keep historical inputs literal, assert exact bytes and manifest contents, and execute negative controls |
| Adding a manifest could mask the missing-manifest guard | Preserve or add a bounded refusal control alongside the positive fixture |
| Green focused runs could be mistaken for release evidence | Run the full canonical suite separately and identify profile runs as diagnostics |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
