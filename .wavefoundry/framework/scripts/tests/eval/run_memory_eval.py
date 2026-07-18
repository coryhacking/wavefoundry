#!/usr/bin/env python3
"""Hermetic memory-retrieval eval baseline (wave 1sufo / change 1sufm).

Builds a synthetic memory corpus (memory_golden.json) in a throwaway repo, runs
the CURRENT ``wave_memory_search`` / ``wave_memory_brief`` paths against golden
fixtures, and reports recall@k / MRR per category plus explicit pass/fail on the
policy invariants (exact-target, decay, supersession, no-index). It also records
three comparison configurations over the paraphrase cases — the live baseline
(policy-primary + semantic tie-break), lexical-only (no index), and semantic-only
(pure semantic order, the pre-1svuj behavior) — so a future fusion change (the
deferred ``1sufn``) has a recorded baseline to beat.

MEASUREMENT-ONLY: it never changes ranking; it calls the shipped search paths.
Deterministic + hermetic: it builds its own corpus and uses a fixed stub for the
semantic index, so nothing depends on this repo's live (empty) corpus.

Usage:  python run_memory_eval.py [--json]
Exit 0 iff every policy invariant passes.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent.parent  # .wavefoundry/framework/scripts
sys.path.insert(0, str(_SCRIPTS))

DEFAULT_K = 3


def load_fixture() -> dict:
    return json.loads((_HERE / "memory_golden.json").read_text(encoding="utf-8"))


class _StubIndex:
    """Deterministic stand-in for the semantic index: search_docs returns a
    fixed memory-record order, modeling semantic retrieval without embeddings."""

    def __init__(self, order: list[str]) -> None:
        self._order = order

    def search_docs(self, query: str, top_n: int = 0):
        return ([{"path": f"docs/agents/memory/{mid}.md"} for mid in self._order], False)


def build_corpus(root: Path, records: list[dict], mem) -> None:
    for rec in records:
        content = mem.render_memory_record(
            memory_id=rec["memory_id"], kind=rec["kind"], summary=rec["summary"],
            evidence=list(rec["evidence"]), targets=list(rec["targets"]),
            title=rec["memory_id"], confidence=rec.get("confidence", 0.6),
            status=rec.get("status", "active"), supersedes=rec.get("supersedes", ""),
            date=rec.get("created"),
        )
        # A superseded record must also carry `Superseded by:` to parse; the
        # renderer only emits `Supersedes:`, so patch the successor link in.
        if rec.get("superseded_by"):
            content = content.replace(
                "Kind: `", f"Superseded by: `{rec['superseded_by']}`\nKind: `", 1)
        mem.write_memory_record(root, content, rec["memory_id"])


def _recall_at_k(ranked: list[str], expected: list[str], k: int) -> float:
    if not expected:
        return 1.0
    topk = set(ranked[:k])
    return sum(1 for e in expected if e in topk) / len(expected)


def _reciprocal_rank(ranked: list[str], expected: list[str]) -> float:
    for i, mid in enumerate(ranked, start=1):
        if mid in expected:
            return 1.0 / i
    return 0.0


def _search_ids(srv, root: Path, case: dict) -> list[str]:
    index = None if case.get("no_index") else (
        _StubIndex(case["semantic_order"]) if case.get("semantic_order") else None)
    resp = srv.wave_memory_search_response(
        root, query=case.get("query", ""), target=case.get("target", ""),
        index=index, limit=20)
    return [r["memory_id"] for r in resp["data"]["records"]]


def _invariant_pass(case: dict, ranked: list[str]) -> bool:
    kind = case.get("invariant")
    if kind == "top_is":
        return bool(ranked) and ranked[0] == case["invariant_id"]
    if kind == "ranked_above":
        a, b = case["invariant_a"], case["invariant_b"]
        return a in ranked and b in ranked and ranked.index(a) < ranked.index(b)
    if kind == "excludes":
        return case["invariant_id"] not in ranked
    return True


def run(root: Path, k: int = DEFAULT_K) -> dict:
    import server_impl as srv
    mem = srv._memory_mod()
    fixture = load_fixture()
    build_corpus(root, fixture["records"], mem)

    case_results = []
    for case in fixture["cases"]:
        ranked = _search_ids(srv, root, case)
        expected = case.get("expected", [])
        case_results.append({
            "category": case["category"],
            "recall_at_k": _recall_at_k(ranked, expected, k),
            "mrr": _reciprocal_rank(ranked, expected),
            "invariant_pass": _invariant_pass(case, ranked),
            "invariant_note": case.get("invariant_note", ""),
            "ranked": ranked,
        })

    # Comparison configs over the paraphrase (semantic) cases: the live baseline,
    # lexical-only (no index), and semantic-only (pure semantic order = pre-fix).
    comparison = {c: {"recall_at_1": [], "mrr": []}
                  for c in ("baseline", "lexical_only", "semantic_only")}
    for case in fixture["cases"]:
        if case["category"] != "paraphrase":
            continue
        expected = case.get("expected", [])
        baseline = _search_ids(srv, root, case)
        lexical = _search_ids(srv, root, {**case, "no_index": True, "semantic_order": None})
        semantic = list(case["semantic_order"])
        for name, ranked in (("baseline", baseline), ("lexical_only", lexical),
                             ("semantic_only", semantic)):
            comparison[name]["recall_at_1"].append(_recall_at_k(ranked, expected, 1))
            comparison[name]["mrr"].append(_reciprocal_rank(ranked, expected))

    def _avg(xs: list[float]) -> float:
        return round(sum(xs) / len(xs), 4) if xs else 0.0

    comparison = {
        name: {"recall_at_1": _avg(v["recall_at_1"]), "mrr": _avg(v["mrr"])}
        for name, v in comparison.items()
    }

    invariants_total = sum(1 for c in fixture["cases"] if c.get("invariant"))
    invariants_passed = sum(
        1 for r, c in zip(case_results, fixture["cases"])
        if c.get("invariant") and r["invariant_pass"])
    return {
        "k": k,
        "cases": case_results,
        "overall": {
            "recall_at_k": _avg([r["recall_at_k"] for r in case_results]),
            "mrr": _avg([r["mrr"] for r in case_results]),
            "invariants_passed": invariants_passed,
            "invariants_total": invariants_total,
        },
        "comparison": comparison,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        (root / "docs" / "agents").mkdir(parents=True)
        report = run(root)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        ov = report["overall"]
        for r in report["cases"]:
            mark = "PASS" if r["invariant_pass"] else "FAIL"
            print(f"[{mark}] {r['category']:14} recall@{report['k']}={r['recall_at_k']:.2f} "
                  f"mrr={r['mrr']:.2f} :: {r['invariant_note']}")
        print(f"\ninvariants {ov['invariants_passed']}/{ov['invariants_total']}; "
              f"overall recall@{report['k']}={ov['recall_at_k']:.2f} mrr={ov['mrr']:.2f}")
        print("comparison (paraphrase recall@1):",
              ", ".join(f"{n}={v['recall_at_1']:.2f}" for n, v in report["comparison"].items()))
    ov = report["overall"]
    return 0 if ov["invariants_passed"] == ov["invariants_total"] else 1


if __name__ == "__main__":
    sys.exit(main())
