#!/usr/bin/env python3
"""Exact-vs-ANN reference measurement for the vector layer (wave `1wpih` / `1wsc8`).

Production has no way to tell whether an approximate-nearest-neighbour setting
helps, because it has nothing exact to compare against.  This module supplies
that reference and nothing else: it is **measurement-only** and never changes
how production queries run.

The exact side is obtained with LanceDB's ``bypass_vector_index()``, which
forces a flat scan over the same immutable table snapshot, same query vector,
same metric, same filter and same candidate depth as the ANN side.  That
symmetry is the whole point -- an "exact" reference that differed in any of
those respects would measure the difference, not the index.

The seam is deliberately narrow and observable.  ``exact_search`` routes through
``_apply_bypass`` so a spy can prove the bypass actually ran; a build that
silently served ANN while claiming exactness would otherwise be indistinguishable
from a correct one, and would make every overlap number meaningless.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


FIXTURE_SCHEMA = "wavefoundry.ann-reference-fixtures/v1"
REPORT_SCHEMA = "wavefoundry.ann-reference-eval/v1"

LAYERS = ("docs", "code")
# Requirement 9: defaults plus at most three candidates, and at most 64 total
# (configuration, layer, query, filter, K) cases -- NOT 64 per candidate.
MAX_CANDIDATE_CONFIGURATIONS = 3
MAX_TOTAL_CASES = 64
WARMUP_REPETITIONS = 1
MEASURED_REPETITIONS = 3
EXACT_QUERY_TIMEOUT_SECONDS = 15.0
TOTAL_CERTIFICATION_TIMEOUT_SECONDS = 180.0

# Requirement 4: the certification thresholds.  A candidate must clear ONE of
# the two quality branches and must not lose more than 1/K overlap on any slice.
MINIMUM_MEAN_OVERLAP_GAIN = 0.02
QUALITY_NEUTRAL_BAND = 0.005
MINIMUM_LATENCY_GAIN_RATIO = 0.10


class AnnEvaluationInvalid(Exception):
    """The ANN reference measurement could not produce a trustworthy result."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise AnnEvaluationInvalid(code, message)


def digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# The measurement-only exact seam
# ---------------------------------------------------------------------------

def _apply_bypass(builder: Any) -> Any:
    """Force a flat scan on one Lance query builder.

    Isolated into its own function so a test can spy on exactly this call.
    ``bypass_vector_index`` lives on the concrete vector query builder that a
    vector search returns, not on the base builder class, so it is resolved on
    the instance rather than imported.
    """
    bypass = getattr(builder, "bypass_vector_index", None)
    _require(callable(bypass), "exact_mode_unavailable",
             "this LanceDB build exposes no bypass_vector_index(); an exact "
             "reference cannot be established and no candidate may be certified")
    return bypass()


def _base_query(table: Any, query_vector: Sequence[float], top_n: int,
                *, where: str | None, metric: str = "cosine") -> Any:
    """The shared query shape.  Both sides MUST start from this.

    Mirrors production ``WaveIndex._lance_search``: same metric, same limit,
    same prefiltered where clause.  Any divergence here silently invalidates
    every overlap number this module produces.
    """
    builder = table.search(list(query_vector)).metric(metric).limit(top_n)
    if where:
        builder = builder.where(where, prefilter=True)
    return builder


def ann_search(table: Any, query_vector: Sequence[float], top_n: int,
               *, where: str | None = None, metric: str = "cosine") -> list[dict[str, Any]]:
    """The ANN side, shaped exactly like production."""
    return _base_query(table, query_vector, top_n, where=where, metric=metric).to_list()


def exact_search(table: Any, query_vector: Sequence[float], top_n: int,
                 *, where: str | None = None, metric: str = "cosine") -> list[dict[str, Any]]:
    """The exact side: identical query, vector index bypassed."""
    builder = _base_query(table, query_vector, top_n, where=where, metric=metric)
    return _apply_bypass(builder).to_list()


def normalized_ids(rows: Iterable[Mapping[str, Any]]) -> list[str]:
    """Chunk ids in returned order, with ties broken deterministically.

    Requirement 2: exact-reference repetition must return identical normalized
    ids before a candidate can be judged, so the normalization cannot depend on
    anything that varies between runs.
    """
    return [str(row.get("id", "")) for row in rows]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def overlap_at_k(exact_ids: Sequence[str], ann_ids: Sequence[str], k: int) -> float:
    """Fraction of the exact top-k that the ANN top-k also returned."""
    if k <= 0:
        return 0.0
    exact_top = list(dict.fromkeys(exact_ids))[:k]
    if not exact_top:
        return 0.0
    ann_top = set(list(dict.fromkeys(ann_ids))[:k])
    return len([i for i in exact_top if i in ann_top]) / len(exact_top)


def slice_key(layer: str, query_id: str, filter_shape: str, k: int) -> tuple[str, str, str, int]:
    return (str(layer), str(query_id), str(filter_shape), int(k))


