"""MCP scan adapters require a typed current completion result."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

class ScanCompletionMcpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from server_tools_support import load_server
        cls.server = load_server()
        from wave_lint_lib import secrets_validators
        cls.scanner = secrets_validators

    def test_current_process_must_prove_completion_and_never_fallback(self):
        from types import SimpleNamespace
        from wf_server.docs_handlers import wf_scan_secrets_response
        cases = [
            (0, {}), (0, {'complete': 'true', 'failures': []}),
            (0, {'complete': True, 'failures': 'none'}),
            (0, {'complete': True, 'failures': [42]}),
            (2, {'complete': True, 'failures': []}),
            (2, {'complete': False, 'failures': []}),
            (1, {'complete': True, 'failures': []}),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for code, payload in cases:
                with self.subTest(code=code, payload=payload), patch.object(
                    self.server, '_mcp_subprocess_run', return_value=SimpleNamespace(
                        returncode=code, stdout=json.dumps(payload), stderr='')) as run, patch.object(
                    self.scanner, 'check_hardcoded_secrets', side_effect=AssertionError('must not repeat failed attempt')):
                    result = wf_scan_secrets_response(Path(tmp), 'full')
                    self.assertEqual(result['status'], 'error')
                    self.assertFalse(result['data']['complete'])
                    self.assertFalse(result['data']['clean'])
                    self.assertEqual(run.call_count, 1)
            with patch.object(self.server, '_mcp_subprocess_run', return_value=SimpleNamespace(
                    returncode=0, stdout=json.dumps({'complete': True, 'failures': []}), stderr='')):
                result = wf_scan_secrets_response(Path(tmp), 'full')
                self.assertEqual(result['status'], 'ok')
                self.assertTrue(result['data']['complete'])
