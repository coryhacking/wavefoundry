#!/usr/bin/env python3
"""Production-path golden-query retrieval evaluation.

This runner is intentionally outside ``run_tests.py``: it reads a built local
Lance/FTS index and the locally cached embedding/reranking models.  It creates a
``WaveIndex`` directly (never ``ImplHandler``), so no background monitors are
started, and invokes the same response functions used by the MCP tools.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import queue
import re
import shutil
import sqlite3
import stat
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


REPORT_SCHEMA = "wavefoundry.retrieval-eval/v1"
# Wave 1wscp: v2 adds the four mandatory evidence-authority fields
# (evidence_role, authorship_class, consultation_status, mechanism_exposure).
# Adding required fields is incompatible, so v1 corpora must be annotated
# rather than silently accepted with their authority unstated.
FIXTURE_SCHEMA = "wavefoundry.retrieval-eval-fixtures/v2"
TOOLS = ("code_ask", "code_search", "docs_search", "code_lexical")
SPLITS = ("calibration", "holdout")
ANCHOR_TYPES = ("symbol", "content", "section", "line_span", "path")
QUESTION_TYPES = (
    "navigational", "explanatory", "instructional", "artifact_anchored", "assessment",
)

# Wave 1wscp (requirement 2): evidence authority.  Closed wave 1seaw showed a
# green aggregate verdict can coexist with consulted holdouts presented as
# improvement evidence, so gain eligibility is DERIVED from these four fields
# rather than trusted from the ``evidence_role`` label.
EVIDENCE_ROLES = ("calibration", "independent_holdout", "regression_only")
AUTHORSHIP_CLASSES = ("independent_reviewer", "qa_local", "implementer", "historical")
CONSULTATION_STATUSES = ("unconsulted", "consulted", "unknown")
MECHANISM_EXPOSURES = ("unexposed", "exposed", "unknown")
# The ONLY combination that may support ``minimum_improvement``.  Each element
# is the required value of the correspondingly named field; any other
# combination is non-regression-only.
GAIN_ELIGIBLE_COMBINATION = {
    "evidence_role": "independent_holdout",
    "authorship_class": "independent_reviewer",
    "consultation_status": "unconsulted",
    "mechanism_exposure": "unexposed",
}
EVIDENCE_FIELD_VOCABULARIES = {
    "evidence_role": EVIDENCE_ROLES,
    "authorship_class": AUTHORSHIP_CLASSES,
    "consultation_status": CONSULTATION_STATUSES,
    "mechanism_exposure": MECHANISM_EXPOSURES,
}

MAX_FIXTURES = 48
MAX_QUERY_BYTES = 512
MEASURED_REPETITIONS = 3
TOTAL_TIMEOUT_SECONDS = 20 * 60
CALL_TIMEOUT_SECONDS = {
    "code_ask": 30.0,
    "code_search": 15.0,
    "docs_search": 15.0,
    "code_lexical": 5.0,
}
OPERATOR_REVIEW_P95_MS = {
    "code_ask": 5_000.0,
    "code_search": 3_000.0,
    "docs_search": 3_000.0,
    "code_lexical": 1_000.0,
}
OPERATOR_REVIEW_RESPONSE_BYTES = 256 * 1024
# Wave 1wur7 (1wuuh): a same-generation pair's run-to-run jitter is derived from
# the warm-sample FLOOR and MEDIAN, not from ``warm_p95_ms`` alone.  A pair
# whose sample FLOOR or MEDIAN moves by more than this ratio was measured under
# external load and cannot stand as a promotable baseline.  The value is read
# off recorded evidence rather than fitted: the quiet pairs on file
# (``retrieval-quality-baseline``, ``retrieval-quality-before-1seas``) top out at
# 1.72% floor and 1.64% median jitter across all four tools, while the contended
# wave-1wpif pair runs 11.27% to 36.71%, so anything in the 3%-10% band separates
# them with margin on both sides.  The p95 component is deliberately NOT part of
# this gate: the quiet ``before-1seas`` pair shows 10.70% p95 jitter on
# ``code_lexical`` with a 0.74% floor, which is tail noise rather than contention.
PAIR_JITTER_THRESHOLD = 0.05
# The standing minimum warm-sample count across the applicable-tool matrix.
# ``docs_search`` has exactly three applicable fixtures, so it contributes
# 3 * MEASURED_REPETITIONS = 9 warm samples on every run and can never exceed
# that with the frozen corpus.  The declared minimum is therefore pinned AT that
# standing count: a tool below it is labelled and routed to operator review, and
# ``docs_search`` at exactly nine is not escalated, because escalating a value
# the corpus makes permanent would put a clean ``pass`` permanently out of reach.
MIN_WARM_SAMPLES = 3 * MEASURED_REPETITIONS
# Wave 1wur7 (1wtpl): index identity is compared per comparison kind.  The
# repository, index directory, and store path bind every comparison; the state
# store's own device/inode binds only a same-generation pair, where "one frozen
# physical store" is what makes the jitter measurement mean anything.  A
# controlled rebuild recreates that file, and refusing a cross-generation
# comparison for it refuses the exact case the kind exists to cover.
CROSS_GENERATION_INDEX_IDENTITY_KEYS = (
    "repository_root", "repository_device", "repository_inode",
    "index_directory", "state_store",
)
SAME_GENERATION_INDEX_IDENTITY_KEYS = CROSS_GENERATION_INDEX_IDENTITY_KEYS + (
    "state_store_device", "state_store_inode",
)
RECALL_K = 10
QUALITY_METRICS = (
    "recall_at_10", "ndcg_at_10", "agentic_mrr_at_10",
    "abstention_accuracy", "question_type_accuracy",
)
FIXTURE_QUALITY_GATE_METRICS = (
    "recall_at_10", "ndcg_at_10", "mrr_at_10",
    "abstention_accuracy", "question_type_accuracy",
)
# Whole-file summary chunks span every declaration in their file, so they can
# never stand as declaration evidence for a symbol anchor.
SUMMARY_RESULT_KINDS = frozenset({"code-summary", "doc-summary"})
# Production retrieval modules whose bytes bind a report to the retrieval
# implementation that produced it. The evaluator records its own identity
# separately (``evaluator_identity``); a comparison across two production
# identities is a before/after receipt, never a same-generation jitter pair.
# Wave 1wpig (1wpaj Requirement 8): ``graph_cluster.py`` joins the set. The
# clusters artifact carries the communities and the betweenness ranking that
# ``wf_graph_report`` serves, so a cluster-module or cluster-version change
# moves what the measured public paths return and must move production identity.
PRODUCTION_RETRIEVAL_MODULES = (
    "server_impl.py", "indexer.py", "chunker.py", "index_state_store.py",
    "graph_indexer.py", "graph_query.py", "graph_cluster.py", "accel_embedder.py",
)
PRODUCTION_VERSION_CONSTANTS = {
    "chunker": ("chunker.py", "CHUNKER_VERSION"),
    "walker": ("indexer.py", "WALKER_VERSION"),
    "graph_builder": ("graph_indexer.py", "GRAPH_BUILDER_VERSION"),
    "cluster_builder": ("graph_cluster.py", "CLUSTER_BUILDER_VERSION"),
}
# Repository-relative home of the production retrieval modules (for the git binding).
PRODUCTION_MODULE_PREFIX = ".wavefoundry/framework/scripts/"
# Runtime kill switches read on the public retrieval paths. Byte-identical
# production modules behave differently under these, so a receipt records their
# effective state, a comparison refuses a pair that differs, and any active
# switch requires operator review (cycle-2 review, SEC-SEAT-1 / RED-DEL-3).
RETRIEVAL_TOGGLE_ENVS = (
    "WAVEFOUNDRY_DISABLE_LEXICAL_FUSION",
    "WAVEFOUNDRY_DISABLE_DRIFT_PARTITION",
    "WAVEFOUNDRY_ENABLE_DRIFT_PARTITION",
    "WAVEFOUNDRY_DISABLE_RERANKER",
    "WAVEFOUNDRY_DISABLE_GRAPH_QUERY_CACHE",
)
# Wave 1wpig (1wpaj Requirement 8): build/extraction tuning variables whose
# VALUES change what a rebuild produces and how long it takes.  They are
# deliberately NOT part of ``RETRIEVAL_TOGGLE_ENVS``: that set records presence
# as a boolean (two different centrality top-N settings would snapshot
# identically) and treats any set entry as an active quality toggle that routes
# the whole invocation to operator review.  ``WAVEFOUNDRY_MAX_TS_PARSE_BYTES``
# is assigned into the process environment by ``indexer`` during a build, so
# reading it as a toggle would make a clean verdict unreachable on any run that
# followed a build.  Each entry is ``(name, owning module file, module
# default)``; the default is the literal the owning module falls back to, and
# ``test_retrieval_eval`` pins every one of them against that module's source.
PRODUCTION_TUNING_ENVS = (
    ("WAVEFOUNDRY_GRAPH_BETWEENNESS_TOP_N", "graph_cluster.py", "200"),
    ("WAVEFOUNDRY_GRAPH_BETWEENNESS_EXACT_MAX_NODES", "graph_cluster.py", "25000"),
    ("WAVEFOUNDRY_GRAPH_BETWEENNESS_CUTOFF_MAX_NODES", "graph_cluster.py", "100000"),
    ("WAVEFOUNDRY_GRAPH_BETWEENNESS_CUTOFF", "graph_cluster.py", "6"),
    ("WAVEFOUNDRY_MAX_TS_PARSE_BYTES", "chunker.py", "2000000"),
    ("WAVEFOUNDRY_MAX_LINE_SCAN_BYTES", "graph_indexer.py", "5000000"),
    ("WAVEFOUNDRY_GRAPH_PARALLEL_THRESHOLD", "graph_indexer.py", "100"),
    # No module default: an unset worker count means "auto-scale by file count".
    ("WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS", "graph_indexer.py", None),
    ("WAVEFOUNDRY_GRAPH_PARALLEL_BACKEND", "graph_indexer.py", "threads"),
    ("WAVEFOUNDRY_GRAPH_PARALLEL_START_METHOD", "graph_indexer.py", "spawn"),
    # Wave 1wpaj delivery review: the SECOND variable `indexer` assigns into the
    # process environment during every build. It is the published form of the
    # `indexing.spec_aware_chunking` workflow setting and decides whether
    # spec files chunk per operation/definition or fall back to flat emission —
    # a chunk-set change, therefore a direct retrieval-result change. Its module
    # default is a boolean constant rather than a string literal in the env read,
    # so the declared default is None and the drift test pins the constant.
    ("WAVEFOUNDRY_SPEC_CHUNKING", "chunker.py", None),
)
# Frozen at IMPORT, before this process can run (or import a module that runs)
# an index build.  ``indexer`` manages BOTH ``WAVEFOUNDRY_MAX_TS_PARSE_BYTES`` and
# ``WAVEFOUNDRY_SPEC_CHUNKING`` in ``os.environ`` while building (the second is
# assigned when a workflow override is present and popped otherwise), so resolving against the live environment would
# hand two invocations of the same evaluator different snapshots and fail the
# hard equality gate outright.  The frozen mapping is what "never read back from
# whatever a previous build left in the environment" means in code.
_FROZEN_TUNING_ENVIRON: dict[str, str] = {
    name: os.environ[name] for name, _module, _default in PRODUCTION_TUNING_ENVS
    if name in os.environ
}


def _retrieval_toggles() -> dict[str, bool]:
    """Effective (set and non-empty) state of every retrieval kill switch."""
    return {name: bool(os.environ.get(name)) for name in RETRIEVAL_TOGGLE_ENVS}


def _production_tuning(environ: Mapping[str, str] | None = None) -> dict[str, str | None]:
    """Resolved VALUES of the declared build/extraction tuning variables.

    Resolution is identical on every invocation: the variable as it stood when
    the evaluator was imported, falling back to the owning module's default.  An
    empty value is treated as unset.

    That normalisation is the evaluator's OWN rule and deliberately does not
    mirror each reader: only two of the declared variables use the ``or
    DEFAULT`` form that agrees with it, several use ``get(name, default)`` which
    keeps an empty string, and the worker count is read by presence.  The
    purpose here is a stable, comparable identity string, not a simulation of
    production parsing — so this records what the operator SET, normalised one
    way, rather than what each reader derived.  Two consequences are accepted:
    a value differing from a reader's own normalisation (case, whitespace) is
    recorded verbatim and will refuse an otherwise-comparable pair, and an
    empty value is recorded as the declared default even where production would
    have seen the empty string.  Both fail toward refusing a comparison rather
    than accepting a false-clean one, which is the safe direction for a gate.
    """
    source = _FROZEN_TUNING_ENVIRON if environ is None else environ
    resolved: dict[str, str | None] = {}
    for name, _module, default in PRODUCTION_TUNING_ENVS:
        value = source.get(name)
        resolved[name] = str(value) if value else default
    return resolved


class EvaluationInvalid(RuntimeError):
    """The evaluation could not produce a trustworthy gate result."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


ADJUDICATION_SCHEMA = "wavefoundry.retrieval-adjudications/v1"
# Wave 1wscp (requirement 3).  A zero metric is not automatically a ranking
# defect: closed wave 1seaw showed zeros that were oracle errors, classifier
# contract mismatches, and contaminated carriers.  Each verdict names WHICH,
# so a later wave cannot treat every zero as a promised ranking fix.
ADJUDICATION_VERDICTS = (
    "confirmed_retrieval_miss",
    "oracle_anchor_miss",
    "classifier_contract_mismatch",
    "carrier_contaminated",
    "typed_surface_required",
    "intentional_limit",
)
# The metrics whose zero value demands an adjudication.  Scoped to the
# fixture-level gate metrics plus the two per-case correctness flags, because
# those are the ones a fixture-scope quality rule can be written against.
ADJUDICATED_METRICS = tuple(dict.fromkeys(
    FIXTURE_QUALITY_GATE_METRICS + ("abstention_accuracy", "question_type_accuracy")
))
_ADJUDICATION_REQUIRED_FIELDS = {
    "fixture_id", "tool", "metric", "run_id", "inspected_path",
    "anchor", "observed", "verdict", "rationale",
}


