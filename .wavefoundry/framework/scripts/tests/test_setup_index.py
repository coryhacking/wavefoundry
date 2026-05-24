from __future__ import annotations

import importlib.util
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, call, patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
SETUP_INDEX_PATH = SCRIPTS_ROOT / "setup_index.py"

FAKE_VENV_PYTHON = Path("/fake/venv/bin/python")


def load_setup_index():
    spec = importlib.util.spec_from_file_location("setup_index", SETUP_INDEX_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["setup_index"] = mod
    spec.loader.exec_module(mod)
    return mod


def load_indexer():
    indexer_path = SCRIPTS_ROOT / "indexer.py"
    spec = importlib.util.spec_from_file_location("wavefoundry_indexer", indexer_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["wavefoundry_indexer"] = mod
    spec.loader.exec_module(mod)
    return mod


class VenvBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_setup_index()

    def test_bootstrap_venv_creates_venv_when_absent(self):
        """_bootstrap_venv creates the venv when the directory does not exist."""
        with patch.object(self.mod, "_tool_venv_python", return_value=FAKE_VENV_PYTHON):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("subprocess.check_call") as check_call:
                    with redirect_stdout(io.StringIO()):
                        result = self.mod._bootstrap_venv()

        check_call.assert_called_once()
        cmd = check_call.call_args[0][0]
        self.assertIn("-m", cmd)
        self.assertIn("venv", cmd)
        self.assertEqual(result, FAKE_VENV_PYTHON)

    def test_bootstrap_venv_skips_creation_when_python_exists(self):
        """_bootstrap_venv does not call venv when the Python binary already exists."""
        with patch.object(self.mod, "_tool_venv_python", return_value=FAKE_VENV_PYTHON):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("subprocess.check_call") as check_call:
                    with redirect_stdout(io.StringIO()):
                        result = self.mod._bootstrap_venv()

        check_call.assert_not_called()
        self.assertEqual(result, FAKE_VENV_PYTHON)

    def test_bootstrap_venv_recreates_partial_venv(self):
        """_bootstrap_venv deletes and recreates a partial venv (dir exists but Python binary absent)."""
        venv_dir = FAKE_VENV_PYTHON.parent.parent

        def exists_side_effect(self_path):
            # venv_dir.exists() → True; venv_python.exists() → False (binary absent)
            return self_path == venv_dir

        with patch.object(self.mod, "_tool_venv_python", return_value=FAKE_VENV_PYTHON):
            with patch("pathlib.Path.exists", exists_side_effect):
                with patch("shutil.rmtree") as rmtree:
                    with patch("subprocess.check_call"):
                        with redirect_stdout(io.StringIO()):
                            self.mod._bootstrap_venv()

        rmtree.assert_called_once_with(venv_dir, ignore_errors=True)


class SetupIndexTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_setup_index()

    def test_ensure_deps_installs_missing_packages(self):
        """ensure_deps calls _install_deps for missing packages then rechecks."""
        with patch.object(self.mod, "_bootstrap_venv", return_value=FAKE_VENV_PYTHON):
            with patch.object(self.mod, "_missing_in_venv", return_value=["fastembed", "numpy"]):
                with patch.object(self.mod, "_install_deps"):
                    with self.assertRaises(SystemExit) as raised:
                        # Second call to _missing_in_venv still returns packages → exits 2
                        self.mod.ensure_deps()
        self.assertEqual(raised.exception.code, 2)

    def test_ensure_deps_succeeds_when_all_installed(self):
        with patch.object(self.mod, "_bootstrap_venv", return_value=FAKE_VENV_PYTHON):
            with patch.object(self.mod, "_missing_in_venv", return_value=[]):
                with redirect_stdout(io.StringIO()):
                    self.mod.ensure_deps()  # must not raise

    def test_ensure_deps_calls_install_with_missing_list(self):
        """ensure_deps passes the missing list from _missing_in_venv to _install_deps."""
        missing = ["fastembed", "lancedb"]
        call_count = [0]

        def missing_side_effect(venv_python):
            call_count[0] += 1
            return missing if call_count[0] == 1 else []

        with patch.object(self.mod, "_bootstrap_venv", return_value=FAKE_VENV_PYTHON):
            with patch.object(self.mod, "_missing_in_venv", side_effect=missing_side_effect):
                with patch.object(self.mod, "_install_deps") as mock_install:
                    with redirect_stdout(io.StringIO()):
                        self.mod.ensure_deps()

        mock_install.assert_called_once_with(missing, FAKE_VENV_PYTHON)

    def test_install_deps_invokes_pip_via_venv_python(self):
        """_install_deps uses the venv Python, not sys.executable."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            with redirect_stdout(io.StringIO()):
                self.mod._install_deps(["fastembed", "mcp[cli]", "tree-sitter>=0.24,<0.26"], FAKE_VENV_PYTHON)

        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0], str(FAKE_VENV_PYTHON))
        self.assertIn("-m", cmd)
        self.assertIn("pip", cmd)
        # Raw dep strings passed to subprocess — no shell quoting
        self.assertIn("fastembed", cmd)
        self.assertIn("mcp[cli]", cmd)
        self.assertIn("tree-sitter>=0.24,<0.26", cmd)
        # Shell-quoted forms must NOT appear in the subprocess cmd
        self.assertNotIn('"mcp[cli]"', cmd)
        self.assertNotIn('"tree-sitter>=0.24,<0.26"', cmd)
        # Must not use sys.executable
        self.assertNotEqual(cmd[0], sys.executable)

    def test_install_deps_does_not_use_break_system_packages(self):
        """_install_deps never passes --break-system-packages."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            with redirect_stderr(io.StringIO()):
                with redirect_stdout(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        self.mod._install_deps(["fastembed"], FAKE_VENV_PYTHON)

        all_calls = mock_run.call_args_list
        for c in all_calls:
            cmd = c[0][0]
            self.assertNotIn("--break-system-packages", cmd)

    def test_install_deps_exits_on_pip_failure(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            with redirect_stderr(io.StringIO()):
                with redirect_stdout(io.StringIO()):
                    with self.assertRaises(SystemExit) as raised:
                        self.mod._install_deps(["fastembed"], FAKE_VENV_PYTHON)
        self.assertEqual(raised.exception.code, 2)

    def test_build_index_uses_venv_python(self):
        root = Path("/tmp/wavefoundry-test-root")

        with patch.object(self.mod, "_tool_venv_python", return_value=FAKE_VENV_PYTHON):
            with patch("subprocess.check_call") as check_call:
                with redirect_stdout(io.StringIO()):
                    self.mod.build_index(
                        root,
                        full=True,
                        include_code=True,
                        verbose=True,
                        include_tests=True,
                        include_generated=True,
                        project_include_prefixes_for_docs=(),
                        project_include_prefixes_for_code=(),
                    )

        calls = [call.args[0] for call in check_call.call_args_list]
        self.assertEqual(len(calls), 1)
        cmd = calls[0]
        self.assertEqual(cmd[0], str(FAKE_VENV_PYTHON))
        self.assertNotEqual(cmd[0], sys.executable)
        self.assertIn(str(SCRIPTS_ROOT / "indexer.py"), cmd)
        self.assertIn("--content", cmd)
        self.assertIn("all", cmd)
        self.assertIn("--include-tests", cmd)
        self.assertIn("--include-generated", cmd)
        self.assertIn("--full", cmd)
        self.assertIn("--verbose", cmd)
        self.assertNotIn("--project-include-prefix", cmd)

    def test_build_index_can_forward_project_include_prefixes_for_code_pass(self):
        root = Path("/tmp/wavefoundry-test-root")
        with patch.object(self.mod, "_tool_venv_python", return_value=FAKE_VENV_PYTHON):
            with patch("subprocess.check_call") as check_call:
                with redirect_stdout(io.StringIO()):
                    self.mod.build_index(
                        root,
                        full=False,
                        include_code=True,
                        verbose=False,
                        project_include_prefixes_for_docs=("docs/external",),
                        project_include_prefixes_for_code=(".wavefoundry/framework/scripts", "vendor/docs"),
                    )
        calls = [call.args[0] for call in check_call.call_args_list]
        self.assertEqual(len(calls), 1)
        cmd = calls[0]
        self.assertIn("--content", cmd)
        self.assertIn("all", cmd)
        self.assertIn("--project-include-prefix", cmd)
        self.assertIn("docs/external", cmd)
        self.assertIn(".wavefoundry/framework/scripts", cmd)
        self.assertIn("vendor/docs", cmd)

    def test_tool_venv_python_default_path(self):
        """Default venv path is ~/.wavefoundry/venv."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("WAVEFOUNDRY_TOOL_VENV", None)
            result = self.mod._tool_venv_python()
        expected_dir = Path("~/.wavefoundry/venv").expanduser()
        self.assertEqual(result.parent.parent, expected_dir)

    def test_tool_venv_python_env_override(self):
        """WAVEFOUNDRY_TOOL_VENV overrides the default venv path."""
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": tmp}):
                result = self.mod._tool_venv_python()
        self.assertTrue(str(result).startswith(tmp))

    def test_required_imports_include_sql_tree_sitter(self):
        self.assertIn("tree-sitter-sql", self.mod.REQUIRED_IMPORTS)
        self.assertEqual(self.mod.REQUIRED_IMPORTS["tree-sitter-sql"], "tree_sitter_sql")

    def test_required_imports_include_lancedb(self):
        self.assertIn("lancedb", self.mod.REQUIRED_IMPORTS)
        self.assertEqual(self.mod.REQUIRED_IMPORTS["lancedb"], "lancedb")

    def test_prewarm_models_warms_then_verifies_offline(self):
        with patch.object(self.mod, "_indexer_models", return_value=["model-a", "model-b"]):
            with patch.object(self.mod, "_warm_model") as warm:
                with redirect_stdout(io.StringIO()):
                    self.mod.prewarm_models(include_code=True)

        self.assertEqual(
            warm.call_args_list,
            [
                call("model-a", local_files_only=False),
                call("model-a", local_files_only=True),
                call("model-b", local_files_only=False),
                call("model-b", local_files_only=True),
            ],
        )

    def test_prewarm_models_restores_offline_env(self):
        os.environ.pop("HF_HUB_OFFLINE", None)
        with patch.object(self.mod, "_indexer_models", return_value=["model-a"]):
            with patch.object(self.mod, "_warm_model"):
                with redirect_stdout(io.StringIO()):
                    self.mod.prewarm_models(include_code=False)
        self.assertNotIn("HF_HUB_OFFLINE", os.environ)

    def test_main_prewarms_before_building_index(self):
        with patch.object(self.mod, "ensure_deps") as ensure_deps:
            with patch.object(self.mod, "prewarm_models") as prewarm:
                with patch.object(self.mod, "build_index") as build_index:
                    with redirect_stdout(io.StringIO()):
                        rc = self.mod.main(["--root", "/tmp/repo", "--include-code"])

        self.assertEqual(rc, 0)
        ensure_deps.assert_called_once()
        prewarm.assert_called_once_with(include_code=True)
        build_index.assert_called_once()

    def test_workflow_project_include_prefixes_defaults_empty(self):
        root = Path("/tmp/wavefoundry-missing-config")
        with patch.object(Path, "exists", return_value=False):
            result = self.mod._workflow_project_include_prefixes(root)
        self.assertEqual(result["docs"], ())
        self.assertEqual(result["code"], ())

    def test_workflow_project_include_prefixes_reads_generic_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = root / "docs" / "workflow-config.json"
            cfg.parent.mkdir(parents=True, exist_ok=True)
            cfg.write_text(
                '{"indexing":{"project_include_prefixes":{"docs":["docs/external"],"code":[".wavefoundry/framework/scripts","vendor/docs"]}}}',
                encoding="utf-8",
            )
            result = self.mod._workflow_project_include_prefixes(root)
        self.assertEqual(result["docs"], ("docs/external",))
        self.assertEqual(result["code"], (".wavefoundry/framework/scripts", "vendor/docs"))

    def test_workflow_project_include_prefixes_accepts_list_shorthand(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = root / "docs" / "workflow-config.json"
            cfg.parent.mkdir(parents=True, exist_ok=True)
            cfg.write_text(
                '{"indexing":{"project_include_prefixes":[".wavefoundry/framework/scripts","vendor/docs"]}}',
                encoding="utf-8",
            )
            result = self.mod._workflow_project_include_prefixes(root)
        self.assertEqual(result["docs"], (".wavefoundry/framework/scripts", "vendor/docs"))
        self.assertEqual(result["code"], (".wavefoundry/framework/scripts", "vendor/docs"))

    def test_workflow_project_include_prefixes_supports_legacy_boolean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = root / "docs" / "workflow-config.json"
            cfg.parent.mkdir(parents=True, exist_ok=True)
            cfg.write_text(
                '{"indexing":{"include_framework_code_for_code_search":true}}',
                encoding="utf-8",
            )
            result = self.mod._workflow_project_include_prefixes(root)
        self.assertEqual(result["docs"], ())
        self.assertEqual(result["code"], (".wavefoundry/framework/scripts",))


class IndexerToolVenvTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_indexer()

    def test_auto_install_lancedb_uses_tool_venv_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            venv_root = Path(tmp)
            venv_python = venv_root / "bin" / "python"
            venv_python.parent.mkdir(parents=True, exist_ok=True)
            venv_python.write_text("", encoding="utf-8")
            with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv_root)}):
                with patch("subprocess.run", return_value=MagicMock(returncode=0)) as run_mock:
                    with redirect_stdout(io.StringIO()):
                        self.mod._auto_install_lancedb()
        cmd = run_mock.call_args.args[0]
        self.assertEqual(cmd[0], str(venv_python))
        self.assertNotEqual(cmd[0], sys.executable)

    def test_auto_install_lancedb_requires_bootstrapped_venv(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": tmp}):
                with self.assertRaises(ImportError) as raised:
                    self.mod._auto_install_lancedb()
        self.assertIn("tool venv is not bootstrapped", str(raised.exception))


class BackgroundCodeTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_setup_index()

    def test_background_code_prewarms_docs_only(self):
        """--background-code must not prewarm the code model in the foreground."""
        with patch.object(self.mod, "ensure_deps"):
            with patch.object(self.mod, "prewarm_models") as prewarm:
                with patch.object(self.mod, "build_index"):
                    with patch.object(self.mod, "_spawn_background_code_build"):
                        with redirect_stdout(io.StringIO()):
                            self.mod.main(["--root", "/tmp/repo", "--background-code"])
        prewarm.assert_called_once_with(include_code=False)

    def test_background_code_builds_docs_only_in_foreground(self):
        """--background-code must call build_index with include_code=False."""
        with patch.object(self.mod, "ensure_deps"):
            with patch.object(self.mod, "prewarm_models"):
                with patch.object(self.mod, "build_index") as build_index:
                    with patch.object(self.mod, "_spawn_background_code_build"):
                        with redirect_stdout(io.StringIO()):
                            self.mod.main(["--root", "/tmp/repo", "--background-code"])
        _, kwargs = build_index.call_args
        self.assertFalse(kwargs.get("include_code", True))

    def test_background_code_spawns_background_process(self):
        """--background-code must call _spawn_background_code_build after docs build."""
        with patch.object(self.mod, "ensure_deps"):
            with patch.object(self.mod, "prewarm_models"):
                with patch.object(self.mod, "build_index"):
                    with patch.object(self.mod, "_spawn_background_code_build") as spawn:
                        with redirect_stdout(io.StringIO()):
                            self.mod.main(["--root", "/tmp/repo", "--background-code"])
        spawn.assert_called_once()

    def test_include_code_takes_precedence_over_background_code(self):
        """--include-code with --background-code should behave as --include-code (synchronous)."""
        with patch.object(self.mod, "ensure_deps"):
            with patch.object(self.mod, "prewarm_models") as prewarm:
                with patch.object(self.mod, "build_index") as build_index:
                    with patch.object(self.mod, "_spawn_background_code_build") as spawn:
                        with redirect_stdout(io.StringIO()):
                            self.mod.main(["--root", "/tmp/repo", "--include-code", "--background-code"])
        prewarm.assert_called_once_with(include_code=True)
        _, kwargs = build_index.call_args
        self.assertTrue(kwargs.get("include_code", False))
        spawn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
