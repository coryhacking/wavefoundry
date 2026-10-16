"""Small rerun follow-ups through actual server and compatibility entry points."""
from pathlib import Path
import builtins
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import record_paths
import vocabulary_profile
import review_evidence
from server_tools_support import load_server


class MemoryRerankerExceptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = load_server()

    def test_error_before_provider_import_degrades(self):
        import inference_provider
        obj = object.__new__(self.server.WaveIndex)
        original = builtins.__import__
        def refuse_tensorwell(name, *args, **kwargs):
            if name == 'tensorwell_client':
                raise ImportError('fixture early failure')
            return original(name, *args, **kwargs)
        with patch.dict(os.environ, {'WAVEFOUNDRY_DISABLE_RERANKER': ''}), \
                patch.object(builtins, '__import__', side_effect=refuse_tensorwell), \
                patch.object(obj, '_inference_selection', side_effect=lambda role, result, reason: reason):
            self.assertEqual(obj._get_memory_reranker(), 'local_model_unavailable')

    def test_provider_unavailable_still_propagates(self):
        import inference_provider
        obj = object.__new__(self.server.WaveIndex)
        error = inference_provider.ProviderUnavailable()
        with patch.dict(os.environ, {'WAVEFOUNDRY_DISABLE_RERANKER': ''}), \
                patch.object(obj, '_indexer_constant', return_value='model'), \
                patch.object(inference_provider, 'select_reranker', side_effect=error):
            with self.assertRaises(inference_provider.ProviderUnavailable) as raised:
                obj._get_memory_reranker()
        self.assertIs(raised.exception, error)


class OpenScopeDiscoveryTests(unittest.TestCase):
    def test_one_discovery_for_each_cached_and_uncached_guard(self):
        server = load_server()
        record_paths = server.record_paths
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(record_paths, 'NESTED', True), \
                patch.object(record_paths, 'OPEN_CONTAINER_SCOPE', 'parent'):
            root = Path(tmp).resolve()
            paths = []
            for parent, name, status in [('a', '00001 first', 'active'),
                                         ('b', '00002 second', 'implementing'),
                                         ('c', '00003 target', 'planned')]:
                folder = record_paths.load_record_roots(root).waves / parent / name
                folder.mkdir(parents=True)
                record = folder / vocabulary_profile.RECORD_FILENAME
                record.write_text(f'Status: {status}\n')
                paths.append(record)
            cache = server.McpRepoCache(root)
            for selected_cache in (None, cache, cache):
                with self.subTest(cached=selected_cache is not None), \
                        patch.object(record_paths, 'discover_wave_dirs', wraps=record_paths.discover_wave_dirs) as discover:
                    self.assertIsNone(server._find_other_active_wave(root, paths[2], selected_cache))
                    self.assertEqual(discover.call_count, 1)



if __name__ == '__main__':
    unittest.main()
