"""AST census engine for the line-ending rule (wave 244in, change 244fj).

Scans every non-test ``.py`` file under ``.wavefoundry/framework/scripts/``
(including ``benchmarks/``) and reports:

* every write primitive call (Requirement 10.1), with its text-mode
  ``newline`` status;
* every writer function: a function whose body calls a primitive directly or
  calls a function classified ``wrapper`` in the table (Requirement 10.2).
  Writer status propagates only through wrappers;
* every wrapper call site, keyed ``caller -> wrapper #ordinal``.

``tests/test_line_ending_census.py`` compares the report with the checked-in
table ``tests/fixtures/line-ending-census.json``.  The engine is test-only and
does not ship (``build_pack`` excludes ``scripts/tests/``).
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
TABLE_PATH = Path(__file__).resolve().parent / "fixtures" / "line-ending-census.json"

CLASSES = {"in_place", "in_place_raw", "generated", "wrapper", "exempt"}
SITE_CLASSES = {"in_place", "in_place_raw", "generated", "exempt", "wrapper"}

# Call receivers whose ``.open(...)`` is not a file write primitive.
_NON_FILE_OPEN_RECEIVERS = {"os", "webbrowser", "zipfile", "tarfile", "gzip", "bz2", "lzma"}
_OPEN_FUNCS = {"open"}  # builtin
_MODULE_OPEN = {("io", "open"), ("os", "fdopen"), ("tempfile", "NamedTemporaryFile"), ("codecs", "open")}


@dataclass
class Primitive:
    function: str
    line: int
    kind: str
    text_mode: bool
    newline_set: bool
    newline_value: object = None  # the literal ``newline`` value, when one is given


@dataclass
class FunctionInfo:
    key: str
    module: str
    node: ast.AST
    primitives: list = field(default_factory=list)
    calls: list = field(default_factory=list)  # (resolved_key or None, attr_name, line)
    calls_merge: bool = False


def module_name(path: Path, root: Path = SCRIPTS_ROOT) -> str:
    rel = path.relative_to(root).with_suffix("")
    return ".".join(rel.parts)


def iter_source_files(root: Path = SCRIPTS_ROOT):
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        if rel.parts[0] == "tests":
            continue
        if any(part in {"__pycache__"} for part in rel.parts):
            continue
        yield path


def _const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _mode_of(call: ast.Call, positional_index: int, default: str | None, *, dynamic_positional: bool = True):
    """The call's mode string; ``"?"`` when it is not a literal.

    ``dynamic_positional=False`` (``.open(...)`` methods) reads a non-literal
    first positional argument as not a mode (``ZipFile.open(info)``,
    ``opener.open(url)``) and returns ``default``.
    """
    for kw in call.keywords:
        if kw.arg == "mode":
            return _const_str(kw.value) if _const_str(kw.value) is not None else "?"
    if len(call.args) > positional_index:
        value = _const_str(call.args[positional_index])
        if value is not None:
            return value
        return "?" if dynamic_positional else default
    return default


def _newline_set(call: ast.Call) -> bool:
    for kw in call.keywords:
        if kw.arg == "newline":
            return not (isinstance(kw.value, ast.Constant) and kw.value.value is None)
        if kw.arg is None:  # **kwargs: cannot tell; treat as set
            return True
    return False


def _newline_value(call: ast.Call):
    for kw in call.keywords:
        if kw.arg == "newline" and isinstance(kw.value, ast.Constant):
            return kw.value.value
    return None


def _is_write_mode(mode: str) -> bool:
    return mode == "?" or any(flag in mode for flag in "wax+")


def _text_mode(mode: str):
    """True for text, False for binary, None when the mode is not a literal."""
    if mode == "?":
        return None
    return "b" not in mode


class _ModuleScan:
    """Collect functions, imports, primitives and calls for one module."""

    def __init__(self, module: str, tree: ast.Module, framework_modules: set[str]):
        self.module = module
        self.tree = tree
        self.framework_modules = framework_modules
        self.package = module.rsplit(".", 1)[0] if "." in module else ""
        self.functions: dict[str, FunctionInfo] = {}
        self.top_defs: set[str] = set()
        self.module_aliases: dict[str, str] = {}  # local name -> framework module
        self.from_names: dict[str, str] = {}  # local name -> "module.func"

    # -- import resolution -------------------------------------------------
    def _resolve_from_module(self, node: ast.ImportFrom) -> str | None:
        base = node.module or ""
        if node.level:
            parts = self.module.split(".")[:-1]
            if node.level > 1:
                parts = parts[: len(parts) - (node.level - 1)]
            base = ".".join([p for p in parts if p] + ([base] if base else []))
        return base

    def _bind_imports(self, body_nodes, module_aliases, from_names):
        for node in body_nodes:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if name in self.framework_modules:
                        module_aliases[alias.asname or name.split(".")[0]] = name
                    elif self.package and f"{self.package}.{name}" in self.framework_modules:
                        module_aliases[alias.asname or name] = f"{self.package}.{name}"
            elif isinstance(node, ast.ImportFrom):
                base = self._resolve_from_module(node)
                if base is None:
                    continue
                for alias in node.names:
                    local = alias.asname or alias.name
                    full_mod = f"{base}.{alias.name}" if base else alias.name
                    if full_mod in self.framework_modules:
                        module_aliases[local] = full_mod
                    elif base in self.framework_modules:
                        from_names[local] = f"{base}.{alias.name}"

    def scan(self):
        self._parents = {}
        for parent in ast.walk(self.tree):
            for child in ast.iter_child_nodes(parent):
                self._parents[child] = parent
        # Module-level imports anywhere at top level (including try/if blocks).
        top_nodes = [n for n in ast.walk(self.tree) if isinstance(n, (ast.Import, ast.ImportFrom))
                     and self._is_module_level(n)]
        self._bind_imports(top_nodes, self.module_aliases, self.from_names)
        for node in self.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.top_defs.add(node.name)
        self._visit_scope(self.tree, [], {}, self.module_aliases, self.from_names)
        return self

    def _is_module_level(self, node) -> bool:
        current = node
        parents = self._parents
        while current in parents:
            current = parents[current]
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                return False
        return True

    def _visit_scope(self, scope_node, qual, nested_defs, local_aliases, local_from):
        """Walk ``scope_node``'s body; functions become FunctionInfo entries."""
        key = f"{self.module}:{'.'.join(qual) or '<module>'}"
        info = FunctionInfo(key=key, module=self.module, node=scope_node)
        self.functions[key] = info
        body = scope_node.body if hasattr(scope_node, "body") else []
        # Imports local to this function.
        aliases = dict(local_aliases)
        froms = dict(local_from)
        if qual:
            local_imports = [n for n in self._own_nodes(scope_node) if isinstance(n, (ast.Import, ast.ImportFrom))]
            self._bind_imports(local_imports, aliases, froms)
        # Nested defs visible by bare name inside this scope.
        nested = dict(nested_defs)
        for node in self._own_nodes(scope_node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and qual:
                nested[node.name] = f"{self.module}:{'.'.join(qual + [node.name])}"
        for node in self._own_nodes(scope_node):
            if isinstance(node, ast.Call):
                self._record_call(info, node, nested, aliases, froms)
        for node in self._child_scopes(scope_node):
            if isinstance(node, ast.ClassDef):
                self._visit_class(node, qual + [node.name], nested, aliases, froms)
            else:
                self._visit_scope(node, qual + [node.name], nested, aliases, froms)

    def _visit_class(self, cls, qual, nested, aliases, froms):
        for node in cls.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._visit_scope(node, qual + [node.name], nested, aliases, froms)
            elif isinstance(node, ast.ClassDef):
                self._visit_class(node, qual + [node.name], nested, aliases, froms)
            else:
                # class-body statements are attributed to the module scope entry
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call):
                        self._record_call(self.functions[f"{self.module}:<module>"], sub, nested, aliases, froms)

    def _own_nodes(self, scope_node):
        """Nodes inside ``scope_node`` excluding nested function/class bodies."""
        stack = list(ast.iter_child_nodes(scope_node))
        while stack:
            node = stack.pop()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # decorators and defaults belong to the enclosing scope
                for dec in node.decorator_list:
                    stack.append(dec)
                continue
            yield node
            stack.extend(ast.iter_child_nodes(node))

    def _child_scopes(self, scope_node):
        stack = list(ast.iter_child_nodes(scope_node))
        while stack:
            node = stack.pop()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                yield node
                continue
            stack.extend(ast.iter_child_nodes(node))

    # -- calls -------------------------------------------------------------
    def _record_call(self, info: FunctionInfo, call: ast.Call, nested, aliases, froms):
        func = call.func
        line = call.lineno
        # merge detection
        if isinstance(func, ast.Attribute) and func.attr == "merge" and isinstance(func.value, ast.Name):
            receiver = func.value.id
            if receiver == "line_endings" or aliases.get(receiver) == "line_endings":
                info.calls_merge = True
        if isinstance(func, ast.Name) and froms.get(func.id) == "line_endings.merge":
            info.calls_merge = True
        prim = self._primitive(call, aliases, froms)
        if prim is not None:
            kind, text_mode = prim
            info.primitives.append(Primitive(info.key, line, kind, text_mode, _newline_set(call), _newline_value(call)))
            return
        resolved = None
        if isinstance(func, ast.Name):
            name = func.id
            if name in nested:
                resolved = nested[name]
            elif name in froms:
                target = froms[name]
                mod, _, fn = target.rpartition(".")
                resolved = f"{mod}:{fn}"
            elif name in self.top_defs:
                resolved = f"{self.module}:{name}"
        elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            receiver = func.value.id
            if receiver in aliases:
                resolved = f"{aliases[receiver]}:{func.attr}"
            elif receiver in {"self", "cls"}:
                # same-class method: resolved by the caller's enclosing class
                parts = info.key.split(":", 1)[1].split(".")
                if len(parts) >= 2:
                    resolved = f"{self.module}:{'.'.join(parts[:-1])}.{func.attr}"
        info.calls.append((resolved, func.attr if isinstance(func, ast.Attribute) else None, line))

    def _primitive(self, call: ast.Call, aliases, froms):
        func = call.func
        if isinstance(func, ast.Attribute):
            attr = func.attr
            receiver = func.value.id if isinstance(func.value, ast.Name) else None
            receiver_module = aliases.get(receiver) if receiver else None
            if receiver_module == "contained_files" and attr == "write_contained_bytes":
                return "write_contained_bytes", False
            if receiver_module is not None:
                return None  # a framework function call, resolved separately
            if attr == "write_text":
                return "Path.write_text", True
            if attr == "write_bytes":
                return "Path.write_bytes", False
            if receiver == "os" and attr == "write":
                return "os.write", False
            if receiver == "os" and attr == "fdopen":
                mode = _mode_of(call, 1, "r")
                if _is_write_mode(mode):
                    return "os.fdopen", _text_mode(mode)
                return None
            if receiver == "io" and attr == "open":
                mode = _mode_of(call, 1, "r")
                if _is_write_mode(mode):
                    return "io.open", _text_mode(mode)
                return None
            if receiver == "tempfile" and attr == "NamedTemporaryFile":
                mode = _mode_of(call, 0, "w+b")
                if _is_write_mode(mode):
                    return "tempfile.NamedTemporaryFile", _text_mode(mode)
                return None
            if attr == "open" and receiver not in _NON_FILE_OPEN_RECEIVERS:
                mode = _mode_of(call, 0, "r", dynamic_positional=False)
                if _is_write_mode(mode):
                    return "Path.open", _text_mode(mode)
                return None
            return None
        if isinstance(func, ast.Name):
            name = func.id
            if froms.get(name) == "contained_files.write_contained_bytes":
                return "write_contained_bytes", False
            if name == "open" and name not in froms:
                mode = _mode_of(call, 1, "r")
                if _is_write_mode(mode):
                    return "open", _text_mode(mode)
                return None
            if name == "NamedTemporaryFile" and name not in froms:
                mode = _mode_of(call, 0, "w+b")
                if _is_write_mode(mode):
                    return "tempfile.NamedTemporaryFile", _text_mode(mode)
        return None


