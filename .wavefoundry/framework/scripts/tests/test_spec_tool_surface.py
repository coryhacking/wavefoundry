"""Exercise the wire schema and dispatch used by a real FastMCP caller."""
import asyncio
from pathlib import Path
import tempfile
import unittest

from declaration_support import base_declaration
from record_layout_support import default_profile_only
from server_tools_support import _make_repo, load_server


class SpecToolSurfaceTests(unittest.TestCase):
    def setUp(self):
        from mcp.server.fastmcp import FastMCP
        self.surface_class = FastMCP
        self.server = load_server()
        self.root = _make_repo(Path(self.enterContext(tempfile.TemporaryDirectory())))
        self.handler = self.server.build_handler(self.root)
        self.addCleanup(self.handler.close)

    def register(self, **declaration):
        self.enterContext(base_declaration(**declaration))
        self.surface = self.surface_class("spec-surface")
        self.server.register_mcp_surface(self.surface, lambda: self.handler)
        self.table = self.surface._tool_manager._tools

    def call(self, name, **arguments):
        return asyncio.run(self.surface._tool_manager.call_tool(name, arguments))

    @default_profile_only("verifies the shipped spec header vocabulary in generated documents")
    def test_stock_create_returns_and_writes_the_same_spec_identity(self):
        self.register()
        for template in ("Spec", "Change"):
            with self.subTest(template=template):
                plans = self.root / "docs" / "plans"
                plans.mkdir(exist_ok=True)
                (plans / "plan-template.md").write_text(
                    f"# Delivery\n\n{template} ID: `<id-prefix>-<kind> <slug>`\n"
                    f"{template} Status: `planned`\n",
                    encoding="utf-8",
                )
                made = self.call("wf_new_spec", slug=f"stock-{template.lower()}-template")["data"]
                spec_id = made["spec_id"]
                self.assertNotIn("change_id", made)
                lines = (plans / f"{spec_id}.md").read_text(encoding="utf-8").splitlines()
                self.assertIn(f"Spec ID: `{spec_id}`", lines)
                self.assertIn("Spec Status: `planned`", lines)
                self.assertFalse(any(line.startswith(("Change ID:", "Change Status:")) for line in lines))
                fetched = self.call("wf_get_spec", spec_id=spec_id)["data"]["change"]
                self.assertEqual(fetched["spec_id"], spec_id)
                self.assertNotIn("change_id", fetched)

    def test_stock_caller_uses_spec_id_in_requests_and_results(self):
        from mcp.server.fastmcp.exceptions import ToolError
        self.register()
        before = set(self.root.rglob("*"))
        for old, new in self.server.mcp_tool_extensions.SPEC_TOOL_NAMES.items():
            with self.subTest(old=old), self.assertRaisesRegex(ToolError, "Unknown tool"):
                self.call(old)
            self.assertIn(new, self.table)
            self.assertNotIn("change_id", self.table[new].parameters["properties"])
        self.assertEqual(set(self.root.rglob("*")), before)
        help_data = self.call("wf_help", goal="plan_spec")["data"]
        self.assertIn("wf_get_spec", help_data["recommended_chain"])
        made = self.call("wf_new_spec", slug="readable-wire-contract")["data"]
        spec = made["spec_id"]
        self.assertIn("-change", spec)
        wave = self.call("wf_create_wave", slug="wire", mode="create")["data"]["wave_id"]
        args = {"wave_id": wave, "spec_id": spec}
        for name in ("wf_add_spec", "wf_remove_spec", "wf_add_spec"):
            result = self.call(name, **args, mode="create")
            self.assertEqual(result["status"], "ok", result)
            self.assertEqual(result["data"]["spec_id"], spec)
            self.assertNotIn("change_id", result["data"])
        one = self.call("wf_get_spec", spec_id=spec)["data"]
        self.assertEqual(one["change"]["spec_id"], spec)
        self.assertNotIn("change_id", one["change"])
        bulk = self.call("wf_get_spec", wave_id=wave)["data"]["changes"]
        self.assertEqual([row["spec_id"] for row in bulk], [spec])
        original = {p: p.read_bytes() for p in (self.root / "docs").rglob("*.md")}
        result = self.call("wf_close_spec", **args, mode="dry_run")
        self.assertEqual(result["status"], "error")
        self.assertIn("wave_not_open", {diag["code"] for diag in result["diagnostics"]})
        canonical = self.server.wf_close_change_response(self.root, wave, spec, mode="dry_run")
        self.assertEqual(result["diagnostics"], canonical["diagnostics"])
        self.assertEqual(result["data"]["spec_id"], canonical["data"]["change_id"])
        self.assertIn("wf_current_wave", result["next_tools"])
        self.assertEqual({p: p.read_bytes() for p in original}, original)

    def test_existing_downstream_name_keeps_its_parameter_and_hints(self):
        self.register(EXTENSION_TOOL_ALIASES={"wf_get_spec": "wf_get_change"})
        schema = self.table["wf_get_spec"].parameters["properties"]
        self.assertIn("change_id", schema)
        self.assertNotIn("spec_id", schema)
        made = self.call("wf_new_spec", slug="distribution-schema")
        spec = made["data"]["spec_id"]
        self.assertIn("wf_get_spec(change_id=", made["usage"])
        got = self.call("wf_get_spec", change_id=spec)
        self.assertEqual(got["data"]["change"]["change_id"], spec)
        self.assertNotIn("wf_get_change", self.table)

    def test_established_calls_accept_both_ids_and_keep_existing_result_keys(self):
        self.register()
        made = self.call("wf_new_bug", slug="identifier-compatibility")["data"]
        spec = made["spec_id"]
        self.assertEqual(made["change_id"], spec)
        for kind in ("enhancement", "refactor", "documentation", "tech_debt", "task", "maintenance", "operations"):
            with self.subTest(kind=kind):
                created = self.call("wf_new_" + kind, slug="identifier-" + kind.replace("_", "-"))
                self.assertEqual(created["status"], "ok", created)
                self.assertEqual(created["data"]["change_id"], created["data"]["spec_id"])
        self.assertEqual(self.call("wf_new_feature", slug="retired")["status"], "error")
        plans = self.call("wf_list_plans")["data"]["plans"]
        self.assertIn((spec, spec), [(row["id"], row["spec_id"]) for row in plans])
        wave = self.call("wf_create_wave", slug="id-alias", mode="create")["data"]["wave_id"]
        self.call("wf_add_spec", wave_id=wave, spec_id=spec, mode="create")
        for name in ("wf_current_wave", "wf_list_waves"):
            rows = self.call(name)["data"]["waves"]
            members = next(row for row in rows if row["wave_id"] == wave)["changes"]
            self.assertEqual([(row["id"], row["spec_id"]) for row in members], [(spec, spec)])
        for tool, item in (("wf_mark_ac", {"ac_id": "AC-1"}), ("wf_mark_task", {"task": "[Concrete implementation step]"})):
            args = {**item, "wave_id": wave, "state": "x"}
            schema = self.table[tool].parameters
            self.assertIn("change_id", schema["properties"])
            self.assertIn("spec_id", schema["properties"])
            old = self.call(tool, change_id=spec, **args)
            new = self.call(tool, spec_id=spec, **args)
            self.assertEqual(old["status"], new["status"])
            for result in (old, new, self.call(tool, change_id=spec, spec_id=spec, **args)):
                self.assertEqual(result["data"]["spec_id"], spec)
                self.assertEqual(result["data"]["change_id"], spec)
                self.assertNotEqual(result["diagnostics"][0]["code"], "invalid_arguments")
            for legacy in ("other", ""):
                refused = self.call(tool, spec_id=spec, change_id=legacy, mode="create", **args)
                self.assertEqual(refused["status"], "error")
                self.assertEqual(refused["diagnostics"][0]["code"], "invalid_arguments")

    def test_provenance_rows_expose_spec_id_without_rewriting_recorded_reasoning(self):
        from unittest.mock import patch
        self.register()
        resolver = self.server._load_script("commit_provenance")
        reasoning = ['The response contained {"change_id": "earlier"}']
        row = {"change_id": "1abce-bug sample", "decisions": reasoning}
        with patch.object(resolver, "provenance_for_sha", return_value={
            "resolved": True, "waves": ["1abcd"], "provenance": [row],
        }):
            result = self.call("code_commit_provenance", commit="a" * 40)
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["data"]["provenance"], [{**row, "spec_id": row["change_id"]}])
        self.assertEqual(set(row), {"change_id", "decisions"})

    def test_declared_alias_for_unchanged_operation_keeps_original_contract(self):
        self.register(EXTENSION_TOOL_ALIASES={"wf_tick_task": "wf_mark_task", "wf_bug": "wf_new_bug"})
        self.assertIn("spec_id", self.table["wf_mark_task"].parameters["properties"])
        alias = self.table["wf_tick_task"].parameters["properties"]
        self.assertIn("change_id", alias)
        self.assertNotIn("spec_id", alias)
        created = self.call("wf_bug", slug="declared-creator")["data"]
        self.assertIn("change_id", created)
        self.assertNotIn("spec_id", created)

    def test_collision_preserves_unrelated_binding_and_hides_only_its_stock_route(self):
        self.register(EXTENSION_TOOL_ALIASES={"wf_get_spec": "wf_help", "wf_detach": "wf_remove_change"},
                      EXTENSION_HIDDEN_TOOLS=("wf_remove_change",))
        self.assertIn("goal", self.table["wf_get_spec"].parameters["properties"])
        self.assertNotIn("wf_remove_spec", self.table)
        output = self.call("wf_new_spec", slug="occupied")
        self.assertNotIn("wf_get_spec", output["next_tools"])
        self.assertIn("distribution binding", output["usage"])
        self.assertIn("wf_close_spec", self.table)
        # The colliding spelling still serves the downstream help operation.
        help_result = self.call("wf_get_spec", goal="unrecognized")
        self.assertIn("wf_get_spec", help_result["next_tools"])
        self.assertEqual(help_result["usage"], "wf_get_spec()")

    def test_owner_can_explicitly_register_a_retired_spelling(self):
        self.register(EXTENSION_TOOL_ALIASES={"wf_get_change": "wf_get_change"})
        made = self.call("wf_new_spec", slug="old-alias")
        self.assertEqual(self.call("wf_get_change", change_id=made["data"]["spec_id"])["status"], "ok")
        self.assertEqual(self.call("wf_get_spec", spec_id=made["data"]["spec_id"])["status"], "ok")

    def test_held_permission_withholds_wire_name_and_supplies_remedy(self):
        folder = self.root / ".claude"
        folder.mkdir()
        (folder / "settings.json").write_text('{"permissions":{"deny":["mcp__wavefoundry__wf_get_change"]}}')
        self.register()
        self.assertNotIn("wf_get_spec", self.table)
        made = self.call("wf_new_spec", slug="held-route")
        self.assertNotIn("wf_get_spec", made["next_tools"])
        self.assertIn("settings.json", made["usage"])


