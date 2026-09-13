"""Tests for the mixed-artifact graph fidelity measurement (wave `1wpie`)."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import graph_cluster  # noqa: E402
import graph_indexer  # noqa: E402
import graph_quality_eval as subject  # noqa: E402
import index_paths  # noqa: E402
import indexer  # noqa: E402
import retrieval_eval  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[3].parent
CORPUS = REPO_ROOT / "docs" / "evals" / "graph-quality-golden.json"


def _build(corpus):
    """Materialize the corpus and build a real graph over it.

    Wave 1xny6 AC-11: this delegates to the PUBLIC
    ``graph_quality_eval.build_graph_over_corpus`` rather than re-stating its
    body, so the tests and the product cannot drift over what "a real build"
    means. The only thing left here is ownership of the temporary directory.
    """
    tmp = tempfile.TemporaryDirectory()
    _files, payload = subject.build_graph_over_corpus(corpus, Path(tmp.name))
    return tmp, payload


class EvidenceClassifierTests(unittest.TestCase):
    """Wave 1wpie AC-11 and requirements 4/12: classification is CONTENT-only,
    so it survives a move or rename and never fires on legitimate data."""

    def test_explicit_provenance_and_run_signature_both_qualify(self):
        for payload, label in (
            ({"schema": "wavefoundry.machine-result/v1", "rows": []}, "explicit schema"),
            ({"generated_by": "run_tests.py", "rows": []}, "explicit producer"),
            ({"captured_at": "2026-01-01", "file_digests": {}}, "timestamp + digest"),
            ({"recorded_at": "2026-01-01", "command": "pytest"}, "timestamp + command"),
        ):
            with self.subTest(case=label):
                is_evidence, reasons = graph_indexer.classify_evidence_payload(payload)
                self.assertTrue(is_evidence)
                self.assertTrue(reasons, "a classification must state its reason")

    def test_a_partial_signal_is_not_enough(self):
        # Each half alone is ordinary: plenty of hand-authored documents carry a
        # date, and plenty carry a checksum. Only the PAIR says machine run.
        for payload in ({"captured_at": "2026-01-01"},
                        {"file_digests": {}},
                        {"a": 1, "b": 2},
                        {"schema": ""}):
            with self.subTest(payload=list(payload)):
                self.assertFalse(graph_indexer.classify_evidence_payload(payload)[0])

    def test_non_dict_payloads_are_refused(self):
        for payload in ([1, 2, 3], "text", None, 42):
            self.assertFalse(graph_indexer.classify_evidence_payload(payload)[0])

    def test_classification_is_invariant_to_move_and_rename(self):
        # Requirement 12. The verdict depends on the payload alone, so the same
        # bytes classify identically wherever they live and whatever they are
        # called. This is what rules out any path-prefix rule.
        payload = {"captured_at": "2026-01-01", "framework_inputs_hash": "abc"}
        first = graph_indexer.classify_evidence_payload(payload)
        second = graph_indexer.classify_evidence_payload(dict(payload))
        self.assertEqual(first, second)
        self.assertTrue(first[0])

    def test_legitimate_repository_data_is_never_classified(self):
        # Requirement 4's positive controls, as real shapes rather than toys.
        for payload, label in (
            ({"mcpServers": {"wavefoundry": {"command": "python3"}}}, "mcp config"),
            ({"color": {"fg": "#000"}, "space": {"sm": 4}}, "design tokens"),
            ({"$schema": "https://json-schema.org/draft/2020-12/schema",
              "properties": {"a": {"type": "string"}}}, "json schema"),
            ({"review": {"enabled": True}, "lanes": ["code"]}, "workflow config"),
        ):
            with self.subTest(case=label):
                self.assertFalse(graph_indexer.classify_evidence_payload(payload)[0])

    def test_a_config_file_that_merely_mentions_a_command_is_not_evidence(self):
        # `.mcp.json` carries a `command` key. Without a capture timestamp it
        # must stay ordinary, or every launcher config becomes evidence.
        self.assertFalse(graph_indexer.classify_evidence_payload(
            {"mcpServers": {"x": {"command": "python3"}}, "command": "python3"})[0])


class MatrixTests(unittest.TestCase):
    """Requirement 2: the matrix is frozen and complete before scoring."""

    def test_every_scored_relation_declares_the_full_contract(self):
        required = {"public_tool", "direction", "min_confidence",
                    "external_treatment", "duplicate_normalization"}
        for relation, rules in subject.RELATION_TOOL_MATRIX.items():
            with self.subTest(relation=relation):
                self.assertEqual(required, set(rules))
                self.assertIn(rules["external_treatment"], ("included", "excluded"))
                self.assertEqual("source_to_target", rules["direction"])

    def test_ambiguous_is_the_weakest_confidence_and_is_excluded_by_default(self):
        # A doc match the extractor could not bind uniquely must not be scored
        # as a correct extraction.
        self.assertFalse(subject.confidence_admits("AMBIGUOUS", "EXTRACTED"))
        self.assertTrue(subject.confidence_admits("EXTRACTED", "EXTRACTED"))
        self.assertTrue(subject.confidence_admits("RECEIVER_RESOLVED", "LITERAL_DERIVED"))
        self.assertFalse(subject.confidence_admits("EXTRACTED", "LITERAL_DERIVED"))

    def test_an_unknown_confidence_label_is_refused_not_assumed_adequate(self):
        self.assertFalse(subject.confidence_admits("SOMETHING_NEW", "EXTRACTED"))

    def test_imports_includes_externals_and_calls_does_not(self):
        # Measured against the real extractor: an import's faithful target is
        # the external specifier, while a call must resolve to a project node.
        self.assertEqual("included",
                         subject.RELATION_TOOL_MATRIX["imports"]["external_treatment"])
        self.assertEqual("excluded",
                         subject.RELATION_TOOL_MATRIX["calls"]["external_treatment"])


class CorpusTests(unittest.TestCase):
    def _reject(self, payload):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "corpus.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(subject.GraphQualityInvalid) as caught:
                subject.load_corpus(path)
        return caught.exception

    def setUp(self):
        if not CORPUS.is_file():
            self.skipTest("graph corpus is not present in this tree")
        self.corpus = subject.load_corpus(CORPUS)

    def test_a_relation_without_a_forbidden_opportunity_is_refused(self):
        # Recall alone rewards an extractor that emits everything, so a
        # relation with no forbidden edge cannot be scored.
        payload = json.loads(CORPUS.read_text(encoding="utf-8"))
        payload["forbidden_edges"] = [
            r for r in payload["forbidden_edges"] if r["relation"] != "reads_config"]
        error = self._reject(payload)
        self.assertEqual("incomplete_corpus", error.code)
        self.assertIn("reads_config", str(error))

    def test_a_relation_without_an_expected_edge_is_refused(self):
        payload = json.loads(CORPUS.read_text(encoding="utf-8"))
        payload["expected_edges"] = [
            r for r in payload["expected_edges"] if r["relation"] != "calls"]
        error = self._reject(payload)
        self.assertEqual("incomplete_corpus", error.code)
        self.assertIn("calls", str(error))

    def test_the_file_ceiling_is_enforced(self):
        payload = json.loads(CORPUS.read_text(encoding="utf-8"))
        payload["files"] = {f"f{i}.py": "x = 1\n"
                            for i in range(subject.MAX_CORPUS_FILES + 1)}
        self.assertEqual("corpus_cap_exceeded", self._reject(payload).code)

    def test_unsafe_corpus_paths_are_refused(self):
        for bad in ("/etc/passwd", "../escape.py"):
            with self.subTest(path=bad):
                payload = json.loads(CORPUS.read_text(encoding="utf-8"))
                payload["files"] = {bad: "x = 1\n"}
                self.assertEqual("invalid_corpus", self._reject(payload).code)

    def test_the_corpus_is_excluded_from_the_retrieval_index(self):
        retrieval_eval.assert_eval_artifacts_excluded(REPO_ROOT, [CORPUS], indexer)


class ScoringAgainstARealGraphTests(unittest.TestCase):
    """AC-1, AC-2 and AC-9: score a real build, and prove the scorer moves."""

    @classmethod
    def setUpClass(cls):
        if not CORPUS.is_file():
            raise unittest.SkipTest("graph corpus is not present in this tree")
        cls.corpus = subject.load_corpus(CORPUS)
        cls._tmp, cls.payload = _build(cls.corpus)
        cls.observed = subject.observed_edges(cls.payload)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_no_relation_emits_a_forbidden_edge(self):
        # AC-2's hard gate: zero FALSE POSITIVES on the corrected baseline,
        # including the deliberately seeded `cpu_count` and schema/config
        # collisions. A false positive is an edge that is simply not true, so
        # it is never acceptable; recall gaps are handled separately below.
        report = subject.score_relations(self.observed, self.corpus)
        self.assertEqual(set(subject.SCORED_RELATIONS), set(report))
        for relation, row in report.items():
            with self.subTest(relation=relation):
                self.assertEqual(0, row["false_positives"],
                                 row["forbidden_edges_emitted"])
                self.assertEqual(1.0, row["precision"])
                self.assertGreaterEqual(row["true_positives"], 1)

    def test_every_miss_is_a_declared_gap_and_every_declared_gap_still_misses(self):
        # The recall pin, in both directions. A NEW miss fails because it is
        # undeclared. A REPAIRED gap also fails, so an improvement cannot land
        # while the corpus still describes it as broken.
        report = subject.score_relations(self.observed, self.corpus)
        missed = {tuple(m) for row in report.values() for m in row["missed_edges"]}
        declared = {(g["source"], g["relation"], g["target"])
                    for g in self.corpus["known_gaps"]}
        self.assertEqual(declared, missed,
                         "declared gaps and actual misses have diverged")

    def test_the_seeded_external_api_collision_stays_external(self):
        # The `cpu_count` case AC-2 names, asserted directly rather than only
        # through the aggregate score. `os.cpu_count()` must not bind to the
        # project function that happens to share the bare name.
        self.assertNotIn(
            ("svc/pool.py::pool_size", "calls", "svc/limits.py::cpu_count"),
            self.observed,
            "an external stdlib call was bound to unrelated project code")
        targets = {t for s_, r, t in self.observed if s_ == "svc/pool.py::pool_size"}
        self.assertFalse({t for t in targets if not t.startswith("external::")},
                         f"pool_size must reach only external targets: {targets}")

    def test_the_seeded_config_collision_never_cross_binds(self):
        # Two config files declare `retry_budget_ms`. The audit reader must
        # not reach the other file's key. (That it also loses its OWN correct
        # binding is the declared gap `config_key_collision_drops_binding`.)
        self.assertNotIn(
            ("svc/audit.py::audit_sink", "reads_config",
             "svc/config.json::retry_budget_ms"),
            self.observed)

    def test_the_ambiguous_name_binds_through_the_import(self):
        self.assertIn(("svc/ingest.py::ingest", "calls",
                       "svc/parsers/json_parser.py::parse"), self.observed)
        self.assertNotIn(("svc/ingest.py::ingest", "calls",
                          "svc/parsers/yaml_parser.py::parse"), self.observed)

    def test_an_injected_forbidden_edge_is_caught_as_a_false_positive(self):
        # AC-9 first half.  The sharpest control: a config binder that attaches
        # every key in a matched file rather than the literal actually read.
        injected = ("svc/loader.py::load_settings", "reads_config",
                    "svc/config.json::queue_name")
        base = subject.score_relations(self.observed, self.corpus)["reads_config"]
        row = subject.score_relations(
            self.observed | {injected}, self.corpus)["reads_config"]
        # Stated as a DELTA against the clean baseline so that growing the
        # corpus changes the absolute counts without churning this control.
        self.assertEqual(0, base["false_positives"])
        self.assertEqual(1, row["false_positives"])
        self.assertEqual([list(injected)], row["forbidden_edges_emitted"])
        self.assertLess(row["precision"], base["precision"])
        # Recall is untouched: injecting an edge cannot remove one.
        self.assertEqual(base["recall"], row["recall"])
        self.assertEqual(base["false_negatives"], row["false_negatives"])

    def test_a_deleted_expected_edge_is_caught_as_a_false_negative(self):
        # AC-9 second half.
        deleted = ("svc/worker.py::Worker.start", "calls", "svc/loader.py::load_settings")
        self.assertIn(deleted, self.observed)
        base = subject.score_relations(self.observed, self.corpus)["calls"]
        row = subject.score_relations(
            self.observed - {deleted}, self.corpus)["calls"]
        self.assertEqual(base["false_negatives"] + 1, row["false_negatives"])
        self.assertLess(row["recall"], base["recall"])
        self.assertIn(list(deleted), row["missed_edges"])
        # Precision is untouched: removing a true edge invents no false one.
        self.assertEqual(0, row["false_positives"])

    def test_the_built_graph_stays_inside_the_declared_ceilings(self):
        bounds = subject.corpus_within_bounds(self.payload)
        self.assertTrue(bounds["within_bounds"], bounds)
        self.assertEqual(2000, subject.MAX_NORMALIZED_NODES)
        self.assertEqual(5000, subject.MAX_NORMALIZED_EDGES)
        self.assertEqual(128, subject.MAX_CORPUS_FILES)

    def test_external_targets_are_kept_for_imports_and_dropped_for_calls(self):
        relations = {t[1] for t in self.observed}
        self.assertEqual(set(subject.SCORED_RELATIONS), relations)
        import_targets = [t[2] for t in self.observed if t[1] == "imports"]
        self.assertTrue(any(t.startswith("external::") for t in import_targets))
        call_targets = [t[2] for t in self.observed if t[1] == "calls"]
        self.assertFalse(any(t.startswith("external::") for t in call_targets))

    def test_duplicate_edges_collapse_before_scoring(self):
        payload = {"edges": [
            {"source": "a", "relation": "calls", "target": "b", "confidence": "EXTRACTED"},
            {"source": "a", "relation": "calls", "target": "b", "confidence": "EXTRACTED"},
        ]}
        self.assertEqual({("a", "calls", "b")}, subject.observed_edges(payload))

    def test_a_report_serializes_inside_the_size_ceiling(self):
        report = subject.score_relations(self.observed, self.corpus)
        payload = {"schema": subject.REPORT_SCHEMA,
                   "corpus_digest": subject.digest(self.corpus),
                   "graph_builder_version": graph_indexer.GRAPH_BUILDER_VERSION,
                   "relations": report}
        encoded = json.dumps(payload).encode("utf-8")
        self.assertLess(len(encoded), subject.MAX_REPORT_BYTES)
        # Requirement 9: the schema must name every scored relation and tool.
        self.assertEqual(set(subject.SCORED_RELATIONS), set(payload["relations"]))
        for row in payload["relations"].values():
            self.assertTrue(row["public_tool"])


CONTROL_DIR = (REPO_ROOT / "docs" / "waves"
               / "1wpih index-quality-evaluation-and-ranking" / "evidence")
MACHINE_RESULT_CONTROL = CONTROL_DIR / "machine-result-control.json"
LEGITIMATE_CONTROLS = (
    CONTROL_DIR / "design-tokens-control.json",
    CONTROL_DIR / "service-config-control.json",
    CONTROL_DIR / "user-authored-data-control.json",
)


def _load_project_graph():
    """Read the persisted project graph, sniffing gzip like the real readers."""
    import gzip
    path = REPO_ROOT / ".wavefoundry" / "index" / "graph" / "project-graph.json"
    if not path.exists():
        return None
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    try:
        return json.loads(raw)
    except ValueError:
        return None


def _owning_file(node):
    return node.get("file") or str(node.get("id", "")).split("::", 1)[0]


class LiveGraphEvidenceControlTests(unittest.TestCase):
    """Wave 1wpie AC-10 and AC-11 against the PERSISTED graph.

    Requirement 11 makes the control's location load-bearing. A 2026-09-03
    re-derivation of the census confirms it: `docs/evals/` and `docs/reports/`
    contribute zero graph nodes each, while wave evidence trees contribute
    2,758. A control filed beside the other eval fixtures would never be
    indexed, so every classification assertion below is GUARDED by a presence
    assertion. Relocating the control makes these tests FAIL rather than pass
    silently on an empty node set.
    """

    @classmethod
    def setUpClass(cls):
        cls.graph = _load_project_graph()

    def setUp(self):
        if not self.graph:
            self.skipTest("no persisted project graph in this tree")
        rel_dir = CONTROL_DIR.relative_to(REPO_ROOT).as_posix() + "/"
        self.control_nodes = {}
        for node in self.graph.get("nodes", []):
            owner = _owning_file(node)
            if owner.startswith(rel_dir):
                self.control_nodes.setdefault(owner, []).append(node)

    def _nodes_for(self, path: Path):
        rel = path.relative_to(REPO_ROOT).as_posix()
        nodes = self.control_nodes.get(rel) or []
        # AC-10: presence is asserted BEFORE any classification claim.
        self.assertTrue(
            nodes,
            f"{rel} has no graph node — the control is unindexed or was moved "
            "out of the wave evidence tree, so its classification cannot be "
            "asserted. This is a FAILURE, not a vacuous pass.",
        )
        return nodes

    def test_the_control_directory_is_indexed_at_all(self):
        self.assertTrue(self.control_nodes,
                        "the wave evidence tree contributes no graph nodes")

    def test_the_machine_result_control_is_classified_as_evidence(self):
        # The stamp lands on the FILE node; children inherit it at query time
        # through the owning-file resolution, so assert the flag where it is
        # actually written rather than on every node in the file.
        nodes = self._nodes_for(MACHINE_RESULT_CONTROL)
        modules = [n for n in nodes if n.get("kind") == "module"]
        self.assertEqual(1, len(modules), "expected exactly one file node")
        self.assertTrue(modules[0].get("evidence_data"),
                        f"{modules[0].get('id')} must be Evidence/Data")
        self.assertTrue(modules[0].get("classification_reasons"),
                        "a classified node must record WHY")
        # Requirement 7 puts the reasons in the public response, so a caller
        # who disagrees can see which signal fired. Both routes are expected
        # here: this control declares provenance AND carries a run signature.
        joined = " ".join(modules[0]["classification_reasons"])
        self.assertIn("explicit provenance", joined)
        self.assertIn("machine-run signature", joined)

    def test_children_of_the_evidence_control_resolve_as_evidence(self):
        # Requirement 4/5: the classification is per-artifact, so a symbol
        # inside a machine-result file must resolve as evidence too.
        import graph_query
        nodes = self._nodes_for(MACHINE_RESULT_CONTROL)
        children = [n for n in nodes if n.get("kind") != "module"]
        self.assertTrue(children, "the control contributes no child nodes")
        # Build from the payload already read, NOT from_root: from_root can
        # fire a synchronous full rebuild when the persisted graph predates
        # the current builder version, which would stall the suite.
        resolver = graph_query.GraphQueryIndex(dict(self.graph, present=True))
        for node in children[:5]:
            self.assertTrue(resolver.is_evidence_node(node["id"]),
                            f"{node['id']} must inherit its file's evidence flag")

    def test_the_legitimate_controls_stay_in_their_ordinary_domains(self):
        import graph_query
        resolver = graph_query.GraphQueryIndex(dict(self.graph, present=True))
        for path in LEGITIMATE_CONTROLS:
            for node in self._nodes_for(path):
                with self.subTest(control=path.name, node=node.get("id")):
                    self.assertFalse(
                        node.get("evidence_data"),
                        f"{node.get('id')} is legitimate {path.stem} data and "
                        "must NOT be classified as Evidence/Data",
                    )
                    self.assertFalse(
                        resolver.is_evidence_node(node["id"]),
                        f"{node.get('id')} must not RESOLVE as evidence either",
                    )

    def test_retrieval_eval_remains_ordinary_framework_code(self):
        # Requirement 11: co-clustering with machine artifacts must not relabel
        # the evaluator SOURCE. Its own reports are a different question.
        target = ".wavefoundry/framework/scripts/retrieval_eval.py"
        nodes = [n for n in self.graph.get("nodes", [])
                 if _owning_file(n) == target]
        self.assertTrue(nodes, "retrieval_eval.py is missing from the graph")
        for node in nodes:
            self.assertFalse(node.get("evidence_data"),
                             f"{node.get('id')} is framework code, not evidence")

    def test_the_canonically_ignored_standing_artifacts_are_absent(self):
        # Requirement 11: absent from the graph entirely, so there is nothing
        # to relabel. Absence here is the POINT, so no presence guard applies.
        offenders = sorted({
            _owning_file(n) for n in self.graph.get("nodes", [])
            if _owning_file(n).startswith("docs/evals/")
            or _owning_file(n).startswith("docs/reports/")
        })
        self.assertEqual([], offenders,
                         "ignored standing artifacts leaked into the graph")


class MoveRenameInvarianceTests(unittest.TestCase):
    """Wave 1wpie AC-11 / requirement 12: classification is content-only, so an
    identical payload keeps its verdict under any move or rename."""

    def setUp(self):
        self.payload = json.loads(MACHINE_RESULT_CONTROL.read_text())

    def test_the_machine_result_verdict_survives_relocation(self):
        verdict, reasons = graph_indexer.classify_evidence_payload(self.payload)
        self.assertTrue(verdict)
        # The classifier takes the PAYLOAD, never a path, so relocation cannot
        # reach it. Pin that by re-classifying the identical parsed content.
        for _ in range(3):
            again, again_reasons = graph_indexer.classify_evidence_payload(
                json.loads(json.dumps(self.payload)))
            self.assertTrue(again)
            self.assertEqual(reasons, again_reasons)

    def test_the_classifier_signature_takes_no_path_argument(self):
        # Structural proof of invariance: a function with no path parameter
        # cannot vary by location.
        import inspect
        params = list(inspect.signature(
            graph_indexer.classify_evidence_payload).parameters)
        self.assertEqual(["payload"], params,
                         "a path-aware classifier could not be move-invariant")

    def test_renaming_the_control_does_not_change_the_verdict(self):
        for name in ("totally-different-name.json", "config.json", "tokens.json"):
            with self.subTest(renamed_to=name):
                verdict, _ = graph_indexer.classify_evidence_payload(self.payload)
                self.assertTrue(verdict, f"verdict must not depend on {name}")

    def test_the_legitimate_controls_are_also_move_invariant(self):
        for path in LEGITIMATE_CONTROLS:
            with self.subTest(control=path.name):
                payload = json.loads(path.read_text())
                verdict, _ = graph_indexer.classify_evidence_payload(payload)
                self.assertFalse(verdict)
                # Renaming a legitimate control to an evidence-sounding name
                # must not flip it either.
                verdict_again, _ = graph_indexer.classify_evidence_payload(
                    json.loads(json.dumps(payload)))
                self.assertFalse(verdict_again)


class ClassificationControlScorerTests(unittest.TestCase):
    """Wave 1wpie AC-11 / requirement 12: the scorer must FAIL an injected
    false positive on a legitimate control and an injected false negative on
    the machine-result control. A scorer that only ever reports success would
    make the controls decorative."""

    CORRECT = {
        "machine-result-control.json": True,
        "design-tokens-control.json": False,
        "service-config-control.json": False,
        "user-authored-data-control.json": False,
    }

    def test_the_correct_verdicts_pass(self):
        result = subject.score_classification_controls(self.CORRECT)
        self.assertTrue(result["passed"])
        self.assertEqual([], result["false_positives"])
        self.assertEqual([], result["false_negatives"])
        self.assertEqual([], result["not_observed"])

    def test_an_injected_false_positive_fails_the_scorer(self):
        for control in ("design-tokens-control.json",
                        "service-config-control.json",
                        "user-authored-data-control.json"):
            with self.subTest(injected_into=control):
                observed = dict(self.CORRECT, **{control: True})
                result = subject.score_classification_controls(observed)
                self.assertFalse(result["passed"],
                                 "a legitimate control classified as evidence "
                                 "must fail the run")
                self.assertIn(control, result["false_positives"])
                self.assertEqual([], result["false_negatives"])

    def test_an_injected_false_negative_fails_the_scorer(self):
        observed = dict(self.CORRECT, **{"machine-result-control.json": False})
        result = subject.score_classification_controls(observed)
        self.assertFalse(result["passed"],
                         "a missed machine-result artifact must fail the run")
        self.assertEqual(["machine-result-control.json"],
                         result["false_negatives"])
        self.assertEqual([], result["false_positives"])

    def test_the_two_failure_directions_are_reported_separately(self):
        observed = dict(self.CORRECT, **{
            "machine-result-control.json": False,
            "design-tokens-control.json": True,
        })
        result = subject.score_classification_controls(observed)
        self.assertFalse(result["passed"])
        self.assertEqual(["design-tokens-control.json"],
                         result["false_positives"])
        self.assertEqual(["machine-result-control.json"],
                         result["false_negatives"])

    def test_an_unobserved_control_fails_rather_than_passing_silently(self):
        # Requirement 11's anti-vacuity rule at the scorer level: an
        # unindexed or relocated control must not read as "no mismatch".
        observed = dict(self.CORRECT)
        del observed["machine-result-control.json"]
        result = subject.score_classification_controls(observed)
        self.assertFalse(result["passed"])
        self.assertEqual(["machine-result-control.json"],
                         result["not_observed"])

    def test_every_row_names_its_status_and_domain(self):
        rows = subject.score_classification_controls(self.CORRECT)["controls"]
        self.assertEqual(len(subject.CLASSIFICATION_CONTROLS), len(rows))
        for row in rows:
            self.assertEqual("match", row["status"])
            self.assertTrue(row["domain"])

    def test_the_control_directory_matches_the_files_on_disk(self):
        # Binds the frozen table to reality: a renamed or deleted control is
        # caught here rather than silently dropping out of the run.
        on_disk = {p.name for p in CONTROL_DIR.glob("*.json")}
        self.assertEqual(set(subject.CLASSIFICATION_CONTROLS), on_disk)
        self.assertEqual(
            subject.CONTROL_DIRECTORY,
            CONTROL_DIR.relative_to(REPO_ROOT).as_posix(),
        )

    def test_the_live_graph_satisfies_the_frozen_expectation(self):
        # The end-to-end assertion: read the real verdicts out of the
        # persisted graph and score them. Presence is enforced by the scorer's
        # `not_observed` rule, so an unindexed control fails here.
        graph = _load_project_graph()
        if not graph:
            self.skipTest("no persisted project graph in this tree")
        prefix = subject.CONTROL_DIRECTORY + "/"
        observed: dict[str, bool] = {}
        for node in graph.get("nodes", []):
            if node.get("kind") != "module":
                continue
            owner = _owning_file(node)
            if owner.startswith(prefix):
                observed[owner[len(prefix):]] = bool(node.get("evidence_data"))
        result = subject.score_classification_controls(observed)
        self.assertTrue(
            result["passed"],
            f"live graph disagrees with the frozen expectation: {result}",
        )


class ImportHeadAuthorityTests(unittest.TestCase):
    """Wave 1wpie AC-2: the qualified-target fallback must not discard the
    receiver head when the source file explicitly imported it from outside
    the project. Narrow by construction -- every uncertain case keeps the
    prior behaviour, because the guard only ever SUPPRESSES a heuristic."""

    HEADS = frozenset({"svc", "loader", "pool", "limits"})

    _DEFAULT = object()

    def _external(self, src, bare, imports, heads=_DEFAULT):
        return graph_indexer._import_head_is_external(
            src, bare, imports_by_file=imports,
            project_module_heads=self.HEADS if heads is self._DEFAULT else heads)

    def test_an_imported_stdlib_head_is_external(self):
        self.assertTrue(self._external(
            "svc/pool.py::pool_size", "os.cpu_count", {"svc/pool.py": {"os": "os"}}))

    def test_an_imported_third_party_head_is_external(self):
        self.assertTrue(self._external(
            "svc/pool.py::f", "np.array", {"svc/pool.py": {"np": "numpy"}}))

    def test_an_imported_project_head_is_not_external(self):
        # `from svc import loader` then `loader.load_settings()` must keep
        # binding, so the guard must not fire here.
        self.assertFalse(self._external(
            "svc/x.py::f", "loader.load_settings",
            {"svc/x.py": {"loader": "svc.loader"}}))

    def test_an_unimported_head_keeps_the_old_behaviour(self):
        self.assertFalse(self._external("svc/x.py::f", "thing.method",
                                        {"svc/x.py": {}}))

    def test_a_bare_name_is_never_affected(self):
        # No dot means no receiver head to be authoritative about.
        self.assertFalse(self._external("svc/x.py::f", "cpu_count",
                                        {"svc/x.py": {"os": "os"}}))

    def test_absent_head_information_disables_the_guard_entirely(self):
        self.assertFalse(self._external(
            "svc/pool.py::f", "os.cpu_count",
            {"svc/pool.py": {"os": "os"}}, heads=None))

    def test_project_heads_cover_directories_and_module_basenames(self):
        heads = graph_indexer._project_module_heads(
            {"svc/loader.py": 1, "svc/loader.py::load_settings": 1,
             "pkg/sub/deep.py": 1, "root.py": 1})
        for expected in ("svc", "loader", "pkg", "deep", "root"):
            self.assertIn(expected, heads)

    def test_external_prefixed_ids_do_not_contribute_heads(self):
        heads = graph_indexer._project_module_heads(
            {"external::os": 1, "external::numpy.array": 1})
        self.assertNotIn("os", heads)
        self.assertNotIn("numpy", heads)


class CorpusDeterminismTests(unittest.TestCase):
    """Wave 1wpie AC-5 / requirement 10: two fresh builds of the same fixed
    corpus produce identical normalized scored rows and identical community
    ids, and the corpus stays inside its declared ceilings."""

    @classmethod
    def setUpClass(cls):
        if not CORPUS.is_file():
            raise unittest.SkipTest("graph corpus is not present in this tree")
        cls.corpus = subject.load_corpus(CORPUS)

    def _fresh_build(self):
        tmp, payload = _build(self.corpus)
        try:
            return (subject.observed_edges(payload),
                    subject.score_relations(subject.observed_edges(payload),
                                            self.corpus),
                    subject.corpus_within_bounds(payload))
        finally:
            tmp.cleanup()

    def test_two_fresh_builds_agree_on_every_scored_row(self):
        edges_a, report_a, _ = self._fresh_build()
        edges_b, report_b, _ = self._fresh_build()
        self.assertEqual(edges_a, edges_b,
                         "the scored edge set is not reproducible")
        self.assertEqual(json.dumps(report_a, sort_keys=True),
                         json.dumps(report_b, sort_keys=True),
                         "the scored report is not reproducible")

    def test_the_corpus_digest_is_stable_across_reloads(self):
        again = subject.load_corpus(CORPUS)
        self.assertEqual(subject.digest(self.corpus), subject.digest(again))

    def test_the_corpus_stays_inside_every_declared_ceiling(self):
        _, _, bounds = self._fresh_build()
        self.assertTrue(bounds["within_bounds"], bounds)
        self.assertLessEqual(len(self.corpus["files"]),
                             subject.MAX_CORPUS_FILES)
        self.assertLessEqual(bounds["nodes"], subject.MAX_NORMALIZED_NODES)
        self.assertLessEqual(bounds["edges"], subject.MAX_NORMALIZED_EDGES)

    def test_the_declared_ceilings_are_the_requirement_ten_values(self):
        self.assertEqual(128, subject.MAX_CORPUS_FILES)
        self.assertEqual(2_000, subject.MAX_NORMALIZED_NODES)
        self.assertEqual(5_000, subject.MAX_NORMALIZED_EDGES)
        self.assertEqual(1024 * 1024, subject.MAX_REPORT_BYTES)

    def test_community_ids_are_reproducible_on_a_fixed_graph(self):
        # Cluster ids are a pure function of the graph payload, so the same
        # payload must yield the same ids on an independent run.
        import graph_cluster
        import tempfile as _tf
        from contextlib import redirect_stderr
        import io as _io
        tmp, payload = _build(self.corpus)
        try:
            runs = []
            for _ in range(2):
                with _tf.TemporaryDirectory() as scratch:
                    root = Path(scratch)
                    (root / ".wavefoundry" / "index").mkdir(parents=True)
                    with redirect_stderr(_io.StringIO()):
                        result = graph_cluster.update_graph_clusters(
                            root=root, index_dir=root / ".wavefoundry" / "index",
                            layer="project", graph_payload=payload, verbose=False)
                    communities = result.get("communities") or []
                    runs.append([(c.get("community_id"), c.get("label"),
                                  tuple(c.get("node_ids") or ()))
                                 for c in communities])
            # Guard against a vacuous pass: two empty lists are equal. The
            # payload must actually produce communities for this to mean
            # anything (the key is `communities`, not `clusters`).
            self.assertTrue(runs[0], "the corpus produced no communities")
            self.assertTrue(all(cid for cid, _l, _n in runs[0]),
                            "communities were produced without ids")
            self.assertEqual(runs[0], runs[1],
                             "community ids are not reproducible")
        finally:
            tmp.cleanup()


class ImportHeadDeliveryRepairTests(unittest.TestCase):
    """Wave 1wpie delivery review: regressions for CODE-DEL-1/3/4/6.

    Each of these covers a defect that shipped green because this repository's
    own layout could not express it. They are written against the shapes a
    CONSUMING repository has, not the shape this one has."""

    def test_an_intermediate_package_directory_is_a_project_head(self):
        # CODE-DEL-1. A src-layout project imports the intermediate directory
        # (`import mypkg`), not the first path segment. Omitting it made the
        # guard read `mypkg` as external and suppress a fallback that had been
        # binding a real project edge.
        heads = graph_indexer._project_module_heads({
            "src/mypkg/module.py::func": 1,
            "src/mypkg/caller.py::main": 1,
        })
        for expected in ("src", "mypkg", "module", "caller"):
            self.assertIn(expected, heads)

    def test_every_intermediate_segment_counts_not_just_the_first(self):
        heads = graph_indexer._project_module_heads({"a/b/c/d.py::f": 1})
        for expected in ("a", "b", "c", "d"):
            self.assertIn(expected, heads)

    def test_a_true_project_edge_survives_the_guard_in_a_src_layout(self):
        # The end-to-end shape of CODE-DEL-1: with the head present the guard
        # must NOT fire, so the caller's last-segment fallback still runs.
        heads = graph_indexer._project_module_heads({
            "src/mypkg/module.py::func": 1, "src/mypkg/caller.py::main": 1})
        self.assertFalse(
            graph_indexer._import_head_is_external(
                "src/mypkg/caller.py::main", "mypkg.module.func",
                imports_by_file={"src/mypkg/caller.py": {"mypkg": "mypkg"}},
                project_module_heads=heads),
            "an imported INTERMEDIATE package is a project module; suppressing "
            "its fallback drops a real edge")

    def test_a_documentation_file_never_contributes_an_import_head(self):
        # CODE-DEL-3. Doc nodes reach the merged node map but not the code
        # delta, so letting them define heads made an incremental doc-add
        # change guard behaviour with nothing to invalidate the affected edge.
        # A markdown file is not an importable module either way.
        heads = graph_indexer._project_module_heads({
            "docs/loader.md": 1,
            "docs/waves/w/evidence/freeze.json": 1,
            "app/main.py::run": 1,
        })
        self.assertNotIn("loader", heads)
        self.assertNotIn("freeze", heads)
        self.assertIn("app", heads)

    def test_adding_a_doc_cannot_flip_the_guard(self):
        # The divergence stated as behaviour: head membership must be
        # identical before and after a doc-only add.
        before = graph_indexer._project_module_heads({"app/main.py::run": 1})
        after = graph_indexer._project_module_heads({
            "app/main.py::run": 1, "docs/loader.md": 1})
        self.assertEqual(before, after)

    def test_a_timestamp_key_with_no_real_value_is_not_a_machine_run(self):
        # CODE-DEL-4. The provenance route always required a non-empty string;
        # the run-signature route checked only that a KEY existed, so a
        # hand-authored `{"updated_at": null, ...}` classified as evidence.
        for payload in (
            {"foo_at": None, "digest": "d"},
            {"captured_at": "", "digest": "d"},
            {"captured_at": "   ", "file_digests": {}},
            {"recorded_at": 12345, "command": "pytest"},
        ):
            with self.subTest(payload=sorted(payload)):
                self.assertFalse(
                    graph_indexer.classify_evidence_payload(payload)[0],
                    "a timestamp KEY without a real value is not a capture time")

    def test_a_real_timestamp_still_qualifies(self):
        # The positive control that keeps the test above from passing by
        # disabling the route entirely.
        self.assertTrue(graph_indexer.classify_evidence_payload(
            {"captured_at": "2026-01-01T00:00:00Z", "digest": "abc"})[0])

    def test_external_ids_contribute_no_head_including_the_bare_token(self):
        # CODE-DEL-6. The old guard tested for an "external::" prefix, which a
        # split-on-"::" file part can never carry, so the branch was dead and
        # the token `external` itself leaked in as a head.
        heads = graph_indexer._project_module_heads(
            {"external::os": 1, "external::numpy.array": 1})
        self.assertNotIn("os", heads)
        self.assertNotIn("numpy", heads)
        self.assertNotIn("external", heads)
        self.assertEqual(frozenset(), heads)


class ImportableExtensionCouplingTests(unittest.TestCase):
    """Delivery reverification (finding C): nothing pinned
    `_IMPORTABLE_MODULE_EXTENSIONS` against `_CODE_EXTENSIONS`, so adding an
    importable language to the indexer would silently stop contributing heads
    and silently drop edges. That is the SAME failure mode as the defect this
    repair exists to fix, one level up, so it gets a pin."""

    def test_every_importable_extension_is_actually_indexed(self):
        # A head drawn from an extension the walker never indexes is dead
        # weight; the two sets must not drift apart in that direction.
        extra = graph_indexer._IMPORTABLE_MODULE_EXTENSIONS - graph_indexer._CODE_EXTENSIONS
        self.assertEqual(set(), extra,
                         f"importable extensions absent from _CODE_EXTENSIONS: {sorted(extra)}")

    def test_newly_indexed_languages_are_triaged_not_silently_dropped(self):
        # The load-bearing direction. This list is the RECORDED triage of every
        # indexed extension deliberately excluded from head contribution. When
        # a language is added to _CODE_EXTENSIONS this test fails, which forces
        # a decision instead of a silent edge loss.
        triaged_non_importable = {
            ".bash", ".css", ".ddl", ".dml", ".fish", ".hcl", ".hql", ".htm",
            ".html", ".json", ".jsonc", ".jsp", ".pgsql", ".properties",
            ".ps1", ".psm1", ".psql", ".scss", ".sh", ".sql", ".svg", ".tf",
            ".tfvars", ".toml", ".tpl", ".tsql", ".xml", ".xsd", ".xsl",
            ".xslt", ".yaml", ".yml", ".zsh",
        }
        untriaged = (graph_indexer._CODE_EXTENSIONS
                     - graph_indexer._IMPORTABLE_MODULE_EXTENSIONS
                     - triaged_non_importable)
        self.assertEqual(
            set(), untriaged,
            "these indexed extensions are neither importable nor triaged as "
            f"non-importable: {sorted(untriaged)}. Decide explicitly: add to "
            "_IMPORTABLE_MODULE_EXTENSIONS if the language imports modules by "
            "name, otherwise add to this triage list.")


class ReportContractTests(unittest.TestCase):
    """Wave 1wpie AC-9 and Requirement 9: the report is an IDENTITY-BOUND
    artifact, not a bag of numbers.

    Requirement 9 enumerates what a report must bind. Each field is asserted
    by name so that dropping one fails here rather than silently producing a
    report whose deltas cannot be attributed to anything.
    """

    REQUIRED_TOP_LEVEL = (
        "schema", "label", "run_started_at", "run_completed_at", "corpus",
        "evaluator_identity", "production_identity", "builder_versions",
        "graph_input_fingerprint", "repository_identity", "environment",
        "scored_relations", "public_tools", "relations",
        "classification_controls", "graph_bounds", "totals", "report_digest",
    )

    @classmethod
    def setUpClass(cls):
        if not CORPUS.is_file():
            raise unittest.SkipTest("graph corpus is not present in this tree")
        cls.report = subject.build_report(CORPUS, label="post", root=REPO_ROOT)

    def test_every_requirement_nine_field_is_bound(self):
        for field in self.REQUIRED_TOP_LEVEL:
            with self.subTest(field=field):
                self.assertIn(field, self.report)
                self.assertIsNotNone(self.report[field])

    def test_evaluator_and_production_identity_are_separate(self):
        # A baseline/post pair is the SAME instrument reading two different
        # productions. One combined digest would hide the measured difference.
        evaluator = self.report["evaluator_identity"]
        production = self.report["production_identity"]
        self.assertEqual(subject.REPORT_SCHEMA, evaluator["report_schema"])
        self.assertEqual(subject.FIXTURE_SCHEMA, evaluator["fixture_schema"])
        self.assertEqual(64, len(evaluator["source_sha256"]))
        for key in ("graph_indexer_sha256", "graph_query_sha256",
                    "graph_cluster_sha256"):
            self.assertEqual(64, len(production[key]), key)
        self.assertNotEqual(evaluator["source_sha256"],
                            production["graph_indexer_sha256"])
        # The production's own load path, so a baseline taken from a
        # predecessor checkout cannot be misread as the working repository.
        self.assertTrue(production["source_root"])

    def test_builder_versions_track_the_live_modules(self):
        import graph_cluster
        versions = self.report["builder_versions"]
        self.assertEqual(graph_indexer.GRAPH_BUILDER_VERSION,
                         versions["graph_builder_version"])
        self.assertEqual(graph_cluster.CLUSTER_BUILDER_VERSION,
                         versions["cluster_builder_version"])

    def test_the_schema_names_every_scored_relation_and_public_tool(self):
        self.assertEqual(set(subject.SCORED_RELATIONS),
                         set(self.report["scored_relations"]))
        self.assertEqual(set(subject.SCORED_RELATIONS),
                         set(self.report["relations"]))
        tools = {row["public_tool"] for row in self.report["relations"].values()}
        self.assertEqual(tools, set(self.report["public_tools"]))
        self.assertTrue(all(self.report["public_tools"]))

    def test_the_input_fingerprint_follows_content_not_names(self):
        # Two builds of the same corpus agree; a corpus whose file CONTENT
        # changed must not reuse the fingerprint.
        corpus = subject.load_corpus(CORPUS)
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            root_a, root_b = Path(a), Path(b)
            files_a = subject.materialize(root_a, corpus)
            files_b = subject.materialize(root_b, corpus)
            first = subject.graph_input_fingerprint(
                root_a, files_a, walker_version="1", chunker_version="1")
            second = subject.graph_input_fingerprint(
                root_b, files_b, walker_version="1", chunker_version="1")
            self.assertEqual(first, second)
            files_b[0].write_text(
                files_b[0].read_text(encoding="utf-8") + "\n# edited\n",
                encoding="utf-8")
            mutated = subject.graph_input_fingerprint(
                root_b, files_b, walker_version="1", chunker_version="1")
            self.assertNotEqual(first, mutated)
            # The builder versions are part of the input too.
            self.assertNotEqual(first, subject.graph_input_fingerprint(
                root_a, files_a, walker_version="2", chunker_version="1"))

    def test_the_report_digest_covers_the_report_content(self):
        mutated = dict(self.report)
        mutated.pop("report_digest")
        self.assertEqual(self.report["report_digest"], subject.digest(mutated))
        changed = dict(mutated)
        changed["totals"] = dict(mutated["totals"])
        changed["totals"]["false_positives"] += 1
        self.assertNotEqual(self.report["report_digest"], subject.digest(changed))

    def test_the_writer_refuses_a_report_over_the_ceiling(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "oversized.json"
            oversized = {"schema": subject.REPORT_SCHEMA,
                         "padding": "x" * (subject.MAX_REPORT_BYTES + 1)}
            with self.assertRaises(subject.GraphQualityInvalid) as caught:
                subject.write_report(oversized, path)
            self.assertEqual("report_too_large", caught.exception.code)
            self.assertFalse(path.exists(), "a refused report must write nothing")

    def test_an_unknown_label_is_refused(self):
        with self.assertRaises(subject.GraphQualityInvalid):
            subject.build_report(CORPUS, label="interim", root=REPO_ROOT)


class ShippedReportPairTests(unittest.TestCase):
    """Requirement 9 names the two report paths; they must exist, agree with a
    fresh run, and support the comparison they were produced for."""

    BASELINE = REPO_ROOT / "docs" / "reports" / "graph-quality-baseline.json"
    POST = REPO_ROOT / "docs" / "reports" / "graph-quality-post.json"

    @classmethod
    def setUpClass(cls):
        if not (cls.BASELINE.is_file() and cls.POST.is_file()):
            raise unittest.SkipTest("the shipped report pair is not in this tree")
        cls.baseline = json.loads(cls.BASELINE.read_text(encoding="utf-8"))
        cls.post = json.loads(cls.POST.read_text(encoding="utf-8"))

    def test_both_reports_carry_their_own_digest(self):
        for label, report in (("baseline", self.baseline), ("post", self.post)):
            with self.subTest(report=label):
                self.assertEqual(label, report["label"])
                body = {k: v for k, v in report.items() if k != "report_digest"}
                self.assertEqual(report["report_digest"], subject.digest(body))

    def test_the_pair_is_inside_the_declared_size_ceiling(self):
        total = self.BASELINE.stat().st_size + self.POST.stat().st_size
        self.assertLessEqual(total, subject.MAX_REPORT_PAIR_BYTES)
        for path in (self.BASELINE, self.POST):
            self.assertLessEqual(path.stat().st_size, subject.MAX_REPORT_BYTES)

    def test_the_shipped_post_report_still_matches_a_fresh_run(self):
        # Guards against a stale report surviving an extraction change: the
        # numbers, not the timestamps, must still reproduce.
        if not CORPUS.is_file():
            self.skipTest("graph corpus is not present in this tree")
        fresh = subject.build_report(CORPUS, label="post", root=REPO_ROOT)
        self.assertEqual(self.post["relations"], fresh["relations"])
        self.assertEqual(self.post["totals"], fresh["totals"])
        self.assertEqual(self.post["corpus"]["digest"], fresh["corpus"]["digest"])
        self.assertEqual(self.post["builder_versions"], fresh["builder_versions"])

    def test_both_shipped_reports_describe_the_shipped_evaluator(self):
        # Requirement 9's reports must describe the instrument that ships, not
        # an earlier one. Editing the evaluator without regenerating them is
        # exactly the drift this catches; the remedy is one command per side.
        current = subject.evaluator_identity()
        for label, report in (("baseline", self.baseline), ("post", self.post)):
            with self.subTest(report=label):
                self.assertEqual(current, report["evaluator_identity"])

    def test_the_pair_supports_an_attributable_comparison(self):
        verdict = subject.verify_report_pair(self.baseline, self.post)
        self.assertTrue(verdict["same_corpus"])
        self.assertTrue(verdict["same_evaluator"])
        self.assertTrue(verdict["production_changed"])
        self.assertTrue(verdict["delta_attributable_to_production"])
        # What the wave actually bought: the seeded external-API collision is
        # a false positive at baseline and gone afterwards, with no recall lost.
        self.assertEqual(1, self.baseline["totals"]["false_positives"])
        self.assertEqual(0, self.post["totals"]["false_positives"])
        self.assertLessEqual(self.post["totals"]["false_negatives"],
                             self.baseline["totals"]["false_negatives"])
        self.assertGreaterEqual(self.post["totals"]["true_positives"],
                                self.baseline["totals"]["true_positives"])

    def test_a_pair_whose_corpus_moved_is_not_attributable(self):
        # The comparison guard itself, in its failing direction.
        moved = json.loads(json.dumps(self.baseline))
        moved["corpus"]["digest"] = "0" * 64
        self.assertFalse(subject.verify_report_pair(moved, self.post)[
            "delta_attributable_to_production"])
        reinstrumented = json.loads(json.dumps(self.baseline))
        reinstrumented["evaluator_identity"]["source_sha256"] = "0" * 64
        self.assertFalse(subject.verify_report_pair(reinstrumented, self.post)[
            "delta_attributable_to_production"])

    def test_the_baseline_records_that_it_had_no_classifier(self):
        # The baseline production predates classify_evidence_payload. Silence
        # must read as failure, never as a clean sheet.
        controls = self.baseline["classification_controls"]
        self.assertFalse(controls["passed"])
        self.assertEqual(sorted(subject.CLASSIFICATION_CONTROLS),
                         sorted(controls["not_observed"]))
        self.assertTrue(self.post["classification_controls"]["passed"])


class ReportCliTests(unittest.TestCase):
    """The command line is the surface Requirement 9 names, so it is tested
    as a command line rather than only through the functions beneath it."""

    def test_report_and_label_are_used_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            for argv in ([f"--corpus={CORPUS}", f"--report={path}"],
                         [f"--corpus={CORPUS}", "--label=post"]):
                with self.subTest(argv=argv):
                    with self.assertRaises(SystemExit) as caught:
                        subject.main(argv)
                    self.assertEqual(2, caught.exception.code)
                    self.assertFalse(path.exists())

    def test_the_corpus_summary_mode_still_works_without_a_report(self):
        if not CORPUS.is_file():
            self.skipTest("graph corpus is not present in this tree")
        self.assertEqual(0, subject.main([f"--corpus={CORPUS}"]))

    def test_the_cli_writes_a_report_that_reloads(self):
        if not CORPUS.is_file():
            self.skipTest("graph corpus is not present in this tree")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "post.json"
            self.assertEqual(0, subject.main(
                [f"--corpus={CORPUS}", f"--report={path}", "--label=post",
                 f"--root={REPO_ROOT}"]))
            written = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("post", written["label"])
            self.assertEqual(set(subject.SCORED_RELATIONS),
                             set(written["relations"]))


class ProductionWithoutAClassifierTests(unittest.TestCase):
    """Requirement 11's vacuity rule, applied to the report path."""

    def test_a_production_lacking_the_classifier_observes_nothing(self):
        import types
        stand_in = types.ModuleType("graph_indexer")   # no classify_evidence_payload
        original = sys.modules.get("graph_indexer")
        sys.modules["graph_indexer"] = stand_in
        try:
            self.assertEqual({}, subject.observed_control_verdicts(REPO_ROOT))
        finally:
            if original is None:
                sys.modules.pop("graph_indexer", None)
            else:
                sys.modules["graph_indexer"] = original
        # And silence scores as a failure, not as a clean sheet.
        scored = subject.score_classification_controls({})
        self.assertFalse(scored["passed"])
        self.assertEqual(sorted(subject.CLASSIFICATION_CONTROLS),
                         sorted(scored["not_observed"]))


