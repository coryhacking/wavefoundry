"""Build a disposable scripts tree that mimics the 1yzd0 target layout.

Layout written under <dest>/scripts:
  server.py                         thin runner (same reload code shape as HEAD/v1.25/v1.26:
                                    ``server_impl._script_cache.clear(); server_impl = importlib.reload(server_impl)``)
  shared_substrate.py               retained flat shared module (like review_evidence)
  retained_tool.py                  retained flat script loaded through _load_script
  server_impl.py, graph_handlers.py flat compatibility modules (shape depends on STRATEGY)
  wf_alias_finder.py                (strategy c only) meta-path alias finder
  wavefoundry_server/__init__.py    light initializer, no imports
  wavefoundry_server/server_impl.py canonical composition root
  wavefoundry_server/graph_handlers.py canonical handler

Knobs:
  strategy   : a | b | b2 | c | old   ("old" = pre-migration flat monolith, for the old-runner transition)
  purge      : both | flat_only       (reload purge keys in the canonical server_impl)
  scripts_dir: root | naive           (SCRIPTS_DIR = parent.parent vs the naive Path(__file__).parent)
  version    : string baked into IMPL_VERSION / HANDLER_VERSION (edited to prove reload freshness)
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

RUNNER = '''
import importlib, sys
from pathlib import Path
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
if (_SCRIPTS_DIR / "wf_alias_finder.py").exists():
    import wf_alias_finder
    wf_alias_finder.install()
import server_impl
_RUNNER_CAPTURED_IDENTITY = "runner-captured"

def _record_runner_identity():
    # same shape as server._record_runner_identity: attribute writes on the runner's module ref
    server_impl._SETUP_LOADED_IDENTITY = _RUNNER_CAPTURED_IDENTITY
    setter = getattr(server_impl, "set_runner_version", None)
    if setter:
        setter("runner-v")

def perform_reload():
    global server_impl
    server_impl._script_cache.clear()
    for _key in list(sys.modules):
        if _key.startswith("wave_lint_lib"):
            del sys.modules[_key]
    server_impl = importlib.reload(server_impl)
    _record_runner_identity()
    return server_impl

_record_runner_identity()
'''

SHARED = '''
LOADS = globals().get("LOADS", 0) + 1
SUBSTRATE_VERSION = "{version}"
'''

RETAINED_TOOL = '''
TOOL_VERSION = "{version}"
'''

PKG_INIT = '''"""Wavefoundry server package. Deliberately imports nothing."""
'''

PKG_IMPL = '''"""Canonical composition root (demo)."""
import importlib.util
import sys
from pathlib import Path

_PURGE_MODE = "{purge}"
_FLAT = {{"graph_handlers", "shared_substrate"}}
_PKG = {{"wavefoundry_server.graph_handlers"}}
for _key in list(sys.modules):
    if _key in _FLAT or (_PURGE_MODE == "both" and _key in _PKG):
        del sys.modules[_key]
if _PURGE_MODE == "both":
    _parent = sys.modules.get("wavefoundry_server")
    if _parent is not None and "graph_handlers" in vars(_parent):
        delattr(_parent, "graph_handlers")

SCRIPTS_DIR = {scripts_dir_expr}
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import shared_substrate
from {handler_import} import graph_response, _HCACHE

IMPL_VERSION = "{version}"
_CACHE = {{}}
_runner_version = None
if "_SETUP_LOADED_IDENTITY" not in globals():
    _SETUP_LOADED_IDENTITY = "captured-from-disk"


def set_runner_version(value):
    global _runner_version
    _runner_version = value


def read_runner_version():
    return _runner_version


def read_identity():
    return _SETUP_LOADED_IDENTITY


def shared_helper():
    return "real-shared-helper"


_script_cache = {{}}


def _load_script(name):
    key = f"_wavefoundry_{{name}}"
    if key in _script_cache:
        return _script_cache[key]
    spec = importlib.util.spec_from_file_location(key, SCRIPTS_DIR / f"{{name}}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[key] = mod
    spec.loader.exec_module(mod)
    _script_cache[key] = mod
    return mod


def respond():
    return graph_response()
'''

PKG_HANDLER = '''"""Canonical graph handler (demo)."""
HANDLER_VERSION = "{version}"
_HCACHE = {{}}


def helper():
    return "real-graph-helper"


def graph_response():
    import server_impl  # function-local public import, as the real handlers do
    return {{
        "handler_version": HANDLER_VERSION,
        "helper": helper(),
        "shared": server_impl.shared_helper(),
        "impl_version_seen_by_handler": server_impl.IMPL_VERSION,
    }}
'''

FLAT_A = '''"""Compatibility alias for wavefoundry_server.{mod}; no business logic."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("wavefoundry_server.{mod}")
'''

FLAT_B = '''"""Compatibility stub (star re-export) for wavefoundry_server.{mod}."""
from wavefoundry_server.{mod} import *  # noqa: F401,F403
'''

FLAT_B2 = '''"""Compatibility stub (star re-export + __getattr__ forwarding)."""
import wavefoundry_server.{mod} as _impl
from wavefoundry_server.{mod} import *  # noqa: F401,F403


