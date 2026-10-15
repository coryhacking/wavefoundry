# Declare framework inference providers and downstream API adapters

Change ID: `20qvu-enh repository-inference-policy`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-15
Wave: `20qvt inference-provider-policy`

## Rationale

Framework distributions need to select their inference integration independently of target repositories. Keep automatic Tensorwell discovery and bounded startup as the default, while allowing downstream distributions to disable it or supply an adapter for an enterprise-hosted inference API. The original change ID is retained for continuity; no repository setting is introduced.

## Requirements

1. Add a framework/distribution-owned provider declaration using the existing extension conventions. With the shipped declaration, retain automatic Tensorwell discovery and bounded MCP-lifespan startup. Do not add per-repository consent or provider-selection settings.
2. A distribution can disable Tensorwell use and startup, retaining the existing local fallback, or explicitly replace it with its own provider adapter. Replacement must not implicitly contact or start Tensorwell. Preserve existing explicit runtime disable controls and document precedence.
3. Define the smallest adapter contract needed for embedding and reranking: capability/compatibility description, inference operations, bounded failure outcomes and provider identity for existing diagnostics. Reuse current adapters where possible; avoid a plugin marketplace, dynamic package installation or automatic discovery of arbitrary modules.
4. The distribution owns its enterprise endpoint, transport, authentication and model files. Wavefoundry consumes the declared adapter without requiring access to weights or local model hashes. Do not record credentials or request contents in status, index metadata or review evidence. No enterprise endpoint is enabled or contacted by the shipped default.
5. Derive integration coverage from all current framework embedding and reranking consumers, including serving, indexing/setup and memory routes. Apply the selected declaration consistently and reuse the compatibility/index contract from wave 20qvq.
6. When the selected compatible provider serves a workload, do not eagerly construct that workload's local model. Declare capability and fallback behavior explicitly, including partial embedding/reranking support. A failed selected request must not silently retry another provider or change embedding space; preserve existing safe failure semantics.
7. Reuse status and index provenance fields to distinguish availability, selected provider, actual provider and fallback reason. Disabling Tensorwell never stops its shared operator-owned daemon. Third-party adapters do not gain daemon lifecycle ownership merely by implementing inference.

## Scope

In scope: framework declaration, narrow downstream adapter seam, existing-route integration, status reuse, bounded fixture tests and author guidance. A synthetic enterprise adapter proves that downstream code can supply its own API without modifying core consumers.

Out of scope: implementing a particular enterprise API, choosing enterprise hardware or credentials, making live enterprise requests, per-repository settings, provider marketplaces, dependency installation, model-file management, release execution and timing investigation.

Wave 20qvq owns model/index compatibility and the provider integrity boundary. This wave owns framework selection, adapter dispatch and startup/reporting. Serialize overlapping source edits.

## Acceptance Criteria

- [x] AC-1: With no distribution override, current automatic Tensorwell behavior remains; a disable declaration prevents both use and startup and preserves the existing eligible local fallback. Repository configuration cannot override this framework declaration.
- [x] AC-2: A downstream fixture adapter supplies embeddings and reranking through current registered consumers without modifying their core implementations, accessing local weights or starting/contacting Tensorwell. Tests derive consumer coverage from the shared inference entry points.
- [x] AC-3: Compatible external inference avoids eager local model construction; partial capabilities, unavailable providers and incompatible identities follow explicit documented behavior without silent cross-provider retries or embedding-space changes.
- [x] AC-4: Malformed declarations and adapter responses fail safely, calls use bounded execution semantics, and public diagnostics distinguish actual provider/fallback without credentials or request text.
- [x] AC-5: Disabling/replacing Tensorwell leaves a shared daemon running; existing Tensorwell compatibility controls remain valid. Adapter documentation states ownership, precedence, capabilities and limitations, including that enterprise fixture qualification is not native enterprise-hardware qualification.

## Implementation contract for readiness

Use new stdlib-only inference_profile.py declarations and an inference_provider.py selection facade, not MCP tool overrides: setup and indexer must use the same provider outside the server. Declare shipped automatic Tensorwell, explicit local-only, or one explicitly named downstream Python adapter module/factory. Validate module names and shape; no discovery/import based on repository input. The profile exposes a selector with tensorwell (shipped), local and extension values plus a flat declared module name for extension mode. Reuse the existing declared-helper inventory for extension source provenance/pack inclusion; validate it before loading. The factory receives a finite deadline and returns a descriptor plus embedding/reranking callables. Prepare reviewers verify the final signature against current consumers before approving.

