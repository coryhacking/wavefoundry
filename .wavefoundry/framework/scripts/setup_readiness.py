"""Bounded setup observations, safe before activating the shared tool environment.

No parent SQLite binding, package imports, source-corpus walk, or repair. The
isolated reader permits SQLite's normal coordination sidecars, never data writes.
"""
from __future__ import annotations

import ast
from contextlib import redirect_stderr
import io
import email.parser
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import stat
import subprocess
import sys
import tempfile
import time
import tomllib

import subprocess_util
import venv_bootstrap
import runtime_advisory
from provider_policy import REQUESTED_PROVIDER_ENV, SETUP_SELECTED_ENV

from setup_requirements import REQUIRED_IMPORTS, CUDA_DEPENDENCY_IMPORTS, GPU_ACCEL_IMPORTS, parse_args as parse_setup_args

SCHEMA_VERSION = 1
SCRIPTS = Path(__file__).resolve().parent
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_JSON_BYTES = 256 * 1024
MAX_METADATA_BYTES = 256 * 1024
MAX_ENV_ENTRIES = 4096
SOURCE_FILES = (
    'setup_readiness.py', 'runtime_advisory.py', 'setup_requirements.py', 'setup_wavefoundry.py', 'setup_index.py',
    'setup_reconciliation.py', 'venv_bootstrap.py', 'subprocess_util.py', 'repo_root.py', 'wf_cli.py',
    'server.py', 'server_impl.py', 'index_compatibility.py', 'index_paths.py',
    'index_state_store.py', 'sqlite_vector_store.py', 'sqlite_runtime.py', 'chunker.py',
    'indexer.py', 'graph_indexer.py', 'graph_store.py', 'model_bundle.py',
    'provider_policy.py', 'render_platform_surfaces.py', 'render_agent_surfaces.py',
)
CONFIG_FILES = ('docs/workflow-config.json', '.wavefoundry/framework/VERSION',
                '.wavefoundry/framework/install/workflow-config.defaults.json')
SURFACE_FILES = ('.mcp.json', '.codex/config.toml', '.cursor/mcp.json',
                 '.junie/mcp/mcp.json', '.agents/mcp_config.json',
                 '.wavefoundry/bin/wf', '.wavefoundry/bin/wf.cmd')
OWNERSHIP_FILES = ('.wavefoundry/upgrade-in-progress.json',
                   '.wavefoundry/index/sqlite-migration.json')
STAMP_PATH = '.wavefoundry/index/setup-state.json'
ENV_KEYS = (REQUESTED_PROVIDER_ENV, SETUP_SELECTED_ENV,
            'WAVEFOUNDRY_DISABLE_RERANKER', 'PYTHONPATH', 'VIRTUAL_ENV')
LIMITATIONS = [
    'Setup readiness is not an integrity, search-quality, model-execution or source-freshness audit.',
    'Dependency metadata does not prove native package imports or accelerator availability.',
    'Python interpreter startup customization precedes this check; package .pth files are not executed by it.',
    'SQLite may create or update coordination WAL/SHM files; application data and recovery records are read-only.',
    'The child deadline bounds database probing; parent filesystem calls have no hard wall-clock deadline.',
]


class ObservationError(ValueError):
    pass


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _safe(root: Path, relative: str) -> Path:
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ObservationError(f'path escapes repository: {relative}')
    return path


def _read(path: Path, limit: int = MAX_JSON_BYTES) -> bytes:
    if not stat.S_ISREG(path.stat().st_mode):
        raise ObservationError(f'not a regular file: {path.name}')
    with path.open('rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ObservationError(f'not a regular file: {path.name}')
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ObservationError(f'input exceeds {limit} bytes: {path.name}')
    return data


def _json(path: Path):
    value = json.loads(_read(path))
    if not isinstance(value, dict):
        raise ObservationError(f'expected object: {path.name}')
    return value


def _stat(path: Path):
    try:
        s = path.stat()
        return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns]
    except FileNotFoundError:
        return None


def _venv() -> Path:
    return venv_bootstrap.tool_venv_base()


def _site() -> Path:
    return venv_bootstrap._venv_site_packages(_venv())


def _metadata_paths() -> dict[str, list[Path]]:
    result = {}
    try:
        with os.scandir(_site()) as entries:
            for count, entry in enumerate(entries, 1):
                if count > MAX_ENV_ENTRIES:
                    raise ObservationError('tool environment exceeds bounded entry census')
                if entry.name.endswith('.dist-info'):
                    name = entry.name[:-10].rsplit('-', 1)[0]
                    result.setdefault(re.sub(r'[-_.]+', '-', name).lower(), []).append(Path(entry.path) / 'METADATA')
    except FileNotFoundError:
        pass
    return result


