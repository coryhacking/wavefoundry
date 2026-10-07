"""The shared base-declaration helper and the FastMCP-backed double (wave 1zim5, change 1zim4).

* The helper patches every declaration constant, on every loaded copy of the
  declaration module, to the shipped empty base plus the test's own
  declaration; resets the server state computed from a declaration; and
  restores both on exit.
* The double is a real ``FastMCP``: a declared alias (plain or
  parameter-mapped) is served from it as from the server, and it records the
  functions the server registers.
"""
from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import mcp_tool_extensions  # noqa: E402
from declaration_support import (  # noqa: E402
    DECLARATION_CONSTANTS,
    RecordingFastMCP,
    apply_base_declaration,
    base_declaration,
    base_declaration_source,
    declaration_profile_mismatch,
    served_functions,
)
from record_layout_support import (  # noqa: E402
    PROFILES_DIR,
    SHIPPED_DECLARATION,
    TEST_PROFILE_ENV,
    expected_profile,
    load_profile,
)

AMBIENT = {"wf_ambient_help": "wf_help"}


class BaseDeclarationTests(unittest.TestCase):
    def setUp(self):
        # An ambient declaration, as a distribution ships one, on the module
        # and on a second copy another module still holds.
        self.held = types.ModuleType("mcp_tool_extensions_held_copy")
        for name in DECLARATION_CONSTANTS:
            setattr(self.held, name, getattr(mcp_tool_extensions, name))
        self.holder = types.ModuleType("declaration_support_holder_probe")
        self.holder.mcp_tool_extensions = self.held
        sys.modules[self.holder.__name__] = self.holder
        self.addCleanup(sys.modules.pop, self.holder.__name__, None)
        self.saved = {name: getattr(mcp_tool_extensions, name) for name in DECLARATION_CONSTANTS}
        self.addCleanup(lambda: [setattr(mcp_tool_extensions, n, v) for n, v in self.saved.items()])
        for module in (mcp_tool_extensions, self.held):
            module.EXTENSION_TOOL_ALIASES = dict(AMBIENT)
            module.EXTENSION_HIDDEN_TOOLS = ("wf_help",)

    def test_every_copy_gets_the_base_plus_the_test_declaration_and_is_restored(self):
        with base_declaration(EXTENSION_TOOL_ALIASES={"wf_alias_help": "wf_help"}):
            for module in (mcp_tool_extensions, self.held):
                self.assertEqual(module.EXTENSION_TOOL_ALIASES, {"wf_alias_help": "wf_help"})
                self.assertEqual(module.EXTENSION_HIDDEN_TOOLS, ())
                for name in DECLARATION_CONSTANTS:
                    if name != "EXTENSION_TOOL_ALIASES":
                        self.assertEqual(getattr(module, name), SHIPPED_DECLARATION[name], name)
        for module in (mcp_tool_extensions, self.held):
            self.assertEqual(module.EXTENSION_TOOL_ALIASES, AMBIENT)
            self.assertEqual(module.EXTENSION_HIDDEN_TOOLS, ("wf_help",))

    def test_the_empty_base_is_undeclared_and_a_copy(self):
        with base_declaration():
            self.assertFalse(mcp_tool_extensions.declared())
            self.assertEqual(mcp_tool_extensions.served_name_map(), {})
            mcp_tool_extensions.EXTENSION_TOOL_TIERS["x"] = "read"
        self.assertEqual(SHIPPED_DECLARATION["EXTENSION_TOOL_TIERS"], {})

    def test_bound_to_a_test_cleanup(self):
        case = unittest.TestCase()
        apply_base_declaration(case)
        self.assertEqual(mcp_tool_extensions.EXTENSION_TOOL_ALIASES, {})
        case.doCleanups()
        self.assertEqual(mcp_tool_extensions.EXTENSION_TOOL_ALIASES, AMBIENT)

    def test_server_state_from_a_declaration_is_reset(self):
        impl = types.ModuleType("server_impl")
        impl._EXTENSION_PROVENANCE = {"aliases": AMBIENT}
        impl._EXTENSION_REPLACED_CORE = {"wf_help": object()}
        key = "declaration_support_probe.server_impl"
        sys.modules[key] = impl
        self.addCleanup(sys.modules.pop, key, None)
        with base_declaration():
            self.assertIsNone(impl._EXTENSION_PROVENANCE)
            self.assertEqual(impl._EXTENSION_REPLACED_CORE, {})
            impl._EXTENSION_PROVENANCE = {"built": "inside"}
        self.assertIsNone(impl._EXTENSION_PROVENANCE)

    def test_unknown_names_are_refused(self):
        with self.assertRaises(ValueError):
            with base_declaration(EDIT_GATE_TOOLS=frozenset()):
                pass
        with self.assertRaises(ValueError):
            base_declaration_source(EXTENSION_ALIASES={})

    def test_source_form_overrides_the_module_above_it(self):
        namespace: dict = {}
        exec("EXTENSION_TOOL_ALIASES = {'wf_ambient_help': 'wf_help'}\nEXTENSION_HIDDEN_TOOLS = ('wf_help',)\n"
             + base_declaration_source(EXTENSION_TOOL_TIERS={"acme_x": "read"}), namespace)
        self.assertEqual({name: namespace[name] for name in DECLARATION_CONSTANTS},
                         {**SHIPPED_DECLARATION, "EXTENSION_TOOL_TIERS": {"acme_x": "read"}})

    def test_declaration_profile_match(self):
        # The resolver is injected (an explicit environment and a directory
        # holding only the framework's assets), so this holds under every run
        # mode and beside any asset a distribution marks active (change 1zima).
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("second", "declared"):
                shutil.copy2(PROFILES_DIR / f"{name}.json", Path(tmp) / f"{name}.json")
            # The assets' module_files sources (wave 1zyb3, change 1zxnu).
            for source in PROFILES_DIR.glob("*.py"):
                shutil.copy2(source, Path(tmp) / source.name)
            shipped = expected_profile({}, tmp)
            run_declared = expected_profile({TEST_PROFILE_ENV: "declared"}, tmp)
        with base_declaration():
            self.assertIsNone(declaration_profile_mismatch(shipped))
            self.assertIn("'declared' from WAVEFOUNDRY_TEST_PROFILE", declaration_profile_mismatch(run_declared))
        declared = load_profile("declared")["modules"]["mcp_tool_extensions"]
        with base_declaration(**declared):
            self.assertIsNone(declaration_profile_mismatch(run_declared))
            self.assertIn("(the shipped defaults)", declaration_profile_mismatch(shipped))
        # The ambient declaration has no asset: named, with each copy's differing constant.
        message = declaration_profile_mismatch(shipped)
        self.assertIn("mcp_tool_extensions.EXTENSION_TOOL_ALIASES is {'wf_ambient_help': 'wf_help'}, expected {}",
                      message)
        self.assertIn("mcp_tool_extensions.EXTENSION_HIDDEN_TOOLS is ['wf_help'], expected []", message)


