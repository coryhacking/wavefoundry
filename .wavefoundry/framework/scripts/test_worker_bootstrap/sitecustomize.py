"""Worker-only startup shim, chaining the next filesystem sitecustomize."""
from importlib import machinery, util
import os
from pathlib import Path
import sys


_directory = Path(__file__).resolve().parent
_visited = getattr(sys, "_wavefoundry_test_bootstrap_dirs", set())
_visited.add(_directory)
sys._wavefoundry_test_bootstrap_dirs = _visited
if "WAVEFOUNDRY_TEST_WORKER_PROTECTED_ROOTS" in os.environ:
    _name = "test_worker_guard"
    _guard = sys.modules.get(_name)
    try:
        if _guard is None:
            _source = _directory.parent / "test_worker_guard.py"
            _spec = util.spec_from_file_location(_name, _source)
            _guard = util.module_from_spec(_spec)
            sys.modules[_name] = _guard
            # Preserve import metadata but execute source directly: -B alone
            # prevents cache writes, not reads of adjacent unchecked bytecode.
            exec(compile(_source.read_bytes(), str(_source), "exec"), _guard.__dict__)
        _guard.install()
    except Exception as _error:
        # site normally suppresses Exception. A broken guard must stop startup;
        # exceptions from the user's chained customization retain normal rules.
        raise SystemExit(f"test-worker guard installation failed: {_error}") from _error

# Nested runners may inherit another copy of this shim. Exclude visited copies
# and their aliases so chaining reaches the user's customization exactly once.
_search = [entry for entry in sys.path if Path(entry or os.curdir).resolve() not in _visited]
_next = machinery.PathFinder.find_spec("sitecustomize", _search)
if _next is not None and _next.loader is not None:
    _customization = util.module_from_spec(_next)
    sys.modules["sitecustomize"] = _customization
    _next.loader.exec_module(_customization)
