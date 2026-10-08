"""Distribution-declared MCP tool extensions (wave 1yv9l, change 1yuc4).

Every case runs the real server in a scratch copy of the scripts tree, because
declared extension modules must sit directly in the scripts directory. One
subprocess per mode drives ``server.build_server`` / ``perform_mcp_reload`` /
``register_mcp_surface`` and reports observations as JSON; the assertions
below judge them.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
from framework_files import framework_source_files  # wf_server-aware source locations (wave 1yzd0)


def _disk_declaration(scripts: Path) -> "dict[str, object] | None":
    """The ``EXTENSION_*`` constants assigned in ``mcp_tool_extensions.py`` on
    disk (the last assignment wins), or ``None`` when one cannot be read as a
    literal (a computed value or an augmented assignment). Read from the file,
    not the module: the census tests run under the base declaration, which
    hides what a distribution declares."""
    import ast
    from record_layout_support import SHIPPED_DECLARATION
    values: dict[str, object] = {}
    tree = ast.parse((scripts / "mcp_tool_extensions.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets = [node.target]
        else:
            continue
        for target in targets:
            if not (isinstance(target, ast.Name) and target.id in SHIPPED_DECLARATION):
                continue
            if isinstance(node, ast.AugAssign) or node.value is None:
                return None
            try:
                values[target.id] = ast.literal_eval(node.value)
            except Exception:  # noqa: BLE001 - any unreadable value is "not a literal"
                return None
    # A constant not assigned at top level by a plain name (inside an ``if``,
    # by unpacking) cannot be read either.
    if set(SHIPPED_DECLARATION) - set(values):
        return None
    return values


def _normalized_declaration(value: object) -> object:
    """Tuples and lists compare alike (``()`` and ``[]`` both mean empty)."""
    if isinstance(value, (tuple, list)):
        return [_normalized_declaration(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalized_declaration(item) for key, item in value.items()}
    return value


def _flat_imports(path: Path, flat: "set[str]") -> "set[str]":
    """The flat script modules ``path`` imports anywhere in its body (AST)."""
    import ast
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            found.add(node.module.split(".")[0])
    return found & flat


def framework_script_census_problems(scripts: Path, listed: "frozenset[str]", stems: "set[str]") -> "list[str]":
    """Problems with ``FRAMEWORK_SCRIPT_MODULE_NAMES`` (``listed``) against the
    flat scripts on disk (``stems``). Every listed module must exist. On the
    stock declaration the unlisted scripts must be none (upstream stays
    exact). When the declaration on disk is a distribution's, its declared
    modules are its own and a module it never declared is allowed unless the
    server (``server.py``, ``wf_server/``) or a listed module imports it: a
    framework script reached that way must be listed. Many framework scripts
    are command-line entry points or loaded by name, so no import closure can
    stand in for the exact stock check."""
    from record_layout_support import SHIPPED_DECLARATION
    problems: list[str] = []
    missing = sorted(listed - stems)
    if missing:
        problems.append("listed framework script(s) missing from disk: " + ", ".join(missing))
    declaration = _disk_declaration(scripts)
    if declaration is None:
        # Fail closed: an unreadable declaration must not drop the exact check.
        problems.append("mcp_tool_extensions.py declares an EXTENSION_* constant that is not a plain literal")
        return problems
    if all(
        _normalized_declaration(declaration.get(name)) == _normalized_declaration(SHIPPED_DECLARATION[name])
        for name in SHIPPED_DECLARATION
    ):
        unlisted = sorted(stems - listed)
        if unlisted:
            problems.append("unlisted flat script(s) on a stock declaration: " + ", ".join(unlisted))
        return problems
    declared = set(declaration.get("EXTENSION_MODULES", ())) | set(declaration.get("EXTENSION_HELPER_MODULES", ()))
    sources = [scripts / "server.py", *sorted((scripts / "wf_server").rglob("*.py"))]
    sources += [scripts / f"{name}.py" for name in sorted(listed & stems)]
    reached: set[str] = set()
    for source in sources:
        if source.is_file():
            reached |= _flat_imports(source, stems)
    unlisted = sorted(reached - listed - declared)
    if unlisted:
        problems.append("server-reachable flat script(s) not listed: " + ", ".join(unlisted))
    return problems

_DRIVER = r'''
import asyncio, contextlib, hashlib, inspect, json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tests"))
from server_tools_support import _make_repo, load_server, load_thin_runner

SCRATCH = Path.cwd()
DECL = SCRATCH / "mcp_tool_extensions.py"
DECL_ORIG = DECL.read_text()
MODE = sys.argv[1]

ACME = """
import server_impl

def register(mcp, get_handler):
    @mcp.tool()
    def acme_echo(text: str = "", **kwargs):
        bad = server_impl.ensure_no_extra_args("acme_echo", kwargs)
        if bad is not None:
            return bad
        return {"status": "ok", "data": {"echo": text, "version": "v1"}}

    @mcp.tool()
    def acme_write(**kwargs):
        bad = server_impl.ensure_no_extra_args("acme_write", kwargs)
        if bad is not None:
            return bad
        return {"status": "ok", "data": {"wrote": True}}

    @mcp.tool()
    def wf_current_wave(**kwargs):
        bad = server_impl.ensure_no_extra_args("wf_current_wave", kwargs)
        if bad is not None:
            return bad
        return {"status": "ok", "data": {"overridden": "wf_current_wave"}}

    @mcp.tool()
    def wf_create_wave(slug: str, mode: str = "dry_run", **kwargs):
        bad = server_impl.ensure_no_extra_args("wf_create_wave", kwargs)
        if bad is not None:
            return bad
        probe = getattr(server_impl, "_WF_LOCK_PROBE", None) or {}
        return {"status": "ok", "data": {"overridden": "wf_create_wave", "slug": slug, "lock_held": probe.get("held")}}
"""

STRAY = """
def register(mcp, get_handler):
    @mcp.tool()
    def acme_stray(**kwargs):
        return {"status": "ok"}
"""

GOOD_DECL = """
EXTENSION_MODULES = ("acme_tools",)
EXTENSION_TOOL_PREFIXES = ("acme_",)
EXTENSION_TOOL_TIERS = {"acme_echo": "read", "acme_write": "write"}
EXTENSION_OVERRIDES = {"acme_tools": ("wf_current_wave", "wf_create_wave")}
"""

def write_module(name, src):
    (SCRATCH / f"{name}.py").write_text(src)

def table(mcp):
    return mcp._tool_manager._tools

def markers(mcp, name):
    return list(getattr(table(mcp)[name].fn, "__wf_middleware__", ()) or ())

def call(mcp, name, **kwargs):
    return table(mcp)[name].fn(**kwargs)

def ccall(mcp, name, args=None):
    """Call through FastMCP's real client path (argument model, is_async, run)."""
    result = asyncio.run(mcp.call_tool(name, args or {}))
    if isinstance(result, tuple):
        structured = result[1]
        if isinstance(structured, dict):
            return structured.get("result", structured)
        result = result[0]
    if isinstance(result, dict):
        return result
    return json.loads(result[0].text)

def install_lock_probe(impl):
    original = impl._lifecycle_mutation_lock
    state = {"held": False}

    @contextlib.contextmanager
    def probe(root):
        with original(root):
            state["held"] = True
            try:
                yield
            finally:
                state["held"] = False

    impl._lifecycle_mutation_lock = probe
    impl._WF_LOCK_PROBE = state

# Wave 1z8oz fixtures.
ALIAS_DECL = """
EXTENSION_TOOL_PREFIXES = ("fork_",)
EXTENSION_TOOL_ALIASES = {
    "fork_close_container": "wf_close_wave",
    "fork_add_change": "wf_add_change",
    "fork_current": "wf_current_wave",
    "fork_current_again": "wf_current_wave",
}
EXTENSION_HIDDEN_TOOLS = ("wf_current_wave",)
"""

REPLACE_DECL = """
EXTENSION_MODULES = ("fork_tools",)
EXTENSION_TOOL_PREFIXES = ("fork_",)
EXTENSION_REPLACEMENTS = {"fork_tools": {
    "wf_close_wave": {"alias_for_core": "fork_close_container"},
    "wf_review_event": {"alias_for_core": "fork_review_event_core"},
    "wf_help": {"alias_for_core": "fork_help_core", "tier": "write"},
    "memory_validate": {"alias_for_core": "fork_memory_validate_core", "tier": "write"},
    "wf_current_wave": {"alias_for_core": "fork_current_core"},
}}
"""

FORK = """
import server_impl

def register(mcp, get_handler):
    @mcp.tool()
    def wf_close_wave(item: str, **kwargs):
        bad = server_impl.ensure_no_extra_args("wf_close_wave", kwargs)
        if bad is not None:
            return bad
        return {"status": "ok", "data": {"closed_item": item},
                "next_tools": ["wf_close_wave"], "usage": "wf_close_wave(item=...)"}

    @mcp.tool()
    def wf_review_event(note: str, **kwargs):
        bad = server_impl.ensure_no_extra_args("wf_review_event", kwargs)
        if bad is not None:
            return bad
        return {"status": "ok", "data": {"note": note}}

    @mcp.tool()
    def wf_help(topic: str = "", **kwargs):
        bad = server_impl.ensure_no_extra_args("wf_help", kwargs)
        if bad is not None:
            return bad
        return {"status": "ok", "data": {"fork_help": topic}}

    @mcp.tool()
    def memory_validate(record: str = "", **kwargs):
        bad = server_impl.ensure_no_extra_args("memory_validate", kwargs)
        if bad is not None:
            return bad
        return {"status": "ok", "data": {"fork_validate": record}}

    @mcp.tool()
    def wf_current_wave(scope: str = "", **kwargs):
        bad = server_impl.ensure_no_extra_args("wf_current_wave", kwargs)
        if bad is not None:
            return bad
        return {"status": "ok", "data": {"fork_scope": scope}}
"""

# Wave 1zim3 fixtures: parameter-mapped aliases and an override delegating to
# the core handler.
PARAM_DECL = """
EXTENSION_MODULES = ("fork_delegate",)
EXTENSION_TOOL_PREFIXES = ("fork_",)
EXTENSION_TOOL_TIERS = {"fork_echo": "read"}
EXTENSION_OVERRIDES = {"fork_delegate": ("wf_remove_change",)}
EXTENSION_TOOL_ALIASES = {
    "fork_say": "fork_echo",
    "fork_say_whole": "fork_echo",
    "fork_read_raw": "code_read",
    "fork_add_wave": "wf_add_change",
    "fork_add_wave_now": "wf_add_change",
    "fork_review_prepare": "wf_review_wave",
    "fork_say_plain": "fork_echo",
    "fork_get_change": "wf_get_change",
}
EXTENSION_TOOL_PARAMETERS = {
    "fork_say": {"rename": {"words": "text"}, "description": "  Echo the given words back. Provide words; count repeats them.\\n"},
    "fork_say_whole": {"fixed": {"ratio": 1, "tags": ["a"]}},
    "fork_read_raw": {"fixed": {"with_line_numbers": False}},
    "fork_add_wave": {"rename": {"set_id": "wave_id", "wave_id": "change_id"}},
    "fork_add_wave_now": {"rename": {"set_id": "wave_id", "wave_id": "change_id"}, "fixed": {"mode": "create"}},
    "fork_review_prepare": {"fixed": {"phase": "prepare"}},
}
"""

DELEGATE = """
from typing import Annotated, Optional
from pydantic import Field
import server_impl

STAGING = None

def register(mcp, get_handler):
    global STAGING
    STAGING = mcp
    core = mcp.core_handler("wf_remove_change")

    @mcp.tool()
    def fork_echo(text: Annotated[str, Field(description="Text to echo.", min_length=2)], count: int = 3,
                  ratio: float = 1.0, tags: Optional[list[str]] = None, **kwargs):
        'Echo text back. Provide text; count repeats it.'
        bad = server_impl.ensure_no_extra_args("fork_echo", kwargs)
        if bad is not None:
            return bad
        if tags is not None:
            tags.append("seen")
        return {"status": "ok", "data": {"text": text, "count": count, "ratio_type": type(ratio).__name__,
                                         "tags": list(tags) if tags is not None else None}}

    @mcp.tool()
    def wf_remove_change(wave_id: str, change_id: str, mode: str = "dry_run", **kwargs):
        result = core(wave_id=wave_id, change_id=change_id, mode=mode, **kwargs)
        return {**result, "delegated": True}
"""

# Wave 1zimf (1zimn): a module that uses only the public helpers.
PUBLIC = """
import server_impl

def register(mcp, get_handler):
    @mcp.tool()
    def acme_public(text: str = "", **kwargs):
        bad = server_impl.ensure_no_extra_args("acme_public", kwargs)
        if bad is not None:
            return bad
        if text == "fail":
            return server_impl.make_response(
                "error", {"text": text},
                diagnostics=[server_impl.make_diagnostic(
                    "acme_failed", "asked to fail", recovery_tools=["acme_public"],
                    recovery_usage="acme_public(text='x')")],
                next_tools=["acme_public"], usage="acme_public(text='x')")
        return server_impl.make_response("ok", {"echo": text})

    # Wave 200ey (change 200ew): the published member-doc reader.
    @mcp.tool()
    def acme_member(name: str = "", **kwargs):
        bad = server_impl.ensure_no_extra_args("acme_member", kwargs)
        if bad is not None:
            return bad
        if not server_impl.is_change_id(name):
            return server_impl.make_response("ok", {"change_id": False})
        root = get_handler().root
        folder = root / "docs" / "plans"
        try:
            data = server_impl.read_member_doc_bytes(folder, folder / (name + ".md"), root=root)
        except server_impl.MemberDocRefused as exc:
            return server_impl.make_response("ok", {"change_id": True, "refused": exc.strerror})
        return server_impl.make_response("ok", {"change_id": True, "bytes": len(data)})
"""

PUBLIC_DECL = """
EXTENSION_MODULES = ("acme_public_tools",)
EXTENSION_TOOL_PREFIXES = ("acme_",)
EXTENSION_TOOL_TIERS = {"acme_public": "read", "acme_member": "read"}
"""

# Wave 1zimf (1zimo): a declared lifecycle tool, an undeclared write tool, a
# credited creation tool and an uncredited one. HOOK lets the driver observe
# the lock from inside the handler.
LIFE = """
import server_impl

HOOK = None

def register(mcp, get_handler):
    @mcp.tool()
    def acme_record(note: str = "", **kwargs):
        bad = server_impl.ensure_no_extra_args("acme_record", kwargs)
        if bad is not None:
            return bad
        seen = HOOK(get_handler().root) if HOOK is not None else None
        return server_impl.make_response("ok", {"note": note, "seen": seen})

    @mcp.tool()
    def acme_free(**kwargs):
        bad = server_impl.ensure_no_extra_args("acme_free", kwargs)
        if bad is not None:
            return bad
        return server_impl.make_response("ok", {"free": True})

    @mcp.tool()
    def acme_make(written: list[str], status: str = "ok", **kwargs):
        bad = server_impl.ensure_no_extra_args("acme_make", kwargs)
        if bad is not None:
            return bad
        return server_impl.make_response(status, {"written": written})

    @mcp.tool()
    def acme_make_free(written: list[str], **kwargs):
        bad = server_impl.ensure_no_extra_args("acme_make_free", kwargs)
        if bad is not None:
            return bad
        return server_impl.make_response("ok", {"written": written})
"""

LIFE_DECL = """
EXTENSION_MODULES = ("acme_life",)
EXTENSION_TOOL_PREFIXES = ("acme_",)
EXTENSION_TOOL_TIERS = {"acme_record": "write", "acme_free": "write", "acme_make": "write", "acme_make_free": "write"}
EXTENSION_LIFECYCLE_TOOLS = ("acme_record",)
EXTENSION_ARTIFACT_PATH_FIELDS = {"acme_make": "written", "acme_record": "note"}
EXTENSION_TOOL_ALIASES = {"acme_record_alias": "acme_record", "acme_record_mapped": "acme_record"}
EXTENSION_TOOL_PARAMETERS = {"acme_record_mapped": {"rename": {"text": "note"}}}
"""

# Wave 1zls8 (1zltx): declared helper modules and an extension module that
# uses only the public helper contract. The helper's register must never run.
HELPER = """
VERSION = "h1"
REGISTER_CALLS = []

def describe():
    return VERSION

def register(mcp, get_handler):
    REGISTER_CALLS.append(1)

    @mcp.tool()
    def acme_helper_leak(**kwargs):
        return {"status": "ok"}
"""

HELPER_EXTRA = """
EXTRA = True
"""

CONTRACT = """
import server_impl
import acme_shared

def register(mcp, get_handler):
    @mcp.tool()
    def acme_touch(wave_id: str, mode: str = "dry_run", **kwargs):
        bad = server_impl.ensure_no_extra_args("acme_touch", kwargs)
        if bad is not None:
            return bad
        return touch(get_handler().root, wave_id, mode)

@server_impl.fail_closed_on_record_layout("acme_touch")
def touch(root, wave_id, mode):
    wave_md, _read_error, _unreadable = server_impl.find_wave_record(root, wave_id)
    if wave_md is None:
        archived = server_impl.refuse_if_archived(root, wave_id, "wave")
        if archived is not None:
            return server_impl.make_response("error", {"wave_id": wave_id}, diagnostics=[archived])
        return server_impl.make_response("error", {"wave_id": wave_id}, diagnostics=[
            server_impl.make_diagnostic("wave_not_found", "no such wave")])
    refreshed = server_impl.refresh_index_for_paths(root, [wave_md]) if mode == "create" else None
    envelope = server_impl.make_response("ok", {"wave_id": wave_id, "helper": acme_shared.describe(),
                                                "refreshed": refreshed, "mode": mode})
    return server_impl.attach_lint(envelope, root, mode)
"""

HELPER_DECL = """
EXTENSION_HELPER_MODULES = ("acme_shared", "acme_extra")
EXTENSION_MODULES = ("acme_contract",)
EXTENSION_TOOL_PREFIXES = ("acme_",)
EXTENSION_TOOL_TIERS = {"acme_touch": "write"}
"""

# Wave 1zls8 (1zlty): declared response-key renames on mapped aliases.
KEYS_DECL = """
EXTENSION_TOOL_PREFIXES = ("fork_",)
EXTENSION_TOOL_ALIASES = {
    "fork_get_items": "wf_get_change",
    "fork_get_plain": "wf_get_change",
    "fork_add_item": "wf_add_change",
}
EXTENSION_TOOL_PARAMETERS = {
    "fork_get_items": {"response_keys": {"changes": "items", "changes[].id": "item_id"},
                       "description": "Get one item, or every item of a set."},
    "fork_add_item": {"rename": {"set_id": "wave_id", "item_id": "change_id"},
                      "response_keys": {"changes": "items", "changes[].change_id": "item_id", "meta.count": "total",
                                        "meta.list[].key": "item_key", "absent.deep": "never", "scalar.inner": "never"}},
}
"""

NESTED_RESULT = {
    "status": "ok",
    "data": {
        "wave_id": "1abcd", "change_id": "1abce-enh x", "mode": "dry_run",
        "changes": [
            {"change_id": "a", "item_id": "already"},
            {"change_id": "b", "note": "renamed"},
            {"change_id": "c", "item_id": "also there"},
            "not a dict",
        ],
        "meta": {"count": 2, "list": [{"key": 1}, 7, {"other": 2}]},
        "scalar": 5,
    },
    "diagnostics": [{"code": "existing", "message": "kept"}],
    "next_tools": ["probe_next"],
    "usage": "probe_next(item='a')",
}

# Wave 1zls8 (1zltz): overrides of a self-recording lifecycle tool and a
# self-recording retrieval tool, plus a non-exempt override, each delegating
# through core_handler as BEHAVIOUR says. HOOK observes the lock after the
# core call returns; LAST holds the core and final results of the last call.
MEASURED = """
import server_impl

BEHAVIOUR = {"wf_close_wave": "add", "code_outline": "add"}
EVENTS = []
LAST = {}
CORES = {}
HOOK = None

def _finish(name, how, result, get_handler):
    LAST[name] = {"core": result}
    seen = HOOK(get_handler().root) if HOOK is not None else None
    if how == "same":
        final = result
    else:
        final = {**result, "fork_added": "x" * 400, **({"seen": seen} if seen is not None else {})}
    LAST[name]["final"] = final
    return final

def register(mcp, get_handler):
    CORES["wf_close_wave"] = mcp.core_handler("wf_close_wave")
    CORES["code_outline"] = mcp.core_handler("code_outline")
    CORES["wf_current_wave"] = mcp.core_handler("wf_current_wave")

    @mcp.tool()
    def wf_close_wave(wave_id: str, mode: str = "dry_run", **kwargs):
        EVENTS.append("close_body")
        bad = server_impl.ensure_no_extra_args("wf_close_wave", kwargs)
        if bad is not None:
            return bad
        how = BEHAVIOUR["wf_close_wave"]
        if how == "self":
            return {"status": "ok", "data": {"answered": wave_id}}
        if how == "non_exempt_core":
            return {**CORES["wf_current_wave"](), "fork_added": "y"}
        return _finish("wf_close_wave", how, CORES["wf_close_wave"](wave_id=wave_id, mode=mode), get_handler)

    @mcp.tool()
    def code_outline(path: str, **kwargs):
        bad = server_impl.ensure_no_extra_args("code_outline", kwargs)
        if bad is not None:
            return bad
        how = BEHAVIOUR["code_outline"]
        if how == "self":
            return {"status": "ok", "data": {"path": path, "symbols": []}}
        return _finish("code_outline", how, CORES["code_outline"](path=path), get_handler)

    @mcp.tool()
    def wf_current_wave(**kwargs):
        bad = server_impl.ensure_no_extra_args("wf_current_wave", kwargs)
        if bad is not None:
            return bad
        return {**CORES["wf_current_wave"](), "fork_current": True}
"""

MEASURED_DECL = """
EXTENSION_MODULES = ("fork_measured",)
EXTENSION_OVERRIDES = {"fork_measured": ("wf_close_wave", "code_outline", "wf_current_wave")}
"""

_LOCK_CHILD_TRY = (
    "import sys\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from pathlib import Path\n"
    "import lifecycle_lock\n"
    "try:\n"
    "    with lifecycle_lock.lifecycle_mutation_lock(Path(sys.argv[2])):\n"
    "        print('acquired', flush=True)\n"
    "except lifecycle_lock.LifecycleLockBusy:\n"
    "    print('busy', flush=True)\n"
)

_LOCK_CHILD_HOLD = (
    "import sys\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from pathlib import Path\n"
    "import lifecycle_lock\n"
    "with lifecycle_lock.lifecycle_mutation_lock(Path(sys.argv[2])):\n"
    "    print('held', flush=True)\n"
    "    sys.stdin.readline()\n"
    "print('released', flush=True)\n"
)

