#!/usr/bin/env python3
"""Bounded disposable-store lexical ranking evaluation (wave `1wpih` / `1wpid`).

This is a COMPONENT evaluator, not the standing retrieval gate.  It builds a
throwaway index-state store, populates it through the canonical producer
(``index_state_store.apply_chunk_deltas``) rather than by writing FTS rows by
hand, and scores the lexical layer directly.  Two things it must be able to
detect, because they are the measured weaknesses the change exists to address:

1. **Tail-identifier truncation.**  ``_fts_match_expression`` keeps the first
   ``FTS_QUERY_MAX_TOKENS`` whitespace tokens, so a distinctive identifier past
   that position is discarded before the query reaches FTS5.
2. **Cross-table raw-BM25 comparison.**  ``docs`` and ``code`` are separately
   normalised FTS tables; merging their raw scores means unrelated growth in one
   table can reverse the order of unchanged, equally relevant rows.

Evidence discipline (wave `1wscp` requirement 2 applies here too): the corpus is
split into a ``calibration`` artifact that may select a mechanism and a
``regression_only`` artifact that may not.  ``leak_scan`` fails when an exact
regression query appears in calibration data or in implementation tests, which
is what stops a mechanism from being tuned against the cases later reported as
its validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import index_state_store as iss  # noqa: E402


FIXTURE_SCHEMA = "wavefoundry.lexical-ranking-fixtures/v1"
REPORT_SCHEMA = "wavefoundry.lexical-ranking-eval/v1"

TABLES = ("docs", "code")
EVIDENCE_ROLES = ("calibration", "regression_only", "independent_holdout")

# Requirement 8: fixed corpus and runtime bounds.  Small on purpose -- this is a
# component probe, and an unbounded corpus would turn it into a second index.
MAX_ROWS_PER_TABLE = 256
RUNNER_BUDGET_SECONDS = 30.0
# Requirement 9: one untimed warm-up plus exactly three measured repetitions.
WARMUP_REPETITIONS = 1
MEASURED_REPETITIONS = 3
HOSTILE_P95_CEILING_MS = 1_000.0
RECALL_K = 10


class LexicalEvaluationInvalid(Exception):
    """The lexical evaluation could not produce a trustworthy result."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise LexicalEvaluationInvalid(code, message)


def _stable_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def digest(payload: Any) -> str:
    return hashlib.sha256(_stable_json_bytes(payload)).hexdigest()


# ---------------------------------------------------------------------------
# Corpus
# ---------------------------------------------------------------------------

