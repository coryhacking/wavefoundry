"""The local repair changes runtime source only and refuses unrelated checkpoints."""
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock
import zipfile

import repair_ppol_memory_staging as repair


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "project"
        self.scripts = self.root / repair.SCRIPTS
        self.scripts.mkdir(parents=True)
        self.index = self.root / ".wavefoundry/index"
        self.index.mkdir()
        self.kit = self.base / "kit"
        (self.kit / "fixed").mkdir(parents=True)
        self.old = {name: ("# original " + name + "\n").encode() for name in repair.OLD_HASHES}
        self.fixed = {name: ("# fixed " + name + "\n").encode() for name in self.old}
        self.runner = b"# pinned runner\n"
        self.hashes = {name: repair.digest(data) for name, data in self.old.items()}
        feature_io = io.BytesIO()
        with zipfile.ZipFile(feature_io, "w") as z:
            for name, data in self.old.items():
                z.writestr(repair.SCRIPTS + "/" + name, data)
        self.feature = feature_io.getvalue()
        self.recorded_pack = self.base / "retained-feature.zip"
        self.recorded_pack.write_bytes(self.feature)
        self.pack = self.base / "original.zip"
        with zipfile.ZipFile(self.pack, "w") as z:
            z.writestr("payload/wavefoundry-1.24.0.ppol.zip", self.feature)
        for target, value in (("OLD_HASHES", self.hashes), ("PACK_SHA256", repair.digest(self.pack.read_bytes())),
                              ("FEATURE_SHA256", repair.digest(self.feature)), ("RUNNER_HASH", repair.digest(self.runner))):
            patch = mock.patch.object(repair, target, value)
            patch.start()
            self.addCleanup(patch.stop)
        patch = mock.patch.object(repair, "hosts", return_value=([], ["best effort"]))
        self.hosts = patch.start()
        self.addCleanup(patch.stop)
        (self.scripts.parent / "VERSION").write_text(repair.VERSION)
        (self.scripts / "upgrade_wavefoundry.py").write_bytes(self.runner)
        for name in self.old:
            (self.scripts / name).write_bytes(self.old[name])
            (self.kit / "fixed" / name).write_bytes(self.fixed[name])
        (self.kit / "repair-manifest.json").write_text(json.dumps({name: repair.digest(data) for name, data in self.fixed.items()}))
        self.source = self.index / "index-state.sqlite"
        conn = sqlite3.connect(self.source)
        conn.execute("CREATE TABLE meta (key TEXT, value TEXT)")
        conn.execute("INSERT INTO meta VALUES ('store_schema_version','7')")
        conn.commit()
        conn.close()
        self.memory = self.index / "memory-state.sqlite"
        conn = sqlite3.connect(self.memory)
        conn.execute("CREATE TABLE memory_backfill_runs (run_id TEXT, state TEXT)")
        conn.execute("INSERT INTO memory_backfill_runs VALUES ('run1','ready_for_index')")
        conn.commit()
        conn.close()
        self.work = self.index / ("index-migration-" + "a" * 32)
        self.work.mkdir()
        self.receipt = dict(receipt_version=2, kind="index_sqlite_schema8", state="staged",
                            migration_id="a" * 32, index_dir=str(self.index), root_identity=repair.identity(self.root),
                            target_version=repair.VERSION, pack_sha256=repair.PACK_SHA256, source_database="legacy",
                            source_sqlite_identity=repair.identity(self.source), work_dir=self.work.name,
                            work_identity=repair.identity(self.work), staging_pid=123456)
        self.checkpoint = dict(to_version=repair.VERSION, storage_migration_id="a" * 32,
                               failed_phase="index_update", current_phase="memory_resume_preflight", memory_backfill_run_id="run1", pid=123455, zip_path=str(self.recorded_pack))
        self.write_state()

    def write_state(self):
        (self.index / "sqlite-migration.json").write_text(json.dumps(self.receipt))
        (self.root / ".wavefoundry/upgrade-in-progress.json").write_text(json.dumps(self.checkpoint))

    def run_repair(self, apply=False):
        return repair.apply_repair(self.root, self.pack, self.kit, apply=apply, confirm_hosts_stopped=apply)

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_dry_run_writes_nothing_and_returns_retained_phase(self):
        before = self.snapshot()
        result = self.run_repair()
        self.assertEqual("dry_run", result["status"])
        self.assertIn("--resume-after-memory", result["command_argv"])
        self.assertNotIn("--yes", result["command_argv"])
        self.assertEqual(before, self.snapshot())

    def test_apply_is_idempotent_retains_backups_and_does_not_touch_recovery_data(self):
        before = self.snapshot()
        self.assertEqual("applied", self.run_repair(True)["status"])
        after = self.snapshot()
        self.run_repair(True)
        self.assertEqual(after, self.snapshot())
        for name, data in before.items():
            if name not in {repair.SCRIPTS + "/" + n for n in self.old}:
                self.assertEqual(data, after[name], name)
        for name, data in self.fixed.items():
            self.assertEqual(data, (self.scripts / name).read_bytes())
            self.assertEqual(self.old[name], (self.root / ".wavefoundry/repair-backups/ppol-memory-staging" / name).read_bytes())

    def test_retained_outer_archive_applies_without_rewriting_checkpoint(self):
        self.recorded_pack.write_bytes(self.pack.read_bytes())
        before = self.snapshot()
        self.assertEqual("dry_run", self.run_repair()["status"])
        self.assertEqual(before, self.snapshot())
        self.assertEqual("applied", self.run_repair(True)["status"])
        after = self.snapshot()
        for name, data in before.items():
            if name not in {repair.SCRIPTS + "/" + n for n in self.old}:
                self.assertEqual(data, after[name], name)
        self.assertEqual(self.pack.read_bytes(), self.recorded_pack.read_bytes())

    def test_changed_retained_outer_archive_is_refused_without_writes(self):
        self.recorded_pack.write_bytes(self.pack.read_bytes() + b"changed")
        before = self.snapshot()
        with self.assertRaisesRegex(repair.Refused, "checkpoint package"):
            self.run_repair(True)
        self.assertEqual(before, self.snapshot())

    def test_both_reported_checkpoint_phases_are_supported(self):
        self.checkpoint["current_phase"] = "awaiting_memory_validation"
        self.write_state()
        self.assertEqual("dry_run", self.run_repair()["status"])

    def test_apply_requires_confirmation_even_when_discovery_is_empty(self):
        with self.assertRaisesRegex(repair.Refused, "confirm-hosts-stopped"):
            repair.apply_repair(self.root, self.pack, self.kit, apply=True)

    def test_running_hosts_block_apply(self):
        self.hosts.return_value = ([{"pid": 1234, "kind": "mcp"}], [])
        before = self.snapshot()
        with self.assertRaisesRegex(repair.Refused, "still running"):
            self.run_repair(True)
        self.assertEqual(before, self.snapshot())

    def test_unrelated_receipt_and_checkpoint_are_refused_without_writes(self):
        cases = [(self.receipt, "state", "cutover_pending"), (self.receipt, "source_database", "current"),
                 (self.receipt, "root_identity", {}), (self.receipt, "work_identity", {}),
                 (self.receipt, "pack_sha256", "wrong"), (self.receipt, "kind", "other"),
                 (self.checkpoint, "current_phase", "extract"), (self.checkpoint, "failed_phase", "docs_gate"),
                 (self.checkpoint, "storage_migration_id", "b" * 32), (self.checkpoint, "memory_backfill_run_id", "absent")]
        for record, key, value in cases:
            with self.subTest(key=key, value=value):
                original = record[key]
                record[key] = value
                self.write_state()
                before = self.snapshot()
                with self.assertRaises(repair.Refused):
                    self.run_repair(True)
                self.assertEqual(before, self.snapshot())
                record[key] = original
        self.write_state()

    def test_altered_pack_is_refused(self):
        self.pack.write_bytes(self.pack.read_bytes() + b"changed")
        with self.assertRaisesRegex(repair.Refused, "Package differs"):
            self.run_repair(True)

    def test_altered_runtime_or_payload_is_refused(self):
        for path in [self.scripts / next(iter(self.old)), self.scripts / "upgrade_wavefoundry.py", self.kit / "fixed" / next(iter(self.old))]:
            with self.subTest(path=path):
                original = path.read_bytes()
                path.write_bytes(b"changed")
                with self.assertRaises(repair.Refused):
                    self.run_repair(True)
                path.write_bytes(original)

    def test_conflicting_backup_refuses_before_source_replacement(self):
        backup = self.root / ".wavefoundry/repair-backups/ppol-memory-staging"
        backup.mkdir(parents=True)
        (backup / next(iter(self.old))).write_bytes(b"unowned")
        before = self.snapshot()
        with self.assertRaisesRegex(repair.Refused, "backup differs"):
            self.run_repair(True)
        self.assertEqual(before, self.snapshot())

    def test_wrong_schema_and_already_published_database_are_refused(self):
        conn = sqlite3.connect(self.source)
        conn.execute("UPDATE meta SET value='8'")
        conn.commit()
        conn.close()
        with self.assertRaisesRegex(repair.Refused, "schema 7"):
            self.run_repair()
        (self.index / "index.sqlite").write_bytes(b"other")
        with self.assertRaisesRegex(repair.Refused, "sole pre-cutover"):
            self.run_repair()

    def test_symlink_and_reparse_components_refused(self):
        alias = self.base / "alias"
        try:
            alias.symlink_to(self.root, target_is_directory=True)
        except OSError:
            pass  # Native Windows may deny symlink creation; reparse branch below is always exercised.
        else:
            with self.assertRaisesRegex(repair.Refused, "Redirected"):
                repair.safe(alias / "child", self.base)
        info = mock.Mock(st_mode=0, st_file_attributes=0x400)
        with mock.patch.object(Path, "lstat", return_value=info):
            with self.assertRaisesRegex(repair.Refused, "Redirected"):
                repair.safe(self.root)

    def test_missing_or_changed_retained_feature_never_falls_back_to_another_pack(self):
        self.recorded_pack.unlink()
        with self.assertRaises(OSError):
            self.run_repair()
        self.recorded_pack.write_bytes(b"another pack")
        with self.assertRaisesRegex(repair.Refused, "checkpoint package"):
            self.run_repair()

    def test_recorded_coordinator_ids_are_checked_in_addition_to_host_discovery(self):
        self.run_repair()
        self.hosts.assert_called_once_with(self.root, [123455, 123456])
        self.receipt["staging_pid"] = None
        self.write_state()
        with self.assertRaisesRegex(repair.Refused, "PID"):
            self.run_repair()

    def test_build_kit_embeds_exact_fixed_bytes_and_refuses_overwrite(self):
        source = self.base / "source"
        source.mkdir()
        script = source / "repair_ppol_memory_staging.py"
        script.write_bytes(Path(repair.__file__).read_bytes())
        for name, data in self.fixed.items():
            (source / name).write_bytes(data)
        output = self.base / "repair.zip"
        with mock.patch.object(repair, "__file__", str(script)):
            repair.build_kit(output, self.pack)
            with self.assertRaises(FileExistsError):
                repair.build_kit(output, self.pack)
        with zipfile.ZipFile(output) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()), {script.name, "repair-manifest.json", "README.txt"}
                             | {"fixed/" + name for name in self.fixed})
            for name, data in self.fixed.items():
                self.assertEqual(archive.read("fixed/" + name), data)

    def test_partial_replacement_can_be_retried(self):
        (self.scripts / next(iter(self.fixed))).write_bytes(next(iter(self.fixed.values())))
        self.run_repair(True)
        for name, data in self.fixed.items():
            self.assertEqual(data, (self.scripts / name).read_bytes())


if __name__ == "__main__":
    unittest.main()
