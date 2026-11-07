"""Deterministic scanner work limits carry a token-specific lasting remedy.

Change 22r96: a file that stops on an engine work limit records a fixed
detail chosen by exact membership, and each limit gets its own remedy. A
worker timeout gets retry-first guidance; a path-check timeout gets retry only.
"""
from __future__ import annotations

import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import scanner_skips
from wave_lint_lib import betterleaks_engine as engine
from wave_lint_lib import betterleaks_worker as worker
from wave_lint_lib import secrets_validators as scanner

UPSTREAM_RULES = 'wavefoundryProfile="betterleaks-v2-8f376ff9"\n[[rules]]\nid="synthetic"\nregex="SYNTHETIC_TOKEN"\n'
ENTRY = "'^data\\ dir/many\\-matches\\.txt$'"
ADD = f"add {ENTRY} to the project [allowlist] paths in docs/scan-rules.toml."
MATCH_REMEDY = (
    "Rescanning alone will not clear a fixed scanner work limit: the file produced more raw rule "
    "matches than one scan evaluates. Convert or split the file, or, after confirming it holds no "
    "secrets, " + ADD)
RESULT_REMEDY = (
    "Rescanning alone will not clear a fixed scanner work limit: the file holds more candidate "
    "findings, after filtering, than one scan can return, so none are shown and they are unreviewed "
    "candidate secrets. Split the file and rescan the parts so the findings appear; only after those "
    "findings are reviewed, " + ADD)
COMPONENT_REMEDY = (
    "Rescanning alone will not clear a fixed scanner work limit: the scan stopped combining related "
    "findings. The findings it reported stand, and a path entry would also suppress them. Resolve the "
    "reported findings, or narrow the rule, first; only after confirming they are false positives, " + ADD)
TIMEOUT_GUIDANCE = (
    "The scan of this file timed out. Retry the scan first. If it times out again on unchanged "
    "content, convert or split the file, or, after confirming it holds no secrets, " + ADD)
PATH_CHECK_GUIDANCE = (
    "The path-exclusion check for this file timed out. Retry the scan; a path entry cannot clear "
    "this, because the same check evaluates it.")
RETRY = "inspect scanner completion details and retry."


def _live_worker():
    # load_server() elsewhere may reload the scanner package; patch the module
    # the scanner resolves at call time.
    return sys.modules["wave_lint_lib.betterleaks_worker"]


class WorkLimitRemedyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(worker.close_worker)
        self.root = Path(self.tmp.name)
        self.rules = self.root / scanner.SCAN_RULES_FRAMEWORK_PATH
        self.rules.parent.mkdir(parents=True)
        self.rules.write_text(UPSTREAM_RULES)
        self.rel = "data dir/many-matches.txt"
        self.file = self.root / self.rel
        self.file.parent.mkdir(parents=True)
        self.assertEqual(scanner_skips.allowlist_entry(self.rel), ENTRY)

    def scan(self):
        with contextlib.redirect_stderr(io.StringIO()):
            return scanner.check_hardcoded_secrets(self.root, files=[self.file])

    def rows(self):
        return scanner_skips.scanner_completion(self.root)["incomplete"]

    def allowlist(self, entry):
        self.rules.write_text(UPSTREAM_RULES.replace(
            "[[rules]]", f"[allowlist]\npaths=[{entry}]\n[[rules]]", 1))

    def test_live_match_limit_gets_lasting_remedy_and_allowlist_entry_clears_it(self):
        # Synthetic rule and content: one raw match per line, past MAX_MATCHES.
        self.file.write_text("SYNTHETIC_TOKEN\n" * (engine.MAX_MATCHES + 1))
        for attempt in range(2):  # Rescanning reaches the same limit.
            with self.subTest(attempt=attempt):
                failures = self.scan()
                rows = self.rows()
                self.assertEqual([(r["reason"], r["detail"]) for r in rows],
                                 [("upstream scan incomplete", "match_limit")], rows)
                self.assertEqual(rows[0]["remedy"], MATCH_REMEDY)
                summary = [f for f in failures if f.startswith("[scan-incomplete]")]
                self.assertTrue(summary, failures)
                self.assertTrue(all("fixed scanner work limit" in f and "retry" not in f
                                    and "input limit" not in f and self.rel not in f for f in summary), summary)
        self.allowlist(ENTRY)
        self.assertEqual(self.scan(), [])
        self.assertTrue(scanner_skips.scanner_completion(self.root)["complete"])

    def test_token_to_detail_mapping_is_exact_with_fixed_precedence(self):
        cases = {
            ("match_limit",): "match_limit",
            ("result_limit",): "result_limit",
            ("component_set_limit",): "component_set_limit",
            # Multi-token: a raised limit outranks the composite-set limit.
            ("component_set_limit", "result_limit"): "result_limit",
            ("component_set_limit", "match_limit"): "match_limit",
            ("filter_evaluation_error:synthetic", "match_limit"): "match_limit",
            ("result_limit", "match_limit"): "result_limit",
            # Only exact members count; nothing is copied from worker text.
            ("match_limit; add ^.*$",): None,
            ("MATCH_LIMIT",): None,
            ("filter_evaluation_error:synthetic",): None,
            (): None,
        }
        for tokens, detail in cases.items():
            with self.subTest(tokens=tokens):
                self.assertEqual(scanner_skips.work_limit_detail(list(tokens)), detail)
        self.assertIsNone(scanner_skips.work_limit_detail("match_limit"))
        self.assertEqual(worker.WorkerError("worker_response_too_large").code, "worker_response_too_large")

    def test_each_work_limit_has_its_own_exact_remedy_never_called_an_input_limit(self):
        expected = {"match_limit": MATCH_REMEDY, "result_limit": RESULT_REMEDY,
                    "worker_response_too_large": RESULT_REMEDY, "component_set_limit": COMPONENT_REMEDY}
        for detail, remedy in expected.items():
            with self.subTest(detail=detail):
                row = {"file": self.rel, "reason": "upstream scan incomplete", "detail": detail}
                self.assertEqual(scanner_skips.fixed_limit_remedy(row), remedy)
                self.assertNotIn("input limit", remedy)
                guidance = scanner_skips.incomplete_guidance([row], RETRY)
                self.assertIn("fixed scanner work limit", guidance)
                self.assertNotIn("input limit", guidance)
        # Input limits keep their text; other residual reasons keep theirs.
        self.assertIn("fixed scanner input limit", scanner_skips.fixed_limit_remedy(
            {"file": self.rel, "reason": scanner_skips.FILE_TOO_LARGE_REASON}))
        residual = {"file": self.rel, "reason": "upstream scan incomplete",
                    "detail": "detection_or_filter_work_incomplete"}
        self.assertIsNone(scanner_skips.fixed_limit_remedy(residual))
        self.assertEqual(scanner_skips.incomplete_guidance([residual], RETRY), RETRY)

    def test_filter_error_residual_keeps_retry_text(self):
        # A runtime filter failure (live worker) is residual work, not a limit.
        self.file.write_text("SYNTHETIC_TOKEN\n")
        self.rules.write_text(UPSTREAM_RULES + "filter='fromBase64(\"bad*\") == \"\"'\n")
        self.scan()
        rows = self.rows()
        self.assertEqual([(r["reason"], r["detail"]) for r in rows],
                         [("upstream scan incomplete", "detection_or_filter_work_incomplete")], rows)
        self.assertNotIn("remedy", rows[0])
        self.assertEqual(scanner_skips.scanner_completion_failures(self.root),
                         ["[scan-incomplete] 1 eligible file(s) have unresolved incomplete scans; " + RETRY])

    def test_scan_timeout_gets_retry_first_guidance_and_path_check_timeout_retry_only(self):
        self.file.write_text("ordinary content\n")
        self.allowlist("'^unrelated$'")  # Makes the path-exclusion check reach the worker.
        live = _live_worker()
        actual = live.worker_request
        for operation, detail, guidance in (
                ("scan", "worker_timeout", TIMEOUT_GUIDANCE),
                ("path_excluded", "path_check_worker_timeout", PATH_CHECK_GUIDANCE)):
            with self.subTest(operation=operation):
                # Each case starts from no recorded history for the file.
                (self.root / scanner_skips.LEDGER_REL).unlink(missing_ok=True)

                def timeout(op, payload, _operation=operation):
                    if op == _operation:
                        raise live.WorkerError("worker_timeout")
                    return actual(op, payload)
                with patch.object(live, "worker_request", side_effect=timeout):
                    self.scan()
                rows = self.rows()
                self.assertEqual([(r["reason"], r["detail"]) for r in rows],
                                 [("upstream scan incomplete", detail)], rows)
                self.assertEqual(rows[0]["remedy"], guidance)
                self.assertTrue(guidance.startswith("The ") and "Retry the scan" in guidance)
                # Neither timeout counts as a fixed limit in any summary.
                self.assertEqual(scanner_skips.scanner_completion_failures(self.root),
                                 ["[scan-incomplete] 1 eligible file(s) have unresolved incomplete scans; " + RETRY])
                self.assertEqual(scanner_skips.incomplete_guidance(rows, RETRY), RETRY)
        self.assertNotIn("allowlist", PATH_CHECK_GUIDANCE)

    def test_response_cap_from_the_scan_path_records_its_exact_detail_and_remedy(self):
        # A live response-cap fixture needs about 10,000 surviving findings (~22 s);
        # the worker's own closed error is raised instead, through the real
        # _scan_upstream_raw except branch, for the scan operation only.
        self.file.write_text("ordinary content\n")
        live = _live_worker()
        actual = live.worker_request

        def response_cap(op, payload):
            if op == "scan":
                raise live.WorkerError("worker_response_too_large")
            return actual(op, payload)
        with patch.object(live, "worker_request", side_effect=response_cap):
            failures = self.scan()
        rows = self.rows()
        self.assertEqual([(r["reason"], r["detail"]) for r in rows],
                         [("upstream scan incomplete", "worker_response_too_large")], rows)
        self.assertEqual(rows[0]["remedy"], RESULT_REMEDY)
        summary = [f for f in failures if f.startswith("[scan-incomplete]")]
        self.assertTrue(summary and all("fixed scanner work limit" in f for f in summary), failures)

    def test_mixed_summary_names_input_work_and_retry_files_separately(self):
        rows = [{"file": "a.txt", "reason": scanner_skips.FILE_TOO_LARGE_REASON, "detail": "x"},
                {"file": "b.txt", "reason": "upstream scan incomplete", "detail": "match_limit"},
                {"file": "c.txt", "reason": "upstream scan incomplete", "detail": "worker_timeout"}]
        guidance = scanner_skips.incomplete_guidance(rows, RETRY)
        self.assertIn("1 of them exceed a fixed scanner input limit.", guidance)
        self.assertIn("1 of them reached a fixed scanner work limit", guidance)
        self.assertTrue(guidance.endswith("Inspect completion details and retry the other file(s)."), guidance)


if __name__ == "__main__":
    unittest.main()
