"""Receipt fencing and real native conversion; no model downloads or indexing."""
from __future__ import annotations

import contextlib
import errno
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
import index_paths
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

    def confirm(self, protocol=2):
        # The INSTALLED CLI declares storage protocol 2 (it can run the
        # schema-8 kind in-process); pass 1 to model an older coordinator.
        self.ctx.storage_migration_protocol = protocol
        with patch.dict(os.environ, {migration.CONFIRM_ENV: "1"}):
            return migration.prepare_upgrade(self.ctx)

    def test_direct_identity_equalities_are_only_reviewed_boundaries(self):
        # Bounded syntax guard, not arbitrary dataflow proof. Exact normalized
        # comparisons are excluded: same-run snapshots, content/configuration
        # hashes, owned path roles, and strict persisted-to-persisted binding.
        # No whole function is exempt; adding a persisted comparison to a
        # snapshot owner must still fail this guard.
        import ast
        modules = ("sqlite_storage_migration", "setup_readiness", "setup_reconciliation",
                   "upgrade_extensions", "retrieval_eval")
        sources = {name: (SCRIPTS / (name + ".py")).read_text() for name in modules}
        def scan(name, source):
            found = set()
            for owner in ast.walk(ast.parse(source)):
                if not isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for node in ast.walk(owner):
                    if not isinstance(node, ast.Compare) or not any(
                            isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops):
                        continue
                    expression = ast.unparse(node)
                    if any(key in expression for key in ("identity", "st_dev", "st_ino")) or any(
                            isinstance(part, ast.Name) and part.id in {"stored", "live", "retained", "published"}
                            for part in ast.walk(node)):
                        found.add((name, owner.name, expression))
            return found
        allowed = {('retrieval_eval', '_leftover_temporary_aliases', 'entry.st_dev == published.st_dev'),
         ('retrieval_eval', '_leftover_temporary_aliases', 'entry.st_ino == published.st_ino'),
         ('retrieval_eval',
          '_validate_baseline_compatibility',
          "baseline.get('evaluator_identity') == report.get('evaluator_identity')"),
         ('retrieval_eval',
          'read_baseline_bytes',
          '(named.st_dev, named.st_ino) == (held.st_dev, held.st_ino)'),
         ('retrieval_eval', 'run_evaluation', "end_identity['digest'] == production_identity['digest']"),
         ('setup_readiness', 'assess_setup', 'loaded_identity != identity'),
         ('setup_readiness', 'assess_setup', "stamp.get('configuration') != _configuration_identity(root)"),
         ('setup_readiness', 'assess_setup', "stamp.get('environment') != _environment_identity()"),
         ('setup_readiness', 'assess_setup', "stamp['sources'] != identity['sources']"),
         ('sqlite_storage_migration',
          '_candidate_build_scope',
          "receipt.get('work_identity') != _identity(work)"),
         ('sqlite_storage_migration', '_database_schema', '_identity(path) != identity'),
         ('sqlite_storage_migration', '_migrate_schema8', '_identity(source) != source_snapshot'),
         ('sqlite_storage_migration', '_migrate_schema8', 'live != source'),
         ('sqlite_storage_migration', '_migrate_schema8', 'live == source'),
         ('sqlite_storage_migration',
          '_resume_schema8_cutover',
          "_file_hash(live) == receipt.get('candidate_sha256')"),
         ('sqlite_storage_migration', '_resume_schema8_cutover', 'live == source'),
         ('sqlite_storage_migration',
          '_validated_rebuild_proof',
          "version != f'{model}@{precision}@{indexer._identity_fingerprint_for_class(precision)}'"),
         ('sqlite_storage_migration',
          'is_unpublished_candidate',
          '_identity(_safe_sqlite(candidate)) != candidate_id'),
         ('sqlite_storage_migration', 'is_unpublished_candidate', '_identity(staging) != staging_id'),
         ('sqlite_storage_migration', 'is_unpublished_candidate', '_identity(work) != work_id'),
         ('sqlite_storage_migration',
          'is_unpublished_candidate',
          "receipt.get('work_identity') != work_id"),
         ('sqlite_storage_migration',
          'migrate_legacy',
          "_file_hash(live) == receipt.get('candidate_sha256')"),
         ('sqlite_storage_migration', 'migrate_legacy', 'live == source_path'),
         ('sqlite_storage_migration',
          'read_restart_action',
          "action.get('root_identity') != receipt['root_identity']")}
        observed = set().union(*(scan(name, source) for name, source in sources.items()))
        self.assertEqual(observed, allowed)
        mutations = (
            ("sqlite_storage_migration", "if source_identity is None or not source.exists() or not storage_identity.compare_identity(source_identity, _identity(source))[\"matches\"]:",
             "if source_identity is None or not source.exists() or source_identity != _identity(source):"),
            ("setup_readiness", "matches(receipt.get('root_identity'), 'receipt')", "receipt.get('root_identity') == identity"),
            ("retrieval_eval", 'comparison["matches"]', 'stored == live'),
        )
        for name, old, replacement in mutations:
            with self.subTest(module=name):
                self.assertIn(old, sources[name])
                mutant = sources[name].replace(old, replacement, 1)
                self.assertTrue(scan(name, mutant) - allowed, "direct identity regression was not detected")

    def test_device_drift_preserves_pending_records_and_later_refusals(self):
        with patch.dict(os.environ, {migration.INVOCATION_ENV: "drift-nonce"}):
            receipt = self.prepare()
        files = [self.index / migration.RECEIPT,
                 self.root / ".wavefoundry/upgrade-in-progress.json"]
        original = {path: path.read_bytes() for path in files}
        identity = migration._identity
        def drift(path):
            value = identity(path)
            return {**value, "device": value["device"] + 1}
        with patch.object(migration, "_identity", side_effect=drift):
            self.assertEqual(migration.read_receipt(self.index), receipt)
            report = migration.detect(self.index)
            self.assertEqual(report["receipt"], receipt)
            self.assertEqual(report["identity_comparison"],
                             {"matches": True, "basis": "path+inode", "device_drift": True})
            self.assertIsNotNone(migration.read_restart_action(self.root, 3, "drift-nonce"))
            # A valid drifted root cannot relax a later continuation binding.
            self.assertIsNone(migration.read_restart_action(self.root, 3, "wrong-nonce"))
        self.assertEqual({path: path.read_bytes() for path in files}, original)
        receipt["kind"] = "unsupported-kind"
        files[0].write_text(json.dumps(receipt))
        before = files[0].read_bytes()
        with patch.object(migration, "_identity", side_effect=drift):
            with self.assertRaisesRegex(migration.MigrationRequired, "storage_receipt_kind_unsupported"):
                migration.read_receipt(self.index)
        self.assertEqual(files[0].read_bytes(), before)

    def test_persisted_identity_refusal_preserves_receipt_and_artifacts(self):
        receipt = self.prepare()
        path = self.index / migration.RECEIPT
        identity = migration._identity
        def replaced(target):
            value = identity(target)
            return {**value, "inode": value["inode"] + 1}
        original = path.read_bytes()
        with patch.object(migration, "_identity", side_effect=replaced):
            with self.assertRaisesRegex(migration.MigrationRequired, "storage_receipt_identity_mismatch"):
                migration.read_receipt(self.index)
        self.assertEqual(path.read_bytes(), original)
        def changed_artifact(target):
            value = identity(target)
            return {**value, "inode": value["inode"] + 1} if Path(target).name == "docs.lance" else value
        with patch.object(migration, "_identity", side_effect=changed_artifact):
            recovered = migration.read_receipt(self.index)
            with self.assertRaisesRegex(migration.MigrationRequired, "storage_source_identity_changed"):
                migration._assert_sources(self.index, recovered)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual((self.index / "docs.lance/data").read_bytes(), b"retained legacy source")
        for malformed in (None, {}, {"device": 1, "inode": "0"},
                          {"device": 1, "inode": False}, {"device": 1, "inode": -1}):
            with self.subTest(identity=malformed):
                receipt["root_identity"] = malformed
                path.write_text(json.dumps(receipt)); before = path.read_bytes()
                with self.assertRaisesRegex(migration.MigrationRequired, "storage_receipt_identity_mismatch"):
                    migration.read_receipt(self.index)
                self.assertEqual(path.read_bytes(), before)

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
        for owned in (index_paths.index_database_path(self.index),
                      index_paths.legacy_index_database_path(self.index)):
            self.assertFalse(owned.exists(), owned)
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
        # The conversion READS the retired name and PUBLISHES the name runtime
        # consumers open; after the schema-8 rename those are two files, so the
        # fixture names both by role instead of by string.
        self.source = index_paths.legacy_index_database_path(self.index)
        self.live = index_paths.index_database_path(self.index)
        import sqlite_runtime
        with contextlib.closing(sqlite_runtime.connect(self.source)) as conn, conn:
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
        before = self.source.read_bytes()
        with patch.object(migration, "_legacy_counts", return_value=counts), \
             patch.object(migration, "_legacy_batches", side_effect=AssertionError("capacity refusal precedes scan")):
            with self.assertRaisesRegex(migration.MigrationRequired, "storage_capacity_unqualified"):
                migration.migrate_legacy(self.root)
        receipt = migration.read_receipt(self.index)
        self.assertEqual(receipt["last_failure"]["code"], "storage_capacity_unqualified")
        self.assertFalse(receipt["capacity_qualification"]["qualified"])
        self.assertNotIn("work_dir", receipt)
        self.assertEqual(self.source.read_bytes(), before)
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
        with contextlib.closing(sqlite_runtime.connect(self.source, read_only=True)) as conn:
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
        before = self.source.read_bytes()
        with self.assertRaises(migration.MigrationRequired) as refused:
            migration.migrate_legacy(self.root)
        self.assertIn("storage_legacy_source_unreadable", str(refused.exception))
        self.assertIn("Current wf setup --full cannot bypass", str(refused.exception))
        self.assertEqual(self.source.read_bytes(), before)
        self.assertTrue((self.index / "docs.lance/data").exists())
        self.assertEqual(migration.read_receipt(self.index)["state"], "quiesced")
        self.assertIsNotNone(upgrade_lib.read_upgrade_lock(self.root))

    def test_legacy_fts_digest_is_not_xored_into_imported_payload(self):
        import index_state_store as state
        import sqlite_runtime
        conn = sqlite_runtime.connect(self.source)
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
                    if scope == "all":
                        # The model-heavy child seam must publish the provenance
                        # a real all-layer builder writes before completing its epoch.
                        import indexer
                        import chunker
                        import index_compatibility
                        with contextlib.closing(state.IndexStateStore(self.index)) as store:
                            with index_compatibility.writer_transaction(store._conn):
                                state.write_build_bookkeeping_locked(store._conn, {
                                    "walker_version": indexer.WALKER_VERSION,
                                    "chunker_versions": {layer: chunker.CHUNKER_VERSION for layer in ("docs", "code")},
                                    "model_versions": {layer: f"{model}@full@{indexer._identity_fingerprint_for_class('full')}"
                                                       for layer, model in (("docs", indexer.DOCS_MODEL), ("code", indexer.CODE_MODEL))},
                                })
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

    @patch.dict(os.environ, {migration.CONFIRM_ENV: "1"})
    @patch.object(migration, "discover_hosts", new=lambda root: ([], ["fixture confirmed hosts"]))
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

    @patch.dict(os.environ, {migration.CONFIRM_ENV: "1"})
    @patch.object(migration, "discover_hosts", new=lambda root: ([], ["fixture confirmed hosts"]))
    def test_normal_native_phase_still_verifies_its_completed_epoch(self):
        import upgrade_wavefoundry as upgrade
        self.convert()
        observed = []
        with patch.object(upgrade.subprocess_util, "isolated_run", side_effect=self._native_phase_children(observed)), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(upgrade.phase_index_update(self.root))
        self.assertEqual(observed, [("all", "complete"), ("graph", "complete"), ("verify", "complete")])
        self.assertEqual(migration.read_receipt(self.index)["state"], "verified")

    @patch.dict(os.environ, {migration.CONFIRM_ENV: "1"})
    @patch.object(migration, "discover_hosts", new=lambda root: ([], ["fixture confirmed hosts"]))
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

    @patch.dict(os.environ, {migration.CONFIRM_ENV: "1"})
    @patch.object(migration, "discover_hosts", new=lambda root: ([], ["fixture confirmed hosts"]))
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

    @patch.dict(os.environ, {migration.CONFIRM_ENV: "1"})
    @patch.object(migration, "discover_hosts", new=lambda root: ([], ["fixture confirmed hosts"]))
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

    @patch.dict(os.environ, {migration.CONFIRM_ENV: "1"})
    @patch.object(migration, "discover_hosts", new=lambda root: ([], ["fixture confirmed hosts"]))
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
        legacy = sqlite_runtime.connect(self.source)
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
            self.assertEqual(conn.execute("SELECT value FROM meta WHERE key='store_schema_version'").fetchone(),
                             (migration.SCHEMA_VERSION,))
            self.assertEqual(conn.execute("PRAGMA auto_vacuum").fetchone(), (2,))
        finally:
            conn.close()

    def test_every_legacy_schema_adds_tables_without_erasing_auxiliary_state(self):
        """One subtest per MIGRATABLE schema, driven by LEGACY_SCHEMA_VERSIONS.

        The covered set is derived from the dispatch constant, not from the
        fixture file: a fixture entry captured for the CURRENT schema must not
        silently assert legacy behavior, and a version added to the dispatch
        set without a fixture must fail rather than be skipped. The
        post-migration version is read from the constant so a future bump
        cannot leave a stale literal passing for an unrelated reason.

        The arms disagree about FTS, so each side is asserted: schemas that
        predate the canonical-chunk FTS contract legitimately lose their FTS
        tables, payload digests and lexical statistics, while a schema-7
        source keeps all three (wave 1xny6 — the additive 7 -> 8 arm).
        """
        import sqlite_runtime
        import index_state_store
        fixtures = json.loads((SCRIPTS / "tests/fixtures/legacy_sqlite_state_schemas.json").read_text("utf-8"))
        covered = sorted(migration.LEGACY_SCHEMA_VERSIONS, key=int)
        self.assertTrue(covered)
        missing = [v for v in covered if v not in fixtures]
        self.assertEqual(missing, [], f"no captured fixture for migratable schema(s) {missing}")
        self.assertNotIn(migration.SCHEMA_VERSION, migration.LEGACY_SCHEMA_VERSIONS)
        for version in covered:
            fixture = fixtures[version]
            keeps_fts = version in index_state_store.LEGACY_SCHEMA_ADDITIVE_VERSIONS
            with self.subTest(schema=version, historical_commit=fixture["source_commit"]):
                root = self.root / ("historical-" + version)
                index = root / ".wavefoundry/index"
                index.mkdir(parents=True)
                # A real source for the auxiliary rows below: the schema-8 kind
                # rebuilds the graph from current sources, and a row naming a
                # file that does not exist is legitimately reconciled away.
                (root / "retained.py").write_text("def retained():\n    return 1\n", encoding="utf-8")
                # Seed under the CURRENT name first, so the ordinary-open
                # refusal below is the real one a consumer would hit, then move
                # it to the retired name: the pre-rename layout the upgrade finds.
                published = index_paths.index_database_path(index)
                path = index_paths.legacy_index_database_path(index)
                conn = sqlite_runtime.connect(published)
                try:
                    with conn:
                        for ddl in fixture["table_ddl"]:
                            conn.execute(ddl)
                        conn.execute("INSERT INTO meta VALUES('store_schema_version',?)", (version,))
                        conn.execute("INSERT INTO file_freshness VALUES('retained.py',1,0.2,3,'git',4)")
                        conn.execute("INSERT INTO secret_scan_cache VALUES('retained.py','hash','rules',4,1,'[]')")
                        conn.execute("INSERT INTO build_layer_meta VALUES('model_versions',?)",
                                     (json.dumps({"docs": "BAAI/bge-small-en-v1.5"}),))
                        if version in {"5", "6", "7"}:
                            conn.execute("INSERT INTO layer_path_state VALUES('docs','retained.py','hash')")
                        # Lexical state every real store of every one of these
                        # schemas carries (the capability flag is written on
                        # each open since schema 2). Seeded for ALL versions so
                        # the reset arms' deletion is what the assertions below
                        # observe, not an unrelated capability-probe wipe.
                        # (Row-level FTS preservation is pinned directly
                        # against the arm in test_index_state_store.)
                        conn.execute("INSERT INTO meta VALUES(?,?)",
                                     (index_state_store.META_FTS_AVAILABLE, "1"))
                        conn.execute("INSERT INTO meta VALUES(?,?)",
                                     (index_state_store.META_FTS_PAYLOAD_DIGEST_PREFIX + "docs",
                                      "ab" * 32))
                        conn.execute("INSERT INTO meta VALUES(?,?)",
                                     (index_state_store.META_LEXICAL_STATISTICS,
                                      json.dumps({"version": index_state_store.LEXICAL_STATISTICS_VERSION})))
                finally:
                    conn.close()
                before = published.read_bytes()
                with self.assertRaises(sqlite_runtime.StorageRecoveryRequired):
                    index_state_store.IndexStateStore(index)
                self.assertEqual(published.read_bytes(), before)
                published.rename(path)
                context = SimpleNamespace(root=root, from_version="1.11.2", to_version="2.0.0.test",
                                          zip_path=None, dry_run=False, storage_migration_protocol=0)
                with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                    migration.prepare_upgrade(context)
                # A schema-7 source dispatches the schema-8 kind, which needs a
                # coordinator declaring storage protocol 2; 4/5/6 take the
                # version-1 conversion, which needs only 1.
                context.storage_migration_protocol = migration.required_protocol(
                    migration.read_receipt(index))
                with patch.dict(os.environ, {migration.CONFIRM_ENV: "1"}):
                    migration.prepare_upgrade(context)
                self.assertEqual(migration.migrate_legacy(root)["state"], "published")
                # The conversion publishes the name runtime consumers open; the
                # historical source is retained until receipt-owned cleanup.
                self.assertTrue(path.exists())
                conn = sqlite_runtime.connect(published, read_only=True)
                try:
                    if keeps_fts:
                        # The kind runs the ordinary graph builder against the
                        # current sources, which recomputes source-derived
                        # bookkeeping; the row identity must survive.
                        self.assertIsNotNone(conn.execute(
                            "SELECT path FROM file_freshness WHERE path='retained.py'").fetchone())
                        self.assertIsNotNone(conn.execute(
                            "SELECT path FROM secret_scan_cache WHERE path='retained.py'").fetchone())
                    else:
                        self.assertEqual(conn.execute("SELECT * FROM file_freshness").fetchone(),
                                         ("retained.py", 1, 0.2, 3, "git", 4))
                        self.assertEqual(conn.execute("SELECT * FROM secret_scan_cache").fetchone(),
                                         ("retained.py", "hash", "rules", 4, 1, "[]"))
                    self.assertEqual(conn.execute("SELECT value FROM meta WHERE key='store_schema_version'").fetchone(),
                                     (index_state_store.STATE_STORE_SCHEMA_VERSION,))
                    self.assertIsNotNone(conn.execute("SELECT name FROM sqlite_schema WHERE name='layer_path_state'").fetchone())
                    # The version-1 conversion leaves the epoch un-finalized for
                    # the ordinary build that follows; the schema-8 kind rebuilds
                    # the graph in staging and finalizes its own epoch.
                    self.assertEqual(conn.execute("SELECT status FROM build_state WHERE id=1").fetchone(),
                                     ("complete",) if keeps_fts else ("building",))
                    self.assertIn("BAAI/bge-small", conn.execute("SELECT value FROM build_layer_meta WHERE key='model_versions'").fetchone()[0])
                    # Every migratable source reaches the schema-8 graph tables.
                    self.assertIsNotNone(conn.execute(
                        "SELECT name FROM sqlite_schema WHERE name='graph_nodes'").fetchone())
                    if version in {"5", "6", "7"}:
                        self.assertEqual(conn.execute("SELECT * FROM layer_path_state").fetchone(), ("docs", "retained.py", "hash"))
                    digest = conn.execute(
                        "SELECT value FROM meta WHERE key=?",
                        (index_state_store.META_FTS_PAYLOAD_DIGEST_PREFIX + "docs",)).fetchone()
                    stats = conn.execute(
                        "SELECT value FROM meta WHERE key=?",
                        (index_state_store.META_LEXICAL_STATISTICS,)).fetchone()
                    if keeps_fts:
                        # Additive arm: the FTS tables and their digest key
                        # survive the bump. The kind's staged rebuild then runs
                        # the ordinary derived-FTS verify, which recomputes the
                        # digest over the real canonical tables — row-level arm
                        # preservation is pinned in test_index_state_store.
                        self.assertIsNotNone(digest)
                        self.assertIsNotNone(conn.execute(
                            "SELECT name FROM sqlite_schema WHERE name='fts_docs'").fetchone())
                    else:
                        # Pre-canonical arm: the legacy FTS tables and the
                        # digests describing them are dropped, so the freshly
                        # created empty tables start from the empty digest.
                        self.assertEqual(digest, ("0" * 64,))
                        self.assertIsNone(stats)
                finally:
                    conn.close()

    @patch.dict(os.environ, {migration.CONFIRM_ENV: "1"})
    @patch.object(migration, "discover_hosts", new=lambda root: ([], ["fixture confirmed hosts"]))
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
        conn = sqlite_runtime.connect(self.source)
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            before = self.source.read_bytes()
            with conn:
                conn.execute("UPDATE meta SET value=? WHERE key='store_schema_version'",
                             (migration.SCHEMA_VERSION,))
            self.assertEqual(self.source.read_bytes(), before)
            self.assertGreater(Path(str(self.source) + "-wal").stat().st_size, 0)
            self.assertEqual(migration.detect(self.index)["sqlite_schema"], migration.SCHEMA_VERSION)
            # Schema 8 under the RETIRED name still owes the rename, so the
            # schema read is current while the kind is still required.
            self.assertTrue(migration.detect(self.index)["kind_required"])
        finally:
            conn.close()

    def test_bootstrap_candidate_resolves_current_without_format_change(self):
        import sqlite_runtime
        self._reset_without_lance()
        self.source.rename(self.live)
        conn = sqlite_runtime.connect(self.live)
        with conn:
            conn.execute("UPDATE meta SET value=? WHERE key='store_schema_version'",
                         (migration.SCHEMA_VERSION,))
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
        before = self.source.read_bytes()
        with patch.object(sqlite_runtime, "apsw", None):
            with self.assertRaisesRegex(migration.MigrationRequired, "storage_runtime_restart_required.*fresh process.*recorded owning setup or upgrade continuation"):
                migration.migrate_legacy(self.root)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(migration.read_receipt(self.index)["state"], "quiesced")
        self.assertIsNotNone(upgrade_lib.read_upgrade_lock(self.root))

    def test_unknown_schema_is_preserved_and_fresh_absence_needs_no_receipt(self):
        import sqlite_runtime
        self._reset_without_lance()
        conn = sqlite_runtime.connect(self.source)
        with conn:
            conn.execute("UPDATE meta SET value='999' WHERE key='store_schema_version'")
        conn.close()
        before = self.source.read_bytes()
        with self.assertRaisesRegex(migration.MigrationRequired, "schema_unsupported"):
            migration.prepare_upgrade(self.ctx)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertIsNone(migration.read_receipt(self.index))
        fresh = self.root / "fresh-target"
        fresh.mkdir()
        self.assertFalse(migration.detect(fresh / ".wavefoundry/index")["migration_required"])
        self.assertIsNone(migration.prepare_upgrade(SimpleNamespace(root=fresh, dry_run=False)))

    def test_orphan_wal_is_not_treated_as_a_fresh_empty_index(self):
        self._reset_without_lance()
        self.source.unlink()
        wal = Path(str(self.source) + "-wal")
        wal.write_bytes(b"retained orphan sidecar")
        with self.assertRaisesRegex(migration.MigrationRequired, "orphan SQLite sidecars"):
            migration.detect(self.index)
        self.assertEqual(wal.read_bytes(), b"retained orphan sidecar")
        self.assertFalse(self.source.exists())

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

    @patch.dict(os.environ, {migration.CONFIRM_ENV: "1"})
    @patch.object(migration, "discover_hosts", new=lambda root: ([], ["fixture confirmed hosts"]))
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
        original = self.source.read_bytes()
        for error in (sqlite_runtime.RuntimeUnavailable("runtime unavailable"),
                      sqlite_runtime.StorageRecoveryRequired("WAL unavailable")):
            with self.subTest(error=type(error).__name__), \
                 patch.object(sqlite_runtime, "preflight", side_effect=error), \
                 patch.object(sqlite_runtime, "backup", side_effect=AssertionError("must not stage")):
                with self.assertRaisesRegex(migration.MigrationRequired, "before staging or cutover"):
                    self.convert()
            self.assertEqual(self.source.read_bytes(), original)
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
                    original_hash = migration._file_hash(self.source)
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
                    # Staging is named for the store module that opens it.
                    candidate = migration.staged_database_path(self.index / receipt["work_dir"])
                    self.assertEqual(migration._file_hash(candidate), receipt["candidate_sha256"])
                    self.assertFalse(self.live.exists())
                    self.assertEqual(migration._file_hash(self.source), original_hash)
                    self.assertTrue((candidate.parent / migration.STAGING_ROLLBACK_STEM).exists())
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
        before = self.source.read_bytes()
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
                self.assertEqual(self.source.read_bytes(), before)
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


