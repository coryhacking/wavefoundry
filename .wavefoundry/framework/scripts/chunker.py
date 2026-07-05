#!/usr/bin/env python3
"""Language-aware text chunker for the Wavefoundry index builder."""
from __future__ import annotations

import ast
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Callable, Optional

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


# Wave 1p5c4: skip tree-sitter on very large files — building a full AST over a multi-MB (or,
# pathologically, multi-GB) file spins. Files over the cap fall back to the regex/line chunker
# (still indexed as text). Override via WAVEFOUNDRY_MAX_TS_PARSE_BYTES, which the indexer sets from
# `indexing.max_treesitter_parse_bytes` in workflow-config.json. 0/negative disables the cap.
MAX_TREESITTER_PARSE_BYTES_DEFAULT = 2_000_000


def _ts_parse(lang_key: str, source: str):
    """Parse source with tree-sitter. Returns tree or None on failure/unavailability/oversize.
    Logs a warning on first miss so operators know which language fell back to regex.
    """
    import os
    _cap = int(os.environ.get("WAVEFOUNDRY_MAX_TS_PARSE_BYTES") or MAX_TREESITTER_PARSE_BYTES_DEFAULT)
    if _cap > 0 and len(source) > _cap:
        return None
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


# Wave 1p3dk / 1p3ho validation: bumped 23 → 24 to exercise the upgrade-time
# chunker-bump detection path in production. No chunker algorithm change; the
# bump itself is the test fixture. After this pack ships, consumer upgrades
# should observe: (a) `⚠  Chunker version changed: 23 → 24. Forcing full
# index rebuild on next --update-index.` in the upgrade log during extract,
# (b) `phase_index_rebuild` (full) running on `--update-index` instead of
# `phase_index_update` (incremental), (c) post-condition verification confirming
# the new version in `.wavefoundry/index/meta.json` after rebuild.
CHUNKER_VERSION = "31"  # 1p5k0 (nested-type-const-qualification): nested types (Swift struct/enum/class in a class body; other langs' nested classes) now attribute member constants AND methods to the nested qualified owner (Outer.Inner.x) in the chunk lane — was flattened onto the outermost type — and emit a nested-type __decl__ chunk. Aligns chunk-lane qnames with the already-correct graph lane; paired with code_constants dotted-suffix matching so the natural Inner.x query resolves. Chunk-set shape change → bump (consumer code index re-chunks). 1p4w9: docs chunks prepend their section breadcrumb to embedded text (NL→docs retrieval +10pp on the 32-query eval; docs-only — code chunk text unchanged, so code vectors reuse by content-hash and only docs re-embed). 1p4q4 review (C1/C2/C3): complete the TS namespace/module const-chunk coverage — the `module M{}` keyword form, NON-export namespace const, `export namespace`, `declare namespace`, and `declare enum` members now chunk. Chunk-set shape change → bump (consumer code index re-chunks). 1p4q4 (28): TS enum/const-enum members + namespace const + declare const are now constant chunks (Enum.Member). 1p4hi close (27): all-11-language constant chunking + Go short-const fix. 1p4mf (26): module/class-level constants emitted as chunks (kind="code", breadcrumb-prefixed text, merge-excluded via " [const]" section marker)

# Lines per window and overlap for the line-window fallback chunker.
WINDOW_SIZE = 120
WINDOW_OVERLAP = 10

# Wave 1p3b9 (1p397): per-kind chunk-size caps calibrated to the actual
# embedder (BGE family, 512-token input cap). Empirically measured against
# the cached tokenizer:
#   - Python source: ~3.07 chars/token → 500 tokens ≈ 1535 chars
#   - English/markdown prose: ~3.62-4.17 chars/token → 500 tokens ≈ 1800-2100 chars
#   - Markdown pipe tables: ~4.38 chars/token → 500 tokens ≈ 2190 chars
#
# Code is denser per token than prose, so code chunks need a tighter cap to
# stay under the embedder's input cap and avoid silent truncation. Previous
# value was 4000 for both — code chunks lost ~62% to truncation and prose
# chunks lost ~45%. Dropping to per-kind caps keeps every byte addressable.
MAX_CODE_CHUNK_CHARS = 1500   # was 4000; matches BGE token budget for code
MAX_DOC_CHUNK_CHARS = 2000    # everything else (doc / seed / prompt / plain / yaml / json / etc.)
# Default for `split_large_chunks(max_chars=...)` legacy callers — equal to
# the doc cap. The runtime per-kind selection happens inside the function.
MAX_CHUNK_CHARS = MAX_DOC_CHUNK_CHARS


def _max_chars_for_chunk(chunk: "Chunk") -> int:
    """Per-kind cap selector. Code chunks get the tighter limit; everything
    else (doc, seed, prompt, doc-summary, plain text, etc.) gets the larger."""
    return MAX_CODE_CHUNK_CHARS if chunk.kind == "code" else MAX_DOC_CHUNK_CHARS

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
JS_TS_EXTENSIONS = {".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs", ".mts", ".cts"}
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
    ".ts": "typescript", ".tsx": "typescript", ".mts": "typescript", ".cts": "typescript",
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
    # 1p4ww: the framework README is folded into the project docs index as a seed
    # (framework overview alongside the seed methodology content).
    ".wavefoundry/framework/README.md",
    ".wavefoundry\\framework\\README.md",
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


# Wave 1p4mf: module/class-level constant chunking. Constants are emitted as kind="code"
# (constants ARE code — searchable everywhere, no new-kind routing/filter surprises). To
# stop _merge_small_chunks from silently folding a 1-line constant chunk into a neighbour
# (CHUNK_MIN_LINES=2), the constant's `section` carries a marker suffix the merge excludes
# (mirrors the existing "> imports" exclusion); the marker is kept OUT of the embedded
# `text`, which gets the clean breadcrumb prefix. Casing IS the only Python constant signal.
_CONST_SECTION_SUFFIX = " [const]"
_CONST_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _is_const_name(name: str) -> bool:
    """UPPER_SNAKE constant name, excluding single-letter TypeVars (T, K, V)."""
    return bool(_CONST_NAME_RE.match(name)) and (len(name) >= 2 or "_" in name)


def _is_final_annotation(ann: Optional[ast.AST]) -> bool:
    """True when an AnnAssign annotation is ``typing.Final`` / ``Final[...]`` (casing-independent constant override)."""
    if ann is None:
        return False
    if isinstance(ann, ast.Subscript):
        ann = ann.value
    if isinstance(ann, ast.Name):
        return ann.id == "Final"
    if isinstance(ann, ast.Attribute):
        return ann.attr == "Final"
    return False


def _is_enum_class(node: ast.ClassDef) -> bool:
    """Heuristic: the class inherits an Enum/Flag base — its members stay together in the class chunk, not split."""
    for base in node.bases:
        name = base.id if isinstance(base, ast.Name) else getattr(base, "attr", "")
        if name and ("Enum" in name or "Flag" in name):
            return True
    return False


def _leading_comment_start(lineno: int, source_lines: list[str]) -> int:
    """Extend a statement's start line upward over a contiguous leading ``#`` comment block."""
    start = lineno
    i = lineno - 2  # 0-indexed line directly above the statement
    while i >= 0 and source_lines[i].strip().startswith("#"):
        start = i + 1
        i -= 1
    return start


