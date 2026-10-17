# Preserve Tensorwell failure causes, bound retries and concurrency, and report capacity

Change ID: `20tpr-enh tensorwell-failure-causes-backpressure-and-reporting`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-16
Wave: `20tpp tensorwell-workload-aware-client`

## Rationale

The current client collapses every non-200 response other than 401 into one `unavailable response` error and every failure into the single reason `inference_unavailable`; rediscovery happens only for 401 and transport errors, and every other status fails outright. The new Tensorwell contract distinguishes bounded-capacity refusal (429 with `Retry-After`), an expired service deadline (504), a starting or stopping instance (503), request-contract errors (400, 404, 408, 413, 415) and credential mismatch (401), and it asks consumers to retry only overload and uncertain delivery, within a bounded budget, with reduced pressure, and never to hedge or fall back to a local model silently. It also publishes per-model capacity statistics and per-request timing that `wf_server_info` does not surface today. Without this change the operator cannot tell an overloaded service from a broken one, and a bulk reindex can hammer a service that just asked it to wait.

## Requirements

1. **Outcome classification.** Each HTTP outcome maps to a distinct, stable reason that status, diagnostics and the raised error carry: `overloaded` (429), `deadline_exceeded` (504), `service_unavailable` (503), `transport_uncertain` (timeout or disconnect after the request was sent), `invalid_request` (400), `unauthorized` (401), `model_not_found` (404), `request_timeout` (408), `payload_rejected` (413, 415) and `unexpected_response` (anything else). On a non-200 the body is read under the same `MAX_RESPONSE_BYTES` cap and `_json` parser as a success; the envelope `{"error":{"code","message","retryable"}}` is parsed when present, `message` is discarded after parsing and never retained or surfaced, `code` is kept only when it matches `[a-z_]{1,40}` and is one of the documented codes and is then preferred over the status mapping, and `retryable` must be a bool; a true `retryable` never authorises more attempts than the policy below. The reason on the exception, in `_status`, in `diagnostic["reason"]` and in the attempt record is always one of the enumerated tokens, never a service string; the exception message stays the fixed sentence plus the token. Safe diagnostics keep status, code and failure phase (discovery, capabilities, readiness, request, response validation) and never include input text, document bodies, tokens or the session hint. Only `transport_uncertain`, `service_unavailable`, `unauthorized` after its rediscovery and `unexpected_response` deselect the pair (`_failed`, 5 s backoff); contract errors and `overloaded` keep the pair qualified so one bad batch does not unqualify the service for every interactive caller.
2. **Bounded retry policy.** Retry waiting happens inside the adapter and never in parallel, and every wait checks the one wall-clock operation deadline from change `20tpq` (interactive 40 s in total, the service deadline plus margin; batch the request count times the per-request deadline plus margin). Per request, at most 4 attempts across all causes. `overloaded`: `Retry-After` is parsed as a non-negative integer of seconds only (an HTTP-date or unparsable value counts as absent); the wait is the parsed `Retry-After` value (or the floor when absent), clamped to at least 1 s and at most the lesser of 60 s and the remaining operation budget, plus jitter in [0, 1) s; if even the floor exceeds the remaining budget the attempt fails immediately with `overloaded` and no sleep; at most 3 retries. `transport_uncertain`: rediscover once; if the instance identity is unchanged and this batch's output is unpublished, retry once; a changed instance ends the operation. `deadline_exceeded`: no immediate or hedged retry; batch requests may retry once after a 2 s backoff with the same request, interactive requests fail. `service_unavailable`: recheck readiness after 1 s and then 2 s, at most twice, then fail. `invalid_request`, `model_not_found`, `request_timeout`, `payload_rejected` and `unexpected_response`: no retry. `unauthorized`: the existing single consistent rediscovery, no loop on a stale pair. The floor, ceiling, jitter range and backoff values are module constants so tests can patch them.
3. **Concurrency bounds.** At most one in-flight batch request per process, enforced with a lock in the client. Interactive requests share a small global in-process limit of 4 and never wait behind the batch lock. An interactive request that cannot acquire a slot within its own request deadline fails locally with `overloaded` without sending HTTP, and the slot wait counts against that deadline, so a stalled service cannot queue MCP tool calls without bound. More sessions or more UUIDs are never used to gain capacity.
4. **No silent fallback, unchanged.** After the policy above is exhausted the adapter raises `TensorwellUnavailable` carrying the reason; query paths keep their explicit lexical recovery, indexing discards unpublished output and requires retry, and no local model is constructed in response. Selecting Tensorwell never authorises a local fallback on busy or timeout.
5. **Capacity and timing reporting using the deployed envelopes.** Preserve the existing normalized `wf_server_info().data.tensorwell` keys: negotiated capabilities summary, per-role timing, fixed process-local counters, last readiness time and cached statistics. Capability normalization is owned by `20tpq`; this reporting path must not parse another capability wire dialect. `/v1/stats` uses `schema_version` 2 or 3 and a `models` array. Locate each pinned profile by `row.model.id`, independent of order; duplicate pinned IDs or missing required profile rows remain invalid. Read cumulative `load_count` from `row.model.load_count` and promote it to the existing cached per-profile `load_count` key. Other allow-listed numeric fields are at row level: configured_sessions, resident_sessions, ready_sessions, active_sessions, known_clients_active, known_clients_queued, unknown_active_requests and unknown_queued_requests; validate present values as JSON ints in [0, 2^53). The optional labels optional_state and suppression_reason may be missing or JSON null: omit the normalized key in either case, validate non-null strings against [a-z0-9_-]{1,64}, and never stringify null or discard an otherwise valid stats document for null. Drop unknown fields; do not copy the whole model descriptor or service policy state into diagnostics. In particular, the wire root suppression_reason is global policy data and is dropped, never copied into per-profile rows; only a label actually present on a row is eligible for the existing per-profile allow-list. Normalize nested response timing from `20tpq` without changing its cached per-role shape. The stats GET remains best-effort after qualification, once per cache window, with its own 1 s timeout outside interactive admission; failures/404/malformed documents do not unqualify inference and yield stats null plus invalid/absent reason. Status reads perform no HTTP. Preserve existing counter meanings: load_count is cumulative constructions, not residency; do not sum active/queued known-client counts. The registered docstring remains accurate without unrelated edits.
6. **Documentation.** The framework README section **Optional Tensorwell inference** describes workload classification, deadlines, the session hint, the retry policy and the new status fields in operator terms, and states that a pre-capabilities Tensorwell now falls to local inference with reason `capabilities_unsupported`. `docs/specs/mcp-tool-surface.md`, section Cached inference status, documents the new `data.tensorwell` fields and that status still performs no HTTP. `docs/architecture/embedding-model.md` records the outcome vocabulary and retry bounds; `docs/architecture/threat-model.md` records that error codes, stats values and `Retry-After` are bounded and the envelope message is discarded. `CHANGELOG.md` Unreleased gains one `### Changed` bullet covering both changes, ending `Wave 20tpp.`
7. **Bounded selected-candidate acceptance.** Before closure, verify real inference through the Wavefoundry client against the deliberately selected deployed candidate: supported capabilities and stable instance/model pins, query prefix applied exactly once, stable outbound session UUID, interactive 40-candidate reranking, explicit batch indexing with aligned deadlines, the 32-versus-128 request-size comparison, valid nested timing/cached stats, and telemetry hygiene. Use generic synthetic input only, no project indexing/publication, service restart, credential rotation or model download. Verify negative schema/instance-change, 429/504/503/transport/401/400, bounded retries/admission/cancellation and checkpoint partial-failure recovery through the existing isolated service-faithful harness; these results are fixture qualification, not claims that those faults or remote cancellation occurred in the shared daemon. The checklist reports live and isolated results separately and names any unexecuted remainder. Record dated results in wave.md Live Acceptance and this Progress Log with observed HTTP instance identity and separately collected installed version/build metadata; the health endpoint exposes no build identity and installed metadata is not remote attestation. The adaptive API is now available, but current parsing must be reconciled before live inference can pass. Keep the wave paused until implementation/review are ready; any unverified required result remains unmet and must be resolved rather than silently waived. Native Windows/Linux are not qualified by this run.
8. **Platforms.** Selection policy is unchanged: macOS arm64 only. Windows, Linux and WSL2 keep `unsupported_host`. Reporting fields are present on every platform with the local-route values.

