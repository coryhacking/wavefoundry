# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-09-14
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1y0do tool-surface-snapshot`
Title: Tool Surface Snapshot

## Objective

When this wave closes, every registered MCP tool's name, roster tier, input schema, and annotations are pinned in a committed golden fixture checked by the ordinary test suite, and the post-registration wrapper order is proven by behavior. It lands first because the layout, gate, registry, and handler-split waves are all judged against it.

## Changes

Change ID: `1xzsl-enh tool-surface-golden-snapshot`
Change Status: `planned`

## Participants

- Coordinator: Engineering
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

## Wave Summary

Test-only wave adding the missing slice-0 guard from the modularity RFC: a deterministic golden snapshot of the public tool surface with explicit regeneration, a bidirectional runtime roster parity check, and a behavioral wrapper-order test. No production code changes.

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
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | pending | no current executed approval | record approval evidence for wave-council-delivery |
| code-reviewer | pending | no current executed approval | record approval evidence for code-reviewer |
| qa-reviewer | pending | no current executed approval | record approval evidence for qa-reviewer |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 282 | 6,336,672 |
| review | 1 | 0 |
| **Total** | **283** | **6,336,672** |

<!-- wave:context-efficiency-state {"generation":12,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":282,"content_source_credit":6884298,"derived_artifact_credit":11739,"direct_net":6336672,"estimated_tokens_saved":6336672,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9278,"response_debit":561172,"source_credit_count":226,"source_credit_drop_count":0,"structural_source_credit":7478,"workflow_prompt_credit":3607},"review":{"calls":1,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-897,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10,"response_debit":887,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"33652402c1924592b478c511b0100138","totals":{"calls":283,"content_source_credit":6884298,"derived_artifact_credit":11739,"direct_net":6335775,"estimated_tokens_saved":6336672,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9288,"response_debit":562059,"source_credit_count":226,"source_credit_drop_count":0,"structural_source_credit":7478,"workflow_prompt_credit":3607},"wave_id":"1y0do tool-surface-snapshot"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->

## Review checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: index_health gained a setup_readiness response field from an intervening wave; strongest-alternative: none needed, confirmed correctly out of this change's input-schema-only scope).
