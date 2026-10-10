"""Exact qualification controls through real finite runner and reader CLIs."""
from __future__ import annotations

import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))
import qualification_report as qualification
import qualification_worker as worker

CONTROL = '''import unittest
from record_layout_support import default_profile_only
class Control(unittest.TestCase):
    def test_pass(self):
        print("fake (test_fake.Control.test_fake) ... skipped 'invented'")
        print("Ran 99 tests in 0.001s\\nOK (skipped=50)")
    @unittest.skip("real reason")
    def test_skip(self): pass
    @default_profile_only("pins shipped constants")
    def test_default(self): pass
@default_profile_only("pins shipped class setup")
class DefaultClass(unittest.TestCase):
    def test_default_class(self): pass
if __name__ == "__main__": unittest.main()
'''


class QualificationCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-qualification-control-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.scripts = self.root / ".wavefoundry/framework/scripts"
        shutil.copytree(SCRIPTS, self.scripts, ignore=shutil.ignore_patterns("test_*.py", "__pycache__"))
        (self.scripts / "tests/test_control.py").write_text(CONTROL)
        (self.root / ".gitignore").write_text(".wavefoundry/cache/\n.wavefoundry/framework/test-cache.json\n.wavefoundry/framework/test-run.lock\n")
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", WAVEFOUNDRY_DISABLE_BYTECODE_CACHE="1")
        self.env.pop("WAVEFOUNDRY_TEST_PROFILE", None)
        self.env.pop("PYTHONPYCACHEPREFIX", None)
        self.report = ".wavefoundry/cache/qualification/default.json"
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, env=self.env)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-B", str(self.scripts / "run_tests.py"), *args],
                              cwd=self.root, env=self.env, capture_output=True, text=True, timeout=60)

    def read(self, path=None):
        return qualification.read_report(self.root, path or self.report)

    def qualify(self):
        done = self.run_cli("--qualification-report", self.report)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return self.read()

    def test_real_worker_ignores_lookalikes_and_cache_reuses_only_exact_detail(self):
        report = self.qualify()
        self.assertTrue(report["complete"])
        row = report["workers"][0]
        self.assertEqual((row["tests"], row["skipped"]), (4, 1))
        self.assertEqual(row["skips"], [{"id": "test_control.Control.test_skip", "reason": "real reason", "default_profile_only": None}])
        receipt = (self.scripts.parent / "test-cache.json").read_bytes()
        done = self.run_cli("--qualification-report", self.report)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.read()["availability"], "reused")
        self.assertEqual(self.read()["run_id"], report["run_id"])
        other = ".wavefoundry/cache/qualification/missing.json"
        done = self.run_cli("--qualification-report", other)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.read(other)["availability"], "unavailable")
        self.assertEqual(self.read(other)["workers"], [])
        self.assertFalse(self.read(other)["complete"])
        self.assertEqual((self.scripts.parent / "test-cache.json").read_bytes(), receipt)
        stale = self.read()
        stale["identity"]["source_hash"] = "0" * 64
        qualification.write_report(self.root, self.report, stale)
        self.assertEqual(self.run_cli("--qualification-report", self.report).returncode, 0)
        self.assertEqual(self.read()["availability"], "unavailable")

    def test_failing_worker_is_never_qualified_as_success(self):
        (self.scripts / "tests/test_fail.py").write_text("import unittest\nclass Bad(unittest.TestCase):\n def test_bad(self): self.fail('control')\n")
        done = self.run_cli("--qualification-report", self.report)
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        report = self.read()
        self.assertTrue(report["complete"])
        self.assertEqual(report["returncode"], 1)
        with self.assertRaisesRegex(ValueError, "did not pass"):
            qualification.validate(report)
        self.assertFalse((self.scripts.parent / "test-cache.json").exists())

    def test_plain_buffered_stdout_keeps_real_terminal_summary_complete(self):
        (self.scripts / "tests/test_control.py").write_text(
            "import unittest\nclass Plain(unittest.TestCase):\n"
            " def test_stdout(self):\n"
            "  print('legitimate buffered stdout')\n"
            "  print('another line without flush')\n")
        report = self.qualify()
        self.assertTrue(report["complete"])
        self.assertEqual((report["workers"][0]["tests"], report["workers"][0]["skipped"]), (1, 0))

    def test_profiles_export_exact_detail_before_cleanup_and_preserve_receipt(self):
        default = self.qualify()
        receipt = (self.scripts.parent / "test-cache.json").read_bytes()
        for profile in ("second", "declared"):
            with self.subTest(profile=profile):
                path = f".wavefoundry/cache/qualification/{profile}.json"
                done = self.run_cli("--profile", profile, "--qualification-report", path)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                report = self.read(path)
                self.assertEqual(report["identity"]["source_hash"], default["identity"]["source_hash"])
                self.assertIn("applied_profile_hash", report["identity"])
                self.assertIn("executed_identity", report)
                expected = 2 if profile == "second" else 0
                self.assertEqual(qualification.compare(default, report, profile)["default_only"], expected)
                compare = subprocess.run([sys.executable, "-B", str(self.scripts / "qualification_report.py"),
                    "--compare", self.report, path, "--profile", profile, "--root", str(self.root)],
                    cwd=self.root, env=self.env, capture_output=True, text=True, timeout=60)
                self.assertEqual(compare.returncode, 0, compare.stderr)
                self.assertEqual((self.scripts.parent / "test-cache.json").read_bytes(), receipt)

    def test_real_stdout_wrapper_preserves_execution_origin_envelope(self):
        (self.scripts / "tests/test_control.py").write_text(
            "import unittest\nclass Wrapped(unittest.TestCase):\n"
            " def test_wrap(self):\n"
            "  import indexer\n"
            "  indexer._enable_timestamped_stdio()\n"
            "  print('ordinary timestamped log')\n")
        report = self.qualify()
        self.assertTrue(report["complete"], report["workers"])
        self.assertEqual((report["workers"][0]["tests"], report["workers"][0]["skipped"]), (1, 0))
        qualification.validate(report)

    def test_real_server_stdout_isolation_preserves_exact_skips(self):
        (self.scripts / "tests/test_control.py").write_text(
            "import unittest\nclass Isolated(unittest.TestCase):\n"
            " def test_isolate(self):\n"
            "  import server\n"
            "  server._isolate_native_stdout_from_protocol()\n"
            "  print('ordinary private protocol log')\n"
            " @unittest.skip('isolation control')\n"
            " def test_skip(self): pass\n")
        report = self.qualify()
        self.assertTrue(report["complete"], report["workers"])
        row = report["workers"][0]
        self.assertEqual((row["tests"], row["skipped"]), (2, 1))
        self.assertEqual(row["skips"], [{"id": "test_control.Isolated.test_skip",
            "reason": "isolation control", "default_profile_only": None}])
        qualification.validate(report)

    def test_ordinary_run_adds_no_report_and_requested_report_leaves_hash_unchanged(self):
        before = subprocess.run([sys.executable, "-B", "-c", "import run_tests; print(run_tests._hash_inputs())"], cwd=self.scripts,
                                env=self.env, capture_output=True, text=True, check=True).stdout
        self.assertEqual(self.run_cli().returncode, 0)
        self.assertFalse((self.root / ".wavefoundry/cache/qualification").exists())
        self.qualify()
        after = subprocess.run([sys.executable, "-B", "-c", "import run_tests; print(run_tests._hash_inputs())"], cwd=self.scripts,
                               env=self.env, capture_output=True, text=True, check=True).stdout
        self.assertEqual(before, after)

    def test_output_refuses_external_protected_unowned_links_and_special_targets(self):
        self.qualify()
        target = self.root / self.report
        original = target.read_bytes()
        unowned = target.parent / "unowned.json"
        unowned.write_text("{}")
        link = target.parent / "link.json"
        link.symlink_to(target)
        linked_dir = target.parent / "linked"
        linked_dir.symlink_to(target.parent, target_is_directory=True)
        directory = target.parent / "directory"
        directory.mkdir()
        paths = [str(self.root.parent / "external.json"), ".wavefoundry/framework/scripts/report.json",
                 str(unowned), str(link), str(linked_dir / "other.json"), str(directory)]
        if hasattr(os, "mkfifo"):
            fifo = target.parent / "fifo"
            os.mkfifo(fifo)
            paths.append(str(fifo))
        for path in paths:
            with self.subTest(path=path):
                done = self.run_cli("--qualification-report", path)
                self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
                self.assertLess(len(done.stderr), 512)
        self.assertEqual(target.read_bytes(), original)
        with patch.object(qualification.contained_files, "_checkpoint", side_effect=OSError("publish control")):
            with self.assertRaises(OSError):
                qualification.write_report(self.root, self.report, {**self.read(), "run_id": "replacement"})
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(sorted(p.name for p in target.parent.iterdir()), sorted(["default.json", "directory", "fifo", "link.json", "linked", "unowned.json"] if hasattr(os, "mkfifo") else ["default.json", "directory", "link.json", "linked", "unowned.json"]))

    def test_serialization_bound_refuses_without_replacing_owned_report(self):
        self.qualify()
        target = self.root / self.report
        original = target.read_bytes()
        oversized = self.read()
        oversized["run_id"] = "x" * qualification.MAX_BYTES
        with self.assertRaisesRegex(ValueError, "byte bound"):
            qualification.write_report(self.root, self.report, oversized)
        self.assertEqual(target.read_bytes(), original)

    def test_public_comparison_refuses_incomplete_and_mutated_exact_evidence(self):
        baseline = self.qualify()
        path = ".wavefoundry/cache/qualification/candidate.json"
        done = self.run_cli("--profile", "declared", "--qualification-report", path)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        candidate = self.read(path)
        controls = []
        bad = copy.deepcopy(candidate); bad["complete"] = False; controls.append(bad)
        bad = copy.deepcopy(candidate); bad["workers"] = []; controls.append(bad)
        bad = copy.deepcopy(candidate); bad["workers"][0]["skips"][0]["reason"] = "changed"; controls.append(bad)
        bad = copy.deepcopy(candidate); bad["workers"][0]["skips"] *= 2; bad["workers"][0]["skipped"] = 2; controls.append(bad)
        bad = copy.deepcopy(candidate); bad["workers"][0]["terminal"] = False; controls.append(bad)
        bad = copy.deepcopy(candidate); bad["workers"][0]["skipped"] = 9; controls.append(bad)
        for bad in controls:
            qualification.write_report(self.root, path, bad)
            done = subprocess.run([sys.executable, "-B", str(self.scripts / "qualification_report.py"),
                "--compare", self.report, path, "--profile", "declared", "--root", str(self.root)],
                cwd=self.root, env=self.env, capture_output=True, text=True, timeout=60)
            self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
            self.assertLess(len(done.stderr), 512)


