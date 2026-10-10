"""The single workflow-config include-prefix reader (change 2038p, AC-11)."""
from __future__ import annotations

import ast
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import workflow_include_prefixes as wip  # noqa: E402
import contained_files  # noqa: E402
from framework_files import source_path  # noqa: E402

SCRIPTS = ".wavefoundry/framework/scripts"


class WorkflowIncludePrefixReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _read(self, data) -> dict:
        cfg = self.root / "docs" / "workflow-config.json"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
        return wip.read_project_include_prefixes(self.root)

    def _indexing(self, indexing) -> dict:
        return self._read({"indexing": indexing})

    def test_missing_file_yields_empty_layers(self):
        self.assertEqual(wip.read_project_include_prefixes(self.root), {"docs": (), "code": ()})

    def test_per_layer_dict(self):
        result = self._indexing({"project_include_prefixes": {
            "docs": ["docs/external"], "code": [SCRIPTS, "vendor/docs"]}})
        self.assertEqual(result, {"docs": ("docs/external",), "code": (SCRIPTS, "vendor/docs")})

    def test_list_shorthand_applies_to_both_layers(self):
        result = self._indexing({"project_include_prefixes": [SCRIPTS, "vendor/docs"]})
        self.assertEqual(result, {"docs": (SCRIPTS, "vendor/docs"), "code": (SCRIPTS, "vendor/docs")})

    def test_legacy_boolean_maps_to_scripts_only_when_code_is_empty(self):
        self.assertEqual(self._indexing({"include_framework_code_for_code_search": True}),
                         {"docs": (), "code": (SCRIPTS,)})
        self.assertEqual(self._indexing({"include_framework_code_for_code_search": True,
                                         "project_include_prefixes": {"code": ["src"]}}),
                         {"docs": (), "code": ("src",)})
        self.assertEqual(self._indexing({"include_framework_code_for_code_search": False}),
                         {"docs": (), "code": ()})

    def test_tokens_are_normalized_and_deduplicated_in_order(self):
        result = self._indexing({"project_include_prefixes": {
            "code": [" /vendor\\docs/ ", "vendor/docs", "", "  ", "/", "src/"]}})
        self.assertEqual(result["code"], ("vendor/docs", "src"))

    def test_malformed_values_never_raise_or_split_into_characters(self):
        cases = {
            "string value for a layer": {"project_include_prefixes": {"docs": "docs/x", "code": SCRIPTS}},
            "dict value for a layer": {"project_include_prefixes": {"code": {"a": "b"}}},
            "string shorthand": {"project_include_prefixes": SCRIPTS},
            "number shorthand": {"project_include_prefixes": 7},
            "null shorthand": {"project_include_prefixes": None},
        }
        for label, indexing in cases.items():
            with self.subTest(label):
                self.assertEqual(self._indexing(indexing), {"docs": (), "code": ()})

    def test_non_string_items_are_skipped(self):
        result = self._indexing({"project_include_prefixes": {
            "docs": [1, None, ["nested"], {"k": "v"}, "docs/ok", True], "code": [3.5, SCRIPTS]}})
        self.assertEqual(result, {"docs": ("docs/ok",), "code": (SCRIPTS,)})

    def test_malformed_file_or_indexing_block_yields_empty_layers(self):
        for label, raw in {
            "invalid json": "{not json",
            "top-level list": "[1, 2]",
            "indexing is a list": json.dumps({"indexing": ["src"]}),
            "indexing is a string": json.dumps({"indexing": "src"}),
        }.items():
            with self.subTest(label):
                self.assertEqual(self._read(raw), {"docs": (), "code": ()})

    def test_undecodable_bytes_yield_empty_layers(self):
        cfg = self.root / "docs" / "workflow-config.json"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_bytes(b"\xff\xfe\x00{")
        self.assertEqual(wip.read_project_include_prefixes(self.root), {"docs": (), "code": ()})

    def test_exact_byte_cap_is_accepted_and_one_more_is_refused(self):
        self._indexing({"project_include_prefixes": ["src"]})
        cfg = self.root / "docs" / "workflow-config.json"
        data = cfg.read_bytes()
        cfg.write_bytes(data + b" " * (8 * 1024 * 1024 - len(data)))
        self.assertEqual(wip.read_project_include_prefixes(self.root), {"docs": ("src",), "code": ("src",)})
        with cfg.open("ab") as stream:
            stream.write(b" ")
        self.assertEqual(wip.read_project_include_prefixes(self.root), {"docs": (), "code": ()})

    def test_contained_link_is_supported_and_external_link_is_refused(self):
        self._indexing({"project_include_prefixes": ["src"]})
        cfg = self.root / "docs" / "workflow-config.json"
        target = self.root / "inside.json"
        cfg.rename(target)
        cfg.symlink_to(target)
        self.assertEqual(wip.read_project_include_prefixes(self.root)["code"], ("src",))
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / "config.json"
            external.write_bytes(target.read_bytes())
            cfg.unlink()
            cfg.symlink_to(external)
            self.assertEqual(wip.read_project_include_prefixes(self.root), {"docs": (), "code": ()})

    def test_special_and_runtime_lock_targets_are_refused_before_read(self):
        self._read({})
        cfg = self.root / "docs" / "workflow-config.json"
        cfg.unlink()
        if hasattr(os, "mkfifo"):
            os.mkfifo(cfg)
            # A regression to read_text must fail immediately instead of hanging.
            with patch.object(Path, "read_text", side_effect=AssertionError("following read")):
                self.assertEqual(wip.read_project_include_prefixes(self.root), {"docs": (), "code": ()})
            cfg.unlink()
        lock = self.root / ".wavefoundry" / "lifecycle-mutation.lock"
        lock.parent.mkdir(parents=True)
        lock.write_text('{"indexing":{"project_include_prefixes":["src"]}}')
        os.link(lock, cfg)
        self.assertEqual(wip.read_project_include_prefixes(self.root), {"docs": (), "code": ()})

    def test_config_replaced_between_judgment_and_open_is_refused(self):
        self._indexing({"project_include_prefixes": ["original"]})
        cfg = self.root / "docs" / "workflow-config.json"
        original_open = contained_files._open_verified
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / "config.json"
            external.write_text('{"indexing":{"project_include_prefixes":["outside"]}}')
            def replace_then_open(*args):
                cfg.unlink()
                cfg.symlink_to(external)
                return original_open(*args)
            with patch.object(contained_files, "_open_verified", side_effect=replace_then_open) as opened:
                self.assertEqual(wip.read_project_include_prefixes(self.root), {"docs": (), "code": ()})
            opened.assert_called_once()
            self.assertIn("outside", external.read_text())

    def test_utf16_json_does_not_change_the_utf8_fallback(self):
        self._read({})
        cfg = self.root / "docs" / "workflow-config.json"
        cfg.write_bytes('{"indexing":{"project_include_prefixes":["src"]}}'.encode("utf-16"))
        self.assertEqual(wip.read_project_include_prefixes(self.root), {"docs": (), "code": ()})


