# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-26
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21s7b dashboard-stale-runtime-reporting`
Title: Dashboard Stale Runtime Reporting

## Objective

Operators using a long-running dashboard can tell when it is running index code older than what is installed: the Index dialog shows the refusal and its recovery action instead of "not built", and every view shows a restart notice while the condition holds. The index-compatibility guard is unchanged and the dashboard never restarts itself.

## Changes

Change ID: `21s79-bug dashboard-index-panel-hides-refusal`
Change Status: `implemented`

Change ID: `21s7a-enh dashboard-stale-runtime-banner`
Change Status: `implemented`

## Participants

- Coordinator: main session
- Write-owning roles: implementer (main session)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-27

## Wave Summary

Wave `21s7b` (Dashboard Stale Runtime Reporting) delivered two changes: Dashboard Index panel reports a refused read as "not built" and Dashboard reports when it is running stale index code. Notable adjustments during implementation: Dashboard Index panel reports a refused read as "not built": Follow-up (not this scope): two other surfaces still read a refusal as absent: the Graph view's "Graph index has not been built yet." and the main Index metric card's "Missing". The global notice from `21s7a` now explains both while the runtime is stale.; Dashboard Index panel reports a refused read as "not built": Delivery review follow-ups (one future change, not this scope): (I1) for `index_version_newer` and `index_compatibility_unproven` no notice shows, so the Index metric card ("Missing") and Graph view ("not built yet") still contradict the dialog; (M1) a `graph_publication_in_flight` diagnostic now reads "The index could not be read" and should read as in progress; (M2) the `title` tooltip for non-stale compatibility codes carries the exception's restart text, contradicting the visible `index_health()` action; the semantic path maps migration failures to `index_health()` where the graph path names `wf_upgrade_status()`; the compatibility code set is defined in three places; the JS render path is checked only by source-string tests plus screenshots.

**Changes delivered:**

- **Dashboard Index panel reports a refused read as "not built"** (`21s79-bug dashboard-index-panel-hides-refusal`) — 4 ACs completed. Key decisions: Carry a typed diagnostic from the server payload into both Index sections.; Readiness repair (red-team F3, F4, F6): restart label only for `index_runtime_stale`; rendered check is required AC-2 evidence; two other swallowing reads recorded as out of scope.
- **Dashboard reports when it is running stale index code** (`21s7a-enh dashboard-stale-runtime-banner`) — 4 ACs completed. Key decisions: Detect with the existing compatibility check and show a global notice naming **Restart dashboard**.; Readiness repair (red-team F1, F2, F5): check at request time with an uncached `ensure_runtime_current()`, no stat-signature cache, no `server_impl` reuse.
## Watchpoints

- Watchpoint: 21s79 lands before 21s7a; both edit `dashboard.js` and `test_dashboard_server.py`.
- Framework edits need `framework_edit_allowed`; close it afterwards.
- Follow-up: dashboard CPU and watcher stalls on the stale process are out of scope (cause unverified); re-observe after delivery.

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

## Review Checkpoints

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 93 | 0 |
| implement | 42 | 119,260 |
| review | 44 | 372,415 |
| **Total** | **179** | **491,675** |

<!-- wave:context-efficiency-state {"generation":100,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":42,"content_source_credit":126612,"derived_artifact_credit":0,"direct_net":119260,"estimated_tokens_saved":119260,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1591,"response_debit":9983,"source_credit_count":3,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4222},"plan":{"calls":93,"content_source_credit":26534,"derived_artifact_credit":3535,"direct_net":-16812,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5719,"response_debit":46215,"source_credit_count":15,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5053},"review":{"calls":44,"content_source_credit":452050,"derived_artifact_credit":1148,"direct_net":372415,"estimated_tokens_saved":372415,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5435,"response_debit":79037,"source_credit_count":21,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3689}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":179,"content_source_credit":605196,"derived_artifact_credit":4683,"direct_net":474863,"estimated_tokens_saved":491675,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12745,"response_debit":135235,"source_credit_count":39,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12964},"wave_id":"21s7b dashboard-stale-runtime-reporting"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 1 | 0 | 1 | 107,177 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":1,"estimated_exploration_avoided":107177,"surfaced_events":1} -->
<!-- wave:exploration-avoided end -->