def other_process_lifecycle(lock_root):
    """One acquire attempt from a fresh interpreter (never a fork)."""
    import subprocess
    done = subprocess.run([sys.executable, "-B", "-c", _LOCK_CHILD_TRY, str(SCRATCH), str(lock_root)],
                          capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
    return done.stdout.strip() or f"<rc={done.returncode} {done.stderr[-1000:]}>"

@contextlib.contextmanager
def lifecycle_held_elsewhere(lock_root):
    """Another process holds the lifecycle lock for the block."""
    import subprocess
    child = subprocess.Popen([sys.executable, "-B", "-c", _LOCK_CHILD_HOLD, str(SCRATCH), str(lock_root)],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        line = child.stdout.readline().strip()
        if line != "held":
            raise RuntimeError(f"lock holder did not start: {line!r} {child.stderr.read()[-1000:]}")
        yield
    finally:
        try:
            child.stdin.write("go\n")
            child.stdin.flush()
        except OSError:
            pass
        child.wait(timeout=60)
        for stream in (child.stdin, child.stdout, child.stderr):
            stream.close()

def spy_response(impl, name, calls, echo=False):
    """Replace a core response function; record its arguments and the lock state.

    With ``echo`` the spy's ``data`` echoes its arguments at top level, by the
    real function's parameter names and defaults, as the lifecycle handlers do
    (wave 1zime, 1zimm).
    """
    signature = inspect.signature(getattr(impl, name))
    def spy(root, *args, **kwargs):
        probe = getattr(impl, "_WF_LOCK_PROBE", None) or {}
        calls.append({"args": list(args), "kwargs": {k: v for k, v in kwargs.items() if k != "cache"},
                      "lock_held": probe.get("held"), "acquired": probe.get("acquired")})
        if echo:
            bound = signature.bind(root, *args, **kwargs)
            bound.apply_defaults()
            return {"status": "ok", "data": {k: v for k, v in bound.arguments.items() if k not in ("root", "cache")}}
        return {"status": "ok", "data": {"spied": name}}
    setattr(impl, name, spy)

def install_counting_lock_probe(impl):
    install_lock_probe(impl)
    state = impl._WF_LOCK_PROBE
    state["acquired"] = 0
    probe = impl._lifecycle_mutation_lock

    @contextlib.contextmanager
    def counting(root):
        state["acquired"] += 1
        with probe(root):
            yield

    impl._lifecycle_mutation_lock = counting

def normalized(schema):
    if isinstance(schema, dict):
        return {k: normalized(v) for k, v in schema.items() if k != "title"}
    if isinstance(schema, list):
        return [normalized(v) for v in schema]
    return schema

MEMORY_VALIDATE_ARGS = {
    "memory_id": "mem-x", "verdict": "promote", "action_delta": "a", "rationale": "r",
    "evidence_verified": True, "current_target_verified": True, "canonical_overlap": "none",
}

@contextlib.contextmanager
def busy_lock(impl):
    """Make every lifecycle-lock acquisition report another holder."""
    original = impl._lifecycle_mutation_lock

    @contextlib.contextmanager
    def held(root):
        raise impl.LifecycleMutationBusy("fixture holds the lifecycle lock")
        yield

    impl._lifecycle_mutation_lock = held
    try:
        yield
    finally:
        impl._lifecycle_mutation_lock = original

def codes(result):
    return [result["status"]] + [d["code"] for d in result.get("diagnostics", [])]

def hints(result):
    diagnostics = result.get("diagnostics", [])
    return {
        "codes": codes(result),
        "busy": (result.get("data") or {}).get("busy"),
        "next_tools": result.get("next_tools"),
        "usage": result.get("usage"),
        "recovery_tools": [d.get("recovery_tools") for d in diagnostics],
        "recovery_usage": [d.get("recovery_usage") for d in diagnostics],
    }

# Wave 1zim3 repair: hint calls whose argument values are tool names.
VALUE_HINT_USAGE = "wf_add_change(wave_id='wf_add_change', change_id='fork_add_wave') then wf_review_wave(wave_id='wf_add_change')"
VALUE_HINT_RECOVERY = "dict(x='wf_add_change') or wf_add_change(wave_id=f(wf_add_change)); retry wf_add_change"

def value_hints(impl, mcp):
    """Recovery hints from the canonical body, read back through the served alias."""
    impl.wf_add_change_response = lambda root, *a, **k: {
        "status": "error", "data": {}, "usage": VALUE_HINT_USAGE,
        "diagnostics": [{"code": "probe", "message": "probe", "recovery_tools": [], "recovery_usage": VALUE_HINT_RECOVERY}],
    }
    return hints(ccall(mcp, "fork_add_wave", {"set_id": "1abcd", "wave_id": "1abce-feat x"}))

def observe_surface(impl, mcp, roster):
    reg = impl._TOOL_REGISTRY
    tiers = roster.all_tool_tiers()
    runner_tools = set(roster.RUNNER_TOOLS)
    rule_names = lambda write: sorted(r.rsplit("__", 1)[-1] for r in roster.allow_rules(write))
    watched = ("wf_help", "wf_current_wave", "wf_close_wave", "wf_add_change", "memory_validate")
    return {
        "parity_defects": [d.name for d in reg.parity_defects],
        "registry_vs_tiers": sorted({s.name for s in reg.tools()} ^ (set(tiers) - runner_tools)),
        "tier_mismatches": sorted(s.name for s in reg.tools() if s.tier != tiers.get(s.name)),
        "served_vs_tiers": sorted(set(table(mcp)) ^ set(tiers)),
        "tiers": {n: tiers.get(n) for n in sorted(set(tiers) | set(watched)) if n.startswith("fork_") or n in watched},
        "read_rules": [n for n in rule_names(False) if n.startswith("fork_") or n in watched],
        "write_rules": [n for n in rule_names(True) if n.startswith("fork_") or n in watched],
    }

out = {}
with tempfile.TemporaryDirectory() as tmp:
    root = _make_repo(Path(tmp))
    if MODE == "stock":
        load_server(); runner = load_thin_runner()
        mcp = runner.build_server(root)
        impl = runner.server_impl
        out["markers"] = {n: markers(mcp, n) for n in (
            "wf_current_wave", "wf_create_wave", "wf_close_wave", "wf_review_event", "wf_help", "memory_validate")}
        out["extensions"] = impl.wf_server_info_response(root)["data"]["extensions"]
        out["tool_count"] = len(table(mcp))
        # Wave 1zime (1zimm AC-2): the stock data the mapped server must match.
        spy_response(impl, "wf_add_change_response", [], echo=True)
        out["add_call"] = ccall(mcp, "wf_add_change", {"wave_id": "1abcd", "change_id": "1abce-feat x"})["data"]
        out["get_call"] = ccall(mcp, "wf_get_change", {"change_id": "1abce-feat x"})["data"]
        # Wave 1zls8 (1zltz AC-4): the stock declaration adds no cost keyword.
        out["cost_pass_kwargs"] = sorted(impl._cost_pass_kwargs())
        out["deltas_installed"] = sorted(impl._EXTENSION_OVERRIDE_DELTAS)
        runner._get_handler().close()

    elif MODE == "alias":
        # Wave 1z8oz: an aliases-only declaration (no module) with a hidden name.
        DECL.write_text(DECL_ORIG + ALIAS_DECL)
        load_server(); runner = load_thin_runner()
        mcp = runner.build_server(root)
        impl = runner.server_impl
        import mcp_tool_roster
        from unittest import mock
        out.update(observe_surface(impl, mcp, mcp_tool_roster))
        out["alias_shares_fn"] = table(mcp)["fork_close_container"].fn is table(mcp)["wf_close_wave"].fn
        out["markers"] = {n: markers(mcp, n) for n in ("fork_close_container", "wf_close_wave", "fork_add_change", "fork_current")}
        listed = [t.name for t in asyncio.run(mcp.list_tools())]
        out["listed_hidden"] = "wf_current_wave" in listed
        out["listed_alias"] = "fork_current" in listed
        try:
            ccall(mcp, "wf_current_wave")
            out["hidden_call"] = "served"
        except Exception as exc:
            out["hidden_call"] = type(exc).__name__ + ": " + str(exc)
        out["alias_call"] = ccall(mcp, "fork_current")["status"]
        handler = runner._get_handler()
        costs = []
        with mock.patch.object(handler.telemetry, "record_tool_cost", lambda name, **kw: costs.append(name)):
            ccall(mcp, "fork_current")
            out["cost_after_costed_alias"] = list(costs)
            out["exempt_alias_call"] = codes(ccall(mcp, "fork_close_container", {"wave_id": "1abcd", "mode": "dry_run"}))
            out["cost_after_exempt_alias"] = list(costs)
        with busy_lock(impl):
            busy = ccall(mcp, "fork_close_container", {"wave_id": "1abcd", "mode": "dry_run"})
        out["busy"] = hints(busy)
        checkpoint = root / ".wavefoundry" / "upgrade-in-progress.json"
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text(json.dumps({"current_phase": "extracting"}))
        guarded = ccall(mcp, "fork_add_change", {"wave_id": "1abcd", "change_id": "1abce-feat x"})
        checkpoint.unlink()
        out["guarded"] = [guarded["status"]] + [d["code"] for d in guarded.get("diagnostics", [])]
        out["extensions"] = impl.wf_server_info_response(root)["data"]["extensions"]
        # Reload rebuilds the served names, then fails closed on a bad declaration.
        result = runner.perform_mcp_reload()
        out["reload_status"] = result["status"]
        out["reload_names"] = sorted(n for n in table(mcp) if n.startswith("fork_"))
        out["reload_hidden"] = "wf_current_wave" in table(mcp)
        out["reload_shares_fn"] = table(mcp)["fork_close_container"].fn is table(mcp)["wf_close_wave"].fn
        DECL.write_text(DECL_ORIG + ALIAS_DECL + '\nEXTENSION_TOOL_ALIASES = {"fork_ghost": "wf_not_a_tool"}\n')
        failed = runner.perform_mcp_reload()
        out["failed_reload_text"] = json.dumps(failed)[:4000]
        out["served_after_failure"] = sorted(table(mcp))
        handler.close()

    elif MODE == "replace":
        DECL.write_text(DECL_ORIG + REPLACE_DECL)
        write_module("fork_tools", FORK)
        load_server(); runner = load_thin_runner()
        mcp = runner.build_server(root)
        impl = runner.server_impl
        import mcp_tool_roster
        from unittest import mock
        out.update(observe_surface(impl, mcp, mcp_tool_roster))
        out["markers"] = {n: markers(mcp, n) for n in (
            "wf_close_wave", "fork_close_container", "wf_review_event", "fork_review_event_core",
            "wf_help", "fork_help_core", "memory_validate", "fork_memory_validate_core",
            "wf_current_wave", "fork_current_core")}
        out["replaced_call"] = ccall(mcp, "wf_close_wave", {"item": "task-7"})
        with busy_lock(impl):
            out["replaced_busy"] = hints(ccall(mcp, "wf_close_wave", {"item": "task-7"}))
            out["core_busy"] = hints(ccall(mcp, "fork_close_container", {"wave_id": "1abcd", "mode": "dry_run"}))
            # A core tool that is not replaced names a replaced core name in its hints.
            out["other_core_busy"] = hints(ccall(mcp, "wf_add_change", {"wave_id": "1abcd", "change_id": "1abce-feat x"}))
        handler = runner._get_handler()
        exempt_costs = []
        with mock.patch.object(handler.telemetry, "record_tool_cost", lambda name, **kw: exempt_costs.append(name)):
            ccall(mcp, "wf_close_wave", {"item": "task-8"})
        out["cost_after_exempt_replacement"] = exempt_costs
        extractor_calls, costs = [], []
        spy = lambda root_, result: (extractor_calls.append(1), ([], None))[1]
        with mock.patch.dict(impl._ARTIFACT_EXTRACTORS, {"wf_review_event": spy}), \
                mock.patch.object(handler.telemetry, "record_tool_cost", lambda name, **kw: costs.append([name, kw.get("derived_artifact_tokens")])):
            out["replaced_review"] = ccall(mcp, "wf_review_event", {"note": "n"})["data"]
            out["extractor_after_replaced"] = len(extractor_calls)
            out["cost_after_replaced"] = list(costs)
            ccall(mcp, "fork_review_event_core", {"wave_id": "1abcd", "event": "run", "actor": "qa-reviewer", "context_id": "c1", "mode": "dry_run"})
            out["extractor_after_core"] = len(extractor_calls)
        checkpoint = root / ".wavefoundry" / "upgrade-in-progress.json"
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text(json.dumps({"current_phase": "extracting"}))
        out["core_close_guarded"] = codes(ccall(mcp, "fork_close_container", {"wave_id": "1abcd", "mode": "dry_run"}))
        out["write_replacement_guarded"] = codes(ccall(mcp, "wf_help", {"topic": "x"}))
        out["read_core_unguarded"] = codes(ccall(mcp, "fork_help_core"))
        out["memory_core_extracting"] = codes(ccall(mcp, "fork_memory_validate_core", MEMORY_VALIDATE_ARGS))
        out["memory_replacing_extracting"] = codes(ccall(mcp, "memory_validate", {"record": "r"}))
        checkpoint.write_text(json.dumps({"current_phase": "awaiting_memory_validation"}))
        out["memory_core_recovery"] = codes(ccall(mcp, "fork_memory_validate_core", MEMORY_VALIDATE_ARGS))
        out["memory_replacing_recovery"] = codes(ccall(mcp, "memory_validate", {"record": "r"}))
        checkpoint.unlink()
        out["extensions"] = impl.wf_server_info_response(root)["data"]["extensions"]
        # Reload with replacements rebuilds them.
        result = runner.perform_mcp_reload()
        out["reload_status"] = result["status"]
        out["reload_replaced_call"] = ccall(mcp, "wf_close_wave", {"item": "task-9"})["data"]
        out["reload_core_markers"] = markers(mcp, "fork_close_container")
        handler.close()

    elif MODE == "params":
        DECL.write_text(DECL_ORIG + PARAM_DECL)
        write_module("fork_delegate", DELEGATE)
        load_server(); runner = load_thin_runner()
        mcp = runner.build_server(root)
        impl = runner.server_impl
        import mcp_tool_roster
        from unittest import mock
        out.update(observe_surface(impl, mcp, mcp_tool_roster))
        tools = table(mcp)
        out["schemas"] = {n: normalized(tools[n].parameters) for n in (
            "wf_add_change", "fork_add_wave", "fork_add_wave_now", "wf_review_wave", "fork_review_prepare",
            "fork_echo", "fork_say")}
        out["say_call"] = ccall(mcp, "fork_say", {"words": "hello"})["data"]
        # A pin reaches the body as the strictly validated value, copied per call.
        out["whole_calls"] = [ccall(mcp, "fork_say_whole", {"text": "hey"})["data"] for _ in range(2)]
        (root / "notes.txt").write_text("alpha\nbeta\n")
        out["read_raw"] = ccall(mcp, "fork_read_raw", {"path": "notes.txt"})["data"].get("content")
        out["read_canonical"] = ccall(mcp, "code_read", {"path": "notes.txt", "with_line_numbers": False})["data"].get("content")
        try:
            sys.modules["fork_delegate"].STAGING.core_handler("wf_remove_change")
            out["late_core_handler"] = "returned"
        except Exception as exc:
            out["late_core_handler"] = type(exc).__name__ + ": " + str(exc)
        try:
            ccall(mcp, "fork_say", {"words": "h"})
            out["say_short"] = "accepted"
        except Exception as exc:
            out["say_short"] = type(exc).__name__ + ": " + str(exc)
        out["descriptions_equal"] = {n: tools[n].description == tools[c].description for n, c in (
            ("fork_add_wave", "wf_add_change"), ("fork_review_prepare", "wf_review_wave"))}
        out["annotations_equal"] = {n: tools[n].annotations == tools[c].annotations for n, c in (
            ("fork_add_wave", "wf_add_change"), ("fork_review_prepare", "wf_review_wave"))}
        out["markers"] = {n: markers(mcp, n) for n in (
            "wf_add_change", "fork_add_wave", "fork_add_wave_now", "wf_review_wave", "fork_review_prepare", "wf_remove_change")}
        # Wave 1zoju (1zodw): both entries end in their own render wrapper; the
        # translator wraps the canonical callable that render wraps.
        out["wraps_canonical"] = tools["fork_add_wave"].fn.__wrapped__.__wrapped__ is tools["wf_add_change"].fn.__wrapped__
        install_counting_lock_probe(impl)
        add_calls, review_calls, remove_calls = [], [], []
        spy_response(impl, "wf_add_change_response", add_calls, echo=True)
        spy_response(impl, "wf_review_wave_response", review_calls)
        spy_response(impl, "wf_remove_change_response", remove_calls)
        handler = runner._get_handler()
        costs = []
        with mock.patch.object(handler.telemetry, "record_tool_cost", lambda name, **kw: costs.append(name)):
            out["swap_call"] = ccall(mcp, "fork_add_wave", {"set_id": "1abcd", "wave_id": "1abce-feat x"})["data"]
            out["swap_cost"] = list(costs)
            out["swap_lock_acquired"] = impl._WF_LOCK_PROBE["acquired"]
            out["pinned_add_call"] = ccall(mcp, "fork_add_wave_now", {"set_id": "1abcd", "wave_id": "1abce-feat x"})["data"]
            out["review_call"] = ccall(mcp, "fork_review_prepare", {"wave_id": "1abcd"})
            del costs[:]
            impl._WF_LOCK_PROBE["acquired"] = 0
            out["delegate_call"] = ccall(mcp, "wf_remove_change", {"wave_id": "1abcd", "change_id": "1abce-feat x"})
            out["delegate_cost"] = list(costs)
            out["delegate_lock_acquired"] = impl._WF_LOCK_PROBE["acquired"]
        out["add_calls"] = list(add_calls)
        out["review_calls"] = list(review_calls)
        out["remove_calls"] = list(remove_calls)
        before = (len(add_calls), len(review_calls))
        extras = {}
        for label, name, args in (
            ("renamed_away", "fork_add_wave", {"set_id": "1abcd", "wave_id": "1abce-feat x", "change_id": "other"}),
            ("pinned_override", "fork_add_wave_now", {"set_id": "1abcd", "wave_id": "1abce-feat x", "mode": "dry_run"}),
            ("pinned_phase", "fork_review_prepare", {"wave_id": "1abcd", "phase": "implementation"}),
            ("nested_kwargs", "fork_add_wave", {"set_id": "1abcd", "wave_id": "1abce-feat x", "kwargs": {"mode": "create"}}),
            ("stranger", "fork_review_prepare", {"wave_id": "1abcd", "bogus": 1}),
        ):
            result = ccall(mcp, name, args)
            extras[label] = {"codes": codes(result), "data": result.get("data"),
                             "message": [d.get("message") for d in result.get("diagnostics", [])]}
        out["extras"] = extras
        out["extras_reached_canonical"] = [len(add_calls), len(review_calls)] != list(before)
        out["empty_kwargs_call"] = codes(ccall(mcp, "fork_add_wave", {"set_id": "1abcd", "wave_id": "1abce-feat x", "kwargs": {}}))
        checkpoint = root / ".wavefoundry" / "upgrade-in-progress.json"
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text(json.dumps({"current_phase": "extracting"}))
        calls_before = len(add_calls)
        out["guarded"] = codes(ccall(mcp, "fork_add_wave", {"set_id": "1abcd", "wave_id": "1abce-feat x"}))
        out["guarded_reached_canonical"] = len(add_calls) != calls_before
        checkpoint.unlink()
        # Wave 1zime (1zimm): response data under the canonical name and a plain alias.
        out["canonical_add_call"] = ccall(mcp, "wf_add_change", {"wave_id": "1abcd", "change_id": "1abce-feat x"})["data"]
        out["plain_get_call"] = ccall(mcp, "fork_get_change", {"change_id": "1abce-feat x"})["data"]
        out["canonical_get_call"] = ccall(mcp, "wf_get_change", {"change_id": "1abce-feat x"})["data"]
        listed = {t.name: t.description for t in asyncio.run(mcp.list_tools())}
        out["listed_descriptions"] = {n: listed.get(n) for n in ("fork_echo", "fork_say", "fork_say_whole", "fork_say_plain")}
        ext_now = sys.modules["mcp_tool_extensions"]
        out["mapped_targets_coroutine"] = {
            alias: [inspect.iscoroutinefunction(tools[canonical].fn),
                    inspect.iscoroutinefunction(inspect.unwrap(tools[canonical].fn)),
                    inspect.iscoroutinefunction(tools[alias].fn)]
            for alias, canonical in ext_now.EXTENSION_TOOL_ALIASES.items() if alias in ext_now.EXTENSION_TOOL_PARAMETERS
        }
        with busy_lock(impl):
            out["busy"] = hints(ccall(mcp, "fork_add_wave", {"set_id": "1abcd", "wave_id": "1abce-feat x"}))
        out["value_hints"] = value_hints(impl, mcp)
        ext = sys.modules["mcp_tool_extensions"]
        specs = impl._alias_call_specs(tools)
        out["call_specs"] = {k: {"aliases": [list(a) for a in v["aliases"]], "defaults": v["defaults"]} for k, v in specs.items()}
        served = ext.served_name_map()
        prepare_only = {"wf_review_wave": specs["wf_review_wave"]}
        delivery = {"wf_review_wave": {"aliases": specs["wf_review_wave"]["aliases"] + [("fork_review_delivery", {}, {"phase": "implementation"})],
                                       "defaults": specs["wf_review_wave"]["defaults"]}}
        rewrite = lambda usage, calls=specs: impl._rewrite_served_names({"usage": usage}, served, calls)["usage"]
        out["hint_lists"] = impl._rewrite_served_names({"next_tools": ["wf_review_wave", "wf_add_change"],
                                                         "diagnostics": [{"recovery_tools": ["wf_review_wave"]}]}, served, specs)
        out["hint_usage"] = {
            "pin_present_equal": rewrite("wf_review_wave(wave_id='1abcd', phase='prepare')"),
            "pin_present_differs": rewrite("wf_review_wave(wave_id='1abcd', phase='implementation')"),
            "pin_absent_default_differs": rewrite("wf_review_wave(wave_id='1abcd')", prepare_only),
            "pin_absent_default_equal": rewrite("wf_review_wave(wave_id='1abcd')", delivery),
            "swap": rewrite("then wf_add_change(wave_id='1abcd', change_id='1abce-feat x', mode='create') now"),
            "unparseable": rewrite("wf_add_change(wave_id='1abcd', change_id="),
            "non_literal": rewrite("wf_add_change(wave_id=wave, change_id=change)"),
            "duplicate": rewrite("wf_add_change(wave_id='a', wave_id='b')"),
            "star_star": rewrite("wf_add_change(**opts)"),
            "pinned_non_literal_value": rewrite("wf_review_wave(wave_id=w, phase='prepare')"),
            "pinned_non_literal_pin": rewrite("wf_review_wave(wave_id='w', phase=p)"),
            "prose": rewrite("retry wf_add_change after the lock clears"),
            "placeholder": rewrite("wf_add_change(...) once free"),
            "pinned_placeholder": rewrite("wf_review_wave(...)"),
        }
        out["extensions"] = impl.wf_server_info_response(root)["data"]["extensions"]
        result = runner.perform_mcp_reload()
        out["reload_status"] = result["status"]
        out["reload_schema"] = normalized(table(mcp)["fork_add_wave"].parameters)
        out["reload_wraps_canonical"] = table(mcp)["fork_add_wave"].fn.__wrapped__.__wrapped__ is table(mcp)["wf_add_change"].fn.__wrapped__
        reloaded = {t.name: t.description for t in asyncio.run(mcp.list_tools())}
        out["reload_descriptions"] = {n: reloaded.get(n) for n in ("fork_echo", "fork_say")}
        handler.close()

    elif MODE == "params_hidden":
        # Wave 1zim3 repair: a hidden canonical name whose only unpinned alias is a rename.
        DECL.write_text(DECL_ORIG + PARAM_DECL + '\nEXTENSION_HIDDEN_TOOLS = ("wf_add_change",)\n')
        write_module("fork_delegate", DELEGATE)
        load_server(); runner = load_thin_runner()
        mcp = runner.build_server(root)
        impl = runner.server_impl
        out["hidden_served"] = "wf_add_change" in table(mcp)
        with busy_lock(impl):
            out["busy"] = hints(ccall(mcp, "fork_add_wave", {"set_id": "1abcd", "wave_id": "1abce-feat x"}))
        out["value_hints"] = value_hints(impl, mcp)
        ext = sys.modules["mcp_tool_extensions"]
        specs = impl._alias_call_specs(table(mcp))
        served = ext.served_name_map()
        rewritten = impl._rewrite_served_names({
            "next_tools": ["wf_add_change"],
            "usage": "wf_add_change is hidden; call wf_add_change(wave_id=w, change_id=c) or wf_add_change (wave_id='a')",
            "diagnostics": [{"recovery_tools": ["wf_add_change"], "recovery_usage": "retry wf_add_change later"}],
        }, served, specs)
        out["rewritten"] = rewritten
        runner._get_handler().close()

    elif MODE == "ext":
        DECL.write_text(DECL_ORIG + GOOD_DECL)
        write_module("acme_tools", ACME)
        write_module("stray_tools", STRAY)
        root = _make_repo(SCRATCH.parent)  # scripts under the root: relative provenance
        load_server(); runner = load_thin_runner()
        mcp = runner.build_server(root)
        impl = runner.server_impl
        import mcp_tool_roster
        names = set(table(mcp))
        out["names"] = sorted(n for n in names if n.startswith("acme_"))
        out["override_read"] = call(mcp, "wf_current_wave")["data"]
        out["override_lifecycle"] = call(mcp, "wf_create_wave", slug="probe")["data"]
        bad = call(mcp, "wf_current_wave", bogus=1)
        out["override_unknown_arg"] = [d["code"] for d in bad.get("diagnostics", [])]
        out["markers"] = {n: markers(mcp, n) for n in ("wf_current_wave", "wf_create_wave", "acme_echo", "acme_write")}
        out["cost_wrapped"] = bool(getattr(table(mcp)["acme_echo"].fn, "_wf_cost_wrapped", False))
        install_lock_probe(impl)
        via = ccall(mcp, "wf_create_wave", {"slug": "probe"})
        out["call_tool_lifecycle"] = via["data"]
        out["call_tool_lock_released"] = impl._WF_LOCK_PROBE["held"] is False
        bad_via = ccall(mcp, "wf_current_wave", {"bogus": 1})
        out["call_tool_unknown_arg"] = [d["code"] for d in bad_via.get("diagnostics", [])]
        # Wave 1zlu1 (F3): this override omits the omittable core `parent`, so
        # a call passing it is refused by the override's strict schema.
        bad_parent = ccall(mcp, "wf_create_wave", {"slug": "probe", "parent": "q4"})
        out["call_tool_parent_refused"] = [bad_parent.get("status")] + [d["code"] for d in bad_parent.get("diagnostics", [])]
        out["call_tool_echo"] = ccall(mcp, "acme_echo", {"text": "hi"})["data"]["echo"]
        reg = impl._TOOL_REGISTRY
        out["parity_defects"] = [d.name for d in reg.parity_defects]
        out["tiers"] = {n: reg.get(n).tier for n in ("acme_echo", "acme_write", "wf_current_wave", "wf_create_wave")}
        out["core_tiers"] = {n: mcp_tool_roster.TOOL_TIERS[n] for n in ("wf_current_wave", "wf_create_wave")}
        out["read_rules"] = [r for r in mcp_tool_roster.allow_rules(False) if "acme_" in r or r.endswith("wf_current_wave")]
        out["write_rules"] = [r for r in mcp_tool_roster.allow_rules(True) if "acme_" in r]
        out["write_ok"] = call(mcp, "acme_write")["status"]
        checkpoint = root / ".wavefoundry" / "upgrade-in-progress.json"
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text(json.dumps({"current_phase": "extracting"}))
        blocked = call(mcp, "acme_write")
        out["write_blocked"] = [blocked["status"]] + [d["code"] for d in blocked.get("diagnostics", [])]
        blocked_via = ccall(mcp, "acme_write")
        out["call_tool_write_blocked"] = [blocked_via["status"]] + [d["code"] for d in blocked_via.get("diagnostics", [])]
        out["echo_during_upgrade"] = call(mcp, "acme_echo", text="x")["status"]
        checkpoint.unlink()
        out["extensions"] = impl.wf_server_info_response(root)["data"]["extensions"]
        out["acme_sha"] = hashlib.sha256((SCRATCH / "acme_tools.py").read_bytes()).hexdigest()
        runner._get_handler().close()

    elif MODE == "public":
        # Wave 1zimf (1zimn AC-2, AC-4): the public helpers end to end and after reload.
        DECL.write_text(DECL_ORIG + PUBLIC_DECL)
        write_module("acme_public_tools", PUBLIC)
        load_server(); runner = load_thin_runner()
        mcp = runner.build_server(root)
        out["names"] = sorted(n for n in table(mcp) if n.startswith("acme_"))
        out["ok_call"] = ccall(mcp, "acme_public", {"text": "hi"})
        out["fail_call"] = ccall(mcp, "acme_public", {"text": "fail"})
        out["unknown_call"] = ccall(mcp, "acme_public", {"text": "hi", "bogus": 1})
        out["empty_kwargs_call"] = ccall(mcp, "acme_public", {"text": "hi", "kwargs": {}})
        # Wave 200ey (change 200ew): a regular member doc reads, a linked one
        # is refused through the published refusal type, a non-id is not read.
        import os as _os
        plans = root / "docs" / "plans"
        plans.mkdir(parents=True, exist_ok=True)
        (plans / "1aaaa-enh member-probe.md").write_text("# Probe\n", encoding="utf-8")
        outside = Path(tempfile.mkdtemp()) / "outside.md"
        outside.write_text("# Outside\n", encoding="utf-8")
        try:
            _os.symlink(outside, plans / "1aaab-enh linked-probe.md")
            linked = True
        except (OSError, NotImplementedError):
            linked = False
        out["member_read"] = ccall(mcp, "acme_member", {"name": "1aaaa-enh member-probe"})
        out["member_linked"] = ccall(mcp, "acme_member", {"name": "1aaab-enh linked-probe"}) if linked else None
        out["member_not_id"] = ccall(mcp, "acme_member", {"name": "../escape"})
        before = runner.server_impl
        result = runner.perform_mcp_reload()
        out["reload_status"] = result["status"]
        impl = sys.modules["server_impl"]
        out["reload_same_module"] = impl is before
        out["reload_helpers"] = {n: callable(getattr(impl, n, None)) for n in impl.EXTENSION_PUBLIC_HELPERS}
        out["reload_equal"] = {
            "make_response": impl.make_response("ok", {"a": 1}) == impl._response("ok", {"a": 1}),
            "make_diagnostic": impl.make_diagnostic("c", "m", advisory=True) == impl._diagnostic("c", "m", advisory=True),
            "ensure_no_extra_args": impl.ensure_no_extra_args("t", {"x": 1}) == impl._ensure_no_extra_args("t", {"x": 1}),
        }
        from unittest import mock
        with mock.patch.object(impl, "_response", lambda *a, **k: {"patched": True}):
            out["reload_late_bound"] = impl.make_response("ok")
        out["reload_unknown_call"] = ccall(mcp, "acme_public", {"bogus": 1})
        out["reload_ok_call"] = ccall(mcp, "acme_public", {"text": "again"})
        out["reload_member_linked"] = ccall(mcp, "acme_member", {"name": "1aaab-enh linked-probe"}) if linked else None
        runner._get_handler().close()

    elif MODE == "lifecycle":
        # Wave 1zimf (1zimo): declared lifecycle tools and artifact path fields.
        DECL.write_text(DECL_ORIG + LIFE_DECL)
        write_module("acme_life", LIFE)
        load_server(); runner = load_thin_runner()
        mcp = runner.build_server(root)
        impl = runner.server_impl
        import lifecycle_lock, runtime_lock, os
        from unittest import mock
        life = sys.modules["acme_life"]
        handler = runner._get_handler()
        lock_path = root / lifecycle_lock.LIFECYCLE_MUTATION_LOCK_REL
        (root / ".wavefoundry").mkdir(parents=True, exist_ok=True)
        out["markers"] = {n: markers(mcp, n) for n in (
            "acme_record", "acme_free", "acme_make", "acme_make_free", "acme_record_alias", "acme_record_mapped")}
        out["locked"] = {n: bool(getattr(table(mcp)[n].fn, "_wf_mutation_locked", False)) or "lock" in markers(mcp, n)
                         for n in ("acme_record", "acme_free", "acme_make")}
        out["extensions"] = impl.wf_server_info_response(root)["data"]["extensions"]
        out["lock_tools"] = sorted(impl._LIFECYCLE_MUTATION_LOCK_TOOLS)
        out["artifact_extractors"] = sorted(impl._ARTIFACT_EXTRACTORS)
        out["core_behaviour_lock_tools"] = sorted(impl._LIFECYCLE_MUTATION_LOCK_TOOLS)
        # AC-3: another process holds the lifecycle lock.
        with lifecycle_held_elsewhere(root):
            held = ccall(mcp, "acme_record", {"note": "n"})
            out["held_record"] = {"codes": codes(held), "data": held.get("data")}
            out["held_alias"] = codes(ccall(mcp, "acme_record_alias", {"note": "n"}))
            out["held_mapped"] = codes(ccall(mcp, "acme_record_mapped", {"text": "n"}))
            out["held_free"] = codes(ccall(mcp, "acme_free"))
        out["free_record"] = ccall(mcp, "acme_record", {"note": "n"})["data"]
        out["free_mapped"] = ccall(mcp, "acme_record_mapped", {"text": "m"})["data"]
        # AC-4: the hold is registered; re-entry and a served locked tool are refused
        # without opening the lock file, and the hold survives both.
        def observe(hroot, reraise):
            seen = {}
            hold = runtime_lock.process_hold(lock_path)
            seen["hold_registered"] = hold is not None and hold.get("pid") == os.getpid()
            opened = []
            real = runtime_lock._open_lock_carrier

            def recorder(path, mode):
                opened.append(os.path.realpath(os.fspath(path)))
                return real(path, mode)

            with mock.patch.object(runtime_lock, "_open_lock_carrier", recorder):
                served = table(mcp)["wf_set_handoff"].fn(content="x")
                seen["served_codes"] = codes(served)
                try:
                    with lifecycle_lock.lifecycle_mutation_lock(hroot):
                        seen["reentry"] = "entered"
                except lifecycle_lock.LifecycleLockBusy as exc:
                    seen["reentry"] = "LifecycleLockBusy"
                    seen["lock_file_opened"] = os.path.realpath(lock_path) in opened
                    seen["other_process"] = other_process_lifecycle(hroot)
                    if reraise:
                        raise
            seen["lock_file_opened"] = os.path.realpath(lock_path) in opened
            seen["other_process"] = other_process_lifecycle(hroot)
            return seen
        record = {}
        life.HOOK = lambda hroot: observe(hroot, False)
        out["observed"] = ccall(mcp, "acme_record", {"note": "n"})["data"]["seen"]
        out["hold_after"] = runtime_lock.process_hold(lock_path)
        out["other_after"] = other_process_lifecycle(root)

        def reraise_hook(hroot):
            try:
                return observe(hroot, True)
            except lifecycle_lock.LifecycleLockBusy:
                record["raised"] = True
                record["other_process_while_raising"] = other_process_lifecycle(hroot)
                raise
        life.HOOK = reraise_hook
        raised = ccall(mcp, "acme_record", {"note": "n"})
        out["reraised"] = {"codes": codes(raised), "data": raised.get("data"), **record}
        out["hold_after_reraise"] = runtime_lock.process_hold(lock_path)
        out["other_after_reraise"] = other_process_lifecycle(root)
        # The artifact credit runs inside the lock: stat-only, so a credited
        # path naming the lock file itself keeps the hold.
        life.HOOK = None
        during_cost = []
        with mock.patch.object(handler.telemetry, "record_tool_cost",
                               lambda name, **kw: during_cost.append(other_process_lifecycle(root))):
            ccall(mcp, "acme_record", {"note": lifecycle_lock.LIFECYCLE_MUTATION_LOCK_REL.as_posix()})
        out["lock_while_crediting_lock_file"] = during_cost
        # AC-5: derived-artifact credit for the declared field only.
        (root / "big.md").write_text("x" * 4000)
        (root / "small.md").write_text("abcd")
        (root / "sub").mkdir(exist_ok=True)
        duplicate_names = ["big.md", "./big.md", "sub/../big.md"]
        try:
            (root / "big-link.md").symlink_to(root / "big.md")
            duplicate_names.append("big-link.md")
        except (OSError, NotImplementedError):
            pass  # no symlink privilege (Windows without Developer Mode): the other names still cover it
        outside = root.parent / "outside-credit.md"
        outside.write_text("y" * 4000)
        costs = []
        extract = impl._artifact_from_written_paths("written")
        with mock.patch.object(handler.telemetry, "record_tool_cost",
                               lambda name, **kw: costs.append({"name": name, **{k: kw.get(k) for k in (
                                   "request_tokens", "derived_artifact_tokens", "event_id")}})):
            cases = {
                "ok": ("acme_make", {"written": ["big.md", "small.md"]}),
                "replay": ("acme_make", {"written": ["big.md", "small.md"]}),
                "error": ("acme_make", {"written": ["big.md"], "status": "error"}),
                "outside": ("acme_make", {"written": ["../outside-credit.md"]}),
                "missing": ("acme_make", {"written": ["nope.md"]}),
                "undeclared": ("acme_make_free", {"written": ["big.md"]}),
                "single": ("acme_make", {"written": ["big.md"]}),
                "duplicate": ("acme_make", {"written": duplicate_names}),
            }
            credit = {}
            for label, (name, args) in cases.items():
                del costs[:]
                result = ccall(mcp, name, args)
                raw, _event = extract(root, result)
                row = costs[-1] if costs else {}
                credit[label] = {
                    "name": row.get("name"),
                    "credit": row.get("derived_artifact_tokens"),
                    "core_contract": sum(max(0, int(r) - int(row.get("request_tokens") or 0)) for r in raw),
                    "event_id": row.get("event_id"),
                    "status": result.get("status"),
                    "artifacts": len(raw),
                }
        out["credit"] = credit
        # AC-6: core collections untouched and the core-behaviour chain unchanged.
        out["lock_tools_after"] = sorted(impl._LIFECYCLE_MUTATION_LOCK_TOOLS)
        out["artifact_extractors_after"] = sorted(impl._ARTIFACT_EXTRACTORS)
        out["installed_lock_and_credit"] = [sorted(impl._EXTENSION_LIFECYCLE_TOOLS), dict(impl._EXTENSION_ARTIFACT_PATH_FIELDS)]
        # Reload rebuilds the passes from the declaration.
        result = runner.perform_mcp_reload()
        out["reload_status"] = result["status"]
        impl = runner.server_impl
        with lifecycle_held_elsewhere(root):
            out["reload_held_record"] = codes(ccall(mcp, "acme_record", {"note": "n"}))
            out["reload_held_free"] = codes(ccall(mcp, "acme_free"))
        # Dropping both declarations and reloading stops the lock and the credit.
        DECL.write_text(DECL_ORIG + LIFE_DECL.replace(
            'EXTENSION_LIFECYCLE_TOOLS = ("acme_record",)', "EXTENSION_LIFECYCLE_TOOLS = ()").replace(
            'EXTENSION_ARTIFACT_PATH_FIELDS = {"acme_make": "written", "acme_record": "note"}',
            "EXTENSION_ARTIFACT_PATH_FIELDS = {}"))
        result = runner.perform_mcp_reload()
        out["dropped_reload_status"] = result["status"]
        impl = runner.server_impl
        out["dropped_installed"] = [sorted(impl._EXTENSION_LIFECYCLE_TOOLS), dict(impl._EXTENSION_ARTIFACT_PATH_FIELDS)]
        out["dropped_declaration"] = impl.wf_server_info_response(root)["data"]["extensions"]["declaration"]
        with lifecycle_held_elsewhere(root):
            out["dropped_held_record"] = codes(ccall(mcp, "acme_record", {"note": "n"}))
        costs = []
        with mock.patch.object(runner._get_handler().telemetry, "record_tool_cost",
                               lambda name, **kw: costs.append(kw.get("derived_artifact_tokens"))):
            ccall(mcp, "acme_make", {"written": ["big.md"]})
        out["dropped_credit"] = costs
        handler.close()

    elif MODE == "reload":
        DECL.write_text(DECL_ORIG + GOOD_DECL)
        write_module("acme_tools", ACME)
        load_server(); runner = load_thin_runner()
        mcp = runner.build_server(root)
        before = runner.server_impl.wf_server_info_response(root)["data"]["extensions"]["modules"][0]["sha256"]
        write_module("acme_tools", ACME.replace('"version": "v1"', '"version": "v2"'))
        result = runner.perform_mcp_reload()
        out["reload_status"] = result["status"]
        out["echo_version"] = call(mcp, "acme_echo")["data"]["version"]
        after = runner.server_impl.wf_server_info_response(root)["data"]["extensions"]["modules"][0]["sha256"]
        out["sha_changed"] = before != after
        out["sha_matches_file"] = after == hashlib.sha256((SCRATCH / "acme_tools.py").read_bytes()).hexdigest()
        # A broken declaration on reload: only runner tools stay served.
        DECL.write_text(DECL_ORIG + GOOD_DECL + '\nEXTENSION_TOOL_TIERS = {"acme_echo": "read", "acme_write": "write", "acme_ghost": "read"}\n')
        failed = runner.perform_mcp_reload()
        out["failed_reload_codes"] = [d.get("code") for d in failed.get("diagnostics", []) + failed.get("data", {}).get("warnings", [])]
        out["failed_reload_text"] = json.dumps(failed)[:4000]
        out["served_after_failure"] = sorted(table(mcp))
        runner._get_handler().close()

    elif MODE == "startup_fail":
        DECL.write_text(DECL_ORIG + GOOD_DECL + '\nEXTENSION_TOOL_TIERS = {"acme_echo": "read", "acme_write": "write", "acme_ghost": "read"}\n')
        write_module("acme_tools", ACME)
        load_server(); runner = load_thin_runner()
        try:
            runner.build_server(root)
            out["raised"] = None
        except BaseException as exc:
            out["raised"] = type(exc).__name__
            out["message"] = str(exc)
        mcp = getattr(runner, "_mcp", None)
        out["served"] = sorted(table(mcp)) if mcp is not None else None

    elif MODE == "fail":
        from mcp.server.fastmcp import FastMCP
        load_server(); runner = load_thin_runner()
        runner.build_server(root)
        impl = runner.server_impl
        ext = sys.modules["mcp_tool_extensions"]
        write_module("acme_tools", ACME)
        write_module("no_register", "X = 1\n")
        write_module("raiser", "def register(mcp, get_handler):\n    raise ValueError('boom')\n")
        write_module("undeclared_override", "def register(mcp, get_handler):\n    @mcp.tool()\n    def wf_help(**kwargs):\n        return {}\n")
        write_module("bad_compat", (
            "def register(mcp, get_handler):\n"
            "    @mcp.tool()\n"
            "    def wf_current_wave():\n        return {}\n"
            "    @mcp.tool()\n"
            "    def wf_create_wave(mode: str = 'x', parent: 'str | None' = None, **kwargs):\n        return {}\n"
            "    @mcp.tool()\n"
            "    def wf_help(goal: str, **kwargs):\n        return {}\n"
        ))
        write_module("twin_a", "def register(mcp, get_handler):\n    @mcp.tool()\n    def acme_twin(**kwargs):\n        return {}\n")
        write_module("twin_b", "def register(mcp, get_handler):\n    @mcp.tool()\n    def acme_twin(**kwargs):\n        return {}\n")
        write_module("unprefixed", "def register(mcp, get_handler):\n    @mcp.tool()\n    def other_tool(**kwargs):\n        return {}\n")
        write_module("async_tools", "def register(mcp, get_handler):\n    @mcp.tool()\n    async def acme_async(**kwargs):\n        return {}\n")
        write_module("bypass_manager", "def register(mcp, get_handler):\n    def acme_hidden(**kwargs):\n        return {}\n    mcp._tool_manager.add_tool(acme_hidden, name='acme_hidden')\n")
        write_module("bypass_table", (
            "from mcp.server.fastmcp.tools import Tool\n"
            "def register(mcp, get_handler):\n"
            "    def fake(**kwargs):\n        return {}\n"
            "    mcp._tool_manager._tools['wf_help'] = Tool.from_function(fake, name='wf_help')\n"
        ))
        write_module("tamperer", "def register(mcp, get_handler):\n    mcp._tool_manager._tools.pop('acme_twin', None)\n")
        write_module("resource_tools", "def register(mcp, get_handler):\n    @mcp.resource('acme://thing')\n    def thing():\n        return 'x'\n")
        write_module("prompt_tools", "def register(mcp, get_handler):\n    @mcp.prompt()\n    def acme_prompt():\n        return 'x'\n")
        write_module("type_change", (
            "def register(mcp, get_handler):\n"
            "    @mcp.tool()\n"
            "    def wf_create_wave(slug: int, mode: str = 'dry_run', parent: 'str | None' = None, **kwargs):\n        return {}\n"
        ))
        write_module("parent_swallow", (
            "CALLS = []\n"
            "def register(mcp, get_handler):\n"
            "    @mcp.tool()\n"
            "    def wf_create_wave(slug: str, mode: str = 'dry_run', **kwargs):\n"
            "        CALLS.append(sorted(kwargs))\n"
            "        return {'status': 'ok', 'got': sorted(kwargs)}\n"
        ))
        write_module("parent_change", (
            "def register(mcp, get_handler):\n"
            "    @mcp.tool()\n"
            "    def wf_create_wave(slug: str, mode: str = 'dry_run', parent: int = 0, **kwargs):\n        return {}\n"
        ))
        write_module("default_change", (
            "import server_impl\n"
            "def register(mcp, get_handler):\n"
            "    @mcp.tool()\n"
            "    def wf_create_wave(slug: str, mode: str = 'create', parent: 'str | None' = None, **kwargs):\n"
            "        return {'status': 'ok', 'data': {'mode': mode}}\n"
        ))
        write_module("extended_tools", (
            "from typing import Annotated\n"
            "from pydantic import Field\n"
            "import server_impl\n"
            "def register(mcp, get_handler):\n"
            "    @mcp.tool()\n"
            "    def wf_create_wave(slug: Annotated[str, Field(title='Wave slug')], mode: str = 'dry_run', team: str = '', parent: 'str | None' = None, **kwargs):\n"
            "        bad = server_impl.ensure_no_extra_args('wf_create_wave', kwargs)\n"
            "        if bad is not None:\n"
            "            return bad\n"
            "        return {'status': 'ok', 'data': {'slug': slug, 'team': team}}\n"
        ))
        write_module("wf_fork", (
            "import server_impl\n"
            "def register(mcp, get_handler):\n"
            "    @mcp.tool()\n"
            "    def wf_fork_tool(**kwargs):\n"
            "        bad = server_impl.ensure_no_extra_args('wf_fork_tool', kwargs)\n"
            "        if bad is not None:\n"
            "            return bad\n"
            "        return {'status': 'ok', 'data': {'fork': True}}\n"
        ))
        write_module("retired_name", "def register(mcp, get_handler):\n    @mcp.tool()\n    def wf_review_evidence(**kwargs):\n        return {}\n")
        write_module("reserved_name", "def register(mcp, get_handler):\n    @mcp.tool()\n    def wf_fixture_reserved(**kwargs):\n        return {}\n")
        write_module("withdrawer", (
            "import server_impl\n"
            "def register(mcp, get_handler):\n"
            "    @mcp.tool()\n"
            "    def wf_current_wave(**kwargs):\n        return {}\n"
            "    mcp.remove_tool('wf_current_wave')\n"
        ))
        write_module("served_writer", (
            "import server_impl\n"
            "def register(mcp, get_handler):\n"
            "    def acme_sneak(**kwargs):\n        return {}\n"
            "    server_impl._MCP_INSTANCE.add_tool(acme_sneak, name='acme_sneak')\n"
        ))
        write_module("replace_close", (
            "import server_impl\n"
            "def register(mcp, get_handler):\n"
            "    @mcp.tool()\n"
            "    def wf_close_wave(item: str, **kwargs):\n"
            "        bad = server_impl.ensure_no_extra_args('wf_close_wave', kwargs)\n"
            "        if bad is not None:\n"
            "            return bad\n"
            "        return {'status': 'ok', 'data': {'item': item}}\n"
        ))
        write_module("open_replacement", "def register(mcp, get_handler):\n    @mcp.tool()\n    def wf_close_wave(item: str):\n        return {}\n")
        write_module("ask_undeclared", "def register(mcp, get_handler):\n    mcp.core_handler('wf_help')\n")
        write_module("echo_tool", (
            "import server_impl\n"
            "def register(mcp, get_handler):\n"
            "    @mcp.tool()\n"
            "    def acme_echo(text: str = '', count: int = 3, **kwargs):\n"
            "        return {'status': 'ok'}\n"
        ))
        outside = Path(tmp) / "outside"
        outside.mkdir()
        (outside / "escaped.py").write_text("def register(mcp, get_handler):\n    pass\n")
        (SCRATCH / "escaped.py").symlink_to(outside / "escaped.py")
        # Wave 1zls8 (1zltx): helper fixtures. A plainly imported module that
        # is not a framework script backs the already-imported cases, since a
        # framework script name is now refused by the declaration itself.
        write_module("plain_imported", "X = 1\n")
        import plain_imported  # noqa: F401
        # A module-level __getattr__ answers every name, __wf_extension__ included.
        write_module("lazy_truthy", "def __getattr__(name):\n    return True\n")
        import lazy_truthy  # noqa: F401
        write_module("helper_first", "import helper_second\n")
        write_module("helper_second", "Y = 2\n")
        write_module("helper_raises", "raise RuntimeError('helper boom')\n")
        write_module("acme_helper", "Z = 3\n")
        write_module("helper_with_register", (
            "CALLS = []\n"
            "def register(mcp, get_handler):\n"
            "    CALLS.append(1)\n"
        ))

        cases = {
            "missing_module": dict(EXTENSION_MODULES=("not_there",)),
            "outside_scripts": dict(EXTENSION_MODULES=("escaped",)),
            "already_imported": dict(EXTENSION_MODULES=("plain_imported",)),
            # Wave 1zls8 (1zltx): framework script names and helper modules.
            "framework_script_name": dict(EXTENSION_MODULES=("record_paths",)),
            "helper_framework_script": dict(EXTENSION_HELPER_MODULES=("lifecycle_lock",)),
            "helper_outside_scripts": dict(EXTENSION_HELPER_MODULES=("escaped",)),
            "helper_miscased": dict(EXTENSION_HELPER_MODULES=("Acme_Helper",)),
            "helper_already_imported": dict(EXTENSION_HELPER_MODULES=("plain_imported",)),
            "helper_lazy_truthy": dict(EXTENSION_HELPER_MODULES=("lazy_truthy",)),
            "module_lazy_truthy": dict(EXTENSION_MODULES=("lazy_truthy",)),
            "helper_out_of_order": dict(EXTENSION_HELPER_MODULES=("helper_first", "helper_second")),
            "helper_import_raises": dict(EXTENSION_HELPER_MODULES=("helper_raises",)),
            "helper_missing": dict(EXTENSION_HELPER_MODULES=("helper_not_there",)),
            "helper_also_module": dict(EXTENSION_MODULES=("acme_tools",), EXTENSION_HELPER_MODULES=("acme_tools",)),
            "helper_with_register": dict(EXTENSION_HELPER_MODULES=("helper_with_register",), EXTENSION_TOOL_ALIASES={"wf_alias_help": "wf_help"}),
            "stdlib_name": dict(EXTENSION_MODULES=("json",)),
            "reserved_name": dict(EXTENSION_MODULES=("server_impl",)),
            "no_register": dict(EXTENSION_MODULES=("no_register",)),
            "register_raises": dict(EXTENSION_MODULES=("raiser",)),
            "undeclared_override": dict(EXTENSION_MODULES=("undeclared_override",)),
            "runner_override": dict(EXTENSION_MODULES=("acme_tools",), EXTENSION_OVERRIDES={"acme_tools": ("wf_reload_mcp",)}),
            "unknown_override": dict(EXTENSION_MODULES=("acme_tools",), EXTENSION_OVERRIDES={"acme_tools": ("wf_not_a_tool",)}),
            "override_not_registered": dict(EXTENSION_MODULES=("unprefixed",),EXTENSION_TOOL_PREFIXES=("other_",), EXTENSION_TOOL_TIERS={"other_tool": "read"}, EXTENSION_OVERRIDES={"unprefixed": ("wf_help",)}),
            "override_two_modules": dict(EXTENSION_MODULES=("twin_a", "twin_b"), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_twin": "read"}, EXTENSION_OVERRIDES={"twin_a": ("wf_help",), "twin_b": ("wf_help",)}),
            "new_name_two_modules": dict(EXTENSION_MODULES=("twin_a", "twin_b"), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_twin": "read"}),
            "no_prefix_registered": dict(EXTENSION_MODULES=("unprefixed",), EXTENSION_TOOL_PREFIXES=("acme_",)),
            "no_tier_registered": dict(EXTENSION_MODULES=("twin_a",), EXTENSION_TOOL_PREFIXES=("acme_",)),
            "tier_unregistered": dict(EXTENSION_MODULES=("twin_a",), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_twin": "read", "acme_ghost": "read"}),
            "core_prefix_new_tool": dict(EXTENSION_MODULES=("wf_fork",), EXTENSION_TOOL_PREFIXES=("wf_",), EXTENSION_TOOL_TIERS={"wf_fork_tool": "read"}),
            "reserved_retired_name": dict(EXTENSION_MODULES=("retired_name",), EXTENSION_TOOL_PREFIXES=("wf_",), EXTENSION_TOOL_TIERS={"wf_review_evidence": "read"}),
            "reserved_collection_name": dict(EXTENSION_MODULES=("reserved_name",), EXTENSION_TOOL_PREFIXES=("wf_",), EXTENSION_TOOL_TIERS={"wf_fixture_reserved": "read"}),
            "async_handler": dict(EXTENSION_MODULES=("async_tools",), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_async": "read"}),
            "unrecorded_manager_add": dict(EXTENSION_MODULES=("bypass_manager",), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_hidden": "read"}),
            "unrecorded_table_write": dict(EXTENSION_MODULES=("bypass_table",)),
            "tampered_staging": dict(EXTENSION_MODULES=("twin_a", "tamperer"), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_twin": "read"}),
            "resource_registered": dict(EXTENSION_MODULES=("resource_tools",)),
            "prompt_registered": dict(EXTENSION_MODULES=("prompt_tools",)),
            "type_changed_override": dict(EXTENSION_MODULES=("type_change",), EXTENSION_OVERRIDES={"type_change": ("wf_create_wave",)}),
            "extended_override": dict(EXTENSION_MODULES=("extended_tools",), EXTENSION_OVERRIDES={"extended_tools": ("wf_create_wave",)}),
            "default_changed_override": dict(EXTENSION_MODULES=("default_change",), EXTENSION_OVERRIDES={"default_change": ("wf_create_wave",)}),
            "parent_changed_override": dict(EXTENSION_MODULES=("parent_change",), EXTENSION_OVERRIDES={"parent_change": ("wf_create_wave",)}),
            "parent_swallowing_override": dict(EXTENSION_MODULES=("parent_swallow",), EXTENSION_OVERRIDES={"parent_swallow": ("wf_create_wave",)}),
            "withdrawn_override": dict(EXTENSION_MODULES=("withdrawer",), EXTENSION_OVERRIDES={"withdrawer": ("wf_current_wave",)}),
            "served_table_write": dict(EXTENSION_MODULES=("served_writer",), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_sneak": "read"}),
            "incompatible_override": dict(EXTENSION_MODULES=("bad_compat",), EXTENSION_OVERRIDES={"bad_compat": ("wf_current_wave", "wf_create_wave", "wf_help")}),
            # Wave 1z8oz: aliases, hidden names and replacements.
            "alias_runner_name": dict(EXTENSION_TOOL_ALIASES={"wf_reload_mcp": "wf_help"}),
            "alias_existing_name": dict(EXTENSION_TOOL_ALIASES={"wf_help": "wf_current_wave"}),
            "alias_no_prefix": dict(EXTENSION_TOOL_ALIASES={"other_help": "wf_help"}),
            "alias_missing_target": dict(EXTENSION_TOOL_ALIASES={"wf_alias_ghost": "wf_not_a_tool"}),
            "alias_of_alias": dict(EXTENSION_TOOL_ALIASES={"wf_alias_a": "wf_help", "wf_alias_b": "wf_alias_a"}),
            "alias_retired_name": dict(EXTENSION_TOOL_ALIASES={"wf_review_evidence": "wf_help"}),
            "hidden_without_alias": dict(EXTENSION_HIDDEN_TOOLS=("wf_help",)),
            "hidden_runner": dict(EXTENSION_HIDDEN_TOOLS=("wf_reload_mcp",)),
            "hidden_twice": dict(EXTENSION_TOOL_ALIASES={"wf_alias_help": "wf_help"}, EXTENSION_HIDDEN_TOOLS=("wf_help", "wf_help")),
            "alias_of_alias_for_core": dict(EXTENSION_MODULES=("replace_close",), EXTENSION_REPLACEMENTS={"replace_close": {"wf_close_wave": {"alias_for_core": "wf_core_close"}}}, EXTENSION_TOOL_ALIASES={"wf_alias_core": "wf_core_close"}),
            "alias_to_replaced": dict(EXTENSION_MODULES=("replace_close",), EXTENSION_REPLACEMENTS={"replace_close": {"wf_close_wave": {"alias_for_core": "wf_core_close"}}}, EXTENSION_TOOL_ALIASES={"wf_alias_close": "wf_close_wave"}),
            "hide_replaced": dict(EXTENSION_MODULES=("replace_close",), EXTENSION_REPLACEMENTS={"replace_close": {"wf_close_wave": {"alias_for_core": "wf_core_close"}}}, EXTENSION_HIDDEN_TOOLS=("wf_close_wave",)),
            "replace_runner": dict(EXTENSION_MODULES=("replace_close",), EXTENSION_REPLACEMENTS={"replace_close": {"wf_reload_mcp": {"alias_for_core": "wf_core_reload"}}}),
            "replace_and_override": dict(EXTENSION_MODULES=("replace_close",), EXTENSION_OVERRIDES={"replace_close": ("wf_close_wave",)}, EXTENSION_REPLACEMENTS={"replace_close": {"wf_close_wave": {"alias_for_core": "wf_core_close"}}}),
            "replace_bad_tier": dict(EXTENSION_MODULES=("replace_close",), EXTENSION_REPLACEMENTS={"replace_close": {"wf_close_wave": {"alias_for_core": "wf_core_close", "tier": "admin"}}}),
            "replace_alias_collides": dict(EXTENSION_MODULES=("replace_close",), EXTENSION_REPLACEMENTS={"replace_close": {"wf_close_wave": {"alias_for_core": "wf_help"}}}),
            "replace_alias_retired": dict(EXTENSION_MODULES=("replace_close",), EXTENSION_REPLACEMENTS={"replace_close": {"wf_close_wave": {"alias_for_core": "wf_review_evidence"}}}),
            "replace_open_schema": dict(EXTENSION_MODULES=("open_replacement",), EXTENSION_REPLACEMENTS={"open_replacement": {"wf_close_wave": {"alias_for_core": "wf_core_close"}}}),
            "aliases_only_served": dict(EXTENSION_TOOL_ALIASES={"wf_alias_help": "wf_help"}),
            "replace_not_registered": dict(EXTENSION_MODULES=("twin_a",), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_twin": "read"}, EXTENSION_REPLACEMENTS={"twin_a": {"wf_close_wave": {"alias_for_core": "wf_core_close"}}}),
            # Wave 1zicq: no tier downgrade; the edit-gate tools cannot be taken over.
            "replace_downgrade": dict(EXTENSION_MODULES=("replace_close",), EXTENSION_REPLACEMENTS={"replace_close": {"wf_close_wave": {"alias_for_core": "wf_core_close", "tier": "read"}}}),
            "override_gate": dict(EXTENSION_MODULES=("replace_close",), EXTENSION_OVERRIDES={"replace_close": ("wf_open_gate",)}),
            "replace_gate": dict(EXTENSION_MODULES=("replace_close",), EXTENSION_REPLACEMENTS={"replace_close": {"wf_close_gate": {"alias_for_core": "wf_core_close_gate"}}}),
            "hidden_gate": dict(EXTENSION_TOOL_ALIASES={"wf_alias_open_gate": "wf_open_gate"}, EXTENSION_HIDDEN_TOOLS=("wf_open_gate",)),
            # Wave 1zim3: parameter mappings and core_handler.
            "params_not_alias": dict(EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"rename": {"set_id": "wave_id"}}}),
            "params_unknown_key": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"rename": {}, "pin": {}}}),
            "params_rename_unknown": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"rename": {"set_id": "set_id"}}}),
            "params_rename_twice": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"rename": {"set_id": "wave_id", "box_id": "wave_id"}}}),
            "params_fixed_unknown": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"fixed": {"force": True}}}),
            "params_fixed_renamed": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"rename": {"how": "mode"}, "fixed": {"mode": "create"}}}),
            "params_fixed_type": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"fixed": {"mode": 5}}}),
            "params_kwargs_name": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"rename": {"kwargs": "wave_id"}}}),
            "params_model_prefix": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"rename": {"model_id": "wave_id"}}}),
            "params_model_attribute": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"rename": {"copy": "wave_id"}}}),
            "params_duplicate_name": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"rename": {"change_id": "wave_id"}}}),
            "params_runner": dict(EXTENSION_TOOL_ALIASES={"wf_alias_reload": "wf_reload_mcp"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_reload": {}}),
            "params_edit_gate": dict(EXTENSION_TOOL_ALIASES={"wf_alias_gate": "wf_open_gate"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_gate": {"rename": {"name": "gate"}}}),
            "params_hide_pinned_only": dict(EXTENSION_TOOL_ALIASES={"wf_alias_review": "wf_review_wave"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_review": {"fixed": {"phase": "prepare"}}}, EXTENSION_HIDDEN_TOOLS=("wf_review_wave",)),
            "params_swap_valid": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"rename": {"set_id": "wave_id", "wave_id": "change_id"}}}),
            "core_handler_undeclared": dict(EXTENSION_MODULES=("ask_undeclared",)),
            # Wave 1zim3 repair: strict fixed values, name rules, extension-tool targets.
            "params_bool_string": dict(EXTENSION_TOOL_ALIASES={"wf_alias_read": "code_read"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_read": {"fixed": {"with_line_numbers": "false"}}}),
            "params_int_string": dict(EXTENSION_TOOL_ALIASES={"wf_alias_waves": "wf_list_waves"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_waves": {"fixed": {"limit": "3"}}}),
            "params_underscore_name": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"rename": {"_x": "wave_id"}}}),
            "params_keyword_name": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"rename": {"class": "wave_id"}}}),
            "params_ext_rename_unknown": dict(EXTENSION_MODULES=("echo_tool",), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_echo": "read"}, EXTENSION_TOOL_ALIASES={"acme_say": "acme_echo"}, EXTENSION_TOOL_PARAMETERS={"acme_say": {"rename": {"words": "nope"}}}),
            # Wave 1zime (1zimm): the optional alias description.
            "params_desc_not_str": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"rename": {"set_id": "wave_id"}, "description": 5}}),
            "params_desc_empty": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"rename": {"set_id": "wave_id"}, "description": ""}}),
            "params_desc_blank": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"rename": {"set_id": "wave_id"}, "description": " \n\t "}}),
            "params_desc_too_long": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"rename": {"set_id": "wave_id"}, "description": "x" * 16385}}),
            "params_desc_plain": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"description": "An alias."}}),
            "params_desc_empty_mappings": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"rename": {}, "fixed": {}, "description": "An alias."}}),
            # Wave 1zls8 (1zlty): response_keys refused by the server's declaration check.
            "params_response_keys_bad_path": dict(EXTENSION_TOOL_ALIASES={"wf_alias_get": "wf_get_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_get": {"response_keys": {"changes\n": "items"}}}),
            "params_response_keys_echo": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"rename": {"set_id": "wave_id"}, "response_keys": {"wave_id": "set_key"}}}),
            "params_desc_max_valid": dict(EXTENSION_TOOL_ALIASES={"wf_alias_add": "wf_add_change"}, EXTENSION_TOOL_PARAMETERS={"wf_alias_add": {"rename": {"set_id": "wave_id"}, "description": "y" * 16384}}),
            "params_ext_fixed_type": dict(EXTENSION_MODULES=("echo_tool",), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_echo": "read"}, EXTENSION_TOOL_ALIASES={"acme_say": "acme_echo"}, EXTENSION_TOOL_PARAMETERS={"acme_say": {"fixed": {"count": "3"}}}),
            # Wave 1zimf (1zimo): a lock or credit declaration without a registered tool.
            "lifecycle_unregistered": dict(EXTENSION_MODULES=("twin_a",), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_twin": "read", "acme_ghost": "write"}, EXTENSION_LIFECYCLE_TOOLS=("acme_ghost",)),
            "artifact_unregistered": dict(EXTENSION_MODULES=("twin_a",), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_twin": "read", "acme_ghost": "write"}, EXTENSION_ARTIFACT_PATH_FIELDS={"acme_ghost": "path"}),
            "lifecycle_reserved_name": dict(EXTENSION_MODULES=("retired_name",), EXTENSION_TOOL_PREFIXES=("wf_",), EXTENSION_TOOL_TIERS={"wf_review_evidence": "write"}, EXTENSION_LIFECYCLE_TOOLS=("wf_review_evidence",), EXTENSION_ARTIFACT_PATH_FIELDS={"wf_review_evidence": "path"}),
            "lifecycle_invalid_declaration": dict(EXTENSION_MODULES=("twin_a",), EXTENSION_TOOL_PREFIXES=("acme_",), EXTENSION_TOOL_TIERS={"acme_twin": "read"}, EXTENSION_LIFECYCLE_TOOLS=("acme_twin",)),
        }
        empty = dict(EXTENSION_MODULES=(), EXTENSION_HELPER_MODULES=(), EXTENSION_TOOL_PREFIXES=(), EXTENSION_TOOL_TIERS={}, EXTENSION_OVERRIDES={},
                     EXTENSION_TOOL_ALIASES={}, EXTENSION_TOOL_PARAMETERS={}, EXTENSION_HIDDEN_TOOLS=(),
                     EXTENSION_LIFECYCLE_TOOLS=(), EXTENSION_ARTIFACT_PATH_FIELDS={}, EXTENSION_SKILLS={},
                     EXTENSION_JOURNAL_TEMPLATES=(), EXTENSION_JOURNAL_PRE_MIGRATION_HOOK="",
                     EXTENSION_REPLACEMENTS={})
        results = {}
        for label, attrs in cases.items():
            for key, value in {**empty, **attrs}.items():
                setattr(ext, key, value)
            for mod in ("acme_tools", "no_register", "raiser", "undeclared_override", "bad_compat", "twin_a", "twin_b", "unprefixed", "escaped", "not_there",
                        "async_tools", "bypass_manager", "bypass_table", "tamperer", "resource_tools", "prompt_tools",
                        "withdrawer", "served_writer", "type_change", "parent_change", "parent_swallow", "default_change", "extended_tools",
                        "wf_fork", "retired_name", "reserved_name", "replace_close", "open_replacement", "ask_undeclared", "echo_tool"):
                if getattr(sys.modules.get(mod), "__wf_extension__", False):
                    sys.modules.pop(mod, None)
            mcp = FastMCP("case")
            if label == "reserved_collection_name":
                impl._COST_FOCUS_EXTRACTORS["wf_fixture_reserved"] = lambda *a, **k: None
            try:
                impl.register_mcp_surface(mcp, runner._get_handler)
                results[label] = {"raised": None, "served": len(table(mcp))}
                if label == "core_prefix_new_tool":
                    import mcp_tool_roster
                    results[label]["call"] = ccall(mcp, "wf_fork_tool")["data"]
                    results[label]["tier"] = impl._TOOL_REGISTRY.get("wf_fork_tool").tier
                    results[label]["markers"] = markers(mcp, "wf_fork_tool")
                    results[label]["parity_defects"] = [d.name for d in impl._TOOL_REGISTRY.parity_defects]
                    results[label]["read_rule"] = "mcp__wavefoundry__wf_fork_tool" in mcp_tool_roster.allow_rules(False)
                if label == "aliases_only_served":
                    import mcp_tool_roster
                    results[label]["call"] = ccall(mcp, "wf_alias_help")["status"]
                    results[label]["shares_fn"] = table(mcp)["wf_alias_help"].fn is table(mcp)["wf_help"].fn
                    results[label]["parity_defects"] = [d.name for d in impl._TOOL_REGISTRY.parity_defects]
                    results[label]["read_rule"] = "mcp__wavefoundry__wf_alias_help" in mcp_tool_roster.allow_rules(False)
                if label == "params_swap_valid":
                    results[label]["parameters"] = normalized(table(mcp)["wf_alias_add"].parameters)
                if label == "params_desc_max_valid":
                    results[label]["description"] = table(mcp)["wf_alias_add"].description
                if label == "helper_with_register":
                    results[label]["register_calls"] = list(sys.modules["helper_with_register"].CALLS)
                    results[label]["helpers"] = [h["module"] for h in (impl._EXTENSION_PROVENANCE or {}).get("helper_modules", [])]
                if label == "parent_swallowing_override":
                    # Wave 1zlu1 (N1): the handler swallows **kwargs, so only
                    # the structural guard can refuse an omitted parameter.
                    spy = sys.modules["parent_swallow"].CALLS
                    refused = ccall(mcp, "wf_create_wave", {"slug": "s", "parent": "q4"})
                    results[label]["refused"] = [refused.get("status")] + [d["code"] for d in refused.get("diagnostics", [])]
                    results[label]["rejected"] = (refused.get("data") or {}).get("rejected_arguments")
                    results[label]["calls_after_refusal"] = list(spy)
                    results[label]["plain"] = ccall(mcp, "wf_create_wave", {"slug": "s"}).get("got")
                    results[label]["calls_after_plain"] = list(spy)
                    results[label]["markers"] = list(markers(mcp, "wf_create_wave"))
                if label == "extended_override":
                    results[label]["with_team"] = ccall(mcp, "wf_create_wave", {"slug": "probe", "team": "blue"})["data"]
                    results[label]["core_call"] = ccall(mcp, "wf_create_wave", {"slug": "probe"})["data"]
            except BaseException as exc:
                results[label] = {"raised": type(exc).__name__, "message": str(exc), "served": sorted(table(mcp))}
                if label.startswith("helper_"):
                    # Wave 1zls8 (1zltx): a failed install leaves no declared module it imported.
                    results[label]["left_in_modules"] = sorted(
                        name for name in ("helper_first", "helper_second", "helper_raises", "acme_helper", "escaped")
                        if name in sys.modules)
            impl._COST_FOCUS_EXTRACTORS.pop("wf_fixture_reserved", None)
        out["cases"] = results
        # Wave 1z8oz: registering again after a replacement leaves no replaced state behind.
        for key, value in {**empty, "EXTENSION_MODULES": ("replace_close",),
                           "EXTENSION_REPLACEMENTS": {"replace_close": {"wf_close_wave": {"alias_for_core": "wf_core_close"}}}}.items():
            setattr(ext, key, value)
        sys.modules.pop("replace_close", None)
        with_replacement = FastMCP("with_replacement")
        impl.register_mcp_surface(with_replacement, runner._get_handler)
        out["replaced_during"] = sorted(impl._EXTENSION_REPLACED_CORE)
        for key, value in empty.items():
            setattr(ext, key, value)
        stock_again = FastMCP("stock_again")
        impl.register_mcp_surface(stock_again, runner._get_handler)
        out["replaced_after_stock"] = sorted(impl._EXTENSION_REPLACED_CORE)
        out["stock_again_markers"] = markers(stock_again, "wf_close_wave")
        # The allowlist renderer refuses an invalid tier declaration.
        for key, value in {**empty, "EXTENSION_TOOL_PREFIXES": ("acme_",), "EXTENSION_TOOL_TIERS": {"wf_upgrade": "read"}}.items():
            setattr(ext, key, value)
        import mcp_tool_roster, render_platform_surfaces
        settings = root / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text("{}\n")
        try:
            mcp_tool_roster.allow_rules(False)
            out["roster_raised"] = None
        except Exception as exc:
            out["roster_raised"] = type(exc).__name__
        try:
            render_platform_surfaces.render_claude_permissions(root)
            out["renderer_raised"] = None
        except Exception as exc:
            out["renderer_raised"] = type(exc).__name__
        out["settings_after"] = settings.read_text()
        for key, value in empty.items():
            setattr(ext, key, value)
        runner._get_handler().close()

    elif MODE == "response_keys":
        # Wave 1zls8 (1zlty AC-2 to AC-6): declared response-key renames through call_tool.
        DECL.write_text(DECL_ORIG + KEYS_DECL)
        load_server(); runner = load_thin_runner()
        mcp = runner.build_server(root)
        impl = runner.server_impl
        import copy
        created = impl.wf_create_wave_response(root, "keyed", mode="create")
        wave_id = created["data"]["wave_id"]
        # One admitted change, written in the loaded vocabulary.
        vp = impl._vocab
        wave_md = impl.find_wave_record(root, wave_id)[0]
        change_id = "1abce-enh keyed-item"
        (wave_md.parent / f"{change_id}.md").write_text(
            f"# Keyed Item\n\n{vp.MEMBER_ID_LABEL}: `{change_id}`\n{vp.MEMBER_STATUS_LABEL}: `planned`\n", encoding="utf-8")
        with wave_md.open("a", encoding="utf-8") as record:
            record.write(f"\n{vp.MEMBER_ID_LABEL}: `{change_id}`\n{vp.MEMBER_STATUS_LABEL}: `planned`\n")
        out["admitted"] = [c["id"] for c in impl.wf_get_change_response(root, wave_id=wave_id)["data"]["changes"]]
        out["items_bulk"] = ccall(mcp, "fork_get_items", {"wave_id": wave_id})
        out["canonical_bulk"] = ccall(mcp, "wf_get_change", {"wave_id": wave_id})
        out["plain_bulk"] = ccall(mcp, "fork_get_plain", {"wave_id": wave_id})
        out["items_unknown"] = ccall(mcp, "fork_get_items", {"wave_id": wave_id, "bogus": 1})
        out["listed_description"] = {t.name: t.description for t in asyncio.run(mcp.list_tools())}.get("fork_get_items")
        # A fixture core response with nested lists, collisions and wrong types.
        source = copy.deepcopy(NESTED_RESULT)
        impl.wf_add_change_response = lambda root_, *a, **k: source
        before = copy.deepcopy(source)
        result = table(mcp)["fork_add_item"].fn(set_id="1abcd", item_id="1abce-enh x")
        out["nested"] = result
        out["nested_input_unchanged"] = source == before
        out["nested_identity"] = {
            "note_value": result["data"]["items"][1]["note"] is source["data"]["changes"][1]["note"],
            "collided_element": result["data"]["items"][0] is source["data"]["changes"][0],
            "list_is_new": result["data"]["items"] is not source["data"]["changes"],
            "renamed_element_is_new": result["data"]["items"][1] is not source["data"]["changes"][1],
            "meta_is_new": result["data"]["meta"] is not source["data"]["meta"],
            "meta_list_is_new": result["data"]["meta"]["list"] is not source["data"]["meta"]["list"],
            "untouched_element": result["data"]["meta"]["list"][2] is source["data"]["meta"]["list"][2],
            "diagnostics_input_unchanged": source["diagnostics"] == before["diagnostics"],
        }
        out["canonical_add"] = ccall(mcp, "wf_add_change", {"wave_id": "1abcd", "change_id": "1abce-enh x"})
        out["extensions"] = impl.wf_server_info_response(root)["data"]["extensions"]
        runner._get_handler().close()

    elif MODE == "override_costs":
        # Wave 1zls8 (1zltz AC-1, AC-2, AC-4 to AC-6, AC-9, AC-10).
        DECL.write_text(DECL_ORIG + MEASURED_DECL)
        write_module("fork_measured", MEASURED)
        load_server(); runner = load_thin_runner()
        mcp = runner.build_server(root)
        impl = runner.server_impl
        import context_efficiency, lifecycle_lock, runtime_lock, os
        from unittest import mock
        fork = sys.modules["fork_measured"]
        handler = runner._get_handler()
        size = lambda value: context_efficiency.estimate_tokens_utf8(json.dumps(value, sort_keys=True, default=str))
        (root / "mod.py").write_text("def alpha():\n    return 1\n\nclass Beta:\n    def gamma(self):\n        return 2\n")
        out["markers"] = {n: markers(mcp, n) for n in ("wf_close_wave", "code_outline", "wf_current_wave")}
        out["deltas_installed"] = sorted(impl._EXTENSION_OVERRIDE_DELTAS)
        out["cost_pass_kwargs"] = sorted(impl._cost_pass_kwargs())
        out["override_deltas"] = sorted(impl._cost_pass_kwargs().get("override_deltas", ()))

        def recorded(name, call_args, behaviours):
            fork.BEHAVIOUR.update(behaviours)
            costs, workflow = [], []
            real_workflow = handler.telemetry.record_workflow
            with mock.patch.object(handler.telemetry, "record_tool_cost",
                                   lambda tool, **kw: costs.append({"name": tool, **{k: kw.get(k) for k in (
                                       "request_tokens", "response_tokens", "derived_artifact_tokens")}})), \
                    mock.patch.object(handler.telemetry, "record_workflow",
                                      lambda *a, **k: workflow.append(a[2]) or real_workflow(*a, **k)):
                result = ccall(mcp, name, call_args)
            last = fork.LAST.pop(name, None)
            return {"costs": costs, "workflow": workflow, "status": result.get("status"),
                    "added": "fork_added" in result,
                    "expected_delta": size(last["final"]) - size(last["core"]) if last else None,
                    "core_size": size(last["core"]) if last else None}

        close_args = {"wave_id": "1abcd", "mode": "dry_run"}
        out["close_add"] = recorded("wf_close_wave", close_args, {"wf_close_wave": "add"})
        out["close_same"] = recorded("wf_close_wave", close_args, {"wf_close_wave": "same"})
        out["close_self"] = recorded("wf_close_wave", close_args, {"wf_close_wave": "self"})
        out["close_non_exempt_core"] = recorded("wf_close_wave", close_args, {"wf_close_wave": "non_exempt_core"})
        out["close_self_request"] = size({"wave_id": "1abcd", "mode": "dry_run"})
        out["close_self_response"] = size({"status": "ok", "data": {"answered": "1abcd"}})
        # A direct core call outside any override records the core's own events only.
        costs, workflow = [], []
        real_workflow = handler.telemetry.record_workflow
        with mock.patch.object(handler.telemetry, "record_tool_cost", lambda tool, **kw: costs.append(tool)), \
                mock.patch.object(handler.telemetry, "record_workflow",
                                  lambda *a, **k: workflow.append(a[2]) or real_workflow(*a, **k)):
            fork.CORES["wf_close_wave"](wave_id="1abcd", mode="dry_run")
        out["direct_core"] = {"costs": costs, "workflow": workflow}
        out["outline_add"] = recorded("code_outline", {"path": "mod.py"}, {"code_outline": "add"})
        out["outline_same"] = recorded("code_outline", {"path": "mod.py"}, {"code_outline": "same"})
        out["outline_self"] = recorded("code_outline", {"path": "mod.py"}, {"code_outline": "self"})
        out["outline_self_request"] = size({"path": "mod.py"})
        out["outline_self_response"] = size({"status": "ok", "data": {"path": "mod.py", "symbols": []}})
        out["current"] = recorded("wf_current_wave", {}, {})
        costs = []
        with mock.patch.object(handler.telemetry, "record_tool_cost", lambda tool, **kw: costs.append(
                {"name": tool, "request_tokens": kw.get("request_tokens"), "response_tokens": kw.get("response_tokens")})):
            current_result = table(mcp)["wf_current_wave"].fn()
        out["current_direct"] = {"costs": costs, "request": size({}), "response": size(current_result)}
        # AC-5: observational. A failing telemetry write and an active checkpoint
        # leave the result unchanged and record nothing.
        fork.BEHAVIOUR.update({"code_outline": "add"})
        def boom(*a, **k):
            raise RuntimeError("telemetry down")
        with mock.patch.object(handler.telemetry, "record_tool_cost", boom):
            failing = ccall(mcp, "code_outline", {"path": "mod.py"})
        out["failing_telemetry"] = {"status": failing.get("status"), "added": "fork_added" in failing}
        checkpoint = root / ".wavefoundry" / "upgrade-in-progress.json"
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text(json.dumps({"current_phase": "extracting"}))
        guarded_costs = []
        with mock.patch.object(handler.telemetry, "record_tool_cost", lambda tool, **kw: guarded_costs.append(tool)):
            during = ccall(mcp, "code_outline", {"path": "mod.py"})
            out["checkpoint_outline"] = {"status": during.get("status"), "added": "fork_added" in during,
                                         "costs": list(guarded_costs)}
            # AC-10: the guard refuses the override of a locked exempt name before its body runs.
            del fork.EVENTS[:]
            fork.BEHAVIOUR.update({"wf_close_wave": "add"})
            refused = ccall(mcp, "wf_close_wave", close_args)
            out["checkpoint_close"] = {"codes": codes(refused), "body_ran": list(fork.EVENTS),
                                       "costs": list(guarded_costs)}
        checkpoint.unlink()
        # AC-6: after core_handler returns, the override still holds the lifecycle lock.
        lock_path = root / lifecycle_lock.LIFECYCLE_MUTATION_LOCK_REL
        def observe(hroot):
            hold = runtime_lock.process_hold(lock_path)
            return {"hold_registered": hold is not None and hold.get("pid") == os.getpid(),
                    "other_process": other_process_lifecycle(hroot)}
        fork.HOOK = observe
        observed = ccall(mcp, "wf_close_wave", close_args)
        fork.HOOK = None
        out["lock_after_core"] = observed.get("seen")
        out["lock_after_return"] = other_process_lifecycle(root)
        # AC-9: the stage calls count in the context-efficiency totals.
        created = impl.wf_create_wave_response(root, "measured", mode="create")
        wave_id = created["data"]["wave_id"]
        def calls():
            snapshot = context_efficiency.read_wave_snapshot(root, wave_id)
            return {"review": snapshot["stages"].get("review", {}).get("calls", 0),
                    "total": snapshot["totals"]["calls"] + context_efficiency.read_general_totals(root)["calls"]}
        handler.telemetry.set_focus(wave_id, "review")
        counts = {}
        before = calls()
        fork.CORES["wf_close_wave"](wave_id=wave_id, mode="dry_run")
        counts["direct"] = {k: v - before[k] for k, v in calls().items()}
        for how in ("same", "add"):
            fork.BEHAVIOUR.update({"wf_close_wave": how})
            handler.telemetry.set_focus(wave_id, "review")
            before = calls()
            ccall(mcp, "wf_close_wave", {"wave_id": wave_id, "mode": "dry_run"})
            counts[how] = {k: v - before[k] for k, v in calls().items()}
        out["calls"] = counts
        # A failure after the extension install clears the installed override deltas.
        from mcp.server.fastmcp import FastMCP
        with mock.patch.object(impl, "_install_served_names", boom):
            try:
                impl.register_mcp_surface(FastMCP("late_failure"), runner._get_handler)
                out["late_failure"] = "served"
            except RuntimeError:
                out["late_failure"] = "raised"
        out["deltas_after_late_failure"] = sorted(impl._EXTENSION_OVERRIDE_DELTAS)
        handler.close()

    elif MODE == "helpers":
        # Wave 1zls8 (1zltx AC-2, AC-3, AC-5, AC-10, AC-11): declared helper
        # modules, the public lifecycle helpers end to end, and reload.
        DECL.write_text(DECL_ORIG + HELPER_DECL)
        write_module("acme_shared", HELPER)
        write_module("acme_extra", HELPER_EXTRA)
        write_module("acme_contract", CONTRACT)
        load_server(); runner = load_thin_runner()
        mcp = runner.build_server(root)
        impl = runner.server_impl
        from unittest import mock
        from record_layout_support import patch_layout
        from test_archive_root import ARCHIVE_REL, SECOND, _module_copies, _write_archive
        sha = lambda name: hashlib.sha256((SCRATCH / f"{name}.py").read_bytes()).hexdigest()
        marked = lambda name: getattr(sys.modules.get(name), "__wf_extension__", None)
        out["names"] = sorted(n for n in table(mcp) if n.startswith("acme_"))
        out["register_calls"] = list(sys.modules["acme_shared"].REGISTER_CALLS)
        out["marked"] = {n: marked(n) for n in ("acme_shared", "acme_extra", "acme_contract")}
        info = impl.wf_server_info_response(root)["data"]["extensions"]
        out["helper_provenance"] = info["helper_modules"]
        out["declared_helpers"] = info["declaration"]["helper_modules"]
        out["helper_sha"] = {n: sha(n) for n in ("acme_shared", "acme_extra")}
        created = impl.wf_create_wave_response(root, "helped", mode="create")
        wave_id = created["data"]["wave_id"]
        refreshes = []
        with mock.patch.object(impl, "_trigger_background_index_refresh_for_paths",
                               lambda r, paths: refreshes.append([Path(x).name for x in paths]) or {"project": True}), \
                mock.patch.object(impl, "_run_post_write_lint", lambda r: {"passed": True, "stub": True}):
            out["touch_create"] = ccall(mcp, "acme_touch", {"wave_id": wave_id, "mode": "create"})
            out["touch_dry_run"] = ccall(mcp, "acme_touch", {"wave_id": wave_id})
        out["refreshes"] = refreshes
        out["record_filename"] = impl._vocab.RECORD_FILENAME
        # Archived and record-layout refusals in the core shape.
        _write_archive(root)
        rps, vps = _module_copies(impl)
        with patch_layout(modules=rps, archive_root=ARCHIVE_REL), contextlib.ExitStack() as stack:
            for vp in vps:
                stack.enter_context(mock.patch.object(vp, "ARCHIVE_PROFILE", SECOND))
            out["touch_archived"] = ccall(mcp, "acme_touch", {"wave_id": "1a000"})
            out["core_archived"] = ccall(mcp, "wf_pause_wave", {"wave_id": "1a000", "mode": "create"})
        with patch_layout(modules=rps, waves_root="../x"):
            out["touch_invalid"] = ccall(mcp, "acme_touch", {"wave_id": wave_id})
            out["core_invalid"] = ccall(mcp, "wf_pause_wave", {"wave_id": wave_id, "mode": "dry_run"})
        # AC-5: an edited helper is served, with its new hash, after reload.
        write_module("acme_shared", HELPER.replace('VERSION = "h1"', 'VERSION = "h2"'))
        result = runner.perform_mcp_reload()
        out["edit_reload_status"] = result["status"]
        impl = runner.server_impl
        out["edit_touch"] = ccall(mcp, "acme_touch", {"wave_id": wave_id})["data"].get("helper")
        out["edit_provenance"] = impl.wf_server_info_response(root)["data"]["extensions"]["helper_modules"]
        out["edit_sha"] = sha("acme_shared")
        # AC-2: the wrappers resolve and stay late-bound after the reload.
        out["reload_helpers"] = {n: callable(getattr(impl, n, None)) for n in impl.EXTENSION_PUBLIC_HELPERS}
        with mock.patch.object(impl, "_find_wave_md_detailed", lambda *a, **k: ("patched", None, [])):
            out["reload_late_bound"] = impl.find_wave_record(root, wave_id)[0]
        # AC-10: a dropped helper is evicted on reload.
        DECL.write_text(DECL_ORIG + HELPER_DECL.replace('("acme_shared", "acme_extra")', '("acme_shared",)'))
        result = runner.perform_mcp_reload()
        out["drop_reload_status"] = result["status"]
        out["drop_in_modules"] = {n: n in sys.modules for n in ("acme_shared", "acme_extra", "acme_contract")}
        # AC-11: a helper edited to import a later-declared helper is refused
        # on reload, and fixing the order recovers without a restart.
        DECL.write_text(DECL_ORIG + HELPER_DECL)
        write_module("acme_shared", "import acme_extra\n" + HELPER)
        result = runner.perform_mcp_reload()
        out["order_reload_status"] = result["status"]
        out["order_reload_text"] = json.dumps(result)[:4000]
        out["order_served"] = sorted(n for n in table(mcp) if n.startswith("acme_"))
        out["order_in_modules"] = {n: n in sys.modules for n in ("acme_shared", "acme_extra", "acme_contract")}
        DECL.write_text(DECL_ORIG + HELPER_DECL.replace('("acme_shared", "acme_extra")', '("acme_extra", "acme_shared")'))
        result = runner.perform_mcp_reload()
        out["fixed_reload_status"] = result["status"]
        out["fixed_reload_text"] = json.dumps(result)[:4000]
        out["fixed_names"] = sorted(n for n in table(mcp) if n.startswith("acme_"))
        out["fixed_marked"] = {n: marked(n) for n in ("acme_shared", "acme_extra", "acme_contract")}
        # AC-10: an emptied declaration evicts every extension and helper module.
        DECL.write_text(DECL_ORIG)
        result = runner.perform_mcp_reload()
        out["empty_reload_status"] = result["status"]
        out["empty_in_modules"] = {n: n in sys.modules for n in ("acme_shared", "acme_extra", "acme_contract")}
        out["empty_provenance"] = runner.server_impl.wf_server_info_response(root)["data"]["extensions"]["helper_modules"]
        runner._get_handler().close()

    elif MODE == "render":
        # Wave 1zoju (1zodw): an exception escaping any served callable is
        # rendered as a path-free error envelope by the final render pass.
        import errno, copy as copy_module
        from unittest import mock
        RENDER_DECL = (
            "\nEXTENSION_MODULES = ('fork_render',)\n"
            "EXTENSION_TOOL_PREFIXES = ('fork_',)\n"
            "EXTENSION_TOOL_TIERS = {'fork_boom': 'read'}\n"
            "EXTENSION_OVERRIDES = {'fork_render': ('wf_current_wave',)}\n"
            "EXTENSION_REPLACEMENTS = {'fork_render': {'wf_help': {'alias_for_core': 'fork_help_core', 'tier': 'write'}}}\n"
            "EXTENSION_TOOL_ALIASES = {'fork_plain': 'fork_boom', 'fork_mapped': 'fork_boom'}\n"
            "EXTENSION_TOOL_PARAMETERS = {'fork_mapped': {'rename': {'words': 'text'}, 'fixed': {'count': 2}}}\n"
        )
        RENDER_MODULE = (
            "import server_impl\n"
            "RAISE = {'what': None}\n"
            "def register(mcp, get_handler):\n"
            "    @mcp.tool()\n"
            "    def fork_boom(text: str = '', count: int = 1, **kwargs):\n"
            "        bad = server_impl.ensure_no_extra_args('fork_boom', kwargs)\n"
            "        if bad is not None:\n"
            "            return bad\n"
            "        if RAISE['what'] is not None:\n"
            "            raise RAISE['what']\n"
            "        return {'status': 'ok', 'data': {'text': text, 'count': count}}\n"
            "    @mcp.tool()\n"
            "    def wf_current_wave(**kwargs):\n"
            "        bad = server_impl.ensure_no_extra_args('wf_current_wave', kwargs)\n"
            "        if bad is not None:\n"
            "            return bad\n"
            "        if RAISE['what'] is not None:\n"
            "            raise RAISE['what']\n"
            "        return {'status': 'ok', 'data': {'overridden': True}}\n"
            "    @mcp.tool()\n"
            "    def wf_help(topic: str = '', **kwargs):\n"
            "        bad = server_impl.ensure_no_extra_args('wf_help', kwargs)\n"
            "        if bad is not None:\n"
            "            return bad\n"
            "        return {'status': 'ok', 'data': {'fork_help': topic}}\n"
        )
        DECL.write_text(DECL_ORIG + RENDER_DECL)
        write_module("fork_render", RENDER_MODULE)
        load_server(); runner = load_thin_runner()
        mcp = runner.build_server(root)
        impl = runner.server_impl
        fork = sys.modules["fork_render"]
        # The served root, as the handler holds it (the filename an OSError
        # names is built from it, as server code builds its paths).
        hroot = Path(runner._get_handler().root)
        roots = {str(root), str(root.resolve()), str(hroot)}

        def observe(fn):
            try:
                result = fn()
            except BaseException as exc:
                return {"escaped": type(exc).__name__}
            text = json.dumps(result)
            return {"status": result.get("status"), "isError": result.get("isError"),
                    "tool": (result.get("data") or {}).get("tool"),
                    "diagnostics": [[d.get("code"), d.get("message")] for d in result.get("diagnostics") or []],
                    "leaks_root": any(r in text for r in roots)}

        out["markers"] = {name: markers(mcp, name) for name in table(mcp)}
        out["coroutines"] = sorted(name for name in table(mcp) if inspect.iscoroutinefunction(table(mcp)[name].fn))
        out["alias_shares_fn"] = table(mcp)["fork_plain"].fn is table(mcp)["fork_boom"].fn
        cases = {}
        fork.RAISE["what"] = OSError(errno.EACCES, "Permission denied", str(hroot / "docs" / "x.md"))
        cases["extension_client"] = observe(lambda: ccall(mcp, "fork_boom"))
        cases["extension"] = observe(lambda: call(mcp, "fork_boom"))
        fork.RAISE["what"] = RuntimeError(f"cannot open {root}/lock")
        cases["plain_alias"] = observe(lambda: call(mcp, "fork_plain"))
        cases["override"] = observe(lambda: call(mcp, "wf_current_wave"))
        fork.RAISE["what"] = None
        with mock.patch.object(impl, "wf_help_response", side_effect=ValueError("bad goal")):
            cases["alias_for_core"] = observe(lambda: call(mcp, "fork_help_core"))
        with mock.patch.object(impl, "_rewrite_served_names", side_effect=KeyError("rewrite")):
            cases["mapped_rewrite"] = observe(lambda: call(mcp, "fork_mapped", words="hi", extra=1))
        with mock.patch.object(copy_module, "deepcopy", side_effect=TypeError("deepcopy")):
            cases["mapped_deepcopy"] = observe(lambda: call(mcp, "fork_mapped", words="hi"))
        with mock.patch.object(impl, "_rename_response_keys", side_effect=LookupError("rename")):
            cases["mapped_rename"] = observe(lambda: call(mcp, "fork_mapped", words="hi"))
        cases["mapped_ok"] = observe(lambda: call(mcp, "fork_mapped", words="hi"))
        # AC-4: an inner wrapper (the upgrade-publication guard, outside the
        # body and every other core wrapper) raising is rendered too.
        with mock.patch.object(impl.publication_control, "publication_block_reason",
                               side_effect=RuntimeError(f"guard failed at {root}")):
            cases["inner_guard"] = observe(lambda: call(mcp, "wf_add_change", wave_id="x", change_id="y"))
        # AC-5: an interrupt propagates unchanged.
        fork.RAISE["what"] = KeyboardInterrupt()
        cases["interrupt"] = observe(lambda: call(mcp, "fork_boom"))
        fork.RAISE["what"] = None
        # Wave 1zqe4 (1zqe3) AC-1: the coroutine runner tool, through FastMCP's
        # client path, renders a reload exception path-free instead of raising.
        reload_error = OSError(errno.EACCES, "Permission denied", str(hroot / "docs" / "x.md"))
        with mock.patch.object(runner, "perform_mcp_reload", side_effect=reload_error):
            cases["reload_client"] = observe(lambda: ccall(mcp, "wf_reload_mcp"))
            out["reload_escape_text_leaks_root"] = False
            try:
                ccall(mcp, "wf_reload_mcp")
            except BaseException as exc:
                out["reload_escape_text_leaks_root"] = any(r in str(exc) for r in roots)
        out["cases"] = cases
        # AC-4: rendered once at build, kept by identity across a real reload,
        # and a second application of the pass changes no entry.
        reload_fn = table(mcp)["wf_reload_mcp"].fn
        reload_result = runner.perform_mcp_reload()
        out["real_reload_status"] = reload_result["status"]
        out["reload_same_fn"] = table(mcp)["wf_reload_mcp"].fn is reload_fn
        out["reload_markers_after_reload"] = markers(mcp, "wf_reload_mcp")
        before = {name: entry.fn for name, entry in table(mcp).items()}
        impl = runner.server_impl
        impl.mcp_tool_registry.apply_middleware(mcp, runner._get_handler, impl._RENDER_PASS)
        out["second_pass_unchanged"] = set(table(mcp)) == set(before) and all(
            table(mcp)[name].fn is fn for name, fn in before.items())
        runner._get_handler().close()

    elif MODE in ("stale", "stale_declared"):
        # Wave 1zoju (1zojt): an undeclared importer of a declared helper keeps
        # the old helper after a reload, and the post-install scan reports it.
        import gc, types, weakref
        from unittest import mock
        STALE_H = (
            "VERSION = 'h1'\n"
            "def f():\n    return VERSION\n"
            "class C:\n    pass\n"
            "class Outer:\n    class Nested:\n        pass\n"
            "def factory():\n    def inner():\n        return 1\n    return inner\n"
            "inst = C()\n"
            "DROPPED = object()\n"
            "LIMIT = 1000\n"
        )
        STALE_U = (
            "import acme_h\n"
            "from acme_h import f, C, inst, DROPPED, LIMIT\n"
            "import acme_lazy\n"
            "import acme_pkg.sub\n"
            "holder = [acme_h]\n"
            "made = acme_h.factory()\n"
            "Nested = acme_h.Outer.Nested\n"
            "mine = acme_h.C()\n"
            "helper_spec = acme_h.__spec__\n"
        )
        STALE_E = (
            "import server_impl\n"
            "import acme_u\n"
            "def register(mcp, get_handler):\n"
            "    @mcp.tool()\n"
            "    def acme_stale(**kwargs):\n"
            "        return server_impl.make_response('ok', {'value': acme_u.f()})\n"
        )
        helpers = '("acme_h", "acme_u")' if MODE == "stale_declared" else '("acme_h",)'
        STALE_DECL = (
            f"\nEXTENSION_HELPER_MODULES = {helpers}\n"
            "EXTENSION_MODULES = ('acme_e',)\n"
            "EXTENSION_TOOL_PREFIXES = ('acme_',)\n"
            "EXTENSION_TOOL_TIERS = {'acme_stale': 'read'}\n"
        )
        DECL.write_text(DECL_ORIG + STALE_DECL)
        write_module("acme_h", STALE_H)
        write_module("acme_u", STALE_U)
        write_module("acme_e", STALE_E)
        write_module("acme_lazy", "CALLS = []\ndef __getattr__(name):\n    CALLS.append(name)\n    raise AttributeError(name)\n")
        (SCRATCH / "acme_pkg").mkdir()
        (SCRATCH / "acme_pkg" / "__init__.py").write_text("")
        (SCRATCH / "acme_pkg" / "sub.py").write_text("from acme_h import f\n")
        load_server(); runner = load_thin_runner()
        mcp = runner.build_server(root)
        impl = runner.server_impl
        first = impl.wf_server_info_response(root)
        out["first_refs"] = first["data"]["extensions"]["stale_helper_references"]
        out["first_codes"] = [d["code"] for d in first.get("diagnostics") or []]
        old_h = weakref.ref(sys.modules["acme_h"])

        class Proxy:
            touched = []
            def __getattribute__(self, name):
                Proxy.touched.append(name)
                raise AttributeError(name)

        class Hostile(str):
            def startswith(self, *args, **kwargs):
                raise RuntimeError("hostile path text")

        broken = types.ModuleType("acme_broken")
        broken.__file__ = Hostile(str(SCRATCH / "acme_broken.py"))
        sys.modules["acme_proxy"] = Proxy()
        sys.modules["acme_broken"] = broken
        # Scanned after the failing module, so one failure must not end the scan.
        for name in ("acme_pkg.sub", "acme_u"):
            sys.modules[name] = sys.modules.pop(name)
        # The new helper drops DROPPED: a name it no longer binds is not stale.
        # (A declared importer is re-executed, so there it must stay bound.)
        # Repair F2: the new helper also gains a docstring and bumps an int
        # constant; cached immutables are shared, so neither is reported.
        if MODE == "stale":
            write_module("acme_h", '"""The edited helper."""\n'
                         + STALE_H.replace("DROPPED = object()\n", "").replace("LIMIT = 1000", "LIMIT = 2000"))
        result = runner.perform_mcp_reload()
        out["reload_status"] = result["status"]
        impl = runner.server_impl
        info = impl.wf_server_info_response(root)
        out["refs"] = info["data"]["extensions"]["stale_helper_references"]
        out["diagnostics"] = [{k: d.get(k) for k in ("code", "message", "advisory")} for d in info.get("diagnostics") or []]
        out["retained_after_scan"] = len(impl._EXTENSION_RETAINED_MODULES)
        out["lazy_calls"] = list(sys.modules["acme_lazy"].CALLS)
        out["proxy_touched"] = list(Proxy.touched)
        out["served_value"] = ccall(mcp, "acme_stale").get("data")
        del sys.modules["acme_proxy"], sys.modules["acme_broken"], broken
        # The importer drops its references; the old helper is then freed,
        # because the server retained it only until the scan finished.
        u = sys.modules["acme_u"]
        for name in ("acme_h", "f", "C", "inst", "DROPPED", "LIMIT", "holder", "made", "Nested", "mine", "helper_spec"):
            vars(u).pop(name, None)
        vars(sys.modules["acme_pkg.sub"]).pop("f", None)
        del u
        gc.collect()
        out["old_h_freed"] = old_h() is None
        # A failed install after eviction releases the evicted modules too:
        # a forced tool-name prefix violation, and an install that raises.
        from mcp.server.fastmcp import FastMCP
        failed = {}
        for label in ("prefix", "install"):
            u = sys.modules["acme_u"]
            vars(u)["acme_h"] = sys.modules["acme_h"]
            current = weakref.ref(sys.modules["acme_h"])
            target, patch = (("first_party_tool_names_violating_prefix", lambda names: ["acme_forced"])
                             if label == "prefix" else
                             ("_install_declared_extension_tools", mock.Mock(side_effect=RuntimeError("forced"))))
            with mock.patch.object(impl, target, patch):
                try:
                    impl.register_mcp_surface(FastMCP("fail-" + label), runner._get_handler)
                    raised = None
                except BaseException as exc:
                    raised = type(exc).__name__
            retained = len(impl._EXTENSION_RETAINED_MODULES)
            vars(u).pop("acme_h", None)
            del u
            gc.collect()
            failed[label] = {"raised": raised, "retained": retained, "freed": current() is None}
            # Restore a served state for the next case.
            result = runner.perform_mcp_reload()
            impl = runner.server_impl
            failed[label]["recovered"] = result["status"]
        out["failed"] = failed
        runner._get_handler().close()

    elif MODE == "caseok":
        # Wave 1zls8 (1zltx AC-6, Requirement 10): run with PYTHONCASEOK=1. A
        # declared name whose case differs from its file is refused on every
        # platform, for a helper and for an extension module.
        import importlib.machinery, os
        from mcp.server.fastmcp import FastMCP
        load_server(); runner = load_thin_runner()
        runner.build_server(root)
        impl = runner.server_impl
        ext = sys.modules["mcp_tool_extensions"]
        write_module("acme_case_helper", "VALUE = 1\n")
        write_module("acme_case_tools", (
            "import server_impl\n"
            "def register(mcp, get_handler):\n"
            "    @mcp.tool()\n"
            "    def acme_case(**kwargs):\n"
            "        return {'status': 'ok'}\n"
        ))
        scripts = str(Path(impl.SCRIPTS_DIR).resolve())
        out["caseok"] = os.environ.get("PYTHONCASEOK")
        out["find_spec_resolves_miscased"] = importlib.machinery.PathFinder.find_spec("Acme_Case_Helper", [scripts]) is not None
        results = {}
        for label, attrs in (
            ("helper", dict(EXTENSION_HELPER_MODULES=("Acme_Case_Helper",))),
            ("module", dict(EXTENSION_MODULES=("Acme_Case_Tools",), EXTENSION_TOOL_PREFIXES=("acme_",),
                            EXTENSION_TOOL_TIERS={"acme_case": "read"})),
            ("helper_exact", dict(EXTENSION_HELPER_MODULES=("acme_case_helper",))),
        ):
            for key, value in attrs.items():
                setattr(ext, key, value)
            mcp = FastMCP("case")
            try:
                impl.register_mcp_surface(mcp, runner._get_handler)
                results[label] = {"raised": None, "served": sorted(table(mcp)),
                                  "helpers": [h["module"] for h in (impl._EXTENSION_PROVENANCE or {}).get("helper_modules", [])]}
            except BaseException as exc:
                results[label] = {"raised": type(exc).__name__, "message": str(exc), "served": sorted(table(mcp))}
            for key in attrs:
                setattr(ext, key, type(getattr(ext, key))())
        out["cases"] = results
        runner._get_handler().close()

print(json.dumps(out))
'''


def _run(mode: str, env: dict | None = None) -> dict:
    with tempfile.TemporaryDirectory() as temp:
        scratch = Path(temp) / "scripts"
        shutil.copytree(SCRIPTS, scratch, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        # Every mode starts from the shipped empty declaration, whatever this
        # tree declares (change 1zim4); a mode appends its own declaration.
        with (scratch / "mcp_tool_extensions.py").open("a", encoding="utf-8") as decl:
            decl.write(base_declaration_source())
        result = subprocess.run(
            [sys.executable, "-B", "-c", _DRIVER, mode],
            cwd=scratch,
            env=dict(os.environ, PYTHONPATH=str(scratch), PYTHONDONTWRITEBYTECODE="1", **(env or {})),
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            raise AssertionError(f"{mode} driver failed:\n{result.stderr[-6000:]}")
        return json.loads(result.stdout.strip().splitlines()[-1])


class StockSurfaceTests(unittest.TestCase):
    """AC-1: the shipped empty declaration changes nothing but adds an empty field."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run("stock")

    def test_empty_declaration_reports_empty_extensions(self):
        ext = self.out["extensions"]
        self.assertEqual(ext["modules"], [])
        self.assertEqual(ext["declaration"]["prefixes"], [])
        self.assertEqual(ext["declaration"]["tiers"], {})
        self.assertTrue(ext["declaration"]["sha256"])

    def test_declaration_module_ships_empty(self):
        # The module ships the empty declaration; a distribution that edits it
        # marks its own profile asset active (changes 1zim4, 1zima), and a run
        # mode names its asset in WAVEFOUNDRY_TEST_PROFILE, so the loaded
        # declaration is exactly the expected profile's and any other change
        # fails loudly.
        from declaration_support import (ProfileInvalid, base_declaration, declaration_profile_mismatch,
                                         expected_profile)
        try:
            expected = expected_profile()
        except ProfileInvalid as exc:
            self.fail(str(exc))
        problem = declaration_profile_mismatch(expected)
        self.assertIsNone(problem, problem)
        import mcp_tool_extensions
        with base_declaration():
            self.assertFalse(mcp_tool_extensions.declared())
            self.assertEqual(mcp_tool_extensions.served_name_map(), {})

    def test_empty_declaration_reports_no_served_names(self):
        # Wave 1z8oz: the new provenance fields exist and are empty.
        ext = self.out["extensions"]
        # Wave 1zoju (1zojt AC-5): the stale-reference list is always present.
        self.assertEqual(ext["stale_helper_references"], [])
        self.assertEqual(ext["aliases"], {})
        self.assertEqual(ext["hidden"], [])
        self.assertEqual(ext["replacements"], [])
        self.assertEqual(ext["parameters"], {})
        self.assertEqual(ext["served_names"], {})


class AliasServingTests(unittest.TestCase):
    """Wave 1z8oz AC-1 to AC-3, AC-5 to AC-7: an aliases-only declaration."""

    @classmethod
    def setUpClass(cls):
        cls.stock = _run("stock")
        cls.out = _run("alias")

    def test_aliases_only_declaration_is_served_with_roster_parity(self):
        self.assertEqual(self.out["parity_defects"], [])
        self.assertEqual(self.out["registry_vs_tiers"], [])
        self.assertEqual(self.out["tier_mismatches"], [])
        self.assertEqual(self.out["served_vs_tiers"], [])

    def test_alias_is_the_canonical_wrapped_tool(self):
        self.assertTrue(self.out["alias_shares_fn"])
        self.assertEqual(self.out["markers"]["fork_close_container"], self.out["markers"]["wf_close_wave"])
        # The canonical markers are the stock chain plus the hint rewrite,
        # then the final render pass (wave 1zoju, 1zodw).
        self.assertEqual(self.stock["markers"]["wf_close_wave"][-1], "render")
        self.assertEqual(self.out["markers"]["wf_close_wave"],
                         self.stock["markers"]["wf_close_wave"][:-1] + ["rewrite", "render"])

    def test_alias_takes_the_canonical_lock_and_its_hints_name_served_tools(self):
        busy = self.out["busy"]
        self.assertEqual(busy["codes"], ["error", "lifecycle_mutation_locked"])
        self.assertTrue(busy["busy"])
        self.assertEqual(busy["next_tools"], ["fork_close_container", "fork_current"])
        self.assertEqual(busy["recovery_tools"], [["fork_close_container", "fork_current"]])
        self.assertTrue(busy["usage"].startswith("retry fork_close_container "), busy["usage"])
        self.assertTrue(busy["recovery_usage"][0].startswith("fork_close_container(...)"), busy["recovery_usage"])

    def test_alias_takes_the_canonical_publication_guard(self):
        self.assertEqual(self.out["guarded"], ["error", "upgrade_in_progress"])

    def test_cost_accounting_follows_the_canonical_name(self):
        # wf_close_wave is cost-exempt, wf_current_wave is not; the record
        # carries the canonical name. The exempt call reaches the handler.
        self.assertEqual(self.out["cost_after_costed_alias"], ["wf_current_wave"])
        self.assertEqual(self.out["exempt_alias_call"], ["error", "wave_not_found"])  # the handler answered
        self.assertEqual(self.out["cost_after_exempt_alias"], ["wf_current_wave"])
        self.assertNotIn("cost", self.out["markers"]["fork_close_container"])

    def test_hidden_name_is_not_listed_or_callable_while_its_alias_works(self):
        self.assertFalse(self.out["listed_hidden"])
        self.assertTrue(self.out["listed_alias"])
        self.assertIn("Unknown tool", self.out["hidden_call"])
        self.assertEqual(self.out["alias_call"], "ok")

    def test_allowlist_carries_aliases_at_their_tier_and_omits_hidden_names(self):
        self.assertEqual(self.out["tiers"]["fork_current"], "read")
        self.assertEqual(self.out["tiers"]["fork_close_container"], "write")
        self.assertIsNone(self.out["tiers"]["wf_current_wave"])  # hidden: no roster tier
        self.assertIn("fork_current", self.out["read_rules"])
        self.assertNotIn("wf_current_wave", self.out["read_rules"])
        self.assertIn("fork_close_container", self.out["write_rules"])
        self.assertNotIn("fork_close_container", self.out["read_rules"])

    def test_provenance_publishes_aliases_hidden_names_and_the_first_declared_map(self):
        ext = self.out["extensions"]
        self.assertEqual(ext["hidden"], ["wf_current_wave"])
        self.assertEqual(ext["aliases"]["fork_current_again"], "wf_current_wave")
        self.assertEqual(ext["served_names"], {
            "wf_close_wave": "fork_close_container",
            "wf_add_change": "fork_add_change",
            "wf_current_wave": "fork_current",
        })
        self.assertEqual(ext["replacements"], [])

    def test_reload_rebuilds_served_names_and_fails_closed(self):
        self.assertEqual(self.out["reload_status"], "ok")
        self.assertEqual(self.out["reload_names"], ["fork_add_change", "fork_close_container", "fork_current", "fork_current_again"])
        self.assertFalse(self.out["reload_hidden"])
        self.assertTrue(self.out["reload_shares_fn"])
        self.assertIn("register_surface_failed", self.out["failed_reload_text"])
        self.assertIn("which is not a served tool", self.out["failed_reload_text"])
        self.assertEqual(self.out["served_after_failure"], ["wf_reload_mcp"])


class ReplacementServingTests(unittest.TestCase):
    """Wave 1z8oz AC-4 and AC-7: core names reused with incompatible handlers."""

    @classmethod
    def setUpClass(cls):
        cls.stock = _run("stock")
        cls.out = _run("replace")

    def test_roster_parity_with_replacements(self):
        self.assertEqual(self.out["parity_defects"], [])
        self.assertEqual(self.out["registry_vs_tiers"], [])
        self.assertEqual(self.out["tier_mismatches"], [])
        self.assertEqual(self.out["served_vs_tiers"], [])

    def test_replacing_handler_is_served_under_the_core_name_with_stock_wrappers(self):
        self.assertEqual(self.out["replaced_call"]["data"], {"closed_item": "task-7"})
        for name in ("wf_review_event", "wf_current_wave"):
            self.assertEqual(self.out["markers"][name], self.stock["markers"][name], name)
        # wf_close_wave is cost-exempt because its core handler records its own
        # cost; the replacing handler gets the cost wrapper instead (DEL-1).
        self.assertNotIn("cost", self.stock["markers"]["wf_close_wave"])
        self.assertEqual(self.out["markers"]["wf_close_wave"], ["cost"] + self.stock["markers"]["wf_close_wave"])
        self.assertIn("lock", self.out["markers"]["wf_close_wave"])

    def test_replacing_handler_on_a_cost_exempt_name_records_its_debit(self):
        self.assertEqual(self.out["cost_after_exempt_replacement"], ["wf_close_wave"])

    def test_replacing_handler_keeps_its_own_hints(self):
        self.assertEqual(self.out["replaced_call"]["next_tools"], ["wf_close_wave"])
        self.assertEqual(self.out["replaced_call"]["usage"], "wf_close_wave(item=...)")
        busy = self.out["replaced_busy"]
        self.assertEqual(busy["codes"], ["error", "lifecycle_mutation_locked"])
        self.assertEqual(busy["recovery_tools"], [["wf_close_wave", "wf_current_wave"]])

    def test_core_behaviour_has_stock_wrappers_plus_rewrite(self):
        for core, alias in (("wf_close_wave", "fork_close_container"), ("wf_review_event", "fork_review_event_core"),
                            ("wf_help", "fork_help_core"), ("memory_validate", "fork_memory_validate_core"),
                            ("wf_current_wave", "fork_current_core")):
            # Wave 1zoju (1zodw): the stock chain ends in the final render pass.
            self.assertEqual(self.out["markers"][alias], self.stock["markers"][core][:-1] + ["rewrite", "render"], alias)

    def test_core_behaviour_lock_busy_names_alias_for_core(self):
        busy = self.out["core_busy"]
        self.assertEqual(busy["codes"], ["error", "lifecycle_mutation_locked"])
        self.assertEqual(busy["next_tools"], ["fork_close_container", "fork_current_core"])
        self.assertEqual(busy["recovery_tools"], [["fork_close_container", "fork_current_core"]])

    def test_core_tools_that_are_not_replaced_name_alias_for_core(self):
        busy = self.out["other_core_busy"]
        self.assertEqual(busy["codes"], ["error", "lifecycle_mutation_locked"])
        self.assertEqual(busy["next_tools"], ["wf_add_change", "fork_current_core"])
        self.assertEqual(busy["recovery_tools"], [["wf_add_change", "fork_current_core"]])

    def test_core_behaviour_is_upgrade_guarded(self):
        self.assertEqual(self.out["core_close_guarded"], ["error", "upgrade_in_progress"])

    def test_extractors_run_for_the_core_behaviour_only(self):
        self.assertEqual(self.out["replaced_review"], {"note": "n"})
        self.assertEqual(self.out["extractor_after_replaced"], 0)
        self.assertEqual(self.out["cost_after_replaced"], [["wf_review_event", 0]])
        self.assertEqual(self.out["extractor_after_core"], 1)

    def test_write_replacement_of_a_read_tool_is_guarded_and_write_tiered(self):
        self.assertIn("guard", self.out["markers"]["wf_help"])
        self.assertNotIn("guard", self.stock["markers"]["wf_help"])
        self.assertEqual(self.out["write_replacement_guarded"], ["error", "upgrade_in_progress"])
        self.assertEqual(self.out["tiers"]["wf_help"], "write")
        self.assertEqual(self.out["tiers"]["fork_help_core"], "read")
        self.assertNotIn("wf_help", self.out["read_rules"])
        self.assertIn("wf_help", self.out["write_rules"])
        self.assertIn("fork_help_core", self.out["read_rules"])
        # The core behaviour stays read and unguarded.
        self.assertNotIn("guard", self.out["markers"]["fork_help_core"])
        self.assertEqual(self.out["read_core_unguarded"][0], "ok")

    def test_memory_validate_core_keeps_its_recovery_exemption(self):
        self.assertIn("upgrade_in_progress", self.out["memory_core_extracting"])
        self.assertNotIn("upgrade_in_progress", self.out["memory_core_recovery"])

    def test_replacing_handler_of_a_registered_publisher_keeps_its_guard(self):
        # memory_validate is a registered publisher: its replacing handler keeps
        # the block guard with the memory_recovery exemption, not the checkpoint.
        self.assertIn("upgrade_in_progress", self.out["memory_replacing_extracting"])
        self.assertEqual(self.out["memory_replacing_recovery"], ["ok"])

    def test_reload_rebuilds_replacements(self):
        self.assertEqual(self.out["reload_status"], "ok")
        self.assertEqual(self.out["reload_replaced_call"], {"closed_item": "task-9"})
        self.assertEqual(self.out["reload_core_markers"], self.out["markers"]["fork_close_container"])

    def test_provenance_lists_replacements_and_the_served_map(self):
        ext = self.out["extensions"]
        self.assertEqual(ext["replacements"], [
            {"core_name": "memory_validate", "module": "fork_tools", "alias_for_core": "fork_memory_validate_core", "tier": "write"},
            {"core_name": "wf_close_wave", "module": "fork_tools", "alias_for_core": "fork_close_container", "tier": "write"},
            {"core_name": "wf_current_wave", "module": "fork_tools", "alias_for_core": "fork_current_core", "tier": "read"},
            {"core_name": "wf_help", "module": "fork_tools", "alias_for_core": "fork_help_core", "tier": "write"},
            {"core_name": "wf_review_event", "module": "fork_tools", "alias_for_core": "fork_review_event_core", "tier": "write"},
        ])
        self.assertEqual(ext["served_names"]["wf_close_wave"], "fork_close_container")
        (module,) = ext["modules"]
        self.assertEqual(module["replacements"], ["memory_validate", "wf_close_wave", "wf_current_wave", "wf_help", "wf_review_event"])


def _renamed_schema(canonical: dict, rename: dict, fixed: dict) -> dict:
    """The canonical (title-normalized) schema with fields renamed and fixed ones removed."""
    to_alias = {c: a for a, c in rename.items()}
    props = {to_alias.get(k, k): v for k, v in canonical["properties"].items() if k not in fixed}
    required = [to_alias.get(k, k) for k in canonical.get("required", []) if k not in fixed]
    return {**canonical, "properties": props, "required": required}


# Wave 1zime (1zimm): the declared description, served byte for byte; the
# surrounding whitespace proves nothing strips or rewrites it.
SAY_DESCRIPTION = "  Echo the given words back. Provide words; count repeats them.\n"


class ParameterMappedAliasTests(unittest.TestCase):
    """Wave 1zim3 AC-1, AC-2 and AC-4 through the real build_server and FastMCP call_tool."""

    @classmethod
    def setUpClass(cls):
        cls.stock = _run("stock")
        cls.out = _run("params")

    def test_alias_schema_is_the_renamed_canonical_schema(self):
        schemas = self.out["schemas"]
        swap = {"set_id": "wave_id", "wave_id": "change_id"}
        self.assertEqual(schemas["fork_add_wave"], _renamed_schema(schemas["wf_add_change"], swap, {}))
        self.assertEqual(schemas["fork_add_wave_now"], _renamed_schema(schemas["wf_add_change"], swap, {"mode": "create"}))
        self.assertEqual(schemas["fork_review_prepare"], _renamed_schema(schemas["wf_review_wave"], {}, {"phase": "prepare"}))
        self.assertEqual(schemas["fork_say"], _renamed_schema(schemas["fork_echo"], {"words": "text"}, {}))
        # Annotated metadata and descriptions are carried, not re-derived.
        self.assertEqual(schemas["fork_say"]["properties"]["words"], {"description": "Text to echo.", "minLength": 2, "type": "string"})
        self.assertEqual(schemas["fork_add_wave"]["required"], ["set_id", "wave_id"])
        self.assertIs(schemas["fork_add_wave"]["additionalProperties"], False)

    def test_alias_keeps_canonical_description_annotations_and_wrappers(self):
        self.assertEqual(self.out["descriptions_equal"], {"fork_add_wave": True, "fork_review_prepare": True})
        self.assertEqual(self.out["annotations_equal"], {"fork_add_wave": True, "fork_review_prepare": True})
        self.assertTrue(self.out["wraps_canonical"])
        for alias, canonical in (("fork_add_wave", "wf_add_change"), ("fork_add_wave_now", "wf_add_change"),
                                 ("fork_review_prepare", "wf_review_wave")):
            self.assertEqual(self.out["markers"][alias], self.out["markers"][canonical], alias)

    def test_calls_reach_the_canonical_body_with_translated_arguments(self):
        swap, pinned = self.out["add_calls"]
        self.assertEqual(swap["args"], ["1abcd", "1abce-feat x"])
        self.assertEqual(swap["kwargs"], {"mode": "dry_run"})
        self.assertEqual(pinned["args"], ["1abcd", "1abce-feat x"])
        self.assertEqual(pinned["kwargs"], {"mode": "create"})
        (review,) = self.out["review_calls"]
        self.assertEqual(review["args"], ["1abcd"])
        self.assertEqual(review["kwargs"], {"phase": "prepare"})
        # Wave 1zime (1zimm): the echoed renamed parameter carries the alias name.
        self.assertEqual(self.out["say_call"], {"words": "hello", "count": 3, "ratio_type": "float", "tags": None})
        self.assertIn("String should have at least 2 characters", self.out["say_short"])

    def test_a_pin_is_forwarded_as_its_validated_value(self):
        # The declared int 1 for a float field reaches the body as the validated 1.0.
        first, second = self.out["whole_calls"]
        self.assertEqual(first["ratio_type"], "float")
        self.assertEqual(first["tags"], ["a", "seen"])

    def test_a_mutable_pin_mutated_by_the_body_does_not_leak(self):
        self.assertEqual(self.out["whole_calls"][1]["tags"], ["a", "seen"])

    def test_a_valid_pin_behaves_like_the_canonical_call(self):
        self.assertEqual(self.out["read_raw"], self.out["read_canonical"])
        self.assertTrue(self.out["read_raw"].startswith("alpha"), self.out["read_raw"])

    def test_core_handler_refuses_after_register_returns(self):
        self.assertIn("ExtensionLoadError: core_handler is available only while a module registers",
                      self.out["late_core_handler"])

    def test_extra_arguments_are_refused_and_never_forwarded(self):
        extras = self.out["extras"]
        for label, rejected in (("renamed_away", ["change_id"]), ("pinned_override", ["mode"]),
                                ("pinned_phase", ["phase"]), ("nested_kwargs", ["mode"]), ("stranger", ["bogus"])):
            with self.subTest(case=label):
                self.assertEqual(extras[label]["codes"], ["error", "unknown_arguments"])
                self.assertEqual(extras[label]["data"]["rejected_arguments"], rejected)
        self.assertEqual(extras["pinned_override"]["data"]["supported_arguments"], ["set_id", "wave_id"])
        self.assertIn("Supported parameters: set_id, wave_id.", extras["pinned_override"]["message"][0])
        self.assertEqual(extras["pinned_phase"]["data"]["supported_arguments"], ["wave_id"])
        self.assertFalse(self.out["extras_reached_canonical"])
        # The empty compatibility payload is accepted, as on canonical tools.
        self.assertEqual(self.out["empty_kwargs_call"], ["ok"])

    def test_lock_taken_once_inside_the_canonical_body(self):
        swap = self.out["add_calls"][0]
        self.assertTrue(swap["lock_held"])
        self.assertEqual(swap["acquired"], 1)
        self.assertEqual(self.out["swap_lock_acquired"], 1)

    def test_upgrade_checkpoint_fails_fast(self):
        self.assertEqual(self.out["guarded"], ["error", "upgrade_in_progress"])
        self.assertFalse(self.out["guarded_reached_canonical"])

    def test_cost_recorded_once_under_the_canonical_name(self):
        self.assertEqual(self.out["swap_cost"], ["wf_add_change"])

    def test_aliases_take_the_canonical_tier_in_allow_rules(self):
        self.assertEqual(self.out["parity_defects"], [])
        self.assertEqual(self.out["served_vs_tiers"], [])
        for alias in ("fork_add_wave", "fork_add_wave_now", "fork_review_prepare"):
            self.assertEqual(self.out["tiers"][alias], "write", alias)
            self.assertIn(alias, self.out["write_rules"])
            self.assertNotIn(alias, self.out["read_rules"])

    def test_busy_hints_name_the_unpinned_alias(self):
        busy = self.out["busy"]
        self.assertEqual(busy["codes"], ["error", "lifecycle_mutation_locked"])
        self.assertEqual(busy["next_tools"], ["fork_add_wave", "wf_current_wave"])
        self.assertEqual(busy["recovery_usage"], ["fork_add_wave(...) once the concurrent mutation completes"])
        # Prose names the preferred unpinned alias too.
        self.assertEqual(busy["usage"], "retry fork_add_wave after the concurrent lifecycle mutation completes")

    def test_served_call_hints_never_rewrite_argument_values(self):
        _assert_value_hints_kept(self, self.out["value_hints"])

    def test_hint_rules_on_the_live_call_specs(self):
        specs = self.out["call_specs"]
        self.assertEqual(specs["wf_add_change"]["aliases"][0][0], "fork_add_wave")
        self.assertEqual(specs["wf_review_wave"]["defaults"], {"phase": "implementation"})
        lists = self.out["hint_lists"]
        self.assertEqual(lists["next_tools"], ["wf_review_wave", "fork_add_wave"])
        self.assertEqual(lists["diagnostics"][0]["recovery_tools"], ["wf_review_wave"])
        usage = self.out["hint_usage"]
        self.assertEqual(usage["pin_present_equal"], "fork_review_prepare(wave_id='1abcd')")
        self.assertEqual(usage["pin_present_differs"], "wf_review_wave(wave_id='1abcd', phase='implementation')")
        self.assertEqual(usage["pin_absent_default_differs"], "wf_review_wave(wave_id='1abcd')")
        self.assertEqual(usage["pin_absent_default_equal"], "fork_review_delivery(wave_id='1abcd')")
        self.assertEqual(usage["swap"], "then fork_add_wave(set_id='1abcd', wave_id='1abce-feat x', mode='create') now")
        self.assertEqual(usage["unparseable"], "wf_add_change(wave_id='1abcd', change_id=")
        self.assertEqual(usage["non_literal"], "fork_add_wave(set_id=wave, wave_id=change)")
        self.assertEqual(usage["duplicate"], "wf_add_change(wave_id='a', wave_id='b')")
        self.assertEqual(usage["star_star"], "wf_add_change(**opts)")
        self.assertEqual(usage["pinned_non_literal_value"], "fork_review_prepare(wave_id=w)")
        self.assertEqual(usage["pinned_non_literal_pin"], "wf_review_wave(wave_id='w', phase=p)")
        self.assertEqual(usage["prose"], "retry fork_add_wave after the lock clears")
        self.assertEqual(usage["placeholder"], "fork_add_wave(...) once free")
        self.assertEqual(usage["pinned_placeholder"], "wf_review_wave(...)")

    def test_override_delegates_to_the_core_handler(self):
        call = self.out["delegate_call"]
        self.assertEqual(call["data"], {"spied": "wf_remove_change_response"})
        self.assertTrue(call["delegated"])
        (remove,) = self.out["remove_calls"]
        self.assertTrue(remove["lock_held"])
        self.assertEqual(self.out["delegate_lock_acquired"], 1)
        self.assertEqual(self.out["delegate_cost"], ["wf_remove_change"])
        # The override gets the canonical name-keyed wrappers once; the core handler none.
        self.assertEqual(self.out["markers"]["wf_remove_change"], ["cost", "lock", "guard", "setup", "rewrite", "render"])

    def test_provenance_lists_parameter_mappings(self):
        params = self.out["extensions"]["parameters"]
        # Wave 1zls8 (1zlty AC-6): every entry reports response_keys, empty when undeclared.
        self.assertEqual(params["fork_add_wave_now"], {
            "canonical": "wf_add_change", "rename": {"set_id": "wave_id", "wave_id": "change_id"}, "fixed": {"mode": "create"},
            "description": None, "response_keys": {},
        })
        self.assertEqual(params["fork_review_prepare"], {"canonical": "wf_review_wave", "rename": {}, "fixed": {"phase": "prepare"},
                                                         "description": None, "response_keys": {}})
        # Wave 1zime (1zimm AC-7): a declared description is reported verbatim.
        self.assertEqual(params["fork_say"], {"canonical": "fork_echo", "rename": {"words": "text"}, "fixed": {},
                                              "description": SAY_DESCRIPTION, "response_keys": {}})
        self.assertEqual(self.stock["extensions"]["parameters"], {})
        # A pinned-only canonical name keeps its canonical served name.
        self.assertNotIn("wf_review_wave", self.out["extensions"]["served_names"])
        self.assertEqual(self.out["extensions"]["served_names"]["wf_add_change"], "fork_add_wave")

    # Wave 1zime (1zimm) AC-1.
    def test_alias_response_data_echoes_alias_parameter_names(self):
        self.assertEqual(self.out["swap_call"], {"set_id": "1abcd", "wave_id": "1abce-feat x", "mode": "dry_run"})
        self.assertNotIn("change_id", self.out["swap_call"])
        self.assertEqual(list(self.out["swap_call"]), ["set_id", "wave_id", "mode"])
        # A pinned parameter's echoed key keeps its canonical name.
        self.assertEqual(self.out["pinned_add_call"], {"set_id": "1abcd", "wave_id": "1abce-feat x", "mode": "create"})

    # AC-2.
    def test_canonical_and_plain_alias_data_match_the_stock_server(self):
        self.assertEqual(json.dumps(self.out["canonical_add_call"]), json.dumps(self.stock["add_call"]))
        self.assertEqual(self.stock["add_call"], {"wave_id": "1abcd", "change_id": "1abce-feat x", "mode": "dry_run"})
        self.assertEqual(json.dumps(self.out["plain_get_call"]), json.dumps(self.stock["get_call"]))
        self.assertEqual(json.dumps(self.out["canonical_get_call"]), json.dumps(self.stock["get_call"]))

    # AC-4.
    def test_every_canonical_tool_of_a_mapped_alias_is_synchronous(self):
        targets = self.out["mapped_targets_coroutine"]
        self.assertEqual(sorted(targets), ["fork_add_wave", "fork_add_wave_now", "fork_read_raw",
                                           "fork_review_prepare", "fork_say", "fork_say_whole"])
        for alias, flags in targets.items():
            self.assertEqual(flags, [False, False, False], alias)

    # AC-7.
    def test_a_declared_description_is_served_only_on_its_alias(self):
        listed = self.out["listed_descriptions"]
        canonical = "Echo text back. Provide text; count repeats it."
        self.assertEqual(listed["fork_say"], SAY_DESCRIPTION)
        self.assertEqual(listed["fork_echo"], canonical)
        self.assertEqual(listed["fork_say_plain"], canonical)
        self.assertEqual(listed["fork_say_whole"], canonical)
        self.assertEqual(self.out["reload_descriptions"],
                         {"fork_echo": canonical, "fork_say": SAY_DESCRIPTION})

    def test_reload_rebuilds_the_translator(self):
        self.assertEqual(self.out["reload_status"], "ok")
        self.assertEqual(self.out["reload_schema"], self.out["schemas"]["fork_add_wave"])
        self.assertTrue(self.out["reload_wraps_canonical"])


_VALUE_HINTS_SERVED = {
    "usage": "fork_add_wave(set_id='wf_add_change', wave_id='fork_add_wave') then wf_review_wave(wave_id='wf_add_change')",
    "recovery_usage": ["dict(x='wf_add_change') or fork_add_wave(set_id=f(wf_add_change)); retry fork_add_wave"],
}


def _assert_value_hints_kept(case, value_hints):
    # Wave 1zim3 repair: only callee and keyword names change; argument values
    # (including ones equal to a canonical or alias tool name) are byte-identical.
    case.assertEqual(value_hints["usage"], _VALUE_HINTS_SERVED["usage"])
    case.assertEqual(value_hints["recovery_usage"], _VALUE_HINTS_SERVED["recovery_usage"])


class HiddenMappedAliasHintTests(unittest.TestCase):
    """Wave 1zim3 repair: a hidden canonical name with only a rename-only alias."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run("params_hidden")

    def test_busy_hints_name_only_served_tools(self):
        self.assertFalse(self.out["hidden_served"])
        busy = self.out["busy"]
        self.assertEqual(busy["codes"], ["error", "lifecycle_mutation_locked"])
        self.assertEqual(busy["next_tools"], ["fork_add_wave", "wf_current_wave"])
        self.assertEqual(busy["recovery_tools"], [["fork_add_wave", "wf_current_wave"]])
        self.assertEqual(busy["usage"], "retry fork_add_wave after the concurrent lifecycle mutation completes")
        self.assertEqual(busy["recovery_usage"], ["fork_add_wave(...) once the concurrent mutation completes"])

    def test_served_call_hints_never_rewrite_argument_values(self):
        _assert_value_hints_kept(self, self.out["value_hints"])

    def test_prose_lists_and_calls_name_the_alias(self):
        out = self.out["rewritten"]
        self.assertEqual(out["next_tools"], ["fork_add_wave"])
        self.assertEqual(out["usage"], "fork_add_wave is hidden; call fork_add_wave(set_id=w, wave_id=c) or fork_add_wave(set_id='a')")
        self.assertEqual(out["diagnostics"][0]["recovery_tools"], ["fork_add_wave"])
        self.assertEqual(out["diagnostics"][0]["recovery_usage"], "retry fork_add_wave later")


class EchoedParameterRenameTests(unittest.TestCase):
    """Wave 1zime (1zimm AC-3): the alias translator's top-level data key rename."""

    SWAP = {"set_id": "wave_id", "wave_id": "change_id"}

    def setUp(self):
        from server_tools_support import load_server
        self.rename = load_server()._rename_echoed_parameters

    def test_swap_is_simultaneous_and_keeps_order_and_values(self):
        value = ["kept", "by", "identity"]
        result = {"status": "ok", "data": {"wave_id": "w", "mode": "dry_run", "change_id": value, "other": 1}}
        out = self.rename(result, self.SWAP)
        self.assertEqual(list(out["data"]), ["set_id", "mode", "wave_id", "other"])
        self.assertEqual(out["data"]["set_id"], "w")
        self.assertIs(out["data"]["wave_id"], value)

    def test_nested_data_keeps_its_keys(self):
        nested = {"wave_id": "inner", "items": [{"change_id": "c"}]}
        out = self.rename({"data": {"wave_id": "w", "nested": nested, "list": [{"wave_id": "x"}]}}, self.SWAP)
        self.assertIs(out["data"]["nested"], nested)
        self.assertEqual(out["data"]["nested"], {"wave_id": "inner", "items": [{"change_id": "c"}]})
        self.assertEqual(out["data"]["list"], [{"wave_id": "x"}])

    def test_string_value_equal_to_a_parameter_name_is_unchanged(self):
        out = self.rename({"data": {"wave_id": "change_id", "note": "wave_id"}}, self.SWAP)
        self.assertEqual(out["data"], {"set_id": "change_id", "note": "wave_id"})

    def test_pinned_parameter_keeps_its_canonical_key(self):
        # `mode` is pinned (fixed), not renamed: the alias has no name for it.
        out = self.rename({"data": {"wave_id": "w", "change_id": "c", "mode": "create"}}, self.SWAP)
        self.assertEqual(out["data"], {"set_id": "w", "wave_id": "c", "mode": "create"})

    def test_collision_leaves_data_unchanged(self):
        result = {"status": "ok", "data": {"set_id": "already", "wave_id": "w"}}
        out = self.rename(result, {"set_id": "wave_id"})
        self.assertIs(out, result)
        self.assertEqual(out["data"], {"set_id": "already", "wave_id": "w"})

    def test_input_is_never_mutated(self):
        result = {"status": "ok", "data": {"wave_id": "w", "change_id": "c"}, "next_tools": ["x"]}
        before = json.dumps(result)
        out = self.rename(result, self.SWAP)
        self.assertEqual(json.dumps(result), before)
        self.assertIsNot(out, result)
        self.assertIsNot(out["data"], result["data"])
        self.assertIs(out["next_tools"], result["next_tools"])

    def test_non_dict_shapes_are_returned_unchanged(self):
        for result in ("text", None, ["wave_id"], {"status": "ok"}, {"data": None}, {"data": ["wave_id"]}):
            with self.subTest(result=result):
                self.assertIs(self.rename(result, self.SWAP), result)
        result = {"data": {"wave_id": "w"}}
        self.assertIs(self.rename(result, {}), result)

    def test_an_awaitable_result_is_returned_unchanged(self):
        async def coroutine():
            return {"data": {"wave_id": "w"}}
        awaitable = coroutine()
        try:
            self.assertIs(self.rename(awaitable, self.SWAP), awaitable)
        finally:
            awaitable.close()


class ResponseKeyRenameTests(unittest.TestCase):
    """Wave 1zls8 (1zlty AC-3 to AC-5): the combined echo and response-key walk."""

    def setUp(self):
        from server_tools_support import load_server
        impl = load_server()
        self.walk = lambda result, rename, keys: impl._rename_response_keys(result, rename, impl._response_key_tree(keys))

    def test_nested_paths_rename_only_their_last_key_in_place(self):
        result = {"status": "ok", "data": {"changes": [{"change_id": "a", "x": 1}], "wave_id": "w"}}
        out = self.walk(result, {}, {"changes": "items", "changes[].change_id": "item_id"})
        self.assertEqual(out["data"], {"items": [{"item_id": "a", "x": 1}], "wave_id": "w"})
        self.assertEqual(list(out["data"]), ["items", "wave_id"])
        self.assertNotIn("diagnostics", out)

    def test_a_swap_does_not_chain(self):
        out = self.walk({"data": {"a": 1, "b": 2, "c": 3}}, {}, {"a": "b", "b": "a"})
        self.assertEqual(list(out["data"].items()), [("b", 1), ("a", 2), ("c", 3)])

    def test_echo_and_single_segment_keys_share_one_top_level_pass(self):
        out = self.walk({"data": {"wave_id": "w", "changes": [], "mode": "m"}},
                        {"set_id": "wave_id"}, {"changes": "items"})
        self.assertEqual(list(out["data"]), ["set_id", "items", "mode"])

    def test_a_collision_keeps_that_object_canonical_with_one_advisory(self):
        result = {"status": "ok", "data": {"changes": [{"change_id": "a", "item_id": "x"}, {"change_id": "b"},
                                                       {"change_id": "c", "item_id": "y"}]},
                  "diagnostics": [{"code": "existing", "message": "m"}], "next_tools": ["t"], "usage": "u"}
        out = self.walk(result, {}, {"changes": "items", "changes[].change_id": "item_id"})
        self.assertEqual(out["data"]["items"], [{"change_id": "a", "item_id": "x"}, {"item_id": "b"},
                                                {"change_id": "c", "item_id": "y"}])
        advisory = [d for d in out["diagnostics"] if d["code"] == "response_key_rename_skipped"]
        self.assertEqual(len(advisory), 1)
        self.assertTrue(advisory[0]["advisory"])
        self.assertEqual(advisory[0]["message"].count("changes[].change_id"), 1)
        self.assertIn("stayed canonical because a rename at the same object would duplicate a key already present",
                      advisory[0]["message"])
        self.assertEqual(out["diagnostics"][0], {"code": "existing", "message": "m"})
        self.assertEqual((out["status"], out["next_tools"], out["usage"]), ("ok", ["t"], "u"))

    def test_a_top_level_collision_still_applies_child_renames(self):
        out = self.walk({"data": {"changes": [{"change_id": "a"}], "items": 1}}, {},
                        {"changes": "items", "changes[].change_id": "item_id"})
        self.assertEqual(out["data"], {"changes": [{"item_id": "a"}], "items": 1})
        self.assertTrue(out["diagnostics"][0]["message"].endswith(": changes."), out["diagnostics"])

    def test_an_echo_only_collision_adds_no_advisory_and_returns_the_result(self):
        result = {"status": "ok", "data": {"set_id": "already", "wave_id": "w"}}
        self.assertIs(self.walk(result, {"set_id": "wave_id"}, {}), result)
        # With response_keys elsewhere, the echo collision still names only declared paths.
        out = self.walk({"data": {"set_id": "s", "wave_id": "w", "meta": {"count": 1}}},
                        {"set_id": "wave_id"}, {"meta.count": "total"})
        self.assertEqual(out["data"], {"set_id": "s", "wave_id": "w", "meta": {"total": 1}})
        self.assertNotIn("diagnostics", out)

    def test_absent_and_wrongly_typed_paths_are_skipped(self):
        result = {"data": {"meta": 5, "list": {"k": 1}, "rows": [1, "x", None, {"k": 2}]}}
        out = self.walk(result, {}, {"meta.count": "n", "list[].k": "key", "rows[].k": "key", "gone.x": "y"})
        self.assertEqual(out["data"], {"meta": 5, "list": {"k": 1}, "rows": [1, "x", None, {"key": 2}]})
        self.assertIs(self.walk({"data": {"meta": 5}}, {}, {"meta.count": "n"})["data"]["meta"], 5)

    def test_values_keep_identity_and_the_input_is_never_mutated(self):
        import copy
        leaf = ["kept"]
        untouched = {"z": 1}
        result = {"status": "ok", "data": {"changes": [{"change_id": leaf, "keep": untouched}], "other": untouched},
                  "next_tools": ["n"]}
        before = copy.deepcopy(result)
        out = self.walk(result, {}, {"changes[].change_id": "item_id"})
        self.assertEqual(result, before)
        self.assertIs(out["data"]["changes"][0]["item_id"], leaf)
        self.assertIs(out["data"]["changes"][0]["keep"], untouched)
        self.assertIs(out["data"]["other"], untouched)
        self.assertIsNot(out["data"], result["data"])
        self.assertIsNot(out["data"]["changes"], result["data"]["changes"])
        self.assertIsNot(out["data"]["changes"][0], result["data"]["changes"][0])
        self.assertIs(out["next_tools"], result["next_tools"])

    def test_unchanged_shapes_are_returned_as_is(self):
        keys = {"changes": "items"}
        for result in ("text", None, ["changes"], {"status": "ok"}, {"data": None}, {"data": ["changes"]},
                       {"data": {"other": 1}}):
            with self.subTest(result=result):
                self.assertIs(self.walk(result, {}, keys), result)
        result = {"data": {"changes": 1}}
        self.assertIs(self.walk(result, {}, {}), result)

        async def coroutine():
            return {"data": {"changes": 1}}
        awaitable = coroutine()
        try:
            self.assertIs(self.walk(awaitable, {}, keys), awaitable)
        finally:
            awaitable.close()


class ResponseKeyServingTests(unittest.TestCase):
    """Wave 1zls8 (1zlty AC-2 to AC-6) through call_tool."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run("response_keys")

    def test_a_bulk_alias_answers_in_its_own_keys_with_canonical_values(self):
        out = self.out
        self.assertEqual(out["admitted"], ["1abce-enh keyed-item"])
        items, canonical = out["items_bulk"], out["canonical_bulk"]
        self.assertEqual(items["status"], "ok", items)
        self.assertNotIn("changes", items["data"])
        self.assertEqual(len(items["data"]["items"]), 1)
        self.assertEqual(len(canonical["data"]["changes"]), 1)
        for got, want in zip(items["data"]["items"], canonical["data"]["changes"]):
            self.assertEqual(got, {("item_id" if key == "id" else key): value for key, value in want.items()})
        self.assertEqual({k: v for k, v in items["data"].items() if k != "items"},
                         {k: v for k, v in canonical["data"].items() if k != "changes"})
        self.assertEqual(out["listed_description"], "Get one item, or every item of a set.")

    def test_canonical_plain_alias_and_unknown_arguments_answer_unchanged(self):
        out = self.out
        self.assertEqual(out["plain_bulk"]["data"], out["canonical_bulk"]["data"])
        self.assertIn("changes", out["canonical_bulk"]["data"])
        unknown = out["items_unknown"]
        self.assertEqual([d["code"] for d in unknown["diagnostics"]], ["unknown_arguments"])
        self.assertIn("rejected_arguments", unknown["data"])
        self.assertIn("supported_arguments", unknown["data"])

    def test_nested_lists_collisions_and_wrong_types_through_the_translator(self):
        data = self.out["nested"]["data"]
        self.assertEqual(list(data), ["set_id", "item_id", "mode", "items", "meta", "scalar"])
        self.assertEqual(data["items"], [
            {"change_id": "a", "item_id": "already"},
            {"item_id": "b", "note": "renamed"},
            {"change_id": "c", "item_id": "also there"},
            "not a dict",
        ])
        self.assertEqual(data["meta"], {"total": 2, "list": [{"item_key": 1}, 7, {"other": 2}]})
        self.assertEqual(data["scalar"], 5)
        diagnostics = self.out["nested"]["diagnostics"]
        self.assertEqual(diagnostics[0], {"code": "existing", "message": "kept"})
        skipped = [d for d in diagnostics if d["code"] == "response_key_rename_skipped"]
        self.assertEqual(len(skipped), 1, diagnostics)
        self.assertEqual(skipped[0]["message"].count("changes[].change_id"), 1)
        self.assertNotIn("wave_id", skipped[0]["message"])
        self.assertEqual(self.out["nested"]["status"], "ok")
        self.assertEqual(self.out["nested"]["next_tools"], ["probe_next"])
        self.assertEqual(self.out["nested"]["usage"], "probe_next(item='a')")

    def test_the_input_is_unchanged_and_values_keep_identity(self):
        self.assertTrue(self.out["nested_input_unchanged"])
        self.assertEqual(self.out["nested_identity"], {
            "note_value": True, "collided_element": True, "list_is_new": True, "renamed_element_is_new": True,
            "meta_is_new": True, "meta_list_is_new": True, "untouched_element": True,
            "diagnostics_input_unchanged": True,
        })

    def test_provenance_reports_the_declared_response_keys(self):
        params = self.out["extensions"]["parameters"]
        self.assertEqual(params["fork_get_items"]["response_keys"], {"changes": "items", "changes[].id": "item_id"})
        self.assertEqual(list(params["fork_add_item"]["response_keys"]),
                         sorted(["changes", "changes[].change_id", "meta.count", "meta.list[].key", "absent.deep", "scalar.inner"]))


class ServedNameRewriteTests(unittest.TestCase):
    """Wave 1z8oz Requirement 6: the four hint fields, exact and whole-name."""

    def setUp(self):
        from server_tools_support import load_server
        self.impl = load_server()

    def test_rewrites_only_the_hint_fields_and_never_mutates(self):
        names = {"wf_close_wave": "fork_close_container"}
        result = {
            "status": "error",
            "data": {"next_step": "wf_close_wave"},
            "next_tools": ["wf_close_wave", "wf_close_wave_x", "wf_current_wave"],
            "usage": "retry wf_close_wave(mode='x'); not wf_close_wave_x or xwf_close_wave",
            "diagnostics": [{"code": "c", "message": "wf_close_wave is busy",
                             "recovery_tools": ["wf_close_wave"], "recovery_usage": "wf_close_wave(...)"}],
        }
        before = json.dumps(result, sort_keys=True)
        out = self.impl._rewrite_served_names(result, names)
        self.assertEqual(json.dumps(result, sort_keys=True), before)
        self.assertEqual(out["next_tools"], ["fork_close_container", "wf_close_wave_x", "wf_current_wave"])
        self.assertEqual(out["usage"], "retry fork_close_container(mode='x'); not wf_close_wave_x or xwf_close_wave")
        self.assertEqual(out["diagnostics"][0]["recovery_tools"], ["fork_close_container"])
        self.assertEqual(out["diagnostics"][0]["recovery_usage"], "fork_close_container(...)")
        self.assertEqual(out["diagnostics"][0]["message"], "wf_close_wave is busy")
        self.assertEqual(out["data"], {"next_step": "wf_close_wave"})

    def test_core_behaviour_chain_tracks_middleware(self):
        # The core behaviour of a replaced name must get every wrapper the main
        # chain applies; a wrapper added to MIDDLEWARE alone would be missed.
        self.assertEqual([label for label, _ in self.impl._CORE_BEHAVIOUR_MIDDLEWARE],
                         [label for label, _ in self.impl.MIDDLEWARE])

    def test_empty_map_returns_the_same_object(self):
        result = {"next_tools": ["wf_close_wave"]}
        self.assertIs(self.impl._rewrite_served_names(result, {}), result)

    def test_a_plain_alias_beside_a_pinned_one_is_an_identity_mapping(self):
        # Wave 1zim3: the plain alias is preferred; canonical parameters keep their names.
        calls = {"wf_review_wave": {"aliases": [("fork_review", {}, {}), ("fork_review_prepare", {}, {"phase": "prepare"})],
                                    "defaults": {"phase": "implementation"}}}
        names = {"wf_review_wave": "fork_review"}
        out = self.impl._rewrite_served_names(
            {"next_tools": ["wf_review_wave"], "usage": "wf_review_wave(wave_id='w', phase='prepare'); wf_review_wave is read-only"},
            names, calls)
        self.assertEqual(out["next_tools"], ["fork_review"])
        self.assertEqual(out["usage"], "fork_review(wave_id='w', phase='prepare'); fork_review is read-only")

    def test_call_rewrite_handles_parentheses_in_values_and_unrelated_names(self):
        calls = {"wf_add_change": {"aliases": [("fork_add_wave", {"wave_id": "set_id", "change_id": "wave_id"}, {})],
                                   "defaults": {"mode": "dry_run"}}}
        out = self.impl._rewrite_served_names(
            {"usage": "wf_add_change(wave_id='a)b', change_id=\"c\") then wf_add_change_x(wave_id='a') or wf_close_wave()"},
            {"wf_close_wave": "fork_close"}, calls)
        self.assertEqual(out["usage"], "fork_add_wave(set_id='a)b', wave_id=\"c\") then wf_add_change_x(wave_id='a') or fork_close()")

    def test_whitespace_before_the_call_parenthesis_is_still_a_call(self):
        # Wave 1zim3 reverification: prose mapping must not give the alias name to
        # call text whose `(` follows after spaces or a newline.
        calls = {"wf_add_change": {"aliases": [("fork_add_wave", {"wave_id": "set_id", "change_id": "wave_id"}, {})],
                                   "defaults": {"mode": "dry_run"}}}
        names = {"wf_add_change": "fork_add_wave"}
        rewrite = lambda usage: self.impl._rewrite_served_names({"usage": usage}, names, calls)["usage"]
        self.assertEqual(rewrite("wf_add_change (wave_id='a')"), "fork_add_wave(set_id='a')")
        # A newline before `(` is not parsed as a call, so the text stays canonical rather
        # than pairing the alias name with canonical parameters.
        self.assertEqual(rewrite("wf_add_change\n(wave_id='a')"), "wf_add_change\n(wave_id='a')")
        # A placeholder beside keywords keeps the canonical text (spec).
        for usage in ("wf_add_change(..., mode='create')",):
            with self.subTest(usage=usage):
                self.assertEqual(self.impl._rewrite_served_names({"usage": usage}, names, calls)["usage"], usage)

    def test_present_pin_must_match_type_as_well_as_value(self):
        calls = {"wf_x": {"aliases": [("fork_x", {}, {"flag": True})], "defaults": {}}}
        rewrite = lambda usage: self.impl._rewrite_served_names({"usage": usage}, {}, calls)["usage"]
        self.assertEqual(rewrite("wf_x(flag=1)"), "wf_x(flag=1)")
        self.assertEqual(rewrite("wf_x(flag=True, n=2)"), "fork_x(n=2)")
        self.assertEqual(rewrite("wf_x(n=2)"), "wf_x(n=2)")  # absent with no canonical default
        self.assertEqual(rewrite("wf_x(**opts)"), "wf_x(**opts)")

    def _value_rewrite(self, usage, names=None, calls=None):
        names = {"wf_close_wave": "fork_close"} if names is None else names
        return self.impl._rewrite_served_names({"usage": usage}, names, calls)["usage"]

    def test_mapped_calls_keep_argument_values(self):
        # Wave 1zim3 repair: a value equal to a tool name, or holding `name(`, is not a name.
        calls = {"wf_add_change": {"aliases": [("fork_add_wave", {"wave_id": "set_id", "change_id": "wave_id"}, {})],
                                   "defaults": {"mode": "dry_run"}}}
        for usage, expected in (
            ("wf_add_change(wave_id='wf_add_change')", "fork_add_wave(set_id='wf_add_change')"),
            ("wf_add_change(wave_id='wf_close_wave', change_id=wf_close_wave)",
             "fork_add_wave(set_id='wf_close_wave', wave_id=wf_close_wave)"),
            ("wf_add_change(wave_id='wf_add_change(', change_id='x')", "fork_add_wave(set_id='wf_add_change(', wave_id='x')"),
            ("wf_add_change(wave_id=wf_add_change(change_id='wf_close_wave'))",
             "fork_add_wave(set_id=wf_add_change(change_id='wf_close_wave'))"),
            # Unmapped (pinned-only, non-literal pin) keeps the canonical callee and the values.
            ("wf_add_change(**{'wave_id': 'wf_close_wave'})", "wf_add_change(**{'wave_id': 'wf_close_wave'})"),
        ):
            with self.subTest(usage=usage):
                self.assertEqual(self._value_rewrite(usage, calls=calls), expected)

    def test_whole_name_calls_keep_argument_values(self):
        # The 1z8oz plain-alias path: only the callee is renamed.
        for usage, expected in (
            ("wf_close_wave(wave_id='wf_close_wave')", "fork_close(wave_id='wf_close_wave')"),
            ("wf_close_wave (wave_id=wf_close_wave)", "fork_close (wave_id=wf_close_wave)"),
            ("wf_close_wave(wave_id=wf_close_wave(...))", "fork_close(wave_id=wf_close_wave(...))"),
            ("wf_close_wave(note='wf_close_wave(x)')", "fork_close(note='wf_close_wave(x)')"),
            ("wf_close_wave(note=\"a ) wf_close_wave\")", "fork_close(note=\"a ) wf_close_wave\")"),
            # Any parsed callee's values are protected, not only served names.
            ("dict(x='wf_close_wave') then wf_close_wave()", "dict(x='wf_close_wave') then fork_close()"),
        ):
            with self.subTest(usage=usage):
                self.assertEqual(self._value_rewrite(usage), expected)

    def test_unparseable_call_arguments_are_left_unchanged(self):
        for usage, expected in (
            # Bounded by the matching parenthesis: text after it is still rewritten.
            ("wf_close_wave(path=<wf_close_wave>) then wf_close_wave", "fork_close(path=<wf_close_wave>) then fork_close"),
            # No matching parenthesis: the rest of the string is left unchanged.
            ("wf_close_wave(note='wf_close_wave", "fork_close(note='wf_close_wave"),
            ("wf_close_wave(a=(wf_close_wave", "fork_close(a=(wf_close_wave"),
        ):
            with self.subTest(usage=usage):
                self.assertEqual(self._value_rewrite(usage), expected)

    def test_unparseable_call_bound_respects_quotes_and_escapes(self):
        for usage, expected in (
            ("wf_close_wave(p=<a ')' wf_close_wave>)", "fork_close(p=<a ')' wf_close_wave>)"),
            ("wf_close_wave(p=<'it\\'s )' wf_close_wave>) then wf_close_wave",
             "fork_close(p=<'it\\'s )' wf_close_wave>) then fork_close"),
            # An unknown name whose call text does not parse is prose, so a served name after it maps.
            ("a(1 wf_close_wave", "a(1 fork_close"),
            # A `)` inside a comment does not close the call; a comment without a newline runs to the end.
            ("wf_close_wave(p=<1, # )\n wf_close_wave>) after wf_close_wave",
             "fork_close(p=<1, # )\n wf_close_wave>) after fork_close"),
            ("wf_close_wave(p=<1 # ) wf_close_wave", "fork_close(p=<1 # ) wf_close_wave"),
            # A `)` and a lone quote inside a triple-quoted string do not end it.
            ("wf_close_wave(p=<'''a ) ' wf_close_wave'''>) then wf_close_wave",
             "fork_close(p=<'''a ) ' wf_close_wave'''>) then fork_close"),
            ('wf_close_wave(p=<"""x ) " wf_close_wave""">) then wf_close_wave',
             'fork_close(p=<"""x ) " wf_close_wave""">) then fork_close'),
        ):
            with self.subTest(usage=usage):
                self.assertEqual(self._value_rewrite(usage), expected)

    def test_call_parsing_is_bounded(self):
        # Wave 1zim3 repair (NEW-1): at most one parse per candidate and a fixed
        # number of candidates per string, whatever the nesting.
        from unittest import mock
        import ast as ast_module
        limit = self.impl._HINT_CALL_ATTEMPTS
        real_parse = ast_module.parse
        count = [0]

        def counting_parse(*args, **kwargs):
            count[0] += 1
            if count[0] > limit:
                raise AssertionError(f"more than {limit} parses for one hint")
            return real_parse(*args, **kwargs)

        cases = (
            "a(" * 400 + ")" * 400,
            "a(" * 1600 + ")" * 1600,
            "code_list_files(glob='x' " + "a(" * 380 + ")" * 380 + "/**')",
            "wf_close_wave(" * 300 + ")" * 300,
        )
        for usage in cases:
            with self.subTest(length=len(usage), head=usage[:20]):
                count[0] = 0
                with mock.patch.object(self.impl.ast, "parse", counting_parse):
                    started = time.monotonic()
                    out = self._value_rewrite(usage)
                    elapsed = time.monotonic() - started
                self.assertLessEqual(count[0], limit)
                self.assertLess(elapsed, 5.0)
                if usage.startswith("wf_close_wave"):
                    self.assertEqual(out, "fork_close" + usage[len("wf_close_wave"):])
                else:
                    self.assertEqual(out, usage)

    def test_hint_strings_over_the_length_cap_are_unchanged(self):
        usage = "retry wf_close_wave(wave_id='w') " * 3000
        self.assertGreater(len(usage), self.impl._HINT_CALL_TEXT_LIMIT)
        self.assertEqual(self._value_rewrite(usage), usage)

    def test_mapped_calls_keep_every_byte_but_keyword_names(self):
        # Wave 1zim3 repair (NEW-2): parentheses, comments and newlines survive.
        swap = {"wf_add_change": {"aliases": [("fork_add_wave", {"wave_id": "set_id", "change_id": "wave_id"}, {})],
                                  "defaults": {}}}
        for usage, expected in (
            ("wf_add_change(wave_id=(x:=1))", "fork_add_wave(set_id=(x:=1))"),
            ("wf_add_change(wave_id=(a), change_id=( 'b' ))", "fork_add_wave(set_id=(a), wave_id=( 'b' ))"),
            ("wf_add_change(\n    wave_id='w',  # the wave\n    change_id='c',\n)",
             "fork_add_wave(\n    set_id='w',  # the wave\n    wave_id='c',\n)"),
            ("wf_add_change(wave_id='été', change_id='c')", "fork_add_wave(set_id='été', wave_id='c')"),
        ):
            with self.subTest(usage=usage):
                self.assertEqual(self._value_rewrite(usage, names={}, calls=swap), expected)

    def test_pinned_keywords_are_removed_in_any_position(self):
        calls = {
            "wf_x": {"aliases": [("fork_x", {"a": "b"}, {"mode": "create"})], "defaults": {}},
            "wf_y": {"aliases": [("fork_y", {"a": "b"}, {"mode": "create", "n": 1})], "defaults": {}},
        }
        for usage, expected in (
            ("wf_x(mode='create', a=1, c=2)", "fork_x(b=1, c=2)"),
            ("wf_x(a=1, mode='create', c=2)", "fork_x(b=1, c=2)"),
            ("wf_x(a=1, c=2, mode='create')", "fork_x(b=1, c=2)"),
            ("wf_x(a=1, c=2, mode='create',)", "fork_x(b=1, c=2,)"),
            ("wf_x(mode='create')", "fork_x()"),
            ("wf_y(a=1, mode='create', n=1)", "fork_y(b=1)"),
            ("wf_y(mode='create', a=1, n=1)", "fork_y(b=1)"),
            ("wf_y(n=1, mode='create', a=(1))", "fork_y(b=(1))"),
            ("wf_x(a=(1), mode=('create'))", "fork_x(b=(1))"),
            # A comment where a pinned keyword would be removed keeps the canonical form.
            ("wf_x(a=1,  # keep\n mode='create')", "wf_x(a=1,  # keep\n mode='create')"),
        ):
            with self.subTest(usage=usage):
                self.assertEqual(self._value_rewrite(usage, names={}, calls=calls), expected)

    def test_prose_outside_calls_still_maps(self):
        calls = {"wf_add_change": {"aliases": [("fork_add_wave", {"wave_id": "set_id"}, {})], "defaults": {}}}
        self.assertEqual(
            self._value_rewrite("retry wf_close_wave; or wf_add_change later (see wf_close_wave)", calls=calls),
            "retry fork_close; or fork_add_wave later (see fork_close)")
        self.assertEqual(self._value_rewrite("wf_add_change(wave_id='w') after wf_add_change", calls=calls),
                         "fork_add_wave(set_id='w') after fork_add_wave")


