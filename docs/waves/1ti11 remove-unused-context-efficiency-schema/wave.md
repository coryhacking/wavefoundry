# Wave Record

Owner: Engineering
Status: paused
Last verified: 2026-07-25
review-evidence-source: events.jsonl

wave-id: `1ti11 remove-unused-context-efficiency-schema`
Title: Remove Unused Context Efficiency Schema

## Objective

Stop shipping the unused Context Efficiency pair JSON Schema while preserving
the scorer-backed paired-evaluation workflow and a clean upgrade path for
projects that received the file from an earlier pack.

## Changes

Change ID: `1th3p-maint remove-unused-context-efficiency-schema`
Change Status: `implemented`

## Wave Summary

Delete the redundant schema, pin its absence from future distributions, verify
old MANIFEST-driven upgrades prune it, and document the compatibility change.
Paired-evaluation scoring and accounting remain unchanged.

## Watchpoints

- Watchpoint: preserve `score_context_efficiency_pairs.py` and scorer-derived scaffold
  behavior as the only executable contract.
- Watchpoint: exercise an old-pack-to-new-pack pruning fixture; a fresh-pack absence check
  alone does not prove existing target projects are cleaned.
- Watchpoint: keep closed wave history intact and leave the CHANGELOG unchanged
  per operator direction.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review evidence — 2 records; 1 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare seat evidence — red-team — 2026-07-25:** challenged the compatibility impact of removing an intentionally shipped file despite the zero-runtime-consumer census; the operator later narrowed the response to artifact and regression cleanup with no CHANGELOG entry.
- **Prepare seat evidence — docs-contract-reviewer — 2026-07-25:** no further findings after confirming closed wave history remains untouched and AC-5 records the operator-directed CHANGELOG exclusion.
- **Prepare-phase Wave Council [prepare-council] — 2026-07-25: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: removing an intentionally shipped file could break an undisclosed out-of-tree harness even though no project tool consumes it; operator direction confines the response to artifact and regression cleanup with no CHANGELOG entry; strongest-alternative: retain and generate the schema from scorer constants as a documented public integration contract, rejected because no current tool or reference exposes that contract and the operator chose removal)

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
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
| plan | 6 | 0 |
| implement | 23 | 569,903 |
| review | 1 | 0 |
| paused | 1 | 0 |
| **Total** | **31** | **569,903** |

<!-- wave:context-efficiency-state {"generation":31,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":23,"content_source_credit":597613,"derived_artifact_credit":0,"direct_net":569903,"estimated_tokens_saved":569903,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":582,"response_debit":28701,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1573},"paused":{"calls":1,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-151,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10,"response_debit":141,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":6,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-214,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":68,"response_debit":3337,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3191},"review":{"calls":1,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-131,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10,"response_debit":121,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":31,"content_source_credit":597613,"derived_artifact_credit":0,"direct_net":569407,"estimated_tokens_saved":569903,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":670,"response_debit":32300,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4764},"wave_id":"1ti11 remove-unused-context-efficiency-schema"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
