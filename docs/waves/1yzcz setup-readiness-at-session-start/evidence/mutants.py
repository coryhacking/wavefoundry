"""Mutation check for wave 1yzcz. Scratch copies only.

Usage: python -B mutants.py <repo-root>
Each mutant is applied to a scratch mirror (framework scripts and seeds, AGENTS.md,
.claude/) and the named test targets must fail. Every mutant is expected killed.
"""
import os, shutil, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
SCR = '.wavefoundry/framework/scripts/'
SR, UP, SV, RPS = SCR + 'setup_readiness.py', SCR + 'upgrade_wavefoundry.py', SCR + 'server.py', SCR + 'render_platform_surfaces.py'
READINESS = ['test_setup_readiness']
WRITERS = ['test_setup_stamp_writers']
UPGRADE = ['test_upgrade_wavefoundry.PhaseCleanupSetupBaselineTests']
HOOK = ['test_session_start_hook']

MUTANTS = {
    # 1yzcy
    'full_environment_compared': (SR, "projected_environment(stamp.get('environment'))\n                             != projected_environment(_environment_identity())",
                                  "stamp.get('environment') != _environment_identity()", READINESS + WRITERS),
    'setup_handoff_compared': (SR, "COMPARED_ENV_KEYS = (REQUESTED_PROVIDER_ENV, 'WAVEFOUNDRY_DISABLE_RERANKER')",
                               "COMPARED_ENV_KEYS = (REQUESTED_PROVIDER_ENV, SETUP_SELECTED_ENV, 'WAVEFOUNDRY_DISABLE_RERANKER')", WRITERS),
    'provider_not_compared': (SR, "COMPARED_ENV_KEYS = (REQUESTED_PROVIDER_ENV, 'WAVEFOUNDRY_DISABLE_RERANKER')",
                              "COMPARED_ENV_KEYS = ('WAVEFOUNDRY_DISABLE_RERANKER',)", READINESS),
    'full_python_version_compared': (SR, "'python': match.group(0) if match else version,", "'python': version,", READINESS),
    'use_stamp_ignored': (SR, "if use_stamp and stamp_path.exists():", "if stamp_path.exists():", READINESS + UPGRADE),
    'identity_guard_removed': (SR, "if identity is not None and identity.get('sources') != current['sources']:", "if False:", READINESS + WRITERS),
    'adoption_overwrites_readable_stamp': (SR, "    if read_setup_stamp(root) is not None:\n        return False\n", "", READINESS + WRITERS),
    'adoption_ignores_status': (SR, "    if assessment.get('status') != 'ready':\n        return False\n    if read_setup_stamp", "    if read_setup_stamp", READINESS),
    'check_writes_stamp': (SR, "    result['timings_ms']['total'] = round((time.monotonic() - started) * 1000, 3)\n    return result",
                           "    result['timings_ms']['total'] = round((time.monotonic() - started) * 1000, 3)\n    if result['status'] == 'ready':\n        write_setup_stamp(root)\n    return result", WRITERS),
    'upgrade_writes_when_not_ready': (UP, '        if status != "ready":\n            command', '        if False:\n            command', UPGRADE),
    'upgrade_uses_its_own_stale_stamp': (UP, "setup_readiness.assess_setup(root, use_stamp=False)", "setup_readiness.assess_setup(root)", UPGRADE),
    # Moves the call ahead of lock removal (a duplicate call would be an equivalent mutant).
    'upgrade_baseline_before_lock_removal': (UP, [('    upgrade_lib.remove_upgrade_lock(root)\n    _log("  Upgrade lock removed',
                                              '    _record_setup_baseline(root)\n    upgrade_lib.remove_upgrade_lock(root)\n    _log("  Upgrade lock removed'),
                                             ("    if not index_update_failed:\n        _record_setup_baseline(root)\n    else:\n", "    if index_update_failed:\n")], None, UPGRADE),
    'upgrade_ignores_environment_guard': (UP, "        if prior is not None and (", "        if False and (", UPGRADE),
    'upgrade_error_propagates': (UP, "    except Exception as exc:  # the stamp is advisory", "    except ImportError as exc:  # the stamp is advisory", UPGRADE),
    'upgrade_ignores_index_failure': (UP, "    if not index_update_failed:\n        _record_setup_baseline(root)\n    else:\n        _log(", "    _record_setup_baseline(root)\n    if False:\n        _log(", UPGRADE),
    'adoption_under_dry_run': (SV, "    if args.dry_run:\n        # Wave 1p35d", "    _adopt_setup_baseline(root, _STARTUP_ASSESSMENT)\n    if args.dry_run:\n        # Wave 1p35d", WRITERS),
    'adoption_error_fails_startup': (SV, "    except (OSError, ValueError) as exc:\n        print(f\"wavefoundry: setup baseline", "    except ImportError as exc:\n        print(f\"wavefoundry: setup baseline", WRITERS),
    # 1yzcx
    'hook_bootstrap_restored': (RPS, "    return compose_preactivation_script(\n        \"\"\"\n        import sys\n\n        sys.dont_write_bytecode",
                                "    return compose_script(\n        \"\"\"\n        import sys\n\n        sys.dont_write_bytecode", HOOK),
    'hook_writes_bytecode': (RPS, "        sys.dont_write_bytecode = True\n\n        import os", "        import os", HOOK),
    'hook_catches_only_exception': (RPS, "            except BaseException as exc:\n                try:", "            except Exception as exc:\n                try:", HOOK),
    'hook_prints_when_ready': (RPS, "            if status == \"ready\":\n                return []", "            if status == \"ready\":\n                return [\"ready\"]", HOOK),
    'hook_no_retry': (RPS, "            if [item.get(\"code\") for item in result.get(\"reasons\") or []] == [\"inputs_changed\"]:", "            if False:", HOOK),
    'hook_no_ask': (RPS, "            lines.append(ASK)\n", "", HOOK),
    'hook_unsanitized': (RPS, "            text = \"\".join(ch if ch.isprintable() else \" \" for ch in str(text))\n            return text[:MAX_LINE]", "            return str(text)", HOOK),
    'hook_reasons_uncapped': (RPS, "            for item in reasons[:MAX_REASONS]:", "            for item in reasons:", HOOK),
    'hook_setup_note_for_every_action': (RPS, "                if kind == \"setup\":\n                    lines.append(\"Setup ends", "                if True:\n                    lines.append(\"Setup ends", HOOK),
    'hook_startup_only': (RPS, '"matcher": "startup|resume",', '"matcher": "startup",', HOOK),
    'hook_no_timeout': (RPS, '        "timeout": 15,\n', '', HOOK),
    'hook_name_not_namespaced': (RPS, [('        "name": "wf-session-start",', '        "name": "session-start",'),
                                        ('"hooks" / "wf-session-start", claude_session_start_source())', '"hooks" / "session-start", claude_session_start_source())')], None, HOOK),
    'upgrade_drops_identity_guard': (UP, 'setup_readiness.write_setup_stamp(root, provenance="upgrade", identity=identity)', 'setup_readiness.write_setup_stamp(root, provenance="upgrade")', UPGRADE),
    'hook_cuts_long_command': (RPS, '                if len(command) > MAX_LINE:\n', '                if False:\n', HOOK),
    'adoption_after_transport': (SV, '    _adopt_setup_baseline(root, _STARTUP_ASSESSMENT)\n    _configure_stdio_for_mcp_transport()', '    _configure_stdio_for_mcp_transport()', WRITERS),
    'read_stamp_ignores_schema': (SR, "    if stamp.get('schema_version') != SCHEMA_VERSION or not isinstance(stamp.get('sources'), dict):", "    if not isinstance(stamp.get('sources'), dict):", READINESS),
    'timeout_on_every_hook': (RPS, '        if "timeout" in hook:\n            entry_hook["timeout"] = hook["timeout"]', '        entry_hook["timeout"] = hook.get("timeout", 15)', HOOK),
}