class ReportSelfContaminationTests(unittest.TestCase):
    """Requirement 11 applied to the evaluator's OWN output.

    `.json` is an indexed source extension, so a report written where no ignore
    rule covers it becomes a search answer about itself. The ignore line alone
    is not the fix -- it is one file away from being forgotten again, which is
    exactly how the two shipped reports first entered the graph.
    """

    def test_the_shipped_report_paths_are_ignored(self):
        import indexer
        patterns = indexer._load_ignore_patterns(REPO_ROOT)
        for rel in ("docs/reports/graph-quality-baseline.json",
                    "docs/reports/graph-quality-post.json"):
            with self.subTest(path=rel):
                self.assertTrue(indexer._matches_ignore(rel, patterns),
                                f"{rel} would enter the retrieval corpus")

    def _repo_probe(self, name: str) -> Path:
        """A repository destination that is cleaned up even when the guard fails.

        Without this, a run against a broken guard leaves a stray `.json` in
        `docs/reports/` -- which is the very contamination under test.
        """
        target = REPO_ROOT / "docs" / "reports" / name
        self.assertFalse(target.exists(), "the probe path must not already exist")
        self.addCleanup(target.unlink, missing_ok=True)
        return target

    def test_writing_to_an_unignored_repository_path_is_refused(self):
        target = self._repo_probe("gq-unlisted-probe.json")
        with self.assertRaises(subject.GraphQualityInvalid) as caught:
            subject.write_report({"schema": subject.REPORT_SCHEMA},
                                 target, root=REPO_ROOT)
        self.assertEqual("self_contaminating_artifact", caught.exception.code)
        self.assertFalse(target.exists(), "a refused report must write nothing")

    def test_a_destination_outside_the_repository_is_allowed(self):
        # Scratch destinations cannot be indexed, so they are not contamination.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "graph-quality-scratch.json"
            subject.assert_report_is_excluded_from_the_corpus(path, REPO_ROOT)
            written = subject.write_report(
                {"schema": subject.REPORT_SCHEMA}, path, root=REPO_ROOT)
            self.assertGreater(written, 0)
            self.assertTrue(path.is_file())

    def test_the_cli_refuses_a_contaminating_destination(self):
        if not CORPUS.is_file():
            self.skipTest("graph corpus is not present in this tree")
        target = self._repo_probe("gq-cli-probe.json")
        self.assertEqual(2, subject.main(
            [f"--corpus={CORPUS}", f"--report={target}", "--label=post",
             f"--root={REPO_ROOT}"]))
        self.assertFalse(target.exists(), "a refused run must write nothing")


