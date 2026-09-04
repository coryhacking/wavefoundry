#!/usr/bin/env python3
"""Mixed-artifact graph fidelity measurement (wave `1wpih` / `1wpie`).

The graph suite has deep isolated fixture coverage but no representative corpus
that reports precision and recall **per relation** through the public tools.
That gap is why cross-domain false positives survived until a live audit found
them: a fixture proves one extractor branch, while precision is a property of
the whole extraction over a realistic mixture of artifacts.

This module supplies the missing measure.  It materialises a fixed, bounded
corpus of real source files, builds a real graph over them through the same
`update_graph_index` entry the product uses, and scores the resulting edge set
against declared expectations.

Two design points carry most of the weight:

**Forbidden edges are as load-bearing as expected ones.**  A recall-only score
rewards an extractor that emits everything.  Every scored relation must declare
at least one expected edge AND at least one forbidden opportunity -- a pair of
symbols the extractor could plausibly but wrongly connect -- so precision has
something to measure.

**The matrix is frozen before implementation.**  Direction, confidence floor,
duplicate normalisation and external-node treatment are declared per relation
up front, because deciding them after seeing results is how a measurement gets
fitted to the outcome it was supposed to judge.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


FIXTURE_SCHEMA = "wavefoundry.graph-quality-fixtures/v1"
REPORT_SCHEMA = "wavefoundry.graph-quality-eval/v1"

# Requirement 10: fixed corpus and report ceilings.
MAX_CORPUS_FILES = 128
MAX_NORMALIZED_NODES = 2_000
MAX_NORMALIZED_EDGES = 5_000
MAX_REPORT_BYTES = 1024 * 1024

# Requirement 2: the FROZEN relation-to-public-tool matrix.  Declared before any
# scoring so the contract cannot be adjusted to fit an outcome.
#
#   public_tool            -- the public surface a caller would use to observe it
#   direction              -- "source_to_target"; recorded explicitly because a
#                             reversed edge is a real defect class, not a tie
#   min_confidence         -- edges below this confidence are not scored, so a
#                             speculative bind cannot inflate recall
#   external_treatment     -- "excluded": edges into `external::` targets are not
#                             scored, because binding a third-party symbol is not
#                             a claim this corpus can adjudicate
#   duplicate_normalization-- "collapse_by_triple": repeated (source, relation,
#                             target) rows collapse to one before scoring
RELATION_TOOL_MATRIX: dict[str, dict[str, str]] = {
    "calls": {
        "public_tool": "code_callhierarchy",
        "direction": "source_to_target",
        "min_confidence": "EXTRACTED",
        "external_treatment": "excluded",
        "duplicate_normalization": "collapse_by_triple",
    },
    # `imports` deliberately INCLUDES external targets.  Measured against the
    # real extractor: a Python `from svc.loader import load_settings` emits
    # `imports -> external::svc.loader.load_settings` while the corresponding
    # CALL resolves to the project node.  The external target is the faithful
    # extraction result for an import -- it records what was imported -- so
    # excluding externals here would leave the relation with nothing to score.
    "imports": {
        "public_tool": "code_dependencies",
        "direction": "source_to_target",
        "min_confidence": "EXTRACTED",
        "external_treatment": "included",
        "duplicate_normalization": "collapse_by_triple",
    },
    "defines": {
        "public_tool": "code_outline",
        "direction": "source_to_target",
        "min_confidence": "EXTRACTED",
        "external_treatment": "excluded",
        "duplicate_normalization": "collapse_by_triple",
    },
    "reads_config": {
        "public_tool": "code_references",
        "direction": "source_to_target",
        "min_confidence": "LITERAL_DERIVED",
        "external_treatment": "excluded",
        "duplicate_normalization": "collapse_by_triple",
    },
    "doc_references_code": {
        "public_tool": "wf_graph_report",
        "direction": "source_to_target",
        "min_confidence": "EXTRACTED",
        "external_treatment": "excluded",
        "duplicate_normalization": "collapse_by_triple",
    },
}

SCORED_RELATIONS = tuple(RELATION_TOOL_MATRIX)

# Confidence ordering, weakest first.  A relation's floor admits its own tier
# and everything stronger.  ``AMBIGUOUS`` is listed explicitly and sits below
# every other tier: the doc matcher emits it when a reference could bind to
# more than one symbol, and scoring such an edge as a correct extraction would
# credit a guess.  Naming it here makes the exclusion a decision rather than an
# accident of an unrecognised label.
_CONFIDENCE_ORDER = ("AMBIGUOUS", "EXTRACTED", "LITERAL_DERIVED",
                     "CONSTRUCTION_RESOLVED", "RECEIVER_RESOLVED")


class GraphQualityInvalid(Exception):
    """The graph fidelity measurement could not produce a trustworthy result."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise GraphQualityInvalid(code, message)


def digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")).hexdigest()


def confidence_admits(observed: str, floor: str) -> bool:
    """Whether an observed confidence clears a relation's declared floor."""
    try:
        return _CONFIDENCE_ORDER.index(observed) >= _CONFIDENCE_ORDER.index(floor)
    except ValueError:
        # An unknown confidence label is refused rather than assumed adequate.
        return False


# ---------------------------------------------------------------------------
# Corpus
# ---------------------------------------------------------------------------

def _edge_triple(raw: Mapping[str, Any]) -> tuple[str, str, str]:
    return (str(raw["source"]), str(raw["relation"]), str(raw["target"]))


def load_corpus(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GraphQualityInvalid(
            "missing_corpus", f"graph corpus not found: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GraphQualityInvalid(
            "invalid_corpus", f"cannot read graph corpus: {exc}") from exc
    _require(isinstance(payload, dict)
             and set(payload) <= {"schema", "files", "expected_edges",
                                  "forbidden_edges", "known_gaps"}
             and {"schema", "files", "expected_edges",
                  "forbidden_edges"} <= set(payload),
             "invalid_corpus", "graph corpus has missing or unknown top-level fields")
    _require(payload.get("schema") == FIXTURE_SCHEMA, "invalid_corpus",
             f"graph corpus schema must be {FIXTURE_SCHEMA}")

    files = payload.get("files")
    _require(isinstance(files, dict) and files, "invalid_corpus",
             "files must be a non-empty mapping of path to content")
    _require(len(files) <= MAX_CORPUS_FILES, "corpus_cap_exceeded",
             f"corpus declares {len(files)} files; the ceiling is {MAX_CORPUS_FILES}")
    for rel_path, content in files.items():
        _require(isinstance(rel_path, str) and rel_path.strip()
                 and not rel_path.startswith("/") and ".." not in rel_path.split("/"),
                 "invalid_corpus", f"unsafe or empty corpus path: {rel_path!r}")
        _require(isinstance(content, str), "invalid_corpus",
                 f"{rel_path}: content must be a string")

    seen: set[tuple[str, str, str]] = set()
    normalized: dict[str, list[dict[str, Any]]] = {}
    for bucket in ("expected_edges", "forbidden_edges"):
        rows = payload.get(bucket)
        _require(isinstance(rows, list) and rows, "invalid_corpus",
                 f"{bucket} must be a non-empty list")
        out: list[dict[str, Any]] = []
        for pos, raw in enumerate(rows):
            _require(isinstance(raw, dict)
                     and set(raw) == {"source", "relation", "target", "rationale"},
                     "invalid_corpus",
                     f"{bucket}[{pos}] needs exactly source/relation/target/rationale")
            _require(raw["relation"] in RELATION_TOOL_MATRIX, "invalid_corpus",
                     f"{bucket}[{pos}]: {raw['relation']!r} is not a scored relation")
            for field in ("source", "target", "rationale"):
                _require(isinstance(raw[field], str) and raw[field].strip(),
                         "invalid_corpus", f"{bucket}[{pos}].{field} must be non-empty")
            triple = _edge_triple(raw)
            _require(triple not in seen, "invalid_corpus",
                     f"{bucket}[{pos}]: duplicate edge declaration {triple}")
            seen.add(triple)
            out.append(dict(raw))
        normalized[bucket] = out

    # Requirement 2: every scored relation needs BOTH an expected edge and a
    # forbidden opportunity, or its precision or recall is undefined and the
    # relation would score vacuously.
    expected_relations = {r["relation"] for r in normalized["expected_edges"]}
    forbidden_relations = {r["relation"] for r in normalized["forbidden_edges"]}
    missing_expected = sorted(set(SCORED_RELATIONS) - expected_relations)
    missing_forbidden = sorted(set(SCORED_RELATIONS) - forbidden_relations)
    _require(not missing_expected, "incomplete_corpus",
             f"relations with no expected edge: {missing_expected}")
    _require(not missing_forbidden, "incomplete_corpus",
             f"relations with no forbidden opportunity: {missing_forbidden}")

    # Requirement 2 / AC-2: measured recall gaps are DECLARED, never silent.
    # Each gap names an edge the graph does not currently produce, with the
    # evidence that isolated it. Declaring one does not excuse it: the scorer
    # still counts it as a false negative, and the suite pins the gap SET, so
    # a new miss and a repaired miss both force this list to be revisited.
    gaps: list[dict[str, Any]] = []
    raw_gaps = payload.get("known_gaps") or []
    _require(isinstance(raw_gaps, list), "invalid_corpus",
             "known_gaps must be a list")
    expected_triples = {_edge_triple(r) for r in normalized["expected_edges"]}
    gap_ids: set[str] = set()
    for pos, raw in enumerate(raw_gaps):
        _require(isinstance(raw, dict)
                 and set(raw) == {"source", "relation", "target", "id", "rationale"},
                 "invalid_corpus",
                 f"known_gaps[{pos}] needs exactly source/relation/target/id/rationale")
        for field in ("source", "target", "id", "rationale"):
            _require(isinstance(raw[field], str) and raw[field].strip(),
                     "invalid_corpus", f"known_gaps[{pos}].{field} must be non-empty")
        _require(raw["relation"] in RELATION_TOOL_MATRIX, "invalid_corpus",
                 f"known_gaps[{pos}]: {raw['relation']!r} is not a scored relation")
        _require(raw["id"] not in gap_ids, "invalid_corpus",
                 f"known_gaps[{pos}]: duplicate gap id {raw['id']!r}")
        gap_ids.add(raw["id"])
        # A gap must name an edge the corpus actually EXPECTS. A gap for an
        # unexpected edge would be a claim about nothing.
        _require(_edge_triple(raw) in expected_triples, "invalid_corpus",
                 f"known_gaps[{pos}] does not correspond to any expected edge")
        gaps.append(dict(raw))

    return {"schema": FIXTURE_SCHEMA, "files": dict(files), "known_gaps": gaps,
            **normalized}


def materialize(root: Path, corpus: Mapping[str, Any]) -> list[Path]:
    """Write the corpus files under ``root`` and return them in declared order."""
    written: list[Path] = []
    for rel_path, content in corpus["files"].items():
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(target)
    return written


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def observed_edges(payload: Mapping[str, Any]) -> set[tuple[str, str, str]]:
    """Scored edges from a graph payload, matrix rules applied.

    Applies, in order: relation filter, external exclusion, confidence floor,
    then duplicate collapse.  Every one of those is a declared matrix rule, so
    an edge that survives is one the matrix says is in scope.
    """
    kept: set[tuple[str, str, str]] = set()
    for edge in payload.get("edges", []) or []:
        if not isinstance(edge, Mapping):
            continue
        relation = str(edge.get("relation") or "")
        rules = RELATION_TOOL_MATRIX.get(relation)
        if rules is None:
            continue
        source, target = str(edge.get("source") or ""), str(edge.get("target") or "")
        if not source or not target:
            continue
        if rules["external_treatment"] == "excluded" and (
                source.startswith("external::") or target.startswith("external::")):
            continue
        confidence = str(edge.get("confidence") or "EXTRACTED")
        if not confidence_admits(confidence, rules["min_confidence"]):
            continue
        kept.add((source, relation, target))   # collapse_by_triple
    return kept


def score_relations(observed: Iterable[tuple[str, str, str]],
                    corpus: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Per-relation true/false positives, false negatives, precision, recall.

    A false positive is a FORBIDDEN edge that appeared, not merely any
    unexpected edge: a bounded corpus cannot enumerate every legitimate edge a
    real extractor emits, so counting all unexpected edges as errors would
    measure the corpus's incompleteness rather than the extractor's precision.
    """
    observed_set = set(observed)
    expected_by_relation: dict[str, set[tuple[str, str, str]]] = {}
    forbidden_by_relation: dict[str, set[tuple[str, str, str]]] = {}
    for row in corpus["expected_edges"]:
        expected_by_relation.setdefault(row["relation"], set()).add(_edge_triple(row))
    for row in corpus["forbidden_edges"]:
        forbidden_by_relation.setdefault(row["relation"], set()).add(_edge_triple(row))

    report: dict[str, dict[str, Any]] = {}
    for relation in SCORED_RELATIONS:
        expected = expected_by_relation.get(relation, set())
        forbidden = forbidden_by_relation.get(relation, set())
        true_positives = sorted(expected & observed_set)
        false_negatives = sorted(expected - observed_set)
        false_positives = sorted(forbidden & observed_set)
        tp, fp, fn = len(true_positives), len(false_positives), len(false_negatives)
        precision = tp / (tp + fp) if (tp + fp) else None
        recall = tp / (tp + fn) if (tp + fn) else None
        report[relation] = {
            "public_tool": RELATION_TOOL_MATRIX[relation]["public_tool"],
            "direction": RELATION_TOOL_MATRIX[relation]["direction"],
            "min_confidence": RELATION_TOOL_MATRIX[relation]["min_confidence"],
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": None if precision is None else round(precision, 8),
            "recall": None if recall is None else round(recall, 8),
            "missed_edges": [list(t) for t in false_negatives],
            "forbidden_edges_emitted": [list(t) for t in false_positives],
        }
    return report


def corpus_within_bounds(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Node and edge counts against the Requirement 10 ceilings."""
    nodes = len(payload.get("nodes", []) or [])
    edges = len(payload.get("edges", []) or [])
    return {
        "nodes": nodes, "edges": edges,
        "node_ceiling": MAX_NORMALIZED_NODES, "edge_ceiling": MAX_NORMALIZED_EDGES,
        "within_bounds": nodes <= MAX_NORMALIZED_NODES and edges <= MAX_NORMALIZED_EDGES,
    }


# ---------------------------------------------------------------------------
# Evidence/Data classification controls (Requirement 11 and 12)
#
# The frozen expectation for each control artifact. These live under this
# wave's own evidence directory because that is where the walker actually
# indexes them: a 2026-09-03 census of the persisted graph found `docs/evals/`
# and `docs/reports/` contribute ZERO nodes each, while wave evidence trees
# contribute 2,758. A control filed beside the other eval fixtures could never
# be classified, so it would pass vacuously rather than prove anything.
CONTROL_DIRECTORY = (
    "docs/waves/1wpih index-quality-evaluation-and-ranking/evidence"
)
CLASSIFICATION_CONTROLS: dict[str, dict[str, Any]] = {
    "machine-result-control.json": {
        "expected_evidence": True,
        "domain": "machine_result",
        "why": "explicit producer/schema provenance plus a machine-run signature",
    },
    "design-tokens-control.json": {
        "expected_evidence": False,
        "domain": "design_tokens",
        "why": "a design-token document; repeated-key shape is not provenance",
    },
    "service-config-control.json": {
        "expected_evidence": False,
        "domain": "configuration",
        "why": "service configuration; a `command` property is not a run record",
    },
    "user-authored-data-control.json": {
        "expected_evidence": False,
        "domain": "user_authored",
        "why": "hand-authored reference data with no provenance or run signature",
    },
}


def score_classification_controls(
    observed: Mapping[str, bool],
    *,
    controls: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Score observed Evidence/Data verdicts against the frozen expectation.

    Requirement 12: the scorer must FAIL an injected false positive on a
    legitimate control and an injected false negative on the provenance-backed
    machine-result control. Both are ordinary mismatches here, reported with
    the direction named so a reader can tell which failure mode fired.

    A control that is MISSING from `observed` fails too. Silence means the
    artifact was never indexed, which is exactly the vacuous pass Requirement
    11 forbids -- it must not read as "no mismatch, therefore correct".
    """
    table = dict(controls or CLASSIFICATION_CONTROLS)
    rows: list[dict[str, Any]] = []
    false_positives: list[str] = []
    false_negatives: list[str] = []
    unobserved: list[str] = []
    for name, spec in sorted(table.items()):
        expected = bool(spec["expected_evidence"])
        if name not in observed:
            unobserved.append(name)
            rows.append({
                "control": name, "domain": spec["domain"],
                "expected_evidence": expected, "observed_evidence": None,
                "status": "not_observed",
            })
            continue
        actual = bool(observed[name])
        if actual == expected:
            status = "match"
        elif actual and not expected:
            status = "false_positive"
            false_positives.append(name)
        else:
            status = "false_negative"
            false_negatives.append(name)
        rows.append({
            "control": name, "domain": spec["domain"],
            "expected_evidence": expected, "observed_evidence": actual,
            "status": status,
        })
    return {
        "controls": rows,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "not_observed": unobserved,
        "passed": not (false_positives or false_negatives or unobserved),
    }


# ---------------------------------------------------------------------------
# Report generation (Requirement 9)
#
# Scored numbers are only half of a report.  Without identity binding, a
# baseline and a post report can differ for reasons that have nothing to do
# with extraction quality: a different corpus, a different evaluator, a
# different machine, a different graph builder.  Every identity field below
# exists so a reader can tell WHICH of those changed between two reports
# instead of assuming the delta belongs to the extractor.

REPORT_LABELS = ("baseline", "post")

MAX_REPORT_PAIR_BYTES = 2 * 1024 * 1024


def _file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise GraphQualityInvalid(
            "unreadable_source", f"cannot identify {path.name}: {exc}") from exc


def evaluator_identity() -> dict[str, str]:
    """Identity of the measuring instrument."""
    return {
        "source_sha256": _file_sha256(Path(__file__).resolve()),
        "report_schema": REPORT_SCHEMA,
        "fixture_schema": FIXTURE_SCHEMA,
    }


def production_identity() -> dict[str, str]:
    """Identity of the extraction and query code under measurement.

    Deliberately separate from ``evaluator_identity``: a baseline/post pair is
    normally the SAME instrument reading two different productions.  One
    combined digest would hide the very difference being measured.
    """
    return {
        # Where the measured production was LOADED from, which is not always
        # the repository being reported on: a baseline is normally taken from
        # a checkout of the predecessor code while provenance still points at
        # the working repository. Without this field a reader can misread
        # `repository_identity.dirty` as describing the production too.
        "source_root": str(_HERE),
        "graph_indexer_sha256": _file_sha256(_HERE / "graph_indexer.py"),
        "graph_query_sha256": _file_sha256(_HERE / "graph_query.py"),
        "graph_cluster_sha256": _file_sha256(_HERE / "graph_cluster.py"),
    }


def builder_versions() -> dict[str, str]:
    import graph_cluster
    import graph_indexer
    return {
        "graph_builder_version": str(graph_indexer.GRAPH_BUILDER_VERSION),
        "graph_schema_version": str(graph_indexer.GRAPH_SCHEMA_VERSION),
        "cluster_builder_version": str(graph_cluster.CLUSTER_BUILDER_VERSION),
        "cluster_schema_version": str(graph_cluster.CLUSTER_SCHEMA_VERSION),
    }


def graph_input_fingerprint(root: Path, files: Sequence[Path],
                            *, walker_version: str, chunker_version: str) -> str:
    """Digest of exactly what the builder was fed.

    Content, not just names: a corpus file edited in place would otherwise
    produce a matching fingerprint across two genuinely different builds.
    """
    parts = [f"walker={walker_version}", f"chunker={chunker_version}"]
    for path in sorted(files, key=lambda p: str(p.relative_to(root))):
        rel = str(path.relative_to(root)).replace("\\", "/")
        parts.append(f"{rel}={_file_sha256(path)}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _git_value(root: Path, *args: str) -> str | None:
    """One git answer, or ``None`` when git cannot supply it.

    The call chain raises ``OSError`` when git is absent or the root is gone
    and ``subprocess.SubprocessError`` (``TimeoutExpired`` among them) when the
    spawn misbehaves.  Both mean the same thing here -- provenance is
    unavailable -- and neither should abort a measurement run.
    """
    import subprocess

    try:
        from subprocess_util import isolated_run
    except ImportError:
        return None
    try:
        completed = isolated_run(["git", *args], cwd=str(root),
                                 capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def repository_identity(root: Path) -> dict[str, Any]:
    """Which repository state produced this report.

    ``dirty`` is load-bearing rather than cosmetic: a report taken on a dirty
    tree cannot be reproduced from its commit alone, and a reader comparing
    two reports needs to know that before trusting a delta.
    """
    commit = _git_value(root, "rev-parse", "HEAD")
    status = _git_value(root, "status", "--porcelain")
    return {
        "root": str(root),
        "commit": commit,
        "dirty": None if status is None else bool(status),
    }


def community_backend() -> str:
    """Which clustering backend this environment would actually use."""
    try:
        import graph_cluster
    except ImportError:  # pragma: no cover - the module ships beside this one
        return "unavailable"
    probe = getattr(graph_cluster, "_load_leiden_backend", None)
    if probe is None:  # pragma: no cover - only if the cluster module is restructured
        return "unknown"
    return "igraph+leidenalg" if probe() else "label_propagation"


def environment_snapshot() -> dict[str, Any]:
    import platform
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "system": platform.system(),
        "machine": platform.machine(),
        "community_backend": community_backend(),
    }


def _utc_now() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_graph_over_corpus(corpus: Mapping[str, Any], root: Path,
                            *, walker_version: str = "1",
                            chunker_version: str = "1") -> tuple[list[Path], dict[str, Any]]:
    """Materialize the corpus under ``root`` and build a real graph over it.

    This is the same ``update_graph_index`` entry the product uses; the report
    is worthless if it measures a bespoke extraction path.
    """
    import graph_indexer

    files = materialize(root, corpus)
    meta = {str(p.relative_to(root)): {"hash": f"h{i}"} for i, p in enumerate(files)}
    payload = graph_indexer.update_graph_index(
        root=root, index_dir=root / ".wavefoundry" / "index", layer="project",
        files=files, current_file_meta=meta, changed=set(meta), removed=set(),
        walker_version=walker_version, chunker_version=chunker_version, verbose=False)
    return files, payload


def observed_control_verdicts(root: Path) -> dict[str, bool]:
    """Classify each control artifact through the production classifier.

    Reads the controls from the repository rather than the corpus: they are
    fixtures about CONTENT, and Requirement 12 pins that the verdict survives
    a move, so their location is not part of what is being measured here.
    """
    import graph_indexer

    classify = getattr(graph_indexer, "classify_evidence_payload", None)
    if classify is None:
        # A production that predates the classifier reports NOTHING rather
        # than a clean sheet: every control comes back `not_observed`, which
        # scores as a failure. That is the honest baseline reading -- silence
        # must never be mistaken for correct classification.
        return {}

    verdicts: dict[str, bool] = {}
    directory = root / CONTROL_DIRECTORY
    for name in CLASSIFICATION_CONTROLS:
        path = directory / name
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        is_evidence, _reasons = classify(payload)
        verdicts[name] = bool(is_evidence)
    return verdicts


def build_report(corpus_path: Path, *, label: str, root: Path | None = None) -> dict[str, Any]:
    """Score one full run and bind every identity Requirement 9 names."""
    import tempfile

    if label not in REPORT_LABELS:
        raise GraphQualityInvalid(
            "unknown_label", f"label must be one of {', '.join(REPORT_LABELS)}")
    repo_root = (root or Path.cwd()).resolve()
    corpus = load_corpus(corpus_path)
    started = _utc_now()
    walker_version, chunker_version = "1", "1"
    with tempfile.TemporaryDirectory() as tmp:
        build_root = Path(tmp)
        files, payload = build_graph_over_corpus(
            corpus, build_root,
            walker_version=walker_version, chunker_version=chunker_version)
        fingerprint = graph_input_fingerprint(
            build_root, files,
            walker_version=walker_version, chunker_version=chunker_version)
        observed = observed_edges(payload)
        relations = score_relations(observed, corpus)
        bounds = corpus_within_bounds(payload)
    controls = score_classification_controls(observed_control_verdicts(repo_root))
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "label": label,
        "run_started_at": started,
        "run_completed_at": _utc_now(),
        "corpus": {
            "path": str(corpus_path),
            "digest": digest(corpus),
            "files": len(corpus["files"]),
            "expected_edges": len(corpus["expected_edges"]),
            "forbidden_edges": len(corpus["forbidden_edges"]),
            "known_gaps": len(corpus["known_gaps"]),
        },
        "evaluator_identity": evaluator_identity(),
        "production_identity": production_identity(),
        "builder_versions": builder_versions(),
        "graph_input_fingerprint": fingerprint,
        "repository_identity": repository_identity(repo_root),
        "environment": environment_snapshot(),
        "scored_relations": list(SCORED_RELATIONS),
        "public_tools": sorted({spec["public_tool"] for spec in RELATION_TOOL_MATRIX.values()}),
        "relations": relations,
        "classification_controls": controls,
        "graph_bounds": bounds,
        "totals": {
            "true_positives": sum(row["true_positives"] for row in relations.values()),
            "false_positives": sum(row["false_positives"] for row in relations.values()),
            "false_negatives": sum(row["false_negatives"] for row in relations.values()),
        },
    }
    report["report_digest"] = digest(report)
    return report


def assert_report_is_excluded_from_the_corpus(path: Path, root: Path) -> None:
    """Refuse to write a report that the indexer would then read back.

    `.json` is an indexed source extension, so a report written under a path no
    ignore rule covers becomes a search answer about itself and contaminates
    the next measurement.  A file OUTSIDE the repository cannot be indexed and
    is left alone, which is what makes scratch destinations usable.
    """
    import indexer

    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return
    if indexer._matches_ignore(rel, indexer._load_ignore_patterns(root)):
        return
    raise GraphQualityInvalid(
        "self_contaminating_artifact",
        f"the report would enter the retrieval corpus: {rel}; exclude it in .aiignore")


def write_report(report: Mapping[str, Any], path: Path,
                 *, root: Path | None = None) -> int:
    """Serialize one report, refusing to exceed the Requirement 10 ceiling.

    When ``root`` is supplied the destination is also checked against that
    repository's ignore rules, so a report cannot silently become part of the
    corpus it measures.
    """
    if root is not None:
        assert_report_is_excluded_from_the_corpus(path, root)
    encoded = json.dumps(report, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    if len(encoded) > MAX_REPORT_BYTES:
        raise GraphQualityInvalid(
            "report_too_large",
            f"{len(encoded)} bytes exceeds the {MAX_REPORT_BYTES}-byte ceiling")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)
    return len(encoded)


def verify_report_pair(baseline: Mapping[str, Any], post: Mapping[str, Any]) -> dict[str, Any]:
    """What a baseline/post pair is allowed to conclude.

    A delta is attributable to production only when the corpus and the
    instrument held still.  When they did not, the comparison is reported as
    unattributable rather than quietly presented as a quality change.
    """
    same_corpus = baseline.get("corpus", {}).get("digest") == post.get("corpus", {}).get("digest")
    same_evaluator = baseline.get("evaluator_identity") == post.get("evaluator_identity")
    production_changed = baseline.get("production_identity") != post.get("production_identity")
    return {
        "same_corpus": same_corpus,
        "same_evaluator": same_evaluator,
        "production_changed": production_changed,
        "delta_attributable_to_production": bool(same_corpus and same_evaluator),
        "false_positive_delta": (post.get("totals", {}).get("false_positives")
                                 - baseline.get("totals", {}).get("false_positives")),
        "false_negative_delta": (post.get("totals", {}).get("false_negatives")
                                 - baseline.get("totals", {}).get("false_negatives")),
        "true_positive_delta": (post.get("totals", {}).get("true_positives")
                                - baseline.get("totals", {}).get("true_positives")),
    }


__all__ = [
    "FIXTURE_SCHEMA", "REPORT_SCHEMA", "RELATION_TOOL_MATRIX", "SCORED_RELATIONS",
    "MAX_CORPUS_FILES", "MAX_NORMALIZED_NODES", "MAX_NORMALIZED_EDGES",
    "MAX_REPORT_BYTES", "MAX_REPORT_PAIR_BYTES", "REPORT_LABELS",
    "GraphQualityInvalid", "digest", "confidence_admits",
    "load_corpus", "materialize", "observed_edges", "score_relations",
    "corpus_within_bounds", "CONTROL_DIRECTORY", "CLASSIFICATION_CONTROLS",
    "score_classification_controls", "evaluator_identity", "production_identity",
    "builder_versions", "graph_input_fingerprint", "repository_identity",
    "community_backend", "environment_snapshot", "build_graph_over_corpus",
    "observed_control_verdicts", "build_report", "write_report",
    "verify_report_pair", "assert_report_is_excluded_from_the_corpus",
]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--report", type=Path,
                        help="write a full scored report to this path")
    parser.add_argument("--label", choices=list(REPORT_LABELS),
                        help="which side of the baseline/post pair this run is")
    parser.add_argument("--root", type=Path, default=None,
                        help="repository root for provenance and control lookup")
    args = parser.parse_args(argv)

    if bool(args.report) != bool(args.label):
        parser.error("--report and --label are used together")

    if not args.report:
        corpus = load_corpus(args.corpus)
        print(json.dumps({
            "status": "ok",
            "files": len(corpus["files"]),
            "expected_edges": len(corpus["expected_edges"]),
            "forbidden_edges": len(corpus["forbidden_edges"]),
            "scored_relations": list(SCORED_RELATIONS),
            "corpus_digest": digest(corpus),
        }, indent=2))
        return 0

    # Resolved once so the writer's contamination check runs on the SAME root
    # the report was built against, including the default cwd case.
    repo_root = (args.root or Path.cwd()).resolve()
    try:
        report = build_report(args.corpus, label=args.label, root=repo_root)
        written = write_report(report, args.report, root=repo_root)
    except GraphQualityInvalid as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps({
        "status": "ok",
        "report": str(args.report),
        "label": report["label"],
        "bytes": written,
        "report_digest": report["report_digest"],
        "totals": report["totals"],
        "classification_controls_passed": report["classification_controls"]["passed"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
