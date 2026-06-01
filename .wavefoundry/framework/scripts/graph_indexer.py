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
GRAPH_BUILDER_VERSION = "14"  # bumped for wave 13129 (1316l): Swift class/module pair merge at index time
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


# ---------------------------------------------------------------------------
# Generated-code classifier (wave 130rj — Aceiss field feedback §6)
# ---------------------------------------------------------------------------
#
# Tags graph nodes from machine-generated source files with `generated: true`.
# Downstream consumers (wave_graph_report `exclude_generated`, `community_type`,
# `betweenness_dominated_by_generated`, and the 130su collapse mode) read this
# tag to filter or aggregate generated nodes out of architectural views without
# discarding the underlying graph edges.
#
# Three signal sources, in priority order: in-file header marker (matched in
# first 200 bytes), path heuristic (directory segments or filename suffix),
# `.gitattributes` `linguist-generated=true` annotation.
#
# Coverage in this change: Java/JVM + C#. Multi-language follow-up (Go, TS/JS,
# Rust, Swift, Kotlin, Python) is deferred per the change doc — operator
# validation of Java+C# coverage informs the follow-up's architectural shape.

# Header substrings matched in the first 200 bytes (case-sensitive).
_GENERATED_HEADER_SIGNATURES = (
    # Java / JVM ecosystem
    "Generated By:JJTree",
    "Generated By:JavaCC",
    "DO NOT EDIT",
    "Code generated by",
    "@javax.annotation.Generated",
    "@jakarta.annotation.Generated",
    "@javax.annotation.processing.Generated",
    # C# / .NET ecosystem
    "<auto-generated>",
    "<auto-generated/>",
    "[GeneratedCode(",
    "[GeneratedCodeAttribute(",
)

# Regex patterns for headers that need pattern matching (e.g. ANTLR's version-flexible header).
_GENERATED_HEADER_PATTERNS = (
    re.compile(rb"Generated from .* by ANTLR"),
    # bare `@Generated(` annotation form (avoid catching `@Generated...` in javadoc prose by
    # requiring an opening paren or a newline immediately after).
    re.compile(rb"^[\s\*]*@Generated\b\s*[(\n]", re.MULTILINE),
)

# Directory segment matches (any segment in the path counts).
_GENERATED_DIR_SEGMENTS = (
    "generated-sources",
    "build/generated",
    "generated",
    "Service References",
    "Connected Services",
)

# Filename suffix matches (case-insensitive).
_GENERATED_FILENAME_SUFFIXES = (
    ".designer.cs",
    ".g.cs",
    ".g.i.cs",
)


def _load_gitattributes_generated_paths(root: Path) -> frozenset[str]:
    """Parse .gitattributes for `linguist-generated=true` annotations once per session.

    Returns a frozenset of relative-path patterns (forward-slash). Patterns may include
    glob characters (`*`, `?`); the consumer checks via fnmatch-style match.
    """
    paths: list[str] = []
    gitattrs = root / ".gitattributes"
    if not gitattrs.is_file():
        return frozenset()
    try:
        for raw in gitattrs.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            # Expected shape: <pattern> linguist-generated=true [...other attrs]
            if "linguist-generated=true" not in line and "linguist-generated" not in line:
                continue
            # First whitespace-separated token is the pattern.
            parts = line.split()
            if not parts:
                continue
            pattern = parts[0].replace("\\", "/")
            if pattern:
                paths.append(pattern)
    except OSError:
        return frozenset()
    return frozenset(paths)


def _path_matches_gitattributes(rel_path: str, patterns: frozenset[str]) -> bool:
    if not patterns:
        return False
    import fnmatch
    rel = rel_path.replace("\\", "/")
    for p in patterns:
        # Anchored patterns (starting with /) match from repo root only.
        if p.startswith("/"):
            if fnmatch.fnmatchcase(rel, p[1:]):
                return True
            continue
        # Unanchored: match against the full path AND any path suffix (matching git's behavior).
        if fnmatch.fnmatchcase(rel, p):
            return True
        # Also try matching just the basename for simple patterns like *.designer.cs.
        if "/" not in p and fnmatch.fnmatchcase(Path(rel).name, p):
            return True
    return False


def _classify_generated(rel_path: str, source_bytes: bytes | None, gitattrs_patterns: frozenset[str]) -> bool:
    """Return True when the file is machine-generated (wave 130rj).

    Three signal sources (any-of):
    1. In-file header marker — substring or regex match within first 200 bytes.
    2. Path heuristic — directory segment or filename suffix.
    3. `.gitattributes` `linguist-generated=true` pattern match.
    """
    rel = rel_path.replace("\\", "/")
    # Filename suffix (case-insensitive)
    lower_name = Path(rel).name.lower()
    for suffix in _GENERATED_FILENAME_SUFFIXES:
        if lower_name.endswith(suffix):
            return True
    # Directory segment (any segment)
    parts = rel.split("/")
    for seg in _GENERATED_DIR_SEGMENTS:
        # Multi-segment patterns like "build/generated" need a sliding-window check.
        seg_parts = seg.split("/")
        if len(seg_parts) == 1:
            if seg in parts:
                return True
        else:
            for i in range(len(parts) - len(seg_parts) + 1):
                if parts[i:i + len(seg_parts)] == seg_parts:
                    return True
    # .gitattributes
    if _path_matches_gitattributes(rel, gitattrs_patterns):
        return True
    # In-file header markers (limit to first 200 bytes to avoid false positives on
    # docstrings, comments, or in-file string literals far below the file head).
    if source_bytes is not None:
        head = source_bytes[:200]
        for sig in _GENERATED_HEADER_SIGNATURES:
            if sig.encode("utf-8", errors="replace") in head:
                return True
        for pattern in _GENERATED_HEADER_PATTERNS:
            if pattern.search(head):
                return True
    return False


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
    # Explicit per-language call-node grammar names (wave 130ol). When non-empty,
    # _ts_is_call_node consults this set instead of the legacy substring-match
    # heuristic on "expression" — which over-matched try_expression, await_expression,
    # binary_expression, etc., producing edges to language keywords.
    call_node_types: frozenset[str] = frozenset()
    # Per-language reserved-word stop terms (wave 130ol). Augments the global
    # _STOP_TERMS set. Identifiers in this set are never emitted as call candidates
    # from the regex fallback path.
    stop_terms: frozenset[str] = frozenset()
    # Per-language builtin-and-common-value denylist (wave 130ol). The cross-file
    # resolution pass refuses to rewrite `external::<name>` to a project-internal
    # node when <name> is in this set — even if a project file happens to define
    # a symbol with the same simple name. Prevents mis-resolving stdlib calls
    # (Python `len`/`range`, JS `Object`/`Array`, Swift `String`, etc.) to
    # same-named project definitions.
    builtin_denylist: frozenset[str] = frozenset()


# Tree-sitter call-node grammar names per language (AC-3). The legacy
# substring-match on "expression" matched many non-call node types
# (try_expression, await_expression, binary_expression, ...) and produced
# `external::<keyword>` edges via the regex-fallback candidate extractor.
_TS_CALL_NODES_DEFAULT = frozenset({"call_expression"})
_TS_CALL_NODES_JS = frozenset({"call_expression", "new_expression"})
_TS_CALL_NODES_GO = frozenset({"call_expression"})
_TS_CALL_NODES_RUST = frozenset({"call_expression", "macro_invocation"})
_TS_CALL_NODES_JAVA = frozenset({"method_invocation", "object_creation_expression"})
_TS_CALL_NODES_KOTLIN = frozenset({"call_expression"})
_TS_CALL_NODES_C = frozenset({"call_expression"})
_TS_CALL_NODES_CPP = frozenset({"call_expression"})
_TS_CALL_NODES_CSHARP = frozenset({"invocation_expression", "object_creation_expression"})
_TS_CALL_NODES_SWIFT = frozenset({"call_expression"})
_TS_CALL_NODES_OBJC = frozenset({"message_expression"})
_TS_CALL_NODES_SCALA = frozenset({"call_expression"})
_TS_CALL_NODES_RUBY = frozenset({"call", "method_call", "command"})
_TS_CALL_NODES_PHP = frozenset({
    "function_call_expression",
    "member_call_expression",
    "scoped_call_expression",
})
_TS_CALL_NODES_BASH = frozenset({"command"})

# Per-language reserved-word stop terms (AC-5).
_TS_STOP_PYTHON = frozenset({
    "self", "cls", "True", "False", "None", "if", "elif", "else", "for", "while",
    "return", "yield", "break", "continue", "pass", "raise", "try", "except",
    "finally", "with", "as", "import", "from", "def", "class", "lambda", "global",
    "nonlocal", "and", "or", "not", "in", "is",
})
_TS_STOP_JS = frozenset({
    "var", "let", "const", "function", "class", "extends", "implements", "interface",
    "type", "enum", "typeof", "instanceof", "void", "await", "async", "yield",
    "return", "if", "else", "for", "while", "do", "switch", "case", "default",
    "break", "continue", "throw", "try", "catch", "finally", "new", "delete",
    "in", "of", "this", "super",
})
_TS_STOP_GO = frozenset({
    "func", "var", "const", "type", "struct", "interface", "package", "import",
    "return", "if", "else", "for", "range", "switch", "case", "default", "break",
    "continue", "go", "defer", "select", "chan", "map", "fallthrough", "goto",
})
_TS_STOP_RUST = frozenset({
    "fn", "let", "mut", "pub", "mod", "use", "struct", "enum", "impl", "trait",
    "type", "const", "static", "if", "else", "match", "for", "while", "loop",
    "break", "continue", "return", "as", "in", "where", "ref", "move", "async",
    "await", "self", "Self", "super", "crate",
})
_TS_STOP_JAVA = frozenset({
    "public", "private", "protected", "static", "final", "abstract", "synchronized",
    "transient", "volatile", "class", "interface", "enum", "extends", "implements",
    "import", "package", "return", "if", "else", "for", "while", "do", "switch",
    "case", "default", "break", "continue", "throw", "throws", "try", "catch",
    "finally", "new", "this", "super", "instanceof", "void",
})
_TS_STOP_KOTLIN = frozenset({
    "fun", "val", "var", "class", "interface", "object", "enum", "data", "sealed",
    "open", "override", "abstract", "final", "private", "protected", "internal",
    "public", "import", "package", "return", "if", "else", "for", "while", "do",
    "when", "is", "in", "as", "throw", "try", "catch", "finally", "this", "super",
    "init", "constructor", "by", "lateinit", "vararg", "inline", "noinline",
    "crossinline", "reified", "tailrec", "operator", "infix", "suspend",
})
_TS_STOP_C = frozenset({
    "int", "char", "short", "long", "float", "double", "void", "signed", "unsigned",
    "const", "volatile", "static", "extern", "auto", "register", "struct", "union",
    "enum", "typedef", "sizeof", "return", "if", "else", "for", "while", "do",
    "switch", "case", "default", "break", "continue", "goto",
})
_TS_STOP_CSHARP = frozenset({
    "public", "private", "protected", "internal", "static", "abstract", "virtual",
    "override", "sealed", "readonly", "const", "class", "interface", "struct",
    "enum", "namespace", "using", "return", "if", "else", "for", "foreach", "in",
    "while", "do", "switch", "case", "default", "break", "continue", "throw",
    "try", "catch", "finally", "new", "this", "base", "is", "as", "typeof",
    "void", "var", "async", "await",
})
_TS_STOP_SWIFT = frozenset({
    "func", "let", "var", "class", "struct", "enum", "protocol", "extension",
    "import", "public", "private", "internal", "fileprivate", "open", "static",
    "final", "lazy", "weak", "unowned", "mutating", "nonmutating", "inout",
    "throws", "rethrows", "if", "else", "for", "while", "repeat", "do", "catch",
    "defer", "guard", "switch", "case", "default", "break", "continue", "return",
    "where", "as", "is", "in", "init", "deinit", "self", "Self", "super",
    "Type", "associatedtype", "typealias", "try", "await", "async",
})
_TS_STOP_OBJC = _TS_STOP_C | frozenset({"@interface", "@implementation", "@end", "@property", "@synthesize", "self", "super", "id", "nil", "YES", "NO", "BOOL", "nonatomic", "atomic", "strong", "weak", "copy", "assign", "readonly", "readwrite"})
_TS_STOP_RUBY = frozenset({
    "def", "end", "class", "module", "if", "elsif", "else", "unless", "case",
    "when", "then", "for", "while", "until", "do", "break", "next", "redo", "retry",
    "return", "yield", "begin", "rescue", "ensure", "raise", "require", "include",
    "extend", "self", "super", "nil", "true", "false", "and", "or", "not", "in",
})
_TS_STOP_PHP = frozenset({
    "function", "class", "interface", "trait", "extends", "implements", "namespace",
    "use", "public", "private", "protected", "static", "final", "abstract", "const",
    "var", "return", "if", "else", "elseif", "for", "foreach", "as", "while", "do",
    "switch", "case", "default", "break", "continue", "throw", "try", "catch",
    "finally", "new", "self", "parent", "this", "instanceof", "echo", "print",
    "isset", "unset", "empty",
})
_TS_STOP_SCALA = frozenset({
    "def", "val", "var", "lazy", "class", "object", "trait", "case", "match",
    "extends", "with", "import", "package", "return", "if", "else", "for", "while",
    "do", "yield", "throw", "try", "catch", "finally", "new", "this", "super",
    "implicit", "private", "protected", "abstract", "override", "final", "sealed",
    "type",
})
_TS_STOP_BASH = frozenset({
    "if", "then", "elif", "else", "fi", "for", "while", "until", "do", "done",
    "case", "esac", "function", "in", "select", "time", "return", "exit", "break",
    "continue", "local", "export", "readonly", "declare", "typeset",
})

