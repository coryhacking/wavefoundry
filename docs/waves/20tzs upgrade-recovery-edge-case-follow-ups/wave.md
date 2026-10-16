# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-15
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20tzs upgrade-recovery-edge-case-follow-ups`
Title: Upgrade recovery edge-case follow-ups

## Objective

Repair four bounded upgrade recovery and executable-lookup edge cases while preserving existing ownership, no-clobber and compatibility contracts. Keep prior wave scope and the separate timing receipt hold unchanged.

## Changes

Change ID: `20tzr-bug upgrade-recovery-and-path-diagnostic-edge-cases`
Change Status: `implemented`

## Participants

- Coordinator: Coordinator
- Write-owning roles: One implementer after readiness; coordinator owns lifecycle records
- Requested review lanes: code-reviewer, qa-reviewer, security-reviewer, architecture-reviewer, release-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-10-15

## Wave Summary

Wave `20tzs` (Upgrade recovery edge-case follow-ups) delivered one change: Repair upgrade recovery and PATH diagnostic edge cases. Notable adjustments during implementation: Repair upgrade recovery and PATH diagnostic edge cases: Replacement qualification also passed all 11,838 tests / 200 files / 12 existing skips in 744.159s. Its only failure was concurrent authored changes in another session's wave 20tpp; no 20tzs or reviewed source path was flagged. Implementation/review are complete and paused; green receipt remains withheld. Await coordination before any further full run; do not revert or absorb the other session's edits.; Repair upgrade recovery and PATH diagnostic edge cases: Readback consolidation: pre-edit operator updates described the four intended repairs and preserved proof/compatibility boundaries. For example, read-back failure previously stranded an unowned slot; now it rolls back or persists provable existing-format ownership, with explicit compound failure. This consolidates execution narration, not a new scope or approval.; Repair upgrade recovery and PATH diagnostic edge cases: Held-descriptor Windows sharing required a narrow handle-based ReOpenFile adapter before publication, independently checked against Microsoft API/CRT contracts. Exact identity census in test_sqlite_storage_migration.py now lists only the five added fresh comparisons; no wildcard/exemption or historical-device semantics changed.

**Changes delivered:**

- **Repair upgrade recovery and PATH diagnostic edge cases** (`20tzr-bug upgrade-recovery-and-path-diagnostic-edge-cases`) — 6 ACs completed. Key decisions: Keep post-publication read-back and use the existing checkpoint only for positively proven retained ownership; Select bounded repairs using existing helpers/proof/checkpoint formats
## Watchpoints

- Watchpoint: prove the post-publication rollback/existing-checkpoint retry route and old-runner helper availability before code edits.
- Watchpoint: preserve no-clobber, final no-follow, fresh identity/hash and replacement refusal; never adopt an occupied slot by name.
- Follow-up: timing/receipt exceptions, native qualification and the original waves remain separate; do not alter the explicitly approved policies.
- Watchpoint: source inspection found the same raw attribute check in _preserve_original_manifest on pre_extract; include that bounded recovery path in the classification census.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 20tzs-readiness-ac3-compound-failure | do_now | no | completed | qa-reviewer, security-reviewer |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 129 | 384,307 |
| implement | 31 | 80,982 |
| review | 124 | 930,715 |
| **Total** | **284** | **1,396,004** |

<!-- wave:context-efficiency-state {"generation":202,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":31,"content_source_credit":91958,"derived_artifact_credit":0,"direct_net":80982,"estimated_tokens_saved":80982,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1405,"response_debit":13461,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3890},"plan":{"calls":129,"content_source_credit":662278,"derived_artifact_credit":3246,"direct_net":384307,"estimated_tokens_saved":384307,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":18367,"response_debit":270128,"source_credit_count":45,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7278},"review":{"calls":124,"content_source_credit":1228787,"derived_artifact_credit":3535,"direct_net":930715,"estimated_tokens_saved":930715,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16152,"response_debit":288522,"source_credit_count":73,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3067}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":284,"content_source_credit":1983023,"derived_artifact_credit":6781,"direct_net":1396004,"estimated_tokens_saved":1396004,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":35924,"response_debit":572111,"source_credit_count":130,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":14235},"wave_id":"20tzs upgrade-recovery-edge-case-follow-ups"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 13 | 0 | 8 | 5,800,452 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":8,"estimated_exploration_avoided":5800452,"surfaced_events":13} -->
<!-- wave:exploration-avoided end -->
## Progress Log

Readiness: isolated standard red-team primer, six required lanes and targeted docs-contract council seat; one AC-3 plan finding repaired once and independently cleared by fresh QA/security contexts. Strongest alternative, removing read-back, was rejected because it loses verification. Source edits start only after successful Prepare.

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Planned the four source-confirmed follow-ups as one bug change. Use bounded existing-format repairs rather than superficial line substitutions or a new recovery framework. | Current-source anchors and two disposable controls; code unchanged |

## Review checkpoints

Readiness used an isolated standard red-team primer, six required lane contexts and the targeted docs-contract council seat. One AC-3 plan finding received one bounded amendment and fresh QA/security verification. Receipt-only bookkeeping rebinding preserved the original review judgments; it did not create another review round.

Delivery approved code, QA, security, architecture, release and docs-contract with no findings. Actual targeted council participants were red-team and docs-contract, with council-chair synthesis; no five-seat roster ran. The docs lane and council seat were the same reviewer. The strongest challenge was preserving descriptor-based ownership through read-back and failed rollback/checkpoint publication; current tests and mutants support the bounded continuation. Dropping read-back or adding a sidecar was rejected.

QA independently ran 55 relevant tests and injected original-function mutants; code, security and chair detected same-hash replacement adoption; architecture/release exercised the incoming hook without an installed sibling; docs checked the emitted retained-validation reason. Current reviewed 11-path aggregate: `c0922b039d3f0319ad1bf99ad8cb21c7707f5712dba5225104571d8caebfa352`. Canonical focused qualification passed 509 tests / nine files / one existing skip. The first canonical full suite passed all 11,838 tests / 200 files / 12 existing skips in 845.377s, but the run withheld its receipt because the coordinator added this authored section during execution. Ledger and generated views validate; authored Review checkpoints are material to the repository guard. No source repair or further review is needed. All authored records are settled before the replacement qualification run; no green receipt is claimed until it completes successfully.

Native Windows sharing, OneDrive, WSL2 and reboot remain unqualified. Timing policy remains deferred. Some lane baselines were whole-module runs and code/QA saw the primer; these limits do not create native or independent-reference claims beyond their executed evidence. Raw logs/probes stay under `/private/tmp`; this wave/change and immutable ledger contain durable summaries. No evidence folder, receipt bypass, operator closure approval, commit or package was added.

## Qualification handoff

Both complete default runs passed all 11,838 tests / 200 files / 12 existing skips. The first run (845.377s) withheld its receipt because the coordinator added authored Review checkpoints during execution; the second (744.159s), after our records/gates settled, withheld it for concurrent changes to wave 20tpp in another session. No 20tzs or reviewed source path changed in the second run. No further run, other-session revert or timing adjustment was made. All implementation/review ACs are complete; the wave remains paused.

The operator then explicitly authorized: “You can override it since the other wave records are the only changes.” Accepted only the second run’s repository-state rejection for the two change docs, events.jsonl and wave.md under `20tpp tensorwell-workload-aware-client`. All 200 per-file results and 11,838 tests passed, with 12 existing skips; all 11 reviewed paths still match the delivery fingerprint, and the framework diff contains only the nine reviewed source/test files. The receipt now records `accepted_with_operator_exception`, the original exit 1 and rejection, the four waived paths and the operator authorization. Current `inputs_hash`: `e5e529674529010c4f27c96b66f66e26f04f3337e4b3a88acb33d85626f2e13b`. Raw second-run log SHA-256: `80d6f95c9fa2a7c6fe478732a50f127db9dc5b4680e1b59e2d2d5f3b6cf87234`. This is an explicit operator exception, not an unconditional runner pass; the original log is unchanged. No failed tests, framework changes, first-run coordination error, timing policy, future mutations or profile qualification are waived. Exact per-test qualification detail was not reconstructed from progress output. No additional suite, review round, closure, commit, push or package was performed.
