"""Unit tests for ``mcp_tool_registry`` against a stub FastMCP tool table (wave 1y0h1).

These exercise the registry and the middleware chain with no server boot: a
stub ``mcp`` carries a hand-built ``_tool_manager._tools`` table and a stub
roster carries ``TOOL_TIERS`` and ``RUNNER_TOOLS``.

``HandlerDigestTests`` pins every ``@mcp.tool`` handler in
``register_mcp_surface`` against digests captured before this wave edited
``server_impl.py`` (AC-1). The digest is taken over each handler's exact source
text, located through the AST, rather than over ``ast.dump``, whose output
varies between the supported Python versions.

``RealSurfaceRegistryTests`` boots the real server with a stub handler and
checks the registry and the wrapper marks it records (AC-2, AC-3).
``ReloadFreshnessTests`` proves in a subprocess, against a scratch copy of the
scripts tree, that a reload rebuilds the registry from fresh code (AC-4).
"""
from __future__ import annotations

import ast
import contextlib
import functools
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
import types
import unittest
from pathlib import Path

from unittest.mock import patch

import mcp_tool_registry as reg
from server_tools_support import load_server
from test_tool_surface_golden import _BootedSurface

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
DIGEST_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "register-surface-handler-digests.json"


def _entry(fn, annotations=None):
    return types.SimpleNamespace(fn=fn, annotations=annotations)


def _mcp(table):
    return types.SimpleNamespace(_tool_manager=types.SimpleNamespace(_tools=table))


def _roster(tiers, runner=()):
    return types.SimpleNamespace(TOOL_TIERS=dict(tiers), RUNNER_TOOLS=frozenset(runner))


def _tool(name):
    def fn():
        return name
    fn.__name__ = name
    return fn


class BuildRegistryTests(unittest.TestCase):
    def test_specs_mirror_the_table_and_the_roster(self):
        read_fn, write_fn = _tool("a_read"), _tool("b_write")
        mcp = _mcp({
            "b_write": _entry(write_fn, annotations={"destructiveHint": True}),
            "a_read": _entry(read_fn),
        })
        registry = reg.build_registry(mcp, _roster({"a_read": "read", "b_write": "write"}))

        self.assertEqual([s.name for s in registry.tools()], ["a_read", "b_write"])
        spec = registry.get("b_write")
        self.assertEqual(spec.tier, "write")
        self.assertEqual(spec.annotations, {"destructiveHint": True})
        self.assertIs(spec.callable, write_fn)
        self.assertEqual(spec.source_module, write_fn.__module__)
        self.assertIsNone(registry.get("missing"))
        self.assertEqual(registry.parity_defects, [])

    def test_extra_tool_and_removed_roster_entry_are_both_reported(self):
        # AC-2: one registered tool absent from the roster, and one roster
        # entry with no registration, must both surface as defects.
        mcp = _mcp({"kept": _entry(_tool("kept")), "extra": _entry(_tool("extra"))})
        registry = reg.build_registry(mcp, _roster({"kept": "read", "removed": "read"}))

        self.assertEqual(
            sorted((d.kind, d.name) for d in registry.parity_defects),
            [
                (reg.DEFECT_UNROSTERED_TOOL, "extra"),
                (reg.DEFECT_UNREGISTERED_ROSTER_TOOL, "removed"),
            ],
        )
        self.assertIsNone(registry.get("extra").tier)

    def test_runner_survivors_are_excluded_on_both_registration_paths(self):
        roster = _roster({"impl": "read", "wf_reload_mcp": "write"}, runner={"wf_reload_mcp"})
        initial = reg.build_registry(_mcp({"impl": _entry(_tool("impl"))}), roster)
        reloaded = reg.build_registry(
            _mcp({"impl": _entry(_tool("impl")), "wf_reload_mcp": _entry(_tool("wf_reload_mcp"))}),
            roster,
        )
        for label, registry in (("initial", initial), ("reload", reloaded)):
            with self.subTest(path=label):
                self.assertEqual([s.name for s in registry.tools()], ["impl"])
                self.assertEqual(registry.parity_defects, [])

    def test_stub_without_a_tool_table_yields_an_empty_registry(self):
        for label, mcp in (
            ("no manager", types.SimpleNamespace()),
            ("no table", types.SimpleNamespace(_tool_manager=types.SimpleNamespace())),
            ("empty table", _mcp({})),
        ):
            with self.subTest(stub=label):
                registry = reg.build_registry(mcp, _roster({"a": "read"}))
                self.assertEqual(registry.tools(), [])
                # An empty surface is a stub, not drift: the roster tool is
                # not reported missing, matching the runtime roster warning.
                self.assertEqual(registry.parity_defects, [])

    def test_bare_function_entries_are_their_own_callable(self):
        fn = _tool("bare")
        registry = reg.build_registry(_mcp({"bare": fn}), _roster({"bare": "read"}))
        self.assertIs(registry.get("bare").callable, fn)
        self.assertIsNone(registry.get("bare").annotations)

    def test_a_legacy_top_level_table_is_read(self):
        # Matches the server's _registered_mcp_tool_names fallback, so the
        # roster warning keeps covering FastMCP versions with a top-level table.
        mcp = types.SimpleNamespace(_tools={"legacy": _entry(_tool("legacy"))})
        registry = reg.build_registry(mcp, _roster({"legacy": "read"}))
        self.assertEqual([s.name for s in registry.tools()], ["legacy"])

    def test_an_unusable_roster_yields_an_empty_registry(self):
        # Without tiers there is nothing to cross-reference and no runner set
        # to exclude; reporting every tool as a defect would be noise.
        mcp = _mcp({"a": _entry(_tool("a"))})
        for label, roster in (
            ("no roster", None),
            ("no tier table", types.SimpleNamespace(RUNNER_TOOLS=frozenset())),
            ("tier table not a mapping", types.SimpleNamespace(TOOL_TIERS=["a"], RUNNER_TOOLS=frozenset())),
        ):
            with self.subTest(roster=label):
                registry = reg.build_registry(mcp, roster)
                self.assertEqual(registry.tools(), [])
                self.assertEqual(registry.parity_defects, [])

    def test_tools_are_sorted_whatever_the_registration_order(self):
        registry = reg.ToolRegistry()
        for name in ("c", "a", "b"):
            registry.register(reg.ToolSpec(name, "read", None, _tool(name), "m"))
        self.assertEqual([spec.name for spec in registry.tools()], ["a", "b", "c"])

    def test_register_refuses_a_duplicate_name(self):
        registry = reg.ToolRegistry()
        spec = reg.ToolSpec("x", "read", None, _tool("x"), "m")
        registry.register(spec)
        with self.assertRaises(ValueError):
            registry.register(spec)


