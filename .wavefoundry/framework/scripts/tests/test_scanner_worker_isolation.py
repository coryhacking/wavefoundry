#!/usr/bin/env python3
"""The scanner worker starts in isolated mode (wave 22upa, change 22ubg).

``PYTHONPATH`` entries precede the standard library on ``sys.path``, so without ``-I`` a
directory on ``PYTHONPATH`` holding ``json.py`` would run before the worker installs its
audit hook. The worker adds its own ``scripts/`` directory, so it needs nothing from the
environment.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from wave_lint_lib import betterleaks_worker as worker


class WorkerIsolationTests(unittest.TestCase):
    def test_the_default_command_is_isolated(self):
        client = worker._Client()
        self.addCleanup(client.close)
        script = str(Path(worker.__file__).resolve())
        self.assertEqual(client._command[1:3], ["-I", "-B"])
        self.assertEqual(client._command[3:], [script, "--worker"])

    def test_a_module_on_pythonpath_is_never_imported(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "planted-ran"
            planted = Path(tmp) / "planted"
            planted.mkdir()
            (planted / "json.py").write_text(
                f"open({str(marker)!r}, 'w').close()\nraise ImportError('planted json')\n", encoding="utf-8")
            client = worker._Client()
            self.addCleanup(client.close)
            with mock.patch.dict(os.environ, {"PYTHONPATH": str(planted)}):
                result = client.request("parse_toml", {"text": "n = 1"})
            self.assertEqual(result, {"n": 1})
            self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