## Scope

**Problem statement:** failure causes are collapsed, retries are either absent or blind, concurrency is unbounded, and capacity is invisible.

**In scope:**

- `tensorwell_client.py`: response classification on the status-carrying seam from `20tpq`, error envelope parsing, retry and backoff, concurrency locks, counters, best-effort stats read, status fields
- `wf_server/server_impl.py`: `wf_server_info` surface and docstring for the new fields
- Framework README, `docs/specs/mcp-tool-surface.md`, `docs/architecture/embedding-model.md`, `docs/architecture/threat-model.md`, and one CHANGELOG bullet
- Focused regressions in `test_tensorwell_client.py` and `test_tensorwell_integration.py`; the live checklist as a recorded wave qualification, not a committed test

**Out of scope:**

- Capability negotiation, workload, deadlines and the session hint themselves (change `20tpq`)
- A dashboard surface for the new counters
- Any change to lexical recovery, index publication or checkpoint formats
- Any Tensorwell source or service lifecycle behaviour

## Acceptance Criteria

- [x] AC-1: A fake service returning each of 429, 504, 503, 400, 401, 404, 408, 413, 415, a transport disconnect and an unexpected status yields the mapped reason token in the raised error, in the role's last-attempt record and in the status snapshot; a well-formed envelope `code` is preferred, an undocumented or oversized `code` falls back to the status mapping, and the envelope `message` appears nowhere; only the four deselecting outcomes leave `select_embedder` returning `None` afterwards; no diagnostic contains input text, tokens or the session hint.
- [x] AC-2: On 429 the client waits at least the patched floor, honours an integer `Retry-After` up to the patched ceiling, ignores an HTTP-date value, retries at most 3 times and never beyond the operation deadline, fails immediately when the floor exceeds the remaining budget, and never issues two requests concurrently; on 504 interactive fails without retry and batch retries once after backoff; on 503 readiness is rechecked at most twice; on a transport disconnect the client rediscovers once and retries only when the instance is unchanged; 400, 404, 408, 413 and 415 are never retried; a flapping 429/503 service cannot hold a batch `embed()` past its operation ceiling or an interactive call past 40 s.
- [x] AC-3: Under concurrent callers the fake service never sees more than one batch request in flight, interactive requests proceed while a batch handler is blocked, at most 4 interactive requests are in flight with 5 or more concurrent callers, and a fifth caller that gets no slot within its deadline fails locally with `overloaded` having sent nothing.
- [x] AC-4: After retry exhaustion no local model is constructed: query paths return lexical recovery, indexing discards unpublished output, and the memory path keeps its existing fallback outcome.
- [x] AC-5: Registered wf_server_info reports normalized capability/timing/counter/readiness/statistics fields using service-faithful schema_version 2/3 stats fixtures with reversed model order, nested model.load_count, and null optional labels on the reranker. Counts survive normalization, null labels are omitted without invalidating stats, duplicates and malformed non-null values fail the stats read without deselecting the pair, and status reads perform no HTTP. Unsupported hosts retain local-route values and unknown fields remain excluded.
- [x] AC-6: The bounded checklist in requirement 7 is complete with real selected-candidate inference results separated from isolated negative/recovery controls, observed instance identity and honest build provenance, and all deviations/unexecuted limits recorded in wave.md Live Acceptance and this Progress Log.
- [x] AC-7: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Replace the single `unavailable response` path with status and envelope classification, the reason vocabulary and the deselection rule.
- [x] Implement the per-outcome retry table with the `Retry-After` parse and clamp, jitter, the 4-attempt request cap and the operation deadline; keep the values as module constants.
- [x] Add the batch lock and the interactive limit with local `overloaded` on slot timeout; prove with a concurrent fake-service test of at least five interactive callers.
- [x] Add counters, last-readiness time, timing and the best-effort allow-listed stats read to the status snapshot and `wf_server_info`, including its docstring.
- [x] Update the README section, the MCP tool surface spec, the two architecture docs and the CHANGELOG bullet.
- [x] Run the live acceptance checklist against the deployed candidate and record results in the wave record and this Progress Log.

