#!/usr/bin/env python3
"""Memory-retrieval policy and candidate evaluation.

Builds a synthetic memory corpus (memory_golden.json) in a throwaway repo, runs
the current ``memory_search`` path against golden fixtures, and compares the
shipped semantic tie-break with an evaluation-only lexical+semantic RRF
candidate. The optional curated pass freezes a bounded sample of the live
corpus before scoring and emits aggregate metrics, counts, and a fingerprint
only — never memory bodies, summaries, or record ids.

MEASUREMENT-ONLY: the RRF candidate is not wired into product code. Deterministic
and hermetic by default; ``--curated-root`` is an explicit operator-run
observational pass.

This module ships with the framework (wave 1tgws) so the curated pass can
measure ANY target repository's memory corpus, through ``wf_memory_eval`` or
this CLI. Two distinct surfaces live here:

* ``run_curated(root)`` — the shipped cross-project measurement. Needs only a
  target repo; returns aggregate-only evidence.
* ``run(root)`` — the hermetic invariant pass. Needs the golden fixture, which
  is test scaffolding and is NOT packaged; it is exercised by
  ``tests/test_memory_eval.py``. Calling it without the fixture raises a clear
  ``FileNotFoundError`` rather than degrading silently.

Usage:  python memory_eval.py [--json] [--curated-root PATH]
Exit 0 iff every policy invariant passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent  # .wavefoundry/framework/scripts
sys.path.insert(0, str(_SCRIPTS))
# The golden fixture is test scaffolding: build_pack excludes `scripts/tests`,
# so it is absent in a target repository. Only the hermetic `run()` needs it.
_FIXTURE_PATH = _SCRIPTS / "tests" / "eval" / "memory_golden.json"

DEFAULT_K = 3
CURATED_SAMPLE_CAP = 12
RRF_K = 60
_TOKEN_RE = re.compile(r"[a-z0-9_]+")


def load_fixture() -> dict:
    """Load the hermetic golden corpus (test scaffolding, not packaged)."""
    if not _FIXTURE_PATH.is_file():
        raise FileNotFoundError(
            f"hermetic memory-eval fixture not found at {_FIXTURE_PATH}; "
            "the golden corpus is test scaffolding and is not packaged. Use "
            "run_curated(root) / wf_memory_eval for a shipped measurement."
        )
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


class _StubIndex:
    """Deterministic stand-in for the semantic index: search_docs returns a
    fixed memory-record order, modeling semantic retrieval without embeddings."""

    def __init__(self, order: list[str]) -> None:
        self._order = order

    def search_docs(self, query: str, top_n: int = 0):
        return ([{"path": f"docs/agents/memory/{mid}.md"} for mid in self._order], False)


def _seed_commit_history(srv, root: Path, histories: dict[str, list[int]]) -> None:
    """Write synthetic commit history into a THROWAWAY repo's own store.

    The hermetic pass needs the shipped search path to observe deterministic
    per-target histories. It seeds them through the canonical writer so the
    fixture corpus is real rather than patched — never by rebinding
    ``index_state_store.file_commit_times``, which is process-global and
    therefore unsafe in the long-lived MCP server (wave 1tis8).

    Only ever called on a temporary corpus built by ``build_corpus``; the
    curated pass reads the live store and never writes to it.
    """
    if not histories:
        return
    index_store = srv._load_script("index_state_store")
    store = index_store.IndexStateStore(root / ".wavefoundry" / "index")
    try:
        store.apply_freshness(
            rows={
                path: {"commit_count": len(times), "source": "memory-eval-fixture"}
                for path, times in histories.items()
            },
            commits=[
                (path, f"fixture{index:040x}", int(ts))
                for path, times in histories.items()
                for index, ts in enumerate(times)
            ],
            fingerprint="memory-eval-fixture",
            paths_hash="memory-eval-fixture",
        )
    finally:
        store.close()


def build_corpus(root: Path, records: list[dict], mem) -> None:
    archives: list[str] = []
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
        if rec.get("archive"):
            archives.append(rec["memory_id"])
    for memory_id in archives:
        mem.archive_memory_record(
            root, memory_id, reason="hermetic retrieval evaluation fixture"
        )


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


def _search_result(srv, root: Path, case: dict) -> dict[str, Any]:
    index = None if case.get("no_index") else (
        _StubIndex(case["semantic_order"]) if case.get("semantic_order") else None)
    return srv.memory_search_response(
        root, query=case.get("query", ""), target=case.get("target", ""),
        include_history=bool(case.get("include_history")),
        index=index, limit=20)


def _search_ids(srv, root: Path, case: dict) -> list[str]:
    response = _search_result(srv, root, case)
    return [r["memory_id"] for r in response["data"]["records"]]


def _invariant_pass(case: dict, response: dict[str, Any]) -> bool:
    data = response["data"]
    records = data["records"]
    ranked = [record["memory_id"] for record in records]
    kind = case.get("invariant")
    if kind == "top_is":
        return bool(ranked) and ranked[0] == case["invariant_id"]
    if kind == "ranked_above":
        a, b = case["invariant_a"], case["invariant_b"]
        return a in ranked and b in ranked and ranked.index(a) < ranked.index(b)
    if kind == "excludes":
        return case["invariant_id"] not in ranked
    if kind == "data_equals":
        return data.get(case["invariant_field"]) == case["invariant_value"]
    if kind == "record_truthy":
        return any(
            record["memory_id"] == case["invariant_id"]
            and bool(record.get(case["invariant_field"]))
            for record in records
        )
    return True


def _ranking_invariant_pass(
    case: dict, ranked: list[str], shipped_invariant_pass: bool
) -> bool:
    """Evaluate candidate ordering invariants; structural invariants are shared."""
    kind = case.get("invariant")
    if kind == "top_is":
        return bool(ranked) and ranked[0] == case["invariant_id"]
    if kind == "ranked_above":
        a, b = case["invariant_a"], case["invariant_b"]
        return a in ranked and b in ranked and ranked.index(a) < ranked.index(b)
    if kind == "excludes":
        return case["invariant_id"] not in ranked
    return shipped_invariant_pass


def _tokens(value: str) -> list[str]:
    return _TOKEN_RE.findall(str(value or "").lower())


def _record_text(record: dict[str, Any]) -> str:
    return " ".join([
        str(record.get("summary") or ""),
        str(record.get("title") or ""),
        " ".join(record.get("evidence_refs") or []),
        " ".join(record.get("target_refs") or []),
        " ".join(record.get("keywords") or []),
    ])


def lexical_bm25_order(
    records: list[dict[str, Any]], query: str
) -> list[str]:
    """Evaluation-only deterministic BM25 over already-loaded records."""
    query_terms = _tokens(query)
    if not query_terms or not records:
        return []
    tokenized = [_tokens(_record_text(record)) for record in records]
    avg_len = sum(len(tokens) for tokens in tokenized) / max(len(tokenized), 1)
    document_frequency = Counter(
        token for tokens in tokenized for token in set(tokens)
    )
    scored: list[tuple[float, str]] = []
    for record, tokens in zip(records, tokenized):
        frequencies = Counter(tokens)
        score = 0.0
        for term in query_terms:
            frequency = frequencies.get(term, 0)
            if not frequency:
                continue
            documents = len(records)
            frequency_docs = document_frequency[term]
            inverse = math.log(1.0 + (documents - frequency_docs + 0.5)
                               / (frequency_docs + 0.5))
            denominator = frequency + 1.2 * (
                1.0 - 0.75 + 0.75 * len(tokens) / max(avg_len, 1.0)
            )
            score += inverse * frequency * 2.2 / denominator
        if score > 0:
            scored.append((score, record["memory_id"]))
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [memory_id for _score, memory_id in scored]


def reciprocal_rank_fusion(
    rankings: list[list[str]], *, rrf_k: int = RRF_K
) -> list[str]:
    """Evaluation-only deterministic RRF over positive-match streams."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, memory_id in enumerate(ranking, start=1):
            scores[memory_id] = scores.get(memory_id, 0.0) + 1.0 / (rrf_k + rank)
    return [
        memory_id
        for memory_id, _score in sorted(
            scores.items(), key=lambda pair: (-pair[1], pair[0])
        )
    ]


