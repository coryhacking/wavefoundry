# Summary5 final independent QA — repaired tree

Owner: Engineering
Status: active
Last verified: 2026-09-17

Verdict: **approved**. Source-freshness repair, public production qualification and final AC-8 evidence verified. Earlier pending statements below describe intermediate checkpoints and are superseded by the final approval section.

All 12 reviewed paths matched `/private/tmp/wf-summary5-freeze-repaired.json` before and after the executable checks. No repository source, tests, parameters, labels or lifecycle records were edited. This reviewer did not implement the repair. Fresh context and independent review apply to this repair verification. Scope/budget: three bounded risk groups, 15 minutes; targeted mutant tests, whole-file tests only for surviving mutants. No mutant survived.

## Independent repair verification

The independent reference is the admitted stale-state/recovery contract and the original same-path edit reproduction. The falsifying assertion is that changed source bytes with unchanged size/mtime must produce explicit unavailable lexical recovery until current source/hash/vector state is published. A temporary repository uses the actual `indexer._build_file_hashes` producer, `IndexStateStore` current schema, production `sqlite_vector_store.write_rows`, native APSW/sqlite-vec and real read-only dense SQL. Embedding/model outputs are controlled deterministic values; this proves storage/public-response behavior, not model quality or performance. The public `memory_search_response` and production `_memory_candidate_scores` wrapper execute.

Observed sequence: fresh hybrid response → same-size source edit with restored mtime → `memory_source_state_stale` lexical recovery → re-publication with current producer hash/vector → healthy hybrid recovery. Missing published hash state and injected source read `PermissionError` also recover explicitly; an unrelated source edit does not invalidate memory retrieval. Database main-file bytes remain unchanged around every retrieval. Code inspection establishes only eligible body paths are hashed, archive-register identities remain lexical, and hashes/vector candidates share the native connection transaction. This does not claim an atomic filesystem snapshot against concurrent changes after hashing or a full index rebuild test.

Bypassing only the expected-hash check restores the original known-bad healthy response against stale source. The same independent expected-fallback assertion distinguishes the repair from the old behavior.

## Executed controls and mutations

Sixteen qualification and ordering/brief controls passed, zero failures/errors/skips. These inherited tests were independently executed and inspected; their assertions are not newly authored by this reviewer. They cover filters before limits, status/history and compact archives, raw threshold, checked cap/no-refill/order, healthy-empty versus unavailable, malformed/nonfinite scores, model isolation/cache/disable, title fallback, queryless listings and brief ordering.

| Mechanism | Safe in-process mutation | Detection |
| --- | --- | --- |
| Source freshness | Omit expected hashes from dense helper | Independent public-path probe reproduces stale healthy result; expected-fallback property fails |
| Raw threshold | Accept >= -5 instead of >= -4 | Five-summary test: one assertion failure |
| Finite scores | Remove finite guard | Failure-path test: two assertion failures |
| RRF output order | Reverse selected output | Five-summary test: one assertion failure |
| Cached-model guidance | Replace restart remedy with index-refresh-only wording | Guidance test: one assertion failure |

Each targeted test mutant had zero errors/skips and reached its relevant public response. Mutations were restored in-process; no repository files changed. The source-freshness probe is reviewer-authored; the four other detectors are inherited tests independently fault-injected. Scratch source and raw results: `/private/tmp/wf-summary5-final-qa-probe.py`, `/private/tmp/wf-summary5-final-qa-probe.json`.

## AC evidence and outstanding claims

- AC-1/2: historical frozen corpus/holdout, comparisons and labels remain preserved; no retuning occurred in this lane. Current bounded grouping/fusion mechanics retain prior evidence.
- AC-3: filters/history/archive and unchanged policy/brief controls passed. Ranking does not establish authority.
- AC-4: repaired source freshness directly verified above, with model/index/malformed-score recovery controls passing. Calling agents still judge relevance/support; model screening is not answer verification.
- AC-5/6: actual public CPU benchmark and all-24 parity/immutable-label audit passed, as detailed below. Operator-approved newly-empty replacement of irrelevant baseline is accepted; no useful-answer loss occurred.
- AC-7: support-unverified and recovery diagnostics inspected; restart guidance detector passes and catches its removal. Full evaluator privacy evidence remains inherited pending final suite.
- AC-8: targeted controls pass; canonical full suite and final document validation remain coordinator-owned and pending. Native Windows/Linux/Intel qualification is not claimed.

Typed handoff: `S5-STALE-SOURCE`, repair cycle 1, validation successful, fresh_context=true, independent=true, actor=`summary5_final_qa`, context=`summary5-final-qa-native-sqlite`. Public path executed, fixture reachable, zero unintended skips, non-vacuous assertions, known-bad detection by focused mutation; all five evidence-integrity conditions satisfied for that repair. Full QA delivery approval is not yet supplied.


## Actual public production qualification audit

Independently inspected the executable candidate and baseline scripts and recomputed quality metrics from actual ranked identities. All 24 candidate identity lists match the frozen summary5 prototype; all 24 old-public-function identity lists match the frozen production baseline. Query text and expected IDs match the frozen holdout. All eight archived evidence-file hashes verify, including linked holdout hash `32b4e8dab4514d07853a4c7e63b8393cbc640c25757659b48431ee2f73a6c757`. This is an independent audit of prior independent blind judgments, not new blind adjudication or a fresh holdout. No returned identity is unjudged.

