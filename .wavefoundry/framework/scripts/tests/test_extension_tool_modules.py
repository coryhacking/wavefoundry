"""Distribution-declared MCP tool extensions (wave 1yv9l, change 1yuc4).

Every case runs the real server in a scratch copy of the scripts tree, because
declared extension modules must sit directly in the scripts directory. One
subprocess per mode drives ``server.build_server`` / ``perform_mcp_reload`` /
``register_mcp_surface`` and reports observations as JSON; the assertions
below judge them.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]

_DRIVER = r'''
import asyncio, contextlib, hashlib, json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tests"))
from server_tools_support import _make_repo, load_server, load_thin_runner

SCRATCH = Path.cwd()
DECL = SCRATCH / "mcp_tool_extensions.py"
DECL_ORIG = DECL.read_text()
MODE = sys.argv[1]

ACME = """
import server_impl

def register(mcp, get_handler):
    @mcp.tool()
    def acme_echo(text: str = "", **kwargs):
        bad = server_impl._ensure_no_extra_args("acme_echo", kwargs)
        if bad is not None:
            return bad
        return {"status": "ok", "data": {"echo": text, "version": "v1"}}

    @mcp.tool()
    def acme_write(**kwargs):
        bad = server_impl._ensure_no_extra_args("acme_write", kwargs)
        if bad is not None:
            return bad
        return {"status": "ok", "data": {"wrote": True}}

    @mcp.tool()
    def wf_current_wave(**kwargs):
        bad = server_impl._ensure_no_extra_args("wf_current_wave", kwargs)
        if bad is not None:
            return bad
        return {"status": "ok", "data": {"overridden": "wf_current_wave"}}

    @mcp.tool()
    def wf_create_wave(slug: str, mode: str = "dry_run", **kwargs):
        bad = server_impl._ensure_no_extra_args("wf_create_wave", kwargs)
        if bad is not None:
            return bad
        probe = getattr(server_impl, "_WF_LOCK_PROBE", None) or {}
        return {"status": "ok", "data": {"overridden": "wf_create_wave", "slug": slug, "lock_held": probe.get("held")}}
"""

STRAY = """
def register(mcp, get_handler):
    @mcp.tool()
    def acme_stray(**kwargs):
        return {"status": "ok"}
"""

GOOD_DECL = """
EXTENSION_MODULES = ("acme_tools",)
EXTENSION_TOOL_PREFIXES = ("acme_",)
EXTENSION_TOOL_TIERS = {"acme_echo": "read", "acme_write": "write"}
EXTENSION_OVERRIDES = {"acme_tools": ("wf_current_wave", "wf_create_wave")}
"""

def write_module(name, src):
    (SCRATCH / f"{name}.py").write_text(src)

def table(mcp):
    return mcp._tool_manager._tools

def markers(mcp, name):
    return list(getattr(table(mcp)[name].fn, "__wf_middleware__", ()) or ())

def call(mcp, name, **kwargs):
    return table(mcp)[name].fn(**kwargs)

def ccall(mcp, name, args=None):
    """Call through FastMCP's real client path (argument model, is_async, run)."""
    result = asyncio.run(mcp.call_tool(name, args or {}))
    if isinstance(result, tuple):
        structured = result[1]
        if isinstance(structured, dict):
            return structured.get("result", structured)
        result = result[0]
    if isinstance(result, dict):
        return result
    return json.loads(result[0].text)

def install_lock_probe(impl):
    original = impl._lifecycle_mutation_lock
    state = {"held": False}

    @contextlib.contextmanager
    def probe(root):
        with original(root):
            state["held"] = True
            try:
                yield
            finally:
                state["held"] = False

    impl._lifecycle_mutation_lock = probe
    impl._WF_LOCK_PROBE = state

