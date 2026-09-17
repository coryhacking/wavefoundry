# Independent delivery lane review

Owner: Engineering
Status: active
Last verified: 2026-09-16

## Scope, verdict and independence

**Code, security, architecture, performance and docs-contract: approved for the delivered non-adoption outcome.** No unresolved material finding. This single independent reviewer performed the five lanes sequentially; this packet does not claim five isolated agents. The reviewer did not implement the reviewed source and changed only this review artifact. Typed review events belong to the coordinator.

Review target: the 12-file Git-blob map in delivery-fingerprint.json. Every hash matched before and after probes. Review budget: eight minutes; targeted test per mutant, whole-file expansion only for a survivor. Production memory ranking is unchanged. The running canonical full suite and final docs validation remain coordinator-owned prerequisites; this packet does not claim either has finished.

## Code-reviewer

Approved. The shipped additions implement reusable evaluation helpers and explicitly nonqualifying sampled diagnostics. They do not insert an experimental ranking branch into memory_search_response, memory_brief or ordinary code/docs retrieval. The server_impl diff changes evaluator descriptions only; the selected outcome keeps existing policy order.

Inspected memory_eval.py:276-564 for capped fusion, finite scores, frozen-manifest structure/labels, metrics and adoption gating; 840-962 for diagnostic privacy and unavailable states. Candidate streams and final lists cap at 20, union at 40. Empty answerable results remain in denominator and miss counts; nonempty negatives count as false positives; unavailable evidence invalidates qualification. Impossible query/error populations are rejected. Input fingerprints do not pretend to prove reviewer independence or untouched holdout.

The final QualificationTests class passed all 11 tests. The retained 24-case report reproduced all five aggregate metric objects and all four non-adoption decisions exactly using the shipped helpers, with no new inference or query scoring. The existing known-bad controls catch the repaired invalid-count, missing-label and code-only-index problems.

## Security-reviewer

Approved; no demonstrated vulnerability or exploit chain under the existing trusted local-operator threat model. The new storage helper uses allowlisted table layers and JSON-bound exact paths, not interpolated path SQL. It opens the native store read-only, performs count and grouped-distance reads, materializes at most 20 records, and closes the connection. The new public diagnostic returns aggregate fields and sanitized failure reasons; the exception-content leakage mutant was rejected through the actual public response path.

The wave runner writes explicit local evidence and an owned disposable snapshot. Its source connection uses mode=ro and SQLite backup; removals affect the scratch copy only. It verifies the complete source census and frozen bytes before and after evaluation. Corpus records remain repository-owned inputs under the existing trusted model, not new remote/untrusted input. This review makes no new external-input security claim.

The earlier native scratch probe exercised the actual dense_path_scores helper: 25 duplicate chunks for one body did not starve a second body; an apostrophe path matched exactly; an unrelated suffix path was excluded; missing coverage was explicit; database SHA-256 remained unchanged. Snapshot/qualification controls also verified copy-only exclusion, 20 checks, threshold equality, individual rejection, no tail backfill and NaN/Infinity refusal. No authoritative index or memory was edited by this reviewer.

## Architecture-reviewer

Approved. Non-adoption preserves the current confidence/status/freshness-before-relevance policy. The conditional authority decision remains an experimental design decision, not a shipped policy change. No shared policy helper, model, dependency, schema or stored-memory authority was changed. Compact archive entries retain memory_id identity through lexical evidence; the SQL helper groups individual body paths only.

Snapshot decontamination is effective for the measured public path: server_impl.WaveIndex.search_docs at 2271-2305 uses dense vector candidates followed by optional reranking; it does not query FTS or the chunk registry. The dense read joins canonical chunks_docs with vectors_docs. Deleting the wave's rows and vectors in the scratch snapshot therefore prevents those entries from reaching that path. Experimental dense queries use the exact eligible memory-body path set, while experimental lexical candidates come from memory bodies/register entries rather than the wave prose. Residual registry metadata does not restore removed candidates in this call chain. This conclusion is scoped to the actual measured search_docs path, not every hypothetical index consumer.

The final runner handles missing docs layers, swallowed semantic failures, incomplete path coverage and required-qualifier failure as unavailable measurements with public lexical fallback. Failed calls receive no timing credit. The public diagnostic separately rejects a valid code-only index as unavailable for memory semantics. No automatic adoption or global repair follows any of these states.

## Performance-reviewer

Approved as evidence for non-adoption, not as an adopted optimization or universal latency guarantee. The retained table and decision objects agree: ungated designs increase no-match false positives from 2 to 8; qualified designs introduce one empty answerable result; qualified RRF also exceeds the 500 ms ceiling. Those failures correctly outweigh rank/latency improvements.

Finalist public result limits are equal: baseline explicitly requests 20; fusion_rankings returns at most 20; qualification only removes entries from that prefix. Distinct-candidate caps do not bound physical exact scans or BM25 corpus traversal. The report discloses scanned rows, duplicate density, CPU environment, fresh-WaveIndex cold semantics, 100 warm calls per design and contention during synthetic component scaling. The existing performance-budget doc identifies these as experiments, not new production budgets. No competing CPU benchmark or new timing qualification was run during this review.

