"""Receipt fencing and real native conversion; no model downloads or indexing."""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import sqlite_storage_migration as migration
import upgrade_lib


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.index = self.root / ".wavefoundry/index"
        self.index.mkdir(parents=True)
        (self.index / "docs.lance").mkdir()
        (self.index / "docs.lance/data").write_bytes(b"retained legacy source")
        self.ctx = SimpleNamespace(root=self.root, from_version="1.16.2.pipa",
                                   to_version="2.0.0.test", zip_path=None, dry_run=False)

    def prepare(self):
        with patch.dict(os.environ, {migration.CONFIRM_ENV: "1"}), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as stopped:
                migration.prepare_upgrade(self.ctx)
        self.assertEqual(stopped.exception.code, 3)
        return migration.read_receipt(self.index)

    def confirm(self):
        self.ctx.storage_migration_protocol = 1
        with patch.dict(os.environ, {migration.CONFIRM_ENV: "1"}):
            return migration.prepare_upgrade(self.ctx)

    def test_rebuild_selection_requires_original_target_and_archive(self):
        original = self.prepare()
        self.ctx.rebuild_storage = True
        self.ctx.to_version = "wrong.target"
        with self.assertRaisesRegex(migration.MigrationRequired, "storage_target_changed"):
            self.confirm()
        self.assertNotIn("strategy", migration.read_receipt(self.index))
        self.ctx.to_version = original["target_version"]
        selected = self.confirm()
        self.assertEqual(selected["strategy"], "rebuild")
        self.assertIn("--rebuild-storage", migration.restart_command(self.root, None, True)["command_argv"])

    def test_rebuild_flag_refuses_complete_or_absent_storage(self):
        shutil.rmtree(self.index / "docs.lance")
        self.ctx.rebuild_storage = True
        with self.assertRaisesRegex(migration.MigrationRequired, "storage_rebuild_not_applicable"):
            migration.prepare_upgrade(self.ctx)
        self.assertFalse((self.index / migration.RECEIPT).exists())
        (self.index / "docs.lance").mkdir()
        self.ctx.rebuild_storage = False
        receipt = self.prepare()
        receipt["state"] = "complete"
        migration._write(self.index, receipt)
        self.ctx.rebuild_storage = True
        with self.assertRaisesRegex(migration.MigrationRequired, "storage_rebuild_not_applicable"):
            migration.prepare_upgrade(self.ctx)

    def test_restart_action_is_invocation_receipt_checkpoint_and_pack_bound(self):
        self.ctx.zip_path = self.root / "pack 'quoted' $.zip"
        self.ctx.zip_path.write_bytes(b"original pack")
        with patch.dict(os.environ, {migration.INVOCATION_ENV: "current-nonce"}):
            receipt = self.prepare()
        action = migration.read_restart_action(self.root, 3, "current-nonce")
        import shlex
        self.assertEqual(shlex.split(action["command"]), action["command_argv"])
        self.assertIn(str(self.ctx.zip_path), action["command_argv"])
        self.assertIsNone(migration.read_restart_action(self.root, 1, "current-nonce"))
        self.assertIsNone(migration.read_restart_action(self.root, 3, "stale-nonce"))
        upgrade_lib.update_upgrade_lock(self.root, to_version="other")
        self.assertIsNone(migration.read_restart_action(self.root, 3, "current-nonce"))
        upgrade_lib.update_upgrade_lock(self.root, to_version=self.ctx.to_version)
        self.ctx.zip_path.write_bytes(b"different pack")
        self.assertIsNone(migration.read_restart_action(self.root, 3, "current-nonce"))
        with self.assertRaisesRegex(migration.MigrationRequired, "storage_pack_changed"):
            self.confirm()

    def test_relocated_identical_pack_recovers_deleted_temporary_locator(self):
        self.ctx.zip_path = self.root / "first-stage.zip"
        self.ctx.zip_path.write_bytes(b"identical archive")
        original = self.prepare()
        self.ctx.zip_path.unlink()
        self.ctx.zip_path = self.root / "second-stage.zip"
        self.ctx.zip_path.write_bytes(b"identical archive")
        self.ctx.selected_feature_zip = self.root / "relocated-source.zip"
        self.ctx.selected_feature_zip.write_bytes(b"identical archive")
        resumed = self.confirm()
        self.assertEqual(resumed["state"], "quiesced")
        self.assertEqual(resumed["migration_id"], original["migration_id"])
        self.assertEqual(resumed["pack_sha256"], original["pack_sha256"])
        self.assertEqual(resumed["pack_path"], str(self.ctx.selected_feature_zip))

    def test_reissued_action_binds_current_copy_separately_from_locator(self):
        self.ctx.selected_feature_zip = self.root / "source.zip"
        self.ctx.selected_feature_zip.write_bytes(b"archive")
        for number in (1, 2):
            self.ctx.zip_path = self.root / f"stage-{number}.zip"
            self.ctx.zip_path.write_bytes(b"archive")
            with patch.dict(os.environ, {migration.INVOCATION_ENV: f"nonce-{number}"}):
                receipt = self.prepare()
            action = migration.read_restart_action(self.root, 3, f"nonce-{number}")
            self.assertIsNotNone(action)
            self.assertEqual(action["pack_path"], str(self.ctx.selected_feature_zip))
            self.assertEqual(action["consumed_pack_path"], str(self.ctx.zip_path))
            self.assertIn(str(self.ctx.selected_feature_zip), action["command_argv"])
            self.assertEqual(upgrade_lib.read_upgrade_lock(self.root)["zip_path"], str(self.ctx.zip_path))
        self.assertIsNone(migration.read_restart_action(self.root, 3, "nonce-1"))
        upgrade_lib.update_upgrade_lock(self.root, zip_path=str(self.ctx.selected_feature_zip))
        self.assertIsNone(migration.read_restart_action(self.root, 3, "nonce-2"))
        upgrade_lib.update_upgrade_lock(self.root, zip_path=str(self.ctx.zip_path))
        self.ctx.zip_path.write_bytes(b"tampered consumed copy")
        self.assertIsNone(migration.read_restart_action(self.root, 3, "nonce-2"))

    def test_legacy_context_discovers_only_hash_matching_original_archive(self):
        import upgrade_wavefoundry as runner
        self.ctx = runner.UpgradeContext(self.root, self.ctx.from_version, self.ctx.to_version, None, True)
        self.ctx.zip_path = self.root / "stage.zip"
        self.ctx.zip_path.write_bytes(b"original")
        source = self.root / "discovered.zip"
        source.write_bytes(b"original")
        self.ctx.storage_migration_protocol = 0
        # Emulate the installing version's context without the new attribute.
        self.ctx.__dict__.pop("selected_feature_zip", None)
        with patch.object(runner, "_find_zip", return_value=source):
            receipt = self.prepare()
        self.assertEqual(receipt["pack_path"], str(source))
        source.write_bytes(b"different archive, same version")
        with patch.object(runner, "_find_zip", return_value=source):
            receipt = self.prepare()
        self.assertEqual(receipt["pack_path"], str(self.ctx.zip_path))
        self.assertIn("byte-identical", receipt["restart_action"]["message"])

    def test_existing_pack_receipt_requires_valid_historical_digest(self):
        self.ctx.zip_path = self.root / "pack.zip"
        self.ctx.zip_path.write_bytes(b"archive")
        receipt = self.prepare()
        for digest in (None, "", "bad", "g" * 64):
            with self.subTest(digest=digest):
                receipt["pack_sha256"] = digest
                migration._write(self.index, receipt)
                before = (self.index / migration.RECEIPT).read_bytes()
                with self.assertRaisesRegex(migration.MigrationRequired, "SHA-256 is missing or invalid"):
                    self.confirm()
                self.assertEqual((self.index / migration.RECEIPT).read_bytes(), before)

    def test_relocated_pack_with_same_version_changed_bytes_is_refused(self):
        self.ctx.zip_path = self.root / "original.zip"
        self.ctx.zip_path.write_bytes(b"original")
        self.prepare()
        before = (self.index / migration.RECEIPT).read_bytes()
        self.ctx.zip_path = self.root / "new-stage.zip"
        self.ctx.zip_path.write_bytes(b"different archive, same VERSION")
        with self.assertRaisesRegex(migration.MigrationRequired, "storage_pack_changed"):
            self.confirm()
        self.assertEqual((self.index / migration.RECEIPT).read_bytes(), before)

    def test_pack_relocation_retains_target_root_and_live_host_fences(self):
        self.ctx.zip_path = self.root / "original.zip"
        self.ctx.zip_path.write_bytes(b"archive")
        self.ctx.storage_old_hosts = [{"kind": "mcp", "pid": os.getpid()}]
        original = self.prepare()
        self.ctx.zip_path = self.root / "relocated.zip"
        self.ctx.zip_path.write_bytes(b"archive")
        with self.assertRaisesRegex(migration.MigrationRequired, "storage_old_host_alive"):
            self.confirm()
        self.ctx.to_version = "different.VERSION"
        with self.assertRaisesRegex(migration.MigrationRequired, "storage_target_changed"):
            self.confirm()
        original["root_identity"] = {"device": -1, "inode": -1}
        migration._write(self.index, original)
        with self.assertRaisesRegex(migration.MigrationRequired, "storage_receipt_identity_mismatch"):
            self.confirm()

    def test_finalizer_bridge_is_one_shot_and_rejects_unrelated_exit(self):
        import upgrade_wavefoundry as runner
        for exit_code in (3, 2):
            with self.subTest(exit_code=exit_code):
                ctx = runner.UpgradeContext(self.root, self.ctx.from_version, self.ctx.to_version, None, True)
                ctx.storage_migration_protocol = 0
                original = MagicMock()
                with patch.object(runner, "_finalize_failed_upgrade", original), contextlib.redirect_stdout(io.StringIO()):
                    try:
                        migration.prepare_upgrade(ctx)
                    except SystemExit:
                        if exit_code == 3:
                            runner._finalize_failed_upgrade(self.root, True, "extract")
                        else:
                            try:
                                raise SystemExit(exit_code)
                            except SystemExit:
                                runner._finalize_failed_upgrade(self.root, True, "extract")
                self.assertEqual(original.call_count, int(exit_code != 3))

    def test_host_discovery_positive_association_and_limits(self):
        script = self.root / ".wavefoundry/framework/scripts/server.py"
        dashboard = self.root / ".wavefoundry/framework/scripts/dashboard_server.py"
        result = SimpleNamespace(stdout=f"901 python {script} --root {self.root}\n902 python {dashboard} --root {self.root}\n903 python {script} --root /unrelated\n904 python /other/server.py --root {self.root}\n905 zsh --root {self.root}\n")
        with patch.object(migration.subprocess, "run", return_value=result):
            hosts, limits = migration.discover_hosts(self.root)
        self.assertEqual({h["pid"] for h in hosts}, {901, 902})
        self.assertTrue(all(h["association"] for h in hosts))
        self.assertTrue(limits)
        with patch.object(migration.subprocess, "run", side_effect=OSError):
            self.assertIn("failed", migration.discover_hosts(self.root)[1][-1])

    def test_resume_refreshes_new_hosts_and_preserves_prior_pid_guards(self):
        with patch.object(migration, "discover_hosts", return_value=([{"pid": 901, "kind": "mcp"}], [])):
            self.prepare()
        with patch.object(migration, "discover_hosts", return_value=([{"pid": 902, "kind": "dashboard"}], [])), patch.object(migration, "_host_is_running", side_effect=lambda pid: pid == 902):
            with self.assertRaisesRegex(migration.MigrationRequired, "storage_old_host_alive: 902"):
                self.confirm()
        self.assertEqual({h["pid"] for h in migration.read_receipt(self.index)["old_hosts"]}, {901, 902})

    def test_completed_receipt_allows_later_target_upgrade(self):
        receipt = self.prepare()
        receipt["state"] = "complete"
        migration._write(self.index, receipt)
        self.ctx.to_version = "9.0.0"
        self.ctx.zip_path = self.root / "future-pack.zip"
        self.assertEqual(migration.prepare_upgrade(self.ctx)["state"], "complete")

    def test_host_discovery_handles_ps_spaces_quotes_and_rejects_echo(self):
        for name in ("repo with spaces", "repo's spaces"):
            root = self.root / name
            script = root / ".wavefoundry/framework/scripts/server.py"
            result = SimpleNamespace(stdout=f'901 python {script} --root {root}\n902 echo {script} --root {root}\n903 python -c "{script}" --root "{root}"\n904 python "{script}" --root "{root}"\n')
            with patch.object(migration.subprocess, "run", return_value=result):
                hosts, _ = migration.discover_hosts(root)
            self.assertEqual([h["pid"] for h in hosts], [901, 904])

    def test_relative_framework_entrypoint_requires_observed_cwd(self):
        result = SimpleNamespace(stdout="901 python .wavefoundry/framework/scripts/server.py\n902 python .wavefoundry/framework/scripts/dashboard_server.py\n903 zsh\n904 python .wavefoundry/framework/scripts/server.py\n")
        with patch.object(migration.subprocess, "run", return_value=result), patch.object(migration, "_process_cwds", return_value={901: self.root, 902: Path("/unrelated"), 903: self.root}):
            hosts, limits = migration.discover_hosts(self.root)
        self.assertEqual([h["pid"] for h in hosts], [901])
        self.assertIn("cwd", hosts[0]["association"])
        self.assertTrue(any("PID 904" in limit for limit in limits))

    def test_powershell_handoff_uses_console_python_and_literal_quotes(self):
        with patch.object(migration, "os", SimpleNamespace(name="nt")), patch.object(migration.sys, "executable", "/python env/pythonw.exe"):
            command = migration.restart_command(self.root, "C:/packs/it's $literal.zip")
        self.assertEqual(command["command_shell"], "PowerShell")
        self.assertTrue(command["command_argv"][0].endswith("python.exe"))
        self.assertIn("'C:/packs/it''s $literal.zip'", command["command"])
        self.assertTrue(command["command"].startswith("& "))

    def test_old_runner_stops_even_with_confirmation_before_downstream(self):
        downstream = []
        with patch.dict(os.environ, {migration.CONFIRM_ENV: "1"}), contextlib.redirect_stdout(io.StringIO()):
            try:
                migration.prepare_upgrade(self.ctx)
                downstream.extend(["index", "cleanup"])
            except SystemExit as exc:
                self.assertEqual(exc.code, 3)
        self.assertEqual(downstream, [])
        self.assertTrue((self.index / "docs.lance/data").exists())
        self.assertEqual(migration.read_receipt(self.index)["state"], "restart_required")

    def test_existing_framework_without_index_requires_restart_but_fresh_installer_does_not(self):
        shutil.rmtree(self.index / "docs.lance")
        self.index.rmdir()
        self.ctx.from_version = None
        self.assertIsNone(migration.prepare_upgrade(self.ctx))
        self.assertFalse(self.index.exists())
        self.ctx.from_version = "1.22.0.pomi"
        receipt = self.prepare()
        self.assertEqual(receipt["reason"], "existing_framework_without_index")
        self.assertEqual(receipt["artifacts"], {})
        self.assertIsNone(receipt["source_sqlite_identity"])
        self.assertFalse((self.index / "index-state.sqlite").exists())
        self.assertEqual(self.confirm()["state"], "quiesced")

    def test_incoming_post_extract_hook_is_fatal_through_real_dispatcher(self):
        import upgrade_extensions
        import upgrade_wavefoundry
        installed = self.root / ".wavefoundry/framework/scripts"
        installed.mkdir(parents=True)
        shutil.copy2(SCRIPTS / "sqlite_storage_migration.py", installed)
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as stopped:
                upgrade_wavefoundry._run_hook("post_extract", self.ctx, upgrade_extensions)
        self.assertEqual(stopped.exception.code, 3)
        self.assertEqual(migration.read_receipt(self.index)["state"], "restart_required")

    def test_incoming_manifest_survives_restart_and_drives_real_pruning(self):
        import upgrade_extensions as extensions
        import upgrade_wavefoundry as upgrade
        framework = self.root / ".wavefoundry/framework"
        (framework / "seeds").mkdir(parents=True)
        (framework / "VERSION").write_text(self.ctx.from_version)
        old_manifest = "seeds/175-interrogate-plan.prompt.md\n"
        (framework / "MANIFEST").write_text(old_manifest)
        old_seed = framework / "seeds/175-interrogate-plan.prompt.md"
        old_seed.write_text("old framework seed")
        user_file = framework / "seeds/project-local.md"
        user_file.write_text("unlisted project file")
        upgrade_lib.write_upgrade_lock(self.root, self.ctx.from_version, self.ctx.to_version)
        extensions.pre_extract(self.ctx)
        snapshot = self.root / ".wavefoundry/upgrade-manifest-old.json"
        self.assertEqual(json.loads(snapshot.read_text())["manifest"], old_manifest)
        # The real incoming restart fence runs after extraction. An old
        # finalizer may erase its separate global temp copy; this authority
        # remains outside both the extracted framework and that temp path.
        (framework / "VERSION").write_text(self.ctx.to_version)
        (framework / "MANIFEST").write_text("seeds/175-review-plan.prompt.md\n")
        new_seed = framework / "seeds/175-review-plan.prompt.md"
        new_seed.write_text("new framework seed")
        self.prepare()
        self.assertTrue(snapshot.exists())
        self.assertEqual(upgrade.phase_pruning(self.root), 1)
        self.assertFalse(old_seed.exists())
        self.assertTrue(new_seed.exists())
        self.assertEqual(user_file.read_text(), "unlisted project file")

    def test_original_manifest_snapshot_refuses_divergence_and_retains_retry(self):
        import upgrade_extensions as extensions
        framework = self.root / ".wavefoundry/framework"
        framework.mkdir()
        (framework / "VERSION").write_text(self.ctx.from_version)
        manifest = framework / "MANIFEST"
        manifest.write_text("original\n")
        extensions._preserve_original_manifest(self.ctx)
        snapshot = self.root / ".wavefoundry/upgrade-manifest-old.json"
        before = snapshot.read_bytes()
        manifest.write_text("divergent before extraction\n")
        with self.assertRaisesRegex(ValueError, "differs"):
            extensions._preserve_original_manifest(self.ctx)
        self.assertEqual(snapshot.read_bytes(), before)
        (framework / "VERSION").write_text(self.ctx.to_version)
        extensions._preserve_original_manifest(self.ctx)
        self.assertEqual(snapshot.read_bytes(), before)
        self.ctx.to_version = "3.0.0.test"
        with self.assertRaisesRegex(ValueError, "divergent"):
            extensions._preserve_original_manifest(self.ctx)
        self.assertEqual(snapshot.read_bytes(), before)

    def test_receipt_restores_lost_retry_checkpoint_before_stale_cleanup(self):
        receipt = self.prepare()
        upgrade_lib.remove_upgrade_lock(self.root)
        import upgrade_wavefoundry
        upgrade_wavefoundry._clear_stale_upgrade_lock_for_preflight(self.root, upgrade_lib)
        checkpoint = upgrade_lib.read_upgrade_lock(self.root)
        self.assertEqual(checkpoint["storage_migration_id"], receipt["migration_id"])
        with self.assertRaises(migration.MigrationRequired):
            migration.require_ready(self.index)

    def test_preflight_admits_its_restored_receipt_but_not_an_unrelated_lock(self):
        self.prepare()
        import upgrade_wavefoundry as upgrade
        class PastCheckpoint(Exception):
            pass
        with patch.object(upgrade, "_detect_dashboard", side_effect=PastCheckpoint):
            with self.assertRaises(PastCheckpoint):
                upgrade.phase_preflight(self.root, True)
        upgrade_lib.update_upgrade_lock(self.root, storage_migration_id="unrelated")
        with patch.object(upgrade, "_detect_dashboard", side_effect=AssertionError("must not advance")), \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                upgrade.phase_preflight(self.root, True)

    def test_current_runner_still_requires_explicit_confirmation(self):
        self.prepare()
        self.ctx.storage_migration_protocol = 1
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                migration.prepare_upgrade(self.ctx)
        self.assertEqual(self.confirm()["state"], "quiesced")

    def test_old_runner_still_cannot_continue_after_published_receipt(self):
        receipt = self.prepare()
        receipt["state"] = "published"
        migration._write(self.index, receipt)
        with patch.dict(os.environ, {migration.CONFIRM_ENV: "1"}), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(migration.MigrationRequired, "storage_current_runner_required"):
                migration.prepare_upgrade(self.ctx)

    def test_identified_live_host_blocks_but_shell_parent_is_not_inferred(self):
        self.ctx.storage_old_hosts = [{"kind": "mcp", "pid": os.getpid()}]
        self.prepare()
        with self.assertRaisesRegex(migration.MigrationRequired, "old_host_alive"):
            self.confirm()
        self.assertEqual(migration.read_receipt(self.index)["state"], "restart_required")

    def test_wrapper_pid_is_captured_only_at_first_receipt(self):
        with patch.dict(os.environ, {migration.OLD_MCP_PID_ENV: str(os.getpid())}):
            receipt = self.prepare()
        self.assertEqual(receipt["old_hosts"][0]["pid"], os.getpid())
        with patch.dict(os.environ, {migration.OLD_MCP_PID_ENV: "123456789"}):
            with self.assertRaisesRegex(migration.MigrationRequired, "old_host_alive"):
                self.confirm()
        self.assertEqual(migration.read_receipt(self.index)["old_hosts"], receipt["old_hosts"])

    def test_windows_liveness_uses_nonterminating_process_handle(self):
        import ctypes
        from ctypes import wintypes  # import before mocking the platform
        kernel = MagicMock()
        kernel.OpenProcess.return_value = 17
        with patch.object(migration.os, "name", "nt"), \
             patch.object(ctypes, "WinDLL", return_value=kernel, create=True), \
             patch.object(migration.os, "kill", side_effect=AssertionError("must never signal Windows process")):
            kernel.WaitForSingleObject.return_value = 258
            self.assertTrue(migration._host_is_running(123))
            kernel.WaitForSingleObject.return_value = 0
            self.assertFalse(migration._host_is_running(123))
            kernel.OpenProcess.assert_called_with(0x00100000, False, 123)
            self.assertEqual(kernel.CloseHandle.call_count, 2)
            kernel.OpenProcess.return_value = 0
            with patch.object(ctypes, "get_last_error", return_value=5, create=True):
                with self.assertRaises(migration.MigrationRequired):
                    migration._host_is_running(123)

    def test_cleanup_before_proof_preserves_sources(self):
        self.prepare()
        with self.assertRaisesRegex(migration.MigrationRequired, "cleanup_unverified"):
            migration.cleanup_legacy(self.root)
        self.assertTrue((self.index / "docs.lance/data").exists())

    def test_symlink_source_and_tampered_receipt_refused(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.index / "code.lance").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(migration.MigrationRequired, "path_unowned"):
            self.prepare()
        (self.index / "code.lance").unlink()
        receipt = self.prepare()
        receipt["migration_id"] = "../../outside"
        migration._write(self.index, receipt)
        with self.assertRaisesRegex(migration.MigrationRequired, "identity_mismatch"):
            migration.read_receipt(self.index)

    def test_windows311_reparse_metadata_refuses_all_owned_path_components(self):
        real_lstat = Path.lstat
        for candidate in (self.root / ".wavefoundry", self.index,
                          self.index / "docs.lance", self.index / "docs.lance/data"):
            with self.subTest(candidate=candidate):
                def metadata(path, *args, **kwargs):
                    result = real_lstat(path, *args, **kwargs)
                    if path == candidate:
                        return SimpleNamespace(st_mode=result.st_mode,
                            st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
                    return result
                with patch.object(Path, "lstat", metadata), \
                     patch.object(Path, "is_junction", side_effect=AssertionError("3.12 API unavailable"), create=True):
                    with self.assertRaisesRegex(migration.MigrationRequired, "path_unowned"):
                        migration._safe(self.index / "docs.lance/data")
                self.assertEqual((self.index / "docs.lance/data").read_bytes(), b"retained legacy source")
        # The same real file is accepted when no reparse metadata is present.
        self.assertEqual(migration._safe(self.index / "docs.lance/data"), self.index / "docs.lance/data")

    def test_cleanup_bounds_reparse_checks_to_owned_repository_descendants(self):
        import upgrade_wavefoundry as upgrade
        real_lstat = Path.lstat
        def metadata(path, *args, **kwargs):
            result = real_lstat(path, *args, **kwargs)
            if path == self.root.parent:
                return SimpleNamespace(st_mode=result.st_mode,
                    st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
            return result
        with patch.object(Path, "lstat", metadata), patch.object(os, "supports_dir_fd", set()):
            self.assertEqual(upgrade._remove_retired_component(
                self.index, "docs.lance", False, ownership_root=self.root), "removed")
        self.assertFalse((self.index / "docs.lance").exists())

    def test_bounded_cleanup_rejects_owned_reparse_and_outside_boundary(self):
        import upgrade_wavefoundry as upgrade
        real_lstat = Path.lstat
        for candidate in (self.root / ".wavefoundry", self.index):
            with self.subTest(candidate=candidate):
                def metadata(path, *args, **kwargs):
                    result = real_lstat(path, *args, **kwargs)
                    if path == candidate:
                        return SimpleNamespace(st_mode=result.st_mode,
                            st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
                    return result
                with patch.object(Path, "lstat", metadata), patch.object(os, "supports_dir_fd", set()):
                    self.assertEqual(upgrade._remove_retired_component(
                        self.index, "docs.lance", False, ownership_root=self.root), "unowned")
                self.assertEqual((self.index / "docs.lance/data").read_bytes(), b"retained legacy source")
        self.assertEqual(upgrade._remove_retired_component(
            self.index, "docs.lance", False, ownership_root=self.root / "other"), "unowned")
        self.assertTrue((self.index / "docs.lance/data").exists())

    @unittest.skipUnless(os.name == "nt", "native Windows junction execution required; simulated Python 3.11 metadata runs on every host")
    def test_native_windows_junction_migration_components_are_refused(self):
        outside = self.root / "outside-junction-target"
        outside.mkdir()
        sentinel = outside / "keep"
        sentinel.write_bytes(b"outside retained")
        for relative in (".wavefoundry", ".wavefoundry/index", ".wavefoundry/index/docs.lance"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                junction = root / relative
                junction.parent.mkdir(parents=True, exist_ok=True)
                made = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
                                      capture_output=True, text=True)
                self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
                try:
                    with self.assertRaisesRegex(migration.MigrationRequired, "path_unowned"):
                        migration._safe(junction / "keep")
                    self.assertEqual(sentinel.read_bytes(), b"outside retained")
                finally:
                    os.rmdir(junction)


def _native_available():
    try:
        import sqlite_runtime
        with tempfile.TemporaryDirectory() as directory:
            sqlite_runtime.connect(Path(directory) / "probe.sqlite").close()
        return True
    except (ImportError, RuntimeError):
        return False


@unittest.skipUnless(_native_available(), "qualified APSW + sqlite-vec runtime unavailable")
class NativeMigrationTests(unittest.TestCase):
    prepare = ReceiptTests.prepare
    confirm = ReceiptTests.confirm

    def setUp(self):
        ReceiptTests.setUp(self)
        self.live = self.index / "index-state.sqlite"
        import sqlite_runtime
        with contextlib.closing(sqlite_runtime.connect(self.live)) as conn, conn:
            conn.execute("CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            conn.execute("INSERT INTO meta VALUES('store_schema_version','6')")
            conn.execute("CREATE TABLE preserved_memory(id TEXT PRIMARY KEY,body TEXT)")
            conn.execute("INSERT INTO preserved_memory VALUES('memory-1','retain me')")
        self.rows = [{"id": "docs-a", "path": "docs/a.md", "kind": "docs", "text": "alpha_beta searchable text",
                      "tags": ["one", "two"], "start_line": 1, "end_line": 2,
                      "vector": [1.0] + [0.0] * 383}]
        self.prepare()
        self.confirm()

    def convert(self):
        with patch.object(migration, "_legacy_counts", return_value={"docs": len(self.rows), "code": 0}), \
             patch.object(migration, "_legacy_batches", return_value=iter([self.rows])):
            return migration.migrate_legacy(self.root)

    def test_explicit_rebuild_preserves_auxiliary_and_skips_legacy_reader(self):
        self.ctx.rebuild_storage = True
        selected = self.confirm()
        self.assertEqual(selected["strategy"], "rebuild")
        self.ctx.rebuild_storage = False
        self.assertEqual(self.confirm()["rebuild_id"], selected["rebuild_id"])
        with patch.object(migration, "_legacy_counts", side_effect=AssertionError("must not read old vectors")), \
             patch.object(migration, "_legacy_batches", side_effect=AssertionError("must not import old chunks")):
            receipt = migration.migrate_legacy(self.root)
        self.assertEqual(receipt["state"], "published")
        self.assertEqual(receipt["candidate_counts"], {"docs": 0, "code": 0})
        self.assertIsNone(receipt["capacity_qualification"]["qualified"])
        self.assertNotIn("source_counts", receipt)
        import sqlite_runtime
        with contextlib.closing(sqlite_runtime.connect(self.live)) as conn:
            self.assertEqual(conn.execute("SELECT body FROM preserved_memory").fetchone()[0], "retain me")
            self.assertEqual(conn.execute("SELECT status FROM build_state").fetchone()[0], "building")
            for layer in ("docs", "code"):
                self.assertEqual(conn.execute(f"SELECT count(*) FROM chunks_{layer}").fetchone()[0], 0)
            conn.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (migration.REBUILD_PROOF_KEY, '{}'))
        migration.begin_upgrade_publication(self.root)
        with contextlib.closing(sqlite_runtime.connect(self.live)) as conn:
            self.assertIsNone(conn.execute("SELECT value FROM meta WHERE key=?", (migration.REBUILD_PROOF_KEY,)).fetchone())
        with self.assertRaisesRegex(migration.MigrationRequired, "storage_rebuild_proof_missing"):
            migration.record_upgrade_publication(self.root)
        self.assertTrue((self.index / "docs.lance/data").exists())

    def test_rebuild_choice_after_candidate_staging_is_refused(self):
        receipt = migration.read_receipt(self.index)
        receipt["state"] = "validated"
        migration._write(self.index, receipt)
        self.ctx.rebuild_storage = True
        with self.assertRaisesRegex(migration.MigrationRequired, "storage_strategy_changed_after_staging"):
            self.confirm()
        self.assertNotIn("strategy", migration.read_receipt(self.index))

    def test_candidate_clear_removes_derived_rows_but_keeps_auxiliary(self):
        self.convert()
        import sqlite_runtime
        with contextlib.closing(sqlite_runtime.connect(self.live)) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM chunks_docs").fetchone()[0], 1)
            conn.execute("INSERT OR REPLACE INTO meta VALUES('project-owned-note','keep')")
            migration._clear_rebuild_candidate(conn)
            for layer in ("docs", "code"):
                for table in (f"chunks_{layer}", f"vectors_{layer}"):
                    self.assertEqual(conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0], 0)
            for table in ("chunk_registry", "layer_path_state", "build_file_meta", "build_layer_meta"):
                self.assertEqual(conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT value FROM meta WHERE key='project-owned-note'").fetchone()[0], "keep")
            self.assertEqual(conn.execute("SELECT body FROM preserved_memory").fetchone()[0], "retain me")

    def test_capacity_refusal_precedes_staging_and_retains_source_receipt(self):
        import sqlite_vector_store as vectors
        limits = vectors.capacity_qualification({"docs": 0, "code": 0})["qualified_max_rows"]
        counts = {"docs": limits["docs"] + 1, "code": 0}
        before = self.live.read_bytes()
        with patch.object(migration, "_legacy_counts", return_value=counts), \
             patch.object(migration, "_legacy_batches", side_effect=AssertionError("capacity refusal precedes scan")):
            with self.assertRaisesRegex(migration.MigrationRequired, "storage_capacity_unqualified"):
                migration.migrate_legacy(self.root)
        receipt = migration.read_receipt(self.index)
        self.assertEqual(receipt["last_failure"]["code"], "storage_capacity_unqualified")
        self.assertFalse(receipt["capacity_qualification"]["qualified"])
        self.assertNotIn("work_dir", receipt)
        self.assertEqual(self.live.read_bytes(), before)
        self.assertTrue((self.index / "docs.lance/data").exists())

    def test_native_transfer_preserves_payload_vector_auxiliary_and_requires_fresh_process(self):
        receipt = self.convert()
        self.assertEqual(receipt["state"], "published")
        import sqlite_runtime
        import sqlite_vector_store
        conn = sqlite_runtime.connect(self.live)
        self.assertEqual(conn.execute("SELECT body FROM preserved_memory").fetchone(), ("retain me",))
        self.assertEqual(sqlite_vector_store.payload_rows(self.index, "docs", include_vector=True), self.rows)
        migration.record_upgrade_publication(self.root)
        with self.assertRaisesRegex(migration.MigrationRequired, "new_process"):
            migration.verify_migration(self.root)
        # This fixture represents successful ordinary publication. It does not
        # claim to run the model/source reconciliation pipeline.
        with conn:
            conn.execute("UPDATE build_state SET status='complete',attempt_id='fixture',generation=1 WHERE id=1")
        conn.close()
        self.assertEqual(migration._identity(self.live), receipt["published_sqlite_identity"])
        child = subprocess.run([sys.executable, "-B", str(SCRIPTS / "sqlite_storage_migration.py"), "--verify", str(self.root)],
                               capture_output=True, text=True)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertEqual(migration.read_receipt(self.index)["state"], "verified")
        # The standard coordinator may clean up after the fresh child proves
        # reopen; it must not be required to restart for a third process.
        self.assertEqual(migration.cleanup_legacy(self.root)["state"], "complete")
        self.assertFalse((self.index / "docs.lance").exists())
        self.assertTrue(self.live.exists())
        self.assertEqual(migration.cleanup_legacy(self.root)["state"], "complete")

    def test_verification_refuses_replaced_main_or_sidecars_before_native_open(self):
        import sqlite_runtime
        self.convert()
        migration.record_upgrade_publication(self.root)
        before_receipt = (self.index / migration.RECEIPT).read_bytes()
        outside = self.root / "outside.sqlite"
        shutil.copy2(self.live, outside)
        outside_before = outside.read_bytes()
        for suffix in ("", "-wal", "-shm"):
            with self.subTest(suffix=suffix):
                candidate = Path(str(self.live) + suffix)
                retained = candidate.with_name(candidate.name + ".retained")
                if candidate.exists():
                    candidate.rename(retained)
                candidate.symlink_to(outside)
                try:
                    with patch.object(migration.os, "getpid", return_value=os.getpid() + 10000), \
                         patch.object(sqlite_runtime, "connect", side_effect=AssertionError("must refuse before native open")):
                        with self.assertRaisesRegex(migration.MigrationRequired, "path_unowned"):
                            migration.verify_migration(self.root)
                finally:
                    candidate.unlink()
                    if retained.exists():
                        retained.rename(candidate)
                self.assertEqual(outside.read_bytes(), outside_before)
                self.assertEqual((self.index / migration.RECEIPT).read_bytes(), before_receipt)
        receipt = migration.read_receipt(self.index)
        receipt.update(state="verified", verification={"pid": os.getpid() + 10000})
        migration._write(self.index, receipt)
        retained = self.live.with_name("original-published.sqlite")
        self.live.rename(retained)
        shutil.copy2(outside, self.live)
        with patch.object(migration.os, "getpid", return_value=os.getpid() + 10000), \
             patch.object(sqlite_runtime, "connect", side_effect=AssertionError("must refuse before native open")):
            with self.assertRaisesRegex(migration.MigrationRequired, "publication_identity_changed"):
                migration.verify_migration(self.root)
            with self.assertRaisesRegex(migration.MigrationRequired, "publication_identity_changed"):
                migration.cleanup_legacy(self.root)
            with self.assertRaisesRegex(migration.MigrationRequired, "publication_identity_changed"):
                migration.require_ready(self.index)
            with self.assertRaisesRegex(migration.MigrationRequired, "publication_identity_changed"):
                migration.begin_upgrade_publication(self.root)
        self.assertTrue((self.index / "docs.lance/data").exists())
        self.assertTrue(retained.exists())
        receipt = migration.read_receipt(self.index)
        receipt.pop("published_sqlite_identity")
        migration._write(self.index, receipt)
        with patch.object(migration.os, "getpid", return_value=os.getpid() + 10000), \
             patch.object(sqlite_runtime, "connect", side_effect=AssertionError("must refuse before native open")):
            with self.assertRaisesRegex(migration.MigrationRequired, "publication_identity_missing"):
                migration.verify_migration(self.root)

    def test_interrupted_after_replace_retains_candidate_identity_for_retry(self):
        real_sync = migration._sync_directory
        def interrupt(path):
            real_sync(path)
            if path == self.index:
                raise OSError("interrupted after replacement")
        with patch.object(migration, "_sync_directory", side_effect=interrupt):
            with self.assertRaisesRegex(OSError, "interrupted after replacement"):
                self.convert()
        receipt = migration.read_receipt(self.index)
        self.assertEqual(receipt["state"], "cutover_pending")
        self.assertEqual(receipt["published_sqlite_identity"], migration._identity(self.live))
        with patch.object(migration, "_legacy_batches", side_effect=AssertionError("already replaced")):
            self.assertEqual(migration.migrate_legacy(self.root)["state"], "published")

    def test_invalid_vector_retains_live_schema_and_sources(self):
        self.rows[0]["vector"] = [0.0] * 12
        with self.assertRaisesRegex(migration.MigrationRequired, "vector_invalid"):
            self.convert()
        import sqlite_runtime
        with contextlib.closing(sqlite_runtime.connect(self.live, read_only=True)) as conn:
            self.assertEqual(conn.execute("SELECT value FROM meta").fetchone(), ("6",))
        self.assertTrue((self.index / "docs.lance/data").exists())
        with self.assertRaises(migration.MigrationRequired) as refused:
            migration._row_digest(self.rows[0])
        self.assertIn("Current wf setup --full cannot bypass", str(refused.exception))
        self.assertIn("compatible older framework/runtime", str(refused.exception))

    def test_unreadable_legacy_source_retains_receipt_and_names_honest_recovery(self):
        try:
            import lancedb
        except ImportError:
            self.skipTest("migration-only Lance reader unavailable")
        if lancedb.__version__ != "0.33.0":
            self.skipTest("requires pinned migration-only Lance reader")
        # The placeholder has no readable Lance manifest. The real reader must
        # fail closed before staging, never claim current setup bypasses it.
        before = self.live.read_bytes()
        with self.assertRaises(migration.MigrationRequired) as refused:
            migration.migrate_legacy(self.root)
        self.assertIn("storage_legacy_source_unreadable", str(refused.exception))
        self.assertIn("Current wf setup --full cannot bypass", str(refused.exception))
        self.assertEqual(self.live.read_bytes(), before)
        self.assertTrue((self.index / "docs.lance/data").exists())
        self.assertEqual(migration.read_receipt(self.index)["state"], "quiesced")
        self.assertIsNotNone(upgrade_lib.read_upgrade_lock(self.root))

    def test_legacy_fts_digest_is_not_xored_into_imported_payload(self):
        import index_state_store as state
        import sqlite_runtime
        conn = sqlite_runtime.connect(self.live)
        with conn:
            conn.execute("INSERT INTO meta VALUES(?,?)",
                         (state.META_FTS_PAYLOAD_DIGEST_PREFIX + "docs",
                          state._fts_digest_hex(state._fts_digest_of_rows(self.rows))))
        conn.close()
        self.convert()
        verdict = state.fts_state_verdict(self.index, "docs")
        self.assertTrue(verdict["ok"], verdict)

    def _native_phase_children(self, observed):
        """Exercise native epoch producers; replace only model-heavy child work."""
        import index_state_store as state

        def run(argv, **kwargs):
            if Path(argv[1]).name == "setup_index.py":
                scope = "graph" if "--graph-only" in argv else "all"
                with patch.dict(os.environ, kwargs.get("env", {})):
                    attempt = state.begin_build_epoch(self.index, scope)
                    self.assertTrue(state.finalize_build_epoch(self.index, attempt))
                observed.append((scope, state.read_build_state(self.index)["status"]))
                return subprocess.CompletedProcess(argv, 0)
            self.assertEqual(Path(argv[1]).name, "sqlite_storage_migration.py")
            observed.append(("verify", state.read_build_state(self.index)["status"]))
            return subprocess.run(argv, capture_output=True, text=True, check=False)
        return run

    def _native_memory_scope(self):
        import memory_backfill
        run_id = memory_backfill.ensure_run(self.root, "upgrade")
        self.assertEqual(memory_backfill.sync_inventory(self.root, run_id)["state"], "ready_for_index")
        return run_id, memory_backfill.index_publication_scope(run_id)

    def test_parent_owned_native_epoch_is_published_before_fresh_storage_verifier(self):
        import upgrade_wavefoundry as upgrade
        import memory_backfill
        self.convert()
        run_id, scope = self._native_memory_scope()
        observed = []
        with scope, patch.object(upgrade.subprocess_util, "isolated_run", side_effect=self._native_phase_children(observed)), \
             contextlib.redirect_stdout(io.StringIO()):
            upgrade.phase_index_update_parent_owned(self.root, run_id)
        self.assertEqual(observed, [("all", "building"), ("graph", "building"), ("verify", "complete")])
        self.assertEqual(memory_backfill.run_summary(self.root, run_id)["state"], "indexed")
        self.assertEqual(migration.read_receipt(self.index)["state"], "verified")
        self.assertEqual(migration.cleanup_legacy(self.root)["state"], "complete")

    def test_normal_native_phase_still_verifies_its_completed_epoch(self):
        import upgrade_wavefoundry as upgrade
        self.convert()
        observed = []
        with patch.object(upgrade.subprocess_util, "isolated_run", side_effect=self._native_phase_children(observed)), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(upgrade.phase_index_update(self.root))
        self.assertEqual(observed, [("all", "complete"), ("graph", "complete"), ("verify", "complete")])
        self.assertEqual(migration.read_receipt(self.index)["state"], "verified")

    def test_recovered_native_staging_receipt_requires_child_outcomes_and_fresh_verification(self):
        import upgrade_wavefoundry as upgrade
        import index_state_store as state
        self.convert()
        run_id, scope = self._native_memory_scope()
        observed = []
        receipt_path = self.index / "upgrade-index-staging-receipt.json"
        with scope, patch.object(upgrade.subprocess_util, "isolated_run", side_effect=self._native_phase_children(observed)), \
             contextlib.redirect_stdout(io.StringIO()):
            with patch.dict(os.environ, {"WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT": str(receipt_path)}):
                self.assertTrue(upgrade.phase_index_update(self.root))
            self.assertEqual(state.read_build_state(self.index)["status"], "building")
            with self.assertRaisesRegex(migration.MigrationRequired, "cleanup_unverified"):
                migration.cleanup_legacy(self.root)
            upgrade.phase_index_update_parent_owned(self.root, run_id)
        self.assertEqual(observed, [("all", "building"), ("graph", "building"), ("verify", "complete")])
        self.assertFalse(receipt_path.exists())
        self.assertEqual(migration.read_receipt(self.index)["state"], "verified")

    def test_unobserved_child_exit_cannot_be_inferred_from_native_staging_receipt(self):
        import upgrade_wavefoundry as upgrade
        self.convert()
        run_id, scope = self._native_memory_scope()
        observed = []
        receipt_path = self.index / "upgrade-index-staging-receipt.json"
        with scope, patch.object(upgrade.subprocess_util, "isolated_run", side_effect=self._native_phase_children(observed)), \
             contextlib.redirect_stdout(io.StringIO()):
            with patch.dict(os.environ, {"WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT": str(receipt_path)}):
                self.assertTrue(upgrade.phase_index_update(self.root))
            # Simulate interruption before the coordinator could persist both
            # observed exits. The existing staged attempt is not that proof.
            migration.begin_upgrade_publication(self.root)
            upgrade.phase_index_update_parent_owned(self.root, run_id)
        self.assertEqual(observed, [("all", "building"), ("graph", "building"),
                                    ("all", "building"), ("graph", "building"), ("verify", "complete")])
        self.assertEqual(migration.read_receipt(self.index)["state"], "verified")

    def test_standard_memory_reconciliation_restages_before_parent_cas(self):
        import upgrade_wavefoundry as upgrade
        import memory_backfill
        import index_state_store as state
        self.convert()
        run_id, scope = self._native_memory_scope()
        observed = []
        receipt_path = self.index / "upgrade-index-staging-receipt.json"
        with scope, patch.object(upgrade.subprocess_util, "isolated_run", side_effect=self._native_phase_children(observed)), \
             contextlib.redirect_stdout(io.StringIO()):
            with patch.dict(os.environ, {"WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT": str(receipt_path)}):
                self.assertTrue(upgrade.phase_index_update(self.root))
            # The standard resume preflight reconciles an unpublished attempt:
            # its memory authorization is retired even though the child file
            # remains. Re-authorize by rerunning the ordinary child pipeline.
            reconciled = memory_backfill.reconcile_index_publication(self.root, run_id)
            self.assertEqual(reconciled["state"], "ready_for_index")
            self.assertEqual(state.read_build_state(self.index)["status"], "building")
            upgrade.phase_index_update_parent_owned(self.root, run_id)
        self.assertEqual(observed, [("all", "building"), ("graph", "building"),
                                    ("all", "building"), ("graph", "building"), ("verify", "complete")])
        self.assertEqual(memory_backfill.run_summary(self.root, run_id)["state"], "indexed")
        self.assertEqual(migration.cleanup_legacy(self.root)["state"], "complete")

    def test_graph_failure_cannot_verify_or_clean_up_migration(self):
        import upgrade_wavefoundry as upgrade
        self.convert()
        # A retry must invalidate a previous observed success before it starts.
        migration.record_upgrade_publication(self.root)
        with patch.object(upgrade.subprocess_util, "isolated_run", side_effect=[
                subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 1)]), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "Graph index update failed"):
                upgrade.phase_index_update(self.root)
        self.assertNotIn("upgrade_publication", migration.read_receipt(self.index))
        with self.assertRaisesRegex(migration.MigrationRequired, "all_layer_publication_unverified"):
            migration.verify_migration(self.root)
        self.assertTrue((self.index / "docs.lance/data").exists())

    def _reset_without_lance(self):
        shutil.rmtree(self.index / "docs.lance")
        (self.index / migration.RECEIPT).unlink()
        self.ctx.storage_migration_protocol = 0

    def test_schema_only_conversion_preserves_auxiliary_without_legacy_import(self):
        import builtins
        import sqlite_runtime
        self._reset_without_lance()
        legacy = sqlite_runtime.connect(self.live)
        legacy.execute("PRAGMA auto_vacuum=NONE")
        legacy.execute("VACUUM")
        self.assertEqual(legacy.execute("PRAGMA auto_vacuum").fetchone(), (0,))
        legacy.close()
        self.assertTrue(migration.detect(self.index)["migration_required"])
        self.prepare()
        self.confirm()
        real_import = builtins.__import__
        def no_legacy(name, *args, **kwargs):
            if name.split(".")[0] in {"lancedb", "lance"}:
                raise AssertionError("schema-only conversion must not import a Lance reader")
            return real_import(name, *args, **kwargs)
        with patch.object(builtins, "__import__", side_effect=no_legacy):
            receipt = migration.migrate_legacy(self.root)
        self.assertEqual(receipt["source_counts"], {"docs": 0, "code": 0})
        conn = sqlite_runtime.connect(self.live, read_only=True)
        try:
            self.assertEqual(conn.execute("SELECT body FROM preserved_memory").fetchone(), ("retain me",))
            self.assertEqual(conn.execute("SELECT value FROM meta WHERE key='store_schema_version'").fetchone(), ("7",))
            self.assertEqual(conn.execute("PRAGMA auto_vacuum").fetchone(), (2,))
        finally:
            conn.close()

    def test_historical_schema4_and5_add_tables_without_erasing_auxiliary_state(self):
        import sqlite_runtime
        import index_state_store
        fixtures = json.loads((SCRIPTS / "tests/fixtures/legacy_sqlite_state_schemas.json").read_text("utf-8"))
        for version, fixture in fixtures.items():
            with self.subTest(schema=version, historical_commit=fixture["source_commit"]):
                root = self.root / ("historical-" + version)
                index = root / ".wavefoundry/index"
                index.mkdir(parents=True)
                path = index / "index-state.sqlite"
                conn = sqlite_runtime.connect(path)
                try:
                    with conn:
                        for ddl in fixture["table_ddl"]:
                            conn.execute(ddl)
                        conn.execute("INSERT INTO meta VALUES('store_schema_version',?)", (version,))
                        conn.execute("INSERT INTO file_freshness VALUES('retained.py',1,0.2,3,'git',4)")
                        conn.execute("INSERT INTO secret_scan_cache VALUES('retained.py','hash','rules',4,1,'[]')")
                        conn.execute("INSERT INTO build_layer_meta VALUES('model_versions',?)",
                                     (json.dumps({"docs": "BAAI/bge-small-en-v1.5"}),))
                        if version == "5":
                            conn.execute("INSERT INTO layer_path_state VALUES('docs','retained.py','hash')")
                finally:
                    conn.close()
                before = path.read_bytes()
                with self.assertRaises(sqlite_runtime.StorageRecoveryRequired):
                    index_state_store.IndexStateStore(index)
                self.assertEqual(path.read_bytes(), before)
                context = SimpleNamespace(root=root, from_version="1.11.2", to_version="2.0.0.test",
                                          zip_path=None, dry_run=False, storage_migration_protocol=0)
                with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                    migration.prepare_upgrade(context)
                context.storage_migration_protocol = 1
                with patch.dict(os.environ, {migration.CONFIRM_ENV: "1"}):
                    migration.prepare_upgrade(context)
                self.assertEqual(migration.migrate_legacy(root)["state"], "published")
                conn = sqlite_runtime.connect(path, read_only=True)
                try:
                    self.assertEqual(conn.execute("SELECT * FROM file_freshness").fetchone(),
                                     ("retained.py", 1, 0.2, 3, "git", 4))
                    self.assertEqual(conn.execute("SELECT * FROM secret_scan_cache").fetchone(),
                                     ("retained.py", "hash", "rules", 4, 1, "[]"))
                    self.assertEqual(conn.execute("SELECT value FROM meta WHERE key='store_schema_version'").fetchone(), ("7",))
                    self.assertIsNotNone(conn.execute("SELECT name FROM sqlite_schema WHERE name='layer_path_state'").fetchone())
                    self.assertEqual(conn.execute("SELECT status FROM build_state WHERE id=1").fetchone(), ("building",))
                    self.assertIn("BAAI/bge-small", conn.execute("SELECT value FROM build_layer_meta WHERE key='model_versions'").fetchone()[0])
                    if version == "5":
                        self.assertEqual(conn.execute("SELECT * FROM layer_path_state").fetchone(), ("docs", "retained.py", "hash"))
                finally:
                    conn.close()

    def test_schema_only_phase_does_not_provision_legacy_reader(self):
        import setup_index
        import upgrade_wavefoundry as upgrade
        self._reset_without_lance()
        self.prepare()
        self.confirm()
        with patch.object(setup_index, "ensure_deps"), \
             patch.object(setup_index, "ensure_migration_deps", side_effect=AssertionError("no legacy sources")), \
             patch.object(upgrade.subprocess_util, "isolated_run", return_value=subprocess.CompletedProcess([], 1)), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "Semantic index update"):
                upgrade.phase_index_update(self.root)
        self.assertEqual(migration.read_receipt(self.index)["state"], "published")

    def test_current_schema_visible_only_in_wal_is_not_legacy(self):
        import sqlite_runtime
        self._reset_without_lance()
        conn = sqlite_runtime.connect(self.live)
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            before = self.live.read_bytes()
            with conn:
                conn.execute("UPDATE meta SET value='7' WHERE key='store_schema_version'")
            self.assertEqual(self.live.read_bytes(), before)
            self.assertGreater(Path(str(self.live) + "-wal").stat().st_size, 0)
            self.assertEqual(migration.detect(self.index)["sqlite_schema"], "7")
            self.assertFalse(migration.detect(self.index)["migration_required"])
        finally:
            conn.close()

    def test_bootstrap_candidate_resolves_current_without_format_change(self):
        import sqlite_runtime
        self._reset_without_lance()
        conn = sqlite_runtime.connect(self.live)
        with conn:
            conn.execute("UPDATE meta SET value='7' WHERE key='store_schema_version'")
        conn.close()
        before = self.live.read_bytes()
        with patch.object(sqlite_runtime, "connect", side_effect=sqlite_runtime.RuntimeUnavailable("not installed")):
            self.assertTrue(migration.detect(self.index)["migration_required"])
            self.prepare()
        self.confirm()
        result = migration.migrate_legacy(self.root)
        self.assertEqual((result["state"], result["disposition"]), ("complete", "already_current"))
        self.assertEqual(self.live.read_bytes(), before)

    def test_cached_missing_binding_requires_fresh_standard_resume(self):
        import sqlite_runtime
        before = self.live.read_bytes()
        with patch.object(sqlite_runtime, "apsw", None):
            with self.assertRaisesRegex(migration.MigrationRequired, "storage_runtime_restart_required.*fresh process.*wf_upgrade"):
                migration.migrate_legacy(self.root)
        self.assertEqual(self.live.read_bytes(), before)
        self.assertEqual(migration.read_receipt(self.index)["state"], "quiesced")
        self.assertIsNotNone(upgrade_lib.read_upgrade_lock(self.root))

    def test_unknown_schema_is_preserved_and_fresh_absence_needs_no_receipt(self):
        import sqlite_runtime
        self._reset_without_lance()
        conn = sqlite_runtime.connect(self.live)
        with conn:
            conn.execute("UPDATE meta SET value='999' WHERE key='store_schema_version'")
        conn.close()
        before = self.live.read_bytes()
        with self.assertRaisesRegex(migration.MigrationRequired, "schema_unsupported"):
            migration.prepare_upgrade(self.ctx)
        self.assertEqual(self.live.read_bytes(), before)
        self.assertIsNone(migration.read_receipt(self.index))
        fresh = self.root / "fresh-target"
        fresh.mkdir()
        self.assertFalse(migration.detect(fresh / ".wavefoundry/index")["migration_required"])
        self.assertIsNone(migration.prepare_upgrade(SimpleNamespace(root=fresh, dry_run=False)))

    def test_orphan_wal_is_not_treated_as_a_fresh_empty_index(self):
        self._reset_without_lance()
        self.live.unlink()
        wal = Path(str(self.live) + "-wal")
        wal.write_bytes(b"retained orphan sidecar")
        with self.assertRaisesRegex(migration.MigrationRequired, "orphan SQLite sidecars"):
            migration.detect(self.index)
        self.assertEqual(wal.read_bytes(), b"retained orphan sidecar")
        self.assertFalse(self.live.exists())

    def test_orphan_vectors_cannot_be_verified_or_cleaned_up(self):
        import sqlite_runtime
        self.convert()
        conn = sqlite_runtime.connect(self.live)
        try:
            conn.execute("PRAGMA foreign_keys=OFF")
            with conn:
                conn.execute("INSERT INTO vectors_docs(chunk_id,embedding) SELECT 9999,embedding FROM vectors_docs LIMIT 1")
                conn.execute("UPDATE build_state SET status='complete',attempt_id='fixture',generation=1 WHERE id=1")
        finally:
            conn.close()
        migration.record_upgrade_publication(self.root)
        with patch.object(migration.os, "getpid", return_value=os.getpid() + 10000):
            with self.assertRaisesRegex(migration.MigrationRequired, "vector_integrity_failed"):
                migration.verify_migration(self.root)
        self.assertTrue((self.index / "docs.lance/data").exists())

    def test_semantic_failure_stops_before_graph_during_migration(self):
        import upgrade_wavefoundry as upgrade
        self.convert()
        with patch.object(upgrade.subprocess_util, "isolated_run", return_value=subprocess.CompletedProcess([], 1)) as child, \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "Semantic index update"):
                upgrade.phase_index_update(self.root)
        self.assertEqual(child.call_count, 1)
        self.assertNotIn("upgrade_publication", migration.read_receipt(self.index))

    def test_real_pinned_legacy_reader_transfers_without_optional_pylance(self):
        try:
            import lancedb
        except ImportError:
            self.skipTest("migration-only Lance reader unavailable")
        if lancedb.__version__ != "0.33.0":
            self.skipTest("requires pinned migration-only Lance reader")
        # Replace the initial placeholder before recording the source identity.
        shutil.rmtree(self.index / "docs.lance")
        (self.index / migration.RECEIPT).unlink()
        self.ctx.storage_migration_protocol = 0
        lancedb.connect(self.index).create_table("docs", self.rows)
        self.prepare()
        self.confirm()
        receipt = migration.migrate_legacy(self.root)
        self.assertEqual(receipt["source_counts"], {"docs": 1, "code": 0})

    def test_interrupted_cutover_resumes_from_owned_validated_candidate(self):
        original_replace = os.replace
        def fail_cutover(source, destination):
            if Path(destination) == self.live:
                raise OSError("injected cutover failure")
            return original_replace(source, destination)
        with patch.object(migration.os, "replace", side_effect=fail_cutover):
            with self.assertRaisesRegex(migration.MigrationRequired, "storage_cutover_io_failed"):
                self.convert()
        self.assertEqual(migration.read_receipt(self.index)["state"], "cutover_pending")
        with patch.object(migration, "_legacy_batches", side_effect=AssertionError("retry must use validated candidate")):
            self.assertEqual(migration.migrate_legacy(self.root)["state"], "published")

    def test_native_runtime_preflight_refusal_precedes_staging_and_preserves_retry(self):
        import sqlite_runtime
        original = self.live.read_bytes()
        for error in (sqlite_runtime.RuntimeUnavailable("runtime unavailable"),
                      sqlite_runtime.StorageRecoveryRequired("WAL unavailable")):
            with self.subTest(error=type(error).__name__), \
                 patch.object(sqlite_runtime, "preflight", side_effect=error), \
                 patch.object(sqlite_runtime, "backup", side_effect=AssertionError("must not stage")):
                with self.assertRaisesRegex(migration.MigrationRequired, "before staging or cutover"):
                    self.convert()
            self.assertEqual(self.live.read_bytes(), original)
            self.assertNotIn("work_dir", migration.read_receipt(self.index))
            self.assertTrue((self.index / "docs.lance/data").exists())
        self.assertEqual(self.convert()["state"], "published")

    def test_cutover_access_errors_retain_candidate_and_retry_without_transfer(self):
        original_replace = os.replace
        original_unlink = Path.unlink
        for operation in ("replace", "-wal", "-shm"):
            for winerror in (5, 32):
                with self.subTest(operation=operation, winerror=winerror):
                    # Each scenario needs its own original source and receipt.
                    self.setUp()
                    original_hash = migration._file_hash(self.live)
                    denied = PermissionError(13, "injected Windows access/sharing failure")
                    denied.winerror = winerror
                    def replace(source, destination):
                        if operation == "replace" and Path(destination) == self.live:
                            raise denied
                        return original_replace(source, destination)
                    def unlink(path, *args, **kwargs):
                        if operation != "replace" and path == Path(str(self.live) + operation):
                            raise denied
                        return original_unlink(path, *args, **kwargs)
                    with patch.object(migration.os, "replace", side_effect=replace), \
                         patch.object(Path, "unlink", unlink):
                        with self.assertRaisesRegex(migration.MigrationRequired, "storage_cutover_io_failed") as raised:
                            self.convert()
                    self.assertIs(raised.exception.__cause__, denied)
                    receipt = migration.read_receipt(self.index)
                    self.assertEqual(receipt["state"], "cutover_pending")
                    candidate = self.index / receipt["work_dir"] / "index-state.sqlite"
                    self.assertEqual(migration._file_hash(candidate), receipt["candidate_sha256"])
                    self.assertEqual(migration._file_hash(self.live), original_hash)
                    self.assertTrue((candidate.parent / "rollback.sqlite").exists())
                    self.assertTrue((self.index / "docs.lance/data").exists())
                    with patch.object(migration, "_legacy_batches", side_effect=AssertionError("no retransferring")):
                        self.assertEqual(migration.migrate_legacy(self.root)["state"], "published")

    def test_cleanup_distinguishes_unowned_path_from_failed_removal(self):
        import sqlite_runtime
        import upgrade_wavefoundry as upgrade
        self.convert()
        migration.record_upgrade_publication(self.root)
        with contextlib.closing(sqlite_runtime.connect(self.live)) as conn, conn:
            conn.execute("UPDATE build_state SET status='complete',attempt_id='fixture',generation=1 WHERE id=1")
        child = subprocess.run([sys.executable, "-B", str(SCRIPTS / "sqlite_storage_migration.py"), "--verify", str(self.root)],
                               capture_output=True, text=True)
        self.assertEqual(child.returncode, 0, child.stderr)
        for result, code in (("unowned", "storage_cleanup_path_unowned"),
                             ("failed", "storage_cleanup_removal_failed")):
            with self.subTest(result=result), patch.object(upgrade, "_remove_retired_component", return_value=result) as remove:
                with self.assertRaisesRegex(migration.MigrationRequired, code):
                    migration.cleanup_legacy(self.root)
            remove.assert_called_with(self.index, "docs.lance", custom=False, ownership_root=self.root)
            self.assertEqual(migration.read_receipt(self.index)["state"], "cleanup_pending")
            self.assertTrue((self.index / "docs.lance/data").exists())
        self.assertEqual(migration.cleanup_legacy(self.root)["state"], "complete")

    def test_retry_refuses_dangling_rollback_main_or_sidecar_before_backup(self):
        import sqlite_runtime
        self.rows[0]["vector"] = []
        with self.assertRaisesRegex(migration.MigrationRequired, "vector_invalid"):
            self.convert()
        work = self.index / migration.read_receipt(self.index)["work_dir"]
        before = self.live.read_bytes()
        for suffix in ("", "-wal", "-shm"):
            with self.subTest(suffix=suffix):
                candidate = work / ("rollback.sqlite" + suffix)
                retained = self.root / ("retained-rollback" + suffix)
                if candidate.exists():
                    candidate.rename(retained)
                outside = self.root / ("must-not-create" + suffix)
                candidate.symlink_to(outside)
                try:
                    with patch.object(sqlite_runtime, "backup", side_effect=AssertionError("no unowned native backup")):
                        with self.assertRaisesRegex(migration.MigrationRequired, "path_unowned"):
                            self.convert()
                finally:
                    candidate.unlink()
                    if retained.exists():
                        retained.rename(candidate)
                self.assertFalse(outside.exists())
                self.assertEqual(self.live.read_bytes(), before)
                self.assertTrue((self.index / "docs.lance/data").exists())

    def test_replaced_staging_directory_is_not_adopted(self):
        self.rows[0]["vector"] = []
        with self.assertRaises(migration.MigrationRequired):
            self.convert()
        receipt = migration.read_receipt(self.index)
        work = self.index / receipt["work_dir"]
        work.rename(work.with_name("retained-original"))
        work.mkdir()
        with self.assertRaisesRegex(migration.MigrationRequired, "staging_identity_changed"):
            self.convert()


if __name__ == "__main__":
    unittest.main()
