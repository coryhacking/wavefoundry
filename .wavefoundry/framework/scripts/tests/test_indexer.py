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

    def fake_embed(texts, batch_size=256):
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

    def test_excludes_elf_and_office_binaries(self):
        # AC-1 (12c7n-bug binary-files-indexed-as-text): ELF, EPS, PPTX excluded
        _make_repo(self.root, {"src/app.py": "x = 1\n"})
        (self.root / "src" / "app").write_bytes(b"\x7fELF\x02\x01\x01")
        (self.root / "src" / "slide.pptx").write_bytes(b"PK\x03\x04")
        (self.root / "src" / "logo.eps").write_bytes(b"%!PS-Adobe-3.0 EPSF-3.0\n")
        (self.root / "src" / "icon.png").write_bytes(b"\x89PNG\r\n")
        (self.root / "src" / "diagram.svg").write_bytes(b"<svg></svg>")
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertIn("app.py", names)
        self.assertNotIn("slide.pptx", names)
        self.assertNotIn("logo.eps", names)
        self.assertNotIn("icon.png", names)
        self.assertNotIn("diagram.svg", names)

    def test_excludes_null_byte_unknown_extension(self):
        # AC-3 (12c7n-bug binary-files-indexed-as-text): null-byte sniff for unknown extensions
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        # Use .myext — not in any known binary or text list
        (self.root / "src" / "data.myext").write_bytes(b"\x00\x01\x02binary data here")
        (self.root / "src" / "config.myext").write_text("key=value\n", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertNotIn("data.myext", names)
        self.assertIn("config.myext", names)

    def test_excludes_lock_files(self):
        # AC-1..AC-3 (12c7n-bug generated-lock-files-indexed): lock files excluded
        _make_repo(self.root, {
            "package.json": '{"name":"app"}',
            "src/index.ts": "export {};",
        })
        (self.root / "package-lock.json").write_text('{"lockfileVersion":3}', encoding="utf-8")
        (self.root / "yarn.lock").write_text("# yarn lockfile\n", encoding="utf-8")
        (self.root / "pnpm-lock.yaml").write_text("lockfileVersion: '6.0'\n", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertNotIn("package-lock.json", names)
        self.assertNotIn("yarn.lock", names)
        self.assertNotIn("pnpm-lock.yaml", names)
        self.assertIn("package.json", names)

    def test_excludes_snap_and_excalidraw(self):
        # AC-4, AC-5 (12c7n-bug generated-lock-files-indexed): snapshots and diagrams excluded
        _make_repo(self.root, {"src/foo.ts": "export {};", "src/bar.json": "{}"}),
        (self.root / "src" / "Component.test.ts.snap").write_text("{}", encoding="utf-8")
        (self.root / "src" / "diagram.excalidraw").write_text("{}", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertNotIn("Component.test.ts.snap", names)
        self.assertNotIn("diagram.excalidraw", names)
        self.assertIn("foo.ts", names)
        self.assertIn("bar.json", names)

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

    def test_returns_paths_with_forward_slashes(self):
        _make_repo(self.root, {"src/sub/foo.py": "x = 1\n"})
        files = self.bi.walk_repo(self.root)
        for f in files:
            rel = str(f.relative_to(self.root)).replace("\\", "/")
            self.assertNotIn("\\", rel)

    def test_excludes_dot_dirs_blanket(self):
        """All dot-prefix dirs except .wavefoundry are excluded, at any depth."""
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        for dot_dir in (".idea", ".vscode", ".cursor", ".claude", ".codex", ".github"):
            d = self.root / dot_dir
            d.mkdir(parents=True, exist_ok=True)
            (d / "settings.json").write_text("{}", encoding="utf-8")
        # Also test nested: a dot-dir inside a non-dot dir
        nested = self.root / "src" / ".idea"
        nested.mkdir(parents=True, exist_ok=True)
        (nested / "workspace.xml").write_text("<project/>", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        rel_strs = {str(f.relative_to(self.root)).replace("\\", "/") for f in files}
        for dot_dir in (".idea", ".vscode", ".cursor", ".claude", ".codex", ".github"):
            self.assertFalse(
                any(s.startswith(dot_dir + "/") for s in rel_strs),
                f"{dot_dir} should be excluded",
            )
        self.assertNotIn("src/.idea/workspace.xml", rel_strs, "nested .idea should be excluded")

    def test_wavefoundry_dir_still_walked(self):
        """Files under .wavefoundry/ are not excluded by the blanket dot-dir rule."""
        _make_repo(self.root, {
            "src/foo.py": "x = 1\n",
            ".wavefoundry/config.json": '{"ok": true}\n',
        })
        files = self.bi.walk_repo(self.root)
        rel_strs = {str(f.relative_to(self.root)).replace("\\", "/") for f in files}
        self.assertIn(".wavefoundry/config.json", rel_strs)

    def test_excludes_env_files(self):
        """.env and .env.* files are excluded (secrets risk)."""
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        (self.root / ".env").write_text("SECRET=abc\n", encoding="utf-8")
        (self.root / ".env.local").write_text("LOCAL=xyz\n", encoding="utf-8")
        (self.root / ".env.production").write_text("PROD=123\n", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertNotIn(".env", names)
        self.assertNotIn(".env.local", names)
        self.assertNotIn(".env.production", names)

    def test_includes_txt_files(self):
        """.txt files pass through the walker."""
        _make_repo(self.root, {
            "src/foo.py": "x = 1\n",
            "docs/notes.txt": "Some notes.\n",
        })
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertIn("notes.txt", names)

    def test_includes_extensionless_readme(self):
        """README and other extensionless docs filenames pass through the walker."""
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        for name in ("README", "LICENSE", "CHANGELOG", "CONTRIBUTING", "NOTICE"):
            (self.root / name).write_text(f"# {name}\n", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        for name in ("README", "LICENSE", "CHANGELOG", "CONTRIBUTING", "NOTICE"):
            self.assertIn(name, names, f"{name} should be included")

    def test_new_code_extensions_in_source_set(self):
        """AC-7: .xml, .graphql, .gql, .proto, .sql are in SOURCE_CODE_EXTENSIONS."""
        for ext in (".xml", ".graphql", ".gql", ".proto", ".sql"):
            self.assertIn(ext, self.bi.SOURCE_CODE_EXTENSIONS, f"{ext} missing from SOURCE_CODE_EXTENSIONS")


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
        # .claude/ is excluded by the blanket dot-dir walker rule, so generated
        # files under .claude/ never reach _filter_code_files regardless of include_generated.
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "tests/test_foo.py": "def test_f(): pass\n",
            "generated/output.py": "def gen(): pass\n",
        })
        # write generated/output.py with a generated-code prefix pattern via a non-dot dir
        (self.root / "generated" / "output.py").write_text("def gen(): pass\n", encoding="utf-8")

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

    def test_build_file_hashes_returns_rel_path_to_hex(self):
        (self.root / "a.py").write_text("hello\n", encoding="utf-8")
        (self.root / "sub").mkdir()
        (self.root / "sub" / "b.md").write_text("world\n", encoding="utf-8")
        files = [self.root / "a.py", self.root / "sub" / "b.md"]
        result = self.bi._build_file_hashes(files, self.root)
        self.assertEqual(set(result.keys()), {"a.py", "sub/b.md"})
        for v in result.values():
            self.assertRegex(v, r"^[0-9a-f]{64}$")

    def test_build_file_hashes_consistent_with_sha256(self):
        p = self.root / "c.py"
        p.write_text("data\n", encoding="utf-8")
        result = self.bi._build_file_hashes([p], self.root)
        self.assertEqual(result["c.py"], self.bi._sha256(p))


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

    def test_meta_records_file_meta(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        meta = json.loads((self.root / ".wavefoundry" / "index" / "meta.json").read_text())
        self.assertIn("file_meta", meta)
        self.assertIn("src/foo.py", meta["file_meta"])
        self.assertNotIn("file_hashes", meta)

    def test_meta_records_file_meta_with_stat_fields(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        meta = json.loads((self.root / ".wavefoundry" / "index" / "meta.json").read_text())
        self.assertIn("file_meta", meta)
        entry = meta["file_meta"].get("src/foo.py")
        self.assertIsNotNone(entry)
        self.assertIn("hash", entry)
        self.assertIn("mtime", entry)
        self.assertIn("size", entry)
        self.assertIn("inode", entry)

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
        self.assertIn("framework/seeds/example.md", meta["file_meta"])
        self.assertNotIn("framework/index/stale.json", meta["file_meta"])

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
        self.assertIn("docs/guide.md", meta["file_meta"])
        self.assertNotIn(".wavefoundry/framework/README.md", meta["file_meta"])
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
        self.assertIn(".wavefoundry/framework/README.md", meta["file_meta"])
        self.assertTrue(any(c["path"] == ".wavefoundry/framework/README.md" for c in chunks))

    def test_project_docs_index_can_opt_in_excluded_prefixes(self):
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nHello.\n",
            ".wavefoundry/framework/README.md": "## Framework\n\nCanonical framework docs.\n",
        })

        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            self.bi.build_index(
                self.root,
                full=True,
                content="docs",
                project_include_prefixes=(".wavefoundry/framework",),
                verbose=False,
            )

        index_dir = self.root / ".wavefoundry" / "index"
        meta = json.loads((index_dir / "meta.json").read_text())
        chunks = json.loads((index_dir / "docs.json").read_text())
        self.assertIn(".wavefoundry/framework/README.md", meta["file_meta"])
        self.assertTrue(any(c["path"] == ".wavefoundry/framework/README.md" for c in chunks))

    def test_project_code_index_can_opt_in_excluded_prefixes(self):
        _make_repo(self.root, {
            "src/app.py": "def app(): pass\n",
            ".wavefoundry/framework/scripts/server.py": "def server_main(): pass\n",
            "vendor/docs/custom.py": "def custom(): pass\n",
        })

        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            self.bi.build_index(
                self.root,
                full=True,
                content="code",
                project_include_prefixes=(".wavefoundry/framework/scripts", "vendor/docs"),
                verbose=False,
            )

        index_dir = self.root / ".wavefoundry" / "index"
        meta = json.loads((index_dir / "meta.json").read_text())
        code_chunks = json.loads((index_dir / "code.json").read_text())
        self.assertIn(".wavefoundry/framework/scripts/server.py", meta["file_meta"])
        self.assertTrue(any(c["path"] == ".wavefoundry/framework/scripts/server.py" for c in code_chunks))
        self.assertIn("vendor/docs/custom.py", meta["file_meta"])


class StatCacheTests(unittest.TestCase):
    """12b1a: stat+inode cache pre-filter for incremental change detection."""

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

    def test_stat_cache_hit_skips_hash_on_clean_pass(self):
        """On a clean incremental pass, _sha256 must not be called for any file."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        with patch.object(self.bi, "_sha256", wraps=self.bi._sha256) as mock_hash:
            result = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertTrue(result["up_to_date"])
        mock_hash.assert_not_called()

    def test_stat_cache_miss_on_content_change(self):
        """A file whose content changes is detected and re-chunked."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        (self.root / "src" / "foo.py").write_text("def f(): return 42\n", encoding="utf-8")
        result = self._run_build(full=False)
        self.assertFalse(result["up_to_date"])
        self.assertEqual(result["files_indexed"], 1)

    def test_same_content_same_mtime_not_rechunked(self):
        """A file written with identical content and restored mtime is not re-chunked."""
        p = self.root / "src" / "foo.py"
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        # Capture original mtime
        original_mtime = p.stat().st_mtime
        # Overwrite with identical content, restore mtime
        p.write_text("def f(): pass\n", encoding="utf-8")
        import os
        os.utime(p, (original_mtime, original_mtime))
        result = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertTrue(result["up_to_date"])

    def test_missing_file_meta_treated_as_empty(self):
        """An index with no file_meta is treated as empty — all files re-hashed."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        (index_dir / "meta.json").write_text(
            json.dumps({
                "model_versions": {"docs": self.bi.DOCS_MODEL, "code": self.bi.CODE_MODEL},
                "chunker_version": "",
            }),
            encoding="utf-8",
        )
        result = self._run_build(full=False)
        meta = json.loads((index_dir / "meta.json").read_text())
        self.assertIn("file_meta", meta)
        entry = meta["file_meta"].get("src/foo.py")
        self.assertIsNotNone(entry)
        self.assertIn("mtime", entry)

    def test_full_rebuild_bypasses_stat_cache(self):
        """Full rebuild re-hashes all files regardless of cached stat."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        with patch.object(self.bi, "_sha256", wraps=self.bi._sha256) as mock_hash:
            result = self._run_build(full=True)
        self.assertFalse(result["up_to_date"])
        mock_hash.assert_called()


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
                "file_meta": {},
            }),
            encoding="utf-8",
        )
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            result = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertFalse(result["up_to_date"])
        self.assertGreater(result["files_indexed"], 0)

    def test_chunker_version_change_per_layer_triggers_rebuild(self):
        """A docs-only update must not stamp the code layer as current (regression guard)."""
        _make_repo(self.root, {"src/foo.md": "## Guide\n\nContent.\n"})
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        current_cv = self.bi._get_chunker().CHUNKER_VERSION
        # Simulate: code layer was built with an old chunker; docs layer is current
        (index_dir / "meta.json").write_text(
            json.dumps({
                "model_versions": {
                    "docs": self.bi.DOCS_MODEL,
                    "code": self.bi.CODE_MODEL,
                },
                "chunker_versions": {
                    "docs": current_cv,
                    "code": "old-chunker-version",
                },
                "content": ["docs", "code"],
                "file_meta": {},
            }),
            encoding="utf-8",
        )
        # A code-only update must detect the stale chunker and force a full rebuild
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            result = self.bi.build_index(self.root, full=False, content="code", verbose=False)
        self.assertFalse(result.get("up_to_date", False))
        # After the build, the code layer must record the current chunker version
        meta = json.loads((index_dir / "meta.json").read_text())
        self.assertEqual(meta["chunker_versions"]["code"], current_cv)

    def test_legacy_chunker_version_scalar_migrated(self):
        """Old meta with scalar chunker_version is treated as applying to both layers."""
        _make_repo(self.root, {"src/foo.md": "## Guide\n\nContent.\n"})
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        current_cv = self.bi._get_chunker().CHUNKER_VERSION
        # Legacy format: single scalar, not per-layer
        (index_dir / "meta.json").write_text(
            json.dumps({
                "model_versions": {
                    "docs": self.bi.DOCS_MODEL,
                    "code": self.bi.CODE_MODEL,
                },
                "chunker_version": "old-chunker",
                "content": ["docs", "code"],
                "file_meta": {},
            }),
            encoding="utf-8",
        )
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        # Must trigger a rebuild since old-chunker != current
        self.assertFalse(result.get("up_to_date", False))
        # New meta must use chunker_versions dict, not scalar
        meta = json.loads((index_dir / "meta.json").read_text())
        self.assertIn("chunker_versions", meta)
        self.assertEqual(meta["chunker_versions"]["docs"], current_cv)


class OnnxProviderSelectionTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_build_index()

    def _providers(self, available: list[str]) -> list[str]:
        with patch("onnxruntime.get_available_providers", return_value=available):
            return self.mod._onnx_providers()

    def test_coreml_not_used_on_apple_silicon(self):
        # CoreML is excluded: no-op for INT8 models, actively hurts FP32 models.
        providers = self._providers(["CoreMLExecutionProvider", "CPUExecutionProvider"])
        self.assertNotIn("CoreMLExecutionProvider", providers)
        self.assertIn("CPUExecutionProvider", providers)

    def test_cuda_preferred_when_available(self):
        providers = self._providers(["CUDAExecutionProvider", "CPUExecutionProvider"])
        self.assertEqual(providers[0], "CUDAExecutionProvider")
        self.assertIn("CPUExecutionProvider", providers)

    def test_cpu_only_fallback(self):
        providers = self._providers(["CPUExecutionProvider"])
        self.assertEqual(providers, ["CPUExecutionProvider"])

    def test_cuda_preferred_when_both_cuda_and_coreml_available(self):
        providers = self._providers(["CoreMLExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"])
        self.assertEqual(providers[0], "CUDAExecutionProvider")

    def test_onnxruntime_import_error_returns_cpu(self):
        with patch.dict("sys.modules", {"onnxruntime": None}):
            result = self.mod._onnx_providers()
        self.assertEqual(result, ["CPUExecutionProvider"])


if __name__ == "__main__":
    unittest.main()
