#!/usr/bin/env python3
"""Language-aware text chunker for the Wavefoundry index builder."""
from __future__ import annotations

import ast
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Optional

try:
    from _tag_utils import infer_tags as _infer_tags
except ImportError:  # pragma: no cover - exercised when chunker is loaded as a standalone script module
    import importlib.util
    from pathlib import Path

    _tag_utils_path = Path(__file__).resolve().with_name("_tag_utils.py")
    _tag_utils_spec = importlib.util.spec_from_file_location("_tag_utils", _tag_utils_path)
    if _tag_utils_spec is None or _tag_utils_spec.loader is None:
        raise
    _tag_utils_mod = importlib.util.module_from_spec(_tag_utils_spec)
    _tag_utils_spec.loader.exec_module(_tag_utils_mod)
    _infer_tags = _tag_utils_mod.infer_tags

_log = logging.getLogger(__name__)


sys.dont_write_bytecode = True

# ---------------------------------------------------------------------------
# Tree-sitter lazy loader — optional; falls back to regex chunkers if absent
# ---------------------------------------------------------------------------
try:
    from tree_sitter import Language, Parser as _TSParser
    _TS_AVAILABLE = True
except ImportError:
    _TS_AVAILABLE = False
    Language = None  # type: ignore
    _TSParser = None  # type: ignore


def _ts_language(module_name: str, lang_fn: str):
    """Load a tree-sitter Language, returning None if the grammar is unavailable."""
    if not _TS_AVAILABLE:
        return None
    try:
        mod = __import__(module_name, fromlist=[lang_fn])
        return Language(getattr(mod, lang_fn)())
    except Exception:
        return None


# Lazily populated grammar Language objects — None until first call or if grammar not installed
_TS_LANGS: dict[str, Optional[object]] = {}
# Lazily populated Parser objects cached per language key for indexer throughput
_TS_PARSERS: dict[str, Optional[object]] = {}
# Tracks language keys for which a grammar-miss warning has already been emitted this process
_TS_WARNED: set[str] = set()


def _get_ts_lang(key: str):
    if key in _TS_LANGS:
        return _TS_LANGS[key]
    # tree-sitter >=0.24 grammar packages expose `.language` (callable, no-arg).
    # tree_sitter_typescript is the exception: exposes language_typescript / language_tsx.
    if key == "sql":
        lang = _ts_language("tree_sitter_sql", "language")
        if lang is None:
            lang = _ts_language("tree_sitter_sql", "language_sql")
        _TS_LANGS[key] = lang
        return lang
    if key == "xml":
        lang = _ts_language("tree_sitter_xml", "language_xml")
        if lang is None:
            lang = _ts_language("tree_sitter_xml", "language_dtd")
        _TS_LANGS[key] = lang
        return lang
    if key == "php":
        lang = _ts_language("tree_sitter_php", "language_php")
        if lang is None:
            lang = _ts_language("tree_sitter_php", "language_php_only")
        _TS_LANGS[key] = lang
        return lang
    mapping = {
        "typescript": ("tree_sitter_typescript", "language_typescript"),
        "javascript": ("tree_sitter_javascript", "language"),
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
    }
    if key not in mapping:
        _TS_LANGS[key] = None
        return None
    mod_name, fn_name = mapping[key]
    lang = _ts_language(mod_name, fn_name)
    _TS_LANGS[key] = lang
    return lang


def _get_ts_parser(lang_key: str):
    """Return a cached Parser for lang_key, creating it on first use."""
    if lang_key in _TS_PARSERS:
        return _TS_PARSERS[lang_key]
    lang = _get_ts_lang(lang_key)
    if lang is None:
        _TS_PARSERS[lang_key] = None
        return None
    try:
        parser = _TSParser(lang)
        _TS_PARSERS[lang_key] = parser
        return parser
    except Exception:
        _TS_PARSERS[lang_key] = None
        return None


def _ts_parse(lang_key: str, source: str):
    """Parse source with tree-sitter. Returns tree or None on failure/unavailability.
    Logs a warning on first miss so operators know which language fell back to regex.
    """
    parser = _get_ts_parser(lang_key)
    if parser is None:
        if lang_key not in _TS_WARNED:
            _TS_WARNED.add(lang_key)
            if not _TS_AVAILABLE:
                _log.debug("tree-sitter not installed; using regex chunker for %s", lang_key)
            else:
                _log.warning(
                    "tree-sitter grammar for %s not installed; falling back to regex chunker",
                    lang_key,
                )
        return None
    try:
        return parser.parse(source.encode("utf-8", errors="replace"))
    except Exception as exc:
        _log.warning("tree-sitter parse error for %s (%s); falling back to regex chunker", lang_key, exc)
        return None


def _ts_node_lines(node) -> tuple[int, int]:
    """Return 1-based (start_line, end_line) for a tree-sitter node."""
    return (node.start_point[0] + 1, node.end_point[0] + 1)


def _ts_node_text(node, source_lines: list[str]) -> str:
    start = node.start_point[0]
    end = node.end_point[0]
    return "\n".join(source_lines[start:end + 1])


def _ts_collapse_body(text: str, max_lines: int = 150) -> str:
    """If text exceeds max_lines, collapse body to signature + '{ ... }' + last line.

    For languages without braces (e.g. a Rust fn declaration ending in ';'), keeps
    the first max_lines lines so the signature is always preserved.
    """
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    # Find opening brace line; collapse body around it
    for i, line in enumerate(lines):
        if "{" in line:
            sig = "\n".join(lines[:i + 1])
            last = lines[-1].strip()
            return f"{sig}\n    // ... {len(lines) - i - 2} lines ...\n{last}"
    # No brace found (declarations ending in ';', etc.) — keep the first max_lines
    return "\n".join(lines[:max_lines])


CHUNKER_VERSION = "22"

# Lines per window and overlap for the line-window fallback chunker.
WINDOW_SIZE = 120
WINDOW_OVERLAP = 10
MAX_CODE_CHUNK_CHARS = 4000

# Minimum chunk size for structured chunkers.  Sub-minimum chunks are merged
# into their predecessor.  Imports chunks are exempt.  Reused by tree-sitter
# wave (12c86).
CHUNK_MIN_LINES = 2

# Character threshold above which a ## section is re-split at ### boundaries.
H3_SPLIT_THRESHOLD_CHARS = 2000

# Extensions routed to each chunker.
PYTHON_EXTENSIONS = {".py"}
MARKDOWN_EXTENSIONS = {".md", ".markdown"}
JAVA_EXTENSIONS = {".java"}
SCALA_EXTENSIONS = {".scala"}
CSHARP_EXTENSIONS = {".cs"}
JS_TS_EXTENSIONS = {".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"}
C_CPP_EXTENSIONS = {".c", ".cpp", ".h", ".hpp"}
HTML_EXTENSIONS = {".html", ".htm"}
GO_EXTENSIONS = {".go"}
RUST_EXTENSIONS = {".rs"}
SHELL_EXTENSIONS = {".sh", ".bash", ".zsh", ".fish"}
BATCH_EXTENSIONS = {".bat", ".cmd"}
TERRAFORM_EXTENSIONS = {".tf", ".tfvars"}
HCL_EXTENSIONS = {".hcl"}
HELM_EXTENSIONS = {".tpl"}  # Helm/Go template files; .tpl is also used by non-Helm templating systems
# Extensionless filenames dispatched to code chunkers rather than plain-text doc chunker.
# Keep in sync with indexer.py:CODE_EXTENSIONLESS_NAMES.
CODE_EXTENSIONLESS_NAMES = {
    "Jenkinsfile", "Makefile", "Dockerfile", "Vagrantfile", "Brewfile",
    "Fastfile", "Appfile", "Podfile", "Gemfile", "Procfile",
}
SQL_EXTENSIONS = {".sql", ".psql", ".pgsql", ".ddl", ".dml", ".tsql", ".hql"}
XML_EXTENSIONS = {".xml", ".jsp", ".xsd", ".xsl", ".xslt", ".svg"}
KOTLIN_EXTENSIONS = {".kt", ".kts"}
RUBY_EXTENSIONS = {".rb"}
PHP_EXTENSIONS = {".php"}
YAML_EXTENSIONS = {".yaml", ".yml"}
TOML_EXTENSIONS = {".toml"}
JSON_EXTENSIONS = {".json", ".jsonc"}
CSS_EXTENSIONS = {".css"}
SCSS_EXTENSIONS = {".scss"}
POWERSHELL_EXTENSIONS = {".ps1", ".psm1"}
HCL_INDEX_EXTENSIONS = {".tf", ".hcl"}
MAKEFILE_NAMES = {"Makefile", "GNUmakefile"}
CODE_EXTENSIONS = {
    ".sass",
    *BATCH_EXTENSIONS,
    *HELM_EXTENSIONS,
}

SWIFT_EXTENSIONS = {".swift"}
OBJC_EXTENSIONS = {".m", ".mm"}
IPYNB_EXTENSIONS = {".ipynb"}

# Maps raw file extensions to canonical language names used in chunk metadata.
# Ensures code_search(language=...) filters match stored chunk language values.
_EXT_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".cs": "csharp",
    ".cpp": "cpp", ".hpp": "cpp",
    ".c": "c", ".h": "c",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell",
    ".fish": "fish",
    ".kt": "kotlin", ".kts": "kotlin",
    ".groovy": "groovy",
    ".scala": "scala",
    ".css": "css",
    ".scss": "scss",
    ".sql": "sql",
    ".xml": "xml",
    ".html": "html", ".htm": "html",
    ".swift": "swift",
    ".json": "json", ".jsonc": "json",
    ".toml": "toml",
    ".yml": "yaml", ".yaml": "yaml",
    **{ext: "powershell" for ext in (".ps1", ".psm1")},
    **{ext: "batch" for ext in BATCH_EXTENSIONS},
    **{ext: "terraform" for ext in TERRAFORM_EXTENSIONS},
    **{ext: "hcl" for ext in HCL_EXTENSIONS},
    **{ext: "helm" for ext in HELM_EXTENSIONS},
    ".psql": "sql", ".pgsql": "sql", ".ddl": "sql", ".dml": "sql", ".tsql": "sql", ".hql": "sql",
    ".ipynb": "jupyter",
}


def _ext_language(ext: str) -> str:
    """Return canonical language name for a file extension (with or without leading dot)."""
    key = ext if ext.startswith(".") else f".{ext}"
    return _EXT_TO_LANGUAGE.get(key, ext.lstrip("."))


SEED_PATH_MARKERS = (
    ".wavefoundry/framework/seeds/",
    ".wavefoundry\\framework\\seeds\\",
)

PROMPT_PATH_MARKERS = (
    "docs/prompts/",
    "docs\\prompts\\",
)

# Files ending in .prompt.md are treated as prompts regardless of directory.
PROMPT_SUFFIX = ".prompt.md"

# Extensionless filenames routed to plain-text doc chunker.
# Keep in sync with indexer.py:DOCS_EXTENSIONLESS_NAMES.
DOCS_EXTENSIONLESS_NAMES = {"README", "LICENSE", "CHANGELOG", "CONTRIBUTING", "NOTICE"}

# Plain-text extensions routed to plain-text doc chunker.
TEXT_EXTENSIONS = {".txt"}

# Pre-compiled import/namespace scan patterns (used in chunker pre-passes)
_RE_JAVA_PKG = re.compile(r"^\s*package\s+")
_RE_JAVA_IMPORT = re.compile(r"^\s*import\s+")
_RE_CS_NS = re.compile(r"^\s*namespace\s+")
_RE_CS_USING = re.compile(r"^\s*using\s+")
_RE_JS_IMPORT = re.compile(r"^\s*(?:import\b|const\s+\w+\s*=\s*require\s*\()")
_RE_GO_PKG = re.compile(r"^\s*package\s+")
_RE_GO_IMPORT_BLOCK = re.compile(r"^import\s+\(")
_RE_GO_IMPORT_SINGLE = re.compile(r'^import\s+"')  # aliased form (import alias "pkg") not captured
_RE_RUST_USE = re.compile(r"^\s*(?:use\s+|extern\s+crate\s+)")
_RE_C_INCLUDE = re.compile(r"^\s*#\s*(?:include|import)\b")
_RE_SWIFT_IMPORT = re.compile(r"^\s*import\s+\w")
_RE_OBJC_IMPORT = re.compile(r"^\s*#\s*import\b")

DESIGN_JSON_MARKER = "docs/design-system/"


def _normalize_path(path: str) -> str:
    """Return path with forward slashes on all platforms."""
    return path.replace("\\", "/")


