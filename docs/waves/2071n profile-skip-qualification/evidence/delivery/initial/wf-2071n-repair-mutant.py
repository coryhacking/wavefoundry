import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

repo = Path('/Users/coryhacking/Developer/wavefoundry')
scripts = repo / '.wavefoundry/framework/scripts'
sys.path[:0] = [str(scripts), str(scripts / 'tests')]
import run_tests
import record_layout_support as profiles

with tempfile.TemporaryDirectory(prefix='wf-2071n-fixed-marker-') as work:
    target = Path(work) / 'repo'
    target.mkdir()
    copied, error = run_tests._copy_listed_tree(repo, target)
    assert error is None, error
    copied_scripts = target / '.wavefoundry/framework/scripts'
    profiles.apply_profile(copied_scripts, profiles.load_profile('second'), repo_root=target,
                           python=sys.executable)
    path = copied_scripts / 'tests/test_profile_support.py'
    cmd = [sys.executable, '-B', '-m', 'unittest',
           'test_profile_support.DefaultProfileOnlyMarkerTests.test_repository_corpus_runs_under_declared_tools', '-v']
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', WAVEFOUNDRY_TEST_PROFILE='second',
               PYTHONPATH=str(copied_scripts))
    env.pop('PYTHONPYCACHEPREFIX', None)
    baseline = subprocess.run(cmd, cwd=path.parent, env=env, capture_output=True, text=True)
    assert baseline.returncode == 0 and 'skipped=' not in baseline.stderr, baseline.stderr
    good = '''with self._loaded(), mock.patch.object(
                corpus.vp, "MEMBER_ID_LABEL_RE", re.escape(corpus.vp.MEMBER_ID_LABEL)), \\
                mock.patch.dict(os.environ, {"WAVEFOUNDRY_TEST_PROFILE": "declared"}):'''
    bad = '''with self._loaded(), mock.patch.dict(os.environ, {"WAVEFOUNDRY_TEST_PROFILE": "declared"}):'''
    source = path.read_text()
    assert source.count(good) == 1
    path.write_text(source.replace(good, bad))
    mutant = subprocess.run(cmd, cwd=path.parent, env=env, capture_output=True, text=True)
    assert mutant.returncode != 0 and 'FAILED (failures=1)' in mutant.stderr
    assert '0 not greater than 100' in mutant.stderr and 'skipped=' not in mutant.stderr
    print(json.dumps({'copied_files': copied, 'baseline': baseline.stderr,
                      'deleted_derived_regex_fix': mutant.stderr,
                      'known_bad_detected': True}, indent=2))
