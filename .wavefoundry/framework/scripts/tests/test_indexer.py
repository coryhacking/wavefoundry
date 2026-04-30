from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
INDEXER_PATH = SCRIPTS_ROOT / "indexer.py"


def load_build_index():
    spec = importlib.util.spec_from_file_location("indexer", INDEXER_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["indexer"] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_embedder_mock(dim: int = 4):
    """Return a mock embedder whose .embed() yields zero vectors of given dimension."""
    import numpy as np

    def fake_embed(texts):
        for _ in texts:
            yield np.zeros(dim, dtype=np.float32)

    mock = MagicMock()
    mock.embed.side_effect = fake_embed
    return mock


def _make_repo(tmp: Path, files: dict[str, str]) -> None:
    """Write files into a temp repo with a minimal workflow-config.json."""
    (tmp / "docs").mkdir(parents=True, exist_ok=True)
    (tmp / "docs" / "workflow-config.json").write_text(
        json.dumps({"lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0}}),
        encoding="utf-8",
    )
    for rel, content in files.items():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


class FileWalkerTests(unittest.TestCase):
    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_walks_python_and_markdown(self):
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "docs/guide.md": "# Guide\n\nContent.\n",
        })
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertIn("foo.py", names)
        self.assertIn("guide.md", names)

    def test_excludes_git_directory(self):
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        git_file = self.root / ".git" / "config"
        git_file.parent.mkdir(parents=True, exist_ok=True)
        git_file.write_text("git config", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        self.assertFalse(any(".git" in str(f) for f in files))

    def test_excludes_node_modules(self):
        _make_repo(self.root, {
            "src/foo.py": "x = 1\n",
            "node_modules/pkg/index.js": "module.exports = {};\n",
        })
        files = self.bi.walk_repo(self.root)
        self.assertFalse(any("node_modules" in str(f) for f in files))

    def test_excludes_pycache(self):
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        cache = self.root / "src" / "__pycache__" / "foo.cpython-312.pyc"
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(b"\x00")
        files = self.bi.walk_repo(self.root)
        self.assertFalse(any("__pycache__" in str(f) for f in files))

    def test_excludes_binary_extensions(self):
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        (self.root / "src" / "image.png").write_bytes(b"\x89PNG")
        (self.root / "src" / "data.npy").write_bytes(b"\x93NUMPY")
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertNotIn("image.png", names)
        self.assertNotIn("data.npy", names)

    def test_respects_gitignore(self):
        _make_repo(self.root, {
            "src/foo.py": "x = 1\n",
            "build/output.js": "var x = 1;\n",
        })
        (self.root / ".gitignore").write_text("build/\n", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        self.assertFalse(any("build" in str(f) for f in files))

    def test_respects_aiignore(self):
        _make_repo(self.root, {
            "src/foo.py": "x = 1\n",
            "secret/keys.txt": "token=abc\n",
        })
        (self.root / ".aiignore").write_text("secret/\n", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        self.assertFalse(any("secret" in str(f) for f in files))

    def test_excludes_wavefoundry_index(self):
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        idx = self.root / ".wavefoundry" / "index"
        idx.mkdir(parents=True, exist_ok=True)
        (idx / "docs.json").write_text("[]", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        self.assertFalse(any(".wavefoundry/index" in str(f).replace("\\", "/") for f in files))

    def test_returns_paths_with_forward_slashes_in_hashes(self):
        _make_repo(self.root, {"src/sub/foo.py": "x = 1\n"})
        files = self.bi.walk_repo(self.root)
        hashes = self.bi._build_file_hashes(files, self.root)
        for key in hashes:
            self.assertNotIn("\\", key)


class CodeFileFilterTests(unittest.TestCase):
    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_code_filter_defaults_to_source_files_only(self):
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "src/config.json": "{}\n",
            "docs/guide.md": "# Guide\n\n```python\nprint('example')\n```\n",
            "tests/test_foo.py": "def test_f(): pass\n",
            ".claude/hooks/post-edit.py": "def hook(): pass\n",
            "notes.txt": "not source code\n",
        })

        files = self.bi.walk_repo(self.root)
        filtered = self.bi._filter_code_files(
            files,
            self.root,
            include_tests=False,
            include_generated=False,
        )
        paths = {str(path.relative_to(self.root)).replace("\\", "/") for path in filtered}

        self.assertIn("src/foo.py", paths)
        self.assertIn("src/config.json", paths)
        self.assertNotIn("docs/guide.md", paths)
        self.assertNotIn("tests/test_foo.py", paths)
        self.assertNotIn(".claude/hooks/post-edit.py", paths)
        self.assertNotIn("notes.txt", paths)

    def test_code_filter_can_include_tests_and_generated_files(self):
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "tests/test_foo.py": "def test_f(): pass\n",
            ".claude/hooks/post-edit.py": "def hook(): pass\n",
        })

        files = self.bi.walk_repo(self.root)
        filtered = self.bi._filter_code_files(
            files,
            self.root,
            include_tests=True,
            include_generated=True,
        )
        paths = {str(path.relative_to(self.root)).replace("\\", "/") for path in filtered}

        self.assertIn("src/foo.py", paths)
        self.assertIn("tests/test_foo.py", paths)
        self.assertIn(".claude/hooks/post-edit.py", paths)

    def test_code_filter_always_excludes_framework_internal_tests(self):
        _make_repo(self.root, {
            ".wavefoundry/framework/scripts/indexer.py": "def build_index(): pass\n",
            ".wavefoundry/framework/scripts/tests/test_indexer.py": "def test_build_index(): pass\n",
        })

        files = self.bi.walk_repo(self.root)
        filtered = self.bi._filter_code_files(
            files,
            self.root,
            include_tests=True,
            include_generated=True,
        )
        paths = {str(path.relative_to(self.root)).replace("\\", "/") for path in filtered}

        self.assertIn(".wavefoundry/framework/scripts/indexer.py", paths)
        self.assertNotIn(".wavefoundry/framework/scripts/tests/test_indexer.py", paths)


class HashTests(unittest.TestCase):
    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_same_content_same_hash(self):
        p = self.root / "f.py"
        p.write_text("x = 1\n", encoding="utf-8")
        h1 = self.bi._sha256(p)
        h2 = self.bi._sha256(p)
        self.assertEqual(h1, h2)

    def test_different_content_different_hash(self):
        p = self.root / "f.py"
        p.write_text("x = 1\n", encoding="utf-8")
        h1 = self.bi._sha256(p)
        p.write_text("x = 2\n", encoding="utf-8")
        h2 = self.bi._sha256(p)
        self.assertNotEqual(h1, h2)


class IncrementalBuildTests(unittest.TestCase):
    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run_build(self, full: bool = False) -> dict:
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            return self.bi.build_index(self.root, full=full, content="all", verbose=False)

    def test_full_build_produces_index_files(self):
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        result = self._run_build(full=True)
        index_dir = self.root / ".wavefoundry" / "index"
        self.assertTrue((index_dir / "meta.json").exists())
        self.assertTrue((index_dir / "docs.json").exists())
        self.assertTrue((index_dir / "code.json").exists())
        self.assertFalse(result["up_to_date"])

    def test_second_run_is_up_to_date(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        # Second run — no changes, no embedder calls needed
        result = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertTrue(result["up_to_date"])
        self.assertEqual(result["files_indexed"], 0)

    def test_incremental_only_reindexes_changed_file(self):
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "src/bar.py": "def g(): pass\n",
        })
        self._run_build(full=True)

        # Modify one file
        (self.root / "src" / "foo.py").write_text("def f(): return 1\n", encoding="utf-8")

        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            result = self.bi.build_index(self.root, full=False, content="all", verbose=False)

        self.assertEqual(result["files_indexed"], 1)

    def test_meta_records_file_hashes(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        meta = json.loads((self.root / ".wavefoundry" / "index" / "meta.json").read_text())
        self.assertIn("file_hashes", meta)
        self.assertIn("src/foo.py", meta["file_hashes"])

    def test_meta_records_model_versions(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        meta = json.loads((self.root / ".wavefoundry" / "index" / "meta.json").read_text())
        self.assertIn("docs", meta["model_versions"])
        self.assertIn("code", meta["model_versions"])

    def test_full_flag_ignores_existing_meta(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        # Force full again — should reindex even though nothing changed
        result = self._run_build(full=True)
        self.assertFalse(result["up_to_date"])
        self.assertGreater(result["files_indexed"], 0)

    def test_removed_file_chunks_excluded_from_index(self):
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "src/bar.py": "def g(): pass\n",
        })
        self._run_build(full=True)

        (self.root / "src" / "bar.py").unlink()

        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            self.bi.build_index(self.root, full=False, content="all", verbose=False)

        code_chunks = json.loads((self.root / ".wavefoundry" / "index" / "code.json").read_text())
        paths = {c["path"] for c in code_chunks}
        self.assertNotIn("src/bar.py", paths)

    def test_chunks_json_paths_use_forward_slashes(self):
        _make_repo(self.root, {"src/sub/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        code_chunks = json.loads((self.root / ".wavefoundry" / "index" / "code.json").read_text())
        for c in code_chunks:
            self.assertNotIn("\\", c["path"])
            self.assertNotIn("\\", c["id"])

    def test_npy_row_count_matches_chunks_json(self):
        import numpy as np
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\ndef g(): pass\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        self._run_build(full=True)
        index_dir = self.root / ".wavefoundry" / "index"
        code_chunks = json.loads((index_dir / "code.json").read_text())
        docs_chunks = json.loads((index_dir / "docs.json").read_text())
        code_npy = index_dir / "code.npy"
        docs_npy = index_dir / "docs.npy"
        if code_chunks and code_npy.exists():
            self.assertEqual(np.load(str(code_npy)).shape[0], len(code_chunks))
        if docs_chunks and docs_npy.exists():
            self.assertEqual(np.load(str(docs_npy)).shape[0], len(docs_chunks))

    def test_custom_index_dir_is_excluded_from_rebuild_hashes(self):
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nHello.\n",
            "framework/seeds/example.md": "## Seed\n\nExample.\n",
        })
        index_dir = self.root / "framework" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        (index_dir / "stale.json").write_text('{"old": true}', encoding="utf-8")

        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            self.bi.build_index(
                self.root,
                full=True,
                content="docs",
                index_dir=index_dir,
                include_prefixes=("framework",),
                verbose=False,
            )

        meta = json.loads((index_dir / "meta.json").read_text())
        self.assertIn("framework/seeds/example.md", meta["file_hashes"])
        self.assertNotIn("framework/index/stale.json", meta["file_hashes"])

    def test_default_project_index_excludes_framework_source(self):
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nHello.\n",
            ".wavefoundry/framework/README.md": "## Framework\n\nCanonical framework docs.\n",
        })

        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            self.bi.build_index(self.root, full=True, content="docs", verbose=False)

        index_dir = self.root / ".wavefoundry" / "index"
        meta = json.loads((index_dir / "meta.json").read_text())
        chunks = json.loads((index_dir / "docs.json").read_text())
        self.assertIn("docs/guide.md", meta["file_hashes"])
        self.assertNotIn(".wavefoundry/framework/README.md", meta["file_hashes"])
        self.assertFalse(any(c["path"].startswith(".wavefoundry/framework/") for c in chunks))

    def test_explicit_framework_index_can_include_framework_source(self):
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nHello.\n",
            ".wavefoundry/framework/README.md": "## Framework\n\nCanonical framework docs.\n",
        })

        index_dir = self.root / ".wavefoundry" / "framework" / "index"
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            self.bi.build_index(
                self.root,
                full=True,
                content="docs",
                index_dir=index_dir,
                include_prefixes=(".wavefoundry/framework",),
                respect_ignore=False,
                verbose=False,
            )

        meta = json.loads((index_dir / "meta.json").read_text())
        chunks = json.loads((index_dir / "docs.json").read_text())
        self.assertIn(".wavefoundry/framework/README.md", meta["file_hashes"])
        self.assertTrue(any(c["path"] == ".wavefoundry/framework/README.md" for c in chunks))


