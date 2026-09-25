#!/usr/bin/env python3
"""Enumerable runtime registry of the MCP tool surface (wave 1y0h1).

The server registers its tools with FastMCP decorators inside
``server_impl.register_mcp_surface``; this module never replaces that. After
registration, ``build_registry`` reads FastMCP's own tool table and the
permission roster (``mcp_tool_roster``) and produces one ``ToolSpec`` per
implementation-owned tool, so the surface can be enumerated at runtime instead
of by parsing source.

``apply_middleware`` applies the post-registration call wrappers as one ordered
chain and stamps each replaced callable with the labels of the wrappers that
applied to it, in application order, under ``__wf_middleware__``. The chain
itself is declared by the caller: the wrappers live in ``server_impl`` and are
the only place a tool's callable is rebound, so this module rebinds nothing.

This module is stateless and imports nothing from ``server_impl`` at any
scope; everything it needs arrives as an argument. It is on the reload purge
list, so a registry built after ``wf_reload_mcp`` comes from fresh code.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

MIDDLEWARE_MARKER = "__wf_middleware__"

# Parity defect kinds recorded on a registry; neither ever denies startup.
DEFECT_UNROSTERED_TOOL = "registered_tool_without_roster_tier"
DEFECT_UNREGISTERED_ROSTER_TOOL = "roster_tool_not_registered"


@dataclass(frozen=True)
class ToolSpec:
    """One implementation-owned tool as FastMCP serves it."""

    name: str
    tier: str | None
    annotations: Any
    callable: Any
    source_module: str | None


@dataclass(frozen=True)
class ParityDefect:
    """A mismatch between the registered surface and the permission roster."""

    kind: str
    name: str


class ToolRegistry:
    """Specs keyed by tool name, plus the parity defects found building them."""

    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}
        self.parity_defects: list[ParityDefect] = []

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._specs:
            raise ValueError(f"tool already registered: {spec.name}")
        self._specs[spec.name] = spec

    def tools(self) -> list[ToolSpec]:
        return [self._specs[name] for name in sorted(self._specs)]

    def get(self, name: str) -> ToolSpec | None:
        return self._specs.get(name)


def _tool_table(mcp: Any) -> Mapping[str, Any]:
    """FastMCP's tool table, or an empty mapping for a stub without one.

    Falls back to a legacy top-level ``_tools`` table, as the server's own
    ``_registered_mcp_tool_names`` does, so the roster warning keeps covering
    the FastMCP versions that expose it there.
    """
    manager = getattr(mcp, "_tool_manager", None)
    table = getattr(manager, "_tools", None) if manager is not None else None
    if not table:
        table = getattr(mcp, "_tools", None)
    return table if isinstance(table, Mapping) else {}


def _served_callable(entry: Any) -> Any:
    """The callable a table entry serves; a bare-function entry is its own."""
    fn = getattr(entry, "fn", None)
    if fn is not None:
        return fn
    return entry if callable(entry) else None


def build_registry(mcp: Any, roster: Any) -> ToolRegistry:
    """Build the registry from FastMCP's tool table and the permission roster.

    Runner-registered survivors (``roster.RUNNER_TOOLS``) are excluded on both
    sides, because the runner registers them after the implementation surface
    on first start and they are already present when reload re-registers. A
    registered tool with no roster tier, or a roster tool with no registration,
    is recorded as a parity defect rather than raised. A table with no
    implementation-owned entry records no defects: that is a stub or partial
    harness, not drift, matching the runtime roster warning. Without a usable
    roster (none loaded, or no ``TOOL_TIERS`` mapping) there is nothing to
    cross-reference and no runner set to exclude, so the registry is empty.
    """
    registry = ToolRegistry()
    tier_table = getattr(roster, "TOOL_TIERS", None) if roster is not None else None
    all_tiers = getattr(roster, "all_tool_tiers", None) if roster is not None else None
    if isinstance(tier_table, Mapping) and callable(all_tiers):
        # Declared extension tools are rostered too (wave 1yv9l).
        tier_table = all_tiers()
    if not isinstance(tier_table, Mapping):
        return registry
    tiers = dict(tier_table)
    runner = set(getattr(roster, "RUNNER_TOOLS", None) or ())
    table = _tool_table(mcp)
    registered: set[str] = set()
    for name in sorted(table):
        if name in runner:
            continue
        entry = table[name]
        fn = _served_callable(entry)
        if fn is None:
            continue
        registered.add(name)
        registry.register(ToolSpec(
            name=name,
            tier=tiers.get(name),
            annotations=getattr(entry, "annotations", None),
            callable=fn,
            source_module=getattr(fn, "__module__", None),
        ))
        if name not in tiers:
            registry.parity_defects.append(ParityDefect(DEFECT_UNROSTERED_TOOL, name))
    if registered:
        for name in sorted(set(tiers) - runner - registered):
            registry.parity_defects.append(ParityDefect(DEFECT_UNREGISTERED_ROSTER_TOOL, name))
    return registry


def apply_middleware(
    mcp: Any,
    get_handler: Any,
    middleware: Iterable[tuple[str, Callable[[Any, Any], None]]],
) -> None:
    """Apply ``middleware`` in order, innermost first, stamping each wrapped tool.

    Each entry is ``(label, apply)``; ``apply(mcp, get_handler)`` runs one
    wrapper pass. After each pass, every tool whose callable that pass replaced
    (detected by a change of identity) gets that label appended to its
    ``__wf_middleware__`` tuple, so a tool a wrapper skips carries only the
    labels of the wrappers that did apply to it. Wrapper exceptions propagate
    exactly as the direct calls did.
    """
    for label, apply in middleware:
        before = {name: getattr(entry, "fn", None) for name, entry in _tool_table(mcp).items()}
        apply(mcp, get_handler)
        for name, entry in _tool_table(mcp).items():
            fn = getattr(entry, "fn", None)
            prior = before.get(name)
            if fn is None or fn is prior:
                continue
            labels = tuple(getattr(prior, MIDDLEWARE_MARKER, ()) or ()) + (label,)
            try:
                setattr(fn, MIDDLEWARE_MARKER, labels)
            except (AttributeError, TypeError):
                continue
