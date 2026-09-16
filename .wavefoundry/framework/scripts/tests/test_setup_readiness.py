"""Read-only bootstrap assessment and real isolated SQLite observations."""
from __future__ import annotations

import json
import ast
import inspect
import io
from contextlib import redirect_stderr, redirect_stdout
import os
from pathlib import Path
import sqlite3
import shutil
import shlex
from types import SimpleNamespace
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import setup_readiness as readiness


class SetupReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.index = self.root / '.wavefoundry/index'
        self.index.mkdir(parents=True)
        target = self.root / '.wavefoundry/framework/scripts'
        target.mkdir(parents=True)
        for name in readiness.SOURCE_FILES:
            shutil.copy2(SCRIPTS / name, target / name)
        (self.root / 'docs').mkdir()
        (self.root / 'docs/workflow-config.json').write_text('{}')
        self.venv = self.root / 'venv'
        python = self.venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        python.parent.mkdir(parents=True)
        python.touch()
        (self.venv / 'pyvenv.cfg').write_text(f'version = {sys.version_info.major}.{sys.version_info.minor}.0')
        self.env = patch.dict(os.environ, {'WAVEFOUNDRY_TOOL_VENV': str(self.venv)})
        self.env.start(); self.addCleanup(self.env.stop)
        readiness._site().mkdir(parents=True)
        self.deps = patch.object(readiness, '_dependencies', return_value=[])
        self.deps.start(); self.addCleanup(self.deps.stop)
        self.database = self.index / 'index.sqlite'
        self.conn = sqlite3.connect(self.database)
        self.addCleanup(self.conn.close)
        self.conn.executescript('CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT); CREATE TABLE build_layer_meta(key TEXT PRIMARY KEY,value TEXT); CREATE TABLE build_state(id INTEGER PRIMARY KEY,status TEXT,generation INTEGER); INSERT INTO build_state VALUES(1,"complete",1);')
        self.versions = readiness._versions()
        for key, value in self.versions.items():
            if key == 'store_schema_version' or key.startswith('graph:'):
                self.conn.execute('INSERT INTO meta VALUES(?,?)', (key, value))
        self.conn.execute('INSERT INTO meta VALUES(?,?)', ('lexical_statistics', json.dumps({'version': int(self.versions['lexical_statistics.version'])})))
        for key, value in {'walker_version': self.versions['walker_version'],
                           'chunker_versions': json.dumps({name: self.versions['chunker_version'] for name in ('docs', 'code')}),
                           'model_versions': json.dumps({name: self.versions[name + '_model'] for name in ('docs', 'code')})}.items():
            self.conn.execute('INSERT INTO build_layer_meta VALUES(?,?)', (key, value))
        self.conn.commit()

    def assess(self, **kwargs):
        return readiness.assess_setup(self.root, **kwargs)

    def test_ready_without_stamp_and_no_application_writes(self):
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = self.assess()
        self.assertEqual(result['status'], 'ready', result)
        self.assertEqual(readiness.exit_code(result), 0)
        after = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertNotIn('sqlite3', readiness.__dict__)

    def test_missing_dependency_checked_despite_matching_stamp(self):
        readiness.write_setup_stamp(self.root)
        with patch.object(readiness, '_dependencies', return_value=['apsw==3.53.4.0']):
            result = self.assess()
        self.assertEqual(result['status'], 'action_required', result)
        self.assertTrue(result['startup_blocked'])
        self.assertEqual(result['actions'][0]['kind'], 'setup')

    def test_old_schema_recommends_setup(self):
        self.conn.execute("UPDATE meta SET value='7' WHERE key='store_schema_version'"); self.conn.commit()
        self.assertEqual(self.assess()['status'], 'action_required')

    def test_newer_schema_suppresses_setup_even_if_dependencies_missing(self):
        self.conn.execute("UPDATE meta SET value='999' WHERE key='store_schema_version'"); self.conn.commit()
        with patch.object(readiness, '_dependencies', return_value=['numpy']):
            result = self.assess()
        self.assertEqual(result['status'], 'indeterminate')
        self.assertEqual(result['actions'], [])

    def test_lexical_producer_newer_is_not_ready(self):
        self.conn.execute("UPDATE meta SET value=? WHERE key='lexical_statistics'", (json.dumps({'version': 999}),)); self.conn.commit()
        self.assertEqual(self.assess()['status'], 'indeterminate')

    def test_stale_loaded_assessor_returns_restart_without_sql_or_setup(self):
        identity = readiness.capture_loaded_identity(); identity['sources']['setup_readiness.py'] = 'old'
        with patch.object(readiness, '_storage_probe', side_effect=AssertionError('SQL should not run')):
            result = self.assess(loaded_identity=identity)
        self.assertEqual(result['status'], 'indeterminate')
        self.assertEqual(result['actions'], [{'kind': 'restart', 'argv': []}])

    def test_timeout_is_indeterminate(self):
        with patch.object(readiness, '_storage_probe', side_effect=subprocess.TimeoutExpired('probe', .01)):
            result = self.assess()
        self.assertEqual(result['status'], 'indeterminate')
        self.assertIn('probe_timeout', [r['code'] for r in result['reasons']])

    def test_real_child_deadline_and_isolation_flags(self):
        with patch.object(readiness, '_SQL_PROBE', 'import time; time.sleep(10)'):
            result = self.assess(timeout_seconds=.05)
        self.assertEqual(result['status'], 'indeterminate')
        with patch.object(readiness.subprocess, 'run', wraps=subprocess.run) as run:
            self.assess()
        self.assertEqual(run.call_args.args[0][1:4], ['-I', '-S', '-B'])

    def test_wal_snapshot_sees_newer_schema_before_checkpoint(self):
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute("UPDATE meta SET value='999' WHERE key='store_schema_version'"); self.conn.commit()
        result = self.assess()
        self.assertEqual(result['status'], 'indeterminate')
        self.assertTrue(any('newer' in item['message'] for item in result['reasons']))

    def test_malformed_ownership_suppresses_setup(self):
        (self.root / '.wavefoundry/upgrade-in-progress.json').write_text('{}')
        with patch.object(readiness, '_dependencies', return_value=['numpy']):
            result = self.assess()
        self.assertEqual(result['status'], 'indeterminate')
        self.assertFalse(any(a['kind'] == 'setup' for a in result['actions']))

    def test_configuration_change_after_stamp_requests_setup(self):
        readiness.write_setup_stamp(self.root)
        (self.root / 'docs/workflow-config.json').write_text('{"indexing":{"include_tests":true}}')
        result = self.assess()
        self.assertEqual(result['status'], 'action_required', result)

    def test_changed_metadata_signature(self):
        path = readiness._site() / 'numpy-1.0.dist-info'
        path.mkdir(); meta = path / 'METADATA'; meta.write_text('Name: numpy\nVersion: 1.0\n')
        before = readiness.assessment_signature(self.root)
        meta.write_text('Name: numpy\nVersion: 2.0\n')
        self.assertNotEqual(before, readiness.assessment_signature(self.root))

    def test_metadata_extras_without_import_or_pth_execution(self):
        self.deps.stop()
        marker = self.root / 'executed'
        (readiness._site() / 'probe.pth').write_text(f'import pathlib; pathlib.Path({str(marker)!r}).touch()')
        for name, version, extra in [('httpx', '0.28.0', 'Provides-Extra: socks\nRequires-Dist: socksio==1.*; extra == "socks"\n'), ('socksio', '1.0.0', '')]:
            path = readiness._site() / f'{name}-{version}.dist-info'; path.mkdir()
            (path / 'METADATA').write_text(f'Name: {name}\nVersion: {version}\n' + extra)
        with patch.object(readiness, 'REQUIRED_IMPORTS', {'httpx[socks]': 'socksio'}), patch.object(readiness, 'GPU_ACCEL_IMPORTS', {}):
            self.assertEqual(readiness._dependencies(), [])
        self.assertFalse(marker.exists())

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'POSIX FIFO fixture')
    def test_fifo_rejected_before_open(self):
        path = self.root / 'fifo'; os.mkfifo(path)
        with patch.object(Path, 'open', side_effect=AssertionError('must reject before open')):
            with self.assertRaises(readiness.ObservationError):
                readiness._read(path)

    def test_provider_canonical_environment_changes_signature(self):
        before = readiness.assessment_signature(self.root)
        with patch.dict(os.environ, {readiness.REQUESTED_PROVIDER_ENV: 'nvidia'}):
            self.assertNotEqual(before, readiness.assessment_signature(self.root))

    def test_other_host_preferences_do_not_change_stamp_projection(self):
        path = self.root / '.codex/config.toml'; path.parent.mkdir()
        entry = '[mcp_servers.wavefoundry]\ncommand="python3"\nargs=' + json.dumps([str(self.root / '.wavefoundry/framework/scripts/server.py'), '--root', str(self.root)])
        path.write_text('model="one"\n' + entry)
        readiness.write_setup_stamp(self.root)
        path.write_text('model="two"\n' + entry)
        self.assertEqual(self.assess()['status'], 'ready')
        path.write_text(entry.replace('python3', 'wrong-python'))
        self.assertEqual(self.assess()['status'], 'action_required')

    def test_different_target_framework_never_ready(self):
        path = self.root / '.wavefoundry/framework/scripts/setup_readiness.py'
        path.write_text(path.read_text() + '\n# changed target\n')
        result = self.assess()
        self.assertEqual(result['status'], 'indeterminate')
        self.assertEqual(result['actions'], [])

    def test_valid_recorded_archive_continuation_preserved(self):
        identity = {'device': self.root.stat().st_dev, 'inode': self.root.stat().st_ino}
        migration_id = 'a' * 32
        pack = str(self.root / 'original.zip')
        argv = [sys.executable, str(self.root / '.wavefoundry/framework/scripts/upgrade_wavefoundry.py'), '--root', str(self.root), '--pack', pack, '--yes', '--confirm-hosts-stopped']
        action = {'root': str(self.root), 'root_identity': identity, 'migration_id': migration_id, 'checkpoint_started_at': 'then', 'command_argv': argv}
        receipt = {'receipt_version': 2, 'kind': 'index_sqlite_schema8', 'state': 'restart_required', 'index_dir': str(self.index), 'root_identity': identity, 'migration_id': migration_id, 'pack_path': pack, 'restart_action': action}
        checkpoint = {'started_at': 'then', 'storage_migration_id': migration_id, 'zip_path': pack, 'action_required': action}
        (self.index / 'sqlite-migration.json').write_text(json.dumps(receipt))
        (self.root / '.wavefoundry/upgrade-in-progress.json').write_text(json.dumps(checkpoint))
        with patch.object(readiness, '_dependencies', return_value=['numpy']):
            result = self.assess()
        self.assertEqual(result['status'], 'action_required', result)
        self.assertEqual(result['actions'], [{'kind': 'resume', 'argv': argv}])
        self.assertTrue(result['startup_blocked'])
        original_interpreter = action['command_argv'][0]
        action['command_argv'][0] = '/tmp/untrusted/python3'
        checkpoint['action_required'] = action
        (self.root / '.wavefoundry/upgrade-in-progress.json').write_text(json.dumps(checkpoint))
        rejected = self.assess()
        self.assertEqual(rejected['status'], 'indeterminate')
        self.assertEqual(rejected['actions'], [])
        action['command_argv'][0] = original_interpreter
        checkpoint['root_identity'] = {'device': -1, 'inode': -1}
        (self.root / '.wavefoundry/upgrade-in-progress.json').write_text(json.dumps(checkpoint))
        self.assertEqual(self.assess()['status'], 'indeterminate')
        del checkpoint['root_identity']
        action['command_argv'] += ['--force']
        checkpoint['action_required'] = action
        (self.root / '.wavefoundry/upgrade-in-progress.json').write_text(json.dumps(checkpoint))
        result = self.assess()
        self.assertEqual(result['status'], 'indeterminate')
        self.assertEqual(result['actions'], [])

    def test_venv_executable_removal_invalidates_signature(self):
        before = readiness.assessment_signature(self.root)
        (self.venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')).unlink()
        self.assertNotEqual(before, readiness.assessment_signature(self.root))
        self.assertTrue(self.assess()['startup_blocked'])

    def test_unsupported_historical_schema_preserved(self):
        self.conn.execute("UPDATE meta SET value='1' WHERE key='store_schema_version'"); self.conn.commit()
        result = self.assess()
        self.assertEqual(result['status'], 'indeterminate')
        self.assertEqual(result['actions'], [])

    def test_newer_legacy_named_database_does_not_recommend_setup(self):
        self.conn.execute("UPDATE meta SET value='999' WHERE key='store_schema_version'"); self.conn.commit()
        self.conn.close()
        self.database.rename(self.index / 'index-state.sqlite')
        result = self.assess()
        self.assertEqual(result['status'], 'indeterminate')
        self.assertEqual(result['actions'], [])

    def test_unreadable_advisory_stamp_does_not_force_setup(self):
        (self.index / 'setup-state.json').write_text('{broken')
        result = self.assess()
        self.assertEqual(result['status'], 'ready', result)
        self.assertTrue(any('stamp is unreadable' in value for value in result['limitations']))

    def test_tampered_ready_stamp_cannot_override_newer_database(self):
        readiness.write_setup_stamp(self.root)
        path = self.index / 'setup-state.json'
        stamp = json.loads(path.read_text()); stamp.update(status='ready', storage_schema_version='8')
        path.write_text(json.dumps(stamp))
        self.conn.execute("UPDATE meta SET value='999' WHERE key='store_schema_version'"); self.conn.commit()
        before = path.read_bytes()
        result = self.assess()
        self.assertEqual(result['status'], 'indeterminate')
        self.assertEqual(path.read_bytes(), before)

    def test_ownership_changed_during_snapshot_never_ready(self):
        original = readiness._storage_probe
        def changing_probe(*args):
            observed = original(*args)
            (self.root / '.wavefoundry/upgrade-in-progress.json').write_text('{}')
            return observed
        with patch.object(readiness, '_storage_probe', side_effect=changing_probe):
            result = self.assess()
        self.assertEqual(result['status'], 'indeterminate')
        self.assertIn('inputs_changed', [r['code'] for r in result['reasons']])
        self.assertEqual(result['actions'], [])

    def test_malformed_database_preserved(self):
        self.conn.close(); self.database.write_bytes(b'not a SQLite database')
        before = self.database.read_bytes()
        result = self.assess()
        self.assertEqual(result['status'], 'indeterminate')
        self.assertEqual(result['actions'], [])
        self.assertEqual(self.database.read_bytes(), before)

    def test_busy_database_returns_indeterminate_without_setup(self):
        self.conn.execute('BEGIN EXCLUSIVE')
        try:
            result = self.assess(timeout_seconds=.5)
        finally:
            self.conn.rollback()
        self.assertEqual(result['status'], 'indeterminate')
        self.assertEqual(result['actions'], [])

    def test_wal_commit_invalidates_monitor_signature(self):
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute("UPDATE meta SET value='7' WHERE key='store_schema_version'"); self.conn.commit()
        before = readiness.assessment_signature(self.root)
        self.conn.execute("UPDATE meta SET value='999' WHERE key='store_schema_version'"); self.conn.commit()
        self.assertNotEqual(before, readiness.assessment_signature(self.root))

    def test_assessment_has_no_product_walk_and_at_most_one_child(self):
        (self.root / 'product').mkdir()
        (self.root / 'product/source.py').write_text('never inspected')
        with patch.object(readiness.os, 'walk', side_effect=AssertionError('product walk')), patch.object(Path, 'rglob', side_effect=AssertionError('recursive walk')), patch.object(readiness.subprocess, 'run', wraps=subprocess.run) as run:
            self.assertEqual(self.assess()['status'], 'ready')
        self.assertEqual(run.call_count, 1)

    def test_command_format_posix_and_windows_are_shell_correct(self):
        argv = ['python3', "C:\\repo space\\O'Brien\\setup.py", '--root', 'root with space']
        result = {'status': 'action_required', 'reasons': [], 'actions': [{'kind': 'resume', 'argv': argv}]}
        with patch.object(readiness, 'os', SimpleNamespace(name='posix')):
            posix = readiness.format_text(result).splitlines()[1]
        self.assertEqual(shlex.split(posix), argv)
        with patch.object(readiness, 'os', SimpleNamespace(name='nt')):
            windows = readiness.format_text(result).splitlines()[1]
        self.assertEqual(windows, '& ' + ' '.join("'" + value.replace("'", "''") + "'" for value in argv))
        self.assertIn("O''Brien", windows)

    def test_real_setup_continuation_requires_checkpoint_root_identity(self):
        from sqlite_storage_migration import restart_command
        identity = {'device': self.root.stat().st_dev, 'inode': self.root.stat().st_ino}
        migration_id = 'b' * 32
        saved_args = ['--root', str(self.root), '--include-tests']
        generated = restart_command(self.root, None, entry_path='setup', setup_args=saved_args)
        action = {'root': str(self.root), 'root_identity': identity, 'migration_id': migration_id,
                  'checkpoint_started_at': 'then', 'entry_path': 'setup', **generated}
        receipt = {'receipt_version': 2, 'kind': 'index_sqlite_schema8', 'state': 'restart_required',
                   'index_dir': str(self.index), 'root_identity': identity, 'migration_id': migration_id,
                   'entry_path': 'setup', 'setup_args': saved_args, 'installed_framework_sha256': 'f' * 64,
                   'restart_action': action}
        checkpoint = {'started_at': 'then', 'storage_migration_id': migration_id,
                      'entry_path': 'setup', 'root_identity': identity, 'action_required': action}
        (self.index / 'sqlite-migration.json').write_text(json.dumps(receipt))
        checkpoint_path = self.root / '.wavefoundry/upgrade-in-progress.json'
        checkpoint_path.write_text(json.dumps(checkpoint))
        result = self.assess()
        self.assertEqual(result['status'], 'action_required', result)
        self.assertEqual(result['actions'], [{'kind': 'resume', 'argv': generated['command_argv']}])
        del checkpoint['root_identity']; checkpoint_path.write_text(json.dumps(checkpoint))
        refused = self.assess()
        self.assertEqual(refused['status'], 'indeterminate')
        self.assertEqual(refused['actions'], [])

    def test_real_renderers_reach_ready_fixed_point_for_all_hosts_twice(self):
        import render_platform_surfaces as renderer
        producers = (
            ('.mcp.json', renderer.render_mcp_json),
            ('.cursor/mcp.json', renderer.render_cursor_mcp_json),
            ('.junie/mcp/mcp.json', renderer.render_junie_mcp_json),
            ('.agents/mcp_config.json', renderer.render_antigravity_mcp_json),
            ('.codex/config.toml', renderer.render_codex_mcp_config),
        )
        for iteration in range(2):
            for relative, produce in producers:
                with self.subTest(iteration=iteration, host=relative):
                    produce(self.root)
                    entry = readiness._surface_entry(self.root, relative)
                    self.assertTrue(readiness._valid_surface_entry(self.root, entry, relative), entry)
                    result = self.assess()
                    self.assertEqual(result['status'], 'ready', result)
            readiness.write_setup_stamp(self.root)

    def test_surface_cwd_root_and_unknown_variables_are_checked(self):
        relative = '.cursor/mcp.json'
        path = self.root / relative; path.parent.mkdir()
        def write(entry):
            path.write_text(json.dumps({'mcpServers': {'wavefoundry': entry}}))
        entry = {'command': 'python3', 'args': ['.wavefoundry/framework/scripts/server.py'], 'cwd': '${workspaceFolder}'}
        write(entry)
        self.assertEqual(self.assess()['status'], 'ready')
        before_signature = readiness.assessment_signature(self.root)
        before_identity = readiness._configuration_identity(self.root)
        entry['cwd'] = str(self.root / 'elsewhere'); write(entry)
        self.assertNotEqual(before_signature, readiness.assessment_signature(self.root))
        self.assertNotEqual(before_identity, readiness._configuration_identity(self.root))
        self.assertEqual(self.assess()['status'], 'action_required')
        entry['cwd'] = str(self.root); entry['args'] += ['--root', str(self.root / 'elsewhere')]; write(entry)
        self.assertEqual(self.assess()['status'], 'action_required')
        entry['args'][-1] = str(self.root); write(entry)
        self.assertEqual(self.assess()['status'], 'ready')
        entry['cwd'] = '${unknownWorkspace}'; write(entry)
        self.assertEqual(self.assess()['status'], 'indeterminate')

    def test_junie_argument_base_is_config_directory(self):
        entry = {'command': 'python3', 'args': ['../../.wavefoundry/framework/scripts/server.py']}
        self.assertTrue(readiness._valid_surface_entry(self.root, entry, '.junie/mcp/mcp.json'))
        self.assertFalse(readiness._valid_surface_entry(self.root, entry, '.mcp.json'))
        entry['args'] = ['.wavefoundry/framework/scripts/server.py']
        self.assertFalse(readiness._valid_surface_entry(self.root, entry, '.junie/mcp/mcp.json'))

    def test_all_canonical_setup_parser_options_survive_real_continuation(self):
        from sqlite_storage_migration import restart_command
        identity = {'device': self.root.stat().st_dev, 'inode': self.root.stat().st_ino}
        migration_id = 'c' * 32

        def assess_saved(saved):
            action = {'root': str(self.root), 'root_identity': identity, 'migration_id': migration_id,
                      'checkpoint_started_at': 'then', 'entry_path': 'setup',
                      **restart_command(self.root, None, entry_path='setup', setup_args=saved)}
            receipt = {'receipt_version': 2, 'kind': 'index_sqlite_schema8', 'state': 'restart_required',
                       'index_dir': str(self.index), 'root_identity': identity, 'migration_id': migration_id,
                       'entry_path': 'setup', 'setup_args': saved, 'installed_framework_sha256': 'f' * 64,
                       'restart_action': action}
            checkpoint = {'started_at': 'then', 'storage_migration_id': migration_id,
                          'entry_path': 'setup', 'root_identity': identity, 'action_required': action}
            (self.index / 'sqlite-migration.json').write_text(json.dumps(receipt))
            (self.root / '.wavefoundry/upgrade-in-progress.json').write_text(json.dumps(checkpoint))
            return self.assess(), action['command_argv']

        # Derive the census from the shared producer grammar rather than mirror
        # a second option allowlist in either the assessor or its regression.
        values = {'--root': str(self.root), '--model-bundle': str(self.root / 'offline models.zip'),
                  '--model-bundle-model-set-version': '7'}
        options = []
        import setup_requirements
        for node in ast.walk(ast.parse(inspect.getsource(setup_requirements.parse_args))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'add_argument':
                flags = [arg.value for arg in node.args if isinstance(arg, ast.Constant) and isinstance(arg.value, str)]
                boolean = any(key.arg == 'action' and isinstance(key.value, ast.Constant) and key.value.value == 'store_true' for key in node.keywords)
                for flag in flags:
                    options.append([flag] if boolean else [flag, values[flags[0]]])
        self.assertGreater(len(options), 15)
        for option in options:
            with self.subTest(option=option):
                result, command = assess_saved(['--root', str(self.root), *option])
                self.assertEqual(result['status'], 'action_required', result)
                self.assertEqual(result['actions'], [{'kind': 'resume', 'argv': command}])
        for invalid in (['--unsupported'], ['--force'], ['--no-optimize'], ['--model-bundle'], ['--help']):
            with self.subTest(invalid=invalid):
                stdout, stderr = io.StringIO(), io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    result, _ = assess_saved(invalid)
                self.assertEqual(result['status'], 'indeterminate', result)
                self.assertEqual(result['actions'], [])
                self.assertEqual(stdout.getvalue(), '')
                self.assertEqual(stderr.getvalue(), '')


if __name__ == '__main__':
    unittest.main()