def load_corpus(path: Path) -> dict[str, Any]:
    """Load and validate one lexical corpus artifact."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LexicalEvaluationInvalid(
            "missing_corpus", f"lexical corpus not found: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LexicalEvaluationInvalid(
            "invalid_corpus", f"cannot read lexical corpus: {exc}") from exc
    _require(isinstance(payload, dict)
             and set(payload) == {"schema", "evidence_role", "rows", "cases"},
             "invalid_corpus", "lexical corpus has missing or unknown top-level fields")
    _require(payload.get("schema") == FIXTURE_SCHEMA, "invalid_corpus",
             f"lexical corpus schema must be {FIXTURE_SCHEMA}")
    role = payload.get("evidence_role")
    _require(role in EVIDENCE_ROLES, "invalid_corpus",
             f"evidence_role must be one of {list(EVIDENCE_ROLES)}")

    rows = payload.get("rows")
    _require(isinstance(rows, dict) and set(rows) <= set(TABLES) and rows,
             "invalid_corpus", "rows must map table names to row lists")
    normalized_rows: dict[str, list[dict[str, Any]]] = {}
    for table, table_rows in rows.items():
        _require(isinstance(table_rows, list) and table_rows, "invalid_corpus",
                 f"rows[{table}] must be a non-empty list")
        _require(len(table_rows) <= MAX_ROWS_PER_TABLE, "corpus_cap_exceeded",
                 f"rows[{table}] has {len(table_rows)} rows; maximum is {MAX_ROWS_PER_TABLE}")
        seen_ids: set[str] = set()
        out: list[dict[str, Any]] = []
        for pos, raw in enumerate(table_rows):
            _require(isinstance(raw, dict) and set(raw) == {"id", "path", "text"},
                     "invalid_corpus", f"rows[{table}][{pos}] needs exactly id/path/text")
            for field in ("id", "path", "text"):
                _require(isinstance(raw[field], str) and raw[field].strip(),
                         "invalid_corpus",
                         f"rows[{table}][{pos}].{field} must be a non-empty string")
            _require(raw["id"] not in seen_ids, "invalid_corpus",
                     f"duplicate row id in {table}: {raw['id']}")
            seen_ids.add(raw["id"])
            out.append(dict(raw))
        normalized_rows[table] = out

    cases = payload.get("cases")
    _require(isinstance(cases, list) and cases, "invalid_corpus",
             "cases must be a non-empty list")
    normalized_cases: list[dict[str, Any]] = []
    case_ids: set[str] = set()
    for pos, raw in enumerate(cases):
        _require(isinstance(raw, dict)
                 and set(raw) == {"id", "query", "table", "relevant_ids", "rationale"},
                 "invalid_corpus",
                 f"cases[{pos}] needs exactly id/query/table/relevant_ids/rationale")
        case_id = str(raw["id"]).strip()
        _require(case_id and case_id not in case_ids, "invalid_corpus",
                 f"duplicate or empty case id: {case_id!r}")
        case_ids.add(case_id)
        _require(isinstance(raw["query"], str) and raw["query"].strip(),
                 "invalid_corpus", f"{case_id}: query must be non-empty")
        _require(raw["table"] in TABLES + ("both",), "invalid_corpus",
                 f"{case_id}: table must be a real table or 'both'")
        relevant = raw["relevant_ids"]
        _require(isinstance(relevant, list) and relevant
                 and all(isinstance(v, str) and v for v in relevant),
                 "invalid_corpus", f"{case_id}: relevant_ids must be a non-empty string list")
        known = {r["id"] for table_rows in normalized_rows.values() for r in table_rows}
        unknown = sorted(set(relevant) - known)
        _require(not unknown, "invalid_corpus",
                 f"{case_id}: relevant_ids name rows absent from the corpus: {unknown}")
        _require(isinstance(raw["rationale"], str) and raw["rationale"].strip(),
                 "invalid_corpus", f"{case_id}: rationale must be non-empty")
        normalized_cases.append(dict(raw, id=case_id))

    return {"schema": FIXTURE_SCHEMA, "evidence_role": role,
            "rows": normalized_rows, "cases": normalized_cases}


def leak_scan(regression: Mapping[str, Any], calibration: Mapping[str, Any],
              search_paths: Iterable[Path] = ()) -> list[dict[str, str]]:
    """Exact regression queries that leaked into selectable material.

    Requirement 8.  A regression query that appears verbatim in the calibration
    corpus, or in an implementation test or prompt, is no longer held out: a
    mechanism can be tuned until that exact string passes.  Returns the leaks
    rather than raising, so a caller can report every one at once.
    """
    regression_queries = {str(c["query"]).strip() for c in regression.get("cases", [])}
    leaks: list[dict[str, str]] = []
    for case in calibration.get("cases", []):
        query = str(case.get("query", "")).strip()
        if query in regression_queries:
            leaks.append({"query": query, "where": "calibration_corpus",
                          "detail": f"calibration case {case.get('id')}"})
    for path in search_paths:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeError):
            continue
        for query in sorted(regression_queries):
            if query in text:
                leaks.append({"query": query, "where": "implementation_source",
                              "detail": str(path)})
    return leaks


# ---------------------------------------------------------------------------
# Disposable store
# ---------------------------------------------------------------------------

def build_disposable_store(index_dir: Path, rows: Mapping[str, Sequence[Mapping[str, Any]]],
                           *, kind: str = "code") -> None:
    """Populate a throwaway store through the canonical producer.

    Deliberately routes through ``apply_chunk_deltas`` rather than writing FTS
    rows directly: a hand-built fixture would not exercise the same registry and
    FTS reconciliation the product uses, and a probe that disagrees with the
    real writer proves nothing about the real reader.
    """
    index_dir.mkdir(parents=True, exist_ok=True)
    for table, table_rows in rows.items():
        add_rows = [{
            "id": row["id"], "path": row["path"], "kind": kind,
            "lines": [1, 1 + row["text"].count("\n")], "text": row["text"],
            "chunk_hash": hashlib.sha256(row["text"].encode("utf-8")).hexdigest()[:16],
        } for row in table_rows]
        iss.apply_chunk_deltas(index_dir, table, add_rows=add_rows)


def _search(index_dir: Path, table: str, query: str, limit: int) -> list[dict[str, Any]]:
    """One lexical read, matching the product's cross-table merge semantics.

    ``table="both"`` reproduces ``WaveIndex._lexical_candidates``: query each
    table separately, then sort the union by RAW bm25.  That merge is the
    behaviour under measurement, so the probe must not quietly improve on it.
    """
    if table in TABLES:
        return iss.fts_search(index_dir, table, query, limit=limit)
    merged: list[dict[str, Any]] = []
    for name in TABLES:
        merged.extend(iss.fts_search(index_dir, name, query, limit=limit))
    merged.sort(key=lambda row: row.get("bm25", 0.0))
    return merged[:limit]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _dcg(gains: Sequence[float]) -> float:
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def score_case(returned_ids: Sequence[str], relevant_ids: Sequence[str],
               *, k: int = RECALL_K) -> dict[str, float]:
    """Recall@k, MRR@k and nDCG@k for one case."""
    relevant = list(dict.fromkeys(relevant_ids))
    top = list(returned_ids[:k])
    hits = [rid for rid in relevant if rid in top]
    recall = len(hits) / len(relevant) if relevant else 0.0
    mrr = 0.0
    for rank, chunk_id in enumerate(top, start=1):
        if chunk_id in relevant:
            mrr = 1.0 / rank
            break
    gains = [1.0 if chunk_id in relevant else 0.0 for chunk_id in top]
    ideal = _dcg([1.0] * min(len(relevant), k))
    ndcg = (_dcg(gains) / ideal) if ideal > 0 else 0.0
    return {"recall_at_10": round(recall, 8), "mrr_at_10": round(mrr, 8),
            "ndcg_at_10": round(ndcg, 8)}


def _nearest_rank_p95(samples: Sequence[float]) -> float:
    ordered = sorted(samples)
    if not ordered:
        return 0.0
    index = max(1, math.ceil(0.95 * len(ordered))) - 1
    return ordered[index]


def measure_case(index_dir: Path, case: Mapping[str, Any],
                 *, k: int = RECALL_K) -> dict[str, Any]:
    """Score one case and time it under the fixed repetition protocol."""
    query, table = str(case["query"]), str(case["table"])
    for _ in range(WARMUP_REPETITIONS):
        _search(index_dir, table, query, k)
    samples: list[float] = []
    returned: list[str] = []
    for _ in range(MEASURED_REPETITIONS):
        start = time.perf_counter()
        results = _search(index_dir, table, query, k)
        samples.append((time.perf_counter() - start) * 1000.0)
        returned = [str(row.get("id", "")) for row in results]
    metrics = score_case(returned, case["relevant_ids"], k=k)
    return {"case_id": case["id"], "table": table, "query": query,
            "returned_ids": returned, "warm_p95_ms": round(_nearest_rank_p95(samples), 4),
            **metrics}


# ---------------------------------------------------------------------------
# Probes
# ---------------------------------------------------------------------------

def tail_token_probe(index_dir: Path, *, identifier: str,
                     lead_terms: int = iss.FTS_QUERY_MAX_TOKENS) -> dict[str, Any]:
    """Does a distinctive identifier past the token cap survive query construction?

    Builds a query of ``lead_terms`` ordinary words followed by ``identifier``.
    Reads the constructed MATCH expression directly rather than inferring from
    results, so the probe reports the CAUSE, not just a zero.
    """
    filler = " ".join(f"term{i}" for i in range(lead_terms))
    query = f"{filler} {identifier}"
    expression = iss._fts_match_expression(query)
    return {
        "query": query,
        "identifier": identifier,
        "identifier_survived": f'"{identifier}"' in expression,
        "match_terms": expression.count(" OR ") + 1 if expression else 0,
        "within_cap": (expression.count(" OR ") + 1 if expression else 0)
        <= iss.FTS_QUERY_MAX_TOKENS,
    }


def corpus_growth_probe(index_dir_factory: Callable[[str], Path],
                        rows: Mapping[str, Sequence[Mapping[str, Any]]],
                        case: Mapping[str, Any], *, filler_rows: int,
                        grow_table: str = "docs") -> dict[str, Any]:
    """Does unrelated growth in ONE table reverse the fused order of unchanged rows?

    Builds the same corpus twice, once with ``filler_rows`` extra unrelated rows
    in ``grow_table``.  Both stores answer the same query over the same relevant
    rows, so any order change is attributable to the growth alone.
    """
    base_dir = index_dir_factory("base")
    build_disposable_store(base_dir, rows)
    before = [str(r.get("id", "")) for r in _search(
        base_dir, str(case["table"]), str(case["query"]), RECALL_K)]

    grown = {table: list(table_rows) for table, table_rows in rows.items()}
    grown.setdefault(grow_table, [])
    grown[grow_table] = list(grown[grow_table]) + [{
        "id": f"filler-{i}", "path": f"filler/{i}.md",
        "text": f"unrelated filler document {i} with padding words",
    } for i in range(filler_rows)]
    grown_dir = index_dir_factory("grown")
    build_disposable_store(grown_dir, grown)
    after = [str(r.get("id", "")) for r in _search(
        grown_dir, str(case["table"]), str(case["query"]), RECALL_K)]

    tracked = {str(i) for i in case["relevant_ids"]}
    before_tracked = [i for i in before if i in tracked]
    after_tracked = [i for i in after if i in tracked]
    return {
        "grow_table": grow_table,
        "filler_rows": filler_rows,
        "order_before": before_tracked,
        "order_after": after_tracked,
        "order_reversed": (before_tracked != after_tracked
                           and sorted(before_tracked) == sorted(after_tracked)),
    }


__all__ = [
    "FIXTURE_SCHEMA", "REPORT_SCHEMA", "TABLES", "EVIDENCE_ROLES",
    "MAX_ROWS_PER_TABLE", "RUNNER_BUDGET_SECONDS", "MEASURED_REPETITIONS",
    "HOSTILE_P95_CEILING_MS", "RECALL_K",
    "LexicalEvaluationInvalid", "digest", "load_corpus", "leak_scan",
    "build_disposable_store", "score_case", "measure_case",
    "tail_token_probe", "corpus_growth_probe",
]


def _mechanism_identity() -> dict[str, Any]:
    """Bind the report to the production mechanism that produced it.

    Hashes the two functions under measurement rather than the whole module, so
    a report's identity moves when the RANKING changes and not when an unrelated
    edit lands elsewhere in the file.
    """
    import inspect
    parts = {}
    for name in ("_fts_match_expression", "_distinctive_term_score", "fuse_lexical_tables"):
        fn = getattr(iss, name, None)
        parts[name] = (hashlib.sha256(inspect.getsource(fn).encode("utf-8")).hexdigest()
                       if fn is not None else None)
    return {
        "module": "index_state_store",
        "fts_query_max_tokens": getattr(iss, "FTS_QUERY_MAX_TOKENS", None),
        "lexical_fusion_k": getattr(iss, "LEXICAL_FUSION_K", None),
        "function_digests": parts,
    }


def run_evaluation(corpus: Mapping[str, Any], *, label: str) -> dict[str, Any]:
    """Score one frozen corpus end to end and return a bindable report."""
    import tempfile

    started = time.perf_counter()
    cases: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        index_dir = root / "idx"
        build_disposable_store(index_dir, corpus["rows"])
        for case in corpus["cases"]:
            cases.append(measure_case(index_dir, case))

        counter = [0]

        def factory(tag: str) -> Path:
            counter[0] += 1
            return root / f"probe-{tag}-{counter[0]}"

        growth = [
            corpus_growth_probe(factory, corpus["rows"], case, filler_rows=32)
            for case in corpus["cases"] if case["table"] == "both"
        ]
    elapsed = time.perf_counter() - started
    aggregate = {
        metric: (sum(c[metric] for c in cases) / len(cases) if cases else 0.0)
        for metric in ("recall_at_10", "mrr_at_10", "ndcg_at_10")
    }
    return {
        "schema": REPORT_SCHEMA,
        "label": label,
        "evidence_role": corpus["evidence_role"],
        # Requirement 6: the report states WHO may use it for what.  The
        # authorship fields are constants here because this corpus is authored
        # by the implementing party; only a separately supplied, unconsulted
        # artifact could claim otherwise.
        "evidence_authority": {
            "evidence_role": corpus["evidence_role"],
            "authorship_class": "qa_local",
            "consultation_status": (
                "consulted" if corpus["evidence_role"] == "calibration" else "unconsulted"),
            "mechanism_exposure": (
                "exposed" if corpus["evidence_role"] == "calibration" else "unexposed"),
            "supports_improvement_claim": False,
            "why": ("QA-authored local evidence. Non-regression only: an improvement "
                    "claim requires a separately supplied, mechanism-independent, "
                    "unconsulted artifact, which this is not."),
        },
        "corpus_digest": digest(corpus),
        "mechanism_identity": _mechanism_identity(),
        "environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "fts5_available": bool(iss.fts5_available()),
        },
        "protocol": {
            "warmups": WARMUP_REPETITIONS,
            "measured_repetitions": MEASURED_REPETITIONS,
            "p95_method": "nearest_rank",
            "max_rows_per_table": MAX_ROWS_PER_TABLE,
            "runner_budget_seconds": RUNNER_BUDGET_SECONDS,
        },
        "elapsed_seconds": round(elapsed, 4),
        "within_runtime_budget": elapsed < RUNNER_BUDGET_SECONDS,
        "aggregate": {k: round(v, 8) for k, v in aggregate.items()},
        "cases": cases,
        "corpus_growth_probes": growth,
    }


def write_report(report: Mapping[str, Any], destination: Path) -> str:
    """Write one report and return its content digest. Never overwrites."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(report)
    payload["content_sha256"] = digest(
        {k: v for k, v in report.items() if k != "content_sha256"})
    if destination.exists():
        raise LexicalEvaluationInvalid(
            "report_destination_exists",
            f"report destination already exists and is never overwritten: {destination}")
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload["content_sha256"]


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--regression", type=Path, required=True)
    parser.add_argument("--out", type=Path, help="report destination")
    parser.add_argument("--label", default="unlabelled",
                        help="what this run measures, e.g. 'baseline' or 'post'")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    calibration = load_corpus(args.calibration)
    regression = load_corpus(args.regression)
    leaks = leak_scan(regression, calibration)
    if leaks:
        print(json.dumps({"status": "leak", "leaks": leaks}, indent=2))
        return 1
    if args.out is None:
        print(json.dumps({
            "status": "ok",
            "calibration_digest": digest(calibration),
            "regression_digest": digest(regression),
        }, indent=2))
        return 0
    report = {
        "calibration": run_evaluation(calibration, label=f"{args.label}:calibration"),
        "regression": run_evaluation(regression, label=f"{args.label}:regression"),
        "leak_scan": {"clean": True, "leaks": []},
    }
    content = write_report(report, args.out)
    print(json.dumps({"status": "ok", "out": str(args.out),
                      "content_sha256": content,
                      "calibration_aggregate": report["calibration"]["aggregate"],
                      "regression_aggregate": report["regression"]["aggregate"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
