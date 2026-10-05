"""Wave 1zrak (1zraj): guards that relied on ``pathlib`` predicates raising.

From Python 3.14, ``Path.exists``, ``is_symlink``, ``is_file`` and ``is_dir``
return ``False`` on any ``OSError`` instead of raising (3.11 to 3.13 raised
every error other than not-found). Each fixed site now determines path state
with ``os.lstat`` or ``os.stat`` under one errno rule: ``FileNotFoundError``
and ``NotADirectoryError`` mean absent, every other ``OSError`` refuses or
reports. ``upgrade_wavefoundry._retired_sidecar_path_error`` is pinned in
``test_upgrade_wavefoundry.py`` through its backstop caller.

Each fix has two pins:

* a mode-0 pin, which goes red on Python 3.14 against the unfixed code. It
  skips on native Windows (``chmod 0`` does not deny traversal there) and
  under root (which ignores mode 0); symlink-dependent mode-0 pins also skip
  when the host refuses ``os.symlink`` for lack of privilege;
* a platform-independent pin that patches the stat primitive the fix uses
  (``os.lstat``, or ``os.stat`` where the replaced predicate followed links)
  to raise ``PermissionError`` for the guarded path. It runs on Windows.
"""
from __future__ import annotations

import contextlib
import errno
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import index_paths  # noqa: E402
import memory_backfill  # noqa: E402
import memory_records  # noqa: E402
import record_paths  # noqa: E402
import review_policy_upgrade  # noqa: E402
import setup_index  # noqa: E402
import setup_wavefoundry  # noqa: E402
import upgrade_lib  # noqa: E402
import upgrade_wavefoundry  # noqa: E402


def _skip_unless_mode_zero_denies(test: unittest.TestCase) -> None:
    if os.name == "nt":
        test.skipTest("chmod 0 does not deny directory traversal on Windows; the patched-stat pin covers it")
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        test.skipTest("root ignores mode 0")


@contextlib.contextmanager
def _mode_zero(path: Path):
    os.chmod(path, 0)
    try:
        yield
    finally:
        os.chmod(path, 0o755)


def _symlink_or_skip(test: unittest.TestCase, link: Path, target: Path) -> None:
    try:
        link.symlink_to(target)
    except OSError as exc:
        test.skipTest(f"symlinks unavailable without privilege: {exc}")


@contextlib.contextmanager
def _denied(primitive: str, *paths: Path):
    """Patch ``os.<primitive>`` to raise ``PermissionError`` for ``paths``.

    Both spellings are computed before the patch (``realpath`` itself calls
    ``os.lstat``); every other path reaches the real primitive. A patched
    ``os.stat`` denies only the link-following form: Python 3.13's
    ``Path.lstat`` calls ``os.stat(..., follow_symlinks=False)``.
    """

    real = getattr(os, primitive)
    denied = {os.path.abspath(p) for p in paths} | {os.path.realpath(p) for p in paths}

    def fake(path, *args, **kwargs):
        following = kwargs.get("follow_symlinks", True)
        if (following and not isinstance(path, int)
                and os.path.abspath(os.fspath(path)) in denied):
            raise PermissionError(errno.EACCES, "Permission denied", os.fspath(path))
        return real(path, *args, **kwargs)

    with patch.object(os, primitive, fake):
        yield


