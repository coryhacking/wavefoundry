# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-26
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21s91 ce-projection-monitor-cpu`
Title: CE Projection Monitor CPU

## Objective

Long-running Wavefoundry MCP servers stop spending a CPU core re-attempting context-efficiency projections that cannot succeed. Measure of success: on this repository's real telemetry store, a monitor tick after the first attempt makes no wave lookup. Hard-boundary projection and the pending census are unchanged.

## Changes

Change ID: `21s90-bug ce-projection-monitor-retries-terminal-waves`
Change Status: `implemented`

## Participants

- Coordinator: implementer
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-26

## Wave Summary

Wave `21s91` (CE Projection Monitor CPU) delivered one change: CE projection monitor retries closed and unknown waves on every tick. Notable adjustments during implementation: CE projection monitor retries closed and unknown waves on every tick: Readiness repair pass from the red-team and security seats: raise counts as retryable, contention bound stated, per-wave lists named, reopen risk, AC-4 on a scratch copy, AC-2 labelled a regression guard, index-source-guard suite added, unverified hard-boundary claim removed; CE projection monitor retries closed and unknown waves on every tick: Known-bad: on a scratch copy with both new blocks removed, all five new tests fail; with only parking removed, the AC-1, AC-2, mixed-pass and hard-boundary tests fail.

Intent outcome: 2026-10-26, drafted by the coordinator, confirmed by the qa-reviewer with a wording correction. Established. On a scratch copy of this repository's real store, the monitor attempted all 28 pending waves once (2 open waves projected, 26 closed or unknown waves parked), then made no wave lookup on the next tick past the quiet period (0.02 s against 7.01 s for the attempting tick, and against 11.5 s every 15 s before the fix). Unit tests show the same for closed and unknown waves, back-off for retryable failures and raises, and that a hard boundary still projects a parked wave. Not shown directly: a live multi-server run on the fixed code; restarted servers will attempt the stuck waves once each.

**Changes delivered:**

- **CE projection monitor retries closed and unknown waves on every tick** (`21s90-bug ce-projection-monitor-retries-terminal-waves`) — 5 ACs completed. Key decisions: Park terminal waves in the monitor's `observed` map until their generation changes; restart the quiet period after a retryable failure. Efficacy: replaying the incident, the 27 waves are attempted once and then cost one snapshot read each per tick; it controls the outcome directly; it can wrongly park a wave that is reopened (`unseal_wave` leaves the generation unchanged) or whose folder appears later, until its next telemetry event or a hard boundary (see Risks); whether hard boundaries clear closed waves from pending is `unverified`, since 23 remain pending here, and the fix does not rely on it; success is measured by AC-4 and by servers staying idle
## Watchpoints

- Watchpoint: open `framework_edit_allowed` before the framework edit and close it after.
- Follow-up: the four phantom pending rows in the telemetry store stay; their origin is untraced.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 21S91-DEL-CONTENTION-COST | dont_do_later | no | not_required | — |

*Machine review state — 1 findings; current: do_now 0, maybe_later 0, dont_do_later 1, not_issue 0*
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

## Review Checkpoints

Intent outcome: 2026-10-26, drafted by the coordinator, confirmed by the qa-reviewer with a wording correction. Established. On a scratch copy of this repository's real store, the monitor attempted all 28 pending waves once (2 open waves projected, 26 closed or unknown waves parked), then made no wave lookup on the next tick past the quiet period (0.02 s against 7.01 s for the attempting tick, and against 11.5 s every 15 s before the fix). Unit tests show the same for closed and unknown waves, back-off for retryable failures and raises, and that a hard boundary still projects a parked wave. Not shown directly: a live multi-server run on the fixed code; restarted servers will attempt the stuck waves once each.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 21 | 121,867 |
| implement | 19 | 0 |
| review | 34 | 702,634 |
| **Total** | **74** | **824,501** |

<!-- wave:context-efficiency-state {"generation":64,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":19,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-5903,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4298,"response_debit":4929,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3324},"plan":{"calls":21,"content_source_credit":153598,"derived_artifact_credit":2123,"direct_net":121867,"estimated_tokens_saved":121867,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2197,"response_debit":36710,"source_credit_count":30,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5053},"review":{"calls":34,"content_source_credit":750900,"derived_artifact_credit":2299,"direct_net":702634,"estimated_tokens_saved":702634,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3594,"response_debit":50660,"source_credit_count":21,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3689}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":74,"content_source_credit":904498,"derived_artifact_credit":4422,"direct_net":818598,"estimated_tokens_saved":824501,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10089,"response_debit":92299,"source_credit_count":51,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12066},"wave_id":"21s91 ce-projection-monitor-cpu"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
