# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-15
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20qvq artifact-integrity-provenance`
Title: Inference Provider Compatibility Boundary

## Objective

Keep model-file integrity with the inference provider and validate supported inference and index compatibility in Wavefoundry. Reuse existing checks and repair only demonstrated gaps; no expanded local model-management or release-security infrastructure.

## Changes

Change ID: `20qvr-enh model-dependency-integrity`
Change Status: `implemented`


## Participants

- Coordinator: Coordinator
- Write-owning roles: Implementer after readiness; coordinator owns lifecycle records
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer

Completed At: 2026-10-15

## Wave Summary

Wave `20qvq` (Inference Provider Compatibility Boundary) delivered one change: Clarify and preserve the inference provider compatibility boundary.

**Changes delivered:**

- **Clarify and preserve the inference provider compatibility boundary** (`20qvr-enh model-dependency-integrity`) — 5 ACs completed. Key decisions: Reuse current provider checks and repair only demonstrated compatibility gaps; Remove dependency-locking and release-signing work from this wave
## Watchpoints

- Planning only. Resolve admitted open decisions before readiness. Preserve protected publication and recovery behavior; do not copy private intake material into tracked artifacts. Timing investigation stays deferred.

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
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
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
| plan | 69 | 694,212 |
| implement | 112 | 737,999 |
| review | 7 | 49,108 |
| **Total** | **188** | **1,481,319** |

<!-- wave:context-efficiency-state {"generation":173,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":112,"content_source_credit":1055066,"derived_artifact_credit":0,"direct_net":737999,"estimated_tokens_saved":737999,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3620,"response_debit":316373,"source_credit_count":41,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2926},"plan":{"calls":69,"content_source_credit":845334,"derived_artifact_credit":4143,"direct_net":694212,"estimated_tokens_saved":694212,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":18889,"response_debit":140181,"source_credit_count":53,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":7,"content_source_credit":55370,"derived_artifact_credit":0,"direct_net":49108,"estimated_tokens_saved":49108,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":123,"response_debit":9206,"source_credit_count":1,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3067}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":188,"content_source_credit":1955770,"derived_artifact_credit":4143,"direct_net":1481319,"estimated_tokens_saved":1481319,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":22632,"response_debit":465760,"source_credit_count":95,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9798},"wave_id":"20qvq artifact-integrity-provenance"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 17 | 0 | 15 | 6,621,459 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":15,"estimated_exploration_avoided":6621459,"surfaced_events":17} -->
<!-- wave:exploration-avoided end -->
## Current assumptions

Four cohesive waves avoid a single large approval boundary and the overhead of one wave per small item. Shared framework files are implemented serially; planning does not open an implementation slot.

## Outputs produced or expected

Admitted change plans, focused regression coverage, updated canonical guidance and a concise durable result in this wave record. No permanent raw probe/evidence folders are planned.

## Review checkpoints

Delivery: code, QA, architecture and security approved in one disclosed fresh independent context (`qvq-delivery-fresh-20261015-root-qvq_delivery`). The reviewer independently derived the workload and same-dimension/changed-identity controls from the AC and consumer contract: 37 positive checks passed without skips, and three focused in-memory mutants failed the intended assertions (bypass removed, precision guard removed, reported identity ignored). Eight reviewed path hashes were unchanged; no findings. Required AC1–5 reconciled. Aggregate qualification remains pending.

Durable test anchors: `.wavefoundry/framework/scripts/tests/test_tensorwell_integration.py` (`IntegrationTests.test_failed_incremental_build_preserves_published_vectors_and_file_meta`, `test_registered_query_raw_prefix_precision_and_rerank`, `test_native_prewarm_preserves_int8_eligibility`), `.wavefoundry/framework/scripts/tests/test_tensorwell_client.py` (`ClientTests.test_pair_rejects_partial_identity_dimensions_provider_precision`, `test_invalid_response_count_index_dimension_finite_and_identity`), and `.wavefoundry/framework/scripts/tests/test_model_bundle.py`. No live model/service, enterprise equivalence or native Windows qualification; online attestation enforcement, signing and hash locks remain explicitly deferred.

Prepare verifies decisions and exact affected surfaces before implementation. Delivery checks registered behavior, negative controls and compatibility. Reuse valid framework qualification; consolidate a necessary suite run after code changes settle rather than repeating it for bookkeeping.

## Completion criteria

Every admitted AC and task is reconciled with evidence, required delivery lanes approve, documentation validates and the operator authorizes closure.

## Handoff or next-wave notes

Readied; implementation waits for the current upgrade wave to pause. Prioritize upgrade correctness and distribution activation scope. The provider compatibility plan is narrowed; wave 20qvt separately implements framework-level selection and a downstream adapter seam. No release or external publication is authorized by this plan.

## Scope revision — 2026-10-15

The operator selected the simpler provider-owned model boundary. The single remaining admitted change retains its original ID for continuity. Release provenance change `20qvs-enh release-provenance-verification` was removed to docs/plans and deferred. Dependency hash-locking and direct-download attestation enforcement are also deferred; neither is claimed resolved. Release signing, new release gates and per-commit version machinery are outside this wave.

Wave 20qvt owns framework/distribution selection, downstream adapter dispatch, startup and provider-use reporting. This wave owns compatibility and its documented trust boundary. No new external API adapter or generic provider registry is included.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Operator authorized Prepare, review and implementation; closure/commit/release remain unrequested. Coordinator integrates serial source changes; independent role contexts review. Inherited capable model chosen for cross-module reasoning; actual runtime model/effort not exposed. | Current task; canonical lifecycle prompts |
| 2026-10-15 | Baseline test_tensorwell_client: 27 passed in 2.665s using isolated fixtures; sandbox-only loopback bind errors cleared by authorized test execution. No installed service contacted. | unittest discover -s .wavefoundry/framework/scripts/tests -p test_tensorwell_client.py |

## Readiness outcome

2026-10-15: Prepare passed after independent architecture, security, QA and code approvals plus council synthesis. Full isolated red-team primer; fixed architecture/security/QA/reality seats and rotating code seat. Unanimous, no blocking findings. The strongest alternative was the smallest per-model provisioning guard, conditioned on the same predicted precision as indexing; a blanket service-ready bypass was rejected. Existing later GPU warmup tests do not cover initial provisioning. Delivery must exercise that initial path, mixed models and INT8 controls. Source/AST feasibility review only; no live service or unimplemented behavior claimed. Typed events retain review authority; no separate evidence folder.

## Implementation results

Initial setup provisioning and later native warmup now use the same per-model service eligibility and indexer precision. Qualified full-precision workloads skip local weights; mixed/unsupported, disabled/unavailable and INT8 workloads preserve local preparation. Model/index identities and bundle verification are unchanged. Architecture docs distinguish provider-owned artifact integrity from compatibility, and explicitly retain the deferred non-blocking online attestation limitation.

Focused integration23, bundle29 and index-compatibility19 tests passed. Setup203 had two sandbox temp-file restrictions; both mocked-bootstrap tests passed when rerun with access, with no dependency installation. Four named in-memory guard mutants failed as intended. No installed service, model download or native qualification used. Canonical aggregate suite and independent delivery review remain pending after all waves settle.

Memory retrospective: bounded `memory_propose(mode="dry_run")` returned no eligible draft. Durable repair/provider contracts are already in the current implementation, tests and canonical guidance; no additional memory file or raw evidence folder was created.

## Final qualification

2026-10-15: canonical `run_tests.py` passed 11,731 tests across 189 files, with 12 skips, in 796.576 seconds. Fresh green receipt recorded after all source repairs and review-record writes settled; no repository writes during the run. Earlier census failures are repaired, and previously failing or timed-out files passed. Full docs validation passed before qualification. Required delivery reviews approve; wave remains paused for operator closure. No close, commit, push, package or release performed. Timing investigation remains deferred; no threshold or waiver changed.

Closure reconciliation (2026-10-15): operator authorized closure, commit and push; close verified current green qualification and required review authority. No package or release requested. Only wave.md, admitted change documents and authoritative events.jsonl are retained in this wave folder; no disposable evidence artifacts were present. Prior paused/pending notes above describe earlier checkpoints.
