# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-27
review-evidence-source: events.jsonl

wave-id: `1tomw events-only-review-evidence-authority`
Title: Events Only Review Evidence Authority

## Objective

Make each wave's `events.jsonl` the sole machine authority for executable review evidence, removing the global adoption receipt and completed self-host migration state. Preserve direct ledger validation, cross-process serialization, exact replay, released-version upgrade safety, and the human current-state projection without replacing the removed receipts with another hash scheme.

## Changes

Change ID: `1to8f-enh events-only-review-evidence-authority`
Change Status: `planned`

## Wave Summary

This wave removes `review-evidence-adoptions.json`, `review-evidence-migration.json`, their proof/migration code, and every live consumer that no longer has an independent purpose. Upgrade preserves prose-only pre-1.14 history and 1.14+ event ledgers byte-for-byte; the legacy-named physical lock path remains as a deliberate cross-version coordination ABI while its code symbols become review-event terminology.

## Watchpoints

- Watchpoint: the typed-inline review format never shipped; upgrade tests must prove the released boundary instead of preserving a fallback reader.
- Do not rename or delete `.wavefoundry/locks/review-evidence-adoptions.lock` in this wave: an old MCP process and upgraded process must continue to contend on one OS lock.
- Preserve atomic visibility and exact-replay guarantees without implying `fsync` or power-loss durability.
- The deletion census excludes only closed historical records and the documented stable lock-path literal; no dormant adoption or migration implementation may remain.

## Participants

- Coordinator: `wave-council`
- Adversarial primer: `red-team`
- Fixed readiness seats: `architecture-reviewer`, `security-reviewer`, `qa-reviewer`, `reality-checker`
- Rotating readiness seat: `docs-contract-reviewer`

## Review checkpoints

- Readiness adversarial primer — `red-team`, full depth: strongest challenge was that the draft treated all inline/adoption migration code as self-host-only even though `phase_review_status_projection` still called a general inline bridge; strongest alternative was a version-gated expand/contract bridge or an explicit upgrade-floor change. The plan resolved this with release evidence: the inline protocol never shipped, 1.14.0 introduced external ledgers, and required fixtures now prove byte-preserving pre-1.14 prose and 1.14+ ledger upgrades. The primer also found that physically renaming the global lock could split old/new writers; the plan now preserves the existing pathname as a coordination ABI and requires a real two-process race.

## Prepare Review Evidence

- `red-team`: full-depth primer completed. Strongest challenge: prove removing `externalize_adopted_inline_wave_locked` does not violate skipped-version upgrades. Strongest alternative: retain a temporary version-gated bridge or raise the upgrade floor. Primer questions covered the earliest external-ledger release, treatment of typed-inline state, all-writer lock quiescence, true subprocess concurrency, and the boundary between process-crash replay and power-loss durability. Findings RT-001 through RT-004 were incorporated into the plan before fixed-seat review.

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

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 2 | 1,071 |
| **Total** | **2** | **1,071** |

<!-- wave:context-efficiency-state {"generation":2,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":2,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":1071,"estimated_tokens_saved":1071,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":33,"response_debit":193,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1297}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":2,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":1071,"estimated_tokens_saved":1071,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":33,"response_debit":193,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1297},"wave_id":"1tomw events-only-review-evidence-authority"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
