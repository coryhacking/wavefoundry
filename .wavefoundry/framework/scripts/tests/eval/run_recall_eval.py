#!/usr/bin/env python3
"""Wave 1p4hi AC-10 / 1p4mf AC-6 known-answer recall eval (committed gate artifact).

Runs code_ask (agent mode) against the LOCAL project index for the committed
known-answer set (ac10_known_answers.json) and reports per-query answer rank.

- constant_value_queries validate 1p4mf's constant chunks — a constant's VALUE is now
  retrievable. With 1p4lr not yet implemented, these ranks ARE the "breadcrumb-chunk-alone"
  measurement (does the breadcrumb prefix alone lift retrieval, decoupling from 1p4lr?).
- symbol_recall_queries are the dilution baseline — their answers must not regress beyond
  baseline_rank + dilution_tolerance when constant chunks are added.

Usage:  python run_recall_eval.py [--root <project_root>] [--json]
Exit 0 iff every query passes the bar (constant rank <= constant_rank_max; symbol rank <=
baseline+tolerance, or symbol_rank_max when no baseline). Requires a built CHUNKER_VERSION=26
index.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent.parent  # .wavefoundry/framework/scripts
sys.path.insert(0, str(_SCRIPTS))


def _answer_rank(citations: list, answer_any: list) -> int | None:
    """final_rank of the first citation whose path or excerpt contains any answer string."""
    needles = [a.lower() for a in answer_any]
    for c in citations:
        blob = (str(c.get("path", "")) + " " + str(c.get("excerpt") or "")).lower()
        if any(n in blob for n in needles):
            return c.get("final_rank")
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None, help="project root (default: cwd)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve() if args.root else Path.cwd()
    fixture = json.loads((_HERE / "ac10_known_answers.json").read_text())
    bar = fixture["pass_bar"]

    import server_impl as srv
    idx = srv.build_handler(root).index

    results = []
    for section, key in (("constant", "constant_value_queries"), ("symbol", "symbol_recall_queries")):
        for q in fixture[key]:
            cits = srv.code_ask_response(idx, root, q["query"], rerank="agent")["data"]["citations"]
            rank = _answer_rank(cits, q["answer_any"])
            if section == "constant":
                tol = bar["constant_rank_max"]
            elif q.get("baseline_rank") is not None:
                tol = q["baseline_rank"] + bar["dilution_tolerance"]
            else:
                tol = bar["symbol_rank_max"]
            ok = rank is not None and rank <= tol
            results.append({"section": section, "query": q["query"], "rank": rank,
                            "baseline": q.get("baseline_rank"), "bar": tol, "pass": ok})

    passed = sum(1 for r in results if r["pass"])
    total = len(results)
    if args.json:
        print(json.dumps({"results": results, "passed": passed, "total": total}, indent=2))
    else:
        for r in results:
            mark = "PASS" if r["pass"] else "FAIL"
            base = "" if r["baseline"] is None else f", v25={r['baseline']}"
            print(f"[{mark}] {r['section']:8} rank={str(r['rank']):>4} (bar<={r['bar']}{base}) :: {r['query'][:52]}")
        print(f"\n{passed}/{total} passed."
              + ("" if passed == total else "  — GATE FAIL"))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
