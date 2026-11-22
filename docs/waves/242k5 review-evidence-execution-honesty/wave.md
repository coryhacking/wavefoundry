# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-22
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `242k5 review-evidence-execution-honesty`
Title: Review Evidence Execution Honesty

## Objective

A reviewer who verified a claim by reading, without running anything, can record that honestly in the review ledger, so the ledger never says a check was executed when it was not and readers can tell executed evidence from read-only evidence.

## Changes

Change ID: `242k4-bug review-event-execution-status-honesty`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator (main session)
- Write-owning roles: implementer
- Requested review lanes: security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-11-22

## Wave Summary

Wave `242k5` (Review Evidence Execution Honesty) delivered one change: Review Event Execution Status Honesty.

**Changes delivered:**

- **Review Event Execution Status Honesty** (`242k4-bug review-event-execution-status-honesty`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8 and AC-9 completed. Key decisions: Operator decision 2026-11-22, narrowing the fix. `evidence.execution_status` is an optional, documented input whose default stays `executed`. The tool stores the stated status. No gate changes: non-executed evidence can open and record a finding, and it clears no lane, completes no repair, satisfies no approval and completes no checkpoint. This supersedes the two earlier decisions of the same date in the next two rows; Superseded by the first row. An omitted status on a new finding was to be refused.

## Watchpoints

- Watchpoint: wave 241lp is open in another session with uncommitted framework edits; do not touch its files.
- Watchpoint: this wave shares `review_evidence.py`, `wf_server/server_impl.py`, `tests/test_review_evidence.py`, `tests/fixtures/register-surface-handler-digests.json`, `docs/specs/mcp-tool-surface.md`, `CHANGELOG.md` and `test_small_change_lifecycle.py` with 241lp. Ready it now, but do not implement until 241lp is closed and committed.
- Watchpoint: this changes the review-evidence contract; closed records and their ledgers must stay valid and must never be recomputed or rewritten.
- Watchpoint: open `framework_edit_allowed` around framework edits and close it after.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| D-242k4-recheck-and-depth-release | dont_do_later | no | not_required | — |
| R1-242k4-checkpoint-completion | do_now | no | completed | — |
| R1-242k4-old-ledger-replay | do_now | no | completed | — |
| R1-242k4-outcome-rule-completed-trigger | do_now | no | completed | — |
| R1-242k4-readiness-relabel-bypass | do_now | no | completed | — |
| R1-242k4-relabel-open-wave | do_now | no | completed | — |
| R1-242k4-repair-start-status | do_now | no | completed | — |
| R1-242k4-status-meaning-boundary | do_now | no | completed | — |
| R1-242k4-upgrade-guardrail-not-rendered | do_now | no | completed | — |

*Machine review state — 9 findings; current: do_now 8, maybe_later 0, dont_do_later 1, not_issue 0*
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
| docs-contract-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking); known-bad control not applicable: Docs-contract readiness review of spec text against the current builder source. Inspected scope: Requirements 5, AC-5, AC-9, Decision Log. No code or seed edited by the change is affected yet, so no known-bad control was run. | none |
| docs-contract-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| security-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
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
| plan | 75 | 886,440 |
| implement | 43 | 0 |
| review | 79 | 319,342 |
| **Total** | **197** | **1,205,782** |

<!-- wave:context-efficiency-state {"generation":197,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":43,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-428,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1350,"response_debit":9429,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10351},"plan":{"calls":75,"content_source_credit":1236550,"derived_artifact_credit":2045,"direct_net":886440,"estimated_tokens_saved":886440,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":48690,"response_debit":314091,"source_credit_count":70,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10626},"review":{"calls":79,"content_source_credit":417302,"derived_artifact_credit":79846,"direct_net":319342,"estimated_tokens_saved":319342,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11284,"response_debit":173300,"source_credit_count":17,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6778}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":197,"content_source_credit":1653852,"derived_artifact_credit":81891,"direct_net":1205354,"estimated_tokens_saved":1205782,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":61324,"response_debit":496820,"source_credit_count":87,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":27755},"wave_id":"242k5 review-evidence-execution-honesty"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