def chunk_python(source: str, path: str) -> list[Chunk]:
    """Chunk a Python source file into function, class, method, and docstring chunks."""
    path = _normalize_path(path)
    if not source.strip():
        return []

    try:
        tree = ast.parse(source, filename=path)
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

    def _emit_constants(body: list, owner: Optional[str]) -> None:
        # Wave 1p4mf: one chunk per module/class-level named constant (per-identifier for
        # multi-target). owner=None → module-level; owner=ClassName → class-level. Scope is
        # the discriminator: only DIRECT children of Module / a (non-Enum) ClassDef body are
        # passed here, so function-locals and ``if TYPE_CHECKING:`` bodies are never reached.
        for stmt in body:
            if isinstance(stmt, ast.Assign):
                names: list[str] = []
                for tgt in stmt.targets:
                    if isinstance(tgt, ast.Name):
                        names.append(tgt.id)
                    elif isinstance(tgt, (ast.Tuple, ast.List)):
                        names.extend(e.id for e in tgt.elts if isinstance(e, ast.Name))
                is_final = False
            elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None and isinstance(stmt.target, ast.Name):
                names = [stmt.target.id]
                is_final = _is_final_annotation(stmt.annotation)
            else:
                continue
            for name in names:
                if not (_is_const_name(name) or is_final):
                    continue
                qname = f"{owner}.{name}" if owner else name
                start = _leading_comment_start(stmt.lineno, source_lines)
                _, end = _node_line_range(stmt, source_lines)
                decl = "\n".join(source_lines[start - 1:end])
                breadcrumb = f"{stem} > {qname}"
                chunks.append(Chunk(
                    id=f"{path}::{qname}",
                    path=path,
                    kind="code",
                    language="python",
                    lines=(start, end),
                    # marker suffix → excluded from _merge_small_chunks; clean breadcrumb in text
                    section=f"{breadcrumb}{_CONST_SECTION_SUFFIX}",
                    text=f"{breadcrumb}\n\n{decl}",
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
                # Wave 1p4mf: class-level constants — but NOT enum members (an Enum's
                # members stay together in the class chunk; do not split them out).
                if not _is_enum_class(node):
                    _emit_constants(node.body, qname)
        else:
            for child in ast.iter_child_nodes(node):
                _visit(child, parent_name=parent_name)

    for node in ast.iter_child_nodes(tree):
        _visit(node)

    # Wave 1p4mf: module-level constants (direct children of the module only).
    _emit_constants(tree.body, None)

    return _merge_small_chunks(chunks)


# Wave 1p3b9 (1p397): regex for a markdown pipe-table separator row, e.g.
# `|---|---|---|` or `| --- | :--- | ---: |`. Detection of this line within
# a run of pipe-prefixed lines is the load-bearing signal that the run is
# a real table (not just prose containing pipe characters).
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|[\s\-:|]+\|\s*$")


def _is_pipe_table_line(line: str) -> bool:
    """True for lines that start AND end with `|` (ignoring trailing whitespace)
    AND contain at least one interior `|`. The shape that markdown pipe tables
    use for header, separator, and data rows."""
    s = line.rstrip()
    return s.startswith("|") and s.endswith("|") and s.count("|") >= 2


def _find_oversized_table(text: str, max_chars: int) -> Optional[tuple[int, int, int]]:
    """Find a pipe table in `text` that exceeds `max_chars` (header + body).

    Returns ``(start_line_idx, separator_line_idx, end_line_idx)`` where
    `start_line_idx` is the header row's index in the line list,
    `separator_line_idx` is the `|---|---|` row index, and `end_line_idx` is
    the line index just past the table's last data row. Returns None when
    no such table exists in `text`.

    A real markdown pipe table is: header row + separator row + 1+ data
    rows. Detection requires at least 3 consecutive `_is_pipe_table_line`
    lines AND one of them is the separator. The total table-region size
    must exceed `max_chars` to qualify as "oversized."
    """
    lines = text.splitlines()
    n = len(lines)
    i = 0
    while i < n:
        if not _is_pipe_table_line(lines[i]):
            i += 1
            continue
        # Walk the run of pipe-table lines
        run_start = i
        while i < n and _is_pipe_table_line(lines[i]):
            i += 1
        run_end = i  # exclusive
        run_lines = lines[run_start:run_end]
        if len(run_lines) < 3:
            continue
        # Find the separator row within the run (expected at index 1)
        sep_idx_in_run = None
        for j, line in enumerate(run_lines):
            if _TABLE_SEPARATOR_RE.match(line):
                sep_idx_in_run = j
                break
        if sep_idx_in_run is None or sep_idx_in_run >= len(run_lines) - 1:
            continue  # no separator, or no data rows after it
        # Size check
        table_text = "\n".join(run_lines)
        if len(table_text) <= max_chars:
            continue
        return (run_start, run_start + sep_idx_in_run, run_end)
    return None


def _decompose_oversized_table_chunk(chunk: "Chunk", max_chars: int) -> Optional[list["Chunk"]]:
    """Decompose a chunk whose dominant oversized content is a markdown pipe
    table. Returns None if no oversized table is found; otherwise returns the
    list of decomposed chunks.

    Each emitted chunk contains:
    1. The chunk-level prelude (any lines BEFORE the table — typically the
       section breadcrumb / H2 title block).
    2. The table's header row + separator row (preserved on every emitted
       chunk so column context survives decomposition).
    3. A greedy group of data rows that, combined with the prelude + header,
       stays under `max_chars`.
    4. Any chunk-level postlude (lines AFTER the table) is appended to the
       FINAL emitted chunk only; subsequent tables in the same chunk are
       beyond this helper's scope and fall through to line-wrap.

    Section labels get `(rows N–M of T)` suffix so retrieval surfaces can
    address coherent row ranges.
    """
    table_loc = _find_oversized_table(chunk.text, max_chars)
    if table_loc is None:
        return None
    table_start, sep_idx, table_end = table_loc
    lines = chunk.text.splitlines()
    prelude = lines[:table_start]
    header_lines = lines[table_start:sep_idx + 1]  # header row + separator
    data_rows = lines[sep_idx + 1:table_end]
    postlude = lines[table_end:]

    # Compute the per-emit fixed-text size: prelude + header preamble + 2 newlines
    prelude_text = "\n".join(prelude).rstrip()
    header_text = "\n".join(header_lines)
    fixed_text = (prelude_text + "\n\n" if prelude_text else "") + header_text + "\n"
    fixed_size = len(fixed_text)
    if fixed_size >= max_chars:
        # Header alone already over-cap — fall through to line-wrap. This
        # shouldn't happen for real tables (header rows are short) but
        # guards against pathological input.
        return None

    # Greedy row grouping
    groups: list[list[str]] = []
    current: list[str] = []
    current_size = fixed_size
    for row in data_rows:
        row_len = len(row) + 1  # +1 for newline
        if current and current_size + row_len > max_chars:
            groups.append(current)
            current = []
            current_size = fixed_size
        current.append(row)
        current_size += row_len
    if current:
        groups.append(current)
    if not groups:
        return None

    total_rows = len(data_rows)
    base_section = chunk.section or ""
    base_line_start, _ = chunk.lines
    table_start_line = base_line_start + table_start  # 1-based source line of header
    prelude_line_offset = base_line_start

    result: list[Chunk] = []
    rows_emitted = 0
    last_idx = len(groups) - 1
    for g_idx, group in enumerate(groups):
        group_start_row = rows_emitted + 1
        group_end_row = rows_emitted + len(group)
        rows_emitted = group_end_row
        parts = []
        if prelude_text:
            parts.append(prelude_text)
        parts.append(header_text)
        parts.append("\n".join(group))
        # Append postlude to the last group only
        if g_idx == last_idx and postlude:
            postlude_text = "\n".join(postlude).rstrip()
            if postlude_text:
                parts.append(postlude_text)
        text = "\n\n".join(parts) if prelude_text else "\n".join(parts)
        # Actually we need header attached to rows with single newline, not double
        text_parts: list[str] = []
        if prelude_text:
            text_parts.append(prelude_text + "\n\n")
        text_parts.append(header_text + "\n")
        text_parts.append("\n".join(group))
        if g_idx == last_idx and postlude:
            postlude_text = "\n".join(postlude).rstrip()
            if postlude_text:
                text_parts.append("\n\n" + postlude_text)
        emitted_text = "".join(text_parts)
        suffix = f"rows {group_start_row}–{group_end_row} of {total_rows}"
        section = f"{base_section} ({suffix})" if base_section else f"({suffix})"
        result.append(Chunk(
            id=f"{chunk.id}:rows{group_start_row}-{group_end_row}",
            path=chunk.path,
            kind=chunk.kind,
            language=chunk.language,
            lines=(table_start_line, table_start_line + len(group) + len(header_lines) - 1),
            section=section,
            text=emitted_text,
        ))
    return result


# Wave 1p3b9 (1p397): line prefixes that mean "this line is content, NOT a
# breadcrumb preamble." Used by `_extract_breadcrumb_preamble` to detect
# whether the chunk's leading line is the markdown chunker's injected section
# breadcrumb (e.g., `Doc Title > Section Heading`) vs. real content.
_BREADCRUMB_NON_CONTENT_PREFIXES = ("-", "*", "+", "|", "#", "```", ">", "\t")
_NUMBERED_LIST_RE = re.compile(r"^\s*\d+\.\s+")


def _extract_breadcrumb_preamble(lines: list[str]) -> tuple[list[str], int]:
    """If the chunk's leading line(s) look like a breadcrumb preamble (a
    non-content line followed by a blank line), return them and the offset
    past the blank. Otherwise return ``([], 0)``.

    The markdown chunker injects breadcrumbs as ``Doc Title > Section`` on
    its own line followed by a blank line and then the section body. When
    we line-wrap an oversized section, every emitted part should retain
    that breadcrumb so the retrieval consumer sees the section context.
    """
    if len(lines) < 2:
        return [], 0
    first = lines[0]
    second = lines[1]
    if not first.strip() or second.strip() != "":
        return [], 0
    stripped = first.lstrip()
    if stripped.startswith(_BREADCRUMB_NON_CONTENT_PREFIXES):
        return [], 0
    if _NUMBERED_LIST_RE.match(first):
        return [], 0
    return [first, ""], 2


def _line_wrap_chunk(chunk: Chunk, cap: int) -> list[Chunk]:
    """Line-window split a single oversized chunk into windows ≤ ``cap``.

    Falls back to character-window splitting on lines that themselves
    exceed ``cap``. Each derived chunk gets a ``(part N/M)`` section
    suffix.

    Wave 1p3b9 (1p397): when the chunk's leading line is a breadcrumb
    preamble (the markdown chunker's injected ``Doc Title > Section`` line
    followed by a blank), that preamble is preserved on every emitted
    part so retrieval consumers see the section context in every chunk
    body, not just the lead part.
    """
    start_line, _ = chunk.lines
    lines = chunk.text.splitlines()
    if not lines:
        return []

    # Detect breadcrumb preamble BEFORE char-windowing so we can size the
    # body cap correctly (every emitted chunk = preamble + \n + body slice).
    preamble_lines, body_offset = _extract_breadcrumb_preamble(lines)
    body_lines_raw = lines[body_offset:]
    preamble_text = "\n".join(preamble_lines)
    preamble_size = len(preamble_text) + (1 if preamble_text else 0)
    # Leave room in each window for the preamble. If the preamble is so
    # large that the effective body cap drops below half the cap, skip the
    # preamble entirely — better than emitting almost-empty body windows.
    body_cap = cap - preamble_size
    if body_cap < cap // 2:
        preamble_lines = []
        preamble_text = ""
        preamble_size = 0
        body_cap = cap
        body_lines_raw = lines
        body_offset = 0

    if not body_lines_raw:
        # The whole chunk was preamble — nothing to split, return as-is.
        return [chunk]

    # Char-window split any line that itself exceeds body_cap, so no single
    # line exceeds the body budget.
    body_lines: list[str] = []
    for line in body_lines_raw:
        if len(line) <= body_cap:
            body_lines.append(line)
            continue
        for i in range(0, len(line), body_cap):
            body_lines.append(line[i:i + body_cap])

    windows: list[tuple[int, int, list[str]]] = []
    window_lines: list[str] = []
    window_start = start_line + body_offset
    current_len = 0
    for offset, line in enumerate(body_lines):
        line_len = len(line) + 1
        if window_lines and current_len + line_len > body_cap:
            window_end = window_start + len(window_lines) - 1
            windows.append((window_start, window_end, window_lines))
            window_lines = []
            window_start = start_line + body_offset + offset
            current_len = 0
        window_lines.append(line)
        current_len += line_len
    if window_lines:
        window_end = window_start + len(window_lines) - 1
        windows.append((window_start, window_end, window_lines))

    out: list[Chunk] = []
    total = len(windows)
    base_section = chunk.section or ""
    for idx, (ws, we, wl) in enumerate(windows, start=1):
        section = f"{base_section} (part {idx}/{total})" if base_section else f"(part {idx}/{total})"
        body_text = "\n".join(wl)
        if preamble_text:
            text = preamble_text + "\n" + body_text
        else:
            text = body_text
        out.append(Chunk(
            id=f"{chunk.id}:L{ws}-L{we}",
            path=chunk.path,
            kind=chunk.kind,
            language=chunk.language,
            lines=(ws, we),
            section=section,
            text=text,
        ))
    return out


def split_large_chunks(chunks: list[Chunk], max_chars: Optional[int] = None) -> list[Chunk]:
    """Split oversized chunks of any kind into smaller line-window chunks.

    Wave 1p3b9 (1p397): generalized from the previous `split_large_code_chunks`
    by dropping the `kind != "code"` early-skip. Now serves as the universal
    last-resort guard applied at the `chunk_file` dispatcher level — every
    chunk emitted by any chunker passes through, regardless of kind (doc,
    seed, prompt, code, plain text, etc.).

    When ``max_chars`` is None (the default for new callers), each chunk's
    cap is selected per its kind via ``_max_chars_for_chunk``: code chunks
    use ``MAX_CODE_CHUNK_CHARS`` (1500) to match the BGE embedder's token
    budget for denser tokenization; non-code chunks use ``MAX_DOC_CHUNK_CHARS``
    (2000). When ``max_chars`` is given explicitly (legacy callers), that
    value applies to every chunk.

    Decomposition priority:
    1. If the chunk contains an oversized markdown pipe table (header +
       separator + many rows), decompose per-row with the header preserved
       on each emitted chunk via `_decompose_oversized_table_chunk`. This
       preserves column context which is the load-bearing retrieval-quality
       property for Decision Log / AC Priority / Risks tables in change docs.
    2. Otherwise, line-window split with character-window fallback for
       single-line oversized content. Each derived chunk's `section` field
       gets a ` (part N/M)` suffix.

    Chunks already at or under their cap pass through unchanged.
    """
    result: list[Chunk] = []
    for chunk in chunks:
        cap = max_chars if max_chars is not None else _max_chars_for_chunk(chunk)
        if len(chunk.text) <= cap:
            result.append(chunk)
            continue

        # Wave 1p3b9 (1p397): table-aware decomposition before line-wrap.
        # Preserves column context — load-bearing for Decision Log / AC
        # Priority / Risks tables in change docs (real-world tables reach
        # 41K chars in committed change docs).
        table_chunks = _decompose_oversized_table_chunk(chunk, cap)
        if table_chunks is not None:
            # Each emitted table chunk may itself still be over-cap (e.g., a
            # single data row + header > cap on very wide tables under a low
            # cap). Fall through to line/char-wrap for those residuals —
            # don't recurse into `split_large_chunks`, which would re-enter
            # the table path and infinite-loop.
            for tc in table_chunks:
                if len(tc.text) <= cap:
                    result.append(tc)
                else:
                    result.extend(_line_wrap_chunk(tc, cap))
            continue

        result.extend(_line_wrap_chunk(chunk, cap))

    return result


# Backward-compat alias for any external caller still referencing the old
# code-only name. Internal callers should use `split_large_chunks` directly.
split_large_code_chunks = split_large_chunks


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


# Wave 1p3b9 (1p397): regex for top-level list-item starts. Matches both
# numbered (`1.`, `2.`, etc.) and bullet (`-`, `*`, `+`) lists at column 0
# (top-level only — nested list items are indented and stay with their
# parent). Used by `_decompose_oversized_markdown_body` to detect list
# structure for per-item decomposition.
_TOP_LEVEL_LIST_ITEM_RE = re.compile(r"^(?:\d+\.|[-*+])\s+", re.MULTILINE)


def _decompose_oversized_markdown_body(
    body: str,
    start_line: int,
    path: str,
    kind: str,
    slug: str,
    max_chars: int = MAX_CHUNK_CHARS,
) -> list[Chunk]:
    """Decompose an oversized markdown body into chunks ≤ max_chars.

    Wave 1p3b9 (1p397): used when a primary section's body exceeds
    ``MAX_CHUNK_CHARS`` (typically H1-only seed/prompt files like
    seed-040 with long numbered task lists). Walks top-level blocks
    (blank-line-separated paragraphs / lists) and groups them greedily
    into chunks up to the cap.

    When a single block (typically an entire numbered list) itself
    exceeds the cap, it is decomposed at top-level list-item boundaries
    so each emitted chunk contains a coherent set of items, not an
    arbitrary hard-wrap of the middle of an item.

    Anything still over-cap after this pass (e.g., a single list item
    that is itself a 10K-char code block) falls through to the universal
    ``split_large_chunks`` guard at ``chunk_file``.

    Each emitted chunk's ``section`` derives from the first paragraph or
    list-item text (truncated to 80 chars) so retrieval surfaces have a
    meaningful breadcrumb.
    """
    if not body.strip():
        return []

    # Split body into top-level blocks at blank-line boundaries
    blocks: list[tuple[int, str]] = []  # (start_line_offset, block_text)
    current_block_lines: list[str] = []
    current_block_start_offset = 0
    line_offset = 0
    for line in body.splitlines():
        if line.strip() == "":
            if current_block_lines:
                blocks.append((current_block_start_offset, "\n".join(current_block_lines)))
                current_block_lines = []
            line_offset += 1
            continue
        if not current_block_lines:
            current_block_start_offset = line_offset
        current_block_lines.append(line)
        line_offset += 1
    if current_block_lines:
        blocks.append((current_block_start_offset, "\n".join(current_block_lines)))

    if not blocks:
        return []

    # Pre-pass: any block that is itself oversized AND is a top-level list
    # gets decomposed into per-list-item sub-blocks. Other oversized blocks
    # (long single paragraphs, code blocks) stay as one block for now and
    # rely on the universal guard.
    expanded_blocks: list[tuple[int, str]] = []
    for offset, block_text in blocks:
        if len(block_text) <= max_chars:
            expanded_blocks.append((offset, block_text))
            continue
        # Is this a top-level list? Check first line.
        first_line = block_text.split("\n", 1)[0]
        if not _TOP_LEVEL_LIST_ITEM_RE.match(first_line):
            expanded_blocks.append((offset, block_text))
            continue
        # Decompose at top-level list-item boundaries. Nested children
        # (lines starting with whitespace) stay with their parent item.
        item_lines: list[str] = []
        item_start_offset = offset
        sub_offset = 0
        for line in block_text.splitlines():
            if item_lines and _TOP_LEVEL_LIST_ITEM_RE.match(line):
                expanded_blocks.append((item_start_offset, "\n".join(item_lines)))
                item_lines = []
                item_start_offset = offset + sub_offset
            item_lines.append(line)
            sub_offset += 1
        if item_lines:
            expanded_blocks.append((item_start_offset, "\n".join(item_lines)))

    # Walker: group blocks greedily into chunks ≤ max_chars.
    chunks: list[Chunk] = []
    current_text_parts: list[str] = []
    current_first_block_text: Optional[str] = None
    current_start_offset: int = 0
    current_len = 0

    def _flush() -> None:
        if not current_text_parts:
            return
        text = "\n\n".join(current_text_parts).strip()
        if not text:
            return
        section_hint = (current_first_block_text or text).split("\n", 1)[0].strip()
        # Strip leading list-item marker for cleaner section labels
        section_hint = re.sub(r"^(?:\d+\.|[-*+])\s+", "", section_hint)
        section = section_hint[:80].strip() or None
        sl = start_line + current_start_offset
        el = sl + text.count("\n")
        chunks.append(Chunk(
            id=f"{path}#{slug}@L{sl}",
            path=path,
            kind=kind,
            language=None,
            lines=(sl, el),
            section=section,
            text=text,
        ))

    for offset, block_text in expanded_blocks:
        block_len = len(block_text) + 2  # +2 for the blank-line separator
        if current_text_parts and current_len + block_len > max_chars:
            _flush()
            current_text_parts = []
            current_first_block_text = None
            current_len = 0
        if not current_text_parts:
            current_start_offset = offset
            current_first_block_text = block_text
        current_text_parts.append(block_text)
        current_len += block_len
    _flush()
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
                    # Wave 1p3b9 (1p397): when an H1-only seed/prompt body
                    # exceeds the cap, decompose at paragraph + list-item
                    # boundaries before falling through to the universal
                    # guard. Acute case: seed-040 / seed-060 / etc. with
                    # long "Intent + numbered Tasks" structure and no H2s.
                    if (default_kind in ("seed", "prompt")
                            and len(prose) > MAX_CHUNK_CHARS):
                        chunks.extend(_decompose_oversized_markdown_body(
                            prose, start_line, path, default_kind, slug,
                        ))
                    else:
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
                    if (default_kind in ("seed", "prompt")
                            and len(prose) > MAX_CHUNK_CHARS):
                        chunks.extend(_decompose_oversized_markdown_body(
                            prose, start_line, path, default_kind, slug,
                        ))
                        continue
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
        # Wave 1p4mf: constant chunks carry a marker suffix and are excluded from merging
        # (a 1-line constant must keep its own id, never fold into a neighbour) — both as a
        # merge SOURCE (the predicate below) and as a merge TARGET (the finder here).
        is_const = chunk.section is not None and chunk.section.endswith(_CONST_SECTION_SUFFIX)
        is_doc = chunk.kind == "doc"
        line_count = chunk.lines[1] - chunk.lines[0] + 1

        # Find last code chunk in result as merge target (skip imports + constant chunks)
        last_code_idx = next(
            (
                idx for idx in range(len(result) - 1, -1, -1)
                if result[idx].kind == "code"
                and not (result[idx].section is not None and result[idx].section.endswith("> imports"))
                and not (result[idx].section is not None and result[idx].section.endswith(_CONST_SECTION_SUFFIX))
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
            and not is_const
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
# Wave 1p4mf (JS/TS regex fallback): a top-level VALUE constant — `const NAME = <literal>`,
# exported OR not. The RHS first token (quote/backtick/brace/bracket/digit/bool/null) is the
# discriminator: it separates a value const from an arrow fn (`= (`, caught by _JS_ARROW_RE) and
# from a factory/styled/`require` call (`= ident(...)`, an identifier-start RHS). This closes the
# export-only gap (non-exported consts were never chunked) and marks value consts for retrieval.
_JS_VALUE_CONST_RE = re.compile(
    r"^(?:export\s+)?const\s+(\w+)\s*(?::[^=]+)?\s*=\s*"
    r"(?:['\"`\{\[]|-?\d|true\b|false\b|null\b)"
)
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

            # Top-level VALUE constant (exported or not): const NAME = <literal>.
            # Marked with the const section suffix so it is retrievable + merge-excluded, like the
            # tree-sitter path. Checked BEFORE the generic export-const block so a value export
            # (`export const URL = "…"`) is marked, while a styled/function export falls through.
            if not current_class:
                vcm = _JS_VALUE_CONST_RE.match(line)
                if vcm:
                    const_name = vcm.group(1)
                    breadcrumb = f"{stem} > {const_name}"
                    body_lines = [line]
                    # Multi-line object/array/template literal — collect until brackets + backticks
                    # balance (a single-line `const X = 1;` stops immediately).
                    depth = (line.count("{") - line.count("}")
                             + line.count("[") - line.count("]")
                             + line.count("(") - line.count(")"))
                    btick = line.count("`") % 2
                    j = i + 1
                    while j < len(lines) and (depth > 0 or btick):
                        body_lines.append(lines[j])
                        depth += (lines[j].count("{") - lines[j].count("}")
                                  + lines[j].count("[") - lines[j].count("]")
                                  + lines[j].count("(") - lines[j].count(")"))
                        btick = (btick + lines[j].count("`")) % 2
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
                        lines=(i + 1, max(j, i + 1)),
                        section=f"{breadcrumb}{_CONST_SECTION_SUFFIX}",
                        text=f"{breadcrumb}\n\n{code_text}",
                    ))
                    i = j if j > i else i + 1
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


# Wave 1p4mf (JS/TS): a `const` whose RHS is one of these literal value types is a VALUE
# constant (→ constant chunk + " [const]" marker). arrow_function / call_expression (styled
# components, computed values) are functions/components and stay as plain code chunks.
_JS_VALUE_CONST_TYPES = frozenset({
    "number", "string", "object", "array", "true", "false", "null",
    "template_string", "unary_expression", "regex",
})


def _js_const_value_type(declarator) -> str:
    """Tree-sitter type of a JS/TS variable_declarator's RHS value, or '' when absent."""
    val = declarator.child_by_field_name("value")
    if val is None:
        kids = [c for c in declarator.children if c.type != "="]
        val = kids[-1] if len(kids) > 1 else None
    return val.type if val is not None else ""


def _js_is_const_decl(node) -> bool:
    """True when a lexical_declaration's keyword token is `const` (not `let`). Checks the
    keyword node type directly — robust to `export const` (where line text starts with `export`)."""
    return bool(node.children) and node.children[0].type == "const"


def chunk_js_ts_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    """Tree-sitter JS/TS chunker. Returns None if tree-sitter unavailable."""
    ext = PurePosixPath(_normalize_path(path)).suffix.lower()
    lang_key = "typescript" if ext in {".ts", ".tsx", ".mts", ".cts"} else "javascript"
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

    def _enum_member_name(member) -> Optional[str]:
        # Wave 1p4q4: a TS enum member is `property_identifier` (bare) or `enum_assignment`
        # (property_identifier = value). Return the member's name in both shapes.
        if member.type == "property_identifier":
            return source_lines[member.start_point[0]][member.start_point[1]:member.end_point[1]]
        for c in member.children:
            if c.type == "property_identifier":
                return source_lines[c.start_point[0]][c.start_point[1]:c.end_point[1]]
        return None

    def _emit_const_chunk(qname: str, node) -> None:
        breadcrumb = f"{stem} > {qname}"
        start, end = _ts_node_lines(node)
        text = _ts_node_text(node, source_lines)
        chunks.append(Chunk(id=f"{path}::{qname}", path=path, kind="code", language=lang,
                            lines=(start, end), section=f"{breadcrumb}{_CONST_SECTION_SUFFIX}",
                            text=f"{breadcrumb}\n\n{text}"))

    def _process_node(node, class_name: Optional[str] = None):
        nonlocal import_nodes
        t = node.type

        if t == "import_statement":
            import_nodes.append(node)
            return

        if t == "enum_declaration":
            # Wave 1p4q4: TS `enum` / `const enum` — each member becomes a `Enum.Member` constant
            # chunk (members are how TS expresses named constants).
            ename = _symbol_name(node) or "Enum"
            qprefix = f"{class_name}.{ename}" if class_name else ename
            for child in node.children:
                if child.type == "enum_body":
                    for member in child.named_children:
                        if member.type not in ("enum_assignment", "property_identifier"):
                            continue
                        mname = _enum_member_name(member)
                        if mname:
                            _emit_const_chunk(f"{qprefix}.{mname}", member)
            return

        if t in ("internal_module", "module"):
            # Wave 1p4q4: `namespace NS { ... }` (→ internal_module) and the `module NS { ... }`
            # keyword form (→ a top-level `module` node) — recurse into the body, qualifying by NS.
            nsname = _symbol_name(node) or "namespace"
            nsq = f"{class_name}.{nsname}" if class_name else nsname
            for child in node.children:
                if child.type == "statement_block":
                    for stmt in child.children:
                        _process_node(stmt, class_name=nsq)
            return

        if t == "expression_statement":
            # A top-level `namespace`/`module` block parses as expression_statement → internal_module.
            for child in node.children:
                if child.type in ("internal_module", "module"):
                    _process_node(child, class_name=class_name)
            return

        if t == "ambient_declaration":
            # Wave 1p4q4: `declare const X = <value>` → the inner value const; `declare namespace`
            # / `declare module` (→ internal_module / module) and `declare enum` → recurse so the
            # contained consts / enum members are chunked (review C3).
            for child in node.children:
                if child.type in ("lexical_declaration", "variable_declaration",
                                  "internal_module", "module", "enum_declaration"):
                    _process_node(child, class_name=class_name)
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
            # export function Foo / export class Foo / export const Foo = ... / export enum Foo /
            # export namespace NS { ... } (→ internal_module / module — review C3)
            for child in node.children:
                if child.type in ("function_declaration", "class_declaration",
                                  "generator_function_declaration", "enum_declaration",
                                  "internal_module", "module"):
                    _process_node(child, class_name=class_name)
                    return
                if child.type in ("lexical_declaration", "variable_declaration"):
                    # export const Foo = ...
                    is_const = child.type == "lexical_declaration" and _js_is_const_decl(child)
                    for decl in child.children:
                        if decl.type != "variable_declarator":
                            continue
                        name = _symbol_name(decl) or "const"
                        qname = f"{class_name}.{name}" if class_name else name
                        breadcrumb = f"{stem} > {qname}"
                        start, end = _ts_node_lines(node)
                        text = _ts_collapse_body(_ts_node_text(node, source_lines))
                        # Wave 1p4mf: a VALUE const (literal RHS) → constant chunk (marker +
                        # breadcrumb prefix); a function/component const (arrow/call) → code chunk.
                        if is_const and _js_const_value_type(decl) in _JS_VALUE_CONST_TYPES:
                            chunks.append(Chunk(id=f"{path}::{qname}", path=path, kind="code",
                                                language=lang, lines=(start, end),
                                                section=f"{breadcrumb}{_CONST_SECTION_SUFFIX}",
                                                text=f"{breadcrumb}\n\n{text}"))
                        else:
                            chunks.append(Chunk(id=f"{path}::{qname}", path=path, kind="code",
                                                language=lang, lines=(start, end),
                                                section=breadcrumb, text=text))
                    return
            return

        if t in ("lexical_declaration", "variable_declaration"):
            # Top-level const Foo = <value>  /  const Foo = () => ...  /  const Foo = styled(...).
            # A class body routes ONLY method_definition here, so a set `class_name` means this was
            # reached via namespace recursion (review C2) — qualify by it so a NON-export `const`
            # inside `namespace N { const X = 5 }` is chunked as `N.X` (previously a `class_name is
            # None` guard dropped it; only `export const` survived).
            is_const = t == "lexical_declaration" and _js_is_const_decl(node)
            for decl in node.children:
                if decl.type != "variable_declarator":
                    continue
                name = _symbol_name(decl) or "const"
                qname = f"{class_name}.{name}" if class_name else name
                breadcrumb = f"{stem} > {qname}"
                start, end = _ts_node_lines(node)
                text = _ts_collapse_body(_ts_node_text(node, source_lines))
                vtype = _js_const_value_type(decl)
                # Wave 1p4mf: a VALUE const (literal RHS — incl. scalars, previously unchunked)
                # → constant chunk (marker + breadcrumb). Function/component consts (arrow/call)
                # keep the existing plain code-chunk behavior.
                if is_const and vtype in _JS_VALUE_CONST_TYPES:
                    chunks.append(Chunk(id=f"{path}::{qname}", path=path, kind="code", language=lang,
                                        lines=(start, end), section=f"{breadcrumb}{_CONST_SECTION_SUFFIX}",
                                        text=f"{breadcrumb}\n\n{text}"))
                elif vtype in ("arrow_function", "call_expression", "template_string", "object"):
                    # function/component/styled (or a non-const object/template) — plain code chunk
                    chunks.append(Chunk(id=f"{path}::{qname}", path=path, kind="code",
                                        language=lang, lines=(start, end), section=breadcrumb, text=text))

    for node in tree.root_node.children:
        _process_node(node)

    imp = _ts_imports_chunk(import_nodes, source_lines, path, lang, stem)
    if imp:
        chunks.insert(0, imp)

    if not chunks:
        return None
    return split_large_code_chunks(_merge_small_chunks(chunks, scoped=True))


def _go_const_spec_names(spec, source_lines: list[str]) -> list[str]:
    """First-level identifier names declared by a Go const_spec. A const_spec can declare
    multiple targets (``const a, b = 1, 2``), so collect every direct ``identifier`` child."""
    names: list[str] = []
    for c in spec.children:
        if c.type == "identifier":
            names.append(source_lines[c.start_point[0]][c.start_point[1]:c.end_point[1]])
    return names


def _go_const_chunk_name(node, source_lines: list[str]) -> Optional[str]:
    """Chunk NAME for a Go ``const_declaration`` (single OR grouped). Returns the first usable
    identifier across all const_specs — single ``const X =`` -> its name; grouped
    ``const ( A=iota; B )`` block -> its first usable member (the block stays ONE chunk).
    Excludes ONLY the blank identifier ``_``; returns None if none usable (a blank-only
    declaration is skipped). Short names (``Pi``/``KB``/``MB``/``Hz``/``OK``/``ID``) ARE chunked —
    they are common, retrievable Go constants, and dropping them made them unfindable (1p4ls
    delivery review). The CHUNK lane includes every named const-keyword declaration; the graph
    applies its own short-symbol prune separately, so retrieval is not gated on name length here.
    No casing gate — Go const-ness is the ``const`` keyword (MixedCaps/camelCase are normal);
    first-letter case is EXPORT only."""
    for spec in node.children:
        if spec.type != "const_spec":
            continue
        for name in _go_const_spec_names(spec, source_lines):
            if name != "_":
                return name
    return None


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
        elif t == "const_declaration":
            # Wave 1p4mf: package/file-level Go constants. Scope = root-level iteration here, so
            # function-local `const` (nested in function_declaration) is never reached. `var`/
            # grouped `var(...)` are var_declaration and never match. No casing gate (Go const-ness
            # is the keyword; first-letter case = export). Single `const X =` -> ONE chunk; grouped
            # `const ( ... )` (Go's enum, no enum type node) -> ONE chunk for the WHOLE block so a
            # member query still hits it. Blank `const _ =` and <=2-char flag names are skipped.
            cname = _go_const_chunk_name(node, source_lines)
            if cname is not None:
                breadcrumb = f"{stem} > {cname}"
                start, end = _ts_node_lines(node)
                decl_text = _ts_collapse_body(_ts_node_text(node, source_lines))
                chunks.append(Chunk(
                    id=f"{path}::{cname}", path=path, kind="code", language="go",
                    lines=(start, end),
                    section=f"{breadcrumb}{_CONST_SECTION_SUFFIX}",
                    text=f"{breadcrumb}\n\n{decl_text}",
                ))

    imp = _ts_imports_chunk(import_nodes, source_lines, path, "go", stem)
    if imp:
        # insert after namespace if present
        insert_idx = 1 if chunks and chunks[0].section and chunks[0].section.endswith("> namespace") else 0
        chunks.insert(insert_idx, imp)

    if not chunks:
        return None
    return split_large_code_chunks(_merge_small_chunks(chunks, scoped=True))


# Wave 1p4mf (Rust): module/type-level constant detection. ``const_item`` (const NAME: T = …)
# and ``static_item`` (static / static mut) are the const node types; the const/static KEYWORD
# is authoritative (no casing gate). SCOPE is the discriminator — a FUNCTION-LOCAL const/static is
# the SAME node type but lives inside a ``block``; the walker never descends into a ``block`` /
# ``function_item`` body, so only file/module-top-level + impl/trait associated consts are emitted.
_RUST_CONST_NODE_TYPES = ("const_item", "static_item")


def _rust_const_name(node, source_lines: list[str]) -> Optional[str]:
    """Name identifier of a ``const_item`` / ``static_item`` (the FIRST direct ``identifier`` child;
    skips ``visibility_modifier`` for ``pub`` and ``mutable_specifier`` for ``static mut``)."""
    for c in node.children:
        if c.type == "identifier":
            return source_lines[c.start_point[0]][c.start_point[1]:c.end_point[1]]
    return None


def _rust_leading_doc_start(start_line: int, source_lines: list[str]) -> int:
    """Extend a const's start line upward over a contiguous leading ``///`` doc-comment block."""
    start = start_line
    i = start_line - 2  # 0-indexed line directly above the declaration
    while i >= 0 and source_lines[i].lstrip().startswith("///"):
        start = i + 1
        i -= 1
    return start


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

    def _emit_const(node, owner: Optional[str]) -> None:
        # Wave 1p4mf: one constant chunk per const_item / static_item. owner=None → file/module
        # top-level; owner=TypeName → impl/trait associated const (Owner.NAME). Span includes any
        # leading ``///`` doc; value is optional (trait consts may be declaration-only).
        name = _rust_const_name(node, source_lines)
        if not name:
            return
        qname = f"{owner}.{name}" if owner else name
        raw_start, end = _ts_node_lines(node)
        start = _rust_leading_doc_start(raw_start, source_lines)
        decl = "\n".join(source_lines[start - 1:end])
        breadcrumb = f"{stem} > {qname}"
        chunks.append(Chunk(
            id=f"{path}::{qname}", path=path, kind="code", language="rust",
            lines=(start, end),
            section=f"{breadcrumb}{_CONST_SECTION_SUFFIX}",
            text=f"{breadcrumb}\n\n{decl}",
        ))

    def _process(node, impl_name: Optional[str] = None):
        t = node.type
        if t == "use_declaration":
            import_nodes.append(node)
        elif t in _RUST_CONST_NODE_TYPES:
            # file/module top-level const / static (NOT function-local — those live in a block we
            # never descend into). impl_name is None at file scope.
            _emit_const(node, impl_name)
        elif t in ("struct_item", "enum_item", "trait_item"):
            name = _name(node)
            breadcrumb = f"{stem} > {name}"
            start, end = _ts_node_lines(node)
            text = _ts_collapse_body(_ts_node_text(node, source_lines))
            chunks.append(Chunk(id=f"{path}::{name}", path=path, kind="code", language="rust",
                                lines=(start, end), section=breadcrumb, text=text))
            if t == "trait_item":
                # trait associated consts (Owner.NAME); value optional (declaration-only allowed).
                for child in node.children:
                    if child.type == "declaration_list":
                        for member in child.children:
                            if member.type in _RUST_CONST_NODE_TYPES:
                                _emit_const(member, name)
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
                        elif member.type in _RUST_CONST_NODE_TYPES:
                            # impl associated const (Owner.NAME).
                            _emit_const(member, iname)
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


def _java_field_is_static_final(field_node) -> bool:
    """True when a field_declaration's `modifiers` child contains BOTH the `static`
    and `final` keyword tokens — the Java type-constant signal (casing-independent)."""
    for child in field_node.children:
        if child.type == "modifiers":
            kinds = {m.type for m in child.children}
            return "static" in kinds and "final" in kinds
    return False


def _java_declarator_name(declarator, source_lines: list[str]) -> Optional[str]:
    """Identifier name of a variable_declarator, or None."""
    name = declarator.child_by_field_name("name")
    if name is None:
        for c in declarator.children:
            if c.type == "identifier":
                name = c
                break
    if name is None:
        return None
    return source_lines[name.start_point[0]][name.start_point[1]:name.end_point[1]]


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

    def _java_body_members(body_node):
        # Direct body members; for enums the constants/fields live one level deeper
        # under `enum_body_declarations` (after the enum_constant list).
        for m in body_node.children:
            if m.type == "enum_body_declarations":
                yield from m.children
            else:
                yield m

    def _emit_java_constants(members, owner_qname: str) -> None:
        # Wave 1p4mf: one chunk per type-level constant identifier. The MODIFIER PAIR
        # `static final` is the gate (field_declaration); interface `constant_declaration`
        # is implicitly static final. NO casing gate. Per-NAME for multi-declarators.
        for member in members:
            if member.type == "field_declaration":
                if not _java_field_is_static_final(member):
                    continue          # instance `final`, mutable `static`, plain field
            elif member.type != "constant_declaration":
                continue              # not a constant member (method/enum_const/etc.)
            start, end = _ts_node_lines(member)
            decl_text = _ts_node_text(member, source_lines)
            for decl in member.children:
                if decl.type != "variable_declarator":
                    continue
                cname = _java_declarator_name(decl, source_lines)
                if not cname:
                    continue
                qname = f"{owner_qname}.{cname}"
                breadcrumb = f"{stem} > {qname}"
                chunks.append(Chunk(
                    id=f"{path}::{qname}", path=path, kind="code", language="java",
                    lines=(start, end),
                    section=f"{breadcrumb}{_CONST_SECTION_SUFFIX}",
                    text=f"{breadcrumb}\n\n{decl_text}",
                ))

    def _process_class(class_node, class_name: str):
        for child in class_node.children:
            if child.type in ("class_body", "interface_body", "enum_body"):
                members = list(_java_body_members(child))
                for member in members:
                    if member.type in ("method_declaration", "constructor_declaration"):
                        name = _name(member)
                        qname = f"{class_name}.{name}"
                        breadcrumb = f"{stem} > {qname}"
                        start, end = _ts_node_lines(member)
                        text = _ts_collapse_body(_ts_node_text(member, source_lines))
                        chunks.append(Chunk(id=f"{path}::{qname}", path=path, kind="code",
                                            language="java", lines=(start, end),
                                            section=breadcrumb, text=text))
                    elif member.type in ("class_declaration", "interface_declaration",
                                         "enum_declaration"):
                        # Nested type → Outer.Inner.CONST qualification.
                        _process_class(member, f"{class_name}.{_name(member)}")
                # Wave 1p4mf: type-level constants for this class/interface/enum body.
                _emit_java_constants(members, class_name)

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


# Wave 1p4mf (C#): a type-member constant is a `field_declaration` with the `const`
# modifier, OR with BOTH `static` and `readonly`. Modifiers appear as `modifier`
# child nodes whose source text is the keyword. NO casing gate (idiomatic PascalCase).
def _csharp_field_modifier_set(field_node, source_lines: list[str]) -> set[str]:
    mods: set[str] = set()
    for c in field_node.children:
        if c.type == "modifier":
            s, e = c.start_point, c.end_point
            mods.add(source_lines[s[0]][s[1]:e[1]])
    return mods


def _csharp_is_const_field(field_node, source_lines: list[str]) -> bool:
    mods = _csharp_field_modifier_set(field_node, source_lines)
    # const field OR the full static+readonly pair (static-alone / readonly-alone excluded)
    return "const" in mods or ("static" in mods and "readonly" in mods)


def _csharp_declarator_names(field_node, source_lines: list[str]) -> list[str]:
    # One name per `variable_declarator` (first `identifier` child) → per-name multi-declarator.
    names: list[str] = []
    for vd in field_node.children:
        if vd.type != "variable_declaration":
            continue
        for decl in vd.children:
            if decl.type != "variable_declarator":
                continue
            for ic in decl.children:
                if ic.type == "identifier":
                    s, e = ic.start_point, ic.end_point
                    names.append(source_lines[s[0]][s[1]:e[1]])
                    break
    return names


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
                    # Wave 1p4mf: type-member constants — `const` field OR `static readonly`
                    # pair. One chunk per declarator name; private const included; method-body
                    # local `const` is a `local_declaration_statement` (not a field_declaration)
                    # so it never reaches here. Marker suffix keeps it out of _merge_small_chunks.
                    elif member.type == "field_declaration" and _csharp_is_const_field(member, source_lines):
                        start, end = _ts_node_lines(member)
                        decl_text = _ts_node_text(member, source_lines)
                        for const_name in _csharp_declarator_names(member, source_lines):
                            qname = f"{type_name}.{const_name}"
                            breadcrumb = f"{stem} > {qname}"
                            chunks.append(Chunk(id=f"{path}::{qname}", path=path, kind="code",
                                                language="csharp", lines=(start, end),
                                                section=f"{breadcrumb}{_CONST_SECTION_SUFFIX}",
                                                text=f"{breadcrumb}\n\n{decl_text}"))

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


def _kotlin_property_is_const(node) -> bool:
    """True if a Kotlin property_declaration carries a `const` modifier (compile-time const val).

    Wave 1p4mf: the const token — not casing — gates the chunk. A plain val/var
    property has no modifiers/property_modifier/const child and returns False.
    """
    if node.type != "property_declaration":
        return False
    for child in node.children:
        if child.type == "modifiers":
            for mod_node in child.children:
                if mod_node.type == "property_modifier":
                    for leaf in mod_node.children:
                        if leaf.type == "const":
                            return True
    return False


def _kotlin_property_name(node, source_lines: list[str]) -> Optional[str]:
    """Return the single declared name of a Kotlin property_declaration, or None."""
    for child in node.children:
        if child.type == "variable_declaration":
            for leaf in child.children:
                if leaf.type in ("identifier", "simple_identifier"):
                    return source_lines[leaf.start_point[0]][leaf.start_point[1]:leaf.end_point[1]]
    return None


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

    def _emit_const(node, owner: Optional[str]) -> None:
        # Wave 1p4mf: chunk a module/object/companion-level `const val` so code_ask can
        # answer "what value is X". SCOPE is the discriminator — only property_declaration
        # nodes reached from file top-level / an object body / a companion-object body are
        # passed here, so function-body-local `const val` (same node type + same modifier)
        # is never emitted. owner=None -> file-level; owner=Type -> "{Type}.{NAME}".
        if not _kotlin_property_is_const(node):
            return
        cname = _kotlin_property_name(node, source_lines)
        if not cname:
            return
        qname = f"{owner}.{cname}" if owner else cname
        start, end = _ts_node_lines(node)
        decl_text = _ts_node_text(node, source_lines)
        breadcrumb = f"{stem} > {qname}"
        chunks.append(Chunk(
            id=f"{path}::{qname}", path=path, kind="code", language="kotlin",
            lines=(start, end),
            section=f"{breadcrumb}{_CONST_SECTION_SUFFIX}",
            text=f"{breadcrumb}\n\n{decl_text}",
        ))

    def _process(node):
        t = node.type
        if t == "package_header":
            breadcrumb = f"{stem} > namespace"
            chunks.append(Chunk(id=f"{path}::__namespace__", path=path, kind="code",
                                language="kotlin", lines=_ts_node_lines(node), section=breadcrumb,
                                text=f"{breadcrumb}\n\n{_ts_node_text(node, source_lines)}"))
        elif t in ("import_list", "import"):
            import_nodes.append(node)
        elif t == "property_declaration":
            # Wave 1p4mf: file top-level `const val` (owner=None). A plain val/var is not const.
            _emit_const(node, None)
        elif t in ("class_declaration", "object_declaration", "interface_declaration"):
            name = _name(node)
            breadcrumb = f"{stem} > {name}"
            start, end = _ts_node_lines(node)
            decl_line = source_lines[node.start_point[0]].strip()
            chunks.append(Chunk(id=f"{path}::{name}.__decl__", path=path, kind="code",
                                language="kotlin", lines=(start, start), section=breadcrumb,
                                text=f"{breadcrumb}\n\n{decl_line}"))
            is_object = t == "object_declaration"
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
                        elif is_object and member.type == "property_declaration":
                            # `object Foo { const val X = ... }` — X scoped to the object
                            _emit_const(member, name)
                        elif member.type == "companion_object":
                            # `class Foo { companion object { const val X = ... } }`
                            # X is accessed via Foo, so qualify with the enclosing class name
                            for comp_child in member.children:
                                if comp_child.type == "class_body":
                                    for comp_member in comp_child.children:
                                        if comp_member.type == "property_declaration":
                                            _emit_const(comp_member, name)
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
    # Ruby encodes a class/module name as a `constant` node (capital-initial); needed so a
    # Ruby class-scoped constant resolves its owner (Service.RETRY_LIMIT, not anonymous.RETRY_LIMIT).
    "constant",
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
    const_emitter: Optional[Callable] = None,
    scoped: bool = True,
) -> Optional[list[Chunk]]:
    """Walk a tree-sitter parse tree and emit declaration-boundary code chunks.

    Wave 1p4mf: when ``const_emitter`` is provided it is invoked for every top-level node
    (``owner=None``) and every class-body member (``owner=<class qname>``) as
    ``const_emitter(node, owner, emit_const)``. The callback inspects the node (its grammar type +
    modifiers/LHS + scope) and calls ``emit_const(qname, decl_node)`` once per constant it finds —
    function/block locals are never reached because methods are emitted, not descended. The emitter
    is dormant by default (``None`` → identical legacy behavior)."""
    path = _normalize_path(path)
    stem = _file_stem(path)
    tree = _ts_parse(lang_key, source)
    if tree is None:
        return None

    source_lines = source.splitlines()
    chunks: list[Chunk] = []
    import_nodes: list = []

    def emit_const(qname: str, decl_node) -> None:
        """Append one constant chunk: kind=code, the " [const]" merge-excluded suffix, and
        breadcrumb-prefixed text carrying the declaration value (mirrors the Python/JS const work)."""
        breadcrumb = f"{stem} > {qname}"
        start, end = _ts_node_lines(decl_node)
        chunks.append(Chunk(
            id=f"{path}::{qname}",
            path=path,
            kind="code",
            language=language,
            lines=(start, end),
            section=f"{breadcrumb}{_CONST_SECTION_SUFFIX}",
            text=f"{breadcrumb}\n\n{_ts_node_text(decl_node, source_lines)}",
        ))

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
            # Nested type (Swift struct/enum/class all parse as class_declaration; likewise other
            # langs' nested classes): descend under its QUALIFIED owner so a member constant/method
            # is attributed to the nested type (Outer.Inner.x), not flattened onto the outer type.
            # Was: recursed with the unchanged class_name, so e.g. `static let maxRetries` inside a
            # nested struct was recorded as Outer.maxRetries — diverging from the graph lane (which
            # nests correctly) and making the natural Inner.x query unresolvable (1p5k0).
            if child.type in class_node_types:
                nested = _ts_node_name(child, source_lines)
                nested_qname = f"{class_name}.{nested}" if nested != "anonymous" else class_name
                _emit_code(child, nested_qname, decl_only=True)
                _walk_class_members(child, nested_qname)
                continue
            if const_emitter is not None:
                const_emitter(child, class_name, emit_const)
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
        # Wave 1p4mf: top-level fall-through (not a class/method/namespace/import) — a constant
        # candidate. The callback decides (by node type + scope); owner=None ⇒ module/file scope.
        if const_emitter is not None:
            const_emitter(node, None, emit_const)

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


def _swift_property_has_static(node) -> bool:
    """True when a Swift property_declaration carries a `static` (or type-level `class`) modifier
    — i.e. it is a TYPE constant (`static let`/`static var`), not an instance field. Instance
    `let`/`var`, `lazy var`, and `@Published/@State var` have no static property_modifier."""
    for child in node.children:
        if child.type == "modifiers":
            for mod in child.children:
                if mod.type == "property_modifier":
                    for tok in mod.children:
                        if tok.type in ("static", "class"):
                            return True
    return False


def _swift_property_is_computed(node) -> bool:
    """True when a property_declaration is a computed property (`var x: T { ... }`) — it stores
    no value, so it is not a constant even when `static`."""
    return any(child.type == "computed_property" for child in node.children)


def _swift_property_names(node) -> list[str]:
    """Each bound identifier of a property_declaration, in source order. Handles grouped
    multi-declarators (`let a = 1, b = 2` -> [a, b]) and tuple destructuring
    (`let (x, y) = ...` -> [x, y]) by recursing through nested patterns."""
    names: list[str] = []

    def _descend(pat) -> None:
        for child in pat.children:
            if child.type == "simple_identifier":
                txt = child.text.decode().strip()
                if txt:
                    names.append(txt)
            elif child.type in ("pattern", "tuple_pattern"):
                _descend(child)

    for child in node.children:
        if child.type == "pattern":
            _descend(child)
    return names


def _swift_const_emitter(node, owner, emit) -> None:
    """Wave 1p4mf Swift constant detector for the _ts_generic_structured_chunker const hook. Wired
    at BOTH top-level (owner=None -> file/global `let`/`var`) and type-member scope
    (owner=TypeName -> `static let`/`static var` + enum cases). Scope is the discriminator: the
    walker never descends into func/init/computed bodies, so locals, `if let`/`guard let`, and
    `for x in` bindings (same node type) are never reached. No casing gate — Swift constants are
    lowerCamelCase. ``emit(qname, decl_node)`` appends the const chunk."""
    t = node.type
    if t == "property_declaration":
        if _swift_property_is_computed(node):
            return  # computed var stores no value
        # Type scope: only `static let`/`static var` are constants (instance let/var = field).
        if owner is not None and not _swift_property_has_static(node):
            return
        for name in _swift_property_names(node):
            emit(f"{owner}.{name}" if owner else name, node)
    elif t == "enum_entry":
        # Each enum case (and each name in `case a, b`) is a constant.
        for child in node.children:
            if child.type == "simple_identifier":
                txt = child.text.decode().strip()
                if txt:
                    emit(f"{owner}.{txt}" if owner else txt, node)


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
        const_emitter=_swift_const_emitter,
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


# Wave 1p4mf (Ruby): an `assignment` LHS of one of these types is a local / ivar / cvar /
# global, NEVER a constant — excluded. A `constant` / `scope_resolution` / `left_assignment_list`
# LHS is a constant (the grammar encodes capital-initial as the `constant` node type, so no
# casing re-grep). Class/module NAMEs and DSL `call`s are not `assignment` nodes and are skipped.
_RUBY_LOCAL_LHS_TYPES = frozenset({"identifier", "instance_variable", "class_variable", "global_variable"})


def _ruby_scope_resolution_name(node) -> str:
    """Last `::` segment of a scope_resolution LHS (Config::SETTING -> SETTING)."""
    nm = node.child_by_field_name("name")
    if nm is not None:
        return nm.text.decode().strip()
    return node.text.decode().split("::")[-1].strip()


def _ruby_const_lhs_names(lhs):
    """Yield constant NAME(s) for an assignment LHS; empty for a local/ivar/cvar/global LHS."""
    t = lhs.type
    if t == "constant":
        yield lhs.text.decode().strip()
    elif t == "scope_resolution":
        yield _ruby_scope_resolution_name(lhs)
    elif t == "left_assignment_list":  # multi-target: A_URL, B_URL = ...  -> per-name
        for child in lhs.children:
            if child.type == "constant":
                yield child.text.decode().strip()
            elif child.type == "scope_resolution":
                yield _ruby_scope_resolution_name(child)


def _ruby_const_emitter(node, owner, emit) -> None:
    """const_emitter callback for the _ts_generic_structured_chunker hook. node = a candidate stmt;
    owner = ClassName or None; emit(qname, decl_node) appends a [const] chunk. Wired at BOTH file
    top-level (owner=None) and class/module member scope (owner=ClassName) via the walker's
    recursion through `body_statement`; method bodies are emitted (not descended) so a const inside
    a method is never reached. An identifier/ivar/cvar/global LHS is a local, never a constant."""
    if node.type != "assignment":
        return
    lhs = node.child_by_field_name("left")
    if lhs is None or lhs.type in _RUBY_LOCAL_LHS_TYPES:
        return
    for name in _ruby_const_lhs_names(lhs):
        if name:
            emit(f"{owner}.{name}" if owner else name, node)


def chunk_ruby_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    return _ts_generic_structured_chunker(
        "ruby", source, path, "ruby",
        class_node_types=frozenset({"class", "module", "singleton_class"}),
        method_node_types=frozenset({"method", "singleton_method"}),
        const_emitter=_ruby_const_emitter,
    )


# Wave 1p4mf: PHP constant detection for the generic structured walker.
# `string` (single-quote) / `encapsed_string` (double-quote) are the only define() name
# literals we accept; a computed name (binary_expression) is excluded.
_PHP_DEFINE_NAME_LITERALS = frozenset({"string", "encapsed_string"})


def _php_string_literal_value(lit_node) -> str:
    """Inner value of a php `string`/`encapsed_string` literal (quotes stripped)."""
    sc = next((c for c in lit_node.children if c.type == "string_content"), None)
    if sc is not None:
        return sc.text.decode()
    raw = lit_node.text.decode()  # empty literal '' has no string_content
    return raw[1:-1] if len(raw) >= 2 else raw


def _php_const_emitter(node, owner, emit) -> None:
    """Self-contained PHP const callback for the _ts_generic_structured_chunker hook.
    (node, owner, emit) where emit(qname, decl_node) appends the const chunk. owner is None at
    file/namespace top-level, ClassName inside a class/interface/trait/enum body. NO casing gate —
    `const`/`define` is the signal. NOTE: constants inside a BRACED `namespace App { ... }` block
    are not reached (the walker treats namespace_definition as one chunk); the dominant PSR-4
    semicolon form `namespace App;` works (its const/define are root-level siblings)."""
    t = node.type
    # (1) `const` — file/namespace top-level AND class/interface/trait/enum body.
    #     One emit per const_element (iterates `const A=1, B=2`). decl_node = whole statement.
    if t == "const_declaration":
        for child in node.children:
            if child.type == "const_element":
                name_node = next((c for c in child.children if c.type == "name"), None)
                if name_node is not None:
                    name = name_node.text.decode().strip()
                    if name:
                        emit(f"{owner}.{name}" if owner else name, node)
        return
    # (2) legacy top-level define('NAME', value) — only at file/namespace scope (owner is None).
    if owner is None and t == "expression_statement":
        call = next((c for c in node.children if c.type == "function_call_expression"), None)
        if call is None:
            return
        callee = next((c for c in call.children if c.type == "name"), None)
        if callee is None or callee.text.decode().strip() != "define":
            return  # excludes defined()/constant() reads and any other call
        args = next((c for c in call.children if c.type == "arguments"), None)
        if args is None:
            return
        arg_nodes = [c for c in args.children if c.type == "argument"]
        if not arg_nodes:
            return
        first_lit = next((c for c in arg_nodes[0].children if c.is_named), None)
        if first_lit is None or first_lit.type not in _PHP_DEFINE_NAME_LITERALS:
            return  # define($computed, …) / binary_expression name -> skip
        name = _php_string_literal_value(first_lit).strip()
        if name:
            emit(name, node)


def chunk_php_treesitter(source: str, path: str) -> Optional[list[Chunk]]:
    return _ts_generic_structured_chunker(
        "php", source, path, "php",
        class_node_types=frozenset({"class_declaration", "interface_declaration", "trait_declaration", "enum_declaration"}),
        method_node_types=frozenset({"function_definition", "method_declaration"}),
        namespace_node_types=frozenset({"namespace_definition"}),
        const_emitter=_php_const_emitter,
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


def _extract_python_module_docstring(source: str, filename: str = "<unknown>") -> Optional[str]:
    try:
        tree = ast.parse(source, filename=filename)
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


def _chunk_code_summary(
    source: str,
    path: str,
    language: str,
    *,
    allow_module_fallback: bool = True,
) -> Optional[Chunk]:
    """Emit one kind='code-summary' chunk per source file: module docstring +
    top-level symbols.

    Wave 1p3iv (1p3jc): when neither a docstring nor extractable symbols are
    found but the file has non-comment content (re-export `__init__.py`,
    TypeScript barrel `index.ts`, Go single-file packages, Rust `mod.rs`,
    etc.), fall back to emitting the top-level non-comment lines so the
    package's public surface is semantically searchable. Without this
    fallback, `code_search` misses re-export files entirely; today only
    `code_keyword` (text-backed) finds them. Language-agnostic — works for
    any code file because the fallback only fires when language-specific
    symbol extraction yields nothing.
    """
    if not source.strip():
        return None
    if language == "python":
        docstring = _extract_python_module_docstring(source, filename=path) or _extract_leading_comment(source)
    else:
        docstring = _extract_leading_comment(source)
    symbols = _extract_code_symbols(source, language)
    if docstring or symbols:
        parts = []
        if docstring:
            parts.append(docstring)
        if symbols:
            parts.append("Symbols: " + ", ".join(symbols))
        text = "\n".join(parts)
    else:
        # Wave 1p3iv (1p3jc): symbolless-code-file fallback.
        if not allow_module_fallback:
            return None
        fallback = _extract_module_content_lines(source, language)
        if not fallback:
            return None
        total_lines = source.count("\n") + 1
        return Chunk(
            id=f"{path}::__module__",
            path=path,
            kind="code",
            language=language,
            lines=(1, total_lines),
            section=_file_stem(path),
            text=fallback,
        )
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


# Wave 1p3iv (1p3jc): per-language comment-line prefixes. Used by the
# symbolless-code-file fallback in `_chunk_code_summary` to skip comment
# lines when building a module-summary text body. Unknown languages get a
# permissive default that covers the most common shells.
_MODULE_SUMMARY_COMMENT_PREFIXES = {
    "python": ("#",),
    "bash": ("#",),
    "shell": ("#",),
    "ruby": ("#",),
    "perl": ("#",),
    "yaml": ("#",),
    "toml": ("#",),
    "hcl": ("#",),
    "javascript": ("//", "/*", "*"),
    "typescript": ("//", "/*", "*"),
    "go": ("//", "/*", "*"),
    "rust": ("//", "/*", "*"),
    "java": ("//", "/*", "*"),
    "kotlin": ("//", "/*", "*"),
    "swift": ("//", "/*", "*"),
    "scala": ("//", "/*", "*"),
    "csharp": ("//", "/*", "*"),
    "c": ("//", "/*", "*"),
    "cpp": ("//", "/*", "*"),
    "objc": ("//", "/*", "*"),
    "php": ("//", "#", "/*", "*"),
    "sql": ("--", "/*", "*"),
    "html": ("<!--",),
    "xml": ("<!--",),
}

_MODULE_SUMMARY_MAX_LINES = 50


def _extract_module_content_lines(source: str, language: str) -> Optional[str]:
    """Return non-blank, non-comment top-level lines from ``source`` (up to
    ``_MODULE_SUMMARY_MAX_LINES``) for use as a fallback summary body when
    no docstring or symbols are extractable.

    Wave 1p3iv (1p3jc): gives `code_search` a foothold on re-export files,
    barrel files, single-file packages, and module-level constant
    declarations that would otherwise be invisible to semantic search.
    """
    prefixes = _MODULE_SUMMARY_COMMENT_PREFIXES.get(
        language, ("//", "#", "--", "/*", "<!--")
    )
    out: list[str] = []
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.startswith(p) for p in prefixes):
            continue
        out.append(stripped)
        if len(out) >= _MODULE_SUMMARY_MAX_LINES:
            break
    if not out:
        return None
    return "\n".join(out)


_WAVEFRAMEWORK_MARKER_BEGIN_RE = re.compile(
    r"<!--\s*waveframework:[\w:-]+\s+begin\s*-->"
)
_WAVEFRAMEWORK_MARKER_END_RE = re.compile(r"<!--\s*end\s*-->")


def _strip_waveframework_marker_regions(source: str) -> str:
    """Return source with generated Wave Framework marker regions removed.

    Used only as a zero-content guard before dispatch: if a file contains
    nothing outside generated marker regions, it should emit zero semantic
    chunks. Files with hand-authored content outside the markers continue
    through the normal chunking path unchanged.
    """
    lines: list[str] = []
    inside_marker = False
    for line in source.splitlines():
        if not inside_marker and _WAVEFRAMEWORK_MARKER_BEGIN_RE.search(line):
            inside_marker = True
            continue
        if inside_marker:
            if _WAVEFRAMEWORK_MARKER_END_RE.search(line):
                inside_marker = False
            continue
        lines.append(line)
    return "\n".join(lines)


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


# doc-summary is excluded: its `section` is the literal "doc-summary" sentinel (not a real heading),
# so prefixing it would inject a meaningless token into the embedding. The summary text already opens
# with the H1 title and carries a real "Sections: …" breadcrumb (see _chunk_doc_summary), so it needs
# no injection. (Mirrors the code-summary exclusion.)
_DOCS_BREADCRUMB_KINDS = ("doc", "seed", "prompt")


def _inject_docs_breadcrumb(chunks: list[Chunk]) -> list[Chunk]:
    """Prepend the section breadcrumb to docs-chunk embedded text so heading/topic
    context reaches the embedding vector (NL→docs retrieval +10pp on the 32-query eval;
    change 1p4w9-enh docs-chunk-context-injection). Docs-kind only — code chunks already
    carry the symbol name in the body and prefixing regresses code retrieval. Idempotent:
    skips chunks whose text already opens with the breadcrumb (e.g. docstring chunks whose
    text is built from the breadcrumb)."""
    for c in chunks:
        if c.kind in _DOCS_BREADCRUMB_KINDS:
            section = (c.section or "").strip()
            if section and not (c.text or "").startswith(section):
                c.text = f"{section}\n{c.text}"
    return chunks


def chunk_file(source: str, path: str) -> list[Chunk]:
    """Dispatch to the appropriate chunker; then apply the universal oversized-chunk guard.

    Wave 1p3b9 (1p397): the universal guard at the end ensures every emitted
    chunk is ≤ ``MAX_CHUNK_CHARS`` regardless of which dispatch branch
    produced it. Code branches already apply ``split_large_code_chunks``
    per-branch; the universal pass here is idempotent on those (chunks
    already at or under the cap pass through unchanged). The load-bearing
    case is non-code dispatch paths (markdown / doc / seed / prompt / plain
    text / YAML / JSON / TOML / HTML / XML) that previously emitted unbounded
    chunks the embedder would silently truncate.
    """
    if source.strip() and not _strip_waveframework_marker_regions(source).strip():
        return []
    # Inject the docs breadcrumb BEFORE the oversized guard so split_large_chunks
    # re-caps any chunk the prefix pushes over MAX_CHUNK_CHARS.
    return split_large_chunks(_inject_docs_breadcrumb(_chunk_file_dispatch(source, path)))


def _chunk_file_dispatch(source: str, path: str) -> list[Chunk]:
    """The original chunk-by-extension dispatch logic. See ``chunk_file``."""
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
        summary = _chunk_code_summary(
            source, normalized, "python", allow_module_fallback=False
        )
        if summary:
            chunks = [summary] + chunks
        else:
            module_chunk = _chunk_code_summary(
                source, normalized, "python", allow_module_fallback=True
            )
            if module_chunk:
                chunks = [module_chunk]
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
        s = _chunk_code_summary(
            source, normalized, language, allow_module_fallback=False
        )
        if s:
            return [s] + chunks
        module_chunk = _chunk_code_summary(
            source, normalized, language, allow_module_fallback=True
        )
        return [module_chunk] if module_chunk else chunks

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