def capture_loaded_identity() -> dict:
    """Capture immutable launch identity before loading producer/runtime modules."""
    values, errors = {}, []
    for name in SOURCE_FILES:
        try:
            values[name] = hashlib.sha256(_read(SCRIPTS / name, MAX_FILE_BYTES)).hexdigest()
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    return {'schema_version': 1, 'sources': values, 'errors': errors}


def assessment_signature(root: Path) -> dict:
    """Bounded monitor signals; no SQL, persistent writes or source-corpus walk."""
    values, errors = {}, []
    try:
        root = Path(root).resolve(strict=True)
        for relative in (*CONFIG_FILES, *SURFACE_FILES, *OWNERSHIP_FILES, STAMP_PATH,
                         '.wavefoundry/index/index.sqlite', '.wavefoundry/index/index.sqlite-wal',
                         '.wavefoundry/index/index-state.sqlite'):
            values[relative] = _stat(_safe(root, relative))
        for name in SOURCE_FILES:
            values['source:' + name] = _stat(SCRIPTS / name)
        values['venv_root'] = str(_venv().resolve())
        values['venv'] = _stat(_venv() / 'pyvenv.cfg')
        values['venv_python'] = _stat(venv_bootstrap.tool_venv_python())
        values['venv_site'] = _stat(_site())
        values['interpreter'] = [sys.executable, sys.version, sys.prefix, getattr(sys, 'abiflags', '')]
        values['environment'] = {key: os.environ.get(key) for key in ENV_KEYS}
        for name, paths in sorted(_metadata_paths().items()):
            values['distribution:' + name] = [[str(p), _stat(p)] for p in paths]
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
    return {'schema_version': 1, 'inputs': values, 'errors': errors}


def _literals(name: str, wanted: set[str]) -> dict:
    result = {}
    source = _read(SCRIPTS / name, MAX_FILE_BYTES).decode('utf-8')
    for declaration in wanted:
        match = re.search(r'^' + re.escape(declaration) + r'\s*=\s*([^\n]+)', source, re.MULTILINE)
        if match:
            result[declaration] = ast.literal_eval(match.group(1))
    if set(result) != wanted:
        raise ObservationError(f'producer declarations missing: {name}')
    return result


def _versions() -> dict:
    state = _literals('index_state_store.py', {'STATE_STORE_SCHEMA_VERSION', 'LEXICAL_STATISTICS_VERSION'})
    graph = _literals('graph_indexer.py', {'GRAPH_STORE_SCHEMA_VERSION', 'GRAPH_SCHEMA_VERSION', 'GRAPH_BUILDER_VERSION'})
    index = _literals('indexer.py', {'WALKER_VERSION', 'DOCS_MODEL', 'CODE_MODEL'})
    chunk = _literals('chunker.py', {'CHUNKER_VERSION'})
    return {'store_schema_version': str(state['STATE_STORE_SCHEMA_VERSION']),
            'graph:store_schema_version': str(graph['GRAPH_STORE_SCHEMA_VERSION']),
            'graph:schema_version': str(graph['GRAPH_SCHEMA_VERSION']),
            'graph:builder_version': str(graph['GRAPH_BUILDER_VERSION']),
            'graph:walker_version': str(index['WALKER_VERSION']),
            'graph:chunker_version': str(chunk['CHUNKER_VERSION']),
            'walker_version': str(index['WALKER_VERSION']),
            'chunker_version': str(chunk['CHUNKER_VERSION']),
            'lexical_statistics.version': str(state['LEXICAL_STATISTICS_VERSION']),
            'docs_model': index['DOCS_MODEL'], 'code_model': index['CODE_MODEL']}


def _requirement(spec: str):
    match = re.fullmatch(r'([A-Za-z0-9_.-]+)(?:\[([A-Za-z0-9_,.-]+)\])?\s*(.*)', spec.strip())
    if not match:
        raise ObservationError(f'unsupported dependency requirement: {spec}')
    name, extras, constraints = match.groups()
    return re.sub(r'[-_.]+', '-', name).lower(), (extras or '').split(','), constraints.replace(' ', '')


