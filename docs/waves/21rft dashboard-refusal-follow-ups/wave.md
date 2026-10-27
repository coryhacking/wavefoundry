# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-27
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21rft dashboard-refusal-follow-ups`
Title: Dashboard Refusal Follow Ups

## Objective

Operators reading the dashboard while the index is refused or mid-publication see one consistent explanation and recovery action on the metric card, the Graph view and the Index dialog. Dashboard presentation and its own diagnostic mapping only; MCP responses are unchanged.

## Changes

Change ID: `21rf7-bug dashboard-refusal-follow-ups`
Change Status: `implemented`

## Participants

- Coordinator: main session
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-27

## Wave Summary

Wave `21rft` (Dashboard Refusal Follow Ups) delivered one change: Dashboard refusal follow-ups. Notable adjustments during implementation: Dashboard refusal follow-ups: Implemented. `index_compatibility.INDEX_COMPATIBILITY_CODES`, imported lazily in `dashboard_lib._store_read_diagnostic` and `graph_snapshot._read_failure`. `dashboard.js`: an explicitly declared JS set, `indexDiagnosticView` (label, action, tooltip) shared by `MissingIndexSection`, the Index tile and `graphSubtitle`, and a module-level `graphPayloadSignature` that keys not-present payloads by diagnostic code. Implementation decision (carried readiness note): on the tile the refusal wins over counts and over a running build's status text; the running state class is kept. The tile value reads `Unreadable`; the files/chunks subnote is replaced by the action. Two 1p2q3/index-tile source-string assertions were updated for the moved text. The lexical render slice stayed valid because the tile only calls the helper when a diagnostic exists. Tests: owning files `test_dashboard_server`, `test_graph_snapshot_readers`, `test_index_compatibility`, `test_dashboard_terminology` and `test_sqlite_serving` ran 371 tests, OK; the one skip is the opt-in Chrome viewport test. Known-bad: six mutants in a scratch framework copy each fail the new tests (tile refusal removed, signature reverted, tooltip unsuppressed, in-flight label removed, subtitle reverted, fourth Python code). Real browser: a headless Chrome screenshot of a scratch repo with a stale runtime and a sidecar count of 42 shows the tile `Unreadable` plus the restart action (no 42, no Missing), and the Graph subtitle names the refusal. The in-flight state is covered by render tests only. Follow-ups (not this scope): MCP `index_health()` restart wording for all three compatibility codes; migration-pending semantic store reads as not built.; Dashboard refusal follow-ups: Readiness repair after the red-team primer. The red-team confirmed three findings, each re-read in code: the sidecar `files_indexed` hides "Missing" (`_index_stats`), `_graphSignature` collapses not-present payloads, and `MigrationRequired` is unreachable on the semantic read path (`open_read_only` never calls `require_ready`). R1/AC-1 now require the diagnostic to take precedence over counts. R2/AC-2 and T-2 add the signature fix. The migration item (old R5/AC-4) was deleted and recorded as an out-of-scope follow-up. A new R5/AC-4 adds one shared JS helper, per the red-team's best alternative.

**Changes delivered:**

- **Dashboard refusal follow-ups** (`21rf7-bug dashboard-refusal-follow-ups`) — 6 ACs completed. Key decisions: Fix each surface to read the diagnostic it already receives (metric tile, Graph subtitle, dialog). Keep the global notice `index_runtime_stale`-only.; For M2, keep the dashboard's `index_health()` action and suppress the restart-bearing tooltip for `index_version_newer`/`index_compatibility_unproven`; do not edit `graph_snapshot`'s message.
## Watchpoints

- Watchpoint: framework edits need `framework_edit_allowed`; close it after edits.
- Watchpoint: run the canonical suite last; any framework edit after it rotates the receipt.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| CODE-DEL-1 | do_now | no | completed | code-reviewer |
| QA-DEL-1 | do_now | no | completed | qa-reviewer |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
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
| plan | 47 | 3,585,440 |
| implement | 25 | 0 |
| review | 26 | 84,256 |
| **Total** | **98** | **3,669,696** |

<!-- wave:context-efficiency-state {"generation":86,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":25,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-1934,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":662,"response_debit":5322,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4050},"plan":{"calls":47,"content_source_credit":3651374,"derived_artifact_credit":2280,"direct_net":3585440,"estimated_tokens_saved":3585440,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4554,"response_debit":68713,"source_credit_count":81,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5053},"review":{"calls":26,"content_source_credit":149756,"derived_artifact_credit":1804,"direct_net":84256,"estimated_tokens_saved":84256,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12656,"response_debit":58337,"source_credit_count":26,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3689}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":98,"content_source_credit":3801130,"derived_artifact_credit":4084,"direct_net":3667762,"estimated_tokens_saved":3669696,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17872,"response_debit":132372,"source_credit_count":107,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12792},"wave_id":"21rft dashboard-refusal-follow-ups"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
