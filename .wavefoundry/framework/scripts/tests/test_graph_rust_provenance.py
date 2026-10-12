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


def expected_site(source: str, expression: str, occurrence: int = 0, *, source_file: str = PATH) -> dict:
    """Source oracle: byte and point coordinates of an explicitly named call."""
    raw = source.encode("utf-8")
    token = expression.encode("utf-8")
    start = -1
    for _ in range(occurrence + 1):
        start = raw.index(token, start + 1)
    end = start + len(token)
    return {
        "source_file": source_file, "start_byte": start, "end_byte": end,
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
        # Legacy or degraded producers may prove a relationship without a span.
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

    def test_non_rust_target_and_confidence_preserve_exact_persisted_location(self):
        source = "def helper(): pass\ndef run(): helper()\n"
        self.driver.write("src/plain.py", source)
        payload = self.driver.build_incremental({"src/plain.py"})
        expected = [(e["source"], e["target"], e["confidence"])
                    for e in payload["edges"] if e["relation"] == "calls"]
        result = self.srv.code_callgraph_response(
            self.root, "src/plain.py::run", direction="callees", include_tests=True)
        self.assertEqual(result["status"], "ok", result)
        calls = [e for e in result["data"]["edges"] if e["relation"] == "calls"]
        self.assertEqual([(e["source"], e["target"], e["confidence"]) for e in calls], expected)
        self.assertEqual(len(calls), 1)
        self.assertEqual(expected, [("src/plain.py::run", "src/plain.py::helper", "RECEIVER_RESOLVED")])
        site = expected_site(source, "helper()", 1, source_file="src/plain.py")
        self.assertEqual(calls[0].get("call_sites"), [site])
        self.assertEqual(calls[0]["line"], site["line"])

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
        self.assertEqual(rebuilt["builder_version"], "56")
        self.assertEqual(self.g.read_state_builder_version(self.driver.index_dir), "56")
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


class RustCratePathTests(unittest.TestCase):
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

    def build(self, files, removed=()):
        for path, source in files.items():
            tree = self.g._ts_parse("rust", source)
            self.assertIsNotNone(tree, "Rust grammar is required")
            self.assertFalse(tree.root_node.has_error, source)
            self.driver.write(path, source)
        for path in removed:
            self.driver.delete(path)
        attempt = index_state_store.begin_build_epoch(self.driver.index_dir, "graph")
        payload = self.driver.build_incremental(set(files), set(removed))
        self.assertTrue(index_state_store.finalize_build_epoch(self.driver.index_dir, attempt))
        return payload

    @staticmethod
    def calls(payload):
        return sorted((e["source"], e["target"], e["confidence"],
                       json.dumps(e.get("call_sites", []), sort_keys=True))
                      for e in payload["edges"] if e["relation"] == "calls")

    def response(self, symbol, direction="callees"):
        result = self.srv.code_callgraph_response(
            self.root, symbol, direction=direction, include_tests=True)
        self.assertEqual(result["status"], "ok", result)
        return [e for e in result["data"]["edges"] if e["relation"] == "calls"]

    def targets(self, payload, caller):
        return {e["target"] for e in payload["edges"]
                if e["relation"] == "calls" and e["source"] == caller}

    def test_crate_paths_aliases_inline_and_published_repeated_sites(self):
        source = '''mod left; mod right;
use crate::left::ping as left_ping;
pub fn run() { left_ping(); crate::right::ping(); left_ping(); crate::right::ping(); }
pub mod inline { pub fn ping() {} }
pub fn nested() { crate::inline::ping(); }
'''
        payload = self.build({"src/lib.rs": source, "src/left.rs": "pub fn ping() {}",
                              "src/right.rs": "pub fn ping() {}"})
        self.assertEqual(self.targets(payload, "src/lib.rs::run"),
                         {"src/left.rs::ping", "src/right.rs::ping"})
        self.assertEqual(self.targets(payload, "src/lib.rs::nested"), {"src/lib.rs::inline.ping"})
        for target, expression in [("src/left.rs::ping", "left_ping()"),
                                   ("src/right.rs::ping", "crate::right::ping()")]:
            expected = [expected_site(source, expression, n, source_file="src/lib.rs") for n in (0, 1)]
            outgoing = [e for e in self.response("src/lib.rs::run") if e["target"] == target]
            incoming = [e for e in self.response(target, "callers") if e["source"] == "src/lib.rs::run"]
            self.assertEqual(len(outgoing), 1)
            self.assertEqual(len(incoming), 1)
            for edge in outgoing + incoming:
                self.assertEqual(edge["call_sites"], expected)
                self.assertEqual(edge["confidence"], "RECEIVER_RESOLVED")
                self.assertFalse(any(k.startswith("_rust") for k in edge))

    def test_alias_scope_shadow_and_external_import_refuse_local_twins(self):
        source = '''mod left;
use crate::left::ping as chosen;
pub fn positive() { chosen(); }
pub fn parameter(chosen: fn()) { chosen(); }
pub fn local() { let chosen = || {}; chosen(); }
pub fn local_item() { fn chosen() {} chosen(); }
pub fn captured() { let chosen = || {}; let closure = || chosen(); closure(); }
pub fn closure_parameter() { let closure = |chosen: fn()| chosen(); }
pub fn untyped_closure() { let closure: fn(fn()) = |chosen| { chosen(); }; closure(replace); }
pub fn other() { use crate::left::ping as elsewhere; elsewhere(); }
pub fn sibling(elsewhere: fn()) { elsewhere(); }
pub fn nonproject() { use std::mem::replace as imported_replace; let mut x = 0; imported_replace(&mut x, 1); }
pub fn replace() {}
pub mod child { pub fn nested(chosen: fn()) { chosen(); } }
'''
        payload = self.build({"src/lib.rs": source, "src/left.rs": "pub fn ping() {}"})
        self.assertEqual(self.targets(payload, "src/lib.rs::positive"), {"src/left.rs::ping"})
        self.assertEqual(self.targets(payload, "src/lib.rs::other"), {"src/left.rs::ping"})
        for caller in ("parameter", "local", "local_item", "captured", "closure_parameter", "untyped_closure", "sibling", "nonproject", "child.nested"):
            targets = self.targets(payload, "src/lib.rs::" + caller)
            self.assertTrue(targets, caller)
            self.assertTrue(all(t.startswith("external::") for t in targets), (caller, targets))

    def test_hoisted_imports_initializer_scope_and_module_boundaries(self):
        source = '''mod left; use crate::left::ping as chosen;
fn first() { chosen(); let chosen = { chosen(); || {} }; chosen(); }
fn hoisted() { nested(); use crate::left::ping as nested; }
fn block() { { use crate::left::ping as nested; nested(); } nested(); }
mod child { pub fn call() { chosen(); } }
fn elsewhere() { use crate::left::ping as chosen; chosen(); }
'''
        payload = self.build({"src/lib.rs": source, "src/left.rs": "pub fn ping() {}"})
        self.assertEqual(self.targets(payload, "src/lib.rs::first"), {"src/left.rs::ping", "external::chosen"})
        self.assertEqual(self.targets(payload, "src/lib.rs::hoisted"), {"src/left.rs::ping"})
        self.assertEqual(self.targets(payload, "src/lib.rs::block"), {"src/left.rs::ping", "external::nested"})
        self.assertEqual(self.targets(payload, "src/lib.rs::child.call"), {"external::chosen"})

    def test_pattern_bindings_refuse_alias_but_preserve_sibling_else_and_outer_sites(self):
        source = '''mod left;
use crate::left::ping as chosen;
use crate::left::ping as witness;
pub fn matched(arg: Option<fn()>) {
    match arg { Some(chosen) if { chosen(); witness(); true } => chosen(), _ => chosen() }
    chosen();
}
pub fn conditional(arg: Option<fn()>) {
    if let Some(chosen) = { chosen(); arg } { chosen(); } else { chosen(); }
    chosen();
}
pub fn repeated(arg: Option<fn()>) {
    while let Some(chosen) = arg { chosen(); break; }
    chosen();
}
pub fn chained(arg: Option<fn()>) {
    if let Some(chosen) = { chosen(); arg } && { chosen(); true } { chosen(); } else { chosen(); }
    chosen();
}
'''
        payload = self.build({"src/lib.rs": source, "src/left.rs": "pub fn ping() {}"})
        # Expected source occurrences prove the exact arm/body boundary, not
        # merely that one resolved and one unresolved edge happen to exist.
        expected = {"matched": ([0, 1], [2, 3]),
                    "conditional": ([5], [4, 6, 7]), "repeated": ([8], [9]),
                    "chained": ([11, 12], [10, 13, 14])}
        for caller, (shadowed, imported) in expected.items():
            edges = self.response("src/lib.rs::" + caller)
            self.assertEqual({e["target"] for e in edges}, {"external::chosen", "src/left.rs::ping"})
            for target, occurrences in [("external::chosen", shadowed), ("src/left.rs::ping", imported)]:
                edge = next(e for e in edges if e["target"] == target)
                sites = [expected_site(source, "chosen()", i, source_file="src/lib.rs") for i in occurrences]
                if caller == "matched" and target == "src/left.rs::ping":
                    sites.append(expected_site(source, "witness()", source_file="src/lib.rs"))
                self.assertEqual(edge["call_sites"], sorted(sites, key=lambda site: site["start_byte"]))
        self.assertEqual(self.calls(payload), self.calls(self.driver.build_oracle()))

    def test_missing_ambiguous_and_non_free_targets_never_use_leaf_fallback(self):
        cases = [
            ({"src/lib.rs": "fn call(){crate::missing::ping();} fn ping() {}"}, "src/lib.rs::call"),
            ({"src/lib.rs": "mod left; fn call(){crate::left::absent();} fn absent() {}",
              "src/left.rs": "pub fn ping() {}"}, "src/lib.rs::call"),
            ({"src/loose.rs": "fn call(){crate::left::ping();}", "src/left.rs": "pub fn ping() {}"}, "src/loose.rs::call"),
            ({"src/lib.rs": "mod left; fn call(){crate::left::ping();}",
              "src/left.rs": "pub fn ping() {}", "src/left/mod.rs": "pub fn ping() {}"}, "src/lib.rs::call"),
            ({"src/lib.rs": "mod left; mod left; fn call(){crate::left::ping();}",
              "src/left.rs": "pub fn ping() {}"}, "src/lib.rs::call"),
            ({"src/lib.rs": "mod left {pub fn ping(){}} mod left {pub fn ping(){}} fn call(){crate::left::ping();}"}, "src/lib.rs::call"),
            ({"src/lib.rs": "mod left {pub fn ping(){}} mod left; fn call(){crate::left::ping();}",
              "src/left.rs": "pub fn ping() {}"}, "src/lib.rs::call"),
            ({"src/lib.rs": "mod left; fn call(){crate::left::ping();}",
              "src/left.rs": "pub fn ping() {} pub fn ping() {}"}, "src/lib.rs::call"),
            ({"src/lib.rs": "struct Thing; impl Thing {fn ping(){}} fn call(){crate::Thing::ping();}"}, "src/lib.rs::call"),
        ]
        for files, caller in cases:
            with self.subTest(files=files):
                removed = set(self.driver.files) - set(files)
                payload = self.build(files, removed)
                targets = self.targets(payload, caller)
                self.assertTrue(targets)
                self.assertTrue(all(t.startswith("external::") for t in targets), targets)
                self.assertEqual(self.calls(payload), self.calls(self.driver.build_oracle()))

    def test_multiple_crates_do_not_cross_bind_and_shared_ownership_refuses(self):
        payload = self.build({
            "a/lib.rs": "mod left; fn run(){crate::left::ping();}",
            "a/left.rs": "pub fn ping() {}",
            "b/lib.rs": "mod left; fn run(){crate::left::ping();}",
            "b/left.rs": "pub fn ping() {}",
        })
        self.assertEqual(self.targets(payload, "a/lib.rs::run"), {"a/left.rs::ping"})
        self.assertEqual(self.targets(payload, "b/lib.rs::run"), {"b/left.rs::ping"})
        payload = self.build({"a/main.rs": "mod left; fn run(){crate::left::ping();}"})
        self.assertEqual(self.targets(payload, "a/lib.rs::run"), {"external::crate.left.ping"})
        self.assertEqual(self.targets(payload, "b/lib.rs::run"), {"b/left.rs::ping"})
        self.assertEqual(self.calls(payload), self.calls(self.driver.build_oracle()))

    def test_callee_and_topology_changes_reresolve_untouched_published_callers(self):
        source = "use crate::left::ping as chosen; pub fn run(){chosen(); chosen(); crate::left::ping();}"
        files = {"src/lib.rs": "mod left; mod caller;", "src/left.rs": "pub fn ping() {}",
                 "src/caller.rs": source, "src/other.rs": "pub fn ping() {}"}
        self.build(files)
        steps = [({}, ["src/left.rs"], "external::crate.left.ping"),
                 ({"src/left.rs": files["src/left.rs"]}, [], "src/left.rs::ping"),
                 ({"src/lib.rs": 'mod caller; #[path="other.rs"] mod left;'}, [], "src/other.rs::ping"),
                 ({"src/lib.rs": "mod caller;"}, [], "external::crate.left.ping"),
                 ({"src/lib.rs": files["src/lib.rs"]}, [], "src/left.rs::ping"),
                 ({"src/main.rs": "mod caller; mod left;"}, [], "external::crate.left.ping"),
                 ({}, ["src/main.rs"], "src/left.rs::ping")]
        for changed, removed, expected in steps:
            with self.subTest(changed=changed, removed=removed):
                payload = self.build(changed, removed)
                self.assertEqual(self.targets(payload, "src/caller.rs::run"), {expected})
                self.assertEqual(self.calls(payload), self.calls(self.driver.build_oracle()))
                edges = self.response("src/caller.rs::run")
                self.assertEqual({e["target"] for e in edges}, {expected})
                self.assertEqual(edges[0]["call_sites"], [
                    expected_site(source, "chosen()", i, source_file="src/caller.rs") for i in (0, 1)
                ] + [expected_site(source, "crate::left::ping()", source_file="src/caller.rs")])

    def test_context_built_once_per_changed_merge_and_never_zero_change(self):
        files = {"src/lib.rs": "mod left; fn call(){crate::left::ping();}", "src/left.rs": "pub fn ping() {}"}
        with patch.object(self.g, "_build_rust_crate_context", wraps=self.g._build_rust_crate_context) as build:
            self.build(files)
            self.assertEqual(build.call_count, 1)
            self.assertIn("src/lib.rs", build.call_args.args[0])
            build.reset_mock()
            self.build({"src/left.rs": "pub fn ping() { let _x = 1; }"})
            self.assertEqual(build.call_count, 1)
            self.assertIn("src/lib.rs", build.call_args.args[0])
            build.reset_mock()
            self.driver.build_incremental(set())
            self.assertEqual(build.call_count, 0)

    def test_type_new_convention_is_preserved_but_module_new_is_a_free_call(self):
        source = '''mod caller; struct Profile;
impl Profile { fn new() -> Self { Profile } fn method() {} }
mod module {pub fn new(){}}
mod Upper {pub fn new(){}}
fn call(){crate::Profile::new(); crate::module::new(); crate::Upper::new(); crate::Profile::method();}
'''
        payload = self.build({"src/lib.rs": source,
                              "src/caller.rs": "pub fn run(){crate::Upper::new();}"})
        self.assertEqual(self.targets(payload, "src/lib.rs::call"), {
            "src/lib.rs::Profile", "src/lib.rs::module.new", "src/lib.rs::Upper.new", "external::crate.Profile.method"})
        constructor = next(e for e in payload["edges"] if e["relation"] == "calls" and e["target"] == "src/lib.rs::Profile")
        self.assertEqual(constructor["confidence"], "CONSTRUCTION_RESOLVED")
        self.assertEqual(self.targets(payload, "src/caller.rs::run"), {"src/lib.rs::Upper.new"})

    def test_builder_55_fragments_refresh_crate_binding_without_source_changes(self):
        files = {"src/lib.rs": "mod left; mod right; fn call(){crate::left::ping();}",
                 "src/left.rs": "pub fn ping() {}", "src/right.rs": "pub fn ping() {}"}
        with patch.object(self.g, "GRAPH_BUILDER_VERSION", "55"), \
                patch.object(self.g._RustLexicalFacts, "free_call", return_value=None):
            old = self.build(files)
        self.assertEqual(self.targets(old, "src/lib.rs::call"), {"external::ping"})
        real_extract = self.g.GraphIndexSession._extract_tree_sitter_artifact
        with patch.object(self.g.GraphIndexSession, "_extract_tree_sitter_artifact", autospec=True,
                          side_effect=real_extract) as extraction:
            fresh = self.driver.build_incremental(set())
        self.assertEqual(extraction.call_count, len(files))
        self.assertEqual(fresh["builder_version"], "56")
        self.assertEqual(self.targets(fresh, "src/lib.rs::call"), {"src/left.rs::ping"})
        self.assertEqual(self.calls(fresh), self.calls(self.driver.build_oracle()))

    def test_cross_file_type_new_keeps_exact_constructor_and_incremental_identity(self):
        files = {"src/lib.rs": "mod types; mod caller; mod constructors;",
                 "src/types.rs": "pub struct Profile;",
                 "src/constructors.rs": "use crate::types::Profile; impl Profile {pub fn new()->Self{Profile}}",
                 "src/caller.rs": "pub fn run(){crate::types::Profile::new();}"}
        payload = self.build(files)
        self.assertEqual(self.targets(payload, "src/caller.rs::run"), {"src/types.rs::Profile"})
        edge = next(e for e in payload["edges"] if e["relation"] == "calls")
        self.assertEqual(edge["confidence"], "CONSTRUCTION_RESOLVED")
        for body, target in [("pub struct Other;", "external::crate.types.Profile.new"),
                             (files["src/types.rs"], "src/types.rs::Profile")]:
            payload = self.build({"src/types.rs": body})
            self.assertEqual(self.targets(payload, "src/caller.rs::run"), {target})
            self.assertEqual(self.calls(payload), self.calls(self.driver.build_oracle()))

    def test_module_path_overrides_refuse_escape_absolute_drive_and_backslash(self):
        for override, decoy in [("../../outside.rs", "outside.rs"),
                                ("/outside.rs", "src/outside.rs"),
                                ("C:/outside.rs", "src/outside.rs"),
                                ("other\\outside.rs", "src/other/outside.rs")]:
            with self.subTest(override=override):
                files = {"src/lib.rs": '#[path="' + override + '"] mod left; fn call(){crate::left::ping();}',
                         decoy: "pub fn ping() {}"}
                payload = self.build(files, set(self.driver.files) - set(files))
                self.assertEqual(self.targets(payload, "src/lib.rs::call"), {"external::crate.left.ping"})


if __name__ == "__main__":
    unittest.main()