out = {}
with tempfile.TemporaryDirectory() as tmp:
    root = _make_repo(Path(tmp))
    if MODE == "stock":
        load_server(); runner = load_thin_runner()
        mcp = runner.build_server(root)
        impl = runner.server_impl
        out["markers"] = {n: markers(mcp, n) for n in ("wf_current_wave", "wf_create_wave")}
        out["extensions"] = impl.wf_server_info_response(root)["data"]["extensions"]
        out["tool_count"] = len(table(mcp))
        runner._get_handler().close()

    elif MODE == "ext":
        DECL.write_text(DECL_ORIG + GOOD_DECL)
        write_module("acme_tools", ACME)
        write_module("stray_tools", STRAY)
        root = _make_repo(SCRATCH.parent)  # scripts under the root: relative provenance
        load_server(); runner = load_thin_runner()
        mcp = runner.build_server(root)
        impl = runner.server_impl
        import mcp_tool_roster
        names = set(table(mcp))
        out["names"] = sorted(n for n in names if n.startswith("acme_"))
        out["override_read"] = call(mcp, "wf_current_wave")["data"]
        out["override_lifecycle"] = call(mcp, "wf_create_wave", slug="probe")["data"]
        bad = call(mcp, "wf_current_wave", bogus=1)
        out["override_unknown_arg"] = [d["code"] for d in bad.get("diagnostics", [])]
        out["markers"] = {n: markers(mcp, n) for n in ("wf_current_wave", "wf_create_wave", "acme_echo", "acme_write")}
        out["cost_wrapped"] = bool(getattr(table(mcp)["acme_echo"].fn, "_wf_cost_wrapped", False))
        install_lock_probe(impl)
        via = ccall(mcp, "wf_create_wave", {"slug": "probe"})
        out["call_tool_lifecycle"] = via["data"]
        out["call_tool_lock_released"] = impl._WF_LOCK_PROBE["held"] is False
        bad_via = ccall(mcp, "wf_current_wave", {"bogus": 1})
        out["call_tool_unknown_arg"] = [d["code"] for d in bad_via.get("diagnostics", [])]
        out["call_tool_echo"] = ccall(mcp, "acme_echo", {"text": "hi"})["data"]["echo"]
        reg = impl._TOOL_REGISTRY
        out["parity_defects"] = [d.name for d in reg.parity_defects]
        out["tiers"] = {n: reg.get(n).tier for n in ("acme_echo", "acme_write", "wf_current_wave", "wf_create_wave")}
        out["core_tiers"] = {n: mcp_tool_roster.TOOL_TIERS[n] for n in ("wf_current_wave", "wf_create_wave")}
        out["read_rules"] = [r for r in mcp_tool_roster.allow_rules(False) if "acme_" in r or r.endswith("wf_current_wave")]
        out["write_rules"] = [r for r in mcp_tool_roster.allow_rules(True) if "acme_" in r]
        out["write_ok"] = call(mcp, "acme_write")["status"]
        checkpoint = root / ".wavefoundry" / "upgrade-in-progress.json"
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text(json.dumps({"current_phase": "extracting"}))
        blocked = call(mcp, "acme_write")
        out["write_blocked"] = [blocked["status"]] + [d["code"] for d in blocked.get("diagnostics", [])]
        blocked_via = ccall(mcp, "acme_write")
        out["call_tool_write_blocked"] = [blocked_via["status"]] + [d["code"] for d in blocked_via.get("diagnostics", [])]
        out["echo_during_upgrade"] = call(mcp, "acme_echo", text="x")["status"]
        checkpoint.unlink()
        out["extensions"] = impl.wf_server_info_response(root)["data"]["extensions"]
        out["acme_sha"] = hashlib.sha256((SCRATCH / "acme_tools.py").read_bytes()).hexdigest()
        runner._get_handler().close()

    elif MODE == "reload":
        DECL.write_text(DECL_ORIG + GOOD_DECL)
        write_module("acme_tools", ACME)
        load_server(); runner = load_thin_runner()
        mcp = runner.build_server(root)
        before = runner.server_impl.wf_server_info_response(root)["data"]["extensions"]["modules"][0]["sha256"]
        write_module("acme_tools", ACME.replace('"version": "v1"', '"version": "v2"'))
        result = runner.perform_mcp_reload()
        out["reload_status"] = result["status"]
        out["echo_version"] = call(mcp, "acme_echo")["data"]["version"]
        after = runner.server_impl.wf_server_info_response(root)["data"]["extensions"]["modules"][0]["sha256"]
        out["sha_changed"] = before != after
        out["sha_matches_file"] = after == hashlib.sha256((SCRATCH / "acme_tools.py").read_bytes()).hexdigest()
        # A broken declaration on reload: only runner tools stay served.
        DECL.write_text(DECL_ORIG + GOOD_DECL + '\nEXTENSION_TOOL_TIERS = {"acme_echo": "read", "acme_write": "write", "acme_ghost": "read"}\n')
        failed = runner.perform_mcp_reload()
        out["failed_reload_codes"] = [d.get("code") for d in failed.get("diagnostics", []) + failed.get("data", {}).get("warnings", [])]
        out["failed_reload_text"] = json.dumps(failed)[:4000]
        out["served_after_failure"] = sorted(table(mcp))
        runner._get_handler().close()

    elif MODE == "startup_fail":
        DECL.write_text(DECL_ORIG + GOOD_DECL + '\nEXTENSION_TOOL_TIERS = {"acme_echo": "read", "acme_write": "write", "acme_ghost": "read"}\n')
        write_module("acme_tools", ACME)
        load_server(); runner = load_thin_runner()
        try:
            runner.build_server(root)
            out["raised"] = None
        except BaseException as exc:
            out["raised"] = type(exc).__name__
            out["message"] = str(exc)
        mcp = getattr(runner, "_mcp", None)
        out["served"] = sorted(table(mcp)) if mcp is not None else None

    elif MODE == "fail":
        from mcp.server.fastmcp import FastMCP
        load_server(); runner = load_thin_runner()
        runner.build_server(root)
        impl = runner.server_impl
        ext = sys.modules["mcp_tool_extensions"]
        write_module("acme_tools", ACME)
        write_module("no_register", "X = 1\n")
        write_module("raiser", "def register(mcp, get_handler):\n    raise ValueError('boom')\n")
        write_module("undeclared_override", "def register(mcp, get_handler):\n    @mcp.tool()\n    def wf_help(**kwargs):\n        return {}\n")
        write_module("bad_compat", (
            "def register(mcp, get_handler):\n"
            "    @mcp.tool()\n"
            "    def wf_current_wave():\n        return {}\n"
            "    @mcp.tool()\n"
            "    def wf_create_wave(mode: str = 'x', **kwargs):\n        return {}\n"
            "    @mcp.tool()\n"
            "    def wf_help(goal: str, **kwargs):\n        return {}\n"
        ))
        write_module("twin_a", "def register(mcp, get_handler):\n    @mcp.tool()\n    def acme_twin(**kwargs):\n        return {}\n")
        write_module("twin_b", "def register(mcp, get_handler):\n    @mcp.tool()\n    def acme_twin(**kwargs):\n        return {}\n")
        write_module("unprefixed", "def register(mcp, get_handler):\n    @mcp.tool()\n    def other_tool(**kwargs):\n        return {}\n")
        write_module("async_tools", "def register(mcp, get_handler):\n    @mcp.tool()\n    async def acme_async(**kwargs):\n        return {}\n")
        write_module("bypass_manager", "def register(mcp, get_handler):\n    def acme_hidden(**kwargs):\n        return {}\n    mcp._tool_manager.add_tool(acme_hidden, name='acme_hidden')\n")
        write_module("bypass_table", (
            "from mcp.server.fastmcp.tools import Tool\n"
            "def register(mcp, get_handler):\n"
            "    def fake(**kwargs):\n        return {}\n"
            "    mcp._tool_manager._tools['wf_help'] = Tool.from_function(fake, name='wf_help')\n"
        ))
        write_module("tamperer", "def register(mcp, get_handler):\n    mcp._tool_manager._tools.pop('acme_twin', None)\n")
        write_module("resource_tools", "def register(mcp, get_handler):\n    @mcp.resource('acme://thing')\n    def thing():\n        return 'x'\n")
        write_module("prompt_tools", "def register(mcp, get_handler):\n    @mcp.prompt()\n    def acme_prompt():\n        return 'x'\n")
        write_module("type_change", (
            "def register(mcp, get_handler):\n"
            "    @mcp.tool()\n"
            "    def wf_create_wave(slug: int, mode: str = 'dry_run', **kwargs):\n        return {}\n"
        ))
        write_module("default_change", (
            "import server_impl\n"
            "def register(mcp, get_handler):\n"
            "    @mcp.tool()\n"
            "    def wf_create_wave(slug: str, mode: str = 'create', **kwargs):\n"
            "        return {'status': 'ok', 'data': {'mode': mode}}\n"
        ))
        write_module("extended_tools", (
            "from typing import Annotated\n"
            "from pydantic import Field\n"
            "import server_impl\n"
            "def register(mcp, get_handler):\n"
            "    @mcp.tool()\n"
            "    def wf_create_wave(slug: Annotated[str, Field(title='Wave slug')], mode: str = 'dry_run', team: str = '', **kwargs):\n"
            "        bad = server_impl._ensure_no_extra_args('wf_create_wave', kwargs)\n"
            "        if bad is not None:\n"
            "            return bad\n"
            "        return {'status': 'ok', 'data': {'slug': slug, 'team': team}}\n"
        ))
        write_module("withdrawer", (
            "import server_impl\n"
            "def register(mcp, get_handler):\n"
            "    @mcp.tool()\n"
            "    def wf_current_wave(**kwargs):\n        return {}\n"
            "    mcp.remove_tool('wf_current_wave')\n"
        ))
        write_module("served_writer", (
            "import server_impl\n"
            "def register(mcp, get_handler):\n"
            "    def acme_sneak(**kwargs):\n        return {}\n"
            "    server_impl._MCP_INSTANCE.add_tool(acme_sneak, name='acme_sneak')\n"
        ))
        outside = Path(tmp) / "outside"
        outside.mkdir()
        (outside / "escaped.py").write_text("def register(mcp, get_handler):\n    pass\n")
        (SCRATCH / "escaped.py").symlink_to(outside / "escaped.py")

        cases = {
            "missing_module": dict(EXTENSION_MODULES=("not_there",)),
            "outside_scripts": dict(EXTENSION_MODULES=("escaped",)),
            "already_imported": dict(EXTENSION_MODULES=("record_paths",)),
            "stdlib_name": dict(EXTENSION_MODULES=("json",)),
            "reserved_name": dict(EXTENSION_MODULES=("server_impl",)),
            "no_register": dict(EXTENSION_MODULES=("no_register",)),
            "register_raises": dict(EXTENSION_MODULES=("raiser",)),
            "undeclared_override": dict(EXTENSION_MODULES=("undeclared_override",)),
            "runner_override": dict(EXTENSION_MODULES=("acme_tools",), EXTENSION_OVERRIDES={"acme_tools": ("wf_reload_mcp",)}),
            "unknown_override": dict(EXTENSION_MODULES=("acme_tools",), EXTENSION_OVERRIDES={"acme_tools": ("wf_not_a_tool",)}),
            "override_not_registered": dict(EXTENSION_MODULES=("unprefixed",),EXTENSION_TOOL_PREFIXES=("other_",), EXTENSION_TOOL_TIERS={"other_tool": "read"}, EXTENSION_OVERRIDES={"unprefixed": ("wf_help",)}),
            "override_two_modules": dict(EXTENSION_MODULES=("twin_a", "twin_b"), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_twin": "read"}, EXTENSION_OVERRIDES={"twin_a": ("wf_help",), "twin_b": ("wf_help",)}),
            "new_name_two_modules": dict(EXTENSION_MODULES=("twin_a", "twin_b"), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_twin": "read"}),
            "no_prefix_registered": dict(EXTENSION_MODULES=("unprefixed",), EXTENSION_TOOL_PREFIXES=("acme_",)),
            "no_tier_registered": dict(EXTENSION_MODULES=("twin_a",), EXTENSION_TOOL_PREFIXES=("acme_",)),
            "core_prefix_tier": dict(EXTENSION_MODULES=("twin_a",), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_twin": "read", "wf_extra": "read"}),
            "tier_unregistered": dict(EXTENSION_MODULES=("twin_a",), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_twin": "read", "acme_ghost": "read"}),
            "prefix_shorter_than_core": dict(EXTENSION_MODULES=("twin_a",), EXTENSION_TOOL_PREFIXES=("wf",), EXTENSION_TOOL_TIERS={"acme_twin": "read"}),
            "prefix_longer_than_core": dict(EXTENSION_MODULES=("twin_a",), EXTENSION_TOOL_PREFIXES=("wf_x_",), EXTENSION_TOOL_TIERS={"acme_twin": "read"}),
            "async_handler": dict(EXTENSION_MODULES=("async_tools",), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_async": "read"}),
            "unrecorded_manager_add": dict(EXTENSION_MODULES=("bypass_manager",), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_hidden": "read"}),
            "unrecorded_table_write": dict(EXTENSION_MODULES=("bypass_table",)),
            "tampered_staging": dict(EXTENSION_MODULES=("twin_a", "tamperer"), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_twin": "read"}),
            "resource_registered": dict(EXTENSION_MODULES=("resource_tools",)),
            "prompt_registered": dict(EXTENSION_MODULES=("prompt_tools",)),
            "type_changed_override": dict(EXTENSION_MODULES=("type_change",), EXTENSION_OVERRIDES={"type_change": ("wf_create_wave",)}),
            "extended_override": dict(EXTENSION_MODULES=("extended_tools",), EXTENSION_OVERRIDES={"extended_tools": ("wf_create_wave",)}),
            "default_changed_override": dict(EXTENSION_MODULES=("default_change",), EXTENSION_OVERRIDES={"default_change": ("wf_create_wave",)}),
            "withdrawn_override": dict(EXTENSION_MODULES=("withdrawer",), EXTENSION_OVERRIDES={"withdrawer": ("wf_current_wave",)}),
            "served_table_write": dict(EXTENSION_MODULES=("served_writer",), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_sneak": "read"}),
            "incompatible_override": dict(EXTENSION_MODULES=("bad_compat",), EXTENSION_OVERRIDES={"bad_compat": ("wf_current_wave", "wf_create_wave", "wf_help")}),
        }
        empty = dict(EXTENSION_MODULES=(), EXTENSION_TOOL_PREFIXES=(), EXTENSION_TOOL_TIERS={}, EXTENSION_OVERRIDES={})
        results = {}
        for label, attrs in cases.items():
            for key, value in {**empty, **attrs}.items():
                setattr(ext, key, value)
            for mod in ("acme_tools", "no_register", "raiser", "undeclared_override", "bad_compat", "twin_a", "twin_b", "unprefixed", "escaped", "not_there",
                        "async_tools", "bypass_manager", "bypass_table", "tamperer", "resource_tools", "prompt_tools",
                        "withdrawer", "served_writer", "type_change", "default_change", "extended_tools"):
                if getattr(sys.modules.get(mod), "__wf_extension__", False):
                    sys.modules.pop(mod, None)
            mcp = FastMCP("case")
            try:
                impl.register_mcp_surface(mcp, runner._get_handler)
                results[label] = {"raised": None, "served": len(table(mcp))}
                if label == "extended_override":
                    results[label]["with_team"] = ccall(mcp, "wf_create_wave", {"slug": "probe", "team": "blue"})["data"]
                    results[label]["core_call"] = ccall(mcp, "wf_create_wave", {"slug": "probe"})["data"]
            except BaseException as exc:
                results[label] = {"raised": type(exc).__name__, "message": str(exc), "served": sorted(table(mcp))}
        out["cases"] = results
        # The allowlist renderer refuses an invalid tier declaration.
        for key, value in {**empty, "EXTENSION_TOOL_PREFIXES": ("acme_",), "EXTENSION_TOOL_TIERS": {"wf_upgrade": "read"}}.items():
            setattr(ext, key, value)
        import mcp_tool_roster, render_platform_surfaces
        settings = root / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text("{}\n")
        try:
            mcp_tool_roster.allow_rules(False)
            out["roster_raised"] = None
        except Exception as exc:
            out["roster_raised"] = type(exc).__name__
        try:
            render_platform_surfaces.render_claude_permissions(root)
            out["renderer_raised"] = None
        except Exception as exc:
            out["renderer_raised"] = type(exc).__name__
        out["settings_after"] = settings.read_text()
        for key, value in empty.items():
            setattr(ext, key, value)
        runner._get_handler().close()

print(json.dumps(out))
'''


def _run(mode: str) -> dict:
    with tempfile.TemporaryDirectory() as temp:
        scratch = Path(temp) / "scripts"
        shutil.copytree(SCRIPTS, scratch, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        result = subprocess.run(
            [sys.executable, "-B", "-c", _DRIVER, mode],
            cwd=scratch,
            env=dict(os.environ, PYTHONPATH=str(scratch), PYTHONDONTWRITEBYTECODE="1"),
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            raise AssertionError(f"{mode} driver failed:\n{result.stderr[-6000:]}")
        return json.loads(result.stdout.strip().splitlines()[-1])


class StockSurfaceTests(unittest.TestCase):
    """AC-1: the shipped empty declaration changes nothing but adds an empty field."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run("stock")

    def test_empty_declaration_reports_empty_extensions(self):
        ext = self.out["extensions"]
        self.assertEqual(ext["modules"], [])
        self.assertEqual(ext["declaration"]["prefixes"], [])
        self.assertEqual(ext["declaration"]["tiers"], {})
        self.assertTrue(ext["declaration"]["sha256"])

    def test_declaration_module_ships_empty(self):
        import mcp_tool_extensions
        self.assertFalse(mcp_tool_extensions.declared())


class ExtensionServingTests(unittest.TestCase):
    """AC-2, AC-4, AC-7 through the real build_server path."""

    @classmethod
    def setUpClass(cls):
        cls.stock = _run("stock")
        cls.out = _run("ext")

    def test_new_tools_served_and_undeclared_module_ignored(self):
        self.assertEqual(self.out["names"], ["acme_echo", "acme_write"])

    def test_registry_and_allowlist_carry_declared_tiers(self):
        self.assertEqual(self.out["parity_defects"], [])
        self.assertEqual(self.out["tiers"]["acme_echo"], "read")
        self.assertEqual(self.out["tiers"]["acme_write"], "write")
        self.assertEqual(self.out["read_rules"], ["mcp__wavefoundry__acme_echo", "mcp__wavefoundry__wf_current_wave"])
        self.assertEqual(self.out["write_rules"], ["mcp__wavefoundry__acme_echo", "mcp__wavefoundry__acme_write"])

    def test_overrides_serve_under_core_names_with_core_tiers(self):
        self.assertEqual(self.out["override_read"], {"overridden": "wf_current_wave"})
        # The lock probe is installed later (see the real-client-path test).
        self.assertEqual(self.out["override_lifecycle"], {"overridden": "wf_create_wave", "slug": "probe", "lock_held": None})
        self.assertEqual(self.out["tiers"]["wf_current_wave"], self.out["core_tiers"]["wf_current_wave"])
        self.assertEqual(self.out["tiers"]["wf_create_wave"], self.out["core_tiers"]["wf_create_wave"])
        self.assertEqual(self.out["override_unknown_arg"], ["unknown_arguments"])

    def test_real_client_path_holds_the_lock_and_validates_arguments(self):
        # Through FastMCP call_tool: argument model, sync/async dispatch, run.
        self.assertEqual(self.out["call_tool_lifecycle"], {"overridden": "wf_create_wave", "slug": "probe", "lock_held": True})
        self.assertTrue(self.out["call_tool_lock_released"])
        self.assertEqual(self.out["call_tool_unknown_arg"], ["unknown_arguments"])
        self.assertEqual(self.out["call_tool_echo"], "hi")
        self.assertEqual(self.out["call_tool_write_blocked"], ["error", "upgrade_in_progress"])

    def test_overrides_inherit_exactly_the_core_wrappers(self):
        for name in ("wf_current_wave", "wf_create_wave"):
            self.assertEqual(self.out["markers"][name], self.stock["markers"][name], name)
        self.assertIn("lock", self.out["markers"]["wf_create_wave"])

    def test_new_tools_are_wrapped_costed_and_upgrade_guarded(self):
        self.assertIn("cost", self.out["markers"]["acme_echo"])
        self.assertTrue(self.out["cost_wrapped"])
        self.assertIn("guard", self.out["markers"]["acme_write"])
        self.assertNotIn("guard", self.out["markers"]["acme_echo"])
        self.assertEqual(self.out["write_ok"], "ok")
        self.assertEqual(self.out["write_blocked"], ["error", "upgrade_in_progress"])
        self.assertEqual(self.out["echo_during_upgrade"], "ok")

    def test_provenance_names_module_hash_tools_and_overrides(self):
        ext = self.out["extensions"]
        self.assertEqual(ext["declaration"]["prefixes"], ["acme_"])
        self.assertEqual(ext["declaration"]["tiers"], {"acme_echo": "read", "acme_write": "write"})
        (module,) = ext["modules"]
        self.assertEqual(module["module"], "acme_tools")
        self.assertEqual(module["path"], "scripts/acme_tools.py")
        self.assertEqual(ext["declaration"]["path"], "scripts/mcp_tool_extensions.py")
        self.assertEqual(module["sha256"], self.out["acme_sha"])
        self.assertEqual(module["tools"], [{"name": "acme_echo", "tier": "read"}, {"name": "acme_write", "tier": "write"}])
        self.assertEqual(module["overrides"], ["wf_create_wave", "wf_current_wave"])


class ExtensionReloadTests(unittest.TestCase):
    """AC-5 and the reload half of AC-3."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run("reload")

    def test_reload_serves_edited_extension_with_new_hash(self):
        self.assertEqual(self.out["reload_status"], "ok")
        self.assertEqual(self.out["echo_version"], "v2")
        self.assertTrue(self.out["sha_changed"])
        self.assertTrue(self.out["sha_matches_file"])

    def test_failed_reload_serves_only_runner_tools(self):
        self.assertIn("register_surface_failed", self.out["failed_reload_text"])
        self.assertEqual(self.out["served_after_failure"], ["wf_reload_mcp"])


class ExtensionStartupRefusalTests(unittest.TestCase):
    """AC-3 at startup: build_server refuses and serves nothing."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run("startup_fail")

    def test_build_server_refuses_and_serves_no_tool(self):
        self.assertEqual(self.out["raised"], "ExtensionLoadError")
        self.assertIn("has no registered tool", self.out["message"])
        self.assertEqual(self.out["served"], [])


class ExtensionRefusalTests(unittest.TestCase):
    """AC-3: every fail-closed case refuses and serves nothing."""

    EXPECTED = {
        "missing_module": "has no .py source",
        "outside_scripts": "outside",
        "already_imported": "already imported",
        "stdlib_name": "standard-library",
        "reserved_name": "framework or standard-library",
        "no_register": "defines no register",
        "register_raises": "raised during register",
        "undeclared_override": "without declaring an override",
        "runner_override": "may not override runner tool",
        "unknown_override": "which core does not register",
        "override_not_registered": "does not register it",
        "override_two_modules": "declared by both",
        "new_name_two_modules": "already staged",
        "no_prefix_registered": "without a declared extension prefix",
        "no_tier_registered": "without a declared tier",
        "core_prefix_tier": "uses a core prefix",
        "tier_unregistered": "has no registered tool",
        "prefix_shorter_than_core": "overlaps core prefix",
        "prefix_longer_than_core": "overlaps core prefix",
        "async_handler": "extension handlers must be synchronous",
        "unrecorded_manager_add": "outside FastMCP.add_tool",
        "unrecorded_table_write": "outside FastMCP.add_tool",
        "tampered_staging": "replaces or removes tools staged by another module",
        "resource_registered": "registers MCP resources",
        "prompt_registered": "registers MCP prompts",
        "type_changed_override": "changes the schema of parameters ['slug']",
        "withdrawn_override": "removes tools it registered",
        "served_table_write": "changes the served tool table directly",
    }

    @classmethod
    def setUpClass(cls):
        cls.out = _run("fail")

    def test_each_case_refuses_with_its_cause_and_serves_nothing(self):
        cases = self.out["cases"]
        for label, needle in self.EXPECTED.items():
            with self.subTest(case=label):
                result = cases[label]
                self.assertIsNotNone(result["raised"], result)
                self.assertIn(needle, result["message"])
                self.assertEqual(result["served"], [])

    def test_changed_default_alone_is_call_compatible(self):
        # A different default changes behavior, not the values callers may send.
        result = self.out["cases"]["default_changed_override"]
        self.assertIsNone(result["raised"], result)

    def test_added_optional_parameter_and_custom_title_stay_call_compatible(self):
        # Extra optional parameters extend the core signature; titles are annotations.
        result = self.out["cases"]["extended_override"]
        self.assertIsNone(result["raised"], result)
        self.assertEqual(result["with_team"], {"slug": "probe", "team": "blue"})
        self.assertEqual(result["core_call"], {"slug": "probe", "team": ""})

    def test_incompatible_overrides_are_refused(self):
        result = self.out["cases"]["incompatible_override"]
        self.assertIsNotNone(result["raised"], result)
        self.assertIn("'wf_current_wave' does not reject undeclared arguments", result["message"])
        self.assertIn("'wf_create_wave' drops parameters ['slug']", result["message"])
        self.assertIn("'wf_help' newly requires parameters ['goal']", result["message"])
        self.assertEqual(result["served"], [])

    def test_invalid_tier_declaration_stops_the_allowlist_renderer(self):
        self.assertEqual(self.out["roster_raised"], "ExtensionDeclarationError")
        self.assertEqual(self.out["renderer_raised"], "ExtensionDeclarationError")
        self.assertEqual(self.out["settings_after"], "{}\n")


class DeclarationValidationTests(unittest.TestCase):
    """Pure helper coverage for the stdlib declaration module."""

    def setUp(self):
        import mcp_tool_extensions
        self.ext = mcp_tool_extensions
        self.saved = {k: getattr(mcp_tool_extensions, k) for k in (
            "EXTENSION_MODULES", "EXTENSION_TOOL_PREFIXES", "EXTENSION_TOOL_TIERS", "EXTENSION_OVERRIDES")}

    def tearDown(self):
        for key, value in self.saved.items():
            setattr(self.ext, key, value)

    def test_core_prefixes_are_the_server_prefix_contract(self):
        from server_tools_support import load_server
        impl = load_server()
        # load_server purges and re-imports the declaration module; compare
        # against the object the server itself imported.
        self.assertIs(impl.MCP_TOOL_PREFIXES, impl.mcp_tool_extensions.CORE_TOOL_PREFIXES)

    def test_valid_declaration_has_no_problems(self):
        self.ext.EXTENSION_MODULES = ("acme_tools",)
        self.ext.EXTENSION_TOOL_PREFIXES = ("acme_",)
        self.ext.EXTENSION_TOOL_TIERS = {"acme_echo": "read"}
        self.ext.EXTENSION_OVERRIDES = {"acme_tools": ("wf_help",)}
        self.assertEqual(self.ext.declaration_problems(core_tools={"wf_help"}, runner_tools={"wf_reload_mcp"}), [])

    def test_bad_tier_value_and_undeclared_override_module(self):
        self.ext.EXTENSION_MODULES = ("acme_tools",)
        self.ext.EXTENSION_TOOL_PREFIXES = ("acme_",)
        self.ext.EXTENSION_TOOL_TIERS = {"acme_echo": "admin"}
        self.ext.EXTENSION_OVERRIDES = {"other": ("wf_help",)}
        problems = " ".join(self.ext.declaration_problems(core_tools={"wf_help"}, runner_tools=set()))
        self.assertIn("declares tier 'admin'", problems)
        self.assertIn("undeclared module 'other'", problems)


if __name__ == "__main__":
    unittest.main()
