# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-16
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1vgep agent-role-canonicalization-audit`
Title: Agent Role Canonicalization Audit

## Objective

Ship a shared, read-only agent-surface integrity audit that detects duplicate framework specialist role documents in upgraded target repositories (a canonical carrier created beside a repo-grown copy) and reports the canonical destination and merge-before-retire remediation through `wf_audit` and the upgrade operator summary, without deleting, moving, or rewriting any project-owned document. Two independent target-repository audits found this drift live; nothing detected it.

## Changes

Change ID: `1vflu-bug agent-role-canonicalization-audit`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator (implemented in one session; independently reviewed and repaired in a second)
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, docs-contract-reviewer

Completed At: 2026-08-16

## Wave Summary

Wave `1vgep` (Agent Role Canonicalization Audit) delivered one change: Prevent Agent Role Canonicalization Drift. Notable adjustments during implementation: Prevent Agent Role Canonicalization Drift: Observe: added a registry-derived, read-only `agent_surface_integrity` inventory and surfaced it through `wf_audit` as a non-blocking advisory.; Prevent Agent Role Canonicalization Drift: Operator narrowed scope to the audit-only first increment.; Prevent Agent Role Canonicalization Drift: Added advisory-only upgrade-summary reporting and completed verification.

**Changes delivered:**

- **Prevent Agent Role Canonicalization Drift** (`1vflu-bug agent-role-canonicalization-audit`) — 6 ACs completed. Key decisions: Add a shared advisory integrity audit, integrated with `wf_audit` and targeted/full upgrade reporting.; Derive framework canonical destinations from the existing review-policy carrier registry.
## Watchpoints

- Deferred follow-ups live in the change doc's `[~]` items (reference census, wrapper policy, repo-local role classification, seed/prompt reconciliation).
- The advisory is intentionally non-blocking in this release; promoting it to a docs-lint error needs a migration window.

## Review Checkpoints

- **Delivery review — 2026-08-16: REPAIRED AND REVERIFIED.** `agent-surface-integrity-noisy-orphan-scan` is resolved: the audit now reports duplicate framework-role findings only, and the focused fixture asserts one duplicate with no orphan/reference fields. `code-reviewer` independently reverified the repair and approved delivery.
- **Delivery review — 2026-08-16: REPAIRED AND REVERIFIED.** `agent-role-audit-scope-contract-stale` is resolved: Requirements, Scope, workstreams, risks, and decision language now match the deferred ACs/tasks. `docs-contract-reviewer` independently reverified the repair and approved delivery.
- **Council delivery:** not required by the current targeted-delivery receipt. The refreshed readiness council remains current.
- **Memory pass:** `memory_propose(mode='dry_run')` returned no durable-shaped candidates.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| agent-role-audit-scope-contract-stale | do_now | no | completed | docs-contract-reviewer |
| agent-surface-advisory-absent-on-delivering-upgrade | do_now | no | completed | — |
| agent-surface-advisory-integrations-untested | do_now | no | completed | — |
| agent-surface-integrity-noisy-orphan-scan | do_now | no | completed | code-reviewer |
| pre-cleanup-hook-duplicates-advisory | do_now | no | completed | — |

*Machine review state — 5 findings; current: do_now 5, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
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
| plan | 7 | 0 |
| implement | 1 | 0 |
| review | 141 | 2,364,908 |
| **Total** | **149** | **2,364,908** |

<!-- wave:context-efficiency-state {"generation":157,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":1,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-493,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":213,"response_debit":280,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":7,"content_source_credit":4216,"derived_artifact_credit":0,"direct_net":-1636,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":150,"response_debit":7892,"source_credit_count":3,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2190},"review":{"calls":141,"content_source_credit":2616050,"derived_artifact_credit":2049,"direct_net":2364908,"estimated_tokens_saved":2364908,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25602,"response_debit":228935,"source_credit_count":78,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":149,"content_source_credit":2620266,"derived_artifact_credit":2049,"direct_net":2362779,"estimated_tokens_saved":2364908,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25965,"response_debit":237107,"source_credit_count":81,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3536},"wave_id":"1vgep agent-role-canonicalization-audit"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 14 | 0 | 7 | 4,174,157 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":7,"estimated_exploration_avoided":4174157,"surfaced_events":14} -->
<!-- wave:exploration-avoided end -->
