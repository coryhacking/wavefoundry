"""Tool-surface serialization for the golden tests (wave 1zyb3, change 1zxnu).

The one definition of how a served MCP tool surface becomes the golden
document, shared by the in-process boot in ``test_tool_surface_golden`` and
the subprocess boot that serves a profile asset's extension modules from a
scratch copy of the scripts tree. Stdlib only, so ``copy_scripts_tree`` can
copy it beside the other test support modules and a fresh interpreter over
the copy imports it without the rest of the tests package.
"""
from __future__ import annotations

import copy
import types
from pathlib import Path

FIXTURE_SCHEMA = "1"

# JSON-Schema keywords whose VALUE is a map of names to schemas. A key named
# ``description`` directly under one of these is a property/definition name,
# not prose, and must survive; anywhere else ``description`` is prose.
_SCHEMA_MAP_KEYS = frozenset({"properties", "$defs", "definitions", "patternProperties"})


def strip_prose_descriptions(node, *, in_name_map: bool = False):
    """Drop schema-node ``description`` prose; keep names that happen to be
    ``description`` inside ``properties`` / ``$defs`` maps."""
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if key == "description" and not in_name_map:
                continue
            child_is_map = (key in _SCHEMA_MAP_KEYS) and not in_name_map
            out[key] = strip_prose_descriptions(value, in_name_map=child_is_map)
        return out
    if isinstance(node, list):
        return [strip_prose_descriptions(item) for item in node]
    return node


def _canonical_schema(schema):
    """Deep copy with prose stripped and set-like ``required`` arrays sorted
    so declaration order never shows up as a public-surface diff."""
    out = strip_prose_descriptions(copy.deepcopy(schema))

    def _sort_required(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "required" and isinstance(value, list) and all(
                    isinstance(item, str) for item in value
                ):
                    node[key] = sorted(value)
                else:
                    _sort_required(value)
        elif isinstance(node, list):
            for item in node:
                _sort_required(item)

    _sort_required(out)
    return out


def serialize_surface(mcp, tiers) -> dict:
    """Deterministic document for every registered tool."""
    registry = mcp._tool_manager._tools
    tools = {}
    for name in sorted(registry):
        tool = registry[name]
        annotations = getattr(tool, "annotations", None)
        tools[name] = {
            "tier": tiers.get(name),
            "inputSchema": _canonical_schema(tool.parameters),
            "annotations": (
                annotations.model_dump(exclude_none=True)
                if annotations is not None
                else None
            ),
        }
    return {"fixture_schema": FIXTURE_SCHEMA, "tools": tools}


def _stub_handler(root: Path):
    return types.SimpleNamespace(root=root.resolve(), close=lambda: None)
