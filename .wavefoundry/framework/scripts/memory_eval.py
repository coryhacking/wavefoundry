#!/usr/bin/env python3
"""Memory-retrieval policy and candidate evaluation.

Builds a synthetic memory corpus (memory_golden.json) in a throwaway repo, runs
the current ``memory_search`` path against golden fixtures, and compares it
with the legacy confidence-first lexical+semantic RRF control. The optional
curated pass scores a frozen situation-language query set
(``docs/evals/memory-query-set.json`` and its lock) against baseline arms over
one corpus, and keeps the old self-summary sample only as a labeled sanity
floor. It emits aggregate metrics and counts only, never memory bodies,
summaries, record ids, query text or case ids (wave 245na).

The shared BM25/RRF primitives also serve production memory search; comparison
variants and sampled diagnostics remain measurement-only. Deterministic
and hermetic by default; ``--curated-root`` is an explicit operator-run
observational pass, never adoption qualification. Explicit frozen full-corpus
inputs use the qualification helpers; ordinary MCP calls do not discover
local qualification files automatically.

This module ships with the framework (wave 1tgws) so the curated pass can
measure ANY target repository's memory corpus, through ``wf_memory_eval`` or
this CLI. Two distinct surfaces live here:

* ``run_curated(root)`` — the shipped cross-project measurement. Needs only a
  target repo; returns aggregate-only evidence.
* ``run(root)`` — the hermetic invariant pass. Needs the golden fixture, which
  is test scaffolding and is NOT packaged; it is exercised by
  ``tests/test_memory_eval.py``. Calling it without the fixture raises a clear
  ``FileNotFoundError`` rather than degrading silently.

Usage:  python memory_eval.py [--json] [--curated-root PATH] [--query-set-version N]
        python memory_eval.py --freeze-query-set ROOT [--query-set-version N]
        python memory_eval.py --uncoverable-records ROOT
Exit 0 iff every policy invariant passes.

Change 246to: both passes report model-free, aggregate ``maintenance_signals``
(``maintenance_signals(root, state)``); the memory ids of the records the
frozen set cannot cover come only from ``uncoverable_records`` and
``--uncoverable-records``, never from the report. Query set version 1 is
``docs/evals/memory-query-set.json``; version N of 2 or more is
``memory-query-set.vN.json`` with ``memory-query-set.vN.lock.json``.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import math
import random
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

# Change 1zyv1: bytecode goes only to the project cache (``bytecode_cache``),
# never beside the sources; writes stay off until configure() enables the cache.
if __name__ == "__main__" or sys.pycache_prefix is None:
    sys.dont_write_bytecode = True
import bytecode_cache  # noqa: E402

if __name__ == "__main__":
    bytecode_cache.configure()


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

    def __init__(self, order: list[str], index_dir: Path | None = None) -> None:
        self._order = order
        self._docs_vector_layer = "docs"
        self.index_dir = index_dir
        self._meta = {"project": {}}

    def _ensure_loaded(self):
        return None

    def _memory_query_vector(self, query: str):
        return query

    def _memory_dense_scores(self, vector, paths: list[str], *,
                             expected_hashes: dict[str, str]) -> dict[str, Any]:
        ranks = {mid: i for i, mid in enumerate(self._order)}
        return {"scores": {path: 1.0 / (1 + ranks[Path(path).stem])
                           for path in paths if Path(path).stem in ranks},
                "complete": True, "eligible_chunks": len(paths),
                "covered_paths": len(paths), "requested_paths": len(paths)}

    def _get_memory_reranker(self):
        return self

    def rerank(self, query: str, texts: list[str]) -> list[float]:
        return [0.0] * len(texts)  # eligibility/order fixtures, not model qualification

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
        # Change 246to: the fixture's file targets exist in the throwaway
        # tree, so they resolve and churn on their canonical paths.
        for target in rec["targets"]:
            if not str(target).startswith(("symbol:", "community:")):
                target_path = root / str(target)
                if not target_path.exists():
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_bytes(b"# memory eval fixture target\n")
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
        _StubIndex(case["semantic_order"], root / ".wavefoundry" / "index")
        if case.get("semantic_order") else None)
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
        if case.get("invariant_falsy_id") and not any(
            record["memory_id"] == case["invariant_falsy_id"]
            and not record.get(case["invariant_field"])
            for record in records
        ):
            # Change 246to: the named control record must be present and unflagged.
            return False
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


def lexical_bm25_scores(
    records: list[dict[str, Any]], query: str
) -> dict[str, float]:
    """Positive BM25 scores over the complete supplied eligible record corpus."""
    query_terms = _tokens(query)
    if not query_terms or not records:
        return {}
    identities = [record["memory_id"] for record in records]
    if len(set(identities)) != len(identities):
        raise ValueError("BM25 requires distinct memory identities")
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
    return {memory_id: score for score, memory_id in scored}


def lexical_bm25_order(
    records: list[dict[str, Any]], query: str
) -> list[str]:
    """Deterministic BM25 over already-loaded eligible memory records."""
    return list(lexical_bm25_scores(records, query))


def reciprocal_rank_fusion(
    rankings: list[list[str]], *, rrf_k: int = RRF_K
) -> list[str]:
    """Deterministic RRF over record-deduplicated candidate streams."""
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


def fusion_rankings(
    dense_scores: dict[str, float], lexical_scores: dict[str, float],
    cap: int = 20, *, injection_eligible: set[str] | None = None,
) -> dict[str, list[str]]:
    """Frozen evaluation variants, with at most ``cap`` records per channel.

    Min-max populations are the capped channels, not all stored memories.
    A constant nonempty channel maps to one; an absent identity maps to zero.
    These scores order candidates and are not relevance probabilities.
    """
    if type(cap) is not int or not 1 <= cap <= 20:
        raise ValueError("candidate cap must be an integer from 1 to 20")

    def bounded(scores: dict[str, float], positive: bool) -> dict[str, float]:
        if any(not isinstance(mid, str) or not mid or isinstance(score, bool)
               or not isinstance(score, (int, float)) or not math.isfinite(score)
               for mid, score in scores.items()):
            raise ValueError("candidate scores must have identities and finite numbers")
        return dict(sorted(
            ((mid, score) for mid, score in scores.items() if not positive or score > 0),
            key=lambda item: (-item[1], item[0]),
        )[:cap])

    dense = bounded(dense_scores, False)
    lexical = bounded(lexical_scores, True)

    def normalized(scores: dict[str, float]) -> dict[str, float]:
        if not scores:
            return {}
        low, high = min(scores.values()), max(scores.values())
        return {mid: (score - low) / (high - low) if high > low else 1.0
                for mid, score in scores.items()}

    def weighted_rrf(weight: float) -> list[str]:
        scores: dict[str, float] = {}
        for channel, factor in ((dense, weight), (lexical, 1.0 - weight)):
            for rank, mid in enumerate(channel, 1):
                scores[mid] = scores.get(mid, 0.0) + factor / (RRF_K + rank)
        return sorted(scores, key=lambda mid: (-scores[mid], mid))[:cap]

    dn, ln = normalized(dense), normalized(lexical)
    union = set(dense) | set(lexical)
    score_order = sorted(
        union, key=lambda mid: (-(0.75 * dn.get(mid, 0.0) + 0.25 * ln.get(mid, 0.0)), mid)
    )[:cap]
    injected = list(dense)
    if lexical and injection_eligible:
        threshold = 0.5 * max(lexical.values())
        for mid, score in lexical.items():
            if mid in injection_eligible and mid not in injected and score >= threshold:
                injected.insert(min(1, len(injected)), mid)
                break
    return {
        "semantic": list(dense), "lexical": list(lexical),
        "rrf": weighted_rrf(0.5), "score_fusion": score_order,
        "weighted025": weighted_rrf(0.25), "weighted075": weighted_rrf(0.75),
        "injection": injected[:cap],
    }


def qualification_fingerprint(payload: Any) -> str:
    """Canonical complete-payload identity; not proof of reviewer independence."""
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")).hexdigest()


def validate_qualification_manifest(
    corpus: dict[str, Any], queries: dict[str, Any], manifest: dict[str, Any],
) -> dict[str, Any]:
    """Validate pinned local inputs without returning their identities or text.

    Independence and untouched holdout remain reviewer declarations; hashes
    detect changed inputs, not whether somebody inspected a held-out result.
    """
    def malformed(reason: str) -> dict[str, Any]:
        return {"valid": False, "reasons": [reason], "corpus_count": 0, "holdout_count": 0}

    if not all(isinstance(value, dict) for value in (corpus, queries, manifest)):
        return malformed("invalid_manifest_structure")
    populations = (corpus.get("records"), corpus.get("archive_register", []))
    if any(not isinstance(population, list)
           or any(not isinstance(record, dict) for record in population)
           for population in populations):
        return malformed("invalid_corpus_structure")
    cases, development = queries.get("cases"), queries.get("development_cases", [])
    if any(not isinstance(population, list)
           or any(not isinstance(case, dict) for case in population)
           for population in (cases, development)):
        return malformed("invalid_query_structure")
    if not isinstance(manifest.get("parameters"), dict) or not isinstance(manifest.get("gates"), dict):
        return malformed("invalid_manifest_structure")
    reasons: list[str] = []
    for key, payload in (("corpus_fingerprint", corpus), ("queries_fingerprint", queries),
                         ("parameters_fingerprint", manifest.get("parameters", {}))):
        try:
            fingerprint = qualification_fingerprint(payload)
        except (ValueError, TypeError):
            return malformed("invalid_fingerprint_payload")
        if manifest.get(key) != fingerprint:
            reasons.append(key + "_mismatch")
    if manifest.get("schema_version") != 1:
        reasons.append("unsupported_manifest_version")
    reviewer, author = manifest.get("reviewer"), manifest.get("ranker_author")
    if not reviewer or not author or reviewer == author or queries.get("reviewer") != reviewer:
        reasons.append("independent_reviewer_unproven")
    if not manifest.get("split_protocol"):
        reasons.append("split_protocol_missing")
    parameters = manifest.get("parameters", {})
    expected = {"channel_cap": 20, "result_cap": 20, "rrf_k": 60,
                "score_semantic_weight": 0.75, "normalization": "bounded-channel-minmax",
                "relevance_text": "title-action-summary", "relevance_threshold": -4.0,
                "qualification_cap": 20}
    if any(parameters.get(key) != value for key, value in expected.items()):
        reasons.append("parameters_do_not_match_frozen_contract")
    gates = {"recall3_gain": 0.05, "latency_reduction": 0.20, "warm_p95_ms": 500}
    if any(manifest.get("gates", {}).get(key) != value for key, value in gates.items()):
        reasons.append("gates_do_not_match_frozen_contract")
    ids: set[str] = set()
    for population in populations:
        seen: set[str] = set()
        for record in population:
            mid = record.get("memory_id")
            if not isinstance(mid, str) or not mid or mid in seen:
                reasons.append("invalid_corpus_identity")
                continue
            seen.add(mid)
        ids.update(seen)  # archived body and compact entry may share an identity
    if not ids:
        reasons.append("empty_corpus")
    development_queries = {" ".join(str(case.get("query", "")).lower().split())
                           for case in development}
    holdout_queries: set[str] = set()
    case_ids: set[str] = set()
    negatives = 0
    for case in cases:
        q = " ".join(str(case.get("query", "")).lower().split())
        cid = case.get("id")
        if (not isinstance(case.get("query"), str) or not q
                or q in development_queries or q in holdout_queries
                or not isinstance(cid, str) or not cid or cid in case_ids
                or case.get("split") != "holdout"):
            reasons.append("holdout_not_disjoint")
        holdout_queries.add(q)
        if isinstance(cid, str):
            case_ids.add(cid)
        labels = [case.get(key) for key in ("relevant_ids", "irrelevant_ids", "unjudged_ids")]
        if any(not isinstance(label, list)
               or any(not isinstance(mid, str) or not mid for mid in label)
               or len(label) != len(set(label)) for label in labels):
            reasons.append("explicit_relevance_labels_required")
            continue
        relevant, irrelevant, unjudged = map(set, labels)
        if (not (relevant | irrelevant | unjudged) <= ids
                or relevant & irrelevant or relevant & unjudged or irrelevant & unjudged):
            reasons.append("invalid_relevance_labels")
        if not relevant and not irrelevant:
            reasons.append("no_match_judgment_unproven")
        negatives += not relevant
    if len(cases) < 24 or negatives < 8 or negatives == len(cases):
        reasons.append("insufficient_holdout_coverage")
    return {"valid": not reasons, "reasons": sorted(set(reasons)),
            "corpus_count": len(ids), "holdout_count": len(cases)}


def quality_metrics(rows: list[dict[str, Any]], variant: str) -> dict[str, Any]:
    """Aggregate frozen judgments; negatives never inflate recall or MRR.

    Rows are explicit local evidence. Only this aggregate may enter ordinary
    MCP responses. Unavailable measurements invalidate the aggregate instead
    of being counted as successful no-match abstentions.
    """
    answerable: list[dict[str, float]] = []
    unavailable = negatives = false_positives = misses = no_relevant = 0
    irrelevant_count = unjudged_count = returned_count = 0
    candidate_values: list[float] = []
    for row in rows:
        available = row.get("available", row.get("availability", True))
        if isinstance(available, dict):
            available = available.get(variant, False)
        rankings = row.get("rankings", {})
        if available is not True or variant not in rankings:
            unavailable += 1
            continue
        ranked = list(dict.fromkeys(rankings[variant]))[:20]
        expected = set(row.get("relevant_ids", row.get("expected_ids", [])))
        irrelevant = set(row.get("irrelevant_ids", []))
        if expected & irrelevant:
            raise ValueError("relevance labels overlap")
        returned_count += len(ranked)
        irrelevant_count += len(set(ranked) & irrelevant)
        unjudged_count += len(set(ranked) - expected - irrelevant)
        if not expected:
            negatives += 1
            false_positives += bool(ranked)
            continue
        misses += not ranked
        no_relevant += not (set(ranked) & expected)
        answerable.append({
            "recall_at_3": _recall_at_k(ranked, sorted(expected), 3),
            "recall_at_10": _recall_at_k(ranked, sorted(expected), 10),
            "mrr": _reciprocal_rank(ranked, sorted(expected)),
        })
        candidates = row.get("candidate_ids")
        if isinstance(candidates, dict):
            candidates = candidates.get(variant)
        if candidates is None:
            candidates = row.get("evidence", {}).get(variant, {}).get("candidate_ids")
        if candidates is not None:
            candidate_values.append(len(set(candidates) & expected) / len(expected))
    valid = bool(rows) and not unavailable
    report: dict[str, Any] = {
        "available": valid, "queries": len(rows), "unavailable_queries": unavailable,
        "answerable_queries": len(answerable), "no_match_queries": negatives,
        "answerable_misses": misses, "answerable_without_relevant": no_relevant,
        "no_match_false_positives": false_positives,
        "judged_irrelevant_results": irrelevant_count, "unjudged_results": unjudged_count,
        "returned_results": returned_count,
        "candidate_recall": (sum(candidate_values) / len(candidate_values)
                             if valid and answerable and len(candidate_values) == len(answerable)
                             else None),
    }
    for key in ("recall_at_3", "recall_at_10", "mrr"):
        report[key] = (sum(case[key] for case in answerable) / len(answerable)
                       if valid and answerable else None)
    return report


def qualification_adoption(
    baseline: dict[str, Any], candidate: dict[str, Any],
    latencies: dict[str, Any], validity: dict[str, Any],
) -> dict[str, Any]:
    """Fail-closed readiness-contract gate over aggregate qualification evidence."""
    reasons = [key + "_unproven" for key in (
        "manifest_valid", "independent_labels", "holdout_untouched", "coverage_complete",
        "policy_approved", "performance_complete",
    ) if validity.get(key) is not True]
    quality_valid = baseline.get("available") is True and candidate.get("available") is True
    for metrics in (baseline, candidate):
        counts = [metrics.get(key) for key in ("queries", "answerable_queries", "no_match_queries")]
        if (any(type(value) is not int for value in counts)
                or counts[0] < 24 or counts[1] <= 0 or counts[2] < 8
                or counts[0] != counts[1] + counts[2]):
            quality_valid = False
        for count_key, population_key in (("answerable_misses", "answerable_queries"),
                                          ("no_match_false_positives", "no_match_queries")):
            count, population = metrics.get(count_key), metrics.get(population_key)
            if (type(count) is not int or type(population) is not int
                    or count < 0 or count > population):
                quality_valid = False
    for key in ("queries", "answerable_queries", "no_match_queries"):
        if baseline.get(key) != candidate.get(key) or not baseline.get(key):
            quality_valid = False
    gain = None
    for key in ("recall_at_3", "recall_at_10", "mrr"):
        before, after = baseline.get(key), candidate.get(key)
        if any(isinstance(v, bool) or not isinstance(v, (int, float))
               or not math.isfinite(v) or not 0 <= v <= 1 for v in (before, after)):
            quality_valid = False
        elif after + 1e-12 < before:
            reasons.append(key + "_regressed")
        if key == "recall_at_3" and quality_valid:
            gain = after - before
    for key in ("answerable_misses", "no_match_false_positives"):
        before, after = baseline.get(key), candidate.get(key)
        if any(type(v) is not int or v < 0 for v in (before, after)):
            quality_valid = False
        elif after > before:
            reasons.append(key + "_increased")
    if not quality_valid:
        reasons.append("quality_measurement_unavailable")
    before = latencies.get("baseline_p95_ms")
    after = latencies.get("candidate_p95_ms")
    timing_valid = all(not isinstance(v, bool) and isinstance(v, (int, float))
                       and math.isfinite(v) and v > 0 for v in (before, after))
    calls = [latencies.get(key) for key in ("baseline_warm_calls", "candidate_warm_calls")]
    timing_valid = timing_valid and all(type(v) is int and v >= 100 for v in calls)
    speed_gain = None
    if not timing_valid:
        reasons.append("performance_measurement_unavailable")
    else:
        speed_gain = 1.0 - after / before
        if after > 500 or after > before:
            reasons.append("warm_p95_budget_exceeded")
    if not ((gain is not None and gain + 1e-12 >= 0.05)
            or (speed_gain is not None and speed_gain + 1e-12 >= 0.20)):
        reasons.append("material_benefit_not_demonstrated")
    return {"adopt": not reasons, "reasons": reasons, "product_path_changed": False}


def _case_records(srv, root: Path, case: dict) -> list[dict[str, Any]]:
    mem = srv._memory_mod()
    statuses = None if case.get("include_history") else list(mem.DEFAULT_SURFACED_STATUSES)
    records = mem.load_memory_records(root, statuses=statuses)
    if not case.get("include_history") and (
        case.get("query") or case.get("target")
    ):
        records.extend(mem.load_archive_register_entries(root))
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
    bounded: bool = False,
) -> dict[str, list[str]]:
    """Candidate and stream-only controls under the shipped policy order.

    ``bounded=True`` is the curated pass (wave 245na): each stream is cut to
    production's caps before ``_policy_order``, so the policy sort orders a
    shortlist the size of production's instead of every lexical match. The
    hermetic ``run()`` keeps the unbounded streams.
    """
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
    if bounded:
        search_cap, check_cap = _production_caps()
        fused = reciprocal_rank_fusion([lexical[:search_cap], semantic])[:check_cap]
        return {
            "candidate": _policy_order(srv, root, records, fused, commit_times=commit_times),
            "lexical_only": _policy_order(
                srv, root, records, lexical[:check_cap], commit_times=commit_times),
            "semantic_only": _policy_order(
                srv, root, records, semantic[:check_cap], commit_times=commit_times),
        }
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
        "maintenance_signals": maintenance_signals(root, load_query_set(root)),
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
    elif curated.get("qualifying") is not True:
        reasons.append("self-summary diagnostic cannot qualify production adoption")
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


def _production_caps() -> tuple[int, int]:
    """Production's search and screen caps, read from ``memory_handlers``."""
    import wf_server.memory_handlers as memory_handlers
    return memory_handlers.MEMORY_SEARCH_CAP, memory_handlers.MEMORY_QUERY_CHECK_CAP


