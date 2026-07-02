# Index Compression and FTS Benchmark

Owner: Engineering
Status: draft
Last verified: 2026-07-02

## Purpose

Record the local benchmark results for LanceDB vector compression and FTS storage settings so the follow-up implementation wave has a stable evidence trail.

The benchmark compared docs and code semantic index tables using the current Wavefoundry corpus. The vector baseline was `IVF_FLAT`; compressed candidates were compared against that baseline before and after applying the local cross-encoder reranker.

## Corpus

| Layer | Rows |
|-------|------|
| Docs | 17,261 to 17,407 depending on run snapshot |
| Code | 12,057 |
| Vector dimension | 384 |

The benchmark used isolated temp copies under `/private/tmp/` rather than modifying `.wavefoundry/index/`.

## Vector Compression Size

| Layer | Index | Size | Savings vs `IVF_FLAT` |
|-------|-------|------|------------------------|
| Docs | `IVF_FLAT` | 73.26 MB | baseline |
| Docs | `IVF_HNSW_SQ` | 56.40 MB | 16.86 MB / 23.0% |
| Docs | `IVF_HNSW_PQ` | 51.72 MB | 21.54 MB / 29.4% |
| Docs | `IVF_RQ` | 49.00 MB | 24.26 MB / 33.1% |
| Code | `IVF_FLAT` | 49.77 MB | baseline |
| Code | `IVF_HNSW_SQ` | 38.06 MB | 11.71 MB / 23.5% |
| Code | `IVF_HNSW_PQ` | 34.65 MB | 15.12 MB / 30.4% |
| Code | `IVF_RQ` | 32.70 MB | 17.07 MB / 34.3% |

Combined table size:

| Index | Combined Size | Savings vs `IVF_FLAT` |
|-------|---------------|------------------------|
| `IVF_FLAT` | 123.03 MB | baseline |
| `IVF_HNSW_SQ` | 94.46 MB | 28.57 MB / 23.2% |
| `IVF_HNSW_PQ` | 86.37 MB | 36.66 MB / 29.8% |
| `IVF_RQ` | 81.70 MB | 41.33 MB / 33.6% |

## Vector-Only Rank Movement

Metrics compare compressed vector search top-20 against `IVF_FLAT` top-20 before reranking.

| Layer | Index | Top 1 Changed | Top 1 Outside Top 3 | Top 3 Not All In Top 5 | Top 5 Not All In Top 10 | Top 20 Overlap |
|-------|-------|---------------|----------------------|--------------------------|---------------------------|----------------|
| Docs | `IVF_HNSW_SQ` | 1.00% | 1.00% | 5.00% | 5.67% | 95.88% |
| Docs | `IVF_HNSW_PQ` | 3.00% | 1.33% | 28.33% | 37.67% | 72.88% |
| Docs | `IVF_RQ` | 1.00% | 0.00% | 13.67% | 14.67% | 82.57% |
| Code | `IVF_HNSW_SQ` | 2.33% | 2.33% | 6.67% | 11.33% | 91.63% |
| Code | `IVF_HNSW_PQ` | 4.00% | 4.00% | 24.67% | 35.33% | 69.42% |
| Code | `IVF_RQ` | 0.00% | 0.00% | 9.00% | 12.67% | 79.53% |

## Post-Rerank Rank Movement

The rerank pass used the production `StaticShapeReranker` on the supported CPU fallback path with `WAVEFOUNDRY_EMBED_PROVIDER=cpu`. For each sampled query, the benchmark searched all index variants, scored the union of returned candidates once with the reranker, then sorted each index's returned top-20 by those shared reranker scores before comparison.

Metrics compare compressed post-rerank top-20 against post-rerank `IVF_FLAT` top-20.

| Layer | Index | Top 1 Changed | Top 1 Outside Top 3 | Top 3 Not All In Top 5 | Top 5 Not All In Top 10 | Top 20 Overlap |
|-------|-------|---------------|----------------------|--------------------------|---------------------------|----------------|
| Docs | `IVF_HNSW_SQ` | 0.67% | 0.67% | 2.33% | 4.67% | 96.28% |
| Docs | `IVF_HNSW_PQ` | 3.00% | 2.33% | 22.67% | 37.33% | 73.32% |
| Docs | `IVF_RQ` | 0.67% | 0.67% | 15.33% | 29.00% | 81.90% |
| Code | `IVF_HNSW_SQ` | 4.67% | 4.00% | 9.00% | 13.33% | 92.68% |
| Code | `IVF_HNSW_PQ` | 9.00% | 8.00% | 28.67% | 48.33% | 71.43% |
| Code | `IVF_RQ` | 0.67% | 0.33% | 12.00% | 31.00% | 81.41% |

## Vector Compression Conclusion

Use `IVF_HNSW_SQ` as the preferred compression candidate if Wavefoundry changes the default vector index.

Rationale:

- `IVF_HNSW_SQ` gives meaningful size savings, about 23% for both docs and code.
- It preserves the candidate set much better than `IVF_HNSW_PQ` and `IVF_RQ`.
- Reranking improves the top of the docs result set for SQ and keeps it close to flat.
- PQ and RQ save more disk, but they lose too many candidates before reranking can recover them. Reranking can reorder returned candidates; it cannot rescue candidates that failed to enter the vector top-20.

Keep `IVF_FLAT` as the benchmark baseline. `IVF_FLAT` is the no-compression reference; SQ should be evaluated as a candidate, not as the baseline.

## FTS Parameter Results

Current FTS settings:

```text
base_tokenizer="simple"
stem=False
remove_stop_words=False
lower_case=True
max_token_length=80
with_position=True
```

The largest FTS size lever was `with_position`.

| Layer | Current FTS | `with_position=False` | Savings |
|-------|-------------|------------------------|---------|
| Docs | 12.71 MB | 3.99 MB | 8.72 MB / 68.6% |
| Code | 8.00 MB | 2.25 MB | 5.75 MB / 71.9% |

Quality caveat: the current `_fts_query` path wraps identifier-like searches in quoted phrases. LanceDB no-position FTS cannot satisfy those phrase queries, so 100/140 benchmark queries errored when the existing query shape was used unchanged. When the same no-position index was queried without phrase quoting, overlap was effectively preserved:

| Layer | Unquoted no-position overlap |
|-------|-------------------------------|
| Docs | 100.00% |
| Code | 98.43% |

Other parameter changes did not produce a better immediate tradeoff than removing positions. There was not enough evidence to change stemming, stop-word removal, tokenizer, or `max_token_length` as part of the same move.

## FTS Conclusion

Yes, we reached a conclusion on FTS: `with_position=False` is the best storage optimization candidate, but it must ship with a query-shape fix.

Recommended implementation direction:

- Change FTS index creation to `with_position=False`.
- Stop issuing phrase queries against no-position FTS, or add a deterministic retry/fallback from quoted phrase search to unquoted token search.
- Keep the current tokenizer, lower-casing, stop-word, stemming, and token-length settings until a separate quality benchmark justifies changing them.
- Add regression tests that cover identifier-like queries, natural-language queries, and code symbol queries on no-position FTS.

Do not change FTS positions alone. That would mask a production bug by making existing phrase-shaped queries fail or silently degrade.

## Open Follow-Up

The CoreML reranker path crashed locally with native exit code 139 during this benchmark attempt. The CPU reranker fallback worked when forced through the supported production knob, `WAVEFOUNDRY_EMBED_PROVIDER=cpu`.

This should be investigated as a production issue. The benchmark report should not be used to justify masking the CoreML crash.