class SingleReaderOwnershipTests(unittest.TestCase):
    """One bootstrap-safe reader; only its contained-files leaf may be non-stdlib."""

    def _tree(self, name: str) -> ast.Module:
        return ast.parse(source_path(name).read_text(encoding="utf-8"))

    def test_reader_module_imports_only_stdlib_and_the_contained_leaf(self):
        imported: set[str] = set()
        for node in ast.walk(self._tree("workflow_include_prefixes.py")):
            if isinstance(node, ast.Import):
                imported |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        imported.discard("__future__")
        allowed = set(sys.stdlib_module_names) | {"contained_files"}
        self.assertIn("contained_files", imported)
        self.assertTrue(imported <= allowed, imported - allowed)
        leaf_imports = set()
        for node in ast.walk(self._tree("contained_files.py")):
            if isinstance(node, ast.Import):
                leaf_imports.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                leaf_imports.add((node.module or "").split(".")[0])
        leaf_imports.discard("__future__")
        self.assertTrue(leaf_imports <= set(sys.stdlib_module_names), leaf_imports - set(sys.stdlib_module_names))

    def test_setup_and_indexer_define_no_prefix_coercion_of_their_own(self):
        for name in ("setup_index.py", "indexer.py"):
            defined = {n.name for n in ast.walk(self._tree(name)) if isinstance(n, ast.FunctionDef)}
            with self.subTest(name):
                self.assertFalse(defined & {"_coerce_prefix_list", "_merge_project_include_prefixes"})
        setup_defs = {n.name for n in ast.walk(self._tree("setup_index.py")) if isinstance(n, ast.FunctionDef)}
        self.assertNotIn("_workflow_project_include_prefixes", setup_defs)

    def test_setup_has_no_module_level_indexer_import(self):
        for node in self._tree("setup_index.py").body:
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            self.assertNotIn("indexer", names)

    def test_indexer_reader_delegates_to_the_module(self):
        import importlib.util
        from unittest.mock import patch

        spec = importlib.util.spec_from_file_location("indexer_for_reader_test", source_path("indexer"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sentinel = {"docs": ("d",), "code": ("c",)}
        with patch.object(mod.workflow_include_prefixes, "read_project_include_prefixes",
                          return_value=sentinel) as reader:
            self.assertIs(mod._workflow_project_include_prefixes(Path("/r")), sentinel)
        reader.assert_called_once_with(Path("/r"))
        self.assertEqual(mod._normalize_prefixes((" /a\\b/ ", "a/b", "")), ("a/b",))


if __name__ == "__main__":
    unittest.main()
