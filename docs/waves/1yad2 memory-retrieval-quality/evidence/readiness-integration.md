# Summary5 integration readiness review

Owner: Engineering
Status: active
Last verified: 2026-09-17

## Verdict and scope

APPROVED for renewed readiness: code-reviewer, architecture-reviewer, security-reviewer, performance-reviewer and docs-contract-reviewer. The precise conditional explicit-query relevance-first policy is reaffirmed with the newly frozen summary-only top-five qualification. This approves implementation and verification of the plan, not delivered behavior or release adoption. Fresh qualification, all remaining prepare approvals, the coordinator's readiness transition and delivery review remain required.

Reviewer: `/root/python_advisory_primer`, context `1yad2-summary5-readiness-20260917`. One independent reviewer performed five sequential lane assessments and this moderator synthesis in shared context; these are not five isolated agents. The reviewer did not implement source. Prior review and blind-agent experiment context is retained (`fresh_context: false`). Separate QA ownership remains `/root/memory_holdout`; this document does not fabricate its approval or its future labels. No lifecycle calls or source edits were made.

Reviewed admitted change SHA-256: `6028f1ca8beb2a232a7328537f99915497e04ff6894091e86161f85ee7db7d92`. Governing section: **Production integration decision — 2026-09-17**, including **Fresh integration verification gates**. Historical non-adoption reports remain historical, not overwritten. AC-3 through AC-8 are correctly reopened.

## Isolated primer and resolution

The strongest challenge was query-level success concealing weak record-level tails: the prior follow-up rejected eight no-match queries but admitted four adjacent positive-query records. A passing -4 logit is not evidence of verified answer support. Strongest alternative: keep existing production until the selected frozen candidate passes fresh complete record adjudication; host-agent quote validation is a separately unqualified serving workflow.

The three primer questions concerned the precision denominator and fixed gate; failure/limit paths that could return unchecked records; and authority claims on conflicting or lower-confidence records. The revision answers them: every baseline and candidate return is independently judged, unjudged records prevent qualification, pooled direct-support precision must meet paired production precision, existing quality gates survive, no unchecked refill is allowed, fallback is explicit, and status/provenance remain unchanged. A paired baseline precision floor is a measurable predeclared rule despite not being an invented absolute percentage. It demonstrates nonregression, not universal safety. Report per-query added adjacent tails so pooling does not conceal where losses occur.

## Sequential lane judgments

| Lane | Verdict | Assessment and required implementation controls |
| --- | --- | --- |
| Code | Approved readiness | Freeze RRF k60, 20+20 candidates, deterministic order, finite raw >= -4 and the first five identities. Interpret five as the available prefix `min(5, candidate_count)`, never fabrication or refill. Validate score count/identity alignment as well as finite values; a missing or malformed score cannot qualify a neighbor. Caller limit restricts returned accepted prefix. Reusing shipped pure BM25/RRF helpers is feasible without loading golden fixtures; production must not call evaluator orchestration or import test fixtures. |
| Architecture | Approved readiness | Reaffirm relevance-first for explicit free-text queries only. Preserve exact target/symbol eligibility, independent compact archive identity, lexical history recovery, target-only/empty-query/brief/advisory ordering and every authority metadata field. Ranking does not resolve contradictions. The selected top-five summary representation supersedes the earlier experimental twenty-check/title-action-summary option for this integration only. |
| Security | Approved readiness | Existing storage helper binds the exact path list through json_each, groups canonical paths before LIMIT, and closes its connection. Reuse remains read-only and root-scoped. No automatic model/index repair, remote service or shared provider mutation is authorized. If the global reranker is GPU-backed, a privately cached CPU instance is acceptable with synchronized initialization, existing model identity and lifecycle ownership; changing the shared object's provider is not. Diagnostics must use bounded reason codes, not raw corpus text/queries/model exceptions. Aggregate evaluation privacy remains distinct from authorized memory-search records. |
| Performance | Approved readiness | Five CPU checks have plausible prior local evidence but future public-path performance remains unqualified. Retain <=500 ms and no worse than baseline CPU warm p95, 100 warm calls, fixed material gain and separately reported cold loading. Include private CPU instance load/resident memory and initialization contention when applicable. Dense result limits do not bound distance scans; BM25 reads the eligible records. Preserve physical-work, duplicate-density and scaling disclosure. No GPU-derived CPU claim or batch-agent serving claim. |
| Docs-contract | Approved readiness | Describe screened candidates with support unverified, healthy empties separately from unavailable fallback, selected method and checked cap, and unchanged confidence/status/provenance. Scope includes tool registration text, MCP spec, evaluation reference, search/testing/performance docs and release notes. Do not advertise old experimental non-adoption as the new outcome or imply known weak tails were fixed. No seed or generated surface change is needed. |

## Current-tree feasibility evidence

MCP `code_outline` then targeted `code_read` inspected `memory_eval.lexical_bm25_scores`, `reciprocal_rank_fusion`, module imports and `load_fixture`; the fixture is accessed by an explicit function, not read at module import. Import currently inserts the scripts path; reuse must not invoke the evaluator's corpus builder or orchestration. BM25 scores all eligible records and rejects duplicate identities; RRF sorts score ties by memory_id. These are reusable mechanisms, not evidence the integration has shipped.

MCP inspection of `sqlite_vector_store.dense_path_scores` confirmed bound JSON path membership, canonical chunk/vector join, group-before-limit, finite distances, coverage counts and explicit connection close. Its docstring truthfully distinguishes bounded rows from full eligible-chunk work. Prior authority-decision and prepare-lanes source assessments remain context; new provider isolation and public integration are delivery obligations, not executed claims here. Direct MCP reads succeeded; an initially guessed seed filename was absent, then the actual seed-209 path was located and read. No code_definition failure was invoked in this review.

