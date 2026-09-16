"""Installed-tree storage ownership, real cutover, and recovery boundaries."""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import setup_reconciliation as setup
import sqlite_storage_migration as migration
import upgrade_lib


class SetupReceiptTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.framework = self.root / ".wavefoundry/framework"
        self.framework.mkdir(parents=True)
        (self.framework / "VERSION").write_text("1.24.0")
        (self.framework / "behavior.py").write_text("VALUE = 1\n")
        self.index = self.root / ".wavefoundry/index"
        self.index.mkdir()
        self.addCleanup(patch.stopall)
        patch.object(migration, "discover_hosts", return_value=([], [])).start()

    def legacy(self):
        (self.index / "docs.lance").mkdir()
        (self.index / "docs.lance/data").write_bytes(b"preserve")

    def pause(self):
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as stopped:
            with setup.session(self.root, ["--root", str(self.root)]) as run:
                run.prepare()
        self.assertEqual(stopped.exception.code, 3)
        return migration.read_receipt(self.index)

    def test_fresh_setup_has_no_receipt_and_no_archive_discovery(self):
        (self.root / "unrelated.zip").write_bytes(b"not an archive")
        import upgrade_wavefoundry
        with patch.object(upgrade_wavefoundry, "_find_zip", side_effect=AssertionError("archive discovery")):
            for _ in range(2):
                with setup.session(self.root, []) as run:
                    self.assertFalse(run.requires_index)
                    run.prepare()
                    run.complete()
        self.assertIsNone(migration.read_receipt(self.index))
        self.assertIsNone(upgrade_lib.read_upgrade_lock(self.root))

    def test_pause_binds_source_and_setup_continuation(self):
        self.legacy()
        receipt = self.pause()
        action = receipt["restart_action"]
        self.assertEqual(receipt["entry_path"], "setup")
        self.assertIn("setup_wavefoundry.py", action["command_argv"][1])
        self.assertIn("--confirm-hosts-stopped", action["command_argv"])
        self.assertNotIn("--pack", action["command_argv"])
        self.assertIsNotNone(migration.read_restart_action(self.root, 3, action["invocation_token"]))
        self.assertEqual((self.index / "docs.lance/data").read_bytes(), b"preserve")

    def test_setup_preflight_recovery_keeps_recorded_owner(self):
        import setup_index
        import sqlite_runtime
        self.legacy()
        self.pause()
        for failure in (sqlite_runtime.RuntimeUnavailable("binding unavailable"),
                        sqlite_runtime.StorageRecoveryRequired("WAL unavailable")):
            with self.subTest(failure=type(failure).__name__):
                with patch.object(setup_index, "ensure_migration_deps"), \
                        patch.object(sqlite_runtime, "preflight", side_effect=failure):
                    with self.assertRaises(migration.MigrationRequired) as caught:
                        with setup.session(self.root, ["--confirm-hosts-stopped"]) as run:
                            run.prepare()
                message = str(caught.exception)
                self.assertIn("recorded owning setup or upgrade continuation", message)
                self.assertNotIn("wf_upgrade", message)
                self.assertEqual(migration.read_receipt(self.index)["entry_path"], "setup")
                self.assertEqual((self.index / "docs.lance/data").read_bytes(), b"preserve")

    def test_shared_forward_and_cleanup_advice_preserves_owner(self):
        for message in (migration._forward_recovery(self.index / "index-state.sqlite"),
                        str(migration._unknown_staging(self.index / "unknown"))):
            self.assertIn("recorded owning setup or upgrade continuation", message)
            self.assertNotIn("standard upgrade", message)
            self.assertNotIn("wf_upgrade", message)

    def test_same_version_source_drift_refuses_without_changing_receipt(self):
        self.legacy()
        self.pause()
        before = (self.index / migration.RECEIPT).read_bytes()
        (self.framework / "behavior.py").write_text("VALUE = 2\n")
        with self.assertRaisesRegex(setup.MigrationRequired, "source_changed"):
            with setup.session(self.root, ["--confirm-hosts-stopped"]):
                self.fail("drift guard bypassed")
        self.assertEqual(before, (self.index / migration.RECEIPT).read_bytes())

    def test_source_guard_control_detects_injected_bypass(self):
        self.legacy()
        receipt = self.pause()
        (self.framework / "behavior.py").write_text("CHANGED = True\n")
        with self.assertRaises(setup.MigrationRequired):
            setup.validate_source_binding(self.root, receipt)
        # Control: replacing the fingerprint oracle makes the same drift pass.
        with patch.object(setup, "framework_fingerprint", return_value=receipt["installed_framework_sha256"]):
            setup.validate_source_binding(self.root, receipt)

    def test_foreign_checkpoint_preserved_before_any_setup_write(self):
        upgrade_lib.write_upgrade_lock(self.root, "old", "new", self.root / "original.zip")
        path = upgrade_lib.upgrade_lock_path(self.root)
        before = path.read_bytes()
        with self.assertRaisesRegex(setup.MigrationRequired, "foreign_upgrade"):
            with setup.session(self.root, []):
                self.fail("foreign owner accepted")
        self.assertEqual(before, path.read_bytes())

    def test_foreign_owner_guard_control_detects_injected_bypass(self):
        upgrade_lib.write_upgrade_lock(self.root, "old", "new", self.root / "original.zip")
        with self.assertRaises(setup.MigrationRequired):
            with setup.session(self.root, []):
                self.fail("owner guard bypassed")
        reached = False
        with patch.object(setup.session, "_inspect", return_value=(None, None)):
            with setup.session(self.root, []):
                reached = True
        self.assertTrue(reached, "control mutation must cross the ownership boundary")

    def test_package_receipt_without_checkpoint_is_not_adopted(self):
        self.legacy()
        receipt = self.pause()
        receipt.pop("entry_path")
        receipt.update(pack_path=str(self.root / "original.zip"), pack_sha256="a" * 64)
        migration._write(self.index, receipt)
        upgrade_lib.remove_upgrade_lock(self.root)
        before = (self.index / migration.RECEIPT).read_bytes()
        with self.assertRaisesRegex(setup.MigrationRequired, "foreign_upgrade"):
            with setup.session(self.root, []):
                self.fail("archive owner accepted")
        self.assertEqual(before, (self.index / migration.RECEIPT).read_bytes())
        self.assertIsNone(upgrade_lib.read_upgrade_lock(self.root))

    def test_lost_checkpoint_restores_setup_owner(self):
        self.legacy()
        receipt = self.pause()
        upgrade_lib.remove_upgrade_lock(self.root)
        migration.restore_checkpoint(self.root)
        restored = upgrade_lib.read_upgrade_lock(self.root)
        self.assertEqual(restored["entry_path"], "setup")
        self.assertEqual(restored["installed_framework_sha256"], receipt["installed_framework_sha256"])
        self.assertEqual(restored["root_identity"], receipt["root_identity"])

    def test_no_database_old_host_requires_handoff_and_refuses_live_resume(self):
        host = {"kind": "mcp", "pid": 12345}
        with patch.object(migration, "discover_hosts", return_value=([host], [])):
            receipt = self.pause()
            self.assertEqual(receipt["reason"], "existing_framework_without_index")
            with patch.object(migration, "_host_is_running", return_value=True):
                with self.assertRaises(setup.MigrationRequired):
                    with setup.session(self.root, ["--confirm-hosts-stopped"]) as run:
                        run.prepare()
        self.assertFalse((self.index / "index.sqlite").exists())

    def test_setup_receipt_cannot_be_resumed_by_upgrade(self):
        self.legacy()
        self.pause()
        from types import SimpleNamespace
        ctx = SimpleNamespace(root=self.root, zip_path=None, from_version="1.24.0", to_version="1.24.0")
        with self.assertRaisesRegex(setup.MigrationRequired, "setup_resume_required"):
            migration.prepare_upgrade(ctx)

    def test_windows_continuation_quotes_and_strips_duplicate_root(self):
        with patch.object(migration.os, "name", "nt"):
            # pathlib constructs PosixPath from the existing concrete root on
            # POSIX; patch only the module's Path factory to keep that fixture.
            with patch.object(migration, "Path", type(self.root)):
                action = migration.restart_command(self.root, None, True, entry_path="setup",
                    setup_args=["--root", "old root", "--include-tests"])
        self.assertEqual(action["command_shell"], "PowerShell")
        self.assertEqual(action["command_argv"].count("--root"), 1)
        self.assertIn("--rebuild-storage", action["command_argv"])
        self.assertTrue(action["command"].startswith("& '"))

    def test_cache_change_does_not_change_installed_behavior_fingerprint(self):
        before = setup.framework_fingerprint(self.root)
        (self.framework / "test-cache.json").write_text("{}")
        cache = self.framework / "__pycache__"
        cache.mkdir()
        (cache / "ignored.pyc").write_bytes(b"cache")
        self.assertEqual(before, setup.framework_fingerprint(self.root))
        finder = self.framework / ".DS_Store"
        finder.write_bytes(b"Finder metadata")
        self.assertEqual(before, setup.framework_fingerprint(self.root))
        finder.unlink()
        self.assertEqual(before, setup.framework_fingerprint(self.root))

    def test_interrupted_publication_retains_checkpoint_and_grant_does_not_leak(self):
        self.legacy()
        self.pause()
        previous = os.environ.get(setup._PUBLISHER_ENV)
        with self.assertRaisesRegex(RuntimeError, "build failed"):
            with setup.session(self.root, ["--confirm-hosts-stopped"]) as run:
                with patch.object(migration, "begin_upgrade_publication"):
                    with run.publication():
                        self.assertTrue(os.environ.get(setup._PUBLISHER_ENV))
                        raise RuntimeError("build failed")
        self.assertEqual(previous, os.environ.get(setup._PUBLISHER_ENV))
        self.assertIsNotNone(upgrade_lib.read_upgrade_lock(self.root))
        self.assertEqual((self.index / "docs.lance/data").read_bytes(), b"preserve")

    def test_checkpoint_migration_id_cannot_be_removed(self):
        self.legacy()
        self.pause()
        upgrade_lib.update_upgrade_lock(self.root, storage_migration_id=None)
        with self.assertRaisesRegex(setup.MigrationRequired, "checkpoint_mismatch"):
            with setup.session(self.root, []):
                self.fail("missing operation identity accepted")

    def test_checkpoint_root_identity_mismatch_refuses_without_mutation(self):
        self.legacy()
        self.pause()
        upgrade_lib.update_upgrade_lock(self.root, root_identity={"device": -1, "inode": -1})
        checkpoint_path = upgrade_lib.upgrade_lock_path(self.root)
        checkpoint_before = checkpoint_path.read_bytes()
        receipt_before = (self.index / migration.RECEIPT).read_bytes()
        with self.assertRaisesRegex(setup.MigrationRequired, "checkpoint_mismatch"):
            with setup.session(self.root, ["--confirm-hosts-stopped"]):
                self.fail("changed checkpoint root identity accepted")
        self.assertEqual(checkpoint_before, checkpoint_path.read_bytes())
        self.assertEqual(receipt_before, (self.index / migration.RECEIPT).read_bytes())
        self.assertEqual((self.index / "docs.lance/data").read_bytes(), b"preserve")

    def test_model_preflight_failure_preserves_legacy_source(self):
        self.legacy()
        import setup_index
        with patch.object(setup_index, "main", return_value=2), self.assertRaisesRegex(setup.MigrationRequired, "models_unavailable"):
            with setup.session(self.root, ["--confirm-hosts-stopped", "--rebuild-storage"]) as run:
                run.prepare()
        self.assertEqual((self.index / "docs.lance/data").read_bytes(), b"preserve")
        self.assertIsNotNone(upgrade_lib.read_upgrade_lock(self.root))

    def test_runtime_provisioning_reclassifies_current_store_without_restart(self):
        real = migration.detect(self.index)
        initial = dict(real, migration_required=True, authority_role="current", sqlite_schema="runtime_unavailable")
        ready = dict(real, migration_required=False, authority_role="current", sqlite_schema=migration.SCHEMA_VERSION)
        with patch.object(migration, "detect", side_effect=[initial, ready]), patch.object(migration, "prepare_upgrade") as prepare:
            with setup.session(self.root, []) as run:
                self.assertTrue(run.requires_index)
                run.prepare()
                self.assertFalse(run.requires_index)
                run.complete()
        prepare.assert_not_called()
        self.assertIsNone(upgrade_lib.read_upgrade_lock(self.root))

    def test_upgrade_refuses_setup_owner_before_materialization_or_package_search(self):
        self.legacy()
        self.pause()
        import upgrade_wavefoundry
        before = upgrade_lib.upgrade_lock_path(self.root).read_bytes()
        with patch.object(upgrade_wavefoundry, "materialize_lifecycle_policy", side_effect=AssertionError("mutation")), \
             patch.object(upgrade_wavefoundry, "_find_zip", side_effect=AssertionError("package search")), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(upgrade_wavefoundry.main(["--root", str(self.root), "--materialize-lifecycle-policy"]), 3)
            self.assertEqual(upgrade_wavefoundry.main(["--root", str(self.root), "--yes"]), 3)
        self.assertEqual(before, upgrade_lib.upgrade_lock_path(self.root).read_bytes())

    def test_require_ready_dispatches_to_receipt_owner(self):
        self.legacy()
        with self.assertRaisesRegex(setup.MigrationRequired, "run wf setup"):
            migration.require_ready(self.index)
        receipt = self.pause()
        with self.assertRaisesRegex(setup.MigrationRequired, "run wf setup"):
            migration.require_ready(self.index)
        receipt.pop("entry_path")
        migration._write(self.index, receipt)
        with self.assertRaisesRegex(setup.MigrationRequired, "run wf_upgrade"):
            migration.require_ready(self.index)


