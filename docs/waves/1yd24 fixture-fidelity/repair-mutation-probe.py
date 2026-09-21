"""Replay the six delivery guard deletions without modifying source files."""
import inspect
import io
import json
import unittest
from unittest.mock import patch
import server_tools_support as support
import test_declared_wave_fixtures as tests

INPUT_TEST = 'test_invalid_helper_inputs_fail_before_producer_entry'
PREPARE_TEST = 'test_invalid_prepare_envelopes_reject_after_real_receipt_publication'
MUTANTS = [
    ('approvals-require-ready', 'make_declared_wave', 'if approvals and not ready:', 'if False:', INPUT_TEST),
    ('supported-status', 'make_declared_wave', 'if status not in {"planned", "active", "implementing", "paused", "closed"}:', 'if False:', INPUT_TEST),
    ('callable-stubs', 'declared_wave_doc_gates', ' or not all(callable(stubs[key]) for key in required)', '', INPUT_TEST),
    ('prepare-status', 'make_declared_wave', 'prepared.get("status") not in {"ok", "error"}', 'False', PREPARE_TEST),
    ('prepare-error-blockers', 'make_declared_wave', 'or (prepared.get("status") == "error" and not blockers)', 'or False', PREPARE_TEST),
    ('prepare-unexpected-blocker', 'make_declared_wave', 'or any(d["code"] != "missing_wave_council_signoff" for d in blockers)', 'or False', PREPARE_TEST),
]
rows = []
for name, function, old, new, test in MUTANTS:
    source = inspect.getsource(getattr(support, function))
    assert source.count(old) == 1, name
    namespace = dict(vars(support))
    exec(compile(source.replace(old, new), '<guard-deletion>', 'exec'), namespace)
    with patch.object(support, function, namespace[function]), patch.object(tests, function, namespace[function]):
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream).run(tests.DeclaredWaveFixtureTests(test))
    rows.append({'mutant': name, 'test': test, 'failures': len(result.failures),
                 'errors': len(result.errors), 'skips': len(result.skipped),
                 'killed': bool(result.failures) and not result.errors and not result.skipped})
print(json.dumps(rows, indent=2))
assert all(row['killed'] for row in rows), rows