def _satisfies(version: str, constraints: str) -> bool:
    if not constraints:
        return True
    if not re.fullmatch(r'\d+(?:\.\d+)*', version):
        raise ObservationError(f'unsupported dependency version: {version}')
    current = tuple(int(x) for x in version.split('.'))
    for part in constraints.split(','):
        match = re.fullmatch(r'(==|>=|<=|>|<|!=)(\d+(?:\.\d+)*(?:\.\*)?)', part)
        if not match:
            raise ObservationError(f'unsupported dependency constraint: {part}')
        op, target = match.groups()
        if target.endswith('.*'):
            if op not in ('==', '!='):
                raise ObservationError('unsupported wildcard comparison')
            wanted = tuple(int(x) for x in target[:-2].split('.'))
            good = current[:len(wanted)] == wanted
            if not (good if op == '==' else not good):
                return False
            continue
        wanted = tuple(int(x) for x in target.split('.'))
        length = max(len(wanted), len(current))
        a, b = current + (0,) * (length - len(current)), wanted + (0,) * (length - len(wanted))
        if not {'==': a == b, '!=': a != b, '>=': a >= b, '<=': a <= b, '>': a > b, '<': a < b}[op]:
            return False
    return True


def _dependencies() -> list[str]:
    paths = _metadata_paths()
    requirements = list(REQUIRED_IMPORTS)
    requested = os.environ.get(REQUESTED_PROVIDER_ENV, 'auto').strip().lower()
    if requested in {'cuda', 'nvidia'} or os.environ.get(SETUP_SELECTED_ENV) == 'CUDAExecutionProvider':
        requirements += list(CUDA_DEPENDENCY_IMPORTS)
    disabled = os.environ.get('WAVEFOUNDRY_DISABLE_RERANKER', '').lower() in {'1', 'true', 'yes', 'on'}
    if not disabled or requested not in {'cpu', 'auto'} or (platform.system() == 'Darwin' and platform.machine() in {'arm64', 'aarch64'}):
        requirements += list(GPU_ACCEL_IMPORTS)
    missing, seen = [], set()
    while requirements:
        spec = requirements.pop(0)
        if spec in seen:
            continue
        seen.add(spec)
        if len(seen) > 128:
            raise ObservationError('dependency extras exceed bounded census')
        name, extras, constraints = _requirement(spec)
        candidates = paths.get(name, [])
        # CPU and CUDA FastEmbed distributions export the same ordinary package.
        if name == 'fastembed' and not candidates:
            candidates = paths.get('fastembed-gpu', [])
        if not candidates:
            missing.append(spec)
            continue
        if len(candidates) != 1:
            raise ObservationError(f'ambiguous installed dependency: {name}')
        metadata = email.parser.Parser().parsestr(_read(candidates[0], MAX_METADATA_BYTES).decode('utf-8'))
        version = metadata.get('Version')
        if not version:
            raise ObservationError(f'missing distribution version: {name}')
        if not _satisfies(version, constraints):
            missing.append(spec)
        for extra in filter(None, extras):
            if extra not in metadata.get_all('Provides-Extra', []):
                raise ObservationError(f'unproven distribution extra: {name}[{extra}]')
            for requirement in metadata.get_all('Requires-Dist', []):
                base, sep, marker = requirement.partition(';')
                if not sep or 'extra' not in marker:
                    continue
                if re.fullmatch(r'\s*extra\s*==\s*[\'"]' + re.escape(extra) + r'[\'"]\s*', marker):
                    requirements.append(base.strip())
                elif re.search(r'[\'"]' + re.escape(extra) + r'[\'"]', marker):
                    raise ObservationError(f'unsupported extra condition: {marker}')
    return missing


# This child is deliberately self-contained: importing sqlite_runtime would activate
# the native runtime; importing this module would resolve non-stdlib siblings under -I.
_SQL_PROBE = r'''
import json, pathlib, sqlite3, sys, time
path = pathlib.Path(sys.argv[1]); budget = float(sys.argv[2]); start = time.monotonic()
try:
    c = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=min(.05, budget))
    try:
        c.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 262144)
        c.set_progress_handler(lambda: int(time.monotonic() - start > budget), 1000)
        c.execute('PRAGMA query_only=ON'); c.execute('BEGIN')
        allowed = ('meta', 'build_layer_meta', 'build_state')
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name IN ('meta','build_layer_meta','build_state') LIMIT 4")}
        out = {'meta': {}, 'layer': {}, 'state': None}
        for table, key, names in (
          ('meta', 'meta', ('store_schema_version','graph:store_schema_version','graph:schema_version','graph:builder_version','graph:walker_version','graph:chunker_version','lexical_statistics')),
          ('build_layer_meta', 'layer', ('walker_version','chunker_version','chunker_versions','model_versions'))):
            if table in tables:
                rows = c.execute('SELECT key,value FROM ' + table + ' WHERE key IN (' + ','.join('?' for _ in names) + ') LIMIT 16', names).fetchall()
                if len(rows) != len(dict(rows)): raise ValueError('duplicate metadata keys')
                out[key] = dict(rows)
        if 'build_state' in tables:
            out['state'] = c.execute('SELECT status,generation FROM build_state WHERE id=1 LIMIT 1').fetchone()
        raw = json.dumps(out)
        if len(raw) > 131072: raise ValueError('metadata response exceeds bound')
        print(raw)
    finally:
        c.close()
except Exception as exc:
    print(json.dumps({'error': type(exc).__name__ + ': ' + str(exc)[:500]}))
    sys.exit(2)
'''