def _wrapping_pass(names):
    """A stub wrapper pass that rebinds ``tool.fn`` for the named tools only."""
    def apply(mcp, get_handler):
        for name, entry in mcp._tool_manager._tools.items():
            if name not in names:
                continue
            original = entry.fn

            @functools.wraps(original)
            def wrapped(*args, _fn=original, **kwargs):
                return _fn(*args, **kwargs)

            entry.fn = wrapped
    return apply


class ApplyMiddlewareTests(unittest.TestCase):
    def test_labels_record_the_passes_that_applied_in_order(self):
        mcp = _mcp({
            "all_three": _entry(_tool("all_three")),
            "cost_exempt": _entry(_tool("cost_exempt")),
            "untouched": _entry(_tool("untouched")),
        })
        untouched_fn = mcp._tool_manager._tools["untouched"].fn
        chain = (
            ("cost", _wrapping_pass({"all_three"})),
            ("lock", _wrapping_pass({"all_three", "cost_exempt"})),
            ("guard", _wrapping_pass({"all_three", "cost_exempt"})),
        )
        reg.apply_middleware(mcp, lambda: None, chain)
        table = mcp._tool_manager._tools

        self.assertEqual(getattr(table["all_three"].fn, reg.MIDDLEWARE_MARKER), ("cost", "lock", "guard"))
        self.assertEqual(getattr(table["cost_exempt"].fn, reg.MIDDLEWARE_MARKER), ("lock", "guard"))
        # A tool no pass replaced is neither rebound nor stamped.
        self.assertIs(table["untouched"].fn, untouched_fn)
        self.assertFalse(hasattr(table["untouched"].fn, reg.MIDDLEWARE_MARKER))

    def test_a_late_binding_entry_runs_whatever_the_name_is_bound_to_at_apply_time(self):
        # The chain in server_impl spells out each wrapper call through a
        # lambda, so rebinding the module-level wrapper name before the chain
        # runs changes which wrapper is applied.
        namespace = types.SimpleNamespace(wrapper=_wrapping_pass(set()))
        chain = (("lock", lambda mcp, get_handler: namespace.wrapper(mcp, get_handler)),)
        namespace.wrapper = _wrapping_pass({"tool"})
        mcp = _mcp({"tool": _entry(_tool("tool"))})

        reg.apply_middleware(mcp, lambda: None, chain)
        self.assertEqual(getattr(mcp._tool_manager._tools["tool"].fn, reg.MIDDLEWARE_MARKER), ("lock",))

    def test_a_wrapper_exception_propagates(self):
        def failing(mcp, get_handler):
            raise RuntimeError("wrapper failed")

        with self.assertRaisesRegex(RuntimeError, "wrapper failed"):
            reg.apply_middleware(_mcp({"tool": _entry(_tool("tool"))}), lambda: None, (("cost", failing),))

    def test_passes_receive_the_handler_accessor(self):
        seen = []
        get_handler = object()
        reg.apply_middleware(_mcp({}), get_handler, (("cost", lambda m, g: seen.append(g)),))
        self.assertEqual(seen, [get_handler])


