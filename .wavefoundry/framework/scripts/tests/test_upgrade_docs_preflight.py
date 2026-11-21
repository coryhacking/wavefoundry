"""Read-only upgrade lint through the real current and supported older runners."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import record_paths
import upgrade_extensions as extension
import upgrade_protocol
import vocabulary_profile
from record_layout_support import copy_scripts_tree, localized_docs_lint_fixture


DRIVER = """
import sys
from pathlib import Path
root, pack, action = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
scripts = root / '.wavefoundry/framework/scripts'
sys.path.insert(0, str(scripts))
import upgrade_wavefoundry as runner
runner._preferred_python = lambda: sys.executable
# v1.22 dry run always discovers its pack, including in real home/download
# directories. Give the archived search routine only the fixture directory.
for location in ("_HOME_DIR", "_HOME_WAVEFOUNDRY_DIR", "_DIST_DIR", "_DOWNLOADS_DIR"):
    setattr(runner, location, pack.parent)
original_hook = runner._run_hook
def hook(name, ctx, ext):
    if name == "post_preflight":
        assert ext is not None
        if action == "without-preflight":
            ext._docs_preflight = lambda ctx: None
        if action == "fault":
            def fault(root):
                raise OSError("controlled preflight fault")
            ext._preflight_marker = fault
        return original_hook(name, ctx, ext)
    if name == "post_extract" and not getattr(ctx, "dry_run", False):
        print("EXTRACTION COMPLETE", flush=True)
        if action not in {"gate", "retain", "without-preflight"}:
            raise SystemExit(77)
runner._run_hook = hook
def render(root):
    if action == "retain":
        raise RuntimeError("test rendering failure")
runner.phase_surface_rendering = render
runner.phase_pruning = lambda root: 0
args = ["--root", str(root), "--pack", str(pack), "--yes"]
if action == "dry":
    args += ["--dry-run"]
