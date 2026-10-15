# Clarify and preserve the inference provider compatibility boundary

Change ID: `20qvr-enh model-dependency-integrity`
Change Status: `implemented`
Owner: Engineering
Status: implementing
Last verified: 2026-10-15
Wave: `20qvq artifact-integrity-provenance`

## Rationale

Wavefoundry consumes inference from Tensorwell and is moving toward other API providers whose model files it cannot access. Model-file acquisition and integrity belong to the provider. Wavefoundry must validate the inference contract and protect index compatibility without duplicating provider internals. Existing Tensorwell model-pair checks already cover much of this boundary; retain them and close only demonstrated gaps. The original change ID is retained for continuity; its former dependency-locking scope is removed.

## Requirements

1. Describe a clear ownership boundary: providers own model files, downloads and artifact integrity; Wavefoundry owns supported model/configuration compatibility, input/output validation and compatibility with its persisted indexes.
2. Reuse existing Tensorwell qualification and response checks. Derive affected paths from registered embedding and reranking consumers; make only changes needed to enforce the existing supported contract consistently.
3. Provider-backed inference must not require locally accessible weights, cache markers or local file hashes. Provider-reported identity is compatibility metadata, not proof of the provider's underlying files.
4. Match the supported embedding model identity/version, dimensions and preprocessing contract before using an existing semantic index. An incompatible embedding configuration must require the existing explicit rebuild/migration path; matching dimensions alone are insufficient.
5. Validate supported reranker and response contracts independently of embedding-space compatibility. Refuse malformed/incompatible results without publishing partial incompatible index data or silently changing embedding spaces.
6. Preserve existing local/bundled model checks and current fallback behavior. Do not expand local download management, remove local fallback or implement a new external API adapter in this wave.
7. Document the same ownership principle for future API adapters without building a generic provider registry or inventing metadata requirements that arbitrary APIs cannot meet. A future adapter needs its own explicit supported identity and compatibility mapping.

## Scope

In scope: a source-grounded boundary description, existing provider contract regression coverage and minimal demonstrated fixes in current routes.
Out of scope: dependency hash locks, release signing/attestation, new release gates, build-identity machinery, new API integrations, removal of local models, timing investigation and framework provider selection policy.

The remaining direct-download cache attestation is non-blocking today. Enforcement of that legacy route is explicitly deferred, not claimed fixed by provider compatibility. Existing offline bundle verification must not regress. Wave 20qvt owns framework/distribution selection, adapter dispatch, startup, fallback visibility and provider-use reporting.

## Acceptance Criteria

- [x] AC-1: Documentation assigns model-file integrity to the provider and compatibility/index validation to Wavefoundry, accurately distinguishing service-reported identity from file verification.
- [x] AC-2: Current registered provider inference succeeds with a compatible service and no accessible local model files; the exercised path does not add local file verification or model loading.
- [x] AC-3: Targeted controls reject incompatible embedding identity/preprocessing or dimensions before incompatible index use/publication; compatible identities retain existing behavior.
- [x] AC-4: Reranker and malformed-response controls preserve supported behavior and refuse invalid results without silently changing embedding spaces or publishing incompatible partial data.
- [x] AC-5: Existing local/bundled verification controls remain valid, and guidance explicitly identifies the unchanged direct-download attestation limitation.

## Implementation contract

Reuse tensorwell_client._qualified_pair/_descriptor and _Adapter._operation for identity, dimensions, order, finite-value and complete-result checks. Reuse indexer._identity_fingerprint_for_class and existing index compatibility refusal; do not introduce another model hash or change a fingerprint for documentation alone. The source-backed gap to verify is setup_index.prewarm_models: it currently provisions local models before _prewarm_gpu_accel checks the resident provider. Setup must skip local provisioning only for a qualified matching workload, retaining current unavailable-service behavior. Existing select_embedder/select_reranker APIs remain unchanged in this wave.

Tests use isolated service descriptors and traps on local model loading/downloads, never the installed service. Exercise setup/prewarm and registered inference consumers, plus incompatible/changed descriptor and late-invalid-response controls. Existing test_tensorwell_client cases already cover many negative contracts and should be reused.

## Tasks