def _slugify(text: str) -> str:
    """Convert a section heading to a URL-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = slug.strip("-")
    return slug


@dataclass
class Chunk:
    id: str
    path: str
    kind: str          # "code" | "code-summary" | "doc" | "doc-summary" | "seed" | "prompt"
    language: Optional[str]
    lines: tuple[int, int]
    section: Optional[str]
    text: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "path": self.path,
            "kind": self.kind,
            "language": self.language,
            "lines": list(self.lines),
            "section": self.section,
            "text": self.text,
        }


# ---------------------------------------------------------------------------
# Python chunker
# ---------------------------------------------------------------------------

def _extract_docstring(node: ast.AST) -> Optional[str]:
    """Return the docstring of a function/class/module node, or None."""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
        return None
    if not node.body:
        return None
    first = node.body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
        return first.value.value
    return None


def _node_line_range(node: ast.AST, source_lines: list[str]) -> tuple[int, int]:
    start = node.lineno
    end = getattr(node, "end_lineno", start)
    return (start, min(end, len(source_lines)))


def _qualified_name(node: ast.AST, parent_name: Optional[str]) -> str:
    name = getattr(node, "name", "?")
    return f"{parent_name}.{name}" if parent_name else name


def _file_stem(path: str) -> str:
    """Return the stem of a file path (filename without extension)."""
    return PurePosixPath(path).stem


def chunk_python(source: str, path: str) -> list[Chunk]:
    """Chunk a Python source file into function, class, method, and docstring chunks."""
    path = _normalize_path(path)
    if not source.strip():
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return chunk_line_window(source, path, language="python", section=_file_stem(path))

    source_lines = source.splitlines()
    chunks: list[Chunk] = []
    stem = _file_stem(path)

    # Module-level docstring
    module_doc = _extract_docstring(tree)
    if module_doc:
        chunks.append(Chunk(
            id=f"{path}::__doc__",
            path=path,
            kind="doc",
            language="python",
            lines=(1, module_doc.count("\n") + 1),
            section=None,
            text=module_doc.strip(),
        ))

    def _visit(node: ast.AST, parent_name: Optional[str] = None) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            qname = _qualified_name(node, parent_name)
            # Include decorator lines in the chunk start (AC-6 / decorator fix)
            if hasattr(node, "decorator_list") and node.decorator_list:
                start = node.decorator_list[0].lineno
            else:
                start = node.lineno
            _, end = _node_line_range(node, source_lines)
            node_source = "\n".join(source_lines[start - 1:end])
            # Breadcrumb: {file_stem} > {qualified_name}
            breadcrumb = f"{stem} > {qname}"

            # Emit docstring as doc chunk if present
            doc = _extract_docstring(node)
            if doc:
                doc_end = node.lineno + doc.count("\n") + 2
                chunks.append(Chunk(
                    id=f"{path}::{qname}.__doc__",
                    path=path,
                    kind="doc",
                    language="python",
                    lines=(node.lineno, min(doc_end, end)),
                    section=breadcrumb,
                    text=f"{breadcrumb}\n\n{doc.strip()}",
                ))

            # Emit the node itself as a code chunk
            chunks.append(Chunk(
                id=f"{path}::{qname}",
                path=path,
                kind="code",
                language="python",
                lines=(start, end),
                section=breadcrumb,
                text=node_source,
            ))

            # Recurse into class bodies for methods
            if isinstance(node, ast.ClassDef):
                for child in ast.iter_child_nodes(node):
                    _visit(child, parent_name=qname)
        else:
            for child in ast.iter_child_nodes(node):
                _visit(child, parent_name=parent_name)

    for node in ast.iter_child_nodes(tree):
        _visit(node)

    return _merge_small_chunks(chunks)


def split_large_code_chunks(chunks: list[Chunk], max_chars: int = MAX_CODE_CHUNK_CHARS) -> list[Chunk]:
    """Split oversized code chunks into smaller line-window chunks."""
    result: list[Chunk] = []
    for chunk in chunks:
        if chunk.kind != "code" or len(chunk.text) <= max_chars:
            result.append(chunk)
            continue

        start_line, _ = chunk.lines
        lines = chunk.text.splitlines()
        if not lines:
            continue

        window_lines: list[str] = []
        window_start = start_line
        current_len = 0

        for offset, line in enumerate(lines):
            line_len = len(line) + 1
            if window_lines and current_len + line_len > max_chars:
                window_end = window_start + len(window_lines) - 1
                result.append(Chunk(
                    id=f"{chunk.id}:L{window_start}-L{window_end}",
                    path=chunk.path,
                    kind=chunk.kind,
                    language=chunk.language,
                    lines=(window_start, window_end),
                    section=chunk.section,
                    text="\n".join(window_lines),
                ))
                window_lines = []
                window_start = start_line + offset
                current_len = 0
            window_lines.append(line)
            current_len += line_len

        if window_lines:
            window_end = window_start + len(window_lines) - 1
            result.append(Chunk(
                id=f"{chunk.id}:L{window_start}-L{window_end}",
                path=chunk.path,
                kind=chunk.kind,
                language=chunk.language,
                lines=(window_start, window_end),
                section=chunk.section,
                text="\n".join(window_lines),
            ))

    return result


# ---------------------------------------------------------------------------
# Markdown chunker
# ---------------------------------------------------------------------------

_FENCED_CODE_PATTERN = re.compile(
    r"^```(\w*)\n(.*?)^```", re.MULTILINE | re.DOTALL
)
_H1_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_H2_PATTERN = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_H3_PATTERN = re.compile(r"^###\s+(.+)$", re.MULTILINE)


def _detect_primary_heading_level(source: str) -> int:
    """Return the primary section split depth for a markdown document: 2 (##) or 3 (###).

    Uses ## when any ## headings exist (they are the top-level section boundary).
    Falls back to ### only when the document has ### headings but no ## headings at all.
    Defaults to 2 (preserves existing behavior) when neither level is present.
    """
    h2_count = len(_H2_PATTERN.findall(source))
    if h2_count > 0:
        return 2
    h3_count = len(_H3_PATTERN.findall(source))
    return 3 if h3_count > 0 else 2


def _extract_fenced_code(
    body: str,
    base_line: int,
    section_label: str,
    h2_slug: str,
    path: str,
    default_kind: str,
    h3_slug: Optional[str] = None,
) -> tuple[list[Chunk], list[tuple[int, int]]]:
    """Extract fenced code blocks from body, return (chunks, spans_to_remove)."""
    chunks: list[Chunk] = []
    spans: list[tuple[int, int]] = []
    id_prefix = f"{path}#{h2_slug}/{h3_slug}" if h3_slug else f"{path}#{h2_slug}"
    for m in _FENCED_CODE_PATTERN.finditer(body):
        lang = m.group(1) or None
        code_text = m.group(2)
        block_start_offset = body[:m.start()].count("\n")
        abs_start = base_line + block_start_offset + 1
        abs_end = abs_start + code_text.count("\n")
        spans.append((m.start(), m.end()))
        if code_text.strip():
            chunks.append(Chunk(
                id=f"{id_prefix}:code",
                path=path,
                kind="code",
                language=lang,
                lines=(abs_start, abs_end),
                section=section_label,
                text=f"{section_label}\n\n{code_text.strip()}",
            ))
    return chunks, spans


def _split_h3_sections(
    body: str,
    base_line: int,
    h2_title: str,
    h2_slug: str,
    doc_title: Optional[str],
    path: str,
    default_kind: str,
) -> list[Chunk]:
    """Split an oversized ## section body at ### boundaries."""
    chunks: list[Chunk] = []
    sub_sections: list[tuple[str, int, str]] = []
    lines = body.splitlines(keepends=True)
    current_h3: Optional[str] = None
    current_start_offset = 0
    current_lines: list[str] = []

    for i, line in enumerate(lines):
        m = re.match(r"^###\s+(.+)$", line.rstrip())
        if m:
            if current_lines:
                sub_sections.append((current_h3, current_start_offset, "".join(current_lines)))
            current_h3 = m.group(1).strip()
            current_start_offset = i
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sub_sections.append((current_h3, current_start_offset, "".join(current_lines)))

    for h3_title, offset, sub_body in sub_sections:
        if not sub_body.strip():
            continue
        abs_start = base_line + offset
        if h3_title:
            if doc_title:
                section_label = f"{doc_title} > {h2_title} > {h3_title}"
            else:
                section_label = f"{h2_title} > {h3_title}"
            h3_slug = _slugify(h3_title)
        else:
            # Content before the first ### in this body (part of the ## prose)
            if doc_title:
                section_label = f"{doc_title} > {h2_title}"
            else:
                section_label = h2_title
            h3_slug = None

        code_chunks, code_spans = _extract_fenced_code(
            sub_body, abs_start, section_label, h2_slug, path, default_kind, h3_slug=h3_slug
        )
        chunks.extend(code_chunks)

        prose = sub_body
        for start_pos, end_pos in reversed(code_spans):
            prose = prose[:start_pos] + prose[end_pos:]
        prose = prose.strip()

        if prose:
            id_str = f"{path}#{h2_slug}/{h3_slug}" if h3_slug else f"{path}#{h2_slug}"
            chunks.append(Chunk(
                id=id_str,
                path=path,
                kind=default_kind,
                language=None,
                lines=(abs_start, abs_start + sub_body.count("\n")),
                section=section_label,
                text=f"{section_label}\n\n{prose}",
            ))

    return chunks


def chunk_markdown(
    source: str,
    path: str,
    kind_override: Optional[str] = None,
    suppress_h3_split: bool = False,
    suppress_code_extraction: bool = False,
) -> list[Chunk]:
    """Chunk a markdown file by primary heading level, splitting out fenced code blocks.

    The primary split boundary is detected from the document: ## when any ## headings
    are present, ### only when no ## headings exist.

    suppress_h3_split: when True, never re-split oversized ## sections at ### boundaries
        (used for prompt files where step sequences must stay intact).
    suppress_code_extraction: when True, fenced code blocks stay inline with surrounding
        prose rather than being extracted as separate chunks (used for prompt files where
        commands are inseparable from their instructional context).
    """
    path = _normalize_path(path)
    default_kind = kind_override or "doc"

    if not source.strip():
        return []

    # Detect primary heading level and build split pattern
    primary_level = _detect_primary_heading_level(source)
    primary_hashes = "#" * primary_level
    split_pattern = re.compile(rf"^{re.escape(primary_hashes)}\s+(.+)$")

    # Capture H1 title for breadcrumb injection
    h1_match = _H1_PATTERN.search(source)
    doc_title: Optional[str] = h1_match.group(1).strip() if h1_match else None

    chunks: list[Chunk] = []

    # Split on primary heading level
    sections: list[tuple[Optional[str], int, str]] = []  # (title, start_line, text)
    lines = source.splitlines(keepends=True)
    current_title: Optional[str] = None
    current_start = 1
    current_lines: list[str] = []

    for i, line in enumerate(lines, start=1):
        m = split_pattern.match(line.rstrip())
        if m:
            if current_lines:
                sections.append((current_title, current_start, "".join(current_lines)))
            current_title = m.group(1).strip()
            current_start = i
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, current_start, "".join(current_lines)))

    for title, start_line, body in sections:
        if not body.strip():
            continue

        is_preamble = title is None
        slug = _slugify(title) if title else "preamble"
        section_end = start_line + len(body.splitlines())

        # Preamble: no breadcrumb injection
        if is_preamble:
            if suppress_code_extraction:
                prose = body.strip()
                if prose:
                    chunks.append(Chunk(
                        id=f"{path}#{slug}",
                        path=path,
                        kind=default_kind,
                        language=None,
                        lines=(start_line, section_end),
                        section=None,
                        text=prose,
                    ))
            else:
                code_chunks, code_spans = _extract_fenced_code(
                    body, start_line, None, slug, path, default_kind
                )
                for c in code_chunks:
                    c.section = None
                    c.text = c.text.split("\n\n", 1)[-1] if "\n\n" in c.text else c.text
                chunks.extend(code_chunks)
                prose = body
                for start_pos, end_pos in reversed(code_spans):
                    prose = prose[:start_pos] + prose[end_pos:]
                prose = prose.strip()
                if prose:
                    chunks.append(Chunk(
                        id=f"{path}#{slug}",
                        path=path,
                        kind=default_kind,
                        language=None,
                        lines=(start_line, section_end),
                        section=None,
                        text=prose,
                    ))
            continue

        # Build breadcrumb for this ## section
        if doc_title:
            section_label = f"{doc_title} > {title}"
        else:
            section_label = title

        # Threshold-gate H3 splitting for oversized sections (skipped for prompts)
        if not suppress_h3_split and len(body.strip()) > H3_SPLIT_THRESHOLD_CHARS and _H3_PATTERN.search(body):
            chunks.extend(_split_h3_sections(
                body, start_line, title, slug, doc_title, path, default_kind
            ))
            continue

        if suppress_code_extraction:
            # Keep fenced code inline — emit entire section as a single prose chunk
            prose = body.strip()
            if prose:
                if not suppress_h3_split and len(prose) > H3_SPLIT_THRESHOLD_CHARS:
                    for fw_chunk in chunk_line_window(prose, path):
                        fw_chunk.id = f"{path}#{slug}:L{fw_chunk.lines[0]}-L{fw_chunk.lines[1]}"
                        fw_chunk.kind = default_kind
                        fw_chunk.section = section_label
                        fw_chunk.text = f"{section_label}\n\n{fw_chunk.text}"
                        chunks.append(fw_chunk)
                else:
                    chunks.append(Chunk(
                        id=f"{path}#{slug}",
                        path=path,
                        kind=default_kind,
                        language=None,
                        lines=(start_line, section_end),
                        section=section_label,
                        text=f"{section_label}\n\n{prose}",
                    ))
        else:
            # Standard section: extract fenced code then emit prose
            code_chunks, code_spans = _extract_fenced_code(
                body, start_line, section_label, slug, path, default_kind
            )
            chunks.extend(code_chunks)

            prose = body
            for start_pos, end_pos in reversed(code_spans):
                prose = prose[:start_pos] + prose[end_pos:]
            prose = prose.strip()

            if prose:
                # For oversized sections without ### (line-window fallback), inject breadcrumb
                if len(prose) > H3_SPLIT_THRESHOLD_CHARS:
                    for fw_chunk in chunk_line_window(prose, path):
                        fw_chunk.id = f"{path}#{slug}:L{fw_chunk.lines[0]}-L{fw_chunk.lines[1]}"
                        fw_chunk.kind = default_kind
                        fw_chunk.section = section_label
                        fw_chunk.text = f"{section_label}\n\n{fw_chunk.text}"
                        chunks.append(fw_chunk)
                else:
                    chunks.append(Chunk(
                        id=f"{path}#{slug}",
                        path=path,
                        kind=default_kind,
                        language=None,
                        lines=(start_line, section_end),
                        section=section_label,
                        text=f"{section_label}\n\n{prose}",
                    ))

    return chunks


# ---------------------------------------------------------------------------
# Line-window fallback chunker
# ---------------------------------------------------------------------------

_TOP_LEVEL_BOUNDARY_RE = re.compile(
    r"^(?:def |class |function |async function |export (?:default )?(?:function|class)|@)"
)

MIN_CHUNK_LINES = 10  # minimum for line-window chunks (prevents tiny orphan tails)


