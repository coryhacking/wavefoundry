# Qualification report refusal and publication boundaries

Change ID: `20cyo-bug qualification-report-boundaries`
Change Status: `implemented`
Owner: implementer
Status: implemented
Last verified: 2026-10-11
Wave: 20d90 qualification-report-boundaries

## Rationale

Provide framework maintainers with predictable optional report failures and contained publication, using the existing report format and file helpers. Scratch decoder-failure controls show that `qualification_report.read_report` lets injected `RecursionError` and `MemoryError` escape; a switched final in-root link between report preflight and write is followed by the generic writer. The report's stricter lexical link policy must survive publication.

## Product Intent

Optional release diagnostics should refuse malformed observations and unsafe targets clearly while preserving existing canonical test-receipt authority. Governing context: `docs/contributing/build-and-verification.md`, Optional compact qualification reports.

Design Intent: N/A — no UI surface changes.

## Requirements

1. `qualification_report.read_report` converts JSON decoder `RecursionError` and `MemoryError` into the existing caught refusal vocabulary, without treating the input as a valid report or exposing an uncaught traceback through `main`.
2. `qualification_report.write_report` holds its no-link policy across every lexical parent and the final component through commit: revalidate lexical parents against the held parent descriptor and refuse pathname publication if a parent was renamed or substituted; the final component must be unlinked when judged for commit. Use contained atomic descriptor publication, preserve the ownership check, byte cap and permission behavior, and leave the original report and alternate targets unchanged on a detected substitution. Do not change the generic writer's existing acceptance of safe in-root links for other consumers. Document the exact POSIX descriptor and native-Windows fallback guarantees; do not claim exclusion of every adversarial same-user rename in the final check-to-commit interval.
3. Document that the worker nonce is visible to code in the test process and provides protocol correlation, not authentication against that process. Qualification reports and comparisons are diagnostic observations, not canonical receipts or independent execution attestation.
4. Retain ordinary-run opt-in behavior and existing comparison semantics; introduce no new receipt or close gate.

## Scope

In scope: the source symbols named in Requirements and Discovery evidence, their tests listed below, directly necessary contained-helper edits, and the named architecture/build guidance.

Out of scope: new receipt gates, general frameworks, release packaging, index rebuilds, unrelated host hooks/prompts, history rewriting, commits and wave closure. Optional bytecode exemptions are not admitted.

## Acceptance Criteria

- [x] AC-1: Decoder resource failures produce a caught refusal from `read_report` and nonzero concise CLI refusal from `main`; a valid owned control still loads. Focused decoder controls must fail without normalization.
- [x] AC-2: Checkpoint controls substituting a final link or renaming/substituting a held parent before commit produce refusal, preserve original report bytes and every alternate target, and do not publish through the changed pathname. Valid unchanged-parent descriptor publication passes. Platform-specific tests and guidance state their actual guarantee and final check-to-commit limit; these controls distinguish the current behavior.
- [x] AC-3: Normal first publication and owned replacement remain complete atomic JSON with the intended mode; unowned, oversized, special and linked targets refuse without truncation. Focused tests check cleanup of temporary publication files.
- [x] AC-4: The edited guidance accurately states worker-visible nonce correlation and report diagnostic authority, verified against `qualification_worker._run`, `qualification_report.worker_detail` and runner receipt behavior; no receipt gate is added.
- [x] AC-5: This change's focused suites and added tests pass, its authored/edited docs validate, and no failure elsewhere is attributable to this change; each new boundary regression rejects a fix-absent control.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Malformed-input refusal. |
| AC-2 | required | Publication boundary. |
| AC-3 | required | Compatibility and atomicity. |
| AC-4 | required | Authority clarity. |
| AC-5 | required | Scoped verification. |

## Tasks

- [x] Add decoder refusal and switched-parent/final publication regressions with valid controls.
- [x] Implement report-specific no-link atomic publication, reusing contained helpers with only directly required helper changes.
- [x] Update nonce/diagnostic authority guidance and architecture boundary notes.
- [x] Run focused tests and independent boundary review; reconcile AC evidence before canonical qualification.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Reproduction and minimal repair | implementer | Readiness and activation | Python stdlib, contained I/O, regression controls; one write owner. |
| Documentation reconciliation | implementer | Repair behavior stable | Named docs only; no new report/evidence folder. |
| Independent delivery review | code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer | Current implementation | Read-only; Council synthesizes; coordinator owns state. |

## Serialization Points

- `.wavefoundry/framework/scripts/qualification_report.py`
- `.wavefoundry/framework/scripts/contained_files.py`
- `.wavefoundry/framework/scripts/qualification_worker.py`
- `.wavefoundry/framework/scripts/tests/test_qualification_report.py`
- `docs/contributing/build-and-verification.md`
- `docs/architecture/testing-architecture.md`
- `docs/architecture/cross-cutting-concerns.md`

The implementer exclusively owns listed source/test/doc edits during activation; review lanes remain read-only. Protected: canonical seeds, generated agent/platform surfaces, root AGENTS.md, workflow/repo-profile config, qualification/test receipts, shipped ownership fixture, Git and history. No protected-surface edit is planned; directly necessary helper or fixture changes require coordinator scope check. Other waves touching shared modules must finish/pause before activation; never edit another wave's artifacts.

