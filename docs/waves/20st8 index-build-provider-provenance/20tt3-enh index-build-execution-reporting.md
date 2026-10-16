# Index build execution reporting

Change ID: `20tt3-enh index-build-execution-reporting`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-10-16
Wave: `20st8 index-build-provider-provenance`

## Rationale

Operators need to identify which provider actually embedded an index build. MCP availability/counters cover its own process; setup/indexing execute in children. A service adapter can successfully embed without provider-specific build output, so a local-provider readiness banner does not establish execution.

Field feedback reports 3,355 docs plus 2,931 code chunks and service deltas of 6,286 items/201 requests during a rebuild. This corroborates service use, but shared totals cannot establish per-build ownership or exactly-once execution. The client deliberately defaults to 32 items within a 128-item ceiling. The operator withdrew the batching complaint; no tuning is planned.

Add a bounded child-owned last-build summary through existing logs/build statistics. Preserve model/precision compatibility authority and keep child execution separate from MCP-process observations. Do not create a telemetry history or additional evidence folders.

## Requirements

1. Observe work where the build calls and accepts embedding results. Per docs/code layer, report backend and fixed selection/fallback reason, accepted embedding input count, and build-owned service logical requests offered/succeeded when observable. Local/extension providers must explicitly mark unavailable/not-applicable HTTP counts; mixed execution must not be reduced to one provider label.
2. Logical requests exclude transport retry attempts. Accepted inputs accrue after validation at the consuming embedding boundary. Reused vectors/no-op builds are not newly embedded work. Counts describe observed calls in this attempt, not daemon totals, physical device use, unique chunks or exactly-once execution; repeated work must not be presented as unique.
3. Emit a compact additive structured child-log summary and expose it through the existing completed-build statistics in `index_build_status`. Reuse existing last-build persistence. Cover docs-only, code-only and setup-combined builds, including separate child passes and shared embedder objects without double attribution. Preserve existing completion markers.
4. Associate summaries with the actual attempt/layer so old records, previous stats or unrelated service activity cannot be credited to a new build. Legacy builds report unknown execution. No-op builds report zero new work rather than copying earlier activity.
5. Separate execution from publication. Failed/aborted work may consume inference; report its outcome or incomplete/unknown status without claiming successful publication or replacing last-successful provenance with a successful-looking record. Execution backend must not enter model/precision fingerprints or force re-embedding when location changes.
6. Bound collection/output by the fixed layer/provider summary. Include no per-chunk history, repository text, prompts, credentials, service session identifiers or absolute paths. Status reads use cached/persisted observations only: no HTTP, model construction, qualification probe, traversal or build. Preserve extension behavior and disclose measurements its contract cannot expose.

## Scope

**In scope:** accepted-work observations in existing indexer/adapters; additive child summary; existing parent log/stat parsing and status; regression coverage and documentation.

**Out of scope:** batching/retry/concurrency changes; timing benchmarks; daemon-global telemetry; reranker accounting; metrics database/dashboard; historical backfill; new repository settings; extra install/upgrade work just to populate status; changes to compatibility, publication, recovery or extension callback authority.

## Acceptance Criteria

- [x] AC-1: A registered build-path regression with a controlled service yields attempt/layer-owned accepted-input and logical-request counts. Unrelated traffic is excluded, retries are not new logical requests, and local or unobservable providers are labelled accurately.
- [x] AC-2: Docs-only, code-only and setup-combined child summaries reach completed-build status through existing log/stat storage. Shared adapters do not double-credit work; incremental reuse and no-op controls report only new work, including zero.
- [x] AC-3: Invalid output, selected-service failure, interrupted/partial work and stale/legacy summaries cannot masquerade as a successful current build. Publication/compatibility metadata stays correct, and changing execution backend alone does not force re-embedding.
- [x] AC-4: Repeated status reads perform no inference/probes. Summaries remain bounded and exclude text, credentials, session identifiers and absolute paths; edited guidance distinguishes availability, selection, accepted execution, publication and process scope.
- [x] AC-5: The change's own suites and new tests pass, and its edited documents validate. Child-to-status assertions exercise the consumer path rather than only checking adapter counters.

## Tasks

- [x] Define minimal additive fields and counting semantics at existing build/adapter boundaries; derive supported providers from the framework declaration.
- [x] Collect bounded per-layer activity during real work, separate from publication outcome and compatibility identity.
- [x] Emit/parse the child summary through existing log/stat storage, preserving legacy and explicit unknown/no-op behavior.
- [x] Add controlled child-to-status, retry, shared/mixed/local/extension, no-op, stale-summary and failed-publication regressions without downloads or project-index mutation.
- [x] Update embedding/indexing architecture, MCP status spec and operator guidance; retain useful conclusions in wave.md.
- [x] After both changes settle, run focused checks and one canonical framework qualification, then delivery review. Reuse unchanged results for bookkeeping and later closure.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Reporting | implementer | 20st9 selection repair | Serialize shared-file edits after readiness. |
| Consumer verification | qa-reviewer | reporting | Independent read-only review of served status and negative controls. |

