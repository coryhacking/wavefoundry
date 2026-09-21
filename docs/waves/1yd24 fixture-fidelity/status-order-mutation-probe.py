"""Independent cycle-3 focused replay; source mutations exist only in memory."""
import inspect
import io
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
import server_tools_support as support
import test_declared_wave_fixtures as tests

packet = json.loads(Path('docs/waves/1yd24 fixture-fidelity/delivery-fingerprint.json').read_text())
def verify_tree():
    for path, expected in packet['paths'].items():
        actual = subprocess.check_output(['git', 'hash-object', path], text=True).strip()
        assert actual == expected, (path, actual, expected)
verify_tree()
source = inspect.getsource(support.make_declared_wave)
start = source.index('        if status != "planned":')
end = source.index('        return wave_id, wave_md', start)
block = source[start:end]
early = source[:start] + source[end:]
early = early.replace('        if ready:\n', block + '        if ready:\n', 1)
ready = source.replace('{"planned", "active",', '{"planned", "ready", "active",', 1)
rows = []
for name, changed, test in [
    ('old-status-order', early, 'test_real_producers_run_in_order_and_stubs_restore'),
    ('legacy-ready-restored', ready, 'test_invalid_helper_inputs_fail_before_producer_entry'),
]:
    assert changed != source
    namespace = dict(vars(support))
    exec(compile(changed, '<status-order-mutant>', 'exec'), namespace)
    with patch.object(support, 'make_declared_wave', namespace['make_declared_wave']), patch.object(tests, 'make_declared_wave', namespace['make_declared_wave']):
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream).run(tests.DeclaredWaveFixtureTests(test))
    rows.append({'mutant': name, 'test': test, 'failures': len(result.failures), 'errors': len(result.errors), 'skips': len(result.skipped), 'killed': bool(result.failures) and not result.errors and not result.skipped})
verify_tree()
print(json.dumps({'tree_fingerprint': packet['tree_fingerprint'], 'rows': rows}, indent=2))
assert all(row['killed'] for row in rows), rows