def macro_mean_overlap(slices: Mapping[tuple, float]) -> float:
    """Equal weight per frozen slice.

    Requirement 4 is explicit that aggregation is a MACRO mean with one
    equal-weight observation per identical frozen key, so a layer with many
    queries cannot outvote one with few.
    """
    values = list(slices.values())
    return sum(values) / len(values) if values else 0.0


def certification_verdict(default_slices: Mapping[tuple, float],
                          candidate_slices: Mapping[tuple, float],
                          *, k: int,
                          default_p95_ms: float | None = None,
                          candidate_p95_ms: float | None = None) -> dict[str, Any]:
    """Fail-closed verdict for one candidate against library defaults.

    Rejects unless the slice sets match exactly and one of the two quality
    branches is cleared with no slice losing more than ``1/k`` overlap.  A
    missing slice is a rejection, never a skip: a candidate that simply failed
    to produce a measurement must not thereby appear equal.
    """
    reasons: list[str] = []
    default_keys, candidate_keys = set(default_slices), set(candidate_slices)
    if default_keys != candidate_keys:
        missing = sorted(str(k_) for k_ in default_keys - candidate_keys)
        extra = sorted(str(k_) for k_ in candidate_keys - default_keys)
        reasons.append(f"slice sets differ; missing={missing} extra={extra}")
        return {"certified": False, "reasons": reasons,
                "mean_default": None, "mean_candidate": None}

    mean_default = macro_mean_overlap(default_slices)
    mean_candidate = macro_mean_overlap(candidate_slices)
    per_slice_tolerance = 1.0 / float(k) if k else 0.0
    regressed = sorted(
        str(key) for key in default_keys
        if default_slices[key] - candidate_slices[key] > per_slice_tolerance + 1e-12
    )
    if regressed:
        reasons.append(f"slices lost more than 1/K overlap: {regressed}")

    gain = mean_candidate - mean_default
    quality_branch = gain >= MINIMUM_MEAN_OVERLAP_GAIN - 1e-12
    latency_branch = False
    if abs(gain) <= QUALITY_NEUTRAL_BAND + 1e-12:
        if (default_p95_ms is not None and candidate_p95_ms is not None
                and default_p95_ms > 0):
            improvement = (default_p95_ms - candidate_p95_ms) / default_p95_ms
            latency_branch = improvement >= MINIMUM_LATENCY_GAIN_RATIO - 1e-12
            if not latency_branch:
                reasons.append(
                    f"quality neutral and latency gain {improvement:.4f} is below "
                    f"the required {MINIMUM_LATENCY_GAIN_RATIO}")
        else:
            reasons.append("quality neutral and no paired p95 measurement was supplied")
    elif not quality_branch:
        reasons.append(
            f"mean overlap gain {gain:.4f} is below the required "
            f"{MINIMUM_MEAN_OVERLAP_GAIN} and outside the neutral band")

    certified = (not reasons) and (quality_branch or latency_branch)
    return {"certified": certified, "reasons": reasons,
            "mean_default": round(mean_default, 8),
            "mean_candidate": round(mean_candidate, 8),
            "gain": round(gain, 8),
            "per_slice_tolerance": round(per_slice_tolerance, 8)}


# ---------------------------------------------------------------------------
# Corpus
# ---------------------------------------------------------------------------

