"""Tests for the shared CLI UTF-8 stdio reconfigure (wave 1p8gv).

The field defect: a native-Windows upgrade crashed with UnicodeEncodeError the first time it
``print("⚠")`` on a cp1252 console. We simulate a cp1252-backed stdout and assert that printing
non-ASCII raises BEFORE the reconfigure and does NOT raise AFTER it.
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
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


class IsolatedStdoutFdTests(unittest.TestCase):
    """Wave 1p8vc: the fd-level stdout isolation that protects the MCP JSON-RPC channel from native
    C-extension writes to fd 1 (which `contextlib.redirect_stdout` cannot intercept)."""

    def test_diverts_native_fd1_writes_and_restores(self):
        # AC-1: a raw os.write(1, ...) INSIDE the block must NOT reach the original fd-1 target
        # (it goes to devnull); after the block fd 1 is restored so later writes DO reach it.
        with tempfile.TemporaryFile() as tf:
            saved_out = os.dup(1)
            try:
                os.dup2(tf.fileno(), 1)  # stand in for the MCP stdout pipe on the real fd 1
                with cli_stdio.isolated_stdout_fd():
                    os.write(1, b"NATIVE_INSIDE")  # native fd-1 write — must be diverted away
                os.write(1, b"AFTER_RESTORE")       # fd 1 restored — must reach the pipe
            finally:
                os.dup2(saved_out, 1)
                os.close(saved_out)
            tf.seek(0)
            data = tf.read()
        self.assertNotIn(b"NATIVE_INSIDE", data, "native fd-1 write must be diverted inside the block")
        self.assertIn(b"AFTER_RESTORE", data, "fd 1 must be restored after the block")

    def test_noop_without_real_fileno(self):
        # AC-2: when sys.stdout has no real fileno (e.g. a captured StringIO), the CM is a safe no-op
        # and never raises — Python-level writes still land in the captured stream.
        saved = sys.stdout
        sys.stdout = io.StringIO()
        try:
            with cli_stdio.isolated_stdout_fd():
                print("hello-under-capture")
            captured = sys.stdout.getvalue()
        finally:
            sys.stdout = saved
        self.assertIn("hello-under-capture", captured)

    def test_does_not_leak_file_descriptors(self):
        # The save/devnull fds must be closed in finally — repeated use must not exhaust fds.
        with tempfile.TemporaryFile() as tf:
            saved_out = os.dup(1)
            try:
                os.dup2(tf.fileno(), 1)
                before = os.dup(1); os.close(before)  # next free fd number as a baseline
                for _ in range(50):
                    with cli_stdio.isolated_stdout_fd():
                        os.write(1, b"x")
                after = os.dup(1); os.close(after)
            finally:
                os.dup2(saved_out, 1)
                os.close(saved_out)
        self.assertEqual(before, after, "isolated_stdout_fd must not leak file descriptors")


if __name__ == "__main__":
    unittest.main()
