# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-23
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `244in preserve-line-endings`
Title: Preserve Line Endings

## Objective

Every framework writer that edits an existing file keeps that file's own line endings, the same way on Windows, macOS, Linux and WSL2, so Windows checkouts no longer see whole-file line-ending churn and a mixed-ending spec is never corrupted to `\r\r\n`. Files the framework generates keep their LF policy, and gating digests keep their verified current behavior.

## Changes

Change ID: `244fj-bug preserve-line-endings-on-in-place-writes`
Change Status: `implemented`

## Participants

- Coordinator: main session
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, release-reviewer


Completed At: 2026-11-23

## Wave Summary

Wave `244in` (Preserve Line Endings) delivered one change: Preserve Line Endings on In-Place Writes and CRLF-Equal Gate Digests.

**Changes delivered:**

- **Preserve Line Endings on In-Place Writes and CRLF-Equal Gate Digests** (`244fj-bug preserve-line-endings-on-in-place-writes`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11, AC-12, AC-13 and AC-14 completed. Key decisions: In-place writers preserve the file's own line endings; generated files stay LF; reserialized operator files count as in-place; One new module `line_endings.py`, with each writer keeping its own write primitive and passing bytes.

## Watchpoints

- Watchpoint: wave 244fi also changes `memory_records.py` and `wf_server/memory_handlers.py`; implement this wave only after 244fi closes and its files are committed.
- Watchpoint: open `framework_edit_allowed` around the edits and close it after; no framework edits while a full test suite runs.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 244in-arch-census-transitive-class-gap | do_now | no | completed | architecture-reviewer |
| 244in-arch-census-wrapper-and-generated-gap | do_now | no | completed | architecture-reviewer |
| 244in-arch-exempt-wrapper-blindspot | do_now | no | completed | architecture-reviewer |
| 244in-cr-writer-census-incomplete | do_now | no | completed | — |
| 244in-f-upgrade-ext-import | do_now | no | completed | — |
| 244in-qa-census-wrapper-blindspot | do_now | no | completed | — |
| 244in-qa-crlf-simulation-quadrant | do_now | no | completed | — |
| DC-1 | do_now | no | completed | — |
| RT-1 | do_now | no | completed | — |

*Machine review state — 9 findings; current: do_now 9, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | Phase | State | Why | Next action |
| --- | --- | --- | --- | --- |
| council-readiness | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| release-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking); known-bad control not applicable: Inspected the changed Decision Log and Serialization Points against the release lane (pack contents, upgrade loading, CHANGELOG); no defect found, so no known-bad control applies at readiness. | none |
| release-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
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
| plan | 90 | 1,289,641 |
| implement | 74 | 0 |
| review | 84 | 1,436,297 |
| **Total** | **248** | **2,725,938** |

<!-- wave:context-efficiency-state {"generation":229,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":74,"content_source_credit":3543,"derived_artifact_credit":0,"direct_net":-12217,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3243,"response_debit":19257,"source_credit_count":2,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6740},"plan":{"calls":90,"content_source_credit":1629350,"derived_artifact_credit":1773,"direct_net":1289641,"estimated_tokens_saved":1289641,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":60574,"response_debit":291703,"source_credit_count":74,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10795},"review":{"calls":84,"content_source_credit":1653807,"derived_artifact_credit":3251,"direct_net":1436297,"estimated_tokens_saved":1436297,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":20331,"response_debit":213986,"source_credit_count":38,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":13556}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":248,"content_source_credit":3286700,"derived_artifact_credit":5024,"direct_net":2713721,"estimated_tokens_saved":2725938,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":84148,"response_debit":524946,"source_credit_count":114,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":31091},"wave_id":"244in preserve-line-endings"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
