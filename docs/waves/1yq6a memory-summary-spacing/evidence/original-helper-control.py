"""Run current spacing regressions with the original helper, in memory only.

Run from the repository root with the configured test interpreter and -B.
The control succeeds only if the old helper causes assertion failures, not errors.
"""
import ast
import importlib.util
import io
import subprocess
import unittest
from pathlib import Path

path = Path('.wavefoundry/framework/scripts/tests/test_memory_records.py')
spec = importlib.util.spec_from_file_location('spacing_tests', path)
tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tests)
source = subprocess.check_output([
    'git', 'show', 'c4bd0059:.wavefoundry/framework/scripts/memory_records.py',
], text=True)
helper = next(node for node in ast.parse(source).body
              if isinstance(node, ast.FunctionDef)
              and node.name == '_replace_or_insert_metadata')
code = compile(ast.Module(body=[helper], type_ignores=[]), '<original-helper>', 'exec')
original_setup = tests._MemoryCase.setUp


def setup(case):
    original_setup(case)
    exec(code, case.mem.__dict__)
    exec(code, tests.load_server()._memory_mod().__dict__)


tests._MemoryCase.setUp = setup
suite = unittest.TestSuite([
    tests.MemoryMetadataSpacingTests('test_insert_replace_and_repeat_have_one_blank_line'),
    tests.MemoryAgentValidationTests('test_promote_retain_and_reject_persist_compact_judgment'),
])
result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
print(f'Original helper: {result.testsRun} tests, {len(result.failures)} assertion failures, '
      f'{len(result.errors)} errors')
raise SystemExit(0 if len(result.failures) == 11 and not result.errors else 1)
