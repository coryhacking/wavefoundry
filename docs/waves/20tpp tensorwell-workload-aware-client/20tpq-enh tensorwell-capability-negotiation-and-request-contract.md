# Negotiate Tensorwell capabilities and send workload, deadline and session hints

Change ID: `20tpq-enh tensorwell-capability-negotiation-and-request-contract`
Change Status: `implementing`
Owner: Engineering
Status: implementing
Last verified: 2026-10-16
Wave: `20tpp tensorwell-workload-aware-client`

## Rationale

Tensorwell is adding a workload-aware and client-aware service contract: an authenticated capabilities endpoint, a `workload` field that separates interactive queries from batch indexing, a negotiable request deadline up to 300000 ms, a per-client-session scheduling hint and optional timing metadata. The Wavefoundry client in `tensorwell_client.py` predates all of it. It discovers only `/health/ready` and `/v1/models`, sends every request with a 30000 ms ceiling, runs a whole `embed()` call over many HTTP requests under one 30 s operation deadline, never says which workload it is, and sends no session hint. That is wrong for indexing, where one request can legitimately need minutes on a CPU profile, and it leaves the service unable to tell a user query from a bulk reindex.

The operator has deployed the current client nowhere but this machine and has decided not to keep backward compatibility with the pre-capabilities service shape. On 2026-10-16 the local adaptive API was observed ready, with capabilities schema_version 2 and stats schema_version 3. Its nested capabilities document is rejected by the provisional flat parser. The same contract check found nested response timing. This revision aligns the already-admitted change with that deployed wire contract before live acceptance; earlier fixture qualification remains historical evidence, not evidence that the deployed API is usable.

## Requirements