class ExtensionServingTests(unittest.TestCase):
    """AC-2, AC-4, AC-7 through the real build_server path."""

    @classmethod
    def setUpClass(cls):
        cls.stock = _run("stock")
        cls.out = _run("ext")

    def test_new_tools_served_and_undeclared_module_ignored(self):
        self.assertEqual(self.out["names"], ["acme_echo", "acme_write"])

    def test_registry_and_allowlist_carry_declared_tiers(self):
        self.assertEqual(self.out["parity_defects"], [])
        self.assertEqual(self.out["tiers"]["acme_echo"], "read")
        self.assertEqual(self.out["tiers"]["acme_write"], "write")
        self.assertEqual(self.out["read_rules"], ["mcp__wavefoundry__acme_echo", "mcp__wavefoundry__wf_current_wave"])
        self.assertEqual(self.out["write_rules"], ["mcp__wavefoundry__acme_echo", "mcp__wavefoundry__acme_write"])

    def test_overrides_serve_under_core_names_with_core_tiers(self):
        self.assertEqual(self.out["override_read"], {"overridden": "wf_current_wave"})
        # The lock probe is installed later (see the real-client-path test).
        self.assertEqual(self.out["override_lifecycle"], {"overridden": "wf_create_wave", "slug": "probe", "lock_held": None})
        self.assertEqual(self.out["tiers"]["wf_current_wave"], self.out["core_tiers"]["wf_current_wave"])
        self.assertEqual(self.out["tiers"]["wf_create_wave"], self.out["core_tiers"]["wf_create_wave"])
        self.assertEqual(self.out["override_unknown_arg"], ["unknown_arguments"])

    def test_real_client_path_holds_the_lock_and_validates_arguments(self):
        # Through FastMCP call_tool: argument model, sync/async dispatch, run.
        self.assertEqual(self.out["call_tool_lifecycle"], {"overridden": "wf_create_wave", "slug": "probe", "lock_held": True})
        self.assertTrue(self.out["call_tool_lock_released"])
        self.assertEqual(self.out["call_tool_unknown_arg"], ["unknown_arguments"])
        self.assertEqual(self.out["call_tool_echo"], "hi")
        self.assertEqual(self.out["call_tool_write_blocked"], ["error", "upgrade_in_progress"])

    def test_overrides_inherit_exactly_the_core_wrappers(self):
        self.assertEqual(self.out["markers"]["wf_current_wave"], self.stock["markers"]["wf_current_wave"])
        # Wave 1zls8 (1zltz): an override of a cost-exempt core name also gets
        # the innermost delta recorder, since the core it may delegate to
        # records only its own response.
        # Wave 1zlu1 (N1): this override omits `parent`, so the outermost
        # omitted-parameter guard is added after the core chain.
        # Wave 1zoju (1zodw): the final render pass stays outermost.
        self.assertEqual(self.out["markers"]["wf_create_wave"],
                         ["cost"] + self.stock["markers"]["wf_create_wave"][:-1] + ["omitted", "render"])
        self.assertIn("lock", self.out["markers"]["wf_create_wave"])

    def test_new_tools_are_wrapped_costed_and_upgrade_guarded(self):
        self.assertIn("cost", self.out["markers"]["acme_echo"])
        self.assertTrue(self.out["cost_wrapped"])
        self.assertIn("guard", self.out["markers"]["acme_write"])
        self.assertNotIn("guard", self.out["markers"]["acme_echo"])
        self.assertEqual(self.out["write_ok"], "ok")
        self.assertEqual(self.out["write_blocked"], ["error", "upgrade_in_progress"])
        self.assertEqual(self.out["echo_during_upgrade"], "ok")

    def test_provenance_names_module_hash_tools_and_overrides(self):
        ext = self.out["extensions"]
        self.assertEqual(ext["declaration"]["prefixes"], ["acme_"])
        self.assertEqual(ext["declaration"]["tiers"], {"acme_echo": "read", "acme_write": "write"})
        (module,) = ext["modules"]
        self.assertEqual(module["module"], "acme_tools")
        self.assertEqual(module["path"], "scripts/acme_tools.py")
        self.assertEqual(ext["declaration"]["path"], "scripts/mcp_tool_extensions.py")
        self.assertEqual(module["sha256"], self.out["acme_sha"])
        self.assertEqual(module["tools"], [{"name": "acme_echo", "tier": "read"}, {"name": "acme_write", "tier": "write"}])
        self.assertEqual(module["overrides"], ["wf_create_wave", "wf_current_wave"])
        # Wave 1zlu1 (F3): the pre-1zlu1 override signature omits `parent`.
        self.assertEqual(module["omitted_core_parameters"], {"wf_create_wave": ["parent"]})

    def test_override_omitting_parent_installs_and_refuses_a_parent_argument(self):
        self.assertEqual(self.out["call_tool_parent_refused"], ["error", "unknown_arguments"])


