# Independent prepare lane reviews

Owner: Engineering
Status: active
Last verified: 2026-09-16

## Scope and independence

Phase: PREPARE. Reviewed the admitted memory-retrieval change and corrected readiness contract, current source seams, and the independent [authority decision](authority-decision.md). This reviewer did not author the retrieval implementation and made no source edits. The code, security and performance reviews below were performed sequentially by the same independent reviewer; they are distinct lane judgments, not claims of three isolated agents. The coordinator owns typed approval events. QA has separate ownership of holdout judgments.

These are plan/readiness approvals. No production integration, SQL implementation, new evaluator behavior, holdout result, latency improvement or model qualification is approved as delivered. All new mechanisms still require implementation and delivery evidence.

## Code-reviewer: approved

The bounded plan preserves a real public baseline, distinguishes candidate-source improvements from fusion, and permits non-adoption. Current source substantiates its diagnosis: memory_eval.run_curated uses sampled self-summary queries; public memory_search filters docs hits after the candidate limit; memory_policy_sort_key places confidence and freshness before relevance. The independent authority decision names that changed invariant rather than claiming relevance-first preserves the old ordering.

Required implementation controls are already in the admitted contract or authority decision: explicit-query scope only; eligibility before ranking; archive identity by memory_id; frozen deterministic ties/normalization; empty answerable queries retained; every nonempty negative counted; unavailable runs excluded from adoption success; finite per-record logits; and no unchecked tail backfill. Existing caller contracts are the independent reference, not a copy of the new ranker.

Re-entrant safety was checked at the existing seam. Two focused tests passed: test_curated_pass_never_rebinds_the_shared_commit_times_global and test_frozen_histories_reach_ranking_without_global_mutation. Keep frozen histories as explicit arguments; do not patch shared globals during a live evaluation. Source evidence: server_impl.py:10396-10444 and memory_eval.py:601-628.

There are no new landed guards/constants to mutate at this phase. Delivery must reject policy leakage into target-only/brief/advisory callers, post-limit eligibility filtering, empty-query denominator removal, false-positive relabeling and unavailable-as-success variants. No outstanding readiness code finding.

## Security-reviewer: approved

Overall severity: none identified within the declared local, single-operator threat model. The operator, operator-owned repository content read as data, and same-user processes remain trusted per docs/architecture/threat-model.md:17-49. No remote listener, less-trusted repository mode, new credentials, write privilege or third-party data ingestion is introduced. This review identifies correctness/privacy controls without inventing an attacker or escalation.

Verified existing seams:

- sqlite_vector_store.py:58-86 defines chunk identity/path columns, unique chunk_id, path/kind/language indexes, vector-to-chunk foreign key and FP32 byte-length constraint. New memory queries must target this actual schema, not assume a stored memory_id column or one row per record.
- sqlite_vector_store.py:154-177 binds literal values and restricts internal columns/operators; _layer restricts dynamic table selection. _open at 180-189 requests read_only=True. dense_rows at 203-219 binds the vector, predicate values and limit while using the allowlisted layer.
- server_impl.py:29450-29483 receives the configured root and returns the evaluator's aggregate report. It does not expose a caller-supplied target directory. Existing public-envelope and unavailable-report privacy tests passed in the docs-contract review.

Executed guard controls: a quoted apostrophe in a path remained a bound parameter; three unsupported filter forms, two invalid layer identifiers and three non-finite vector inputs were rejected. This checks current storage helpers, not a future query or qualifier. SQL literals must remain bound; memory eligibility must be a non-overridable query restriction, not caller-supplied arbitrary SQL. Parameterization alone does not prove logical scoping or wildcard semantics.

Before delivery, instrument new read paths for no persistent writes, no source/index repair, no escape through record paths, and no shared-global mutation. Keep detailed queries/IDs/text in explicitly requested repository-owned artifacts; ordinary MCP evaluation output must remain aggregate-only, including diagnostic values. Do not copy raw SQL exception strings or model inputs into public diagnostics. No new regex/shell surface is proposed; existing containment remains required rather than claimed newly verified. No exploit chains identified. Promotion to a less-trusted actor class would require re-review.

## Performance-reviewer: approved