1. **Capability negotiation against the deployed contract.** After the existing consistent endpoint/token snapshot, discovery reads authenticated `/v1/capabilities`, `/v1/models` and `/health/ready` on the same instance. Support the real nested `schema_version: 1` normal-service and `schema_version: 2` adaptive-service envelopes. Replace the provisional flat capability fixture and parser; retain no flat-wire alias or pre-capabilities fallback. Consume `limits.max_items`, `limits.max_body_bytes`, `limits.max_text_bytes`, `timeouts.max_ms`, `workloads.supported`, `timing.request_flag`, `timing.unit`, `timing.rounding`, and the schema-2 `client_session` advertisement. Wire-to-internal normalization preserves the existing adapter and cached status contract: `schema_version` maps to internal `schema`, `timeouts.max_ms` to `max_timeout_ms`, `limits.max_text_bytes` to `max_input_bytes`, the other consumed limits retain their internal names, and the supported session advertisement maps to `client_session_hint`. Validate object containers before fields; numeric limits are JSON ints, timeout is in [1000, 300000], size/item limits are positive, and every effective bound is the lesser of the local and advertised value. `workloads.supported` is a list of at most 8 strings containing both `interactive` and `batch`. Timing advertisement must identify `include_timing`, `milliseconds` and `floor`, matching the request/response fields this client uses. Schema 1 sends no session hint; schema 2 requires the supported session declaration in requirement 4. Informational scheduling, adaptive-policy, connection and native-profile-batch fields neither raise local limits nor change profile selection or concurrency. A 404, unsupported schema, missing consumed field, malformed container or out-of-range value remains `capabilities_unsupported`, availability `incompatible`, with no inference request and the existing local selection route. Negotiated capabilities remain bound to the instance and are re-read only on instance change or after rejection; ordinary same-instance cache refresh performs no new capabilities GET. Keep the existing discovery deadline and safe HTTP/instance checks.
2. **Workload classification, derived in the adapter.** Every embedding and reranking request carries `workload` explicitly, and the value is derived from the adapter entry point, never passed by callers: `embed()` is `batch`, `embed_query()` and `rerank()` are `interactive`. This applies to both `tensorwell_client._Adapter` and `inference_provider._Adapter`, so the four real wire call sites (`indexer._embed_texts`, `WaveIndex._embed_query`, `WaveIndex._agent_rerank` and `_rerank`, and the memory reranking in `memory_handlers`) need no edits and no caller can omit or misspell the value. Setup is not a call site: its qualification samples embed through a local fastembed model in a probe child and only select the adapter to skip prewarming. The extension `create_provider` callback contract from wave `20qvt` is unchanged (`embed(texts, *, role, deadline)` and `rerank(query, texts, *, deadline)`); `workload` stops at the facade and is not forwarded, so existing extension adapters and the committed fixture keep loading. `workload` never selects a profile or extends a deadline on its own.
3. **Per-request deadlines.** The service deadline is set per HTTP request, not per `embed()` call. Interactive requests use the lesser of 30000 ms and negotiated `timeouts.max_ms`; batch requests use the lesser of 300000 ms and that maximum. Normalize that field once; existing internal deadline calculations stay unchanged. The HTTP watchdog uses the service deadline plus the fixed 10 s delivery margin and the connection timeout remains `DISCOVERY_SECONDS` (2 s). `timeout_ms` on the wire equals the service deadline. One wall-clock operation deadline bounds each adapter call: interactive is its effective service deadline plus margin (at most 40 s); batch is request count times that amount, with the existing per-request attempt cap from `20tpr`. Size the final payload with workload, timing opt-in and timeout present; keep 32-item batch requests and existing 128-item/1 MiB interactive ceilings, all further clamped by negotiated limits. All bounds remain module constants. A result completing at or after the operation deadline, including response validation and success-lock admission, is rejected without success accounting or a local-model retry.
4. **One session hint per process.** Schema 2 advertises an object `client_session` with `header: "Client-Session-Id"`, `format: "uuid-shaped-ascii-8-4-4-4-12-hex"`, `optional: true` and `authentication: false`; validate these supported values rather than inventing a wire `client_session_hint` boolean or using a service-provided header name. An absent/malformed/incompatible schema-2 declaration refuses capability qualification. Schema 1 has no session extension and sends no header. When supported, every request, retry and post-rediscovery request carries exactly one fixed `Client-Session-Id` header with one lowercase random UUID allocated per Wavefoundry process on first use. Keep its existing reload retention and PID-change reallocation, never derive it from credentials or rotate it to gain capacity, and keep it out of adapter attributes, logs, status, records, exceptions and diagnostics. The existing normalized status booleans may report advertised/in-use only; the hint is not authentication.
5. **Nested timing metadata.** Requests still send `include_timing: true`. The deployed response is `metadata: {"workload": ..., "timing": {"queue_ms": ..., "execution_ms": ..., "total_ms": ...}}`. Validate metadata and timing as objects, require workload to match the request, and require each timing value to be a JSON int in [0, 2^31). Read only the nested timing values; a flat provisional timing block is not an alternate wire format. Retain the existing normalized per-role timing observation shape so downstream callers do not change. Missing metadata remains tolerated; present but malformed metadata/timing is an invalid response, and no success is recorded before complete output validation and the final deadline check.
6. **Preserved contract.** Raw text plus `role` with the query prefix applied exactly once by the service; aligned raw logits in document order; count, order, 384 dimensions and finiteness checks; the pinned `arctic-fp16-coreml` and `minilm-fp16-coreml` descriptors; the model-set fingerprint pin; `WAVEFOUNDRY_DISABLE_TENSORWELL`, provider and reranker-disable controls; discovery safety rules (owner-only directory, literal loopback, bearer header only, no proxy, no redirect, instance identity on every response including capabilities). Profile selection and a second embedding model are out of scope.
7. **Platforms.** Selection policy is unchanged: macOS arm64 only. Windows, Linux and WSL2 hosts keep `unsupported_host` and local inference. Nothing here executes on those platforms.

## Scope

**Problem statement:** the client cannot negotiate the new service contract, classify its workloads, size deadlines per request or identify its session.

**In scope:**

- `tensorwell_client.py`: discovery, capability validation and caching, status-carrying HTTP exception, request construction and sizing, adapter-derived workload, per-request deadlines, session hint, timing validation
- `inference_provider.py`: adapter-derived workload in the facade adapter; the extension callback contract is untouched
- Focused regressions in `test_tensorwell_client.py` (including the rewrite of the 128-item chunking assertion to 32-item batches), `test_tensorwell_integration.py` and `test_inference_provider.py`, with a capabilities fixture carrying the pinned names
- `docs/architecture/embedding-model.md` (section Optional Tensorwell execution: capabilities, per-request deadlines, 32-item batching, session hint) and `docs/architecture/threat-model.md` (section Optional Tensorwell client: the session hint never enters diagnostics)