- [x] Inventory existing provider qualification, response validation and index identity checks through registered consumers; record covered behavior and demonstrated gaps.
- [x] Add only missing boundary controls and regression coverage; reuse existing checks rather than adding a second validation layer.
- [x] Update embedding architecture and threat-model ownership guidance; cross-reference the separate provider-policy wave.
- [x] Run focused provider/index compatibility and existing bundle-verification tests; record durable results in wave.md.
- [x] Complete readiness before source edits and required delivery review before requesting closure.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Contract and minimal repairs | Implementer | Readiness | Single writer; reuse current checks |
| Verification | QA and required reviewers | Implementation | Read-only review; coordinator records evidence |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/tensorwell_client.py`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/architecture/embedding-model.md`
- `docs/architecture/threat-model.md`

Implementer owns minimal in-scope fixes and documentation; reviewers remain read-only. Protect model-bundle verification, publication guards, existing index identity and lazy fallback. Serialize shared-file edits with wave 20qvt. No new seed or generated surface edit is anticipated; name any necessary canonical guidance target during Prepare before editing it.

## Affected Architecture Docs

Update `docs/architecture/embedding-model.md` and `docs/architecture/threat-model.md` to describe the provider boundary and current direct-download limitation.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Accurate ownership contract |
| AC-2 | required | No dependency on inaccessible weights |
| AC-3 | required | Preserve embedding-space compatibility |
| AC-4 | required | Validate provider results |
| AC-5 | required | Honest transition and no regression |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Implemented per-model service/precision eligibility in initial provisioning and later native warmup; existing descriptors, response checks, fingerprints and bundle verifier unchanged. Provider and legacy-download boundaries documented. | setup_index._resident_setup_embedder; architecture embedding/threat-model |
| 2026-10-15 | Focused tests: Tensorwell integration23, bundle29, index compatibility19 passed. Setup203: 201 passed in sandbox; two mocked bootstrap temp-file permission failures passed with required filesystem access (no install). Existing client27 baseline remains applicable to unchanged client. | unittest modules test_tensorwell_integration, test_model_bundle, test_index_compatibility, test_setup_index; baseline test_tensorwell_client |
| 2026-10-15 | Four in-memory mutants detected: remove service bypass; remove precision guard; grant unsupported model; skip native INT8 preparation. Each named test failed by assertion, no skips/errors. | test_setup_and_optional_downloads_avoid_native_construction; test_initial_provisioning_preserves_mixed_and_ineligible_workloads; test_native_prewarm_preserves_int8_eligibility |
| 2026-10-15 | Readback: skip local provisioning only when the selected service matches the model and indexer precision; preserve local fallback, existing response/index guards and offline bundle verification. Before: compatible service setup still warms local weights. After: that eligible workload bypasses local provisioning. Change setup_index, focused tests and embedding/threat-model docs only; no model registry or fingerprint change. | Readied plan AC1–5; current setup/indexer source |
| 2026-10-15 | Replanned to the operator's simpler provider-owned model boundary; implementation not begun | Requirements and ACs above |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Reuse current provider checks and repair only demonstrated compatibility gaps | Model files are owned by the inference provider and may be inaccessible | Expand local integrity infrastructure: invests in a boundary being externalized. Trust every provider response without compatibility checks: risks invalid results and index mismatch. |
| 2026-10-15 | Remove dependency-locking and release-signing work from this wave | Independent concerns add substantial scope without serving this provider boundary | Combine all acquisition/release concerns: increases review and maintenance overhead. |
| 2026-10-15 | Preserve existing direct-model support while deferring its attestation enforcement | Provider migration does not itself remove or repair the current local path | Silently claim the local issue resolved: inaccurate; remove fallback now: unrequested behavior change. |

## Open Decisions

No new operator policy decision for this narrowed scope. Prepare confirms the existing supported compatibility fields and actual gaps. Wave 20qvt implements the decided automatic Tensorwell default and distribution disable/replacement seam.

## Risks

| Risk | Mitigation |
| --- | --- |
| Overengineering a future API contract | Limit implementation to existing routes; future providers receive explicit adapter qualification. |
| Reimplementing existing checks | Inventory coverage first and accept documentation/test-only work where behavior already satisfies the contract. |
| Confusing compatibility with authenticity | Label service identity as reported and leave file integrity with the provider. |
| Duplicate work with 20qvt | This wave owns compatibility; 20qvt owns selection, adapter dispatch, startup and reporting. |
