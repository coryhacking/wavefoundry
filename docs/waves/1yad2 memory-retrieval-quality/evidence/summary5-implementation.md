# Summary-five production implementation checks

Owner: Engineering
Status: active
Last verified: 2026-09-17

## Scope and independence

Implementer: `/root/memory_readiness_primer`. This actor previously authored the readiness primer/moderation and evaluation helpers; this is implementation evidence, not independent review. Production integration followed renewed readiness and the operator's approved query-relevance and useful-answer tradeoffs.

Owned edits: `server_impl.py`, shared primitives and hermetic stub in `memory_eval.py`, the memory-specific SQLite helper's promotion docstring, `test_memory_records.py`, `test_memory_eval.py`, and the explicitly superseded query invariant in `tests/eval/memory_golden.json`. No held-out queries, labels, parameters or prior measurements were modified.

## Implemented behavior

Eligible records are selected with the existing status, kind, target, symbol and archive/history rules. Individual body paths are resolved relative to the canonical repository root and converted to POSIX index paths; compact archive entries remain distinct lexical identities. Memory-scoped SQL groups body vectors by path before its twenty-record limit. BM25 supplies at most twenty lexical records; equal-weight RRF uses k=60.

Only the first five RRF identities receive raw CPU relevance scores over summary text, falling back to title only when summary is empty. Finite scores at least -4 pass; accepted records retain RRF order. There is no refill, unchecked tail, score normalization or threshold retuning. Query results are capped at min(requested limit,5). Existing decay/provenance metadata is retained independently of query ordering.

The response reports `retrieval.method`, `qualification`, `checked_candidate_cap`, `checked_candidates`, `support_verified=false`, and a fixed `fallback_reason` code. Healthy screening is `hybrid_rrf` / `model_relevance`; unavailable infrastructure uses `lexical_policy` / `unavailable` plus `memory_query_fallback`. Queryless listings remain `policy` / `not_requested`. A healthy zero-pass result does not trigger lexical refill. The calling agent assesses relevance, direct support and applicability; model screening does not verify answers or establish authority.

## CPU isolation and lifecycle

`WaveIndex._get_memory_reranker` honors the reranker-disable setting before consulting any cache. It reuses only a current-model CPU reranker, or builds `StaticShapeReranker(model, ["CPUExecutionProvider"])` under the existing per-index reranker lock. It deliberately bypasses `make_reranker`, whose CPU provider argument permits GPU discovery. A private memory cache and per-model failure marker avoid repeated construction; handler cleanup releases them. It does not replace the ordinary code/docs reranker, change global provider selection or mutate environment variables.

GPU hosts may consequently retain a separate CPU model for memory screening. Actual RSS, loaded model/provider and public serving latency require the coordinator's native benchmark; unit tests do not establish those measurements.

## Focused test execution

On macOS ARM64 with Python 3.13:

```text
PATH="/opt/homebrew/bin:/Library/Developer/CommandLineTools/usr/bin:$PATH" PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests /opt/homebrew/bin/python3 -B -m unittest test_memory_eval test_memory_records -q
Ran 238 tests in 13.213s — OK
```

An initial `test_memory_records` invocation without the corrected PATH encountered three existing Git-based decay-test errors because `/usr/bin/git` required Xcode license acceptance. The command above used the installed Command Line Tools Git and passed all tests without skips or weakening assertions.

After tightening the comparison-control assertion to require that the one deliberately superseded invariant is specifically `paraphrase`, the exact affected test was rerun:

```text
PATH="/opt/homebrew/bin:/Library/Developer/CommandLineTools/usr/bin:$PATH" PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests /opt/homebrew/bin/python3 -B -m unittest test_memory_eval.MemoryEvalTests.test_all_policy_invariants_pass -q
Ran 1 test in 1.162s — OK
```

`git diff --check` passed on the six edited source/test files. The canonical full suite and independent delivery review remain coordinator-owned. No native Windows/Linux execution or full Python 3.11 runtime execution is claimed here.

## Public-path and provider controls

All names below are in `test_memory_records.py` unless noted otherwise.

| Test | Verified behavior |
| --- | --- |
| `MemoryQueryQualificationTests.test_five_summary_checks_no_refill_and_rrf_order_is_preserved` | Exactly five summaries checked, threshold boundary, no sixth-result refill, RRF order retained despite unequal passing logits, requested limit honored |
| `test_empty_qualified_result_does_not_fall_back_or_refill` | Healthy all-rejected set remains empty even when lexical containment could return a record |
| `test_relevance_failure_never_returns_unchecked_semantic_hits` | NaN, infinity, wrong-length, boolean/string scores and exceptions trigger explicit recovery without returning unmatched dense hits or leaking exception text |
| `test_missing_stale_code_only_incomplete_and_model_disabled_recover_lexically` | Missing index, loader refusal, missing docs layer, incomplete path coverage, unavailable model and nonfinite dense scores retain eligible lexical recovery and explicit unavailable state |
| `test_filters_precede_candidate_limits_and_status_is_preserved` | Target/symbol/kind/default-status filters run before dense candidates; explicitly requested stale status remains visible |
| `test_archive_entries_keep_identity_and_unindexed_history_recovers` | Two compact entries retain separate identities; intentionally unindexed archive bodies use lexical recovery without re-embedding |
| `test_title_fallback_and_alias_root_paths` | Empty-summary title fallback and canonical source/root path mapping |
| `test_cpu_reranker_is_isolated_cached_and_respects_disable` | Direct CPU construction, caching, disable flag, GPU cache preservation and prohibition of the GPU-discovering factory |
| `test_cpu_model_failure_is_cached_without_disabling_other_search` | Failure does not repeatedly construct a model or disable ordinary search |
| `MemorySearchOrderingTests` | Approved explicit-query relevance ordering preserves visible confidence; queryless/fallback policy and briefing exact-target behavior remain intact |

