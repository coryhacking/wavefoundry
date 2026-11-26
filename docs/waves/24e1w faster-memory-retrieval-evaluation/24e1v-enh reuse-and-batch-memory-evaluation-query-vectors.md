# Reuse query embeddings and evaluate bounded batching

Spec ID: `24e1v-enh reuse-and-batch-memory-evaluation-query-vectors`
Spec Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-26
Wave: 24e1w faster-memory-retrieval-evaluation

## Rationale

The November 25 memory review took about 11½ minutes to score 576 queries after the incremental docs index finished. All 576 queries in frozen set v2 are distinct. A planning probe passed one query through both current comparison matrices and observed two identical calls to the same model. Across this set that accounts for 1,152 vector requests from those two comparisons alone. The elapsed time includes the whole evaluation. We have no timing yet that attributes the delay to those requests.

## Product Intent

A maintainer running Review memories gets the same retrieval judgments with fewer inference requests. The first independently useful outcome is for Wavefoundry to compute the vector for a case once across the summary-only and compact comparisons. The second is to establish, by measurement, whether submitting independent queries together saves additional elapsed time. This advances the controlled comparisons in Horizon 4 of VISION.md and supports the evaluation in memory-quality arc 244cm.

## Requirements

1. Give both comparison matrices the same query vector for each case under the same model, precision, provider and query formatting. Hold it only for the case or bounded batch. Keep the matrices separate. The improvement must work with a scalar-only provider and with an empty provider cache.
2. Compare three configurations on matching inputs: current scalar behavior, local reuse with scalar inference, and local reuse with bounded batches where supported. Preserve asymmetric query prefixes, query role, provider limits, ordering and per-case association. Use the existing scalar route when a provider lacks a qualified query-batch operation. Validate incomplete, misordered or invalid results using the existing provider contract and failure reporting. An inference failure must remain visible. Preserve cancellation and deadlines.
3. Keep the measured production arm on the real memory search handler, once per scored case. Preserve ranking, tie ordering, production qualification and fallback accounting. Keep the frozen queries, labels, model and index generation fixed for the comparison. Do not share cached results across production and experimental arms. Leave persistent caching and eviction to a separate provider decision.
4. Measure elapsed time and distinguish logical queries, vectors requested and actual provider calls for each configuration. Record provider/runtime, batch limit, corpus, query-set digest, competing load and warm-up policy. Attribute time to the comparison arms and to the production path sufficiently to explain the result. Keep measurements aggregate; exclude query texts and vectors from retained evidence.
5. Deliver local reuse when parity and call reduction hold. Enable bounded batching by default on supported direct CPU and local GPU paths after checking same-backend scalar parity. Honor existing device and precision selection, fail safely when GPU qualification fails, and keep batch-sensitive INT8 scalar. Report effects of changing backends separately from effects of batching. Preserve the independently measured Tensorwell default. Record whether residual repeated work warrants asking Tensorwell about a cache.

## Scope

Evaluation only. No persistent Wavefoundry cache, Tensorwell service changes, production search redesign, reindexing policy change, or relabeling the frozen set. A cache shared across clients or processes is a possible Tensorwell follow-up. No remote service is required for local reuse.

## Acceptance Criteria

- [x] AC-1: A counting scalar provider observes one query embedding per case across the two comparison matrices. Both still produce the reference ordered record IDs, including ties. A second run with a different provider does its own work.
- [x] AC-2: On distinct queries spanning a batch boundary and a short final batch, a capable provider receives fewer calls than scalar reuse. Its results match scalar query semantics case by case. A scalar-only provider completes the same fixture. Partial or invalid responses cannot silently shift a vector to another query or produce a successful score. If no installed provider qualifies, retain the fixture evidence and name the specific capability missing before adoption.
- [x] AC-3: Against the same frozen set and index, compare ordered outcomes for each case and arm and the resulting aggregate scores. The production arm still runs the real handler on every case and preserves fallback counts on controlled success and fallback inputs. Investigate any discrepancy before enabling either optimization.
- [x] AC-4: Retain matched timing and call-count results for baseline, scalar reuse and the qualified batch path, or document why the batch measurement could not run. Repeat a close timing comparison before choosing a default. State the observed end-to-end gain, the remaining dominant cost and the Tensorwell follow-up decision. AC-1 and AC-3 establish the first outcome; AC-2 and AC-4 establish the batching decision.
- [x] AC-5: A normal local evaluation uses batches without an opt-in on supported CPU and qualified GPU. Test configured CPU, failed GPU qualification, short batches, explicit scalar override and batch-sensitive INT8. Check same-backend scalar rankings. Distinguish measured hardware from fixture coverage.

## Tasks

