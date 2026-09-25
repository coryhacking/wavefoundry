"""A repository that the real setup-readiness check reports ready from a fresh process (wave 1yzcz).

In-process readiness tests patch ``_dependencies``; a subprocess cannot be
patched, so this fixture satisfies the live checks for real: the fixture carries
its own copy of the framework scripts (so the fixture's check is the executing
assessor), a fake tool environment reached through ``WAVEFOUNDRY_TOOL_VENV``
with a ``pyvenv.cfg`` matching the running interpreter, synthetic dist-info
metadata for the whole dependency census (``REQUIRED_IMPORTS`` plus
``GPU_ACCEL_IMPORTS`` and each declared extra), and an index database whose
recorded versions match the installed producers.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import setup_readiness as readiness  # noqa: E402
import setup_requirements  # noqa: E402
import venv_bootstrap  # noqa: E402


def _version_for(constraints: str) -> str:
    """A version satisfying a census constraint string such as ``>=0.11``."""
    for part in filter(None, constraints.split(',')):
        match = re.fullmatch(r'(==|>=|<=|>|<|!=)(\d+(?:\.\d+)*)(\.\*)?', part)
        if match and match.group(1) in ('==', '>=', '<='):
            return match.group(2)
        if match and match.group(1) == '>':
            return match.group(2) + '.1'
    return '1.0'


def _write_dist_info(site: Path) -> None:
    specs = list(setup_requirements.REQUIRED_IMPORTS) + list(setup_requirements.GPU_ACCEL_IMPORTS)
    for spec in specs:
        name, extras, constraints = readiness._requirement(spec)
        version = _version_for(constraints)
        lines = [f'Metadata-Version: 2.1', f'Name: {name}', f'Version: {version}']
        lines += [f'Provides-Extra: {extra}' for extra in filter(None, extras)]
        info = site / f'{name.replace("-", "_")}-{version}.dist-info'
        info.mkdir(parents=True, exist_ok=True)
        (info / 'METADATA').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _write_database(index: Path) -> None:
    versions = readiness._versions()
    conn = sqlite3.connect(index / 'index.sqlite')
    try:
        conn.executescript(
            'CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT); '
            'CREATE TABLE build_layer_meta(key TEXT PRIMARY KEY,value TEXT); '
            'CREATE TABLE build_state(id INTEGER PRIMARY KEY,status TEXT,generation INTEGER); '
            'INSERT INTO build_state VALUES(1,"complete",1);')
        for key, value in versions.items():
            if key == 'store_schema_version' or key.startswith('graph:'):
                conn.execute('INSERT INTO meta VALUES(?,?)', (key, value))
        conn.execute('INSERT INTO meta VALUES(?,?)', (
            'lexical_statistics', json.dumps({'version': int(versions['lexical_statistics.version'])})))
        for key, value in {
                'walker_version': versions['walker_version'],
                'chunker_versions': json.dumps({name: versions['chunker_version'] for name in ('docs', 'code')}),
                'model_versions': json.dumps({name: versions[name + '_model'] for name in ('docs', 'code')})}.items():
            conn.execute('INSERT INTO build_layer_meta VALUES(?,?)', (key, value))
        conn.commit()
    finally:
        conn.close()


def build(root: Path, *, claude: bool = False) -> dict[str, str]:
    """Populate ``root`` and return the environment for processes that assess it.

    With ``claude``, the fixture also carries ``.claude/`` and a valid
    ``.mcp.json`` so the Claude launch-surface check stays ready.
    """
    root = Path(root)
    scripts = root / '.wavefoundry/framework/scripts'
    shutil.copytree(SCRIPTS, scripts, ignore=shutil.ignore_patterns('tests', '__pycache__', '*.pyc'))
    (root / 'docs').mkdir(parents=True, exist_ok=True)
    (root / 'docs/workflow-config.json').write_text('{}', encoding='utf-8')
    venv = root / 'venv'
    python = venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    python.parent.mkdir(parents=True)
    python.touch()
    (venv / 'pyvenv.cfg').write_text(
        f'version = {sys.version_info.major}.{sys.version_info.minor}.0\n', encoding='utf-8')
    env = clean_environment(venv)
    site = _site_packages(venv, env)
    site.mkdir(parents=True, exist_ok=True)
    _write_dist_info(site)
    index = root / '.wavefoundry/index'
    index.mkdir(parents=True)
    _write_database(index)
    if claude:
        (root / '.claude').mkdir(exist_ok=True)
        (root / '.mcp.json').write_text(json.dumps({'mcpServers': {'wavefoundry': {
            'command': 'python3', 'args': ['.wavefoundry/framework/scripts/server.py']}}}), encoding='utf-8')
    return env


def _site_packages(venv: Path, env: dict[str, str]) -> Path:
    saved = os.environ.get('WAVEFOUNDRY_TOOL_VENV')
    os.environ['WAVEFOUNDRY_TOOL_VENV'] = env['WAVEFOUNDRY_TOOL_VENV']
    try:
        return venv_bootstrap._venv_site_packages(venv)
    finally:
        if saved is None:
            os.environ.pop('WAVEFOUNDRY_TOOL_VENV', None)
        else:
            os.environ['WAVEFOUNDRY_TOOL_VENV'] = saved


def clean_environment(venv: Path) -> dict[str, str]:
    """The current environment without any recorded setup variable, pointing at ``venv``."""
    env = {key: value for key, value in os.environ.items() if key not in readiness.ENV_KEYS}
    env['WAVEFOUNDRY_TOOL_VENV'] = str(venv)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


def check(root: Path, env: dict[str, str]) -> dict:
    """Run the fixture's own ``wf setup --check --json`` in a fresh process."""
    script = Path(root) / '.wavefoundry/framework/scripts/setup_wavefoundry.py'
    completed = subprocess.run(
        [sys.executable, '-B', str(script), '--check', '--json', '--root', str(root)],
        env=env, capture_output=True, text=True, timeout=60, check=False)
    try:
        return json.loads(completed.stdout)
    except ValueError as exc:
        raise AssertionError(f'check output is not JSON: {completed.stdout!r} {completed.stderr!r}') from exc
