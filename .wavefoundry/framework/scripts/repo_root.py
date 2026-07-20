#!/usr/bin/env python3
"""Shared cwd-independent repo-root discovery (wave 1t3gt / change 1t1b3).

Single source for the script-location-anchored discovery pattern originally
implemented in ``server_impl._discover_root``. Every framework script lives at
``<root>/.wavefoundry/framework/scripts/``, so the caller's own ``__file__``
anchors the served repo without depending on the process cwd. A cwd-anchored
``--root`` default silently created ``.wavefoundry/index/`` state wherever the
process happened to run from; this module exists so no CLI entry point repeats
that defect.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

_ROOT_ENV_KEYS = ("CLAUDE_PROJECT_DIR", "PROJECT_ROOT", "REPO_ROOT")


def _is_root(path: Path) -> bool:
    return (path / "docs" / "workflow-config.json").is_file()


def discover_root(override: Optional[str] = None) -> Path:
    """Resolve the repo root, anchored by ``docs/workflow-config.json``, cwd-independently.

    Priority — first candidate carrying the marker wins:
    1. an explicit ``override`` (``--root`` / MCP tool arg);
    2. this module's own install location — ``<root>/.wavefoundry/framework/scripts/``,
       so ``parents[3]`` IS the served repo, independent of the host's cwd;
    3. host / generic project-root env vars, used only when they line up with a real
       Wavefoundry tree (the marker), so a stray var can't mis-root us;
    4. CWD and its parents.
    Falls back to the script root (if it looks like a Wavefoundry tree) else CWD.
    """
    if override:
        return Path(override).expanduser().resolve()
    # Resolved at call time from the module global so tests can fake the
    # install location by patching ``repo_root.__file__``.
    script_root = Path(__file__).resolve().parents[3]
    if _is_root(script_root):
        return script_root
    for env_key in _ROOT_ENV_KEYS:
        raw = os.environ.get(env_key)
        if raw:
            candidate = Path(raw).expanduser().resolve()
            if _is_root(candidate):
                return candidate
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if _is_root(candidate):
            return candidate
    return script_root if (script_root / ".wavefoundry").is_dir() else cwd
