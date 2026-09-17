# Memory relevance-admission follow-up

Owner: Engineering
Status: active
Last verified: 2026-09-16

## Outcome

Historical candidate-selection experiment, superseded by [final production qualification](summary5-production-qualification.md).

A promising local improvement exists: RRF followed by summary-only qualification of its top five records. On a fresh independently authored holdout it returned a judged useful memory for 11/12 answerable queries, rejected all eight no-match queries, and measured 196.2 ms warm p95. Production scored 8/12, two false-positive queries, and 674.6 ms. No production behavior was changed; this is follow-up evidence, not a replacement for the wave's frozen non-adoption result or permission to ship a retuned ranker.

## Protocol

The former 24-query holdout became development data. At the existing raw logit cutoff of -4, action-only qualification achieved Recall 0.46875, summary-only 0.875, and maximum sentence score 0.8125. Action-only produced five empty answerable responses. Summary-only produced none and rejected all eight negatives; sentence splitting admitted one negative and cost about 1,045 ms median qualification time. Summary-only was selected before opening the new holdout.

Independent QA authored 12 answerable and eight no-match questions without running retrieval. The new labels were frozen at SHA-256 `2c9a686a2f55d6989e1672bf4c8b49eb7e070a0ec56d9cff363bd58c19ecbd4e`. Before reading/scoring them, the coordinator froze parameters at `7ae519b699fe3c422ea3c0ec375d3f5667ff5ccb4ca129baa2ae9392c5548d2a`: unchanged candidate sources and RRF, unchanged -4 cutoff, summary-only checks over top five and top twenty, plus blind host-agent support validation over top five. No threshold or text-representation retuning followed fresh outcomes.

All runtime variants use the same eligible frozen memory corpus and a WAL-consistent disposable index snapshot. Source hashes were checked before and after. No authoritative index or memory writes were made by the experiment. Runtime uses existing local CPU embedding/reranking models; metadata is in qualification-models.json. The timings below each contain 100 warm full-path calls. The scratch runner's `cold` field is only an initial call after shared candidate/model warmup, NOT a cold-start measurement; no cold claim is made. Variants ran sequentially rather than randomized, on one macOS ARM64 host.

## Fresh paired results

| Variant | Recall@3 | Recall@10 | MRR | Useful answer /12 | Empty answerable | Nonempty no-match /8 | Warm p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Production | 0.6250 | 0.6250 | 0.5694 | 8 | 3 | 2 | 674.6 |
| RRF, no admission check | 0.9167 | 1.0000 | 0.9583 | 12 | 0 | 8 | 112.8 |
| RRF + summary, top 20 | 0.8333 | 0.8750 | 0.8750 | 11 | 1 | 0 | 470.2 |
| RRF + summary, top 5 | 0.8333 | 0.8750 | 0.8750 | 11 | 1 | 0 | 196.2 |
| RRF + host-agent evidence, top 5 | 0.9167 | 0.9167 | 1.0000 | 12 | 0 | 0 | not measured |

Useful answer means at least one independently labelled relevant memory; it does not mean the system generated and verified a final natural-language answer. Recall accounts for all labelled relevant records; the agent missed secondary relevant records even though it found useful support for every answerable query. Unlabelled positive-query returns remain unjudged in primary metrics, not automatically false: production returned five such identities, RRF 225, summary20 fourteen, summary5 five, and agent5 one.

Both summary variants missed fresh-04 (shared review-authority decisions). Production was also empty on that exact case. Aggregate empty responses improve from three to one, with no newly empty response and no production-correct query or labelled hit lost. Both the original strict new-empty condition and the useful-answer comparison pass on this fresh sample; no policy change is needed to describe this result. The earlier development-case distinction between an irrelevant nonempty answer and an empty answer remains important but does not apply to fresh-04.

## Why the earlier gate failed

Ungated RRF always ranks the available nearest neighbours; its rank scores contain no absolute evidence that a question is answerable. Per-query min-max score fusion has the same limitation. Topic overlap can produce strong relative ordering without the requested fact.

The cross-encoder is sensitive to its input representation. For the prior CLI-test isolation failure, title + action + summary scored the correct memory -8.69; action-only scored -10.44; summary-only scored -1.47 and passed the unchanged -4 threshold. The summary contains the concrete nested-directory failure and isolation remedy. This demonstrates representation sensitivity, not proof of truncation or a universal calibration fix. The fresh authority question still scored relevant memories -5.99 and -9.86 and failed the summary gate.

## Supplemental precision review

Independent QA audited the five initially unjudged summary5 returns: one is useful supplemental guidance, while four provide adjacent context without answering the exact question (fresh-05, 06, 07, 08). The agent validator’s one additional unlabelled acceptance is useful mutation-test guidance. These judgments remain separate from primary frozen labels and metrics. Thus zero no-match false-positive queries does not imply every returned record is relevant. The detailed audit is [relevance-followup-qa.md](relevance-followup-qa.md). QA also verified all fourteen agent quotes and identity mappings.

## Agent-side evidence experiment and cost

A separate agent received only opaque candidate IDs, queries, titles, actions and summaries. It was denied labels and ranking scores, and required to return an exact evidence quote supporting the requested fact or directly applicable guidance; topical similarity and missing requested values were rejected. All fourteen accepted quotes were mechanically verified against supplied text, and order was preserved. This tests a host-agent workflow, not an additional shipped model or local service.

The batch ran from 2026-09-17T05:50:16Z to 05:52:54.877Z: 158.877 seconds for twenty queries/one hundred candidates. Model identity and metered monetary/token cost are unavailable. The pretty-printed input packet was 118,837 bytes and output 7,164 bytes (rough estimates 29,709 and 1,791 tokens, not billed usage). Compact per-query content averaged about 5.6 KB. Batch wall time cannot establish per-query p95, concurrency performance, or production latency. Host reasoning cost and any existing agent context must be included before adopting this route.

## Recommendation and limits

Advance top-five summary qualification as the next production-integration candidate. It passes the measured original recall, MRR, false-positive, new-empty and latency comparisons on this fresh sample; the original failed experiment remains unchanged. Agent-side evidence validation is promising for questions that need stronger support reasoning, but requires a separate host workflow and real serving/cost measurements. Do not simply return an unchecked candidate when the local gate rejects it, and do not call an uncertain result a passed no-match case.

These are small, local, now-observed datasets. Fresh negatives request absent exact facts; this does not establish rejection quality on every ambiguous conceptual query. Test broader near-topic negatives, query distributions from other repositories, per-record precision and availability/fallback contracts before shipping. Both candidate budgets and raw thresholds remain corpus/model-dependent. Native Windows/Linux execution was not performed.

## Reproduction evidence

The superseded follow-up raw bundle was retired on 2026-09-17. `relevance-followup-metrics.json`, this report and its independent QA report retain the outcome, limitations and candidate-selection rationale. The imported `wf_relevance_probe.py` helper was preserved byte-for-byte in `qualification-inputs.json.gz` because the final benchmark scripts depend on it. Final independent labels, blind judgments and production outputs remain in the summary5 bundles; see [retention and reproduction](README.md). Earlier agent-packet/quote audits are historical observations, not a retained raw replay dataset.
