# Independent summary5 integration preflight audit

Owner: Engineering
Status: active
Last verified: 2026-09-17

Reviewer: memory_holdout (original expected-set author and independent metric recomputation; not the blind per-record judge). Scratch-only evaluation; no source, lifecycle, or frozen label edits.

The result's parameter fingerprint matches the retained parameter file: `438a7c52dad904959659ed0cc7d1a03afdf945f57dc5e44901630e2029d06e92`. Holdout SHA-256 is `32b4e8dab4514d07853a4c7e63b8393cbc640c25757659b48431ee2f73a6c757`. All 24 result questions and expected sets match the frozen manifest. Parameters remain dense20/lexical20/equal RRF60, first5 summary-or-title CPU qualification, finite raw logit >= -4. No retuning.

## Recomputed metrics

| Metric | Production | Summary5 |
|---|---:|---:|
| Macro Recall@3 / Recall@10 (16 answerable) | 0.65625 / 0.65625 | 0.84375 / 0.84375 |
| MRR | 0.71875 | 0.8333333333 |
| Queries with expected relevant hit | 12/16 | 15/16 |
| Empty answerable queries | 3/16 | 1/16 |
| No-match queries returning records | 0/8 | 0/8 |
| Warm p95, 100 calls | 693.818 ms | 199.974 ms |

The candidate recovers integration-11, integration-15 and integration-16; no query with a production expected-set hit loses all useful hits. The speed improvement is roughly 71.2% at warm p95. This is one macOS ARM64 CPU environment, not Windows/Linux or serving cold-start qualification.

## Original gate and explicitly revised gate

The original strict paired-new-empty gate **fails**: integration-10 returns a production record but an empty candidate list. Aggregate empty count improving does not satisfy that original paired rule. The expected installer-defaults record receives -4.178222179412842 and is rejected by the frozen -4 threshold. Do not adjust it after seeing this case.

The production record on integration-10 concerns generated documentation metadata and fixture fidelity. The independent blind reviewer classifies it as adjacent_context, not direct_support for where configuration defaults are guaranteed. Thus this new empty does not remove a useful answer, though it removes potentially adjacent context.

The coordinator reports explicit operator approval, after these results, of the increased useful-answer tradeoff and a revised veto on **paired loss of a useful answer**, retaining new-empty as a reported metric. Under that revised component the observed candidate passes: zero paired losses. This is a disclosed post-result operator policy change, not success against the originally frozen gate. No threshold, questions, labels or ranking parameters changed.

Integration-13 loses one expected record (`1x40o-mem a-two-clause-acceptance-criterion-can-read-as-met-on-one-cla`) and gains another (`1wmag-mem symmetric-property-acs-need-per-side-execution-coverage-clai`). Both returned alternatives directly support the question. Each implementation retrieves one of the two expected records, so per-query recall is unchanged and useful-answer coverage is retained. Do not describe this as zero record-level hit loss.

## Blind per-record precision audit

Using precision-map.json to decode all precision-verdicts.json judgments, I independently counted every returned record from both variants, including negative queries. There are no unjudged returned records.

| Classification | Production | Summary5 |
|---|---:|---:|
| Direct support | 11 | 15 |
| Adjacent context | 5 | 6 |
| Irrelevant/unsupported | 0 | 0 |
| Total returned | 16 | 21 |
| Direct-support precision | 11/16 = 68.75% | 15/21 = 71.43% |
| Queries with blind-judged direct support | 11 | 15 |

The paired production precision floor passes by about 2.68 percentage points. Expected-set useful counts (12 vs15) and blind direct-support query counts (11 vs15) are distinct measurements, not interchangeable denominators. Adjacent records count against direct-support precision. Six candidate adjacent tails remain; passing the model threshold must not be described as verified direct support or authoritative guidance.

Verdicts SHA-256: `33fce96d1e3f2647b7dc7ba1c21ac75b5065b817d330131557ff4e9e41dde519`. Mapping SHA-256: `8541aa287c6ef22184e682957c060757dd0c06136cc595a6cf8799c4dc748218`. I authored the questions and therefore am not a second blind judge; this audit checks the separate judge's coverage and arithmetic.

## Verdict

Preflight supports proceeding under the explicitly amended useful-answer gate: recall/MRR, direct-support precision floor, no-match, useful-answer nonregression and warm latency pass this bounded sample. Preserve the original gate failure in the evidence. This is not implementation delivery approval: production integration, provider/model parity, fallback/error controls, policy/status/history filtering, public diagnostics, tests and final artifact fingerprints still need verification against the actual implementation. Agent review is offline evaluation, not a runtime dependency or serving-latency claim.
