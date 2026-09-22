# Retrieval evaluation evidence retention

Owner: Engineering
Status: active
Last verified: 2026-09-22

## Retained evidence

The operator approved consolidating historical retrieval and semantic-search output after the 1.25.0 release. Retain five raw receipts: the three protected historical inputs and the documented reference comparison pair. These are historical measurements, not a fresh qualification of today's tree.

| Receipt | Reason retained |
| --- | --- |
| [baseline-run1](retrieval-quality-baseline-run1.json) | Historical input protected by the evaluator. |
| [baseline](retrieval-quality-baseline.json) | Historical input protected by the evaluator; old evaluator identity is incomparable with later runs. |
| [post-1seas-vs-before](retrieval-quality-post-1seas-vs-before.json) | Protected historical comparison. |
| [post-1wuju](retrieval-quality-post-1wuju.json) | Before-receipt consumed by the reference comparison. |
| [post-1wybs](retrieval-quality-post-1wybs.json) | Documented reference receipt, subject to evaluator compatibility. Its fail verdict is preserved. |

Keep the query fixture at `docs/evals/retrieval-quality-golden.json`, evaluator code, tests and closed-wave review records. The [evaluation policy](../contributing/review-and-evals.md) still governs baseline compatibility and when to measure again.

## Conclusions worth keeping

- Invalid attempts measured no usable comparison: their reasons were an incomplete build epoch, stale index, changed evaluator identity or mismatched fixture schema. Freeze the corpus and verify identities before interpreting a result.
- Repeated and superseded runs are development history, not independent replications. A pass from a superseded experiment does not establish current quality. The archived verdicts below remain visible rather than retaining only passing outcomes.
- The final `1wpih` same-generation comparison recorded no comparison violations but required operator review for absolute latency and a contended baseline pair. Its later repaired report returned pass. Timing contention and quality regression must be adjudicated separately.
- The retained `1wybs` comparison returned fail on five zero-tolerance code_ask holdout regressions (largest 0.055 nDCG@10). Its wave attributed the difference to corpus drift after proving the production diff reached no retrieval tool. That historical disposition is not a blanket exemption for future failures.
- The [quick semantic probe](semantic-search-quick-evaluation-2026-09-17.md) showed that reducing reranking to the first five or ten candidates loses useful candidates; a normalized leading score of 1.0 does not establish answer support.
- The [quality-first evaluation](semantic-search-quality-evaluation-2026-09-17.md) improved targeted living-guide hits from 2/6 to 5/6 but left code mechanism coverage at 4/6. These unblinded development probes did not establish better answer success or justify changing production ranking. The contaminated first pass was rejected.
- The [operational-guidance follow-up](operational-guidance-retrieval-followup-2026-09-17.md) supports an agent-directed second lookup when facts are missing, while retaining broad/history retrieval. Existing exact prompt lookup recovered the missing closure rule; no search-engine implementation was justified. Its Markdown report retains the fact-coverage judgments and counterexamples; the raw capture is archived below.

## Lessons from retired downstream test plans

The 1.6.1 and 1.7.1 package-specific plans are obsolete, not current runbooks. Their useful lessons remain:

- Keep evaluation queries and reports outside the measured retrieval corpus; otherwise a report can answer its own test queries and inflate confidence. The 1.7.1 field report recorded that contamination explicitly.
- Verify the actual inference provider and fallback diagnostics, and separate cold-start from warm timings. A successful tool response alone does not prove the intended accelerated path ran.
- The 1.6.1 CUDA investigation rejected a library-name symlink as an ABI repair: matching names did not supply the required symbols. This is historical evidence, not advice about today's dependency versions.
- Exercise security-gate outcomes with synthetic findings in an isolated fixture and a dry run, never real credentials. Check unknown-state handling and reminders as well as success.
- Test useful-answer retention, citation fidelity and explicit enumeration limits alongside negative queries. Repeated graph builds on unchanged input should be compared for determinism.

## Archived raw outputs

Removed 50 tracked reports and raw outputs (17.97 MiB) from the working tree. Historical wave events and the checkpoint ledger remain unchanged: their report names identify artifacts as they existed at review time. They are not promises that every intermediate output remains in the current checkout. The summaries above preserve decisions, caveats and failure outcomes; the raw evidence is recoverable from Git.

Last complete snapshot: `5e5a6a898fe79d67d9af9c9727e1e82d0f9366a7` (official 1.25.0 release). To inspect any archived report without altering the checkout:

```bash
git show 5e5a6a898fe79d67d9af9c9727e1e82d0f9366a7:docs/reports/<filename>
```

For a compressed JSON bundle, redirect that output to a scratch `.json.gz` file before decompression. No Git history was rewritten. Baselines required for current documented comparisons were not removed.

