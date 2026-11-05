# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-05
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `22l9i canonical-fallback-reference`
Title: Canonical Fallback Reference

## Objective

Remove the contradictory fallback count from the prompt-bootstrap instruction. Agents should follow seed 180 without a separately maintained numerical count; the retrieval policy itself remains unchanged.

## Changes

Change ID: `22l9h-doc seed-bootstrap-fallback-reference`
Change Status: `implemented`

## Participants

- Coordinator: root
- Write-owning roles: coordinator only
- Requested review lanes: qa-reviewer, docs-contract-reviewer
- Required review lanes: qa-reviewer, docs-contract-reviewer

Completed At: 2026-11-05

## Wave Summary

Wave `22l9i` (Canonical Fallback Reference) delivered one change: Reference canonical shell retrieval fallback rules.

Intent outcome: achieved the instruction-consistency outcome. Exact baseline comparison proves only the stale-count phrase changed and the canonical citation survived; seeds 020/180 are byte-identical. Fresh QA and docs-contract delivery approvals confirm the bounded intent. The canonical frozen-tree suite passes 12,314 tests / 217 files / 12 intended skips. Published package remains unchanged.

**Changes delivered:**

- **Reference canonical shell retrieval fallback rules** (`22l9h-doc seed-bootstrap-fallback-reference`) — 2 ACs completed. Key decisions: Reference canonical conditions without a count.
## Watchpoints

- Watchpoint: preserve the three canonical retrieval-fallback reasons and separate literal-byte/Git uses.
- Coordinator implements this tightly coupled phrase edit; independent reviewers are read-only. Use current host defaults for this low-ambiguity task; runtime model identity is unverified. Readiness council uses the policy-selected standard tier with red-team and docs-contract seats.

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
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-05: Closure retrospective: a count-free reference avoids maintaining duplicate policy state; no new memory is needed because the correction is self-explanatory and existing guidance already requires a settled tree before qualification. The first runner refusal and successful frozen rerun are recorded above. Memory dry-run proposes no eligible durable record. Final scope adds no review lane or delivery Council. Exact pre-change source remains recoverable from commit ddb56265; typed records retain independent probe observations, so disposable baseline copies add no unique proof and may be cleaned by Close. Operator explicitly authorized close, commit and push.

2026-11-05: Delivery is complete; required lanes approve, no findings, all ACs/tasks complete. Initial tests all passed but receipt was refused for a concurrent coordinator handoff edit; unchanged-source frozen rerun passes and writes the current green receipt (616.761 seconds). Only operator signoff remains; no closure or commit requested.

2026-11-05: Readiness approved on review-policy-443ce6c84ce1cd0851dc: standard targeted council (isolated red-team primer, docs-contract seat, independent chair); required QA/docs-contract approve. No findings, unanimous, intent_fit establishes. Same model family; exact runtime identity unverified. Contract correction only, not proof of agent adherence.

2026-11-05: Intent outcome: achieved the instruction-consistency outcome. Exact baseline comparison proves only the stale-count phrase changed and the canonical citation survived; seeds 020/180 are byte-identical. Fresh QA and docs-contract delivery approvals confirm the bounded intent. The canonical frozen-tree suite passes 12,314 tests / 217 files / 12 intended skips. Published package remains unchanged.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 26 | 27,964 |
| implement | 50 | 27,287 |
| review | 13 | 8,912 |
| **Total** | **89** | **64,163** |

<!-- wave:context-efficiency-state {"generation":63,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":50,"content_source_credit":76647,"derived_artifact_credit":0,"direct_net":27287,"estimated_tokens_saved":27287,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1592,"response_debit":50524,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2756},"plan":{"calls":26,"content_source_credit":53044,"derived_artifact_credit":2114,"direct_net":27964,"estimated_tokens_saved":27964,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1402,"response_debit":31300,"source_credit_count":17,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5508},"review":{"calls":13,"content_source_credit":20380,"derived_artifact_credit":821,"direct_net":8912,"estimated_tokens_saved":8912,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1221,"response_debit":14846,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3778}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":89,"content_source_credit":150071,"derived_artifact_credit":2935,"direct_net":64163,"estimated_tokens_saved":64163,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4215,"response_debit":96670,"source_credit_count":37,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12042},"wave_id":"22l9i canonical-fallback-reference"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
