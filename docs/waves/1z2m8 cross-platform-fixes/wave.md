# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-26
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1z2m8 cross-platform-fixes`
Title: Cross Platform Fixes

## Objective

Fix five cross-platform defects found by review before the 1.27.0 release: the Windows launcher's misleading Python hint, `.cmd` sensors on Windows, the session-start hook on Python below 3.11, stamp adoption without hard links, and Windows blocking locks that give up after ten seconds.

## Changes

Change ID: `1z2m7-bug cross-platform-launcher-sensor-and-lock-fixes`
Change Status: `review`

## Participants

- Coordinator: operator session
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-09-26

## Wave Summary

Wave `1z2m8` (Cross Platform Fixes) delivered one change: Cross-Platform Fixes: Launcher Hint, Sensors, Old Python, Stamp Links and Windows Lock Waits. Notable adjustments during implementation: Cross-Platform Fixes: Launcher Hint, Sensors, Old Python, Stamp Links and Windows Lock Waits: Delivery review approved (no blocking findings); its wording note fixed (a relative sensor path resolves against the MCP server's working directory on Windows). The first full run failed `test_patch_census_has_nonvacuous_runtime_obligations`: the `_IS_WINDOWS` value patch in `test_sensor_runner.py` lacked the required `inert-by-design:` note; added. Full suite then green: 9714 tests across 129 files.

**Changes delivered:**

- **Cross-Platform Fixes: Launcher Hint, Sensors, Old Python, Stamp Links and Windows Lock Waits** (`1z2m7-bug cross-platform-launcher-sensor-and-lock-fixes`) — 6 ACs completed. Key decisions: Gate the launcher hint on a live `python3` probe rather than on exit codes; Accept cmd.exe argument parsing for resolved `.cmd` sensors
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
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 10 | 0 |
| implement | 3 | 1,932 |
| review | 7 | 17,667 |
| **Total** | **20** | **19,599** |

<!-- wave:context-efficiency-state {"generation":20,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":3,"content_source_credit":4150,"derived_artifact_credit":265,"direct_net":1932,"estimated_tokens_saved":1932,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":347,"response_debit":2136,"source_credit_count":2,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":10,"content_source_credit":9596,"derived_artifact_credit":803,"direct_net":-1054,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1273,"response_debit":13989,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":7,"content_source_credit":27026,"derived_artifact_credit":968,"direct_net":17667,"estimated_tokens_saved":17667,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1382,"response_debit":11261,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":20,"content_source_credit":40772,"derived_artifact_credit":2036,"direct_net":18545,"estimated_tokens_saved":19599,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3002,"response_debit":27386,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6125},"wave_id":"1z2m8 cross-platform-fixes"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
