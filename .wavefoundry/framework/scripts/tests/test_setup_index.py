from __future__ import annotations

import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


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
                )

        calls = [call.args[0] for call in check_call.call_args_list]
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], sys.executable)
        self.assertEqual(calls[1][0], sys.executable)
        self.assertIn(str(SCRIPTS_ROOT / "indexer.py"), calls[0])
        self.assertIn(str(SCRIPTS_ROOT / "indexer.py"), calls[1])
        self.assertIn("--content", calls[0])
        self.assertIn("docs", calls[0])
        self.assertIn("--content", calls[1])
        self.assertIn("code", calls[1])
        self.assertIn("--include-tests", calls[1])
        self.assertIn("--include-generated", calls[1])
        self.assertIn("--full", calls[0])
        self.assertIn("--full", calls[1])
        self.assertIn("--verbose", calls[0])
        self.assertIn("--verbose", calls[1])


if __name__ == "__main__":
    unittest.main()