class NativeSetupTests(unittest.TestCase):
    def setUp(self):
        import test_sqlite_storage_migration as fixtures
        self.fixture = fixtures.SchemaEightKindTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root, self.index = self.fixture.root, self.fixture.index
        framework = self.root / ".wavefoundry/framework"
        shutil.copytree(SCRIPTS, framework / "scripts",
                        ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"))
        (framework / "VERSION").write_text("1.24.0")
        self.addCleanup(patch.stopall)
        patch.object(migration, "discover_hosts", return_value=([], [])).start()

    def test_schema_seven_cutover_verifies_in_child_and_preserves_auxiliary(self):
        # Two installed checkouts: A supplies pulled framework bytes; B retains
        # its own older host-local database, memory and unrelated archive.
        with tempfile.TemporaryDirectory() as checkout:
            checkout_a = Path(checkout).resolve()
            source_framework = checkout_a / ".wavefoundry/framework"
            target_framework = self.root / ".wavefoundry/framework"
            shutil.copytree(target_framework, source_framework)
            (source_framework / "pulled-behavior.py").write_text("REVISION = 2\n")
            (target_framework / "pulled-behavior.py").write_text("REVISION = 1\n")
            source_hash = setup.framework_fingerprint(checkout_a)
            shutil.copytree(source_framework, target_framework, dirs_exist_ok=True)
            self.assertEqual(source_hash, setup.framework_fingerprint(self.root))
            self._complete_schema_seven_fixture()
            self.assertEqual(source_hash, setup.framework_fingerprint(checkout_a))
            self.assertFalse((checkout_a / ".wavefoundry/index").exists())

    def _complete_schema_seven_fixture(self):
        rows = [{"id": "retained-vector", "path": "docs/a.md", "kind": "docs",
                 "text": "preserve searchable embedding", "tags": [], "start_line": 1,
                 "end_line": 1, "vector": [1.0] + [0.0] * 383}]
        source = self.fixture._seed("7", rows=rows)
        import sqlite_runtime
        with contextlib.closing(sqlite_runtime.connect(source, read_only=True)) as conn:
            original_embedding = conn.execute("SELECT embedding FROM vectors_docs").fetchone()
        memory = self.index / "memory-state.sqlite"
        memory.write_bytes(b"separate memory fixture preserved")
        (self.root / "wavefoundry-unrelated.zip").write_bytes(b"not a package")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with setup.session(self.root, ["--confirm-hosts-stopped"]) as run:
                run.prepare()
                self.assertTrue(source.exists())
                self.assertEqual(run.index_args(["--background-code", "--docs-only"]), [])
                # The real staged kind already produced a complete all-layer
                # epoch; model-free fixture simulates the subsequent no-op pass.
                with run.publication():
                    pass
                run.complete()
        self.assertFalse(source.exists())
        self.assertEqual(memory.read_bytes(), b"separate memory fixture preserved")
        self.assertIsNone(upgrade_lib.read_upgrade_lock(self.root))
        receipt = migration.read_receipt(self.index)
        self.assertEqual(receipt["state"], "complete")
        self.assertNotEqual(receipt["verification"]["pid"], os.getpid())
        with contextlib.closing(sqlite_runtime.connect(self.fixture.current, read_only=True)) as conn:
            self.assertEqual(conn.execute("SELECT body FROM preserved_memory").fetchone(), ("retain me",))
            self.assertEqual(conn.execute("SELECT embedding FROM vectors_docs").fetchone(), original_embedding)
        with setup.session(self.root, []) as repeat:
            self.assertFalse(repeat.requires_index)
            repeat.complete()

    def test_failed_fresh_verification_retains_source_and_checkpoint(self):
        source = self.fixture._seed("7")
        import subprocess_util
        from types import SimpleNamespace
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(setup.MigrationRequired, "verification_failed"):
                with setup.session(self.root, ["--confirm-hosts-stopped"]) as run:
                    run.prepare()
                    with run.publication():
                        pass
                    with patch.object(subprocess_util, "isolated_run", return_value=SimpleNamespace(returncode=9)):
                        run.complete()
        self.assertTrue(source.exists())
        self.assertIsNotNone(upgrade_lib.read_upgrade_lock(self.root))
        self.assertNotEqual(migration.read_receipt(self.index)["state"], "complete")
        # Same installed source and original source identity recover forward.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with setup.session(self.root, ["--confirm-hosts-stopped"]) as retry:
                retry.prepare()
                with retry.publication():
                    pass
                retry.complete()
        self.assertFalse(source.exists())
        self.assertEqual(migration.read_receipt(self.index)["state"], "complete")
        self.assertIsNone(upgrade_lib.read_upgrade_lock(self.root))

    def test_newer_schema_refuses_preserving_database(self):
        source = self.fixture._seed("999")
        before = source.read_bytes()
        with self.assertRaisesRegex(setup.MigrationRequired, "schema_unsupported"):
            with setup.session(self.root, []):
                self.fail("newer schema accepted")
        self.assertEqual(source.read_bytes(), before)
        self.assertIsNone(upgrade_lib.read_upgrade_lock(self.root))

    def test_legacy_receipt_cleanup_advances_its_owned_checkpoint(self):
        self.fixture._seed("6")
        import sqlite_runtime
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with setup.session(self.root, ["--confirm-hosts-stopped"]) as run:
                run.prepare()
                prior = migration.read_receipt(self.index)
                self.assertEqual(prior["receipt_version"], 1)
                with run.publication():
                    # Model-free publication fixture, same native receipt
                    # convention as NativeMigrationTests in the migration suite.
                    with contextlib.closing(sqlite_runtime.connect(self.fixture.current)) as conn, conn:
                        conn.execute("UPDATE build_state SET status='complete', attempt_id='fixture', generation=1 WHERE id=1")
                run.complete()
        receipt = migration.read_receipt(self.index)
        self.assertEqual(receipt["receipt_version"], 2)
        self.assertNotEqual(receipt["migration_id"], prior["migration_id"])
        self.assertEqual(receipt["supersedes"]["migration_id"], prior["migration_id"])
        self.assertIsNone(upgrade_lib.read_upgrade_lock(self.root))

    def test_fence_write_interruption_recovers_only_through_bound_parent(self):
        self.fixture._seed("6")
        import sqlite_runtime
        original_restore = migration.restore_checkpoint

        def interrupt_after_fence(root):
            receipt = migration.read_receipt(self.index)
            if receipt and receipt.get("reason") == "index_database_fence":
                raise RuntimeError("interrupted after fence receipt")
            return original_restore(root)

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "interrupted after fence"):
                with setup.session(self.root, ["--confirm-hosts-stopped"]) as run:
                    run.prepare()
                    with run.publication():
                        with contextlib.closing(sqlite_runtime.connect(self.fixture.current)) as conn, conn:
                            conn.execute("UPDATE build_state SET status='complete', attempt_id='fixture', generation=1 WHERE id=1")
                    with patch.object(migration, "restore_checkpoint", side_effect=interrupt_after_fence):
                        run.complete()
            receipt = migration.read_receipt(self.index)
            checkpoint = upgrade_lib.read_upgrade_lock(self.root)
            self.assertNotEqual(checkpoint["storage_migration_id"], receipt["migration_id"])
            self.assertEqual(checkpoint["storage_migration_id"], receipt["supersedes"]["migration_id"])
            with setup.session(self.root, ["--confirm-hosts-stopped"]) as retry:
                retry.prepare()
                with retry.publication():
                    pass
                retry.complete()
        self.assertEqual(migration.read_receipt(self.index)["state"], "complete")
        self.assertIsNone(upgrade_lib.read_upgrade_lock(self.root))

    def test_completed_upgrade_parent_can_resume_interrupted_setup_kind(self):
        self.fixture._seed("7")
        prior = migration._new_receipt(self.fixture.ctx, self.root, self.index, migration.detect(self.index))
        prior.update(receipt_version=1, state="complete")
        prior.pop("kind", None)
        migration._write(self.index, prior)
        original_write = migration._write

        def interrupt_new_record(index, receipt):
            original_write(index, receipt)
            if receipt.get("entry_path") == "setup":
                raise RuntimeError("interrupted new setup receipt")

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "interrupted new setup receipt"):
                with setup.session(self.root, ["--confirm-hosts-stopped"]) as run:
                    with patch.object(migration, "_write", side_effect=interrupt_new_record):
                        run.prepare()
            checkpoint = upgrade_lib.read_upgrade_lock(self.root)
            receipt = migration.read_receipt(self.index)
            self.assertEqual(checkpoint["storage_migration_id"], prior["migration_id"])
            self.assertNotEqual(receipt["migration_id"], prior["migration_id"])
            with setup.session(self.root, ["--confirm-hosts-stopped"]) as retry:
                retry.prepare()
                with retry.publication():
                    pass
                retry.complete()
        self.assertEqual(migration.read_receipt(self.index)["state"], "complete")
        self.assertIsNone(upgrade_lib.read_upgrade_lock(self.root))

    def test_completed_parent_digest_mismatch_refuses_interrupted_handoff(self):
        source = self.fixture._seed("7")
        prior = migration._new_receipt(self.fixture.ctx, self.root, self.index, migration.detect(self.index))
        prior.update(receipt_version=1, state="complete")
        prior.pop("kind", None)
        migration._write(self.index, prior)
        original_write = migration._write

        def interrupt_new_record(index, receipt):
            original_write(index, receipt)
            if receipt.get("entry_path") == "setup":
                raise RuntimeError("interrupted new setup receipt")

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "interrupted new setup receipt"):
                with setup.session(self.root, ["--confirm-hosts-stopped"]) as run:
                    with patch.object(migration, "_write", side_effect=interrupt_new_record):
                        run.prepare()
        checkpoint = upgrade_lib.read_upgrade_lock(self.root)
        binding = dict(checkpoint["setup_completed_parent"], receipt_sha256="0" * 64)
        upgrade_lib.update_upgrade_lock(self.root, setup_completed_parent=binding)
        checkpoint_path = upgrade_lib.upgrade_lock_path(self.root)
        checkpoint_before = checkpoint_path.read_bytes()
        receipt_before = (self.index / migration.RECEIPT).read_bytes()
        source_before = source.read_bytes()
        with self.assertRaisesRegex(setup.MigrationRequired, "checkpoint_mismatch"):
            with setup.session(self.root, ["--confirm-hosts-stopped"]):
                self.fail("mismatched completed-parent digest accepted")
        self.assertEqual(checkpoint_before, checkpoint_path.read_bytes())
        self.assertEqual(receipt_before, (self.index / migration.RECEIPT).read_bytes())
        self.assertEqual(source_before, source.read_bytes())


if __name__ == "__main__":
    unittest.main()
