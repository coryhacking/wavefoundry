# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-19
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `23ve4 repair-renamed-profile-qualification`
Title: Repair Renamed Profile Qualification

## Objective

Qualify v1.45.0 for distributions that rename lifecycle records and prompts. Preserve their registered names, diagnostic behavior and repository boundaries.

## Changes

Change ID: `23uxi-bug renamed-profile-release-qualification`
Change Status: `implemented`

## Participants

- Coordinator: Coordinator
- Write-owning roles: Implementer
- Requested review lanes: code-reviewer, qa-reviewer, release-reviewer
- Required review lanes: code-reviewer, qa-reviewer, release-reviewer

Completed At: 2026-11-19

## Wave Summary

Wave `23ve4 repair-renamed-profile-qualification` (Repair Renamed Profile Qualification) delivered one change: Qualify renamed distributions for v1.45.0.

Intent outcome: achieved for release qualification. QA independently confirmed that refusing an external manifest still reports genuine in-root drift and that both public renderers preserve registered skill names, owner bytes and unrelated skills. On the same candidate, all 26 previous failures mapped to passing, unskipped checks across 11 files. Downstream field use remains unobserved.

**Changes delivered:**

- **Qualify renamed distributions for v1.45.0** (`23uxi-bug renamed-profile-release-qualification`) — AC-1, AC-2 and AC-3 completed.

## Watchpoints

- Watchpoint: preserve the failing baseline, profile coverage and containment checks.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 23uxi-drift-fallback-test | do_now | no | completed | qa-reviewer, code-reviewer, release-reviewer |
| 23uxi-ordinary-registry-test | do_now | no | completed | qa-reviewer, code-reviewer, release-reviewer |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-19: Intent outcome: achieved for release qualification. QA independently confirmed that refusing an external manifest still reports genuine in-root drift and that both public renderers preserve registered skill names, owner bytes and unrelated skills. On the same candidate, all 26 previous failures mapped to passing, unskipped checks across 11 files. Downstream field use remains unobserved.

2026-11-19: Readiness council used a full red-team primer, architecture, security, QA and reality checks, a rotating release reviewer and a separate code specialist. The independent reviews used one host and shared the same failing baseline. The council approved with literal fixture expectations and paired valid and invalid controls. Its strongest challenge was that tests could silently accept wrong names if they obtained their expectations from the resolver.

2026-11-19: Code, QA and release reviewed delivery in separate contexts. QA identified two weak regression controls. The repaired symlink fixture caught suppression of a genuine local drift finding, and both renderers caught removal of a reserved skill from the real registry. Only the synthetic future name used an injected registry. Fresh reviewers reverified both repairs. The receipt selected targeted delivery.

2026-11-19: Each reviewer checked the 13 frozen framework files and the three completed 251-worker reports. Default and declared each ran 13,080 tests with 12 skips. The renamed profile ran 13,058 with 38 skips. Both qualification comparisons passed. Each profile retained its original skip IDs and reasons. An earlier concurrent default run missed its 10 ms timing budget at 13.347 ms. The standalone rerun passed with the same source and budget.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 16 | 972 |
| implement | 56 | 305,064 |
| review | 20 | 64,005 |
| **Total** | **92** | **370,041** |

<!-- wave:context-efficiency-state {"generation":80,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":56,"content_source_credit":391230,"derived_artifact_credit":0,"direct_net":305064,"estimated_tokens_saved":305064,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2298,"response_debit":87198,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3330},"plan":{"calls":16,"content_source_credit":17392,"derived_artifact_credit":2321,"direct_net":972,"estimated_tokens_saved":972,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2526,"response_debit":22143,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5928},"review":{"calls":20,"content_source_credit":104519,"derived_artifact_credit":1044,"direct_net":64005,"estimated_tokens_saved":64005,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6657,"response_debit":45185,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10284}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":92,"content_source_credit":513141,"derived_artifact_credit":3365,"direct_net":370041,"estimated_tokens_saved":370041,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11481,"response_debit":154526,"source_credit_count":42,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":19542},"wave_id":"23ve4 repair-renamed-profile-qualification"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 2 | 0 | 2 | 3,392,409 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":3392409,"surfaced_events":2} -->
<!-- wave:exploration-avoided end -->