class ModuleBoundaryTests(unittest.TestCase):
    def test_module_never_imports_server_impl_at_any_scope(self):
        source = (SCRIPTS_DIR / "mcp_tool_registry.py").read_text(encoding="utf-8")

        def imported(tree):
            names = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names.append(node.module)
            return names

        self.assertNotIn("server_impl", imported(ast.parse(source)))
        # Known-bad: the same scan must see a function-local import.
        mutated = source + "\n\ndef _probe():\n    import server_impl\n"
        self.assertIn("server_impl", imported(ast.parse(mutated)))

    def test_module_never_rebinds_a_tool_callable(self):
        # The provenance rule keys on `tool.fn` being rebound only inside the
        # three server_impl wrappers; this module stamps, it never rebinds,
        # in any spelling.
        def rebinds(source):
            found = []
            for node in ast.walk(ast.parse(source)):
                targets = []
                if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    for sub in ast.walk(target):
                        if isinstance(sub, ast.Attribute) and sub.attr == "fn" and isinstance(sub.ctx, ast.Store):
                            found.append(ast.unparse(node))
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "setattr"
                        and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and node.args[1].value == "fn"):
                    found.append(ast.unparse(node))
            return found

        source = (SCRIPTS_DIR / "mcp_tool_registry.py").read_text(encoding="utf-8")
        self.assertEqual(rebinds(source), [])
        for known_bad in ("entry.fn = fn", "setattr(entry, 'fn', fn)", "entry.fn, other = fn, 1"):
            with self.subTest(known_bad=known_bad):
                self.assertTrue(rebinds(source + f"\n\ndef _probe(entry, fn, other):\n    {known_bad}\n"))

    def test_registry_module_is_in_purge_set_and_imported_at_module_top(self):
        # A module-top public-name import is what 1y0h0's reload test proves;
        # the purge entry is what makes that import fresh after reload.
        def placement(source):
            tree = ast.parse(source)
            top_level = any(
                isinstance(node, ast.Import) and any(alias.name == "mcp_tool_registry" for alias in node.names)
                for node in tree.body
            )
            purge = next(
                node for node in ast.walk(tree)
                if isinstance(node, ast.Set)
                and any(isinstance(e, ast.Constant) and e.value == "sensor_runner" for e in node.elts)
            )
            present = any(isinstance(e, ast.Constant) and e.value == "mcp_tool_registry" for e in purge.elts)
            return top_level, present

        source = (SCRIPTS_DIR / "server_impl.py").read_text(encoding="utf-8")
        self.assertEqual(placement(source), (True, True))
        lazy = source.replace(
            "import mcp_tool_registry  # tool registry",
            "def _probe():\n    import mcp_tool_registry  # tool registry", 1)
        self.assertEqual(placement(lazy)[0], False, "the known-bad lazy import must be detected")


