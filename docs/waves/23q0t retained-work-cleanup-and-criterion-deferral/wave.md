# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-17
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `23q0t retained-work-cleanup-and-criterion-deferral`
Title: Retained Work Cleanup And Criterion Deferral

## Objective

An operator can see disposable work left behind after a wave closes and reclaim one reviewed folder deliberately, and an implementer can defer a criterion without the wave's readiness approvals lapsing while the delivery verdicts that judged the full scope stop being current. Normal ownership checks, closed waves and durable evidence are not weakened. A small runner fix rides along.

## Changes

Change ID: `23phc-bug retained-work-visibility-and-cleanup`
Change Status: `implemented`

Change ID: `23q0s-enh explicit-work-cleanup`
Change Status: `implemented`

Change ID: `23q1h-bug criterion-deferral-lapses-readiness-approvals`
Change Status: `implemented`

Change ID: `23q0r-bug tolerated-change-filter-rebuilds-set`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-11-18

## Wave Summary

Wave `23q0t` (Retained Work Cleanup And Criterion Deferral) delivered 4 changes: Report retained work after close and find older leftovers, Explicit cleanup of one retained work folder, Criterion deferral lapses readiness approvals, and Tolerated-change filter rebuilds its set for every path.

Intent outcome: 2026-11-18: partial. Drafted by the coordinator, an interested party, after the lane approvals and the council verdict instead of first as the workflow asks; the independent intent check is assigned to `qa-reviewer`. `23phc`: achieved on macOS: retained, partially removed and leftover work folders are reported by close, `wf_audit` and the upgrade report, and records citing a work path get an advisory (evidence: `test_wave_work.py`, `test_wave_work_lifecycle.py`; red-team's fixture and preview-only runs). `23q0s`: achieved on macOS and, by reading, Linux: one folder is reclaimed through preview then apply with identity, device, owner and token re-checks; the open wave, links and other-device content are refused (evidence: `ExplicitCleanupTests`; security's attack run and real nested-mount probe). Native Windows previews only and refuses apply by design, so the reclaim half of the Objective is not met there. `23q1h`: achieved: a deferral, re-tick, reopen or repeated deferral leaves the review-policy digest and the readiness approvals unchanged; Review lists each deferral as `deferred_criterion_scope_change`; and a criterion deferred or noted after `council-delivery` or `operator-signoff` blocks Review and Close until that approval is recorded again (evidence: `CriterionDeferralCurrencyTests`; red-team's end-to-end attack after the repair). `23q0r`: achieved (evidence: `run_tests._stray_artifact_failure` builds the tolerated set once; `test_run_tests_repo_guard.py` and `test_run_tests_reconciliation.py` pass unedited, 93 tests; no timing measured). Independent check: `qa-reviewer` confirmed the verdict for each change and for the Objective and supplied the two corrected sentences for `23q1h` and `23q0r`, incorporated here; it read `23phc` without executing its tests. Material limitations: native Windows, WSL2 and a packaged upgrade were not executed; the gate gives an advisory only for a deferral on a duplicate AC id or a criterion without an id; a folder with no record in this checkout, including `.wavefoundry/work/23lxe/`, can be cleaned with a label (an open operator decision).

**Changes delivered:**

- **Report retained work after close and find older leftovers** (`23phc-bug retained-work-visibility-and-cleanup`) — AC-1, AC-2, AC-3, AC-4, AC-5 and AC-6 completed. Key decisions: Select shared inventory, prominent advisories and one explicit cleanup operation; Use audit and upgrade as discovery points; keep cleanup separate from closure.
- **Explicit cleanup of one retained work folder** (`23q0s-enh explicit-work-cleanup`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6 and AC-7 completed. Key decisions: A separate verification closure for explicit cleanup, binding an owner fingerprint instead of calling `_read_owner`. Planner's choice, not separately confirmed by the operator; Bind `st_dev` and `st_ino` in the token and accept that a device change fails safe. Planner's choice.
- **Criterion deferral lapses readiness approvals** (`23q1h-bug criterion-deferral-lapses-readiness-approvals`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10 and AC-11 completed. Key decisions: Operator: "go with your recommendations, one spec two changes", accepting the coordinator's recommendation for deferral: readiness approvals never lapse on a deferral; `council-delivery` and `operator-signoff` lapse only if recorded before it; specialist delivery lanes stay current; The receipt records deferred criteria. Coordinator's design, not separately confirmed by the operator. Superseded by the replan rows below.
- **Tolerated-change filter rebuilds its set for every path** (`23q0r-bug tolerated-change-filter-rebuilds-set`) — AC-1 and AC-2 completed. Key decisions: Operator: "Building the set once before the comprehension fixes it without changing which paths pass."; No new test. Planner's choice, not separately confirmed by the operator.

## Watchpoints

- Operator, 2026-11-17, on the two plans left after wave `23p89` was split: "can you put these together?", then "once that is done, review and implement the wave." The coordinator reads this as one wave holding both, prepared, implemented and delivery-reviewed; close and commit stay with the operator.
- `23phc` was written by another session and revised here; the cleanup operation was split out of it as `23q0s`. Implement `23phc` before `23q0s`. `23q1h` touches the review machinery and is implemented on its own, after the other two, so the two workstreams do not share files during a test run.
- Watchpoint: `23q0s` adds a destructive tool: `security-reviewer` is requested for readiness and delivery.
- Follow-up: open operator decisions are listed in each spec's Decision Log. The coordinator proceeds on the planner's recommendation for each and records them as not confirmed by the operator.
- No spec body edits after readiness except the Progress Log. The framework test suite runs last; no edits in this wave's folder during a run.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DELIV-Q0S-NESTED-MOUNT-UNPINNED | do_now | no | completed | — |
| DELIV-Q1H-CLOSED-STALE | do_now | no | completed | — |
| DELIV-Q1H-CONTINUATION-NOTE-UNPINNED | do_now | no | completed | — |
| DELIV-Q1H-REDEFER | do_now | no | completed | — |
| DELIV-Q1H-UNATTACHED-CONTROL-VACUOUS | do_now | no | completed | — |
| READY-PHC-CITENOISE | do_now | no | completed | — |
| READY-PHC-CLASSIFIER-SEAM | do_now | no | completed | — |
| READY-PHC-OWNER-STATE | do_now | no | completed | — |
| READY-PHC-Q0S-CHANGELOG | do_now | no | completed | — |
| READY-PHC-WORKROOT-LINK | do_now | no | completed | — |
| READY-Q0S-CITE | do_now | no | completed | — |
| READY-Q0S-DESTRUCTIVE-ANNOTATION | do_now | no | completed | — |
| READY-Q0S-MIDDELETE-ORACLE | do_now | no | completed | — |
| READY-Q0S-MOUNT-TOP | do_now | no | completed | — |
| READY-Q0S-OWNER-FINGERPRINT | do_now | no | completed | — |
| READY-Q0S-PREVIEW-UNSAFE-HOST | do_now | no | completed | — |
| READY-Q0S-RECORDLESS-FOLDER | do_now | no | completed | — |
| READY-Q0S-REGISTRY | do_now | no | completed | — |
| READY-Q1H-DOC-TESTARCH | do_now | no | completed | — |
| READY-Q1H-FORGED-LINE-ORACLE | do_now | no | completed | — |
| READY-Q1H-STATUSNOTE | do_now | no | completed | — |

*Machine review state — 21 findings; current: do_now 21, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

- Readiness, 2026-11-17 to 2026-11-18: the first lane review approved `release-reviewer` and withheld `code-reviewer`, `qa-reviewer`, `architecture-reviewer`, `docs-contract-reviewer` and `security-reviewer`; `red-team` raised findings. Sixteen blocking findings: `READY-Q1H-DOC-TESTARCH`, `READY-PHC-Q0S-CHANGELOG`, `READY-Q0S-MIDDELETE-ORACLE`, `READY-Q1H-FORGED-LINE-ORACLE`, `READY-Q0S-CITE`, `READY-PHC-CITENOISE`, `READY-Q1H-STATUSNOTE`, `READY-Q0S-MOUNT-TOP`, `READY-Q0S-OWNER-FINGERPRINT`, `READY-Q0S-DESTRUCTIVE-ANNOTATION`, `READY-Q0S-RECORDLESS-FOLDER`, `READY-PHC-WORKROOT-LINK`, `READY-PHC-CLASSIFIER-SEAM`, `READY-Q0S-REGISTRY`, `READY-Q0S-PREVIEW-UNSAFE-HOST`, `READY-PHC-OWNER-STATE`. One repair pass, context `23q0t-readiness-repair-1`: a repair start for each finding, then plan edits to `23phc`, `23q0s` and `23q1h` recorded in each spec's Progress Log; each source lane reverifies its own findings.
- Focused verification round, 2026-11-18: fifteen of sixteen findings were reverified by the lanes that raised them; `red-team` did not reverify `READY-Q1H-STATUSNOTE`, because a status note added or reworded after `council-delivery` or `operator-signoff` lapsed nothing and surfaced only as an advisory. Asked how to proceed, the operator chose "Second repair (Recommended)": one more narrow repair on `23q1h` only, then one verification by `red-team`, the council, and implementation of all four changes. Second repair: `23q1h` Requirements 4 and 5 record a note hash per deferred or noted criterion on the two delivery approvals and block Review and Close when a note is added or reworded afterwards (AC-2, AC-3; Progress Log and Decision Log of `23q1h`). The ledger refused a cycle 2 repair start because cycle 1 is not complete, so the repair continues under the cycle 1 repair start of context `23q0t-readiness-repair-1`. Verification-round notes for the implementer are in the Progress Logs of `23phc`, `23q0s` and `23q1h`.
- 2026-11-18, Prepare wave, a fresh red-team context reverified `READY-Q1H-STATUSNOTE` after the second repair (`ev-ready-q1h-statusnote-3`). All sixteen readiness findings are terminal. Lane approvals and `council-readiness` follow a re-Prepare, because the plan edits changed the receipt.
- 2026-11-18, Implement wave: all four changes implemented by delegated implementers in the order `23q0r`, `23phc`, `23q0s`, `23q1h`, each report checked against the tree by the coordinator. Final framework run after the last framework edit: 12,976 tests across 250 files, OK. Not verified: native Windows, WSL2, a packaged upgrade. Delivery review follows.
- 2026-11-18, Review wave: `docs-contract-reviewer` approved; `release-reviewer`, `architecture-reviewer`, `code-reviewer`, `security-reviewer`, `qa-reviewer` and the `red-team` seat withheld on five typed findings (`DELIV-Q1H-CLOSED-STALE`, `DELIV-Q1H-REDEFER`, `DELIV-Q0S-NESTED-MOUNT-UNPINNED`, `DELIV-Q1H-CONTINUATION-NOTE-UNPINNED`, `DELIV-Q1H-UNATTACHED-CONTROL-VACUOUS`). One repair pass (cycle 2); framework run after it: 12,979 tests across 250 files, OK. All five findings were reverified by fresh contexts of the lanes that raised them. Follow-up: the non-blocking notes are listed in the `23q1h` and `23q0s` Progress Logs.
- Intent outcome: 2026-11-18: partial. Drafted by the coordinator, an interested party, after the lane approvals and the council verdict instead of first as the workflow asks; the independent intent check is assigned to `qa-reviewer`. `23phc`: achieved on macOS: retained, partially removed and leftover work folders are reported by close, `wf_audit` and the upgrade report, and records citing a work path get an advisory (evidence: `test_wave_work.py`, `test_wave_work_lifecycle.py`; red-team's fixture and preview-only runs). `23q0s`: achieved on macOS and, by reading, Linux: one folder is reclaimed through preview then apply with identity, device, owner and token re-checks; the open wave, links and other-device content are refused (evidence: `ExplicitCleanupTests`; security's attack run and real nested-mount probe). Native Windows previews only and refuses apply by design, so the reclaim half of the Objective is not met there. `23q1h`: achieved: a deferral, re-tick, reopen or repeated deferral leaves the review-policy digest and the readiness approvals unchanged; Review lists each deferral as `deferred_criterion_scope_change`; and a criterion deferred or noted after `council-delivery` or `operator-signoff` blocks Review and Close until that approval is recorded again (evidence: `CriterionDeferralCurrencyTests`; red-team's end-to-end attack after the repair). `23q0r`: achieved (evidence: `run_tests._stray_artifact_failure` builds the tolerated set once; `test_run_tests_repo_guard.py` and `test_run_tests_reconciliation.py` pass unedited, 93 tests; no timing measured). Independent check: `qa-reviewer` confirmed the verdict for each change and for the Objective and supplied the two corrected sentences for `23q1h` and `23q0r`, incorporated here; it read `23phc` without executing its tests. Material limitations: native Windows, WSL2 and a packaged upgrade were not executed; the gate gives an advisory only for a deferral on a duplicate AC id or a criterion without an id; a folder with no record in this checkout, including `.wavefoundry/work/23lxe/`, can be cleaned with a label (an open operator decision).
- 2026-11-18, Review wave, delivery approvals and council: after the repair the six required lanes recorded delivery approvals (`ev-approval-code-reviewer-2`, `ev-approval-qa-reviewer-2`, `ev-approval-architecture-reviewer-2`, `ev-approval-docs-contract-reviewer-3`, `ev-approval-release-reviewer-3`, `ev-approval-security-reviewer-2`). An independent `council-chair` context recorded `council-delivery` as `ev-approval-council-delivery`, PASS, intent fit `partially`: the Objective is met on macOS and Linux; native Windows cannot reclaim through the tool and no Windows, WSL2 or packaged-upgrade run exists. Council roster: the chair, `red-team` (fixed seat) and `docs-contract-reviewer` (rotating seat). Disagreement left for the operator: `red-team` judges the cleanability of folders with no record in this checkout borderline unsafe for `.wavefoundry/work/23lxe/`; `security-reviewer` and `release-reviewer` judge it not unsafe. Operator sign-off is not recorded.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 135 | 4,708,356 |
| implement | 49 | 2,243,015 |
| review | 113 | 5,559,187 |
| **Total** | **297** | **12,510,558** |

<!-- wave:context-efficiency-state {"generation":278,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":49,"content_source_credit":2265195,"derived_artifact_credit":0,"direct_net":2243015,"estimated_tokens_saved":2243015,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":670,"response_debit":21510,"source_credit_count":40,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":135,"content_source_credit":5305436,"derived_artifact_credit":5736,"direct_net":4708356,"estimated_tokens_saved":4708356,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":71618,"response_debit":536685,"source_credit_count":186,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5487},"review":{"calls":113,"content_source_credit":6018111,"derived_artifact_credit":2452,"direct_net":5559187,"estimated_tokens_saved":5559187,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":27750,"response_debit":438380,"source_credit_count":99,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4754}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":297,"content_source_credit":13588742,"derived_artifact_credit":8188,"direct_net":12510558,"estimated_tokens_saved":12510558,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":100038,"response_debit":996575,"source_credit_count":325,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10241},"wave_id":"23q0t retained-work-cleanup-and-criterion-deferral"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
