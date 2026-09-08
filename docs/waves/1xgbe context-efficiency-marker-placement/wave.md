# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-08
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1xgbe context-efficiency-marker-placement`
Title: Context Efficiency Marker Placement

## Objective

Place Context Efficiency ownership markers below their section headings consistently, while preserving existing checkpoint data and backward compatibility.

## Changes

Change ID: `1xgbd-bug context-efficiency-marker-after-heading`
Change Status: `implemented`

## Participants

- Coordinator: wave coordinator
- Write-owning roles: implementer (coordinator)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-09-08

## Wave Summary

Wave `1xgbe` (Context Efficiency Marker Placement) delivered one change: Context Efficiency Marker Placement.

**Changes delivered:**

- **Context Efficiency Marker Placement** (`1xgbd-bug context-efficiency-marker-after-heading`) — 3 ACs completed. Key decisions: Change renderer, accept the old layout, and normalize existing wave formatting.
## Watchpoints

- Watchpoint: preserve all prior uncommitted changes; operator now requests review and closure, no commit.
- Product-owner acknowledgment: operator requested this layout consistency fix.
- Exact old-prefix normalization only; preserve state bytes, surrounding prose and marker names.

## Review checkpoints

Delivery review PASS (2026-09-08): fresh independent code-reviewer and QA contexts approved with no actionable findings. Code ran seven checkpoint tests; QA ran all55module tests, each without skips. Code executed five targeted mutants; QA four. All were caught by assertions with no errors/skips or survivors. Current full-suite receipt proves8,560tests across75files, three skips. No delivery council selected by the current receipt.

| Mutation | Detecting CheckpointTests test | Reviewers |
| --- | --- | --- |
| Restore old marker-first renderer | test_checkpoint_heading_precedes_marker_with_legacy_compatibility | Code, QA |
| Skip old-layout normalization | test_checkpoint_heading_precedes_marker_with_legacy_compatibility | Code, QA |
| Remove line-start guard | test_checkpoint_replacement_preserves_nonheading_prefix | Code, QA |
| Remove exact-heading comparison | test_checkpoint_replacement_preserves_nonheading_prefix | Code, QA |
| Omit consuming exact external heading | test_checkpoint_heading_precedes_marker_with_legacy_compatibility | Code |

Independent migration evidence:115trackedwavefiles equal HEAD after only the specified prefix move; code also compared116state-commentlines byte-for-byte. QA compared historical/current renderings across118realstates and verified old-output parse equality and current replacement idempotence. All118listedsections use new order. Three untracked wave records (1xfbh,1xgbc,1xgbe) lack independent pre-migration snapshots; their raw-state preservation is the coordinator's write-time before/after assertion, not independently reproduced. No browser, registered MCP upgrade run or exhaustive malformed-input census claimed. Source c2c2adc82eb45cb03dc67e8095aa0a58bb2f27ed and tests a3320cd608822f0168913f81095108f43c3f9f43 remained frozen. Reports and integrity fields are recorded here and in events.jsonl, with no separate Markdown reports.


Closure preparation: all three ACs and tasks complete; current8,560-test framework receipt verified by close dry-run. Docs-contract review not applicable: no specs or seed contracts changed. Memory proposal returned no candidates. Retrospective: moving a generated heading changes replacement boundaries and exact-render validation together; the compatibility and prose-preservation tests now encode that lesson, so no duplicate memory was created. No open questions or deferrals. Destination upgrades retain valid old closed checkpoints rather than bulk-rewriting them; this repository's118-record normalization was explicit formatting-only work.


Code/QA readiness also approved in the architecture reviewer’s paired readiness context: five CheckpointTests passed, old-prefix negative control confirms the defect, and simulated118-file normalization preserved raw state with reversible/idempotent text edits. These are readiness approvals, not delivery review. Implementation now has55passing module tests and four mutation controls, and full-suite verification complete:8,560tests across75files pass, three skips.


Prepare readiness council PASS: standard red-team primer and rotating architecture seat. Exact old-prefix compatibility and exact adjacent-heading replacement are required to avoid old-checkpoint rejection, duplicate headings or consumed prose. Existing nonempty checkpoint probe accepted7calls99saved, rejected altered visible count for canonical/legacy namespaces, and preserved before/after prose over repeat replacement. New layout and migration byte equality remain implementation checks. No source edits before readiness; no delivery approval claimed.

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
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

## Context Efficiency

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 36 | 698,471 |
| implement | 29 | 525,385 |
| review | 17 | 47,008 |
| **Total** | **82** | **1,270,864** |

<!-- wave:context-efficiency-state {"generation":70,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":29,"content_source_credit":545474,"derived_artifact_credit":0,"direct_net":525385,"estimated_tokens_saved":525385,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1212,"response_debit":20986,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2109},"plan":{"calls":36,"content_source_credit":736683,"derived_artifact_credit":1868,"direct_net":698471,"estimated_tokens_saved":698471,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3325,"response_debit":40261,"source_credit_count":23,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"review":{"calls":17,"content_source_credit":75084,"derived_artifact_credit":500,"direct_net":47008,"estimated_tokens_saved":47008,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3094,"response_debit":27371,"source_credit_count":11,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":82,"content_source_credit":1357241,"derived_artifact_credit":2368,"direct_net":1270864,"estimated_tokens_saved":1270864,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7631,"response_debit":88618,"source_credit_count":42,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7504},"wave_id":"1xgbe context-efficiency-marker-placement"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
