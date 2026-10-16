# Skip local probes for service indexing

Change ID: `20st9-bug skip-local-probes-for-service-indexing`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-10-16
Wave: `20st8 index-build-provider-provenance`

## Rationale

Setup should use a compatible inference service without constructing local models to assess an unused provider. The operator requested this repair together with child-process execution reporting in one new wave. Preserve framework-level provider selection and local fallback; batching is outside scope.

`setup_index.main` calls `prewarm_models`, then unconditionally calls `report_embedding_provider_decision`. The helpers skip service-eligible workloads, but this intervening diagnostic runs the local ONNX probe. It may construct CPU/CoreML models unnecessarily. If it selects CPU, its inherited selected-provider environment value can make the indexing child reject a previously qualified Tensorwell service. The existing service-only setup test covers the helpers, not this main-path sequence.

A bounded diagnostic using actual selection code and simulated probe outcomes reproduced unnecessary probing and the failed CoreML probe → CPU selection → service refusal sequence. No native model was constructed or project index modified. This confirms a control-flow defect, not that the operator's successful rebuild fell back locally.

## Requirements

1. Derive local preparation needs from the models actually required by the requested build, their supported service mappings and the existing precision-compatibility rule. Apply this rule to initial provisioning, provider probing and native warmup; do not maintain another hardcoded model list.
2. When every required embedding model is service-eligible and qualified, omit local embedding probes and constructors. Distinguish service selection from local-provider diagnostics. Reuse existing bounded qualification where possible; add no inference requests just to decide readiness.
3. Mixed workloads prepare/probe local models only where needed. Automatic local CPU fallback for uncovered work must not itself disqualify covered service work. Explicit provider policy, unavailable/incompatible service, unsupported models and INT8 compatibility retain their authority.
4. Preserve these rules in the actual child environment. A parent's readiness is not proof of later execution. Service disappearance before child selection retains supported local-selection behavior; an operation that fails after service selection must not silently retry locally.
5. Preserve model pins, compatibility fingerprints, download deadlines, startup ownership and extension contracts. Do not force re-embedding or change precision to satisfy this repair.

## Scope

**In scope:** setup main-path preparation, inherited automatic provider decisions, necessary shared selection adjustments, regression controls and accurate operator guidance.

**Out of scope:** batching/limits, timing targets, new provider APIs or repository settings, model eviction, daemon lifecycle, diagnostic downloads/rebuilds, and release fixture repairs in wave 20st7.

## Acceptance Criteria

- [x] AC-1: A setup main-path regression with all required embedding models service-eligible reaches indexing without local embedding probes or constructors; an unused local probe cannot set CPU policy and disqualify the service.
- [x] AC-2: Mixed workloads prepare only uncovered local work and retain service selection for covered models. Disabled/unavailable service, explicit local policy, unsupported models and INT8 controls retain expected local behavior.
- [x] AC-3: Parent-to-child controls preserve selection and compatibility; a selected service-operation failure remains visible without hidden local retry. Preparation/selection messages are not represented as accepted child execution.
- [x] AC-4: The change's own tests pass and its edited documents validate; bounded regression evidence demonstrates the main-path failure before repair and the corrected behavior after it without real downloads or project-index mutation.

## Tasks

- [x] Trace required models through real setup, standalone and MCP child launch paths before local-policy side effects.
- [x] Repair preparation/probe dispatch and inherited automatic decisions using existing service and precision rules.
- [x] Add main-path, child-environment and mixed/local controls; preserve existing negative and failed-publication assertions.
- [x] Update operator guidance and embedding architecture; record results in wave.md and share settled-tree qualification with the sibling change.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Selection repair | implementer | readiness | Precedes sibling reporting integration. |
| Verification | qa-reviewer | repair | Independent read-only checks at review. |

## Serialization Points

Serialize shared setup/indexer, test and documentation writes with 20tt3. The implementer owns writes after successful Prepare; reviewer lanes inspect and report findings.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/provider_policy.py`
- `.wavefoundry/framework/scripts/inference_provider.py`
- `.wavefoundry/framework/scripts/tensorwell_client.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_tensorwell_integration.py`
- `.wavefoundry/framework/scripts/tests/test_inference_provider.py`
- `.wavefoundry/framework/README.md`
- `docs/architecture/embedding-model.md`

The root `CHANGELOG.md` will receive a concise behavior note during implementation. No seed, hook/config or generated prompt edits are intended. Preserve unrelated packaging stamps and wave records.

## Affected Architecture Docs

- `docs/architecture/embedding-model.md`: describe service-aware preparation and local fallback through setup's main path, not only helper behavior.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes unnecessary construction and accidental service disqualification. |
| AC-2 | required | Preserves mixed and local-only support. |
| AC-3 | required | Protects child policy and explicit failures. |
| AC-4 | required | Demonstrates the admitted repair. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-16 | Final canonical qualification passed11,892 tests/200 files with12 existing skips in730.325s and wrote a current green receipt. All admitted ACs/tasks and independent delivery reviews are complete. Earlier failed executions remain historical evidence; none was waived. | /private/tmp/20st8-close-canonical-suite.log; framework test-cache.json matching current inputs. |
| 2026-10-16 | Main/child and mixed-policy repair implemented, focused suites passed and all required delivery lanes approved. Documentation and shared settled-tree test evidence are complete. The final canonical run passed every test file; concurrent planning edits prevented a formal green receipt for the wave. | Existing setup/integration/client/provider tests; wave.md final verification and typed ledger. |
| 2026-10-16 | Readback: service-covered setup must reach indexing without unused local probes/constructors; mixed/local/INT8 work keeps preparation and explicit policy. Before: a failed unused local CoreML probe can set inherited CPU policy and disable qualified service selection. After: only necessary local preparation runs and cannot itself disable covered service work. Expected edits: setup_index/provider-policy selection and existing setup/integration tests. AC-1–4; no batching, model pin or publication changes. | Readied receipt review-policy-7554fda61d41a64cdb7d; successful Prepare and Implement. |
| 2026-10-16 | Planned from current source and bounded diagnostics; no code edits or readiness approval. | `setup_index.main`, `report_embedding_provider_decision`, `tensorwell_client._policy_reason`; temporary diagnostic under /private/tmp. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-16 | Select workload-aware omission of unused local probes using existing selection rules. | Fixes the cause while retaining local fallback where needed. | Relabel the banner only: leaves construction and CPU side effects. Remove all local probes: loses useful validation for mixed, unsupported and local-only work. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Local policy for one model suppresses another model's service selection. | Exercise mixed workloads and inherited child environment, not just helpers. |
| Service availability changes before the child runs. | Preserve bounded selection and explicit failures; sibling reporting observes execution. |

## Session Handoff

See `docs/agents/session-handoff.md`. Planned only; successful Prepare remains required before code edits.