# Per-language builtin / common-value denylist (AC-1a). These names stay
# `external::*` even when a project node defines a same-named symbol.
_TS_DENY_PYTHON = frozenset({
    "len", "range", "str", "int", "float", "bool", "list", "dict", "set", "tuple",
    "bytes", "bytearray", "frozenset", "print", "input", "open", "iter", "next",
    "enumerate", "zip", "map", "filter", "sorted", "reversed", "sum", "min", "max",
    "abs", "round", "pow", "divmod", "hash", "id", "type", "isinstance", "issubclass",
    "super", "object", "Exception", "ValueError", "TypeError", "KeyError",
    "IndexError", "AttributeError", "RuntimeError", "StopIteration", "True",
    "False", "None", "callable", "hasattr", "getattr", "setattr", "delattr",
    "vars", "dir", "globals", "locals", "repr", "format",
})
_TS_DENY_JS = frozenset({
    "Object", "Array", "String", "Number", "Boolean", "Promise", "Map", "Set",
    "Date", "Math", "JSON", "RegExp", "Error", "TypeError", "RangeError", "Symbol",
    "Proxy", "Reflect", "Function", "globalThis", "console", "undefined", "null",
    "NaN", "Infinity", "parseInt", "parseFloat", "isNaN", "isFinite",
    "encodeURIComponent", "decodeURIComponent",
})
_TS_DENY_GO = frozenset({
    "len", "cap", "make", "new", "panic", "recover", "append", "copy", "delete",
    "close", "print", "println", "error", "string", "int", "int8", "int16",
    "int32", "int64", "uint", "uint8", "uint16", "uint32", "uint64", "uintptr",
    "float32", "float64", "complex64", "complex128", "bool", "byte", "rune",
    "true", "false", "nil",
})
_TS_DENY_RUST = frozenset({
    "Some", "None", "Ok", "Err", "Box", "Vec", "String", "Option", "Result",
    "panic", "println", "print", "eprintln", "eprint", "format", "vec", "assert",
    "assert_eq", "assert_ne", "debug_assert", "unreachable", "todo", "unimplemented",
    "matches", "write", "writeln", "dbg",
})
_TS_DENY_JAVA = frozenset({
    "String", "Integer", "Boolean", "Double", "Float", "Long", "Short", "Byte",
    "Character", "Object", "List", "Map", "Set", "Collection", "Iterable",
    "Exception", "RuntimeException", "IllegalArgumentException",
    "IllegalStateException", "NullPointerException", "IndexOutOfBoundsException",
    "System", "Math", "Thread", "Class", "Number", "Optional", "Stream",
    "Arrays", "Collections", "Objects",
})
_TS_DENY_KOTLIN = _TS_DENY_JAVA | frozenset({
    "Any", "Unit", "Nothing", "Pair", "Triple", "Sequence", "Array", "IntArray",
    "DoubleArray", "BooleanArray", "ByteArray", "CharArray", "FloatArray",
    "LongArray", "ShortArray", "MutableList", "MutableMap", "MutableSet",
    "listOf", "mapOf", "setOf", "mutableListOf", "mutableMapOf", "mutableSetOf",
    "println", "print", "error", "TODO", "require", "check", "let", "run",
    "with", "apply", "also",
})
_TS_DENY_CSHARP = frozenset({
    "String", "Int32", "Int64", "Int16", "Boolean", "Double", "Single", "Decimal",
    "Object", "List", "Dictionary", "HashSet", "IEnumerable", "Exception",
    "ArgumentException", "InvalidOperationException", "NullReferenceException",
    "ArgumentNullException", "Console", "Math", "DateTime", "TimeSpan", "Guid",
    "Task", "ValueTask", "Action", "Func", "Tuple",
})
_TS_DENY_SWIFT = frozenset({
    "String", "Int", "Int8", "Int16", "Int32", "Int64", "UInt", "UInt8", "UInt16",
    "UInt32", "UInt64", "Double", "Float", "Bool", "Array", "Dictionary", "Set",
    "Optional", "Result", "Date", "Data", "URL", "URLRequest", "URLSession",
    "Error", "Never", "Void", "Any", "AnyObject", "AnyHashable", "Range",
    "ClosedRange", "Character",
})
_TS_DENY_OBJC = frozenset({
    "NSString", "NSNumber", "NSArray", "NSDictionary", "NSSet", "NSObject",
    "NSError", "NSData", "NSDate", "NSURL", "NSMutableArray", "NSMutableDictionary",
    "NSMutableString", "NSMutableSet", "NSException", "BOOL", "id", "Class",
    "SEL", "IMP",
})
_TS_DENY_RUBY = frozenset({
    "String", "Integer", "Float", "Array", "Hash", "Symbol", "Range", "Regexp",
    "Object", "Class", "Module", "Proc", "Lambda", "NilClass", "TrueClass",
    "FalseClass", "Exception", "StandardError", "RuntimeError", "ArgumentError",
    "TypeError", "NameError", "NoMethodError", "puts", "print", "p", "raise",
    "require", "require_relative", "attr_accessor", "attr_reader", "attr_writer",
})
_TS_DENY_PHP = frozenset({
    "true", "false", "null", "array", "string", "int", "float", "bool", "object",
    "callable", "iterable", "void", "Exception", "Error", "TypeError",
    "ValueError", "RuntimeException", "InvalidArgumentException",
    "LogicException", "OutOfRangeException", "Closure", "Generator",
    "ArrayObject", "stdClass", "Iterator", "Traversable",
})
_TS_DENY_SCALA = frozenset({
    "String", "Int", "Long", "Double", "Float", "Boolean", "Char", "Byte", "Short",
    "Unit", "Nothing", "Any", "AnyRef", "AnyVal", "Null", "Option", "Some", "None",
    "Either", "Left", "Right", "List", "Seq", "Set", "Map", "Vector", "Array",
    "Tuple1", "Tuple2", "Tuple3", "Exception", "RuntimeException", "Throwable",
    "Future", "println", "print",
})
_TS_DENY_BASH = frozenset({
    "echo", "printf", "read", "cd", "pwd", "ls", "rm", "cp", "mv", "mkdir", "rmdir",
    "touch", "cat", "head", "tail", "grep", "sed", "awk", "find", "test", "true",
    "false", "exit", "source", "exec", "trap", "set", "unset", "shift", "let",
    "eval", "alias", "history", "type", "which", "command",
})

_TS_CODE_PROFILE = _TsLanguageProfile(mode="code")  # generic fallback for code mode
_TS_MARKUP_PROFILE = _TsLanguageProfile(mode="markup")
_TS_SQL_PROFILE = _TsLanguageProfile(mode="sql")
_TS_CONFIG_PROFILE = _TsLanguageProfile(mode="config")

_TS_LANGUAGE_PROFILES: dict[str, _TsLanguageProfile] = {
    "javascript": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_JS, stop_terms=_TS_STOP_JS, builtin_denylist=_TS_DENY_JS),
    "typescript": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_JS, stop_terms=_TS_STOP_JS, builtin_denylist=_TS_DENY_JS),
    "go": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_GO, stop_terms=_TS_STOP_GO, builtin_denylist=_TS_DENY_GO),
    "rust": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_RUST, stop_terms=_TS_STOP_RUST, builtin_denylist=_TS_DENY_RUST),
    "java": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_JAVA, stop_terms=_TS_STOP_JAVA, builtin_denylist=_TS_DENY_JAVA),
    "c": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_C, stop_terms=_TS_STOP_C, builtin_denylist=frozenset()),
    "cpp": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_CPP, stop_terms=_TS_STOP_C, builtin_denylist=frozenset()),
    "csharp": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_CSHARP, stop_terms=_TS_STOP_CSHARP, builtin_denylist=_TS_DENY_CSHARP),
    "bash": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_BASH, stop_terms=_TS_STOP_BASH, builtin_denylist=_TS_DENY_BASH),
    "kotlin": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_KOTLIN, stop_terms=_TS_STOP_KOTLIN, builtin_denylist=_TS_DENY_KOTLIN),
    "swift": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_SWIFT, stop_terms=_TS_STOP_SWIFT, builtin_denylist=_TS_DENY_SWIFT),
    "objc": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_OBJC, stop_terms=_TS_STOP_OBJC, builtin_denylist=_TS_DENY_OBJC),
    "scala": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_SCALA, stop_terms=_TS_STOP_SCALA, builtin_denylist=_TS_DENY_SCALA),
    "ruby": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_RUBY, stop_terms=_TS_STOP_RUBY, builtin_denylist=_TS_DENY_RUBY),
    "php": _TsLanguageProfile(mode="code", call_node_types=_TS_CALL_NODES_PHP, stop_terms=_TS_STOP_PHP, builtin_denylist=_TS_DENY_PHP),
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

# Aggregate denylist across all known languages — used by the cross-file
# resolution pass when the target node's source language is unknown (e.g. edges
# without a source-file context). Conservative: a name is denied if ANY language
# considers it a builtin.
_TS_GLOBAL_DENYLIST: frozenset[str] = frozenset().union(*(
    profile.builtin_denylist for profile in _TS_LANGUAGE_PROFILES.values()
))


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
    # Variable bindings (Swift/Kotlin `property_declaration`, TS/JS/C# `variable_declaration`,
    # Java `local_variable_declaration`/`field_declaration`, Rust `let_declaration`, Go
    # `var_declaration`/`const_declaration`/`short_var_declaration`) are NOT scope-pushing.
    # The kind ``variable`` is excluded from ``_ts_is_scope_node`` so calls inside
    # ``let result = foo()`` are correctly attributed to the enclosing function (wave 130ol).
    if lower in _TS_VARIABLE_DEFINITION_TYPES:
        return "variable"
    if any(token in lower for token in ("method", "constructor", "member")):
        return "function"
    if any(token in lower for token in ("class", "interface", "struct", "enum", "trait", "record")):
        return "class"
    if any(token in lower for token in ("module", "namespace", "package", "object")):
        return "module"
    if any(token in lower for token in ("table", "view", "schema", "resource")):
        return "class"
    return "function"


