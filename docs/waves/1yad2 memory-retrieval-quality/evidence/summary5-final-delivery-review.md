# Summary5 fresh delivery repair reverification

Owner: Engineering
Status: active
Last verified: 2026-09-17

Reviewer `/root/summary5_final_delivery`, context `summary5-final-delivery-repaired-20260917`, independently reviewed the repaired freeze. Code, architecture, docs-contract, security and performance are five lenses in this ONE fresh context, not five isolated reviewers. This reviewer implemented no production repair and changed no source, tests, labels, parameters or living docs. QA is separately assigned.

## Verdict

S5-STALE-SOURCE is resolved for code-reviewer, architecture-reviewer and docs-contract-reviewer. S5-MODEL-RECOVERY-GUIDANCE is resolved for code-reviewer and docs-contract-reviewer. Security mechanisms approve within the existing trusted local operator/repository threat model. All five assigned lenses approve the bounded delivered change following the production evidence audit below: code-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer and performance-reviewer. Canonical suite and final docs validation remain coordinator-owned; these approvals do not claim those pending checks ran.

## Scope, reference and integrity

All 12 Git blob hashes in `/private/tmp/wf-summary5-freeze-repaired.json` matched before and after execution using `/Library/Developer/CommandLineTools/usr/bin/git hash-object`. Budget 15 minutes; targeted tests per mutant, whole-file only for survivors. None survived. Reviewed admitted plan production-integration contract, original delivery/QA defects, repair evidence, implementation, selected tests, SQLite schema/connection ownership, layering and threat-model contracts, public tool docs, architecture/performance/reference docs and changelog. MCP code_outline/code_read supplied current source; targeted filesystem reads and Git diff supplemented source navigation. No stale indexed semantic answer or old MCP runtime inference was used as current behavior evidence. Fresh subprocesses loaded current code. This reviewer ran no model inference or production index mutation. The coordinator later supplied actual CPU public-path measurements, independently audited below.

Independent references: admitted filter-before-cap/20+20/RRF60/first-five/raw-logit>=-4/no-refill contract; original same-path stale-source reproduction; documented cached-constructor behavior; public aggregate-only evaluator contract; SQLite snapshot invariant independently probed with a concurrent native writer. Tests alone share implementation assumptions, so the native transaction and registered-tool state probes supplement them.

## Executed evidence

Explicit `/opt/homebrew/bin/python3 -B` (Python 3.13.5, macOS ARM64), PATH including CommandLineTools Git:

- 18 selected unittest checks: all eleven MemoryQueryQualificationTests, all five MemorySearchOrderingTests, SQL grouping/read-only test and curated shared-global sentinel test: passed, zero skips.
- Four additional evaluator checks: aggregate-only tool output, aggregate-only unavailable output, fusion channel caps/negative cosine, negative/empty/unjudged metric distinction: passed, zero skips.
- Nine baseline tests in the prior review mutation script repeated successfully before five mutants; the two repair-mutant tests ran independently as well.
- `/private/tmp/wf-summary5-final-registered.py`: real FastMCP registration, actual registered memory_search function, temporary memory root, deterministic candidate/model seams. Healthy result screened with support_verified=false; unknown argument rejected; actual CPU constructor cache failed once, two successive registered calls recovered lexically and included restart guidance; private constructor exception omitted. Explicit cache reset positive control then recovered screened behavior. A real host restart was not executed. Initial scratch invocation lacked activated MCP dependencies; activating the normal tool venv corrected the harness setup before successful execution.
- `/private/tmp/wf-summary5-final-snapshot.py`: native pinned APSW/SQLite-vector runtime with temporary WAL database. Writer commits changed source hash and vector after reader source-hash SELECT; current reader still returns original vector and matching source state; next read rejects old expected hash. This independently proves hash/vector snapshot coupling under publication, not merely a connection-shaped mock.

## Repair facts

S5-STALE-SOURCE: eligible individual memory bodies are hashed as raw SHA-256, after root confinement. Existing published layer_path_state(layer,path,hash) rows are read inside the same read transaction as vectors; no schema change. Missing/mismatched provenance rejects screening. The repaired public test executes unchanged source -> unrelated source edit -> same-size eligible edit with exact preserved mtime -> restored bytes -> missing published source row. Expected and observed are healthy -> healthy -> unavailable/memory_source_state_stale -> healthy -> unavailable/memory_source_state_stale. Query statements are SELECT-only and fixture database bytes remain unchanged. No global freshness walker is called. Concurrent native publication invariant additionally passes. This checks bytes observed at call time, not a filesystem-wide atomic snapshot or same-user post-hash races.

