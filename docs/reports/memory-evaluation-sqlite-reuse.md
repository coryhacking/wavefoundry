# SQLite reuse for frozen memory evaluation queries

Owner: Engineering
Status: active
Last verified: 2026-11-26

An exact-input SQLite cache can eliminate comparison query inference on repeat evaluations. Its measured benefit on direct CPU is about 2.5 seconds for the frozen 576-query set. The operator selected default local batching after this experiment. Persistent query caching remains a separate decision.

## Existing index

A read-only exact-text lookup for all 576 frozen v2 queries found zero matches in both the document and code chunk tables. Those tables store document-role representations. The query model uses a query prefix, so a text match alone would not establish vector compatibility.

## Separate cache experiment

Three trials used a temporary SQLite database, the locally installed Arctic S FastEmbed model, the framework's query prefix and groups of eight. Each trial warmed the model before timing. A cold pass started with an empty table, computed the missing vectors and committed once. The warm pass reopened the database and loaded the vectors in the original input order. Times cover the query-vector stage, including lookup, serialization and writes where applicable. The OS file cache remained warm.

| Trial | Batch without cache | Empty cache | Populated cache |
| --- | ---: | ---: | ---: |
| 1 | 2.6031 s | 2.4830 s | 0.0054 s |
| 2 | 2.4605 s | 2.4521 s | 0.0052 s |
| 3 | 2.4442 s | 2.5311 s | 0.0054 s |

An empty cache required 72 model calls. A populated cache required zero. In each trial the full ordered float32 output matched the uncached output byte for byte. Editing one query produced one miss. Changing the simulated runtime namespace produced eight misses on an eight-query probe. The table used 2,723,840 bytes. It held digests and vectors in a temporary database that was removed after the experiment.

## Decision

The earlier Tensorwell benchmark spent about 12.4 seconds of its 403-second batched evaluation on comparison inference and ranking combined. That puts the maximum additional full-run gain from caching these comparison queries alone near 3%. The experiment did not measure Tensorwell with SQLite or a cold disk.

If repeat-run demand warrants a cache, keep it disposable and project-local. Match the effective input, role, model and tokenizer revision, runtime, precision and compatible batching semantics. Batch the misses, preserve case order, and bypass persistent reuse when measuring cold inference or the independent production search arm. A change to corpus documents alone need not invalidate a query vector. This experiment used a fixed runtime namespace and did not qualify production identity discovery, eviction, concurrent writers or mixed-hit ranking parity.
