# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-10
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `22yox blank-line-before-headings`
Title: Blank Line Before Headings

## Objective

Readers and tools get Markdown in which every heading has a blank line above it: prepare and close fix the wave's own documents, the producers stop writing the defect, and a lint rule covers live documents. The close-time wave summary reports completed and deferred criteria accurately and quotes no superseded notes. Closed wave records and archived memories are not rewritten.

## Changes

Change ID: `22y1k-enh blank-line-before-headings`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (root); reviewers are read-only
- Requested review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-11-10

## Wave Summary

Wave `22yox` (Blank Line Before Headings) delivered one change: Keep a Blank Line Before Every Markdown Heading.

Intent outcome: achieved, on macOS. Evidence: every live Markdown heading now has a blank line above it (docs-lint reports no `heading_without_blank_line_before` warning; 24 live files fixed; closed wave folders and archived memories unchanged against `85de7176`); prepare inserts the line in the wave's own documents before the review-policy receipt is computed and leaves closed records alone; close repairs the record it writes; the close summary lists each change's completed and deferred criteria with their notes and no longer quotes the Progress Log, checked by replay on the 23041 record and on all 125 historical deferred criteria; the advisory check fails nothing. Full suite 12,741 tests OK. Limits: no downstream upgrade was run, so "fails no repository on upgrade" follows from the advisory polarity and is not measured; "no other document is touched at close" was read from the code; no native Windows, Linux or WSL2 run.

**Changes delivered:**

- **Keep a Blank Line Before Every Markdown Heading** (`22y1k-enh blank-line-before-headings`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7 and AC-8 completed. Key decisions: Fix headings at prepare for the wave's documents and at close for its record, fix the producers, and warn in live documents; Build the summary from criteria states, notes and the Decision Log, not the Progress Log.

## Watchpoints

- Watchpoint: wave 230k8 is readied or open in another session; this wave implements only when 230k8 is not open. Do not edit closed wave records or archived memories. Run the full suite last before close, when no other session is editing tracked files.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| RT-DEL-1 | do_now | no | completed | — |
| RT-DEL-2 | do_now | no | completed | — |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
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
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

- 2026-11-10: Delivery review PASS. Required lanes code-reviewer, qa-reviewer, architecture-reviewer and docs-contract-reviewer each ran in a fresh, independent context and approved. The delivery council ran with a red-team adversarial primer first, then those four seats with the primer, then the council-chair's synthesis: PASS, intent fit establishes. The primer raised two findings, RT-DEL-1 (the close summary's own criteria parser garbled labels and dropped deferral notes) and RT-DEL-2 (prepare rewrote a closed record's documents); both were repaired in cycle 1 and reverified by a separate red-team context. Lower lane findings were fixed before any approval. The typed ledger is authority.
- Intent outcome: achieved, on macOS. Evidence: every live Markdown heading now has a blank line above it (docs-lint reports no `heading_without_blank_line_before` warning; 24 live files fixed; closed wave folders and archived memories unchanged against `85de7176`); prepare inserts the line in the wave's own documents before the review-policy receipt is computed and leaves closed records alone; close repairs the record it writes; the close summary lists each change's completed and deferred criteria with their notes and no longer quotes the Progress Log, checked by replay on the 23041 record and on all 125 historical deferred criteria; the advisory check fails nothing. Full suite 12,741 tests OK. Limits: no downstream upgrade was run, so "fails no repository on upgrade" follows from the advisory polarity and is not measured; "no other document is touched at close" was read from the code; no native Windows, Linux or WSL2 run.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 20 | 50,743 |
| implement | 27 | 0 |
| review | 64 | 3,355,161 |
| **Total** | **111** | **3,405,904** |

<!-- wave:context-efficiency-state {"generation":113,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":27,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-2693,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":846,"response_debit":6054,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4207},"plan":{"calls":20,"content_source_credit":83178,"derived_artifact_credit":2641,"direct_net":50743,"estimated_tokens_saved":50743,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2799,"response_debit":37779,"source_credit_count":30,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5502},"review":{"calls":64,"content_source_credit":3477976,"derived_artifact_credit":1665,"direct_net":3355161,"estimated_tokens_saved":3355161,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9350,"response_debit":118906,"source_credit_count":97,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3776}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":111,"content_source_credit":3561154,"derived_artifact_credit":4306,"direct_net":3403211,"estimated_tokens_saved":3405904,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12995,"response_debit":162739,"source_credit_count":127,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":13485},"wave_id":"22yox blank-line-before-headings"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 10 | 0 | 7 | 5,363,195 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":7,"estimated_exploration_avoided":5363195,"surfaced_events":10} -->
<!-- wave:exploration-avoided end -->
