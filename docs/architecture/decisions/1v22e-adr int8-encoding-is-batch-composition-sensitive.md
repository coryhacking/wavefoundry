# 1v22e-adr — INT8 embeddings are batch-composition sensitive, so the INT8 path encodes one row per call

Owner: Engineering
Status: accepted
Last verified: 2026-08-12

## Context

ADR [1p92d](1p92d-adr%20embedding-precision-policy.md) established the precision policy: FP16 end to
end on GPU machines, INT8 end to end on CPU-bound machines, with the precision class folded into
`model_versions`. It cleared INT8 on gold-labelled recall (0/30 regressions). It did not consider how
INT8 activations are quantized, and that turns out to matter.

The INT8 export quantizes activations with `DynamicQuantizeLinear`. Per the ONNX operator contract
that operator emits a **scalar** scale:

```
y_scale = (maximum(0, max(x)) - minimum(0, min(x))) / (qmax - qmin)
```

The `ReduceMin` / `ReduceMax` carry no axis restriction, so the reduction spans every dimension of
the input tensor, **including the batch dimension**. One scale is derived from the whole batch, and
every row's quantized values therefore depend on the most extreme activation anywhere in that batch.
The shipped `model_int8.onnx` contains 48 such operators. `model_fp16.onnx` contains none.

This is a documented property of per-tensor dynamic quantization, not a defect in the Snowflake
export, in ONNX Runtime, or in Wavefoundry. What was ours was the integration choice: the embedder
submitted 32 rows per call and padded with empty strings only when the group was short.

Three consequences were measured on the shipped graph, all on the CPU-bound / `int8` path only:

| Batch content (target text at row 0) | cos vs the target encoded with only empty padding |
| --- | --- |
| 1 real + 31 empty | 1.00000000 |
| 1 real + 30 real + 1 empty | 0.99630791 |
| 1 real + 16 real + 15 empty | 0.99551839 |
| 1 real + 31 real | 0.99467921 |
| 1 real alone | 0.99694288 |

1. A chunk's stored vector depended on which other chunks shared its batch.
2. Re-indexing was not reproducible: chunk ordering, or any change in chunk count that moved batch
   boundaries, reassigned neighbours and changed vectors. Position *within* a batch was stable, so
   this was batch membership, not nondeterminism.
3. A full 32-chunk batch carries no empty rows while a query is encoded as 1 real row plus 31
   empties, so **queries and the bulk index sat in different quantization regimes** (cos 0.996160
   through the production embedder).

Batch *size* was ruled out: batches of 2, 8 and 32 that all contained empty rows agreed at cos
1.00000000. FP16 and fastembed were both invariant under the identical test, exactly as the mechanism
predicts.

Batching was also not earning anything on the path it compromised. The graph padded every row to 512
tokens, so a 32-row batch performed the same token work as 32 single-row calls: 33.7 ms/chunk batched
versus 32.4 ms/chunk single-row over 64 realistic 512-token chunks.

## Decision

**On the INT8 path, every inference call carries exactly one real row, and the batch dimension is
never padded.** A vector is therefore a function of its own text alone. This is a *correctness*
requirement, not a performance tuning choice.

The CPU path runs the shipped dynamic `model_int8.onnx` directly rather than a locally built
batch-pinned derivative, because a pinned graph cannot accept a single row.

The GPU / `full` path keeps `STATIC_BATCH` batching unchanged: its graph carries no quantization
operators, it was measured composition-invariant, and the GPU genuinely amortizes its fixed dispatch
cost over a full batch.

The one-time re-embed this forces is **scoped to `int8`-class layers** by appending an encoding
revision to the recorded identity fingerprint for that class only.
`EMBEDDING_MODEL_SET_FINGERPRINT` is an all-layer compatibility boundary, so bumping it would have
re-embedded both layers on every GPU host for a defect they never had.

## Consequences

**Positive:**

- INT8 vectors are reproducible: the same text yields the same vector regardless of neighbours,
  ordering, or batch boundaries (verified at cos 1.00000000 across reordered corpora).
- Query and index agree exactly on an INT8 index for the first time (cos 1.00000012, previously
  0.996160). The prior fastembed fallback was further still at cos 0.990245.
- Peak resident memory on the CPU-bound query path drops from 1353 MiB to 245 MiB, because the
  32x512 pin no longer materializes activations for 16,384 token positions to encode one query.
- Throughput is unchanged to marginally better (0.96x), so determinism cost nothing.
- The path now loads a manifest-verified shipped artifact instead of a locally generated derivative
  that was never hash-verified.

**Negative / tradeoffs:**

- CPU-bound repositories re-embed both semantic layers once on the upgrade that lands this. GPU-class
  repositories re-embed nothing.
