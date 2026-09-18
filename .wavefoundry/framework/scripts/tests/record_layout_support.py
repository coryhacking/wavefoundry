"""Test support for the record-layout constants (wave 1y0gz).

The layout is defined by module constants in ``record_paths`` (no runtime
configuration), so a test that wants a relocated or nested layout patches the
constants. Two forms:

* :func:`patch_layout` / :func:`apply_layout` for in-process tests. Every
  loaded copy of ``record_paths`` is patched (the server support loader may
  hold its own module object), and the docs-lint root cache is cleared.
* :func:`run_script_with_layout` for subprocess CLI tests (docs-lint, the
  gardener): the constants are set in the child before the script runs.
"""
from __future__ import annotations

import contextlib
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1]

_KEYS = {"waves_root": "WAVES_ROOT", "plans_root": "PLANS_ROOT", "nested": "NESTED", "max_depth": "MAX_DEPTH"}


def _record_paths_modules(extra: tuple[Any, ...] = ()) -> list[Any]:
    found: list[Any] = []
    for name, mod in list(sys.modules.items()):
        if mod is not None and (name == "record_paths" or name.endswith(".record_paths")):
            found.append(mod)
    for mod in extra:
        if mod is not None:
            found.append(mod)
    if not found:
        import record_paths  # noqa: WPS433 (test support)

        found.append(record_paths)
    return list(dict.fromkeys(found))


def _values(**kwargs: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, attr in _KEYS.items():
        if key in kwargs:
            out[attr] = kwargs[key]
    return out


def _clear_lint_cache() -> None:
    for name, mod in list(sys.modules.items()):
        if mod is not None and name.endswith("wave_lint_lib.helpers"):
            clear = getattr(mod, "read_text_cache_clear", None)
            if clear is not None:
                clear()


@contextlib.contextmanager
def patch_layout(*, modules: tuple[Any, ...] = (), **kwargs: Any):
    """Patch ``WAVES_ROOT`` / ``PLANS_ROOT`` / ``NESTED`` / ``MAX_DEPTH`` on
    every loaded ``record_paths`` (plus ``modules``) for the block."""
    values = _values(**kwargs)
    with contextlib.ExitStack() as stack:
        for mod in _record_paths_modules(modules):
            for attr, value in values.items():
                stack.enter_context(mock.patch.object(mod, attr, value))
        _clear_lint_cache()
        try:
            yield
        finally:
            _clear_lint_cache()


def apply_layout(testcase: Any, *, modules: tuple[Any, ...] = (), **kwargs: Any) -> None:
    """``patch_layout`` bound to a ``TestCase``'s cleanup."""
    cm = patch_layout(modules=modules, **kwargs)
    cm.__enter__()
    testcase.addCleanup(cm.__exit__, None, None, None)


def layout_prelude(**kwargs: Any) -> str:
    """Python source that sets the constants in a fresh interpreter."""
    lines = [
        "import sys",
        f"sys.path.insert(0, {str(SCRIPTS_DIR)!r})",
        "import record_paths as _rp",
    ]
    for attr, value in _values(**kwargs).items():
        lines.append(f"_rp.{attr} = {value!r}")
    return "\n".join(lines)


def run_script_with_layout(
    script: Path, args: list[str], *, layout: dict[str, Any], cwd: Path | None = None, env: dict | None = None
) -> subprocess.CompletedProcess[str]:
    """Run ``script`` as ``__main__`` in a child interpreter whose
    ``record_paths`` constants are set to ``layout`` first."""
    code = "\n".join(
        [
            layout_prelude(**layout),
            "import runpy",
            f"sys.argv = [{str(script)!r}] + {list(args)!r}",
            f"runpy.run_path({str(script)!r}, run_name='__main__')",
        ]
    )
    return subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
