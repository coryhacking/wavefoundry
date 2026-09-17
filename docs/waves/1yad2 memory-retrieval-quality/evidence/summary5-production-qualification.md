# Summary5 production qualification

Owner: Engineering
Status: active
Last verified: 2026-09-17

## Delivered public path

The repaired production `memory_search_response` was executed through `qualification_eval.baseline` and normal `WaveIndex` behavior. Its observer subclass changes no ranking. Every one of 100 warm calls asserted healthy model relevance and `support_verified=false`. The old public function was extracted unchanged from commit `6a74faed26176b36f4a59d250eb9689a00a437a8`, using unchanged shared helpers and the same current read runtime. Every baseline call asserted no swallowed semantic failure. Both used the same completed WAL-consistent scratch snapshot, the same 24 frozen cases and the same CPU model. The snapshot excludes 291 chunks from this wave's evaluation prose; its SHA-256 is `a493472bf7ea7d53b915e1cc34804a266e0d5ce8340af23c0566b7c4953a9578`. Frozen memory source census and byte hashes were verified before and after both runs.

All 24 delivered candidate lists exactly match the frozen summary5 prototype, and all 24 baseline lists exactly match the prior production lists. Therefore the original independent expected labels and blind query-record judgments apply without new labels, threshold tuning or assumptions about changed output identities.

| Measure | Original public path | Delivered summary5 |
| --- | ---: | ---: |
| Useful queries, original expected sets | 12/16 | 15/16 |
| Queries with blind direct support | 11/16 | 15/16 |
| Recall@3 / Recall@10 | 0.65625 | 0.84375 |
| MRR | 0.71875 | 0.83333 |
| Direct-support precision over all returns | 11/16 (68.75%) | 15/21 (71.43%) |
| Adjacent non-answering records | 5 | 6 |
| Nonempty no-match responses | 0/8 | 0/8 |
| Warm calls | 100 | 100 |
| p50 ms | 596.6 | 179.8 |
| p95 ms | 614.0 | 192.2 |
| p99 ms | 655.0 | 199.8 |
| First-call ms | 1677.2 | 1513.2 |

Warm p95 improves 68.7% and stays below the 500 ms budget. No query with a useful baseline answer loses all useful support. Integration-10 is newly empty instead of returning an adjacent record; integration-13 exchanges one relevant record for another. The operator-approved acceptance revision and original failed strict-new-empty gate remain disclosed in summary5-integration-preflight.md; this is not an unchanged predeclared pass.

## Runtime and limits

Python 3.13.5, macOS ARM64, `CPUExecutionProvider`, `cross-encoder/ms-marco-MiniLM-L-6-v2`, batch size 1. Both variants use the same model/provider and query schedule. This is a single-machine qualification, not native Windows/Linux execution or a universal latency claim. First-call timing includes initialization but does not evict OS caches.

Candidate peak process RSS was 743.4 MiB, versus 140.5 MiB before the first call. This includes embeddings, index/runtime and reranker allocations; it does **not** isolate an additional CPU model on a GPU host. CPU reuse and GPU-cache isolation have separate executable controls. Full eligible SQL/BM25 scanning remains; 20+20 and five are materialization/qualification caps, not total scan limits. The frozen corpus has 119 eligible bodies plus 13 distinct compact archive entries.

Six adjacent returns remain. The calling agent must assess relevance, applicability and direct support just as for semantic, lexical and graph searches. Model screening is not answer verification or instruction authority.

## Reproduction and operational observations

Exact final scripts, results, reviewed hashes, original public function and independent repair probes are bundled in `summary5-production-qualification.json.gz`; prior labels/judgments remain in `summary5-integration-preflight.json.gz`; frozen corpus/query inputs and the imported helper are in `qualification-inputs.json.gz`, with model hashes in `qualification-models.json`. See [retention and reproduction](README.md) before rerunning historical scripts. The initial baseline timing lacked a persisted semantic-error assertion and was repeated with that guard; only the guarded run is reported above.

Initial snapshot attempts refused incomplete epochs. The stale running MCP writer correctly refused publication; standard update in a fresh process recovered the index. A sandbox-restricted CPU rebuild was stopped and retried through the same standard command with native access; foreground and background passes completed before the accepted snapshot. No index epochs, recovery receipts or memory sources were manually changed. No ranking/source edits landed during either final benchmark. Final canonical suite and delivery ledger are recorded separately.
