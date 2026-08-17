# Model Selection Record

Owner: Engineering
Status: active
Last verified: 2026-08-16

## Current Release Policy

Wavefoundry `1.16.0` advances the directly distributable companion asset to
`wavefoundry-models-2.zip`; releases after `1.17.0` declare `wavefoundry-models-3.zip`,
which carries the same weights and embedding fingerprint and corrects one cache
reference file (see ADR `1vglc`). The active set uses Snowflake Arctic Embed S for
both semantic layers and retains the MS MARCO MiniLM L-6 cross-encoder. The
document and code selectors remain independent configuration authorities even
though their v2 values are equal; equal identifiers reuse one process-local
embedder instance.

| Role | Runtime identifier | Artifact publisher | License | Runtime policy |
| --- | --- | --- | --- | --- |
| Docs embeddings | `Snowflake/snowflake-arctic-embed-s` | Snowflake on Hugging Face | Apache-2.0 | FP16 GPU / INT8 CPU, batch 32 |
| Code embeddings | `Snowflake/snowflake-arctic-embed-s` | Snowflake on Hugging Face | Apache-2.0 | FP16 GPU / INT8 CPU, batch 32 |
| Reranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Xenova ONNX export on Hugging Face | Apache-2.0 | FP16 GPU / INT8 CPU, batch 40 |

The generated verification manifest is the authority for exact upstream
revisions, file hashes, licenses, and attributions. The hand-authored supplier
decision below is intentionally separate from that reproducible bundle
identity. A model-set change must advance the model-set version and publish the
matching versioned companion asset; it advances the shared compatibility
fingerprint only when weights, pooling, or precision change (an executed byte
compare of the shipped weight files is required to keep it; ADR `1vglc`).

## 2026-08-11 Supplier-Origin Decision

- **Embedding supplier:** Snowflake Inc.
- **Artifact publisher:** the official `Snowflake` organization on Hugging
  Face.
- **Supplier-origin decision:** eligible. Snowflake Inc. is a United States
  corporation with its principal place of business in Bozeman, Montana. The
  selected artifact is published by Snowflake under Apache-2.0.
- **Verification date:** 2026-08-11.
- **Reviewer:** Product and Engineering owner (operator-approved).
- **Method:** manual evidence review. Wavefoundry does not infer or enforce
  jurisdiction at runtime; repeat this review whenever a model is swapped.
- **Evidence:** [Snowflake supplier identity and principal place of business](https://www.snowflake.com/procurement/doing-business-with-snowflake-ws/),
  [official Arctic Embed S artifact and model card](https://huggingface.co/Snowflake/snowflake-arctic-embed-s),
  [logical L6 model](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2),
  and [pinned Xenova ONNX export](https://huggingface.co/Xenova/ms-marco-MiniLM-L-6-v2).

The 28-query code and 100-query document comparisons recorded in
`model_swap_v2_result.json` support the single-model choice. Arctic S was
non-worse than Arctic XS on the accepted code metrics. On documents, every
paired 95% interval included zero; post-rerank top-5/top-10/top-20 recall tied,
top-3 differed by one query, and MRR differed by less than 0.001. The measured
same-machine FP16 indexing ratio remained below the accepted 2.0x ceiling.

## Upgrade Rule

"Newer" means a newer release-pinned compatible model set, not whatever an
upstream endpoint reports at upgrade time. Release and release-dry-run builds
must include the matching model companion; non-release local feature-pack
builds may remain model-optional. An embedding-set change forces one atomic
all-layer rebuild under the new shared fingerprint before publication.

Beginning with `1.16.0`, the freshly loaded cleanup phase may remove only the
exact retired Wavefoundry-owned BAAI cache components after the installed
canonical model set and a stable complete docs-and-code SQLite epoch prove
convergence. Arctic XS is inactive in v2 but is not part of that supplier
cleanup. Historical decision records remain the source for prior model choices.
