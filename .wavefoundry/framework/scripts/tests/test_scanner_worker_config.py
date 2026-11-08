"""Scanner configuration is sent once per worker and digest, never per request.

Change 22qr5: the parent keys configuration on a digest of the exact config
and execution key it would send; the child recomputes that digest and refuses
a digest it does not hold without being discarded.
"""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from wave_lint_lib import betterleaks_worker as worker
from wave_lint_lib import secrets_validators as scanner


def setUpModule():
    # Another test module in the same process may reload the scanner package (``load_server``),
    # which would leave the objects imported above stale: patches would land on modules the scan
    # no longer uses. Bind the current ones before these tests run (wave 22u26, change 22qr7).
    global worker, scanner
    from wave_lint_lib import betterleaks_worker as worker
    from wave_lint_lib import secrets_validators as scanner

RULES = ('wavefoundryProfile="betterleaks-v2-8f376ff9"\n[allowlist]\npaths=["^ignored/"]\n'
         '[[rules]]\nid="synthetic"\nregex="SYNTHETIC_TOKEN"\n')


class _Wire(contextlib.ExitStack):
    """Count configuration bytes on the wire and child process starts."""

    def __enter__(self):
        super().__enter__()
        self.config_bytes = self.config_requests = self.starts = 0
        encode, start = worker._encode, worker._Client._start

        def counting_encode(value, limit):
            raw = encode(value, limit)
            if isinstance(value, dict) and isinstance(value.get("payload"), dict) and "config" in value["payload"]:
                self.config_bytes += len(raw)
                self.config_requests += 1
            return raw

        def counting_start(client, cancel):
            self.starts += 1
            return start(client, cancel)
        self.enter_context(patch.object(worker, "_encode", counting_encode))
        self.enter_context(patch.object(worker._Client, "_start", counting_start))
        return self


class ConfigSentOncePerWorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        worker.close_worker()
        self.addCleanup(worker.close_worker)
        self.root = Path(self.tmp.name)
        rules = self.root / scanner.SCAN_RULES_FRAMEWORK_PATH
        rules.parent.mkdir(parents=True)
        rules.write_text(RULES)

    def files(self, count):
        paths = []
        for n in range(count):
            path = self.root / f"src/file-{n}.txt"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"line {n}\nSYNTHETIC_TOKEN\n" if n % 2 else f"ordinary {n}\n")
            paths.append(path)
        return paths

    def scan(self, files):
        with contextlib.redirect_stderr(io.StringIO()):
            return scanner.check_hardcoded_secrets(self.root, files=files)

    def policy(self):
        _, policy, errors = scanner.load_merged_ruleset(self.root)
        self.assertEqual(errors, [])
        return policy

    # AC-1 ---------------------------------------------------------------
    def test_config_bytes_and_worker_starts_do_not_scale_with_file_count(self):
        observed = {}
        for count in (3, 12):
            worker.close_worker()
            for path in (self.root / "src").glob("*") if (self.root / "src").exists() else ():
                path.unlink()
            (self.root / "docs/scan-findings.json").unlink(missing_ok=True)
            with _Wire() as wire:
                failures = self.scan(self.files(count))
            observed[count] = (wire.config_bytes, wire.config_requests, wire.starts,
                               sum("[secrets]" in f for f in failures))
        self.assertEqual(observed[3][3], 1)
        self.assertEqual(observed[12][3], 6)
        self.assertEqual(observed[3][1:3], observed[12][1:3], observed)
        # Request ids and remaining budgets vary by a few digits, nothing more.
        self.assertLessEqual(abs(observed[3][0] - observed[12][0]), 32, observed)
        self.assertEqual(observed[12][2], 1, observed)  # One child for the whole scan.
        self.assertLessEqual(observed[12][1], 3, observed)  # Bounded by distinct digests.

    # AC-1a --------------------------------------------------------------
    def test_same_cache_key_with_different_allowlists_keeps_separate_results(self):
        policy = self.policy()
        key = policy["_betterleaks_cache_key"]
        for _ in range(2):
            self.assertTrue(scanner._upstream_path_excluded("a/x.txt", policy, ["^a/"]))
            self.assertFalse(scanner._upstream_path_excluded("a/x.txt", policy, ["^b/"]))
        self.assertEqual(policy["_betterleaks_cache_key"], key)
        content = "SYNTHETIC_TOKEN\n"
        with contextlib.redirect_stderr(io.StringIO()):
            found = scanner._scan_upstream_raw(content, "f.txt", ["SYNTHETIC_TOKEN"], policy, [], [])
            filtered = scanner._scan_upstream_raw(content, "f.txt", ["SYNTHETIC_TOKEN"], policy, ["^SYNTHETIC_TOKEN$"], [])
            found_again = scanner._scan_upstream_raw(content, "f.txt", ["SYNTHETIC_TOKEN"], policy, [], [])
        self.assertEqual(len(found), 1)
        self.assertEqual(filtered, [])
        self.assertEqual(found_again, found)

    # AC-2 ---------------------------------------------------------------
    def test_worker_killed_between_requests_is_respawned_configured(self):
        files = self.files(4)
        with _Wire() as wire:
            first = self.scan(files)
            process = worker._CLIENT._process
            process.kill()
            process.wait(timeout=5)
            (self.root / "docs/scan-findings.json").unlink()
            second = self.scan(files)
        self.assertEqual(sorted(first), sorted(second))
        self.assertEqual(sum("[secrets]" in f for f in second), 2)
        self.assertFalse(any("[scan-incomplete]" in f for f in second), second)
        self.assertEqual(wire.starts, 2)
        self.assertIsNot(worker._CLIENT._process, process)

    def test_worker_killed_between_files_of_one_scan_is_respawned_configured(self):
        files = self.files(4)
        baseline = self.scan(files)
        (self.root / "docs/scan-findings.json").unlink()
        original = scanner.scan_file_raw
        killed = []

        def kill_after_first(*args, **kwargs):
            result = original(*args, **kwargs)
            if not killed:  # Between digest-only requests, after configuration.
                process = worker._CLIENT._process
                process.kill()
                process.wait(timeout=5)
                killed.append(process)
            return result
        with _Wire() as wire, patch.object(scanner, "scan_file_raw", side_effect=kill_after_first):
            interrupted = self.scan(files)
        self.assertTrue(killed)
        self.assertEqual(sorted(interrupted), sorted(baseline))
        self.assertFalse(any("[scan-incomplete]" in f for f in interrupted), interrupted)
        self.assertEqual(wire.starts, 1)  # The respawn; the first child predates the counter.