An adapter supplies selected embedding/reranking model objects implementing the operations existing consumers use, plus explicit model name, precision class, compatibility fingerprint and provider label. The downstream mapping must agree with the distribution's existing pinned index model identity; another model requires its own explicit migration, not a dimensions-only substitution. Selection and inference receive finite deadline/budget information; the trusted adapter must enforce it in its transport. This is an extension contract, not a sandbox capable of stopping arbitrary trusted Python code. The reference fixture demonstrates a compliant timeout and safe surfaced failure; no unbounded automatic retry is introduced. The first enterprise contract requires both declared embedding and reranking capabilities; an incomplete or unavailable extension is refused explicitly rather than silently selecting Tensorwell or a local model. The shipped Tensorwell mode retains its existing compatible local fallback on selection failure. Once selected, operation failure surfaces instead of silently retrying another backend. This keeps fallback policy small and deterministic.

The concrete extension entry is a declared `create_provider(*, deadline)` factory (deadline is an absolute `time.monotonic()` value). It returns a mapping with a safe public provider label, embedding and reranking descriptors, and two callables: `embed(texts, *, role, deadline)` and `rerank(query, texts, *, deadline)`. Descriptors identify the configured model, task, precision class, compatibility fingerprint, and embedding dimensions; the query/document role assigns prefix/preprocessing responsibility to the adapter exactly once. Each operation returns its descriptor and ordered results, so the facade validates current identity, cardinality, dimensions and finite values before exposing any output. Reranking results must be the pinned model’s raw logits, without sigmoid, normalization or rank-only conversion; the adapter preserves that calibrated preprocessing and score scale across batches. Public-consumer fixtures check raw scores -4.01, -4, 0 and a positive score against the memory cutoff and exactly one sigmoid in normal search, including multiple batches and original input order. The facade wraps this narrow transport contract in existing `embed`, `embed_query` and `rerank` consumer methods. Invalid or exceptional extension output becomes a bounded, path/secret-free provider failure; do not include arbitrary exception text. No local or Tensorwell fallback is permitted for an explicitly selected extension. A distribution may implement batching inside the deadline; the core adds no retry policy.

For explicit extension mode, precision prediction and actual selection must use the same declared, validated provider compatibility class, including on a CPU-only host. Preserve the existing index compatibility gate for a stored different class; selecting a full-precision API never silently converts an existing INT8 index. Default Tensorwell and local modes retain their existing host-based precision policy. Query selection remains constrained by stored layer precision, and mixed stored classes must refuse external selection rather than silently construct a local replacement. Readiness must verify the minimal integration against `_predicted_precision_class`, `_get_embedder_inner`, `WaveIndex._get_embedder`, `_embed_query`, reranking, setup/prewarming and memory consumers. A synthetic CPU-host/full-provider fixture must prove consistent comparison, publication metadata and query selection without importing local model runtimes for inference.

Preserve Tensorwell's current transport and startup machinery behind the facade. Dispatch startup only for the Tensorwell default; an enterprise service is externally managed in this version. Reuse current observation fields and register the profile/adapter in the existing source identity/reload and pack dependency inventories so a changed declaration cannot leave stale routing alive. Tests must prove fresh process and reload behavior, with no enterprise network or credential access.

## Tasks

