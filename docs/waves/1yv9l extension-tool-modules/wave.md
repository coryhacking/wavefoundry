# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-23
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1yv9l extension-tool-modules`
Title: Extension Tool Modules

## Objective

Let a downstream distribution add or explicitly override MCP tools in-process through one fork-edited declaration, so enterprise operators approve a single server entry point while forks stop editing core registration.

## Changes

Change ID: `1yuc4-feat extension-tool-modules`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-09-24

## Wave Summary

Wave `1yv9l` (Extension Tool Modules) delivered one change: Extension Tool Modules.

**Changes delivered:**

- **Extension Tool Modules** (`1yuc4-feat extension-tool-modules`) — 7 ACs completed. Key decisions: Fork-edited stdlib-only declaration module, loaded only from that declaration; Fail closed at startup for any declared-module defect
## Watchpoints

- Watchpoint: the golden tool-surface fixture must not change; no extension code is ever loaded from a target repository.
- Watchpoint: server_impl.py edits owe the usual reload-purge census and middleware-order checks.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-ASYNC-HANDLERS | do_now | no | completed | — |
| DEL-CALL-PATH-TESTS | do_now | no | completed | — |
| DEL-OVERRIDE-VALUE-COMPATIBILITY | do_now | no | completed | code-reviewer, qa-reviewer, docs-contract-reviewer, wave-council-delivery |
| DEL-UNRECORDED-REGISTRATION | do_now | no | completed | — |

*Machine review state — 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 20 | 3,403 |
| implement | 28 | 0 |
| review | 75 | 978,383 |
| **Total** | **123** | **981,786** |

<!-- wave:context-efficiency-state {"generation":126,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":28,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-4387,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1095,"response_debit":5996,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2704},"plan":{"calls":20,"content_source_credit":24972,"derived_artifact_credit":2688,"direct_net":3403,"estimated_tokens_saved":3403,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3164,"response_debit":24902,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":75,"content_source_credit":1218197,"derived_artifact_credit":3021,"direct_net":978383,"estimated_tokens_saved":978383,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":21736,"response_debit":223415,"source_credit_count":70,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":123,"content_source_credit":1243169,"derived_artifact_credit":5709,"direct_net":977399,"estimated_tokens_saved":981786,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25995,"response_debit":254313,"source_credit_count":84,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8829},"wave_id":"1yv9l extension-tool-modules"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 7 | 0 | 5 | 4,182,840 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":5,"estimated_exploration_avoided":4182840,"surfaced_events":7} -->
<!-- wave:exploration-avoided end -->
