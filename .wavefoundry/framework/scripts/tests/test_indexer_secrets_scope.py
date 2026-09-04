"""Wave 1x4ol / 1x4oj: a graph-only rebuild must not force a full secrets scan.

The build's ``full`` flag means "rebuild the GRAPH from scratch". It says
nothing about file CONTENT, which is the only thing secret detection depends
on. Passing it through as a full SCAN bypassed the per-file content-hash
cache and re-read every tracked file on every graph rebuild.

Two layers are pinned here, because the defect lived at their seam:

* the indexer layer: what ``build_index`` hands the scanner for each content
  mode (the flag, and the candidate set), and
* the scanner layer: what the REAL scanner does with a non-full call against a
  REAL cache, including every escalation that must still force a full pass.

No mock scanner is used at the scanner layer. A mock cannot skip a file, so a
"nonzero cache-skipped" assertion against one would be vacuous.
"""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))

from test_indexer import _make_embedder_mock, _make_repo, load_build_index  # noqa: E402
from test_secret_scan_cache import RULES_TOML, _CacheCase  # noqa: E402


class GraphOnlyBuildScopesSecretsFullFlagTests(unittest.TestCase):
    """Indexer layer: the flag and the candidate set handed to the scanner."""

    def setUp(self):
        import tempfile
        self.bi = load_build_index()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        _make_repo(self.root, {
            "src/foo.py": "def f():\n    return 1\n",
            "src/bar.py": "from foo import f\n\ndef g():\n    return f()\n",
        })

    def _capture_secrets_call(self, **build_kwargs) -> list[dict]:
        calls: list[dict] = []

        def _fake(**kwargs):
            calls.append(kwargs)
            return {}

        with patch.object(self.bi, "_build_secrets_artifacts", side_effect=_fake):
            self.bi.build_index(self.root, verbose=False, **build_kwargs)
        return calls

    def test_graph_only_full_rebuild_does_not_request_a_full_scan(self):
        # AC-1 (indexer half): the graph's full flag must not become the
        # scanner's full flag.
        calls = self._capture_secrets_call(full=True, content="graph")
        self.assertEqual(1, len(calls), "the scan must still be submitted once")
        self.assertIs(False, calls[0]["full"])

    def test_graph_only_rebuild_still_hands_the_scanner_every_file(self):
        # AC-6: the change is safe ONLY because the candidate set is non-empty.
        # The scanner's incremental branch returns early on an empty set and
        # reports success, so a later narrowing here would make the scan a
        # silent no-op. Pin it.
        calls = self._capture_secrets_call(full=True, content="graph")
        changed = calls[0]["changed"]
        self.assertTrue(changed, "graph-only build handed the scanner an empty candidate set")
        self.assertIn("src/foo.py", changed)
        self.assertIn("src/bar.py", changed)

    def test_non_graph_full_rebuild_still_requests_a_full_scan(self):
        # Control: the docs/code full path is unchanged. Without this the
        # scoping could be "fixed" by dropping the full scan everywhere.
        docs_mock = _make_embedder_mock(dim=4)
        with patch.object(self.bi, "_get_embedder", return_value=docs_mock):
            calls = self._capture_secrets_call(full=True, content="docs")
        self.assertEqual(1, len(calls))
        self.assertIs(True, calls[0]["full"])


class GraphOnlyIncrementalScanTests(_CacheCase):
    """Scanner layer: the REAL scanner against a REAL cache."""

    def setUp(self):
        super().setUp()
        self.scan_dir = self.index_dir / "scan"
        self.scan_dir.mkdir(parents=True, exist_ok=True)
        self._write("a.py", "x = 1\n")
        self._write("b.py", "y = 2\n")
        self._write("c.md", "# notes\n")

    def _all_rel(self) -> set[str]:
        return {
            str(p.relative_to(self.root)).replace("\\", "/")
            for p in self.root.rglob("*")
            if p.is_file() and ".wavefoundry" not in p.parts and p.name != "scan-findings.json"
        }

    def _run(self, *, full: bool, changed: set[str] | None = None, removed: set[str] | None = None):
        out = io.StringIO()
        with redirect_stdout(out):
            result = self.scan_secrets.update_secrets_scan(
                root=self.root, scan_dir=self.scan_dir,
                changed=set(self._all_rel() if changed is None else changed),
                removed=set(removed or ()), full=full, verbose=True,
            )
        return result, out.getvalue(), self.scan_secrets._load_scan_state(self.scan_dir)

    def _warm(self):
        result, _out, state = self._run(full=True)
        self.assertEqual("full", state["scan_type"])
        return result

    def test_incremental_after_a_full_scan_skips_unchanged_files(self):
        # AC-1 (scanner half): the path a graph rebuild now takes reports a
        # NONZERO cache-skipped count and records itself as incremental.
        self._warm()
        result, out, state = self._run(full=False)
        self.assertEqual("incremental", state["scan_type"])
        self.assertGreater(result["files_skipped"], 0)
        self.assertEqual(0, result["files_scanned"])
        self.assertIn("secrets scan complete (incremental)", out)

    def test_a_changed_file_is_scanned_not_skipped(self):
        # AC-3: the cache keys on content, so a real edit cannot be skipped.
        self._warm()
        self._write("b.py", "y = 2\nz = 3\n")
        result, _out, state = self._run(full=False)
        self.assertEqual("incremental", state["scan_type"])
        self.assertEqual(1, result["files_scanned"], "the edited file must be scanned")
        self.assertEqual(len(self._all_rel()) - 1, result["files_skipped"])

    def test_rules_change_still_forces_a_full_scan_from_the_incremental_path(self):
        # AC-2 (a): a rules edit is one of the three ways a previously
        # scanned file can yield a new finding. It must win over full=False.
        self._warm()
        (self.root / ".wavefoundry" / "framework" / "scan-rules.toml").write_text(
            RULES_TOML + '\n[[rules]]\nid = "added"\ndescription = "x"\nregex = \'\'\'ADDED-[A-Z]{4}\'\'\'\nkeywords = ["added-"]\n',
            encoding="utf-8",
        )
        result, _out, state = self._run(full=False)
        self.assertEqual("full", state["scan_type"])
        self.assertTrue(result["rules_change_escalation"])

    def test_scanner_version_change_still_forces_a_full_scan(self):
        # AC-2 (b).
        self._warm()
        state = self.scan_secrets._load_scan_state(self.scan_dir)
        state["scanner_version"] = "stale-version"
        self.scan_secrets._save_scan_state(self.scan_dir, state)
        _result, _out, state = self._run(full=False)
        self.assertEqual("full", state["scan_type"])

    def test_missing_findings_ledger_still_forces_a_full_scan(self):
        # AC-2 (c).
        self._warm()
        (self.root / "docs" / "scan-findings.json").unlink()
        _result, _out, state = self._run(full=False)
        self.assertEqual("full", state["scan_type"])

    def test_an_empty_candidate_set_returns_early_and_prints_no_completion(self):
        # AC-6 (characterisation): this is the silent-no-op shape the
        # indexer-layer pin exists to prevent. Make it visible in a test.
        self._warm()
        result, out, _state = self._run(full=False, changed=set(), removed=set())
        self.assertTrue(result["up_to_date"])
        self.assertEqual(0, result["files_skipped"])
        self.assertEqual(0, result["files_scanned"])
        self.assertNotIn("secrets scan complete", out)
        self.assertIn("nothing changed", out)


if __name__ == "__main__":
    unittest.main()
