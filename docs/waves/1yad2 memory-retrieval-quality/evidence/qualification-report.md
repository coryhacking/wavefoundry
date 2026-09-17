# Memory retrieval qualification and selection

Owner: Engineering
Status: active
Last verified: 2026-09-16

## Decision

Historical result, superseded by [final production qualification](summary5-production-qualification.md). The following non-adoption decision belongs to the original experiment, not the delivered implementation. See [evidence retention](README.md) for the current artifact inventory.

**Do not adopt a replacement ranking in this wave.** Keep production memory search, briefing and read-tool advisories unchanged. Deliver explicit diagnostic-versus-qualification reporting, reusable bounded evaluation helpers, and retained independent evidence. No schema, model, native dependency, global code/docs ranking or automatic memory curation changed.

The frozen 24-query holdout has 16 answerable questions and eight no-match questions. An independent QA reviewer authored its labels before scoring, without tuning the ranker. The full frozen corpus contains 218 bodies and 13 compact archive entries; default eligibility is 119 surfaced bodies plus 13 compact entries. History/status controls are separate. The eligibility filters and memory identities are the same for both finalists. Production is the exact public response path, whose existing docs-first candidate generation differs intentionally; the same-source policy-order ablation separates this coverage difference from fusion ordering.

## Paired outcomes

| Design | Recall@3 | Recall@10 | MRR | Empty answerable /16 | Nonempty no-match /8 | Warm p95 ms | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Current production | 0.75000 | 0.75000 | 0.84375 | 0 | 2 | 690.8 | control |
| Plain RRF | 1.00000 | 1.00000 | 1.00000 | 0 | 8 | 137.1 | false positives increase |
| 75/25 score fusion | 0.90625 | 1.00000 | 0.91875 | 0 | 8 | 136.2 | false positives increase |
| RRF + per-record qualifier | 0.84375 | 0.84375 | 0.93750 | 1 | 0 | 506.9 | new empty answer; exceeds 500 ms |
| Score fusion + per-record qualifier | 0.84375 | 0.84375 | 0.90625 | 1 | 0 | 478.5 | new empty answer |

The gate counts an empty answerable response separately from a nonempty response that contains no judged-relevant record. Production had two such nonempty misses; ungated finalists had none, and qualified finalists had one empty miss. Better aggregate recall does not excuse that new empty answer under the predeclared gate. Every nonempty no-match response counts as a false positive, even if described as uncertain. No threshold was retuned after scoring.

All experimental candidate unions captured every independently labelled relevant record. Plain RRF retained all within the first three; the qualifier discarded useful candidates. Weighted RRF controls achieved Recall@3 0.96875 at either 0.25 or 0.75 semantic weight; lexical-only 0.96875, semantic-only and lexical injection 0.84375. The same-source policy-order ablation scored only 0.09375 at three: expanding candidates while preserving confidence-first order is insufficient. These are controls, not separately qualified release candidates. Production candidate recall is unavailable because its public response does not expose the pre-filter candidate ledger; no zero or inferred success is substituted.

Detailed per-case outputs were used for this original review and later retired during operator-requested evidence cleanup. The aggregate decision remains; final production per-case outputs and blind judgments are retained separately. Positive unlabelled results remain unjudged, not automatically wrong. These 24 cases are useful local evidence, not a confidence interval or a claim about arbitrary repositories.

## Reproduction and artifacts

Historical runner: first restore the byte-identical corpus/query fixtures from `qualification-inputs.json.gz` in a disposable checkout as described in [audit and reproduction](README.md#audit-and-reproduction), then run with the provisioned Python:

```bash
python3 -B 'docs/waves/1yad2 memory-retrieval-quality/qualification_eval.py' --split holdout --warm-calls 100 --output /tmp/memory-qualification.json
```

Use an appropriate local output path on Windows. The runner verifies frozen source hashes/census, creates a WAL-consistent disposable SQLite backup, refuses incomplete epochs, and excludes this wave's evaluation prose in the copy. It changes neither the authoritative index nor memories. Corpus drift deliberately refuses reproduction until a new evaluation is planned. Repeating this frozen run can verify mechanics; these now-observed queries cannot serve as an untouched holdout for new tuning.

- `qualification-inputs.json.gz`: original frozen corpus and query fixture, preserved byte-for-byte for explicit restoration; `qualification-parameters.json` retains the original gates.
- Earlier complete development/holdout reports and their process logs were retired on 2026-09-17. Aggregate results above and `qualification-decision.json` remain; final production outputs are retained separately.
- `qualification-decision.json`: aggregate gates, controls, cold/warm timing and explicit non-adoption.
- `qualification-models.json`: local hardware/runtime identity and hashes of cached ONNX/tokenizer inputs and the CPU reranker graph; models were not downloaded or changed.
- `qualification-scale.json`, `qualification_scale.py`: synthetic native SQL/BM25 scaling, with 100 calls per size.
- `policy-controls.md`, `implementation-checks.md`, `qa-qualification.md`: independent policy/fault review and regression/mutation evidence.

## Work and latency bounds

Each finalist retrieves at most 20 distinct semantic identities and 20 lexical identities, unions at most 40 and returns at most 20. SQL groups chunk distances by exact parameter-bound path before LIMIT; duplicate chunks cannot consume the record budget. Compact archive entries remain independent lexical identities even though they share a manifest path. A qualified design checks each of at most 20 records using title, action delta and summary, raw logit >= -4; a passing record never admits the unchecked tail. Scores are ranking signals, not probabilities or authority.

Bounded outputs do not imply constant work: SQL scans eligible vector chunks and BM25 scans the eligible record texts. No Python list materializes all vector chunks. The native scale probe covered up to 11,900 records and 29,750 physical chunks, including 100 chunks per memory; SQL p95 ranged 2.2–34.0 ms, BM25 0.7–77.9 ms. It ran alongside the recovery index update, so these are contention-affected component observations, not isolated end-to-end qualification or universal performance guarantees.

Each design had one fresh-WaveIndex cold call and 100 warm CPU calls. Original aggregate distributions remain in `qualification-decision.json`; the superseded per-case stage dump was retired. Cold includes model initialization but does not evict OS caches. Warm holdout timing began after index recovery/scaling finished. Environment: macOS ARM64, 12 logical CPUs, Python 3.13.5, ONNX Runtime 1.27.0, APSW 3.53.4.0, sqlite-vec 0.1.9. Precise chip/RAM identification was sandbox-denied. No native Windows/Linux or Python 3.11 native-model qualification is claimed; eight pure helper tests passed on 3.11. A 500 ms candidate p95 ceiling was fixed before scoring. Production's 690.8 ms is a control measurement, not a new standing budget.

## Recovery and integrity

Infrastructure failure is not a successful empty result. Missing/stale/unavailable semantic data, partial eligible-path coverage, or an unavailable/failing/nonfinite required relevance model produces the existing public lexical fallback plus unavailable experiment status, excluded from timing credit and adoption. The evaluator additionally rejects a code-only index even though the general loader can serve that index. That diagnostic guard was added after the healthy holdout run; the measured snapshot had a docs layer and all 119 requested body paths covered, so the repair changes no measured rankings.

The index initially had an incomplete epoch. A standard all-content update recovered it; an edit during the first recovery made publication refuse, and a second update against stable files completed. No manual epoch reset or data deletion was used. The failed first development launch scored no queries. These infrastructure retries did not tune the frozen designs.