def scan_tree(root: Path = SCRIPTS_ROOT, extra_sources: dict | None = None):
    """Return ``{function key: FunctionInfo}`` for the whole scope.

    ``extra_sources`` maps a module name to source text that replaces (or
    adds) that module, for known-bad copies.
    """
    sources: dict[str, str] = {}
    for path in iter_source_files(root):
        sources[module_name(path, root)] = path.read_text(encoding="utf-8")
    if extra_sources:
        sources.update(extra_sources)
    framework_modules = set(sources)
    functions: dict[str, FunctionInfo] = {}
    for mod, text in sources.items():
        tree = ast.parse(text)
        scan = _ModuleScan(mod, tree, framework_modules).scan()
        functions.update(scan.functions)
    return functions


def _merges(key: str, entry: dict, functions: dict) -> bool:
    """``key`` calls ``line_endings.merge`` itself, or its entry names a
    ``merged_by`` planner that calls merge and a ``merged_by_reason``.  The
    review-policy planners merge so that their plan holds the final bytes and
    the apply step's "changed after preflight" checks compare those bytes; the
    apply step publishes the planned bytes it receives."""
    info = functions.get(key)
    if info is None:
        return False
    if info.calls_merge:
        return True
    planner = entry.get("merged_by")
    return bool(
        planner and entry.get("merged_by_reason")
        and planner in functions and functions[planner].calls_merge
    )


