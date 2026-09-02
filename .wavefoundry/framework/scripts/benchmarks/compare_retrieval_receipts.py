#!/usr/bin/env python3
"""Data-level comparison of two retrieval-eval receipts.

Reproduces the standing evaluator's comparison arithmetic over the recorded
numbers in two ``wavefoundry.retrieval-eval/v1`` receipts: holdout aggregate
and per-class quality regressions, the corpus critical floors, the
``max(25%, 3 x jitter)`` warm-p95 threshold, and the ``max(15%, 4 KiB)``
envelope threshold. It imports nothing from ``retrieval_eval`` and touches no
gate: it produces an explicitly labelled *computed* comparison for the case the
signed path cannot serve.

The case that prompted it -- wave 1wpif, where the evaluator bound the sqlite
store file inode inside ``index_identity`` and a compatibility rebuild that
recreated the store made its own ``cross_generation`` kind unavailable -- was
repaired by wave 1wur7 (``1wtpl``): index identity is now compared per
comparison kind. This tool remains for the residual cases where a signed
receipt is structurally unavailable, most commonly a comparison across two
different ``evaluator_identity`` values, which the compatibility rule binds
unconditionally and by design. A computed comparison is disclosure, never a
signed receipt, and it satisfies no gate.

Divergence note (wave 1wur7 delivery review, CODE-DEL-8): every comparison this
tool can make reads ``jitter_ratio`` off the baseline, so it is always the
inherited-jitter case; a baseline with no numeric ``jitter_ratio`` (a single run,
the default since wave 1wuju) is accepted at the 25% floor and labelled
``jitter_source: single_run_floor``, exactly as the signed evaluator does. The
signed evaluator reports a latency shortfall in that
case as an ``operator_review_reasons`` entry carrying ``enforcement:
"operator_review"``, NOT as a violation. This tool still classifies it under
``violations``; read a ``latency_regression`` row here as "the signed gate would
route this to operator review", not as "the signed gate would fail".

Usage::

    python3 -B compare_retrieval_receipts.py --baseline <receipt> --current <receipt> \
        --out <computed.json> [--note "<why the signed path was unavailable>"]

The output records both input content digests and the rules applied, so a
reader can re-run it and verify the arithmetic without trusting prose.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

SCHEMA = "wavefoundry.retrieval-eval-computed-comparison/v1"
TOOLS = ("code_ask", "code_search", "docs_search", "code_lexical")
QUALITY_METRICS = ("recall_at_10", "ndcg_at_10", "agentic_mrr_at_10",
                   "question_type_accuracy", "abstention_accuracy")
CASE_FIELD = {"recall_at_10": "recall_at_10", "ndcg_at_10": "ndcg_at_10",
              "mrr_at_10": "mrr_at_10", "agentic_mrr_at_10": "mrr_at_10",
              "question_type_accuracy": "question_type_correct",
              "abstention_accuracy": "abstention_correct"}
RULES = [
    "quality_regression: holdout aggregate and per-class metric drop below baseline "
    "(recall_at_10, ndcg_at_10, agentic_mrr_at_10, question_type_accuracy, abstention_accuracy)",
    "critical_quality_floor: corpus critical_floors evaluated on the current receipt "
    "(class scope from by_split_and_class.holdout, fixture scope from the case row)",
    "latency_regression: current warm p95 above baseline warm p95 x (1 + max(0.25, 3 x baseline "
    "same-generation jitter))",
    "response_size_regression: current max envelope above baseline + max(15%, 4096 bytes)",
]


def _scope_metric(report: dict, rule: dict) -> float | None:
    tool, metric = str(rule["tool"]), str(rule["metric"])
    if rule["scope"] == "class":
        value = (report["metrics"]["by_tool"][tool]["by_split_and_class"]["holdout"]
                 .get(str(rule["target"]), {}).get(metric))
        return float(value) if isinstance(value, (int, float)) else None
    rows = [r for r in report.get("cases", []) if r.get("applicable") and r.get("split") == "holdout"
            and r.get("fixture_id") == rule["target"] and r.get("tool") == tool]
    if len(rows) != 1:
        return None
    value = rows[0].get(CASE_FIELD.get(metric, metric))
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    return float(value) if isinstance(value, (int, float)) else None


def _bindings(base: dict, cur: dict) -> dict:
    env_keys = ("python", "platform", "machine", "processor", "models", "indexed_model_versions",
                "execution_providers", "reranker_provider", "packages", "offline", "retrieval_toggles")
    bi, ci = base.get("index_identity", {}), cur.get("index_identity", {})
    return {
        "fixture_digest_equal": base.get("fixture_digest") == cur.get("fixture_digest"),
        "evaluator_identity_equal": base.get("evaluator_identity") == cur.get("evaluator_identity"),
        "environment_equal": {k: base["environment"].get(k) == cur["environment"].get(k) for k in env_keys},
        "index_identity_differences": {k: [bi.get(k), ci.get(k)] for k in set(bi) | set(ci) if bi.get(k) != ci.get(k)},
        "generation": {"baseline": base["generation"]["start"], "current": cur["generation"]["start"],
                       "baseline_attempt": base["generation"]["start_attempt_id"],
                       "current_attempt": cur["generation"]["start_attempt_id"]},
        "production": {"baseline": base["production_identity"]["digest"],
                       "current": cur["production_identity"]["digest"],
                       "baseline_versions": base["production_identity"].get("versions"),
                       "current_versions": cur["production_identity"].get("versions")},
    }


def compare(base: dict, cur: dict) -> tuple[list[dict], list[dict], dict, dict]:
    violations: list[dict] = []
    for tool in TOOLS:
        c = cur["metrics"]["by_tool"][tool]["by_split"]["holdout"]
        b = base["metrics"]["by_tool"][tool]["by_split"]["holdout"]
        for name in QUALITY_METRICS:
            cv, bv = c.get(name), b.get(name)
            if cv is not None and bv is not None and cv + 1e-12 < bv:
                violations.append({"kind": "quality_regression", "tool": tool, "metric": name,
                                   "scope": "aggregate", "split": "holdout", "baseline": bv, "current": cv})
        cc = cur["metrics"]["by_tool"][tool]["by_split_and_class"]["holdout"]
        bc = base["metrics"]["by_tool"][tool]["by_split_and_class"]["holdout"]
        if set(cc) != set(bc):
            raise SystemExit(f"holdout classes differ for {tool}: {sorted(set(cc) ^ set(bc))}")
        for case_class in sorted(cc):
            for name in QUALITY_METRICS:
                cv, bv = cc[case_class].get(name), bc[case_class].get(name)
                if cv is not None and bv is not None and cv + 1e-12 < bv:
                    violations.append({"kind": "quality_regression", "tool": tool, "metric": name,
                                       "scope": "class", "class": case_class, "split": "holdout",
                                       "baseline": bv, "current": cv})
    floors: list[dict] = []
    for rule in cur.get("quality_gate", {}).get("critical_floors", []):
        value = _scope_metric(cur, rule)
        floors.append({**rule, "current": value})
        if value is None:
            violations.append({"kind": "critical_quality_metric_unavailable", **rule})
        elif value + 1e-12 < float(rule["floor"]):
            violations.append({"kind": "critical_quality_floor", **rule, "current": value})
    performance: dict = {}
    for tool in TOOLS:
        cp = cur["performance"]["tools"][tool]
        bp = base["performance"]["tools"][tool]
        cur_p95, base_p95, jitter = cp.get("warm_p95_ms"), bp.get("warm_p95_ms"), bp.get("jitter_ratio")
        if cur_p95 is None or base_p95 is None:
            performance[tool] = {"skipped": "baseline or current lacks warm p95"}
            continue
        # Wave 1wuju: mirror the signed evaluator's single-run branch. A baseline
        # with no numeric pair-derived jitter is accepted at the explicit 25% floor.
        if isinstance(jitter, bool) or not isinstance(jitter, (int, float)):
            jitter, jitter_source, allowed = None, "single_run_floor", 0.25
        else:
            jitter_source, allowed = "baseline_same_generation_pair", max(0.25, 3.0 * float(jitter))
        threshold = float(base_p95) * (1.0 + allowed)
        cur_bytes, base_bytes = int(cp.get("max_response_bytes") or 0), int(bp.get("max_response_bytes") or 0)
        byte_threshold = base_bytes + max(base_bytes * 0.15, 4096.0)
        performance[tool] = {"baseline_warm_p95_ms": base_p95, "current_warm_p95_ms": cur_p95,
                             "baseline_jitter_ratio": jitter, "jitter_source": jitter_source,
                             "permitted_relative_regression": round(allowed, 8),
                             "warm_p95_threshold_ms": round(threshold, 6),
                             "baseline_max_response_bytes": base_bytes, "current_max_response_bytes": cur_bytes,
                             "response_bytes_threshold": math.floor(byte_threshold)}
        if float(cur_p95) > threshold:
            violations.append({"kind": "latency_regression", "tool": tool, "baseline_ms": base_p95,
                               "current_ms": cur_p95, "threshold_ms": round(threshold, 6)})
        if cur_bytes > byte_threshold:
            violations.append({"kind": "response_size_regression", "tool": tool, "baseline_bytes": base_bytes,
                               "current_bytes": cur_bytes, "threshold_bytes": math.floor(byte_threshold)})
    deltas: dict = {}
    for tool in TOOLS:
        deltas[tool] = {}
        for split in ("holdout", "calibration"):
            b = base["metrics"]["by_tool"][tool]["by_split"][split]
            c = cur["metrics"]["by_tool"][tool]["by_split"][split]
            deltas[tool][split] = {m: [b.get(m), c.get(m)] for m in QUALITY_METRICS
                                   if b.get(m) is not None or c.get(m) is not None}
    return violations, floors, performance, deltas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--current", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--note", default="", help="why the signed evaluator comparison was unavailable")
    args = parser.parse_args(argv)
    base = json.loads(args.baseline.read_text(encoding="utf-8"))
    cur = json.loads(args.current.read_text(encoding="utf-8"))
    violations, floors, performance, deltas = compare(base, cur)
    report = {
        "schema": SCHEMA,
        "method": {
            "description": "Data-level reproduction of retrieval_eval.apply_baseline_comparison arithmetic over the "
                           "two receipts' recorded numbers; no evaluator code imported or patched.",
            "why_not_a_signed_receipt": args.note,
            "rules": RULES,
            "baseline_file": args.baseline.as_posix(), "current_file": args.current.as_posix(),
            "baseline_run_id": base.get("run_id"), "current_run_id": cur.get("run_id"),
            "baseline_content_sha256": hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
            "current_content_sha256": hashlib.sha256(args.current.read_bytes()).hexdigest(),
            "computed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "script": ".wavefoundry/framework/scripts/benchmarks/compare_retrieval_receipts.py",
        },
        "bindings": _bindings(base, cur),
        "comparison_kind": "cross_generation (computed)",
        "violations": violations,
        "critical_floors": floors,
        "performance": performance,
        "metric_deltas": deltas,
        "verdict": "pass" if not violations else "fail",
    }
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": args.out.as_posix(), "verdict": report["verdict"],
                      "violations": len(violations)}))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