The hermetic stub now drives the memory-specific candidate and raw-score seams. Its fixed passing scores test deterministic eligibility and ordering, not learned model quality. The former confidence-first paraphrase invariant is expressly replaced by the approved relevance-first query invariant. The historical confidence-first comparison consequently fails that one invariant; tests name it rather than accepting an arbitrary failure.

## Mutation evidence

Mutations were compiled into isolated test-process namespaces and restored immediately. No mutated source was written to the repository or live MCP process. Each named test passed on the delivered code and failed under its indicated mutation, with one assertion failure and zero errors:

| Mutation | Protecting test |
| --- | --- |
| Change the RRF shortlist from `[:MEMORY_QUERY_CHECK_CAP]` to `[:MEMORY_SEARCH_CAP]` | `test_five_summary_checks_no_refill_and_rrf_order_is_preserved` |
| Replace `score >= MEMORY_QUERY_MIN_LOGIT` with unconditional acceptance | `test_empty_qualified_result_does_not_fall_back_or_refill` |
| Disable the `not dense["complete"]` recovery condition | `test_missing_stale_code_only_incomplete_and_model_disabled_recover_lexically` |
| Substitute `make_reranker` for direct `StaticShapeReranker` CPU construction | `test_cpu_reranker_is_isolated_cached_and_respects_disable` |

## Unchanged paths and limitations

No ordinary code/docs vector ranking, graph search, memory_brief or unsolicited advisory algorithm was changed. Shared BM25/RRF primitives remain deterministic; comparison variants stay evaluation-only. No new model, native dependency, database format or re-embedding was introduced. Confidence, status, validation, evidence and successor metadata remain visible.

The initial implementation checked the loaded epoch and path coverage but missed changed source bytes at an existing indexed path. Independent delivery reviewers reproduced that AC-4 defect. The cycle-1 repair below adds per-body source-hash qualification; the initial implementation must not be treated as having passed that contract.

The earlier twenty-case follow-up had four weak tails; the later twenty-four-case blind integration audit had six adjacent tails. Neither set is claimed eliminated. Honest support-unverified semantics mitigate misuse; direct-support precision, paired useful-answer quality and current native latency still require independent public-path evidence. The implementation was frozen before the coordinator's benchmark. Its initial attempt refused an incomplete local index epoch; normal index recovery and the later benchmark are separate evidence, not results claimed by this report.


## Cycle-1 delivery repairs

Before editing, the implementer independently ran `/opt/homebrew/bin/python3 -B /private/tmp/wf-summary5-review-controls.py`: fresh and changed bytes both reported healthy hybrid retrieval, and a transient CPU construction failure remained cached until its failure marker was reset. Typed `repair_start` events for `S5-STALE-SOURCE` and `S5-MODEL-RECOVERY-GUIDANCE` were previewed and created before source mutation, under the shared implementer context (not independent review).

Production now hashes only eligible individual memory body files using raw SHA-256. The bounded path-to-hash map is passed to `dense_path_scores`, which checks the published docs `layer_path_state` hashes in the same read transaction as candidate-vector selection. Missing or mismatched source state returns `memory_source_state_stale` lexical recovery before qualification. Unreadable body bytes also recover lexically. Compact register identities stay lexical. No global source walk, database writes, schema changes, new model or parameter changes were introduced. This checks bytes observed during the call; it does not claim filesystem-wide transactional snapshots or immunity to edits after hashing.

Unavailable qualification now gives specific recovery guidance: check the disable setting and local model/runtime availability, use `wf setup` when provisioning is needed, and restart MCP after correcting availability to clear cached model-load failures. Refreshing the index alone is explicitly insufficient. The cache policy itself is unchanged.

Focused verification used temporary indexes only:

```text
PATH="/opt/homebrew/bin:/Library/Developer/CommandLineTools/usr/bin:$PATH" PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests /opt/homebrew/bin/python3 -B -m unittest test_memory_eval test_memory_records -q
Ran 240 tests in 12.630s — OK
```

A subsequent diagnostic-stage reason assignment was checked by the whole affected qualification class: eleven tests in 0.706s, OK. `git diff --check` also passed. No full-suite or native cross-platform qualification is claimed.

`test_source_hashes_guard_current_vectors_without_global_freshness_scan` executes the public memory function, production candidate wrapper and real read-only SQLite SQL with a deterministic distance kernel. It verifies unchanged source, an unrelated file edit, a same-size memory edit with preserved mtime, restored source, missing published hash state, SELECT-only statements and unchanged database bytes during retrieval. `test_model_failure_guidance_explains_cached_failure_recovery` asserts the explicit disable/setup/restart guidance and unavailable response.

Two safe in-process mutations in `/private/tmp/wf_summary5_repair_mutants.py` were executed and restored without repository mutations: bypass the published-hash check, and remove the MCP restart remedy. Each corresponding new test failed with one assertion failure and zero errors. These are defect-detection controls, not independent reverification or performance measurements. Public benchmark and lane clearance remain coordinator/reviewer-owned.