class ExtensionReloadTests(unittest.TestCase):
    """AC-5 and the reload half of AC-3."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run("reload")

    def test_reload_serves_edited_extension_with_new_hash(self):
        self.assertEqual(self.out["reload_status"], "ok")
        self.assertEqual(self.out["echo_version"], "v2")
        self.assertTrue(self.out["sha_changed"])
        self.assertTrue(self.out["sha_matches_file"])

    def test_failed_reload_serves_only_runner_tools(self):
        self.assertIn("register_surface_failed", self.out["failed_reload_text"])
        self.assertEqual(self.out["served_after_failure"], ["wf_reload_mcp"])


class ExtensionStartupRefusalTests(unittest.TestCase):
    """AC-3 at startup: build_server refuses and serves nothing."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run("startup_fail")

    def test_build_server_refuses_and_serves_no_tool(self):
        self.assertEqual(self.out["raised"], "ExtensionLoadError")
        self.assertIn("has no registered tool", self.out["message"])
        self.assertEqual(self.out["served"], [])


class PublicHelperServingTests(unittest.TestCase):
    """Wave 1zimf (1zimn AC-2, AC-4): a module using only the public helpers."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run("public")

    def test_the_fixture_uses_only_public_helpers(self):
        start = _DRIVER.index('PUBLIC = """')
        source = _DRIVER[start:_DRIVER.index('"""', start + len('PUBLIC = """'))]
        self.assertNotIn("server_impl._", source)
        for name in ("ensure_no_extra_args", "make_response", "make_diagnostic"):
            self.assertIn(f"server_impl.{name}(", source)

    def test_registers_and_serves_through_call_tool(self):
        self.assertEqual(self.out["names"], ["acme_member", "acme_public"])
        self.assertEqual(self.out["ok_call"]["status"], "ok")
        self.assertEqual(self.out["ok_call"]["data"], {"echo": "hi"})
        failed = self.out["fail_call"]
        self.assertEqual(failed["status"], "error")
        self.assertIs(failed["isError"], True)
        self.assertEqual(failed["diagnostics"], [{
            "code": "acme_failed", "message": "asked to fail",
            "recovery_tools": ["acme_public"], "recovery_usage": "acme_public(text='x')",
        }])

    def test_the_member_doc_reader_is_published(self):
        # Wave 200ey (change 200ew, AC-2): the declared module reads a member
        # doc, catches the published refusal type for a linked one, before and
        # after a reload, and checks the change-id shape.
        self.assertEqual(self.out["member_read"]["data"], {"change_id": True, "bytes": len("# Probe\n")})
        self.assertEqual(self.out["member_not_id"]["data"], {"change_id": False})
        if self.out["member_linked"] is None:
            self.skipTest("symbolic links are unavailable on this host")
        for key in ("member_linked", "reload_member_linked"):
            with self.subTest(call=key):
                self.assertEqual(self.out[key]["status"], "ok", self.out[key])
                self.assertTrue(self.out[key]["data"]["change_id"])
                self.assertEqual(self.out[key]["data"]["refused"], "not a regular file")

    def test_an_undeclared_argument_gets_the_unknown_arguments_envelope(self):
        refused = self.out["unknown_call"]
        self.assertEqual(refused["status"], "error")
        self.assertIs(refused["isError"], True)
        self.assertEqual([d["code"] for d in refused["diagnostics"]], ["unknown_arguments"])
        self.assertEqual(refused["data"]["rejected_arguments"], ["bogus"])
        self.assertEqual(self.out["empty_kwargs_call"]["status"], "ok")

    def test_public_helpers_resolve_and_stay_late_bound_after_reload(self):
        self.assertEqual(self.out["reload_status"], "ok")
        self.assertTrue(self.out["reload_helpers"])
        self.assertTrue(all(self.out["reload_helpers"].values()), self.out["reload_helpers"])
        self.assertTrue(all(self.out["reload_equal"].values()), self.out["reload_equal"])
        self.assertEqual(self.out["reload_late_bound"], {"patched": True})
        self.assertEqual([d["code"] for d in self.out["reload_unknown_call"]["diagnostics"]], ["unknown_arguments"])
        self.assertEqual(self.out["reload_ok_call"]["data"], {"echo": "again"})


