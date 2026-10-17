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
from declaration_support import apply_base_declaration, base_declaration


class CoreReadHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.temp).resolve()
        self.scripts = self.root / '.wavefoundry/framework/scripts'
        self.scripts.mkdir(parents=True)
        for name in ('mcp_tool_roster.py', 'mcp_tool_extensions.py'):
            # Byte copies: CORE_READ_CONTRACT digests the on-disk bytes, so the
            # declaration is owned in memory below, never appended to the copy.
            shutil.copyfile(SCRIPTS / name, self.scripts / name)
        # Change 20rvq: own the declaration explicitly (the shipped empty one plus
        # each test's own) instead of inheriting an ambient distribution profile.
        apply_base_declaration(self)

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

    # Change 20wqb: one real, validated declaration covering every kind of
    # declared name the exemption must judge by its effective tier.
    DISTRIBUTION = dict(
        EXTENSION_MODULES=('distribution_hooks',),
        EXTENSION_TOOL_PREFIXES=('dist_',),
        EXTENSION_TOOL_TIERS={'dist_read': 'read', 'dist_write': 'write'},
        EXTENSION_OVERRIDES={'distribution_hooks': ('code_read',)},
        EXTENSION_TOOL_ALIASES={'code_outline_alias': 'code_outline', 'dist_prepare_alias': 'wf_prepare_wave',
                                'dist_open_gate_alias': 'wf_open_gate', 'wf_alias_gpu_doctor': 'wf_gpu_doctor'},
        EXTENSION_HIDDEN_TOOLS=('wf_gpu_doctor',),
        EXTENSION_REPLACEMENTS={'distribution_hooks': {
            'code_search': {'alias_for_core': 'dist_core_code_search'},
            'code_keyword': {'alias_for_core': 'dist_core_code_keyword', 'tier': 'write'},
        }},
    )

    def test_declared_read_tier_names_are_exempt_and_write_tier_names_are_not(self):
        with base_declaration(**self.DISTRIBUTION):
            tiers = roster.all_tool_tiers()  # Real declaration validation, not a stub.
            hook = self.hook()
        self.assertEqual(len(hook['CORE_READ_CONTRACT']), 2)
        exempt = ('code_read', 'code_outline_alias', 'wf_alias_gpu_doctor', 'code_search',
                  'dist_core_code_search', 'dist_core_code_keyword', 'dist_read', 'code_outline')
        gated = ('dist_write', 'dist_prepare_alias', 'dist_open_gate_alias', 'code_keyword',
                 'wf_gpu_doctor', 'wf_open_gate', 'wf_prepare_wave')
        for name in exempt:
            with self.subTest(exempt=name):
                self.assertEqual(tiers[name], roster.TIER_READ)
                self.assertEqual(self.invoke(hook, roster.MCP_RULE_PREFIX + name), 0)
        for name in gated:
            with self.subTest(gated=name):
                self.assertEqual(self.invoke(hook, roster.MCP_RULE_PREFIX + name), 2)
        self.assertNotIn('wf_gpu_doctor', tiers)

    def test_invalid_declaration_grants_no_exemption_at_all(self):
        # A replacement may never lower write to read: the whole declaration is
        # refused, and the contract grants nothing, core reads included.
        with base_declaration(EXTENSION_MODULES=('distribution_hooks',), EXTENSION_TOOL_PREFIXES=('dist_',),
                              EXTENSION_REPLACEMENTS={'distribution_hooks': {
                                  'wf_prepare_wave': {'alias_for_core': 'dist_core_prepare', 'tier': 'read'}}}):
            with self.assertRaises(extensions.ExtensionDeclarationError) as refused:
                roster.all_tool_tiers()
            self.assertEqual(str(refused.exception).count(';'), 0, str(refused.exception))
            self.assertIn('wf_prepare_wave', str(refused.exception))
            hook = self.hook()
        self.assertEqual(hook['CORE_READ_TOOLS'], ())
        self.assertEqual(self.invoke(hook, 'mcp__wavefoundry__code_read'), 2)
        self.assertEqual(self.invoke(hook, 'mcp__wavefoundry__wf_prepare_wave'), 2)

    def test_stale_missing_nonregular_and_malformed_contracts_fail_closed(self):
        hook = self.hook()
        self.assertEqual(self.invoke(hook, 'mcp__wavefoundry__code_read'), 0)  # Positive control first.
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
