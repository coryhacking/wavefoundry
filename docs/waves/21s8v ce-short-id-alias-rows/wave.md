# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-26
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21s8v ce-short-id-alias-rows`
Title: CE Short-Id Alias Rows

## Objective

Reopening a wave by its short id stops splitting its context-efficiency telemetry onto a key that never publishes, and the existing short-id alias rows leave the pending census at the next reload or upgrade with their telemetry kept. Measure of success: on a copy of this repository's store, all 22 alias rows retire and no folder-id row does. Canonical rows are never retired and closed records are not rewritten.

## Changes

Change ID: `21s8u-bug ce-short-id-alias-pending-rows`
Change Status: `implemented`

## Participants

- Coordinator: implementer
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-26

## Wave Summary

Wave `21s8v` (CE Short-Id Alias Rows) delivered one change: Reopen by short id creates context-efficiency alias rows that never clear. Notable adjustments during implementation: Reopen by short id creates context-efficiency alias rows that never clear: Full suite: 12244 tests OK. Delivery finding 21S8V-DEL-UNREADABLE-ALIAS-VACUOUS (qa-reviewer, do_now): the AC-3 unreadable subtest stubbed no match, so the guard-removed mutant survived. Stub now keeps the real resolution and adds an unreadable sibling; the mutant now fails it. The unresolved-reopen test now starts with focus on another wave and asserts it is unchanged (code-reviewer note).

Intent outcome: 2026-10-26, drafted by the coordinator, confirmed by the qa-reviewer (its caveat on the unreadable-record guard is resolved by the repaired alias subtest). Established. A short-id reopen now focuses and unseals the wave's full folder id and creates no short-id row (unit test; the old wrapper line fails it). On a scratch copy of this repository's store and wave tree with `now` fixed at 2026-10-26T00:00Z, one reload-style pass retired exactly the 22 short-id alias rows with their telemetry kept, retired the four wave-21s1u orphans separately, retired no folder-name key, and left only `20np3` pending (27 to 1). The guards retire nothing on an unreadable record, a raised resolution or the automatic path, each with a positive control. The affected suites pass under the downstream Set/Wave profile. Not shown: a live reload on this repository, and alias telemetry still does not reach the canonical records (by design).

**Changes delivered:**

- **Reopen by short id creates context-efficiency alias rows that never clear** (`21s8u-bug ce-short-id-alias-pending-rows`) — 5 ACs completed. Key decisions: Fix the reopen wrapper to use the canonical folder id, and retire existing alias rows at the hard boundary with no idle wait, keeping telemetry. Efficacy: replaying today's data, all 22 alias rows retire at the next reload or upgrade and no new ones are created by reopen; it controls the outcome directly; it could wrongly retire a row only if a key that differs from its wave's folder name could still publish, which projection never does because it publishes under the folder name; success is AC-1 and AC-4
## Watchpoints

- Watchpoint: open `framework_edit_allowed` before the framework edit and close it after; refresh the handler-digest pin for the edited tool handler.
- Watchpoint: no ledger or doc writes while the full suite runs.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 21S8V-DEL-UNREADABLE-ALIAS-VACUOUS | do_now | no | completed | — |

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

Intent outcome: 2026-10-26, drafted by the coordinator, confirmed by the qa-reviewer (its caveat on the unreadable-record guard is resolved by the repaired alias subtest). Established. A short-id reopen now focuses and unseals the wave's full folder id and creates no short-id row (unit test; the old wrapper line fails it). On a scratch copy of this repository's store and wave tree with `now` fixed at 2026-10-26T00:00Z, one reload-style pass retired exactly the 22 short-id alias rows with their telemetry kept, retired the four wave-21s1u orphans separately, retired no folder-name key, and left only `20np3` pending (27 to 1). The guards retire nothing on an unreadable record, a raised resolution or the automatic path, each with a positive control. The affected suites pass under the downstream Set/Wave profile. Not shown: a live reload on this repository, and alias telemetry still does not reach the canonical records (by design).

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 10 | 4,958 |
| implement | 10 | 10,457 |
| review | 9 | 42,025 |
| **Total** | **29** | **57,440** |

<!-- wave:context-efficiency-state {"generation":29,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":10,"content_source_credit":9868,"derived_artifact_credit":0,"direct_net":10457,"estimated_tokens_saved":10457,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":151,"response_debit":1832,"source_credit_count":1,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2572},"plan":{"calls":10,"content_source_credit":14774,"derived_artifact_credit":2124,"direct_net":4958,"estimated_tokens_saved":4958,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1454,"response_debit":15539,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5053},"review":{"calls":9,"content_source_credit":60590,"derived_artifact_credit":1020,"direct_net":42025,"estimated_tokens_saved":42025,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3398,"response_debit":19876,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3689}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":29,"content_source_credit":85232,"derived_artifact_credit":3144,"direct_net":57440,"estimated_tokens_saved":57440,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5003,"response_debit":37247,"source_credit_count":23,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11314},"wave_id":"21s8v ce-short-id-alias-rows"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
