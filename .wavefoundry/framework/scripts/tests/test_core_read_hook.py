"""Exact observational core tools in the generated pre-edit entry point."""
from pathlib import Path
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import render_platform_surfaces as renderer
import mcp_tool_extensions as extensions
import mcp_tool_roster as roster


class CoreReadHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.temp).resolve()
        self.scripts = self.root / '.wavefoundry/framework/scripts'
        self.scripts.mkdir(parents=True)
        for name in ('mcp_tool_roster.py', 'mcp_tool_extensions.py'):
            shutil.copyfile(SCRIPTS / name, self.scripts / name)

    def hook(self):
        namespace = {'__name__': 'hook_fixture', '__file__': str(self.root / '.claude/hooks/pre-edit.py')}
        exec(compile(renderer.claude_pre_edit_source(), '<rendered-hook>', 'exec'), namespace)
        return namespace

    def invoke(self, namespace, name):
        namespace['read_payload_text'] = lambda: json.dumps({
            'tool_name': name, 'tool_input': {'path': '.wavefoundry/framework/scripts/server.py'}})
        with contextlib.redirect_stderr(io.StringIO()):
            return namespace['main']()

    def test_exact_core_reads_pass_closed_guards_and_writers_do_not(self):
        hook = self.hook()
        names = hook['CORE_READ_TOOLS']
        self.assertIn('mcp__wavefoundry__code_read', names)
        self.assertNotIn('mcp__wavefoundry__wf_prepare_wave', names)
        for name, tier in roster.TOOL_TIERS.items():
            with self.subTest(name=name):
                full = roster.MCP_RULE_PREFIX + name
                self.assertEqual(self.invoke(hook, full), 0 if tier == roster.TIER_READ else 2)
        for name in ('mcp__foreign__code_read', 'mcp__wavefoundry__code_write',
                     'mcp__wavefoundry__code_read_alias', 'mcp__wavefoundry__extension_read'):
            self.assertEqual(self.invoke(hook, name), 2)

    def test_overridden_core_and_aliases_are_not_exempt(self):
        with patch.object(extensions, 'EXTENSION_MODULES', ('distribution_hooks',)), \
                patch.object(extensions, 'EXTENSION_OVERRIDES', {'distribution_hooks': ('code_read',)}), \
                patch.object(extensions, 'EXTENSION_TOOL_ALIASES', {'code_read_alias': 'code_outline'}):
            roster.all_tool_tiers()  # Real declaration validation, not a stub.
            hook = self.hook()
        self.assertEqual(self.invoke(hook, 'mcp__wavefoundry__code_read'), 2)
        self.assertEqual(self.invoke(hook, 'mcp__wavefoundry__code_read_alias'), 2)
        self.assertEqual(self.invoke(hook, 'mcp__wavefoundry__code_outline'), 0)

    def test_stale_missing_nonregular_and_malformed_contracts_fail_closed(self):
        hook = self.hook()
        target = self.scripts / 'mcp_tool_roster.py'
        target.write_bytes(target.read_bytes() + b'\n# changed\n')
        self.assertEqual(self.invoke(hook, 'mcp__wavefoundry__code_read'), 2)
        target.unlink()
        self.assertEqual(self.invoke(hook, 'mcp__wavefoundry__code_read'), 2)
        if hasattr(os, 'mkfifo'):
            os.mkfifo(target)
            self.assertEqual(self.invoke(hook, 'mcp__wavefoundry__code_read'), 2)
        with patch.object(extensions, 'EXTENSION_MODULES', ['invalid-tuple']):
            self.assertEqual(renderer._claude_core_read_contract(), ((), {}))
        with patch.object(extensions, 'PERMISSION_SOURCE_DIGEST', 'stale'):
            self.assertEqual(renderer._claude_core_read_contract(), ((), {}))

    def test_rendering_does_not_import_server_or_models(self):
        code = ('import sys; import render_platform_surfaces as r; '
                'assert r._claude_core_read_contract()[0]; r.claude_pre_edit_source(); '
                'assert not any(name in sys.modules for name in '
                '("server", "server_impl", "wf_server.server_impl", "fastembed", "onnxruntime", "tensorwell_client"))')
        child = subprocess.run([sys.executable, '-B', '-c', code], cwd=SCRIPTS,
                               capture_output=True, text=True, timeout=10)
        self.assertEqual(child.returncode, 0, child.stderr)


if __name__ == '__main__':
    unittest.main()
