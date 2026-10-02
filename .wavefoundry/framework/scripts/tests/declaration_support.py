"""Test support for distribution tool declarations (wave 1zim5, change 1zim4).

A distribution edits the ``EXTENSION_*`` constants in ``mcp_tool_extensions``
at merge time. Two kinds of test must not see that ambient declaration:

* stock-surface tests, whose subject is the shipped tool surface (tool lists,
  tiers, rosters, provenance);
* declaration-machinery tests, which exercise the machinery with a
  declaration of their own.

Both run against a known base through :func:`base_declaration` (a context
manager) or :func:`apply_base_declaration` (bound to a ``TestCase``'s
cleanup): every declaration constant is patched to its shipped empty value
plus the test's own declaration, on every loaded copy of the module, and the
server state computed from a declaration is reset on every loaded server.

MCP-surface test doubles use :class:`RecordingFastMCP`, a real ``FastMCP``
that also records the functions registered as resources, so the declaration
machinery (``_install_served_names`` and friends) runs against them exactly as
against the server. This module is test support: production code never
imports it.
"""
from __future__ import annotations

import contextlib
import copy
import sys
import types
import unittest
from pathlib import Path
from typing import Any, Iterator

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from record_layout_support import (  # noqa: E402
    SHIPPED_DECLARATION,
    ExpectedProfile,
    ProfileInvalid,  # noqa: F401 (re-exported: the guard's callers resolve here)
    expected_profile,  # noqa: F401
)

DECLARATION_MODULE = "mcp_tool_extensions"
DECLARATION_CONSTANTS: tuple[str, ...] = tuple(SHIPPED_DECLARATION)


def _declaration_modules() -> list[types.ModuleType]:
    """Every loaded copy of the declaration module: those registered in
    ``sys.modules`` and those another loaded module still holds (a reload of
    the server re-imports the module while the roster keeps its own copy)."""
    found: list[types.ModuleType] = []
    for key, module in list(sys.modules.items()):
        if module is None:
            continue
        if key == DECLARATION_MODULE or key.endswith("." + DECLARATION_MODULE):
            found.append(module)
        held = getattr(module, DECLARATION_MODULE, None)
        if isinstance(held, types.ModuleType):
            found.append(held)
    if not found:
        found.append(__import__(DECLARATION_MODULE))
    return list({id(module): module for module in found}.values())


def _reset_server_state() -> None:
    """Clear what a server computed from a declaration on every loaded copy
    of ``server_impl``: the extension provenance, the captured core
    behaviour of replaced names and the installed lock and credit
    declarations. All are rebuilt by the next registration."""
    for key, module in list(sys.modules.items()):
        if module is None or not (key == "server_impl" or key.endswith(".server_impl")):
            continue
        if hasattr(module, "_EXTENSION_PROVENANCE"):
            module._EXTENSION_PROVENANCE = None
        replaced = getattr(module, "_EXTENSION_REPLACED_CORE", None)
        if isinstance(replaced, dict):
            replaced.clear()
        # Wave 1zimf (1zimo): the installed lock and credit declarations.
        for name in ("_EXTENSION_LIFECYCLE_TOOLS", "_EXTENSION_ARTIFACT_PATH_FIELDS"):
            installed = getattr(module, name, None)
            if isinstance(installed, (set, dict)):
                installed.clear()


@contextlib.contextmanager
def base_declaration(**declaration: Any) -> Iterator[None]:
    """Run with the shipped empty declaration plus ``declaration`` (keyword
    names are ``EXTENSION_*`` constants), whatever the module on disk
    declares. Restores every patched copy, and resets the server state again,
    on exit."""
    unknown = sorted(set(declaration) - set(DECLARATION_CONSTANTS))
    if unknown:
        raise ValueError(f"not declaration constants: {', '.join(unknown)}")
    modules = _declaration_modules()
    saved = [(module, {name: getattr(module, name) for name in DECLARATION_CONSTANTS}) for module in modules]
    try:
        for module in modules:
            for name in DECLARATION_CONSTANTS:
                setattr(module, name, copy.deepcopy(declaration.get(name, SHIPPED_DECLARATION[name])))
        _reset_server_state()
        yield
    finally:
        for module, values in saved:
            for name, value in values.items():
                setattr(module, name, value)
        _reset_server_state()


