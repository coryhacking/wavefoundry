# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-11
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1v08w code-ask-known-symbol-definition-first`
Title: Code Ask Known Symbol Definition First

## Objective

Make `code_ask` place a structurally confirmed exact declaration ahead of generic symbol usages while preserving the existing hybrid retrieval contract and direct-tool guidance.

## Changes

Change ID: `1v08v-bug code-ask-known-symbol-definition-first`
Change Status: `implementing`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-08-11

## Wave Summary

Wave `1v08w` (Code Ask Known Symbol Definition First) delivered one change: `code_ask` Known-Symbol Definition-First Routing. Notable adjustments during implementation: `code_ask` Known-Symbol Definition-First Routing: Scope correction after delivery review: AC-1 is language-neutral wherever the published graph supplies a declaration-capable node, not limited to Python and JavaScript. Reopened the affected status, ACs, and implementation/test tasks while the summary-collision, citation-range, declaration-kind, source-binding, and expanded language-matrix repairs remain outstanding.; `code_ask` Known-Symbol Definition-First Routing: Implemented the language-neutral repair: one read-only SQLite statement binds the exact opened payload to its source hash, one source buffer supplies verification and citation text, declaration kinds gate authority, same-line summaries are replaced by the verified candidate, and inclusive ranges are correct. Expanded public and graph-owner regressions cover the language, receipt/race, fallback, collision, and no-extra-inference boundaries.

**Changes delivered:**

- **`code_ask` Known-Symbol Definition-First Routing** (`1v08v-bug code-ask-known-symbol-definition-first`) — 5 ACs completed. Key decisions: Select structurally confirmed definition-first preference with ordinary hybrid fallback.; Keep the change separate from supplier-lineage wave `1v0r0`.
## Watchpoints

- Watchpoint: read only the already-published graph payload and its payload-bound SQLite state receipt; do not construct a mutable graph state store or use accessors/public resolvers that can rebuild, refresh, invalidate, or full-scan.
- Watchpoint: a finite score bonus is insufficient; the exact declaration must be deterministically pinned after final selection while broader context remains available.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-11: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: graph accessors can auto-rebuild and a finite bonus cannot guarantee definition-first ordering; strongest-alternative: read the published graph payload, require one exact node, reuse the existing bounded candidate helper, and stable-pin it after final selection)

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 1v08w-code-summary-collision | do_now | no | completed | code-reviewer, qa-reviewer |
| 1v08w-doc-contract-current-tree-mismatch | do_now | no | completed | docs-contract-reviewer |
| 1v08w-fallback-response-shape-self-reference | do_now | no | completed | qa-reviewer |
| 1v08w-graph-declaration-authority-unproven | do_now | no | completed | architecture-reviewer, code-reviewer, qa-reviewer |
| 1v08w-graph-range-off-by-one | do_now | no | completed | code-reviewer, qa-reviewer |

*Machine review state — 5 findings; current: do_now 5, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 34 | 0 |
| implement | 116 | 2,837,274 |
| review | 536 | 15,059,698 |
| **Total** | **686** | **17,896,972** |

<!-- wave:context-efficiency-state {"generation":698,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":116,"content_source_credit":2981160,"derived_artifact_credit":0,"direct_net":2837274,"estimated_tokens_saved":2837274,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5273,"response_debit":143400,"source_credit_count":43,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4787},"plan":{"calls":34,"content_source_credit":30915,"derived_artifact_credit":1474,"direct_net":-8568,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5940,"response_debit":40713,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5696},"review":{"calls":536,"content_source_credit":16732043,"derived_artifact_credit":2081,"direct_net":15059698,"estimated_tokens_saved":15059698,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":34595,"response_debit":1641177,"source_credit_count":410,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":686,"content_source_credit":19744118,"derived_artifact_credit":3555,"direct_net":17888404,"estimated_tokens_saved":17896972,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":45808,"response_debit":1825290,"source_credit_count":471,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11829},"wave_id":"1v08w code-ask-known-symbol-definition-first"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 19 | 0 | 2 | 8,506,964 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":8506964,"surfaced_events":19} -->
<!-- wave:exploration-avoided end -->
