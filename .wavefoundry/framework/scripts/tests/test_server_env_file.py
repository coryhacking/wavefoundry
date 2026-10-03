"""Change 1zltt: MCP startup never reads a ``.env`` for FastMCP settings.

mcp 1.x builds ``mcp.server.fastmcp.server.Settings`` (pydantic-settings,
``env_file=".env"`` relative to the process working directory) inside
``FastMCP.__init__``. A ``.env`` the server cannot read or decode crashed
startup. The subprocess cases run ``build_server`` with the working directory
holding the ``.env`` under test, so the module-level class mutation never
reaches this test process.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

_HAS_MCP = importlib.util.find_spec("mcp") is not None

_DRIVER = r"""
import json, sys
from pathlib import Path
scripts, root = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(scripts))
import server
mcp = server.build_server(root)
tools = sorted(mcp._tool_manager._tools)
print(json.dumps({"tool_count": len(tools), "has_reload": "wf_reload_mcp" in tools,
                  "settings": mcp.settings.model_dump(mode="json")}, default=str))
"""


def _run_build(workdir: Path, root: Path) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith("FASTMCP_") and k != "PYTHONPATH"}
    return subprocess.run(
        [sys.executable, "-B", "-c", _DRIVER, str(SCRIPTS), str(root)],
        cwd=str(workdir), env=env, capture_output=True, text=True, timeout=300,
    )


def _make_root(base: Path) -> Path:
    root = base / "repo"
    (root / "docs").mkdir(parents=True)
    return root


def _deny_read(path: Path) -> bool:
    """Make ``path`` unreadable to this process; False when that cannot be done."""
    if os.name == "nt":
        user = os.environ.get("USERNAME")
        if not user or shutil.which("icacls") is None:
            return False
        result = subprocess.run(["icacls", str(path), "/deny", f"{user}:(R)"], capture_output=True, text=True)
        if result.returncode != 0:
            return False
    else:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            return False
        path.chmod(0)
    try:
        path.read_bytes()
    except OSError:
        return True
    return False


def _allow_read(path: Path) -> None:
    if os.name == "nt":
        user = os.environ.get("USERNAME")
        if user:
            subprocess.run(["icacls", str(path), "/remove:d", user], capture_output=True, text=True)
    else:
        try:
            path.chmod(0o600)
        except OSError:
            pass


@unittest.skipUnless(_HAS_MCP, "mcp is not importable in this interpreter")
class StartupEnvFileTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.workdir = self.base / "cwd"
        self.workdir.mkdir()
        self.root = _make_root(self.base)
        self.env_file = self.workdir / ".env"

    def tearDown(self):
        if self.env_file.exists():
            _allow_read(self.env_file)
        self._tmp.cleanup()

    def _built(self) -> dict:
        result = _run_build(self.workdir, self.root)
        self.assertEqual(result.returncode, 0, result.stderr[-4000:])
        return json.loads(result.stdout.strip().splitlines()[-1])

    def test_ac1_unreadable_env_file_does_not_stop_startup(self):
        self.env_file.write_text("FASTMCP_DEBUG=true\n", encoding="utf-8")
        if not _deny_read(self.env_file):
            self.skipTest("cannot make .env unreadable to this process (root, or no ACL support)")
        out = self._built()
        self.assertTrue(out["has_reload"])
        self.assertGreater(out["tool_count"], 10)

    def test_ac2_undecodable_env_file_does_not_stop_startup(self):
        self.env_file.write_bytes(b"FASTMCP_DEBUG=\xff\xfe\xfa\n")
        out = self._built()
        self.assertTrue(out["has_reload"])

    def test_ac3_fastmcp_keys_in_env_file_do_not_change_settings(self):
        baseline = self._built()["settings"]
        self.env_file.write_text(
            "FASTMCP_LOG_LEVEL=DEBUG\nFASTMCP_DEBUG=true\nFASTMCP_PORT=9999\n"
            "FASTMCP_WARN_ON_DUPLICATE_TOOLS=false\n",
            encoding="utf-8",
        )
        with_env = self._built()["settings"]
        self.assertEqual(with_env, baseline)
        self.assertNotEqual(with_env.get("port"), 9999)
        self.assertNotEqual(with_env.get("log_level"), "DEBUG")


@unittest.skipUnless(_HAS_MCP, "mcp is not importable in this interpreter")
class DisableDotenvHelperTests(unittest.TestCase):
    """AC-4: the helper clears ``env_file`` and tolerates other mcp 1.x shapes."""

    def setUp(self):
        import server
        from mcp.server.fastmcp import server as fastmcp_server

        self.server = server
        self.fastmcp_server = fastmcp_server

    def test_helper_sets_env_file_to_none(self):
        settings_cls = self.fastmcp_server.Settings
        with mock.patch.dict(settings_cls.model_config, {"env_file": ".env"}):
            self.server._disable_fastmcp_dotenv()
            self.assertIsNone(settings_cls.model_config["env_file"])
            self.server._disable_fastmcp_dotenv()  # idempotent
            self.assertIsNone(settings_cls.model_config["env_file"])

    def test_helper_is_a_no_op_without_the_env_file_key(self):
        settings_cls = self.fastmcp_server.Settings
        with mock.patch.dict(settings_cls.model_config, {}, clear=False):
            settings_cls.model_config.pop("env_file", None)
            self.server._disable_fastmcp_dotenv()
            self.assertNotIn("env_file", settings_cls.model_config)

    def test_helper_is_a_no_op_without_the_settings_attribute(self):
        sentinel = object()
        with mock.patch.object(self.fastmcp_server, "Settings", sentinel):
            del self.fastmcp_server.Settings
            try:
                self.server._disable_fastmcp_dotenv()
            finally:
                self.fastmcp_server.Settings = sentinel

    def test_build_server_still_builds_without_the_settings_attribute(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(Path(tmp))
            settings_cls = self.fastmcp_server.Settings
            with mock.patch.dict(settings_cls.model_config, {"env_file": ".env"}), \
                    mock.patch.object(self.server, "_fastmcp_settings_class", return_value=None):
                mcp = self.server.build_server(root)
            self.assertIn("wf_reload_mcp", mcp._tool_manager._tools)


if __name__ == "__main__":
    unittest.main()