def _case_records(srv, root: Path, case: dict) -> list[dict[str, Any]]:
    mem = srv._memory_mod()
    statuses = None if case.get("include_history") else list(mem.DEFAULT_SURFACED_STATUSES)
    records = mem.load_memory_records(root, statuses=statuses)
    if not case.get("include_history") and (
        case.get("query") or case.get("target")
    ):
        records.extend(mem.load_memory_pointers(root))
    if case.get("target"):
        records = [
            record for record in records
            if mem.match_targets(record, path=case["target"])
        ]
    return records


def _policy_order(
    srv,
    root: Path,
    records: list[dict[str, Any]],
    relevance_order: list[str],
    *,
    prefiltered: bool = False,
    commit_times: dict[str, list[int]] | None = None,
) -> list[str]:
    """Order records by the shipped policy, restricted to the relevance union.

    For query evaluation the relevance order IS the candidate filter: an empty
    order means neither the lexical nor the semantic stream matched, so the
    positive-match-union contract requires zero candidates, not unrestricted
    admission. ``prefiltered=True`` declares that the caller already applied
    its own candidate filter (the shipped-baseline containment union), so the
    records pass through unrestricted and an empty order only means
    policy-alone ordering of those already-filtered records.
    """
    if prefiltered:
        candidates = list(records)
    else:
        candidate_ids = set(relevance_order)
        candidates = [
            record for record in records
            if record["memory_id"] in candidate_ids
        ]
    ranks = {memory_id: rank for rank, memory_id in enumerate(relevance_order)}
    return [
        record["memory_id"]
        for record, _decay in srv._memory_ranked(
            root,
            candidates,
            relevance_rank_by_id=ranks or None,
            commit_times_override=commit_times,
        )
    ]