class AliasedSpecPermissionTests(unittest.TestCase):
    """Exercise a distribution's override and its public alias across host policy and MCP."""

    def setUp(self):
        from server_tools_support import _make_repo, load_server
        self.server = load_server()
        import mcp_tool_roster
        self.roster = mcp_tool_roster
        from test_spec_tool_permissions import isolate_host_policy
        isolate_host_policy(self)
        self.root = _make_repo(Path(self.enterContext(tempfile.TemporaryDirectory())))
        (self.root / ".wavefoundry/framework/scripts").mkdir(parents=True, exist_ok=True)
        self.handler = self.server.build_handler(self.root)
        self.addCleanup(self.handler.close)

    def declaration(self, old, new=None):
        aliases = {new: old} if new else {}
        return base_declaration(
            EXTENSION_MODULES=("delivery_tools",),
            EXTENSION_OVERRIDES={"delivery_tools": (old,)},
            EXTENSION_TOOL_ALIASES=aliases,
        )

    def register(self, old):
        from mcp.server.fastmcp import FastMCP
        from types import SimpleNamespace
        from unittest import mock

        def register_override(mcp, get_handler):
            @mcp.tool(name=old)
            def current(wave_id: str, change_id: str, mode: str = "dry_run", **kwargs):
                return {"status": "ok", "next_tools": [old], "data": {"id": change_id}}

        surface = FastMCP("permission-fixture")
        module = SimpleNamespace(register=register_override)
        with mock.patch.object(self.server, "_load_extension_module",
                               return_value=(module, self.root / "delivery_tools.py", "a" * 64)):
            self.server.register_mcp_surface(surface, lambda: self.handler)
        return surface._tool_manager

    def test_unverified_alias_is_withheld_with_recovery_and_hints_use_served_name(self):
        import asyncio
        import spec_tool_permissions as stp
        import upgrade_wavefoundry
        old, new = "wf_close_change", "wf_close_spec"
        with self.declaration(old, new):
            self.assertTrue(stp._requires_review(self.root))
            remedy = self.roster.spec_permission_holds(self.root)[new]
            self.assertIn(remedy, upgrade_wavefoundry._spec_tool_permission_summary(self.root)["spec_tool_permission_holds"])
            manager = self.register(old)
            self.assertNotIn(new, manager._tools)
            self.assertEqual(self.server._EXTENSION_PROVENANCE["spec_tool_remedies"][new], remedy)
            args = {"wave_id": "abcde", "change_id": "bcdef"}
            result = asyncio.run(manager.call_tool(old, args))
            self.assertIn(old, result["next_tools"], result)
            routes = self.roster.mcp_tool_extensions.spec_permission_routes()
            stp.record_verification(self.root, routes, self.roster.MCP_RULE_PREFIX)
            self.assertFalse(self.roster.spec_permission_holds(self.root))
            manager = self.register(old)
            self.assertIn("change_id", manager._tools[new].parameters["properties"])
            self.assertEqual(asyncio.run(manager.call_tool(new, args))["data"]["id"], "bcdef")

    def test_unaliased_override_keeps_stock_permission_behavior(self):
        old, new = "wf_close_change", "wf_close_spec"
        with self.declaration(old):
            ext = self.roster.mcp_tool_extensions
            self.assertEqual(ext.spec_permission_routes(), ext.stock_spec_routes())
            self.assertNotIn(new, self.roster.spec_permission_holds(self.root))
            served = sorted(self.register(old)._tools)
            self.assertNotIn(new, served)
            from unittest.mock import patch
            with patch.object(ext, "spec_permission_routes", ext.stock_spec_routes):
                self.assertEqual(served, sorted(self.register(old)._tools))
