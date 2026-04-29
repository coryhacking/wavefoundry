from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = TESTS_ROOT.parent


def _load_gardener():
    path = SCRIPTS_ROOT / "docs_gardener.py"
    spec = importlib.util.spec_from_file_location("docs_gardener_test_module", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


dg = _load_gardener()


class DocsGardenerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="docs-gardener-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def _write_doc(self, rel: str, last_verified: str = "2000-01-01") -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            f"# T\n\nOwner: Engineering\nStatus: draft\nLast verified: {last_verified}\n",
            encoding="utf-8",
        )
        return p

    def _minimal_manifest(self) -> None:
        mp = self.root / "docs" / "prompts" / "prompt-surface-manifest.json"
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(
            '{"schema_version": 1, "framework_revision": "2099-01-01a", '
            '"last_gardened_at": "1999-01-01", '
            '"public_prompt_surface": [], "seed_framework_source": "test"}\n',
            encoding="utf-8",
        )

    def test_default_run_stamps_changed_docs(self) -> None:
        self._init_git()
        tracked = self._write_doc("docs/tracked.md", "2000-01-01")
        subprocess.run(
            ["git", "-C", str(self.root), "add", "docs/tracked.md"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-m", "init"],
            check=True, capture_output=True,
        )
        other = self._write_doc("docs/other.md", "2000-01-01")
        self._minimal_manifest()
        tracked.write_text(tracked.read_text(encoding="utf-8") + "\n## touch\n", encoding="utf-8")
        code, _ = dg.gardener_run(self.root, dg.parse_args(["--date", "2020-06-01"]))
        self.assertEqual(code, 0)
        self.assertIn("Last verified: 2020-06-01", tracked.read_text(encoding="utf-8"))
        self.assertIn("Last verified: 2000-01-01", other.read_text(encoding="utf-8"))

    def test_paths_updates_target_only(self) -> None:
        a = self._write_doc("docs/a.md", "2000-01-01")
        b = self._write_doc("docs/b.md", "2000-01-01")
        self._minimal_manifest()
        code, paths = dg.gardener_run(
            self.root,
            dg.parse_args(["--date", "2020-06-01", "--paths", "docs/a.md"]),
        )
        self.assertEqual(code, 0)
        self.assertIn("Last verified: 2020-06-01", a.read_text(encoding="utf-8"))
        self.assertIn("Last verified: 2000-01-01", b.read_text(encoding="utf-8"))
        self.assertTrue(any("docs/a.md" in p for p in paths))

    def test_all_docs_and_paths_are_mutually_exclusive(self) -> None:
        self._write_doc("docs/a.md")
        with self.assertRaises(SystemExit):
            dg.gardener_run(self.root, dg.parse_args(["--all-docs", "--paths", "docs/a.md"]))

    def test_all_docs_stamps_every_doc(self) -> None:
        a = self._write_doc("docs/a.md", "2000-01-01")
        b = self._write_doc("docs/b.md", "2000-01-01")
        self._minimal_manifest()
        code, _ = dg.gardener_run(self.root, dg.parse_args(["--date", "2020-06-01", "--all-docs"]))
        self.assertEqual(code, 0)
        self.assertIn("Last verified: 2020-06-01", a.read_text(encoding="utf-8"))
        self.assertIn("Last verified: 2020-06-01", b.read_text(encoding="utf-8"))

    def _init_git(self) -> None:
        subprocess.run(
            ["git", "-C", str(self.root), "init"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.email", "t@e.st"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.name", "test"],
            check=True, capture_output=True,
        )

    def test_cli_subprocess_smoke(self) -> None:
        self._write_doc("docs/a.md")
        env = os.environ.copy()
        env["PROJECT_ROOT"] = str(self.root)
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_ROOT / "docs_gardener.py"), "--date", "2020-01-03"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)


if __name__ == "__main__":
    unittest.main()
