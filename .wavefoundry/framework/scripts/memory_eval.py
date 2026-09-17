#!/usr/bin/env python3
"""Memory-retrieval policy and candidate evaluation.

Builds a synthetic memory corpus (memory_golden.json) in a throwaway repo, runs
the current ``memory_search`` path against golden fixtures, and compares it
with the legacy confidence-first lexical+semantic RRF control. The optional
curated diagnostic freezes a bounded sample of the live
corpus before scoring and emits aggregate metrics, counts, and a fingerprint
only — never memory bodies, summaries, or record ids.

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
        self._docs_vector_layer = "docs"

    def _ensure_loaded(self):
        return None

    def _memory_candidate_scores(self, query: str, paths: list[str], *,
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
    """Run a nonqualifying self-summary diagnostic with aggregate-only output."""
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
        "evaluation_kind": "sampled_self_summary_diagnostic",
        "qualifying": False,
        "production_variant": "memory_rrf_summary5",
        "baseline_variant": "legacy_policy_ordering",
        "experimental_variant": "policy_ordered_rrf",
        "adoption_gate": {
            "adopt": False, "product_path_changed": False,
            "reasons": ["independent_full_corpus_holdout_required"],
        },
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
        if getattr(index, "_docs_vector_layer", None) is None:
            report["unavailable_reason"] = "semantic docs layer unavailable"
            return report
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
        try:
            semantic = [
                memory_id
                for memory_id in _semantic_order(index, query, mem.MEMORY_DIR)
                if memory_id in selected_ids
            ]
        except Exception:
            # Model/query failures are unavailable observations, not successful
            # abstention; exception messages can contain private query text.
            report["unavailable_reason"] = "semantic query measurement unavailable"
            return report
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