class HelperModuleTests(unittest.TestCase):
    """Wave 1zls8 (1zltx AC-2, AC-3, AC-5, AC-10, AC-11): declared helper modules."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run("helpers")

    def test_helpers_load_marked_and_register_is_never_called(self):
        out = self.out
        self.assertEqual(out["names"], ["acme_touch"])
        self.assertEqual(out["register_calls"], [])
        self.assertEqual(out["marked"], {"acme_shared": True, "acme_extra": True, "acme_contract": True})

    def test_provenance_reports_each_helper_path_and_hash(self):
        out = self.out
        self.assertEqual(out["declared_helpers"], ["acme_shared", "acme_extra"])
        self.assertEqual([h["module"] for h in out["helper_provenance"]], ["acme_shared", "acme_extra"])
        for entry in out["helper_provenance"]:
            with self.subTest(helper=entry["module"]):
                self.assertTrue(entry["path"].endswith(f"{entry['module']}.py"), entry)
                self.assertEqual(entry["sha256"], out["helper_sha"][entry["module"]])

    def test_the_contract_only_module_serves_through_call_tool(self):
        out = self.out
        created = out["touch_create"]
        self.assertEqual(created["status"], "ok", created)
        self.assertEqual(created["data"]["helper"], "h1")
        self.assertEqual(created["data"]["refreshed"], {"project": True})
        self.assertEqual(created["data"]["lint"], {"passed": True, "stub": True})
        self.assertEqual(out["refreshes"], [[out["record_filename"]]])
        dry = out["touch_dry_run"]
        self.assertEqual(dry["status"], "ok", dry)
        self.assertNotIn("lint", dry["data"])

    def test_archived_and_record_layout_refusals_take_the_core_shape(self):
        out = self.out
        touch, core = out["touch_archived"], out["core_archived"]
        self.assertEqual(touch["status"], "error")
        touch_diag = [d for d in touch["diagnostics"] if d["code"] == "archived_record_read_only"]
        core_diag = [d for d in core["diagnostics"] if d["code"] == "archived_record_read_only"]
        self.assertEqual(len(touch_diag), 1, touch)
        self.assertEqual(touch_diag, core_diag)
        touch, core = out["touch_invalid"], out["core_invalid"]
        self.assertEqual(touch["status"], core["status"])
        self.assertEqual(touch["status"], "error")
        self.assertEqual(touch["diagnostics"], core["diagnostics"])
        self.assertEqual(touch["data"]["tool"], "acme_touch")
        for key in ("record_layout_valid", "diagnostics_detail"):
            self.assertEqual(touch["data"][key], core["data"][key], key)

    def test_an_edited_helper_is_served_with_its_new_hash_after_reload(self):
        # Known-bad (AC-5): without helper preloading the helper is imported
        # only by the extension module's import, has no hash and keeps the old bytes.
        out = self.out
        self.assertEqual(out["edit_reload_status"], "ok")
        self.assertEqual(out["edit_touch"], "h2")
        shared = [h for h in out["edit_provenance"] if h["module"] == "acme_shared"]
        self.assertEqual(len(shared), 1, out["edit_provenance"])
        self.assertEqual(shared[0]["sha256"], out["edit_sha"])
        self.assertNotEqual(out["edit_sha"], out["helper_sha"]["acme_shared"])

    def test_the_wrappers_resolve_and_stay_late_bound_after_reload(self):
        self.assertTrue(all(self.out["reload_helpers"].values()), self.out["reload_helpers"])
        # Eleven helpers, plus wave 200ey's (change 200ew) member-doc reader,
        # change-id test and refusal type.
        self.assertEqual(len(self.out["reload_helpers"]), 14)
        self.assertEqual(self.out["reload_late_bound"], "patched")

    def test_a_dropped_helper_and_an_emptied_declaration_are_evicted(self):
        out = self.out
        self.assertEqual(out["drop_reload_status"], "ok")
        self.assertEqual(out["drop_in_modules"], {"acme_shared": True, "acme_extra": False, "acme_contract": True})
        self.assertEqual(out["empty_reload_status"], "ok")
        self.assertEqual(out["empty_in_modules"], {"acme_shared": False, "acme_extra": False, "acme_contract": False})
        self.assertEqual(out["empty_provenance"], [])

    def test_an_out_of_order_import_is_refused_on_reload_and_a_fixed_order_recovers(self):
        out = self.out
        self.assertIn("register_surface_failed", out["order_reload_text"])
        self.assertIn("collides with a module the server already imported", out["order_reload_text"])
        self.assertEqual(out["order_served"], [])
        self.assertEqual(out["order_in_modules"], {"acme_shared": False, "acme_extra": False, "acme_contract": False})
        self.assertEqual(out["fixed_reload_status"], "ok", out["fixed_reload_text"])
        self.assertEqual(out["fixed_names"], ["acme_touch"])
        self.assertEqual(out["fixed_marked"], {"acme_shared": True, "acme_extra": True, "acme_contract": True})


class UnhandledToolExceptionRenderTests(unittest.TestCase):
    """Wave 1zoju (1zodw): an exception escaping a served callable reaches the
    client as a path-free `tool_unhandled_exception` error envelope."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run("render")

    def case(self, name):
        return self.out["cases"][name]

    def assert_rendered(self, name, message, tool):
        case = self.case(name)
        self.assertNotIn("escaped", case, f"{name}: {case}")
        self.assertEqual(case["status"], "error", name)
        self.assertIs(case["isError"], True, name)
        self.assertEqual(case["tool"], tool, name)
        self.assertEqual(case["diagnostics"], [["tool_unhandled_exception", message]], name)
        self.assertFalse(case["leaks_root"], name)

    def test_os_error_renders_class_errno_and_relative_filename(self):
        """AC-1, through FastMCP's client path and the served table."""
        for name in ("extension_client", "extension"):
            self.assert_rendered(name, "PermissionError EACCES on docs/x.md", "fork_boom")

    def test_every_served_kind_is_rendered(self):
        """AC-3: extension, plain alias, override, alias_for_core, and each
        step of a mapped alias's translator."""
        self.assert_rendered("plain_alias", "RuntimeError", "fork_boom")
        self.assert_rendered("override", "RuntimeError", "wf_current_wave")
        self.assert_rendered("alias_for_core", "ValueError: bad goal", "fork_help_core")
        self.assert_rendered("mapped_rewrite", "KeyError: 'rewrite'", "fork_mapped")
        self.assert_rendered("mapped_deepcopy", "TypeError: deepcopy", "fork_mapped")
        self.assert_rendered("mapped_rename", "LookupError: rename", "fork_mapped")
        self.assertEqual(self.case("mapped_ok")["status"], "ok")

    def test_the_render_pass_is_last_and_wraps_each_entry_once(self):
        """1zodw AC-3 and AC-8, amended by wave 1zqe4 (1zqe3) AC-4: every served
        tool ends in `render`, once, including the coroutine runner tool."""
        markers = self.out["markers"]
        self.assertEqual(self.out["coroutines"], ["wf_reload_mcp"])
        for name, labels in markers.items():
            with self.subTest(tool=name):
                self.assertEqual(labels[-1:], ["render"], labels)
                self.assertEqual(labels.count("render"), 1, labels)
        for name in ("fork_boom", "fork_plain", "fork_mapped", "fork_help_core", "wf_help", "wf_current_wave"):
            self.assertIn(name, markers)
        self.assertTrue(self.out["alias_shares_fn"])

    def test_the_reload_tool_renders_an_exception_path_free(self):
        """Wave 1zqe4 (1zqe3) AC-1: through FastMCP's client path."""
        self.assert_rendered("reload_client", "PermissionError EACCES on docs/x.md", "wf_reload_mcp")
        self.assertIs(self.out["reload_escape_text_leaks_root"], False)

    def test_the_reload_tool_keeps_its_one_render_across_a_reload(self):
        """Wave 1zqe4 (1zqe3) AC-4."""
        self.assertEqual(self.out["markers"]["wf_reload_mcp"][-1:], ["render"])
        self.assertEqual(self.out["markers"]["wf_reload_mcp"].count("render"), 1)
        self.assertEqual(self.out["real_reload_status"], "ok")
        self.assertIs(self.out["reload_same_fn"], True)
        self.assertEqual(self.out["reload_markers_after_reload"], self.out["markers"]["wf_reload_mcp"])
        self.assertIs(self.out["second_pass_unchanged"], True)

    def test_an_inner_wrapper_exception_is_rendered(self):
        """AC-4: raised by the upgrade-publication guard, outside the body."""
        self.assert_rendered("inner_guard", "RuntimeError", "wf_add_change")

    def test_an_interrupt_propagates(self):
        """AC-5."""
        self.assertEqual(self.case("interrupt"), {"escaped": "KeyboardInterrupt"})