**Out of scope:**

- Failure-cause classification, retry, backpressure and reporting (change `20tpr`)
- Legacy service compatibility (operator decision: none required)
- Any change to the `20qvt` extension adapter contract or to call sites
- CPU INT8 or other profile selection, a second embedding model, index identity changes
- Any Tensorwell source, service start/stop behaviour, or new dependencies

## Acceptance Criteria

- [x] AC-1: Against a service-faithful fixture, actual nested schema_version 1 and 2 capabilities qualify the pinned pair, normalize negotiated limits and session support, and keep one capabilities GET per instance. A 404, unsupported version, missing/wrong-type nested object or consumed field, invalid timeout/item/text/body limit, unsupported timing declaration or malformed schema-2 session advertisement refuses qualification as capabilities_unsupported before inference. Provisional flat capabilities do not qualify; unrelated informational fields do not change bounds. Values above local bounds are clamped.
- [x] AC-2: The fake service observes `workload: "batch"` from an index build through `indexer._embed_texts` and `workload: "interactive"` from query embedding, search reranking (`_agent_rerank` and `_rerank`) and memory reranking, with no call-site edits; both adapters derive the value from the entry point; the extension fixture in `test_inference_provider.py` loads unchanged and its callbacks receive no `workload` argument.
- [x] AC-3: The real nested maximum controls request timeouts and operation ceilings without changing their existing deadline/late-output semantics. Interactive requests use min(30000, advertised maximum), batch uses min(300000, advertised maximum); each batch request has at most min(32, negotiated item limit), final serialized payload stays within negotiated byte/text bounds, and the watchdog/final validation guard rejects late output.
- [x] AC-4: The schema-2 client_session advertisement enables one stable UUID-shaped Client-Session-Id across both adapters, retries and consistent rediscovery; reload retains it and simulated PID change reallocates it. Schema 1 sends none. Malformed header/format/optional/authentication advertisements refuse qualification. All existing token/session privacy assertions remain in force.
- [x] AC-5: Service-shaped metadata.workload and metadata.timing queue_ms/execution_ms/total_ms are validated and normalized into existing per-role timing. Missing metadata is tolerated; malformed/nonnested timing, wrong workload, boolean/string/negative/nonfinite/out-of-range values reject success without replacing valid observations or escaping the operation deadline.
- [x] AC-6: Existing prefix-once, logit-alignment, dimension, descriptor-pin, fingerprint-pin, disable-control and discovery-safety tests pass unchanged; the two architecture docs describe the new behaviour.
- [x] AC-7: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Replace provisional capabilities and timing fixtures with the deployed nested schema_version 1/2 envelopes and metadata.timing response contract; ground fixtures in the service/OpenAPI contract and the observed local capabilities, not the existing parser.
- [x] Add the status-carrying HTTP exception, capability discovery, value validation and per-instance caching to `_qualified_pair`; classify 404/unsupported/malformed/out-of-range as `capabilities_unsupported` with state `incompatible`.
- [x] Derive `workload` from the entry point in both adapters; leave call sites and the extension callback contract untouched.
- [x] Move the deadline from the operation to the request, add the operation ceilings, the 10 s delivery margin, the 2 s connect timeout, the 32-item batch bound and the final-payload body sizing; keep all of them module constants.
- [x] Map the validated client_session declaration into the existing hint gate; retain reload/PID behavior and all privacy controls.
- [x] Read and validate metadata.timing, preserving the existing normalized per-role observations and final deadline guard.
- [x] Add or extend the fake-service tests for AC-1 to AC-5 (capabilities and header capture in the fixture), rewrite the chunking assertion, and run the existing Tensorwell suites.
- [x] Update `docs/architecture/embedding-model.md` and `docs/architecture/threat-model.md`.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Client contract | Implementer | Readiness | Single write owner of `tensorwell_client.py` for this change |
| Architecture docs | Implementer | Client contract | Two existing sections |
| Delivery review | QA, security, architecture, performance | Both | Read-only |