## Readiness-safe known-bad probes

The actual plan section was loaded through a read-only Python probe. For each constraint below, the current section passed a literal presence check; an in-memory copy omitting that exact condition failed the same check. No repository plan was mutated. The substantive reasons for rejecting each proposal were independently judged before the textual check. This is a bounded plan completeness control, not a semantic parser or product mutation test.

| Probe | Deliberately bad proposal | Observed readiness result | Future delivery counterexample |
| --- | --- | --- | --- |
| RI-CODE | Omit no-unchecked-tail/refill rule | Rejected; actual plan retained rule | Passing first record admits sixth unchecked record |
| RI-ARCH | Omit no-authority/conflict-resolution boundary | Rejected; actual plan retained rule | Ranking rewrites confidence or successor |
| RI-SEC | Omit shared-global-provider prohibition | Rejected; actual plan retained rule | CPU selection mutates shared GPU provider |
| RI-PERF | Omit 500 ms CPU p95 ceiling | Rejected; actual plan retained rule | Incomplete/failed timings earn adoption |
| RI-DOC | Omit unjudged-record disqualification | Rejected; actual plan retained rule | Missing judgments counted as direct support |

Additional explicitly refuted claim: zero negative-query false positives proves all returned records are directly supported. The follow-up QA's four identified adjacent tails contradict it; honest support metadata does not repair their precision and does not exempt them from the denominator.

## Evidence record and integrity

- `claim_kind: approval`; `phase: readiness`; `required_for_approval: true`.
- `proposition`: the amended plan has explicit bounded retrieval, authority, failure, measurement and truthful-public-contract constraints sufficient for gated implementation.
- `counterexample_or_failure_condition`: any omitted constraint above, unavailable evidence treated as a pass, or authority promotion by rank.
- `execution_status: executed` for current-plan inspection and in-memory omission checks; future product behavior remains unverified.
- `public_path`: admitted change's Production integration decision, the faithful readiness boundary; no production endpoint was executed.
- `command_or_fixture`: read the named change, select text between Production integration decision and Scope, check the five quoted conditions above, replace each separately with `UNSAFE OMITTED CONDITION`, and assert its absence. This reproduces the bounded textual omission check.
- `expected`: actual plan includes all five; each omission is rejected. `observed`: five original-condition checks and five omitted-condition checks completed as expected.
- `artifact_or_test_id`: this document, RI-CODE/RI-ARCH/RI-SEC/RI-PERF/RI-DOC.
- `adjacent_controls`: actual amended plan beside each deliberately weakened copy; prior follow-up counts versus supplemental precision judgments.
- `known_bad_detection_method: readiness-safe-control`.
- `probe_class: local_safe`; `authorization_status: authorized`; `safe_boundary: false`; `unexecuted_remainder_prohibited: false`; `universal_claim: false`.
- `safety_and_authorization`: parent authorized readiness inspection and this single evidence artifact; mutations were in-memory strings only.

```json
{
  "integrity_checks": {
    "test_ran_without_unintended_skip": true,
    "public_path_reached": true,
    "boundary_values_realistic": true,
    "assertions_non_vacuous": true,
    "known_bad_detected": true
  },
  "verification_context": {
    "actor": "wave-council",
    "context_id": "1yad2-summary5-readiness-20260917",
    "fresh_context": false,
    "independent": true
  }
}
```

The five booleans apply to readiness plan controls only. For each specialist event, use that lane's actor and the same disclosed context; they do not attest to five separate executions. Limits: no new holdout scored, no model loaded, no provider race executed, no timing reproduced, no native Windows/Linux claim, no full suite or docs validation rerun. Coordinator owns validation and typed receipts. No blocking readiness gap remains under the precise interpretations above; missing future product evidence remains a delivery gate, never a presumed pass.

## Final targeted council synthesis and freshness clarification

The moderator subsequently read [qa-integration-readiness.md](qa-integration-readiness.md), including its separately performed **docs-contract council seat**. The required targeted roster is now evidenced: this worker's isolated red-team primer plus the independent `/root/memory_holdout` docs-contract seat. The second worker shares its QA and docs-contract context; this worker shares primer, five lane reviews and moderation context. Neither worker is represented as multiple isolated agents. The docs seat independently inspected current public source and published carriers and answered the primer's precision, fallback and authority questions. No contradictory seat finding remains.

**Substantive council readiness verdict: approved for the revised gated implementation.** The separate QA seat adds precise constraints consistent with the reviewed plan: blind pooled record adjudication hides variant/rank/logit/expected labels; the adjudicator is neither label author nor tuner; empty precision denominator is unavailable; actual CPU artifacts/preprocessing must match; no failure timing receives qualified serving credit. Its 24-query manifest fingerprint and pre-scoring checks are attributed to that seat, not rerun or independently inspected here. This reviewer has read no new private query or label file.

**Typed approval eligibility is distinct from the substantive verdict.** This worker retains prior reviewer/recheck and blind-experiment context but never implemented the ranker or authored its repair. Therefore `independent: true` is appropriate, while `fresh_context: false` is retained under seed-209's explicit rule that true requires no retained implementation/recheck context. The tool parameter's narrower phrase, “started without retained repair context,” could describe this worker favorably, but does not justify erasing the disclosed retained review context or claiming a newly isolated agent. The coordinator should use this artifact as evidence and route typed approval through an eligible fresh reviewer if the canonical freshness requirement applies; this document does not assert that an approval event can validly be minted for this worker. A newly named context ID alone would not create independence or freshness.

No outstanding substantive plan blocker was found. Fresh scoring, provider isolation, all source mutations and final documentation remain unexecuted delivery obligations. No lifecycle event, source edit or model run occurred during this synthesis.
