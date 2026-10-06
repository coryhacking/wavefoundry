"""Declared MCP tool extensions for a downstream distribution (wave 1yv9l).

A distribution that ships its own framework pack edits the declarations below
at merge time to add tools to, or explicitly override tools on, the one
Wavefoundry MCP server. Nothing is discovered: the server loads only the
modules named here, each a single-file module directly in this scripts
directory that defines ``register(mcp, get_handler)``. Wave 1z8oz adds served
aliases, hidden canonical names and replacements of core names. Wave 1zls8 adds
declared helper modules, which extension modules import and the server hashes
and reloads, and declared response-key renames for parameter-mapped aliases.

Stdlib-only and import-light on purpose: the permission-allowlist renderer
and upgrade read the declared tiers through ``mcp_tool_roster`` without
starting the server, and both paths apply the same validation helpers as the
server so an invalid declaration can never reach a rendered allowlist.

Wave 1zv8c (change 1zv89) adds ``EXTENSION_SKILLS``, the distribution's own
skills. It is read only by the agent-surface renderer, at call time, and is
never part of ``declared()``, ``declaration_problems`` or
``validate_declaration``: an invalid skill entry refuses the skill render and
is never fatal to the server, the tool roster or the allowlist render.

Shipped values are empty, which leaves the stock tool surface unchanged.
"""
from __future__ import annotations

import keyword
import re
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

# Flat helper module names that extension modules import, in load order (wave
# 1zls8, change 1zltx). Each is a single ``.py`` file directly in this scripts
# directory, loaded before any extension module, hashed into provenance and
# re-executed on reload; its ``register``, if any, is never called. A helper
# may import only helpers declared before it.
EXTENSION_HELPER_MODULES: tuple[str, ...] = ()

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
#            "description": text, "response_keys": {path: new_key}}}``.
# Every canonical parameter that is neither renamed nor fixed passes through
# under its own name. The alias serves a translator into the canonical tool's
# wrapped callable, so every control stays keyed on the canonical name. Top-level
# response ``data`` keys that echo a renamed parameter carry the alias name. The
# optional ``description`` (wave 1zime) replaces the canonical description for
# this alias only; it needs a non-empty ``rename``, ``fixed`` or ``response_keys``
# and is at most ALIAS_DESCRIPTION_MAX_CHARS characters. The optional
# ``response_keys`` (wave 1zls8, change 1zlty) renames keys of the canonical
# response ``data``: each path names one key in canonical names, dot-separated,
# with ``[]`` meaning each element of the list at that key (for example
# ``{"changes": "items", "changes[].id": "item_id"}``); the new name replaces
# the last key only, and values never change.
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

# Skills the distribution renders to every active skill host (wave 1zv8c,
# change 1zv89): ``{name: {"title": text, "description": text,
# "prompt_doc": "docs/prompts/<name>.prompt.md", "summary": [line, ...]}}``.
# Each renders as a thin-pointer SKILL.md only where its prompt doc exists.
# Renderer-only: the server never validates it, so a bad entry refuses the
# skill render (see ``skill_declaration_problems``) and never stops the server.
# Names never start with "wf-", which the framework's own skills keep.
EXTENSION_SKILLS: Mapping[str, Mapping[str, object]] = {}

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

# The most segments one response_keys path may have, and the most entries one
# alias may declare (wave 1zls8, change 1zlty). Core responses nest well under
# eight levels, and the rename walk stays proportional to the declaration.
RESPONSE_KEY_MAX_DEPTH = 8
RESPONSE_KEY_MAX_ENTRIES = 64

# A response_keys path: dot-separated keys, each optionally ending in "[]".
_RESPONSE_KEY_PATH = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\[\])?(\.[A-Za-z_][A-Za-z0-9_]*(\[\])?)*")

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