Both runs copy the same complete native-index snapshot SHA-256 `a493472bf7ea7d53b915e1cc34804a266e0d5ce8340af23c0566b7c4953a9578`, with 291 evaluation-owned chunks excluded. Memory corpus manifests verify before/after. The candidate executes current public `memory_search_response`; baseline extracts the exact HEAD public function and uses unchanged shared helpers/current serving runtime. `ProbeIndex` only observes semantic failures. The first baseline run omitted explicit swallowed-failure assertions, so QA requested the corrected baseline: every one of its 100 calls resets and asserts `semantic_failed == False`; the resulting artifact persists false and per-case semantic-assist metadata. No parameter changed and no initial-baseline timing is used below.

| Measure | Old public function | Current public function |
| --- | ---: | ---: |
| Recall@3 / Recall@10 | 0.65625 / 0.65625 | 0.84375 / 0.84375 |
| MRR | 0.71875 | 0.83333 |
| Direct support / all returns | 11/16 (68.75%) | 15/21 (71.43%) |
| Queries with direct support | 11/16 | 15/16 |
| Adjacent returned records | 5 | 6 |
| Answerable empty | 3/16 | 1/16 |
| Nonempty no-match | 0/8 | 0/8 |
| Warm p50 / p95 / p99 ms | 596.64 / 614.03 / 654.95 | 179.76 / 192.20 / 199.85 |
| First-call latency ms | 1677.23 | 1513 (rounded) |

There are zero paired losses of a useful answer, zero judged authority conflicts, and one newly empty case, integration-10, whose baseline returned adjacent non-answering material. That case follows the explicit operator-approved acceptance revision; it is not silently excluded from recall/abstention denominators. Recall@3 gains 18.75 percentage points and p95 improves 68.70%, passing both material-benefit alternatives; current p95 is below 500 ms and baseline p95. Candidate still returns six adjacent records on integration-01 (two), 02, 04, 05 and 07. Of these, 01 (two), 02 and 05 are additions over baseline; 04 and 07 retain a baseline adjacent record. They are not verified answers. Ordinary calling agents must judge support and applicability.

Each timing run has 100 warm calls with identical cycling through the 24 cases. Both use CPUExecutionProvider, existing cross-encoder/ms-marco-MiniLM-L-6-v2, batch size one. Every candidate warm response asserts `model_relevance` and `support_verified=false`. Candidate process peak RSS is 743.4 MiB including embedding/runtime/index/model, not isolated reranker allocation. First-call timing does not evict OS caches. Native qualification remains local macOS ARM64; timing generalization, native Windows/Linux/Intel and larger-corpus deployment performance are not established by this run. Historical corpus-size/duplicate-density evidence and fresh bounded SQL controls complement this small-corpus measurement.

Independent audit script/results: `/private/tmp/wf-summary5-final-qa-audit.py` and `.json`. The coordinator retains the candidate/baseline scripts, outputs and snapshot metadata in the public qualification evidence bundle. Reviewed-path hashes still match all 12 frozen values. Canonical suite and final docs validation are the remaining AC-8 approval prerequisites.


## Final QA approval — 2026-09-17

**Approved** for delivery of the admitted implementation; no closure or commit authorization is implied. All eight required acceptance criteria have supporting verification in this report, the retained qualification evidence, and the final canonical result. No required AC is deferred.

Independently inspected `/private/tmp/wf-summary5-canonical-tests.log`: 9,126 tests across 95 files, two native workers, 628.380 seconds, OK, with 12 suite skips disclosed. This includes all 25 memory-evaluation tests, 215 memory-record tests, and 1,036 retrieval-tool tests. The suite is coordinator-executed evidence, independently audited here; this lane did not rerun it. Its twelve skips are not represented as executed coverage or zero-skip evidence. The material repair and qualification controls separately executed by this reviewer have zero unintended skips. No native Windows/Linux/Intel execution claim is added.

Independently loaded `.wavefoundry/framework/test-cache.json`: `result=ok`, `test_count=9126`, `ran_at=2026-09-17T07:17:16.542267+00:00`. Recomputed `run_tests._hash_inputs()` matches receipt hash `0cc49fa57dbf7046f46ae283d5911bb22f3a447c30ac986aa9ba756cef261fb9`. All twelve source/test/contract git-blob fingerprints still match the repaired freeze. The framework-scoped receipt is current; it does not independently guarantee later documentation edits. Full MCP docs validation passed after qualification artifacts; a fresh final lint follows this report update.

Typed approval facts: role=`qa-reviewer`, actor=`summary5_final_qa`, context=`summary5-final-qa-native-sqlite`, verdict=`approved`, fresh_context=true, independent=true. The reviewer did not author the implementation or repair. Evidence reference: this report plus `summary5-production-qualification.md` and its bundled scripts/raw outputs. Source-freshness repair cycle 1 is verified; original known-bad behavior is detected by an independent producer-shaped public-path probe and focused safe mutation. Claims retain the six adjacent-result, non-atomic-filesystem, small-holdout and local-platform limitations recorded above. Calling-agent support judgment remains required.