def load_table(path: Path = TABLE_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def census(table: dict, functions: dict) -> dict:
    """Compute the census report against ``table``.

    Returns ``{"writers": {key: info}, "sites": {site_key: (caller, wrapper)},
    "failures": [str, ...]}``.
    """
    entries = table["functions"]
    site_entries = table["wrapper_call_sites"]
    wrappers = {key for key, entry in entries.items() if entry["class"] == "wrapper"}
    writers: dict[str, dict] = {}
    sites: dict[str, tuple] = {}
    for key, info in functions.items():
        wrapper_calls = []
        for resolved, _attr, line in info.calls:
            if resolved in wrappers:
                wrapper_calls.append((resolved, line))
        if info.primitives or wrapper_calls:
            writers[key] = {
                "primitive_calls": len(info.primitives),
                "wrapper_calls": len(wrapper_calls),
                "calls_merge": info.calls_merge,
            }
        ordinals: dict[str, int] = {}
        for resolved, _line in wrapper_calls:
            ordinals[resolved] = ordinals.get(resolved, 0) + 1
            sites[f"{key} -> {resolved} #{ordinals[resolved]}"] = (key, resolved)

    failures: list[str] = []
    for key, entry in entries.items():
        cls = entry.get("class")
        if cls not in CLASSES:
            failures.append(f"BAD_CLASS {key}: {cls!r}")
        if cls == "exempt" and not entry.get("reason"):
            failures.append(f"EXEMPT_WITHOUT_REASON {key}")
        if cls == "in_place_raw" and not entry.get("reason"):
            failures.append(f"RAW_WITHOUT_REASON {key}")
        if key not in writers:
            failures.append(f"STALE {key}: no longer writes")
            continue
        got = writers[key]
        if got["primitive_calls"] != entry.get("primitive_calls") or got["wrapper_calls"] != entry.get("wrapper_calls"):
            failures.append(
                f"COUNT {key}: table primitive={entry.get('primitive_calls')} wrapper={entry.get('wrapper_calls')}"
                f", tree primitive={got['primitive_calls']} wrapper={got['wrapper_calls']}"
            )
        if cls == "in_place" and not _merges(key, entry, functions):
            failures.append(f"IN_PLACE_WITHOUT_MERGE {key}")
    for key in writers:
        if key not in entries:
            failures.append(f"UNCLASSIFIED {key}")
    for site_key, (caller, _wrapper) in sites.items():
        entry = site_entries.get(site_key)
        if entry is None:
            failures.append(f"UNCLASSIFIED_SITE {site_key}")
            continue
        cls = entry.get("class")
        if cls not in SITE_CLASSES:
            failures.append(f"BAD_SITE_CLASS {site_key}: {cls!r}")
        if cls == "exempt" and not entry.get("reason"):
            failures.append(f"EXEMPT_SITE_WITHOUT_REASON {site_key}")
        if cls == "in_place" and not _merges(caller, entries.get(caller, {}), functions):
            failures.append(f"IN_PLACE_SITE_WITHOUT_MERGE {site_key}")
        if cls == "wrapper" and entries.get(caller, {}).get("class") != "wrapper":
            failures.append(f"WRAPPER_SITE_CALLER_NOT_WRAPPER {site_key}")
    for site_key in site_entries:
        if site_key not in sites:
            failures.append(f"STALE_SITE {site_key}")
    # Text-mode primitives must set newline, except process-log exemptions.
    for key, info in functions.items():
        entry = entries.get(key, {})
        # A process log, or an exempt writer with a stated reason that its
        # text write may translate (``newline_unset_reason``), is allowed.
        log_exempt = entry.get("class") == "exempt" and (
            entry.get("process_log") is True or bool(entry.get("newline_unset_reason"))
        )
        for prim in info.primitives:
            if prim.text_mode and not prim.newline_set and not log_exempt:
                failures.append(f"NEWLINE_UNSET {key} line {prim.line} ({prim.kind})")
            if prim.text_mode is None and not prim.newline_set and not entry.get("dynamic_mode_reason"):
                failures.append(f"DYNAMIC_MODE_UNCHECKED {key} line {prim.line} ({prim.kind})")
    # Council advisory (244in readiness): a function other writers call to do
    # their writing is a wrapper, never ``generated``.  A ``generated`` entry
    # pins its in-scope callers, so a new caller fails until it is reviewed;
    # a caller that is itself a writer (an orchestrator such as
    # ``render_agent_surfaces``) needs a recorded ``writer_callers_reason``.
    callers_of: dict[str, set[str]] = {}
    for key, info in functions.items():
        for resolved, _attr, _line in info.calls:
            if resolved is not None and resolved != key:
                callers_of.setdefault(resolved, set()).add(key)
    # The same pinning covers ``exempt`` entries (finding
    # 244in-arch-exempt-wrapper-blindspot): a new caller of an exempt writer
    # is not itself a writer, so without the pin it would never surface.
    for key, entry in entries.items():
        cls = entry.get("class")
        if cls not in {"generated", "exempt"}:
            continue
        label = cls.upper()
        callers = sorted(callers_of.get(key, set()))
        pinned = sorted(entry.get("callers", []))
        if callers != pinned:
            failures.append(f"{label}_CALLERS {key}: table {pinned}, tree {callers}")
        writer_callers = [caller for caller in callers if caller in writers]
        if writer_callers and not entry.get("writer_callers_reason"):
            failures.append(f"{label}_CALLED_BY_WRITER {key} <- {', '.join(writer_callers)}")
    # An in-place writer publishes ``merge``'s endings verbatim: a text-mode
    # write in an ``in_place`` or ``in_place_raw`` function may only pass
    # ``newline=""`` (a ``newline="\r\n"`` would rewrite every ending).
    for key, entry in entries.items():
        if entry.get("class") not in {"in_place", "in_place_raw"} or key not in functions:
            continue
        for prim in functions[key].primitives:
            if prim.text_mode is not False and prim.newline_set and prim.newline_value != "":
                failures.append(
                    f"IN_PLACE_NEWLINE {key} line {prim.line}: newline={prim.newline_value!r}"
                )
    return {"writers": writers, "sites": sites, "failures": failures, "callers_of": callers_of}