raise SystemExit(runner.main(args))
"""


class PackagedPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.temp = Path(tmp.name).resolve()
        pack_dir = cls.temp / "packs with spaces"
        pack_dir.mkdir()
        cls.pack = pack_dir / "wavefoundry-1.47.0.fixture.zip"
        cls.prefix = ".wavefoundry/framework/"
        with zipfile.ZipFile(cls.pack, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in SCRIPTS.rglob("*.py"):
                relative = path.relative_to(SCRIPTS)
                if not {"tests", "benchmarks"}.intersection(relative.parts):
                    archive.write(path, cls.prefix + "scripts/" + relative.as_posix())
            archive.writestr(cls.prefix + "VERSION", "1.47.0\n")
            archive.writestr(upgrade_protocol.PROTOCOL_METADATA_ARCNAME, json.dumps(
                upgrade_protocol.build_protocol_metadata(release_version="1.47.0", build_id="fixture", artifact_type="feature")))
        cls.driver = cls.temp / "driver.py"
        cls.driver.write_text(DRIVER, encoding="utf-8")

    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve() / "project"
        localized_docs_lint_fixture(self.root)
        framework = self.root / ".wavefoundry/framework"
        self.scripts = copy_scripts_tree(framework, with_support=False)
        (framework / "VERSION").write_text("1.46.0\n")
        (framework / "MANIFEST").write_text("VERSION\nMANIFEST\n")
        manifest = self.root / "docs/prompts/prompt-surface-manifest.json"
        manifest.write_text(manifest.read_text().replace("2099-01-01a", "1.46.0"))
        self.document = self.root / "docs/example.md"
        self.document.write_text("# Example\n")
        self.linter = self.scripts / "docs_lint.py"
        self.set_linter()

    def set_linter(self, *errors):
        # A sentinel emitted only by a deliberate incorrect bytecode invocation
        # would fail the unchanged-tree check.
        self.linter.write_text("import sys\nfrom pathlib import Path\n"
                               "if not sys.dont_write_bytecode: Path('unwanted-bytecode').touch()\n"
                               + ("print(%r)\n" % "\n".join(errors) if errors else "")
                               + f"sys.exit({int(bool(errors))})\n", encoding="utf-8")

    def drive(self, action="apply", version=None):
        if version:
            fixture = SCRIPTS / f"tests/fixtures/upgrade_old_runner/upgrade_runner_v{version}.py.txt"
            shutil.copyfile(fixture, self.scripts / "upgrade_wavefoundry.py")
        run = subprocess.run([sys.executable, "-B", str(self.driver), str(self.root), str(self.pack), action],
                             cwd=self.root, capture_output=True, text=True, timeout=120,
                             env={**os.environ, "PROJECT_ROOT": str(self.root), "PYTHONDONTWRITEBYTECODE": "1",
                                  "TMPDIR": str(self.temp), "TMP": str(self.temp), "TEMP": str(self.temp),
                                  "WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1"})
        # Dry-run inventory also prints the entire hook source verbatim. Only
        # inspect emitted diagnostics and summaries, outside that inventory.
        output = run.stdout.split("── End extension module ──")[-1] + run.stderr
        return run.returncode, output

    def snapshot(self):
        return {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*")
                if p.is_file() and not any(p.is_relative_to(self.root / ".wavefoundry" / area)
                                           for area in ("logs", "locks", "cache/pycache"))
                and p != self.root / ".wavefoundry/lifecycle-mutation.lock"}

    def check_apply(self, source, version=None):
        if version:
            shutil.copyfile(SCRIPTS / f"tests/fixtures/upgrade_old_runner/upgrade_runner_v{version}.py.txt",
                            self.scripts / "upgrade_wavefoundry.py")
        before = self.snapshot()
        code, output = self.drive()
        self.assertEqual(code, 3, output[-3200:])
        self.assertIn("docs_preflight_failed", output[-3600:])
        self.assertIn(source, output[-3600:])
        self.assertIn("wf_upgrade(phase='preflight_to_docs_gate')", output)
        after = self.snapshot()
        self.assertEqual(after.keys(), before.keys())
        self.assertEqual([key for key, data in after.items() if data != before[key]], [])
        # Unquote the single POSIX path, including spaces; this test also runs
        # on Windows where list2cmdline uses double quotes instead.
        retry = output.rsplit(" upgrade --pack ", 1)[-1].split(" or wf_upgrade", 1)[0].strip().strip("\"'")
        self.assertTrue(Path(retry).is_file(), retry)

    def test_current_and_old_apply_refuse_before_extraction(self):
        self.set_linter("ERROR: docs/example.md: missing metadata")
        for version in (None, "1_22_0", "1_31_0"):
            with self.subTest(version=version):
                self.check_apply("missing metadata", version)

    def test_incoming_scan_refuses_without_installed_rule(self):
        self.document.write_bytes(b"# Example\nmiddle\x01end")
        self.check_apply("U+0001 (rule added by incoming version)")
        code, output = self.drive("dry")
        self.assertEqual(code, 0, output[-1800:])
        self.assertIn("docs_preflight_failed: upgrade would be refused", output)
        self.assertIn("U+0001", output)

        # Hold the target and real pack constant, suppress only the new hook,
        # and observe the same control byte reach the real final docs gate.
        code, output = self.drive("without-preflight")
        self.assertNotEqual(code, 0)
        self.assertIn("EXTRACTION COMPLETE", output)
        log = (self.root / ".wavefoundry/logs/upgrade.log").read_text()
        self.assertIn("docs/example.md:2:7: control character U+0001", output + log)
        lock = json.loads((self.root / ".wavefoundry/upgrade-in-progress.json").read_bytes())
        self.assertEqual(lock["failed_phase"], "docs_gate")

    def test_incoming_scan_keeps_raw_path_for_classification_and_escapes_display(self):
        name = "target\u202e\U0001f600.md"
        path = self.root / "docs" / name
        path.write_bytes(b"# Title\n\x01\n")
        result, output = self.preview()
        self.assertEqual(result["blocking"], 1)
        self.assertIn(r"docs/target\u202e\U0001f600.md:2:1: control character U+0001", output)
        self.assertNotIn(name, output)
        self.assertTrue(result["findings"][0].isascii())

    def test_preexisting_indeterminate_error_reaches_real_docs_gate(self):
        # This fixture remains invalid through extraction. The installed linter
        # names a directory with no attributable document; the final gate reads
        # the real malformed document with the newly extracted linter.
        self.set_linter("ERROR: unplaceable pre-existing document error")
        folder = self.root / record_paths.WAVES_ROOT / "123ab unknown"
        folder.mkdir(parents=True)
        record = folder / vocabulary_profile.RECORD_FILENAME
        record.write_text("# Record with unknown status\n", encoding="utf-8")
        affected = folder / "example.md"
        affected.write_text("# First line\nFixture\x01\n", encoding="utf-8")
        code, output = self.drive("gate")
        self.assertIn("docs_preflight_indeterminate", output)
        self.assertIn("EXTRACTION COMPLETE", output)
        self.assertNotEqual(code, 0)
        # The failing post-upgrade lint identifies the very same pre-existing
        # file even though its live status was indeterminate before extraction.
        log = (self.root / ".wavefoundry/logs/upgrade.log").read_text()
        self.assertIn(affected.relative_to(self.root).as_posix() + ":2:8: control character U+0001", output + log)
        lock = json.loads((self.root / ".wavefoundry/upgrade-in-progress.json").read_bytes())
        self.assertEqual(lock["failed_phase"], "docs_gate")
        self.assertIn("upgrade --resume-after-gate", output)

    def test_installed_and_control_findings_obey_target_layout(self):
        layout_file = self.scripts / "record_paths.py"
        layout_file.write_text(layout_file.read_text() + "\nWAVES_ROOT='records/sets'\nARCHIVE_ROOT='docs/retired'\nNESTED=True\n")
        record = self.root / "records/sets/team/12345 old"
        record.mkdir(parents=True)
        doc = record / vocabulary_profile.RECORD_FILENAME
        doc.write_bytes(b"# Record\nStatus: closed\n\n## Evidence\n\x01\n")
        archived = self.root / "docs/retired/archive.md"
        archived.parent.mkdir()
        archived.write_bytes(b"# History\n\x01\n")
        self.set_linter("ERROR: " + doc.relative_to(self.root).as_posix() + ": historical marker",
                        "ERROR: docs/retired/archive.md: old formatting", "ERROR: [secrets] withheld")
        ctx = SimpleNamespace(root=self.root, zip_path=self.pack, dry_run=True)
        for dry in (True, False):
            ctx.dry_run = dry
            with contextlib.redirect_stdout(io.StringIO()):
                extension._docs_preflight(ctx)
            self.assertEqual(ctx.docs_preflight["verdict"], "passed", ctx.docs_preflight)
            self.assertGreaterEqual(ctx.docs_preflight["ignored_closed"], 2)
            self.assertEqual(ctx.docs_preflight["ignored_secrets"], 1)
        doc.write_text("# Record\nStatus: planned\n\n## Evidence\n\x01\n")
        self.set_linter()
        result, _ = self.preview()
        self.assertEqual(result["blocking"], 1, result)
        self.assertIn("U+0001", result["findings"][0])
        self.set_linter("ERROR: missing path", "ERROR: " + doc.relative_to(self.root).as_posix() + ": live record",
                        "ERROR: docs/retired/archive.md: history")
        ctx.dry_run = True
        with contextlib.redirect_stdout(io.StringIO()):
            extension._docs_preflight(ctx)
        self.assertEqual(ctx.docs_preflight["blocking"], 1)
        self.assertEqual(ctx.docs_preflight["indeterminate"], 1)
        self.assertEqual(ctx.docs_preflight["ignored_closed"], 1)

    def preview(self):
        ctx = SimpleNamespace(root=self.root, zip_path=self.pack, dry_run=True)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            extension._docs_preflight(ctx)
        return ctx.docs_preflight, output.getvalue()

    def test_dry_run_refuses_once_on_current_and_supported_old_runner(self):
        self.set_linter("ERROR: docs/example.md: live planning error")
        log = self.root / ".wavefoundry/logs/lint-calls"
        log.parent.mkdir(parents=True, exist_ok=True)
        self.linter.write_text('from pathlib import Path\nwith Path(%r).open("a") as log: log.write("call\\n")\n'
                               % str(log) + self.linter.read_text())
        for version in (None, "1_31_0", "1_22_0"):
            with self.subTest(version=version):
                log.write_text("")
                code, output = self.drive("dry", version)
                self.assertEqual(code, 0, output[-2200:])
                self.assertIn("docs_preflight_failed: upgrade would be refused", output)
                self.assertEqual(log.read_text(), "call\n")
                self.assertFalse((self.root / ".wavefoundry/upgrade-in-progress.json").exists())
                if version is None:
                    self.assertIn('"verdict": "would_be_refused"', output)
                    self.assertNotIn('Run without --dry-run', output.split("End Dry Run")[-1])

    def test_historical_v131_marker_ignores_closed_but_refuses_planned(self):
        folder = self.root / record_paths.WAVES_ROOT / "1293d mcp-server-foundation"
        folder.mkdir(parents=True, exist_ok=True)
        doc = folder / vocabulary_profile.RECORD_FILENAME
        rel = doc.relative_to(self.root).as_posix()
        # negative-fixture: replay the two v1.31 linter messages for a legacy record header.
        self.set_linter(f"ERROR: {rel}: review evidence: wave header must declare `review-evidence-source: events.jsonl`",
                        f"ERROR: {rel}: review evidence: legacy inline review-evidence wave is no longer readable; "
                        "migrate manually: move each record line from the fenced `jsonl` block into a sibling "
                        "`events.jsonl` ledger (one JSON object per line, LF-terminated), replace the "
                        # negative-fixture: preserve the complete migration instruction from the real v1.31 linter.
                        "`review-evidence-protocol:` header line with `review-evidence-source: events.jsonl`, "
                        "and regenerate the Finding Synthesis projection by replaying the last typed review event")
        header = "# Record\nStatus: {}\nreview-evidence-protocol: 1\n"
        doc.write_text(header.format("planned"))
        self.check_apply("legacy inline review-evidence")
        doc.write_text(header.format("closed"))
        code, output = self.drive()
        self.assertEqual(code, 77, output[-2200:])
        self.assertIn("ignored 0 secrets and 2 closed-history findings", output)
        self.assertIn("EXTRACTION COMPLETE", output)

    def test_cap_and_platform_retry_commands(self):
        self.set_linter(*(f"ERROR: docs/example.md: error {i:03}" for i in range(51)))
        result, output = self.preview()
        self.assertEqual(result["blocking"], 51)
        self.assertEqual(len(result["findings"]), 50)
        self.assertIn("error 049", output)
        self.assertNotIn("error 050", output)
        self.assertIn("1 additional findings omitted", output)
        self.assertEqual(extension._docs_preflight_command("a b.zip", platform_name="nt"),
                         r'.\.wavefoundry\bin\wf.cmd upgrade --pack "a b.zip"')
        self.assertEqual(extension._docs_preflight_command("a b.zip", platform_name="posix"),
                         "./.wavefoundry/bin/wf upgrade --pack 'a b.zip'")

    def test_indeterminate_linter_and_scan_conditions_never_refuse(self):
        for name, source in (("missing", None),
                             ("rejects --read-only", 'import sys; sys.exit("unrecognized arguments: --read-only")'),
                             ("without ERROR", "raise SystemExit(8)"),
                             ("undecodable", 'import sys; sys.stdout.buffer.write(bytes([255])); sys.exit(1)')):
            with self.subTest(cause=name):
                if source is None:
                    self.linter.unlink()
                else:
                    self.linter.write_text(source)
                result, output = self.preview()
                self.assertEqual(result["verdict"], "indeterminate")
                self.assertIn(name, output)
        with patch.object(extension, "_preflight_marker", side_effect=OSError("synthetic fault")):
            self.assertIn("preflight fault", self.preview()[1])
        self.linter.write_text("import time; time.sleep(3)")
        config = self.root / "docs/workflow-config.json"
        config.write_text('{"docs_lint":{"full_scan_timeout_seconds":0.1}}')
        self.assertIn("installed lint timed out", self.preview()[1])
        self.set_linter()
        self.pack = self.root.parent / "empty.zip"
        with zipfile.ZipFile(self.pack, "w"):
            pass
        self.assertIn("incoming control-character scan unavailable", self.preview()[1])

    def test_retained_markers_skip_both_children(self):
        for marker in ("upgrade-in-progress.json", "upgrade-manifest-old.json", "index/sqlite-migration.json"):
            path = self.root / ".wavefoundry" / marker
            path.parent.mkdir(parents=True, exist_ok=True)
            for body in ('{"state":"restart_required"}', 'invalid json'):
                with self.subTest(marker=marker, body=body):
                    path.write_text(body)
                    with patch.object(extension, "_preflight_child") as child:
                        self.assertIn(marker, self.preview()[1])
                        child.assert_not_called()
            path.unlink()

    def test_real_manifest_retry_ignores_lint_on_the_extracted_tree(self):
        code, output = self.drive("retain")
        self.assertIn("test rendering failure", output)
        self.assertNotEqual(code, 0)
        lock = self.root / ".wavefoundry/upgrade-in-progress.json"
        self.assertEqual(json.loads(lock.read_bytes())["failed_phase"], "surface_rendering")
        self.assertTrue((self.root / ".wavefoundry/upgrade-manifest-old.json").is_file())
        log = self.root / ".wavefoundry/logs/lint-calls"
        self.set_linter("ERROR: docs/example.md: would fail while recovering")
        self.linter.write_text(f"from pathlib import Path\nPath({str(log)!r}).touch()\n" + self.linter.read_text())
        code, output = self.drive("dry")
        self.assertNotIn("docs_preflight_failed:", output)
        self.assertIn("docs_preflight_indeterminate", output)
        code, output = self.drive()
        self.assertIn("docs_preflight_indeterminate", output)
        self.assertIn("EXTRACTION COMPLETE", output)
        self.assertEqual(code, 77, output[-1800:])
        self.assertFalse(log.exists())

    def test_indeterminate_and_secret_only_upgrades_reach_extraction(self):
        # Each run starts with a fresh installed tree. In particular, a lock
        # from an earlier subtest must never mask a failure in this one.
        original = self.root
        for case, script, expected in (
            ("missing", None, "installed docs linter missing"),
            ("old", 'raise SystemExit("unrecognized arguments: --read-only")', "rejects --read-only"),
            ("empty", "raise SystemExit(7)", "without ERROR"),
            ("bytes", 'import sys; sys.stdout.buffer.write(bytes([255])); sys.exit(1)', "undecodable"),
            ("timeout", "import time; time.sleep(4)", "installed lint timed out"),
            ("fault", "", "preflight fault"),
            ("secrets", 'print("ERROR: docs/example.md: [secrets] withheld"); raise SystemExit(1)',
             "ignored 1 secrets"),
        ):
            with self.subTest(case=case):
                self.root = original.parent / case
                shutil.copytree(original, self.root)
                linter = self.root / ".wavefoundry/framework/scripts/docs_lint.py"
                if script is None:
                    linter.unlink()
                else:
                    linter.write_text(script)
                if case == "timeout":
                    config = self.root / "docs/workflow-config.json"
                    data = json.loads(config.read_bytes())
                    data["docs_lint"] = {"full_scan_timeout_seconds": 0.15}
                    config.write_text(json.dumps(data))
                code, output = self.drive("fault" if case == "fault" else "apply")
                self.assertEqual(code, 77, output[-1600:])
                self.assertIn(expected, output)
                self.assertIn("EXTRACTION COMPLETE", output)
                self.assertNotIn("docs_preflight_failed:", output)

    def test_pathless_status_and_missing_layout_are_indeterminate(self):
        record = self.root / record_paths.WAVES_ROOT / "123aa ambiguous"
        record.mkdir(parents=True)
        document = record / vocabulary_profile.RECORD_FILENAME
        document.write_text("# Record\nStatus: closed\nStatus: planned\n")
        lines = ["ERROR: path unknown", "ERROR: docs/no-such-doc.md: missing document",
                 "ERROR: " + document.relative_to(self.root).as_posix() + ": note"]
        self.set_linter(*lines)
        result, _ = self.preview()
        self.assertEqual((result["blocking"], result["indeterminate"]), (0, 3))
        self.set_linter(*lines, "ERROR: docs/example.md: independently live")
        result, _ = self.preview()
        self.assertEqual((result["blocking"], result["indeterminate"]), (1, 3))
        (self.scripts / "record_paths.py").unlink()
        result, output = self.preview()
        self.assertEqual((result["blocking"], result["indeterminate"]), (0, 4))
        self.assertIn("layout unavailable", output)

    def test_installed_lint_uses_owner_status_for_saved_record(self):
        owner = self.root / record_paths.WAVES_ROOT / "1293d owner"
        saved = owner / "evidence/snapshot"
        saved.mkdir(parents=True, exist_ok=True)
        name = vocabulary_profile.RECORD_FILENAME
        relative = (saved / name).relative_to(self.root).as_posix()
        finding = f"ERROR: {relative}: stale metadata"
        self.set_linter(finding)
        for outer, inner, expected in (("closed", "active", 0), ("active", "closed", 1)):
            with self.subTest(outer=outer, inner=inner):
                (owner / name).write_text(f"# Owner\nStatus: {outer}\n")
                (saved / name).write_text(f"# Copy\nStatus: {inner}\n")
                result, _ = self.preview()
                self.assertEqual(result["blocking"], expected)
                self.assertEqual(result["ignored_closed"], 1 - expected)

    def test_visible_status_governs_installed_and_incoming_findings(self):
        owner = self.root / record_paths.WAVES_ROOT / "1293d header"
        owner.mkdir(parents=True)
        record = owner / vocabulary_profile.RECORD_FILENAME
        member = owner / "member.md"
        relative = member.relative_to(self.root).as_posix()
        error = f"ERROR: {relative}: fixture error"
        cases = (
            ("<!--\n## Example\nStatus: closed\n-->", "active", "live"),
            ("~~~md\n## Example\nStatus: closed\n~~~", "implementing", "live"),
            ("<!--\n## Example\nStatus: active\n-->", "closed", "closed"),
            ("```md\n## Example\nStatus: active\n```", "completed", "closed"),
            ("<!--\nStatus: active\n-->", None, "unknown"),
            ("Status: active", "closed", "unknown"),
        )
        for hidden, visible, expected in cases:
            with self.subTest(hidden=hidden, visible=visible):
                header = hidden + "\n" + (f"Status: {visible}\n" if visible else "")
                record.write_text("# Header\n" + header + "\n## Body\nStatus: paused\n")
                member.write_text("# Member\n")
                self.set_linter(error)
                result, _ = self.preview()
                self.assertEqual((result["blocking"], result["ignored_closed"], result["indeterminate"]),
                                 (int(expected == "live"), int(expected == "closed"), int(expected == "unknown")))
                self.set_linter()
                member.write_bytes(b"# Member\nfield sample: \x00\n")
                result, _ = self.preview()
                self.assertEqual(result["blocking"], int(expected == "live"))
                if expected == "live":
                    self.assertIn(relative + ":2:15: control character U+0000", result["findings"][0])
                elif expected == "unknown":
                    self.assertEqual(result["indeterminate"], 1)

    @unittest.skipIf(os.name == "nt", "a native Windows filename cannot contain a colon")
    def test_colon_in_record_root_never_becomes_a_different_live_document(self):
        prefix = self.root / "docs/releases.md"
        prefix.write_text("# Current release\n")
        for delimiter in (":", ": "):
            with self.subTest(delimiter=delimiter):
                waves = "docs/releases.md" + delimiter + "records"
                layout = self.scripts / "record_paths.py"
                layout.write_text(layout.read_text() + f"\nWAVES_ROOT={waves!r}\n")
                directory = self.root / waves / "1293d closed"
                directory.mkdir(parents=True)
                record = directory / vocabulary_profile.RECORD_FILENAME
                record.write_text("# Record\nStatus: closed\n")
                relative = record.relative_to(self.root).as_posix()
                history = f"ERROR: {relative}: legacy record"
                live = "ERROR: docs/example.md:2:4: verified live error"
                self.set_linter(history)
                result, _ = self.preview()
                self.assertEqual(result["blocking"], 0, result)
                self.assertEqual(result["ignored_closed"] + result["indeterminate"], 1)
                self.set_linter(history, live)
                result, _ = self.preview()
                self.assertEqual(result["findings"], [live])
                self.check_apply("verified live error")
        # With the unrelated prefix still in place the real fresh upgrade
        # reaches extraction when the only remaining report concerns history.
        self.set_linter(history)
        code, output = self.drive()
        self.assertEqual(code, 77, output[-1200:])
        self.assertIn("EXTRACTION COMPLETE", output)


class PreflightDiagnosticPathTests(unittest.TestCase):
    def test_path_delimiter_and_unquoted_ambiguity(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (root / "docs").mkdir()
        (root / "docs/example.md").write_text("# Live")
        layout = {"waves": "docs/releases.md: records", "archive": None, "memory_archive": None}
        cases = (
            ("docs/example.md:2:4: control character", "docs/example.md"),
            ("docs/example.md: review evidence: stale projection", "docs/example.md"),
            ("docs/example.md: review evidence: 'status.jsonl' expected: fix the ledger", "docs/example.md"),
            ("docs/unplaceable.md: punctuation in prose:", None),
            ("without a document", None),
        )
        for body, expected in cases:
            with self.subTest(body=body):
                self.assertEqual(extension._preflight_error_path(root, "ERROR: " + body, layout), expected)