class ModelVersionChangeTests(unittest.TestCase):
    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_model_version_change_triggers_full_rebuild(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        # Write stale meta with old model name
        (index_dir / "meta.json").write_text(
            json.dumps({
                "model_versions": {"docs": "old-model", "code": "old-model"},
                "file_hashes": {},
            }),
            encoding="utf-8",
        )
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            result = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertFalse(result["up_to_date"])
        self.assertGreater(result["files_indexed"], 0)


class OnnxProviderSelectionTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_build_index()

    def _providers(self, system: str, machine: str, available: list[str]) -> list[str]:
        with patch("platform.system", return_value=system), \
             patch("platform.machine", return_value=machine), \
             patch("onnxruntime.get_available_providers", return_value=available):
            return self.mod._onnx_providers()

    def test_apple_silicon_prefers_coreml(self):
        providers = self._providers("Darwin", "arm64", ["CoreMLExecutionProvider", "CPUExecutionProvider"])
        self.assertEqual(providers[0], "CoreMLExecutionProvider")
        self.assertIn("CPUExecutionProvider", providers)

    def test_apple_silicon_falls_back_to_cpu_without_coreml(self):
        providers = self._providers("Darwin", "arm64", ["CPUExecutionProvider"])
        self.assertEqual(providers, ["CPUExecutionProvider"])

    def test_cuda_used_on_non_apple(self):
        providers = self._providers("Linux", "x86_64", ["CUDAExecutionProvider", "CPUExecutionProvider"])
        self.assertEqual(providers[0], "CUDAExecutionProvider")
        self.assertIn("CPUExecutionProvider", providers)

    def test_cpu_only_fallback(self):
        providers = self._providers("Linux", "x86_64", ["CPUExecutionProvider"])
        self.assertEqual(providers, ["CPUExecutionProvider"])

    def test_coreml_not_used_on_intel_mac(self):
        providers = self._providers("Darwin", "x86_64", ["CoreMLExecutionProvider", "CPUExecutionProvider"])
        self.assertEqual(providers, ["CPUExecutionProvider"])

    def test_onnxruntime_import_error_returns_cpu(self):
        with patch.dict("sys.modules", {"onnxruntime": None}):
            result = self.mod._onnx_providers()
        self.assertEqual(result, ["CPUExecutionProvider"])


if __name__ == "__main__":
    unittest.main()
