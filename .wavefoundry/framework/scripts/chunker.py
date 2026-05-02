#!/usr/bin/env python3
"""Language-aware text chunker for the Wavefoundry index builder."""
from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Optional


sys.dont_write_bytecode = True

# Lines per window and overlap for the line-window fallback chunker.
WINDOW_SIZE = 60
WINDOW_OVERLAP = 10
MAX_CODE_CHUNK_CHARS = 4000

# Extensions routed to each chunker.
PYTHON_EXTENSIONS = {".py"}
MARKDOWN_EXTENSIONS = {".md", ".markdown"}
CODE_EXTENSIONS = {
    ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs",
    ".go", ".rs", ".java", ".kt", ".swift", ".c", ".cpp", ".h", ".hpp",
    ".cs", ".rb", ".php", ".sh", ".bash", ".zsh", ".fish",
    ".yaml", ".yml", ".toml", ".json", ".jsonc",
    ".html", ".css", ".scss", ".sass",
}

SEED_PATH_MARKERS = (
    ".wavefoundry/framework/seeds/",
    ".wavefoundry\\framework\\seeds\\",
)

DESIGN_JSON_MARKER = "docs/design/"


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


def chunk_python(source: str, path: str) -> list[Chunk]:
    """Chunk a Python source file into function, class, method, and docstring chunks."""
    path = _normalize_path(path)
    if not source.strip():
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return chunk_line_window(source, path, language="python")

    source_lines = source.splitlines()
    chunks: list[Chunk] = []

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
            start, end = _node_line_range(node, source_lines)
            node_source = "\n".join(source_lines[start - 1:end])

            # Emit docstring as doc chunk if present
            doc = _extract_docstring(node)
            if doc:
                doc_end = start + doc.count("\n") + 2  # rough estimate
                chunks.append(Chunk(
                    id=f"{path}::{qname}.__doc__",
                    path=path,
                    kind="doc",
                    language="python",
                    lines=(start, min(doc_end, end)),
                    section=qname,
                    text=doc.strip(),
                ))

            # Emit the node itself as a code chunk
            chunks.append(Chunk(
                id=f"{path}::{qname}",
                path=path,
                kind="code",
                language="python",
                lines=(start, end),
                section=qname,
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

    return chunks


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

_H2_PATTERN = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_FENCED_CODE_PATTERN = re.compile(
    r"^```(\w*)\n(.*?)^```", re.MULTILINE | re.DOTALL
)


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

        slug = _slugify(title) if title else "preamble"
        section_end = start_line + len(body.splitlines())

        # Extract fenced code blocks as separate code chunks
        code_spans: list[tuple[int, int]] = []
        for m in _FENCED_CODE_PATTERN.finditer(body):
            lang = m.group(1) or None
            code_text = m.group(2)
            block_start_offset = body[:m.start()].count("\n")
            abs_start = start_line + block_start_offset + 1
            abs_end = abs_start + code_text.count("\n")
            code_spans.append((m.start(), m.end()))
            if code_text.strip():
                chunks.append(Chunk(
                    id=f"{path}#{slug}:code",
                    path=path,
                    kind="code",
                    language=lang,
                    lines=(abs_start, abs_end),
                    section=title,
                    text=code_text.strip(),
                ))

        # Emit prose (body minus code blocks) as doc chunk
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
                section=title,
                text=prose,
            ))

    return chunks


# ---------------------------------------------------------------------------
# Line-window fallback chunker
# ---------------------------------------------------------------------------

def chunk_line_window(
    source: str,
    path: str,
    language: Optional[str] = None,
    window: int = WINDOW_SIZE,
    overlap: int = WINDOW_OVERLAP,
) -> list[Chunk]:
    """Chunk any text into overlapping line windows."""
    path = _normalize_path(path)
    lines = source.splitlines()
    if not lines:
        return []

    chunks: list[Chunk] = []
    step = max(1, window - overlap)
    i = 0
    while i < len(lines):
        end = min(i + window, len(lines))
        start_line = i + 1
        end_line = end
        text = "\n".join(lines[i:end])
        chunks.append(Chunk(
            id=f"{path}:L{start_line}-L{end_line}",
            path=path,
            kind="code",
            language=language,
            lines=(start_line, end_line),
            section=None,
            text=text,
        ))
        if end >= len(lines):
            break
        i += step

    return chunks


# ---------------------------------------------------------------------------
# Top-level dispatcher
# ---------------------------------------------------------------------------

def _chunk_design_json(source: str, path: str) -> list[Chunk]:
    """Chunk a docs/design/**/*.json file as doc-kind chunks via the markdown chunker.

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

    if suffix in PYTHON_EXTENSIONS:
        return split_large_code_chunks(chunk_python(source, normalized))

    if suffix in MARKDOWN_EXTENSIONS:
        kind = "seed" if is_seed else "doc"
        return chunk_markdown(source, normalized, kind_override=kind)

    if is_design_json:
        return _chunk_design_json(source, normalized)

    if suffix in CODE_EXTENSIONS:
        return chunk_line_window(source, normalized, language=suffix.lstrip(".") or None)

    # Unknown type — line window with no language
    return chunk_line_window(source, normalized, language=None)