- Single-row encoding forgoes any future batching benefit on the INT8 path. That is deliberate:
  batching is what breaks the invariant, and it was measured to buy nothing here.
- The retrieval-quality effect of the prior mismatch was never measured. No gold-labelled eval set
  exists in this repository, so the comparison ADR 1p92d ran for the original INT8 decision could not
  be repeated. The correctness argument stands on reproducibility and query/index agreement alone.

**Constraints imposed:**

- **Any future change that batches the INT8 embedder reintroduces this defect.** Treat batch shape on
  a dynamically quantized graph as part of the vector contract, not an implementation detail. This
  generalizes beyond the embedder: it holds for **every** dynamically quantized graph in the system,
  and `StaticShapeReranker` is a confirmed second instance (see **Related**).
- Index-time and query-time encoding must stay identical on the INT8 path. They are the same class,
  so a change to one silently changes the other's agreement.
- The precision-class token and the identity fingerprint are consulted by both compare and write
  sites. They must route through one shared derivation, or an incremental build re-embeds forever.
- The recorded identity fingerprint is class-scoped. Any predicate comparing it to the bare model-set
  constant is wrong for `int8` layers. One such predicate gated retired-model cleanup and had to be
  repaired; check for others before adding new comparisons.

## Alternatives Considered

| Alternative | Reason rejected |
|-------------|----------------|
| Pad every batch to include at least one empty row, hoping pad tokens clamp the activation range | **Falsified by measurement**, not argument. A batch of 1 real + 30 real + 1 empty still drifted to cos 0.99630791. The earlier stable readings held only because those batches contained nothing but the target and empties. |
| Calibrated (static) quantization export | Fixes the cause at its source and preserves batching, but requires producing, validating and redistributing a new INT8 artifact plus a calibration set, and bumping the model set immediately after wave 1v0r0 narrowed that supply-chain surface. Revisit if single-row encoding proves insufficient. |
| Drop INT8 and run FP on CPU | Removes the defect class entirely and would simplify the model set, but roughly doubles CPU embedding cost, discards the INT8 recall parity ADR 1p92d established, and still forces a re-embed. |
| Encode the revision in the precision-class token instead of the fingerprint | Materially larger blast radius: that token is compared against the literal `"int8"` at three sites, including an upgrade validity allowlist. |
| Bump `EMBEDDING_MODEL_SET_FINGERPRINT` to force the re-embed | It is an all-layer boundary, so it would re-embed both layers on every GPU host for a defect confined to CPU-bound ones. |
| Document the behaviour and accept it | Rejected on reproducibility grounds alone: an index whose vectors depend on chunk ordering cannot be rebuilt to the same state, independent of any retrieval-quality finding. |

## Related

- ADR [1p92d](1p92d-adr%20embedding-precision-policy.md) — the precision policy this refines. Its
  recall parity result stands; this ADR adds the encoding constraint it did not consider.
- Wave `1v454 int8-embedding-determinism` / change `1v453-bug`.
- **`StaticShapeReranker` carries the same defect. CONFIRMED and measured 2026-08-12**, after this
  ADR was first written; the earlier "may carry" wording is superseded. It is a separate change and
  is **not** a regression from this wave, which never touched the reranker path.

  The reranker INT8 export carries **26** `DynamicQuantizeLinear` operators (its FP16 export carries
  none, so GPU hosts are unaffected, exactly as for the embedder). `rerank` pads to
  `RERANK_STATIC_BATCH` = 40 only when the group is short, so the same composition dependence
  applies. The difference that makes it worse rather than better: reranker scores **are compared
  across batch boundaries**. `AGENT_CANDIDATE_MAX` = 40 is a *post*-rerank selection backstop, not a
  cap on what reaches the reranker, and `VECTOR_TOP_K` = 30 per index across two indexes makes pools
  of roughly 60 routine, so a pool splits into 40 real plus a padded remainder. `_rerank` then
  min-max normalizes across all scores spanning both batches, and `_agent_rerank` sigmoids each
  logit into the relevance floor, drop-off, and confidence band.

  Measured: holding the query and the 60 candidates fixed and changing only which batch a passage
  lands in moved its score from `+1.4068` to `+1.5228`, about 1.8 points of sigmoid relevance. A
  correct cross-encoder scores each (query, passage) pair independently and must therefore be
  order-invariant; over five queries against real repository passages, reordering the same pool
  changed top-5 ordering in 3 and top-10 membership in 1, while the top-1 result held in all 5.
  A control isolates the cause and pre-validates the remedy: at pool sizes of 40 and 35, where no
  split occurs, ordering is identical in 5/5.

  Limits on that evidence: five queries, one pool, one shuffle seed, and passages assembled from
  repository text rather than drawn through the live retrieval pipeline. The direction and the cause
  are established; the rates are not calibrated frequencies.
