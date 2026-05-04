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


CHUNKER_VERSION = "13"

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
SQL_EXTENSIONS = {".sql"}
XML_EXTENSIONS = {".xml", ".jsp", ".xsd", ".xsl", ".xslt", ".svg"}
KOTLIN_EXTENSIONS = {".kt", ".kts"}
CODE_EXTENSIONS = {
    ".rb", ".php",
    ".yaml", ".yml", ".toml", ".json", ".jsonc",
    ".css", ".scss", ".sass",
    ".ps1", ".psm1",
}

SWIFT_EXTENSIONS = {".swift"}
OBJC_EXTENSIONS = {".m", ".mm"}

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
}


def _ext_language(ext: str) -> str:
    """Return canonical language name for a file extension (with or without leading dot)."""
    key = ext if ext.startswith(".") else f".{ext}"
    return _EXT_TO_LANGUAGE.get(key, ext.lstrip("."))


SEED_PATH_MARKERS = (
    ".wavefoundry/framework/seeds/",
    ".wavefoundry\\framework\\seeds\\",
)

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
    kind: str          # "code" | "doc" | "seed"
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
_H3_PATTERN = re.compile(r"^###\s+(.+)$", re.MULTILINE)


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
) -> list[Chunk]:
    """Chunk a markdown file by ## sections, splitting out fenced code blocks."""
    path = _normalize_path(path)
    default_kind = kind_override or "doc"

    if not source.strip():
        return []

    # Capture H1 title for breadcrumb injection
    h1_match = _H1_PATTERN.search(source)
    doc_title: Optional[str] = h1_match.group(1).strip() if h1_match else None

    chunks: list[Chunk] = []

    # Split on ## headings
    sections: list[tuple[Optional[str], int, str]] = []  # (title, start_line, text)
    lines = source.splitlines(keepends=True)
    current_title: Optional[str] = None
    current_start = 1
    current_lines: list[str] = []

    for i, line in enumerate(lines, start=1):
        m = re.match(r"^##\s+(.+)$", line.rstrip())
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
            code_chunks, code_spans = _extract_fenced_code(
                body, start_line, None, slug, path, default_kind
            )
            # For preamble, use plain section label (None)
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

        # Threshold-gate H3 splitting for oversized sections
        if len(body.strip()) > H3_SPLIT_THRESHOLD_CHARS and _H3_PATTERN.search(body):
            chunks.extend(_split_h3_sections(
                body, start_line, title, slug, doc_title, path, default_kind
            ))
            continue

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
    r"^\s*CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW|FUNCTION|PROCEDURE|INDEX)\s+(?:\w+\.)?(\w+)",
    re.IGNORECASE | re.MULTILINE,
)
_SQL_COMMENT_RE = re.compile(r"((?:[ \t]*--[^\n]*\n)+|/\*.*?\*/)", re.DOTALL)


def chunk_sql(source: str, path: str) -> list[Chunk]:
    stem = _file_stem(path)
    lines = source.splitlines()
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
    return split_large_code_chunks(chunks)


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


def chunk_file(source: str, path: str) -> list[Chunk]:
    """Dispatch to the appropriate chunker based on file path and extension."""
    normalized = _normalize_path(path)
    suffix = PurePosixPath(normalized).suffix.lower()

    is_seed = any(marker in normalized for marker in SEED_PATH_MARKERS)
    is_design_json = suffix == ".json" and DESIGN_JSON_MARKER in normalized
    stem = PurePosixPath(normalized).name  # full filename (no directory); equals stem when no suffix

    if suffix in TEXT_EXTENSIONS or (not suffix and stem in DOCS_EXTENSIONLESS_NAMES):
        return chunk_plain_text(source, normalized)

    if suffix in PYTHON_EXTENSIONS:
        return split_large_code_chunks(chunk_python(source, normalized))

    if suffix in MARKDOWN_EXTENSIONS:
        kind = "seed" if is_seed else "doc"
        return chunk_markdown(source, normalized, kind_override=kind)

    if is_design_json:
        return _chunk_design_json(source, normalized)

    if suffix in JAVA_EXTENSIONS:
        ts_result = chunk_java_treesitter(source, normalized)
        if ts_result is not None:
            return ts_result
        return chunk_java(source, normalized)

    if suffix in SCALA_EXTENSIONS:
        return chunk_scala(source, normalized)

    if suffix in CSHARP_EXTENSIONS:
        ts_result = chunk_csharp_treesitter(source, normalized)
        if ts_result is not None:
            return ts_result
        return chunk_csharp(source, normalized)

    if suffix in JS_TS_EXTENSIONS:
        ts_result = chunk_js_ts_treesitter(source, normalized)
        if ts_result is not None:
            return ts_result
        return chunk_js_ts(source, normalized)

    if suffix in C_CPP_EXTENSIONS:
        ts_result = chunk_c_cpp_treesitter(source, normalized)
        if ts_result is not None:
            return ts_result
        return chunk_c_cpp(source, normalized)

    if suffix in HTML_EXTENSIONS:
        return chunk_html(source, normalized)

    if suffix in GO_EXTENSIONS:
        ts_result = chunk_go_treesitter(source, normalized)
        if ts_result is not None:
            return ts_result
        return chunk_go(source, normalized)

    if suffix in RUST_EXTENSIONS:
        ts_result = chunk_rust_treesitter(source, normalized)
        if ts_result is not None:
            return ts_result
        return chunk_rust(source, normalized)

    if suffix in KOTLIN_EXTENSIONS:
        ts_result = chunk_kotlin_treesitter(source, normalized)
        if ts_result is not None:
            return ts_result
        return chunk_line_window(source, normalized, language="kotlin", section=_file_stem(normalized))

    if suffix in SWIFT_EXTENSIONS:
        return chunk_swift(source, normalized)

    if suffix in OBJC_EXTENSIONS:
        return chunk_objc(source, normalized)

    if suffix in SHELL_EXTENSIONS:
        if suffix != ".fish":
            ts_result = chunk_bash_treesitter(source, normalized)
            if ts_result is not None:
                return ts_result
        return chunk_shell(source, normalized)

    if suffix in SQL_EXTENSIONS:
        return chunk_sql(source, normalized)

    if suffix in XML_EXTENSIONS:
        return chunk_xml(source, normalized)

    if suffix in CODE_EXTENSIONS:
        return chunk_line_window(source, normalized, language=_ext_language(suffix) or None,
                                 section=_file_stem(normalized))

    # Unknown type — line window with file-stem breadcrumb
    return chunk_line_window(source, normalized, language=None, section=_file_stem(normalized))