class _TempRoot(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()


class IndexDatabasePresenceTests(_TempRoot):
    """``index_paths._present`` reads an undecidable probe as present."""

    def setUp(self):
        super().setUp()
        self.index_dir = self.root / "index"
        self.index_dir.mkdir()
        index_paths.index_database_path(self.index_dir).write_bytes(b"db")

    def test_untraversable_index_dir_is_not_absent(self):
        _skip_unless_mode_zero_denies(self)
        with _mode_zero(self.index_dir):
            state = index_paths.resolve_index_database(self.index_dir)["state"]
        self.assertEqual(state, index_paths.BOTH)

    def test_denied_stat_reads_present_on_every_platform(self):
        with _denied("stat", index_paths.index_database_path(self.index_dir)):
            state = index_paths.resolve_index_database(self.index_dir)["state"]
        self.assertEqual(state, index_paths.CURRENT)


class UpgradeLockPresenceTests(_TempRoot):
    """``upgrade_lib.read_upgrade_lock`` treats an undetermined lock as present."""

    def setUp(self):
        super().setUp()
        upgrade_lib.write_upgrade_lock(self.root, "1.0.0", "1.1.0")

    def test_untraversable_lock_parent_reads_as_locked(self):
        _skip_unless_mode_zero_denies(self)
        with _mode_zero(self.root / ".wavefoundry"):
            lock = upgrade_lib.read_upgrade_lock(self.root)
        self.assertEqual(lock, {})

    def test_denied_stat_reads_as_locked_on_every_platform(self):
        with _denied("stat", upgrade_lib.upgrade_lock_path(self.root)):
            lock = upgrade_lib.read_upgrade_lock(self.root)
        self.assertEqual(lock, {})

    def test_absent_lock_still_reads_as_none(self):
        upgrade_lib.upgrade_lock_path(self.root).unlink()
        self.assertIsNone(upgrade_lib.read_upgrade_lock(self.root))

    # Delivery repair DEL-R1: an uninspectable lock is neither a foreign, a
    # live nor a stale upgrade. Callers refuse with its own path-free cause
    # and recovery, never clear it, and never rewrite it.

    def _assert_unreadable_message(self, message: str) -> None:
        self.assertIn(".wavefoundry/upgrade-in-progress.json cannot be inspected (Permission denied)", message)
        self.assertIn("remove it if no upgrade is running", message)
        self.assertNotIn("foreign", message)
        for spelling in {str(self.root), os.path.realpath(self.root)}:
            self.assertNotIn(spelling, message)

    def _setup_refusal(self) -> str:
        import setup_reconciliation
        import sqlite_storage_migration

        with patch.object(sqlite_storage_migration, "discover_hosts", return_value=([], [])), \
             self.assertRaises(sqlite_storage_migration.MigrationRequired) as raised:
            with setup_reconciliation.session(self.root, []):
                pass
        return str(raised.exception)

    def test_unreadable_lock_refuses_setup_with_its_own_cause(self):
        _skip_unless_mode_zero_denies(self)
        lock = upgrade_lib.upgrade_lock_path(self.root)
        os.chmod(lock, 0)
        try:
            message = self._setup_refusal()
        finally:
            os.chmod(lock, 0o644)
        self.assertIn("storage_setup_upgrade_lock_unreadable", message)
        self._assert_unreadable_message(message)

    def test_denied_lock_stat_refuses_setup_on_every_platform(self):
        with _denied("stat", upgrade_lib.upgrade_lock_path(self.root)):
            message = self._setup_refusal()
        self.assertIn("storage_setup_upgrade_lock_unreadable", message)
        self._assert_unreadable_message(message)

    def test_unreadable_lock_is_never_stale_nor_rewritten(self):
        _skip_unless_mode_zero_denies(self)
        lock = upgrade_lib.upgrade_lock_path(self.root)
        before = lock.read_bytes()
        os.chmod(lock, 0)
        try:
            stale = upgrade_lib.is_lock_stale(self.root)
            updated = upgrade_lib.update_upgrade_lock(self.root, failed_phase="x")
        finally:
            os.chmod(lock, 0o644)
        self.assertFalse(stale)
        self.assertFalse(updated)
        self.assertEqual(lock.read_bytes(), before)

    def test_denied_lock_stat_is_never_stale_nor_rewritten_on_every_platform(self):
        lock = upgrade_lib.upgrade_lock_path(self.root)
        before = lock.read_bytes()
        with _denied("stat", lock):
            stale = upgrade_lib.is_lock_stale(self.root)
            updated = upgrade_lib.update_upgrade_lock(self.root, failed_phase="x")
            cause = upgrade_lib.upgrade_lock_unreadable_cause(self.root)
        self.assertFalse(stale)
        self.assertFalse(updated)
        self.assertEqual(cause, "Permission denied")
        self.assertEqual(lock.read_bytes(), before)

    def test_unreadable_lock_refuses_upgrade_preflight_path_free(self):
        _skip_unless_mode_zero_denies(self)
        lock = upgrade_lib.upgrade_lock_path(self.root)
        err = io.StringIO()
        os.chmod(lock, 0)
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()), \
                 self.assertRaises(SystemExit) as raised:
                upgrade_wavefoundry.phase_preflight(self.root, True)
        finally:
            os.chmod(lock, 0o644)
        self.assertEqual(raised.exception.code, 3)
        self._assert_unreadable_message(err.getvalue())
        self.assertTrue(lock.exists())

    def _dry_run_output(self) -> str:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            upgrade_wavefoundry.phase_dry_run(self.root)
        return out.getvalue()

    def _assert_dry_run_names_unreadable_lock(self, output: str) -> None:
        self.assertNotIn("Upgrade already in progress", output)
        self.assertNotIn("Stale upgrade lock detected", output)
        lines = [line for line in output.splitlines() if "cannot be inspected" in line]
        self.assertEqual(len(lines), 1, output)
        self._assert_unreadable_message(lines[0])

    def test_unreadable_lock_is_named_by_the_dry_run(self):
        _skip_unless_mode_zero_denies(self)
        lock = upgrade_lib.upgrade_lock_path(self.root)
        os.chmod(lock, 0)
        try:
            output = self._dry_run_output()
        finally:
            os.chmod(lock, 0o644)
        self._assert_dry_run_names_unreadable_lock(output)

    def test_denied_lock_stat_is_named_by_the_dry_run_on_every_platform(self):
        with _denied("stat", upgrade_lib.upgrade_lock_path(self.root)):
            output = self._dry_run_output()
        self._assert_dry_run_names_unreadable_lock(output)

    def test_corrupt_lock_keeps_its_stale_reading(self):
        lock = upgrade_lib.upgrade_lock_path(self.root)
        lock.write_text("{not json", encoding="utf-8")
        self.assertEqual(upgrade_lib.read_upgrade_lock(self.root), {})
        self.assertIsNone(upgrade_lib.upgrade_lock_unreadable_cause(self.root))
        self.assertTrue(upgrade_lib.is_lock_stale(self.root))


