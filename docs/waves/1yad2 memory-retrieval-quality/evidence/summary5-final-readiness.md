# Final summary5 acceptance readiness

Owner: Engineering
Status: active
Last verified: 2026-09-17

## Verdict and review identity

**Approved for readiness** from code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer and security-reviewer. The council substantive synthesis approves implementing and verifying this revised contract. This is not adoption, delivery, closure or commit approval. The coordinator owns typed receipts and the readiness transition.

Reviewer `/root/summary5_final_readiness`; context `1yad2-summary5-final-readiness-20260917`. This worker began without retained implementation or recheck context and implemented no source or repair: `fresh_context: true`, `independent: true`. All six specialist judgments and this synthesis share one fresh context; they are not seven isolated reviews. Prior reviews were read as attributed evidence and independently assessed, not treated as substitute proof.

Reviewed change SHA-256: `4276f03a8b934f85649219fab71dfd8d1b5ea0cca0a290dce5722bfdfd32a6f4`.
Current server_impl.py SHA-256: `af9eb334afe4519f4619000c26eadf40c188c4764fc92c9dd80fda62c0f29e44`, identical to the prior fresh review's baseline.

## Independent assessment

MCP code_read inspected the current integration decision and verification gates, server_impl.memory_search_response at lines 11710–11807, and the prior [fresh readiness](summary5-fresh-readiness.md), [integration review](readiness-integration.md) and [QA/docs seat](qa-integration-readiness.md). The current source still uses optional docs-wide search, all-token lexical matching and policy ordering. It filters kind/target/symbol before retrieval, preserves archive-entry loading and projects existing metadata. The proposed memory-scoped RRF/CPU summary qualification is not already implemented by this baseline.

The operator acceptance revision is reasonable and bounded: an empty response replacing a baseline with no useful support is reported but does not itself block adoption; losing a previously useful answer does block. This does not make empty output successful, remove misses from metric denominators or license weaker precision. Useful-answer success, Recall@3/10/MRR, paired useful-answer preservation, complete per-record precision, no-match false positives and CPU latency remain gates. The plan explicitly calls this a later operator-approved acceptance revision, not a predeclared unchanged threshold. Prior QA wording that prohibited every additional empty is historical and superseded only on that point.

Agents validate evaluation evidence and review; the serving design remains local CPU qualification using the existing reranker. No extra agent call, new model, dependency, migration or global ranking change is authorized. Parameters remain dense20/lexical20, equal RRF k60, summary/title fallback, first available five identities, finite raw logit >= -4, no refill and at most min(limit,5) results. A screened hit does not establish direct support or authority.

| Lane | Readiness decision and delivery falsifier |
| --- | --- |
| Code | Approved. The bounded explicit-query branch is implementable. Reject unchecked tails, malformed score alignment, nonfinite scores, refill and confidence sorting of accepted RRF results. |
| QA | Approved. Every baseline/candidate return needs independent blind adjudication; unjudged prevents qualification. Reject hiding paired useful-answer losses behind a net gain, counting empty precision as perfect or silently changing another gate. Report new empties separately. |
| Architecture | Approved. Queryless/target-only listings, briefings, advisories, provenance and authority remain unchanged. Reject collapsed compact archive identities, mandatory archive re-embedding or ranking-based conflict resolution. |
| Docs-contract | Approved. Public method, checked cap, unavailable fallback and support-unverified semantics must match delivery. Reject claims that score means support, agents run on every search, or the revised empty gate was unchanged before scoring. |
| Performance | Approved. Retain CPU p95 <=500 ms and no worse than baseline, 100 warm calls, cold timing and material benefit. Reject GPU-as-CPU evidence, failure timing credited as success and result caps presented as scan-work caps. |
| Security | Approved. Existing local retrieval boundary is retained. Reject shared provider/environment mutation, automatic model/index repair and raw query/model-error leakage through aggregate diagnostics. |

## Council synthesis

The assigned standard-depth targeted review uses the separately performed isolated red-team primer and independent docs-contract seat documented in readiness-integration.md and qa-integration-readiness.md. The coordinator supplied the authoritative wf_prepare_wave derived roster: council_brief.council_seats is red-team (fixed) plus docs-contract-reviewer (rotating), with reason “Bound to current review-policy receipt”; the receipt selects primer_depth standard and retains all six specialist lanes. The coordinator reports that the subsequent ready call confirmed the same roster. Those lifecycle tool results are attributed to the coordinator, not executed by this worker; delivery_mode alone was not used to infer a reduced readiness roster. This worker did not rerun or impersonate those seats. The same earlier QA worker authored that docs seat, and the earlier primer worker also moderated; those shared contexts remain disclosed. This report adds a fresh independent synthesis and six sequential specialist lenses, not a claim of a newly executed generic five-seat council.

