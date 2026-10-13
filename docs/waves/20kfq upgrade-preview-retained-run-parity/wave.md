# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-12
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20kfq upgrade-preview-retained-run-parity`
Title: Upgrade Preview Retained Run Parity

## Objective

Make preview and apply agree on retained upgrade state before pack discovery, preserving valid recovery authority and invalid-lock refusal.

## Changes

Change ID: `20jo4-bug upgrade-preview-retained-run-parity`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-10-12

## Wave Summary

Delivered preview/apply retained-run parity before discovery, explicit recovery-pack selection and refusal/continuation controls. Three ACs and every task are complete; all six specialist delivery approvals and operator closure are recorded. No admitted deferrals. Retrospective: the shared observer and paired unchanged-checkpoint tests preserve the non-obvious recovery boundary; proposal preview returned no new memory. Both waves qualified together: 12,430 tests across 185 files, 12 skips, current green receipt. Cleanup retained only wave.md, the admitted change and authoritative events.jsonl; detailed probes remain temporary.

## Watchpoints

- Watchpoint resolved: preview wave was reviewed and paused before scanner implementation. No live consumer checkpoint was mutated.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| SECURITY-READINESS-1 | do_now | no | completed | security-reviewer, council-readiness |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 247 | 1,488,684 |
| implement | 37 | 779,821 |
| review | 170 | 1,275,823 |
| **Total** | **454** | **3,544,328** |

<!-- wave:context-efficiency-state {"generation":240,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":37,"content_source_credit":825312,"derived_artifact_credit":0,"direct_net":779821,"estimated_tokens_saved":779821,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1071,"response_debit":47000,"source_credit_count":9,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2580},"plan":{"calls":247,"content_source_credit":2203420,"derived_artifact_credit":5673,"direct_net":1488684,"estimated_tokens_saved":1488684,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":24592,"response_debit":699622,"source_credit_count":90,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":170,"content_source_credit":1925517,"derived_artifact_credit":213,"direct_net":1275823,"estimated_tokens_saved":1275823,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7991,"response_debit":644847,"source_credit_count":61,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2931}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":454,"content_source_credit":4954249,"derived_artifact_credit":5886,"direct_net":3544328,"estimated_tokens_saved":3544328,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":33654,"response_debit":1391469,"source_credit_count":160,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9316},"wave_id":"20kfq upgrade-preview-retained-run-parity"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 23 | 0 | 15 | 16,185,660 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":15,"estimated_exploration_avoided":16185660,"surfaced_events":23} -->
<!-- wave:exploration-avoided end -->
## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-12 | Operator authorized both repairs through implementation and full review, pausing each before moving on. Coordinator owns coupled upgrade edits; scoped implementer designs scanner traversal. Independent chair/seat tasks request gpt-6.1-sol high for bounded contract and ownership review; actual runtime identity is unverified. No extra evidence folder; compact outcomes stay here. | Current operator request; admitted change |

| 2026-10-12 | Implementation and required independent specialist delivery reviews complete; paused pending operator closure. | Every AC/task checked; canonical 12,430 tests/185 files/12 skips green; current receipt recorded below. Edit gates closed. No commit, push or package in this task. |

## Review checkpoints

Readiness: independent standard-depth council with red-team primer, fixed architecture/security/QA/reality seats and rotating docs-contract seat; code and release remits also reviewed. The security lane required a compatibility-table correction before implementation. Fresh security reverification cleared it, and all six specialist readiness approvals plus council-readiness were recorded.

Delivery: independent code/security, QA/architecture and docs-contract/release contexts inspected frozen source and ran bounded public-path controls. No implementation defect was found; guard-removal mutants were detected. All six specialist delivery approvals are recorded after current qualification. No delivery council is required by the receipt. The wave was paused before scanner implementation and remains paused, ready for the currently authorized closure.

Qualification: final combined canonical run passed 12,430 tests across 185 files with 12 skips, exit 0; current green receipt inputs hash is e4821ce2fb674828b350dd4b0f1048c2707714a34d65b55f3536078520a90345. The initial sandbox-restricted run and subsequent scanner fixture failures remain documented in the change records; the final run had required permissions and no source/record movement. No timing conclusions, threshold changes, qualification waiver or package claim.