## Serialization Points

Implement after 20st9 stabilizes selection. Serialize indexer/setup, adapters, shared tests and documentation. Readied implementer owns writes; reviewers inspect. Prefer existing files and last-build storage over new helpers/artifacts.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/inference_provider.py`
- `.wavefoundry/framework/scripts/tensorwell_client.py`
- `.wavefoundry/framework/scripts/wf_server/index_handlers.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_tensorwell_client.py`
- `.wavefoundry/framework/scripts/tests/test_tensorwell_integration.py`
- `.wavefoundry/framework/README.md`
- `docs/architecture/embedding-model.md`
- `docs/architecture/chunking-and-indexing-pipeline.md`
- `docs/specs/mcp-tool-surface.md`

The root `CHANGELOG.md` will receive a concise behavior note during implementation. No seed, hook/config or generated prompt edits are planned. Preserve unrelated release stamps, fixtures and wave records.

## Affected Architecture Docs

- `docs/architecture/embedding-model.md`: child execution versus MCP-process status and counting limits.
- `docs/architecture/chunking-and-indexing-pipeline.md`: observation and bounded last-build reporting without changing vector/publication authority.
- `docs/specs/mcp-tool-surface.md`: additive completed-build statistics and unknown/failure/no-op semantics.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Attributes real accepted work to the attempt. |
| AC-2 | required | Makes subprocess and incremental activity observable. |
| AC-3 | required | Prevents false success, stale attribution and unnecessary indexing. |
| AC-4 | required | Keeps status cheap, private and bounded. |
| AC-5 | required | Verifies the served result, not only internal collection. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-16 | Final canonical qualification passed11,892 tests/200 files with12 existing skips in730.325s and wrote a current green receipt. All admitted ACs/tasks and independent delivery reviews are complete. Earlier failed executions remain historical evidence; none was waived. | /private/tmp/20st8-close-canonical-suite.log; framework test-cache.json matching current inputs. |
| 2026-10-16 | Fresh independent code/QA review executed13 reporting tests with zero skips/errors and two assertion-detected mutants; confirmed current12 code inputs replace prior102 counts, repeated reads converge and failed/incomplete/MCP controls hold. Cycle2 finding cleared in both lanes, fresh delivery approvals restored. Qualification task remains open pending a current canonical receipt; unrelated timing/model concerns were not expanded. | Typed DEL-BACKGROUND-CONTENT cycle2; existing test_server_tools.IndexEmbeddingExecutionTests; /private/tmp/20st8-background-repair-2-independent-code-qa.log. |
| 2026-10-16 | DEL-BACKGROUND-CONTENT repaired: standalone log parsing no longer borrows prior job bindings, elapsed time or content. Current content derives from validated layers; MCP log bindings remain enforced after state-file removal. All13 reporting tests pass, including3 new regressions. Restoring standalone binding or job-scope promotion fails the successful-background test; removing MCP fallback completeness fails its adjacent guard test (assertions only, zero errors/skips). | test_server_tools.IndexEmbeddingExecutionTests; /private/tmp/20st8-background-repair-mutations.json. Independent code/QA verification pending. |
| 2026-10-16 | Readback: repair DEL-BACKGROUND-CONTENT within AC-2/AC-5. Before: prior all-content stats constrain an independent successful code-only setup log, yielding incomplete and stale counts. After: standalone logs derive scope/content from their own validated records; MCP-owned logs retain state/job completeness checks and failed attempts preserve prior success. Expected code edits: server_impl parser and existing server-tools tests only. Finding and cycle-2 repair_start recorded before code edits. | Actual pre-repair status reproduction returned incomplete and old102codechunks instead of current12; typed finding DEL-BACKGROUND-CONTENT. |
| 2026-10-16 | All ACs verified through actual child/status controls, invalid/failure cases and known-bad mutations; all six delivery lanes approved. Final canonical execution passed 11,889 tests/200 files/12 existing skips, but the repository-change guard named concurrent 20t73 planning edits and wrote no green receipt. The final qualification task remains unchecked until a valid receipt exists. | Existing indexer/server/client tests; wave.md and /private/tmp/20st8-canonical-repaired-suite.log. |
| 2026-10-16 | Independent QA closed an initially surviving classifier probe with a faithful returned-failure boundary: actual build_index receives the real failed-result shape without SQLite/model/publication work, reports failed and clears context. Forcing finish() to success makes the same named assertion fail; baseline1/1 passed and mutant1assertion/0errors/0skips. No source edit or qualification repeat was needed. | `ReturnedFailureBoundary.test_build_index_returned_failure_never_becomes_execution_success`; /private/tmp/20st8-returned-failure-review-addendum.json. |
| 2026-10-16 | Implemented fixed child build/pass summaries with inherited MCP job identity, per-layer provider aggregates, consumer validation and thread-local request observation. Existing last-build stats preserve earlier successful provenance beside later failed/incomplete attempts. Actual service-fixture build output reaches the actual parser; no-op, extension-null counts, retry exclusion, unrelated threads and post-embedding failure are covered. | `EmbeddingExecutionTests` 7/7; `IndexEmbeddingExecutionTests` 10/10 and 38 existing status/build controls passed. |
| 2026-10-16 | Guard pin: deleting accepted-input credit fails the shared full/incremental count test; deleting shape/dimension/finite validation fails the invalid-result test; removing worker context propagation fails the incremental count assertion. | `test_full_and_threaded_incremental_shared_model_have_layer_owned_counts`; `test_invalid_results_do_not_receive_accepted_input_credit`; three AST mutants detected with assertions, zero errors/skips. |
| 2026-10-16 | Guard pin: moving logical-request credit into the transport retry loop fails the retry-exclusion test; removing observation-context reset fails cleanup after a synthetic build error. | `test_logical_requests_exclude_retries_and_other_threads`; `test_failure_after_embeddings_records_consumption_without_publication_success`; two AST mutants detected with assertions, zero errors/skips. |
| 2026-10-16 | Guard pin: removing job ownership, record caps or all-layer completeness is detected by the corresponding status regression; dropping preserved successful stats is detected as the missing required prior fields. The latter is a schema/retention failure, not a fixture/import failure. | `test_owned_records_refuse_stale_duplicate_and_conflicting_passes`; `test_malformed_bounded_records_fail_closed_without_echoing_fields`; `test_all_job_does_not_finish_between_successful_docs_and_code_start`; `test_failed_and_incomplete_attempt_preserve_previous_success`. |
| 2026-10-16 | All source edits settled before the single canonical suite. Two earlier owned-file checks encountered source-generation changes while the indexer was still being edited; both passed in a fresh focused process. They are not accepted failures or reasons to repeat broad qualification. Delivery reviewers inspect frozen hashes and run only targeted checks while qualification proceeds. | /private/tmp/20st8-delivery-packet.json; /private/tmp/20tt3-server-owned-fresh-controls.log; canonical qualification remains pending. |
| 2026-10-16 | Readback: observe accepted embedding work in the child and carry bounded attempt/layer summaries through existing logs/stats. Before: Tensorwell can embed successfully with no build-provider output while MCP lifetime counters stay zero. After: accepted inputs and logical service requests are attributed to this attempt; failed/incomplete work stays distinct from published success. AC-1–5; fixed model/precision identity, batch sizes and publication authority remain unchanged. Expected edits: indexer/tensorwell_client, existing server log/status consumers and their tests plus named docs. | Readied receipt review-policy-7554fda61d41a64cdb7d; 20st9 selection interface stable and main/child controls pass. |
| 2026-10-16 | Planned only. An actual indexer adapter diagnostic accepted a service embedding with empty indexer stdout; current build stats lack child provider activity. | `indexer._get_embedder_inner`, `_embed_texts`; `server_impl._parse_finished_build_stats_from_log`; `index_handlers._refresh_index_build_stats_from_finished_log`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-16 | Select compact child-owned summaries in existing logs/last-build stats. | Attributes execution without another retained telemetry system or service requests. | Compare daemon counters: unrelated traffic prevents ownership claims. Per-chunk or central history: adds storage/privacy/lifecycle overhead beyond the need. |
| 2026-10-16 | Keep 32-item batching and negotiated limits unchanged. | The field counts establish no throughput defect. | Tune toward the ceiling: unsupported performance inference and a separate scope. |

## Risks

| Risk | Mitigation |
| --- | --- |
| MCP process counters or unrelated operations bleed into reporting. | Build-scoped collection with layer ownership; keep lifetime counters separate. |
| Combined logs contain partial, old or duplicate summaries. | Validate attempt/layer association; report missing evidence as unknown/incomplete. |
| An adapter does not expose request internals. | Count accepted inputs at the consumer boundary and mark unavailable request measurements. |

## Session Handoff

See `docs/agents/session-handoff.md`. Planned only; successful Prepare remains required before code edits.
