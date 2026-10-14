# Optional Tensorwell inference with bounded service startup

Change ID: `20njt-enh optional-tensorwell-inference`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-14
Wave: 20nju optional-tensorwell-inference

## Rationale

Use an installed, compatible Tensorwell service to share resident embedding and reranking models across Wavefoundry processes. At MCP startup, start the configured service if stopped without delaying MCP initialization. Preserve local inference when Tensorwell is absent, disabled, unsupported or incompatible. This is an optional execution backend for the pinned models, not a model migration.

Read-only discovery found installed Tensorwell 0.1.0 ready with `arctic-fp16-coreml` (384 dimensions) and `minilm-fp16-coreml`. Its canonical model-set-v3 manifest and Wavefoundry's model-set-verification-manifest.json have identical SHA-256 `22e19c0e4817d96f71882bd0c605a1bb9cbed8c957b2796ad92752d3e0250609`. Its API exposes immutable profile identities and ordered embeddings/raw reranking logits. This establishes an available candidate, not adapter numerical qualification. The API remains experimental and managed startup is currently macOS-only.

Source anchors: Wavefoundry `indexer._get_embedder_inner`, `WaveIndex._get_embedder`, `_embed_query`, `_get_reranker`, `accel_embedder.StaticShapeEmbedder` and `StaticShapeReranker`; Tensorwell `docs/api.md`, `crates/tensorwell-daemon/src/assets.rs`, `profile.rs` and `preprocess.rs` in its separate checkout. That checkout is read-only discovery input. MCP discovery reported stale loaded setup code; current-disk reads and installed CLI observations, not indexed summaries alone, ground this plan. No private downstream report is needed.

## Requirements

1. Default to optional automatic discovery. `WAVEFOUNDRY_DISABLE_TENSORWELL=1` disables use and automatic start. Never install Tensorwell, provision/download models, edit its configuration or change Wavefoundry's pins. Preserve explicit CPU/provider and reranker-disable controls. Initially require a compatible pinned embedding/reranking pair before service selection; a partial set keeps the local route.
2. Ship a narrow compatibility table of qualified full Tensorwell profile identity digests mapped to Wavefoundry's model-set fingerprint, model, preprocessing contract, dimensions and precision class. Independently derive/check entries against pinned artifacts and Tensorwell's identity construction, then qualify numerically. Never trust a digest learned from the service itself. Unknown identities, even with familiar names, remain unavailable. Pin the experimental API contract; runtime/provider identity changes need explicit qualification.
3. On actual MCP serving startup, schedule one background discovery/start attempt after transport initialization. Find the operator-installed CLI through controlled executable lookup excluding repository/current-directory entries. Run bounded read-only status first; if stopped/absent and supported, call `tensorwell start --json --no-menu` with its existing configuration. Use its own management lock/idempotence. Starting joins a bounded wait; Failed/unhealthy/unknown/incompatible live state reports fallback, without automatic restart. Imports, dry-run, status checks, test collection and reload never initiate a start.
4. Use a finite end-to-end startup budget, initially 30 seconds including CLI calls/polling and cancellation/reaping. MCP initialization, list-tools and non-inference tools remain responsive. On timeout, terminate and reap only the exact CLI child launched through the owned Popen handle; never signal a process group, descendant tree or PID obtained from discovery. Automatic start requires a qualified controller binary digest whose cancellation behavior matches this contract; unknown controllers allow read-only ready-service reuse only. Starting is observed read-only. Tensorwell retains its own native failed-start cleanup authority. Later bounded inference discovery can recognize eventual readiness without another start attempt in that MCP lifetime. Shutdown never stops Tensorwell. Multiple MCP processes converge through its single-instance management. Standalone setup/index processes reuse ready services but gain no automatic-start policy in this wave.
5. Add Wavefoundry-owned client/adapters covering docs/code builds, incremental builds, query embedding and reranking. Prefer compatible resident inference before local provider probes/session construction, including small batches. Do not load duplicate native sessions or trigger optional background model downloads merely because service inference was selected. Preserve canonical setup validation/provisioning and packaged local fallback dependencies.
6. Send raw text with explicit query/document roles: Tensorwell adds the query prefix, while the local path retains its current prefix handling. Preserve input/result order and raw reranking logits; apply existing sigmoid/ranking exactly once. Bound batches by serialized UTF-8 body bytes, item count and per-item limits. Never truncate text to fit transport limits. Validate response instance/model identity, counts, indices, dimensions and finite numbers. Handle empty arrays, Unicode and over-limit items explicitly.
7. Preserve model/precision compatibility and publication gates. Query selection follows the indexed layer's recorded precision; builds follow existing explicit provider/precision policy. Pin identity/precision per build/query operation. Compatible backend changes do not themselves require re-embedding. After service failure, discard unpublished partial output; local retry is allowed only under a qualified equivalent contract and the caller's total deadline. Otherwise use existing explicit semantic-unavailable/rebuild-required behavior, preserving the published index. No mixed vectors or mid-publication precision change.
8. Use bounded no-follow regular-file discovery with ownership/permission checks, following Tensorwell's endpoint-token-endpoint read protocol. Validate literal loopback URL, API and instance; disable proxies and redirects. Header-only authentication; at most one bounded rediscovery on connection/authentication races. Bound I/O, response size and parsing. Credentials, input text and raw service errors never enter logs/status. Discovery PIDs confer no process-control authority.
9. Report backend, compatible profiles and short startup/fallback reasons through existing server-info/health diagnostics. Cache contracts by instance/identity; invalidate on restart and back off after failures. Avoid per-call notices, repeated model hashing, new permanent evidence files or statistics polling. Do not claim physical GPU use from provider registration. Ordinary tests use isolated fixtures/opt-out; native numerical checks use bounded synthetic input.

