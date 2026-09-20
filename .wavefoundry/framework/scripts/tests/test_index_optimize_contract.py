"""Exercise maintenance consumers with results from the real SQLite producer."""
import contextlib
import io
import unittest
from unittest.mock import patch

import test_indexer as fixtures
from server_tools_support import load_server
import setup_index


class OptimizeResultContractTests(unittest.TestCase):
    setUp = fixtures.TargetedPublicationContractTests.setUp

    def _failed_optimize(self, consumer):
        server = load_server()
        output = io.StringIO()
        with patch.object(self.iss, 'finalize_build_epoch', return_value=False) as finalize, \
                patch.object(self.iss, 'optimize_state_stores', wraps=self.iss.optimize_state_stores) as maintain, \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            if consumer == 'producer':
                result = self.bi.optimize_index_tables(self.index_dir)
            elif consumer == 'close':
                with patch.object(server, '_load_script', return_value=self.bi), \
                        patch.object(server, '_close_optimize_enabled', return_value=True), \
                        patch.object(server, '_index_table_bloat_ratios', return_value={'docs': 2}):
                    result = server._maybe_optimize_index_on_close(self.root)
            elif consumer == 'mcp':
                with patch.object(server, '_load_script', return_value=self.bi):
                    result = server._index_optimize_response(self.root)
            else:
                with patch.object(setup_index, '_load_indexer_module', return_value=self.bi):
                    result = setup_index._optimize_after_build(self.root)
        finalize.assert_called_once()
        maintain.assert_called_once()
        self.assertEqual('building', self.iss.read_build_state(self.index_dir)['status'])
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))
        return result, output.getvalue(), server

    def test_real_producer_preserves_error_contract(self):
        result, _, server = self._failed_optimize('producer')
        self.assertEqual('epoch finalization CAS miss', result.get('error'))
        self.assertNotIn('failure', result)
        self.assertTrue(result['stores']['index-state']['maintenance_complete'])
        self.assertIn('epoch finalization CAS miss', server._sqlite_maintenance_failure(result))

    def test_close_reports_real_producer_failure(self):
        result, _, _ = self._failed_optimize('close')
        self.assertFalse(result['ran'])
        self.assertIn('epoch finalization CAS miss', result['error'])
        self.assertEqual('optimize_error', result['skipped'])

    def test_mcp_reports_real_producer_failure(self):
        result, _, _ = self._failed_optimize('mcp')
        self.assertEqual('error', result['status'])
        self.assertIn('state_store_maintenance_failed', str(result['diagnostics']))
        self.assertIn('epoch finalization CAS miss', str(result))

    def test_setup_reports_real_producer_failure(self):
        _, output, _ = self._failed_optimize('setup')
        self.assertIn('index optimize skipped: epoch finalization CAS miss', output)
        self.assertNotIn('reclaimed', output)

    def test_successful_optimize_keeps_readers_available(self):
        result = self.bi.optimize_index_tables(self.index_dir)
        self.assertNotIn('error', result)
        self.assertNotIn('failure', result)
        self.assertTrue(result['stores']['index-state']['maintenance_complete'])
        self.assertEqual('complete', self.iss.read_build_state(self.index_dir)['status'])
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))


if __name__ == '__main__':
    unittest.main()
