"""Wave 1z1vt (1yxnc): the post-upgrade reload reaches the serving runner.

In production ``server.py`` runs as ``__main__``. The post-upgrade reload used
to ``import server``, which executed ``server.py`` a second time as a module
with no handler, so the reload reported ``handler_not_ready`` and the upgraded
code was not served.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import wf_server.upgrade_handlers as upgrade_handlers


def _runner(name: str, *, built: bool) -> types.ModuleType:
    module = types.ModuleType(name)
    module.perform_mcp_reload = lambda **_: {"status": "ok", "data": {"ok": True}}
    module._mcp = object() if built else None
    return module


class LiveRunnerLookupTests(unittest.TestCase):
    def _lookup(self, modules: dict):
        with patch.dict(sys.modules, modules):
            return upgrade_handlers._live_runner()

    def test_a_built_main_runner_is_found_beside_an_unbuilt_server_module(self):
        # dashboard_lib imports ``server``, which can leave an unbuilt copy loaded.
        main = _runner("__main__", built=True)
        self.assertIs(self._lookup({"server": _runner("server", built=False), "__main__": main}), main)

    def test_a_built_server_module_is_preferred(self):
        server = _runner("server", built=True)
        self.assertIs(self._lookup({"server": server, "__main__": _runner("__main__", built=True)}), server)

    def test_forwarded_attributes_are_not_a_runner(self):
        # server.py's module __getattr__ re-exports server_impl; only the module's
        # own namespace counts.
        forwarding = types.ModuleType("__main__")
        forwarding.__getattr__ = lambda name: (lambda **_: {}) if name == "perform_mcp_reload" else object()
        self.assertIsNone(self._lookup({"server": _runner("server", built=False), "__main__": forwarding}))

    def test_no_runner_reports_a_skip_naming_wf_reload_mcp(self):
        resp = {"status": "ok", "data": {}}
        with patch.object(upgrade_handlers, "_live_runner", return_value=None):
            upgrade_handlers._reload_live_runner(resp)
        self.assertNotIn("mcp_reload", resp["data"])
        (diag,) = resp["diagnostics"]
        self.assertEqual(diag["code"], "mcp_reload_skipped")
        self.assertIn("wf_reload_mcp", diag["message"])


_PRODUCTION_SHAPE = r'''
import json, sys, tempfile, types
from pathlib import Path
scripts = Path(sys.argv[1])
sys.path.insert(0, str(scripts)); sys.path.insert(0, str(scripts / "tests"))
from server_tools_support import _make_repo
# The production launch shape: server.py's code lives in the __main__ module and
# nothing registers sys.modules["server"].
runner = types.ModuleType("__wf_runner__")
runner.__file__ = str(scripts / "server.py")
sys.modules["__main__"] = runner
exec(compile((scripts / "server.py").read_text(encoding="utf-8"), str(scripts / "server.py"), "exec"),
     runner.__dict__)
import wf_server.upgrade_handlers as handlers
with tempfile.TemporaryDirectory() as tmp:
    root = _make_repo(Path(tmp))
    runner.build_server(root)
    old_handler = runner._get_handler()
    resp = {"status": "ok", "data": {}}
    handlers._reload_live_runner(resp)
    new_handler = runner._get_handler()
    print(json.dumps({
        "reloaded": "mcp_reload" in resp["data"],
        "codes": [d.get("code") for d in resp.get("diagnostics", [])],
        "fresh_handler": new_handler is not old_handler,
        "second_server_module": "server" in sys.modules,
    }))
    new_handler.close()
'''


class ProductionLaunchShapeTests(unittest.TestCase):
    def test_the_reload_reaches_the_main_runner_without_a_second_server_module(self):
        try:
            import mcp  # noqa: F401
        except ImportError:
            self.skipTest("the mcp package is not installed")
        result = subprocess.run(
            [sys.executable, "-B", "-c", _PRODUCTION_SHAPE, str(SCRIPTS)],
            capture_output=True, text=True, timeout=300,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(result.returncode, 0, result.stderr[-4000:])
        observed = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(observed, {"reloaded": True, "codes": [], "fresh_handler": True,
                                    "second_server_module": False}, result.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
