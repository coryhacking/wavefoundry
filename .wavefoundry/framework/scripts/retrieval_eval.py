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
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


REPORT_SCHEMA = "wavefoundry.retrieval-eval/v1"
FIXTURE_SCHEMA = "wavefoundry.retrieval-eval-fixtures/v1"
TOOLS = ("code_ask", "code_search", "docs_search", "code_lexical")
SPLITS = ("calibration", "holdout")
ANCHOR_TYPES = ("symbol", "content", "section", "line_span", "path")
QUESTION_TYPES = (
    "navigational", "explanatory", "instructional", "artifact_anchored", "assessment",
)

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
PRODUCTION_RETRIEVAL_MODULES = (
    "server_impl.py", "indexer.py", "chunker.py", "index_state_store.py",
    "graph_indexer.py", "graph_query.py", "accel_embedder.py",
)
PRODUCTION_VERSION_CONSTANTS = {
    "chunker": ("chunker.py", "CHUNKER_VERSION"),
    "walker": ("indexer.py", "WALKER_VERSION"),
    "graph_builder": ("graph_indexer.py", "GRAPH_BUILDER_VERSION"),
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


def _retrieval_toggles() -> dict[str, bool]:
    """Effective (set and non-empty) state of every retrieval kill switch."""
    return {name: bool(os.environ.get(name)) for name in RETRIEVAL_TOGGLE_ENVS}


class EvaluationInvalid(RuntimeError):
    """The evaluation could not produce a trustworthy gate result."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


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
                "relevance", "provenance", "rationale"}
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
        item = dict(raw)
        item["id"] = fixture_id
        item["class"] = case_class
        item["query"] = query.strip()
        item["applicable_tools"] = list(applicable)
        item["excluded_tools"] = dict(excluded)
        item["relevance"] = relevance
        item["abstention_expected"] = abstention
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


def _validate_baseline_compatibility(report: Mapping[str, Any],
                                     baseline: Mapping[str, Any]) -> tuple[bool, bool]:
    _require(baseline.get("schema") == REPORT_SCHEMA, "invalid_baseline",
             "baseline report schema mismatch")
    _require(baseline.get("fixture_schema") == report.get("fixture_schema") == FIXTURE_SCHEMA,
             "invalid_baseline", "baseline fixture schema mismatch")
    _require(baseline.get("fixture_digest") == report.get("fixture_digest"), "invalid_baseline",
             "baseline fixture digest differs from the current corpus")
    _require(baseline.get("index_identity") == report.get("index_identity") and
             isinstance(report.get("index_identity"), Mapping),
             "invalid_baseline", "baseline repository/index store identity differs")
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
        "retrieval_toggles",
    )
    baseline_environment = baseline.get("environment")
    current_environment = report.get("environment")
    _require(isinstance(baseline_environment, Mapping) and isinstance(current_environment, Mapping),
             "invalid_baseline", "baseline runtime environment is missing")
    for key in environment_keys:
        _require(key in baseline_environment and key in current_environment and
                 baseline_environment[key] == current_environment[key],
                 "invalid_baseline", f"baseline runtime environment differs for {key}")
    baseline_epoch = _validated_epoch(baseline, "baseline")
    current_epoch = _validated_epoch(report, "current report")
    _require(current_epoch[0] >= baseline_epoch[0], "invalid_baseline",
             "current index generation predates the baseline")
    if current_epoch[0] == baseline_epoch[0]:
        _require(current_epoch[1] == baseline_epoch[1], "invalid_baseline",
                 "same generation has a different build attempt identity")
    same_production = baseline_production["digest"] == current_production["digest"]
    return current_epoch == baseline_epoch, same_production


def apply_baseline_comparison(report: dict[str, Any], baseline: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    same_generation, same_production = _validate_baseline_compatibility(report, baseline)
    # Only an identical production implementation on the same frozen generation
    # measures run-to-run jitter; a same-generation production change is a
    # before/after receipt and inherits the baseline pair's recorded jitter.
    same_pair = same_generation and same_production
    violations = _quality_comparison(report, baseline)
    violations.extend(_quality_gate_violations(report, baseline))
    operator_reviews: list[dict[str, Any]] = []
    for tool in TOOLS:
        current_perf = report["performance"]["tools"][tool]
        baseline_perf = baseline.get("performance", {}).get("tools", {}).get(tool, {})
        cur_p95 = current_perf.get("warm_p95_ms")
        base_p95 = baseline_perf.get("warm_p95_ms")
        if cur_p95 is None or base_p95 is None:
            continue
        if same_pair:
            lower = min(float(cur_p95), float(base_p95))
            jitter = abs(float(cur_p95) - float(base_p95)) / lower if lower > 0 else 0.0
            current_perf["jitter_ratio"] = round(jitter, 8)
            current_perf["jitter_source"] = "same_generation_pair"
        else:
            jitter = baseline_perf.get("jitter_ratio")
            _require(isinstance(jitter, (int, float)), "invalid_baseline",
                     f"baseline lacks same-generation jitter for {tool}")
            current_perf["jitter_ratio"] = float(jitter)
            current_perf["jitter_source"] = "baseline_same_generation_pair"
        allowed = max(0.25, 3.0 * float(jitter))
        threshold = float(base_p95) * (1.0 + allowed)
        current_perf["permitted_relative_regression"] = round(allowed, 8)
        current_perf["baseline_warm_p95_ms"] = base_p95
        current_perf["warm_p95_threshold_ms"] = round(threshold, 6)
        if float(cur_p95) > threshold:
            violations.append({"kind": "latency_regression", "tool": tool,
                               "baseline_ms": base_p95, "current_ms": cur_p95,
                               "threshold_ms": round(threshold, 6)})
        cur_bytes = int(current_perf.get("max_response_bytes") or 0)
        base_bytes = int(baseline_perf.get("max_response_bytes") or 0)
        byte_threshold = base_bytes + max(base_bytes * 0.15, 4096.0)
        current_perf["baseline_max_response_bytes"] = base_bytes
        current_perf["response_bytes_threshold"] = math.floor(byte_threshold)
        if cur_bytes > byte_threshold:
            violations.append({"kind": "response_size_regression", "tool": tool,
                               "baseline_bytes": base_bytes, "current_bytes": cur_bytes,
                               "threshold_bytes": math.floor(byte_threshold)})
    if same_pair:
        comparison_kind = "same_generation_pair"
    elif same_generation:
        comparison_kind = "production_change_same_generation"
    else:
        comparison_kind = "cross_generation"
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
    }
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
        p95 = _nearest_rank_p95(performance_samples[tool])
        max_bytes = max(response_sizes[tool], default=0)
        performance["tools"][tool] = {
            "sample_count": len(performance_samples[tool]),
            "warm_p95_ms": round(p95, 6) if p95 is not None else None,
            "max_response_bytes": max_bytes,
        }
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
        try:
            baseline_bytes = baseline_path.read_bytes()
            baseline = json.loads(baseline_bytes.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise EvaluationInvalid("invalid_baseline", f"cannot read baseline report: {exc}") from exc
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
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    root = Path(args.root).resolve()
    fixtures_path = Path(args.fixtures).resolve()
    out_path = Path(args.out).resolve()
    baseline_path = Path(args.baseline).resolve() if args.baseline else None
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        import indexer
        artifact_paths = [fixtures_path, out_path]
        if baseline_path is not None:
            artifact_paths.append(baseline_path)
        assert_eval_artifacts_excluded(root, artifact_paths, indexer)
        report = run_evaluation(root, fixtures_path, baseline_path=baseline_path, indexer=indexer)
    except EvaluationInvalid as exc:
        report = _minimal_invalid_report(exc)
        # A self-contaminating output must not be created; every other invalid
        # run still emits its machine-readable invalidation reason.
        if exc.code != "self_contaminating_artifact":
            write_report(out_path, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2
    write_report(out_path, report)
    print(json.dumps({"schema": REPORT_SCHEMA, "verdict": report["verdict"],
                      "out": str(out_path)}, ensure_ascii=False, sort_keys=True))
    return 0 if report["verdict"] in ("baseline", "pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
