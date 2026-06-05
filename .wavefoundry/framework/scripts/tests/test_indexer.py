from __future__ import annotations

import importlib.util
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
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
        (self.root / ".wavefoundry" / "dashboard-server.json").parent.mkdir(parents=True, exist_ok=True)
        (self.root / ".wavefoundry" / "dashboard-server.json").write_text('{"pid": 1}\n', encoding="utf-8")
        (self.root / ".wavefoundry" / "logs").mkdir(parents=True, exist_ok=True)
        (self.root / ".wavefoundry" / "logs" / "dashboard.log").write_text("started\n", encoding="utf-8")
        (self.root / ".wavefoundry" / "guard-overrides.json").write_text('{"seed_edit_allowed": {"enabled": false}}\n', encoding="utf-8")
        files = self.bi.walk_repo(self.root)
        rel_strs = {str(f.relative_to(self.root)).replace("\\", "/") for f in files}
        self.assertNotIn(".wavefoundry/dashboard-server.json", rel_strs)
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
        """AC-7: .xml, .graphql, .gql, .proto, .sql and common SQL aliases are in SOURCE_CODE_EXTENSIONS."""
        for ext in (".xml", ".graphql", ".gql", ".proto", ".sql", ".psql", ".pgsql", ".ddl", ".dml", ".tsql", ".hql"):
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
        self.assertTrue(self.bi.should_coalesce_hook_reindex(self.index_dir))

        lock_path.write_text(
            json.dumps({"pid": 99999999, "started_at": 0.0}),
            encoding="utf-8",
        )
        self.bi.record_hook_reindex_spawn(self.index_dir)
        self.assertTrue(self.bi.should_coalesce_hook_reindex(self.index_dir))

        time.sleep(self.bi.HOOK_REINDEX_DEBOUNCE_SECONDS + 0.05)
        self.assertFalse(self.bi.should_coalesce_hook_reindex(self.index_dir))


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
        # Index may be stored as LanceDB tables or legacy JSON files.
        has_index = (
            (index_dir / "docs.lance").is_dir() or (index_dir / "docs.json").exists()
            or (index_dir / "code.lance").is_dir() or (index_dir / "code.json").exists()
        )
        self.assertTrue(has_index)
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
        source = "\n".join(f"line {i}" for i in range(1, 151)) + "\n"
        _make_repo(self.root, {"notes.custom": source})
        self._run_build(full=True)

        shifted = "inserted line\n" + source
        (self.root / "notes.custom").write_text(shifted, encoding="utf-8")

        doc_calls: list[list[str]] = []
        code_calls: list[list[str]] = []
        docs_mock = _make_embedder_mock(dim=4, calls=doc_calls)
        code_mock = _make_embedder_mock(dim=4, calls=code_calls)
        with patch.object(self.bi, "_get_embedder", side_effect=[docs_mock, code_mock]):
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
        shifted_rows = [row for row in rows if row["path"] == "notes.custom"]
        self.assertTrue(any(row["lines"][0] > 1 for row in shifted_rows))
        self.assertTrue(all(row.get("chunk_hash") for row in shifted_rows))

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
        chunks = _read_index_chunks(index_dir, "docs")
        self.assertIn("docs/guide.md", meta["file_meta"])
        # Project layer meta must NOT contain framework files (130nf). Framework files
        # belong to the framework layer's meta.json; keeping them in the project meta
        # caused wave_index_health to permanently report them as "removed" because the
        # health check (which applies _filter_project_index_excludes) sees a narrow set
        # while the meta persisted the broad set.
        self.assertNotIn(".wavefoundry/framework/README.md", meta["file_meta"])
        # Framework content must not appear in the semantic docs index either.
        self.assertFalse(any(c["path"].startswith(".wavefoundry/framework/") for c in chunks))

    def test_project_index_excludes_wavefoundry_blanket(self):
        """Wave 1p2q3 (1p2qd): all of .wavefoundry/ excluded from project index."""
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
        meta = json.loads((index_dir / "meta.json").read_text())
        for path in meta["file_meta"]:
            self.assertFalse(path.startswith(".wavefoundry/"),
                             f"unexpected .wavefoundry/ file in project meta: {path}")

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

        meta = json.loads((index_dir / "meta.json").read_text())
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
        meta = json.loads((index_dir / "meta.json").read_text())
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
        meta = json.loads((index_dir / "meta.json").read_text())
        code_chunks = _read_index_chunks(index_dir, "code")
        self.assertIn(".wavefoundry/framework/scripts/server.py", meta["file_meta"])
        self.assertTrue(any(c["path"] == ".wavefoundry/framework/scripts/server.py" for c in code_chunks))
        self.assertIn("vendor/docs/custom.py", meta["file_meta"])

    def test_project_meta_excludes_framework_and_is_stable_across_docs_and_code_runs(self):
        """Regression for 130nf: project meta must not contain framework files (under any
        run), and consecutive docs and code runs must write identical file_meta dicts
        (preserves the original 'no alternating cycle' invariant from indexer.py:1822).
        """
        _make_repo(self.root, {
            "docs/guide.md": "## Intro\n\nHello.\n",
            "src/app.py": "def app(): pass\n",
            ".wavefoundry/framework/README.md": "## Framework\n\nCanonical framework docs.\n",
            ".wavefoundry/framework/MANIFEST": "README.md\nMANIFEST\n",
            ".wavefoundry/framework/scripts/tools.py": "def helper():\n    return 1\n",
        })
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps({"indexing": {"project_include_prefixes": {"docs": [], "code": []}}}),
            encoding="utf-8",
        )

        index_dir = self.root / ".wavefoundry" / "index"

        # Run 1: docs only
        with patch.object(self.bi, "_get_embedder", return_value=_make_embedder_mock(dim=4)):
            self.bi.build_index(self.root, full=True, content="docs", verbose=False)
        meta_after_docs = json.loads((index_dir / "meta.json").read_text())["file_meta"]

        # Project meta must not contain ANY framework files
        framework_in_meta = [p for p in meta_after_docs if p.startswith(".wavefoundry/framework/")]
        self.assertEqual(framework_in_meta, [], f"project meta leaked framework files: {framework_in_meta}")
        self.assertIn("docs/guide.md", meta_after_docs)
        self.assertIn("src/app.py", meta_after_docs)

        # Run 2: code only — incremental, on top of the docs meta
        with patch.object(self.bi, "_get_embedder", side_effect=[_make_embedder_mock(dim=4), _make_embedder_mock(dim=4)]):
            self.bi.build_index(self.root, full=False, content="code", verbose=False)
        meta_after_code = json.loads((index_dir / "meta.json").read_text())["file_meta"]

        # Still no framework files in project meta
        framework_in_meta = [p for p in meta_after_code if p.startswith(".wavefoundry/framework/")]
        self.assertEqual(framework_in_meta, [], f"project meta leaked framework files after code run: {framework_in_meta}")

        # Stability invariant: docs run and code run must write IDENTICAL meta keys
        # (the original line-1822 fix prevented the 93-added/93-removed alternating cycle;
        # the new narrowing must preserve it).
        self.assertEqual(
            set(meta_after_docs.keys()),
            set(meta_after_code.keys()),
            "docs-run and code-run wrote different project meta — alternating cycle would resume",
        )

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
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
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
        meta = json.loads((index_dir / "meta.json").read_text())
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
        meta = json.loads((index_dir / "meta.json").read_text())
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
        meta_path = index_dir / "meta.json"

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
        meta = json.loads(meta_path.read_text())
        meta["file_meta"] = {
            k: v for k, v in meta["file_meta"].items()
            if not k.startswith("lib/")
        }
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
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


    def test_graph_only_rebuild_preserves_docs_code_chunker_versions(self):
        """graph-only rebuild must not wipe docs/code chunker_versions from metadata."""
        _make_repo(self.root, {"src/foo.py": "def f(): pass\n"})
        index_dir = self.root / ".wavefoundry" / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        current_cv = self.bi._get_chunker().CHUNKER_VERSION
        (index_dir / "meta.json").write_text(
            json.dumps({
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
            }),
            encoding="utf-8",
        )
        self.bi.build_index(self.root, full=True, content="graph", verbose=False)
        meta = json.loads((index_dir / "meta.json").read_text())
        self.assertEqual(meta.get("chunker_versions", {}).get("docs"), current_cv)
        self.assertEqual(meta.get("chunker_versions", {}).get("code"), current_cv)
        self.assertIn("docs", meta.get("content", []))
        self.assertIn("code", meta.get("content", []))


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
        (index_dir / "meta.json").write_text(json.dumps(base), encoding="utf-8")
        return index_dir

    def test_legacy_index_missing_walker_version_triggers_rebuild(self):
        """An index built before walker versioning has no walker_version key — must rebuild."""
        _make_repo(self.root, {"src/foo.md": "## Guide\n\nContent.\n"})
        self._write_meta({})  # no walker_version key
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        self.assertFalse(result.get("up_to_date", False))
        meta = json.loads((self.root / ".wavefoundry" / "index" / "meta.json").read_text())
        self.assertEqual(meta["walker_version"], self.bi.WALKER_VERSION)

    def test_stale_walker_version_triggers_rebuild(self):
        """An index with an older walker_version must be fully rebuilt."""
        _make_repo(self.root, {"src/foo.md": "## Guide\n\nContent.\n"})
        self._write_meta({"walker_version": "0"})
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        self.assertFalse(result.get("up_to_date", False))
        meta = json.loads((self.root / ".wavefoundry" / "index" / "meta.json").read_text())
        self.assertEqual(meta["walker_version"], self.bi.WALKER_VERSION)

    def test_current_walker_version_does_not_force_rebuild(self):
        """An up-to-date walker_version does not contribute to a forced rebuild."""
        _make_repo(self.root, {"src/foo.md": "## Guide\n\nContent.\n"})
        current_wv = self.bi.WALKER_VERSION
        self._write_meta({"walker_version": current_wv})
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            result = self.bi.build_index(self.root, full=False, content="docs", verbose=False)
        meta = json.loads((self.root / ".wavefoundry" / "index" / "meta.json").read_text())
        self.assertEqual(meta["walker_version"], current_wv)


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
        result = self.bi._detect_lance_drift(self.root, {}, verbose=False)
        self.assertEqual(result, set())

    def test_returns_empty_when_no_lance_tables_present(self):
        # No `.lance` dirs at index_dir → fresh layer, no drift
        result = self.bi._detect_lance_drift(self.root, self._as_meta({"docs/a.md"}), verbose=False)
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
                index_dir, self._as_meta({"docs/a.md"}), verbose=False,
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
            result = self.bi._detect_lance_drift(index_dir, file_meta, verbose=False)
        self.assertEqual(result, set())

    def test_includes_path_with_chunks_emitted_field_absent(self):
        """AC-3 (1p3iw): a path with no ``chunks_emitted`` field (legacy
        meta.json, or fresh stat-mismatch entry from `_detect_changes`) falls
        through to the drift check unchanged — one repair attempt learns the
        true count."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        db = self._make_db_with_paths({"docs": {"docs/present.md"}})
        file_meta = {
            "docs/present.md": {},
            "docs/legacy-missing.md": {},  # No chunks_emitted field
        }
        with patch.object(self.bi, "_get_lance_db", return_value=db):
            result = self.bi._detect_lance_drift(index_dir, file_meta, verbose=False)
        self.assertEqual(result, {"docs/legacy-missing.md"})

    def test_includes_path_with_chunks_emitted_positive_but_lance_missing(self):
        """AC-4 (1p3iw): a path with ``chunks_emitted > 0`` recorded but
        absent from Lance is real drift — the indexer believed it emitted N
        chunks last time, Lance has 0 rows for it now. Must converge by
        re-chunk + re-embed."""
        from unittest.mock import patch
        index_dir = self._index_dir_with_tables({"docs"})
        db = self._make_db_with_paths({"docs": {"docs/present.md"}})
        file_meta = {
            "docs/present.md": {"chunks_emitted": 3},
            "docs/real-drift.md": {"chunks_emitted": 5},
        }
        with patch.object(self.bi, "_get_lance_db", return_value=db):
            result = self.bi._detect_lance_drift(index_dir, file_meta, verbose=False)
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
        with patch.object(self.bi, "_get_lance_db", return_value=db):
            r1 = self.bi._detect_lance_drift(index_dir, file_meta, verbose=False)
            r2 = self.bi._detect_lance_drift(index_dir, file_meta, verbose=False)
            r3 = self.bi._detect_lance_drift(index_dir, file_meta, verbose=False)
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
            result = self.bi._detect_lance_drift(index_dir, file_meta, verbose=False)
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
        Enterprise-scale bound for Teton-shape monorepos."""
        elapsed = self._run_with_n_rows(100_000)
        self.assertLess(elapsed, 0.2,
            f"100K-row drift detection took {elapsed:.3f}s (expected < 0.2s)")


if __name__ == "__main__":
    unittest.main()
