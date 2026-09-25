"""Generation-bound reads across every migrated consumer (wave 1xny6, lane L5).

Covers the reader half of AC-2, AC-5 and AC-7's map cells: one generation per
whole tool response, cross-generation content sharing with explicit provenance,
the dashboard's WAL-safe refresh signal, the codebase-map receipt's ordering and
busy-tolerance, and the rule that no read path recreates the retired graph
folder.
"""
from __future__ import annotations

import contextlib
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = Path(__file__).resolve().parent
for _p in (str(SCRIPTS_ROOT), str(TESTS_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import graph_cluster  # noqa: E402
import graph_fixture_support as gfs  # noqa: E402
import graph_snapshot  # noqa: E402
import index_paths  # noqa: E402
import index_state_store  # noqa: E402

def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_ROOT / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    # A moved module's flat file is a sys.modules alias (wave 1yzd0): executing
    # it replaces sys.modules[name] with the package module and leaves ``mod``
    # hollow, so return the registered module rather than ``mod``.
    return sys.modules[name]


def _retired_graph_dir(root: Path) -> Path:
    return root / ".wavefoundry" / "index" / "graph"


def _embedder_mock():
    """Deterministic nonzero vectors, so a real build exercises the real store."""
    import numpy as np
    from unittest.mock import MagicMock

    def fake_embed(texts, batch_size=256):
        for text in list(texts):
            vector = np.zeros(384, dtype=np.float32)
            vector[0] = 1
            vector[1] = (len(text) % 13) / 13
            yield vector

    mock = MagicMock()
    mock.embed.side_effect = fake_embed
    return mock


def _nodes(*names):
    return [
        {"id": f"src/{n}.py::{n}", "label": n, "kind": "function",
         "source_file": f"src/{n}.py", "source_location": "1:0", "layer": "project"}
        for n in names
    ]


def _community(cid, label, node_ids):
    return {"community_id": cid, "label": label, "seed_node_id": node_ids[0],
            "node_ids": list(node_ids), "node_count": len(node_ids),
            "edge_count": 0, "boundary_node_count": 0}


class _RootCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / ".wavefoundry" / "index").mkdir(parents=True, exist_ok=True)
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(graph_snapshot.invalidate, self.root)

    def _publish(self, *names, communities=None, **kw):
        nodes = _nodes(*names)
        if communities is None:
            communities = [_community("project:c0", "core", [n["id"] for n in nodes])]
        return gfs.publish_graph(self.root, nodes=nodes, edges=[],
                                 communities=communities, **kw)


class GenerationBoundAcquisitionTests(_RootCase):
    """AC-5: one pinned read snapshot binds the generation AND the rows."""

    def test_graph_and_communities_come_from_one_generation(self):
        self._publish("a", "b")
        snapshot = graph_snapshot.acquire(self.root)
        self.assertTrue(snapshot.ready)
        self.assertEqual(snapshot.graph_content_generation, snapshot.generation)
        self.assertEqual(snapshot.community_content_generation, snapshot.generation)
        self.assertEqual({n["id"] for n in snapshot.graph["nodes"]},
                         set(snapshot.clusters["communities"][0]["node_ids"]))

    def test_a_publication_between_two_reads_cannot_mix_generations(self):
        """The mutant: read the graph, let a publication land, read communities.

        Before the pin this was two independent artifact reads and the pair
        could straddle a build. Now both halves come from the same pinned
        transaction, so the second read either sees the same generation (inside
        a pin) or a COHERENT newer one -- never one half of each.
        """
        self._publish("a", "b")
        with graph_snapshot.pinned(self.root) as pinned:
            first_generation = pinned.generation
            first_nodes = {n["id"] for n in pinned.graph["nodes"]}
            # A whole new generation lands mid-response.
            self._publish("a", "b", "c")
            again = graph_snapshot.acquire(self.root)
            self.assertIs(again, pinned, "a pin must not be swapped mid-response")
            self.assertEqual(again.generation, first_generation)
            self.assertEqual({n["id"] for n in again.graph["nodes"]}, first_nodes)
            self.assertEqual(
                {n["id"] for n in again.graph["nodes"]},
                set(again.clusters["communities"][0]["node_ids"]),
                "graph and communities must describe the same build")
        after = graph_snapshot.acquire(self.root)
        self.assertGreater(after.generation, first_generation)
        self.assertIn("src/c.py::c", {n["id"] for n in after.graph["nodes"]})

    def test_unchanged_input_shares_content_across_generations_with_provenance(self):
        self._publish("a", "b")
        first = graph_snapshot.acquire(self.root)
        gfs.bump_generation(self.root)
        second = graph_snapshot.acquire(self.root)
        self.assertGreater(second.generation, first.generation)
        self.assertIs(second.graph, first.graph)
        self.assertIs(second.clusters, first.clusters)
        self.assertTrue(second.shared_graph_content)
        self.assertTrue(second.shared_community_content)
        provenance = second.provenance()
        self.assertEqual(provenance["graph_content_generation"], first.generation)
        self.assertEqual(provenance["generation"], second.generation)

    def test_changed_graph_is_not_shared(self):
        self._publish("a")
        first = graph_snapshot.acquire(self.root)
        self._publish("a", "b")
        second = graph_snapshot.acquire(self.root)
        self.assertFalse(second.shared_graph_content)
        self.assertIsNot(second.graph, first.graph)
        self.assertEqual(second.graph_content_generation, second.generation)

    def test_retry_is_bounded_to_one_reacquisition(self):
        """A store stuck mid-publication retries once, then returns not-ready."""
        self._publish("a")
        reads: list[bool] = []
        real = graph_snapshot._read_pinned

        def spy(index_dir, layer, cached, *, settle=True):
            reads.append(settle)
            return real(index_dir, layer, cached, settle=settle)

        with patch.object(graph_snapshot, "_read_pinned", spy):
            index_dir = self.root / ".wavefoundry" / "index"
            store = index_state_store.IndexStateStore(index_dir)
            try:
                with store._conn:
                    store._conn.execute(
                        "UPDATE build_state SET status = 'building' WHERE id = 1")
            finally:
                store.close()
            graph_snapshot.invalidate(self.root)
            snapshot = graph_snapshot.acquire(self.root)
        self.assertEqual(reads, [True, False],
                         "exactly one re-acquisition, then the established response")
        self.assertEqual(snapshot.state, graph_snapshot.NOT_READY)
        self.assertFalse(snapshot.present)

    def test_only_a_never_started_epoch_allows_standalone_generation_zero(self):
        self._publish("standalone")
        index_dir = graph_snapshot.index_dir_for(self.root)
        with contextlib.closing(index_state_store.IndexStateStore(index_dir)) as store:
            with store._conn:
                store._conn.execute("UPDATE build_state SET status='uninitialized', attempt_id='', generation=0")
        self.assertTrue(graph_snapshot.acquire(self.root).present)
        for attempt, generation in (("interrupted", 0), ("", 1)):
            with self.subTest(attempt=attempt, generation=generation):
                with contextlib.closing(index_state_store.IndexStateStore(index_dir)) as store:
                    with store._conn:
                        store._conn.execute("UPDATE build_state SET attempt_id=?, generation=?", (attempt, generation))
                self.assertEqual(graph_snapshot.acquire(self.root).state, graph_snapshot.NOT_READY)

    def test_committed_participants_without_final_epoch_are_not_served(self):
        self._publish("old")
        previous = graph_snapshot.acquire(self.root)
        # Real participant commit; suppress only the subsequent epoch CAS.
        with patch.object(index_state_store, "finalize_build_epoch", return_value=True):
            self._publish("new")
        from dashboard_lib import read_graph_payload
        payload = read_graph_payload(self.root, "project")
        self.assertFalse(payload["present"])
        self.assertEqual(graph_snapshot.acquire(self.root).state, graph_snapshot.NOT_READY)
        self.assertIsNone(index_state_store.build_epoch_token(graph_snapshot.index_dir_for(self.root)))
        self.assertEqual(previous.graph["nodes"][0]["id"], "src/old.py::old")

    def test_a_publication_during_the_read_cannot_tear_the_snapshot(self):
        """The pinned read transaction, exercised by a REAL interleaving.

        The header (counts, fingerprint) is read from ``meta`` before the rows.
        Without one pinned read snapshot a publication landing between those
        two reads pairs an old header with new rows -- the exact
        combined-generations result the contract forbids, and a defect no
        amount of before/after comparison outside the transaction can see.
        """
        self._publish("a", "b")
        graph_snapshot.invalidate(self.root)
        import graph_indexer

        real = graph_indexer.read_graph_payload_rows
        fired: list[int] = []

        def spy(conn, layer="project"):
            if not fired:
                fired.append(1)
                # A whole new generation commits between the meta read and this
                # row read. WAL lets it commit while our reader holds a snapshot.
                self._publish("a", "b", "c")
            return real(conn, layer)

        with patch.object(graph_indexer, "read_graph_payload_rows", spy):
            snapshot = graph_snapshot.acquire(self.root)
        self.assertTrue(fired, "the interleaving did not happen")
        self.assertTrue(snapshot.present)
        # The snapshot's fingerprint comes from the meta read that happens
        # BEFORE the rows; the payload's comes from the header read inside the
        # row reader. Equal means both reads saw one committed state.
        self.assertEqual(
            snapshot.graph_fingerprint, snapshot.graph["input_fingerprint"],
            "the generation stamp and the rows came from different commits")
        self.assertEqual(
            len(snapshot.graph["nodes"]), snapshot.graph["counts"]["nodes"],
            "the header and the rows came from different generations")

    def test_an_unreadable_store_returns_failure_not_an_empty_graph(self):
        database = index_paths.runtime_database_path(
            self.root / ".wavefoundry" / "index")
        database.write_bytes(b"not a database")
        graph_snapshot.invalidate(self.root)
        snapshot = graph_snapshot.acquire(self.root)
        self.assertEqual(snapshot.state, graph_snapshot.NOT_READY)
        self.assertNotEqual(snapshot.diagnostic["code"], "graph_publication_in_flight")
        self.assertFalse(snapshot.present)

    def test_concurrent_acquisitions_hydrate_once_and_share(self):
        self._publish("a", "b")
        graph_snapshot.invalidate(self.root)
        results: list = []
        barrier = threading.Barrier(4)

        def worker():
            barrier.wait(timeout=10)
            results.append(graph_snapshot.acquire(self.root))

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        self.assertEqual(len(results), 4)
        self.assertEqual({id(r.graph) for r in results}.__len__(), 1,
                         "concurrent readers must share one hydrated payload")


class ConsumerParityTests(_RootCase):
    """AC-2/AC-5: each migrated consumer serves the published rows."""

    def setUp(self):
        super().setUp()
        self.srv = _load("server_impl")
        self.gq = _load("graph_query")
        self.dash = _load("dashboard_lib")

    def test_cluster_reader_serves_rows_and_names_the_database_component(self):
        self._publish("a", "b")
        payload = graph_cluster.read_cluster_payload(self.root, "project")
        self.assertTrue(payload["present"])
        self.assertEqual(payload["community_count"], 1)
        self.assertTrue(payload["cluster_path"].endswith("#communities"))
        self.assertNotIn("cluster_mtime", payload,
                         "a deleted file's mtime is not a live artifact property")
        self.assertEqual(payload["generation"],
                         graph_snapshot.acquire(self.root).generation)

    def test_cluster_reader_hands_back_a_mutable_copy(self):
        self._publish("a", "b")
        first = graph_cluster.read_cluster_payload(self.root, "project")
        first["communities"][0]["label"] = "MUTATED"
        first["communities"][0]["node_ids"].append("bogus")
        second = graph_cluster.read_cluster_payload(self.root, "project")
        self.assertEqual(second["communities"][0]["label"], "core")
        self.assertNotIn("bogus", second["communities"][0]["node_ids"])

    def test_graph_query_index_serves_rows(self):
        self._publish("a", "b")
        index = self.gq.get_query_index(self.root)
        self.assertTrue(index.present)
        self.assertEqual(len(index.nodes), 2)

    def test_health_reports_the_database_component_not_a_filename(self):
        self._publish("a", "b")
        summary = self.srv._graph_health_summary(self.root)["project"]
        self.assertTrue(summary["present"])
        self.assertEqual(summary["node_count"], 2)
        self.assertTrue(summary["component"].endswith("#graph"))
        self.assertEqual(summary["generation"],
                         graph_snapshot.acquire(self.root).generation)

    def test_dashboard_payload_carries_the_generation_not_mtimes(self):
        self._publish("a", "b")
        payload = self.dash.read_graph_payload(self.root, "project")
        self.assertTrue(payload["present"])
        self.assertNotIn("graph_mtime", payload)
        self.assertNotIn("cluster_mtime", payload)
        generation = graph_snapshot.acquire(self.root).generation
        self.assertEqual(payload["graph_version"], generation)
        self.assertEqual(payload["clusters"]["generation"], generation)

    def test_dashboard_enrichment_does_not_mutate_the_resident_view(self):
        self._publish("a", "b")
        self.dash.read_graph_payload(self.root, "project")
        resident = graph_snapshot.acquire(self.root).graph
        for node in resident["nodes"]:
            self.assertNotIn("degree", node,
                             "the shared resident payload was mutated by a reader")

    def test_memory_betweenness_reads_the_published_ranking(self):
        gfs.publish_graph(
            self.root, nodes=_nodes("core"), edges=[],
            clusters=gfs.cluster_payload(
                [], betweenness={"method": "exact", "node_count": 1, "edge_count": 0,
                                 "elapsed_ms": 0,
                                 "ranking": [{"node_id": "src/core.py::core",
                                              "score": 4.0}]}),
        )
        self.srv._MEMORY_BETWEENNESS_CACHE.clear()
        scores = self.srv._memory_betweenness_by_file(self.root)
        self.assertEqual(scores.get("src/core.py"), 4.0)

    def test_a_whole_report_response_observes_one_generation(self):
        """A mid-response publication must not leak into the response."""
        self._publish("a", "b")
        generation = graph_snapshot.acquire(self.root).generation
        seen: list[int] = []
        # The server loads its own module instance; patch THAT one.
        server_cluster = self.srv._load_script("graph_cluster")
        real = server_cluster.read_cluster_payload

        def spy(root, layer):
            # Publish BETWEEN the report's graph read and its community read.
            self._publish("a", "b", "c")
            payload = real(root, layer)
            seen.append(payload.get("generation"))
            return payload

        with patch.object(server_cluster, "read_cluster_payload", spy):
            result = self.srv.wf_graph_report_response(self.root, layer="project", limit=5)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(seen, "the report did not read communities")
        for observed in seen:
            self.assertEqual(observed, generation,
                             "the response straddled a publication")


class RebuildRebindingTests(_RootCase):
    """A response that rebuilds must then serve what its rebuild published."""

    def setUp(self):
        super().setUp()
        self.gq = _load("graph_query")
        self.addCleanup(self.gq._VERSION_CHECK_CACHE.clear)

    def _with_publishing_rebuild(self):
        """Patch the rebuild coordinator with one that actually publishes."""
        outer = self

        class _Loader:
            def exec_module(self, module):
                def _build(root, **kw):
                    outer._publish("a", "b", "c")
                    return {"ok": True}
                module.build_index = _build

        class _Spec:
            name = "indexer_for_graph_query_rebuild"
            loader = _Loader()

        real_spec = importlib.util.spec_from_file_location
        real_module = importlib.util.module_from_spec

        def spec_patch(name, path):
            return _Spec() if name == _Spec.name else real_spec(name, path)

        def module_patch(spec):
            return (type(sys)("fake") if getattr(spec, "name", "") == _Spec.name
                    else real_module(spec))

        return (patch("importlib.util.spec_from_file_location", spec_patch),
                patch("importlib.util.module_from_spec", module_patch))

    def test_the_version_check_records_the_generation_the_rebuild_published(self):
        """Otherwise every later call re-fires the rebuild.

        The post-rebuild signature is recorded from a re-acquisition that runs
        INSIDE the caller's pin. Reading the pinned (pre-rebuild) view there
        stamps the state the rebuild just replaced as verified, so the next
        call finds the recorded signature stale and rebuilds again -- the
        rebuild storm the verification cache exists to prevent.
        """
        self._publish("a", "b", builder_version="0")
        self.gq._VERSION_CHECK_CACHE.clear()
        key = (str(self.root.resolve()), "project")
        p1, p2 = self._with_publishing_rebuild()
        with p1, p2:
            first = self.gq.get_query_index(self.root)
        self.assertEqual((first.auto_rebuild_diagnostic or {}).get("code"),
                         "graph_auto_rebuilt")
        published = graph_snapshot.acquire(self.root)
        recorded = self.gq._VERSION_CHECK_CACHE.get(key)
        self.assertIsNotNone(recorded, "the post-rebuild state was not recorded")
        self.assertEqual(
            recorded[0], (published.generation, published.graph_fingerprint),
            "the verification cache recorded the PRE-rebuild generation")
        with p1, p2:
            second = self.gq.get_query_index(self.root)
        self.assertIsNone(second.auto_rebuild_diagnostic,
                          "the rebuild re-fired on the very next call")

    def test_a_successful_rebuild_rebinds_the_pin_to_the_new_generation(self):
        """The rebuild happens INSIDE the response's pin.

        Re-acquiring there returns the pinned pre-rebuild view -- correct for
        every other read in the response, and exactly wrong here: the response
        asked for the rebuild and must be served its result, not the state it
        just replaced. Only an explicit rebind does that.
        """
        self._publish("a", "b")
        before = graph_snapshot.acquire(self.root)

        def fake_check(root, layer, snapshot=None):
            # Publish what a real rebuild would have published.
            self._publish("a", "b", "c")
            return {"code": "graph_auto_rebuilt", "from_builder_version": "0",
                    "to_builder_version": "1", "rebuild_duration_ms": 1}

        with patch.object(self.gq, "_ensure_graph_builder_current", fake_check):
            index = self.gq.get_query_index(self.root)
            payload = self.gq.load_graph(self.root)
        ids = {str(n.get("id")) for n in index.nodes}
        self.assertIn("src/c.py::c", ids,
                      "the index served the pre-rebuild generation")
        self.assertIn("src/c.py::c", {str(n.get("id")) for n in payload["nodes"]},
                      "load_graph served the pre-rebuild generation")
        self.assertGreater(graph_snapshot.acquire(self.root).generation,
                           before.generation)


class RetiredGraphFolderTests(_RootCase):
    """AC-7: no read path recreates the retired graph directory."""

    def setUp(self):
        super().setUp()
        self.gen = _load("gen_codebase_map")
        self.gq = _load("graph_query")
        self.srv = _load("server_impl")
        self.dash = _load("dashboard_lib")

    def _assert_absent(self, what: str):
        self.assertFalse(
            _retired_graph_dir(self.root).exists(),
            f"{what} recreated the retired graph directory")

    def test_map_generation_never_creates_it(self):
        self._publish("a", "b")
        shutil.rmtree(_retired_graph_dir(self.root), ignore_errors=True)
        self.gen.generate_codebase_map(self.root)
        self.gen.generate_codebase_map(self.root)
        self._assert_absent("codebase-map generation")

    def test_clustering_read_path_never_creates_it(self):
        self._publish("a", "b")
        shutil.rmtree(_retired_graph_dir(self.root), ignore_errors=True)
        graph_cluster.read_cluster_payload(self.root, "project")
        self._assert_absent("the community reader")

    def test_query_triggered_version_rebuild_never_creates_it(self):
        """The reader's rebuild path must delegate, never repair in place."""
        self._publish("a", "b", builder_version="0")
        shutil.rmtree(_retired_graph_dir(self.root), ignore_errors=True)
        calls: list = []

        def fake_build_index(root, **kw):
            calls.append(kw)
            return {"ok": True}

        module = type(sys)("indexer_for_graph_query_rebuild")
        module.build_index = fake_build_index

        class _Loader:
            def exec_module(self, mod):
                mod.build_index = fake_build_index

        class _Spec:
            name = "indexer_for_graph_query_rebuild"
            loader = _Loader()

        real_spec = importlib.util.spec_from_file_location
        real_module = importlib.util.module_from_spec

        def spec_patch(name, path):
            return _Spec() if name == _Spec.name else real_spec(name, path)

        def module_patch(spec):
            return (type(sys)("fake") if getattr(spec, "name", "") == _Spec.name
                    else real_module(spec))

        with patch("importlib.util.spec_from_file_location", spec_patch), \
                patch("importlib.util.module_from_spec", module_patch):
            diagnostic = self.gq._ensure_graph_builder_current(self.root, "project")
        self.assertEqual((diagnostic or {}).get("code"), "graph_auto_rebuilt")
        self.assertEqual(len(calls), 1,
                         "the reader must go through the coordinated build entry point")
        self._assert_absent("the query-triggered rebuild")

    def test_read_only_health_and_dashboard_calls_never_create_it(self):
        self._publish("a", "b")
        shutil.rmtree(_retired_graph_dir(self.root), ignore_errors=True)
        self.srv._graph_health_summary(self.root)
        self.dash.read_graph_payload(self.root, "project")
        self.dash.read_graph_cluster_payload(self.root, "project")
        self._assert_absent("read-only health/dashboard calls")

    def test_ordinary_indexing_never_creates_it(self):
        """AC-7's ordinary-indexing cell, which this class could not cover.

        Until wave 1xny6 lane L6b the build coordinator ran transitional
        derived writers after every publication, so a real ``build_index`` DID
        recreate the retired folder and only read paths could be asserted here.
        The writers are retired, so the whole build path is now assertable:
        a full build, an incremental build over an edit, and a zero-change
        build must each leave the folder absent while publishing real graph
        rows.
        """
        indexer = _load("indexer")
        src = self.root / "src"
        src.mkdir(parents=True, exist_ok=True)
        (src / "alpha.py").write_text("def alpha():\n    return 1\n", encoding="utf-8")
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text(
            '{"lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0}}',
            encoding="utf-8")

        def run(full: bool) -> dict:
            embedders = [_embedder_mock(), _embedder_mock()]
            with patch.object(indexer, "_get_embedder", side_effect=embedders):
                return indexer.build_index(self.root, full=full, content="all", verbose=False)

        self.assertNotIn("failed", run(True))
        self._assert_absent("a full ordinary build")
        self.assertIn("src/alpha.py::alpha", self._published_node_ids())

        (src / "alpha.py").write_text(
            "def alpha():\n    return 2\n\n\ndef beta():\n    return 3\n", encoding="utf-8")
        self.assertNotIn("failed", run(False))
        self._assert_absent("an incremental ordinary build")
        self.assertIn("src/alpha.py::beta", self._published_node_ids())

        self.assertNotIn("failed", run(False))
        self._assert_absent("a zero-change ordinary build")

    def _published_node_ids(self) -> set:
        graph_snapshot.invalidate(self.root)
        return {str(n.get("id")) for n in graph_snapshot.acquire(self.root).graph["nodes"]}


class CodebaseMapReceiptTests(_RootCase):
    """AC-7 map cells: the receipt replaces the standalone fingerprint file."""

    def setUp(self):
        super().setUp()
        self.gen = _load("gen_codebase_map")
        (self.root / "docs" / "references").mkdir(parents=True, exist_ok=True)
        self._publish("a", "b")

    def _output(self) -> Path:
        return self.gen.output_path(self.root)

    def test_the_receipt_lands_in_sqlite_and_no_fingerprint_file_is_written(self):
        self.gen.generate_codebase_map(self.root)
        receipt = graph_snapshot.read_map_receipt(self.root)
        self.assertIsNotNone(receipt)
        self.assertTrue(receipt["input_fingerprint"])
        self.assertEqual(receipt["graph_generation"],
                         graph_snapshot.acquire(self.root).generation)
        self.assertFalse(
            (_retired_graph_dir(self.root) / ".codebase-map.fingerprint").exists())

    def test_unchanged_inputs_are_a_true_no_op(self):
        first = self.gen.generate_codebase_map(self.root)
        stat = self._output().stat()
        second = self.gen.generate_codebase_map(self.root)
        self.assertEqual(first, second)
        self.assertEqual(self._output().stat().st_mtime_ns, stat.st_mtime_ns)

    def test_a_deleted_map_output_regenerates_even_with_the_receipt_present(self):
        self.gen.generate_codebase_map(self.root)
        self.assertIsNotNone(graph_snapshot.read_map_receipt(self.root))
        self._output().unlink()
        self.gen.generate_codebase_map(self.root)
        self.assertTrue(self._output().is_file())

    def test_a_failed_repo_index_refresh_writes_no_receipt_and_retries_next_run(self):
        with patch.object(self.gen, "_refresh_repo_index_modules",
                          side_effect=RuntimeError("boom")):
            markdown = self.gen.generate_codebase_map(self.root)
        self.assertTrue(markdown, "the render must still return valid output")
        self.assertTrue(self._output().is_file(),
                        "the published markdown must remain valid")
        self.assertIsNone(graph_snapshot.read_map_receipt(self.root),
                          "a half-published render must not be certified")
        calls: list = []
        real_render = self.gen.render_markdown

        def spy(*a, **k):
            calls.append(1)
            return real_render(*a, **k)

        with patch.object(self.gen, "render_markdown", spy):
            self.gen.generate_codebase_map(self.root)
        self.assertTrue(calls, "the next run must re-render, not skip")
        self.assertIsNotNone(graph_snapshot.read_map_receipt(self.root))

    def test_an_older_render_cannot_overwrite_a_newer_completed_one(self):
        self.gen.generate_codebase_map(self.root)
        stale = graph_snapshot.acquire(self.root)
        # A newer generation renders and certifies first.
        self._publish("a", "b", "c")
        self.gen.generate_codebase_map(self.root)
        newer_text = self._output().read_text(encoding="utf-8")
        newer_receipt = graph_snapshot.read_map_receipt(self.root)
        # Now the stale render finishes, still holding the OLD snapshot.
        with patch.object(graph_snapshot, "acquire", return_value=stale):
            self.gen.generate_codebase_map(self.root)
        self.assertEqual(self._output().read_text(encoding="utf-8"), newer_text,
                         "a stale render overwrote a newer completed output")
        self.assertEqual(graph_snapshot.read_map_receipt(self.root), newer_receipt,
                         "a stale render certified a newer generation")

    def test_publication_serializes_after_the_final_freshness_check(self):
        """A second renderer cannot finish between the check and first write."""
        self.gen.generate_codebase_map(self.root)
        reached_write = threading.Event()
        release_write = threading.Event()
        contender_started = threading.Event()
        contender_done = threading.Event()
        errors = []
        original_write = Path.write_text
        import runtime_lock
        original_acquire = runtime_lock.RuntimeFileLock.acquire

        def write(path, *args, **kwargs):
            if path == self._output() and threading.current_thread().name == "old-render":
                reached_write.set()
                if not release_write.wait(10):
                    raise TimeoutError("test did not release old renderer")
            return original_write(path, *args, **kwargs)

        def acquire(lock):
            if threading.current_thread().name == "new-render":
                contender_started.set()
            return original_acquire(lock)

        def render(done=None):
            try:
                self.gen.generate_codebase_map(self.root, force=True)
            except BaseException as exc:
                errors.append(exc)
            finally:
                if done is not None:
                    done.set()

        with patch.object(Path, "write_text", write), patch.object(runtime_lock.RuntimeFileLock, "acquire", acquire):
            old = threading.Thread(target=render, name="old-render")
            old.start()
            try:
                self.assertTrue(reached_write.wait(10))
                self._publish("a", "b", "newest")
                new = threading.Thread(target=render, args=(contender_done,), name="new-render")
                new.start()
                try:
                    self.assertTrue(contender_started.wait(10))
                    self.assertFalse(contender_done.wait(0.2), "new render passed the publication lock")
                finally:
                    release_write.set()
                    new.join(10)
                    self.assertFalse(new.is_alive())
            finally:
                release_write.set()
                old.join(10)
                self.assertFalse(old.is_alive())
        self.assertEqual(errors, [])
        newest = self._output().read_text(encoding="utf-8")
        self.assertIn("newest", newest)
        self.assertEqual(graph_snapshot.read_map_receipt(self.root)["graph_generation"],
                         graph_snapshot.acquire(self.root).generation)
        self.assertEqual(self.gen.generate_codebase_map(self.root), newest)

    def test_another_process_waits_for_output_and_receipt_publication(self):
        """A fresh interpreter uses the same OS lock, not a process-local mutex."""
        original_write = Path.write_text
        child = None
        code = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import runtime_lock, gen_codebase_map
original = runtime_lock.RuntimeFileLock.acquire
def acquire(lock):
    print('acquiring', flush=True)
    return original(lock)
runtime_lock.RuntimeFileLock.acquire = acquire
gen_codebase_map.generate_codebase_map(Path(sys.argv[2]), force=True)
"""

        def write(path, *args, **kwargs):
            nonlocal child
            if path == self._output() and child is None:
                child = subprocess.Popen(
                    [sys.executable, "-B", "-c", code, str(SCRIPTS_ROOT), str(self.root)],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                )
                # The child has prepared its render and reached the real lock.
                self.assertEqual(child.stdout.readline().strip(), "acquiring")
                with self.assertRaises(subprocess.TimeoutExpired):
                    child.wait(timeout=0.2)
            return original_write(path, *args, **kwargs)

        try:
            with patch.object(Path, "write_text", write):
                self.gen.generate_codebase_map(self.root, force=True)
            self.assertIsNotNone(child)
            stdout, stderr = child.communicate(timeout=15)
            self.assertEqual(child.returncode, 0, stderr)
            self.assertTrue(graph_snapshot.read_map_receipt(self.root))
        finally:
            if child is not None:
                if child.poll() is None:
                    child.kill()
                child.communicate()

    def test_unfinished_epoch_preserves_the_existing_map(self):
        expected = self.gen.generate_codebase_map(self.root)
        receipt = graph_snapshot.read_map_receipt(self.root)
        with patch.object(index_state_store, "finalize_build_epoch", return_value=True):
            self._publish("unpublished")
        self.assertEqual(self.gen.generate_codebase_map(self.root, force=True), expected)
        self.assertEqual(self._output().read_text(encoding="utf-8"), expected)
        self.assertEqual(graph_snapshot.read_map_receipt(self.root), receipt)

    def test_same_generation_changed_input_cannot_publish_an_old_render(self):
        area = self.root / "src" / "AGENTS.md"
        area.parent.mkdir(parents=True, exist_ok=True)
        area.write_text("# Old responsibility\n", encoding="utf-8")
        original_render = self.gen.render_markdown
        changed = False

        def render(*args, **kwargs):
            nonlocal changed
            markdown = original_render(*args, **kwargs)
            if not changed:
                changed = True
                area.write_text("# New responsibility\n", encoding="utf-8")
                self.gen.generate_codebase_map(self.root)
            return markdown

        with patch.object(self.gen, "render_markdown", render):
            self.gen.generate_codebase_map(self.root, force=True)
        text = self._output().read_text(encoding="utf-8")
        self.assertIn("New responsibility", text)
        self.assertNotIn("Old responsibility", text)
        self.assertEqual(self.gen.generate_codebase_map(self.root), text)

    def test_a_contended_receipt_write_leaves_valid_output_and_retries(self):
        """A full rebuild holds the write lock longer than the busy timeout.

        The map CLI takes no build lock, so this is an ordinary outcome: the
        render must publish, must not fail, must advance nothing, and the next
        run must retry the receipt.
        """
        generation_before = graph_snapshot.acquire(self.root).generation
        with patch.object(graph_snapshot, "write_map_receipt", return_value=False):
            markdown = self.gen.generate_codebase_map(self.root)
        self.assertTrue(markdown)
        self.assertTrue(self._output().is_file())
        self.assertIsNone(graph_snapshot.read_map_receipt(self.root))
        self.assertEqual(graph_snapshot.acquire(self.root).generation,
                         generation_before,
                         "a derived-output receipt must never advance a generation")
        self.gen.generate_codebase_map(self.root)
        self.assertIsNotNone(graph_snapshot.read_map_receipt(self.root))

    def test_a_busy_writer_is_tolerated_rather_than_raised(self):
        """Hold the real write lock and assert the receipt write reports failure."""
        index_dir = self.root / ".wavefoundry" / "index"
        blocker = index_state_store.IndexStateStore(index_dir)
        try:
            blocker._conn.execute("BEGIN IMMEDIATE")
            blocker._conn.execute(
                "INSERT INTO meta (key, value) VALUES ('1xny6-probe','1') "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value")
            wrote = graph_snapshot.write_map_receipt(
                self.root, input_fingerprint="fp", graph_generation=1)
            self.assertFalse(wrote, "a contended write must report failure, not raise")
            blocker._conn.execute("ROLLBACK")
        finally:
            blocker.close()

    def test_the_receipt_write_itself_refuses_to_certify_backwards(self):
        """The conditional DO UPDATE, tested where it lives.

        The render path has its own pre-write abandon check, so exercising only
        that path leaves this guard unpinned: a stale writer that reached the
        database anyway -- a concurrent process, not a concurrent call -- would
        move ``graph_generation`` backwards unnoticed.
        """
        self.assertTrue(graph_snapshot.write_map_receipt(
            self.root, input_fingerprint="newer", graph_generation=7))
        self.assertFalse(
            graph_snapshot.write_map_receipt(
                self.root, input_fingerprint="older", graph_generation=6),
            "a stale generation must not report that it certified")
        stored = graph_snapshot.read_map_receipt(self.root)
        self.assertEqual(stored["input_fingerprint"], "newer")
        self.assertEqual(stored["graph_generation"], 7)
        # An equal generation is an ordinary idempotent re-render.
        self.assertTrue(graph_snapshot.write_map_receipt(
            self.root, input_fingerprint="same-generation", graph_generation=7))

    def test_the_receipt_never_creates_a_database_where_none_exists(self):
        """The map path must not turn a repository with no index into one with one."""
        empty = tempfile.TemporaryDirectory()
        self.addCleanup(empty.cleanup)
        bare = Path(empty.name)
        (bare / ".wavefoundry" / "index").mkdir(parents=True)
        self.assertFalse(graph_snapshot.write_map_receipt(
            bare, input_fingerprint="fp", graph_generation=1))
        self.assertEqual(
            sorted(p.name for p in (bare / ".wavefoundry" / "index").iterdir()), [],
            "the receipt write created index files in a repository with no index")

    def test_an_agents_md_change_alone_invalidates(self):
        """The non-graph half of the fingerprint survives the storage move.

        An area names the nearest ancestor ``AGENTS.md`` (1p66d), so both the
        per-area file and a project-root one reached by that walk are hashed by
        BYTES. Neither the appearance of the file nor an edit to its content
        touches the graph, so only this half can catch them.
        """
        model = self.gen.compute_areas(self.root)
        baseline = self.gen._fingerprint_inputs(self.root, "project", model)
        context = self.root / "src" / "AGENTS.md"
        context.parent.mkdir(parents=True, exist_ok=True)
        context.write_text("# src\n\nconventions\n", encoding="utf-8")
        appeared = self.gen._fingerprint_inputs(self.root, "project", model)
        self.assertNotEqual(baseline, appeared,
                            "an AGENTS.md appearing must invalidate the map")
        context.write_text("# src\n\nDIFFERENT conventions\n", encoding="utf-8")
        edited = self.gen._fingerprint_inputs(self.root, "project", model)
        self.assertNotEqual(appeared, edited,
                            "an AGENTS.md edit must invalidate the map")

    def test_force_refresh_bypasses_the_receipt(self):
        self.gen.generate_codebase_map(self.root)
        calls: list = []
        real_render = self.gen.render_markdown

        def spy(*a, **k):
            calls.append(1)
            return real_render(*a, **k)

        with patch.object(self.gen, "render_markdown", spy):
            self.gen.generate_codebase_map(self.root, force=True)
        self.assertTrue(calls, "force must bypass the unchanged-input skip")

    def test_unchanged_content_preserves_the_existing_date(self):
        self.gen.generate_codebase_map(self.root, last_verified="2020-01-01")
        original = self._output().read_text(encoding="utf-8")
        self.assertIn("2020-01-01", original)
        # Change a non-structural input so the render runs but the content
        # (modulo the date line) is identical.
        (self.root / "AGENTS.md").write_text("# root\n\nconventions\n",
                                             encoding="utf-8")
        self.gen.generate_codebase_map(self.root)
        self.assertIn("2020-01-01", self._output().read_text(encoding="utf-8"))

    def test_the_receipt_is_written_after_both_outputs(self):
        order: list[str] = []
        real_refresh = self.gen._refresh_repo_index_modules
        real_write = graph_snapshot.write_map_receipt

        def refresh_spy(*a, **k):
            order.append("repo_index")
            return real_refresh(*a, **k)

        def write_spy(*a, **k):
            order.append("receipt")
            return real_write(*a, **k)

        with patch.object(self.gen, "_refresh_repo_index_modules", refresh_spy), \
                patch.object(graph_snapshot, "write_map_receipt", write_spy):
            self.gen.generate_codebase_map(self.root)
        self.assertEqual(order[-2:], ["repo_index", "receipt"],
                         "the receipt must be written LAST")


class DashboardWalRefreshTests(_RootCase):
    """AC-5: the dashboard observes a COMMITTED generation before checkpointing."""

    def setUp(self):
        super().setUp()
        self.server = _load("dashboard_server")
        self._publish("a", "b")

    def _store(self):
        store = self.server.SnapshotStore.__new__(self.server.SnapshotStore)
        store._root = self.root
        return store

    def test_a_committed_generation_is_seen_while_it_still_lives_in_the_wal(self):
        index_dir = self.root / ".wavefoundry" / "index"
        database = index_paths.runtime_database_path(index_dir)
        store = self._store()
        before_signature = store._published_graph_signature()
        before_mtime = database.stat().st_mtime_ns

        # Commit a generation bump with auto-checkpoint DISABLED, so the change
        # is durable in the -wal and the main file is not rewritten.
        conn = index_state_store.IndexStateStore(index_dir)
        try:
            conn._conn.execute("PRAGMA wal_autocheckpoint=0")
        finally:
            conn.close()
        gfs.bump_generation(self.root)
        os.utime(database, ns=(before_mtime, before_mtime))

        after_mtime = database.stat().st_mtime_ns
        self.assertEqual(after_mtime, before_mtime,
                         "precondition: the main file's mtime did not move")
        # The pre-change watcher was a main-file mtime stat: it sees nothing.
        self.assertEqual(
            after_mtime, before_mtime,
            "an mtime-only watcher cannot observe a WAL-resident commit")
        # The published-generation signal does see it.
        after_signature = store._published_graph_signature()
        self.assertNotEqual(after_signature, before_signature)
        self.assertTrue(after_signature.startswith(
            str(graph_snapshot.acquire(self.root).generation) + ":"))

    def test_the_signal_is_part_of_the_watched_change_set(self):
        store = self._store()
        store._nested_signature = lambda base: ""
        store._watched_trees = lambda: []
        signals = store._current_mtimes()
        self.assertIn("graph::published", signals)
        self.assertNotIn(
            str(_retired_graph_dir(self.root) / "project-graph.json"), signals,
            "the retired artifact must not be watched any more")

    def test_an_absent_store_reads_as_absent_rather_than_raising(self):
        empty = tempfile.TemporaryDirectory()
        self.addCleanup(empty.cleanup)
        store = self.server.SnapshotStore.__new__(self.server.SnapshotStore)
        store._root = Path(empty.name)
        self.assertEqual(store._published_graph_signature(), "absent")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


class GraphFailureRecoveryTests(_RootCase):
    """1xoye AC-3: storage causes survive real consumer adapters and recovery."""

    def setUp(self):
        super().setUp()
        self.srv = _load("server_impl")
        self.gq = _load("graph_query")
        self.dash = _load("dashboard_lib")
        self.dashboard = _load("dashboard_server")
        self._publish("a", "b")

    def _calls(self):
        return (
            ("path", lambda: self.srv.code_graph_path_response(self.root, "a", "b")),
            ("impact", lambda: self.srv._code_impact_graph_response(self.root, "a")),
            ("callgraph", lambda: self.srv.code_callgraph_response(self.root, "a")),
            ("callhierarchy", lambda: self.srv.code_callhierarchy_response(self.root, "a")),
            ("risk", lambda: self.srv.code_risk_score_response(self.root, scope="src/")),
            ("report", lambda: self.srv.wf_graph_report_response(self.root)),
            ("community", lambda: self.srv.code_graph_community_response(self.root, "project:c0")),
        )

    def _assert_public_failure(self, code):
        query = self.gq.get_query_index(self.root)
        self.assertFalse(query.present)
        self.assertIsInstance(query.diagnostic, dict)
        self.assertEqual(query.diagnostic["code"], code)
        for name, call in self._calls():
            with self.subTest(consumer=name):
                result = call()
                self.assertEqual(result["status"], "error")
                self.assertEqual(result["diagnostics"][0]["code"], code)
                self.assertNotIn("index_build", result.get("next_tools", []))
                self.assertNotIn("mode='create'", result.get("usage", ""))
                recovery = ("wf_upgrade_status" if code == "storage_migration_required"
                            else "index_build_status" if code == "graph_publication_in_flight"
                            else "index_health")
                self.assertIn(recovery, result["next_tools"])
                self.assertEqual(result["usage"], recovery + "()")
        payload = self.dash.read_graph_payload(self.root, "project")
        self.assertFalse(payload["present"])
        self.assertIsInstance(payload.get("diagnostic"), dict)
        self.assertEqual(payload["diagnostic"]["code"], code)
        self.assertEqual(payload["clusters"]["diagnostic"]["code"], code)
        neighbors = self.dashboard._graph_neighbors_payload(self.root, layer="project", symbol="a")
        self.assertEqual(neighbors["diagnostic"], code)
        self.assertEqual(self.srv._graph_health_summary(self.root)["project"]["diagnostic"]["code"], code)

    def test_storage_faults_survive_public_consumers_with_both_caches_and_recover(self):
        import sqlite_runtime
        import sqlite_storage_migration as migration
        faults = (
            (index_state_store, "open_read_only", sqlite_runtime.RuntimeUnavailable("native binding unavailable"), "storage_runtime_unavailable"),
            (index_state_store, "open_read_only", sqlite_runtime.StorageRecoveryRequired("WAL filesystem refused"), "storage_recovery_required"),
            (migration, "require_ready", migration.MigrationRequired("storage_migration_required: resume retained checkpoint"), "storage_migration_required"),
        )
        for disabled in ("0", "1"):
            for module, seam, error, code in faults:
                with self.subTest(cache_disabled=disabled, code=code), patch.dict(os.environ, {
                    "WAVEFOUNDRY_DISABLE_GRAPH_QUERY_CACHE": disabled,
                    "WAVEFOUNDRY_DISABLE_GRAPH_SNAPSHOT_CACHE": disabled,
                }):
                    self.assertTrue(self.gq.get_query_index(self.root).present)
                    with patch.object(module, seam, side_effect=error), patch.object(
                            self.srv, "index_build_response") as rebuild, patch('wf_server.index_handlers.index_build_response') as index_rebuild:
                        self._assert_public_failure(code)
                        rebuild.assert_not_called()
                        index_rebuild.assert_not_called()
                    self.assertTrue(self.gq.get_query_index(self.root).present)
                    self.assertTrue(self.dash.read_graph_payload(self.root, "project")["present"])

    def test_inner_read_failure_is_typed_and_connection_closed(self):
        import sqlite_runtime
        real_open = index_state_store.open_read_only
        connections = []
        def opened(index_dir):
            conn = real_open(index_dir)
            connections.append(conn)
            return conn
        graph_snapshot.invalidate(self.root)
        with patch.object(index_state_store, "open_read_only", side_effect=opened), patch.object(
                graph_snapshot, "_community_fingerprint",
                side_effect=sqlite_runtime.StorageRecoveryRequired("read refused")):
            self._assert_public_failure("storage_recovery_required")
        self.assertTrue(connections)
        for conn in connections:
            with self.assertRaises(Exception):
                conn.execute("SELECT 1")

    def test_missing_and_inflight_have_distinct_recovery_and_watch_signatures(self):
        watcher = self.dashboard.SnapshotStore.__new__(self.dashboard.SnapshotStore)
        watcher._root = self.root
        ready = watcher._published_graph_signature()
        with contextlib.closing(index_state_store.IndexStateStore(graph_snapshot.index_dir_for(self.root))) as store:
            with store._conn:
                store._conn.execute("UPDATE build_state SET status='building' WHERE id=1")
        self._assert_public_failure("graph_publication_in_flight")
        pending = watcher._published_graph_signature()
        self.assertNotEqual(pending, ready)
        self._publish("a", "b")
        import sqlite_runtime
        with patch.object(index_state_store, "open_read_only", side_effect=sqlite_runtime.RuntimeUnavailable("missing")):
            failed = watcher._published_graph_signature()
        self.assertNotEqual(failed, pending)
        self.assertNotEqual(failed, watcher._published_graph_signature())
        missing = self.root / "unbuilt"
        missing.mkdir()
        absent = self.srv.code_graph_path_response(missing, "a", "b")
        self.assertEqual(absent["diagnostics"][0]["code"], "graph_not_ready")
        self.assertIn("index_build", absent["next_tools"])

    def test_registered_graph_resources_preserve_storage_recovery(self):
        from types import SimpleNamespace
        import sqlite_runtime
        captured = {}
        class Recorder:
            _tool_manager = SimpleNamespace(_tools={})
            def resource(self, uri, **kwargs):
                def deco(fn):
                    captured[fn.__name__] = fn
                    return fn
                return deco
            def tool(self, *args, **kwargs):
                def deco(fn):
                    self._tool_manager._tools[kwargs.get("name", fn.__name__)] = fn
                    return fn
                return deco(args[0]) if args and callable(args[0]) else deco
        self.srv.register_mcp_surface(Recorder(), lambda: SimpleNamespace(root=self.root))
        with patch.object(index_state_store, "open_read_only", side_effect=sqlite_runtime.RuntimeUnavailable("binding unavailable")):
            for name in ("resource_graph_status", "resource_graph_communities"):
                with self.subTest(resource=name):
                    text = captured[name]()
                    self.assertIn("storage_runtime_unavailable", text)
                    self.assertIn("wf setup", text)
                    self.assertNotIn("index_build(", text)

    def test_known_bad_exception_to_absence_is_detected(self):
        """Injected old behavior must fail the same public diagnostic assertion."""
        import sqlite_runtime
        with patch.object(index_state_store, "open_read_only", side_effect=sqlite_runtime.RuntimeUnavailable("missing")), patch.object(
                graph_snapshot, "_read_failure", side_effect=lambda layer, exc: graph_snapshot.GraphSnapshot(state=graph_snapshot.ABSENT, layer=layer)):
            result = self.srv.code_graph_path_response(self.root, "a", "b")
            with self.assertRaises(AssertionError):
                self.assertEqual(result["diagnostics"][0]["code"], "storage_runtime_unavailable")
            self.assertEqual(result["diagnostics"][0]["code"], "graph_not_ready")


    def test_read_failure_preserves_existing_map_and_receipt(self):
        """Legacy not-ready consumers must not certify an empty replacement."""
        import gen_codebase_map as gen
        import sqlite_runtime
        self.assertTrue(gen.generate_safe(self.root, verbose=False))
        output = gen.output_path(self.root)
        before = output.read_bytes()
        receipt = graph_snapshot.read_map_receipt(self.root)
        self.assertIsNotNone(receipt)
        with patch.object(index_state_store, "open_read_only",
                          side_effect=sqlite_runtime.RuntimeUnavailable("binding unavailable")):
            self.assertTrue(gen.generate_safe(self.root, verbose=False))
            self.assertEqual(output.read_bytes(), before)
        self.assertEqual(graph_snapshot.read_map_receipt(self.root), receipt)
