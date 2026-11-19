# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-17
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `23p89 retained-work-and-test-run-tolerance`
Title: Retained Work And Test Run Tolerance

## Objective

An operator can plan new work while a full test run is in progress without the run being refused, and can trust a wave's review status: a delivery approval shown as current covers every change the wave holds. The test guard still refuses changes that affect the work under test, harmless events never lapse an approval, and a closed wave's review status never changes.

## Changes


Change ID: `23nqu-enh test-run-tolerates-concurrent-planning`
Change Status: `implemented`

Change ID: `23q1g-bug delivery-approvals-survive-late-admission`
Change Status: `implemented`


## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-11-17

## Wave Summary

Wave `23p89` (Retained Work And Test Run Tolerance) delivered two changes: Test run tolerates concurrent planning and Delivery approvals survive a late admission.

**Changes delivered:**

- **Test run tolerates concurrent planning** (`23nqu-enh test-run-tolerates-concurrent-planning`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8 and AC-9 completed. Key decisions: Operator: "We need to allow this in the docs folder unless it directly impacts the current work."; Operator: "I think we can tolerate more than just md files." Every file type under the documentation root is tolerated.
- **Delivery approvals survive a late admission** (`23q1g-bug delivery-approvals-survive-late-admission`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10 and AC-11 completed. Key decisions: Operator: "yes, plan it as a bug... make sure that we don't increase approvals are invalidated incorrectly." And, on the second report: "I want to make srue this also doesn't happen."; Operator: "go with your recommendations, one spec two changes", in reply to the coordinator's recommendations: a closed-wave guard; refuse a delivery approval while the receipt is stale; a deferral behaviour now planned in `23q1h`. The packaging has since changed: the operator split the wave, `23q1h` is not in it, and this spec stands alone.

## Watchpoints

- Watchpoint: the operator split this wave on 2026-11-17 after a red-team readiness primer. It first held four changes; `23phc-bug retained-work-visibility-and-cleanup` and `23q1h-bug criterion-deferral-lapses-readiness-approvals` were removed and are back under the plans root with the primer's findings in their Progress Logs.
- Watchpoint: implement `23nqu` first, because it stops parallel planning from refusing the test runs of what follows; then `23q1g`. Both touch `run_tests.py`.
- Watchpoint: for `23q1g` the operator's constraint is that approvals must not be invalidated incorrectly. It makes no change to how specs are normalized and none to what the mark tools accept, so no existing digest moves.
- Watchpoint: `23q1g` changes the review machinery this wave is reviewed with. Recheck this wave's own review status after it lands and before delivery review.
- Follow-up: until `23nqu` ships, no session should write tracked or plan files during a full test run.
- Watchpoint: the operator's instruction for this wave, after the red-team primer's findings and the coordinator's recommendations were put to them: "Ok, split and then prepare, review, and implement them both while I'm awawy". The coordinator reads "them both" as the two changes that remain in this wave. Close and commit remain operator-owned.
- Watchpoint: both changes alter failure or readiness behaviour (the architecture-reviewer flagged it on a finding), so delivery review uses the full council.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| READY-DOCS-RECORD-INTEGRITY | do_now | no | completed | — |
| READY-NQU-DETECTION | do_now | no | completed | — |
| READY-NQU-DOC-COVERAGE | do_now | no | completed | — |
| READY-NQU-FAIL-OPEN-LAYOUT | do_now | no | completed | — |
| READY-NQU-RECONCILE | do_now | no | completed | — |
| READY-Q1G-AC3-ORACLE | do_now | no | completed | — |
| READY-Q1G-DOC-COVERAGE | do_now | no | completed | — |
| READY-Q1G-INTENT-STATUS-WINDOW | dont_do_later | no | not_required | — |
| READY-Q1G-MARK-REFUSAL | do_now | no | completed | — |
| READY-Q1G-NORMALIZER | do_now | no | completed | — |

*Machine review state — 10 findings; current: do_now 9, maybe_later 0, dont_do_later 1, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |

Readiness docs-contract-reviewer: current executed approval by coryhacking follows every affected repair (local account: coryhacking); known-bad control not applicable: Inspected scope is documentation contracts of two plans; the three first-round defects were each confirmed absent by reading the amended text, and the advisory gap shows the check can find a miss. No finding remains in this lane..
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

- 2026-11-17, Prepare wave, red-team primer (depth standard) on the wave as first planned, with four changes. It found the deferral plan `23q1h` self-contradictory and the retained-work plan `23phc` large and unreviewed, and three blocking problems in the two plans now in this wave. The operator split the wave. The red-team seat then typed its three blocking findings (`READY-NQU-DETECTION`, `READY-NQU-RECONCILE`, `READY-Q1G-NORMALIZER`) before any repair; repair starts were recorded and both plans amended.
- 2026-11-17, Prepare wave, first lane review on receipt `review-policy-50d29fe535a56b059a2b`: `code-reviewer`, `qa-reviewer`, `architecture-reviewer`, `docs-contract-reviewer` (also the rotating seat) and a fresh red-team context. The red-team seat reverified two of its findings and not `READY-NQU-RECONCILE`, and typed `READY-Q1G-MARK-REFUSAL`. `architecture-reviewer` typed `READY-NQU-FAIL-OPEN-LAYOUT`, `qa-reviewer` typed `READY-Q1G-AC3-ORACLE`, `docs-contract-reviewer` typed `READY-DOCS-RECORD-INTEGRITY`, `READY-NQU-DOC-COVERAGE` and `READY-Q1G-DOC-COVERAGE`. `code-reviewer` found no blocking issue of its own and could not record an approval because the receipt had gone stale. Every finding was typed by its lane before any repair. Executed by lanes on scratch fixtures: the in-worker guard's behaviour with today's protected roots and with the documentation root added; the carrier classification the reconcile path uses; the digest neutrality of each checkbox and status event. No test suite was run.
- 2026-11-17, one repair pass by the coordinator: repair starts recorded for the six newly typed findings (cycle 1, context `23p89-readiness-repair-2`; `READY-NQU-RECONCILE` continues under its earlier repair start), then both plans amended. The changes are listed in each plan's Progress Log. A record defect for the reader: two repair-start batches share cycle 1 because the first cycle was still open.
- 2026-11-17, Prepare wave, focused verification: fresh contexts of `red-team`, `architecture-reviewer`, `qa-reviewer` and `docs-contract-reviewer` reverified every finding they own, one lane per event; all nine findings are terminal and no new blocking finding was raised. `code-reviewer` (fresh context) found no blocking issue. None of the four lane approvals could be recorded in that round: reverifying `READY-NQU-FAIL-OPEN-LAYOUT` cleared the flag from which the receipt derives that delivery needs the full council, the receipt went stale, and the tool refused approvals. The coordinator re-prepared and asked each lane to record its approval. Delivery review will use the full council whatever the receipt derives. Lane notes are in each plan's Progress Log.
- 2026-11-17, Prepare wave, council-chair (independent, fresh context): `council-readiness` PASS, recorded as the typed approval `ev-approval-council-readiness`, intent fit `partially`. `23nqu`: establishes. `23q1g` and the wave Objective: partially, on a non-blocking finding the chair typed, `READY-Q1G-INTENT-STATUS-WINDOW` (the status rows read approved between a late admission and re-Prepare, while review and close are blocked). Seats run: red-team (fixed) in three contexts and docs-contract-reviewer (rotating) in two. The chair executed a census over 375 ledgers, the in-worker guard on a fixture, and the digest neutrality of the checkbox and status events. Open operator decisions are listed in each plan's Progress Log. No test suite was run at readiness.
- 2026-11-17, Implement wave, `23nqu`: implemented by a delegated implementer and checked against the tree by the coordinator. Full suite `python3 .wavefoundry/framework/scripts/run_tests.py --no-cache`: "Ran 12893 tests across 250 files in 585.843s", "OK". Eleven reverted behaviours were each caught by their tests in a scratch copy. From this point a documentation change during a test run no longer refuses the run, except in an open wave's folder and the policy files.
- 2026-11-17, Implement wave, `23q1g`: implemented by a delegated implementer and checked against the tree by the coordinator. Full suite `python3 .wavefoundry/framework/scripts/run_tests.py --no-cache`, run after the last framework edit: "Ran 12910 tests across 250 files in 580.178s", "OK". Coordinator rerun of the review evidence and lifecycle suites: "Ran 923 tests across 2 files in 174.585s", "OK". Measured before and after by the implementer: normalizer signature identical, 375 per-wave digests identical, 1,982 current delivery approvals across this repository's ledgers and none made not current. The coordinator reloaded the attached server before review so events are recorded under the new code.
- 2026-11-17, Review wave, delivery: fresh independent contexts of `code-reviewer`, `qa-reviewer`, `architecture-reviewer` and `docs-contract-reviewer` each recorded a delivery approval with no blocking finding (`ev-approval-code-reviewer-2`, `ev-approval-qa-reviewer-2`, `ev-approval-architecture-reviewer-2`, `ev-approval-docs-contract-reviewer-2`). A fresh `red-team` seat attacked both changes by execution in a scratch copy and found nothing blocking. The council-chair recorded `ev-approval-council-delivery`, intent fit `partially`: `23nqu` establishes; for `23q1g` the status rows still read approved between a late admission and re-Prepare (close is blocked as stale), and ledgers without change-set data are not detected. Follow-ups the chair listed as fix later, none recorded as findings: a policy file created mid-run under another letter case is tolerated; the documents do not say the test receipt never covers documentation inputs; the advisory sentence "The approvals stay current" can be inaccurate; a reconciled receipt omits the tolerated-changes field; a test for the approval-phase check; nothing ran on Windows. `operator-signoff` is not recorded: the operator was away. Decisions left to the operator are listed in each spec's Decision Log and Progress Log and are not made here.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 74 | 894,252 |
| implement | 25 | 847 |
| review | 80 | 5,214,690 |
| **Total** | **179** | **6,109,789** |

<!-- wave:context-efficiency-state {"generation":164,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":25,"content_source_credit":3002,"derived_artifact_credit":0,"direct_net":847,"estimated_tokens_saved":847,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":117,"response_debit":2038,"source_credit_count":1,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":74,"content_source_credit":1131855,"derived_artifact_credit":1580,"direct_net":894252,"estimated_tokens_saved":894252,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":47961,"response_debit":196709,"source_credit_count":69,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5487},"review":{"calls":80,"content_source_credit":5421190,"derived_artifact_credit":1152,"direct_net":5214690,"estimated_tokens_saved":5214690,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10423,"response_debit":201068,"source_credit_count":100,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3839}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":179,"content_source_credit":6556047,"derived_artifact_credit":2732,"direct_net":6109789,"estimated_tokens_saved":6109789,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":58501,"response_debit":399815,"source_credit_count":170,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9326},"wave_id":"23p89 retained-work-and-test-run-tolerance"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 3 | 0 | 3 | 2,075,722 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":3,"estimated_exploration_avoided":2075722,"surfaced_events":3} -->
<!-- wave:exploration-avoided end -->
