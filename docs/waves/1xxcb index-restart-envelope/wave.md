# Wave Record

Owner: Engineering
Status: paused
Last verified: 2026-09-13
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1xxcb index-restart-envelope`
Title: Index Restart Envelope

## Objective

Present a validated index-writer restart checkpoint as action_required instead of an outer upgrade error, including the ppjy installing hop through its newly loaded restart reader.

## Changes

Change ID: `1xxca-bug first-hop-index-restart-envelope`
Change Status: `in-progress`

## Participants

- Coordinator: implementer
- Write-owning roles: implementer (response compatibility and tests), technical-writer (upgrade guidance)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

## Wave Summary

Correct the expected restart envelope while preserving exact CLI continuation, genuine errors, real storage checkpoints, response bounds and host confirmation. No index data or producer revisions change.

## Watchpoints

- Watchpoint: already-cached older readers cannot acquire incoming behavior; retain the documented checkpoint and exact external CLI recovery.
- Source and tests match the reviewed fingerprint; full verification passes 8,984 tests (12 existing skips). No commit, package or closure authorized in this task.

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
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Delivery council — 2026-09-13: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: old wrapper overwrites action identity and recovery guidance; strongest-alternative: current-wrapper-only correction misses the installing hop). Isolated code, QA and docs lanes approved. Exact invocation capability, altered-action refusal and unchanged original bounder verified. No unresolved findings or disagreements. Evidence: `delivery-review.json`.

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 50 | 1,722,906 |
| implement | 43 | 799,425 |
| review | 70 | 2,257,748 |
| **Total** | **163** | **4,780,079** |

<!-- wave:context-efficiency-state {"generation":143,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":43,"content_source_credit":856113,"derived_artifact_credit":0,"direct_net":799425,"estimated_tokens_saved":799425,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1489,"response_debit":55659,"source_credit_count":13,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":460},"plan":{"calls":50,"content_source_credit":1784160,"derived_artifact_credit":1409,"direct_net":1722906,"estimated_tokens_saved":1722906,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2428,"response_debit":65931,"source_credit_count":37,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5696},"review":{"calls":70,"content_source_credit":2362865,"derived_artifact_credit":1994,"direct_net":2257748,"estimated_tokens_saved":2257748,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5080,"response_debit":102031,"source_credit_count":46,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":163,"content_source_credit":5003138,"derived_artifact_credit":3403,"direct_net":4780079,"estimated_tokens_saved":4780079,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8997,"response_debit":223621,"source_credit_count":96,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6156},"wave_id":"1xxcb index-restart-envelope"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 23 | 0 | 13 | 16,155,783 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":13,"estimated_exploration_avoided":16155783,"surfaced_events":23} -->
<!-- wave:exploration-avoided end -->