def _shipped_baseline_order(
    srv,
    root: Path,
    records: list[dict[str, Any]],
    query: str,
    semantic_order: list[str],
    *,
    commit_times: dict[str, list[int]] | None = None,
) -> list[str]:
    """Apply the shipped containment-union + semantic tie-break to frozen records."""
    tokens = _tokens(query)
    semantic_ids = set(semantic_order)
    candidates = [
        record for record in records
        if record["memory_id"] in semantic_ids
        or (
            tokens
            and all(token in _record_text(record).lower() for token in tokens)
        )
    ]
    # The containment union above IS this path's candidate filter, so the
    # policy pass must not restrict it again by the semantic order alone (that
    # would drop pure-lexical containment matches). An empty candidate list
    # here already means "nothing matched", which orders to zero records.
    return _policy_order(
        srv, root, candidates, semantic_order,
        prefiltered=True, commit_times=commit_times,
    )


def _candidate_and_controls(
    srv,
    root: Path,
    case: dict,
    *,
    semantic_order: list[str] | None = None,
    records_override: list[dict[str, Any]] | None = None,
    commit_times: dict[str, list[int]] | None = None,
) -> dict[str, list[str]]:
    records = (
        list(records_override)
        if records_override is not None
        else _case_records(srv, root, case)
    )
    query = case.get("query", "")
    if not query:
        baseline = _search_ids(srv, root, case)
        return {
            "candidate": baseline,
            "lexical_only": baseline,
            "semantic_only": baseline,
        }
    lexical = lexical_bm25_order(records, query)
    semantic = [] if case.get("no_index") else list(
        semantic_order if semantic_order is not None
        else case.get("semantic_order") or []
    )
    fused = reciprocal_rank_fusion([lexical, semantic])
    return {
        "candidate": _policy_order(srv, root, records, fused, commit_times=commit_times),
        "lexical_only": _policy_order(srv, root, records, lexical, commit_times=commit_times),
        "semantic_only": _policy_order(srv, root, records, semantic, commit_times=commit_times),
    }


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _aggregate_rankings(
    rankings: list[list[str]], expected: list[list[str]], k: int
) -> dict[str, float]:
    return {
        "recall_at_k": _average([
            _recall_at_k(ranked, wanted, k)
            for ranked, wanted in zip(rankings, expected)
        ]),
        "mrr": _average([
            _reciprocal_rank(ranked, wanted)
            for ranked, wanted in zip(rankings, expected)
        ]),
    }


