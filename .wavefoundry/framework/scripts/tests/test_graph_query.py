"""Tests for graph_query.py — load, traversal, and report helpers."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import math
import os
import re
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]


def load_graph_query():
    # graph_query.py does `import cli_stdio` (a sibling module) at load time;
    # make the scripts root importable regardless of which test file ran
    # first instead of depending on suite ordering.
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    sys.modules.pop("graph_query", None)
    spec = importlib.util.spec_from_file_location("graph_query", SCRIPTS / "graph_query.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _write_graph(root: Path, layer: str, payload: dict) -> None:
    # Wave 1p4ww: single project graph.
    graph_dir = root / ".wavefoundry" / "index" / "graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / "project-graph.json").write_text(json.dumps(payload), encoding="utf-8")


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

    def test_load_graph_rejects_non_project_layer(self):
        # Wave 1p4ww: only the project graph exists; framework/union are removed.
        with self.assertRaises(ValueError):
            self.mod.load_graph(self.root, layer="framework")
        self.assertFalse(hasattr(self.mod, "load_union"))


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
        outcome from field validation on wave 131bt 1319v."""
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
        # Wave 1p5l4: composite v2 ranks on confidence-weighted inputs.
        self.assertEqual(out["score_formula"], "risk = weighted_affected_file_count * log1p(weighted_fan_in)")
        self.assertEqual(out["score_components"], [
            "weighted_affected_file_count", "weighted_fan_in", "fan_out",
            "affected_file_count", "fan_in", "extracted_edge_fraction",
            "transitive_extracted_fraction",
        ])
        results = out["results"]
        # Descending by risk; hub (high fan_in + blast radius) is the top risk.
        risks = [r["risk"] for r in results]
        self.assertEqual(risks, sorted(risks, reverse=True))
        self.assertEqual(results[0]["label"], "hub")
        # The composite holds exactly for every entry (math, not hardcoded afc).
        for r in results:
            self.assertAlmostEqual(
                r["risk"],
                r["weighted_affected_file_count"] * math.log1p(r["weighted_fan_in"]),
                places=9,
            )
        # This fixture is all RECEIVER_RESOLVED → weighted == raw, no discount.
        for r in results:
            self.assertEqual(r["weighted_affected_file_count"], r["affected_file_count"])
            self.assertEqual(r["weighted_fan_in"], r["fan_in"])
            self.assertEqual(r["extracted_edge_fraction"], 0.0)

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