| Archived filename | Recorded verdict |
| --- | --- |
| `retrieval-quality-baseline-1wpih-a-attempt1-invalid.json` | invalid |
| `retrieval-quality-baseline-1wpih-a-attempt2-invalid.json` | invalid |
| `retrieval-quality-baseline-1wpih-a.json` | baseline |
| `retrieval-quality-baseline-1wpih-a2-attempt1-invalid.json` | invalid |
| `retrieval-quality-baseline-1wpih-a2-attempt2-invalid.json` | invalid |
| `retrieval-quality-baseline-1wpih-a2.json` | baseline |
| `retrieval-quality-baseline-1wpih-b.json` | baseline |
| `retrieval-quality-baseline-1wpih-b2-attempt1-invalid.json` | invalid |
| `retrieval-quality-baseline-1wpih-b2.json` | baseline |
| `retrieval-quality-baseline-pre-review-run1.json` | operator_review_required |
| `retrieval-quality-baseline-pre-review.json` | operator_review_required |
| `retrieval-quality-before-1seas-run1.json` | fail |
| `retrieval-quality-before-1seas.json` | fail |
| `retrieval-quality-post-1seas-attempt1-fail.json` | fail |
| `retrieval-quality-post-1seas-pre-review.json` | pass |
| `retrieval-quality-post-1wpid-lexical-attempt1-invalid.json` | invalid |
| `retrieval-quality-post-1wpid-lexical-attempt2-invalid.json` | invalid |
| `retrieval-quality-post-1wpid-lexical-attempt3-invalid.json` | invalid |
| `retrieval-quality-post-1wpid-lexical.json` | operator_review_required |
| `retrieval-quality-post-1wpif-run1.json` | baseline |
| `retrieval-quality-post-1wpif-vs-1sear-computed.json` | fail |
| `retrieval-quality-post-1wpif.json` | pass |
| `retrieval-quality-post-1wpig-final.json` | operator_review_required |
| `retrieval-quality-post-1wpig-run2.json` | operator_review_required |
| `retrieval-quality-post-1wpih-final-attempt1-invalid.json` | invalid |
| `retrieval-quality-post-1wpih-final-attempt2-invalid.json` | invalid |
| `retrieval-quality-post-1wpih-final-attempt3-invalid.json` | invalid |
| `retrieval-quality-post-1wpih-final-attempt4-invalid.json` | invalid |
| `retrieval-quality-post-1wpih-final-attempt5-invalid.json` | invalid |
| `retrieval-quality-post-1wpih-final.json` | operator_review_required |
| `retrieval-quality-post-1wpih-repaired-attempt1-invalid.json` | invalid |
| `retrieval-quality-post-1wpih-repaired.json` | pass |
| `retrieval-quality-post-1wpih-replay1.json` | operator_review_required |
| `retrieval-quality-post-1wsc8-refine2.json` | baseline |
| `retrieval-quality-post-1wur7-run1.json` | baseline |
| `retrieval-quality-post-1wur7.json` | operator_review_required |
| `retrieval-quality-review-repair-attempt1-fail.json` | fail |
| `retrieval-quality-review-repair-attempt2-fail.json` | fail |
| `retrieval-quality-review-repair-attempt3-fail.json` | fail |
| `retrieval-quality-review-repair-attempt4-fail.json` | fail |
| `retrieval-quality-superseded-injector-baseline-run1.json` | baseline |
| `retrieval-quality-superseded-injector-baseline.json` | pass |
| `retrieval-quality-superseded-injector-before-1seas-run1.json` | fail |
| `retrieval-quality-superseded-injector-before-1seas.json` | fail |
| `retrieval-quality-superseded-injector-post-1seas-vs-before.json` | pass |
| `semantic-search-quality-evaluation-2026-09-17.json.gz` | exploratory |
| `semantic-search-quick-evaluation-2026-09-17.json` | exploratory |
| `operational-guidance-retrieval-followup-2026-09-17.json` | exploratory |
| `1p5px-validation-test-plan.md` | obsolete package-specific test plan |
| `downstream-test-1.7.1.md` | obsolete package-specific test plan |

## Wave 1ymzq evidence

Retain `retrieval-quality-1ymzq-before.json` (R0 baseline) and `retrieval-quality-1ymzq-mid-comparison.json` (R1 passing signed comparison), together with invalid `retrieval-quality-1ymzq-mid.json` and `retrieval-quality-1ymzq-mid-r1.json` (`stale_index` preflight refusals). The measured invocation rejected because its report destination already existed is retained as the exact failure envelope at `docs/waves/1ymzq handler-module-split-three/r1-report-destination-collision.json`. These failed attempts are not successful comparisons. Exact run identities, dates and caveats are in the wave's `retrieval-evidence.md`. Retain `retrieval-quality-1ymzq-after.json`: R2 completed as a new baseline on stable generation 1914 after evaluator membership and the two moved anchors changed. It is not a comparison to R0/R1.
