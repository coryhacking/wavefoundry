from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
SETUP_WF_PATH = SCRIPTS_ROOT / "setup_wavefoundry.py"


def load_setup_wavefoundry():
    spec = importlib.util.spec_from_file_location("setup_wavefoundry", SETUP_WF_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["setup_wavefoundry"] = mod
    spec.loader.exec_module(mod)
    return mod


class SetupWavefoundryTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_setup_wavefoundry()

    def test_main_delegates_args_to_setup_index_main(self):
        delegated: list[list[str] | None] = []

        class FakeSetupIndex:
            @staticmethod
            def main(argv=None):
                delegated.append(argv)
                return 7

        with patch.object(self.mod, "_load_setup_index", return_value=FakeSetupIndex):
            result = self.mod.main(["--root", "/tmp/repo", "--full"])

        self.assertEqual(result, 7)
        self.assertEqual(delegated, [["--root", "/tmp/repo", "--full"]])


if __name__ == "__main__":
    unittest.main()
