"""Legacy hook declarations fail at the shared declaration preflight."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mcp_tool_extensions as extensions
import mcp_tool_roster as roster


class LegacyHookDeclarationTests(unittest.TestCase):
    def test_malformed_entries_report_declaration_problems(self):
        invalid = [[], (None,), ({'event': 'Stop'},),
                   ({'event': '', 'command': 'run'},),
                   ({'event': 'Stop', 'command': ''},),
                   ({'event': 'Stop', 'command': '{{repo_root}} {{repo_root}}'},),
                   ({'event': 'Stop', 'command': '{{other}}'},)]
        for entries in invalid:
            with self.subTest(entries=entries), patch.object(extensions, 'EXTENSION_LEGACY_CLAUDE_HOOK_COMMANDS', entries):
                self.assertTrue(extensions.declaration_problems(core_tools=set(), runner_tools=set()))
                with self.assertRaises(extensions.ExtensionDeclarationError):
                    roster.all_tool_tiers()

    def test_valid_entries_expand_literal_placeholder(self):
        entries = ({'event': 'Stop', 'command': 'python "{{repo_root}}/hook.py"'},)
        with patch.object(extensions, 'EXTENSION_LEGACY_CLAUDE_HOOK_COMMANDS', entries):
            self.assertFalse(extensions.declaration_problems(core_tools=set(), runner_tools=set()))
            self.assertEqual(extensions.legacy_claude_hook_commands('/root path'), {('Stop', 'python "/root path/hook.py"')})

    def test_renderer_rejects_before_any_render_writer(self):
        import render_platform_surfaces as renderer
        with tempfile.TemporaryDirectory() as directory, patch.object(extensions, 'EXTENSION_LEGACY_CLAUDE_HOOK_COMMANDS', (None,)), patch.object(renderer, 'write_text', side_effect=AssertionError('render started')), patch.object(renderer, 'render_claude_settings', side_effect=AssertionError('settings render started')):
            self.assertEqual(renderer.main(['--repo-root', directory, '--platform', 'claude']), 1)


if __name__ == '__main__':
    unittest.main()