## Affected architecture docs

- `docs/architecture/testing-architecture.md`: reconcile only this change's boundary or verification contract.
- `docs/architecture/cross-cutting-concerns.md`: reconcile only this change's boundary or verification contract.

No new ADR or architecture restructuring is planned.

## Knowledge Transfer Plan

Record focused regression names, fix-absent outcomes and material limits in this change's Progress Log and wave.md. Preserve custom-prose/newline and real-producer fixture cautions from project memory; a guard is complete only when its absence is detected. Keep scratch captures outside the repository; no permanent evidence folder.

## Persona Review Plan

Use the material specialist lanes declared by wave.md; framework-operator concerns are incorporated into their refusal/retry review rather than a separate blanket persona pass. Product-owner and additional persona/factor lanes are requested only when Prepare policy derives them or a material scope finding justifies them. Existing policy-derived lanes and Council authority remain binding.

## Wave Readiness Plan

Coordinator performs docs validation, independent required specialist lanes and Council readiness, then final ready-only Prepare. Implementation requires clean typed readiness and later single-OPEN activation. Operator authorized preparation/review/implementation; this planner owns docs only. Existing open wave remains open until its coordinator pauses it.

## Watchpoints

Use generic fixtures and source anchors only. Report changed assumptions before implementation. Partial failure and skipped safety refusals stay visible. Reuse current matching evidence; never mint receipts manually or copy raw transcripts into docs.

## Progress Log

Readback: AC1–5 repair optional report parsing and publication only. A decoder RecursionError/MemoryError becomes the existing caught refusal; a swapped final link, held-parent substitution or changed owned-file identity refuses while preserving original/alternate targets. Every successful branch, including identical bytes and mode-only handling, must carry the initial ownership/no-link judgment; valid first publication and owned replacement remain atomic mode0600 JSON. Generic writer safe in-root link behavior and canonical receipt authority stay unchanged. Named report/helper/worker-comment/tests and architecture/build guidance only; no seed, host, index, pack, history or lifecycle-gate change. Current status/evidence belong here and in wave.md; the final plan handoff is a retained planning-time snapshot, not current delivery authority.

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-11 | Planning discovery completed; implementation pending. | executed: injected decoder failures escaped as their original exception classes; switched final link modified an ordinary alternate owned JSON file. These temporary fixtures were removed. Direct deeply nested JSON behavior was not established reliably and is not a load-bearing claim. source-inspected: `output_path`, `write_report`, `contained_files.write_contained_bytes`, `qualification_worker._run`, `qualification_report.main`. |


Thought: Complete the report-only boundary repair under the admitted readiness, retaining generic contained-writer behavior. Coordinator checked the optional strict flags inside the existing helper; no new source/fixture target is needed.

Observe: `_decode_report` normalizes injected JSON decoder recursion/memory failures. `write_report` carries the descriptor identity of the initially owned bytes (or initial absence) into `write_contained_bytes(no_links=True, expected_identity=...)`. Strict writes atomically replace even identical content and mode-only cases so no success branch bypasses commit checks; the helper still returns whether bytes changed, and generic writers retain their early unchanged-byte optimization and safe in-root links. Existing 8 MiB serialization/read caps, mode0600, JSON format, comparison semantics and receipt authority remain unchanged.

Observe: Direct focused runs passed `test_qualification_report` (31 tests before the last final-link/fallback controls) and `test_contained_files` (42 tests, one existing platform skip). The final focused runner's 103 assertions passed across report/contained/contained-repo suites, but its exit was 1 because AC bookkeeping concurrently changed the change doc. That invocation is invalid as runner-success evidence; quiet final focused verification remains required. New tests executed without skips on macOS; POSIX-specific descriptor cases are intentionally unavailable on native Windows, which was not executed. Native by-path parent-renaming can leave a moved temporary unreachable for cleanup; the guidance states this limit and the final check-to-commit windows rather than promising descriptor equivalence.

Observe: Eleven faithful focused mutants each exited 1 with the named assertion failure and no setup error. Remove decoder normalization → `test_decoder_resource_failures_are_refused_by_reader_and_cli`; deselect strict report policy → `test_commit_refuses_final_link_for_changed_identical_and_mode_only_bytes`; recapture the final identity by path after reading owned bytes → `test_substitution_after_owned_read_cannot_be_recaptured_as_authority`; weaken lexical-parent no-follow policy (follow stat and remove the redundant link predicate) → `test_parent_link_inserted_during_directory_preparation_is_refused`; remove the initial-parent identity comparison → `test_initial_parent_identity_survives_directory_preparation`; remove commit-parent identity comparison → `test_commit_refuses_held_parent_and_ancestor_substitution`; remove held-parent descriptor comparison → `test_commit_rejects_a_held_descriptor_that_no_longer_matches_lexical_parent`; weaken final no-follow policy (follow stat and remove the redundant link predicate) → `test_commit_refuses_final_link_even_to_initial_owned_inode`; remove final expected-identity comparison → `test_initial_absence_refuses_a_late_unowned_regular_file`; restore early same-byte success for strict writes → `test_commit_preserves_initial_owned_identity_against_ordinary_replacement`; remove by-path commit recheck → `test_by_path_fallback_rechecks_final_identity_and_link_before_replace`. Names are in `ReportBoundaryTests` in `test_qualification_report.py`. Two preliminary single-facet no-follow mutations survived because `_is_windows_link` independently lstats symlinks; their whole-file replays were green, so the load-bearing mutants weaken both facets of the same no-link policy. Passing focus and expected known-bad failures are separate evidence.