# The last commit that shipped the version-1-only receipt reader. Its
# `read_receipt` rejects any receipt_version other than 1, which IS the
# old-code fence a version-2 record installs.
V1_RECEIPT_READER_COMMIT = "5e798daa159119c6f434eaf357b82dd264bb2a48"


@unittest.skipUnless(_native_available(), "qualified APSW + sqlite-vec runtime unavailable")
class SchemaEightKindTests(unittest.TestCase):
    """The schema-8 kind: dispatch per population, staged rebuild, cutover."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.index = self.root / ".wavefoundry/index"
        self.index.mkdir(parents=True)
        (self.root / "src").mkdir()
        (self.root / "src/m.py").write_text(
            "def helper():\n    return 1\n\n\ndef caller():\n    return helper()\n", encoding="utf-8")
        self.current = index_paths.index_database_path(self.index)
        self.legacy = index_paths.legacy_index_database_path(self.index)
        self.ctx = SimpleNamespace(root=self.root, from_version="1.22.0", to_version="1.23.0.test",
                                   zip_path=None, dry_run=False, yes=True,
                                   storage_migration_protocol=migration.PROTOCOL_SCHEMA8)

    # --- fixtures -------------------------------------------------------

    def _seed(self, schema="7", name=None, rows=()):
        """A real store produced by the canonical creator, marked at `schema`."""
        import index_state_store
        import graph_store
        store = index_state_store.IndexStateStore(self.index)
        if rows:
            index_state_store.apply_chunk_deltas(self.index, "docs", add_rows=rows)
            import indexer
            import chunker
            # This fixture represents unchanged embeddings. The canonical
            # suite selects CPU/int8 while a local run may select full precision.
            precision = indexer._predicted_precision_class(indexer.DOCS_MODEL, indexer._onnx_providers())
            index_state_store.write_build_bookkeeping(self.index, {
                "content": ["docs"], "walker_version": indexer.WALKER_VERSION,
                "chunker_versions": {"docs": chunker.CHUNKER_VERSION},
                "model_versions": {"docs": f"{indexer.DOCS_MODEL}@{precision}@{indexer._identity_fingerprint_for_class(precision)}"},
            })
        conn = store._conn
        with conn:
            if schema != migration.SCHEMA_VERSION:
                for table in graph_store.GRAPH_TABLES + graph_store.DERIVED_TABLES:
                    conn.execute(f"DROP TABLE IF EXISTS {table}")
                conn.execute("UPDATE meta SET value=? WHERE key='store_schema_version'", (schema,))
            conn.execute("CREATE TABLE IF NOT EXISTS preserved_memory(id TEXT PRIMARY KEY, body TEXT)")
            conn.execute("INSERT OR REPLACE INTO preserved_memory VALUES('memory-1','retain me')")
        store.close()
        target = self.legacy if name is None else name
        if target != self.current:
            self.current.rename(target)
            for sidecar in index_paths.sidecar_paths(self.current):
                if sidecar.exists():
                    sidecar.rename(Path(str(target) + sidecar.name[len(self.current.name):]))
        return target

    def _run(self, ctx=None):
        with patch.dict(os.environ, {migration.CONFIRM_ENV: "1"}):
            migration.prepare_upgrade(ctx or self.ctx)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return migration.migrate_legacy(self.root)

    def _interrupt_cutover_only(self):
        """Interrupt the cutover replace only; the receipt write uses os.replace too."""
        real_replace = os.replace
        def replace(source, destination):
            if Path(destination) == self.current:
                raise KeyboardInterrupt("interrupted before filesystem publication")
            return real_replace(source, destination)
        return replace

    def _verify_in_child(self):
        child = subprocess.run([sys.executable, "-B", str(SCRIPTS / "sqlite_storage_migration.py"),
                                "--verify", str(self.root)], capture_output=True, text=True)
        self.assertEqual(child.returncode, 0, child.stderr)
        return json.loads(child.stdout)

    # --- populations ----------------------------------------------------

    def test_schema8_staging_does_not_consume_live_memory_publication(self):
        import memory_backfill
        import index_state_store as state
        self._seed("7")
        run_id = memory_backfill.ensure_run(self.root, "upgrade")
        self.assertEqual(memory_backfill.sync_inventory(self.root, run_id)["state"], "ready_for_index")
        parent = self.index / "upgrade-index-staging-receipt.json"
        with memory_backfill.index_publication_scope(run_id), patch.dict(os.environ, {
                "WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT": str(parent)}):
            receipt = self._run()
        self.assertEqual(receipt["state"], "published")
        self.assertEqual(memory_backfill.run_state(self.root, run_id), "ready_for_index")
        self.assertFalse(parent.exists())
        staging = migration._staging_index_dir(self.index / receipt["work_dir"])
        self.assertFalse((staging / "memory-state.sqlite").exists())
        self.assertEqual(state.read_build_state(self.index)["status"], "complete")

    _native_phase_children = NativeMigrationTests._native_phase_children
    _native_memory_scope = NativeMigrationTests._native_memory_scope

    @patch.dict(os.environ, {migration.CONFIRM_ENV: "1"})
    @patch.object(migration, "discover_hosts", new=lambda root: ([], []))
    def test_schema8_parent_publication_retries_staged_with_live_memory(self):
        import upgrade_wavefoundry as upgrade
        import setup_index
        import indexer
        import memory_backfill
        import sqlite_vector_store as vectors
        rows = [{"id": "docs-a", "path": "src/m.py", "kind": "docs",
                 "text": "retained semantic payload", "tags": [], "start_line": 1,
                 "end_line": 1, "vector": [1.0] + [0.0] * 383}]
        self._seed("7", rows=rows)
        migration.prepare_upgrade(self.ctx)
        run_id, scope = self._native_memory_scope()
        parent = self.index / "upgrade-index-staging-receipt.json"
        original = indexer._build_index_locked
        def fail_after_build(*args, **kwargs):
            result = original(*args, **kwargs)
            self.assertFalse(result.get("failed"), result)
            self.assertEqual(memory_backfill.run_state(self.root, run_id), "ready_for_index")
            self.assertFalse(parent.exists())
            raise RuntimeError("injected after candidate completion")
        observed = []
        with scope, patch.object(setup_index, "ensure_deps"), \
                patch.object(upgrade.subprocess_util, "isolated_run", side_effect=self._native_phase_children(observed)), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with patch.object(indexer, "_build_index_locked", side_effect=fail_after_build):
                with self.assertRaisesRegex(RuntimeError, "injected after candidate"):
                    upgrade.phase_index_update_parent_owned(self.root, run_id)
            receipt = migration.read_receipt(self.index)
            self.assertEqual(receipt["state"], "staged")
            self.assertTrue(self.legacy.exists())
            self.assertFalse(self.current.exists())
            staging = migration._staging_index_dir(self.index / receipt["work_dir"])
            self.assertFalse((staging / "memory-state.sqlite").exists())
            upgrade.phase_index_update_parent_owned(self.root, run_id)
        self.assertEqual(observed, [("all", "building"), ("graph", "building"), ("verify", "complete")])
        self.assertEqual(memory_backfill.run_state(self.root, run_id), "indexed")
        self.assertEqual(vectors.payload_rows(self.index, "docs", include_vector=True), rows)
        self.assertEqual(migration.read_receipt(self.index)["state"], "verified")
        self.assertEqual(migration.cleanup_legacy(self.root)["state"], "complete")

    def test_candidate_scope_is_exact_thread_local_and_exception_safe(self):
        import indexer
        import index_state_store as state
        import threading
        self._seed("7")
        original = indexer._build_index_locked
        def inspect(*args, **kwargs):
            staging = kwargs["index_dir"]
            self.assertTrue(migration.is_unpublished_candidate(staging))
            self.assertFalse(migration.is_unpublished_candidate(self.index))
            self.assertFalse(migration.is_unpublished_candidate(staging / "other"))
            outcomes = []
            thread = threading.Thread(target=lambda: outcomes.append(migration.is_unpublished_candidate(staging)))
            thread.start()
            thread.join()
            self.assertEqual(outcomes, [False])
            result = original(*args, **kwargs)
            # The scope cannot turn a stale candidate CAS into success.
            self.assertFalse(state.finalize_build_epoch(staging, "stale-attempt"))
            # Nor can it authorize another index's unknown memory run.
            other = self.root / "other/.wavefoundry/index"
            with contextlib.closing(state.IndexStateStore(other)):
                pass
            attempt = state.begin_build_epoch(other, "graph")
            parent = other / "parent.json"
            with patch.dict(os.environ, {
                    "WAVEFOUNDRY_MEMORY_BACKFILL_RUN_ID": "unknown-run",
                    "WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT": str(parent)}):
                with self.assertRaisesRegex(ValueError, "unknown memory backfill run"):
                    state.finalize_build_epoch(other, attempt)
            self.assertEqual(state.read_build_state(other)["status"], "building")
            self.assertFalse(parent.exists())
            import memory_backfill
            wave = other.parent.parent / "docs/waves/1aaaa closed"
            wave.mkdir(parents=True)
            (wave / "wave.md").write_text(
                "# Wave\n\nStatus: closed\n\nChange ID: `1aaab-enh historical`\n", encoding="utf-8")
            (wave / "1aaab-enh historical.md").write_text(
                "# Change\n\n## Decision Log\n\n"
                "| Date | Decision | Reason | Alternatives |\n"
                "| --- | --- | --- | --- |\n"
                "| 2026-01-01 | Keep local | Offline use | Remote |\n", encoding="utf-8")
            pending = memory_backfill.ensure_run(other.parent.parent, "upgrade")
            self.assertEqual(memory_backfill.sync_inventory(other.parent.parent, pending)["state"], "awaiting_validation")
            with memory_backfill.index_publication_scope(pending), patch.dict(os.environ, {
                    "WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT": str(parent)}):
                self.assertFalse(state.finalize_build_epoch(other, attempt))
            self.assertEqual(state.read_build_state(other)["status"], "building")
            self.assertFalse(parent.exists())
            moved = staging.with_name("replaced-index")
            staging.rename(moved)
            staging.mkdir()
            try:
                with self.assertRaisesRegex(migration.MigrationRequired, "storage_staging_identity_changed"):
                    migration.is_unpublished_candidate(staging)
            finally:
                staging.rmdir()
                moved.rename(staging)
            raise RuntimeError("scope exception")
        with patch.object(indexer, "_build_index_locked", side_effect=inspect):
            with self.assertRaisesRegex(RuntimeError, "scope exception"):
                self._run()
        receipt = migration.read_receipt(self.index)
        staging = migration._staging_index_dir(self.index / receipt["work_dir"])
        self.assertFalse(migration.is_unpublished_candidate(staging))
        self.assertEqual(self._run()["state"], "published")

    def test_candidate_binding_refuses_replaced_file_and_changed_receipt(self):
        import indexer
        self._seed("7")
        def inspect(*args, **kwargs):
            staging = kwargs["index_dir"]
            candidate = migration.staged_database_path(staging)
            retained = candidate.with_name("candidate-retained.sqlite")
            candidate.rename(retained)
            candidate.write_bytes(retained.read_bytes())
            try:
                with self.assertRaisesRegex(migration.MigrationRequired, "storage_staging_identity_changed"):
                    migration.is_unpublished_candidate(staging)
            finally:
                candidate.unlink()
                retained.rename(candidate)
            receipt = migration.read_receipt(self.index)
            receipt["state"] = "validated"
            migration._write(self.index, receipt)
            with self.assertRaisesRegex(migration.MigrationRequired, "storage_staging_identity_changed"):
                migration.is_unpublished_candidate(staging)
            raise RuntimeError("binding checks complete")
        with patch.object(indexer, "_build_index_locked", side_effect=inspect):
            with self.assertRaisesRegex(RuntimeError, "binding checks complete"):
                self._run()

    def test_receiptless_schema_seven_store_requires_the_kind_and_is_renamed(self):
        source = self._seed("7")
        state = migration.detect(self.index)
        self.assertEqual((state["resolution"], state["authority_role"]), ("legacy", "legacy"))
        self.assertTrue(state["kind_required"])
        self.assertTrue(state["migration_required"])
        receipt = self._run()
        self.assertEqual((receipt["receipt_version"], receipt["kind"], receipt["state"]),
                         (migration.RECEIPT_VERSION_CURRENT, migration.KIND_SCHEMA8, "published"))
        self.assertTrue(self.current.is_file())
        # Forward recovery only: the retained source survives until cleanup.
        self.assertTrue(source.is_file())
        import sqlite_runtime
        with contextlib.closing(sqlite_runtime.connect(self.current, read_only=True)) as conn:
            self.assertEqual(conn.execute("SELECT body FROM preserved_memory").fetchone(), ("retain me",))
            self.assertEqual(conn.execute("SELECT value FROM meta WHERE key='store_schema_version'").fetchone(),
                             (migration.SCHEMA_VERSION,))
            self.assertGreater(conn.execute("SELECT count(*) FROM graph_nodes").fetchone()[0], 0)
        # The staged database was checkpointed before publication, so no
        # committed frame is left behind in a sidecar the cutover never moves.
        staging = migration._staging_index_dir(self.index / receipt["work_dir"])
        for sidecar in index_paths.sidecar_paths(migration.staged_database_path(staging)):
            self.assertFalse(sidecar.exists(), sidecar)
        self._verify_in_child()
        final = migration.cleanup_legacy(self.root)
        self.assertEqual(final["state"], "complete")
        self.assertFalse(source.exists())
        self.assertFalse((self.index / final["work_dir"]).exists())

    def test_graph_is_rebuilt_from_sources_and_never_seeded_from_old_artifacts(self):
        self._seed("7")
        stale = self.index / "graph"
        stale.mkdir()
        (stale / "project-graph.json").write_text(json.dumps(
            {"nodes": [{"id": "ghost::never_extracted"}], "edges": []}), encoding="utf-8")
        receipt = self._run()
        import sqlite_runtime
        with contextlib.closing(sqlite_runtime.connect(self.current, read_only=True)) as conn:
            ids = {row[0] for row in conn.execute("SELECT node_id FROM graph_nodes")}
        self.assertTrue(any("helper" in node for node in ids), ids)
        self.assertNotIn("ghost::never_extracted", ids)
        self.assertGreater(receipt["staged_rebuild"]["graph"]["nodes"], 0)

    def test_completed_version_one_receipt_requires_the_kind_exactly_once(self):
        source = self._seed("7")
        stale = {"receipt_version": migration.RECEIPT_VERSION_LEGACY,
                 "migration_id": "b" * 32, "index_dir": str(self.index.resolve()),
                 "root_identity": migration._identity(self.root), "state": "complete",
                 "old_hosts": [], "artifacts": {}, "reason": "legacy_storage"}
        migration._write(self.index, stale)
        pending = migration.detect(self.index)
        self.assertTrue(pending["kind_required"])
        # A record whose own state reads "done" does not clear an unsatisfied
        # once-marker: the upgrade must still dispatch.
        self.assertTrue(pending["migration_required"])
        receipt = self._run()
        self.assertEqual(receipt["supersedes"]["migration_id"], stale["migration_id"])
        self._verify_in_child()
        migration.cleanup_legacy(self.root)
        self.assertFalse(source.exists())
        # Exactly once: the once-marker now holds, so a repeat upgrade is a no-op.
        state = migration.detect(self.index)
        self.assertFalse(state["kind_required"])
        self.assertFalse(state["migration_required"])
        self.assertEqual(migration.prepare_upgrade(self.ctx)["state"], "complete")
        self.assertEqual(migration.migrate_legacy(self.root)["state"], "complete")
        self.assertEqual(migration.cleanup_legacy(self.root)["state"], "complete")

    def test_pending_version_one_receipt_finishes_its_recovery_before_the_kind(self):
        self._seed("7")
        pending = {"receipt_version": migration.RECEIPT_VERSION_LEGACY,
                   "migration_id": "c" * 32, "index_dir": str(self.index.resolve()),
                   "root_identity": migration._identity(self.root), "state": "quiesced",
                   "old_hosts": [], "artifacts": {}, "reason": "legacy_storage",
                   "pack_path": None, "pack_sha256": None,
                   "source_sqlite_identity": migration._identity(self.legacy)}
        migration._write(self.index, pending)
        with patch.dict(os.environ, {migration.CONFIRM_ENV: "1"}):
            resumed = migration.prepare_upgrade(self.ctx)
        # The package-bound legacy record keeps the receipt; no kind supersedes
        # it while it is still pending.
        self.assertEqual(resumed["migration_id"], pending["migration_id"])
        self.assertEqual(resumed["receipt_version"], migration.RECEIPT_VERSION_LEGACY)
        self.assertNotIn("kind", resumed)

    def test_both_filenames_without_a_version_two_receipt_are_ambiguous_and_preserved(self):
        self._seed("7")
        shutil.copy2(self.legacy, self.current)
        current_bytes, legacy_bytes = self.current.read_bytes(), self.legacy.read_bytes()
        state = migration.detect(self.index)
        self.assertEqual(state["resolution"], "both")
        self.assertEqual(state["authority_diagnostic"], migration.AUTHORITY_AMBIGUOUS)
        self.assertIsNone(state["authority_role"])
        for call in (lambda: migration.require_ready(self.index),
                     lambda: migration.prepare_upgrade(self.ctx),
                     lambda: migration.migrate_legacy(self.root)):
            with self.assertRaisesRegex(migration.MigrationRequired, migration.AUTHORITY_AMBIGUOUS):
                call()
        self.assertEqual(self.current.read_bytes(), current_bytes)
        self.assertEqual(self.legacy.read_bytes(), legacy_bytes)

    def test_both_filenames_resolve_through_the_version_two_receipt_only(self):
        self._seed("7")
        receipt = self._run()
        state = migration.detect(self.index)
        self.assertEqual((state["resolution"], state["authority_role"]), ("both", "current"))
        self.assertIsNone(state["authority_diagnostic"])
        self.assertIsNone(state["spurious_legacy"])
        # Authority is never mtime, size or newest schema: break the recorded
        # identity and the same two files become undecidable again.
        receipt["published_sqlite_identity"] = {"device": 1, "inode": 1}
        migration._write(self.index, receipt)
        self.assertEqual(migration.detect(self.index)["authority_diagnostic"],
                         migration.AUTHORITY_AMBIGUOUS)

    def test_reappeared_retired_name_after_cutover_is_spurious_not_authority(self):
        self._seed("7")
        self._run()
        self._verify_in_child()
        migration.cleanup_legacy(self.root)
        self.legacy.write_bytes(b"recreated by an old host")
        state = migration.detect(self.index)
        self.assertEqual(state["authority_role"], "current")
        self.assertIsNone(state["authority_diagnostic"])
        self.assertIn("old Wavefoundry host", state["spurious_legacy"])
        # Preserved, and the published index keeps serving.
        migration.require_ready(self.index)
        self.assertEqual(self.legacy.read_bytes(), b"recreated by an old host")

    def test_lance_era_source_converts_first_then_the_kind_installs_the_fence(self):
        source = self._seed("6")
        (self.index / "docs.lance").mkdir()
        (self.index / "docs.lance/data").write_bytes(b"legacy source")
        state = migration.detect(self.index)
        self.assertEqual(state["legacy"], ["docs.lance"])
        self.assertFalse(migration._kind_dispatch(state))
        with patch.dict(os.environ, {migration.CONFIRM_ENV: "1"}):
            self.ctx.storage_migration_protocol = migration.PROTOCOL_LEGACY
            converted = migration.prepare_upgrade(self.ctx)
        self.assertEqual(converted["receipt_version"], migration.RECEIPT_VERSION_LEGACY)
        with patch.object(migration, "_legacy_counts", return_value={"docs": 0, "code": 0}), \
             patch.object(migration, "_legacy_batches", return_value=iter([])):
            published = migration.migrate_legacy(self.root)
        self.assertEqual(published["state"], "published")
        self.assertTrue(self.current.is_file())
        import sqlite_runtime
        with contextlib.closing(sqlite_runtime.connect(self.current)) as conn, conn:
            conn.execute("UPDATE build_state SET status='complete',attempt_id='fixture',generation=1 WHERE id=1")
        migration.record_upgrade_publication(self.root)
        self._verify_in_child()
        final = migration.cleanup_legacy(self.root)
        # Same upgrade: the kind superseded the completed conversion, so the
        # version-2 fence is installed and the retired source is gone.
        self.assertEqual((final["receipt_version"], final["kind"], final["state"]),
                         (migration.RECEIPT_VERSION_CURRENT, migration.KIND_SCHEMA8, "complete"))
        self.assertEqual(final["supersedes"]["receipt_version"], migration.RECEIPT_VERSION_LEGACY)
        self.assertFalse(source.exists())
        self.assertFalse((self.index / "docs.lance").exists())
        self.assertFalse(migration.detect(self.index)["migration_required"])

    def test_already_current_store_is_a_no_op(self):
        self._seed(migration.SCHEMA_VERSION, name=self.current)
        state = migration.detect(self.index)
        self.assertFalse(state["kind_required"])
        self.assertFalse(state["migration_required"])
        self.assertIsNone(migration.prepare_upgrade(self.ctx))
        self.assertEqual(migration.migrate_legacy(self.root)["state"], "not_applicable")

    # --- the old-code fence ---------------------------------------------

    def test_version_one_code_refuses_a_version_two_receipt_and_creates_nothing(self):
        self._seed("7")
        self._run()
        v1_source = subprocess.run(
            ["git", "show", f"{V1_RECEIPT_READER_COMMIT}:.wavefoundry/framework/scripts/sqlite_storage_migration.py"],
            cwd=str(SCRIPTS.parents[2]), capture_output=True, text=True)
        if v1_source.returncode != 0:
            self.skipTest("version-1 reader commit unavailable in this checkout")
        module = self.root / "v1_storage_migration.py"
        module.write_text(v1_source.stdout, encoding="utf-8")
        for path in (self.legacy, *index_paths.sidecar_paths(self.legacy)):
            if path.exists():
                path.unlink()
        program = (
            "import importlib.util as u, sys;"
            f"sys.path.insert(0, {str(SCRIPTS)!r});"
            f"spec = u.spec_from_file_location('v1', {str(module)!r});"
            "m = u.module_from_spec(spec); spec.loader.exec_module(m);"
            f"m.require_ready({str(self.index)!r})"
        )
        child = subprocess.run([sys.executable, "-B", "-c", program],
                               capture_output=True, text=True, cwd=str(self.root))
        self.assertNotEqual(child.returncode, 0)
        self.assertIn("MigrationRequired", child.stderr)
        # The fence fires BEFORE any store is opened: nothing under the retired
        # name is created, not the database and not its sidecars.
        for path in (self.legacy, *index_paths.sidecar_paths(self.legacy)):
            self.assertFalse(path.exists(), path)

    def test_a_version_one_record_may_not_carry_a_kind_marker(self):
        self._seed("7")
        forged = {"receipt_version": migration.RECEIPT_VERSION_LEGACY, "kind": migration.KIND_SCHEMA8,
                  "migration_id": "d" * 32, "index_dir": str(self.index.resolve()),
                  "root_identity": migration._identity(self.root), "state": "complete",
                  "old_hosts": [], "artifacts": {}}
        (self.index / migration.RECEIPT).write_text(json.dumps(forged), encoding="utf-8")
        with self.assertRaisesRegex(migration.MigrationRequired, "storage_receipt_kind_unsupported"):
            migration.read_receipt(self.index)

    def test_an_unsupported_receipt_version_is_refused(self):
        self._seed("7")
        forged = {"receipt_version": 3, "kind": migration.KIND_SCHEMA8,
                  "migration_id": "f" * 32, "index_dir": str(self.index.resolve()),
                  "root_identity": migration._identity(self.root), "state": "complete",
                  "old_hosts": [], "artifacts": {}}
        (self.index / migration.RECEIPT).write_text(json.dumps(forged), encoding="utf-8")
        with self.assertRaisesRegex(migration.MigrationRequired, "storage_receipt_identity_mismatch"):
            migration.read_receipt(self.index)

    def test_a_completed_conversion_without_the_fence_still_requires_the_kind(self):
        # The conversion published the current name, so the once-marker holds --
        # but a version-1 record installs no fence, and a version-1 runner would
        # read "complete", find nothing under the retired name and create a
        # fresh empty database beside the published index.
        self._seed(migration.SCHEMA_VERSION, name=self.current)
        migration._write(self.index, {
            "receipt_version": migration.RECEIPT_VERSION_LEGACY, "migration_id": "a" * 32,
            "index_dir": str(self.index.resolve()), "root_identity": migration._identity(self.root),
            "state": "complete", "old_hosts": [], "artifacts": {}, "reason": "legacy_storage",
            "published_sqlite_identity": migration._identity(self.current)})
        state = migration.detect(self.index)
        self.assertTrue(state["fence_required"])
        self.assertTrue(state["kind_required"])
        self.assertTrue(state["migration_required"])
        with self.assertRaisesRegex(migration.MigrationRequired, "storage_migration_required"):
            migration.require_ready(self.index)

    def test_stale_graph_rows_in_the_source_do_not_survive_the_staged_rebuild(self):
        import graph_indexer
        import sqlite_runtime
        source = self._seed(migration.SCHEMA_VERSION)
        with contextlib.closing(sqlite_runtime.connect(source)) as conn, conn:
            conn.execute("INSERT INTO graph_nodes (node_id,label,kind,source_file,source_location,"
                         "layer,external,attributes) VALUES ('ghost::stale','ghost','function',"
                         "'deleted.py','1','project',0,'{}')")
            conn.execute("INSERT INTO graph_file_state (path,layer,source_hash,record,extracted_at) "
                         "VALUES ('deleted.py','project','stale',NULL,0)")
            # Complete current graph provenance keeps this fixture compatible;
            # only the migration's own empty start should drop its stale rows.
            import indexer
            import chunker
            versions = graph_indexer.GraphStateStore(
                conn, layer="project", walker_version=indexer.WALKER_VERSION,
                chunker_version=chunker.CHUNKER_VERSION)._expected_versions()
            conn.executemany("INSERT OR REPLACE INTO meta (key,value) VALUES (?,?)",
                             ((graph_indexer.GRAPH_META_PREFIX + key, str(value))
                              for key, value in versions.items()))
        self.assertTrue(migration.detect(self.index)["kind_required"])
        import indexer
        at_entry = {}
        real_entry = indexer._build_index_locked
        def record(root, **kwargs):
            staged = index_paths.index_database_path(Path(kwargs["index_dir"]))
            with contextlib.closing(sqlite_runtime.connect(staged, read_only=True)) as conn:
                at_entry.update({table: conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                                 for table in ("graph_nodes", "graph_edges", "graph_file_state",
                                               "graph_communities", "graph_merge_state")})
            return real_entry(root, **kwargs)
        with patch.object(indexer, "_build_index_locked", side_effect=record):
            self._run()
        # Procedure step 3: the builder starts from EMPTY graph, extraction and
        # community tables — never seeded from the source's own graph rows.
        self.assertEqual(at_entry, dict.fromkeys(at_entry, 0), at_entry)
        with contextlib.closing(sqlite_runtime.connect(self.current, read_only=True)) as conn:
            nodes = {row[0] for row in conn.execute("SELECT node_id FROM graph_nodes")}
            files = {row[0] for row in conn.execute("SELECT path FROM graph_file_state")}
        self.assertNotIn("ghost::stale", nodes)
        self.assertNotIn("deleted.py", files)
        self.assertTrue(any("helper" in node for node in nodes), nodes)

    def test_the_staged_candidate_is_checkpointed_before_its_identity_is_recorded(self):
        # Only the staged MAIN file is published, so its write-ahead log must be
        # folded in before the candidate digest and identity are recorded.
        self._seed("7")
        seen = []
        real = migration._quiesce_source
        def spy(runtime, path):
            seen.append(Path(path))
            return real(runtime, path)
        with patch.object(migration, "_quiesce_source", side_effect=spy):
            receipt = self._run()
        staged = migration.staged_database_path(
            migration._staging_index_dir(self.index / receipt["work_dir"]))
        self.assertEqual(seen, [staged, self.legacy])

    def test_verification_refuses_a_kind_record_without_its_staged_rebuild_proof(self):
        self._seed("7")
        receipt = self._run()
        receipt.pop("staged_rebuild")
        migration._write(self.index, receipt)
        with patch.object(migration.os, "getpid", return_value=os.getpid() + 10000):
            with self.assertRaisesRegex(migration.MigrationRequired, "storage_staged_rebuild_unverified"):
                migration.verify_migration(self.root)

    def test_an_unknown_kind_is_refused(self):
        self._seed("7")
        forged = {"receipt_version": migration.RECEIPT_VERSION_CURRENT, "kind": "index_sqlite_schema9",
                  "migration_id": "e" * 32, "index_dir": str(self.index.resolve()),
                  "root_identity": migration._identity(self.root), "state": "complete",
                  "old_hosts": [], "artifacts": {}}
        (self.index / migration.RECEIPT).write_text(json.dumps(forged), encoding="utf-8")
        with self.assertRaisesRegex(migration.MigrationRequired, "storage_receipt_kind_unsupported"):
            migration.read_receipt(self.index)

    # --- protocol --------------------------------------------------------

    def test_protocol_one_coordinator_still_pauses_for_the_kind(self):
        import upgrade_extensions
        self._seed("7")
        scripts = self.root / ".wavefoundry/framework/scripts"
        scripts.mkdir(parents=True)
        for name in ("sqlite_storage_migration.py", "index_paths.py"):
            shutil.copy2(SCRIPTS / name, scripts / name)
        ctx = SimpleNamespace(root=self.root, from_version="1.22.0", to_version="1.23.0.test",
                              zip_path=None, dry_run=False, yes=True,
                              runner_protocol=2, storage_migration_protocol=migration.PROTOCOL_LEGACY)
        stdout = io.StringIO()
        # Hosts-stopped IS confirmed: only the declared protocol keeps the
        # conversion out of this coordinator's process.
        with patch.dict(os.environ, {migration.CONFIRM_ENV: "1"}), contextlib.redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as paused:
                upgrade_extensions.post_extract(ctx)
        self.assertEqual(paused.exception.code, 3)
        self.assertIn('"status": "action_required"', stdout.getvalue())
        self.assertIn("storage_restart_required", stdout.getvalue())
        receipt = migration.read_receipt(self.index)
        self.assertEqual((receipt["receipt_version"], receipt["state"]),
                         (migration.RECEIPT_VERSION_CURRENT, "restart_required"))
        self.assertFalse(self.current.exists())
        # The installed CLI, which declares 2, resumes the same record.
        resumed = self._run()
        self.assertEqual(resumed["migration_id"], receipt["migration_id"])
        self.assertEqual(resumed["state"], "published")

    def test_required_protocol_is_two_for_the_kind_and_one_for_the_conversion(self):
        self.assertEqual(migration.required_protocol(None), migration.PROTOCOL_LEGACY)
        self.assertEqual(migration.required_protocol({"receipt_version": 1}), migration.PROTOCOL_LEGACY)
        self.assertEqual(migration.required_protocol({"receipt_version": 2}), migration.PROTOCOL_SCHEMA8)
        import upgrade_wavefoundry as upgrade
        context = upgrade.UpgradeContext(self.root, "1.22.0", "1.23.0", None, True)
        self.assertEqual(context.storage_migration_protocol, migration.PROTOCOL_SCHEMA8)
        self.assertEqual(context.runner_protocol, 2)

    # --- staged rebuild preconditions ------------------------------------

    def test_staged_rebuild_uses_a_nested_tree_its_own_preparation_and_a_preopened_store(self):
        import indexer
        import sqlite_vector_store
        self._seed("7")
        observed = {}
        real_entry = indexer._build_index_locked
        def record(root, **kwargs):
            staging = Path(kwargs["index_dir"])
            observed["root"] = Path(root)
            observed["staging"] = staging
            observed["preparation_index"] = kwargs["prepared"].index_dir
            observed["spool"] = kwargs["prepared"].path
            observed["content"] = kwargs["content"]
            import sqlite_runtime
            with contextlib.closing(sqlite_runtime.connect(
                    index_paths.index_database_path(staging), read_only=True)) as conn:
                observed["schema"] = conn.execute(
                    "SELECT value FROM meta WHERE key='store_schema_version'").fetchone()[0]
            return real_entry(root, **kwargs)
        with patch.object(indexer, "_build_index_locked", side_effect=record):
            self._run()
        # The source walk gets the REAL repository root...
        self.assertEqual(observed["root"], self.root)
        # ...while every parent-derived path resolves inside the staging tree.
        self.assertEqual(observed["staging"].name, "index")
        self.assertEqual(observed["staging"].parent.name, ".wavefoundry")
        self.assertEqual(observed["staging"].parent.parent.name[:len(migration.KIND_WORK_PREFIX)],
                         migration.KIND_WORK_PREFIX)
        self.assertEqual(indexer._test_run_lock_path(observed["staging"]).parents[2],
                         observed["staging"].parent.parent)
        # Empty graph-only preparation stays in RAM; any later overflow would
        # belong to staging, never the live repository's index filesystem.
        self.assertEqual(observed["preparation_index"], observed["staging"])
        self.assertIsNone(observed["spool"])
        # The pre-open already ran the legacy-to-current arm.
        self.assertEqual(observed["schema"], migration.SCHEMA_VERSION)
        self.assertEqual(observed["content"], "graph")

    def test_a_failed_staged_rebuild_preserves_the_source_and_publishes_nothing(self):
        import indexer
        self._seed("7")
        with patch.object(indexer, "_build_index_locked",
                          return_value={"failed": True, "failure": "injected extractor failure"}):
            with self.assertRaisesRegex(migration.MigrationRequired, "storage_staged_graph_rebuild_failed"):
                self._run()
        self.assertFalse(self.current.exists())
        self.assertTrue(self.legacy.is_file())
        self.assertIn("Recovery is FORWARD", migration._forward_recovery(self.legacy))
        receipt = migration.read_receipt(self.index)
        self.assertEqual(receipt["state"], "staged")
        # Forward: re-running from the retained source completes normally.
        self.assertEqual(migration.migrate_legacy(self.root)["state"], "published")

    # --- cutover and recovery --------------------------------------------

    def test_interruption_after_replace_before_receipt_advance_adopts_by_identity(self):
        import indexer
        self._seed("7")
        real_replace = os.replace
        def interrupt(source, destination):
            real_replace(source, destination)
            # `migration.os` IS the os module, so only the cutover replace may
            # be interrupted; the receipt's own durable write uses it too.
            if Path(destination) == self.current:
                raise KeyboardInterrupt("interrupted after filesystem publication")
        with patch.object(migration.os, "replace", side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self._run()
        receipt = migration.read_receipt(self.index)
        self.assertEqual(receipt["state"], "cutover_pending")
        self.assertTrue(self.current.is_file())
        # The recorded cutover identity decides; nothing is republished.
        with patch.object(indexer, "_build_index_locked",
                          side_effect=AssertionError("must not rebuild after publication")):
            resumed = migration.migrate_legacy(self.root)
        self.assertEqual(resumed["state"], "published")
        self.assertEqual(migration._identity(self.current), resumed["published_sqlite_identity"])

    def test_current_name_schema_seven_replacement_verifies_and_cleans_up(self):
        self._seed("7", name=self.current)
        original_identity = migration._identity(self.current)
        receipt = self._run()
        self.assertEqual(receipt["state"], "published")
        self.assertNotEqual(migration._identity(self.current), original_identity)
        self._verify_in_child()
        final = migration.cleanup_legacy(self.root)
        self.assertEqual(final["state"], "complete")
        self.assertEqual(final["retired_source_bytes"], 0)
        self.assertEqual(migration._identity(self.current), receipt["published_sqlite_identity"])
        self.assertFalse((self.index / final["work_dir"]).exists())
        self.assertEqual(migration.cleanup_legacy(self.root)["state"], "complete")

    def _check_interruption_before_replace(self, source):
        import indexer
        self._seed("7", name=source)
        with patch.object(migration.os, "replace", side_effect=self._interrupt_cutover_only()):
            with self.assertRaises(KeyboardInterrupt):
                self._run()
        receipt = migration.read_receipt(self.index)
        self.assertEqual(receipt["state"], "cutover_pending")
        self.assertEqual(self.current.exists(), source == self.current)
        with patch.object(indexer, "_build_index_locked",
                          side_effect=AssertionError("must not rebuild a recorded candidate")):
            resumed = migration.migrate_legacy(self.root)
        self.assertEqual(resumed["state"], "published")
        self.assertEqual(migration._file_hash(self.current), receipt["candidate_sha256"])
        self._verify_in_child()
        self.assertEqual(migration.cleanup_legacy(self.root)["state"], "complete")
        self.assertTrue(self.current.is_file())

    def test_device_drift_before_cutover_preserves_authorized_rename(self):
        self._seed("7")
        with patch.object(migration.os, "replace", side_effect=self._interrupt_cutover_only()):
            with self.assertRaises(KeyboardInterrupt):
                self._run()
        receipt = migration.read_receipt(self.index)
        identity = migration._identity
        def drift(path):
            value = identity(path)
            return {**value, "device": value["device"] + 1}
        with patch.object(migration, "_identity", side_effect=drift):
            resumed = migration.migrate_legacy(self.root)
            self.assertEqual(resumed["state"], "published")
            self.assertEqual(migration._file_hash(self.current), receipt["candidate_sha256"])
            self.assertEqual(resumed["root_identity"], receipt["root_identity"])
            self.assertEqual(resumed["published_sqlite_identity"], receipt["published_sqlite_identity"])
            state = migration.detect(self.index)
            self.assertEqual(state["authority_role"], "current")
            self.assertIsNone(state["authority_diagnostic"])
            self.assertIsNone(state["spurious_legacy"])

    def test_interruption_before_replace_publishes_the_recorded_candidate(self):
        self._check_interruption_before_replace(self.legacy)

    def test_current_name_interruption_before_replace_publishes_recorded_candidate(self):
        self._check_interruption_before_replace(self.current)

    def test_current_name_retry_refuses_changed_source_bytes_or_identity(self):
        self._seed("7", name=self.current)
        with patch.object(migration.os, "replace", side_effect=self._interrupt_cutover_only()):
            with self.assertRaises(KeyboardInterrupt):
                self._run()
        original = self.current.read_bytes()
        receipt = migration.read_receipt(self.index)
        # Same inode, different bytes must not be overwritten by the candidate.
        self.current.write_bytes(original + b"changed")
        with self.assertRaisesRegex(migration.MigrationRequired, "storage_cutover_recovery_required"):
            migration.migrate_legacy(self.root)
        self.assertEqual(self.current.read_bytes(), original + b"changed")
        # Identical bytes on a replacement inode are also not the owned source.
        replacement = self.index / "replacement.sqlite"
        replacement.write_bytes(original)
        os.replace(replacement, self.current)
        self.assertNotEqual(migration._identity(self.current), receipt["source_sqlite_identity"])
        with self.assertRaisesRegex(migration.MigrationRequired, "storage_cutover_recovery_required"):
            migration.migrate_legacy(self.root)
        self.assertEqual(self.current.read_bytes(), original)

    def test_a_lost_candidate_refuses_and_names_forward_recovery(self):
        self._seed("7")
        with patch.object(migration.os, "replace", side_effect=self._interrupt_cutover_only()):
            with self.assertRaises(KeyboardInterrupt):
                self._run()
        receipt = migration.read_receipt(self.index)
        staged = migration.staged_database_path(
            migration._staging_index_dir(self.index / receipt["work_dir"]))
        staged.unlink()
        with self.assertRaisesRegex(migration.MigrationRequired, "storage_cutover_recovery_required"):
            migration.migrate_legacy(self.root)
        self.assertTrue(self.legacy.is_file())

    def test_rollback_identities_are_retained_until_verification_and_never_served(self):
        self._seed("7")
        receipt = self._run()
        rollback = migration._staging_index_dir(self.index / receipt["work_dir"]) / migration.STAGING_ROLLBACK_STEM
        self.assertTrue(rollback.is_file())
        self.assertEqual(migration._file_hash(rollback), receipt["rollback"]["sha256"])
        self._verify_in_child()
        self.assertTrue(rollback.is_file())
        migration.cleanup_legacy(self.root)
        self.assertFalse(rollback.exists())

    def test_relocated_byte_identical_package_resumes_the_same_kind_record(self):
        self._seed("7")
        self.ctx.zip_path = self.root / "first.zip"
        self.ctx.zip_path.write_bytes(b"identical archive")
        with patch.dict(os.environ, {migration.CONFIRM_ENV: "1"}), contextlib.redirect_stdout(io.StringIO()):
            self.ctx.storage_migration_protocol = 0
            with self.assertRaises(SystemExit):
                migration.prepare_upgrade(self.ctx)
        original = migration.read_receipt(self.index)
        self.ctx.zip_path.unlink()
        self.ctx.zip_path = self.root / "second.zip"
        self.ctx.zip_path.write_bytes(b"identical archive")
        self.ctx.selected_feature_zip = self.root / "relocated.zip"
        self.ctx.selected_feature_zip.write_bytes(b"identical archive")
        self.ctx.storage_migration_protocol = migration.PROTOCOL_SCHEMA8
        with patch.dict(os.environ, {migration.CONFIRM_ENV: "1"}):
            resumed = migration.prepare_upgrade(self.ctx)
        self.assertEqual(resumed["migration_id"], original["migration_id"])
        self.assertEqual(resumed["pack_sha256"], original["pack_sha256"])
        self.assertEqual(resumed["pack_path"], str(self.ctx.selected_feature_zip))
        self.ctx.zip_path.write_bytes(b"a different archive")
        with self.assertRaisesRegex(migration.MigrationRequired, "storage_pack_changed"):
            migration.prepare_upgrade(self.ctx)

    # --- cleanup ----------------------------------------------------------

    def test_a_staging_refusal_deletes_nothing_and_a_retry_completes(self):
        """The rehearsal's blocking defect, pinned (wave 1xny6 lane L6b).

        Source retirement used to run BEFORE the staging walk, so an unexpected
        entry in the staging index directory refused only AFTER the operator's
        213 MB index had been deleted and recorded as retired -- and the retry
        skipped retirement (``retired_source_bytes`` already present), re-entered
        the same walk and refused again. A permanent block, with a message that
        named no path.

        Every validation now runs before anything irreversible: the refusal
        names the offending path, the source is still present and BYTE-IDENTICAL,
        no staged entry was destroyed on the way to the refusal, the receipt
        records no retirement, and the retry completes.
        """
        self._seed("7")
        receipt = self._run()
        self._verify_in_child()
        staging = migration._staging_index_dir(self.index / receipt["work_dir"])
        before_source = self.legacy.read_bytes()
        before_staging = sorted(q.name for q in staging.iterdir())
        intruder = staging / "not-ours.sqlite"
        intruder.write_bytes(b"unknown staging artifact")
        with self.assertRaises(migration.MigrationRequired) as caught:
            migration.cleanup_legacy(self.root)
        message = str(caught.exception)
        self.assertIn("storage_cleanup_unknown_staging_artifact", message)
        self.assertIn(str(intruder), message, "the refusal must NAME the offending path")
        self.assertTrue(self.legacy.is_file(), "the source was deleted before the refusal")
        self.assertEqual(self.legacy.read_bytes(), before_source)
        self.assertNotIn("retired_source_bytes", migration.read_receipt(self.index),
                         "a refusal must not record a retirement it did not perform")
        self.assertEqual(sorted(q.name for q in staging.iterdir()),
                         sorted([*before_staging, intruder.name]),
                         "the walk destroyed staged entries on its way to the refusal")
        intruder.unlink()
        self.assertEqual(migration.cleanup_legacy(self.root)["state"], "complete")
        self.assertFalse(self.legacy.exists())

    def test_the_staged_build_produces_nothing_the_staging_classifier_refuses(self):
        """Anti-drift oracle for ``_staging_allowlist`` / ``STAGING_DERIVED_DIRNAMES``.

        The rehearsal's defect was not a typo: the staged rebuild runs the REAL
        coordinator, and the coordinator legitimately produced a file the
        hand-maintained allowlist did not cover (``memory-state.sqlite``, created
        by ``index_state_store.memory_invalidate`` whenever the walk touches an
        agent-memory record). The corpus here CARRIES such a record, so the
        staged build takes that branch, and this test fails the moment the build
        starts producing anything the classifier does not accept.
        """
        memory = self.root / "docs" / "agents" / "memory"
        memory.mkdir(parents=True)
        (memory / "mem-fixture.md").write_text(
            "# Fixture memory\n\nA record so the staged build invalidates memory state.\n",
            encoding="utf-8")
        self._seed("7")
        receipt = self._run()
        staging = migration._staging_index_dir(self.index / receipt["work_dir"])
        produced = sorted(q.name for q in staging.iterdir())
        self.assertIn(migration._memory_state_filename(), produced,
                      "precondition: the staged build must have invalidated memory state")
        # The classifier is the oracle: it refuses ANY entry it does not own,
        # so a clean inventory IS the proof that the allowlist covers the build.
        plan = migration._inventory_kind_staging(self.index / receipt["work_dir"])
        classified = {q.name for q in plan["files"]} | {q.name for q in plan["trees"]}
        self.assertTrue(set(produced) <= classified,
                        f"unclassified staged output: {sorted(set(produced) - classified)}")
        self._verify_in_child()
        self.assertEqual(migration.cleanup_legacy(self.root)["state"], "complete")
        self.assertFalse((self.index / receipt["work_dir"]).exists())

    # --- procedure step 6: the retired graph folder's pre-deletion inventory --

    def _graph_folder(self, *names: str) -> Path:
        folder = self.index / migration.GRAPH_OUTPUT_DIRNAME
        folder.mkdir(exist_ok=True)
        for name in names:
            (folder / name).write_bytes(b"retired graph artifact")
        return folder

    def test_the_inventory_preserves_the_whole_folder_for_every_unowned_shape(self):
        """Unknown name, nested directory and link node each retain the folder.

        The SHAPE cases deliberately wear OWNED names as well as unowned ones.
        A classifier that only checked names would pass the unowned variants
        while happily deleting a directory or following a symlink that happens
        to be called ``framework-graph.json`` -- which is the destructive
        direction procedure step 6 exists to prevent.
        """
        folder = self._graph_folder("project-graph.json", "project-graph-clusters.json")
        owned_before = sorted(q.name for q in folder.iterdir())
        cases = (
            ("unknown-file", "operator-notes.txt",
             lambda q: q.write_bytes(b"mine")),
            ("nested-directory-unowned-name", "nested", lambda q: q.mkdir()),
            ("nested-directory-OWNED-name", "framework-graph.json", lambda q: q.mkdir()),
            ("symlink-node-unowned-name", "notes.link",
             lambda q: q.symlink_to(self.root / "src" / "m.py")),
            ("symlink-node-OWNED-name", "framework-graph-state.json",
             lambda q: q.symlink_to(self.root / "src" / "m.py")),
        )
        for label, name, plant in cases:
            with self.subTest(case=label):
                entry = folder / name
                try:
                    plant(entry)
                except (OSError, NotImplementedError) as exc:
                    # Windows accounts without symlink privileges (and hosts
                    # without link support) still exercise all ordinary shapes.
                    unavailable = (isinstance(exc, NotImplementedError)
                                   or getattr(exc, "winerror", None) == 1314
                                   or getattr(exc, "errno", None) in
                                   (errno.EPERM, errno.EACCES, errno.ENOTSUP))
                    if label.startswith("symlink-node-") and unavailable:
                        self.skipTest(f"Native symlink creation unavailable: {exc}")
                    raise
                plan = migration._inventory_retired_graph_directory(self.index)
                self.assertEqual(plan["state"], migration.RETAINED_UNOWNED_CONTENTS, label)
                self.assertEqual(plan["entries"], [name], label)
                self.assertEqual(plan["bytes"], 0, label)
                if entry.is_dir() and not entry.is_symlink():
                    entry.rmdir()
                else:
                    entry.unlink()
                self.assertEqual(sorted(q.name for q in folder.iterdir()), owned_before)
        # With every planted shape gone the same folder classifies as removable,
        # so the retention above is the SHAPE's doing and not a sticky verdict.
        self.assertEqual(
            migration._inventory_retired_graph_directory(self.index)["state"], "removable")

    def test_inventory_symlink_denial_skips_only_link_cases(self):
        case = type(self)(
            "test_the_inventory_preserves_the_whole_folder_for_every_unowned_shape")
        result = unittest.TestResult()
        denied = OSError(errno.EACCES, "A required privilege is not held by the client")
        denied.winerror = 1314
        with patch.object(Path, "symlink_to", side_effect=denied), patch.object(
                migration, "_inventory_retired_graph_directory",
                wraps=migration._inventory_retired_graph_directory) as inventory:
            case.run(result)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.failures, [])
        self.assertEqual(len(result.skipped), 2)
        self.assertTrue(all("Native symlink creation unavailable" in reason
                            for _, reason in result.skipped))
        # Three ordinary shapes and the final removable-folder control ran.
        self.assertEqual(inventory.call_count, 4)

    def test_the_inventory_accepts_owned_names_including_retired_framework_files(self):
        folder = self._graph_folder(
            "project-graph.json", "project-graph-clusters.json",
            "project-graph-state.sqlite", "project-graph-state.sqlite-wal",
            "project-graph-state.sqlite-shm", "project-graph-state.json",
            ".codebase-map.fingerprint", "framework-graph.json",
            "framework-graph-state.json", "framework-graph-clusters.json",
            "project-graph.json.7f3a91.tmp")
        plan = migration._inventory_retired_graph_directory(self.index)
        self.assertEqual(plan["state"], "removable")
        self.assertEqual(sorted(plan["entries"]), sorted(q.name for q in folder.iterdir()))
        self.assertGreater(plan["bytes"], 0)

    def test_an_absent_folder_is_absent_not_removable(self):
        self.assertEqual(
            migration._inventory_retired_graph_directory(self.index)["state"], "absent")

    def test_cleanup_removes_a_wholly_owned_retired_graph_folder(self):
        self._seed("7")
        folder = self._graph_folder(
            "project-graph.json", "project-graph-clusters.json",
            "project-graph-state.sqlite", "project-graph-state.json",
            ".codebase-map.fingerprint", "framework-graph.json",
            "framework-graph-state.json", "framework-graph-clusters.json")
        self._run()
        self._verify_in_child()
        final = migration.cleanup_legacy(self.root)
        self.assertEqual(final["state"], "complete")
        self.assertFalse(folder.exists(), "a normal framework-owned folder is removed completely")
        self.assertEqual(final["graph_directory_cleanup"]["state"], "removed")

    def test_cleanup_retains_an_unowned_retired_graph_folder_and_records_it(self):
        self._seed("7")
        folder = self._graph_folder("project-graph.json")
        (folder / "operator-notes.txt").write_bytes(b"not ours")
        self._run()
        self._verify_in_child()
        with patch("upgrade_wavefoundry._remove_retired_component",
                   side_effect=AssertionError(
                       "the whole-tree primitive was used as the classifier")):
            final = migration.cleanup_legacy(self.root)
        self.assertEqual(final["state"], "complete")
        self.assertEqual(final["graph_directory_cleanup"]["state"],
                         migration.RETAINED_UNOWNED_CONTENTS)
        self.assertEqual(final["graph_directory_cleanup"]["entries"], ["operator-notes.txt"])
        self.assertTrue((folder / "operator-notes.txt").is_file())
        self.assertTrue((folder / "project-graph.json").is_file(),
                        "an unowned entry preserves the WHOLE folder, not only itself")
        # The rest of cleanup still completed: the retired source is gone.
        self.assertFalse(self.legacy.exists())

    def test_a_nonempty_write_ahead_log_preserves_the_retired_source(self):
        self._seed("7")
        self._run()
        self._verify_in_child()
        Path(str(self.legacy) + "-wal").write_bytes(b"committed frames not yet checkpointed")
        with self.assertRaisesRegex(migration.MigrationRequired, "storage_cleanup_live_wal_changed"):
            migration.cleanup_legacy(self.root)
        self.assertTrue(self.legacy.is_file())

    def test_cleanup_refuses_a_retired_source_whose_identity_changed(self):
        self._seed("7")
        self._run()
        self._verify_in_child()
        replaced = self.legacy.with_name("displaced.sqlite")
        self.legacy.rename(replaced)
        shutil.copy2(replaced, self.legacy)
        with self.assertRaisesRegex(migration.MigrationRequired, "storage_cleanup_identity_changed"):
            migration.cleanup_legacy(self.root)
        self.assertTrue(self.legacy.is_file())

    # --- module contract ---------------------------------------------------

    def test_no_filename_literal_survives_in_the_migration_module(self):
        src = (SCRIPTS / "sqlite_storage_migration.py").read_text(encoding="utf-8")
        for name in (index_paths.INDEX_DATABASE_FILENAME,
                     index_paths.LEGACY_INDEX_DATABASE_FILENAME):
            self.assertNotIn(name, src, f"sqlite_storage_migration re-spells {name}")

    def test_the_module_loads_by_path_without_the_scripts_directory_on_syspath(self):
        # Exactly how upgrade_extensions.post_extract loads it from an old
        # runner: by absolute path, with no guarantee about sys.path.
        program = (
            "import importlib.util as u, sys;"
            f"sys.path = [p for p in sys.path if p not in ('', {str(SCRIPTS)!r})];"
            f"spec = u.spec_from_file_location('probe', {str(SCRIPTS / 'sqlite_storage_migration.py')!r});"
            "m = u.module_from_spec(spec); spec.loader.exec_module(m);"
            "print(m.index_paths.RUNTIME_DATABASE_FILENAME)"
        )
        child = subprocess.run([sys.executable, "-B", "-c", program],
                               capture_output=True, text=True, cwd=str(self.root))
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertEqual(child.stdout.strip(), index_paths.RUNTIME_DATABASE_FILENAME)
