"""Public statistics preserve project bytes and canonical index records."""
from __future__ import annotations

import asyncio
import contextlib
import io
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from unittest.mock import patch

from test_tool_surface_golden import _BootedSurface
from test_project_stats import build_index_fixture, tree_bytes, write


def logical_index(directory):
    """Read a private copy: the assertion itself cannot touch source sidecars."""
    import index_state_store as state
    import sqlite_runtime
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / 'index'
        shutil.copytree(directory, target)
        connection = sqlite_runtime.connect(state.state_store_path(target), read_only=True)
        try:
            schema = list(connection.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"))
            records = {}
            for kind, name, _, sql in schema:
                if kind != 'table' or (sql or '').upper().startswith('CREATE VIRTUAL TABLE'):
                    continue
                records[name] = sorted(list(connection.execute('SELECT * FROM "' + name.replace('"', '""') + '"')), key=repr)
            return schema, records
        finally:
            connection.close()


def unexpected_changes(before, after, db_path):
    # This fixture has no finished log/state, so neither refresh nor cleanup
    # is justified here. Only SQLite's physical bookkeeping may vary.
    allowed = {db_path, db_path + '-wal', db_path + '-shm'}
    return sorted(key for key in before.keys() | after.keys()
                  if before.get(key) != after.get(key) and key not in allowed)


class StatisticsIndexSurfaceTests(_BootedSurface):
    def invoke(self, surface):
        import wf_cli
        with patch.object(subprocess, 'Popen', side_effect=AssertionError('statistics spawned subprocess')) as spawn:
            if surface == 'mcp':
                result = asyncio.run(self.mcp._tool_manager._tools['wf_stats'].run({'sections': ['index', 'token_savings']}))
                if hasattr(result, 'structured_content'):
                    result = result.structured_content
                self.assertEqual(result['status'], 'ok', result)
                payload = result['data']
            else:
                output = io.StringIO()
                with patch.object(wf_cli.venv_bootstrap, 'activate_tool_venv'), patch.object(sys, 'argv', list(sys.argv)), contextlib.redirect_stdout(output):
                    status = wf_cli.main(['stats', '--root', str(self.root), '--section', 'index', '--section', 'token_savings', '--json'])
                self.assertEqual(status, 0)
                payload = json.loads(output.getvalue())
            spawn.assert_not_called()
        return payload['sections']

    def test_no_index_both_surfaces_leave_every_byte_unchanged(self):
        before = tree_bytes(self.root)
        for surface in ('mcp', 'cli'):
            with self.subTest(surface=surface):
                result = self.invoke(surface)
                self.assertFalse(result['index']['available'])
                self.assertTrue(result['token_savings']['available'])
                self.assertEqual(tree_bytes(self.root), before)

    def test_populated_index_both_surfaces_preserve_records_and_unrelated_files(self):
        import index_state_store as state
        import context_efficiency as ce
        directory = build_index_fixture(self.root)
        write(self.root, '.wavefoundry/index/unrelated.txt', 'must remain exact\n')
        # A closed WAL-mode store starts with no sidecars; report must never open it.
        path = ce.store_path(self.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as conn:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('CREATE TABLE sentinel(value TEXT)')
            conn.execute("INSERT INTO sentinel VALUES ('keep')")
        conn.close()
        self.assertFalse(Path(str(path) + '-wal').exists())
        db_path = state.state_store_path(directory).relative_to(self.root).as_posix()
        for surface in ('mcp', 'cli'):
            with self.subTest(surface=surface):
                before = tree_bytes(self.root)
                logical = logical_index(directory)
                result = self.invoke(surface)['index']
                self.assertTrue(result['available'], result)
                self.assertEqual((result['embedding']['doc_chunks'], result['embedding']['code_chunks']), (2, 1))
                self.assertEqual(result['lexical']['entries'], 3)
                self.assertEqual((result['graph']['nodes'], result['graph']['edges']), (2, 1))
                self.assertEqual(logical_index(directory), logical)
                self.assertEqual(unexpected_changes(before, tree_bytes(self.root), db_path), [])
                self.assertFalse(Path(str(path) + '-wal').exists())
                self.assertFalse(Path(str(path) + '-shm').exists())

    def test_invalid_and_unreadable_state_stops_before_health_on_both_surfaces(self):
        import dashboard_lib
        directory = build_index_fixture(self.root)
        state = directory / 'index-build.json'
        for contents in ('invalid JSON', '[]', 'null'):
            state.write_text(contents)
            before = tree_bytes(self.root)
            for surface in ('mcp', 'cli'):
                with self.subTest(contents=contents, surface=surface), patch.object(dashboard_lib, 'collect_health', side_effect=AssertionError('health must not read invalid state')) as health:
                    self.assertFalse(self.invoke(surface)['index']['available'])
                    health.assert_not_called()
                    self.assertEqual(tree_bytes(self.root), before)
        original = Path.read_text
        def denied(path, *args, **kwargs):
            if path.resolve() == state.resolve():
                raise PermissionError('state inaccessible')
            return original(path, *args, **kwargs)
        before = tree_bytes(self.root)
        for surface in ('mcp', 'cli'):
            with patch.object(Path, 'read_text', denied), patch.object(dashboard_lib, 'collect_health') as health:
                self.assertEqual(self.invoke(surface)['index']['reason'], 'build_state_unreadable')
                health.assert_not_called()
            self.assertEqual(tree_bytes(self.root), before)

    def test_guard_rejects_unrelated_index_file_mutation(self):
        directory = build_index_fixture(self.root)
        import index_state_store as state
        import project_stats
        target = write(self.root, '.wavefoundry/index/unrelated.txt', 'original')
        before = tree_bytes(self.root)
        original = project_stats._index
        def bad(root):
            result = original(root)
            target.write_text('changed')
            return result
        with patch.object(project_stats, '_index', bad):
            self.invoke('mcp')
        self.assertEqual(unexpected_changes(before, tree_bytes(self.root), state.state_store_path(directory).relative_to(self.root).as_posix()), ['.wavefoundry/index/unrelated.txt'])
