# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-20
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `216ga remove-change-depends-on-and-override-tolerant-tests`
Title: Remove Change Depends On And Override Tolerant Tests

## Objective

Answer Waveforge's note against `7ab3963d`: removing a change from a wave also removes its `Depends On:` lines (X8), and three core-behaviour tests skip when a distribution overrides the tool they drive (X1, X2, X3). No other product behaviour changes.

## Changes

Change ID: `216g8-bug remove-change-leaves-depends-on-line`
Change Status: `implemented`

Change ID: `216g9-debt core-tests-tolerate-distribution-overrides`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-20

## Wave Summary

Wave `216ga` (Remove Change Depends On And Override Tolerant Tests) delivered two changes: Removing a change from a wave also removes its Depends On lines and Core-behaviour tests keep running where a distribution overrides the tool they drive. Notable adjustments during implementation: Removing a change from a wave also removes its Depends On lines: Implemented. `_change_block_pattern` appends `(?:\nDepends On:[^\n]*)*` after the status line, still on one source line, so the census fragment is unchanged. New `WaveLifecycleMutationTests.test_remove_change_takes_its_depends_on_lines` covers middle (a / b dep a / c dep a), first, last before `## Participants`, and last at end of file without a trailing newline; each case asserts the whole record text and the parsed dependencies (`_parse_change_records`). Blank-line handling around the removed entry is unchanged from today. Scratch mutant (pre-fix pattern): all 4 subtests fail, each showing a leftover `Depends On:` line. CHANGELOG `[Unreleased]` opened with the Fixed bullet. Gapfill: shell reads and a Python mutation driver used for mutant setup; MCP reads used for review claims.; Core-behaviour tests keep running where a distribution overrides the tool they drive: Implemented. X1: the rendered `closable statuses` subtest calls `skipTest` when `sys.modules["mcp_tool_extensions"].override_targets()` names `wf_close_change`. X2: a local `dry_close()` uses `wf_close_wave_response` when `wf_close_wave` is overridden, for every close call in the test (the AC-2 probe caught a second call after `memory_reconcile` that the first edit missed). X3: the fixture wave is created through `wf_create_wave_response(..., parent="group")` when `wf_create_wave` is overridden. Scratch evidence: default baseline 4 tests OK, no skips; AC-1 mutants (rendered prompt drops `review`, memory gate returns no diagnostics, `is_operational_evidence_path` returns False) each fail their test; AC-2 with the branch forced, registered tools replaced by `None`, and the rendered prompt narrowed to `active`/`review`: 3 tests OK with exactly one skip (the rendered closable subtest), X2 still fails with the gate removed, and the HEAD tests fail under the same setup (X1 failure, X2 and X3 errors). Gapfill: Python mutation driver for scratch edits.

**Changes delivered:**

- **Removing a change from a wave also removes its Depends On lines** (`216g8-bug remove-change-leaves-depends-on-line`) — 3 ACs completed. Key decisions: Extend the existing pattern rather than parse entries into blocks.
- **Core-behaviour tests keep running where a distribution overrides the tool they drive** (`216g9-debt core-tests-tolerate-distribution-overrides`) — 3 ACs completed. Key decisions: X2 and X3 call the core response function when the driven tool is overridden; X1 skips only its rendered closable subtest.
## Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

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
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 14 | 330,763 |
| implement | 28 | 0 |
| review | 14 | 12,765 |
| **Total** | **56** | **343,528** |

<!-- wave:context-efficiency-state {"generation":54,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":28,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-2695,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":875,"response_debit":5336,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3516},"plan":{"calls":14,"content_source_credit":341120,"derived_artifact_credit":3451,"direct_net":330763,"estimated_tokens_saved":330763,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1575,"response_debit":16661,"source_credit_count":9,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4428},"review":{"calls":14,"content_source_credit":27216,"derived_artifact_credit":1083,"direct_net":12765,"estimated_tokens_saved":12765,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1874,"response_debit":16874,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3214}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":56,"content_source_credit":368336,"derived_artifact_credit":4534,"direct_net":340833,"estimated_tokens_saved":343528,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4324,"response_debit":38871,"source_credit_count":19,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11158},"wave_id":"216ga remove-change-depends-on-and-override-tolerant-tests"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
