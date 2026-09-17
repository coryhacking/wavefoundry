# Memory query relevance and authority decision

Owner: Engineering
Status: active
Last verified: 2026-09-16

## Architecture checkpoint verdict

**Approve the precise conditional policy below for experiments and, only after all frozen adoption gates pass, production integration.** This is the named architecture preintegration decision required by the admitted plan. It does not itself authorize integration, declare a winning ranker, qualify the optional relevance threshold, or replace delivery review. No source or lifecycle event was edited by this reviewer.

The change intentionally relaxes the current confidence-before-relevance ordering for explicit free-text memory queries. It does not relax eligibility, change stored confidence, establish authority, or decide which contradictory instruction is correct. The evaluation-only outcome remains valid if no finalist passes.

## Approved policy

1. For an explicit nonempty free-text query, eligible candidates may be ordered primarily by the selected relevance/fusion score rather than confidence or freshness. Candidate generation and eligibility precede ranking. Exact target/symbol filters remain mandatory, including requests that combine free text with a target or symbol. Deterministic tie-breaking must be frozen before holdout scoring.
2. Target-only/symbol-only requests, empty-query listings, memory_brief and unsolicited read-tool advisories retain their current policy. Keep this change local to explicit memory search: do not rewrite the shared memory_policy_sort_key or silently change every _memory_ranked caller.
3. Rejected/stale/superseded body exclusions, explicit status/history semantics, compact archive-register distinctions and provenance remain unchanged. Identity is memory_id. A compact register entry is individually eligible lexical evidence, not an independently embedded body; history opt-in uses the actual archived body path.
4. Existing confidence, effective confidence, status, evidence, dates, validation, successor and needs-reverification metadata are preserved. Ranking must not rewrite these values, infer supersession, reconcile contradictions, or relabel a candidate as verified/current authority. Conflicting active records remain conflicting evidence; list order resolves neither validity nor precedence.
5. **No hard gate:** returned results are retrieval candidates, not verified answers. The public contract must state that meaning if adopted. Any nonempty response to a no-match query remains a false-positive return for adoption, including an uncertain/candidate-labelled response.
6. **Optional bounded qualifier:** the proposed experimental threshold is a finite raw model logit **greater than or equal to -4**, evaluated separately for each checked record using title, action_delta and summary in a deterministic frozen representation. It is not a probability, authority score, universal cutoff, or calibration claim. Freeze the exact existing model/version, field ordering/separators, missing-field handling, truncation/tokenization and candidate order before holdout. Preserve the existing model/runtime dependency constraints.
7. The qualifier checks at most 20 candidate records. Select that bounded prefix deterministically from the fused order; reject individually failing records, preserve accepted relative order, and do not append unchecked tail records to fill the result limit. Report counts for fused candidates, checked records, accepted records and omissions separately. Candidate-stage recall and final recall remain distinct. A passing record cannot qualify another record or the whole query.
8. If required semantic retrieval or the selected qualifier is unavailable, fails, or returns unusable/non-finite scores, preserve the existing public baseline fallback and mark the experimental measurement unavailable with an explicit reason. Do not quietly switch a gated experiment to ungated success, count an infrastructure failure as valid abstention, or award an adoption win from missing measurements. When the no-hard-gate variant is selected, the unused qualifier is not a dependency. A healthy available model returning zero qualifying records is a real empty result and is scored as such.
9. Only the selected complete design may enter production after the independent frozen holdout, policy controls, privacy and CPU/performance gates pass. The optional qualifier is a bounded design choice to freeze using development evidence, not another post-holdout tuning sweep. Failed or unavailable finalists preserve current production ranking, including the current candidate source; no source-only change bypasses adoption.

## Rationale and alternatives

An explicit query asks for relevant evidence. A highly trusted but unrelated lesson should not automatically outrank a directly relevant eligible lesson merely because of its trust band. Relevance-first is therefore a coherent search contract, provided callers still see the record's trust and status and no retrieval score is mistaken for instruction authority. By contrast, unsolicited advice and target briefings are policy-bearing surfaces; changing them would expand both scope and risk.