# --- Situation-language query set (wave 245na, change 245sp) ---------------

QUERY_SET_PATH = Path("docs") / "evals" / "memory-query-set.json"
QUERY_SET_LOCK_PATH = Path("docs") / "evals" / "memory-query-set.lock.json"
SEQUENCE_RATIO_THRESHOLD = 0.9
COSINE_THRESHOLD = 0.95
BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_MIN_DEFINED = 100
HELDOUT_MODULUS_FLOOR = 3
CASE_TYPES = ("answerable", "null", "stale")
SPLITS = ("heldout", "dev")
ARMS = ("no_memory", "grep", "bm25_only", "dense_only", "hybrid_no_rerank",
        "production", "full_context")
ABLATION_ARMS = ("dense_summary_only", "dense_compact")
METRIC_KEYS = ("recall_at_5", "mrr", "precision_shown", "false_show_rate",
               "stale_shown_rate")
# ``full_context`` ranks by memory id, so recall@5 measures id order, not
# retrieval. It reports recall over every shown record instead (council
# carry-forward 1, wave 245na).
FULL_CONTEXT_RECALL_KEY = "recall_all"
EMBEDDED_TEXT = {"dense": "record_markdown_chunks",
                 "lexical": "summary_title_evidence_targets_keywords",
                 "screen": "summary"}