- [x] Align existing stats fixtures/reader with model.load_count and nullable optional labels; retain order-independent profile selection, duplicate checks, numeric bounds and allow-listed normalized output.
- [x] Verify registered cached reporting against the revised contract, including nested timing and no HTTP on status reads, before repeating live acceptance.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Classification and retry | Implementer | `20tpq` landed | Same write owner of `tensorwell_client.py` |
| Reporting surface | Implementer | Classification and retry | `wf_server_info` and docs |
| Live acceptance | Coordinator with operator | Deployed Tensorwell candidate | Recorded in wave record; wave paused meanwhile |
| Delivery review | QA, security, architecture, performance, docs-contract | All | Read-only |

## Serialization Points

- `.wavefoundry/framework/scripts/tensorwell_client.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_tensorwell_client.py`
- `.wavefoundry/framework/scripts/tests/test_tensorwell_integration.py`
- `.wavefoundry/framework/README.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/embedding-model.md`
- `docs/architecture/threat-model.md`

The root-level changelog gets one Unreleased bullet under Changed, ending with the wave id. Lands after change `20tpq`; one implementer owns the client module across both.

## Affected Architecture Docs

`docs/architecture/embedding-model.md`, section Optional Tensorwell execution: the outcome vocabulary, deselection rule and retry bounds. `docs/architecture/threat-model.md`, section Optional Tensorwell client: bounded `Retry-After`, error codes and stats values; envelope message discarded. `docs/specs/mcp-tool-surface.md`, section Cached inference status: the new `data.tensorwell` fields. The framework README **Optional Tensorwell inference** section for operator guidance. `docs/architecture/cross-cutting-concerns.md` does not describe the client: N/A. No new authority, dependency or data format.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Operators must distinguish overload, timeout and breakage |
| AC-2 | required | The service contract forbids unbounded or hedged retries |
| AC-3 | required | Admission limits are per service, not per client, and MCP tool calls must not queue without bound |
| AC-4 | required | Preserves the no-silent-fallback decision from wave `20nju` |
| AC-5 | important | Capacity visibility; no behaviour depends on it |
| AC-6 | required | Final testing against the real candidate is the operator's stated gate |
| AC-7 | required | Delivery gate |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Planned from the Tensorwell integration brief dated 2026-10-15. Live acceptance waits for Tensorwell's candidate deployment; implementation does not. | Brief; current `tensorwell_client.py` at commit `57f7cecc` |
| 2026-10-15 | Readiness repair in one round: bounded `Retry-After` parse and clamp, one operation deadline instead of retry counters, which outcomes deselect the pair, envelope message discarded and code validated, typed allow-listed stats that never unqualify the pair, local `overloaded` for a fifth interactive caller, the documentation surfaces that actually describe the client and the `wf_server_info` fields, a CHANGELOG bullet, and a recorded fallback for the live-acceptance gate. Removed the no-op "lower batch concurrency" clause. | Security SEC-1/2/3/5/8, red-team RT-3/4/6/8/9/10, code CODE-4/7, QA-7 to QA-11, architecture ARCH-2/3, performance PERF-1/2/3/4, docs DOCS-1/2/4, release REL-1/2 |