## Scope

**In scope:** Optional service client, compatibility mapping, MCP startup integration, existing inference call paths, bounded fallback, focused verification and operator/architecture contracts. Initial native qualification targets installed macOS. CPU profiles are admitted only after their exact identities and numerical contracts qualify; otherwise they remain local.

**Out of scope:** Tensorwell source changes; new models; automatic installation/download/configuration; remote/cloud inference; dashboards/statistics polling; Windows/Linux service management; removing local dependencies; unrelated reload work; performance threshold decisions under concurrent machine load.

## Acceptance Criteria

- [x] AC-1: Contract fixtures accept a qualified pair and reject absent, disabled, partial, unknown-identity, wrong-dimension and precision-incompatible services without touching a real service.
- [x] AC-2: Registered MCP startup schedules bounded background start for a stopped configured installation and reuses a ready instance while initialization/non-inference tools remain available. Lifecycle tests cover Starting, failure, timeout, concurrent clients, eventual readiness, reload and dry-run without duplicate starts, configuration changes or stopping a shared daemon.
- [x] AC-3: Production indexing/query/reranking paths use selected adapters, preserve raw roles/order and avoid local session construction on the healthy service route. Registered-path tests cover query-prefix duplication, small builds and reranker opt-out.
- [x] AC-4: Synthetic parity against current local inference satisfies numerical and retrieval/ranking tolerances fixed before measurement for every admitted profile, including batch composition, Unicode, empty strings, long input and repeated calls. Evidence justifies existing-index compatibility; failing profiles remain ineligible.
- [x] AC-5: Restart, malformed output, overload, timeout and mid-build failure yield bounded equivalent fallback or explicit unavailability, with no partial/mixed-precision index publication, verified through index-state and response assertions.
- [x] AC-6: Security/transport controls reject unsafe discovery, non-loopback endpoints, redirects, proxy routing and identity races, enforce input/output bounds and keep credentials/request text out of diagnostics.
- [x] AC-7: Disabled/absent/unsupported-host paths preserve local inference without a Tensorwell dependency. Tests cover setup, indexing children and query callers; documentation explains startup, opt-out, compatibility and recovery.
- [x] AC-8: A bounded macOS integration check uses the installed matching service for synthetic embedding/reranking and records identities/results. Startup ownership is exercised in isolated fixtures; disruptive live lifecycle testing requires separate coordination. The record distinguishes simulated from native coverage and makes no unmeasured speed claim.

