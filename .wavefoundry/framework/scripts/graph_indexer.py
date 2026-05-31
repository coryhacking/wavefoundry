#!/usr/bin/env python3
"""Graph index extraction and persistence for Wavefoundry."""
from __future__ import annotations

import ast
import importlib
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

try:
    from tree_sitter import Language, Parser as _TSParser
    _TS_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when tree-sitter is not installed
    _TS_AVAILABLE = False
    Language = None  # type: ignore[assignment]
    _TSParser = None  # type: ignore[assignment]

GRAPH_SCHEMA_VERSION = "1"
GRAPH_BUILDER_VERSION = "7"
GRAPH_DIRNAME = "graph"
GRAPH_FILENAMES = {
    "project": "project-graph.json",
    "framework": "framework-graph.json",
}
GRAPH_STATE_FILENAMES = {
    "project": "project-graph-state.json",
    "framework": "framework-graph-state.json",
}

_DOC_EXTENSIONS = {".md", ".markdown", ".txt"}
_CODE_EXTENSIONS = {
    ".py",
    ".js", ".jsx", ".mjs", ".cjs",
    ".ts", ".tsx",
    ".go",
    ".rs",
    ".java",
    ".scala",
    ".cs",
    ".c",
    ".cpp",
    ".cc",
    ".cxx",
    ".h",
    ".hpp",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".tf",
    ".tfvars",
    ".hcl",
    ".tpl",
    ".kt",
    ".kts",
    ".swift",
    ".m",
    ".mm",
    ".rb",
    ".php",
    ".yaml",
    ".yml",
    ".toml",
    ".json",
    ".jsonc",
    ".css",
    ".scss",
    ".ps1",
    ".psm1",
    ".html",
    ".htm",
    ".sql",
    ".psql",
    ".pgsql",
    ".ddl",
    ".dml",
    ".tsql",
    ".hql",
    ".xml",
    ".jsp",
    ".xsd",
    ".xsl",
    ".xslt",
    ".svg",
    ".php",
}
_CODE_FILENAMES = {
    "Jenkinsfile", "Makefile", "GNUmakefile", "Dockerfile", "Vagrantfile", "Brewfile",
    "Fastfile", "Appfile", "Podfile", "Gemfile", "Procfile",
}
_STOP_TERMS = {
    "self", "cls", "main", "test", "tests", "run", "get", "set", "new",
}
_DOC_MATCH_STOP_TERMS = _STOP_TERMS | {
    "accept", "action", "active", "apply", "assert", "buffer", "caller",
    "client", "config", "create", "cursor", "define", "delete", "enable",
    "enabled", "errors", "export", "filter", "format", "handle", "header", "helper",
    "import", "insert", "length", "logger", "lookup", "method", "object",
    "option", "output", "params", "parser", "plugin", "reader", "record",
    "reduce", "remove", "render", "report", "result", "return", "runner",
    "schema", "search", "select", "sender", "server", "signal", "simple",
    "single", "source", "static", "status", "stream", "string", "struct",
    "suffix", "target", "update", "values", "verify", "worker", "writer",
    # Common config / JSON field names — too ambiguous for doc→code keyword edges.
    "auto_index", "change", "dashboard", "entrypoint", "host", "include_dirs",
    "poll_interval_ms", "port_range_end", "port_range_start", "preferred_port",
    "project_label", "task", "terminology", "version", "wave",
}
_DOC_PATH_SUFFIXES = (
    ".md", ".markdown", ".py", ".json", ".jsonc", ".js", ".jsx", ".mjs", ".cjs",
    ".ts", ".tsx", ".css", ".html", ".txt", ".yaml", ".yml", ".toml",
)
_DOC_SCAN_EXCLUDE_PREFIXES = frozenset({
    "docs/waves/", "docs/plans/", "docs/contributing/", "docs/reports/",
})
_MIN_DOC_MATCH_TERM_LEN = 6
_SHORT_SYMBOL_MAX_LEN = 2
_MINIFIED_FILE_RE = re.compile(
    r"(?:\.min\.|\.prod\.|\.production\.|\.bundle\.|\.chunk\.)", re.IGNORECASE
)

_PY_DEF_RE = re.compile(r"^(\s*)(async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)\b")
_JS_DEF_RE = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:function|class)\s+([A-Za-z_][A-Za-z0-9_]*)\b"
)
_JS_CONST_FN_RE = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_][A-Za-z0-9_]*)\s*=>"
)
_JS_REQUIRE_RE = re.compile(
    r"^\s*(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*require\(['\"]([^'\"]+)['\"]\)"
)
_JS_IMPORT_RE = re.compile(
    r"^\s*import\s+(.+?)\s+from\s+['\"]([^'\"]+)['\"]"
)
_JS_CALL_RE = re.compile(r"(?<![\w.])([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_FENCED_CODE_RE = re.compile(r"```[^\n]*\n(.*?)^```", re.DOTALL | re.MULTILINE)
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_MD_LINK_RE = re.compile(r"!?\[([^\]]*)\]\(([^)]+)\)")

_TS_LANGUAGE_MODULES: dict[str, tuple[str, str]] = {
    "javascript": ("tree_sitter_javascript", "language"),
    "typescript": ("tree_sitter_typescript", "language_typescript"),
    "go": ("tree_sitter_go", "language"),
    "rust": ("tree_sitter_rust", "language"),
    "java": ("tree_sitter_java", "language"),
    "c": ("tree_sitter_c", "language"),
    "cpp": ("tree_sitter_cpp", "language"),
    "csharp": ("tree_sitter_c_sharp", "language"),
    "bash": ("tree_sitter_bash", "language"),
    "kotlin": ("tree_sitter_kotlin", "language"),
    "swift": ("tree_sitter_swift", "language"),
    "objc": ("tree_sitter_objc", "language"),
    "hcl": ("tree_sitter_hcl", "language"),
    "scss": ("tree_sitter_scss", "language"),
    "make": ("tree_sitter_make", "language"),
    "scala": ("tree_sitter_scala", "language"),
    "html": ("tree_sitter_html", "language"),
    "ruby": ("tree_sitter_ruby", "language"),
    "yaml": ("tree_sitter_yaml", "language"),
    "toml": ("tree_sitter_toml", "language"),
    "json": ("tree_sitter_json", "language"),
    "css": ("tree_sitter_css", "language"),
    "powershell": ("tree_sitter_powershell", "language"),
    "sql": ("tree_sitter_sql", "language"),
    "xml": ("tree_sitter_xml", "language_xml"),
    "php": ("tree_sitter_php", "language_php"),
}

_TS_PARSERS: dict[str, Any | None] = {}
_TS_LANGS: dict[str, Any | None] = {}
_TS_WARNED: set[str] = set()

_TS_EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".fish": "bash",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".swift": "swift",
    ".m": "objc",
    ".mm": "objc",
    ".hcl": "hcl",
    ".tf": "hcl",
    ".tfvars": "hcl",
    ".scss": "scss",
    ".sass": "scss",
    ".make": "make",
    ".mk": "make",
    ".scala": "scala",
    ".html": "html",
    ".htm": "html",
    ".rb": "ruby",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".jsonc": "json",
    ".css": "css",
    ".ps1": "powershell",
    ".psm1": "powershell",
    ".sql": "sql",
    ".psql": "sql",
    ".pgsql": "sql",
    ".ddl": "sql",
    ".dml": "sql",
    ".tsql": "sql",
    ".hql": "sql",
    ".xml": "xml",
    ".jsp": "xml",
    ".xsd": "xml",
    ".xsl": "xml",
    ".xslt": "xml",
    ".svg": "xml",
    ".php": "php",
}

_TS_DEF_KEYWORDS = (
    "class", "interface", "struct", "enum", "trait", "record", "module",
    "namespace", "package", "function", "method", "constructor", "procedure",
    "macro", "rule", "resource", "object", "target", "task", "command",
    "table", "view", "trigger", "query", "block", "type", "definition",
    "declaration", "implementation", "item", "property", "attribute", "pair",
    "selector", "element", "tag", "pair", "entry",
)
_TS_IMPORT_KEYWORDS = ("import", "using", "include", "require", "source", "use", "load")
_TS_CALL_KEYWORDS = ("call", "invoke", "invocation", "command", "expression", "query", "access", "reference")
_TS_NAME_FIELD_PRIORITY = (
    "name", "identifier", "declarator", "target", "module", "path", "label",
    "field", "table", "view", "procedure", "function", "selector", "key", "attribute",
    "pattern", "object", "callee", "member", "alias",
)
_TS_MARKUP_ATTRS = ("id", "name", "role", "href", "src", "action", "for", "data", "path", "target")
_TS_SQL_DEF_KEYWORDS = ("create", "table", "view", "function", "procedure", "trigger", "schema")
_TS_SQL_REF_KEYWORDS = ("from", "join", "into", "update", "delete", "insert", "call", "with", "use")
_TS_CONFIG_NAME_HINTS = (
    "name", "id", "module", "class", "function", "task", "job", "step", "route", "path",
    "template", "script", "command", "resource", "provider", "output", "variable",
    "selector", "include", "import", "query", "table", "view", "procedure", "target",
    "workflow", "action", "handler", "entry", "rule",
)


def _repo_rel(path: str | Path) -> str:
    return str(path).replace("\\", "/")


def _is_minified_file(rel_path: str) -> bool:
    """Return True for bundled/minified artifacts that have no semantic graph value."""
    name = Path(rel_path).name
    return bool(_MINIFIED_FILE_RE.search(name))


def _extract_code_contexts(source_text: str) -> str:
    """Return concatenated text from fenced code blocks and inline backtick spans."""
    parts: list[str] = []
    fenced_ranges: list[tuple[int, int]] = []
    for m in _FENCED_CODE_RE.finditer(source_text):
        parts.append(m.group(1))
        fenced_ranges.append((m.start(), m.end()))
    for m in _INLINE_CODE_RE.finditer(source_text):
        if any(fs <= m.start() < fe for fs, fe in fenced_ranges):
            continue
        parts.append(m.group(1))
    return " ".join(parts)


def _extract_inline_code_contexts(source_text: str) -> str:
    """Inline backtick spans only — excludes fenced blocks (e.g. JSON config examples)."""
    parts: list[str] = []
    fenced_ranges: list[tuple[int, int]] = []
    for m in _FENCED_CODE_RE.finditer(source_text):
        fenced_ranges.append((m.start(), m.end()))
    for m in _INLINE_CODE_RE.finditer(source_text):
        if any(fs <= m.start() < fe for fs, fe in fenced_ranges):
            continue
        parts.append(m.group(1))
    return " ".join(parts)