def _storage_probe(path: Path, timeout_seconds: float) -> dict:
    if not 0 < timeout_seconds <= 30:
        raise ObservationError('database probe timeout must be in (0,30] seconds')
    kwargs = {'capture_output': True, 'text': True, 'encoding': 'utf-8', 'timeout': timeout_seconds}
    if os.name == 'nt':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    interpreter = subprocess_util.windowless_pythonw() or sys.executable
    result = subprocess.run([interpreter, '-I', '-S', '-B', '-c', _SQL_PROBE,
                             str(path), str(timeout_seconds)], **kwargs)
    if len(result.stdout) > 131072:
        raise ObservationError('database response exceeds bound')
    observation = json.loads(result.stdout)
    if result.returncode or 'error' in observation:
        raise ObservationError(observation.get('error', 'database probe failed'))
    return observation


def _owner(root: Path) -> tuple[bool, list[str] | None]:
    checkpoint_path, receipt_path = (_safe(root, name) for name in OWNERSHIP_FILES)
    checkpoint = _json(checkpoint_path) if checkpoint_path.exists() else None
    receipt = _json(receipt_path) if receipt_path.exists() else None
    st = root.stat(); identity = {'device': st.st_dev, 'inode': st.st_ino}
    if receipt is not None:
        if (receipt.get('receipt_version') not in (1, 2)
                or receipt.get('state') not in {'restart_required', 'quiesced', 'staged', 'validated', 'cutover_pending', 'published', 'verified', 'cleanup_pending', 'complete'}
                or receipt.get('root_identity') != identity
                or receipt.get('index_dir') != str(root / '.wavefoundry/index')
                or not re.fullmatch('[0-9a-f]{32}', str(receipt.get('migration_id', '')))
                or (receipt.get('receipt_version') == 2 and receipt.get('kind') != 'index_sqlite_schema8')):
            raise ObservationError('storage receipt identity/schema is unproven; preserve recovery records')
    if checkpoint is None and (receipt is None or receipt.get('state') == 'complete'):
        return False, None
    pending = receipt if receipt and receipt.get('state') != 'complete' else None
    action = (checkpoint or {}).get('action_required') or (pending or {}).get('restart_action')
    if not isinstance(action, dict):
        raise ObservationError('pending recovery has no validated continuation; inspect its owning checkpoint')
    if (action.get('root') != str(root) or action.get('root_identity') != identity
            or (pending and action.get('migration_id') != pending.get('migration_id'))
            or (checkpoint and action.get('checkpoint_started_at') != checkpoint.get('started_at'))
            or (pending and checkpoint and checkpoint.get('storage_migration_id') != pending.get('migration_id'))):
        raise ObservationError('pending continuation binding mismatch; preserve recovery records')
    entry = (pending or checkpoint or {}).get('entry_path', 'upgrade')
    if checkpoint is not None and (entry == 'setup' or 'root_identity' in checkpoint) and checkpoint.get('root_identity') != identity:
        raise ObservationError('checkpoint repository identity mismatch')
    if entry not in {'setup', 'upgrade'} or action.get('entry_path', 'upgrade') != entry:
        raise ObservationError('pending continuation owner mismatch')
    argv = action.get('command_argv')
    script = root / '.wavefoundry/framework/scripts' / ('setup_wavefoundry.py' if entry == 'setup' else 'upgrade_wavefoundry.py')
    permitted_interpreters = {str(Path(sys.executable).absolute())}
    console = Path(sys.executable)
    if os.name == 'nt' and console.stem.lower() == 'pythonw':
        permitted_interpreters.add(str(console.with_name(console.stem[:-1] + console.suffix).absolute()))
    if (not isinstance(argv, list) or not 4 <= len(argv) <= 64
            or any(not isinstance(v, str) or len(v) > 4096 or '\x00' in v for v in argv)
            or argv[0] not in permitted_interpreters
            or not re.fullmatch(r'python(?:w|3(?:\.\d+)?)?(?:\.exe)?', Path(argv[0]).name.lower())
            or argv[1] != str(script) or argv.count('--root') != 1
            or argv[argv.index('--root') + 1:argv.index('--root') + 2] != [str(root)]
            or '--confirm-hosts-stopped' not in argv):
        raise ObservationError('pending continuation command is not canonical')
    if entry == 'setup':
        if (pending or checkpoint).get('pack_path') or (checkpoint or {}).get('zip_path') or '--pack' in argv:
            raise ObservationError('setup continuation cannot replace archive ownership')
        if not re.fullmatch('[0-9a-f]{64}', str((pending or checkpoint).get('installed_framework_sha256', ''))):
            raise ObservationError('setup source binding missing')
    else:
        pack = (pending or {}).get('pack_path') or (checkpoint or {}).get('zip_path')
        if (not isinstance(pack, str) or argv.count('--pack') != 1
                or argv[argv.index('--pack') + 1:argv.index('--pack') + 2] != [pack]):
            raise ObservationError('archive continuation binding missing')
    # Reconstruct the producer's exact approved shape. Never pass through arbitrary
    # appended options, a second root spelling or an unrelated executable command.
    expected = [argv[0], str(script)]
    if entry == 'setup':
        saved = (pending or checkpoint).get('setup_args', [])
        if not isinstance(saved, list) or len(saved) > 48 or any(not isinstance(v, str) for v in saved):
            raise ObservationError('saved setup arguments are malformed')
        parser_args = [arg for arg in saved if arg not in {'--confirm-hosts-stopped', '--rebuild-storage'}]
        if any(arg in {'--help', '-h'} for arg in parser_args):
            raise ObservationError('help is not a setup recovery continuation')
        try:
            with redirect_stderr(io.StringIO()):
                parse_setup_args(parser_args)
        except SystemExit as exc:
            raise ObservationError('saved setup arguments do not match the canonical setup grammar') from exc
        args = iter(saved)
        for arg in args:
            if arg == '--root':
                next(args, None)
            elif not arg.startswith('--root=') and arg not in {'--confirm-hosts-stopped', '--rebuild-storage'}:
                expected.append(arg)
    expected += ['--root', str(root)]
    if entry == 'upgrade':
        expected += ['--pack', pack, '--yes']
    expected += ['--confirm-hosts-stopped']
    if '--rebuild-storage' in argv:
        # The request is part of the recorded receipt; do not infer authorization.
        if (pending or {}).get('strategy') != 'rebuild':
            raise ObservationError('storage rebuild authorization unproven in bounded continuation')
        expected.append('--rebuild-storage')
    if argv != expected:
        raise ObservationError('continuation differs from its owning canonical arguments')
    return True, argv