class HistoricalMemoryWavesRootTests(_TempRoot):
    """``memory_backfill._canonical_waves_dir`` refuses an undetermined root."""

    def setUp(self):
        super().setUp()
        self.waves = record_paths.load_record_roots(self.root).waves
        self.waves.mkdir(parents=True)

    def test_untraversable_waves_parent_refuses(self):
        _skip_unless_mode_zero_denies(self)
        if self.waves.parent == self.root:
            self.skipTest("waves root has no in-repository parent to lock")
        with _mode_zero(self.waves.parent), self.assertRaises(PermissionError):
            memory_backfill._canonical_waves_dir(self.root)

    def test_denied_lstat_refuses_on_every_platform(self):
        with _denied("lstat", self.waves), self.assertRaises(PermissionError):
            memory_backfill._canonical_waves_dir(self.root)

    def test_absent_waves_root_still_reads_as_none(self):
        self.waves.rmdir()
        self.assertIsNone(memory_backfill._canonical_waves_dir(self.root))


class PurgeSourcePresenceTests(_TempRoot):
    """``resolve_purge_memory_source`` cannot hide a body it cannot inspect."""

    MEMORY_ID = "1zraa-mem pin-fixture"

    def setUp(self):
        super().setUp()
        self.memory_dir = self.root / memory_records.MEMORY_DIR
        self.archive_dir = self.root / memory_records.MEMORY_ARCHIVE_DIR
        self.archive_dir.mkdir(parents=True)
        (self.memory_dir / f"{self.MEMORY_ID}.md").write_text("active body\n", encoding="utf-8")
        self.archived = self.archive_dir / f"{self.MEMORY_ID}.md"
        self.archived.write_text("archived body\n", encoding="utf-8")

    def test_untraversable_archive_body_refuses(self):
        _skip_unless_mode_zero_denies(self)
        with _mode_zero(self.archive_dir), self.assertRaises(PermissionError):
            memory_records.resolve_purge_memory_source(self.root, self.MEMORY_ID)

    def test_denied_lstat_refuses_on_every_platform(self):
        with _denied("lstat", self.archived), self.assertRaises(PermissionError):
            memory_records.resolve_purge_memory_source(self.root, self.MEMORY_ID)

    def test_two_visible_bodies_still_refuse_to_guess(self):
        with self.assertRaisesRegex(ValueError, "refusing to guess"):
            memory_records.resolve_purge_memory_source(self.root, self.MEMORY_ID)


