# Report inference availability, execution and local residency

Change ID: `20np4-enh inference-provider-observability`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-14
Wave: `20np5 inference-provider-status`

## Rationale

Operators need to distinguish a compatible Tensorwell service from actual service use and from models still held inside the MCP process. wf_server_info_response currently exposes tensorwell_client.status_snapshot, a cached discovery summary. Its qualified_pair reason means the last successful readiness/descriptor check matched both pinned models; it is not execution evidence. Selection may still use local inference for precision or policy reasons, and prior local fallback sessions are not evicted when service selection succeeds.

Deliver additive, inexpensive process-scoped diagnostics through the existing wf_server_info surface. Make those distinctions readable without constructing models, running inference or changing routing. This is an additional wave requested separately from qualification and distribution repairs.

## Requirements

1. Separate observed Tensorwell availability/compatibility from execution history. Report not-checked, ready-compatible, unavailable, incompatible and policy-disabled states as applicable, with last-observed time and explicit stale/unknown information. Preserve existing fields for compatibility; explain qualified_pair in human-readable text as both pinned models compatible at the last check.
2. Report actual execution separately for each MCP inference role: query embedding, normal search reranking and memory reranking. Derive the instrumented set from the production dispatch paths for those roles. Include last attempted provider/outcome and last successful provider/time; distinguish selected-but-not-executed, failed and successful operations. A discovery result alone cannot populate success.
3. Preserve the reason for local selection or retrieval degradation, including policy opt-out, index precision mismatch, incompatible service and inference failure. Do not label local routing as CPU-only: the in-process provider may use CoreML or another supported accelerator. A failed selected service operation must not imply an unperformed local retry.
4. Report framework-owned local model residency independently of the latest provider choice, covering embedding, normal reranker and memory reranker caches/sessions in the observed MCP process. Distinguish loaded, not-loaded and unknown where ownership cannot establish a result; do not infer absence from Tensorwell availability or Python RSS. Account for shared model objects and reload-held references without double counting or false eviction claims.
5. Scope every observation to the reporting process/lifetime, with defined startup/reload reset or preservation semantics and safe concurrent snapshots. MCP status must not claim to describe separate indexing workers, other MCP servers or native daemon memory. Child-process/host-wide aggregation is out of scope; clearly label its absence.
6. Status reads use bounded in-memory observations and short critical sections only. They must not probe the service, start it, construct/unload a model, run inference, wait on ongoing inference, download, write durable telemetry, or schedule new polling. Record constant-size state per inference role/model; no request history, prompt text, credentials, account names or absolute discovery paths.
7. Preserve model qualification, precision, scoring, provider selection, error recovery and startup ownership behavior. Document the additive status schema and examples in the MCP contract and embedding architecture; status is diagnostic, not an execution attestation or proof of physical accelerator use.

## Scope

**In scope:** Tensorwell discovery status observations, the MCP provider-selection/execution/cache boundaries, additive wf_server_info response fields, bounded regression controls and operator documentation.

**Out of scope:** Model eviction or memory reclamation, changing provider preferences, service installation, new model qualification, broad timing/call-count analytics, persistent telemetry, an active health-probe command, dashboard transport/UI redesign, and cross-process indexing/daemon aggregation. The first reporting surface is the existing MCP status tool; future UI consumers can use the same schema without redefining its meaning.

## Acceptance Criteria

- [x] AC-1: A compatible-but-unused service reports compatibility with no fabricated successful inference; stale and never-checked observations remain distinguishable through the registered status tool.
- [x] AC-2: Controlled executions for each supported role distinguish successful Tensorwell use, successful in-process use, selection without execution and failed/degraded operations, retaining the correct last-successful observation and reason.
- [x] AC-3: A local model retained after switching to Tensorwell remains reported as locally loaded; fresh service-only and unknown-ownership cases never fabricate local residency or absence.
- [x] AC-4: Reading status during discovery/inference and after reload does not trigger model/service work, block on inference or expose another process's state as current; bounded observations have explicit lifetime/freshness semantics.
- [x] AC-5: Existing routing, qualification, score handling and recovery controls remain unchanged, legacy status fields remain usable, and status payloads contain no request text, credential or discovery-path data.
- [x] AC-6: MCP contract and embedding documentation explain compatibility, actual provider, local residency, fallback reasons and process scope in plain language, including the exact meaning and limits of qualified_pair.