# Per-language variable-binding node types — never push scope (wave 130ol).
# Without this, a call inside ``let result = foo()`` gets attributed to
# ``…enclosingFunction.result`` instead of ``…enclosingFunction``, and when
# ``result`` is short or has no external users the short-symbol pruning pass
# silently drops the call edge with the local-variable node.
_TS_VARIABLE_DEFINITION_TYPES = frozenset({
    # Swift / Kotlin
    "property_declaration",
    # Java
    "local_variable_declaration",
    "field_declaration",
    # C#
    "variable_declaration",
    # JS / TS
    "lexical_declaration",
    "variable_statement",
    # Rust
    "let_declaration",
    # Go
    "var_declaration",
    "const_declaration",
    "short_var_declaration",
    # C / C++ — note: `declaration` is too generic (also covers function decls)
    # so we don't catch those here. Calls in C/C++ initializers are rare in practice.
})


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
    # Wave 1319k: Ruby grammar uses bare `class`, `module`, `method`,
    # `singleton_method` node types (no `_declaration`/`_definition`/`_item`
    # suffix). Recognize these explicitly.
    if lower in ("class", "module", "method", "singleton_method"):
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


def _ts_is_call_node(node_type: str, mode: str, profile: _TsLanguageProfile | None = None) -> bool:
    """Detect tree-sitter call nodes (wave 130ol).

    For code mode with a known per-language profile, consults the explicit
    ``call_node_types`` set. The legacy substring-match heuristic on
    ``"expression"`` matched every ``*_expression`` node type
    (``try_expression``, ``await_expression``, ``binary_expression``, etc.)
    and produced ``external::<keyword>`` edges via the regex-fallback path.
    """
    lower = node_type.lower()
    if mode == "markup":
        return any(token in lower for token in ("script", "style", "form", "link", "anchor", "event", "handler"))
    if mode == "sql":
        return any(token in lower for token in ("select", "where", "join", "from", "into", "call", "update", "delete", "insert"))
    if mode == "config":
        return any(token in lower for token in ("command", "action", "script", "target", "task", "job", "step", "run"))
    if profile is not None and profile.call_node_types:
        return node_type in profile.call_node_types
    return any(token in lower for token in _TS_CALL_KEYWORDS) or "call" in lower or "invoke" in lower or "access" in lower


def _ts_is_scope_node(node_type: str, kind: str, mode: str) -> bool:
    """Whether a definition node should push a new scope frame.

    Variable bindings (kind ``variable``) are intentionally excluded so calls
    inside ``let x = foo()`` attribute to the enclosing function rather than
    creating a fragile ``…fn.x`` scope that the short-symbol pruning pass
    can silently drop (wave 130ol).
    """
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


def _ts_candidate_rejected(candidate: str) -> bool:
    """Reject candidates that are language artifacts, not real callees (wave 130ol).

    - ``_`` (Swift underscore wildcard) — produced degenerate paths in code_graph_path
    - ``foo:`` (Swift named-argument label / general label suffix) — not a callable
    - Empty / whitespace-only strings
    """
    if not candidate or not candidate.strip():
        return True
    if candidate == "_":
        return True
    if candidate.endswith(":"):
        return True
    return False


# Node types that wrap a call's argument list — skip these when walking
# named_children for the positional-callee fallback. The callee is the FIRST
# non-argument child of the call expression.
_TS_ARGS_NODE_TYPES = frozenset({
    "call_suffix",            # Swift
    "value_arguments",        # Kotlin
    "argument_list",          # Java, C#, C, C++, Ruby
    "arguments",              # Scala, JS/TS, Python (when via tree-sitter)
    "parameter_list",         # rare grammars
    "parenthesized_expression",  # some grammars wrap args this way
    "trailing_closure",       # Swift trailing closure (not the callee)
    "lambda_literal",         # Kotlin lambda arg
})

# Node types whose text is itself an identifier we can use as a call target.
_TS_IDENTIFIER_TYPES = frozenset({
    "identifier",
    "simple_identifier",
    "type_identifier",
    "name",
    "variable_name",
    "field_identifier",
    "scoped_identifier",
    "shorthand_identifier",
})

# Node types that represent a member-access / navigation chain. For
# ``f.bar()`` the call-expression's callee child is a navigation_expression
# whose RIGHTMOST identifier child (``bar``) is the method name we want as
# the call target.
_TS_NAVIGATION_TYPES = frozenset({
    "navigation_expression",          # Swift
    "navigation_suffix",              # Kotlin (nested)
    "member_access_expression",       # C#
    "member_expression",              # JS/TS
    "field_access",                   # Java
    "field_expression",               # C/C++
    "field_access_expression",        # generic
    "scoped_call_expression",         # PHP
    "qualified_identifier",           # C++ namespace::name
    "selector_expression",            # Go: x.Method
    "method_expression",              # rare
    "binary_expression",              # some grammars treat `a.b` as binary
})


def _ts_extract_callee_recursive(node, source_bytes: bytes) -> str | None:
    """Find the rightmost identifier in a callee expression (wave 130ol).

    For ``f.bar()`` the callee child is a navigation/member-access expression
    whose RIGHTMOST identifier (``bar``) is the method name. For chained
    ``a.b.c()`` we pick ``c``. For a bare ``helper()`` the callee child is
    already a simple identifier — return its text directly.
    """
    if node.type in _TS_IDENTIFIER_TYPES:
        text = _ts_node_text(node, source_bytes)
        return text if text and not _ts_candidate_rejected(text) else None
    if node.type in _TS_NAVIGATION_TYPES:
        # Prefer the rightmost identifier — that's the method/property name.
        children = list(node.named_children)
        for child in reversed(children):
            result = _ts_extract_callee_recursive(child, source_bytes)
            if result:
                return result
        return None
    # Unknown structure — try named children in order and pick the first
    # identifier-like result. Cheap best-effort.
    for child in node.named_children:
        result = _ts_extract_callee_recursive(child, source_bytes)
        if result:
            return result
    return None


# =============================================================================
# Java receiver-type resolution (wave 13129 — 1312l).
#
# Source of truth — graph_indexer.py owns these helpers; server_impl.py's
# code_callhierarchy defense-in-depth filter (for cached pre-bump graphs)
# imports them via `_load_script("graph_indexer")` rather than duplicating.
# Single implementation; no drift risk.
#
# The resolver must short-circuit on first uncertain branch (wave 13129 council
# action item: performance-reviewer). It returns None as soon as the receiver
# expression can't be classified into one of the three handled cases (this/bare,
# simple identifier, ClassName static).
# =============================================================================


