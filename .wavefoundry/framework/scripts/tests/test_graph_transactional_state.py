"""Real publication/reset and persisted-cluster recovery controls (wave 207t4)."""
from __future__ import annotations

import copy
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import graph_cluster as clusters
import graph_indexer as graphs
import graph_store
import index_compatibility
import sqlite_runtime
import test_indexer as build_fixtures


class ClusterPublicationStateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.index_dir.mkdir(parents=True)
        self.db = self.index_dir / "index.sqlite"
        self.conn = sqlite_runtime.connect(self.db)
        self.addCleanup(self.conn.close)
        with self.conn:
            self.conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
            self.conn.executemany("INSERT INTO meta VALUES (?,?)", [
                (k, str(v)) for k, v in index_compatibility.SUPPORTED.items()
                if k == "store_schema_version" or k.startswith("graph:")
            ])
            graph_store.create_schema(self.conn)
        self.graph = self._graph()

    def _graph(self, fingerprint="stable"):
        paths = ["src/api.py", "src/store.py", "src/cache.py", "src/query.py",
                 "tests/test_api.py", "bench/bench_api.py", "scripts/build.py",
                 "generated/schema.py", ".github/workflows/build.yml", "config/settings.py"]
        nodes = [{"id": p + "::" + name, "kind": "function", "label": name,
                  "source_file": p, "layer": "project"} for p in paths for name in ("run", "helper")]
        nodes += [{"id": "external::vendor", "kind": "external", "external": True},
                  {"id": "src/api.py::LIMIT", "kind": "constant", "source_file": "src/api.py"}]
        return {"input_fingerprint": fingerprint, "builder_version": graphs.GRAPH_BUILDER_VERSION,
                "schema_version": graphs.GRAPH_SCHEMA_VERSION, "nodes": nodes,
                "edges": [{"source": nodes[i]["id"], "target": nodes[j]["id"],
                           "relation": "calls"} for i in range(8) for j in range(i + 1, 8)]}

    def _compute(self, graph=None, **kwargs):
        with redirect_stderr(io.StringIO()), patch.object(clusters, "_load_leiden_backend", return_value=None):
            return clusters.update_graph_clusters(root=self.root, index_dir=self.index_dir,
                layer="project", graph_payload=graph or self.graph, state_conn=self.conn, **kwargs)

    def _publish(self, payload, *, reset=False):
        publication = graphs.GraphPublication(layer="project", root=self.root, reset=reset,
            meta={k.removeprefix("graph:"): str(v) for k, v in index_compatibility.SUPPORTED.items()
                  if k.startswith("graph:")})
        publication.community = payload["_publication"]
        with self.conn:
            publication.apply(self.conn)
        return publication

    def _seed(self):
        payload = self._compute()
        self._publish(payload)
        self.assertEqual(len(self._members()), 20)
        return payload

    def _members(self, conn=None):
        return set((conn or self.conn).execute(
            "SELECT node_id,community_id FROM graph_community_members WHERE layer='project'"))

    def _rows(self, conn=None):
        conn = conn or self.conn
        return tuple(tuple(conn.execute(f"SELECT * FROM {table} ORDER BY 1,2"))
                     for table in graph_store.GRAPH_TABLES)

    def _assert_complete(self, payload):
        expected = {n["id"] for n in self.graph["nodes"]
                    if not n.get("external") and n["kind"] != "constant"}
        members = self._members()
        self.assertEqual({n for n, _ in members}, expected)
        self.assertEqual(len(members), len(expected))
        catalog = dict(self.conn.execute(
            "SELECT community_id,node_count FROM graph_communities WHERE layer='project'"))
        self.assertEqual(set(catalog), {c["community_id"] for c in payload["communities"]})
        self.assertEqual(len(catalog), payload["community_count"])
        for community in payload["communities"]:
            cid = community["community_id"]
            actual = {n for n, c in members if c == cid}
            self.assertEqual(actual, set(community["node_ids"]))
            self.assertEqual(len(actual), catalog[cid])
            self.assertEqual(len(actual), community["node_count"])
        fixed_expected = {frozenset(p + "::" + name for name in ("run", "helper")) for p in (
            "tests/test_api.py", "bench/bench_api.py", "scripts/build.py", "generated/schema.py",
            ".github/workflows/build.yml", "config/settings.py")}
        fixed_actual = {frozenset(c["node_ids"]) for c in payload["communities"] if c.get("kind") == "fixed"}
        self.assertEqual(fixed_actual, fixed_expected)

    def test_valid_empty_projection_reuses_and_reset_publishes_empty_replacement(self):
        graph = self._graph("empty")
        graph["nodes"] = [n for n in graph["nodes"] if n["kind"] in ("constant", "external")]
        graph["edges"] = []
        payload = self._compute(graph)
        self._publish(payload)
        self.assertEqual(payload["communities"], [])
        self.assertEqual(self._members(), set())
        with patch.object(clusters, "_run_clustering", side_effect=AssertionError("empty recompute")), \
             patch.object(clusters, "compute_betweenness_ranking", side_effect=AssertionError("empty ranking")):
            self.assertNotIn("_publication", self._compute(graph))
            reused = self._compute(graph, reset=True)
        self.assertEqual(reused["_publication"].member_inserts, [])
        self._publish(reused, reset=True)
        self.assertEqual(self._members(), set())
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM graph_analysis").fetchone()[0], 1)

    def test_reset_recompute_replaces_unchanged_members_and_preserves_ids(self):
        before = self._seed()
        old = self._members()
        changed = copy.deepcopy(self.graph)
        changed["input_fingerprint"] = "new-generation"
        payload = self._compute(changed, reset=True)
        self.assertEqual(self._members(), old, "preparation must not mutate the visible generation")
        self.assertEqual(len(payload["_publication"].member_inserts), 20)
        self._publish(payload, reset=True)
        self._assert_complete(payload)
        self.assertEqual(self._members(), old)
        self.assertEqual({c["community_id"] for c in before["communities"]},
                         {c["community_id"] for c in payload["communities"]})

    def test_valid_same_fingerprint_reset_republishes_without_expensive_analysis(self):
        self._seed()
        old = self._members()
        with patch.object(clusters, "_run_clustering", side_effect=AssertionError("clustering reused")), \
             patch.object(clusters, "compute_betweenness_ranking", side_effect=AssertionError("ranking reused")):
            payload = self._compute(reset=True)
        self.assertIn("_publication", payload, "reset reuse still requires a replacement participant")
        self.assertEqual(len(payload["_publication"].member_inserts), 20)
        self._publish(payload, reset=True)
        self.assertEqual(self._members(), old)
        self._assert_complete(payload)

    def test_valid_history_fixed_categories_and_exclusions_reuse_without_writes(self):
        payload = self._seed()
        fixed = {c["label"] for c in payload["communities"] if c.get("kind") == "fixed"}
        self.assertEqual(len(fixed), 6)
        with self.conn:
            self.conn.execute("UPDATE graph_community_members SET input_fingerprint='historical-membership'")
        before = self._rows()
        with patch.object(clusters, "_run_clustering", side_effect=AssertionError("unexpected clustering")), \
             patch.object(clusters, "compute_betweenness_ranking", side_effect=AssertionError("unexpected ranking")):
            result = self._compute()
        self.assertNotIn("_publication", result)
        self.assertEqual(self._rows(), before)
        self._assert_complete(result)

    def test_same_fingerprint_structural_corruption_recomputes_and_repairs(self):
        variants = ("missing_member", "missing_community", "ghost_identity", "duplicate_membership",
                    "orphan_membership", "catalog_count", "catalog_label", "catalog_attributes",
                    "analysis_count", "analysis_duplicate", "analysis_shape", "analysis_schema",
                    "analysis_fingerprint", "analysis_method", "wrong_fixed_category")
        for variant in variants:
            with self.subTest(corruption=variant):
                with self.conn:
                    for table in ("graph_communities", "graph_community_members", "graph_analysis"):
                        self.conn.execute(f"DELETE FROM {table}")
                baseline = self._seed()
                member, cid = sorted(self._members())[0]
                if variant == "ghost_identity":
                    production = next(c for c in baseline["communities"] if c.get("kind") != "fixed")
                    cid = production["community_id"]
                    member = next(n for n in production["node_ids"] if n != production["seed_node_id"])
                other = next(c["community_id"] for c in baseline["communities"] if c["community_id"] != cid)
                with self.conn:
                    if variant == "missing_member":
                        self.conn.execute("DELETE FROM graph_community_members WHERE node_id=?", (member,))
                    elif variant == "missing_community":
                        self.conn.execute("DELETE FROM graph_communities WHERE community_id=?", (cid,))
                    elif variant == "ghost_identity":
                        self.conn.execute("UPDATE graph_community_members SET node_id='ghost:missing' WHERE node_id=?", (member,))
                    elif variant in ("duplicate_membership", "orphan_membership"):
                        self.conn.execute("INSERT INTO graph_community_members VALUES (?,?,'project','stable')",
                            (member, other if variant == "duplicate_membership" else "orphan:community"))
                    elif variant.startswith("catalog_"):
                        column, value = {"catalog_count": ("node_count", 999), "catalog_label": ("label", "wrong"),
                                         "catalog_attributes": ("attributes", '{"kind":"fixed"}') }[variant]
                        self.conn.execute(f"UPDATE graph_communities SET {column}=? WHERE community_id=?", (value, cid))
                    else:
                        raw = self.conn.execute("SELECT payload FROM graph_analysis WHERE kind='clusters'").fetchone()[0]
                        analysis = clusters._decode_analysis(raw)
                        if variant == "analysis_count":
                            analysis["community_count"] += 1
                        elif variant == "analysis_duplicate":
                            analysis["communities"].append(copy.deepcopy(analysis["communities"][0]))
                            analysis["community_count"] += 1
                        elif variant == "analysis_shape":
                            analysis["communities"] = {"invalid": "community list"}
                        elif variant == "analysis_schema":
                            analysis["cluster_schema_version"] = "unsupported-shape"
                        elif variant == "analysis_fingerprint":
                            analysis["input_fingerprint"] = "contradicts-persisted-row"
                        elif variant == "analysis_method":
                            analysis["cluster_algorithm"] = "contradicts-persisted-row"
                        else:
                            # Keep counts, catalog and analysis agreeing; only fixed-category membership is wrong.
                            fixed = [c for c in baseline["communities"] if c.get("kind") == "fixed"]
                            a, b = fixed[:2]
                            a_member = next(n for n in a["node_ids"] if n != a["seed_node_id"])
                            b_member = next(n for n in b["node_ids"] if n != b["seed_node_id"])
                            self.conn.execute("UPDATE graph_community_members SET community_id=? WHERE node_id=?",
                                              (b["community_id"], a_member))
                            self.conn.execute("UPDATE graph_community_members SET community_id=? WHERE node_id=?",
                                              (a["community_id"], b_member))
                        self.conn.execute("UPDATE graph_analysis SET payload=? WHERE kind='clusters'",
                                          (clusters._encode_analysis(analysis),))
                with patch.object(clusters, "_run_clustering", wraps=clusters._run_clustering) as recompute:
                    repaired = self._compute()
                self.assertTrue(recompute.called, variant + " must reject reuse")
                self.assertIn("_publication", repaired)
                self._publish(repaired)
                self._assert_complete(repaired)
                self.assertNotIn("ghost:missing", {n for n, _ in self._members()})

    def test_incremental_membership_delta_writes_only_one_added_member(self):
        self._seed()
        old = self._members()
        changed = copy.deepcopy(self.graph)
        changed["input_fingerprint"] = "one-new-member"
        changed["nodes"].append({"id": "tests/test_api.py::extra", "kind": "function",
                                 "source_file": "tests/test_api.py"})
        payload = self._compute(changed)
        publication = payload["_publication"]
        self.assertEqual(len(publication.member_inserts), 1)
        self.assertEqual(publication.member_deletes, [])
        self._publish(payload)
        self.assertTrue(old <= self._members())
        stamps = dict(self.conn.execute("SELECT node_id,input_fingerprint FROM graph_community_members"))
        self.assertTrue(all(stamps[n] == "stable" for n, _ in old))
        self.assertEqual(stamps["tests/test_api.py::extra"], "one-new-member")

    def test_actual_wal_reader_keeps_old_generation_until_commit_and_after_sql_failure(self):
        self._seed()
        reader = sqlite_runtime.connect(self.db, read_only=True)
        self.addCleanup(reader.close)
        self.assertEqual(self.conn.execute("PRAGMA journal_mode").fetchone()[0].lower(), "wal")
        old = self._rows(reader)
        graph = copy.deepcopy(self.graph)
        graph["input_fingerprint"] = "replacement"
        payload = self._compute(graph, reset=True)
        publication = graphs.GraphPublication(layer="project", reset=True,
            meta={k.removeprefix("graph:"): str(v) for k, v in index_compatibility.SUPPORTED.items() if k.startswith("graph:")})
        publication.community = payload["_publication"]
        with self.conn:
            self.conn.execute("CREATE TEMP TRIGGER fail_cluster BEFORE INSERT ON graph_analysis "
                              "BEGIN SELECT RAISE(ABORT, 'injected cluster SQL fault'); END")
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            with self.assertRaisesRegex(Exception, "injected cluster SQL fault"):
                publication.apply(self.conn)
            self.assertEqual(self._rows(reader), old)
        finally:
            self.conn.execute("ROLLBACK")
        self.assertEqual(self._rows(), old)
        self.assertEqual(self._rows(reader), old)
        self.conn.execute("DROP TRIGGER fail_cluster")
        self.conn.execute("BEGIN IMMEDIATE")
        publication.apply(self.conn)
        self.assertEqual(self._rows(reader), old)
        self.assertNotEqual(self._rows(), old)
        self.conn.execute("COMMIT")
        self.assertEqual(self._rows(reader), self._rows())
        self._assert_complete(payload)

    def test_source_recheck_and_newer_schema_reject_reset_without_destroying_rows(self):
        self._seed()
        payload = self._compute(reset=True)
        source = self.root / "source.py"
        source.write_text("before")
        stat = source.stat()
        publication = graphs.GraphPublication(layer="project", root=self.root, reset=True,
            source_stat={"source.py": (stat.st_size, stat.st_mtime_ns)})
        publication.community = payload["_publication"]
        old = self._rows()
        source.write_text("after, changed size")
        with self.assertRaises(graphs.GraphSourceChanged), self.conn:
            publication.apply(self.conn)
        self.assertEqual(self._rows(), old)
        publication.source_stat = {}
        with self.conn:
            self.conn.execute("UPDATE meta SET value=? WHERE key='graph:schema_version'",
                              (str(int(graphs.GRAPH_SCHEMA_VERSION) + 1),))
        with self.assertRaises(index_compatibility.IndexCompatibilityError), self.conn:
            publication.apply(self.conn)
        self.assertEqual(self._rows(), old)

    def test_normal_layer_diff_isolated_and_reset_remains_global(self):
        self._seed()
        with self.conn:
            self.conn.execute("INSERT INTO graph_communities VALUES ('framework:sentinel','framework','old','sentinel','sentinel',1,'{}')")
            self.conn.execute("INSERT INTO graph_community_members VALUES ('framework:sentinel','framework:sentinel','framework','old')")
        graph = copy.deepcopy(self.graph)
        graph["input_fingerprint"] = "next"
        self._publish(self._compute(graph))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM graph_communities WHERE layer='framework'").fetchone()[0], 1)
        self._publish(self._compute(graph, reset=True), reset=True)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM graph_communities WHERE layer='framework'").fetchone()[0], 0)


