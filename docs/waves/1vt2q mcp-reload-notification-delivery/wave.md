# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-20
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1vt2q mcp-reload-notification-delivery`
Title: Mcp Reload Notification Delivery

## Objective

`wf_reload_mcp` reports success for a `notifications/tools/list_changed` it never observes, because a sync in-loop tool returns before the task it schedules can run. When this wave closes the reload tool AWAITS its send and reports a real outcome, the `wf_upgrade` caller keeps delivering unchanged, and no response field claims more than the code saw. Now, because a brand-new MCP tool was just added and did not reach the host, which is the observation that opened this.

## Changes

Change ID: `1vt2p-bug reload-tool-list-notification-fire-and-forget`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (code and tests), operator (AC-8 end-to-end after a full host restart)
- Requested review lanes: architecture-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-08-20

## Wave Summary

Wave `1vt2q` (Mcp Reload Notification Delivery) delivered one change: `wf_reload_mcp` cannot observe or report the tool-list notification it schedules, because a sync in-loop tool returns before the task runs. Notable adjustments during implementation: `wf_reload_mcp` cannot observe or report the tool-list notification it schedules, because a sync in-loop tool returns before the task runs: Readiness cycle 1 repaired three packet defects before code: added the required architecture lane; closed and partitioned the exact internal/public notification state domain; and chose the explicit accepted-gap cancellation disposition with a polarity-test task.

**Changes delivered:**

- **`wf_reload_mcp` cannot observe or report the tool-list notification it schedules, because a sync in-loop tool returns before the task runs** (`1vt2p-bug reload-tool-list-notification-fire-and-forget`) — 11 ACs completed. Key decisions: Alternatives considered; (a) Retain a reference to the scheduled task and add a done-callback. (b) Leave the dispatch alone and only soften the reported fields.
## Watchpoints

- **Watchpoint (blocking): the `wf_upgrade` caller must keep delivering.** A previous design had it
  stop, proven on the wire (pristine `['notifications/tools/list_changed']`, plan-design `[]`).
  `test_cleanup_apply_invokes_mcp_reload` MOCKS `perform_mcp_reload`, so that regression would have
  shipped green. AC-1 pins wire traffic for exactly this reason and blocks delivery if it lapses.
- **Watchpoint: the original root cause was falsified.** A garbage-collection hazard on the scheduled
  task does not occur on this stack; an orphan-task control was collected while the real send-path task
  survived ten `gc.collect()` calls and delivered. Reference-retention work is out of scope; an
  implementer adding it has drifted, and reviewers should block it.
- **Watchpoint: class (c) transition.** `server.py` is un-reloadable runner code, so no `wf_reload_mcp`
  ever loads this fix. Every attached host must be restarted before AC-8 runs; do not retry the reload
  expecting different behaviour, and do not judge the repair from a pre-restart run.
- **Watchpoint: six existing tests in `test_server_tools.py`** assert on fields this change alters and
  must be rewritten or deleted. The churn is budgeted in AC-6 rather than deferred to discovery.
- **Watchpoint: first async tool in the surface.** Verified mechanically free (argument model,
  `_ensure_no_extra_args`, `convert_result`, re-registration survival, zero-buffer stream await), but a
  first of its kind; any surprise here is a follow-up candidate rather than an in-wave widening.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-DEL-RETIRED-VOCAB-SCOPE-001 | do_now | no | completed | architecture-reviewer, docs-contract-reviewer |
| DOCS-DEL-SEED160-RELOAD-CONTRACT-002 | do_now | no | completed | docs-contract-reviewer |
| PREP-ARCHITECTURE-LANE-002 | do_now | no | completed | wave-council-readiness, architecture-reviewer |
| PREP-CANCELLATION-DISPOSITION-003 | do_now | no | completed | wave-council-readiness, qa-reviewer, docs-contract-reviewer |
| PREP-NOTIFICATION-STATE-DOMAIN-001 | do_now | no | completed | wave-council-readiness, code-reviewer, qa-reviewer, docs-contract-reviewer |

*Machine review state — 5 findings; current: do_now 5, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-20: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the awaited direct-tool path can lose its notification if the request is cancelled mid-send, so the packet must state a disposition rather than leave retry semantics to implementation; strongest-alternative: shield or retry the send, rejected for this wave because cancellation can race partial transmission and a second frame could duplicate the notification; the accepted gap is instead explicit, no-retry, and pinned against the unchanged scheduled upgrade control.)

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 222 | 789,226 |
| implement | 65 | 0 |
| review | 230 | 6,010,766 |
| **Total** | **517** | **6,799,992** |

<!-- wave:context-efficiency-state {"generation":359,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":65,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-11956,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2240,"response_debit":15594,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5878},"plan":{"calls":222,"content_source_credit":1372384,"derived_artifact_credit":3031,"direct_net":789226,"estimated_tokens_saved":789226,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":30096,"response_debit":559599,"source_credit_count":89,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"review":{"calls":230,"content_source_credit":7019744,"derived_artifact_credit":988,"direct_net":6010766,"estimated_tokens_saved":6010766,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25770,"response_debit":985542,"source_credit_count":150,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":517,"content_source_credit":8392128,"derived_artifact_credit":4019,"direct_net":6788036,"estimated_tokens_saved":6799992,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":58106,"response_debit":1560735,"source_credit_count":239,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10730},"wave_id":"1vt2q mcp-reload-notification-delivery"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 42 | 0 | 10 | 38,341,564 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":10,"estimated_exploration_avoided":38341564,"surfaced_events":42} -->
<!-- wave:exploration-avoided end -->
