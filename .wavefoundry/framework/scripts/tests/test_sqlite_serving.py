"""Native SQLite serving contracts; no model download or substitute vector engine."""
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sqlite_runtime as runtime
import sqlite_vector_store as vectors
import server_impl as server
import dashboard_lib as dashboard
import retrieval_eval


@unittest.skipIf(runtime.apsw is None, 'qualified APSW runtime unavailable')
class SQLiteServingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / '.wavefoundry' / 'index'
        self.directory.mkdir(parents=True)
        self.conn = runtime.connect(self.directory / vectors.FILENAME)
        self.addCleanup(self.conn.close)
        with self.conn:
            self.conn.execute('CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT)')
            self.conn.execute('INSERT INTO meta VALUES(?,?)', ('store_schema_version', vectors.SCHEMA_VERSION))
            vectors.create_schema(self.conn)
            vectors.write_rows(self.conn, 'docs', [
                self.row('excluded', 'docs/other.md', [1., 0.], kind='doc'),
                self.row('seed', "seeds/it's.md", [.8, .6], kind='seed', text='specific_seed'),
                self.row('seed2', 'seeds/second.md', [0., 1.], kind='seed', text='second_seed'),
                self.row('absent', 'Docs/case.md', [-1., 0.], kind='doc'),
            ])
            vectors.write_rows(self.conn, 'code', [self.row('code', 'src/x.py', [1., 0.], kind='code')])
        self.index = server.WaveIndex(self.root)
        self.index._docs_vector_layer = self.index._proj_docs_vector_layer = 'docs'
        self.index._code_vector_layer = self.index._proj_code_vector_layer = 'code'

    @staticmethod
    def row(identifier, path, components, *, kind, text=None):
        row = dict(id=identifier, path=path, kind=kind, language='python', lines=[2, 4],
                   vector=components + [0.] * 382, section='example', tags='sqlite')
        if text is not None:
            row['text'] = text
        return row

    def assert_filtered(self):
        result = self.index._vector_search('docs', [1.] + [0.] * 383, 1, "kind = 'seed'")
        self.assertEqual([r['id'] for r in result], ['seed'])
        self.assertAlmostEqual(result[0]['score'], .8, places=6)
        self.assertNotIn('vector', result[0])
        self.assertNotIn('_distance', result[0])
        self.assertEqual(result[0]['lines'], [2, 4])

    def _registered_epoch_tools(self):
        class Recorder:
            def __init__(self):
                self._tool_manager = SimpleNamespace(_tools={})

            def tool(self, *args, **kwargs):
                def register(fn):
                    self._tool_manager._tools[kwargs.get("name", fn.__name__)] = fn
                    return fn
                return register(args[0]) if args and callable(args[0]) else register

            def resource(self, *args, **kwargs):
                return lambda fn: fn

        recorder = Recorder()
        handler = SimpleNamespace(root=self.root, index=self.index, background_monitor_status=lambda: {})
        server.register_mcp_surface(recorder, lambda: handler)
        return recorder._tool_manager._tools

    def test_coverage_uses_vector_rows_without_legacy_alias(self):
        import index_state_store as iss
        store = iss.IndexStateStore(self.directory)
        store.close()
        for table in ("docs", "code"):
            iss.rebuild_chunk_index(self.directory, table, vectors.payload_rows(self.directory, table))
        health = self._registered_epoch_tools()["index_health"]
        with patch.object(self.index, "docs_health", return_value={"semantic_ready": True, "layers": {}}):
            response = health()
        self.assertEqual(response["status"], "ok")
        for table, count in (("docs", 4), ("code", 1)):
            coverage = response["data"]["state_store"]["chunk_index"][table]
            self.assertEqual(coverage["vector_rows"], count)
            self.assertEqual(coverage["registry_rows"], count)
            self.assertTrue(coverage["covered"])
            self.assertNotIn("lance_rows", coverage)

        # A fallback reads the last recorded counts, including an unknown raw
        # count. It must expose the same field contract as live coverage.
        iss._record_chunk_sync_counts(self.directory, "docs", 4, 4)
        for count in (4, None):
            if count is None:
                self.conn.execute("DELETE FROM meta WHERE key=?", (iss.META_CHUNK_SYNC_RAW_PREFIX + "docs",))
            with patch.object(server, "_fts_serve_entry", return_value={}), \
                    patch.object(server, "_chunk_index_coverage", return_value={}):
                coverage = server._fts_serving_coverage(self.root, ("docs",), epoch_state=None)
            self.assertEqual(coverage["docs"], {"vector_rows": count, "registry_rows": 4})

    def test_registered_health_errors_offer_cause_specific_recovery(self):
        health = self._registered_epoch_tools()["index_health"]
        advice = "WAL refused; move to local storage and preserve the migration receipt."
        cases = [
            (runtime.RuntimeUnavailable("binding version mismatch"), "storage_runtime_unavailable", "wf setup --root ."),
            (runtime.StorageRecoveryRequired(advice), "storage_recovery_required", advice),
            (OSError("permission denied"), "index_health_error", None),
        ]
        for error, code, expected in cases:
            with self.subTest(code=code), patch.object(self.index, "docs_health", side_effect=error):
                response = health()
            self.assertEqual(response["status"], "error")
            diagnostic = response["diagnostics"][0]
            self.assertEqual(diagnostic["code"], code)
            self.assertIn(str(error), diagnostic["message"])
            self.assertEqual(response["usage"], diagnostic["recovery_usage"])
            self.assertNotIn("setup_wavefoundry.py", str(response))
            if expected:
                self.assertEqual(response["usage"], expected)
            else:
                self.assertIn("Preserve", response["usage"])
                self.assertNotIn("wf setup", str(response))
            if code != "storage_runtime_unavailable":
                self.assertNotIn("index_build", response["next_tools"])
                self.assertNotIn("wf setup", str(response))
            else:
                self.assertIn("restart the MCP host", diagnostic["message"])

    def test_registered_health_actions_match_condition_and_preserve_corruption(self):
        health = self._registered_epoch_tools()["index_health"]
        base = dict(semantic_ready=False, stale_layers=[], missing_layers=[],
                    readiness_overview="needs_update", chunker_version_mismatch_layers=[])
        cases = [
            ({"stale_layers": ["project"]}, {}, "index_stale", "index_build(content='all', mode='update')"),
            ({"chunker_version_mismatch_layers": ["project"], "stale_layers": ["project"]}, {},
             "chunker_version_mismatch", "index_build(content='all', mode='rebuild')"),
            ({"missing_layers": ["project"], "readiness_overview": "absent"}, {},
             "index_missing", "wf setup --root ."),
            ({"readiness_overview": "degraded"}, {}, "index_degraded", "wf setup --root ."),
            ({"stale_layers": ["project"], "chunker_version_mismatch_layers": ["project"]},
             {"integrity": "structural-fail", "fts": {"code": {"ok": False, "reason": "probe_failed", "fts_rows": 3, "registry_rows": 3}}},
             "state_store_structural_fail", None),
            ({"semantic_ready": True, "readiness_overview": "ready"}, {}, None, "docs_search(query='...')"),
        ]
        for values, store, code, expected in cases:
            with self.subTest(code=code), \
                    patch.object(self.index, "docs_health", return_value={**base, **values}), \
                    patch.object(server, "_state_store_health_summary", return_value=store), \
                    patch.object(server, "_index_build_lock_info", return_value={"held": False}), \
                    patch.object(server, "_background_build_status", return_value="none"):
                response = health()
            self.assertEqual(response["status"], "ok")
            self.assertNotIn("setup_wavefoundry.py", str(response))
            if code:
                diagnostic = next(d for d in response["diagnostics"] if d["code"] == code)
                self.assertEqual(diagnostic["recovery_usage"], response["usage"])
            if expected:
                self.assertEqual(response["usage"], expected)
            else:
                self.assertEqual({d["code"] for d in response["diagnostics"]},
                                 {code, "index_stale", "chunker_version_mismatch", "fts_integrity_failed"})
                self.assertTrue(all(d["recovery_usage"] == response["usage"] for d in response["diagnostics"]))
                self.assertIn("Preserve index.sqlite", response["usage"])
                self.assertIn("WAL/SHM", response["usage"])
                self.assertIn("migration receipt", response["usage"])
                self.assertNotIn("index_build", str(response["diagnostics"]))
                self.assertNotIn("index_optimize", str(response))
                self.assertEqual(response["next_tools"], ["wf_help"])
                self.assertEqual(response["data"]["stale_layers"], ["project"])
            if code == "chunker_version_mismatch":
                stale = next(d for d in response["diagnostics"] if d["code"] == "index_stale")
                self.assertEqual(stale["recovery_usage"], expected)

    def _set_registered_epoch(self, status):
        self.conn.execute("CREATE TABLE IF NOT EXISTS build_state (id INTEGER PRIMARY KEY, "
                          "attempt_id TEXT, scope TEXT, status TEXT, generation INTEGER, "
                          "started_at REAL, completed_at REAL)")
        self.conn.execute("DELETE FROM build_state")
        if status is not None:
            self.conn.execute("INSERT INTO build_state VALUES(1,'attempt','all',?,1,0,0)", (status,))

    @staticmethod
    def _registered_requests():
        return {"docs_search": {"query": "specific_seed"},
                "code_search": {"query": "specific_seed", "graph": False},
                "seed_get": {"name": "sample"},
                "code_ask": {"question": "how retrieval works"},
                "wf_map": {"address": "code:src/x.py:L2-L4"},
                "code_lexical": {"query": "specific_seed"}}

    def test_registered_runtime_failure_survives_both_epoch_probes(self):
        tools = self._registered_epoch_tools()
        original_connect = runtime.connect
        self._set_registered_epoch("complete")
        for tool, request in self._registered_requests().items():
            for phase in ("before", "after"):
                for error in (runtime.RuntimeUnavailable("binding missing; run wf setup"),
                              runtime.StorageRecoveryRequired("WAL refused; use local storage")):
                    with self.subTest(tool=tool, phase=phase, error=type(error).__name__):
                        opens = []
                        def fail_at_probe(*args, **kwargs):
                            opens.append(args[0])
                            if phase == "before" or len(opens) == 2:
                                raise error
                            return original_connect(*args, **kwargs)
                        healthy = {"status": "ok", "data": {"results": [{"id": "must-discard"}]}}
                        with patch.object(runtime, "connect", side_effect=fail_at_probe), \
                                patch.object(server, tool + "_response", return_value=healthy) as response_fn, \
                                patch.object(server, "_record_retrieval_context",
                                             side_effect=lambda h, n, r, **kw: r):
                            response = tools[tool](**request)
                        self.assertEqual(len(opens), 1 if phase == "before" else 2)
                        self.assertEqual(response_fn.call_count, 0 if phase == "before" else 1)
                        self.assertEqual(response["status"], "error")
                        self.assertEqual(response["data"]["fallback_reason"], "query_failed")
                        self.assertEqual(response["data"]["results"], [])
                        self.assertEqual(response["diagnostics"][0]["code"], error.code)
                        self.assertIn(str(error), response["diagnostics"][0]["message"])

    def test_registered_epochs_keep_absence_building_transition_and_zero_hit_distinct(self):
        tools = self._registered_epoch_tools()
        strict = {"code_search", "code_ask", "code_lexical"}
        for tool, request in self._registered_requests().items():
            for status in (None, "building", "complete"):
                for transition in (False, True):
                    with self.subTest(tool=tool, status=status, transition=transition):
                        self._set_registered_epoch(status)
                        def response_fn(*args, **kwargs):
                            if transition:
                                self._set_registered_epoch("complete")
                                self.conn.execute("UPDATE build_state SET attempt_id='new',generation=2")
                            return {"status": "ok", "data": {"results": [], "fallback_reason": None}}
                        with patch.object(server, tool + "_response", side_effect=response_fn) as respond, \
                                patch.object(server, "_record_retrieval_context",
                                             side_effect=lambda h, n, r, **kw: r):
                            result = tools[tool](**request)
                        pre_refused = tool in strict and status != "complete"
                        self.assertEqual(respond.call_count, 0 if pre_refused else 1)
                        refused = pre_refused or transition
                        self.assertEqual(result["status"], "error" if refused else "ok")
                        self.assertEqual(result["data"]["fallback_reason"], "index_not_ready" if refused else None)
                        self.assertEqual(result["data"]["results"], [])
                        self.assertFalse(any(d["code"].startswith("storage_")
                                             for d in result.get("diagnostics", [])))

    def test_runtime_failure_is_not_an_absent_layer_or_empty_search(self):
        for error in (runtime.RuntimeUnavailable('native binding missing; run wf setup'),
                      runtime.StorageRecoveryRequired('WAL unavailable; use local storage')):
            with self.subTest(error=type(error).__name__), patch.object(runtime, 'connect', side_effect=error):
                with self.assertRaises(type(error)):
                    self.index._vector_search('docs', [1.] + [0.] * 383, 1)
                with self.assertRaises(type(error)):
                    server._vector_layer_available(self.directory, 'docs')
                with self.assertRaises(type(error)):
                    self.index._open_vector_layer('project', 'docs')
                with self.assertRaises(type(error)):
                    self.index._index_meta_signature(self.directory)
                docs = server.docs_search_response(self.index, 'specific_seed', epoch_state=None)
                code = server.code_search_response(self.index, 'specific_seed', epoch_state=None)
                for response in (docs, code):
                    self.assertEqual(response['data']['fallback_reason'], 'query_failed')
                    self.assertEqual(response['data']['results'], [])
                    messages = ' '.join(d['message'] for d in response['diagnostics'])
                    self.assertIn(str(error), messages)
                    self.assertFalse(any(d['code'] == 'no_results' for d in response['diagnostics']))
                answer = server.code_ask_response(self.index, self.root, 'how retrieval works', epoch_state=None)
                self.assertEqual(answer['data']['fallback_reason'], 'query_failed')
                self.assertTrue(any(str(error) in gap for gap in answer['data']['gaps']))
                health = server.index_health_response(self.index)
                self.assertEqual(health['status'], 'error')
                self.assertEqual(health['diagnostics'][0]['code'], error.code)
                with patch.object(server, 'current_wave', return_value=None), \
                     patch.object(server, 'run_validate', return_value={'passed': True, 'errors': [], 'warnings': []}):
                    audit = server.wf_audit_response(self.root, index=self.index)
                self.assertFalse(audit['data']['index']['metadata_ready'])
                self.assertEqual(audit['data']['index']['readiness_overview'], 'unusable')
                self.assertEqual(audit['data']['index']['error_code'], error.code)
        self.assertFalse(server._vector_layer_available(self.root / 'missing', 'docs'))
        self.assertEqual(self.index._vector_search('docs', [1.] + [0.] * 383, 1, "kind = 'absent'"), [])

    def test_missing_and_mismatched_binding_propagate_from_real_open(self):
        for target, replacement in (('apsw', None), ('APSW_VERSION', '0.0.0')):
            with self.subTest(target=target), patch.object(runtime, target, replacement):
                with self.assertRaises(runtime.RuntimeUnavailable):
                    self.index._index_meta_signature(self.directory)
                with self.assertRaises(runtime.RuntimeUnavailable):
                    server._vector_layer_available(self.directory, 'docs')

    def test_filesystem_preflight_owns_only_disposable_probe(self):
        before = set(self.directory.iterdir())
        self.assertEqual(runtime.preflight(self.directory)['journal_mode'], 'wal')
        self.assertEqual(set(self.directory.iterdir()), before)
        with patch.object(runtime, 'connect', side_effect=runtime.StorageRecoveryRequired('WAL refused')):
            with self.assertRaisesRegex(runtime.StorageRecoveryRequired, 'WAL refused'):
                runtime.preflight(self.directory)
        self.assertEqual(set(self.directory.iterdir()), before)
        self.assert_filtered()

    def test_wal_refusal_is_actionable_and_closes_connection(self):
        from unittest.mock import MagicMock
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = ('delete',)
        with patch.object(runtime.apsw, 'Connection', return_value=conn):
            with self.assertRaisesRegex(runtime.StorageRecoveryRequired, 'local WAL-capable filesystem'):
                runtime.connect(self.directory / 'probe.sqlite')
        conn.close.assert_called_once()

    def test_native_prefilter_cap_cosine_and_payload(self):
        self.assert_filtered()

    def test_docs_search_architecture_prefilters_native_candidates(self):
        # More closer non-architecture rows than the fetch window distinguish
        # true prefiltering from filtering an already-truncated candidate list.
        rows = [self.row(f'decoy-{i}', f'docs/reference/{i}.md', [1., 0.], kind='doc')
                for i in range(server.VECTOR_TOP_K + 1)]
        rows.extend([
            self.row('arch', 'docs/architecture/nested/topic.md', [.8, .6], kind='doc'),
            self.row('hub', 'docs/ARCHITECTURE.md', [.6, .8], kind='doc'),
            self.row('fence', 'docs/architecture/topic.md', [1., 0.], kind='doc-code'),
            self.row('summary', 'docs/architecture/topic.md', [1., 0.], kind='doc-summary'),
            self.row('prefix', 'docs/architecture-extra/topic.md', [1., 0.], kind='doc'),
            self.row('case', 'docs/Architecture/topic.md', [1., 0.], kind='doc'),
        ])
        next(row for row in rows if row['id'] == 'hub')['tags'] = "release's"
        with self.conn:
            vectors.write_rows(self.conn, 'docs', rows)
        # Only model/loading work is stubbed; response routing, predicates,
        # SQLite cosine search and result hydration execute production code.
        with patch.object(self.index, '_start_background_model_downloads_after_startup'), \
                patch.object(self.index, '_ensure_loaded'), \
                patch.object(self.index, '_embed_query', return_value=[1.] + [0.] * 383), \
                patch.object(self.index, '_get_reranker', return_value=None):
            for limit, tags, expected in [
                (2, None, ['arch', 'hub']),
                (1, None, ['arch']),
                (2, ["release's", 'nonexistent'], ['hub']),
                (2, ['nonexistent'], []),
            ]:
                with self.subTest(limit=limit, tags=tags):
                    response = server.docs_search_response(
                        self.index, 'architecture', kind='architecture', limit=limit,
                        tags=tags, epoch_state=(1, 'complete'))
                    self.assertEqual(response['status'], 'ok')
                    self.assertEqual(response['data']['search_mode'], 'semantic')
                    self.assertIsNone(response['data']['fallback_reason'])
                    expected_paths = [next(row['path'] for row in rows if row['id'] == identifier)
                                      for identifier in expected]
                    self.assertEqual([r['path'] for r in response['data']['results']], expected_paths)
            literal = server.docs_search_response(
                self.index, 'architecture', kind='doc-code', limit=1,
                epoch_state=(1, 'complete'))
            self.assertEqual([r['path'] for r in literal['data']['results']],
                             ['docs/architecture/topic.md'])

    def test_dropped_filter_and_cap_negative_controls(self):
        serving_vectors = server._load_script("sqlite_vector_store")
        dense = serving_vectors.dense_rows
        for mutation in ('filter', 'cap'):
            def changed(directory, layer, vector, limit, predicate=None):
                return dense(directory, layer, vector, 10 if mutation == 'cap' else limit,
                             None if mutation == 'filter' else predicate)
            with self.subTest(mutation=mutation), patch.object(serving_vectors, 'dense_rows', changed):
                with self.assertRaises(AssertionError):
                    self.assert_filtered()

    def test_case_sensitive_bound_path_and_payload_presence(self):
        rows = vectors.payload_rows(self.directory, 'docs', "path = 'seeds/it''s.md'")
        self.assertEqual(rows[0]['id'], 'seed')
        self.assertEqual(rows[0]['text'], 'specific_seed')
        rows = vectors.payload_rows(self.directory, 'docs', "path LIKE 'docs/%'")
        self.assertEqual([r['id'] for r in rows], ['excluded'])
        self.assertNotIn('text', rows[0])
        with self.assertRaises(ValueError):
            vectors.payload_rows(self.directory, 'docs', "path = 'x'; DELETE FROM chunks_docs")
        self.assertEqual(vectors.layer_counts(self.directory), {'docs': 4, 'code': 1})

    def test_seed_and_direct_owner_use_real_payloads(self):
        with patch.object(self.index, '_ensure_loaded', return_value=None):
            self.assertEqual(self.index.get_seed("it's")['id'], 'seed')
        rows = self.index._direct_artifact_owner_rows("seeds/it's.md")
        self.assertEqual([r['id'] for r in rows], ['seed'])

    def test_dashboard_counts_and_missing_read_do_not_create_database(self):
        self.assertEqual(dashboard._vector_table_stats(self.directory), (4, 1))
        missing = self.root / 'missing'
        self.assertFalse(server._vector_layer_available(missing, 'docs'))
        self.assertFalse(missing.exists())

    def test_one_missing_vector_is_reported_as_undercoverage(self):
        import index_state_store as iss
        # Add the real control-plane schema/registry around this native fixture.
        store = iss.IndexStateStore(self.directory)
        store.close()
        iss.rebuild_chunk_index(self.directory, "docs", vectors.payload_rows(self.directory, "docs"))
        with self.conn:
            self.conn.execute("DELETE FROM vectors_docs WHERE chunk_id=(SELECT id FROM chunks_docs WHERE chunk_id='seed')")
        coverage = server._chunk_index_coverage(self.root)
        self.assertEqual(coverage["docs"]["vector_rows"], 3)
        self.assertEqual(coverage["docs"]["registry_rows"], 4)
        self.assertFalse(coverage["docs"]["covered"])

    def test_orphan_vector_cannot_hide_behind_equal_joined_counts(self):
        import index_state_store as iss
        store = iss.IndexStateStore(self.directory)
        store.close()
        iss.rebuild_chunk_index(self.directory, 'docs', vectors.payload_rows(self.directory, 'docs'))
        self.conn.execute('PRAGMA foreign_keys=OFF')
        try:
            with self.conn:
                self.conn.execute('INSERT INTO vectors_docs(chunk_id,embedding) VALUES(?,?)',
                                  (999999, vectors.pack_vector([1.] + [0.] * 383)))
        finally:
            self.conn.execute('PRAGMA foreign_keys=ON')
        coverage = server._chunk_index_coverage(self.root)['docs']
        self.assertEqual(coverage['vector_rows'], 4)
        self.assertEqual(coverage['registry_rows'], 4)
        self.assertEqual(coverage['raw_vector_rows'], 5)
        self.assertEqual(coverage['orphan_vectors'], 1)
        self.assertFalse(coverage['covered'])

    def test_capacity_advisory_preserves_ready_state_and_exact_search(self):
        native = server._load_script('sqlite_vector_store')
        with patch.dict(native.QUALIFIED_MAX_ROWS, {'docs': 3, 'code': 50_000}), patch.object(
            self.index, 'docs_health', return_value={'semantic_ready': True, 'layers': {}}
        ):
            response = server.index_health_response(self.index)
        self.assertEqual(response['status'], 'ok')
        self.assertTrue(response['data']['semantic_ready'])
        self.assertFalse(response['data']['capacity']['qualified'])
        self.assertEqual(response['data']['capacity']['exceeded_layers'], ['docs'])
        self.assertIn('capacity_unqualified', [item['code'] for item in response['diagnostics']])
        self.assertEqual(vectors.layer_counts(self.directory), {'docs': 4, 'code': 1})
        self.assert_filtered()

    def test_capacity_evidence_covers_reachable_candidate_windows(self):
        # Raising a public retrieval window requires requalifying the stored
        # latency envelope, even if ordinary golden requests remain smaller.
        self.assertLessEqual(max(server._refill_windows(20)), vectors.QUALIFIED_CANDIDATE_CAPS['code'])
        self.assertLessEqual(max(20 * 4, server.VECTOR_TOP_K), vectors.QUALIFIED_CANDIDATE_CAPS['code'])
        self.assertLessEqual(max(server.VECTOR_TOP_K, server.VECTOR_TOP_K_EXPLANATORY, 20),
                             vectors.QUALIFIED_CANDIDATE_CAPS['docs'])

    def test_shared_backup_contains_committed_wal_and_reopens(self):
        dest = self.root / 'backup.sqlite'
        retrieval_eval._sqlite_backup(self.directory / vectors.FILENAME, dest)
        backup = runtime.connect(dest, read_only=True)
        try:
            self.assertEqual(backup.execute('SELECT count(*) FROM chunks_docs').fetchone(), (4,))
            self.assertEqual(backup.execute("SELECT count(*) FROM fts_docs WHERE fts_docs MATCH 'specific_seed'").fetchone(), (1,))
            self.assertEqual(backup.execute('PRAGMA quick_check').fetchone(), ('ok',))
        finally:
            backup.close()

