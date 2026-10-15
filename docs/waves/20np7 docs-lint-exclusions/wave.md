# Wave Record

Owner: Engineering
Status: paused
Last verified: 2026-10-14
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20np7 docs-lint-exclusions`
Title: Docs Lint Exclusions

## Objective

Allow explicit TOML exclusions for existing project documentation without moving it or weakening required lifecycle checks. Establish the list before installation audits.

## Changes

Change ID: `20np6-enh explicit-docs-lint-exclusions`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: architecture-reviewer, security-reviewer, docs-contract-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer, security-reviewer

## Wave Summary

Implemented: optional docs/lint-rules.toml literal file/folder exclusions for generic metadata/link lint, protected contracts and unchanged search behavior. Pre-audit install guidance preserves existing guides and README. All ACs and scoped tasks are complete; final QA/close qualification remains pending the deferred timing check.

## Watchpoints

- Timing investigation remains deferred. Existing waves 20ngc, 20nnk and 20np5 remain paused. The operator authorized closure; the close dry-run remains blocked by final QA approval and a stale framework test receipt. No commit or release authorization.
- docs/README.md retains its presence requirement while project content may opt out of generic checks. Required lifecycle and safe-read boundaries remain active.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| QA-20NP7-COMPAT-01 | do_now | no | completed | qa-reviewer |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | withheld | repaired findings require fresh approval: QA-20NP7-COMPAT-01 | record a fresh independent approval for qa-reviewer |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| performance-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review checkpoints

- Close attempt: operator requested closure on 2026-10-14. Dry-run docs lint and gardening passed; final QA and the current green framework receipt remain unproven. Closure authorization does not waive the deferred timing failure. Retrospective: literal exclusion rules must preserve safe-read diagnostics and protected contracts; regression tests and canonical guidance retain this lesson. The proposed compatibility-repair memory adds no future action beyond those tests, so no new memory candidate was selected. Only wave/change records and the authoritative ledger are retained; no disposable evidence folder needs cleanup.
- Delivery: code/architecture/performance reviewed in one fresh context; security/docs-contract in another; QA independently verified all 10 new tests and withheld final qualification. Public CLI absent/excluded/emptied rules produced 1/0/1 with one load each; disabled-loader, protected-path, omitted-safe-read and moved-instruction controls detected their intended faults. A separate fresh QA/code/docs repair context verified three fixture-only compatibility corrections with all meaningful assertions retained. No council-delivery was required. QA-20NP7-COMPAT-01 is terminal; no unresolved feature finding remains.
- Qualification: canonical default ran 11,671 tests / 187 files / 12 skips in 1017.741s. Three compatibility failures were repaired and the affected 75-test matrix passed in 12.545s, followed by six independent repair controls in 8.083s. The canonical run remains red on deferred projection timing (38.197ms versus 37.333ms effective limit); these focused passes do not create a green receipt. No timing investigation/threshold change or extra full run to seek a pass. Current final QA and close remain pending. Only normal wave/change records and the typed ledger retain durable evidence; routine reports remain temporary.
- Readiness approved, standard isolated red-team primer then architecture (also code/performance remits, one context), security, QA, reality and rotating docs-contract seats, with independent council-chair synthesis and red-team closing. No findings. Existing CLI dispatch, contained-reader refusal and instruction-order controls supported plan feasibility, not unimplemented behavior. The strongest challenge was loss of unreadable-file refusal when generic checks are skipped; AC-2 already requires preserving it. Reusing scan-rules.toml was weighed and rejected because secrets policy and its later provisioning are distinct. No timing qualification was claimed. Typed events retain the evidence; routine seat reports stay temporary.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 156 | 2,405,845 |
| implement | 85 | 706,665 |
| review | 39 | 343,797 |
| **Total** | **280** | **3,456,307** |

<!-- wave:context-efficiency-state {"generation":153,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":85,"content_source_credit":906545,"derived_artifact_credit":0,"direct_net":706665,"estimated_tokens_saved":706665,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2668,"response_debit":200058,"source_credit_count":27,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2846},"plan":{"calls":156,"content_source_credit":2673095,"derived_artifact_credit":3015,"direct_net":2405845,"estimated_tokens_saved":2405845,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9133,"response_debit":265267,"source_credit_count":104,"source_credit_drop_count":0,"structural_source_credit":330,"workflow_prompt_credit":3805},"review":{"calls":39,"content_source_credit":430712,"derived_artifact_credit":1226,"direct_net":343797,"estimated_tokens_saved":343797,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7962,"response_debit":80179,"source_credit_count":28,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":280,"content_source_credit":4010352,"derived_artifact_credit":4241,"direct_net":3456307,"estimated_tokens_saved":3456307,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19763,"response_debit":545504,"source_credit_count":159,"source_credit_drop_count":0,"structural_source_credit":330,"workflow_prompt_credit":6651},"wave_id":"20np7 docs-lint-exclusions"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 12 | 0 | 9 | 6,967,495 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":9,"estimated_exploration_avoided":6967495,"surfaced_events":12} -->
<!-- wave:exploration-avoided end -->

## Progress Log

- 2026-10-14: Operator authorized closing all six paused waves, committing/pushing and a local 1.31.0 pack, with timing investigation still deferred and one shared default qualification run. That run completed 11,671 tests / 187 files / 12 skips in 884.077s, exit 1: test_tensorwell_client.ClientTests.test_cli_exact_child_timeout_bounded_capture expected the oversized-output ValueError but the child wait reached its deadline and raised TimeoutError. The projection-timing file passed. Source-only independent triage does not establish a capture-cap defect or a harmless scheduling flake; final QA remains unproven. All 60 reviewed source hashes stayed unchanged. No retry or profile run followed the failed default; no current green receipt, closure or new pack is claimed. Compact report remains in ignored cache (close-pack-1.31-default.json); routine log remains temporary. Existing source reviews and terminal repairs stand. Memory proposals add no action beyond canonical tests/guidance, so none were selected; folders retain only wave/change records and typed ledgers.