class _ConfigSymlinkFixture(_TempRoot):
    """``docs/workflow-config.json`` as a symlink whose target cannot be inspected."""

    def setUp(self):
        super().setUp()
        self.docs = self.root / "docs"
        self.docs.mkdir()
        self.cfg = self.docs / "workflow-config.json"

    def _locked_symlinked_config(self) -> Path:
        _skip_unless_mode_zero_denies(self)
        locked = self.root / "outside" / "locked"
        locked.mkdir(parents=True)
        target = locked / "workflow-config.json"
        target.write_text(json.dumps({"operator": "keep"}), encoding="utf-8")
        _symlink_or_skip(self, self.cfg, target)
        return locked


class ReviewPolicyPreflightTests(_ConfigSymlinkFixture):
    """``plan_review_policy_upgrade`` refuses a config it cannot inspect."""

    def test_uninspectable_config_refuses_preflight(self):
        locked = self._locked_symlinked_config()
        with _mode_zero(locked), self.assertRaisesRegex(ValueError, "cannot preflight workflow config"):
            review_policy_upgrade.plan_review_policy_upgrade(self.root)
        self.assertTrue(self.cfg.is_symlink())

    def test_denied_stat_refuses_preflight_on_every_platform(self):
        self.cfg.write_text("{}", encoding="utf-8")
        with _denied("stat", self.cfg), self.assertRaisesRegex(ValueError, "cannot preflight workflow config"):
            review_policy_upgrade.plan_review_policy_upgrade(self.root)


class LifecyclePolicyMaterializeTests(_ConfigSymlinkFixture):
    """``materialize_lifecycle_policy`` never overwrites a config it cannot inspect."""

    def test_uninspectable_config_refuses_without_writing(self):
        locked = self._locked_symlinked_config()
        with _mode_zero(locked), self.assertRaisesRegex(RuntimeError, "could not be inspected"):
            upgrade_wavefoundry.materialize_lifecycle_policy(self.root)
        self.assertTrue(self.cfg.is_symlink())

    def test_denied_stat_refuses_path_free_on_every_platform(self):
        self.cfg.write_text("{}", encoding="utf-8")
        with _denied("stat", self.cfg), self.assertRaises(RuntimeError) as raised:
            upgrade_wavefoundry.materialize_lifecycle_policy(self.root)
        message = str(raised.exception)
        self.assertIn("docs/workflow-config.json could not be inspected (Permission denied)", message)
        self.assertNotIn(str(self.root), message)
        self.assertEqual(self.cfg.read_text(encoding="utf-8"), "{}")

    # Delivery repair DEL-R2: the parse and type refusals are path-free too.

    def _refusal(self, text: str) -> str:
        self.cfg.write_text(text, encoding="utf-8")
        with self.assertRaises(RuntimeError) as raised:
            upgrade_wavefoundry.materialize_lifecycle_policy(self.root)
        self.assertEqual(self.cfg.read_text(encoding="utf-8"), text)
        message = str(raised.exception)
        for spelling in {str(self.root), os.path.realpath(self.root)}:
            self.assertNotIn(spelling, message)
        self.assertIn("re-run the upgrade", message)
        return message

    def test_unparseable_config_refusal_is_path_free(self):
        message = self._refusal("{not json")
        self.assertIn("docs/workflow-config.json exists but could not be parsed", message)
        self.assertIn("at line 1 column 2", message)

    def test_non_utf8_config_refusal_is_path_free(self):
        payload = b'{"a": "\xff"}'
        self.cfg.write_bytes(payload)
        with self.assertRaises(RuntimeError) as raised:
            upgrade_wavefoundry.materialize_lifecycle_policy(self.root)
        message = str(raised.exception)
        self.assertIn("docs/workflow-config.json exists but is not valid UTF-8 (byte 7)", message)
        self.assertIn("re-run the upgrade", message)
        self.assertNotIn(str(self.root), message)
        self.assertEqual(self.cfg.read_bytes(), payload)

    def test_non_object_config_refusal_is_path_free(self):
        message = self._refusal("[]")
        self.assertIn("docs/workflow-config.json must contain a JSON object at the top level, not list", message)