class RecordingFastMCPTests(unittest.TestCase):
    def setUp(self):
        try:
            from server_tools_support import load_server
            self.impl = load_server()
            from mcp.server.fastmcp.tools import Tool
        except ImportError:
            self.skipTest("mcp package not installed")
        self.Tool = Tool
        import tempfile
        from server_tools_support import _make_repo
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = _make_repo(Path(tmp.name))

    def test_a_declared_surface_is_served_from_the_double(self):
        # The double is what the declaration machinery needs: Tool objects.
        # Wave 1zyb3 (change 1zxnu): the asset's module parts need its module
        # file beside the server, which only a copied tree has, so this
        # in-process check keeps the aliases and the hidden name.
        module_parts = ("EXTENSION_MODULES", "EXTENSION_HELPER_MODULES", "EXTENSION_TOOL_PREFIXES",
                        "EXTENSION_TOOL_TIERS", "EXTENSION_REPLACEMENTS")
        declared = {name: tuple(value) if isinstance(SHIPPED_DECLARATION[name], tuple) else value
                    for name, value in load_profile("declared")["modules"]["mcp_tool_extensions"].items()
                    if name not in module_parts}
        apply_base_declaration(self, **declared)
        mcp = RecordingFastMCP()
        self.impl.register_mcp_surface(mcp, lambda: types.SimpleNamespace(root=self.root))
        table = mcp._tool_manager._tools
        hidden = set(declared.get("EXTENSION_HIDDEN_TOOLS", ()))
        self.assertTrue(hidden)
        for alias, canonical in declared["EXTENSION_TOOL_ALIASES"].items():
            self.assertIsInstance(table[alias], self.Tool)
            if canonical in hidden:
                self.assertNotIn(canonical, table)
            else:
                self.assertIn(canonical, table)
        mapped = next(iter(declared["EXTENSION_TOOL_PARAMETERS"]))
        spec = declared["EXTENSION_TOOL_PARAMETERS"][mapped]
        properties = table[mapped].parameters["properties"]
        for alias_param, canonical_param in spec["rename"].items():
            self.assertIn(alias_param, properties)
            self.assertNotIn(canonical_param, properties)
        for fixed in spec["fixed"]:
            self.assertNotIn(fixed, properties)
        # Raw registrations are recorded beside the served (wrapped) callables.
        self.assertIn("wf_help", mcp.tools)
        self.assertNotIn(next(iter(declared["EXTENSION_TOOL_ALIASES"])), mcp.tools)
        self.assertIs(served_functions(mcp)["wf_help"], table["wf_help"].fn)
        self.assertIn("wavefoundry://codebase-map", mcp.resource_uris)
        self.assertIs(mcp.resource_functions[mcp.resource_uris["wavefoundry://codebase-map"].__name__],
                      mcp.resource_uris["wavefoundry://codebase-map"])

    def test_the_stock_surface_on_the_double_has_no_alias(self):
        apply_base_declaration(self)
        mcp = RecordingFastMCP()
        self.impl.register_mcp_surface(mcp, lambda: types.SimpleNamespace(root=self.root))
        declared = load_profile("declared")["modules"]["mcp_tool_extensions"]
        self.assertFalse(set(declared["EXTENSION_TOOL_ALIASES"]) & set(mcp._tool_manager._tools))
        self.assertEqual(set(mcp.tools), set(mcp._tool_manager._tools))


if __name__ == "__main__":
    unittest.main()
