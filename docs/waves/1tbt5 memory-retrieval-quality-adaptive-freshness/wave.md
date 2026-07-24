# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-23
review-evidence-source: events.jsonl

wave-id: `1tbt5 memory-retrieval-quality-adaptive-freshness`
Title: Memory Retrieval Quality Adaptive Freshness

## Objective

Improve memory retrieval with measured, kind-aware freshness while preserving
trust, status, evidence, and archive boundaries. Reconsider lexical+semantic
fusion only through the expanded evaluation gate, leaving it default-off unless
the evidence supports adoption.

## Changes

Change ID: `1t7ab-enh adaptive-memory-freshness-and-retrieval`
Change Status: `planned`

Change ID: `1sufn-enh measured-lexical-semantic-memory-fusion`
Change Status: `planned`

## Wave Summary

This wave expands the memory retrieval evaluation corpus, implements adaptive
freshness and re-verification pressure for comparable tactical records, and
evaluates the previously deferred relevance-fusion design. It consumes the
completed archival contract without changing archival storage or retention.

## Watchpoints

- **Watchpoint:** Keep relevance scoring separate from policy constraints; recency must not
  demote durable decisions or operator preferences.
- **Watchpoint:** Evaluate and pin archive-pointer, archive-history, degraded-index, target
  churn, and old-authoritative cases before changing default ranking behavior.
- **Watchpoint:** Treat `1sufn` as adoption-gated: a measured default-off result is acceptable
  when fusion does not improve the representative corpus.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review evidence — 0 records; 0 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | pending | no current executed approval | record approval evidence for wave-council-readiness |
| wave-council-delivery | pending | no current executed approval | record approval evidence for wave-council-delivery |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Consumes the archive and pointer contract completed by wave
  `1t8la memory-archival-and-retention`; that closed wave is not reopened.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 12 | 3,627 |
| **Total** | **12** | **3,627** |

<!-- wave:context-efficiency-state {"generation":12,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":12,"content_source_credit":10172,"derived_artifact_credit":289,"direct_net":3627,"estimated_tokens_saved":3627,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":527,"response_debit":7424,"source_credit_count":6,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1117}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":12,"content_source_credit":10172,"derived_artifact_credit":289,"direct_net":3627,"estimated_tokens_saved":3627,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":527,"response_debit":7424,"source_credit_count":6,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1117},"wave_id":"1tbt5 memory-retrieval-quality-adaptive-freshness"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