def _resolve_doc_path_ref(href: str, rel_path: str, current_paths: set[str]) -> str | None:
    href = href.strip().split("#")[0].strip()
    if not href or href.startswith(("http://", "https://", "mailto:", "ftp://")):
        return None
    if href.startswith("/"):
        raw = href.lstrip("/")
    elif href.startswith(("./", "../")) or (href.startswith(".") and "/" in href):
        raw = href
    else:
        doc_dir = rel_path.rsplit("/", 1)[0] if "/" in rel_path else ""
        raw = (doc_dir + "/" + href) if doc_dir else href
    parts: list[str] = []
    for part in raw.split("/"):
        if part == "..":
            if parts:
                parts.pop()
        elif part and part != ".":
            parts.append(part)
    resolved = "/".join(parts)
    if not resolved or resolved == rel_path or resolved not in current_paths:
        return None
    return resolved


def _extract_doc_backtick_paths(source_text: str, rel_path: str, current_paths: set[str]) -> list[str]:
    """Repo-relative paths written in backticks (Cross-Links, path callouts)."""
    targets: list[str] = []
    seen: set[str] = set()
    for m in _INLINE_CODE_RE.finditer(source_text):
        raw = m.group(1).strip()
        if not raw or " " in raw:
            continue
        looks_like_path = (
            "/" in raw
            or raw.startswith(".")
            or any(raw.endswith(suffix) for suffix in _DOC_PATH_SUFFIXES)
        )
        if not looks_like_path:
            continue
        resolved = _resolve_doc_path_ref(raw, rel_path, current_paths)
        if resolved and resolved not in seen:
            seen.add(resolved)
            targets.append(resolved)
    return targets


def _is_module_node_id(node_id: str) -> bool:
    return bool(node_id) and "::" not in node_id


def _is_json_config_node_id(node_id: str) -> bool:
    if "::" not in node_id:
        return False
    return node_id.split("::", 1)[0].endswith((".json", ".jsonc"))


def _doc_term_allows_json_target(term: str, target_id: str) -> bool:
    if not _is_json_config_node_id(target_id):
        return True
    key = target_id.split("::", 1)[1]
    lower_term = term.lower()
    if "." in lower_term:
        return True
    key_tail = key.rsplit(".", 1)[-1].lower()
    if lower_term != key_tail:
        return False
    return len(lower_term) >= 10 or "_" in lower_term


def _filter_doc_code_targets(term: str, targets: set[str]) -> list[str]:
    if term in _DOC_MATCH_STOP_TERMS:
        return []
    path_like = (
        "/" in term
        or any(term.endswith(suffix) for suffix in _DOC_PATH_SUFFIXES)
    )
    kept: list[str] = []
    for target in sorted(targets):
        if not _doc_term_allows_json_target(term, target):
            continue
        if path_like and not _is_module_node_id(target):
            continue
        kept.append(target)
    return kept


def _doc_code_reference_confidence(term: str, target_id: str, *, match_count: int) -> str:
    if _is_module_node_id(target_id) and (
        "/" in term or any(term.endswith(suffix) for suffix in _DOC_PATH_SUFFIXES)
    ):
        return "EXTRACTED"
    if match_count == 1 and (len(term) >= 12 or "_" in term):
        return "EXTRACTED"
    return "AMBIGUOUS"


_DOC_MATCH_TERM_STRIP = ".,;:!?)]}\"'"


def _extract_doc_match_terms(code_ctx: str) -> set[str]:
    """Whole-token terms from markdown code spans for symbol lookup.

    Keeps hyphenated names and path segments intact — never splits
    ``project-context-memory`` into ``context``.
    """
    terms: set[str] = set()
    if not code_ctx:
        return terms
    for raw in re.split(r"\s+", code_ctx):
        chunk = raw.strip(_DOC_MATCH_TERM_STRIP)
        if not chunk:
            continue
        terms.add(chunk.lower())
        if "/" in chunk:
            base = chunk.rsplit("/", 1)[-1].strip(_DOC_MATCH_TERM_STRIP)
            if base:
                terms.add(base.lower())
                if "." in base:
                    stem = base.rsplit(".", 1)[0]
                    if stem:
                        terms.add(stem.lower())
        elif "." in chunk and not chunk.startswith("."):
            parts = chunk.split(".")
            for end in range(1, len(parts)):
                prefix = ".".join(parts[:end])
                if prefix:
                    terms.add(prefix.lower())
    return terms


def _extract_doc_links(source_text: str, rel_path: str, current_paths: set[str]) -> list[str]:
    """Return repo-relative paths of known files explicitly linked from this document."""
    targets: list[str] = []
    seen: set[str] = set()
    for m in _MD_LINK_RE.finditer(source_text):
        resolved = _resolve_doc_path_ref(m.group(2).strip(), rel_path, current_paths)
        if resolved and resolved not in seen:
            seen.add(resolved)
            targets.append(resolved)
    return targets


def _gitignored_paths(root: Path) -> frozenset[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--others", "--ignored", "--exclude-standard"],
            capture_output=True, text=True, cwd=str(root), timeout=30,
        )
        if result.returncode == 0:
            return frozenset(
                line.replace("\\", "/") for line in result.stdout.splitlines() if line.strip()
            )
    except Exception:
        pass
    return frozenset()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_stem(path: str) -> str:
    return Path(path).stem


def _kind_for_path(rel_path: str) -> str:
    rel = rel_path.replace("\\", "/")
    if rel.startswith(".wavefoundry/framework/seeds/"):
        return "seed"
    name = Path(rel).name
    suffix = Path(rel).suffix.lower()
    if name in _CODE_FILENAMES:
        return "code"
    if suffix in _CODE_EXTENSIONS:
        return "code"
    if rel.startswith("docs/") or rel.startswith(".wavefoundry/framework/seeds/"):
        return "doc"
    if suffix in _DOC_EXTENSIONS or rel.endswith(".prompt.md"):
        return "doc"
    return "doc"


def _node(
    node_id: str,
    label: str,
    kind: str,
    source_file: str,
    source_location: str,
    *,
    layer: str,
) -> dict[str, Any]:
    return {
        "id": node_id,
        "label": label,
        "kind": kind,
        "source_file": source_file,
        "source_location": source_location,
        "layer": layer,
    }


def _edge(
    source: str,
    target: str,
    relation: str,
    *,
    confidence: str,
    evidence: str | None = None,
) -> dict[str, Any]:
    payload = {
        "source": source,
        "target": target,
        "relation": relation,
        "confidence": confidence,
    }
    if evidence:
        payload["evidence"] = evidence
    return payload


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


_DI_SIGNALS_MOD = None


