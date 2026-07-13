from __future__ import annotations

import importlib.util
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import types
import textwrap
import time
import unittest
from contextlib import redirect_stderr
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


def _make_embedder_mock(dim: int = 4, calls: list[list[str]] | None = None):
    """Return a mock embedder whose .embed() yields zero vectors of given dimension."""
    import numpy as np

    def fake_embed(texts, batch_size=256):
        text_list = list(texts)
        if calls is not None:
            calls.append(text_list)
        for _ in text_list:
            yield np.zeros(dim, dtype=np.float32)

    mock = MagicMock()
    mock.embed.side_effect = fake_embed
    return mock


def _read_index_chunks(index_dir: Path, table_name: str) -> list[dict]:
    """Read all chunks from a LanceDB table if available, else fall back to the legacy JSON file."""
    lance_dir = index_dir / f"{table_name}.lance"
    if lance_dir.is_dir():
        try:
            import lancedb
            db = lancedb.connect(str(index_dir))
            tbl = db.open_table(table_name)
            arrow_tbl = tbl.to_arrow()
            cols = [c for c in arrow_tbl.column_names if c != "vector"]
            return arrow_tbl.select(cols).to_pylist()
        except Exception:
            pass
    json_path = index_dir / f"{table_name}.json"
    if json_path.exists():
        return json.loads(json_path.read_text(encoding="utf-8"))
    return []


def _store_mod():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "index_state_store", SCRIPTS_ROOT / "index_state_store.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read_meta_store(index_dir: Path) -> dict:
    """1sed6: build-state reads go through the store (meta.json retired)."""
    return _store_mod().export_meta_snapshot(index_dir) or {}


def _seed_meta_store(index_dir: Path, meta: dict) -> None:
    """1sed6: seed prior-build state the way production records it."""
    _store_mod().write_build_bookkeeping(index_dir, meta)


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

    def test_prunes_excluded_directories_without_rglob(self):
        _make_repo(self.root, {
            "src/foo.py": "x = 1\n",
            "node_modules/pkg/index.js": "module.exports = {};\n",
            ".git/config": "[core]\nrepositoryformatversion = 0\n",
            "dist/bundle.js": "console.log('ignored');\n",
        })
        with patch.object(Path, "rglob", side_effect=AssertionError("walk_repo should not use rglob")):
            files = self.bi.walk_repo(self.root)
        rels = {str(f.relative_to(self.root)).replace("\\", "/") for f in files}
        self.assertEqual(rels, {"docs/workflow-config.json", "src/foo.py"})