def _copied_worker(test, engine_source: str) -> Path:
    directory = Path(tempfile.mkdtemp())
    test.addCleanup(shutil.rmtree, directory, True)
    package = directory / "scripts" / "wave_lint_lib"
    package.mkdir(parents=True)
    shutil.copyfile(worker.__file__, package / "betterleaks_worker.py")
    shutil.copyfile(SCRIPTS / "bytecode_cache.py", package.parent / "bytecode_cache.py")
    (package / "__init__.py").write_text("")
    (package / "betterleaks_engine.py").write_text(textwrap.dedent(engine_source))
    return package / "betterleaks_worker.py"


SLOW_ENGINE = '''\
    import time
    class BetterleaksEngine:
        def __init__(self, config):
            pass
        def path_excluded(self, path):
            return False
        def scan(self, content, path, metadata_only=False):
            if content == "slow":
                time.sleep(30)
            return {"findings": [], "complete": True, "diagnostics": []}
    '''


class DigestProtocolTests(unittest.TestCase):
    def client(self):
        client = worker._Client([sys.executable, "-B", str(_copied_worker(self, SLOW_ENGINE)), "--worker"])
        self.addCleanup(client.close)
        return client

    def test_unheld_digest_is_refused_and_the_healthy_child_is_kept(self):
        client = self.client()
        held = {"config": {"rules": [], "allowlist": {"paths": ["^a/"]}}, "cache_key": "k"}
        other = {"config": {"rules": [], "allowlist": {"paths": ["^b/"]}}, "cache_key": "k"}
        self.assertEqual(client.request("scan", {**held, "content": "", "path": "f"})["complete"], True)
        process = client._process
        process.config_digest = worker.config_digest(other["config"], "k")  # A wrong belief.
        with self.assertRaises(worker.WorkerError) as raised:
            client.request("scan", {**other, "content": "", "path": "f"})
        self.assertEqual(raised.exception.code, "configuration_not_held")
        self.assertIs(client._process, process)
        self.assertIsNone(process.poll())
        self.assertIsNone(process.config_digest)
        self.assertTrue(client.request("scan", {**other, "content": "", "path": "f"})["complete"])
        self.assertIs(client._process, process)

    def test_child_computes_the_digest_and_ignores_a_client_label(self):
        import subprocess_util
        process = subprocess_util.isolated_popen(
            [sys.executable, "-B", str(_copied_worker(self, SLOW_ENGINE)), "--worker"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.addCleanup(worker._dispose, process)
        real = {"rules": [], "allowlist": {"paths": ["^a/"]}}
        forged = worker.config_digest({"rules": [], "allowlist": {"paths": ["^b/"]}}, "k")

        def call(sequence, op, payload):
            process.stdin.write(json.dumps({"id": sequence, "op": op, "payload": payload, "budget": 5}).encode() + b"\n")
            process.stdin.flush()
            return json.loads(process.stdout.readline())
        never = call(1, "scan", {"config_digest": forged, "content": "", "path": "f"})
        self.assertEqual(never, {"id": 1, "ok": False, "error": "configuration_not_held"})
        configured = call(2, "configure", {"config": real, "cache_key": "k", "config_digest": forged})
        self.assertEqual(configured["result"]["config_digest"], worker.config_digest(real, "k"))
        self.assertEqual(call(3, "scan", {"config_digest": forged, "content": "", "path": "f"})["error"],
                         "configuration_not_held")
        self.assertTrue(call(4, "scan", {"config_digest": worker.config_digest(real, "k"),
                                         "content": "", "path": "f"})["ok"])

    def test_worker_killed_during_request_reports_that_file_incomplete(self):
        client = self.client()
        payload = {"config": {"rules": []}, "cache_key": "k", "path": "f"}
        client.request("scan", {**payload, "content": ""})
        process = client._process
        threading.Timer(0.5, process.kill).start()
        policy = {"_betterleaks_config": {"rules": []}, "_betterleaks_cache_key": "k"}
        live = sys.modules["wave_lint_lib.betterleaks_worker"]
        outcome = {}
        before = len(scanner._SCANNER_SKIPS)
        with patch.object(live, "_CLIENT", client), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(scanner._scan_upstream_raw("slow", "f", ["slow"], policy, [], [], outcome=outcome), [])
        self.assertEqual(scanner._SCANNER_SKIPS[before:],
                         [{"file": "f", "reason": "upstream scan incomplete", "detail": "worker_crashed"}])
        self.assertNotIn("complete", outcome)
        self.assertIsNone(client._process)
        self.assertTrue(client.request("scan", {**payload, "content": ""})["complete"])  # Respawned.


if __name__ == "__main__":
    unittest.main()
