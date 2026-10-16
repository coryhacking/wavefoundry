"""20qrt: Windows-shaped directory identities and no-follow scan races."""
import contextlib
import errno
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import lifecycle_lock as locks
import record_paths
from nt_metadata_support import nt_stat


class ZeroIdentityEntry:
    def __init__(self, entry):
        self.entry = entry
        self.path, self.name = entry.path, entry.name
    def is_symlink(self):
        return self.entry.is_symlink()
    def is_dir(self, **kwargs):
        return self.entry.is_dir(**kwargs)
    def stat(self, **kwargs):
        return nt_stat(self.entry.stat(**kwargs), reparse=False, zero_identity=True)


class WindowsLifecycleScanTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        roots = record_paths.load_record_roots(self.root)
        self.waves = roots.waves
        self.plans = roots.plans
        self.plans.mkdir(parents=True)
        for name in ('a', 'b', 'c'):
            (self.waves / name).mkdir(parents=True)
        self.lock = self.root / '.wavefoundry/lifecycle-mutation.lock'
        self.lock.parent.mkdir()
        self.lock.write_text('{}')
        self.listed = []
        self.fresh = []

    @contextlib.contextmanager
    def windows(self, *, zero_fresh=False, fail=None, replacement=None, vanished=None, listing_error=None, fail_errno=errno.EACCES):
        real_stat, real_scan, real_realpath = os.stat, os.scandir, os.path.realpath
        def fresh(path, *args, **kwargs):
            candidate = Path(path) if not isinstance(path, int) else None
            if kwargs.get('follow_symlinks') is False:
                self.fresh.append(candidate)
                if candidate == fail:
                    raise OSError(fail_errno, 'injected')
                if candidate == vanished:
                    raise FileNotFoundError(str(candidate))
                if replacement and candidate == replacement[0]:
                    info = nt_stat(real_stat(path), 0x20001234)
                    info.st_mode = stat.S_IFDIR
                    return info
            info = real_stat(path, *args, **kwargs)
            return nt_stat(info, reparse=False, zero_identity=True) if zero_fresh and stat.S_ISDIR(info.st_mode) else info
        @contextlib.contextmanager
        def scan(path):
            candidate = Path(path)
            self.listed.append(candidate)
            if candidate == listing_error:
                raise PermissionError(errno.EACCES, 'injected')
            with real_scan(path) as entries:
                yield [ZeroIdentityEntry(entry) for entry in entries]
        def realpath(path, *args, **kwargs):
            if replacement and Path(path) == replacement[0]:
                return str(replacement[1])
            return real_realpath(path, *args, **kwargs)
        facade = SimpleNamespace(**{name: getattr(os, name) for name in dir(os)})
        facade.name, facade.stat, facade.scandir = 'nt', fresh, scan
        facade.path = SimpleNamespace(**{name: getattr(os.path, name) for name in dir(os.path)})
        facade.path.realpath = realpath
        with patch.object(locks, 'os', facade):
            yield

    def scan(self):
        locks._refuse_lock_links(self.root, SimpleNamespace(handle=None))

    def test_zero_direntry_metadata_visits_later_lock_alias(self):
        alias = self.waves / 'c/held.md'
        alias.symlink_to(self.lock)
        with self.windows(), self.assertRaises(locks.LifecycleLockLinkRefused) as caught:
            self.scan()
        self.assertEqual(caught.exception.cause, 'lock_link')
        self.assertIn(self.waves / 'c', self.fresh)

    def test_zero_fresh_keys_keep_sibling_and_top_directories_distinct(self):
        later = self.plans / 'later'
        later.mkdir()
        (later / 'held.md').symlink_to(self.lock)
        with self.windows(zero_fresh=True), self.assertRaises(locks.LifecycleLockLinkRefused) as caught:
            self.scan()
        self.assertEqual(caught.exception.cause, 'lock_link')
        self.assertIn(later, self.listed)

    def test_fresh_nofollow_reclassifies_replacement_before_traversal(self):
        with tempfile.TemporaryDirectory() as outside:
            changed = self.waves / 'b'
            with self.windows(replacement=(changed, Path(outside))), self.assertRaises(locks.LifecycleLockLinkRefused) as caught:
                self.scan()
            self.assertEqual(caught.exception.cause, 'outside_link')
            self.assertNotIn(changed, self.listed)

    def test_fresh_errors_refuse_and_disappearance_skips_only_vanished_entry(self):
        changed = self.waves / 'b'
        for failure in (errno.EACCES, errno.EIO):
            with self.subTest(errno=failure), self.windows(fail=changed, fail_errno=failure), \
                    self.assertRaises(locks.LifecycleLockLinkRefused) as caught:
                self.scan()
            self.assertEqual(caught.exception.cause, 'link_scan_unreadable')
            self.assertNotIn(str(self.root), str(caught.exception))
        self.listed.clear()
        with self.windows(vanished=changed):
            self.scan()
        self.assertNotIn(changed, self.listed)
        self.assertIn(self.waves / 'c', self.listed)

    def test_windows_directory_listing_error_refuses(self):
        with self.windows(listing_error=self.waves / 'a'), self.assertRaises(locks.LifecycleLockLinkRefused) as caught:
            self.scan()
        self.assertEqual(caught.exception.cause, 'link_scan_unreadable')

    def test_zero_identity_link_subtree_still_counts_and_real_tree_is_not_capped(self):
        bulk = self.root / 'vendor/bulk'
        bulk.mkdir(parents=True)
        for index in range(6):
            directory = bulk / str(index)
            directory.mkdir()
            for leaf in range(4):
                (directory / str(leaf)).write_text('')
        alias = self.waves / 'a/vendor'
        alias.symlink_to(bulk, target_is_directory=True)
        for zero in (False, True):
            with self.subTest(zero_fresh=zero), self.windows(zero_fresh=zero), \
                    patch.object(locks, '_LINK_SCAN_ENTRY_LIMIT', 12), \
                    self.assertRaises(locks.LifecycleLockLinkRefused) as caught:
                self.scan()
            self.assertEqual(caught.exception.cause, 'link_scan_limit')
        alias.unlink()
        real = self.waves / 'real'
        real.mkdir()
        for index in range(30):
            (real / str(index)).write_text('')
        with self.windows(zero_fresh=True), patch.object(locks, '_LINK_SCAN_ENTRY_LIMIT', 1):
            self.scan()

    def test_repeated_link_targets_and_cycles_terminate_with_both_key_types(self):
        target = self.root / 'vendor/cycle'
        target.mkdir(parents=True)
        (target / 'again').symlink_to(target, target_is_directory=True)
        (self.waves / 'a/one').symlink_to(target, target_is_directory=True)
        (self.waves / 'b/two').symlink_to(target, target_is_directory=True)
        for zero in (False, True):
            self.listed.clear()
            with self.subTest(zero_fresh=zero), self.windows(zero_fresh=zero):
                self.scan()
            reached = [path for path in self.listed if os.path.realpath(path) == str(target)]
            self.assertEqual(len(reached), 1)


    def test_posix_regular_entries_keep_the_stat_free_fast_path(self):
        ordinary = self.waves / 'a/ordinary.md'
        ordinary.write_text('ordinary')
        real_scan = os.scandir
        stat_calls = []
        class Entry:
            def __init__(self, entry):
                self.entry = entry
                self.path, self.name = entry.path, entry.name
            def is_symlink(self):
                return self.entry.is_symlink()
            def is_dir(self, **kwargs):
                return self.entry.is_dir(**kwargs)
            def stat(self, **kwargs):
                stat_calls.append(Path(self.path))
                return self.entry.stat(**kwargs)
        @contextlib.contextmanager
        def scan(path):
            with real_scan(path) as entries:
                yield [Entry(entry) for entry in entries]
        facade = SimpleNamespace(**{name: getattr(os, name) for name in dir(os)})
        facade.name, facade.scandir = 'posix', scan
        with patch.object(locks, 'os', facade):
            self.scan()
        self.assertNotIn(ordinary, stat_calls)
        self.assertIn(self.waves / 'a', stat_calls)

    def test_zero_identity_later_outside_directory_link_is_refused(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.waves / 'c/outside').symlink_to(outside, target_is_directory=True)
            for zero in (False, True):
                with self.subTest(zero_fresh=zero), self.windows(zero_fresh=zero), \
                        self.assertRaises(locks.LifecycleLockLinkRefused) as caught:
                    self.scan()
                self.assertEqual(caught.exception.cause, 'outside_link')
