# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-09-28
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1z8oz extension-tool-aliases`
Title: Extension Tool Aliases

## Objective

A fork can serve Wavefoundry tools under its own names, hide canonical names, and reuse a core name with an incompatible handler, while every name-keyed protection still applies (RFC section 4.3).

## Changes

Change ID: `1z8oy-enh extension-tool-aliases`
Change Status: `planned`

## Participants

- Coordinator: implementer
- Write-owning roles: implementer
- Requested review lanes: architecture-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

## Wave Summary

Adds alias, hidden-name and replacement declarations to the extension declaration. Aliases are copies of the wrapped canonical tool, so the lifecycle lock, publication guard and cost wrapper apply by construction.

## Watchpoints

- Watchpoint: serializes with wave `1z8ox` (its change `1z8ow` edits `wf_server/server_impl.py` and tests); block opening until `1z8ox` closes, or rebase on it.

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
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | pending | no current executed approval | record approval evidence for wave-council-delivery |
| code-reviewer | pending | no current executed approval | record approval evidence for code-reviewer |
| qa-reviewer | pending | no current executed approval | record approval evidence for qa-reviewer |
| architecture-reviewer | pending | no current executed approval | record approval evidence for architecture-reviewer |
| docs-contract-reviewer | pending | no current executed approval | record approval evidence for docs-contract-reviewer |
| security-reviewer | pending | no current executed approval | record approval evidence for security-reviewer |
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
| plan | 29 | 401,930 |
| **Total** | **29** | **401,930** |

<!-- wave:context-efficiency-state {"generation":29,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":29,"content_source_credit":456975,"derived_artifact_credit":1536,"direct_net":401930,"estimated_tokens_saved":401930,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3208,"response_debit":57182,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":29,"content_source_credit":456975,"derived_artifact_credit":1536,"direct_net":401930,"estimated_tokens_saved":401930,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3208,"response_debit":57182,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"wave_id":"1z8oz extension-tool-aliases"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
