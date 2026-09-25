"""Declared MCP tool extensions for a downstream distribution (wave 1yv9l).

A distribution that ships its own framework pack edits the four declarations
below at merge time to add tools to, or explicitly override tools on, the one
Wavefoundry MCP server. Nothing is discovered: the server loads only the
modules named here, each a single-file module directly in this scripts
directory that defines ``register(mcp, get_handler)``.

Stdlib-only and import-light on purpose: the permission-allowlist renderer
and upgrade read the declared tiers through ``mcp_tool_roster`` without
starting the server, and both paths apply the same validation helpers as the
server so an invalid declaration can never reach a rendered allowlist.

Shipped values are empty, which leaves the stock tool surface unchanged.
"""
from __future__ import annotations

import sys
from typing import Collection, Mapping

# Core tool-name prefixes. The single source of the prefix contract: the
# server's ``MCP_TOOL_PREFIXES`` is this tuple.
CORE_TOOL_PREFIXES: tuple[str, ...] = ("wf_", "memory_", "index_", "docs_", "code_", "seed_")

TIER_READ = "read"
TIER_WRITE = "write"

# ---- Distribution-edited declarations ---------------------------------------

# Flat module names, in registration order.
EXTENSION_MODULES: tuple[str, ...] = ()

# Prefixes every NEW extension tool name must start with. A core prefix such
# as "wf_" is allowed; a distribution-specific prefix is recommended, because a
# later core release that adds the same tool name makes the server refuse to
# start until the extension tool is renamed or declared as an override.
EXTENSION_TOOL_PREFIXES: tuple[str, ...] = ()

# Permission tier ("read" or "write") for every NEW extension tool.
EXTENSION_TOOL_TIERS: Mapping[str, str] = {}

# Core tools each module replaces, keyed by module name. An override keeps
# the core name and tier; it is never listed in EXTENSION_TOOL_TIERS.
EXTENSION_OVERRIDES: Mapping[str, tuple[str, ...]] = {}

# ------------------------------------------------------------------------------

# Names a declared module may never take: the extension machinery itself and
# the server's composition modules. Standard-library names are refused too,
# and the server additionally refuses any name it has already imported.
RESERVED_MODULE_NAMES = frozenset({
    "mcp_tool_extensions",
    "mcp_tool_roster",
    "mcp_tool_registry",
    "server",
    "server_impl",
})


class ExtensionDeclarationError(ValueError):
    """The extension declaration is invalid; nothing may be served from it."""


def declared() -> bool:
    """True when any extension declaration is non-empty."""
    return bool(
        EXTENSION_MODULES or EXTENSION_TOOL_PREFIXES or EXTENSION_TOOL_TIERS or EXTENSION_OVERRIDES
    )


def override_targets() -> dict[str, str]:
    """Map each declared override target to the module that declares it."""
    targets: dict[str, str] = {}
    for module_name, names in EXTENSION_OVERRIDES.items():
        for name in names:
            targets.setdefault(name, module_name)
    return targets


def declaration_problems(
    *,
    core_tools: Collection[str],
    runner_tools: Collection[str],
) -> list[str]:
    """Return every problem with the declaration; empty means valid.

    ``core_tools`` are the tool names core registration serves (runner tools
    excluded); ``runner_tools`` can never be overridden or reused.
    """
    problems: list[str] = []
    core = set(core_tools)
    runner = set(runner_tools)

    seen_modules: set[str] = set()
    for module_name in EXTENSION_MODULES:
        if not isinstance(module_name, str) or not module_name.isidentifier():
            problems.append(f"module {module_name!r} is not a flat single-file module name")
            continue
        if module_name in seen_modules:
            problems.append(f"module {module_name!r} is declared twice")
        seen_modules.add(module_name)
        if module_name in RESERVED_MODULE_NAMES or module_name in sys.stdlib_module_names:
            problems.append(f"module {module_name!r} collides with a framework or standard-library module")

    for prefix in EXTENSION_TOOL_PREFIXES:
        if not isinstance(prefix, str) or not prefix:
            problems.append(f"extension prefix {prefix!r} must be a non-empty string")

    for name, tier in EXTENSION_TOOL_TIERS.items():
        if tier not in (TIER_READ, TIER_WRITE):
            problems.append(f"tool {name!r} declares tier {tier!r}; use 'read' or 'write'")
        if name in core or name in runner:
            problems.append(f"tool {name!r} is an existing tool; declare it as an override, not a tier")
        if not any(isinstance(p, str) and p and name.startswith(p) for p in EXTENSION_TOOL_PREFIXES):
            problems.append(f"tool {name!r} does not start with a declared extension prefix")

    owners: dict[str, str] = {}
    for module_name, names in EXTENSION_OVERRIDES.items():
        if module_name not in seen_modules:
            problems.append(f"overrides are declared for undeclared module {module_name!r}")
        for name in names:
            if name in runner:
                problems.append(f"module {module_name!r} may not override runner tool {name!r}")
            elif name not in core:
                problems.append(f"module {module_name!r} overrides {name!r}, which core does not register")
            if name in EXTENSION_TOOL_TIERS:
                problems.append(f"override {name!r} may not declare a tier; it keeps the core tier")
            if name in owners and owners[name] != module_name:
                problems.append(
                    f"override {name!r} is declared by both {owners[name]!r} and {module_name!r}"
                )
            elif name in owners:
                problems.append(f"override {name!r} is declared twice by {module_name!r}")
            owners[name] = module_name
    return problems


def validate_declaration(*, core_tools: Collection[str], runner_tools: Collection[str]) -> None:
    """Raise ``ExtensionDeclarationError`` listing every declaration problem."""
    problems = declaration_problems(core_tools=core_tools, runner_tools=runner_tools)
    if problems:
        raise ExtensionDeclarationError(
            "invalid MCP tool extension declaration: " + "; ".join(problems)
        )