def assess_setup(root: Path, *, loaded_identity: dict | None = None,
                 timeout_seconds: float = 2.0) -> dict:
    started = time.monotonic()
    advisory = runtime_advisory.python_runtime_advisory()
    result = {'schema_version': SCHEMA_VERSION, 'status': 'ready', 'signature': '',
              'reasons': [], 'actions': [], 'startup_blocked': True,
              'advisories': [advisory] if advisory is not None else [],
              'limitations': list(LIMITATIONS), 'timings_ms': {}}
    unknown, needs_setup, pending, preserve = False, False, False, False
    def reason(code, message):
        result['reasons'].append({'code': code, 'message': message})
    try:
        root = Path(root).resolve(strict=True)
        if not root.is_dir():
            raise ObservationError('root is not an existing directory')
        before = assessment_signature(root)
        result['signature'] = _digest(before)
        if before['errors']:
            raise ObservationError('; '.join(before['errors']))
        identity = capture_loaded_identity()
        target_scripts = root / '.wavefoundry/framework/scripts'
        if not target_scripts.is_dir():
            needs_setup = True
            reason('framework_missing', 'The target checkout framework scripts are missing; install the framework before setup.')
        if target_scripts.is_dir() and target_scripts.resolve() != SCRIPTS.resolve():
            for name, expected in identity['sources'].items():
                candidate = _safe(root, '.wavefoundry/framework/scripts/' + name)
                if hashlib.sha256(_read(candidate, MAX_FILE_BYTES)).hexdigest() != expected:
                    preserve = True
                    raise ObservationError('target framework differs from the executing assessor; run the target checkout command')
        if identity['errors']:
            raise ObservationError('; '.join(identity['errors']))
        if loaded_identity is not None and loaded_identity != identity:
            reason('loaded_code_stale', 'Installed assessment/producer code changed; restart the Wavefoundry host before reassessing.')
            result['actions'].append({'kind': 'restart', 'argv': []})
            unknown = True
        try:
            pending, continuation = _owner(root)
            if pending:
                reason('recovery_pending', 'Resume the recorded owning continuation after stopping the required hosts; its guards revalidate source/archive bytes.')
                result['actions'].append({'kind': 'resume', 'argv': continuation})
                result['limitations'].append('Recovery command ownership/root bindings were checked; complete archive/source hashes are revalidated by its owner, not this bounded check.')
        except (OSError, ValueError, IndexError) as exc:
            pending, unknown = True, True
            reason('recovery_unproven', str(exc))
        env_started = time.monotonic()
        result['startup_blocked'] = True
        python = venv_bootstrap.tool_venv_python()
        if not python.exists() or not _site().is_dir():
            needs_setup = True; result['startup_blocked'] = True
            reason('environment_missing', 'The tool environment is missing; run setup to provision it.')
        else:
            cfg = _read(_venv() / 'pyvenv.cfg').decode('utf-8')
            match = re.search(r'(?m)^version(?:_info)?\s*=\s*(\d+)\.(\d+)', cfg)
            if not match:
                raise ObservationError('tool environment Python version is unproven')
            if tuple(map(int, match.groups())) != sys.version_info[:2] or sys.version_info[:2] < (3, 11):
                needs_setup = True; result['startup_blocked'] = True
                reason('environment_incompatible', 'The tool environment and effective Python versions differ; run setup.')
            missing = _dependencies()
            if not needs_setup:
                result['startup_blocked'] = False
            if missing:
                needs_setup = True; result['startup_blocked'] = True
                reason('dependencies_missing', 'Missing or incompatible dependency metadata: ' + ', '.join(missing))
        result['timings_ms']['environment'] = round((time.monotonic() - env_started) * 1000, 3)
        config = _safe(root, CONFIG_FILES[0])
        if not config.exists():
            needs_setup = True; reason('configuration_missing', 'Setup workflow configuration is missing.')
        else:
            configured = _json(config)
            defaults = _safe(root, CONFIG_FILES[2])
            if defaults.exists() and any(key not in configured for key in _json(defaults)):
                needs_setup = True; reason('configuration_incomplete', 'Setup-owned workflow defaults are missing.')
        for directory, relative in (('.claude', '.mcp.json'), ('.codex', '.codex/config.toml'),
                                     ('.cursor', '.cursor/mcp.json'), ('.junie', '.junie/mcp/mcp.json')):
            if (root / directory).is_dir() and not _safe(root, relative).exists():
                needs_setup = True; reason('surface_missing', f'Setup-generated launch surface is missing: {relative}')
        for relative in SURFACE_FILES:
            if relative.endswith(('.json', '.toml')) and _safe(root, relative).exists():
                entry = _surface_entry(root, relative)
                if entry is None:
                    needs_setup = True; reason('surface_entry_missing', f'Wavefoundry MCP entry is missing: {relative}')
                elif not _valid_surface_entry(root, entry, relative):
                    needs_setup = True; reason('surface_entry_changed', f'Wavefoundry MCP launch entry needs setup reconciliation: {relative}')
        # Stamp comparison can reveal an update, but cannot authorize readiness.
        stamp_path = _safe(root, STAMP_PATH)
        if stamp_path.exists():
            try:
                stamp = _json(stamp_path)
                if (stamp.get('schema_version') == SCHEMA_VERSION and isinstance(stamp.get('sources'), dict)
                        and (stamp['sources'] != identity['sources']
                             or stamp.get('configuration') != _configuration_identity(root)
                             or stamp.get('environment') != _environment_identity())):
                    needs_setup = True; reason('setup_inputs_changed', 'Installed setup inputs changed since successful setup.')
            except (OSError, ValueError):
                result['limitations'].append('The advisory setup stamp is unreadable; live observations were used.')
        if not pending and not (loaded_identity is not None and loaded_identity != identity):
            database = _safe(root, '.wavefoundry/index/index.sqlite')
            legacy = _safe(root, '.wavefoundry/index/index-state.sqlite')
            if database.exists() and legacy.exists():
                preserve = True
                raise ObservationError('storage authority ambiguous: both database names exist; preserve both')
            if not database.exists() and legacy.exists():
                database = legacy
            if not database.exists():
                if any(_safe(root, '.wavefoundry/index/index.sqlite' + suffix).exists() for suffix in ('-wal', '-shm')):
                    raise ObservationError('orphan database sidecars retained; storage authority is unproven')
                needs_setup = True
                reason('index_obsolete' if legacy.exists() else 'index_missing', 'Run setup to reconcile the local index.')
            else:
                for suffix in ('-wal', '-shm'):
                    _safe(root, str(database.relative_to(root)) + suffix)
                preserve = True
                probe_started = time.monotonic()
                observation = _storage_probe(database, timeout_seconds)
                result['timings_ms']['database'] = round((time.monotonic() - probe_started) * 1000, 3)
                versions = _versions(); meta = observation['meta']; layer = observation['layer']
                schema = meta.get('store_schema_version')
                if not isinstance(schema, str) or not schema.isdecimal():
                    raise ObservationError('storage schema unproven; preserve the index')
                if int(schema) > int(versions['store_schema_version']):
                    raise ObservationError('storage schema newer than installed code; preserve the index and use a compatible host')
                if database == legacy:
                    needs_setup = True; reason('index_legacy_name', 'Run setup to reconcile the legacy index filename.')
                if schema != versions['store_schema_version']:
                    if schema not in {'4', '5', '6', '7'}:
                        raise ObservationError('unsupported historical storage schema; preserve index')
                    needs_setup = True; reason('index_obsolete', 'Index schema needs setup reconciliation.')
                else:
                    state = observation['state']
                    if not isinstance(state, list) or len(state) != 2 or state[0] not in {'complete', 'building', 'uninitialized'} or not isinstance(state[1], int):
                        raise ObservationError('publication state is malformed or missing')
                    if state[0] == 'building':
                        raise ObservationError('index publication is in progress or interrupted; retry after its owner completes')
                    if state[0] != 'complete' or state[1] < 1:
                        needs_setup = True; reason('index_unpublished', 'Index has no completed publication; run setup.')
                    else:
                        chunks = json.loads(layer.get('chunker_versions', '{}'))
                        models = json.loads(layer.get('model_versions', '{}'))
                        if not isinstance(chunks, dict) or not isinstance(models, dict):
                            raise ObservationError('producer metadata is malformed')
                        recorded = {**meta, 'walker_version': layer.get('walker_version')}
                        stats = json.loads(meta.get('lexical_statistics', '{}'))
                        if not isinstance(stats, dict) or 'version' not in stats:
                            raise ObservationError('lexical statistics provenance missing')
                        recorded['lexical_statistics.version'] = str(stats['version'])
                        for name in ('docs', 'code'):
                            value = chunks.get(name, layer.get('chunker_version'))
                            recorded['chunker_version:' + name] = value
                            model = models.get(name)
                            if not isinstance(model, str) or not model:
                                raise ObservationError('published model identity is missing')
                            if model.split('@', 1)[0] != versions[name + '_model']:
                                needs_setup = True; reason('model_changed', f'{name} model selection changed; run setup.')
                        for key, value in recorded.items():
                            expected = versions.get(key, versions.get('chunker_version') if key.startswith('chunker_version:') else None)
                            if expected is None:
                                continue
                            if not isinstance(value, str) or not value.isdecimal():
                                raise ObservationError(f'producer version unproven: {key}')
                            if int(value) > int(expected):
                                raise ObservationError(f'producer version newer than installed code: {key}; preserve index')
                            if int(value) < int(expected):
                                needs_setup = True; reason('producer_changed', f'{key} needs setup reconciliation.')
                        for key in ('graph:store_schema_version', 'graph:schema_version', 'graph:builder_version', 'graph:walker_version', 'graph:chunker_version'):
                            if key not in meta:
                                raise ObservationError(f'published graph provenance missing: {key}')
        preserve = False
        after = assessment_signature(root)
        # WAL changes invalidate cached publication observations. First-time SQLite
        # coordination creation may require one conservative reassessment; SHM read marks do not.
        if after != before:
            unknown = True; reason('inputs_changed', 'Setup-relevant inputs changed during assessment; retry.')
    except subprocess.TimeoutExpired:
        unknown = True; reason('probe_timeout', 'Database assessment timed out; retry when its owner is idle.')
    except (OSError, ValueError, SyntaxError, KeyError, TypeError) as exc:
        unknown = True; reason('assessment_unproven', str(exc))
    if needs_setup and not pending and not preserve and not any(r['code'] == 'loaded_code_stale' for r in result['reasons']):
        result['actions'].append({'kind': 'setup', 'argv': ['wf', 'setup', '--root', str(root)]})
    result['status'] = 'indeterminate' if unknown else 'action_required' if result['actions'] else 'ready'
    result['timings_ms']['total'] = round((time.monotonic() - started) * 1000, 3)
    return result