def run(root: Path, k: int = DEFAULT_K) -> dict:
    import server_impl as srv
    mem = srv._memory_mod()
    fixture = load_fixture()
    build_corpus(root, fixture["records"], mem)
    fixture_fingerprint = hashlib.sha256(
        json.dumps(fixture, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    frozen_histories = {
        path: [int(ts) for ts in values]
        for path, values in fixture.get("commit_times", {}).items()
    }
    # Wave 1tis8: SEED the throwaway repo's own store through the canonical
    # writer rather than rebinding `index_state_store.file_commit_times`. A
    # module-global rebind is unsafe in a long-lived server (overlapping calls
    # restore out of order, and unrelated readers observe the replacement), and
    # seeding makes the hermetic corpus real instead of patched.
    _seed_commit_history(srv, root, frozen_histories)

    case_results = []
    comparison_rankings = {
        name: [] for name in (
            "baseline", "candidate", "lexical_only", "semantic_only"
        )
    }
    expected_sets = []
    for case in fixture["cases"]:
        response = _search_result(srv, root, case)
        ranked = [
            record["memory_id"] for record in response["data"]["records"]
        ]
        expected = case.get("expected", [])
        controls = _candidate_and_controls(
            srv, root, case, commit_times=frozen_histories
        )
        shipped_invariant_pass = _invariant_pass(case, response)
        candidate_invariant_pass = _ranking_invariant_pass(
            case, controls["candidate"], shipped_invariant_pass
        )
        case_results.append({
            "category": case["category"],
            "recall_at_k": _recall_at_k(ranked, expected, k),
            "mrr": _reciprocal_rank(ranked, expected),
            "invariant_pass": shipped_invariant_pass,
            "candidate_invariant_pass": candidate_invariant_pass,
            "invariant_note": case.get("invariant_note", ""),
            "ranked": ranked,
        })
        expected_sets.append(expected)
        comparison_rankings["baseline"].append(ranked)
        for name, candidate_ranked in controls.items():
            comparison_rankings[name].append(candidate_ranked)

    comparison = {
        name: _aggregate_rankings(rankings, expected_sets, k)
        for name, rankings in comparison_rankings.items()
    }

    invariants_total = sum(1 for c in fixture["cases"] if c.get("invariant"))
    invariants_passed = sum(
        1 for r, c in zip(case_results, fixture["cases"])
        if c.get("invariant") and r["invariant_pass"])
    candidate_invariants_passed = sum(
        1 for r, c in zip(case_results, fixture["cases"])
        if c.get("invariant") and r["candidate_invariant_pass"])
    return {
        "k": k,
        "fixture_fingerprint": fixture_fingerprint,
        "cases": case_results,
        "overall": {
            "recall_at_k": _average([r["recall_at_k"] for r in case_results]),
            "mrr": _average([r["mrr"] for r in case_results]),
            "invariants_passed": invariants_passed,
            "invariants_total": invariants_total,
            "candidate_invariants_passed": candidate_invariants_passed,
        },
        "comparison": comparison,
        "adoption_gate": evaluate_adoption(
            comparison,
            candidate_invariants_passed=candidate_invariants_passed,
            invariants_total=invariants_total,
            curated=None,
        ),
    }


def evaluate_adoption(
    hermetic: dict[str, dict[str, float]],
    *,
    candidate_invariants_passed: int,
    invariants_total: int,
    curated: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return the explicit fusion adoption decision and machine-readable reasons."""
    reasons = []
    if candidate_invariants_passed != invariants_total:
        reasons.append("candidate failed a hermetic policy invariant")
    if (
        hermetic["candidate"]["recall_at_k"]
        < hermetic["baseline"]["recall_at_k"]
    ):
        reasons.append("candidate regressed hermetic recall@k")
    if not curated or not curated.get("available"):
        reasons.append("curated corpus pass unavailable")
    else:
        metrics = curated["metrics"]
        if metrics["candidate"]["mrr"] <= metrics["baseline"]["mrr"]:
            reasons.append("candidate did not strictly improve curated MRR")
        if (
            metrics["candidate"]["recall_at_k"]
            < metrics["baseline"]["recall_at_k"]
        ):
            reasons.append("candidate regressed curated recall@k")
    return {
        "adopt": not reasons,
        "reasons": reasons,
        "product_path_changed": False,
    }


def _semantic_order(index: Any, query: str, memory_dir: str) -> list[str]:
    hits, _reranked = index.search_docs(query, top_n=20)
    order = []
    for hit in hits:
        path = str(hit.get("path") or "")
        if path.startswith(memory_dir):
            memory_id = Path(path).stem
            if memory_id not in order:
                order.append(memory_id)
    return order


def run_curated(root: Path, k: int = DEFAULT_K) -> dict[str, Any]:
    """Run a bounded live-corpus pass and return aggregate-only evidence."""
    import server_impl as srv
    mem = srv._memory_mod()
    records = [
        record for record in mem.load_memory_records(
            root, statuses=list(mem.DEFAULT_SURFACED_STATUSES)
        )
        if record.get("target_refs") and record.get("summary")
    ]
    counts_by_kind = Counter(record["kind"] for record in records)
    counts_by_status = Counter(record["status"] for record in records)
    selected = sorted(
        records,
        key=lambda record: (
            hashlib.sha256(record["memory_id"].encode("utf-8")).hexdigest(),
            record["memory_id"],
        ),
    )[:CURATED_SAMPLE_CAP]
    frozen_payload = [
        {
            "memory_id": record["memory_id"],
            "kind": record["kind"],
            "status": record["status"],
            "summary": record["summary"],
            "targets": record["target_refs"],
            "evidence": record["evidence_refs"],
            "confidence": record["confidence"],
        }
        for record in selected
    ]
    fingerprint = hashlib.sha256(
        json.dumps(frozen_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    report: dict[str, Any] = {
        "available": False,
        "sample_size": len(selected),
        "sample_cap": CURATED_SAMPLE_CAP,
        "sample_strategy": "stable identity hash, frozen before scoring",
        "fingerprint": fingerprint,
        "counts_by_kind": dict(sorted(counts_by_kind.items())),
        "counts_by_status": dict(sorted(counts_by_status.items())),
    }
    if not selected:
        report["unavailable_reason"] = "no surfaced records with targets and summaries"
        return report
    try:
        index = srv.WaveIndex(root)
        index._ensure_loaded()
    except Exception as exc:
        report["unavailable_reason"] = f"semantic index unavailable: {type(exc).__name__}"
        return report

    rankings = {
        name: [] for name in (
            "baseline", "candidate", "lexical_only", "semantic_only"
        )
    }
    expected_sets: list[list[str]] = []
    index_store = srv._load_script("index_state_store")
    all_targets = {
        target
        for record in selected
        for target in record.get("target_refs") or []
        if not target.startswith(("symbol:", "community:"))
    }
    frozen_histories = index_store.file_commit_times(
        root / ".wavefoundry" / "index", all_targets
    )
    # Wave 1tis8: the frozen snapshot is passed EXPLICITLY into the ranking
    # path. Rebinding the shared `index_state_store.file_commit_times` global
    # here corrupted a long-lived server: two overlapping calls restore out of
    # order, leaving one call's frozen subset installed for every later reader,
    # and concurrent memory_search callers observed the replacement meanwhile.
    selected_ids = {record["memory_id"] for record in selected}
    for selected_record in selected:
        query = selected_record["summary"]
        semantic = [
            memory_id
            for memory_id in _semantic_order(index, query, mem.MEMORY_DIR)
            if memory_id in selected_ids
        ]
        case = {"query": query}
        baseline = _shipped_baseline_order(
            srv, root, selected, query, semantic,
            commit_times=frozen_histories,
        )
        controls = _candidate_and_controls(
            srv,
            root,
            case,
            semantic_order=semantic,
            records_override=selected,
            commit_times=frozen_histories,
        )
        rankings["baseline"].append(baseline)
        for name, ranked in controls.items():
            rankings[name].append(ranked)
        expected_sets.append([selected_record["memory_id"]])

    report["available"] = True
    report["metrics"] = {
        name: _aggregate_rankings(ranked, expected_sets, k)
        for name, ranked in rankings.items()
    }
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--curated-root", type=Path)
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        (root / "docs" / "agents").mkdir(parents=True)
        report = run(root)
    if args.curated_root:
        report["curated"] = run_curated(args.curated_root.resolve())
        report["adoption_gate"] = evaluate_adoption(
            report["comparison"],
            candidate_invariants_passed=report["overall"]["candidate_invariants_passed"],
            invariants_total=report["overall"]["invariants_total"],
            curated=report["curated"],
        )
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
        print("comparison (all-case recall@3 / MRR):",
              ", ".join(
                  f"{name}={metrics['recall_at_k']:.2f}/{metrics['mrr']:.2f}"
                  for name, metrics in report["comparison"].items()
              ))
        if report.get("curated"):
            curated = report["curated"]
            print(
                "curated:",
                "available" if curated["available"] else curated["unavailable_reason"],
                f"sample={curated['sample_size']} fingerprint={curated['fingerprint']}",
            )
    ov = report["overall"]
    return 0 if ov["invariants_passed"] == ov["invariants_total"] else 1


if __name__ == "__main__":
    sys.exit(main())
