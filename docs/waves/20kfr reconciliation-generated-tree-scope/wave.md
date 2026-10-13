# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-12
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20kfr reconciliation-generated-tree-scope`
Title: Reconciliation Generated Tree Scope

## Objective

Prune generated and Git-ignored trees before reconciliation traversal while keeping required operating carriers visible and all work bounded.

## Changes

Change ID: `20kfp-bug reconciliation-generated-tree-scope`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, performance-reviewer, security-reviewer

Completed At: 2026-10-12

## Wave Summary

Delivered generated-directory pruning and bounded Git-ignore queries with explicit required-carrier precedence. Four ACs and every task are complete; all seven specialist delivery approvals and operator closure are recorded. No admitted deferrals. Retrospective: keep the ordinary.toml negative control unignored so Git cannot conceal suffix broadening. The proposed memory duplicated that canonical test and existing review guidance, so no new record was selected. Both waves qualified together: 12,430 tests across 185 files, 12 skips, current green receipt. Cleanup retained only wave.md, the admitted change and authoritative events.jsonl; detailed probes remain temporary.

## Watchpoints

- Watchpoint: Run after preview wave pauses. Do not raise budgets, delete diagnostic artifacts or run field performance probes.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 20kfr-toml-carveout-pin | do_now | no | completed | code-reviewer, qa-reviewer |
| QUAL-DELEGATED-FIXTURE-MODULES-002 | do_now | no | completed | code-reviewer, qa-reviewer, release-reviewer |
| QUAL-TIMED-GIT-CENSUS-001 | do_now | no | completed | code-reviewer, qa-reviewer |

*Machine review state — 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
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
| performance-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 39 | 41,574 |
| implement | 30 | 815,898 |
| review | 110 | 1,660,628 |
| **Total** | **179** | **2,518,100** |

<!-- wave:context-efficiency-state {"generation":182,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":30,"content_source_credit":413443,"derived_artifact_credit":0,"direct_net":815898,"estimated_tokens_saved":815898,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1014,"response_debit":38616,"source_credit_count":23,"source_credit_drop_count":0,"structural_source_credit":439355,"workflow_prompt_credit":2730},"plan":{"calls":39,"content_source_credit":153032,"derived_artifact_credit":251,"direct_net":41574,"estimated_tokens_saved":41574,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19814,"response_debit":95700,"source_credit_count":21,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":110,"content_source_credit":1943191,"derived_artifact_credit":1561,"direct_net":1660628,"estimated_tokens_saved":1660628,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19296,"response_debit":267759,"source_credit_count":84,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2931}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":179,"content_source_credit":2509666,"derived_artifact_credit":1812,"direct_net":2518100,"estimated_tokens_saved":2518100,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":40124,"response_debit":402075,"source_credit_count":128,"source_credit_drop_count":0,"structural_source_credit":439355,"workflow_prompt_credit":9466},"wave_id":"20kfr reconciliation-generated-tree-scope"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 29 | 0 | 17 | 13,414,840 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":17,"estimated_exploration_avoided":13414840,"surfaced_events":29} -->
<!-- wave:exploration-avoided end -->
## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-12 | Operator authorized both repairs through implementation and full review, pausing each before moving on. Coordinator owns coupled upgrade edits; scoped implementer designs scanner traversal. Independent chair/seat tasks request gpt-6.1-sol high for bounded contract and ownership review; actual runtime identity is unverified. No extra evidence folder; compact outcomes stay here. | Current operator request; admitted change |

| 2026-10-12 | Implementation and required independent specialist delivery reviews complete; paused pending operator closure. | Every AC/task checked; canonical 12,430 tests/185 files/12 skips green; current receipt recorded below. Edit gates closed. No commit, push or package in this task. |

## Review checkpoints

Readiness: independent standard-depth council with red-team primer, fixed architecture/security/QA/reality seats and rotating docs-contract seat approved the bounded Git/carrier design; code, performance and release remits also approved. No readiness blockers remain.

Delivery: independent code/security, QA/performance and architecture/docs-contract/release contexts reviewed frozen implementation. Cycle 1 added an unignored ordinary.toml to expose a suffix-broadening mutant. Cycle 2 corrected the timed-call census and staged seven shipped registry modules in the delegated-child fixture. Fresh independent reverification detected the known-bad controls and cleared all three findings; the tool recorded the cycle-2 convergence checkpoint. Production code and original assertions were unchanged during those repairs. All seven required specialist delivery approvals are current. No delivery council is required by the receipt; operator has now authorized closure.

Evidence: durable regression controls live in `.wavefoundry/framework/scripts/tests/test_reconcile_scan.py` (GeneratedAndIgnoredScopeTests, HostPermissionChannelTests and RendererProvenanceChannelTests), `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` (BoundedUpgradeReportingTests and DelegatedSummaryPg1aReproductionTests), and `.wavefoundry/framework/scripts/tests/test_tree_kill_routing.py` (ClassificationTests). Adding 400 excluded descendants preserved 238 visited entries and 189 read bytes in an independent fixture; 513 live files required three Git batches of 256/256/1. These are work counts, not field timing claims. Final canonical qualification passed 12,430 tests across 185 files with 12 skips and wrote current green receipt e4821ce2fb674828b350dd4b0f1048c2707714a34d65b55f3536078520a90345. Full documentation validation is clean; no live field scan, native Windows or package qualification claimed.
