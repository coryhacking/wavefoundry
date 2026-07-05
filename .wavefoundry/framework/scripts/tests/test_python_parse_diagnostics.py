"""Wave 1p9pe / change 1p9p6: indexing-path ``ast.parse`` diagnostics.

Covers:
- AC-2: the indexing-path parse sites (``chunker.chunk_python``,
  ``chunker._extract_python_module_docstring``,
  ``graph_indexer._extract_python_artifact``) pass ``filename=`` so a
  ``SyntaxWarning`` from indexed Python names the real path, not ``<unknown>``.
  Includes the integration-shaped effectiveness check: a real graph index
  build over a fixture tree containing an invalid-escape Python source logs
  the warning naming the fixture path.
- AC-3: ``filename=`` is diagnostic-only — the existing ``except SyntaxError``
  fallbacks still degrade gracefully.
- AC-4: tree-wide regression sweep — no tracked ``.py`` file emits an
  invalid-escape ``SyntaxWarning``.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
import warnings
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
CHUNKER_PATH = SCRIPTS_ROOT / "chunker.py"
GRAPH_INDEXER_PATH = SCRIPTS_ROOT / "graph_indexer.py"

# Built with an escaped backslash so THIS file carries no invalid escape:
# at runtime the string contains a literal backslash-backtick sequence,
# which is an invalid escape when the string is parsed as Python source.
INVALID_ESCAPE_SOURCE = (
    "def helper():\n"
    "    \"\"\"See \\`docs\\` for details.\"\"\"\n"
    "    return 1\n"
)

BROKEN_SOURCE = "def broken(:\n    pass\n"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _syntax_warnings(record):
    return [w for w in record if issubclass(w.category, SyntaxWarning)]


class ParseFilenameInWarningTests(unittest.TestCase):
    """AC-2 unit level: the emitted SyntaxWarning's filename is the supplied path."""

    @classmethod
    def setUpClass(cls):
        cls.chunker = _load("chunker", CHUNKER_PATH)
        cls.graph_indexer = _load("graph_indexer", GRAPH_INDEXER_PATH)

    def test_chunk_python_warning_names_supplied_path(self):
        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            chunks = self.chunker.chunk_python(INVALID_ESCAPE_SOURCE, "pkg/mod.py")
        self.assertTrue(chunks)
        syn = _syntax_warnings(record)
        self.assertTrue(syn, "expected an invalid-escape SyntaxWarning")
        self.assertEqual(syn[0].filename, "pkg/mod.py")
        self.assertNotIn("<unknown>", syn[0].filename)

    def test_extract_python_module_docstring_warning_names_supplied_path(self):
        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            doc = self.chunker._extract_python_module_docstring(
                INVALID_ESCAPE_SOURCE, filename="pkg/mod.py"
            )
        # Source has a function docstring, not a module docstring.
        self.assertIsNone(doc)
        syn = _syntax_warnings(record)
        self.assertTrue(syn, "expected an invalid-escape SyntaxWarning")
        self.assertEqual(syn[0].filename, "pkg/mod.py")

    def test_extract_python_module_docstring_default_stays_call_compatible(self):
        # Existing single-argument callers keep working; default is "<unknown>".
        doc = self.chunker._extract_python_module_docstring('"""Module doc."""\n')
        self.assertEqual(doc, "Module doc.")

    def test_graph_extract_warning_names_rel_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir(parents=True)
            (root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")
            src = root / "src" / "bad_escape.py"
            src.parent.mkdir(parents=True)
            src.write_text(INVALID_ESCAPE_SOURCE, encoding="utf-8")
            with warnings.catch_warnings(record=True) as record:
                warnings.simplefilter("always")
                self.graph_indexer.update_graph_index(
                    root=root,
                    index_dir=root / ".wavefoundry" / "index",
                    layer="project",
                    files=[src],
                    current_file_meta={"src/bad_escape.py": {"hash": "h1"}},
                    changed={"src/bad_escape.py"},
                    removed=set(),
                    walker_version="1",
                    chunker_version="1",
                    verbose=False,
                )
        syn = _syntax_warnings(record)
        self.assertTrue(syn, "expected an invalid-escape SyntaxWarning from graph extraction")
        self.assertTrue(
            any(w.filename.replace("\\", "/").endswith("src/bad_escape.py") for w in syn),
            f"warning filenames {[w.filename for w in syn]} do not name the fixture path",
        )
        self.assertFalse(any(w.filename == "<unknown>" for w in syn))


class SyntaxErrorFallbackTests(unittest.TestCase):
    """AC-3: filename= is diagnostic-only; SyntaxError still degrades gracefully."""

    @classmethod
    def setUpClass(cls):
        cls.chunker = _load("chunker", CHUNKER_PATH)

    def test_chunk_python_syntax_error_falls_back_to_line_window(self):
        chunks = self.chunker.chunk_python(BROKEN_SOURCE, "pkg/broken.py")
        self.assertTrue(chunks)
        self.assertTrue(all(c.language == "python" for c in chunks))

    def test_extract_python_module_docstring_syntax_error_returns_none(self):
        self.assertIsNone(
            self.chunker._extract_python_module_docstring(BROKEN_SOURCE, filename="pkg/broken.py")
        )


class IndexBuildWarningNamesFixturePathTests(unittest.TestCase):
    """AC-2 effectiveness clause: a real graph index build over a fixture tree
    containing an invalid-escape Python source logs the warning naming the
    fixture path (not ``<unknown>``). Runs in a fresh subprocess so the
    warning surfaces on the process stderr stream exactly as it does in a
    live indexer build log."""

    def test_real_graph_build_logs_fixture_path_not_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir(parents=True)
            (root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")
            src = root / "src" / "bad_escape.py"
            src.parent.mkdir(parents=True)
            src.write_text(INVALID_ESCAPE_SOURCE, encoding="utf-8")

            child = textwrap.dedent(
                """
                import importlib.util
                import pathlib
                import sys

                gi_path, root_arg = sys.argv[1], sys.argv[2]
                root = pathlib.Path(root_arg)
                spec = importlib.util.spec_from_file_location("graph_indexer_child", gi_path)
                mod = importlib.util.module_from_spec(spec)
                sys.modules["graph_indexer_child"] = mod
                spec.loader.exec_module(mod)
                mod.update_graph_index(
                    root=root,
                    index_dir=root / ".wavefoundry" / "index",
                    layer="project",
                    files=[root / "src" / "bad_escape.py"],
                    current_file_meta={"src/bad_escape.py": {"hash": "h1"}},
                    changed={"src/bad_escape.py"},
                    removed=set(),
                    walker_version="1",
                    chunker_version="1",
                    verbose=False,
                )
                print("BUILD_OK", flush=True)
                """
            )
            proc = subprocess.run(
                [sys.executable, "-B", "-c", child, str(GRAPH_INDEXER_PATH), str(root)],
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("BUILD_OK", proc.stdout)
            # The build is real: the graph artifact was written.
            self.assertTrue(
                (root / ".wavefoundry" / "index" / "graph" / "project-graph.json").exists()
            )
        self.assertIn("SyntaxWarning", proc.stderr)
        self.assertIn("invalid escape sequence", proc.stderr)
        self.assertIn("src/bad_escape.py", proc.stderr.replace("\\", "/"))
        self.assertNotIn("<unknown>", proc.stderr)


class InvalidEscapeSweepTests(unittest.TestCase):
    """AC-4 regression guard: no tracked, non-vendored ``.py`` file emits an
    invalid-escape SyntaxWarning."""

    VENDORED_MARKERS = ("/vendor/", "/node_modules/", "/third_party/")

    def test_no_tracked_python_file_has_invalid_escape(self):
        try:
            listing = subprocess.run(
                ["git", "ls-files", "-z", "--", "*.py"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )
        except (OSError, subprocess.SubprocessError):
            self.skipTest("git not available or not a git checkout")
        rel_paths = [p for p in listing.stdout.split("\0") if p]
        self.assertTrue(rel_paths, "git ls-files returned no Python files")

        offenders: list[str] = []
        for rel in rel_paths:
            posix = "/" + rel.replace("\\", "/") + "/"
            if any(marker in posix for marker in self.VENDORED_MARKERS):
                continue
            path = REPO_ROOT / rel
            try:
                source = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            with warnings.catch_warnings(record=True) as record:
                warnings.simplefilter("always")
                try:
                    ast.parse(source, filename=rel)
                except SyntaxError as exc:
                    if "invalid escape" in str(exc):
                        offenders.append(f"{rel}:{exc.lineno}: {exc}")
                    continue
            for w in record:
                if issubclass(w.category, SyntaxWarning) and "invalid escape" in str(w.message):
                    offenders.append(f"{w.filename}:{w.lineno}: {w.message}")
        self.assertEqual(
            offenders,
            [],
            "tracked .py files with invalid-escape SyntaxWarning:\n" + "\n".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
