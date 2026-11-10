# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-10
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `23041 writing-guide-concrete-precision`
Title: Writing Guide Concrete Precision

## Objective

Readers of plans, specifications and status records get text that names the specific function, file, setting, number or observed output a claim depends on. The writing guide gains one specificity rule, extends its existing worked example to show it and defines "consequential"; accuracy takes precedence over length. No new review lane, linter or gate. A deferral reason written by `wf_mark_ac` no longer splits a multi-line acceptance criterion, and docs-lint reads a reason anywhere in the criterion.

## Changes

Change ID: `23040-enh writing-guide-concrete-precision`
Change Status: `implemented`

Change ID: `23042-bug mark-ac-reason-splits-multiline-criterion`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (root); reviewers are read-only
- Requested review lanes: qa-reviewer, docs-contract-reviewer, code-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-11-10

## Wave Summary

Wave `23041` (Writing Guide Concrete Precision) delivered two changes.

**Changes delivered:**

- **Make the Writing Guide's Precision Rule Concrete** (`23040-enh writing-guide-concrete-precision`). AC-1 and AC-2 completed; AC-3 deferred (`[~]`). The guide now requires a requirement, acceptance criterion or status claim to name or define the setting, file, function, command, term, error text or limit it depends on, or to say it is not yet known and what will identify it. An imposed limit carries its number and unit; a quantity adjective a requirement acts on is a limit, a category adjective is a term to define, and a quality adjective needs a definition or observable result. Requirements carry no open hedge, and removing one from an obligation keeps **must**. A defect plan shows the observed failure. The 8 MiB example gained an abstract counterpart, and "consequential" is defined at its first use. At the operator's direction (accuracy and precise language over length) there is no word cap; the guide grew from 1,156 to 1,487 words. AC-3, a blind control and candidate reader check on six frozen plans, tied at 5 of 9 key items with 0 false positives each, so no improvement is claimed. That check ran on the guide before the delivery-review precision fixes, which are untested.
- **Keep a Deferral Reason From Splitting a Multi-Line Acceptance Criterion** (`23042-bug mark-ac-reason-splits-multiline-criterion`). All 5 ACs completed. `wf_mark_ac` now writes a deferral reason for a multi-line criterion as a `*Status: ...*` line after the criterion, at its blockquote depth and with the document's line ending; a single-line criterion, or one whose continuation holds a fenced block, keeps the reason on its first line. The inline-note lint keeps its first-line checks and also accepts a `*Status:*` continuation line, and nothing else. The item continuation rule moved to `change_doc_checklist.item_block_end`, shared by the tool and the lint. The 23040 AC-3 note was moved to the new form. Accepted gap: a CRLF document ending on a multi-line criterion with no final newline.

## Watchpoints

- Watchpoint: the AC-3 fixtures are frozen under `.wavefoundry/work/23041/ac3/`; do not edit them. One reader batch; a failed or inconclusive AC-3 is marked [~] with its counts, with no second attempt in this wave. Run the full suite last before close.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
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

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 50 | 526,125 |
| implement | 31 | 0 |
| review | 130 | 1,907,844 |
| **Total** | **211** | **2,433,969** |

<!-- wave:context-efficiency-state {"generation":213,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":31,"content_source_credit":28300,"derived_artifact_credit":801,"direct_net":-827,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2399,"response_debit":33050,"source_credit_count":6,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5521},"plan":{"calls":50,"content_source_credit":558224,"derived_artifact_credit":3317,"direct_net":526125,"estimated_tokens_saved":526125,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3142,"response_debit":50031,"source_credit_count":32,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":17757},"review":{"calls":130,"content_source_credit":2235924,"derived_artifact_credit":6816,"direct_net":1907844,"estimated_tokens_saved":1907844,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11562,"response_debit":327110,"source_credit_count":76,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3776}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":211,"content_source_credit":2822448,"derived_artifact_credit":10934,"direct_net":2433142,"estimated_tokens_saved":2433969,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17103,"response_debit":410191,"source_credit_count":114,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":27054},"wave_id":"23041 writing-guide-concrete-precision"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 16 | 0 | 9 | 8,054,408 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":9,"estimated_exploration_avoided":8054408,"surfaced_events":16} -->
<!-- wave:exploration-avoided end -->
