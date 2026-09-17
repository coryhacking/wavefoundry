# Independent follow-up QA

Owner: Engineering
Status: active
Last verified: 2026-09-16

Date: 2026-09-17
Reviewer: /root/memory_holdout (independent label author, not ranker tuner)
Scope: scratch-only evaluation; no production adoption or repository edits.

## Integrity

Fresh label SHA-256 remains 2c9a686a2f55d6989e1672bf4c8b49eb7e070a0ec56d9cff363bd58c19ecbd4e. Parameter SHA-256 remains 7ae519b699fe3c422ea3c0ec375d3f5667ff5ccb4ca129baa2ae9392c5548d2a. The parameter file references the frozen labels and the result references the parameters. Every result query, expected set and rationale exactly matches the independently authored file. No primary labels were expanded after scoring.

I independently recomputed the following from raw rankings with Fraction arithmetic, not the implementation metric helpers:

| Variant | Recall@3 | Recall@10 | MRR | Useful answer /12 | Empty answer /12 | False-positive query /8 | Unjudged positive returns | p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Production | .62500 | .62500 | .56944 | 8 | 3 | 2 | 5 | 674.58 |
| RRF | .91667 | 1.00000 | .95833 | 12 | 0 | 8 | 225 | 112.85 |
| Summary20 | .83333 | .87500 | .87500 | 11 | 1 | 0 | 14 | 470.18 |
| Summary5 | .83333 | .87500 | .87500 | 11 | 1 | 0 | 5 | 196.21 |
| Agent5 | .91667 | .91667 | 1.00000 | 12 | 0 | 0 | 1 | unavailable |

The supplied aggregate metrics match. Summary5 reduces measured p95 by about 71% versus production. Timings describe this local run, not a native cross-platform or general-corpus result. Agent5 is an unknown-model host-agent simulation taking about 159 seconds for the 20-query batch; that is neither serving latency nor p95, and its monetary cost is unknown.

## Paired gate interpretation

Summary20 and Summary5 lose **no judged-relevant hit that production returned**. Both recover useful answers on fresh-08, fresh-09 and fresh-11. Their one empty answer, fresh-04, was already empty in production. Therefore they pass both the original strict new-empty-response condition and the newly reported useful-answer condition on this fresh sample. There is no need to replace the original gate to describe that result. They also improve frozen recall/MRR, remove the two false-positive queries and satisfy the fixed 500 ms runtime ceiling in this run. This is evidence for a follow-up plan, not permission to integrate or a claim that the earlier wave's failed qualification is retroactively passing.

Agent5 loses no judged-relevant production hit and answers all twelve positives, including fresh-04. It cannot pass a serving-latency/cost adoption gate because those measurements are unavailable. Its recall below 1.0 reflects missing supplemental expected records, not failure to find at least one useful answer.

## Supplemental precision judgments (do not merge into primary labels)

Summary5's five unlabelled accepted records were read against the exact question and frozen full record:

| Case and memory | Supplemental judgment |
| --- | --- |
| fresh-05 / 1u8m9 | Adjacent context, not a direct answer: it explains requirement-byte receipt invalidation, not how to test evaluator-version convergence. Useful background at most; strict direct-support admission should reject it. |
| fresh-06 / 1tax0 | Does not answer the requested launch argument. Gardener stdout parsing can affect refresh triggers, but it supplies no remedy for a docs-only indexer launch. Reject under the exact-question rule. |
| fresh-07 / 1uamr | Adjacent test advice, not permission/parity guidance. It suggests fresh-process probes for registration changes but does not explain roster membership or subtraction. Reject as an answer to this question. |
| fresh-08 / 1xk4o | Related parent-owned recovery constraints, but no explanation of where new package logic can execute under the old parent. Reject under direct-support admission. |
| fresh-08 / 1umf9 | Useful directly applicable supplemental guidance: it explains which bridge/feature code executes on installing versus later upgrades and why archive membership must be verified. It supports the timing/old-code distinction, although it does not itself name the pre-index hook. |

Thus Summary5 removes all eight exact-fact false positives but still admits four weak/adjacent positive-query tails. They are not silently counted as wrong in primary metrics: that would change the frozen labels. This supplemental review supports testing strict evidence admission separately from aggregate recall.

Agent5's additional fresh-01 C5 is 1wvo1, the discriminating-fixture/mutation lesson. It gives directly applicable guidance to make the manipulated guard the sole deciding mechanism and prove its mutant fails. It is a useful supplemental acceptance, though it does not specify actual operation budgets. I independently verified all 14 accepted quotes are exact substrings of the mapped candidate's title/action/summary and that accepted identities match combined rankings. Quote existence proves attribution, not by itself relevance; the rationale and question still require judgment.

I authored the labels and therefore cannot claim a blinded validator role for these supplemental judgments. The original agent validator reports having only query/candidate packets, without labels or prior results. My work is an independent audit of its output, not a second blind validation trial.

## Prior holdout reused as development

Summary-only on all twenty RRF candidates scores Recall@3/10 .875, MRR 1.0, useful answers 16/16, empty answers 0, and false-positive queries 0/8. It recovers the old holdout-04 CLI isolation miss and loses **no judged-relevant hit returned by the original production baseline**. Original production had .75 recall, .84375 MRR, 14/16 useful answers, no empty answers and 2/8 false-positive queries.

Action-only is worse (9/16 useful answers) and loses production hits on holdout-01, 02, 07, 10 and 16. Sentence-max retains production hits but yields 15/16 useful answers and one false-positive query. These are development comparisons, not independent confirmation; action-only must not be confused with the earlier title-action-summary qualified implementation. Summary-only still does not retrieve every supplemental labelled item: mean recall .875 differs from useful-answer success 1.0 by design.

## Conclusion

The fresh evidence supports Summary5 as the efficient runtime candidate for a separate gated implementation, with unresolved weak positive-query tails and a broad-paraphrase miss. Agent evidence validation has stronger observed precision and useful-answer coverage but lacks a reproducible serving model, latency/cost qualification and broad independent replication. Keep both the original empty-response metric and the useful-answer metric visible; do not substitute one silently. Production remains unchanged.
