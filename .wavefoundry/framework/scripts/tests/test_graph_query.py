"""Tests for graph_query.py — load, union, traversal, and report helpers."""

from __future__ import annotations

import importlib.util
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]


def load_graph_query():
    sys.modules.pop("graph_query", None)
    spec = importlib.util.spec_from_file_location("graph_query", SCRIPTS / "graph_query.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _write_graph(root: Path, layer: str, payload: dict) -> None:
    if layer == "project":
        graph_dir = root / ".wavefoundry" / "index" / "graph"
    else:
        graph_dir = root / ".wavefoundry" / "framework" / "index" / "graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    name = "project-graph.json" if layer == "project" else "framework-graph.json"
    (graph_dir / name).write_text(json.dumps(payload), encoding="utf-8")


FIXTURE_GRAPH = {
    "schema_version": "1",
    "builder_version": "1",
    "layer": "project",
    "nodes": [
        {"id": "src/a.py", "label": "a", "kind": "module", "source_file": "src/a.py", "layer": "project"},
        {"id": "src/a.py::foo", "label": "foo", "kind": "function", "source_file": "src/a.py", "layer": "project"},
        {"id": "src/b.py", "label": "b", "kind": "module", "source_file": "src/b.py", "layer": "project"},
        {"id": "src/b.py::bar", "label": "bar", "kind": "function", "source_file": "src/b.py", "layer": "project"},
        {"id": "docs/guide.md", "label": "guide", "kind": "doc", "source_file": "docs/guide.md", "layer": "project"},
    ],
    "edges": [
        {"source": "src/a.py::foo", "target": "src/b.py::bar", "relation": "calls", "confidence": "EXTRACTED"},
        {"source": "src/b.py", "target": "src/a.py", "relation": "imports", "confidence": "EXTRACTED"},
        {"source": "docs/guide.md", "target": "src/a.py::foo", "relation": "doc_references_code", "confidence": "AMBIGUOUS"},
    ],
    "counts": {"files": 3, "nodes": 5, "edges": 3},
}


class GraphQueryLoadTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_graph_query()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_graph_missing_returns_empty(self):
        payload = self.mod.load_graph(self.root, layer="project")
        self.assertFalse(payload["present"])
        self.assertEqual(payload["nodes"], [])

    def test_load_graph_reads_fixture(self):
        _write_graph(self.root, "project", FIXTURE_GRAPH)
        payload = self.mod.load_graph(self.root, layer="project")
        self.assertTrue(payload["present"])
        self.assertEqual(len(payload["nodes"]), 5)

    def test_load_union_composes_layers(self):
        _write_graph(self.root, "project", FIXTURE_GRAPH)
        framework = {
            **FIXTURE_GRAPH,
            "layer": "framework",
            "nodes": [
                {"id": ".wavefoundry/framework/seeds/x.md", "label": "x", "kind": "seed", "source_file": ".wavefoundry/framework/seeds/x.md", "layer": "framework"},
            ],
            "edges": [],
            "counts": {"files": 1, "nodes": 1, "edges": 0},
        }
        _write_graph(self.root, "framework", framework)
        try:
            import networkx  # noqa: F401
        except ImportError:
            self.skipTest("networkx unavailable")
        union = self.mod.load_union(self.root)
        self.assertTrue(union["present"])
        self.assertEqual(union["layer"], "union")
        self.assertEqual(len(union["nodes"]), 6)
        layers = {node.get("layer") for node in union["nodes"]}
        self.assertEqual(layers, {"project", "framework"})


class GraphQueryTraversalTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_graph_query()
        self.index = self.mod.GraphQueryIndex(FIXTURE_GRAPH | {"present": True})

    def test_resolve_symbol_qualified(self):
        self.assertEqual(self.index.resolve_symbol("src/a.py::foo"), "src/a.py::foo")

    def test_resolve_symbol_qualified_alias_for_merged_class(self):
        """131bu polish 1: when a Swift class/module merge consumed the class node
        into the file id (`Foo.swift` is now `kind: class, label: Foo, collapsed_pair: True`),
        querying the natural qualified form `Foo.swift::Foo` should alias to the
        file id rather than returning graph_symbol_not_found. Confirmed-design
        outcome from Solaris field validation on wave 131bt 1319v."""
        idx = self.mod.GraphQueryIndex({
            "present": True,
            "nodes": [
                {"id": "Sources/Foo.swift", "label": "Foo", "kind": "class", "collapsed_pair": True},
                {"id": "Sources/Bar.swift", "label": "Bar", "kind": "module"},
            ],
            "edges": [],
        })
        # Qualified-id alias resolves to the file id.
        self.assertEqual(idx.resolve_symbol("Sources/Foo.swift::Foo"), "Sources/Foo.swift")
        # Bare symbol still resolves via label.
        self.assertEqual(idx.resolve_symbol("Foo"), "Sources/Foo.swift")
        # Non-merged file's natural qualified form does NOT alias (no collapsed_pair).
        self.assertIsNone(idx.resolve_symbol("Sources/Bar.swift::Bar"))
        # Wrong class name in alias position is not consumed.
        self.assertIsNone(idx.resolve_symbol("Sources/Foo.swift::Quux"))

    def test_graph_impact_finds_callers(self):
        impact = self.index.graph_impact("src/b.py::bar", max_hops=2)
        self.assertTrue(impact["resolved"])
        node_ids = {row["node_id"] for row in impact["affected"]}
        self.assertIn("src/a.py::foo", node_ids)

    def test_callgraph_both_directions(self):
        result = self.index.callgraph("src/b.py::bar", depth=1, direction="both")
        self.assertTrue(result["resolved"])
        relations = {edge["relation"] for edge in result["edges"]}
        self.assertEqual(relations, {"calls"})

    def test_report_fan_in_and_orphans(self):
        report = self.index.report(limit=10)
        self.assertIn("fan_in", report)
        self.assertTrue(any(row["node_id"] == "src/b.py::bar" for row in report["fan_in"]))
        orphan_ids = {row["node_id"] for row in report.get("orphan_docs", [])}
        self.assertNotIn("docs/guide.md", orphan_ids)


# Wave 1p41o: code_risk_score composite (blast-radius × log-dampened degree).
_RISK_FIXTURE = {
    "present": True,
    "layer": "project",
    "nodes": [
        {"id": "src/m.py", "label": "m", "kind": "module", "source_file": "src/m.py"},
        {"id": "src/m.py::hub", "label": "hub", "kind": "function", "source_file": "src/m.py"},
        {"id": "src/m.py::mid", "label": "mid", "kind": "function", "source_file": "src/m.py"},
        {"id": "src/m.py::leaf", "label": "leaf", "kind": "function", "source_file": "src/m.py"},
        {"id": "src/m.py::driver", "label": "driver", "kind": "function", "source_file": "src/m.py"},
        {"id": "src/c1.py::a", "label": "a", "kind": "function", "source_file": "src/c1.py"},
        {"id": "src/c2.py::b", "label": "b", "kind": "function", "source_file": "src/c2.py"},
        {"id": "src/c3.py::c", "label": "c", "kind": "function", "source_file": "src/c3.py"},
        {"id": "src/tests/test_x.py::t", "label": "t", "kind": "function", "source_file": "src/tests/test_x.py"},
    ],
    "edges": [
        {"source": "src/c1.py::a", "target": "src/m.py::hub", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
        {"source": "src/c2.py::b", "target": "src/m.py::hub", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
        {"source": "src/c3.py::c", "target": "src/m.py::hub", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
        {"source": "src/tests/test_x.py::t", "target": "src/m.py::hub", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
        {"source": "src/c1.py::a", "target": "src/m.py::mid", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
        {"source": "src/m.py::driver", "target": "src/m.py::hub", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
    ],
}


class GraphQueryRiskScoreTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_graph_query()
        self.index = self.mod.GraphQueryIndex(dict(_RISK_FIXTURE))

    def _by_label(self, results):
        return {r["label"]: r for r in results}

    def test_ranking_and_formula(self):
        out = self.index.risk_score("src/m.py")
        self.assertFalse(out["over_candidate_cap"])
        self.assertEqual(out["score_formula"], "risk = affected_file_count * log1p(fan_in)")
        self.assertEqual(out["score_components"], ["affected_file_count", "fan_in", "fan_out"])
        results = out["results"]
        # Descending by risk; hub (high fan_in + blast radius) is the top risk.
        risks = [r["risk"] for r in results]
        self.assertEqual(risks, sorted(risks, reverse=True))
        self.assertEqual(results[0]["label"], "hub")
        # The composite holds exactly for every entry (math, not hardcoded afc).
        for r in results:
            self.assertAlmostEqual(
                r["risk"], r["affected_file_count"] * math.log1p(r["fan_in"]), places=9
            )

    def test_components_surfaced(self):
        by = self._by_label(self.index.risk_score("src/m.py")["results"])
        # fan_in is raw calls-in degree (matches report(), NOT test-filtered):
        # hub is called by a, b, c, driver, and the test caller t = 5. Only the
        # blast-radius afc is test-filtered (matches code_impact) — the
        # asymmetry is intentional.
        self.assertEqual(by["hub"]["fan_in"], 5)
        self.assertEqual(by["hub"]["fan_out"], 0)
        self.assertEqual(by["mid"]["fan_in"], 1)
        # driver: high-ish fan_out, no callers → fan_out is NOT folded into risk.
        self.assertEqual(by["driver"]["fan_out"], 1)
        self.assertEqual(by["driver"]["fan_in"], 0)
        self.assertEqual(by["driver"]["risk"], 0)
        # leaf: nothing calls it → zero risk.
        self.assertEqual(by["leaf"]["risk"], 0)

    def test_top_cap(self):
        out = self.index.risk_score("src/m.py", top=1)
        self.assertEqual(len(out["results"]), 1)
        self.assertEqual(out["results"][0]["label"], "hub")

    def test_empty_scope_is_not_over_cap(self):
        out = self.index.risk_score("src/nonexistent.py")
        self.assertFalse(out["over_candidate_cap"])
        self.assertEqual(out["results"], [])
        self.assertEqual(out["candidate_count"], 0)

    def test_over_candidate_cap(self):
        out = self.index.risk_score("src/m.py", candidate_cap=2)
        self.assertTrue(out["over_candidate_cap"])
        self.assertEqual(out["results"], [])
        self.assertEqual(out["candidate_count"], 4)

    def test_glob_scope(self):
        out = self.index.risk_score("src/m*.py")
        self.assertTrue(any(r["label"] == "hub" for r in out["results"]))

    def test_test_path_filter_excludes_test_callers(self):
        # hub is called from src/tests/test_x.py::t; with the test filter the
        # test file must NOT count toward hub's blast radius.
        with_tests = self._by_label(self.index.risk_score("src/m.py")["results"])
        no_tests = self._by_label(
            self.index.risk_score("src/m.py", is_test_path=lambda p: "/tests/" in p)["results"]
        )
        self.assertEqual(with_tests["hub"]["affected_file_count"] - 1,
                         no_tests["hub"]["affected_file_count"])


class GraphQueryShortestPathTests(unittest.TestCase):
    """12zxl AC-4: GraphQueryIndex.shortest_path()."""

    def setUp(self):
        self.mod = load_graph_query()
        self.index = self.mod.GraphQueryIndex(FIXTURE_GRAPH | {"present": True})

    def test_path_found(self):
        result = self.index.shortest_path("src/a.py::foo", "src/b.py::bar")
        self.assertTrue(result["found"])
        node_ids = [n["node_id"] for n in result["path_nodes"]]
        self.assertEqual(node_ids[0], "src/a.py::foo")
        self.assertEqual(node_ids[-1], "src/b.py::bar")
        self.assertGreater(result["hop_count"], 0)
        self.assertEqual(len(result["path_edges"]), result["hop_count"])

    def test_path_not_found_returns_empty_shape(self):
        # No reverse path from bar → foo in the fixture
        result = self.index.shortest_path("src/b.py::bar", "src/a.py::foo")
        self.assertFalse(result["found"])
        self.assertEqual(result["path_nodes"], [])
        self.assertEqual(result["path_edges"], [])
        self.assertEqual(result["hop_count"], 0)

    def test_same_symbol_hop_count_zero(self):
        result = self.index.shortest_path("src/a.py::foo", "src/a.py::foo")
        self.assertTrue(result["found"])
        self.assertEqual(result["hop_count"], 0)
        self.assertEqual(len(result["path_nodes"]), 1)

    def test_max_hops_exceeded_returns_not_found(self):
        result = self.index.shortest_path("src/a.py::foo", "src/b.py::bar", max_hops=0)
        self.assertFalse(result["found"])

    def test_path_prefers_construction_resolved_over_extracted_on_tie(self):
        """131bu polish 2: when BFS finds multiple paths of equal hop count from
        source to destination, prefer paths through deterministic-attribution
        edges (CONSTRUCTION_RESOLVED / RECEIVER_RESOLVED) over EXTRACTED. From
        Solaris field validation: a construction edge would tie with an
        EXTRACTED import-placeholder edge; the construction edge is the more
        useful path to surface."""
        idx = self.mod.GraphQueryIndex({
            "present": True,
            "nodes": [
                {"id": "AppDelegate.swift::App.go", "label": "go", "kind": "function"},
                {"id": "StatusBarManager.swift", "label": "StatusBarManager", "kind": "class"},
                {"id": "external::t", "label": "t", "kind": "external"},
            ],
            "edges": [
                # Direct construction edge — deterministic attribution.
                {
                    "source": "AppDelegate.swift::App.go",
                    "target": "StatusBarManager.swift",
                    "relation": "calls",
                    "confidence": "CONSTRUCTION_RESOLVED",
                },
                # Phantom import path with same hop count — EXTRACTED.
                {
                    "source": "AppDelegate.swift::App.go",
                    "target": "external::t",
                    "relation": "imports",
                    "confidence": "EXTRACTED",
                },
                {
                    "source": "external::t",
                    "target": "StatusBarManager.swift",
                    "relation": "imports",
                    "confidence": "EXTRACTED",
                },
            ],
        })
        result = idx.shortest_path("AppDelegate.swift::App.go", "StatusBarManager.swift")
        self.assertTrue(result["found"])
        self.assertEqual(result["hop_count"], 1, "should surface the 1-hop construction edge, not the 2-hop import path")
        edge_confidences = [e.get("confidence") for e in result["path_edges"]]
        self.assertEqual(edge_confidences, ["CONSTRUCTION_RESOLVED"],
                         f"BFS should prefer CONSTRUCTION_RESOLVED on tie; got {edge_confidences}")

    def test_unresolvable_symbol_returns_not_found(self):
        result = self.index.shortest_path("no_such_symbol", "src/b.py::bar")
        self.assertFalse(result["found"])
        self.assertEqual(result["path_nodes"], [])


class GraphQueryShortestPathBackwardTests(unittest.TestCase):
    """13006 AC-2: shortest_path(direction='backward') walks incoming edges only."""

    def setUp(self):
        self.mod = load_graph_query()
        self.index = self.mod.GraphQueryIndex(FIXTURE_GRAPH | {"present": True})

    def test_backward_finds_path_via_incoming_edges(self):
        # In fixture: foo → bar (calls). Forward from bar to foo: no path.
        # Backward from bar to foo: traverse _in[bar] = the calls edge from foo → bar.
        result = self.index.shortest_path("src/b.py::bar", "src/a.py::foo", direction="backward")
        self.assertTrue(result["found"])
        self.assertEqual(result["hop_count"], 1)
        node_ids = [n["node_id"] for n in result["path_nodes"]]
        self.assertEqual(node_ids, ["src/b.py::bar", "src/a.py::foo"])

    def test_backward_no_path_when_no_incoming_chain(self):
        # No backward path from foo to bar (bar has no _in edges that chain to foo).
        result = self.index.shortest_path("src/a.py::foo", "src/b.py::bar", direction="backward")
        self.assertFalse(result["found"])
        self.assertEqual(result["path_nodes"], [])
        self.assertEqual(result["hop_count"], 0)

    def test_backward_preserves_consistent_shape_on_not_found(self):
        result = self.index.shortest_path("src/a.py::foo", "no_such_symbol", direction="backward")
        self.assertFalse(result["found"])
        self.assertEqual(result["path_nodes"], [])
        self.assertEqual(result["path_edges"], [])
        self.assertEqual(result["hop_count"], 0)


class GraphQueryShortestPathEitherTests(unittest.TestCase):
    """13006 AC-3: shortest_path(direction='either') walks both directions with annotation."""

    def setUp(self):
        self.mod = load_graph_query()
        self.index = self.mod.GraphQueryIndex(FIXTURE_GRAPH | {"present": True})

    def test_either_finds_forward_path(self):
        # foo → bar exists via forward calls edge
        result = self.index.shortest_path("src/a.py::foo", "src/b.py::bar", direction="either")
        self.assertTrue(result["found"])
        self.assertEqual(result["hop_count"], 1)
        # traversal_direction annotation must be present on the edge
        self.assertEqual(result["path_edges"][0].get("traversal_direction"), "forward")

    def test_either_finds_backward_path(self):
        # bar to foo requires walking _in
        result = self.index.shortest_path("src/b.py::bar", "src/a.py::foo", direction="either")
        self.assertTrue(result["found"])
        self.assertEqual(result["hop_count"], 1)
        self.assertEqual(result["path_edges"][0].get("traversal_direction"), "backward")

    def test_either_annotates_each_edge(self):
        # Verify every edge in path_edges has traversal_direction
        result = self.index.shortest_path("src/b.py::bar", "src/a.py::foo", direction="either")
        for e in result["path_edges"]:
            self.assertIn(e.get("traversal_direction"), ("forward", "backward"))

    def test_either_hop_count_matches_path_edges(self):
        result = self.index.shortest_path("src/a.py::foo", "src/b.py::bar", direction="either")
        self.assertEqual(result["hop_count"], len(result["path_edges"]))


class GraphQueryShortestPathDirectionValidationTests(unittest.TestCase):
    """13006 AC-5: invalid direction values are rejected with ValueError."""

    def setUp(self):
        self.mod = load_graph_query()
        self.index = self.mod.GraphQueryIndex(FIXTURE_GRAPH | {"present": True})

    def test_invalid_direction_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.index.shortest_path("src/a.py::foo", "src/b.py::bar", direction="sideways")

    def test_direction_case_insensitive(self):
        # "FORWARD" should be normalized to "forward"
        result = self.index.shortest_path("src/a.py::foo", "src/b.py::bar", direction="FORWARD")
        self.assertTrue(result["found"])

    def test_forward_is_default_unchanged(self):
        # AC-1 byte-identity: forward without explicit direction matches direction="forward"
        result_default = self.index.shortest_path("src/a.py::foo", "src/b.py::bar")
        result_forward = self.index.shortest_path("src/a.py::foo", "src/b.py::bar", direction="forward")
        self.assertEqual(result_default, result_forward)


class GraphQueryBetweennessTests(unittest.TestCase):
    """12zxl AC-3: GraphQueryIndex.report(sections=['betweenness'])."""

    def setUp(self):
        self.mod = load_graph_query()
        self.index = self.mod.GraphQueryIndex(FIXTURE_GRAPH | {"present": True})

    def test_betweenness_node_count_guard(self):
        original = self.mod._BETWEENNESS_NODE_LIMIT
        self.mod._BETWEENNESS_NODE_LIMIT = 2  # fixture has 5 nodes → triggers guard
        try:
            result = self.index.report(sections=["betweenness"])
            self.assertIn("betweenness", result)
            self.assertEqual(result["betweenness"]["diagnostic"], "graph_too_large_for_betweenness")
        finally:
            self.mod._BETWEENNESS_NODE_LIMIT = original

    def test_betweenness_igraph_unavailable(self):
        import unittest.mock
        with unittest.mock.patch.dict(sys.modules, {"igraph": None}):
            result = self.index.report(sections=["betweenness"])
            self.assertIn("betweenness", result)
            self.assertEqual(result["betweenness"]["diagnostic"], "igraph_unavailable")

    def test_betweenness_returns_list_when_igraph_available(self):
        try:
            import igraph  # noqa: F401
        except ImportError:
            self.skipTest("igraph unavailable")
        result = self.index.report(sections=["betweenness"])
        self.assertIn("betweenness", result)
        self.assertIsInstance(result["betweenness"], list)


class GraphAugmentationExplicitOptOutTests(unittest.TestCase):
    """12xs5 — verify explicit graph=False still suppresses graph_neighbors.

    These tests previously enforced the OLD contract (graph=false byte-identity by
    default). After the wave 12xr3 promotion, the default flipped to graph=True;
    the suppression code path is now exercised only when callers pass graph=False
    explicitly. These tests guard that opt-out path against regression.
    """

    @classmethod
    def setUpClass(cls):
        from test_server_tools import load_server

        cls.srv = load_server()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps({"lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0}}),
            encoding="utf-8",
        )
        (self.root / "src").mkdir(parents=True, exist_ok=True)
        (self.root / "src" / "sample.py").write_text("def alpha():\n    return 1\n", encoding="utf-8")
        (self.root / "src" / "use_sample.py").write_text(
            "from src.sample import alpha\n\nalpha()\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_code_keyword_response_default_lean_when_no_graph(self):
        """code_keyword_response (internal, no graph-aware wrapper) stays lean — no graph_neighbors."""
        result = self.srv.code_keyword_response(self.root, query="alpha")
        self.assertEqual(result["status"], "ok")
        self.assertNotIn("graph_neighbors", result.get("data") or {})

    def test_code_definition_response_default_lean_when_no_graph(self):
        """code_definition_response (internal) stays lean — augmentation lives at MCP wrapper layer."""
        result = self.srv.code_definition_response(self.root, "alpha")
        self.assertEqual(result["status"], "ok")
        self.assertNotIn("graph_neighbors", result.get("data") or {})


class GraphQueryShortestPathWeightedCostTests(unittest.TestCase):
    """Wave 1p2q3 (1p2q4): Aceiss reproducer for spurious 2-hop paths via shared
    external::* bridges. Weighted-cost Dijkstra-equivalent BFS + non-transitive
    external intermediates must surface the real call chain over the phantom."""

    def setUp(self):
        self.mod = load_graph_query()

    def _build(self, edges, nodes=None):
        if nodes is None:
            ids = set()
            for e in edges:
                ids.add(e["source"]); ids.add(e["target"])
            nodes = [{"id": nid, "label": nid.split("::")[-1],
                      "kind": "external" if nid.startswith("external::") else "function"} for nid in ids]
        return self.mod.GraphQueryIndex({"present": True, "nodes": nodes, "edges": edges})

    def test_aceiss_reproducer_calls_chain_beats_external_bridge(self):
        edges = [
            {"source": "A", "target": "B", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
            {"source": "B", "target": "C", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
            {"source": "C", "target": "D", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
            {"source": "A", "target": "external::common", "relation": "calls", "confidence": "EXTRACTED"},
            {"source": "external::common", "target": "D", "relation": "calls", "confidence": "EXTRACTED"},
        ]
        idx = self._build(edges)
        result = idx.shortest_path("A", "D")
        self.assertTrue(result["found"])
        node_ids = [n["node_id"] for n in result["path_nodes"]]
        self.assertEqual(node_ids, ["A", "B", "C", "D"])

    def test_external_node_is_non_transitive_intermediate(self):
        edges = [
            {"source": "A", "target": "external::bridge", "relation": "calls", "confidence": "EXTRACTED"},
            {"source": "external::bridge", "target": "D", "relation": "calls", "confidence": "EXTRACTED"},
        ]
        idx = self._build(edges)
        result = idx.shortest_path("A", "D")
        self.assertFalse(result["found"])

    def test_external_node_as_endpoint_still_works(self):
        edges = [
            {"source": "A", "target": "external::lib.foo", "relation": "calls", "confidence": "EXTRACTED"},
        ]
        idx = self._build(edges)
        result = idx.shortest_path("A", "external::lib.foo")
        self.assertTrue(result["found"])
        self.assertEqual(result["hop_count"], 1)

    def test_min_confidence_filter_excludes_extracted_edges(self):
        edges = [
            {"source": "A", "target": "B", "relation": "calls", "confidence": "EXTRACTED"},
            {"source": "B", "target": "D", "relation": "calls", "confidence": "EXTRACTED"},
        ]
        idx = self._build(edges)
        self.assertTrue(idx.shortest_path("A", "D")["found"])
        self.assertFalse(idx.shortest_path("A", "D", min_confidence="RECEIVER_RESOLVED")["found"])


class GraphQueryAutoRebuildCallbackTests(unittest.TestCase):
    """Wave 1p2q3 (131hh): post-rebuild callback registry + dispatch."""

    def setUp(self):
        self.mod = load_graph_query()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        try:
            self.mod.set_post_rebuild_callback(None)
        except Exception:
            pass
        self.tmp.cleanup()

    def test_set_post_rebuild_callback_registers_and_clears(self):
        self.assertIsNone(self.mod._POST_REBUILD_CALLBACK)
        fn = lambda **kw: None  # noqa: E731
        self.mod.set_post_rebuild_callback(fn)
        self.assertIs(self.mod._POST_REBUILD_CALLBACK, fn)
        self.mod.set_post_rebuild_callback(None)
        self.assertIsNone(self.mod._POST_REBUILD_CALLBACK)

    def _seed_stale_graph(self):
        graph_dir = self.root / ".wavefoundry" / "index" / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        (graph_dir / "project-graph.json").write_text(
            json.dumps({"present": True, "nodes": [], "edges": []}), encoding="utf-8")
        (graph_dir / "project-graph-state.json").write_text(
            json.dumps({"builder_version": "0"}), encoding="utf-8")

    def _with_fake_rebuild(self):
        from unittest.mock import patch
        self.mod._get_graph_indexer()
        real_spec = importlib.util.spec_from_file_location
        real_module = importlib.util.module_from_spec

        class _FakeLoader:
            def exec_module(self, module):
                module.build_index = lambda *a, **k: {"ok": True}

        class _FakeSpec:
            name = "indexer_for_graph_query_rebuild"
            loader = _FakeLoader()

        def _fake_spec(name, path):
            if name == "indexer_for_graph_query_rebuild":
                return _FakeSpec()
            return real_spec(name, path)

        def _fake_module(spec):
            if getattr(spec, "name", "") == "indexer_for_graph_query_rebuild":
                import types
                return types.ModuleType("fake_indexer_for_rebuild")
            return real_module(spec)

        return patch("importlib.util.spec_from_file_location", _fake_spec), \
               patch("importlib.util.module_from_spec", _fake_module)

    def test_callback_fires_after_successful_auto_rebuild(self):
        self._seed_stale_graph()
        calls: list[dict] = []
        self.mod.set_post_rebuild_callback(lambda **kw: calls.append(kw))
        p1, p2 = self._with_fake_rebuild()
        with p1, p2:
            diag = self.mod._ensure_graph_builder_current(self.root, "project")
        self.assertIsNotNone(diag)
        self.assertEqual(diag["code"], "graph_auto_rebuilt")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["layer"], "project")
        self.assertEqual(calls[0]["root"], self.root)

    def test_callback_exception_does_not_break_rebuild(self):
        self._seed_stale_graph()
        self.mod.set_post_rebuild_callback(lambda **kw: (_ for _ in ()).throw(RuntimeError("boom")))
        p1, p2 = self._with_fake_rebuild()
        with p1, p2:
            diag = self.mod._ensure_graph_builder_current(self.root, "project")
        self.assertEqual(diag["code"], "graph_auto_rebuilt")

    def test_concurrent_auto_rebuild_defers_via_inflight_marker(self):
        """Wave 1p2q3 (1p2w5 / Bug 3): a second `_ensure_graph_builder_current`
        call that arrives while another rebuild is in-flight must defer with
        a `graph_auto_rebuild_in_progress` diagnostic instead of racing for
        the index-build flock. Reproduces the noisy
        `graph_auto_rebuild_failed` spam Teton observed during the v22→v23
        auto-rebuild window."""
        self._seed_stale_graph()
        cache_key = (str(self.root.resolve()), "project")
        # Pre-populate the in-flight marker with a started_at well inside the
        # stale-inflight window (i.e. a "live" rebuild that hasn't crashed).
        import time
        with self.mod._VERSION_REBUILD_INFLIGHT_LOCK:
            self.mod._VERSION_REBUILD_INFLIGHT[cache_key] = time.time()
        try:
            diag = self.mod._ensure_graph_builder_current(self.root, "project")
        finally:
            with self.mod._VERSION_REBUILD_INFLIGHT_LOCK:
                self.mod._VERSION_REBUILD_INFLIGHT.pop(cache_key, None)
        self.assertIsNotNone(diag)
        self.assertEqual(diag["code"], "graph_auto_rebuild_in_progress")
        self.assertIn("rebuild_started_at_age_seconds", diag)
        self.assertGreaterEqual(diag["rebuild_started_at_age_seconds"], 0)
        self.assertEqual(diag["recovery_tools"], ["wave_index_build_status"])

    def test_stale_inflight_marker_allows_fresh_rebuild_attempt(self):
        """Wave 1p2q3 (1p2w5 / Bug 3 AC-5): an in-flight marker older than
        `_INFLIGHT_REBUILD_STALE_SECONDS` does not pin future rebuild
        attempts. Without the safety net a crashed rebuild that never
        reached the finally-pop would block every subsequent auto-rebuild
        indefinitely."""
        self._seed_stale_graph()
        cache_key = (str(self.root.resolve()), "project")
        # Marker older than the stale-inflight threshold.
        import time
        stale_age = self.mod._INFLIGHT_REBUILD_STALE_SECONDS + 1
        with self.mod._VERSION_REBUILD_INFLIGHT_LOCK:
            self.mod._VERSION_REBUILD_INFLIGHT[cache_key] = time.time() - stale_age
        p1, p2 = self._with_fake_rebuild()
        try:
            with p1, p2:
                diag = self.mod._ensure_graph_builder_current(self.root, "project")
        finally:
            with self.mod._VERSION_REBUILD_INFLIGHT_LOCK:
                self.mod._VERSION_REBUILD_INFLIGHT.pop(cache_key, None)
        self.assertIsNotNone(diag)
        self.assertEqual(diag["code"], "graph_auto_rebuilt")

    def test_inflight_marker_released_on_success_and_failure(self):
        """Wave 1p2q3 (1p2w5 / Bug 3): the in-flight marker is released on
        every exit path. The finally clause runs after both the try
        (success → graph_auto_rebuilt) and except (failure →
        graph_auto_rebuild_failed) branches. A leaked marker would gate
        future rebuild attempts until the stale-inflight safety net fires
        (default 120s)."""
        cache_key = (str(self.root.resolve()), "project")

        # Success path.
        self._seed_stale_graph()
        p1, p2 = self._with_fake_rebuild()
        with p1, p2:
            diag = self.mod._ensure_graph_builder_current(self.root, "project")
        self.assertEqual(diag["code"], "graph_auto_rebuilt")
        with self.mod._VERSION_REBUILD_INFLIGHT_LOCK:
            self.assertNotIn(cache_key, self.mod._VERSION_REBUILD_INFLIGHT,
                             "in-flight marker should be cleared after a successful rebuild")

        # Failure path: reset state-file version so the mismatch fires again,
        # and fake build_index to raise so the except branch runs.
        graph_state = self.root / ".wavefoundry" / "index" / "graph" / "project-graph-state.json"
        graph_state.write_text(json.dumps({"builder_version": "0"}), encoding="utf-8")
        # Bust the in-process verification cache so the rebuild fires again.
        with self.mod._VERSION_CHECK_LOCK:
            self.mod._VERSION_CHECK_CACHE.clear()
        from unittest.mock import patch

        class _FakeLoader:
            def exec_module(self, module):
                def _raise(*a, **k):
                    raise RuntimeError("simulated build_index failure")
                module.build_index = _raise

        class _FakeSpec:
            name = "indexer_for_graph_query_rebuild"
            loader = _FakeLoader()

        real_spec = importlib.util.spec_from_file_location
        real_module = importlib.util.module_from_spec

        def _fake_spec(name, path):
            if name == "indexer_for_graph_query_rebuild":
                return _FakeSpec()
            return real_spec(name, path)

        def _fake_module(spec):
            if getattr(spec, "name", "") == "indexer_for_graph_query_rebuild":
                import types
                return types.ModuleType("fake_indexer_for_rebuild")
            return real_module(spec)

        with patch("importlib.util.spec_from_file_location", _fake_spec), \
             patch("importlib.util.module_from_spec", _fake_module):
            diag = self.mod._ensure_graph_builder_current(self.root, "project")
        self.assertEqual(diag["code"], "graph_auto_rebuild_failed")
        with self.mod._VERSION_REBUILD_INFLIGHT_LOCK:
            self.assertNotIn(cache_key, self.mod._VERSION_REBUILD_INFLIGHT,
                             "in-flight marker should be cleared after a failed rebuild too")


class ConstantQueryMustFixTests(unittest.TestCase):
    """Wave 1p4ls council must-fixes on the query layer: kind-aware resolve, reads opt-in +
    neighbor bound, and the lock keeping `reads` out of the impact/call default relation sets."""

    def setUp(self):
        self.mod = load_graph_query()

    def _idx(self, nodes, edges):
        return self.mod.GraphQueryIndex({"present": True, "layer": "project", "nodes": nodes, "edges": edges})

    def test_resolve_symbol_prefers_callable_over_constant(self):
        """A constant sharing a simple name must NOT shadow a function lookup (kind-aware tiebreak)."""
        idx = self._idx([
            {"id": "f.py::HANDLER", "label": "HANDLER", "kind": "function"},
            {"id": "g.py::HANDLER", "label": "HANDLER", "kind": "constant"},
        ], [])
        self.assertEqual(idx.resolve_symbol("HANDLER"), "f.py::HANDLER")

    def test_one_hop_reads_opt_in(self):
        """`reads` is excluded from default 1-hop traversal (hot-constant guard) but included when
        the caller passes it explicitly."""
        nodes = [
            {"id": "m.py::reader", "label": "reader", "kind": "function"},
            {"id": "m.py::CONST", "label": "CONST", "kind": "constant"},
        ]
        edges = [{"source": "m.py::reader", "target": "m.py::CONST", "relation": "reads", "confidence": "EXTRACTED"}]
        idx = self._idx(nodes, edges)
        default = idx.one_hop_neighbors(["m.py::CONST"])
        self.assertEqual([e for e in default["edges"] if e["relation"] == "reads"], [])
        explicit = idx.one_hop_neighbors(["m.py::CONST"], relations=["reads"])
        self.assertTrue([e for e in explicit["edges"] if e["relation"] == "reads"])

    def test_one_hop_max_neighbors_bound(self):
        """A degree bound caps the neighbor set for a hot node + flags truncation."""
        nodes = [{"id": "m.py::CONST", "label": "CONST", "kind": "constant"}]
        edges = []
        for i in range(10):
            nodes.append({"id": f"m.py::rd{i}", "label": f"rd{i}", "kind": "function"})
            edges.append({"source": f"m.py::rd{i}", "target": "m.py::CONST", "relation": "calls", "confidence": "EXTRACTED"})
        bounded = self._idx(nodes, edges).one_hop_neighbors(["m.py::CONST"], max_neighbors=4)
        self.assertLessEqual(len(bounded["nodes"]), 4)
        self.assertTrue(bounded.get("truncated"))

    def test_reads_stays_out_of_default_relation_sets(self):
        """Guard AC (locks the deferral): `reads` never pollutes impact/blast-radius or call graphs."""
        self.assertNotIn("reads", self.mod._DEFAULT_IMPACT_RELATIONS)
        self.assertNotIn("reads", self.mod._DEFAULT_CALL_RELATIONS)


if __name__ == "__main__":
    unittest.main()