def _find_break_point(lines: list[str], window_start: int, window_end: int) -> int:
    """Return the best break index within the last 20% of the window.

    Prefers blank lines first, then lines at column 0 (top-level boundaries).
    Returns window_end (the hard cap) if no preferred break is found.
    The returned value is the exclusive end index (slice end).
    """
    lookback_start = window_end - max(1, (window_end - window_start) // 5)
    # Ensure minimum chunk size
    min_end = window_start + MIN_CHUNK_LINES

    # First pass: blank line
    for j in range(window_end - 1, max(lookback_start, min_end) - 1, -1):
        if j < len(lines) and lines[j].strip() == "":
            return j  # break before this blank line (exclusive end)

    # Second pass: top-level boundary (column 0, non-blank)
    for j in range(window_end - 1, max(lookback_start, min_end) - 1, -1):
        if j < len(lines) and lines[j] and not lines[j][0].isspace():
            if _TOP_LEVEL_BOUNDARY_RE.match(lines[j]):
                return j

    return window_end


def chunk_line_window(
    source: str,
    path: str,
    language: Optional[str] = None,
    window: int = WINDOW_SIZE,
    overlap: int = WINDOW_OVERLAP,
    section: Optional[str] = None,
) -> list[Chunk]:
    """Chunk any text into line windows, preferring logical break points."""
    path = _normalize_path(path)
    lines = source.splitlines()
    if not lines:
        return []

    chunks: list[Chunk] = []
    i = 0
    while i < len(lines):
        hard_end = min(i + window, len(lines))
        # Only look for a smarter break if we haven't reached end of file
        if hard_end < len(lines):
            end = _find_break_point(lines, i, hard_end)
        else:
            end = hard_end
        end = max(end, i + 1)  # always advance at least one line

        start_line = i + 1
        end_line = end
        text = "\n".join(lines[i:end])
        if section:
            text = f"{section}\n\n{text}"
        chunks.append(Chunk(
            id=f"{path}:L{start_line}-L{end_line}",
            path=path,
            kind="code",
            language=language,
            lines=(start_line, end_line),
            section=section,
            text=text,
        ))
        if end >= len(lines):
            break
        # Advance to next window; no overlap for line-window (overlap=0 when called
        # by structured chunkers that already hit fallback)
        i = end

    return chunks


def chunk_secrets_file(source: str, path: str, language: str) -> list[Chunk]:
    """Chunk key=value secrets files (.tfvars, .env) with values redacted.

    Keeps variable names so agents can search for which keys are defined.
    Replaces all values with <redacted> so secret material is never stored in the index.

    Supported formats:
    - .tfvars: KEY = "value", KEY = value, KEY = ["list"], KEY = { map }
    - .env:    KEY=value, KEY="value", export KEY=value
    - Comments (# ...) and blank lines are preserved as-is.
    - Multi-line values (heredoc or block) are collapsed to a single <redacted> line.
    """
    import re
    path = _normalize_path(path)
    # Matches: optional 'export ', KEY, optional whitespace, '=', rest
    _ASSIGN = re.compile(r'^(export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=.*$')
    # Matches start of a multi-line HCL block value: KEY = {  or KEY = [
    _BLOCK_START = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*[\[{]')

    redacted_lines: list[str] = []
    raw_lines = source.splitlines()
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        stripped = line.strip()

        # Blank lines and comments pass through
        if not stripped or stripped.startswith("#"):
            redacted_lines.append(line)
            i += 1
            continue

        # Multi-line block value: consume until matching close bracket/brace
        block_match = _BLOCK_START.match(stripped)
        if block_match and not (stripped.endswith("]") or stripped.endswith("}")):
            key = block_match.group(1)
            redacted_lines.append(f"{key} = <redacted>")
            depth = stripped.count("{") + stripped.count("[") - stripped.count("}") - stripped.count("]")
            i += 1
            while i < len(raw_lines) and depth > 0:
                bl = raw_lines[i]
                depth += bl.count("{") + bl.count("[") - bl.count("}") - bl.count("]")
                i += 1
            continue

        # Single-line assignment
        m = _ASSIGN.match(stripped)
        if m:
            key = m.group(2)
            redacted_lines.append(f"{key} = <redacted>")
            i += 1
            continue

        # Anything else (e.g. bare block closers, unexpected syntax) — drop silently
        i += 1

    redacted_source = "\n".join(redacted_lines)
    stem = _file_stem(path)
    return chunk_line_window(redacted_source, path, language=language, section=stem)


def chunk_plain_text(source: str, path: str) -> list[Chunk]:
    """Chunk plain-text files (.txt, extensionless README/LICENSE/etc.) as doc chunks.

    Uses the same line-window approach as chunk_line_window but emits kind="doc"
    so the content lands in the docs index rather than the code index.
    """
    path = _normalize_path(path)
    lines = source.splitlines()
    if not lines:
        return []

    section = _file_stem(path) or None
    chunks: list[Chunk] = []
    step = max(1, WINDOW_SIZE - WINDOW_OVERLAP)
    i = 0
    while i < len(lines):
        end = min(i + WINDOW_SIZE, len(lines))
        start_line = i + 1
        end_line = end
        text = "\n".join(lines[i:end])
        if section:
            text = f"{section}\n\n{text}"
        chunks.append(Chunk(
            id=f"{path}:L{start_line}-L{end_line}",
            path=path,
            kind="doc",
            language=None,
            lines=(start_line, end_line),
            section=section,
            text=text,
        ))
        if end >= len(lines):
            break
        i += step

    return chunks


# ---------------------------------------------------------------------------
# Shared helpers for structured language chunkers
# ---------------------------------------------------------------------------

def _strip_javadoc(comment: str) -> str:
    """Strip /** ... */ decoration from a Javadoc/Scaladoc block comment."""
    lines = comment.splitlines()
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("/**") or stripped == "*/":
            # Remove opening/closing markers; keep content on same line as /**
            stripped = re.sub(r"^/\*\*\s*", "", stripped)
            stripped = re.sub(r"\s*\*/$", "", stripped)
        elif stripped.startswith("*"):
            stripped = re.sub(r"^\*\s?", "", stripped)
        result.append(stripped)
    return "\n".join(result).strip()


def _strip_line_doc_comments(lines: list[str], prefix: str) -> str:
    """Strip a line-comment prefix (e.g. '/// ' or '// ') from each line."""
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(prefix.rstrip()):
            stripped = stripped[len(prefix.rstrip()):].lstrip()
        result.append(stripped)
    return "\n".join(result).strip()



def _annotation_names(annotations: list[str], prefix: str = "@") -> str:
    """Extract just the annotation names (no arguments) for doc chunks."""
    names = []
    for ann in annotations:
        m = re.match(r"[@\[#](\w+)", ann)
        if m:
            names.append(f"{prefix}{m.group(1)}")
    return " ".join(names)


def _decl_line_ends(line: str, in_block_comment: bool = False) -> tuple[bool, bool]:
    """Return (terminates, in_block_comment_after) for a declaration line.

    Strips // line comments and tracks /* */ block comment state across calls
    so multi-line block comments do not cause false early termination.
    """
    pos = 0
    length = len(line)
    while pos < length:
        if in_block_comment:
            end = line.find("*/", pos)
            if end == -1:
                return False, True  # whole line is inside block comment
            in_block_comment = False
            pos = end + 2
        else:
            # Check for // line comment
            lc = line.find("//", pos)
            # Check for /* block comment open
            bc = line.find("/*", pos)
            # Check for terminators
            t_open = line.find("{", pos)
            t_semi = line.find(";", pos)
            # Pick the earliest event
            candidates = {k: v for k, v in {"lc": lc, "bc": bc, "t_open": t_open, "t_semi": t_semi}.items() if v != -1}
            if not candidates:
                break
            first_key = min(candidates, key=lambda k: candidates[k])
            first_pos = candidates[first_key]
            if first_key == "lc":
                break  # rest of line is a comment
            elif first_key == "bc":
                in_block_comment = True
                pos = first_pos + 2
            else:
                # terminator found outside any comment
                return True, False
    return False, in_block_comment


def _collect_decl_text(lines: list[str], i: int) -> str:
    """Collect a (possibly multi-line) declaration up to the opening '{' or ';'.

    Correctly handles // line comments and /* */ block comments that span lines.
    """
    parts = [lines[i].rstrip()]
    in_block_comment = False
    j = i + 1
    while j < len(lines):
        ends, in_block_comment = _decl_line_ends(parts[-1], in_block_comment)
        if ends:
            break
        parts.append(lines[j].rstrip())
        j += 1
    # Strip trailing brace/semicolon and whitespace
    text = " ".join(p.strip() for p in parts)
    return re.sub(r"\s*[{;]\s*$", "", text).strip()


def _fallback_with_stem(source: str, path: str, lang: str) -> list[Chunk]:
    """Line-window fallback with depth-1 file-stem breadcrumb (AC-9)."""
    stem = _file_stem(path)
    return chunk_line_window(source, path, language=lang, section=stem)


def _parent_scope(section: Optional[str]) -> Optional[str]:
    """Return the parent scope prefix from a breadcrumb section string.

    E.g. "myfile > MyClass.render" → "myfile > MyClass"
         "myfile > topLevelFn"     → None  (top-level, no parent)
    """
    if not section:
        return None
    # breadcrumb format: "stem > [ClassName.]symbolName"
    # The parent scope is everything before the last dot in the symbol part.
    parts = section.split(" > ", 1)
    if len(parts) < 2:
        return None
    symbol = parts[1]
    dot = symbol.rfind(".")
    if dot == -1:
        return None  # top-level symbol — no parent scope
    return f"{parts[0]} > {symbol[:dot]}"


def _merge_small_chunks(chunks: list[Chunk], scoped: bool = False) -> list[Chunk]:
    """Merge sub-minimum code chunks into their preceding code chunk.

    Only code-kind chunks participate in merging.  Doc chunks and imports
    chunks are always emitted as-is.  If the only chunk is sub-minimum, it is
    returned as-is.

    When ``scoped=True`` (used by tree-sitter chunkers), a sub-minimum chunk is
    only merged into its predecessor if both share the same parent scope
    (same class/impl/interface).  This prevents a 1-line method in one class
    from merging into a method in a different class.
    """
    if len(chunks) <= 1:
        return chunks

    result: list[Chunk] = []
    for chunk in chunks:
        is_imports = chunk.section is not None and chunk.section.endswith("> imports")
        is_doc = chunk.kind == "doc"
        line_count = chunk.lines[1] - chunk.lines[0] + 1

        # Find last code chunk in result as merge target (skip imports chunks)
        last_code_idx = next(
            (
                idx for idx in range(len(result) - 1, -1, -1)
                if result[idx].kind == "code"
                and not (result[idx].section is not None and result[idx].section.endswith("> imports"))
            ),
            None,
        )

        # When scoped, only merge if predecessor shares the same parent scope.
        # None == None is intentional: two top-level symbols both return None,
        # meaning they share file-level scope and may merge.
        same_scope = True
        if scoped and last_code_idx is not None:
            prev = result[last_code_idx]
            same_scope = _parent_scope(chunk.section) == _parent_scope(prev.section)

        if (
            not is_imports
            and not is_doc
            and chunk.kind == "code"
            and line_count < CHUNK_MIN_LINES
            and last_code_idx is not None
            and same_scope
        ):
            prev = result[last_code_idx]
            merged_text = prev.text + "\n" + chunk.text
            result[last_code_idx] = Chunk(
                id=prev.id,
                path=prev.path,
                kind=prev.kind,
                language=prev.language,
                lines=(prev.lines[0], chunk.lines[1]),
                section=prev.section,
                text=merged_text,
            )
        else:
            result.append(chunk)
    return result


# ---------------------------------------------------------------------------
# Java / Scala chunker
# ---------------------------------------------------------------------------

_JAVA_CLASS_RE = re.compile(
    r"^(?:public\s+|private\s+|protected\s+|abstract\s+|final\s+|static\s+)*"
    r"(?:class|interface|enum|record)\s+(\w+)",
    re.MULTILINE,
)
_JAVA_METHOD_RE = re.compile(
    r"^[ \t]*(?:(?:public|private|protected|static|final|abstract|synchronized|native|default|override)\s+)*"
    r"(?:<[^>]+>\s+)?(?:\w+(?:<[^>]+>)?(?:\[\])*\s+)+(\w+)\s*\(",
    re.MULTILINE,
)
_JAVADOC_RE = re.compile(r"/\*\*.*?\*/", re.DOTALL)


def _chunk_java_like(source: str, path: str, lang: str, *, has_namespace: bool = False) -> list[Chunk]:
    """Shared structure-aware chunker for Java and Scala."""
    stem = _file_stem(path)
    lines = source.splitlines()
    chunks: list[Chunk] = []

    # Emit __namespace__ chunk for package declaration
    pkg_lines = [l for l in lines if _RE_JAVA_PKG.match(l)]
    if pkg_lines:
        ns_breadcrumb = f"{stem} > namespace"
        chunks.append(Chunk(
            id=f"{path}::__namespace__",
            path=path,
            kind="code",
            language=lang,
            lines=(1, 1),
            section=ns_breadcrumb,
            text=f"{ns_breadcrumb}\n\n" + "\n".join(pkg_lines),
        ))

    # Emit __imports__ chunk for import statements only
    import_lines = [l for l in lines if _RE_JAVA_IMPORT.match(l)]
    if import_lines:
        breadcrumb = f"{stem} > imports"
        chunks.append(Chunk(
            id=f"{path}::__imports__",
            path=path,
            kind="code",
            language=lang,
            lines=(1, len(import_lines)),
            section=breadcrumb,
            text=f"{breadcrumb}\n\n" + "\n".join(import_lines),
        ))

    # Map line number -> docstring comment that ends just before it
    doc_ends: dict[int, str] = {}
    for m in _JAVADOC_RE.finditer(source):
        doc_text = m.group(0)
        end_line = source[:m.end()].count("\n")
        doc_ends[end_line] = _strip_javadoc(doc_text)

    current_class: Optional[str] = None
    ann_prefixes = ("@",)

    i = 0
    try:
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Collect annotations; track true first-annotation line for doc lookup
            anns: list[str] = []
            ann_first_line = i
            while stripped.startswith("@"):
                if not anns:
                    ann_first_line = i
                anns.append(stripped)
                depth = stripped.count("(") - stripped.count(")")
                i += 1
                while depth > 0 and i < len(lines):
                    cont = lines[i].strip()
                    anns[-1] = anns[-1] + " " + cont
                    depth += cont.count("(") - cont.count(")")
                    i += 1
                if i < len(lines):
                    stripped = lines[i].strip()
                else:
                    break
            # Sync line with i after annotation collection
            line = lines[i] if i < len(lines) else ""

            # Class/interface/enum/trait
            cm = _JAVA_CLASS_RE.match(stripped)
            if cm:
                current_class = cm.group(1)
                breadcrumb = f"{stem} > {current_class}"
                ann_start = ann_first_line
                doc_text = next((doc_ends[k] for k in range(i, ann_start - 3, -1) if k in doc_ends), None)
                if doc_text:
                    ann_names = _annotation_names(anns)
                    doc_body = f"{ann_names}\n\n{doc_text}" if ann_names else doc_text
                    chunks.append(Chunk(
                        id=f"{path}::{current_class}.__doc__",
                        path=path,
                        kind="doc",
                        language=lang,
                        lines=(max(1, i), i + 1),
                        section=breadcrumb,
                        text=f"{breadcrumb}\n\n{doc_body}",
                    ))
                # Always emit a declaration chunk so extends/implements is searchable
                decl_text = _collect_decl_text(lines, i)
                chunks.append(Chunk(
                    id=f"{path}::{current_class}.__decl__",
                    path=path,
                    kind="code",
                    language=lang,
                    lines=(i + 1, i + 1),
                    section=breadcrumb,
                    text=f"{breadcrumb}\n\n{decl_text}",
                ))
                i += 1
                continue

            # Method detection
            mm = _JAVA_METHOD_RE.match(line)
            if mm and current_class:
                method_name = mm.group(1)
                if method_name in {"if", "for", "while", "switch", "catch", "return", "new"}:
                    i += 1
                    continue
                qname = f"{current_class}.{method_name}"
                breadcrumb = f"{stem} > {qname}"
                # Collect method body
                body_lines = [line]
                depth = line.count("{") - line.count("}")
                j = i + 1
                while j < len(lines) and (depth > 0 or (depth == 0 and j == i + 1)):
                    body_lines.append(lines[j])
                    depth += lines[j].count("{") - lines[j].count("}")
                    j += 1
                    if depth <= 0:
                        break
                code_text = "\n".join(body_lines)
                if anns:
                    code_text = "\n".join(anns) + "\n" + code_text
                # Doc chunk — search from method line back to before annotations
                ann_start = ann_first_line
                doc_text = next((doc_ends[k] for k in range(i, ann_start - 3, -1) if k in doc_ends), None)
                if doc_text:
                    ann_names = _annotation_names(anns)
                    doc_body = f"{ann_names}\n\n{doc_text}" if ann_names else doc_text
                    chunks.append(Chunk(
                        id=f"{path}::{qname}.__doc__",
                        path=path,
                        kind="doc",
                        language=lang,
                        lines=(max(1, i), i + 1),
                        section=breadcrumb,
                        text=f"{breadcrumb}\n\n{doc_body}",
                    ))
                chunks.append(Chunk(
                    id=f"{path}::{qname}",
                    path=path,
                    kind="code",
                    language=lang,
                    lines=(i + 1, j),
                    section=breadcrumb,
                    text=code_text,
                ))
                i = j
                continue

            i += 1
    except Exception:
        return _fallback_with_stem(source, path, lang)

    if not chunks:
        return _fallback_with_stem(source, path, lang)
    return split_large_code_chunks(_merge_small_chunks(chunks))


def chunk_java(source: str, path: str) -> list[Chunk]:
    return _chunk_java_like(source, path, "java")


def chunk_scala(source: str, path: str) -> list[Chunk]:
    return _chunk_java_like(source, path, "scala")


# ---------------------------------------------------------------------------
# C# chunker
# ---------------------------------------------------------------------------

_CSHARP_CLASS_RE = re.compile(
    r"^\s*(?:(?:public|private|protected|internal|abstract|sealed|static|partial)\s+)*"
    r"(?:class|interface|struct|enum|record)\s+(\w+)",
    re.MULTILINE,
)
_CSHARP_METHOD_RE = re.compile(
    r"^\s*(?:(?:public|private|protected|internal|static|virtual|override|abstract|async|new|sealed)\s+)*"
    r"(?:\w+(?:<[^>]+>)?(?:\[\])*\s+)+(\w+)\s*\(",
    re.MULTILINE,
)
_CSHARP_NS_RE = re.compile(r"^\s*namespace\s+([\w.]+)", re.MULTILINE)
_CSHARP_DOC_RE = re.compile(r"((?:[ \t]*///[^\n]*\n)+)", re.MULTILINE)
_CSHARP_BLOCK_DOC_RE = re.compile(r"/\*\*.*?\*/", re.DOTALL)


def chunk_csharp(source: str, path: str) -> list[Chunk]:
    stem = _file_stem(path)
    lines = source.splitlines()
    chunks: list[Chunk] = []

    # Emit __namespace__ chunk for namespace declaration
    ns_decl_lines = [l for l in lines if _RE_CS_NS.match(l)]
    if ns_decl_lines:
        ns_breadcrumb = f"{stem} > namespace"
        chunks.append(Chunk(
            id=f"{path}::__namespace__",
            path=path,
            kind="code",
            language="csharp",
            lines=(1, 1),
            section=ns_breadcrumb,
            text=f"{ns_breadcrumb}\n\n" + "\n".join(ns_decl_lines),
        ))

    # Emit __imports__ chunk for using directives only
    import_lines = [l for l in lines if _RE_CS_USING.match(l)]
    if import_lines:
        breadcrumb = f"{stem} > imports"
        chunks.append(Chunk(
            id=f"{path}::__imports__",
            path=path,
            kind="code",
            language="csharp",
            lines=(1, len(import_lines)),
            section=breadcrumb,
            text=f"{breadcrumb}\n\n" + "\n".join(import_lines),
        ))

    # Detect namespace for breadcrumb
    ns_match = _CSHARP_NS_RE.search(source)
    namespace = ns_match.group(1) if ns_match else None

    # Map line -> xml doc comment
    doc_ends: dict[int, str] = {}
    for m in _CSHARP_DOC_RE.finditer(source):
        end_line = source[:m.end()].count("\n")
        raw = m.group(1)
        doc_ends[end_line] = _strip_line_doc_comments(raw.splitlines(), "///")
    for m in _CSHARP_BLOCK_DOC_RE.finditer(source):
        end_line = source[:m.end()].count("\n")
        doc_ends[end_line] = _strip_javadoc(m.group(0))

    current_class: Optional[str] = None
    i = 0
    try:
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Collect [Attribute] blocks; track true first-attribute line for doc lookup
            anns: list[str] = []
            ann_first_line = i
            while stripped.startswith("[") and not stripped.startswith("[assembly"):
                if not anns:
                    ann_first_line = i
                anns.append(stripped)
                depth = stripped.count("[") - stripped.count("]")
                i += 1
                while depth > 0 and i < len(lines):
                    cont = lines[i].strip()
                    anns[-1] = anns[-1] + " " + cont
                    depth += cont.count("[") - cont.count("]")
                    i += 1
                if i < len(lines):
                    stripped = lines[i].strip()
                else:
                    break
            # Sync line with i after attribute collection
            line = lines[i] if i < len(lines) else ""

            cm = _CSHARP_CLASS_RE.match(line)
            if cm:
                current_class = cm.group(1)
                if namespace:
                    breadcrumb = f"{stem} > {namespace} > {current_class}"
                else:
                    breadcrumb = f"{stem} > {current_class}"
                ann_start = ann_first_line
                doc_text = next((doc_ends[k] for k in range(i, ann_start - 3, -1) if k in doc_ends), None)
                if doc_text:
                    ann_names = _annotation_names(anns, prefix="@")
                    # Extract string literal from [Obsolete("...")] style
                    for ann in anns:
                        om = re.search(r'\["([^"]+)"\]', ann)
                        if om:
                            doc_text = f"{doc_text}\n{om.group(1)}"
                    doc_body = f"{ann_names}\n\n{doc_text}" if ann_names else doc_text
                    chunks.append(Chunk(
                        id=f"{path}::{current_class}.__doc__",
                        path=path,
                        kind="doc",
                        language="csharp",
                        lines=(max(1, i), i + 1),
                        section=breadcrumb,
                        text=f"{breadcrumb}\n\n{doc_body}",
                    ))
                # Always emit a declaration chunk so : BaseClass, IInterface is searchable
                decl_text = _collect_decl_text(lines, i)
                chunks.append(Chunk(
                    id=f"{path}::{current_class}.__decl__",
                    path=path,
                    kind="code",
                    language="csharp",
                    lines=(i + 1, i + 1),
                    section=breadcrumb,
                    text=f"{breadcrumb}\n\n{decl_text}",
                ))
                i += 1
                continue

            mm = _CSHARP_METHOD_RE.match(line)
            if mm and current_class:
                method_name = mm.group(1)
                if method_name in {"if", "for", "while", "foreach", "switch", "catch", "using", "return", "new", "get", "set"}:
                    i += 1
                    continue
                qname = f"{current_class}.{method_name}"
                if namespace:
                    breadcrumb = f"{stem} > {namespace} > {qname}"
                else:
                    breadcrumb = f"{stem} > {qname}"
                body_lines = [line]
                depth = line.count("{") - line.count("}")
                j = i + 1
                while j < len(lines) and (depth > 0 or j == i + 1):
                    body_lines.append(lines[j])
                    depth += lines[j].count("{") - lines[j].count("}")
                    j += 1
                    if depth <= 0:
                        break
                code_text = "\n".join(body_lines)
                if anns:
                    code_text = "\n".join(anns) + "\n" + code_text
                ann_start = ann_first_line
                doc_text = next((doc_ends[k] for k in range(i, ann_start - 3, -1) if k in doc_ends), None)
                if doc_text:
                    ann_names = _annotation_names(anns, prefix="@")
                    for ann in anns:
                        om = re.search(r'Obsolete\("([^"]+)"\)', ann)
                        if om:
                            doc_text = f"{doc_text}\n{om.group(1)}"
                    doc_body = f"{ann_names}\n\n{doc_text}" if ann_names else doc_text
                    chunks.append(Chunk(
                        id=f"{path}::{qname}.__doc__",
                        path=path,
                        kind="doc",
                        language="csharp",
                        lines=(max(1, i), i + 1),
                        section=breadcrumb,
                        text=f"{breadcrumb}\n\n{doc_body}",
                    ))
                chunks.append(Chunk(
                    id=f"{path}::{qname}",
                    path=path,
                    kind="code",
                    language="csharp",
                    lines=(i + 1, j),
                    section=breadcrumb,
                    text=code_text,
                ))
                i = j
                continue

            i += 1
    except Exception:
        return _fallback_with_stem(source, path, "csharp")

    if not chunks:
        return _fallback_with_stem(source, path, "csharp")
    return split_large_code_chunks(_merge_small_chunks(chunks))


# ---------------------------------------------------------------------------
# JavaScript / TypeScript chunker
# ---------------------------------------------------------------------------

_JS_CLASS_RE = re.compile(r"^\s*(?:export\s+)?(?:default\s+)?class\s+(\w+)", re.MULTILINE)
_JS_FUNC_RE = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)\s*\(", re.MULTILINE
)
_JS_ARROW_RE = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(", re.MULTILINE
)
# Top-level export const declarations at column 0: export const Foo = ...
# (styled-components, plain constants, enum-like objects, etc.)
_JS_EXPORT_CONST_RE = re.compile(r"^export\s+const\s+(\w+)\s*[:=]")
_JS_METHOD_RE = re.compile(
    r"^\s*(?:static\s+)?(?:async\s+)?(?:get\s+|set\s+)?(\w+)\s*\(", re.MULTILINE
)
_JSDOC_RE = re.compile(r"/\*\*.*?\*/", re.DOTALL)


def chunk_js_ts(source: str, path: str) -> list[Chunk]:
    stem = _file_stem(path)
    ext = PurePosixPath(path).suffix.lower()
    lang = _ext_language(ext)
    lines = source.splitlines()
    chunks: list[Chunk] = []

    # Collect import/require lines as __imports__ chunk
    import_lines = [l for l in lines if _RE_JS_IMPORT.match(l)]
    if import_lines:
        breadcrumb = f"{stem} > imports"
        chunks.append(Chunk(
            id=f"{path}::__imports__",
            path=path,
            kind="code",
            language=lang,
            lines=(1, len(import_lines)),
            section=breadcrumb,
            text=f"{breadcrumb}\n\n" + "\n".join(import_lines),
        ))

    doc_ends: dict[int, str] = {}
    for m in _JSDOC_RE.finditer(source):
        end_line = source[:m.end()].count("\n")
        doc_ends[end_line] = _strip_javadoc(m.group(0))

    current_class: Optional[str] = None
    i = 0
    try:
        while i < len(lines):
            line = lines[i]

            cm = _JS_CLASS_RE.match(line)
            if cm:
                current_class = cm.group(1)
                breadcrumb = f"{stem} > {current_class}"
                doc_text = next((doc_ends[k] for k in range(i, i - 3, -1) if k in doc_ends), None)
                if doc_text:
                    chunks.append(Chunk(
                        id=f"{path}::{current_class}.__doc__",
                        path=path,
                        kind="doc",
                        language=lang,
                        lines=(max(1, i), i + 1),
                        section=breadcrumb,
                        text=f"{breadcrumb}\n\n{doc_text}",
                    ))
                i += 1
                continue

            fm = _JS_FUNC_RE.match(line) or _JS_ARROW_RE.match(line)
            if fm:
                func_name = fm.group(1)
                qname = f"{current_class}.{func_name}" if current_class else func_name
                breadcrumb = f"{stem} > {qname}"
                body_lines = [line]
                depth = line.count("{") - line.count("}")
                j = i + 1
                while j < len(lines) and (depth > 0 or j == i + 1):
                    body_lines.append(lines[j])
                    depth += lines[j].count("{") - lines[j].count("}")
                    j += 1
                    if depth <= 0 and j > i + 2:
                        break
                code_text = "\n".join(body_lines)
                doc_text = next((doc_ends[k] for k in range(i, i - 3, -1) if k in doc_ends), None)
                if doc_text:
                    chunks.append(Chunk(
                        id=f"{path}::{qname}.__doc__",
                        path=path,
                        kind="doc",
                        language=lang,
                        lines=(max(1, i), i + 1),
                        section=breadcrumb,
                        text=f"{breadcrumb}\n\n{doc_text}",
                    ))
                chunks.append(Chunk(
                    id=f"{path}::{qname}",
                    path=path,
                    kind="code",
                    language=lang,
                    lines=(i + 1, j),
                    section=breadcrumb,
                    text=code_text,
                ))
                i = j
                continue

            # Top-level export const declarations at column 0 (styled-components, etc.)
            if not current_class:
                ecm = _JS_EXPORT_CONST_RE.match(line)
                if ecm:
                    const_name = ecm.group(1)
                    breadcrumb = f"{stem} > {const_name}"
                    body_lines = [line]
                    # Collect until next top-level `export const` at column 0 or EOF
                    j = i + 1
                    while j < len(lines):
                        if _JS_EXPORT_CONST_RE.match(lines[j]):
                            break
                        # Also stop at top-level class/function declarations
                        if _JS_CLASS_RE.match(lines[j]) or _JS_FUNC_RE.match(lines[j]):
                            break
                        body_lines.append(lines[j])
                        j += 1
                    code_text = "\n".join(body_lines)
                    doc_text = next((doc_ends[k] for k in range(i, i - 3, -1) if k in doc_ends), None)
                    if doc_text:
                        chunks.append(Chunk(
                            id=f"{path}::{const_name}.__doc__",
                            path=path,
                            kind="doc",
                            language=lang,
                            lines=(max(1, i), i + 1),
                            section=breadcrumb,
                            text=f"{breadcrumb}\n\n{doc_text}",
                        ))
                    chunks.append(Chunk(
                        id=f"{path}::{const_name}",
                        path=path,
                        kind="code",
                        language=lang,
                        lines=(i + 1, j),
                        section=breadcrumb,
                        text=code_text,
                    ))
                    i = j
                    continue

            if current_class:
                mm = _JS_METHOD_RE.match(line)
                if mm and mm.group(1) not in {"if", "for", "while", "switch", "catch", "constructor"}:
                    method_name = mm.group(1)
                    qname = f"{current_class}.{method_name}"
                    breadcrumb = f"{stem} > {qname}"
                    body_lines = [line]
                    depth = line.count("{") - line.count("}")
                    j = i + 1
                    while j < len(lines) and (depth > 0 or j == i + 1):
                        body_lines.append(lines[j])
                        depth += lines[j].count("{") - lines[j].count("}")
                        j += 1
                        if depth <= 0 and j > i + 2:
                            break
                    doc_text = next((doc_ends[k] for k in range(i, i - 3, -1) if k in doc_ends), None)
                    if doc_text:
                        chunks.append(Chunk(
                            id=f"{path}::{qname}.__doc__",
                            path=path,
                            kind="doc",
                            language=lang,
                            lines=(max(1, i), i + 1),
                            section=breadcrumb,
                            text=f"{breadcrumb}\n\n{doc_text}",
                        ))
                    chunks.append(Chunk(
                        id=f"{path}::{qname}",
                        path=path,
                        kind="code",
                        language=lang,
                        lines=(i + 1, j),
                        section=breadcrumb,
                        text="\n".join(body_lines),
                    ))
                    i = j
                    continue

            i += 1
    except Exception:
        return _fallback_with_stem(source, path, lang)

    if not chunks:
        return _fallback_with_stem(source, path, lang)
    return split_large_code_chunks(_merge_small_chunks(chunks))


# ---------------------------------------------------------------------------
# C / C++ chunker
# ---------------------------------------------------------------------------

_C_FUNC_RE = re.compile(
    r"^(?!#|//|/\*)(?:\w+(?:\s*\*+\s*|\s+))+(\w+)\s*\([^;{]*\)\s*(?:const\s*)?\{",
    re.MULTILINE,
)
_C_CLASS_RE = re.compile(r"^\s*(?:class|struct)\s+(\w+)", re.MULTILINE)
_CDOC_RE = re.compile(r"(?:/\*\*.*?\*/|(?:[ \t]*///[^\n]*\n)+)", re.DOTALL)


def chunk_c_cpp(source: str, path: str) -> list[Chunk]:
    ext = PurePosixPath(path).suffix.lower()
    lang = _ext_language(ext)
    stem = _file_stem(path)
    lines = source.splitlines()
    chunks: list[Chunk] = []

    # Collect #include / #import lines as __imports__ chunk
    import_lines = [l for l in lines if _RE_C_INCLUDE.match(l)]
    if import_lines:
        breadcrumb = f"{stem} > imports"
        chunks.append(Chunk(
            id=f"{path}::__imports__",
            path=path,
            kind="code",
            language=lang,
            lines=(1, len(import_lines)),
            section=breadcrumb,
            text=f"{breadcrumb}\n\n" + "\n".join(import_lines),
        ))

    doc_ends: dict[int, str] = {}
    for m in _CDOC_RE.finditer(source):
        end_line = source[:m.end()].count("\n")
        raw = m.group(0)
        if raw.startswith("/**"):
            doc_ends[end_line] = _strip_javadoc(raw)
        else:
            doc_ends[end_line] = _strip_line_doc_comments(raw.splitlines(), "///")

    current_class: Optional[str] = None
    i = 0
    try:
        while i < len(lines):
            line = lines[i]
            cm = _C_CLASS_RE.match(line)
            if cm:
                current_class = cm.group(1)
                breadcrumb = f"{stem} > {current_class}"
                decl_text = _collect_decl_text(lines, i)
                chunks.append(Chunk(
                    id=f"{path}::{current_class}.__decl__",
                    path=path,
                    kind="code",
                    language=lang,
                    lines=(i + 1, i + 1),
                    section=breadcrumb,
                    text=f"{breadcrumb}\n\n{decl_text}",
                ))
                i += 1
                continue

            fm = _C_FUNC_RE.match(line)
            if fm:
                func_name = fm.group(1)
                if func_name in {"if", "for", "while", "switch", "else", "do"}:
                    i += 1
                    continue
                qname = f"{current_class}.{func_name}" if current_class else func_name
                breadcrumb = f"{stem} > {qname}"
                body_lines = [line]
                depth = line.count("{") - line.count("}")
                j = i + 1
                while j < len(lines) and depth > 0:
                    body_lines.append(lines[j])
                    depth += lines[j].count("{") - lines[j].count("}")
                    j += 1
                code_text = "\n".join(body_lines)
                doc_text = doc_ends.get(i)
                if doc_text:
                    chunks.append(Chunk(
                        id=f"{path}::{qname}.__doc__",
                        path=path,
                        kind="doc",
                        language=lang,
                        lines=(max(1, i), i + 1),
                        section=breadcrumb,
                        text=f"{breadcrumb}\n\n{doc_text}",
                    ))
                chunks.append(Chunk(
                    id=f"{path}::{qname}",
                    path=path,
                    kind="code",
                    language=lang,
                    lines=(i + 1, j),
                    section=breadcrumb,
                    text=code_text,
                ))
                i = j
                continue
            i += 1
    except Exception:
        return _fallback_with_stem(source, path, lang)

    if not chunks:
        return _fallback_with_stem(source, path, lang)
    return split_large_code_chunks(_merge_small_chunks(chunks))


# ---------------------------------------------------------------------------
# HTML chunker
# ---------------------------------------------------------------------------

_HTML_LANDMARK_RE = re.compile(
    r"<(section|article|nav|main|header|footer|h[1-6])(?:\s[^>]*)?>",
    re.IGNORECASE,
)
_HTML_ID_RE = re.compile(r'\bid=["\']([^"\']+)["\']', re.IGNORECASE)


def chunk_html(source: str, path: str) -> list[Chunk]:
    stem = _file_stem(path)
    lines = source.splitlines()
    chunks: list[Chunk] = []

    try:
        sections: list[tuple[str, int, list[str]]] = []
        current_tag: Optional[str] = None
        current_start = 1
        current_lines: list[str] = []

        for i, line in enumerate(lines, start=1):
            m = _HTML_LANDMARK_RE.search(line)
            if m:
                if current_lines and current_tag:
                    sections.append((current_tag, current_start, current_lines))
                tag = m.group(1).lower()
                id_m = _HTML_ID_RE.search(line)
                current_tag = id_m.group(1) if id_m else tag
                current_start = i
                current_lines = [line]
            elif current_tag is not None:
                current_lines.append(line)

        if current_lines and current_tag:
            sections.append((current_tag, current_start, current_lines))

        if not sections:
            return _fallback_with_stem(source, path, "html")

        for tag, start, sec_lines in sections:
            breadcrumb = f"{stem} > {tag}"
            text = "\n".join(sec_lines).strip()
            if not text:
                continue
            chunks.append(Chunk(
                id=f"{path}#{_slugify(tag)}",
                path=path,
                kind="doc",
                language="html",
                lines=(start, start + len(sec_lines) - 1),
                section=breadcrumb,
                text=f"{breadcrumb}\n\n{text}",
            ))
    except Exception:
        return _fallback_with_stem(source, path, "html")

    if not chunks:
        return _fallback_with_stem(source, path, "html")
    return split_large_code_chunks(chunks)


# ---------------------------------------------------------------------------
# Go chunker
# ---------------------------------------------------------------------------

_GO_FUNC_RE = re.compile(
    r"^func\s+(?:\((\w+)\s+\*?(\w+)\)\s+)?(\w+)\s*\(", re.MULTILINE
)
_GO_TYPE_RE = re.compile(r"^type\s+(\w+)\s+(?:struct|interface)", re.MULTILINE)


def chunk_go(source: str, path: str) -> list[Chunk]:
    stem = _file_stem(path)
    lines = source.splitlines()
    chunks: list[Chunk] = []

    # Emit __namespace__ chunk for package declaration
    pkg_lines = [l for l in lines if _RE_GO_PKG.match(l)]
    if pkg_lines:
        ns_breadcrumb = f"{stem} > namespace"
        chunks.append(Chunk(
            id=f"{path}::__namespace__",
            path=path,
            kind="code",
            language="go",
            lines=(1, 1),
            section=ns_breadcrumb,
            text=f"{ns_breadcrumb}\n\n" + "\n".join(pkg_lines),
        ))

    # Collect import lines (including multi-line import blocks) as __imports__ chunk
    import_lines: list[str] = []
    in_import_block = False
    for l in lines:
        stripped = l.strip()
        if _RE_GO_IMPORT_BLOCK.match(stripped):
            in_import_block = True
            import_lines.append(l)
        elif in_import_block:
            import_lines.append(l)
            if stripped == ")":
                in_import_block = False
        elif _RE_GO_IMPORT_SINGLE.match(stripped):
            import_lines.append(l)
    if import_lines:
        breadcrumb = f"{stem} > imports"
        chunks.append(Chunk(
            id=f"{path}::__imports__",
            path=path,
            kind="code",
            language="go",
            lines=(1, len(import_lines)),
            section=breadcrumb,
            text=f"{breadcrumb}\n\n" + "\n".join(import_lines),
        ))

    # Build map: line -> adjacent // comment block (no blank line before declaration)
    comment_blocks: dict[int, str] = {}
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("//"):
            block = []
            j = i
            while j < len(lines) and lines[j].strip().startswith("//"):
                block.append(re.sub(r"^//\s?", "", lines[j].strip()))
                j += 1
            # j now points to the line after the comment block
            if j < len(lines) and not lines[j].strip() == "":
                comment_blocks[j] = "\n".join(block)
            i = j
        else:
            i += 1

    i = 0
    try:
        while i < len(lines):
            line = lines[i]

            tm = _GO_TYPE_RE.match(line)
            if tm:
                type_name = tm.group(1)
                breadcrumb = f"{stem} > {type_name}"
                body_lines = [line]
                depth = line.count("{") - line.count("}")
                j = i + 1
                while j < len(lines) and depth > 0:
                    body_lines.append(lines[j])
                    depth += lines[j].count("{") - lines[j].count("}")
                    j += 1
                chunks.append(Chunk(
                    id=f"{path}::{type_name}",
                    path=path,
                    kind="code",
                    language="go",
                    lines=(i + 1, j),
                    section=breadcrumb,
                    text="\n".join(body_lines),
                ))
                doc = comment_blocks.get(i)
                if doc:
                    chunks.append(Chunk(
                        id=f"{path}::{type_name}.__doc__",
                        path=path,
                        kind="doc",
                        language="go",
                        lines=(max(1, i), i + 1),
                        section=breadcrumb,
                        text=f"{breadcrumb}\n\n{doc}",
                    ))
                i = j
                continue

            fm = _GO_FUNC_RE.match(line)
            if fm:
                receiver_type = fm.group(2)
                func_name = fm.group(3)
                if receiver_type:
                    qname = f"{receiver_type}.{func_name}"
                else:
                    qname = func_name
                breadcrumb = f"{stem} > {qname}"
                body_lines = [line]
                depth = line.count("{") - line.count("}")
                j = i + 1
                while j < len(lines) and (depth > 0 or j == i + 1):
                    body_lines.append(lines[j])
                    depth += lines[j].count("{") - lines[j].count("}")
                    j += 1
                    if depth <= 0:
                        break
                doc = comment_blocks.get(i)
                if doc:
                    chunks.append(Chunk(
                        id=f"{path}::{qname}.__doc__",
                        path=path,
                        kind="doc",
                        language="go",
                        lines=(max(1, i), i + 1),
                        section=breadcrumb,
                        text=f"{breadcrumb}\n\n{doc}",
                    ))
                chunks.append(Chunk(
                    id=f"{path}::{qname}",
                    path=path,
                    kind="code",
                    language="go",
                    lines=(i + 1, j),
                    section=breadcrumb,
                    text="\n".join(body_lines),
                ))
                i = j
                continue

            i += 1
    except Exception:
        return _fallback_with_stem(source, path, "go")

    if not chunks:
        return _fallback_with_stem(source, path, "go")
    return split_large_code_chunks(_merge_small_chunks(chunks))


# ---------------------------------------------------------------------------
# Rust chunker
# ---------------------------------------------------------------------------

_RUST_IMPL_RE = re.compile(r"^impl(?:<[^>]+>)?(?:\s+\S+\s+for)?\s+(\w+)", re.MULTILINE)
_RUST_FN_RE = re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*[\(<]", re.MULTILINE)
_RUST_STRUCT_RE = re.compile(r"^(?:pub\s+)?(?:struct|trait|enum)\s+(\w+)", re.MULTILINE)
_RUST_DOC_RE = re.compile(r"((?:[ \t]*///[^\n]*\n)+)", re.MULTILINE)
_RUST_INNER_DOC_RE = re.compile(r"((?:[ \t]*//![^\n]*\n)+)", re.MULTILINE)
_RUST_ATTR_RE = re.compile(r"^\s*#\[([^\]]+)\]")


def chunk_rust(source: str, path: str) -> list[Chunk]:
    stem = _file_stem(path)
    lines = source.splitlines()
    chunks: list[Chunk] = []

    # Collect use/extern crate lines as __imports__ chunk
    import_lines = [l for l in lines if _RE_RUST_USE.match(l)]
    if import_lines:
        breadcrumb = f"{stem} > imports"
        chunks.append(Chunk(
            id=f"{path}::__imports__",
            path=path,
            kind="code",
            language="rust",
            lines=(1, len(import_lines)),
            section=breadcrumb,
            text=f"{breadcrumb}\n\n" + "\n".join(import_lines),
        ))

    # Build doc comment map
    doc_ends: dict[int, str] = {}
    for m in _RUST_DOC_RE.finditer(source):
        end_line = source[:m.end()].count("\n")
        doc_ends[end_line] = _strip_line_doc_comments(m.group(1).splitlines(), "///")
    for m in _RUST_INNER_DOC_RE.finditer(source):
        end_line = source[:m.end()].count("\n")
        doc_ends[end_line] = _strip_line_doc_comments(m.group(1).splitlines(), "//!")

    # File-level inner doc chunk
    inner_doc = doc_ends.get(0)
    if inner_doc:
        chunks.append(Chunk(
            id=f"{path}::__doc__",
            path=path,
            kind="doc",
            language="rust",
            lines=(1, 1),
            section=stem,
            text=f"{stem}\n\n{inner_doc}",
        ))

    current_impl: Optional[str] = None
    i = 0
    try:
        while i < len(lines):
            line = lines[i]

            # Track impl blocks and emit a declaration chunk
            im = _RUST_IMPL_RE.match(line)
            if im:
                current_impl = im.group(1)
                breadcrumb = f"{stem} > {current_impl}"
                impl_decl = _collect_decl_text(lines, i)
                chunks.append(Chunk(
                    id=f"{path}::{current_impl}.__impl__",
                    path=path,
                    kind="code",
                    language="rust",
                    lines=(i + 1, i + 1),
                    section=breadcrumb,
                    text=f"{breadcrumb}\n\n{impl_decl}",
                ))
                i += 1
                continue

            sm = _RUST_STRUCT_RE.match(line)
            if sm:
                type_name = sm.group(1)
                breadcrumb = f"{stem} > {type_name}"
                body_lines = [line]
                depth = line.count("{") - line.count("}")
                j = i + 1
                while j < len(lines) and depth > 0:
                    body_lines.append(lines[j])
                    depth += lines[j].count("{") - lines[j].count("}")
                    j += 1
                doc = doc_ends.get(i)
                if doc:
                    chunks.append(Chunk(
                        id=f"{path}::{type_name}.__doc__",
                        path=path,
                        kind="doc",
                        language="rust",
                        lines=(max(1, i), i + 1),
                        section=breadcrumb,
                        text=f"{breadcrumb}\n\n{doc}",
                    ))
                chunks.append(Chunk(
                    id=f"{path}::{type_name}",
                    path=path,
                    kind="code",
                    language="rust",
                    lines=(i + 1, j),
                    section=breadcrumb,
                    text="\n".join(body_lines),
                ))
                i = j
                continue

            fm = _RUST_FN_RE.match(line)
            if fm:
                fn_name = fm.group(1)
                if current_impl:
                    qname = f"{current_impl}.{fn_name}"
                else:
                    qname = fn_name
                breadcrumb = f"{stem} > {qname}"
                body_lines = [line]
                depth = line.count("{") - line.count("}")
                j = i + 1
                while j < len(lines) and (depth > 0 or j == i + 1):
                    body_lines.append(lines[j])
                    depth += lines[j].count("{") - lines[j].count("}")
                    j += 1
                    if depth <= 0:
                        break
                doc = doc_ends.get(i)
                if doc:
                    chunks.append(Chunk(
                        id=f"{path}::{qname}.__doc__",
                        path=path,
                        kind="doc",
                        language="rust",
                        lines=(max(1, i), i + 1),
                        section=breadcrumb,
                        text=f"{breadcrumb}\n\n{doc}",
                    ))
                chunks.append(Chunk(
                    id=f"{path}::{qname}",
                    path=path,
                    kind="code",
                    language="rust",
                    lines=(i + 1, j),
                    section=breadcrumb,
                    text="\n".join(body_lines),
                ))
                i = j
                continue

            i += 1
    except Exception:
        return _fallback_with_stem(source, path, "rust")

    if not chunks:
        return _fallback_with_stem(source, path, "rust")
    return split_large_code_chunks(_merge_small_chunks(chunks))


# ---------------------------------------------------------------------------
# Shell chunker
# ---------------------------------------------------------------------------

_SHELL_FUNC_RE = re.compile(r"^(?:function\s+)?(\w+)\s*\(\s*\)\s*\{", re.MULTILINE)
_FISH_FUNC_RE = re.compile(r"^function\s+(\w+)", re.MULTILINE)


def chunk_shell(source: str, path: str) -> list[Chunk]:
    ext = PurePosixPath(path).suffix.lower()
    lang = _ext_language(ext) if ext else "shell"
    stem = _file_stem(path)
    lines = source.splitlines()
    chunks: list[Chunk] = []
    is_fish = lang == "fish"

    # Build comment blocks: map line_index -> comment text for heuristic doc chunks
    comment_before: dict[int, str] = {}
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("#"):
            block = []
            j = i
            while j < len(lines) and lines[j].strip().startswith("#"):
                block.append(re.sub(r"^#\s?", "", lines[j].strip()))
                j += 1
            if j < len(lines) and not lines[j].strip() == "":
                comment_before[j] = "\n".join(block)
            i = j
        else:
            i += 1

    i = 0
    try:
        if is_fish:
            while i < len(lines):
                line = lines[i]
                fm = _FISH_FUNC_RE.match(line)
                if fm:
                    func_name = fm.group(1)
                    breadcrumb = f"{stem} > {func_name}"
                    body_lines = [line]
                    j = i + 1
                    while j < len(lines) and not re.match(r"^end\b", lines[j].strip()):
                        body_lines.append(lines[j])
                        j += 1
                    if j < len(lines):
                        body_lines.append(lines[j])
                        j += 1
                    doc = comment_before.get(i)
                    if doc:
                        chunks.append(Chunk(
                            id=f"{path}::{func_name}.__doc__",
                            path=path,
                            kind="doc",
                            language="fish",
                            lines=(max(1, i), i + 1),
                            section=breadcrumb,
                            text=f"{breadcrumb}\n\n[inferred from comments]\n{doc}",
                        ))
                    chunks.append(Chunk(
                        id=f"{path}::{func_name}",
                        path=path,
                        kind="code",
                        language="fish",
                        lines=(i + 1, j),
                        section=breadcrumb,
                        text="\n".join(body_lines),
                    ))
                    i = j
                else:
                    i += 1
        else:
            while i < len(lines):
                line = lines[i]
                fm = _SHELL_FUNC_RE.match(line)
                if fm:
                    func_name = fm.group(1)
                    breadcrumb = f"{stem} > {func_name}"
                    body_lines = [line]
                    depth = line.count("{") - line.count("}")
                    j = i + 1
                    while j < len(lines) and depth > 0:
                        body_lines.append(lines[j])
                        depth += lines[j].count("{") - lines[j].count("}")
                        j += 1
                    doc = comment_before.get(i)
                    if doc:
                        chunks.append(Chunk(
                            id=f"{path}::{func_name}.__doc__",
                            path=path,
                            kind="doc",
                            language=lang,
                            lines=(max(1, i), i + 1),
                            section=breadcrumb,
                            text=f"{breadcrumb}\n\n[inferred from comments]\n{doc}",
                        ))
                    chunks.append(Chunk(
                        id=f"{path}::{func_name}",
                        path=path,
                        kind="code",
                        language=lang,
                        lines=(i + 1, j),
                        section=breadcrumb,
                        text="\n".join(body_lines),
                    ))
                    i = j
                else:
                    i += 1
    except Exception:
        return _fallback_with_stem(source, path, lang)

    if not chunks:
        return _fallback_with_stem(source, path, lang)
    return split_large_code_chunks(_merge_small_chunks(chunks))


# ---------------------------------------------------------------------------
# SQL chunker
# ---------------------------------------------------------------------------

_SQL_DDL_RE = re.compile(
    r"^\s*CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW|FUNCTION|PROCEDURE|INDEX)\s+((?:\w+\.)?\w+)",
    re.IGNORECASE | re.MULTILINE,
)
_SQL_COMMENT_RE = re.compile(r"((?:[ \t]*--[^\n]*\n)+|/\*.*?\*/)", re.DOTALL)
_SQL_ANON_BLOCK_RE = re.compile(
    r"(?ims)^[ \t]*DO\b\s*(?P<tag>\$\$|\$[A-Za-z_][\w]*\$)(?P<body>.*?)(?P=tag)(?:\s+LANGUAGE\s+\w+)?\s*;",
)
_SQL_STRUCTURAL_NAME_PATTERNS = [
    re.compile(r"^\s*CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW|FUNCTION|PROCEDURE|INDEX|SCHEMA|TRIGGER|TYPE)\s+((?:\w+\.)?\w+)", re.IGNORECASE),
    re.compile(r"^\s*ALTER\s+(?:TABLE|VIEW|FUNCTION|PROCEDURE|INDEX|SCHEMA|TRIGGER|TYPE)\s+((?:\w+\.)?\w+)", re.IGNORECASE),
    re.compile(r"^\s*DROP\s+(?:TABLE|VIEW|FUNCTION|PROCEDURE|INDEX|SCHEMA|TRIGGER|TYPE)\s+((?:\w+\.)?\w+)", re.IGNORECASE),
]


def _sql_statement_name(text: str, fallback: str) -> str:
    for pattern in _SQL_STRUCTURAL_NAME_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return fallback


def _sql_anonymous_block_chunks(source: str, path: str, stem: str, doc_ends: dict[int, str]) -> tuple[list[Chunk], list[tuple[int, int]]]:
    chunks: list[Chunk] = []
    ranges: list[tuple[int, int]] = []
    for index, match in enumerate(_SQL_ANON_BLOCK_RE.finditer(source)):
        start = source[:match.start()].count("\n") + 1
        end = source[:match.end()].count("\n") + 1
        ranges.append((start, end))
        name = f"anonymous_block@line_{start}"
        breadcrumb = f"{stem} > {name}"
        doc_text = doc_ends.get(start - 1)
        if doc_text:
            chunks.append(Chunk(
                id=f"{path}::{name}.__doc__",
                path=path,
                kind="doc",
                language="sql",
                lines=(max(1, start - 1), start),
                section=breadcrumb,
                text=f"{breadcrumb}\n\n{doc_text}",
            ))
        chunks.append(Chunk(
            id=f"{path}::{name}",
            path=path,
            kind="code",
            language="sql",
            lines=(start, end),
            section=breadcrumb,
            text=match.group(0),
        ))
    return chunks, ranges


def _sql_overlaps_ranges(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    return any(not (end < range_start or start > range_end) for range_start, range_end in ranges)


def _sort_sql_chunks(chunks: list[Chunk]) -> list[Chunk]:
    return sorted(
        chunks,
        key=lambda c: (
            c.lines[0] if getattr(c, "lines", None) else 0,
            c.lines[1] if getattr(c, "lines", None) else 0,
            0 if getattr(c, "kind", "") == "doc" else 1,
            getattr(c, "id", ""),
        ),
    )


def _chunk_sql_treesitter(source: str, path: str, tree) -> list[Chunk]:
    stem = _file_stem(path)
    source_lines = source.splitlines()
    chunks: list[Chunk] = []

    doc_ends: dict[int, str] = {}
    for m in _SQL_COMMENT_RE.finditer(source):
        end_line = source[:m.end()].count("\n")
        raw = m.group(0)
        if raw.startswith("--"):
            doc_ends[end_line] = "\n".join(
                re.sub(r"^--\s?", "", l.strip()) for l in raw.splitlines()
            ).strip()
        else:
            doc_ends[end_line] = re.sub(r"/\*|\*/", "", raw).strip()

    anonymous_chunks, anonymous_ranges = _sql_anonymous_block_chunks(source, path, stem, doc_ends)
    chunks.extend(anonymous_chunks)

    def _walk(node):
        node_type = getattr(node, "type", "")
        if node_type in {"comment", "block_comment", "line_comment"}:
            return
        children = list(getattr(node, "children", []) or [])
        if children:
            statement_like = (
                "statement" in node_type
                or "declaration" in node_type
                or node_type in {"select", "insert", "update", "delete", "query"}
            )
            if statement_like and getattr(node, "parent", None) is not None:
                yield node
                return
            for child in children:
                yield from _walk(child)
        elif getattr(node, "parent", None) is not None and any(token in node_type for token in ("statement", "clause", "definition")):
            yield node

    seen: set[tuple[int, int, str]] = set()
    for index, node in enumerate(_walk(tree.root_node)):
        start, end = _ts_node_lines(node)
        if start <= 0 or end <= 0:
            continue
        if _sql_overlaps_ranges(start, end, anonymous_ranges):
            continue
        text = _ts_node_text(node, source_lines)
        if not text.strip():
            continue
        name = _sql_statement_name(text, f"statement_{index + 1}")
        key = (start, end, name)
        if key in seen:
            continue
        seen.add(key)
        breadcrumb = f"{stem} > {name}"
        doc_text = doc_ends.get(start - 1)
        if doc_text:
            chunks.append(Chunk(
                id=f"{path}::{name}.__doc__",
                path=path,
                kind="doc",
                language="sql",
                lines=(max(1, start - 1), start),
                section=breadcrumb,
                text=f"{breadcrumb}\n\n{doc_text}",
            ))
        chunks.append(Chunk(
            id=f"{path}::{name}",
            path=path,
                kind="code",
                language="sql",
                lines=(start, end),
                section=breadcrumb,
                text=text,
        ))

    if not chunks:
        return _chunk_sql_regex(source, path, stem, doc_ends)
    return split_large_code_chunks(_merge_small_chunks(_sort_sql_chunks(chunks), scoped=True))


def _chunk_sql_regex(source: str, path: str, stem: str, doc_ends: dict[int, str]) -> list[Chunk]:
    lines = source.splitlines()
    chunks: list[Chunk] = []

    anonymous_chunks, _ = _sql_anonymous_block_chunks(source, path, stem, doc_ends)
    chunks.extend(anonymous_chunks)

    i = 0
    try:
        while i < len(lines):
            line = lines[i]
            dm = _SQL_DDL_RE.match(line)
            if dm:
                obj_name = dm.group(1)
                breadcrumb = f"{stem} > {obj_name}"
                body_lines = [line]
                # DDL block ends at semicolon
                j = i + 1
                while j < len(lines) and ";" not in lines[j - 1]:
                    body_lines.append(lines[j])
                    j += 1
                code_text = "\n".join(body_lines)
                doc_text = doc_ends.get(i)
                if doc_text:
                    chunks.append(Chunk(
                        id=f"{path}::{obj_name}.__doc__",
                        path=path,
                        kind="doc",
                        language="sql",
                        lines=(max(1, i), i + 1),
                        section=breadcrumb,
                        text=f"{breadcrumb}\n\n{doc_text}",
                    ))
                chunks.append(Chunk(
                    id=f"{path}::{obj_name}",
                    path=path,
                    kind="code",
                    language="sql",
                    lines=(i + 1, j),
                    section=breadcrumb,
                    text=code_text,
                ))
                i = j
                continue
            i += 1
    except Exception:
        return _fallback_with_stem(source, path, "sql")

    if not chunks:
        return _fallback_with_stem(source, path, "sql")
    return split_large_code_chunks(_sort_sql_chunks(chunks))


def chunk_sql(source: str, path: str) -> list[Chunk]:
    stem = _file_stem(path)
    tree = _ts_parse("sql", source)
    if tree is not None:
        try:
            return _chunk_sql_treesitter(source, path, tree)
        except Exception:
            pass
    doc_ends: dict[int, str] = {}
    for m in _SQL_COMMENT_RE.finditer(source):
        end_line = source[:m.end()].count("\n")
        raw = m.group(0)
        if raw.startswith("--"):
            doc_ends[end_line] = "\n".join(
                re.sub(r"^--\s?", "", l.strip()) for l in raw.splitlines()
            ).strip()
        else:
            doc_ends[end_line] = re.sub(r"/\*|\*/", "", raw).strip()
    return _chunk_sql_regex(source, path, stem, doc_ends)


# ---------------------------------------------------------------------------
# Swift chunker
# ---------------------------------------------------------------------------

_SWIFT_TYPE_RE = re.compile(
    r"^\s*(?:(?:public|private|internal|fileprivate|open|final|@objc\s+)?(?:public|private|internal|fileprivate|open|final|\s)*)"
    r"(?:class|struct|enum|protocol|extension)\s+(\w+)",
    re.MULTILINE,
)  # note: @MainActor/@preconcurrency global-actor prefixes not matched; those files fall back to line-window
_SWIFT_FUNC_RE = re.compile(
    r"^\s*(?:(?:public|private|internal|fileprivate|open|override|static|class|mutating|nonmutating|final)\s+)*"
    r"(func|init|deinit)\s+(\w+)?",
    re.MULTILINE,
)
_SWIFT_DOC_RE = re.compile(r"((?:[ \t]*///[^\n]*\n)+)", re.MULTILINE)


def chunk_swift(source: str, path: str) -> list[Chunk]:
    stem = _file_stem(path)
    lines = source.splitlines()
    chunks: list[Chunk] = []

    # Collect import statements as __imports__ chunk
    import_lines = [l for l in lines if _RE_SWIFT_IMPORT.match(l)]
    if import_lines:
        breadcrumb = f"{stem} > imports"
        chunks.append(Chunk(
            id=f"{path}::__imports__",
            path=path,
            kind="code",
            language="swift",
            lines=(1, len(import_lines)),
            section=breadcrumb,
            text=f"{breadcrumb}\n\n" + "\n".join(import_lines),
        ))

    # Build doc comment map: line_index -> stripped doc text
    doc_ends: dict[int, str] = {}
    for m in _SWIFT_DOC_RE.finditer(source):
        end_line = source[:m.end()].count("\n")
        doc_ends[end_line] = _strip_line_doc_comments(m.group(1).splitlines(), "///")

    current_type: Optional[str] = None
    i = 0
    try:
        while i < len(lines):
            line = lines[i]

            tm = _SWIFT_TYPE_RE.match(line)
            if tm:
                current_type = tm.group(1)
                breadcrumb = f"{stem} > {current_type}"
                decl_text = _collect_decl_text(lines, i)
                chunks.append(Chunk(
                    id=f"{path}::{current_type}.__decl__",
                    path=path,
                    kind="code",
                    language="swift",
                    lines=(i + 1, i + 1),
                    section=breadcrumb,
                    text=f"{breadcrumb}\n\n{decl_text}",
                ))
                doc = doc_ends.get(i)
                if doc:
                    chunks.append(Chunk(
                        id=f"{path}::{current_type}.__doc__",
                        path=path,
                        kind="doc",
                        language="swift",
                        lines=(max(1, i), i + 1),
                        section=breadcrumb,
                        text=f"{breadcrumb}\n\n{doc}",
                    ))
                i += 1
                continue

            fm = _SWIFT_FUNC_RE.match(line)
            if fm:
                keyword = fm.group(1)   # "func", "init", or "deinit"
                raw_name = fm.group(2) or keyword  # name after keyword, or keyword itself for init/deinit
                qname = f"{current_type}.{raw_name}" if current_type else raw_name
                breadcrumb = f"{stem} > {qname}"
                body_lines = [line]
                depth = line.count("{") - line.count("}")
                j = i + 1
                while j < len(lines) and (depth > 0 or j == i + 1):
                    body_lines.append(lines[j])
                    depth += lines[j].count("{") - lines[j].count("}")
                    j += 1
                    if depth <= 0 and j > i + 2:
                        break
                doc = doc_ends.get(i)
                if doc:
                    chunks.append(Chunk(
                        id=f"{path}::{qname}.__doc__",
                        path=path,
                        kind="doc",
                        language="swift",
                        lines=(max(1, i), i + 1),
                        section=breadcrumb,
                        text=f"{breadcrumb}\n\n{doc}",
                    ))
                chunks.append(Chunk(
                    id=f"{path}::{qname}",
                    path=path,
                    kind="code",
                    language="swift",
                    lines=(i + 1, j),
                    section=breadcrumb,
                    text="\n".join(body_lines),
                ))
                i = j
                continue

            i += 1
    except Exception:
        return _fallback_with_stem(source, path, "swift")

    if not chunks:
        return _fallback_with_stem(source, path, "swift")
    return split_large_code_chunks(_merge_small_chunks(chunks))


# ---------------------------------------------------------------------------
# Objective-C chunker
# ---------------------------------------------------------------------------

_OBJC_SECTION_RE = re.compile(
    r"^@(?:interface|implementation|protocol)\s+(\w+)", re.MULTILINE
)
_OBJC_METHOD_RE = re.compile(
    r"^\s*[-+]\s*\([^)]+\)\s*(\w+)", re.MULTILINE
)
_OBJC_DOC_RE = re.compile(r"(?:/\*\*.*?\*/|(?:[ \t]*///[^\n]*\n)+)", re.DOTALL)


def chunk_objc(source: str, path: str) -> list[Chunk]:
    stem = _file_stem(path)
    lines = source.splitlines()
    chunks: list[Chunk] = []

    # Collect #import lines as __imports__ chunk
    import_lines = [l for l in lines if _RE_OBJC_IMPORT.match(l)]
    if import_lines:
        breadcrumb = f"{stem} > imports"
        chunks.append(Chunk(
            id=f"{path}::__imports__",
            path=path,
            kind="code",
            language="objc",
            lines=(1, len(import_lines)),
            section=breadcrumb,
            text=f"{breadcrumb}\n\n" + "\n".join(import_lines),
        ))

    # Build doc comment map
    doc_ends: dict[int, str] = {}
    for m in _OBJC_DOC_RE.finditer(source):
        end_line = source[:m.end()].count("\n")
        raw = m.group(0)
        if raw.startswith("/**"):
            doc_ends[end_line] = _strip_javadoc(raw)
        else:
            doc_ends[end_line] = _strip_line_doc_comments(raw.splitlines(), "///")

    current_class: Optional[str] = None
    i = 0
    try:
        while i < len(lines):
            line = lines[i]

            if line.strip() == "@end":
                current_class = None
                i += 1
                continue

            sm = _OBJC_SECTION_RE.match(line)
            if sm:
                current_class = sm.group(1)
                i += 1
                continue

            mm = _OBJC_METHOD_RE.match(line)
            if mm and current_class:
                method_name = mm.group(1)
                qname = f"{current_class}.{method_name}"
                breadcrumb = f"{stem} > {qname}"
                body_lines = [line]
                depth = line.count("{") - line.count("}")
                # body_open: True if the opening brace has been seen on the first line
                body_open = "{" in line
                j = i + 1
                while j < len(lines) and (depth > 0 or (not body_open and j == i + 1)):
                    body_lines.append(lines[j])
                    depth += lines[j].count("{") - lines[j].count("}")
                    body_open = body_open or ("{" in lines[j])
                    j += 1
                    if depth <= 0 and body_open:
                        break
                doc = next((doc_ends[k] for k in range(i, i - 3, -1) if k in doc_ends), None)
                if doc:
                    chunks.append(Chunk(
                        id=f"{path}::{qname}.__doc__",
                        path=path,
                        kind="doc",
                        language="objc",
                        lines=(max(1, i), i + 1),
                        section=breadcrumb,
                        text=f"{breadcrumb}\n\n{doc}",
                    ))
                chunks.append(Chunk(
                    id=f"{path}::{qname}",
                    path=path,
                    kind="code",
                    language="objc",
                    lines=(i + 1, j),
                    section=breadcrumb,
                    text="\n".join(body_lines),
                ))
                i = j
                continue

            i += 1
    except Exception:
        return _fallback_with_stem(source, path, "objc")

    if not chunks:
        return _fallback_with_stem(source, path, "objc")
    return split_large_code_chunks(_merge_small_chunks(chunks))


# ---------------------------------------------------------------------------
# XML / HTML markup chunker (secondary — for .xml, .jsp, .xsd, .svg, etc.)
# ---------------------------------------------------------------------------

_XML_ELEM_RE = re.compile(
    r"<(\w[\w:-]*)(?:\s[^>]*)?>",
    re.IGNORECASE,
)
_XML_ID_RE = re.compile(r'\b(?:id|name)=["\']([^"\']+)["\']', re.IGNORECASE)


def chunk_xml(source: str, path: str) -> list[Chunk]:
    stem = _file_stem(path)
    lines = source.splitlines()
    chunks: list[Chunk] = []

    try:
        sections: list[tuple[str, int, list[str]]] = []
        depth = 0
        current_label: Optional[str] = None
        current_start = 1
        current_lines: list[str] = []

        for i, line in enumerate(lines, start=1):
            m = _XML_ELEM_RE.search(line)
            if m and depth <= 2:
                tag = m.group(1).lower()
                id_m = _XML_ID_RE.search(line)
                label = id_m.group(1) if id_m else tag
                if current_lines and current_label:
                    sections.append((current_label, current_start, current_lines))
                current_label = label
                current_start = i
                current_lines = [line]
                depth += 1
            elif current_label is not None:
                current_lines.append(line)

        if current_lines and current_label:
            sections.append((current_label, current_start, current_lines))

        if not sections:
            return _fallback_with_stem(source, path, "xml")

        for label, start, sec_lines in sections:
            breadcrumb = f"{stem} > {label}"
            text = "\n".join(sec_lines).strip()
            if not text:
                continue
            chunks.append(Chunk(
                id=f"{path}#{_slugify(label)}",
                path=path,
                kind="doc",
                language="xml",
                lines=(start, start + len(sec_lines) - 1),
                section=breadcrumb,
                text=f"{breadcrumb}\n\n{text}",
            ))
    except Exception:
        return _fallback_with_stem(source, path, "xml")

    if not chunks:
        return _fallback_with_stem(source, path, "xml")
    return split_large_code_chunks(chunks)


# ---------------------------------------------------------------------------
# Tree-sitter chunkers
# ---------------------------------------------------------------------------

def _ts_imports_chunk(import_nodes, source_lines: list[str], path: str, lang: str, stem: str) -> Optional[Chunk]:
    """Build an __imports__ chunk from a list of import nodes."""
    if not import_nodes:
        return None
    texts = [_ts_node_text(n, source_lines) for n in import_nodes]
    text = "\n".join(texts)
    start = import_nodes[0].start_point[0] + 1
    end = import_nodes[-1].end_point[0] + 1
    breadcrumb = f"{stem} > imports"
    return Chunk(
        id=f"{path}::__imports__",
        path=path,
        kind="code",
        language=lang,
        lines=(start, end),
        section=breadcrumb,
        text=f"{breadcrumb}\n\n{text}",
    )


def chunk_js_ts_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    """Tree-sitter JS/TS chunker. Returns None if tree-sitter unavailable."""
    ext = PurePosixPath(_normalize_path(path)).suffix.lower()
    lang_key = "typescript" if ext in {".ts", ".tsx"} else "javascript"
    lang = _ext_language(ext)
    stem = _file_stem(path)
    path = _normalize_path(path)

    tree = _ts_parse(lang_key, source)
    if tree is None:
        return None

    source_lines = source.splitlines()
    chunks: list[Chunk] = []
    import_nodes = []

    def _symbol_name(node) -> Optional[str]:
        for child in node.children:
            if child.type == "identifier":
                return source_lines[child.start_point[0]][child.start_point[1]:child.end_point[1]]
        return None

    def _process_node(node, class_name: Optional[str] = None):
        nonlocal import_nodes
        t = node.type

        if t == "import_statement":
            import_nodes.append(node)
            return

        if t in ("function_declaration", "generator_function_declaration"):
            name = _symbol_name(node) or "anonymous"
            qname = f"{class_name}.{name}" if class_name else name
            breadcrumb = f"{stem} > {qname}"
            start, end = _ts_node_lines(node)
            text = _ts_collapse_body(_ts_node_text(node, source_lines))
            chunks.append(Chunk(id=f"{path}::{qname}", path=path, kind="code", language=lang,
                                lines=(start, end), section=breadcrumb, text=text))
            return

        if t == "class_declaration":
            name = _symbol_name(node) or "AnonymousClass"
            breadcrumb = f"{stem} > {name}"
            start, end = _ts_node_lines(node)
            chunks.append(Chunk(id=f"{path}::{name}.__decl__", path=path, kind="code", language=lang,
                                lines=(start, start), section=breadcrumb,
                                text=f"{breadcrumb}\n\nclass {name}"))
            for child in node.children:
                if child.type == "class_body":
                    for member in child.children:
                        if member.type == "method_definition":
                            _process_node(member, class_name=name)
            return

        if t == "method_definition":
            name = _symbol_name(node) or "method"
            qname = f"{class_name}.{name}" if class_name else name
            breadcrumb = f"{stem} > {qname}"
            start, end = _ts_node_lines(node)
            text = _ts_collapse_body(_ts_node_text(node, source_lines))
            chunks.append(Chunk(id=f"{path}::{qname}", path=path, kind="code", language=lang,
                                lines=(start, end), section=breadcrumb, text=text))
            return

        if t == "export_statement":
            # export function Foo / export class Foo / export const Foo = ...
            for child in node.children:
                if child.type in ("function_declaration", "class_declaration",
                                  "generator_function_declaration"):
                    _process_node(child, class_name=class_name)
                    return
                if child.type in ("lexical_declaration", "variable_declaration"):
                    # export const Foo = ...
                    for decl in child.children:
                        if decl.type == "variable_declarator":
                            name = _symbol_name(decl) or "const"
                            qname = f"{class_name}.{name}" if class_name else name
                            breadcrumb = f"{stem} > {qname}"
                            start, end = _ts_node_lines(node)
                            text = _ts_collapse_body(_ts_node_text(node, source_lines))
                            chunks.append(Chunk(id=f"{path}::{qname}", path=path, kind="code",
                                                language=lang, lines=(start, end),
                                                section=breadcrumb, text=text))
                    return
            return

        if t in ("lexical_declaration", "variable_declaration") and class_name is None:
            # Top-level const Foo = () => ...  or const Foo = styled(...)
            for decl in node.children:
                if decl.type == "variable_declarator":
                    # check if value is arrow_function or call_expression (styled)
                    for val in decl.children:
                        if val.type in ("arrow_function", "call_expression",
                                        "template_string", "object"):
                            name = _symbol_name(decl) or "const"
                            breadcrumb = f"{stem} > {name}"
                            start, end = _ts_node_lines(node)
                            text = _ts_collapse_body(_ts_node_text(node, source_lines))
                            chunks.append(Chunk(id=f"{path}::{name}", path=path, kind="code",
                                                language=lang, lines=(start, end),
                                                section=breadcrumb, text=text))
                            break

    for node in tree.root_node.children:
        _process_node(node)

    imp = _ts_imports_chunk(import_nodes, source_lines, path, lang, stem)
    if imp:
        chunks.insert(0, imp)

    if not chunks:
        return None
    return split_large_code_chunks(_merge_small_chunks(chunks, scoped=True))


def chunk_go_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    """Tree-sitter Go chunker. Returns None if unavailable."""
    path = _normalize_path(path)
    stem = _file_stem(path)
    tree = _ts_parse("go", source)
    if tree is None:
        return None

    source_lines = source.splitlines()
    chunks: list[Chunk] = []
    import_nodes = []

    def _name(node) -> str:
        for c in node.children:
            if c.type in ("identifier", "field_identifier", "type_identifier"):
                return source_lines[c.start_point[0]][c.start_point[1]:c.end_point[1]]
        return "unknown"

    for node in tree.root_node.children:
        t = node.type
        if t == "package_clause":
            breadcrumb = f"{stem} > namespace"
            chunks.append(Chunk(id=f"{path}::__namespace__", path=path, kind="code",
                                language="go", lines=_ts_node_lines(node), section=breadcrumb,
                                text=f"{breadcrumb}\n\n{_ts_node_text(node, source_lines)}"))
        elif t == "import_declaration":
            import_nodes.append(node)
        elif t == "function_declaration":
            name = _name(node)
            breadcrumb = f"{stem} > {name}"
            start, end = _ts_node_lines(node)
            text = _ts_collapse_body(_ts_node_text(node, source_lines))
            chunks.append(Chunk(id=f"{path}::{name}", path=path, kind="code", language="go",
                                lines=(start, end), section=breadcrumb, text=text))
        elif t == "method_declaration":
            # receiver type + method name
            recv_type = ""
            method_name = ""
            for c in node.children:
                if c.type == "parameter_list":
                    for rc in c.children:
                        if rc.type == "parameter_declaration":
                            for tc in rc.children:
                                if tc.type in ("type_identifier", "pointer_type"):
                                    if tc.type == "pointer_type":
                                        for ptc in tc.children:
                                            if ptc.type == "type_identifier":
                                                recv_type = source_lines[ptc.start_point[0]][ptc.start_point[1]:ptc.end_point[1]]
                                    else:
                                        recv_type = source_lines[tc.start_point[0]][tc.start_point[1]:tc.end_point[1]]
                elif c.type == "field_identifier":
                    method_name = source_lines[c.start_point[0]][c.start_point[1]:c.end_point[1]]
            qname = f"{recv_type}.{method_name}" if recv_type else method_name
            breadcrumb = f"{stem} > {qname}"
            start, end = _ts_node_lines(node)
            text = _ts_collapse_body(_ts_node_text(node, source_lines))
            chunks.append(Chunk(id=f"{path}::{qname}", path=path, kind="code", language="go",
                                lines=(start, end), section=breadcrumb, text=text))
        elif t == "type_declaration":
            name = _name(node)
            breadcrumb = f"{stem} > {name}"
            start, end = _ts_node_lines(node)
            text = _ts_collapse_body(_ts_node_text(node, source_lines))
            chunks.append(Chunk(id=f"{path}::{name}", path=path, kind="code", language="go",
                                lines=(start, end), section=breadcrumb, text=text))

    imp = _ts_imports_chunk(import_nodes, source_lines, path, "go", stem)
    if imp:
        # insert after namespace if present
        insert_idx = 1 if chunks and chunks[0].section and chunks[0].section.endswith("> namespace") else 0
        chunks.insert(insert_idx, imp)

    if not chunks:
        return None
    return split_large_code_chunks(_merge_small_chunks(chunks, scoped=True))


def chunk_rust_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    """Tree-sitter Rust chunker. Returns None if unavailable."""
    path = _normalize_path(path)
    stem = _file_stem(path)
    tree = _ts_parse("rust", source)
    if tree is None:
        return None

    source_lines = source.splitlines()
    chunks: list[Chunk] = []
    import_nodes = []

    def _name(node) -> str:
        for c in node.children:
            if c.type in ("identifier", "type_identifier"):
                return source_lines[c.start_point[0]][c.start_point[1]:c.end_point[1]]
        return "unknown"

    def _process(node, impl_name: Optional[str] = None):
        t = node.type
        if t == "use_declaration":
            import_nodes.append(node)
        elif t in ("struct_item", "enum_item", "trait_item"):
            name = _name(node)
            breadcrumb = f"{stem} > {name}"
            start, end = _ts_node_lines(node)
            text = _ts_collapse_body(_ts_node_text(node, source_lines))
            chunks.append(Chunk(id=f"{path}::{name}", path=path, kind="code", language="rust",
                                lines=(start, end), section=breadcrumb, text=text))
        elif t == "impl_item":
            # find the type name
            iname = None
            for c in node.children:
                if c.type == "type_identifier":
                    iname = source_lines[c.start_point[0]][c.start_point[1]:c.end_point[1]]
                    break
            if not iname:
                iname = "impl"
            breadcrumb = f"{stem} > {iname}"
            decl_line = source_lines[node.start_point[0]]
            chunks.append(Chunk(id=f"{path}::{iname}.__impl__", path=path, kind="code",
                                language="rust", lines=(_ts_node_lines(node)[0],) * 2,
                                section=breadcrumb,
                                text=f"{breadcrumb}\n\n{decl_line.strip()}"))
            for child in node.children:
                if child.type == "declaration_list":
                    for member in child.children:
                        if member.type == "function_item":
                            _process(member, impl_name=iname)
        elif t == "function_item":
            name = _name(node)
            qname = f"{impl_name}.{name}" if impl_name else name
            breadcrumb = f"{stem} > {qname}"
            start, end = _ts_node_lines(node)
            text = _ts_collapse_body(_ts_node_text(node, source_lines))
            chunks.append(Chunk(id=f"{path}::{qname}", path=path, kind="code", language="rust",
                                lines=(start, end), section=breadcrumb, text=text))

    for node in tree.root_node.children:
        _process(node)

    imp = _ts_imports_chunk(import_nodes, source_lines, path, "rust", stem)
    if imp:
        chunks.insert(0, imp)

    if not chunks:
        return None
    return split_large_code_chunks(_merge_small_chunks(chunks, scoped=True))


def chunk_java_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    """Tree-sitter Java chunker. Returns None if unavailable."""
    path = _normalize_path(path)
    stem = _file_stem(path)
    tree = _ts_parse("java", source)
    if tree is None:
        return None

    source_lines = source.splitlines()
    chunks: list[Chunk] = []
    import_nodes = []

    def _name(node) -> str:
        for c in node.children:
            if c.type == "identifier":
                return source_lines[c.start_point[0]][c.start_point[1]:c.end_point[1]]
        return "unknown"

    def _process_class(class_node, class_name: str):
        for child in class_node.children:
            if child.type == "class_body":
                for member in child.children:
                    if member.type in ("method_declaration", "constructor_declaration"):
                        name = _name(member)
                        qname = f"{class_name}.{name}"
                        breadcrumb = f"{stem} > {qname}"
                        start, end = _ts_node_lines(member)
                        text = _ts_collapse_body(_ts_node_text(member, source_lines))
                        chunks.append(Chunk(id=f"{path}::{qname}", path=path, kind="code",
                                            language="java", lines=(start, end),
                                            section=breadcrumb, text=text))

    for node in tree.root_node.children:
        t = node.type
        if t == "package_declaration":
            breadcrumb = f"{stem} > namespace"
            chunks.append(Chunk(id=f"{path}::__namespace__", path=path, kind="code",
                                language="java", lines=_ts_node_lines(node), section=breadcrumb,
                                text=f"{breadcrumb}\n\n{_ts_node_text(node, source_lines)}"))
        elif t == "import_declaration":
            import_nodes.append(node)
        elif t in ("class_declaration", "interface_declaration", "enum_declaration",
                   "annotation_type_declaration"):
            name = _name(node)
            breadcrumb = f"{stem} > {name}"
            start, end = _ts_node_lines(node)
            decl_line = source_lines[node.start_point[0]].strip()
            chunks.append(Chunk(id=f"{path}::{name}.__decl__", path=path, kind="code",
                                language="java", lines=(start, start), section=breadcrumb,
                                text=f"{breadcrumb}\n\n{decl_line}"))
            _process_class(node, name)

    imp = _ts_imports_chunk(import_nodes, source_lines, path, "java", stem)
    if imp:
        insert_idx = 1 if chunks and chunks[0].section and chunks[0].section.endswith("> namespace") else 0
        chunks.insert(insert_idx, imp)

    if not chunks:
        return None
    return split_large_code_chunks(_merge_small_chunks(chunks, scoped=True))


def chunk_c_cpp_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    """Tree-sitter C/C++ chunker. Returns None if unavailable."""
    path = _normalize_path(path)
    ext = PurePosixPath(path).suffix.lower()
    lang_key = "cpp" if ext in {".cpp", ".hpp"} else "c"
    lang = _ext_language(ext)
    stem = _file_stem(path)

    tree = _ts_parse(lang_key, source)
    if tree is None:
        return None

    source_lines = source.splitlines()
    chunks: list[Chunk] = []
    include_nodes = []

    def _name(node) -> str:
        for c in node.children:
            if c.type in ("identifier", "field_identifier", "type_identifier",
                          "function_declarator"):
                if c.type == "function_declarator":
                    for cc in c.children:
                        if cc.type == "identifier":
                            return source_lines[cc.start_point[0]][cc.start_point[1]:cc.end_point[1]]
                return source_lines[c.start_point[0]][c.start_point[1]:c.end_point[1]]
        return "unknown"

    for node in tree.root_node.children:
        t = node.type
        if t == "preproc_include":
            include_nodes.append(node)
        elif t == "function_definition":
            name = _name(node)
            if name in {"if", "for", "while", "switch", "else", "do"}:
                continue
            breadcrumb = f"{stem} > {name}"
            start, end = _ts_node_lines(node)
            text = _ts_collapse_body(_ts_node_text(node, source_lines))
            chunks.append(Chunk(id=f"{path}::{name}", path=path, kind="code", language=lang,
                                lines=(start, end), section=breadcrumb, text=text))
        elif t in ("class_specifier", "struct_specifier"):
            name = _name(node)
            breadcrumb = f"{stem} > {name}"
            start, end = _ts_node_lines(node)
            text = _ts_collapse_body(_ts_node_text(node, source_lines))
            chunks.append(Chunk(id=f"{path}::{name}", path=path, kind="code", language=lang,
                                lines=(start, end), section=breadcrumb, text=text))

    imp = _ts_imports_chunk(include_nodes, source_lines, path, lang, stem)
    if imp:
        chunks.insert(0, imp)

    if not chunks:
        return None
    return split_large_code_chunks(_merge_small_chunks(chunks, scoped=True))


def chunk_csharp_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    """Tree-sitter C# chunker. Returns None if unavailable."""
    path = _normalize_path(path)
    stem = _file_stem(path)
    tree = _ts_parse("csharp", source)
    if tree is None:
        return None

    source_lines = source.splitlines()
    chunks: list[Chunk] = []
    using_nodes = []

    def _name(node) -> str:
        for c in node.children:
            if c.type == "identifier":
                return source_lines[c.start_point[0]][c.start_point[1]:c.end_point[1]]
        return "unknown"

    def _process_type(type_node, type_name: str):
        for child in type_node.children:
            if child.type == "declaration_list":
                for member in child.children:
                    if member.type in ("method_declaration", "constructor_declaration",
                                       "operator_declaration"):
                        name = _name(member)
                        qname = f"{type_name}.{name}"
                        breadcrumb = f"{stem} > {qname}"
                        start, end = _ts_node_lines(member)
                        text = _ts_collapse_body(_ts_node_text(member, source_lines))
                        chunks.append(Chunk(id=f"{path}::{qname}", path=path, kind="code",
                                            language="csharp", lines=(start, end),
                                            section=breadcrumb, text=text))

    def _walk(node):
        t = node.type
        if t == "using_directive":
            using_nodes.append(node)
        elif t == "namespace_declaration":
            for child in node.children:
                if child.type == "declaration_list":
                    for member in child.children:
                        _walk(member)
        elif t in ("class_declaration", "interface_declaration", "struct_declaration",
                   "enum_declaration", "record_declaration"):
            name = _name(node)
            breadcrumb = f"{stem} > {name}"
            start, end = _ts_node_lines(node)
            decl_line = source_lines[node.start_point[0]].strip()
            chunks.append(Chunk(id=f"{path}::{name}.__decl__", path=path, kind="code",
                                language="csharp", lines=(start, start), section=breadcrumb,
                                text=f"{breadcrumb}\n\n{decl_line}"))
            _process_type(node, name)

    for node in tree.root_node.children:
        _walk(node)

    imp = _ts_imports_chunk(using_nodes, source_lines, path, "csharp", stem)
    if imp:
        chunks.insert(0, imp)

    if not chunks:
        return None
    return split_large_code_chunks(_merge_small_chunks(chunks, scoped=True))


def chunk_bash_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    """Tree-sitter Bash chunker. Returns None if unavailable."""
    path = _normalize_path(path)
    stem = _file_stem(path)
    tree = _ts_parse("bash", source)
    if tree is None:
        return None

    source_lines = source.splitlines()
    chunks: list[Chunk] = []
    lang = _ext_language(PurePosixPath(path).suffix.lower()) or "shell"

    def _name(node) -> str:
        for c in node.children:
            if c.type == "word":
                return source_lines[c.start_point[0]][c.start_point[1]:c.end_point[1]]
        return "unknown"

    for node in tree.root_node.children:
        if node.type == "function_definition":
            name = _name(node)
            breadcrumb = f"{stem} > {name}"
            start, end = _ts_node_lines(node)
            text = _ts_collapse_body(_ts_node_text(node, source_lines))
            chunks.append(Chunk(id=f"{path}::{name}", path=path, kind="code", language=lang,
                                lines=(start, end), section=breadcrumb, text=text))

    if not chunks:
        return None
    return split_large_code_chunks(_merge_small_chunks(chunks, scoped=True))


def chunk_kotlin_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    """Tree-sitter Kotlin chunker. Returns None if unavailable."""
    path = _normalize_path(path)
    stem = _file_stem(path)
    tree = _ts_parse("kotlin", source)
    if tree is None:
        return None

    source_lines = source.splitlines()
    chunks: list[Chunk] = []
    import_nodes = []

    def _name(node) -> str:
        for c in node.children:
            if c.type in ("simple_identifier", "identifier"):
                return source_lines[c.start_point[0]][c.start_point[1]:c.end_point[1]]
        return "unknown"

    def _process(node):
        t = node.type
        if t == "package_header":
            breadcrumb = f"{stem} > namespace"
            chunks.append(Chunk(id=f"{path}::__namespace__", path=path, kind="code",
                                language="kotlin", lines=_ts_node_lines(node), section=breadcrumb,
                                text=f"{breadcrumb}\n\n{_ts_node_text(node, source_lines)}"))
        elif t in ("import_list", "import"):
            import_nodes.append(node)
        elif t in ("class_declaration", "object_declaration", "interface_declaration"):
            name = _name(node)
            breadcrumb = f"{stem} > {name}"
            start, end = _ts_node_lines(node)
            decl_line = source_lines[node.start_point[0]].strip()
            chunks.append(Chunk(id=f"{path}::{name}.__decl__", path=path, kind="code",
                                language="kotlin", lines=(start, start), section=breadcrumb,
                                text=f"{breadcrumb}\n\n{decl_line}"))
            for child in node.children:
                if child.type == "class_body":
                    for member in child.children:
                        if member.type in ("function_declaration", "secondary_constructor"):
                            mname = _name(member)
                            qname = f"{name}.{mname}"
                            bc = f"{stem} > {qname}"
                            ms, me = _ts_node_lines(member)
                            text = _ts_collapse_body(_ts_node_text(member, source_lines))
                            chunks.append(Chunk(id=f"{path}::{qname}", path=path, kind="code",
                                                language="kotlin", lines=(ms, me),
                                                section=bc, text=text))
        elif t == "function_declaration":
            name = _name(node)
            breadcrumb = f"{stem} > {name}"
            start, end = _ts_node_lines(node)
            text = _ts_collapse_body(_ts_node_text(node, source_lines))
            chunks.append(Chunk(id=f"{path}::{name}", path=path, kind="code", language="kotlin",
                                lines=(start, end), section=breadcrumb, text=text))

    for node in tree.root_node.children:
        _process(node)

    # import_list is a single node containing all imports — wrap as __imports__ chunk
    if import_nodes:
        all_import_text = "\n".join(_ts_node_text(n, source_lines) for n in import_nodes)
        start = import_nodes[0].start_point[0] + 1
        end = import_nodes[-1].end_point[0] + 1
        breadcrumb = f"{stem} > imports"
        imp = Chunk(id=f"{path}::__imports__", path=path, kind="code", language="kotlin",
                    lines=(start, end), section=breadcrumb,
                    text=f"{breadcrumb}\n\n{all_import_text}")
        insert_idx = 1 if chunks and chunks[0].section and chunks[0].section.endswith("> namespace") else 0
        chunks.insert(insert_idx, imp)

    if not chunks:
        return None
    return split_large_code_chunks(_merge_small_chunks(chunks, scoped=True))


_TS_NAME_CHILD_TYPES = frozenset({
    "identifier", "type_identifier", "simple_identifier", "property_identifier",
    "field_identifier", "name", "function_name", "bare_key", "class_name",
})


def _ts_node_name(node, source_lines: list[str]) -> str:
    """Extract a symbol name from a tree-sitter node."""
    for child in node.children:
        if child.type in _TS_NAME_CHILD_TYPES:
            text = source_lines[child.start_point[0]][child.start_point[1]:child.end_point[1]].strip()
            if text:
                return text
    for child in node.children:
        nested = _ts_node_name(child, source_lines)
        if nested != "anonymous":
            return nested
    return "anonymous"


def _ts_generic_structured_chunker(
    lang_key: str,
    source: str,
    path: str,
    language: str,
    *,
    class_node_types: frozenset[str] = frozenset(),
    method_node_types: frozenset[str] = frozenset(),
    top_level_node_types: frozenset[str] = frozenset(),
    import_node_types: frozenset[str] = frozenset(),
    namespace_node_types: frozenset[str] = frozenset(),
    scoped: bool = True,
) -> Optional[list[Chunk]]:
    """Walk a tree-sitter parse tree and emit declaration-boundary code chunks."""
    path = _normalize_path(path)
    stem = _file_stem(path)
    tree = _ts_parse(lang_key, source)
    if tree is None:
        return None

    source_lines = source.splitlines()
    chunks: list[Chunk] = []
    import_nodes: list = []

    def _emit_code(node, qname: str, *, decl_only: bool = False) -> None:
        breadcrumb = f"{stem} > {qname}"
        start, end = _ts_node_lines(node)
        if decl_only:
            decl_line = source_lines[node.start_point[0]].strip()
            text = f"{breadcrumb}\n\n{decl_line}"
            lines = (start, start)
            chunk_id = f"{path}::{qname}.__decl__"
        else:
            text = _ts_collapse_body(_ts_node_text(node, source_lines))
            lines = (start, end)
            chunk_id = f"{path}::{qname}"
        chunks.append(Chunk(
            id=chunk_id,
            path=path,
            kind="code",
            language=language,
            lines=lines,
            section=breadcrumb,
            text=text,
        ))

    def _walk_class_members(node, class_name: str) -> None:
        for child in node.children:
            if child.type in method_node_types:
                mname = _ts_node_name(child, source_lines)
                qname = f"{class_name}.{mname}" if mname != "anonymous" else class_name
                _emit_code(child, qname)
            elif child.type not in method_node_types:
                _walk_class_members(child, class_name)

    def _process(node, class_name: Optional[str] = None) -> None:
        t = node.type
        if t in import_node_types:
            import_nodes.append(node)
            return
        if t in namespace_node_types:
            breadcrumb = f"{stem} > namespace"
            chunks.append(Chunk(
                id=f"{path}::__namespace__",
                path=path,
                kind="code",
                language=language,
                lines=_ts_node_lines(node),
                section=breadcrumb,
                text=f"{breadcrumb}\n\n{_ts_node_text(node, source_lines)}",
            ))
            return
        if t in class_node_types:
            name = _ts_node_name(node, source_lines)
            _emit_code(node, name, decl_only=True)
            _walk_class_members(node, name)
            return
        if t in method_node_types and class_name:
            mname = _ts_node_name(node, source_lines)
            qname = f"{class_name}.{mname}" if mname != "anonymous" else class_name
            _emit_code(node, qname)
            return
        if t in method_node_types or t in top_level_node_types:
            name = _ts_node_name(node, source_lines)
            _emit_code(node, name)
            return

    for node in tree.root_node.children:
        _process(node)

    imp = _ts_imports_chunk(import_nodes, source_lines, path, language, stem)
    if imp:
        insert_idx = 1 if chunks and chunks[0].section and chunks[0].section.endswith("> namespace") else 0
        chunks.insert(insert_idx, imp)

    if not chunks:
        return None
    return split_large_code_chunks(_merge_small_chunks(chunks, scoped=scoped))


def _ts_flat_emit_chunker(
    lang_key: str,
    source: str,
    path: str,
    language: str,
    emit_node_types: frozenset[str],
) -> Optional[list[Chunk]]:
    """Emit one chunk per matching node type (config / markup flat files)."""
    path = _normalize_path(path)
    stem = _file_stem(path)
    tree = _ts_parse(lang_key, source)
    if tree is None:
        return None

    source_lines = source.splitlines()
    chunks: list[Chunk] = []
    counter = 0

    def _walk(node, inside_emit: bool = False) -> None:
        nonlocal counter
        if node.type in emit_node_types and not inside_emit:
            name = _ts_node_name(node, source_lines)
            slug = _slugify(name) if name != "anonymous" else f"node-{counter}"
            counter += 1
            start, end = _ts_node_lines(node)
            breadcrumb = f"{stem} > {name}" if name != "anonymous" else f"{stem} > {slug}"
            text = _ts_collapse_body(_ts_node_text(node, source_lines))
            chunks.append(Chunk(
                id=f"{path}#{slug}",
                path=path,
                kind="code",
                language=language,
                lines=(start, end),
                section=breadcrumb,
                text=f"{breadcrumb}\n\n{text}",
            ))
            for child in node.children:
                _walk(child, inside_emit=True)
        else:
            for child in node.children:
                _walk(child, inside_emit)

    _walk(tree.root_node)
    if not chunks:
        return None
    return split_large_code_chunks(chunks)


def _ts_markup_chunker(
    lang_key: str,
    source: str,
    path: str,
    language: str,
    *,
    max_depth: int = 4,
) -> Optional[list[Chunk]]:
    """Emit chunks for shallow element nodes in HTML/XML."""
    path = _normalize_path(path)
    stem = _file_stem(path)
    tree = _ts_parse(lang_key, source)
    if tree is None:
        return None

    source_lines = source.splitlines()
    chunks: list[Chunk] = []
    counter = 0

    def _walk(node, depth: int = 0) -> None:
        nonlocal counter
        if node.type == "element" and depth <= max_depth:
            tag = "element"
            for child in node.children:
                if child.type in ("start_tag", "self_closing_tag"):
                    for tc in child.children:
                        if tc.type in ("tag_name", "tag_identifier"):
                            tag = source_lines[tc.start_point[0]][tc.start_point[1]:tc.end_point[1]]
            slug = _slugify(tag) if tag != "element" else f"el-{counter}"
            counter += 1
            start, end = _ts_node_lines(node)
            breadcrumb = f"{stem} > {tag}"
            text = _ts_collapse_body(_ts_node_text(node, source_lines))
            chunks.append(Chunk(
                id=f"{path}#{slug}-L{start}",
                path=path,
                kind="doc",
                language=language,
                lines=(start, end),
                section=breadcrumb,
                text=f"{breadcrumb}\n\n{text}",
            ))
        for child in node.children:
            _walk(child, depth + 1)

    _walk(tree.root_node)
    if not chunks:
        return None
    return split_large_code_chunks(chunks)


def chunk_swift_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    return _ts_generic_structured_chunker(
        "swift", source, path, "swift",
        class_node_types=frozenset({"class_declaration", "protocol_declaration"}),
        method_node_types=frozenset({
            "function_declaration", "init_declaration", "deinit_declaration",
            "protocol_function_declaration",
        }),
        top_level_node_types=frozenset({
            "function_declaration", "init_declaration", "deinit_declaration",
        }),
        import_node_types=frozenset({"import_declaration"}),
    )


def chunk_objc_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    return _ts_generic_structured_chunker(
        "objc", source, path, "objc",
        class_node_types=frozenset({"class_interface", "class_implementation", "category_interface", "category_implementation"}),
        method_node_types=frozenset({"method_declaration", "method_definition"}),
        import_node_types=frozenset({"preproc_include", "preproc_import"}),
    )


def chunk_scala_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    return _ts_generic_structured_chunker(
        "scala", source, path, "scala",
        class_node_types=frozenset({"object_definition", "class_definition", "trait_definition"}),
        method_node_types=frozenset({"function_definition"}),
        import_node_types=frozenset({"import_declaration"}),
        namespace_node_types=frozenset({"package_clause"}),
    )


def chunk_ruby_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    return _ts_generic_structured_chunker(
        "ruby", source, path, "ruby",
        class_node_types=frozenset({"class", "module", "singleton_class"}),
        method_node_types=frozenset({"method", "singleton_method"}),
    )


def chunk_php_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    return _ts_generic_structured_chunker(
        "php", source, path, "php",
        class_node_types=frozenset({"class_declaration", "interface_declaration", "trait_declaration", "enum_declaration"}),
        method_node_types=frozenset({"function_definition", "method_declaration"}),
        namespace_node_types=frozenset({"namespace_definition"}),
    )


def chunk_hcl_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    return _ts_flat_emit_chunker("hcl", source, path, "terraform", frozenset({"block", "attribute"}))


def chunk_scss_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    return _ts_flat_emit_chunker("scss", source, path, "scss", frozenset({"rule_set", "declaration"}))


def chunk_css_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    return _ts_flat_emit_chunker("css", source, path, "css", frozenset({"rule_set", "declaration"}))


def chunk_make_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    return _ts_flat_emit_chunker("make", source, path, "make", frozenset({"rule"}))


def chunk_yaml_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    return _ts_flat_emit_chunker("yaml", source, path, "yaml", frozenset({"block_mapping_pair", "flow_pair"}))


def chunk_toml_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    return _ts_flat_emit_chunker("toml", source, path, "toml", frozenset({"table", "table_array_element"}))


def chunk_json_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    return _ts_flat_emit_chunker("json", source, path, "json", frozenset({"pair"}))


def chunk_powershell_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    return _ts_generic_structured_chunker(
        "powershell", source, path, "powershell",
        top_level_node_types=frozenset({"function_statement", "class_statement"}),
    )


def chunk_html_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    return _ts_markup_chunker("html", source, path, "html")


def chunk_xml_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    return _ts_markup_chunker("xml", source, path, "xml")


def _ts_dispatch(
    ts_fn,
    regex_fn,
    source: str,
    path: str,
    language: str,
    *,
    with_summary: bool = False,
) -> list[Chunk]:
    """Try tree-sitter chunker, fall back to regex_fn or line-window."""
    ts_result = ts_fn(source, path)
    if ts_result is not None:
        chunks = ts_result
    elif regex_fn is not None:
        chunks = regex_fn(source, path)
    else:
        chunks = chunk_line_window(source, path, language=language, section=_file_stem(path))
    if with_summary:
        s = _chunk_code_summary(source, path, language)
        return ([s] + chunks) if s else chunks
    return chunks


# ---------------------------------------------------------------------------
# Top-level dispatcher
# ---------------------------------------------------------------------------

def _chunk_design_json(source: str, path: str) -> list[Chunk]:
    """Chunk a docs/design-system/**/*.json file as doc-kind chunks via the markdown chunker.

    Falls back to line-window chunking when the source is not valid JSON so a
    malformed file never raises and still produces searchable chunks.
    """
    import json as _json
    try:
        _json.loads(source)
    except (ValueError, TypeError):
        return chunk_line_window(source, path, language="json")

    # Render the JSON as indented text and treat it like a markdown doc section
    # so it is indexed as kind="doc" and findable via docs_search.
    try:
        pretty = _json.dumps(_json.loads(source), indent=2, ensure_ascii=False)
    except Exception:
        return chunk_line_window(source, path, language="json")

    lines = pretty.splitlines()
    if not lines:
        return []
    return [Chunk(
        id=f"{path}#root",
        path=path,
        kind="doc",
        language="json",
        lines=(1, len(lines)),
        section=None,
        text=pretty,
    )]


_SUMMARY_SYMBOL_CAP = 20

# Pre-compiled heading pattern for doc-summary extraction (all levels).
_DOC_HEADING_RE = re.compile(r"^#{1,3}\s+(.+)$")

# Matches frontmatter key-value lines: "Key: value" or "Key: `value`"
_FRONTMATTER_LINE_RE = re.compile(r"^\w[\w\s\-]*:\s+\S")

# Per-language pre-compiled regex patterns for top-level exported symbols.
_SYMBOL_PATTERNS: dict[str, list[re.Pattern]] = {
    "python": [re.compile(r"^(?:def|class|async def)\s+(\w+)")],
    "javascript": [re.compile(r"^export\s+(?:default\s+)?(?:function|class|const|let|var)\s+(\w+)"), re.compile(r"^(?:function|class)\s+(\w+)")],
    "typescript": [re.compile(r"^export\s+(?:default\s+)?(?:function|class|const|let|var|type|interface|enum)\s+(\w+)"), re.compile(r"^(?:function|class)\s+(\w+)")],
    "go": [re.compile(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)"), re.compile(r"^type\s+(\w+)")],
    "rust": [re.compile(r"^pub\s+(?:fn|struct|enum|trait|type|const)\s+(\w+)"), re.compile(r"^(?:fn|struct|enum|trait)\s+(\w+)")],
    "java": [re.compile(r"^(?:public|protected|private)?\s*(?:static\s+)?(?:class|interface|enum)\s+(\w+)"), re.compile(r"^(?:public|protected|private)\s+(?:static\s+)?[\w<>\[\]]+\s+(\w+)\s*\(")],
    "csharp": [re.compile(r"^(?:public|internal|protected|private)?\s*(?:static\s+)?(?:class|interface|enum|struct|record)\s+(\w+)"), re.compile(r"^(?:public|protected|private|internal)\s+(?:static\s+)?[\w<>\[\]]+\s+(\w+)\s*\(")],
    "kotlin": [re.compile(r"^(?:fun|class|object|data class|interface|enum class)\s+(\w+)")],
    "swift": [re.compile(r"^(?:public|internal|private|open)?\s*(?:func|class|struct|enum|protocol)\s+(\w+)")],
}

def _extract_code_symbols(source: str, language: str) -> list[str]:
    patterns = _SYMBOL_PATTERNS.get(language, [])
    seen: set[str] = set()
    symbols: list[str] = []
    for line in source.splitlines():
        line = line.strip()
        for pattern in patterns:
            m = pattern.match(line)
            if m:
                name = m.group(1)
                if name not in seen:
                    seen.add(name)
                    symbols.append(name)
                    if len(symbols) >= _SUMMARY_SYMBOL_CAP:
                        return symbols
                break
    return symbols


def _extract_python_module_docstring(source: str) -> Optional[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant) and isinstance(tree.body[0].value.value, str):
        return tree.body[0].value.value.strip()
    return None


def _extract_leading_comment(source: str) -> Optional[str]:
    lines = source.splitlines()
    comment_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            comment_lines.append(stripped.lstrip("# ").strip())
        elif stripped == "":
            if comment_lines:
                break
        else:
            break
    return "\n".join(comment_lines) if comment_lines else None


def _chunk_code_summary(source: str, path: str, language: str) -> Optional[Chunk]:
    """Emit one kind='code-summary' chunk per source file: module docstring + top-level symbols."""
    if not source.strip():
        return None
    if language == "python":
        docstring = _extract_python_module_docstring(source) or _extract_leading_comment(source)
    else:
        docstring = _extract_leading_comment(source)
    symbols = _extract_code_symbols(source, language)
    if not docstring and not symbols:
        return None
    parts = []
    if docstring:
        parts.append(docstring)
    if symbols:
        parts.append("Symbols: " + ", ".join(symbols))
    text = "\n".join(parts)
    total_lines = source.count("\n") + 1
    return Chunk(
        id=f"{path}#summary",
        path=path,
        kind="code-summary",
        language=language,
        lines=(1, total_lines),
        section="summary",
        text=text,
    )


_FIRST_SECTION_OPENING_MAX = 150


def _chunk_doc_summary(source: str, path: str, kind: str) -> Optional[Chunk]:
    """Emit one kind='doc-summary' chunk per markdown doc file.

    Captures: H1 title, frontmatter key-value lines, opening sentence of the first
    primary-level section body, and the full heading list.
    """
    if not source.strip():
        return None
    lines = source.splitlines()
    total_lines = len(lines)
    primary_level = _detect_primary_heading_level(source)
    primary_hashes = "#" * primary_level
    primary_re = re.compile(rf"^{re.escape(primary_hashes)}\s+(.+)$")

    # Extract all headings for the Sections list (## and ### regardless of primary level)
    headings: list[str] = []
    for line in lines:
        m = _DOC_HEADING_RE.match(line.rstrip())
        if m:
            headings.append(m.group(1).strip())

    # Extract H1 title
    h1_title: Optional[str] = None
    h1_re = re.compile(r"^#\s+(.+)$")
    for line in lines:
        m = h1_re.match(line.rstrip())
        if m:
            h1_title = m.group(1).strip()
            break

    # Extract preamble: lines between H1 and the first primary-level heading.
    # If the preamble contains key-value frontmatter lines, preserve them individually.
    # Otherwise, join non-empty non-heading lines as plain prose (original behavior).
    preamble_lines: list[str] = []
    past_h1 = h1_title is None  # if no H1, treat all pre-section lines as candidates
    for line in lines:
        stripped = line.strip()
        if not past_h1:
            if h1_re.match(line.rstrip()):
                past_h1 = True
            continue
        if primary_re.match(line.rstrip()) or _DOC_HEADING_RE.match(line.rstrip()):
            break
        if stripped:
            preamble_lines.append(stripped)

    frontmatter_lines: list[str] = []
    prose_preamble: Optional[str] = None
    if preamble_lines:
        kv_lines = [l for l in preamble_lines if _FRONTMATTER_LINE_RE.match(l)]
        if len(kv_lines) >= len(preamble_lines) // 2 + 1:
            # Majority are key-value: treat all as structured frontmatter
            frontmatter_lines = preamble_lines
        else:
            # Plain prose preamble: join as a paragraph
            prose_preamble = " ".join(preamble_lines)

    # Extract opening sentence of first primary-level section body
    first_section_opening: Optional[str] = None
    in_first_section = False
    for line in lines:
        if primary_re.match(line.rstrip()):
            if in_first_section:
                break
            in_first_section = True
            continue
        if not in_first_section:
            continue
        stripped = line.strip()
        if not stripped or _DOC_HEADING_RE.match(stripped):
            if first_section_opening:
                break
            continue
        # Take up to the first period or max chars
        period_pos = stripped.find(".")
        if period_pos != -1:
            first_section_opening = stripped[: period_pos + 1]
        else:
            first_section_opening = stripped[:_FIRST_SECTION_OPENING_MAX]
        break

    parts: list[str] = []
    if h1_title:
        parts.append(h1_title)
    if frontmatter_lines:
        parts.extend(frontmatter_lines)
    elif prose_preamble:
        parts.append(prose_preamble)
    if first_section_opening:
        parts.append(first_section_opening)
    if headings:
        parts.append("Sections: " + " · ".join(headings))

    if not parts:
        return None

    return Chunk(
        id=f"{path}#doc-summary",
        path=path,
        kind="doc-summary",
        language=None,
        lines=(1, total_lines),
        section="doc-summary",
        text="\n".join(parts),
    )


def chunk_jupyter(source: str, path: str) -> list[Chunk]:
    """Chunk a Jupyter notebook into typed chunks — one per non-empty cell.

    markdown cells → kind="doc"
    code cells     → kind="code"
    raw/unknown    → skipped
    """
    import json

    path = _normalize_path(path)

    try:
        nb = json.loads(source)
    except (json.JSONDecodeError, ValueError):
        return chunk_line_window(source, path)

    cells = nb.get("cells", [])

    # Detect kernel language from notebook metadata
    meta = nb.get("metadata", {})
    language = (
        meta.get("kernelspec", {}).get("language")
        or meta.get("language_info", {}).get("name")
        or "python"
    )

    chunks: list[Chunk] = []
    virtual_line = 1  # cumulative line offset across all cells

    for cell_index, cell in enumerate(cells):
        cell_type = cell.get("cell_type", "")

        cell_source = cell.get("source", "")
        if isinstance(cell_source, list):
            cell_source = "".join(cell_source)

        if cell_type not in ("markdown", "code"):
            # skip raw and unknown cell types — still advance virtual line counter
            cell_lines = len(cell_source.splitlines()) or 1
            virtual_line += cell_lines
            continue

        # Skip empty/whitespace-only cells
        if not cell_source.strip():
            continue

        cell_lines_list = cell_source.splitlines()
        line_count = len(cell_lines_list) if cell_lines_list else 1
        start_line = virtual_line
        end_line = virtual_line + line_count - 1
        virtual_line = end_line + 1

        # Build section breadcrumb
        n = len(chunks) + 1  # 1-based index among emitted chunks
        if cell_type == "markdown":
            first_line = next((ln for ln in cell_lines_list if ln.strip()), "")
            if first_line.startswith("#"):
                heading = first_line.lstrip("#").strip()
                section = f"notebook > {heading}"
            else:
                section = f"notebook > Cell {n}"
            kind = "doc"
            cell_language = None
        else:
            section = f"notebook > Cell {n}"
            kind = "code"
            cell_language = language

        chunk = Chunk(
            id=f"{path}#cell-{cell_index}",
            path=path,
            kind=kind,
            language=cell_language,
            lines=(start_line, end_line),
            section=section,
            text=cell_source,
        )
        chunks.append(chunk)

    return chunks


def chunk_file(source: str, path: str) -> list[Chunk]:
    """Dispatch to the appropriate chunker based on file path and extension."""
    normalized = _normalize_path(path)
    suffix = PurePosixPath(normalized).suffix.lower()

    is_seed = any(marker in normalized for marker in SEED_PATH_MARKERS)
    is_prompt = (
        any(marker in normalized for marker in PROMPT_PATH_MARKERS)
        or normalized.endswith(PROMPT_SUFFIX)
    )
    is_design_json = suffix == ".json" and DESIGN_JSON_MARKER in normalized
    stem = PurePosixPath(normalized).name  # full filename (no directory); equals stem when no suffix

    if not suffix and stem in MAKEFILE_NAMES:
        ts_result = chunk_make_treesitter(source, normalized)
        if ts_result is not None:
            return ts_result
        return chunk_line_window(source, normalized, language="make", section=stem)

    if not suffix and stem in CODE_EXTENSIONLESS_NAMES:
        return chunk_line_window(source, normalized, language=stem.lower(), section=stem)

    if suffix in TEXT_EXTENSIONS or (not suffix and stem in DOCS_EXTENSIONLESS_NAMES):
        return chunk_plain_text(source, normalized)

    if suffix in PYTHON_EXTENSIONS:
        chunks = split_large_code_chunks(chunk_python(source, normalized))
        summary = _chunk_code_summary(source, normalized, "python")
        if summary:
            chunks = [summary] + chunks
        return chunks

    if suffix in MARKDOWN_EXTENSIONS:
        if is_seed:
            kind = "seed"
        elif is_prompt:
            kind = "prompt"
        else:
            kind = "doc"
        chunks = chunk_markdown(
            source, normalized,
            kind_override=kind,
            suppress_h3_split=(kind == "prompt"),
            suppress_code_extraction=(kind == "prompt"),
        )
        doc_summary = _chunk_doc_summary(source, normalized, kind)
        if doc_summary:
            chunks = [doc_summary] + chunks
        return chunks

    if is_design_json:
        return _chunk_design_json(source, normalized)

    # For all code language paths below, prepend a code-summary chunk when extractable.
    def _with_summary(chunks: list[Chunk], language: str) -> list[Chunk]:
        s = _chunk_code_summary(source, normalized, language)
        return ([s] + chunks) if s else chunks

    if suffix in JAVA_EXTENSIONS:
        ts_result = chunk_java_treesitter(source, normalized)
        chunks = ts_result if ts_result is not None else chunk_java(source, normalized)
        return _with_summary(chunks, "java")

    if suffix in SCALA_EXTENSIONS:
        return _with_summary(_ts_dispatch(chunk_scala_treesitter, chunk_scala, source, normalized, "scala"), "scala")

    if suffix in CSHARP_EXTENSIONS:
        ts_result = chunk_csharp_treesitter(source, normalized)
        chunks = ts_result if ts_result is not None else chunk_csharp(source, normalized)
        return _with_summary(chunks, "csharp")

    if suffix in JS_TS_EXTENSIONS:
        ts_result = chunk_js_ts_treesitter(source, normalized)
        chunks = ts_result if ts_result is not None else chunk_js_ts(source, normalized)
        lang = _EXT_TO_LANGUAGE.get(suffix, "javascript")
        return _with_summary(chunks, lang)

    if suffix in C_CPP_EXTENSIONS:
        ts_result = chunk_c_cpp_treesitter(source, normalized)
        chunks = ts_result if ts_result is not None else chunk_c_cpp(source, normalized)
        lang = "cpp" if suffix in {".cpp", ".hpp", ".cc", ".cxx"} else "c"
        return _with_summary(chunks, lang)

    if suffix in HTML_EXTENSIONS:
        ts_result = chunk_html_treesitter(source, normalized)
        return ts_result if ts_result is not None else chunk_html(source, normalized)

    if suffix in GO_EXTENSIONS:
        ts_result = chunk_go_treesitter(source, normalized)
        chunks = ts_result if ts_result is not None else chunk_go(source, normalized)
        return _with_summary(chunks, "go")

    if suffix in RUST_EXTENSIONS:
        ts_result = chunk_rust_treesitter(source, normalized)
        chunks = ts_result if ts_result is not None else chunk_rust(source, normalized)
        return _with_summary(chunks, "rust")

    if suffix in KOTLIN_EXTENSIONS:
        ts_result = chunk_kotlin_treesitter(source, normalized)
        chunks = ts_result if ts_result is not None else chunk_line_window(source, normalized, language="kotlin", section=_file_stem(normalized))
        return _with_summary(chunks, "kotlin")

    if suffix in SWIFT_EXTENSIONS:
        return _with_summary(
            _ts_dispatch(chunk_swift_treesitter, chunk_swift, source, normalized, "swift"),
            "swift",
        )

    if suffix in OBJC_EXTENSIONS:
        return _ts_dispatch(
            chunk_objc_treesitter, chunk_objc, source, normalized, "objc", with_summary=True
        )

    if suffix in SHELL_EXTENSIONS:
        if suffix != ".fish":
            ts_result = chunk_bash_treesitter(source, normalized)
            if ts_result is not None:
                return ts_result
        return chunk_shell(source, normalized)

    if suffix in SQL_EXTENSIONS:
        return chunk_sql(source, normalized)

    if suffix in XML_EXTENSIONS:
        ts_result = chunk_xml_treesitter(source, normalized)
        return ts_result if ts_result is not None else chunk_xml(source, normalized)

    if suffix in RUBY_EXTENSIONS:
        return _ts_dispatch(chunk_ruby_treesitter, None, source, normalized, "ruby", with_summary=True)

    if suffix in PHP_EXTENSIONS:
        return _ts_dispatch(chunk_php_treesitter, None, source, normalized, "php", with_summary=True)

    if suffix in YAML_EXTENSIONS:
        return _ts_dispatch(chunk_yaml_treesitter, None, source, normalized, "yaml")

    if suffix in TOML_EXTENSIONS:
        return _ts_dispatch(chunk_toml_treesitter, None, source, normalized, "toml")

    if suffix in JSON_EXTENSIONS:
        return _ts_dispatch(chunk_json_treesitter, None, source, normalized, "json")

    if suffix in CSS_EXTENSIONS:
        return _ts_dispatch(chunk_css_treesitter, None, source, normalized, "css")

    if suffix in SCSS_EXTENSIONS:
        return _ts_dispatch(chunk_scss_treesitter, None, source, normalized, "scss")

    if suffix in POWERSHELL_EXTENSIONS:
        return _ts_dispatch(chunk_powershell_treesitter, None, source, normalized, "powershell")

    if suffix in HCL_INDEX_EXTENSIONS:
        return _ts_dispatch(chunk_hcl_treesitter, None, source, normalized, "terraform")

    # Secrets files: index variable names only, redact all values
    if suffix == ".tfvars":
        return chunk_secrets_file(source, normalized, language="terraform")
    if stem == ".env" or stem.startswith(".env."):
        return chunk_secrets_file(source, normalized, language="env")

    if suffix in IPYNB_EXTENSIONS:
        return chunk_jupyter(source, normalized)

    if suffix in CODE_EXTENSIONS:
        return chunk_line_window(source, normalized, language=_ext_language(suffix) or None,
                                 section=_file_stem(normalized))

    # Unknown type — line window with file-stem breadcrumb
    return chunk_line_window(source, normalized, language=None, section=_file_stem(normalized))