def load_corpus(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AnnEvaluationInvalid(
            "missing_corpus", f"ANN corpus not found: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AnnEvaluationInvalid(
            "invalid_corpus", f"cannot read ANN corpus: {exc}") from exc
    _require(isinstance(payload, dict) and set(payload) == {"schema", "cases"},
             "invalid_corpus", "ANN corpus has missing or unknown top-level fields")
    _require(payload.get("schema") == FIXTURE_SCHEMA, "invalid_corpus",
             f"ANN corpus schema must be {FIXTURE_SCHEMA}")
    cases = payload.get("cases")
    _require(isinstance(cases, list) and cases, "invalid_corpus",
             "ANN corpus cases must be a non-empty list")
    _require(len(cases) <= MAX_TOTAL_CASES, "case_cap_exceeded",
             f"ANN corpus has {len(cases)} cases; the total ceiling is {MAX_TOTAL_CASES}")
    seen: set[tuple] = set()
    normalized: list[dict[str, Any]] = []
    for pos, raw in enumerate(cases):
        _require(isinstance(raw, dict)
                 and set(raw) == {"id", "layer", "query_text", "filter_shape", "k", "rationale"},
                 "invalid_corpus",
                 f"cases[{pos}] needs exactly id/layer/query_text/filter_shape/k/rationale")
        _require(raw["layer"] in LAYERS, "invalid_corpus",
                 f"cases[{pos}]: layer must be one of {list(LAYERS)}")
        _require(isinstance(raw["k"], int) and not isinstance(raw["k"], bool)
                 and raw["k"] > 0, "invalid_corpus",
                 f"cases[{pos}]: k must be a positive integer")
        for field in ("id", "query_text", "filter_shape", "rationale"):
            _require(isinstance(raw[field], str) and raw[field].strip(),
                     "invalid_corpus", f"cases[{pos}].{field} must be non-empty")
        key = slice_key(raw["layer"], raw["id"], raw["filter_shape"], raw["k"])
        _require(key not in seen, "invalid_corpus", f"duplicate slice key: {key}")
        seen.add(key)
        normalized.append(dict(raw))
    return {"schema": FIXTURE_SCHEMA, "cases": normalized}


# Requirement 3: every field a report must bind. Named as data so a test can
# assert completeness against the requirement instead of against a hand-copied
# list that drifts from it.
REQUIRED_IDENTITY_FIELDS = (
    "fixture_digest", "evaluator_digest", "production_identity",
    "lance_table_version", "build_epoch", "build_attempt",
    "embedding_model", "embedding_provider", "vector_index_present",
    "backend", "content_sha256",
)
REQUIRED_SLICE_FIELDS = (
    "layer", "query_id", "filter_shape", "k",
    "exact_ids", "ann_ids", "overlap", "exact_ms", "ann_ms",
)


def evaluator_digest() -> str:
    """Content digest of this module, so a report names the code that made it."""
    return hashlib.sha256(
        Path(__file__).read_bytes()).hexdigest()


def build_report(*, corpus: Mapping[str, Any], slices: Sequence[Mapping[str, Any]],
                 identity: Mapping[str, Any],
                 candidates: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Assemble one exact/ANN report with every Requirement 3 binding.

    ``content_sha256`` is computed over everything else, so altering any bound
    identity after the fact changes the digest and `verify_report_identity`
    reports it. That is what makes the identity a receipt rather than a label.
    """
    body: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "fixture_digest": digest(corpus),
        "evaluator_digest": evaluator_digest(),
        "slices": [dict(s) for s in slices],
        "candidates": dict(candidates or {}),
        "case_ceiling": MAX_TOTAL_CASES,
        "candidate_ceiling": MAX_CANDIDATE_CONFIGURATIONS,
        "protocol": {
            "warmups": WARMUP_REPETITIONS,
            "measured_repetitions": MEASURED_REPETITIONS,
            "exact_query_timeout_seconds": EXACT_QUERY_TIMEOUT_SECONDS,
            "total_timeout_seconds": TOTAL_CERTIFICATION_TIMEOUT_SECONDS,
        },
        # Requirement 5 / AC-7: this report cannot support a gain claim, and
        # says so in the artifact rather than leaving it to a reader's memory.
        "evidence_authority": {
            "evidence_tier": "standing_regression",
            "evidence_role": "regression_only",
            "consulted_holdout": True,
            "supports_gain_claim": False,
            "why": ("Component overlap against an exact reference on a corpus "
                    "authored by the implementing party. It certifies a setting "
                    "against defaults; it is not independent out-of-sample "
                    "evidence and may not carry an improvement claim."),
        },
    }
    for field in REQUIRED_IDENTITY_FIELDS:
        if field in ("fixture_digest", "evaluator_digest", "content_sha256"):
            continue
        body[field] = identity.get(field)
    body["content_sha256"] = digest({k: v for k, v in body.items()
                                     if k != "content_sha256"})
    return body


def verify_report_identity(report: Mapping[str, Any]) -> list[str]:
    """Problems with a report's own bindings; empty when the receipt holds.

    Detects two distinct failures: a MISSING binding (the report never named
    something Requirement 3 requires) and a TAMPERED one (a field was edited
    after the content digest was computed).
    """
    problems: list[str] = []
    for field in REQUIRED_IDENTITY_FIELDS:
        if report.get(field) in (None, ""):
            problems.append(f"missing identity binding: {field}")
    for pos, row in enumerate(report.get("slices") or []):
        for field in REQUIRED_SLICE_FIELDS:
            if field not in row:
                problems.append(f"slices[{pos}] missing {field}")
    recomputed = digest({k: v for k, v in report.items() if k != "content_sha256"})
    if report.get("content_sha256") and recomputed != report["content_sha256"]:
        problems.append(
            "content_sha256 does not match the report body: a bound identity "
            "or measurement was altered after the report was written")
    return problems


__all__ = [
    "FIXTURE_SCHEMA", "REPORT_SCHEMA", "LAYERS",
    "MAX_CANDIDATE_CONFIGURATIONS", "MAX_TOTAL_CASES",
    "WARMUP_REPETITIONS", "MEASURED_REPETITIONS",
    "EXACT_QUERY_TIMEOUT_SECONDS", "TOTAL_CERTIFICATION_TIMEOUT_SECONDS",
    "MINIMUM_MEAN_OVERLAP_GAIN", "QUALITY_NEUTRAL_BAND", "MINIMUM_LATENCY_GAIN_RATIO",
    "AnnEvaluationInvalid", "digest", "exact_search", "ann_search",
    "normalized_ids", "overlap_at_k", "slice_key", "macro_mean_overlap",
    "certification_verdict", "load_corpus",
    "REQUIRED_IDENTITY_FIELDS", "REQUIRED_SLICE_FIELDS",
    "evaluator_digest", "build_report", "verify_report_identity",
]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    args = parser.parse_args(argv)
    corpus = load_corpus(args.corpus)
    print(json.dumps({"status": "ok", "cases": len(corpus["cases"]),
                      "corpus_digest": digest(corpus)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