def __getattr__(name):
    return getattr(_impl, name)
'''

FINDER = '''"""Meta-path alias finder: flat names resolve to package modules."""
import importlib
import importlib.abc
import importlib.util
import sys

ALIASES = {"server_impl": "wavefoundry_server.server_impl",
           "graph_handlers": "wavefoundry_server.graph_handlers"}


class _AliasLoader(importlib.abc.Loader):
    def __init__(self, target):
        self.target = target

    def create_module(self, spec):
        return importlib.import_module(self.target)

    def exec_module(self, module):
        return None


class AliasFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name in ALIASES:
            return importlib.util.spec_from_loader(name, _AliasLoader(ALIASES[name]))
        return None


def install():
    if not any(isinstance(f, AliasFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, AliasFinder())
'''

OLD_FLAT_IMPL = '''"""Pre-migration flat monolith (demo of an installed 1.25/1.26 tree)."""
import sys
from pathlib import Path
for _key in list(sys.modules):
    if _key in {{"graph_handlers", "shared_substrate"}}:
        del sys.modules[_key]
SCRIPTS_DIR = Path(__file__).resolve().parent
import shared_substrate
from graph_handlers import graph_response, _HCACHE
IMPL_VERSION = "{version}"
_CACHE = {{}}
_runner_version = None
if "_SETUP_LOADED_IDENTITY" not in globals():
    _SETUP_LOADED_IDENTITY = "captured-from-disk"
def set_runner_version(value):
    global _runner_version
    _runner_version = value
def read_runner_version():
    return _runner_version
def read_identity():
    return _SETUP_LOADED_IDENTITY
def shared_helper():
    return "real-shared-helper"
_script_cache = {{}}
def respond():
    return graph_response()
'''


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")


def build(dest: Path, *, strategy: str, purge: str = "both", scripts_dir: str = "root",
          version: str = "v1", handler_import: str = "wavefoundry_server.graph_handlers",
          flat_files: bool = True) -> Path:
    s = dest / "scripts"
    for stale in ("server_impl.py", "graph_handlers.py", "wf_alias_finder.py"):
        (s / stale).unlink(missing_ok=True)
    write(s / "server.py", RUNNER)
    write(s / "shared_substrate.py", SHARED.format(version=version))
    write(s / "retained_tool.py", RETAINED_TOOL.format(version=version))
    if strategy == "old":
        write(s / "server_impl.py", OLD_FLAT_IMPL.format(version=version))
        write(s / "graph_handlers.py", PKG_HANDLER.format(version=version))
        return s
    expr = "Path(__file__).resolve().parent.parent" if scripts_dir == "root" else "Path(__file__).resolve().parent"
    write(s / "wavefoundry_server" / "__init__.py", PKG_INIT)
    write(s / "wavefoundry_server" / "server_impl.py",
          PKG_IMPL.format(purge=purge, scripts_dir_expr=expr, version=version, handler_import=handler_import))
    write(s / "wavefoundry_server" / "graph_handlers.py", PKG_HANDLER.format(version=version))
    flat = {"a": FLAT_A, "b": FLAT_B, "b2": FLAT_B2, "c": FLAT_A}[strategy]
    if flat_files:
        for mod in ("server_impl", "graph_handlers"):
            write(s / f"{mod}.py", flat.format(mod=mod))
    if strategy == "c":
        write(s / "wf_alias_finder.py", FINDER)
    return s


if __name__ == "__main__":
    build(Path(sys.argv[1]), strategy=sys.argv[2])
