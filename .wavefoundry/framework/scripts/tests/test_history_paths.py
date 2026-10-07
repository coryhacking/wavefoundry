"""The one record-history definition and its nine call sites (wave 1zyb2, change 1zxnt).

Every site treats a file under ``journals/`` and under ``snapshots/`` as history and a
sibling outside both as live, keeps its own extras (``memory``, ``personas``,
``reports``), and tests a path RELATIVE to its scan root, so a checkout placed under an
ancestor directory named ``snapshots``, ``journals`` or ``memory`` skips nothing.
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
import tempfile
import shutil
import unittest
from pathlib import Path, PurePosixPath, PureWindowsPath

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import history_paths  # noqa: E402
from history_paths import HISTORY_PATH_COMPONENTS, is_history_path  # noqa: E402

REPO_ROOT = SCRIPTS_ROOT.parents[2]
ANCESTORS = ("snapshots", "journals", "memory")


class _TempRoots(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="wf-history-"))
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)
        saved = list(sys.path)
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), saved))

    def _root(self, ancestor: str | None = None) -> Path:
        root = self.base / (ancestor or "plain") / "repo"
        root.mkdir(parents=True)
        return root

    @staticmethod
    def _write(root: Path, rel: str, text: str) -> Path:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


class HelperTests(unittest.TestCase):
    def test_value_is_the_stable_contract(self):
        self.assertEqual(HISTORY_PATH_COMPONENTS, ("journals", "snapshots"))

    def test_component_match_not_substring(self):
        for rel in ("docs/agents/journals/a.md", "x/snapshots/y.md", "journals/a.md"):
            self.assertTrue(is_history_path(rel), rel)
            self.assertTrue(is_history_path(Path(rel)), rel)
        for rel in ("src/snapshotter.py", "docs/journal-notes.md", "docs/Journals/a.md", "docs/agents/a.md"):
            self.assertFalse(is_history_path(rel), rel)

    def test_windows_spelling_is_component_tested(self):
        self.assertTrue(is_history_path(PureWindowsPath("docs\\agents\\journals\\a.md")))
        self.assertFalse(is_history_path(PureWindowsPath("docs\\agents\\a.md")))

    def test_an_anchored_path_is_refused_not_tested(self):
        for path in ("/x/journals/a.md", "C:/x/journals/a.md", PurePosixPath("/snapshots/a.md"),
                     PureWindowsPath("C:\\journals\\a.md"), "//server/share/a.md"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                is_history_path(path)

    def test_stdlib_only_imports(self):
        tree = ast.parse((SCRIPTS_ROOT / "history_paths.py").read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.add((node.module or "").split(".")[0])
        self.assertTrue(names)
        self.assertEqual(sorted(n for n in names if n not in sys.stdlib_module_names and n != "__future__"), [])

    def test_listed_in_the_framework_script_census(self):
        import mcp_tool_extensions

        self.assertIn("history_paths", mcp_tool_extensions.FRAMEWORK_SCRIPT_MODULE_NAMES)

    def test_imports_in_a_fresh_isolated_interpreter(self):
        driver = (
            "import sys; sys.path.insert(0, sys.argv[1]); before = set(sys.modules); "
            "import history_paths; "
            "new = sorted(m for m in set(sys.modules) - before "
            "if (getattr(sys.modules[m], '__file__', '') or '').startswith(sys.argv[1])); "
            "print(new, history_paths.HISTORY_PATH_COMPONENTS)"
        )
        completed = subprocess.run(
            [sys.executable, "-I", "-B", "-c", driver, str(SCRIPTS_ROOT)],
            capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "['history_paths'] ('journals', 'snapshots')")

    def test_upgrade_sites_import_inside_the_function_after_the_path_insert(self):
        tree = ast.parse((SCRIPTS_ROOT / "upgrade_extensions.py").read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] + [getattr(node, "module", None) or ""]
                self.assertNotIn("history_paths", names, "no module-top import")
        functions = {
            node.name: node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name in ("_backfill_role_field_on_agent_docs", "_preview_role_field_backfill")
        }
        self.assertEqual(len(functions), 2)
        for name, function in functions.items():
            insert_line = import_line = None
            for node in ast.walk(function):
                if isinstance(node, ast.ImportFrom) and node.module == "history_paths":
                    import_line = node.lineno
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "insert" and ast.unparse(node.func.value) == "sys.path"):
                    insert_line = node.lineno
                self.assertFalse(
                    isinstance(node, ast.Attribute) and ast.unparse(node.value) == "record_paths",
                    f"{name} must not reach history through record_paths",
                )
            self.assertIsNotNone(import_line, name)
            self.assertIsNotNone(insert_line, name)
            self.assertLess(insert_line, import_line, name)


class ContractDocTests(unittest.TestCase):
    """AC-6: the documented tuple and the constant cannot drift."""

    def test_project_overview_pins_the_tuple(self):
        overview = REPO_ROOT / "docs" / "references" / "project-overview.md"
        layering = REPO_ROOT / "docs" / "architecture" / "layering-rules.md"
        if not overview.is_file() or not layering.is_file():
            self.skipTest("project docs are not part of this tree")
        text = overview.read_text(encoding="utf-8")
        self.assertIn(f"`HISTORY_PATH_COMPONENTS = {HISTORY_PATH_COMPONENTS!r}`", text)
        for phrase in ("changelog line", "path component", "Hugging Face"):
            self.assertIn(phrase, text)
        self.assertIn("`history_paths`", layering.read_text(encoding="utf-8"))


class AgentSurfaceIntegritySiteTests(_TempRoots):
    def _roles(self, root: Path) -> set[str]:
        import agent_surface_integrity

        return set(agent_surface_integrity._role_docs(root))

    def _seed(self, root: Path) -> None:
        for rel, role in (("docs/agents/journals/a.md", "a"), ("docs/agents/snapshots/b.md", "b"),
                          ("docs/agents/memory/m.md", "m"), ("docs/agents/live.md", "live")):
            self._write(root, rel, f"# x\n\nRole: {role}\n")

    def test_history_and_memory_skipped_sibling_live(self):
        root = self._root()
        self._seed(root)
        self.assertEqual(self._roles(root), {"live"})

    def test_ancestor_directories_do_not_skip(self):
        for ancestor in ANCESTORS:
            with self.subTest(ancestor=ancestor):
                root = self._root(ancestor)
                self._seed(root)
                self.assertEqual(self._roles(root), {"live"})


class WaveValidatorSiteTests(_TempRoots):
    def _seed(self, root: Path) -> None:
        for rel in ("docs/agents/journals/a.md", "docs/agents/snapshots/b.md",
                    "docs/agents/memory/m.md", "docs/agents/live.md"):
            self._write(root, rel, "# x\n\nOwner: x\n")

    @staticmethod
    def _flagged(failures: list[str]) -> set[str]:
        return {f.split(":", 1)[0] for f in failures}

    def test_role_validator(self):
        from wave_lint_lib import wave_validators

        for ancestor in (None, *ANCESTORS):
            with self.subTest(ancestor=ancestor):
                root = self._root(ancestor)
                self._seed(root)
                failures = wave_validators._check_agent_role_metadata(root)
                self.assertEqual(self._flagged(failures), {"docs/agents/live.md"}, failures)

    def test_category_validator(self):
        from wave_lint_lib import wave_validators

        for ancestor in (None, *ANCESTORS):
            with self.subTest(ancestor=ancestor):
                root = self._root(ancestor)
                self._seed(root)
                failures = wave_validators._check_agent_category_metadata(root)
                self.assertEqual(self._flagged(failures), {"docs/agents/live.md"}, failures)

    def test_expected_category(self):
        from wave_lint_lib import wave_validators

        expected = wave_validators._expected_agent_category
        self.assertIsNone(expected(Path("docs/agents/journals/x-reviewer.md")))
        self.assertIsNone(expected(Path("docs/agents/snapshots/x-reviewer.md")))
        self.assertIsNone(expected(Path("docs/agents/memory/x-reviewer.md")))
        self.assertEqual(expected(Path("docs/agents/x-reviewer.md")), "review")
        self.assertEqual(expected(Path("docs/agents/personas/p.md")), "persona")
        # Driven through the validator: under each ancestor the expected category
        # is still computed, so a wrong declaration is reported.
        for ancestor in ANCESTORS:
            with self.subTest(ancestor=ancestor):
                root = self._root(ancestor)
                self._write(root, "docs/agents/x-reviewer.md", "# x\n\nCategory: build\n")
                failures = wave_validators._check_agent_category_metadata(root)
                self.assertEqual(failures, ["docs/agents/x-reviewer.md: `Category:` must be `review`"])


class RenderReviewRoleSlugSiteTests(_TempRoots):
    def test_slug(self):
        import render_agent_surfaces as ras

        def slug(destination: str):
            return ras._review_role_slug(ras.ReviewProtocolCarrier("seed", destination))

        self.assertIsNone(slug("docs/agents/journals/r.md"))
        self.assertIsNone(slug("docs/agents/snapshots/r.md"))
        self.assertIsNone(slug("docs/agents/memory/r.md"))
        self.assertIsNone(slug("docs/agents/personas/r.md"))
        self.assertEqual(slug("docs/agents/r.md"), "r")

    def test_ancestor_directories_do_not_drop_native_wrappers(self):
        import render_agent_surfaces as ras

        role = next(r for r in map(ras._review_role_slug, ras.REVIEW_PROTOCOL_CARRIER_REGISTRY) if r)
        for ancestor in ANCESTORS:
            with self.subTest(ancestor=ancestor):
                root = self._root(ancestor)
                self._write(root, f".claude/agents/{role}.md", "# wrapper\n")
                manifest = ras.review_protocol_carrier_manifest(root)
                self.assertIn(f".claude/agents/{role}.md", manifest)


class UpgradeRoleBackfillSiteTests(_TempRoots):
    def _seed(self, root: Path) -> None:
        for rel in ("docs/agents/journals/a.md", "docs/agents/snapshots/b.md", "docs/agents/live.md"):
            self._write(root, rel, "# x\n\nStatus: active\n")

    def _ext(self):
        sys.path.insert(0, str(SCRIPTS_ROOT))
        import upgrade_extensions

        return upgrade_extensions

    def test_backfill(self):
        ext = self._ext()
        for ancestor in (None, *ANCESTORS):
            with self.subTest(ancestor=ancestor):
                root = self._root(ancestor)
                self._seed(root)
                modified = ext._backfill_role_field_on_agent_docs(root)
                self.assertEqual(len(modified), 1, modified)
                self.assertIn("live.md", modified[0])
                self.assertIn("Role: live", (root / "docs/agents/live.md").read_text(encoding="utf-8"))
                for rel in ("docs/agents/journals/a.md", "docs/agents/snapshots/b.md"):
                    self.assertEqual((root / rel).read_text(encoding="utf-8"), "# x\n\nStatus: active\n")

    def test_preview(self):
        ext = self._ext()
        for ancestor in (None, *ANCESTORS):
            with self.subTest(ancestor=ancestor):
                root = self._root(ancestor)
                self._seed(root)
                planned = ext._preview_role_field_backfill(root)
                self.assertEqual(planned, ["docs/agents/live.md: would insert `Role: live`"])


class ReconcileScanSiteTests(_TempRoots):
    def test_is_excluded(self):
        import reconcile_scan

        def excluded(rel: str) -> bool:
            return reconcile_scan.is_excluded(rel, name=rel.rsplit("/", 1)[-1], suffix=".md", excluded_dirs=())

        self.assertTrue(excluded("docs/journals/a.md"))
        self.assertTrue(excluded("docs/snapshots/a.md"))
        self.assertFalse(excluded("docs/guide.md"))
        self.assertFalse(excluded("docs/snapshotter.md"))

    def test_ancestor_directories_do_not_skip_the_walk(self):
        import reconcile_scan

        for ancestor in ANCESTORS:
            with self.subTest(ancestor=ancestor):
                root = self._root(ancestor)
                for rel in ("docs/guide.md", "docs/journals/a.md", "docs/snapshots/b.md"):
                    self._write(root, rel, "x\n")
                rels = {rel for _path, rel in reconcile_scan._iter_scannable_files(root)}
                self.assertIn("docs/guide.md", rels)
                self.assertNotIn("docs/journals/a.md", rels)
                self.assertNotIn("docs/snapshots/b.md", rels)


    @unittest.skipIf(sys.platform == "win32", "a file name holding a colon cannot exist on Windows")
    def test_a_drive_shaped_root_file_name_does_not_break_the_scan(self):
        # DEL-1: ``c:notes.md`` is a plain POSIX name; the scan reports it like any
        # other file instead of the history helper refusing it as drive-anchored.
        import reconcile_scan

        root = self._root()
        self._write(root, "c:notes.md", "Run `.wavefoundry/bin/docs-lint` here.\n")
        self._write(root, "a:b.md", "plain\n")
        self._write(root, "docs/snapshots/c:old.md", "Run `.wavefoundry/bin/docs-lint` here.\n")
        self.assertFalse(reconcile_scan.is_excluded("c:notes.md", name="c:notes.md", suffix=".md",
                                                    excluded_dirs=()))
        findings = reconcile_scan.scan_repo(root)
        self.assertEqual([(f.file, f.retired_surface) for f in findings], [("c:notes.md", "docs-lint")])


class DemotionSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from server_tools_support import load_server

        cls.srv = load_server()

    def _weight(self, path: str) -> float:
        return self.srv._doc_demotion_weight(path, "doc", ("zz-w/", "zz-p/"))

    def test_history_extras_and_live(self):
        jrnls = self.srv._DEMOTION_JRNLS
        self.assertEqual(self._weight("docs/agents/journals/a.md"), jrnls)
        self.assertEqual(self._weight("docs/snapshots/a.md"), jrnls)
        self.assertEqual(self._weight("docs/reports/a.md"), jrnls)
        self.assertEqual(self._weight("docs/feedback-log.md"), jrnls)
        self.assertEqual(self._weight("docs/journal-2026.md"), jrnls)
        self.assertEqual(self._weight("docs/guide.md"), 1.0)
        self.assertEqual(self._weight("src/snapshotter.py"), 1.0)

    def test_history_applies_to_document_results_only(self):
        # DEL-2: target source code under a history-named directory is not demoted;
        # a document there is.
        jrnls = self.srv._DEMOTION_JRNLS
        prefixes = ("zz-w/", "zz-p/")
        self.assertEqual(self.srv._doc_demotion_weight("src/snapshots/model.py", "code", prefixes), 1.0)
        self.assertEqual(self.srv._doc_demotion_weight("src/journals/entry.py", "code", prefixes), 1.0)
        self.assertEqual(self.srv._doc_demotion_weight("docs/snapshots/a.md", "doc", prefixes), jrnls)
        results = [
            {"path": "src/snapshots/model.py", "kind": "code", "score": 1.0},
            {"path": "docs/snapshots/a.md", "kind": "doc", "score": 1.0},
        ]
        demoted, count = self.srv._demote_doc_results(results, "explanatory", prefixes)
        self.assertEqual(count, 1)
        self.assertEqual(demoted[0]["score"], 1.0)
        self.assertLess(demoted[1]["score"], 1.0)

    def test_an_absolute_path_under_an_ancestor_is_not_history(self):
        for ancestor in ANCESTORS:
            with self.subTest(ancestor=ancestor):
                self.assertEqual(self._weight(f"/x/{ancestor}/repo/docs/guide.md"), 1.0)


class CensusTests(unittest.TestCase):
    """AC-3: the history literals appear only in the definition."""

    def test_no_other_history_literal_exclusion(self):
        allowed = {"history_paths.py", "model_bundle.py", "accel_embedder.py", "setup_index.py",
                   "upgrade_wavefoundry.py", "upgrade_extensions.py"}
        pattern = re.compile(r'"journals"|"snapshots"')
        offenders = []
        for path in sorted(SCRIPTS_ROOT.rglob("*.py")):
            rel = path.relative_to(SCRIPTS_ROOT)
            if rel.parts[0] == "tests" or path.name in allowed:
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if pattern.search(line):
                    offenders.append(f"{rel.as_posix()}:{number}")
        self.assertEqual(offenders, [])
        ext = (SCRIPTS_ROOT / "upgrade_extensions.py").read_text(encoding="utf-8")
        self.assertNotRegex(ext, r'"journals" in \w+\.parts')


if __name__ == "__main__":
    unittest.main()