def _extract_simple_java_type_name(type_node, source_bytes: bytes) -> str | None:
    """Extract the simple class name from a Java type AST node."""
    n_type = getattr(type_node, "type", "")
    if n_type == "type_identifier":
        return source_bytes[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace")
    if n_type == "generic_type":
        for child in (getattr(type_node, "children", []) or []):
            if getattr(child, "type", "") in ("type_identifier", "scoped_type_identifier"):
                return _extract_simple_java_type_name(child, source_bytes)
        return None
    if n_type == "scoped_type_identifier":
        last_name = None
        for child in (getattr(type_node, "children", []) or []):
            if getattr(child, "type", "") == "type_identifier":
                last_name = child
        if last_name is not None:
            return source_bytes[last_name.start_byte:last_name.end_byte].decode("utf-8", errors="replace")
        return None
    if n_type == "array_type":
        elem = type_node.child_by_field_name("element")
        if elem is not None:
            return _extract_simple_java_type_name(elem, source_bytes)
        return None
    return None


def _find_enclosing_java_class_name(node, source_bytes: bytes) -> str | None:
    """Walk up the AST to the enclosing class_declaration's name."""
    cur = getattr(node, "parent", None)
    while cur is not None:
        if getattr(cur, "type", "") == "class_declaration":
            name_node = cur.child_by_field_name("name")
            if name_node is not None:
                return source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
            return None
        cur = getattr(cur, "parent", None)
    return None


def _search_java_declarations_in_scope(scope_node, name: str, source_bytes: bytes) -> str | None:
    """Search descendants of scope_node for a matching variable/parameter/field declaration."""
    stack = [scope_node]
    while stack:
        n = stack.pop()
        n_type = getattr(n, "type", "")
        if n_type in ("local_variable_declaration", "field_declaration"):
            type_node = n.child_by_field_name("type")
            for child in (getattr(n, "children", []) or []):
                if getattr(child, "type", "") == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    if name_node is not None and type_node is not None:
                        var_name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                        if var_name == name:
                            return _extract_simple_java_type_name(type_node, source_bytes)
        elif n_type == "formal_parameter":
            type_node = n.child_by_field_name("type")
            name_node = n.child_by_field_name("name")
            if name_node is not None and type_node is not None:
                param_name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                if param_name == name:
                    return _extract_simple_java_type_name(type_node, source_bytes)
        # Don't descend into nested method/class bodies — they're separate scopes.
        if n_type in ("method_declaration", "constructor_declaration", "class_declaration") and n is not scope_node:
            continue
        stack.extend(reversed(getattr(n, "children", []) or []))
    return None


def _resolve_java_identifier_type(name: str, ref_node, source_bytes: bytes) -> str | None:
    """Resolve a Java identifier to its declared simple type name.

    Short-circuits on first uncertain branch per wave 13129 performance-reviewer
    action item.
    """
    cur = getattr(ref_node, "parent", None)
    while cur is not None:
        cur_type = getattr(cur, "type", "")
        if cur_type in ("method_declaration", "constructor_declaration", "class_declaration"):
            resolved = _search_java_declarations_in_scope(cur, name, source_bytes)
            if resolved is not None:
                return resolved
            if cur_type == "class_declaration":
                break
        cur = getattr(cur, "parent", None)
    if name and name[:1].isupper():
        return name
    return None


def _resolve_java_receiver_type(invocation_node, source_bytes: bytes) -> str | None:
    """Resolve the simple type name of a Java method_invocation's receiver.

    Returns the simple class name when resolvable, or None when uncertain
    (preserve the candidate per false-positive bias). Per wave 13129 council
    action item (performance-reviewer), short-circuits as soon as the receiver
    expression can't be classified — no exhaustive scope walks past the first
    identifiable ambiguity.
    """
    if invocation_node is None or getattr(invocation_node, "type", "") != "method_invocation":
        return None
    obj = invocation_node.child_by_field_name("object")
    if obj is None:
        return _find_enclosing_java_class_name(invocation_node, source_bytes)
    obj_type = getattr(obj, "type", "")
    if obj_type == "this":
        return _find_enclosing_java_class_name(invocation_node, source_bytes)
    if obj_type == "super":
        return None  # uncertain — defer inheritance walk
    if obj_type == "identifier":
        ident_text = source_bytes[obj.start_byte:obj.end_byte].decode("utf-8", errors="replace")
        return _resolve_java_identifier_type(ident_text, invocation_node, source_bytes)
    # field_access, cast_expression, method_invocation chains, lambdas → uncertain.
    return None


# =============================================================================
# Kotlin receiver-type resolution (wave 13194).
#
# Mirrors the Java helpers. Conservative coverage: this/super/bare,
# explicit type annotations (`val foo: Foo = ...`), simple identifiers, and
# `ClassName.method()` static-style. Deferred: var-typed locals with type
# inference, nullable receivers (`foo?.bar()`), extension functions, lambdas.
# Uncertain cases return None (false-positive bias preserved).
# =============================================================================


def _extract_simple_kotlin_type_name(type_node, source_bytes: bytes) -> str | None:
    """Extract simple class name from a Kotlin type AST node.

    Verified Kotlin grammar (2026-06-01):
    - ``user_type`` wraps a child of type ``identifier`` (not ``type_identifier``).
    - ``nullable_type`` wraps a ``user_type``.
    """
    n_type = getattr(type_node, "type", "")
    if n_type == "user_type":
        # Kotlin user_type wraps an `identifier` child carrying the type name.
        for child in (getattr(type_node, "children", []) or []):
            if getattr(child, "type", "") in ("identifier", "type_identifier"):
                return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
        return None
    if n_type == "type_identifier":
        return source_bytes[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace")
    if n_type == "nullable_type":
        for child in (getattr(type_node, "children", []) or []):
            if getattr(child, "type", "") in ("user_type", "type_identifier"):
                return _extract_simple_kotlin_type_name(child, source_bytes)
        return None
    return None


def _find_enclosing_kotlin_class_name(node, source_bytes: bytes) -> str | None:
    """Walk up to the enclosing Kotlin class_declaration / object_declaration."""
    cur = getattr(node, "parent", None)
    while cur is not None:
        if getattr(cur, "type", "") in ("class_declaration", "object_declaration", "interface_declaration"):
            # Kotlin class declaration: first child is `class` / `object`,
            # then `type_identifier` (the name).
            for child in (getattr(cur, "children", []) or []):
                if getattr(child, "type", "") == "type_identifier":
                    return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            return None
        cur = getattr(cur, "parent", None)
    return None


def _search_kotlin_declarations_in_scope(scope_node, name: str, source_bytes: bytes) -> str | None:
    """Search Kotlin scope for `val name: Type = ...` or function parameter.

    Kotlin tree-sitter grammar uses plain `identifier` for binding names and
    type names — NOT `simple_identifier` (which is reserved for other contexts).
    Verified by AST inspection 2026-06-01.
    """
    stack = [scope_node]
    while stack:
        n = stack.pop()
        n_type = getattr(n, "type", "")
        if n_type == "property_declaration":
            # Kotlin: `val name: Type = value` — variable_declaration child holds
            # `identifier <name>` + `:` + `user_type <Type>`.
            for child in (getattr(n, "children", []) or []):
                if getattr(child, "type", "") == "variable_declaration":
                    name_child = None
                    type_child = None
                    for gc in (getattr(child, "children", []) or []):
                        gc_type = getattr(gc, "type", "")
                        if gc_type == "identifier" and name_child is None:
                            name_child = gc
                        elif gc_type in ("user_type", "type_identifier", "nullable_type"):
                            type_child = gc
                    if name_child is not None and type_child is not None:
                        var_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                        if var_name == name:
                            return _extract_simple_kotlin_type_name(type_child, source_bytes)
        elif n_type == "parameter":
            # Kotlin: `fun foo(name: Type)` — parameter has identifier + user_type.
            name_child = None
            type_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct == "identifier" and name_child is None:
                    name_child = child
                elif ct in ("user_type", "type_identifier", "nullable_type"):
                    type_child = child
            if name_child is not None and type_child is not None:
                param_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if param_name == name:
                    return _extract_simple_kotlin_type_name(type_child, source_bytes)
        # Don't recurse into nested function / class bodies.
        if n_type in ("function_declaration", "class_declaration", "object_declaration", "interface_declaration") and n is not scope_node:
            continue
        stack.extend(reversed(getattr(n, "children", []) or []))
    return None


def _resolve_kotlin_identifier_type(name: str, ref_node, source_bytes: bytes) -> str | None:
    """Resolve a Kotlin identifier to its declared simple type name."""
    cur = getattr(ref_node, "parent", None)
    while cur is not None:
        cur_type = getattr(cur, "type", "")
        if cur_type in ("function_declaration", "class_declaration", "object_declaration", "interface_declaration"):
            resolved = _search_kotlin_declarations_in_scope(cur, name, source_bytes)
            if resolved is not None:
                return resolved
            if cur_type in ("class_declaration", "object_declaration", "interface_declaration"):
                break
        cur = getattr(cur, "parent", None)
    if name and name[:1].isupper():
        return name
    return None


def _resolve_kotlin_receiver_type(call_node, source_bytes: bytes) -> str | None:
    """Resolve the simple type name of a Kotlin call_expression's receiver.

    Kotlin tree-sitter grammar shape (verified 2026-06-01):
    - Bare call `bar()`: call_expression has child `identifier "bar"` + `value_arguments`.
    - Member call `foo.bar()`: call_expression has child `navigation_expression`
      (children: `identifier "foo"` + `.` + `identifier "bar"`) + `value_arguments`.
    """
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    if callee_type == "identifier":
        # Bare call `bar()` → resolves to enclosing class.
        return _find_enclosing_kotlin_class_name(call_node, source_bytes)
    if callee_type == "navigation_expression":
        # Children: identifier (receiver), '.', identifier (method). Take the
        # first identifier as the receiver.
        nav_children = list(getattr(callee, "children", []) or [])
        receiver = next(
            (c for c in nav_children if getattr(c, "type", "") == "identifier"),
            None,
        )
        if receiver is None:
            return None
        text = source_bytes[receiver.start_byte:receiver.end_byte].decode("utf-8", errors="replace")
        if text == "this":
            return _find_enclosing_kotlin_class_name(call_node, source_bytes)
        if text == "super":
            return None
        return _resolve_kotlin_identifier_type(text, call_node, source_bytes)
    return None


def _resolve_kotlin_call_target(
    call_node, source_bytes: bytes, symbol_lookup: dict[str, str]
) -> str | None:
    """Resolve a Kotlin call_expression to a graph node id (project or external-qualified)."""
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    method_name: str | None = None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    if callee_type == "identifier":
        method_name = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace")
    elif callee_type == "navigation_expression":
        # For `foo.bar()`, the method name is the LAST identifier in the
        # navigation_expression (after the `.`).
        nav_children = list(getattr(callee, "children", []) or [])
        identifiers = [c for c in nav_children if getattr(c, "type", "") == "identifier"]
        if len(identifiers) >= 2:
            method_node = identifiers[-1]
            method_name = source_bytes[method_node.start_byte:method_node.end_byte].decode("utf-8", errors="replace")
    if not method_name:
        return None
    receiver_type = _resolve_kotlin_receiver_type(call_node, source_bytes)
    if receiver_type is None:
        return None
    qualified = f"{receiver_type}.{method_name}"
    if qualified in symbol_lookup:
        return symbol_lookup[qualified]
    return f"external::{receiver_type}.{method_name}"


# =============================================================================
# C# receiver-type resolution (wave 13194).
# Mirrors Java; AST node names differ (`invocation_expression`,
# `member_access_expression`, etc.).
# =============================================================================


def _extract_simple_csharp_type_name(type_node, source_bytes: bytes) -> str | None:
    n_type = getattr(type_node, "type", "")
    if n_type == "identifier":
        return source_bytes[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace")
    if n_type == "predefined_type":
        return source_bytes[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace")
    if n_type == "qualified_name":
        # `System.IO.Stream` → take the last identifier (`Stream`).
        last_ident = None
        for child in (getattr(type_node, "children", []) or []):
            if getattr(child, "type", "") == "identifier":
                last_ident = child
        if last_ident is not None:
            return source_bytes[last_ident.start_byte:last_ident.end_byte].decode("utf-8", errors="replace")
        return None
    if n_type == "generic_name":
        for child in (getattr(type_node, "children", []) or []):
            if getattr(child, "type", "") == "identifier":
                return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
        return None
    if n_type == "nullable_type":
        for child in (getattr(type_node, "children", []) or []):
            t = getattr(child, "type", "")
            if t in ("identifier", "predefined_type", "qualified_name", "generic_name"):
                return _extract_simple_csharp_type_name(child, source_bytes)
        return None
    if n_type == "array_type":
        for child in (getattr(type_node, "children", []) or []):
            t = getattr(child, "type", "")
            if t in ("identifier", "predefined_type", "qualified_name", "generic_name"):
                return _extract_simple_csharp_type_name(child, source_bytes)
        return None
    return None


def _find_enclosing_csharp_class_name(node, source_bytes: bytes) -> str | None:
    cur = getattr(node, "parent", None)
    while cur is not None:
        if getattr(cur, "type", "") in ("class_declaration", "struct_declaration", "interface_declaration", "record_declaration"):
            for child in (getattr(cur, "children", []) or []):
                if getattr(child, "type", "") == "identifier":
                    return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            return None
        cur = getattr(cur, "parent", None)
    return None


def _search_csharp_declarations_in_scope(scope_node, name: str, source_bytes: bytes) -> str | None:
    stack = [scope_node]
    while stack:
        n = stack.pop()
        n_type = getattr(n, "type", "")
        # Field declaration: `Type field;` or `Type field = value;`
        if n_type in ("field_declaration", "local_declaration_statement"):
            for child in (getattr(n, "children", []) or []):
                if getattr(child, "type", "") == "variable_declaration":
                    # variable_declaration has type child + variable_declarator children.
                    type_child = None
                    declarator = None
                    for gc in (getattr(child, "children", []) or []):
                        gc_type = getattr(gc, "type", "")
                        if gc_type in ("identifier", "predefined_type", "qualified_name", "generic_name", "nullable_type", "array_type") and type_child is None:
                            type_child = gc
                        elif gc_type == "variable_declarator":
                            declarator = gc
                    if type_child is not None and declarator is not None:
                        for dc in (getattr(declarator, "children", []) or []):
                            if getattr(dc, "type", "") == "identifier":
                                var_name = source_bytes[dc.start_byte:dc.end_byte].decode("utf-8", errors="replace")
                                if var_name == name:
                                    return _extract_simple_csharp_type_name(type_child, source_bytes)
        elif n_type == "parameter":
            # C# parameter: `Type name` — type child + identifier.
            type_child = None
            name_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct in ("identifier", "predefined_type", "qualified_name", "generic_name", "nullable_type", "array_type") and type_child is None:
                    type_child = child
                elif ct == "identifier" and type_child is not None:
                    name_child = child
            if type_child is not None and name_child is not None:
                param_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if param_name == name:
                    return _extract_simple_csharp_type_name(type_child, source_bytes)
        # Don't recurse into nested method / class bodies.
        if n_type in ("method_declaration", "constructor_declaration", "class_declaration",
                      "struct_declaration", "interface_declaration", "record_declaration") and n is not scope_node:
            continue
        stack.extend(reversed(getattr(n, "children", []) or []))
    return None


def _resolve_csharp_identifier_type(name: str, ref_node, source_bytes: bytes) -> str | None:
    cur = getattr(ref_node, "parent", None)
    while cur is not None:
        cur_type = getattr(cur, "type", "")
        if cur_type in ("method_declaration", "constructor_declaration", "class_declaration",
                        "struct_declaration", "interface_declaration", "record_declaration"):
            resolved = _search_csharp_declarations_in_scope(cur, name, source_bytes)
            if resolved is not None:
                return resolved
            if cur_type in ("class_declaration", "struct_declaration", "interface_declaration", "record_declaration"):
                break
        cur = getattr(cur, "parent", None)
    if name and name[:1].isupper():
        return name
    return None


def _resolve_csharp_receiver_type(invocation_node, source_bytes: bytes) -> str | None:
    """Resolve the simple type name of a C# invocation_expression's receiver.

    C# AST shape: `invocation_expression` with first child being the callee
    (`member_access_expression` for `receiver.Method()` or `identifier` for
    bare `Method()`).
    """
    if invocation_node is None or getattr(invocation_node, "type", "") != "invocation_expression":
        return None
    children = list(getattr(invocation_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    if callee_type == "identifier":
        # Bare call → enclosing class.
        return _find_enclosing_csharp_class_name(invocation_node, source_bytes)
    if callee_type == "member_access_expression":
        # member_access_expression has receiver + identifier (method name).
        ma_children = list(getattr(callee, "children", []) or [])
        if not ma_children:
            return None
        receiver = ma_children[0]
        receiver_type = getattr(receiver, "type", "")
        if receiver_type == "identifier":
            text = source_bytes[receiver.start_byte:receiver.end_byte].decode("utf-8", errors="replace")
            if text == "this":
                return _find_enclosing_csharp_class_name(invocation_node, source_bytes)
            if text == "base":
                return None  # defer inheritance walk
            return _resolve_csharp_identifier_type(text, invocation_node, source_bytes)
    return None


def _resolve_csharp_call_target(
    invocation_node, source_bytes: bytes, symbol_lookup: dict[str, str]
) -> str | None:
    if invocation_node is None or getattr(invocation_node, "type", "") != "invocation_expression":
        return None
    method_name: str | None = None
    children = list(getattr(invocation_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    if callee_type == "identifier":
        method_name = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace")
    elif callee_type == "member_access_expression":
        ma_children = list(getattr(callee, "children", []) or [])
        # Last identifier in member_access_expression is the method name.
        for child in reversed(ma_children):
            if getattr(child, "type", "") == "identifier":
                method_name = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
                break
    if not method_name:
        return None
    receiver_type = _resolve_csharp_receiver_type(invocation_node, source_bytes)
    if receiver_type is None:
        return None
    qualified = f"{receiver_type}.{method_name}"
    if qualified in symbol_lookup:
        return symbol_lookup[qualified]
    return f"external::{receiver_type}.{method_name}"


# =============================================================================
# Go receiver-type resolution (wave 1319a).
# =============================================================================


def _find_enclosing_go_method_receiver_type(node, source_bytes: bytes) -> str | None:
    """Walk up to enclosing method_declaration; return the receiver's type.

    Go method shape: `func (h Helper) Method() {...}` — the first parameter_list
    after `func` is the receiver. We extract its type_identifier.
    """
    cur = getattr(node, "parent", None)
    while cur is not None:
        if getattr(cur, "type", "") == "method_declaration":
            children = list(getattr(cur, "children", []) or [])
            # First parameter_list is the receiver (between func and name).
            for child in children:
                if getattr(child, "type", "") == "parameter_list":
                    pl_children = list(getattr(child, "children", []) or [])
                    for pl_child in pl_children:
                        if getattr(pl_child, "type", "") == "parameter_declaration":
                            for pd_child in (getattr(pl_child, "children", []) or []):
                                if getattr(pd_child, "type", "") in ("type_identifier", "pointer_type"):
                                    # Handle pointer types: `*Helper` wraps type_identifier.
                                    if getattr(pd_child, "type", "") == "pointer_type":
                                        for pc in (getattr(pd_child, "children", []) or []):
                                            if getattr(pc, "type", "") == "type_identifier":
                                                return source_bytes[pc.start_byte:pc.end_byte].decode("utf-8", errors="replace")
                                    else:
                                        return source_bytes[pd_child.start_byte:pd_child.end_byte].decode("utf-8", errors="replace")
                    return None  # parameter_list found but no type
            return None
        cur = getattr(cur, "parent", None)
    return None


def _search_go_declarations_in_scope(scope_node, name: str, source_bytes: bytes) -> str | None:
    """Search Go scope for `var name Type` declarations or function parameters."""
    stack = [scope_node]
    while stack:
        n = stack.pop()
        n_type = getattr(n, "type", "")
        if n_type == "var_spec":
            # var_spec: identifier <name> + type_identifier <Type>
            name_child = None
            type_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct == "identifier" and name_child is None:
                    name_child = child
                elif ct in ("type_identifier", "pointer_type"):
                    type_child = child
            if name_child is not None and type_child is not None:
                var_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if var_name == name:
                    t_type = getattr(type_child, "type", "")
                    if t_type == "pointer_type":
                        for c in (getattr(type_child, "children", []) or []):
                            if getattr(c, "type", "") == "type_identifier":
                                return source_bytes[c.start_byte:c.end_byte].decode("utf-8", errors="replace")
                    else:
                        return source_bytes[type_child.start_byte:type_child.end_byte].decode("utf-8", errors="replace")
        elif n_type == "parameter_declaration":
            # parameter_declaration: identifier <name> + type_identifier <Type>
            name_child = None
            type_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct == "identifier" and name_child is None:
                    name_child = child
                elif ct in ("type_identifier", "pointer_type"):
                    type_child = child
            if name_child is not None and type_child is not None:
                param_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if param_name == name:
                    t_type = getattr(type_child, "type", "")
                    if t_type == "pointer_type":
                        for c in (getattr(type_child, "children", []) or []):
                            if getattr(c, "type", "") == "type_identifier":
                                return source_bytes[c.start_byte:c.end_byte].decode("utf-8", errors="replace")
                    else:
                        return source_bytes[type_child.start_byte:type_child.end_byte].decode("utf-8", errors="replace")
        # Don't descend into nested function bodies.
        if n_type in ("method_declaration", "function_declaration") and n is not scope_node:
            continue
        stack.extend(reversed(getattr(n, "children", []) or []))
    return None


def _resolve_go_identifier_type(name: str, ref_node, source_bytes: bytes) -> str | None:
    """Resolve a Go identifier to its declared simple type name."""
    cur = getattr(ref_node, "parent", None)
    while cur is not None:
        cur_type = getattr(cur, "type", "")
        if cur_type in ("method_declaration", "function_declaration"):
            resolved = _search_go_declarations_in_scope(cur, name, source_bytes)
            if resolved is not None:
                return resolved
            break
        cur = getattr(cur, "parent", None)
    if name and name[:1].isupper():
        # Likely a static-style call to a type (TypeName.Method()).
        return name
    return None


def _resolve_go_receiver_type(call_node, source_bytes: bytes) -> str | None:
    """Resolve Go call_expression receiver type.

    Shape: call_expression → selector_expression (`h.Method`) or identifier (bare).
    """
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    if callee_type == "identifier":
        # Bare call → enclosing method's receiver type (Go has no explicit "this").
        return _find_enclosing_go_method_receiver_type(call_node, source_bytes)
    if callee_type == "selector_expression":
        # First child is the receiver identifier.
        nav_children = list(getattr(callee, "children", []) or [])
        if not nav_children:
            return None
        receiver = nav_children[0]
        receiver_type = getattr(receiver, "type", "")
        if receiver_type == "identifier":
            text = source_bytes[receiver.start_byte:receiver.end_byte].decode("utf-8", errors="replace")
            return _resolve_go_identifier_type(text, call_node, source_bytes)
    return None


def _resolve_go_call_target(call_node, source_bytes: bytes, symbol_lookup: dict[str, str]) -> str | None:
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    method_name: str | None = None
    if callee_type == "identifier":
        method_name = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace")
    elif callee_type == "selector_expression":
        # The method name is the field_identifier child.
        for child in (getattr(callee, "children", []) or []):
            if getattr(child, "type", "") == "field_identifier":
                method_name = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
                break
    if not method_name:
        return None
    receiver_type = _resolve_go_receiver_type(call_node, source_bytes)
    if receiver_type is None:
        return None
    qualified = f"{receiver_type}.{method_name}"
    if qualified in symbol_lookup:
        return symbol_lookup[qualified]
    return f"external::{receiver_type}.{method_name}"


# =============================================================================
# Rust receiver-type resolution (wave 1319a).
# =============================================================================


def _find_enclosing_rust_impl_type(node, source_bytes: bytes) -> str | None:
    """Walk up to enclosing impl_item; return its target type."""
    cur = getattr(node, "parent", None)
    while cur is not None:
        if getattr(cur, "type", "") == "impl_item":
            for child in (getattr(cur, "children", []) or []):
                if getattr(child, "type", "") == "type_identifier":
                    return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            return None
        cur = getattr(cur, "parent", None)
    return None


def _search_rust_declarations_in_scope(scope_node, name: str, source_bytes: bytes) -> str | None:
    """Search Rust scope for `let name: Type = ...` or function parameter."""
    stack = [scope_node]
    while stack:
        n = stack.pop()
        n_type = getattr(n, "type", "")
        if n_type == "let_declaration":
            # let_declaration: let identifier <name> : type_identifier <Type> = ...
            name_child = None
            type_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct == "identifier" and name_child is None:
                    name_child = child
                elif ct == "type_identifier":
                    type_child = child
            if name_child is not None and type_child is not None:
                var_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if var_name == name:
                    return source_bytes[type_child.start_byte:type_child.end_byte].decode("utf-8", errors="replace")
        elif n_type == "parameter":
            # parameter: identifier <name> : type_identifier <Type>
            name_child = None
            type_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct == "identifier" and name_child is None:
                    name_child = child
                elif ct == "type_identifier":
                    type_child = child
            if name_child is not None and type_child is not None:
                param_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if param_name == name:
                    return source_bytes[type_child.start_byte:type_child.end_byte].decode("utf-8", errors="replace")
        # Don't descend into nested function bodies.
        if n_type == "function_item" and n is not scope_node:
            continue
        stack.extend(reversed(getattr(n, "children", []) or []))
    return None


def _resolve_rust_identifier_type(name: str, ref_node, source_bytes: bytes) -> str | None:
    cur = getattr(ref_node, "parent", None)
    while cur is not None:
        cur_type = getattr(cur, "type", "")
        if cur_type == "function_item":
            resolved = _search_rust_declarations_in_scope(cur, name, source_bytes)
            if resolved is not None:
                return resolved
            break
        cur = getattr(cur, "parent", None)
    if name and name[:1].isupper():
        return name
    return None


def _resolve_rust_receiver_type(call_node, source_bytes: bytes) -> str | None:
    """Resolve Rust call_expression receiver type.

    Shape: call_expression → field_expression (`h.method`) or identifier (bare).
    """
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    if callee_type == "identifier":
        return _find_enclosing_rust_impl_type(call_node, source_bytes)
    if callee_type == "field_expression":
        nav_children = list(getattr(callee, "children", []) or [])
        if not nav_children:
            return None
        receiver = nav_children[0]
        receiver_type = getattr(receiver, "type", "")
        if receiver_type == "self":
            return _find_enclosing_rust_impl_type(call_node, source_bytes)
        if receiver_type == "identifier":
            text = source_bytes[receiver.start_byte:receiver.end_byte].decode("utf-8", errors="replace")
            if text == "self":
                return _find_enclosing_rust_impl_type(call_node, source_bytes)
            return _resolve_rust_identifier_type(text, call_node, source_bytes)
    return None


def _resolve_rust_call_target(call_node, source_bytes: bytes, symbol_lookup: dict[str, str]) -> str | None:
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    method_name: str | None = None
    if callee_type == "identifier":
        method_name = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace")
    elif callee_type == "field_expression":
        for child in (getattr(callee, "children", []) or []):
            if getattr(child, "type", "") == "field_identifier":
                method_name = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
                break
    if not method_name:
        return None
    receiver_type = _resolve_rust_receiver_type(call_node, source_bytes)
    if receiver_type is None:
        return None
    qualified = f"{receiver_type}.{method_name}"
    if qualified in symbol_lookup:
        return symbol_lookup[qualified]
    return f"external::{receiver_type}.{method_name}"


# =============================================================================
# Scala receiver-type resolution (wave 1319a).
# =============================================================================


def _find_enclosing_scala_class_name(node, source_bytes: bytes) -> str | None:
    cur = getattr(node, "parent", None)
    while cur is not None:
        if getattr(cur, "type", "") in ("class_definition", "object_definition", "trait_definition"):
            for child in (getattr(cur, "children", []) or []):
                if getattr(child, "type", "") == "identifier":
                    return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            return None
        cur = getattr(cur, "parent", None)
    return None


def _search_scala_declarations_in_scope(scope_node, name: str, source_bytes: bytes) -> str | None:
    """Search Scala scope for `val name: Type = ...` or function parameter."""
    stack = [scope_node]
    while stack:
        n = stack.pop()
        n_type = getattr(n, "type", "")
        if n_type in ("val_definition", "var_definition"):
            name_child = None
            type_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct == "identifier" and name_child is None:
                    name_child = child
                elif ct == "type_identifier":
                    type_child = child
            if name_child is not None and type_child is not None:
                var_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if var_name == name:
                    return source_bytes[type_child.start_byte:type_child.end_byte].decode("utf-8", errors="replace")
        elif n_type == "parameter":
            name_child = None
            type_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct == "identifier" and name_child is None:
                    name_child = child
                elif ct == "type_identifier":
                    type_child = child
            if name_child is not None and type_child is not None:
                param_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if param_name == name:
                    return source_bytes[type_child.start_byte:type_child.end_byte].decode("utf-8", errors="replace")
        # Don't descend into nested function/class bodies.
        if n_type in ("function_definition", "class_definition", "object_definition", "trait_definition") and n is not scope_node:
            continue
        stack.extend(reversed(getattr(n, "children", []) or []))
    return None


def _resolve_scala_identifier_type(name: str, ref_node, source_bytes: bytes) -> str | None:
    cur = getattr(ref_node, "parent", None)
    while cur is not None:
        cur_type = getattr(cur, "type", "")
        if cur_type in ("function_definition", "class_definition", "object_definition", "trait_definition"):
            resolved = _search_scala_declarations_in_scope(cur, name, source_bytes)
            if resolved is not None:
                return resolved
            if cur_type in ("class_definition", "object_definition", "trait_definition"):
                break
        cur = getattr(cur, "parent", None)
    if name and name[:1].isupper():
        return name
    return None


def _resolve_scala_receiver_type(call_node, source_bytes: bytes) -> str | None:
    """Resolve Scala call_expression receiver type.

    Shape: call_expression → field_expression (`h.process`) or identifier (bare).
    """
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    if callee_type == "identifier":
        return _find_enclosing_scala_class_name(call_node, source_bytes)
    if callee_type == "field_expression":
        nav_children = list(getattr(callee, "children", []) or [])
        if not nav_children:
            return None
        receiver = nav_children[0]
        receiver_type = getattr(receiver, "type", "")
        if receiver_type == "identifier":
            text = source_bytes[receiver.start_byte:receiver.end_byte].decode("utf-8", errors="replace")
            if text == "this":
                return _find_enclosing_scala_class_name(call_node, source_bytes)
            if text == "super":
                return None
            return _resolve_scala_identifier_type(text, call_node, source_bytes)
    return None


def _resolve_scala_call_target(call_node, source_bytes: bytes, symbol_lookup: dict[str, str]) -> str | None:
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    method_name: str | None = None
    if callee_type == "identifier":
        method_name = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace")
    elif callee_type == "field_expression":
        # Method name is the LAST identifier child (after the `.`).
        identifiers = [c for c in (getattr(callee, "children", []) or []) if getattr(c, "type", "") == "identifier"]
        if len(identifiers) >= 2:
            method_name = source_bytes[identifiers[-1].start_byte:identifiers[-1].end_byte].decode("utf-8", errors="replace")
    if not method_name:
        return None
    receiver_type = _resolve_scala_receiver_type(call_node, source_bytes)
    if receiver_type is None:
        return None
    qualified = f"{receiver_type}.{method_name}"
    if qualified in symbol_lookup:
        return symbol_lookup[qualified]
    return f"external::{receiver_type}.{method_name}"


# =============================================================================
# Swift receiver-type resolution (wave 1319g).
# =============================================================================


def _extract_simple_swift_type_name(type_node, source_bytes: bytes) -> str | None:
    """Extract simple type name from a Swift type AST node.

    Swift grammar shapes (verified 2026-06-01):
    - `user_type` wraps `type_identifier`.
    - `type_annotation` (`: Foo`) wraps `user_type` after the `:` token.
    - `optional_type` wraps `user_type` for `Foo?`.
    """
    n_type = getattr(type_node, "type", "")
    if n_type == "type_annotation":
        for child in (getattr(type_node, "children", []) or []):
            if getattr(child, "type", "") in ("user_type", "type_identifier", "optional_type"):
                return _extract_simple_swift_type_name(child, source_bytes)
        return None
    if n_type == "user_type":
        for child in (getattr(type_node, "children", []) or []):
            if getattr(child, "type", "") == "type_identifier":
                return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
        return None
    if n_type == "type_identifier":
        return source_bytes[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace")
    if n_type == "optional_type":
        for child in (getattr(type_node, "children", []) or []):
            if getattr(child, "type", "") in ("user_type", "type_identifier"):
                return _extract_simple_swift_type_name(child, source_bytes)
        return None
    return None


def _find_enclosing_swift_class_name(node, source_bytes: bytes) -> str | None:
    """Walk up to Swift class/struct/actor/enum/protocol declaration's type_identifier."""
    cur = getattr(node, "parent", None)
    while cur is not None:
        if getattr(cur, "type", "") in (
            "class_declaration", "struct_declaration", "actor_declaration",
            "enum_declaration", "protocol_declaration",
        ):
            for child in (getattr(cur, "children", []) or []):
                if getattr(child, "type", "") == "type_identifier":
                    return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            return None
        cur = getattr(cur, "parent", None)
    return None


def _search_swift_declarations_in_scope(scope_node, name: str, source_bytes: bytes) -> str | None:
    """Search Swift scope for `let foo: Foo = ...` / `var foo: Foo` / `func bar(foo: Foo)`."""
    stack = [scope_node]
    while stack:
        n = stack.pop()
        n_type = getattr(n, "type", "")
        if n_type == "property_declaration":
            # Swift: `let oos: ObjectOutputStream = ...`
            # children: value_binding_pattern + pattern (simple_identifier) + type_annotation + ...
            name_child = None
            type_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct == "pattern":
                    for gc in (getattr(child, "children", []) or []):
                        if getattr(gc, "type", "") == "simple_identifier":
                            name_child = gc
                            break
                elif ct == "type_annotation" and type_child is None:
                    type_child = child
            if name_child is not None and type_child is not None:
                var_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if var_name == name:
                    return _extract_simple_swift_type_name(type_child, source_bytes)
        elif n_type == "parameter":
            # Swift: `func bar(oos: ObjectOutputStream)` — simple_identifier + : + user_type
            name_child = None
            type_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct == "simple_identifier" and name_child is None:
                    name_child = child
                elif ct in ("user_type", "type_identifier", "optional_type"):
                    type_child = child
            if name_child is not None and type_child is not None:
                param_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if param_name == name:
                    return _extract_simple_swift_type_name(type_child, source_bytes)
        # Don't descend into nested function/class bodies.
        if n_type in (
            "function_declaration", "class_declaration", "struct_declaration",
            "actor_declaration", "enum_declaration", "protocol_declaration",
        ) and n is not scope_node:
            continue
        stack.extend(reversed(getattr(n, "children", []) or []))
    return None


def _resolve_swift_identifier_type(name: str, ref_node, source_bytes: bytes) -> str | None:
    cur = getattr(ref_node, "parent", None)
    while cur is not None:
        cur_type = getattr(cur, "type", "")
        if cur_type in (
            "function_declaration", "class_declaration", "struct_declaration",
            "actor_declaration", "enum_declaration", "protocol_declaration",
        ):
            resolved = _search_swift_declarations_in_scope(cur, name, source_bytes)
            if resolved is not None:
                return resolved
            if cur_type in (
                "class_declaration", "struct_declaration", "actor_declaration",
                "enum_declaration", "protocol_declaration",
            ):
                break
        cur = getattr(cur, "parent", None)
    if name and name[:1].isupper():
        return name
    return None


def _resolve_swift_receiver_type(call_node, source_bytes: bytes) -> str | None:
    """Resolve Swift call_expression receiver type.

    Swift grammar shapes:
    - Bare method call `bar()`: call_expression has simple_identifier + call_suffix.
    - Constructor call `Foo()`: same AST shape as bare call (Swift has no `new`
      keyword). Discriminated by case — PascalCase identifier → constructor,
      lowerCamelCase → method. Constructor calls return None so the standard
      attribution handles them (target the type's init).
    - Member call `foo.bar()`: call_expression has navigation_expression
      (children: simple_identifier "foo" + navigation_suffix (.bar)) + call_suffix.
    """
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    if callee_type == "simple_identifier":
        text = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace")
        if text and text[:1].isupper():
            # Constructor call (`Foo()`) — defer to standard attribution.
            return None
        return _find_enclosing_swift_class_name(call_node, source_bytes)
    if callee_type == "navigation_expression":
        nav_children = list(getattr(callee, "children", []) or [])
        if not nav_children:
            return None
        receiver = nav_children[0]
        receiver_type = getattr(receiver, "type", "")
        if receiver_type == "simple_identifier":
            text = source_bytes[receiver.start_byte:receiver.end_byte].decode("utf-8", errors="replace")
            if text == "self":
                return _find_enclosing_swift_class_name(call_node, source_bytes)
            if text == "super":
                return None
            return _resolve_swift_identifier_type(text, call_node, source_bytes)
    return None


def _resolve_swift_call_target(call_node, source_bytes: bytes, symbol_lookup: dict[str, str]) -> str | None:
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "")
    method_name: str | None = None
    if callee_type == "simple_identifier":
        method_name = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace")
    elif callee_type == "navigation_expression":
        # Method name is in the navigation_suffix's simple_identifier child.
        nav_children = list(getattr(callee, "children", []) or [])
        for nc in nav_children:
            if getattr(nc, "type", "") == "navigation_suffix":
                for sc in (getattr(nc, "children", []) or []):
                    if getattr(sc, "type", "") == "simple_identifier":
                        method_name = source_bytes[sc.start_byte:sc.end_byte].decode("utf-8", errors="replace")
                        break
                break
    if not method_name:
        return None
    receiver_type = _resolve_swift_receiver_type(call_node, source_bytes)
    if receiver_type is None:
        return None
    qualified = f"{receiver_type}.{method_name}"
    if qualified in symbol_lookup:
        return symbol_lookup[qualified]
    return f"external::{receiver_type}.{method_name}"


def _resolve_java_call_target(
    invocation_node, source_bytes: bytes, symbol_lookup: dict[str, str]
) -> str | None:
    """Resolve a Java method_invocation to a graph node id.

    Deterministic per-call-site dispatch (wave 13129 council action item:
    red-team — no double-emission):

    - Receiver type resolves to a project class (qname found in symbol_lookup)
      → return the project node id.
    - Receiver type resolves to a non-project type → return the qualified
      external node id (``external::<ResolvedType>.<method>``).
    - Receiver type is uncertain (None) → return None; caller falls through
      to existing simple-name attribution.

    Args:
        invocation_node: Java AST ``method_invocation`` node.
        source_bytes: Source file bytes for text extraction.
        symbol_lookup: Mapping of qname → node_id for project symbols.
    """
    if invocation_node is None or getattr(invocation_node, "type", "") != "method_invocation":
        return None
    method_name_node = invocation_node.child_by_field_name("name")
    if method_name_node is None:
        return None
    method_name = source_bytes[method_name_node.start_byte:method_name_node.end_byte].decode("utf-8", errors="replace")
    if not method_name:
        return None
    receiver_type = _resolve_java_receiver_type(invocation_node, source_bytes)
    if receiver_type is None:
        return None  # Uncertain — fall through to existing attribution.
    # Project lookup: try the qualified name.
    qualified = f"{receiver_type}.{method_name}"
    if qualified in symbol_lookup:
        return symbol_lookup[qualified]
    # External attribution: qualified external node id.
    return f"external::{receiver_type}.{method_name}"


def _ts_extract_java_annotations(node, source_bytes: bytes) -> list[str]:
    """Extract annotation names from a Java method/class declaration (wave 130rj).

    Walks the ``modifiers`` child for ``marker_annotation`` and ``annotation``
    nodes, reads the ``name`` field of each, and returns the names verbatim
    (e.g. ``["Advice.OnMethodEnter", "Around"]``). Names may be qualified
    (e.g. ``"org.aspectj.lang.annotation.Around"``); downstream consumers match
    by trailing segment.
    """
    annotations: list[str] = []
    try:
        children = list(getattr(node, "named_children", []) or [])
    except Exception:
        return annotations
    for child in children:
        ctype = getattr(child, "type", "") or ""
        if ctype != "modifiers":
            continue
        try:
            mod_children = list(getattr(child, "named_children", []) or [])
        except Exception:
            continue
        for ann in mod_children:
            ann_type = getattr(ann, "type", "") or ""
            if ann_type not in ("marker_annotation", "annotation"):
                continue
            try:
                name_node = ann.child_by_field_name("name")
            except Exception:
                name_node = None
            if name_node is None:
                continue
            name = _ts_node_text(name_node, source_bytes).strip()
            if name and name not in annotations:
                annotations.append(name)
    return annotations


def _ts_extract_csharp_attributes(node, source_bytes: bytes) -> list[str]:
    """Extract attribute names from a C# method/class declaration (wave 130rj — 130tc).

    C# uses `[Attribute]` syntax that lives in ``attribute_list`` children of
    ``method_declaration`` / ``class_declaration`` (sibling to ``modifiers``
    rather than nested inside it as in Java). Each ``attribute_list`` contains
    one or more ``attribute`` nodes; each ``attribute`` exposes its name via
    the ``name`` field. Returns the names verbatim (e.g.
    ``["Around", "OnMethodBoundaryAspect"]``).
    """
    attributes: list[str] = []
    try:
        children = list(getattr(node, "named_children", []) or [])
    except Exception:
        return attributes
    for child in children:
        ctype = getattr(child, "type", "") or ""
        if ctype != "attribute_list":
            continue
        try:
            list_children = list(getattr(child, "named_children", []) or [])
        except Exception:
            continue
        for attr in list_children:
            attr_type = getattr(attr, "type", "") or ""
            if attr_type != "attribute":
                continue
            try:
                name_node = attr.child_by_field_name("name")
            except Exception:
                name_node = None
            if name_node is None:
                continue
            name = _ts_node_text(name_node, source_bytes).strip()
            if name and name not in attributes:
                attributes.append(name)
    return attributes


def _ts_extract_callee_positional(node, source_bytes: bytes) -> str | None:
    """Fallback for grammars whose call_expression has no callee field name.

    Walks the call node's named_children, skips argument/suffix-like nodes,
    and recursively extracts the rightmost identifier from the first
    remaining child. Used by ``_ts_relation_candidates`` when the field-name
    lookup returns empty (Swift, Kotlin) — safe because the caller has
    already confirmed the node is a call (per ``profile.call_node_types``).
    """
    for child in node.named_children:
        if child.type in _TS_ARGS_NODE_TYPES:
            continue
        candidate = _ts_extract_callee_recursive(child, source_bytes)
        if candidate:
            return candidate
    return None


def _ts_relation_candidates(
    node,
    source_bytes: bytes,
    relation: str,
    mode: str,
    profile: _TsLanguageProfile | None = None,
) -> list[str]:
    candidates = []
    for field_name in _ts_relation_field_names(relation, mode):
        try:
            child = node.child_by_field_name(field_name)
        except Exception:
            child = None
        if child is None:
            continue
        candidate = _ts_clean_name(_ts_node_text(child, source_bytes))
        if candidate and not _ts_candidate_rejected(candidate) and candidate not in candidates:
            candidates.append(candidate)
    if candidates:
        return candidates
    # For "call" relation in code mode, field-name lookup may miss for
    # grammars whose call_expression exposes the callee positionally rather
    # than via a named field (Swift, Kotlin). Try the positional fallback
    # (wave 130ol): walk named_children, skip argument-list nodes, and
    # extract the rightmost identifier from the first non-suffix child.
    # Safe because the caller (walk_calls) has already confirmed the node
    # is a call via the explicit per-language ``profile.call_node_types``.
    if relation == "call" and mode == "code":
        positional = _ts_extract_callee_positional(node, source_bytes)
        if positional and not _ts_candidate_rejected(positional):
            profile_stop = profile.stop_terms if profile is not None else frozenset()
            if positional not in _STOP_TERMS and positional not in profile_stop:
                return [positional]
        return []
    text = _ts_node_text(node, source_bytes)
    if not text:
        return []
    # Fall back to a light parse of the AST span, keeping the grammar boundary.
    # Preserved for non-call relations (e.g. import) where the multi-token
    # fallback is still useful and the noise risk is lower.
    raw_candidates = re.findall(r"[A-Za-z_][A-Za-z0-9_.$:#/\-]*", text)
    profile_stop = profile.stop_terms if profile is not None else frozenset()
    return [
        candidate for candidate in raw_candidates
        if candidate not in _STOP_TERMS
        and candidate not in profile_stop
        and not _ts_candidate_rejected(candidate)
    ]


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
        # Lazy-cached `.gitattributes` `linguist-generated=true` patterns (wave 130rj).
        # Populated on first call to record_file() so we only parse the file once
        # per session even when no generated-code classification is required.
        self._gitattrs_patterns: frozenset[str] | None = None
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
            # Pre-classify the file for generated-code tagging (wave 130rj).
            # Cache gitattributes patterns lazily on first classification call.
            if self._gitattrs_patterns is None:
                self._gitattrs_patterns = _load_gitattributes_generated_paths(self.root)
            source_bytes = source_text.encode("utf-8", errors="replace")
            is_generated = _classify_generated(rel, source_bytes, self._gitattrs_patterns)
            artifact = self._extract_code_artifact(rel, source_text)
            if is_generated:
                # Tag every node from a generated-classified file with `generated: True`
                # so downstream consumers can filter/aggregate without re-classifying.
                artifact["generated"] = True
                for node in artifact.get("nodes", []):
                    if isinstance(node, dict):
                        node["generated"] = True
            self.pending_code[rel] = {
                "source_hash": source_hash,
                "artifact": artifact,
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

        # Wave 13129 (1316l + 13190): class/module merge — when a file
        # `Foo.<ext>` contains a top-level type declaration named `Foo`
        # (basename match), the file node and the class node merge into
        # a single node at the file id. The class id (`<file>::<basename>`)
        # is NOT registered; edges that would target it route to the file id
        # instead. Operators querying by either form get the unified node.
        #
        # Per-language merge-eligible kinds (13190/13196/1319i/1319k multi-language extension):
        _CLASS_MODULE_MERGE_KINDS_BY_LANG: dict[str, frozenset[str]] = {
            "swift":      frozenset({"class", "struct", "actor", "enum", "protocol"}),
            "java":       frozenset({"class", "interface", "enum", "record", "annotation_type"}),
            "kotlin":     frozenset({"class", "interface", "object", "enum_class"}),
            "csharp":     frozenset({"class", "interface", "struct", "record", "enum"}),
            # Wave 13196: JS/TS/Scala/PHP
            "javascript": frozenset({"class"}),
            "typescript": frozenset({"class", "interface", "type", "enum"}),
            "scala":      frozenset({"class", "object", "trait", "enum"}),
            "php":        frozenset({"class", "interface", "trait"}),
            # Wave 1319i/1319k: Rust/Ruby — snake_case file convention.
            # Note: indexer's _ts_kind_for_definition normalizes Rust's
            # `struct_item`/`enum_item`/`trait_item` ALL to `"class"` kind;
            # similarly Ruby's `class` registers as `"class"` and `module`
            # registers as `"module"`. Merge gate matches against the
            # normalized kind values.
            "rust":       frozenset({"class"}),
            "ruby":       frozenset({"class", "module"}),
        }
        # Multi-extension languages (JS has 4, TS has 2).
        _CLASS_MODULE_MERGE_EXTS_BY_LANG: dict[str, tuple[str, ...]] = {
            "swift":      (".swift",),
            "java":       (".java",),
            "kotlin":     (".kt",),
            "csharp":     (".cs",),
            "javascript": (".js", ".jsx", ".mjs", ".cjs"),
            "typescript": (".ts", ".tsx"),
            "scala":      (".scala",),
            "php":        (".php",),
            "rust":       (".rs",),
            "ruby":       (".rb",),
        }
        # Wave 1319i/1319k: languages with snake_case file convention need
        # snake-to-PascalCase basename conversion. `foo_bar.rs` looks for
        # `struct FooBar`. Detection tries BOTH the snake-derived name AND
        # the literal basename (some Rust crates use `Foo.rs` directly).
        _SNAKE_TO_PASCAL_LANGS = frozenset({"rust", "ruby"})

        def _snake_to_pascal(name: str) -> str:
            if not name:
                return ""
            parts = name.split("_")
            return "".join(p[:1].upper() + p[1:] for p in parts if p)

        _merge_kinds = _CLASS_MODULE_MERGE_KINDS_BY_LANG.get(lang_key, frozenset())
        _merge_exts = _CLASS_MODULE_MERGE_EXTS_BY_LANG.get(lang_key, ())
        _basename_raw = ""
        for _ext in _merge_exts:
            if rel_path.endswith(_ext):
                _basename_raw = rel_path.rsplit("/", 1)[-1].rsplit(_ext, 1)[0]
                break
        # Build the set of basename candidates the merge gate matches against.
        # For exact-match languages (Swift/Java/Kotlin/C#/JS/TS/Scala/PHP),
        # only the literal basename matches. For snake-to-Pascal languages,
        # both the literal basename and its PascalCase conversion match.
        _file_basename_candidates: frozenset[str] = (
            frozenset({_basename_raw, _snake_to_pascal(_basename_raw)})
            if lang_key in _SNAKE_TO_PASCAL_LANGS
            else frozenset({_basename_raw}) if _basename_raw
            else frozenset()
        )

        def register_symbol(qname: str, kind: str, node, parent_symbol: str | None) -> str:
            # Wave 13129 (1316l/13190/1319i/1319k): merge top-level type whose
            # name matches one of the file basename candidates into the module
            # node. Candidates are the literal basename plus (for languages
            # with snake_case file convention like Rust/Ruby) the PascalCase
            # conversion of the basename.
            if (
                _file_basename_candidates
                and kind in _merge_kinds
                and qname in _file_basename_candidates
            ):
                # Update module node identity to take on the class.
                module_node = node_map.get(module_id)
                if module_node is not None:
                    module_node["label"] = qname
                    module_node["kind"] = kind
                    module_node["collapsed_pair"] = True
                # Register the basename under simple_names so cross-file
                # resolution can rebind `external::Foo` to this module_id.
                simple_names.setdefault(qname, []).append(module_id)
                # Track as defined for symbol_lookup population (uses the
                # qname → module_id mapping).
                if module_id not in defined_symbols:
                    defined_symbols.append(module_id)
                return module_id
            node_id = f"{rel_path}::{qname}"
            label = qname.rsplit(".", 1)[-1]
            add_node(node_id, label, kind, self._source_location(source_text, node.start_point[0] + 1))
            # Wave 130rj — Aceiss §2.3: capture annotation tails on Java and
            # attribute tails on C# so code_callhierarchy can emit
            # `caller_pattern: "advice"` when incoming is empty for an AOP-
            # annotated/attributed method. Java annotations live inside the
            # `modifiers` child; C# attributes live in sibling `attribute_list`
            # nodes (130tc).
            if lang_key == "java":
                annotations = _ts_extract_java_annotations(node, source_bytes)
                if annotations:
                    node_map[node_id]["annotations"] = annotations
            elif lang_key == "csharp":
                attributes = _ts_extract_csharp_attributes(node, source_bytes)
                if attributes:
                    # Surface as `annotations` for downstream parity with Java.
                    node_map[node_id]["annotations"] = attributes
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
            if _ts_is_call_node(node_type, mode, profile):
                source_symbol = scope_symbols[-1] if scope_symbols else module_id
                # Wave 13129 (1312l + 13194): per-language receiver-type
                # resolution at edge construction time. For supported language
                # invocation nodes, try the receiver-type resolver first; on a
                # hit, it provides the deterministic per-call-site target
                # (project-qualified or external-qualified). On uncertain
                # receivers, fall through to the existing simple-name
                # attribution.
                java_resolved_target: str | None = None
                if lang_key == "java" and node_type == "method_invocation":
                    java_resolved_target = _resolve_java_call_target(
                        node, source_bytes, symbol_lookup
                    )
                elif lang_key == "kotlin" and node_type == "call_expression":
                    java_resolved_target = _resolve_kotlin_call_target(
                        node, source_bytes, symbol_lookup
                    )
                elif lang_key == "csharp" and node_type == "invocation_expression":
                    java_resolved_target = _resolve_csharp_call_target(
                        node, source_bytes, symbol_lookup
                    )
                # Wave 1319a: Go/Rust/Scala extensions.
                elif lang_key == "go" and node_type == "call_expression":
                    java_resolved_target = _resolve_go_call_target(
                        node, source_bytes, symbol_lookup
                    )
                elif lang_key == "rust" and node_type == "call_expression":
                    java_resolved_target = _resolve_rust_call_target(
                        node, source_bytes, symbol_lookup
                    )
                elif lang_key == "scala" and node_type == "call_expression":
                    java_resolved_target = _resolve_scala_call_target(
                        node, source_bytes, symbol_lookup
                    )
                # Wave 1319g: Swift extension.
                elif lang_key == "swift" and node_type == "call_expression":
                    java_resolved_target = _resolve_swift_call_target(
                        node, source_bytes, symbol_lookup
                    )
                if java_resolved_target is not None:
                    # Confidence "RECEIVER_RESOLVED" tells the cross-file
                    # resolution pass to leave this edge alone — the
                    # receiver-type resolution has already determined the
                    # correct target (project or external-qualified) and
                    # the simple-name fallback would mis-rewrite an
                    # external-qualified edge back to a project node.
                    add_edge(source_symbol, java_resolved_target, "calls", confidence="RECEIVER_RESOLVED")
                else:
                    for target in _ts_relation_candidates(node, source_bytes, "call", mode, profile):
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

        # Cross-file symbol resolution pass (wave 130ol — AC-1, AC-1a, AC-2).
        #
        # The per-file extractors build a local `symbol_lookup` from just THIS
        # file's defined symbols, so any call to a function defined in another
        # file resolves to `external::<name>` even when the target is a real
        # project-internal symbol. Here, after per-file artifacts are merged
        # into node_map/edge_map, we rewrite `external::<bare-name>` edge
        # targets to project-internal node ids when:
        #   (a) the simple name is unambiguous across all project nodes, AND
        #   (b) the name is not in the per-language builtin denylist (so
        #       `external::pathlib.Path`, `external::len`, `external::String`
        #       etc. stay external even if a project file happens to define a
        #       same-named symbol).
        # Dotted targets (`external::a.b.c`) are handled via a qualified-suffix
        # match against project node qualified names. The pass runs on the
        # FULL merged edge set every build (incremental and full) — cached
        # referrer artifacts may still carry `external::*` edges into newly-
        # defined cross-file symbols and the rewrite must catch them.
        #
        # Performance: pre-built indexes give O(edges + nodes); each edge is
        # an O(1) dict lookup. Negligible at typical graph scales (~100K edges).
        # Build per-(file, simple_name) dedupe map FIRST so we don't double-count
        # phantom inner-grammar duplicates (e.g. C++ function_declarator nested
        # inside function_definition both registered as `helper_process` — they're
        # the same logical symbol). Keep the entry with the shortest qualified
        # name (the outer/real definition); ambiguity then reflects only the
        # cross-file case the resolver actually cares about (wave 130ol).
        simple_name_index: dict[str, list[str]] = {}
        qualified_index: dict[str, list[str]] = {}
        per_file_simple: dict[tuple[str, str], str] = {}
        for node_id, node in node_map.items():
            if node_id.startswith("external::"):
                continue  # external endpoint nodes are not project candidates
            # Wave 13129 (1316l): merged Swift class/module nodes (collapsed_pair=True)
            # live at the file id and carry the class label. Include them in the
            # simple_name_index so cross-file external::Foo rewrites resolve to the
            # merged file node. Other module-level nodes (no class merge) are
            # excluded — they don't represent a queryable symbol.
            is_collapsed_pair = bool(node.get("collapsed_pair"))
            if "::" not in node_id and not is_collapsed_pair:
                continue
            if is_collapsed_pair:
                # Module-level merged node: file_part is the node_id itself,
                # qualified is the class label.
                file_part = node_id
                qualified = str(node.get("label") or "")
            else:
                file_part, qualified = node_id.split("::", 1)
            label = str(node.get("label") or "")
            simple = label or qualified.rsplit(".", 1)[-1]
            if not simple:
                continue
            key = (file_part, simple)
            existing = per_file_simple.get(key)
            if existing is None or len(node_id) < len(existing):
                per_file_simple[key] = node_id
        for (file_part, simple), node_id in per_file_simple.items():
            simple_name_index.setdefault(simple, []).append(node_id)
            # Wave 13129 (1316l): merged Swift class/module nodes have no "::";
            # their qualified is the class label (== simple), so skip the
            # qualified_index addition (which dedupes against simple anyway).
            if "::" in node_id:
                _, qualified = node_id.split("::", 1)
                if qualified and qualified != simple:
                    qualified_index.setdefault(qualified, []).append(node_id)
            # Also index a module-path-derived dotted form so per-file extractors
            # that emit dotted external targets (e.g. Python `from src.a import
            # foo` produces `external::src.a.foo`) can resolve to project nodes.
            # Strip the file extension and convert path separators to dots.
            dotted_module = re.sub(r"\.[A-Za-z0-9]+$", "", file_part).replace("/", ".")
            # Strip a leading "." from hidden directories so
            # ".wavefoundry/framework/scripts/..." becomes the actual Python
            # module path (e.g. `wave_lint_lib...`).
            dotted_module = dotted_module.lstrip(".")
            if dotted_module:
                dotted_full = f"{dotted_module}.{qualified}"
                qualified_index.setdefault(dotted_full, []).append(node_id)
                # Index every dotted-path suffix so cross-module imports that
                # strip leading directory segments still resolve (e.g.
                # `from wave_lint_lib.foo import bar` when the file is at
                # `.wavefoundry/framework/scripts/wave_lint_lib/foo.py`).
                parts = dotted_full.split(".")
                for i in range(1, len(parts)):
                    suffix = ".".join(parts[i:])
                    if "." in suffix:
                        qualified_index.setdefault(suffix, []).append(node_id)

        # Wave 13129 (1312l): dedupe qualified_index entries — the suffix-indexing
        # path can re-add the same node_id under its dotted suffix when that
        # suffix equals the direct qualified key (e.g., file "A.java" with class
        # `Helper.process` produces dotted_full "A.Helper.process" whose suffix
        # "Helper.process" matches the direct qualified, double-adding the node).
        # Without dedupe, `len(candidates) == 1` rewrite check fails for legit
        # single-candidate matches once the qualified-form external edges 1312l
        # emits hit the lookup path. Preserve order via dict.fromkeys (stable).
        for _k in list(qualified_index.keys()):
            qualified_index[_k] = list(dict.fromkeys(qualified_index[_k]))
        for _k in list(simple_name_index.keys()):
            simple_name_index[_k] = list(dict.fromkeys(simple_name_index[_k]))
        if simple_name_index or qualified_index:
            new_edge_map: dict[tuple[str, str, str, str], dict[str, Any]] = {}
            rewrite_count = 0
            for key, edge in edge_map.items():
                src, tgt, rel, conf = key
                if rel != "calls" or not tgt.startswith("external::"):
                    new_edge_map[key] = edge
                    continue
                bare = tgt[len("external::"):]
                if not bare or bare in _TS_GLOBAL_DENYLIST:
                    new_edge_map[key] = edge
                    continue
                # Wave 13129 (1312l): for edges emitted by Java receiver-type
                # resolution (confidence=RECEIVER_RESOLVED), trust the qualified
                # match (rebind to project node if the qualified name matches a
                # project symbol) but BLOCK the simple-name fallback. The
                # receiver-type resolver determined the call's target class
                # explicitly; falling back to simple-name match would re-introduce
                # the phantom (e.g. external::ObjectOutputStream.writeObject
                # would mis-rewrite to project JSON.writeObject via the unique
                # simple-name "writeObject").
                _receiver_resolved = conf == "RECEIVER_RESOLVED"
                resolved: str | None = None
                if "." in bare:
                    # AC-2: qualified target — require an exact qualified-name
                    # match to a project node's post-`::` portion. The final
                    # segment must also pass the denylist (so
                    # `external::pathlib.Path` stays external even if some
                    # project file defines `Path`).
                    final_seg = bare.rsplit(".", 1)[-1]
                    if final_seg in _TS_GLOBAL_DENYLIST:
                        new_edge_map[key] = edge
                        continue
                    candidates = qualified_index.get(bare, [])
                    if len(candidates) == 1:
                        resolved = candidates[0]
                    elif not candidates and not _receiver_resolved:
                        # Fallback: try the last segment in simple_name_index
                        # (with ambiguity safety + denylist already checked).
                        # Covers cases like C# `h.Process()` where `h` is a
                        # local variable of unknown type and the call should
                        # resolve to the unique project `Process` method.
                        # Skipped for RECEIVER_RESOLVED edges: the resolver
                        # already determined the target class — simple-name
                        # fallback would mis-rewrite to a phantom project node.
                        simple_candidates = simple_name_index.get(final_seg, [])
                        if len(simple_candidates) == 1:
                            resolved = simple_candidates[0]
                else:
                    # AC-1: bare simple name match.
                    candidates = simple_name_index.get(bare, [])
                    if len(candidates) == 1:
                        resolved = candidates[0]
                if resolved and resolved != src:
                    new_key = (src, resolved, rel, conf)
                    new_edge = dict(edge)
                    new_edge["target"] = resolved
                    # setdefault: if a same-key edge already exists, the
                    # rewrite collapses both into one — desired dedupe.
                    new_edge_map.setdefault(new_key, new_edge)
                    rewrite_count += 1
                else:
                    new_edge_map[key] = edge
            edge_map = new_edge_map
            if self.verbose and rewrite_count:
                print(
                    f"build_index: graph cross-file resolution rewrote {rewrite_count} external::* edges to project-internal nodes",
                    flush=True,
                )

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
