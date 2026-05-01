from __future__ import annotations

import importlib.util
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import call, patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
SETUP_INDEX_PATH = SCRIPTS_ROOT / "setup_index.py"


def load_setup_index():
    spec = importlib.util.spec_from_file_location("setup_index", SETUP_INDEX_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["setup_index"] = mod
    spec.loader.exec_module(mod)
    return mod


class SetupIndexTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_setup_index()

    def test_missing_deps_exits_with_isolated_venv_help(self):
        with patch.object(self.mod, "_installed", return_value=False):
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    self.mod.ensure_deps()

        self.assertEqual(raised.exception.code, 2)

    def test_dependency_help_mentions_tool_venv_and_required_deps(self):
        help_text = self.mod._dependency_help(["fastembed"])

        self.assertIn("python3 -m venv", help_text)
        self.assertIn("fastembed", help_text)
        self.assertIn("numpy", help_text)
        self.assertIn('"mcp[cli]"', help_text)
        self.assertIn("WAVEFOUNDRY_TOOL_VENV", help_text)

    def test_build_index_uses_current_python(self):
        root = Path("/tmp/wavefoundry-test-root")

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
        self.assertEqual(cmd[0], sys.executable)
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


if __name__ == "__main__":
    unittest.main()
