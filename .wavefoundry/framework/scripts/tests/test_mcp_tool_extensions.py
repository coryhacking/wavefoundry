"""Legacy hook declarations fail at the shared declaration preflight."""
from pathlib import Path
import contextlib
import io
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mcp_tool_extensions as extensions
import mcp_tool_roster as roster


def roster_arguments():
    """The arguments production uses (``mcp_tool_roster.all_tool_tiers``), so a
    valid ambient distribution declaration is valid here too (change 20rvq)."""
    return dict(core_tools=set(roster.TOOL_TIERS) - roster.RUNNER_TOOLS,
                runner_tools=roster.RUNNER_TOOLS, core_tiers=roster.TOOL_TIERS)


class LegacyHookDeclarationTests(unittest.TestCase):
    def test_malformed_entries_report_declaration_problems(self):
        tuple_message = 'EXTENSION_LEGACY_CLAUDE_HOOK_COMMANDS must be a tuple'
        shape_message = 'legacy hook entries require exactly event and command'
        empty_message = 'legacy hook event and command must be nonempty strings'
        placeholder_message = 'legacy hook commands support only one {{repo_root}} placeholder'
        invalid = [([], tuple_message), ((None,), shape_message), (({'event': 'Stop'},), shape_message),
                   (({'event': '', 'command': 'run'},), empty_message),
                   (({'event': 'Stop', 'command': ''},), empty_message),
                   (({'event': 'Stop', 'command': '{{repo_root}} {{repo_root}}'},), placeholder_message),
                   (({'event': 'Stop', 'command': '{{other}}'},), placeholder_message)]
        for entries, message in invalid:
            with self.subTest(entries=entries), patch.object(extensions, 'EXTENSION_LEGACY_CLAUDE_HOOK_COMMANDS', entries):
                # Exactly the legacy-hook problem: an ambient declaration problem cannot stand in for it.
                self.assertEqual(extensions.declaration_problems(**roster_arguments()), [message])
                with self.assertRaisesRegex(extensions.ExtensionDeclarationError, re.escape(message)):
                    roster.all_tool_tiers()

    def test_valid_entries_expand_literal_placeholder(self):
        entries = ({'event': 'Stop', 'command': 'python "{{repo_root}}/hook.py"'},)
        with patch.object(extensions, 'EXTENSION_LEGACY_CLAUDE_HOOK_COMMANDS', entries):
            self.assertEqual(extensions.declaration_problems(**roster_arguments()), [])
            self.assertEqual(extensions.legacy_claude_hook_commands('/root path'), {('Stop', 'python "/root path/hook.py"')})

    def test_renderer_rejects_before_any_render_writer(self):
        import render_platform_surfaces as renderer
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as directory, patch.object(extensions, 'EXTENSION_LEGACY_CLAUDE_HOOK_COMMANDS', (None,)), patch.object(renderer, 'write_text', side_effect=AssertionError('render started')), patch.object(renderer, 'render_claude_settings', side_effect=AssertionError('settings render started')), contextlib.redirect_stderr(stderr):
            self.assertEqual(renderer.main(['--repo-root', directory, '--platform', 'claude']), 1)
        # The refusal is the legacy entry's, not an ambient declaration problem.
        self.assertIn('legacy hook entries require exactly event and command', stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