EMBEDDED_TEXT_NOTE = (
    "dense_summary_only and dense_compact embed one vector per record in "
    "process; dense_only uses the best stored chunk per record, so the "
    "comparison mixes the text choice with chunking."
)
FREEZE_MODEL_MESSAGE = "freeze requires the docs embedding model"


class FreezeModelUnavailable(RuntimeError):
    """The docs embedding model could not embed the freeze probes."""


def query_set_sha256(payload: Any) -> str:
    """SHA-256 of the canonical JSON of the parsed query set, not its bytes."""
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()


def split_for(cluster_key: str) -> str:
    """Record-level split: ``heldout`` when sha256(key)[:8] mod 10 is 3 or more."""
    digest = hashlib.sha256(str(cluster_key).encode("utf-8")).hexdigest()
    return "heldout" if int(digest[:8], 16) % 10 >= HELDOUT_MODULUS_FLOOR else "dev"


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item for item in value)


def validate_query_set(payload: Any) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Return the cases, or ``(None, "query_set_invalid")``. A ``split`` field is ignored."""
    cases = payload.get("cases") if isinstance(payload, dict) else None
    if not isinstance(cases, list) or not cases:
        return None, "query_set_invalid"
    seen: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            return None, "query_set_invalid"
        case_id, query, case_type = case.get("id"), case.get("query"), case.get("case_type")
        relevant, stale, terms = case.get("relevant_ids"), case.get("stale_ids"), case.get("grep_terms")
        if (not isinstance(case_id, str) or not case_id or case_id in seen
                or not isinstance(query, str) or not query.strip()
                or case_type not in CASE_TYPES
                or not isinstance(case.get("source_id"), str) or not case["source_id"]
                or not _string_list(relevant) or not _string_list(stale)
                or not _string_list(terms) or not 1 <= len(terms) <= 3
                or not isinstance(case.get("author"), str) or not case["author"].strip()):
            return None, "query_set_invalid"
        if case_type == "null" and (relevant or case["source_id"] != case_id):
            return None, "query_set_invalid"
        if case_type != "null" and not relevant:
            return None, "query_set_invalid"
        if (case_type == "stale") != bool(stale):
            return None, "query_set_invalid"
        seen.add(case_id)
    return cases, None


def sequence_leaks(case: dict[str, Any], summaries: dict[str, str]) -> bool:
    """True when the query is a near copy of any relevant record's summary."""
    query = case["query"].lower()
    return any(
        difflib.SequenceMatcher(None, query, summary.lower()).ratio() >= SEQUENCE_RATIO_THRESHOLD
        for summary in (summaries.get(mid) or "" for mid in case["relevant_ids"])
        if summary
    )


