#!/usr/bin/env python3
"""Embedding model benchmark harness for Wavefoundry.

Measures three workloads per candidate model:
  - query:       Single-query embedding latency (P50, P95 over N_QUERY_REPS runs)
  - incremental: Embed a small batch (5 chunks) simulating an incremental update
  - full:        Embed the full project corpus

Also measures:
  - Peak RSS during full rebuild
  - Retrieval quality (top-3 accuracy) against retrieval_eval.json ground truth
  - 512-token truncation rate on the corpus

Usage:
    python3 embed_bench.py [--root <repo-root>] [--models <m1,m2,...>] [--report <out.json>]

Outputs a JSON report to --report (default: bench_report.json in same directory).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import resource
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Optional

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
BENCH_DIR = Path(__file__).resolve().parent
EVAL_PATH = BENCH_DIR / "retrieval_eval.json"
MODEL_SWAP_CODE_PATH = BENCH_DIR / "model_swap_code_queries.json"
MODEL_SWAP_DOCS_PATH = BENCH_DIR / "model_swap_docs_queries.json"
MODEL_SWAP_RESULT_PATH = BENCH_DIR / "model_swap_v2_result.json"
MODEL_SWAP_CODE_SHA256 = "77e069006207fd04247476c2660d6dd16e0595a77489c51e9e32a348d5a59bd9"
MODEL_SWAP_DOCS_SHA256 = "63359684afa4ba0cd91aa5c51f109176223cedd1dd4485bf838e7e0bd7a411e5"

DEFAULT_MODELS = ["Snowflake/snowflake-arctic-embed-s"]
N_QUERY_REPS = 20
INCREMENTAL_SAMPLE = 5
TOP_K = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_indexer():
    spec = importlib.util.spec_from_file_location("indexer", SCRIPTS_ROOT / "indexer.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["indexer"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_chunks(root: Path) -> tuple[list[dict], list[dict]]:
    """Load current project index chunks from disk."""
    index_dir = root / ".wavefoundry" / "index"
    doc_chunks, code_chunks = [], []
    for name, target in [("docs.json", doc_chunks), ("code.json", code_chunks)]:
        p = index_dir / name
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            target.extend(data if isinstance(data, list) else data.get("chunks", []))
    return doc_chunks, code_chunks


def _get_embedder(model_name: str, indexer_mod):
    return indexer_mod._get_embedder(model_name)


def _embed_texts(embedder, texts: list[str], indexer_mod) -> Any:
    return indexer_mod._embed_texts(embedder, texts)


def _peak_rss_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # macOS reports in bytes, Linux in kilobytes
    if sys.platform == "darwin":
        return usage.ru_maxrss / (1024 * 1024)
    return usage.ru_maxrss / 1024


def _cosine_top_k(query_vec, corpus_vecs, chunks: list[dict], k: int) -> list[dict]:
    import numpy as np
    qn = query_vec / (np.linalg.norm(query_vec) + 1e-9)
    norms = np.linalg.norm(corpus_vecs, axis=1, keepdims=True) + 1e-9
    scores = corpus_vecs / norms @ qn
    idx = np.argsort(-scores)[:k]
    return [{"chunk": chunks[i], "score": float(scores[i])} for i in idx]


def _truncation_rate(chunks: list[dict], model_name: str) -> dict:
    """Estimate fraction of chunks that would be truncated at model's token limit."""
    try:
        from fastembed import TextEmbedding
        model_info = next(
            (m for m in TextEmbedding.list_supported_models() if m["model"] == model_name),
            None,
        )
        max_tokens = None  # will be resolved from known_limits below
        # Use known limits
        known_limits = {
            "Snowflake/snowflake-arctic-embed-s": 512,
            "jinaai/jina-embeddings-v2-base-code": 8192,
            "nomic-ai/nomic-embed-text-v1.5": 8192,
        }
        max_tokens = known_limits.get(model_name, 512)
    except Exception:
        max_tokens = 512

    # Rough token estimate: ~0.75 tokens per word
    over = [c for c in chunks if len(c.get("text", "").split()) * 1.33 > max_tokens]
    return {
        "max_tokens": max_tokens,
        "truncated_count": len(over),
        "total_count": len(chunks),
        "truncation_rate": round(len(over) / len(chunks), 4) if chunks else 0.0,
    }


