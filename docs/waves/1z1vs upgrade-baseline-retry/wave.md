# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-25
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1z1vs upgrade-baseline-retry`
Title: Upgrade Baseline Retry

## Objective

<Describe the wave's load-bearing goal in 1–3 sentences — what changes in the project state when this wave closes, and why now. This text is displayed in the dashboard wave card.>

## Changes

Change ID: `1z1vr-bug upgrade-baseline-skipped-during-reindex`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, release-reviewer

Completed At: 2026-09-25

## Wave Summary

Wave `1z1vs` (Upgrade Baseline Retry) delivered one change: Retry the Setup Baseline When Cleanup Races the Reindex. Notable adjustments during implementation: Retry the Setup Baseline When Cleanup Races the Reindex: Implemented. `_record_setup_baseline` retries `assess_setup` while the result is `indeterminate` with at least one reason and every reason in `_TRANSIENT_SETUP_REASONS` (`inputs_changed`, `probe_timeout`), waiting 2, 5 and 10 s; `identity` is captured once before the loop; `time.sleep` resolves at call time (module imports unchanged). Tests in `PhaseCleanupSetupBaselineTests`: transient then ready records the baseline after waits [2, 5]; persistently transient stops after 4 attempts with the existing message; unproven, mixed, empty-reasons and `action_required` results are not retried. `test_upgrade_wavefoundry.py` 542 OK. Mutants killed by assertions: the non-empty-reasons guard dropped, the loop removed, the transient-code check removed. CHANGELOG `[Unreleased]` Fixed bullet added.

**Changes delivered:**

- **Retry the Setup Baseline When Cleanup Races the Reindex** (`1z1vr-bug upgrade-baseline-skipped-during-reindex`) — 3 ACs completed. Key decisions: Retry only on transient reasons, bounded at 4 attempts
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
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| accounting_gap | 0 | 0 |

<!-- wave:context-efficiency-state {"generation":0,"measurement_status":"accounting_gap","pending":false,"schema_version":1,"stages":{},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":0,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":0,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":0,"response_debit":0,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"wave_id":"1z1vs upgrade-baseline-retry"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
