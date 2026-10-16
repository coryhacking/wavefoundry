"""20tpn: bounded layout refusals and safe uncached rename-failure outcomes."""
import concurrent.futures
import contextlib
import errno
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import bytecode_cache as cache
import lifecycle_lock as locks
import record_paths
import render_platform_surfaces as surfaces


@unittest.skipIf(os.name == 'nt', 'POSIX public-lock and directory-symlink fixtures')
class LayoutLinkTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        roots = record_paths.load_record_roots(self.root)
        self.wave = roots.waves / '1abcd wave'
        self.wave.mkdir(parents=True)
        roots.plans.mkdir(parents=True, exist_ok=True)

    def hold(self):
        with locks.lifecycle_mutation_lock(self.root):
            return 'body reached'

    def test_public_root_alias_refuses_before_checkout_descent(self):
        (self.root / 'docs/site').symlink_to('..', target_is_directory=True)
        original = os.scandir
        listed = []
        def scandir(path):
            listed.append(Path(path))
            return original(path)
        with patch.object(os, 'scandir', side_effect=scandir), self.assertRaises(locks.LifecycleLockLinkRefused) as caught:
            self.hold()
        self.assertEqual(caught.exception.cause, 'scan_ancestor_link')
        self.assertNotIn(self.root / 'docs/site', listed)
        self.assertNotIn(str(self.root), str(caught.exception))
        self.assertLess(len(str(caught.exception)), 512)
        self.assertIn('replace', str(caught.exception))

    def test_root_alias_diagnostic_escapes_and_bounds_untrusted_link_name(self):
        link = self.root / 'docs' / ('site\n\x1b[31m' + 'x' * 180)
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(locks.LifecycleLockLinkRefused) as caught:
            self.hold()
        message = str(caught.exception)
        self.assertLess(len(message), 512)
        self.assertNotIn('\x1b', message)
        self.assertEqual(len(message.splitlines()), 1)
        self.assertNotIn(str(self.root), message)

    def test_public_scan_top_ancestor_refuses_even_if_already_visited(self):
        (self.wave / 'up').symlink_to(self.root / 'docs', target_is_directory=True)
        with self.assertRaises(locks.LifecycleLockLinkRefused) as caught:
            self.hold()
        self.assertEqual(caught.exception.cause, 'scan_ancestor_link')

    def test_root_alias_never_accepts_a_hidden_lock_alias(self):
        (self.root / 'docs/site').symlink_to(self.root, target_is_directory=True)
        hidden = self.root / 'src/hidden'
        hidden.mkdir(parents=True)
        (hidden / 'notes.md').symlink_to(self.root / locks.LIFECYCLE_MUTATION_LOCK_REL)
        with self.assertRaises(locks.LifecycleLockLinkRefused) as caught:
            self.hold()
        self.assertEqual(caught.exception.cause, 'scan_ancestor_link')

    def test_cache_lock_alias_coverage_and_safe_link_budget_remain(self):
        hidden = self.root / '.wavefoundry/cache/pycache'
        hidden.mkdir(parents=True)
        alias = hidden / 'notes.pyc'
        alias.symlink_to(self.root / locks.LIFECYCLE_MUTATION_LOCK_REL)
        with self.assertRaises(locks.LifecycleLockLinkRefused) as caught:
            self.hold()
        self.assertEqual(caught.exception.cause, 'lock_link')
        alias.unlink()
        safe = self.root / 'src/safe'
        safe.mkdir(parents=True)
        (safe / 'ordinary.md').write_text('safe')
        (self.wave / 'safe').symlink_to(safe, target_is_directory=True)
        self.assertEqual(self.hold(), 'body reached')
        for number in range(10):
            (safe / str(number)).write_text('')
        with patch.object(locks, '_LINK_SCAN_ENTRY_LIMIT', 5), self.assertRaises(locks.LifecycleLockLinkRefused) as caught:
            self.hold()
        self.assertEqual(caught.exception.cause, 'link_scan_limit')

    def test_renderer_keeps_lexical_parent_link_refusal(self):
        actual = self.root / 'surface-storage'
        actual.mkdir()
        (self.root / '.claude').symlink_to(actual, target_is_directory=True)
        target = actual / 'settings.json'
        target.write_bytes(b'operator settings')
        with self.assertRaisesRegex(RuntimeError, 'refused to write .claude/settings.json'):
            surfaces.write_text(self.root / '.claude/settings.json', 'replaced', root=self.root)
        self.assertEqual(target.read_bytes(), b'operator settings')
        self.assertTrue((self.root / '.claude').is_symlink())


class CacheRenameFailureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.scripts = self.root / '.wavefoundry/framework/scripts'
        self.scripts.mkdir(parents=True)
        self.version = self.scripts.parent / 'VERSION'
        self.version.write_bytes(b'new generation')
        self.cache_root = self.root / '.wavefoundry/cache'
        self.prefix = self.cache_root / 'pycache'
        self.prefix.mkdir(parents=True)
        (self.prefix / cache.STAMP_NAME).write_bytes(b'old generation')
        (self.prefix / 'old.pyc').write_bytes(b'old bytecode')
        self.before = self.snapshot()
        self.original_prefix, self.original_flag = sys.pycache_prefix, sys.dont_write_bytecode
        self.addCleanup(setattr, sys, 'pycache_prefix', self.original_prefix)
        self.addCleanup(setattr, sys, 'dont_write_bytecode', self.original_flag)
        self.addCleanup(setattr, cache, '_configured', cache._UNSET)
        cache._configured = cache._UNSET
        # New code resets only diagnostic state here; no caching flag bypass.
        if hasattr(cache, '_flush_warning_reported'):
            cache._flush_warning_reported = False
        self.addCleanup(lambda: setattr(cache, '_flush_warning_reported', False))

    def snapshot(self):
        return {str(path.relative_to(self.cache_root)): path.read_bytes()
                for path in self.cache_root.rglob('*') if path.is_file()}

    def test_rename_failures_preserve_old_generation_and_report_once(self):
        failure_type = type('Unsafe\n\x1b[31m' + 'x' * 2000, (OSError,), {})
        failure = failure_type(errno.EXDEV, 'untrusted\n\x1b[31m' + 'x' * 2000)
        sys.pycache_prefix = str(self.prefix)
        error = io.StringIO()
        with patch.object(cache, '_disabled', return_value=False), \
                patch.object(cache.os, 'rename', side_effect=failure), \
                patch.object(cache, '_remove_tree_no_follow', side_effect=AssertionError('in-place deletion')), \
                contextlib.redirect_stderr(error):
            self.assertIsNone(cache.configure(scripts_dir=self.scripts))
            self.assertIsNone(cache.configure(scripts_dir=self.scripts))
            self.assertFalse(cache._flush_if_stale(self.cache_root, self.prefix, self.version))
        self.assertIsNone(sys.pycache_prefix)
        self.assertTrue(sys.dont_write_bytecode)
        self.assertEqual(self.snapshot(), self.before)
        lines = error.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertIn('EXDEV', lines[0])
        self.assertIn('disabled', lines[0])
        self.assertLess(len(lines[0]), 512)
        self.assertNotIn('\x1b', lines[0])
        self.assertNotIn(str(self.root), lines[0])

    def test_concurrent_failures_do_not_adopt_stamp_or_repeat_diagnostic(self):
        error = io.StringIO()
        with patch.object(cache.os, 'rename', side_effect=PermissionError(errno.EACCES, 'denied')), \
                contextlib.redirect_stderr(error), concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda _: cache._flush_if_stale(self.cache_root, self.prefix, self.version), range(12)))
        self.assertEqual(results, [False] * 12)
        self.assertEqual(self.snapshot(), self.before)
        self.assertEqual(len(error.getvalue().splitlines()), 1)
        self.assertIn('EACCES', error.getvalue())

    def test_disabled_and_read_only_are_silent_and_touch_no_cache(self):
        for read_only, environment in ((True, {}), (False, {cache.DISABLE_ENV: '1'}),
                                       (False, {'PYTHONDONTWRITEBYTECODE': '1'})):
            with self.subTest(read_only=read_only, environment=environment):
                cache._configured = cache._UNSET
                error = io.StringIO()
                with patch.dict(os.environ, environment), \
                        patch.object(cache, '_flush_if_stale', side_effect=AssertionError('disabled flush')), \
                        contextlib.redirect_stderr(error):
                    self.assertIsNone(cache.configure(read_only=read_only, scripts_dir=self.scripts))
                self.assertEqual(error.getvalue(), '')
                self.assertEqual(self.snapshot(), self.before)


    def test_failed_rename_never_accepts_partial_in_place_removal(self):
        (self.prefix / 'remaining.pyc').write_bytes(b'stale survives partial removal')
        before = self.snapshot()
        def partial(path):
            (Path(path) / 'old.pyc').unlink(missing_ok=True)
        with patch.object(cache.os, 'rename', side_effect=OSError(errno.EXDEV, 'cross device')), \
                patch.object(cache, '_remove_tree_no_follow', side_effect=partial) as removal, \
                contextlib.redirect_stderr(io.StringIO()):
            result = cache._flush_if_stale(self.cache_root, self.prefix, self.version)
        self.assertFalse(result)
        removal.assert_not_called()
        self.assertEqual(self.snapshot(), before)
