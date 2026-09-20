"""Automatic source writers and builders exclude each other with real OS locks."""
from contextlib import contextmanager
import errno
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
        self.wave_md = self.root / 'docs/waves' / self.wave / 'wave.md'
        self.wave_md.parent.mkdir(parents=True)
        self.wave_md.write_text(f'# Wave\n\nStatus: implementing\n\nwave-id: `{self.wave}`\n')
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
        with patch.object(guard.RuntimeFileLock, 'acquire', side_effect=guard.RuntimeLockError(errno.EIO, 'probe failure')):
            result = server._project_context_efficiency_wave(self.root, self.wave, automatic=True)
        self.assertEqual(result['reason'], 'index_source_unavailable')
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
        class Registry:
            def __init__(self):
                self.resources = {}
            def tool(self, **kwargs):
                return lambda fn: fn
            def resource(self, uri, **kwargs):
                def register(fn):
                    self.resources[uri] = fn
                    return fn
                return register
        registry = Registry()
        server.register_mcp_surface(registry, lambda: SimpleNamespace(root=self.root))
        read = registry.resources['wavefoundry://codebase-map']
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
