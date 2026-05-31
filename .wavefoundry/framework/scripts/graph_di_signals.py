"""Dependency-injection signal collection and cross-file resolution for graph_indexer."""

from __future__ import annotations

import re
from typing import Any

_JAVA_STEREOTYPES = frozenset({
    "Component", "Service", "Repository", "Controller", "RestController", "Named", "Configuration",
})
_JAVA_INJECT_MARKERS = frozenset({"Autowired", "Inject", "Resource"})
_BIND_RE = re.compile(
    r"bind\s*\(\s*([\w.$]+)\.class\s*\)\s*\.to\s*\(\s*([\w.$]+)\.class\s*\)",
    re.MULTILINE,
)
_DOTNET_ADD_RE = re.compile(
    r"Add(?:Singleton|Scoped|Transient|HostedService)\s*<\s*([\w.]+)\s*,\s*([\w.]+)\s*>\s*\(\s*\)",
    re.MULTILINE,
)
_AUTOFAC_RE = re.compile(
    r"RegisterType\s*<\s*([\w.]+)\s*>\s*\(\s*\)\s*\.As\s*<\s*([\w.]+)\s*>\s*\(\s*\)",
    re.MULTILINE,
)
_CLASS_RE = re.compile(
    r"(?:public\s+|private\s+|protected\s+)?(?:final\s+|abstract\s+)?class\s+(\w+)"
    r"(?:\s+extends\s+[\w.]+)?(?:\s+implements\s+([\w.,\s]+))?",
    re.MULTILINE,
)
_BEAN_METHOD_RE = re.compile(
    r"@Bean(?:\([^)]*\))?\s+(?:public\s+)?([\w<>,\s\[\]?]+)\s+(\w+)\s*\(",
    re.MULTILINE,
)
_CONSTRUCTOR_RE = re.compile(
    r"(?:@[\w.]+\s+)*public\s+(\w+)\s*\(([^)]*)\)",
    re.MULTILINE,
)
_PARAM_TYPE_RE = re.compile(r"(?:final\s+)?(@[\w.]+\s+)*([\w<>,\s\[\]?]+)\s+(\w+)")


def _simple_type(name: str) -> str:
    cleaned = name.strip()
    if "<" in cleaned:
        cleaned = cleaned.split("<", 1)[0]
    return cleaned.split(".")[-1].strip()


def collect_di_signals(rel_path: str, source_text: str) -> list[dict[str, Any]]:
    suffix = rel_path.rsplit(".", 1)[-1].lower() if "." in rel_path else ""
    if suffix in {"java", "kt", "kts"}:
        return _collect_java_kotlin_signals(rel_path, source_text)
    if suffix == "cs":
        return _collect_csharp_signals(rel_path, source_text)
    return []


