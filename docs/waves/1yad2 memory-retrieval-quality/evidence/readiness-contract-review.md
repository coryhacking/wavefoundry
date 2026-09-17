# Memory retrieval docs-contract readiness review

Owner: Engineering
Status: active
Last verified: 2026-09-16

## Verdict and scope

**Approve readiness for the evaluation-first scope.** This is an independent docs-contract-reviewer judgment, not production-adoption approval or a delivery signoff. No source code was changed. The coordinator owns typed review events. The reviewed contract includes the corrected archive identity rule and standard-depth targeted council allocation.

The current evaluator is not sufficient to qualify the proposed replacement, and the plan says so accurately. Readiness authorizes building the evidence and comparisons; changing production authority/ranking still requires the specified architecture decision and adoption gates. A non-adoption result remains successful delivery when the maintained evaluator and truthful report satisfy the admitted ACs.

## Strongest challenge and primer answers

The primer's strongest challenge is valid: candidate coverage, query relevance, and instruction authority cannot be collapsed into one ranking score. The revised contract separates all three and prevents uncertainty labels from disguising false-positive returns.

1. **Authority and public behavior:** Current policy orders exactness, confidence, status/family and effective confidence before relevance. Relevance-first is experimental for explicit free-text queries, not an already approved product invariant. Target-only queries, memory_brief and unsolicited advisories retain policy ordering. Metadata and active contradictions remain visible; no ranking score establishes authority or supersession. Architecture must approve any precise changed invariant before integration. The shared-source ablation distinguishes candidate coverage from fusion, and neither may enter production through a failed adoption gate.
2. **Evidence, bounds and failure meaning:** Independent QA owns the disjoint holdout and labels; exploratory queries are development-only. Every answerable query, including an empty return, remains in the quality denominator. Every nonempty no-match return counts as a false positive, even if uncertain. Unjudged and judged-irrelevant outputs are separate. The public production path is the baseline, with a shared-candidate-source ablation and matched result limits. At most 20 semantic plus 20 lexical identities enter fusion, with at most 20 public results. SQL may scan the eligible chunk population: bounded materialization is expressly not a claim of bounded distance computation. Physical scan counts/costs and incomplete coverage must be reported honestly. The fixed quality/effect gates and CPU latency ceilings are acceptance criteria, not existing measurements.

Archive identity clarification was necessary and is now present: compact register entries have individual memory_id values but share the manifest file; they remain individually eligible lexical candidates. Grouping body vectors by source path does not authorize collapsing register entries or claiming separate vectors for them. History opt-in uses the archived bodies. This is a resolved contract correction, not a remaining blocking finding.

## Source-verified current behavior

| Contract claim | Current implementation evidence | Review result |
| --- | --- | --- |
| Live evaluator is sampled and uses self-summary queries | memory_eval.py:535-633 loads eligible records, selects CURATED_SAMPLE_CAP, queries each selected summary and restricts expected/candidate identities to that selection | Accurate diagnosis; full-corpus independent evidence is future work |
| Public semantic memory filtering currently follows a docs limit | server_impl.py:11749-11756 calls search_docs with MEMORY_SEARCH_CAP, then filters memory paths | Accurate diagnosis; new memory-scoped retrieval must be compared with this actual baseline |
| Policy precedes semantic relevance | memory_records.py:1559-1579 places relevance after confidence/status/family/freshness | Authority change must be explicit, as the plan requires |
| No-index lexical recovery and archive eligibility are existing contracts | server_impl.py:11731-11775 loads status-filtered records/register entries, applies target/symbol filters and unions all-token containment with semantic hits | Preserve behavior and positive/negative controls |
| Register entries are distinct identities | memory_records.py:406-434 parses each manifest heading into a memory_id and archive_register_entry | Revised identity rule matches source |
| Existing evaluation cannot use recall alone to judge negatives | memory_eval.py:134-145 returns recall 1 for empty expected labels, regardless of unrelated returned hits | Dedicated false-positive metric is required; do not average negative recall into the answerable denominator |
| Unavailable evaluation is not adoption success | memory_eval.py:489-520 rejects unavailable curated evidence | Retain the fail-closed adoption meaning |

Paths in this table are relative to `.wavefoundry/framework/scripts/`. Evidence was retrieved with MCP outlines, definitions and targeted reads. Proposed SQL grouping and finalist behavior have not been implemented or performance-qualified by this review.

## Executed readiness controls

On the available macOS Python 3.13 environment, four existing tests passed in 1.151 seconds:

```text
PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests python3 -B -m unittest test_memory_eval.MemoryEvalTests.test_memory_eval_tool_reports_aggregate_only test_memory_eval.MemoryEvalTests.test_curated_unavailable_report_is_aggregate_only test_memory_eval.MemoryEvalTests.test_empty_relevance_union_yields_zero_candidates test_memory_eval.MemoryEvalTests.test_failed_gate_leaves_no_product_fusion_branch
```

These exercise the current public response function's aggregate envelope, unavailable observation, empty candidate controls and non-adoption behavior. They do not prove the proposed evaluator's privacy or quality. The privacy test checks forbidden structural keys; future tests must also cover query/identity leakage through values and diagnostics.

A separate direct function probe verified four exact expectations: answerable empty recall is 0; answerable empty reciprocal rank is 0; the existing negative-label recall convention is 1 even for an unrelated returned ID; unavailable curated evidence rejects current adoption. All assertions passed. This exposes the need for the declared separate negative metric without claiming a new implementation.

Evidence integrity: (1) existing source functions and tests were executed; (2) no proposed ranking was substituted for the public baseline; (3) positive empty-result and unavailable controls were checked; (4) source was not mutated, and no holdout was scored; (5) conclusions remain readiness-only, with no full-corpus, CPU scaling, model-quality or native-platform qualification claim.

## Required implementation and delivery follow-through

- Freeze normalization population, any relevance representation/threshold and the complete matched timing protocol before holdout scoring. Include model loading in cold measurements and embedding, optional qualification, assembly and response costs in warm end-to-end timing; use identical cache conditions and output limits.
- Test multiple compact entries in one manifest, eligible body duplicates, history opt-in and exhausted safety bounds. Report incomplete/unavailable coverage rather than silently treating it as complete.
- Update the evaluator reference, MCP tool contract and listed architecture documents to distinguish the old sampled evaluator from delivered full-corpus evidence and to state the selected policy or non-adoption. No seed/generated-surface edits or packaging-version assertions are authorized by this readiness review.
- Preserve aggregate-only ordinary MCP output; detailed query/identity evidence belongs only in explicit repository-owned evaluation artifacts. Retain status/error distinction for infrastructure unavailability versus genuine zero relevant results.

These are existing admitted obligations and clarified verification details, not additional tuning families or a request to expand scope. No unresolved docs-contract blocker remains.

## Reviewed artifact identities

SHA-256 at review:

| Artifact | Digest |
| --- | --- |
| Admitted change document | d9c12150250fb34d9691eba0ef8fceff0248e413e26ab6fbfdf752bb74ce1e9c |
| readiness-contract.md | e951e81becc073ccecf42fa4361768d232a3315ec4ac9f77a8ebc8c21ab52cae |
| readiness-primer.md | 261bcf49291d4cb6aa28186c621cb1a3b92eac123788a5664b61bbc980bfa9c0 |

The contract file is a readiness decision packet, not a statement that current production already meets the new metrics. The reviewed plan's production changes remain gated.
