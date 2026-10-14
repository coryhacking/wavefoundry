#!/usr/bin/env python3
"""Opt-in, cached-only native memory relevance qualification (wave 20lul).

Run with the tool Python and an already-running qualified Tensorwell service:
  python -B tests/oracle/tensorwell_memory_parity.py

The 120-second process deadline includes reference construction. No downloads,
service lifecycle operations, live index/memory writes or output files. The
frozen historical bundles are parsed as data, never executed. Ordinary tests
can call load_fixture/evaluate_quality without importing inference libraries.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import sys
import threading

SCRIPTS_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SCRIPTS_ROOT.parents[2]
CUTOFF = -4.0
BUNDLES = {
    "qualification-inputs.json.gz": "7e0b8fb0014a17d2c44d92f30b73411feb6763d5a23cd80332696cf35a1a2eab",
    "summary5-integration-preflight.json.gz": "22ab975523551b9c12129a7433420271c582de2ab5411f636d3dcf9ed83091a0",
}
REFERENCE_FILES = {
    "model_int8.onnx": "a13ec391ca99f49886694e12d3e800521f36d4267d7d448c34421c541a2baf50",
    "tokenizer.json": "d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66",
    "rerank_cpu_int8_static_1x512.onnx": "c507287de3d8282d15cfe96160e4ec05cb8274378a3ac6bf764868b77e3854ac",
}
PROFILE_IDENTITY = "sha256:3a14f1775368230d55eecc1fec7a144b17b845e5706bc47757cb45470df699f8"
NEW_JUDGMENT = {
    "case": "integration-10",
    "candidate": "1vnka-mem fresh-install-gate-requirements-ship-as-install-data-applied",
    "classification": "direct_support",
    "provenance": "20lul readiness QA: independent NONBLIND frozen-query/summary assessment; not an original blind label",
}


def _check_digest(path: Path, expected: str) -> bytes:
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("qualification input identity mismatch")
    return data


def load_fixture(root: Path = REPO_ROOT) -> list[dict]:
    """Return 24 fixed cases with five RRF-ordered candidate summaries apiece."""
    folder = root / "docs/waves/1yad2 memory-retrieval-quality/evidence"
    files = {}
    for name, digest in BUNDLES.items():
        bundle = json.loads(gzip.decompress(_check_digest(folder / name, digest)))
        for filename, entry in bundle["files"].items():
            if hashlib.sha256(entry["text"].encode()).hexdigest() != entry["sha256"]:
                raise ValueError("embedded qualification input identity mismatch")
            if filename.endswith(".json"):
                files[filename] = json.loads(entry["text"])
    corpus = files["qualification-corpus.json"]
    records = {r["memory_id"]: r for r in corpus["records"] + corpus["archive_register"]}
    maps = files["wf-summary5-precision-map.json"]
    judgments = {}
    for case in files["wf-summary5-precision-verdicts.json"]["cases"]:
        judgments[case["id"]] = {
            maps[case["id"]][j["candidate_id"]]: j["classification"]
            for j in case["judgments"]
        }
        if any(j["authority_conflict"] for j in case["judgments"]):
            raise ValueError("historical authority conflict")
    cases = []
    for case in files["wf-summary5-integration-preflight.json"]["cases"]:
        scores = case["evidence"]["summary5"]["qualifier_scores"]
        # These scores were inserted in the five-item RRF order by the frozen
        # prototype. Check against the retained delivered order before reuse.
        candidate_ids = list(scores)
        if [mid for mid in candidate_ids if scores[mid] >= CUTOFF] != case["rankings"]["summary5"]:
            raise ValueError("historical RRF order mismatch")
        labels = dict(judgments.get(case["id"], {}))
        if case["id"] == NEW_JUDGMENT["case"]:
            mid = NEW_JUDGMENT["candidate"]
            if mid in labels:
                raise ValueError("new assessment must not replace a historical blind label")
            labels[mid] = NEW_JUDGMENT["classification"]
        cases.append({
            "id": case["id"], "query": case["query"], "candidate_ids": candidate_ids,
            "texts": [str(records[mid].get("summary") or records[mid].get("title") or "") for mid in candidate_ids],
            "relevant_ids": case["relevant_ids"], "labels": labels,
            "historical_scores": list(scores.values()),
        })
    if (len(cases) != 24 or any(len(c["candidate_ids"]) != 5 for c in cases)
            or sum(bool(c["relevant_ids"]) for c in cases) != 16):
        raise ValueError("frozen corpus census changed")
    return cases


def evaluate_quality(cases: list[dict], reference_scores: dict, service_scores: dict) -> dict:
    """Evaluate score maps keyed by case ID; malformed or unjudged output fails.

    Expected relevant IDs measure recall/MRR/useful answers. Independent support
    labels separately measure micro precision; adjacency is not direct support.
    Returned diagnostics contain case IDs/positions and numbers, never text.
    """
    expected = {case["id"] for case in cases}
    if not cases or len(expected) != len(cases) or set(reference_scores) != expected or set(service_scores) != expected:
        raise ValueError("case census mismatch")
    metrics = {name: {"recall_at_3": 0.0, "recall_at_10": 0.0, "mrr": 0.0,
                      "useful_cases": 0, "negative_returns": 0, "returned": 0, "direct_support": 0}
               for name in ("reference", "service")}
    flips, losses, negatives, unjudged = [], [], [], []
    max_delta, historical_delta, answerable, pairs = 0.0, 0.0, 0, 0
    for case in cases:
        cid = case["id"]
        ids, relevant = case["candidate_ids"], set(case["relevant_ids"])
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("candidate census mismatch")
        rows = [reference_scores[cid], service_scores[cid]]
        if any(len(row) != len(ids) or any(type(v) not in (float, int) or not math.isfinite(v) for v in row) for row in rows):
            raise ValueError("invalid raw relevance scores")
        selected = [[mid for mid, score in zip(ids, row) if score >= CUTOFF] for row in rows]
        answerable += bool(relevant)
        for name, chosen in zip(("reference", "service"), selected):
            m = metrics[name]
            m["returned"] += len(chosen)
            m["useful_cases"] += bool(set(chosen) & relevant)
            m["negative_returns"] += bool(chosen) and not relevant
            if relevant:
                for k in (3, 10):
                    m[f"recall_at_{k}"] += len(set(chosen[:k]) & relevant) / len(relevant)
                m["mrr"] += next((1 / rank for rank, mid in enumerate(chosen, 1) if mid in relevant), 0)
            for mid in chosen:
                label = case["labels"].get(mid)
                if label is None:
                    unjudged.append({"case": cid, "position": ids.index(mid), "backend": name})
                m["direct_support"] += label == "direct_support"
        if set(selected[0]) & relevant and not set(selected[1]) & relevant:
            losses.append(cid)
        if selected[1] and not relevant:
            negatives.append(cid)
        for i, (a, b) in enumerate(zip(*rows)):
            pairs += 1
            max_delta = max(max_delta, abs(a - b))
            historical_delta = max(historical_delta, abs(a - case["historical_scores"][i]))
            if (a >= CUTOFF) != (b >= CUTOFF):
                flips.append({"case": cid, "position": i, "reference": a, "service": b,
                              "expected_relevant": ids[i] in relevant, "support_label": case["labels"].get(ids[i])})
    for m in metrics.values():
        for key in ("recall_at_3", "recall_at_10", "mrr"):
            m[key] /= answerable or 1
        m["direct_support_precision"] = m["direct_support"] / m["returned"] if m["returned"] else 1.0
    ref, service = metrics["reference"], metrics["service"]
    comparisons = {key: service[key] >= ref[key] for key in ("recall_at_3", "recall_at_10", "mrr", "direct_support_precision")}
    return {"pass": not losses and not negatives and not unjudged and all(comparisons.values()),
            "cases": len(cases), "pairs": pairs, "cutoff": CUTOFF, "metrics": metrics,
            "non_regression": comparisons, "useful_support_losses": losses,
            "negative_case_returns": negatives, "unjudged_returns": unjudged,
            "classification_flips": flips, "classification_flip_count": len(flips),
            "max_abs_logit_delta": max_delta, "historical_reference_max_abs_delta": historical_delta}


def qualify() -> dict:
    if sys.platform != "darwin":
        raise RuntimeError("native qualification requires macOS")
    signal.alarm(120)
    try:
        os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                          WAVEFOUNDRY_DISABLE_BYTECODE_CACHE="1")
        sys.path.insert(0, str(SCRIPTS_ROOT))
        import accel_embedder as ae
        import tensorwell_client as tc
        from wf_server import server_impl
        from wf_server.memory_handlers import MEMORY_QUERY_MIN_LOGIT
        from unittest.mock import patch
        cases = load_fixture()
        if MEMORY_QUERY_MIN_LOGIT != CUTOFF or tc.RERANKER_IDENTITY != PROFILE_IDENTITY:
            raise ValueError("production cutoff or service identity changed")
        static = ae._ONNX_CACHE / ae._safe(tc.RERANKER_MODEL) / "rerank_cpu_int8_static_1x512.onnx"
        _check_digest(static, REFERENCE_FILES[static.name])
        files = ae._resolve_reranker_cpu_files(tc.RERANKER_MODEL)
        if files is None:
            raise ValueError("cached CPU reference absent")
        for filename in files:
            path = Path(filename)
            _check_digest(path, REFERENCE_FILES[path.name])
        # Use the production selection seam without constructing a live index.
        index = object.__new__(server_impl.WaveIndex)
        index._reranker_lock = threading.Lock()
        index._indexer_constant = lambda name: tc.RERANKER_MODEL
        with patch.object(ae, "StaticShapeReranker", side_effect=AssertionError("local construction forbidden")):
            remote = index._get_memory_reranker()
        if getattr(remote, "is_tensorwell", False) is not True:
            raise ValueError("production memory getter did not select ready Tensorwell")
        local = ae.StaticShapeReranker(tc.RERANKER_MODEL, ["CPUExecutionProvider"])
        reference, service = {}, {}
        for case in cases:
            reference[case["id"]] = local.rerank(case["query"], case["texts"])
            service[case["id"]] = remote.rerank(case["query"], case["texts"])
        result = evaluate_quality(cases, reference, service)
        result.update(input_bundle_sha256=BUNDLES, reference_file_sha256=REFERENCE_FILES,
                      profile_identity=PROFILE_IDENTITY, production_getter_selected=True,
                      new_judgment_provenance=NEW_JUDGMENT["provenance"],
                      limitations=["Frozen candidate order isolates reranker selection; not a live index or whole corpus test.",
                                   "CPU INT8 and service FP16 logits need not match; unchanged -4 quality gate evaluated separately.",
                                   "Historical blind support labels retained; one new independent nonblind direct-support label.",
                                   "No timing, memory-use, global near-cutoff parity or approval-authority claim."])
        return result
    finally:
        signal.alarm(0)


def main() -> int:
    try:
        result = qualify()
    except Exception as exc:
        print(json.dumps({"pass": False, "error_type": type(exc).__name__}))
        return 1
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