class UnhandledToolExceptionUnitTests(unittest.TestCase):
    """Wave 1zoju (1zodw) AC-2, AC-5 to AC-7 on the pass itself."""

    @classmethod
    def setUpClass(cls):
        from server_tools_support import load_server
        cls.srv = load_server()

    def served(self, exc, get_handler):
        from types import SimpleNamespace

        def body():
            raise exc

        table = {"probe_tool": SimpleNamespace(fn=body)}
        self.srv._wrap_unhandled_tool_exceptions(SimpleNamespace(_tool_manager=SimpleNamespace(_tools=table)), get_handler)
        self.assertTrue(table["probe_tool"].fn._wf_rendered)
        return table["probe_tool"].fn

    def message(self, exc, get_handler):
        from unittest import mock
        with mock.patch.object(self.srv, "_wf_log"):
            result = self.served(exc, get_handler)()
        self.assertEqual(result["status"], "error")
        self.assertIs(result["isError"], True)
        self.assertEqual(result["data"], {"tool": "probe_tool"})
        (diagnostic,) = result["diagnostics"]
        self.assertEqual(diagnostic["code"], "tool_unhandled_exception")
        return diagnostic["message"]

    def test_absolute_paths_are_withheld_and_plain_text_kept(self):
        """AC-2."""
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            handler = lambda: SimpleNamespace(root=Path(tmp))
            self.assertEqual(self.message(RuntimeError("cannot open /tmp/elsewhere/lock"), handler), "RuntimeError")
            self.assertEqual(self.message(RuntimeError("cannot open C:\\elsewhere\\lock"), handler), "RuntimeError")
            self.assertEqual(self.message(ValueError("bad id"), handler), "ValueError: bad id")

    def test_a_failing_root_lookup_falls_back_to_class_and_errno(self):
        """AC-6."""
        import errno

        def broken():
            raise RuntimeError("handler at /srv/private/root failed")

        self.assertEqual(self.message(OSError(errno.EACCES, "Permission denied", "/srv/private/x"), broken),
                         "PermissionError EACCES")
        self.assertEqual(self.message(RuntimeError("cannot open /srv/private/lock"), broken), "RuntimeError")

    def test_interrupts_and_exits_propagate(self):
        """AC-5 on the pass: only ``Exception`` is caught."""
        for exc in (KeyboardInterrupt(), SystemExit(3)):
            with self.subTest(exc=type(exc).__name__), self.assertRaises(type(exc)):
                self.served(exc, lambda: None)()

    def test_the_full_traceback_goes_to_stderr(self):
        """AC-7."""
        import contextlib
        import io
        from types import SimpleNamespace
        stream = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(stream):
            result = self.served(RuntimeError(f"cannot open {tmp}/secret"), lambda: SimpleNamespace(root=Path(tmp)))()
        self.assertEqual(result["diagnostics"][0]["message"], "RuntimeError")
        logged = stream.getvalue()
        self.assertIn("Traceback (most recent call last)", logged)
        self.assertIn("probe_tool", logged)
        self.assertIn(f"RuntimeError: cannot open {tmp}/secret", logged)

    def test_coroutines_are_rendered_once_and_rendered_callables_skipped(self):
        """1zodw AC-8 as amended by wave 1zqe4 (1zqe3): coroutines are rendered
        too, still once; a plain alias shares the one rendered wrapper."""
        from types import SimpleNamespace

        async def runner_tool():
            return None

        def body():
            return {"status": "ok"}

        table = {"a": SimpleNamespace(fn=runner_tool), "a_alias": SimpleNamespace(fn=runner_tool),
                 "b": SimpleNamespace(fn=body), "c": SimpleNamespace(fn=body)}
        mcp = SimpleNamespace(_tool_manager=SimpleNamespace(_tools=table))
        self.srv._wrap_unhandled_tool_exceptions(mcp, lambda: None)
        rendered_coroutine = table["a"].fn
        self.assertIsNot(rendered_coroutine, runner_tool)
        self.assertIs(table["a_alias"].fn, rendered_coroutine)
        self.assertTrue(inspect.iscoroutinefunction(rendered_coroutine))
        first = table["b"].fn
        self.assertIs(table["c"].fn, first)
        self.srv._wrap_unhandled_tool_exceptions(mcp, lambda: None)
        self.assertIs(table["a"].fn, rendered_coroutine)
        self.assertIs(table["b"].fn, first)
        self.assertIs(first.__wrapped__, body)
        self.assertIs(rendered_coroutine.__wrapped__, runner_tool)

    def served_async(self, exc, get_handler):
        from types import SimpleNamespace

        async def body():
            raise exc

        table = {"probe_tool": SimpleNamespace(fn=body)}
        self.srv._wrap_unhandled_tool_exceptions(SimpleNamespace(_tool_manager=SimpleNamespace(_tools=table)), get_handler)
        fn = table["probe_tool"].fn
        self.assertIsNot(fn, body)
        self.assertTrue(fn._wf_rendered)
        self.assertTrue(inspect.iscoroutinefunction(fn))
        return fn

    def test_a_coroutine_renders_the_same_envelope_as_a_synchronous_callable(self):
        """Wave 1zqe4 (1zqe3) AC-2."""
        import asyncio
        import contextlib
        import errno
        import io
        from types import SimpleNamespace

        def broken():
            raise RuntimeError("handler at /srv/private/root failed")

        with tempfile.TemporaryDirectory() as tmp:
            handler = lambda: SimpleNamespace(root=Path(tmp))
            cases = (
                (OSError(errno.EACCES, "Permission denied", f"{tmp}/docs/x.md"), handler),
                (RuntimeError("cannot open /tmp/elsewhere/lock"), handler),
                (ValueError("bad id"), handler),
                (OSError(errno.EACCES, "Permission denied", "/srv/private/x"), broken),
                (RuntimeError("cannot open /srv/private/lock"), broken),
            )
            for exc, get_handler in cases:
                with self.subTest(exc=repr(exc)):
                    stream = io.StringIO()
                    with contextlib.redirect_stderr(stream):
                        expected = self.served(exc, get_handler)()
                        actual = asyncio.run(self.served_async(exc, get_handler)())
                    self.assertEqual(actual, expected)
                    self.assertEqual(actual["diagnostics"][0]["code"], "tool_unhandled_exception")
                    self.assertEqual(stream.getvalue().count("Traceback (most recent call last)"), 2)
                    self.assertIn("unhandled exception in tool probe_tool", stream.getvalue())
            with contextlib.redirect_stderr(io.StringIO()):
                messages = [asyncio.run(self.served_async(exc, get_handler)())["diagnostics"][0]["message"]
                            for exc, get_handler in cases]
        self.assertEqual(messages, ["PermissionError EACCES on docs/x.md", "RuntimeError", "ValueError: bad id",
                                    "PermissionError EACCES", "RuntimeError"])

    def test_cancellation_interrupts_and_exits_propagate_from_a_coroutine(self):
        """Wave 1zqe4 (1zqe3) AC-3: only ``Exception`` is caught."""
        import asyncio
        for exc in (asyncio.CancelledError(), KeyboardInterrupt(), SystemExit(3)):
            with self.subTest(exc=type(exc).__name__), self.assertRaises(type(exc)):
                asyncio.run(self.served_async(exc, lambda: None)())


class StaleHelperReferenceTests(unittest.TestCase):
    """Wave 1zoju (1zojt): an undeclared importer still holding a replaced
    helper after a reload is reported; the scan never breaks an install."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run("stale")

    def test_first_install_reports_nothing(self):
        """AC-1 and AC-5: nothing was evicted, so nothing is reported."""
        self.assertEqual(self.out["first_refs"], [])
        self.assertNotIn("extension_helper_stale_reference", self.out["first_codes"])

    def test_reload_reports_the_stale_module_function_class_and_instance(self):
        """AC-1, AC-3 and the AC-4 positive case."""
        self.assertEqual(self.out["reload_status"], "ok")
        self.assertEqual(self.out["refs"], [
            {"module": "acme_pkg.sub", "global": "f", "helper": "acme_h"},
            {"module": "acme_u", "global": "C", "helper": "acme_h"},
            {"module": "acme_u", "global": "acme_h", "helper": "acme_h"},
            {"module": "acme_u", "global": "f", "helper": "acme_h"},
            {"module": "acme_u", "global": "inst", "helper": "acme_h"},
        ])
        advisory = [d for d in self.out["diagnostics"] if d["code"] == "extension_helper_stale_reference"]
        self.assertEqual(len(advisory), 1, self.out["diagnostics"])
        self.assertIs(advisory[0]["advisory"], True)
        for text in ("acme_pkg.sub", "acme_u", "EXTENSION_HELPER_MODULES", "restart", "module-level"):
            self.assertIn(text, advisory[0]["message"])
        # The importer really does call stale code: the helper it serves through is the old one.
        self.assertEqual(self.out["served_value"], {"value": "h1"})

    def test_false_positive_shapes_are_not_reported_and_run_no_code(self):
        """AC-4 (1) to (6), and AC-6's dropped name."""
        reported = {(r["module"], r["global"]) for r in self.out["refs"]}
        # helper_spec holds the old helper's __spec__: import machinery under a
        # dunder name, which repair F2 does not compare.
        for name in ("holder", "made", "Nested", "mine", "DROPPED", "LIMIT", "helper_spec"):
            self.assertNotIn(("acme_u", name), reported)
        # Repair F2: a docstring added to the helper and a bumped int constant
        # report nothing in any framework module (the exact list in the reload
        # test pins that only the five real positives remain).
        self.assertEqual({module for module, _ in reported}, {"acme_u", "acme_pkg.sub"})
        self.assertFalse(any(module in {"acme_lazy", "acme_proxy"} for module, _ in reported))
        self.assertEqual(self.out["lazy_calls"], [])
        self.assertEqual(self.out["proxy_touched"], [])

    def test_a_module_that_fails_the_scan_is_skipped_with_a_class_only_advisory(self):
        """AC-6: the install succeeds, the other module is still reported."""
        skipped = [d for d in self.out["diagnostics"] if d["code"] == "extension_helper_stale_scan_skipped"]
        self.assertEqual(len(skipped), 1, self.out["diagnostics"])
        self.assertIs(skipped[0]["advisory"], True)
        self.assertIn("RuntimeError", skipped[0]["message"])
        self.assertNotIn("hostile path text", skipped[0]["message"])
        self.assertTrue(self.out["refs"])

    def test_retained_modules_are_released(self):
        """AC-1 and AC-6: released after the scan and after a failed install."""
        self.assertEqual(self.out["retained_after_scan"], 0)
        self.assertTrue(self.out["old_h_freed"])
        for label, case in self.out["failed"].items():
            with self.subTest(case=label):
                self.assertIsNotNone(case["raised"])
                self.assertEqual(case["retained"], 0)
                self.assertTrue(case["freed"])
                self.assertEqual(case["recovered"], "ok")


class StaleHelperDeclaredImporterTests(unittest.TestCase):
    """Wave 1zoju (1zojt) AC-2: declaring the importer clears the report."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run("stale_declared")

    def test_declared_importer_is_re_executed_and_not_reported(self):
        self.assertEqual(self.out["reload_status"], "ok")
        self.assertEqual([r for r in self.out["refs"] if r["module"] == "acme_u"], [])
        self.assertEqual(self.out["served_value"], {"value": "h1"})


class StaleHelperScanUnitTests(unittest.TestCase):
    """Wave 1zoju (1zojt) AC-5: with nothing evicted the scan reads nothing."""

    def test_empty_retained_list_never_reads_sys_modules(self):
        from types import SimpleNamespace
        from unittest import mock
        from server_tools_support import load_server
        srv = load_server()

        class Exploding(dict):
            def items(self):
                raise AssertionError("sys.modules was read")
            def get(self, *args):
                raise AssertionError("sys.modules was read")

        self.assertEqual(srv._EXTENSION_RETAINED_MODULES, [])
        with mock.patch.object(srv, "sys", SimpleNamespace(modules=Exploding(), path=[])):
            self.assertEqual(srv._scan_stale_helper_references(), ([], []))
        self.assertEqual(srv._empty_extension_provenance()["stale_helper_references"], [])

    def test_a_scan_wide_failure_is_reported_by_class_and_yields_nothing(self):
        """Repair F6: a failure outside the per-module guards (here resolving
        the scripts directory) returns no entries and the class name only."""
        import types as module_types
        from types import SimpleNamespace
        from unittest import mock
        from server_tools_support import load_server
        srv = load_server()

        def broken():
            raise RuntimeError("cannot resolve /private/scripts")

        retained = [("acme_old", module_types.ModuleType("acme_old"))]
        with mock.patch.object(srv, "_EXTENSION_RETAINED_MODULES", retained), \
                mock.patch.object(srv, "SCRIPTS_DIR", SimpleNamespace(resolve=broken)):
            self.assertEqual(srv._scan_stale_helper_references(), ([], ["RuntimeError"]))


class MiscasedModuleTests(unittest.TestCase):
    """Wave 1zls8 (1zltx AC-6, Requirement 10): the exact-name check under PYTHONCASEOK=1."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run("caseok", env={"PYTHONCASEOK": "1"})

    def test_a_miscased_helper_and_extension_module_are_refused(self):
        self.assertEqual(self.out["caseok"], "1")
        for label in ("helper", "module"):
            with self.subTest(case=label, find_spec_resolves=self.out["find_spec_resolves_miscased"]):
                result = self.out["cases"][label]
                self.assertIsNotNone(result["raised"], result)
                self.assertIn("has no .py source directly in", result["message"])
                self.assertIn("(no file named exactly", result["message"])
                self.assertEqual(result["served"], [])

    def test_the_exact_name_still_loads(self):
        result = self.out["cases"]["helper_exact"]
        self.assertIsNone(result["raised"], result)
        self.assertEqual(result["helpers"], ["acme_case_helper"])