This approves the measurement contract, not a speed claim. The local budget is explicit: warm end-to-end CPU p95 at most 500 ms and no worse than matched production; at least 100 timed warm calls per finalist; cold separately; p50/p95/p99; live eligible corpus plus 10x/100x synthetic timing-only controls. Quality labels do not come from synthetic scaling data.

The result caps are 20 distinct semantic plus 20 lexical identities, at most 40 fused records and 20 public results. The optional qualifier checks at most 20 records. SQL grouping before LIMIT avoids duplicate chunks consuming the materialized record budget, but exact distance computation may scan the eligible population. Report scanned rows, duplicate density and time; never call the result cap a sublinear-work guarantee. The archive register requires separate identity-preserving lexical treatment. An exhausted safety bound means incomplete/unavailable coverage, not a complete zero-result observation.

Current sqlite_vector_store.dense_rows orders exact cosine distances and limits output; no grouped-record optimization or new complexity claim is proven here. docs/architecture/performance-budget.md:24-27 records CPU reranking at batch one, so 20 optional checks can materially affect latency and must be included in finalist timing. Use matched cache conditions, public limits, model/runtime/hardware fingerprints and end-to-end response assembly; record model loading in cold timing. The no-new-dependency and no-model-change constraints remain.

The existing 1,000-record lexical evaluation budget test passed. It constructs and scores all 1,000 records and checks its registered contention-safe budget; it does not demonstrate the proposed memory SQL path, 100x scaling, qualifier latency or 500 ms end-to-end ceiling. No outstanding readiness performance finding; measured adoption remains gated.

## Architecture and docs-contract approvals

- **Architecture-reviewer: approved for the conditional policy only.** See authority-decision.md for precise relevance-first scope, per-record finite raw logit >= -4 option, 20-check cap, fallback/unavailable behavior, metadata preservation and required delivery controls. Production integration still requires every adoption gate.
- **Docs-contract-reviewer: approved readiness.** See readiness-contract-review.md. The corrected contract retains answerable empties, counts uncertain negative returns as false positives, separates physical work from materialization, adds the public baseline/shared-source ablation and preserves compact archive identities. Published specs/reference docs must describe only the eventual selected behavior or non-adoption.

## Executed evidence and integrity

Additional command:

```text
PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests python3 -B -m unittest test_memory_eval.MemoryEvalTests.test_curated_pass_never_rebinds_the_shared_commit_times_global test_memory_eval.MemoryEvalTests.test_frozen_histories_reach_ranking_without_global_mutation test_memory_eval.MemoryEvalTests.test_lexical_evaluation_has_registered_contention_safe_budget
```

Observed: 3 tests passed in 2.000 seconds on the available macOS Python 3.13 runtime. Guard probe observed: one valid quoted path bound; 3 invalid filter forms, 2 invalid layers and 3 non-finite vectors rejected. The authority checkpoint separately executed two current policy-order assertions. Earlier docs-contract evidence includes four current public/evaluator tests and direct empty/unavailable metric checks.

Five integrity facts: actual existing functions/tests were exercised; expectations came from independently read contracts and current callers; negative inputs were accepted only when rejection was expected and observed; no new implementation or holdout was substituted into the baseline; no source edits, SQL mutation, full benchmark or native-platform qualification was claimed. No whole suite or full docs lint was rerun for this bounded packet. There are no mutation survivors to report because no new landed mechanism was mutation-tested at PREPARE; the required delivery bad variants are specified above and in the authority decision.

Reviewed SHA-256 identities:

| Artifact | Digest |
| --- | --- |
| Admitted change | d9c12150250fb34d9691eba0ef8fceff0248e413e26ab6fbfdf752bb74ce1e9c |
| readiness-contract.md | e951e81becc073ccecf42fa4361768d232a3315ec4ac9f77a8ebc8c21ab52cae |
| authority-decision.md | b0edf163d3bfeea2ab556ec9fdfb7a4e0f793a48adb8657553ca4ea665d8f95a |

Approval facts supplied to the coordinator: phase PREPARE; lanes code-reviewer, security-reviewer, performance-reviewer, architecture-reviewer and docs-contract-reviewer; verdict approved within the explicit readiness limits; outstanding findings none. These facts do not replace the separately owned QA lane or council record.
