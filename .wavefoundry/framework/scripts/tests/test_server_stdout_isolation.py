"""Wave 1p8vp: the startup fd-1 isolation that protects the MCP JSON-RPC channel from native
onnxruntime/DirectML/CUDA writes to fd 1 (which `redirect_stdout` cannot catch and a per-call
`os.dup2` cannot safely do against the background prewarm thread).

The tests drive `_isolate_native_stdout_from_protocol` over a CONTROLLED fd (never the runner's real
fd 1) — the function operates on `sys.stdout.fileno()`, so pointing sys.stdout at a temp-file-backed
fd exercises the exact logic without risking the test harness's own stdout.
"""
from __future__ import annotations

import importlib.util
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = SCRIPTS_ROOT / "server.py"


def _load_server_module():
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    spec = importlib.util.spec_from_file_location("server_under_test_stdout_iso", SERVER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class IsolateNativeStdoutTests(unittest.TestCase):
    def setUp(self):
        self.mod = _load_server_module()

    def test_protocol_writes_reach_private_dup_native_writes_dropped(self):
        # AC-1/AC-2: after isolation, writes via sys.stdout.buffer (what the mcp transport uses)
        # reach the PRIVATE dup of the original target, while a raw os.write to the (now-devnull) fd
        # is dropped. Driven over a controlled fd so the real fd 1 is never touched.
        saved_stdout = sys.stdout
        saved_stderr = sys.stderr
        tf = tempfile.TemporaryFile()
        ctrl_fd = os.dup(tf.fileno())  # controlled fd -> temp file (stands in for the host pipe)
        data = b""
        try:
            sys.stdout = io.TextIOWrapper(
                io.BufferedWriter(io.FileIO(ctrl_fd, "w", closefd=False)),
                encoding="utf-8", newline="\n", write_through=True,
            )
            self.mod._isolate_native_stdout_from_protocol()
            sys.stdout.buffer.write(b"PROTOCOL\n")   # mcp-style protocol write
            sys.stdout.buffer.flush()
            os.write(ctrl_fd, b"NATIVE\n")            # native-lib write -> ctrl_fd is now devnull
            self.assertIs(sys.stderr, saved_stderr, "stderr must be untouched")
            tf.flush()
            tf.seek(0)
            data = tf.read()
        finally:
            cur = sys.stdout
            sys.stdout = saved_stdout
            try:
                if cur is not saved_stdout:
                    cur.close()
            except Exception:
                pass
            try:
                os.close(ctrl_fd)
            except Exception:
                pass
            tf.close()
        self.assertIn(b"PROTOCOL", data, "protocol writes must reach the private dup (host pipe)")
        self.assertNotIn(b"NATIVE", data, "native fd writes must be dropped to devnull")

    def test_fail_safe_no_real_fileno_leaves_stdout_intact(self):
        # AC-3: when sys.stdout has no real fileno, the function is a safe no-op (no raise, unchanged).
        saved = sys.stdout

        class _NoFileno:
            def fileno(self):
                raise io.UnsupportedOperation("no fileno")

        sentinel = _NoFileno()
        sys.stdout = sentinel
        try:
            self.mod._isolate_native_stdout_from_protocol()  # must not raise
            self.assertIs(sys.stdout, sentinel, "stdout must be left intact on the no-fileno path")
        finally:
            sys.stdout = saved

    def test_isolation_runs_on_stdio_path_before_mcp_run(self):
        # AC-4: main() calls the isolation after _configure_stdio and before mcp.run (the transport
        # path); the dry-run branch returns earlier so it is never run for --dry-run.
        src = SERVER_PATH.read_text(encoding="utf-8")
        i_cfg = src.index("_configure_stdio_for_mcp_transport()\n    # wave 1p8vp")
        i_iso = src.index("_isolate_native_stdout_from_protocol()", i_cfg)
        i_run = src.index('mcp.run(transport="stdio")', i_iso)
        self.assertLess(i_cfg, i_iso)
        self.assertLess(i_iso, i_run, "isolation must run before mcp.run")


if __name__ == "__main__":
    unittest.main()