def _collect_java_kotlin_signals(rel_path: str, source_text: str) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for match in _BIND_RE.finditer(source_text):
        signals.append(
            {
                "kind": "binds",
                "file": rel_path,
                "interface_type": _simple_type(match.group(1)),
                "implementation_type": _simple_type(match.group(2)),
                "confidence": "EXTRACTED",
                "evidence": match.group(0).strip(),
            }
        )
    for class_match in _CLASS_RE.finditer(source_text):
        class_name = class_match.group(1)
        implements = class_match.group(2) or ""
        window_start = max(0, class_match.start() - 400)
        window = source_text[window_start:class_match.start()]
        stereotypes = [name for name in _JAVA_STEREOTYPES if f"@{name}" in window]
        if stereotypes:
            for iface in [part.strip() for part in implements.split(",") if part.strip()]:
                signals.append(
                    {
                        "kind": "binds",
                        "file": rel_path,
                        "interface_type": _simple_type(iface),
                        "implementation_type": class_name,
                        "confidence": "INFERRED",
                        "evidence": f"@{stereotypes[0]} class {class_name} implements {iface}",
                    }
                )
            if not implements and len(stereotypes) == 1:
                signals.append(
                    {
                        "kind": "provider",
                        "file": rel_path,
                        "implementation_type": class_name,
                        "confidence": "INFERRED",
                        "evidence": f"@{stereotypes[0]} class {class_name}",
                    }
                )
        for ctor in _CONSTRUCTOR_RE.finditer(source_text[class_match.start(): class_match.end() + 800]):
            if ctor.group(1) != class_name:
                continue
            ctor_window = source_text[max(0, class_match.start() + ctor.start() - 120): class_match.start() + ctor.start()]
            injectable_class = bool(stereotypes) or any(
                f"@{marker}" in ctor_window for marker in _JAVA_INJECT_MARKERS
            )
            if not injectable_class:
                continue
            params = ctor.group(2)
            for param in _PARAM_TYPE_RE.finditer(params):
                dep_type = _simple_type(param.group(2))
                if dep_type in {"String", "int", "long", "boolean", "double", "float"}:
                    continue
                signals.append(
                    {
                        "kind": "injects",
                        "file": rel_path,
                        "consumer_type": class_name,
                        "dependency_type": dep_type,
                        "confidence": "INFERRED",
                        "evidence": f"constructor injection in {class_name}",
                    }
                )
    for bean in _BEAN_METHOD_RE.finditer(source_text):
        return_type = _simple_type(bean.group(1))
        signals.append(
            {
                "kind": "binds",
                "file": rel_path,
                "interface_type": return_type,
                "implementation_type": return_type,
                "provider_method": bean.group(2),
                "confidence": "EXTRACTED",
                "evidence": f"@Bean {bean.group(2)} -> {return_type}",
            }
        )
    return signals


def _collect_csharp_signals(rel_path: str, source_text: str) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for match in _DOTNET_ADD_RE.finditer(source_text):
        signals.append(
            {
                "kind": "binds",
                "file": rel_path,
                "interface_type": _simple_type(match.group(1)),
                "implementation_type": _simple_type(match.group(2)),
                "confidence": "EXTRACTED",
                "evidence": match.group(0).strip(),
            }
        )
    for match in _AUTOFAC_RE.finditer(source_text):
        signals.append(
            {
                "kind": "binds",
                "file": rel_path,
                "interface_type": _simple_type(match.group(2)),
                "implementation_type": _simple_type(match.group(1)),
                "confidence": "EXTRACTED",
                "evidence": match.group(0).strip(),
            }
        )
    for class_match in re.finditer(r"class\s+(\w+)(?:\s*:\s*([\w,\s]+))?", source_text):
        class_name = class_match.group(1)
        ctor_pattern = re.compile(
            rf"public\s+{re.escape(class_name)}\s*\(([^)]*)\)",
            re.MULTILINE,
        )
        for ctor in ctor_pattern.finditer(source_text):
            params = ctor.group(1)
            if not params.strip():
                continue
            for chunk in params.split(","):
                chunk = chunk.strip()
                if not chunk:
                    continue
                parts = chunk.split()
                if len(parts) < 2:
                    continue
                dep_type = _simple_type(parts[-2])
                if dep_type in {class_name, "IServiceCollection", "IConfiguration"}:
                    continue
                signals.append(
                    {
                        "kind": "injects",
                        "file": rel_path,
                        "consumer_type": class_name,
                        "dependency_type": dep_type,
                        "confidence": "INFERRED",
                        "evidence": f"constructor injection in {class_name}",
                    }
                )
    return signals