# ---------------------------------------------------------------------------
# Workload measurements
# ---------------------------------------------------------------------------

def measure_query_latency(embedder, query: str, indexer_mod, n_reps: int = N_QUERY_REPS) -> dict:
    times = []
    for _ in range(n_reps):
        t0 = time.perf_counter()
        _embed_texts(embedder, [query], indexer_mod)
        times.append(time.perf_counter() - t0)
    times.sort()
    p50 = times[len(times) // 2]
    p95 = times[int(len(times) * 0.95)]
    return {"p50_ms": round(p50 * 1000, 2), "p95_ms": round(p95 * 1000, 2), "n_reps": n_reps}


def measure_incremental(embedder, chunks: list[dict], indexer_mod, sample: int = INCREMENTAL_SAMPLE) -> dict:
    sample_chunks = chunks[:sample]
    texts = [c.get("text", "") for c in sample_chunks]
    t0 = time.perf_counter()
    _embed_texts(embedder, texts, indexer_mod)
    elapsed = time.perf_counter() - t0
    return {"chunks": len(sample_chunks), "elapsed_ms": round(elapsed * 1000, 2)}


def measure_full_rebuild(embedder, chunks: list[dict], indexer_mod) -> tuple[dict, Any]:
    rss_before = _peak_rss_mb()
    texts = [c.get("text", "") for c in chunks]
    t0 = time.perf_counter()
    corpus_vecs = _embed_texts(embedder, texts, indexer_mod)
    elapsed = time.perf_counter() - t0
    rss_after = _peak_rss_mb()
    stats = {
        "chunks": len(chunks),
        "elapsed_s": round(elapsed, 3),
        "chunks_per_sec": round(len(chunks) / elapsed, 1) if elapsed > 0 else 0,
        "peak_rss_mb": round(rss_after, 1),
        "rss_delta_mb": round(rss_after - rss_before, 1),
    }
    return stats, corpus_vecs


# ---------------------------------------------------------------------------
# Retrieval quality
# ---------------------------------------------------------------------------

def measure_retrieval_quality(
    embedder,
    all_chunks: list[dict],
    indexer_mod,
    corpus_vecs: Any = None,
    eval_path: Path = EVAL_PATH,
    top_k: int = TOP_K,
) -> dict:
    import numpy as np

    if not eval_path.exists():
        return {"error": f"eval file not found: {eval_path}"}

    eval_data = json.loads(eval_path.read_text(encoding="utf-8"))
    queries = eval_data.get("queries", [])
    if not queries:
        return {"error": "no queries in eval file"}

    # Reuse vectors from full rebuild if available; otherwise embed the corpus.
    if corpus_vecs is None:
        texts = [c.get("text", "") for c in all_chunks]
        corpus_vecs = _embed_texts(embedder, texts, indexer_mod)

    results_by_kind: dict[str, list] = {}
    all_results = []

    for entry in queries:
        qid = entry["id"]
        kind = entry.get("kind", "unknown")
        query = entry["query"]
        expected = entry.get("expected_paths", [])

        q_vec = _embed_texts(embedder, [query], indexer_mod)[0]
        top_hits = _cosine_top_k(q_vec, corpus_vecs, all_chunks, top_k)

        hit_paths = [h["chunk"].get("path", "") for h in top_hits]
        # A hit counts if any returned path starts with any expected prefix.
        hit = any(
            any(hp.startswith(ep) or ep in hp for ep in expected)
            for hp in hit_paths
        )

        result = {
            "id": qid,
            "kind": kind,
            "query": query,
            "hit": hit,
            "top_paths": hit_paths,
            "expected": expected,
            "top_score": top_hits[0]["score"] if top_hits else 0.0,
        }
        all_results.append(result)
        results_by_kind.setdefault(kind, []).append(hit)

    overall_hits = sum(r["hit"] for r in all_results)
    summary: dict[str, Any] = {
        "top_k": top_k,
        "total_queries": len(queries),
        "overall_accuracy": round(overall_hits / len(queries), 4) if queries else 0.0,
        "by_kind": {
            kind: {
                "queries": len(hits),
                "hits": sum(hits),
                "accuracy": round(sum(hits) / len(hits), 4) if hits else 0.0,
            }
            for kind, hits in results_by_kind.items()
        },
        "per_query": all_results,
    }
    return summary


def _rank_metrics(
    rows: list[dict[str, Any]], candidate: str, stage: str
) -> dict[str, Any]:
    cutoffs = (1, 3, 5, 10, 20, 40)
    key = f"{candidate}_{stage}_rank"
    ranks = [row.get(key) for row in rows]
    reciprocal = [
        1.0 / int(rank)
        if isinstance(rank, int) and 0 < rank <= 40
        else 0.0
        for rank in ranks
    ]
    return {
        "queries": len(rows),
        "recall": {
            str(cutoff): round(
                sum(
                    isinstance(rank, int) and 0 < rank <= cutoff
                    for rank in ranks
                )
                / len(rows),
                6,
            )
            for cutoff in cutoffs
        },
        "mrr_at_40": round(sum(reciprocal) / len(rows), 6),
    }


def _paired_interval(
    rows: list[dict[str, Any]], stage: str, cutoff: int | None
) -> dict[str, float]:
    deltas: list[float] = []
    for row in rows:
        xs_rank = row.get(f"xs_{stage}_rank")
        s_rank = row.get(f"s_{stage}_rank")
        if cutoff is None:
            xs_value = 1.0 / xs_rank if isinstance(xs_rank, int) and 0 < xs_rank <= 40 else 0.0
            s_value = 1.0 / s_rank if isinstance(s_rank, int) and 0 < s_rank <= 40 else 0.0
        else:
            xs_value = float(isinstance(xs_rank, int) and 0 < xs_rank <= cutoff)
            s_value = float(isinstance(s_rank, int) and 0 < s_rank <= cutoff)
        deltas.append(s_value - xs_value)
    mean = sum(deltas) / len(deltas)
    margin = (
        1.96 * statistics.stdev(deltas) / math.sqrt(len(deltas))
        if len(deltas) > 1
        else 0.0
    )
    return {
        "mean": round(mean, 6),
        "low_95": round(mean - margin, 6),
        "high_95": round(mean + margin, 6),
    }


def model_swap_metrics(result: dict[str, Any]) -> dict[str, Any]:
    corpora = result.get("corpora") or {}
    computed: dict[str, Any] = {}
    for corpus in ("code", "documents"):
        rows = list((corpora.get(corpus) or {}).get("per_query") or [])
        computed[corpus] = {
            stage: {
                candidate: _rank_metrics(rows, candidate, stage)
                for candidate in ("xs", "s")
            }
            for stage in ("raw", "reranked")
        }
    document_rows = list((corpora.get("documents") or {}).get("per_query") or [])
    computed["documents"]["paired_s_minus_xs_95"] = {
        f"top_{cutoff}": _paired_interval(document_rows, "reranked", cutoff)
        for cutoff in (3, 5, 10, 20, 40)
    }
    computed["documents"]["paired_s_minus_xs_95"]["mrr_at_40"] = (
        _paired_interval(document_rows, "reranked", None)
    )
    for corpus in ("code", "documents"):
        timing = (corpora.get(corpus) or {}).get("timing_seconds") or {}
        xs = float(timing.get("xs") or 0.0)
        s = float(timing.get("s") or 0.0)
        computed[corpus]["s_over_xs_timing_ratio"] = round(s / xs, 6) if xs else None
    return computed


def validate_model_swap_result(
    result_path: Path = MODEL_SWAP_RESULT_PATH,
    code_path: Path = MODEL_SWAP_CODE_PATH,
    docs_path: Path = MODEL_SWAP_DOCS_PATH,
) -> dict[str, Any]:
    """Inference-free validation of the committed controlled comparison."""
    errors: list[str] = []
    result = json.loads(result_path.read_text(encoding="utf-8"))
    code_input = json.loads(code_path.read_text(encoding="utf-8"))
    docs_input = json.loads(docs_path.read_text(encoding="utf-8"))
    if hashlib.sha256(code_path.read_bytes()).hexdigest() != MODEL_SWAP_CODE_SHA256:
        errors.append("code query/answer fixture differs from the reviewed input")
    if hashlib.sha256(docs_path.read_bytes()).hexdigest() != MODEL_SWAP_DOCS_SHA256:
        errors.append("document query/answer fixture differs from the reviewed input")
    code_rows = list((result.get("corpora", {}).get("code") or {}).get("per_query") or [])
    docs_rows = list((result.get("corpora", {}).get("documents") or {}).get("per_query") or [])
    if len(code_input.get("queries") or []) != 28 or len(code_rows) != 28:
        errors.append("code comparison must contain exactly 28 queries")
    if len(docs_input.get("queries") or []) != 100 or len(docs_rows) != 100:
        errors.append("document comparison must contain exactly 100 queries")
    for name, input_rows, result_rows in (
        ("code", code_input.get("queries") or [], code_rows),
        ("documents", docs_input.get("queries") or [], docs_rows),
    ):
        if [row.get("id") for row in input_rows] != [row.get("id") for row in result_rows]:
            errors.append(f"{name} query IDs/order differ from the committed input")
        if [row.get("query") for row in input_rows] != [row.get("query") for row in result_rows]:
            errors.append(f"{name} query text differs from the committed input")
        if len({row.get("id") for row in result_rows}) != len(result_rows):
            errors.append(f"{name} query IDs are not unique")
    expected_provenance = {
        "xs_model": "Snowflake/snowflake-arctic-embed-xs",
        "xs_revision": "d8c86521100d3556476a063fc2342036d45c106f",
        "s_model": "Snowflake/snowflake-arctic-embed-s",
        "s_revision": "e596f507467533e48a2e17c007f0e1dacc837b33",
        "reranker_logical_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
        "reranker_artifact": "Xenova/ms-marco-MiniLM-L-6-v2",
        "reranker_revision": "a09144355adeed5f58c8ed011d209bf8ee5a1fec",
    }
    if result.get("provenance") != expected_provenance:
        errors.append("pinned model provenance differs from the reviewed comparison")
    runtime = result.get("runtime") or {}
    if runtime.get("provider") != "MPS" or runtime.get("dtype") != "FP16" or runtime.get("batch_size") != 32:
        errors.append("controlled runtime must be MPS FP16 at batch 32")
    computed = model_swap_metrics(result)
    if result.get("metrics") != computed:
        errors.append("stored metrics/intervals/ratios do not recompute from per-query ranks")
    code = computed.get("code") or {}
    for stage, cutoffs in (("raw", (3, 10)), ("reranked", (5, 10))):
        for cutoff in cutoffs:
            if code[stage]["s"]["recall"][str(cutoff)] < code[stage]["xs"]["recall"][str(cutoff)]:
                errors.append(f"code S regresses {stage} top-{cutoff}")
        if code[stage]["s"]["mrr_at_40"] < code[stage]["xs"]["mrr_at_40"]:
            errors.append(f"code S regresses {stage} MRR")
    for row in code_rows:
        xs_rank, s_rank = row.get("xs_raw_rank"), row.get("s_raw_rank")
        if isinstance(xs_rank, int) and xs_rank <= 40 and not (isinstance(s_rank, int) and s_rank <= 40):
            errors.append(f"code S loses required answer from top 40: {row.get('id')}")
    paired = computed.get("documents", {}).get("paired_s_minus_xs_95") or {}
    for metric, interval in paired.items():
        if not (interval["low_95"] <= 0 <= interval["high_95"]):
            errors.append(f"document paired interval excludes zero: {metric}")
        if interval["mean"] < -0.02:
            errors.append(f"document S point estimate exceeds regression budget: {metric}")
    for corpus in ("code", "documents"):
        ratio = computed.get(corpus, {}).get("s_over_xs_timing_ratio")
        if ratio is None or ratio > 2.0:
            errors.append(f"{corpus} S timing ratio exceeds 2.0x")
    return {"ok": not errors, "errors": errors, "computed": computed}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_benchmark(
    model_name: str,
    root: Path,
    doc_chunks: list[dict],
    code_chunks: list[dict],
    indexer_mod,
) -> dict:
    all_chunks = doc_chunks + code_chunks
    print(f"\n{'='*60}", flush=True)
    print(f"Model: {model_name}", flush=True)
    print(f"Corpus: {len(doc_chunks)} doc chunks + {len(code_chunks)} code chunks", flush=True)

    print("  Loading model...", flush=True)
    t_load = time.perf_counter()
    embedder = _get_embedder(model_name, indexer_mod)
    load_ms = round((time.perf_counter() - t_load) * 1000, 1)
    print(f"  Model loaded in {load_ms}ms", flush=True)

    print("  Query latency...", flush=True)
    query_result = measure_query_latency(
        embedder, "function that parses wave IDs from a string", indexer_mod
    )
    print(f"  Query P50={query_result['p50_ms']}ms P95={query_result['p95_ms']}ms", flush=True)

    print(f"  Incremental ({INCREMENTAL_SAMPLE} chunks)...", flush=True)
    incr_result = measure_incremental(embedder, all_chunks, indexer_mod)
    print(f"  Incremental: {incr_result['elapsed_ms']}ms", flush=True)

    print(f"  Full rebuild ({len(all_chunks)} chunks)...", flush=True)
    full_result, corpus_vecs = measure_full_rebuild(embedder, all_chunks, indexer_mod)
    print(f"  Full: {full_result['elapsed_s']}s, {full_result['chunks_per_sec']} chunks/s, {full_result['peak_rss_mb']}MB RSS", flush=True)

    print("  Retrieval quality...", flush=True)
    quality = measure_retrieval_quality(embedder, all_chunks, indexer_mod, corpus_vecs=corpus_vecs)
    if "error" not in quality:
        print(f"  Quality: overall={quality['overall_accuracy']:.0%}, "
              f"code={quality['by_kind'].get('code', {}).get('accuracy', 0):.0%}, "
              f"docs={quality['by_kind'].get('docs', {}).get('accuracy', 0):.0%}", flush=True)

    print("  Truncation rate...", flush=True)
    trunc = _truncation_rate(all_chunks, model_name)
    print(f"  Truncation: {trunc['truncated_count']}/{trunc['total_count']} ({trunc['truncation_rate']:.1%}) exceed {trunc['max_tokens']} tokens", flush=True)

    return {
        "model": model_name,
        "model_load_ms": load_ms,
        "corpus": {"doc_chunks": len(doc_chunks), "code_chunks": len(code_chunks), "total": len(all_chunks)},
        "query_latency": query_result,
        "incremental": incr_result,
        "full_rebuild": full_result,
        "retrieval_quality": quality,
        "truncation": trunc,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Embedding model benchmark harness")
    parser.add_argument("--root", default=".", help="Repository root (default: cwd)")
    parser.add_argument(
        "--models",
        default=",".join(DEFAULT_MODELS),
        help=f"Comma-separated model names (default: {','.join(DEFAULT_MODELS)})",
    )
    parser.add_argument(
        "--report",
        default=str(BENCH_DIR / "bench_report.json"),
        help="Output JSON report path",
    )
    parser.add_argument(
        "--model-swap-validate",
        nargs="?",
        const=str(MODEL_SWAP_RESULT_PATH),
        help="Recompute and validate a committed model-swap result without model inference",
    )
    args = parser.parse_args()

    if args.model_swap_validate:
        validation = validate_model_swap_result(Path(args.model_swap_validate))
        print(json.dumps(validation, indent=2, sort_keys=True))
        if not validation["ok"]:
            raise SystemExit(1)
        return

    root = Path(args.root).resolve()
    models = [m.strip() for m in args.models.split(",") if m.strip()]

    print(f"Loading indexer from {SCRIPTS_ROOT}...", flush=True)
    indexer_mod = _load_indexer()

    print(f"Loading corpus from {root}...", flush=True)
    doc_chunks, code_chunks = _load_chunks(root)
    if not doc_chunks and not code_chunks:
        print("ERROR: No index chunks found. Run index_build first.", file=sys.stderr)
        sys.exit(1)

    report: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "root": str(root),
        "models": [],
        "decision_criteria": {
            "code_retrieval_improvement_threshold": 0.15,
            "quality_regression_max": 0.05,
            "full_rebuild_speedup_for_coreml": 3.0,
            "query_speedup_for_warmprocess": 5.0,
            "memory_growth_max": 2.0,
            "truncation_rate_for_longcontext": 0.02,
        },
    }

    baseline_quality: Optional[float] = None
    baseline_rss: Optional[float] = None

    for i, model_name in enumerate(models):
        try:
            result = run_benchmark(model_name, root, doc_chunks, code_chunks, indexer_mod)
            if i == 0:
                baseline_quality = result["retrieval_quality"].get("overall_accuracy")
                baseline_rss = result["full_rebuild"].get("peak_rss_mb")

            # Apply decision criteria vs baseline
            if i > 0 and baseline_quality is not None:
                current_quality = result["retrieval_quality"].get("overall_accuracy", 0)
                code_quality = result["retrieval_quality"].get("by_kind", {}).get("code", {}).get("accuracy", 0)
                baseline_code = report["models"][0]["retrieval_quality"].get("by_kind", {}).get("code", {}).get("accuracy", 0)
                result["vs_baseline"] = {
                    "quality_delta": round(current_quality - baseline_quality, 4),
                    "code_quality_delta": round(code_quality - baseline_code, 4),
                    "quality_regression": (baseline_quality - current_quality) > 0.05,
                    "code_improvement_met": (code_quality - baseline_code) >= 0.15,
                    "memory_ok": (result["full_rebuild"]["peak_rss_mb"] / (baseline_rss or 1)) <= 2.0,
                }

            report["models"].append(result)
        except Exception as exc:
            print(f"  ERROR benchmarking {model_name}: {exc}", file=sys.stderr)
            report["models"].append({"model": model_name, "error": str(exc)})

    out_path = Path(args.report)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport written to {out_path}", flush=True)

    # Print summary table
    print("\n" + "="*60, flush=True)
    print("SUMMARY", flush=True)
    print("="*60, flush=True)
    print(f"{'Model':<45} {'Quality':>8} {'Code':>6} {'Docs':>6} {'Full(s)':>8} {'RSS(MB)':>8}", flush=True)
    print("-"*60, flush=True)
    for m in report["models"]:
        if "error" in m:
            print(f"{m['model']:<45} ERROR: {m['error']}", flush=True)
            continue
        q = m["retrieval_quality"]
        full = m["full_rebuild"]
        print(
            f"{m['model']:<45} "
            f"{q.get('overall_accuracy', 0):>8.1%} "
            f"{q.get('by_kind', {}).get('code', {}).get('accuracy', 0):>6.1%} "
            f"{q.get('by_kind', {}).get('docs', {}).get('accuracy', 0):>6.1%} "
            f"{full.get('elapsed_s', 0):>8.1f} "
            f"{full.get('peak_rss_mb', 0):>8.0f}",
            flush=True,
        )


if __name__ == "__main__":
    main()
