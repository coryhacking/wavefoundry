# Wave Record

Owner: Engineering
Status: paused
Last verified: 2026-10-12
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20gz3 uv-release-bootstrap`
Title: Uv Release Bootstrap

## Objective

Refresh the official 1.29.0 bootstrap to uv 0.12.17 and its verified wheel inventory while preserving existing uv installations. Qualify the changed release source and build the official feature/model artifacts.

## Changes

Change ID: `20gz2-maint refresh-uv-release-bootstrap`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (coordinator only)
- Requested review lanes: code-reviewer, qa-reviewer, security-reviewer, release-reviewer
- Required review lanes: code-reviewer, qa-reviewer, release-reviewer, security-reviewer

## Wave Summary

Release authorization (2026-10-12): the operator requested a follow-up wave for the combined log-tail fixture and then said, "So we can release now." This explicitly permits the 1.29.0 pack with the second-profile timing-budget exception deferred under concurrent load and the declared-profile log-content exception tracked in wave 20h6q / change 20gz6. Reports remain red; no passing canonical profile comparison is claimed. Existing uv users are not forced to update. Source qualification remains the green default receipt for 7ed6f72bf5f7df9eb7940d2f5039f915634c10d145f54598c409b960b6dcabac.

A bounded release dependency refresh: only the bootstrap pin and hashes change; installed uv remains operator-managed.

## Watchpoints

- Watchpoint: do not force-upgrade an existing uv or change setup control flow.
- Finish source edits before qualification; run packaging profiles sequentially.
- Native Windows execution remains outside this macOS qualification.
- Required reviewers use fresh contexts and temporary evidence; no permanent evidence folder.
- Allocation: coordinator owns the small constant edit; independent review contexts use gpt-6.1-sol/high for scoped checks and synthesis. Requested model settings are recorded; actual runtime identity is unavailable unless the host reports it.

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
| council-readiness | pending | approval binding is stale: pinned receipt `review-policy-6b938e38cd2e63317ecd` does not match current receipt `review-policy-bfa3f06889d8d7c371fe` | record approval evidence for council-readiness |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 149 | 205,977 |
| implement | 137 | 0 |
| review | 41 | 131,325 |
| **Total** | **327** | **337,302** |

<!-- wave:context-efficiency-state {"generation":214,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":137,"content_source_credit":312015,"derived_artifact_credit":0,"direct_net":-67597,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3955,"response_debit":378593,"source_credit_count":22,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2936},"plan":{"calls":149,"content_source_credit":776506,"derived_artifact_credit":1802,"direct_net":205977,"estimated_tokens_saved":205977,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":23289,"response_debit":555545,"source_credit_count":58,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6503},"review":{"calls":41,"content_source_credit":269596,"derived_artifact_credit":1260,"direct_net":131325,"estimated_tokens_saved":131325,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4613,"response_debit":134918,"source_credit_count":25,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":327,"content_source_credit":1358117,"derived_artifact_credit":3062,"direct_net":269705,"estimated_tokens_saved":337302,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":31857,"response_debit":1069056,"source_credit_count":105,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9439},"wave_id":"20gz3 uv-release-bootstrap"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 4 | 0 | 4 | 435,017 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":435017,"surfaced_events":4} -->
<!-- wave:exploration-avoided end -->
## Review Checkpoints

- Delivery (2026-10-12): code, security, QA, release and council approvals recorded; no findings remain. Final QA/release/chair checks inspected the actual archives and current qualification metadata without rerunning tests. Default qualification is green (12,402 tests, 185 files, 12 skips); the complete red second/declared reports remain explicitly deferred for this release under AC-3. Follow-up 20h6q owns the combined log-tail assertion; no timing conclusion is claimed under concurrent load. The original full council roster and adversarial primer remain the review basis; the final artifact pass was scoped to QA, release and chair. Wave remains paused pending operator closure.
- Artifacts: feature `wavefoundry-1.29.0.pw6p.zip`, SHA256 `e766964f6334d33a5db1ed7e0365aed6087114563145dda365ca16acb80bea5a`; models `wavefoundry-models-3.zip`, SHA256 `c3de8d60e8dd55dd6c357f8256af4748a90b089ec92d6c677671b22c56030142`. Verified CRC, safe unique paths, 248 exact source counterparts, stamped version/changelog, 18 pinned uv wheel hashes, 15 model hashes and license notices. Native Windows execution is not claimed. Source commit and publication have not occurred.

- Readiness: full adversarial primer followed by independent architecture-reviewer, security-reviewer, qa-reviewer and reality-checker fixed seats; rotating release-reviewer and separate code-reviewer. Council unanimously approved after an anonymous merits pass and fixed-seat consideration of the release alternative. No blockers or material disagreements. Exact registry comparison, real binary exercise and sequential final-source qualification remain delivery obligations; native Windows execution is not claimed.