The strongest challenge remains a good query-level result concealing weak individual tails. Complete blind record adjudication, paired precision nonregression, explicit support-unverified semantics and newly added adjacent-tail reporting answer it without pretending the score proves support. The strongest alternative is retaining production unchanged: it is better if any remaining gate fails, and remains the required failure branch. Agent answer-support validation is not a qualified serving alternative in this scope. No substantive disagreement remains; the only changed acceptance term is explicitly reconciled above. Recommended delivery improvement: show paired new-empty and lost-useful-answer counts together, alongside precision and added adjacent tails, so readers can inspect the accepted tradeoff directly.

## Executed readiness controls

Executed one parameterized read-only `python3 -B` fixture with eight current-plan/known-bad-omission pairs, three AST source seam assertions and SHA-256 comparisons. The fixture extracts the text between `## Production integration decision` and `## Scope`; it asserts each clause below exists, replaces only that clause with `OMITTED` in an in-memory copy, and rejects that weakened copy by the same presence criterion. Semantic rejection reasons are the lane judgments above. These checks establish contract completeness, not runtime enforcement.

| Control | Required clause |
| --- | --- |
| FINAL-CODE | No unchecked tail, refill or threshold tuning on observed holdout. |
| FINAL-QA | unjudged records prevent a precision qualification, never count as correct. |
| FINAL-ARCH | relevance does not establish authority or resolve contradictions. |
| FINAL-DOC | not verified answer support. |
| FINAL-PERF | Retain 500 ms CPU p95 |
| FINAL-SEC | without mutating a shared global provider or affecting other search paths. |
| FINAL-ACCEPT | block on loss of a useful answer, not loss of an irrelevant nonempty response. |
| FINAL-HISTORY | disclosed operator-approved acceptance revision after the preflight, not an unchanged predeclared gate. |

Observed: 8/8 actual clauses accepted; 8/8 omissions rejected. AST extraction of memory_search_response confirmed `if target or symbol:` precedes `index.search_docs`, `all(t in haystack for t in tokens)` exists, and `relevance_rank_by_id=semantic_hit_order if query else None` exists: 3/3 passed. The complete server file hash matched the prior fresh review. No model or production endpoint was invoked.

## Evidence facts for typed authoring

- claim_kind: approval; phase: readiness; required_for_approval: true; execution_status: executed.
- proposition: the revised acceptance gate preserves useful-answer and precision protections while transparently allowing empty output to replace irrelevant output; all six implementation boundaries remain explicit.
- counterexample_or_failure_condition: any named omission, hidden paired useful-answer loss, unjudged precision, unsupported authority claim or misrepresentation of the later gate revision.
- public_path: admitted change's Production integration decision and Fresh integration verification gates; this is the readiness contract boundary, not a running new candidate.
- command_or_fixture: python3 -B, the section extraction, eight literal presence/omission pairs, three AST assertions and SHA-256 checks specified above.
- expected: current contract passes, weakened contracts fail, current source remains baseline. observed: 8/8, 8/8, 3/3 and identical baseline server hash.
- artifact_or_test_id: this document, FINAL-CODE through FINAL-HISTORY.
- adjacent_controls: intact current clause beside each omission; baseline source eligibility/recovery/query-policy seams.
- limitations: private holdout queries, labels and result files were not opened or scored; summaries present in the plan and prior reviews were seen but not independently verified. No runtime model/provider race, candidate timing, implementation fault mutation, suite, final documentation parity or native-platform proof is supplied. No new tool/model dependency is proposed by the plan; this is not an exhaustive dependency audit.
- safety_and_authorization: assigned review and this single evidence artifact; bad proposals existed only in memory; no source, lifecycle state or holdout file was modified.
- probe_class: local_safe; authorization_status: authorized; safe_boundary: false; unexecuted_remainder_prohibited: false; universal_claim: false.

```json
{
  "integrity_checks": {
    "test_ran_without_unintended_skip": true,
    "public_path_reached": true,
    "boundary_values_realistic": true,
    "assertions_non_vacuous": true,
    "known_bad_detected": true,
    "known_bad_detection_method": "readiness-safe-control"
  },
  "verification_context": {
    "actor": "wave-council",
    "context_id": "1yad2-summary5-final-readiness-20260917",
    "fresh_context": true,
    "independent": true
  }
}
```

For each specialist event, use its exact lane actor and this same context, with the corresponding judgment/control. These facts attest to executed readiness review only. The coordinator must record current approvals and renew readiness before implementation; final qualification and delivery review remain mandatory.
