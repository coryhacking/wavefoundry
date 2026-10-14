#!/usr/bin/env python3
"""Opt-in native qualification, outside ordinary test discovery.

Run with the tool-venv Python and a ready, configured qualified service:
  python -B tests/oracle/tensorwell_parity.py [--output /tmp/parity.json]

No installation, download, start/stop, configuration or index mutation. Local
models must already be cached. The 120-second process alarm bounds even native
reference construction; adapter requests retain their own total deadlines.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import platform
import signal
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_ROOT))

TEXTS = ["A cat rests on a warm windowsill.",
         "The database commits a transaction after validation.",
         "Solar panels convert sunlight into electricity.", "", "Café naïve 東京 — Unicode text.",
         "Long synthetic passage about database transactions and reliable software. " * 300]
QUERIES = ["Where does the cat rest?", "When is a database transaction committed?",
           "How is sunlight converted to electricity?", "", "東京 café"]
MIN_COSINE = 0.999
MAX_LOGIT_DELTA = 0.05  # strict, following existing FP16/FP32 reranker oracle
RANKING_MARGIN = 0.10


def qualify() -> dict:
    if platform.system() != "Darwin":
        raise RuntimeError("native qualification requires macOS")
    signal.alarm(120)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import numpy as np
    import indexer
    import tensorwell_client as tc
    from fastembed import TextEmbedding
    import onnxruntime as ort
    from tokenizers import Tokenizer
    ort.disable_telemetry_events()
    adapter = tc.select_embedder(indexer.DOCS_MODEL, "full")
    reranker = tc.select_reranker(indexer.RERANKER_MODEL)
    if adapter is None or reranker is None:
        raise RuntimeError("qualified pair unavailable")
    local = TextEmbedding(model_name=indexer.DOCS_MODEL, providers=["CPUExecutionProvider"], local_files_only=True)
    docs_ref = np.asarray(list(local.embed(TEXTS)), dtype=np.float32)
    prefix = indexer.query_embedding_prefix(indexer.DOCS_MODEL)
    query_ref = np.asarray(list(local.embed([prefix + q for q in QUERIES])), dtype=np.float32)
    # Same pinned FP32 export and 40x512 padded inputs as the existing
    # test_reranker_fp16_matches_fp32_when_available qualification oracle.
    root = Path.home() / ".wavefoundry/cache/onnx-src/models--Xenova--ms-marco-MiniLM-L-6-v2/snapshots/a09144355adeed5f58c8ed011d209bf8ee5a1fec"
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(root / "onnx/model.onnx"), sess_options=options, providers=["CPUExecutionProvider"])
    tokenizer = Tokenizer.from_file(str(root / "tokenizer.json"))
    tokenizer.enable_truncation(max_length=512)
    tokenizer.enable_padding(length=512)
    logits_ref = []
    for query in QUERIES:
        enc = tokenizer.encode_batch([(query, t) for t in TEXTS] + [(query, "")] * (40 - len(TEXTS)))
        features = {"input_ids": np.asarray([e.ids for e in enc], dtype=np.int64),
                    "attention_mask": np.asarray([e.attention_mask for e in enc], dtype=np.int64),
                    "token_type_ids": np.asarray([e.type_ids for e in enc], dtype=np.int64)}
        logits_ref.append(session.run(None, {i.name: features[i.name] for i in session.get_inputs()})[0].reshape(-1)[:len(TEXTS)])
    logits_ref = np.asarray(logits_ref)
    docs = np.asarray(list(adapter.embed(TEXTS)), dtype=np.float32)
    query_vectors = np.asarray([adapter.embed_query(q) for q in QUERIES], dtype=np.float32)
    logits = np.asarray([reranker.rerank(q, TEXTS) for q in QUERIES], dtype=np.float32)
    repeat = np.asarray(list(adapter.embed(TEXTS)), dtype=np.float32)
    singleton = np.asarray(list(adapter.embed(TEXTS[:1])), dtype=np.float32)
    singleton_logit = reranker.rerank(QUERIES[0], TEXTS[:1])[0]
    cosine = lambda a, b: np.sum(a * b, axis=-1) / (np.linalg.norm(a, axis=-1) * np.linalg.norm(b, axis=-1))
    minimum = float(min(cosine(docs, docs_ref).min(), cosine(query_vectors, query_ref).min()))
    delta = float(abs(logits - logits_ref).max())
    comparisons, preserved, margins = 0, True, []
    for expected, actual in zip(logits_ref, logits):
        for i in range(len(expected)):
            for j in range(i):
                if abs(expected[i] - expected[j]) > RANKING_MARGIN:
                    comparisons += 1
                    margins.append(float(abs(expected[i] - expected[j])))
                    preserved &= bool((expected[i] > expected[j]) == (actual[i] > actual[j]))
    nearest = bool((np.argmax(query_vectors[:3] @ docs[:3].T, axis=1) ==
                    np.argmax(query_ref[:3] @ docs_ref[:3].T, axis=1)).all())
    repeated = float(abs(repeat - docs).max())
    batch_cosine = float(cosine(singleton, docs[:1])[0])
    batch_delta = float(abs(singleton_logit - logits[0, 0]))
    result = {"production_adapter_probe": True,
              "profile_identities": {"arctic-fp16-coreml": tc.EMBEDDING_IDENTITY, "minilm-fp16-coreml": tc.RERANKER_IDENTITY},
              "thresholds": {"embedding_cosine_min": MIN_COSINE, "rerank_abs_delta_strict_max": MAX_LOGIT_DELTA, "ranking_margin_min": RANKING_MARGIN},
              "embedding_cosine_min": minimum, "rerank_max_abs_delta": delta,
              "ranking_margin_comparisons": comparisons, "ranking_preserved": preserved,
              "compared_ranking_margin_min": min(margins) if margins else None,
              "compared_ranking_margin_max": max(margins) if margins else None,
              "reference_top1_cosine_margins": [float(row[-1] - row[-2])
                                               for row in np.sort(query_ref[:3] @ docs_ref[:3].T, axis=1)],
              "nearest_document_top1_preserved": nearest, "repeated_embed_max_abs_delta": repeated,
              "single_vs_batch_embed_cosine": batch_cosine, "single_vs_batch_rerank_abs_delta": batch_delta}
    result["pass"] = bool(minimum >= MIN_COSINE and delta < MAX_LOGIT_DELTA and comparisons > 0 and preserved and nearest
                          and repeated == 0 and batch_cosine >= MIN_COSINE and batch_delta < MAX_LOGIT_DELTA)
    signal.alarm(0)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = qualify()
    except Exception as exc:
        print(json.dumps({"pass": False, "error_type": type(exc).__name__}))
        return 1
    encoded = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(encoded + "\n")
    print(encoded)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