class WorkflowDefaultsProvisionTests(_ConfigSymlinkFixture):
    """``_provision_workflow_defaults_if_absent`` refuses a config it cannot inspect."""

    def setUp(self):
        super().setUp()
        (self.root / ".wavefoundry" / "framework").mkdir(parents=True)

    def _provision(self) -> tuple[int, str]:
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            rc = setup_wavefoundry._provision_workflow_defaults_if_absent(self.root)
        return rc, err.getvalue()

    def test_uninspectable_config_refuses_without_writing(self):
        locked = self._locked_symlinked_config()
        with _mode_zero(locked):
            rc, err = self._provision()
        self.assertEqual(rc, 1, err)
        self.assertIn("could not be provisioned", err)
        self.assertTrue(self.cfg.is_symlink())

    def test_denied_stat_refuses_on_every_platform(self):
        self.cfg.write_text("{}", encoding="utf-8")
        with _denied("stat", self.cfg):
            rc, err = self._provision()
        self.assertEqual(rc, 1, err)
        self.assertEqual(self.cfg.read_text(encoding="utf-8"), "{}")


class PackScanLocationTests(_TempRoot):
    """``_scan_dir_entries`` records an inaccessible location, never skips it silently."""

    def setUp(self):
        super().setUp()
        self.parent = self.root / "locked"
        self.search_dir = self.parent / "downloads"
        self.search_dir.mkdir(parents=True)

    def _scan(self):
        with patch.object(upgrade_wavefoundry, "_record_skipped_scan_location") as recorded:
            entries = upgrade_wavefoundry._scan_dir_entries(self.search_dir)
        return entries, recorded

    def test_untraversable_location_is_recorded(self):
        _skip_unless_mode_zero_denies(self)
        with _mode_zero(self.parent):
            entries, recorded = self._scan()
        self.assertIsNone(entries)
        recorded.assert_called_once()

    def test_denied_stat_is_recorded_on_every_platform(self):
        with _denied("stat", self.search_dir):
            entries, recorded = self._scan()
        self.assertIsNone(entries)
        recorded.assert_called_once()

    def test_absent_location_is_skipped_silently(self):
        self.search_dir.rmdir()
        entries, recorded = self._scan()
        self.assertIsNone(entries)
        recorded.assert_not_called()


class LegacyMetaJsonReportTests(_TempRoot):
    """``_remove_legacy_meta_json`` stays LOUD when it cannot inspect the file."""

    def setUp(self):
        super().setUp()
        import indexer

        self.indexer = indexer
        self.index_dir = self.root / "index"
        self.index_dir.mkdir()
        self.meta = self.index_dir / indexer.META_JSON
        self.meta.write_text("{}", encoding="utf-8")

    def _remove(self) -> tuple[bool, str]:
        err = io.StringIO()
        with patch.object(self.indexer, "_get_index_state_store", return_value=None), \
             contextlib.redirect_stderr(err):
            removed = self.indexer._remove_legacy_meta_json(self.index_dir)
        return removed, err.getvalue()

    def test_untraversable_index_dir_warns(self):
        _skip_unless_mode_zero_denies(self)
        with _mode_zero(self.index_dir):
            removed, err = self._remove()
        self.assertFalse(removed)
        self.assertIn("legacy meta.json could not be removed", err)

    def test_denied_stat_warns_on_every_platform(self):
        with _denied("stat", self.meta):
            removed, err = self._remove()
        self.assertFalse(removed)
        self.assertIn("legacy meta.json could not be removed", err)
        self.assertTrue(self.meta.exists())


class ModelCacheCorruptionTests(_TempRoot):
    """``_model_cache_corruption_reason`` reports an unreadable snapshot."""

    def setUp(self):
        super().setUp()
        self.model_dir = self.root / "models--org--model"
        self.snapshot = self.model_dir / "snapshots" / "abc"
        onnx = self.snapshot / "onnx"
        onnx.mkdir(parents=True)
        (onnx / "model.onnx").write_bytes(b"onnx")

    def _reason(self):
        with patch.object(setup_index, "_model_cache_dir_candidates", return_value=(self.model_dir,)):
            return setup_index._model_cache_corruption_reason("org/model")

    def test_healthy_cache_has_no_reason(self):
        self.assertIsNone(self._reason())

    def test_untraversable_snapshot_is_reported(self):
        _skip_unless_mode_zero_denies(self)
        with _mode_zero(self.snapshot):
            reason = self._reason()
        self.assertEqual(reason, "snapshot onnx directory unreadable")

    def test_denied_stat_is_reported_on_every_platform(self):
        with _denied("stat", self.snapshot / "onnx"):
            reason = self._reason()
        self.assertEqual(reason, "snapshot onnx directory unreadable")


if __name__ == "__main__":
    unittest.main()
