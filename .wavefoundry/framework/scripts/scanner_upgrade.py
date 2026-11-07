"""Validate project rules against a private incoming scanner before publication.

Only a trusted, operator-selected framework pack supplies executable Python.
Project configuration remains data. No source scan or provider action runs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tempfile
import zipfile

if __name__ == '__main__' or sys.pycache_prefix is None:
    sys.dont_write_bytecode = True

import bytecode_cache

if __name__ == '__main__':
    bytecode_cache.configure()

FRAMEWORK = '.wavefoundry/framework'
PROJECT_RULES = 'docs/scan-rules.toml'
MAX_RULE_BYTES = 2 * 1024 * 1024
MAX_STAGE_BYTES = 64 * 1024 * 1024
MAX_MEMBER_BYTES = 8 * 1024 * 1024
MAX_MEMBERS = 4096
MAX_ISSUES = 50


def _result(status, issues=(), **extra):
    return {'status': status, 'complete': status != 'incomplete',
            'issues': list(issues)[:MAX_ISSUES],
            'issues_omitted': max(0, len(issues) - MAX_ISSUES), **extra}


def _issue(field, code, rule=None):
    def safe(value):
        return ''.join(c if c.isascii() and c.isprintable() else '?' for c in str(value))[:100]
    return {'file': PROJECT_RULES, 'field': safe(field), 'code': code,
            **({'rule': safe(rule)} if rule is not None else {})}


def _read_rules(path):
    if path.is_symlink():
        raise ValueError('project_rule_link')
    with path.open('rb') as stream:
        data = stream.read(MAX_RULE_BYTES + 1)
    if len(data) > MAX_RULE_BYTES:
        raise ValueError('rule_size_limit')
    return data


def _selected(name):
    if name == f'{FRAMEWORK}/scan-rules.toml':
        return True
    if name.startswith(f'{FRAMEWORK}/scan/'):
        return True
    prefix = f'{FRAMEWORK}/scripts/'
    return name.startswith(prefix) and name.endswith('.py') and '/tests/' not in name


def _stage(root, pack, target):
    """Copy bounded scanner dependencies to scratch; never extract into a target."""
    total = count = 0
    def put(name, size, source):
        nonlocal total, count
        parts = PurePosixPath(name).parts
        if PurePosixPath(name).is_absolute() or '..' in parts or '\\' in name:
            raise ValueError('invalid_member_path')
        count += 1
        total += size
        if count > MAX_MEMBERS or total > MAX_STAGE_BYTES or size > MAX_MEMBER_BYTES:
            raise ValueError('stage_size_limit')
        destination = target.joinpath(*parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise ValueError('duplicate_member')
        with source() as incoming, destination.open('xb') as out:
            data = incoming.read(MAX_MEMBER_BYTES + 1)
            if len(data) != size:
                raise ValueError('member_size_changed')
            out.write(data)
    if pack is not None:
        with zipfile.ZipFile(pack) as archive:
            for entry in archive.infolist():
                if entry.is_dir() or not _selected(entry.filename):
                    continue
                if stat.S_ISLNK(entry.external_attr >> 16):
                    raise ValueError('member_link')
                put(entry.filename, entry.file_size, lambda e=entry: archive.open(e))
    else:
        framework = root / FRAMEWORK
        for path in framework.rglob('*'):
            name = path.relative_to(root).as_posix()
            if not _selected(name) or not path.is_file():
                continue
            if path.is_symlink():
                raise ValueError('member_link')
            put(name, path.stat().st_size, lambda p=path: p.open('rb'))


def inspect_project_rules(root: Path, pack: Path | None = None) -> dict:
    """Preview with incoming code/data, without changing installed or local rules."""
    try:
        project = _read_rules(root / PROJECT_RULES)
    except FileNotFoundError:
        return _result('not_applicable')
    except (OSError, ValueError):
        return _result('incomplete', [_issue('$', 'project_rules_unreadable_or_oversized')])
    try:
        with tempfile.TemporaryDirectory(prefix='wf-scan-preflight-') as directory:
            staged = Path(directory)
            _stage(root, pack, staged)
            local = staged / PROJECT_RULES
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_bytes(project)
            from subprocess_util import run_with_tree_kill
            proc = run_with_tree_kill(
                [sys.executable, '-B', str(Path(__file__).resolve()), '--inspect-root', str(staged)],
                cwd=str(staged), capture_output=True, text=True, timeout=120,
                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
            )
            if proc.returncode != 0 or len(proc.stdout) > 65536:
                return _result('incomplete', [_issue('$', 'validation_process_failed')])
            result = json.loads(proc.stdout)
            if (not isinstance(result, dict) or result.get('status') not in
                    {'compatible', 'unsupported', 'incomplete'} or
                    type(result.get('complete')) is not bool or
                    not isinstance(result.get('issues'), list)):
                raise ValueError('invalid_validation_result')
            if _read_rules(root / PROJECT_RULES) != project:
                return _result('incomplete', [_issue('$', 'project_rules_changed')])
            return result
    except Exception:
        # Do not include arbitrary parser, archive, subprocess or file text.
        return _result('incomplete', [_issue('$', 'validation_unavailable')])


def _staged_import_path(staged_scripts):
    """Staged scripts first, then stdlib/site; never an installed scripts tree.

    Change 22qr4: the child's own directory (the installed scripts) and any
    inherited PYTHONPATH entry outside stdlib/site are dropped, so a module
    missing from an incomplete pack cannot resolve from the installed copy.
    Bootstrap modules this process already imported stay loaded.
    """
    import site
    import sysconfig

    def norm(entry):
        return os.path.normcase(os.path.realpath(entry or os.getcwd()))

    installed = norm(str(Path(__file__).resolve().parent))
    inherited = {norm(p) for p in os.environ.get('PYTHONPATH', '').split(os.pathsep) if p}
    bases = {norm(p) for scheme in (sysconfig.get_paths(), sysconfig.get_paths(vars={
        'base': sys.base_prefix, 'platbase': sys.base_exec_prefix}))
        for key, p in scheme.items() if key in {'stdlib', 'platstdlib', 'purelib', 'platlib'}}
    try:
        bases.update(norm(p) for p in site.getsitepackages())
    except AttributeError:
        pass
    user_site = getattr(site, 'USER_SITE', None)
    if user_site:
        bases.add(norm(user_site))

    def standard(real):
        return any(real == base or real.startswith(base.rstrip(os.sep) + os.sep) for base in bases)

    kept = [str(staged_scripts)]
    for entry in sys.path:
        real = norm(entry)
        if real == installed or (real in inherited and not standard(real)):
            continue
        kept.append(entry)
    return kept


def _inspect_root(root):
    # Import the incoming dependency closure, never cached installed modules.
    sys.path[:] = _staged_import_path(root / FRAMEWORK / 'scripts')
    try:
        from wave_lint_lib import secrets_validators as scanner
        project = scanner._load_toml(root / PROJECT_RULES)
        framework = scanner._load_toml(root / FRAMEWORK / 'scan-rules.toml')
        profile = framework.get('wavefoundryProfile', 'legacy-cel')
        issues = []
        if profile == 'betterleaks-v2-8f376ff9':
            from wave_lint_lib.betterleaks_engine import _RULE_FIELDS
            from wave_lint_lib.expr_filter import compile_filter
            for field in ('filter', 'prefilter'):
                if project.get(field):
                    issues.append(_issue(field, 'unsupported_global_filter'))
            if project.get('wavefoundryProfile', profile) != profile:
                issues.append(_issue('wavefoundryProfile', 'profile_mismatch'))
            for n, rule in enumerate(project.get('rules', [])):
                if not isinstance(rule, dict):
                    issues.append(_issue(f'rules[{n}]', 'invalid_rule'))
                    continue
                rid = rule.get('id')
                if not isinstance(rid, str) or not rid.strip():
                    rid = f'rules[{n}]'
                    issues.append(_issue('id', 'invalid_rule_id', rid))
                for field in rule:
                    if field not in _RULE_FIELDS:
                        issues.append(_issue(field, 'unsupported_rule_field', rid))
                if rule.get('filter'):
                    try:
                        compile_filter(rule['filter'])
                    except Exception:
                        issues.append(_issue('filter', 'invalid_expression_syntax', rid))
        if issues:
            return _result('unsupported', issues)
        rules, policy, errors = scanner.load_merged_ruleset(root)
        if errors:
            return _result('unsupported', [_issue('$', 'invalid_merged_configuration')])
        if policy.get('_betterleaks_config'):
            from wave_lint_lib.betterleaks_worker import worker_request, WorkerError, close_worker
            try:
                worker_request('configure', {'config': policy['_betterleaks_config'],
                                            'cache_key': policy.get('_betterleaks_cache_key', '')})
            except WorkerError as exc:
                return _result('unsupported' if exc.code == 'invalid_configuration' else 'incomplete',
                               [_issue('$', exc.code)])
            finally:
                close_worker()
        else:
            report = scanner.inspect_ruleset_compatibility({'rules': rules})
            if report['status'] != 'within_checked_subset':
                return _result('unsupported' if report.get('complete') else 'incomplete',
                               [_issue('$', 'legacy_configuration_not_supported')])
        return _result('compatible')
    except Exception:
        return _result('incomplete', [_issue('$', 'incoming_validator_unavailable')])


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != '--inspect-root':
        raise SystemExit(2)
    print(json.dumps(_inspect_root(Path(sys.argv[2]))))
