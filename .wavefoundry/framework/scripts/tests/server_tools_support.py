"""Shared server-tool test support (wave 1tmtx / 1tm6d).

Pure fixture helpers and the framework-wide subprocess-scan seams used
by the test_server_tools* shards and by test_render_platform_surfaces
and test_graph_query. Deliberately NOT unittest-discovered: no TestCase,
no test_* names, no module-level mutable/cache/singleton server state —
helpers mutate process state only when explicitly called (Requirement 6
of 1tm6d).
"""
from __future__ import annotations

import ast
import asyncio
import contextlib
import hashlib
import importlib.util
import inspect
import json
import math
import os
import stat
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SPAWN_ATTRS = {"run", "Popen", "call", "check_output", "check_call"}



SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = SCRIPTS_ROOT / "server.py"


def integrity_checks(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "test_ran_without_unintended_skip": True,
        "public_path_reached": True,
        "boundary_values_realistic": True,
        "assertions_non_vacuous": True,
        "known_bad_detected": True,
        "known_bad_detection_method": "known-bad mutation was detected",
    }
    values.update(overrides)
    return values


def load_server():
    """Load server.py (which imports server_impl) and return server_impl.

    Returning server_impl ensures patch.object(self.srv, "foo") patches the
    module where server_impl functions look up their siblings at call time,
    so mocks are visible to internal function-to-function calls.
    """
    sys.modules.pop("server", None)
    spec = importlib.util.spec_from_file_location("server", SERVER_PATH)
    srv_mod = importlib.util.module_from_spec(spec)
    sys.modules["server"] = srv_mod
    spec.loader.exec_module(srv_mod)
    impl = sys.modules["server_impl"]
    # Wave 1p2q3 (1p2w5): run_index_rebuild gained a post-Popen verification
    # window (default 1.5s) to detect subprocesses that exit early with a
    # lock-busy error. Many tests across this file rely on the historical
    # race window where `subprocess.Popen` returns instantly and downstream
    # reads of the fixture graph happen before the spawned subprocess can
    # rewrite it. Zero out the verify timeout at module-load time so all
    # tests inherit the original timing. Tests that exercise the
    # verification behavior itself can locally re-patch the constant.
    if hasattr(impl, "_INDEX_BUILD_VERIFY_TIMEOUT_SECONDS"):
        impl._INDEX_BUILD_VERIFY_TIMEOUT_SECONDS = 0.0
    return impl


def load_thin_runner():
    """Return the thin runner module (server.py). Call load_server() first."""
    return sys.modules.get("server")


