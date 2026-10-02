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

import keyword
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

# Parameter mappings for declared aliases (wave 1zim3):
# ``{alias: {"rename": {alias_param: canonical_param}, "fixed": {canonical_param: value},
#            "description": text}}``.
# Every canonical parameter that is neither renamed nor fixed passes through
# under its own name. The alias serves a translator into the canonical tool's
# wrapped callable, so every control stays keyed on the canonical name. Top-level
# response ``data`` keys that echo a renamed parameter carry the alias name. The
# optional ``description`` (wave 1zime) replaces the canonical description for
# this alias only; it needs a non-empty ``rename`` or ``fixed`` and is at most
# ALIAS_DESCRIPTION_MAX_CHARS characters.
EXTENSION_TOOL_PARAMETERS: Mapping[str, Mapping[str, object]] = {}

# Canonical names that are not served. Each must have an alias without fixed
# parameters.
EXTENSION_HIDDEN_TOOLS: tuple[str, ...] = ()

# Core names a module reuses with an incompatible handler, keyed by module:
# ``{module: {core_name: {"alias_for_core": name, "tier": "read" | "write"}}}``.
# The module's handler is served under the core name; the core behaviour stays
# reachable under ``alias_for_core``. ``tier`` is optional and replaces the
# core name's tier, but never lowers it: a write tool stays write (wave 1zicq).
EXTENSION_REPLACEMENTS: Mapping[str, Mapping[str, Mapping[str, str]]] = {}

# New extension tools that run under the lifecycle mutation lock, exactly as
# the core lifecycle tools do (wave 1zimf). A new extension tool that writes
# wave lifecycle records must be declared here. Each entry is a write-tier
# tool declared in EXTENSION_TOOL_TIERS; core names keep the core lock set.
EXTENSION_LIFECYCLE_TOOLS: tuple[str, ...] = ()

# ``{tool: data_field}`` (wave 1zimf): the response ``data`` field holding the
# repository-relative paths a new write-tier extension tool wrote, credited as
# derived artifacts by the core contract. The declaration is the
# distribution's assertion that the tool wrote those files.
EXTENSION_ARTIFACT_PATH_FIELDS: Mapping[str, str] = {}

# ------------------------------------------------------------------------------

# Edit-gate tools no declaration may override, replace or hide (wave 1zicq):
# hooks and prompts call them by name. Aliases stay allowed, since an alias
# serves the core handler. Extension modules are trusted code in the server
# process, so this catches a careless declaration; it is not a sandbox.
EDIT_GATE_TOOLS = frozenset({"wf_open_gate", "wf_close_gate"})

# The longest description a parameter-mapped alias may declare (wave 1zime).
# It clears the longest core tool description (about 11,600 characters) and
# keeps a runaway declaration out of every tool listing.
ALIAS_DESCRIPTION_MAX_CHARS = 16_384

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
        or EXTENSION_TOOL_ALIASES or EXTENSION_TOOL_PARAMETERS or EXTENSION_HIDDEN_TOOLS
        or EXTENSION_REPLACEMENTS or EXTENSION_LIFECYCLE_TOOLS or EXTENSION_ARTIFACT_PATH_FIELDS
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


def pinned_aliases() -> frozenset[str]:
    """Aliases whose parameter mapping fixes at least one canonical parameter."""
    return frozenset(
        alias for alias, spec in EXTENSION_TOOL_PARAMETERS.items()
        if isinstance(spec, Mapping) and spec.get("fixed")
    )


def served_name_map() -> dict[str, str]:
    """Canonical name to the name response hints should use.

    A replaced core name maps to its ``alias_for_core``; any other aliased
    name maps to its first-declared plain alias, else its first-declared
    alias without fixed parameters, so a name-only hint never selects a
    pinned call (wave 1zim3). A name whose only aliases are pinned keeps its
    canonical name. Empty for the stock declaration.
    """
    served: dict[str, str] = {}
    pinned = pinned_aliases()
    for alias, canonical in EXTENSION_TOOL_ALIASES.items():
        if alias not in EXTENSION_TOOL_PARAMETERS:
            served.setdefault(canonical, alias)
    for alias, canonical in EXTENSION_TOOL_ALIASES.items():
        if alias not in pinned:
            served.setdefault(canonical, alias)
    for core_name, (_module, spec) in replacement_targets().items():
        served[core_name] = spec.get("alias_for_core")
    return served


