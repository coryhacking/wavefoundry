# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-19
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `23tcw test-boundaries-and-technology-evidence`
Title: Test Boundaries And Technology Evidence

## Objective

Builders choose a test boundary that exposes the claimed failure. For projects evaluating a schema generator or a runtime, builders and reviewers can identify the evidence that justifies adoption, rejection or a targeted trial.

## Changes

Change ID: `23tcu-enh match-test-boundary-to-failure`
Change Status: `implemented`

Change ID: `23tcv-enh guide-schema-consumers-and-runtime-decisions`
Change Status: `implemented`

## Participants

- Coordinator: Codex coordinator
- Write-owning roles: Documentation implementer
- Requested review lanes: none
- Required review lanes: docs-contract-reviewer

Completed At: 2026-11-19

## Wave Summary

Wave `23tcw` (Test Boundaries And Technology Evidence) delivered two changes: Match the test boundary to the failure and Guide Rust schema consumers and runtime performance decisions.

Intent outcome: The builder exercised the failing listener and chose a transport measurement before a migration. QA distinguished the counter from recovery and valid-payload compatibility from rejection of invalid inputs. These exercises demonstrate use of the guidance in the supplied cases.

**Changes delivered:**

- **Match the test boundary to the failure** (`23tcu-enh match-test-boundary-to-failure`) — AC-1 and AC-2 completed. Key decisions: Propose a question in the existing builder and QA guidance.
- **Guide Rust schema consumers and runtime performance decisions** (`23tcv-enh guide-schema-consumers-and-runtime-decisions`) — AC-1, AC-2 and AC-3 completed. Key decisions: Put schema generation in situational Rust guidance and workload measurement in shared guidance.

## Watchpoints

- Watchpoint: Use one writer for overlapping role instructions. Preserve the difference between field results and local worked exercises.

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
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-19: Intent outcome: The builder exercised the failing listener and chose a transport measurement before a migration. QA distinguished the counter from recovery and valid-payload compatibility from rejection of invalid inputs. These exercises demonstrate use of the guidance in the supplied cases.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 26 | 37,457 |
| implement | 56 | 0 |
| review | 17 | 822 |
| **Total** | **99** | **38,279** |

<!-- wave:context-efficiency-state {"generation":71,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":56,"content_source_credit":106042,"derived_artifact_credit":0,"direct_net":-20410,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1746,"response_debit":128458,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3752},"plan":{"calls":26,"content_source_credit":51280,"derived_artifact_credit":3024,"direct_net":37457,"estimated_tokens_saved":37457,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3091,"response_debit":19684,"source_credit_count":11,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5928},"review":{"calls":17,"content_source_credit":29870,"derived_artifact_credit":795,"direct_net":822,"estimated_tokens_saved":822,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3122,"response_debit":33283,"source_credit_count":13,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6562}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":99,"content_source_credit":187192,"derived_artifact_credit":3819,"direct_net":17869,"estimated_tokens_saved":38279,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7959,"response_debit":181425,"source_credit_count":40,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":16242},"wave_id":"23tcw test-boundaries-and-technology-evidence"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