def mirror(dest: Path) -> None:
    ignore = shutil.ignore_patterns('__pycache__', '*.pyc', 'index')
    for rel in ('.wavefoundry/framework/scripts', '.wavefoundry/framework/seeds', '.claude'):
        shutil.copytree(REPO / rel, dest / rel, ignore=ignore)
    shutil.copy2(REPO / 'AGENTS.md', dest / 'AGENTS.md')


def run(root: Path, targets):
    scripts = root / SCR
    env = dict(os.environ, PYTHONPATH=f'{scripts}{os.pathsep}{scripts / "tests"}', PYTHONDONTWRITEBYTECODE='1')
    return subprocess.run([sys.executable, '-B', '-m', 'unittest', *targets], cwd=scripts / 'tests',
                          env=env, capture_output=True, text=True, timeout=1800)


with tempfile.TemporaryDirectory() as base:
    control = Path(base) / 'control'
    mirror(control)
    targets = sorted({t for m in MUTANTS.values() for t in m[3]})
    baseline = run(control, targets)
    print(f'baseline: rc={baseline.returncode} {baseline.stderr.strip().splitlines()[-1]}')
    for label, (rel, old, new, targets) in MUTANTS.items():
        if len(sys.argv) > 2 and label not in sys.argv[2:]:
            continue
        root = Path(base) / label
        mirror(root)
        path = root / rel
        text = path.read_text()
        for before, after in (old if isinstance(old, list) else [(old, new)]):
            assert text.count(before) == 1, label
            text = text.replace(before, after)
        path.write_text(text)
        result = run(root, targets)
        verdict = 'KILLED' if result.returncode != 0 else 'SURVIVED'
        print(f'{label}: {verdict} ({result.stderr.strip().splitlines()[-1]})')
        shutil.rmtree(root)