## Serialization Points

- `.wavefoundry/framework/scripts/tensorwell_client.py`
- `.wavefoundry/framework/scripts/inference_provider.py`
- `.wavefoundry/framework/scripts/tests/test_tensorwell_client.py`
- `.wavefoundry/framework/scripts/tests/test_tensorwell_integration.py`
- `.wavefoundry/framework/scripts/tests/test_inference_provider.py`
- `docs/architecture/embedding-model.md`
- `docs/architecture/threat-model.md`

Change `20tpr` edits the same client module after this change lands; one implementer owns the file across both.

## Affected Architecture Docs

`docs/architecture/embedding-model.md`, section Optional Tensorwell execution: capability negotiation, per-request deadlines and operation ceilings, 32-item batching, the session hint. `docs/architecture/threat-model.md`, section Optional Tensorwell client: the session hint and capability values are bounded and never enter diagnostics. `docs/architecture/cross-cutting-concerns.md` does not describe the client: N/A. The framework README and `docs/specs/mcp-tool-surface.md` are updated by change `20tpr`.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Nothing else is safe without negotiated, validated capabilities |
| AC-2 | required | The service schedules on workload |
| AC-3 | required | Indexing fails today under the 30 s ceiling on slow profiles |
| AC-4 | required | The adaptive candidate needs stable session identity |
| AC-5 | important | Observability input for the reporting change |
| AC-6 | required | Preservation of the qualified contract |
| AC-7 | required | Delivery gate |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Planned from the Tensorwell integration brief dated 2026-10-15 (consumer instructions section). Operator decision: no backward compatibility with the pre-capabilities service. | Brief; current `tensorwell_client.py` at commit `57f7cecc` |
| 2026-10-15 | Readiness repair in one round: setup was a phantom call site (its samples embed through local fastembed), and a mandatory caller keyword would have broken the `20qvt` extension contract and its fixture; workload is now derived from the adapter entry point. Added capability value validation and per-instance caching, operation ceilings, the connect-timeout change, final-payload sizing, reload and fork rules for the session hint, timing value bounds, and the architecture docs that actually describe the client. | Red-team RT-1/2/5/7/9/11, security SEC-4/6/7, code CODE-1 to CODE-7, QA-1 to QA-6, architecture ARCH-1/2/4/5/6, performance PERF-1/3, docs DOCS-1/3 |

| 2026-10-15 | Readback: negotiate the pinned capabilities on the same instance; derive batch from embed and interactive from embed_query/rerank; retain the extension callbacks unchanged. Before: every request uses a 30-second ceiling and omits workload/session/timing. After: 32-item batch requests have negotiated deadlines, interactive requests retain 30 seconds plus delivery margin, with process-stable optional session hints and validated timing. AC-1–7; tensorwell_client.py, inference_provider.py, existing client/integration/provider tests and two architecture sections. No live service or call-site edits. | Current approved Requirements and ACs; successful wf_implement_wave |

| 2026-10-15 | Facade derives workload at its entry points and converts it to the unchanged callback role. The committed synthetic callback fixture remains byte-for-byte unchanged and keeps its existing 30-second extension deadline contract. Focused canonical provider file: 11 tests / 0 skips passed. A post-bootstrap in-memory mutant classifying embed as interactive fails the new named test with one assertion failure and no errors. Initial pre-bootstrap mutation was discarded by server fixture reload and was not counted as detection. | test_facade_derives_workload_without_changing_extension_callbacks; focused provider run |

| 2026-10-15 | Client and facade contract tests, real indexing/query/search/memory call-site workload checks, and corrected service stats envelope pass together: canonical focused 82 tests / 3 files / 0 skips in 12.988s. Eight client guard mutants plus the post-bootstrap facade classification mutant are detected by named tests. A stale-X failure cannot deselect newly qualified instance Y; response timing commits only after full result validation. Interactive deadlines respect a smaller advertised maximum under Requirement 1, with 30 seconds as the local ceiling. No live qualification or final receipt yet. | /private/tmp/20tpp-focused.log; client implementation packet and named regression controls |