| 2026-10-15 | Readback: classify bounded error envelopes, serialize bounded retries under the operation deadline, limit batch and interactive concurrency separately, and expose cached allow-listed capacity/timing/counters. Before: busy and contract failures share one unavailable reason. After: 429 is overloaded with bounded waiting while 400 fails once; no selected-service error constructs a local model. AC-1–5/7 implemented with isolated services; AC-6 and its live-checklist task remain unmet until a deliberately selected deployed candidate exists. Shared tensorwell_client.py ownership is serialized after 20tpq; reporting/doc/test surfaces only. Pause after review pending live acceptance, without closing. | Current approved Requirements and ACs; successful wf_implement_wave |

| 2026-10-15 | Operator final-contract check: /v1/stats uses schema_version 2 (existing service) or 3 (adaptive, not deployed), with a models array whose profile ID is row.model.id. Locate rows by ID, never position; normalize only the two pinned profiles and documented fields for cached status. This reconciles the envelope explicitly awaiting Tensorwell final check in the approved plan; no live execution is claimed. | Operator-provided abbreviated envelope and response owner crates/tensorwell-daemon/src/service/qualification.rs:1463; reversed-order isolated fixture |

| 2026-10-15 | Classified 429/504/400 failures preserve their fixed reason through real query/search/memory recovery and attempt records, without local model construction. Cached registered status reports allow-listed stats/timing with no HTTP; integration fixture explicitly simulates session-header allocation because its HTTP seam is replaced. Client socket tests separately verify actual header delivery. Canonical focused 82 tests / 3 files / 0 skips passed; exact optional selection failure phase/status/code is being completed before final qualification. Live acceptance AC-6 and its task remain intentionally unchecked pending deployed candidate. | /private/tmp/20tpp-focused.log; client implementation packet and named regression controls |