def query_set_paths(version: int = 1) -> tuple[Path, Path]:
    """``(query set, lock)`` relative paths of query set ``version``.

    Version 1 is the original pair; version N of 2 or more is
    ``memory-query-set.vN.json`` with ``memory-query-set.vN.lock.json``.
    """
    version = int(version)
    if version < 1:
        raise ValueError("query set version must be 1 or more")
    if version == 1:
        return QUERY_SET_PATH, QUERY_SET_LOCK_PATH
    return (QUERY_SET_PATH.with_name(f"memory-query-set.v{version}.json"),
            QUERY_SET_LOCK_PATH.with_name(f"memory-query-set.v{version}.lock.json"))


_VERSIONED_QUERY_SET_RE = re.compile(r"^memory-query-set\.v([1-9][0-9]*)\.json$")


def default_query_set_version(root: Path) -> int:
    """The highest version N of 2 or more with both files, else 1."""
    folder = root / QUERY_SET_PATH.parent
    versions: list[int] = []
    try:
        names = [entry.name for entry in folder.iterdir()]
    except OSError:
        names = []
    for name in names:
        match = _VERSIONED_QUERY_SET_RE.match(name)
        if not match or int(match.group(1)) < 2:
            continue
        version = int(match.group(1))
        set_path, lock_path = query_set_paths(version)
        if (root / set_path).is_file() and (root / lock_path).is_file():
            versions.append(version)
    return max(versions, default=1)


def load_query_set(root: Path, version: int | None = None) -> dict[str, Any]:
    """Load, validate and hash-check the frozen query set.

    Returns ``{"available": bool, "reason": str|None, "cases": [...],
    "sha256": str|None, "lock": dict|None, "version": int}``. An absent set is
    not an error: only the sanity floor runs. ``version`` defaults to
    ``default_query_set_version(root)``.
    """
    version = default_query_set_version(root) if version is None else int(version)
    set_rel, lock_rel = query_set_paths(version)
    state: dict[str, Any] = {"available": False, "reason": None, "cases": [],
                             "sha256": None, "lock": None, "version": version}
    path = root / set_rel
    if not path.is_file():
        state["reason"] = "query_set_absent"
        return state
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state["reason"] = "query_set_invalid"
        return state
    cases, reason = validate_query_set(payload)
    if cases is None:
        state["reason"] = reason
        return state
    state["sha256"] = query_set_sha256(payload)
    lock_path = root / lock_rel
    if not lock_path.is_file():
        state["reason"] = "query_set_unfrozen"
        return state
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        lock = None
    if (not isinstance(lock, dict) or not isinstance(lock.get("query_set_sha256"), str)
            or not _string_list(lock.get("cosine_rejected", []))):
        state["reason"] = "query_set_lock_invalid"
        return state
    if lock["query_set_sha256"] != state["sha256"]:
        state["reason"] = "query_set_hash_mismatch"
        return state
    state.update(available=True, cases=cases, lock=lock)
    return state


COVERAGE_MIN_ANSWERABLE_CASES = 2
RETIRED_STATUSES = ("stale", "superseded", "rejected", "archived")


def _scored_cases(root: Path, state: dict[str, Any] | None, mem: Any) -> list[dict[str, Any]] | None:
    """The scored cases of a loaded query set, or None without one.

    Scored means not cosine-rejected by the lock and not a sequence leak,
    exactly as ``run_curated`` filters; no model is used.
    """
    if not state or not state.get("available"):
        return None
    corpus = (mem.load_memory_records(root, statuses=list(mem.DEFAULT_SURFACED_STATUSES))
              + mem.load_archive_register_entries(root))
    summaries = {record["memory_id"]: str(record.get("summary") or "") for record in corpus}
    cosine_rejected = set((state.get("lock") or {}).get("cosine_rejected") or [])
    return [case for case in state["cases"]
            if case["id"] not in cosine_rejected and not sequence_leaks(case, summaries)]


def _answerable_counts(scored: list[dict[str, Any]]) -> Counter:
    return Counter(case["source_id"] for case in scored if case["case_type"] == "answerable")


def _has_file_target(record: dict[str, Any]) -> bool:
    return any(not str(ref).startswith(("symbol:", "community:"))
               for ref in record.get("target_refs") or [])


def _coverage_gap(record: dict[str, Any], counts: Counter) -> bool:
    return (_has_file_target(record) and bool(str(record.get("summary") or "").strip())
            and counts.get(record["memory_id"], 0) < COVERAGE_MIN_ANSWERABLE_CASES)


def _has_rationale(record: dict[str, Any]) -> bool:
    return bool(str(record.get("validation_rationale") or "").strip()
                or str(record.get("action_delta") or "").strip())


