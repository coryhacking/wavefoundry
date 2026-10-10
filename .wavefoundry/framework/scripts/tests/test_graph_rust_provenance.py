"""Rust graph identity and expression spans, checked through published MCP reads.

Expected spans come from exact fixture expressions, independently of the parser.
The driver runs the real extraction, merge and SQLite publication path.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_graph_incremental_merge import _RepoDriver, load_graph_indexer
from server_tools_support import load_server
import graph_fixture_support as gfs
import graph_snapshot
import index_state_store


PATH = "src/profiles.rs"
SAME_NAMES = '''struct Profile;
struct Version;
impl Profile { fn as_str(&self) -> &str { "profile" } }
impl Version { fn as_str(&self) -> &str { "version" } }
fn neighbor(profile: Profile) { profile.as_str(); }
fn execute(profile: Profile, version: Version) {
    let _label = "évidence"; println!("{}", version.as_str());
    profile.as_str();
    profile.as_str();
}
'''
TRAITS = '''struct Profile;
struct Role;
impl FromStr for Profile { fn from_str() -> Self { Profile } }
impl FromStr for Role { fn from_str() -> Self { Role } }
fn read() { Profile::from_str(); Role::from_str(); }
'''


def expected_site(source: str, expression: str, occurrence: int = 0) -> dict:
    """Source oracle: byte and point coordinates of an explicitly named call."""
    raw = source.encode("utf-8")
    token = expression.encode("utf-8")
    start = -1
    for _ in range(occurrence + 1):
        start = raw.index(token, start + 1)
    end = start + len(token)
    return {
        "source_file": PATH, "start_byte": start, "end_byte": end,
        "line": raw[:start].count(b"\n") + 1,
        "column": start - (raw.rfind(b"\n", 0, start) + 1) + 1,
        "end_line": raw[:end].count(b"\n") + 1,
        "end_column": end - (raw.rfind(b"\n", 0, end) + 1) + 1,
    }


class RustPublishedProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = load_graph_indexer()
        cls.srv = load_server()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.addCleanup(graph_snapshot.invalidate, self.root)
        self.driver = _RepoDriver(self.g, self.root)

    def build(self, source):
        tree = self.g._ts_parse("rust", source)
        self.assertIsNotNone(tree, "Rust grammar is required for this regression")
        self.assertFalse(tree.root_node.has_error)
        self.driver.write(PATH, source)
        # The merge driver owns rows; the build coordinator owns the epoch.
        # Exercise both canonical producers, including the per-file cache.
        attempt = index_state_store.begin_build_epoch(self.driver.index_dir, "graph")
        payload = self.driver.build_incremental({PATH})
        self.assertTrue(index_state_store.finalize_build_epoch(self.driver.index_dir, attempt))
        return payload

    def response(self, caller="execute"):
        result = self.srv.code_callgraph_response(
            self.root, f"{PATH}::{caller}", direction="callees", include_tests=True)
        self.assertEqual(result["status"], "ok", result)
        return result["data"]

    def edge(self, edges, caller, target):
        found = [e for e in edges if e.get("relation") == "calls"
                 and e.get("source") == f"{PATH}::{caller}"
                 and e.get("target") == f"{PATH}::{target}"]
        self.assertEqual(len(found), 1, found)
        return found[0]

    def assert_spans(self, edges, source=SAME_NAMES):
        profile = self.edge(edges, "execute", "Profile.as_str")
        version = self.edge(edges, "execute", "Version.as_str")
        self.assertEqual(profile["confidence"], "RECEIVER_RESOLVED")
        self.assertEqual(version["confidence"], "RECEIVER_RESOLVED")
        # The earlier neighbor call is outside execute's caller boundary.
        self.assertEqual(profile.get("call_sites"), [expected_site(source, "profile.as_str()", 1),
                                                     expected_site(source, "profile.as_str()", 2)])
        self.assertEqual(version.get("call_sites"), [expected_site(source, "version.as_str()")])

    def test_exact_receiver_spans_survive_extraction_storage_and_public_projection(self):
        payload = self.build(SAME_NAMES)
        self.assert_spans(payload["edges"])
        stored = graph_snapshot.acquire(self.root)
        self.assertTrue(stored.ready)
        self.assert_spans(stored.graph["edges"])
        public = self.response()
        self.assert_spans(public["edges"])
        self.assertEqual(self.edge(public["edges"], "execute", "Profile.as_str")["line"], 8)
        self.assertEqual(self.edge(public["edges"], "execute", "Version.as_str")["line"], 7)

    def test_distinct_trait_targets_and_locations_reach_public_callgraph(self):
        payload = self.build(TRAITS)
        ids = {n["id"] for n in payload["nodes"]}
        expected = ("<Profile as FromStr>.from_str", "<Role as FromStr>.from_str")
        self.assertTrue(all(f"{PATH}::{name}" in ids for name in expected), ids)
        self.assertNotIn(f"{PATH}::FromStr.from_str", ids)
        public = self.response("read")
        for name, expression in zip(expected, ("Profile::from_str()", "Role::from_str()")):
            with self.subTest(target=name):
                edge = self.edge(public["edges"], "read", name)
                self.assertEqual(edge.get("call_sites"), [expected_site(TRAITS, expression)])
                self.assertEqual(edge["line"], 5)

    def test_incremental_edit_replaces_occurrences_and_matches_fresh_build(self):
        self.build(SAME_NAMES)
        old = copy.deepcopy(graph_snapshot.acquire(self.root).graph)
        edited = SAME_NAMES.replace("    profile.as_str();\n    profile.as_str();",
                                    "    // shifted call\n    profile.as_str();")
        incremental = self.build(edited)
        fresh = self.driver.build_oracle()
        calls = lambda p: sorted((e["source"], e["target"], e["confidence"],
                                  json.dumps(e.get("call_sites", []), sort_keys=True))
                                 for e in p["edges"] if e["relation"] == "calls")
        self.assertEqual(calls(incremental), calls(fresh))
        expected = [expected_site(edited, "profile.as_str()", 1)]
        self.assertEqual(self.edge(self.response()["edges"], "execute", "Profile.as_str")["call_sites"], expected)
        self.assertEqual(len(self.edge(old["edges"], "execute", "Profile.as_str")["call_sites"]), 2)

    def test_projecting_or_mutating_response_cannot_modify_shared_occurrences(self):
        self.build(SAME_NAMES)
        snapshot = graph_snapshot.acquire(self.root)
        before = copy.deepcopy(snapshot.graph)
        public = self.response()
        self.assertEqual(snapshot.graph, before)
        self.edge(public["edges"], "execute", "Profile.as_str")["call_sites"][0]["line"] = 999
        self.assertEqual(snapshot.graph, before)
        self.assertEqual(self.edge(self.response()["edges"], "execute", "Profile.as_str")["line"], 8)

    def test_missing_provenance_never_scans_same_name_for_a_precise_line(self):
        # Old or non-Rust producers may prove a relationship without a span.
        (self.root / "src").mkdir()
        (self.root / PATH).write_text(SAME_NAMES, encoding="utf-8")
        nodes = [{"id": f"{PATH}::{name}", "label": name.rsplit(".", 1)[-1],
                  "kind": "function", "source_file": PATH, "source_location": "6:0"}
                 for name in ("execute", "Profile.as_str")]
        gfs.publish_graph(self.root, nodes=nodes, edges=[{
            "source": f"{PATH}::execute", "target": f"{PATH}::Profile.as_str",
            "relation": "calls", "confidence": "RECEIVER_RESOLVED"}])
        edge = self.edge(self.response()["edges"], "execute", "Profile.as_str")
        self.assertEqual(edge.get("call_sites"), [])
        self.assertNotIn("line", edge)
        self.assertEqual(edge["confidence"], "RECEIVER_RESOLVED")

    def test_non_rust_target_and_confidence_are_preserved_without_guessed_location(self):
        self.driver.write("src/plain.py", "def helper(): pass\ndef run(): helper()\n")
        payload = self.driver.build_incremental({"src/plain.py"})
        expected = [(e["source"], e["target"], e["confidence"])
                    for e in payload["edges"] if e["relation"] == "calls"]
        result = self.srv.code_callgraph_response(
            self.root, "src/plain.py::run", direction="callees", include_tests=True)
        self.assertEqual(result["status"], "ok", result)
        calls = [e for e in result["data"]["edges"] if e["relation"] == "calls"]
        self.assertEqual([(e["source"], e["target"], e["confidence"]) for e in calls], expected)
        for edge in calls:
            self.assertEqual(edge.get("call_sites"), [])
            self.assertNotIn("line", edge)

    def test_previous_builder_cached_calls_are_reextracted_even_without_changed_paths(self):
        self.driver.write(PATH, SAME_NAMES)
        real_extract = self.g.GraphIndexSession._extract_tree_sitter_artifact

        def old_representation(session, *args, **kwargs):
            artifact = real_extract(session, *args, **kwargs)
            for edge in artifact["edges"]:
                edge.pop("call_sites", None)
            return artifact

        # Produce a predecessor-version cache with unchanged source hashes.
        with patch.object(self.g, "GRAPH_BUILDER_VERSION", "53"), \
                patch.object(self.g.GraphIndexSession, "_extract_tree_sitter_artifact", old_representation):
            stale = self.driver.build_incremental({PATH})
        self.assertEqual(self.g.read_state_builder_version(self.driver.index_dir), "53")
        self.assertTrue(all(not e.get("call_sites") for e in stale["edges"]))
        with patch.object(self.g.GraphIndexSession, "_extract_tree_sitter_artifact", autospec=True,
                          side_effect=real_extract) as extraction:
            rebuilt = self.driver.build_incremental(set())
        self.assertGreater(extraction.call_count, 0, "the old file cache must not be reused")
        self.assertEqual(rebuilt["builder_version"], "54")
        self.assertEqual(self.g.read_state_builder_version(self.driver.index_dir), "54")
        self.assert_spans(rebuilt["edges"])
        fresh = self.driver.build_oracle()
        self.assert_spans(fresh["edges"])
        self.assertEqual({n["id"] for n in rebuilt["nodes"]}, {n["id"] for n in fresh["nodes"]})

    def test_failed_previous_builder_rebuild_returns_not_ready_instead_of_old_relationships(self):
        nodes = [{"id": f"{PATH}::{name}", "label": name, "kind": "function", "source_file": PATH}
                 for name in ("execute", "FromStr.from_str")]
        gfs.publish_graph(self.root, nodes=nodes, builder_version="53", edges=[{
            "source": f"{PATH}::execute", "target": f"{PATH}::FromStr.from_str",
            "relation": "calls", "confidence": "EXTRACTED"}])
        real_spec = importlib.util.spec_from_file_location

        class FailedBuildLoader:
            def create_module(self, spec):
                return None

            def exec_module(self, module):
                module.build_index = lambda *args, **kwargs: {"failed": True, "failure": "injected publication failure"}

        def rebuild_spec(name, *args, **kwargs):
            if name == "indexer_for_graph_query_rebuild":
                return importlib.util.spec_from_loader(name, FailedBuildLoader())
            return real_spec(name, *args, **kwargs)

        with patch.object(importlib.util, "spec_from_file_location", side_effect=rebuild_spec):
            result = self.srv.code_callgraph_response(
                self.root, f"{PATH}::execute", direction="callees", include_tests=True)
        self.assertEqual(result["status"], "error", result)
        self.assertFalse(result["data"].get("edges"))
        self.assertIn("graph_auto_rebuild_failed", json.dumps(result))
        snapshot = graph_snapshot.acquire(self.root)
        self.assertEqual(snapshot.builder_version, "53", "failure preserves the previous generation")

    def test_pinned_response_keeps_its_occurrences_when_new_generation_lands(self):
        self.build(SAME_NAMES)
        with graph_snapshot.pinned(self.root) as pinned:
            before = copy.deepcopy(pinned.graph)
            edited = SAME_NAMES.replace("    profile.as_str();", "    // delay\n    profile.as_str();", 1)
            self.build(edited)
            self.assertIs(graph_snapshot.acquire(self.root), pinned)
            self.assertEqual(pinned.graph, before)
            self.assert_spans(self.response()["edges"])
        public = self.response()
        self.assertEqual(self.edge(public["edges"], "execute", "Profile.as_str")["call_sites"],
                         [expected_site(edited, "profile.as_str()", 1), expected_site(edited, "profile.as_str()", 2)])


if __name__ == "__main__":
    unittest.main()