## Tasks

- [x] Freeze API/profile compatibility mappings and parity thresholds; census production embedding/reranking callers.
- [x] Implement bounded private discovery, authenticated transport, validation and inference adapters.
- [x] Integrate indexing/query/reranker selection, role handling and precision-preserving fallback.
- [x] Add once-per-serving-lifetime background startup and compact status diagnostics with reload/dry-run controls.
- [x] Add registered-path, lifecycle, security and publication tests; execute bounded synthetic parity for admitted profiles.
- [x] Update contracts/changelog and complete independent review and change-local verification before normal qualification/close gates.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Compatibility | implementer | — | Freeze identity and parity contract |
| Client and inference | implementer | Compatibility | One writer across indexing/query seams |
| Startup/status | implementer | Client and inference | Client owns no shared daemon lifetime |
| Verification | qa-reviewer, code-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer | Startup/status | Independent review through normal readiness/delivery workflows |

## Serialization Points

One implementer owns source edits; reviewers read only. No seed or generated host configuration edits are planned. Ordinary readiness and framework-edit gates apply.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/tensorwell_client.py`
- `.wavefoundry/framework/scripts/accel_embedder.py`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/run_tests.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/README.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/`

Root README/CHANGELOG document the optional backend. The model-set manifest remains read-only.

## Affected Architecture Docs

