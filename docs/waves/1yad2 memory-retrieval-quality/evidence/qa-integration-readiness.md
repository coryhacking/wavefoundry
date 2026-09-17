# Independent QA integration readiness

Owner: Engineering
Status: active
Last verified: 2026-09-17

Reviewer: `/root/memory_holdout`, independent from ranker implementation/tuning.
Verdict: **approved for the revised integration implementation**, subject to the plan's fresh qualification and delivery gates. This is not an adoption, delivery, closure or commit approval.

## Frozen protocol and independent evidence

Reviewed the revised Production integration decision and Fresh integration verification gates in change `1yad1-enh`. The selected design is memory-scoped dense20 and lexical20, equal RRF k60, summary-only CPU qualification of the first five identities at finite raw logit >= -4, no refill, and output capped by both five and the requested limit. Parameters must be declared frozen before the coordinator reads the new private questions or any outcomes. Previously observed questions are development/regression only.

New private QA holdout: 24 distinct queries, 16 positive and eight broad near-topic conceptual negatives, grounded in the frozen 119 eligible bodies plus 13 compact archive entries. File SHA-256: `32b4e8dab4514d07853a4c7e63b8393cbc640c25757659b48431ee2f73a6c757`. This review discloses no query text. I executed checks of that file hash, corpus identity, case count, unique queries, eight negative cases and eligibility of every labelled identity. No models, rankers or holdout scoring were called.

Original expected sets remain the primary recall labels. Every returned baseline and candidate record needs a separate blind direct-support adjudication, including all baseline records even if its result limit is larger. Pool/deduplicate query-record pairs, hide source variant, rank, raw score and expected labels, and provide the exact query and frozen record evidence. The adjudicator must not be the label author or tuner. I authored the labels and therefore cannot claim that blind role; I can audit mappings, attribution and metrics afterward. Classify direct_support, adjacent_context and irrelevant_or_unsupported, with an explicit conflict/authority flag. Retain rationale and exact evidence where support is claimed. An unjudged record prevents precision qualification.

## Gates and limits

Pooled direct-support precision counts direct-support returned records over **all** returned records, including negative-query returns. Adjacent context is not direct support; report it separately. No fabricated absolute precision threshold is introduced: candidate precision must meet or exceed the paired production baseline. An empty denominator is unavailable rather than perfect precision. Also retain useful-answer success, Recall@3/10, MRR, no additional paired empty answerable response, and no increased no-match false-positive queries. Publish paired changes, not only net totals. The 500 ms CPU p95 ceiling and material-benefit requirement stay fixed.

The four previously observed weak tails are not claimed repaired. Honest support-unverified metadata limits the claim agents may make, but does not convert a weak hit into correct support. Fresh precision qualification still has to pass. No unsupported conflict or authority promotion is allowed. A failed gate means retain non-adoption or design a new explicitly reviewed candidate; do not retune this holdout.

The native CPU baseline and candidate must use the same existing embedding and CPU reranker artifacts, tokenizer/preprocessing and precision. Record actual provider/model hashes and verify the candidate representation matches the frozen summary/title rule. Do not change a shared global provider to force CPU or inadvertently alter ordinary code/docs retrieval. Timing includes eligibility, embedding, candidate selection and qualifying work; unavailable fallbacks get no valid serving-latency credit. Native Windows/Linux execution remains unproven until actually run.

## Required discriminating execution controls

- Filters before caps: status, kind, exact target/symbol, compact archives with shared manifest paths, explicit historical bodies without required re-embedding, duplicates and missing eligible coverage.
- No-query and target-only listing preserve old policy ordering; briefing/advisories remain unchanged. Provenance, validation and successor metadata survive.
- Limits below five, empty candidate sets and fewer than five eligible candidates; no unchecked tail or replacement after a rejection.
- Missing database, valid code-only database, stale/incomplete epoch, partial vector coverage, embedder failure, unavailable/throwing reranker, malformed count/type and NaN/Inf logits. Each infrastructure failure must exercise actual public lexical-policy fallback and explicit unavailable metadata; a healthy zero-qualified result must be distinguishable.
- Known-bad mutations must demonstrate that tests reject confidence-first accidental reordering, unchecked tails, filter-after-cap, silent lexical-success classification and qualification metadata asserting verified answer support.
- Re-run focused tests, full canonical suite, final docs validation and independent delivery review against final source fingerprints. Reviewer-authored scenarios are not substitutes for executed production-path tests.

The plan names these obligations and permits failure without silently changing its gates, so no QA readiness blocker remains. Independent blind per-record adjudication and actual CPU parity verification remain mandatory implementation evidence, not assumptions discharged by this approval.

## Separate docs-contract council seat

Role/context disclosure: the same `/root/memory_holdout` worker also performed this docs-contract readiness review. It is independent of the primer and implementer but **not** a second independent context from the QA review above. Verdict: **docs-contract readiness approved**, with the following implementation obligations already named by the revised plan.

Current behavior was checked directly through MCP source reads: `server_impl.py:11743` filters targets before retrieval; `:11749-11758` catches optional docs-search failure; `:11772-11781` unions semantic identities with all-token containment and applies `_memory_ranked`; `:11803` reports only semantic_assist. The registered `memory_search` description at `:33807-33814` currently advertises confidence/freshness ranking. Search architecture's Agent memory retrieval paragraph and the tool spec's Adaptive memory freshness section accurately describe that current ordering; they must become conditional on query versus queryless/fallback paths when integration lands. The memory evaluation reference's Current qualification gate and result section currently says production remains unchanged; preserve the historical result but distinguish the later integration decision rather than rewriting history or leaving it as the current contract.

The revised plan owns these carriers and requires tool-visible retrieval method, qualification availability and checked cap. It explicitly preserves confidence/provenance/successor metadata and forbids equating a score with authority. That addresses the primer's strongest challenge. The strongest alternative remains keeping production unchanged until complete precision evidence passes; the plan's failed-gate/non-adoption branch must remain executable and honestly described.

### Contract counterexamples examined

| Known-bad proposed wording or behavior | Why the reviewed plan rejects it |
| --- | --- |
| “Every returned record directly supports the answer because its logit passed.” | A raw model score only screens relevance; four known adjacent tails disprove direct-support equivalence. Metadata must say support is unverified. |
| “Precision is correct records among the candidate's five positives.” | The denominator includes every returned record from both systems and negative queries; omitting baseline tails or negatives changes the comparison. |
| “An unjudged record is harmless context and counts as correct.” | Unjudged prevents precision qualification; adjacent_context is separate from direct_support. |
| “A high score on one record admits the remainder of the candidate list.” | Every returned record must be individually checked within the fixed first five; no unchecked tail or refill. |
| “No results means the repository has no useful memory.” | Healthy zero-qualified and unavailable infrastructure are different states; absence of a retrieved record is not proof of absent guidance. |
| “Fallback is the same qualified method, just with fewer results.” | Existing lexical-policy recovery requires explicit unavailable/fallback status; it is not model-qualified success. |
| “The newest or first-ranked conflicting active record is authoritative.” | Preserve confidence/status/validation/successor evidence; ranking does not resolve contradictory active claims or infer supersession. |

These are plan-level semantic counterexample checks, not executed source mutants or a claim that final docs already encode the new runtime. Delivery review must compare actual response fields and registered descriptions to the updated architecture/spec/reference text, including low-confidence records and explicit history. Queryless listing, briefing and unsolicited advisories must retain their existing policy description while free-text search documents the new ordering. No frozen query text was disclosed during this review.