def exit_code(result: dict) -> int:
    return {'ready': 0, 'action_required': 1, 'indeterminate': 2}.get(result.get('status'), 2)


def format_text(result: dict) -> str:
    lines = ['Setup readiness: ' + result['status']]
    lines.extend(item['message'] for item in result['reasons'])
    for action in result['actions']:
        argv = action['argv']
        command = ('& ' + ' '.join("'" + arg.replace("'", "''") + "'" for arg in argv)
                   if os.name == 'nt' else shlex.join(argv)) if argv else 'Restart the Wavefoundry host.'
        lines.append(command)
    lines.append('Scope: metadata readiness only; no full integrity, model or source-freshness audit.')
    return '\n'.join(lines)


def _environment_identity() -> dict:
    return {'tool_venv': str(_venv().resolve()),
            'variables': {key: os.environ.get(key) for key in ENV_KEYS},
            'python': [sys.executable, sys.version, sys.prefix, getattr(sys, 'abiflags', '')]}


def _surface_entry(root: Path, relative: str):
    raw = _read(_safe(root, relative)).decode('utf-8')
    data = tomllib.loads(raw) if relative.endswith('.toml') else json.loads(raw)
    if not isinstance(data, dict):
        raise ObservationError('MCP configuration is not an object')
    servers = data.get('mcp_servers' if relative.endswith('.toml') else 'mcpServers', {})
    if not isinstance(servers, dict):
        raise ObservationError('MCP server mapping is malformed')
    entry = servers.get('wavefoundry')
    if entry is not None and not isinstance(entry, dict):
        raise ObservationError('Wavefoundry MCP entry is malformed')
    # Only launch fields owned by setup affect readiness, not other servers or host preferences.
    return {key: entry[key] for key in ('command', 'args', 'env', 'cwd') if key in entry} if entry is not None else None


