"""Wave 1p9i7: server.py fail-fast guards for missing/broken tool venv.

Each test drives server.py in a subprocess so that sys.exit(2) from the guards
does not terminate the test runner process.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]


def _run_server_import(extra_setup: str = "") -> subprocess.CompletedProcess:
    """Execute `import server` in a subprocess with optional setup code injected first."""
    code = textwrap.dedent(f"""
        import sys
        sys.path.insert(0, {str(SCRIPTS_ROOT)!r})
        import venv_bootstrap
        from pathlib import Path
        {extra_setup}
        import server
    """)
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


# Use a path under tempdir that is guaranteed not to exist on any platform.
_MISSING_VENV_PATCH = (
    "import tempfile; "
    "venv_bootstrap.tool_venv_python = "
    "lambda: Path(tempfile.gettempdir()) / '__wf_test_no_such_venv' / 'python3'"
)


class MissingVenvGuardTests(unittest.TestCase):
    """AC-1 + AC-3: venv Python does not exist."""

    def test_exits_2(self):
        result = _run_server_import(_MISSING_VENV_PATCH)
        self.assertEqual(result.returncode, 2, f"stderr={result.stderr!r}")

    def test_stderr_mentions_wf_setup(self):
        result = _run_server_import(_MISSING_VENV_PATCH)
        self.assertIn("wf setup", result.stderr)

    def test_stdout_is_clean(self):
        result = _run_server_import(_MISSING_VENV_PATCH)
        self.assertNotIn("wf setup", result.stdout)


class BrokenVenvImportGuardTests(unittest.TestCase):
    """AC-2 + AC-3: venv exists but server_impl raises ImportError."""

    def _run_with_fake_server_impl(self, tmpdir: str) -> subprocess.CompletedProcess:
        code = textwrap.dedent(f"""
            import sys
            sys.path.insert(0, {str(SCRIPTS_ROOT)!r})
            # Prepend tmpdir so our stub shadows the real server_impl.
            sys.path.insert(0, {tmpdir!r})
            import venv_bootstrap
            from pathlib import Path
            import server
        """)
        return subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def test_exits_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "server_impl.py").write_text(
                'raise ImportError("test: forced import failure")\n'
            )
            result = self._run_with_fake_server_impl(tmpdir)
        self.assertEqual(result.returncode, 2, f"stderr={result.stderr!r}")

    def test_stderr_mentions_wf_setup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "server_impl.py").write_text(
                'raise ImportError("test: forced import failure")\n'
            )
            result = self._run_with_fake_server_impl(tmpdir)
        self.assertIn("wf setup", result.stderr)

    def test_stdout_is_clean(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "server_impl.py").write_text(
                'raise ImportError("test: forced import failure")\n'
            )
            result = self._run_with_fake_server_impl(tmpdir)
        self.assertNotIn("wf setup", result.stdout)


if __name__ == "__main__":
    unittest.main()