class OverrideCostRecordingTests(unittest.TestCase):
    """Wave 1zls8 (1zltz): what an override of a self-recording tool adds is recorded."""

    @classmethod
    def setUpClass(cls):
        cls.stock = _run("stock")
        cls.out = _run("override_costs")

    def test_only_exempt_override_targets_get_the_delta_recorder(self):
        out = self.out
        self.assertEqual(out["deltas_installed"], ["code_outline", "wf_close_wave"])
        self.assertEqual(out["override_deltas"], ["code_outline", "wf_close_wave"])
        self.assertIn("cost", out["markers"]["wf_close_wave"])
        self.assertIn("cost", out["markers"]["code_outline"])
        self.assertEqual(self.stock["cost_pass_kwargs"], [])
        self.assertEqual(self.stock["deltas_installed"], [])

    def test_a_delegating_lifecycle_override_records_only_what_it_adds(self):
        add = self.out["close_add"]
        self.assertTrue(add["added"])
        self.assertGreater(add["expected_delta"], 0)
        self.assertEqual(add["costs"], [{"name": "wf_close_wave", "request_tokens": 0,
                                         "response_tokens": add["expected_delta"], "derived_artifact_tokens": 0}])
        self.assertEqual(self.out["close_same"]["costs"], [])

    def test_the_core_recording_is_unchanged_by_the_override(self):
        out = self.out
        self.assertEqual(out["direct_core"]["costs"], [])
        self.assertTrue(out["direct_core"]["workflow"])
        for label in ("close_add", "close_same"):
            with self.subTest(case=label):
                self.assertEqual(out[label]["workflow"], out["direct_core"]["workflow"])

    def test_a_delegating_retrieval_override_records_only_what_it_adds(self):
        add = self.out["outline_add"]
        self.assertTrue(add["added"])
        self.assertEqual(add["status"], "ok")
        self.assertGreater(add["expected_delta"], 0)
        self.assertEqual(add["costs"], [{"name": "code_outline", "request_tokens": 0,
                                         "response_tokens": add["expected_delta"], "derived_artifact_tokens": 0}])
        self.assertEqual(self.out["outline_same"]["costs"], [])

    def test_an_override_that_never_delegates_records_its_request_and_response(self):
        out = self.out
        self.assertEqual(out["close_self"]["costs"], [{"name": "wf_close_wave", "request_tokens": out["close_self_request"],
                                                       "response_tokens": out["close_self_response"],
                                                       "derived_artifact_tokens": 0}])
        self.assertEqual(out["close_self"]["workflow"], [])
        self.assertEqual(out["outline_self"]["costs"], [{"name": "code_outline", "request_tokens": out["outline_self_request"],
                                                         "response_tokens": out["outline_self_response"],
                                                         "derived_artifact_tokens": 0}])

    def test_a_non_exempt_core_inside_the_scope_counts_as_the_override_answering(self):
        # Its core recorded nothing, so the whole call is the single event.
        costs = self.out["close_non_exempt_core"]["costs"]
        self.assertEqual(len(costs), 1, costs)
        self.assertGreater(costs[0]["request_tokens"], 0)
        self.assertGreater(costs[0]["response_tokens"], 0)

    def test_a_non_exempt_override_records_as_before(self):
        current, direct = self.out["current"], self.out["current_direct"]
        self.assertEqual(len(current["costs"]), 1, current)
        self.assertEqual(direct["costs"], [{"name": "wf_current_wave", "request_tokens": direct["request"],
                                            "response_tokens": direct["response"]}])

    def test_recording_is_observational(self):
        out = self.out
        self.assertEqual(out["failing_telemetry"], {"status": "ok", "added": True})
        self.assertEqual(out["checkpoint_outline"], {"status": "ok", "added": True, "costs": []})

    def test_the_guard_refuses_a_locked_exempt_override_before_its_body(self):
        refused = self.out["checkpoint_close"]
        self.assertEqual(refused["codes"], ["error", "upgrade_in_progress"])
        self.assertEqual(refused["body_ran"], [])
        self.assertEqual(refused["costs"], [])

    def test_the_override_runs_under_the_lock_after_the_core_call(self):
        self.assertEqual(self.out["lock_after_core"], {"hold_registered": True, "other_process": "busy"})
        self.assertEqual(self.out["lock_after_return"], "acquired")

    def test_a_late_registration_failure_clears_the_installed_deltas(self):
        self.assertEqual(self.out["late_failure"], "raised")
        self.assertEqual(self.out["deltas_after_late_failure"], [])

    def test_the_stage_call_count_rises_only_by_a_real_addition(self):
        calls = self.out["calls"]
        self.assertGreater(calls["direct"]["review"], 0, calls)
        self.assertEqual(calls["same"], calls["direct"], calls)
        self.assertEqual(calls["add"]["review"], calls["direct"]["review"] + 1, calls)
        self.assertEqual(calls["add"]["total"], calls["direct"]["total"] + 1, calls)


class MeasuredCoreHandlerTests(unittest.TestCase):
    """Wave 1zls8 (1zltz AC-3): the measuring wrapper core_handler returns."""

    def setUp(self):
        from types import SimpleNamespace
        from unittest import mock
        from server_tools_support import load_server
        self.impl = load_server()
        self.result = {"status": "ok", "data": {"value": "x" * 40}}
        self.error = ValueError("core failed")

        def exempt(**kwargs):
            if kwargs.get("fail"):
                raise self.error
            return self.result

        table = {"code_outline": SimpleNamespace(fn=exempt), "wf_current_wave": SimpleNamespace(fn=lambda **k: {"n": 1})}
        patcher = mock.patch.object(self.impl.mcp_tool_extensions, "EXTENSION_OVERRIDES",
                                    {"m": ("code_outline", "wf_current_wave")})
        patcher.start()
        self.addCleanup(patcher.stop)
        surface = self.impl._extension_staging_surface(table)
        surface.wf_registering = "m"
        self.exempt = surface.core_handler("code_outline")
        self.non_exempt = surface.core_handler("wf_current_wave")
        surface.wf_registering = None

    def test_the_result_is_the_core_object_and_exceptions_propagate(self):
        self.assertIs(self.exempt(), self.result)
        with self.assertRaises(ValueError) as raised:
            self.exempt(fail=True)
        self.assertIs(raised.exception, self.error)

    def test_no_active_scope_only_calls_through(self):
        self.assertIsNone(self.impl._OVERRIDE_COST_SCOPE.get())
        self.assertIs(self.exempt(), self.result)
        self.assertIsNone(self.impl._OVERRIDE_COST_SCOPE.get())

    def test_only_a_self_recording_core_adds_to_the_innermost_scope(self):
        var = self.impl._OVERRIDE_COST_SCOPE
        outer, inner = [], []
        outer_token = var.set(outer)
        try:
            self.non_exempt()
            self.assertEqual(outer, [])
            inner_token = var.set(inner)
            try:
                self.exempt()
            finally:
                var.reset(inner_token)
            self.assertEqual(inner, [self.impl._response_size_tokens(self.result)])
            self.assertEqual(outer, [])
            self.exempt()
            self.assertEqual(len(outer), 1)
        finally:
            var.reset(outer_token)


class ExtensionLifecycleToolTests(unittest.TestCase):
    """Wave 1zimf (1zimo AC-3 to AC-7): lock and credit for declared extension tools."""

    @classmethod
    def setUpClass(cls):
        cls.out = _run("lifecycle")
        cls.stock = _run("stock")

    def test_only_the_declared_tool_and_its_aliases_take_the_lock(self):
        self.assertEqual(self.out["locked"], {"acme_record": True, "acme_free": False, "acme_make": False})
        for name in ("acme_record", "acme_record_alias", "acme_record_mapped"):
            self.assertIn("lock", self.out["markers"][name], name)
        for name in ("acme_free", "acme_make", "acme_make_free"):
            self.assertNotIn("lock", self.out["markers"][name], name)
            self.assertIn("cost", self.out["markers"][name], name)

    def test_busy_while_another_process_holds_the_lock(self):
        held = self.out["held_record"]
        self.assertEqual(held["codes"], ["error", "lifecycle_mutation_locked"])
        self.assertEqual(held["data"]["tool"], "acme_record")
        self.assertIs(held["data"]["busy"], True)
        self.assertEqual(self.out["held_alias"], ["error", "lifecycle_mutation_locked"])
        self.assertEqual(self.out["held_mapped"], ["error", "lifecycle_mutation_locked"])
        self.assertEqual(self.out["held_free"], ["ok"])
        self.assertEqual(self.out["free_record"], {"note": "n", "seen": None})
        self.assertEqual(self.out["free_mapped"], {"text": "m", "seen": None})

    def test_the_hold_is_registered_and_reentry_is_refused_without_opening_the_file(self):
        seen = self.out["observed"]
        self.assertTrue(seen["hold_registered"], seen)
        # Wave 1zls7 (1zlts): a served locked tool called from this body is a
        # same-thread re-entry, not another session's contention.
        self.assertEqual(seen["served_codes"], ["error", "lifecycle_lock_reentry"])
        self.assertEqual(seen["reentry"], "LifecycleLockBusy")
        self.assertFalse(seen["lock_file_opened"], seen)
        self.assertEqual(seen["other_process"], "busy")
        self.assertIsNone(self.out["hold_after"])
        self.assertEqual(self.out["other_after"], "acquired")

    def test_an_unhandled_reentry_returns_reentry_and_keeps_the_hold_until_return(self):
        raised = self.out["reraised"]
        self.assertTrue(raised.get("raised"), raised)
        self.assertEqual(raised["other_process_while_raising"], "busy")
        # Wave 1zls7 (1zlts): a body-raised re-entry is reported as such.
        self.assertEqual(raised["codes"], ["error", "lifecycle_lock_reentry"])
        self.assertEqual(raised["data"]["tool"], "acme_record")
        self.assertIsNone(self.out["hold_after_reraise"])
        self.assertEqual(self.out["other_after_reraise"], "acquired")

    def test_crediting_inside_the_lock_never_releases_it(self):
        self.assertEqual(self.out["lock_while_crediting_lock_file"], ["busy"])

    def test_declared_artifact_field_credits_by_the_core_contract(self):
        credit = self.out["credit"]
        ok = credit["ok"]
        self.assertEqual(ok["name"], "acme_make")
        self.assertGreater(ok["credit"], 0)
        self.assertEqual(ok["credit"], ok["core_contract"])
        self.assertTrue(ok["event_id"].startswith("artifact:"), ok)
        # A replay of an identical request and response carries the same
        # replay identity, which the store records once.
        self.assertEqual(credit["replay"]["event_id"], ok["event_id"])
        self.assertEqual(credit["replay"]["credit"], ok["credit"])
        for label in ("error", "outside", "missing", "undeclared"):
            with self.subTest(case=label):
                self.assertEqual(credit[label]["credit"], 0, credit[label])
        self.assertEqual(credit["error"]["status"], "error")
        self.assertEqual(credit["undeclared"]["name"], "acme_make_free")
        # One file named several ways (duplicate, ./, .., symlink) is credited once.
        self.assertEqual(credit["single"]["artifacts"], 1)
        self.assertEqual(credit["duplicate"]["artifacts"], 1)
        self.assertGreater(credit["duplicate"]["credit"], 0)
        self.assertEqual(credit["duplicate"]["credit"], credit["duplicate"]["core_contract"])

    def test_core_collections_are_unchanged(self):
        stock_locked = sorted(n for n, labels in self.stock["markers"].items() if "lock" in labels)
        self.assertEqual(self.out["lock_tools"], self.out["lock_tools_after"])
        self.assertNotIn("acme_record", self.out["lock_tools_after"])
        self.assertEqual(len(self.out["lock_tools_after"]), 12)  # wave 1zlu1 added wf_close_change
        self.assertTrue(set(stock_locked) <= set(self.out["lock_tools_after"]))
        self.assertNotIn("acme_make", self.out["artifact_extractors_after"])
        self.assertEqual(self.out["artifact_extractors"], self.out["artifact_extractors_after"])
        self.assertEqual(self.out["installed_lock_and_credit"],
                         [["acme_record"], {"acme_make": "written", "acme_record": "note"}])

    def test_provenance_reports_the_declarations(self):
        declaration = self.out["extensions"]["declaration"]
        self.assertEqual(declaration["lifecycle_tools"], ["acme_record"])
        self.assertEqual(declaration["artifact_path_fields"], {"acme_make": "written", "acme_record": "note"})
        self.assertEqual(list(declaration["artifact_path_fields"]), ["acme_make", "acme_record"])
        stock = self.stock["extensions"]["declaration"]
        self.assertEqual(stock["lifecycle_tools"], [])
        self.assertEqual(stock["artifact_path_fields"], {})

    def test_reload_rebuilds_the_lock_pass(self):
        self.assertEqual(self.out["reload_status"], "ok")
        self.assertEqual(self.out["reload_held_record"], ["error", "lifecycle_mutation_locked"])
        self.assertEqual(self.out["reload_held_free"], ["ok"])

    def test_reload_after_dropping_the_declarations_stops_lock_and_credit(self):
        self.assertEqual(self.out["dropped_reload_status"], "ok")
        self.assertEqual(self.out["dropped_installed"], [[], {}])
        self.assertEqual(self.out["dropped_declaration"]["lifecycle_tools"], [])
        self.assertEqual(self.out["dropped_declaration"]["artifact_path_fields"], {})
        self.assertEqual(self.out["dropped_held_record"], ["ok"])
        self.assertEqual(self.out["dropped_credit"], [0])


class ExtensionRefusalTests(unittest.TestCase):
    """AC-3: every fail-closed case refuses and serves nothing."""

    EXPECTED = {
        "missing_module": "has no .py source",
        "outside_scripts": "outside",
        "already_imported": "already imported",
        # Wave 1zls8 (1zltx AC-4, AC-6).
        "framework_script_name": "module 'record_paths' matches the framework script record_paths.py",
        "helper_framework_script": "helper module 'lifecycle_lock' matches the framework script lifecycle_lock.py",
        "helper_outside_scripts": "outside",
        "helper_miscased": "(no file named exactly Acme_Helper.py)",
        "helper_already_imported": "'plain_imported' collides with a module the server already imported",
        "helper_lazy_truthy": "'lazy_truthy' collides with a module the server already imported",
        "module_lazy_truthy": "'lazy_truthy' collides with a module the server already imported",
        "helper_out_of_order": "'helper_second' collides with a module the server already imported",
        "helper_import_raises": "'helper_raises' failed to import",
        "helper_missing": "has no .py source",
        "helper_also_module": "helper module 'acme_tools' is also declared in EXTENSION_MODULES",
        "stdlib_name": "standard-library",
        "reserved_name": "framework or standard-library",
        "no_register": "defines no register",
        "register_raises": "raised during register",
        "undeclared_override": "without declaring an override",
        "runner_override": "may not override runner tool",
        "unknown_override": "which core does not register",
        "override_not_registered": "does not register it",
        "override_two_modules": "declared by both",
        "new_name_two_modules": "already staged",
        "no_prefix_registered": "without a declared extension prefix",
        "no_tier_registered": "without a declared tier",
        "tier_unregistered": "has no registered tool",
        "reserved_retired_name": "a name reserved by core _RENAMED_MCP_TOOLS",
        "reserved_collection_name": "a name reserved by core _COST_FOCUS_EXTRACTORS",
        "async_handler": "extension handlers must be synchronous",
        "unrecorded_manager_add": "outside FastMCP.add_tool",
        "unrecorded_table_write": "outside FastMCP.add_tool",
        "tampered_staging": "replaces or removes tools staged by another module",
        "resource_registered": "registers MCP resources",
        "prompt_registered": "registers MCP prompts",
        "type_changed_override": "changes the schema of parameters ['slug']",
        "parent_changed_override": "changes the schema of parameters ['parent']",
        "withdrawn_override": "removes tools it registered",
        "served_table_write": "changes the served tool table directly",
        # Wave 1z8oz.
        "alias_runner_name": "alias 'wf_reload_mcp' collides with runner tool",
        "alias_existing_name": "alias 'wf_help' collides with an existing tool",
        "alias_no_prefix": "alias 'other_help' does not start with a core or declared extension prefix",
        "alias_missing_target": "targets 'wf_not_a_tool', which is not a served tool",
        "alias_of_alias": "alias 'wf_alias_b' targets another alias 'wf_alias_a'",
        "alias_retired_name": "alias 'wf_review_evidence' is a name reserved by core _RENAMED_MCP_TOOLS",
        "hidden_without_alias": "hidden name 'wf_help' has no alias",
        "hidden_runner": "hidden name 'wf_reload_mcp' is a runner tool",
        "alias_to_replaced": "alias 'wf_alias_close' targets replaced core name 'wf_close_wave'; its core behaviour is served only under its alias_for_core",
        "alias_of_alias_for_core": "alias 'wf_alias_core' targets another alias 'wf_core_close'",
        "hidden_twice": "hidden name 'wf_help' is declared twice",
        "hide_replaced": "hidden name 'wf_close_wave' is a replaced core name",
        "replace_runner": "may not replace runner tool 'wf_reload_mcp'",
        "replace_and_override": "'wf_close_wave' is declared both as an override and as a replacement",
        "replace_bad_tier": "replacement 'wf_close_wave' declares tier 'admin'",
        "replace_alias_collides": "alias_for_core of 'wf_close_wave' 'wf_help' collides with an existing tool",
        "replace_alias_retired": "alias_for_core of 'wf_close_wave' 'wf_review_evidence' is a name reserved by core _RENAMED_MCP_TOOLS",
        "replace_open_schema": "replacement 'wf_close_wave' does not reject undeclared arguments",
        "replace_not_registered": "declares replacement 'wf_close_wave' but does not register it",
        # Wave 1zim3.
        "params_not_alias": "parameter mapping for 'wf_alias_add', which is not an alias",
        "params_unknown_key": "parameter mapping for 'wf_alias_add' has unknown keys ['pin']",
        "params_rename_unknown": "renames 'set_id', which is not a parameter of 'wf_add_change'",
        "params_rename_twice": "renames canonical parameter 'wave_id' twice",
        "params_fixed_unknown": "fixes 'force', which is not a parameter of 'wf_add_change'",
        "params_fixed_renamed": "fixes 'mode', which it also renames",
        "params_fixed_type": "fixes 'mode' to 5, which 'wf_add_change' rejects",
        "params_kwargs_name": "renames to reserved parameter name 'kwargs'",
        "params_model_prefix": "renames to reserved parameter name 'model_id'",
        "params_model_attribute": "renames to 'copy', which collides with a model attribute",
        "params_duplicate_name": "serves parameter names more than once: ['change_id']",
        "params_runner": "maps an alias of runner tool 'wf_reload_mcp'",
        "params_edit_gate": "maps an alias of edit-gate tool 'wf_open_gate'",
        "params_hide_pinned_only": "hidden name 'wf_review_wave' has only aliases with fixed parameters",
        "core_handler_undeclared": "asks for core_handler('wf_help') but does not declare it as an override",
        "params_bool_string": "fixes 'with_line_numbers' to 'false', which 'code_read' rejects",
        "params_int_string": "fixes 'limit' to '3', which 'wf_list_waves' rejects",
        "params_underscore_name": "renames to '_x', which is not a parameter name",
        "params_keyword_name": "renames to 'class', which is a Python keyword",
        "params_ext_rename_unknown": "renames 'nope', which is not a parameter of 'acme_echo'",
        "params_ext_fixed_type": "fixes 'count' to '3', which 'acme_echo' rejects",
        # Wave 1zime (1zimm).
        "params_desc_not_str": "parameter mapping for 'wf_alias_add': 'description' must be a string, not int",
        "params_desc_empty": "parameter mapping for 'wf_alias_add': 'description' is empty",
        "params_desc_blank": "parameter mapping for 'wf_alias_add': 'description' is whitespace only",
        "params_desc_too_long": "parameter mapping for 'wf_alias_add': 'description' has 16385 characters, more than 16384",
        # Wave 1zls8 (1zlty): the description rule names response_keys too.
        "params_desc_plain": "parameter mapping for 'wf_alias_add' declares 'description' without a non-empty 'rename', 'fixed' or 'response_keys'; a plain alias keeps the canonical description",
        "params_desc_empty_mappings": "parameter mapping for 'wf_alias_add' declares 'description' without a non-empty 'rename', 'fixed' or 'response_keys'",
        "params_response_keys_bad_path": "parameter mapping for 'wf_alias_get': response key path 'changes\\n' is not a dot-separated key path",
        "params_response_keys_echo": "parameter mapping for 'wf_alias_add': response key path 'wave_id' is a renamed parameter",
        # Wave 1zicq.
        "replace_downgrade": "replacement 'wf_close_wave' may not lower its tier from 'write' to 'read'",
        "override_gate": "may not override edit-gate tool 'wf_open_gate'",
        "replace_gate": "may not replace edit-gate tool 'wf_close_gate'",
        "hidden_gate": "hidden name 'wf_open_gate' is an edit-gate tool",
        # Wave 1zimf (1zimo AC-2, AC-6).
        "lifecycle_unregistered": "declared lifecycle tool 'acme_ghost' has no registered tool",
        "artifact_unregistered": "declared artifact path field for 'acme_ghost' has no registered tool",
        "lifecycle_reserved_name": "a name reserved by core _RENAMED_MCP_TOOLS",
        "lifecycle_invalid_declaration": "lifecycle tool 'acme_twin' is a read tool",
    }

    @classmethod
    def setUpClass(cls):
        cls.out = _run("fail")

    def test_each_case_refuses_with_its_cause_and_serves_nothing(self):
        cases = self.out["cases"]
        for label, needle in self.EXPECTED.items():
            with self.subTest(case=label):
                result = cases[label]
                self.assertIsNotNone(result["raised"], result)
                self.assertIn(needle, result["message"])
                self.assertEqual(result["served"], [])

    def test_a_failed_helper_install_leaves_no_declared_module_imported(self):
        # Wave 1zls8 (1zltx Requirement 5): the failure cleanup pops what the
        # install imported, including an out-of-order helper loaded unmarked.
        for label in ("helper_out_of_order", "helper_import_raises", "helper_miscased"):
            with self.subTest(case=label):
                self.assertEqual(self.out["cases"][label]["left_in_modules"], [])

    def test_a_helper_register_is_never_called_and_serves_nothing(self):
        result = self.out["cases"]["helper_with_register"]
        self.assertIsNone(result["raised"], result)
        self.assertEqual(result["register_calls"], [])
        self.assertEqual(result["helpers"], ["helper_with_register"])

    def test_refusals_name_the_public_helper(self):
        # Wave 1zimf (1zimn AC-5): both loader messages point at the public name.
        needle = "accept **kwargs and pass them to server_impl.ensure_no_extra_args"
        for label in ("replace_open_schema", "incompatible_override"):
            with self.subTest(case=label):
                self.assertIn(needle, self.out["cases"][label]["message"])
                self.assertNotIn("pass them to _ensure_no_extra_args", self.out["cases"][label]["message"])

    def test_core_prefixed_new_tool_is_served_tiered_and_wrapped(self):
        # Wave 1yyoj: extension tools may use core prefixes such as wf_.
        result = self.out["cases"]["core_prefix_new_tool"]
        self.assertIsNone(result["raised"], result)
        self.assertEqual(result["call"], {"fork": True})
        self.assertEqual(result["tier"], "read")
        self.assertIn("cost", result["markers"])
        self.assertEqual(result["parity_defects"], [])
        self.assertTrue(result["read_rule"])

    def test_registration_after_a_replacement_leaves_no_replaced_state(self):
        self.assertEqual(self.out["replaced_during"], ["wf_close_wave"])
        self.assertEqual(self.out["replaced_after_stock"], [])
        self.assertNotIn("cost", self.out["stock_again_markers"])

    def test_aliases_only_declaration_is_validated_and_served(self):
        # Wave 1z8oz AC-1: no module and no prefix, only an alias.
        result = self.out["cases"]["aliases_only_served"]
        self.assertIsNone(result["raised"], result)
        self.assertEqual(result["call"], "ok")
        self.assertTrue(result["shares_fn"])
        self.assertEqual(result["parity_defects"], [])
        self.assertTrue(result["read_rule"])

    def test_a_description_at_the_cap_is_accepted_and_served(self):
        # Wave 1zime (1zimm AC-8): 16,384 characters is within the cap.
        result = self.out["cases"]["params_desc_max_valid"]
        self.assertIsNone(result["raised"], result)
        self.assertEqual(result["description"], "y" * 16384)

    def test_a_parameter_swap_is_a_valid_mapping(self):
        # Wave 1zim3: an alias parameter may reuse a canonical name that is renamed away.
        result = self.out["cases"]["params_swap_valid"]
        self.assertIsNone(result["raised"], result)
        self.assertEqual(sorted(result["parameters"]["properties"]), ["mode", "set_id", "wave_id"])

    def test_changed_default_alone_is_call_compatible(self):
        # A different default changes behavior, not the values callers may send.
        result = self.out["cases"]["default_changed_override"]
        self.assertIsNone(result["raised"], result)

    def test_added_optional_parameter_and_custom_title_stay_call_compatible(self):
        # Extra optional parameters extend the core signature; titles are annotations.
        result = self.out["cases"]["extended_override"]
        self.assertIsNone(result["raised"], result)
        self.assertEqual(result["with_team"], {"slug": "probe", "team": "blue"})
        self.assertEqual(result["core_call"], {"slug": "probe", "team": ""})

    def test_swallowing_override_omitting_parent_is_refused_structurally(self):
        """Wave 1zlu1 (N1): a handler that swallows **kwargs still never sees
        an omitted core parameter; the outermost guard refuses the call."""
        result = self.out["cases"]["parent_swallowing_override"]
        self.assertIsNone(result["raised"], result)
        self.assertEqual(result["refused"], ["error", "unknown_arguments"])
        self.assertEqual(result["rejected"], ["parent"])
        self.assertEqual(result["calls_after_refusal"], [], "the handler must not run")
        self.assertNotIn("parent", result["plain"])
        self.assertEqual(len(result["calls_after_plain"]), 1, "a call without parent reaches the handler")
        # Wave 1zoju (1zodw): outermost but for the final render pass.
        self.assertEqual(result["markers"][-2:], ["omitted", "render"], "the guard is outermost")

    def test_incompatible_overrides_are_refused(self):
        result = self.out["cases"]["incompatible_override"]
        self.assertIsNotNone(result["raised"], result)
        self.assertIn("'wf_current_wave' does not reject undeclared arguments", result["message"])
        self.assertIn("'wf_create_wave' drops parameters ['slug']", result["message"])
        self.assertIn("'wf_help' newly requires parameters ['goal']", result["message"])
        self.assertEqual(result["served"], [])

    def test_invalid_tier_declaration_stops_the_allowlist_renderer(self):
        self.assertEqual(self.out["roster_raised"], "ExtensionDeclarationError")
        self.assertEqual(self.out["renderer_raised"], "ExtensionDeclarationError")
        self.assertEqual(self.out["settings_after"], "{}\n")


# Wave 1yyoj: every module-level assignment in scripts/ and wave_lint_lib/ whose
# string literals include a registered or retired MCP tool name, or whose value
# references an already-classified collection, classified by whether it changes
# how the server wraps, accounts, dispatches or upgrade-reconciles a tool by that
# name. A collection that names only unserved tools, or that lives inside a
# function, is outside this census; the membership invariant below keeps the
# reserved collections to served core or retired names.
RESERVED_COLLECTIONS = {
    ("wf_server/server_impl.py", "_LIFECYCLE_MUTATION_LOCK_TOOLS"),
    ("wf_server/server_impl.py", "_COST_EXEMPT_TOOLS"),
    ("wf_server/server_impl.py", "_ARTIFACT_EXTRACTORS"),
    ("wf_server/server_impl.py", "_COST_FOCUS_EXTRACTORS"),
    ("wf_server/context_efficiency_handlers.py", "_STATE_SOURCE_EXTRACTORS"),
    ("publication_control.py", "PUBLICATION_WRITER_REGISTRY"),
    ("render_platform_surfaces.py", "_RENAMED_MCP_TOOLS"),
}
# Reached only through core code passing its own literal tool name, or data
# about the roster, evaluation or configuration: no behavior for a foreign name.
NON_BEHAVIOR_COLLECTIONS = {
    ("context_efficiency.py", "LIFECYCLE_PROMPT_MAP"),
    ("graph_quality_eval.py", "RELATION_TOOL_MATRIX"),
    # Declaration validation only: names no override, replacement or hidden
    # name may target (wave 1zicq); it keys no served behaviour.
    ("mcp_tool_extensions.py", "EDIT_GATE_TOOLS"),
    # Flat script module names a declared module may not take (wave 1zls8,
    # 1zltx); "memory_backfill" is also a tool name, but these are modules.
    ("mcp_tool_extensions.py", "FRAMEWORK_SCRIPT_MODULE_NAMES"),
    ("mcp_tool_roster.py", "RUNNER_TOOLS"),
    ("mcp_tool_roster.py", "TOOL_TIERS"),
    ("reconcile_scan.py", "_CONFIG_KEY_TOOL_NAMES"),
    ("retrieval_eval.py", "TOOLS"),
    ("retrieval_eval.py", "CALL_TIMEOUT_SECONDS"),
    ("retrieval_eval.py", "OPERATOR_REVIEW_P95_MS"),
    ("server.py", "_RELOAD_SURVIVOR_TOOLS"),
    # Module names reloaded by the upgrade memory hook; "memory_backfill" is
    # also a tool name, but this tuple selects modules, not tools (wave 1zeyo).
    ("upgrade_extensions.py", "_MEMORY_BOOTSTRAP_MODULES"),
    ("wf_server/server_impl.py", "CODE_SEARCH_SUBSTRATE_SOURCES"),
    ("wf_server/server_impl.py", "CODE_ASK_SUBSTRATE_SOURCES"),
    ("wf_server/server_impl.py", "_CONTEXT_RETRIEVAL_TOOLS"),
    ("wf_server/server_impl.py", "_INDEXED_CONTEXT_TOOLS"),
    ("wf_server/server_impl.py", "_REFERENCE_ONLY_GRAPH_TOOLS"),
    ("wf_server/server_impl.py", "_LIFECYCLE_CONTEXT_STAGES"),
    ("wf_server/server_impl.py", "_TRACKING_CONTEXT_TOOLS"),
    # Override compatibility only: core parameters an override may omit
    # (wave 1zlu1, F3); it reserves no name and keys no served behaviour.
    ("wf_server/server_impl.py", "_OVERRIDE_OMITTABLE_CORE_PARAMETERS"),
    ("upgrade_extensions.py", "_CONFIG_KEY_RENAMES"),
    ("wave_lint_lib/constants.py", "WORKFLOW_REQUIRED_KEYS"),
}
# Built from a classified collection, so they hold the same names: each maps to
# its source and is covered by the source's classification.
DERIVED_COLLECTIONS = {
    ("graph_quality_eval.py", "SCORED_RELATIONS"): "RELATION_TOOL_MATRIX",
    ("publication_control.py", "_BY_TOOL"): "PUBLICATION_WRITER_REGISTRY",
    ("publication_control.py", "_BY_NATIVE_PRODUCER"): "PUBLICATION_WRITER_REGISTRY",
    ("reconcile_scan.py", "RENAMED_TOOLS"): "_RENAMED_MCP_TOOLS",
    ("reconcile_scan.py", "_RENAMED_ALT_ALL"): "RENAMED_TOOLS",
    ("reconcile_scan.py", "_RENAMED_ALT_BARE"): "RENAMED_TOOLS",
    ("reconcile_scan.py", "_TOOL_BARE_PATTERN"): "_RENAMED_ALT_BARE",
    ("reconcile_scan.py", "_TOOL_MCP_PATTERN"): "_RENAMED_ALT_ALL",
}


def _tool_name_collections() -> set[tuple[str, str]]:
    import ast
    import mcp_tool_roster
    import render_platform_surfaces
    names = set(mcp_tool_roster.TOOL_TIERS) | set(render_platform_surfaces._RENAMED_MCP_TOOLS)
    classified = {
        name for _file, name in RESERVED_COLLECTIONS | NON_BEHAVIOR_COLLECTIONS | set(DERIVED_COLLECTIONS)
    }
    found: set[tuple[str, str]] = set()
    paths = framework_source_files() + sorted((SCRIPTS / "wave_lint_lib").glob("*.py"))
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            target_names = [t.id for t in targets if isinstance(t, ast.Name)]
            if not target_names:
                continue
            literals = {
                n.value for n in ast.walk(node.value)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
            }
            refs = {n.id for n in ast.walk(node.value) if isinstance(n, ast.Name)}
            refs |= {n.attr for n in ast.walk(node.value) if isinstance(n, ast.Attribute)}
            if literals & names or (refs & classified) - {target_names[0]}:
                rel = path.relative_to(SCRIPTS).as_posix()
                if rel == "mcp_tool_extensions.py" and target_names[0] in DECLARATION_CONSTANTS:
                    # A distribution's own declaration names tools by design;
                    # DeclarationConstantCensusTests classifies these (change 1zim4).
                    continue
                found.add((rel, target_names[0]))
    return found


class OverrideOmittableParameterTests(unittest.TestCase):
    """Wave 1zlu1 (F3, reverification nit 1): the compatibility check itself."""

    @classmethod
    def setUpClass(cls):
        from server_tools_support import load_server
        try:
            from mcp.server.fastmcp import FastMCP
        except ImportError:
            raise unittest.SkipTest("mcp package not installed")
        cls.impl = load_server()
        mcp = FastMCP("omittable")
        cls.impl.register_mcp_surface(mcp, lambda: None)
        cls.core = mcp._tool_manager._tools["wf_create_wave"]

    def staged(self, mutate):
        import copy
        from types import SimpleNamespace
        schema = copy.deepcopy(self.core.parameters)
        mutate(schema)
        return SimpleNamespace(parameters=schema)

    def test_an_omitted_parent_is_accepted_and_reported(self):
        staged = self.staged(lambda s: s["properties"].pop("parent"))
        self.assertIsNone(self.impl._override_compatibility_problem("wf_create_wave", self.core, staged))
        self.assertEqual(self.impl._override_omitted_core_parameters("wf_create_wave", self.core, staged), ["parent"])

    def test_a_declared_parent_with_another_schema_is_refused(self):
        def mutate(schema):
            schema["properties"]["parent"] = {"default": 0, "title": "Parent", "type": "integer"}
        staged = self.staged(mutate)
        self.assertEqual(self.impl._override_omitted_core_parameters("wf_create_wave", self.core, staged), [])
        self.assertEqual(self.impl._override_compatibility_problem("wf_create_wave", self.core, staged),
                         "override 'wf_create_wave' changes the schema of parameters ['parent']")

    def test_omission_is_only_for_listed_parameters(self):
        staged = self.staged(lambda s: s["properties"].pop("mode"))
        self.assertEqual(self.impl._override_compatibility_problem("wf_create_wave", self.core, staged),
                         "override 'wf_create_wave' drops parameters ['mode']")


class ReservedNameCensusTests(unittest.TestCase):
    """Every tool-name collection is classified; reserved ones are refused."""

    def test_every_tool_name_collection_is_classified(self):
        found = _tool_name_collections()
        known = RESERVED_COLLECTIONS | NON_BEHAVIOR_COLLECTIONS | set(DERIVED_COLLECTIONS)
        unclassified = found - known
        self.assertEqual(unclassified, set(), "classify new tool-name collections as reserved, non-behavior or derived")
        stale = known - found
        self.assertEqual(stale, set(), "remove classifications for collections that no longer exist")

    def test_every_derived_collection_maps_to_a_classified_source(self):
        classified = {
            name for _file, name in RESERVED_COLLECTIONS | NON_BEHAVIOR_COLLECTIONS | set(DERIVED_COLLECTIONS)
        }
        orphans = {key: src for key, src in DERIVED_COLLECTIONS.items() if src not in classified}
        self.assertEqual(orphans, {})

    def test_reserved_collections_hold_only_served_or_retired_names(self):
        from server_tools_support import load_server
        import mcp_tool_roster
        impl = load_server()
        served = set(mcp_tool_roster.TOOL_TIERS)
        collections = impl._reserved_tool_name_collections()
        retired = collections.pop("_RENAMED_MCP_TOOLS")
        self.assertTrue(retired)
        self.assertEqual(retired & served, set(), "a retired name is served again")
        for label, members in collections.items():
            with self.subTest(collection=label):
                self.assertTrue(members, f"{label} is empty, so this check would pass vacuously")
                self.assertEqual(members - served, set(), f"{label} names a tool core does not serve")

    def test_registration_reserves_exactly_the_reserved_collections(self):
        from server_tools_support import load_server
        impl = load_server()
        labels = set(impl._reserved_tool_name_collections())
        expected = {name for _file, name in RESERVED_COLLECTIONS}
        expected = {"publication_control.PUBLICATION_WRITER_REGISTRY" if n == "PUBLICATION_WRITER_REGISTRY" else n for n in expected}
        self.assertEqual(labels, expected)


# Every distribution-edited declaration constant: the helpers below save and
# restore exactly these, the refusal driver resets them, and declared() counts
# each. The census test keeps this tuple equal to the module's EXTENSION_* names.
# The shared base-declaration helper's names (change 1zim4 promoted them to
# declaration_support, so the helper and this census use one list).
from declaration_support import DECLARATION_CONSTANTS, apply_base_declaration, base_declaration_source  # noqa: E402


class DeclarationConstantCensusTests(unittest.TestCase):
    """Wave 1zim3 AC-5: a new declaration constant cannot be missed by the save/restore helpers."""

    def test_every_declaration_constant_is_classified(self):
        import ast
        tree = ast.parse((SCRIPTS / "mcp_tool_extensions.py").read_text(encoding="utf-8"))
        names = set()
        for node in tree.body:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
            names |= {t.id for t in targets if isinstance(t, ast.Name) and t.id.startswith("EXTENSION_")}
        self.assertEqual(names, set(DECLARATION_CONSTANTS))

    def test_the_refusal_driver_resets_every_declaration_constant(self):
        start = _DRIVER.index("empty = dict(")
        empty_line = _DRIVER[start:_DRIVER.index(")\n", _DRIVER.index("EXTENSION_REPLACEMENTS", start))]
        for name in DECLARATION_CONSTANTS:
            self.assertIn(f"{name}=", empty_line, name)