def _index_type_nodes(node_map: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    by_type: dict[str, list[str]] = {}
    for node_id, node in node_map.items():
        if node.get("kind") not in {"class", "function", "module"}:
            continue
        label = str(node.get("label") or "")
        if not label:
            continue
        by_type.setdefault(label, []).append(node_id)
        if "::" in node_id:
            by_type.setdefault(node_id.split("::")[-1], []).append(node_id)
    return by_type


def _pick_node(candidates: list[str], *, prefer_file: str | None = None) -> str | None:
    if not candidates:
        return None
    if prefer_file:
        for node_id in candidates:
            if node_id.startswith(prefer_file):
                return node_id
    return sorted(candidates, key=len)[0]


def _ensure_type_node(
    type_name: str,
    *,
    prefer_file: str | None,
    node_map: dict[str, dict[str, Any]],
    type_index: dict[str, list[str]],
    layer: str = "project",
) -> str | None:
    existing = _pick_node(type_index.get(type_name, []), prefer_file=prefer_file)
    if existing:
        return existing
    if not prefer_file or not type_name:
        return None
    node_id = f"{prefer_file}::{type_name}"
    if node_id not in node_map:
        node_map[node_id] = {
            "id": node_id,
            "label": type_name,
            "kind": "class",
            "source_file": prefer_file,
            "source_location": "1:0",
            "layer": layer,
        }
    type_index.setdefault(type_name, []).append(node_id)
    return node_id


def resolve_di_edges(
    artifacts: dict[str, dict[str, Any]],
    node_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve collected DI signals into graph edges."""
    type_index = _index_type_nodes(node_map)
    binds_map: dict[str, list[tuple[str, str, str]]] = {}
    edges: list[dict[str, Any]] = []

    all_signals: list[tuple[str, dict[str, Any]]] = []
    for rel, artifact in artifacts.items():
        if artifact.get("kind") != "code":
            continue
        for signal in artifact.get("di_signals") or []:
            if isinstance(signal, dict):
                all_signals.append((rel, signal))

    for rel, signal in all_signals:
        if signal.get("kind") != "binds":
            continue
        iface = str(signal.get("interface_type") or "")
        impl = str(signal.get("implementation_type") or "")
        if not iface or not impl:
            continue
        impl_node = _ensure_type_node(
            impl,
            prefer_file=rel,
            node_map=node_map,
            type_index=type_index,
        )
        iface_node = _ensure_type_node(
            iface,
            prefer_file=rel,
            node_map=node_map,
            type_index=type_index,
        ) or impl_node
        if impl_node:
            token = iface or impl
            binds_map.setdefault(token, []).append((iface_node or impl_node, impl_node, str(signal.get("confidence") or "INFERRED")))
            if iface_node and impl_node and iface_node != impl_node:
                edges.append(
                    {
                        "source": iface_node,
                        "target": impl_node,
                        "relation": "binds",
                        "confidence": signal.get("confidence") or "INFERRED",
                        "evidence": signal.get("evidence"),
                    }
                )

    for rel, signal in all_signals:
        if signal.get("kind") != "injects":
            continue
        consumer = str(signal.get("consumer_type") or "")
        dependency = str(signal.get("dependency_type") or "")
        if not consumer or not dependency:
            continue
        consumer_node = _ensure_type_node(
            consumer,
            prefer_file=rel,
            node_map=node_map,
            type_index=type_index,
        )
        if not consumer_node:
            continue
        dep_node = None
        bind_candidates = binds_map.get(dependency, [])
        if len(bind_candidates) == 1:
            dep_node = bind_candidates[0][1]
        else:
            dep_matches = type_index.get(dependency, [])
            if len(dep_matches) == 1:
                dep_node = dep_matches[0]
            elif len(dep_matches) > 1:
                dep_node = _pick_node(dep_matches)
            else:
                bind_signal_file = next((s_rel for s_rel, s in all_signals if s.get("implementation_type") == dependency), None)
                dep_node = _ensure_type_node(
                    dependency,
                    prefer_file=bind_signal_file or rel,
                    node_map=node_map,
                    type_index=type_index,
                )
        if dep_node:
            edges.append(
                {
                    "source": consumer_node,
                    "target": dep_node,
                    "relation": "injects",
                    "confidence": signal.get("confidence") or "INFERRED",
                    "evidence": signal.get("evidence"),
                }
            )
    return edges
