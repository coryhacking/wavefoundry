# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-14
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20gz5 child-log-timeout-check`
Title: Child Log Timeout Check

## Objective

Remove the demonstrated scheduler-dependent failure in the large child-log timeout fixture while preserving actual deadline and bounded-log coverage. Resume the official release qualification with unchanged production logging behavior.

## Changes

Change ID: `20gz4-bug deterministic-child-log-timeout-check`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (coordinator)
- Requested review lanes: code-reviewer, qa-reviewer
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-14

## Wave Summary

Wave `20gz5` (Child Log Timeout Check) delivered one change: Make the large child-log timeout check deterministic.

**Changes delivered:**

- **Make the large child-log timeout check deterministic** (`20gz4-bug deterministic-child-log-timeout-check`) — 3 ACs completed. Key decisions: Observe delivered endings, then inject timeout at the process wait boundary in this finalization test
## Watchpoints

- Watchpoint: observe both output endings before the injected timeout; keep the independent real-deadline tests.
- No production edits or concurrent review probes during full qualification.
- Allocation: scoped independent reviewers use gpt-6.1-sol/high; actual model identity is not exposed.
- Only temporary review reports; final evidence belongs in this record.

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
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 107 | 0 |
| implement | 58 | 92,800 |
| review | 26 | 8,773 |
| **Total** | **191** | **101,573** |

<!-- wave:context-efficiency-state {"generation":93,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":58,"content_source_credit":240904,"derived_artifact_credit":0,"direct_net":92800,"estimated_tokens_saved":92800,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1563,"response_debit":149137,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2596},"plan":{"calls":107,"content_source_credit":168253,"derived_artifact_credit":471,"direct_net":-218479,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7735,"response_debit":383273,"source_credit_count":26,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":26,"content_source_credit":40747,"derived_artifact_credit":136,"direct_net":8773,"estimated_tokens_saved":8773,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4677,"response_debit":30364,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2931}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":191,"content_source_credit":449904,"derived_artifact_credit":607,"direct_net":-116906,"estimated_tokens_saved":101573,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13975,"response_debit":562774,"source_credit_count":54,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9332},"wave_id":"20gz5 child-log-timeout-check"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 2 | 0 | 2 | 2,636,098 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":2636098,"surfaced_events":2} -->
<!-- wave:exploration-avoided end -->
## Review Checkpoints

- Shared release follow-up: final default suite passed all 12,402 tests. The declared-profile run later failed the unchanged nonzero-exit leg's `FINAL-STDOUT` assertion at test_child_tee.py:178, before reaching the repaired timeout leg. The report remains red; no production regression or timing-only cause is claimed from this run. Operator deferred timing investigation while concurrent reviews run, requested planned follow-up 20h6q / 20gz6 for this log-content check and explicitly authorized the release with the exception. No further test or source repair was started.

- Delivery: independent code and QA approved with no findings. Canonical `run_tests.py --file test_child_tee.py`: 20 tests, zero skips, 8.081 seconds. Both reviewers delayed the third `FINAL-STDERR` read by 2.1 seconds: the fixed large-output test passed. Suppressing `_BoundedLog.finalize` only for its third, timeout log failed the elision assertion in both reviews; nonzero/check=True legs still passed. QA independently passed the two unchanged real deadline controls. These are controlled macOS fixtures, not arbitrary per-stream retention or native Windows qualification. Production `child_tee.py` remains blob `c115cc5b31841f55c420b9771edc0259a4d3fb01`; changed test blob `45ab04c8afb8e1986208024ba4d2ad8e88a6f32b`. Full release qualification is shared with wave 20gz3; operator closure remains pending.

- Readiness: standard red-team primer; independent architecture-reviewer, security-reviewer, qa-reviewer and reality-checker fixed seats; rotating release-reviewer plus separate code-reviewer. Unanimous approval, no findings. All fixed seats weighed a real-wait-after-observation alternative: the selected injected timeout is narrower and faster, while separate unchanged tests retain real elapsed-time coverage. Claims apply to the controlled fixture, not arbitrary per-stream retention. The initial architecture context lacked its pre-primer stance and was replaced by a fresh read-only assessment; only the replacement counts.

## Progress Log

- 2026-10-14: Operator authorized closing all six paused waves, committing/pushing and a local 1.31.0 pack, with timing investigation still deferred and one shared default qualification run. That run completed 11,671 tests / 187 files / 12 skips in 884.077s, exit 1: test_tensorwell_client.ClientTests.test_cli_exact_child_timeout_bounded_capture expected the oversized-output ValueError but the child wait reached its deadline and raised TimeoutError. The projection-timing file passed. Source-only independent triage does not establish a capture-cap defect or a harmless scheduling flake; final QA remains unproven. All 60 reviewed source hashes stayed unchanged. No retry or profile run followed the failed default; no current green receipt, closure or new pack is claimed. Compact report remains in ignored cache (close-pack-1.31-default.json); routine log remains temporary. Existing source reviews and terminal repairs stand. Memory proposals add no action beyond canonical tests/guidance, so none were selected; folders retain only wave/change records and typed ledgers.
