# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-08-12
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1v4ms reranker-order-invariance`
Title: Reranker Order Invariance

## Objective

Make reranker output invariant to the order of its candidate pool, so the same question over the same candidates returns the same ranking. Measured today on a CPU-bound host: reordering a 60-candidate pool changed top-5 ordering in 3 of 5 queries and top-10 membership in 1 of 5, because pools larger than the 40-row batch split into two quantization regimes whose scores are then compared against each other.

## Changes

Change ID: `1v455-bug reranker-scores-depend-on-batch-composition`
Change Status: `planned`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer (remedy, consumer census), qa (measurement, GPU-path pin)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

## Wave Summary

One bug change: the reranker's INT8 export derives a per-tensor activation scale across the batch, so a candidate's score depends on which batch it lands in, and those scores are then compared across batch boundaries. The remedy is deliberately left open at plan time because the leading candidate trades recall for consistency and that trade is not yet measured.

## Watchpoints

- **Watchpoint:** the remedy is NOT pre-decided. Capping the pool at `RERANK_STATIC_BATCH` is measured to restore order-invariance (5/5 identical at pool 40 and 35) and costs no extra inference calls, but it drops candidates 41+ from reranking. Do not implement it before the consumer census and the AC-6 measurement.
- **Watchpoint:** this is CPU-bound only. The FP16 reranker export carries zero quantization operators. The GPU path must be left alone and proven untouched (AC-4).
- **Watchpoint:** scores feed the relevance floor, drop-off cut, and confidence band, not just the sort. A remedy that fixes ordering can still change which candidates are returned, so AC-6 measures end to end rather than ordering alone.
- **Follow-up (deferred, do not expand this wave):** the standing alternative for this whole defect class is a calibrated static-quantization export. If it is ever taken it should cover the embedder and the reranker together, per ADR `1v22e`, not be bolted on here.
- Pre-existing defect, NOT a regression from wave `1v454`, which fixed the embedder and never touched the reranker path. It does not block shipping the embedder fix.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-12: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the entire change rests on pools actually exceeding `RERANK_STATIC_BATCH` in production, so if candidates were capped before reranking the defect would be unreachable and the plan pointless; verified against the tree rather than the plan, and the shipped comment above `_agent_rerank`'s call site states the cross-encoder scores "the full retrieved pool on ONE unified relevance scale ... BEFORE selection", which both confirms no pre-rerank cap and raises the severity, because the split does not merely shift scores, it silently violates a documented design invariant that those scores are mutually comparable; strongest-alternative: cap the pool at `RERANK_STATIC_BATCH`, measured to restore exact order-invariance at pool 40 and 35 and costing no extra inference calls, deliberately NOT adopted at plan time because it discards candidates 41 and beyond from reranking and that recall cost is unmeasured, which is the same measure-before-committing discipline the sibling wave had to apply retroactively)

Seat evidence:

- **red-team** — verified code-grounded. Confirmed the mechanism exists on this graph (26 `DynamicQuantizeLinear` operators in the reranker INT8 export, zero in its FP16 export, so the CPU-only blast radius holds). Confirmed `rerank` pads to `RERANK_STATIC_BATCH` only when the group is short, so composition varies with pool size. Confirmed the claim that would have killed the plan is false: `AGENT_CANDIDATE_MAX` is a post-rerank selection backstop, `_agent_rerank` forwards the full candidate list uncapped, and the call-site comment documents that intent explicitly. Confirmed the cross-batch comparison is real rather than theoretical: `_rerank` min-max normalizes over all scores and `_agent_rerank` sigmoids each logit into the floor, drop-off and confidence band. The plan's own evidence was checked for non-vacuity: the control at pool 40 and 35 returns 5/5 identical ordering, so the reported instability is attributable to the split rather than to reranker noise.
- **docs-contract-reviewer** — no finding, with one observation recorded rather than raised. `docs/specs/mcp-tool-surface.md` makes no determinism or stable-ordering promise about the rerank path, so no shipped documentation is currently false and nothing must change to stop a lie. The plan's Affected Architecture Docs section is correct that ADR `1v22e` already carries this exposure as confirmed with measurements and needs updating to resolved at close, and correct that no new ADR is warranted since the constraint is `1v22e`'s applied to a second graph. Observation for the implementer, not a blocker: if the remedy makes ordering guaranteed, the spec gains something worth stating that it does not say today.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | pending | no current executed approval | record approval evidence for code-reviewer |
| qa-reviewer | pending | no current executed approval | record approval evidence for qa-reviewer |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 23 | 911,376 |
| **Total** | **23** | **911,376** |

<!-- wave:context-efficiency-state {"generation":11,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":23,"content_source_credit":945504,"derived_artifact_credit":1675,"direct_net":911376,"estimated_tokens_saved":911376,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2354,"response_debit":36955,"source_credit_count":25,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":23,"content_source_credit":945504,"derived_artifact_credit":1675,"direct_net":911376,"estimated_tokens_saved":911376,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2354,"response_debit":36955,"source_credit_count":25,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"wave_id":"1v4ms reranker-order-invariance"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
