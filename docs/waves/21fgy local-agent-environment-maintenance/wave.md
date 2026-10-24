# Wave Record

Owner: Engineering
Status: paused
Last verified: 2026-10-23
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21fgy local-agent-environment-maintenance`
Title: Local Agent Environment Maintenance

## Objective

Remove exactly the two obsolete project-local permission entries and preserve every other setting. A7/Morning is excluded at the operator’s instruction on2026-10-23 because Anthropic maintains it. No shipped framework behavior or tool access expansion.

## Changes

Change ID: `21fgs-ops local-agent-permissions-and-morning-portability`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: qa-reviewer, security-reviewer, docs-contract-reviewer
- Required review lanes: qa-reviewer, docs-contract-reviewer, security-reviewer

## Wave Summary

Resolve audit A6 as bounded local maintenance. A7 was removed by the operator on2026-10-23; its historical investigation is retained, and no upstream correction is claimed.

## Watchpoints

- Watchpoint: Preserve all114other allowlist entries and every other local setting.
- Watchpoint: A7 is outside this wave; do not mutate or remove the Anthropic-maintained Morning skill or its synced cache.

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
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 63 | 30,092 |
| implement | 14 | 0 |
| review | 27 | 700,821 |
| **Total** | **104** | **730,913** |

<!-- wave:context-efficiency-state {"generation":92,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":14,"content_source_credit":1029,"derived_artifact_credit":0,"direct_net":-3041,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":488,"response_debit":6556,"source_credit_count":3,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2974},"plan":{"calls":63,"content_source_credit":161856,"derived_artifact_credit":2482,"direct_net":30092,"estimated_tokens_saved":30092,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":15562,"response_debit":126222,"source_credit_count":42,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7538},"review":{"calls":27,"content_source_credit":770726,"derived_artifact_credit":0,"direct_net":700821,"estimated_tokens_saved":700821,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":743,"response_debit":69162,"source_credit_count":11,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":104,"content_source_credit":933611,"derived_artifact_credit":2482,"direct_net":727872,"estimated_tokens_saved":730913,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16793,"response_debit":201940,"source_credit_count":56,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10512},"wave_id":"21fgy local-agent-environment-maintenance"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

Readiness: isolated adversarial primer, fixed architecture/security/QA/reality seats and rotating docs-contract alternative completed, with all fixed seats weighing alternatives. All required lane and council-readiness approvals recorded; no blocking design finding. Code/architecture shared one independent context, disclosed. Existing exact scanner exclusions and conservative missing-only skill metadata favored over parser/YAML-merge expansion. Modernization remains context-only and requires actual plugin observation. Morning maintained-source adoption remains an unmet prerequisite, not waived by a staged patch or browser capability check. Current scanner owner is `_audit_harness_coherence`; one historical readiness narrative mistakenly called it `_audit_seed_text_coherence`, while its inspected range and public audit observation were correct. No immutable evidence was rewritten.

Implementation checkpoint: A6 exact two-entry local permission cleanup independently verified; all 114 other allow entries and all other settings preserved. Bounded synthetic Chrome render inspected; full docs validation passed. A7 maintained Morning source is still unavailable; AC-2/T-2 remain unchecked and full-wave approval is not claimed. Pause pending that source while repository-wave final qualification continues.

Current scope checkpoint (2026-10-23): Operator removed A7 because Morning belongs to Anthropic. A6 is the only remaining implementation scope and is already independently verified. Earlier Morning prerequisites above describe the previous scope; they no longer block delivery. Required review authority must reflect the narrowed scope before closure.