| 2026-10-15 | Material implementation, docs and tests are frozen for one canonical default qualification. Earlier canonical focused group: 82 tests / 3 files / 0 skips passed; final client-only diagnostic completion: 46 tests / 0 skips passed. Nine refreshed in-memory client mutants and the facade workload mutant are detected by named tests. Full suite is pending; live AC-6 remains unmet. | /private/tmp/20tpp-focused.log; /private/tmp/20tpp-client-implementation.json |

| 2026-10-15 | Frozen delivery QA and independent code review found that valid output crossing the operation deadline during validation returns success through embed, embed_query and rerank. The owning deadline AC is reopened until the bounded repair and fresh reverification. No source edit while remaining seats review. The first canonical attempt was deliberately stopped (exit 143), with its runner stdout identity and descendant ancestry verified; no owned test process remains. It produced no qualification or receipt. | Deterministic QA/code deadline probes; /private/tmp/20tpp-full-suite.log; finding pending typed normalization |

| 2026-10-15 | Cycle-1 repair checks the deadline after vector/timing validation and before success accounting. Late validation reports deadline_exceeded / response_validation, retains the qualified pair and releases admission slots. New regression covers 18 deterministic entry/seam/boundary combinations; deleted/loosened guards cause 12/6 assertion failures, zero errors. Fresh separate QA/code contexts cleared the exact issue; code independently checked 27 cases including status-lock admission. Corrected canonical focused group passes 84 tests / 3 files / 0 skips in 13.074s. All other nine reviewed paths are unchanged; framework gate closed. The final canonical suite follows on this frozen tree, and full QA/council authority remains withheld for live acceptance. | Existing test_tensorwell_client.py regression; /private/tmp/20tpp-deadline-repair-cycle-1.json; /private/tmp/20tpp-repaired-focused.log; repaired aggregate 81330376a7eda42ed72fdfda5480885b6a71bd34a97efdcb685c3ffac291e3ad |

| 2026-10-16 | Second canonical attempt was stopped deliberately (exit 143) after the registry module exposed the obsolete wf_server_info description pin; it is not qualification and wrote no receipt. Fresh separate QA/release contexts confirmed exactly one mismatch among 90 handler digests and unchanged executable AST. Typed repair_start cycle 2 preceded updating only that supporting fixture entry. Registry module now passes 27 tests / 0 skips; every prior reviewed path is unchanged. Fresh focused QA/release verify the pin and description-mutation control before qualification resumes. | test_mcp_tool_registry.py HandlerDigestTests; events.jsonl; frozen 12-path aggregate 114a298125bac63a3fe7758a4906e5099a1becd6df6ac2abefa6528460e639b2 |

| 2026-10-16 | Final canonical default qualification passed 11,862 tests / 200 files / 12 existing skips in 740.812s. Green receipt matches current framework inputs, and all 12 reviewed paths remain unchanged. D1 and D2 are independently reverified and terminal; six implemented-scope approvals are recorded. AC-7 is complete in both changes. Wave paused with 20tpr AC-6/live task and full QA/council approval still pending the deliberately selected deployed candidate; no close/commit/push/package. | inputs_hash 5cec243a19aa224dc3934a6a0dc5ebe4f9bf73d79a8a00bc860935ccd0ada239; /private/tmp/20tpp-qualified-suite.log; events.jsonl |

| 2026-10-16 | Reopened affected AC-1/3/4/5/6/7 and fixture/parser/session/timing/doc tasks for deployed-API reconciliation. AC-2 and completed workload/facade work remain unchanged. Local read-only probes returned ready, capabilities schema_version 2, matching pinned model descriptors and adaptive stats schema_version 3; actual client selection returned capabilities_unsupported before inference. No inference or source edits were performed. | Authenticated loopback GETs; Tensorwell service.rs capabilities route and timing response builder; workers.rs capabilities; docs/api.md and OpenAPI |