## Docs-contract-reviewer

Approved. The evaluator reference, public tool descriptions, search/testing/performance architecture updates and qualification report consistently distinguish sampled diagnostics from independent qualification and explicitly state non-adoption. The changelog describes more trustworthy evaluation rather than promising deployed faster search. Reported quality and timing figures match retained aggregate evidence. Native Windows/Linux and Python 3.11 native-model qualification are expressly unclaimed. The code-only docs-layer repair is disclosed as post-measurement diagnostic hardening with the healthy measured snapshot identified.

No claim that rank implies authority, threshold is universal, result caps imply constant work, or current sampled diagnostics authorize adoption was found in the reviewed updates.

## Mutation table and executed evidence

Mutations were in-memory replacements only; all source bytes remained frozen. Test names below belong to test_memory_eval.QualificationTests.

| Mechanism | Injected defect | Targeted detection |
| --- | --- | --- |
| Candidate/result caps | Change capped slices to cap + 1 | test_fusion_caps_each_channel_and_handles_negative_cosine: assertion failure |
| Finite fusion scores | Remove finite-score rejection | Same test: assertion failure |
| No-match false positives | Count every negative return as zero | test_metrics_keep_negatives_empty_answers_and_unjudged_distinct: assertion failure |
| Empty answerable misses | Remove empty miss increment | Same metrics test: assertion failure |
| Explicit negative judgments | Accept no relevant and no irrelevant labels | test_manifest_requires_explicit_judgments_and_rejects_malformed_corpus: assertion failure |
| Impossible error populations | Remove count <= population check | test_adoption_rejects_missing_evidence_regressions_and_timing_shortcuts: two assertion failures |
| Docs-layer availability | Remove run_curated docs-layer guard | test_curated_code_only_index_is_unavailable_not_empty_semantic_success: assertion failure |
| SQL record deduplication | Group by chunk ID instead of record path | test_scoped_sql_groups_before_limit_and_preserves_database: assertion failure |
| SQL eligible scope | Add an always-true OR to the path predicate | Same SQL test: assertion failure |
| Public failure privacy | Return exception text containing private query/identity | test_curated_diagnostic_is_nonqualifying_and_query_failures_do_not_leak: assertion failure |
| Redundant count type check | Remove one repeated count/population type guard | Survived targeted test and the permitted whole-file run: 25 tests passed. Other earlier population checks and later count checks still reject the invalid types. No lost observable guard was demonstrated; this is a redundant/equivalent mutation, not claimed killed. |

The first docs-layer attempt patched the ordinary imported module, but the public response uses srv._load_script's separate module instance. That initial survivor was a harness-targeting mistake, not evidence of public coverage. Repeating the mutation on the actual loaded module produced the recorded assertion failure. All ten behavior-changing mutations in the table were detected without import or fixture errors.

Executed anchors: baseline 11 tests passed; the one permitted survivor whole-file run passed 25 tests; raw-evidence reproduction matched five metric objects/four decisions; 12 frozen hashes matched before and after. Earlier native and AST-isolated probes are reported as such rather than represented as a complete real-model rerun. No new holdout tuning, whole model evaluation, full native-platform qualification or final canonical-suite pass is claimed here.

Five integrity facts: exact frozen files identified; actual current tests/functions exercised; negative mutations separated from baseline and restored in memory; redundant and mistargeted survivors disclosed; conclusions limited to tested behavior and source-verified call paths. The five lane approvals are independent of the implementers but share this reviewer's context.

<a id="readiness-renewal"></a>

## Bounded readiness renewal

On 2026-09-16, independently re-read the current Requirements, Scope, AC labels and qualification thresholds against this reviewer's original readiness packet. Their obligations and limits are unchanged; completion checkboxes and Session Handoff chronology record progress rather than a revised contract. The readiness-contract.md SHA-256 remains exactly e951e81becc073ccecf42fa4361768d232a3315ec4ac9f77a8ebc8c21ab52cae, as recorded by the original independent docs-contract review. All 12 delivery-fingerprint Git-blob hashes still match. No source, gate threshold, authority decision or adoption outcome changed.

**Support renewal of the existing readiness judgment for the refreshed policy receipt.** The updated Session Handoff accurately replaces the historical planning-only statement with implementation/non-adoption status and remaining verification. The original standard-depth targeted council rationale still applies: isolated red-team challenged authority versus relevance, metric denominators and physical work; the independent docs-contract seat verified the corrected public-baseline, negative-counting, archive-identity and bounded-materialization contracts. Its two-seat synthesis and existing named prepare-lane judgments need no substantive revision. This is a bounded renewal after chronology changed, not a newly run full council, a waiver of final verification, or approval to close/commit/push. Typed receipt binding remains coordinator-owned.
