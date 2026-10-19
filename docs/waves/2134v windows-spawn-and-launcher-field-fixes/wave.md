# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-19
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `2134v windows-spawn-and-launcher-field-fixes`
Title: Windows Spawn And Launcher Field Fixes

## Objective

Windows operators stop losing the MCP connection when write tools trigger a background index refresh, and rendered hooks stop passing the host's pipes to their detached children. POSIX behaviour and detach semantics are unchanged.

## Changes

Change ID: `2134t-bug windows-background-spawn-handle-inheritance`
Change Status: `implemented`

## Participants

- Coordinator: Engineering
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-19

## Wave Summary

Wave `2134v` (Windows Spawn And Launcher Field Fixes) delivered one change: Background spawns inherit handles on Windows. Notable adjustments during implementation: Background spawns inherit handles on Windows: Delivery repair (QA blocker on AC-2): the census checked only `close_fds`, so the rendered spawns' other arguments were unguarded (mutants `cwd=None` in `claude_stop_source` and `stdin` removed in `claude_context_efficiency_source` survived). Added `test_rendered_background_spawns_keep_their_isolation_arguments`: for `hook_helpers`, `claude_context_efficiency_source` and `claude_stop_source`, exactly one background `Popen` with `stdin`/`stdout`/`stderr` = `subprocess.DEVNULL`, a non-literal `cwd`, the detach `**` splat and `close_fds=True`; both mutants now fail it. Not covered (accepted): a positional `close_fds` argument (the eighth positional `Popen` parameter; no framework call passes it positionally).

**Changes delivered:**

- **Background spawns inherit handles on Windows** (`2134t-bug windows-background-spawn-handle-inheritance`) — 4 ACs completed. Key decisions: `close_fds=True` on every OS at these spawns, enforced by a census test.
## Watchpoints

- Watchpoint: open `framework_edit_allowed` before editing framework scripts, whatever the edit tool, and close it after.
- Watchpoint: the Windows disconnect cannot be reproduced here; record Waveforge's field confirmation when it arrives.
- Watchpoint: reply to Waveforge on W1 and W2, together with the 2134s vocabulary reply.

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
| plan | 16 | 1,638,526 |
| implement | 31 | 30,576 |
| review | 7 | 19,023 |
| **Total** | **54** | **1,688,125** |

<!-- wave:context-efficiency-state {"generation":53,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":31,"content_source_credit":40283,"derived_artifact_credit":0,"direct_net":30576,"estimated_tokens_saved":30576,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1063,"response_debit":9330,"source_credit_count":3,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":686},"plan":{"calls":16,"content_source_credit":1660150,"derived_artifact_credit":3474,"direct_net":1638526,"estimated_tokens_saved":1638526,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1744,"response_debit":27782,"source_credit_count":43,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4428},"review":{"calls":7,"content_source_credit":28620,"derived_artifact_credit":1152,"direct_net":19023,"estimated_tokens_saved":19023,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1919,"response_debit":12044,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3214}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":54,"content_source_credit":1729053,"derived_artifact_credit":4626,"direct_net":1688125,"estimated_tokens_saved":1688125,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4726,"response_debit":49156,"source_credit_count":56,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8328},"wave_id":"2134v windows-spawn-and-launcher-field-fixes"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
