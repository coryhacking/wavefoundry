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
from framework_files import framework_source_files  # wf_server-aware source locations (wave 1yzd0)

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

# Wave 1z8oz fixtures.
ALIAS_DECL = """
EXTENSION_TOOL_PREFIXES = ("fork_",)
EXTENSION_TOOL_ALIASES = {
    "fork_close_container": "wf_close_wave",
    "fork_add_change": "wf_add_change",
    "fork_current": "wf_current_wave",
    "fork_current_again": "wf_current_wave",
}
EXTENSION_HIDDEN_TOOLS = ("wf_current_wave",)
"""

REPLACE_DECL = """
EXTENSION_MODULES = ("fork_tools",)
EXTENSION_TOOL_PREFIXES = ("fork_",)
EXTENSION_REPLACEMENTS = {"fork_tools": {
    "wf_close_wave": {"alias_for_core": "fork_close_container"},
    "wf_review_event": {"alias_for_core": "fork_review_event_core"},
    "wf_help": {"alias_for_core": "fork_help_core", "tier": "write"},
    "memory_validate": {"alias_for_core": "fork_memory_validate_core", "tier": "write"},
    "wf_current_wave": {"alias_for_core": "fork_current_core"},
}}
"""

FORK = """
import server_impl

def register(mcp, get_handler):
    @mcp.tool()
    def wf_close_wave(item: str, **kwargs):
        bad = server_impl._ensure_no_extra_args("wf_close_wave", kwargs)
        if bad is not None:
            return bad
        return {"status": "ok", "data": {"closed_item": item},
                "next_tools": ["wf_close_wave"], "usage": "wf_close_wave(item=...)"}

    @mcp.tool()
    def wf_review_event(note: str, **kwargs):
        bad = server_impl._ensure_no_extra_args("wf_review_event", kwargs)
        if bad is not None:
            return bad
        return {"status": "ok", "data": {"note": note}}

    @mcp.tool()
    def wf_help(topic: str = "", **kwargs):
        bad = server_impl._ensure_no_extra_args("wf_help", kwargs)
        if bad is not None:
            return bad
        return {"status": "ok", "data": {"fork_help": topic}}

    @mcp.tool()
    def memory_validate(record: str = "", **kwargs):
        bad = server_impl._ensure_no_extra_args("memory_validate", kwargs)
        if bad is not None:
            return bad
        return {"status": "ok", "data": {"fork_validate": record}}

    @mcp.tool()
    def wf_current_wave(scope: str = "", **kwargs):
        bad = server_impl._ensure_no_extra_args("wf_current_wave", kwargs)
        if bad is not None:
            return bad
        return {"status": "ok", "data": {"fork_scope": scope}}
"""

MEMORY_VALIDATE_ARGS = {
    "memory_id": "mem-x", "verdict": "promote", "action_delta": "a", "rationale": "r",
    "evidence_verified": True, "current_target_verified": True, "canonical_overlap": "none",
}

@contextlib.contextmanager
def busy_lock(impl):
    """Make every lifecycle-lock acquisition report another holder."""
    original = impl._lifecycle_mutation_lock

    @contextlib.contextmanager
    def held(root):
        raise impl.LifecycleMutationBusy("fixture holds the lifecycle lock")
        yield

    impl._lifecycle_mutation_lock = held
    try:
        yield
    finally:
        impl._lifecycle_mutation_lock = original

def codes(result):
    return [result["status"]] + [d["code"] for d in result.get("diagnostics", [])]

def hints(result):
    diagnostics = result.get("diagnostics", [])
    return {
        "codes": codes(result),
        "busy": (result.get("data") or {}).get("busy"),
        "next_tools": result.get("next_tools"),
        "usage": result.get("usage"),
        "recovery_tools": [d.get("recovery_tools") for d in diagnostics],
        "recovery_usage": [d.get("recovery_usage") for d in diagnostics],
    }

def observe_surface(impl, mcp, roster):
    reg = impl._TOOL_REGISTRY
    tiers = roster.all_tool_tiers()
    runner_tools = set(roster.RUNNER_TOOLS)
    rule_names = lambda write: sorted(r.rsplit("__", 1)[-1] for r in roster.allow_rules(write))
    watched = ("wf_help", "wf_current_wave", "wf_close_wave", "wf_add_change", "memory_validate")
    return {
        "parity_defects": [d.name for d in reg.parity_defects],
        "registry_vs_tiers": sorted({s.name for s in reg.tools()} ^ (set(tiers) - runner_tools)),
        "tier_mismatches": sorted(s.name for s in reg.tools() if s.tier != tiers.get(s.name)),
        "served_vs_tiers": sorted(set(table(mcp)) ^ set(tiers)),
        "tiers": {n: tiers.get(n) for n in sorted(set(tiers) | set(watched)) if n.startswith("fork_") or n in watched},
        "read_rules": [n for n in rule_names(False) if n.startswith("fork_") or n in watched],
        "write_rules": [n for n in rule_names(True) if n.startswith("fork_") or n in watched],
    }

