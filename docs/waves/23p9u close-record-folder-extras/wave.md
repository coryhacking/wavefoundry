# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-18
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `23p9u close-record-folder-extras`
Title: Close Record Folder Extras

## Objective

The agent closing a record and the operator approving the close see which files in the record folder are not the record, an admitted spec or the ledger, with sizes and whether anything cites them, and the Close prompt says what is worth keeping and asks for one disposition per extra. The tool only reports: it deletes nothing, blocks nothing and looks only at the record being closed. A second change, admitted later on the operator's direction, stops the docs gardener from re-dating documents that have not changed since their last stamp.

## Changes

Change ID: `23p9t-enh close-record-folder-extras-review`
Change Status: `implemented`

Change ID: `23qfz-bug gardener-restamps-unchanged-docs`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-11-18

## Wave Summary

Wave `23p9u` (Close Record Folder Extras) delivered two changes: Review extra files in a record folder at Close and Docs gardener re-stamps documents that have not changed since their last stamp.

Intent outcome: 2026-11-18: partial. Independent check by `qa-reviewer` at the second delivery review, incorporated as given, with its one open exception removed after that finding was repaired and reverified. Reporting is achieved on macOS: Close, in dry run and write, blocked or not, and on the `change_doc_unreadable` and `review_projection_failed` returns, lists the files in the closing record's folder that are not the record, an admitted spec or the ledger. Each listed file carries its size, citation state and loose-mention flags, capped at 50 listed with totals and a not-listed count; the unreadable-record return names the record and lists no files (evidence: `test_wave_work_lifecycle.py`, where mutations of each return attachment and each message count fail). Guidance is achieved: seed 190, its repository copy and the lifecycle template tell the agent to give every extra a disposition and to list and review the folder by hand, including files beyond the 50 the report lists. Before removing a `not_cited` file with all four flags false, the agent searches the ledger for its name stem and the other extras for its name (evidence: `test_compact_review_artifacts.py`, which fails when any of these sentences is removed or the old keep-unlisted sentence is restored). The per-extra review is guidance only: by the operator's decision nothing records or checks it, and the tool and its cap are unchanged. The gardener change is achieved: in default mode `docs_gardener` stamps a Git-changed document only when it differs from `HEAD` outside the date line and changed since its stamp; explicit modes are unchanged (evidence: `DefaultModeStampRuleTests`, which the pre-change gardener fails and where every guard mutation fails a test, including the passing of the run's date). Stated limits: a hand edit of a changed document's date line, a Git rewrite, a run across midnight or across time zones can each cause one extra stamp. Not established: that agents leave tidier folders and that multi-day diffs lose date-only churn, which later closes will show. Not executed: native Windows junction handling and the `core.autocrlf` behaviour there, WSL2, Python 3.11, a packaged upgrade.

**Changes delivered:**

- **Review extra files in a record folder at Close** (`23p9t-enh close-record-folder-extras-review`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7 and AC-8 completed. Key decisions: Scope is Close only, for the record being closed. Operator's decision, quoted: "yes, plan it as a spec, Close only"; Selected approach: an advisory close diagnostic listing extras with citation state, plus a disposition step and keep guidance in the Close prompt. Planner's choice, not separately confirmed by the operator beyond the request itself.
- **Docs gardener re-stamps documents that have not changed since their last stamp** (`23qfz-bug gardener-restamps-unchanged-docs`) — AC-1, AC-2, AC-3, AC-4, AC-5 and AC-6 completed. Key decisions: Stamp only when the document changed since its stamp. Operator's direction, quoted: "they shouldn't be tagged unless they change to reduce git churn, etc."; Detect "changed since its stamp" by comparing the file's modification date with the stamp date. Planner's choice, not separately confirmed by the operator.

## Watchpoints

- Operator scope, quoted: "yes, plan it as a spec, Close only". Cap decision: "That's good, show the total count if it's more than 50." Legacy typed review files reported, not recognized: "agree".
- Operator instruction for this wave, quoted: "close 23q0t; then plan, prepare, review, and implement this in a new wave." Close of this wave and any commit are not authorized by it.
- The tool must never delete, move or block; a ledger-cited file is always kept. Windows is enterprise-critical: the report is read-only and compares forward-slash paths exactly on every platform.
- Seeds 190 and 209 change shipped wording ("reference resolver"); `seed_edit_allowed` and `framework_edit_allowed` are opened for the edits and closed before the final suite.
- Operator direction after the first delivery report, quoted: files beyond the cap are reviewed by the agent by hand ("The guidance should be that agents should manually review the files even the ones beyond the 50"); the extra Close prompt sentence is wanted ("yes I want it"); and on the gardener re-stamping documents: "they shouldn't be tagged unless they change to reduce git churn, etc.", planned as `23qfz` and admitted here after the first delivery review.
- The working tree is uncommitted and holds closed waves `23lxd`, `23p89`, `23q0t` and another session's work.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DELIV-P9T-JSON-ESCAPE-BOUNDARY | do_now | no | completed | — |
| DELIV-P9T-NAME-AFTER-SLASH | do_now | no | completed | — |
| DELIV-P9T-QA-MESSAGE-COUNTS | do_now | no | completed | — |
| DELIV-P9T-QA-NOTE4-PIN | do_now | no | completed | — |
| DELIV-P9T-QA-UNTESTED-RETURNS | do_now | no | completed | — |
| DELIV-P9T-RETURN-ORACLES | do_now | no | completed | — |
| DELIV-QFZ-RUN-DATE-UNPINNED | do_now | no | completed | — |
| READY-P9T-BLOCKED-DRYRUN | do_now | no | completed | — |
| READY-P9T-CITE-LEFT-BOUNDARY | do_now | no | completed | — |
| READY-P9T-DOCS-SURFACES | do_now | no | completed | — |
| READY-P9T-NAME-CITE | do_now | no | completed | — |
| READY-P9T-REMOVAL-RULE | do_now | no | completed | — |
| READY-P9T-SPEC-DIGEST | do_now | no | completed | — |
| READY-QFZ-DATE-ONLY-DIFF | do_now | no | completed | — |
| READY-QFZ-FUTURE-STAMP | do_now | no | completed | — |

*Machine review state — 15 findings; current: do_now 15, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

- Readiness, 2026-11-18. First pass typed six blocking findings (`READY-P9T-DOCS-SURFACES`, `READY-P9T-REMOVAL-RULE`, `READY-P9T-NAME-CITE`, `READY-P9T-SPEC-DIGEST`, `READY-P9T-BLOCKED-DRYRUN`, `READY-P9T-CITE-LEFT-BOUNDARY`); one repair pass amended the spec and fresh contexts of the raising lanes reverified all six. Council PASS, intent fit `establishes` (seats `red-team` fixed, `docs-contract-reviewer` rotating). After implementation one review-target bullet was corrected, which added `qa-reviewer` as a required lane; the three lanes and the council re-approved against receipt `review-policy-445dff81ce4cd0fb83fc` with no finding.
- Implementation, 2026-11-18. One implementer; coordinator check and corrections are in the spec's Progress Log.
- Delivery review and repair, 2026-11-18. First pass: `docs-contract-reviewer` approved; six blocking findings from the other seats: `DELIV-P9T-NAME-AFTER-SLASH` (`red-team`: a file the ledger names as the tail of another path read as unreferenced), `DELIV-P9T-JSON-ESCAPE-BOUNDARY` and `DELIV-P9T-RETURN-ORACLES` (`code-reviewer`), `DELIV-P9T-QA-UNTESTED-RETURNS`, `DELIV-P9T-QA-MESSAGE-COUNTS` and `DELIV-P9T-QA-NOTE4-PIN` (`qa-reviewer`). One repair pass (cycle 2, context `23p9u-delivery-repair-1`); fresh contexts of the raising lanes reverified all six, and `code-reviewer`, `qa-reviewer` and `docs-contract-reviewer` approved delivery after the repair. Red-team after the repair: 238 listed files across the existing record folders read as unreferenced on every flag, down from 256; of those, 8 are renamed copies of files the ledger names under another name and about 21 are named only inside sibling evidence files, which the report does not read. Follow-ups not done, for the operator: a Close prompt sentence asking the agent to search the ledger for a file's name stem and the folder's other extras for its name before removing a file with every flag false (red-team); a path written as a JSON object key in the ledger is not matched; the binding note 4 pin is a substring; directory totals stop at the top level; the ledger is read into memory without a size limit.
- Delivery council, 2026-11-18. PASS, intent fit `partially` (`ev-approval-council-delivery`; chair `council-chair`; seats `red-team` fixed and `docs-contract-reviewer` rotating). The seats did not disagree: reporting and guidance are delivered, the per-extra disposition is guidance only, and files beyond the cap of 50 are kept by the guidance without review. The verdict was recorded before the final full framework run.
- Reopened 2026-11-18 on the operator's direction (quoted in Watchpoints). `23qfz` was admitted: readiness typed two blocking findings (`READY-QFZ-DATE-ONLY-DIFF`, `READY-QFZ-FUTURE-STAMP`), repaired in one pass and reverified; the three lanes approved and the council passed readiness again with intent fit `establishes` (`ev-approval-council-readiness-3`). One implementer built `23qfz` and the two operator-directed changes to the Close guidance. Second delivery review: `code-reviewer` and `docs-contract-reviewer` approved, `red-team` found nothing blocking (replayed on this tree: 72 Git-changed documents, all re-dated on the next day under the old rule, none under the new one), `qa-reviewer` typed `DELIV-QFZ-RUN-DATE-UNPINNED` (a missing test), repaired and reverified; the same pass added one sentence on judging a file the report does not list. `code-reviewer`'s approval precedes that test-and-prose repair, which changed no code; `qa-reviewer` and `docs-contract-reviewer` approved after it. Follow-ups not done: `collect_changed_markdown_paths` skips non-ASCII paths and a root below the Git top level (both older than this wave); one Git read per changed document, sequential (about 9 s for 500 documents on macOS); a pure staged rename and a file with the `ident` attribute are stamped once without a content change.
- Delivery council, second sitting, 2026-11-18. PASS, intent fit `partially` (`ev-approval-council-delivery-2`; seats `red-team` fixed and `docs-contract-reviewer` rotating). `23qfz` meets its intent; `23p9t` and the Objective are partly met because the per-extra review is guidance only, by the operator's decision, and its effect on later closes is not yet observed. Recorded before the final full framework run.

Intent outcome: 2026-11-18: partial. Independent check by `qa-reviewer` at the second delivery review, incorporated as given, with its one open exception removed after that finding was repaired and reverified. Reporting is achieved on macOS: Close, in dry run and write, blocked or not, and on the `change_doc_unreadable` and `review_projection_failed` returns, lists the files in the closing record's folder that are not the record, an admitted spec or the ledger. Each listed file carries its size, citation state and loose-mention flags, capped at 50 listed with totals and a not-listed count; the unreadable-record return names the record and lists no files (evidence: `test_wave_work_lifecycle.py`, where mutations of each return attachment and each message count fail). Guidance is achieved: seed 190, its repository copy and the lifecycle template tell the agent to give every extra a disposition and to list and review the folder by hand, including files beyond the 50 the report lists. Before removing a `not_cited` file with all four flags false, the agent searches the ledger for its name stem and the other extras for its name (evidence: `test_compact_review_artifacts.py`, which fails when any of these sentences is removed or the old keep-unlisted sentence is restored). The per-extra review is guidance only: by the operator's decision nothing records or checks it, and the tool and its cap are unchanged. The gardener change is achieved: in default mode `docs_gardener` stamps a Git-changed document only when it differs from `HEAD` outside the date line and changed since its stamp; explicit modes are unchanged (evidence: `DefaultModeStampRuleTests`, which the pre-change gardener fails and where every guard mutation fails a test, including the passing of the run's date). Stated limits: a hand edit of a changed document's date line, a Git rewrite, a run across midnight or across time zones can each cause one extra stamp. Not established: that agents leave tidier folders and that multi-day diffs lose date-only churn, which later closes will show. Not executed: native Windows junction handling and the `core.autocrlf` behaviour there, WSL2, Python 3.11, a packaged upgrade.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 44 | 156,950 |
| implement | 14 | 830,353 |
| review | 206 | 6,831,214 |
| **Total** | **264** | **7,818,517** |

<!-- wave:context-efficiency-state {"generation":264,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":14,"content_source_credit":832620,"derived_artifact_credit":0,"direct_net":830353,"estimated_tokens_saved":830353,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":192,"response_debit":2075,"source_credit_count":13,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":44,"content_source_credit":345310,"derived_artifact_credit":811,"direct_net":156950,"estimated_tokens_saved":156950,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19468,"response_debit":175201,"source_credit_count":43,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5498},"review":{"calls":206,"content_source_credit":7545252,"derived_artifact_credit":8268,"direct_net":6831214,"estimated_tokens_saved":6831214,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":55249,"response_debit":673236,"source_credit_count":187,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6179}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":264,"content_source_credit":8723182,"derived_artifact_credit":9079,"direct_net":7818517,"estimated_tokens_saved":7818517,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":74909,"response_debit":850512,"source_credit_count":243,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11677},"wave_id":"23p9u close-record-folder-extras"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 3 | 0 | 3 | 386,646 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":3,"estimated_exploration_avoided":386646,"surfaced_events":3} -->
<!-- wave:exploration-avoided end -->
