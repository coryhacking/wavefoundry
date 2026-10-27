# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-26
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21s1u retire-orphaned-ce-pending-rows`
Title: Retire Orphaned CE Pending Rows

## Objective

Context-efficiency pending rows whose wave id matches no wave record stop lingering forever: a reload or upgrade retires those inactive for 30 days, keeping their telemetry. Measure of success: on a copy of this repository's store, the four stale unknown ids leave the pending census and the recent one stays. Live waves, recent rows, unreadable checkouts and short-id alias rows (a follow-up) are never touched.

## Changes

Change ID: `21s1t-enh retire-orphaned-ce-pending-rows`
Change Status: `implemented`

## Participants

- Coordinator: implementer
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-26

## Wave Summary

Wave `21s1u` (Retire Orphaned CE Pending Rows) delivered one change: Retire orphaned context-efficiency pending rows. Notable adjustments during implementation: Retire orphaned context-efficiency pending rows: Readiness repair pass from the red-team and security seats and the code and QA lanes: callers corrected to reload and upgrade, alias rows named out of scope, pass-level discovery guard with `_find_wave_md_detailed`, one transaction outside the publication lock, exact row predicate, injectable `now`, retirement only after a complete loop, AC-2 negatives made non-vacuous with sealed and generation-race cases, AC-3 labelled a regression guard, AC-4 pinned instant and alias counts, three new Risks; Retire orphaned context-efficiency pending rows: Delivery finding 21S1U-DEL-PHASE-ACTIVITY (qa-reviewer, do_now): no test covered `phase_state` activity. Added `test_recent_phase_activity_keeps_an_unknown_row`; the phase_state-branch mutant now fails it.

Intent outcome: 2026-10-26, drafted by the coordinator, confirmed by the qa-reviewer (its wording correction on last-activity coverage is resolved by the added phase_state test). Established. On a scratch copy of this repository's store and wave tree with `now` fixed at 2026-10-26T00:00Z, one hard-boundary pass retired the four unknown ids idle for more than 30 days (`1u12h`, `1v4ms`, `1yzj9 ac-locality-sensor-blocking`, `zzzz-council-probe-nonexistent`), kept their telemetry, left `20np3` (12 days idle) pending and reported, and left all 22 short-id alias rows pending (pending 27 to 23). Unit tests show recent (by telemetry or by phase), existing, sealed and generation-moved rows are spared, unreadable or empty discovery and a raised resolution retire nothing, the automatic monitor never retires, and new telemetry re-pends a retired id. Not shown: a live reload or upgrade on this repository, which will happen at the next reload. The 22 alias rows remain for a follow-up change. The affected suite also passes under the downstream Set/Wave vocabulary profile.

**Changes delivered:**

- **Retire orphaned context-efficiency pending rows** (`21s1t-enh retire-orphaned-ce-pending-rows`) — 5 ACs completed. Key decisions: Retire at the hard boundary by setting `pending=0`, guarded by 30 days of inactivity, unresolvable id, readable and non-empty wave discovery, and the generation; keep all telemetry. Efficacy: replaying today's data, four of the five unknown-id rows retire at the next reload or upgrade and the fifth after 2026-11-13, while the 22 alias rows are untouched (named as a follow-up); it controls the outcome directly; it could wrongly retire a row only if a wave record is missing without an unreadable signal for 30 days while its telemetry is real, and then new telemetry re-pends it and no data is lost; success is AC-4 and a pending census without them
## Watchpoints

- Watchpoint: open `framework_edit_allowed` before the framework edit and close it after.
- Blocking: wave 21s91 must close before this wave can be activated (single OPEN wave).

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 21S1U-DEL-PHASE-ACTIVITY | do_now | no | completed | — |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
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

Intent outcome: 2026-10-26, drafted by the coordinator, confirmed by the qa-reviewer (its wording correction on last-activity coverage is resolved by the added phase_state test). Established. On a scratch copy of this repository's store and wave tree with `now` fixed at 2026-10-26T00:00Z, one hard-boundary pass retired the four unknown ids idle for more than 30 days (`1u12h`, `1v4ms`, `1yzj9 ac-locality-sensor-blocking`, `zzzz-council-probe-nonexistent`), kept their telemetry, left `20np3` (12 days idle) pending and reported, and left all 22 short-id alias rows pending (pending 27 to 23). Unit tests show recent (by telemetry or by phase), existing, sealed and generation-moved rows are spared, unreadable or empty discovery and a raised resolution retire nothing, the automatic monitor never retires, and new telemetry re-pends a retired id. Not shown: a live reload or upgrade on this repository, which will happen at the next reload. The 22 alias rows remain for a follow-up change. The affected suite also passes under the downstream Set/Wave vocabulary profile.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 12 | 9,623 |
| implement | 12 | 0 |
| review | 10 | 40,608 |
| **Total** | **34** | **50,231** |

<!-- wave:context-efficiency-state {"generation":34,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":12,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-1950,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":680,"response_debit":3838,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2568},"plan":{"calls":12,"content_source_credit":23763,"derived_artifact_credit":856,"direct_net":9623,"estimated_tokens_saved":9623,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1515,"response_debit":18534,"source_credit_count":9,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5053},"review":{"calls":10,"content_source_credit":59535,"derived_artifact_credit":1008,"direct_net":40608,"estimated_tokens_saved":40608,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3866,"response_debit":19758,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3689}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":34,"content_source_credit":83298,"derived_artifact_credit":1864,"direct_net":48281,"estimated_tokens_saved":50231,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6061,"response_debit":42130,"source_credit_count":23,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11310},"wave_id":"21s1u retire-orphaned-ce-pending-rows"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
