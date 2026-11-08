"""Fixed scanner input limits are named accurately and carry a working remedy.

Change 22qoz: decoded-size and newline-count limits are checked by the parent
with the engine's own predicate; the idle worker never ends itself; every
``[scan-incomplete]`` producer shares one remedy projection.
"""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import tomllib
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_secrets_scan
import scanner_skips
from wave_lint_lib import betterleaks_engine as engine
from wave_lint_lib import betterleaks_worker as worker
from wave_lint_lib import secrets_validators as scanner

UPSTREAM_RULES = 'wavefoundryProfile="betterleaks-v2-8f376ff9"\n[[rules]]\nid="synthetic"\nregex="SYNTHETIC_TOKEN"\n'
REMEDY_MARK = "Rescanning alone will not clear"


def _live_worker():
    # load_server() reloads the scanner package; patch the module the scanner
    # resolves at call time rather than this file's import-time reference.
    return sys.modules["wave_lint_lib.betterleaks_worker"]


class FixedInputLimitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(worker.close_worker)
        self.root = Path(self.tmp.name)
        self.rules = self.root / scanner.SCAN_RULES_FRAMEWORK_PATH
        self.rules.parent.mkdir(parents=True)
        self.rules.write_text(UPSTREAM_RULES)
        self.rel = "data dir/large-file.txt"
        self.file = self.root / self.rel
        self.file.parent.mkdir(parents=True)

    def scan(self, **kwargs):
        with contextlib.redirect_stderr(io.StringIO()):
            return scanner.check_hardcoded_secrets(self.root, files=[self.file], **kwargs)

    def rows(self):
        return scanner_skips.scanner_completion(self.root)["incomplete"]

    def exclude_with_remedy_entry(self):
        # The remedy's own entry text must be valid TOML that excludes the path.
        entry = scanner_skips.allowlist_entry(self.rel)
        self.rules.write_text(UPSTREAM_RULES.replace(
            "[[rules]]", f"[allowlist]\npaths=[{entry}]\n[[rules]]", 1))

    def assert_fixed_limit(self, reason):
        failures = self.scan()
        rows = self.rows()
        self.assertEqual([(r["file"], r["reason"]) for r in rows], [(self.rel, reason)], rows)
        self.assertNotIn("worker_input_too_large", json.dumps(rows))
        self.assertNotIn("detection_or_filter_work_incomplete", json.dumps(rows))
        self.assertIn(REMEDY_MARK, rows[0]["remedy"])
        self.assertIn(scanner_skips.allowlist_entry(self.rel), rows[0]["remedy"])
        summary = [f for f in failures if f.startswith("[scan-incomplete]")]
        self.assertTrue(summary and all(REMEDY_MARK in f for f in summary), failures)
        self.assertFalse(any("retry" in f for f in summary), summary)
        self.assertFalse(any(self.rel in f for f in summary), summary)  # Summaries stay path-free.
        return failures

    # AC-1 ---------------------------------------------------------------
    def test_decoded_size_expansion_is_named_with_remedy(self):
        self.file.write_bytes((b"\xe9" * 99 + b"\n") * 20972)  # about 2 MiB, no NUL
        self.assertLess(self.file.stat().st_size, scanner.MAX_FILE_BYTES)
        self.assert_fixed_limit(scanner_skips.DECODED_TOO_LARGE_REASON)
        self.assertIn("decoded cap", self.rows()[0]["detail"])

    def test_decoded_size_just_under_cap_scans_completely_with_full_ruleset(self):
        shutil.copyfile(SCRIPTS.parent / "scan-rules.toml", self.rules)
        count = engine.MAX_CONTENT_BYTES // 3
        self.file.write_bytes(b"\xe9" * count)
        content = self.file.read_bytes().decode("utf-8", errors="replace")
        self.assertLessEqual(len(content.encode("utf-8")), engine.MAX_CONTENT_BYTES)
        self.assertGreater(len(content.encode("utf-8")) + 3, engine.MAX_CONTENT_BYTES)
        outcome = {}
        rules, policy, errors = scanner.load_merged_ruleset(self.root)
        self.assertEqual(errors, [])
        start = time.monotonic()
        with contextlib.redirect_stderr(io.StringIO()):
            scanner.scan_file_raw(self.file, self.rel, [], [], set(), policy, _outcome=outcome)
        self.assertLess(time.monotonic() - start, worker.MAX_TIMEOUT_SECONDS)
        self.assertEqual(len(rules), 474)
        self.assertTrue(outcome["complete"], scanner._SCANNER_SKIPS)

    def test_shared_predicate_matches_engine_refusal_exactly(self):
        config = {"rules": [{"id": "synthetic", "regex": "SYNTHETIC_TOKEN"}]}
        built = engine.BetterleaksEngine(config)
        cases = {
            "at_size": "�" * (engine.MAX_CONTENT_BYTES // 3) + "ab",
            "over_size": "�" * (engine.MAX_CONTENT_BYTES // 3) + "abc",
            "at_lines": "a\n" * engine.MAX_LINES + "a",
            "over_lines": "a\n" * (engine.MAX_LINES + 1),
            "form_feeds": "a\f" * (engine.MAX_LINES + 1),
        }
        for name, content in cases.items():
            with self.subTest(name):
                limit = engine.exceeded_input_limit(content)
                self.assertEqual(limit is None, built.scan(content, "f.txt")["complete"])
                self.assertEqual(limit, {"over_size": "decoded_size", "over_lines": "line_count"}.get(name))

    # AC-1b --------------------------------------------------------------
    def test_newline_count_over_limit_is_named_and_cleared_by_anchored_entry(self):
        self.file.write_text("a\n" * (engine.MAX_LINES + 1))
        self.assert_fixed_limit(scanner_skips.TOO_MANY_LINES_REASON)
        self.assertIn("newlines", self.rows()[0]["detail"])
        self.exclude_with_remedy_entry()
        self.assertEqual(self.scan(), [])
        self.assertTrue(scanner_skips.scanner_completion(self.root)["complete"])

    def test_newline_controls_scan_completely(self):
        for name, text in (("unterminated_final_line", "a\n" * engine.MAX_LINES + "a"),
                           ("form_feed_separators", "a\f" * (engine.MAX_LINES + 1))):
            with self.subTest(name):
                self.file.write_text(text)
                self.assertEqual(self.scan(), [])
                self.assertTrue(scanner_skips.scanner_completion(self.root)["complete"])

    def test_residual_engine_incompleteness_keeps_retry_text_without_remedy(self):
        self.file.write_text("ordinary content\n")
        live = _live_worker()
        actual = live.worker_request

        def incomplete(operation, payload):
            result = actual(operation, payload)
            if operation == "scan":
                result["complete"] = False
            return result
        with patch.object(live, "worker_request", side_effect=incomplete):
            failures = self.scan()
        rows = self.rows()
        self.assertEqual(rows[0]["detail"], "detection_or_filter_work_incomplete")
        self.assertNotIn("remedy", rows[0])
        summary = [f for f in failures if f.startswith("[scan-incomplete]")]
        self.assertTrue(summary)
        self.assertTrue(all("retry" in f and REMEDY_MARK not in f for f in summary), summary)

    # AC-3 ---------------------------------------------------------------
    def test_remedy_reaches_docs_lint_cli_and_mcp_and_allowlist_clears_it(self):
        self.file.write_bytes((b"\xe9" * 99 + b"\n") * 20972)
        for attempt in range(2):  # Rescanning never clears a fixed limit.
            with self.subTest(attempt=attempt):
                lint = self.scan(record_only=True)
                self.assertTrue(any(REMEDY_MARK in f for f in lint), lint)
                self.assertFalse(scanner_skips.scanner_completion(self.root)["complete"])
        out = io.StringIO()
        with patch.object(scanner, "get_scan_files", return_value=[self.file]), patch.object(
                sys, "argv", ["scan", "--root", str(self.root), "--mode", "full"]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(run_secrets_scan.main(), 2)
        cli = json.loads(out.getvalue().splitlines()[-1])
        self.assertFalse(cli["complete"])
        self.assertIn(REMEDY_MARK, cli["incomplete"][0]["remedy"])
        self.assertTrue(any(REMEDY_MARK in f for f in cli["failures"]), cli["failures"])
        from server_tools_support import load_server
        load_server()
        from wf_server.docs_handlers import wf_scan_secrets_response
        mcp = wf_scan_secrets_response(self.root, "full")
        self.assertEqual(mcp["status"], "error")
        self.assertIn(REMEDY_MARK, mcp["data"]["incomplete"][0]["remedy"])
        self.assertTrue(any(REMEDY_MARK in f for f in mcp["data"]["failures"]))
        diag = [d["message"] for d in mcp["diagnostics"] if d["code"] == "scan_incomplete"]
        self.assertTrue(diag and REMEDY_MARK in diag[0], diag)
        self.exclude_with_remedy_entry()
        self.assertEqual(self.scan(), [])
        self.assertTrue(scanner_skips.scanner_completion(self.root)["complete"])

    def test_read_guard_size_gets_remedy_but_worker_timeout_does_not(self):
        self.file.write_text("ordinary content\n")
        with patch.object(scanner, "MAX_FILE_BYTES", 3):
            failures = self.scan()
        self.assertEqual(self.rows()[0]["reason"], scanner_skips.FILE_TOO_LARGE_REASON)
        self.assertIn(REMEDY_MARK, self.rows()[0]["remedy"])
        self.assertTrue(any(REMEDY_MARK in f for f in failures))
        live = _live_worker()
        actual = live.worker_request

        def timeout(operation, payload):
            if operation == "scan":
                raise live.WorkerError("worker_timeout")
            return actual(operation, payload)
        with patch.object(live, "worker_request", side_effect=timeout):
            failures = self.scan()
        rows = self.rows()
        self.assertEqual(rows[0]["detail"], "worker_timeout")
        # Change 22r96: a timeout row carries retry-first guidance, never the
        # fixed-limit remedy, and is not counted as a fixed limit.
        self.assertTrue(rows[0]["remedy"].startswith("The scan of this file timed out. Retry the scan first."))
        self.assertNotIn(REMEDY_MARK, rows[0]["remedy"])
        self.assertFalse(any(REMEDY_MARK in f for f in failures), failures)
        self.assertFalse(any(REMEDY_MARK in f for f in scanner_skips.scanner_completion_failures(self.root)))


class RemedyProjectionTests(unittest.TestCase):
    def test_entry_is_valid_toml_anchored_to_exactly_one_path(self):
        import re
        for rel in ("big.txt", "docs/a b/c-d#e~&.txt", "o'brien/notes.txt", 'q"uote/x\\y.txt'):
            with self.subTest(rel=rel):
                entry = scanner_skips.allowlist_entry(rel)
                pattern = tomllib.loads(f"paths=[{entry}]\n")["paths"][0]
                self.assertEqual(pattern, "^" + re.escape(rel) + "\\z")  # wave 22u26 (22qr7)
                compiled = engine.compile_regex(pattern)
                self.assertTrue(compiled.search(rel))
                self.assertFalse(compiled.search(rel + "\n"))
                self.assertFalse(compiled.search(rel + ".bak"))
                self.assertFalse(compiled.search("x/" + rel))

    def test_only_fixed_limit_reasons_get_a_remedy(self):
        for reason in scanner_skips.FIXED_LIMIT_REASONS:
            self.assertIn(REMEDY_MARK, scanner_skips.fixed_limit_remedy({"file": "a.txt", "reason": reason}))
        for reason in ("upstream scan incomplete", "input unreadable", "scan incomplete", "binary file"):
            self.assertIsNone(scanner_skips.fixed_limit_remedy({"file": "a.txt", "reason": reason}))
        rows = [{"file": "a.txt", "reason": "upstream scan incomplete", "detail": "worker_timeout"}]
        self.assertEqual(scanner_skips.incomplete_guidance(rows), "inspect completion details and retry.")


@unittest.skipUnless(hasattr(signal, "setitimer"), "SIGALRM bounds exist only on POSIX")
class WorkerIdleAlarmTests(unittest.TestCase):
    """AC-2: a short patched timeout ends requests, never an idle worker."""

    def copied_worker(self, timeout: float, engine_source: str = "") -> Path:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, True)
        package = directory / "scripts" / "wave_lint_lib"
        package.mkdir(parents=True)
        source = Path(worker.__file__).read_text()
        self.assertIn("MAX_TIMEOUT_SECONDS = 115.0\n", source)
        (package / "betterleaks_worker.py").write_text(
            source.replace("MAX_TIMEOUT_SECONDS = 115.0\n", f"MAX_TIMEOUT_SECONDS = {timeout}\n"))
        shutil.copyfile(SCRIPTS / "bytecode_cache.py", package.parent / "bytecode_cache.py")
        (package / "__init__.py").write_text("")
        if engine_source:
            (package / "betterleaks_engine.py").write_text(textwrap.dedent(engine_source))
        return package / "betterleaks_worker.py"

    def test_idle_worker_serves_next_request_on_same_process(self):
        client = worker._Client([sys.executable, "-B", str(self.copied_worker(0.5)), "--worker"])
        self.addCleanup(client.close)
        self.assertEqual(client.request("parse_toml", {"text": "n=1"}, timeout=0.5), {"n": 1})
        process = client._process
        time.sleep(1.5)  # Three idle timeouts.
        self.assertIsNone(process.poll(), process.returncode)
        self.assertEqual(client.request("parse_toml", {"text": "n=2"}, timeout=0.5), {"n": 2})
        self.assertIs(client._process, process)

    def test_request_alarm_still_ends_an_overlong_request_at_the_worker(self):
        path = self.copied_worker(60.0, '''\
            import time
            class BetterleaksEngine:
                def __init__(self, config):
                    time.sleep(30)
            ''')
        import subprocess_util
        process = subprocess_util.isolated_popen(
            [sys.executable, "-B", str(path), "--worker"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.addCleanup(worker._dispose, process)
        request = {"id": 1, "op": "configure", "budget": 0.5,
                   "payload": {"config": {"rules": []}, "cache_key": ""}}
        process.stdin.write(json.dumps(request).encode() + b"\n")
        process.stdin.flush()
        # The parent does not kill it here: only the worker's own alarm can.
        self.assertEqual(process.wait(timeout=10), -signal.SIGALRM)

    def test_closing_input_ends_an_idle_worker(self):
        import subprocess_util
        process = subprocess_util.isolated_popen(
            [sys.executable, "-B", str(self.copied_worker(0.5)), "--worker"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.addCleanup(worker._dispose, process)
        process.stdin.write(b'{"id":1,"op":"parse_toml","payload":{"text":"n=1"},"budget":0.5}\n')
        process.stdin.flush()
        self.assertTrue(process.stdout.readline().startswith(b'{"id":1,"ok":true'))
        time.sleep(1.0)
        self.assertIsNone(process.poll())
        process.stdin.close()
        self.assertEqual(process.wait(timeout=5), 0)


if __name__ == "__main__":
    unittest.main()