class SQLiteUpgradeWrapperTests(unittest.TestCase):
    def test_rebuild_storage_is_explicit_and_only_selectable_on_normal_resume(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for selected in (False, True):
                with self.subTest(selected=selected), patch.object(
                    server, '_mcp_subprocess_run', return_value=subprocess.CompletedProcess([], 0, '', '')
                ) as run:
                    server.wf_upgrade_response(root, rebuild_storage=selected)
                    self.assertEqual('--rebuild-storage' in run.call_args.args[0], selected)
            with patch.object(server, '_mcp_subprocess_run') as run:
                for invalid in ('yes', 1, None):
                    self.assertEqual(server.wf_upgrade_response(root, rebuild_storage=invalid)['status'], 'error')
                for phase in ('update_index', 'rebuild_index', 'cleanup', 'resume_after_memory', 'resume_after_gate'):
                    self.assertEqual(server.wf_upgrade_response(root, phase=phase, rebuild_storage=True)['status'], 'error')
                run.assert_not_called()

    def test_operator_confirmation_and_initiating_host_are_forwarded(self):
        import os
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            for confirmed in (False, True):
                with self.subTest(confirmed=confirmed), patch.object(
                    server, '_mcp_subprocess_run', return_value=subprocess.CompletedProcess([], 0, '', '')
                ) as run:
                    server.wf_upgrade_response(Path(temp), confirm_hosts_stopped=confirmed)
                    args, kwargs = run.call_args
                    self.assertEqual('--confirm-hosts-stopped' in args[0], confirmed)
                    self.assertEqual(kwargs['env']['WAVEFOUNDRY_STORAGE_OLD_MCP_PID'], str(os.getpid()))

    def test_confirmation_is_not_coerced_from_a_truthy_string(self):
        with patch.object(server, '_mcp_subprocess_run') as run:
            result = server.wf_upgrade_response(Path('/unused'), confirm_hosts_stopped='yes')
        self.assertEqual(result['status'], 'error')
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()


@unittest.skipIf(runtime.apsw is None, 'qualified APSW runtime unavailable')
class MemoryPreparationTests(unittest.TestCase):
    def setUp(self):
        import index_state_store as iss
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.store = iss.IndexStateStore(self.directory)
        self.addCleanup(self.store.close)

    @staticmethod
    def row(key, text='alpha'):
        return dict(id=key, path=f'src/{key}.py', text=text, kind='code',
                    lines=[1, 2], vector=[1.] + [0.] * 383)

    def contents(self, prepared):
        if prepared.path is None:
            return list(prepared._pending)
        conn = runtime.connect(prepared.path, read_only=True)
        try:
            return conn.execute('SELECT layer,action,payload,vector FROM operations ORDER BY seq').fetchall()
        finally:
            conn.close()

    def publish(self, prepared):
        with self.store._conn:
            prepared.apply(self.store)
        return vectors.payload_rows(self.directory, 'code', include_vector=True)

    def test_default_limit_and_empty_preparation_have_no_disk_effects(self):
        self.assertEqual(vectors.PreparedUpdates.MEMORY_LIMIT_BYTES, 64 * 1024 * 1024)
        with patch.object(vectors.tempfile, 'TemporaryDirectory', side_effect=AssertionError('spool')), \
                patch.object(runtime, 'connect', side_effect=AssertionError('spool connection')):
            with vectors.PreparedUpdates(self.directory) as prepared:
                prepared.add('code')
                with self.store._conn:
                    prepared.apply(self.store)
                self.assertIsNone(prepared.path)

    def test_exact_boundary_then_first_overflow_preserves_order_and_unicode(self):
        operation = ('code', 'id', '猫😀', None)
        base = sys.getsizeof([])
        for offset, spill in ((-1, True), (0, False), (1, False)):
            # SQLite may cache the shared Unicode object's UTF-8 encoding in
            # the preceding spill variant; account its actual allocation now.
            limit = base + vectors.PreparedUpdates._operation_bytes(operation) + offset
            with self.subTest(limit=limit), patch.object(vectors.PreparedUpdates, 'MEMORY_LIMIT_BYTES', limit):
                with vectors.PreparedUpdates(self.directory) as prepared:
                    prepared.add('code', ids=['猫😀'])
                    self.assertEqual(prepared.path is not None, spill)
                    self.assertEqual(self.contents(prepared), [operation])
                    self.assertLessEqual(prepared.peak_retained_bytes, limit)
                    prepared.add('code', ids=['later'])
                    self.assertIsNotNone(prepared.path)
                    self.assertEqual(self.contents(prepared), [operation, ('code', 'id', 'later', None)])
                    self.assertLessEqual(prepared.peak_retained_bytes, limit)

    def test_accounting_covers_real_container_capacity_and_encoded_objects(self):
        with vectors.PreparedUpdates(self.directory) as prepared:
            for n in range(1000):
                prepared.add('code', ids=[str(n) + '😀'])
                actual = sys.getsizeof(prepared._pending) + sum(
                    sys.getsizeof(op) + sum(sys.getsizeof(v) for v in op) for op in prepared._pending)
                self.assertGreaterEqual(prepared.retained_bytes, actual)
            self.assertIsNone(prepared.path)

    def test_oversized_single_row_spills_without_retention(self):
        with patch.object(vectors.PreparedUpdates, 'MEMORY_LIMIT_BYTES', 1024):
            with vectors.PreparedUpdates(self.directory) as prepared:
                prepared.add('code', rows=[self.row('big', '😀' * 10000)])
                self.assertIsNotNone(prepared.path)
                self.assertGreater(prepared.largest_operation_bytes, 1024)
                self.assertLessEqual(prepared.peak_retained_bytes, 1024)
                self.assertEqual(self.publish(prepared)[0]['text'], '😀' * 10000)

    def test_ordered_replace_add_delete_parity_and_caller_rollback(self):
        outputs = []
        for limit in (64 * 1024 * 1024, 0):
            with patch.object(vectors.PreparedUpdates, 'MEMORY_LIMIT_BYTES', limit):
                with vectors.PreparedUpdates(self.directory) as prepared:
                    prepared.add('code', replace=True, rows=[self.row('a'), self.row('b')])
                    prepared.add('code', ids=['a'], rows=[self.row('c')])
                    prepared.add('code', paths=['src/b.py'])
                    outputs.append(self.publish(prepared))
                    self.assertEqual([r['id'] for r in outputs[-1]], ['c'])
                    before = outputs[-1]
                    prepared.add('code', replace=True, rows=[self.row('discard')])
                    with self.assertRaisesRegex(ValueError, 'after writes'):
                        with self.store._conn:
                            prepared.apply(self.store)
                            raise ValueError('after writes')
                    self.assertEqual(vectors.payload_rows(self.directory, 'code', include_vector=True), before)
        self.assertEqual(outputs[0], outputs[1])

    def test_failed_encoder_rolls_back_destructive_prefix_before_and_after_spill(self):
        for limit in (64 * 1024 * 1024, 3000, 0):
            with self.subTest(limit=limit), patch.object(vectors.PreparedUpdates, 'MEMORY_LIMIT_BYTES', limit):
                with vectors.PreparedUpdates(self.directory) as prepared:
                    prepared.add('code', rows=[self.row('keep')])
                    before = self.contents(prepared)
                    def broken():
                        yield self.row('discard')
                        raise ValueError('encoder failed')
                    with self.assertRaisesRegex(ValueError, 'encoder failed'):
                        prepared.add('code', replace=True, rows=broken())
                    self.assertEqual(self.contents(prepared), before)
                    prepared.add('code', rows=[self.row('later')])
                    self.assertEqual({r['id'] for r in self.publish(prepared)}, {'keep', 'later'})
                    # Reset the serving store between variants.
                    with self.store._conn:
                        self.store._conn.execute('DELETE FROM chunks_code')

    def test_spill_faults_preserve_prior_add_or_refuse_uncertain_commit(self):
        original = runtime.connect
        # Fail each transfer boundary: schema, committed prefix, prefix commit,
        # current prefix, remaining stream, and the current add's COMMIT.
        for failure in ('schema', 'insert1', 'commit1', 'insert2', 'insert3', 'commit2', 'rollback'):
            with self.subTest(failure=failure):
                with vectors.PreparedUpdates(self.directory) as prepared:
                    prepared.add('code', ids=['keep'])
                    prior = self.contents(prepared)
                    class FaultConnection:
                        def __init__(self, conn):
                            self.conn = conn
                            self.inserts = self.commits = 0
                        def __getattr__(self, name):
                            return getattr(self.conn, name)
                        def __enter__(self):
                            self.conn.execute('BEGIN')
                            return self
                        def __exit__(self, kind, value, traceback):
                            self.execute('ROLLBACK' if kind else 'COMMIT')
                        def execute(self, sql, *args):
                            if sql.startswith('CREATE TABLE') and failure == 'schema':
                                raise OSError('schema')
                            if sql == 'COMMIT':
                                self.commits += 1
                                if failure == f'commit{self.commits}':
                                    raise OSError(failure)
                            if sql == 'ROLLBACK' and failure == 'rollback':
                                raise OSError('rollback')
                            return self.conn.execute(sql, *args)
                        def executemany(self, sql, values):
                            self.inserts += 1
                            if failure == f'insert{self.inserts}' or (failure == 'rollback' and self.inserts == 3):
                                # Fail after a real write, not before the tested effect.
                                values = list(values)
                                self.conn.executemany(sql, values)
                                raise OSError(failure)
                            return self.conn.executemany(sql, values)
                    limit = prepared.retained_bytes + vectors.PreparedUpdates._operation_bytes(('code', 'replace', None, None))
                    with patch.object(vectors.PreparedUpdates, 'MEMORY_LIMIT_BYTES', limit), \
                            patch.object(runtime, 'connect', side_effect=lambda *a, **k: FaultConnection(original(*a, **k))):
                        with self.assertRaises(OSError):
                            prepared.add('code', replace=True, rows=[self.row('discard')])
                    if failure in ('commit2', 'rollback'):
                        with self.assertRaisesRegex(RuntimeError, 'uncertain'):
                            self.publish(prepared)
                    else:
                        self.assertEqual(self.contents(prepared), prior)
                        prepared.add('code', ids=['later'])
                        self.assertEqual(self.contents(prepared)[-1], ('code', 'id', 'later', None))
                self.assertEqual(list(self.directory.glob('wavefoundry-sqlite-prepared-*')), [])

    def test_concurrent_adds_are_whole_ordered_units(self):
        from concurrent.futures import ThreadPoolExecutor
        for limit in (64 * 1024 * 1024, 2000):
            with patch.object(vectors.PreparedUpdates, 'MEMORY_LIMIT_BYTES', limit):
                with vectors.PreparedUpdates(self.directory) as prepared:
                    def identifiers(n):
                        import time
                        for i in range(25):
                            time.sleep(0.0001)  # release the GIL within each add
                            yield f'{n}-{i}'
                    with ThreadPoolExecutor(max_workers=4) as pool:
                        list(pool.map(lambda n: prepared.add('code', ids=identifiers(n)), range(8)))
                    values = [op[2] for op in self.contents(prepared)]
                    self.assertEqual(len(values), 200)
                    self.assertEqual(len(set(values)), 200)
                    for n in range(8):
                        start = values.index(f'{n}-0')
                        self.assertEqual(values[start:start + 25], [f'{n}-{i}' for i in range(25)])

    def test_spool_connections_close_before_directory_cleanup_on_success_and_failure(self):
        original_connect = runtime.connect
        original_cleanup = tempfile.TemporaryDirectory.cleanup
        for fail in (False, True):
            connections = []
            class Tracked:
                def __init__(self, conn):
                    self.conn, self.closed = conn, False
                    connections.append(self)
                def __getattr__(self, name):
                    return getattr(self.conn, name)
                def __enter__(self):
                    self.conn.__enter__()
                    return self
                def __exit__(self, *args):
                    return self.conn.__exit__(*args)
                def close(self):
                    self.conn.close()
                    self.closed = True
            def cleanup(directory):
                if Path(directory.name).name.startswith('wavefoundry-sqlite-prepared-'):
                    self.assertTrue(connections)
                    self.assertTrue(all(conn.closed for conn in connections))
                return original_cleanup(directory)
            with self.subTest(fail=fail), patch.object(vectors.PreparedUpdates, 'MEMORY_LIMIT_BYTES', 0), \
                    patch.object(runtime, 'connect', side_effect=lambda *a, **k: Tracked(original_connect(*a, **k))), \
                    patch.object(tempfile.TemporaryDirectory, 'cleanup', cleanup):
                try:
                    with vectors.PreparedUpdates(self.directory) as prepared:
                        prepared.add('code', rows=[self.row('kept')])
                        if fail:
                            raise ValueError('after preparation')
                        with self.store._conn:
                            prepared.apply(self.store)
                except ValueError:
                    self.assertTrue(fail)
            self.assertEqual(list(self.directory.glob('wavefoundry-sqlite-prepared-*')), [])

    def test_failed_spill_cleanup_refuses_reuse_and_retries_disposal(self):
        original_cleanup = tempfile.TemporaryDirectory.cleanup
        attempts = []
        def fail_once(directory):
            attempts.append(directory.name)
            if len(attempts) == 1:
                raise OSError('cleanup refused')
            return original_cleanup(directory)
        with vectors.PreparedUpdates(self.directory) as prepared:
            prepared.add('code', ids=['prior'])
            with patch.object(vectors.PreparedUpdates, 'MEMORY_LIMIT_BYTES', 0), \
                    patch.object(runtime, 'connect', side_effect=OSError('open refused')), \
                    patch.object(tempfile.TemporaryDirectory, 'cleanup', fail_once):
                with self.assertRaisesRegex(OSError, 'cleanup refused'):
                    prepared.add('code', ids=['discard'])
            with self.assertRaisesRegex(RuntimeError, 'uncertain'):
                self.publish(prepared)
            with self.assertRaisesRegex(RuntimeError, 'uncertain'):
                prepared.add('code', ids=['later'])
        self.assertEqual(list(self.directory.glob('wavefoundry-sqlite-prepared-*')), [])
