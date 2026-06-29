"""Tests for the shared CLI UTF-8 stdio reconfigure (wave 1p8gv).

The field defect: a native-Windows upgrade crashed with UnicodeEncodeError the first time it
``print("⚠")`` on a cp1252 console. We simulate a cp1252-backed stdout and assert that printing
non-ASCII raises BEFORE the reconfigure and does NOT raise AFTER it.
"""
from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import cli_stdio


class _Cp1252Stream:
    """A TextIOWrapper-like stream pinned to cp1252 that, like a real Windows console, raises on
    non-encodable characters — until ``reconfigure`` swaps it to UTF-8 with errors=replace."""

    def __init__(self) -> None:
        self._buf = io.BytesIO()
        self.encoding = "cp1252"
        self.errors = "strict"

    def write(self, s: str) -> int:
        data = s.encode(self.encoding, self.errors)  # raises UnicodeEncodeError under cp1252/strict
        return self._buf.write(data)

    def flush(self) -> None:
        pass

    def reconfigure(self, *, encoding=None, errors=None, **kwargs):
        if encoding is not None:
            self.encoding = encoding
        if errors is not None:
            self.errors = errors

    def getvalue(self) -> bytes:
        return self._buf.getvalue()


class ConfigureUtf8StdioTests(unittest.TestCase):
    def test_cp1252_print_raises_before_reconfigure(self):
        stream = _Cp1252Stream()
        with self.assertRaises(UnicodeEncodeError):
            stream.write("⚠\n")  # ⚠ is not encodable in cp1252

    def test_cp1252_print_does_not_raise_after_reconfigure(self):
        out = _Cp1252Stream()
        err = _Cp1252Stream()
        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
            cli_stdio.configure_utf8_stdio()
            # After reconfigure both streams are UTF-8 with errors=replace — printing ⚠ must not raise.
            print("⚠ upgrade warning", file=sys.stdout)
            print("── phase", file=sys.stderr)  # box-drawing ──
        self.assertEqual(out.encoding, "utf-8")
        self.assertEqual(out.errors, "replace")
        self.assertIn("⚠".encode("utf-8"), out.getvalue())
        self.assertIn("─".encode("utf-8"), err.getvalue())

    def test_stream_without_reconfigure_is_skipped(self):
        # A stream object lacking reconfigure (e.g. a redirected pipe) must be skipped silently —
        # the helper must never crash the program it is hardening.
        class NoReconfigure:
            encoding = "utf-8"

        with patch.object(sys, "stdout", NoReconfigure()), patch.object(sys, "stderr", NoReconfigure()):
            cli_stdio.configure_utf8_stdio()  # no exception

    def test_reconfigure_failure_is_swallowed(self):
        class RaisingStream:
            def reconfigure(self, *a, **k):
                raise ValueError("unsupported option")

        with patch.object(sys, "stdout", RaisingStream()), patch.object(sys, "stderr", RaisingStream()):
            cli_stdio.configure_utf8_stdio()  # no exception


if __name__ == "__main__":
    unittest.main()