Observe: `ProtocolOwnershipTests.test_worker_nonce_is_visible_to_executed_test_code` runs the real worker CLI and a test that reads its nonce from argv. Existing real-runner controls reconfirm ordinary-run opt-in behavior, exact comparison and canonical receipt separation. Named build/testing/cross-cutting guidance and the worker comment describe correlation and diagnostic authority. AC1–4 and the first three tasks are marked complete through typed tools. AC5 and the final task await quiet focused/docs verification, coordinator canonical qualification and independent delivery review; no implementation self-approval, close, commit, push or pack was performed.

Observe: Final quiet focused runner passed `python3 -B .wavefoundry/framework/scripts/run_tests.py --file test_qualification_report.py --file test_contained_files.py --file test_contained_repo_access.py`: 104 tests across three files in 15.071s, exit0; report33 + contained42 + contained-repo29. One existing contained platform skip; all 14 added methods ran without skips. Final-source rerun reconfirmed all eleven faithful mutants as assertion failures with no setup errors. Existing `WriteRuleTests.test_a_link_leaving_the_root_is_refused_and_one_inside_it_writes_its_target` and `test_unchanged_bytes_write_nothing_and_a_mode_is_kept_or_set` passed beside the strict controls. Full `wf_validate_docs` passed with zero errors/warnings before this final narration; coordinator owns canonical full-suite qualification, independent delivery review, AC5/final-task completion and pause. Source and named guidance are frozen.
| 2026-10-11 | Matching canonical qualification completed; final independent delivery approvals pending. | executed: isolated `run_tests.py --no-cache` exited 0, 12,296 tests/185 files/12 aggregate skips in 761.650s. Genuine receipt ran 2026-10-11T08:36:01.131637+00:00; inputs `205ceff182022c9a40efbc33c6f8f6ea4178a21e998c58b629dff7a0eff691c6`, SHA256 `bcf52f3c8e60f346c62373307e80034e447a2c88f21a743dbe6c1d34d8e03065`; current framework and isolated source match, receipt transferred byte-identically. Independent root scratch reader also catches naturally deeply nested capped JSON as ValueError. Existing focused 104 tests include 14 new methods without skips; exact full-suite skip identities were not exported. Seven frozen source/guidance objects still match. Final task remains pending actual independent QA/Council and final docs gate; original Session Handoff is the planning-time snapshot, current status is here and in wave.md. |
| 2026-10-11 | Delivered and independently approved; pause for operator-owned closure. | executed: all five required specialist lanes and FULL Council have current typed delivery approvals, no findings/deferrals/waivers, and successful continuation leaves only operator signoff. Canonical receipt matches the frozen framework; final guided docs validation passed with maximum severity none. All five ACs/four tasks reconciled. No closure, commit, push or package authority inferred. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-11 | Request only material specialist review lanes. | Wave record names scope-specific lanes; preserve policy-derived requirements and Council. | Reject blanket independent specialties/personas absent a material boundary or policy trigger because they add overhead without a demonstrated quality benefit. |
| 2026-10-11 | Required divergent pre-plan completed. | Select direct report-boundary repair: it preserves the format and separates the report's stricter policy from other contained writers. Reject validation-only repair because a post-check substitution remains possible. Reject a new authenticated report/receipt protocol because code in the worker shares process authority and that would expand lifecycle semantics. | Alternatives critiqued in selection rationale. |
| 2026-10-11 | Execute authorized follow-up within named scope. | Operator authorized preparation, review and implementation; coordinator serializes waves and pauses completed work. | No close, commit or push; unchanged authorized execution packet needs no new permission hold. |

## Risks

Native Windows lacks the same descriptor facilities as POSIX; refuse detected unsafe cases and document its by-path check-to-commit limit rather than claiming unexecuted equivalence. Held descriptors alone do not establish that the lexical parent still names that directory: parent-identity revalidation is required before commit, and a detected substitution must leave the original report and alternate targets unchanged. No protection against all adversarial same-user changes in the final check-to-commit interval is claimed. Helper changes must preserve all existing generic contained I/O consumers.

## Session Handoff

Planned; no code edited and no AC/task complete. Coordinator owns Prepare/Council and future activation. Read this file and wave.md for durable scope/evidence. Global handoff is coordinator-owned.

Review routing note: requested lanes are scope-specific; Prepare's actual policy-derived requirements and current Council gate remain authoritative. Product-owner and other unrequested specialties are not independently mandatory absent policy selection or a justified material finding.
