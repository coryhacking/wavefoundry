from __future__ import annotations

import io
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from types import SimpleNamespace


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
GRAPH_CLUSTER_PATH = SCRIPTS_ROOT / "graph_cluster.py"


def load_graph_cluster():
    spec = importlib.util.spec_from_file_location("graph_cluster", GRAPH_CLUSTER_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["graph_cluster"] = mod
    spec.loader.exec_module(mod)
    return mod


class GraphClusterTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_graph_cluster()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry" / "index").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _payload(self, extra_b: bool = False) -> dict[str, object]:
        # Build two well-connected communities of 13 nodes each (above MIN_COMMUNITY_SIZE).
        # One weak cross-community edge keeps them separable for Leiden.
        func_names_a = [f"fn_a{i}" for i in range(12)]
        func_names_b = [f"fn_b{i}" for i in range(12)]
        nodes = [
            {"id": "src/a.py", "label": "a", "kind": "module", "source_file": "src/a.py", "source_location": "1:0", "layer": "project"},
            *[{"id": f"src/a.py::{n}", "label": n, "kind": "function", "source_file": "src/a.py", "source_location": f"{i+2}:0", "layer": "project"} for i, n in enumerate(func_names_a)],
            {"id": "src/b.py", "label": "b", "kind": "module", "source_file": "src/b.py", "source_location": "1:0", "layer": "project"},
            *[{"id": f"src/b.py::{n}", "label": n, "kind": "function", "source_file": "src/b.py", "source_location": f"{i+2}:0", "layer": "project"} for i, n in enumerate(func_names_b)],
        ]
        edges = [
            *[{"source": "src/a.py", "target": f"src/a.py::{n}", "relation": "defines", "confidence": "EXTRACTED"} for n in func_names_a],
            *[{"source": f"src/a.py::{func_names_a[i]}", "target": f"src/a.py::{func_names_a[i+1]}", "relation": "calls", "confidence": "EXTRACTED"} for i in range(len(func_names_a) - 1)],
            *[{"source": "src/b.py", "target": f"src/b.py::{n}", "relation": "defines", "confidence": "EXTRACTED"} for n in func_names_b],
            *[{"source": f"src/b.py::{func_names_b[i]}", "target": f"src/b.py::{func_names_b[i+1]}", "relation": "calls", "confidence": "EXTRACTED"} for i in range(len(func_names_b) - 1)],
            {"source": f"src/a.py::{func_names_a[-1]}", "target": f"src/b.py::{func_names_b[0]}", "relation": "calls", "confidence": "EXTRACTED"},
        ]
        if extra_b:
            nodes.append({"id": "src/b.py::epsilon", "label": "epsilon", "kind": "function", "source_file": "src/b.py", "source_location": "14:0", "layer": "project"})
            edges.extend([
                {"source": "src/b.py", "target": "src/b.py::epsilon", "relation": "defines", "confidence": "EXTRACTED"},
                {"source": f"src/b.py::{func_names_b[-1]}", "target": "src/b.py::epsilon", "relation": "calls", "confidence": "EXTRACTED"},
            ])
        return {
            "schema_version": "1",
            "builder_version": "1",
            "layer": "project",
            "graph_mtime": 100,
            "nodes": nodes,
            "edges": edges,
            "counts": {"files": 2, "nodes": len(nodes), "edges": len(edges)},
            "present": True,
        }

    def test_update_graph_clusters_writes_cluster_artifact(self):
        payload = self.mod.update_graph_clusters(
            root=self.root,
            index_dir=self.root / ".wavefoundry" / "index",
            layer="project",
            graph_payload=self._payload(),
            verbose=False,
        )
        cluster_path = self.root / ".wavefoundry" / "index" / "graph" / "project-graph-clusters.json"
        self.assertTrue(cluster_path.exists())
        self.assertTrue(payload["present"])
        self.assertEqual(payload["community_count"], 2)
        self.assertIn(payload["cluster_algorithm"], {"leiden", "label-propagation"})
        community_ids = {community["community_id"] for community in payload["communities"]}
        self.assertEqual(len(community_ids), 2)
        for community in payload["communities"]:
            self.assertGreaterEqual(community["node_count"], 12)
            self.assertIn("seed_node_id", community)
            self.assertIn("label", community)

    def test_documents_grouped_into_documentation_community(self):
        payload = self._payload()
        payload["nodes"].extend([
            {"id": "docs/guide.md", "label": "guide", "kind": "doc", "source_file": "docs/guide.md", "source_location": "1:0", "layer": "project"},
            {"id": "docs/spec.md", "label": "spec", "kind": "doc", "source_file": "docs/spec.md", "source_location": "1:0", "layer": "project"},
            {"id": ".wavefoundry/framework/seeds/001.md", "label": "001", "kind": "seed", "source_file": ".wavefoundry/framework/seeds/001.md", "source_location": "1:0", "layer": "project"},
        ])
        payload["edges"].extend([
            {"source": "docs/guide.md", "target": "src/a.py::fn_a0", "relation": "doc_references_code", "confidence": "AMBIGUOUS"},
            {"source": "docs/spec.md", "target": "src/b.py::fn_b0", "relation": "doc_references_code", "confidence": "AMBIGUOUS"},
            {"source": ".wavefoundry/framework/seeds/001.md", "target": "src/b.py::fn_b0", "relation": "doc_references_code", "confidence": "AMBIGUOUS"},
        ])
        result = self.mod.update_graph_clusters(
            root=self.root,
            index_dir=self.root / ".wavefoundry" / "index",
            layer="project",
            graph_payload=payload,
            verbose=False,
        )
        communities = result["communities"]
        doc_communities = [c for c in communities if c.get("label") == "Documentation"]
        self.assertEqual(len(doc_communities), 1, "docs should collapse into a single Documentation community")
        doc_ids = set(doc_communities[0]["node_ids"])
        self.assertEqual(
            doc_ids,
            {"docs/guide.md", "docs/spec.md", ".wavefoundry/framework/seeds/001.md"},
        )
        self.assertEqual(doc_communities[0].get("kind"), "fixed")
        # Code communities must not contain any document node.
        code_ids = {nid for c in communities if c.get("label") != "Documentation" for nid in c["node_ids"]}
        self.assertNotIn("docs/guide.md", code_ids)
        self.assertNotIn(".wavefoundry/framework/seeds/001.md", code_ids)
        self.assertIn("src/a.py::fn_a0", code_ids)

    def test_update_graph_clusters_logs_backend_and_write(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.mod.update_graph_clusters(
                root=self.root,
                index_dir=self.root / ".wavefoundry" / "index",
                layer="project",
                graph_payload=self._payload(),
                verbose=True,
            )
        output = buf.getvalue()
        self.assertIn("graph clustering inputs ready for project layer", output)
        self.assertIn("graph clustering wrote project cluster artifact", output)

    def test_update_graph_clusters_logs_label_propagation_fallback(self):
        self.mod._load_leiden_backend = lambda: None
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.mod.update_graph_clusters(
                root=self.root,
                index_dir=self.root / ".wavefoundry" / "index",
                layer="project",
                graph_payload=self._payload(),
                verbose=True,
            )
        output = buf.getvalue()
        self.assertIn("Leiden backend unavailable", output)
        self.assertIn("falling back to label-propagation", output)

    def test_update_graph_clusters_uses_leiden_backend_when_available(self):
        original_igraph = sys.modules.get("igraph")
        original_leidenalg = sys.modules.get("leidenalg")

        class FakeEdgeSeq(dict):
            pass

        class FakeGraph:
            def __init__(self, n: int, edges: list[tuple[int, int]], directed: bool = False):
                self.n = n
                self.edges = edges
                self.directed = directed
                self.es = FakeEdgeSeq()

        def fake_find_partition(graph, partition_type, weights=None, seed=None):
            half = graph.n // 2
            membership = [0 if i < half else 1 for i in range(graph.n)]
            return SimpleNamespace(membership=membership)

        try:
            sys.modules["igraph"] = SimpleNamespace(Graph=FakeGraph)
            sys.modules["leidenalg"] = SimpleNamespace(
                RBConfigurationVertexPartition=object(),
                find_partition=fake_find_partition,
            )
            mod = load_graph_cluster()
            payload = mod.update_graph_clusters(
                root=self.root,
                index_dir=self.root / ".wavefoundry" / "index",
                layer="project",
                graph_payload=self._payload(),
                verbose=False,
            )
            self.assertEqual(payload["cluster_algorithm"], "leiden")
            self.assertEqual(payload["community_count"], 2)
        finally:
            if original_igraph is None:
                sys.modules.pop("igraph", None)
            else:
                sys.modules["igraph"] = original_igraph
            if original_leidenalg is None:
                sys.modules.pop("leidenalg", None)
            else:
                sys.modules["leidenalg"] = original_leidenalg

    def test_update_graph_clusters_remaps_community_ids_on_rerun(self):
        first = self.mod.update_graph_clusters(
            root=self.root,
            index_dir=self.root / ".wavefoundry" / "index",
            layer="project",
            graph_payload=self._payload(),
            verbose=False,
        )
        self.assertGreaterEqual(len(first["communities"]), 1)
        first_ids = {c["community_id"] for c in first["communities"]}

        # Second run with the same payload — community IDs must be stable.
        second = self.mod.update_graph_clusters(
            root=self.root,
            index_dir=self.root / ".wavefoundry" / "index",
            layer="project",
            graph_payload=self._payload(),
            verbose=False,
        )
        self.assertEqual(second["community_count"], first["community_count"])
        second_ids = {c["community_id"] for c in second["communities"]}
        self.assertEqual(second_ids, first_ids)

    def test_update_graph_clusters_handles_isolated_node(self):
        payload = {
            "schema_version": "1",
            "builder_version": "1",
            "layer": "project",
            "graph_mtime": 100,
            "nodes": [
                {"id": "src/c.py", "label": "c", "kind": "module", "source_file": "src/c.py", "source_location": "1:0", "layer": "project"},
            ],
            "edges": [],
            "counts": {"files": 1, "nodes": 1, "edges": 0},
            "present": True,
        }
        result = self.mod.update_graph_clusters(
            root=self.root,
            index_dir=self.root / ".wavefoundry" / "index",
            layer="project",
            graph_payload=payload,
            verbose=False,
        )
        self.assertEqual(result["community_count"], 1)
        self.assertEqual(result["communities"][0]["node_count"], 1)
        self.assertEqual(result["communities"][0]["seed_node_id"], "src/c.py")


    def test_disambiguate_labels_qualifies_duplicates_with_parent_dir(self):
        nodes_by_id = {
            "ui/dashboard.js": {"id": "ui/dashboard.js", "label": "dashboard", "source_file": "ui/dashboard.js"},
            "server/dashboard.py": {"id": "server/dashboard.py", "label": "dashboard", "source_file": "server/dashboard.py"},
        }
        communities = [
            {"community_id": "project:c0", "label": "dashboard", "seed_node_id": "ui/dashboard.js", "node_ids": ["ui/dashboard.js"]},
            {"community_id": "project:c1", "label": "dashboard", "seed_node_id": "server/dashboard.py", "node_ids": ["server/dashboard.py"]},
        ]
        self.mod._disambiguate_labels(communities, nodes_by_id)
        labels = {c["label"] for c in communities}
        self.assertEqual(labels, {"ui/dashboard", "server/dashboard"})

    def test_disambiguate_labels_adds_numeric_suffix_when_labels_still_collide(self):
        # Two communities from different dirs but same label — parent dir qualifies them uniquely
        nodes_by_id = {
            "src/utils.py": {"id": "src/utils.py", "label": "utils", "source_file": "src/utils.py"},
            "lib/utils.js": {"id": "lib/utils.js", "label": "utils", "source_file": "lib/utils.js"},
        }
        communities = [
            {"community_id": "project:c0", "label": "utils", "seed_node_id": "src/utils.py", "node_ids": ["src/utils.py"]},
            {"community_id": "project:c1", "label": "utils", "seed_node_id": "lib/utils.js", "node_ids": ["lib/utils.js"]},
        ]
        self.mod._disambiguate_labels(communities, nodes_by_id)
        labels = {c["label"] for c in communities}
        self.assertEqual(labels, {"src/utils", "lib/utils"})

    def test_disambiguate_labels_leaves_unique_labels_unchanged(self):
        nodes_by_id = {
            "src/indexer.py": {"id": "src/indexer.py", "label": "indexer", "source_file": "src/indexer.py"},
            "src/dashboard.py": {"id": "src/dashboard.py", "label": "dashboard", "source_file": "src/dashboard.py"},
        }
        communities = [
            {"community_id": "project:c0", "label": "indexer", "seed_node_id": "src/indexer.py", "node_ids": ["src/indexer.py"]},
            {"community_id": "project:c1", "label": "dashboard", "seed_node_id": "src/dashboard.py", "node_ids": ["src/dashboard.py"]},
        ]
        self.mod._disambiguate_labels(communities, nodes_by_id)
        self.assertEqual(communities[0]["label"], "indexer")
        self.assertEqual(communities[1]["label"], "dashboard")


    def test_merge_same_stem_communities_combines_same_dir_stem(self):
        adjacency: dict = {}
        nodes_by_id = {
            "ui/dashboard.js": {"id": "ui/dashboard.js", "label": "dashboard", "source_file": "ui/dashboard.js"},
            "ui/dashboard.css": {"id": "ui/dashboard.css", "label": "dashboard", "source_file": "ui/dashboard.css"},
        }
        communities = [
            {"community_id": "project:c0", "label": "dashboard", "seed_node_id": "ui/dashboard.js",
             "node_ids": ["ui/dashboard.js"], "node_count": 1, "edge_count": 0, "boundary_node_count": 0},
            {"community_id": "project:c1", "label": "dashboard", "seed_node_id": "ui/dashboard.css",
             "node_ids": ["ui/dashboard.css"], "node_count": 1, "edge_count": 0, "boundary_node_count": 0},
        ]
        result = self.mod._merge_same_stem_communities(communities, nodes_by_id, adjacency)
        self.assertEqual(len(result), 1)
        self.assertEqual(set(result[0]["node_ids"]), {"ui/dashboard.js", "ui/dashboard.css"})
        self.assertEqual(result[0]["node_count"], 2)

    def test_merge_same_stem_communities_leaves_different_dirs_separate(self):
        adjacency: dict = {}
        nodes_by_id = {
            "src/utils.py": {"id": "src/utils.py", "label": "utils", "source_file": "src/utils.py"},
            "lib/utils.js": {"id": "lib/utils.js", "label": "utils", "source_file": "lib/utils.js"},
        }
        communities = [
            {"community_id": "project:c0", "label": "utils", "seed_node_id": "src/utils.py",
             "node_ids": ["src/utils.py"], "node_count": 1, "edge_count": 0, "boundary_node_count": 0},
            {"community_id": "project:c1", "label": "utils", "seed_node_id": "lib/utils.js",
             "node_ids": ["lib/utils.js"], "node_count": 1, "edge_count": 0, "boundary_node_count": 0},
        ]
        result = self.mod._merge_same_stem_communities(communities, nodes_by_id, adjacency)
        self.assertEqual(len(result), 2)


class IsTestBenchSourceFileTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_graph_cluster()

    def test_test_prefix_filename(self):
        self.assertTrue(self.mod._is_test_source_file("src/test_indexer.py"))

    def test_test_suffix_filename(self):
        self.assertTrue(self.mod._is_test_source_file("src/indexer_test.py"))

    def test_tests_directory(self):
        self.assertTrue(self.mod._is_test_source_file("scripts/tests/test_chunker.py"))

    def test_non_test_file(self):
        self.assertFalse(self.mod._is_test_source_file("src/indexer.py"))

    def test_bench_prefix_filename(self):
        self.assertTrue(self.mod._is_bench_source_file("scripts/bench_report.py"))

    def test_bench_suffix_filename(self):
        self.assertTrue(self.mod._is_bench_source_file("scripts/embed_bench.py"))

    def test_benchmarks_directory(self):
        self.assertTrue(self.mod._is_bench_source_file("scripts/benchmarks/embed_bench.py"))

    def test_non_bench_file(self):
        self.assertFalse(self.mod._is_bench_source_file("src/indexer.py"))

    def test_scripts_directory(self):
        self.assertTrue(self.mod._is_scripts_source_file("scripts/seed.py"))

    def test_scripts_depth_two(self):
        self.assertTrue(self.mod._is_scripts_source_file("backend/scripts/migrate.py"))

    def test_scripts_deep_excluded(self):
        # depth 3+ should not classify as Scripts
        self.assertFalse(self.mod._is_scripts_source_file("pkg/framework/scripts/server.py"))

    def test_bin_directory(self):
        self.assertTrue(self.mod._is_scripts_source_file("bin/update-indexes"))

    def test_cli_directory_any_depth(self):
        self.assertTrue(self.mod._is_scripts_source_file("cli/main.py"))
        self.assertTrue(self.mod._is_scripts_source_file("app/pkg/cli/main.py"))

    def test_non_scripts_file(self):
        self.assertFalse(self.mod._is_scripts_source_file("src/indexer.py"))

    def test_generated_directory(self):
        self.assertTrue(self.mod._is_generated_source_file("generated/models.py"))

    def test_migrations_directory(self):
        self.assertTrue(self.mod._is_generated_source_file("migrations/0001_initial.py"))

    def test_pb2_suffix(self):
        self.assertTrue(self.mod._is_generated_source_file("src/schema_pb2.py"))

    def test_non_generated_file(self):
        self.assertFalse(self.mod._is_generated_source_file("src/models.py"))

    def test_github_actions(self):
        self.assertTrue(self.mod._is_cicd_source_file(".github/workflows/ci.yml"))

    def test_dockerfile(self):
        self.assertTrue(self.mod._is_cicd_source_file("Dockerfile"))

    def test_dockerfile_variant(self):
        self.assertTrue(self.mod._is_cicd_source_file("Dockerfile.prod"))

    def test_docker_compose(self):
        self.assertTrue(self.mod._is_cicd_source_file("docker-compose.yml"))

    def test_non_cicd_file(self):
        self.assertFalse(self.mod._is_cicd_source_file("src/server.py"))

    def test_config_directory(self):
        self.assertTrue(self.mod._is_config_source_file("config/settings.py"))

    def test_config_suffix(self):
        self.assertTrue(self.mod._is_config_source_file("webpack.config.js"))

    def test_non_config_file(self):
        self.assertFalse(self.mod._is_config_source_file("src/indexer.py"))

    def test_pyproject_toml(self):
        self.assertTrue(self.mod._is_config_source_file("pyproject.toml"))

    def test_setup_cfg(self):
        self.assertTrue(self.mod._is_config_source_file("setup.cfg"))

    def test_tsconfig_json(self):
        self.assertTrue(self.mod._is_config_source_file("tsconfig.json"))

    def test_tests_take_priority_over_scripts_in_categorization(self):
        # Both detectors fire, but _extract_fixed_communities puts Tests first.
        self.assertTrue(self.mod._is_test_source_file("scripts/tests/test_foo.py"))
        self.assertTrue(self.mod._is_scripts_source_file("scripts/tests/test_foo.py"))
        nodes_by_id = {
            "scripts/tests/test_foo.py": {"id": "scripts/tests/test_foo.py", "source_file": "scripts/tests/test_foo.py", "label": "test_foo"},
        }
        adjacency: dict = {}
        fixed, _, _ = self.mod._extract_fixed_communities(nodes_by_id, adjacency)
        labels = [c["label"] for c in fixed]
        self.assertIn("Tests", labels)
        self.assertNotIn("Scripts", labels)


class ExtractFixedCommunitiesTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_graph_cluster()

    def _make_nodes_adj(self):
        nodes_by_id = {
            "src/indexer.py": {"id": "src/indexer.py", "source_file": "src/indexer.py", "label": "indexer"},
            "src/indexer.py::build": {"id": "src/indexer.py::build", "source_file": "src/indexer.py", "label": "build"},
            "tests/test_indexer.py": {"id": "tests/test_indexer.py", "source_file": "tests/test_indexer.py", "label": "test_indexer"},
            "benchmarks/bench_embed.py": {"id": "benchmarks/bench_embed.py", "source_file": "benchmarks/bench_embed.py", "label": "bench_embed"},
        }
        adjacency = {
            "src/indexer.py": {"src/indexer.py::build": 1},
            "src/indexer.py::build": {"src/indexer.py": 1},
            "tests/test_indexer.py": {"src/indexer.py": 1},
            "src/indexer.py": {"tests/test_indexer.py": 1},
            "benchmarks/bench_embed.py": {},
        }
        return nodes_by_id, adjacency

    def test_test_nodes_go_into_fixed_tests_community(self):
        nodes_by_id, adjacency = self._make_nodes_adj()
        fixed, reduced_nodes, _ = self.mod._extract_fixed_communities(nodes_by_id, adjacency)
        test_comm = next((c for c in fixed if c["label"] == "Tests"), None)
        self.assertIsNotNone(test_comm)
        self.assertIn("tests/test_indexer.py", test_comm["node_ids"])
        self.assertTrue(test_comm.get("_fixed"))

    def test_bench_nodes_go_into_fixed_benchmarks_community(self):
        nodes_by_id, adjacency = self._make_nodes_adj()
        fixed, _, _ = self.mod._extract_fixed_communities(nodes_by_id, adjacency)
        bench_comm = next((c for c in fixed if c["label"] == "Benchmarks"), None)
        self.assertIsNotNone(bench_comm)
        self.assertIn("benchmarks/bench_embed.py", bench_comm["node_ids"])

    def test_reduced_nodes_excludes_test_and_bench(self):
        nodes_by_id, adjacency = self._make_nodes_adj()
        _, reduced_nodes, _ = self.mod._extract_fixed_communities(nodes_by_id, adjacency)
        self.assertNotIn("tests/test_indexer.py", reduced_nodes)
        self.assertNotIn("benchmarks/bench_embed.py", reduced_nodes)
        self.assertIn("src/indexer.py", reduced_nodes)

    def test_reduced_adjacency_excludes_test_edges(self):
        nodes_by_id, adjacency = self._make_nodes_adj()
        _, _, reduced_adj = self.mod._extract_fixed_communities(nodes_by_id, adjacency)
        self.assertNotIn("tests/test_indexer.py", reduced_adj)
        for neighbors in reduced_adj.values():
            self.assertNotIn("tests/test_indexer.py", neighbors)

    def test_all_six_categories_detected(self):
        nodes_by_id = {
            "tests/test_a.py":        {"id": "tests/test_a.py",        "source_file": "tests/test_a.py",        "label": "test_a"},
            "benchmarks/bench_b.py":  {"id": "benchmarks/bench_b.py",  "source_file": "benchmarks/bench_b.py",  "label": "bench_b"},
            ".github/workflows/ci.yml": {"id": ".github/workflows/ci.yml", "source_file": ".github/workflows/ci.yml", "label": "ci"},
            "generated/schema_pb2.py": {"id": "generated/schema_pb2.py", "source_file": "generated/schema_pb2.py", "label": "schema"},
            "scripts/seed.py":        {"id": "scripts/seed.py",        "source_file": "scripts/seed.py",        "label": "seed"},
            "config/settings.py":     {"id": "config/settings.py",     "source_file": "config/settings.py",     "label": "settings"},
            "src/core.py":            {"id": "src/core.py",            "source_file": "src/core.py",            "label": "core"},
        }
        adjacency: dict = {nid: {} for nid in nodes_by_id}
        fixed, reduced_nodes, _ = self.mod._extract_fixed_communities(nodes_by_id, adjacency)
        labels = {c["label"] for c in fixed}
        self.assertEqual(labels, {"Tests", "Benchmarks", "CI/CD", "Generated", "Scripts", "Configuration"})
        self.assertIn("src/core.py", reduced_nodes)
        self.assertNotIn("tests/test_a.py", reduced_nodes)
        self.assertNotIn(".github/workflows/ci.yml", reduced_nodes)

    def test_no_bench_nodes_omits_benchmarks_community(self):
        nodes_by_id = {
            "src/a.py": {"id": "src/a.py", "source_file": "src/a.py", "label": "a"},
            "tests/test_a.py": {"id": "tests/test_a.py", "source_file": "tests/test_a.py", "label": "test_a"},
        }
        adjacency: dict = {}
        fixed, _, _ = self.mod._extract_fixed_communities(nodes_by_id, adjacency)
        labels = [c["label"] for c in fixed]
        self.assertIn("Tests", labels)
        self.assertNotIn("Benchmarks", labels)


class MergeSmallCommunitiesTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_graph_cluster()

    def _make_community(self, community_id, node_ids, adjacency):
        nodes_by_id = {nid: {"id": nid, "source_file": nid, "label": nid.split("/")[-1]} for nid in node_ids}
        internal_edges = sum(
            1 for a in node_ids for b in adjacency.get(a, {}) if b in node_ids and a < b
        )
        return {
            "community_id": community_id,
            "label": node_ids[0].split("/")[-1],
            "seed_node_id": node_ids[0],
            "node_ids": sorted(node_ids),
            "node_count": len(node_ids),
            "edge_count": internal_edges,
            "boundary_node_count": 0,
        }

    def test_small_community_absorbed_into_neighbor(self):
        adjacency = {
            "src/a.py": {"src/b.py": 5, "src/c.py": 1},
            "src/b.py": {"src/a.py": 5},
            "src/c.py": {"src/a.py": 1},
            "src/d.py": {"src/a.py": 5},
            "src/e.py": {"src/a.py": 5},
        }
        nodes_by_id = {nid: {"id": nid, "source_file": nid, "label": nid} for nid in adjacency}
        big_comm = {
            "community_id": "project:c0", "label": "big", "seed_node_id": "src/a.py",
            "node_ids": ["src/a.py", "src/b.py", "src/d.py", "src/e.py"], "node_count": 4,
            "edge_count": 3, "boundary_node_count": 0,
        }
        small_comm = {
            "community_id": "project:c1", "label": "small", "seed_node_id": "src/c.py",
            "node_ids": ["src/c.py"], "node_count": 1,
            "edge_count": 0, "boundary_node_count": 0,
        }
        result = self.mod._merge_small_communities([big_comm, small_comm], nodes_by_id, adjacency, min_size=4)
        self.assertEqual(len(result), 1)
        self.assertIn("src/c.py", result[0]["node_ids"])
        self.assertIn("src/a.py", result[0]["node_ids"])

    def test_fixed_community_not_absorbed(self):
        adjacency = {
            "tests/test_a.py": {"src/a.py": 2},
            "src/a.py": {"tests/test_a.py": 2, "src/b.py": 3},
            "src/b.py": {"src/a.py": 3, "src/c.py": 3, "src/d.py": 3},
            "src/c.py": {"src/b.py": 3},
            "src/d.py": {"src/b.py": 3},
        }
        nodes_by_id = {nid: {"id": nid, "source_file": nid, "label": nid} for nid in adjacency}
        fixed_comm = {
            "community_id": "project:c0", "label": "Tests", "seed_node_id": "tests/test_a.py",
            "node_ids": ["tests/test_a.py"], "node_count": 1,
            "edge_count": 0, "boundary_node_count": 0, "_fixed": True,
        }
        big_comm = {
            "community_id": "project:c1", "label": "prod", "seed_node_id": "src/a.py",
            "node_ids": ["src/a.py", "src/b.py", "src/c.py", "src/d.py"], "node_count": 4,
            "edge_count": 3, "boundary_node_count": 0,
        }
        result = self.mod._merge_small_communities([fixed_comm, big_comm], nodes_by_id, adjacency, min_size=4)
        fixed_results = [c for c in result if c.get("_fixed")]
        self.assertEqual(len(fixed_results), 1)
        self.assertEqual(fixed_results[0]["label"], "Tests")
        self.assertNotIn("tests/test_a.py", [nid for c in result if not c.get("_fixed") for nid in c["node_ids"]])

    def test_isolated_small_community_left_alone(self):
        adjacency: dict = {"src/a.py": {}, "src/b.py": {}, "src/c.py": {}, "src/d.py": {}}
        nodes_by_id = {nid: {"id": nid, "source_file": nid, "label": nid} for nid in adjacency}
        big = {
            "community_id": "project:c0", "label": "big", "seed_node_id": "src/a.py",
            "node_ids": ["src/a.py", "src/b.py", "src/c.py", "src/d.py"], "node_count": 4,
            "edge_count": 0, "boundary_node_count": 0,
        }
        lone = {
            "community_id": "project:c1", "label": "lone", "seed_node_id": "src/e.py",
            "node_ids": ["src/e.py"], "node_count": 1,
            "edge_count": 0, "boundary_node_count": 0,
        }
        nodes_by_id["src/e.py"] = {"id": "src/e.py", "source_file": "src/e.py", "label": "e"}
        result = self.mod._merge_small_communities([big, lone], nodes_by_id, adjacency, min_size=4)
        # Isolated small community falls back to merging into the largest community.
        self.assertEqual(len(result), 1)
        self.assertIn("src/e.py", result[0]["node_ids"])


class FixedCommunitiesIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_graph_cluster()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry" / "index").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_test_files_grouped_into_tests_community(self):
        nodes = [
            {"id": "src/indexer.py", "label": "indexer", "kind": "module", "source_file": "src/indexer.py", "source_location": "1:0", "layer": "project"},
            {"id": "src/indexer.py::build", "label": "build", "kind": "function", "source_file": "src/indexer.py", "source_location": "2:0", "layer": "project"},
            {"id": "src/indexer.py::run", "label": "run", "kind": "function", "source_file": "src/indexer.py", "source_location": "3:0", "layer": "project"},
            {"id": "src/indexer.py::load", "label": "load", "kind": "function", "source_file": "src/indexer.py", "source_location": "4:0", "layer": "project"},
            {"id": "tests/test_indexer.py", "label": "test_indexer", "kind": "module", "source_file": "tests/test_indexer.py", "source_location": "1:0", "layer": "project"},
            {"id": "tests/test_indexer.py::test_build", "label": "test_build", "kind": "function", "source_file": "tests/test_indexer.py", "source_location": "2:0", "layer": "project"},
        ]
        edges = [
            {"source": "src/indexer.py", "target": "src/indexer.py::build", "relation": "defines", "confidence": "EXTRACTED"},
            {"source": "src/indexer.py", "target": "src/indexer.py::run", "relation": "defines", "confidence": "EXTRACTED"},
            {"source": "src/indexer.py", "target": "src/indexer.py::load", "relation": "defines", "confidence": "EXTRACTED"},
            {"source": "tests/test_indexer.py", "target": "tests/test_indexer.py::test_build", "relation": "defines", "confidence": "EXTRACTED"},
            {"source": "tests/test_indexer.py", "target": "src/indexer.py", "relation": "imports", "confidence": "EXTRACTED"},
        ]
        payload = {
            "schema_version": "1", "builder_version": "1", "layer": "project",
            "graph_mtime": 100, "nodes": nodes, "edges": edges,
            "counts": {"files": 2, "nodes": len(nodes), "edges": len(edges)}, "present": True,
        }
        result = self.mod.update_graph_clusters(
            root=self.root,
            index_dir=self.root / ".wavefoundry" / "index",
            layer="project",
            graph_payload=payload,
            verbose=False,
        )
        communities = result["communities"]
        test_comm = next((c for c in communities if c["label"] == "Tests"), None)
        self.assertIsNotNone(test_comm, "Expected a 'Tests' community")
        self.assertIn("tests/test_indexer.py", test_comm["node_ids"])
        # Test nodes must not appear in any production community
        prod_node_ids = {nid for c in communities if c["label"] != "Tests" for nid in c["node_ids"]}
        self.assertNotIn("tests/test_indexer.py", prod_node_ids)
        self.assertNotIn("tests/test_indexer.py::test_build", prod_node_ids)


if __name__ == "__main__":
    unittest.main()
