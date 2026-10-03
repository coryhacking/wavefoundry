"""Automatic source writers and builders exclude each other with real OS locks."""
from contextlib import contextmanager
import errno
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import index_source_guard as guard
import indexer
import server_impl as server


class SourceGuardTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        (self.root / 'docs').mkdir()
        (self.root / 'docs/workflow-config.json').write_text('{}')
        self.wave = '1aaaa automatic-source-guard'
        # The record in the configured layout and vocabulary (the shipped
        # profile, or a profile's).
        import record_paths
        import vocabulary_profile as vp

        self.wave_md = self.root / record_paths.WAVES_ROOT / self.wave / vp.RECORD_FILENAME
        self.wave_md.parent.mkdir(parents=True)
        self.wave_md.write_text(f'# Wave\n\nStatus: implementing\n\n{vp.ID_KEY}: `{self.wave}`\n')
        self.ce = server.context_efficiency
        self.telemetry = self.ce.ProcessTelemetry(self.root)
        self.telemetry.set_focus(self.wave, 'implement', new_phase=True)
        self.record('initial')
        server._project_context_efficiency_wave(self.root, self.wave, automatic=True)
        self.before = self.wave_md.read_bytes()
        self.record('pending')

    def record(self, event):
        self.telemetry.record_retrieval({
            'estimated_request_tokens': 2, 'estimated_returned_tokens': 3,
            'estimated_source_tokens': 1, 'estimated_avoided_tokens': 4,
            'source_files_counted': 1, 'source_files_verified': 1,
            'source_files_estimated': 0, 'captured': True,
            'persistence': 'pending', 'method': self.ce.RETRIEVAL_METHOD,
        }, event_id=event)

    def wait_until(self, predicate):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(.01)
        self.fail('bounded concurrent operation did not reach its expected state')

    @contextmanager
    def monitor(self):
        handler = server.ImplHandler.__new__(server.ImplHandler)
        handler.root = self.root
        handler._ce_projection_observed = {}
        handler._ce_projection_status = {}
        handler._ce_projection_stop = handler._ce_projection_thread = None
        with patch.object(server, '_read_ce_projection_config', return_value={
                'enabled': True, 'interval_seconds': .01, 'quiet_period_seconds': 0}):
            handler._start_ce_projection_monitor()
            try:
                yield handler
            finally:
                handler._stop_ce_projection_monitor()

    def test_real_monitor_defers_to_other_process_build_then_rearms(self):
        code = '''import sys
from pathlib import Path
import indexer,index_source_guard
root=Path(sys.argv[1])
with indexer._index_build_lock(root/'.wavefoundry/index'), index_source_guard.index_source_guard(root):
 print('held',flush=True)
 sys.stdin.readline()
'''
        env = dict(os.environ, PYTHONPATH=str(SCRIPTS), PYTHONDONTWRITEBYTECODE='1')
        child = subprocess.Popen([sys.executable, '-B', '-c', code, str(self.root)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, env=env)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'held')
            with self.monitor() as handler:
                self.wait_until(lambda: handler._ce_projection_status.get('reason') == 'index_source_busy'
                                or self.wave_md.read_bytes() != self.before)
                self.assertEqual(self.wave_md.read_bytes(), self.before,
                                 'automatic monitor wrote while another process held build/source exclusion')
                self.assertTrue(self.ce.read_wave_snapshot(self.root, self.wave)['pending'])
                child.stdin.write('\n'); child.stdin.flush()
                child.communicate(timeout=3)
                self.wait_until(lambda: not self.ce.read_wave_snapshot(self.root, self.wave)['pending'])
                self.assertGreater(self.ce.parse_checkpoint_block(self.wave_md.read_text())['generation'],
                                   self.ce.parse_checkpoint_block(self.before.decode())['generation'])
        finally:
            if child.poll() is None:
                child.kill(); child.communicate(timeout=3)
        self.assertTrue((self.root / '.wavefoundry/index/index-build.lock').exists())
        self.assertTrue((self.root / '.wavefoundry/locks/index-source-mutation.lock').exists())

    def assert_path_free(self, error):
        self.assertIsInstance(error, str)
        for form in {str(self.root), json.dumps(str(self.root))[1:-1], str(self.root).replace('/', '\\\\')}:
            self.assertNotIn(form, error)
        self.assertNotIn(json.dumps(str(self.root))[1:-1], json.dumps(error))

    def test_busy_projection_row_names_the_lock_without_an_absolute_path(self):
        """Delivery review (wave 1zls7): the row index_health surfaces through
        background_monitors carries the class, errno name and the
        repository-relative lock path, never the absolute lock path."""
        code = '''import sys
from pathlib import Path
import index_source_guard
with index_source_guard.index_source_guard(Path(sys.argv[1])):
 print('held',flush=True)
 sys.stdin.readline()
'''
        env = dict(os.environ, PYTHONPATH=str(SCRIPTS), PYTHONDONTWRITEBYTECODE='1')
        child = subprocess.Popen([sys.executable, '-B', '-c', code, str(self.root)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, env=env)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'held')
            row = server._project_context_efficiency_wave(self.root, self.wave, automatic=True)
        finally:
            child.stdin.write('\n'); child.stdin.flush()
            child.communicate(timeout=3)
        self.assertEqual(row['reason'], 'index_source_busy')
        self.assert_path_free(row['error'])
        self.assertTrue(row['error'].startswith('RuntimeLockBusy E'), row['error'])
        self.assertTrue(row['error'].endswith('.wavefoundry/locks/index-source-mutation.lock'), row['error'])
        self.assertEqual(self.wave_md.read_bytes(), self.before)

    def test_unavailable_and_failed_projection_rows_are_path_free(self):
        lock = self.root / '.wavefoundry/locks/index-source-mutation.lock'
        # The modules the called function actually resolves at run time: its
        # own globals, never sys.modules (an in-process reload earlier in the
        # same run leaves this test's ``server`` binding on the old modules).
        projection_globals = server._project_context_efficiency_wave.__globals__
        live_guard = projection_globals['index_source_guard']
        live_ce = projection_globals['context_efficiency']

        @contextmanager
        def unavailable(root, *, wait=True):
            raise live_guard.RuntimeLockError(errno.EIO, f'Unable to acquire runtime lock {lock}: denied')
            yield

        with patch.object(live_guard, 'index_source_guard', unavailable):
            row = server._project_context_efficiency_wave(self.root, self.wave, automatic=True)
        self.assertEqual(row.get('reason'), 'index_source_unavailable', row)
        self.assertEqual(row.get('error'), 'RuntimeLockError EIO on .wavefoundry/locks/index-source-mutation.lock')

        with patch.object(live_ce, 'read_wave_snapshot',
                          side_effect=PermissionError(errno.EACCES, 'denied', str(self.wave_md))):
            row = server._project_context_efficiency_wave(self.root, self.wave, automatic=True)
        self.assertEqual(row.get('persistence'), 'failed', row)
        self.assertEqual(row.get('error'), 'PermissionError EACCES')
        for error in (row['error'],):
            self.assert_path_free(error)

    def test_same_process_build_excludes_monitor_and_unlocked_carrier_allows_write(self):
        with self.monitor() as handler:
            with indexer._index_build_lock(self.root / '.wavefoundry/index'), guard.index_source_guard(self.root):
                self.wait_until(lambda: handler._ce_projection_status.get('reason') == 'index_source_busy')
                self.assertEqual(self.wave_md.read_bytes(), self.before)
            self.wait_until(lambda: not self.ce.read_wave_snapshot(self.root, self.wave)['pending'])
        self.assertNotEqual(self.wave_md.read_bytes(), self.before)
        self.assertTrue((self.root / '.wavefoundry/locks/index-source-mutation.lock').exists())

    def test_writer_first_blocks_build_source_reads_until_write_finishes(self):
        writing, release, builder_started, source_read = (threading.Event() for _ in range(4))
        failures = []
        original = server._atomic_replace_text
        def paused_write(*args):
            writing.set()
            if not release.wait(3):
                raise AssertionError('writer release missing')
            return original(*args)
        def builder():
            try:
                with indexer._index_build_lock(self.root / '.wavefoundry/index'):
                    builder_started.set()
                    with guard.index_source_guard(self.root):
                        source_read.set()
            except BaseException as exc:
                failures.append(exc)
        with patch.object(server, '_atomic_replace_text', side_effect=paused_write), self.monitor():
            self.assertTrue(writing.wait(3))
            thread = threading.Thread(target=builder)
            thread.start()
            try:
                self.assertTrue(builder_started.wait(3))
                self.assertFalse(source_read.wait(.05), 'builder read while automatic write was held')
            finally:
                release.set(); thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertEqual(failures, [])
            self.assertTrue(source_read.is_set())

    def test_unknown_acquisition_preserves_pending_work(self):
        # The guard module the called function resolves (its own globals),
        # which an in-process reload may have replaced since this module imported.
        live_guard = server._project_context_efficiency_wave.__globals__['index_source_guard']
        with patch.object(live_guard.RuntimeFileLock, 'acquire', side_effect=live_guard.RuntimeLockError(errno.EIO, 'probe failure')):
            result = server._project_context_efficiency_wave(self.root, self.wave, automatic=True)
        self.assertEqual(result.get('reason'), 'index_source_unavailable', result)
        self.assertEqual(self.wave_md.read_bytes(), self.before)
        self.assertTrue(self.ce.read_wave_snapshot(self.root, self.wave)['pending'])

    def test_writer_first_blocks_other_process_source_read(self):
        writing, release, source_read = (threading.Event() for _ in range(3))
        original = server._atomic_replace_text
        def paused_write(*args):
            writing.set()
            if not release.wait(3):
                raise AssertionError('writer release missing')
            return original(*args)
        code = '''import sys
from pathlib import Path
import indexer,index_source_guard
root=Path(sys.argv[1])
with indexer._index_build_lock(root/'.wavefoundry/index'):
 print('build-held',flush=True)
 with index_source_guard.index_source_guard(root):
  print('source-read',flush=True)
'''
        env = dict(os.environ, PYTHONPATH=str(SCRIPTS), PYTHONDONTWRITEBYTECODE='1')
        with patch.object(server, '_atomic_replace_text', side_effect=paused_write), self.monitor():
            self.assertTrue(writing.wait(3))
            child = subprocess.Popen([sys.executable, '-B', '-c', code, str(self.root)],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            try:
                self.assertEqual(child.stdout.readline().strip(), 'build-held')
                def read_child():
                    if child.stdout.readline().strip() == 'source-read':
                        source_read.set()
                reader = threading.Thread(target=read_child)
                reader.start()
                self.assertFalse(source_read.wait(.05))
                release.set()
                self.assertTrue(source_read.wait(3))
                reader.join(3)
                child.wait(timeout=3)
                self.assertEqual(child.returncode, 0)
            finally:
                release.set()
                if child.poll() is None:
                    child.kill()
                child.communicate(timeout=3)

    def test_publication_contention_releases_source_guard(self):
        held, release = threading.Event(), threading.Event()
        def publisher():
            with server.project_state_publication_lock(self.root):
                held.set(); release.wait(3)
        thread = threading.Thread(target=publisher); thread.start()
        try:
            self.assertTrue(held.wait(3))
            result = server._project_context_efficiency_wave(self.root, self.wave, automatic=True)
            self.assertEqual(result['reason'], 'publication_lock_busy')
            with guard.index_source_guard(self.root, wait=False):
                pass
        finally:
            release.set(); thread.join(3)
        self.assertEqual(self.wave_md.read_bytes(), self.before)

    def test_missing_map_resource_defers_both_outputs_then_retries(self):
        from declaration_support import RecordingFastMCP  # shared FastMCP-backed double (change 1zim4)
        registry = RecordingFastMCP()
        server.register_mcp_surface(registry, lambda: SimpleNamespace(root=self.root))
        read = registry.resource_uris['wavefoundry://codebase-map']
        gen = server._load_script('gen_codebase_map')
        repo_index = self.root / 'docs/repo-index.md'
        repo_index.write_text('# Index\n' + gen.REPO_INDEX_MARKER_BEGIN + '\nold\n' + gen.REPO_INDEX_MARKER_END)
        before = repo_index.read_bytes()
        output = self.root / gen.OUTPUT_REL_PATH
        with guard.index_source_guard(self.root):
            self.assertIn('No map available', read())
            self.assertFalse(output.exists())
            self.assertEqual(repo_index.read_bytes(), before)
        self.assertIn('Codebase Map', read())
        self.assertTrue(output.exists())
        self.assertNotEqual(repo_index.read_bytes(), before)
        rendered = output.read_bytes()
        with guard.index_source_guard(self.root):
            read()
        self.assertEqual(output.read_bytes(), rendered)


if __name__ == '__main__':
    unittest.main()
