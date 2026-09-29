"""Code navigation under a stale or missing index runtime (wave 1za2y, change 1z9u7).

The walker never falls back to an unfiltered walk. With a stale runtime every
tool that reaches it answers from the loaded indexer and carries an
``index_runtime_stale`` warning; with no indexer it returns an error, never an
empty-result success.
"""
from __future__ import annotations

import ast
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from server_tools_support import _make_repo, load_server, load_thin_runner  # noqa: E402

SYMBOL = "NAVPROBE_SYMBOL"

# Every public tool whose handler reaches the navigation walker without a
# graph index, with arguments that make it walk.
TOOL_CALLS = {
    "code_list_files": {},
    "code_keyword": {"query": SYMBOL},
    "code_constants": {"symbols": [SYMBOL]},
    "code_pattern": {"pattern": SYMBOL},
    "code_definition": {"symbol_or_path_position": SYMBOL},
    "code_references": {"symbol_or_path_position": SYMBOL},
    "code_impact": {"path": "app.py"},
}


def _codes(result):
    return [d.get("code") for d in (result.get("diagnostics") or []) if isinstance(d, dict)]


class _Surface(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name))
        (self.root / ".gitignore").write_text(".wavefoundry/index/\n", encoding="utf-8")
        (self.root / "app.py").write_text(f"{SYMBOL} = 1\n\nprint({SYMBOL})\n", encoding="utf-8")
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        (index_dir / "index.sqlite").write_bytes(b"SQLite format 3\x00" + f"{SYMBOL} = 2\n".encode())
        self.impl = load_server()
        self.runner = load_thin_runner()
        self.mcp = self.runner.build_server(self.root)
        self.addCleanup(lambda: self.runner._get_handler().close())
        import index_compatibility
        self.ic = index_compatibility
        # A private copy of the producer sources, so a test can make the
        # runtime stale without touching the real framework files.
        self.sources = Path(self.tmp.name) / "producer-sources"
        self.sources.mkdir()
        for name in self.ic._SOURCE_NAMES:
            shutil.copy2(self.ic._SOURCE_ROOT / f"{name}.py", self.sources / f"{name}.py")
        root_patch = mock.patch.object(self.ic, "_SOURCE_ROOT", self.sources)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self.impl._RUNTIME_SIGNATURE_CACHE.update(signature=None, stale=False)

    def call(self, name, args):
        return self.mcp._tool_manager._tools[name].fn(**args)

    def make_stale(self):
        (self.sources / "chunker.py").write_text("# edited after the runtime loaded\n", encoding="utf-8")

    def assert_no_leak(self, result):
        text = repr(result)
        self.assertNotIn(".wavefoundry/index", text)
        self.assertNotIn("SQLite format", text)


class StaleRuntimeTests(_Surface):
    def test_every_tool_keeps_filtered_files_and_warns(self):
        self.make_stale()
        for name, args in TOOL_CALLS.items():
            with self.subTest(tool=name):
                result = self.call(name, args)
                self.assert_no_leak(result)
                self.assertIn("index_runtime_stale", _codes(result), result)
                self.assertNotEqual(result.get("status"), "error", result)

    def test_listing_matches_a_current_runtime(self):
        current = self.call("code_list_files", {})
        self.make_stale()
        stale = self.call("code_list_files", {})
        self.assertEqual(current["data"], stale["data"])
        self.assertIn("app.py", repr(current["data"]))

    def test_current_runtime_adds_no_diagnostic(self):
        for name, args in TOOL_CALLS.items():
            with self.subTest(tool=name):
                result = self.call(name, args)
                self.assertNotIn("index_runtime_stale", _codes(result))
                self.assertNotIn("navigation_indexer_unavailable", _codes(result))
                self.assert_no_leak(result)