# The stem of every flat ``.py`` file the framework ships in this scripts
# directory (wave 1zls8, change 1zltx). No extension or helper module may take
# one: the server's collision check catches only a script it has already
# imported, and a helper needs no ``register``, so a helper declaration naming
# a framework script would otherwise execute that script as a hashed helper. A
# census test pins this set to the directory, less the names the declaration
# lists.
FRAMEWORK_SCRIPT_MODULE_NAMES = frozenset({
    '_tag_utils', 'accel_embedder', 'agent_surface_integrity', 'ann_reference_eval', 'build_pack',
    'build_scan_allowlist', 'change_doc_checklist', 'check_version', 'chunker', 'cli_stdio',
    'commit_provenance', 'context_efficiency', 'dashboard_handlers', 'dashboard_lib',
    'dashboard_server', 'design_token_build', 'docs_gardener', 'docs_lint', 'eval_chunker',
    'exploration_avoided', 'gardener_metadata', 'gen_codebase_map', 'gpu_doctor',
    'graph_call_census', 'graph_cluster', 'graph_di_signals', 'graph_indexer',
    'graph_quality_eval', 'graph_query', 'graph_snapshot', 'graph_store', 'index_compatibility',
    'index_paths', 'index_source_guard', 'index_state_store', 'indexer', 'install_log_lib',
    'lexical_ranking_eval', 'lifecycle_gate_support', 'lifecycle_gates', 'lifecycle_id',
    'lifecycle_lock', 'machine_authority', 'marker_namespaces', 'mcp_tool_extensions',
    'mcp_tool_roster', 'memory_backfill', 'memory_cli', 'memory_eval', 'memory_records',
    'memory_supply', 'model_bundle', 'operator_identity', 'path_containment', 'process_info',
    'project_context_efficiency', 'provider_policy', 'prune_framework', 'public_contract',
    'publication_control', 'reconcile_scan', 'record_paths', 'render_agent_surfaces',
    'render_platform_surfaces', 'repair_ppol_memory_staging', 'repo_root', 'retrieval_eval',
    'review_evidence', 'review_policy', 'review_policy_reconcile', 'review_policy_upgrade',
    'run_secrets_scan', 'run_tests', 'runtime_advisory', 'runtime_lock', 'scan_secrets',
    'scanner_skips', 'score_context_efficiency_pairs', 'sensor_runner', 'server', 'server_impl',
    'setup_index', 'setup_readiness', 'setup_reconciliation', 'setup_requirements',
    'setup_wavefoundry', 'sqlite_runtime', 'sqlite_storage_migration', 'sqlite_vector_store',
    'storage_identity', 'subprocess_util', 'techdocs_audit', 'techdocs_audit_lib',
    'techdocs_baseline', 'tree_sitter_cache', 'upgrade_bridge_bootstrap', 'upgrade_bundle',
    'upgrade_extensions', 'upgrade_lib', 'upgrade_protocol', 'upgrade_wavefoundry',
    'venv_bootstrap', 'verify_vendored_scripts', 'vocabulary_profile', 'wave_gate', 'wf_cli',
})


class ExtensionDeclarationError(ValueError):
    """The extension declaration is invalid; nothing may be served from it."""


