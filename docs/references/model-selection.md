# Model Selection Record

Owner: Engineering
Status: active
Last verified: 2026-08-03

## Current Release Policy

The directly distributable model-set asset (`wavefoundry-models-1.zip`) pins the already validated runtime
set: Snowflake Arctic Embed XS for docs, BAAI BGE Small v1.5 for code, and the
Xenova ONNX export of the MS MARCO MiniLM L-6 reranker. The bundle carries the
cache snapshots required for FastEmbed and the clean ONNX acceleration path;
it does not include compiled CoreML/static artifacts.

| Role | Runtime identifier | Artifact source | License | Decision |
| --- | --- | --- | --- | --- |
| Docs embeddings | `Snowflake/snowflake-arctic-embed-xs` | Snowflake cache + clean ONNX snapshot | Apache-2.0 | Retain |
| Code embeddings | `BAAI/bge-small-en-v1.5` | FastEmbed/Qdrant cache + Xenova clean ONNX snapshot | MIT | Retain |
| Reranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Xenova clean ONNX snapshot | Apache-2.0 | Retain |

The package manifest, rather than this narrative, is the authority for the
exact upstream revisions and per-file hashes. A new model set must advance the
model-set version and declared compatibility fingerprint, re-evaluate index
impact, and be published once under its own versioned asset name.

## 2026-08-03 Compatibility Check

- Runtime examined: FastEmbed 0.8.0 supported-model catalog.
- Candidate set: the current validated models; Jina Embeddings v2 Base Code and
  Jina reranker v1 Turbo as supported Apache-2.0 candidates.
- Rejected for this packaging release: BGE-M3 and BGE reranker v2-M3. They are
  not drop-in FastEmbed 0.8.0 choices, alter runtime/index assumptions, and
  therefore require a separately admitted model/runtime migration.
- Decision: retain the current models. Their retrieval and acceleration
  behavior is already integrated and their Apache-2.0/MIT terms permit direct
  distribution when notices and provenance are retained.

Sources: [FastEmbed supported models](https://qdrant.github.io/fastembed/examples/Supported_Models/),
[Arctic Embed XS](https://huggingface.co/Snowflake/snowflake-arctic-embed-xs),
[BGE Small v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5), and
[MS MARCO MiniLM L-6](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2).

## Upgrade Rule

"Newer" means a newer release-pinned, compatible model set—not whatever an
upstream endpoint reports at target upgrade time. A standard framework upgrade
detects that state, retains the verified cache, and reports the exact
independently versioned model-set asset required for replacement. The asset may
atomically replace an older verified matching set. Framework-only releases do
not republish model bytes. Any embedding-set change forces a full rebuild of
the affected semantic layer.