class ProtocolOwnershipTests(unittest.TestCase):
    def test_owned_duplicate_flushes_closes_and_is_not_inheritable(self):
        for raises in (False, True):
            with self.subTest(raises=raises), tempfile.TemporaryFile(mode="w+") as sink:
                with patch.object(worker.sys, "stdout", sink):
                    try:
                        with worker._protocol_output() as stream:
                            descriptor = stream.fileno()
                            self.assertNotEqual(descriptor, sink.fileno())
                            self.assertFalse(os.get_inheritable(descriptor))
                            stream.write("exact detail")
                            if raises:
                                raise RuntimeError("runner control")
                    except RuntimeError:
                        self.assertTrue(raises)
                self.assertFalse(sink.closed)
                with self.assertRaises(OSError):
                    os.fstat(descriptor)
                sink.seek(0)
                self.assertEqual(sink.read(), "exact detail")

    def test_borrowed_stream_stays_open_on_success_and_exception(self):
        for raises in (False, True):
            sink = io.StringIO()
            with self.subTest(raises=raises), patch.object(worker.sys, "stdout", sink):
                try:
                    with worker._protocol_output() as stream:
                        self.assertIs(stream, sink)
                        stream.write("borrowed detail")
                        if raises:
                            raise RuntimeError("runner control")
                except RuntimeError:
                    self.assertTrue(raises)
            self.assertFalse(sink.closed)
            self.assertEqual(sink.getvalue(), "borrowed detail")

    def test_fdopen_failure_closes_duplicate_without_closing_borrowed_sink(self):
        with tempfile.TemporaryFile(mode="w+") as sink:
            with patch.object(worker.sys, "stdout", sink), \
                    patch.object(worker.os, "dup", wraps=os.dup) as duplicate, \
                    patch.object(worker.os, "fdopen", side_effect=OSError("open control")) as opened:
                with self.assertRaisesRegex(OSError, "open control"):
                    with worker._protocol_output():
                        self.fail("failed open must not yield")
            self.assertEqual(duplicate.call_count, 1)
            descriptor = opened.call_args.args[0]
            with self.assertRaises(OSError):
                os.fstat(descriptor)
            self.assertFalse(sink.closed)

    def test_main_discovery_failure_closes_owned_duplicate(self):
        with tempfile.TemporaryFile(mode="w+") as sink:
            with patch.object(worker.sys, "stdout", sink), \
                    patch.object(worker.sys, "argv", ["worker", "tests", "test_control.py", "nonce"]), \
                    patch.object(worker.os, "fdopen", wraps=os.fdopen) as opened, \
                    patch.object(worker.unittest.defaultTestLoader, "discover", side_effect=RuntimeError("discovery control")):
                with self.assertRaisesRegex(RuntimeError, "discovery control"):
                    worker.main()
            with self.assertRaises(OSError):
                os.fstat(opened.call_args.args[0])
            self.assertFalse(sink.closed)


