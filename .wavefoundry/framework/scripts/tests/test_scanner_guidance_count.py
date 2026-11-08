#!/usr/bin/env python3
"""Scan-incomplete guidance counts every outstanding file (wave 22u26, change 22qr7).

``scanner_completion`` returns at most 50 rows for display. The close and ``wf_scan_secrets``
diagnostics used to count fixed-limit files from that list, so beyond 50 they undercounted.
"""
from __future__ import annotations

import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from server_tools_support import _make_repo, load_server
import scanner_skips
import test_server_tools_lifecycle as fixtures

OUTSTANDING = 60
WORK_LIMIT = f"{OUTSTANDING} of them reached a fixed scanner work limit"


class OutstandingGuidanceCountTests(unittest.TestCase):
    _write_config = fixtures.WaveCouncilPolicyTests._write_config
    _prepared_wave_with_change = fixtures.WaveCouncilPolicyTests._prepared_wave_with_change
    _record_readiness_approval = fixtures.WaveCouncilPolicyTests._record_readiness_approval
    _run_prepare = fixtures.WaveCouncilPolicyTests._run_prepare
    LINT_OK = fixtures.WaveCouncilPolicyTests.LINT_OK
    GARDEN_OK = fixtures.WaveCouncilPolicyTests.GARDEN_OK

    def setUp(self):
        self.srv = load_server()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = _make_repo(Path(self.temp.name))
        outcomes = {}
        for number in range(OUTSTANDING):
            rel = f"many/file-{number:02d}.txt"
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text("content\n", encoding="utf-8")
            outcomes[rel] = {"complete": False, "skips": [
                {"file": rel, "reason": scanner_skips.UPSTREAM_INCOMPLETE_REASON, "detail": "match_limit"}]}
        scanner_skips.update_scanner_skips(self.root, outcomes)
        coverage = scanner_skips.scanner_completion(self.root)
        # The fixture exercises the truncation: 60 outstanding, 50 displayed.
        self.assertEqual((coverage["incomplete_files"], len(coverage["incomplete"])), (OUTSTANDING, 50))

    @staticmethod
    def _messages(result: dict, code: str) -> list[str]:
        return [d["message"] for d in result.get("diagnostics", []) if d.get("code") == code]

    def test_the_scan_diagnostic_counts_every_outstanding_file(self):
        completed = types.SimpleNamespace(
            returncode=2, stdout=json.dumps({"complete": False, "failures": []}), stderr="")
        with patch.object(self.srv, "_mcp_subprocess_run", return_value=completed):
            result = self.srv.wf_scan_secrets_response(self.root, mode="incremental")
        messages = self._messages(result, "scan_incomplete")
        self.assertEqual(len(messages), 1, result)
        self.assertIn(WORK_LIMIT, messages[0])

    def test_the_close_diagnostic_counts_every_outstanding_file(self):
        self._write_config()
        wave_id, _wave_md, _change = self._prepared_wave_with_change("guidance-count")
        with patch.object(self.srv, "run_validate", return_value=self.LINT_OK), \
                patch.object(self.srv, "run_garden", return_value=self.GARDEN_OK):
            result = self.srv.wf_close_wave_response(self.root, wave_id, mode="dry_run")
        messages = self._messages(result, "secret_scan_incomplete")
        self.assertEqual(len(messages), 1, result)
        self.assertIn(WORK_LIMIT, messages[0])


if __name__ == "__main__":
    unittest.main()