class MissingIndexerTests(_Surface):
    def test_every_tool_errors_without_a_file_list(self):
        original = self.impl._load_script

        def refuse_indexer(name):
            if name == "indexer":
                raise RuntimeError("index_runtime_stale: indexer: fixture")
            return original(name)

        with mock.patch.object(self.impl, "_load_script", refuse_indexer), \
                mock.patch.dict(sys.modules, {self.impl._LAST_GOOD_INDEXER_KEY: None}):
            sys.modules.pop(self.impl._LAST_GOOD_INDEXER_KEY, None)
            for name, args in TOOL_CALLS.items():
                with self.subTest(tool=name):
                    result = self.call(name, args)
                    self.assertEqual(result.get("status"), "error", result)
                    self.assertIn("navigation_indexer_unavailable", _codes(result))
                    self.assertNotIn("app.py", repr(result.get("data")))

    def test_the_last_good_indexer_serves_when_a_fresh_load_fails(self):
        last_good = self.impl._indexer_module()

        def refuse(name):
            raise RuntimeError("index_runtime_stale")

        self.impl._script_cache.clear()
        with mock.patch.object(self.impl, "_load_script", refuse):
            self.assertIs(self.impl._indexer_module(), last_good)


class SharedModuleTests(_Surface):
    def test_indexer_module_is_the_cached_load(self):
        self.assertIs(self.impl._indexer_module(), self.impl._load_script("indexer"))

    def test_server_start_loads_the_indexer(self):
        # Clear what setUp's build already loaded, then run only the surface
        # registration, so the load observed here is the startup call itself.
        from mcp.server.fastmcp import FastMCP

        self.impl._script_cache.pop("_wavefoundry_indexer", None)
        with mock.patch.dict(sys.modules):
            sys.modules.pop(self.impl._LAST_GOOD_INDEXER_KEY, None)
            self.impl.register_mcp_surface(FastMCP("startup-probe"), self.runner._get_handler)
            self.assertIn("_wavefoundry_indexer", self.impl._script_cache)
            self.assertIn(self.impl._LAST_GOOD_INDEXER_KEY, sys.modules)

    def test_no_fresh_indexer_load_and_no_unfiltered_fallback_remain(self):
        for path in sorted((SCRIPTS / "wf_server").glob("*.py")):
            source = path.read_text(encoding="utf-8")
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "spec_from_file_location":
                    self.assertNotIn("indexer", ast.unparse(node), f"{path.name}: fresh indexer load")
        walker = ast.get_source_segment(
            (SCRIPTS / "wf_server" / "server_impl.py").read_text(encoding="utf-8"),
            next(
                n for n in ast.parse((SCRIPTS / "wf_server" / "server_impl.py").read_text(encoding="utf-8")).body
                if isinstance(n, ast.FunctionDef) and n.name == "_walk_repo_for_navigation"
            ),
        )
        self.assertNotIn("rglob", walker)


class FreshnessCacheTests(_Surface):
    def test_unchanged_signatures_do_not_rehash(self):
        calls = []
        real = self.ic.ensure_runtime_current

        def counting():
            calls.append(1)
            return real()

        with mock.patch.object(self.ic, "ensure_runtime_current", counting):
            self.assertFalse(self.impl._index_runtime_stale())
            self.assertFalse(self.impl._index_runtime_stale())
            self.assertEqual(len(calls), 1)
            self.make_stale()
            self.assertTrue(self.impl._index_runtime_stale())
            self.assertEqual(len(calls), 2)


class WrapperMechanismTests(unittest.TestCase):
    """Any wrapped tool that reaches the walker gets the notices, including
    tools that reach it only after a graph lookup."""

    def test_notices_follow_the_walker_not_the_tool_name(self):
        impl = load_server()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")

            def fake_tool(**kwargs):
                files = impl._walk_repo_for_navigation(root)
                return impl._response("ok", {"count": len(files)})

            table = {"code_callgraph": mock.Mock(fn=fake_tool)}
            surface = mock.Mock()
            surface._tool_manager._tools = table
            impl._wrap_setup_notice(surface, lambda: mock.Mock(_setup_assessment_result=None))
            with mock.patch.object(impl, "_index_runtime_stale", return_value=True):
                result = table["code_callgraph"].fn()
            self.assertIn("index_runtime_stale", _codes(result))


if __name__ == "__main__":
    unittest.main()