| 2026-10-15 | Material implementation, docs and tests are frozen for one canonical default qualification. Earlier canonical focused group: 82 tests / 3 files / 0 skips passed; final client-only diagnostic completion: 46 tests / 0 skips passed. Nine refreshed in-memory client mutants and the facade workload mutant are detected by named tests. Full suite is pending; live AC-6 remains unmet. | /private/tmp/20tpp-focused.log; /private/tmp/20tpp-client-implementation.json |

| 2026-10-15 | Frozen delivery QA and independent code review found that valid output crossing the operation deadline during validation returns success through embed, embed_query and rerank. The owning deadline AC is reopened until the bounded repair and fresh reverification. No source edit while remaining seats review. The first canonical attempt was deliberately stopped (exit 143), with its runner stdout identity and descendant ancestry verified; no owned test process remains. It produced no qualification or receipt. | Deterministic QA/code deadline probes; /private/tmp/20tpp-full-suite.log; finding pending typed normalization |

| 2026-10-15 | Cycle-1 repair checks the deadline after vector/timing validation and before success accounting. Late validation reports deadline_exceeded / response_validation, retains the qualified pair and releases admission slots. New regression covers 18 deterministic entry/seam/boundary combinations; deleted/loosened guards cause 12/6 assertion failures, zero errors. Fresh separate QA/code contexts cleared the exact issue; code independently checked 27 cases including status-lock admission. Corrected canonical focused group passes 84 tests / 3 files / 0 skips in 13.074s. All other nine reviewed paths are unchanged; framework gate closed. The final canonical suite follows on this frozen tree, and full QA/council authority remains withheld for live acceptance. | Existing test_tensorwell_client.py regression; /private/tmp/20tpp-deadline-repair-cycle-1.json; /private/tmp/20tpp-repaired-focused.log; repaired aggregate 81330376a7eda42ed72fdfda5480885b6a71bd34a97efdcb685c3ffac291e3ad |

| 2026-10-16 | Second canonical attempt was stopped deliberately (exit 143) after the registry module exposed the obsolete wf_server_info description pin; it is not qualification and wrote no receipt. Fresh separate QA/release contexts confirmed exactly one mismatch among 90 handler digests and unchanged executable AST. Typed repair_start cycle 2 preceded updating only that supporting fixture entry. Registry module now passes 27 tests / 0 skips; every prior reviewed path is unchanged. Fresh focused QA/release verify the pin and description-mutation control before qualification resumes. | test_mcp_tool_registry.py HandlerDigestTests; events.jsonl; frozen 12-path aggregate 114a298125bac63a3fe7758a4906e5099a1becd6df6ac2abefa6528460e639b2 |

| 2026-10-16 | Final canonical default qualification passed 11,862 tests / 200 files / 12 existing skips in 740.812s. Green receipt matches current framework inputs, and all 12 reviewed paths remain unchanged. D1 and D2 are independently reverified and terminal; six implemented-scope approvals are recorded. AC-7 is complete in both changes. Wave paused with 20tpr AC-6/live task and full QA/council approval still pending the deliberately selected deployed candidate; no close/commit/push/package. | inputs_hash 5cec243a19aa224dc3934a6a0dc5ebe4f9bf73d79a8a00bc860935ccd0ada239; /private/tmp/20tpp-qualified-suite.log; events.jsonl |

| 2026-10-16 | Deployed API reconciliation reopens AC-5/7 and reporting/doc tasks. Live stats uses schema_version 3, models selected by model.id, model.load_count, and a null optional_state for the reranker; the current stats reader would reject that null and miss nested load_count. Response timing is nested under metadata.timing. These are contract adjustments inside admitted reporting scope, not new service policy or model-selection work. Live AC-6 remains unmet; availability GETs performed no inference. | Read-only authenticated local stats; Tensorwell service.rs response builder and workers.rs snapshot; revised 20tpq requirements |

| 2026-10-16 | Focused readiness clarified the verification boundary: selected-candidate nominal inference is live; negative failure/cancellation/checkpoint controls run in the owned service-faithful harness. Global stats suppression_reason is intentionally dropped. No service fault, remote cancellation or full live qualification is claimed before execution. | Revised Requirements 5/7 and AC-6; independent primer testability check |