| 2026-10-16 | Readback: consume actual nested schema_version capabilities/client_session and metadata.timing, normalize nested load_count/null labels without changing internal status/callbacks or model/deadline/privacy boundaries. Before: ready local service is rejected as capabilities_unsupported. After: the real pair qualifies and returns validated embedding/reranking results. Single client/test owner; coordinator integration/docs owner. Current focused readiness approvals recorded and prepare/open succeeded before framework edits. Live positive checks and isolated negative/recovery checks remain distinct. | Revised owning Requirements/ACs; review-policy-dfb1deaa01d9735b47f5; wf_prepare_wave/create and wf_implement_wave/create |

| 2026-10-16 | Revised API implementation passes producer-grounded controls: client 52/52 green, zero skips; nine guard mutants detected. Consumer/provider focus 37/37 green. Added healthy checkpoint-recovery leg after preserved failed epoch; integration 26/26 green with elapsed-backoff fixture and no local model factories. Real selected-candidate positives passed eight HTTP inference requests, nested timing/stats, prefix/session/privacy and batch-size comparison; results and limits are in wave.md Live Acceptance. Source frozen for fresh delivery review; full canonical suite follows once review settles. | Existing named client/integration tests; /private/tmp/20tpp-api-client-implementation.json; /private/tmp/20tpp-api-live-acceptance.json; /private/tmp/20tpp-api-recovery-integration.log; aggregate c5ed1347ca471a9076e8055bc7482c6e8baec6d13507aac7a3bd14e1cf77fde8 |

| 2026-10-16 | Revised API delivery complete: all required ACs/tasks verified, fresh focused review found no new actionable findings, all seven lane and council delivery approvals current. Canonical default passed 11,867 tests / 200 files / 12 existing skips in 756.863s; receipt matches current framework inputs and all twelve frozen hashes. Full docs validation passes. Wave paused for operator closure; no close/commit/push/package performed. API nominal checks are live; controlled faults/recovery are isolated as recorded. MCP reload succeeded, while setup assessment separately requests host restart; no setup/index rebuild was run. | inputs_hash 818020c3e26c974fbc93ff4c28c1b33645c808481522ac76ae98b8ad61f0479d; aggregate c5ed1347ca471a9076e8055bc7482c6e8baec6d13507aac7a3bd14e1cf77fde8; events.jsonl; /private/tmp/20tpp-api-canonical-suite.log |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Require capabilities; drop the legacy request shape | The client is deployed only on the operator's machine and Tensorwell ships capabilities with the candidate | Keep a 404 legacy branch (rejected: unreachable code to test and maintain) |
| 2026-10-15 | Derive `workload` from the adapter entry point; do not forward it to extension callbacks | Maps exactly onto the four real wire sites with zero call-site edits, keeps the published `20qvt` contract and makes omission impossible by construction | Mandatory caller keyword (rejected at readiness: breaks duck-typed local models, test doubles and the extension fixture); keyword on the service branch only (rejected: new branches in index and memory paths) |
| 2026-10-15 | One session UUID per process, allocated at first use, reload-retained, fork-reallocated | The MCP host exposes no session identity; one stdio transport is one client, which matches the service's definition | Per-tool-call IDs (rejected by the contract); a persisted ID across restarts (no benefit, more state) |
| 2026-10-15 | Deadline per request under one wall-clock operation ceiling (interactive 40 s; batch request count times 310 s); 300 s batch requests; 32-item batch requests | Matches the service's absolute deadline semantics, lets the delivery margin apply to interactive calls, and bounds a batch call in proportion to the work submitted | Keep one operation deadline (rejected: a long index build cannot fit); unbounded per-request retries (rejected: no ceiling) |

| 2026-10-16 | Replace the provisional flat wire contract with the deployed nested schema_version 1/2 contract and normalize into existing client fields | Smallest consumer-side change that uses the available API while preserving established internal behavior | Accept both flat/nested shapes (rejected: maintains an unused invented format); flatten Tensorwell (rejected: changes the provider and its real consumers) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Pinned names differ from Tensorwell's final check | Names live in one fixture and one request builder; rename is a bounded edit before the live checklist in `20tpr` |
| Tensorwell's candidate is not deployed when implementation finishes | Fake-service tests cover the contract; the wave pauses after review until the live checklist in `20tpr` runs |
| Session UUID leaks into diagnostics | AC-4 asserts absence from every status surface, exception text and captured output |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
