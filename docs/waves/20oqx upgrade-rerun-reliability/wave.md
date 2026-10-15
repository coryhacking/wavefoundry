# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-15
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20oqx upgrade-rerun-reliability`
Title: Upgrade Rerun Reliability

## Objective

Make completed upgrades safely repeatable, preserve unchanged rendered documents and finish verified retired-storage cleanup.

## Changes

Change ID: `20qvm-bug upgrade-rerun-reliability`
Change Status: `implemented`

## Participants

- Coordinator: Coordinator
- Write-owning roles: Implementer after readiness; coordinator owns lifecycle records
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-10-15

## Wave Summary

Wave `20oqx` (Upgrade Rerun Reliability) delivered one change: Make upgrade reruns terminal and content-stable. Notable adjustments during implementation: Make upgrade reruns terminal and content-stable: Added receipt-bound graph ownership for both legacy and schema-kind receipts. Complete classification precedes deletion; descriptor identity checks refuse replacements. Concurrent changes after the first unlink can leave partial progress; retry reuses captured identities. Platforms without descriptor-safe deletion retain graph and cleanup state; no native Windows execution claimed.

**Changes delivered:**

- **Make upgrade reruns terminal and content-stable** (`20qvm-bug upgrade-rerun-reliability`) — 5 ACs completed. Key decisions: Choose conservative refusal of ordinary same-full-build adoption, with retained recovery precedence and explicit index repair.
## Watchpoints

- Preserve protected publication and recovery behavior. Implementation and focused tests are complete; aggregate qualification and independent delivery review remain. Timing investigation stays deferred.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| RD-20OQX-1 | do_now | no | completed | architecture-reviewer, code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer, council-readiness |
| RD-20OQX-2 | do_now | no | completed | code-reviewer, qa-reviewer, security-reviewer, architecture-reviewer, council-readiness |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: pending

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 261 | 2,759,013 |
| implement | 19 | 412,697 |
| review | 237 | 3,204,329 |
| **Total** | **517** | **6,376,039** |

<!-- wave:context-efficiency-state {"generation":320,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":19,"content_source_credit":424738,"derived_artifact_credit":0,"direct_net":412697,"estimated_tokens_saved":412697,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":535,"response_debit":14622,"source_credit_count":4,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3116},"plan":{"calls":261,"content_source_credit":3360679,"derived_artifact_credit":3204,"direct_net":2759013,"estimated_tokens_saved":2759013,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":39926,"response_debit":568749,"source_credit_count":126,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":237,"content_source_credit":3633427,"derived_artifact_credit":0,"direct_net":3204329,"estimated_tokens_saved":3204329,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8079,"response_debit":424086,"source_credit_count":87,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3067}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":517,"content_source_credit":7418844,"derived_artifact_credit":3204,"direct_net":6376039,"estimated_tokens_saved":6376039,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":48540,"response_debit":1007457,"source_credit_count":217,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9988},"wave_id":"20oqx upgrade-rerun-reliability"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 24 | 0 | 20 | 12,455,621 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":20,"estimated_exploration_avoided":12455621,"surfaced_events":24} -->
<!-- wave:exploration-avoided end -->
## Current assumptions

Four cohesive waves avoid a single large approval boundary and the overhead of one wave per small item. Shared framework files are implemented serially; planning does not open an implementation slot.

## Outputs produced or expected

Admitted change plans, focused regression coverage, updated canonical guidance and a concise durable result in this wave record. No permanent raw probe/evidence folders are planned.

## Review checkpoints

Delivery review: code, QA, architecture, security, docs-contract and release lanes approved in one disclosed fresh independent context (`20oqx-delivery-independent-oqx_delivery-20261015`), not six independent reviewers. The reviewer executed 36 selected positive tests without skips and killed three in-memory mutants (same-build bypass, graph ownership recapture, unknown publication accepted). Reviewed source hashes remained unchanged. AC-1–AC-5 reconciled; no delivery findings. Aggregate canonical qualification remains pending, and no closure/release approval is implied.

Durable reproduction anchors: `.wavefoundry/framework/scripts/tests/test_upgrade_rerun_reliability.py` (`RerunTests`, `IncomingOutcomeTests`, `GraphOwnershipTests`), `.wavefoundry/framework/scripts/tests/test_storage_upgrade_resume.py` (`StorageUpgradeProcessResumeTests`), `.wavefoundry/framework/scripts/tests/test_sqlite_storage_migration.py` (`SchemaEightKindTests`), `.wavefoundry/framework/scripts/tests/test_upgrade_recovery_guidance.py`, and `.wavefoundry/framework/scripts/tests/test_memory_backfill.py` (`HistoricalMemoryBackfillTests.test_source_fingerprint_change_requeues_completed_wave`). Temporary raw review output is outside the repository. No native Windows, live model/service or exact-release qualification was performed; deletion can make partial progress after the first unlink, as documented.

Prepare verifies decisions and exact affected surfaces before implementation. Delivery checks registered behavior, negative controls and compatibility. Reuse valid framework qualification; consolidate a necessary suite run after code changes settle rather than repeating it for bookkeeping.

## Completion criteria

Every admitted AC and task is reconciled with evidence, required delivery lanes approve, documentation validates and the operator authorizes closure.

## Handoff or next-wave notes

Implemented after recorded readiness. Pause for aggregate qualification and independent delivery review while the remaining admitted waves proceed. No close, commit, release or external publication is authorized.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Operator authorized Prepare, review and implementation; closure/commit/release remain unrequested. Coordinator integrates serial source changes; independent role contexts review. Inherited capable model chosen for cross-module reasoning; actual runtime model/effort not exposed. | Current task; canonical lifecycle prompts |
| 2026-10-15 | Implementation and focused regression work complete; all five ACs have observable controls. Same-build adoption refuses, retained recovery and explicit repairs remain supported, index failure returns nonzero, graph cleanup uses original receipt identities. Unchanged renderer dates verified without writer changes. Eight guard mutants detected; full docs lint passed. Aggregate suite and delivery approval remain pending; see change Progress Log for exact counts and limitations. | 20qvm; temporary logs outside repository |

Memory retrospective: bounded `memory_propose(mode="dry_run")` returned no eligible draft. Durable repair/provider contracts are already in the current implementation, tests and canonical guidance; no additional memory file or raw evidence folder was created.

## Final qualification

2026-10-15: canonical `run_tests.py` passed 11,731 tests across 189 files, with 12 skips, in 796.576 seconds. Fresh green receipt recorded after all source repairs and review-record writes settled; no repository writes during the run. Earlier census failures are repaired, and previously failing or timed-out files passed. Full docs validation passed before qualification. Required delivery reviews approve; wave remains paused for operator closure. No close, commit, push, package or release performed. Timing investigation remains deferred; no threshold or waiver changed.

Closure reconciliation (2026-10-15): operator authorized closure, commit and push; close verified current green qualification and required review authority. No package or release requested. Only wave.md, admitted change documents and authoritative events.jsonl are retained in this wave folder; no disposable evidence artifacts were present. Prior paused/pending notes above describe earlier checkpoints.