def _valid_surface_entry(root: Path, entry: dict, relative: str = '.mcp.json') -> bool:
    """Validate the launch shape using the renderer's host-specific path base."""
    command, args = entry.get('command'), entry.get('args')
    if command != 'python3' or not isinstance(args, list) or any(not isinstance(v, str) for v in args):
        return False
    if len(args) not in (1, 3) or (len(args) == 3 and args[1] != '--root'):
        return False

    def resolved(value: str, base: Path) -> Path:
        if relative == '.cursor/mcp.json':
            value = value.replace('${workspaceFolder}', str(root))
        if re.search(r'\$\{|\$[A-Za-z_]|%[^%]+%', value):
            raise ObservationError(f'unrecognized MCP launch variable: {relative}')
        path = Path(value)
        return (path if path.is_absolute() else base / path).resolve()

    # Junie resolves argument paths from the configuration directory. Other
    # canonical host launchers use the workspace root. Explicit cwd must retain
    # that root, even when an absolute server argument would happen to launch.
    base = (root / relative).parent if relative == '.junie/mcp/mcp.json' else root
    if 'cwd' in entry:
        if not isinstance(entry['cwd'], str) or not entry['cwd']:
            return False
        if resolved(entry['cwd'], root) != root:
            return False
    if resolved(args[0], base) != root / '.wavefoundry/framework/scripts/server.py':
        return False
    return len(args) == 1 or resolved(args[2], base) == root


