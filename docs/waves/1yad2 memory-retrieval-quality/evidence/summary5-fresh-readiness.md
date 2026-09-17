# Fresh summary5 integration readiness

Owner: Engineering
Status: active
Last verified: 2026-09-17

## Verdict and identity

**Approved for readiness:** wave-council, code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer and security-reviewer. This approves the revised gated implementation, not adoption, delivery, closure or a commit. No substantive readiness blocker remains. AC-3 through AC-8 remain open until their implementation evidence exists.

Reviewer `/root/summary5_readiness`; context `1yad2-summary5-fresh-readiness-20260917`. This worker started without retained implementation or recheck context and implemented no source or repair. It independently inspected the actual plan and current source and formed its own assessment; predecessor reviews supply attributed context, not substitute proof. All seven judgments below share this one fresh reviewer context: these are sequential specialist lenses and a council synthesis, not seven isolated agents. The separately performed primer and docs-contract seat are documented in readiness-integration.md and qa-integration-readiness.md; this worker did not impersonate those seats. `fresh_context: true`, `independent: true` describe this review, not those earlier contexts.

Reviewed full change SHA-256: `6028f1ca8beb2a232a7328537f99915497e04ff6894091e86161f85ee7db7d92`.
Baseline server_impl.py SHA-256: `af9eb334afe4519f4619000c26eadf40c188c4764fc92c9dd80fda62c0f29e44`.
Frozen parameter-file SHA-256: `438a7c52dad904959659ed0cc7d1a03afdf945f57dc5e44901630e2029d06e92`.
The private holdout/label file was not opened, scored or inferred. No lifecycle state or source was edited.

## Independent current-tree assessment

MCP code_read inspected these resolvable source anchors:

- server_impl.memory_search_response: current filters precede optional docs search; lexical recovery requires all tokens; semantic assist exceptions currently disappear; _memory_ranked supplies policy ordering. The selected change must replace explicit-query retrieval and its diagnostics while retaining the existing listing branch.
- server_impl._memory_view: status, confidence, validation, evidence, archive and successor fields already have a centralized projection. Preserve that projection rather than treating model qualification as authority.
- server_impl._memory_ranked and memory_brief_response: the latter uses policy ordering directly. Keep that shared policy implementation intact for briefings and queryless listing; explicit-query order can be restored separately after computing metadata.
- Registered server_impl.memory_search: current documentation promises silent degradation and confidence ordering. It must change with the explicit-query contract; the current wording is historical baseline, not compliant final documentation.
- memory_eval.lexical_bm25_scores and reciprocal_rank_fusion: BM25 requires distinct IDs and ranks positive matches deterministically; RRF is deterministic but assumes deduplicated channel identities. Production must preserve that precondition and cap each channel before fusion.
- sqlite_vector_store.dense_path_scores: eligible paths are bound through json_each, canonical paths are grouped before LIMIT, nonfinite distances reject, coverage is reported, and the connection closes. Returned-row bounds do not bound eligible-chunk distance work. Compact archive identities cannot be collapsed by their shared register path.
- WaveIndex._get_reranker and accel_embedder.make_reranker: current shared cache is protected by a lock, but make_reranker(model, [CPUExecutionProvider]) can still discover available GPU providers. A CPU-only argument is therefore not CPU proof. A separately cached CPU StaticShapeReranker or equivalent explicit CPU construction must preserve disabled-model handling, model identity, initialization synchronization and failure recovery without changing the shared provider or process environment. This is an implementation control covered by the approved isolation requirement, not an assertion that CPU integration exists.

The actual source independently confirms that this is a material explicit-query policy change. Merely changing a top_n or swapping rank scores would not implement the plan. The current source is still the production baseline; no fresh qualification claim is inferred from previous experiments.

## Lane decisions and falsifiers

| Lane | Readiness judgment | Delivery falsifier / remaining proof |
| --- | --- | --- |
| Code | Approved: fixed dense20/lexical20, equal RRF k60, finite raw >= -4 on available first min(5,count) identities, summary with title fallback, no refill is implementable. | Sixth identity admitted; score count/order misalignment; bool/string/NaN/Inf accepted as valid score; confidence sorting changes accepted RRF order. Limits below five constrain output, not identity selection. |
| QA | Approved: untouched 24+ query gate, eight negatives, complete paired return adjudication and fixed precision nonregression can reject the candidate. | Any baseline/candidate return omitted from blind adjudication; unjudged counted correct; zero denominator called perfect; retuning after outcomes; a paired new empty hidden by a net gain. |
| Architecture | Approved: policy exception is explicit free-text only; history and compact entries remain eligible without compulsory re-embedding. | Empty-query, target-only, briefing or advisory policy changes; relevance changes status/confidence/successor; archive entry identities collapsed. |
| Docs-contract | Approved: selected method and unavailable state have an explicit public contract, and support stays unverified. | Tool/spec/reference says passing score proves direct support; healthy zero and unavailable fallback are conflated; old non-adoption is rewritten as if the original experiment passed. |
| Performance | Approved: fixed CPU p95 <=500 ms, no worse than paired baseline, material benefit and 100-call gate remain enforceable. | GPU timings credited as CPU; failed/fallback timings credited as qualified serving; physical scan work hidden behind result caps; cold private model construction omitted. |
| Security | Approved: no new authority boundary is proposed; current path-bound SQL and read-only retrieval are usable. | Process-global provider/environment mutation; automatic download/reindex repair on query; raw query/model exception leaked in aggregate evaluation diagnostics. Operator-owned local memory content is trusted under the existing threat model; a poor hit is a correctness issue, not invented privilege escalation. |
| Council | Approved: no unaddressed disagreement after independent source inspection and the attributed isolated primer/docs seat. | Any failed gate silently relaxed or old evidence reused to claim fresh qualification. Failed qualification retains non-adoption. |