# --------------------------------------------------------------------------- #
# Wave 1xny6 AC-6: the committed graph parity baseline gets a GUARD.
# --------------------------------------------------------------------------- #
PARITY_FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures" / "graph_parity_baseline_golden_corpus.json"
)


def _canon(value):
    """The fixture's own recorded canonical form."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value) -> str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()


def _strip(payload, removed):
    return {k: v for k, v in payload.items() if k not in removed}


def _owner(node_id) -> str:
    """The source file a node id or edge endpoint belongs to."""
    return str(node_id).split("::", 1)[0]


def _parity_sections(root, files, payload, communities, normalization):
    """Re-derive the fixture's three compared sections from a fresh build.

    Every rule here is the one the fixture RECORDS: volatile build bookkeeping
    stripped by name, nodes sorted by ``(id, canonical json)``, edges collapsed
    into a multiset keyed on the canonical json of the WHOLE edge record with an
    explicit multiplicity so a lost duplicate is visible, and community order
    left as the producer emitted it.
    """
    nodes = sorted(payload.get("nodes") or [],
                   key=lambda n: (str(n.get("id") or ""), _canon(n)))
    edges = list(payload.get("edges") or [])
    multiset = [{"edge": json.loads(key), "multiplicity": count}
                for key, count in sorted(Counter(_canon(e) for e in edges).items())]
    declared = sorted(str(p.relative_to(root)).replace("\\", "/") for p in files)
    with_nodes = sorted({str(n["source_file"]) for n in nodes if n.get("source_file")})
    coverage = {
        "declared_corpus_files": declared,
        "files_with_extracted_nodes": with_nodes,
        "files_without_extracted_nodes": sorted(set(declared) - set(with_nodes)),
        "file_coverage_ratio": (round(len(with_nodes) / len(declared), 4)
                                if declared else 0.0),
        "nodes_per_source_file": dict(sorted(Counter(
            str(n["source_file"]) for n in nodes if n.get("source_file")).items())),
        "edges_per_source_owner": dict(sorted(Counter(
            _owner(e.get("source")) for e in edges).items())),
        "edges_per_relation": dict(sorted(Counter(
            str(e.get("relation") or "") for e in edges).items())),
        "edges_per_confidence": dict(sorted(Counter(
            str(e.get("confidence") or "") for e in edges).items())),
        "external_endpoints": sorted({str(e.get("target")) for e in edges
                                      if str(e.get("target")).startswith("external::")}),
        "graph_bounds": subject.corpus_within_bounds(payload),
        "scored_relation_triples": sorted(
            list(triple) for triple in subject.observed_edges(payload)),
    }
    graph = {
        **_strip({k: v for k, v in payload.items() if k not in ("nodes", "edges")},
                 set(normalization["graph_fields_removed"])),
        "node_count": len(nodes),
        "edge_count_with_multiplicity": sum(m["multiplicity"] for m in multiset),
        "distinct_edge_count": len(multiset),
        "nodes": nodes,
        "edge_evidence_multiset": multiset,
    }
    clusters = _strip(communities, set(normalization["community_fields_removed"]))
    if isinstance(clusters.get("betweenness"), dict):
        clusters["betweenness"] = _strip(
            clusters["betweenness"], set(normalization["betweenness_fields_removed"]))
    return {"graph": graph, "extraction_coverage": coverage, "communities": clusters}


class GraphParityBaselineFixtureTests(unittest.TestCase):
    """Wave 1xny6 AC-6: ASSERT the committed pre-change parity baseline.

    ``tests/fixtures/graph_parity_baseline_golden_corpus.json`` was captured
    from the pre-change builder through exactly the public entries its own
    ``producer`` block names -- ``graph_quality_eval.build_graph_over_corpus``
    for the graph and ``graph_cluster.update_graph_clusters`` for the
    communities. Until this class existed the fixture was evidence with NO
    guard: it re-derived green by hand and nothing in the suite would have
    caught a later regression that moved a node identity, dropped a duplicate
    edge, changed extraction coverage or reshaped community output.

    No skip path, deliberately. The fixture records its corpus by ``sha256``
    and NOT by content, so there is no recorded copy to rebuild from; embedding
    one would mean re-capturing a baseline whose file digest is already
    recorded in the wave's ``runtime-qualification.json``, which is receipt
    editing. Instead an absent or drifted corpus FAILS here and names which of
    the two moved. That costs nothing in practice: this module is a framework
    internal that is never packaged, so it only ever runs in a tree that also
    carries ``docs/evals/graph-quality-golden.json``.
    """

    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(PARITY_FIXTURE.read_text(encoding="utf-8"))
        if not CORPUS.is_file():
            return  # reported as a failure by the corpus-identity test below
        cls.corpus = subject.load_corpus(CORPUS)
        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name)
        cls.files, cls.payload = subject.build_graph_over_corpus(cls.corpus, root)
        index_dir = root / ".wavefoundry" / "index"
        # Observed BEFORE the cluster pass: the graph build itself publishes
        # into the shared database and writes no graph folder.
        cls.store_after_graph_build = sorted(p.name for p in index_dir.iterdir())
        cls.communities = graph_cluster.update_graph_clusters(
            root=root, index_dir=index_dir, layer="project",
            graph_payload=cls.payload)
        cls.sections = _parity_sections(
            root, cls.files, cls.payload, cls.communities,
            cls.fixture["normalization"])

    @classmethod
    def tearDownClass(cls):
        tmp = getattr(cls, "_tmp", None)
        if tmp is not None:
            tmp.cleanup()

    def _sections(self):
        sections = getattr(self, "sections", None)
        if sections is None:
            self.fail("the parity build did not run; see the corpus-identity test")
        # 1xtnr keeps the archived 1xny6 fixture byte-for-byte. On this
        # unchanged corpus, builder52 changes only two version labels and
        # adds the explicitly empty integrity snapshot below. Assert those
        # new values before adapting metadata to the archived digest; never
        # normalize nodes, edges, evidence, coverage or community membership.
        self.assertEqual(sections["graph"]["builder_version"], "52")
        self.assertEqual(sections["communities"]["graph_builder_version"], "52")
        self.assertEqual(sections["graph"]["call_integrity"], {
            "non_callable_call_targets": 0,
            "callable_wins_collisions": 0,
            "callable_wins_collision_details": [],
            "malformed_external_call_targets_dropped": 0,
        })
        self.assertEqual(self.fixture["graph"]["builder_version"], "51")
        self.assertEqual(self.fixture["communities"]["graph_builder_version"], "51")
        normalized = json.loads(json.dumps(sections))
        normalized["graph"]["builder_version"] = "51"
        normalized["graph"].pop("call_integrity")
        normalized["communities"]["graph_builder_version"] = "51"
        return normalized

    def test_metadata_adaptation_never_masks_node_or_edge_changes(self):
        for section, key in (("nodes", "label"), ("edge_evidence_multiset", "confidence")):
            changed = json.loads(json.dumps(self.sections))
            rows = changed["graph"][section]
            self.assertTrue(rows)
            if section == "nodes":
                rows[0][key] = "injected-node-regression"
                assertion = self.test_node_identities_and_attributes_match_the_baseline
            else:
                rows[0]["edge"][key] = "injected-edge-regression"
                assertion = self.test_edge_evidence_multiset_matches_including_multiplicity
            with self.subTest(section=section), patch.object(self, "sections", changed):
                with self.assertRaises(AssertionError):
                    assertion()

    def test_the_corpus_is_the_one_the_baseline_was_captured_from(self):
        recorded = self.fixture["corpus"]
        self.assertTrue(
            CORPUS.is_file(),
            f"the parity baseline pins {recorded['path']} by sha256 and records no "
            "copy of it, so an absent corpus is a failure, never a skip")
        digest = hashlib.sha256(CORPUS.read_bytes()).hexdigest()
        self.assertEqual(
            recorded["sha256"], digest,
            "the evaluation corpus drifted from the one the parity baseline was "
            "captured over; re-capture the fixture rather than relaxing this")
        self.assertEqual(recorded["files"], len(self._sections()
                                                ["extraction_coverage"]
                                                ["declared_corpus_files"]))

    def test_node_identities_and_attributes_match_the_baseline(self):
        expected = self.fixture["graph"]["nodes"]
        actual = self._sections()["graph"]["nodes"]
        self.assertEqual([n["id"] for n in expected], [n["id"] for n in actual])
        self.assertEqual(_canon(expected), _canon(actual))
        self.assertEqual(self.fixture["graph"]["node_count"], len(actual))

    def test_edge_evidence_multiset_matches_including_multiplicity(self):
        expected = self.fixture["graph"]["edge_evidence_multiset"]
        actual = self._sections()["graph"]["edge_evidence_multiset"]
        # Multiplicity first: a silently dropped duplicate is the regression a
        # plain set comparison cannot see.
        self.assertEqual([m["multiplicity"] for m in expected],
                         [m["multiplicity"] for m in actual])
        self.assertEqual(_canon(expected), _canon(actual))
        self.assertEqual(self.fixture["graph"]["edge_count_with_multiplicity"],
                         self._sections()["graph"]["edge_count_with_multiplicity"])
        self.assertEqual(self.fixture["graph"]["distinct_edge_count"],
                         self._sections()["graph"]["distinct_edge_count"])

    def test_graph_section_matches_the_baseline_whole(self):
        # Counts, layer, input fingerprint and the builder/schema versions the
        # payload carries, on top of the node and edge sections above.
        self.assertEqual(_canon(self.fixture["graph"]),
                         _canon(self._sections()["graph"]))

    def test_extraction_coverage_matches_the_baseline(self):
        expected = self.fixture["extraction_coverage"]
        actual = self._sections()["extraction_coverage"]
        for key in sorted(expected):
            with self.subTest(field=key):
                self.assertEqual(_canon(expected[key]), _canon(actual.get(key)))
        self.assertEqual(_canon(expected), _canon(actual))

    def test_community_output_matches_the_baseline(self):
        expected = self.fixture["communities"]
        actual = self._sections()["communities"]
        # Named first so a missing community backend reads as "different
        # backend" instead of a ten-kilobyte membership diff. The baseline was
        # captured on igraph+leidenalg with the producer's own seeding; the
        # label-propagation fallback cannot reproduce it and must not be
        # silently accepted as parity.
        self.assertEqual(
            expected["cluster_algorithm"], actual.get("cluster_algorithm"),
            "the parity baseline was captured with the "
            f"{self.fixture['community_seed']['backend']} community backend")
        self.assertEqual([c["community_id"] for c in expected["communities"]],
                         [c["community_id"] for c in actual["communities"]])
        self.assertEqual([c["node_ids"] for c in expected["communities"]],
                         [c["node_ids"] for c in actual["communities"]])
        self.assertEqual(_canon(expected["betweenness"]), _canon(actual["betweenness"]))
        self.assertEqual(_canon(expected), _canon(actual))

    def test_every_recorded_digest_re_derives(self):
        sections = self._sections()
        digests = self.fixture["digests"]
        self.assertEqual(digests["nodes_sha256"], _sha(sections["graph"]["nodes"]))
        self.assertEqual(digests["edge_evidence_multiset_sha256"],
                         _sha(sections["graph"]["edge_evidence_multiset"]))
        self.assertEqual(digests["extraction_coverage_sha256"],
                         _sha(sections["extraction_coverage"]))
        self.assertEqual(digests["communities_sha256"], _sha(sections["communities"]))
        self.assertEqual(digests["body_sha256"], _sha(sections))
        # The repeatability claim the fixture makes about itself.
        self.assertEqual(self.fixture["repeatability"]["body_digest"],
                         digests["body_sha256"])

    def test_the_parity_build_publishes_into_the_shared_store(self):
        # The parity corpus is built through the product entry, so the baseline
        # is re-derived against schema-8 storage rather than a retired folder.
        self.assertEqual([index_paths.RUNTIME_DATABASE_FILENAME],
                         self.store_after_graph_build)


class EvaluatorFailedPublicationRollbackTests(unittest.TestCase):
    """The evaluator's production publisher rolls back actual SQLite writes.

    This inline corpus keeps bootstrap and rollback coverage independent of
    the optional repository evaluation corpus and its parity artifacts.
    """

    def setUp(self):
        self.corpus = {"files": {"src/a.py":
            "def helper():\n    return 1\n\ndef caller():\n    return helper()\n"}}
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()

    def _graph_row_counts(self):
        import graph_store
        import sqlite_runtime
        path = self.root / ".wavefoundry" / "index" / index_paths.RUNTIME_DATABASE_FILENAME
        self.assertTrue(path.is_file(), "the production path must bootstrap the shared store")
        conn = sqlite_runtime.connect(path, read_only=True)
        try:
            return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                    for t in graph_store.GRAPH_TABLES}
        finally:
            conn.close()

    def test_inline_corpus_bootstraps_shared_storage(self):
        subject.build_graph_over_corpus(self.corpus, self.root)
        self.assertGreater(self._graph_row_counts()["graph_nodes"], 0)
        self.assertFalse((self.root / ".wavefoundry" / "index" / "graph").exists())

    def test_missing_extraction_result_refuses_publication(self):
        with patch.object(graph_indexer.GraphIndexSession, "record_file") as record:
            with self.assertRaisesRegex(RuntimeError, "graph extraction incomplete: src/a.py"):
                subject.build_graph_over_corpus(self.corpus, self.root)
        record.assert_called_once()
        counts = self._graph_row_counts()
        self.assertEqual({t: 0 for t in counts}, counts)

    def test_a_producer_failure_after_partial_writes_commits_no_graph_rows(self):
        original = graph_indexer.GraphPublication.apply
        written = []

        def failing_apply(publication, conn):
            original(publication, conn)
            self.assertFalse(conn.get_autocommit(), "writes must share the publisher transaction")
            written.append(conn.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()[0])
            raise RuntimeError("injected failure after actual graph writes")

        with patch.object(graph_indexer.GraphPublication, "apply", failing_apply):
            with self.assertRaisesRegex(RuntimeError, "after actual graph writes"):
                subject.build_graph_over_corpus(self.corpus, self.root)

        self.assertEqual(len(written), 1, "the real publisher must reach the fault")
        self.assertGreater(written[0], 0, "preparation alone does not prove rollback")
        counts = self._graph_row_counts()
        self.assertEqual({t: 0 for t in counts}, counts,
                         "a failed producer committed graph rows")
        self.assertFalse((self.root / ".wavefoundry" / "index" / "graph").exists())


if __name__ == "__main__":
    unittest.main()
