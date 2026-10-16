"""Distribution adapter contracts through the shared runtime entry points."""
from __future__ import annotations

import asyncio
import importlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import server_tools_support as support

# Synthetic transport only: no endpoints, credentials, model weights or native runtimes.
ADAPTER = '''
import time
import model_bundle
EMBED = {"model": "Snowflake/snowflake-arctic-embed-s", "task": "embedding", "precision_class": "full", "compatibility_fingerprint": model_bundle.EMBEDDING_COMPATIBILITY_FINGERPRINT, "dimensions": 384}
RERANK = {"model": "cross-encoder/ms-marco-MiniLM-L-6-v2", "task": "reranking", "precision_class": "full", "compatibility_fingerprint": model_bundle.EMBEDDING_COMPATIBILITY_FINGERPRINT, "score_type": "raw_logits"}
calls = []
fault = None
def check(deadline):
    assert 0 < deadline - time.monotonic() <= 31
    if fault == "timeout":
        raise TimeoutError("secret-credential /private/endpoint")
def embed(texts, *, role, deadline):
    check(deadline)
    calls.append((role, list(texts)))
    result = {"descriptor": dict(EMBED), "results": [[float(i + 1)] * 384 for i, _ in enumerate(texts)]}
    return corrupt(result)
def rerank(query, texts, *, deadline):
    check(deadline)
    # Simulate two-item transport batches, preserving original ordering and raw scale.
    values = []
    for offset in range(0, len(texts), 2):
        check(deadline)
        values.extend([-4.01, -4., 0., 2.][i % 4] for i in range(offset, min(offset + 2, len(texts))))
    calls.append(("rerank", list(texts)))
    return corrupt({"descriptor": dict(RERANK), "results": values})
def corrupt(result):
    if fault == "identity": result["descriptor"]["compatibility_fingerprint"] = "other"
    if fault == "count": result["results"] = []
    if fault == "shape": result["results"] = [[0.]] * len(result["results"])
    if fault == "nan": result["results"][0] = float("nan")
    if fault == "bool": result["results"][0] = True
    return result
def create_provider(*, deadline):
    check(deadline)
    return {"provider": "synthetic_api", "embedding": dict(EMBED), "reranking": dict(RERANK), "embed": embed, "rerank": rerank}
'''


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.srv = support.load_server()
        self.ip = importlib.import_module('inference_provider')
        self.profile = importlib.import_module('inference_profile')
        self.ext = importlib.import_module('mcp_tool_extensions')
        self.tc = importlib.import_module('tensorwell_client')
        self.indexer = importlib.import_module('indexer')
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.tmp)
        (self.root / 'synthetic_api.py').write_text(ADAPTER)
        self.enterContext(patch.object(self.ip, '__file__', str(self.root / 'inference_provider.py')))
        self.enterContext(patch.object(self.profile, 'PROVIDER', 'extension'))
        self.enterContext(patch.object(self.profile, 'ADAPTER_MODULE', 'synthetic_api'))
        self.enterContext(patch.object(self.ext, 'EXTENSION_HELPER_MODULES', ('synthetic_api',)))
        sys.modules.pop('synthetic_api', None)
        self.addCleanup(sys.modules.pop, 'synthetic_api', None)
        self.enterContext(patch.dict(os.environ, {'WAVEFOUNDRY_DISABLE_RERANKER': '0', 'HF_HUB_OFFLINE': '1'}))
        for name in ('select_embedder', 'select_reranker', 'start_background'):
            self.enterContext(patch.object(self.tc, name, side_effect=AssertionError('Tensorwell forbidden')))

    def index(self, versions=None):
        obj = self.srv.WaveIndex.__new__(self.srv.WaveIndex)
        obj.root = self.root
        obj._meta = {'project': {'model_versions': versions or {'docs': 'model@full', 'code': 'model@full'}}}
        obj._embedders = {}
        obj._reranker = None
        obj._reranker_lock = threading.Lock()
        obj._indexer_module = lambda: self.indexer
        obj._indexer_constant = lambda key: getattr(self.indexer, key)
        return obj

    def test_shared_consumers_cpu_full_query_roles_and_raw_scores(self):
        import accel_embedder
        import setup_index
        with patch.object(accel_embedder, '_available_gpu_providers', return_value=[]), patch.object(self.indexer, '_onnx_providers', side_effect=AssertionError('local probe forbidden')):
            self.assertEqual(self.indexer._predicted_precision_class(self.indexer.DOCS_MODEL, []), 'full')
            model = self.indexer._get_embedder_inner(self.indexer.DOCS_MODEL)
            self.assertEqual(len(list(model.embed(['a', 'b']))), 2)
            with patch.object(setup_index, '_load_indexer_module', return_value=self.indexer), patch.object(setup_index, '_prewarm_required_model', side_effect=AssertionError('local warm forbidden')):
                setup_index.prewarm_models(include_code=True)
                self.assertEqual(setup_index._prewarm_gpu_accel([self.indexer.DOCS_MODEL]), [])
        obj = self.index()
        raw = 'Represent this sentence for searching relevant passages: already-prefixed'
        self.assertEqual(obj._embed_query(raw, self.indexer.DOCS_MODEL).shape, (384,))
        adapter = sys.modules['synthetic_api']
        self.assertIn(('query', [raw]), adapter.calls)
        self.assertEqual(obj._get_memory_reranker().rerank('q', ['a', 'b', 'c', 'd']), [-4.01, -4., 0., 2.])
        candidates = [{'text': str(i)} for i in range(8)]
        self.assertTrue(obj._agent_rerank('q', candidates))
        for i, candidate in enumerate(candidates):
            self.assertAlmostEqual(candidate['score'], 1 / (1 + math.exp(-[-4.01, -4., 0., 2.][i % 4])))
        status = self.tc.inference_status_snapshot()
        self.assertEqual(status['roles']['query_embedding']['last_success']['provider'], 'synthetic_api')
        self.assertFalse(getattr(model, 'is_tensorwell', False))
        self.ip.start_background(self.root)

    def test_cpu_full_build_publication_and_implicit_migration_gate(self):
        import test_indexer as ix_tests
        import index_state_store
        import accel_embedder
        root = self.root / 'build'; root.mkdir()
        ix_tests._make_repo(root, {'docs/guide.md': '# Guide\n\nSynthetic content.\n'})
        with patch.object(self.indexer, '_onnx_providers', return_value=['CPUExecutionProvider']), patch.object(accel_embedder, '_available_gpu_providers', return_value=[]), patch.object(self.indexer, '_text_embedding_cached_first', side_effect=AssertionError('local model')), patch.object(accel_embedder, 'make_embedder', side_effect=AssertionError('local model')):
            result = self.indexer.build_index(root, full=True, content='docs', verbose=False)
            self.assertFalse(result.get('failed'), result)
            directory = root / self.indexer.INDEX_DIR_NAME
            meta = index_state_store.export_meta_snapshot(directory)
            self.assertEqual(meta['model_versions']['docs'], self.indexer.DOCS_MODEL + '@full@' + self.indexer.EMBEDDING_MODEL_SET_FINGERPRINT)
            self.assertEqual(self.indexer._implicit_precision_changes(directory), [])
            # The same comparison refuses a stored INT8 class; no implicit conversion.
            prior = dict(meta, model_versions={'docs': self.indexer.DOCS_MODEL + '@int8@old'})
            with patch.object(self.indexer, '_load_meta', return_value=prior):
                self.assertEqual(self.indexer._implicit_precision_changes(directory)[0]['requested'], 'full')

    def test_memory_public_cutoff_preserves_raw_logit_scale(self):
        from test_memory_records import _MemoryCase
        case = _MemoryCase(); case.setUp(); self.addCleanup(case.doCleanups)
        paths = [case._add(f'mem-{i}', 'review_finding') for i in range(4)]
        obj = self.index(); obj.root = case.root
        obj._ensure_loaded = lambda: None; obj._docs_vector_layer = 'docs'
        obj._memory_candidate_scores = lambda *a, **kw: {'complete': True, 'scores': {p.relative_to(case.root).as_posix(): 1-i/100 for i,p in enumerate(paths)}}
        result = self.srv.memory_search_response(case.root, query='semantic-only', index=obj)
        self.assertEqual(result['data']['retrieval']['qualification'], 'model_relevance')
        self.assertEqual(result['data']['retrieval']['checked_candidates'], 4)
        self.assertEqual(result['data']['count'], 3, result)

    def test_explicit_selection_never_falls_back_for_partial_or_incompatible(self):
        for versions in ({'docs': 'model@int8', 'code': 'model@int8'}, {'docs': 'model@int8', 'code': 'model@full'}):
            with self.subTest(versions=versions), self.assertRaises(self.ip.ProviderUnavailable):
                self.index(versions)._get_embedder(self.indexer.DOCS_MODEL)
        self.ip.select_embedder(self.indexer.DOCS_MODEL)
        adapter = sys.modules['synthetic_api']
        original = adapter.create_provider
        for field in ('embedding', 'reranking', 'embed', 'rerank'):
            def partial(*, deadline, field=field):
                result = original(deadline=deadline); result.pop(field); return result
            self.ip._cache_until = 0
            with patch.object(adapter, 'create_provider', partial), self.assertRaises(self.ip.ProviderUnavailable):
                self.index()._get_memory_reranker()
        with self.assertRaises(self.ip.ProviderUnavailable):
            self.ip.select_embedder('different-model')

    def test_response_guards_and_timeout_are_safe_no_retry(self):
        model = self.ip.select_reranker(self.indexer.RERANKER_MODEL)
        adapter = sys.modules['synthetic_api']
        for fault in ('identity', 'count', 'shape', 'nan', 'bool', 'timeout'):
            adapter.fault = fault
            with self.subTest(fault=fault), self.assertRaises(self.ip.ProviderUnavailable) as caught:
                model.rerank('secret-query', ['secret-document'])
            self.assertNotIn('secret', str(caught.exception))
            self.assertIsNone(caught.exception.__cause__)
        adapter.fault = None
        model = self.ip.select_embedder(self.indexer.DOCS_MODEL)
        adapter.fault = 'shape'
        with self.assertRaises(self.ip.ProviderUnavailable): list(model.embed(['a']))
        adapter.fault = None
        def late(texts, *, role, deadline):
            time.sleep(0.01)
            return {'descriptor': dict(adapter.EMBED), 'results': [[0.] * 384 for _ in texts]}
        model._provider['embed'] = late
        with patch.object(self.tc, 'INFERENCE_SECONDS', 0.001), self.assertRaises(self.ip.ProviderUnavailable):
            list(model.embed(['a']))

    def test_background_preparation_and_factory_failure_never_load_local(self):
        obj = self.index(); obj._model_downloads_started = False
        class InlineThread:
            def __init__(self, *, target, **kwargs): self.target = target
            def start(self): self.target()
        with patch.dict(os.environ, {'HF_HUB_OFFLINE': '0'}), patch.object(threading, 'Thread', InlineThread), patch.object(self.srv, '_ensure_model_cached') as local:
            obj._start_background_model_downloads()
            local.assert_not_called()
        adapter = sys.modules['synthetic_api']
        self.ip._cache_until = 0
        with patch.object(adapter, 'create_provider', side_effect=TimeoutError('secret-credential /private/endpoint')):
            with self.assertRaises(self.ip.ProviderUnavailable) as caught:
                obj._get_memory_reranker()
            self.assertNotIn('secret', str(caught.exception))
            self.assertNotIn('/private', str(caught.exception))

    def test_selection_cache_and_generation_invalidation(self):
        first = self.ip.select_embedder(self.indexer.DOCS_MODEL)
        adapter = sys.modules['synthetic_api']
        with patch.object(adapter, 'create_provider', wraps=adapter.create_provider) as factory:
            self.ip.extension_precision(self.indexer.DOCS_MODEL)
            self.ip.select_reranker(self.indexer.RERANKER_MODEL)
            factory.assert_not_called()
            self.ip._cache_until = 0
            self.ip.select_reranker(self.indexer.RERANKER_MODEL)
            factory.assert_called_once()
        with patch.object(self.tc, '_generation', self.tc._generation + 1), self.assertRaises(self.ip.ProviderUnavailable):
            first.embed_query('raw')
        with patch.object(self.tc, '_generation', self.tc._generation + 1), patch.object(self.ext, 'EXTENSION_HELPER_MODULES', ()), self.assertRaises(self.ip.ProviderUnavailable):
            self.ip.select_embedder(self.indexer.DOCS_MODEL)

    def test_declaration_validation_once_per_generation_across_batches(self):
        with patch.object(self.tc, '_generation', self.tc._generation + 1), patch.object(self.ext, '_module_name_problems', wraps=self.ext._module_name_problems) as validate:
            embedder = self.ip.select_embedder(self.indexer.DOCS_MODEL)
            reranker = self.ip.select_reranker(self.indexer.RERANKER_MODEL)
            initial = validate.call_count
            self.assertGreater(initial, 0)
            for _ in range(20):
                embedder.embed_query('q')
                reranker.rerank('q', ['a', 'b'])
                self.ip.select_embedder(self.indexer.DOCS_MODEL)
                self.ip.mode()
            self.assertEqual(validate.call_count, initial)
            with patch.object(self.tc, '_generation', self.tc._generation + 1):
                self.ip.mode()
                self.assertEqual(validate.call_count, 2 * initial)
                with self.assertRaises(self.ip.ProviderUnavailable):
                    embedder.embed_query('stale')
                with self.assertRaises(self.ip.ProviderUnavailable):
                    reranker.rerank('q', ['stale'])

    def test_declaration_is_strict_and_local_never_starts_daemon(self):
        for name in ('../synthetic_api', 'synthetic_api.sub', 'os', 'inference_provider', ''):
            with patch.object(self.profile, 'ADAPTER_MODULE', name), self.assertRaises(self.ip.ProviderUnavailable):
                self.ip.select_embedder(self.indexer.DOCS_MODEL)
        with patch.object(self.profile, 'PROVIDER', 'local'), patch.object(self.profile, 'ADAPTER_MODULE', ''):
            self.assertIsNone(self.ip.select_embedder(self.indexer.DOCS_MODEL))
            self.assertIsNone(self.ip.select_reranker(self.indexer.RERANKER_MODEL))
            self.ip.start_background(self.root)
        with patch.dict(os.environ, {'WAVEFOUNDRY_DISABLE_RERANKER': '1'}):
            self.assertIsNone(self.ip.select_reranker(self.indexer.RERANKER_MODEL))
        with patch.object(self.profile, 'PROVIDER', 'bogus'), self.assertRaises(self.ip.ProviderUnavailable):
            self.ip.start_background(self.root)