- [x] Inventory existing declaration conventions and all embedding/reranking entry points; specify the minimal adapter interface, precedence and bounded execution mechanism during Prepare.
- [x] Implement the framework declaration with unchanged shipped Tensorwell defaults and explicit disable/replacement behavior.
- [x] Route existing consumers through the selected adapter while reusing compatibility, lazy loading and failure semantics.
- [x] Add a synthetic downstream API adapter and targeted positive/negative registered-path tests; reuse status/provenance fields.
- [x] Document downstream adapter authoring and ownership boundaries; record actual qualification and limitations in wave.md.
- [x] Complete readiness before source edits and required delivery review before closure.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation and guidance | Implementer | Readiness | Single write owner; serialize shared files |
| Verification and review | QA and required reviewers | Implementation | Read-only review; coordinator records evidence |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/inference_profile.py`
- `.wavefoundry/framework/scripts/inference_provider.py`
- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/tensorwell_client.py`
- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/`
- `docs/architecture/embedding-model.md`

Write ownership: implementer owns admitted behavior and its derived callers/tests. Canonical seed edits precede regeneration; do not hand-patch generated surfaces. Reviewers are read-only. Protect publication guards, recovery checkpoints, unrelated user hooks/docs, secrets and existing evidence; no historical ledger rewrites. Confirm exact seed/config edits during Prepare before opening gates.

## Affected Architecture Docs

Update `docs/architecture/embedding-model.md` and `docs/architecture/data-and-control-flow.md`; document the distribution declaration and adapter contract in the existing extension guidance. Confirm exact canonical guidance and declaration paths during Prepare.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Preserve defaults and distribution control |
| AC-2 | required | Demonstrate the requested enterprise extension seam |
| AC-3 | required | Preserve memory and index correctness |
| AC-4 | required | Bounded, truthful operation |
| AC-5 | required | Ownership and usable documentation |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Implemented AC-1–5: distribution profile/facade, all existing inference consumers, CPU/full publication compatibility, bounded safe adapter contract, cached selection, provider telemetry, exact-source routing reload and declared helper provenance. Nine synthetic adapter tests pass; Tensorwell integration 23, extension inventory 229, reload closure 15, setup readiness 49, readiness integration 20 and package seams 31 pass. Full suite and independent delivery review remain coordinator-owned and pending. | test_inference_provider.py; /private/tmp/qvt-provider-final.log, qvt-tensorwell-final.log, qvt-extensions.log, qvt-structure-final.log, qvt-readiness.log, qvt-readiness-integration.log, qvt-package-seams.log |
| 2026-10-15 | Guard mutation evidence: eight isolated source mutants each caused a named test failure, not an incidental import error. Response descriptor, cardinality, vector dimension, finite-number and completion-deadline guards: test_response_guards_and_timeout_are_safe_no_retry. Stored-precision guard: test_explicit_selection_never_falls_back_for_partial_or_incompatible. Helper-declaration and stale-generation guards: test_selection_cache_and_generation_invalidation. | /private/tmp/qvt-mutants.log; mutants run on temporary copies only |
| 2026-10-15 | Qualification limits: synthetic transports only; no live enterprise/Tensorwell endpoint, native model/hardware, credentials, model downloads or performance qualification. Trusted adapters must enforce transport deadlines; Python code is not sandboxed. Model pins stay bound to the loaded index runtime; profile/facade reload executes exact bytes and refreshes only matching pre/post source hashes. No close, commit, push or package build. | Registered pre/post index_health stale-code check and profile/helper reload fixture; required delivery task remains open |
| 2026-10-15 | Readback: implement AC-1–5 with distribution-owned automatic Tensorwell/local/explicit adapter selection, shared inference facade, safe deadlines/results and existing precision gates. Before: every consumer selects Tensorwell directly. After: declared enterprise inference serves matching full-class indexes on CPU without local construction; unavailable explicit adapters fail. No repository policy, service lifecycle ownership or live enterprise qualification. | inference_profile.py, inference_provider.py; setup/indexer/server consumers; declaration/reload inventory; tests and architecture/extension guidance |
| 2026-10-15 | QVT-RD1 bounded readiness repair: made existing raw-logit units, stable batching and public cutoff/calibration fixtures explicit; no provider policy change. | Typed repair_start precedes this amendment; focused verification pending |
| 2026-10-15 | Replanned after operator selected framework defaults and downstream API substitution; no implementation | Requirements and ACs above |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Keep Tensorwell automatic by default; declare selection at framework/distribution level | Operator explicitly rejected per-repository provider settings | Repository opt-in/opt-out: wrong ownership scope. Environment-only configuration: insufficient downstream integration contract. |
| 2026-10-15 | Add a narrow adapter seam for downstream enterprise APIs | Downstream must be able to replace Tensorwell without forking every consumer | Boolean disable alone: cannot deliver replacement integration. Full plugin system: unnecessary complexity. |

## Open Decisions

No unresolved operator decision on defaults or configuration ownership. Prepare must verify the proposed declaration, adapter signature, capability/fallback precedence and trusted-adapter timeout contract against current source before implementation. Enterprise endpoint and credentials belong to the downstream implementation and are not needed to test this seam.

## Risks

| Risk | Mitigation |
| --- | --- |
| Adapter seam grows into a general plugin framework | Support only existing embedding/reranking operations and explicit framework declarations. |
| A trusted adapter ignores its deadline | Document the adapter responsibility, verify the fixture transport honors the total budget, and avoid claiming a sandbox or termination guarantee for arbitrary Python extensions. |
| Fallback changes embedding space or loads unnecessary models | Reuse 20qvq compatibility checks and explicit per-workload capability/failure semantics. |
| Enterprise credentials leak into diagnostics | Keep secrets in downstream configuration and test public outputs with synthetic sentinel credentials. |
| Duplicate compatibility work | Keep 20qvq as contract owner and serialize shared edits. |