def _normalized(value: Any) -> Any:
    """JSON form (tuples as lists), as a profile asset writes a declaration."""
    import json
    return json.loads(json.dumps(value))


def declaration_profile_mismatch(expected: ExpectedProfile) -> "str | None":
    """``None`` when every loaded copy of the declaration module holds
    ``expected``'s declaration exactly (the shipped empty one overlaid with
    each layer's ``mcp_tool_extensions`` entry, in JSON form); else a message
    naming each layer, its source and each differing constant. Resolve
    ``expected`` with :func:`expected_profile` (imported from
    ``record_layout_support``, the one reader of ``WAVEFOUNDRY_TEST_PROFILE``).
    Mirrors ``expected_profile_mismatch``."""
    want = _normalized(expected.declaration())
    differences: list[str] = []
    for module in _declaration_modules():
        loaded = _normalized({name: getattr(module, name, None) for name in DECLARATION_CONSTANTS})
        for name in DECLARATION_CONSTANTS:
            if loaded[name] != want[name]:
                differences.append(f"{DECLARATION_MODULE}.{name} is {loaded[name]!r}, expected {want[name]!r}")
    if not differences:
        return None
    return expected.mismatch_message("tool declarations", list(dict.fromkeys(differences)))


def base_declaration_source(**declaration: Any) -> str:
    """Python assignments that set the base declaration (the shipped empty
    one plus ``declaration``), for a subprocess or a copied scripts tree:
    appended to a copied ``mcp_tool_extensions.py`` it overrides whatever the
    module above it declares."""
    unknown = sorted(set(declaration) - set(DECLARATION_CONSTANTS))
    if unknown:
        raise ValueError(f"not declaration constants: {', '.join(unknown)}")
    lines = ["", "# Base declaration (test support, change 1zim4)."]
    for name in DECLARATION_CONSTANTS:
        lines.append(f"{name} = {declaration.get(name, SHIPPED_DECLARATION[name])!r}")
    return "\n".join(lines) + "\n"


def apply_base_declaration(testcase: unittest.TestCase, **declaration: Any) -> None:
    """:func:`base_declaration` entered now and exited at ``testcase`` cleanup.

    Apply it after anything that re-imports the declaration module (such as
    ``server_tools_support.load_server``) and before the surface is built."""
    context = base_declaration(**declaration)
    context.__enter__()
    testcase.addCleanup(context.__exit__, None, None, None)


def _fastmcp_class():
    from mcp.server.fastmcp import FastMCP
    return FastMCP


class _RecordingMixin:
    """Records each function as registered, before FastMCP wraps or copies it."""

    def tool(self, name: Any = None, **kwargs: Any):
        register = super().tool(name, **kwargs)  # type: ignore[misc]

        def record(fn):
            self.tools[name or fn.__name__] = fn
            return register(fn)

        return record

    def resource(self, uri: str, **kwargs: Any):
        register = super().resource(uri, **kwargs)  # type: ignore[misc]

        def record(fn):
            self.resource_functions[fn.__name__] = fn
            self.resource_uris[uri] = fn
            return register(fn)

        return record


def RecordingFastMCP(name: str = "test-double") -> Any:  # noqa: N802 (reads as a class)
    """A real ``FastMCP`` that also records what the server registers on it:
    ``tools`` maps each tool name to the function as registered (before the
    server's middleware wraps the served copy), ``resource_functions`` each
    resource function's name and ``resource_uris`` each resource URI to the
    function. Its tool table is FastMCP's own (``_tool_manager._tools`` of
    ``Tool`` objects), so the middleware and the declaration machinery
    (``_install_extension_tools``, ``_install_served_names``) run against it
    exactly as against the server. Raises ``ImportError`` when the ``mcp``
    package is not installed."""
    cls = type("RecordingFastMCP", (_RecordingMixin, _fastmcp_class()), {})
    mcp = cls(name)
    mcp.tools = {}
    mcp.resource_functions = {}
    mcp.resource_uris = {}
    return mcp


def served_functions(mcp: Any) -> "dict[str, Any]":
    """Each served tool's callable as served (after the middleware), by name."""
    return {name: tool.fn for name, tool in mcp._tool_manager._tools.items()}