_RELOAD_DRIVER = r'''
import asyncio, importlib, json, sys, threading
from pathlib import Path
scripts, root = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(scripts))
import server
mcp = server.build_server(root)
import inference_provider as ip
import tensorwell_client as tc
import indexer
assert ip.mode() == 'extension'
assert ip.select_embedder(indexer.DOCS_MODEL).embed_query('raw') == [1.] * 384
assert 'onnxruntime' not in sys.modules and 'fastembed' not in sys.modules
async def call(name):
    content, result = await mcp.call_tool(name, {})
    return result or json.loads(next(item.text for item in content if item.type == 'text'))
async def run():
    info = await call('wf_server_info')
    helpers = info['data']['extensions']['helper_modules']
    assert any(row['module'] == 'synthetic_api' for row in helpers), info
    path = scripts / 'synthetic_api.py'
    path.write_text(path.read_text().replace('synthetic_api', 'synthetic_api_v2'))
    result = await call('wf_reload_mcp')
    assert result['status'] == 'ok', result
    import inference_provider as fresh
    assert fresh is not ip
    assert fresh.select_embedder(indexer.DOCS_MODEL).provider_label == 'synthetic_api_v2'
    profile_path = scripts / 'inference_profile.py'
    profile_path.write_text('PROVIDER = "local"\nADAPTER_MODULE = ""\n')
    import hashlib
    new_digest = hashlib.sha256(profile_path.read_bytes()).hexdigest()
    assert server._SETUP_LOADED_IDENTITY['sources']['inference_profile.py'] != new_digest
    before = await call('index_health')
    assert 'loaded_code_stale' in json.dumps(before), before
    result = await call('wf_reload_mcp')
    assert result['status'] == 'ok', result
    import inference_provider as local
    assert server._SETUP_LOADED_IDENTITY['sources']['inference_profile.py'] == new_digest
    after = await call('index_health')
    assert 'loaded_code_stale' not in json.dumps(after), after
    tc.start_background = lambda *a: (_ for _ in ()).throw(AssertionError('daemon startup'))
    assert local.select_embedder(indexer.DOCS_MODEL) is None
    local.start_background(root)
asyncio.run(run())
print('registered provider reload OK')
'''

class RegisteredProviderTests(unittest.TestCase):
    def test_fresh_process_and_registered_reload_refresh_profile_and_helper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); scripts = root / 'scripts'
            shutil.copytree(SCRIPTS, scripts, ignore=shutil.ignore_patterns('tests', '__pycache__', '*.pyc'))
            (scripts / 'synthetic_api.py').write_text(ADAPTER)
            (scripts / 'inference_profile.py').write_text('PROVIDER = "extension"\nADAPTER_MODULE = "synthetic_api"\n')
            declaration = scripts / 'mcp_tool_extensions.py'
            declaration.write_text(declaration.read_text() + '\nEXTENSION_HELPER_MODULES = ("synthetic_api",)\n')
            env = dict(os.environ, HF_HUB_OFFLINE='1', WAVEFOUNDRY_DISABLE_BYTECODE_CACHE='1')
            env.pop('PYTHONPYCACHEPREFIX', None)
            result = subprocess.run([sys.executable, '-B', '-c', _RELOAD_DRIVER, str(scripts), str(root)], env=env, cwd=root, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr[-6000:])
            self.assertIn('registered provider reload OK', result.stdout)

if __name__ == '__main__': unittest.main()
