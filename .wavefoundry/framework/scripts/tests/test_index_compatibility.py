"""Native publication and process-barrier regressions for monotonic writers."""
from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import index_compatibility as ic
import index_state_store as iss
import graph_indexer as gi
import sqlite_runtime
import sqlite_vector_store as vectors


def _line(process):
    """Portable finite barrier read, including native Windows anonymous pipes."""
    result = queue.Queue()
    thread = threading.Thread(target=lambda: result.put(process.stdout.readline()), daemon=True)
    thread.start()
    return result.get(timeout=25).strip()


class StoreFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.index_dir = Path(self.tmp.name) / '.wavefoundry' / 'index'
        self.store = iss.IndexStateStore(self.index_dir)
        self.addCleanup(self.store.close)
        self.conn = self.store._conn

    def graph_meta(self):
        return {key: str(value) for key, value in ic.SUPPORTED.items() if key.startswith('graph:')}

    def inject(self, **meta):
        with self.conn:
            self.conn.executemany('INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)', meta.items())

    def snapshot(self):
        return {table: list(self.conn.execute(f'SELECT * FROM {table} ORDER BY 1'))
                for table in ('meta', 'build_state', 'build_layer_meta', 'chunks_docs',
                              'vectors_docs', 'chunk_registry', 'graph_nodes', 'graph_file_state')}


