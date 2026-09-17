# Independent QA qualification checkpoint

Owner: Engineering
Status: active
Last verified: 2026-09-16

Reviewer: `/root/memory_holdout`, independent of implementation/tuning. **Non-adoption confirmed; this is an implementation-review checkpoint, not final delivery approval.** Every holdout aggregate was independently recomputed with Python fractions directly from saved rankings and labels, without calling the delivered metric function. All reported values matched. Holdout report SHA-256: `5bc6268e04d06a8bcc9ba523d21880b621b79d2bfedadfc95b6f04da73cea308`.

| Variant | Recall@3 | Recall@10 | MRR | Empty answerable /16 | Nonempty no-match /8 | Warm p95 ms |
| --- | --- | --- | --- | --- | --- | --- |
| Production | 0.75000 | 0.75000 | 0.84375 | 0 | 2 | 690.77 |
| RRF | 1.00000 | 1.00000 | 1.00000 | 0 | 8 | 137.08 |
| Score fusion | 0.90625 | 1.00000 | 0.91875 | 0 | 8 | 136.19 |
| Qualified RRF | 0.84375 | 0.84375 | 0.93750 | 1 | 0 | 506.91 |
| Qualified score fusion | 0.84375 | 0.84375 | 0.90625 | 1 | 0 | 478.53 |

The two ungated finalists add six false-positive queries: holdout-17, 19, 20, 21, 23 and 24. Both qualified finalists eliminate production's false positives on holdout-18 and 22, but introduce an empty answer on holdout-04 (CLI test isolation). Qualified RRF also exceeds the 500 ms ceiling. Every finalist fails a predeclared adoption condition even if all other evidence-validity flags are optimistically granted. No retuning or label revisions followed these outcomes.

## Executed integrity controls and repairs

| Challenge / defect | Original observation | Independent replay |
| --- | --- | --- |
| Negative, boolean, inconsistent population counts | Adoption accepted invalid reports | Rejected with quality_measurement_unavailable |
| Delete judgment lists from eight negative cases | Manifest still valid | Rejected with explicit_relevance_labels_required |
| records=None or scalar record entry | Raw exception | Typed invalid_corpus_structure |
| Empty answerable query excluded from denominator | Known-bad metric shape | Correct mean 0.5, miss counted |
| Nonempty uncertain negative response | Must count as false positive | One false positive |
| Missing variant measurement | Must not count as successful abstention | available=false and null quality metrics |
| Code-only index with no docs layer | Production measurement marked available | available=false, real public lexical fallback |
| Missing/stale loader refusal, semantic failure, reranker absent/throw/NaN, incomplete coverage, swallowed production semantic failure | Nine distinct failure seams | 9/9 returned public lexical fallback and unavailable measurement |

The code-only guard was added to the runner after the healthy holdout measurements. It rejects an absent docs layer immediately after loading; it changes no parameter, ranking or score on the existing healthy snapshot. The holdout experimental evidence reports complete memory coverage. This edit's behavior was verified with the actual WaveIndex loader/search path using a code-only layer fixture; the remaining missing/stale faults inject loader failures. The timing loop excludes unavailable calls by its available branch; the fault probes verify that flag, not an end-to-end replay of main's timing loop.

`qa-probes.json` retains exact scratch script text and results as inert evidence. Every fixture write used a temporary root; no live index/memory write occurred. Shared provisioned Python 3.13.5 on macOS ARM64 executed these probes. The existing 23-test memory-eval suite passed before the helper repairs; a fresh final test receipt remains the coordinator's obligation.

## Acceptance-criterion coverage and remaining checks

