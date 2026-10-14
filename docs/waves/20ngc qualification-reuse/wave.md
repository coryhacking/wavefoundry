# Wave Record

Owner: Engineering
Status: paused
Last verified: 2026-10-14
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20ngc qualification-reuse`
Title: Qualification Efficiency

## Objective

Eliminate duplicate qualification work: retain exact default-run detail for packaging reuse, then qualify narrower customization-profile coverage with conservative full-profile fallback.

## Changes

Change ID: `20lr2-enh reuse-default-qualification-detail`
Change Status: `implemented`

Change ID: `20nnh-enh focused-profile-qualification`
Change Status: `active`
Depends On: `20lr2-enh reuse-default-qualification-detail`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer after readiness
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, release-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer

## Wave Summary

*(Populated at closure.)*

## Watchpoints

- Watchpoint: No new suite or review solely for recording bookkeeping; validate work reduction by worker invocations, not host-dependent wall-clock targets.
- Keep source feedback, attribution and identifying reproductions outside tracked artifacts.
- Planning records no implementation, qualification or approval claim.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| QA-FINAL-MARKER-PUBLICATION | do_now | no | completed | code-reviewer, qa-reviewer, release-reviewer |
| QUAL-DEL-1 | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | withheld | repaired findings require fresh approval: QUAL-DEL-1, QA-FINAL-MARKER-PUBLICATION | record a fresh independent approval for qa-reviewer |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| release-reviewer | withheld | repaired findings require fresh approval: QUAL-DEL-1, QA-FINAL-MARKER-PUBLICATION | record a fresh independent approval for release-reviewer |
| operator-signoff | withheld | repaired findings require fresh approval: QUAL-DEL-1, QA-FINAL-MARKER-PUBLICATION | record a fresh independent approval for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: pending; closure not requested.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.
- Implement default-detail reuse before profile selection; both changes share runner/report ownership, readiness, delivery review and final qualification.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 132 | 877,184 |
| implement | 305 | 2,114,696 |
| review | 347 | 1,985,887 |
| **Total** | **784** | **4,977,767** |

<!-- wave:context-efficiency-state {"generation":730,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":305,"content_source_credit":2708649,"derived_artifact_credit":0,"direct_net":2114696,"estimated_tokens_saved":2114696,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10453,"response_debit":586572,"source_credit_count":108,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3072},"plan":{"calls":132,"content_source_credit":1184809,"derived_artifact_credit":3625,"direct_net":877184,"estimated_tokens_saved":877184,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":29290,"response_debit":291161,"source_credit_count":58,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9201},"review":{"calls":347,"content_source_credit":2990427,"derived_artifact_credit":46,"direct_net":1985887,"estimated_tokens_saved":1985887,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":42086,"response_debit":962500,"source_credit_count":123,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":784,"content_source_credit":6883885,"derived_artifact_credit":3671,"direct_net":4977767,"estimated_tokens_saved":4977767,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":81829,"response_debit":1840233,"source_credit_count":289,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12273},"wave_id":"20ngc qualification-reuse"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 63 | 0 | 36 | 22,090,758 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":36,"estimated_exploration_avoided":22090758,"surfaced_events":63} -->
<!-- wave:exploration-avoided end -->
## Current assumptions

Existing defaults and authority remain unchanged until this wave is prepared and implemented. No commit, push or close is authorized by this planning step.

## Outputs produced or expected

- Admitted change documents with requirements, AC priorities and alternatives.
- Implementation and regression coverage in declared files after readiness.
- Final results in wave.md and typed review events; no permanent evidence folder.

## Review checkpoints

- 2026-10-14: Source-grounded planning complete. Requested lanes express anticipated scope; Prepare will calculate required lanes and obtain independent readiness review. No approvals recorded.
- 2026-10-14: Operator requested fewer waves. Moved the unchanged profile-qualification change from unreviewed draft `20nni` into this wave and removed its empty untracked scaffold. One readiness/delivery cycle covers both changes; each retains its own ACs. Rejected retaining separate waves because it repeats shared runner/report reviews; rejected merging the unrelated repair batch here because that couples release-test policy to runtime repairs.

## Completion criteria

Every admitted AC and task has evidence or an explicit scoped disposition; required delivery reviews and canonical qualification pass before operator-owned closure.

## Handoff or next-wave notes

First implementation priority: reuse default execution detail before profile selection.

## Progress Log

- 2026-10-14: Operator chose to keep timing deferred and commit/push the reviewed implementation with this wave paused. Final qualification, closure and a new local pack remain pending; no waiver, passing receipt or final delivery approval is claimed.

- 2026-10-14: Final repaired-tree qualification executed 11,661 tests across 187 files with 12 skips in 825.892 s. Both child-marker and reload integration repairs passed; the only failure was the deferred lifecycle projection timing check (32.396 ms p95 versus 25.724 ms effective limit). No green receipt, profile matrix or final QA approval resulted, and the sequence stopped without an unchanged retry. Closure/build remain pending an operator decision on timing; source reviews and terminal repairs remain valid. Retrospective and cleanup: no new memory selected because canonical regression tests and this wave/ledger preserve the future-action lessons. Dry-run proposals were reviewed; no candidate files or routine evidence folders were created.

- 2026-10-14: QA-FINAL-MARKER-PUBLICATION cycle 2 is terminal after fresh independent verification; convergence checkpoint recorded. Reviewer independently executed ordinary/delayed-write positives and the reverting-publication mutant: two passes and the exact expected empty-read failure, zero errors/skips. Only the three-line fixture publication hunk differs from its original source; all assertions/deadlines remain intact. Code delivery approval is current; full QA/release remains pending qualification. AC-5 and the marker task are complete. Canonical evidence: .wavefoundry/framework/scripts/tests/test_child_tee.py::ChildTeeTests.test_explicit_timeout_includes_withheld_descendant_pipes_and_closes_readers. Timing stays deferred, all waves paused, no new permanent evidence artifact or separate memory record needed.

- 2026-10-14: Operator approved the bounded preexisting child completion-marker repair. The owning 20nnh requirements/scope/AC-5/task/review targets were amended and focused readiness approved against review-policy-9c79abf93ab9bc5ac0ce. One disclosed independent context reviewed the amendment across required remits; original standard council and unaffected qualification judgments remain attributed by reference. No repeated full council, profile-policy change or timing waiver.
- 2026-10-14: ChildTeeTests.test_explicit_timeout_includes_withheld_descendant_pipes_and_closes_readers now closes a sibling temporary marker before atomic replacement. Its normal case and a 250 ms pending-write gap pass; reverting only publication in the child command reproduces exactly one empty-read assertion failure. No errors/skips; existing deadlines, held-pipe/parent, reader/thread and final-payload assertions remain unchanged. Durable owner: .wavefoundry/framework/scripts/tests/test_child_tee.py. No production child-output edit or extra permanent evidence file; temporary probe scripts remain outside the repository. Timing and full qualification remain pending.

- 2026-10-14: Operator explicitly retained timing deferral. Final qualification and dependent delivery approvals remain pending; no waiver, suite retry, close, commit, push or build. All three waves are paused with gates closed. The final reload integration repair is terminal after fresh independent verification; preexisting child completion-marker fixture repair awaits a separate scope decision.


- 2026-10-14: Combined reviewed-source default ran 11,661 tests in 187 files with 12 skips (882.161 s): three assertions failed in two files. One reload source-sequence integration assertion was repaired in 20nnk; a preexisting child completion-marker race was independently reproduced and awaits an explicit scope decision. The operator again deferred the timing gate (42.371 ms versus 35.373 ms); no threshold change, waiver or unchanged full-suite retry. No green receipt, retained default export or reference-profile execution resulted. QA/release approvals and the full reference matrix remain pending; 20nnh ACs remain unchecked. Existing 186/187 coverage and zero-worker export fixture evidence do not substitute for that matrix.

- 2026-10-14: Default detail reuse implemented; focused report/cache modules passed 38 and 97 tests. A real controlled packaging repeat invoked zero workers and preserved execution identity. Actual whole-suite savings will be measured by worker invocations after final qualification; no wall-clock improvement is claimed from the fixture. Report storage stays at one ignored bounded last-default.json, separate from receipt authority. Compatibility selection is now active; combined canonical qualification and independent delivery review remain pending.

- 2026-10-14: Implementation and focused independent repair review complete; QUAL-DEL-1 terminal. Repaired-tree canonical default ran 11,622 tests / 187 files / 12 skips, with only the existing lifecycle projection timing assertion failing (42.784 ms versus 33.242 ms). No fresh green receipt or full reference profile matrix. Paused with QA/release qualification pending; timing investigation remains deferred, no assertion weakened and no successful qualification claimed. Continue the other admitted waves; revisit final qualification after meaningful source work.

- 2026-10-14: Resumed for final combined qualification after both later implementations paused. Refreshed only coverage.json test_worker_guard pin to reviewed ff40736fc2c972b31a35e19d5e7227f7486261b5994a8a96405ce32f7c32b6fd. Independent code/architecture reviewer reconfirmed unchanged 16-contract inventory and omitted version-worker footprint; bootstrap hygiene adds no profile-sensitive dependency. This is reviewed coverage maintenance, not automatic trust or completed matrix evidence.