class CompatibilityTests(StoreFixture):
    def test_decimal_controls_and_malformed_values(self):
        for old in ('0', '9', '10', 10):
            ic.check_ordered('builder', old, '10')
        with self.assertRaises(ic.IndexCompatibilityError) as raised:
            ic.check_ordered('builder', '11', '10')
        self.assertEqual(raised.exception.code, 'index_version_newer')
        for value in (None, True, False, 1.5, -1, '-1', '1.0', ' 1', '1-old', {}, []):
            with self.subTest(value=value), self.assertRaises(ic.IndexCompatibilityError) as raised:
                ic.check_ordered('builder', value, '10')
            self.assertEqual(raised.exception.code, 'index_compatibility_unproven')

    def test_each_ordered_participant_refuses_open_and_preserves(self):
        initial = self.snapshot()
        for key, value in ic.SUPPORTED.items():
            with self.subTest(key=key):
                self.inject(**self.graph_meta())
                if key.startswith('graph:') or key == 'store_schema_version':
                    self.inject(**{key: str(int(value) + 1)})
                elif key == 'lexical_statistics.version':
                    self.inject(lexical_statistics=json.dumps({'version': int(value) + 1}))
                else:
                    layer_key = 'walker_version' if key == 'walker_version' else 'chunker_versions'
                    raw = str(int(value) + 1) if key == 'walker_version' else json.dumps({'docs': str(int(value) + 1)})
                    with self.conn:
                        self.conn.execute('INSERT OR REPLACE INTO build_layer_meta(key,value) VALUES(?,?)', (layer_key, raw))
                before = self.snapshot()
                with self.assertRaises(ic.IndexCompatibilityError) as raised:
                    iss.IndexStateStore(self.index_dir)
                self.assertEqual(raised.exception.code, 'index_version_newer')
                self.assertEqual(self.snapshot(), before)
                with self.conn:
                    self.conn.execute('DELETE FROM meta')
                    self.conn.executemany('INSERT INTO meta VALUES(?,?)', initial['meta'])
                    self.conn.execute('DELETE FROM build_layer_meta')

    def test_empty_and_legacy_scalar_are_allowed_but_partial_graph_refused(self):
        ic.check_connection(self.conn)
        with self.conn:
            self.conn.execute("INSERT INTO build_layer_meta VALUES('chunker_version','1')")
        ic.check_connection(self.conn)
        self.inject(**{'graph:builder_version': gi.GRAPH_BUILDER_VERSION})
        before = self.snapshot()
        with self.assertRaises(ic.IndexCompatibilityError) as raised:
            iss.begin_build_epoch(self.index_dir, 'graph')
        self.assertEqual(raised.exception.code, 'index_compatibility_unproven')
        self.assertEqual(self.snapshot(), before)

    def test_newer_graph_blocks_direct_semantic_fts_epoch_and_graph_paths(self):
        self.inject(**self.graph_meta())
        self.inject(**{'graph:builder_version': str(int(gi.GRAPH_BUILDER_VERSION) + 1)})
        publication = gi.GraphPublication(layer='project', reset=True)
        operations = (
            lambda: iss.begin_build_epoch(self.index_dir, 'all'),
            lambda: iss.apply_chunk_deltas(self.index_dir, 'docs', delete_ids=['retained']),
            lambda: iss.rebuild_chunk_index(self.index_dir, 'docs', []),
            lambda: gi.GraphStateStore(self.conn, layer='project', walker_version='16', chunker_version='42').ensure_current(),
            lambda: publication.apply(self.conn),
            lambda: vectors.delete_rows(self.conn, 'docs', ids=['retained']),
            lambda: iss.write_build_bookkeeping(self.index_dir, {}),
        )
        before = self.snapshot()
        for operation in operations:
            with self.subTest(operation=operation), self.assertRaises(ic.IndexCompatibilityError):
                operation()
            self.assertEqual(self.snapshot(), before)

    def test_finalizer_refuses_newer_statistics_before_generation_change(self):
        attempt = iss.begin_build_epoch(self.index_dir, 'all')
        self.inject(lexical_statistics=json.dumps({'version': iss.LEXICAL_STATISTICS_VERSION + 1}))
        before = self.snapshot()
        with self.assertRaises(ic.IndexCompatibilityError):
            iss.finalize_build_epoch(self.index_dir, attempt)
        self.assertEqual(self.snapshot(), before)

    def test_fts_maintenance_refuses_newer_statistics_without_mutation(self):
        self.inject(lexical_statistics=json.dumps({'version': iss.LEXICAL_STATISTICS_VERSION + 1}))
        before = self.snapshot()
        with self.assertRaises(ic.IndexCompatibilityError) as raised:
            iss.sqlite_store_maintenance(self.store.path)
        self.assertEqual(raised.exception.code, 'index_version_newer')
        self.assertEqual(self.snapshot(), before)

    def test_separate_memory_maintenance_keeps_its_own_contract(self):
        import sqlite3
        memory = Path(self.tmp.name) / 'memory-state.sqlite'
        conn = sqlite3.connect(memory)
        try:
            conn.execute('CREATE VIRTUAL TABLE memory_fts USING fts5(text)')
            conn.execute("INSERT INTO memory_fts(text) VALUES('retained memory text')")
            conn.commit()
        finally:
            conn.close()
        result = iss.sqlite_store_maintenance(memory)
        self.assertTrue(result['maintenance_complete'], result)
        conn = sqlite3.connect(memory)
        try:
            self.assertEqual(conn.execute('SELECT text FROM memory_fts').fetchall(), [('retained memory text',)])
        finally:
            conn.close()

    def test_newer_schema_read_is_typed_not_absent(self):
        self.inject(store_schema_version=str(int(iss.STATE_STORE_SCHEMA_VERSION) + 1))
        with self.assertRaises(ic.IndexCompatibilityError) as raised:
            iss.open_read_only(self.index_dir)
        self.assertEqual(raised.exception.code, 'index_version_newer')

    def test_complete_text_only_provenance_is_required_before_repair(self):
        iss.apply_chunk_deltas(self.index_dir, 'docs', add_rows=[{'id':'real','path':'guide.md','text':'retained text'}])
        with self.conn:
            self.conn.execute("UPDATE build_state SET status='complete',generation=1 WHERE id=1")
        before = self.snapshot()
        with self.assertRaises(ic.IndexCompatibilityError) as raised:
            iss.rebuild_chunk_index(self.index_dir, 'docs', [])
        self.assertEqual(raised.exception.component, 'walker_version')
        self.assertEqual(self.snapshot(), before)

    def test_same_runtime_explicit_model_identity_remains_opaque(self):
        for model in ('z-model@full@hash-9', 'a-model@int8@hash-1'):
            iss.write_build_bookkeeping(self.index_dir, {'model_versions': {'docs': model},
                'chunker_versions': {'docs': '42'}, 'walker_version': '16'})
            ic.check_connection(self.conn)
        self.assertIn('a-model', dict(self.conn.execute('SELECT * FROM build_layer_meta'))['model_versions'])

    def test_malformed_stats_and_opaque_tokenizer_preserve(self):
        for raw in ('[]', '{', json.dumps({'version': True}),
                    json.dumps({'version': 1, 'tokenizer': 'future opaque tokenizer'})):
            self.inject(lexical_statistics=raw)
            before = self.snapshot()
            with self.assertRaises(ic.IndexCompatibilityError):
                iss.rebuild_chunk_index(self.index_dir, 'docs', [])
            self.assertEqual(self.snapshot(), before)


