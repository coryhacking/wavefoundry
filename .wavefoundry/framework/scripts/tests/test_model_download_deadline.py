"""Cold download deadlines: bounded local stubs only, never a model/network fetch."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import numpy  # retain native module across scoped sys.modules fixture restoration
import setup_index as setup
import accel_embedder as accel
import indexer


class ModelDownloadDeadlineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'docs').mkdir()
        (self.root / 'docs/workflow-config.json').write_text(json.dumps({'setup': {
            'model_warm_timeout_seconds': .05,
            'hf_hub_download_timeout_seconds': .2,
            'hf_hub_etag_timeout_seconds': .3}}))
        self.constants = types.SimpleNamespace(HF_HUB_DOWNLOAD_TIMEOUT=10,
            HF_HUB_ETAG_TIMEOUT=10, HF_HUB_DISABLE_XET=False)
        self.hub = types.SimpleNamespace(constants=self.constants)
        self.enter = self.enterContext
        self.enter(patch.dict(sys.modules, {'huggingface_hub': self.hub}))
        self.enter(patch.object(setup, 'ensure_ca_bundle_applied'))
        self.enter(patch.object(setup, 'retry_with_ca_bundle_ladder', side_effect=lambda f, m: f()))
        self.enter(patch.dict(os.environ, {'FASTEMBED_CACHE_PATH': str(self.root/'cache'), 'HF_HUB_DISABLE_XET':'1'}))

    def blocking(self):
        release = threading.Event()
        exited = threading.Event()
        def work(*a, **kw):
            if kw.get('local_files_only'):
                raise RuntimeError('not cached')
            try:
                release.wait(2)
                return '/downloaded/model.onnx'
            finally:
                exited.set()
        def clean():
            release.set()
            self.assertTrue(exited.wait(2))
            for thread in threading.enumerate():
                if thread.name == 'wavefoundry-model-download-deadline':
                    thread.join(2)
                    self.assertFalse(thread.is_alive())
        self.addCleanup(clean)
        return work, release, exited

    def test_all_four_online_routes_obey_root_settings_and_propagate(self):
        import server_impl as srv
        for route in ('hub', 'resident', 'cpu', 'background'):
            with self.subTest(route=route):
                work, release, exited = self.blocking()
                self.hub.hf_hub_download = work
                with patch.dict(sys.modules, {'fastembed': types.SimpleNamespace(TextEmbedding=work)}), setup.model_download_root(self.root):
                    started = time.monotonic()
                    with self.assertRaisesRegex(setup.ModelDownloadDeadline, 'cache.*elapsed'):
                        if route == 'hub': accel._hf_download_cached_first(route, 'model.onnx', str(self.root/'cache'))
                        elif route == 'resident': accel._ensure_fastembed_model_cached(route)
                        elif route == 'cpu': indexer._text_embedding_cached_first(work, route, [])
                        else: srv._ensure_model_cached(route, 'embedding', root=self.root)
                    self.assertLess(time.monotonic()-started, .8)
                    self.assertEqual(self.constants.HF_HUB_DOWNLOAD_TIMEOUT, .2)
                    self.assertEqual(self.constants.HF_HUB_ETAG_TIMEOUT, .3)
                    self.assertTrue(self.constants.HF_HUB_DISABLE_XET)
                    release.set(); self.assertTrue(exited.wait(2))
                    for thread in threading.enumerate():
                        if thread.name == 'wavefoundry-model-download-deadline': thread.join(2)
                    self.assertEqual(self.constants.HF_HUB_DOWNLOAD_TIMEOUT, 10)
                    self.assertFalse(self.constants.HF_HUB_DISABLE_XET)

    def test_same_model_guard_survives_timeout_alias_and_owner_release(self):
        work, release, exited = self.blocking()
        with self.assertRaises(setup.ModelDownloadDeadline):
            setup.download_with_deadline(work, 'Snowflake/model', self.root/'cache', root=self.root)
        calls=[]
        with self.assertRaisesRegex(setup.ModelDownloadDeadline, 'still running'):
            setup.download_with_deadline(lambda: calls.append(1), 'snowflake/MODEL', self.root/'cache/../cache', root=self.root)
        self.assertEqual(calls, [])
        key=setup._model_download_key('Snowflake/model', self.root/'cache')
        owner=setup._MODEL_DOWNLOAD_OWNERS[key]
        setup._release_model_download(key, object())
        self.assertIs(setup._MODEL_DOWNLOAD_OWNERS[key], owner)
        release.set(); self.assertTrue(exited.wait(2))
        for thread in threading.enumerate():
            if thread.name == 'wavefoundry-model-download-deadline': thread.join(2)
        self.assertEqual(setup.download_with_deadline(lambda: 'path', 'snowflake/model', self.root/'cache', root=self.root), 'path')

    def test_cached_paths_start_no_worker_and_return_path(self):
        self.hub.hf_hub_download=lambda *a,**k:'/cached/model.onnx'
        with patch.object(threading.Thread,'start', side_effect=AssertionError('cached branch started worker')):
            self.assertEqual(accel._hf_download_cached_first('repo','model.onnx',str(self.root)), '/cached/model.onnx')
            self.assertEqual(indexer._text_embedding_cached_first(lambda **kw:'cached', 'repo', []), 'cached')
            with patch.dict(sys.modules, {'fastembed':types.SimpleNamespace(TextEmbedding=lambda **kw:'cached')}):
                accel._ensure_fastembed_model_cached('repo')
                import server_impl
                server_impl._ensure_model_cached('repo','embedding',root=self.root)

    def test_required_accel_timeout_never_starts_cpu_fallback(self):
        indexer._EMBEDDER_CACHE.clear()
        with patch.object(indexer,'_onnx_providers',return_value=['CPUExecutionProvider']), patch.object(indexer.accel_embedder,'make_embedder',side_effect=setup.ModelDownloadDeadline('deadline')), patch.object(indexer,'_text_embedding_cached_first') as cpu, patch.dict(sys.modules, {'fastembed':types.SimpleNamespace(TextEmbedding=lambda **kw:None)}):
            with self.assertRaises(setup.ModelDownloadDeadline): indexer._get_embedder('deadline',root=self.root)
            cpu.assert_not_called()
        with patch.object(indexer,'_onnx_providers',return_value=['CPUExecutionProvider']), patch.object(indexer.accel_embedder,'make_embedder',side_effect=ValueError('ordinary')), patch.object(indexer,'_text_embedding_cached_first',return_value='cpu'), patch.dict(sys.modules, {'fastembed':types.SimpleNamespace(TextEmbedding=lambda **kw:None)}):
            self.assertEqual(indexer._get_embedder('ordinary',root=self.root),'cpu')

    def test_direct_cpu_without_setup_main_uses_actual_root(self):
        work, _, _ = self.blocking()
        indexer._EMBEDDER_CACHE.clear()
        with patch.object(indexer,'accel_embedder',None), patch.dict(sys.modules, {'fastembed':types.SimpleNamespace(TextEmbedding=work)}):
            with self.assertRaises(setup.ModelDownloadDeadline): indexer._get_embedder('initial-cpu',root=self.root)

    def test_real_docs_and_code_index_build_without_prewarm_fails_at_deadline(self):
        (self.root/'docs/guide.md').write_text('# Guide\n\nA small local indexing fixture.')
        (self.root/'example.py').write_text('def example():\n    return "local"\n')
        for content in ('docs', 'code'):
            with self.subTest(content=content):
                work, release, exited = self.blocking()
                indexer._EMBEDDER_CACHE.clear()
                with patch.object(indexer,'accel_embedder',None), patch.dict(sys.modules, {'fastembed':types.SimpleNamespace(TextEmbedding=work)}):
                    with self.assertRaises(setup.ModelDownloadDeadline):
                        indexer.build_index(self.root,full=True,content=content)
                release.set(); self.assertTrue(exited.wait(2))
                for thread in threading.enumerate():
                    if thread.name=='wavefoundry-model-download-deadline':thread.join(2)

    def test_accepted_finite_timeout_public_indexer_never_leaks_join_overflow(self):
        (self.root/'docs/workflow-config.json').write_text(
            '{"setup":{"model_warm_timeout_seconds":1e20}}')
        (self.root/'docs/guide.md').write_text('# Guide\n\nLocal numeric deadline fixture.')
        self.assertEqual(setup._setup_deadlines(self.root)['model_warm_timeout_seconds'], 1e20)
        release = threading.Event()
        exited = threading.Event()
        calls = []
        def work(**kw):
            if kw.get('local_files_only'):
                raise RuntimeError('not cached')
            calls.append(kw)
            try:
                if not release.wait(2):
                    raise AssertionError('local worker was not released')
                raise ValueError('released local worker')
            finally:
                exited.set()
        timer = threading.Timer(.05, release.set)
        timer.start()
        try:
            indexer._EMBEDDER_CACHE.clear()
            with patch.object(indexer, 'accel_embedder', None), patch.dict(
                    sys.modules, {'fastembed': types.SimpleNamespace(TextEmbedding=work)}):
                started = time.monotonic()
                with self.assertRaisesRegex(ValueError, 'released local worker'):
                    indexer.build_index(self.root, full=True, content='docs')
                self.assertLess(time.monotonic()-started, 1)
        finally:
            release.set()
            timer.join(2)
            self.assertTrue(exited.wait(2))
            for thread in threading.enumerate():
                if thread.name == 'wavefoundry-model-download-deadline':
                    thread.join(2)
                    self.assertFalse(thread.is_alive())
        self.assertEqual(len(calls), 1)
        self.assertEqual(setup._MODEL_DOWNLOAD_OWNERS, {})

    def test_nonfinite_json_uses_default_before_ownership_and_worker(self):
        (self.root/'docs/workflow-config.json').write_text(
            '{"setup":{"model_warm_timeout_seconds":1e309}}')
        stages = []
        read_settings = setup._setup_deadlines
        make_key = setup._model_download_key
        start_thread = threading.Thread.start
        def settings(root):
            result = read_settings(root)
            self.assertEqual(result['model_warm_timeout_seconds'], 1800)
            self.assertEqual(setup._MODEL_DOWNLOAD_OWNERS, {})
            stages.append('normalized')
            return result
        def key(*args):
            self.assertEqual(stages, ['normalized'])
            stages.append('ownership')
            return make_key(*args)
        def start(thread):
            self.assertEqual(stages, ['normalized', 'ownership'])
            stages.append('worker')
            return start_thread(thread)
        with patch.object(setup, '_setup_deadlines', side_effect=settings), patch.object(
                setup, '_model_download_key', side_effect=key), patch.object(
                threading.Thread, 'start', new=start):
            self.assertEqual(setup.download_with_deadline(
                lambda: 'local', 'nonfinite', self.root/'cache', root=self.root), 'local')
        self.assertEqual(stages, ['normalized', 'ownership', 'worker'])
        self.assertEqual(setup._MODEL_DOWNLOAD_OWNERS, {})

    def test_oversized_config_falls_back_before_real_download_worker(self):
        (self.root / 'docs/workflow-config.json').write_bytes(
            b'{"setup":{"model_warm_timeout_seconds":0.001}}' + b' ' * setup.DEFAULT_MAX_BYTES)
        observed = []
        read_settings = setup._setup_deadlines
        def settings(root):
            result = read_settings(root)
            self.assertEqual(result, dict(setup._SETUP_DEADLINE_KEYS))
            self.assertEqual(setup._MODEL_DOWNLOAD_OWNERS, {})
            observed.append('defaults')
            return result
        def work():
            self.assertEqual(observed, ['defaults'])
            time.sleep(.02)
            return 'local-download'
        with patch.object(setup, '_setup_deadlines', side_effect=settings):
            self.assertEqual(setup.download_with_deadline(work, 'oversized-config',
                self.root / 'cache', root=self.root), 'local-download')
        self.assertEqual(setup._MODEL_DOWNLOAD_OWNERS, {})

    def test_wait_slices_preserve_one_original_deadline(self):
        (self.root/'docs/workflow-config.json').write_text(
            '{"setup":{"model_warm_timeout_seconds":10}}')
        clock = [100.]
        waits = []
        workers = []
        class LocalWorker:
            def __init__(self, *, target, **kw):
                self.target = target
                workers.append(self)
            def start(self): pass
            def is_alive(self): return True
            def join(self, duration):
                waits.append(duration)
                if len(waits) > 4:
                    raise AssertionError('wait loop restarted its budget')
                if not 0 < duration <= 4:
                    raise AssertionError('join duration is not OS-representable')
                clock[0] += duration
        try:
            with patch.object(setup.threading, 'Thread', LocalWorker), patch.object(
                    setup.threading, 'TIMEOUT_MAX', 4), patch.object(
                    setup.time, 'monotonic', side_effect=lambda: clock[0]):
                with self.assertRaisesRegex(setup.ModelDownloadDeadline, 'elapsed 10.000s'):
                    setup.download_with_deadline(lambda: 'local', 'slices', self.root, root=self.root)
                self.assertEqual(waits, [4, 4, 2])
                self.assertEqual(clock[0], 110)
                self.assertEqual(len(setup._MODEL_DOWNLOAD_OWNERS), 1)
        finally:
            for worker in workers:
                worker.target()
        self.assertEqual(setup._MODEL_DOWNLOAD_OWNERS, {})

    def test_large_finite_wait_stops_immediately_when_worker_finishes(self):
        (self.root/'docs/workflow-config.json').write_text(
            '{"setup":{"model_warm_timeout_seconds":1e20}}')
        waits = []
        class LocalWorker:
            def __init__(self, *, target, **kw):
                self.target = target
                self.alive = True
            def start(self): pass
            def is_alive(self): return self.alive
            def join(self, duration):
                waits.append(duration)
                if not 0 < duration <= 4:
                    raise AssertionError('join duration is not OS-representable')
                try:
                    self.target()
                finally:
                    self.alive = False
        with patch.object(setup.threading, 'Thread', LocalWorker), patch.object(
                setup.threading, 'TIMEOUT_MAX', 4):
            self.assertEqual(setup.download_with_deadline(
                lambda: 'local', 'completed', self.root, root=self.root), 'local')
        self.assertEqual(waits, [4])
        self.assertEqual(setup._MODEL_DOWNLOAD_OWNERS, {})

    def test_prewarm_models_preserves_actual_finite_default_and_normal_config(self):
        for label, value in (('default', None), ('normal', .025), ('finite', 1e20)):
            with self.subTest(label=label):
                config = '{}' if value is None else json.dumps({'setup': {
                    'model_warm_timeout_seconds': value}})
                (self.root/'docs/workflow-config.json').write_text(config)
                duration = setup._setup_deadlines(self.root)['model_warm_timeout_seconds']
                self.assertEqual(duration, 1800 if value is None else value)
                release = threading.Event()
                exited = threading.Event()
                calls = []
                def inner(model_name, *, local_files_only):
                    calls.append(local_files_only)
                    if local_files_only:
                        return
                    try:
                        if not release.wait(2):
                            raise AssertionError('prewarm worker was not released')
                    finally:
                        exited.set()
                timer = threading.Timer(.05, release.set)
                timer.start()
                try:
                    with patch.object(setup, '_ACTIVE_MODEL_WARM_DEADLINE_SECONDS', duration), patch.object(
                            setup, '_warm_model_inner', side_effect=inner), patch.object(
                            setup, '_indexer_models', return_value=['local/model']), patch.object(
                            setup, '_model_cache_corruption_reason', return_value=None):
                        started = time.monotonic()
                        if label == 'normal':
                            with self.assertRaises(setup.ModelPrewarmTimeout):
                                setup.prewarm_models(include_code=False)
                            self.assertEqual(calls, [False])
                        else:
                            self.assertIsNone(setup.prewarm_models(include_code=False))
                            self.assertEqual(calls, [False, True])
                        self.assertLess(time.monotonic()-started, 1)
                finally:
                    release.set()
                    timer.join(2)
                    self.assertTrue(exited.wait(2))
                    for thread in threading.enumerate():
                        if thread.name == 'wavefoundry-model-warm':
                            thread.join(2)
                            self.assertFalse(thread.is_alive())

    def test_legacy_wait_slices_preserve_original_budget_and_timeout_object(self):
        clock = [100.]
        waits = []
        timeout = setup.ModelPrewarmTimeout('bounded legacy wait')
        class LocalWorker:
            def __init__(self, **kw): pass
            def start(self): pass
            def is_alive(self): return True
            def join(self, duration):
                waits.append(duration)
                if len(waits) > 4:
                    raise AssertionError('legacy wait loop restarted its budget')
                if not 0 < duration <= 4:
                    raise AssertionError('legacy join duration is not OS-representable')
                clock[0] += duration
        with patch.object(setup.threading, 'Thread', LocalWorker), patch.object(
                setup.threading, 'TIMEOUT_MAX', 4), patch.object(
                setup.time, 'monotonic', side_effect=lambda: clock[0]):
            with self.assertRaises(setup.ModelPrewarmTimeout) as caught:
                setup._run_in_process_with_deadline(
                    lambda: None, deadline_seconds=10, timeout_error=timeout)
        self.assertIs(caught.exception, timeout)
        self.assertEqual(waits, [4, 4, 2])
        self.assertEqual(clock[0], 110)

    def test_legacy_finite_wait_finishes_promptly_preserving_none_and_exception(self):
        for exception in (None, ValueError('ordinary legacy error')):
            with self.subTest(exception=exception):
                waits = []
                class LocalWorker:
                    def __init__(self, *, target, **kw):
                        self.target = target
                        self.alive = True
                    def start(self): pass
                    def is_alive(self): return self.alive
                    def join(self, duration):
                        waits.append(duration)
                        if not 0 < duration <= 4:
                            raise AssertionError('legacy join duration is not OS-representable')
                        try:
                            self.target()
                        finally:
                            self.alive = False
                def work():
                    if exception is not None:
                        raise exception
                    return 'discarded result'
                with patch.object(setup.threading, 'Thread', LocalWorker), patch.object(
                        setup.threading, 'TIMEOUT_MAX', 4):
                    if exception is None:
                        self.assertIsNone(setup._run_in_process_with_deadline(
                            work, deadline_seconds=1e20, timeout_error=TimeoutError()))
                    else:
                        with self.assertRaises(ValueError) as caught:
                            setup._run_in_process_with_deadline(
                                work, deadline_seconds=1e20, timeout_error=TimeoutError())
                        self.assertIs(caught.exception, exception)
                self.assertEqual(waits, [4])

    def test_partial_repo_real_resolver_redownloads_after_worker_exit(self):
        repo=self.root/'cache/models--partial--model'
        (repo/'blobs').mkdir(parents=True); (repo/'blobs/weights.incomplete').write_bytes(b'partial')
        tok=repo/'snapshots/rev/tokenizer.json';tok.parent.mkdir(parents=True);tok.write_text('{}')
        work, release, exited = self.blocking()
        before={str(p.relative_to(repo)):p.read_bytes() for p in repo.rglob('*') if p.is_file()}
        with self.assertRaises(setup.ModelDownloadDeadline):
            setup.download_with_deadline(work,'partial/model',self.root/'cache',root=self.root)
        self.assertEqual(before,{str(p.relative_to(repo)):p.read_bytes() for p in repo.rglob('*') if p.is_file()})
        release.set(); self.assertTrue(exited.wait(2))
        for thread in threading.enumerate():
            if thread.name=='wavefoundry-model-download-deadline':thread.join(2)
        calls=[]
        def embed(**kw):
            calls.append(kw.get('local_files_only', False))
            if kw.get('local_files_only', False): raise RuntimeError('no weights')
            (tok.parent/'model.onnx').write_bytes(b'weights')
        with patch.dict(sys.modules, {'fastembed':types.SimpleNamespace(TextEmbedding=embed)}), setup.model_download_root(self.root):
            path=accel._resolve_model_files('partial/model')
        self.assertTrue(Path(path[0]).is_file());self.assertEqual(calls,[True,False])
        self.assertEqual((repo/'blobs/weights.incomplete').read_bytes(),b'partial')

    def test_scope_optout_error_restoration_missing_constant_and_defaults(self):
        with patch.dict(os.environ,{'HF_HUB_DISABLE_XET':'0'}):
            with setup._hf_hub_timeout_scope(): self.assertFalse(self.constants.HF_HUB_DISABLE_XET)
        with self.assertRaises(ValueError):
            setup.download_with_deadline(lambda: (_ for _ in ()).throw(ValueError('ordinary')), 'm',self.root,root=self.root)
        self.assertFalse(self.constants.HF_HUB_DISABLE_XET)
        del self.constants.HF_HUB_DISABLE_XET
        with contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(setup.download_with_deadline(lambda:'p','m',self.root,root=self.root),'p')
        self.assertIn('no HF_HUB_DISABLE_XET constant',output.getvalue())
        self.assertEqual(setup._setup_deadlines(None)['model_warm_timeout_seconds'],1800)
        self.assertIsNone(setup._run_in_process_with_deadline(lambda:'discarded',deadline_seconds=.1,timeout_error=TimeoutError()))

    def test_required_resolver_and_builder_catches_preserve_deadline(self):
        for resolve in (accel._resolve_clean_onnx, accel._resolve_embedder_cpu_files):
            with patch.object(accel, '_hf_download_cached_first', side_effect=setup.ModelDownloadDeadline('expired')):
                with self.assertRaises(setup.ModelDownloadDeadline): resolve('Snowflake/snowflake-arctic-embed-s')
        with patch.dict(sys.modules, {'onnx':types.SimpleNamespace(), 'onnxruntime':types.SimpleNamespace(), 'tokenizers':types.SimpleNamespace()}), patch.object(accel.venv_bootstrap,'disable_onnxruntime_telemetry'), patch.object(accel,'StaticShapeEmbedder',side_effect=setup.ModelDownloadDeadline('expired')), patch.object(accel,'_available_gpu_providers',return_value=[]), patch.object(accel,'_warn_cuda12_gap_if_present'):
            for providers in ([], ['CUDAExecutionProvider']):
                with self.assertRaises(setup.ModelDownloadDeadline): accel.make_embedder('m', providers)

    def test_optional_gpu_and_background_consumers_log_and_continue(self):
        import server_impl as srv
        with patch.object(setup.provider_policy,'select_embedding_providers',return_value=types.SimpleNamespace(providers=[])), patch.object(setup,'_indexer_reranker_model',return_value='rerank'), patch.object(accel,'make_reranker',side_effect=setup.ModelDownloadDeadline('optional rerank')), patch.object(accel,'make_embedder',side_effect=[setup.ModelDownloadDeadline('optional embed'),None]) as embed, contextlib.redirect_stdout(io.StringIO()) as output:
            setup._prewarm_gpu_accel(['first','second'])
        self.assertIn('optional embed',output.getvalue()); self.assertEqual(embed.call_count,2)
        index=srv.WaveIndex(self.root)
        with patch.dict(os.environ, {'HF_HUB_OFFLINE':'0'}), patch.object(index,'_indexer_constant',side_effect=['first','second','rerank']), patch.object(srv,'_ensure_model_cached',side_effect=[setup.ModelDownloadDeadline('optional background'), None, None]) as cache, patch.object(srv,'_wf_log') as log:
            index._start_background_model_downloads()
            for thread in threading.enumerate():
                if thread.name=='wavefoundry-model-download': thread.join(2); self.assertFalse(thread.is_alive())
        self.assertEqual(cache.call_count,3)
        self.assertIn('optional background',str(log.call_args_list))
        self.assertEqual(cache.call_args_list[0].kwargs['root'],self.root)

    def test_missing_xet_constant_still_times_out(self):
        del self.constants.HF_HUB_DISABLE_XET
        work, _, _ = self.blocking()
        with contextlib.redirect_stderr(io.StringIO()) as output:
            with self.assertRaises(setup.ModelDownloadDeadline): setup.download_with_deadline(work,'no-constant',self.root,root=self.root)
        self.assertIn('deadline remains enforced',output.getvalue())



class FreshEntryXetTests(unittest.TestCase):
    def test_clean_entry_defaults_and_operator_optout(self):
        for module in ('venv_bootstrap','setup_index','accel_embedder','indexer','wf_server.server_impl'):
            for value in (None,'0'):
                with self.subTest(module=module,value=value):
                    env=dict(os.environ, PYTHONPATH=str(SCRIPTS), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
                    env.pop('HF_HUB_DISABLE_XET',None)
                    if value is not None:env['HF_HUB_DISABLE_XET']=value
                    code=f'import {module}; from huggingface_hub import constants; assert constants.HF_HUB_DISABLE_XET is {value is None}'
                    result=subprocess.run([sys.executable,'-B','-c',code],env=env,capture_output=True,text=True,timeout=30)
                    self.assertEqual(result.returncode,0,result.stderr)


class ReloadDownloadOwnershipTests(unittest.TestCase):
    def test_registered_public_reload_preserves_canonical_owner(self):
        probe = "import asyncio, tempfile, threading, json, sys, os\nfrom pathlib import Path\nimport setup_index as s\nfrom unittest.mock import patch\nimport server\nwith tempfile.TemporaryDirectory() as td:\n root=Path(td);(root/'docs').mkdir();(root/'docs/workflow-config.json').write_text(json.dumps({'setup':{'model_warm_timeout_seconds':.02}}))\n release=threading.Event()\n with patch.object(s,'ensure_ca_bundle_applied'), patch.object(s,'retry_with_ca_bundle_ladder',side_effect=lambda f,m:f()):\n  try:s.download_with_deadline(lambda:release.wait(5),'repo/model',root/'cache',root=root)\n  except s.ModelDownloadDeadline:pass\n  try:\n   mcp=server.build_server(root)\n   result=asyncio.run(mcp._tool_manager._tools['wf_reload_mcp'].fn())\n   print(result['status'])\n   import setup_index\n   assert setup_index is s\n   assert __import__('server_impl') is __import__('wf_server.server_impl',fromlist=['x'])\n   try:s.download_with_deadline(lambda:None,'REPO/MODEL',root/'cache',root=root)\n   except s.ModelDownloadDeadline:print('guard retained')\n   else:raise AssertionError('second writer')\n  finally:\n   release.set()\n   for thread in threading.enumerate():\n    if thread.name=='wavefoundry-model-download-deadline':thread.join(2)\n"
        env=dict(os.environ, PYTHONPATH=str(SCRIPTS), HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
        result=subprocess.run([sys.executable,"-B","-c",probe],env=env,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("guard retained",result.stdout)