def uncoverable_records(root: Path, query_set: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Active records the frozen query set cannot cover (change 246to).

    ``query_set`` is a ``load_query_set`` state; without an available one only
    ``no_rationale`` is evaluated. Each entry is ``{"memory_id", "reasons"}``
    with sorted reasons: ``coverage_gap`` (a file target and a summary, and
    fewer than 2 answerable scored cases whose ``source_id`` is the record)
    and ``no_rationale`` (neither a ``Validation rationale:`` nor an
    ``Action delta:`` line). Sorted by id. This is the Review memories batch;
    the ids never enter the evaluation report.
    """
    import server_impl as srv
    mem = srv._memory_mod()
    scored = _scored_cases(root, query_set, mem)
    counts = _answerable_counts(scored) if scored is not None else None
    out: list[dict[str, Any]] = []
    for record in sorted(mem.load_memory_records(root, statuses=["active"]),
                         key=lambda record: record["memory_id"]):
        reasons = []
        if counts is not None and _coverage_gap(record, counts):
            reasons.append("coverage_gap")
        if not _has_rationale(record):
            reasons.append("no_rationale")
        if reasons:
            out.append({"memory_id": record["memory_id"], "reasons": sorted(reasons)})
    return out


def maintenance_signals(root: Path, query_set: dict[str, Any] | None = None) -> dict[str, Any]:
    """Model-free maintenance counts for ``root`` (change 246to Requirement 7).

    Aggregate only: counts, never memory ids. Flags are the derived
    revalidation reasons the shipped ranker reports.
    """
    import server_impl as srv
    import wf_server.memory_handlers as memory_handlers
    mem = srv._memory_mod()
    active = mem.load_memory_records(root, statuses=["active"])
    reasons = [decay.get("revalidation_reasons") or []
               for _record, decay in memory_handlers._memory_ranked(root, active)]
    unresolved = sum(1 for item in reasons if "target_unresolved" in item)
    scored = _scored_cases(root, query_set, mem)
    if scored is None:
        coverage_gaps = None
    else:
        counts = _answerable_counts(scored)
        coverage_gaps = sum(1 for record in active if _coverage_gap(record, counts))
    outcomes = {"flagged": {"active": 0, "retired": 0},
                "unflagged": {"active": 0, "retired": 0}}
    for record in mem.load_memory_records(root, statuses=None):
        flags = record.get("check_flags")
        if flags is None or record.get("record_type") == "archive_register_entry":
            continue
        status = record.get("status")
        if status == "active":
            bucket = "active"
        elif status in RETIRED_STATUSES:
            bucket = "retired"
        else:
            continue
        flagged = bool(flags.strip()) and flags.strip() != "none"
        outcomes["flagged" if flagged else "unflagged"][bucket] += 1
    return {
        "active_records": len(active),
        "unresolved_target_records": unresolved,
        "unresolved_target_fraction": round(unresolved / len(active), 4) if active else None,
        "not_canonical_target_records": sum(
            1 for item in reasons if "target_not_canonical" in item),
        "churn_flagged_records": sum(1 for item in reasons if "target_churn" in item),
        "coverage_gap_records": coverage_gaps,
        "uncoverable_records": len(uncoverable_records(root, query_set)),
        "check_outcomes": outcomes,
    }


def _case_contributions(case: dict[str, Any], ranked: list[str], shown: list[str],
                        *, recall_all: bool = False) -> dict[str, tuple[float, int]]:
    """Per-case (numerator, denominator) for each metric; den 0 means not eligible."""
    relevant, stale = set(case["relevant_ids"]), set(case["stale_ids"])
    shown_set = set(shown)
    out = {key: (0.0, 0) for key in METRIC_KEYS}
    if case["case_type"] in ("answerable", "stale"):
        window = ranked if recall_all else ranked[:5]
        out["recall_at_5"] = (len(relevant & set(window)) / len(relevant), 1)
        out["mrr"] = (_reciprocal_rank(ranked, sorted(relevant)), 1)
        out["precision_shown"] = (float(len(relevant & shown_set)), len(shown_set))
    if case["case_type"] == "null":
        out["false_show_rate"] = (1.0 if shown_set else 0.0, 1)
    if case["case_type"] == "stale":
        out["stale_shown_rate"] = (1.0 if shown_set & stale else 0.0, 1)
    out["mean_shown"] = (float(len(shown_set)), 1)
    return out


def _ratio(num: float, den: int) -> float | None:
    return round(num / den, 4) if den else None


def _bootstrap(clusters: list[tuple[float, int]], draws: list[list[int]]) -> dict[str, Any]:
    """Percentile interval over cluster resamples; undefined resamples are skipped."""
    values: list[float] = []
    undefined = 0
    for draw in draws:
        den = sum(clusters[i][1] for i in draw)
        if not den:
            undefined += 1
            continue
        values.append(sum(clusters[i][0] for i in draw) / den)
    values.sort()
    n = len(values)
    interval = None
    if n >= BOOTSTRAP_MIN_DEFINED:
        interval = [round(values[math.floor(0.025 * n)], 4),
                    round(values[math.ceil(0.975 * n) - 1], 4)]
    return {"interval": interval, "undefined_resamples": undefined}


def _cluster_draws(cluster_count: int) -> list[list[int]]:
    """The draws of one ``random.Random(0)``; identical for every split metric."""
    rng = random.Random(0)
    if not cluster_count:
        return [[] for _ in range(BOOTSTRAP_RESAMPLES)]
    return [[rng.randrange(cluster_count) for _ in range(cluster_count)]
            for _ in range(BOOTSTRAP_RESAMPLES)]


def score_arms(cases: list[dict[str, Any]],
               outcomes: dict[str, list[tuple[list[str], list[str]]]],
               *, ordered_arms: tuple[str, ...] = ARMS) -> dict[str, Any]:
    """Score every arm per split with cluster bootstrap intervals.

    ``outcomes[arm][i]`` is ``(ranked, shown)`` for ``cases[i]``. Each case's
    cluster is its ``source_id``; a case-level ``split`` field is ignored.
    """
    by_split: dict[str, list[int]] = {split: [] for split in SPLITS}
    for i, case in enumerate(cases):
        by_split[split_for(case["source_id"])].append(i)
    metrics: dict[str, dict[str, Any]] = {}
    arm_order: dict[str, list[str]] = {}
    split_counts: dict[str, dict[str, int]] = {}
    for split in SPLITS:
        members = by_split[split]
        cluster_keys = sorted({cases[i]["source_id"] for i in members})
        position = {key: n for n, key in enumerate(cluster_keys)}
        draws = _cluster_draws(len(cluster_keys))
        split_counts[split] = {
            "cases": len(members), "clusters": len(cluster_keys),
            **{case_type: sum(1 for i in members if cases[i]["case_type"] == case_type)
               for case_type in CASE_TYPES},
        }
        split_metrics: dict[str, Any] = {}
        for arm, rows in outcomes.items():
            recall_all = arm == "full_context"
            recall_key = FULL_CONTEXT_RECALL_KEY if recall_all else "recall_at_5"
            per_cluster = {key: [[0.0, 0] for _ in cluster_keys]
                           for key in (*METRIC_KEYS, "mean_shown")}
            for i in members:
                ranked, shown = rows[i]
                slot = position[cases[i]["source_id"]]
                for key, (num, den) in _case_contributions(
                        cases[i], ranked, shown, recall_all=recall_all).items():
                    per_cluster[key][slot][0] += num
                    per_cluster[key][slot][1] += den
            row: dict[str, Any] = {}
            intervals: dict[str, Any] = {}
            undefined: dict[str, int] = {}
            for key in METRIC_KEYS:
                clusters = [(num, den) for num, den in per_cluster[key]]
                name = recall_key if key == "recall_at_5" else key
                row[name] = _ratio(sum(c[0] for c in clusters), sum(c[1] for c in clusters))
                boot = _bootstrap(clusters, draws)
                intervals[name] = boot["interval"]
                undefined[name] = boot["undefined_resamples"]
            shown_clusters = per_cluster["mean_shown"]
            row["mean_shown"] = _ratio(sum(c[0] for c in shown_clusters),
                                       sum(c[1] for c in shown_clusters))
            row["intervals"] = intervals
            row["undefined_resamples"] = undefined
            row["flags"] = []
            split_metrics[arm] = row
        bm25 = split_metrics.get("bm25_only", {}).get("recall_at_5")
        for arm, row in split_metrics.items():
            key = FULL_CONTEXT_RECALL_KEY if arm == "full_context" else "recall_at_5"
            interval = row["intervals"].get(key)
            if (arm != "bm25_only" and bm25 is not None and interval is not None
                    and interval[1] < bm25):
                row["flags"].append("recall_below_bm25")

        def order_key(arm: str) -> tuple[float, float, str]:
            row = split_metrics[arm]
            recall = row.get(FULL_CONTEXT_RECALL_KEY if arm == "full_context" else "recall_at_5")
            mrr = row.get("mrr")
            return (-(recall if recall is not None else -1.0),
                    -(mrr if mrr is not None else -1.0), arm)

        arm_order[split] = sorted((arm for arm in split_metrics if arm in ordered_arms),
                                  key=order_key)
        metrics[split] = split_metrics
    return {"metrics": metrics, "arm_order": arm_order, "split_counts": split_counts}


def _register_sections(root: Path) -> dict[str, str]:
    """Each archive register entry's section text, keyed by memory id."""
    mem_path = root / "docs" / "agents" / "memory-archive.md"
    try:
        import memory_records
        mem_path = root / memory_records.MEMORY_ARCHIVE_MANIFEST
        text = mem_path.read_text(encoding="utf-8")
    except (OSError, ImportError, AttributeError):
        return {}
    sections: dict[str, str] = {}
    for block in re.split(r"(?m)^## ", text)[1:]:
        lines = block.splitlines()
        if lines:
            sections[lines[0].strip()] = "## " + block
    return sections


def _corpus_texts(root: Path, corpus: list[dict[str, Any]]) -> dict[str, str]:
    """Grep text per corpus item: a record's file, a register entry's section."""
    sections = _register_sections(root)
    texts: dict[str, str] = {}
    for record in corpus:
        mid = record["memory_id"]
        if record.get("record_type") == "archive_register_entry":
            texts[mid] = sections.get(mid, "")
            continue
        source = Path(record["path"])
        if not source.is_absolute():
            source = root / source
        try:
            texts[mid] = source.read_text(encoding="utf-8")
        except OSError:
            texts[mid] = ""
    return texts


def grep_order(texts: dict[str, str], terms: list[str]) -> list[str]:
    """Items containing every term (case-insensitive), by total count, then id."""
    lowered = [term.lower() for term in terms if term]
    if not lowered:
        return []
    scored = []
    for mid, text in texts.items():
        haystack = text.lower()
        counts = [haystack.count(term) for term in lowered]
        if all(counts):
            scored.append((-sum(counts), mid))
    return [mid for _count, mid in sorted(scored)]


def dense_stream(index: Any, query: str, body_paths: dict[str, str],
                 expected_hashes: dict[str, str]) -> tuple[list[str] | None, str | None]:
    """Production's semantic stream, ties by ``(-score, memory_id)``; None when not current."""
    vector = index._memory_query_vector(query)
    dense = index._memory_dense_scores(
        vector, list(body_paths), expected_hashes=expected_hashes)
    if dense.get("source_current") is False:
        return None, "memory_source_state_stale"
    if not dense.get("complete"):
        return None, "memory_vector_coverage_incomplete"
    scores = dense["scores"]
    return [body_paths[path] for path in sorted(
        scores, key=lambda path: (-scores[path], body_paths[path]))], None


def _compact_text(record: dict[str, Any]) -> str:
    return "\n".join([
        str(record.get("title") or ""), str(record.get("summary") or ""),
        *[ref for ref in record.get("target_refs") or []
          if not ref.startswith(("symbol:", "community:"))],
        *[str(word) for word in record.get("keywords") or []],
    ])


class _Ablation:
    """In-process one-vector-per-record arms; never writes the index."""

    def __init__(self, index: Any, records: list[dict[str, Any]], texts: list[str]):
        import numpy as np
        self._np = np
        self._ids = [record["memory_id"] for record in records]
        self._model = index._indexer_constant("DOCS_MODEL")
        self._index = index
        embedder = index._get_embedder(self._model)
        matrix = np.asarray([np.asarray(v, dtype=np.float32) for v in embedder.embed(texts)])
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._matrix = matrix / norms
        self.mean_chars = round(sum(len(text) for text in texts) / max(len(texts), 1), 1)

    def order(self, query: str, cap: int) -> list[str]:
        np = self._np
        vector = np.asarray(self._index._embed_query(query, self._model), dtype=np.float32)
        norm = float(np.linalg.norm(vector)) or 1.0
        scores = self._matrix @ (vector / norm)
        ranked = sorted(range(len(self._ids)), key=lambda i: (-float(scores[i]), self._ids[i]))
        return [self._ids[i] for i in ranked[:cap]]


def target_retrievable(root: Path, records: list[dict[str, Any]], index: Any,
                       mem: Any) -> dict[str, int]:
    """Reachability of each record by its own file targets.

    ``retrievable`` uses the uncapped ``match_targets`` predicate, so it is a
    sanity check (near-tautological), not a quality signal;
    ``crowded_past_search_cap`` is the signal: a capped target search returns
    the record for none of its file targets.
    """
    import wf_server.memory_handlers as memory_handlers
    cap = memory_handlers.MEMORY_SEARCH_CAP
    returned: dict[str, set[str]] = {}
    with_targets = retrievable = crowded = 0
    for record in records:
        targets = [ref for ref in record.get("target_refs") or []
                   if not ref.startswith(("symbol:", "community:"))]
        if not targets:
            continue
        with_targets += 1
        retrievable += any(mem.match_targets(record, path=target) for target in targets)
        found = False
        for target in targets:
            if target not in returned:
                response = memory_handlers.memory_search_response(
                    root, target=target, index=index, limit=cap)
                returned[target] = {
                    row["memory_id"] for row in response["data"].get("records") or []}
            if record["memory_id"] in returned[target]:
                found = True
                break
        crowded += not found
    return {"records_with_file_targets": with_targets, "retrievable": retrievable,
            "crowded_past_search_cap": crowded}


def _sanity_floor(srv, root: Path, index: Any, selected: list[dict[str, Any]],
                  k: int) -> dict[str, Any]:
    """The old self-summary sample: a labeled floor, never the headline."""
    frozen_payload = [
        {"memory_id": record["memory_id"], "kind": record["kind"],
         "status": record["status"], "summary": record["summary"],
         "targets": record["target_refs"], "evidence": record["evidence_refs"],
         "confidence": record["confidence"]}
        for record in selected
    ]
    floor: dict[str, Any] = {
        "label": "self_summary_sanity_floor", "headline": False,
        "available": False,
        "sample_size": len(selected), "sample_cap": CURATED_SAMPLE_CAP,
        "sample_strategy": "stable identity hash, frozen before scoring",
        "fingerprint": hashlib.sha256(json.dumps(
            frozen_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
    }
    if not selected:
        floor["unavailable_reason"] = "no surfaced records with targets and summaries"
        return floor
    index_store = srv._load_script("index_state_store")
    all_targets = {target for record in selected for target in record.get("target_refs") or []
                   if not target.startswith(("symbol:", "community:"))}
    frozen_histories = index_store.file_commit_times(root / ".wavefoundry" / "index", all_targets)
    rankings: dict[str, list[list[str]]] = {
        name: [] for name in ("baseline", "candidate", "lexical_only", "semantic_only")}
    expected_sets: list[list[str]] = []
    dense_measured = True
    try:
        body_paths, expected_hashes = srv._memory_mod().memory_body_paths(root, selected)
        for record in selected:
            query = record["summary"]
            semantic, reason = dense_stream(index, query, body_paths, expected_hashes)
            if semantic is None:
                dense_measured = False
                semantic = []
            rankings["baseline"].append(_shipped_baseline_order(
                srv, root, selected, query, semantic, commit_times=frozen_histories))
            controls = _candidate_and_controls(
                srv, root, {"query": query}, semantic_order=semantic,
                records_override=selected, commit_times=frozen_histories, bounded=True)
            for name, ranked in controls.items():
                rankings[name].append(ranked)
            expected_sets.append([record["memory_id"]])
    except Exception:
        # Exception text can carry private query or record text.
        floor["unavailable_reason"] = "semantic query measurement unavailable"
        return floor
    floor["available"] = True
    floor["dense_measured"] = dense_measured
    floor["metrics"] = {name: _aggregate_rankings(ranked, expected_sets, k)
                        for name, ranked in rankings.items()}
    return floor


def _unavailable(report: dict[str, Any], reason: str) -> dict[str, Any]:
    report["available"] = False
    report["unavailable_reason"] = reason
    return report


def run_curated(root: Path, k: int = DEFAULT_K, *, index: Any = None,
                query_set_version: int | None = None) -> dict[str, Any]:
    """Score the frozen situation-language query set against baseline arms.

    Aggregate-only: no query text, record bodies, summaries, memory ids,
    target refs or case ids enter the report. Nonqualifying by contract; the
    report states no verdict. ``index`` is the shared handler index; with
    ``None`` a ``WaveIndex(root)`` is constructed (CLI path).
    """
    import server_impl as srv
    import wf_server.memory_handlers as memory_handlers
    mem = srv._memory_mod()
    surfaced = mem.load_memory_records(root, statuses=list(mem.DEFAULT_SURFACED_STATUSES))
    register = mem.load_archive_register_entries(root)
    corpus = surfaced + register
    sample_pool = [record for record in surfaced
                   if record.get("target_refs") and record.get("summary")]
    selected = sorted(sample_pool, key=lambda record: (
        hashlib.sha256(record["memory_id"].encode("utf-8")).hexdigest(),
        record["memory_id"]))[:CURATED_SAMPLE_CAP]
    report: dict[str, Any] = {
        "available": False,
        "evaluation_kind": "situation_query_baselines",
        "qualifying": False,
        "production_variant": "memory_search_hybrid_rrf",
        "experimental_variant": "policy_ordered_rrf_shortlist5",
        "baseline_variant": "legacy_policy_ordering",
        "headline_variant": "production",
        "headline_split": "heldout",
        "adoption_gate": {
            "adopt": False, "product_path_changed": False,
            "reasons": ["independent_full_corpus_holdout_required"],
        },
        "counts_by_kind": dict(sorted(Counter(r["kind"] for r in sample_pool).items())),
        "counts_by_status": dict(sorted(Counter(r["status"] for r in sample_pool).items())),
        "embedded_text": dict(EMBEDDED_TEXT),
    }
    state = load_query_set(root, query_set_version)
    report["query_set"] = {"available": state["available"], "reason": state["reason"],
                           "sha256": state["sha256"], "version": state["version"]}
    # Change 246to: model-free counts, reported whether or not the model or
    # the query set is available.
    report["maintenance_signals"] = maintenance_signals(root, state)
    if state["reason"] in ("query_set_invalid", "query_set_hash_mismatch",
                           "query_set_unfrozen", "query_set_lock_invalid"):
        return _unavailable(report, state["reason"])
    if not selected and not state["available"]:
        return _unavailable(report, "no surfaced records with targets and summaries")
    try:
        if index is None:
            index = srv.WaveIndex(root)
        # Wave 248lb: load inside a read snapshot, so an eval that starts
        # during an index build serves the last published rows.
        with srv._load_script("sqlite_vector_store").read_snapshot(index.index_dir):
            index._ensure_loaded()
        if getattr(index, "_docs_vector_layer", None) is None:
            return _unavailable(report, "semantic docs layer unavailable")
    except Exception as exc:
        return _unavailable(report, f"semantic index unavailable: {type(exc).__name__}")

    report["sanity_floor"] = _sanity_floor(srv, root, index, selected, k)

    try:
        body_paths, expected_hashes = mem.memory_body_paths(root, surfaced)
    except Exception:
        return _unavailable(report, "dense query measurement unavailable")
    signals: dict[str, Any] = {"memory_vector_coverage": None}
    try:
        store = srv._load_script("sqlite_vector_store")
        signals["memory_vector_coverage"] = store.memory_vector_coverage(
            index.index_dir, "docs", expected_hashes)
    except Exception:
        signals["coverage_unavailable_reason"] = "index store unreadable"
    try:
        signals["target_retrievable"] = target_retrievable(root, surfaced, index, mem)
    except Exception:
        return _unavailable(report, "target retrievability measurement unavailable")
    signals["target_retrievable_note"] = (
        "retrievable is a sanity check (the uncapped predicate matches nearly "
        "every record); crowded_past_search_cap is the signal")
    report["index_signals"] = signals

    if not state["available"]:
        report["production_measured"] = False
        report["production_unavailable_reason"] = "query_set_unavailable"
        report["available"] = bool(report["sanity_floor"].get("available"))
        if not report["available"]:
            report["unavailable_reason"] = report["sanity_floor"].get("unavailable_reason")
        return report

    summaries = {record["memory_id"]: str(record.get("summary") or "") for record in corpus}
    cosine_rejected = set(state["lock"].get("cosine_rejected") or [])
    scored: list[dict[str, Any]] = []
    leakage = cosine = 0
    for case in state["cases"]:
        if case["id"] in cosine_rejected:
            cosine += 1
        elif sequence_leaks(case, summaries):
            leakage += 1
        else:
            scored.append(case)
    report["query_set"].update(
        cases=len(state["cases"]), scored=len(scored),
        leakage_rejected=leakage, cosine_rejected=cosine,
        **{f"{case_type}_cases": sum(1 for c in scored if c["case_type"] == case_type)
           for case_type in CASE_TYPES})
    if not scored:
        return _unavailable(report, "query set has no scored cases")

    search_cap, check_cap = _production_caps()
    texts = _corpus_texts(root, corpus)
    full = sorted(record["memory_id"] for record in corpus)
    outcomes: dict[str, list[tuple[list[str], list[str]]]] = {
        arm: [] for arm in (*ARMS, *ABLATION_ARMS)}
    production = {"model_screened_probes": 0, "fallback_probes": 0}
    fallback_reasons: Counter = Counter()
    dense_reason: str | None = None
    try:
        ablations = {
            "dense_summary_only": _Ablation(index, surfaced,
                                            [str(r.get("summary") or "") for r in surfaced]),
            "dense_compact": _Ablation(index, surfaced, [_compact_text(r) for r in surfaced]),
        }
    except Exception:
        return _unavailable(report, "dense_summary_only query measurement unavailable")
    for case in scored:
        query = case["query"]
        lexical = lexical_bm25_order(corpus, query)
        outcomes["no_memory"].append(([], []))
        outcomes["full_context"].append((full, full))
        try:
            matched = grep_order(texts, case["grep_terms"])
        except Exception:
            return _unavailable(report, "grep query measurement unavailable")
        outcomes["grep"].append((matched, matched))
        bm25 = lexical[:check_cap]
        outcomes["bm25_only"].append((bm25, bm25))
        try:
            semantic, reason = dense_stream(index, query, body_paths, expected_hashes)
        except Exception:
            return _unavailable(report, "dense query measurement unavailable")
        if semantic is None:
            dense_reason = dense_reason or reason
            semantic = []
        dense = semantic[:check_cap]
        hybrid = reciprocal_rank_fusion([semantic, lexical[:search_cap]])[:check_cap]
        outcomes["dense_only"].append((dense, dense))
        outcomes["hybrid_no_rerank"].append((hybrid, hybrid))
        try:
            response = memory_handlers.memory_search_response(
                root, query=query, index=index, limit=check_cap)
            data = response["data"]
            shown = [row["memory_id"] for row in data.get("records") or []]
            retrieval = data.get("retrieval") or {}
        except Exception:
            return _unavailable(report, "production query measurement unavailable")
        if retrieval.get("qualification") == "model_relevance":
            production["model_screened_probes"] += 1
        else:
            production["fallback_probes"] += 1
            fallback_reasons[str(retrieval.get("fallback_reason"))] += 1
        outcomes["production"].append((shown, shown))
        for arm, ablation in ablations.items():
            try:
                ranked = ablation.order(query, check_cap)
            except Exception:
                return _unavailable(report, f"{arm} query measurement unavailable")
            outcomes[arm].append((ranked, ranked))

    production["fallback_reasons"] = dict(sorted(fallback_reasons.items()))
    report["production_retrieval"] = production
    report["production_measured"] = production["fallback_probes"] == 0
    if not report["production_measured"]:
        del outcomes["production"]
        report["production_unavailable_reason"] = "production_path_fell_back"
    report["dense_measured"] = dense_reason is None
    if dense_reason is not None:
        # Council carry-forward 2: a stale or incomplete index is not a measured
        # dense result, the same rule as the production arm.
        for arm in ("dense_only", "hybrid_no_rerank"):
            del outcomes[arm]
        report["dense_unavailable_reason"] = dense_reason
    scoring = score_arms(scored, outcomes)
    report["metrics"] = scoring["metrics"]
    report["arm_order"] = scoring["arm_order"]
    report["split_counts"] = scoring["split_counts"]
    report["recall_key"] = {"default": "recall_at_5", "full_context": FULL_CONTEXT_RECALL_KEY}
    mean_chars = {"dense_only": round(
        sum(len(t) for mid, t in texts.items() if mid in set(body_paths.values()))
        / max(len(body_paths), 1), 1)}
    mean_chars.update({arm: ablation.mean_chars for arm, ablation in ablations.items()})
    report["embedded_text_mean_chars"] = mean_chars
    report["embedded_text_preferred"] = embedded_text_preferred(
        scoring["metrics"].get("heldout", {}), mean_chars)
    report["embedded_text_note"] = EMBEDDED_TEXT_NOTE
    report["available"] = True
    return report


def embedded_text_preferred(heldout: dict[str, Any], mean_chars: dict[str, float]) -> str | None:
    """Highest held-out recall@5 among the dense text arms; ties to the shortest text."""
    candidates = [(heldout[arm]["recall_at_5"], arm)
                  for arm in ("dense_only", *ABLATION_ARMS)
                  if arm in heldout and heldout[arm].get("recall_at_5") is not None]
    if not candidates:
        return None
    best = max(value for value, _arm in candidates)
    tied = [arm for value, arm in candidates if round(value, 4) == round(best, 4)]
    return min(tied, key=lambda arm: (mean_chars.get(arm, float("inf")), arm))


def _default_freeze_embedder(root: Path):
    """Return ``(docs_model, embed_queries, embed_documents)`` from the docs model."""
    import server_impl as srv
    index = srv.WaveIndex(root)
    model = index._indexer_constant("DOCS_MODEL")
    embedder = index._get_embedder(model)

    def queries(texts: list[str]) -> list[Any]:
        return [index._embed_query(text, model) for text in texts]

    def documents(texts: list[str]) -> list[Any]:
        return list(embedder.embed(texts))

    return model, queries, documents


def _cosine(a: Any, b: Any) -> float:
    a, b = [float(x) for x in a], [float(x) for x in b]
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


class ParentQuerySetMismatch(ValueError):
    """The parent version's query set does not match its own lock."""


PARENT_MISMATCH_MESSAGE = "parent query set does not match its lock"


def freeze_query_set(root: Path, *, embedder: Any = None, version: int = 1) -> dict[str, Any]:
    """Apply both leakage filters and write the lock; the query file is unchanged.

    ``embedder`` is ``(docs_model, embed_queries, embed_documents)``. Any
    embedding failure raises ``FreezeModelUnavailable`` before a lock exists.
    For ``version`` N of 2 or more (change 246to) the parent N-1 set must
    match its own lock, else ``ParentQuerySetMismatch`` is raised and nothing
    is written; the lock adds ``version``, ``parent_version``,
    ``parent_query_set_sha256`` and the sorted ``added_case_ids`` and
    ``removed_case_ids`` against the parent, by case id.
    """
    import server_impl as srv
    mem = srv._memory_mod()
    version = int(version)
    set_rel, lock_rel = query_set_paths(version)
    lineage: dict[str, Any] = {}
    if version >= 2:
        parent_set, parent_lock = query_set_paths(version - 1)
        try:
            parent_payload = json.loads((root / parent_set).read_text(encoding="utf-8"))
            parent_lock_data = json.loads((root / parent_lock).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ParentQuerySetMismatch(PARENT_MISMATCH_MESSAGE) from exc
        parent_sha = query_set_sha256(parent_payload)
        if not isinstance(parent_lock_data, dict) or parent_lock_data.get("query_set_sha256") != parent_sha:
            raise ParentQuerySetMismatch(PARENT_MISMATCH_MESSAGE)
        parent_cases = parent_payload.get("cases") if isinstance(parent_payload, dict) else None
        parent_ids = {case.get("id") for case in parent_cases or [] if isinstance(case, dict)}
        lineage = {"parent_ids": parent_ids, "parent_sha": parent_sha}
    payload = json.loads((root / set_rel).read_text(encoding="utf-8"))
    cases, reason = validate_query_set(payload)
    if cases is None:
        raise ValueError(reason)
    corpus = (mem.load_memory_records(root, statuses=list(mem.DEFAULT_SURFACED_STATUSES))
              + mem.load_archive_register_entries(root))
    summaries = {record["memory_id"]: str(record.get("summary") or "") for record in corpus}
    sequence_rejected = sorted(case["id"] for case in cases if sequence_leaks(case, summaries))
    probes = [(case, [summaries[mid] for mid in case["relevant_ids"] if summaries.get(mid)])
              for case in cases]
    probes = [(case, texts) for case, texts in probes if texts]
    try:
        model, embed_queries, embed_documents = (
            embedder if embedder is not None else _default_freeze_embedder(root))
        query_vectors = embed_queries([case["query"] for case, _texts in probes])
        unique = sorted({text for _case, texts in probes for text in texts})
        document_vectors = dict(zip(unique, embed_documents(unique)))
    except Exception as exc:
        raise FreezeModelUnavailable(FREEZE_MODEL_MESSAGE) from exc
    cosine_rejected = sorted(
        case["id"] for (case, texts), vector in zip(probes, query_vectors)
        if max(_cosine(vector, document_vectors[text]) for text in texts) >= COSINE_THRESHOLD
    )
    lock = {
        "schema_version": 1,
        "query_set_sha256": query_set_sha256(payload),
        "docs_model": model,
        "sequence_ratio_threshold": SEQUENCE_RATIO_THRESHOLD,
        "cosine_threshold": COSINE_THRESHOLD,
        "case_count": len(cases),
        "sequence_rejected": sequence_rejected,
        "cosine_rejected": cosine_rejected,
    }
    if lineage:
        ids = {case["id"] for case in cases}
        lock.update({
            "version": version,
            "parent_version": version - 1,
            "parent_query_set_sha256": lineage["parent_sha"],
            "added_case_ids": sorted(ids - lineage["parent_ids"]),
            "removed_case_ids": sorted(lineage["parent_ids"] - ids),
        })
    import line_endings
    (root / lock_rel).write_bytes(
        line_endings.encode(json.dumps(lock, indent=2, ensure_ascii=False) + "\n"))
    return lock


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--curated-root", type=Path)
    ap.add_argument("--freeze-query-set", type=Path, metavar="ROOT",
                    help="apply both leakage filters and write the query-set lock")
    ap.add_argument("--query-set-version", type=int, metavar="N",
                    help="query set version to freeze or score (default: freeze 1, "
                         "score the highest frozen version)")
    ap.add_argument("--uncoverable-records", type=Path, metavar="ROOT",
                    help="print, as JSON, the active records the frozen query set cannot cover")
    args = ap.parse_args(argv)
    if args.query_set_version is not None and args.query_set_version < 1:
        print("--query-set-version must be 1 or more", file=sys.stderr)
        return 2
    if args.uncoverable_records:
        root = args.uncoverable_records.resolve()
        print(json.dumps(uncoverable_records(
            root, load_query_set(root, args.query_set_version)), indent=2))
        return 0
    if args.freeze_query_set:
        try:
            lock = freeze_query_set(args.freeze_query_set.resolve(),
                                    version=args.query_set_version or 1)
        except FreezeModelUnavailable:
            print(FREEZE_MODEL_MESSAGE, file=sys.stderr)
            return 2
        except ParentQuerySetMismatch:
            print(PARENT_MISMATCH_MESSAGE, file=sys.stderr)
            return 2
        except (OSError, ValueError) as exc:
            print(f"freeze failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        print(json.dumps({key: (len(value) if isinstance(value, list) else value)
                          for key, value in lock.items()}, indent=2))
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        (root / "docs" / "agents").mkdir(parents=True)
        report = run(root)
    if args.curated_root:
        report["curated"] = run_curated(args.curated_root.resolve(),
                                        query_set_version=args.query_set_version)
        # Change 246to: the top-level signals describe ROOT when one is named.
        report["maintenance_signals"] = report["curated"]["maintenance_signals"]
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
            floor = curated.get("sanity_floor") or {}
            print(
                "curated:",
                "available" if curated["available"] else curated["unavailable_reason"],
                f"arm_order={curated.get('arm_order', {}).get('heldout')}",
                f"sanity_floor_sample={floor.get('sample_size')}",
            )
    ov = report["overall"]
    return 0 if ov["invariants_passed"] == ov["invariants_total"] else 1


if __name__ == "__main__":
    sys.exit(main())