class TimestampedLogTests(unittest.TestCase):
    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_timestamped_stream_prefixes_each_complete_line(self):
        out = io.StringIO()
        stream = self.bi._TimestampedStream(out)

        stream.write("build_index: embedding doc chunks 1-2/2\n")
        stream.write("build_index: index is up to date\n")
        stream.flush()

        lines = out.getvalue().splitlines()
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertRegex(line, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00 build_index: ")
        self.assertIn("embedding doc chunks 1-2/2", lines[0])
        self.assertIn("index is up to date", lines[1])

    def test_walk_repo_returns_sorted_paths(self):
        _make_repo(self.root, {
            "z.txt": "z\n",
            "a.txt": "a\n",
            "src/b.txt": "b\n",
            "src/a.txt": "a\n",
            "src/nested/c.txt": "c\n",
        })
        files = self.bi.walk_repo(self.root)
        rels = [str(f.relative_to(self.root)).replace("\\", "/") for f in files]
        self.assertEqual(rels, sorted(rels))

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
        (self.root / "src" / "data.bin").write_bytes(b"\x93NUMPY")
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertNotIn("image.png", names)
        self.assertNotIn("data.bin", names)

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

    def test_excludes_elf_extensionless(self):
        # Extensionless ELF binaries (Lambda extension pattern) excluded via magic bytes.
        # Uses no null bytes so null-byte fallback cannot carry this — magic check must fire.
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        elf_header = b"\x7fELF" + b"\x01\x01\x01\x03" * 16  # ELF magic + non-null padding
        (self.root / "src" / "AWSSecretsLambdaExtension").write_bytes(elf_header)
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertNotIn("AWSSecretsLambdaExtension", names)
        self.assertIn("foo.py", names)

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

    def test_excludes_prompt_surface_manifest(self):
        # AC-7 (12cv4): prompt-surface-manifest.json is a machine-generated artifact, not indexed
        _make_repo(self.root, {"docs/prompts/index.md": "# Index\n"})
        manifest = self.root / "docs" / "prompts" / "prompt-surface-manifest.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text('{"schema_version":"1.0"}', encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertNotIn("prompt-surface-manifest.json", names)
        self.assertIn("index.md", names)

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

    def test_excludes_wavefoundry_framework_index(self):
        """framework/index/ (pre-built pack index) must never be walked into the project index."""
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        fw_idx = self.root / ".wavefoundry" / "framework" / "index"
        fw_idx.mkdir(parents=True, exist_ok=True)
        (fw_idx / "docs.json").write_text("[]", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        paths = [str(f.relative_to(self.root)).replace("\\", "/") for f in files]
        self.assertFalse(any(p.startswith(".wavefoundry/framework/index/") for p in paths))

    def test_excludes_wavefoundry_runtime_state_files(self):
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        (self.root / ".wavefoundry" / "dashboard-server.lock").parent.mkdir(parents=True, exist_ok=True)
        (self.root / ".wavefoundry" / "dashboard-server.lock").write_text('{"pid": 1}\n', encoding="utf-8")
        (self.root / ".wavefoundry" / "logs").mkdir(parents=True, exist_ok=True)
        (self.root / ".wavefoundry" / "logs" / "dashboard.log").write_text("started\n", encoding="utf-8")
        (self.root / ".wavefoundry" / "guard-overrides.json").write_text('{"seed_edit_allowed": {"enabled": false}}\n', encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        rel_strs = {str(f.relative_to(self.root)).replace("\\", "/") for f in files}
        self.assertNotIn(".wavefoundry/dashboard-server.lock", rel_strs)
        self.assertNotIn(".wavefoundry/logs/dashboard.log", rel_strs)
        self.assertNotIn(".wavefoundry/guard-overrides.json", rel_strs)

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

    def test_includes_env_files_for_scrubbing(self):
        """.env and .env.* files are now included — values are redacted at chunk time."""
        _make_repo(self.root, {"src/foo.py": "x = 1\n"})
        (self.root / ".env").write_text("SECRET=abc\n", encoding="utf-8")
        (self.root / ".env.local").write_text("LOCAL=xyz\n", encoding="utf-8")
        (self.root / ".env.production").write_text("PROD=123\n", encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        names = {f.name for f in files}
        self.assertIn(".env", names)
        self.assertIn(".env.local", names)
        self.assertIn(".env.production", names)

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
        """AC-7: .xml, .graphql, .gql, .proto, .sql and common SQL aliases are in SOURCE_CODE_EXTENSIONS.
        Plus `.mts`/`.cts` (1p4q4 review B4): TypeScript module extensions are first-class indexable."""
        for ext in (".xml", ".graphql", ".gql", ".proto", ".sql", ".psql", ".pgsql", ".ddl", ".dml", ".tsql", ".hql",
                    ".mts", ".cts"):
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

    def test_framework_pack_artifacts_filter_strips_transient_extensions(self):
        """Regression for 130o2: transient artifact extensions must be stripped from
        the framework-layer walk so they never enter framework meta.json or the pack."""
        _make_repo(self.root, {
            ".wavefoundry/framework/scripts/tool.py": "def t(): pass\n",
            ".wavefoundry/framework/test-run.lock": "pid\n",
            ".wavefoundry/framework/index/index-build.lock": "pid\n",
            ".wavefoundry/framework/index/index-build.log": "log line\n",
            ".wavefoundry/framework/index/index-build-docs.log": "log line\n",
            ".wavefoundry/framework/leftover.bak": "editor backup\n",
            ".wavefoundry/framework/leftover.swp": "editor swap\n",
            ".wavefoundry/framework/leftover.tmp": "temp\n",
            ".wavefoundry/framework/conflict.orig": "merge artifact\n",
            ".wavefoundry/framework/conflict.rej": "merge artifact\n",
        })
        files = self.bi.walk_repo(self.root, respect_ignore=False)
        framework_files = [
            p for p in files
            if str(p.relative_to(self.root)).replace("\\", "/").startswith(".wavefoundry/framework/")
        ]
        filtered = self.bi._filter_framework_pack_artifacts(framework_files, self.root)
        paths = {str(p.relative_to(self.root)).replace("\\", "/") for p in filtered}

        # Source files survive
        self.assertIn(".wavefoundry/framework/scripts/tool.py", paths)
        # Every transient extension stripped
        for forbidden in [
            ".wavefoundry/framework/test-run.lock",
            ".wavefoundry/framework/index/index-build.lock",
            ".wavefoundry/framework/index/index-build.log",
            ".wavefoundry/framework/index/index-build-docs.log",
            ".wavefoundry/framework/leftover.bak",
            ".wavefoundry/framework/leftover.swp",
            ".wavefoundry/framework/leftover.tmp",
            ".wavefoundry/framework/conflict.orig",
            ".wavefoundry/framework/conflict.rej",
        ]:
            self.assertNotIn(forbidden, paths, f"transient artifact leaked: {forbidden}")


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


class ProjectIndexInputsStaleTests(unittest.TestCase):
    """Wave 1p5xu: indexer.project_index_inputs_stale cheap stat-fast-path check."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root, {"docs/guide.md": "# Guide\n\nOriginal.\n"})
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _build_meta(self) -> dict:
        """Compute a current file_meta snapshot using the indexer's own primitives."""
        files = self.bi.walk_repo(self.root, respect_ignore=True)
        files = [p for p in files if not self.bi._is_relative_to(p, self.index_dir)]
        files = self.bi._filter_project_index_excludes(
            files, self.root, (),
            project_include_prefixes=self.bi.FRAMEWORK_FOLD_DOCS_PREFIXES,
        )
        current, _, _ = self.bi._detect_changes(files, self.root, {})
        return {"built_at": "2026-06-16T00:00:00Z", "file_meta": current}

    def test_returns_none_when_no_file_meta(self):
        self.assertIsNone(self.bi.project_index_inputs_stale(self.root, {}))
        self.assertIsNone(self.bi.project_index_inputs_stale(self.root, {"file_meta": {}}))

    def test_returns_false_when_inputs_unchanged(self):
        meta = self._build_meta()
        self.assertFalse(self.bi.project_index_inputs_stale(self.root, meta))

    def test_returns_true_when_file_content_changes(self):
        meta = self._build_meta()
        (self.root / "docs" / "guide.md").write_text("# Guide\n\nChanged.\n", encoding="utf-8")
        self.assertTrue(self.bi.project_index_inputs_stale(self.root, meta))

    def test_generated_codebase_map_does_not_drive_staleness(self):
        # Wave 1p601: writing the regenerated codebase map (at prepare/close/upgrade/
        # resource-read) must NOT mark the index stale — otherwise it would trigger
        # a reindex (the write→reindex coupling the decoupling eliminates).
        meta = self._build_meta()
        map_path = self.root / "docs" / "references" / "codebase-map.md"
        map_path.parent.mkdir(parents=True, exist_ok=True)
        map_path.write_text("# Codebase Map\n\nbrand new generated content\n", encoding="utf-8")
        self.assertFalse(self.bi.project_index_inputs_stale(self.root, meta))

    def test_returns_true_when_indexed_file_removed(self):
        meta = self._build_meta()
        (self.root / "docs" / "guide.md").unlink()
        self.assertTrue(self.bi.project_index_inputs_stale(self.root, meta))

    def test_loads_meta_from_disk_when_not_passed(self):
        meta = self._build_meta()
        _seed_meta_store(self.index_dir, meta)
        self.assertFalse(self.bi.project_index_inputs_stale(self.root))
        (self.root / "docs" / "guide.md").write_text("# Guide\n\nChanged.\n", encoding="utf-8")
        self.assertTrue(self.bi.project_index_inputs_stale(self.root))


class IndexBuildLockTests(unittest.TestCase):
    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root, {"docs/guide.md": "# Guide\n"})
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_index_build_lock_leaves_metadata_but_releases_os_lock(self):
        lock_path = self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME

        with self.bi._index_build_lock(self.index_dir):
            self.assertTrue(lock_path.exists())
            data = json.loads(lock_path.read_text(encoding="utf-8"))
            self.assertEqual(data.get("pid"), os.getpid())
            self.assertIsInstance(data.get("started_at"), float)

        with self.bi._index_build_lock(self.index_dir):
            self.assertTrue(lock_path.exists())

    def test_main_fails_fast_when_another_process_holds_index_lock(self):
        holder = textwrap.dedent(
            f"""
            import importlib.util
            import pathlib
            import sys
            import time

            spec = importlib.util.spec_from_file_location("indexer_holder", {str(INDEXER_PATH)!r})
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            with mod._index_build_lock(pathlib.Path(sys.argv[1])):
                print("locked", flush=True)
                time.sleep(2.0)
            """
        )

        proc = subprocess.Popen(
            [sys.executable, "-B", "-c", holder, str(self.index_dir)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual(proc.stdout.readline().strip(), "locked")
            rc = self.bi.main([
                "--root", str(self.root),
                "--index-dir", str(self.index_dir),
                "--content", "docs",
            ])
            self.assertEqual(rc, 1)
        finally:
            proc.terminate()
            proc.communicate(timeout=5)

    def test_stale_lock_metadata_is_reclaimed_on_acquire(self):
        lock_path = self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME
        lock_path.write_text(
            json.dumps({"pid": 99999999, "started_at": 0.0}),
            encoding="utf-8",
        )
        err_buf = io.StringIO()
        with redirect_stderr(err_buf):
            with self.bi._index_build_lock(self.index_dir):
                data = json.loads(lock_path.read_text(encoding="utf-8"))
                self.assertEqual(data.get("pid"), os.getpid())
        self.assertIn("reclaimed stale", err_buf.getvalue())

    def test_classify_index_build_lock_owner_live_and_stale(self):
        # Wave 1p98u: a live owner is a running index-builder process (not merely os.kill-alive).
        with patch.object(self.bi, "_pid_is_index_builder", return_value=True):
            live = self.bi.classify_index_build_lock_owner(
                {"pid": os.getpid(), "started_at": time.time()}
            )
        self.assertEqual(live, "live")
        stale = self.bi.classify_index_build_lock_owner(
            {"pid": 99999999, "started_at": 0.0}
        )
        self.assertEqual(stale, "stale")
        completed = self.bi.classify_index_build_lock_owner(
            {"pid": 99999999, "started_at": time.time()}
        )
        self.assertEqual(completed, "completed")

    def test_stale_lock_file_is_unlinked_before_acquire(self):
        """Wave 1p2q3 (1p2w5 / Bug 1): a lock file whose metadata records a
        dead PID must be unlinked at `_index_build_lock` entry so downstream
        tools that read the file (status surfaces, diagnostic messages) see
        the fresh post-acquire metadata, not the dead-pid legacy."""
        lock_path = self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME
        lock_path.write_text(
            json.dumps({"pid": 99999999, "started_at": 0.0}),
            encoding="utf-8",
        )
        # Capture the inode of the pre-existing file so we can confirm the
        # post-acquire file is a fresh inode (i.e. the unlink ran).
        pre_inode = lock_path.stat().st_ino
        with redirect_stderr(io.StringIO()):
            with self.bi._index_build_lock(self.index_dir):
                post_inode = lock_path.stat().st_ino
                meta = json.loads(lock_path.read_text(encoding="utf-8"))
                self.assertEqual(meta.get("pid"), os.getpid())
        self.assertNotEqual(
            pre_inode, post_inode,
            "stale lock file should have been unlinked before acquire — "
            "same inode means the original dead-PID metadata file was reused",
        )

    def test_recent_completed_owner_does_not_log_reclaimed_stale(self):
        lock_path = self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME
        lock_path.write_text(
            json.dumps({"pid": 99999999, "started_at": time.time()}),
            encoding="utf-8",
        )
        err_buf = io.StringIO()
        with redirect_stderr(err_buf):
            with self.bi._index_build_lock(self.index_dir):
                pass
        self.assertNotIn("reclaimed stale", err_buf.getvalue())

    def test_format_index_build_lock_conflict_distinguishes_live_and_stale(self):
        (self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME).write_text(
            json.dumps({"pid": os.getpid(), "started_at": time.time()}),
            encoding="utf-8",
        )
        with patch.object(self.bi, "_pid_is_index_builder", return_value=True):
            live_msg = self.bi.format_index_build_lock_conflict(self.index_dir)
        self.assertIn("live build in progress", live_msg)

        (self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME).write_text(
            json.dumps({"pid": 99999999, "started_at": 0.0}),
            encoding="utf-8",
        )
        stale_msg = self.bi.format_index_build_lock_conflict(self.index_dir)
        self.assertIn("appears stale", stale_msg)

    def test_should_coalesce_hook_reindex_when_live_or_recent_spawn(self):
        lock_path = self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME
        lock_path.write_text(
            json.dumps({"pid": os.getpid(), "started_at": time.time()}),
            encoding="utf-8",
        )
        # Wave 1p98u: the live-owner coalesce path requires the owner be a running index builder.
        with patch.object(self.bi, "_pid_is_index_builder", return_value=True):
            self.assertTrue(self.bi.should_coalesce_hook_reindex(self.index_dir))

        lock_path.write_text(
            json.dumps({"pid": 99999999, "started_at": 0.0}),
            encoding="utf-8",
        )
        self.bi.record_hook_reindex_spawn(self.index_dir)
        self.assertTrue(self.bi.should_coalesce_hook_reindex(self.index_dir))

        # Wave 1p9am: the debounce is now 45s — backdate the last-spawn marker past the window rather
        # than sleeping it out.
        (self.index_dir / self.bi.HOOK_REINDEX_LAST_SPAWN_NAME).write_text(
            str(time.time() - self.bi.HOOK_REINDEX_DEBOUNCE_SECONDS - 1.0), encoding="utf-8"
        )
        self.assertFalse(self.bi.should_coalesce_hook_reindex(self.index_dir))

    # ---- Wave 1p98u: zombie / recycled-PID liveness hardening ----

    def test_zombie_owner_reads_not_running(self):
        # A defunct owner (os.kill-alive but Z-state) must read as not running.
        with patch.object(self.bi, "_process_is_zombie", return_value=True):
            self.assertFalse(self.bi._pid_is_running(os.getpid()))

    def test_zombie_owner_classifies_stale_and_reclaims(self):
        # A zombie owner → not live → age-based stale → the existing reclaim path clears it.
        lock_path = self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME
        lock_path.write_text(
            json.dumps({"pid": os.getpid(), "started_at": 0.0}), encoding="utf-8"
        )
        with patch.object(self.bi, "_process_is_zombie", return_value=True):
            owner = self.bi.classify_index_build_lock_owner(
                self.bi.read_index_build_lock_metadata(lock_path)
            )
            self.assertEqual(owner, "stale")
            with redirect_stderr(io.StringIO()):
                with self.bi._index_build_lock(self.index_dir):
                    data = json.loads(lock_path.read_text(encoding="utf-8"))
                    self.assertEqual(data.get("pid"), os.getpid())

    def test_recycled_pid_not_index_builder_is_not_live(self):
        # A live PID whose cmdline is not an index build (recycled PID) must not read as a live build.
        with patch.object(self.bi, "_process_cmdline", return_value="/bin/bash -l"):
            recent = self.bi.classify_index_build_lock_owner(
                {"pid": os.getpid(), "started_at": time.time()}
            )
            self.assertEqual(recent, "completed")  # not live
            old = self.bi.classify_index_build_lock_owner(
                {"pid": os.getpid(), "started_at": 0.0}
            )
            self.assertEqual(old, "stale")

    def test_live_index_builder_classifies_live(self):
        with patch.object(
            self.bi, "_process_cmdline",
            return_value="python3 .wavefoundry/framework/scripts/indexer.py --root .",
        ):
            self.assertEqual(
                self.bi.classify_index_build_lock_owner(
                    {"pid": os.getpid(), "started_at": time.time()}
                ),
                "live",
            )

    def test_scan_unavailable_owner_treated_live_not_reclaimed(self):
        # When the cmdline scan is unavailable, an alive owner stays "live" (never reclaimed → no
        # double-build); the OS flock remains the authority.
        with patch.object(self.bi, "_process_cmdline", return_value=None):
            self.assertEqual(
                self.bi.classify_index_build_lock_owner(
                    {"pid": os.getpid(), "started_at": time.time()}
                ),
                "live",
            )

    def test_metadata_without_cmdline_marker_degrades_gracefully(self):
        # Older metadata lacking the "cmdline" field must classify without crashing (liveness uses
        # the live PID's cmdline, not the recorded marker).
        with patch.object(self.bi, "_process_cmdline", return_value=None):
            owner = self.bi.classify_index_build_lock_owner(
                {"pid": os.getpid(), "started_at": time.time()}
            )
        self.assertEqual(owner, "live")

    def test_lock_metadata_records_cmdline_marker(self):
        lock_path = self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME
        with self.bi._index_build_lock(self.index_dir):
            data = json.loads(lock_path.read_text(encoding="utf-8"))
        self.assertIn("cmdline", data)
        self.assertIsInstance(data["cmdline"], str)

    def test_process_is_zombie_parses_ps_state(self):
        def fake_run(cmd, **kw):
            return MagicMock(returncode=0, stdout="Z\n")
        with patch.object(self.bi, "os") as fake_os:
            fake_os.name = "posix"
            with patch.object(self.bi.subprocess_util, "isolated_run", side_effect=fake_run):
                self.assertTrue(self.bi._process_is_zombie(4321))
        with patch.object(self.bi, "os") as fake_os:
            fake_os.name = "posix"
            with patch.object(self.bi.subprocess_util, "isolated_run",
                              side_effect=lambda cmd, **kw: MagicMock(returncode=0, stdout="S\n")):
                self.assertFalse(self.bi._process_is_zombie(4321))

    def test_process_is_zombie_noop_on_windows(self):
        with patch.object(self.bi, "os") as fake_os:
            fake_os.name = "nt"
            with patch.object(self.bi.subprocess_util, "isolated_run") as run:
                self.assertFalse(self.bi._process_is_zombie(4321))
                run.assert_not_called()

    def test_liveness_probes_route_through_windowless_helper(self):
        # AC-6: process probes must use subprocess_util.isolated_run (windowless), never bare subprocess.
        captured = {}
        def fake_run(cmd, **kw):
            captured["cmd"] = cmd
            return MagicMock(returncode=0, stdout="python indexer.py --root .")
        with patch.object(self.bi.subprocess_util, "isolated_run", side_effect=fake_run):
            self.bi._process_cmdline(4321)
        self.assertIn("cmd", captured)


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
        # 1sed6: SQLite is the only state authority — no meta.json is written.
        self.assertFalse((index_dir / "meta.json").exists())
        self.assertTrue(_read_meta_store(index_dir).get("file_meta"))
        # Index may be stored as LanceDB tables or legacy JSON files.
        has_index = (
            (index_dir / "docs.lance").is_dir() or (index_dir / "docs.json").exists()
            or (index_dir / "code.lance").is_dir() or (index_dir / "code.json").exists()
        )
        self.assertTrue(has_index)
        self.assertFalse(result["up_to_date"])

    def test_build_does_not_write_codebase_map(self):
        # Wave 1p601 AC-2b: map regen is DECOUPLED from the index build — an
        # indexer-driven build must NOT write docs/references/codebase-map.md
        # (that would create a write→reindex loop into the indexed docs tree).
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        self._run_build(full=True)
        map_path = self.root / "docs" / "references" / "codebase-map.md"
        self.assertFalse(map_path.exists(), "indexer build must NOT regenerate the codebase map")

    def test_second_run_is_up_to_date(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        # Next run — no changes, no embedder calls needed; a true no-op.
        result = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertTrue(result["up_to_date"])
        self.assertEqual(result["files_indexed"], 0)

    def test_incremental_docs_only_change_skips_code_embedder(self):
        """1p5d6: an incremental update touching only a doc file must NOT construct the code
        embedder (no new code chunks → no model load)."""
        _make_repo(self.root, {
            "src/foo.py": "def f():\n    return 1\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        self._run_build(full=True)
        (self.root / "docs" / "guide.md").write_text("## Intro\n\nHello changed now.\n", encoding="utf-8")
        requested: list[str] = []

        def spy(model, n_chunks=None):
            requested.append(model)
            return _make_embedder_mock(dim=4)

        with patch.object(self.bi, "_get_embedder", side_effect=spy):
            self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertIn(self.bi.DOCS_MODEL, requested)
        self.assertNotIn(self.bi.CODE_MODEL, requested, "code embedder must not load for a docs-only change")

    def test_incremental_code_only_change_skips_docs_embedder(self):
        """1p5d6: the mirror — a code-only change must not construct the docs embedder."""
        _make_repo(self.root, {
            "src/foo.py": "def f():\n    return 1\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        self._run_build(full=True)
        (self.root / "src" / "foo.py").write_text("def f():\n    return 42\n", encoding="utf-8")
        requested: list[str] = []

        def spy(model, n_chunks=None):
            requested.append(model)
            return _make_embedder_mock(dim=4)

        with patch.object(self.bi, "_get_embedder", side_effect=spy):
            self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertIn(self.bi.CODE_MODEL, requested)
        self.assertNotIn(self.bi.DOCS_MODEL, requested, "docs embedder must not load for a code-only change")

    def test_full_rebuild_loads_both_embedders(self):
        """1p5d6: a full rebuild always loads both layer embedders (both layers have all chunks)."""
        _make_repo(self.root, {
            "src/foo.py": "def f():\n    return 1\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        requested: list[str] = []

        def spy(model, n_chunks=None):
            requested.append(model)
            return _make_embedder_mock(dim=4)

        with patch.object(self.bi, "_get_embedder", side_effect=spy):
            self.bi.build_index(self.root, full=True, content="all", verbose=False)
        self.assertIn(self.bi.DOCS_MODEL, requested)
        self.assertIn(self.bi.CODE_MODEL, requested)

    def test_chunker_version_bump_reuses_vectors_no_reembed(self):
        """1p4n4: a chunker-ONLY version bump re-chunks every file but reuses embeddings by
        content hash — content-identical chunks are NOT re-embedded (no full re-encode)."""
        _make_repo(self.root, {"src/foo.py": "def f():\n    return 1\n\ndef g():\n    return 2\n"})
        self._run_build(full=True)
        index_dir = self.root / ".wavefoundry" / "index"
        meta = _read_meta_store(index_dir)
        meta.setdefault("chunker_versions", {})["code"] = "old-chunker-version"  # simulate a bump
        _seed_meta_store(index_dir, meta)

        code_calls: list[list[str]] = []
        spy = _make_embedder_mock(dim=4, calls=code_calls)
        with patch.object(self.bi, "_get_embedder", return_value=spy):
            self.bi.build_index(self.root, full=False, content="code", verbose=False)

        embedded = [t for batch in code_calls for t in batch]
        self.assertEqual(embedded, [], "chunker-only bump must reuse vectors, not re-embed")
        # the bump is recorded (so it doesn't re-trigger)
        meta2 = _read_meta_store(index_dir)
        self.assertEqual(meta2["chunker_versions"]["code"], self.bi._get_chunker().CHUNKER_VERSION)

    def test_model_version_bump_reembeds_all_no_reuse(self):
        """1p4n4: a MODEL-version change forces a full re-embed (old-model vectors are invalid)
        — it must NOT take the chunker-only reuse path."""
        _make_repo(self.root, {"src/foo.py": "def f():\n    return 1\n"})
        self._run_build(full=True)
        index_dir = self.root / ".wavefoundry" / "index"
        meta = _read_meta_store(index_dir)
        meta.setdefault("model_versions", {})["code"] = "old-model"
        _seed_meta_store(index_dir, meta)

        code_calls: list[list[str]] = []
        spy = _make_embedder_mock(dim=4, calls=code_calls)
        with patch.object(self.bi, "_get_embedder", return_value=spy):
            self.bi.build_index(self.root, full=False, content="code", verbose=False)

        embedded = [t for batch in code_calls for t in batch]
        self.assertTrue(any("return 1" in t for t in embedded), "model change must re-embed, not reuse")

    def test_framework_seeds_and_readme_fold_into_project_docs_index(self):
        """1p4ww (real-pipeline regression): the framework seeds + README must actually
        land in the project docs index. The original fold unit tests wrote synthetic index
        rows and never exercised the walk+filter pipeline, which dropped the seeds at the
        ``files_for_meta`` stage (it used the docs+code graph surface, not the fold prefixes)."""
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nProject docs.\n",
            ".wavefoundry/framework/seeds/100-install.prompt.md": "# Install seed\n\nHow to install.\n",
            ".wavefoundry/framework/README.md": "# Wavefoundry Framework\n\nOverview.\n",
        })
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock]):
            self.bi.build_index(self.root, full=True, content="docs", verbose=False)

        import lancedb
        rows = lancedb.connect(str(self.root / ".wavefoundry" / "index")).open_table("docs").search().limit(10000).to_list()
        paths = {r.get("path") for r in rows}
        self.assertIn(".wavefoundry/framework/seeds/100-install.prompt.md", paths,
                      "framework seed must be folded into the project docs index")
        self.assertIn(".wavefoundry/framework/README.md", paths,
                      "framework README must be folded into the project docs index")
        self.assertIn("docs/guide.md", paths, "project docs must still be indexed")

        # The folded seed/README must also be tracked in meta.json file_meta (staleness).
        meta = _read_meta_store(self.root / ".wavefoundry" / "index")
        file_meta = meta.get("file_meta") or meta.get("file_hashes") or {}
        self.assertIn(".wavefoundry/framework/seeds/100-install.prompt.md", file_meta)
        self.assertIn(".wavefoundry/framework/README.md", file_meta)

    def test_docs_model_change_reembeds_docs_only_code_untouched(self):
        """1p4wx (AC-4): switching the DOCS model forces a docs-only re-embed via the
        existing ``model_versions['docs'] != DOCS_MODEL`` trigger. The realistic trigger
        path is content='docs' (the post-edit hook default), which never loads the code
        embedder — code vectors are left untouched."""
        _make_repo(self.root, {
            "src/foo.py": "def f():\n    return 1\n",
            "docs/guide.md": "## Intro\n\nWave lifecycle docs.\n",
        })
        self._run_build(full=True)
        index_dir = self.root / ".wavefoundry" / "index"
        meta = _read_meta_store(index_dir)
        # Simulate the docs-model upgrade: the index was built under an old docs model;
        # the code model still matches the current CODE_MODEL.
        meta.setdefault("model_versions", {})["docs"] = "old-docs-model"
        meta["model_versions"]["code"] = self.bi.CODE_MODEL
        _seed_meta_store(index_dir, meta)

        # Snapshot the code table before the docs re-embed.
        code_lance = index_dir / "code.lance"
        code_before = sorted(
            (p.name, p.stat().st_size) for p in code_lance.rglob("*") if p.is_file()
        ) if code_lance.is_dir() else []

        docs_calls: list[list[str]] = []
        docs_spy = _make_embedder_mock(dim=4, calls=docs_calls)
        # Only ONE embedder is provided: if the content='docs' build tried to load a
        # CODE embedder, side_effect would be exhausted and raise — proving code is untouched.
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_spy]):
            self.bi.build_index(self.root, full=False, content="docs", verbose=False)

        embedded = [t for batch in docs_calls for t in batch]
        self.assertTrue(any("Wave lifecycle" in t for t in embedded),
                        "docs-model change must re-embed the docs layer")
        # meta now records the current docs model; code model untouched.
        meta_after = _read_meta_store(index_dir)
        # Wave 1p936: model_versions now carries a precision-class suffix ("@full" or "@int8"). The
        # class is machine-dependent (a CPU-bound box with the INT8 export cached records "@int8";
        # a GPU box or a box without the INT8 source records "@full"), so assert the MODEL-NAME
        # prefix, not the exact class.
        self.assertEqual(meta_after["model_versions"]["docs"].split("@", 1)[0], self.bi.DOCS_MODEL)
        self.assertEqual(meta_after["model_versions"]["code"], self.bi.CODE_MODEL)
        # The code table files are byte-identical (never rewritten by the docs build).
        code_after = sorted(
            (p.name, p.stat().st_size) for p in code_lance.rglob("*") if p.is_file()
        ) if code_lance.is_dir() else []
        self.assertEqual(code_before, code_after, "code index must be untouched by a docs-only re-embed")

    def test_explicit_rechunk_rechunks_all_reuses_vectors_no_version_change(self):
        """1p4n4 mode='rechunk': an explicit rechunk re-chunks EVERY file even with NO version
        change (a plain update would re-chunk nothing) while reusing embeddings by content hash —
        only new/changed chunks re-embed. Lets an operator re-materialize chunks after a chunker
        LOGIC change that was not version-bumped, cheaply."""
        _make_repo(self.root, {"src/foo.py": "def f():\n    return 1\n\ndef g():\n    return 2\n"})
        self._run_build(full=True)

        # A plain update with nothing changed re-chunks nothing.
        upd_calls: list[list[str]] = []
        with patch.object(self.bi, "_get_embedder", return_value=_make_embedder_mock(dim=4, calls=upd_calls)):
            r_upd = self.bi.build_index(self.root, full=False, content="code", verbose=False)
        self.assertEqual(r_upd.get("files_indexed"), 0, "plain update with no changes must re-chunk nothing")

        # rechunk re-processes every file but reuses vectors (nothing re-embedded), no version change.
        rc_calls: list[list[str]] = []
        with patch.object(self.bi, "_get_embedder", return_value=_make_embedder_mock(dim=4, calls=rc_calls)):
            r_rc = self.bi.build_index(self.root, full=False, rechunk=True, content="code", verbose=False)
        self.assertGreater(r_rc.get("files_indexed") or 0, 0, "rechunk must re-process every file")
        self.assertEqual([t for batch in rc_calls for t in batch], [],
                         "rechunk must reuse embeddings (content unchanged), not re-embed")

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

    def test_incremental_markdown_embeds_only_changed_heading_chunk(self):
        _make_repo(self.root, {
            "docs/guide.md": textwrap.dedent("""\
                # Guide

                ## Alpha

                Alpha body stays the same.

                ## Beta

                Beta body before.
                """),
        })
        self._run_build(full=True)

        (self.root / "docs" / "guide.md").write_text(textwrap.dedent("""\
            # Guide

            ## Alpha

            Alpha body stays the same.

            ## Beta

            Beta body after.
            """), encoding="utf-8")

        doc_calls: list[list[str]] = []
        code_calls: list[list[str]] = []
        docs_mock = _make_embedder_mock(dim=4, calls=doc_calls)
        code_mock = _make_embedder_mock(dim=4, calls=code_calls)
        stdout = io.StringIO()
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            with contextlib.redirect_stdout(stdout):
                self.bi.build_index(self.root, full=False, content="all", verbose=False)

        embedded_doc_texts = [text for batch in doc_calls for text in batch]
        embedded_code_texts = [text for batch in code_calls for text in batch]
        self.assertEqual(len(embedded_doc_texts), 1)
        self.assertIn("Beta body after.", embedded_doc_texts[0])
        self.assertEqual(embedded_code_texts, [])
        self.assertRegex(
            stdout.getvalue(),
            r"semantic file update path=docs/guide\.md table=docs written=1 removed=1 unchanged=3",
        )

    def test_incremental_python_embeds_only_changed_code_chunk_for_mixed_path(self):
        _make_repo(self.root, {
            "src/tools.py": textwrap.dedent('''\
                def alpha():
                    """Alpha docs."""
                    return 1

                def beta():
                    return 2
                '''),
        })
        self._run_build(full=True)

        (self.root / "src" / "tools.py").write_text(textwrap.dedent('''\
            def alpha():
                """Alpha docs."""
                return 42

            def beta():
                return 2
            '''), encoding="utf-8")

        doc_calls: list[list[str]] = []
        code_calls: list[list[str]] = []
        docs_mock = _make_embedder_mock(dim=4, calls=doc_calls)
        code_mock = _make_embedder_mock(dim=4, calls=code_calls)
        stdout = io.StringIO()
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            with contextlib.redirect_stdout(stdout):
                self.bi.build_index(self.root, full=False, content="all", verbose=False)

        embedded_doc_texts = [text for batch in doc_calls for text in batch]
        embedded_code_texts = [text for batch in code_calls for text in batch]
        self.assertEqual(embedded_doc_texts, [])
        self.assertEqual(len(embedded_code_texts), 1)
        self.assertIn("return 42", embedded_code_texts[0])
        self.assertNotIn("def beta", embedded_code_texts[0])
        output = stdout.getvalue()
        self.assertRegex(output, r"semantic file update path=src/tools\.py table=docs written=0 removed=0 unchanged=1")
        self.assertRegex(output, r"semantic file update path=src/tools\.py table=code written=1 removed=1 unchanged=2")

    def test_incremental_line_window_shift_reembeds_affected_chunks(self):
        # 1sek8: the file must be CODE-CORPUS-ELIGIBLE under the unified
        # membership rule (source extensions + known extensionless code
        # names) — the former `.custom` fixture rode content=all's
        # unfiltered corpus, which no longer exists. Jenkinsfile is
        # line-window chunked by name, preserving the shift semantics
        # this test pins.
        source = "\n".join(f"line {i}" for i in range(1, 151)) + "\n"
        _make_repo(self.root, {"Jenkinsfile": source})
        self._run_build(full=True)

        shifted = "inserted line\n" + source
        (self.root / "Jenkinsfile").write_text(shifted, encoding="utf-8")

        doc_calls: list[list[str]] = []
        code_calls: list[list[str]] = []
        docs_mock = _make_embedder_mock(dim=4, calls=doc_calls)
        code_mock = _make_embedder_mock(dim=4, calls=code_calls)
        # 1p5d6: notes.custom is a pure line-window CODE file (no doc chunks), so the docs embedder
        # is not loaded for this change — map by model name rather than relying on call order.
        def _emb(model, n_chunks=None):
            return docs_mock if model == self.bi.DOCS_MODEL else code_mock
        with patch.object(self.bi, "_get_embedder", side_effect=_emb):
            self.bi.build_index(self.root, full=False, content="all", verbose=False)

        embedded_doc_texts = [text for batch in doc_calls for text in batch]
        embedded_code_texts = [text for batch in code_calls for text in batch]
        # Line-window ids are line-range based. A leading insertion changes the
        # window boundaries, so the safe behavior is to re-embed affected windows
        # instead of guessing at vector reuse.
        self.assertEqual(len(embedded_code_texts), 2)
        self.assertTrue(any("inserted line" in text for text in embedded_code_texts))
        self.assertEqual(embedded_doc_texts, [])

        rows = _read_index_chunks(self.root / ".wavefoundry" / "index", "code")
        shifted_rows = [row for row in rows if row["path"] == "Jenkinsfile"]
        self.assertTrue(any(row["lines"][0] > 1 for row in shifted_rows))
        self.assertTrue(all(row.get("chunk_hash") for row in shifted_rows))

    def test_meta_records_file_meta(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        meta = _read_meta_store(self.root / ".wavefoundry" / "index")
        self.assertIn("file_meta", meta)
        self.assertIn("src/foo.py", meta["file_meta"])
        self.assertNotIn("file_hashes", meta)

    def test_meta_records_file_meta_with_stat_fields(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        meta = _read_meta_store(self.root / ".wavefoundry" / "index")
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
        meta = _read_meta_store(self.root / ".wavefoundry" / "index")
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

        code_chunks = _read_index_chunks(self.root / ".wavefoundry" / "index", "code")
        paths = {c["path"] for c in code_chunks}
        self.assertNotIn("src/bar.py", paths)

    def test_chunks_json_paths_use_forward_slashes(self):
        _make_repo(self.root, {"src/sub/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        code_chunks = _read_index_chunks(self.root / ".wavefoundry" / "index", "code")
        for c in code_chunks:
            self.assertNotIn("\\", c["path"])
            self.assertNotIn("\\", c["id"])

    def test_lance_row_count_matches_chunk_rows(self):
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\ndef g(): pass\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        self._run_build(full=True)
        index_dir = self.root / ".wavefoundry" / "index"
        code_chunks = _read_index_chunks(index_dir, "code")
        docs_chunks = _read_index_chunks(index_dir, "docs")
        self.assertTrue((index_dir / "code.lance").is_dir())
        self.assertTrue((index_dir / "docs.lance").is_dir())
        self.assertGreater(len(code_chunks), 0)
        self.assertGreater(len(docs_chunks), 0)

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

        meta = _read_meta_store(index_dir)
        self.assertIn("framework/seeds/example.md", meta["file_meta"])
        self.assertNotIn("framework/index/stale.json", meta["file_meta"])

    def test_default_project_index_folds_framework_docs_but_excludes_other_framework_source(self):
        # Wave 1p4ww: the project docs index FOLDS the framework seeds + README, but the
        # rest of .wavefoundry/framework/ (scripts, MANIFEST, …) stays excluded by the
        # blanket .wavefoundry/ exclusion unless explicitly opted in via workflow-config.
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nHello.\n",
            ".wavefoundry/framework/README.md": "## Framework\n\nCanonical framework docs.\n",
            ".wavefoundry/framework/seeds/100-x.prompt.md": "# Seed\n\nBody.\n",
            ".wavefoundry/framework/scripts/server_impl.py": "def foo(): pass\n",
            ".wavefoundry/framework/MANIFEST": "README.md\nMANIFEST\n",
        })

        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            self.bi.build_index(self.root, full=True, content="docs", verbose=False)

        index_dir = self.root / ".wavefoundry" / "index"
        meta = _read_meta_store(index_dir)
        chunks = _read_index_chunks(index_dir, "docs")
        chunk_paths = {c["path"] for c in chunks}
        self.assertIn("docs/guide.md", meta["file_meta"])
        # Folded framework docs ARE indexed.
        self.assertIn(".wavefoundry/framework/README.md", meta["file_meta"])
        self.assertIn(".wavefoundry/framework/seeds/100-x.prompt.md", meta["file_meta"])
        self.assertIn(".wavefoundry/framework/README.md", chunk_paths)
        self.assertIn(".wavefoundry/framework/seeds/100-x.prompt.md", chunk_paths)
        # Non-fold framework source stays excluded (not in the fold prefixes).
        self.assertNotIn(".wavefoundry/framework/scripts/server_impl.py", meta["file_meta"])
        self.assertNotIn(".wavefoundry/framework/MANIFEST", meta["file_meta"])
        self.assertFalse(any(c["path"] == ".wavefoundry/framework/scripts/server_impl.py" for c in chunks))

    def test_project_index_excludes_wavefoundry_blanket_except_folded_docs(self):
        """Wave 1p2q3 (1p2qd): all of .wavefoundry/ excluded from the project index —
        EXCEPT the framework docs folded in by 1p4ww (seeds + README)."""
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nHello.\n",
            ".wavefoundry/framework/scripts/server_impl.py": "def foo(): pass\n",
            ".wavefoundry/framework/dashboard/dashboard.js": "// dashboard\n",
            ".wavefoundry/framework/seeds/100.md": "## seed\n",
            ".wavefoundry/logs/event.log": "log\n",
            ".wavefoundry/state.json": "{}\n",
        })
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            self.bi.build_index(self.root, full=True, content="docs", verbose=False)
        index_dir = self.root / ".wavefoundry" / "index"
        meta = _read_meta_store(index_dir)
        fold_allowed = {".wavefoundry/framework/seeds/100.md"}
        for path in meta["file_meta"]:
            if path in fold_allowed:
                continue
            self.assertFalse(path.startswith(".wavefoundry/"),
                             f"unexpected .wavefoundry/ file in project meta: {path}")
        # The folded seed IS present.
        self.assertIn(".wavefoundry/framework/seeds/100.md", meta["file_meta"])

    def test_explicit_framework_index_can_include_framework_source(self):
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nHello.\n",
            ".wavefoundry/framework/README.md": "## Framework\n\nCanonical framework docs.\n",
            ".wavefoundry/framework/MANIFEST": "README.md\nMANIFEST\n",
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

        meta = _read_meta_store(index_dir)
        chunks = _read_index_chunks(index_dir, "docs")
        self.assertIn(".wavefoundry/framework/README.md", meta["file_meta"])
        self.assertNotIn(".wavefoundry/framework/MANIFEST", meta["file_meta"])
        self.assertTrue(any(c["path"] == ".wavefoundry/framework/README.md" for c in chunks))
        self.assertFalse(any(c["path"] == ".wavefoundry/framework/MANIFEST" for c in chunks))

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
        meta = _read_meta_store(index_dir)
        chunks = _read_index_chunks(index_dir, "docs")
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
        meta = _read_meta_store(index_dir)
        code_chunks = _read_index_chunks(index_dir, "code")
        self.assertIn(".wavefoundry/framework/scripts/server.py", meta["file_meta"])
        self.assertTrue(any(c["path"] == ".wavefoundry/framework/scripts/server.py" for c in code_chunks))
        self.assertIn("vendor/docs/custom.py", meta["file_meta"])

    def test_project_meta_folds_framework_docs_only_and_is_stable_across_docs_and_code_runs(self):
        """Regression for 130nf + 1p4ww: project meta contains the FOLDED framework docs
        (seeds + README) but no other framework source, under any run; and consecutive docs
        and code runs must write identical file_meta dicts (the 'no alternating cycle'
        invariant — the fold lives in the shared files_for_meta surface, so it is stable).
        """
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nHello.\n",
            "src/app.py": "def app(): pass\n",
            ".wavefoundry/framework/README.md": "## Framework\n\nCanonical framework docs.\n",
            ".wavefoundry/framework/seeds/100-x.prompt.md": "# Seed\n\nBody.\n",
            ".wavefoundry/framework/MANIFEST": "README.md\nMANIFEST\n",
            ".wavefoundry/framework/scripts/tools.py": "def helper():\n    return 1\n",
        })
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps({"indexing": {"project_include_prefixes": {"docs": [], "code": []}}}),
            encoding="utf-8",
        )

        index_dir = self.root / ".wavefoundry" / "index"
        folded = {".wavefoundry/framework/README.md", ".wavefoundry/framework/seeds/100-x.prompt.md"}

        # Run 1: docs only.
        with patch.object(self.bi, "_get_embedder", return_value=_make_embedder_mock(dim=4)):
            self.bi.build_index(self.root, full=True, content="docs", verbose=False)
        meta_after_docs = _read_meta_store(index_dir)["file_meta"]

        # Only the FOLDED framework docs appear — not MANIFEST or scripts.
        framework_in_meta = {p for p in meta_after_docs if p.startswith(".wavefoundry/framework/")}
        self.assertEqual(framework_in_meta, folded, f"unexpected framework files in project meta: {framework_in_meta}")
        self.assertIn("docs/guide.md", meta_after_docs)
        self.assertIn("src/app.py", meta_after_docs)

        # Run 2: code only — incremental, on top of the docs meta
        with patch.object(self.bi, "_get_embedder", side_effect=[_make_embedder_mock(dim=4), _make_embedder_mock(dim=4)]):
            self.bi.build_index(self.root, full=False, content="code", verbose=False)
        meta_after_code = _read_meta_store(index_dir)["file_meta"]

        # Still only the folded framework docs in project meta after the code run.
        framework_in_meta = {p for p in meta_after_code if p.startswith(".wavefoundry/framework/")}
        self.assertEqual(framework_in_meta, folded, f"unexpected framework files after code run: {framework_in_meta}")

        # Stability invariant: docs run and code run must write IDENTICAL meta keys
        # (the original line-1822 fix prevented the 93-added/93-removed alternating cycle;
        # the new narrowing must preserve it).
        self.assertEqual(
            set(meta_after_docs.keys()),
            set(meta_after_code.keys()),
            "docs-run and code-run wrote different project meta — alternating cycle would resume",
        )

    def test_fold_survives_forwarded_non_empty_override_prefixes(self):
        """Regression (1p4ww × self-hosting): a launcher that FORWARDS non-empty
        project include-prefixes — e.g. setup_index merging the workflow-config
        code prefix ``.wavefoundry/framework/scripts`` and passing it as
        ``project_include_prefixes`` — must NOT disable the framework-seed fold.

        The override path previously returned early WITHOUT appending
        ``FRAMEWORK_FOLD_DOCS_PREFIXES``, so the moment a project configured ANY
        code prefix the override became non-empty and every seed silently vanished
        from the docs index (observed: 0/67 seeds after a real rebuild)."""
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nHello.\n",
            ".wavefoundry/framework/README.md": "## Framework\n\nCanonical.\n",
            ".wavefoundry/framework/seeds/100-x.prompt.md": "# Seed\n\nBody.\n",
            ".wavefoundry/framework/scripts/tools.py": "def helper():\n    return 1\n",
        })
        index_dir = self.root / ".wavefoundry" / "index"
        folded = {".wavefoundry/framework/README.md", ".wavefoundry/framework/seeds/100-x.prompt.md"}

        # content="all" with a FORWARDED override prefix (the setup_index merge result).
        with patch.object(self.bi, "_get_embedder",
                          side_effect=[_make_embedder_mock(dim=4), _make_embedder_mock(dim=4)]):
            self.bi.build_index(
                self.root,
                full=True,
                content="all",
                project_include_prefixes=(".wavefoundry/framework/scripts",),
                verbose=False,
            )

        meta = _read_meta_store(index_dir)["file_meta"]
        docs_chunks = {c["path"] for c in _read_index_chunks(index_dir, "docs")}

        # The forwarded code prefix is honored...
        self.assertIn(".wavefoundry/framework/scripts/tools.py", meta)
        # ...AND the folded seeds survive into both meta and the docs index.
        for path in folded:
            self.assertIn(path, meta, f"folded seed dropped from meta when override present: {path}")
            self.assertIn(path, docs_chunks, f"folded seed not embedded into docs index: {path}")

    def test_docs_only_graph_includes_workflow_code_prefixes_without_cli_args(self):
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nHello.\n",
            ".wavefoundry/framework/scripts/tools.py": "def helper():\n    return 1\n",
        })
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps(
                {
                    "lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0},
                    "indexing": {
                        "project_include_prefixes": {
                            "docs": [],
                            "code": [".wavefoundry/framework/scripts"],
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            self.bi.build_index(
                self.root,
                full=True,
                content="docs",
                verbose=False,
            )
        graph_path = self.root / ".wavefoundry" / "index" / "graph" / "project-graph.json"
        self.assertTrue(graph_path.exists())
        # 1p9py: graph artifacts are gzip-compressed compact JSON — sniffing read.
        import gzip as _gzip
        graph = json.loads(_gzip.decompress(graph_path.read_bytes()).decode("utf-8"))
        node_ids = {n["id"] for n in graph.get("nodes", [])}
        self.assertIn(".wavefoundry/framework/scripts/tools.py::helper", node_ids)

    def test_code_pass_self_reads_workflow_code_prefixes_without_cli_args(self):
        _make_repo(self.root, {
            "src/app.py": "def app(): pass\n",
            ".wavefoundry/framework/scripts/server.py": "def server_main(): pass\n",
        })
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps(
                {
                    "indexing": {
                        "project_include_prefixes": {
                            "docs": [],
                            "code": [".wavefoundry/framework/scripts"],
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            self.bi.build_index(
                self.root,
                full=True,
                content="code",
                verbose=False,
            )
        index_dir = self.root / ".wavefoundry" / "index"
        meta = _read_meta_store(index_dir)
        code_chunks = _read_index_chunks(index_dir, "code")
        self.assertIn(".wavefoundry/framework/scripts/server.py", meta["file_meta"])
        self.assertTrue(
            any(c["path"] == ".wavefoundry/framework/scripts/server.py" for c in code_chunks)
        )

    def test_legacy_include_framework_boolean_indexes_framework_scripts(self):
        _make_repo(self.root, {
            "src/app.py": "def app(): pass\n",
            ".wavefoundry/framework/scripts/server.py": "def server_main(): pass\n",
        })
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps(
                {"indexing": {"include_framework_code_for_code_search": True}}
            ),
            encoding="utf-8",
        )
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            self.bi.build_index(
                self.root,
                full=True,
                content="code",
                verbose=False,
            )
        index_dir = self.root / ".wavefoundry" / "index"
        meta = _read_meta_store(index_dir)
        self.assertIn(".wavefoundry/framework/scripts/server.py", meta["file_meta"])

    def test_workflow_config_evolution_reaps_orphaned_lance_rows(self):
        """Wave 1p31b (1p312): incremental update must reap LanceDB rows for
        paths excluded by workflow-config evolution, even when meta.json and
        the on-disk eligible set both already reflect the post-narrowing
        state (the post-evolution stable state where the reaper is the only
        thing that can detect the LanceDB orphan condition).

        Simulates the bug pattern in its hardest form: a prior build correctly
        cleaned meta.json AND the now-ineligible files no longer exist in the
        eligible set on disk, but earlier eviction failed to remove the
        LanceDB rows. Subsequent incrementals see "current matches meta" and
        treat the index as up-to-date — the orphan condition is invisible to
        the existing change-detection logic, so the reaper is the only
        guarantee that orphans are removed.
        """
        # Build with both src/ and lib/ indexed.
        _make_repo(self.root, {
            "src/app.py": "def app(): pass\n",
            "lib/helper.py": "def help(): pass\n",
            "lib/another.py": "def other(): pass\n",
        })
        self._run_build(full=True)

        index_dir = self.root / ".wavefoundry" / "index"

        # Confirm starting state: lib/ paths are in LanceDB.
        code_chunks_before = _read_index_chunks(index_dir, "code")
        paths_before = {c["path"] for c in code_chunks_before}
        self.assertIn("lib/helper.py", paths_before)
        self.assertIn("lib/another.py", paths_before)

        # Simulate post-evolution stable state:
        # 1. Trim meta.json to drop lib/ (workflow-config narrowing was applied).
        # 2. Delete the lib/ files from disk (the eligibility set narrowed and a
        #    subsequent run dropped them from meta, but earlier eviction failed
        #    to remove the LanceDB rows). This is the silent-orphan condition
        #    every operator with an evolving workflow-config accumulates.
        meta = _read_meta_store(index_dir)
        meta["file_meta"] = {
            k: v for k, v in meta["file_meta"].items()
            if not k.startswith("lib/")
        }
        _seed_meta_store(index_dir, meta)
        (self.root / "lib" / "helper.py").unlink()
        (self.root / "lib" / "another.py").unlink()

        # Run incremental update. From _detect_changes' perspective the index
        # is up-to-date (current eligible matches meta, both exclude lib/),
        # but LanceDB still has lib/ rows. The reaper must catch and remove
        # them on the up-to-date path itself.
        result = self.bi.build_index(self.root, full=False, content="all", verbose=False)

        # Reaper count surfaces in response.
        self.assertIn("stranded_rows_reaped", result)
        self.assertGreater(result["stranded_rows_reaped"], 0, msg="reaper should report > 0 orphans removed")

        # LanceDB no longer contains lib/ paths.
        code_chunks_after = _read_index_chunks(index_dir, "code")
        paths_after = {c["path"] for c in code_chunks_after}
        self.assertNotIn("lib/helper.py", paths_after)
        self.assertNotIn("lib/another.py", paths_after)
        # src/app.py survives — it was never excluded.
        self.assertIn("src/app.py", paths_after)

    def test_reaper_idempotent_on_clean_index(self):
        """Wave 1p31b (1p312): subsequent reaper runs on an already-clean
        index report stranded_rows_reaped: 0. Verifies AC-5 second-half:
        once orphans are reaped, future runs surface 0."""
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "src/bar.py": "def g(): pass\n",
        })
        self._run_build(full=True)
        # First incremental on a clean (no orphan) index.
        result = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertEqual(result.get("stranded_rows_reaped", 0), 0)
        # Second incremental on a clean index.
        result2 = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertEqual(result2.get("stranded_rows_reaped", 0), 0)


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
        _seed_meta_store(index_dir, {
                "model_versions": {"docs": self.bi.DOCS_MODEL, "code": self.bi.CODE_MODEL},
                "chunker_version": "",
            })
        result = self._run_build(full=False)
        meta = _read_meta_store(index_dir)
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
        _seed_meta_store(index_dir, {
                "model_versions": {"docs": "old-model", "code": "old-model"},
                "file_meta": {},
            })
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
        _seed_meta_store(index_dir, {
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
            })
        # A code-only update must detect the stale chunker and force a full rebuild
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            result = self.bi.build_index(self.root, full=False, content="code", verbose=False)
        self.assertFalse(result.get("up_to_date", False))
        # After the build, the code layer must record the current chunker version
        meta = _read_meta_store(index_dir)
        self.assertEqual(meta["chunker_versions"]["code"], current_cv)

    def test_legacy_chunker_version_scalar_migrated(self):
        """Old meta with scalar chunker_version is treated as applying to both layers."""
        _make_repo(self.root, {"src/foo.md": "## Guide\n\nContent.\n"})
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        current_cv = self.bi._get_chunker().CHUNKER_VERSION
        # Legacy format: single scalar, not per-layer
        _seed_meta_store(index_dir, {
                "model_versions": {
                    "docs": self.bi.DOCS_MODEL,
                    "code": self.bi.CODE_MODEL,
                },
                "chunker_version": "old-chunker",
                "content": ["docs", "code"],
                "file_meta": {},
            })
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        # Must trigger a rebuild since old-chunker != current
        self.assertFalse(result.get("up_to_date", False))
        # New meta must use chunker_versions dict, not scalar
        meta = _read_meta_store(index_dir)
        self.assertIn("chunker_versions", meta)
        self.assertEqual(meta["chunker_versions"]["docs"], current_cv)


    def test_graph_only_rebuild_preserves_docs_code_chunker_versions(self):
        """graph-only rebuild must not wipe docs/code chunker_versions from metadata."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        current_cv = self.bi._get_chunker().CHUNKER_VERSION
        _seed_meta_store(index_dir, {
                "model_versions": {
                    "docs": self.bi.DOCS_MODEL,
                    "code": self.bi.CODE_MODEL,
                },
                "chunker_versions": {
                    "docs": current_cv,
                    "code": current_cv,
                },
                "walker_version": self.bi.WALKER_VERSION,
                "content": ["docs", "code"],
                "file_meta": {},
            })
        self.bi.build_index(self.root, full=True, content="graph", verbose=False)
        meta = _read_meta_store(index_dir)
        self.assertEqual(meta.get("chunker_versions", {}).get("docs"), current_cv)
        self.assertEqual(meta.get("chunker_versions", {}).get("code"), current_cv)
        self.assertIn("docs", meta.get("content", []))
        self.assertIn("code", meta.get("content", []))


class PrecisionClassVersionTests(unittest.TestCase):
    """Wave 1p936: the precision class (``full`` vs ``int8``) folded into ``model_versions`` —
    a class change forces a re-embed; a same-class provider/format swap (FP16<->FP32) does not."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    # --- the pure helpers (deterministic, no hardware / no build) ---

    def test_precision_class_from_version_parses_suffix(self):
        self.assertEqual(self.bi._precision_class_from_version("MODEL@int8"), "int8")
        self.assertEqual(self.bi._precision_class_from_version("MODEL@full"), "full")

    def test_precision_class_from_version_legacy_bare_name_is_full(self):
        # AC-3: a legacy value with no "@class" suffix predates the precision split → "full"
        # (existing indexes are full-precision; must not spuriously rebuild on upgrade).
        self.assertEqual(self.bi._precision_class_from_version("BAAI/bge-small-en-v1.5"), "full")
        self.assertEqual(self.bi._precision_class_from_version(""), "full")
        self.assertEqual(self.bi._precision_class_from_version(None), "full")

    def test_predicted_precision_class_gpu_is_full(self):
        # A GPU machine runs FP16 end-to-end → "full" (a non-offloading model falls back to
        # fastembed full, never int8 — so "GPU available" always means "full").
        self.assertEqual(
            self.bi._predicted_precision_class("BAAI/bge-small-en-v1.5", ["CoreMLExecutionProvider"]),
            "full",
        )

    def test_predicted_precision_class_cpu_registered_is_int8(self):
        # No GPU + a model with an INT8 clean-export source → "int8".
        with patch.object(self.bi.accel_embedder, "_available_gpu_providers", return_value=[]):
            self.assertEqual(
                self.bi._predicted_precision_class("BAAI/bge-small-en-v1.5", ["CPUExecutionProvider"]),
                "int8",
            )

    def test_predicted_precision_class_cpu_unregistered_is_full(self):
        # No GPU + a model with NO INT8 source → "full" (fastembed-resident).
        with patch.object(self.bi.accel_embedder, "_available_gpu_providers", return_value=[]):
            self.assertEqual(
                self.bi._predicted_precision_class("Some/unregistered-model", ["CPUExecutionProvider"]),
                "full",
            )

    # --- build-level: re-embed on class change, no re-embed on same class ---

    def _write_meta(self, docs_value: str) -> Path:
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        _seed_meta_store(index_dir, {
                "model_versions": {"docs": docs_value},
                "chunker_versions": {"docs": self.bi._get_chunker().CHUNKER_VERSION},
                "walker_version": self.bi.WALKER_VERSION,
                "content": ["docs"],
                "file_meta": {},
            })
        return index_dir

    def test_precision_class_change_forces_reembed(self):
        """AC-1: switching a layer's precision class (int8 -> full) forces a full re-embed."""
        _make_repo(self.root, {"docs/guide.md": "## Intro\n\nWave lifecycle docs.\n"})
        # Index recorded as int8; the CURRENT machine predicts "full" (patched) → class change.
        self._write_meta(f"{self.bi.DOCS_MODEL}@int8")
        docs_calls: list[list[str]] = []
        docs_spy = _make_embedder_mock(dim=4, calls=docs_calls)
        with patch.object(self.bi, "_predicted_precision_class", return_value="full"), \
             patch.object(self.bi, "_get_embedder", return_value=docs_spy):
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        self.assertFalse(result.get("up_to_date", False), "class change must force a rebuild")
        embedded = [t for batch in docs_calls for t in batch]
        self.assertTrue(any("Wave lifecycle" in t for t in embedded), "must re-embed on class change")
        meta = _read_meta_store(self.root / ".wavefoundry" / "index")
        self.assertEqual(meta["model_versions"]["docs"], f"{self.bi.DOCS_MODEL}@full")

    def _make_docs_only_repo(self) -> None:
        # NOTE: deliberately NOT _make_repo — its docs/workflow-config.json drifts on a content=docs
        # second pass (a pre-existing drift-repair quirk unrelated to precision) and would mask the
        # up-to-date assertion. A bare docs file settles cleanly.
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "guide.md").write_text("## Intro\n\nHello.\n", encoding="utf-8")

    def test_same_precision_class_no_reembed(self):
        """AC-2: a same-class provider/format swap (both "full") does NOT force a re-embed — the
        1p517 FP16<->FP32 interchangeability invariant is preserved."""
        self._make_docs_only_repo()
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_predicted_precision_class", return_value="full"), \
             patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            self.bi.build_index(self.root, full=True, content="docs", verbose=False)
            # Second pass, SAME predicted class, no file changes → up-to-date (no rebuild, no embed).
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        self.assertTrue(result.get("up_to_date", False), "same class + no changes must be a no-op")

    def test_legacy_bare_name_index_not_rebuilt_when_full(self):
        """AC-3: a legacy index whose model_versions has a bare name (no @class) is treated as
        "full" and must NOT spuriously rebuild when the machine also predicts "full"."""
        self._make_docs_only_repo()
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_predicted_precision_class", return_value="full"), \
             patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            self.bi.build_index(self.root, full=True, content="docs", verbose=False)
            _idx = self.root / ".wavefoundry" / "index"
            meta = _read_meta_store(_idx)
            meta["model_versions"]["docs"] = self.bi.DOCS_MODEL  # legacy bare name, no @class
            _seed_meta_store(_idx, meta)
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        self.assertTrue(result.get("up_to_date", False), "legacy bare-name (== full) must not rebuild")


class WalkerVersionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.bi = load_build_index()

    def tearDown(self):
        self.tmp.cleanup()

    def _write_meta(self, extra: dict) -> Path:
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        base = {
            "model_versions": {
                "docs": self.bi.DOCS_MODEL,
                "code": self.bi.CODE_MODEL,
            },
            "chunker_versions": {
                "docs": self.bi._get_chunker().CHUNKER_VERSION,
                "code": self.bi._get_chunker().CHUNKER_VERSION,
            },
            "content": ["docs", "code"],
            "file_meta": {},
        }
        base.update(extra)
        _seed_meta_store(index_dir, base)
        return index_dir

    def test_legacy_index_missing_walker_version_triggers_rebuild(self):
        """An index built before walker versioning has no walker_version key — must rebuild."""
        _make_repo(self.root, {"src/foo.md": "## Guide\n\nContent.\n"})
        self._write_meta({})  # no walker_version key
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        self.assertFalse(result.get("up_to_date", False))
        meta = _read_meta_store(self.root / ".wavefoundry" / "index")
        self.assertEqual(meta["walker_version"], self.bi.WALKER_VERSION)

    def test_stale_walker_version_triggers_rebuild(self):
        """An index with an older walker_version must be fully rebuilt."""
        _make_repo(self.root, {"src/foo.md": "## Guide\n\nContent.\n"})
        self._write_meta({"walker_version": "0"})
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        self.assertFalse(result.get("up_to_date", False))
        meta = _read_meta_store(self.root / ".wavefoundry" / "index")
        self.assertEqual(meta["walker_version"], self.bi.WALKER_VERSION)

    def test_current_walker_version_does_not_force_rebuild(self):
        """An up-to-date walker_version does not contribute to a forced rebuild."""
        _make_repo(self.root, {"src/foo.md": "## Guide\n\nContent.\n"})
        current_wv = self.bi.WALKER_VERSION
        self._write_meta({"walker_version": current_wv})
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        meta = _read_meta_store(self.root / ".wavefoundry" / "index")
        self.assertEqual(meta["walker_version"], current_wv)


class OnnxProviderSelectionTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_build_index()

    def _providers(self, available: list[str]) -> list[str]:
        with patch.object(self.mod.provider_policy, "available_onnx_providers", return_value=tuple(available)):
            with patch.dict(os.environ, {}, clear=True):
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

    def test_setup_validated_coreml_handoff_is_honored(self):
        with patch.object(
            self.mod.provider_policy,
            "available_onnx_providers",
            return_value=("CoreMLExecutionProvider", "CPUExecutionProvider"),
        ):
            with patch.dict(
                os.environ,
                {"WAVEFOUNDRY_EMBED_PROVIDER_SELECTED": "CoreMLExecutionProvider"},
                clear=True,
            ):
                providers = self.mod._onnx_providers()
        self.assertEqual(providers, ["CoreMLExecutionProvider", "CPUExecutionProvider"])

    def test_onnxruntime_import_error_returns_cpu(self):
        with patch.object(self.mod.provider_policy, "available_onnx_providers", return_value=("CPUExecutionProvider",)):
            result = self.mod._onnx_providers()
        self.assertEqual(result, ["CPUExecutionProvider"])


# ---------------------------------------------------------------------------
# _make_lance_rows null-normalization tests (12qmp-bug)
# ---------------------------------------------------------------------------

class MakeLanceRowsNullNormalizationTests(unittest.TestCase):
    """AC-1 / AC-2: None language/section are normalized to '' before LanceDB write."""

    def setUp(self):
        self.mod = load_build_index()

    def _make_vec(self, dim=4):
        import numpy as np
        return np.zeros(dim, dtype=np.float32)

    def _call(self, chunk):
        import numpy as np
        vecs = np.zeros((1, 4), dtype=np.float32)
        return self.mod._make_lance_rows([chunk], vecs)[0]

    def test_language_none_normalized_to_empty_string(self):
        """AC-1: language=None in chunk dict produces row['language']==''."""
        chunk = {"text": "hello", "path": "docs/a.md", "kind": "doc", "language": None, "section": "Intro"}
        row = self._call(chunk)
        self.assertEqual(row["language"], "")

    def test_section_none_normalized_to_empty_string(self):
        """AC-2: section=None in chunk dict produces row['section']==''."""
        chunk = {"text": "hello", "path": "docs/a.md", "kind": "doc", "language": "markdown", "section": None}
        row = self._call(chunk)
        self.assertEqual(row["section"], "")

    def test_both_none_normalized(self):
        """Both language and section None in same chunk are both normalized."""
        chunk = {"text": "hello", "path": "docs/a.md", "kind": "doc", "language": None, "section": None}
        row = self._call(chunk)
        self.assertEqual(row["language"], "")
        self.assertEqual(row["section"], "")

    def test_non_none_values_preserved(self):
        """Non-None language/section values are not modified."""
        chunk = {"text": "fn foo()", "path": "src/a.py", "kind": "function", "language": "python", "section": "auth"}
        row = self._call(chunk)
        self.assertEqual(row["language"], "python")
        self.assertEqual(row["section"], "auth")

    def test_original_chunk_not_mutated(self):
        """_make_lance_rows must not mutate the input chunk dict."""
        chunk = {"text": "x", "path": "a.md", "kind": "doc", "language": None, "section": None}
        self._call(chunk)
        self.assertIsNone(chunk["language"])
        self.assertIsNone(chunk["section"])


class PlanLanceDeltaRowsTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_build_index()

    def _chunk(self, chunk_id: str, text: str) -> dict:
        return {"id": chunk_id, "text": text, "path": "src/a.py", "kind": "function"}

    def test_missing_chunk_hash_key_forces_full_rebuild(self):
        existing = [{"id": "c1", "text": "old"}]  # no chunk_hash key
        new_chunks = [self._chunk("c1", "new")]
        delete_ids, rows_to_add, fallback_required, stats = self.mod._plan_lance_delta_rows(
            existing_rows=existing,
            new_chunks=new_chunks,
            embedder=_make_embedder_mock(),
            label="project",
        )
        self.assertTrue(fallback_required)
        self.assertEqual(delete_ids, set())
        self.assertEqual(rows_to_add, [])

    def test_empty_chunk_hash_value_forces_full_rebuild(self):
        existing = [{"id": "c1", "text": "old", "chunk_hash": "   "}]  # present but blank
        new_chunks = [self._chunk("c1", "new")]
        delete_ids, rows_to_add, fallback_required, stats = self.mod._plan_lance_delta_rows(
            existing_rows=existing,
            new_chunks=new_chunks,
            embedder=_make_embedder_mock(),
            label="project",
        )
        self.assertTrue(fallback_required)


# ---------------------------------------------------------------------------
# Wave 1p3b9 (1p399): drift detection between file_meta and Lance
# ---------------------------------------------------------------------------

class LanceDriftDetectionTests(unittest.TestCase):
    """AC-1, AC-2, AC-7, AC-8: `_detect_lance_drift` returns the file_meta
    paths that have zero rows in any Lance table — those are "drifted" and
    must be re-chunked even when file_meta hash matches.

    Tests use mocked Lance access since the surface is set-difference logic;
    full end-to-end is covered by the incremental-build tests when run with
    LanceDB available in the tool venv."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_db_with_paths(self, table_to_paths: dict[str, set[str]]):
        """Build a mock LanceDB-like object whose tables expose the given path
        sets via `.to_arrow().column("path").to_pylist()`."""
        from unittest.mock import MagicMock
        db = MagicMock()

        def open_table(name):
            paths = list(table_to_paths.get(name, set()))
            tbl = MagicMock()
            arrow = MagicMock()
            col = MagicMock()
            col.to_pylist.return_value = paths
            arrow.column.return_value = col
            tbl.to_arrow.return_value = arrow
            return tbl

        db.open_table.side_effect = open_table
        return db

    def _index_dir_with_tables(self, table_names: set[str]) -> Path:
        """Create the table directory markers `_detect_lance_drift` looks for."""
        index_dir = self.root / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        for t in table_names:
            (index_dir / f"{t}.lance").mkdir(exist_ok=True)
        return index_dir

    def _as_meta(self, paths, chunks_emitted=None):
        """Build the dict shape `_detect_lance_drift` expects (wave 1p3iw).
        Empty dict per entry means `chunks_emitted` is absent → falls through
        to the drift check unchanged (legacy / first-pass behavior).
        Pass `chunks_emitted=0` (or a mapping) to test the skip behavior."""
        if chunks_emitted is None:
            return {p: {} for p in paths}
        if isinstance(chunks_emitted, dict):
            return {p: ({"chunks_emitted": chunks_emitted[p]} if p in chunks_emitted else {}) for p in paths}
        # Scalar — apply to every path
        return {p: {"chunks_emitted": chunks_emitted} for p in paths}

    def test_returns_empty_when_file_meta_empty(self):
        result = self.bi._detect_lance_drift(
            self.root, {}, chunk_eligible_rel_paths={"docs/a.md"}, verbose=False,
        )
        self.assertEqual(result, set())

    def test_returns_empty_when_no_lance_tables_present(self):
        # No `.lance` dirs at index_dir → fresh layer, no drift
        result = self.bi._detect_lance_drift(
            self.root,
            self._as_meta({"docs/a.md"}),
            chunk_eligible_rel_paths={"docs/a.md"},
            verbose=False,
        )
        self.assertEqual(result, set())

    def test_detects_drift_when_path_missing_from_lance(self):
        """AC-1, AC-2: a path claimed by file_meta but absent from Lance is
        returned as drifted."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        db = self._make_db_with_paths({"docs": {"docs/present.md"}})
        with patch.object(self.bi, "_get_lance_db", return_value=db):
            result = self.bi._detect_lance_drift(
                index_dir,
                self._as_meta({"docs/present.md", "docs/drifted.md"}),
                chunk_eligible_rel_paths={"docs/present.md", "docs/drifted.md"},
                verbose=False,
            )
        self.assertEqual(result, {"docs/drifted.md"})

    def test_no_drift_when_file_meta_and_lance_agree(self):
        """AC-5, AC-8 (happy path): when every file_meta path has Lance rows,
        return empty set; the incremental skip-on-hash-match optimization is
        preserved unchanged."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs", "code"})
        db = self._make_db_with_paths({
            "docs": {"docs/a.md", "docs/b.md"},
            "code": {"src/foo.py"},
        })
        with patch.object(self.bi, "_get_lance_db", return_value=db):
            result = self.bi._detect_lance_drift(
                index_dir,
                self._as_meta({"docs/a.md", "docs/b.md", "src/foo.py"}),
                chunk_eligible_rel_paths={"docs/a.md", "docs/b.md", "src/foo.py"},
                verbose=False,
            )
        self.assertEqual(result, set())

    def test_drift_detection_unions_across_tables(self):
        """AC-3: a file_meta path counts as "indexed" if it appears in ANY
        Lance table (docs OR code). A path in both file_meta and either Lance
        table is not drifted."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs", "code"})
        db = self._make_db_with_paths({
            "docs": {"docs/a.md"},
            "code": {"src/foo.py"},
        })
        with patch.object(self.bi, "_get_lance_db", return_value=db):
            result = self.bi._detect_lance_drift(
                index_dir,
                self._as_meta({"docs/a.md", "src/foo.py", "docs/missing.md"}),
                chunk_eligible_rel_paths={"docs/a.md", "src/foo.py", "docs/missing.md"},
                verbose=False,
            )
        self.assertEqual(result, {"docs/missing.md"})

    def test_lance_open_failure_returns_empty_set(self):
        """Defensive: if Lance can't be opened, treat as "no drift detected"
        rather than spuriously flagging everything. The reaper / build path
        handles the table-missing case separately."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        with patch.object(self.bi, "_get_lance_db", side_effect=RuntimeError("simulated")):
            result = self.bi._detect_lance_drift(
                index_dir,
                self._as_meta({"docs/a.md"}),
                chunk_eligible_rel_paths={"docs/a.md"},
                verbose=False,
            )
        self.assertEqual(result, set())

    # --- Wave 1p3iw: chunks_emitted skip behavior ---

    def test_excludes_path_with_chunks_emitted_zero(self):
        """AC-2 (1p3iw): a path with explicit ``chunks_emitted == 0`` in its
        file_meta entry is excluded from the drift check — the prior run
        recorded that this file legitimately produces zero chunks, so its
        absence from Lance is expected, not drift."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        db = self._make_db_with_paths({"docs": {"docs/present.md"}})
        file_meta = {
            "docs/present.md": {},
            "docs/empty.md": {"chunks_emitted": 0},
        }
        with patch.object(self.bi, "_get_lance_db", return_value=db):
            result = self.bi._detect_lance_drift(
                index_dir, file_meta,
                chunk_eligible_rel_paths=set(file_meta), verbose=False,
            )
        self.assertEqual(result, set())

    def test_includes_path_with_chunks_emitted_field_absent(self):
        """AC-3 (1p3iw): a path with no ``chunks_emitted`` field (legacy
        meta.json, or fresh stat-mismatch entry from `_detect_changes`) falls
        through to the drift check unchanged — one repair attempt learns the
        true count. (1rmaf narrowing guard: the eligibility set INCLUDES the
        zero-row path, so the flag here is attributable to the field logic —
        an over-broad eligibility exclusion would turn this test red.)"""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        db = self._make_db_with_paths({"docs": {"docs/present.md"}})
        file_meta = {
            "docs/present.md": {},
            "docs/legacy-missing.md": {},  # No chunks_emitted field
        }
        with patch.object(self.bi, "_get_lance_db", return_value=db):
            result = self.bi._detect_lance_drift(
                index_dir, file_meta,
                chunk_eligible_rel_paths=set(file_meta), verbose=False,
            )
        self.assertEqual(result, {"docs/legacy-missing.md"})

    def test_includes_path_with_chunks_emitted_positive_but_lance_missing(self):
        """AC-4 (1p3iw): a path with ``chunks_emitted > 0`` recorded but
        absent from Lance is real drift — the indexer believed it emitted N
        chunks last time, Lance has 0 rows for it now. Must converge by
        re-chunk + re-embed. (1rmaf narrowing guard: the zero-row path is in
        the eligibility set, so positive-field drift on ELIGIBLE paths must
        keep repairing — the 1p3b9 contract narrows only by eligibility.)"""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        db = self._make_db_with_paths({"docs": {"docs/present.md"}})
        file_meta = {
            "docs/present.md": {"chunks_emitted": 3},
            "docs/real-drift.md": {"chunks_emitted": 5},
        }
        with patch.object(self.bi, "_get_lance_db", return_value=db):
            result = self.bi._detect_lance_drift(
                index_dir, file_meta,
                chunk_eligible_rel_paths=set(file_meta), verbose=False,
            )
        self.assertEqual(result, {"docs/real-drift.md"})

    def test_thrash_regression_zero_chunk_file_skipped_on_subsequent_updates(self):
        """AC-7 (1p3iw): the thrash regression — a file with `chunks_emitted=0`
        is NOT returned as drifted, even when called repeatedly. This is the
        observable contract that distinguishes the fix from the prior
        behavior. On pre-fix code: every call returned the path. On post-fix:
        no call does."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        db = self._make_db_with_paths({"docs": set()})  # Lance has zero rows
        file_meta = {"docs/legitimately-empty.md": {"chunks_emitted": 0}}
        eligible = set(file_meta)
        with patch.object(self.bi, "_get_lance_db", return_value=db):
            r1 = self.bi._detect_lance_drift(
                index_dir, file_meta, chunk_eligible_rel_paths=eligible, verbose=False)
            r2 = self.bi._detect_lance_drift(
                index_dir, file_meta, chunk_eligible_rel_paths=eligible, verbose=False)
            r3 = self.bi._detect_lance_drift(
                index_dir, file_meta, chunk_eligible_rel_paths=eligible, verbose=False)
        self.assertEqual(r1, set())
        self.assertEqual(r2, set())
        self.assertEqual(r3, set())

    def test_chunks_for_file_returns_empty_on_empty_input(self):
        """AC-5 (1p3iw) — data path for the chunks_emitted population: an
        empty source produces no doc and no code chunks. The build_index
        loop computes `len(dc) + len(cc) == 0` and persists that as
        chunks_emitted=0, which the next-update drift check uses to skip."""
        dc, cc = self.bi._chunks_for_file("docs/empty.md", "")
        self.assertEqual(dc, [])
        self.assertEqual(cc, [])

    def test_chunks_for_file_returns_empty_on_marker_region_only_content(self):
        """AC-5 (1p3jc): renderer-owned marker-region-only files produce no
        semantic chunks, so chunks_emitted remains 0 and drift detection skips
        them on subsequent updates."""
        source = "<!-- waveframework:agent-surface begin -->\nGenerated\n<!-- end -->\n"
        dc, cc = self.bi._chunks_for_file("src/generated.py", source)
        self.assertEqual(dc, [])
        self.assertEqual(cc, [])

    def test_chunks_for_file_returns_nonempty_on_real_content(self):
        """AC-5 (1p3iw) — the contrapositive: a normal markdown file emits
        chunks; chunks_emitted would be > 0."""
        dc, cc = self.bi._chunks_for_file(
            "docs/sample.md",
            "# Title\n\nThis is a test paragraph with enough content to chunk.\n",
        )
        self.assertGreaterEqual(len(dc) + len(cc), 1)

    # --- 1rmaf: chunk-eligibility gate (drift candidacy scoped to files_for_content) ---

    def test_excludes_chunk_ineligible_path_field_absent(self):
        """1rmaf AC-1 (helper level): a meta-tracked, zero-row path with NO
        ``chunks_emitted`` field is NOT flagged when it lies outside the
        current build's chunk-eligible set — the repair path could never
        reach it, so flagging it would loop forever (the live defect)."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        db = self._make_db_with_paths({"docs": {"docs/present.md"}})
        file_meta = {
            "docs/present.md": {},
            ".wavefoundry/framework/scripts/tests/test_x.py": {},  # excluded upstream
        }
        with patch.object(self.bi, "_get_lance_db", return_value=db):
            result = self.bi._detect_lance_drift(
                index_dir, file_meta,
                chunk_eligible_rel_paths={"docs/present.md"}, verbose=False,
            )
        self.assertEqual(result, set())

    def test_excludes_chunk_ineligible_path_stale_positive_field(self):
        """1rmaf Req-2: an ineligible zero-row path carrying a STALE POSITIVE
        ``chunks_emitted`` (recorded under earlier include flags) is likewise
        not flagged — eligibility, not the recorded count, is the primary
        gate."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs", "code"})
        db = self._make_db_with_paths({"docs": {"docs/present.md"}, "code": set()})
        file_meta = {
            "docs/present.md": {},
            "tests/test_helper.py": {"chunks_emitted": 99},  # stale positive, now excluded
        }
        with patch.object(self.bi, "_get_lance_db", return_value=db):
            result = self.bi._detect_lance_drift(
                index_dir, file_meta,
                chunk_eligible_rel_paths={"docs/present.md"}, verbose=False,
            )
        self.assertEqual(result, set())

    def test_eligible_zero_row_path_still_flagged_alongside_ineligible_skip(self):
        """1rmaf AC-2 guard: the eligibility gate must narrow, not weaken —
        an ELIGIBLE zero-row path is still flagged in the same call that
        skips an ineligible one."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        db = self._make_db_with_paths({"docs": {"docs/present.md"}})
        file_meta = {
            "docs/present.md": {},
            "docs/drifted.md": {},
            ".wavefoundry/framework/scripts/tests/test_x.py": {},
        }
        with patch.object(self.bi, "_get_lance_db", return_value=db):
            result = self.bi._detect_lance_drift(
                index_dir, file_meta,
                chunk_eligible_rel_paths={"docs/present.md", "docs/drifted.md"},
                verbose=False,
            )
        self.assertEqual(result, {"docs/drifted.md"})

    def test_verbose_logs_ineligible_skip_count_with_reason(self):
        """1rmaf AC-5 (log shape): when verbose, the ineligible-skip count is
        logged WITH the reason, distinguishable from genuine drift repairs."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        db = self._make_db_with_paths({"docs": {"docs/present.md"}})
        file_meta = {
            "docs/present.md": {},
            ".wavefoundry/framework/scripts/tests/test_x.py": {},
        }
        out = io.StringIO()
        with patch.object(self.bi, "_get_lance_db", return_value=db), \
                contextlib.redirect_stdout(out):
            result = self.bi._detect_lance_drift(
                index_dir, file_meta,
                chunk_eligible_rel_paths={"docs/present.md"}, verbose=True,
            )
        self.assertEqual(result, set())
        self.assertIn(
            "drift-detect skipped 1 path(s) as chunk-ineligible "
            "(outside this build's content filters)",
            out.getvalue(),
        )

    def test_verbose_no_ineligible_line_when_all_paths_eligible(self):
        """1rmaf AC-5 (log shape, contrapositive): no ineligible-skip line
        when every meta path is chunk-eligible — quiet logs stay quiet."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        db = self._make_db_with_paths({"docs": {"docs/present.md"}})
        file_meta = {"docs/present.md": {}}
        out = io.StringIO()
        with patch.object(self.bi, "_get_lance_db", return_value=db), \
                contextlib.redirect_stdout(out):
            self.bi._detect_lance_drift(
                index_dir, file_meta,
                chunk_eligible_rel_paths={"docs/present.md"}, verbose=True,
            )
        self.assertNotIn("chunk-ineligible", out.getvalue())


class LanceDriftDetectionScaleTests(unittest.TestCase):
    """AC-9 / MF-1: drift query latency on enterprise-scale corpora.

    Bounds:
    - 10K rows → sub-second (1.0s)
    - 100K rows → < 200ms

    Synthetic test: the bottleneck is the file_meta set-difference against a
    paths set; the Lance query is mocked. This measures the set-difference
    half (always cheap) and the Python-level path enumeration (the actual
    overhead). A real-Lance scale benchmark is out of scope (would require
    actual LanceDB infrastructure); this test guards against accidental
    O(N²) regressions in the set-difference + diagnostic-formatting path."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _index_dir_with_tables(self, table_names: set[str]) -> Path:
        index_dir = self.root / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        for t in table_names:
            (index_dir / f"{t}.lance").mkdir(exist_ok=True)
        return index_dir

    def _run_with_n_rows(self, n_rows: int) -> float:
        """Run a drift-check with `n_rows` Lance paths and a 1% drifted
        set (≈ n_rows / 100 paths claimed by file_meta but absent from
        Lance). Returns elapsed seconds."""
        from unittest.mock import MagicMock, patch
        import time

        lance_paths = [f"docs/file-{i:07d}.md" for i in range(n_rows)]
        # file_meta = all Lance paths + a small drift set
        n_drifted = max(1, n_rows // 100)
        drifted_paths = [f"docs/drifted-{i:07d}.md" for i in range(n_drifted)]
        # Wave 1p3iw: drift check now takes the file_meta dict (not just paths).
        # Empty entry per path → no chunks_emitted field → falls through to
        # the original drift detection unchanged.
        file_meta = {p: {} for p in (set(lance_paths) | set(drifted_paths))}

        db = MagicMock()
        def open_table(name):
            tbl = MagicMock()
            arrow = MagicMock()
            col = MagicMock()
            col.to_pylist.return_value = lance_paths if name == "docs" else []
            arrow.column.return_value = col
            tbl.to_arrow.return_value = arrow
            return tbl
        db.open_table.side_effect = open_table

        index_dir = self._index_dir_with_tables({"docs"})

        with patch.object(self.bi, "_get_lance_db", return_value=db):
            t0 = time.perf_counter()
            result = self.bi._detect_lance_drift(
                index_dir, file_meta,
                chunk_eligible_rel_paths=set(file_meta), verbose=False,
            )
            elapsed = time.perf_counter() - t0
        self.assertEqual(len(result), n_drifted)
        return elapsed

    def test_10k_rows_sub_second(self):
        """AC-9: 10K Lance rows + ~100 drifted paths → < 1.0 second."""
        elapsed = self._run_with_n_rows(10_000)
        self.assertLess(elapsed, 1.0,
            f"10K-row drift detection took {elapsed:.3f}s (expected < 1.0s)")

    def test_100k_rows_under_200ms(self):
        """AC-9 / MF-1: 100K Lance rows + ~1000 drifted paths → < 200ms.
        Enterprise-scale bound for large-monorepo-shape repos."""
        elapsed = self._run_with_n_rows(100_000)
        self.assertLess(elapsed, 0.2,
            f"100K-row drift detection took {elapsed:.3f}s (expected < 0.2s)")


class LanceDriftEligibilityBuildTests(unittest.TestCase):
    """1rmaf: end-to-end drift-eligibility behavior through ``build_index``.

    The live defect: ``meta.json`` tracks the full walked set but
    ``chunks_emitted`` is only ever recorded for files that pass the content
    filters, so a meta-tracked, chunking-excluded, zero-row file was drift-
    flagged on EVERY incremental build — a non-converging repair loop that
    nullified the zero-change fast path. Fixtures mirror the live shape:
    a ``.wavefoundry/framework/scripts`` file made meta-trackable via the
    workflow-config code prefix but chunk-INELIGIBLE in docs mode (the
    post-edit hook's default content mode, where the live loop manifested).
    """

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_docs_mode_repo(self) -> str:
        """Repo where a framework-script file is meta-tracked (docs+code
        graph surface) but outside the docs content walk (under the
        ``.wavefoundry/`` blanket exclusion, not in the docs include set).
        Returns the excluded file's rel path."""
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps({
                "lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0},
                "indexing": {
                    "project_include_prefixes": {
                        "docs": [],
                        "code": [".wavefoundry/framework/scripts"],
                    },
                },
            }),
            encoding="utf-8",
        )
        (self.root / "docs" / "guide.md").write_text(
            "## Intro\n\nEnough real content to emit at least one docs chunk.\n",
            encoding="utf-8",
        )
        util = self.root / ".wavefoundry" / "framework" / "scripts" / "util.py"
        util.parent.mkdir(parents=True, exist_ok=True)
        util.write_text("def util():\n    return 1\n", encoding="utf-8")
        return ".wavefoundry/framework/scripts/util.py"

    def _build(self, *, full=False, content="docs", include_tests=False, verbose=False):
        """Run build_index with a mocked embedder; returns (result, stderr, stdout)."""
        err, out = io.StringIO(), io.StringIO()
        with patch.object(self.bi, "_get_embedder", return_value=_make_embedder_mock(dim=4)), \
                redirect_stderr(err), contextlib.redirect_stdout(out):
            result = self.bi.build_index(
                self.root, full=full, content=content,
                include_tests=include_tests, verbose=verbose,
            )
        return result, err.getvalue(), out.getvalue()

    def _meta(self) -> dict:
        return _read_meta_store(self.root / ".wavefoundry" / "index")

    def _neutralize_per_kind_residual(self) -> None:
        """Pin ``docs/workflow-config.json``'s ``chunks_emitted`` to 0 after a
        docs-only full build. The file emits only code-KIND chunks, so a
        docs-only build records a positive count while writing zero rows —
        the per-kind residual the change doc names as deferred out-of-scope
        (it would otherwise be drift-flagged here and drown the assertions).
        On the live repo the equivalent files have code-table rows from
        all-mode setup; pinning the field keeps these fixtures focused on
        the ELIGIBILITY defect under test."""
        index_dir = self.root / ".wavefoundry" / "index"
        meta = self._meta()
        entry = meta["file_meta"].get("docs/workflow-config.json")
        if entry is not None:
            entry["chunks_emitted"] = 0
            _seed_meta_store(index_dir, meta)

    def test_ac1_docs_mode_excluded_zero_row_file_field_absent_never_flagged(self):
        """AC-1 (field absent): meta-tracked + chunking-excluded + zero rows →
        zero drift flags across two consecutive incremental docs builds."""
        rel = self._make_docs_mode_repo()
        self._build(full=True, content="docs")
        file_meta = self._meta().get("file_meta", {})
        # Fixture validity: meta-tracked, never chunked (field absent) — the
        # exact live-loop state. A self-healing fixture would prove nothing.
        self.assertIn(rel, file_meta)
        self.assertNotIn("chunks_emitted", file_meta[rel])
        self._neutralize_per_kind_residual()
        for i in (1, 2):
            result, err, _ = self._build(full=False, content="docs")
            self.assertNotIn("repairing", err,
                f"incremental build {i} drift-flagged the chunk-ineligible file:\n{err}")
            self.assertTrue(result.get("up_to_date"),
                f"incremental build {i} should be a no-op")

    def test_ac1_docs_mode_excluded_zero_row_file_stale_positive_never_flagged(self):
        """AC-1 (stale positive): the same excluded file carrying a stale
        positive ``chunks_emitted`` (recorded under earlier include flags) is
        likewise never flagged — eligibility is the primary gate."""
        rel = self._make_docs_mode_repo()
        self._build(full=True, content="docs")
        self._neutralize_per_kind_residual()
        index_dir = self.root / ".wavefoundry" / "index"
        meta = self._meta()
        meta["file_meta"][rel]["chunks_emitted"] = 7  # stale positive
        _seed_meta_store(index_dir, meta)
        for i in (1, 2):
            result, err, _ = self._build(full=False, content="docs")
            self.assertNotIn("repairing", err,
                f"incremental build {i} drift-flagged the stale-positive excluded file:\n{err}")
            self.assertTrue(result.get("up_to_date"))

    def test_ac2_eligible_zero_row_file_still_repaired_then_quiet(self):
        """AC-2 guard: a chunk-ELIGIBLE file with zero Lance rows is still
        drift-flagged and repaired; the repair records ``chunks_emitted`` and
        the next build is quiet."""
        self._make_docs_mode_repo()
        self._build(full=True, content="docs")
        self._neutralize_per_kind_residual()
        index_dir = self.root / ".wavefoundry" / "index"
        # Simulate real drift: rows vanish for an eligible docs file.
        import lancedb
        db = lancedb.connect(str(index_dir))
        db.open_table("docs").delete("path = 'docs/guide.md'")
        result, err, _ = self._build(full=False, content="docs")
        self.assertIn("repairing 1 drifted file(s)", err)
        self.assertIn("docs/guide.md", err)
        rows = _read_index_chunks(index_dir, "docs")
        self.assertIn("docs/guide.md", {r.get("path") for r in rows},
            "repair must restore the eligible file's rows")
        self.assertGreater(
            self._meta()["file_meta"]["docs/guide.md"].get("chunks_emitted", 0), 0)
        result2, err2, _ = self._build(full=False, content="docs")
        self.assertNotIn("repairing", err2, "repaired file must converge")
        self.assertTrue(result2.get("up_to_date"))

    def test_ac3_include_tests_flip_makes_excluded_file_eligible_flagged_repaired(self):
        """AC-3 (code mode, ``_is_test_code_path`` class): with the flag off
        the test file is never flagged; flipping ``--include-tests`` on makes
        it eligible → flagged → repaired; the next build is quiet. Eligibility
        is computed per build from the current filters, never persisted."""
        _make_repo(self.root, {
            "src/foo.py": "def foo():\n    return 1\n",
            "tests/test_helper.py": "def test_helper():\n    assert 1 + 1 == 2\n",
        })
        rel = "tests/test_helper.py"
        self._build(full=True, content="code", include_tests=False)
        file_meta = self._meta().get("file_meta", {})
        # Fixture validity: meta-tracked, excluded by the flag-sensitive
        # layer (NOT the unconditional framework-test carve-out), zero rows.
        self.assertIn(rel, file_meta)
        self.assertNotIn("chunks_emitted", file_meta[rel])
        result, err, _ = self._build(full=False, content="code", include_tests=False)
        self.assertNotIn("repairing", err,
            f"flag off: excluded test file must not be drift-flagged:\n{err}")
        result, err, _ = self._build(full=False, content="code", include_tests=True)
        self.assertIn("repairing 1 drifted file(s)", err,
            f"flag on: newly eligible zero-row file must be flagged:\n{err}")
        self.assertIn(rel, err)
        meta_after = self._meta()["file_meta"][rel]
        self.assertGreater(meta_after.get("chunks_emitted", 0), 0,
            "repair must record the true chunk count")
        rows = _read_index_chunks(self.root / ".wavefoundry" / "index", "code")
        self.assertIn(rel, {r.get("path") for r in rows})
        result, err, _ = self._build(full=False, content="code", include_tests=True)
        self.assertNotIn("repairing", err, "repaired file must converge")
        self.assertTrue(result.get("up_to_date"))

    def test_ac6_graph_only_incremental_performs_no_drift_detection(self):
        """AC-6 (write-capability guard, Req-7): a ``content="graph"``
        incremental build never calls ``_detect_lance_drift`` — in that mode
        ``files_for_content`` is the UNFILTERED code walk while zero semantic
        rows are writable, so any eligibility intersection would be a no-op
        and the loop would survive."""
        self._make_docs_mode_repo()
        self._build(full=True, content="docs")
        calls: list = []
        def spy(*args, **kwargs):
            calls.append((args, kwargs))
            return set()
        err = io.StringIO()
        with patch.object(self.bi, "_detect_lance_drift", side_effect=spy), \
                redirect_stderr(err):
            self.bi.build_index(self.root, full=False, content="graph", verbose=False)
        self.assertEqual(calls, [], "graph-only build must skip drift detection outright")
        self.assertNotIn("repairing", err.getvalue())

    def test_ac6_graph_only_incremental_no_repair_log_and_verbose_reason(self):
        """AC-6 (unpatched) + AC-5: the real graph-only incremental flags
        nothing — the "repairing N drifted file(s)" stderr line is ABSENT
        even with a meta-tracked zero-row file present — and the verbose skip
        line states the REASON so quiet builds are distinguishable from
        no-drift builds in field logs."""
        rel = self._make_docs_mode_repo()
        self._build(full=True, content="docs")
        self.assertNotIn("chunks_emitted", self._meta()["file_meta"][rel])
        err, out = io.StringIO(), io.StringIO()
        with redirect_stderr(err), contextlib.redirect_stdout(out):
            self.bi.build_index(self.root, full=False, content="graph", verbose=True)
        self.assertNotIn("repairing", err.getvalue())
        self.assertIn("no semantic writes this build", out.getvalue())

    def test_idle_reap_still_receives_wide_meta_union(self):
        """1rmaf security tripwire (Req-8): the idle-path
        ``_reap_stranded_lance_rows`` call still receives the WIDE meta union
        — including chunk-INELIGIBLE paths — never the narrow eligibility
        set. The zero-change fast path is the common path post-fix; a set
        mix-up here would be high-frequency destructive (a docs-only run
        would reap every code-table row)."""
        rel = self._make_docs_mode_repo()
        self._build(full=True, content="docs")
        self._neutralize_per_kind_residual()
        captured: dict = {}
        def fake_reap(db_path, eligible_paths, **kwargs):
            captured["eligible_paths"] = set(eligible_paths)
            return {"total": 0}
        err = io.StringIO()
        with patch.object(self.bi, "_reap_stranded_lance_rows", side_effect=fake_reap), \
                patch.object(self.bi, "_get_embedder", return_value=_make_embedder_mock(dim=4)), \
                redirect_stderr(err):
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        self.assertTrue(result.get("up_to_date"))
        self.assertIn("eligible_paths", captured, "idle reap must run on the fast path")
        self.assertEqual(captured["eligible_paths"], set(self._meta()["file_meta"].keys()))
        self.assertIn(rel, captured["eligible_paths"],
            "the chunk-INELIGIBLE path must stay in the reaper's wide union")


class OversizedFileGuardTests(unittest.TestCase):
    """Wave 1p5c4: walk_repo drops files over the hard size cap so a multi-GB blob (e.g. a SQL
    backup) is never read or tree-sitter-parsed."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_config(self, indexing: dict) -> None:
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps({"indexing": indexing}), encoding="utf-8")

    def test_walk_repo_skips_oversized_files(self):
        self._write_config({"max_file_bytes": 50})
        (self.root / "small.md").write_text("hi\n", encoding="utf-8")
        (self.root / "big.md").write_text("x" * 500, encoding="utf-8")
        rels = {str(f.relative_to(self.root)).replace("\\", "/") for f in self.bi.walk_repo(self.root)}
        self.assertIn("small.md", rels)
        self.assertNotIn("big.md", rels)

    def test_walk_repo_keeps_all_when_cap_disabled(self):
        self._write_config({"max_file_bytes": 0})  # 0 = no cap
        (self.root / "big.md").write_text("x" * 500, encoding="utf-8")
        rels = {str(f.relative_to(self.root)).replace("\\", "/") for f in self.bi.walk_repo(self.root)}
        self.assertIn("big.md", rels)

    def test_default_cap_keeps_normal_files(self):
        # No override → generous default (5 MB); ordinary source/docs are unaffected.
        (self.root / "code.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        rels = {str(f.relative_to(self.root)).replace("\\", "/") for f in self.bi.walk_repo(self.root)}
        self.assertIn("code.py", rels)

    def test_walk_repo_prunes_gitignored_directories(self):
        # Wave 1p5c4: a gitignored directory (e.g. the LanceDB index dir) must never be walked —
        # we should not even stat the files inside it.
        (self.root / ".gitignore").write_text("ignored_index/\n", encoding="utf-8")
        (self.root / "ignored_index").mkdir()
        (self.root / "ignored_index" / "shard.md").write_text("data\n", encoding="utf-8")
        (self.root / "kept.md").write_text("# Kept\n", encoding="utf-8")
        rels = {str(f.relative_to(self.root)).replace("\\", "/") for f in self.bi.walk_repo(self.root)}
        self.assertIn("kept.md", rels)
        self.assertFalse(any(r.startswith("ignored_index/") for r in rels),
                         f"gitignored dir should not be walked; got {rels}")


class StreamingRebuildParityTests(unittest.TestCase):
    """Wave 1p5ch: the streamed full-rebuild table must be row-identical regardless of buffer size.
    Feeding every chunk in one `add()` IS the batch write (a single create_table with all rows), so
    'one big add' vs 'tiny buffer, many flushes' is the streaming-vs-batch parity check — using only
    the production `_StreamingLayerWriter`, with no separate reference implementation to drift."""

    def setUp(self):
        self.bi = load_build_index()

    @staticmethod
    def _fake_embedder():
        import numpy as np

        class _Fake:
            # Deterministic, finite per-text vector — batching boundaries cannot change it.
            def embed(self, texts, batch_size=256):
                import hashlib as _h
                for t in texts:
                    digest = _h.sha256(t.encode("utf-8")).digest()
                    yield np.array([float(b) for b in digest[:4]], dtype=np.float32)

        return _Fake()

    def _chunks(self, n):
        return [
            {"id": f"f{i}.py::sym{i}", "path": f"f{i}.py", "kind": "code", "language": "python",
             "section": f"sym{i}", "lines": [1, 2], "text": f"def sym{i}(): return {i}"}
            for i in range(n)
        ]

    def test_streamed_table_is_buffer_invariant(self):
        import tempfile
        chunks = self._chunks(25)

        with tempfile.TemporaryDirectory() as ta, tempfile.TemporaryDirectory() as tb:
            # Batch reference: one add() with every chunk == a single create_table with all rows.
            db_a = self.bi._get_lance_db(Path(ta))
            w_a = self.bi._StreamingLayerWriter(db_a, "code", self._fake_embedder(), "code")
            w_a.add([dict(c) for c in chunks])
            w_a.finalize()

            # Streamed: tiny buffer → many flushes / append calls.
            db_b = self.bi._get_lance_db(Path(tb))
            w_b = self.bi._StreamingLayerWriter(db_b, "code", self._fake_embedder(), "code")
            buf = []
            for c in chunks:
                buf.append(dict(c))
                if len(buf) >= 3:
                    w_b.add(buf); buf = []
            if buf:
                w_b.add(buf)
            w_b.finalize()

            rows_a = {r["id"]: r for r in db_a.open_table("code").to_arrow().to_pylist()}
            rows_b = {r["id"]: r for r in db_b.open_table("code").to_arrow().to_pylist()}

        self.assertEqual(set(rows_a), set(rows_b), "streamed table must hold the same chunk ids")
        for cid in rows_a:
            self.assertEqual(rows_a[cid]["text"], rows_b[cid]["text"], cid)
            self.assertEqual(rows_a[cid]["vector"], rows_b[cid]["vector"], cid)
            self.assertEqual(rows_a[cid]["chunk_hash"], rows_b[cid]["chunk_hash"], cid)

    def test_resolve_embed_buffer_chunks_override_and_floor(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            # Honors a sane override.
            (root / "docs" / "workflow-config.json").write_text(
                json.dumps({"indexing": {"embed_buffer_chunks": 5000}}), encoding="utf-8")
            self.assertEqual(self.bi._resolve_embed_buffer_chunks(root), 5000)
            # Floors at EMBED_BATCH_SIZE so GPU batches stay full.
            (root / "docs" / "workflow-config.json").write_text(
                json.dumps({"indexing": {"embed_buffer_chunks": 1}}), encoding="utf-8")
            self.assertEqual(self.bi._resolve_embed_buffer_chunks(root), self.bi.EMBED_BATCH_SIZE)
            # Default when unset.
            (root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")
            self.assertEqual(self.bi._resolve_embed_buffer_chunks(root), self.bi.EMBED_BUFFER_CHUNKS_DEFAULT)
            # 1p7it: the unset default is pinned to 1024 — best build throughput in the on-machine
            # benchmark (peak RSS is buffer-invariant, so this is purely a throughput choice).
            self.assertEqual(self.bi.EMBED_BUFFER_CHUNKS_DEFAULT, 1024)

    def test_resolve_embed_batch_size_per_model_and_global(self):
        # 1p7iv: per-model forward-batch width is independently overridable so docs (arctic-xs) and
        # code (bge-small) need not share a size; smaller batch = less CPU activation memory.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            cfg = root / "docs" / "workflow-config.json"
            DOCS, CODE = self.bi.DOCS_MODEL, self.bi.CODE_MODEL
            # Unset → per-model default, pinned to 32 (the lowest-memory + fastest CPU batch).
            cfg.write_text("{}", encoding="utf-8")
            self.assertEqual(self.bi._DEFAULT_EMBED_BATCH, 32)
            self.assertEqual(self.bi._resolve_embed_batch_size(DOCS, root), 32)
            self.assertEqual(self.bi._resolve_embed_batch_size(CODE, root), 32)
            # Global override applies to both models.
            cfg.write_text(json.dumps({"indexing": {"embed_batch_size": 64}}), encoding="utf-8")
            self.assertEqual(self.bi._resolve_embed_batch_size(DOCS, root), 64)
            self.assertEqual(self.bi._resolve_embed_batch_size(CODE, root), 64)
            # Per-model override wins over the global and is independent per model.
            cfg.write_text(json.dumps({"indexing": {
                "embed_batch_size": 64, "code_embed_batch_size": 32, "docs_embed_batch_size": 128}}),
                encoding="utf-8")
            self.assertEqual(self.bi._resolve_embed_batch_size(CODE, root), 32)
            self.assertEqual(self.bi._resolve_embed_batch_size(DOCS, root), 128)
            # Invalid (non-positive) falls through to the default.
            cfg.write_text(json.dumps({"indexing": {"code_embed_batch_size": 0}}), encoding="utf-8")
            self.assertEqual(self.bi._resolve_embed_batch_size(CODE, root), 32)

    def test_streaming_rebuild_bounds_buffer_and_reports_file_progress(self):
        """AC-1 (memory bound) + AC-4 (file-oriented progress): driving the real
        `_run_streaming_full_rebuild` over many files with a tiny buffer, no single
        embed batch may approach the corpus size — each is bounded by
        ``buffer_chunks + max(per-file chunks)`` — and progress is logged as
        ``indexed file N/M files`` with no total-chunk pre-count."""
        import tempfile, io, contextlib, re
        import unittest.mock as mock

        buffer_chunks = 4
        n_files = 14
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = []
            for i in range(n_files):
                p = root / f"mod{i}.py"
                # Two functions per file → a couple of code chunks each.
                p.write_text(
                    f"def alpha{i}(x):\n    return x + {i}\n\n\ndef beta{i}(y):\n    return y * {i}\n",
                    encoding="utf-8",
                )
                files.append(p)

            db_path = root / "lance"
            chunks_emitted = {}
            sizes = []  # length of every batch handed to the writer (== peak resident buffer at flush)
            orig_add = self.bi._StreamingLayerWriter.add

            def spy_add(writer_self, chunks):
                sizes.append(len(chunks))
                return orig_add(writer_self, chunks)

            out = io.StringIO()
            with mock.patch.object(self.bi._StreamingLayerWriter, "add", spy_add), \
                    contextlib.redirect_stdout(out):
                self.bi._run_streaming_full_rebuild(
                    db_path=db_path,
                    files_to_index=files,
                    root=root,
                    build_docs=False,
                    build_code=True,
                    docs_embedder=None,
                    code_embedder=self._fake_embedder(),
                    chunks_emitted_by_file=chunks_emitted,
                    buffer_chunks=buffer_chunks,
                    verbose=False,
                    docs_elapsed=[],
                    code_elapsed=[],
                )
            log = out.getvalue()

            total_code = self.bi._get_lance_db(db_path).open_table("code").count_rows()

            # AC-1: streamed, not one big write — multiple flushes, and every batch is
            # bounded by the buffer plus a single file's chunk count (corpus-independent).
            self.assertGreaterEqual(len(sizes), 2, "expected multiple flushes (streaming)")
            self.assertEqual(sum(sizes), total_code, "every chunk must be written exactly once")
            max_file_chunks = max(chunks_emitted.values())
            self.assertLessEqual(
                max(sizes), buffer_chunks + max_file_chunks,
                "peak resident buffer must stay bounded by buffer + one file's chunks",
            )
            self.assertLess(max(sizes), total_code, "no single batch may hold the whole corpus")

            # AC-4: file-oriented progress, terminating at N/N, with no total-chunk pre-count.
            self.assertRegex(log, r"indexed file \d+/%d files" % n_files)
            self.assertIn("indexed file %d/%d files" % (n_files, n_files), log)
            self.assertNotIn("/%d code chunks" % total_code, log)
            self.assertNotRegex(log, r"chunks \d+[–-]\d+/\d+")


class CachedFirstEmbedderTests(unittest.TestCase):
    """Wave 1p5cx: the reindex path must load fastembed models from the local HF cache first
    (``local_files_only=True``, no network / no unauthenticated-request warning) and fall back to an
    online download only on a genuine cache miss."""

    def setUp(self):
        self.bi = load_build_index()
        self.bi._EMBEDDER_CACHE.clear()

    def test_cached_first_returns_offline_construct_when_present(self):
        calls = []

        def fake_cls(model_name, providers, local_files_only=False):
            calls.append(local_files_only)
            return f"embedder::{model_name}::lfo={local_files_only}"

        emb = self.bi._text_embedding_cached_first(fake_cls, "m", ["CPUExecutionProvider"])
        self.assertEqual(emb, "embedder::m::lfo=True")
        self.assertEqual(calls, [True], "no online attempt when the cached load succeeds")

    def test_cached_first_falls_back_to_online_on_cache_miss(self):
        calls = []

        def fake_cls(model_name, providers, local_files_only=False):
            calls.append(local_files_only)
            if local_files_only:
                raise RuntimeError("LocalEntryNotFound (simulated cold cache)")
            return f"online::{model_name}"

        emb = self.bi._text_embedding_cached_first(fake_cls, "m", ["CPUExecutionProvider"])
        self.assertEqual(emb, "online::m")
        self.assertEqual(calls, [True, False], "cached-first, then online download fallback")

    def test_get_embedder_uses_cached_first_on_fastembed_path(self):
        seen = []

        class FakeTE:
            def __init__(self, model_name, providers, local_files_only=False):
                seen.append(local_files_only)
                self.model_name = model_name

        # Force the fastembed branch: no accel embedder.
        with patch.object(self.bi, "accel_embedder", None), \
                patch.object(self.bi, "_onnx_providers", return_value=["CPUExecutionProvider"]), \
                patch.dict("sys.modules", {"fastembed": types.SimpleNamespace(TextEmbedding=FakeTE)}):
            emb = self.bi._get_embedder("BAAI/bge-small-en-v1.5")
        self.assertIsInstance(emb, FakeTE)
        self.assertEqual(seen, [True], "fastembed path loads cached-first (local_files_only=True)")


class IncrementalGpuRoutingTests(unittest.TestCase):
    """Wave 1p938: a build run smaller than one full GPU batch (INCREMENTAL_GPU_MIN_CHUNKS) is
    routed to the full-precision CPU fastembed path on a GPU machine, skipping the 64x512 GPU
    accel session's pad-waste. No effect on a CPU-bound machine."""

    def setUp(self):
        self.bi = load_build_index()
        self.bi._EMBEDDER_CACHE.clear()

    def _patch_fastembed(self):
        # Returns a context that forces the fastembed branch to a known sentinel + records the load.
        seen = []

        class FakeTE:
            def __init__(self, model_name, providers, local_files_only=False):
                seen.append(local_files_only)
                self.model_name = model_name
                self.provider = "fastembed-cpu-full"

        return FakeTE, seen

    def test_small_run_on_gpu_machine_uses_cpu_fastembed(self):
        # AC-1 / AC-4: GPU available + n_chunks below threshold → CPU fastembed (full precision),
        # make_embedder (the GPU accel session) is NOT constructed.
        FakeTE, seen = self._patch_fastembed()
        with patch.object(self.bi, "_onnx_providers", return_value=["CoreMLExecutionProvider"]), \
             patch.object(self.bi.accel_embedder, "make_embedder") as mk, \
             patch.dict("sys.modules", {"fastembed": types.SimpleNamespace(TextEmbedding=FakeTE)}):
            emb = self.bi._get_embedder("BAAI/bge-small-en-v1.5", n_chunks=3)
        self.assertIsInstance(emb, FakeTE)
        mk.assert_not_called()
        self.assertEqual(seen, [True], "small run loads fastembed cached-first (full precision)")

    def test_bulk_run_on_gpu_machine_uses_accel(self):
        # AC-2: GPU available + n_chunks at/above threshold → the GPU accel embedder is used
        # unchanged (no small-run CPU detour).
        accel_sentinel = MagicMock()
        accel_sentinel.provider = "CoreMLExecutionProvider"
        with patch.object(self.bi, "_onnx_providers", return_value=["CoreMLExecutionProvider"]), \
             patch.object(self.bi.accel_embedder, "make_embedder", return_value=accel_sentinel) as mk:
            emb = self.bi._get_embedder("BAAI/bge-small-en-v1.5",
                                        n_chunks=self.bi.INCREMENTAL_GPU_MIN_CHUNKS)
        self.assertIs(emb, accel_sentinel)
        mk.assert_called_once()

    def test_cpu_bound_machine_small_run_unchanged(self):
        # AC-3: no GPU → the small-run detour never triggers (no GPU session to skip); make_embedder
        # is still called (it would resolve the INT8-CPU embedder in production).
        accel_sentinel = MagicMock()
        accel_sentinel.provider = "CPUExecutionProvider"
        with patch.object(self.bi, "_onnx_providers", return_value=["CPUExecutionProvider"]), \
             patch.object(self.bi.accel_embedder, "_available_gpu_providers", return_value=[]), \
             patch.object(self.bi.accel_embedder, "make_embedder", return_value=accel_sentinel) as mk:
            emb = self.bi._get_embedder("BAAI/bge-small-en-v1.5", n_chunks=3)
        self.assertIs(emb, accel_sentinel, "CPU-bound machine: small run still uses the resolved embedder")
        mk.assert_called_once()

    def test_no_n_chunks_hint_uses_accel(self):
        # A caller that omits n_chunks (e.g. a full build) never takes the small-run detour.
        accel_sentinel = MagicMock()
        accel_sentinel.provider = "CoreMLExecutionProvider"
        with patch.object(self.bi, "_onnx_providers", return_value=["CoreMLExecutionProvider"]), \
             patch.object(self.bi.accel_embedder, "make_embedder", return_value=accel_sentinel) as mk:
            emb = self.bi._get_embedder("BAAI/bge-small-en-v1.5")  # no n_chunks
        self.assertIs(emb, accel_sentinel)
        mk.assert_called_once()

    def test_small_run_cpu_path_is_full_precision_class(self):
        # AC-4: the small-run CPU path on a GPU machine stays in the "full" precision class (cos 1.0
        # with the FP16 index), so it composes with 1p936 as a no-op — no precision-class change,
        # no spurious re-embed. A GPU machine always predicts "full" for the model.
        self.assertEqual(
            self.bi._predicted_precision_class("BAAI/bge-small-en-v1.5", ["CoreMLExecutionProvider"]),
            "full",
        )

    def test_threshold_default_is_static_batch(self):
        # The default threshold is one full GPU batch (accel_embedder.STATIC_BATCH), so a bulk/full
        # build (>= one batch) uses GPU and only genuinely small incremental runs go to CPU.
        self.assertEqual(self.bi.INCREMENTAL_GPU_MIN_CHUNKS, self.bi.accel_embedder.STATIC_BATCH)

    def test_full_rebuild_never_passes_small_n_chunks(self):
        """Regression (found by a real full rebuild): the streaming full-rebuild path produces
        chunks AFTER the embedder is loaded, so ``new_doc_chunks`` is still empty at load time.
        A full build must pass ``n_chunks=None`` (bulk → GPU), NOT ``len()==0`` — else a full
        rebuild of the entire corpus would be misrouted to the CPU fastembed path."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "guide.md").write_text("## Intro\n\nHello docs.\n", encoding="utf-8")
        (root / "src").mkdir(parents=True)
        (root / "src" / "foo.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        seen = []

        def spy(model, n_chunks=None):
            seen.append((model, n_chunks))
            return _make_embedder_mock(dim=4)

        with patch.object(self.bi, "_get_embedder", side_effect=spy):
            self.bi.build_index(root, full=True, content="all", verbose=False)
        self.assertTrue(seen, "a full build must load at least one embedder")
        for model, n in seen:
            self.assertIsNone(n, f"full rebuild must pass n_chunks=None, got {n!r} for {model}")


class ContentScopeFreshnessTests(unittest.TestCase):
    """Wave 1sc7c (1sek8): per-layer change detection, corpus unification,
    hook coverage, and the heal path for the content-scope staleness cluster."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.index_dir = self.root / ".wavefoundry" / "index"

    def _build(self, content: str = "all", full: bool = False, **kw) -> dict:
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)

        def _emb(model, n_chunks=None):
            return docs_mock if model == self.bi.DOCS_MODEL else code_mock
        with patch.object(self.bi, "_get_embedder", side_effect=_emb):
            with contextlib.redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                return self.bi.build_index(self.root, full=full, content=content, verbose=False, **kw)

    def _code_paths(self) -> set:
        return {r["path"] for r in _read_index_chunks(self.index_dir, "code")}

    def _code_texts(self) -> str:
        return "\n".join(r.get("text") or "" for r in _read_index_chunks(self.index_dir, "code"))

    def test_poison_scenario_docs_build_cannot_freeze_code_layer(self):
        # AC-1: the exact field sequence — code + docs edits interleaved, the
        # docs build runs first (the hook's historic behavior), then a code
        # build. Pre-1sek8 the docs build stamped the code file's fresh hash
        # and the code build said "up to date" forever.
        _make_repo(self.root, {
            "src/app.py": "def alpha():\n    return 1\n",
            "docs/guide.md": "## Guide\n\nOriginal.\n",
        })
        self._build(full=True)
        (self.root / "src" / "app.py").write_text(
            "def alpha():\n    return 'freshness_sentinel_token'\n", encoding="utf-8")
        (self.root / "docs" / "guide.md").write_text("## Guide\n\nEdited.\n", encoding="utf-8")
        self._build(content="docs")
        self.assertNotIn("freshness_sentinel_token", self._code_texts())  # docs build didn't touch code
        result = self._build(content="code")
        self.assertFalse(result.get("up_to_date", False))
        self.assertIn("freshness_sentinel_token", self._code_texts())

    def test_dual_output_file_coherent_under_content_all(self):
        # A .py edit updates BOTH its code chunks and its docstring doc chunks
        # in one automatic-path (content=all) build.
        _make_repo(self.root, {
            "src/mod.py": '"""Module doc original."""\n\ndef f():\n    return 1\n',
        })
        self._build(full=True)
        (self.root / "src" / "mod.py").write_text(
            '"""Module doc updated_sentinel."""\n\ndef f():\n    return "code_updated_sentinel"\n',
            encoding="utf-8")
        self._build(content="all")
        docs_text = "\n".join(r.get("text") or "" for r in _read_index_chunks(self.index_dir, "docs"))
        self.assertIn("updated_sentinel", docs_text)
        self.assertIn("code_updated_sentinel", self._code_texts())

    def test_scoped_build_leaves_other_layer_queued_not_erased(self):
        # A code-only build after a dual-output edit updates the code table
        # and leaves the DOCS layer stale-but-queued: the next docs build
        # picks the docstring change up.
        _make_repo(self.root, {
            "src/mod.py": '"""Doc one."""\n\ndef f():\n    return 1\n',
            "docs/guide.md": "## G\n\nBody.\n",
        })
        self._build(full=True)
        (self.root / "src" / "mod.py").write_text(
            '"""Doc two_sentinel."""\n\ndef f():\n    return "two_code_sentinel"\n', encoding="utf-8")
        self._build(content="code")
        self.assertIn("two_code_sentinel", self._code_texts())
        docs_text = "\n".join(r.get("text") or "" for r in _read_index_chunks(self.index_dir, "docs"))
        self.assertNotIn("two_sentinel", docs_text)  # docs layer not built yet
        self._build(content="docs")
        docs_text = "\n".join(r.get("text") or "" for r in _read_index_chunks(self.index_dir, "docs"))
        self.assertIn("two_sentinel", docs_text)  # ...and not erased, queued

    def test_corpus_membership_identical_across_content_scopes(self):
        # AC-3: content=all and content=code agree — tests/generated excluded
        # under both (unless --include-tests), extensionless code names kept.
        files = {
            "src/foo.py": "def f(): pass\n",
            "tests/test_foo.py": "def test_f(): pass\n",
            "Jenkinsfile": "stage one\n" * 30,
        }
        _make_repo(self.root, files)
        self._build(content="all", full=True)
        all_paths = self._code_paths()
        import shutil
        shutil.rmtree(self.index_dir)
        self._build(content="code", full=True)
        code_paths = self._code_paths()
        self.assertEqual(all_paths, code_paths)
        self.assertIn("src/foo.py", all_paths)
        self.assertIn("Jenkinsfile", all_paths)
        self.assertNotIn("tests/test_foo.py", all_paths)
        shutil.rmtree(self.index_dir)
        self._build(content="all", full=True, include_tests=True)
        self.assertIn("tests/test_foo.py", self._code_paths())

    def test_empty_layer_state_heals_poisoned_repo(self):
        # The migration IS the heal: a pre-1sek8 repo arrives with hash-current
        # meta, stale Lance content, and NO layer state (the v5 bump reset the
        # store) — the first build re-chunks everything eligible and converges.
        _make_repo(self.root, {"src/app.py": "def f():\n    return 'old_content'\n"})
        self._build(full=True)
        # Simulate the poisoned arrival: newer file content, meta stamped
        # current (as a pre-fix docs build would have done), layer state absent.
        (self.root / "src" / "app.py").write_text(
            "def f():\n    return 'healed_content_sentinel'\n", encoding="utf-8")
        meta = _read_meta_store(self.index_dir)
        import hashlib as _h
        fresh = (self.root / "src" / "app.py").read_bytes()
        entry = meta["file_meta"]["src/app.py"]
        entry["hash"] = _h.sha256(fresh).hexdigest()
        st = (self.root / "src" / "app.py").stat()
        entry["mtime"] = st.st_mtime; entry["size"] = st.st_size
        entry["inode"] = getattr(st, "st_ino", 0)
        _seed_meta_store(self.index_dir, meta)
        # Wipe layer state (what a schema-bump reset / pre-1sek8 store looks like).
        import sqlite3 as _sq
        con = _sq.connect(self.index_dir / "index-state.sqlite")
        with con:
            con.execute("DELETE FROM layer_path_state")
        con.close()
        self.assertNotIn("healed_content_sentinel", self._code_texts())
        result = self._build(content="code")
        self.assertFalse(result.get("up_to_date", False))
        self.assertIn("healed_content_sentinel", self._code_texts())

    def test_healthy_zero_change_build_keeps_fast_exit(self):
        # No perpetual churn: with layer state populated, a zero-change build
        # (ineligible test files present) takes the up-to-date fast path.
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "tests/test_foo.py": "def test_f(): pass\n",
        })
        self._build(full=True)
        self._build(content="all")  # first incremental populates nothing new
        result = self._build(content="all")
        self.assertTrue(result.get("up_to_date", False))

    def test_corpus_narrowing_reap_cleans_layer_state_and_logs(self):
        # Migration reap: a code table carrying test-file rows (the old
        # content=all corpus) gets them reaped on the next default build,
        # loudly (store log) — and the layer state follows, so re-widening
        # via --include-tests re-indexes them.
        _make_repo(self.root, {
            "src/foo.py": "def f(): pass\n",
            "tests/test_foo.py": "def test_marker_token(): pass\n",
        })
        self._build(content="all", full=True, include_tests=True)
        self.assertIn("tests/test_foo.py", self._code_paths())
        result = self._build(content="all")  # default: tests excluded now
        self.assertNotIn("tests/test_foo.py", self._code_paths())
        log_path = self.index_dir.parent / "logs" / "index-state.log"
        self.assertTrue(log_path.is_file())
        self.assertIn("reaper code", log_path.read_text(encoding="utf-8"))
        # Layer state cleaned: re-widening re-indexes the unchanged test file.
        self._build(content="all", include_tests=True)
        self.assertIn("tests/test_foo.py", self._code_paths())

    def test_hook_spawns_all_content_reindex(self):
        # AC-2 pin: the rendered hook template and this repo's live hooks
        # spawn the indexer with --content all.
        render_src = (SCRIPTS_ROOT / "render_platform_surfaces.py").read_text(encoding="utf-8")
        self.assertIn('str(indexer), "--root", str(REPO_ROOT), "--content", "all"', render_src)
        self.assertIn('str(indexer_path), "--root", str(root), "--content", "all"', render_src)
        repo_root = SCRIPTS_ROOT.parents[2]
        hook = repo_root / ".claude" / "hooks" / "post-edit.py"
        if hook.is_file():
            self.assertIn('"--content", "all"', hook.read_text(encoding="utf-8"))

    def test_extensionless_code_names_stay_synced_with_chunker(self):
        import importlib.util as ilu
        spec = ilu.spec_from_file_location("chunker", SCRIPTS_ROOT / "chunker.py")
        ch = ilu.module_from_spec(spec)
        spec.loader.exec_module(ch)
        self.assertEqual(
            self.bi.CODE_EXTENSIONLESS_SOURCE_NAMES,
            set(ch.CODE_EXTENSIONLESS_NAMES) | set(ch.MAKEFILE_NAMES),
        )


