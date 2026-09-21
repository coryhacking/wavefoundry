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


def review_policy_config(**overrides) -> dict:
    """Return a complete policy block; install under workflow-config's wave_review."""
    return {"enabled": True, "delivery_mode": "targeted", **overrides}


@contextlib.contextmanager
def declared_wave_doc_gates(srv, stubs):
    """Scope caller-owned fakes across all fixture producers, including failures."""
    required = {"run_validate", "run_garden", "_run_post_write_lint",
                "_trigger_background_index_refresh_for_paths"}
    if set(stubs) != required or not all(callable(stubs[key]) for key in required):
        raise ValueError("doc_gate_stubs must supply callable stubs for " + ", ".join(sorted(required)))
    with contextlib.ExitStack() as stack:
        for name, stub in stubs.items():
            stack.enter_context(patch.object(srv, name, stub))
        yield


def make_declared_wave(srv, root, slug, *, status="planned", change_ids=(),
                       ready=False, readiness_run=False, approvals=(), doc_gate_stubs):
    """Build lifecycle prerequisites through real producers, never guessed JSONL.

    Change documents already exist (use the canonical change creator); callers
    may customize their content before admission. The sole synthetic escape is
    the produced Status line, applied after all producers for tests of later
    lifecycle phases. Producers always receive canonical planned state.
    Omission of readiness_run is intentional and supported for negative controls;
    only a final Prepare call independently proves the fixture is ready.
    """
    if ready and not change_ids:
        raise ValueError("ready=True requires at least one admitted change")
    if approvals and not ready:
        raise ValueError("readiness approvals require ready=True")
    if status not in {"planned", "active", "implementing", "paused", "closed"}:
        raise ValueError(f"unsupported synthetic wave status: {status}")

    def successful(step, response):
        if response.get("status") != "ok":
            raise AssertionError(f"{step} refused: {response!r}")
        return response["data"]

    with declared_wave_doc_gates(srv, doc_gate_stubs):
        made = successful("create wave", srv.wf_create_wave_response(root, slug, mode="create"))
        wave_id, wave_md = made["wave_id"], root / made["path"]
        for change_id in change_ids:
            successful("admit change", srv.wf_add_change_response(root, wave_id, change_id, mode="create"))
        if ready:
            prepared = srv.wf_prepare_wave_response(root, wave_id, mode="ready")
            blockers = [d for d in prepared.get("diagnostics", ()) if not d.get("advisory")]
            if (prepared.get("status") not in {"ok", "error"}
                    or any(d["code"] != "missing_wave_council_signoff" for d in blockers)
                    or (prepared.get("status") == "error" and not blockers)):
                raise AssertionError(f"prepare receipt refused: {prepared!r}")
            records, errors = srv.read_review_event_ledger(wave_md)
            if errors or not any(r.get("record_type") == "review_policy_receipt" for r in records):
                raise AssertionError(f"prepare did not publish a receipt: {errors!r}; {prepared!r}")
        if readiness_run:
            successful("readiness run", srv.wf_review_event_response(
                root, wave_id, event="run", actor="wave-council", context_id="fixture-readiness",
                mode="create", run_kind="readiness", cycle=0))
        for key in approvals:
            actor = "wave-council" if key.startswith("wave-council") else key
            successful("readiness approval", srv.wf_review_event_response(
                root, wave_id, event="approval", actor=actor, context_id="fixture-approval-" + key,
                mode="create", signoff_key=key, approval_phase="readiness",
                fresh_context=True, independent=True,
                evidence={"observed": "fixture approval", "artifact_or_test_id": "test:declared-wave"},
                integrity_checks=integrity_checks()))
        if status != "planned":
            text, count = re.subn(r"(?m)^Status: planned$", f"Status: {status}", wave_md.read_text(), count=1)
            if count != 1:
                raise AssertionError("created wave must have exactly one planned Status line")
            wave_md.write_text(text, encoding="utf-8")
        return wave_id, wave_md


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
    # Complete fixture publications carry the same producer provenance as a
    # real build. Preserve explicit caller versions for compatibility tests.
    import index_compatibility
    meta = dict(meta)
    meta.setdefault("walker_version", str(index_compatibility.SUPPORTED["walker_version"]))
    meta.setdefault("chunker_versions", {
        layer: str(index_compatibility.SUPPORTED["chunker_version"])
        for layer in ("docs", "code")})
    meta.setdefault("model_versions", {layer: "test-model" for layer in ("docs", "code")})
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
