# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-09-04
review-evidence-source: events.jsonl

review-policy-reprepare-required: false

wave-id: `1x4ol index-build-cost-and-scanner-bounds`
Title: Index Build Cost And Scanner Bounds

## Objective

Make a graph rebuild cost what the graph costs. Today the command takes about 203 seconds, of which 198.5 are a full secrets re-scan the graph rebuild has no reason to trigger, and 173.6 of those come from one file meeting a regex that is linear upstream and quadratic here. This wave scopes the flag and bounds the scanner, so the cost is both removed from the common path and capped on the rare one.

## Changes

Change ID: `1x4oj-bug graph-rebuild-forces-full-secrets-scan`
Change Status: `planned`

Change ID: `1x4ok-enh secrets-scan-cost-bounds`
Change Status: `planned`

## Participants

- Coordinator: coordinator
- Write-owning roles: implementer
- Requested review lanes: performance-reviewer, code-reviewer, qa-reviewer, security-reviewer
- Required review lanes: none
- Product-owner admission review: operator-approved on 2026-09-04 by the instruction to plan the optimization wave after the measured diagnosis was presented.

## Wave Summary

Two changes against one measured problem. `1x4oj` stops a graph-only rebuild from forcing a full secrets scan, which removes about 198.5 seconds from the command an operator actually waits on. `1x4ok` bounds the time any single file may cost the scanner and fixes the pattern shape behind the outlier, so the rare genuine full scan cannot stall without a ceiling or a diagnostic. The first is the saving; the second is what keeps the saving from being reintroduced by the next ruleset refresh.

## Watchpoints

- **This is a security scanner. A performance change here must not cost detection.** Every pattern edit is judged against true-positive and false-positive fixtures frozen BEFORE the edit, never against the edited pattern's own output. The repository's findings ledger holds zero entries, so parity judged on live findings would pass vacuously.
- **A skipped file must never read as a clean one.** The time bound in `1x4ok` reports every skip by path through the existing scan-skip channel and must not populate the per-file cache, or a one-time timeout becomes permanent silent non-coverage.
- **Do not narrow the scan set to buy speed.** Excluding the expensive evidence artifacts would make the numbers look right by scanning less of the committed tree. Both changes keep the same files eligible.
- **`1x4oj` before `1x4ok`.** The scoping fix removes the cost from the common path in one line; the scanner work is then measured against the rare full scan rather than against a number the flag fix was going to erase anyway.
- Both changes touch the secrets path, so they share one production write owner and land in the order above.

### Measured but not admitted

Two further costs were measured during diagnosis and are deliberately left out, recorded here so a later wave does not re-derive them.

- **Graph extraction worker sizing.** 335 code files fall in the `< 500` tier, which caps at 3 workers on a machine with 8 performance cores. Only about 18 seconds of the 46.6 second graph phase is parallelisable, because the incremental merge is 25.3 of it, so the ceiling on this is modest.
- **The incremental merge.** 25.3 seconds for 719 files, 127,225 symbols and 93,415 re-resolved edges is the single largest graph-side cost and the more promising target of the two. It has not been profiled, so it is named rather than scoped.

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
| wave-council-readiness | pending | no current executed approval | record approval evidence for wave-council-readiness |
| wave-council-delivery | pending | no current executed approval | record approval evidence for wave-council-delivery |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Follows closed wave `1wpih index-quality-evaluation-and-ranking`, which did not cause this cost but made it frequent: it bumped the graph builder twice, and every bump forces a full graph rebuild that drags a full secrets scan behind it.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 5 | 2,839 |
| review | 3 | 1,136 |
| **Total** | **8** | **3,975** |

<!-- wave:context-efficiency-state {"generation":7,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":5,"content_source_credit":0,"derived_artifact_credit":2294,"direct_net":2839,"estimated_tokens_saved":2839,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":68,"response_debit":703,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1316},"review":{"calls":3,"content_source_credit":3271,"derived_artifact_credit":0,"direct_net":1136,"estimated_tokens_saved":1136,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12,"response_debit":2123,"source_credit_count":2,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":8,"content_source_credit":3271,"derived_artifact_credit":2294,"direct_net":3975,"estimated_tokens_saved":3975,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":80,"response_debit":2826,"source_credit_count":2,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1316},"wave_id":"1x4ol index-build-cost-and-scanner-bounds"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