class ProcessBarrierTests(StoreFixture):
    def child(self, source, *args, extra_path=None):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        env['PYTHONPATH'] = os.pathsep.join(filter(None, [str(extra_path) if extra_path else '', str(SCRIPTS)]))
        process = subprocess.Popen([sys.executable, '-B', '-c', source, *map(str, args)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
            cwd=self.tmp.name)  # Do not let the suite's scripts cwd shadow copied producer sources.
        def close():
            if process.poll() is None:
                process.terminate()
            process.communicate(timeout=10)
        self.addCleanup(close)
        return process

    def test_optional_store_loaders_wait_for_complete_canonical_import(self):
        # Exercise the real loader in isolation. Pause module execution, then
        # distinguish a waiting canonical import from premature module exposure
        # by observing its import-lock acquisition, without a timing assertion.
        source = """import importlib, importlib.machinery, importlib._bootstrap
import queue, sys, threading
producer = importlib.import_module(sys.argv[1])
loader = getattr(producer, sys.argv[2])
sys.modules.pop('index_state_store', None)
entered, release, observed = threading.Event(), threading.Event(), threading.Event()
outcomes, loaded, failures = queue.Queue(), [], []
original_exec = importlib.machinery.SourceFileLoader.exec_module
original_acquire = importlib._bootstrap._ModuleLock.acquire
def paused_exec(self, module):
    if module.__name__ == 'index_state_store':
        entered.set()
        assert release.wait(15), 'execution barrier timed out'
    return original_exec(self, module)
def observed_acquire(self):
    if self.name == 'index_state_store' and threading.current_thread().name == 'reader' and not observed.is_set():
        observed.set()
        outcomes.put('waiting')
    return original_acquire(self)
def initialize():
    try: loaded.append(loader())
    except BaseException as exc: failures.append(repr(exc))
def read():
    try:
        module = importlib.import_module('index_state_store')
        outcomes.put('complete' if hasattr(module, 'open_read_only') else 'partial')
        loaded.append(module)
    except BaseException as exc: failures.append(repr(exc))
importlib.machinery.SourceFileLoader.exec_module = paused_exec
importlib._bootstrap._ModuleLock.acquire = observed_acquire
writer = threading.Thread(target=initialize, daemon=True)
reader = threading.Thread(target=read, name='reader', daemon=True)
writer.start()
assert entered.wait(15), 'loader never entered'
reader.start()
try:
    first = outcomes.get(timeout=15)
finally:
    release.set()
writer.join(15); reader.join(15)
assert not writer.is_alive() and not reader.is_alive()
assert not failures, failures
assert first == 'waiting', first
assert outcomes.get(timeout=15) == 'complete'
assert len(loaded) == 2 and loaded[0] is loaded[1]
assert loader() is loaded[0]
print('synchronized', flush=True)
"""
        for module, loader in (('indexer', '_get_index_state_store'),
                               ('scan_secrets', '_load_state_store')):
            with self.subTest(module=module):
                process = self.child(source, module, loader)
                stdout, stderr = process.communicate(timeout=40)
                self.assertEqual(process.returncode, 0, stderr)
                self.assertEqual(stdout.strip(), 'synchronized')

    def test_prepared_graph_worker_rechecks_publication_and_mutant_is_killed(self):
        source = '''import sys
from pathlib import Path
import index_compatibility as ic
import index_state_store as iss
import graph_indexer as gi
store=iss.IndexStateStore(Path(sys.argv[1]))
expected={k.removeprefix('graph:'):str(v) for k,v in ic.SUPPORTED.items() if k.startswith('graph:')}
plan=gi.GraphPublication(layer='project',reset=True,meta=expected)
ic.check_connection(store._conn)
print('prepared',flush=True)
input()
if sys.argv[2]=='mutant': ic.check_connection=lambda *a,**k:None
try:
    plan.apply(store._conn)
    print('committed',flush=True)
except ic.IndexCompatibilityError as exc: print(exc.code,flush=True)
finally: store.close()
'''
        for mutant in (False, True):
            with self.subTest(mutant=mutant):
                self.inject(**self.graph_meta())
                with self.conn:
                    self.conn.execute("DELETE FROM graph_nodes")
                process = self.child(source, self.index_dir, 'mutant' if mutant else 'guarded')
                self.assertEqual(_line(process), 'prepared')
                future = str(int(gi.GRAPH_BUILDER_VERSION) + 1)
                self.inject(**{'graph:builder_version': future})
                with self.conn:
                    self.conn.execute("INSERT INTO graph_nodes(node_id,label,kind,source_file,source_location,layer,external,attributes) VALUES('new::retained','retained','function','new.py','1:0','project',0,'{}')")
                    self.conn.execute("UPDATE build_state SET status='complete',generation=generation+1 WHERE id=1")
                before = self.snapshot()
                process.stdin.write('publish\n'); process.stdin.flush()
                result = _line(process)
                stdout, stderr = process.communicate(timeout=25)
                self.assertEqual(process.returncode, 0, stderr)
                if not mutant:
                    self.assertEqual(result, 'index_version_newer')
                    self.assertEqual(self.snapshot(), before)
                else:
                    self.assertEqual(result, 'committed')
                    self.assertNotEqual(self.snapshot(), before, 'omitting publication fence must invalidate preservation oracle')
                    self.assertEqual(dict(self.conn.execute('SELECT * FROM meta'))['graph:builder_version'], gi.GRAPH_BUILDER_VERSION)

    def test_worker_started_before_new_publication_refuses_at_preparation(self):
        self.inject(**self.graph_meta())
        source = '''import sys
from pathlib import Path
import index_state_store as iss
import index_compatibility as ic
print('loaded',flush=True)
input()
try: iss.IndexStateStore(Path(sys.argv[1])); print('opened',flush=True)
except ic.IndexCompatibilityError as exc: print(exc.code,flush=True)
'''
        process = self.child(source, self.index_dir)
        self.assertEqual(_line(process), 'loaded')
        self.inject(**{'graph:builder_version': str(int(gi.GRAPH_BUILDER_VERSION)+1)})
        before=self.snapshot()
        process.stdin.write('prepare\n'); process.stdin.flush()
        self.assertEqual(_line(process), 'index_version_newer')
        process.communicate(timeout=25)
        self.assertEqual(process.returncode,0)
        self.assertEqual(self.snapshot(),before)

    def test_loaded_model_and_lazy_producer_refuse_same_stat_source_replacement(self):
        copied = Path(self.tmp.name) / 'scripts'; copied.mkdir()
        for name in (*ic._SOURCE_NAMES, 'index_compatibility'):
            shutil.copy2(SCRIPTS / (name + '.py'), copied / (name + '.py'))
        source = '''import sys
import model_bundle
import index_compatibility as ic
print(model_bundle.EMBEDDING_COMPATIBILITY_FINGERPRINT,flush=True)
input()
try:
    import graph_indexer
    print('accepted',flush=True)
except ic.IndexCompatibilityError as exc: print(exc.code,flush=True)
'''
        process=self.child(source, extra_path=copied)
        initial=_line(process); self.assertIn('arctic-s',initial)
        path=copied/'model_bundle.py'; st=path.stat(); data=path.read_bytes()
        changed=data.replace(b'wf-model-set-2-20260811-arctic-s',b'wf-model-set-2-20260811-arctic-x')
        self.assertNotEqual(data,changed); self.assertEqual(len(data),len(changed))
        path.write_bytes(changed); os.utime(path,ns=(st.st_atime_ns,st.st_mtime_ns))
        process.stdin.write('lazy-import\n'); process.stdin.flush()
        self.assertEqual(_line(process),'index_runtime_stale')
        process.communicate(timeout=25);self.assertEqual(process.returncode,0)
        # Explicit fresh runtime selection adopts the installed opaque identity.
        fresh=self.child('import model_bundle; print(model_bundle.EMBEDDING_COMPATIBILITY_FINGERPRINT,flush=True)',extra_path=copied)
        self.assertIn('arctic-x',_line(fresh));fresh.communicate(timeout=25);self.assertEqual(fresh.returncode,0)

    def test_marker_namespace_source_unchanged_passes_and_replacement_is_stale(self):
        copied = Path(self.tmp.name) / 'marker-scripts'
        copied.mkdir()
        for name in (*ic._SOURCE_NAMES, 'index_compatibility'):
            shutil.copy2(SCRIPTS / (name + '.py'), copied / (name + '.py'))
        source = '''import chunker
import index_compatibility as ic
ic.ensure_runtime_current()
print('unchanged', flush=True)
input()
try:
    ic.ensure_runtime_current()
    print('accepted', flush=True)
except ic.IndexCompatibilityError as exc:
    print(exc.code + ':' + exc.component, flush=True)
'''
        process = self.child(source, extra_path=copied)
        self.assertEqual(_line(process), 'unchanged')
        path = copied / 'marker_namespaces.py'
        stat = path.stat()
        original = path.read_bytes()
        replacement = original.replace(b'"waveforge"', b'"waveforgx"')
        self.assertNotEqual(replacement, original)
        self.assertEqual(len(replacement), len(original))
        path.write_bytes(replacement)
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        process.stdin.write('check\n')
        process.stdin.flush()
        self.assertEqual(_line(process), 'index_runtime_stale:marker_namespaces')
        _, stderr = process.communicate(timeout=25)
        self.assertEqual(process.returncode, 0, stderr)
        fresh = self.child('import chunker; import index_compatibility as ic; '
                           'ic.ensure_runtime_current(); print("adopted", flush=True)',
                           extra_path=copied)
        self.assertEqual(_line(fresh), 'adopted')
        _, stderr = fresh.communicate(timeout=25)
        self.assertEqual(fresh.returncode, 0, stderr)

    def test_compiled_old_module_cannot_capture_new_installed_bytes(self):
        copied = Path(self.tmp.name) / 'compiled-scripts'; copied.mkdir()
        for name in (*ic._SOURCE_NAMES, 'index_compatibility'):
            shutil.copy2(SCRIPTS / (name + '.py'), copied / (name + '.py'))
        source = """import sys
from pathlib import Path
path=Path(sys.argv[1])/'model_bundle.py'
code=compile(path.read_bytes(),str(path),'exec',dont_inherit=True)
print('compiled',flush=True)
input()
try: exec(code,{'__name__':'old_loaded_model','__file__':str(path)})
except Exception as exc: print(getattr(exc,'code',type(exc).__name__),flush=True)
"""
        process=self.child(source,copied,extra_path=copied)
        self.assertEqual(_line(process),'compiled')
        path=copied/'model_bundle.py'
        path.write_bytes(path.read_bytes().replace(b'wf-model-set-2-20260811-arctic-s',b'wf-model-set-2-20260811-arctic-x'))
        process.stdin.write('execute-old-code\n');process.stdin.flush()
        self.assertEqual(_line(process),'index_runtime_stale')
        process.communicate(timeout=25);self.assertEqual(process.returncode,0)


if __name__ == '__main__':
    unittest.main()