def _configuration_identity(root: Path) -> dict:
    result = {}
    for relative in (*CONFIG_FILES, *SURFACE_FILES):
        path = _safe(root, relative)
        if path.exists():
            if relative == 'docs/workflow-config.json':
                data = _json(path)
                # Notes, review/lifecycle state and unrelated product settings do not
                # change setup fitness. Index/provider/platform selections do.
                data = {key: data[key] for key in ('indexing', 'setup', 'platforms', 'embedding', 'providers') if key in data}
                result[relative] = _digest(data)
            elif relative.endswith(('.toml', '.json')) and relative in SURFACE_FILES:
                result[relative] = _digest(_surface_entry(root, relative))
            else:
                result[relative] = hashlib.sha256(_read(path, MAX_FILE_BYTES)).hexdigest()
        else:
            result[relative] = None
    return result


def write_setup_stamp(root: Path) -> None:
    """Write the non-authoritative hint only from successful ordinary setup."""
    root = Path(root).resolve(strict=True)
    path = _safe(root, STAMP_PATH)
    identity = capture_loaded_identity()
    if identity['errors']:
        raise ObservationError('; '.join(identity['errors']))
    payload = {'schema_version': SCHEMA_VERSION, 'sources': identity['sources'],
               'environment': _environment_identity(), 'configuration': _configuration_identity(root), 'written_at': time.time()}
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix='.setup-state-', dir=path.parent)
    temporary = Path(raw)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(payload, stream, sort_keys=True); stream.write('\n')
            stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