# Wave 1p5l4: confidence-weighted blast radius / risk. Mirrors the field
# reproducer — a ubiquitous accessor name (`getKey`) collects 2 real
# RECEIVER_RESOLVED callers + 6 EXTRACTED name-collision in-edges from unrelated
# files (Map.Entry.getKey()), while a genuinely load-bearing symbol (`realCore`)
# has 4 type-resolved callers. Under v1 (every edge weighted equally) the
# accessor's raw blast radius (8) tops the rank; under v2 the EXTRACTED edges are
# down-weighted so the resolved symbol wins.
_COLLISION_FIXTURE = {
    "present": True,
    "layer": "project",
    "nodes": [
        {"id": "src/token.py::getKey", "label": "getKey", "kind": "method", "source_file": "src/token.py"},
        {"id": "src/core.py::realCore", "label": "realCore", "kind": "function", "source_file": "src/core.py"},
        {"id": "src/auth1.py::a1", "label": "a1", "kind": "function", "source_file": "src/auth1.py"},
        {"id": "src/auth2.py::a2", "label": "a2", "kind": "function", "source_file": "src/auth2.py"},
        {"id": "src/u1.py::e1", "label": "e1", "kind": "function", "source_file": "src/u1.py"},
        {"id": "src/u2.py::e2", "label": "e2", "kind": "function", "source_file": "src/u2.py"},
        {"id": "src/u3.py::e3", "label": "e3", "kind": "function", "source_file": "src/u3.py"},
        {"id": "src/u4.py::e4", "label": "e4", "kind": "function", "source_file": "src/u4.py"},
        {"id": "src/u5.py::e5", "label": "e5", "kind": "function", "source_file": "src/u5.py"},
        {"id": "src/u6.py::e6", "label": "e6", "kind": "function", "source_file": "src/u6.py"},
        {"id": "src/r1.py::c1", "label": "c1", "kind": "function", "source_file": "src/r1.py"},
        {"id": "src/r2.py::c2", "label": "c2", "kind": "function", "source_file": "src/r2.py"},
        {"id": "src/r3.py::c3", "label": "c3", "kind": "function", "source_file": "src/r3.py"},
        {"id": "src/r4.py::c4", "label": "c4", "kind": "function", "source_file": "src/r4.py"},
    ],
    "edges": [
        # getKey: 2 real (RECEIVER_RESOLVED) + 6 name-collision (EXTRACTED).
        {"source": "src/auth1.py::a1", "target": "src/token.py::getKey", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
        {"source": "src/auth2.py::a2", "target": "src/token.py::getKey", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
        {"source": "src/u1.py::e1", "target": "src/token.py::getKey", "relation": "calls", "confidence": "EXTRACTED"},
        {"source": "src/u2.py::e2", "target": "src/token.py::getKey", "relation": "calls", "confidence": "EXTRACTED"},
        {"source": "src/u3.py::e3", "target": "src/token.py::getKey", "relation": "calls", "confidence": "EXTRACTED"},
        {"source": "src/u4.py::e4", "target": "src/token.py::getKey", "relation": "calls", "confidence": "EXTRACTED"},
        {"source": "src/u5.py::e5", "target": "src/token.py::getKey", "relation": "calls", "confidence": "EXTRACTED"},
        {"source": "src/u6.py::e6", "target": "src/token.py::getKey", "relation": "calls", "confidence": "EXTRACTED"},
        # realCore: 4 type-resolved callers across distinct files.
        {"source": "src/r1.py::c1", "target": "src/core.py::realCore", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
        {"source": "src/r2.py::c2", "target": "src/core.py::realCore", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
        {"source": "src/r3.py::c3", "target": "src/core.py::realCore", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
        {"source": "src/r4.py::c4", "target": "src/core.py::realCore", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
    ],
}


class GraphQueryConfidenceWeightedRiskTests(unittest.TestCase):
    """Wave 1p5l4: EXTRACTED name-collision edges must not top the risk rank."""

    def setUp(self):
        self.mod = load_graph_query()
        self.index = self.mod.GraphQueryIndex(dict(_COLLISION_FIXTURE))

    def _by_label(self, results):
        return {r["label"]: r for r in results}

    def test_resolved_symbol_outranks_collision_accessor(self):
        by = self._by_label(self.index.risk_score("src/")["results"])
        getkey, core = by["getKey"], by["realCore"]
        # The RAW signal (v1) would have inverted the rank: the accessor's raw
        # blast radius is larger purely from name-collision EXTRACTED edges.
        self.assertGreater(getkey["affected_file_count"], core["affected_file_count"])
        # v2: weighting flips it — the type-resolved symbol is the real risk.
        self.assertGreater(core["risk"], getkey["risk"])

    def test_extracted_edge_fraction_surfaced(self):
        by = self._by_label(self.index.risk_score("src/")["results"])
        # getKey: 6 of 8 blast-radius edges are heuristic → discountable.
        self.assertAlmostEqual(by["getKey"]["extracted_edge_fraction"], 0.75, places=3)
        # realCore: all type-resolved → nothing to discount.
        self.assertEqual(by["realCore"]["extracted_edge_fraction"], 0.0)

    def test_weighted_components_down_weight_extracted(self):
        by = self._by_label(self.index.risk_score("src/")["results"])
        getkey = by["getKey"]
        # 2 resolved (1.0) + 6 extracted (0.25) = 3.5 on both axes.
        self.assertAlmostEqual(getkey["weighted_affected_file_count"], 3.5, places=3)
        self.assertAlmostEqual(getkey["weighted_fan_in"], 3.5, places=3)
        # Raw counts preserved for transparency.
        self.assertEqual(getkey["affected_file_count"], 8)
        self.assertEqual(getkey["fan_in"], 8)

    def test_graph_impact_reports_confidence_counts(self):
        impact = self.index.graph_impact("src/token.py::getKey")
        self.assertEqual(impact["confidence_counts"],
                         {"receiver_resolved": 2, "construction_resolved": 0, "extracted": 6})
        # Each affected node carries its max reaching-edge confidence weight.
        weights = {a["node_id"]: a["confidence_weight"] for a in impact["affected"]}
        self.assertEqual(weights["src/auth1.py::a1"], 1.0)
        self.assertEqual(weights["src/u1.py::e1"], self.mod._EXTRACTED_EDGE_WEIGHT)


# Wave 1p7df: transitive confidence propagation. Blast-radius weight is the
# confidence of the BEST path back to the changed symbol, not just the immediate
# entering edge — so an EXTRACTED hop discounts everything reached *through* it.
_TRANSITIVE_FIXTURE = {
    "present": True,
    "layer": "project",
    "nodes": [
        {"id": "src/s.py::seed", "label": "seed", "kind": "function", "source_file": "src/s.py"},
        {"id": "src/a.py::a", "label": "a", "kind": "function", "source_file": "src/a.py"},
        {"id": "src/x.py::x", "label": "x", "kind": "function", "source_file": "src/x.py"},
        {"id": "src/b.py::b", "label": "b", "kind": "function", "source_file": "src/b.py"},
        {"id": "src/c.py::c", "label": "c", "kind": "function", "source_file": "src/c.py"},
        {"id": "src/d.py::d", "label": "d", "kind": "function", "source_file": "src/d.py"},
        {"id": "src/m.py::m", "label": "m", "kind": "function", "source_file": "src/m.py"},
    ],
    "edges": [
        # 1-hop: a resolved, x extracted.
        {"source": "src/a.py::a", "target": "src/s.py::seed", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
        {"source": "src/x.py::x", "target": "src/s.py::seed", "relation": "calls", "confidence": "EXTRACTED"},
        # 2-hop: b via resolved -> resolved (stays 1.0 — no regression).
        {"source": "src/b.py::b", "target": "src/a.py::a", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
        # 2-hop: c's own edge to a is EXTRACTED -> 0.25.
        {"source": "src/c.py::c", "target": "src/a.py::a", "relation": "calls", "confidence": "EXTRACTED"},
        # 2-hop: d's own edge is RESOLVED but it only reaches seed THROUGH x's
        # EXTRACTED hop -> the discount must propagate (was a full-weight leak).
        {"source": "src/d.py::d", "target": "src/x.py::x", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
        # m reachable via a (resolved path, 1.0) AND via x (0.25) -> best wins.
        {"source": "src/m.py::m", "target": "src/a.py::a", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
        {"source": "src/m.py::m", "target": "src/x.py::x", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
    ],
}


class GraphImpactTransitiveConfidenceTests(unittest.TestCase):
    """Wave 1p7df: confidence propagates along the whole path, not just hop 1."""

    def setUp(self):
        self.mod = load_graph_query()
        self.index = self.mod.GraphQueryIndex(dict(_TRANSITIVE_FIXTURE))

    def _weights(self):
        impact = self.index.graph_impact("src/s.py::seed", max_hops=4)
        return {a["node_id"]: a["confidence_weight"] for a in impact["affected"]}

    def test_single_hop_weights_preserved(self):
        # min-combine reproduces the prior single-hop semantics exactly.
        w = self._weights()
        self.assertEqual(w["src/a.py::a"], 1.0)
        self.assertEqual(w["src/x.py::x"], self.mod._EXTRACTED_EDGE_WEIGHT)

    def test_resolved_path_keeps_full_weight(self):
        # b reached via resolved -> resolved: no discount (no regression).
        self.assertEqual(self._weights()["src/b.py::b"], 1.0)

    def test_extracted_own_hop_discounts(self):
        self.assertEqual(self._weights()["src/c.py::c"], self.mod._EXTRACTED_EDGE_WEIGHT)

    def test_extracted_discount_propagates_transitively(self):
        # d reaches seed only through x's EXTRACTED hop; the discount must carry
        # through even though d's own edge to x is RECEIVER_RESOLVED. Under the
        # old immediate-hop weighting this leaked as a full-weight 1.0.
        self.assertEqual(self._weights()["src/d.py::d"], self.mod._EXTRACTED_EDGE_WEIGHT)

    def test_best_path_wins_for_multi_path_node(self):
        # m is reachable via a resolved path (1.0) and via x (0.25): best wins.
        self.assertEqual(self._weights()["src/m.py::m"], 1.0)

    def test_risk_score_surfaces_transitive_extracted_fraction(self):
        res = self.index.risk_score("src/s.py")["results"]
        seed = next(r for r in res if r["label"] == "seed")
        self.assertIn("transitive_extracted_fraction", seed)
        # x, c, d are reached via an EXTRACTED path -> non-zero fraction.
        self.assertGreater(seed["transitive_extracted_fraction"], 0.0)


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
        Field validation: a construction edge would tie with an
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


class GraphQueryBetweennessRetirementTests(unittest.TestCase):
    """Wave 1p9q3 (1p9q1): the per-query betweenness computation is retired.

    Betweenness is computed at build time (graph_cluster.compute_betweenness_ranking)
    and persisted in the clusters artifact; GraphQueryIndex.report never computes
    it and the 10k-node cap constant no longer exists anywhere.
    """

    def setUp(self):
        self.mod = load_graph_query()
        self.index = self.mod.GraphQueryIndex(FIXTURE_GRAPH | {"present": True})

    def test_report_does_not_serve_betweenness_section(self):
        # AC-5: requesting the old section name from the query index yields no
        # betweenness key — the section is served from the persisted artifact by
        # wf_graph_report, never computed here.
        result = self.index.report(sections=["betweenness"])
        self.assertNotIn("betweenness", result)

    def test_report_never_calls_igraph_betweenness(self):
        # AC-5 instrumentation: even with an igraph module visible, report()
        # must not construct a graph or call betweenness at query time.
        import unittest.mock

        class _ExplodingGraph:
            def __init__(self, *args, **kwargs):
                raise AssertionError("query-time igraph.Graph construction is retired")

        fake_igraph = types.SimpleNamespace(Graph=_ExplodingGraph)
        with unittest.mock.patch.dict(sys.modules, {"igraph": fake_igraph}):
            result = self.index.report(
                sections=["fan_in", "fan_out", "orphan_docs", "chokepoints", "file_hubs", "betweenness"]
            )
        self.assertNotIn("betweenness", result)
        self.assertIn("fan_in", result)

    def test_cap_constant_retired_module_attr(self):
        # The retired cap constant must not resurface on the module.
        self.assertFalse(hasattr(self.mod, "_BETWEENNESS_NODE_LIMIT"))

    def test_cap_constant_retired_grep_gate(self):
        # AC-5 grep gate: `_BETWEENNESS_NODE_LIMIT` no longer exists anywhere in
        # framework scripts (this test file is the only allowed mention).
        offenders: list[str] = []
        for path in SCRIPTS.rglob("*.py"):
            if path == Path(__file__).resolve():
                continue
            if "_BETWEENNESS_NODE_LIMIT" in path.read_text(encoding="utf-8", errors="replace"):
                offenders.append(str(path))
        self.assertEqual(offenders, [], f"retired constant still referenced: {offenders}")


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
    """Wave 1p2q3 (1p2q4): field reproducer for spurious 2-hop paths via shared
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

    def test_field_reproducer_calls_chain_beats_external_bridge(self):
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

    def _with_noisy_rebuild(self):
        """Like _with_fake_rebuild, but the faked build_index deliberately writes to sys.stdout —
        simulating any unconditional progress print inside the real build_index. Used to prove the
        boundary wrapper (isolated_stdout_fd + redirect_stdout) keeps those bytes off the JSON-RPC
        stdout channel."""
        from unittest.mock import patch
        self.mod._get_graph_indexer()
        real_spec = importlib.util.spec_from_file_location
        real_module = importlib.util.module_from_spec

        class _NoisyLoader:
            def exec_module(self, module):
                def _noisy_build_index(*a, **k):
                    print("build_index: NOISE that would corrupt the JSON-RPC frame")
                    return {"ok": True}
                module.build_index = _noisy_build_index

        class _NoisySpec:
            name = "indexer_for_graph_query_rebuild"
            loader = _NoisyLoader()

        def _fake_spec(name, path):
            if name == "indexer_for_graph_query_rebuild":
                return _NoisySpec()
            return real_spec(name, path)

        def _fake_module(spec):
            if getattr(spec, "name", "") == "indexer_for_graph_query_rebuild":
                import types
                return types.ModuleType("fake_indexer_for_rebuild")
            return real_module(spec)

        return patch("importlib.util.spec_from_file_location", _fake_spec), \
               patch("importlib.util.module_from_spec", _fake_module)

    def test_auto_rebuild_writes_no_bytes_to_stdout(self):
        """Wave 1p9io AC-7: the in-process graph auto-rebuild must not write to sys.stdout — that is the
        MCP stdio JSON-RPC channel on the server. A build_index that prints to stdout must have its
        output redirected to stderr by the boundary wrapper (isolated_stdout_fd + redirect_stdout), so
        the captured stdout is empty. Regression guard: removing the wrapper would land the noise on
        stdout and fail this test."""
        self._seed_stale_graph()
        p1, p2 = self._with_noisy_rebuild()
        captured = io.StringIO()
        with p1, p2, contextlib.redirect_stdout(captured):
            diag = self.mod._ensure_graph_builder_current(self.root, "project")
        self.assertIsNotNone(diag)
        self.assertEqual(diag["code"], "graph_auto_rebuilt")
        self.assertEqual(
            captured.getvalue(), "",
            "graph auto-rebuild wrote to sys.stdout — this would corrupt the MCP JSON-RPC frame on the "
            "stdio transport. The build_index call must be wrapped in isolated_stdout_fd()/redirect_stdout.",
        )

    def test_concurrent_auto_rebuild_defers_via_inflight_marker(self):
        """Wave 1p2q3 (1p2w5 / Bug 3): a second `_ensure_graph_builder_current`
        call that arrives while another rebuild is in-flight must defer with
        a `graph_auto_rebuild_in_progress` diagnostic instead of racing for
        the index-build flock. Reproduces the noisy
        `graph_auto_rebuild_failed` spam observed in the field during the v22→v23
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
        self.assertEqual(diag["recovery_tools"], ["index_build_status"])

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


class GraphQueryIndexCacheTests(unittest.TestCase):
    """Wave 1p9q3 (1p9pz): process-level cache of the constructed GraphQueryIndex.

    Covers AC-1 (hit/reuse via loader call-count), AC-2 (invalidation matrix:
    stat change, rebuild-triggered explicit invalidation, same-stat pathological
    rewrite), AC-3 (cached vs kill-switch output equivalence per tool family),
    AC-4 (concurrency: no half-constructed index, no double-build), and the
    AC-5 repeated-query immutability guard on one cached instance.
    """

    KILL_SWITCH = "WAVEFOUNDRY_DISABLE_GRAPH_QUERY_CACHE"

    def setUp(self):
        self.mod = load_graph_query()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.indexer = self.mod._get_graph_indexer()
        # Version-current fixture: the accessor never PINS a payload whose
        # builder_version differs from the runtime constant (old-code-window
        # hardening), so cache-mechanics tests must serve a current payload.
        self.fixture = json.loads(json.dumps(FIXTURE_GRAPH))
        self.fixture["builder_version"] = str(self.indexer.GRAPH_BUILDER_VERSION)
        _write_graph(self.root, "project", self.fixture)
        # Instrument the loader: count every full payload parse (both the
        # cached accessor's miss path and the kill-switch/from_root path go
        # through read_graph_payload on the lazily-loaded indexer module).
        self.load_calls: list[tuple[str, str]] = []
        real_read = self.indexer.read_graph_payload

        def counting_read(root, layer="project"):
            self.load_calls.append((str(root), layer))
            return real_read(root, layer)

        self.indexer.read_graph_payload = counting_read

    def tearDown(self):
        self.tmp.cleanup()

    def _graph_path(self) -> Path:
        return self.root / ".wavefoundry" / "index" / "graph" / "project-graph.json"

    def _seed_state(self, builder_version: str) -> None:
        state_path = self._graph_path().with_name("project-graph-state.json")
        state_path.write_text(json.dumps({"builder_version": builder_version}), encoding="utf-8")

    # ---- AC-1: hit/reuse ----

    def test_cache_hit_parses_payload_once_and_reuses_index(self):
        i1 = self.mod.get_query_index(self.root)
        i2 = self.mod.get_query_index(self.root)
        self.assertEqual(len(self.load_calls), 1)
        self.assertIs(i1, i2)
        self.assertEqual(len(i1._node_by_id), 5)

    def test_kill_switch_restores_load_per_call(self):
        from unittest.mock import patch
        with patch.dict(os.environ, {self.KILL_SWITCH: "1"}):
            i1 = self.mod.get_query_index(self.root)
            i2 = self.mod.get_query_index(self.root)
        self.assertEqual(len(self.load_calls), 2)
        self.assertIsNot(i1, i2)

    def test_stale_builder_version_payload_is_never_pinned(self):
        # Old-code-window hardening: a stale pre-upgrade process can rewrite
        # the payload with an older builder_version while the store meta the
        # version check probes still reads current. Such a payload is served
        # (graceful) but never cached — every access reloads until a build
        # heals it.
        stale = json.loads(json.dumps(self.fixture))
        stale["builder_version"] = "1"  # != runtime GRAPH_BUILDER_VERSION
        _write_graph(self.root, "project", stale)
        i1 = self.mod.get_query_index(self.root)
        i2 = self.mod.get_query_index(self.root)
        self.assertEqual(len(self.load_calls), 2, "stale-version payload must not be pinned")
        self.assertIsNot(i1, i2)
        # A current payload re-enables pinning.
        _write_graph(self.root, "project", self.fixture)
        i3 = self.mod.get_query_index(self.root)
        i4 = self.mod.get_query_index(self.root)
        self.assertIs(i3, i4)

    def test_rejects_non_project_layer(self):
        with self.assertRaises(ValueError):
            self.mod.get_query_index(self.root, layer="framework")

    # ---- AC-2: invalidation matrix ----

    def test_stat_change_reloads_and_reflects_new_graph(self):
        self.mod.get_query_index(self.root)
        new_graph = json.loads(json.dumps(self.fixture))
        new_graph["nodes"].append(
            {"id": "src/c.py::baz", "label": "baz", "kind": "function", "source_file": "src/c.py", "layer": "project"})
        _write_graph(self.root, "project", new_graph)  # different size → different stat
        idx = self.mod.get_query_index(self.root)
        self.assertEqual(len(self.load_calls), 2)
        self.assertIsNotNone(idx.get_node("src/c.py::baz"))

    def test_same_stat_rewrite_requires_explicit_invalidation(self):
        i1 = self.mod.get_query_index(self.root)
        # Pathological rewrite: same byte length, forced-identical mtime_ns.
        graph_path = self._graph_path()
        st = graph_path.stat()
        same_size = json.loads(json.dumps(self.fixture))
        same_size["nodes"][3]["label"] = "baz"  # "bar" → "baz": same length
        data = json.dumps(same_size)
        self.assertEqual(len(data.encode("utf-8")), st.st_size)
        graph_path.write_text(data, encoding="utf-8")
        os.utime(graph_path, ns=(st.st_atime_ns, st.st_mtime_ns))
        # Stat validation alone cannot see this rewrite — cache still serves old.
        i2 = self.mod.get_query_index(self.root)
        self.assertIs(i1, i2)
        # The explicit hook (called by every known-rebuild path) forces reload.
        self.mod.invalidate_query_index_cache(self.root)
        i3 = self.mod.get_query_index(self.root)
        self.assertIsNot(i1, i3)
        self.assertEqual((i3.get_node("src/b.py::bar") or {}).get("label"), "baz")
        # Loads: initial construction + post-invalidation reload (the same-stat
        # hit in between served the cache without loading).
        self.assertEqual(len(self.load_calls), 2)

    def _with_fake_rebuild(self):
        """Patch the auto-rebuild indexer load with a no-op build (mirrors
        GraphQueryAutoRebuildCallbackTests._with_fake_rebuild)."""
        from unittest.mock import patch
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

    def test_rebuild_triggered_invalidation_reloads_despite_equal_stats(self):
        runtime = str(getattr(self.indexer, "GRAPH_BUILDER_VERSION", "") or "")
        self._seed_state(runtime)
        i1 = self.mod.get_query_index(self.root)
        self.assertEqual(len(self.load_calls), 1)
        # Simulate a builder-version bump observed at query time: stale state
        # on disk, fresh runtime (version-check cache cleared as a process
        # restart would). Payload stats are UNCHANGED — only the explicit
        # in-process invalidation (plus the rebuild-ran bypass) can reload.
        self._seed_state("0")
        with self.mod._VERSION_CHECK_LOCK:
            self.mod._VERSION_CHECK_CACHE.clear()
        p1, p2 = self._with_fake_rebuild()
        with p1, p2:
            i2 = self.mod.get_query_index(self.root)
        self.assertEqual((i2.auto_rebuild_diagnostic or {}).get("code"), "graph_auto_rebuilt")
        self.assertEqual(len(self.load_calls), 2)
        self.assertIsNot(i1, i2)
        # Next call: version verified, stats stable → hit, no diagnostic replay.
        i3 = self.mod.get_query_index(self.root)
        self.assertIsNone(i3.auto_rebuild_diagnostic)
        self.assertEqual(len(self.load_calls), 2)

    # ---- AC-3: cached vs kill-switch equivalence per tool family ----

    def test_cached_and_uncached_results_identical_per_tool_family(self):
        from unittest.mock import patch
        cached = self.mod.get_query_index(self.root)
        with patch.dict(os.environ, {self.KILL_SWITCH: "1"}):
            fresh = self.mod.get_query_index(self.root)
        self.assertIsNot(cached, fresh)

        def _families(idx):
            return {
                # path family (code_graph_path)
                "path": idx.shortest_path("foo", "bar"),
                # impact family (code_impact / code_risk_score)
                "impact": idx.graph_impact("bar"),
                "risk": idx.risk_score("src/"),
                # callgraph/hierarchy family (code_callgraph / code_callhierarchy)
                "callgraph": idx.callgraph("foo", depth=2, direction="both"),
                # dependencies/references family (1-hop in/out adjacency)
                "one_hop": idx.one_hop_neighbors(["src/a.py::foo", "src/b.py"]),
                "in_degrees": {n: len(idx._in.get(n, [])) for n in sorted(idx._node_by_id)},
                "out_degrees": {n: len(idx._out.get(n, [])) for n in sorted(idx._node_by_id)},
                # community family reads nodes + degrees (code_graph_community)
                "node": idx.get_node("src/a.py::foo"),
                # report family (wf_graph_report)
                "report": idx.report(limit=10),
            }

        first = _families(cached)
        self.assertEqual(first, _families(fresh))
        # Repeated queries against the SAME cached instance stay identical —
        # locks the immutability contract the cache depends on (AC-5 guard).
        self.assertEqual(first, _families(cached))

    def test_queries_do_not_mutate_cached_structures(self):
        idx = self.mod.get_query_index(self.root)
        snapshot = lambda: (  # noqa: E731
            json.dumps(idx.nodes, sort_keys=True),
            json.dumps(idx.edges, sort_keys=True),
            {k: len(v) for k, v in idx._out.items()},
            {k: len(v) for k, v in idx._in.items()},
            sorted(idx._node_by_id),
        )
        before = snapshot()
        idx.resolve_symbol("bar")
        idx.traverse("src/a.py::foo", max_hops=3, direction="both")
        idx.one_hop_neighbors(["src/a.py::foo"])
        idx.shortest_path("foo", "bar", direction="either")
        idx.graph_impact("bar")
        idx.risk_score("src/")
        idx.callgraph("foo", depth=2, direction="both")
        idx.report(limit=10)
        self.assertEqual(before, snapshot())

    # ---- AC-4: concurrency ----

    def test_concurrent_access_during_construction_is_safe(self):
        entered = threading.Event()
        release = threading.Event()
        real_read = self.indexer.read_graph_payload

        def slow_read(root, layer="project"):
            entered.set()
            release.wait(timeout=10)
            return real_read(root, layer)

        self.indexer.read_graph_payload = slow_read
        results: dict[str, object] = {}
        errors: list[BaseException] = []

        def worker(key):
            try:
                results[key] = self.mod.get_query_index(self.root)
            except BaseException as exc:  # pragma: no cover - failure surface
                errors.append(exc)

        t1 = threading.Thread(target=worker, args=("a",))
        t2 = threading.Thread(target=worker, args=("b",))
        t1.start()
        self.assertTrue(entered.wait(timeout=10))  # t1 is inside construction
        t2.start()                                  # t2 blocks on the cache lock
        time.sleep(0.05)                            # let t2 reach the lock
        release.set()
        t1.join(timeout=10)
        t2.join(timeout=10)
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        # Both threads got a FULLY constructed index — never a partial read.
        for idx in results.values():
            self.assertEqual(len(idx._node_by_id), 5)
            self.assertEqual(len(idx.edges), 3)
        # Construction ran once; the second thread reused the fresh entry.
        self.assertIs(results["a"], results["b"])


class ServerImplGraphAccessorGateTests(unittest.TestCase):
    """Wave 1p9q3 (1p9pz) AC-6 grep gate: every GraphQueryIndex construction in
    server_impl.py routes through the cached accessor; no direct fresh-parse
    site remains outside graph_query's accessor/kill-switch path."""

    def test_no_direct_from_root_sites_in_server_impl(self):
        src = (SCRIPTS / "server_impl.py").read_text(encoding="utf-8")
        self.assertNotIn("GraphQueryIndex.from_root", src)
        self.assertIn("get_query_index(", src)

    def test_direct_constructions_are_transform_payloads_only(self):
        # Direct GraphQueryIndex(...) calls are allowed ONLY over locally
        # transformed in-memory payloads (collapse views) — never a fresh
        # parse of the on-disk artifact.
        src = (SCRIPTS / "server_impl.py").read_text(encoding="utf-8")
        direct = re.findall(r"GraphQueryIndex\((\w+)", src)
        self.assertEqual(
            sorted(set(direct)),
            ["collapsed_payload", "directory_payload", "merged_payload"],
        )


def _inh_node(nid: str, kind: str, label: str | None = None, **extra) -> dict:
    return {
        "id": nid,
        "label": label or nid.rsplit(".", 1)[-1],
        "kind": kind,
        "source_file": nid.split("::")[0],
        "layer": "project",
        **extra,
    }


# Wave 1p9qh (1p9qa): interface + implementation + caller fixture for
# dispatch-aware impact and path cost-tier tests.
_INHERITANCE_FIXTURE = {
    "present": True,
    "layer": "project",
    "nodes": [
        _inh_node("i.java::IUserService", "class", "IUserService", declared_kind="interface"),
        _inh_node("i.java::IUserService.find", "function", "find"),
        _inh_node("impl.java::UserServiceImpl", "class", "UserServiceImpl"),
        _inh_node("impl.java::UserServiceImpl.find", "function", "find"),
        _inh_node("mid.java::MidService", "class", "MidService"),
        _inh_node("mid.java::MidService.find", "function", "find"),
        _inh_node("c.java::Controller", "class", "Controller"),
        _inh_node("c.java::Controller.handle", "function", "handle"),
    ],
    "edges": [
        {"source": "impl.java::UserServiceImpl", "target": "i.java::IUserService", "relation": "implements", "confidence": "RECEIVER_RESOLVED"},
        {"source": "mid.java::MidService", "target": "impl.java::UserServiceImpl", "relation": "extends", "confidence": "RECEIVER_RESOLVED"},
        {"source": "c.java::Controller.handle", "target": "i.java::IUserService.find", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
    ],
}


class DispatchAwareImpactTests(unittest.TestCase):
    """Wave 1p9qh (1p9qa) AC-4: `code_impact` traverses `implements`/`extends`
    at the documented down-weight and expands a supertype METHOD seed to its
    subtype implementations."""

    def setUp(self):
        self.mod = load_graph_query()
        self.index = self.mod.GraphQueryIndex(
            {k: (list(v) if isinstance(v, list) else v) for k, v in _INHERITANCE_FIXTURE.items()}
        )

    def test_default_impact_relations_include_inheritance(self):
        self.assertIn("implements", self.mod._DEFAULT_IMPACT_RELATIONS)
        self.assertIn("extends", self.mod._DEFAULT_IMPACT_RELATIONS)

    def test_interface_method_impact_includes_implementations_down_weighted(self):
        impact = self.index.graph_impact("i.java::IUserService.find", max_hops=3)
        by_id = {a["node_id"]: a for a in impact["affected"]}
        # Direct implementation joins at hop 1 with the dispatch down-weight.
        self.assertIn("impl.java::UserServiceImpl.find", by_id)
        entry = by_id["impl.java::UserServiceImpl.find"]
        self.assertEqual(entry["hop"], 1)
        self.assertEqual(entry["confidence_weight"], self.mod._DISPATCH_EDGE_WEIGHT)
        # Transitive subtype override (MidService extends UserServiceImpl).
        self.assertIn("mid.java::MidService.find", by_id)
        self.assertEqual(
            by_id["mid.java::MidService.find"]["confidence_weight"],
            self.mod._DISPATCH_EDGE_WEIGHT,
        )
        # Real caller keeps full weight.
        self.assertEqual(by_id["c.java::Controller.handle"]["confidence_weight"], 1.0)
        # The synthetic edges are marked so they can't be mistaken for
        # persisted graph edges.
        dispatch_edges = [e for e in impact["edges"] if e.get("derived") == "dispatch"]
        self.assertTrue(dispatch_edges)
        for edge in dispatch_edges:
            self.assertIn(edge.get("relation"), ("implements", "extends"))

    def test_interface_class_impact_includes_subtypes_down_weighted(self):
        impact = self.index.graph_impact("i.java::IUserService", max_hops=3)
        by_id = {a["node_id"]: a for a in impact["affected"]}
        self.assertIn("impl.java::UserServiceImpl", by_id)
        self.assertEqual(
            by_id["impl.java::UserServiceImpl"]["confidence_weight"],
            self.mod._DISPATCH_EDGE_WEIGHT,
        )

    def test_relations_opt_out_excludes_dispatch(self):
        impact = self.index.graph_impact("i.java::IUserService.find", relations=("calls",))
        ids = {a["node_id"] for a in impact["affected"]}
        self.assertNotIn("impl.java::UserServiceImpl.find", ids)
        self.assertIn("c.java::Controller.handle", ids)
        self.assertFalse([e for e in impact["edges"] if e.get("derived") == "dispatch"])

    def test_dispatch_weight_is_extracted_tier(self):
        """The doc'd contract: dispatch is down-weighted LIKE EXTRACTED."""
        self.assertEqual(self.mod._DISPATCH_EDGE_WEIGHT, self.mod._EXTRACTED_EDGE_WEIGHT)
        weight = self.mod._edge_confidence_weight(
            {"relation": "implements", "confidence": "RECEIVER_RESOLVED"}
        )
        self.assertEqual(weight, self.mod._DISPATCH_EDGE_WEIGHT)


class InheritancePathCostTierTests(unittest.TestCase):
    """Wave 1p9qh (1p9qa) AC-4: `code_graph_path` treats inheritance edges as
    structural — a real call chain beats an inheritance shortcut."""

    def setUp(self):
        self.mod = load_graph_query()
        nodes = [
            _inh_node("a.java::Alpha", "class", "Alpha"),
            _inh_node("a.java::Alpha.entry", "function", "entry"),
            _inh_node("b.java::Beta", "class", "Beta"),
            _inh_node("b.java::Beta.step", "function", "step"),
            _inh_node("z.java::Zeta", "class", "Zeta"),
        ]
        edges = [
            # Inheritance shortcut: Alpha.entry's class chain reaches Zeta in 1 hop.
            {"source": "a.java::Alpha.entry", "target": "z.java::Zeta", "relation": "extends", "confidence": "RECEIVER_RESOLVED"},
            # Real call chain: entry -> step -> Zeta (2 hops of calls).
            {"source": "a.java::Alpha.entry", "target": "b.java::Beta.step", "relation": "calls", "confidence": "EXTRACTED"},
            {"source": "b.java::Beta.step", "target": "z.java::Zeta", "relation": "calls", "confidence": "EXTRACTED"},
        ]
        self.index = self.mod.GraphQueryIndex({"present": True, "layer": "project", "nodes": nodes, "edges": edges})

    def test_call_chain_beats_inheritance_shortcut(self):
        result = self.index.shortest_path("a.java::Alpha.entry", "z.java::Zeta")
        self.assertTrue(result["found"])
        relations = [e["relation"] for e in result["path_edges"]]
        self.assertEqual(relations, ["calls", "calls"],
                         f"the 2-hop call chain must beat the 1-hop extends shortcut; got {relations}")

    def test_inheritance_edge_costs_structural_tier(self):
        self.assertEqual(
            self.mod._path_edge_cost({"relation": "extends", "confidence": "RECEIVER_RESOLVED"}),
            self.mod._PATH_COST_STRUCTURAL,
        )
        self.assertEqual(
            self.mod._path_edge_cost({"relation": "implements", "confidence": "EXTRACTED"}),
            self.mod._PATH_COST_STRUCTURAL,
        )


_EXTERNAL_SUPERTYPE_FIXTURE = {
    "schema_version": "1",
    "builder_version": "1",
    "layer": "project",
    "present": True,
    "nodes": [
        {"id": "src/Shop.java", "label": "Shop", "kind": "class", "source_file": "src/Shop.java", "layer": "project"},
        {"id": "src/Sail.java", "label": "Sail", "kind": "class", "source_file": "src/Sail.java", "layer": "project"},
        {"id": "src/Jdbc.java", "label": "Jdbc", "kind": "class", "source_file": "src/Jdbc.java", "layer": "project"},
        {"id": "src/Local.java", "label": "LocalIface", "kind": "class", "source_file": "src/Local.java", "layer": "project"},
        {"id": "src/LocalImpl.java", "label": "LocalImpl", "kind": "class", "source_file": "src/LocalImpl.java", "layer": "project"},
        # Project class whose SIMPLE NAME collides with an external supertype
        # declared elsewhere — project must win resolution (shadowing rule).
        {"id": "src/Node.java", "label": "Node", "kind": "class", "source_file": "src/Node.java", "layer": "project"},
        {"id": "src/UsesShop.java", "label": "UsesShop", "kind": "class", "source_file": "src/UsesShop.java", "layer": "project"},
    ],
    "edges": [
        # Two implementors of ONE external interface (simple-name declaration).
        {"source": "src/Shop.java", "target": "external::TypeInstrumentation", "relation": "implements", "confidence": "EXTRACTED"},
        {"source": "src/Sail.java", "target": "external::TypeInstrumentation", "relation": "implements", "confidence": "EXTRACTED"},
        # extends of an external class, declared FULLY QUALIFIED.
        {"source": "src/Jdbc.java", "target": "external::io.otel.InstrumentationModule", "relation": "extends", "confidence": "EXTRACTED"},
        # A DIFFERENT external supertype sharing the simple name `InstrumentationModule`
        # (declared with a different qualification) — the distinct-id grouping case.
        {"source": "src/Sail.java", "target": "external::com.vendor.InstrumentationModule", "relation": "extends", "confidence": "EXTRACTED"},
        # Project-internal inheritance (control).
        {"source": "src/LocalImpl.java", "target": "src/Local.java", "relation": "implements", "confidence": "RECEIVER_RESOLVED"},
        # A project class implements an external supertype named like a project node.
        {"source": "src/UsesShop.java", "target": "external::Node", "relation": "implements", "confidence": "EXTRACTED"},
        # External CALL target — must NOT become a resolvable supertype.
        {"source": "src/Shop.java", "target": "external::Logger.log", "relation": "calls", "confidence": "EXTRACTED"},
        # Dependent of an implementor (hop-2 blast radius from the interface).
        {"source": "src/UsesShop.java", "target": "src/Shop.java", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
    ],
    "counts": {"files": 7, "nodes": 7, "edges": 8},
}


class ExternalSupertypeVisibilityTests(unittest.TestCase):
    """Wave 1sbfi (1sbfh): external `implements`/`extends` visibility — the
    field-reported blind spot where a class implementing an external interface
    showed zero edges and the external interface resolved to nothing."""

    def setUp(self):
        self.mod = load_graph_query()
        self.index = self.mod.GraphQueryIndex(dict(_EXTERNAL_SUPERTYPE_FIXTURE))

    def test_external_supertype_resolves_by_simple_name(self):
        self.assertEqual(
            self.index.resolve_symbol("TypeInstrumentation"),
            "external::TypeInstrumentation",
        )

    def test_external_supertype_resolves_by_declared_qualified_name(self):
        self.assertEqual(
            self.index.resolve_symbol("io.otel.InstrumentationModule"),
            "external::io.otel.InstrumentationModule",
        )
        self.assertEqual(
            self.index.resolve_symbol("external::io.otel.InstrumentationModule"),
            "external::io.otel.InstrumentationModule",
        )

    def test_project_symbol_shadows_external_supertype(self):
        # `Node` exists as a project class AND as an external supertype name —
        # resolution must return the project node (externals never shadow).
        self.assertEqual(self.index.resolve_symbol("Node"), "src/Node.java")

    def test_distinct_external_ids_sharing_a_simple_name_stay_unmerged(self):
        # Two different external supertypes share the simple name — conservative
        # non-resolution + the grouped breakdown (council amendment).
        self.assertIsNone(self.index.resolve_symbol("InstrumentationModule"))
        groups = self.index.external_supertype_group("InstrumentationModule")
        self.assertEqual(
            [g["id"] for g in groups],
            ["external::com.vendor.InstrumentationModule", "external::io.otel.InstrumentationModule"],
        )
        self.assertEqual({g["subtype_count"] for g in groups}, {1})

    def test_external_call_targets_are_not_supertype_resolvable(self):
        # Only implements/extends targets join the index — external CALL
        # targets stay unresolvable by design.
        self.assertIsNone(self.index.resolve_symbol("Logger.log"))
        self.assertEqual(self.index.external_supertype_matches("Logger.log"), [])

    def test_graph_impact_from_external_interface_returns_implementors(self):
        impact = self.index.graph_impact("TypeInstrumentation", max_hops=2)
        self.assertTrue(impact["resolved"])
        self.assertEqual(impact["node_id"], "external::TypeInstrumentation")
        affected_ids = {a["node_id"] for a in impact["affected"]}
        # Hop 1: both implementors; hop 2: the implementor's dependent.
        self.assertEqual(
            affected_ids, {"src/Shop.java", "src/Sail.java", "src/UsesShop.java"}
        )

    def test_supertype_summary_splits_project_and_external_with_counts(self):
        summary = self.index.supertype_summary("src/Sail.java")
        self.assertEqual(
            [e["id"] for e in summary["external"]],
            ["external::TypeInstrumentation", "external::com.vendor.InstrumentationModule"],
        )
        self.assertEqual(summary["external_implements_count"], 1)
        self.assertEqual(summary["external_extends_count"], 1)
        local = self.index.supertype_summary("src/LocalImpl.java")
        self.assertEqual([e["id"] for e in local["project"]], ["src/Local.java"])
        self.assertEqual(local["external_implements_count"], 0)

    def test_supertype_summary_absent_for_supertype_free_nodes(self):
        self.assertIsNone(self.index.supertype_summary("src/Local.java"))

    def test_report_main_sections_stay_free_of_external_rows(self):
        # Regression pin: external supertype visibility must not leak external
        # rows into the report's main sections.
        report = self.index.report()
        blob = json.dumps(report)
        self.assertNotIn("external::TypeInstrumentation", blob)


if __name__ == "__main__":
    unittest.main()