def declared() -> bool:
    """True when any extension declaration is non-empty."""
    return bool(
        EXTENSION_MODULES or EXTENSION_HELPER_MODULES or EXTENSION_TOOL_PREFIXES or EXTENSION_TOOL_TIERS
        or EXTENSION_OVERRIDES
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
    problems.extend(_module_name_problems("module", EXTENSION_MODULES, seen_modules))
    problems.extend(_helper_module_problems(seen_modules))

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


def _module_name_problems(label: str, names: Collection[object], seen: set[str]) -> list[str]:
    """The flat module name rules for ``EXTENSION_MODULES`` and
    ``EXTENSION_HELPER_MODULES``; each valid identifier is added to ``seen``."""
    problems: list[str] = []
    for module_name in names:
        if not isinstance(module_name, str) or not module_name.isidentifier():
            problems.append(f"{label} {module_name!r} is not a flat single-file module name")
            continue
        if not module_name.isascii():
            # Wave 1zls8: a non-ASCII identifier (an NFD "acmé" among them)
            # would pass here and fail only at load; file names on disk may be
            # normalized differently per platform.
            problems.append(
                f"{label} {module_name!r} is not an ASCII module name; use ASCII letters, digits and underscores"
            )
            continue
        if module_name in seen:
            problems.append(f"{label} {module_name!r} is declared twice")
        seen.add(module_name)
        if module_name in RESERVED_MODULE_NAMES or module_name in sys.stdlib_module_names:
            problems.append(f"{label} {module_name!r} collides with a framework or standard-library module")
        elif module_name in FRAMEWORK_SCRIPT_MODULE_NAMES:
            problems.append(
                f"{label} {module_name!r} matches the framework script {module_name}.py; "
                "give it a distribution-specific name"
            )
    return problems


def _helper_module_problems(extension_modules: set[str]) -> list[str]:
    """``EXTENSION_HELPER_MODULES`` (wave 1zls8, change 1zltx): the extension
    module name rules, no name in both declarations, and a tuple value. A wrong
    container type is reported, never raised."""
    helpers = EXTENSION_HELPER_MODULES
    if not isinstance(helpers, tuple):
        return [f"EXTENSION_HELPER_MODULES must be a tuple of module names, not {type(helpers).__name__}"]
    problems = _module_name_problems("helper module", helpers, set())
    for module_name in helpers:
        if isinstance(module_name, str) and module_name in extension_modules:
            problems.append(f"helper module {module_name!r} is also declared in EXTENSION_MODULES")
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
    the cap, on an entry that renames, pins or renames response keys (wave
    1zls8, change 1zlty); a plain alias has the canonical parameters and
    response, so the canonical description stays accurate."""
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
    if not spec.get("rename") and not spec.get("fixed") and not spec.get("response_keys"):
        problems.append(
            f"{label} declares 'description' without a non-empty 'rename', 'fixed' or 'response_keys'; "
            "a plain alias keeps the canonical description"
        )
    return problems


def _response_key_problems(label: str, response_keys: object, rename: Mapping[object, object]) -> list[str]:
    """The optional ``response_keys`` map (wave 1zls8, change 1zlty).

    Each path names one key of the canonical response ``data`` in canonical
    names (``[]`` after a segment means each element of that list), and the
    new name replaces the last key only. Reported, never raised.
    """
    if not isinstance(response_keys, Mapping):
        return [f"{label}: 'response_keys' must map response key paths to new key names, "
                f"not {type(response_keys).__name__}"]
    problems: list[str] = []
    if len(response_keys) > RESPONSE_KEY_MAX_ENTRIES:
        problems.append(
            f"{label}: 'response_keys' has {len(response_keys)} entries, more than {RESPONSE_KEY_MAX_ENTRIES}"
        )
    renamed_canonical = set(rename.values())
    alias_parameters = set(rename)
    targets: dict[tuple[str, str], str] = {}
    for path, new_key in response_keys.items():
        if not isinstance(path, str) or not _RESPONSE_KEY_PATH.fullmatch(path):
            problems.append(f"{label}: response key path {path!r} is not a dot-separated key path")
            continue
        segments = path.split(".")
        if segments[-1].endswith("[]"):
            problems.append(f"{label}: response key path {path!r} must end in a key, not '[]'")
            continue
        if len(segments) > RESPONSE_KEY_MAX_DEPTH:
            problems.append(
                f"{label}: response key path {path!r} has {len(segments)} segments, more than {RESPONSE_KEY_MAX_DEPTH}"
            )
        if not isinstance(new_key, str) or not new_key.isidentifier():
            problems.append(f"{label}: response key path {path!r} renames to {new_key!r}, which is not an identifier")
            continue
        if new_key == segments[-1]:
            problems.append(f"{label}: response key path {path!r} renames {new_key!r} to itself")
        parent = ".".join(segments[:-1])
        if (parent, new_key) in targets:
            problems.append(
                f"{label}: response key paths {targets[(parent, new_key)]!r} and {path!r} both rename to {new_key!r}"
            )
        else:
            targets[(parent, new_key)] = path
        if len(segments) == 1 and path in renamed_canonical:
            problems.append(
                f"{label}: response key path {path!r} is a renamed parameter, whose echoed key 'rename' already renames"
            )
        if len(segments) == 1 and new_key in alias_parameters:
            problems.append(
                f"{label}: response key path {path!r} renames to {new_key!r}, an alias parameter name in 'rename'"
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
        unknown = sorted(set(spec) - {"rename", "fixed", "description", "response_keys"})
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
        if "response_keys" in spec:
            problems.extend(_response_key_problems(label, spec["response_keys"], rename))
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


# ---- Declared skills (wave 1zv8c, change 1zv89) ------------------------------
# Renderer-only: ``render_agent_surfaces`` calls this before any write and
# also refuses a name whose rendered path is one of its stale skill paths.

SKILL_KEYS = ("title", "description", "prompt_doc", "summary")
SKILL_NAME_MAX_CHARS = 64
SKILL_DESCRIPTION_MAX_CHARS = 1024
SKILL_SUMMARY_MAX_LINES = 8
SKILL_PROMPT_DOC_PREFIX = "docs/prompts/"
SKILL_PROMPT_DOC_SUFFIX = ".prompt.md"

_SKILL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
# Characters that start a YAML indicator when they lead a plain scalar.
_YAML_INDICATORS = frozenset("-?:,[]{}#&*!|>'\"%@`")
# Plain scalars YAML reads as booleans or null rather than as text.
_YAML_SPECIAL_SCALARS = frozenset({"true", "false", "yes", "no", "on", "off", "null", "~"})
# YAML numbers that float() and int(text, 0) do not parse: base-60 such as
# "1:20" (YAML 1.1) and the ".inf" and ".nan" forms.
_YAML_SEXAGESIMAL = re.compile(r"[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+(?:\.[0-9_]*)?")
_YAML_SPECIAL_FLOAT = re.compile(r"[-+]?\.(?:inf|nan)", re.IGNORECASE)


def _breaks_single_line(text: str) -> bool:
    """True when ``text`` holds a C0 or C1 control (CR, LF, tab and U+0085
    among them) or a Unicode line or paragraph separator."""
    return any(ord(ch) < 0x20 or 0x7F <= ord(ch) <= 0x9F or ch in "\u2028\u2029" for ch in text)


def _is_yaml_number(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        pass
    try:
        int(text, 0)
        return True
    except ValueError:
        pass
    return bool(_YAML_SEXAGESIMAL.fullmatch(text) or _YAML_SPECIAL_FLOAT.fullmatch(text))


def _skill_text_problems(label: str, value: object, *, scalar_rules: bool) -> list[str]:
    """The plain-text rules for a title, a description or a summary line:
    safe as a YAML plain scalar and as one markdown line."""
    if not isinstance(value, str) or not value:
        return [f"{label} must be a non-empty string"]
    problems: list[str] = []
    if _breaks_single_line(value):
        problems.append(f"{label} must be a single line without control characters")
    if value != value.strip():
        problems.append(f"{label} must not start or end with a space")
    if ": " in value or " #" in value:
        problems.append(f"{label} must not contain ': ' or ' #'")
    if value.endswith(":"):
        problems.append(f"{label} must not end with ':'")
    if value[0] in _YAML_INDICATORS:
        problems.append(f"{label} must not start with the YAML indicator {value[0]!r}")
    if scalar_rules and value.strip().lower() in _YAML_SPECIAL_SCALARS:
        problems.append(f"{label} must not be the YAML scalar {value!r}")
    if scalar_rules and _is_yaml_number(value.strip()):
        problems.append(f"{label} must not be a number")
    return problems


def _skill_prompt_doc_problems(label: str, value: object) -> list[str]:
    if not isinstance(value, str) or not value:
        return [f"{label} must be a non-empty string"]
    problems: list[str] = []
    if "\\" in value:
        problems.append(f"{label} must use '/' separators, not a backslash")
    if ":" in value:
        problems.append(f"{label} must not contain ':' (a drive or scheme)")
    if value.startswith("/"):
        problems.append(f"{label} must be repository-relative, not absolute")
    if _breaks_single_line(value) or "`" in value:
        problems.append(f"{label} must not contain control characters or a backtick")
    if any(part in ("", ".", "..") for part in value.split("/")):
        problems.append(f"{label} must not contain empty, '.' or '..' segments")
    name = value.rsplit("/", 1)[-1]
    if (not value.startswith(SKILL_PROMPT_DOC_PREFIX) or not name.endswith(SKILL_PROMPT_DOC_SUFFIX)
            or name == SKILL_PROMPT_DOC_SUFFIX):
        problems.append(
            f"{label} must be a path under {SKILL_PROMPT_DOC_PREFIX} ending in {SKILL_PROMPT_DOC_SUFFIX}"
        )
    return problems


def skill_declaration_problems(skills: object = None) -> list[str]:
    """Every problem with a skill declaration (``EXTENSION_SKILLS`` read now
    when ``skills`` is None), one message per problem naming the skill and
    key; empty means valid. Never consulted by the server."""
    if skills is None:
        skills = EXTENSION_SKILLS
    if not isinstance(skills, Mapping):
        return [f"EXTENSION_SKILLS must be a mapping of skill name to entry, not {type(skills).__name__}"]
    problems: list[str] = []
    for name, spec in skills.items():
        if not isinstance(name, str):
            problems.append(f"skill name {name!r} must be a string")
            continue
        label = f"skill {name!r}"
        if not _SKILL_NAME.fullmatch(name):
            problems.append(f"{label}: the name must be lower-case letters and digits joined by single hyphens")
        if len(name) > SKILL_NAME_MAX_CHARS:
            problems.append(f"{label}: the name is longer than {SKILL_NAME_MAX_CHARS} characters")
        if name.startswith("wf-"):
            problems.append(f"{label}: the name prefix 'wf-' is reserved for the framework's own skills")
        lowered = name.lower()
        for reserved in ("claude", "anthropic"):
            if reserved in lowered:
                problems.append(f"{label}: the name must not contain {reserved!r}")
        if not isinstance(spec, Mapping):
            problems.append(f"{label}: the entry must be a mapping with keys {', '.join(SKILL_KEYS)}")
            continue
        missing = [key for key in SKILL_KEYS if key not in spec]
        extra = sorted(str(key) for key in spec if key not in SKILL_KEYS)
        if missing:
            problems.append(f"{label}: missing key(s) {', '.join(missing)}")
        if extra:
            problems.append(f"{label}: unknown key(s) {', '.join(extra)}")
        if "title" in spec:
            problems.extend(_skill_text_problems(f"{label} title", spec["title"], scalar_rules=True))
        if "description" in spec:
            description = spec["description"]
            problems.extend(_skill_text_problems(f"{label} description", description, scalar_rules=True))
            if isinstance(description, str) and len(description) > SKILL_DESCRIPTION_MAX_CHARS:
                problems.append(
                    f"{label} description is longer than {SKILL_DESCRIPTION_MAX_CHARS} characters"
                )
        if "prompt_doc" in spec:
            problems.extend(_skill_prompt_doc_problems(f"{label} prompt_doc", spec["prompt_doc"]))
        if "summary" in spec:
            summary = spec["summary"]
            if not isinstance(summary, (list, tuple)) or not 1 <= len(summary) <= SKILL_SUMMARY_MAX_LINES:
                problems.append(
                    f"{label} summary must be a list or tuple of 1 to {SKILL_SUMMARY_MAX_LINES} strings"
                )
            else:
                for index, line in enumerate(summary):
                    problems.extend(
                        _skill_text_problems(f"{label} summary[{index}]", line, scalar_rules=False)
                    )
    return problems