def load_adjudication_manifest(path: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Load the frozen adjudication receipts, keyed by ``(fixture, tool, metric)``.

    Wave 1wscp requirement 3.  Each receipt must inspect the claimed target and
    replay the public response; a fixture-wide label cannot stand in for
    tool/metric evidence, which is why the key is the exact triple.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvaluationInvalid(
            "missing_adjudications", f"adjudication manifest not found: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvaluationInvalid(
            "invalid_adjudication", f"cannot read adjudication manifest: {exc}") from exc
    _require(isinstance(payload, dict) and set(payload) == {"schema", "adjudications"},
             "invalid_adjudication", "adjudication manifest contains missing or unknown fields")
    _require(payload.get("schema") == ADJUDICATION_SCHEMA, "invalid_adjudication",
             f"adjudication schema must be {ADJUDICATION_SCHEMA}")
    rows = payload.get("adjudications")
    _require(isinstance(rows, list), "invalid_adjudication",
             "adjudications must be a list")
    receipts: dict[tuple[str, str, str], dict[str, Any]] = {}
    for pos, raw in enumerate(rows):
        _require(isinstance(raw, dict), "invalid_adjudication",
                 f"adjudications[{pos}] must be an object")
        _require(set(raw) == _ADJUDICATION_REQUIRED_FIELDS, "invalid_adjudication",
                 f"adjudications[{pos}] has missing or unknown fields; "
                 f"required exactly {sorted(_ADJUDICATION_REQUIRED_FIELDS)}")
        for field in ("fixture_id", "tool", "metric", "run_id", "inspected_path",
                      "observed", "rationale"):
            value = raw.get(field)
            _require(isinstance(value, str) and value.strip(), "invalid_adjudication",
                     f"adjudications[{pos}]: {field} must be a non-empty string")
        _require(raw.get("tool") in TOOLS, "invalid_adjudication",
                 f"adjudications[{pos}]: unsupported tool {raw.get('tool')!r}")
        _require(raw.get("metric") in ADJUDICATED_METRICS, "invalid_adjudication",
                 f"adjudications[{pos}]: unsupported metric {raw.get('metric')!r}")
        _require(raw.get("verdict") in ADJUDICATION_VERDICTS, "invalid_adjudication",
                 f"adjudications[{pos}]: verdict must be one of {list(ADJUDICATION_VERDICTS)}")
        anchor = raw.get("anchor")
        _require(isinstance(anchor, dict) and anchor.get("type") in ANCHOR_TYPES,
                 "invalid_adjudication",
                 f"adjudications[{pos}]: anchor must be a typed anchor object")
        key = (str(raw["fixture_id"]), str(raw["tool"]), str(raw["metric"]))
        _require(key not in receipts, "invalid_adjudication",
                 f"duplicate adjudication for {key}; exactly one receipt per triple")
        receipts[key] = dict(raw)
    return receipts


def adjudication_gaps(report: Mapping[str, Any],
                      receipts: Mapping[tuple[str, str, str], Any]) -> list[tuple[str, str, str]]:
    """Zero-scoring ``(fixture, tool, metric)`` triples carrying no receipt.

    Reads the report's own case rows rather than the aggregate metrics, so a
    class-level average cannot hide an unadjudicated zero underneath it.
    """
    gaps: list[tuple[str, str, str]] = []
    for row in report.get("cases", []) or []:
        if not isinstance(row, Mapping) or row.get("applicable") is not True:
            continue
        fixture_id, tool = str(row.get("fixture_id")), str(row.get("tool"))
        for metric in ADJUDICATED_METRICS:
            value = _case_metric_value(row, metric)
            if value is None or value > 0.0:
                continue
            key = (fixture_id, tool, metric)
            if key not in receipts:
                gaps.append(key)
    return sorted(set(gaps))


# Wave 1wscp (requirement 4): carrier contamination.  A result slot occupied by
# the evaluation apparatus itself -- its fixtures, its reports, the wave records
# that quote its queries -- is not neutral: it can displace the expected target
# or supply an apparent gain the product did not earn.
CARRIER_KINDS = (
    "evaluator_source", "fixture_source", "generated_report",
    "wave_record", "review_commentary",
)
APPROVAL_STATES = ("approved", "unapproved")
CARRIER_EFFECTS = ("none", "displaced_expected", "supplied_gain")
# Path shapes that identify each carrier kind.  Ordered most specific first so
# a fixture under a wave directory classifies as fixture_source, not wave_record.
_CARRIER_PATH_RULES: tuple[tuple[str, Callable[[str], bool]], ...] = (
    ("fixture_source", lambda p: p.startswith("docs/evals/")),
    ("generated_report", lambda p: p.startswith("docs/reports/")),
    ("evaluator_source", lambda p: (
        p.startswith(".wavefoundry/framework/scripts/") and p.endswith("_eval.py"))),
    ("review_commentary", lambda p: p.endswith("events.jsonl")),
    ("wave_record", lambda p: p.startswith("docs/waves/")),
)


def classify_carrier(path: str) -> str | None:
    """The carrier kind for one normalized result path, or ``None`` if ordinary.

    Ordinary product source and documentation are NOT carriers; only the
    evaluation apparatus is.  A path that is not part of that apparatus returns
    ``None`` so it consumes no contamination budget.
    """
    normalized = _normal_path(path)
    for kind, matches in _CARRIER_PATH_RULES:
        if matches(normalized):
            return kind
    return None


def carrier_rows(result_paths: Sequence[str], expected_paths: Sequence[str], *,
                 approved: Iterable[str] = (), top_k: int = RECALL_K) -> list[dict[str, Any]]:
    """Typed carrier rows for one case's top-k results.

    ``effect`` is derived from position rather than asserted: a carrier ranked
    above any expected path DISPLACED it; a carrier present when no expected
    path was returned at all SUPPLIED whatever gain the case shows.
    """
    approved_set = {_normal_path(p) for p in approved}
    expected = {_normal_path(p) for p in expected_paths}
    ranked = [_normal_path(p) for p in result_paths[:top_k]]
    expected_ranks = [i for i, p in enumerate(ranked) if p in expected]
    best_expected = expected_ranks[0] if expected_ranks else None
    rows: list[dict[str, Any]] = []
    for rank, path in enumerate(ranked):
        kind = classify_carrier(path)
        if kind is None:
            continue
        if best_expected is None:
            effect = "supplied_gain" if expected else "none"
        elif rank < best_expected:
            effect = "displaced_expected"
        else:
            effect = "none"
        rows.append({
            "carrier_kind": kind,
            "path": path,
            "rank": rank + 1,
            "approval_state": "approved" if path in approved_set else "unapproved",
            "effect": effect,
        })
    return rows


def carrier_contamination_violations(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Carrier rows that invalidate an improvement claim.

    An APPROVED carrier with a neutral effect is fine; the gate fires only when
    an unapproved carrier is present at all, or when any carrier displaced the
    expected evidence or supplied the apparent gain.
    """
    violations: list[dict[str, Any]] = []
    for row in rows:
        effect = row.get("effect")
        unapproved = row.get("approval_state") == "unapproved"
        if effect in ("displaced_expected", "supplied_gain"):
            violations.append({"kind": f"carrier_{effect}", **dict(row)})
        elif unapproved:
            violations.append({"kind": "unapproved_carrier_present", **dict(row)})
    return violations


def derive_gain_eligibility(fixture: Mapping[str, Any]) -> bool:
    """Whether one fixture may support a ``minimum_improvement`` claim.

    Wave 1wscp (requirement 2).  This is the SOLE authority for gain
    eligibility: callers must not read ``evidence_role`` and infer it, because
    the label alone cannot distinguish an genuinely independent holdout from a
    consulted fixture relabelled after the fact.  Eligibility requires all four
    independence conditions together; every other combination is
    non-regression-only.  ``_validate_evidence_authority`` separately REJECTS
    the incoherent case (a fixture claiming ``independent_holdout`` while
    carrying implementer authorship, consulted status, or mechanism exposure),
    so a false-independence mutant fails validation rather than silently
    deriving ``False`` here.
    """
    return all(
        fixture.get(field) == value
        for field, value in GAIN_ELIGIBLE_COMBINATION.items()
    )


def _validate_evidence_authority(raw: Mapping[str, Any], *, fixture_id: str) -> dict[str, str]:
    """Validate the four evidence-authority fields and reject false independence."""
    resolved: dict[str, str] = {}
    for field, vocabulary in EVIDENCE_FIELD_VOCABULARIES.items():
        value = raw.get(field)
        _require(isinstance(value, str) and value in vocabulary, "invalid_fixture",
                 f"{fixture_id}: {field} must be one of {list(vocabulary)}")
        resolved[field] = value
    # A fixture may only CLAIM independent-holdout authority when every other
    # independence field agrees.  Deriving False and continuing would let the
    # claim sit in the corpus unchallenged; the corpus must not contain it.
    if resolved["evidence_role"] == GAIN_ELIGIBLE_COMBINATION["evidence_role"]:
        conflicting = sorted(
            f"{field}={resolved[field]!r}"
            for field, value in GAIN_ELIGIBLE_COMBINATION.items()
            if field != "evidence_role" and resolved[field] != value
        )
        _require(not conflicting, "invalid_fixture",
                 f"{fixture_id}: evidence_role='independent_holdout' contradicts "
                 f"{', '.join(conflicting)}; independence cannot be asserted by label")
    return resolved


def _stable_json_bytes(value: Any, *, pretty: bool = False) -> bytes:
    kwargs: dict[str, Any] = {
        "ensure_ascii": False,
        "sort_keys": True,
        "allow_nan": False,
    }
    if pretty:
        kwargs["indent"] = 2
    else:
        kwargs["separators"] = (",", ":")
    return (json.dumps(value, **kwargs) + ("\n" if pretty else "")).encode("utf-8")


def _fixture_digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_stable_json_bytes(payload)).hexdigest()


def _normal_path(value: Any) -> str:
    normalized = str(value or "").replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise EvaluationInvalid(code, message)


def _validate_anchor(anchor: Any, *, fixture_id: str) -> dict[str, Any]:
    _require(isinstance(anchor, dict), "invalid_fixture", f"{fixture_id}: anchor must be an object")
    anchor_type = anchor.get("type")
    _require(anchor_type in ANCHOR_TYPES, "invalid_fixture",
             f"{fixture_id}: anchor.type must be one of {', '.join(ANCHOR_TYPES)}")
    if anchor_type in ("symbol", "content", "section"):
        _require(set(anchor) == {"type", "value"}, "invalid_fixture",
                 f"{fixture_id}: {anchor_type} anchor must contain only type/value")
        _require(isinstance(anchor.get("value"), str) and anchor["value"].strip(),
                 "invalid_fixture", f"{fixture_id}: {anchor_type} anchor value must be non-empty")
    elif anchor_type == "line_span":
        _require(set(anchor) == {"type", "start", "end"}, "invalid_fixture",
                 f"{fixture_id}: line_span anchor must contain only type/start/end")
        start, end = anchor.get("start"), anchor.get("end")
        _require(isinstance(start, int) and not isinstance(start, bool) and
                 isinstance(end, int) and not isinstance(end, bool) and 1 <= start <= end,
                 "invalid_fixture", f"{fixture_id}: invalid line_span anchor")
    else:
        _require(set(anchor) == {"type"}, "invalid_fixture",
                 f"{fixture_id}: path anchor must contain only type")
    return dict(anchor)


def _validate_relevance(value: Any, *, fixture_id: str, abstention: bool,
                        applicable_tools: Sequence[str]) -> list[dict[str, Any]]:
    _require(isinstance(value, list), "invalid_fixture", f"{fixture_id}: relevance must be a list")
    if not abstention:
        _require(bool(value), "invalid_fixture", f"{fixture_id}: non-abstention fixture needs relevance")
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for pos, entry in enumerate(value):
        _require(isinstance(entry, dict) and set(entry) >= {"path", "grade", "anchor"} and
                 not (set(entry) - {"path", "grade", "anchor", "tools"}),
                 "invalid_fixture", f"{fixture_id}: relevance[{pos}] has missing or unknown fields")
        path = _normal_path(entry.get("path"))
        grade = entry.get("grade")
        _require(path != "" and not path.startswith("../"), "invalid_fixture",
                 f"{fixture_id}: relevance[{pos}] has an invalid path")
        _require(isinstance(grade, (int, float)) and not isinstance(grade, bool) and
                 math.isfinite(float(grade)) and float(grade) > 0,
                 "invalid_fixture", f"{fixture_id}: relevance[{pos}] grade must be positive and finite")
        anchor = _validate_anchor(entry.get("anchor"), fixture_id=fixture_id)
        identity = (path, str(anchor.get("type")), json.dumps(anchor, sort_keys=True))
        _require(identity not in seen, "invalid_fixture", f"{fixture_id}: duplicate relevance target {identity}")
        seen.add(identity)
        item = {"path": path, "grade": float(grade), "anchor": anchor}
        if "tools" in entry:
            tools = entry.get("tools")
            _require(isinstance(tools, list) and tools and
                     all(isinstance(tool, str) and tool in applicable_tools for tool in tools) and
                     len(set(tools)) == len(tools), "invalid_fixture",
                     f"{fixture_id}: relevance[{pos}].tools must be a unique applicable-tool subset")
            item["tools"] = list(tools)
        normalized.append(item)
    if not abstention:
        missing_tools = [
            tool for tool in applicable_tools
            if not any(tool in target.get("tools", applicable_tools) for target in normalized)
        ]
        _require(not missing_tools, "invalid_fixture",
                 f"{fixture_id}: applicable tools lack relevance targets: {missing_tools}")
    return normalized


def _validate_quality_gate(value: Any, fixtures: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    _require(isinstance(value, dict) and set(value) == {"critical_floors"}, "invalid_fixture",
             "quality_gate must contain only critical_floors")
    rules = value.get("critical_floors")
    _require(isinstance(rules, list) and rules, "invalid_fixture",
             "quality_gate.critical_floors must be a non-empty list")
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for pos, raw in enumerate(rules):
        _require(isinstance(raw, dict), "invalid_fixture",
                 f"quality_gate.critical_floors[{pos}] must be an object")
        required = {"scope", "target", "tool", "metric", "floor"}
        optional = {"minimum_improvement"}
        _require(set(raw) >= required and not (set(raw) - required - optional), "invalid_fixture",
                 f"quality_gate.critical_floors[{pos}] has missing or unknown fields")
        scope = raw.get("scope")
        target = str(raw.get("target") or "").strip()
        tool = raw.get("tool")
        metric = raw.get("metric")
        floor = raw.get("floor")
        improvement = raw.get("minimum_improvement")
        _require(scope in ("fixture", "class") and target, "invalid_fixture",
                 f"quality_gate.critical_floors[{pos}] needs fixture/class scope and target")
        allowed_metrics = FIXTURE_QUALITY_GATE_METRICS if scope == "fixture" else QUALITY_METRICS
        _require(tool in TOOLS and metric in allowed_metrics, "invalid_fixture",
                 f"quality_gate.critical_floors[{pos}] has an unsupported tool or metric")
        _require(isinstance(floor, (int, float)) and not isinstance(floor, bool) and
                 math.isfinite(float(floor)) and 0.0 <= float(floor) <= 1.0,
                 "invalid_fixture", f"quality_gate.critical_floors[{pos}] floor must be in [0, 1]")
        _require(improvement is None or (
            isinstance(improvement, (int, float)) and not isinstance(improvement, bool) and
            math.isfinite(float(improvement)) and 0.0 < float(improvement) <= 1.0
        ), "invalid_fixture",
                 f"quality_gate.critical_floors[{pos}] minimum_improvement must be in (0, 1]")
        matching = [
            fixture for fixture in fixtures
            if fixture["split"] == "holdout" and tool in fixture["applicable_tools"] and
            (fixture["id"] == target if scope == "fixture" else fixture["class"] == target)
        ]
        _require(bool(matching), "invalid_fixture",
                 f"quality_gate.critical_floors[{pos}] target has no applicable holdout case")
        # Wave 1wscp requirement 2: derived eligibility is the SOLE authority
        # for a gain claim.  A floor is a non-regression assertion and any
        # evidence may carry it, but ``minimum_improvement`` asserts the system
        # got BETTER, and only genuinely independent evidence can say so.  This
        # fails closed at corpus load rather than at scoring time, so a corpus
        # that stakes a gain claim on consulted evidence never runs at all.
        if improvement is not None:
            ineligible = sorted(
                fixture["id"] for fixture in matching
                if not derive_gain_eligibility(fixture)
            )
            _require(not ineligible, "invalid_fixture",
                     f"quality_gate.critical_floors[{pos}] declares minimum_improvement on "
                     f"evidence that is not independently eligible: {ineligible}. Only "
                     "independent_holdout evidence from an unconsulted, unexposed "
                     "independent reviewer may support a gain claim; use a floor instead.")
        identity = (str(scope), target, str(tool), str(metric))
        _require(identity not in seen, "invalid_fixture",
                 f"duplicate quality gate rule: {identity}")
        seen.add(identity)
        rule = {"scope": scope, "target": target, "tool": tool,
                "metric": metric, "floor": float(floor)}
        if improvement is not None:
            rule["minimum_improvement"] = float(improvement)
        normalized.append(rule)
    return {"critical_floors": normalized}


def load_fixture_corpus(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvaluationInvalid("missing_corpus", f"fixture corpus not found: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvaluationInvalid("invalid_fixture", f"cannot read fixture corpus: {exc}") from exc
    _require(isinstance(payload, dict) and set(payload) >= {"schema", "fixtures"} and
             not (set(payload) - {"schema", "fixtures", "quality_gate"}),
             "invalid_fixture", "fixture corpus contains missing or unknown fields")
    _require(payload.get("schema") == FIXTURE_SCHEMA, "invalid_fixture",
             f"fixture schema must be {FIXTURE_SCHEMA}")
    fixtures = payload.get("fixtures")
    _require(isinstance(fixtures, list) and fixtures, "empty_corpus", "fixture corpus is empty")
    _require(len(fixtures) <= MAX_FIXTURES, "fixture_cap_exceeded",
             f"fixture corpus has {len(fixtures)} cases; maximum is {MAX_FIXTURES}")

    required = {"id", "class", "split", "query", "applicable_tools", "excluded_tools",
                "relevance", "provenance", "rationale",
                # Wave 1wscp requirement 2: evidence authority is mandatory on
                # every scored fixture, so a case cannot enter the corpus
                # without stating who wrote it and what it saw.
                "evidence_role", "authorship_class", "consultation_status",
                "mechanism_exposure"}
    optional = {"query_form", "expected_question_type", "abstention_expected"}
    normalized: list[dict[str, Any]] = []
    ids: set[str] = set()
    class_splits: dict[str, set[str]] = {}
    for pos, raw in enumerate(fixtures):
        _require(isinstance(raw, dict), "invalid_fixture", f"fixtures[{pos}] must be an object")
        fixture_id = str(raw.get("id") or "").strip()
        _require(set(raw) >= required and not (set(raw) - required - optional), "invalid_fixture",
                 f"{fixture_id or f'fixtures[{pos}]'}: missing or unknown fixture fields")
        _require(fixture_id != "" and fixture_id not in ids, "invalid_fixture",
                 f"duplicate or empty fixture id: {fixture_id!r}")
        ids.add(fixture_id)
        query = raw.get("query")
        _require(isinstance(query, str) and query.strip(), "invalid_fixture",
                 f"{fixture_id}: query must be a non-empty string")
        _require(len(query.encode("utf-8")) <= MAX_QUERY_BYTES, "query_cap_exceeded",
                 f"{fixture_id}: query exceeds {MAX_QUERY_BYTES} UTF-8 bytes")
        case_class = str(raw.get("class") or "").strip()
        split = raw.get("split")
        _require(case_class != "" and split in SPLITS, "invalid_fixture",
                 f"{fixture_id}: class must be non-empty and split must be calibration/holdout")
        class_splits.setdefault(case_class, set()).add(str(split))

        applicable = raw.get("applicable_tools")
        _require(isinstance(applicable, list) and applicable and
                 all(isinstance(v, str) and v in TOOLS for v in applicable) and
                 len(set(applicable)) == len(applicable), "invalid_fixture",
                 f"{fixture_id}: applicable_tools must be a unique non-empty subset of the public tools")
        excluded = raw.get("excluded_tools")
        omitted = set(TOOLS) - set(applicable)
        _require(isinstance(excluded, dict) and set(excluded) == omitted and
                 all(isinstance(v, str) and v.strip() for v in excluded.values()),
                 "invalid_fixture", f"{fixture_id}: excluded_tools must explain every and only omitted tool")
        abstention = raw.get("abstention_expected", False)
        _require(isinstance(abstention, bool), "invalid_fixture",
                 f"{fixture_id}: abstention_expected must be boolean")
        relevance = _validate_relevance(raw.get("relevance"), fixture_id=fixture_id,
                                        abstention=abstention, applicable_tools=applicable)
        if root is not None:
            missing = [r["path"] for r in relevance if not (root / r["path"]).is_file()]
            _require(not missing, "stale_corpus",
                     f"{fixture_id}: relevance paths do not exist in the current tree: {missing}")
        expected_type = raw.get("expected_question_type")
        _require(expected_type is None or expected_type in QUESTION_TYPES, "invalid_fixture",
                 f"{fixture_id}: unsupported expected_question_type {expected_type!r}")
        provenance = raw.get("provenance")
        _require((isinstance(provenance, str) and provenance.strip()) or
                 (isinstance(provenance, dict) and bool(provenance)), "invalid_fixture",
                 f"{fixture_id}: provenance must be a non-empty string or object")
        rationale = raw.get("rationale")
        _require(isinstance(rationale, str) and rationale.strip(), "invalid_fixture",
                 f"{fixture_id}: rationale must be non-empty")
        evidence = _validate_evidence_authority(raw, fixture_id=fixture_id)
        item = dict(raw)
        item["id"] = fixture_id
        item["class"] = case_class
        item["query"] = query.strip()
        item["applicable_tools"] = list(applicable)
        item["excluded_tools"] = dict(excluded)
        item["relevance"] = relevance
        item["abstention_expected"] = abstention
        item.update(evidence)
        # Derived, never read from the corpus: a fixture cannot declare itself
        # gain-eligible.  Recomputed here so every downstream consumer reads the
        # same authority rather than re-deriving it inconsistently.
        item["gain_eligible"] = derive_gain_eligibility(item)
        normalized.append(item)

    _require(len(class_splits) >= 9, "incomplete_corpus",
             f"fixture corpus has {len(class_splits)} classes; at least nine are required")
    incomplete = sorted(name for name, splits in class_splits.items() if splits != set(SPLITS))
    _require(not incomplete, "incomplete_corpus",
             f"every class must appear in calibration and holdout; incomplete: {incomplete}")
    abstentions = [f for f in normalized if f["abstention_expected"]]
    _require(len(abstentions) >= 2, "incomplete_corpus", "at least two abstention controls are required")
    agentic = [f for f in normalized if f["class"] == "agentic_fix_localization"]
    _require(len(agentic) >= 10, "incomplete_corpus",
             "at least ten agentic_fix_localization fixtures are required")
    for split in SPLITS:
        _require(sum(f["split"] == split for f in agentic) >= 5, "incomplete_corpus",
                 f"agentic_fix_localization requires at least five {split} fixtures")
    _require(sum(f.get("query_form") == "symptom_only" for f in agentic) >= math.ceil(len(agentic) / 2),
             "incomplete_corpus", "at least half of agentic fixtures must be symptom_only")
    corpus = {"schema": FIXTURE_SCHEMA, "fixtures": normalized}
    if "quality_gate" in payload:
        corpus["quality_gate"] = _validate_quality_gate(payload["quality_gate"], normalized)
    return corpus


def _path_under_root(path: Path, root: Path) -> str | None:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def assert_eval_artifacts_excluded(root: Path, paths: Sequence[Path], indexer: Any) -> None:
    patterns = indexer._load_ignore_patterns(root)
    known_text = set(indexer.SOURCE_CODE_EXTENSIONS) | set(indexer.DOCS_TEXT_EXTENSIONS) | {
        ".md", ".markdown", ".rst", ".adoc", ".asciidoc", ".drawio", ".excalidraw",
    }
    extensionless = set(indexer.DOCS_EXTENSIONLESS_NAMES) | set(indexer.CODE_EXTENSIONLESS_NAMES)
    for path in paths:
        rel = _path_under_root(path, root)
        if rel is None:
            continue
        eligible = path.suffix.lower() in known_text or path.name in extensionless
        ignored = indexer._matches_ignore(rel, patterns)
        _require(ignored or not eligible, "self_contaminating_artifact",
                 f"evaluation artifact could enter the retrieval corpus: {rel}; exclude it in .aiignore")


# ---------------------------------------------------------------------------
# Wave 1wpig (1wpaj Requirement 8): confined report I/O.
#
# Every baseline, output, and manifest path must be a REGULAR DIRECT CHILD of
# ``<root>/docs/reports`` whose basename begins with ``retrieval-quality-``.
# The prefix is part of the confinement rule rather than a naming convention:
# this repository's ignore rule is keyed on ``docs/reports/retrieval-quality-*.json``
# and ``.json`` is an indexed source extension, so a report written under any
# other basename enters the retrieval corpus and contaminates the NEXT
# invocation's own measurement.
# ---------------------------------------------------------------------------
REPORT_DIRECTORY_PARTS = ("docs", "reports")
REPORT_BASENAME_PREFIX = "retrieval-quality-"
# The publish temporary lives in the destination directory (``os.link`` cannot
# cross filesystems) and must satisfy the same prefix rule, or an interrupt
# between create and link leaves a partial report inside the retrieval corpus.
REPORT_TEMP_INFIX = "tmp-"
_REPORT_TEMP_RE = re.compile(
    rf"^{re.escape(REPORT_BASENAME_PREFIX + REPORT_TEMP_INFIX)}[0-9]+-[0-9a-f]{{32}}\.json$"
)
# Closed-``1seaw`` receipts. Named inline rather than by cross-reference,
# because this wave's own records name no report. They are protected INPUTS and
# can never be a destination.
PROTECTED_REPORT_PATHS = (
    "docs/reports/retrieval-quality-baseline-run1.json",
    "docs/reports/retrieval-quality-baseline.json",
    "docs/reports/retrieval-quality-post-1seas-vs-before.json",
)
_NO_FOLLOW = getattr(os, "O_NOFOLLOW", 0)
_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
# Windows opens a raw descriptor in TEXT mode unless told otherwise, which would
# translate newlines and break the "hash the exact bytes" property on both the
# read and the write side. No-op everywhere else.
_BINARY = getattr(os, "O_BINARY", 0)


def report_directory(root: Path) -> Path:
    return Path(os.path.realpath(root)).joinpath(*REPORT_DIRECTORY_PARTS)


def _assert_confining_ancestors(root: Path) -> None:
    """``O_NOFOLLOW`` rejects only the FINAL component, so the three confining
    ancestors are checked here, explicitly, with ``lstat``: the repository root,
    ``docs``, and ``docs/reports``.  Each must be a real directory; a symlinked
    ancestor would let a confined-looking basename land anywhere on the disk.
    """
    base = Path(os.path.realpath(root))
    for ancestor in (base, base / REPORT_DIRECTORY_PARTS[0],
                     base.joinpath(*REPORT_DIRECTORY_PARTS)):
        try:
            entry = os.lstat(ancestor)
        except OSError as exc:
            raise EvaluationInvalid(
                "report_path_unconfined",
                f"confining directory is unusable: {ancestor} ({exc})") from exc
        if stat.S_ISLNK(entry.st_mode) or not stat.S_ISDIR(entry.st_mode):
            raise EvaluationInvalid(
                "report_path_unconfined",
                f"confining directory is a symlink or not a directory: {ancestor}")


def confined_report_path(root: Path, candidate: Path | str, *, role: str) -> Path:
    """Validate one report path and return it, WITHOUT creating anything.

    Parent directories are never created: a caller-selected parent is exactly
    the escape this confinement exists to refuse.
    """
    base = Path(os.path.realpath(root))
    reports = base.joinpath(*REPORT_DIRECTORY_PARTS)
    _assert_confining_ancestors(base)
    supplied = Path(os.path.abspath(Path(candidate)))
    name = supplied.name
    # The PARENT is resolved (a symlinked ``docs`` or ``docs/reports`` lands
    # somewhere that is not the report directory and is refused here as well as
    # by the ancestor assertion above); the FINAL component never is, so a
    # symlinked destination cannot masquerade as a confined regular file.
    parent = Path(os.path.realpath(supplied.parent))
    _require(parent == reports, "report_path_unconfined",
             f"{role} path must be a direct child of {reports}: {supplied}")
    _require(name and name not in (os.curdir, os.pardir), "report_path_unconfined",
             f"{role} path does not name a file: {supplied}")
    _require(name.startswith(REPORT_BASENAME_PREFIX), "report_path_unconfined",
             f"{role} basename must begin with {REPORT_BASENAME_PREFIX!r}: {name}")
    resolved = reports / name
    if role != "temporary":
        _require(not _REPORT_TEMP_RE.match(resolved.name), "report_path_unconfined",
                 f"{role} basename is reserved for publish temporaries: {resolved.name}")
    if role == "output":
        relative = resolved.relative_to(base).as_posix()
        _require(relative not in PROTECTED_REPORT_PATHS, "report_path_protected",
                 f"protected closed-1seaw receipt cannot be a destination: {relative}")
    try:
        entry = os.lstat(resolved)
    except FileNotFoundError:
        return resolved
    except OSError as exc:
        raise EvaluationInvalid("report_path_unconfined",
                                f"{role} path is unusable: {resolved} ({exc})") from exc
    _require(not stat.S_ISLNK(entry.st_mode), "report_path_unconfined",
             f"{role} path is a symlink: {resolved}")
    _require(stat.S_ISREG(entry.st_mode), "report_path_unconfined",
             f"{role} path is not a regular file: {resolved}")
    return resolved


def read_baseline_bytes(path: Path) -> tuple[bytes, dict[str, Any]]:
    """Open the baseline ONCE without following symlinks, hash the exact bytes
    read from that handle, then parse those same bytes.

    Three precisions, all of them from 1wpaj Requirement 8:

    * device and inode cannot change on a HELD descriptor, so re-reading the
      descriptor proves nothing.  The property worth checking is whether the
      NAME still resolves to the object the descriptor holds -- ``fstat(fd)``
      against ``stat(path)`` -- which is what catches a replacement between
      validation and read.
    * hard-link aliases are rejected from the DESCRIPTOR'S OWN link count.  A
      path-side check would reintroduce the very race the single handle removes.
    * the file must be regular; ``O_NOFOLLOW`` covers the final component only.
    """
    try:
        handle = os.open(path, os.O_RDONLY | _NO_FOLLOW | _CLOEXEC | _BINARY)
    except OSError as exc:
        raise EvaluationInvalid("invalid_baseline",
                                f"cannot open baseline report: {exc}") from exc
    try:
        held = os.fstat(handle)
        _require(stat.S_ISREG(held.st_mode), "invalid_baseline",
                 f"baseline report is not a regular file: {path}")
        _require(held.st_nlink == 1, "invalid_baseline",
                 f"baseline report has {held.st_nlink} links (hard-link alias): {path}")
        try:
            named = os.stat(path)
        except OSError as exc:
            raise EvaluationInvalid(
                "invalid_baseline",
                f"baseline report disappeared between validation and read: {exc}") from exc
        _require((named.st_dev, named.st_ino) == (held.st_dev, held.st_ino),
                 "invalid_baseline",
                 f"baseline report was replaced between validation and read: {path}")
        chunks: list[bytes] = []
        while True:
            block = os.read(handle, 1 << 20)
            if not block:
                break
            chunks.append(block)
    finally:
        os.close(handle)
    payload = b"".join(chunks)
    try:
        baseline = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EvaluationInvalid("invalid_baseline",
                                f"cannot read baseline report: {exc}") from exc
    _require(isinstance(baseline, dict), "invalid_baseline",
             f"baseline report is not a JSON object: {path}")
    return payload, baseline


def _publish_temporary(destination: Path) -> Path:
    return destination.parent / (
        f"{REPORT_BASENAME_PREFIX}{REPORT_TEMP_INFIX}{os.getpid()}-{os.urandom(16).hex()}.json"
    )


def _leftover_temporary_aliases(destination: Path, published: os.stat_result) -> list[Path]:
    """Publish temporaries in the report directory that alias ``destination``."""
    aliases: list[Path] = []
    try:
        entries = sorted(os.listdir(destination.parent))
    except OSError:
        return aliases
    for name in entries:
        if not _REPORT_TEMP_RE.match(name):
            continue
        candidate = destination.parent / name
        try:
            entry = os.lstat(candidate)
        except OSError:
            continue
        if (stat.S_ISREG(entry.st_mode) and entry.st_dev == published.st_dev
                and entry.st_ino == published.st_ino):
            aliases.append(candidate)
    return aliases


def _recover_leftover_temporary(destination: Path, content_sha256: str) -> bool:
    """Recover a destination that exists ONLY because a publish temporary still
    aliases it, and return whether the recovery ran.

    ``os.link`` leaves the destination with two links until the temporary is
    unlinked.  An interrupt in that window leaves a CORRECT destination that the
    next invocation's own hard-link rejection would otherwise have to refuse --
    the same poisoning class this publish design removes.  The recovery is to
    unlink the TEMPORARY after confirming the destination's content hash matches
    the report just written; the destination is never unlinked, whatever it
    holds.  A destination whose content differs, or whose extra links are not
    publish temporaries, is not recoverable and is left exactly as it is.
    """
    try:
        entry = os.lstat(destination)
    except OSError:
        return False
    if stat.S_ISLNK(entry.st_mode) or not stat.S_ISREG(entry.st_mode) or entry.st_nlink < 2:
        return False
    aliases = _leftover_temporary_aliases(destination, entry)
    if not aliases:
        return False
    try:
        if hashlib.sha256(destination.read_bytes()).hexdigest() != content_sha256:
            return False
    except OSError:
        return False
    for alias in aliases:
        try:
            os.unlink(alias)
        except OSError as exc:
            raise EvaluationInvalid(
                "report_publish_failed",
                f"cannot remove leftover publish temporary {alias}: {exc}") from exc
    return True


def _verify_single_link(destination: Path, content_sha256: str) -> bool:
    """The published destination must carry exactly one link.

    Returns whether a leftover publish temporary had to be recovered first.
    """
    try:
        entry = os.lstat(destination)
    except OSError as exc:
        raise EvaluationInvalid("report_publish_unverified",
                                f"published report is unreadable: {exc}") from exc
    _require(stat.S_ISREG(entry.st_mode) and not stat.S_ISLNK(entry.st_mode),
             "report_publish_unverified",
             f"published report is not a regular file: {destination}")
    if entry.st_nlink == 1:
        return False
    # Our own temporary survived the ``finally`` (an interrupt, or a failed
    # unlink): the same recovery applies, and it never touches the destination.
    _require(_recover_leftover_temporary(destination, content_sha256),
             "report_publish_unverified",
             f"published report carries {entry.st_nlink} links that are not recoverable "
             f"publish temporaries: {destination}")
    _require(os.lstat(destination).st_nlink == 1, "report_publish_unverified",
             f"published report still carries more than one link: {destination}")
    return True


def publish_report(root: Path, out_path: Path | str, report: Mapping[str, Any], *,
                   indexer: Any | None = None) -> dict[str, Any]:
    """Confine, then atomically publish one report.

    The write lands in a same-directory temporary and publishes with
    ``os.link``, which refuses an existing destination, does not follow a
    symlink at the final component, and fails even on a dangling one.  Exclusive
    creation directly ON the destination is NOT a substitute: writing bytes into
    a file created that way reintroduces the truncation window this design
    removes, so a timeout or interrupt mid-write would permanently occupy a
    declared destination that exclusive creation can never reclaim.
    """
    destination = confined_report_path(root, out_path, role="output")
    payload = _stable_json_bytes(report, pretty=True)
    content_sha256 = hashlib.sha256(payload).hexdigest()
    recovered = False
    if os.path.lexists(destination):
        # An existing destination is never overwritten and never unlinked. The
        # single exception is a destination that exists ONLY because an
        # interrupted publish left its temporary aliasing it AND whose bytes
        # already equal the report being written: that is this design's own
        # residue, and clearing the temporary is the documented recovery.
        recovered = _recover_leftover_temporary(destination, content_sha256)
        _require(recovered, "report_destination_exists",
                 f"report destination already exists and is never overwritten: {destination}")
        _verify_single_link(destination, content_sha256)
        return {"path": destination.as_posix(), "content_sha256": content_sha256,
                "bytes": len(payload), "recovered_leftover_temporary": True}
    temporary = confined_report_path(root, _publish_temporary(destination), role="temporary")
    if indexer is not None:
        # Re-run immediately before the exclusive create, against BOTH names.
        assert_eval_artifacts_excluded(Path(os.path.abspath(root)),
                                       [destination, temporary], indexer)
    _require(not os.path.lexists(temporary), "report_destination_exists",
             f"publish temporary already exists: {temporary}")
    try:
        handle = os.open(temporary,
                         os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NO_FOLLOW | _CLOEXEC | _BINARY,
                         0o644)
    except OSError as exc:
        raise EvaluationInvalid("report_publish_failed",
                                f"cannot create publish temporary {temporary}: {exc}") from exc
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError as exc:
            raise EvaluationInvalid(
                "report_destination_exists",
                f"report destination already exists and is never overwritten: "
                f"{destination}") from exc
        except OSError as exc:
            raise EvaluationInvalid("report_publish_failed",
                                    f"cannot publish {destination}: {exc}") from exc
    finally:
        try:
            os.unlink(temporary)
        except OSError:
            pass
    # An interrupt (or a failed unlink) in the ``finally`` above leaves our own
    # temporary still aliasing the destination; the verification recovers it.
    recovered = _verify_single_link(destination, content_sha256) or recovered
    return {"path": destination.as_posix(), "content_sha256": content_sha256,
            "bytes": len(payload), "recovered_leftover_temporary": recovered}


def _result_items(tool: str, response: Mapping[str, Any]) -> list[dict[str, Any]]:
    data = response.get("data") if isinstance(response, Mapping) else None
    if not isinstance(data, Mapping):
        return []
    key = "citations" if tool == "code_ask" else "results"
    rows = data.get(key)
    return [dict(row) for row in rows] if isinstance(rows, list) else []


def _normalized_text(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _bounded_text_match(value: Any, expected: Any) -> bool:
    text = _normalized_text(value)
    needle = _normalized_text(expected)
    if not needle:
        return False
    return re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", text) is not None


def _result_line_span(result: Mapping[str, Any]) -> tuple[int, int] | None:
    lines = result.get("lines")
    if not isinstance(lines, (list, tuple)) or not lines:
        return None
    try:
        start = int(lines[0])
        end = int(lines[-1] if len(lines) > 1 else lines[0])
    except (TypeError, ValueError):
        return None
    if start < 1 or end < start:
        return None
    return start, end


def _declaration_key(path: str, symbol: str) -> str:
    return f"{_normal_path(path)}::{symbol}"


def _symbol_match_evidence(result: Mapping[str, Any],
                           declaration: Mapping[str, Any]) -> dict[str, Any] | None:
    """Declaration identity: the result's own line span must intersect the
    resolved declaration span. A same-file call site, comment mention, or
    whole-file summary never satisfies a symbol anchor."""
    if str(result.get("kind") or "").strip().lower() in SUMMARY_RESULT_KINDS:
        return None
    span = _result_line_span(result)
    if span is None:
        return None
    if span[0] <= int(declaration["end_line"]) and span[1] >= int(declaration["start_line"]):
        return {"field": "lines", "evidence": [span[0], span[1]]}
    return None


def _resolve_declaration(server: Any, root: Path, path: str, symbol: str, *,
                         fixture_id: str) -> dict[str, Any]:
    """Resolve one symbol anchor to its declaration span through the public
    structural paths (``code_outline`` first, ``code_constants`` for constants
    the outline cannot name). Unresolved or ambiguous anchors invalidate the
    run: a label without one objective declaration cannot score anything."""
    spans: list[dict[str, Any]] = []
    outline = server.code_outline_response(root, path)
    if isinstance(outline, Mapping) and outline.get("status") == "ok":
        data = outline.get("data") if isinstance(outline.get("data"), Mapping) else {}
        for entry in data.get("symbols") or []:
            if not isinstance(entry, Mapping) or entry.get("name") != symbol:
                continue
            start, end = entry.get("start_line"), entry.get("end_line")
            if isinstance(start, int) and isinstance(end, int) and 1 <= start <= end:
                spans.append({"start_line": start, "end_line": end,
                              "kind": str(entry.get("kind") or "symbol"),
                              "resolver": "code_outline"})
    if not spans:
        constants = server.code_constants_response(root, [symbol])
        if isinstance(constants, Mapping) and constants.get("status") == "ok":
            data = constants.get("data") if isinstance(constants.get("data"), Mapping) else {}
            for entry in data.get("results") or []:
                if not isinstance(entry, Mapping) or entry.get("name") != symbol:
                    continue
                if _normal_path(entry.get("file")) != _normal_path(path):
                    continue
                line = entry.get("line")
                if isinstance(line, int) and line >= 1:
                    spans.append({"start_line": line, "end_line": line,
                                  "kind": "constant", "resolver": "code_constants"})
    _require(len(spans) >= 1, "unresolved_symbol_anchor",
             f"{fixture_id}: symbol {symbol!r} has no declaration in {path}")
    _require(len(spans) == 1, "ambiguous_symbol_anchor",
             f"{fixture_id}: symbol {symbol!r} is declared {len(spans)} times in {path}; "
             "use a line_span anchor")
    return spans[0]


def resolve_symbol_anchors(corpus: Mapping[str, Any], server: Any, root: Path) -> dict[str, dict[str, Any]]:
    """Resolve every symbol anchor in the corpus once, keyed ``path::symbol``."""
    resolved: dict[str, dict[str, Any]] = {}
    for fixture in corpus["fixtures"]:
        for target in fixture["relevance"]:
            anchor = target["anchor"]
            if anchor["type"] != "symbol":
                continue
            key = _declaration_key(target["path"], anchor["value"])
            if key in resolved:
                continue
            resolved[key] = _resolve_declaration(server, root, target["path"], anchor["value"],
                                                 fixture_id=fixture["id"])
    return resolved


def _content_match_evidence(result: Mapping[str, Any], expected: Any) -> dict[str, Any] | None:
    for key in ("excerpt", "text", "snippet"):
        if _bounded_text_match(result.get(key), expected):
            return {"field": key, "evidence": _normalized_text(expected)}
    return None


def _section_match_evidence(result: Mapping[str, Any], expected: Any) -> dict[str, Any] | None:
    """Heading identity against the chunk's section path.

    Public results that carry a ``section`` field are matched on it. A result
    without one (``code_ask`` citations before the field was exposed,
    ``code_lexical`` rows) is matched on the breadcrumb the chunker bakes as the
    first line of every docs section chunk, which is the same section path;
    summary kinds carry a title line rather than a breadcrumb and never match.
    """
    section = result.get("section")
    field = "section"
    if not isinstance(section, str):
        if str(result.get("kind") or "").strip().lower() in SUMMARY_RESULT_KINDS:
            return None
        text = result.get("excerpt") or result.get("text") or ""
        if not isinstance(text, str) or not text:
            return None
        section = text.split("\n", 1)[0]
        field = "breadcrumb"
    expected_heading = _normalized_text(expected)
    for component in section.split(">"):
        heading = re.sub(
            r"\s+\((?:part\s+\d+/\d+|rows\s+\d+[–-]\d+\s+of\s+\d+)\)\s*$",
            "", component.strip(), flags=re.IGNORECASE,
        )
        if _normalized_text(heading) == expected_heading:
            return {"field": field, "evidence": heading}
    return None


def _anchor_match_evidence(result: Mapping[str, Any], expected: Mapping[str, Any],
                           declarations: Mapping[str, Mapping[str, Any]] | None = None) -> dict[str, Any] | None:
    if _normal_path(result.get("path")) != expected["path"]:
        return None
    anchor = expected["anchor"]
    anchor_type = anchor["type"]
    if anchor_type == "path":
        return {"field": "path", "evidence": expected["path"]}
    if anchor_type == "symbol":
        declaration = (declarations or {}).get(_declaration_key(expected["path"], anchor["value"]))
        _require(declaration is not None, "unresolved_symbol_anchor",
                 f"symbol anchor {anchor['value']!r} in {expected['path']} was not resolved to a declaration")
        return _symbol_match_evidence(result, declaration)
    if anchor_type == "content":
        return _content_match_evidence(result, anchor["value"])
    if anchor_type == "section":
        return _section_match_evidence(result, anchor["value"])
    span = _result_line_span(result)
    if span is None:
        return None
    if span[0] <= int(anchor["end"]) and span[1] >= int(anchor["start"]):
        return {"field": "lines", "evidence": [span[0], span[1]]}
    return None


def _anchor_matches(result: Mapping[str, Any], expected: Mapping[str, Any],
                    declarations: Mapping[str, Mapping[str, Any]] | None = None) -> bool:
    return _anchor_match_evidence(result, expected, declarations) is not None


def _nearest_rank_p95(values: Sequence[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(float(v) for v in values)
    rank = max(1, math.ceil(0.95 * len(ordered)))
    return ordered[rank - 1]


def _p95_is_maximum(sample_count: int) -> bool:
    """True when nearest-rank p95 over ``sample_count`` samples IS the maximum.

    Wave 1wur7 (1wuuh): ``ceil(0.95 * n) == n`` for every n below 20, so at the
    frozen corpus's sample counts ``warm_p95_ms`` is literally ``max(samples)``
    while carrying a name that implies a tail quantile.  The receipt says so.
    """
    return sample_count > 0 and max(1, math.ceil(0.95 * sample_count)) == sample_count


def _sample_floor(values: Sequence[float]) -> float | None:
    return min(float(v) for v in values) if values else None


def _sample_median(values: Sequence[float]) -> float | None:
    return float(statistics.median(float(v) for v in values)) if values else None


def _relative_jitter(current: float | None, baseline: float | None) -> float | None:
    """Jitter between one paired statistic, normalised by the smaller value."""
    if current is None or baseline is None:
        return None
    lower = min(float(current), float(baseline))
    if lower <= 0:
        return 0.0
    return abs(float(current) - float(baseline)) / lower


def _dcg(grades: Sequence[float]) -> float:
    return sum((2.0 ** grade - 1.0) / math.log2(rank + 2.0)
               for rank, grade in enumerate(grades))


def score_response(tool: str, fixture: Mapping[str, Any], response: Mapping[str, Any],
                   declarations: Mapping[str, Mapping[str, Any]] | None = None) -> dict[str, Any]:
    results = _result_items(tool, response)[:RECALL_K]
    expected = [
        target for target in fixture["relevance"]
        if tool in target.get("tools", fixture["applicable_tools"])
    ]
    unmatched = set(range(len(expected)))
    normalized: list[dict[str, Any]] = []
    first_relevant: int | None = None
    for rank, result in enumerate(results, start=1):
        matches = [
            (idx, _anchor_match_evidence(result, expected[idx], declarations))
            for idx in unmatched
        ]
        matches = [(idx, evidence) for idx, evidence in matches if evidence is not None]
        if matches:
            best, match_evidence = max(matches, key=lambda item: expected[item[0]]["grade"])
            unmatched.remove(best)
            grade = float(expected[best]["grade"])
            matched_anchor: dict[str, Any] | None = dict(expected[best]["anchor"])
            if first_relevant is None:
                first_relevant = rank
        else:
            grade = 0.0
            matched_anchor = None
            match_evidence = None
        normalized.append({
            "rank": rank,
            "path": _normal_path(result.get("path")),
            "grade": grade,
            "matched_anchor": matched_anchor,
            "matched_field": match_evidence["field"] if match_evidence else None,
            "matched_evidence": match_evidence["evidence"] if match_evidence else None,
        })
    relevant_count = len(expected)
    recall = 1.0 if relevant_count == 0 else (relevant_count - len(unmatched)) / relevant_count
    actual_grades = [row["grade"] for row in normalized]
    ideal_grades = sorted((float(row["grade"]) for row in expected), reverse=True)[:RECALL_K]
    ideal = _dcg(ideal_grades)
    ndcg = 1.0 if not expected else (_dcg(actual_grades) / ideal if ideal else 0.0)
    data = response.get("data") if isinstance(response.get("data"), Mapping) else {}
    if fixture.get("abstention_expected"):
        if tool == "code_ask":
            # A correct abstention is more than a low band: the response must also
            # SAY it found nothing (the "no confident match" gap) or flag every
            # citation weak, so a synthetic-score row can never pass as a match
            # (cycle-2 review, QA-SEAT-2).
            gaps = data.get("gaps") if isinstance(data.get("gaps"), list) else []
            declared_no_match = any("no confident match" in str(gap) for gap in gaps)
            all_weak = bool(results) and all(bool(row.get("weak")) for row in results)
            abstention_correct: bool | None = (
                data.get("confidence") == "low" and first_relevant is None
                and (declared_no_match or all_weak or not results)
            )
        else:
            abstention_correct = len(results) == 0
    else:
        abstention_correct = None
    expected_type = fixture.get("expected_question_type")
    question_type_correct = None
    if tool == "code_ask" and expected_type is not None:
        question_type_correct = data.get("question_type") == expected_type
    return {
        "recall_at_10": round(recall, 8),
        "ndcg_at_10": round(ndcg, 8),
        "first_relevant_rank": first_relevant,
        "mrr_at_10": round(1.0 / first_relevant, 8) if first_relevant else 0.0,
        "abstention_correct": abstention_correct,
        "question_type_correct": question_type_correct,
        "normalized_ranks": normalized,
    }


def _run_with_timeout(function: Callable[[], Any], timeout_seconds: float, label: str) -> Any:
    result_queue: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)

    def target() -> None:
        try:
            result_queue.put((True, function()))
        except BaseException as exc:  # propagate exact production-path failure to caller
            result_queue.put((False, exc))

    thread = threading.Thread(target=target, name=f"retrieval-eval-{label}", daemon=True)
    thread.start()
    try:
        ok, value = result_queue.get(timeout=max(0.001, timeout_seconds))
    except queue.Empty as exc:
        raise EvaluationInvalid("call_timeout", f"{label} exceeded {timeout_seconds:.3f}s") from exc
    if not ok:
        raise EvaluationInvalid("query_failed", f"{label} failed: {type(value).__name__}: {value}") from value
    return value


def _state_token(state: Mapping[str, Any]) -> tuple[str, str, int]:
    return (str(state["attempt_id"]), str(state["status"]), int(state["generation"]))


def _evaluator_identity() -> dict[str, Any]:
    try:
        source_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    except OSError as exc:
        raise EvaluationInvalid("evaluator_unreadable", f"cannot identify evaluator source: {exc}") from exc
    return {
        "source_sha256": source_sha256,
        "report_schema": REPORT_SCHEMA,
        "fixture_schema": FIXTURE_SCHEMA,
    }


def _module_constant(path: Path, name: str) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(rf'^{re.escape(name)}\s*=\s*"([^"]*)"', text, flags=re.MULTILINE)
    return match.group(1) if match else None


def _git_output(root: Path, *args: str, binary: bool = False) -> str | bytes | None:
    """Captured stdout of one git command, or ``None`` when git cannot answer.

    ``binary=True`` returns the raw bytes so a blob can be hashed exactly as the
    served file is hashed (no newline translation, no decode replacement).
    """
    try:
        from subprocess_util import isolated_run  # framework-wide spawn isolation
    except ImportError:
        return None
    try:
        completed = isolated_run(
            ["git", "-C", str(root), *args], capture_output=True, text=not binary,
            timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout


def _git_binding(root: Path | None, modules: Mapping[str, str]) -> dict[str, Any]:
    """Disclose how the served modules relate to the repository's HEAD.

    Informational only (the comparison key is the module digest): a receipt
    produced from a scratch copy of HEAD's ``server_impl.py`` says so here,
    instead of being discoverable only by recomputing hashes against git.
    """
    binding: dict[str, Any] = {"head": None, "matches_head": {}, "worktree_dirty": None}
    if root is None:
        return binding
    head = _git_output(root, "rev-parse", "HEAD")
    if head is None:
        return binding
    binding["head"] = head.strip()
    for name, served_sha in modules.items():
        # Raw blob bytes: a CRLF checkout or a non-UTF-8 byte must not read as a
        # mismatch for an unchanged module (cycle-2 reverification, RV-4).
        blob = _git_output(root, "show", f"HEAD:{PRODUCTION_MODULE_PREFIX}{name}", binary=True)
        binding["matches_head"][name] = (
            None if blob is None else hashlib.sha256(blob).hexdigest() == served_sha
        )
    status = _git_output(root, "status", "--porcelain", "--", PRODUCTION_MODULE_PREFIX.rstrip("/"))
    binding["worktree_dirty"] = None if status is None else bool(status.strip())
    return binding


def _production_identity(scripts_dir: Path, root: Path | None = None) -> dict[str, Any]:
    """Bind the report to the production retrieval modules that served it."""
    modules: dict[str, str] = {}
    for name in PRODUCTION_RETRIEVAL_MODULES:
        try:
            modules[name] = hashlib.sha256((scripts_dir / name).read_bytes()).hexdigest()
        except OSError as exc:
            raise EvaluationInvalid("production_unreadable",
                                    f"cannot identify production retrieval module {name}: {exc}") from exc
    digest = hashlib.sha256(
        "\n".join(f"{name}:{modules[name]}" for name in sorted(modules)).encode("utf-8")
    ).hexdigest()
    versions = {
        label: _module_constant(scripts_dir / file_name, constant)
        for label, (file_name, constant) in PRODUCTION_VERSION_CONSTANTS.items()
    }
    return {
        "scripts_directory": scripts_dir.resolve().as_posix(),
        "modules": modules,
        "digest": digest,
        "versions": versions,
        "git": _git_binding(root, modules),
    }


def _iso_utc(timestamp: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp))


def _compute_run_id(report: Mapping[str, Any]) -> str:
    payload = dict(report)
    payload.pop("run_id", None)
    payload.pop("verdict", None)
    return hashlib.sha256(_stable_json_bytes(payload)).hexdigest()


def _capture_ready_state(index_dir: Path, state_reader: Callable[[Path], Any]) -> dict[str, Any]:
    state = state_reader(index_dir)
    _require(isinstance(state, dict), "index_not_ready", "index build state is absent or unreadable")
    _require(state.get("status") == "complete", "index_not_ready",
             f"index build state is {state.get('status')!r}, not complete")
    _require(isinstance(state.get("generation"), int), "index_not_ready",
             "index generation is absent or invalid")
    return dict(state)


def _new_evaluation_index(server: Any, root: Path) -> Any:
    """Construct a production WaveIndex with evaluator-owned background work disabled."""
    class EvaluationWaveIndex(server.WaveIndex):
        def _start_background_model_downloads(self) -> None:
            return None

        def _start_background_model_downloads_after_startup(self) -> None:
            return None

    return EvaluationWaveIndex(root)


def _verify_current_corpus(root: Path, index_dir: Path, state_store: Any) -> dict[str, int]:
    _require((index_dir / "docs.lance").is_dir() and (index_dir / "code.lance").is_dir(),
             "index_not_ready", "current docs.lance and code.lance tables are required")
    counts: dict[str, int] = {}
    for table in ("docs", "code"):
        count = state_store.registry_chunk_count(index_dir, table)
        _require(isinstance(count, int) and count > 0, "empty_index",
                 f"current {table} Lance/FTS corpus is empty or unregistered")
        counts[table] = count
    return counts


def _call_public_path(server: Any, index: Any, root: Path, tool: str, query: str,
                      epoch_state: tuple[str, str, int]) -> dict[str, Any]:
    if tool == "code_ask":
        return server.code_ask_response(index, root, query, rerank="agent", epoch_state=epoch_state)
    if tool == "code_search":
        return server.code_search_response(index, query, limit=RECALL_K, epoch_state=epoch_state)
    if tool == "docs_search":
        return server.docs_search_response(index, query, limit=RECALL_K, epoch_state=epoch_state)
    if tool == "code_lexical":
        return server.code_lexical_response(root, query=query, limit=RECALL_K)
    raise EvaluationInvalid("invalid_fixture", f"unknown tool: {tool}")


def _mean(values: Iterable[float]) -> float | None:
    rows = [float(value) for value in values]
    return round(sum(rows) / len(rows), 8) if rows else None


def _aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "case_count": len(rows),
        "recall_at_10": _mean(row["recall_at_10"] for row in rows),
        "ndcg_at_10": _mean(row["ndcg_at_10"] for row in rows),
        "agentic_mrr_at_10": _mean(row["mrr_at_10"] for row in rows if row["is_agentic"]),
        "abstention_accuracy": _mean(float(row["abstention_correct"])
                                     for row in rows if row["abstention_correct"] is not None),
        "question_type_accuracy": _mean(float(row["question_type_correct"])
                                        for row in rows if row["question_type_correct"] is not None),
    }


def aggregate_metrics(case_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_tool: dict[str, Any] = {}
    for tool in TOOLS:
        tool_rows = [row for row in case_rows if row["tool"] == tool and row["applicable"]]
        classes = sorted({str(row["class"]) for row in tool_rows})
        by_tool[tool] = {
            "overall": _aggregate(tool_rows),
            "by_split": {split: _aggregate([r for r in tool_rows if r["split"] == split])
                         for split in SPLITS},
            "by_class": {case_class: _aggregate([r for r in tool_rows if r["class"] == case_class])
                         for case_class in classes},
            "by_split_and_class": {
                split: {
                    case_class: _aggregate([
                        row for row in tool_rows
                        if row["split"] == split and row["class"] == case_class
                    ])
                    for case_class in sorted({
                        str(row["class"]) for row in tool_rows if row["split"] == split
                    })
                }
                for split in SPLITS
            },
        }
    return {"by_tool": by_tool}


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _runtime_execution_providers(embedder: Any) -> list[str]:
    """Resolve providers from the concrete embedder/session that executed queries.

    FastEmbed's ``TextEmbedding`` wrapper does not expose ``provider`` itself; its
    ONNX Runtime session is normally reachable as ``model.model``. Accelerated
    Wavefoundry embedders expose a direct provider or session. Only runtime-bound
    values are accepted — installed/available providers do not prove which one ran.
    """
    pending = [embedder]
    seen: set[int] = set()
    providers: set[str] = set()
    while pending:
        current = pending.pop(0)
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        try:
            getter = getattr(current, "get_providers", None)
        except Exception:
            getter = None
        if callable(getter):
            try:
                values = getter()
            except Exception:
                values = None
            if isinstance(values, (list, tuple, set)):
                providers.update(
                    value.strip() for value in values
                    if isinstance(value, str) and value.strip()
                )
        try:
            direct = getattr(current, "provider", None)
        except Exception:
            direct = None
        if isinstance(direct, str) and direct.strip():
            providers.add(direct.strip())
        elif isinstance(direct, (list, tuple, set)):
            providers.update(
                value.strip() for value in direct
                if isinstance(value, str) and value.strip()
            )
        for attribute in ("model", "session", "_session", "ort_session", "_model"):
            try:
                nested = getattr(current, attribute, None)
            except Exception:
                nested = None
            if nested is not None and id(nested) not in seen:
                pending.append(nested)
    return sorted(
        provider for provider in providers
        if provider.casefold() not in {"unknown", "none", "null"}
    )


def _environment_snapshot(index: Any, indexer: Any) -> dict[str, Any]:
    models = {
        "docs": getattr(indexer, "DOCS_MODEL", None),
        "code": getattr(indexer, "CODE_MODEL", None),
        "reranker": getattr(indexer, "RERANKER_MODEL", None),
    }
    model_versions = ((getattr(index, "_meta", {}) or {}).get("project", {}) or {}).get("model_versions", {})
    embedders = getattr(index, "_embedders", {}) or {}
    _require(bool(embedders), "execution_provider_unknown",
             "no initialized embedding runtime was available for provider capture")
    providers: set[str] = set()
    for model_name, embedder in sorted(embedders.items(), key=lambda item: str(item[0])):
        resolved = _runtime_execution_providers(embedder)
        _require(bool(resolved), "execution_provider_unknown",
                 f"cannot determine the execution provider for embedding model {model_name!r}")
        providers.update(resolved)
    reranker = getattr(index, "_reranker", None)
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "models": models,
        "indexed_model_versions": model_versions,
        "execution_providers": sorted(providers),
        "reranker_provider": getattr(reranker, "provider", None),
        "packages": {
            "fastembed": _package_version("fastembed"),
            "lancedb": _package_version("lancedb"),
            "onnxruntime": _package_version("onnxruntime"),
        },
        "offline": True,
        "retrieval_toggles": _retrieval_toggles(),
        # Wave 1wpig (1wpaj Requirement 8): VALUES, in their own compared key.
        "production_tuning": _production_tuning(),
    }


def _index_identity(root: Path, index_dir: Path, state_store: Any) -> dict[str, Any]:
    store_path = state_store.state_store_path(index_dir).resolve()
    try:
        root_stat = root.resolve().stat()
        stat = store_path.stat()
    except OSError as exc:
        raise EvaluationInvalid("index_not_ready", f"cannot identify repository/index store: {exc}") from exc
    return {
        "repository_root": root.resolve().as_posix(),
        "repository_device": int(root_stat.st_dev),
        "repository_inode": int(root_stat.st_ino),
        "index_directory": index_dir.resolve().as_posix(),
        "state_store": store_path.as_posix(),
        "state_store_device": int(stat.st_dev),
        "state_store_inode": int(stat.st_ino),
    }


def _sqlite_backup(source: Path, destination: Path) -> None:
    source_uri = f"file:{source.as_posix()}?mode=ro"
    src = sqlite3.connect(source_uri, uri=True)
    dst = sqlite3.connect(destination)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def _degraded_probe(server: Any, state_store: Any, root: Path, fixture: Mapping[str, Any],
                    deadline: float) -> dict[str, Any]:
    source_store = state_store.state_store_path(root / ".wavefoundry" / "index")
    _require(source_store.is_file(), "index_not_ready", "index-state store is required for degraded probe")
    with tempfile.TemporaryDirectory(prefix="wavefoundry-retrieval-eval-") as temp:
        probe_root = Path(temp)
        probe_index_dir = probe_root / ".wavefoundry" / "index"
        probe_index_dir.mkdir(parents=True)
        _sqlite_backup(source_store, state_store.state_store_path(probe_index_dir))
        probe_state = _capture_ready_state(probe_index_dir, state_store.read_build_state)
        probe_index = _new_evaluation_index(server, probe_root)

        def unavailable(*_args: Any, **_kwargs: Any) -> Any:
            raise server.SemanticModelUnavailableOfflineError("injected offline model outage")

        probe_index.search_docs = unavailable
        probe_index.search_code = unavailable
        probe_index.search_combined = unavailable
        responses: dict[str, Any] = {}
        for tool in ("docs_search", "code_search", "code_ask"):
            remaining = deadline - time.monotonic()
            _require(remaining > 0, "total_timeout", "evaluation exceeded the 20-minute total timeout")
            timeout = min(CALL_TIMEOUT_SECONDS[tool], remaining)
            response = _run_with_timeout(
                lambda t=tool: _call_public_path(server, probe_index, probe_root, t,
                                                 str(fixture["query"]), _state_token(probe_state)),
                timeout, f"degraded-probe:{tool}",
            )
            data = response.get("data") if isinstance(response, dict) else None
            _require(response.get("status") == "ok" and isinstance(data, dict) and
                     data.get("search_mode") == "lexical_fallback" and
                     data.get("fallback_reason") == "model_unavailable",
                     "degraded_probe_failed", f"{tool} did not use the public lexical fallback")
            responses[tool] = {
                "status": response.get("status"),
                "search_mode": data.get("search_mode"),
                "fallback_reason": data.get("fallback_reason"),
                "result_count": len(_result_items(tool, response)),
            }
        return {"passed": True, "disposable_store": True, "tools": responses}


def _quality_comparison(current: Mapping[str, Any], baseline: Mapping[str, Any]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for tool in TOOLS:
        cur = current["metrics"]["by_tool"][tool]["by_split"]["holdout"]
        base = baseline["metrics"]["by_tool"][tool]["by_split"]["holdout"]
        for name in QUALITY_METRICS:
            cur_value, base_value = cur.get(name), base.get(name)
            if cur_value is not None and base_value is not None and cur_value + 1e-12 < base_value:
                violations.append({"kind": "quality_regression", "tool": tool, "metric": name,
                                   "scope": "aggregate", "split": "holdout",
                                   "baseline": base_value, "current": cur_value})
        current_classes = current["metrics"]["by_tool"][tool]["by_split_and_class"]["holdout"]
        baseline_classes = baseline["metrics"]["by_tool"][tool]["by_split_and_class"]["holdout"]
        _require(set(current_classes) == set(baseline_classes), "invalid_baseline",
                 f"baseline holdout classes differ for {tool}")
        for case_class in sorted(current_classes):
            for name in QUALITY_METRICS:
                cur_value = current_classes[case_class].get(name)
                base_value = baseline_classes[case_class].get(name)
                if cur_value is not None and base_value is not None and cur_value + 1e-12 < base_value:
                    violations.append({"kind": "quality_regression", "tool": tool, "metric": name,
                                       "scope": "class", "class": case_class, "split": "holdout",
                                       "baseline": base_value, "current": cur_value})
    return violations


# Wave 1wpig (1wpaj Requirement 8): the gate-metric names do NOT exist on a case
# row.  ``abstention_accuracy`` and ``question_type_accuracy`` are aggregate
# names; the per-case fields are ``abstention_correct`` and
# ``question_type_correct``.  Reading the gate names straight off a case row
# returns null on BOTH sides, and the null-versus-null skip below would then
# silently disable two of the five metrics -- including the abstention metric on
# the majority of applicable rows, where it is the only signal there is.  This is
# the same mapping ``_scope_metric`` already applies to a fixture-scoped floor.
FIXTURE_CASE_METRIC_KEYS = {
    "abstention_accuracy": "abstention_correct",
    "question_type_accuracy": "question_type_correct",
}


def _case_metric_value(row: Mapping[str, Any], metric: str) -> float | None:
    value = row.get(FIXTURE_CASE_METRIC_KEYS.get(metric, metric))
    return float(value) if isinstance(value, (bool, int, float)) else None


def _applicable_holdout_rows(report: Mapping[str, Any],
                             label: str) -> dict[tuple[str, str], Mapping[str, Any]]:
    """Exactly one applicable holdout case row per ``(fixture_id, tool)`` key."""
    rows: dict[tuple[str, str], Mapping[str, Any]] = {}
    duplicates: list[str] = []
    for row in report.get("cases", []) or []:
        if not isinstance(row, Mapping):
            continue
        if row.get("applicable") is not True or row.get("split") != "holdout":
            continue
        key = (str(row.get("fixture_id")), str(row.get("tool")))
        if key in rows:
            duplicates.append(f"{key[0]}/{key[1]}")
            continue
        rows[key] = row
    _require(not duplicates, "invalid_baseline",
             f"{label} carries more than one applicable holdout row for: "
             + ", ".join(sorted(set(duplicates))))
    return rows


def _fixture_quality_comparison(
    current: Mapping[str, Any], baseline: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Per-``(fixture_id, tool)`` regression oracle over the gate metrics.

    A single fixture can regress while every holdout aggregate and class metric
    holds steady (one row's loss offset by another's gain), so the aggregate
    comparison cannot stand alone.

    Null semantics are fixed by 1wpaj Requirement 8 and are asymmetric on
    purpose: a baseline value against a current null is a FAILURE (the signal
    disappeared), a current value against a baseline null is REPORTED and does
    not fail (a signal appeared), and null against null is a SKIP.
    """
    current_rows = _applicable_holdout_rows(current, "current report")
    baseline_rows = _applicable_holdout_rows(baseline, "baseline")
    missing_here = sorted(f"{fid}/{tool}" for fid, tool in baseline_rows.keys() - current_rows.keys())
    missing_there = sorted(f"{fid}/{tool}" for fid, tool in current_rows.keys() - baseline_rows.keys())
    _require(not missing_here, "invalid_baseline",
             "current report is missing applicable holdout rows present in the baseline: "
             + ", ".join(missing_here))
    _require(not missing_there, "invalid_baseline",
             "baseline is missing applicable holdout rows present in the current report: "
             + ", ".join(missing_there))
    violations: list[dict[str, Any]] = []
    reported: list[dict[str, Any]] = []
    for key in sorted(current_rows):
        fixture_id, tool = key
        for metric in FIXTURE_QUALITY_GATE_METRICS:
            current_value = _case_metric_value(current_rows[key], metric)
            baseline_value = _case_metric_value(baseline_rows[key], metric)
            entry = {"fixture_id": fixture_id, "tool": tool, "metric": metric,
                     "scope": "fixture", "split": "holdout",
                     "baseline": baseline_value, "current": current_value}
            if current_value is None and baseline_value is None:
                continue
            if current_value is None:
                violations.append({"kind": "fixture_quality_regression", **entry,
                                   "reason": "baseline value against a current null"})
            elif baseline_value is None:
                reported.append({"kind": "fixture_metric_appeared", **entry,
                                 "reason": "current value against a baseline null"})
            elif current_value + 1e-12 < baseline_value:
                violations.append({"kind": "fixture_quality_regression", **entry,
                                   "reason": "per-fixture regression"})
    return violations, reported


def _scope_metric(report: Mapping[str, Any], rule: Mapping[str, Any]) -> float | None:
    tool = str(rule["tool"])
    metric = str(rule["metric"])
    if rule["scope"] == "class":
        value = report["metrics"]["by_tool"][tool]["by_split_and_class"]["holdout"] \
            .get(str(rule["target"]), {}).get(metric)
        return float(value) if isinstance(value, (int, float)) else None
    rows = [
        row for row in report.get("cases", [])
        if row.get("applicable") and row.get("split") == "holdout" and
        row.get("fixture_id") == rule["target"] and row.get("tool") == tool
    ]
    if len(rows) != 1:
        return None
    key = {
        "abstention_accuracy": "abstention_correct",
        "question_type_accuracy": "question_type_correct",
    }.get(metric, metric)
    value = rows[0].get(key)
    return float(value) if isinstance(value, (bool, int, float)) else None


def _quality_gate_violations(report: Mapping[str, Any],
                             baseline: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    gate = report.get("quality_gate")
    if not isinstance(gate, Mapping):
        return []
    violations: list[dict[str, Any]] = []
    for rule in gate.get("critical_floors", []):
        current_value = _scope_metric(report, rule)
        _require(current_value is not None, "invalid_fixture",
                 f"critical quality metric is unavailable: {rule}")
        if current_value + 1e-12 < float(rule["floor"]):
            violations.append({"kind": "critical_quality_floor", **dict(rule),
                               "current": current_value})
        minimum_improvement = rule.get("minimum_improvement")
        if baseline is not None and minimum_improvement is not None:
            baseline_value = _scope_metric(baseline, rule)
            _require(baseline_value is not None, "invalid_baseline",
                     f"baseline critical quality metric is unavailable: {rule}")
            target = baseline_value + float(minimum_improvement)
            if current_value + 1e-12 < target:
                violations.append({"kind": "targeted_improvement_unmet", **dict(rule),
                                   "baseline": baseline_value, "current": current_value,
                                   "target": round(target, 8)})
    return violations


def _validated_epoch(report: Mapping[str, Any], label: str) -> tuple[int, str]:
    generation = report.get("generation")
    _require(isinstance(generation, Mapping), "invalid_baseline", f"{label} generation is missing")
    start, end = generation.get("start"), generation.get("end")
    start_attempt = generation.get("start_attempt_id")
    end_attempt = generation.get("end_attempt_id")
    _require(isinstance(start, int) and not isinstance(start, bool) and start == end,
             "invalid_baseline", f"{label} generation is not a stable completed epoch")
    _require(isinstance(start_attempt, str) and start_attempt and start_attempt == end_attempt,
             "invalid_baseline", f"{label} attempt identity is absent or changed")
    _require(generation.get("start_status") == "complete" and generation.get("end_status") == "complete",
             "invalid_baseline", f"{label} build status is not complete")
    expected_token = [start_attempt, "complete", int(start)]
    _require(generation.get("start_token") == expected_token and
             generation.get("end_token") == expected_token,
             "invalid_baseline", f"{label} full state tokens are missing or incompatible")
    return int(start), start_attempt


def _compare_index_identity(report: Mapping[str, Any], baseline: Mapping[str, Any],
                            *, same_generation: bool) -> None:
    """Compare index identity against the bindings the comparison kind supports.

    Wave 1wur7 (1wtpl): the repository, index directory, and store path bind
    every kind, so two unrelated indexes still cannot be compared.  The state
    store file's own device/inode binds only a same-generation pair, because a
    controlled rebuild legitimately recreates that file and a cross-generation
    comparison is exactly the kind that covers a controlled rebuild.
    """
    current_identity = report.get("index_identity")
    baseline_identity = baseline.get("index_identity")
    _require(isinstance(current_identity, Mapping) and isinstance(baseline_identity, Mapping),
             "invalid_baseline", "baseline repository/index store identity differs")
    keys = SAME_GENERATION_INDEX_IDENTITY_KEYS if same_generation else CROSS_GENERATION_INDEX_IDENTITY_KEYS
    for key in keys:
        _require(key in current_identity and key in baseline_identity and
                 current_identity[key] == baseline_identity[key],
                 "invalid_baseline",
                 f"baseline repository/index store identity differs for {key}")


def _validate_baseline_compatibility(report: Mapping[str, Any],
                                     baseline: Mapping[str, Any]) -> tuple[bool, bool]:
    _require(baseline.get("schema") == REPORT_SCHEMA, "invalid_baseline",
             "baseline report schema mismatch")
    _require(baseline.get("fixture_schema") == report.get("fixture_schema") == FIXTURE_SCHEMA,
             "invalid_baseline", "baseline fixture schema mismatch")
    _require(baseline.get("fixture_digest") == report.get("fixture_digest"), "invalid_baseline",
             "baseline fixture digest differs from the current corpus")
    # Wave 1wur7 (1wtpl Requirement 5): the epoch is validated BEFORE the index
    # identity comparison, because the identity rule is now evaluated per
    # comparison kind and the kind is derived from the epoch.  The reordering
    # changes which ``invalid_baseline`` message a doubly incompatible report
    # returns first; that ordering is intended and is pinned by a test.
    baseline_epoch = _validated_epoch(baseline, "baseline")
    current_epoch = _validated_epoch(report, "current report")
    _require(current_epoch[0] >= baseline_epoch[0], "invalid_baseline",
             "current index generation predates the baseline")
    if current_epoch[0] == baseline_epoch[0]:
        _require(current_epoch[1] == baseline_epoch[1], "invalid_baseline",
                 "same generation has a different build attempt identity")
    same_generation = current_epoch == baseline_epoch
    _compare_index_identity(report, baseline, same_generation=same_generation)
    _require(baseline.get("evaluator_identity") == report.get("evaluator_identity") and
             isinstance(report.get("evaluator_identity"), Mapping),
             "invalid_baseline", "baseline evaluator identity differs")
    baseline_production = baseline.get("production_identity")
    current_production = report.get("production_identity")
    _require(isinstance(baseline_production, Mapping) and
             isinstance(baseline_production.get("digest"), str),
             "invalid_baseline", "baseline lacks production retrieval identity")
    _require(isinstance(current_production, Mapping) and
             isinstance(current_production.get("digest"), str),
             "invalid_baseline", "current report lacks production retrieval identity")
    baseline_run_id = baseline.get("run_id")
    _require(isinstance(baseline_run_id, str) and baseline_run_id == _compute_run_id(baseline),
             "invalid_baseline", "baseline run id is absent or does not match its report content")
    environment_keys = (
        "python", "platform", "machine", "processor", "models", "indexed_model_versions",
        "execution_providers", "reranker_provider", "packages", "offline",
        "retrieval_toggles", "production_tuning",
    )
    baseline_environment = baseline.get("environment")
    current_environment = report.get("environment")
    _require(isinstance(baseline_environment, Mapping) and isinstance(current_environment, Mapping),
             "invalid_baseline", "baseline runtime environment is missing")
    for key in environment_keys:
        _require(key in baseline_environment and key in current_environment and
                 baseline_environment[key] == current_environment[key],
                 "invalid_baseline", f"baseline runtime environment differs for {key}")
    same_production = baseline_production["digest"] == current_production["digest"]
    return same_generation, same_production


def apply_baseline_comparison(report: dict[str, Any], baseline: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    same_generation, same_production = _validate_baseline_compatibility(report, baseline)
    # Only an identical production implementation on the same frozen generation
    # measures run-to-run jitter; a same-generation production change is a
    # before/after receipt and inherits the baseline pair's recorded jitter.
    same_pair = same_generation and same_production
    if same_pair:
        comparison_kind = "same_generation_pair"
    elif same_generation:
        comparison_kind = "production_change_same_generation"
    else:
        comparison_kind = "cross_generation"
    violations = _quality_comparison(report, baseline)
    violations.extend(_quality_gate_violations(report, baseline))
    # Wave 1wpig (1wpaj Requirement 8): the per-fixture oracle sits BESIDE the
    # aggregate and class comparisons, not inside them -- a masked per-fixture
    # regression is invisible to both.
    fixture_violations, fixture_reports = _fixture_quality_comparison(report, baseline)
    violations.extend(fixture_violations)
    operator_reviews: list[dict[str, Any]] = []
    for tool in TOOLS:
        current_perf = report["performance"]["tools"][tool]
        baseline_perf = baseline.get("performance", {}).get("tools", {}).get(tool, {})
        cur_p95 = current_perf.get("warm_p95_ms")
        base_p95 = baseline_perf.get("warm_p95_ms")
        if cur_p95 is None or base_p95 is None:
            continue
        if same_pair:
            # Wave 1wur7 (1wuuh Requirement 1): jitter comes from the whole warm
            # distribution.  ``warm_p95_ms`` alone is one near-max order statistic
            # per run and is blind to a floor shift: the contended wave-1wpif pair
            # reported 2.56% p95 jitter on ``code_search`` while its floor moved
            # 11.79% and its median 18.10%.
            cur_floor = current_perf.get("warm_floor_ms")
            base_floor = baseline_perf.get("warm_floor_ms")
            cur_median = current_perf.get("warm_median_ms")
            base_median = baseline_perf.get("warm_median_ms")
            _require(all(isinstance(value, (int, float)) and not isinstance(value, bool)
                         for value in (cur_floor, base_floor, cur_median, base_median)),
                     "invalid_baseline",
                     "baseline lacks full-distribution warm statistics "
                     f"(warm_floor_ms/warm_median_ms) for {tool}; re-baseline with the "
                     "current evaluator")
            components = {
                "floor": _relative_jitter(cur_floor, base_floor),
                "median": _relative_jitter(cur_median, base_median),
                "p95": _relative_jitter(cur_p95, base_p95),
            }
            # The band is driven by the STABLE statistics only.  Feeding the p95
            # shift back into the p95 allowance is self-defeating: allowed is
            # 3x the jitter, so a pure p95 move would always widen its own
            # threshold past itself and the latency clause could never fire on a
            # same-generation pair.  The p95 component is recorded for the reader.
            jitter = max(components["floor"], components["median"])
            current_perf["jitter_components"] = {
                name: round(float(value), 8) for name, value in components.items()
            }
            current_perf["jitter_ratio"] = round(jitter, 8)
            current_perf["jitter_source"] = "same_generation_pair"
            # Requirement 2: a pair whose FLOOR or MEDIAN moved past the declared
            # threshold was measured under external load.  It is not promotable as
            # a standing baseline, and every offending tool is named, not one.
            current_perf["pair_jitter_threshold"] = PAIR_JITTER_THRESHOLD
            current_perf["pair_contended"] = jitter > PAIR_JITTER_THRESHOLD
            if current_perf["pair_contended"]:
                operator_reviews.append({
                    "kind": "contended_baseline_pair", "tool": tool,
                    "floor_jitter_ratio": round(float(components["floor"]), 8),
                    "median_jitter_ratio": round(float(components["median"]), 8),
                    "p95_jitter_ratio": round(float(components["p95"]), 8),
                    "threshold_ratio": PAIR_JITTER_THRESHOLD,
                })
        elif (isinstance(baseline_perf.get("jitter_ratio"), (int, float))
              and not isinstance(baseline_perf.get("jitter_ratio"), bool)):
            jitter = baseline_perf["jitter_ratio"]
            # Wave 1wur7 (delivery review ARCH-DEL-6) made `pair_contended` READ
            # here, at the one seam where a contended pair becomes the band. The
            # operator decision at the wave's close made latency advisory for
            # every kind, so a contended baseline widens an advisory band rather
            # than gating a hard violation: it is REPORTED per tool with its
            # recovery, and the receipt records that the band was inherited from
            # a contended pair, instead of the comparison being refused.
            if baseline_perf.get("pair_contended") is True:
                current_perf["baseline_pair_contended"] = True
                operator_reviews.append({
                    "kind": "inherited_contended_baseline", "tool": tool,
                    "baseline_jitter_ratio": round(float(jitter), 8),
                    "threshold_ratio": PAIR_JITTER_THRESHOLD,
                    "recovery": "record a quiet same-generation pair first",
                })
            current_perf["jitter_ratio"] = float(jitter)
            current_perf["jitter_source"] = "baseline_same_generation_pair"
        else:
            # Wave 1wuju (1wujt): a SINGLE receipt is a baseline. A receipt that
            # carries no pair-derived jitter used to be refused ("baseline lacks
            # same-generation jitter"); it is now accepted at the existing 25%
            # floor, which is the band every quiet pair on file produced anyway
            # (max(0.25, 3 x jitter) with jitter at or below 1.7%). Contention is
            # recorded as NOT JUDGED rather than as absent: a single run has no
            # reference level, and the readiness council's replay of the recorded
            # fixture showed that no within-run estimator (repetition pseudo-arms,
            # per-case range, half-corpus split) separates a quiet run from a
            # contended one, so none is computed here. The quiet-machine
            # obligation lives in the operator procedure. Latency stays advisory
            # for every kind, so this loosens baseline VALIDITY and nothing else.
            jitter = 0.0
            current_perf["jitter_ratio"] = None
            current_perf["jitter_source"] = "single_run_floor"
            current_perf["pair_contended"] = None
            current_perf["contention_judged"] = False
            current_perf["contention_reason"] = "a single run has no reference level"
        allowed = max(0.25, 3.0 * float(jitter))
        threshold = float(base_p95) * (1.0 + allowed)
        current_perf["permitted_relative_regression"] = round(allowed, 8)
        current_perf["baseline_warm_p95_ms"] = base_p95
        current_perf["warm_p95_threshold_ms"] = round(threshold, 6)
        if float(cur_p95) > threshold:
            latency = {"kind": "latency_regression", "tool": tool,
                       "baseline_ms": base_p95, "current_ms": cur_p95,
                       "threshold_ms": round(threshold, 6)}
            # Wave 1wur7 (1wuuh Requirement 4, as amended by delivery review
            # CODE-DEL-3): the latency clause is ENFORCED exactly when a
            # production change is the only thing that differs between the arms.
            #
            #   production_change_same_generation -- same frozen index, different
            #     production bytes, jitter inherited from a pair recorded on that
            #     same generation.  A regression is attributable to the change,
            #     so a regression IS attributable; latency is still advisory for it
            #     (operator decision at the wave 1wur7 close), reported with a reason.
            #   same_generation_pair -- identical production bytes on one frozen
            #     index.  There is no change to attribute anything to, so a p95
            #     difference IS jitter by construction.  Enforcing here fails a
            #     clean run on tail noise: quiet-machine p95 swings of 1.79%,
            #     10.70% and 22.90% are on record against a 25% floor allowance.
            #     Reported and routed to operator review; the pair's promotability
            #     is judged by the floor/median contention rule above.
            #   cross_generation -- jitter inherited from an earlier measurement
            #     session, so the band describes the baseline machine rather than
            #     the current one.  Reported and routed to operator review.
            #
            # In no mode is the clause silently dropped.
            # Operator decision at wave 1wur7 close: latency is ADVISORY for every
            # comparison kind. The retrieval-quality metrics are deterministic on a
            # frozen index; the latency clause depends on machine noise, and on a
            # shared machine a hard violation cannot be told from contention. The
            # clause is still computed and recorded for every kind, and the reason
            # says why it is advisory; it is never silently dropped.
            latency["enforcement"] = "operator_review"
            latency["reason"] = {
                "same_generation_pair": (
                    "both arms share one production identity on one frozen generation, "
                    "so the difference is jitter rather than a regression"),
                "production_change_same_generation": (
                    "a production change is the only difference between the arms, but "
                    "latency is advisory for every comparison kind (operator decision, "
                    "wave 1wur7): the regression is reported for review, not enforced"),
            }.get(comparison_kind,
                  "inherited jitter describes the baseline machine state, not the current one")
            current_perf["latency_enforcement"] = "operator_review"
            operator_reviews.append(latency)
        cur_bytes = int(current_perf.get("max_response_bytes") or 0)
        base_bytes = int(baseline_perf.get("max_response_bytes") or 0)
        byte_threshold = base_bytes + max(base_bytes * 0.15, 4096.0)
        current_perf["baseline_max_response_bytes"] = base_bytes
        current_perf["response_bytes_threshold"] = math.floor(byte_threshold)
        if cur_bytes > byte_threshold:
            violations.append({"kind": "response_size_regression", "tool": tool,
                               "baseline_bytes": base_bytes, "current_bytes": cur_bytes,
                               "threshold_bytes": math.floor(byte_threshold)})
    report["comparison"] = {
        "baseline_generation": baseline.get("generation"),
        "baseline_run_id": baseline.get("run_id"),
        "baseline_content_sha256": hashlib.sha256(_stable_json_bytes(baseline)).hexdigest(),
        "baseline_production_digest": baseline["production_identity"]["digest"],
        "current_production_digest": report["production_identity"]["digest"],
        "same_generation": same_generation,
        "same_production_identity": same_production,
        "comparison_kind": comparison_kind,
        "violations": violations,
        "operator_review_reasons": list(operator_reviews),
        # Requirement 8: the per-fixture oracle's own accounting. ``reported``
        # is the "current value against a baseline null" class -- recorded so it
        # is never silent, and deliberately NOT a violation and NOT an operator
        # review reason, because a signal APPEARING is not a regression and
        # must not put a clean verdict out of reach.
        "fixture_comparison": {
            "compared_keys": len(_applicable_holdout_rows(report, "current report")),
            "metrics": list(FIXTURE_QUALITY_GATE_METRICS),
            "violations": fixture_violations,
            "reported": fixture_reports,
        },
    }
    # Wave 1wur7 (1wuuh Requirement 2): the comparison-derived reasons must reach
    # the SAME list object the verdict reads, so they are EXTENDED into
    # ``report["operator_review_reasons"]`` rather than assigned over it.  The
    # caller binds that key to its own local list and derives the verdict from
    # the local; reassigning the key would produce a receipt that reports the
    # regression while the verdict still says ``pass``.
    if operator_reviews:
        existing = report.get("operator_review_reasons")
        if isinstance(existing, list):
            existing.extend(operator_reviews)
        else:
            report["operator_review_reasons"] = list(operator_reviews)
    return violations, operator_reviews


def _minimal_invalid_report(reason: EvaluationInvalid) -> dict[str, Any]:
    return {
        "schema": REPORT_SCHEMA,
        "verdict": "invalid",
        "invalidation_reasons": [{"code": reason.code, "message": reason.message}],
    }


def run_evaluation(root: Path, fixtures_path: Path, *, baseline_path: Path | None = None,
                   server: Any | None = None, state_store: Any | None = None,
                   indexer: Any | None = None, clock: Callable[[], float] = time.monotonic,
                   production_scripts_dir: Path | None = None,
                   wall_clock: Callable[[], float] = time.time) -> dict[str, Any]:
    started_at = wall_clock()
    root = root.resolve()
    fixtures_path = fixtures_path.resolve()
    if server is None or state_store is None or indexer is None:
        scripts_dir = Path(__file__).resolve().parent
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        import index_state_store as loaded_state_store
        import indexer as loaded_indexer
        import server_impl as loaded_server
        server = server or loaded_server
        state_store = state_store or loaded_state_store
        indexer = indexer or loaded_indexer
    if production_scripts_dir is None:
        server_file = getattr(server, "__file__", None)
        _require(isinstance(server_file, str) and server_file != "", "production_unidentifiable",
                 "the production retrieval module directory cannot be identified")
        production_scripts_dir = Path(server_file).resolve().parent
    production_identity = _production_identity(production_scripts_dir, root)
    corpus = load_fixture_corpus(fixtures_path, root=root)
    index_dir = root / ".wavefoundry" / "index"
    start_state = _capture_ready_state(index_dir, state_store.read_build_state)
    corpus_counts = _verify_current_corpus(root, index_dir, state_store)
    epoch_state = _state_token(start_state)
    index = _new_evaluation_index(server, root)
    try:
        index_health = index.docs_health()
    except Exception as exc:
        raise EvaluationInvalid("index_not_ready", f"index health preflight failed: {exc}") from exc
    _require(isinstance(index_health, dict) and index_health.get("semantic_ready") is True and
             index_health.get("readiness_overview") == "ready",
             "stale_index", "working tree and published semantic index are not current/ready")
    declarations = resolve_symbol_anchors(corpus, server, root)
    deadline = clock() + TOTAL_TIMEOUT_SECONDS
    case_rows: list[dict[str, Any]] = []
    warmups: dict[str, Any] = {}
    performance_samples: dict[str, list[float]] = {tool: [] for tool in TOOLS}
    response_sizes: dict[str, list[int]] = {tool: [] for tool in TOOLS}

    previous_offline = {name: os.environ.get(name) for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")}
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        for tool in TOOLS:
            fixture = next((f for f in corpus["fixtures"] if tool in f["applicable_tools"]), None)
            _require(fixture is not None, "incomplete_corpus", f"no applicable fixture for {tool}")
            remaining = deadline - clock()
            _require(remaining > 0, "total_timeout", "evaluation exceeded the 20-minute total timeout")
            started = clock()
            response = _run_with_timeout(
                lambda t=tool, q=fixture["query"]: _call_public_path(server, index, root, t, q, epoch_state),
                min(CALL_TIMEOUT_SECONDS[tool], remaining), f"warmup:{tool}",
            )
            elapsed_ms = (clock() - started) * 1000.0
            _require(response.get("status") == "ok", "query_failed", f"{tool} warm-up returned error")
            warmups[tool] = {"fixture_id": fixture["id"], "cold_start_ms": round(elapsed_ms, 6),
                             "response_bytes": len(_stable_json_bytes(response))}

        degraded = _degraded_probe(server, state_store, root, corpus["fixtures"][0], deadline)

        for fixture in corpus["fixtures"]:
            for tool in TOOLS:
                if tool not in fixture["applicable_tools"]:
                    case_rows.append({
                        "fixture_id": fixture["id"], "class": fixture["class"], "split": fixture["split"],
                        "tool": tool, "applicable": False,
                        "exclusion_reason": fixture["excluded_tools"][tool],
                    })
                    continue
                repetitions: list[dict[str, Any]] = []
                for repetition in range(1, MEASURED_REPETITIONS + 1):
                    remaining = deadline - clock()
                    _require(remaining > 0, "total_timeout", "evaluation exceeded the 20-minute total timeout")
                    started = clock()
                    response = _run_with_timeout(
                        lambda t=tool, q=fixture["query"]: _call_public_path(server, index, root, t, q, epoch_state),
                        min(CALL_TIMEOUT_SECONDS[tool], remaining),
                        f"{fixture['id']}:{tool}:rep{repetition}",
                    )
                    elapsed_ms = (clock() - started) * 1000.0
                    _require(response.get("status") == "ok", "query_failed",
                             f"{fixture['id']}:{tool} returned status {response.get('status')!r}")
                    encoded_size = len(_stable_json_bytes(response))
                    score = score_response(tool, fixture, response, declarations)
                    data = response.get("data") if isinstance(response.get("data"), dict) else {}
                    repetitions.append({
                        "repetition": repetition,
                        "elapsed_ms": round(elapsed_ms, 6),
                        "response_bytes": encoded_size,
                        "search_mode": data.get("search_mode"),
                        "fallback_reason": data.get("fallback_reason"),
                        **score,
                    })
                    performance_samples[tool].append(elapsed_ms)
                    response_sizes[tool].append(encoded_size)
                    observed = _capture_ready_state(index_dir, state_store.read_build_state)
                    _require(_state_token(observed) == epoch_state, "generation_drift",
                             "index build state changed during evaluation")
                case_rows.append({
                    "fixture_id": fixture["id"], "class": fixture["class"], "split": fixture["split"],
                    "tool": tool, "applicable": True,
                    "is_agentic": fixture["class"] == "agentic_fix_localization",
                    "recall_at_10": _mean(row["recall_at_10"] for row in repetitions),
                    "ndcg_at_10": _mean(row["ndcg_at_10"] for row in repetitions),
                    "mrr_at_10": _mean(row["mrr_at_10"] for row in repetitions),
                    "first_relevant_rank": repetitions[0]["first_relevant_rank"],
                    "abstention_correct": (all(row["abstention_correct"] is True for row in repetitions)
                                            if repetitions[0]["abstention_correct"] is not None else None),
                    "question_type_correct": (all(row["question_type_correct"] is True for row in repetitions)
                                              if repetitions[0]["question_type_correct"] is not None else None),
                    "repetitions": repetitions,
                })
    finally:
        for name, value in previous_offline.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    end_state = _capture_ready_state(index_dir, state_store.read_build_state)
    _require(_state_token(end_state) == epoch_state, "generation_drift",
             "index build state changed during evaluation")
    # The receipt binds the modules that SERVED the run: re-hash at the end so a
    # framework edit during the four-minute window invalidates the report the
    # way an index generation change does (cycle-2 review, SEC-SEAT-2).
    end_identity = _production_identity(production_scripts_dir, root)
    _require(end_identity["digest"] == production_identity["digest"], "production_drift",
             "production retrieval modules changed during evaluation")
    # A clean receipt says the end-of-run check ran (the failure path leaves no
    # receipt at all), so a reader need not infer it from the evaluator digest.
    production_identity["end_digest_verified"] = True
    finished_at = wall_clock()
    performance = {
        "protocol": {
            "warmups_per_tool": 1,
            "measured_repetitions_per_applicable_pair": MEASURED_REPETITIONS,
            "p95_method": "nearest_rank_pooled_warm_samples",
            "jitter_method": "max_relative_shift_of_warm_floor_and_median",
            "pair_jitter_threshold": PAIR_JITTER_THRESHOLD,
            "minimum_warm_samples": MIN_WARM_SAMPLES,
            "total_timeout_seconds": TOTAL_TIMEOUT_SECONDS,
            "per_call_timeout_seconds": CALL_TIMEOUT_SECONDS,
            "fixture_cap": MAX_FIXTURES,
            "query_utf8_byte_cap": MAX_QUERY_BYTES,
        },
        "warmups": warmups,
        "tools": {},
    }
    operator_reviews: list[dict[str, Any]] = []
    for tool in TOOLS:
        samples = performance_samples[tool]
        p95 = _nearest_rank_p95(samples)
        floor_ms = _sample_floor(samples)
        median_ms = _sample_median(samples)
        max_bytes = max(response_sizes[tool], default=0)
        sample_count = len(samples)
        # Wave 1wur7 (1wuuh Requirement 1): the floor and the median travel in the
        # receipt beside the p95 so a comparison can read the whole distribution
        # without reaching back into ``cases[].repetitions[]``.
        performance["tools"][tool] = {
            "sample_count": sample_count,
            "warm_p95_ms": round(p95, 6) if p95 is not None else None,
            "warm_floor_ms": round(floor_ms, 6) if floor_ms is not None else None,
            "warm_median_ms": round(median_ms, 6) if median_ms is not None else None,
            # Requirement 3: at these sample counts nearest-rank p95 IS the
            # maximum, so the receipt says so rather than letting the field name
            # imply a tail quantile.
            "p95_is_maximum": _p95_is_maximum(sample_count),
            "small_sample_estimate": 0 < sample_count < MIN_WARM_SAMPLES,
            "minimum_warm_samples": MIN_WARM_SAMPLES,
            "max_response_bytes": max_bytes,
        }
        if 0 < sample_count < MIN_WARM_SAMPLES:
            operator_reviews.append({"kind": "small_sample_warm_p95", "tool": tool,
                                     "sample_count": sample_count,
                                     "minimum_warm_samples": MIN_WARM_SAMPLES})
        if p95 is not None and p95 > OPERATOR_REVIEW_P95_MS[tool]:
            operator_reviews.append({"kind": "absolute_latency", "tool": tool,
                                     "warm_p95_ms": round(p95, 6),
                                     "threshold_ms": OPERATOR_REVIEW_P95_MS[tool]})
        if max_bytes > OPERATOR_REVIEW_RESPONSE_BYTES:
            operator_reviews.append({"kind": "absolute_response_size", "tool": tool,
                                     "max_response_bytes": max_bytes,
                                     "threshold_bytes": OPERATOR_REVIEW_RESPONSE_BYTES})
    environment = _environment_snapshot(index, indexer)
    active_toggles = sorted(name for name, on in environment["retrieval_toggles"].items() if on)
    if active_toggles:
        # A kill-switched run does not certify production behaviour even when
        # both sides of a pair agree (Requirement 9).
        operator_reviews.append({"kind": "retrieval_toggle_active", "toggles": active_toggles})
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "fixture_schema": FIXTURE_SCHEMA,
        "fixture_digest": _fixture_digest(corpus),
        "fixture_count": len(corpus["fixtures"]),
        "index_identity": _index_identity(root, index_dir, state_store),
        "evaluator_identity": _evaluator_identity(),
        "production_identity": production_identity,
        "run_time": {
            "started_at": _iso_utc(started_at),
            "finished_at": _iso_utc(finished_at),
            "duration_seconds": round(max(0.0, finished_at - started_at), 3),
        },
        "anchor_resolution": declarations,
        "generation": {
            "start": start_state["generation"], "end": end_state["generation"],
            "start_attempt_id": start_state["attempt_id"], "end_attempt_id": end_state["attempt_id"],
            "start_status": start_state["status"], "end_status": end_state["status"],
            "start_token": list(_state_token(start_state)),
            "end_token": list(_state_token(end_state)),
        },
        "corpus": {
            "current_lance_fts_counts": corpus_counts,
            "non_empty": True,
            "health": {
                "semantic_ready": index_health.get("semantic_ready"),
                "readiness_overview": index_health.get("readiness_overview"),
                "stale_layers": index_health.get("stale_layers"),
                "missing_layers": index_health.get("missing_layers"),
            },
        },
        "environment": environment,
        "metrics": aggregate_metrics(case_rows),
        "cases": case_rows,
        "performance": performance,
        "degraded_mode_probe": degraded,
        "operator_review_reasons": operator_reviews,
        "invalidation_reasons": [],
    }
    if "quality_gate" in corpus:
        report["quality_gate"] = corpus["quality_gate"]
    violations: list[dict[str, Any]] = []
    if baseline_path is not None:
        # Wave 1wpig (1wpaj Requirement 8): ONE no-follow handle, the exact bytes
        # from that handle hashed before they are parsed (the evaluator already
        # hashed the bytes it parses -- this preserves that property rather than
        # introducing one), and a replacement between validation and read
        # rejected from the descriptor itself.
        baseline_bytes, baseline = read_baseline_bytes(baseline_path)
        violations, _ = apply_baseline_comparison(report, baseline)
        report["comparison"]["baseline_file_sha256"] = hashlib.sha256(baseline_bytes).hexdigest()
    else:
        violations = _quality_gate_violations(report, None)
        if violations:
            report["quality_gate_evaluation"] = {"violations": violations}
    report["run_id"] = _compute_run_id(report)
    if violations:
        report["verdict"] = "fail"
    elif operator_reviews:
        report["verdict"] = "operator_review_required"
    else:
        report["verdict"] = "pass" if baseline_path is not None else "baseline"
    return report


def write_report(path: Path, report: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_stable_json_bytes(report, pretty=True))


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="repository root")
    parser.add_argument("--fixtures", required=True, help="v1 golden-query fixture JSON")
    parser.add_argument("--out", required=True, help="report JSON destination")
    parser.add_argument("--baseline", help="prior v1 report for comparison")
    # Wave 1wpie delivery council: the budget was enforced only in tests. The
    # runner took no ledger argument, so `authorize_checkpoint` had no
    # production caller and the ledger was maintained by hand -- which is how
    # it came to record 6 of 14 retained failures. Passing --slot makes the
    # gate an actual gate: it refuses before measuring, and appends the row
    # itself afterwards.
    parser.add_argument("--slot", help=f"checkpoint slot to consume; one of {list(CHECKPOINT_SLOTS)}")
    parser.add_argument("--ledger", help="checkpoint ledger JSONL to authorize against and append to")
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Standing checkpoint budget (wave 1wscp, Requirement 10)
#
# The sequence is FIXED, not a quota to spend freely: exactly baseline A/B, one
# post-confidence/routing, one post-lexical, one per ANN candidate up to three,
# one post-graph/final, and at most one documented replay. Nine slots, each
# usable once. Enforcement lives here rather than in reviewer discipline
# because an unbudgeted extra run is exactly how a measurement sequence turns
# into a search for a favourable number.
CHECKPOINT_SLOTS: tuple[str, ...] = (
    "baseline_a",
    "baseline_b",
    "post_confidence_routing",
    "post_lexical",
    "ann_candidate_1",
    "ann_candidate_2",
    "ann_candidate_3",
    "post_graph_final",
    "replay",
)
MAX_CHECKPOINT_INVOCATIONS = 9
CHECKPOINT_SEQUENCE_SECONDS = 10_800
CHECKPOINT_SEQUENCE_BYTES = 9 * 1024 * 1024
CHECKPOINT_SEQUENCE_PUBLIC_CALLS = 7_020
CHECKPOINT_INVOCATION_SECONDS = 1_200
CHECKPOINT_INVOCATION_BYTES = 1024 * 1024
CHECKPOINT_INVOCATION_PUBLIC_CALLS = 780

assert len(CHECKPOINT_SLOTS) == MAX_CHECKPOINT_INVOCATIONS


class CheckpointBudgetExhausted(Exception):
    """A cap was reached. The caller must stop and seek operator direction."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


CHECKPOINT_PUBLISHED_KIND = "published"
CHECKPOINT_FAILED_KIND = "failed_attempt"


def checkpoint_budget_state(entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Consumed and remaining budget across a checkpoint ledger.

    Two row kinds, and conflating them was a real defect caught in delivery
    review (wave 1wpie): replaying the shipped ledger through the previous
    version reported 15 invocations against a ceiling of 9, listed the same
    slot several times, and refused the very run the wave's evidence rests on.

    - A ``published`` row OCCUPIES its slot. Nine slots, each usable once.
    - A ``failed_attempt`` row does NOT occupy a slot -- a slot whose attempt
      failed is meant to be retried, which is why every failure is retained
      under its own filename. It DOES consume the cumulative time, byte and
      call budget, because a run that burned those spent what the caps bound
      and excluding it would let unfavourable runs be discarded.

    A row with no explicit kind is treated as published, so a ledger written
    before this distinction still reads conservatively rather than silently
    freeing slots.
    """
    def _is_published(entry: Mapping[str, Any]) -> bool:
        return str(entry.get("kind") or CHECKPOINT_PUBLISHED_KIND) != CHECKPOINT_FAILED_KIND

    published = [e for e in entries if _is_published(e)]
    used_slots = [str(e.get("slot") or "") for e in published]
    # Resource caps count EVERY row, failed attempts included.
    seconds = sum(float(e.get("seconds") or 0.0) for e in entries)
    report_bytes = sum(int(e.get("report_bytes") or 0) for e in entries)
    calls = sum(int(e.get("public_calls") or 0) for e in entries)
    return {
        "invocations": len(published),
        "invocations_remaining": MAX_CHECKPOINT_INVOCATIONS - len(published),
        "failed_attempts": len(entries) - len(published),
        "slots_used": used_slots,
        "slots_available": [s for s in CHECKPOINT_SLOTS if s not in set(used_slots)],
        "seconds": round(seconds, 3),
        "seconds_remaining": round(CHECKPOINT_SEQUENCE_SECONDS - seconds, 3),
        "report_bytes": report_bytes,
        "report_bytes_remaining": CHECKPOINT_SEQUENCE_BYTES - report_bytes,
        "public_calls": calls,
        "public_calls_remaining": CHECKPOINT_SEQUENCE_PUBLIC_CALLS - calls,
    }


def authorize_checkpoint(
    entries: Sequence[Mapping[str, Any]],
    slot: str,
    *,
    seconds: float = 0.0,
    report_bytes: int = 0,
    public_calls: int = 0,
) -> dict[str, Any]:
    """Authorize one checkpoint invocation, or FAIL CLOSED.

    Raises `CheckpointBudgetExhausted` when the slot is unknown, already used,
    or when the projected totals would exceed any sequence cap. Every refusal
    names its own code so the operator sees which ceiling was reached.
    """
    if slot not in CHECKPOINT_SLOTS:
        raise CheckpointBudgetExhausted(
            "unknown_checkpoint_slot",
            f"{slot!r} is not one of the fixed slots: {list(CHECKPOINT_SLOTS)}")
    state = checkpoint_budget_state(entries)
    if slot in state["slots_used"]:
        raise CheckpointBudgetExhausted(
            "checkpoint_slot_already_used",
            f"slot {slot!r} was already recorded; each slot is usable once")
    if state["invocations"] >= MAX_CHECKPOINT_INVOCATIONS:
        raise CheckpointBudgetExhausted(
            "checkpoint_invocations_exhausted",
            f"{MAX_CHECKPOINT_INVOCATIONS} invocations already recorded")
    if seconds > CHECKPOINT_INVOCATION_SECONDS:
        raise CheckpointBudgetExhausted(
            "checkpoint_invocation_seconds_exceeded",
            f"{seconds}s exceeds the per-invocation ceiling "
            f"{CHECKPOINT_INVOCATION_SECONDS}s")
    if report_bytes > CHECKPOINT_INVOCATION_BYTES:
        raise CheckpointBudgetExhausted(
            "checkpoint_invocation_bytes_exceeded",
            f"{report_bytes} bytes exceeds the per-report ceiling "
            f"{CHECKPOINT_INVOCATION_BYTES}")
    if public_calls > CHECKPOINT_INVOCATION_PUBLIC_CALLS:
        raise CheckpointBudgetExhausted(
            "checkpoint_invocation_calls_exceeded",
            f"{public_calls} calls exceeds the per-invocation ceiling "
            f"{CHECKPOINT_INVOCATION_PUBLIC_CALLS}")
    for value, remaining, code, unit in (
        (seconds, state["seconds_remaining"], "checkpoint_sequence_seconds_exhausted", "seconds"),
        (report_bytes, state["report_bytes_remaining"], "checkpoint_sequence_bytes_exhausted", "report bytes"),
        (public_calls, state["public_calls_remaining"], "checkpoint_sequence_calls_exhausted", "public calls"),
    ):
        if value > remaining:
            raise CheckpointBudgetExhausted(
                code,
                f"{value} {unit} exceeds the {remaining} remaining in the sequence budget")
    return {
        "slot": slot, "seconds": seconds, "report_bytes": report_bytes,
        "public_calls": public_calls, "authorized": True,
    }


def _append_checkpoint_row(ledger: Path, slot: str, kind: str, out_path: Path,
                           *, seconds: float, report: Mapping[str, Any]) -> None:
    """Append one ledger row for a run that actually happened.

    The ledger used to be maintained by hand, which is how it came to record 6
    of 14 retained failures and to disagree with the reports on disk. Writing
    it from the runner is what makes the budget an enforced ceiling rather than
    a narrated one.
    """
    try:
        size = out_path.stat().st_size
    except OSError:
        size = 0
    calls = 0
    tools = ((report.get("performance") or {}).get("tools") or {})
    if isinstance(tools, Mapping):
        calls = sum(int((t or {}).get("sample_count") or 0) for t in tools.values()
                    if isinstance(t, Mapping))
    row = {"slot": slot, "kind": kind, "report": out_path.name,
           "seconds": round(float(seconds), 3), "report_bytes": size,
           "public_calls": calls, "verdict": report.get("verdict"),
           "run_id": report.get("run_id")}
    try:
        with ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
    except OSError:
        pass


def load_checkpoint_ledger(path: Path) -> list[dict[str, Any]]:
    """Read the append-only checkpoint ledger; a missing ledger is empty."""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except (OSError, UnicodeError) as exc:
        raise CheckpointBudgetExhausted(
            "checkpoint_ledger_unreadable",
            f"cannot read the checkpoint ledger: {exc}") from exc
    entries: list[dict[str, Any]] = []
    for pos, line in enumerate(raw.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CheckpointBudgetExhausted(
                "checkpoint_ledger_unreadable",
                f"checkpoint ledger line {pos + 1} is not JSON: {exc}") from exc
        if not isinstance(entry, dict):
            raise CheckpointBudgetExhausted(
                "checkpoint_ledger_unreadable",
                f"checkpoint ledger line {pos + 1} is not an object")
        entries.append(entry)
    return entries


# Wave 1wpig (1wpaj Requirement 8): failures whose own subject is the output
# path.  Writing the machine-readable invalidation to a path this run just
# refused would defeat the refusal, so these codes emit to stderr only -- the
# same rule the self-contamination preflight already followed.
_UNWRITABLE_INVALIDATION_CODES = frozenset({
    "self_contaminating_artifact", "report_path_unconfined", "report_path_protected",
    "report_destination_exists", "report_publish_failed", "report_publish_unverified",
})


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    root = Path(args.root).resolve()
    fixtures_path = Path(args.fixtures).resolve()
    out_path = Path(os.path.abspath(args.out))
    baseline_path = Path(os.path.abspath(args.baseline)) if args.baseline else None
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        import indexer
        # Confinement is asserted BEFORE anything is read, run, or created.
        out_path = confined_report_path(root, out_path, role="output")
        if baseline_path is not None:
            baseline_path = confined_report_path(root, baseline_path, role="baseline")
        artifact_paths = [fixtures_path, out_path]
        if baseline_path is not None:
            artifact_paths.append(baseline_path)
        assert_eval_artifacts_excluded(root, artifact_paths, indexer)
        # Authorize BEFORE measuring: a refused run must not burn the time it
        # is being refused for.
        ledger_path = Path(os.path.abspath(args.ledger)) if args.ledger else None
        if args.slot:
            if ledger_path is None:
                raise EvaluationInvalid(
                    "checkpoint_ledger_required",
                    "--slot requires --ledger; a slot cannot be consumed without a ledger to record it in")
            authorize_checkpoint(load_checkpoint_ledger(ledger_path), args.slot)
        started = time.time()
        report = run_evaluation(root, fixtures_path, baseline_path=baseline_path, indexer=indexer)
        publish = publish_report(root, out_path, report, indexer=indexer)
        if args.slot and ledger_path is not None:
            _append_checkpoint_row(
                ledger_path, args.slot, CHECKPOINT_PUBLISHED_KIND, out_path,
                seconds=time.time() - started, report=report)
    except CheckpointBudgetExhausted as exc:
        # Fail closed and say which ceiling. Nothing was measured, so nothing
        # is appended: the slot stays available for a legitimate retry.
        print(json.dumps({"schema": REPORT_SCHEMA, "verdict": "refused",
                          "refusal": {"code": exc.code, "message": str(exc)}}),
              file=sys.stderr, flush=True)
        return 2
    except EvaluationInvalid as exc:
        report = _minimal_invalid_report(exc)
        # A failed attempt consumes the resource caps even though it frees its
        # slot; recording it is what stops unfavourable runs being discarded.
        if getattr(args, "slot", None) and getattr(args, "ledger", None):
            try:
                _append_checkpoint_row(
                    Path(os.path.abspath(args.ledger)), args.slot,
                    CHECKPOINT_FAILED_KIND, out_path, seconds=0.0, report=report)
            except OSError:
                pass
        # A self-contaminating or unconfined output must not be created; every
        # other invalid run still emits its machine-readable invalidation reason.
        if exc.code not in _UNWRITABLE_INVALIDATION_CODES:
            try:
                publish_report(root, out_path, report, indexer=None)
            except EvaluationInvalid as publish_failure:
                report["invalidation_reasons"].append(
                    {"code": publish_failure.code, "message": publish_failure.message})
        print(json.dumps(report, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps({"schema": REPORT_SCHEMA, "verdict": report["verdict"],
                      "out": str(out_path), "content_sha256": publish["content_sha256"]},
                     ensure_ascii=False, sort_keys=True))
    return 0 if report["verdict"] in ("baseline", "pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