class GraphBuildResetTests(build_fixtures._EpochBuildCase):
    def _seed(self):
        build_fixtures._make_repo(self.root, {
            "src/api.py": "def api():\n    return helper()\n\ndef helper():\n    return 1\n",
            "tests/test_api.py": "def test_api():\n    return 1\n",
            "docs/guide.md": "# Guide\n\nAPI guide.\n",
        })
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertNotIn("failed", self._run_build(full=True))

    def _members(self):
        conn = self.iss.open_read_only(self.index_dir)
        try:
            return set(conn.execute("SELECT node_id,community_id FROM graph_community_members WHERE layer='project'"))
        finally:
            conn.close()

    def _force_walker_reset(self):
        conn = sqlite_runtime.connect(self.iss.state_store_path(self.index_dir))
        try:
            with conn:
                conn.execute("UPDATE meta SET value=? WHERE key='graph:walker_version'",
                             (str(int(self.bi.WALKER_VERSION) - 1),))
        finally:
            conn.close()

    def test_public_graph_build_version_reset_restores_all_unchanged_members(self):
        observed = []
        real = self.bi._build_graph_artifacts
        def capture(**kwargs):
            result = real(**kwargs)
            observed.append(result)
            return result
        with patch.object(self.bi, "_build_graph_artifacts", side_effect=capture):
            self._seed()
        self.assertTrue(observed[0]["cluster_recomputed"])
        observed.clear()
        old = self._members()
        self.assertGreater(len(old), 3)
        self._force_walker_reset()
        cluster_module = self.bi._get_graph_cluster()
        with patch.object(self.bi, "_build_graph_artifacts", side_effect=capture), \
             patch.object(cluster_module, "_run_clustering", side_effect=AssertionError("reset must reuse clustering")), \
             patch.object(cluster_module, "compute_betweenness_ranking", side_effect=AssertionError("reset must reuse ranking")), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = self._run_build(content="graph")
        self.assertNotIn("failed", result)
        self.assertTrue(any(r["publication"].reset for r in observed))
        self.assertEqual(self._members(), old)
        for row in observed:
            if row["publication"].reset:
                self.assertIsNotNone(row["publication"].community)
                self.assertFalse(row["cluster_recomputed"])

    def test_actual_orphan_reconciliation_reset_caller_restores_members(self):
        self._seed()
        old = self._members()
        self._force_walker_reset()
        conn = sqlite_runtime.connect(self.iss.state_store_path(self.index_dir))
        try:
            meta = build_fixtures._read_meta_store(self.index_dir)["file_meta"]
            files = [self.root / rel for rel in meta if (self.root / rel).is_file()]
            cluster_module = self.bi._get_graph_cluster()
            with patch.object(cluster_module, "_run_clustering", side_effect=AssertionError("orphan reset clustering reused")), \
                 patch.object(cluster_module, "compute_betweenness_ranking", side_effect=AssertionError("orphan reset ranking reused")), \
                 redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                stats = self.bi._execute_orphan_store_reconcile(self.root, self.index_dir,
                    {"graph": {"src/older-pack-orphan.py"}}, files_for_graph=files,
                    current_file_meta=meta, chunker_version=self.bi._get_chunker().CHUNKER_VERSION,
                    state_conn=conn)
            self.assertIn("graph_publication", stats)
            self.assertFalse(stats["graph_publication"]["cluster_recomputed"])
            publication = stats["graph_publication"]["publication"]
            self.assertTrue(publication.reset)
            self.assertIsNotNone(publication.community)
            with conn:
                publication.apply(conn)
        finally:
            conn.close()
        self.assertEqual(self._members(), old)


if __name__ == "__main__":
    unittest.main()