out = {}
with tempfile.TemporaryDirectory() as tmp:
    root = _make_repo(Path(tmp))
    if MODE == "stock":
        load_server(); runner = load_thin_runner()
        mcp = runner.build_server(root)
        impl = runner.server_impl
        out["markers"] = {n: markers(mcp, n) for n in (
            "wf_current_wave", "wf_create_wave", "wf_close_wave", "wf_review_event", "wf_help", "memory_validate")}
        out["extensions"] = impl.wf_server_info_response(root)["data"]["extensions"]
        out["tool_count"] = len(table(mcp))
        runner._get_handler().close()

    elif MODE == "alias":
        # Wave 1z8oz: an aliases-only declaration (no module) with a hidden name.
        DECL.write_text(DECL_ORIG + ALIAS_DECL)
        load_server(); runner = load_thin_runner()
        mcp = runner.build_server(root)
        impl = runner.server_impl
        import mcp_tool_roster
        from unittest import mock
        out.update(observe_surface(impl, mcp, mcp_tool_roster))
        out["alias_shares_fn"] = table(mcp)["fork_close_container"].fn is table(mcp)["wf_close_wave"].fn
        out["markers"] = {n: markers(mcp, n) for n in ("fork_close_container", "wf_close_wave", "fork_add_change", "fork_current")}
        listed = [t.name for t in asyncio.run(mcp.list_tools())]
        out["listed_hidden"] = "wf_current_wave" in listed
        out["listed_alias"] = "fork_current" in listed
        try:
            ccall(mcp, "wf_current_wave")
            out["hidden_call"] = "served"
        except Exception as exc:
            out["hidden_call"] = type(exc).__name__ + ": " + str(exc)
        out["alias_call"] = ccall(mcp, "fork_current")["status"]
        handler = runner._get_handler()
        costs = []
        with mock.patch.object(handler.telemetry, "record_tool_cost", lambda name, **kw: costs.append(name)):
            ccall(mcp, "fork_current")
            out["cost_after_costed_alias"] = list(costs)
            out["exempt_alias_call"] = codes(ccall(mcp, "fork_close_container", {"wave_id": "1abcd", "mode": "dry_run"}))
            out["cost_after_exempt_alias"] = list(costs)
        with busy_lock(impl):
            busy = ccall(mcp, "fork_close_container", {"wave_id": "1abcd", "mode": "dry_run"})
        out["busy"] = hints(busy)
        checkpoint = root / ".wavefoundry" / "upgrade-in-progress.json"
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text(json.dumps({"current_phase": "extracting"}))
        guarded = ccall(mcp, "fork_add_change", {"wave_id": "1abcd", "change_id": "1abce-feat x"})
        checkpoint.unlink()
        out["guarded"] = [guarded["status"]] + [d["code"] for d in guarded.get("diagnostics", [])]
        out["extensions"] = impl.wf_server_info_response(root)["data"]["extensions"]
        # Reload rebuilds the served names, then fails closed on a bad declaration.
        result = runner.perform_mcp_reload()
        out["reload_status"] = result["status"]
        out["reload_names"] = sorted(n for n in table(mcp) if n.startswith("fork_"))
        out["reload_hidden"] = "wf_current_wave" in table(mcp)
        out["reload_shares_fn"] = table(mcp)["fork_close_container"].fn is table(mcp)["wf_close_wave"].fn
        DECL.write_text(DECL_ORIG + ALIAS_DECL + '\nEXTENSION_TOOL_ALIASES = {"fork_ghost": "wf_not_a_tool"}\n')
        failed = runner.perform_mcp_reload()
        out["failed_reload_text"] = json.dumps(failed)[:4000]
        out["served_after_failure"] = sorted(table(mcp))
        handler.close()

    elif MODE == "replace":
        DECL.write_text(DECL_ORIG + REPLACE_DECL)
        write_module("fork_tools", FORK)
        load_server(); runner = load_thin_runner()
        mcp = runner.build_server(root)
        impl = runner.server_impl
        import mcp_tool_roster
        from unittest import mock
        out.update(observe_surface(impl, mcp, mcp_tool_roster))
        out["markers"] = {n: markers(mcp, n) for n in (
            "wf_close_wave", "fork_close_container", "wf_review_event", "fork_review_event_core",
            "wf_help", "fork_help_core", "memory_validate", "fork_memory_validate_core",
            "wf_current_wave", "fork_current_core")}
        out["replaced_call"] = ccall(mcp, "wf_close_wave", {"item": "task-7"})
        with busy_lock(impl):
            out["replaced_busy"] = hints(ccall(mcp, "wf_close_wave", {"item": "task-7"}))
            out["core_busy"] = hints(ccall(mcp, "fork_close_container", {"wave_id": "1abcd", "mode": "dry_run"}))
            # A core tool that is not replaced names a replaced core name in its hints.
            out["other_core_busy"] = hints(ccall(mcp, "wf_add_change", {"wave_id": "1abcd", "change_id": "1abce-feat x"}))
        handler = runner._get_handler()
        exempt_costs = []
        with mock.patch.object(handler.telemetry, "record_tool_cost", lambda name, **kw: exempt_costs.append(name)):
            ccall(mcp, "wf_close_wave", {"item": "task-8"})
        out["cost_after_exempt_replacement"] = exempt_costs
        extractor_calls, costs = [], []
        spy = lambda root_, result: (extractor_calls.append(1), ([], None))[1]
        with mock.patch.dict(impl._ARTIFACT_EXTRACTORS, {"wf_review_event": spy}), \
                mock.patch.object(handler.telemetry, "record_tool_cost", lambda name, **kw: costs.append([name, kw.get("derived_artifact_tokens")])):
            out["replaced_review"] = ccall(mcp, "wf_review_event", {"note": "n"})["data"]
            out["extractor_after_replaced"] = len(extractor_calls)
            out["cost_after_replaced"] = list(costs)
            ccall(mcp, "fork_review_event_core", {"wave_id": "1abcd", "event": "run", "actor": "qa-reviewer", "context_id": "c1", "mode": "dry_run"})
            out["extractor_after_core"] = len(extractor_calls)
        checkpoint = root / ".wavefoundry" / "upgrade-in-progress.json"
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text(json.dumps({"current_phase": "extracting"}))
        out["core_close_guarded"] = codes(ccall(mcp, "fork_close_container", {"wave_id": "1abcd", "mode": "dry_run"}))
        out["write_replacement_guarded"] = codes(ccall(mcp, "wf_help", {"topic": "x"}))
        out["read_core_unguarded"] = codes(ccall(mcp, "fork_help_core"))
        out["memory_core_extracting"] = codes(ccall(mcp, "fork_memory_validate_core", MEMORY_VALIDATE_ARGS))
        out["memory_replacing_extracting"] = codes(ccall(mcp, "memory_validate", {"record": "r"}))
        checkpoint.write_text(json.dumps({"current_phase": "awaiting_memory_validation"}))
        out["memory_core_recovery"] = codes(ccall(mcp, "fork_memory_validate_core", MEMORY_VALIDATE_ARGS))
        out["memory_replacing_recovery"] = codes(ccall(mcp, "memory_validate", {"record": "r"}))
        checkpoint.unlink()
        out["extensions"] = impl.wf_server_info_response(root)["data"]["extensions"]
        # Reload with replacements rebuilds them.
        result = runner.perform_mcp_reload()
        out["reload_status"] = result["status"]
        out["reload_replaced_call"] = ccall(mcp, "wf_close_wave", {"item": "task-9"})["data"]
        out["reload_core_markers"] = markers(mcp, "fork_close_container")
        handler.close()

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
        write_module("wf_fork", (
            "import server_impl\n"
            "def register(mcp, get_handler):\n"
            "    @mcp.tool()\n"
            "    def wf_fork_tool(**kwargs):\n"
            "        bad = server_impl._ensure_no_extra_args('wf_fork_tool', kwargs)\n"
            "        if bad is not None:\n"
            "            return bad\n"
            "        return {'status': 'ok', 'data': {'fork': True}}\n"
        ))
        write_module("retired_name", "def register(mcp, get_handler):\n    @mcp.tool()\n    def wf_review_evidence(**kwargs):\n        return {}\n")
        write_module("reserved_name", "def register(mcp, get_handler):\n    @mcp.tool()\n    def wf_fixture_reserved(**kwargs):\n        return {}\n")
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
        write_module("replace_close", (
            "import server_impl\n"
            "def register(mcp, get_handler):\n"
            "    @mcp.tool()\n"
            "    def wf_close_wave(item: str, **kwargs):\n"
            "        bad = server_impl._ensure_no_extra_args('wf_close_wave', kwargs)\n"
            "        if bad is not None:\n"
            "            return bad\n"
            "        return {'status': 'ok', 'data': {'item': item}}\n"
        ))
        write_module("open_replacement", "def register(mcp, get_handler):\n    @mcp.tool()\n    def wf_close_wave(item: str):\n        return {}\n")
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
            "tier_unregistered": dict(EXTENSION_MODULES=("twin_a",), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_twin": "read", "acme_ghost": "read"}),
            "core_prefix_new_tool": dict(EXTENSION_MODULES=("wf_fork",), EXTENSION_TOOL_PREFIXES=("wf_",), EXTENSION_TOOL_TIERS={"wf_fork_tool": "read"}),
            "reserved_retired_name": dict(EXTENSION_MODULES=("retired_name",), EXTENSION_TOOL_PREFIXES=("wf_",), EXTENSION_TOOL_TIERS={"wf_review_evidence": "read"}),
            "reserved_collection_name": dict(EXTENSION_MODULES=("reserved_name",), EXTENSION_TOOL_PREFIXES=("wf_",), EXTENSION_TOOL_TIERS={"wf_fixture_reserved": "read"}),
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
            # Wave 1z8oz: aliases, hidden names and replacements.
            "alias_runner_name": dict(EXTENSION_TOOL_ALIASES={"wf_reload_mcp": "wf_help"}),
            "alias_existing_name": dict(EXTENSION_TOOL_ALIASES={"wf_help": "wf_current_wave"}),
            "alias_no_prefix": dict(EXTENSION_TOOL_ALIASES={"other_help": "wf_help"}),
            "alias_missing_target": dict(EXTENSION_TOOL_ALIASES={"wf_alias_ghost": "wf_not_a_tool"}),
            "alias_of_alias": dict(EXTENSION_TOOL_ALIASES={"wf_alias_a": "wf_help", "wf_alias_b": "wf_alias_a"}),
            "alias_retired_name": dict(EXTENSION_TOOL_ALIASES={"wf_review_evidence": "wf_help"}),
            "hidden_without_alias": dict(EXTENSION_HIDDEN_TOOLS=("wf_help",)),
            "hidden_runner": dict(EXTENSION_HIDDEN_TOOLS=("wf_reload_mcp",)),
            "hidden_twice": dict(EXTENSION_TOOL_ALIASES={"wf_alias_help": "wf_help"}, EXTENSION_HIDDEN_TOOLS=("wf_help", "wf_help")),
            "alias_of_alias_for_core": dict(EXTENSION_MODULES=("replace_close",), EXTENSION_REPLACEMENTS={"replace_close": {"wf_close_wave": {"alias_for_core": "wf_core_close"}}}, EXTENSION_TOOL_ALIASES={"wf_alias_core": "wf_core_close"}),
            "alias_to_replaced": dict(EXTENSION_MODULES=("replace_close",), EXTENSION_REPLACEMENTS={"replace_close": {"wf_close_wave": {"alias_for_core": "wf_core_close"}}}, EXTENSION_TOOL_ALIASES={"wf_alias_close": "wf_close_wave"}),
            "hide_replaced": dict(EXTENSION_MODULES=("replace_close",), EXTENSION_REPLACEMENTS={"replace_close": {"wf_close_wave": {"alias_for_core": "wf_core_close"}}}, EXTENSION_HIDDEN_TOOLS=("wf_close_wave",)),
            "replace_runner": dict(EXTENSION_MODULES=("replace_close",), EXTENSION_REPLACEMENTS={"replace_close": {"wf_reload_mcp": {"alias_for_core": "wf_core_reload"}}}),
            "replace_and_override": dict(EXTENSION_MODULES=("replace_close",), EXTENSION_OVERRIDES={"replace_close": ("wf_close_wave",)}, EXTENSION_REPLACEMENTS={"replace_close": {"wf_close_wave": {"alias_for_core": "wf_core_close"}}}),
            "replace_bad_tier": dict(EXTENSION_MODULES=("replace_close",), EXTENSION_REPLACEMENTS={"replace_close": {"wf_close_wave": {"alias_for_core": "wf_core_close", "tier": "admin"}}}),
            "replace_alias_collides": dict(EXTENSION_MODULES=("replace_close",), EXTENSION_REPLACEMENTS={"replace_close": {"wf_close_wave": {"alias_for_core": "wf_help"}}}),
            "replace_alias_retired": dict(EXTENSION_MODULES=("replace_close",), EXTENSION_REPLACEMENTS={"replace_close": {"wf_close_wave": {"alias_for_core": "wf_review_evidence"}}}),
            "replace_open_schema": dict(EXTENSION_MODULES=("open_replacement",), EXTENSION_REPLACEMENTS={"open_replacement": {"wf_close_wave": {"alias_for_core": "wf_core_close"}}}),
            "aliases_only_served": dict(EXTENSION_TOOL_ALIASES={"wf_alias_help": "wf_help"}),
            "replace_not_registered": dict(EXTENSION_MODULES=("twin_a",), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_twin": "read"}, EXTENSION_REPLACEMENTS={"twin_a": {"wf_close_wave": {"alias_for_core": "wf_core_close"}}}),
        }
        empty = dict(EXTENSION_MODULES=(), EXTENSION_TOOL_PREFIXES=(), EXTENSION_TOOL_TIERS={}, EXTENSION_OVERRIDES={},
                     EXTENSION_TOOL_ALIASES={}, EXTENSION_HIDDEN_TOOLS=(), EXTENSION_REPLACEMENTS={})
        results = {}
        for label, attrs in cases.items():
            for key, value in {**empty, **attrs}.items():
                setattr(ext, key, value)
            for mod in ("acme_tools", "no_register", "raiser", "undeclared_override", "bad_compat", "twin_a", "twin_b", "unprefixed", "escaped", "not_there",
                        "async_tools", "bypass_manager", "bypass_table", "tamperer", "resource_tools", "prompt_tools",
                        "withdrawer", "served_writer", "type_change", "default_change", "extended_tools",
                        "wf_fork", "retired_name", "reserved_name", "replace_close", "open_replacement"):
                if getattr(sys.modules.get(mod), "__wf_extension__", False):
                    sys.modules.pop(mod, None)
            mcp = FastMCP("case")
            if label == "reserved_collection_name":
                impl._COST_FOCUS_EXTRACTORS["wf_fixture_reserved"] = lambda *a, **k: None
            try:
                impl.register_mcp_surface(mcp, runner._get_handler)
                results[label] = {"raised": None, "served": len(table(mcp))}
                if label == "core_prefix_new_tool":
                    import mcp_tool_roster
                    results[label]["call"] = ccall(mcp, "wf_fork_tool")["data"]
                    results[label]["tier"] = impl._TOOL_REGISTRY.get("wf_fork_tool").tier
                    results[label]["markers"] = markers(mcp, "wf_fork_tool")
                    results[label]["parity_defects"] = [d.name for d in impl._TOOL_REGISTRY.parity_defects]
                    results[label]["read_rule"] = "mcp__wavefoundry__wf_fork_tool" in mcp_tool_roster.allow_rules(False)
                if label == "aliases_only_served":
                    import mcp_tool_roster
                    results[label]["call"] = ccall(mcp, "wf_alias_help")["status"]
                    results[label]["shares_fn"] = table(mcp)["wf_alias_help"].fn is table(mcp)["wf_help"].fn
                    results[label]["parity_defects"] = [d.name for d in impl._TOOL_REGISTRY.parity_defects]
                    results[label]["read_rule"] = "mcp__wavefoundry__wf_alias_help" in mcp_tool_roster.allow_rules(False)
                if label == "extended_override":
                    results[label]["with_team"] = ccall(mcp, "wf_create_wave", {"slug": "probe", "team": "blue"})["data"]
                    results[label]["core_call"] = ccall(mcp, "wf_create_wave", {"slug": "probe"})["data"]
            except BaseException as exc:
                results[label] = {"raised": type(exc).__name__, "message": str(exc), "served": sorted(table(mcp))}
            impl._COST_FOCUS_EXTRACTORS.pop("wf_fixture_reserved", None)
        out["cases"] = results
        # Wave 1z8oz: registering again after a replacement leaves no replaced state behind.
        for key, value in {**empty, "EXTENSION_MODULES": ("replace_close",),
                           "EXTENSION_REPLACEMENTS": {"replace_close": {"wf_close_wave": {"alias_for_core": "wf_core_close"}}}}.items():
            setattr(ext, key, value)
        sys.modules.pop("replace_close", None)
        with_replacement = FastMCP("with_replacement")
        impl.register_mcp_surface(with_replacement, runner._get_handler)
        out["replaced_during"] = sorted(impl._EXTENSION_REPLACED_CORE)
        for key, value in empty.items():
            setattr(ext, key, value)
        stock_again = FastMCP("stock_again")
        impl.register_mcp_surface(stock_again, runner._get_handler)
        out["replaced_after_stock"] = sorted(impl._EXTENSION_REPLACED_CORE)
        out["stock_again_markers"] = markers(stock_again, "wf_close_wave")
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
        self.assertEqual(mcp_tool_extensions.served_name_map(), {})

    def test_empty_declaration_reports_no_served_names(self):
        # Wave 1z8oz: the new provenance fields exist and are empty.
        ext = self.out["extensions"]
        self.assertEqual(ext["aliases"], {})
        self.assertEqual(ext["hidden"], [])
        self.assertEqual(ext["replacements"], [])
        self.assertEqual(ext["served_names"], {})


class AliasServingTests(unittest.TestCase):
    """Wave 1z8oz AC-1 to AC-3, AC-5 to AC-7: an aliases-only declaration."""

    @classmethod
    def setUpClass(cls):
        cls.stock = _run("stock")
        cls.out = _run("alias")

    def test_aliases_only_declaration_is_served_with_roster_parity(self):
        self.assertEqual(self.out["parity_defects"], [])
        self.assertEqual(self.out["registry_vs_tiers"], [])
        self.assertEqual(self.out["tier_mismatches"], [])
        self.assertEqual(self.out["served_vs_tiers"], [])

    def test_alias_is_the_canonical_wrapped_tool(self):
        self.assertTrue(self.out["alias_shares_fn"])
        self.assertEqual(self.out["markers"]["fork_close_container"], self.out["markers"]["wf_close_wave"])
        # The canonical markers are the stock chain plus the hint rewrite.
        self.assertEqual(self.out["markers"]["wf_close_wave"], self.stock["markers"]["wf_close_wave"] + ["rewrite"])

    def test_alias_takes_the_canonical_lock_and_its_hints_name_served_tools(self):
        busy = self.out["busy"]
        self.assertEqual(busy["codes"], ["error", "lifecycle_mutation_locked"])
        self.assertTrue(busy["busy"])
        self.assertEqual(busy["next_tools"], ["fork_close_container", "fork_current"])
        self.assertEqual(busy["recovery_tools"], [["fork_close_container", "fork_current"]])
        self.assertTrue(busy["usage"].startswith("retry fork_close_container "), busy["usage"])
        self.assertTrue(busy["recovery_usage"][0].startswith("fork_close_container(...)"), busy["recovery_usage"])

    def test_alias_takes_the_canonical_publication_guard(self):
        self.assertEqual(self.out["guarded"], ["error", "upgrade_in_progress"])

    def test_cost_accounting_follows_the_canonical_name(self):
        # wf_close_wave is cost-exempt, wf_current_wave is not; the record
        # carries the canonical name. The exempt call reaches the handler.
        self.assertEqual(self.out["cost_after_costed_alias"], ["wf_current_wave"])
        self.assertEqual(self.out["exempt_alias_call"], ["error", "wave_not_found"])  # the handler answered
        self.assertEqual(self.out["cost_after_exempt_alias"], ["wf_current_wave"])
        self.assertNotIn("cost", self.out["markers"]["fork_close_container"])

    def test_hidden_name_is_not_listed_or_callable_while_its_alias_works(self):
        self.assertFalse(self.out["listed_hidden"])
        self.assertTrue(self.out["listed_alias"])
        self.assertIn("Unknown tool", self.out["hidden_call"])
        self.assertEqual(self.out["alias_call"], "ok")

    def test_allowlist_carries_aliases_at_their_tier_and_omits_hidden_names(self):
        self.assertEqual(self.out["tiers"]["fork_current"], "read")
        self.assertEqual(self.out["tiers"]["fork_close_container"], "write")
        self.assertIsNone(self.out["tiers"]["wf_current_wave"])  # hidden: no roster tier
        self.assertIn("fork_current", self.out["read_rules"])
        self.assertNotIn("wf_current_wave", self.out["read_rules"])
        self.assertIn("fork_close_container", self.out["write_rules"])
        self.assertNotIn("fork_close_container", self.out["read_rules"])

    def test_provenance_publishes_aliases_hidden_names_and_the_first_declared_map(self):
        ext = self.out["extensions"]
        self.assertEqual(ext["hidden"], ["wf_current_wave"])
        self.assertEqual(ext["aliases"]["fork_current_again"], "wf_current_wave")
        self.assertEqual(ext["served_names"], {
            "wf_close_wave": "fork_close_container",
            "wf_add_change": "fork_add_change",
            "wf_current_wave": "fork_current",
        })
        self.assertEqual(ext["replacements"], [])

    def test_reload_rebuilds_served_names_and_fails_closed(self):
        self.assertEqual(self.out["reload_status"], "ok")
        self.assertEqual(self.out["reload_names"], ["fork_add_change", "fork_close_container", "fork_current", "fork_current_again"])
        self.assertFalse(self.out["reload_hidden"])
        self.assertTrue(self.out["reload_shares_fn"])
        self.assertIn("register_surface_failed", self.out["failed_reload_text"])
        self.assertIn("which is not a served tool", self.out["failed_reload_text"])
        self.assertEqual(self.out["served_after_failure"], ["wf_reload_mcp"])


class ReplacementServingTests(unittest.TestCase):
    """Wave 1z8oz AC-4 and AC-7: core names reused with incompatible handlers."""

    @classmethod
    def setUpClass(cls):
        cls.stock = _run("stock")
        cls.out = _run("replace")

    def test_roster_parity_with_replacements(self):
        self.assertEqual(self.out["parity_defects"], [])
        self.assertEqual(self.out["registry_vs_tiers"], [])
        self.assertEqual(self.out["tier_mismatches"], [])
        self.assertEqual(self.out["served_vs_tiers"], [])

    def test_replacing_handler_is_served_under_the_core_name_with_stock_wrappers(self):
        self.assertEqual(self.out["replaced_call"]["data"], {"closed_item": "task-7"})
        for name in ("wf_review_event", "wf_current_wave"):
            self.assertEqual(self.out["markers"][name], self.stock["markers"][name], name)
        # wf_close_wave is cost-exempt because its core handler records its own
        # cost; the replacing handler gets the cost wrapper instead (DEL-1).
        self.assertNotIn("cost", self.stock["markers"]["wf_close_wave"])
        self.assertEqual(self.out["markers"]["wf_close_wave"], ["cost"] + self.stock["markers"]["wf_close_wave"])
        self.assertIn("lock", self.out["markers"]["wf_close_wave"])

    def test_replacing_handler_on_a_cost_exempt_name_records_its_debit(self):
        self.assertEqual(self.out["cost_after_exempt_replacement"], ["wf_close_wave"])

    def test_replacing_handler_keeps_its_own_hints(self):
        self.assertEqual(self.out["replaced_call"]["next_tools"], ["wf_close_wave"])
        self.assertEqual(self.out["replaced_call"]["usage"], "wf_close_wave(item=...)")
        busy = self.out["replaced_busy"]
        self.assertEqual(busy["codes"], ["error", "lifecycle_mutation_locked"])
        self.assertEqual(busy["recovery_tools"], [["wf_close_wave", "wf_current_wave"]])

    def test_core_behaviour_has_stock_wrappers_plus_rewrite(self):
        for core, alias in (("wf_close_wave", "fork_close_container"), ("wf_review_event", "fork_review_event_core"),
                            ("wf_help", "fork_help_core"), ("memory_validate", "fork_memory_validate_core"),
                            ("wf_current_wave", "fork_current_core")):
            self.assertEqual(self.out["markers"][alias], self.stock["markers"][core] + ["rewrite"], alias)

    def test_core_behaviour_lock_busy_names_alias_for_core(self):
        busy = self.out["core_busy"]
        self.assertEqual(busy["codes"], ["error", "lifecycle_mutation_locked"])
        self.assertEqual(busy["next_tools"], ["fork_close_container", "fork_current_core"])
        self.assertEqual(busy["recovery_tools"], [["fork_close_container", "fork_current_core"]])

    def test_core_tools_that_are_not_replaced_name_alias_for_core(self):
        busy = self.out["other_core_busy"]
        self.assertEqual(busy["codes"], ["error", "lifecycle_mutation_locked"])
        self.assertEqual(busy["next_tools"], ["wf_add_change", "fork_current_core"])
        self.assertEqual(busy["recovery_tools"], [["wf_add_change", "fork_current_core"]])

    def test_core_behaviour_is_upgrade_guarded(self):
        self.assertEqual(self.out["core_close_guarded"], ["error", "upgrade_in_progress"])

    def test_extractors_run_for_the_core_behaviour_only(self):
        self.assertEqual(self.out["replaced_review"], {"note": "n"})
        self.assertEqual(self.out["extractor_after_replaced"], 0)
        self.assertEqual(self.out["cost_after_replaced"], [["wf_review_event", 0]])
        self.assertEqual(self.out["extractor_after_core"], 1)

    def test_write_replacement_of_a_read_tool_is_guarded_and_write_tiered(self):
        self.assertIn("guard", self.out["markers"]["wf_help"])
        self.assertNotIn("guard", self.stock["markers"]["wf_help"])
        self.assertEqual(self.out["write_replacement_guarded"], ["error", "upgrade_in_progress"])
        self.assertEqual(self.out["tiers"]["wf_help"], "write")
        self.assertEqual(self.out["tiers"]["fork_help_core"], "read")
        self.assertNotIn("wf_help", self.out["read_rules"])
        self.assertIn("wf_help", self.out["write_rules"])
        self.assertIn("fork_help_core", self.out["read_rules"])
        # The core behaviour stays read and unguarded.
        self.assertNotIn("guard", self.out["markers"]["fork_help_core"])
        self.assertEqual(self.out["read_core_unguarded"][0], "ok")

    def test_memory_validate_core_keeps_its_recovery_exemption(self):
        self.assertIn("upgrade_in_progress", self.out["memory_core_extracting"])
        self.assertNotIn("upgrade_in_progress", self.out["memory_core_recovery"])

    def test_replacing_handler_of_a_registered_publisher_keeps_its_guard(self):
        # memory_validate is a registered publisher: its replacing handler keeps
        # the block guard with the memory_recovery exemption, not the checkpoint.
        self.assertIn("upgrade_in_progress", self.out["memory_replacing_extracting"])
        self.assertEqual(self.out["memory_replacing_recovery"], ["ok"])

    def test_reload_rebuilds_replacements(self):
        self.assertEqual(self.out["reload_status"], "ok")
        self.assertEqual(self.out["reload_replaced_call"], {"closed_item": "task-9"})
        self.assertEqual(self.out["reload_core_markers"], self.out["markers"]["fork_close_container"])

    def test_provenance_lists_replacements_and_the_served_map(self):
        ext = self.out["extensions"]
        self.assertEqual(ext["replacements"], [
            {"core_name": "memory_validate", "module": "fork_tools", "alias_for_core": "fork_memory_validate_core", "tier": "write"},
            {"core_name": "wf_close_wave", "module": "fork_tools", "alias_for_core": "fork_close_container", "tier": "write"},
            {"core_name": "wf_current_wave", "module": "fork_tools", "alias_for_core": "fork_current_core", "tier": "read"},
            {"core_name": "wf_help", "module": "fork_tools", "alias_for_core": "fork_help_core", "tier": "write"},
            {"core_name": "wf_review_event", "module": "fork_tools", "alias_for_core": "fork_review_event_core", "tier": "write"},
        ])
        self.assertEqual(ext["served_names"]["wf_close_wave"], "fork_close_container")
        (module,) = ext["modules"]
        self.assertEqual(module["replacements"], ["memory_validate", "wf_close_wave", "wf_current_wave", "wf_help", "wf_review_event"])


class ServedNameRewriteTests(unittest.TestCase):
    """Wave 1z8oz Requirement 6: the four hint fields, exact and whole-name."""

    def setUp(self):
        from server_tools_support import load_server
        self.impl = load_server()

    def test_rewrites_only_the_hint_fields_and_never_mutates(self):
        names = {"wf_close_wave": "fork_close_container"}
        result = {
            "status": "error",
            "data": {"next_step": "wf_close_wave"},
            "next_tools": ["wf_close_wave", "wf_close_wave_x", "wf_current_wave"],
            "usage": "retry wf_close_wave(mode='x'); not wf_close_wave_x or xwf_close_wave",
            "diagnostics": [{"code": "c", "message": "wf_close_wave is busy",
                             "recovery_tools": ["wf_close_wave"], "recovery_usage": "wf_close_wave(...)"}],
        }
        before = json.dumps(result, sort_keys=True)
        out = self.impl._rewrite_served_names(result, names)
        self.assertEqual(json.dumps(result, sort_keys=True), before)
        self.assertEqual(out["next_tools"], ["fork_close_container", "wf_close_wave_x", "wf_current_wave"])
        self.assertEqual(out["usage"], "retry fork_close_container(mode='x'); not wf_close_wave_x or xwf_close_wave")
        self.assertEqual(out["diagnostics"][0]["recovery_tools"], ["fork_close_container"])
        self.assertEqual(out["diagnostics"][0]["recovery_usage"], "fork_close_container(...)")
        self.assertEqual(out["diagnostics"][0]["message"], "wf_close_wave is busy")
        self.assertEqual(out["data"], {"next_step": "wf_close_wave"})

    def test_core_behaviour_chain_tracks_middleware(self):
        # The core behaviour of a replaced name must get every wrapper the main
        # chain applies; a wrapper added to MIDDLEWARE alone would be missed.
        self.assertEqual([label for label, _ in self.impl._CORE_BEHAVIOUR_MIDDLEWARE],
                         [label for label, _ in self.impl.MIDDLEWARE])

    def test_empty_map_returns_the_same_object(self):
        result = {"next_tools": ["wf_close_wave"]}
        self.assertIs(self.impl._rewrite_served_names(result, {}), result)


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
        "tier_unregistered": "has no registered tool",
        "reserved_retired_name": "a name reserved by core _RENAMED_MCP_TOOLS",
        "reserved_collection_name": "a name reserved by core _COST_FOCUS_EXTRACTORS",
        "async_handler": "extension handlers must be synchronous",
        "unrecorded_manager_add": "outside FastMCP.add_tool",
        "unrecorded_table_write": "outside FastMCP.add_tool",
        "tampered_staging": "replaces or removes tools staged by another module",
        "resource_registered": "registers MCP resources",
        "prompt_registered": "registers MCP prompts",
        "type_changed_override": "changes the schema of parameters ['slug']",
        "withdrawn_override": "removes tools it registered",
        "served_table_write": "changes the served tool table directly",
        # Wave 1z8oz.
        "alias_runner_name": "alias 'wf_reload_mcp' collides with runner tool",
        "alias_existing_name": "alias 'wf_help' collides with an existing tool",
        "alias_no_prefix": "alias 'other_help' does not start with a core or declared extension prefix",
        "alias_missing_target": "targets 'wf_not_a_tool', which is not a served tool",
        "alias_of_alias": "alias 'wf_alias_b' targets another alias 'wf_alias_a'",
        "alias_retired_name": "alias 'wf_review_evidence' is a name reserved by core _RENAMED_MCP_TOOLS",
        "hidden_without_alias": "hidden name 'wf_help' has no alias",
        "hidden_runner": "hidden name 'wf_reload_mcp' is a runner tool",
        "alias_to_replaced": "alias 'wf_alias_close' targets replaced core name 'wf_close_wave'; its core behaviour is served only under its alias_for_core",
        "alias_of_alias_for_core": "alias 'wf_alias_core' targets another alias 'wf_core_close'",
        "hidden_twice": "hidden name 'wf_help' is declared twice",
        "hide_replaced": "hidden name 'wf_close_wave' is a replaced core name",
        "replace_runner": "may not replace runner tool 'wf_reload_mcp'",
        "replace_and_override": "'wf_close_wave' is declared both as an override and as a replacement",
        "replace_bad_tier": "replacement 'wf_close_wave' declares tier 'admin'",
        "replace_alias_collides": "alias_for_core of 'wf_close_wave' 'wf_help' collides with an existing tool",
        "replace_alias_retired": "alias_for_core of 'wf_close_wave' 'wf_review_evidence' is a name reserved by core _RENAMED_MCP_TOOLS",
        "replace_open_schema": "replacement 'wf_close_wave' does not reject undeclared arguments",
        "replace_not_registered": "declares replacement 'wf_close_wave' but does not register it",
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

    def test_core_prefixed_new_tool_is_served_tiered_and_wrapped(self):
        # Wave 1yyoj: extension tools may use core prefixes such as wf_.
        result = self.out["cases"]["core_prefix_new_tool"]
        self.assertIsNone(result["raised"], result)
        self.assertEqual(result["call"], {"fork": True})
        self.assertEqual(result["tier"], "read")
        self.assertIn("cost", result["markers"])
        self.assertEqual(result["parity_defects"], [])
        self.assertTrue(result["read_rule"])

    def test_registration_after_a_replacement_leaves_no_replaced_state(self):
        self.assertEqual(self.out["replaced_during"], ["wf_close_wave"])
        self.assertEqual(self.out["replaced_after_stock"], [])
        self.assertNotIn("cost", self.out["stock_again_markers"])

    def test_aliases_only_declaration_is_validated_and_served(self):
        # Wave 1z8oz AC-1: no module and no prefix, only an alias.
        result = self.out["cases"]["aliases_only_served"]
        self.assertIsNone(result["raised"], result)
        self.assertEqual(result["call"], "ok")
        self.assertTrue(result["shares_fn"])
        self.assertEqual(result["parity_defects"], [])
        self.assertTrue(result["read_rule"])

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


# Wave 1yyoj: every module-level assignment in scripts/ and wave_lint_lib/ whose
# string literals include a registered or retired MCP tool name, or whose value
# references an already-classified collection, classified by whether it changes
# how the server wraps, accounts, dispatches or upgrade-reconciles a tool by that
# name. A collection that names only unserved tools, or that lives inside a
# function, is outside this census; the membership invariant below keeps the
# reserved collections to served core or retired names.
RESERVED_COLLECTIONS = {
    ("wf_server/server_impl.py", "_LIFECYCLE_MUTATION_LOCK_TOOLS"),
    ("wf_server/server_impl.py", "_COST_EXEMPT_TOOLS"),
    ("wf_server/server_impl.py", "_ARTIFACT_EXTRACTORS"),
    ("wf_server/server_impl.py", "_COST_FOCUS_EXTRACTORS"),
    ("wf_server/context_efficiency_handlers.py", "_STATE_SOURCE_EXTRACTORS"),
    ("publication_control.py", "PUBLICATION_WRITER_REGISTRY"),
    ("render_platform_surfaces.py", "_RENAMED_MCP_TOOLS"),
}
# Reached only through core code passing its own literal tool name, or data
# about the roster, evaluation or configuration: no behavior for a foreign name.
NON_BEHAVIOR_COLLECTIONS = {
    ("context_efficiency.py", "LIFECYCLE_PROMPT_MAP"),
    ("graph_quality_eval.py", "RELATION_TOOL_MATRIX"),
    ("mcp_tool_roster.py", "RUNNER_TOOLS"),
    ("mcp_tool_roster.py", "TOOL_TIERS"),
    ("reconcile_scan.py", "_CONFIG_KEY_TOOL_NAMES"),
    ("retrieval_eval.py", "TOOLS"),
    ("retrieval_eval.py", "CALL_TIMEOUT_SECONDS"),
    ("retrieval_eval.py", "OPERATOR_REVIEW_P95_MS"),
    ("server.py", "_RELOAD_SURVIVOR_TOOLS"),
    ("wf_server/server_impl.py", "CODE_SEARCH_SUBSTRATE_SOURCES"),
    ("wf_server/server_impl.py", "CODE_ASK_SUBSTRATE_SOURCES"),
    ("wf_server/server_impl.py", "_CONTEXT_RETRIEVAL_TOOLS"),
    ("wf_server/server_impl.py", "_INDEXED_CONTEXT_TOOLS"),
    ("wf_server/server_impl.py", "_REFERENCE_ONLY_GRAPH_TOOLS"),
    ("wf_server/server_impl.py", "_LIFECYCLE_CONTEXT_STAGES"),
    ("wf_server/server_impl.py", "_TRACKING_CONTEXT_TOOLS"),
    ("upgrade_extensions.py", "_CONFIG_KEY_RENAMES"),
    ("wave_lint_lib/constants.py", "WORKFLOW_REQUIRED_KEYS"),
}
# Built from a classified collection, so they hold the same names: each maps to
# its source and is covered by the source's classification.
DERIVED_COLLECTIONS = {
    ("graph_quality_eval.py", "SCORED_RELATIONS"): "RELATION_TOOL_MATRIX",
    ("publication_control.py", "_BY_TOOL"): "PUBLICATION_WRITER_REGISTRY",
    ("publication_control.py", "_BY_NATIVE_PRODUCER"): "PUBLICATION_WRITER_REGISTRY",
    ("reconcile_scan.py", "RENAMED_TOOLS"): "_RENAMED_MCP_TOOLS",
    ("reconcile_scan.py", "_RENAMED_ALT_ALL"): "RENAMED_TOOLS",
    ("reconcile_scan.py", "_RENAMED_ALT_BARE"): "RENAMED_TOOLS",
    ("reconcile_scan.py", "_TOOL_BARE_PATTERN"): "_RENAMED_ALT_BARE",
    ("reconcile_scan.py", "_TOOL_MCP_PATTERN"): "_RENAMED_ALT_ALL",
}


def _tool_name_collections() -> set[tuple[str, str]]:
    import ast
    import mcp_tool_roster
    import render_platform_surfaces
    names = set(mcp_tool_roster.TOOL_TIERS) | set(render_platform_surfaces._RENAMED_MCP_TOOLS)
    classified = {
        name for _file, name in RESERVED_COLLECTIONS | NON_BEHAVIOR_COLLECTIONS | set(DERIVED_COLLECTIONS)
    }
    found: set[tuple[str, str]] = set()
    paths = framework_source_files() + sorted((SCRIPTS / "wave_lint_lib").glob("*.py"))
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            target_names = [t.id for t in targets if isinstance(t, ast.Name)]
            if not target_names:
                continue
            literals = {
                n.value for n in ast.walk(node.value)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
            }
            refs = {n.id for n in ast.walk(node.value) if isinstance(n, ast.Name)}
            refs |= {n.attr for n in ast.walk(node.value) if isinstance(n, ast.Attribute)}
            if literals & names or (refs & classified) - {target_names[0]}:
                rel = path.relative_to(SCRIPTS).as_posix()
                found.add((rel, target_names[0]))
    return found


class ReservedNameCensusTests(unittest.TestCase):
    """Every tool-name collection is classified; reserved ones are refused."""

    def test_every_tool_name_collection_is_classified(self):
        found = _tool_name_collections()
        known = RESERVED_COLLECTIONS | NON_BEHAVIOR_COLLECTIONS | set(DERIVED_COLLECTIONS)
        unclassified = found - known
        self.assertEqual(unclassified, set(), "classify new tool-name collections as reserved, non-behavior or derived")
        stale = known - found
        self.assertEqual(stale, set(), "remove classifications for collections that no longer exist")

    def test_every_derived_collection_maps_to_a_classified_source(self):
        classified = {
            name for _file, name in RESERVED_COLLECTIONS | NON_BEHAVIOR_COLLECTIONS | set(DERIVED_COLLECTIONS)
        }
        orphans = {key: src for key, src in DERIVED_COLLECTIONS.items() if src not in classified}
        self.assertEqual(orphans, {})

    def test_reserved_collections_hold_only_served_or_retired_names(self):
        from server_tools_support import load_server
        import mcp_tool_roster
        impl = load_server()
        served = set(mcp_tool_roster.TOOL_TIERS)
        collections = impl._reserved_tool_name_collections()
        retired = collections.pop("_RENAMED_MCP_TOOLS")
        self.assertTrue(retired)
        self.assertEqual(retired & served, set(), "a retired name is served again")
        for label, members in collections.items():
            with self.subTest(collection=label):
                self.assertTrue(members, f"{label} is empty, so this check would pass vacuously")
                self.assertEqual(members - served, set(), f"{label} names a tool core does not serve")

    def test_registration_reserves_exactly_the_reserved_collections(self):
        from server_tools_support import load_server
        impl = load_server()
        labels = set(impl._reserved_tool_name_collections())
        expected = {name for _file, name in RESERVED_COLLECTIONS}
        expected = {"publication_control.PUBLICATION_WRITER_REGISTRY" if n == "PUBLICATION_WRITER_REGISTRY" else n for n in expected}
        self.assertEqual(labels, expected)


class DeclarationValidationTests(unittest.TestCase):
    """Pure helper coverage for the stdlib declaration module."""

    def setUp(self):
        import mcp_tool_extensions
        self.ext = mcp_tool_extensions
        self.saved = {k: getattr(mcp_tool_extensions, k) for k in (
            "EXTENSION_MODULES", "EXTENSION_TOOL_PREFIXES", "EXTENSION_TOOL_TIERS", "EXTENSION_OVERRIDES",
            "EXTENSION_TOOL_ALIASES", "EXTENSION_HIDDEN_TOOLS", "EXTENSION_REPLACEMENTS")}

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

    def test_each_new_constant_alone_makes_the_declaration_declared(self):
        # Wave 1z8oz: an aliases-only or hide-only declaration is validated, not ignored.
        for key, value in (
            ("EXTENSION_TOOL_ALIASES", {"wf_alias_help": "wf_help"}),
            ("EXTENSION_HIDDEN_TOOLS", ("wf_help",)),
            ("EXTENSION_REPLACEMENTS", {"m": {"wf_help": {"alias_for_core": "wf_core_help"}}}),
        ):
            with self.subTest(key=key):
                for name in self.saved:
                    setattr(self.ext, name, type(self.saved[name])())
                setattr(self.ext, key, value)
                self.assertTrue(self.ext.declared())

    def test_served_name_map_prefers_the_first_alias_and_the_replacement(self):
        self.ext.EXTENSION_MODULES = ("m",)
        self.ext.EXTENSION_TOOL_ALIASES = {"wf_first": "wf_help", "wf_second": "wf_help", "wf_other": "wf_current_wave"}
        self.ext.EXTENSION_REPLACEMENTS = {"m": {"wf_close_wave": {"alias_for_core": "wf_core_close"}}}
        self.assertEqual(self.ext.served_name_map(), {
            "wf_help": "wf_first", "wf_current_wave": "wf_other", "wf_close_wave": "wf_core_close",
        })
        core = {"wf_help", "wf_current_wave", "wf_close_wave"}
        self.assertEqual(self.ext.declaration_problems(core_tools=core, runner_tools={"wf_reload_mcp"}), [])

    def test_alias_targets_may_be_extension_tools_but_not_unknown_kinds(self):
        self.ext.EXTENSION_MODULES = ("m",)
        self.ext.EXTENSION_TOOL_PREFIXES = ("acme_",)
        self.ext.EXTENSION_TOOL_TIERS = {"acme_echo": "read"}
        self.ext.EXTENSION_TOOL_ALIASES = {"acme_say": "acme_echo"}
        self.assertEqual(self.ext.declaration_problems(core_tools={"wf_help"}, runner_tools=set()), [])
        self.ext.EXTENSION_REPLACEMENTS = {"m": {"wf_help": {"alias_for_core": "acme_core_help", "extra": 1}}}
        problems = " ".join(self.ext.declaration_problems(core_tools={"wf_help"}, runner_tools=set()))
        self.assertIn("has unknown keys ['extra']", problems)


if __name__ == "__main__":
    unittest.main()
