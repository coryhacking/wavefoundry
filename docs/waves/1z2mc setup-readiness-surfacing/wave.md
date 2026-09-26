# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-26
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1z2mc setup-readiness-surfacing`
Title: Setup Readiness Surfacing

## Objective

The agent is told when setup needs attention right after an MCP start or reload, through its tool responses and the reload response, instead of the result staying in stderr. Before the 1.27.0 release.

## Changes

Change ID: `1z2mb-enh setup-readiness-on-start-and-reload`
Change Status: `implemented`

## Participants

- Coordinator: operator session
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-09-26

## Wave Summary

Wave `1z2mc` (Setup Readiness Surfacing) delivered one change: Surface Setup Readiness to the Agent on MCP Start and Reload. Notable adjustments during implementation: Surface Setup Readiness to the Agent on MCP Start and Reload: Implementation found the startup seeding already present in `_record_runner_identity` (the plan and readiness review had missed it). A duplicate seed added to `build_server` was removed; the start test uses the resolved root that `discover_root` returns in production. Mutants: removing the existing seed, the reload assessment, the action predicate, once-per-result or the skips each fail a test.

**Changes delivered:**

- **Surface Setup Readiness to the Agent on MCP Start and Reload** (`1z2mb-enh setup-readiness-on-start-and-reload`) — 4 ACs completed. Key decisions: Surface through a response diagnostic, once per distinct result per handler; Seed the runner's startup result and assess from the reload instead of a thread in `ImplHandler.__init__` (readiness B4 and alternative)
## Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

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
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 78 | 1,757,222 |
| implement | 37 | 965,408 |
| review | 48 | 1,801,204 |
| **Total** | **163** | **4,523,834** |

<!-- wave:context-efficiency-state {"generation":154,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":37,"content_source_credit":1024055,"derived_artifact_credit":1305,"direct_net":965408,"estimated_tokens_saved":965408,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3823,"response_debit":56803,"source_credit_count":50,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":674},"plan":{"calls":78,"content_source_credit":1894678,"derived_artifact_credit":2461,"direct_net":1757222,"estimated_tokens_saved":1757222,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4564,"response_debit":139162,"source_credit_count":67,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":48,"content_source_credit":1868452,"derived_artifact_credit":1279,"direct_net":1801204,"estimated_tokens_saved":1801204,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3366,"response_debit":67477,"source_credit_count":61,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":163,"content_source_credit":4787185,"derived_artifact_credit":5045,"direct_net":4523834,"estimated_tokens_saved":4523834,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11753,"response_debit":263442,"source_credit_count":178,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6799},"wave_id":"1z2mc setup-readiness-surfacing"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 11 | 0 | 8 | 10,828,618 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":8,"estimated_exploration_avoided":10828618,"surfaced_events":11} -->
<!-- wave:exploration-avoided end -->