def _make_repo(tmp: Path, files: dict[str, str] | None = None) -> Path:
    """Create a minimal project directory with workflow-config.json."""
    (tmp / "docs").mkdir(parents=True, exist_ok=True)
    (tmp / "docs" / "workflow-config.json").write_text(
        json.dumps({"lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0}}),
        encoding="utf-8",
    )
    if files:
        for rel, content in files.items():
            p = tmp / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
    return tmp


def _store_read_meta(index_dir: Path) -> dict:
    """1sed6: read the build-state snapshot back from the store."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "index_state_store", Path(__file__).resolve().parents[1] / "index_state_store.py"
    )
    iss = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(iss)
    return iss.export_meta_snapshot(index_dir) or {}


def _seed_store_state(index_dir: Path, meta: dict) -> None:
    """1sed6: fixtures record build state the way production does — store
    bookkeeping plus a COMPLETED build epoch (readers fail closed without one)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "index_state_store", Path(__file__).resolve().parents[1] / "index_state_store.py"
    )
    iss = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(iss)
    iss.write_build_bookkeeping(index_dir, meta)
    attempt = iss.begin_build_epoch(index_dir, "fixture")
    assert iss.finalize_build_epoch(index_dir, attempt)


def _write_index_layer(root: Path, chunks: list[dict], vectors, *, model: str = "test-model") -> None:
    _write_sqlite_index(root, docs_chunks=chunks, docs_vectors=vectors, model=model)


def _write_sqlite_index(root: Path, *, docs_chunks: list[dict] | None = None, docs_vectors=None, code_chunks: list[dict] | None = None, code_vectors=None, model: str = "test-model") -> None:
    """Write the current native SQLite index fixture.

    Zero-padding synthetic low-dimensional fixtures preserves their cosine geometry.
    """
    import index_state_store as iss
    import sqlite_vector_store as storage
    root.mkdir(parents=True, exist_ok=True)
    content = [layer for layer, chunks in (("docs", docs_chunks), ("code", code_chunks)) if chunks is not None]
    store = iss.IndexStateStore(root)
    try:
        with store._conn:
            for layer, chunks, vectors in (("docs", docs_chunks, docs_vectors), ("code", code_chunks, code_vectors)):
                if chunks is None:
                    continue
                store._conn.execute(f"DELETE FROM chunks_{layer}")
                rows = []
                for i, chunk in enumerate(chunks):
                    row = dict(chunk)
                    vector = list(vectors[i] if i < len(vectors) else vectors[0])
                    row["vector"] = [float(v) for v in vector] + [0.] * (storage.DIMENSIONS - len(vector))
                    row.setdefault("language", None)
                    row.setdefault("section", None)
                    row["tags"] = " ".join(map(str, row["tags"])) if isinstance(row.get("tags"), list) else row.get("tags", "")
                    rows.append(row)
                storage.write_rows(store._conn, layer, rows)
    finally:
        store.close()
    _seed_store_state(root, {"model_versions": {layer: model for layer in content},
                            "content": content, "file_hashes": {}})


def _subprocess_aliases(tree) -> tuple[set, set]:
    """Resolve how `subprocess` is referenced in a module via AST import analysis.

    Returns (module_aliases, direct_callables):
      - module_aliases: names that ARE the subprocess module — `subprocess`, plus any
        `import subprocess as X` (adds X). `module_aliases.run(...)` is a spawn.
      - direct_callables: names bound to spawn funcs via `from subprocess import run as r` →
        {"r"}; a bare `r(...)` Call is then a spawn.
    """
    import ast as _ast
    module_aliases = {"subprocess", "_sp"}
    direct_callables: set = set()
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            for alias in node.names:
                if alias.name == "subprocess":
                    module_aliases.add(alias.asname or "subprocess")
        elif isinstance(node, _ast.ImportFrom) and node.module == "subprocess":
            for alias in node.names:
                name = alias.name
                if name in SPAWN_ATTRS:
                    direct_callables.add(alias.asname or name)
    return module_aliases, direct_callables

def _spawn_calls(tree):
    """Yield ast.Call nodes that are subprocess spawns (any aliased/from-import/os.system/asyncio
    form), so a future addition in ANY of these shapes is caught — not just `subprocess.run(`."""
    import ast as _ast
    module_aliases, direct_callables = _subprocess_aliases(tree)
    for node in _ast.walk(tree):
        if not isinstance(node, _ast.Call):
            continue
        func = node.func
        # subprocess.run / sp.Popen / __import__("subprocess").run, os.system, os.popen,
        # asyncio.create_subprocess_exec/shell, loop.subprocess_exec/shell
        if isinstance(func, _ast.Attribute):
            attr = func.attr
            base = getattr(func.value, "id", None)
            if base in module_aliases and attr in SPAWN_ATTRS:
                yield node
            elif base == "os" and attr in ("system", "popen"):
                yield node
            elif attr in ("create_subprocess_exec", "create_subprocess_shell",
                          "subprocess_exec", "subprocess_shell"):
                yield node  # asyncio.* / loop.* process creation
            elif isinstance(func.value, _ast.Call):
                # __import__("subprocess").run(...) form
                iv = func.value
                if (isinstance(iv.func, _ast.Name) and iv.func.id == "__import__"
                        and iv.args and isinstance(iv.args[0], _ast.Constant)
                        and iv.args[0].value == "subprocess" and attr in SPAWN_ATTRS):
                    yield node
        elif isinstance(func, _ast.Name) and func.id in direct_callables:
            yield node  # `from subprocess import run` → bare run(...)

def _call_kwarg_names(node) -> set:
    """The kwarg names passed DIRECTLY to this Call node (scoped — not a text window)."""
    return {kw.arg for kw in node.keywords if kw.arg is not None}

def _call_has_devnull_or_input(node) -> bool:
    """True iff the spawn Call's OWN kwargs isolate stdin: stdin=...DEVNULL, input=..., or
    `**kwargs` splat (the helper-delegation forms set isolation in the splatted dict)."""
    import ast as _ast
    for kw in node.keywords:
        if kw.arg is None:
            return True  # **kwargs splat — isolation lives in the dict (helper delegation)
        if kw.arg == "input":
            return True
        if kw.arg == "stdin":
            src = _ast.dump(kw.value)
            if "DEVNULL" in src:
                return True
    return False

def _call_has_no_window(node) -> bool:
    """True iff the spawn Call's OWN kwargs suppress the Windows console: a creationflags= that
    references a no-window construct, OR a `**kwargs` splat (helper delegation sets it), OR the
    call routes through subprocess_util.isolated_run/isolated_popen (handled by the caller)."""
    import ast as _ast
    tokens = ("CREATE_NO_WINDOW", "no_window_creationflags", "_windows_no_window_flag",
              "detached_background_creationflags")
    for kw in node.keywords:
        if kw.arg is None:
            return True  # **kwargs splat
        if kw.arg == "creationflags":
            src = _ast.dump(kw.value)
            if any(t in src for t in tokens):
                return True
    return False

def _is_isolated_helper_call(node) -> bool:
    """True iff the Call routes through subprocess_util.isolated_run/isolated_popen (or the .run
    delegation inside subprocess_util itself) — inherently isolated, not a raw spawn to audit."""
    import ast as _ast
    func = node.func
    if isinstance(func, _ast.Attribute) and func.attr in ("isolated_run", "isolated_popen"):
        return True
    return False