| AC | QA evidence / remaining obligation |
| --- | --- |
| AC-1 | Frozen complete corpus and independent holdout; all metrics independently recomputed. Model/runtime report checked as supplied, no independent model-binary digest verification. |
| AC-2 | Paired candidate/fusion report retained. Final store-level duplicate/filter mutations and source-policy ablation interpretation belong in delivery evidence. |
| AC-3 | 14 production policy controls incl 11 hermetic invariants; history/archive/target/symbol/contrary active claims covered. Archive-body fixture erratum remains explicitly documented. |
| AC-4 | Nine fault seams plus code-only absence; per-record qualified ranking preserves no-match/miss tradeoff visibly. No universal relevance calibration claim. |
| AC-5 | Independently confirmed objective non-adoption for all four finalists; production preservation requires final diff review. |
| AC-6 | 100 warm observations per variant and cold report supplied. Scaling/duplicate density results and final supported-Python/platform evidence remain to be checked. |
| AC-7 | Aggregate metrics checked; final MCP wire privacy and docs contracts remain to be exercised/reviewed. |
| AC-8 | Final focused/full suites, final source fingerprint and docs validation still outstanding at this checkpoint. |

Positive labels are not exhaustive: unjudged tails remain unjudged. The fixed 24-case local corpus does not establish general quality. Native Windows/Linux were not executed here. The QA verdict supports retaining production ranking and the evaluation work; it does not waive remaining review or test obligations.

## Final QA delivery review

Verdict: **approved for the delivered non-adoption scope**, against all twelve entries of `delivery-fingerprint.json`, independently recomputed as Git blob SHA-1 and matching. Coordinator-owned full-suite and full-docs gates remain pending at this review timestamp; this approval does not substitute for either result.

Additional executed checks on the frozen source:

- Native APSW/sqlite-vec scratch database: 30 dominant duplicate chunks plus one weaker memory still return two distinct paths at limit two; literal quoted path, unrelated path exclusion, known cosine values 1.0 and 0.5, limit one, missing-path completeness and invalid limits all pass. No live database was used.
- Targeted committed SQL grouping, private-error MCP envelope and code-only index tests all pass. Removing SQL GROUP BY in an isolated function causes the exact grouping test to fail with one assertion failure and zero errors. The first mutant attempt had copied module globals and therefore bypassed the test's patched opener; that harness error was corrected by preserving the module globals before recording the discriminating failure.
- Real `run_curated` through `wf_memory_eval_response` reports code-only docs absence as unavailable with no metrics. Sentinel private query/record/path data in a semantic failure does not enter the public envelope. These are actual public-response tests with controlled index inputs, not a live-model success-path privacy claim.
- Independent AST comparisons against HEAD confirm unchanged `memory_search_response`, `memory_brief_response`, `_memory_ranked`, `search_docs`, `search_code` and `_rerank` bodies.
- Independent control recomputation confirms Recall@3: semantic/injection 0.84375, lexical/weighted025/weighted075 0.96875, shared-source policy 0.09375. This supports the report's attribution limit: broader candidates alone do not solve confidence-first ordering; it does not qualify another control for release.
- Scale evidence contains five consistent populations, 100 calls per component each, record/chunk products correct and output capped at twenty. It covers 119/1,190/11,900 records and duplicate densities 100 and 25. The runner uses native SQLite vector distances and BM25 but identical synthetic vectors; it measures scan/lexical cost, not realistic score distribution or end-to-end quality. Contention and native-platform limitations remain disclosed.

Final AC judgments: AC-1 complete for the bounded local benchmark, with incomplete positive relevance labels disclosed; AC-2 complete for bounded SQL/candidates, controls and non-adoption; AC-3 complete with explicit authority preservation and policy probes; AC-4 complete for tested fallbacks and reported candidate tradeoffs; AC-5 complete with independently confirmed no-adoption; AC-6 complete as local CPU/component evidence, with Windows/Linux and Python 3.11 native inference explicitly unqualified; AC-7 complete for unchanged public search and aggregate diagnostic contract; AC-8 has no QA-attributable defect remaining, with final suite/docs gates owned by coordinator. No scope waiver or unsupported platform claim is implied.

The final scratch native/test/mutation runner and raw results are retained in `qa-final-probes.json`. Reviewed source files were not edited. No holdout parameters were retuned, no labels changed, and no production adoption is approved.