def _handler_digests(source: str) -> dict[str, str]:
    """SHA-256 of each ``@mcp.tool`` handler's source in ``register_mcp_surface``."""
    tree = ast.parse(source)
    lines = source.splitlines()
    surface = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "register_mcp_surface"
    )
    digests = {}
    for node in ast.walk(surface):
        if not isinstance(node, ast.FunctionDef):
            continue
        if not any(
            isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "tool"
            and isinstance(d.func.value, ast.Name) and d.func.value.id == "mcp"
            for d in node.decorator_list
        ):
            continue
        start = min(d.lineno for d in node.decorator_list)
        text = textwrap.dedent("\n".join(lines[start - 1:node.end_lineno]))
        digests[node.name] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return digests


class HandlerDigestTests(unittest.TestCase):
    def test_every_handler_matches_its_pre_change_digest(self):
        # AC-1: no handler body, name, parameter, docstring, decorator or
        # annotation changed; the name sets are identical.
        expected = json.loads(DIGEST_FIXTURE.read_text(encoding="utf-8"))["handlers"]
        source = (SCRIPTS_DIR / "server_impl.py").read_text(encoding="utf-8")
        actual = _handler_digests(source)
        self.assertEqual(sorted(actual), sorted(expected))
        self.assertEqual(actual, expected)
        self.assertGreater(len(actual), 0)

    def test_a_one_word_docstring_edit_changes_that_handler_digest(self):
        # Known-bad: the comparison must see a change confined to one
        # handler's docstring, and only that handler's digest may move.
        source = (SCRIPTS_DIR / "server_impl.py").read_text(encoding="utf-8")
        needle = "Return the repository root and implementation version info for this MCP server."
        self.assertEqual(source.count(needle), 1)
        before = _handler_digests(source)
        after = _handler_digests(source.replace(needle, needle.replace("Return", "Report"), 1))
        changed = sorted(name for name in before if before[name] != after.get(name))
        self.assertEqual(changed, ["wf_server_info"])


class RealSurfaceRegistryTests(_BootedSurface):
    def test_registry_names_and_tiers_match_the_roster(self):
        # AC-2: names equal the roster minus runner survivors, tiers match.
        registry = self.impl._TOOL_REGISTRY
        expected = set(self.roster.TOOL_TIERS) - set(self.roster.RUNNER_TOOLS)
        self.assertEqual({spec.name for spec in registry.tools()}, expected)
        for spec in registry.tools():
            self.assertEqual(spec.tier, self.roster.TOOL_TIERS[spec.name], spec.name)
        self.assertEqual(registry.parity_defects, [])

    def test_specs_hold_the_callables_fastmcp_serves(self):
        # The registry is built after the chain, so each spec's callable is
        # the wrapped one FastMCP actually serves.
        table = self.mcp._tool_manager._tools
        for spec in self.impl._TOOL_REGISTRY.tools():
            self.assertIs(spec.callable, table[spec.name].fn, spec.name)

    def test_marker_records_the_wrappers_that_applied(self):
        # AC-3: all three wrappers apply to wf_add_change; wf_prepare_wave is
        # cost-exempt, so it carries only the lock and the guard.
        registry = self.impl._TOOL_REGISTRY
        self.assertEqual(
            getattr(registry.get("wf_add_change").callable, reg.MIDDLEWARE_MARKER),
            ("cost", "lock", "guard"),
        )
        self.assertEqual(
            getattr(registry.get("wf_prepare_wave").callable, reg.MIDDLEWARE_MARKER),
            ("lock", "guard"),
        )

    def test_chain_is_declared_in_application_order(self):
        self.assertEqual([label for label, _ in self.impl.MIDDLEWARE], ["cost", "lock", "guard"])


