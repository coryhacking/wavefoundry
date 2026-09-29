"""Declared MCP tool extensions for a downstream distribution (wave 1yv9l).

A distribution that ships its own framework pack edits the declarations below
at merge time to add tools to, or explicitly override tools on, the one
Wavefoundry MCP server. Nothing is discovered: the server loads only the
modules named here, each a single-file module directly in this scripts
directory that defines ``register(mcp, get_handler)``. Wave 1z8oz adds served
aliases, hidden canonical names and replacements of core names.

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

# Additional served names, ``{alias: canonical_name}`` (wave 1z8oz). An alias is
# a copy of the canonical tool as served, so the lifecycle lock, publication
# guard and cost accounting keyed on the canonical name apply to it, and it
# takes the canonical tier.
EXTENSION_TOOL_ALIASES: Mapping[str, str] = {}

# Canonical names that are not served. Each must have an alias.
EXTENSION_HIDDEN_TOOLS: tuple[str, ...] = ()

# Core names a module reuses with an incompatible handler, keyed by module:
# ``{module: {core_name: {"alias_for_core": name, "tier": "read" | "write"}}}``.
# The module's handler is served under the core name; the core behaviour stays
# reachable under ``alias_for_core``. ``tier`` is optional and replaces the
# core name's tier.
EXTENSION_REPLACEMENTS: Mapping[str, Mapping[str, Mapping[str, str]]] = {}

# ------------------------------------------------------------------------------

# Names a declared module may never take: the extension machinery itself and
# the server's composition modules. Standard-library names are refused too,
# and the server additionally refuses any name it has already imported.
RESERVED_MODULE_NAMES = frozenset({
    "mcp_tool_extensions",
    "mcp_tool_roster",
    "server",
    "wf_server",
    # The wf_server package modules (wave 1yzd0): the two retained flat aliases
    # and the ten retired flat names (wave 1yxyw). test_server_package pins this
    # set to server_impl._FLAT_ALIASES, server_impl._RETIRED_FLAT_NAMES and
    # "wf_server".
    "server_impl",
    "mcp_tool_registry",
    "codenav_handlers",
    "graph_handlers",
    "techdocs_handlers",
    "memory_handlers",
    "index_handlers",
    "upgrade_handlers",
    "edit_gate_handlers",
    "dashboard_handlers",
    "docs_handlers",
    "context_efficiency_handlers",
})


class ExtensionDeclarationError(ValueError):
    """The extension declaration is invalid; nothing may be served from it."""


def declared() -> bool:
    """True when any extension declaration is non-empty."""
    return bool(
        EXTENSION_MODULES or EXTENSION_TOOL_PREFIXES or EXTENSION_TOOL_TIERS or EXTENSION_OVERRIDES
        or EXTENSION_TOOL_ALIASES or EXTENSION_HIDDEN_TOOLS or EXTENSION_REPLACEMENTS
    )


def override_targets() -> dict[str, str]:
    """Map each declared override target to the module that declares it."""
    targets: dict[str, str] = {}
    for module_name, names in EXTENSION_OVERRIDES.items():
        for name in names:
            targets.setdefault(name, module_name)
    return targets


def replacement_targets() -> dict[str, tuple[str, Mapping[str, str]]]:
    """Map each replaced core name to ``(module, spec)``, first declaration first."""
    targets: dict[str, tuple[str, Mapping[str, str]]] = {}
    for module_name, entries in EXTENSION_REPLACEMENTS.items():
        if not isinstance(entries, Mapping):
            continue
        for core_name, spec in entries.items():
            if isinstance(spec, Mapping):
                targets.setdefault(core_name, (module_name, spec))
    return targets


def served_name_map() -> dict[str, str]:
    """Canonical name to the name response hints should use.

    A replaced core name maps to its ``alias_for_core``; any other aliased
    name maps to its first-declared alias. Empty for the stock declaration.
    """
    served: dict[str, str] = {}
    for alias, canonical in EXTENSION_TOOL_ALIASES.items():
        served.setdefault(canonical, alias)
    for core_name, (_module, spec) in replacement_targets().items():
        served[core_name] = spec.get("alias_for_core")
    return served


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
    problems.extend(_alias_hide_replacement_problems(core, runner, seen_modules, owners))
    return problems


def _alias_hide_replacement_problems(
    core: set[str],
    runner: set[str],
    modules: set[str],
    override_owners: Mapping[str, str],
) -> list[str]:
    """Aliases, hidden names and replacements (wave 1z8oz).

    A served name is a core name or a declared extension tool. Reserved-name
    collisions are checked by the server, which owns those collections.
    """
    problems: list[str] = []
    served = core | set(EXTENSION_TOOL_TIERS)
    prefixes = tuple(p for p in CORE_TOOL_PREFIXES + tuple(EXTENSION_TOOL_PREFIXES) if isinstance(p, str) and p)
    taken: dict[str, str] = {}

    def check_alias(alias: object, label: str) -> None:
        if not isinstance(alias, str) or not alias:
            problems.append(f"{label} {alias!r} must be a non-empty string")
            return
        if alias in runner:
            problems.append(f"{label} {alias!r} collides with runner tool {alias!r}")
        elif alias in served:
            problems.append(f"{label} {alias!r} collides with an existing tool")
        if alias in taken:
            problems.append(f"{label} {alias!r} is already declared as {taken[alias]}")
        else:
            taken[alias] = label
        if not alias.startswith(prefixes):
            problems.append(f"{label} {alias!r} does not start with a core or declared extension prefix")

    replaced: dict[str, str] = {}
    for module_name, entries in EXTENSION_REPLACEMENTS.items():
        if module_name not in modules:
            problems.append(f"replacements are declared for undeclared module {module_name!r}")
        if not isinstance(entries, Mapping):
            problems.append(f"replacements for module {module_name!r} must map core names to specs")
            continue
        for core_name, spec in entries.items():
            if core_name in runner:
                problems.append(f"module {module_name!r} may not replace runner tool {core_name!r}")
            elif core_name not in core:
                problems.append(f"module {module_name!r} replaces {core_name!r}, which core does not register")
            if core_name in override_owners:
                problems.append(f"{core_name!r} is declared both as an override and as a replacement")
            if core_name in replaced:
                problems.append(
                    f"replacement {core_name!r} is declared by both {replaced[core_name]!r} and {module_name!r}"
                )
            replaced.setdefault(core_name, module_name)
            if not isinstance(spec, Mapping):
                problems.append(f"replacement {core_name!r} must be a mapping with 'alias_for_core'")
                continue
            unknown = sorted(set(spec) - {"alias_for_core", "tier"})
            if unknown:
                problems.append(f"replacement {core_name!r} has unknown keys {unknown}")
            if "tier" in spec and spec["tier"] not in (TIER_READ, TIER_WRITE):
                problems.append(f"replacement {core_name!r} declares tier {spec['tier']!r}; use 'read' or 'write'")
            check_alias(spec.get("alias_for_core"), f"alias_for_core of {core_name!r}")

    aliases = dict(EXTENSION_TOOL_ALIASES)
    alias_names = set(aliases) | {
        spec.get("alias_for_core")
        for entries in EXTENSION_REPLACEMENTS.values() if isinstance(entries, Mapping)
        for spec in entries.values() if isinstance(spec, Mapping)
    }
    for alias, target in aliases.items():
        check_alias(alias, "alias")
        if target in runner:
            problems.append(f"alias {alias!r} targets runner tool {target!r}")
        elif target in alias_names:
            problems.append(f"alias {alias!r} targets another alias {target!r}")
        elif target in replaced:
            problems.append(
                f"alias {alias!r} targets replaced core name {target!r}; its core behaviour is "
                "served only under its alias_for_core"
            )
        elif target not in served:
            problems.append(f"alias {alias!r} targets {target!r}, which is not a served tool")

    aliased = set(aliases.values())
    seen_hidden: set[str] = set()
    for name in EXTENSION_HIDDEN_TOOLS:
        if name in seen_hidden:
            problems.append(f"hidden name {name!r} is declared twice")
            continue
        seen_hidden.add(name)
        if name in runner:
            problems.append(f"hidden name {name!r} is a runner tool")
        elif name in replaced:
            problems.append(f"hidden name {name!r} is a replaced core name")
        elif name not in aliased:
            problems.append(f"hidden name {name!r} has no alias")
    return problems


def validate_declaration(*, core_tools: Collection[str], runner_tools: Collection[str]) -> None:
    """Raise ``ExtensionDeclarationError`` listing every declaration problem."""
    problems = declaration_problems(core_tools=core_tools, runner_tools=runner_tools)
    if problems:
        raise ExtensionDeclarationError(
            "invalid MCP tool extension declaration: " + "; ".join(problems)
        )