The strongest challenge is unchanged: a logit is not answer support. Four previously observed adjacent tails are reported by prior QA; this reviewer did not re-score them. Their existence motivates full blind record adjudication, including every baseline return and negative-query return. The fixed paired precision floor establishes nonregression, not universal accuracy. Pool and deduplicate query-record pairs while hiding variant, rank, score and expected labels; the blind judge must be neither tuner nor label author. Report contradictions and per-query newly added adjacent tails. These constraints are consistent with the revised gates and QA protocol.

## Executed bounded readiness controls

Executed a read-only python3 -B probe against the actual admitted change and current source. Budget: six single-clause in-memory omissions, three baseline source assertions, frozen-parameter equality and three fingerprints. All selected controls executed without skips; no models or suites were required for this readiness judgment.

The probe extracts text between `## Production integration decision` and `## Scope`. For each literal clause below it asserts presence in the actual section, replaces only that clause with OMITTED in an in-memory copy, and asserts the same clause is absent. Each actual plan control passed and each omitted condition was rejected. Semantic interpretation was checked against the lane falsifiers above; these textual controls establish plan completeness, not product enforcement.

| Probe | Exact required clause / known-bad omission |
| --- | --- |
| SF-CODE | No unchecked tail, refill or threshold tuning on observed holdout. |
| SF-QA | unjudged records prevent a precision qualification, never count as correct. |
| SF-ARCH | relevance does not establish authority or resolve contradictions. |
| SF-DOC | not verified answer support. |
| SF-PERF | Retain 500 ms CPU p95 |
| SF-SEC | without mutating a shared global provider or affecting other search paths. |

Observed: six actual checks accepted and six omissions rejected. Adjacent source controls parsed server_impl.py with ast, extracted memory_search_response, and asserted: `if target or symbol:` precedes `index.search_docs`; `all(t in haystack for t in tokens)` exists; and `relevance_rank_by_id=semantic_hit_order if query else None` exists. All three passed. These independently corroborate the existing eligibility/recovery/query-policy seams; they are not runtime tests. Frozen parameters exactly matched semantic=20, lexical=20, rrf_k=60, qualification_cap=5, representation=summary or title, raw_logit_cutoff=-4, provider=CPUExecutionProvider. Hashes above were computed from bytes during the same execution.

## Evidence facts for typed authoring

- claim_kind: approval; phase: readiness; required_for_approval: true; execution_status: executed.
- proposition: the current revised plan and inspected production seams support bounded, isolated implementation with falsifiable qualification and truthful fallback/support semantics.
- counterexample_or_failure_condition: omit any SF constraint, change policy outside explicit queries, accept incomplete adjudication or substitute shared GPU provider selection for CPU proof.
- public_path: admitted change Production integration decision and Fresh integration verification gates, the actual readiness contract boundary; current registered memory_search source was inspected, not invoked as a candidate implementation.
- command_or_fixture: python3 -B; section extraction, six literal-presence/omission pairs, AST source assertions and SHA-256 calculation as specified above.
- expected: actual contract retains all six controls; every weakened copy loses the relevant requirement; source confirms existing preservation seams.
- observed: 6/6 actual controls, 6/6 rejected omissions, 3/3 baseline assertions and exact frozen parameter equality; no private labels read.
- artifact_or_test_id: docs/waves/1yad2 memory-retrieval-quality/evidence/summary5-fresh-readiness.md, SF-CODE/SF-QA/SF-ARCH/SF-DOC/SF-PERF/SF-SEC.
- adjacent_controls: actual unchanged contract beside each omitted copy; independently inspected current source beside policy preservation requirements.
- limitations: no new candidate exists in inspected source; no runtime model/provider-race/timing, holdout adjudication, suite, final-doc parity or native Windows/Linux proof is supplied here. Static presence controls do not establish runtime behavior. Prior reviews were read as attributed context and challenged using current source.
- safety_and_authorization: assigned read-only readiness review and single evidence document; bad proposals existed only as in-memory strings.
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
    "context_id": "1yad2-summary5-fresh-readiness-20260917",
    "fresh_context": true,
    "independent": true
  }
}
```

For each specialist approval use its exact lane actor with this same disclosed context and the corresponding lane judgment/control. The five booleans attest only to the executed readiness review; they do not attest to unimplemented product behavior or separate agent contexts. Coordinator owns typed lifecycle receipts, full docs validation and renewed readiness before source edits.