class LanceIndexCleanupTests(unittest.TestCase):
    """Wave 1p95j: the index build must compact + clean after building indices so stale FTS/vector
    artifacts don't accumulate unbounded (the observed 400M+ / 11-`_indices`-dir bloat)."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_streaming_finalize_optimizes_and_builds_no_lance_fts(self):
        # Wave 1rsh9 (1sauc): the Lance/Tantivy FTS is retired — finalize
        # compacts the table but creates NO Lance FTS index (the lexical layer
        # is the index-state store's FTS5 tables).
        w = self.bi._StreamingLayerWriter.__new__(self.bi._StreamingLayerWriter)
        w.table = MagicMock()
        w.table_name = "docs"
        w.written = self.bi.LANCEDB_INDEX_THRESHOLD + 1
        with patch.object(self.bi, "_optimize_lance_table") as opt:
            w._finalize_inner(verbose=False)
        opt.assert_called_once_with(w.table)
        w.table.create_fts_index.assert_not_called()

    def test_streaming_finalize_none_table_is_noop(self):
        w = self.bi._StreamingLayerWriter.__new__(self.bi._StreamingLayerWriter)
        w.table = None
        with patch.object(self.bi, "_optimize_lance_table") as opt:
            self.assertEqual(w._finalize_inner(verbose=False), 0)
        opt.assert_not_called()

    def test_optimize_lance_table_swallows_exceptions(self):
        # AC-5: a compaction/cleanup failure must never propagate (best-effort/advisory).
        t = MagicMock()
        t.optimize.side_effect = RuntimeError("boom")
        self.bi._optimize_lance_table(t)  # must not raise

    def test_full_rebuild_runs_cleanup(self):
        # AC-1 (integration): a real full rebuild calls the compaction/cleanup at finalize.
        _make_repo(self.root, {"docs/g.md": "## A\n\nhello docs.\n", "src/f.py": "def f():\n    return 1\n"})
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_optimize_lance_table") as opt, \
             patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            self.bi.build_index(self.root, full=True, content="all", verbose=False)
        self.assertTrue(opt.called, "a full rebuild must run the compaction/cleanup at finalize")

    def test_no_lance_fts_created_anywhere(self):
        # Wave 1rsh9 (1sauc): source-assertion removal lock — no build path
        # creates or refreshes a Lance FTS index. The only permitted
        # `create_fts_index` mention is inside the legacy-cleanup helper's
        # detection logic or comments; the call itself must be gone.
        src = (Path(self.bi.__file__)).read_text(encoding="utf-8")
        self.assertNotIn("_create_fts_index", src)
        self.assertNotIn(".create_fts_index(", src)
        # The legacy drop helper exists and is wired into the reclaim path.
        self.assertIn("def _drop_legacy_fts_indices(", src)
        reclaim_pos = src.index("def reclaim_lance_table(")
        drop_pos = src.index(
            "_drop_legacy_fts_indices(table, table_name, index_dir=index_dir)",
            reclaim_pos,
        )
        self.assertGreater(drop_pos, reclaim_pos)

    def test_incremental_change_creates_no_lance_fts(self):
        # Wave 1rsh9 (1sauc): an incremental pass that changes a table must
        # NOT create/rebuild a Lance FTS index (the 1p95j rebuild is retired).
        _make_repo(self.root, {"docs/g.md": "## A\n\nhello docs.\n"})
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            self.bi.build_index(self.root, full=True, content="all", verbose=False)
        (self.root / "docs" / "g.md").write_text("## A\n\nchanged content now.\n", encoding="utf-8")
        with patch.object(self.bi, "_get_embedder", return_value=_make_embedder_mock(dim=4)):
            self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        import lancedb
        db = lancedb.connect(str(self.root / ".wavefoundry" / "index"))
        table = db.open_table("docs")
        fts_indices = [i for i in (table.list_indices() or [])
                       if "FTS" in str(getattr(i, "index_type", "")).upper()]
        self.assertEqual(fts_indices, [], "no Lance FTS index may exist after builds")


class LanceDbAutoInstallTlsTests(unittest.TestCase):
    """Wave 1p93v: ``_auto_install_lancedb()``'s pip subprocess call must apply the same pip
    TLS-conflict mitigation (``setup_index._pip_tls_env()``) used at every other pip/uv install call
    site in this codebase — it was the one unwired call site found in a post-1p939 sweep."""

    def setUp(self):
        self.bi = load_build_index()

    def test_applies_pip_tls_env_when_ca_var_set(self):
        # AC-1: a host-agent/operator CA var set → the pip subprocess receives the merged-bundle env.
        fake_bundle_env = {"SSL_CERT_FILE": "/fake/merged-bundle.pem", "REQUESTS_CA_BUNDLE": "/fake/merged-bundle.pem"}
        fake_result = MagicMock(returncode=0)
        with patch.object(self.bi.venv_bootstrap, "tool_venv_python", return_value=Path(sys.executable)), \
             patch.object(self.bi.subprocess_util, "isolated_run", return_value=fake_result) as run_mock, \
             patch("setup_index._pip_tls_env", return_value=fake_bundle_env):
            self.bi._auto_install_lancedb()
        run_mock.assert_called_once()
        _, kwargs = run_mock.call_args
        self.assertEqual(kwargs.get("env"), fake_bundle_env)

    def test_no_env_override_in_plain_env(self):
        # AC-2: no CA var set → env=None passed through (inherit unchanged), no regression.
        fake_result = MagicMock(returncode=0)
        with patch.object(self.bi.venv_bootstrap, "tool_venv_python", return_value=Path(sys.executable)), \
             patch.object(self.bi.subprocess_util, "isolated_run", return_value=fake_result) as run_mock, \
             patch("setup_index._pip_tls_env", return_value=None):
            self.bi._auto_install_lancedb()
        run_mock.assert_called_once()
        _, kwargs = run_mock.call_args
        self.assertIsNone(kwargs.get("env"), "plain env must pass env=None (inherit unchanged)")

    def test_raises_on_install_failure(self):
        fake_result = MagicMock(returncode=1)
        with patch.object(self.bi.venv_bootstrap, "tool_venv_python", return_value=Path(sys.executable)), \
             patch.object(self.bi.subprocess_util, "isolated_run", return_value=fake_result), \
             patch("setup_index._pip_tls_env", return_value=None):
            with self.assertRaises(ImportError):
                self.bi._auto_install_lancedb()


if __name__ == "__main__":
    unittest.main()


class IndexBuildLockHeldTests(unittest.TestCase):
    """Wave 1p99o: the build lock is a fcntl record lock (POSIX) on a sentinel byte, probed
    non-destructively via F_GETLK; `ended_at` is written best-effort on clean exit."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.index_dir = Path(self.tmp.name) / ".wavefoundry" / "index"
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_held_false_when_no_lock_file(self):
        self.assertEqual(self.bi._index_build_lock_held(self.index_dir), (False, None))

    @unittest.skipIf(os.name == "nt", "cross-process F_GETLK held test is POSIX")
    def test_held_detects_concurrent_holder_and_clears_after(self):
        holder = textwrap.dedent(
            f"""
            import importlib.util, sys, time, pathlib
            spec = importlib.util.spec_from_file_location("hb", {str(INDEXER_PATH)!r})
            m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
            with m._index_build_lock(pathlib.Path(sys.argv[1])):
                print("LOCKED", flush=True); time.sleep(3)
            """
        )
        proc = subprocess.Popen([sys.executable, "-B", "-c", holder, str(self.index_dir)],
                                stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(proc.stdout.readline().strip(), "LOCKED")
            time.sleep(0.2)
            held, pid = self.bi._index_build_lock_held(self.index_dir)
            self.assertTrue(held)                      # F_GETLK sees the conflicting lock
            self.assertEqual(pid, proc.pid)            # kernel returns the holder PID
            # metadata is readable while held (lock is on the sentinel byte, not byte 0)
            meta = self.bi.read_index_build_lock_metadata(self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME)
            self.assertEqual(meta.get("pid"), proc.pid)
            self.assertNotIn("ended_at", meta)         # not yet ended
        finally:
            proc.wait()
        time.sleep(0.2)
        self.assertEqual(self.bi._index_build_lock_held(self.index_dir), (False, None))

    def test_ended_at_written_on_clean_exit(self):
        with self.bi._index_build_lock(self.index_dir):
            pass
        meta = self.bi.read_index_build_lock_metadata(self.index_dir / self.bi.INDEX_BUILD_LOCK_NAME)
        self.assertIsInstance(meta.get("ended_at"), (int, float))
        # not held after a clean exit
        self.assertEqual(self.bi._index_build_lock_held(self.index_dir), (False, None))


class _ReclaimFakeArrow:
    def __init__(self, n):
        self.num_rows = n


class _ReclaimFakeTable:
    """A LanceDB-table stand-in for exercising the reclaim tiers without a real Lance corruption."""

    def __init__(self, rows, optimize_ok=True, arrow_ok=True):
        self.rows = rows
        self.optimize_ok = optimize_ok
        self.arrow_ok = arrow_ok
        self.created_indices = []
        self.existing_indices = []
        self.dropped_indices = []

    def optimize(self, cleanup_older_than=None):
        if not self.optimize_ok:
            # The real Lance list-offset corruption signature (lance #7538).
            raise RuntimeError("Max offset 99 exceeds length of values 10")

    def count_rows(self):
        return self.rows

    def to_arrow(self):
        if not self.arrow_ok:
            raise RuntimeError("corrupt read — data unreadable")
        return _ReclaimFakeArrow(self.rows)

    def create_index(self, **kw):
        self.created_indices.append(("vector", kw))

    def create_fts_index(self, *a, **kw):
        self.created_indices.append(("fts", kw))

    def list_indices(self):
        return list(self.existing_indices)

    def drop_index(self, name):
        self.dropped_indices.append(name)


class _ReclaimFakeDB:
    def __init__(self, table):
        self._table = table
        self.rename_called = False
        self.created = []

    def open_table(self, name):
        if self._table is None:
            raise ValueError(f"Table '{name}' was not found")
        return self._table

    def create_table(self, name, data=None, mode=None):
        self.created.append((name, mode))
        self._table = _ReclaimFakeTable(rows=data.num_rows)
        return self._table

    def rename_table(self, *a, **k):
        self.rename_called = True
        raise NotImplementedError("LanceDBError: not supported: rename_table is not supported in LanceDB OSS")


class IndexReclaimTests(unittest.TestCase):
    """Wave 1p9aj: tiered LanceDB reclaim (optimize -> compact-by-rewrite -> full rebuild)."""

    def setUp(self):
        self.bi = load_build_index()

    def test_optimize_lance_table_returns_bool(self):
        ok = MagicMock()
        self.assertTrue(self.bi._optimize_lance_table(ok))
        bad = MagicMock()
        bad.optimize.side_effect = RuntimeError("Max offset exceeds length of values")
        self.assertFalse(self.bi._optimize_lance_table(bad))  # must not raise, returns False

    def test_tier1_optimize_success(self):
        db = _ReclaimFakeDB(_ReclaimFakeTable(rows=2000, optimize_ok=True))
        res = self.bi.reclaim_lance_table(db, "docs")
        self.assertEqual(res["tier"], 1)
        self.assertEqual(res["rows"], 2000)
        self.assertFalse(res["needs_rebuild"])
        self.assertEqual(db.created, [])  # no rewrite on the happy path

    def test_tier2_compact_by_rewrite_preserves_rows_and_indices_no_rename(self):
        # AC-2: optimize fails -> rewrite via create_table(overwrite); rows preserved; both indices
        # rebuilt; rename_table NEVER called; no re-embed.
        t = _ReclaimFakeTable(rows=2000, optimize_ok=False, arrow_ok=True)
        db = _ReclaimFakeDB(t)
        res = self.bi.reclaim_lance_table(db, "docs")
        self.assertEqual(res["tier"], 2)
        self.assertFalse(res["needs_rebuild"])
        self.assertEqual(res["rows"], 2000)
        self.assertIn(("docs", "overwrite"), db.created)
        self.assertFalse(db.rename_called, "reclaim must never call rename_table (unsupported in OSS)")
        kinds = [k for k, _ in db._table.created_indices]
        self.assertIn("vector", kinds)  # rows >= threshold
        self.assertNotIn("fts", kinds)  # wave 1rsh9 (1sauc): Lance FTS retired

    def test_tier2_below_threshold_skips_vector_index_and_builds_no_fts(self):
        t = _ReclaimFakeTable(rows=5, optimize_ok=False, arrow_ok=True)
        db = _ReclaimFakeDB(t)
        res = self.bi.reclaim_lance_table(db, "docs")
        self.assertEqual(res["tier"], 2)
        self.assertFalse(res["needs_rebuild"])
        kinds = [k for k, _ in db._table.created_indices]
        self.assertNotIn("vector", kinds)  # below LANCEDB_INDEX_THRESHOLD -> flat scan
        self.assertNotIn("fts", kinds)  # wave 1rsh9 (1sauc): Lance FTS retired

    def test_reclaim_drops_legacy_fts_indices(self):
        # Wave 1rsh9 (1sauc): a field repo carrying the retired Lance FTS index
        # sheds it on the reclaim path (drop_index fires, versions become
        # GC-able by the optimize cleanup); a repo without one is a no-op.
        class _Idx:
            def __init__(self, name, index_type):
                self.name = name
                self.index_type = index_type
        t = _ReclaimFakeTable(rows=100, optimize_ok=True, arrow_ok=True)
        t.existing_indices = [_Idx("text_idx", "FTS"), _Idx("vector_idx", "IvfHnswSq")]
        db = _ReclaimFakeDB(t)
        res = self.bi.reclaim_lance_table(db, "docs")
        self.assertEqual(res["tier"], 1)
        self.assertEqual(t.dropped_indices, ["text_idx"])
        # No legacy index -> nothing dropped.
        clean = _ReclaimFakeTable(rows=100, optimize_ok=True, arrow_ok=True)
        db2 = _ReclaimFakeDB(clean)
        self.bi.reclaim_lance_table(db2, "docs")
        self.assertEqual(clean.dropped_indices, [])

    def test_tier3_only_on_read_failure_not_optimize_failure(self):
        # AC-3: a full rebuild (needs_rebuild) fires ONLY when to_arrow() raises, never for a mere
        # optimize() failure (which is Tier 2).
        read_fail = _ReclaimFakeDB(_ReclaimFakeTable(rows=100, optimize_ok=False, arrow_ok=False))
        res = self.bi.reclaim_lance_table(read_fail, "docs")
        self.assertEqual(res["tier"], 3)
        self.assertTrue(res["needs_rebuild"])
        # optimize-only failure must NOT set needs_rebuild
        opt_fail = _ReclaimFakeDB(_ReclaimFakeTable(rows=100, optimize_ok=False, arrow_ok=True))
        res2 = self.bi.reclaim_lance_table(opt_fail, "docs")
        self.assertEqual(res2["tier"], 2)
        self.assertFalse(res2["needs_rebuild"])

    def test_tier3_on_open_failure(self):
        db = _ReclaimFakeDB(None)  # open_table raises
        res = self.bi.reclaim_lance_table(db, "docs")
        self.assertEqual(res["tier"], 3)
        self.assertTrue(res["needs_rebuild"])

    def test_optimize_index_tables_skips_absent_and_reports_sizes(self):
        with tempfile.TemporaryDirectory() as td:
            index_dir = Path(td)
            (index_dir / "docs.lance").mkdir()  # docs present; code.lance absent
            (index_dir / "docs.lance" / "data.bin").write_bytes(b"x" * 1024)
            # 1sed6 review fix: optimize is restore-only — it requires a
            # completed build epoch before it may run.
            iss = _store_mod()
            iss.write_build_bookkeeping(index_dir, {"built_at": "x"})
            iss.finalize_build_epoch(index_dir, iss.begin_build_epoch(index_dir, "seed"))
            db = _ReclaimFakeDB(_ReclaimFakeTable(rows=2000, optimize_ok=True))
            with patch.object(self.bi, "_get_lance_db", return_value=db):
                results = self.bi.optimize_index_tables(index_dir, ("docs", "code"))
            self.assertIn("docs", results)
            self.assertNotIn("code", results)  # absent table skipped
            self.assertEqual(results["docs"]["tier"], 1)
            self.assertIn("bytes_before", results["docs"])
            self.assertIn("bytes_after", results["docs"])
            self.assertGreater(results["docs"]["bytes_before"], 0)

    def test_finalize_self_heals_on_optimize_failure(self):
        # AC-5: when _optimize_lance_table returns False, finalize escalates to _compact_by_rewrite,
        # re-points the table, and returns early (no redundant FTS rebuild on the old handle).
        w = self.bi._StreamingLayerWriter.__new__(self.bi._StreamingLayerWriter)
        w.table = MagicMock()
        w.db = MagicMock()
        w.table_name = "docs"
        w.written = self.bi.LANCEDB_INDEX_THRESHOLD + 1
        new_table = MagicMock()
        with patch.object(self.bi, "_optimize_lance_table", return_value=False), \
             patch.object(self.bi, "_compact_by_rewrite", return_value=new_table) as rewrite:
            result = w._finalize_inner(verbose=False)
        rewrite.assert_called_once_with(w.db, "docs")
        self.assertIs(w.table, new_table)
        new_table.create_fts_index.assert_not_called()  # wave 1rsh9 (1sauc): Lance FTS retired
        self.assertEqual(result, w.written)

    def test_finalize_reclaim_failure_falls_through_and_does_not_raise(self):
        # A rewrite failure in finalize must not raise; it falls through to a best-effort normal
        # index build on the un-reclaimed table.
        w = self.bi._StreamingLayerWriter.__new__(self.bi._StreamingLayerWriter)
        w.table = MagicMock()
        w.db = MagicMock()
        w.table_name = "docs"
        w.written = self.bi.LANCEDB_INDEX_THRESHOLD + 1
        with patch.object(self.bi, "_optimize_lance_table", return_value=False), \
             patch.object(self.bi, "_compact_by_rewrite", side_effect=RuntimeError("rewrite boom")):
            result = w._finalize_inner(verbose=False)  # must not raise
        w.table.create_fts_index.assert_not_called()  # wave 1rsh9 (1sauc): Lance FTS retired
        self.assertEqual(result, w.written)

    def test_optimize_index_tables_fails_fast_under_lock_contention(self):
        # No-DEADLOCK invariant: optimize_index_tables acquires the SAME non-blocking build lock
        # (`fcntl.LOCK_EX | LOCK_NB` / `msvcrt.LK_NBLCK`) as the main build, so a lock held by another
        # process makes it raise IndexBuildAlreadyRunning *promptly* — it can never block/wait, so it
        # can never deadlock. The setup/upgrade auto-run wraps this in try/except, so its worst case is a
        # skipped optimize, never a hang.
        with tempfile.TemporaryDirectory() as td:
            index_dir = Path(td)
            (index_dir / "docs.lance").mkdir()
            (index_dir / "docs.lance" / "data.bin").write_bytes(b"x" * 32)
            holder = textwrap.dedent(
                f"""
                import importlib.util, pathlib, sys, time
                spec = importlib.util.spec_from_file_location("indexer_holder", {str(INDEXER_PATH)!r})
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                with mod._index_build_lock(pathlib.Path(sys.argv[1])):
                    print("locked", flush=True)
                    time.sleep(3.0)
                """
            )
            proc = subprocess.Popen(
                [sys.executable, "-B", "-c", holder, str(index_dir)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            try:
                self.assertEqual(proc.stdout.readline().strip(), "locked")
                start = time.monotonic()
                with self.assertRaises(self.bi.IndexBuildAlreadyRunning):
                    self.bi.optimize_index_tables(index_dir, ("docs",))
                elapsed = time.monotonic() - start
                # Well under the holder's 3s sleep -> it failed fast, it did NOT wait on the lock.
                self.assertLess(elapsed, 2.0, "optimize_index_tables blocked on the lock (would deadlock)")
            finally:
                proc.terminate()
                proc.communicate(timeout=5)


class ReindexPendingMarkerTests(unittest.TestCase):
    """Wave 1p9am: the reindex-pending marker (turn-end coalescing sentinel)."""

    def setUp(self):
        self.bi = load_build_index()

    def test_debounce_window_raised(self):
        # Non-Stop hosts fall back to a long leading-edge debounce.
        self.assertGreaterEqual(self.bi.HOOK_REINDEX_DEBOUNCE_SECONDS, 45.0)

    def test_mark_then_consume_then_gone(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            self.assertFalse(self.bi.consume_reindex_pending(d))  # nothing pending yet
            self.assertIsNone(self.bi.reindex_pending_age(d))
            self.bi.mark_reindex_pending(d)
            self.assertIsNotNone(self.bi.reindex_pending_age(d))
            self.assertTrue(self.bi.consume_reindex_pending(d))   # consumed
            self.assertFalse(self.bi.consume_reindex_pending(d))  # already cleared
            self.assertIsNone(self.bi.reindex_pending_age(d))

    def test_consume_is_atomic_single_winner(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            self.bi.mark_reindex_pending(d)
            first = self.bi.consume_reindex_pending(d)
            second = self.bi.consume_reindex_pending(d)
            self.assertTrue(first)
            self.assertFalse(second)  # only one unlink wins

    def test_mark_creates_index_dir(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "nested" / "index"  # does not exist yet
            self.bi.mark_reindex_pending(d)
            self.assertTrue((d / self.bi.HOOK_REINDEX_PENDING_NAME).exists())

    def test_reindex_pending_age_is_recent(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            self.bi.mark_reindex_pending(d)
            age = self.bi.reindex_pending_age(d)
            self.assertIsNotNone(age)
            self.assertLess(age, 5.0)


class DocsLintHookTimeoutTests(unittest.TestCase):
    """Wave 1p9bg: the docs-lint hook timeout is generous, configurable, and fail-safe."""

    def setUp(self):
        self.bi = load_build_index()

    def _root_with_config(self, td, cfg_json):
        root = Path(td)
        (root / "docs").mkdir()
        if cfg_json is not None:
            (root / "docs" / "workflow-config.json").write_text(cfg_json, encoding="utf-8")
        return root

    def test_default_when_no_config(self):
        with tempfile.TemporaryDirectory() as td:
            root = self._root_with_config(td, None)
            self.assertEqual(
                self.bi.docs_lint_hook_timeout_seconds(root), self.bi.DOCS_LINT_HOOK_TIMEOUT_DEFAULT
            )
        self.assertGreaterEqual(self.bi.DOCS_LINT_HOOK_TIMEOUT_DEFAULT, 60.0)

    def test_override_from_config(self):
        with tempfile.TemporaryDirectory() as td:
            root = self._root_with_config(td, '{"docs_lint":{"hook_timeout_seconds":300}}')
            self.assertEqual(self.bi.docs_lint_hook_timeout_seconds(root), 300.0)

    def test_bad_values_fall_back_to_default(self):
        default = self.bi.DOCS_LINT_HOOK_TIMEOUT_DEFAULT
        for bad in ('{"docs_lint":{"hook_timeout_seconds":"lots"}}',
                    '{"docs_lint":{"hook_timeout_seconds":0}}',
                    '{"docs_lint":{"hook_timeout_seconds":-5}}',
                    '{not valid json'):
            with tempfile.TemporaryDirectory() as td:
                root = self._root_with_config(td, bad)
                self.assertEqual(self.bi.docs_lint_hook_timeout_seconds(root), default)

    def test_missing_dir_never_raises(self):
        self.assertEqual(
            self.bi.docs_lint_hook_timeout_seconds(Path("/no/such/root/xyz")),
            self.bi.DOCS_LINT_HOOK_TIMEOUT_DEFAULT,
        )


class _EpochBuildCase(unittest.TestCase):
    """Shared harness for the 1sed6 epoch/convergence fixtures."""

    def setUp(self):
        self.bi = load_build_index()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.iss = _store_mod()

    def tearDown(self):
        self.tmp.cleanup()

    def _run_build(self, full: bool = False, content: str = "all") -> dict:
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            return self.bi.build_index(self.root, full=full, content=content, verbose=False)

    def _generation(self) -> int:
        state = self.iss.read_build_state(self.index_dir)
        return state["generation"] if state else -1


class ProjectLayerFreshnessTests(_EpochBuildCase):
    """1seav / 1sbxq AC-2: the cheap per-layer freshness signal — layer-
    crossing regressions in BOTH directions, added/deleted paths, empty
    layers, chunker mismatch, and the honesty rule (unknown, never silently
    current)."""

    def _freshness(self):
        return self.bi.project_layer_freshness(self.root)

    def _seed(self):
        _make_repo(self.root, {
            "src/foo.py": "def f(): return 1\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        self._run_build(full=True)

    def test_current_after_full_build(self):
        self._seed()
        v = self._freshness()
        self.assertIs(v["stale"], False)
        self.assertEqual(v["reason"], "current")

    def test_simple_edit_reads_stale(self):
        self._seed()
        (self.root / "src" / "foo.py").write_text("def f(): return 2\n", encoding="utf-8")
        self.assertIs(self._freshness()["stale"], True)

    def test_layer_crossing_code_edit_survives_docs_only_build(self):
        """The 1sek8 poison direction: edit a code file, run a docs-only
        build that also processes a docs change (the broad snapshot stamps
        the code file's fresh hash) — freshness must STILL read stale until
        a code/all build embeds it."""
        self._seed()
        (self.root / "src" / "foo.py").write_text("def f(): return 2\n", encoding="utf-8")
        (self.root / "docs" / "guide.md").write_text("## Intro\n\nChanged.\n", encoding="utf-8")
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock]):
            self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        v = self._freshness()
        self.assertIs(v["stale"], True, "broad snapshot stamped the code hash; the code layer is behind")
        self.assertIs(v["layers"]["code"], True)
        # A second docs-only build cannot clear it...
        docs_mock2 = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock2]):
            self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        self.assertIs(self._freshness()["stale"], True)
        # ...a code/all build does.
        with patch.object(self.bi, "_get_embedder",
                          side_effect=[_make_embedder_mock(dim=4), _make_embedder_mock(dim=4)]):
            self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertIs(self._freshness()["stale"], False)

    def test_layer_crossing_inverse_docs_edit_survives_code_only_build(self):
        """The inverse direction (code_ask searches BOTH layers): edit a
        docs file, run a code-only build that also processes a code change —
        stale until a docs/all build."""
        self._seed()
        (self.root / "docs" / "guide.md").write_text("## Intro\n\nChanged.\n", encoding="utf-8")
        (self.root / "src" / "foo.py").write_text("def f(): return 3\n", encoding="utf-8")
        with patch.object(self.bi, "_get_embedder", side_effect=[_make_embedder_mock(dim=4)]):
            self.bi.build_index(self.root, full=False, content="code", verbose=False)
        v = self._freshness()
        self.assertIs(v["stale"], True)
        self.assertIs(v["layers"]["docs"], True)
        with patch.object(self.bi, "_get_embedder",
                          side_effect=[_make_embedder_mock(dim=4), _make_embedder_mock(dim=4)]):
            self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertIs(self._freshness()["stale"], False)

    def test_added_and_deleted_paths_read_stale(self):
        self._seed()
        (self.root / "src" / "bar.py").write_text("def g(): pass\n", encoding="utf-8")
        self.assertIs(self._freshness()["stale"], True, "added path")
        with patch.object(self.bi, "_get_embedder",
                          side_effect=[_make_embedder_mock(dim=4), _make_embedder_mock(dim=4)]):
            self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertIs(self._freshness()["stale"], False)
        (self.root / "src" / "bar.py").unlink()
        self.assertIs(self._freshness()["stale"], True, "deleted path")

    def test_legitimately_empty_layer_reads_current(self):
        """A repo with no docs corpus: the empty docs layer is current, not
        stale/unknown."""
        _make_repo(self.root, {"src/foo.py": "def f(): return 1\n"})
        self._run_build(full=True)
        v = self._freshness()
        self.assertIs(v["stale"], False)

    def test_chunker_mismatch_reads_stale(self):
        self._seed()
        store = self.bi._get_index_state_store()
        snapshot = store.read_build_summary(self.index_dir)
        stale_meta = dict(snapshot)
        stale_meta["chunker_versions"] = {"docs": "0", "code": "0"}
        stale_meta["file_meta"] = self.bi._load_meta(self.index_dir).get("file_meta", {})
        store.write_build_bookkeeping(self.index_dir, stale_meta)
        v = self._freshness()
        self.assertIs(v["stale"], True)
        self.assertIs(v["chunker_stale"], True)

    def test_no_store_reads_unknown_never_current(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        v = self._freshness()
        self.assertIsNone(v["stale"], "no snapshot = unknown, never current")

    def test_helper_exception_reads_unknown(self):
        self._seed()
        with patch.object(self.bi, "project_index_inputs_stale", side_effect=RuntimeError("boom")):
            v = self._freshness()
        self.assertIsNone(v["stale"])
        self.assertIn("error", v["reason"])


class LegacyConvergenceTests(_EpochBuildCase):
    """AC-6: a legacy installation (Lance + meta.json, no state store)
    converges by reconstruction — legacy JSON is never authoritative input
    and is removed only after a successful completed epoch."""

    def test_legacy_json_is_never_authority_and_removed_after_convergence(self):
        _make_repo(self.root, {
            "src/foo.py": "def f(): return 1\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        first = self._run_build(full=True)
        self.assertFalse(first.get("failed"))
        # Fabricate the legacy layout: the store's snapshot exported to
        # meta.json (so the JSON claims every file is current), store gone.
        snapshot = _read_meta_store(self.index_dir)
        self.assertTrue(snapshot.get("file_meta"))
        (self.index_dir / "meta.json").write_text(json.dumps(snapshot), encoding="utf-8")
        for suffix in ("", "-wal", "-shm"):
            p = self.index_dir / f"index-state.sqlite{suffix}"
            if p.exists():
                p.unlink()
        # An ordinary incremental build must treat the empty store — not the
        # JSON — as the state authority: everything re-indexes.
        result = self._run_build(full=False)
        self.assertFalse(result.get("failed"))
        self.assertGreater(result["files_indexed"], 0,
                           "legacy meta.json must not satisfy freshness")
        # Converged: completed epoch, repopulated state, legacy JSON removed.
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))
        self.assertTrue(_read_meta_store(self.index_dir).get("file_meta"))
        self.assertFalse((self.index_dir / "meta.json").exists())

    def test_legacy_json_survives_a_failed_convergence(self):
        """Removal happens ONLY after success: a build that fails before
        finalization leaves the legacy file (and no complete epoch) behind."""
        _make_repo(self.root, {"src/foo.py": "def f(): return 1\n"})
        self._run_build(full=True)
        (self.index_dir / "meta.json").write_text("{}", encoding="utf-8")
        store = self.bi._get_index_state_store()
        (self.root / "src" / "foo.py").write_text("def f(): return 2\n", encoding="utf-8")
        with patch.object(store, "write_build_bookkeeping", side_effect=RuntimeError("disk full")):
            result = self._run_build(full=False)
        self.assertTrue(result.get("failed"))
        self.assertTrue((self.index_dir / "meta.json").exists(),
                        "legacy JSON must not be removed before convergence")
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))


class EpochOrderingAndFaultTests(_EpochBuildCase):
    """AC-3/AC-7 core matrix: fence-first ordering, structured no-fallback
    failures at every mandatory boundary, generation semantics, and the
    standalone FTS-rebuild/optimize writers."""

    def test_true_noop_never_opens_the_epoch(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        gen = self._generation()
        tok = self.iss.build_epoch_token(self.index_dir)
        result = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertTrue(result["up_to_date"])
        self.assertEqual(self._generation(), gen,
                         "a proven true no-op must leave the generation unchanged")
        self.assertEqual(self.iss.build_epoch_token(self.index_dir), tok)

    def test_fence_failure_is_a_structured_build_failure(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        store = self.bi._get_index_state_store()
        with patch.object(store, "begin_build_epoch", side_effect=RuntimeError("fence write failed")):
            result = self._run_build(full=True)
        self.assertTrue(result.get("failed"))
        self.assertIn("could not open the build epoch", result["failure"])
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))

    def test_bookkeeping_failure_leaves_epoch_incomplete(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        store = self.bi._get_index_state_store()
        with patch.object(store, "write_build_bookkeeping", side_effect=RuntimeError("locked")):
            result = self._run_build(full=True)
        self.assertTrue(result.get("failed"))
        self.assertIn("canonical build-state write failed", result["failure"])
        state = self.iss.read_build_state(self.index_dir)
        self.assertEqual(state["status"], "building",
                         "a swallowed mandatory-resident failure must not publish")
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))

    def test_mandatory_reconcile_failure_blocks_publication(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        with patch.object(self.bi, "_sync_chunk_derived_state",
                          return_value={"code": {"error": "fts write failed"}}):
            result = self._run_build(full=True)
        self.assertTrue(result.get("failed"))
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))

    def test_finalize_cas_miss_is_a_failed_publication(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        store = self.bi._get_index_state_store()
        with patch.object(store, "finalize_build_epoch", return_value=False):
            result = self._run_build(full=True)
        self.assertTrue(result.get("failed"))
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))

    def test_recovery_after_failure_heals_idempotently(self):
        """Bounded retry contract: after an injected failure the NEXT ordinary
        build converges — no manual repair step, no false completion left over."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        store = self.bi._get_index_state_store()
        with patch.object(store, "write_build_bookkeeping", side_effect=RuntimeError("locked")):
            self._run_build(full=True)
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))
        result = self._run_build(full=False)
        self.assertFalse(result.get("failed"))
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))

    def test_standalone_fts_rebuild_holds_its_own_epoch(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        gen = self._generation()
        with contextlib.redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            stats = self.bi.rebuild_derived_chunk_state(self.index_dir, verbose=False)
        self.assertNotIn("error", stats)
        self.assertEqual(self._generation(), gen + 1)
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))

    def test_optimize_holds_its_own_epoch(self):
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        gen = self._generation()
        with contextlib.redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            results = self.bi.optimize_index_tables(self.index_dir)
        self.assertNotIn("error", results)
        self.assertNotIn("finalize", results)
        self.assertEqual(self._generation(), gen + 1)
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))


    def test_scoped_build_escalates_after_store_reset(self):
        """Review refutation: a scoped build over a reset store (Lance tables
        present, no provenance) must escalate to all-layer convergence — it
        may not publish `complete` around the unprovenanced table."""
        _make_repo(self.root, {
            "src/foo.py": "def f(): return 1\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        self._run_build(full=True)
        for suffix in ("", "-wal", "-shm"):
            p = self.index_dir / f"index-state.sqlite{suffix}"
            if p.exists():
                p.unlink()
        # Scoped docs request over the reset store.
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with redirect_stderr(io.StringIO()) as err, \
             patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        self.assertFalse(result.get("failed"))
        self.assertIn("escalating content='docs' to all-layer convergence", err.getvalue())
        snapshot = _read_meta_store(self.index_dir)
        self.assertTrue((snapshot.get("model_versions") or {}).get("docs"))
        self.assertTrue((snapshot.get("model_versions") or {}).get("code"),
                        "escalation must restore the code layer's provenance")
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))

    def test_schema_bumped_store_converges_before_decisions(self):
        """Review reproduction (reset-after-front-gate): a store on an OLD
        schema version still exposes its pre-reset provenance to read-only
        loads, so the lazily-triggered reset used to fire AFTER the front
        gate and staleness reads — a scoped build idled to a complete epoch
        over freshly-erased state. The build must settle store currency
        FIRST, so the reset store presents empty provenance (escalation) and
        empty layer state (all stale)."""
        _make_repo(self.root, {
            "src/foo.py": "def f(): return 1\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        self._run_build(full=True)
        # Force the review's exact pre-state: old schema version + no build_state.
        import sqlite3
        conn = sqlite3.connect(str(self.index_dir / "index-state.sqlite"))
        with conn:
            conn.execute("UPDATE meta SET value = '5' WHERE key = 'store_schema_version'")
            conn.execute("DROP TABLE build_state")
        conn.close()
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with redirect_stderr(io.StringIO()) as err, \
             patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        self.assertFalse(result.get("failed"))
        self.assertFalse(result.get("up_to_date"),
                         "a version-reset store must never idle to up_to_date")
        self.assertIn("escalating content='docs' to all-layer convergence", err.getvalue())
        state = self.iss.read_build_state(self.index_dir)
        self.assertEqual(state["status"], "complete")
        self.assertNotIn("idle-maintenance", state["scope"])
        snapshot = _read_meta_store(self.index_dir)
        self.assertTrue((snapshot.get("model_versions") or {}).get("docs"))
        self.assertTrue((snapshot.get("model_versions") or {}).get("code"),
                        "all-layer convergence must restore both provenances")

    def test_completion_rear_guard_is_wired_before_finalize(self):
        """Source pin for the rear guard: the unprovenanced-table verification
        sits between the bookkeeping write and the finalize CAS."""
        src = (SCRIPTS_ROOT / "indexer.py").read_text(encoding="utf-8")
        bookkeeping = src.index("write_build_bookkeeping(index_dir, new_meta)")
        guard = src.index("_unprovenanced_at_publish", bookkeeping)
        finalize = src.index("finalize_build_epoch(index_dir, _build_attempt)", guard)
        self.assertGreater(finalize, guard)

    def test_fts_rebuild_refuses_without_completed_epoch(self):
        """Review refutation (empty-FTS false completion): the derived rebuild
        may only RESTORE readiness — on an uninitialized or building store it
        refuses and never manufactures a complete epoch."""
        self.index_dir.mkdir(parents=True, exist_ok=True)
        stats = self.bi.rebuild_derived_chunk_state(self.index_dir, verbose=False)
        self.assertIn("no completed build epoch", stats.get("error", ""))
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))
        # Same over a mid-build (building) store.
        self.iss.begin_build_epoch(self.index_dir, "in-flight")
        stats2 = self.bi.rebuild_derived_chunk_state(self.index_dir, verbose=False)
        self.assertIn("no completed build epoch", stats2.get("error", ""))
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))

    def test_optimize_refuses_without_completed_epoch(self):
        with tempfile.TemporaryDirectory() as td:
            index_dir = Path(td)
            (index_dir / "docs.lance").mkdir()
            results = self.bi.optimize_index_tables(index_dir, ("docs",))
            self.assertIn("no completed build epoch", results.get("error", ""))
            self.assertIsNone(self.iss.build_epoch_token(index_dir))

    def test_optimize_error_does_not_finalize_readiness(self):
        """Review refutation: a Tier-3/error reclaim result leaves the epoch
        un-finalized — readers fail closed instead of trusting an in-place
        rewrite that ended in unknown state."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        gen = self._generation()

        class _BrokenTable:
            def count_rows(self):
                raise RuntimeError("unreadable")
            def to_arrow(self):
                raise RuntimeError("unreadable")

        class _BrokenDB:
            def open_table(self, name):
                raise RuntimeError("unreadable")

        with patch.object(self.bi, "_get_lance_db", return_value=_BrokenDB()):
            results = self.bi.optimize_index_tables(self.index_dir)
        self.assertIn("finalize", results)
        self.assertIn("NOT finalized", results["finalize"]["error"])
        # Fail-closed: no complete token, generation not advanced.
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))
        self.assertEqual(self._generation(), gen)
        # And an ordinary rebuild restores readiness afterwards.
        (self.root / "src" / "foo.py").write_text("def f(): return 2\n", encoding="utf-8")
        recover = self._run_build(full=False)
        self.assertFalse(recover.get("failed"))
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))

    def test_unchanged_retry_heals_a_dirty_epoch(self):
        """Review refutation (dirty-epoch unchanged-retry lockout): zero
        changes + a `building` epoch must run recovery and republish — never
        report up_to_date over a permanently failed-closed store."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        gen = self._generation()
        # Simulate a builder that died between fence and finalize.
        self.iss.begin_build_epoch(self.index_dir, "code:crashed")
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))
        with redirect_stderr(io.StringIO()) as err:
            result = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertTrue(result["up_to_date"])
        self.assertIn("zero-change recovery", err.getvalue())
        # Readiness restored: complete token, generation advanced past the crash.
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))
        self.assertGreater(self._generation(), gen)
        # A second unchanged run over the now-complete epoch is a TRUE no-op.
        gen2 = self._generation()
        result2 = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertTrue(result2["up_to_date"])
        self.assertEqual(self._generation(), gen2)

    def test_recovery_refuses_when_claimed_table_is_missing(self):
        """Independent-review F1: zero-change recovery must not republish a
        canonical state that claims a layer whose Lance table is gone — it
        resets that layer's state and fails visibly; the next ordinary build
        reconstructs the table and only then restores readiness."""
        _make_repo(self.root, {
            "src/foo.py": "def f(): return 1\n",
            "docs/guide.md": "## Intro\n\nHello.\n",
        })
        self._run_build(full=True)
        # Crash simulation + out-of-band table loss for a layer with
        # registry rows. Scoped content='code' is the reviewer's exact
        # reproduction: docs drift-candidacy is out of scope there, so only
        # the recovery guard stands between the loss and republication.
        self.iss.begin_build_epoch(self.index_dir, "code:crashed")
        import shutil
        shutil.rmtree(self.index_dir / "docs.lance")
        with redirect_stderr(io.StringIO()):
            result = self.bi.build_index(self.root, full=False, content="code", verbose=False)
        self.assertTrue(result.get("failed"))
        self.assertIn("Lance table is missing", result["failure"])
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir),
                          "recovery must not publish over a missing claimed table")
        # The reset layer state makes the next ordinary build reconstruct.
        docs_mock = _make_embedder_mock(dim=4)
        code_mock = _make_embedder_mock(dim=4)
        with redirect_stderr(io.StringIO()), \
             patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
            recover = self.bi.build_index(self.root, full=False, content="all", verbose=False)
        self.assertFalse(recover.get("failed"))
        self.assertTrue((self.index_dir / "docs.lance").is_dir())
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))

    def test_cli_exits_nonzero_on_structured_failure(self):
        """Review refutation: a {failed: true} build must exit 1 through the
        CLI so setup/MCP subprocess callers see the failure."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        with patch.object(self.bi, "build_index",
                          return_value={"failed": True, "failure": "injected"}), \
             redirect_stderr(io.StringIO()) as err:
            rc = self.bi.main(["--root", str(self.root), "--content", "all"])
        self.assertEqual(rc, 1)
        self.assertIn("injected", err.getvalue())
        with patch.object(self.bi, "build_index", return_value={"up_to_date": True}):
            self.assertEqual(self.bi.main(["--root", str(self.root), "--content", "all"]), 0)

    def test_fresh_process_kill_between_fence_and_finalize_fails_closed(self):
        """AC-7/AC-9 kill fixture: a builder killed after the durable fence
        leaves building/no-token for a FRESH process; the next ordinary build
        restores readiness."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        self._run_build(full=True)
        gen = self._generation()
        script = (
            "import sys, os\n"
            "from pathlib import Path\n"
            "import importlib.util\n"
            f"spec = importlib.util.spec_from_file_location('iss', {str(SCRIPTS_ROOT / 'index_state_store.py')!r})\n"
            "mod = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(mod)\n"
            f"mod.begin_build_epoch(Path({str(self.index_dir)!r}), 'kill:test')\n"
            "os._exit(9)\n"
        )
        proc = subprocess.run([sys.executable, "-c", script], capture_output=True)
        self.assertEqual(proc.returncode, 9)
        # Fresh reader view: interrupted build = building + fail-closed token.
        state = self.iss.read_build_state(self.index_dir)
        self.assertEqual(state["status"], "building")
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))
        # Ordinary recovery: the next mutating build supersedes the dead
        # attempt and publishes a fresh complete epoch.
        (self.root / "src" / "foo.py").write_text("def f(): return 9\n", encoding="utf-8")
        result = self._run_build(full=False)
        self.assertFalse(result.get("failed"))
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))
        self.assertGreater(self._generation(), gen)


if __name__ == "__main__":
    unittest.main()
