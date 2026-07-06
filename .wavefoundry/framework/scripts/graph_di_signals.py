"""Dependency-injection signal collection and cross-file resolution for graph_indexer."""

from __future__ import annotations

import ast
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


# =============================================================================
# AST-anchored DI signal collection for Python and TypeScript (wave 1p9q7).
#
# Unlike the regex JVM/.NET collectors above, these run over ALREADY-PARSED
# trees supplied by the language extractors (`ast` for Python, tree-sitter for
# TypeScript), so signals attach to real nodes — idiom text inside strings or
# comments never fires.
#
# ORIGIN-CHECK CONVENTION (aligned with the landed embedded-SQL discipline,
# wave 1p9qi `graph_indexer.py`): a DISTINCTIVE idiom name (`Depends`,
# `@Injectable`/`@injectable`, `@Inject`, `@Module`) uses a NEGATIVE origin
# check — it fires unless the local name resolves to a NON-DI-library origin
# (a same-file def or an import from an unrelated module), and an unbound
# canonical spelling is accepted (self-identifying). A GENERIC idiom name
# (`bind`) uses a POSITIVE origin check — the file must import the DI container
# library (Inversify) or no `bind().to()` edge is emitted. This is symmetric
# across both new languages: an alias-imported idiom is recognized and a
# same-named user-defined idiom is refused.
#
# Emitted signals use the SAME `binds`/`injects` schema as the JVM/.NET
# collectors and route through the shared `resolve_di_edges` below. Two
# opt-in per-signal flags let the AST path express the faithfulness stance
# without changing the JVM/.NET output (AC-5, byte-identical):
#   - ``faithful_external``: an ambiguous (>1 candidate) or unresolved target
#     mints a plain ``external::<name>`` node rather than picking a candidate
#     or synthesizing a project node. Plain ``external::`` (NOT a reserved
#     ``external::di::``) is deliberate: an unresolved DI provider is an
#     ordinary code symbol, unlike a foreign SQL table (Decision Log 2026-07-05).
#   - ``*_token`` (``dependency_token``/``interface_token``/
#     ``implementation_token``): a string DI token that is external by
#     construction (never a project symbol).
# =============================================================================

# FastAPI's dependency idiom.
_PY_DEPENDS_ROOT = "fastapi"
_PY_DEPENDS_NAME = "Depends"

# NestJS + Inversify module specifiers whose idioms we recognize.
_TS_NESTJS_MODULES = ("@nestjs/common", "@nestjs/core")
_TS_INVERSIFY_MODULES = ("inversify",)
_TS_DI_MODULES = _TS_NESTJS_MODULES + _TS_INVERSIFY_MODULES
# Built-in / structural TS types that are never a DI class dependency.
_TS_PRIMITIVE_TYPES = frozenset({
    "string", "number", "boolean", "any", "unknown", "void", "object",
    "symbol", "bigint", "never", "null", "undefined", "this",
})

# Wave 1p9q8 (1p9q7 perf follow-up): cheap raw-source pre-check tokens. The DI
# collectors run a FULL extra AST/tree-sitter walk on every Python/TS file even
# when the file contains zero DI idioms. Before walking, a substring scan of the
# raw source short-circuits to `[]` when NONE of these trigger tokens appear.
# The token set is a strict SUPERSET of every literal an emitting collector path
# fires on, so the fast path never drops a real signal (no false negatives):
#   * Python: the only idiom is FastAPI `Depends(...)` — the name `Depends`
#     always appears in source (as the import, the call, or the canonical token).
#   * TS: `@Injectable`/`@injectable`, `@Inject`/`@inject`, `@Module`, and the
#     Inversify `bind(...).to(...)` chain. `Inject`/`inject` are substrings of
#     `Injectable`/`injectable`, so the injectable decorator is covered too; all
#     variants are listed explicitly for faithfulness. Matched as bytes so no
#     full unicode decode of a large file is needed.
_PY_DI_TRIGGER = "Depends"
_TS_DI_TRIGGER_TOKENS = (b"Injectable", b"injectable", b"Inject", b"inject", b"Module", b"bind")