def _load_di_signals_module():
    global _DI_SIGNALS_MOD
    if _DI_SIGNALS_MOD is None:
        import importlib.util

        di_path = Path(__file__).resolve().parent / "graph_di_signals.py"
        spec = importlib.util.spec_from_file_location("graph_di_signals", di_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load graph_di_signals from {di_path}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        _DI_SIGNALS_MOD = mod
    return _DI_SIGNALS_MOD


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_symbol_name(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip()


def _simple_name(symbol_id: str) -> str:
    if "::" not in symbol_id:
        return symbol_id
    return symbol_id.rsplit("::", 1)[-1].split(".", 1)[-1]


def _path_term(path: str) -> str:
    stem = _file_stem(path)
    return stem if stem else path


def _is_module_graph_node(node: dict[str, Any]) -> bool:
    node_id = str(node.get("id") or "")
    if not node_id or "::" in node_id:
        return False
    if str(node.get("kind") or "") == "module":
        return True
    source_file = str(node.get("source_file") or "")
    return bool(source_file) and node_id == source_file


@dataclass(frozen=True)
class _TsLanguageProfile:
    mode: str


_TS_CODE_PROFILE = _TsLanguageProfile(mode="code")
_TS_MARKUP_PROFILE = _TsLanguageProfile(mode="markup")
_TS_SQL_PROFILE = _TsLanguageProfile(mode="sql")
_TS_CONFIG_PROFILE = _TsLanguageProfile(mode="config")

_TS_LANGUAGE_PROFILES: dict[str, _TsLanguageProfile] = {
    "javascript": _TS_CODE_PROFILE,
    "typescript": _TS_CODE_PROFILE,
    "go": _TS_CODE_PROFILE,
    "rust": _TS_CODE_PROFILE,
    "java": _TS_CODE_PROFILE,
    "c": _TS_CODE_PROFILE,
    "cpp": _TS_CODE_PROFILE,
    "csharp": _TS_CODE_PROFILE,
    "bash": _TS_CODE_PROFILE,
    "kotlin": _TS_CODE_PROFILE,
    "swift": _TS_CODE_PROFILE,
    "objc": _TS_CODE_PROFILE,
    "scala": _TS_CODE_PROFILE,
    "ruby": _TS_CODE_PROFILE,
    "php": _TS_CODE_PROFILE,
    "html": _TS_MARKUP_PROFILE,
    "xml": _TS_MARKUP_PROFILE,
    "sql": _TS_SQL_PROFILE,
    "yaml": _TS_CONFIG_PROFILE,
    "toml": _TS_CONFIG_PROFILE,
    "json": _TS_CONFIG_PROFILE,
    "css": _TS_CONFIG_PROFILE,
    "scss": _TS_CONFIG_PROFILE,
    "make": _TS_CONFIG_PROFILE,
    "hcl": _TS_CONFIG_PROFILE,
    "powershell": _TS_CONFIG_PROFILE,
}


def _ts_language_key_for_path(rel_path: str) -> str | None:
    path = Path(rel_path)
    name = path.name
    if name in {"Makefile", "GNUmakefile"}:
        return "make"
    if name in {"Fastfile", "Appfile", "Podfile", "Gemfile", "Procfile", "Vagrantfile", "Brewfile"}:
        return "ruby"
    suffix = path.suffix.lower()
    return _TS_EXTENSION_TO_LANGUAGE.get(suffix)


def _ts_get_language(lang_key: str):
    if not _TS_AVAILABLE:
        return None
    if lang_key in _TS_LANGS:
        return _TS_LANGS[lang_key]
    module_info = _TS_LANGUAGE_MODULES.get(lang_key)
    if not module_info:
        _TS_LANGS[lang_key] = None
        return None
    module_name, language_fn = module_info
    try:
        module = importlib.import_module(module_name)
        language_factory = getattr(module, language_fn)
        raw_language = language_factory()
        lang = Language(raw_language)
    except Exception:
        _TS_LANGS[lang_key] = None
        return None
    _TS_LANGS[lang_key] = lang
    return lang


def _ts_get_parser(lang_key: str):
    if lang_key in _TS_PARSERS:
        return _TS_PARSERS[lang_key]
    lang = _ts_get_language(lang_key)
    if lang is None:
        _TS_PARSERS[lang_key] = None
        return None
    try:
        parser = _TSParser(lang)
    except Exception:
        _TS_PARSERS[lang_key] = None
        return None
    _TS_PARSERS[lang_key] = parser
    return parser


def _ts_parse(lang_key: str, source_text: str):
    parser = _ts_get_parser(lang_key)
    if parser is None:
        if lang_key not in _TS_WARNED:
            _TS_WARNED.add(lang_key)
            if not _TS_AVAILABLE:
                print(f"build_index: tree-sitter unavailable; using fallback graph extraction for {lang_key}", flush=True)
            else:
                print(
                    f"build_index: tree-sitter grammar for {lang_key} unavailable; using fallback graph extraction",
                    flush=True,
                )
        return None
    try:
        return parser.parse(source_text.encode("utf-8", errors="replace"))
    except Exception:
        return None


def _ts_node_text(node, source_bytes: bytes) -> str:
    try:
        return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace").strip()
    except Exception:
        return ""


def _ts_clean_name(text: str) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    if not value:
        return ""
    value = value.strip("`'\"")
    value = value.rstrip(";,)")
    value = value.strip()
    match = re.search(r"[A-Za-z_][A-Za-z0-9_.$:#/\-]*", value)
    if match:
        return match.group(0)
    return value


def _ts_name_from_fields(node, source_bytes: bytes, *, field_names: tuple[str, ...] = _TS_NAME_FIELD_PRIORITY) -> str:
    for field_name in field_names:
        try:
            child = node.child_by_field_name(field_name)
        except Exception:
            child = None
        if child is None:
            continue
        candidate = _ts_clean_name(_ts_node_text(child, source_bytes))
        if candidate:
            return candidate
    return ""


def _ts_name_from_descendants(node, source_bytes: bytes) -> str:
    identifier_types = {
        "identifier",
        "field_identifier",
        "property_identifier",
        "type_identifier",
        "scoped_identifier",
        "qualified_identifier",
        "namespace_identifier",
        "tag_name",
        "object_reference",
        "key",
        "string",
        "string_literal",
        "raw_string_literal",
        "attribute",
        "pair",
    }
    try:
        for child in getattr(node, "named_children", []):
            child_type = str(getattr(child, "type", "") or "")
            if child_type in identifier_types:
                candidate = _ts_clean_name(_ts_node_text(child, source_bytes))
                if candidate:
                    return candidate
    except Exception:
        pass
    return ""


def _ts_markup_name_candidates(node, source_bytes: bytes) -> list[str]:
    text = ""
    try:
        for child in getattr(node, "named_children", []):
            if str(getattr(child, "type", "") or "") == "start_tag":
                text = _ts_node_text(child, source_bytes)
                break
    except Exception:
        text = ""
    if not text:
        text = _ts_node_text(node, source_bytes)
    candidates: list[str] = []
    for attr in ("id", "name", "role", "for"):
        for match in re.finditer(rf"\b{attr}\s*=\s*['\"]([^'\"]+)['\"]", text, re.IGNORECASE):
            candidate = _ts_clean_name(match.group(1))
            if candidate and candidate not in candidates:
                candidates.append(candidate)
    tag_match = re.match(r"\s*<\s*([A-Za-z_][A-Za-z0-9:_-]*)", text)
    if tag_match:
        tag = tag_match.group(1).casefold()
        if tag in {"a", "form", "button", "input", "label", "select", "option", "textarea"}:
            tag_value = _ts_clean_name(tag_match.group(1))
            if tag_value and tag_value not in candidates:
                candidates.append(tag_value)
    return candidates


def _ts_markup_import_nodes(node, source_bytes: bytes) -> bool:
    lower = str(getattr(node, "type", "") or "").lower()
    if any(token in lower for token in ("script", "style", "link", "iframe", "img", "source", "embed")):
        return True
    text = ""
    try:
        for child in getattr(node, "named_children", []):
            if str(getattr(child, "type", "") or "") == "start_tag":
                text = _ts_node_text(child, source_bytes)
                break
    except Exception:
        text = ""
    if not text:
        text = _ts_node_text(node, source_bytes)
    return bool(re.search(r"\b(?:src|href|action|xlink:href)\s*=\s*['\"][^'\"]+['\"]", text, re.IGNORECASE))


def _ts_name_candidates(node, source_bytes: bytes, mode: str | None = None) -> list[str]:
    candidates: list[str] = []
    if mode == "markup":
        for candidate in _ts_markup_name_candidates(node, source_bytes):
            if candidate not in candidates:
                candidates.append(candidate)
        return [candidate for candidate in candidates if candidate]
    field_candidate = _ts_name_from_fields(node, source_bytes)
    if field_candidate:
        candidates.append(field_candidate)
    fallback_candidate = _ts_name_from_descendants(node, source_bytes)
    if fallback_candidate and fallback_candidate not in candidates:
        candidates.append(fallback_candidate)
    return [candidate for candidate in candidates if candidate]


def _ts_kind_for_definition(node_type: str, current_scope_kind: str | None, mode: str) -> str:
    lower = node_type.lower()
    if mode == "markup":
        if "script" in lower or "style" in lower:
            return "module"
        if "tag" in lower or "element" in lower or "attribute" in lower:
            return "class"
        return "module"
    if mode == "sql":
        if any(token in lower for token in ("table", "view", "schema", "cte", "data", "column")):
            return "class"
        if any(token in lower for token in ("procedure", "function", "trigger", "query", "statement")):
            return "function"
        return "module"
    if mode == "config":
        if any(token in lower for token in ("rule", "target", "job", "step", "command", "script", "resource", "provider", "workflow")):
            return "function"
        if any(token in lower for token in ("selector", "block", "property", "attribute", "pair", "entry", "key")):
            return "class"
        return "module"
    if any(token in lower for token in ("method", "constructor", "member")):
        return "function"
    if any(token in lower for token in ("class", "interface", "struct", "enum", "trait", "record")):
        return "class"
    if any(token in lower for token in ("module", "namespace", "package", "object")):
        return "module"
    if any(token in lower for token in ("table", "view", "schema", "resource")):
        return "class"
    return "function"


def _ts_is_definition_node(node_type: str, mode: str) -> bool:
    lower = node_type.lower()
    if mode == "markup":
        return any(token in lower for token in ("element", "tag", "document", "fragment"))
    if mode == "sql":
        return any(token in lower for token in _TS_SQL_DEF_KEYWORDS) or any(token in lower for token in ("table", "view", "cte", "statement", "schema"))
    if mode == "config":
        return any(token in lower for token in ("block", "pair", "property", "attribute", "rule", "selector", "entry", "key", "directive"))
    if any(token in lower for token in _TS_IMPORT_KEYWORDS) or "require" in lower or "source" in lower:
        return False
    def_context = any(token in lower for token in ("declaration", "definition", "specifier", "statement", "item", "declarator", "signature", "impl"))
    if lower.endswith("_declaration") or lower.endswith("_definition") or lower.endswith("_item"):
        return True
    return def_context and any(token in lower for token in (
        "class", "interface", "struct", "enum", "trait", "record", "module", "namespace", "package",
        "function", "method", "constructor", "procedure", "macro", "rule", "resource", "object",
        "target", "task", "command", "table", "view", "trigger", "query", "type", "block",
        "property", "attribute", "selector", "element", "tag", "entry",
    ))


def _ts_is_import_node(node_type: str, mode: str) -> bool:
    lower = node_type.lower()
    if mode == "markup":
        return any(token in lower for token in ("script", "style", "link", "include", "import", "resource"))
    if mode == "sql":
        return any(token in lower for token in ("from", "join", "into", "using", "with", "call", "reference", "source"))
    if mode == "config":
        return any(token in lower for token in ("include", "import", "source", "path", "file", "template", "script", "command"))
    return any(token in lower for token in _TS_IMPORT_KEYWORDS) or "import" in lower or "use" in lower or "include" in lower


def _ts_is_call_node(node_type: str, mode: str) -> bool:
    lower = node_type.lower()
    if mode == "markup":
        return any(token in lower for token in ("script", "style", "form", "link", "anchor", "event", "handler"))
    if mode == "sql":
        return any(token in lower for token in ("select", "where", "join", "from", "into", "call", "update", "delete", "insert"))
    if mode == "config":
        return any(token in lower for token in ("command", "action", "script", "target", "task", "job", "step", "run"))
    return any(token in lower for token in _TS_CALL_KEYWORDS) or "call" in lower or "invoke" in lower or "access" in lower


def _ts_is_scope_node(node_type: str, kind: str, mode: str) -> bool:
    if mode == "markup":
        return kind in {"module", "class"}
    if mode == "sql":
        return kind in {"module", "class", "function"}
    if mode == "config":
        return kind in {"module", "class", "function"}
    return kind in {"module", "class", "function"}


def _ts_relation_field_names(relation: str, mode: str) -> tuple[str, ...]:
    if relation == "import":
        if mode == "markup":
            return ("src", "href", "action", "path", "target", "name", "value", "file", "module", "resource")
        if mode == "sql":
            return ("name", "table", "view", "schema", "target", "source", "from", "join", "into", "using", "call")
        if mode == "config":
            return ("path", "file", "template", "script", "command", "source", "include", "import", "name", "value")
        return ("module", "path", "source", "name", "value", "alias", "import", "target", "path_specifier")
    if relation == "call":
        if mode == "markup":
            return ("name", "href", "src", "action", "target", "handler", "value", "path")
        if mode == "sql":
            return ("name", "function", "procedure", "target", "source", "table", "view", "schema", "expression", "query")
        if mode == "config":
            return ("name", "command", "action", "task", "job", "step", "script", "target", "value")
        return ("callee", "function", "name", "object", "member", "value", "target", "path", "selector", "method")
    return _TS_NAME_FIELD_PRIORITY


def _ts_relation_candidates(node, source_bytes: bytes, relation: str, mode: str) -> list[str]:
    candidates = []
    for field_name in _ts_relation_field_names(relation, mode):
        try:
            child = node.child_by_field_name(field_name)
        except Exception:
            child = None
        if child is None:
            continue
        candidate = _ts_clean_name(_ts_node_text(child, source_bytes))
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    if candidates:
        return candidates
    text = _ts_node_text(node, source_bytes)
    if not text:
        return []
    # Fall back to a light parse of the AST span, keeping the grammar boundary.
    raw_candidates = re.findall(r"[A-Za-z_][A-Za-z0-9_.$:#/\-]*", text)
    return [candidate for candidate in raw_candidates if candidate not in _STOP_TERMS]


def _ts_pick_symbol_name(candidates: list[str], mode: str, node_type: str) -> str:
    if not candidates:
        return ""
    if mode == "markup":
        for candidate in candidates:
            if candidate and candidate.casefold() not in _STOP_TERMS:
                return candidate
        return candidates[0]
    if mode == "sql":
        for candidate in candidates:
            if candidate and candidate.casefold() not in _STOP_TERMS:
                return candidate
        return candidates[0]
    if mode == "config":
        for candidate in candidates:
            if candidate and candidate.casefold() not in _STOP_TERMS:
                return candidate
        return candidates[0]
    for candidate in candidates:
        simple = candidate.rsplit(".", 1)[-1].casefold()
        if simple and simple not in _STOP_TERMS:
            return candidate
    return candidates[0]


def _ts_import_aliases(node, source_bytes: bytes, mode: str) -> dict[str, str]:
    text = _ts_node_text(node, source_bytes)
    aliases: dict[str, str] = {}
    if not text:
        return aliases
    for imported, alias in re.findall(r"\b([A-Za-z_][A-Za-z0-9_.$:#/\-]*)\s+as\s+([A-Za-z_][A-Za-z0-9_]*)\b", text):
        aliases[alias] = imported
    for alias, target in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([A-Za-z_][A-Za-z0-9_.$:#/\-]*)\b", text):
        aliases[alias] = target
    if mode in {"markup", "sql", "config"}:
        return aliases
    if "require(" in text or "import" in text or "using" in text or "use " in text:
        simple_targets = re.findall(r"[A-Za-z_][A-Za-z0-9_.$:#/\-]*", text)
        for candidate in simple_targets:
            if candidate not in aliases:
                aliases[candidate] = candidate
    return aliases


def _ts_resolve_target(candidate: str, symbol_lookup: dict[str, str], import_aliases: dict[str, str]) -> str:
    clean = _ts_clean_name(candidate)
    if not clean:
        return ""
    if clean in import_aliases:
        return f"external::{import_aliases[clean]}"
    if clean in symbol_lookup:
        return symbol_lookup[clean]
    simple = _simple_name(clean)
    if simple in symbol_lookup:
        mapped = symbol_lookup[simple]
        if mapped:
            return mapped
    if "." in clean:
        head, tail = clean.split(".", 1)
        if head in import_aliases:
            return f"external::{import_aliases[head]}.{tail}"
    return f"external::{clean}"


class GraphIndexSession:
    """Incremental graph cache for a single index layer."""

    def __init__(
        self,
        *,
        root: Path,
        index_dir: Path,
        layer: str,
        files: list[Path],
        current_file_meta: dict[str, dict[str, Any]],
        walker_version: str,
        chunker_version: str,
        verbose: bool = False,
    ) -> None:
        if layer not in GRAPH_FILENAMES:
            raise ValueError(f"Unsupported graph layer: {layer}")
        self.root = root
        self.index_dir = index_dir
        self.layer = layer
        self.files = files
        self.current_file_meta = current_file_meta
        self.verbose = verbose
        self.walker_version = walker_version
        self.chunker_version = chunker_version
        self.state_path = index_dir / GRAPH_DIRNAME / GRAPH_STATE_FILENAMES[layer]
        self.graph_path = index_dir / GRAPH_DIRNAME / GRAPH_FILENAMES[layer]
        self.pending_code: dict[str, dict[str, Any]] = {}
        self.pending_doc_text: dict[str, str] = {}
        self._state = self._load_state()
        self._current_paths = {
            _repo_rel(path.relative_to(root)) for path in files
            if path.is_file() and not _is_minified_file(_repo_rel(path.relative_to(root)))
        }
        ignored = _gitignored_paths(root)
        if ignored:
            self._current_paths -= ignored

    def _load_state(self) -> dict[str, Any]:
        state = _read_json(self.state_path, {})
        if not isinstance(state, dict):
            return self._fresh_state()
        if str(state.get("schema_version") or "") != GRAPH_SCHEMA_VERSION:
            return self._fresh_state()
        if str(state.get("builder_version") or "") != GRAPH_BUILDER_VERSION:
            return self._fresh_state()
        if str(state.get("walker_version") or "") != self.walker_version:
            return self._fresh_state()
        if str(state.get("chunker_version") or "") != self.chunker_version:
            return self._fresh_state()
        if str(state.get("layer") or "") != self.layer:
            return self._fresh_state()
        files = state.get("files")
        if not isinstance(files, dict):
            return self._fresh_state()
        return state

    def _fresh_state(self) -> dict[str, Any]:
        return {
            "schema_version": GRAPH_SCHEMA_VERSION,
            "builder_version": GRAPH_BUILDER_VERSION,
            "layer": self.layer,
            "walker_version": self.walker_version,
            "chunker_version": self.chunker_version,
            "files": {},
        }

    def _file_meta_hash(self, rel_path: str) -> str:
        meta = self.current_file_meta.get(rel_path) or {}
        return str(meta.get("hash") or "")

    def _current_artifact_for(self, rel_path: str) -> dict[str, Any] | None:
        entry = self._state.get("files", {}).get(rel_path)
        if not isinstance(entry, dict):
            return None
        artifact = entry.get("artifact")
        return artifact if isinstance(artifact, dict) else None

    def _current_hash_for(self, rel_path: str) -> str:
        entry = self._state.get("files", {}).get(rel_path)
        if not isinstance(entry, dict):
            return ""
        return str(entry.get("source_hash") or "")

    def _source_location(self, text: str, line: int) -> str:
        if line <= 0:
            return "1:0"
        lines = text.splitlines()
        if line > len(lines):
            line = len(lines)
        col = 0
        if 1 <= line <= len(lines):
            match = re.search(r"\S", lines[line - 1])
            col = match.start() if match else 0
        return f"{line}:{col}"

    # ------------------------------------------------------------------
    # Doc scan exclusion
    # ------------------------------------------------------------------

    def _is_doc_scan_excluded(self, rel_path: str) -> bool:
        rel = _repo_rel(rel_path)
        # Framework seeds are explicitly included even though they start with '.'
        if rel.startswith(".wavefoundry/framework/seeds/"):
            return False
        for prefix in _DOC_SCAN_EXCLUDE_PREFIXES:
            if rel.startswith(prefix):
                return True
        # Exclude paths with any component starting with '.'
        for part in rel.split("/"):
            if part.startswith("."):
                return True
        return False

    # ------------------------------------------------------------------
    # File recording
    # ------------------------------------------------------------------

    def record_file(self, rel_path: str, source_text: str) -> None:
        """Record the current contents of a changed file."""
        rel = _repo_rel(rel_path)
        if _is_minified_file(rel):
            return
        kind = _kind_for_path(rel)
        source_hash = _sha256_text(source_text)
        if kind == "code":
            self.pending_code[rel] = {
                "source_hash": source_hash,
                "artifact": self._extract_code_artifact(rel, source_text),
            }
        elif not self._is_doc_scan_excluded(rel):
            self.pending_doc_text[rel] = source_text

    # ------------------------------------------------------------------
    # Code extraction
    # ------------------------------------------------------------------

    def _extract_python_artifact(self, rel_path: str, source_text: str) -> dict[str, Any]:
        try:
            tree = ast.parse(source_text)
        except SyntaxError:
            return {
                "kind": "code",
                "path": rel_path,
                "source_hash": _sha256_text(source_text),
                "nodes": [_node(rel_path, _path_term(rel_path), "module", rel_path, "1:0", layer=self.layer)],
                "edges": [],
                "defined_symbols": [],
                "simple_names": {},
                "mentioned_symbols": [],
            }

        module_id = rel_path
        module_node = _node(module_id, _path_term(rel_path), "module", rel_path, "1:0", layer=self.layer)
        nodes: list[dict[str, Any]] = [module_node]
        edges: list[dict[str, Any]] = []
        defined_symbols: list[str] = []
        simple_names: dict[str, list[str]] = {}
        simple_name_lookup: dict[str, list[str]] = {}
        import_aliases: dict[str, str] = {}

        def add_symbol(qname: str, kind: str, lineno: int, label: str | None = None, parent: str | None = None) -> str:
            node_id = f"{rel_path}::{qname}"
            nodes.append(
                _node(
                    node_id,
                    label or qname.split(".")[-1],
                    kind,
                    rel_path,
                    self._source_location(source_text, lineno),
                    layer=self.layer,
                )
            )
            edges.append(_edge(module_id, node_id, "defines", confidence="EXTRACTED"))
            defined_symbols.append(node_id)
            base_name = qname.split(".")[-1]
            simple_names.setdefault(base_name, []).append(node_id)
            if parent:
                simple_name_lookup.setdefault(parent, []).append(node_id)
            return node_id

        def collect_imports_and_defs(body: list[ast.stmt], parent_qname: str | None = None) -> None:
            for stmt in body:
                if isinstance(stmt, ast.Import):
                    for alias in stmt.names:
                        alias_name = alias.asname or alias.name.split(".")[-1]
                        import_aliases[alias_name] = alias.name
                        target_id = f"external::{alias.name}"
                        nodes.append(
                            _node(target_id, alias.name, "module", "", "1:0", layer=self.layer)
                        )
                        edges.append(_edge(module_id, target_id, "imports", confidence="EXTRACTED"))
                elif isinstance(stmt, ast.ImportFrom):
                    mod = stmt.module or ""
                    for alias in stmt.names:
                        alias_name = alias.asname or alias.name
                        import_aliases[alias_name] = f"{mod}.{alias.name}" if mod else alias.name
                        target_label = f"{mod}.{alias.name}" if mod else alias.name
                        target_id = f"external::{target_label}"
                        nodes.append(
                            _node(target_id, target_label, "module", "", "1:0", layer=self.layer)
                        )
                        edges.append(_edge(module_id, target_id, "imports", confidence="EXTRACTED"))
                elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qname = f"{parent_qname}.{stmt.name}" if parent_qname else stmt.name
                    add_symbol(qname, "function", stmt.lineno)
                    if stmt.body:
                        collect_imports_and_defs(stmt.body, qname)
                elif isinstance(stmt, ast.ClassDef):
                    qname = f"{parent_qname}.{stmt.name}" if parent_qname else stmt.name
                    add_symbol(qname, "class", stmt.lineno)
                    collect_imports_and_defs(stmt.body, qname)

        collect_imports_and_defs(tree.body)

        # Build a lookup for the exact target node IDs available in this file.
        symbol_lookup = {symbol_id.split("::", 1)[-1]: symbol_id for symbol_id in defined_symbols}
        for name, items in simple_names.items():
            if len(items) == 1:
                symbol_lookup.setdefault(name, items[0])

        class CallCollector(ast.NodeVisitor):
            def __init__(self, current_symbol: str, scope_class: str | None = None) -> None:
                self.current_symbol = current_symbol
                self.scope_class = scope_class
                self.calls: list[tuple[str, str]] = []

            def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:  # noqa: N802
                return None

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:  # noqa: N802
                return None

            def visit_ClassDef(self, node: ast.ClassDef) -> Any:  # noqa: N802
                return None

            def visit_Call(self, node: ast.Call) -> Any:  # noqa: N802
                target = self._resolve_call(node.func)
                if target:
                    self.calls.append((self.current_symbol, target))
                self.generic_visit(node)

            def _resolve_call(self, func: ast.AST) -> str | None:
                if isinstance(func, ast.Name):
                    name = func.id
                    if name in import_aliases:
                        target_label = import_aliases[name]
                        return f"external::{target_label}"
                    if name in symbol_lookup:
                        return symbol_lookup[name]
                    if self.scope_class:
                        candidate = f"{self.scope_class}.{name}"
                        if candidate in symbol_lookup:
                            return symbol_lookup[candidate]
                    return None
                if isinstance(func, ast.Attribute):
                    attr = func.attr
                    value = func.value
                    if isinstance(value, ast.Name):
                        root = value.id
                        if root in ("self", "cls") and self.scope_class:
                            candidate = f"{self.scope_class}.{attr}"
                            if candidate in symbol_lookup:
                                return symbol_lookup[candidate]
                        if root in import_aliases:
                            return f"external::{import_aliases[root]}.{attr}"
                        if root in symbol_lookup:
                            candidate = f"{root}.{attr}"
                            if candidate in symbol_lookup:
                                return symbol_lookup[candidate]
                    if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name):
                        root = value.value.id
                        if root in import_aliases:
                            return f"external::{import_aliases[root]}.{value.attr}.{attr}"
                    return None
                return None

        def collect_calls(body: list[ast.stmt], current_symbol: str, scope_class: str | None = None) -> None:
            collector = CallCollector(current_symbol, scope_class=scope_class)
            for stmt in body:
                collector.visit(stmt)
                if isinstance(stmt, ast.ClassDef):
                    class_qname = f"{current_symbol.split('::', 1)[-1]}.{stmt.name}" if current_symbol else stmt.name
                    for child in stmt.body:
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            child_symbol = f"{rel_path}::{class_qname}.{child.name}"
                            collect_calls(child.body, child_symbol, scope_class=class_qname)
                elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_qname = f"{current_symbol.split('::', 1)[-1]}.{stmt.name}" if current_symbol else stmt.name
                    collect_calls(stmt.body, f"{rel_path}::{func_qname}", scope_class=scope_class)
            for src, target in collector.calls:
                edges.append(_edge(src, target, "calls", confidence="EXTRACTED"))

        # Attach call edges for top-level defs and classes.
        for stmt in tree.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                collect_calls(stmt.body, f"{rel_path}::{stmt.name}")
            elif isinstance(stmt, ast.ClassDef):
                class_qname = stmt.name
                for child in stmt.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        collect_calls(child.body, f"{rel_path}::{class_qname}.{child.name}", scope_class=class_qname)

        return {
            "kind": "code",
            "path": rel_path,
            "source_hash": _sha256_text(source_text),
            "nodes": nodes,
            "edges": edges,
            "defined_symbols": defined_symbols,
            "simple_names": simple_names,
            "mentioned_symbols": [],
        }

    def _extract_js_artifact(self, rel_path: str, source_text: str) -> dict[str, Any]:
        lines = source_text.splitlines()
        module_id = rel_path
        nodes: list[dict[str, Any]] = [
            _node(module_id, _path_term(rel_path), "module", rel_path, "1:0", layer=self.layer)
        ]
        edges: list[dict[str, Any]] = []
        defined_symbols: list[str] = []
        simple_names: dict[str, list[str]] = {}
        import_aliases: dict[str, str] = {}
        current_class: str | None = None

        def add_symbol(qname: str, kind: str, lineno: int) -> str:
            node_id = f"{rel_path}::{qname}"
            nodes.append(
                _node(
                    node_id,
                    qname.split(".")[-1],
                    kind,
                    rel_path,
                    self._source_location(source_text, lineno),
                    layer=self.layer,
                )
            )
            edges.append(_edge(module_id, node_id, "defines", confidence="EXTRACTED"))
            defined_symbols.append(node_id)
            simple_names.setdefault(qname.split(".")[-1], []).append(node_id)
            return node_id

        for lineno, raw in enumerate(lines, start=1):
            line = raw.rstrip()
            m = _JS_IMPORT_RE.match(line)
            if m:
                spec = m.group(2)
                clause = m.group(1).strip()
                if clause.startswith("{") and clause.endswith("}"):
                    for part in clause.strip("{} ").split(","):
                        item = part.strip()
                        if not item:
                            continue
                        if " as " in item:
                            imported, alias = [p.strip() for p in item.split(" as ", 1)]
                        else:
                            imported = alias = item
                        import_aliases[alias] = f"{spec}.{imported}"
                else:
                    alias = clause.split(",")[0].strip().split(" as ")[-1].strip()
                    alias = alias.lstrip("* from ").strip() if alias else alias
                    if alias:
                        import_aliases[alias] = spec
                target_id = f"external::{spec}"
                nodes.append(_node(target_id, spec, "module", "", "1:0", layer=self.layer))
                edges.append(_edge(module_id, target_id, "imports", confidence="EXTRACTED"))
                continue
            m = _JS_REQUIRE_RE.match(line)
            if m:
                alias, spec = m.group(1), m.group(2)
                import_aliases[alias] = spec
                target_id = f"external::{spec}"
                nodes.append(_node(target_id, spec, "module", "", "1:0", layer=self.layer))
                edges.append(_edge(module_id, target_id, "imports", confidence="EXTRACTED"))
                continue
            m = _JS_DEF_RE.match(line)
            if m:
                name = m.group(1)
                if line.strip().startswith("class "):
                    current_class = name
                    add_symbol(name, "class", lineno)
                else:
                    qname = f"{current_class}.{name}" if current_class and "class" in line else name
                    add_symbol(qname, "function", lineno)
                continue
            m = _JS_CONST_FN_RE.match(line)
            if m:
                name = m.group(1)
                qname = f"{current_class}.{name}" if current_class and "class" in line else name
                add_symbol(qname, "function", lineno)
                continue
            if line.startswith("}"):
                current_class = None

        symbol_lookup = {symbol_id.split("::", 1)[-1]: symbol_id for symbol_id in defined_symbols}
        for name, items in simple_names.items():
            if len(items) == 1:
                symbol_lookup.setdefault(name, items[0])

        for lineno, raw in enumerate(lines, start=1):
            line = raw.rstrip()
            for match in _JS_CALL_RE.finditer(line):
                name = match.group(1)
                if name in ("function", "class", "if", "for", "while", "switch", "catch", "return", "const", "let", "var", "new"):
                    continue
                target = None
                if name in import_aliases:
                    target = f"external::{import_aliases[name]}"
                elif name in symbol_lookup:
                    target = symbol_lookup[name]
                if target:
                    source_symbol = defined_symbols[0] if defined_symbols else module_id
                    edges.append(_edge(source_symbol, target, "calls", confidence="EXTRACTED"))

        return {
            "kind": "code",
            "path": rel_path,
            "source_hash": _sha256_text(source_text),
            "nodes": nodes,
            "edges": edges,
            "defined_symbols": defined_symbols,
            "simple_names": simple_names,
            "mentioned_symbols": [],
        }

    def _empty_code_artifact(self, rel_path: str, source_text: str) -> dict[str, Any]:
        return {
            "kind": "code",
            "path": rel_path,
            "source_hash": _sha256_text(source_text),
            "nodes": [_node(rel_path, _path_term(rel_path), "module", rel_path, "1:0", layer=self.layer)],
            "edges": [],
            "defined_symbols": [],
            "simple_names": {},
            "mentioned_symbols": [],
        }

    def _extract_json_artifact(self, rel_path: str, source_text: str) -> dict[str, Any]:
        ts_artifact = self._extract_tree_sitter_artifact(rel_path, source_text, "json")
        if ts_artifact is not None and ts_artifact.get("defined_symbols"):
            return ts_artifact
        try:
            payload = json.loads(source_text)
        except json.JSONDecodeError:
            return self._empty_code_artifact(rel_path, source_text)
        module_id = rel_path
        nodes: list[dict[str, Any]] = [
            _node(module_id, _path_term(rel_path), "module", rel_path, "1:0", layer=self.layer)
        ]
        edges: list[dict[str, Any]] = []
        defined_symbols: list[str] = []
        if isinstance(payload, dict):
            for key in sorted(payload.keys()):
                if not isinstance(key, str) or not key:
                    continue
                node_id = f"{rel_path}::{key}"
                nodes.append(
                    _node(node_id, key, "class", rel_path, "1:0", layer=self.layer)
                )
                edges.append(_edge(module_id, node_id, "defines", confidence="EXTRACTED"))
                defined_symbols.append(node_id)
        return {
            "kind": "code",
            "path": rel_path,
            "source_hash": _sha256_text(source_text),
            "nodes": nodes,
            "edges": edges,
            "defined_symbols": defined_symbols,
            "simple_names": {},
            "mentioned_symbols": [],
        }

    def _extract_tree_sitter_artifact(self, rel_path: str, source_text: str, lang_key: str) -> dict[str, Any] | None:
        profile = _TS_LANGUAGE_PROFILES.get(lang_key)
        if profile is None:
            return None
        tree = _ts_parse(lang_key, source_text)
        if tree is None:
            return None
        mode = profile.mode
        source_bytes = source_text.encode("utf-8", errors="replace")
        module_id = rel_path
        node_map: dict[str, dict[str, Any]] = {
            module_id: _node(module_id, _path_term(rel_path), "module", rel_path, "1:0", layer=self.layer)
        }
        edge_map: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        defined_symbols: list[str] = []
        simple_names: dict[str, list[str]] = defaultdict(list)
        import_aliases: dict[str, str] = {}

        def add_node(node_id: str, label: str, kind: str, source_location: str) -> None:
            if node_id not in node_map:
                node_map[node_id] = _node(node_id, label, kind, rel_path, source_location, layer=self.layer)

        def add_edge(source: str, target: str, relation: str, *, confidence: str, evidence: str | None = None) -> None:
            key = (source, target, relation, confidence)
            if key in edge_map:
                return
            edge_map[key] = _edge(source, target, relation, confidence=confidence, evidence=evidence)

        def register_symbol(qname: str, kind: str, node, parent_symbol: str | None) -> str:
            node_id = f"{rel_path}::{qname}"
            label = qname.rsplit(".", 1)[-1]
            add_node(node_id, label, kind, self._source_location(source_text, node.start_point[0] + 1))
            add_edge(module_id, node_id, "defines", confidence="EXTRACTED")
            if parent_symbol and parent_symbol != module_id:
                add_edge(parent_symbol, node_id, "defines", confidence="EXTRACTED")
            defined_symbols.append(node_id)
            simple = _simple_name(node_id)
            if simple:
                simple_names.setdefault(simple, []).append(node_id)
            return node_id

        def walk_definitions(node, scope_names: list[str], scope_kinds: list[str], scope_symbols: list[str]) -> None:
            node_type = str(getattr(node, "type", "") or "")
            current_scope_kind = scope_kinds[-1] if scope_kinds else None
            is_import = _ts_markup_import_nodes(node, source_bytes) if mode == "markup" else _ts_is_import_node(node_type, mode)
            is_definition = bool(_ts_markup_name_candidates(node, source_bytes)) if mode == "markup" else _ts_is_definition_node(node_type, mode)
            if is_import:
                source_symbol = scope_symbols[-1] if scope_symbols else module_id
                for target in _ts_relation_candidates(node, source_bytes, "import", mode):
                    resolved = _ts_resolve_target(target, {}, import_aliases)
                    add_edge(source_symbol, resolved, "imports", confidence="EXTRACTED")
                import_aliases.update(_ts_import_aliases(node, source_bytes, mode))
            if is_definition:
                candidates = _ts_name_candidates(node, source_bytes, mode)
                name = _ts_pick_symbol_name(candidates, mode, node_type)
                if name:
                    kind = _ts_kind_for_definition(node_type, current_scope_kind, mode)
                    qname = ".".join([*scope_names, name]) if scope_names else name
                    parent_symbol = scope_symbols[-1] if scope_symbols else module_id
                    node_id = register_symbol(qname, kind, node, parent_symbol)
                    should_push = _ts_is_scope_node(node_type, kind, mode)
                    if mode == "markup":
                        return
                    next_scope_names = [*scope_names, name] if should_push else scope_names
                    next_scope_kinds = [*scope_kinds, kind] if should_push else scope_kinds
                    next_scope_symbols = [*scope_symbols, node_id] if should_push else scope_symbols
                    for child in getattr(node, "named_children", []):
                        walk_definitions(child, next_scope_names, next_scope_kinds, next_scope_symbols)
                    return
            if mode == "markup" and (is_import or is_definition):
                return
            for child in getattr(node, "named_children", []):
                walk_definitions(child, scope_names, scope_kinds, scope_symbols)

        walk_definitions(tree.root_node, [], [], [])

        symbol_lookup: dict[str, str] = {}
        for symbol_id in defined_symbols:
            symbol_lookup[symbol_id.split("::", 1)[-1]] = symbol_id
        for name, items in simple_names.items():
            if len(items) == 1:
                symbol_lookup.setdefault(name, items[0])

        def walk_calls(node, scope_names: list[str], scope_kinds: list[str], scope_symbols: list[str]) -> None:
            node_type = str(getattr(node, "type", "") or "")
            current_scope_kind = scope_kinds[-1] if scope_kinds else None
            is_import = _ts_markup_import_nodes(node, source_bytes) if mode == "markup" else _ts_is_import_node(node_type, mode)
            is_definition = bool(_ts_markup_name_candidates(node, source_bytes)) if mode == "markup" else _ts_is_definition_node(node_type, mode)
            if is_import:
                source_symbol = scope_symbols[-1] if scope_symbols else module_id
                for target in _ts_relation_candidates(node, source_bytes, "import", mode):
                    resolved = _ts_resolve_target(target, symbol_lookup, import_aliases)
                    add_edge(source_symbol, resolved, "imports", confidence="EXTRACTED")
            if is_definition:
                candidates = _ts_name_candidates(node, source_bytes, mode)
                name = _ts_pick_symbol_name(candidates, mode, node_type)
                if name:
                    kind = _ts_kind_for_definition(node_type, current_scope_kind, mode)
                    should_push = _ts_is_scope_node(node_type, kind, mode)
                    if mode == "markup":
                        return
                    if should_push:
                        next_scope_names = [*scope_names, name]
                        next_scope_kinds = [*scope_kinds, kind]
                        next_scope_symbols = [*scope_symbols, f"{rel_path}::{'.'.join([*scope_names, name])}"]
                    else:
                        next_scope_names = scope_names
                        next_scope_kinds = scope_kinds
                        next_scope_symbols = scope_symbols
                    for child in getattr(node, "named_children", []):
                        walk_calls(child, next_scope_names, next_scope_kinds, next_scope_symbols)
                    return
            if mode == "markup" and (is_import or is_definition):
                return
            if _ts_is_call_node(node_type, mode):
                source_symbol = scope_symbols[-1] if scope_symbols else module_id
                for target in _ts_relation_candidates(node, source_bytes, "call", mode):
                    resolved = _ts_resolve_target(target, symbol_lookup, import_aliases)
                    add_edge(source_symbol, resolved, "calls", confidence="EXTRACTED")
            for child in getattr(node, "named_children", []):
                walk_calls(child, scope_names, scope_kinds, scope_symbols)

        walk_calls(tree.root_node, [], [], [])

        return {
            "kind": "code",
            "path": rel_path,
            "source_hash": _sha256_text(source_text),
            "nodes": sorted(node_map.values(), key=lambda item: str(item.get("id") or "")),
            "edges": sorted(
                edge_map.values(),
                key=lambda item: (
                    str(item.get("source") or ""),
                    str(item.get("target") or ""),
                    str(item.get("relation") or ""),
                ),
            ),
            "defined_symbols": defined_symbols,
            "simple_names": {name: ids for name, ids in simple_names.items()},
            "mentioned_symbols": [],
        }

    def _extract_code_artifact(self, rel_path: str, source_text: str) -> dict[str, Any]:
        suffix = Path(rel_path).suffix.lower()
        if suffix == ".py":
            artifact = self._extract_python_artifact(rel_path, source_text)
        elif suffix in {".json", ".jsonc"}:
            artifact = self._extract_json_artifact(rel_path, source_text)
        else:
            lang_key = _ts_language_key_for_path(rel_path)
            if lang_key:
                artifact = self._extract_tree_sitter_artifact(rel_path, source_text, lang_key)
                if artifact is None:
                    if lang_key in {"javascript", "typescript"}:
                        artifact = self._extract_js_artifact(rel_path, source_text)
                    else:
                        artifact = self._empty_code_artifact(rel_path, source_text)
            elif suffix in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}:
                artifact = self._extract_js_artifact(rel_path, source_text)
            else:
                artifact = {
                    "kind": "code",
                    "path": rel_path,
                    "source_hash": _sha256_text(source_text),
                    "nodes": [_node(rel_path, _path_term(rel_path), "module", rel_path, "1:0", layer=self.layer)],
                    "edges": [],
                    "defined_symbols": [],
                    "simple_names": {},
                    "mentioned_symbols": [],
                }
        try:
            di_mod = _load_di_signals_module()
            artifact["di_signals"] = di_mod.collect_di_signals(rel_path, source_text)
        except Exception:
            artifact["di_signals"] = []
        return artifact

    # ------------------------------------------------------------------
    # Doc extraction
    # ------------------------------------------------------------------

    def _extract_doc_artifact(
        self,
        rel_path: str,
        source_text: str,
        symbol_terms: dict[str, set[str]],
        matcher: tuple[dict[str, set[str]], re.Pattern[str] | None, dict[str, set[str]]] | None = None,
    ) -> dict[str, Any]:
        kind = _kind_for_path(rel_path)
        node_kind = "seed" if kind == "seed" else "doc"
        module_id = rel_path
        nodes = [
            _node(module_id, _path_term(rel_path), node_kind, rel_path, "1:0", layer=self.layer)
        ]
        edges: list[dict[str, Any]] = []
        matched_terms: set[str] = set()
        mentioned_set: set[str] = set()

        if matcher is None:
            matcher = self._compile_doc_matcher(symbol_terms)
        simple_lower, complex_pattern, complex_lower = matcher

        # Only scan inline backtick spans for simple keyword matches (skip JSON/config fences).
        inline_ctx = _extract_inline_code_contexts(source_text)
        inline_terms = _extract_doc_match_terms(inline_ctx)
        code_ctx = _extract_code_contexts(source_text)

        for lower_term, targets in simple_lower.items():
            if lower_term not in inline_terms:
                continue
            matched_terms.add(lower_term)
            filtered = _filter_doc_code_targets(lower_term, targets)
            for target in filtered:
                if target in mentioned_set:
                    continue
                mentioned_set.add(target)
                edges.append(
                    _edge(
                        module_id,
                        target,
                        "doc_references_code",
                        confidence=_doc_code_reference_confidence(lower_term, target, match_count=len(filtered)),
                        evidence=lower_term,
                    )
                )

        # Dotted/complex terms: one combined regex pass over all code context.
        if complex_pattern:
            for m in complex_pattern.finditer(code_ctx):
                key = m.group().lower()
                targets = complex_lower.get(key)
                if not targets:
                    continue
                matched_terms.add(key)
                filtered = _filter_doc_code_targets(key, targets)
                for target in filtered:
                    if target in mentioned_set:
                        continue
                    mentioned_set.add(target)
                    edges.append(
                        _edge(
                            module_id,
                            target,
                            "doc_references_code",
                            confidence=_doc_code_reference_confidence(key, target, match_count=len(filtered)),
                            evidence=key,
                        )
                    )

        # Explicit markdown links and backtick file paths to other known files.
        linked_paths: set[str] = set()
        for linked_path in _extract_doc_links(source_text, rel_path, self._current_paths):
            linked_paths.add(linked_path)
        for linked_path in _extract_doc_backtick_paths(source_text, rel_path, self._current_paths):
            linked_paths.add(linked_path)
        for linked_path in sorted(linked_paths):
            edges.append(_edge(module_id, linked_path, "doc_references_doc", confidence="EXTRACTED"))

        mentioned = sorted(mentioned_set)
        return {
            "kind": node_kind,
            "path": rel_path,
            "source_hash": _sha256_text(source_text),
            "nodes": nodes,
            "edges": edges,
            "defined_symbols": [],
            "simple_names": {},
            "mentioned_symbols": mentioned,
            "matched_terms": sorted(matched_terms),
            "source_text": source_text,
        }

    # ------------------------------------------------------------------
    # Finalization
    # ------------------------------------------------------------------

    def _is_doc_path(self, rel_path: str) -> bool:
        return _kind_for_path(rel_path) in {"doc", "seed"}

    def _build_symbol_terms(self, artifacts: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
        terms: dict[str, set[str]] = {}
        for artifact in artifacts.values():
            if artifact.get("kind") != "code":
                continue
            for node in artifact.get("nodes", []):
                if not isinstance(node, dict):
                    continue
                node_id = str(node.get("id") or "")
                if not node_id:
                    continue
                label = str(node.get("label") or "")
                if label:
                    terms.setdefault(label, set()).add(node_id)
                qname = node_id.split("::", 1)[-1]
                if qname and qname != label:
                    terms.setdefault(qname, set()).add(node_id)
                simple = _simple_name(node_id)
                if simple and simple != label and simple != qname and simple not in _STOP_TERMS:
                    terms.setdefault(simple, set()).add(node_id)
                if _is_module_graph_node(node):
                    source_file = str(node.get("source_file") or node_id)
                    stem = _path_term(source_file)
                    if stem and stem not in _STOP_TERMS:
                        terms.setdefault(stem, set()).add(node_id)
        return terms

    _SIMPLE_TERM_RE = re.compile(r"^[A-Za-z0-9_]+$")

    def _compile_doc_matcher(
        self, symbol_terms: dict[str, set[str]]
    ) -> tuple[dict[str, set[str]], re.Pattern[str] | None, dict[str, set[str]]]:
        """Build fast lookup structures for doc symbol scanning.

        Returns (simple_lower, complex_pattern, complex_lower) where:
        - simple_lower: lowercase pure-identifier terms → node id sets
        - complex_pattern: compiled combined regex for dotted/special terms (or None)
        - complex_lower: lowercase complex terms → node id sets
        """
        simple_lower: dict[str, set[str]] = {}
        complex_lower: dict[str, set[str]] = {}
        for term, ids in symbol_terms.items():
            if not term or term in _DOC_MATCH_STOP_TERMS:
                continue
            if len(term) < _MIN_DOC_MATCH_TERM_LEN:
                continue
            lower = term.lower()
            if self._SIMPLE_TERM_RE.match(term):
                simple_lower.setdefault(lower, set()).update(ids)
            else:
                complex_lower.setdefault(lower, set()).update(ids)
        complex_pattern: re.Pattern[str] | None = None
        if complex_lower:
            sorted_terms = sorted(complex_lower.keys(), key=len, reverse=True)
            complex_pattern = re.compile(
                r"\b(?:" + "|".join(re.escape(t) for t in sorted_terms) + r")\b",
                re.IGNORECASE,
            )
        return simple_lower, complex_pattern, complex_lower

    def _changed_symbol_ids(
        self,
        old_artifact: dict[str, Any] | None,
        new_artifact: dict[str, Any] | None,
    ) -> set[str]:
        old_defs = set(old_artifact.get("defined_symbols") or []) if old_artifact else set()
        new_defs = set(new_artifact.get("defined_symbols") or []) if new_artifact else set()
        return old_defs.symmetric_difference(new_defs)

    def finalize(self) -> dict[str, Any]:
        state_files: dict[str, dict[str, Any]] = dict(self._state.get("files") or {})
        current_paths = set(self._current_paths)

        # Files that existed in the prior graph state but are gone now (deleted or
        # renamed away). Edges from surviving files into these paths are stale and
        # must be pruned even when the referring file itself did not change.
        removed_paths = set(state_files.keys()) - current_paths

        # Remove vanished files from the persistent state first.
        for rel in list(state_files.keys()):
            if rel not in current_paths:
                state_files.pop(rel, None)

        # Purge any doc artifacts cached from paths that are now excluded.
        for rel in list(state_files.keys()):
            if _kind_for_path(rel) in {"doc", "seed"} and self._is_doc_scan_excluded(rel):
                state_files.pop(rel, None)

        artifacts: dict[str, dict[str, Any]] = {}
        changed_code_symbols: set[str] = set()
        # Symbol IDs that existed before but no longer do (renamed/removed within a
        # surviving file). Edges pointing at these are stale and must be pruned.
        removed_symbols: set[str] = set()

        # Start with cached artifacts for surviving files.
        for rel, entry in state_files.items():
            artifact = entry.get("artifact")
            if isinstance(artifact, dict):
                artifacts[rel] = artifact

        # Apply changed code artifacts immediately.
        for rel, payload in self.pending_code.items():
            new_artifact = payload["artifact"]
            old_artifact = artifacts.get(rel)
            changed_code_symbols.update(self._changed_symbol_ids(old_artifact, new_artifact))
            old_defs = set(old_artifact.get("defined_symbols") or []) if old_artifact else set()
            new_defs = set(new_artifact.get("defined_symbols") or [])
            removed_symbols.update(old_defs - new_defs)
            artifacts[rel] = new_artifact
            state_files[rel] = {
                "source_hash": payload["source_hash"],
                "artifact": new_artifact,
            }

        # Rebuild symbol terms from the current code artifact set before scanning docs.
        symbol_terms = self._build_symbol_terms(artifacts)
        matcher = self._compile_doc_matcher(symbol_terms)

        # Changed docs are rescanned directly from their current text.
        for rel, source_text in self.pending_doc_text.items():
            artifact = self._extract_doc_artifact(rel, source_text, symbol_terms, matcher)
            artifacts[rel] = artifact
            state_files[rel] = {
                "source_hash": artifact["source_hash"],
                "artifact": artifact,
            }

        # Any unchanged doc that mentioned a changed symbol is now stale.
        impacted_docs: list[str] = []
        if changed_code_symbols:
            for rel, artifact in artifacts.items():
                if artifact.get("kind") not in {"doc", "seed"}:
                    continue
                mentioned = set(artifact.get("mentioned_symbols") or [])
                if mentioned.intersection(changed_code_symbols):
                    impacted_docs.append(rel)

        for rel in impacted_docs:
            path = self.root / rel
            if not path.exists():
                artifacts.pop(rel, None)
                state_files.pop(rel, None)
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            artifact = self._extract_doc_artifact(rel, text, symbol_terms, matcher)
            artifacts[rel] = artifact
            state_files[rel] = {
                "source_hash": artifact["source_hash"],
                "artifact": artifact,
            }

        # The updated doc scans may have consumed new symbols; if any docs were refreshed,
        # rebuild the symbol term map once more and rescan those docs for stable output.
        if impacted_docs:
            symbol_terms = self._build_symbol_terms(artifacts)
            matcher = self._compile_doc_matcher(symbol_terms)
            for rel in impacted_docs:
                artifact = artifacts.get(rel)
                if not artifact:
                    continue
                path = self.root / rel
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                new_artifact = self._extract_doc_artifact(rel, text, symbol_terms, matcher)
                artifacts[rel] = new_artifact
                state_files[rel] = {
                    "source_hash": new_artifact["source_hash"],
                    "artifact": new_artifact,
                }

        # Keep only current files in the graph state.
        for rel in list(state_files.keys()):
            if rel not in current_paths:
                state_files.pop(rel, None)

        # Build final graph node/edge sets.
        node_map: dict[str, dict[str, Any]] = {}
        edge_map: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        for rel in sorted(artifacts.keys()):
            artifact = artifacts[rel]
            for node in artifact.get("nodes", []):
                if not isinstance(node, dict):
                    continue
                node_id = str(node.get("id") or "")
                if node_id and node_id not in node_map:
                    node_map[node_id] = node
            for edge in artifact.get("edges", []):
                if not isinstance(edge, dict):
                    continue
                key = (
                    str(edge.get("source") or ""),
                    str(edge.get("target") or ""),
                    str(edge.get("relation") or ""),
                    str(edge.get("confidence") or ""),
                )
                if not all(key):
                    continue
                edge_map.setdefault(key, edge)

        try:
            di_mod = _load_di_signals_module()
            for edge in di_mod.resolve_di_edges(artifacts, node_map):
                if not isinstance(edge, dict):
                    continue
                key = (
                    str(edge.get("source") or ""),
                    str(edge.get("target") or ""),
                    str(edge.get("relation") or ""),
                    str(edge.get("confidence") or ""),
                )
                if not all(key):
                    continue
                edge_map.setdefault(key, edge)
                for endpoint in (key[0], key[1]):
                    if endpoint and endpoint not in node_map:
                        file_part = endpoint.split("::")[0] if "::" in endpoint else endpoint
                        label = endpoint.split("::")[-1]
                        node_map[endpoint] = _node(
                            endpoint,
                            label,
                            "class" if "::" in endpoint else "module",
                            file_part,
                            "1:0",
                            layer=self.layer,
                        )
        except Exception:
            pass

        # Reverse invalidation: drop edges left dangling by deletions/renames in
        # surviving (unchanged) referrer files. A cached referrer artifact can still
        # carry an edge into a symbol or file that no longer exists; without this
        # pass those edges point at nodes absent from node_map. We only prune edges
        # whose endpoint is *known* to have been removed (a removed path, or a symbol
        # that vanished from a re-extracted file), so legitimate edges to external
        # imports or unresolved targets are preserved.
        if removed_paths or removed_symbols:
            def _file_of(node_id: str) -> str:
                return node_id.split("::")[0] if "::" in node_id else node_id

            for key in [
                k
                for k in edge_map
                if k[0] in removed_symbols
                or k[1] in removed_symbols
                or _file_of(k[0]) in removed_paths
                or _file_of(k[1]) in removed_paths
            ]:
                edge_map.pop(key, None)

        # Prune short internal symbols: drop code symbol nodes with labels ≤
        # _SHORT_SYMBOL_MAX_LEN chars unless some other file imports or calls them.
        short_symbols: set[str] = {
            node_id
            for node_id, node in node_map.items()
            if "::" in node_id
            and len(str(node.get("label") or "")) <= _SHORT_SYMBOL_MAX_LEN
        }
        if short_symbols:
            externally_used: set[str] = set()
            for src, tgt, rel, conf in edge_map:
                if tgt not in short_symbols or rel == "defines":
                    continue
                tgt_file = str((node_map.get(tgt) or {}).get("source_file") or "")
                src_file = src.split("::")[0] if "::" in src else src
                if src_file != tgt_file:
                    externally_used.add(tgt)
            pruned = short_symbols - externally_used
            for node_id in pruned:
                node_map.pop(node_id, None)
            for key in [k for k in edge_map if k[0] in pruned or k[1] in pruned]:
                edge_map.pop(key, None)

        # Prune zero-edge doc/seed nodes — they're fully covered by semantic search
        # and provide no graph navigation value.
        _DOC_SEED_KINDS = {"doc", "seed"}
        referenced_nodes: set[str] = set()
        for src, tgt, rel, conf in edge_map:
            referenced_nodes.add(src)
            referenced_nodes.add(tgt)
        zero_edge_docs = {
            node_id
            for node_id, node in node_map.items()
            if node.get("kind") in _DOC_SEED_KINDS and node_id not in referenced_nodes
        }
        for node_id in zero_edge_docs:
            node_map.pop(node_id, None)

        # Compute graph analytics: entry points, dead code risk, chokepoints.
        # Restricted to executable source languages — excludes data/config/markup files.
        _EXECUTABLE_EXTS = frozenset({
            ".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
            ".go", ".rs", ".java", ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp",
            ".cs", ".sh", ".bash", ".zsh", ".fish", ".kt", ".kts",
            ".swift", ".m", ".mm", ".rb", ".scala", ".ps1", ".psm1",
            ".sql", ".psql", ".pgsql", ".ddl", ".dml",
        })

        def _is_executable(node_id: str) -> bool:
            f = node_id.split("::")[0] if "::" in node_id else node_id
            return Path(f).suffix.lower() in _EXECUTABLE_EXTS

        # Build per-node edge sets for fast lookup.
        incoming_external: dict[str, set[str]] = {}  # tgt → set of relations from other files
        outgoing_any: set[str] = set()
        for src, tgt, rel, conf in edge_map:
            outgoing_any.add(src)
            src_file = src.split("::")[0] if "::" in src else src
            tgt_file = (node_map.get(tgt) or {}).get("source_file") or (tgt.split("::")[0] if "::" in tgt else tgt)
            if src_file != tgt_file:
                incoming_external.setdefault(tgt, set()).add(rel)

        # Entry points: executable code modules that nothing imports from another file,
        # but that have outgoing edges (so they're not isolated).
        for node_id, node in node_map.items():
            if node.get("kind") != "module" or "::" in node_id:
                continue
            if not _is_executable(node_id):
                continue
            if "imports" not in incoming_external.get(node_id, set()) and node_id in outgoing_any:
                node["is_entry_point"] = True

        # Dead code risk: executable code MODULE nodes where none of their defined
        # symbols are externally called or imported. Flagging at module level avoids
        # per-symbol noise — most internal helpers are legitimately private.
        module_has_external_use: set[str] = set()
        for src, tgt, rel, conf in edge_map:
            if rel not in {"calls", "imports"}:
                continue
            src_file = src.split("::")[0] if "::" in src else src
            tgt_file = (node_map.get(tgt) or {}).get("source_file") or (tgt.split("::")[0] if "::" in tgt else tgt)
            if src_file != tgt_file and tgt_file:
                module_has_external_use.add(tgt_file)
        for node_id, node in node_map.items():
            if node.get("kind") != "module" or "::" in node_id:
                continue
            if not _is_executable(node_id):
                continue
            if node.get("is_entry_point"):
                continue
            if node_id not in module_has_external_use and node_id in outgoing_any:
                node["dead_code_risk"] = True

        # Chokepoints: articulation points in the undirected graph, restricted to
        # executable code modules and their symbols.
        try:
            import igraph as ig
            exec_ids = [
                nid for nid in node_map
                if _is_executable(nid)
            ]
            vid = {nid: i for i, nid in enumerate(exec_ids)}
            ig_edges = [
                (vid[src], vid[tgt])
                for src, tgt, rel, conf in edge_map
                if src in vid and tgt in vid and vid[src] != vid[tgt]
            ]
            G = ig.Graph(n=len(exec_ids), edges=ig_edges, directed=False)
            for ap_idx in G.articulation_points():
                nid = exec_ids[ap_idx]
                if nid in node_map:
                    node_map[nid]["is_chokepoint"] = True
        except Exception:
            pass

        from datetime import UTC, datetime

        graph_payload = {
            "schema_version": GRAPH_SCHEMA_VERSION,
            "builder_version": GRAPH_BUILDER_VERSION,
            "layer": self.layer,
            "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "counts": {
                "files": len(artifacts),
                "nodes": len(node_map),
                "edges": len(edge_map),
                "entry_points": sum(1 for n in node_map.values() if n.get("is_entry_point")),
                "dead_code_risk": sum(1 for n in node_map.values() if n.get("dead_code_risk")),
                "chokepoints": sum(1 for n in node_map.values() if n.get("is_chokepoint")),
            },
            "nodes": sorted(node_map.values(), key=lambda item: str(item.get("id") or "")),
            "edges": sorted(edge_map.values(), key=lambda item: (
                str(item.get("source") or ""),
                str(item.get("target") or ""),
                str(item.get("relation") or ""),
            )),
        }

        _write_json(self.graph_path, graph_payload)
        self._state = {
            "schema_version": GRAPH_SCHEMA_VERSION,
            "builder_version": GRAPH_BUILDER_VERSION,
            "layer": self.layer,
            "walker_version": self.walker_version,
            "chunker_version": self.chunker_version,
            "files": state_files,
        }
        _write_json(self.state_path, self._state)
        return graph_payload


def update_graph_index(
    *,
    root: Path,
    index_dir: Path,
    layer: str,
    files: list[Path],
    current_file_meta: dict[str, dict[str, Any]],
    changed: set[str],
    removed: set[str],
    walker_version: str,
    chunker_version: str,
    verbose: bool = False,
) -> dict[str, Any]:
    session = GraphIndexSession(
        root=root,
        index_dir=index_dir,
        layer=layer,
        files=files,
        current_file_meta=current_file_meta,
        walker_version=walker_version,
        chunker_version=chunker_version,
        verbose=verbose,
    )
    changed_set = {str(rel).replace("\\", "/") for rel in changed}
    removed_set = {str(rel).replace("\\", "/") for rel in removed}
    # After builder/walker/chunker bumps GraphIndexSession starts with empty cached
    # artifacts. Incremental indexer runs only pass a small ``changed`` set (e.g. docs
    # from the post-edit hook), which would otherwise write a nearly empty graph.
    if not (session._state.get("files") or {}):
        changed_set = {
            str(file_path.relative_to(root)).replace("\\", "/")
            for file_path in files
            if file_path.is_file()
        }
        if verbose and changed_set:
            print(
                f"build_index: graph state empty for {layer} layer — "
                f"re-extracting {len(changed_set)} file(s) in corpus",
                flush=True,
            )
    if verbose:
        print(
            f"build_index: graph extraction inputs for {layer} layer — "
            f"{len(changed_set)} changed, {len(removed_set)} removed",
            flush=True,
        )
    for file_path in files:
        rel = _repo_rel(file_path.relative_to(root))
        if rel not in changed_set:
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        session.record_file(rel, text)
    payload = session.finalize()
    if verbose:
        counts = payload.get("counts") or {}
        print(
            f"build_index: graph extraction wrote {layer} graph — "
            f"{counts.get('nodes', 0)} nodes, {counts.get('edges', 0)} edges",
            flush=True,
        )
    return payload


def read_graph_payload(root: Path, layer: str) -> dict[str, Any]:
    if layer not in GRAPH_FILENAMES:
        raise ValueError(f"Unsupported graph layer: {layer}")
    index_dir = root / ".wavefoundry" / ("framework" if layer == "framework" else "") / "index"
    if layer == "project":
        index_dir = root / ".wavefoundry" / "index"
    graph_path = index_dir / GRAPH_DIRNAME / GRAPH_FILENAMES[layer]
    payload = _read_json(graph_path, {})
    if isinstance(payload, dict) and payload:
        payload.setdefault("layer", layer)
        payload.setdefault("schema_version", GRAPH_SCHEMA_VERSION)
        payload.setdefault("nodes", [])
        payload.setdefault("edges", [])
        payload.setdefault("counts", {"files": 0, "nodes": len(payload.get("nodes") or []), "edges": len(payload.get("edges") or [])})
        payload["present"] = True
        payload["graph_path"] = str(graph_path.relative_to(root)).replace("\\", "/")
        return payload
    return {
        "layer": layer,
        "schema_version": GRAPH_SCHEMA_VERSION,
        "present": False,
        "graph_path": str(graph_path.relative_to(root)).replace("\\", "/"),
        "nodes": [],
        "edges": [],
        "counts": {"files": 0, "nodes": 0, "edges": 0},
    }
