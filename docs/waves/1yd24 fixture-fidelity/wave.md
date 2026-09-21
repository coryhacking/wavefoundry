# Wave Record

Owner: Engineering
Status: closed
Completed at: 2026-09-21
Last verified: 2026-09-20
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1yd24 fixture-fidelity`
Title: Fixture Fidelity

## Objective

When this wave closes, building a valid declared wave in a test is a single call to a shared helper that drives the real producers, and the rule behind it reaches every project through the harness seeds. Now, because a hand-authored fixture in wave `1y0h0` produced a golden that named three waves and exercised none of the spans it claimed, and the census finds 51 declaration occurrences across 10 files, including setup and intentionally retained parser/assertion inputs.

## Changes

Change ID: `1yd25-debt canonical-declared-wave-fixtures`
Change Status: `complete`

Change ID: `1yd96-doc fixture-fidelity-harness-rule`
Change Status: `complete`

## Participants

- Coordinator: framework maintainer
- Write-owning roles: implementer, qa
- Requested review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-09-21

## Wave Summary

Delivered both changes: canonical declared-wave test fixtures and fixture-fidelity harness guidance. All nine ACs and all tasks completed; nothing deferred. Real producers build prerequisites before the optional synthetic status rewrite. Per-token census and mutation-proven tests preserve path fidelity without treating producers as correctness oracles.

Code, QA and docs reviews approved; all findings resolved. Full suite: 9444 tests across 117 files, 12 existing skips, green. Retrospective and memory validation are recorded in Closure reconciliation.

## Closure reconciliation

Delivered canonical declared-wave fixtures, five migrated setup seams, a per-token declaration census, and fixture-fidelity guidance in seeds 209/239 with self-hosted QA synchronization. Synthetic status is applied only after every producer; legacy ready is rejected. Expected-value oracles remain independent of fixture producers.

Both admitted changes are complete; every AC/task is checked, with no intentionally deferred ACs or tasks. Code, QA and docs-contract reviews passed; all three findings are repaired and reverified. Current policy requires readiness council only, which is recorded. Docs-contract review was performed; no project specification changes were needed. No tree-moved-under-review finding remains. All edit gates are closed.

Verification: 9444 tests across 117 files, 12 existing skips, green; the current receipt is verified by the close tool. Docs validation passes with one nonblocking existing AC-wording advisory. Operator reviewed the repair evidence and authorized closure and commit on 2026-09-21.

Retrospective: the non-obvious lesson is to observe prerequisite state at producer entry, because a correct final state can hide an invalid route. This is embodied in the producer-order regression and the shipped seed-209 fixture-fidelity rule. Close-time memory candidate 1yk79 was independently validated and rejected: it duplicated shipped guidance, carried administrative prose, and had an inaccurate generated target. Its rejection is preserved in memory history; no new active memory was warranted. No additional canonical guidance is needed beyond this wave's seed and QA changes.

Closed on 2026-09-21 with both change statuses complete and idle handoff updated. The preexisting subprocess-helper docstring discrepancy remains outside this wave and is listed below; no new in-scope work is deferred.

## Watchpoints

- The two changes are independent and may land in either order; neither blocks the other, because `1yd96-doc` edits seeds while the helper is framework-internal and never ships to a target repository.
- Watchpoint: negative fixtures stay hand-authored. Records deliberately malformed to exercise a validator, which is most of `test_review_evidence.py` and `test_docs_lint.py`, are correct precisely because they are hand-written; forcing them through the builder would destroy the subject of the test.
- Watchpoint: `1yd96-doc` edits seeds, so `seed_edit_allowed` opens immediately before and closes immediately after. Seed edits reach every target repository.
- Watchpoint: the helper reaches real lint and gardener subprocesses through `mode="ready"`; stubs are parameters rather than defaults, so a caller that does not need the receipt does not pay for one.
- Follow-up, deliberately out of scope here: `subprocess_util.isolated_run`'s docstring claims `capture_output=True` triggers UTF-8 decoding while the code keys on `text=True`. Two `1y0h0` review lanes found it independently and `1y0bd` works around it; it belongs to the subprocess helper rather than to fixture fidelity.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| fixture-helper-guard-pins | do_now | no | completed | code-reviewer, qa-reviewer |
| fixture-propagation-contract | do_now | no | completed | docs-contract-reviewer, qa-reviewer |
| fixture-status-producer-order | do_now | no | completed | code-reviewer, qa-reviewer |

*Machine review state — 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 47 | 854,715 |
| implement | 48 | 94,639 |
| review | 173 | 3,315,253 |
| **Total** | **268** | **4,264,607** |

<!-- wave:context-efficiency-state {"generation":204,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":48,"content_source_credit":111082,"derived_artifact_credit":0,"direct_net":94639,"estimated_tokens_saved":94639,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1861,"response_debit":17427,"source_credit_count":4,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2845},"plan":{"calls":47,"content_source_credit":918914,"derived_artifact_credit":3318,"direct_net":854715,"estimated_tokens_saved":854715,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7345,"response_debit":64218,"source_credit_count":39,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4046},"review":{"calls":173,"content_source_credit":3639101,"derived_artifact_credit":979,"direct_net":3315253,"estimated_tokens_saved":3315253,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":21576,"response_debit":305253,"source_credit_count":113,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2002}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":268,"content_source_credit":4669097,"derived_artifact_credit":4297,"direct_net":4264607,"estimated_tokens_saved":4264607,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":30782,"response_debit":386898,"source_credit_count":156,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8893},"wave_id":"1yd24 fixture-fidelity"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 3 | 0 | 3 | 1,400,237 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":3,"estimated_exploration_avoided":1400237,"surfaced_events":3} -->
<!-- wave:exploration-avoided end -->
## Review Checkpoints

- 2026-09-20: Preflight fact gathering reconciled obsolete sixth-condition wording and binary census assumptions before the first full readiness pass. Generic implementer owns shared test helper/migration; coordinator owns the disjoint seed guidance/presence pins and rendering. Independent code/docs and QA reviewers assess the current packet. Standard depth: producer-sequence feasibility, per-site census bypass, seed/oracle contract. Use current capable contexts for cross-cutting lifecycle judgment; small coupled edits stay local.
- Gapfill: semantic retrieval reported index runtime stale during preflight; exact MCP keyword/read and targeted shell reads were used. MCP reload now reports loaded implementation matches disk.

- 2026-09-20: Full readiness review found one shared docs-contract/QA blocker: same-text regeneration is not the existing transport. One bounded repair defines canonical seed-209 pointers, fresh QA role generation from seed 239, preservation of target-owned prose, and explicit self-hosted QA synchronization. No renderer source or lifecycle behavior is added. Implementation note: the literal census must handle Python 3.13 f-string segments and scoped post-write/index stubs.
- **Prepare-phase Wave Council [prepare-council] — 2026-09-20: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: swallowed producer refusals and false propagation assumptions can preserve wrong-path evidence; strongest-alternative: strict producer orchestration with independent final-Prepare oracle and existing pointer/fresh-role transport). Evidence: readiness-qa.md and readiness-code-docs.md. Code/docs/council share one independent reviewer context; QA/red-team share another. One bounded repair and focused round resolved the propagation finding; all required lane approvals bind the repaired receipt.

- 2026-09-20: Delivery review identified one grouped verification defect: six strict helper guards lacked discriminating durable controls. Repair changes only test_declared_wave_fixtures.py, adding invalid-input cases and real-receipt malformed-Prepare cases. All six guard deletions now fail their named tests; helper behavior and admitted contracts unchanged. One repaired source snapshot published for focused reverification.

- 2026-09-20: Focused delivery reverification cleared fixture-helper-guard-pins in code and QA lanes. Code/docs share one genuinely fresh delivery reviewer context; QA uses a separate fresh delivery context. Neither authored the repair. Existing readiness contexts were deliberately excluded from final delivery approvals because they retained recheck history. All six former survivors are killed; all gates closed. Memory proposal after reconciled finding heads yielded zero candidates.

- 2026-09-20: Implementation and required delivery review complete. Code-reviewer, qa-reviewer and docs-contract-reviewer approvals recorded against the repaired tree. Final suite9444/117files/12existing skips is green; QA independently recomputed current receipt hash4decf445ea1e79f2584c875baea38b21ba8179d1aa445eb7abaa67b5107c6132. All ACs/tasks complete, all gates closed, no unresolved findings. Wave remains implementing pending explicit operator closure; no commit made.

- 2026-09-21: Operator status-order finding repaired and independently reverified in code/QA lanes; both approvals refreshed. Synthetic status is last, legacy ready rejected, both mutations detected. Final suite 9444 tests/117 files/12 existing skips green in 294.428s; current receipt `1b37f7821ab1163954e6ac71e32ca64496ef88208578afbcd0c4118ca65845c5` verified. All tasks/ACs complete. Wave remains open and uncommitted.