def _py_origin_is_depends(origin: str) -> bool:
    parts = origin.split(".")
    return parts[-1] == _PY_DEPENDS_NAME and parts[0] == _PY_DEPENDS_ROOT


def collect_python_di_signals(
    rel_path: str,
    tree: "ast.Module",
    import_aliases: dict[str, str],
    local_defs: set[str],
    source: str = "",
) -> list[dict[str, Any]]:
    """AST-anchored FastAPI `Depends(...)` `injects` signals (wave 1p9q7).

    ``import_aliases`` maps a local name to its dotted import origin (e.g.
    ``Depends`` -> ``fastapi.Depends``, ``D`` -> ``fastapi.Depends``);
    ``local_defs`` is the set of simple names defined in this file (impostor
    refusal). Emits an ``injects`` signal (enclosing function -> resolved
    provider callable) for each ``param = Depends(provider)`` default and each
    ``Annotated[T, Depends(provider)]`` parameter. Bare ``Depends()`` and a
    same-named non-FastAPI ``Depends`` emit nothing.

    Wave 1p9q8: ``source`` (the raw file text) enables a cheap substring
    pre-check — a file with no ``Depends`` token cannot emit any signal, so the
    AST walk is skipped entirely.
    """
    # Fast path: no `Depends` token in the raw source => no signal possible.
    if source and _PY_DI_TRIGGER not in source:
        return []

    def is_depends(call: ast.Call) -> bool:
        fn = call.func
        if isinstance(fn, ast.Name):
            name = fn.id
            if name in import_aliases:
                return _py_origin_is_depends(import_aliases[name])
            if name in local_defs:
                return False  # same-file impostor
            return name == _PY_DEPENDS_NAME  # unbound canonical token self-identifies
        if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name):
            if fn.attr != _PY_DEPENDS_NAME:
                return False
            origin = import_aliases.get(fn.value.id)
            return bool(origin) and origin.split(".")[0] == _PY_DEPENDS_ROOT
        return False

    def provider_name(call: ast.Call) -> str | None:
        if not call.args:
            return None  # bare Depends() -> annotation-driven, no guess
        arg = call.args[0]
        if isinstance(arg, ast.Name):
            return arg.id
        if isinstance(arg, ast.Attribute):
            return arg.attr  # last segment; cross-file resolution keys on it
        return None  # string / other -> no edge

    signals: list[dict[str, Any]] = []

    def emit_from_call(call: ast.Call, consumer: str) -> None:
        if not is_depends(call):
            return
        provider = provider_name(call)
        if not provider:
            return
        signals.append({
            "kind": "injects",
            "file": rel_path,
            "consumer_type": consumer,
            "dependency_type": provider,
            "confidence": "EXTRACTED",
            "evidence": f"FastAPI Depends({provider}) in {consumer}",
            "faithful_external": True,
        })

    def scan_function(func: ast.FunctionDef | ast.AsyncFunctionDef, consumer: str) -> None:
        args = func.args
        # Depends(...) in a parameter default.
        for default in list(args.defaults) + [d for d in args.kw_defaults if d is not None]:
            if isinstance(default, ast.Call):
                emit_from_call(default, consumer)
        # Depends(...) inside Annotated[T, Depends(provider)] annotations.
        all_args = list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
        if args.vararg:
            all_args.append(args.vararg)
        if args.kwarg:
            all_args.append(args.kwarg)
        for arg in all_args:
            ann = getattr(arg, "annotation", None)
            if isinstance(ann, ast.Subscript) and _is_annotated(ann.value):
                slice_node = ann.slice
                elts = slice_node.elts if isinstance(slice_node, ast.Tuple) else [slice_node]
                for elt in elts:
                    if isinstance(elt, ast.Call):
                        emit_from_call(elt, consumer)

    def walk(node: ast.AST, scope: list[str]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                walk(child, scope + [child.name])
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                consumer = ".".join(scope + [child.name])
                scan_function(child, consumer)
                walk(child, scope + [child.name])
            else:
                walk(child, scope)

    walk(tree, [])
    return signals


def _is_annotated(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "Annotated"
    if isinstance(node, ast.Attribute):
        return node.attr == "Annotated"
    return False


# --- TypeScript tree-sitter helpers (wave 1p9q7) --------------------------

def _ts_text(node, source_bytes: bytes) -> str:
    if node is None:
        return ""
    try:
        return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace").strip()
    except Exception:
        return ""


def _ts_named(node) -> list:
    return list(getattr(node, "named_children", []) or [])


def _ts_child_of_type(node, *types: str):
    for child in _ts_named(node):
        if getattr(child, "type", "") in types:
            return child
    return None


def _ts_children_of_type(node, *types: str) -> list:
    return [c for c in _ts_named(node) if getattr(c, "type", "") in types]


def _ts_first_named(node):
    kids = _ts_named(node)
    return kids[0] if kids else None


def _ts_iter_all(node):
    stack = [node]
    while stack:
        cur = stack.pop()
        yield cur
        stack.extend(_ts_named(cur))


def _ts_string_value(node, sb: bytes) -> str:
    frag = _ts_child_of_type(node, "string_fragment")
    if frag is not None:
        return _ts_text(frag, sb)
    return _ts_text(node, sb).strip("'\"`")


def _ts_di_import_origins(root, sb: bytes) -> dict[str, tuple[str, str]]:
    """Map each imported local name to ``(module_source, original_name)``.

    Aliases resolve to the ORIGINAL name (``import { Inject as I }`` ->
    ``{"I": ("inversify", "Inject")}``) so the idiom check runs on the origin,
    not the local spelling.
    """
    origins: dict[str, tuple[str, str]] = {}
    for stmt in _ts_iter_all(root):
        if getattr(stmt, "type", "") != "import_statement":
            continue
        module = _ts_string_value(_ts_child_of_type(stmt, "string"), sb) if _ts_child_of_type(stmt, "string") else ""
        clause = _ts_child_of_type(stmt, "import_clause")
        if clause is None:
            continue
        named = _ts_child_of_type(clause, "named_imports")
        if named is None:
            continue
        for spec in _ts_children_of_type(named, "import_specifier"):
            ids = _ts_children_of_type(spec, "identifier")
            if not ids:
                continue
            imported = _ts_text(ids[0], sb)
            local = _ts_text(ids[1], sb) if len(ids) > 1 else imported
            if local:
                origins[local] = (module, imported)
    return origins


def _ts_local_decl_names(root, sb: bytes) -> set[str]:
    names: set[str] = set()
    for node in _ts_iter_all(root):
        ntype = getattr(node, "type", "")
        if ntype in ("class_declaration", "function_declaration"):
            nm = node.child_by_field_name("name")
            if nm is not None:
                names.add(_ts_text(nm, sb))
        elif ntype == "variable_declarator":
            nm = node.child_by_field_name("name")
            if nm is not None and getattr(nm, "type", "") == "identifier":
                names.add(_ts_text(nm, sb))
    return names


def _ts_module_matches(module: str, allowed: tuple[str, ...]) -> bool:
    return any(module == m or module.startswith(m + "/") for m in allowed)


def _ts_idiom_ok(
    name: str,
    canonical: set[str],
    allowed_modules: tuple[str, ...],
    origins: dict[str, tuple[str, str]],
    local_decls: set[str],
) -> bool:
    """Negative origin check for a distinctive idiom name (wave 1p9q7)."""
    o = origins.get(name)
    if o is not None:
        module, imported = o
        return imported in canonical and _ts_module_matches(module, allowed_modules)
    if name in local_decls:
        return False  # same-file impostor
    return name in canonical  # unbound canonical spelling self-identifies


def _ts_decorator_name_and_args(dec, sb: bytes) -> tuple[str | None, Any]:
    child = _ts_first_named(dec)
    if child is None:
        return None, None
    ctype = getattr(child, "type", "")
    if ctype == "call_expression":
        fn = child.child_by_field_name("function")
        return (_ts_text(fn, sb) if fn is not None else None), child.child_by_field_name("arguments")
    if ctype == "identifier":
        return _ts_text(child, sb), None
    return None, None


def _ts_class_decorators(class_node, sb: bytes) -> list:
    decs = _ts_children_of_type(class_node, "decorator")
    parent = getattr(class_node, "parent", None)
    if parent is not None and getattr(parent, "type", "") == "export_statement":
        decs = _ts_children_of_type(parent, "decorator") + decs
    return decs


def _ts_token_or_name(node, sb: bytes) -> tuple[str | None, bool]:
    ntype = getattr(node, "type", "")
    if ntype == "string":
        return _ts_string_value(node, sb), True
    if ntype == "identifier":
        return _ts_text(node, sb), False
    return None, False


def collect_ts_di_signals(rel_path: str, root, source_bytes: bytes) -> list[dict[str, Any]]:
    """AST-anchored NestJS/Inversify DI signals (wave 1p9q7).

    Recognizes ``@Injectable``/``@injectable`` constructor injection,
    ``@Inject(TOKEN)`` params, ``@Module({providers})`` provider objects, and
    Inversify ``bind(X).to(Y)``/``.toClass(Y)`` chains (positive-origin gated on
    an Inversify import). Emits ``injects``/``binds`` signals in the shared
    schema.

    Wave 1p9q8: a cheap raw-source pre-check short-circuits to ``[]`` when the
    file contains none of the DI trigger tokens — skipping the full tree walk
    (and the import-origin / local-decl scans) for the common no-DI file.
    """
    # Fast path: no DI idiom token in the raw source => no signal possible.
    # Mirrors the Python collector's `if source and ...` guard for symmetry;
    # inert in practice (tree-sitter always supplies non-empty bytes here).
    if source_bytes and not any(tok in source_bytes for tok in _TS_DI_TRIGGER_TOKENS):
        return []
    origins = _ts_di_import_origins(root, source_bytes)
    local_decls = _ts_local_decl_names(root, source_bytes)
    has_inversify = any(mod in _TS_INVERSIFY_MODULES for mod, _n in origins.values())
    signals: list[dict[str, Any]] = []

    def is_injectable(name: str) -> bool:
        return (
            _ts_idiom_ok(name, {"Injectable"}, _TS_NESTJS_MODULES, origins, local_decls)
            or _ts_idiom_ok(name, {"injectable"}, _TS_INVERSIFY_MODULES, origins, local_decls)
        )

    def is_inject(name: str) -> bool:
        return _ts_idiom_ok(name, {"Inject", "inject"}, _TS_DI_MODULES, origins, local_decls)

    def is_module(name: str) -> bool:
        return _ts_idiom_ok(name, {"Module"}, _TS_NESTJS_MODULES, origins, local_decls)

    def emit_injects(consumer: str, dependency: str, evidence: str, *, token: bool = False) -> None:
        sig = {
            "kind": "injects",
            "file": rel_path,
            "consumer_type": consumer,
            "dependency_type": dependency,
            "confidence": "EXTRACTED",
            "evidence": evidence,
            "faithful_external": True,
        }
        if token:
            sig["dependency_token"] = True
        signals.append(sig)

    def emit_binds(iface: str, impl: str, evidence: str, *, iface_token: bool = False, impl_token: bool = False) -> None:
        sig = {
            "kind": "binds",
            "file": rel_path,
            "interface_type": iface,
            "implementation_type": impl,
            "confidence": "EXTRACTED",
            "evidence": evidence,
            "faithful_external": True,
        }
        if iface_token:
            sig["interface_token"] = True
        if impl_token:
            sig["implementation_token"] = True
        signals.append(sig)

    def emit_module_providers(args_node) -> None:
        obj = _ts_first_named(args_node) if args_node is not None else None
        if obj is None or getattr(obj, "type", "") != "object":
            return
        for pair in _ts_children_of_type(obj, "pair"):
            key = pair.child_by_field_name("key")
            if key is None or _ts_text(key, source_bytes) != "providers":
                continue
            value = pair.child_by_field_name("value")
            arr = value if value is not None and getattr(value, "type", "") == "array" else _ts_child_of_type(value, "array")
            if arr is None:
                continue
            for elem in _ts_named(arr):
                if getattr(elem, "type", "") == "object":
                    emit_provider_object(elem)
                # a bare-class provider is a self-registration; the class's own
                # @Injectable constructor deps are captured separately — no
                # distinct binds edge, so nothing is emitted here.

    def emit_provider_object(obj) -> None:
        provide_val: str | None = None
        provide_token = False
        impl_val: str | None = None
        for pair in _ts_children_of_type(obj, "pair"):
            key = pair.child_by_field_name("key")
            value = pair.child_by_field_name("value")
            if key is None or value is None:
                continue
            kname = _ts_text(key, source_bytes)
            if kname == "provide":
                provide_val, provide_token = _ts_token_or_name(value, source_bytes)
            elif kname == "useClass":
                impl_name, _tok = _ts_token_or_name(value, source_bytes)
                if impl_name and not _tok:
                    impl_val = impl_name
        if provide_val and impl_val:
            emit_binds(
                provide_val, impl_val,
                evidence=f"@Module provider {{ provide: {provide_val}, useClass: {impl_val} }}",
                iface_token=provide_token,
            )

    def emit_ctor_params(class_name: str, class_node) -> None:
        body = class_node.child_by_field_name("body")
        if body is None:
            return
        ctor = None
        for method in _ts_children_of_type(body, "method_definition"):
            nm = method.child_by_field_name("name")
            if nm is not None and _ts_text(nm, source_bytes) == "constructor":
                ctor = method
                break
        if ctor is None:
            return
        params = ctor.child_by_field_name("parameters")
        if params is None:
            return
        for param in _ts_children_of_type(params, "required_parameter", "optional_parameter"):
            emit_ctor_param(class_name, param)

    def emit_ctor_param(class_name: str, param) -> None:
        # @Inject(TOKEN) takes precedence over the type annotation.
        for dec in _ts_children_of_type(param, "decorator"):
            dname, dargs = _ts_decorator_name_and_args(dec, source_bytes)
            if dname and is_inject(dname):
                token = _ts_first_named(dargs) if dargs is not None else None
                if token is None:
                    return
                name, is_tok = _ts_token_or_name(token, source_bytes)
                if not name:
                    return
                emit_injects(class_name, name, evidence=f"@Inject({name}) in {class_name}", token=is_tok)
                return
        ann = _ts_child_of_type(param, "type_annotation")
        if ann is None:
            return
        type_node = _ts_child_of_type(ann, "type_identifier")
        if type_node is None:
            return  # union / generic / predefined type -> no guess
        tname = _ts_text(type_node, source_bytes)
        if not tname or tname in _TS_PRIMITIVE_TYPES:
            return
        emit_injects(class_name, tname, evidence=f"constructor injection in {class_name}")

    def maybe_bind_chain(node) -> None:
        if getattr(node, "type", "") != "call_expression":
            return
        fn = node.child_by_field_name("function")
        if fn is None or getattr(fn, "type", "") != "member_expression":
            return
        prop = fn.child_by_field_name("property")
        if prop is None or _ts_text(prop, source_bytes) not in ("to", "toClass"):
            return
        inner = fn.child_by_field_name("object")
        if inner is None or getattr(inner, "type", "") != "call_expression":
            return
        inner_fn = inner.child_by_field_name("function")
        bind_ok = False
        if inner_fn is not None:
            if getattr(inner_fn, "type", "") == "member_expression":
                ip = inner_fn.child_by_field_name("property")
                bind_ok = ip is not None and _ts_text(ip, source_bytes) == "bind"
            elif getattr(inner_fn, "type", "") == "identifier":
                bind_ok = _ts_text(inner_fn, source_bytes) == "bind"
        if not bind_ok:
            return
        iface_node = _ts_first_named(inner.child_by_field_name("arguments"))
        impl_node = _ts_first_named(node.child_by_field_name("arguments"))
        if iface_node is None or impl_node is None:
            return
        iface, iface_tok = _ts_token_or_name(iface_node, source_bytes)
        impl, impl_tok = _ts_token_or_name(impl_node, source_bytes)
        if not iface or not impl:
            return
        emit_binds(
            iface, impl,
            evidence=f"bind({iface}).{_ts_text(prop, source_bytes)}({impl})",
            iface_token=iface_tok, impl_token=impl_tok,
        )

    for node in _ts_iter_all(root):
        if getattr(node, "type", "") != "class_declaration":
            continue
        name_node = node.child_by_field_name("name")
        class_name = _ts_text(name_node, source_bytes) if name_node is not None else ""
        if not class_name:
            continue
        injectable = False
        for dec in _ts_class_decorators(node, source_bytes):
            dname, dargs = _ts_decorator_name_and_args(dec, source_bytes)
            if not dname:
                continue
            if is_injectable(dname):
                injectable = True
            if is_module(dname):
                emit_module_providers(dargs)
        if injectable:
            emit_ctor_params(class_name, node)

    if has_inversify:
        for node in _ts_iter_all(root):
            maybe_bind_chain(node)

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


def _external_di_node(name: str, node_map: dict[str, dict[str, Any]]) -> str:
    # Wave 1p9q7: an unresolved/ambiguous DI target (or a string token) mints a
    # PLAIN `external::<name>` code node — NOT a reserved `external::di::` form.
    # An unresolved DI provider is an ordinary code symbol in the same namespace
    # as any other `external::` code target (Decision Log 2026-07-05).
    node_id = f"external::{name}"
    if node_id not in node_map:
        node_map[node_id] = {
            "id": node_id,
            "label": name,
            "kind": "module",
            "source_file": "",
            "source_location": "1:0",
            "layer": "project",
        }
    return node_id


def _resolve_di_target(
    name: str,
    *,
    prefer_file: str | None,
    node_map: dict[str, dict[str, Any]],
    type_index: dict[str, list[str]],
    faithful: bool,
    force_external: bool,
) -> str | None:
    # Wave 1p9q7: shared binds-endpoint resolver. `faithful=False` +
    # `force_external=False` reproduces `_ensure_type_node` exactly (JVM/.NET
    # path, byte-identical). A faithful signal that finds no existing type node
    # goes `external::` rather than synthesizing a project node; a string token
    # (`force_external`) is external by construction.
    if force_external:
        return _external_di_node(name, node_map)
    if faithful:
        # Wave 1p9q8: unique-candidate discipline — mirror the faithful injects
        # path (`len==1` else external). A faithful binds endpoint resolves only
        # when exactly ONE candidate type node exists; an ambiguous cross-file
        # same-name twin (two `PgDb` classes for one `useClass: PgDb` /
        # `bind(Token).to(PgDb)`) must go `external::`, never an arbitrary
        # `_pick_node` shortest-length/prefer-file pick. `_index_type_nodes`
        # double-lists a node under its label AND its id-tail, so dedup before
        # counting so a genuinely-unique target still counts as one.
        candidates = list(dict.fromkeys(type_index.get(name, [])))
        if len(candidates) == 1:
            return candidates[0]
        return _external_di_node(name, node_map)
    existing = _pick_node(type_index.get(name, []), prefer_file=prefer_file)
    if existing:
        return existing
    return _ensure_type_node(
        name,
        prefer_file=prefer_file,
        node_map=node_map,
        type_index=type_index,
    )


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
        faithful = bool(signal.get("faithful_external"))
        impl_node = _resolve_di_target(
            impl,
            prefer_file=rel,
            node_map=node_map,
            type_index=type_index,
            faithful=faithful,
            force_external=bool(signal.get("implementation_token")),
        )
        iface_node = _resolve_di_target(
            iface,
            prefer_file=rel,
            node_map=node_map,
            type_index=type_index,
            faithful=faithful,
            force_external=bool(signal.get("interface_token")),
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
        faithful = bool(signal.get("faithful_external"))
        if signal.get("dependency_token"):
            # Wave 1p9q7: a string DI token is external by construction.
            dep_node = _external_di_node(dependency, node_map)
        elif faithful:
            # Wave 1p9q7: unique-candidate rule — resolve only on a single
            # candidate (a bind target, else a unique type node); ambiguity or
            # a miss goes `external::` rather than picking or synthesizing.
            bind_candidates = binds_map.get(dependency, [])
            if len(bind_candidates) == 1:
                dep_node = bind_candidates[0][1]
            else:
                # `_index_type_nodes` lists a node twice under its name (label ==
                # id-tail); dedup so a genuinely-unique target counts as one.
                dep_matches = list(dict.fromkeys(type_index.get(dependency, [])))
                dep_node = dep_matches[0] if len(dep_matches) == 1 else _external_di_node(dependency, node_map)
        else:
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