## Tasks

- [x] Inventory selection, execution and model ownership paths for all three MCP roles; define the additive schema and lifecycle semantics.
- [x] Implement bounded availability/execution observations and truthful ownership-based residency reporting without changing routing.
- [x] Exercise registered status responses with service/local/failure/stale/reload/concurrency controls and traps for status-triggered inference or construction.
- [x] Update canonical contract/architecture docs and retain only final results and limitations in wave.md.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Status contract and implementation | implementer | Readiness approval | Sole writer of shared client/server files |
| Independent review | code, QA and architecture reviewers | Reviewable implementation | Read-only; verify observation versus execution claims |
| Boundary and overhead review | security and performance reviewers | Reviewable implementation | Read-only; inspect bounded state, privacy and hot-path cost |

## Serialization Points

Serialize shared server_impl and review-related changes with the distribution repair wave. Only the implementer writes source after readiness; reviewers are read-only and the coordinator owns lifecycle records. No seed, hook, workflow-config or generated prompt edit is planned. Exact additional implementation files require scope reconciliation before edits. The registry contract test and handler digest fixture are included for the changed wf_server_info contract; refresh only reviewed changed handler entries after the shared distribution handlers settle, preserving the docstring mutation assertion and all unchanged digests.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/tensorwell_client.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/wf_server/memory_handlers.py`
- `.wavefoundry/framework/scripts/accel_embedder.py`
- `.wavefoundry/framework/scripts/tests/test_tensorwell_client.py`
- `.wavefoundry/framework/scripts/tests/test_tensorwell_integration.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_mcp_tool_registry.py`
- `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/embedding-model.md`
- `docs/architecture/search-architecture.md`

## Affected Architecture Docs

docs/specs/mcp-tool-surface.md owns the additive wf_server_info contract. docs/architecture/embedding-model.md explains service compatibility, actual use and resident fallback models; docs/architecture/search-architecture.md explains per-role observation and degradation. No dashboard data path or new storage owner is introduced.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Availability must not be mistaken for actual use. |
| AC-2 | required | Actual execution is the operator's primary routing question. |
| AC-3 | required | Memory-management decisions require truthful local residency. |
| AC-4 | required | Observation must remain cheap, non-invasive and process-scoped. |
| AC-5 | required | Diagnostics cannot alter inference behavior or leak payloads. |
| AC-6 | required | Operators must understand the fields without internal terminology. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-14 | Planned from source inspection and a live wf_server_info response; no implementation or readiness approval. | tensorwell_client._descriptor, _qualified_pair, status_snapshot; wf_server_info_response and WaveIndex provider-selection methods. |

| 2026-10-14 | Thought: Independent readiness chair is orienting on the additive process-local status contract while the preceding wave qualifies. Current available reasoning model retained for concurrency/ownership analysis; full primer depth covers data-path and cross-cutting observation boundaries. | Required code/QA/architecture/docs-contract/performance/security remits will be explicit, with isolated council seats and bounded source/in-memory controls. No live service probing, model work, new polling or full suite for readiness. |
| 2026-10-14 | Observe: Named memory_handlers.py as a review target because the memory reranking caller validates actual operation results there. This reconciles the implementation owner with the existing three-role requirement. | Readiness seats reviewed the caller seam; no expansion to other processes or inference roles. |

| 2026-10-14 | Readback: Add cached process-local availability, actual execution and independently observed local residency to wf_server_info for query embedding, search reranking and memory reranking. A compatible unused service will still say no successful use; a retained local model remains loaded after service selection. Preserve routing, precision, scoring and recovery; status performs no service/model work. | AC-1–AC-6; admitted client/server/memory/accel owners, three test modules and contract/architecture docs. Short metadata locks and epoch/sequence ordering bound state; reload-held references make absence unknown. |

| 2026-10-14 | Inventory complete: three execution roles, four fixed weak ownership slots, availability separate from selection/provider return/caller acceptance, ordered last attempt and last accepted success. PID and reload epoch prevent old completion publication; reload-held references preserve positive residency while absence becomes unknown. | Actual client, WaveIndex embedding/search rerank and memory caller-validation paths inventoried. Observation-start timestamp is not OS process birth. Implementation and regression checks in progress. |

| 2026-10-14 | Additive implementation controls: 43 expanded client/integration tests pass, no skips (8.084 s). Registered wf_server_info completed with inference/probe/model-build locks held and discovery/HTTP/CLI/start/selection/attempt traps untouched. Contract and architecture explain compatibility, actual acceptance, local ownership, process scope and accelerator-label limits. | Local controlled fixtures only; initial sandbox socket denials rerun with local fixture permission. Actual reload and mutation controls pending; no canonical qualification or delivery approval yet. |

| 2026-10-14 | Controlled implementation verification complete: provider tests 44 passed, server tools 391 passed, final isolated deltas 3 passed, all zero skips. Seven copied-source mutants detected by named assertions: epoch, attempt ordering, accepted-success, unknown ownership, weak ownership, detached snapshot and caller acceptance. | test_reload_keeps_weak_ownership_but_invalidates_attempts; test_attempt_order_success_provenance_and_detached_snapshots; test_ownership_is_bounded_shared_and_does_not_keep_models_alive; test_provider_return_rejected_by_each_rerank_caller_preserves_success. Actual registered status/reload paths exercised; full combined qualification and independent delivery pending. |

| 2026-10-14 | Delivery found PROVIDER-DEL-SELECTION-REASON: an expired compatibility cache plus competing discovery selects a retained local model while inheriting qualified_pair from the previous check. AC-2 and AC-6 reopened for per-invocation reason repair. Added the existing registry test and digest fixture to Serialization Points for required handler-contract maintenance; no routing or schema authority expansion. | Independent registered-path probe with unchanged two-second deadline; six focused tests and five mutants otherwise passed. Combined default: 11,658 tests / 187 files / 12 skips, red; provider 44 and server-tools 391 passed. |

| 2026-10-14 | Repair cycle 1 now carries bounded invocation-owned reasons through unchanged selector return APIs. All three getters retain their own reasons under default-deadline contention and overlapping outcomes; compatibility remains an independent cached observation. Provider 47, targeted 4 and retrieval 8 tests passed with zero skips; both reason mutants were rejected in all three roles. | Existing test_tensorwell_client.py and test_tensorwell_integration.py controls; registry docstring mutation retained, only wf_server_info pin updated. Docs validation and diff checks passed. AC-2/AC-6 remain open pending fresh independent verification; source paused for distribution repair. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-14 | Separate bounded availability, execution and residency observations on existing MCP status. | Answers both routing and local-memory questions without new runtime work or a reporting subsystem. | Rename qualified_pair only: remains ambiguous about execution/residency. Probe/infer on every status poll: adds latency, loads models and changes the state being observed. |
| 2026-10-14 | Keep observations process-local and unknown states explicit. | Ownership can support this contract without global process discovery or durable per-request records. | Host-wide aggregation and dashboard transport: separate ownership/lifetime design with unnecessary scope for this first reporting change. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Availability or a selected adapter is labelled successful use | Update execution observations at actual success/failure boundaries and retain distinct selection state. |
| Model references survive reload or share underlying sessions | Define ownership limits; report unknown when references cannot establish absence and do not claim physical memory release. |
| Concurrent operations produce contradictory status | Short synchronized updates, explicit timestamps/lifetime and deterministic completion semantics. |
| Observability adds hot-path work or private data | Fixed-size metadata only, no persistent event stream, no text/credential fields and no status-triggered I/O. |

## Session Handoff

Planned only. Prepare and independent readiness review precede code changes. Keep evidence in this change, wave.md and typed events; no permanent evidence folder. Existing qualification and release requirements remain unchanged.