- [x] Capture a scalar reference and aggregate timing under fixed evaluation conditions.
- [x] Pass a case-local vector to both comparison matrices and verify the scalar reference.
- [x] Probe query-batch capability and limits; exercise a bounded path and scalar fallback.
- [x] Compare rankings, fallback counts, calls and wall time; record which path to ship and why.
- [x] Implement and verify local CPU and GPU defaults through the evaluation entry point, then update operator guidance.

## Agent Execution Graph

Baseline measurement → scalar reuse and parity → bounded batch comparison → delivery decision.

## Serialization Points

- `.wavefoundry/framework/scripts/memory_eval.py`
- `.wavefoundry/framework/scripts/tests/test_memory_eval.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tensorwell_client.py`
- `.wavefoundry/framework/scripts/inference_provider.py`
- `.wavefoundry/framework/scripts/tests/test_tensorwell_client.py`

## Affected Architecture Docs

Review docs/architecture/testing-architecture.md for evaluation methodology and docs/architecture/contracts/mcp-tool-surface.md for the existing wf_memory_eval reporting contract. Document the chosen evaluation path if it changes guidance. Keep per-run timing evidence in the wave.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes local ownership and removes duplicate requests. |
| AC-2 | required | Qualifies batching and preserves scalar support. |
| AC-3 | required | Keeps the benchmark trustworthy. |
| AC-4 | required | Makes the decision on evidence. |
| AC-5 | required | Establishes the requested local defaults. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-25 | Replayed both comparison arms with one query and a counting embedder. Each requested the same query and model. Counted 576 distinct queries in v2. | memory_eval._Ablation.order and docs/evals/memory-query-set.v2.json |
| 2026-11-25 | Inspected the Tensorwell adapter. Its public embed_query sends one string with query role and interactive workload. Its document embedding entry point accepts multiple texts. Support for multiple query-role inputs on a particular runtime remains unverified. | tensorwell_client.py, embed_query and embed |
| 2026-11-26 | Implementation readback: share query inference between the two comparison matrices. Keep production independent. Gate batching on frozen per-case parity and measured elapsed time. | Code and QA readiness controls and matched benchmark snapshot |
| 2026-11-26 | The baseline took 587.587 seconds. Comparison queries consumed 219.882 seconds and 1,152 HTTP calls. All 576 scored production queries used model relevance. | Frozen v2 set, docs generation 6698, Tensorwell 0.5.2 |
| 2026-11-26 | The operator specifically requires direct-model operation. Evaluate direct batching against direct scalar inference with the identical model, precision and query prefix. Qualify local and service paths separately under requirements 1, 2 and 5. | Operator clarification during implementation |
| 2026-11-26 | Tensorwell batches of eight saved 31.3% elapsed time over baseline. Direct ONNX CPU batches preserved all 576 comparison rankings but their end-to-end gain fell within run variation. Enable Tensorwell by default and offer the qualified direct batch path by explicit opt-in. | [Tensorwell results](evidence/tensorwell-benchmark.md) and [direct-model results](evidence/direct-model-comparison.json) |
| 2026-11-26 | Follow-up agreed during delivery: evaluate an exact-input query cache for repeated evaluations, with separate cold and warm timings. The published SQLite vectors represent documents. Batch cache misses and keep production independent. | The comparison matrices took only 1.8 seconds to build. Model revision, role, precision and runtime must match on reuse. |
| 2026-11-26 | The operator requests default bounded batching for direct CPU and local GPU. Use the existing offload qualification and preserve the selected inference path for the scalar comparison. Retain singleton input for batch-sensitive INT8. | Amended requirement 5 and AC-5, focused code, QA and council readiness approvals |
| 2026-11-26 | Qualified direct CPU now defaults to eight and local GPU to its native 32. Native CoreML preserved all 576 comparison rankings. A 35-case evaluation used two GPU calls, versus 35 with the same-device scalar override, and the entire report matched. The offline selector also needed a cached-only path through accel_embedder.py and its isolated child. | [GPU qualification](evidence/direct-gpu-comparison.json), tests/test_accel_embedder.py and tests/test_memory_eval.py |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-25 | Share a vector within the evaluator first, then measure bounded batching independently. | Wavefoundry knows both comparison arms need the identical vector. Reuse removes a known duplicate even with a cold provider. A matched benchmark will show whether inference dominates total time. | Batching alone still requests duplicate work. A Tensorwell cache alone retains client round trips, needs its own key and invalidation policy, and does nothing for scalar local providers. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Document and query operations produce different embeddings. | Verify query-role behavior, prefix ownership and output order against scalar queries before enabling a batch path. |
| Provider warm-up, retries or competing work distort elapsed time. | Run one evaluator at a time, record conditions, count calls and repeat inconclusive comparisons. |
| Archived labels affect absolute quality scores. | Freeze the current set for parity. Handle the 26 affected cases separately from performance work. |

## Session Handoff

See docs/agents/session-handoff.md for current session state.
