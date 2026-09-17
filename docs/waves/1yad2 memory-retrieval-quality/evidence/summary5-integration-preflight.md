# Summary5 integration preflight

Owner: Engineering
Status: active
Last verified: 2026-09-17

## Frozen comparison

Independent QA authored 24 fresh cases (16 answerable and eight conceptual near-topic negatives). The selected summary5/-4 candidate and CPU pipeline were frozen before scoring; prior examples were development only. Source remained unchanged. Each runtime had 100 warm calls on the same local snapshot. Exact scripts, frozen manifests, labels, outputs, timings and blind precision packets/verdicts are retained in summary5-integration-preflight.json.gz.

| Measure | Existing production | Frozen summary5 candidate |
| --- | ---: | ---: |
| Recall@3 | 0.65625 | 0.84375 |
| Recall@10 | 0.65625 | 0.84375 |
| MRR | 0.71875 | 0.83333 |
| Useful answer against original expected sets | 12/16 | 15/16 |
| Empty answerable response | 3/16 | 1/16 |
| Nonempty no-match response | 0/8 | 0/8 |
| Warm p95 ms | 693.8 | 200.0 |
| Blind direct-support returned records | 11/16 (68.75%) | 15/21 (71.43%) |
| Queries with blind direct support | 11/16 | 15/16 |
| Adjacent, non-answering returned records | 5 | 6 |

Precision denominator includes every returned record, including negative-query returns. Variant/rank/score/expected labels were hidden from the separate adjudicator. The label author independently audits rather than claiming blind adjudication. Precision is a small-sample observation, not a universal guarantee or an assertion that every returned record is supported. The candidate adds useful records and also has six weak adjacent returns; metadata must not call them verified answers. Reranker scores are not authority.

## Explicit operator decision

Integration-10 is newly empty, while production returned a non-answering record. Integration-13 replaces one labelled relevant record with a different labelled relevant record and retains a useful answer. There is no loss of a query that production answered usefully. The original strict paired-new-empty veto therefore failed on integration-10 despite improved useful-answer coverage.

After seeing this edge case, the operator said increased useful results are worth doing and authorized proceeding. The plan now blocks paired loss of useful answers rather than an empty response replacing an irrelevant one. This is an explicit post-observation acceptance revision, not an unchanged predeclared pass. All frozen algorithm parameters, false-positive, pooled precision, aggregate recall/MRR, latency and model constraints remain unchanged. No threshold was lowered to rescue integration-10 (its relevant memory scored -4.178 against -4).

## Next verification

This run compares the frozen prototype against the old public path; actual production integration must reproduce candidate ranking, filters and metadata on the public path, pass recovery/mutation tests and the canonical suite, then receive independent delivery review. Agent validation here means independent evaluation/review and normal caller evidence judgment; the local search implementation makes no extra agent/model-service call. No production source changes were made by this preflight.