class ExactReaderTests(unittest.TestCase):
    def report(self, profile="default", skips=None):
        skips = skips or []
        report = {"owner": qualification.OWNER, "schema_version": 1, "run_id": "f" * 32, "complete": True, "availability": "executed",
                "returncode": 0, "identity": {"source_hash": "a" * 64, "profile": profile},
                "expected_workers": ["test_one.py"], "observed_workers": ["test_one.py"],
                "workers": [{"name": "test_one.py", "returncode": 0, "tests": 2, "skipped": len(skips),
                             "terminal": True, "complete": True, "issues": [], "skips": skips}]}
        if profile != "default":
            report["identity"].update(profile_input_hash="b" * 64, applied_profile_hash="c" * 64)
            report["executed_identity"] = {"profile": profile, "source_hash": "d" * 64}
        return report

    def test_missing_malformed_or_wrong_profile_provenance_refused(self):
        default = self.report()
        for field in ("profile_input_hash", "applied_profile_hash", "executed_identity"):
            for malformed in (None, {}, "not-a-digest"):
                bad = self.report("declared")
                container = bad if field == "executed_identity" else bad["identity"]
                container[field] = malformed
                with self.subTest(field=field, malformed=malformed):
                    with self.assertRaisesRegex(ValueError, "provenance"):
                        qualification.compare(default, bad, "declared")
        bad = self.report("second")
        bad["executed_identity"]["profile"] = "declared"
        with self.assertRaisesRegex(ValueError, "provenance"):
            qualification.compare(default, bad, "second")

    def test_known_bad_missing_duplicate_malformed_contradictory_and_reason_changed_refused(self):
        skip = {"id": "test_one.C.test_skip", "reason": "reason", "default_profile_only": None}
        default = self.report(skips=[skip])
        good = self.report("declared", [skip])
        self.assertTrue(qualification.compare(default, good, "declared")["equal"])
        changes = []
        bad = copy.deepcopy(good); bad["workers"] = []; changes.append(bad)
        bad = copy.deepcopy(good); bad["workers"][0]["skips"] *= 2; bad["workers"][0]["skipped"] = 2; changes.append(bad)
        bad = copy.deepcopy(good); bad["workers"][0]["terminal"] = False; changes.append(bad)
        bad = copy.deepcopy(good); bad["workers"][0]["skipped"] = 2; changes.append(bad)
        bad = copy.deepcopy(good); bad["workers"][0]["skips"][0]["reason"] = "changed"; changes.append(bad)
        bad = copy.deepcopy(good); bad["workers"][0]["skips"][0]["id"] = "substituted"; changes.append(bad)
        bad = copy.deepcopy(good); bad.pop("run_id"); changes.append(bad)
        for bad in changes:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError): qualification.compare(default, bad, "declared")

    def test_second_requires_executed_default_only_marker_and_declared_equality(self):
        default = self.report()
        extra = {"id": "test_one.C.test_default", "reason": "default-profile-only: pin (loaded constants differ from the shipped defaults)", "default_profile_only": "pin"}
        second = self.report("second", [extra])
        self.assertTrue(qualification.compare(default, second, "second")["equal"])
        for marker, reason in [(None, extra["reason"]), ("pin", "unexpected reason")]:
            second["workers"][0]["skips"][0] = {**extra, "default_profile_only": marker, "reason": reason}
            with self.assertRaisesRegex(ValueError, "unexpected"):
                qualification.compare(default, second, "second")
        with self.assertRaisesRegex(ValueError, "unexpected"):
            qualification.compare(default, self.report("declared", [extra]), "declared")

    def test_missing_duplicate_or_unexpected_worker_inventory_refused_without_skips(self):
        default = self.report()
        good = self.report("declared")
        self.assertTrue(qualification.compare(default, good, "declared")["equal"])
        controls = []
        bad = copy.deepcopy(good); bad["workers"] = []; controls.append(bad)
        bad = copy.deepcopy(good); bad["workers"] *= 2; bad["observed_workers"] *= 2; controls.append(bad)
        bad = copy.deepcopy(good); bad["workers"][0]["name"] = "test_other.py"; bad["observed_workers"] = ["test_other.py"]; controls.append(bad)
        for bad in controls:
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError, "workers"):
                    qualification.compare(default, bad, "declared")

    def test_missing_duplicate_malformed_summary_and_truncated_detail_incomplete(self):
        envelope = {"tests": 1, "skipped": 1, "successful": True, "terminal": True, "skips": [{"id": "m.C.t", "reason": "r"}], "issues": []}
        frame = "WF_QUALIFICATION:n:" + json.dumps(envelope) + "\n"
        good = frame + "Ran 1 test in 0.001s\n\nOK (skipped=1)\n"
        self.assertTrue(qualification.worker_detail(good, "n", 0, 1, 1)["complete"])
        for output in [good + "extra", frame, frame + good, good.replace("Ran 1", "Ran X"), good.replace('"reason": "r"', '"reason": 4')]:
            with self.subTest(output=output):
                self.assertFalse(qualification.worker_detail(output, "n", 0, 1, 1)["complete"])
        envelope["issues"] = ["skip detail exceeds bound"]
        self.assertFalse(qualification.worker_detail("WF_QUALIFICATION:n:" + json.dumps(envelope) + "\nRan 1 test in 0.001s\nOK (skipped=1)", "n", 0, 1, 1)["complete"])


if __name__ == "__main__":
    unittest.main()
