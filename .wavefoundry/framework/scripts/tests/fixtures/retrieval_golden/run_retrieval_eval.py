"""Component-only chunk/embedder retrieval benchmark (wave 1wfsl, 1wfr8-enh).

This is not the production retrieval-quality gate. It deliberately isolates
chunk shape, embedding, and dense cosine ranking over committed fixtures; it
does not exercise the current Lance/FTS hybrid public response paths,
reranking, partitioning, confidence, or degraded modes. Use
``.wavefoundry/framework/scripts/retrieval_eval.py`` for standing production
retrieval evidence.

Measures natural-language retrieval quality over committed fixture corpora by
running the REAL shipped pipeline stages: `chunker.chunk_file` chunks each
fixture, the indexer's embedder (`indexer._get_embedder`, same model constants,
documents bare / queries prefixed via `indexer.query_embedding_prefix`) embeds
chunks and queries, and cosine ranking scores each query against the corpus.

Fixed metric definitions (1wfr8 Requirement 4; 1wfsm Requirement 5 reuses them):

- recall at 5: fraction of queries whose expected chunk appears in the top 5.
- mean reciprocal rank (MRR): mean over queries of 1/rank of the first
  expected chunk (0 when absent from the top `--depth`, default 20).

A chunk is "expected" for a query when it comes from the query's expected file
AND contains the expected anchor substring — content-anchored labeling, stable
across chunk-identity changes (which are the very thing under measurement).

Query sets:
- golden_queries_specs.json  (1wfr8): [{id, query, expected_file, expected_anchor}]
  Wave 1wik9 (1wfso) adds format-prefixed ids (`asyncapi-q01`, `graphql-q01`,
  `proto-q01`): the specs run reports `metrics` over the UNPREFIXED core set
  only (so the frozen 1wfr8 baseline readout keeps its meaning) plus
  `metrics_by_format` per prefix group.
- golden_queries_prose.json  (1wfsm): [{id, query, variants: {md|rst|adoc:
  {file, anchor}}}] — the same information need labeled per format, so
  per-format recall/MRR compare on equivalent content. Wave 1wik9 (1whup) adds
  single-variant fence-md/fence-rst/fence-adoc entries targeting doc-code
  chunks with anchors proven unique to their expected file.
- golden_queries_diagrams.json (1whuq): flat spec-shaped entries over the
  per-set-disjoint diagrams/ corpus (Mermaid/PlantUML/DOT); evaluated against
  the docs-kind mirror like prose (diagram chunks are docs-routed doc-code).

Usage (from the repository root; the corpus is the fixture tree next to this
script):
    python3 .wavefoundry/framework/scripts/tests/fixtures/retrieval_golden/run_retrieval_eval.py \
        --set specs --out <results.json> [--label before|after]

The output JSON records per-query rank/hit plus the aggregate metrics; commit
result files as wave evidence.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[2]
sys.path.insert(0, str(SCRIPTS))

import numpy as np  # noqa: E402

import chunker  # noqa: E402
import indexer  # noqa: E402

RANK_DEPTH_DEFAULT = 20


# Layer mirrors: the docs table serves docs-kind chunks only (kind-based
# routing), so the prose eval filters to them — a format with no doc-kind
# chunks measures as the true zero-coverage it has in the shipped surface.
# The specs eval mirrors the code layer (code-kind chunks).
# doc-code (1whup): extracted fences/directive bodies route to the docs table,
# so the eval's docs-layer mirror carries them — the eval models the shipped surface.
_DOCS_KINDS = frozenset({"doc", "doc-summary", "seed", "prompt", "doc-code"})
_CODE_KINDS = frozenset({"code", "code-summary"})


def _chunk_corpus(corpus_dir: Path, kinds: frozenset[str]) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(p for p in corpus_dir.rglob("*") if p.is_file()):
        rel = str(path.relative_to(corpus_dir)).replace("\\", "/")
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for chunk in chunker.chunk_file(source, rel):
            if chunk.kind not in kinds:
                continue
            rows.append({
                "file": rel,
                "chunk_id": chunk.id,
                "kind": chunk.kind,
                "text": chunk.text,
            })
    return rows


def _embed(texts: list[str], model_name: str) -> np.ndarray:
    embedder = indexer._get_embedder(model_name)
    vectors = list(embedder.embed(texts, batch_size=64))
    mat = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


def _rank(query_vec: np.ndarray, doc_mat: np.ndarray) -> np.ndarray:
    scores = doc_mat @ query_vec
    return np.argsort(-scores)


def _evaluate(queries: list[dict], rows: list[dict], model_name: str,
              depth: int) -> dict:
    if not rows:
        # Structural zero: the corpus yields no chunks in the mirrored kinds
        # (e.g. the 1whuq diagrams baseline, where diagram files emit no
        # docs-kind chunks pre-change). Every query scores rank 0.
        per_query = [{
            "id": q["id"], "query": q["query"],
            "expected_file": q["expected_file"],
            "rank": 0, "hit_at_5": False, "top5": [],
        } for q in queries]
        n = len(per_query) or 1
        return {
            "recall_at_5": 0.0, "mrr": 0.0,
            "query_count": len(per_query), "chunk_count": 0,
            "per_query": per_query,
        }
    doc_mat = _embed([r["text"] for r in rows], model_name)
    prefix = indexer.query_embedding_prefix(model_name)
    q_mat = _embed([prefix + q["query"] for q in queries], model_name)
    per_query = []
    for qi, q in enumerate(queries):
        order = _rank(q_mat[qi], doc_mat)[:depth]
        rank = 0
        top5_files = []
        for pos, row_idx in enumerate(order, start=1):
            row = rows[int(row_idx)]
            if pos <= 5:
                top5_files.append(f"{row['file']}#{row['chunk_id']}")
            if rank == 0 and row["file"] == q["expected_file"] \
                    and q["expected_anchor"] in row["text"]:
                rank = pos
        per_query.append({
            "id": q["id"],
            "query": q["query"],
            "expected_file": q["expected_file"],
            "rank": rank,           # 0 = not found within depth
            "hit_at_5": 0 < rank <= 5,
            "top5": top5_files,
        })
    n = len(per_query) or 1
    return {
        "recall_at_5": sum(1 for r in per_query if r["hit_at_5"]) / n,
        "mrr": sum((1.0 / r["rank"]) if r["rank"] else 0.0 for r in per_query) / n,
        "query_count": len(per_query),
        "chunk_count": len(rows),
        "per_query": per_query,
    }


def _load_spec_queries(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_prose_queries(path: Path) -> dict[str, list[dict]]:
    """Expand matched-format variants into one flat query list per format."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    by_format: dict[str, list[dict]] = {}
    for entry in raw:
        for fmt, target in entry["variants"].items():
            by_format.setdefault(fmt, []).append({
                "id": f"{entry['id']}:{fmt}",
                "query": entry["query"],
                "expected_file": target["file"],
                "expected_anchor": target["anchor"],
            })
    return by_format


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", choices=["specs", "prose", "diagrams"], required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--label", default="")
    parser.add_argument("--depth", type=int, default=RANK_DEPTH_DEFAULT)
    args = parser.parse_args()

    model_name = indexer.CODE_MODEL if args.set == "specs" else indexer.DOCS_MODEL
    corpus_dir = HERE / args.set
    result: dict = {
        "set": args.set,
        "label": args.label,
        "model": model_name,
        "chunker_version": chunker.CHUNKER_VERSION,
        "rank_depth": args.depth,
    }
    if args.set == "specs":
        queries = _load_spec_queries(HERE / "golden_queries_specs.json")
        rows = _chunk_corpus(corpus_dir, _CODE_KINDS)
        if not queries or not rows:
            parser.error(
                "component benchmark corpus is empty or absent; no production "
                "retrieval score was produced"
            )
        # Per-format grouping (1wfso Requirement 1): ids with a format prefix
        # (`asyncapi-q01`) group under that format so each format's bar reads
        # directly off the committed result JSON; unprefixed ids (the original
        # 24-query set) group as `core`, and `metrics` stays the CORE-only
        # aggregate so the frozen 1wfr8 baseline readout keeps its meaning.
        def _fmt(qid: str) -> str:
            head = qid.split("-", 1)[0]
            return head if "-" in qid and not head.startswith("q") else "core"
        by_format: dict[str, list[dict]] = {}
        for q in queries:
            by_format.setdefault(_fmt(q["id"]), []).append(q)
        result["metrics"] = _evaluate(
            by_format.get("core", []), rows, model_name, args.depth)
        if set(by_format) - {"core"}:
            result["metrics_by_format"] = {
                fmt: _evaluate(qs, rows, model_name, args.depth)
                for fmt, qs in sorted(by_format.items())
            }
    elif args.set == "diagrams":
        # 1whuq: flat spec-shaped queries over the docs-kind mirror (diagram
        # chunks are docs-routed); per-set-disjoint corpus directory.
        # Per-format grouping (1wl7v): prefixed ids (`drawio-q01`) group under
        # that format exactly like the specs branch, so each new format's bar
        # reads off the committed JSON; the original unprefixed d01-d09 set
        # groups as `core` and `metrics` keeps its frozen 1whuq meaning.
        queries = _load_spec_queries(HERE / "golden_queries_diagrams.json")
        rows = _chunk_corpus(corpus_dir, _DOCS_KINDS)
        if not queries or not rows:
            parser.error(
                "component benchmark corpus is empty or absent; no production "
                "retrieval score was produced"
            )
        def _fmt(qid: str) -> str:
            head = qid.split("-", 1)[0]
            return head if "-" in qid and not head.startswith("q") else "core"
        by_format = {}
        for q in queries:
            by_format.setdefault(_fmt(q["id"]), []).append(q)
        result["metrics"] = _evaluate(
            by_format.get("core", []), rows, model_name, args.depth)
        if set(by_format) - {"core"}:
            result["metrics_by_format"] = {
                fmt: _evaluate(qs, rows, model_name, args.depth)
                for fmt, qs in sorted(by_format.items())
            }
    else:
        by_format = _load_prose_queries(HERE / "golden_queries_prose.json")
        rows = _chunk_corpus(corpus_dir, _DOCS_KINDS)
        if not by_format or not rows or any(not queries for queries in by_format.values()):
            parser.error(
                "component benchmark corpus is empty or absent; no production "
                "retrieval score was produced"
            )
        result["metrics_by_format"] = {
            fmt: _evaluate(qs, rows, model_name, args.depth)
            for fmt, qs in sorted(by_format.items())
        }
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    summary = result.get("metrics") or {
        fmt: {k: m[k] for k in ("recall_at_5", "mrr")}
        for fmt, m in result["metrics_by_format"].items()
    }
    print(json.dumps({"set": args.set, "label": args.label, "summary": summary},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
