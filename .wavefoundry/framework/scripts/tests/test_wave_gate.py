"""Tests for wave_gate.py — gate-management CLI."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]


def load_wave_gate():
    sys.modules.pop("wave_gate", None)
    spec = importlib.util.spec_from_file_location("wave_gate", SCRIPTS / "wave_gate.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class WaveGateOpenTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_wave_gate()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_open_creates_overrides_file_and_returns_zero(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = self.mod.cmd_open(self.root, "seed_edit_allowed")
        self.assertEqual(rc, 0)
        overrides = self.root / ".wavefoundry" / "guard-overrides.json"
        self.assertTrue(overrides.exists())
        data = json.loads(overrides.read_text(encoding="utf-8"))
        self.assertTrue(data["seed_edit_allowed"]["enabled"])
        self.assertIn("ok: gate 'seed_edit_allowed' opened.", out.getvalue())

    def test_open_already_open_returns_one(self):
        self.mod.cmd_open(self.root, "seed_edit_allowed")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = self.mod.cmd_open(self.root, "seed_edit_allowed")
        self.assertEqual(rc, 1)
        self.assertIn("already open", err.getvalue())

    def test_open_unknown_gate_returns_one(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = self.mod.cmd_open(self.root, "no_such_gate")
        self.assertEqual(rc, 1)
        self.assertIn("unknown gate", err.getvalue())


class WaveGateCloseTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_wave_gate()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_close_open_gate_returns_zero(self):
        self.mod.cmd_open(self.root, "framework_edit_allowed")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = self.mod.cmd_close(self.root, "framework_edit_allowed")
        self.assertEqual(rc, 0)
        data = json.loads((self.root / ".wavefoundry" / "guard-overrides.json").read_text(encoding="utf-8"))
        self.assertFalse(data["framework_edit_allowed"]["enabled"])
        self.assertIn("ok: gate 'framework_edit_allowed' closed.", out.getvalue())

    def test_close_already_closed_returns_zero_with_advisory(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = self.mod.cmd_close(self.root, "framework_edit_allowed")
        self.assertEqual(rc, 0)
        self.assertIn("advisory:", out.getvalue())
        self.assertIn("was already closed", out.getvalue())

    def test_close_unknown_gate_returns_one(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = self.mod.cmd_close(self.root, "no_such_gate")
        self.assertEqual(rc, 1)
        self.assertIn("unknown gate", err.getvalue())


class WaveGateStatusTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_wave_gate()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_status_lists_both_gates_closed_on_empty(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = self.mod.cmd_status(self.root)
        self.assertEqual(rc, 0)
        text = out.getvalue()
        self.assertIn("seed_edit_allowed: closed", text)
        self.assertIn("framework_edit_allowed: closed", text)

    def test_status_reflects_open_gate(self):
        self.mod.cmd_open(self.root, "seed_edit_allowed")
        out = io.StringIO()
        with redirect_stdout(out):
            self.mod.cmd_status(self.root)
        text = out.getvalue()
        self.assertIn("seed_edit_allowed: open", text)
        self.assertIn("framework_edit_allowed: closed", text)


class WaveGateMainTests(unittest.TestCase):
    """Cover the top-level main() entry, --root override, and arg parsing."""

    def setUp(self):
        self.mod = load_wave_gate()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_help_returns_zero(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = self.mod.main(["--help"])
        self.assertEqual(rc, 0)
        self.assertIn("Manages the", out.getvalue())

    def test_no_args_returns_zero_and_prints_help(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = self.mod.main([])
        self.assertEqual(rc, 0)

    def test_root_override_redirects_overrides_path(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = self.mod.main(["--root", str(self.root), "open", "seed_edit_allowed"])
        self.assertEqual(rc, 0)
        self.assertTrue((self.root / ".wavefoundry" / "guard-overrides.json").exists())

    def test_root_override_before_subcommand(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = self.mod.main(["--root", str(self.root), "status"])
        self.assertEqual(rc, 0)
        self.assertIn("Gate states:", out.getvalue())

    def test_unknown_subcommand_returns_one(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = self.mod.main(["--root", str(self.root), "wat"])
        self.assertEqual(rc, 1)
        self.assertIn("usage:", err.getvalue())


class WaveGateRoundTripTests(unittest.TestCase):
    """End-to-end: open + status + close + status sequence on a temp dir."""

    def setUp(self):
        self.mod = load_wave_gate()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_open_close_round_trip_preserves_state(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(self.mod.cmd_open(self.root, "seed_edit_allowed"), 0)
        data1 = json.loads((self.root / ".wavefoundry" / "guard-overrides.json").read_text(encoding="utf-8"))
        self.assertTrue(data1["seed_edit_allowed"]["enabled"])

        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(self.mod.cmd_close(self.root, "seed_edit_allowed"), 0)
        data2 = json.loads((self.root / ".wavefoundry" / "guard-overrides.json").read_text(encoding="utf-8"))
        self.assertFalse(data2["seed_edit_allowed"]["enabled"])


if __name__ == "__main__":
    unittest.main()
