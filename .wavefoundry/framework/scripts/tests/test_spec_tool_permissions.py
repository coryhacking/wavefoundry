"""Host permissions retain their original owner, tier and scope across a rename."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest import mock

from declaration_support import base_declaration
import mcp_tool_roster as roster
import render_platform_surfaces as surfaces
import spec_tool_permissions as stp
from spec_tool_permissions import CLAUDE_LOCAL, CLAUDE_PROJECT, CODEX_PROJECT, CURSOR_PROJECT

SCRIPTS = Path(__file__).resolve().parents[1]
# The worker's environment as the runner started it, before any test patches it.
_WORKER_ENV = dict(os.environ)


def isolate_host_policy(test):
    """Point every outside policy location at a temporary folder for ``test``.

    Returns the folder. No test in this module reads the real home or system
    policy files (wave 24buu, change 24ax3)."""
    outside = Path(test.enterContext(tempfile.TemporaryDirectory())).resolve()
    test.enterContext(mock.patch.dict(os.environ, {
        "HOME": str(outside / "home"), "USERPROFILE": str(outside / "home"),
        "CLAUDE_CONFIG_DIR": str(outside / "claude"), "CODEX_HOME": str(outside / "codex"),
        "WAVEFOUNDRY_MANAGED_SETTINGS_PATH": str(outside / "managed" / "managed-settings.json")}))
    return outside


class SpecPermissionTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(base_declaration())
        self.outside = isolate_host_policy(self)
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

    def test_rules_follow_declared_rename_in_render_and_migration(self):
        for old, new in (("wf_close_change", "wf_close_spec"), ("wf_remove_change", "wf_remove_spec")):
            with self.subTest(new=new), base_declaration(
                    EXTENSION_MODULES=("delivery_tools",), EXTENSION_OVERRIDES={"delivery_tools": (old,)},
                    EXTENSION_TOOL_ALIASES={new: old}):
                path = self.root / CLAUDE_PROJECT
                path.parent.mkdir(exist_ok=True)
                path.write_text(json.dumps({"permissions": {
                    "deny": [P + old], "ask": [P + old + "(change_id:abcde)"]}}))
                self.assertIn(new, roster.spec_permission_holds(self.root))
                surfaces.migrate_spec_tool_permissions(self.root)
                surfaces.render_claude_permissions(self.root)
                rules = json.loads(path.read_text())["permissions"]
                for tier, suffix in (("deny", ""), ("ask", "(change_id:abcde)")):
                    self.assertIn(P + old + suffix, rules[tier])
                    self.assertIn(P + new + suffix, rules[tier])

    def test_no_alias_matches_old_permission_results_and_render_bytes(self):
        with base_declaration(EXTENSION_MODULES=("delivery_tools",),
                              EXTENSION_OVERRIDES={"delivery_tools": ("wf_close_change",)}):
            extension = surfaces._load_tool_roster().mcp_tool_extensions
            def observe(root):
                (root / ".wavefoundry/framework").mkdir(parents=True)
                path = root / CLAUDE_PROJECT
                path.parent.mkdir()
                path.write_text(json.dumps({"permissions": {"deny": [self.old]}}))
                pending = stp.setup_pending(root, extension.spec_permission_routes(), self.prefix)
                report = surfaces.migrate_spec_tool_permissions(root)
                surfaces.render_claude_permissions(root)
                return pending, report, path.read_bytes()

            actual = observe(self.root / "current")
            with mock.patch.object(extension, "spec_permission_routes", extension.stock_spec_routes):
                self.assertEqual(actual, observe(self.root / "stock"))

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


P = roster.MCP_RULE_PREFIX
CODEX_WITH_COMMENT = (
    "# operator comment survives\n"
    "[mcp_servers.wavefoundry]\n"
    'command = "python3"\n'
    'disabled_tools = ["wf_new_change"] # keep this note\n')


class SpecPermissionMigrationTests(unittest.TestCase):
    """Wave 24buu (24ax3): upgrade and setup migrate repository rules and verify."""

    def setUp(self):
        self.enterContext(base_declaration())
        self.outside = isolate_host_policy(self)
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        (self.root / ".wavefoundry/framework").mkdir(parents=True)  # legacy install: no install log
        self.routes = roster.mcp_tool_extensions.stock_spec_routes()

    def write(self, rel, data, root=None):
        path = (root or self.root) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data if isinstance(data, str) else json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return path

    def legacy_fixture(self):
        self.write(CLAUDE_LOCAL, {"permissions": {"allow": [P + "wf_add_change", P + "wf_get_change"]}})
        self.write(CLAUDE_PROJECT, {"permissions": {"deny": [P + "wf_remove_change"],
                                                    "ask": [P + "wf_close_change(mode=dry_run)"]}})
        self.write(CODEX_PROJECT, CODEX_WITH_COMMENT)

    def all_old_allowed(self):
        self.write(CLAUDE_LOCAL, {"permissions": {"allow": [P + old for old in self.routes]}})

    def migrate(self, root=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            report = surfaces.migrate_spec_tool_permissions(root or self.root)
        return report, out.getvalue()

    def receipt(self, tool, root=None):
        root = root or self.root
        return root / stp._receipt_path(root, tool)

    def tree(self, root=None):
        root = root or self.root
        return {path.relative_to(root).as_posix(): path.read_bytes()
                for path in sorted(root.rglob("*")) if path.is_file() and not path.is_symlink()}

    def assert_ac1(self, root):
        local = json.loads((root / CLAUDE_LOCAL).read_text(encoding="utf-8"))["permissions"]
        project = json.loads((root / CLAUDE_PROJECT).read_text(encoding="utf-8"))["permissions"]
        self.assertIn(P + "wf_add_spec", local["allow"])
        self.assertIn(P + "wf_get_spec", local["allow"])
        self.assertIn(P + "wf_remove_spec", project["deny"])
        self.assertIn(P + "wf_close_spec(mode=dry_run)", project["ask"])
        codex = (root / CODEX_PROJECT).read_text(encoding="utf-8")
        self.assertIn("# operator comment survives", codex)
        self.assertIn("# keep this note", codex)
        self.assertIn("wf_new_spec", tomllib.loads(codex)["mcp_servers"]["wavefoundry"]["disabled_tools"])
        self.assertEqual(roster.spec_permission_holds(root), {})
        for tool in self.routes.values():
            body = self.receipt(tool, root).read_text(encoding="utf-8")
            self.assertTrue(body.startswith(stp._UPGRADE_RECEIPT), body)

    def test_ac1_ac2_ac7_render_child_migrates_verifies_and_is_idempotent(self):
        self.legacy_fixture()
        self.assertEqual(len(roster.spec_permission_holds(self.root)), 5)  # known bad: all five held
        self.assertEqual(surfaces.main(["--repo-root", str(self.root), "--include-permissions"]), 0)
        self.assert_ac1(self.root)
        # AC-2: per layer, each new name's rules equal its old name's rules.
        for rel in (CLAUDE_PROJECT, CLAUDE_LOCAL):
            permissions = json.loads((self.root / rel).read_text(encoding="utf-8"))["permissions"]
            for old, new in self.routes.items():
                for category in ("allow", "ask", "deny"):
                    rules = permissions.get(category, [])
                    old_rules = sorted(r[len(P + old):] for r in rules if r.partition("(")[0] == P + old)
                    new_rules = sorted(r[len(P + new):] for r in rules if r.partition("(")[0] == P + new)
                    if rel == CLAUDE_PROJECT and category == "allow":
                        continue  # framework-managed grants belong to the permissions render
                    self.assertEqual(old_rules, new_rules, (rel, category, old))
        codex = tomllib.loads((self.root / CODEX_PROJECT).read_text(encoding="utf-8"))["mcp_servers"]["wavefoundry"]
        for old, new in self.routes.items():
            for key in ("enabled_tools", "disabled_tools"):
                self.assertEqual(old in codex.get(key, []), new in codex.get(key, []), (key, old))
        # AC-7: a second run changes no byte, receipts included.
        before = self.tree()
        self.assertEqual(surfaces.main(["--repo-root", str(self.root), "--include-permissions"]), 0)
        self.assertEqual(self.tree(), before)
        report, out = self.migrate()
        self.assertEqual((report["migrated"], report["verified"]), ([], []))
        self.assertEqual(sorted(report["already_verified"]), sorted(self.routes.values()))
        self.assertEqual(self.tree(), before)

    def test_permissions_only_backstop_runs_the_same_steps_without_the_claude_platform(self):
        self.legacy_fixture()
        self.assertEqual(surfaces.main(["--repo-root", str(self.root), "--platform", "codex",
                                        "--include-permissions", "--permissions-only"]), 0)
        self.assert_ac1(self.root)
        # Without the permissions switch nothing migrates.
        other = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        (other / ".wavefoundry/framework").mkdir(parents=True)
        self.write(CLAUDE_LOCAL, {"permissions": {"allow": [P + "wf_get_change"]}}, root=other)
        surfaces.main(["--repo-root", str(other), "--permissions-only"])
        self.assertNotIn("wf_get_spec", (other / CLAUDE_LOCAL).read_text(encoding="utf-8"))

    def test_ac3_malformed_repository_file_is_left_and_held(self):
        local = self.write(CLAUDE_LOCAL, '{"permissions": {"allow": ["%swf_get_change",]}}\n' % P)
        before = local.read_bytes()
        self.write(CLAUDE_PROJECT, {"permissions": {"deny": [P + "wf_remove_change"]}})
        report, _ = self.migrate()
        self.assertEqual(local.read_bytes(), before)
        self.assertIn(CLAUDE_LOCAL, report["refused"])
        holds = roster.spec_permission_holds(self.root)
        self.assertIn("Inspect or repair .claude/settings.local.json", holds["wf_get_spec"])
        self.assertFalse(any(self.receipt(tool).exists() for tool in self.routes.values()))
        self.assertIn(P + "wf_remove_spec", (self.root / CLAUDE_PROJECT).read_text(encoding="utf-8"))

    def outside_cases(self):
        user = self.outside / "claude" / "settings.json"
        codex = self.outside / "codex" / "config.toml"
        managed = self.outside / "managed" / "managed-settings.json"
        denied = self.outside / "dotfiles" / "claude.json"
        return [
            ("user deny", {user: json.dumps({"permissions": {"deny": [P + "wf_close_change"]}})},
             {"wf_close_spec"}, user),
            ("user deny pattern", {user: json.dumps({"permissions": {"deny": [P + "wf_*_change"]}})},
             set(self.routes.values()), user),
            ("codex disabled", {codex: '[mcp_servers.wavefoundry]\ndisabled_tools = ["wf_remove_change"]\n'},
             {"wf_remove_spec"}, codex),
            ("symlinked user file", {denied: json.dumps({"permissions": {"deny": [P + "wf_close_change"]}}),
                                     user: denied}, {"wf_close_spec"}, user),
            ("unparseable user file", {user: '{"permissions": {"deny": ["%swf_get_change"' % P},
             {"wf_get_spec"}, user),
            ("enterprise ask", {managed: json.dumps({"permissions": {"ask": [P + "wf_add_change"]}})},
             {"wf_add_spec"}, managed),
        ]

    def test_ac4_outside_restrictions_hold_routes_and_are_never_written(self):
        for name, files, held, named in self.outside_cases():
            with self.subTest(name):
                for tool in self.routes.values():
                    self.receipt(tool).unlink(missing_ok=True)
                shutil.rmtree(self.outside / "claude", ignore_errors=True)
                shutil.rmtree(self.outside / "codex", ignore_errors=True)
                shutil.rmtree(self.outside / "managed", ignore_errors=True)
                for path, content in files.items():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if isinstance(content, Path):
                        try:
                            path.symlink_to(content)
                        except OSError:
                            self.skipTest("symbolic links are unavailable")
                    else:
                        path.write_text(content, encoding="utf-8")
                outside_before = {path: path.read_bytes() for path in files}
                self.all_old_allowed()
                report, out = self.migrate()
                self.assertEqual(set(report["held"]), held)
                self.assertEqual(set(roster.spec_permission_holds(self.root)), held)
                for tool in self.routes.values():
                    self.assertEqual(self.receipt(tool).exists(), tool not in held, tool)
                for tool in held:
                    line = next(line for line in out.splitlines() if f"withheld: {tool}:" in line)
                    self.assertIn(str(named), line)
                self.assertIn(f"Spec-tool outside layer: {named}", out)
                self.assertEqual({path: path.read_bytes() for path in files}, outside_before)
                self.assertTrue(os.path.islink(named) if name == "symlinked user file" else True)

    def test_outside_allow_only_recommends_and_receipt_records_the_files_read(self):
        user = self.write("settings.json", {"permissions": {"allow": [P + "wf_get_change"]}},
                          root=self.outside / "claude")
        self.all_old_allowed()
        report, out = self.migrate()
        self.assertEqual(report["held"], {})
        self.assertIn(f"Spec-tool recommendation: Add the allow rule {P}wf_get_spec to {user}", out)
        body = self.receipt("wf_get_spec").read_text(encoding="utf-8")
        self.assertIn(f"Checked: {user} (read)\n", body)
        self.assertIn("Managed settings override: set\n", body)
        self.assertTrue(stp._receipt_valid(body))
        self.assertFalse(stp._receipt_valid(body + "Injected line\n"))

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFOs are POSIX-only")
    def test_outside_special_file_is_refused_without_blocking_and_holds_every_route(self):
        user = self.outside / "claude" / "settings.json"
        user.parent.mkdir(parents=True)
        os.mkfifo(user)
        self.all_old_allowed()
        report, out = self.migrate()
        self.assertEqual(set(report["held"]), set(self.routes.values()))
        self.assertIn(f"{user} (unreadable)", out)

    def test_outside_file_over_the_size_cap_holds_every_route(self):
        self.write("settings.json", '{"permissions": {}}' + " " * 65536, root=self.outside / "claude")
        self.all_old_allowed()
        with mock.patch.object(stp, "MAX_POLICY_BYTES", 32768):
            report, _ = self.migrate()
        self.assertEqual(set(report["held"]), set(self.routes.values()))
        self.assertTrue(all("Inspect or repair" in remedy for remedy in report["held"].values()))

    def test_outside_paths_resolve_per_platform_and_honor_overrides(self):
        env = {"HOME": "/h", "USERPROFILE": "/u"}
        paths = [str(p) for _, _, p in stp.outside_layer_paths(env, "darwin")]
        self.assertEqual(paths, [str(Path("/h/.claude/settings.json")), str(Path("/h/.codex/config.toml")),
                                 str(Path("/Library/Application Support/ClaudeCode/managed-settings.json"))])
        self.assertEqual(str(stp.outside_layer_paths(env, "linux")[2][2]),
                         str(Path("/etc/claude-code/managed-settings.json")))
        windows = [str(p) for _, _, p in stp.outside_layer_paths({"USERPROFILE": "/u"}, "win32")]
        self.assertEqual(windows[0], str(Path("/u/.claude/settings.json")))
        self.assertEqual(windows[2:], [str(Path(r"C:\ProgramData\ClaudeCode\managed-settings.json")),
                                       str(Path(r"C:\Program Files\ClaudeCode\managed-settings.json"))])
        overridden = stp.outside_layer_paths({"HOME": "/h", "CLAUDE_CONFIG_DIR": "/c", "CODEX_HOME": "/x",
                                              stp.MANAGED_SETTINGS_ENV: "/m.json"}, "linux")
        self.assertEqual([str(p) for _, _, p in overridden],
                         [str(Path("/c/settings.json")), str(Path("/x/config.toml")), str(Path("/m.json"))])

    def test_ac5_repository_pattern_rule_is_not_rewritten_and_holds(self):
        local = self.write(CLAUDE_LOCAL, {"permissions": {"deny": [P + "wf_*_change"]}})
        before = local.read_bytes()
        report, _ = self.migrate()
        self.assertEqual(local.read_bytes(), before)
        self.assertEqual(set(report["held"]), set(self.routes.values()))
        self.assertFalse(any(self.receipt(tool).exists() for tool in self.routes.values()))

    def test_ac9_symlinked_or_outside_repository_settings_are_not_written(self):
        elsewhere = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        target = self.write("policy.json", {"permissions": {"allow": [P + "wf_get_change"]}})
        (self.root / ".claude").mkdir()
        try:
            (self.root / CLAUDE_LOCAL).symlink_to(target)
        except OSError:
            self.skipTest("symbolic links are unavailable")
        cases = {"symlink inside the checkout": target}
        other = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        (other / ".wavefoundry/framework").mkdir(parents=True)
        outside_target = self.write(".claude/settings.local.json",
                                    {"permissions": {"allow": [P + "wf_get_change"]}}, root=elsewhere)
        (other / ".claude").symlink_to(elsewhere / ".claude", target_is_directory=True)
        cases["directory resolving outside"] = outside_target
        for (name, file_bytes), root in zip(cases.items(), (self.root, other)):
            with self.subTest(name):
                before = file_bytes.read_bytes()
                report, _ = self.migrate(root)
                self.assertEqual(file_bytes.read_bytes(), before)
                self.assertIn(CLAUDE_LOCAL, report["refused"])
                self.assertIn("wf_get_spec", roster.spec_permission_holds(root))
                self.assertFalse(self.receipt("wf_get_spec", root).exists())

    def test_ac12_codex_tool_table_is_copied_and_comments_survive(self):
        original = ("# top comment\n[mcp_servers.wavefoundry]\ncommand = \"python3\"\n\n"
                    "[mcp_servers.wavefoundry.tools.wf_get_change]\n# table note\napproval_mode = \"approve\"\n")
        self.write(CODEX_PROJECT, original)
        self.migrate()
        text = (self.root / CODEX_PROJECT).read_text(encoding="utf-8")
        self.assertTrue(text.startswith(original), text)
        self.assertIn("# top comment", text)
        parsed, before = tomllib.loads(text), tomllib.loads(original)
        tools = parsed["mcp_servers"]["wavefoundry"].pop("tools")
        self.assertEqual(tools, {"wf_get_change": {"approval_mode": "approve"},
                                 "wf_get_spec": {"approval_mode": "approve"}})
        before["mcp_servers"]["wavefoundry"].pop("tools")
        self.assertEqual(parsed, before)
        self.assertNotIn("wf_get_spec", roster.spec_permission_holds(self.root))

    def test_codex_insertion_is_reparsed_and_never_edits_another_server(self):
        original = ('[mcp_servers.other]\ndisabled_tools = ["wf_new_change"]\n\n'
                    '[mcp_servers.wavefoundry]\ndisabled_tools = [\n  "wf_new_change", # why\n]\n')
        self.write(CODEX_PROJECT, original)
        self.migrate()
        parsed = tomllib.loads((self.root / CODEX_PROJECT).read_text(encoding="utf-8"))["mcp_servers"]
        self.assertEqual(parsed["other"]["disabled_tools"], ["wf_new_change"])
        self.assertEqual(parsed["wavefoundry"]["disabled_tools"], ["wf_new_change", "wf_new_spec"])
        # A shape the text insertion cannot place exactly keeps the original bytes.
        inline = 'mcp_servers = { wavefoundry = { disabled_tools = ["wf_new_change"] } }\n'
        path = self.write(CODEX_PROJECT, inline)
        report, _ = self.migrate()
        self.assertEqual(path.read_text(encoding="utf-8"), inline)
        self.assertIn(CODEX_PROJECT, report["refused"])
        self.assertIn("wf_new_spec", roster.spec_permission_holds(self.root))

    def test_json_rewrite_keeps_order_indentation_and_line_endings(self):
        path = self.root / CLAUDE_LOCAL
        path.parent.mkdir(parents=True)
        path.write_bytes(b'{\r\n    "z": 1,\r\n    "permissions": {\r\n        "allow": [\r\n'
                         b'            "' + (P + "wf_get_change").encode() + b'"\r\n        ]\r\n    }\r\n}\r\n')
        self.migrate()
        data = path.read_bytes()
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
        self.assertTrue(data.startswith(b'{\r\n    "z": 1,\r\n    "permissions"'), data)
        self.assertIn(b'            "' + (P + "wf_get_spec").encode() + b'"\r\n', data)

    def test_constraint_equivalence_and_separated_holds(self):
        self.write(CLAUDE_LOCAL, {"permissions": {"ask": [P + "wf_get_change(id:1)", P + "wf_get_spec(id:1)",
                                                          P + "wf_add_change(id:1)", P + "wf_add_spec(id:2)"]}})
        self.write("settings.json", {"permissions": {"deny": [P + "wf_close_change"]}}, root=self.outside / "claude")
        layers = stp.assess_layers(self.root, self.routes, P)
        self.assertEqual(set(layers["repository"]), {"wf_add_spec"})
        self.assertEqual(set(layers["outside"]), {"wf_close_spec"})
        self.assertEqual(set(layers["review"]), set(self.routes.values()))
        combined, _ = stp.assess(self.root, self.routes, P)
        self.assertEqual(combined["wf_add_spec"], layers["repository"]["wf_add_spec"])
        self.assertEqual(combined["wf_close_spec"], layers["outside"]["wf_close_spec"])
        self.assertEqual(combined["wf_get_spec"], layers["review"]["wf_get_spec"])

    def test_existing_operator_receipt_is_left_unchanged(self):
        self.all_old_allowed()
        path = self.receipt("wf_get_spec")
        path.parent.mkdir(parents=True)
        path.write_text(stp._RECEIPT, encoding="utf-8")
        before = path.stat().st_mtime_ns
        report, _ = self.migrate()
        self.assertIn("wf_get_spec", report["already_verified"])
        self.assertEqual(path.read_text(encoding="utf-8"), stp._RECEIPT)
        self.assertEqual(path.stat().st_mtime_ns, before)

    def test_fresh_install_writes_no_receipt(self):
        self.write(".wavefoundry/install-log.md", "# Install\n\nInitial MCP vocabulary: spec-tools-v1\n")
        self.all_old_allowed()
        report, _ = self.migrate()
        self.assertEqual(report["verified"], [])
        self.assertEqual(roster.spec_permission_holds(self.root), {})

    def test_setup_pending_reports_until_migration_and_verification_ran(self):
        self.legacy_fixture()
        pending = stp.setup_pending(self.root, self.routes, P)
        self.assertEqual(sorted(pending["unverified"]), sorted(self.routes.values()))
        self.assertTrue(pending["migrations"])
        self.migrate()
        self.assertEqual(stp.setup_pending(self.root, self.routes, P), {"migrations": [], "unverified": []})
        # A route setup cannot change is not reported as pending.
        self.receipt("wf_close_spec").unlink()
        self.write("settings.json", {"permissions": {"deny": [P + "wf_close_change"]}}, root=self.outside / "claude")
        self.assertEqual(stp.setup_pending(self.root, self.routes, P), {"migrations": [], "unverified": []})

    def test_ac10_installing_hop_argv_and_teammate_setup_path(self):
        self.legacy_fixture()
        manifest = self.root.parent / (self.root.name + "-render.json")
        self.addCleanup(manifest.unlink, missing_ok=True)
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        completed = subprocess.run(
            [sys.executable, "-B", str(SCRIPTS / "render_platform_surfaces.py"),
             "--repo-root", str(self.root), "--include-permissions", "--manifest", str(manifest)],
            env=env, capture_output=True, text=True, timeout=300, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assert_ac1(self.root)
        self.assertIn(CLAUDE_LOCAL, json.loads(manifest.read_text(encoding="utf-8"))["written"])
        # A teammate's fresh clone of the migrated repository has no receipts.
        clone = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        shutil.copytree(self.root, clone, dirs_exist_ok=True, ignore=shutil.ignore_patterns("cache"))
        self.assertFalse((clone / ".wavefoundry/cache").exists())
        self.assertEqual(len(roster.spec_permission_holds(clone)), 5)
        import setup_wavefoundry
        self.assertEqual(setup_wavefoundry._run_render_platform_surfaces(clone), 0)
        self.assertEqual(roster.spec_permission_holds(clone), {})
        for tool in self.routes.values():
            self.assertTrue(self.receipt(tool, clone).is_file(), tool)


class SpecPermissionGuidanceTests(unittest.TestCase):
    """Wave 24buu (24ax3) AC-8: seed 160 and its self-hosted copy state the migration."""

    REQUIRED = (
        "### MCP tool names for change specs",
        "Upgrade and `wf setup` carry the permissions over.",
        "each exact rule for a previous tool gets the same rule, constraint included, for its replacement.",
        "read the user-level Claude and Codex settings and the enterprise managed settings without changing them",
        "the alias inherits the same rules and stays withheld until verification.",
        "A teammate who pulls the upgraded repository runs `wf setup`",
        "The summary names the file and the rule to add there, and the operator applies it.",
        "Upgrade cannot inspect MDM profiles, the Windows registry, server-managed settings or host launch flags.",
        "A tool can appear in MCP even when those layers still restrict only its old name.",
        "`wf upgrade spec-permissions --root . --tool wf_get_spec --confirm-effective-host-rules`",
    )
    REMOVED = (
        "Repeat for each replacement you reviewed.",
        "On an existing installation, check each host’s effective permissions",
        "Transfer any exact-name rules in the layer that owns them.",
    )

    def test_seed_and_self_hosted_copy_state_the_migration(self):
        repo = SCRIPTS.parents[2]
        for path in (SCRIPTS.parent / "seeds/160-upgrade-wavefoundry.prompt.md",
                     repo / "docs/prompts/upgrade-wavefoundry.prompt.md"):
            if not path.is_file():
                continue  # the packaged framework carries no self-hosted copy
            text = path.read_text(encoding="utf-8")
            section = text.split("### MCP tool names for change specs", 1)[1].split("\n## ", 1)[0]
            with self.subTest(path.name):
                for phrase in self.REQUIRED:
                    self.assertIn(phrase, text if phrase.startswith("###") else section)
                for phrase in self.REMOVED:
                    self.assertNotIn(phrase, text)


class RunnerHostPolicyIsolationTests(unittest.TestCase):
    """Wave 24buu (24ax3): run_tests points every outside policy location at a missing path."""

    def test_runner_isolates_host_policy_locations(self):
        import test_worker_guard
        if test_worker_guard.MARKER not in _WORKER_ENV:
            self.skipTest("not running under run_tests.py")
        for key in ("CLAUDE_CONFIG_DIR", "CODEX_HOME", stp.MANAGED_SETTINGS_ENV):
            self.assertIn(key, _WORKER_ENV)
            self.assertFalse(os.path.lexists(_WORKER_ENV[key]), key)