S5-MODEL-RECOVERY-GUIDANCE: model-specific fallback now names disable setting, local runtime/model availability, wf setup if provisioning needed, and MCP restart after correction; index refresh alone explicitly does not clear the failure cache. Registered-tool probe verifies two cached-failure fallbacks and a reset recovery control. No per-query retry loop or shared provider mutation added. Source docs describe the same remedy.

## Mutation table

| Mechanism | Safe in-process mutation | Falsifying check | Observed |
| --- | --- | --- | --- |
| Published source hash | Bypass expected_hashes guard | test_source_hashes_guard_current_vectors_without_global_freshness_scan | 1 assertion failure, 0 errors |
| Model recovery | Remove restart remedy | test_model_failure_guidance_explains_cached_failure_recovery | 1 assertion failure, 0 errors |
| Summary cap | Check six | test_five_summary_checks_no_refill_and_rrf_order_is_preserved | 1 failure |
| Raw threshold | Change -4 to -5 | Same five-summary test | 1 failure |
| RRF order | Restore confidence-first sort | test_query_relevance_can_precede_confidence_without_claiming_authority | 1 failure |
| Coverage | Ignore incomplete dense state | test_missing_stale_code_only_incomplete_and_model_disabled_recover_lexically | 1 failure |
| Finite scores | Remove finite guard | test_relevance_failure_never_returns_unchecked_semantic_hits | 2 failures |

Mutants were compiled into subprocess module objects and restored, never written to reviewed paths. No survivor required whole-file testing. The typed known_bad_detection_method is focused-mutation.

## Remaining lens assessment

Code: filter-before-retrieval, record grouping before LIMIT20, lexical20/RRF60, exactly first-five summary/title qualification, -4 inclusive boundary, preserved RRF order/no refill, unavailable/healthy-empty distinction and limit handling align with the admitted contract. Confidence/provenance remains attached; support_verified=false and calling-agent judgment are explicit. Queryless/brief ordering, archive-register identities and historical lexical recovery controls pass. CPU factory uses explicit CPU StaticShapeReranker and leaves neighboring provider/global cache unaffected; actual provider parity is corroborated by the audited production benchmark below.

Architecture: no migration or new dependency; existing SQLite path-state provenance participates in one read transaction. Source SHA producer uses raw bytes and published schema key is (layer,path). Query consumers stay read-only and canonical storage ownership is preserved. Reused memory_eval BM25/RRF primitives are documented production dependencies.

Security: path resolution checks relative_to(canonical_root) before the new byte read; SQL layer allowlist and parameterized JSON path values avoid interpolation. Existing quote-bearing SQL control and unchanged database checks pass. Exception messages do not expose query/model failures. No shell execution added, no new remote service or privileged caller surface, no credible attacker-controlled authority delta or exploit chain established under current trust assumptions. Concurrent malicious same-user filesystem races are outside the stated threat model.

Docs-contract: repaired public promise and recovery guidance match executed behavior; candidate scores do not assert answer support or conflict resolution. Prototype timing/precision is explicitly marked prototype. Changelog's faster/more-relevant claim is supported on the measured local sample by the production audit below, not by mocks or a universal precision guarantee.

Performance: materialized counts are bounded; eligible-source hashing, exact SQL distance scan and BM25 remain corpus-dependent. Native snapshot checks prove consistency, not speed. The actual CPU/public benchmark audit below supplies 100-call p95, cold cost, paired baseline/material benefit and production parity. Performance approves within the local measured scope; process RSS does not isolate the extra allocation of a CPU model beside an already resident GPU model.

## Typed reverification facts

For S5-STALE-SOURCE code/architecture/docs and S5-MODEL-RECOVERY-GUIDANCE code/docs: phase=delivery; claim_kind=reverification; disposition=resolved; independent=true; fresh_context=true; actor is the corresponding lane under reviewer context above, distinct from implementer repair actor; execution_status=executed; probe_class=local_safe; authorization_status=authorized; required_for_approval=true; safe_boundary=false; universal_claim=false. Coordinator authors typed events, not this report.