Update the owning contracts in `docs/ARCHITECTURE.md`, `docs/architecture/search-architecture.md`, `docs/architecture/embedding-model.md`, `docs/architecture/chunking-and-indexing-pipeline.md`, `docs/architecture/data-and-control-flow.md`, `docs/architecture/layering-rules.md`, `docs/architecture/threat-model.md` and `docs/architecture/testing-architecture.md` for inference ownership, startup, trust and verification. Cross-link rather than duplicate facts.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Availability alone is not compatibility |
| AC-2 | required | Requested startup without blocking MCP |
| AC-3 | required | Reach actual inference callers |
| AC-4 | required | Preserve vector/ranking semantics |
| AC-5 | required | Protect current indexes and bound failures |
| AC-6 | required | Credentials/source text cross a process boundary |
| AC-7 | required | Tensorwell remains optional |
| AC-8 | required | Verify more than mocked adapters |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-13 | Complete: all required ACs/tasks have evidence. Fresh focused verification cleared all six delivery findings; code, QA, architecture, docs-contract, performance, security and council-delivery approvals are recorded. Final canonical qualification passed 12,499 tests across 187 files with 12 reported skips on the unchanged reviewed tree. Both edit gates are closed. Ready for operator-owned closure; no commit, push or package was performed. | Green receipt `3eb074fae2e3949e83124ea7d50b89dcdb1ea01e83d432b3c82ae819141655ff`; all 29 reviewed Git blobs unchanged; `wave.md` review checkpoints and typed ledger; no AC deferrals or unresolved findings |
| 2026-10-13 | Observe: cycle-2 source frozen after all six repairs. Seven focused files passed 381 tests, no skips; both mocked-reranker cases also passed under the runner's disable setting. The final client assertions passed 20 tests. Actual registered reload preserves one pending worker/locks/status while refreshing source/pins and invalidating qualification. Late-batch failure preserves vector bytes, file metadata and precision. Framework edit gate closed for fresh focused review. | Source fingerprint `c54a85bb62e75375a2ad672f2a85e00a8a5de03008a48da0e7b76c30f0192131`; implementer-executed focused checks; canonical full qualification pending |
| 2026-10-13 | Guard landing: 14/14 repair mutants detected. Removing pending-pair, old-failure and initial/final operation generation checks fails `ClientTests.test_reload_generation_refuses_pending_publication_and_old_failure`; resetting startup-once/worker/locks/status/generation fails `IntegrationTests.test_registered_reload_refreshes_client_preserves_pending_start`. Loosening float32 range fails `test_float32_representability_in_actual_query_build_and_rerank`; unsafe local retry fails `test_failed_incremental_build_preserves_published_vectors_and_file_meta`. | Named tests in `test_tensorwell_client.py` and `test_tensorwell_integration.py`; removing the timeout exception fails `ClassificationTests.test_every_timed_call_is_routed_or_classified`, and removing builtin registration fails `HelperModuleDeclarationTests.test_the_framework_script_census_matches_the_scripts_directory`. Temporary mutation table `/private/tmp/20nju-cycle2-mutants.json`; no unexpected errors |
| 2026-10-13 | Act: all six delivery findings now have cycle-2 repair starts before edits. One implementation pass will preserve live startup state during client reload, validate finite float32 output, register the builtin module and owned-child wait exceptions, and correct the lifespan/reranker fixture prerequisites. No timing threshold or broader lifecycle contract changes are admitted. | Typed initial-delivery and repair-start records; fresh affected lanes will reverify after the source is frozen again |
| 2026-10-13 | Reflect: new-module integration must include the existing reload and builtin-module inventories, while exact-child timeout ownership needs its narrowly counted routing exception. Existing fixtures must opt into their mocked reranker and serialize data settings separately from the lifespan callback. Numeric validity must hold in the consumer's float32 domain, not only JSON/Python float. | Independent delivery findings and complete canonical run: 12,496 tests / 187 files / 12 skips, six failing files; exact full log `/private/tmp/20nju-full-suite-qualified.log`. Two TechDocs cases passed unchanged in isolation; their full-run cause remains unproven and no timing threshold was changed |
| 2026-10-13 | Observe: independent delivery checks found missing reload participation and a finite-JSON value that becomes nonfinite on float32 conversion; AC-2 and AC-6 reopened pending repair. Qualification also detected lifespan serialization and exact-child timeout census fixture gaps. A composed valid-batch/late-failure build preserved published vectors, file metadata and precision; its unsafe local-retry control was detected. | Current frozen-tree review; `ReloadClosureGuardTests`; `/private/tmp/20nju-security-float32.json`; `/private/tmp/20nju-qa-composed-results.json`; no source repair before consolidated findings and repair-start records |
| 2026-10-13 | Observe: implementation frozen; 40 focused tests passed (19 client, 6 integration, 15 runner), no skips. All 27 deliberately weakened guards were detected by named tests, including pins/pair/precision/provider, opt-out, private discovery, API/instance, JSON/transport bounds, response validation, one rediscovery and bounded startup. | `test_tensorwell_client.py`, `test_tensorwell_integration.py`, `test_run_tests_lock.py`; `/private/tmp/20nju-mutants.json` maps each mutant to its failing test; subprocess-isolation guard and `git diff --check` passed |
| 2026-10-13 | Thought: run canonical qualification and fresh independent delivery review against the frozen implementation. Full primer and architecture/security/QA/reality seats plus performance alternative address the local authenticated service, inference precision/publication and process ownership boundaries; supplemental code/docs lanes retain their own authority. | Reviewed-path hashes: `/private/tmp/20nju-delivery-fingerprint.json`; full suite `/private/tmp/20nju-full-suite.log`; requested capable workhorse at high reasoning for the chair and risk-matched independent reviewers; observed runtime identity unavailable |
| 2026-10-13 | Reusable native oracle passed through current production adapters after transport repairs: minimum cosine 0.9998404980, maximum raw-logit delta 0.0085492134, 63 ordering comparisons and top-1 preserved, repeated/singleton controls unchanged. Reference ordering margins were 0.1008–18.1878 and embedding top-1 margins 0.2967, 0.3009, 0.3734. Native discovery also caught and corrected the initial 32-character ID assumption; the actual API requires 64. | `.wavefoundry/framework/scripts/tests/oracle/tensorwell_parity.py`; tool-venv Python with `-B`, output `/private/tmp/20nju-native-oracle.json`; 120-second process bound, cached references, no service lifecycle or index mutation |
| 2026-10-13 | Readback: currently each process constructs local embedding/reranking sessions. After this change a qualified ready Tensorwell pair serves raw document/query text and raw rerank logits before local construction, even for a small update; absent/ineligible services keep local behavior. Only actual MCP serving schedules one bounded background start. Preserve model pins, indexed precision, CPU memory scoring and shared-service ownership. One implementer owns client, inference/startup integration and tests; coordinator owns documentation and native numerical qualification. AC-1 through AC-8 remain the verification boundary. | Implementation readback before source edits; readiness and framework edit gate still required |
| 2026-10-13 | Bounded readiness repair replaces waiter abandonment with exact owned-controller termination/reaping and qualified controller eligibility. The isolated three-cell check reproduced abandoned-controller delayed work and detected a group-signal mutant; no live service was signalled. | PERF-STARTUP-CONTROLLER cycle 1; /private/tmp/20nju-chair-controller-lifetime.py; focused review of receipt review-policy-0dc2f577b64430357fa5 |
| 2026-10-13 | Planned from current source, installed CLI read-only status and matching manifests; no inference/service mutation/source edits | Rationale discovery; planning-only operator request |
| 2026-10-13 | Preparation: code indexing uses the shared indexer, not a separate code_indexer.py. Test-worker opt-out belongs in run_tests.py; review targets corrected before approvals. Independent derivation reproduced both CoreML profile identities from pinned artifacts/runtime metadata without reading live service credentials. | /private/tmp/tensorwell-20nju-independent-identities.json; numerical qualification remains pending |
| 2026-10-13 | Readiness implementation notes under existing R4/AC2: timeout cancels/reaps only the exact owned Popen CLI controller; never use run_with_tree_kill, process-group signals or discovery PIDs. Qualify that controller behavior; unknown contracts retain read-only reuse but no automatic start. Tensorwell owns its native startup-failure cleanup. | Independent security subprocess control /private/tmp/20nju-security-cancel.py; reality reviewer confirmed this satisfies the existing ownership boundary |
| 2026-10-13 | Freeze numerical qualification before measurement: normalized embedding cosine at least 0.999 against local full-class inference and synthetic nearest-document ranking agreement; reranker maximum absolute raw-logit delta strictly below 0.05, with order preserved where local margins exceed 0.10. Report measured margins and batch/repetition deviations; failing profiles are not admitted. | AC-4; strict reranker bound follows existing test_reranker_fp16_matches_fp32_when_available; embedding bound is this wave's explicit qualification criterion, not prior proof |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-13 | Optional service with background startup and local fallback | Meets sharing/startup intent without mandatory dependency | Mandatory service breaks unprovisioned hosts; query-only routing leaves repeated indexing model loads |
| 2026-10-13 | Narrow qualified immutable-identity table | API digest includes artifacts/runtime/preprocessing | Name matching misses drift; extending Tensorwell's API adds another repository/dependency |
| 2026-10-13 | Start with existing configuration and no menu; never restart incompatible live service | Respect shared operator-owned state | Overriding profiles or restarting disrupts other consumers |

## Risks

| Risk | Mitigation |
| --- | --- |
| Experimental runtime/API identity changes | Unknown versions fall back locally pending qualification |
| Prefix/precision/tokenization differs despite matching weights | Explicit roles and predeclared parity oracles |
| Native startup outlives waiter | Bound and reap the exact qualified CLI controller; later discovery, no shared-process kill; Tensorwell owns native failure cleanup |
| Failure causes duplicate expensive model loads | Select service before construction; bounded fallback/backoff |
| Concurrent load confounds timing | No timing benchmark/threshold decision in scope |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