class RosterWarningTests(unittest.TestCase):
    """The runtime roster warning, read from the registry: warning-only on
    stderr, silent for a clean roster and when the roster cannot load, and a
    registry build failure never stops registration."""

    def setUp(self):
        self.impl = load_server()
        try:
            from mcp.server.fastmcp import FastMCP
        except ImportError:
            self.skipTest("mcp package not installed")
        self.FastMCP = FastMCP
        self.real_load = self.impl._load_script
        self.real_roster = self.real_load("mcp_tool_roster")

    def _register(self, roster_loader=None):
        loader = roster_loader or self.real_load

        def load(name):
            return loader(name) if name == "mcp_tool_roster" else self.real_load(name)

        stderr = io.StringIO()
        with patch.object(self.impl, "_load_script", side_effect=load) as spy, contextlib.redirect_stderr(stderr):
            self.impl.register_mcp_surface(self.FastMCP("roster-warning-probe"), lambda: None)
        spy.assert_any_call("mcp_tool_roster")
        return stderr.getvalue()

    def test_drift_names_both_directions(self):
        tiers = dict(self.real_roster.TOOL_TIERS)
        del tiers["wf_help"]
        tiers["wf_ghost"] = "read"
        drifted = types.SimpleNamespace(TOOL_TIERS=tiers, RUNNER_TOOLS=self.real_roster.RUNNER_TOOLS)
        output = self._register(lambda name: drifted)
        self.assertIn("mcp_tool_roster drift", output)
        self.assertIn("registered-not-in-roster=['wf_help']", output)
        self.assertIn("roster-not-registered=['wf_ghost']", output)

    def test_a_clean_roster_is_silent(self):
        self.assertNotIn("mcp_tool_roster drift", self._register())
        self.assertEqual(self.impl._TOOL_REGISTRY.parity_defects, [])

    def test_a_roster_that_cannot_load_is_silent_and_leaves_an_empty_registry(self):
        def failing(name):
            raise ImportError("roster unavailable")

        self.assertNotIn("mcp_tool_roster drift", self._register(failing))
        self.assertEqual(self.impl._TOOL_REGISTRY.tools(), [])

    def test_a_registry_build_failure_never_stops_registration(self):
        with patch.object(self.impl.mcp_tool_registry, "build_registry", side_effect=RuntimeError("boom")) as build:
            output = self._register()
        build.assert_called_once()
        self.assertEqual(self.impl._TOOL_REGISTRY.tools(), [])
        self.assertNotIn("mcp_tool_roster drift", output)


_RELOAD_PROBE = r"""
import importlib, json, sys
sys.dont_write_bytecode = True
from mcp.server.fastmcp import FastMCP
import server_impl

def register():
    server_impl.register_mcp_surface(FastMCP("reload-probe"), lambda: None)
    return server_impl._TOOL_REGISTRY

import inspect, os
first = register()
old_spec_class = type(first.get("wf_help"))
old_callable = first.get("wf_help").callable
old_code = {s.name: inspect.unwrap(s.callable).__code__ for s in first.tools()}
path = server_impl.__file__
scratch = os.environ["WF_RELOAD_SCRATCH"]
assert os.path.realpath(path).startswith(os.path.realpath(scratch) + os.sep), path
source = open(path, encoding="utf-8").read()
needle = "Return a structured MCP workflow catalogue or a goal-specific recommended chain."
assert source.count(needle) == 1
with open(path, "w", encoding="utf-8") as handle:
    handle.write(source.replace(needle, "RELOAD-PROBE-DESCRIPTION " + needle, 1))
importlib.reload(server_impl)
second = register()
spec = second.get("wf_help")
print(json.dumps({
    "fresh_class": not isinstance(spec, old_spec_class),
    "fresh_callable": spec.callable is not old_callable,
    "description_updated": "RELOAD-PROBE-DESCRIPTION" in (spec.callable.__doc__ or ""),
    "any_old_instance": any(isinstance(s, old_spec_class) for s in second.tools()),
    "any_old_code": any(inspect.unwrap(s.callable).__code__ is old_code.get(s.name) for s in second.tools()),
}))
"""


class ReloadFreshnessTests(unittest.TestCase):
    def test_reload_rebuilds_the_registry_from_fresh_code(self):
        # AC-4, in a subprocess over a scratch copy: the live server_impl.py is
        # never edited, and the shared in-process module is never reloaded.
        try:
            import mcp.server.fastmcp  # noqa: F401
        except ImportError:
            self.skipTest("mcp package not installed")
        with tempfile.TemporaryDirectory() as tmp:
            scratch = Path(tmp) / "scripts"
            shutil.copytree(
                SCRIPTS_DIR, scratch,
                ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"),
            )
            result = subprocess.run(
                [sys.executable, "-B", "-c", _RELOAD_PROBE],
                cwd=scratch, capture_output=True, text=True, timeout=300,
                env={"PYTHONPATH": str(scratch), "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1",
                     "WF_RELOAD_SCRATCH": str(scratch)},
            )
            self.assertEqual(result.returncode, 0, result.stderr[-2000:])
            observed = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(observed, {
            "fresh_class": True,
            "fresh_callable": True,
            "description_updated": True,
            "any_old_instance": False,
            "any_old_code": False,
        })


if __name__ == "__main__":
    unittest.main()