Integrity booleans: test_ran_without_unintended_skip=true; public_path_reached=true; boundary_values_realistic=true; assertions_non_vacuous=true; known_bad_detected=true. known_bad_detection_method=focused-mutation. Counterexamples: same-size preserved-mtime body edit still qualifies, published hash/vector versions mix in one call, or latched model failure lacks restart recovery guidance. All are rejected by executed controls.

Not personally run: actual native model/provider inference and public benchmark (coordinator executed; independently audited below), canonical suite, full neighboring code/docs retrieval suites, native Windows/Linux/Intel, actual host restart, exhaustive parameter/guard mutation, global filesystem snapshot. No claim exceeds these limits.


## Production evidence audit and final five-lane approval

The coordinator executed the actual repaired public `memory_search_response` and the exact pre-wave public function extracted from HEAD, each on its own copy of the same complete frozen database snapshot. Shared ranking/record helpers remain unchanged; `ProbeIndex` only observes swallowed docs-search failures. This reviewer inspected both scripts and output artifacts, independently recomputed result/quality/precision metrics and checked all 12 reviewed hashes again. No implementation, label or parameter was changed for this audit.

The snapshot SHA-256 is `a493472bf7ea7d53b915e1cc34804a266e0d5ce8340af23c0566b7c4953a9578`, with 291 own-wave evaluation chunks excluded to avoid evaluation prose contaminating retrieval. The source-census/hash verifier runs before and after each benchmark. Both paths use the same cyclic 24-query schedule for 100 warm calls and the same CPUExecutionProvider, cross-encoder/ms-marco-MiniLM-L-6-v2, singleton batch. Candidate qualification is asserted healthy and support_verified=false on all 100 calls. The baseline rerun additionally asserts no observed semantic failure on every call; its final semantic_failed=false and 13/24 recorded cases have semantic assist. The earlier baseline run lacking that explicit failure assertion is not the final timing authority.

| Measure | Exact old public function | Repaired public candidate |
| --- | ---: | ---: |
| Warm calls | 100 | 100 |
| p50 ms | 596.639 | 179.755 |
| p95 ms | 614.034 | 192.199 |
| p99 ms | 654.951 | 199.845 |
| First call ms | 1677.228 | 1513.204 |
| Recall@3 and Recall@10 | 0.65625 | 0.84375 |
| MRR | 0.71875 | 0.83333 |
| Useful answers | 12/16 | 15/16 |
| Empty answerable responses | 3/16 | 1/16 |
| Nonempty negative queries | 0/8 | 0/8 |
| Direct support / all returned | 11/16 | 15/21 |
| Adjacent-context records | 5 | 6 |

Candidate p95 improves 68.70%, remains below 500 ms and does not exceed baseline. No baseline useful answer is lost. All 24 candidate ordered ID lists exactly equal the frozen independently judged prototype output; all 24 baseline lists equal its original baseline. This reviewer recomputed direct-support counts from the hash-verified retained blind verdict/map files against actual current output IDs: no unjudged records and zero authority-conflict labels. This is transfer of prior independent judgments by exact output parity, not a fresh blind judging claim. The operator-approved empty-response exception remains disclosed and no threshold was retuned.

Candidate process peak RSS is 779,550,720 bytes (743.4 MiB), a whole-process high-water mark including embedding/model/runtime allocations. It is NOT isolated incremental CPU-reranker memory. Cold measurements do not evict OS caches. Native qualification is macOS ARM64/Python 3.13.5 only; sequential local runs are not cross-platform, concurrent-load or universal quality guarantees. Six adjacent records remain a real limitation.

Raw candidate artifact SHA-256: `2ff2aeb76b165ee37d38c1b4d072c5fa5f4e5b2a84fe23964afc3c66c32ade69`. Final baseline artifact SHA-256: `1c8ba7db8fa727a7a83fe2aa7272ea1f6931414fa9333fc736e31466a5ca142d`. Coordinator retains the scripts/results in `summary5-production-qualification.json.gz` and narrative `summary5-production-qualification.md`.

Final typed approval facts for the five assigned lanes: phase=delivery, claim_kind=approval, verdict=approved, independent=true, fresh_context=true, execution_status=executed, probe_class=local_safe, authorization_status=authorized; shared context `summary5-final-delivery-repaired-20260917`. Each approval inherits the six integrity declarations above and the bounded limitations. Performance evidence is coordinator-executed and independently audited, while functional/repair/mutation probes are this reviewer's own execution. Canonical whole-suite and final document validation remain unclaimed coordinator checks.