The strongest alternative is to retain current policy ordering while improving the memory-scoped candidate source. The required shared-source ablation evaluates that alternative and locates the cause of any gain. Its advantage is preserving authority-order expectations; its cost is that a relevant lower-confidence result may remain buried. Neither this review nor the exploratory one-result gain establishes which design wins. Non-adoption is preferable to weakening the declared gate after measurement.

## Boundaries and verified source

The existing MCP Server domain owns typed memory reads and local SQLite retrieval (`docs/architecture/domain-map.md`, MCP Server row and archive interaction edge). The conditional search change stays within that domain and existing storage/model boundaries. It adds no schema, model, hosted service, write action or new external dependency. Ordinary evaluation responses remain aggregate-only; detailed local evaluation output follows the existing explicit repository-owned artifact contract. Allowed-root and read-only controls must continue to hold.

Current source evidence, inspected with MCP definition/read tools:

- `.wavefoundry/framework/scripts/memory_records.py:1559`: memory_policy_sort_key places confidence/status/family/effective confidence ahead of relevance.
- `.wavefoundry/framework/scripts/server_impl.py:10361`: _memory_view preserves the status, confidence, provenance and optional validation/successor/reverification fields named above.
- `.wavefoundry/framework/scripts/server_impl.py:10396`: _memory_ranked is shared policy ordering and batches freshness history. Frozen evaluation histories are explicit overrides; do not rebind global commit-history functions in this concurrent server.
- `.wavefoundry/framework/scripts/server_impl.py:11710`: memory_search_response applies status/history, kind, target/symbol eligibility and uses semantic-plus-containment candidates before shared ranking.
- `.wavefoundry/framework/scripts/memory_records.py:406`: compact archive entries retain distinct memory_id identities despite sharing the manifest.

These observations establish the current boundary and the precise proposed invariant change. They do not verify a future SQL implementation. Any new storage query still needs inspection of the actual schema/constraints/indexes, parameterized memory scope, duplicate grouping before LIMIT, physical scan accounting and archive handling during implementation review.

## Required positive and negative controls

| Mechanism | Required positive control | Required bad variant or negative control |
| --- | --- | --- |
| Explicit-query relevance-first | Eligible lower-confidence directly relevant record can outrank higher-confidence unrelated record | Target-only/advisory/brief ordering changes: reject |
| Eligibility before ranking | Matching active record survives with metadata intact | High-score rejected/stale/superseded or wrong-target body surfaces: reject |
| Contradiction/authority separation | Both eligible conflicting records retain original evidence/status | Ranking changes status, confidence, successor or validation: reject |
| Archive identity | Multiple compact entries from one manifest remain individually discoverable | Manifest-path dedup collapses identities; history body leaks by default: reject |
| Per-record qualification | At-threshold and above-threshold finite scores pass; below-threshold fails | One passing hit admits unrelated or unchecked tail: reject |
| Qualification budget | At most 20 records checked; omitted counts explicit | Backfill evaluates or returns unchecked records beyond the frozen prefix: reject |
| Model/index failures | Existing baseline fallback returned; experiment unavailable | Failure becomes healthy empty, qualified output or ungated success: reject |
| Adoption decision | Complete frozen evidence applies every gate | Unavailable run or false-positive relabeling produces adoption: reject |

This is a preimplementation decision: these are required delivery probes, not tests claimed to pass today. No new mechanism has landed in this reviewer's scope, so there is no executed mutation table for a new implementation yet.

## Executed checkpoint and limitations

A read-only Python 3.13 probe called the current memory_policy_sort_key directly with two active decision records: confidence 0.9/relevance rank 20 beat confidence 0.6/rank 0; equal-confidence/effective-confidence records correctly used relevance rank as the later tie-break. Both assertions passed. This confirms that the approved proposed ordering changes a real existing invariant; it does not claim the relevance-first policy is implemented.

Integrity: actual existing function executed; independent context did not implement the change; no corpus mutation or holdout scoring; no model threshold/performance qualification; no native-platform claim. The earlier docs-contract readiness artifact records separate current evaluator/public-envelope tests. No additional full docs lint was run for this bounded checkpoint, per coordinator instruction.

Before any adopted behavior ships, update the memory evaluation reference, memory-search MCP contract and search/testing/performance architecture docs. Describe the actual selected candidate/qualification policy and fallback state accurately; if adoption fails, document non-adoption without advertising a retrieval improvement.