def declaration_problems(
    *,
    core_tools: Collection[str],
    runner_tools: Collection[str],
    core_tiers: Mapping[str, str] | None = None,
) -> list[str]:
    """Return every problem with the declaration; empty means valid.

    ``core_tools`` are the tool names core registration serves (runner tools
    excluded); ``runner_tools`` can never be overridden or reused.
    ``core_tiers`` maps core names to their tiers; when given, a replacement
    may not lower a write tool to read (this module cannot import the roster).
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
            elif name in EDIT_GATE_TOOLS:
                problems.append(f"module {module_name!r} may not override edit-gate tool {name!r}")
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
    problems.extend(_alias_hide_replacement_problems(core, runner, seen_modules, owners, core_tiers or {}))
    problems.extend(_lock_and_credit_problems(core, runner))
    return problems


def _lock_and_credit_problems(core: set[str], runner: set[str]) -> list[str]:
    """``EXTENSION_LIFECYCLE_TOOLS`` and ``EXTENSION_ARTIFACT_PATH_FIELDS`` (wave 1zimf).

    Every entry must be a new extension tool declared ``write`` in
    ``EXTENSION_TOOL_TIERS``: a core name's lock membership and extractors are
    fixed by core (overrides and replacements keep the core name's), and a
    read tool neither mutates lifecycle state nor writes artifacts. A wrong
    container type is reported, never raised.
    """
    problems: list[str] = []
    entries: list[tuple[str, object]] = []
    lifecycle = EXTENSION_LIFECYCLE_TOOLS
    if not isinstance(lifecycle, tuple):
        problems.append(f"EXTENSION_LIFECYCLE_TOOLS must be a tuple of tool names, not {type(lifecycle).__name__}")
    else:
        seen: set[str] = set()
        for name in lifecycle:
            if isinstance(name, str) and name in seen:
                problems.append(f"lifecycle tool {name!r} is declared twice")
                continue
            if isinstance(name, str):
                seen.add(name)
            entries.append(("lifecycle tool", name))
    fields = EXTENSION_ARTIFACT_PATH_FIELDS
    if not isinstance(fields, Mapping):
        problems.append(
            "EXTENSION_ARTIFACT_PATH_FIELDS must map tool names to response data fields, "
            f"not {type(fields).__name__}"
        )
    else:
        for name, field in fields.items():
            if not isinstance(field, str) or not field.isidentifier():
                problems.append(f"artifact path field for {name!r} is {field!r}; use a non-empty identifier string")
            entries.append(("artifact path field for", name))
    aliases = set(EXTENSION_TOOL_ALIASES) | {
        spec.get("alias_for_core")
        for entries_ in EXTENSION_REPLACEMENTS.values() if isinstance(entries_, Mapping)
        for spec in entries_.values() if isinstance(spec, Mapping)
    }
    taken_by_core = core | set(override_targets()) | set(replacement_targets())
    tiers = EXTENSION_TOOL_TIERS if isinstance(EXTENSION_TOOL_TIERS, Mapping) else {}
    for label, name in entries:
        if not isinstance(name, str) or not name:
            problems.append(f"{label} {name!r} must be a non-empty tool name string")
        elif name in runner:
            problems.append(f"{label} {name!r} is a runner tool; only new write-tier extension tools may be declared")
        elif name in EDIT_GATE_TOOLS:
            problems.append(f"{label} {name!r} is an edit-gate tool; only new write-tier extension tools may be declared")
        elif name in taken_by_core:
            problems.append(
                f"{label} {name!r} is a core tool; its lock membership and extractors are fixed by core"
            )
        elif name in aliases:
            problems.append(f"{label} {name!r} is an alias; declare the canonical extension tool instead")
        elif name not in tiers:
            problems.append(f"{label} {name!r} is not a new extension tool declared in EXTENSION_TOOL_TIERS")
        elif tiers[name] != TIER_WRITE:
            problems.append(f"{label} {name!r} is a read tool; lifecycle and artifact declarations require tier 'write'")
    return problems


def _alias_hide_replacement_problems(
    core: set[str],
    runner: set[str],
    modules: set[str],
    override_owners: Mapping[str, str],
    core_tiers: Mapping[str, str],
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
            elif core_name in EDIT_GATE_TOOLS:
                problems.append(f"module {module_name!r} may not replace edit-gate tool {core_name!r}")
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
            elif spec.get("tier") == TIER_READ and core_tiers.get(core_name) == TIER_WRITE:
                problems.append(f"replacement {core_name!r} may not lower its tier from 'write' to 'read'")
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

    problems.extend(_parameter_mapping_problems(aliases, runner))
    pinned = pinned_aliases()
    aliased = set(aliases.values())
    aliased_unpinned = {target for alias, target in aliases.items() if alias not in pinned}
    seen_hidden: set[str] = set()
    for name in EXTENSION_HIDDEN_TOOLS:
        if name in seen_hidden:
            problems.append(f"hidden name {name!r} is declared twice")
            continue
        seen_hidden.add(name)
        if name in runner:
            problems.append(f"hidden name {name!r} is a runner tool")
        elif name in EDIT_GATE_TOOLS:
            problems.append(f"hidden name {name!r} is an edit-gate tool")
        elif name in replaced:
            problems.append(f"hidden name {name!r} is a replaced core name")
        elif name not in aliased:
            problems.append(f"hidden name {name!r} has no alias")
        elif name not in aliased_unpinned:
            problems.append(f"hidden name {name!r} has only aliases with fixed parameters")
    return problems


def _alias_description_problems(label: str, spec: Mapping[str, object]) -> list[str]:
    """The optional alias ``description`` (wave 1zime): a non-blank string within
    the cap, on an entry that renames or pins (a plain alias has the canonical
    parameters, so the canonical description stays accurate)."""
    problems: list[str] = []
    description = spec["description"]
    if not isinstance(description, str):
        problems.append(f"{label}: 'description' must be a string, not {type(description).__name__}")
    elif not description:
        problems.append(f"{label}: 'description' is empty")
    elif not description.strip():
        problems.append(f"{label}: 'description' is whitespace only")
    elif len(description) > ALIAS_DESCRIPTION_MAX_CHARS:
        problems.append(
            f"{label}: 'description' has {len(description)} characters, more than {ALIAS_DESCRIPTION_MAX_CHARS}"
        )
    if not spec.get("rename") and not spec.get("fixed"):
        problems.append(
            f"{label} declares 'description' without a non-empty 'rename' or 'fixed'; "
            "a plain alias keeps the canonical description"
        )
    return problems


def _parameter_mapping_problems(aliases: Mapping[str, str], runner: set[str]) -> list[str]:
    """Structural checks on ``EXTENSION_TOOL_PARAMETERS`` (wave 1zim3).

    Checks that need the canonical argument model (a rename or fixed name
    that is not a canonical parameter, a fixed value the canonical field
    rejects, an alias parameter that collides with a pass-through parameter
    or a model attribute) run in the server, which owns that model.
    """
    problems: list[str] = []
    if not isinstance(EXTENSION_TOOL_PARAMETERS, Mapping):
        return ["EXTENSION_TOOL_PARAMETERS must map aliases to parameter mappings"]
    for alias, spec in EXTENSION_TOOL_PARAMETERS.items():
        label = f"parameter mapping for {alias!r}"
        if alias not in aliases:
            problems.append(f"{label}, which is not an alias")
            continue
        target = aliases[alias]
        if target in runner:
            problems.append(f"{label} maps an alias of runner tool {target!r}")
        elif target in EDIT_GATE_TOOLS:
            problems.append(f"{label} maps an alias of edit-gate tool {target!r}")
        if not isinstance(spec, Mapping):
            problems.append(f"{label} must be a mapping with 'rename' and/or 'fixed'")
            continue
        unknown = sorted(set(spec) - {"rename", "fixed", "description"})
        if unknown:
            problems.append(f"{label} has unknown keys {unknown}")
        if "description" in spec:
            problems.extend(_alias_description_problems(label, spec))
        rename = spec.get("rename", {})
        fixed = spec.get("fixed", {})
        if not isinstance(rename, Mapping) or not isinstance(fixed, Mapping):
            problems.append(f"{label}: 'rename' and 'fixed' must be mappings")
            continue
        targets: set[object] = set()
        for alias_param, canonical_param in rename.items():
            if not isinstance(alias_param, str) or not alias_param.isidentifier() or alias_param.startswith("_"):
                problems.append(f"{label} renames to {alias_param!r}, which is not a parameter name")
            elif keyword.iskeyword(alias_param):
                problems.append(f"{label} renames to {alias_param!r}, which is a Python keyword")
            elif alias_param == "kwargs" or alias_param.startswith("model_"):
                problems.append(f"{label} renames to reserved parameter name {alias_param!r}")
            if not isinstance(canonical_param, str) or not canonical_param:
                problems.append(f"{label} renames {alias_param!r} from {canonical_param!r}, which is not a parameter name")
            elif canonical_param in targets:
                problems.append(f"{label} renames canonical parameter {canonical_param!r} twice")
            targets.add(canonical_param)
        for canonical_param in fixed:
            if not isinstance(canonical_param, str) or not canonical_param:
                problems.append(f"{label} fixes {canonical_param!r}, which is not a parameter name")
            elif canonical_param in targets:
                problems.append(f"{label} fixes {canonical_param!r}, which it also renames")
    return problems


def validate_declaration(
    *,
    core_tools: Collection[str],
    runner_tools: Collection[str],
    core_tiers: Mapping[str, str] | None = None,
) -> None:
    """Raise ``ExtensionDeclarationError`` listing every declaration problem."""
    problems = declaration_problems(core_tools=core_tools, runner_tools=runner_tools, core_tiers=core_tiers)
    if problems:
        raise ExtensionDeclarationError(
            "invalid MCP tool extension declaration: " + "; ".join(problems)
        )
