# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-17
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1y0do tool-surface-snapshot`
Title: Tool Surface Snapshot

## Objective

When this wave closes, every registered MCP tool's name, roster tier, input schema, and annotations are pinned in a committed golden fixture checked by the ordinary test suite, and the post-registration wrapper order is proven by behavior. It lands first because the layout, gate, registry, and handler-split waves are all judged against it.

## Changes

Change ID: `1xzsl-enh tool-surface-golden-snapshot`
Change Status: `complete`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer (tests and fixture); implementer (contributing and architecture documentation), serialized around the shared test helper.
- Readiness allocation: coordinator reviews scope and ACs; independent wave-council runs the standard red-team primer and docs-contract seat. Current host model retained; no model switch requested or claimed.
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-09-17

## Wave Summary

Wave `1y0do` (Tool Surface Snapshot) delivered one change: Golden Snapshot Of The Public MCP Tool Surface.

**Changes delivered:**

- **Golden Snapshot Of The Public MCP Tool Surface** (`1xzsl-enh tool-surface-golden-snapshot`) — 6 ACs completed. Key decisions: Snapshot name, tier, input schema, and annotations; exclude descriptions; Committed JSON fixture compared by a test, not a snapshot library
## Watchpoints

- Watchpoint: must close before `1y0h1 tool-registry-dispatch` starts implementation, otherwise that wave is blocked; the registry change's AC-1 is defined against this fixture.
- Follow-up rule: any later wave that intentionally changes a tool schema must regenerate the fixture as a named, reviewed step in its own change doc.
- The fixture lands under the framework test tree, so it is inside the close-time receipt hash and outside the distribution pack.

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
| wave-council-delivery | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| credit_history_unavailable | 0 | 0 |

<!-- wave:context-efficiency-state {"generation":85,"measurement_status":"credit_history_unavailable","pending":false,"schema_version":1,"stages":{"implement":{"calls":106,"content_source_credit":115798565,"derived_artifact_credit":0,"direct_net":115709658,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3504,"response_debit":88376,"source_credit_count":21,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2973},"plan":{"calls":23,"content_source_credit":17589,"derived_artifact_credit":699,"direct_net":3953,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2398,"response_debit":16519,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4582},"review":{"calls":12,"content_source_credit":39588,"derived_artifact_credit":392,"direct_net":21572,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4302,"response_debit":16108,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2002}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":141,"content_source_credit":115855742,"derived_artifact_credit":1091,"direct_net":115735183,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10204,"response_debit":121003,"source_credit_count":39,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9557},"wave_id":"1y0do tool-surface-snapshot"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: index_health gained a setup_readiness response field from an intervening wave; strongest-alternative: none needed, confirmed correctly out of this change's input-schema-only scope).

- **Prepare-phase Wave Council [prepare-council] — 2026-09-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: implementation-only registration omits runner survivor schemas; strongest-alternative: real full-runner registration with a stub handler, now adopted). Re-reviewed amended scope; no unresolved operator questions. Evidence: [readiness review](readiness-review-2026-09-17.md).
- **Delivery-phase Wave Council [delivery-council] — 2026-09-17: PASS** (moderator: wave-council; primer-depth: lightweight; seats: red-team, code-reviewer, qa-reviewer; rotating-seat: none at lightweight depth, red-team's strongest-alternative role covered it; strongest-challenge: red-team attempted five evasions of the golden guard (additionalProperties, nested $defs, same-name re-registration with different annotations, tier mismatch, survivor annotations) and each is detected key-for-key; strongest-alternative: use FastMCP's public list_tools instead of the private tool table, judged not materially stronger since both resolve to the same dict and the private read is a documented risk; findings: one real qa finding, the AC-3 leak assertion failed under the documented regeneration command, repaired under the gate and reverified independently with a leak-polarity mutant; disagreements: none; mutants killed: six across the two lanes plus the reverifier's polarity mutant).