| 2026-10-16 | Readback: consume actual nested schema_version capabilities/client_session and metadata.timing, normalize nested load_count/null labels without changing internal status/callbacks or model/deadline/privacy boundaries. Before: ready local service is rejected as capabilities_unsupported. After: the real pair qualifies and returns validated embedding/reranking results. Single client/test owner; coordinator integration/docs owner. Current focused readiness approvals recorded and prepare/open succeeded before framework edits. Live positive checks and isolated negative/recovery checks remain distinct. | Revised owning Requirements/ACs; review-policy-dfb1deaa01d9735b47f5; wf_prepare_wave/create and wf_implement_wave/create |

| 2026-10-16 | Revised API implementation passes producer-grounded controls: client 52/52 green, zero skips; nine guard mutants detected. Consumer/provider focus 37/37 green. Added healthy checkpoint-recovery leg after preserved failed epoch; integration 26/26 green with elapsed-backoff fixture and no local model factories. Real selected-candidate positives passed eight HTTP inference requests, nested timing/stats, prefix/session/privacy and batch-size comparison; results and limits are in wave.md Live Acceptance. Source frozen for fresh delivery review; full canonical suite follows once review settles. | Existing named client/integration tests; /private/tmp/20tpp-api-client-implementation.json; /private/tmp/20tpp-api-live-acceptance.json; /private/tmp/20tpp-api-recovery-integration.log; aggregate c5ed1347ca471a9076e8055bc7482c6e8baec6d13507aac7a3bd14e1cf77fde8 |

| 2026-10-16 | Revised API delivery complete: all required ACs/tasks verified, fresh focused review found no new actionable findings, all seven lane and council delivery approvals current. Canonical default passed 11,867 tests / 200 files / 12 existing skips in 756.863s; receipt matches current framework inputs and all twelve frozen hashes. Full docs validation passes. Wave paused for operator closure; no close/commit/push/package performed. API nominal checks are live; controlled faults/recovery are isolated as recorded. MCP reload succeeded, while setup assessment separately requests host restart; no setup/index rebuild was run. | inputs_hash 818020c3e26c974fbc93ff4c28c1b33645c808481522ac76ae98b8ad61f0479d; aggregate c5ed1347ca471a9076e8055bc7482c6e8baec6d13507aac7a3bd14e1cf77fde8; events.jsonl; /private/tmp/20tpp-api-canonical-suite.log |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Retry table with small fixed caps per outcome, all under one wall-clock operation deadline, in the adapter | Matches the brief's per-outcome guidance, keeps waiting out of the server and bounds composition with one number | Separate retry counters and a time budget (rejected at readiness: caps compose into hours on a flapping service); generic exponential retry (rejected: hedges deadlines and masks contract errors) |
| 2026-10-15 | Read `/v1/stats` best-effort after qualification, once per cache window | Keeps status a no-HTTP snapshot, adds one bounded GET per refresh, and a stats failure never unqualifies a compatible pair | Fetch on every status read (rejected: status must not do I/O); stats inside the qualification try (rejected: a 404 on a schema 1 service would deselect inference) |
| 2026-10-15 | Only transport, 503, post-rediscovery 401 and unexpected outcomes deselect the pair | Contract errors and overload describe one request, not the service | Deselect on every failure as today (rejected: one bad batch blanks interactive callers for 5 s) |
| 2026-10-15 | Live checklist is a wave qualification record with a recorded fallback; the wave pauses while waiting | It needs a deployed service and operator selection, and must not hold the single OPEN slot | Skip it (rejected: operator asked for final testing against the candidate); hold the wave OPEN (rejected: blocks every other wave) |

| 2026-10-16 | Normalize the deployed nested counts and nullable labels into the existing cached status shape | Uses the actual API without expanding public status or coupling the client to adaptive policy internals | Expose raw stats (rejected: broadens diagnostics and leaks unbounded fields); require invented row-level load_count/non-null labels (rejected: rejects the deployed service) |

| 2026-10-16 | Use the shared local service for nominal inference and isolated harnesses for controlled faults/recovery | Tests the real consumer wire contract without disrupting a service shared by other clients; retains negative-path verification and explicit limits | Force failures/restart on shared service (rejected: disrupts other clients); call availability alone live acceptance (rejected: does not test inference) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Retry budgets make a failing index build slow to fail | The operation deadline bounds total time per `embed()` call; counters expose it |
| Stats path or fields differ from Tensorwell's final check | Names are pinned in one reader; unknown fields are dropped, missing documented fields reported as absent; rename is a bounded edit |
| Candidate deployment slips past implementation | Wave pauses on AC-6 with the fallback in requirement 7; everything else is complete and reviewed meanwhile |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
