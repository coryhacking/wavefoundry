"""Guard history transitions and atomic publication using disposable fake deltas."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scanner_skips as ledger
from runtime_lock import RuntimeFileLock


class ScannerSkipLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / ledger.LEDGER_REL
        for rel in ("one.txt", "two.txt", "clean.txt"):
            (self.root / rel).write_text("ordinary fixture", encoding="utf-8")

    def skipped(self, rel="one.txt", reason="file_size"):
        return {rel: {"complete": False, "skips": [
            {"file": rel, "reason": reason, "detail": "fixture guard limit"},
        ]}}

    def recorded(self):
        return {row["file"]: row["reason"] for row in ledger.scanner_skip_notice(self.root).get("scanner_skips", [])}

    def test_guard_publication_survives_fresh_read_and_reskip_then_clears_on_complete_scan(self):
        ledger.update_scanner_skips(self.root, self.skipped())
        self.assertTrue(self.path.is_file())
        self.assertEqual(self.recorded(), {"one.txt": "file_size"})
        self.assertEqual(json.loads(self.path.read_text())["version"], 1)
        ledger.update_scanner_skips(self.root, self.skipped(reason="line_length"))
        self.assertEqual(self.recorded(), {"one.txt": "line_length"})
        ledger.update_scanner_skips(self.root, {"one.txt": {"complete": True, "skips": []}})
        self.assertEqual(ledger.scanner_skip_notice(self.root), {})
        self.assertEqual(json.loads(self.path.read_text()), {"version": 1, "files": {}})

    def test_cache_hit_unrelated_scan_and_incomplete_outcomes_preserve_history(self):
        ledger.update_scanner_skips(self.root, self.skipped())
        before = self.path.read_bytes()
        for delta in ({}, {"clean.txt": {"complete": True, "skips": []}}, {"one.txt": {"complete": False, "skips": []}}):
            with self.subTest(delta=delta), patch.object(ledger.os, "replace", side_effect=AssertionError("unchanged ledger rewritten")):
                ledger.update_scanner_skips(self.root, delta)
                self.assertEqual(self.path.read_bytes(), before)
        ledger.update_scanner_skips(self.root, self.skipped("two.txt"))
        self.assertEqual(self.recorded(), {"one.txt": "file_size", "two.txt": "file_size"})

    def test_identical_reskip_does_not_rewrite_history(self):
        ledger.update_scanner_skips(self.root, self.skipped())
        with patch.object(ledger.os, "replace", side_effect=AssertionError("rewritten")):
            ledger.update_scanner_skips(self.root, self.skipped())

    def test_duplicate_rows_collapse_to_one_on_publish_and_read(self):
        row = {"file": "one.txt", "reason": "file_size", "detail": "fixture guard limit"}
        ledger.update_scanner_skips(self.root, {"one.txt": {"complete": False, "skips": [dict(row), dict(row), dict(row)]}})
        self.assertEqual(ledger.scanner_skip_notice(self.root)["scanner_skips"], [row])
        stored = json.loads(self.path.read_text())
        self.assertEqual(len(stored["files"]["one.txt"]), 1)
        stored["files"]["one.txt"] = [stored["files"]["one.txt"][0]] * 3  # hand-edited duplicate rows
        self.path.write_text(json.dumps(stored))
        self.assertEqual(ledger.scanner_skip_notice(self.root)["scanner_skips"], [row])

    def test_missing_history_and_clean_scan_create_no_index_or_lock(self):
        self.assertEqual(ledger.scanner_skip_notice(self.root), {})
        ledger.update_scanner_skips(self.root, {})
        ledger.update_scanner_skips(self.root, {"one.txt": {"complete": True, "skips": []}})
        self.assertFalse((self.root / ".wavefoundry").exists())

    def test_reader_does_not_prune_removed_paths_write_or_acquire_lock(self):
        ledger.update_scanner_skips(self.root, self.skipped())
        (self.root / "one.txt").unlink()
        before = self.path.read_bytes()
        with patch.object(ledger, "RuntimeFileLock", side_effect=AssertionError("reader locked")), patch.object(ledger.os, "replace", side_effect=AssertionError("reader wrote")), patch.object(Path, "stat", side_effect=AssertionError("reader checked source")):
            self.assertEqual(self.recorded(), {"one.txt": "file_size"})
        self.assertEqual(self.path.read_bytes(), before)

    def test_confirmed_removal_clears_history_but_io_errors_do_not(self):
        ledger.update_scanner_skips(self.root, self.skipped())
        lstat = Path.lstat
        for error in (PermissionError("fixture permission"), OSError("fixture I/O")):
            def failing_lstat(path, *args, **kwargs):
                if path == self.root / "one.txt":
                    raise error
                return lstat(path, *args, **kwargs)
            with self.subTest(error=error), patch.object(Path, "lstat", failing_lstat):
                ledger.update_scanner_skips(self.root, {})
            self.assertEqual(self.recorded(), {"one.txt": "file_size"})
        (self.root / "one.txt").unlink()
        ledger.update_scanner_skips(self.root, {})
        self.assertEqual(ledger.scanner_skip_notice(self.root), {})

    def test_dangling_symlink_retains_history_until_link_itself_is_removed(self):
        ledger.update_scanner_skips(self.root, self.skipped())
        source = self.root / "one.txt"
        source.unlink()
        try:
            source.symlink_to("missing-target.txt")
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        ledger.update_scanner_skips(self.root, {})
        self.assertEqual(self.recorded(), {"one.txt": "file_size"})
        source.unlink()
        ledger.update_scanner_skips(self.root, {})
        self.assertEqual(ledger.scanner_skip_notice(self.root), {})

    def test_malformed_history_is_explicit_and_preserved_by_publisher(self):
        self.path.parent.mkdir(parents=True)
        invalid = [b"not json", b"\xff", b"{}", b'{"version":true,"files":{}}']
        for rel in ("../outside", "/absolute", "C:/absolute", "a/../b", "a\\b", "a//b"):
            invalid.append(json.dumps({"version": 1, "files": {rel: [{"reason": "guard", "detail": "fixture"}]}}).encode())
        for rows in ([], "guard", [{"reason": 1, "detail": "fixture"}], [{"reason": "guard", "detail": "fixture", "content": "forbidden"}]):
            invalid.append(json.dumps({"version": 1, "files": {"one.txt": rows}}).encode())
        # Decoder recursion on pathological nesting is malformed, not a crash.
        invalid.append(b"[" * 100_000 + b"]" * 100_000)
        invalid.append(b'{"version": 1, "files": {"one.txt": ' + b"[" * 100_000 + b"]" * 100_000 + b"}}")
        for raw in invalid:
            with self.subTest(raw=raw):
                self.path.write_bytes(raw)
                self.assertIn("coverage unavailable", ledger.scanner_skip_notice(self.root)["scanner_skips_error"])
                with self.assertRaises(ValueError):
                    ledger.update_scanner_skips(self.root, self.skipped("two.txt"))
                self.assertEqual(self.path.read_bytes(), raw)

    def test_unreadable_history_is_explicit_and_not_overwritten(self):
        ledger.update_scanner_skips(self.root, self.skipped())
        before = self.path.read_bytes()
        with patch.object(Path, "read_text", side_effect=PermissionError("fixture")):
            self.assertIn("scanner_skips_error", ledger.scanner_skip_notice(self.root))
            with self.assertRaises(PermissionError):
                ledger.update_scanner_skips(self.root, self.skipped("two.txt"))
        self.assertEqual(self.path.read_bytes(), before)

    def test_failed_atomic_replace_preserves_prior_bytes_and_cleans_temporary_file(self):
        ledger.update_scanner_skips(self.root, self.skipped())
        before = self.path.read_bytes()
        with patch.object(ledger.os, "replace", side_effect=OSError("fixture publication failure")):
            with self.assertRaises(OSError):
                ledger.update_scanner_skips(self.root, self.skipped("two.txt"))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_disjoint_concurrent_deltas_wait_for_lock_and_merge(self):
        held = RuntimeFileLock(self.path.with_suffix(".lock"), blocking=True).acquire()
        entered = {rel: threading.Event() for rel in ("one.txt", "two.txt")}
        acquire = RuntimeFileLock.acquire
        local = threading.local()

        def observed_acquire(lock):
            entered[local.rel].set()
            return acquire(lock)

        def publish(rel):
            local.rel = rel
            ledger.update_scanner_skips(self.root, self.skipped(rel))

        with ThreadPoolExecutor(max_workers=2) as pool, patch.object(RuntimeFileLock, "acquire", observed_acquire):
            futures = [pool.submit(publish, rel) for rel in entered]
            try:
                for event in entered.values():
                    self.assertTrue(event.wait(3), "writer did not attempt lock")
                self.assertTrue(all(not future.done() for future in futures))
                self.assertFalse(self.path.exists())
            finally:
                held.release()
            for future in futures:
                future.result(timeout=5)
        self.assertEqual(self.recorded(), {"one.txt": "file_size", "two.txt": "file_size"})


if __name__ == "__main__":
    unittest.main()
