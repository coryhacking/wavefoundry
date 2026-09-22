# Retrieval Evidence — 1ymzq

Owner: Engineering
Status: active
Last verified: 2026-09-22

R1 passes the signed cross-generation comparison against staged baseline R0: 27 fixture/tool keys compared, zero comparison or fixture violations, no invalidation or operator-review reasons. This covers containment adoption, CE, thin wrappers and upgrade before index extraction. It does not prove a no-regression comparison across the subsequent index-handler evaluator membership change; R2 must be a NEW baseline.

| Receipt | Run ID | Generation | UTC start → finish | Verdict |
| --- | --- | --- | --- | --- |
| R0 | `9660e98184a322494510fd6d22254e28228679d523fe8baede8f1f30beec2d6c` | 1892 → 1892 | 2026-09-22T03:17:21Z → 2026-09-22T03:23:06Z | baseline |
| R1 | `b6b02e53c74327452ca7598c1b7ae08a33a3e794c57e3a9c4a863b8c83e72eed` | 1899 → 1899 | 2026-09-22T03:59:25Z → 2026-09-22T04:04:50Z | pass |

Both reports use evaluator source SHA256 `2db63339b76ad3d655bb3c311eb039a2429ca7880940f7dfd442ad4c8a49fd03`, fixture digest `b4b00b893e2e72e6a60062851592fba3a4d52ff0f2e0003aa0064ef4a29b0d57`, 35 declared fixtures, offline execution and CPUExecutionProvider reranking with cross-encoder/ms-marco-MiniLM-L-6-v2. CPU query reranking is not a CPU embedding rebuild. Index refreshes remained incremental.

R0 production digest: `1d7be1ff468329a2028a10a9230e66a1a006b33fd0a5f361eb6bf78c7688773a`. R1 production digest: `4675d31bf583dd87fd10c821b40f54097799e1deb849476d39b89091e1d08376`. R1 binds the baseline file SHA256 `78f48fb12f8a9e42d409b4e8e59a8c5e26e1c12d1f7a3e4eb2964d224615441e`. Each report begins and ends on the same complete generation/attempt token: R0 `66c73ce6eefb4b6c8a2f3de33aec3936`, R1 `473a8756f6a64e309f543f1cbc6c2aca`. Actual result metrics and latency remain authoritative in the raw receipts.

## Preserved unsuccessful attempts

- `docs/reports/retrieval-quality-1ymzq-mid.json`: invalid preflight, `stale_index`; no measured comparison.
- A subsequent measured invocation reused that existing destination and was refused at publication. Its exact stdout failure envelope is retained in `r1-report-destination-collision.json`, extracted from `/private/tmp/1ymzq-r1.log`; `report_destination_exists` means no usable persisted comparison was produced. The earlier invalid receipt was correctly not overwritten. Do not count this attempt as a passing receipt.
- `docs/reports/retrieval-quality-1ymzq-mid-r1.json`: invalid preflight, `stale_index`; coordinator traced the source drift to deferred CE projection of wave.md. The receipt itself proves staleness, not its cause.
- Coordinator explicitly flushed pending CE and incrementally refreshed docs before using the fresh destination `docs/reports/retrieval-quality-1ymzq-mid-comparison.json`. That persisted receipt is the successful R1.

No failed receipt was removed or overwritten. The completed R2 below finalizes the baseline pointers and lint pins; it is not a comparison across evaluator identities.

## R2 final baseline

`docs/reports/retrieval-quality-1ymzq-after.json` records verdict `baseline`, run ID `f9e00315a3cbb68ff01ce6bb06bc1af300e249d2dbc01b0c5be3932ec3e8a45e`, UTC 2026-09-22T14:50:27Z → 14:56:12Z (345.422 seconds). Generation 1914 and attempt `3adce80c426f406bbb846336967687c3` remained complete and unchanged. All 35 fixtures ran; no invalidation or operator-review reasons. Degraded-mode probe passed.

Evaluator SHA256 `25bb941502b84a29c9e8899640dfa2e31e1776218e2554ac881491c1f8d16832`; fixture digest `e5567e76515684fd7908b737923c83d62091ee3ecaf5253ae3fe17e8674275de`; production digest `cb382d900be670500cfa824c78b6505f7c50fccb68c1f5c966b86626f2ee18d6`, verified at run end. The index-handler symbol anchor resolved to its new module. Evaluator membership and two moved fixture anchors changed after R1, so this is deliberately a NEW baseline, not a signed no-regression comparison to R0, R1 or older references. Raw metrics remain authoritative.

Preflight found zero excluded framework-test paths in both docs/code tables. Pending CE was flushed, then the index was refreshed incrementally. A temporary canonical pending-marker heartbeat deferred automatic refresh during measurement; no repository content was changed during the run. The isolated CoreML probe exited -11 and selected CPUExecutionProvider query reranking, without rebuilding embeddings. Reproduction: after a completed fresh index and a quiet write window, run `python3 -B .wavefoundry/framework/scripts/retrieval_eval.py --root . --fixtures docs/evals/retrieval-quality-golden.json --out docs/reports/retrieval-quality-<unique-id>.json` with no baseline argument; never overwrite retained receipts.
