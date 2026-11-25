"""Host permissions retain their original owner, tier and scope across a rename."""
import json
from pathlib import Path
import tempfile
import unittest

from declaration_support import base_declaration
import mcp_tool_roster as roster
import render_platform_surfaces as surfaces
from spec_tool_permissions import CLAUDE_LOCAL, CLAUDE_PROJECT, CODEX_PROJECT, CURSOR_PROJECT


class SpecPermissionTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(base_declaration())
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.prefix = roster.MCP_RULE_PREFIX
        self.old, self.new = [self.prefix + x for x in ("wf_get_change", "wf_get_spec")]

    def write(self, rel, data):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
        return path

    def render(self):
        surfaces.render_claude_permissions(self.root)
        return json.loads((self.root / CLAUDE_PROJECT).read_text(encoding="utf-8"))

    def holds(self):
        return roster.spec_permission_holds(self.root)

    def test_project_ask_and_personal_deny_must_each_match(self):
        self.write(CLAUDE_PROJECT, {"permissions": {"ask": [self.old, self.new]}})
        private = self.write(CLAUDE_LOCAL, {"permissions": {"deny": [self.old]}})
        before = private.read_bytes()
        self.assertIn("wf_get_spec", self.holds())
        self.assertNotIn(self.new, self.render()["permissions"]["allow"])
        self.assertEqual(private.read_bytes(), before)
        self.write(CLAUDE_LOCAL, {"permissions": {"deny": [self.old, self.new]}})
        self.assertNotIn("wf_get_spec", self.holds())

    def test_private_allow_stays_private(self):
        self.write(CLAUDE_LOCAL, {"permissions": {"allow": [self.old, self.new]}})
        self.assertFalse(self.holds())
        settings = self.render()
        self.assertNotIn(self.new, settings["permissions"]["allow"])
        self.assertNotIn(self.new, settings[surfaces.PERMISSIONS_PROVENANCE_KEY])

    def test_renderer_migrates_only_its_existing_grant_and_preserves_pending_provenance(self):
        self.write(CLAUDE_PROJECT, {"permissions": {"allow": [self.old, "Bash(ls)"]},
                                   surfaces.PERMISSIONS_PROVENANCE_KEY: [self.old]})
        self.write(CLAUDE_LOCAL, {"permissions": {"ask": [self.old]}})
        settings = self.render()
        self.assertIn(self.old, settings[surfaces.PERMISSIONS_PROVENANCE_KEY])
        self.assertNotIn(self.new, settings["permissions"]["allow"])
        self.write(CLAUDE_LOCAL, {"permissions": {"ask": [self.new]}})
        settings = self.render()
        self.assertIn(self.new, settings[surfaces.PERMISSIONS_PROVENANCE_KEY])
        self.assertNotIn(self.old, settings["permissions"]["allow"])
        self.assertIn("Bash(ls)", settings["permissions"]["allow"])

    def test_codex_controls_withhold_only_affected_routes_and_need_matching_values(self):
        server = self.prefix.removeprefix("mcp__").removesuffix("__")
        policy = f'[mcp_servers.{server}]\ndisabled_tools = ["wf_close_change"]\n' + (
            f'[mcp_servers.{server}.tools.wf_new_change]\napproval_mode = "prompt"\n'
            f'[mcp_servers.{server}.tools.wf_new_spec]\napproval_mode = "approve"\n')
        self.write(CODEX_PROJECT, policy)
        self.assertEqual(set(self.holds()), {"wf_new_spec", "wf_close_spec"})
        self.write(CODEX_PROJECT, policy.replace('"approve"', '"prompt"').replace(
            '["wf_close_change"]', '["wf_close_change","wf_close_spec"]'))
        self.assertFalse(self.holds())

    def test_unreadable_policy_and_opaque_host(self):
        self.write(CURSOR_PROJECT, {"example": self.old})
        self.assertEqual(set(self.holds()), {"wf_get_spec"})
        self.write(CLAUDE_LOCAL, "{")
        self.assertEqual(len(self.holds()), 5)

    def test_new_low_risk_tier_membership_is_limited_to_creation(self):
        low = set(roster.allow_rules(include_low_risk=True)) - set(roster.allow_rules())
        self.assertIn(self.prefix + "wf_new_spec", low)
        for name in ("wf_new_change", "wf_add_spec", "wf_remove_spec", "wf_close_spec"):
            self.assertNotIn(self.prefix + name, low)

    def test_external_policy_confirmation_is_scoped_and_never_overrides_deny(self):
        from spec_tool_permissions import acknowledge
        import upgrade_wavefoundry
        from unittest import mock
        (self.root / ".wavefoundry/framework").mkdir(parents=True)
        self.assertEqual(len(self.holds()), 5)
        self.assertEqual(len(upgrade_wavefoundry._spec_tool_permission_summary(self.root)["spec_tool_permission_holds"]), 5)
        self.assertIn("--confirm-effective-host-rules", self.holds()["wf_get_spec"])
        args = ["--root", str(self.root), "--tool", "wf_get_spec", "--confirm-effective-host-rules"]
        self.assertEqual(acknowledge(args), 0)
        self.assertEqual(acknowledge(args), 0)
        self.assertNotIn("wf_get_spec", self.holds())
        self.assertEqual(len(self.holds()), 4)
        with mock.patch("spec_tool_permissions.platform.node", return_value="different-workstation"):
            self.assertEqual(len(self.holds()), 5)
        self.write(CLAUDE_LOCAL, {"permissions": {"deny": [self.old]}})
        self.assertIn("deny", self.holds()["wf_get_spec"])

    def test_fresh_install_uses_only_live_template_and_unknown_upgrade_stays_withheld(self):
        template = Path(__file__).resolve().parents[2] / "install/install-log.template.md"
        self.write(".wavefoundry/framework/install/install-log.template.md", template.read_text())
        self.assertEqual(len(self.holds()), 5)
        self.write(".wavefoundry/install-log.md", "# Old install state\n")
        self.assertEqual(len(self.holds()), 5)
        self.write(".wavefoundry/install-log.md", template.read_text())
        self.assertFalse(self.holds())
        self.write(CLAUDE_PROJECT, {"permissions": {"ask": [self.old]}})
        self.assertEqual(set(self.holds()), {"wf_get_spec"})

    def test_wildcard_and_argument_controls_do_not_grant_a_new_route(self):
        self.write(CLAUDE_LOCAL, {"permissions": {"deny": [self.prefix + "wf_*_change"]}})
        self.assertEqual(len(self.holds()), 5)
        self.write(CLAUDE_LOCAL, {"permissions": {"deny": [self.prefix + "wf_get_*"]}})
        self.assertFalse(self.holds())
        self.write(CLAUDE_LOCAL, {"permissions": {"ask": [self.old + "(change_id:abcde)"]}})
        self.assertEqual(set(self.holds()), {"wf_get_spec"})
