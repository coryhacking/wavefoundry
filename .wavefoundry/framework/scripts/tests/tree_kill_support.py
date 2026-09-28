"""Test support for wave 1z8tr (change 1z8qm).

Setup installs, the upgrade runner's hooks, summary child and graph-builder
probe, and the techdocs audit worker call ``subprocess_util.run_with_tree_kill``.
Tests written before that routing fake these calls by patching
``subprocess.run`` or ``subprocess_util.isolated_run``. Rather than rewrite each
fake, a module that holds such tests routes ``run_with_tree_kill`` back through
``isolated_run`` (looked up at call time), so every existing fake still
intercepts and no test can reach a real pip, uv, venv or network call. The
routing itself, and the tree kill, are pinned without this shim in
``test_tree_kill_routing.py``.
"""
from __future__ import annotations

from unittest import mock

import subprocess_util


def route_tree_kill_through_isolated_run():
    """A patcher (call ``start``/``stop``) for the shim described above."""

    def _delegate(cmd, **kwargs):
        return subprocess_util.isolated_run(cmd, **kwargs)

    return mock.patch.object(subprocess_util, "run_with_tree_kill", side_effect=_delegate)


class ModuleShim:
    """``setUpModule``/``tearDownModule`` pair installing the shim for one test module."""

    def __init__(self) -> None:
        self._patcher = None

    def start(self) -> None:
        self._patcher = route_tree_kill_through_isolated_run()
        self._patcher.start()

    def stop(self) -> None:
        if self._patcher is not None:
            self._patcher.stop()
            self._patcher = None