class DeclarationValidationTests(unittest.TestCase):
    """Pure helper coverage for the stdlib declaration module."""

    def setUp(self):
        import mcp_tool_extensions
        self.ext = mcp_tool_extensions
        # Each test declares on the shipped empty base, never on the ambient
        # declaration a distribution ships (change 1zim4).
        apply_base_declaration(self)

    def test_core_prefixes_are_the_server_prefix_contract(self):
        from server_tools_support import load_server
        impl = load_server()
        # load_server purges and re-imports the declaration module; compare
        # against the object the server itself imported.
        self.assertIs(impl.MCP_TOOL_PREFIXES, impl.mcp_tool_extensions.CORE_TOOL_PREFIXES)

    def test_valid_declaration_has_no_problems(self):
        self.ext.EXTENSION_MODULES = ("acme_tools",)
        self.ext.EXTENSION_TOOL_PREFIXES = ("acme_",)
        self.ext.EXTENSION_TOOL_TIERS = {"acme_echo": "read"}
        self.ext.EXTENSION_OVERRIDES = {"acme_tools": ("wf_help",)}
        self.assertEqual(self.ext.declaration_problems(core_tools={"wf_help"}, runner_tools={"wf_reload_mcp"}), [])

    def test_bad_tier_value_and_undeclared_override_module(self):
        self.ext.EXTENSION_MODULES = ("acme_tools",)
        self.ext.EXTENSION_TOOL_PREFIXES = ("acme_",)
        self.ext.EXTENSION_TOOL_TIERS = {"acme_echo": "admin"}
        self.ext.EXTENSION_OVERRIDES = {"other": ("wf_help",)}
        problems = " ".join(self.ext.declaration_problems(core_tools={"wf_help"}, runner_tools=set()))
        self.assertIn("declares tier 'admin'", problems)
        self.assertIn("undeclared module 'other'", problems)

    def test_each_new_constant_alone_makes_the_declaration_declared(self):
        # Wave 1z8oz: an aliases-only or hide-only declaration is validated, not ignored.
        for key, value in (
            ("EXTENSION_HELPER_MODULES", ("acme_shared",)),
            ("EXTENSION_TOOL_ALIASES", {"wf_alias_help": "wf_help"}),
            ("EXTENSION_HIDDEN_TOOLS", ("wf_help",)),
            ("EXTENSION_REPLACEMENTS", {"m": {"wf_help": {"alias_for_core": "wf_core_help"}}}),
            ("EXTENSION_TOOL_PARAMETERS", {"wf_alias_help": {"fixed": {"goal": "x"}}}),
        ):
            with self.subTest(key=key):
                for name in DECLARATION_CONSTANTS:
                    setattr(self.ext, name, type(getattr(self.ext, name))())
                setattr(self.ext, key, value)
                self.assertTrue(self.ext.declared())

    def test_served_name_map_prefers_the_first_alias_and_the_replacement(self):
        self.ext.EXTENSION_MODULES = ("m",)
        self.ext.EXTENSION_TOOL_ALIASES = {"wf_first": "wf_help", "wf_second": "wf_help", "wf_other": "wf_current_wave"}
        self.ext.EXTENSION_REPLACEMENTS = {"m": {"wf_close_wave": {"alias_for_core": "wf_core_close"}}}
        self.assertEqual(self.ext.served_name_map(), {
            "wf_help": "wf_first", "wf_current_wave": "wf_other", "wf_close_wave": "wf_core_close",
        })
        core = {"wf_help", "wf_current_wave", "wf_close_wave"}
        self.assertEqual(self.ext.declaration_problems(core_tools=core, runner_tools={"wf_reload_mcp"}), [])

    def test_served_name_map_skips_pinned_aliases(self):
        # Wave 1zim3: a name-only hint never selects a pinned alias.
        self.ext.EXTENSION_TOOL_ALIASES = {"wf_pinned": "wf_help", "wf_renamed": "wf_help", "wf_only_pinned": "wf_current_wave"}
        self.ext.EXTENSION_TOOL_PARAMETERS = {
            "wf_pinned": {"fixed": {"goal": "x"}},
            "wf_renamed": {"rename": {"topic": "goal"}},
            "wf_only_pinned": {"fixed": {"scope": "x"}},
        }
        self.assertEqual(self.ext.served_name_map(), {"wf_help": "wf_renamed"})
        self.assertEqual(self.ext.pinned_aliases(), frozenset({"wf_pinned", "wf_only_pinned"}))
        core = {"wf_help", "wf_current_wave"}
        self.assertEqual(self.ext.declaration_problems(core_tools=core, runner_tools=set()), [])
        self.ext.EXTENSION_HIDDEN_TOOLS = ("wf_help",)
        self.assertEqual(self.ext.declaration_problems(core_tools=core, runner_tools=set()), [])
        self.ext.EXTENSION_HIDDEN_TOOLS = ("wf_current_wave",)
        self.assertEqual(self.ext.declaration_problems(core_tools=core, runner_tools=set()),
                         ["hidden name 'wf_current_wave' has only aliases with fixed parameters"])

    def test_served_name_map_prefers_a_plain_alias(self):
        # Wave 1zim3 repair: a plain alias is preferred over an unpinned mapped one.
        self.ext.EXTENSION_TOOL_ALIASES = {"wf_renamed": "wf_help", "wf_plain": "wf_help"}
        self.ext.EXTENSION_TOOL_PARAMETERS = {"wf_renamed": {"rename": {"topic": "goal"}}}
        self.assertEqual(self.ext.served_name_map(), {"wf_help": "wf_plain"})

    def test_the_roster_validates_parameter_mappings_and_tiers_aliases(self):
        import mcp_tool_roster
        self.ext.EXTENSION_TOOL_ALIASES = {"wf_alias_add": "wf_add_change"}
        self.ext.EXTENSION_TOOL_PARAMETERS = {"wf_alias_add": {"rename": {"kwargs": "wave_id"}}}
        with self.assertRaises(self.ext.ExtensionDeclarationError):
            mcp_tool_roster.all_tool_tiers()
        self.ext.EXTENSION_TOOL_PARAMETERS = {"wf_alias_add": {"rename": {"set_id": "wave_id"}}}
        self.assertEqual(mcp_tool_roster.all_tool_tiers()["wf_alias_add"], mcp_tool_roster.TOOL_TIERS["wf_add_change"])

    def test_a_replacement_may_not_lower_a_write_tool_to_read(self):
        # Wave 1zicq: same tier and read-to-write stay allowed.
        core = {"wf_close_wave", "wf_help"}
        tiers = {"wf_close_wave": "write", "wf_help": "read"}
        self.ext.EXTENSION_MODULES = ("m",)
        self.ext.EXTENSION_REPLACEMENTS = {"m": {"wf_close_wave": {"alias_for_core": "wf_core_close", "tier": "read"}}}
        problems = self.ext.declaration_problems(core_tools=core, runner_tools=set(), core_tiers=tiers)
        self.assertEqual(problems, ["replacement 'wf_close_wave' may not lower its tier from 'write' to 'read'"])
        self.ext.EXTENSION_REPLACEMENTS = {"m": {
            "wf_close_wave": {"alias_for_core": "wf_core_close", "tier": "write"},
            "wf_help": {"alias_for_core": "wf_core_help", "tier": "write"},
        }}
        self.assertEqual(self.ext.declaration_problems(core_tools=core, runner_tools=set(), core_tiers=tiers), [])

    def test_the_roster_refuses_a_downgrade_and_keeps_allowed_tiers(self):
        import mcp_tool_roster
        self.ext.EXTENSION_MODULES = ("m",)
        self.ext.EXTENSION_REPLACEMENTS = {"m": {"wf_close_wave": {"alias_for_core": "wf_core_close", "tier": "read"}}}
        with self.assertRaises(self.ext.ExtensionDeclarationError) as raised:
            mcp_tool_roster.all_tool_tiers()
        self.assertIn("may not lower its tier", str(raised.exception))
        self.ext.EXTENSION_REPLACEMENTS = {"m": {"wf_help": {"alias_for_core": "wf_core_help", "tier": "write"}}}
        tiers = mcp_tool_roster.all_tool_tiers()
        self.assertEqual(tiers["wf_help"], "write")
        self.assertEqual(tiers["wf_core_help"], mcp_tool_roster.TOOL_TIERS["wf_help"])

    def test_edit_gate_tools_may_be_aliased_but_not_overridden_replaced_or_hidden(self):
        core = {"wf_open_gate", "wf_close_gate", "wf_help"}
        self.ext.EXTENSION_MODULES = ("m",)
        self.ext.EXTENSION_TOOL_ALIASES = {"wf_alias_open_gate": "wf_open_gate"}
        self.assertEqual(self.ext.declaration_problems(core_tools=core, runner_tools=set()), [])
        self.ext.EXTENSION_OVERRIDES = {"m": ("wf_open_gate",)}
        self.ext.EXTENSION_REPLACEMENTS = {"m": {"wf_close_gate": {"alias_for_core": "wf_core_close_gate"}}}
        self.ext.EXTENSION_HIDDEN_TOOLS = ("wf_open_gate",)
        problems = self.ext.declaration_problems(core_tools=core, runner_tools=set())
        self.assertIn("module 'm' may not override edit-gate tool 'wf_open_gate'", problems)
        self.assertIn("module 'm' may not replace edit-gate tool 'wf_close_gate'", problems)
        self.assertIn("hidden name 'wf_open_gate' is an edit-gate tool", problems)
        self.assertEqual(self.ext.EDIT_GATE_TOOLS, frozenset({"wf_open_gate", "wf_close_gate"}))

    def test_alias_targets_may_be_extension_tools_but_not_unknown_kinds(self):
        self.ext.EXTENSION_MODULES = ("m",)
        self.ext.EXTENSION_TOOL_PREFIXES = ("acme_",)
        self.ext.EXTENSION_TOOL_TIERS = {"acme_echo": "read"}
        self.ext.EXTENSION_TOOL_ALIASES = {"acme_say": "acme_echo"}
        self.assertEqual(self.ext.declaration_problems(core_tools={"wf_help"}, runner_tools=set()), [])
        self.ext.EXTENSION_REPLACEMENTS = {"m": {"wf_help": {"alias_for_core": "acme_core_help", "extra": 1}}}
        problems = " ".join(self.ext.declaration_problems(core_tools={"wf_help"}, runner_tools=set()))
        self.assertIn("has unknown keys ['extra']", problems)


class RosterReloadPurgeTests(unittest.TestCase):
    """Wave 1zls8 delivery repair (N1): a server reload purges the roster with
    the declaration module, so a roster imported first never validates an
    evicted declaration."""

    def test_a_roster_imported_before_a_server_load_follows_the_live_declaration(self):
        from unittest import mock
        from server_tools_support import load_server
        import mcp_tool_roster  # noqa: F401  (imported before the reload, as an earlier test would)
        load_server()
        import mcp_tool_extensions as ext_now
        import mcp_tool_roster as roster_now
        self.assertIs(roster_now.mcp_tool_extensions, ext_now)
        with mock.patch.object(ext_now, "EXTENSION_TOOL_ALIASES", {"wf_alias_add": "wf_add_change"}), \
                mock.patch.object(ext_now, "EXTENSION_TOOL_PARAMETERS", {"wf_alias_add": {"rename": {"kwargs": "wave_id"}}}):
            with self.assertRaises(ext_now.ExtensionDeclarationError):
                roster_now.all_tool_tiers()


class ResponseKeyDeclarationTests(unittest.TestCase):
    """Wave 1zls8 (1zlty AC-1): the response_keys declaration checks."""

    CORE = {"wf_get_change", "wf_add_change"}
    RUNNER = {"wf_reload_mcp"}

    def setUp(self):
        import mcp_tool_extensions
        self.ext = mcp_tool_extensions
        apply_base_declaration(self)
        self.ext.EXTENSION_TOOL_ALIASES = {"wf_alias_get": "wf_get_change"}

    def problems(self, spec):
        self.ext.EXTENSION_TOOL_PARAMETERS = {"wf_alias_get": spec}
        return self.ext.declaration_problems(core_tools=self.CORE, runner_tools=self.RUNNER)

    def test_valid_declarations(self):
        for spec in (
            {"response_keys": {"changes": "items", "changes[].id": "item_id"}},
            {"response_keys": {"a": "b", "b": "a"}},
            {"response_keys": {"changes": "items"}, "description": "Items."},
            {"rename": {"item": "change_id"}, "response_keys": {"change": "entry", "changes[].change_id": "item"}},
            {"response_keys": {".".join(["k"] * 8): "x"}},
            {"response_keys": {f"k{i}": f"n{i}" for i in range(64)}},
        ):
            with self.subTest(spec=spec):
                self.assertEqual(self.problems(spec), [])
        self.assertTrue(self.ext.declared())

    def test_each_refusal_is_reported(self):
        label = "parameter mapping for 'wf_alias_get'"
        cases = {
            "not a mapping": ({"response_keys": ["changes"]}, f"{label}: 'response_keys' must map response key paths to new key names, not list"),
            "bad syntax": ({"response_keys": {"changes..id": "x"}}, f"{label}: response key path 'changes..id' is not a dot-separated key path"),
            "trailing newline": ({"response_keys": {"changes\n": "x"}}, f"{label}: response key path 'changes\\n' is not a dot-separated key path"),
            "not a string": ({"response_keys": {5: "x"}}, f"{label}: response key path 5 is not a dot-separated key path"),
            "trailing list": ({"response_keys": {"changes[]": "x"}}, f"{label}: response key path 'changes[]' must end in a key, not '[]'"),
            "too deep": ({"response_keys": {".".join(["k"] * 9): "x"}}, f"{label}: response key path '{'.'.join(['k'] * 9)}' has 9 segments, more than 8"),
            "too many": ({"response_keys": {f"k{i}": f"n{i}" for i in range(65)}}, f"{label}: 'response_keys' has 65 entries, more than 64"),
            "not an identifier": ({"response_keys": {"changes": "new-key"}}, f"{label}: response key path 'changes' renames to 'new-key', which is not an identifier"),
            "unchanged": ({"response_keys": {"changes[].id": "id"}}, f"{label}: response key path 'changes[].id' renames 'id' to itself"),
            "static collision": ({"response_keys": {"changes[].id": "key", "changes[].path": "key"}}, f"{label}: response key paths 'changes[].id' and 'changes[].path' both rename to 'key'"),
            "echoed parameter": ({"rename": {"item": "change_id"}, "response_keys": {"change_id": "entry"}}, f"{label}: response key path 'change_id' is a renamed parameter, whose echoed key 'rename' already renames"),
            "alias parameter name": ({"rename": {"item": "change_id"}, "response_keys": {"changes": "item"}}, f"{label}: response key path 'changes' renames to 'item', an alias parameter name in 'rename'"),
        }
        for case, (spec, needle) in cases.items():
            with self.subTest(case=case):
                self.assertIn(needle, self.problems(spec))

    def test_a_nested_key_may_reuse_an_alias_parameter_name(self):
        self.assertEqual(self.problems({"rename": {"item": "change_id"}, "response_keys": {"changes[].id": "item"}}), [])

    def test_the_roster_refuses_the_same_declarations_without_the_server(self):
        from unittest import mock
        import mcp_tool_roster
        ext = mcp_tool_roster.mcp_tool_extensions
        with mock.patch.object(ext, "EXTENSION_TOOL_ALIASES", {"wf_alias_get": "wf_get_change"}):
            for spec in ({"response_keys": {"changes[]": "x"}}, {"response_keys": "changes"},
                         {"response_keys": {"changes": "items"}, "pin": {}}):
                with self.subTest(spec=spec):
                    with mock.patch.object(ext, "EXTENSION_TOOL_PARAMETERS", {"wf_alias_get": spec}):
                        with self.assertRaises(ext.ExtensionDeclarationError):
                            mcp_tool_roster.all_tool_tiers()
            with mock.patch.object(ext, "EXTENSION_TOOL_PARAMETERS", {"wf_alias_get": {"response_keys": {"changes": "items"}}}):
                self.assertIn("wf_alias_get", mcp_tool_roster.all_tool_tiers())


class HelperModuleDeclarationTests(unittest.TestCase):
    """Wave 1zls8 (1zltx AC-4, AC-7): EXTENSION_HELPER_MODULES and FRAMEWORK_SCRIPT_MODULE_NAMES."""

    CORE = {"wf_help"}
    RUNNER = {"wf_reload_mcp"}

    def setUp(self):
        import mcp_tool_extensions
        self.ext = mcp_tool_extensions
        apply_base_declaration(self)

    def problems(self, **declaration):
        for name, value in declaration.items():
            setattr(self.ext, name, value)
        return self.ext.declaration_problems(core_tools=self.CORE, runner_tools=self.RUNNER)

    def test_a_valid_helper_declaration_has_no_problems(self):
        self.assertEqual(self.problems(EXTENSION_HELPER_MODULES=("acme_shared", "acme_more"),
                                       EXTENSION_MODULES=("acme_tools",)), [])

    def test_each_helper_refusal_is_reported(self):
        cases = {
            "not an identifier": (("acme-shared",), "helper module 'acme-shared' is not a flat single-file module name"),
            "not a string": ((5,), "helper module 5 is not a flat single-file module name"),
            "non-ASCII NFD": (("acme\u0301_x",), "helper module 'acme\u0301_x' is not an ASCII module name; use ASCII letters, digits and underscores"),
            "non-ASCII NFC": (("acm\u00e9_x",), "helper module 'acm\u00e9_x' is not an ASCII module name; use ASCII letters, digits and underscores"),
            "declared twice": (("acme_shared", "acme_shared"), "helper module 'acme_shared' is declared twice"),
            "reserved": (("server_impl",), "helper module 'server_impl' collides with a framework or standard-library module"),
            "standard library": (("json",), "helper module 'json' collides with a framework or standard-library module"),
            "framework script": (("record_paths",), "helper module 'record_paths' matches the framework script record_paths.py; give it a distribution-specific name"),
            "also a module": (("acme_tools",), "helper module 'acme_tools' is also declared in EXTENSION_MODULES"),
        }
        for label, (helpers, needle) in cases.items():
            with self.subTest(case=label):
                problems = self.problems(EXTENSION_MODULES=("acme_tools",), EXTENSION_HELPER_MODULES=helpers)
                self.assertIn(needle, problems)
        for value in (["acme_shared"], "acme_shared", {"acme_shared": 1}, None):
            with self.subTest(value=value):
                self.assertEqual(self.problems(EXTENSION_HELPER_MODULES=value),
                                 [f"EXTENSION_HELPER_MODULES must be a tuple of module names, not {type(value).__name__}"])

    def test_a_non_ascii_extension_module_name_is_refused(self):
        # Wave 1zls8 delivery repair (N6b): an NFD name passes isidentifier().
        self.assertTrue("acme\u0301_x".isidentifier())
        for name in ("acme\u0301_x", "acm\u00e9_x"):
            with self.subTest(name=name):
                self.assertIn(f"module {name!r} is not an ASCII module name; use ASCII letters, digits and underscores",
                              self.problems(EXTENSION_MODULES=(name,)))

    def test_an_extension_module_naming_a_framework_script_is_refused(self):
        self.assertIn("module 'indexer' matches the framework script indexer.py; give it a distribution-specific name",
                      self.problems(EXTENSION_MODULES=("indexer",)))

    def test_the_roster_refuses_the_same_declarations_without_the_server(self):
        # Patched on the declaration module the roster itself imported, which
        # a server load in another test may have replaced in sys.modules.
        from unittest import mock
        import mcp_tool_roster
        ext = mcp_tool_roster.mcp_tool_extensions
        for modules, helpers in ((("acme_tools",), ("record_paths",)), (("acme_tools",), ["acme_shared"]),
                                 (("acme_tools",), ("json",)), (("acme_tools",), ("acme_tools",)),
                                 (("indexer",), ())):
            with self.subTest(modules=modules, helpers=helpers):
                with mock.patch.object(ext, "EXTENSION_MODULES", modules), \
                        mock.patch.object(ext, "EXTENSION_HELPER_MODULES", helpers):
                    with self.assertRaises(ext.ExtensionDeclarationError):
                        mcp_tool_roster.all_tool_tiers()
        with mock.patch.object(ext, "EXTENSION_MODULES", ()), \
                mock.patch.object(ext, "EXTENSION_HELPER_MODULES", ("acme_shared",)):
            self.assertIn("wf_help", mcp_tool_roster.all_tool_tiers())

    def test_the_framework_script_census_matches_the_scripts_directory(self):
        # The flat scripts on disk, less the modules the declaration on disk
        # lists (a distribution's own files), are exactly the framework set.
        import mcp_tool_extensions
        flat = framework_source_files(include_aliases=True)
        stems = {path.stem for path in flat if path.parent == SCRIPTS}
        self.assertEqual(
            framework_script_census_problems(SCRIPTS, mcp_tool_extensions.FRAMEWORK_SCRIPT_MODULE_NAMES, stems), []
        )

    def _census_tree(self, declaration: str = "", modules=("server", "listed_a", "listed_b")):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / "wf_server").mkdir()
        (root / "wf_server" / "handlers.py").write_text("import listed_b\n", encoding="utf-8")
        for name in modules:
            (root / f"{name}.py").write_text("import listed_a\n" if name == "server" else "", encoding="utf-8")
        from declaration_support import base_declaration_source
        (root / "mcp_tool_extensions.py").write_text(base_declaration_source() + declaration, encoding="utf-8")
        return root

    def _census(self, root, listed=("server", "listed_a", "listed_b", "mcp_tool_extensions")):
        stems = {path.stem for path in root.glob("*.py")}
        return framework_script_census_problems(root, frozenset(listed), stems)

    def test_census_stock_declaration_is_exact(self):
        root = self._census_tree()
        self.assertEqual(self._census(root), [])
        (root / "acme_render.py").write_text("", encoding="utf-8")
        self.assertEqual(self._census(root), ["unlisted flat script(s) on a stock declaration: acme_render"])

    def test_census_declared_distribution_allows_an_unimported_module_of_its_own(self):
        root = self._census_tree('EXTENSION_MODULES = ("acme_tools",)\n')
        (root / "acme_tools.py").write_text("import acme_render\n", encoding="utf-8")
        (root / "acme_render.py").write_text("", encoding="utf-8")
        self.assertEqual(self._census(root), [])

    def test_census_declared_distribution_still_requires_server_imported_modules_listed(self):
        root = self._census_tree('EXTENSION_MODULES = ("acme_tools",)\n')
        (root / "acme_tools.py").write_text("", encoding="utf-8")
        (root / "new_core.py").write_text("", encoding="utf-8")
        (root / "wf_server" / "handlers.py").write_text("import listed_b\nfrom new_core import x\n", encoding="utf-8")
        self.assertEqual(self._census(root), ["server-reachable flat script(s) not listed: new_core"])
        # A listed framework module importing it is caught the same way.
        (root / "wf_server" / "handlers.py").write_text("import listed_b\n", encoding="utf-8")
        (root / "listed_a.py").write_text("import new_core\n", encoding="utf-8")
        self.assertEqual(self._census(root), ["server-reachable flat script(s) not listed: new_core"])

    def test_census_fails_closed_on_an_unreadable_declaration(self):
        # A computed or augmented EXTENSION_* value must not drop the exact
        # stock check by reading as a distribution.
        for declaration in ('EXTENSION_MODULES = tuple(["acme_tools"])\n',
                            'EXTENSION_MODULES = ("acme_tools",)\nEXTENSION_MODULES += ("acme_more",)\n',
                            None):
            with self.subTest(declaration=declaration):
                root = self._census_tree(declaration or "")
                if declaration is None:
                    # A constant assigned only by unpacking reads as missing.
                    decl = root / "mcp_tool_extensions.py"
                    text = decl.read_text(encoding="utf-8").replace(
                        "EXTENSION_MODULES = ()", "EXTENSION_MODULES, _unused = (), 1")
                    self.assertIn("EXTENSION_MODULES, _unused", text)
                    decl.write_text(text, encoding="utf-8")
                self.assertEqual(self._census(root), [
                    "mcp_tool_extensions.py declares an EXTENSION_* constant that is not a plain literal",
                ])

    def test_census_treats_an_empty_list_as_the_stock_empty_tuple(self):
        root = self._census_tree("EXTENSION_MODULES = []\n")
        (root / "acme_render.py").write_text("", encoding="utf-8")
        self.assertEqual(self._census(root), ["unlisted flat script(s) on a stock declaration: acme_render"])

    def test_census_listed_module_missing_from_disk_fails_either_way(self):
        for declaration in ("", 'EXTENSION_MODULES = ("acme_tools",)\n'):
            with self.subTest(declaration=declaration):
                root = self._census_tree(declaration)
                if declaration:
                    (root / "acme_tools.py").write_text("", encoding="utf-8")
                (root / "listed_b.py").unlink()
                self.assertIn("listed framework script(s) missing from disk: listed_b", self._census(root))

    def test_the_stock_declaration_validates_and_ships_no_helpers(self):
        from declaration_support import SHIPPED_DECLARATION, base_declaration, declaration_profile_mismatch
        from record_layout_support import ExpectedProfile, ProfileLayer
        self.assertEqual(SHIPPED_DECLARATION["EXTENSION_HELPER_MODULES"], ())
        with base_declaration():
            self.assertEqual(self.ext.EXTENSION_HELPER_MODULES, ())
            self.assertFalse(self.ext.declared())
            self.assertEqual(self.ext.declaration_problems(core_tools=self.CORE, runner_tools=self.RUNNER), [])
        shipped = ExpectedProfile(ProfileLayer("shipped", "shipped", "the shipped defaults", {}))
        with base_declaration(EXTENSION_HELPER_MODULES=("acme_shared",)):
            problem = declaration_profile_mismatch(shipped)
        self.assertIsNotNone(problem)
        self.assertIn("mcp_tool_extensions.EXTENSION_HELPER_MODULES is", problem)


class LockAndCreditDeclarationTests(unittest.TestCase):
    """Wave 1zimf (1zimo AC-1, AC-8): EXTENSION_LIFECYCLE_TOOLS and EXTENSION_ARTIFACT_PATH_FIELDS."""

    CORE = {"wf_help", "wf_close_wave", "wf_open_gate", "wf_close_gate", "wf_current_wave"}
    RUNNER = {"wf_reload_mcp"}

    def setUp(self):
        import mcp_tool_extensions
        self.ext = mcp_tool_extensions
        apply_base_declaration(self)
        self.ext.EXTENSION_MODULES = ("m",)
        self.ext.EXTENSION_TOOL_PREFIXES = ("acme_",)
        self.ext.EXTENSION_TOOL_TIERS = {"acme_w": "write", "acme_r": "read"}

    def problems(self, **declaration):
        for name, value in declaration.items():
            setattr(self.ext, name, value)
        return self.ext.declaration_problems(core_tools=self.CORE, runner_tools=self.RUNNER)

    def test_the_stock_declaration_validates_and_ships_empty(self):
        from declaration_support import base_declaration
        with base_declaration():
            self.assertEqual(self.ext.EXTENSION_LIFECYCLE_TOOLS, ())
            self.assertEqual(self.ext.EXTENSION_ARTIFACT_PATH_FIELDS, {})
            self.assertFalse(self.ext.declared())
            self.assertEqual(self.ext.declaration_problems(core_tools=self.CORE, runner_tools=self.RUNNER), [])

    def test_a_valid_declaration_has_no_problems_and_is_declared(self):
        self.assertEqual(self.problems(EXTENSION_LIFECYCLE_TOOLS=("acme_w",),
                                       EXTENSION_ARTIFACT_PATH_FIELDS={"acme_w": "path"}), [])
        for name, value in (("EXTENSION_LIFECYCLE_TOOLS", ("acme_w",)),
                            ("EXTENSION_ARTIFACT_PATH_FIELDS", {"acme_w": "path"})):
            with self.subTest(constant=name):
                from declaration_support import base_declaration
                with base_declaration(**{name: value}):
                    self.assertTrue(self.ext.declared())

    def test_each_refusal_is_reported(self):
        self.ext.EXTENSION_OVERRIDES = {"m": ("wf_current_wave",)}
        self.ext.EXTENSION_REPLACEMENTS = {"m": {"wf_close_wave": {"alias_for_core": "acme_core_close"}}}
        self.ext.EXTENSION_TOOL_ALIASES = {"acme_alias": "acme_w"}
        cases = {
            "undeclared": ("acme_ghost", "is not a new extension tool declared in EXTENSION_TOOL_TIERS"),
            "read": ("acme_r", "is a read tool"),
            "core": ("wf_help", "is a core tool"),
            "override target": ("wf_current_wave", "is a core tool"),
            "replacement target": ("wf_close_wave", "is a core tool"),
            "alias": ("acme_alias", "is an alias"),
            "alias_for_core": ("acme_core_close", "is an alias"),
            "runner": ("wf_reload_mcp", "is a runner tool"),
            "edit gate": ("wf_open_gate", "is an edit-gate tool"),
        }
        for label, (name, needle) in cases.items():
            for constant, value, prefix in (
                ("EXTENSION_LIFECYCLE_TOOLS", (name,), f"lifecycle tool {name!r}"),
                ("EXTENSION_ARTIFACT_PATH_FIELDS", {name: "path"}, f"artifact path field for {name!r}"),
            ):
                with self.subTest(case=label, constant=constant):
                    self.ext.EXTENSION_LIFECYCLE_TOOLS = ()
                    self.ext.EXTENSION_ARTIFACT_PATH_FIELDS = {}
                    problems = self.problems(**{constant: value})
                    self.assertTrue(any(p.startswith(prefix) and needle in p for p in problems),
                                    problems)

    def test_duplicates_invalid_fields_and_wrong_container_types_are_reported_not_raised(self):
        self.assertIn("lifecycle tool 'acme_w' is declared twice",
                      self.problems(EXTENSION_LIFECYCLE_TOOLS=("acme_w", "acme_w")))
        self.ext.EXTENSION_LIFECYCLE_TOOLS = ()
        for field in ("", "not an identifier", 5, None, "a-b"):
            with self.subTest(field=field):
                problems = self.problems(EXTENSION_ARTIFACT_PATH_FIELDS={"acme_w": field})
                self.assertIn(f"artifact path field for 'acme_w' is {field!r}; use a non-empty identifier string",
                              problems)
        self.ext.EXTENSION_ARTIFACT_PATH_FIELDS = {}
        for value in (["acme_w"], "acme_w", {"acme_w": 1}, None):
            with self.subTest(lifecycle=value):
                problems = self.problems(EXTENSION_LIFECYCLE_TOOLS=value)
                self.assertTrue(any(p.startswith("EXTENSION_LIFECYCLE_TOOLS must be a tuple") for p in problems),
                                problems)
        self.ext.EXTENSION_LIFECYCLE_TOOLS = ()
        for value in (("acme_w",), ["acme_w"], "acme_w", None):
            with self.subTest(fields=value):
                problems = self.problems(EXTENSION_ARTIFACT_PATH_FIELDS=value)
                self.assertTrue(any(p.startswith("EXTENSION_ARTIFACT_PATH_FIELDS must map") for p in problems),
                                problems)
        self.ext.EXTENSION_ARTIFACT_PATH_FIELDS = {}
        self.assertIn("lifecycle tool 5 must be a non-empty tool name string",
                      self.problems(EXTENSION_LIFECYCLE_TOOLS=(5,)))

    def test_the_roster_refuses_the_same_declarations_without_the_server(self):
        import mcp_tool_roster
        self.ext.EXTENSION_TOOL_TIERS = {"acme_w": "write", "acme_r": "read"}
        for constant, value in (("EXTENSION_LIFECYCLE_TOOLS", ("acme_r",)),
                                ("EXTENSION_ARTIFACT_PATH_FIELDS", {"wf_help": "path"}),
                                ("EXTENSION_LIFECYCLE_TOOLS", ["acme_w"])):
            with self.subTest(constant=constant, value=value):
                self.ext.EXTENSION_LIFECYCLE_TOOLS = ()
                self.ext.EXTENSION_ARTIFACT_PATH_FIELDS = {}
                setattr(self.ext, constant, value)
                with self.assertRaises(self.ext.ExtensionDeclarationError):
                    mcp_tool_roster.all_tool_tiers()

    def test_shipped_declaration_lists_both_constants_and_a_non_empty_value_fails(self):
        from declaration_support import SHIPPED_DECLARATION, declaration_profile_mismatch
        from record_layout_support import ExpectedProfile, ProfileLayer
        self.assertEqual(SHIPPED_DECLARATION["EXTENSION_LIFECYCLE_TOOLS"], ())
        self.assertEqual(SHIPPED_DECLARATION["EXTENSION_ARTIFACT_PATH_FIELDS"], {})
        shipped = ExpectedProfile(ProfileLayer("shipped", "shipped", "the shipped defaults", {}))
        from declaration_support import base_declaration
        with base_declaration():
            self.assertIsNone(declaration_profile_mismatch(shipped))
        for constant, value in (("EXTENSION_LIFECYCLE_TOOLS", ("acme_w",)),
                                ("EXTENSION_ARTIFACT_PATH_FIELDS", {"acme_w": "path"})):
            with self.subTest(constant=constant):
                with base_declaration(**{constant: value}):
                    problem = declaration_profile_mismatch(shipped)
                self.assertIsNotNone(problem)
                self.assertIn(f"mcp_tool_extensions.{constant} is", problem)


class ExtensionProvenanceLabelTests(unittest.TestCase):
    """Wave 1zxo0 (1zxns, AC-13): ``wf_server_info`` ``data.extensions`` paths are
    repository-relative under the root, ``framework:<rel>`` for a framework
    loaded from outside the root, ``external:<name>`` otherwise, and never
    absolute on POSIX or Windows spellings."""

    def setUp(self) -> None:
        from unittest.mock import patch
        from server_tools_support import load_server

        self.srv = load_server()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        # The framework (this scripts tree) lies outside this temporary root.
        self.root = Path(tmp.name) / "repo"
        self.root.mkdir()
        self.framework_dir = Path(self.srv.__file__).resolve().parents[2]
        self.outside = Path(tmp.name) / "elsewhere" / "acme_external.py"
        provenance = self.srv._empty_extension_provenance()
        provenance["declaration"] = {**provenance["declaration"],
                                     "path": str(self.framework_dir / "scripts" / "mcp_tool_extensions.py")}
        provenance["modules"] = [
            {"module": "acme_in_root", "path": str(self.root / "ext" / "acme_in_root.py")},
            {"module": "acme_external", "path": str(self.outside)},
        ]
        provenance["helper_modules"] = [
            {"module": "acme_helper", "path": str(self.framework_dir / "scripts" / "acme_helper.py")},
            {"module": "acme_windows", "path": "C:\\Users\\someone\\acme_windows.py"},
        ]
        patcher = patch.object(self.srv, "_EXTENSION_PROVENANCE", provenance)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_labels_are_relative_framework_or_external(self) -> None:
        extensions = self.srv._extension_provenance_for_response(self.root)
        self.assertEqual(extensions["declaration"]["path"], "framework:scripts/mcp_tool_extensions.py")
        self.assertEqual([m["path"] for m in extensions["modules"]],
                         ["ext/acme_in_root.py", "external:acme_external.py"])
        self.assertEqual(extensions["helper_modules"][0]["path"], "framework:scripts/acme_helper.py")
        self.assertTrue(extensions["helper_modules"][1]["path"].startswith("external:"))
        self.assertTrue(extensions["helper_modules"][1]["path"].endswith("acme_windows.py"))

    def test_server_info_extensions_carry_no_absolute_path(self) -> None:
        import ntpath
        import re as _re

        data = self.srv.wf_server_info_response(self.root)["data"]["extensions"]
        paths = [data["declaration"]["path"], *(m["path"] for m in data["modules"]),
                 *(m["path"] for m in data["helper_modules"])]
        for value in paths:
            with self.subTest(value=value):
                bare = value.split(":", 1)[1] if value.startswith(("framework:", "external:")) else value
                self.assertFalse(os.path.isabs(bare), value)
                self.assertFalse(ntpath.isabs(bare), value)
                self.assertIsNone(_re.match(r"^[A-Za-z]:", bare), value)
                self.assertNotIn("\\", value)
        blob = json.dumps(data)
        for absolute in (str(self.root), str(self.framework_dir), str(self.outside.parent)):
            self.assertNotIn(absolute, blob)


if __name__ == "__main__":
    unittest.main()
