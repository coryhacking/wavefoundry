#!/usr/bin/env python3
"""Graph index extraction and persistence for Wavefoundry."""
from __future__ import annotations

import ast
import functools
import importlib
import hashlib
import json
import os
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
GRAPH_BUILDER_VERSION = "31"  # Wave 1p61v (ts-symbol-kind-extraction-faithfulness): TS/JS type-shape members are no longer mislabeled `function`. A `type_alias_declaration` now extracts as kind="type" and an interface/object-type `property_signature` (a `: T` data member) as kind="property" (method *signatures* keep `function`) — previously both fell through to the default `function`, so `code_outline`-invisible `: string` fields and `export type` aliases rendered as `(function)` entry points in the codebase map (teton p60n field trace, Issue 1). Plus a registration-site faithfulness guard (`_ts_is_emittable_symbol_name`): a definition whose picked name is the reserved word `function` (anonymous `function (…){}` expressions) or a non-identifier route-path token (`/`) is no longer registered as a junk symbol (Issue 2). Node KIND-set + node-set shape change → bump (consumer graph caches re-extract). Conservative: contextual keywords that are legal identifiers (`type`, `async`, `fn`, …) are NOT rejected, so no real callable is dropped. Previous bump (1p5c4, guard-oversized-files-indexing): files over the tree-sitter parse cap (default 2 MB; override WAVEFOUNDRY_MAX_TS_PARSE_BYTES / `indexing.max_treesitter_parse_bytes`) now SKIP AST graph extraction, and files over the hard size cap are dropped from the walk entirely — so oversized files contribute no graph nodes. Bump forces re-extraction so any large file parsed under v29 has its stale nodes pruned. Wave 1p4up (member-access-constant-reads): a CONSTANT accessed via a qualified member expression (`Status.ACTIVE`, `SolarisConstants.Network.userAgent`, `Outer.Inner.TOKEN`, Ruby/PHP `A::B::C`) now produces a function→constant `reads` edge by EXACT qualified-name match (const-kind-gated; the qualifier disambiguates so a same-leaf param/import/bare-call can't match). Faithfulness guards: F1 full-qname (not `_simple_name` partial key), F2 reject `this`/`self`/`super`/`cls`, F4 qualifier-shadow (a member-access read whose head is a function param/local is dropped — `func_locals` from per-language binding nodes) + the property/trailing leaf of a member access is no longer also buffered as a bare read (member-path resolves it instead). New `reads` edges → node/edge-set shape change → bump (consumer graph caches re-extract). Wave 1p4q4 review (28) (D1/D2): namespace-scoped enum member nodes now carry the enclosing namespace prefix (`NSA.Inner.AAA` vs `NSB.Inner.AAA` — no cross-namespace collision/clobber), and constant nodes are EXEMPT from the ≤2-char short-symbol prune so short members (`Status.OK`/`Dir.Up`) resolve. Node-set shape change → bump (consumer graph caches re-extract). Wave 1p4q4 (27): TS `enum`/`const enum` members are now `kind="constant"` graph nodes (`Enum.Member`), child of the enum type node. Wave 1p4ls (26) (graph-constant-nodes-and-references): module-/type-level CONSTANT declarations are now graph nodes (kind="constant", carrying a simple-literal `value` where the RHS is a literal) across all core languages, plus a faithfulness-gated function→constant `reads` edge (same-scope + explicitly-imported only; never binds a coincidental same-name twin — symbol_lookup uniqueness + a const-kind gate + a local-shadow guard). Consumers surface them: code_definition resolves a constant name; code_references lists readers in a distinct `reads` bucket (NOT merged into callers); graph_neighbors includes constants when `reads` is requested. `reads` is OPT-IN for default 1-hop traversal (excluded when no explicit relations are passed, so a hot constant does not balloon neighbor sets / 1p4hu expansion) and stays OUT of the impact/call default relations; constant nodes + `reads` edges are excluded from clustering (CLUSTER_BUILDER_VERSION 8→9, no community-label shift). resolve_symbol is kind-aware (a constant sharing a simple name no longer shadows a callable lookup). Detection reuses the 1p4mf chunk-lane per-language predicates (one detector, two consumers — Req-7); the graph lane is BROADER where it lands naturally (class/type-level constants; Swift enum cases; Go grouped-const per member). NOTE: TS `enum`/`const enum` members ARE emitted as constant nodes (`Enum.Member`) — delivered in 1p4q4 (see the v27 line at the top). Kotlin bare top-level/object `val` (no `const`) stays `kind="variable"` (an immutable binding is not a compile-time constant — won't-do). Previous bump (1p4eq, cross-file-resolution-followups): one consolidated bump covering five graph-shaping changes: (1p4ef) fix a leaked `qualified` loop var that injected phantom qualified_index candidates for collapsed/basename-merged nodes (C#/Swift/Rust/Ruby) and silently suppressed unique cross-file resolution; (1p4er) same-package/same-directory disambiguation fallback for ambiguous receivers used WITHOUT an import (Java field miss, `JreCompat.canAccess`), GATED to Java/Kotlin/Go (same-dir ⇒ same-package visibility; Python/JS/TS/Rust/C# excluded); (1p4et) Go methods now keyed `Type.method` (was bare `method`) + package-qualified receiver inference (`var h foo.Helper` → `foo.Helper`, package PRESERVED and resolved by the candidate's package directory); (1p4eu) Rust `Type::assoc_fn()` resolution + struct-literal/`::new()` let-binding type inference; (1p4ev) C# namespace-membership disambiguation (own-namespace ∪ `using`), the namespace derived from each file's DECLARED namespace nodes by longest-prefix (nesting-proof), NOT by fixed-segment qname stripping. FAITHFULNESS FIXES (1p4eq adversarial verification): the 1p4et/1p4ev paths above already incorporate the over-resolution fixes the verification caught — dropping the Go package qualifier bound a co-located cross-package twin, and fixed-segment C# namespace stripping mis-derived a nested-class caller's namespace and bound a coincident sibling twin; both now stay external unless a unique package/namespace-faithful candidate matches. COVERAGE SCOPE — synthetic-fixture tests only, NOT yet validated against a real consumer project: same-package = Java; cross-file method/assoc-fn = Go + Rust; ambiguous-receiver namespace membership = C#. Each carries an adversarial "never binds the wrong twin / stays external" test. **Correction to the v24 line below:** v24 advertised its `imports`-edge disambiguation as "language-agnostic (Python + Java/Kotlin/C#/Go)" — that was over-stated; it fired ONLY for Python + Java (per-type imports), and was dead code for C#/Go/Rust (their import heads are namespaces/packages, not type names) until v25 supplied the per-language mechanisms above. Previous bump (1p47e 1p470): Python sibling-loader return-type inference + cross-file import disambiguation. v24 resolves the lazy-loader blast-radius hole — `gq = _load_graph_query()` (→ `_load_script("graph_query")`) and direct `v = _load_script("mod")` now bind `v.Class.method()` / `v.func()` to the loaded module's symbols (previously emitted NO edge because `v` had no known type; e.g. `GraphQueryIndex.from_root` was called from 14 sites with 0 incoming edges). Also adds import-edge-based disambiguation in the cross-file rewrite pass: an ambiguous `external::Type.method` (multiple same-simple-name candidates) is disambiguated via the source file's `imports` edge for `Type`, language-agnostically (Python + Java/Kotlin/C#/Go). Previous bump (1p2q3 / 1p2tz post-ship-5 1.3.16): TS/JS symbol-table promotion. Intra-file (and cross-file unique-simple-name) calls where `_ts_resolve_target` bound directly to a project node previously landed as `EXTRACTED` even though the binding required an exact match in `symbol_lookup`. Teton field validation on the v22 stable state showed `getRootToken` and similar intra-file arrow-const targets had only `EXTRACTED` incoming edges — invisible to the `receiver_resolved` attribution bucket — despite the symbol being correctly resolved at extraction time. v23 promotes these to `RECEIVER_RESOLVED` for TS/JS only: when `_ts_resolve_target` returns a non-`external::` project node (i.e. the call site bound to a locally-defined symbol or to the unique cross-file simple-name match) the edge is high-confidence by construction. Affects TS/JS only — other languages route through their per-language receiver resolvers + the cross-file rewrite pass and are out of scope for this round. Previous bump (1.3.12 v21→v22): TS/JS relative-import path resolution into import_targets. v21 emitted arrow-const function nodes but +9,379 of the new TS edges landed as EXTRACTED rather than RECEIVER_RESOLVED because intra-package callers using relative imports (`import { foo } from './events'`) had `import_targets[foo]` populated with the lossy `external::events` form. The cross-file rewrite pass then promoted the edge to the right project node but kept it at EXTRACTED confidence. v22 extracts the raw module specifier before `_ts_clean_name` strips the `./` prefix, resolves relative imports against the source file's directory, then runs the same barrel walk + import_targets binding as the aliased path. The +9,379 EXTRACTED edges Teton observed in v21 → v22 should migrate to RECEIVER_RESOLVED for any intra-package direct call to a relatively-imported arrow-const. Affects TS/JS only. Previous bump (1.3.11 v20→v21) was the arrow-const node-emission half — v22 completes the receiver-type attribution half. Modern TS code uses `export const foo = async (args) => { ... }` as the dominant function shape (Teton-confirmed: ALL backend functions on their 12k-node Nx monorepo are arrow-const, zero `function` declarations). Tree-sitter parses these as `lexical_declaration → variable_declarator → arrow_function`, not `function_declaration`, so the default name-from-descendants extractor returned empty and the symbol never registered. v21 detects arrow-const bindings explicitly and registers each as a function symbol; walks scope through the arrow body so calls FROM inside arrow-const-bound functions get attributed to the const name rather than the file. Expected impact on barrel-export-heavy + arrow-const-heavy codebases: TS resolved-share rises from 6% range into 30–60% (per Teton estimate). Affects TS/JS only — other languages unchanged. Previous bump (1.3.10 v19→v20) covered direct-function-call import_targets promotion + bundler-mode .js→.ts swap + community-label barrel deprioritization
GRAPH_DIRNAME = "graph"
# Wave 1p4ww: single project graph — the framework graph layer was removed.
GRAPH_FILENAMES = {
    "project": "project-graph.json",
}
GRAPH_STATE_FILENAMES = {
    "project": "project-graph-state.json",
}

_DOC_EXTENSIONS = {".md", ".markdown", ".txt"}
_CODE_EXTENSIONS = {
    ".py",
    ".js", ".jsx", ".mjs", ".cjs",
    ".ts", ".tsx", ".mts", ".cts",
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
    ".mts": "typescript",
    ".cts": "typescript",
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
# Wave 1p4eu: language statement keywords the multi-token relation fallback (a
# regex over a node's text) would otherwise emit as junk `external::<kw>` import
# edges — e.g. Java/Kotlin `import`, Kotlin `as`/`package`, Rust `use`/`pub`/`fn`.
# None is ever a valid import or call TARGET in any supported language.
_RELATION_KEYWORD_NOISE = frozenset({
    "import", "use", "using", "package", "as", "from", "pub", "fn", "fun",
    "mod", "export", "include", "require",
})
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
    # Wave 1p2q3 (1p2q9 Workstream C): JS/TS conventional generated-output directories.
    "__generated__",
    ".generated",
)

# Filename suffix matches (case-insensitive).
_GENERATED_FILENAME_SUFFIXES = (
    ".designer.cs",
    ".g.cs",
    ".g.i.cs",
    # Wave 1p2q3 (1p2q9 Workstream C): JS/TS naming conventions for codegen output.
    # Covers TanStack Router (routeTree.gen.ts), GraphQL codegen (*.graphql.ts when
    # paired with .gen suffix), Apollo, OpenAPI generators, Prisma client output.
    # Operators with hand-written files matching the suffix can opt out via the
    # standard exclude_generated=false filter.
    ".gen.ts",
    ".gen.tsx",
    ".gen.js",
    ".gen.jsx",
    ".generated.ts",
    ".generated.tsx",
    ".generated.js",
    ".generated.jsx",
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


# Wave 1p4ls: constant graph nodes + the `reads` edge.
GRAPH_CONST_KIND = "constant"
GRAPH_READS_RELATION = "reads"


@functools.lru_cache(maxsize=1)
def _chunker_module():
    """Lazily import chunker.py for its per-language constant-detection predicates so the graph
    lane (1p4ls) and the chunk lane (1p4mf) share ONE detector (Req-7 — no divergent detection).
    Robust to both the standalone-subprocess and the _load_script(MCP) load contexts: ensures the
    scripts directory is importable before the import. The predicates are pure (stateless), so a
    second module instance under the plain `chunker` key is harmless."""
    _dir = str(Path(__file__).resolve().parent)
    if _dir not in sys.path:
        sys.path.insert(0, _dir)
    import chunker  # noqa: E402 — lazy by design (heavy tree-sitter deps load on first use)
    return chunker


def _py_const_literal_value(value_node: "ast.AST | None") -> str | None:
    """Short source-faithful value for a Python constant RHS when it is a SIMPLE literal
    (str/num/bool/None, or a 1-level list/tuple/set/dict of literals). None for anything computed
    (calls, names, comprehensions, f-strings) — the node still exists, it just carries no value."""
    if value_node is None:
        return None

    def _lit(n: "ast.AST") -> "str | None":
        if isinstance(n, ast.Constant):
            return repr(n.value)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)) and isinstance(n.operand, ast.Constant):
            return ("-" if isinstance(n.op, ast.USub) else "") + repr(n.operand.value)
        return None

    direct = _lit(value_node)
    if direct is not None:
        return direct[:200]
    if isinstance(value_node, (ast.List, ast.Tuple, ast.Set)):
        parts = [_lit(e) for e in value_node.elts]
        if parts and all(p is not None for p in parts):
            brackets = {"List": ("[", "]"), "Tuple": ("(", ")"), "Set": ("{", "}")}[type(value_node).__name__]
            return (brackets[0] + ", ".join(parts) + brackets[1])[:200]
    if isinstance(value_node, ast.Dict):
        keys = [_lit(k) for k in value_node.keys]
        vals = [_lit(v) for v in value_node.values]
        if keys and all(k is not None for k in keys) and all(v is not None for v in vals):
            return ("{" + ", ".join(f"{k}: {v}" for k, v in zip(keys, vals)) + "}")[:200]
    return None


def _py_local_names(owner_node: "ast.AST") -> set[str]:
    """Names BOUND locally inside a Python function — parameters + every Store/Del-context Name in
    its body (assignments, for-targets, with-as, nested def/class names) — NOT descending into
    nested scopes. Wave 1p4ls reads-edge faithfulness: a read of such a name is the LOCAL binding,
    not a module/class constant of the same name, so it must NOT emit a reads edge to the constant."""
    names: set[str] = set()
    a = getattr(owner_node, "args", None)
    if a is not None:
        for arg in [*getattr(a, "posonlyargs", []), *a.args, *a.kwonlyargs]:
            names.add(arg.arg)
        if a.vararg:
            names.add(a.vararg.arg)
        if a.kwarg:
            names.add(a.kwarg.arg)
    stack: list[Any] = list(getattr(owner_node, "body", []))
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(n.name)  # the nested def/class name binds locally; don't descend
            continue
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            names.add(n.id)
        for child in ast.iter_child_nodes(n):
            stack.append(child)
    return names


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
    self_edge_kind: str | None = None,
) -> dict[str, Any]:
    payload = {
        "source": source,
        "target": target,
        "relation": relation,
        "confidence": confidence,
    }
    if evidence:
        payload["evidence"] = evidence
    # Wave 1p2q3 (1p2td): tag self-edges on overloaded methods so consumers can
    # distinguish recursion from overload-forwarding.
    if self_edge_kind:
        payload["self_edge_kind"] = self_edge_kind
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
    # INTENTIONALLY split('.', 1) (FIRST dot), NOT rsplit. Do NOT "fix" this to the bare leaf:
    # folding a 2+-level-nested symbol's bare leaf into simple_names -> symbol_lookup over-binds the
    # UNGUARDED bare-call and bare-read paths. An adversarial review verified three regressions from
    # rsplit: (1) a receiver-less bare `run()` wrong-binds to a unique nested `Outer.Inner.run`
    # (TS/JS/Rust; promoted to RECEIVER_RESOLVED on TS/JS); (2) a bare PARAMETER read (`TOKEN`)
    # wrong-binds to a same-leaf nested constant `Outer.Inner.TOKEN` (Java/Kotlin/C#/Swift — the
    # tree-sitter reads path has no local-shadow guard); (3) a bare read of an EXPLICITLY-IMPORTED
    # symbol gets shadowed by a same-leaf nested member, which on a real repo file (http2.d.ts)
    # silently DROPPED 5 correct `external::url` import-reads. The faithful fix for nested
    # member-access CONSTANT reads is exact qualified-PATH capture (const-gated), not bare-leaf
    # widening — see the member-access-reads follow-on. Keep this split('.', 1).
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
# Wave 131bt (1319s): added composite_literal to Go and struct_expression to
# Rust so that construction-shape AST nodes are visited by walk_calls and routed
# to the class node via _resolve_construction_target.
_TS_CALL_NODES_GO = frozenset({"call_expression", "composite_literal"})
_TS_CALL_NODES_RUST = frozenset({"call_expression", "macro_invocation", "struct_expression"})
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
    # Wave 131bt (1319s): added so PHP `new Foo()` construction shapes are
    # visited by walk_calls and routed to the class node.
    "object_creation_expression",
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


# Wave 1p2q3 (1p2q9 A): TypeScript `tsconfig.json` path-alias resolution.
# Nx and other monorepos configure cross-package import aliases via the
# `compilerOptions.paths` field. The graph indexer previously dropped those
# imports to `external::*` because the resolver treated specifiers literally;
# Aceiss / Teton field validation surfaced this as near-zero per-function
# `calls` coverage on TypeScript monorepos. This block discovers the nearest
# tsconfig with `paths`, applies the alias substitution, and probes the
# resolved candidate against project files so the import edge binds to the
# real project node id instead of `external::@scope/...`.

_TS_PATH_RESOLVE_EXTS: tuple[str, ...] = (".ts", ".tsx", ".d.ts", ".js", ".jsx", ".mjs", ".cjs")
_TS_PATH_RESOLVE_INDEX_FILES: tuple[str, ...] = ("index.ts", "index.tsx", "index.js", "index.jsx", "index.mjs", "index.cjs")

# tsconfig path → (tsconfig_dir, paths_map, base_url_dir) or None when no `paths` configured.
_TSCONFIG_PATHS_CACHE: dict[str, tuple[Path, dict[str, list[str]], Path] | None] = {}
# (root_str, file_dir_str) → discovered tsconfig path string, or None when no tsconfig with paths exists above this dir.
_TSCONFIG_DISCOVERY_CACHE: dict[tuple[str, str], str | None] = {}


def _strip_jsonc_comments(text: str) -> str:
    """Strip JSONC comments and trailing commas so json.loads can parse.

    Handles /* */ block and // line comments. Both strips track string-literal
    state so `/*` or `//` appearing inside `"..."` (e.g. tsconfig path patterns
    like `"@aceiss/*"`, URLs like `"https://..."`) are preserved verbatim.
    """
    out: list[str] = []
    in_str = False
    escape = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if escape:
            out.append(ch)
            escape = False
            i += 1
            continue
        if in_str:
            if ch == "\\":
                out.append(ch)
                escape = True
                i += 1
                continue
            if ch == '"':
                in_str = False
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            # Line comment — skip to newline (preserve the newline).
            j = text.find("\n", i)
            if j == -1:
                break
            i = j
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            # Block comment — skip to closing */.
            j = text.find("*/", i + 2)
            if j == -1:
                break
            i = j + 2
            continue
        out.append(ch)
        i += 1
    result = "".join(out)
    result = re.sub(r",(\s*[}\]])", r"\1", result)
    return result


def _load_tsconfig_paths(tsconfig_path: Path) -> tuple[Path, dict[str, list[str]], Path] | None:
    """Read tsconfig.json, return (tsconfig_dir, paths_map, base_url_dir) or None."""
    key = str(tsconfig_path)
    if key in _TSCONFIG_PATHS_CACHE:
        return _TSCONFIG_PATHS_CACHE[key]
    try:
        raw = tsconfig_path.read_text(encoding="utf-8")
    except OSError:
        _TSCONFIG_PATHS_CACHE[key] = None
        return None
    try:
        data = json.loads(_strip_jsonc_comments(raw))
    except (ValueError, TypeError):
        _TSCONFIG_PATHS_CACHE[key] = None
        return None
    if not isinstance(data, dict):
        _TSCONFIG_PATHS_CACHE[key] = None
        return None
    compiler = data.get("compilerOptions")
    if not isinstance(compiler, dict):
        _TSCONFIG_PATHS_CACHE[key] = None
        return None
    paths = compiler.get("paths")
    if not isinstance(paths, dict) or not paths:
        _TSCONFIG_PATHS_CACHE[key] = None
        return None
    paths_clean: dict[str, list[str]] = {}
    for pattern, replacements in paths.items():
        if not isinstance(pattern, str) or not isinstance(replacements, list):
            continue
        clean_repls = [r for r in replacements if isinstance(r, str) and r]
        if clean_repls:
            paths_clean[pattern] = clean_repls
    if not paths_clean:
        _TSCONFIG_PATHS_CACHE[key] = None
        return None
    tsconfig_dir = tsconfig_path.parent
    base_url_raw = compiler.get("baseUrl") if isinstance(compiler.get("baseUrl"), str) else "."
    base_url_dir = (tsconfig_dir / base_url_raw).resolve()
    result = (tsconfig_dir, paths_clean, base_url_dir)
    _TSCONFIG_PATHS_CACHE[key] = result
    return result


def _discover_tsconfig_for_file(file_path: Path, root: Path) -> str | None:
    """Walk upward from file_path to root, return the path of the nearest
    tsconfig (preferring `tsconfig.base.json` for Nx) that has `paths`
    configured. Caches per (root, file_dir)."""
    try:
        file_dir = file_path.parent.resolve() if file_path.is_file() else file_path.resolve()
        root_resolved = root.resolve()
    except OSError:
        return None
    cache_key = (str(root_resolved), str(file_dir))
    if cache_key in _TSCONFIG_DISCOVERY_CACHE:
        return _TSCONFIG_DISCOVERY_CACHE[cache_key]
    current = file_dir
    while True:
        for name in ("tsconfig.base.json", "tsconfig.json"):
            candidate = current / name
            if candidate.is_file() and _load_tsconfig_paths(candidate) is not None:
                _TSCONFIG_DISCOVERY_CACHE[cache_key] = str(candidate)
                return str(candidate)
        if current == root_resolved:
            break
        parent = current.parent
        if parent == current:
            break
        current = parent
    _TSCONFIG_DISCOVERY_CACHE[cache_key] = None
    return None


def _ts_path_alias_match(specifier: str, pattern: str) -> str | None:
    """Match an import specifier against a tsconfig paths pattern.

    Returns the wildcard substitution portion (or "" for exact matches), or
    None when the pattern doesn't match. Patterns may contain at most one `*`.
    """
    if "*" in pattern:
        head, _, tail = pattern.partition("*")
        if specifier.startswith(head) and (not tail or specifier.endswith(tail)):
            return specifier[len(head): len(specifier) - len(tail) if tail else None]
        return None
    return "" if specifier == pattern else None


# Wave 1p2q3 (1p2tz post-ship-3 perf): LRU cache for probe/relative-import
# resolution. Both are pure functions of `(args, filesystem state)`. Filesystem
# state changes infrequently relative to call volume during a single graph
# build, so caching pays for itself many times over on barrel-export-heavy
# codebases where each unique import specifier is hit dozens of times across
# different callers. Caches are NOT cleared per-build by design — LRU pressure
# handles eviction and stale-result risk is low (deleted files don't appear in
# the per-build file list so they're not extracted regardless of cached probe
# results).
@functools.lru_cache(maxsize=20000)
def _probe_ts_alias_target(candidate: Path, root: Path) -> str | None:
    """Probe a candidate path with TS resolution rules; return rel_path or None.

    TS bundler-mode resolution (TS 5.x `moduleResolution: "Bundler"`, used by
    Vite / esbuild / Nx defaults) allows source code to write `./foo.js` and
    have it resolve to `./foo.ts` at compile time. When the candidate's
    explicit `.js`/`.jsx`/`.mjs`/`.cjs` extension doesn't exist on disk, also
    try the matching `.ts`/`.tsx` form. Without this swap, every barrel
    re-export of the shape `export { x } from './foo.js'` would silently
    fail to resolve through.
    """
    try:
        candidate_resolved = candidate.resolve()
        root_resolved = root.resolve()
    except OSError:
        return None
    paths_to_try: list[Path] = []
    if candidate_resolved.suffix:
        paths_to_try.append(candidate_resolved)
        # Bundler-mode fallback for js → ts swap.
        suffix = candidate_resolved.suffix.lower()
        if suffix == ".js":
            paths_to_try.append(candidate_resolved.with_suffix(".ts"))
        elif suffix == ".jsx":
            paths_to_try.append(candidate_resolved.with_suffix(".tsx"))
        elif suffix == ".mjs":
            paths_to_try.append(candidate_resolved.with_suffix(".mts"))
            paths_to_try.append(candidate_resolved.with_suffix(".ts"))
        elif suffix == ".cjs":
            paths_to_try.append(candidate_resolved.with_suffix(".cts"))
            paths_to_try.append(candidate_resolved.with_suffix(".ts"))
    else:
        for ext in _TS_PATH_RESOLVE_EXTS:
            paths_to_try.append(candidate_resolved.with_suffix(ext))
    if candidate_resolved.is_dir():
        for idx in _TS_PATH_RESOLVE_INDEX_FILES:
            paths_to_try.append(candidate_resolved / idx)
    for probe in paths_to_try:
        if not probe.is_file():
            continue
        try:
            rel = probe.relative_to(root_resolved)
        except ValueError:
            continue
        return rel.as_posix()
    return None


def _resolve_ts_import_via_tsconfig(specifier: str, rel_path: str, root: Path) -> str | None:
    """Resolve `specifier` through nearest tsconfig `paths` aliases; return
    the project rel_path or None when no alias matches or the candidate is
    missing on disk."""
    if not specifier:
        return None
    if specifier.startswith(".") or specifier.startswith("/"):
        return None
    file_path = root / rel_path
    tsconfig_path_str = _discover_tsconfig_for_file(file_path, root)
    if tsconfig_path_str is None:
        return None
    loaded = _load_tsconfig_paths(Path(tsconfig_path_str))
    if loaded is None:
        return None
    _tsconfig_dir, paths_map, base_url_dir = loaded
    for pattern, replacements in paths_map.items():
        middle = _ts_path_alias_match(specifier, pattern)
        if middle is None:
            continue
        for repl in replacements:
            substituted = repl.replace("*", middle) if "*" in repl else repl
            candidate = base_url_dir / substituted
            resolved = _probe_ts_alias_target(candidate, root)
            if resolved is not None:
                return resolved
    return None


# Wave 1p2q3 (1p2tz): barrel re-export resolution. tsconfig.paths aliases on
# Nx-shaped monorepos point at `src/index.ts` barrel files that re-export
# from `./lib/<name>`. Stopping at the barrel collapses every aliased import
# onto the same N hub nodes; following re-exports to the definition file is
# what produces RECEIVER_RESOLVED edges with per-symbol granularity.

_TS_BARREL_PARSE_CACHE: dict[tuple[str, float], dict[str, str]] = {}
_TS_BARREL_WILDCARDS_CACHE: dict[tuple[str, float], list[str]] = {}
_TS_BARREL_RESOLVE_MAX_HOPS = 5

# Match `export { Foo, Bar as Baz, default as Qux } from './path'`. Group 1 is
# the brace clause body; group 2 is the module specifier.
_TS_REEXPORT_NAMED_RE = re.compile(
    r"export\s*\{\s*([^}]+?)\s*\}\s*from\s*['\"]([^'\"]+)['\"]"
)
# Match `export * from './path'`.
_TS_REEXPORT_WILDCARD_RE = re.compile(
    r"export\s*\*\s*from\s*['\"]([^'\"]+)['\"]"
)


def _parse_barrel(barrel_path: Path) -> tuple[dict[str, str], list[str]]:
    """Return ({local_name: (module_specifier, source_name)}, [wildcard_modules]).

    Cached per file path + mtime. `local_name` is the name as exposed by the
    barrel; `source_name` is the original name in the re-exported module.
    Default re-exports (`{ default as Foo }`) appear with source_name="default".
    """
    try:
        stat = barrel_path.stat()
    except OSError:
        return ({}, [])
    cache_key = (str(barrel_path), stat.st_mtime)
    if cache_key in _TS_BARREL_PARSE_CACHE:
        return (_TS_BARREL_PARSE_CACHE[cache_key], _TS_BARREL_WILDCARDS_CACHE.get(cache_key, []))
    named_map: dict[str, str] = {}
    sourcename_map: dict[str, str] = {}  # local_name -> original name in source module
    wildcards: list[str] = []
    try:
        text = barrel_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        _TS_BARREL_PARSE_CACHE[cache_key] = {}
        _TS_BARREL_WILDCARDS_CACHE[cache_key] = []
        return ({}, [])
    for m in _TS_REEXPORT_NAMED_RE.finditer(text):
        clause = m.group(1)
        module_spec = m.group(2)
        for part in clause.split(","):
            item = part.strip()
            if not item:
                continue
            # Three shapes: "Foo", "Foo as Bar", "default as Foo".
            if " as " in item:
                left, right = [s.strip() for s in item.split(" as ", 1)]
                source_name = left
                local_name = right
            else:
                source_name = local_name = item
            if not local_name:
                continue
            named_map[local_name] = module_spec
            sourcename_map[local_name] = source_name
    for m in _TS_REEXPORT_WILDCARD_RE.finditer(text):
        wildcards.append(m.group(1))
    _TS_BARREL_PARSE_CACHE[cache_key] = named_map
    _TS_BARREL_WILDCARDS_CACHE[cache_key] = wildcards
    # Stash the rename info under the same key as a small attached dict so the
    # resolver can recover the original source name for the next hop.
    _TS_BARREL_PARSE_CACHE[(str(barrel_path), stat.st_mtime, "_rename")] = sourcename_map  # type: ignore[assignment]
    return (named_map, wildcards)


@functools.lru_cache(maxsize=20000)
def _resolve_relative_ts_import(specifier: str, from_file: Path, root: Path) -> str | None:
    """Resolve a relative TS import specifier (`./foo`, `../bar`) against the
    containing file. Returns the repo-relative project path or None when the
    target doesn't probe to a real file."""
    if not specifier:
        return None
    if not (specifier.startswith(".") or specifier.startswith("/")):
        return None
    candidate = (from_file.parent / specifier).resolve()
    return _probe_ts_alias_target(candidate, root)


# Wave 1p2q3 (1p2tz post-ship-3 perf): cache the set of top-level declared
# names per file (keyed on path + mtime) so `_file_declares_name` becomes a
# hash-set membership check after the first parse rather than re-reading the
# file and re-running the regex for every name. On barrel-export-heavy codebases
# (Teton: 14 aliases, each pointing at a barrel that re-exports 10–100 symbols,
# each re-export potentially walking through 2–3 hops to reach a definition
# file), the prior implementation triggered tens of thousands of redundant file
# reads + regex runs during a single graph build.
_TS_FILE_DECLARED_NAMES_CACHE: dict[tuple[str, float], frozenset[str]] = {}

# Single combined regex matching any top-level declaration's binding name.
# Captures the identifier as group(1).
_TS_DECLARED_NAMES_RE = re.compile(
    r"(?m)^\s*(?:export\s+)?(?:default\s+)?"
    r"(?:abstract\s+|async\s+)?"
    r"(?:class|function|const|let|var|interface|type|enum)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)"
)


def _file_declared_names(file_rel: str, root: Path) -> frozenset[str]:
    """Return the set of top-level binding names declared in a TS/JS file.

    Cached per (file path, mtime). The cache is module-level — populated
    lazily during graph extraction and naturally invalidated when source
    files change mtime."""
    if not file_rel:
        return frozenset()
    path = root / file_rel
    try:
        stat = path.stat()
    except OSError:
        return frozenset()
    key = (str(path), stat.st_mtime)
    cached = _TS_FILE_DECLARED_NAMES_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        result: frozenset[str] = frozenset()
        _TS_FILE_DECLARED_NAMES_CACHE[key] = result
        return result
    names = frozenset(m.group(1) for m in _TS_DECLARED_NAMES_RE.finditer(text))
    _TS_FILE_DECLARED_NAMES_CACHE[key] = names
    return names


def _file_declares_name(file_rel: str, name: str, root: Path) -> bool:
    """Return True when the file declares `name` at the top level via class /
    function / const / let / var / interface / type / enum syntax. Reads
    through `_file_declared_names`, so the file's declaration set is parsed
    at most once per (path, mtime)."""
    if not name:
        return False
    return name in _file_declared_names(file_rel, root)


def _resolve_through_barrel(
    imported_name: str,
    target_rel_path: str,
    root: Path,
    _seen: set[str] | None = None,
    _depth: int = 0,
) -> str:
    """Walk barrel re-exports until the symbol's actual definition file is found.

    Returns the repo-relative project path. Falls back to ``target_rel_path``
    (the input barrel) when no chain terminates at a declaration of
    ``imported_name``. Recursion is bounded at ``_TS_BARREL_RESOLVE_MAX_HOPS``;
    cycles in the resolved-paths chain are detected via ``_seen``.
    """
    if _depth >= _TS_BARREL_RESOLVE_MAX_HOPS:
        return target_rel_path
    if _seen is None:
        _seen = set()
    if target_rel_path in _seen:
        return target_rel_path
    _seen = _seen | {target_rel_path}
    barrel_path = root / target_rel_path
    if not barrel_path.is_file():
        return target_rel_path
    # If the current file declares the name directly, stop here.
    if _depth > 0 and _file_declares_name(target_rel_path, imported_name, root):
        return target_rel_path
    named_map, wildcards = _parse_barrel(barrel_path)
    # Named / renamed re-exports.
    if imported_name in named_map:
        try:
            stat = barrel_path.stat()
            sourcename_map = _TS_BARREL_PARSE_CACHE.get(
                (str(barrel_path), stat.st_mtime, "_rename")  # type: ignore[arg-type]
            ) or {}
        except OSError:
            sourcename_map = {}
        next_module_spec = named_map[imported_name]
        next_name = sourcename_map.get(imported_name, imported_name)
        next_rel = _resolve_relative_ts_import(next_module_spec, barrel_path, root)
        if next_rel is not None:
            # Recurse with the source-side name (post-rename).
            return _resolve_through_barrel(next_name, next_rel, root, _seen, _depth + 1)
    # Wildcard re-exports: probe each. Stop at first hit where the name is
    # declared; otherwise fall back to the barrel.
    for wild_spec in wildcards:
        wild_rel = _resolve_relative_ts_import(wild_spec, barrel_path, root)
        if wild_rel is None:
            continue
        if _file_declares_name(wild_rel, imported_name, root):
            return wild_rel
        # Recurse into the wildcard target — it might itself be a barrel.
        wild_resolved = _resolve_through_barrel(imported_name, wild_rel, root, _seen, _depth + 1)
        if wild_resolved != wild_rel:
            return wild_resolved
    # No re-export chain produced a declaration; stay at the (last) barrel.
    return target_rel_path


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


# Wave 1p5c4: skip tree-sitter graph extraction on very large files (a full AST over a multi-MB/GB
# file spins). Over the cap → no extraction for that file (graceful, same as tree-sitter-unavailable).
# Override via WAVEFOUNDRY_MAX_TS_PARSE_BYTES (the indexer sets it from
# `indexing.max_treesitter_parse_bytes` in workflow-config.json). 0/negative disables the cap.
MAX_TREESITTER_PARSE_BYTES_DEFAULT = 2_000_000


def _ts_parse(lang_key: str, source_text: str):
    _cap = int(os.environ.get("WAVEFOUNDRY_MAX_TS_PARSE_BYTES") or MAX_TREESITTER_PARSE_BYTES_DEFAULT)
    if _cap > 0 and len(source_text) > _cap:
        return None
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
    # Wave 1p2q3 (1p2tz field follow-up): preserve a leading `@` so scoped npm /
    # Nx package specifiers (`@aceiss/hooks`, `@teton/backend`, `@scope/pkg`)
    # survive into the alias resolver. Without this, `@aceiss/hooks` would be
    # cleaned to `aceiss/hooks` and fail to match the tsconfig.paths pattern
    # `@aceiss/hooks` — which is the silent root cause of every scoped-import
    # resolution failing on Nx monorepos. The leading `@` is the only special
    # case; bare `@` mid-string is not a valid identifier prefix in TS/JS.
    if value.startswith("@"):
        rest_match = re.search(r"[A-Za-z_][A-Za-z0-9_.$:#/\-]*", value[1:])
        if rest_match:
            return "@" + rest_match.group(0)
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
    # Wave 1p61v: TS/JS type-shape members are NOT callables and must not fall
    # through to the default `function`. A type alias is a `type`; an interface /
    # object-type DATA member (`property_signature`) is a `property`. Method
    # *signatures* keep `function` via the `method` branch below. Without this,
    # `: string` fields and `export type X = …` aliases rendered as `(function)`
    # entry points in the codebase map (teton p60n field trace, Issue 1) — the
    # graph diverged from `code_outline`, which yields zero callable symbols for
    # the same pure-type files.
    if "type_alias" in lower:
        return "type"
    if lower == "property_signature":
        return "property"
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


# Wave 1p4ls: tree-sitter literal node types whose source text we capture as a constant's `value`.
_TS_CONST_LITERAL_TYPES = frozenset({
    "integer_literal", "int_literal", "integer", "float_literal", "decimal_integer_literal",
    "decimal_floating_point_literal", "number", "numeric_literal", "string_literal",
    "interpreted_string_literal", "raw_string_literal", "line_string_literal", "string",
    "true", "false", "null", "nil", "boolean_literal", "character_literal", "char_literal",
    "rune_literal", "encapsed_string", "unary_expression", "prefix_expression",
})


# Wave 1p4ls: leaf node types that can be a constant READ (name-use) for the `reads` edge.
# `constant` is Ruby's capital-initial reference node; `name` is PHP's bare const/callee reference;
# the rest are the per-grammar identifiers. The const-target gate keeps non-constant uses harmless.
_TS_READ_IDENT_TYPES = frozenset({"identifier", "simple_identifier", "field_identifier", "constant", "name"})

# Member-access read attribution: the node type of a qualified reference `A.B.C` / `A::B::C` per
# language. A read of a CONSTANT via member access (`Status.ACTIVE`, `SolarisConstants.Network.userAgent`,
# `Outer.Inner.TOKEN`) is resolved by EXACT qualified-name match against constant nodes — faithful (the
# qualifier disambiguates), const-gated, and it NEVER widens bare-leaf resolution (so it introduces none
# of the bare-call / param-shadow / import-shadow over-binds that a `_simple_name` rsplit would).
_TS_MEMBER_ACCESS_TYPES = frozenset({
    "member_expression",                  # TS / JS  (A.B.C)
    "navigation_expression",              # Swift, Kotlin  (A.B.C)
    "field_access",                       # Java  (A.B.C)
    "member_access_expression",           # C#  (A.B.C)
    "selector_expression",                # Go  (A.B.C)
    "scoped_identifier",                  # Rust  (A::B::C)
    "scope_resolution",                   # Ruby  (A::B::C)
    "class_constant_access_expression",   # PHP  (A::B)
})

# A PURE static qualified path: identifiers joined by `.` / `::` only — no calls, subscripts, `this`,
# literals, or whitespace (which would signal a computed/dynamic member access, not a resolvable name).
_TS_MEMBER_PATH_RE = re.compile(r"^[A-Za-z_$][\w$]*(?:(?:\.|::)[A-Za-z_$][\w$]*)+$")

# Parameter + local-variable BINDING nodes per language. Their bound NAME (never the type) is collected
# per function so a member-access constant read whose head qualifier is a local/param shadow is suppressed
# (member-access review F4: `func reader(Config: Holder){ return Config.value }` reads the param, not the
# struct's static const). Suppressing is FAITHFUL — if the head is a local binding, the access is on that
# local, never the type's constant.
_TS_BINDING_NODE_TYPES = frozenset({
    "formal_parameter", "spread_parameter",                  # Java
    "parameter",                                             # Swift, C#, Rust, Kotlin
    "required_parameter", "optional_parameter",              # TS / JS
    "parameter_declaration",                                 # Go
    "simple_parameter", "variadic_parameter",               # PHP
    "function_value_parameter",                              # Kotlin
    "variable_declarator",                                   # Java / TS / JS / C#  (function-local only — gated to fn scope)
    "property_declaration", "variable_declaration",          # Swift / Kotlin
    "let_declaration",                                       # Rust
    "short_var_declaration", "var_spec", "const_spec",       # Go
    "assignment", "assignment_expression",                  # Ruby / PHP (implicit locals)
})


def _ts_is_member_property_leaf(node) -> bool:
    """True when ``node`` is the PROPERTY/field side of a member access (the trailing `C` in `A.B.C`).
    Such leaves are NOT buffered as bare reads — the member-access PATH branch resolves the qualified
    read instead (by exact qname, const-gated, with the F4 qualifier-shadow guard). This removes the
    pre-existing trailing-member over-fire where a bare leaf `value` from an instance access
    `local.value` wrong-binds a same-named top-level constant `Type.value`."""
    p = getattr(node, "parent", None)
    if p is None:
        return False
    pt = str(getattr(p, "type", "") or "")
    if pt == "navigation_suffix":   # Swift trailing `.member` wrapper
        return True
    if pt in _TS_MEMBER_ACCESS_TYPES:
        # The object/operand is the FIRST named child of a member-access node; any OTHER identifier
        # under it is the trailing property/field side (works uniformly whether the grammar uses a
        # `property`/`field` field, a bare trailing identifier (Kotlin), or a `field_identifier` (Go)).
        kids = list(getattr(p, "named_children", []))
        # NOTE: `==` not `is` — tree-sitter's Python binding returns a NEW wrapper object on every
        # `.named_children`/`.parent` access, so `is` is ALWAYS False (a blanket skip that would also
        # drop the legit HEAD read, e.g. the const in `FRAMEWORK_FLOW.length`). `Node.__eq__` compares
        # the underlying AST node.
        if kids and kids[0] != node:
            return True
    return False


def _ts_binding_names(node) -> set[str]:
    """The NAME(s) bound by a parameter / local-variable node — extracted from the ``name``/``pattern``/
    ``left`` field (never the type), so the qualifier-shadow guard cannot accidentally suppress a real
    read of a type's constant."""
    names: set[str] = set()
    fields: list = []
    for fld in ("name", "pattern", "left"):
        try:
            c = node.child_by_field_name(fld)
        except Exception:
            c = None
        if c is not None:
            fields.append(c)
    if not fields:  # Kotlin parameter / variable_declaration carry the name as a bare leading identifier
        for c in getattr(node, "named_children", []):
            if str(getattr(c, "type", "") or "") in ("simple_identifier", "identifier"):
                fields.append(c)
                break
    for c in fields:
        ct = str(getattr(c, "type", "") or "")
        leaves = [c] if ct in ("identifier", "simple_identifier", "variable_name") else [
            g for g in getattr(c, "named_children", [])
            if str(getattr(g, "type", "") or "") in ("identifier", "simple_identifier", "variable_name")
        ]
        for leaf in leaves:
            try:
                nm = leaf.text.decode().strip()
            except Exception:
                nm = ""
            if nm:
                names.add(nm)
    return names


def _ts_member_access_path(node, source_bytes: bytes) -> str | None:
    """The dotted qualified name of a member-access node (``::`` normalized to ``.``), or ``None`` when
    it is not a pure static path (e.g. ``foo().bar``, ``arr[0].x``, ``this.x``). Used to resolve a
    qualified CONSTANT read by exact qname match."""
    try:
        text = source_bytes[node.start_byte:node.end_byte].decode("utf-8", "replace").strip()
    except Exception:
        return None
    if not _TS_MEMBER_PATH_RE.match(text):
        return None
    norm = text.replace("::", ".")
    # A receiver-relative access (`this.X`, `self.X`, `super.X`, `cls.X`) is not a static type path;
    # no constant qname begins with these, but reject them so the contract is explicit (not reliant
    # on an unstated qname-mismatch invariant).
    if norm.split(".", 1)[0] in ("this", "self", "super", "cls"):
        return None
    return norm


def _ts_literal_value(value_node, source_bytes: bytes) -> str | None:
    if value_node is None:
        return None
    if str(getattr(value_node, "type", "") or "") in _TS_CONST_LITERAL_TYPES:
        try:
            return source_bytes[value_node.start_byte:value_node.end_byte].decode("utf-8", "replace")[:200]
        except Exception:
            return None
    return None


def _ts_declarator_value(decl_node, source_bytes: bytes) -> str | None:
    """RHS value of a declarator / const_spec / element node when it is a simple literal."""
    v = None
    try:
        v = decl_node.child_by_field_name("value")
    except Exception:
        v = None
    if v is None:
        kids = list(getattr(decl_node, "children", []) or [])
        for i, c in enumerate(kids):
            if str(getattr(c, "type", "") or "") == "=" and i + 1 < len(kids):
                v = kids[i + 1]
                break
    # Go wraps the RHS in an `expression_list`; unwrap a single-element list to its literal.
    if v is not None and str(getattr(v, "type", "") or "") == "expression_list":
        named = [c for c in getattr(v, "children", []) if getattr(c, "is_named", False)]
        if len(named) == 1:
            v = named[0]
    return _ts_literal_value(v, source_bytes)


def _ts_constant_decls(lang_key, node, node_type, source_bytes, source_lines, *, in_type_body):
    """Wave 1p4ls: the constant(s) DECLARED directly by ``node`` for the graph lane — a list of
    ``(name, value_or_None)``. Reuses the 1p4mf chunk-lane detection predicates (Req-7 — ONE
    detector, two consumers). Returns [] when ``node`` is not a constant declaration. The caller
    scope-gates (function/method-body locals are never passed). ``in_type_body`` is True when the
    enclosing scope is a class/struct/type member body (used by Swift's static-vs-instance rule)."""
    ck = _chunker_module()
    out: list[tuple[str, str | None]] = []
    try:
        if lang_key == "java":
            if node_type == "field_declaration" and not ck._java_field_is_static_final(node):
                return []
            if node_type in ("field_declaration", "constant_declaration"):
                for d in node.children:
                    if str(getattr(d, "type", "") or "") == "variable_declarator":
                        nm = ck._java_declarator_name(d, source_lines)
                        if nm:
                            out.append((nm, _ts_declarator_value(d, source_bytes)))
        elif lang_key == "csharp":
            if node_type == "field_declaration" and ck._csharp_is_const_field(node, source_lines):
                for d in node.children:
                    if str(getattr(d, "type", "") or "") == "variable_declaration":
                        for vd in d.children:
                            if str(getattr(vd, "type", "") or "") == "variable_declarator":
                                ident = next((c for c in vd.children if str(getattr(c, "type", "") or "") == "identifier"), None)
                                if ident is not None:
                                    out.append((ident.text.decode(), _ts_declarator_value(vd, source_bytes)))
        elif lang_key == "kotlin":
            if node_type == "property_declaration" and ck._kotlin_property_is_const(node):
                nm = ck._kotlin_property_name(node, source_lines)
                if nm:
                    out.append((nm, _ts_declarator_value(node, source_bytes)))
        elif lang_key == "go":
            if node_type == "const_declaration":
                for spec in node.children:
                    if str(getattr(spec, "type", "") or "") == "const_spec":
                        for nm in ck._go_const_spec_names(spec, source_lines):
                            if nm != "_":
                                out.append((nm, _ts_declarator_value(spec, source_bytes)))
        elif lang_key == "rust":
            if node_type in ck._RUST_CONST_NODE_TYPES:
                nm = ck._rust_const_name(node, source_lines)
                if nm:
                    out.append((nm, _ts_declarator_value(node, source_bytes)))
        elif lang_key == "swift":
            if node_type == "property_declaration":
                if ck._swift_property_is_computed(node):
                    return []
                if in_type_body and not ck._swift_property_has_static(node):
                    return []  # instance let/var = a field, not a constant
                for nm in ck._swift_property_names(node):
                    out.append((nm, _ts_declarator_value(node, source_bytes)))
            elif node_type == "enum_entry":
                for c in node.children:
                    if str(getattr(c, "type", "") or "") == "simple_identifier":
                        out.append((c.text.decode().strip(), None))
        elif lang_key == "ruby":
            if node_type == "assignment":
                lhs = node.child_by_field_name("left")
                if lhs is not None and str(getattr(lhs, "type", "") or "") not in ck._RUBY_LOCAL_LHS_TYPES:
                    for nm in ck._ruby_const_lhs_names(lhs):
                        if nm:
                            out.append((nm, _ts_declarator_value(node, source_bytes)))
        elif lang_key == "php":
            if node_type == "const_declaration":
                for el in node.children:
                    if str(getattr(el, "type", "") or "") == "const_element":
                        nm_node = next((c for c in el.children if str(getattr(c, "type", "") or "") == "name"), None)
                        if nm_node is not None:
                            out.append((nm_node.text.decode().strip(), _ts_declarator_value(el, source_bytes)))
        elif lang_key in ("typescript", "javascript"):
            if node_type == "lexical_declaration" and ck._js_is_const_decl(node):
                for d in node.children:
                    if str(getattr(d, "type", "") or "") == "variable_declarator":
                        if ck._js_const_value_type(d) in ck._JS_VALUE_CONST_TYPES:
                            nm_node = d.child_by_field_name("name")
                            if nm_node is not None and str(getattr(nm_node, "type", "") or "") == "identifier":
                                out.append((nm_node.text.decode(), _ts_declarator_value(d, source_bytes)))
    except Exception:
        return []
    return out


# Wave 131bt (1319v): languages where the indexer should recover an ERROR-wrapped
# top-level class declaration. Tree-sitter occasionally fails to parse a class body
# (parse-resistant interior construct) and emits an ERROR node wrapping the entire
# class declaration. Without recovery the class node is never registered, the
# basename-match class/module merge can't fire, and cross-file `external::ClassName`
# construction edges (CONSTRUCTION_RESOLVED) have no project node to bind to.
# Limited to languages that use file-level type declarations.
_TS_ERROR_CLASS_RECOVERY_LANGS: frozenset[str] = frozenset({
    "swift", "kotlin", "scala", "java", "csharp",
})

# Match the prefix of an ERROR-wrapped class declaration after stripping leading
# attributes/modifiers. Captures the keyword and the type name; the type name must
# be PascalCase to keep this conservative (avoid recovering e.g. ERROR nodes that
# happen to start with `class` in some other context).
_TS_ERROR_CLASS_PREFIX_RE = re.compile(
    r"^(class|struct|actor|enum|protocol|interface|object|record|trait)\s+([A-Z]\w*)"
)
# Strips one or more leading attribute (`@Foo`, `@Foo(...)`) or access/final
# modifier tokens before the class keyword. Run iteratively so it doesn't have to
# enumerate every modifier combination.
_TS_ERROR_CLASS_MODIFIER_RE = re.compile(
    r"^\s*(?:@\w+(?:\([^)]*\))?\s+|"
    r"(?:public|private|internal|fileprivate|open|final|sealed|abstract|static)\s+)+"
)


def _ts_recover_error_class(node, source_bytes: bytes, lang_key: str) -> tuple[str, str] | None:
    """Recover (name, kind) from an ERROR node that wraps a class declaration.

    Returns a tuple when the ERROR node's source-text prefix matches a recognizable
    class-declaration shape AND the node contains an identifier named child whose
    text matches the recovered name. Both conditions are required so that ERROR
    nodes containing the word "class" in some other context (e.g. a property of
    type `class`) are NOT recovered as types.

    The accepted identifier child kinds are ``type_identifier``, ``simple_identifier``,
    and ``identifier`` — different tree-sitter grammars use different node-type
    names for the same role, and recovery-state ERROR nodes don't always preserve
    the same identifier-kind label the successful parse would carry. The
    prefix-match + name-match-to-child-text pair keeps false positives narrow
    even with the broader child-kind acceptance.
    """
    if lang_key not in _TS_ERROR_CLASS_RECOVERY_LANGS:
        return None
    if str(getattr(node, "type", "") or "") != "ERROR":
        return None
    start = getattr(node, "start_byte", 0)
    end = min(getattr(node, "end_byte", start), start + 512)
    prefix = source_bytes[start:end].decode("utf-8", errors="replace")
    stripped = _TS_ERROR_CLASS_MODIFIER_RE.sub("", prefix, count=8)
    match = _TS_ERROR_CLASS_PREFIX_RE.match(stripped)
    if not match:
        return None
    name = match.group(2)
    # Second gate: the ERROR node must carry an identifier child whose text matches
    # the recovered name. Broad identifier-kind acceptance (type_identifier,
    # simple_identifier, identifier) covers grammar variants and recovery-state
    # node-type relabeling. Name-match-to-child-text replaces the prior
    # type_identifier-presence-only check — that check missed the production case
    # where tree-sitter-swift's recovery emits the identifier as simple_identifier.
    identifier_kinds = ("type_identifier", "simple_identifier", "identifier")
    has_matching_identifier = False
    for child in getattr(node, "named_children", []) or []:
        if str(getattr(child, "type", "") or "") not in identifier_kinds:
            continue
        child_start = getattr(child, "start_byte", 0)
        child_end = getattr(child, "end_byte", child_start)
        child_text = source_bytes[child_start:child_end].decode("utf-8", errors="replace")
        if child_text == name:
            has_matching_identifier = True
            break
    if not has_matching_identifier:
        return None
    return (name, "class")


def _ts_is_import_node(node_type: str, mode: str) -> bool:
    lower = node_type.lower()
    if mode == "markup":
        return any(token in lower for token in ("script", "style", "link", "include", "import", "resource"))
    if mode == "sql":
        return any(token in lower for token in ("from", "join", "into", "using", "with", "call", "reference", "source"))
    if mode == "config":
        return any(token in lower for token in ("include", "import", "source", "path", "file", "template", "script", "command"))
    # Wave 1p4eu: the grammar ROOT node (`source_file` for Rust/Kotlin/Go/Swift/
    # C/…) is NEVER an import, but the `source` import-keyword substring-matches
    # it — so the generic relation fallback regexed the ENTIRE file into junk
    # `external::<token>` import edges (every keyword/identifier on every line:
    # `use`/`pub`/`fn`/`as`/`package`/function names). Java's root (`program`)
    # never matched, which is why only the `source_file` languages were noisy.
    if lower == "source_file":
        return False
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


def _go_simple_type_name(type_node, source_bytes: bytes) -> str | None:
    """Type name from a Go type node (wave 1p4et; package-preserving since 1p4eq).

    `type_identifier` → itself; `pointer_type` (`*T`) → inner type; `qualified_type`
    (`pkg.Type`) → the PACKAGE-QUALIFIED `pkg.Type`. Returns None for shapes we
    don't model (slices, maps, func types, generics).

    Wave 1p4eq faithfulness fix: a `qualified_type` previously returned only the
    bare trailing `Type`, dropping the package. That collapsed `foo.Helper` and a
    co-located `bar.Helper` to the same `Helper` receiver key, so the 1p4er
    same-directory fallback could bind the caller's OWN-package twin even though
    the source explicitly named a DIFFERENT package — a wrong RECEIVER_RESOLVED
    edge (caught by the 1p4eq adversarial verification). Preserving `pkg.Type`
    lets the cross-file rewrite pass resolve by the candidate's package directory,
    and stay external when no project package matches `pkg`.
    """
    tt = getattr(type_node, "type", "")
    if tt == "type_identifier":
        return source_bytes[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace")
    if tt == "pointer_type":
        for c in (getattr(type_node, "children", []) or []):
            inner = _go_simple_type_name(c, source_bytes)
            if inner:
                return inner
    if tt == "qualified_type":
        pkg = None
        typ = None
        for c in (getattr(type_node, "children", []) or []):
            ct = getattr(c, "type", "")
            if ct == "package_identifier" and pkg is None:
                pkg = source_bytes[c.start_byte:c.end_byte].decode("utf-8", errors="replace")
            elif ct == "type_identifier":
                typ = source_bytes[c.start_byte:c.end_byte].decode("utf-8", errors="replace")
        if typ:
            return f"{pkg}.{typ}" if pkg else typ
    return None


def _go_method_node_receiver_type(method_node, source_bytes: bytes) -> str | None:
    """Receiver type of a Go `method_declaration` node directly (wave 1p4et).

    `func (h Helper) M()` / `func (h *Helper) M()` → 'Helper'. The FIRST
    `parameter_list` (between `func` and the name) is the receiver.
    """
    for child in (getattr(method_node, "children", []) or []):
        if getattr(child, "type", "") == "parameter_list":
            for pl_child in (getattr(child, "children", []) or []):
                if getattr(pl_child, "type", "") == "parameter_declaration":
                    for pd_child in (getattr(pl_child, "children", []) or []):
                        if getattr(pd_child, "type", "") in ("type_identifier", "pointer_type", "qualified_type"):
                            return _go_simple_type_name(pd_child, source_bytes)
            return None  # first parameter_list is the receiver; stop
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
                elif ct in ("type_identifier", "pointer_type", "qualified_type"):
                    type_child = child
            if name_child is not None and type_child is not None:
                var_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if var_name == name:
                    # Wave 1p4et: + qualified_type so `var h foo.Helper` infers `Helper`
                    # (the dominant cross-package receiver shape; previously returned None).
                    return _go_simple_type_name(type_child, source_bytes)
        elif n_type == "parameter_declaration":
            # parameter_declaration: identifier <name> + type_identifier <Type>
            name_child = None
            type_child = None
            for child in (getattr(n, "children", []) or []):
                ct = getattr(child, "type", "")
                if ct == "identifier" and name_child is None:
                    name_child = child
                elif ct in ("type_identifier", "pointer_type", "qualified_type"):
                    type_child = child
            if name_child is not None and type_child is not None:
                param_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if param_name == name:
                    return _go_simple_type_name(type_child, source_bytes)  # wave 1p4et: + qualified_type
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


def _rust_use_imports(use_node, source_bytes: bytes) -> list[tuple[str, str]]:
    """Wave 1p4eu: clean (head, dotted_target) pairs from a Rust `use_declaration`.

    Replaces the generic relation-candidate fallback, which emitted lossy
    `::`-joined paths (`external::crate::services::Helper`) plus `use`/`as`
    keyword-noise edges. Each pair's dotted target's FINAL segment is the
    imported type name (so `imports_by_file`, which keys by the target's last
    segment, is consumable); an `as` alias becomes the head while the target
    keeps the REAL type name (the caller registers the alias in `import_aliases`).

      use crate::services::Helper;            -> [("Helper", "crate.services.Helper")]
      use super::util::{Reader, Writer as W}; -> [("Reader","super.util.Reader"),
                                                  ("W","super.util.Writer")]
      use foo::Bar as Baz;                    -> [("Baz", "foo.Bar")]
      use crate::x::*;                        -> []   (glob — no specific symbol)
    """
    try:
        arg = use_node.child_by_field_name("argument")
    except Exception:
        arg = None
    if arg is None:
        return []
    out: list[tuple[str, str]] = []
    _rust_walk_use_tree(arg, "", source_bytes, out)
    return out


def _rust_walk_use_tree(node, prefix: str, source_bytes: bytes, out: list[tuple[str, str]]) -> None:
    """Recursive helper for `_rust_use_imports` — accumulates (head, target) pairs.

    `prefix` is the accumulated dotted path from any enclosing `scoped_use_list`
    (`use a::b::{...}`), without a trailing dot.
    """
    def _txt(n) -> str:
        return source_bytes[n.start_byte:n.end_byte].decode("utf-8", errors="replace")

    def _dotted(n) -> str:
        return _txt(n).replace("::", ".")

    def _join(p: str, seg: str) -> str:
        return f"{p}.{seg}" if (p and seg) else (p or seg)

    t = getattr(node, "type", "")
    if t == "scoped_identifier":
        name = node.child_by_field_name("name")
        if name is not None:
            out.append((_txt(name), _join(prefix, _dotted(node))))
    elif t == "identifier":
        nm = _txt(node)
        if nm:
            out.append((nm, _join(prefix, nm)))
    elif t == "use_as_clause":
        path = node.child_by_field_name("path")
        alias = node.child_by_field_name("alias")
        if path is not None and alias is not None:
            # head = alias; target keeps the REAL type/path (final segment = type)
            out.append((_txt(alias), _join(prefix, _dotted(path))))
    elif t == "scoped_use_list":
        path = node.child_by_field_name("path")
        lst = node.child_by_field_name("list")
        new_prefix = _join(prefix, _dotted(path)) if path is not None else prefix
        if lst is not None:
            for c in (getattr(lst, "children", []) or []):
                if getattr(c, "type", "") in (
                    "identifier", "scoped_identifier", "use_as_clause", "scoped_use_list",
                ):
                    _rust_walk_use_tree(c, new_prefix, source_bytes, out)
    # use_wildcard (`::*`) and punctuation: skip — no specific imported symbol.


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


def _rust_value_type(value_node, source_bytes: bytes) -> str | None:
    """Infer the type of a Rust let-binding value (wave 1p4eu).

    `Bar { .. }` (struct_expression) → 'Bar'; `Bar::new()` / `Type::from()` /
    `Type::with_capacity()` / `Type::default()` (a call to a scoped_identifier
    whose final segment is a constructor-convention name) → the type prefix.
    Anything else → None (conservative — only the syntactically-named-type cases,
    never an inter-procedural return type).
    """
    vt = getattr(value_node, "type", "")
    if vt == "struct_expression":
        for c in (getattr(value_node, "children", []) or []):
            ct = getattr(c, "type", "")
            if ct == "type_identifier":
                return source_bytes[c.start_byte:c.end_byte].decode("utf-8", errors="replace")
            if ct == "scoped_type_identifier":
                last = None
                for cc in (getattr(c, "children", []) or []):
                    if getattr(cc, "type", "") == "type_identifier":
                        last = cc
                if last is not None:
                    return source_bytes[last.start_byte:last.end_byte].decode("utf-8", errors="replace")
        return None
    if vt == "call_expression":
        children = list(getattr(value_node, "children", []) or [])
        callee = children[0] if children else None
        if callee is not None and getattr(callee, "type", "") == "scoped_identifier":
            text = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace")
            parts = text.split("::")
            ctor = parts[-1] if parts else ""
            if (
                len(parts) >= 2
                and parts[-2][:1].isupper()
                and (ctor in ("new", "from", "default") or ctor.startswith("with_"))
            ):
                return parts[-2]
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
            if name_child is not None:
                var_name = source_bytes[name_child.start_byte:name_child.end_byte].decode("utf-8", errors="replace")
                if var_name == name:
                    if type_child is not None:
                        return source_bytes[type_child.start_byte:type_child.end_byte].decode("utf-8", errors="replace")
                    # Wave 1p4eu: no explicit annotation — infer from the value
                    # (`let x = Bar{..}` / `let x = Bar::new()`).
                    try:
                        value_node = n.child_by_field_name("value")
                    except Exception:
                        value_node = None
                    if value_node is not None:
                        inferred = _rust_value_type(value_node, source_bytes)
                        if inferred:
                            return inferred
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
    # Wave 1p4eu: associated-function call `Type::assoc_fn()` — callee is a
    # scoped_identifier (`new` is owned by the construction resolver, excluded
    # here). The `::` form is never indexed; emit the DOTTED `external::Type.fn`
    # so the rewrite pass's qualified_index can resolve it cross-file. The
    # PascalCase guard makes a module-fn call like `io::stdin()` fall through to
    # None (stays external) — never mis-keyed as a type method (faithfulness).
    if callee_type == "scoped_identifier":
        _txt = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace")
        _parts = _txt.split("::")
        if len(_parts) >= 2 and _parts[-1] != "new" and _parts[-2][:1].isupper():
            _rt, _fn = _parts[-2], _parts[-1]
            _q = f"{_rt}.{_fn}"
            return symbol_lookup[_q] if _q in symbol_lookup else f"external::{_rt}.{_fn}"
        return None
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


# Wave 131bt (1319s): Construction-call resolution.
#
# Languages with explicit-shape construction nodes — the type identifier is
# extracted directly from the AST.
_CONSTRUCTION_EXPLICIT_NODE_TYPES_BY_LANG: dict[str, frozenset[str]] = {
    "java": frozenset({"object_creation_expression"}),
    "csharp": frozenset({"object_creation_expression"}),
    "typescript": frozenset({"new_expression"}),
    "javascript": frozenset({"new_expression"}),
    "php": frozenset({"object_creation_expression"}),
    "rust": frozenset({"struct_expression"}),
    "go": frozenset({"composite_literal"}),
}

# Languages where bare PascalCase calls indicate construction. The detector
# requires (a) callee is a bare identifier (no navigation/scope prefix), (b)
# the name resolves to a class/struct/enum/actor/protocol symbol via
# symbol_lookup. Per the prepare-council red-team finding, the symbol-lookup
# precondition is scope-aware: the call's resolver consults symbol_lookup which
# tracks lexically reachable definitions, and methods on the enclosing class
# shadow same-named sibling classes (handled by the qname structure of
# symbol_lookup entries).
_CONSTRUCTION_BARE_CALL_LANGS: frozenset[str] = frozenset({
    "swift", "python", "kotlin", "scala",
})

# Kinds that confirm the symbol is a class-like construct (not a function
# whose name happens to be PascalCase). Used by the bare-call resolver.
_CLASS_LIKE_KINDS_FOR_CONSTRUCTION: frozenset[str] = frozenset({
    "class", "struct", "enum", "actor", "protocol", "interface",
    "record", "module",  # Ruby module is namespace-like; allow it as a construction target.
})


def _ts_construction_node_text(node, source_bytes: bytes, field_name: str) -> str | None:
    """Extract field text from a construction node; return None on miss."""
    try:
        child = node.child_by_field_name(field_name)
    except Exception:
        child = None
    if child is None:
        return None
    text = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip()
    return text or None


def _ts_extract_type_identifier_child(node, source_bytes: bytes) -> str | None:
    """Return the first child of type ``type_identifier`` / ``identifier`` / ``name``.

    Used for AST shapes where the type name appears as a direct named child but
    is not bound to a specific field (Go composite_literal in some grammars, etc.).
    """
    for child in getattr(node, "named_children", []) or []:
        ctype = getattr(child, "type", "") or ""
        if ctype in ("type_identifier", "identifier", "name"):
            text = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip()
            if text:
                return text
    return None


def _ts_lookup_class_node(simple_name: str, symbol_lookup: dict[str, str]) -> str | None:
    """Resolve a simple class name to a class-like node id, or None.

    The lookup tries (a) the simple name directly (project-internal class merge
    means ``Foo`` often resolves to ``src/Foo.java``), and (b) the import-alias
    chain via cross-file resolution at the post-pass. For consistency with the
    receiver-type resolvers, we return the qname-matched id when present and
    let the cross-file rewrite handle the rest.
    """
    if not simple_name:
        return None
    if simple_name in symbol_lookup:
        return symbol_lookup[simple_name]
    return None


def _resolve_construction_target(
    call_node,
    node_type: str,
    source_bytes: bytes,
    symbol_lookup: dict[str, str],
    symbol_lookup_kinds: dict[str, str],
    lang_key: str,
) -> str | None:
    """Resolve a construction-shaped call to a class-like node id.

    Handles two categories:

    1. Explicit-shape construction (Java/C#/TS/JS ``object_creation_expression``
       / ``new_expression``, PHP ``object_creation_expression``, Rust
       ``struct_expression``, Go ``composite_literal``). The AST node carries
       the type identifier directly.

    2. Bare-call construction (Swift/Python/Kotlin/Scala). The callee is a
       bare PascalCase identifier and the name resolves to a class-like
       symbol via ``symbol_lookup``.

    Also handles two retarget cases:

    3. Rust ``Foo::new()`` convention — the call is captured as a
       ``call_expression`` whose callee is a ``scoped_identifier`` ending in
       ``new``. Retargets to the struct node when the prefix matches a
       ``struct_item``/``enum_item`` in ``symbol_lookup``. Lower-confidence
       convention; the caller still tags with ``CONSTRUCTION_RESOLVED``.

    4. Go ``new(<TypeName>)`` builtin — extract the type-identifier argument
       and retarget to the struct node.

    Returns:
        The resolved class-node id (project or import-aliased), or None when
        the node is not a construction shape or the type is not in scope.

    Per the prepare-council red-team finding, scope-aware symbol lookup is
    enforced by ``symbol_lookup_kinds``: a class symbol only wins when it
    resolves to a class-like kind. Methods or functions with PascalCase names
    do not match.
    """
    if call_node is None or not node_type:
        return None

    # --- Explicit-shape construction nodes (per-language) ---
    explicit_types = _CONSTRUCTION_EXPLICIT_NODE_TYPES_BY_LANG.get(lang_key, frozenset())
    if node_type in explicit_types:
        # Per-language type-name extraction.
        type_name: str | None = None
        if lang_key in ("java", "csharp"):
            # object_creation_expression: ``type`` field carries the class name
            # (Java type_identifier / C# identifier).
            type_name = _ts_construction_node_text(call_node, source_bytes, "type")
        elif lang_key == "php":
            # PHP object_creation_expression has no field names; the class
            # name appears as a named child of type ``name``.
            type_name = _ts_extract_type_identifier_child(call_node, source_bytes)
        elif lang_key in ("typescript", "javascript"):
            # new_expression: ``constructor`` field carries the class name.
            type_name = _ts_construction_node_text(call_node, source_bytes, "constructor")
        elif lang_key == "rust":
            # struct_expression: ``name`` field carries the type identifier.
            type_name = _ts_construction_node_text(call_node, source_bytes, "name")
        elif lang_key == "go":
            # composite_literal: ``type`` field — filter to type_identifier-only
            # to exclude map/slice/array literals.
            try:
                type_child = call_node.child_by_field_name("type")
            except Exception:
                type_child = None
            if type_child is not None:
                tc_type = getattr(type_child, "type", "") or ""
                if tc_type == "type_identifier":
                    type_name = source_bytes[type_child.start_byte:type_child.end_byte].decode("utf-8", errors="replace").strip() or None

        if type_name:
            # Strip generic type-parameter suffix for languages that allow them
            # in construction position (TS ``new Container<Foo>()``, C# ``new
            # List<Foo>()``). Use the outermost type only.
            if "<" in type_name:
                type_name = type_name.split("<", 1)[0].strip()
            resolved = _ts_lookup_class_node(type_name, symbol_lookup)
            if resolved is not None:
                # Scope-aware kind check: ensure the symbol IS a class-like
                # entity, not a function whose name happens to be PascalCase.
                kind = symbol_lookup_kinds.get(type_name, "")
                if not kind or kind in _CLASS_LIKE_KINDS_FOR_CONSTRUCTION:
                    return resolved
                # If kind says it's a function/method, do NOT route as
                # construction; the caller falls back to standard attribution.
                return None
            # When the symbol is not in scope, return None — the cross-file
            # rewrite pass at the end handles import resolution. We return the
            # external-prefixed key so the cross-file pass can promote it.
            return f"external::{type_name}"

    # --- Rust ``Foo::new()`` convention (retarget) ---
    if lang_key == "rust" and node_type == "call_expression":
        target = _resolve_rust_new_convention(call_node, source_bytes, symbol_lookup, symbol_lookup_kinds)
        if target is not None:
            return target

    # --- Go ``new(<TypeName>)`` builtin (retarget) ---
    if lang_key == "go" and node_type == "call_expression":
        target = _resolve_go_new_builtin(call_node, source_bytes, symbol_lookup, symbol_lookup_kinds)
        if target is not None:
            return target

    # --- Ruby ``Foo.new(...)`` shape ---
    if lang_key == "ruby" and node_type in ("call", "method_call"):
        target = _resolve_ruby_new_call(call_node, source_bytes, symbol_lookup, symbol_lookup_kinds)
        if target is not None:
            return target

    # --- Bare-call construction (Swift/Python/Kotlin/Scala) ---
    if lang_key in _CONSTRUCTION_BARE_CALL_LANGS and node_type in ("call_expression", "call"):
        target = _resolve_bare_call_construction(call_node, source_bytes, symbol_lookup, symbol_lookup_kinds, lang_key)
        if target is not None:
            return target

    return None


def _resolve_rust_new_convention(
    call_node, source_bytes: bytes, symbol_lookup: dict[str, str], symbol_lookup_kinds: dict[str, str]
) -> str | None:
    """Retarget Rust ``Foo::new()`` to the struct node when ``Foo`` is in scope.

    Convention only; not language-required. Returns the struct node id when
    the prefix matches a class-like symbol; otherwise None (so the standard
    receiver-type/EXTRACTED path runs).
    """
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    try:
        callee = call_node.child_by_field_name("function")
    except Exception:
        callee = None
    if callee is None:
        return None
    if getattr(callee, "type", "") != "scoped_identifier":
        return None
    text = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace").strip()
    if not text or "::" not in text:
        return None
    parts = text.split("::")
    if parts[-1] != "new" or len(parts) < 2:
        return None
    type_name = parts[-2]
    if not type_name or not type_name[:1].isupper():
        return None
    kind = symbol_lookup_kinds.get(type_name, "")
    if kind and kind not in _CLASS_LIKE_KINDS_FOR_CONSTRUCTION:
        return None
    resolved = _ts_lookup_class_node(type_name, symbol_lookup)
    if resolved is not None:
        return resolved
    # Cross-file fallback: return external::<TypeName> so the cross-file
    # rewrite pass can promote to a project node via simple_name_index.
    return f"external::{type_name}"


def _resolve_go_new_builtin(
    call_node, source_bytes: bytes, symbol_lookup: dict[str, str], symbol_lookup_kinds: dict[str, str]
) -> str | None:
    """Retarget Go ``new(<TypeName>)`` to the struct node.

    The ``new`` builtin takes a single type-identifier argument. Returns the
    struct node id when the argument matches a class-like symbol; otherwise
    None.
    """
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    try:
        callee = call_node.child_by_field_name("function")
    except Exception:
        callee = None
    if callee is None:
        return None
    callee_text = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace").strip()
    if callee_text != "new":
        return None
    try:
        args = call_node.child_by_field_name("arguments")
    except Exception:
        args = None
    if args is None:
        return None
    for child in getattr(args, "named_children", []) or []:
        if getattr(child, "type", "") == "type_identifier":
            type_name = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip()
            if not type_name:
                continue
            kind = symbol_lookup_kinds.get(type_name, "")
            if kind and kind not in _CLASS_LIKE_KINDS_FOR_CONSTRUCTION:
                return None
            resolved = _ts_lookup_class_node(type_name, symbol_lookup)
            if resolved is not None:
                return resolved
            return f"external::{type_name}"
    return None


def _resolve_ruby_new_call(
    call_node, source_bytes: bytes, symbol_lookup: dict[str, str], symbol_lookup_kinds: dict[str, str]
) -> str | None:
    """Resolve Ruby ``Foo.new(args)`` to the class/module node when in scope."""
    if call_node is None:
        return None
    # Tree-sitter Ruby: call → receiver, method
    try:
        method = call_node.child_by_field_name("method")
    except Exception:
        method = None
    if method is None:
        return None
    method_name = source_bytes[method.start_byte:method.end_byte].decode("utf-8", errors="replace").strip()
    if method_name != "new":
        return None
    try:
        receiver = call_node.child_by_field_name("receiver")
    except Exception:
        receiver = None
    if receiver is None:
        return None
    receiver_text = source_bytes[receiver.start_byte:receiver.end_byte].decode("utf-8", errors="replace").strip()
    if not receiver_text or not receiver_text[:1].isupper():
        return None
    kind = symbol_lookup_kinds.get(receiver_text, "")
    if kind and kind not in _CLASS_LIKE_KINDS_FOR_CONSTRUCTION:
        return None
    resolved = _ts_lookup_class_node(receiver_text, symbol_lookup)
    if resolved is not None:
        return resolved
    return f"external::{receiver_text}"


def _resolve_bare_call_construction(
    call_node, source_bytes: bytes, symbol_lookup: dict[str, str], symbol_lookup_kinds: dict[str, str], lang_key: str
) -> str | None:
    """Resolve a bare PascalCase call to a class-like node, or None.

    Used for Swift/Python/Kotlin/Scala. Requires the callee to be a bare
    identifier (no navigation/scope prefix) starting with an uppercase letter,
    AND the name to resolve to a class-like symbol in scope.

    For Swift, ``Foo.init(args)`` is also handled (navigation_expression with
    ``init`` selector on a type name).

    Returns None when the callee is not a bare PascalCase identifier or the
    name does not match a class-like symbol — the caller then falls through
    to receiver-type or standard attribution.
    """
    if call_node is None:
        return None
    children = list(getattr(call_node, "children", []) or [])
    if not children:
        return None
    callee = children[0]
    callee_type = getattr(callee, "type", "") or ""

    name: str | None = None
    if callee_type in ("simple_identifier", "identifier", "constant"):
        # Bare identifier callee. Extract the name.
        name = source_bytes[callee.start_byte:callee.end_byte].decode("utf-8", errors="replace").strip()
    elif lang_key == "swift" and callee_type == "navigation_expression":
        # Swift ``Foo.init(args)`` — the type name is the first child and the
        # navigation suffix selector is ``init``.
        nav_children = list(getattr(callee, "children", []) or [])
        if not nav_children:
            return None
        # First child is the type identifier; the navigation_suffix should
        # contain ``init``.
        type_child = nav_children[0]
        type_text = source_bytes[type_child.start_byte:type_child.end_byte].decode("utf-8", errors="replace").strip()
        # Verify the selector is ``init``.
        selector_is_init = False
        for nc in nav_children[1:]:
            if getattr(nc, "type", "") == "navigation_suffix":
                for sc in (getattr(nc, "children", []) or []):
                    sc_text = source_bytes[sc.start_byte:sc.end_byte].decode("utf-8", errors="replace").strip()
                    if sc_text == "init":
                        selector_is_init = True
                        break
                break
        if not selector_is_init:
            return None
        if not type_text or not type_text[:1].isupper():
            return None
        name = type_text

    if not name:
        return None
    # Must start with uppercase (PascalCase discriminator).
    if not name[:1].isupper():
        return None
    # Scope-aware kind check: only route to class-like symbols.
    kind = symbol_lookup_kinds.get(name, "")
    if kind and kind not in _CLASS_LIKE_KINDS_FOR_CONSTRUCTION:
        # The name resolves to a non-class entity (function, method) — don't
        # route as construction; fall through to standard attribution.
        return None
    resolved = _ts_lookup_class_node(name, symbol_lookup)
    if resolved is not None:
        return resolved
    # When the symbol is not in scope locally, return external::<name> so the
    # cross-file rewrite pass can promote to a project node via
    # simple_name_index. The PascalCase + class-kind precondition (above)
    # filters out methods/functions; only legitimate class references reach
    # this fallback.
    return f"external::{name}"


# Wave 131bt (1319q): TypeScript / JavaScript receiver-type resolution.
#
# TS/JS share the same tree-sitter grammar family. Receiver-type resolution
# requires the call to be of the form ``foo.bar()`` where ``foo`` has a known
# type — either from a TS type annotation (``let foo: Foo = ...``,
# ``function m(foo: Foo)``), an ``as`` cast (``(x as Foo).bar()``), or JSDoc
# ``/** @type {Foo} */`` immediately preceding the declaration (JS).
#
# Phase 1 (TS native annotations) is implemented; Phase 2 (JS JSDoc regex
# extraction) is the same dispatch shape with a separate annotation source.
# When no annotation is found, the helper returns None and standard attribution
# proceeds — no false positives from inference, matching ``mypy`` / TSC's
# ``strict`` defaults.


def _extract_simple_ts_type_name(type_node, source_bytes: bytes) -> str | None:
    """Extract a single type identifier from a TS type_annotation subtree.

    Handles `type_annotation > type_identifier`, generic_type (Container<Foo>
    → "Container"), union_type (Foo | null → "Foo"), and nullable shapes.
    """
    if type_node is None:
        return None
    n_type = getattr(type_node, "type", "")
    if n_type == "type_annotation":
        for child in (getattr(type_node, "named_children", []) or []):
            return _extract_simple_ts_type_name(child, source_bytes)
        return None
    if n_type == "type_identifier":
        return source_bytes[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace").strip() or None
    if n_type == "generic_type":
        # Container<Foo> — extract the outer type name.
        for child in (getattr(type_node, "named_children", []) or []):
            ct = getattr(child, "type", "")
            if ct == "type_identifier":
                return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip() or None
        return None
    if n_type in ("union_type", "intersection_type"):
        # Foo | null → extract the first non-null type.
        for child in (getattr(type_node, "named_children", []) or []):
            ct = getattr(child, "type", "")
            if ct in ("type_identifier", "generic_type"):
                inner = _extract_simple_ts_type_name(child, source_bytes)
                if inner and inner not in ("null", "undefined"):
                    return inner
        return None
    if n_type == "nullable_type":
        for child in (getattr(type_node, "named_children", []) or []):
            inner = _extract_simple_ts_type_name(child, source_bytes)
            if inner:
                return inner
        return None
    if n_type == "predefined_type":
        # `void`, `string`, etc. — not class-like.
        return None
    return None


def _find_enclosing_ts_class_name(node, source_bytes: bytes) -> str | None:
    """Walk up to the enclosing TS/JS class_declaration's name."""
    cur = getattr(node, "parent", None)
    while cur is not None:
        ctype = getattr(cur, "type", "") or ""
        if ctype in ("class_declaration", "abstract_class_declaration"):
            try:
                name_node = cur.child_by_field_name("name")
            except Exception:
                name_node = None
            if name_node is not None:
                return source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace").strip() or None
            return None
        cur = getattr(cur, "parent", None)
    return None


_JSDOC_TYPE_RE = re.compile(r"@type\s*\{\s*([A-Za-z_][\w.]*)")
_JSDOC_PARAM_RE = re.compile(r"@param\s*\{\s*([A-Za-z_][\w.]*)\s*\}\s*([A-Za-z_]\w*)")


def _ts_jsdoc_type_for_lexical_decl(lex_decl, source_bytes: bytes) -> str | None:
    """Return the JS type from a JSDoc `@type {Foo}` comment preceding a
    `lexical_declaration`. JS-only — TS uses native annotations.

    Walks the immediately-preceding sibling looking for a comment shaped
    ``/** @type {Foo} */``. Returns the bare type name or None.
    """
    parent = getattr(lex_decl, "parent", None)
    if parent is None:
        return None
    children = list(getattr(parent, "children", []) or [])
    try:
        idx = children.index(lex_decl)
    except ValueError:
        return None
    # Scan backwards for the nearest comment sibling.
    for prev in reversed(children[:idx]):
        ctype = getattr(prev, "type", "") or ""
        if ctype != "comment":
            break  # Not a comment — JSDoc must be immediately adjacent.
        text = source_bytes[prev.start_byte:prev.end_byte].decode("utf-8", errors="replace")
        if text.startswith("/**"):
            m = _JSDOC_TYPE_RE.search(text)
            if m:
                return m.group(1)
    return None


def _search_ts_declarations_in_scope(scope_node, name: str, source_bytes: bytes) -> str | None:
    """Search TS/JS scope for `let foo: Foo = ...` / parameter `foo: Foo`
    OR (JS only) the preceding JSDoc ``@type {Foo}`` comment."""
    stack = [scope_node]
    while stack:
        n = stack.pop()
        n_type = getattr(n, "type", "") or ""
        # let / const / var declarators
        if n_type == "variable_declarator":
            try:
                name_node = n.child_by_field_name("name")
            except Exception:
                name_node = None
            try:
                type_node = n.child_by_field_name("type")
            except Exception:
                type_node = None
            if name_node is not None:
                var_name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace").strip()
                if var_name == name:
                    # Native annotation (TS) takes precedence.
                    if type_node is not None:
                        resolved = _extract_simple_ts_type_name(type_node, source_bytes)
                        if resolved:
                            return resolved
                    # JS JSDoc fallback: look at the preceding comment on the
                    # enclosing lexical_declaration.
                    lex_decl = getattr(n, "parent", None)
                    if lex_decl is not None and getattr(lex_decl, "type", "") == "lexical_declaration":
                        return _ts_jsdoc_type_for_lexical_decl(lex_decl, source_bytes)
                    return None
            if name_node is not None and type_node is not None:
                var_name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace").strip()
                if var_name == name:
                    return _extract_simple_ts_type_name(type_node, source_bytes)
        # Function parameters with type annotations
        elif n_type in ("required_parameter", "optional_parameter"):
            param_name = None
            type_child = None
            for child in (getattr(n, "named_children", []) or []):
                ct = getattr(child, "type", "") or ""
                if ct == "identifier" and param_name is None:
                    param_name = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip()
                elif ct == "type_annotation":
                    type_child = child
            if param_name == name and type_child is not None:
                return _extract_simple_ts_type_name(type_child, source_bytes)
        # Don't descend into nested function/class bodies.
        if n_type in (
            "function_declaration", "function_expression", "arrow_function",
            "method_definition", "class_declaration", "abstract_class_declaration",
        ) and n is not scope_node:
            continue
        stack.extend(reversed(getattr(n, "named_children", []) or []))
    return None


def _resolve_ts_identifier_type(name: str, ref_node, source_bytes: bytes) -> str | None:
    """Resolve a TS/JS identifier to its declared type by walking up scopes."""
    cur = getattr(ref_node, "parent", None)
    while cur is not None:
        cur_type = getattr(cur, "type", "") or ""
        if cur_type in (
            "function_declaration", "function_expression", "arrow_function",
            "method_definition", "class_declaration", "abstract_class_declaration",
            "statement_block", "program",
        ):
            resolved = _search_ts_declarations_in_scope(cur, name, source_bytes)
            if resolved is not None:
                return resolved
            if cur_type in ("class_declaration", "abstract_class_declaration", "program"):
                break
        cur = getattr(cur, "parent", None)
    return None


def _resolve_ts_receiver_type(call_node, source_bytes: bytes) -> str | None:
    """Resolve a TS/JS call_expression receiver type.

    Handles:
    - `foo.bar()` where `foo` has a declared type — call_expression with
      function=member_expression(object, property).
    - `this.bar()` — routes to enclosing class.
    - `super.bar()` — uncertain; return None.
    - Bare `bar()` — resolves to enclosing class for non-PascalCase callees.
    """
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    try:
        func = call_node.child_by_field_name("function")
    except Exception:
        func = None
    if func is None:
        return None
    func_type = getattr(func, "type", "") or ""
    if func_type == "member_expression":
        try:
            obj = func.child_by_field_name("object")
        except Exception:
            obj = None
        if obj is None:
            return None
        obj_type = getattr(obj, "type", "") or ""
        if obj_type == "identifier":
            text = source_bytes[obj.start_byte:obj.end_byte].decode("utf-8", errors="replace").strip()
            if text == "this":
                return _find_enclosing_ts_class_name(call_node, source_bytes)
            if text == "super":
                return None
            # PascalCase: static call like `Foo.method()` — receiver IS the class.
            if text and text[:1].isupper():
                return text
            return _resolve_ts_identifier_type(text, call_node, source_bytes)
        if obj_type == "this":
            return _find_enclosing_ts_class_name(call_node, source_bytes)
        if obj_type == "as_expression":
            # (x as Foo).bar() — type is on the right side of `as`
            try:
                type_child = obj.child_by_field_name("type")
            except Exception:
                type_child = None
            if type_child is None:
                # Fallback to scanning children
                for c in (getattr(obj, "named_children", []) or [])[::-1]:
                    ct = getattr(c, "type", "") or ""
                    if ct in ("type_identifier", "generic_type", "union_type"):
                        type_child = c
                        break
            if type_child is not None:
                return _extract_simple_ts_type_name(type_child, source_bytes)
            return None
        return None
    if func_type == "identifier":
        # Bare call — `bar()` from inside a class method routes to enclosing class.
        text = source_bytes[func.start_byte:func.end_byte].decode("utf-8", errors="replace").strip()
        if text and text[:1].isupper():
            # Constructor-style call (`Foo()` without `new`) — defer.
            return None
        return _find_enclosing_ts_class_name(call_node, source_bytes)
    return None


def _resolve_ts_call_target(
    call_node,
    source_bytes: bytes,
    symbol_lookup: dict[str, str],
    import_targets: dict[str, str] | None = None,
) -> str | None:
    """Resolve a TS/JS call_expression to a graph node id when receiver type is known.

    Wave 1p2q3 (1p2tf): when the receiver type was imported (e.g.
    `import { Foo } from '@aceiss/lib'` resolved to a project file via
    tsconfig.paths), `import_targets[receiver_type]` carries the resolved
    project node id. The resolver constructs the cross-file node id directly
    instead of falling through to `external::*`, so receiver-resolved edges
    land on aliased cross-package types without depending on the per-project
    unambiguous-simple-name cross-file rewrite.
    """
    if call_node is None or getattr(call_node, "type", "") != "call_expression":
        return None
    try:
        func = call_node.child_by_field_name("function")
    except Exception:
        func = None
    if func is None:
        return None
    func_type = getattr(func, "type", "") or ""
    method_name: str | None = None
    if func_type == "member_expression":
        try:
            prop = func.child_by_field_name("property")
        except Exception:
            prop = None
        if prop is not None:
            method_name = source_bytes[prop.start_byte:prop.end_byte].decode("utf-8", errors="replace").strip() or None
    elif func_type == "identifier":
        method_name = source_bytes[func.start_byte:func.end_byte].decode("utf-8", errors="replace").strip() or None
    if not method_name:
        return None
    receiver_type = _resolve_ts_receiver_type(call_node, source_bytes)
    if receiver_type is None:
        return None
    qualified = f"{receiver_type}.{method_name}"
    if qualified in symbol_lookup:
        return symbol_lookup[qualified]
    # Wave 1p2q3 (1p2tf): aliased-import receiver-type resolution.
    if import_targets:
        target = import_targets.get(receiver_type)
        if target and not target.startswith("external::"):
            return f"{target}::{receiver_type}.{method_name}"
    return f"external::{receiver_type}.{method_name}"


# Wave 131bt (1319q): PHP receiver-type resolution.
#
# PHP grammars expose native type hints directly. Object method calls use
# ``->`` syntax (member_call_expression). Static calls use ``::``
# (scoped_call_expression). Resolution mirrors TS but reads PHP-specific
# field names.


def _extract_simple_php_type_name(type_node, source_bytes: bytes) -> str | None:
    if type_node is None:
        return None
    n_type = getattr(type_node, "type", "") or ""
    if n_type in ("named_type", "type_list"):
        # PHP wraps types in a `named_type` node; extract the `name` child.
        for child in (getattr(type_node, "named_children", []) or []):
            ct = getattr(child, "type", "") or ""
            if ct == "name":
                text = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip()
                return text or None
        return None
    if n_type == "name":
        text = source_bytes[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace").strip()
        return text or None
    if n_type == "optional_type":
        for child in (getattr(type_node, "named_children", []) or []):
            inner = _extract_simple_php_type_name(child, source_bytes)
            if inner:
                return inner
        return None
    if n_type == "primitive_type":
        return None  # int/string/bool are not class-like.
    return None


def _find_enclosing_php_class_name(node, source_bytes: bytes) -> str | None:
    cur = getattr(node, "parent", None)
    while cur is not None:
        ctype = getattr(cur, "type", "") or ""
        if ctype in ("class_declaration", "interface_declaration", "trait_declaration"):
            try:
                name_node = cur.child_by_field_name("name")
            except Exception:
                name_node = None
            if name_node is not None:
                return source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace").strip() or None
            return None
        cur = getattr(cur, "parent", None)
    return None


def _search_php_declarations_in_scope(scope_node, name: str, source_bytes: bytes) -> str | None:
    """Search PHP scope for parameter / property declarations matching name."""
    target = "$" + name if not name.startswith("$") else name
    stack = [scope_node]
    while stack:
        n = stack.pop()
        n_type = getattr(n, "type", "") or ""
        if n_type == "simple_parameter":
            param_name = None
            type_child = None
            for child in (getattr(n, "named_children", []) or []):
                ct = getattr(child, "type", "") or ""
                if ct == "variable_name":
                    param_name = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip()
                elif ct in ("named_type", "optional_type", "primitive_type"):
                    type_child = child
            if param_name == target and type_child is not None:
                return _extract_simple_php_type_name(type_child, source_bytes)
        elif n_type == "property_declaration":
            # PHP 7.4+ typed property: `private Foo $foo;`
            type_child = None
            for child in (getattr(n, "named_children", []) or []):
                ct = getattr(child, "type", "") or ""
                if ct in ("named_type", "primitive_type") and type_child is None:
                    type_child = child
                elif ct == "property_element":
                    for gc in (getattr(child, "named_children", []) or []):
                        if getattr(gc, "type", "") == "variable_name":
                            prop_name = source_bytes[gc.start_byte:gc.end_byte].decode("utf-8", errors="replace").strip()
                            if prop_name == target and type_child is not None:
                                return _extract_simple_php_type_name(type_child, source_bytes)
        # Don't descend into nested function/class bodies.
        if n_type in (
            "method_declaration", "function_definition",
            "class_declaration", "interface_declaration", "trait_declaration",
        ) and n is not scope_node:
            continue
        stack.extend(reversed(getattr(n, "named_children", []) or []))
    return None


def _resolve_php_identifier_type(name: str, ref_node, source_bytes: bytes) -> str | None:
    cur = getattr(ref_node, "parent", None)
    while cur is not None:
        cur_type = getattr(cur, "type", "") or ""
        if cur_type in (
            "method_declaration", "function_definition",
            "class_declaration", "interface_declaration", "trait_declaration",
            "compound_statement",
        ):
            resolved = _search_php_declarations_in_scope(cur, name, source_bytes)
            if resolved is not None:
                return resolved
            if cur_type in ("class_declaration", "interface_declaration", "trait_declaration"):
                break
        cur = getattr(cur, "parent", None)
    return None


def _resolve_php_call_target(call_node, source_bytes: bytes, symbol_lookup: dict[str, str]) -> str | None:
    """Resolve PHP member_call_expression / scoped_call_expression to a node id."""
    if call_node is None:
        return None
    n_type = getattr(call_node, "type", "") or ""
    if n_type == "member_call_expression":
        # $obj->method(args)
        try:
            obj = call_node.child_by_field_name("object")
            method_node = call_node.child_by_field_name("name")
        except Exception:
            return None
        if obj is None or method_node is None:
            return None
        obj_type = getattr(obj, "type", "") or ""
        method_name = source_bytes[method_node.start_byte:method_node.end_byte].decode("utf-8", errors="replace").strip()
        if not method_name:
            return None
        receiver_type: str | None = None
        if obj_type == "variable_name":
            var_text = source_bytes[obj.start_byte:obj.end_byte].decode("utf-8", errors="replace").strip()
            if var_text == "$this":
                receiver_type = _find_enclosing_php_class_name(call_node, source_bytes)
            else:
                # Strip leading $ before searching
                bare = var_text[1:] if var_text.startswith("$") else var_text
                receiver_type = _resolve_php_identifier_type(bare, call_node, source_bytes)
        if receiver_type is None:
            return None
        qualified = f"{receiver_type}.{method_name}"
        if qualified in symbol_lookup:
            return symbol_lookup[qualified]
        return f"external::{receiver_type}.{method_name}"
    if n_type == "scoped_call_expression":
        # Foo::method(args) — static call where receiver is the class itself.
        try:
            scope = call_node.child_by_field_name("scope")
            method_node = call_node.child_by_field_name("name")
        except Exception:
            return None
        if scope is None or method_node is None:
            return None
        method_name = source_bytes[method_node.start_byte:method_node.end_byte].decode("utf-8", errors="replace").strip()
        scope_text = source_bytes[scope.start_byte:scope.end_byte].decode("utf-8", errors="replace").strip()
        if not method_name or not scope_text:
            return None
        if scope_text in ("self", "static", "parent"):
            scope_text = _find_enclosing_php_class_name(call_node, source_bytes) or ""
            if not scope_text:
                return None
        qualified = f"{scope_text}.{method_name}"
        if qualified in symbol_lookup:
            return symbol_lookup[qualified]
        return f"external::{scope_text}.{method_name}"
    return None


# Wave 1p2q3 (1p2td): per-overload parameter-signature extraction so the per-file
# qname-merge that collapses overloads into one node can still be unwound at the
# edge layer. A self-edge on a merged node ambiguously denotes either recursion
# or overload-forwarding; comparing the call-site signature against the enclosing
# overload's signature and the merged node's overload-signature set distinguishes
# them. Swift uses argument labels (native syntax); Java/Kotlin/C#/Scala/C++ use
# arity plus optional named-arg labels.

_OVERLOAD_LANGUAGES: frozenset[str] = frozenset({"swift", "java", "kotlin", "csharp", "scala", "cpp"})


def _swift_param_signature(def_node, source_bytes: bytes) -> str | None:
    """Return Swift parameter-label fingerprint like ``base:offset:customTime:``.

    Tree-sitter Swift exposes parameters as repeated `parameter` siblings
    directly under the `function_declaration` node (no wrapping node).
    Each `parameter` has children: an optional external label identifier,
    then the internal name identifier, then `:`, then the type.
    """
    if def_node is None:
        return None
    labels: list[str] = []
    for child in (getattr(def_node, "children", []) or []):
        if getattr(child, "type", "") == "parameter":
            labels.append(_swift_extract_param_label(child, source_bytes))
    if not labels:
        return "()"
    return "".join(f"{lbl}:" for lbl in labels)


def _swift_extract_param_label(param_node, source_bytes: bytes) -> str:
    """Extract a single Swift parameter's external label (or internal name)."""
    # Tree-sitter Swift exposes parameter children in order:
    #   external_label? (or simple_identifier) simple_identifier ':' type
    # When the first identifier is present and the second is too, the first
    # is the external label. When only one identifier, that IS the label.
    idents: list[str] = []
    for child in (getattr(param_node, "children", []) or []):
        ctype = getattr(child, "type", "") or ""
        if ctype in ("simple_identifier", "identifier", "external_label"):
            text = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            idents.append(text)
    if not idents:
        return "_"
    if len(idents) >= 2:
        return idents[0] or "_"
    return idents[0] or "_"


def _arity_param_signature(def_node, source_bytes: bytes, lang_key: str) -> str | None:
    """Return ``arity:N`` for Java/Kotlin/C#/Scala/C++ definitions.

    Counts the parameter nodes inside the language-specific parameter list.
    Languages with named arguments at call sites still use this as the
    definition-side signature (named args at call sites are matched against
    arity + label-set during call-signature derivation).
    """
    if def_node is None:
        return None
    param_list_types = {
        "java": ("formal_parameters",),
        "kotlin": ("function_value_parameters", "class_parameters"),
        "csharp": ("parameter_list",),
        "scala": ("parameters", "class_parameters"),
        "cpp": ("parameter_list",),
    }.get(lang_key, ())
    param_child_types = {
        "java": ("formal_parameter", "spread_parameter"),
        "kotlin": ("parameter", "class_parameter"),
        "csharp": ("parameter",),
        "scala": ("parameter", "class_parameter"),
        "cpp": ("parameter_declaration",),
    }.get(lang_key, ())
    for child in (getattr(def_node, "children", []) or []):
        ctype = getattr(child, "type", "") or ""
        if ctype in param_list_types:
            count = 0
            for grandchild in (getattr(child, "children", []) or []):
                gtype = getattr(grandchild, "type", "") or ""
                if gtype in param_child_types:
                    count += 1
            return f"arity:{count}"
    return None


def _extract_definition_signature(def_node, source_bytes: bytes, lang_key: str) -> str | None:
    """Return a per-overload parameter signature for a definition.

    Returns None for languages without overloading or when extraction fails.
    """
    if lang_key not in _OVERLOAD_LANGUAGES:
        return None
    if lang_key == "swift":
        return _swift_param_signature(def_node, source_bytes)
    return _arity_param_signature(def_node, source_bytes, lang_key)


def _swift_call_signature(call_node, source_bytes: bytes) -> str | None:
    """Return Swift call-site argument-label fingerprint.

    Tree-sitter Swift wraps argument labels in a `value_argument_label` node:

        value_argument
          value_argument_label   ← present iff arg has a label
            simple_identifier
          :
          <expression>

    Unlabeled (positional) args have no `value_argument_label` child.
    """
    if call_node is None:
        return None
    value_args = None
    for child in (getattr(call_node, "children", []) or []):
        ctype = getattr(child, "type", "") or ""
        if ctype == "call_suffix":
            for sc in (getattr(child, "children", []) or []):
                if getattr(sc, "type", "") == "value_arguments":
                    value_args = sc
                    break
            if value_args is None:
                value_args = child
            break
        if ctype == "value_arguments":
            value_args = child
            break
    if value_args is None:
        return "()"
    labels: list[str] = []
    any_arg = False
    for child in (getattr(value_args, "children", []) or []):
        ctype = getattr(child, "type", "") or ""
        if ctype != "value_argument":
            continue
        any_arg = True
        label = "_"
        for ac in (getattr(child, "children", []) or []):
            if getattr(ac, "type", "") == "value_argument_label":
                for label_child in (getattr(ac, "children", []) or []):
                    if getattr(label_child, "type", "") in ("simple_identifier", "identifier"):
                        label = source_bytes[label_child.start_byte:label_child.end_byte].decode("utf-8", errors="replace") or "_"
                        break
                break
        labels.append(label)
    if not any_arg:
        return "()"
    return "".join(f"{lbl}:" for lbl in labels)


def _arity_call_signature(call_node, source_bytes: bytes, lang_key: str) -> str | None:
    """Return ``arity:N`` for Java/Kotlin/C#/Scala/C++ call sites."""
    if call_node is None:
        return None
    arg_list_types = {
        "java": ("argument_list",),
        "kotlin": ("value_arguments", "call_suffix"),
        "csharp": ("argument_list",),
        "scala": ("arguments",),
        "cpp": ("argument_list",),
    }.get(lang_key, ())
    arg_child_types = {
        "java": ("expression", "method_invocation", "field_access", "identifier",
                 "decimal_integer_literal", "string_literal", "binary_expression",
                 "null_literal", "true", "false", "lambda_expression", "this",
                 "object_creation_expression", "array_access", "cast_expression",
                 "unary_expression", "ternary_expression", "parenthesized_expression"),
        "kotlin": ("value_argument",),
        "csharp": ("argument",),
        "scala": ("identifier", "integer_literal", "string_literal", "boolean_literal",
                  "call_expression", "field_expression", "infix_expression"),
        "cpp": ("argument", "call_expression", "identifier", "number_literal",
                "string_literal", "binary_expression", "parenthesized_expression",
                "field_expression"),
    }.get(lang_key, ())
    for child in (getattr(call_node, "children", []) or []):
        ctype = getattr(child, "type", "") or ""
        if ctype in arg_list_types:
            # Count the args. For Kotlin/C# we have a wrapper node (value_argument
            # / argument); for Java/Scala/C++ we count any non-trivial child that
            # isn't a comma or paren.
            if lang_key in ("kotlin", "csharp"):
                count = sum(
                    1 for gc in (getattr(child, "children", []) or [])
                    if getattr(gc, "type", "") in arg_child_types
                )
            else:
                # Count all non-punctuation children as args.
                count = sum(
                    1 for gc in (getattr(child, "children", []) or [])
                    if getattr(gc, "type", "") not in ("(", ")", ",", "{", "}")
                    and getattr(gc, "is_named", True)
                )
            return f"arity:{count}"
    return None


def _extract_call_signature(call_node, source_bytes: bytes, lang_key: str) -> str | None:
    """Return a call-site signature derivable from the AST."""
    if lang_key not in _OVERLOAD_LANGUAGES:
        return None
    if lang_key == "swift":
        return _swift_call_signature(call_node, source_bytes)
    return _arity_call_signature(call_node, source_bytes, lang_key)


def _classify_self_edge(
    call_signature: str | None,
    enclosing_signature: str | None,
    overload_signatures: set[str],
) -> str:
    """Classify a self-edge as recursion / overload_forwarding / unknown.

    - call_signature == enclosing_signature → recursion
    - call_signature in (overload_signatures - {enclosing_signature}) → overload_forwarding
    - otherwise → unknown
    """
    if not call_signature or not enclosing_signature:
        return "unknown"
    if call_signature == enclosing_signature:
        return "recursion"
    other_sigs = overload_signatures - {enclosing_signature}
    if call_signature in other_sigs:
        return "overload_forwarding"
    # No overloads registered, or call_signature doesn't match any known overload
    # (same-arity-different-types disambiguation needs type inference).
    if not other_sigs and call_signature != enclosing_signature:
        # Single overload only — anything that doesn't match it is unknown
        # (could be a different-arity call that we mis-counted, or a same-arity
        # different-types case we can't disambiguate without type-checking).
        return "unknown"
    return "unknown"


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
        # Import-only: statement keywords (`import`/`use`/`as`/…) are never import
        # targets, but several (`from`, `require`, `default`) ARE valid method/
        # function names, so the filter must NOT touch call candidates.
        and not (relation == "import" and candidate in _RELATION_KEYWORD_NOISE)
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


# Wave 1p61v: a valid code symbol name is a plain identifier. `function` is a
# fully-reserved word in every C-family / TS / JS grammar, so it can never be a
# real definition name — anonymous `function (…) {}` expressions otherwise
# registered as a junk symbol literally named `function` (teton p60n field trace,
# Issue 2: `function (function)` entry points). Deliberately minimal: contextual
# keywords that ARE legal identifiers (`type`, `async`, `await`, `yield`, `fn`,
# `func`, …) are NOT listed, so no real symbol is ever dropped.
_TS_SYMBOL_NAME_RE = re.compile(r"^[A-Za-z_$][\w$]*$")
_TS_NEVER_SYMBOL_NAMES = frozenset({"function"})


def _ts_is_emittable_symbol_name(name: str, mode: str) -> bool:
    """False when ``name`` is a parser artifact rather than a real symbol.

    Markup / SQL / config names legitimately include dashes, dots, and slashes,
    so only code-mode names are required to be plain identifiers. Catches the
    anonymous-function `function` junk node and non-identifier route-path tokens
    (`/`, `/users`) without rejecting any legal identifier.

    NOTE: the caller gates this to TS/JS only. The plain-identifier rule would
    wrongly reject legitimate non-identifier symbol names in other languages
    (C++ `operator==`, Rust operators, Ruby `valid?`/`save!`/`<=>`), so it must
    not be applied to them.
    """
    if not name:
        return False
    if mode in ("markup", "sql", "config"):
        return True
    simple = name.rsplit(".", 1)[-1]
    if not _TS_SYMBOL_NAME_RE.match(simple):
        return False
    return simple not in _TS_NEVER_SYMBOL_NAMES


def _ts_extract_arrow_const_bindings(node, source_bytes: bytes) -> list[tuple[str, "Any"]]:
    """Extract function names from `const X = (...) => {...}` / `const X = function() {...}` shapes.

    Wave 1p2q3 (1p2tz post-ship per Teton field validation): modern TS code
    extensively uses `export const myFunc = async (args) => { ... }` instead
    of `export function myFunc(args) { ... }`. Tree-sitter parses these as
    ``lexical_declaration → variable_declarator → arrow_function`` rather than
    ``function_declaration``, so the standard name-from-descendants extractor
    finds no identifier at the lexical_declaration level and the symbol never
    registers. This helper walks the lexical_declaration's variable_declarator
    children, returns one (name, declarator_node) per function-bound declarator.

    Returns empty list when ``node`` isn't a lexical_declaration / variable_statement
    or when no child binds a function-shaped expression.
    """
    if node is None:
        return []
    node_type = str(getattr(node, "type", "") or "")
    if node_type not in ("lexical_declaration", "variable_statement", "variable_declaration"):
        return []
    bindings: list[tuple[str, "Any"]] = []
    for child in (getattr(node, "named_children", []) or []):
        if str(getattr(child, "type", "") or "") != "variable_declarator":
            continue
        # Identify the bound name and whether the value is function-shaped.
        decl_children = list(getattr(child, "children", []) or [])
        name = ""
        is_fn_value = False
        for dc in decl_children:
            dctype = str(getattr(dc, "type", "") or "")
            if dctype == "identifier" and not name:
                name = source_bytes[dc.start_byte:dc.end_byte].decode("utf-8", errors="replace").strip()
            elif dctype in ("arrow_function", "function_expression", "function"):
                is_fn_value = True
        if name and is_fn_value:
            bindings.append((name, child))
    return bindings


def _ts_extract_import_module_specifier(import_node, source_bytes: bytes) -> str:
    """Return the raw module-specifier text from a TS/JS import statement.

    Wave 1p2q3 (1p2tz post-ship-3 per Teton field validation): the existing
    `_ts_relation_candidates` path runs every candidate through `_ts_clean_name`
    which strips leading `./` and `../` characters (the regex starts at the
    first identifier character). That's correct for general identifier
    handling but loses the relative-import shape — both `./events` and `events`
    collapse to `"events"` at the call site of `_resolve_ts_import_via_tsconfig`,
    so the resolver can't tell that `./events` should go through the
    relative-path resolver instead of the tsconfig.paths resolver. This helper
    returns the raw specifier (quotes stripped, but `./` preserved) so the
    import handler can branch on the actual import shape.

    Returns empty string when the import has no parseable source field
    (e.g. side-effect-only imports without `from` clause).
    """
    if import_node is None:
        return ""
    # Try the `source` field first (tree-sitter TS exposes it directly on
    # import_statement). Fall back to scanning children for a `string` node.
    src_node = None
    try:
        src_node = import_node.child_by_field_name("source")
    except Exception:
        src_node = None
    if src_node is None:
        for child in (getattr(import_node, "children", []) or []):
            if str(getattr(child, "type", "") or "") == "string":
                src_node = child
                break
    if src_node is None:
        return ""
    text = source_bytes[src_node.start_byte:src_node.end_byte].decode("utf-8", errors="replace").strip()
    # Strip surrounding quotes (single or double or backtick).
    if len(text) >= 2 and text[0] in ("'", '"', "`") and text[0] == text[-1]:
        text = text[1:-1]
    return text


def _ts_extract_imported_names(import_node, source_bytes: bytes) -> list[str]:
    """Return the locally-bound names introduced by a TS/JS import statement.

    Wave 1p2q3 (1p2tf): supports the four shapes consumers care about for
    receiver-type resolution:
      - named:      `import { Foo, Bar } from '@aceiss/lib'` → ['Foo', 'Bar']
      - named alias: `import { Foo as F } from '@aceiss/lib'` → ['F']
      - default:    `import Default from '@aceiss/lib'` → ['Default']
      - namespace:  `import * as Util from '@aceiss/lib'` → ['Util']
      - type-only:  `import type { Foo } from '@aceiss/lib'` → ['Foo']
                    (the `type` keyword sits between `import` and `import_clause`)
    Returns an empty list when no imported names are surfaced (side-effect
    imports like `import './polyfill';`).
    """
    if import_node is None:
        return []
    names: list[str] = []
    for child in (getattr(import_node, "children", []) or []):
        if getattr(child, "type", "") != "import_clause":
            continue
        for clause_child in (getattr(child, "children", []) or []):
            ctype = getattr(clause_child, "type", "") or ""
            if ctype == "identifier":
                # Default import: import_clause contains a direct identifier.
                names.append(
                    source_bytes[clause_child.start_byte:clause_child.end_byte].decode("utf-8", errors="replace")
                )
            elif ctype == "named_imports":
                for spec in (getattr(clause_child, "children", []) or []):
                    if getattr(spec, "type", "") != "import_specifier":
                        continue
                    # When `as` alias is present, the SECOND identifier child is
                    # the local name; otherwise the single identifier IS the
                    # local name. Walk children left-to-right and grab the last
                    # identifier before any non-identifier separator.
                    spec_idents: list[str] = []
                    for sc in (getattr(spec, "children", []) or []):
                        if getattr(sc, "type", "") == "identifier":
                            spec_idents.append(
                                source_bytes[sc.start_byte:sc.end_byte].decode("utf-8", errors="replace")
                            )
                    if spec_idents:
                        names.append(spec_idents[-1])
            elif ctype == "namespace_import":
                for sc in (getattr(clause_child, "children", []) or []):
                    if getattr(sc, "type", "") == "identifier":
                        names.append(
                            source_bytes[sc.start_byte:sc.end_byte].decode("utf-8", errors="replace")
                        )
                        break
    return [n for n in names if n]


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
        state: dict[str, Any] | None = None,
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
        # Wave 1p2q3 (1p2wd post-ship 1.3.28): optional pre-loaded state.
        # Parent loads state from disk once and shares it with worker sessions
        # to avoid 1,542× redundant JSON reads + parses that serialized on the
        # GIL under thread-mode parallel extraction. Teton kernel-sample
        # histogram showed 43% of samples in mutex/condvar waits — classic
        # GIL thrashing where 4 threads serialize on Python work that doesn't
        # release the GIL (state read, JSON parse, dict construction). With
        # state passed in, the worker's __init__ skips _load_state entirely.
        if state is not None:
            self._state = state
        else:
            self._state = self._load_state()
        self._current_paths = {
            _repo_rel(path.relative_to(root)) for path in files
            if path.is_file() and not _is_minified_file(_repo_rel(path.relative_to(root)))
        }
        # Wave 1p2q3 (1p2wd post-ship 1.3.25 / Bug 9): skip `git ls-files` when
        # there are no files to filter. The parallel-extraction workers each
        # construct a fresh `GraphIndexSession` with `files=[]` per task; the
        # resulting `self._current_paths` is also empty, so `set() -= ignored`
        # was a no-op — but the subprocess.run that produced `ignored` still
        # fired on every call. On a 1,542-file workload that's 1,542 git
        # subprocess invocations per build. On macOS spawn-mode workers,
        # `subprocess.Popen.__init__`'s internal `select.poll().poll()` for
        # fork-completion can deadlock when called from inside an already-
        # spawned worker process (Teton field session, stack samples show
        # all 4 workers stuck in this exact poll). The empty-files guard
        # makes the worker path subprocess-free while keeping the
        # parent-thread behavior identical (the parent always has `files`).
        if self._current_paths:
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

        # Wave 131bt (1319o): Python single-dominant-class merge.
        # When a file `foo_bar.py` (or `Foo.py`) has exactly one top-level
        # `class_definition` whose name matches the basename (literal or
        # snake-to-PascalCase), merge the file node and the class node into
        # one node at the file id. Module-level functions/constants don't
        # block the merge.
        _py_basename_raw = ""
        if rel_path.endswith(".py"):
            _py_basename_raw = rel_path.rsplit("/", 1)[-1][:-3]
        _py_basename_candidates: frozenset[str] = (
            frozenset({
                _py_basename_raw,
                "".join(p[:1].upper() + p[1:] for p in _py_basename_raw.split("_") if p),
            })
            if _py_basename_raw
            else frozenset()
        )
        _py_top_level_class_count = sum(
            1 for s in tree.body if isinstance(s, ast.ClassDef)
        )

        def add_symbol(qname: str, kind: str, lineno: int, label: str | None = None, parent: str | None = None, value: str | None = None) -> str:
            # Wave 131bt (1319o): merge top-level class into module node when
            # the dominance gate passes (exactly one top-level class) and the
            # class name matches the file basename (literal or snake-to-Pascal).
            if (
                kind == "class"
                and parent is None
                and _py_top_level_class_count == 1
                and qname in _py_basename_candidates
            ):
                module_node["label"] = qname
                module_node["kind"] = "class"
                module_node["collapsed_pair"] = True
                simple_names.setdefault(qname, []).append(module_id)
                if module_id not in defined_symbols:
                    defined_symbols.append(module_id)
                return module_id
            node_id = f"{rel_path}::{qname}"
            new_node = _node(
                node_id,
                label or qname.split(".")[-1],
                kind,
                rel_path,
                self._source_location(source_text, lineno),
                layer=self.layer,
            )
            if value is not None:  # Wave 1p4ls: constant nodes carry a simple-literal value
                new_node["value"] = value
            nodes.append(new_node)
            edges.append(_edge(module_id, node_id, "defines", confidence="EXTRACTED"))
            defined_symbols.append(node_id)
            base_name = qname.split(".")[-1]
            simple_names.setdefault(base_name, []).append(node_id)
            if parent:
                simple_name_lookup.setdefault(parent, []).append(node_id)
            return node_id

        def emit_py_constant(stmt: "ast.Assign | ast.AnnAssign", parent_qname: str | None) -> None:
            # Wave 1p4ls: a module-/class-level Python constant → a graph node (kind="constant").
            # Reuses the chunk lane's detection predicates (Req-7 — one detector): UPPER_SNAKE name,
            # with typing.Final as a casing-independent override. Function-local assigns never reach
            # here (scope_kind gate); Enum members are skipped (their class body is scope_kind="enum").
            _ck = _chunker_module()
            value_node = stmt.value
            if isinstance(stmt, ast.AnnAssign):
                targets = [stmt.target]
                final_override = _ck._is_final_annotation(stmt.annotation)
            else:
                targets = list(stmt.targets)
                final_override = False
            # value only for a single simple-literal RHS; chained/unpacked targets share or drop it
            literal = _py_const_literal_value(value_node)
            names: list[str] = []
            for tgt in targets:
                if isinstance(tgt, ast.Name):
                    names.append(tgt.id)
                elif isinstance(tgt, (ast.Tuple, ast.List)):
                    names.extend(e.id for e in tgt.elts if isinstance(e, ast.Name))
            tuple_unpack = any(isinstance(t, (ast.Tuple, ast.List)) for t in targets)
            for name in names:
                if not (final_override or _ck._is_const_name(name)):
                    continue
                qname = f"{parent_qname}.{name}" if parent_qname else name
                add_symbol(qname, GRAPH_CONST_KIND, stmt.lineno,
                           value=None if tuple_unpack else literal)

        def collect_imports_and_defs(body: list[ast.stmt], parent_qname: str | None = None, scope_kind: str = "module") -> None:
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
                        collect_imports_and_defs(stmt.body, qname, "function")
                elif isinstance(stmt, ast.ClassDef):
                    qname = f"{parent_qname}.{stmt.name}" if parent_qname else stmt.name
                    add_symbol(qname, "class", stmt.lineno)
                    # Wave 1p4ls: an Enum class body's members are NOT constants (kept as the class
                    # node), mirroring the chunk lane — recurse with scope_kind="enum" to skip them.
                    body_scope = "enum" if _chunker_module()._is_enum_class(stmt) else "class"
                    collect_imports_and_defs(stmt.body, qname, body_scope)
                elif scope_kind in ("module", "class") and isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                    # Wave 1p4ls: module/class-level constant → graph node. Function-local assigns
                    # (scope_kind="function") and Enum members (scope_kind="enum") are excluded.
                    emit_py_constant(stmt, parent_qname)

        collect_imports_and_defs(tree.body)

        # Build a lookup for the exact target node IDs available in this file.
        symbol_lookup = {symbol_id.split("::", 1)[-1]: symbol_id for symbol_id in defined_symbols}
        for name, items in simple_names.items():
            if len(items) == 1:
                symbol_lookup.setdefault(name, items[0])

        # Wave 1p4ls: ids of THIS file's constant nodes — gates reads-edge emission so a `reads`
        # edge only ever binds a constant target (never a coincidental same-name function/class).
        const_ids = {n["id"] for n in nodes if n.get("kind") == GRAPH_CONST_KIND}

        # Wave 131bt (1319q): Python receiver-type resolution via PEP 484
        # type annotations. Extracts simple type names from annotated locals
        # (`foo: Foo = ...`), typed parameters (`def m(self, foo: Foo)`), and
        # routes `foo.method()` calls to `Foo.method`. Unannotated declarations
        # remain unresolved — falls back to the existing EXTRACTED path.
        def _py_extract_simple_type(annotation: ast.AST | None) -> str | None:
            if annotation is None:
                return None
            if isinstance(annotation, ast.Name):
                return annotation.id
            if isinstance(annotation, ast.Subscript):
                # Optional[Foo] / Union[Foo, None] — extract inner non-None.
                if isinstance(annotation.value, ast.Name) and annotation.value.id in ("Optional", "Union"):
                    slice_node = annotation.slice
                    if isinstance(slice_node, ast.Name):
                        return slice_node.id
                    if isinstance(slice_node, ast.Tuple):
                        for elt in slice_node.elts:
                            inner = _py_extract_simple_type(elt)
                            if inner and inner != "None":
                                return inner
                    return _py_extract_simple_type(slice_node)
                # List[Foo] / Container[Foo] / Dict[str, Foo] — outer name (e.g. List).
                if isinstance(annotation.value, ast.Name):
                    return annotation.value.id
            if isinstance(annotation, ast.Attribute):
                # foo.bar.Foo — last segment.
                return annotation.attr
            if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
                # Foo | None → first non-None type
                left = _py_extract_simple_type(annotation.left)
                right = _py_extract_simple_type(annotation.right)
                if left and left != "None":
                    return left
                if right and right != "None":
                    return right
            return None

        # Wave 1p47e (1p470): lazy-loader return-type inference. The wavefoundry
        # sibling-script loader idiom `def _load_X(): return _load_script("mod")`
        # (and direct `v = _load_script("mod")`) returns a *module* object. Without
        # tracking it, `v.Class.method()` / `v.func()` emitted no call edge at all
        # because `v` had no known type — the dominant self-host blast-radius hole
        # (`GraphQueryIndex.from_root` called from 14 sites, 0 incoming edges).
        # `loader_modules` maps a file-local wrapper-function name → module name.
        loader_modules: dict[str, str] = {}
        for _ldr_stmt in tree.body:
            if isinstance(_ldr_stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _eff = [
                    s for s in _ldr_stmt.body
                    if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))
                ]
                if len(_eff) == 1 and isinstance(_eff[0], ast.Return):
                    _ret = _eff[0].value
                    if (
                        isinstance(_ret, ast.Call)
                        and isinstance(_ret.func, ast.Name)
                        and _ret.func.id == "_load_script"
                        and _ret.args
                        and isinstance(_ret.args[0], ast.Constant)
                        and isinstance(_ret.args[0].value, str)
                    ):
                        loader_modules[_ldr_stmt.name] = _ret.args[0].value

        def _py_loader_module(call_node: ast.AST) -> str | None:
            """Module name a sibling-loader call returns, else None (wave 1p470).

            Recognizes `_load_script("mod")` (direct) and `_load_wrapper()` where
            the wrapper's body is `return _load_script("mod")`.
            """
            if isinstance(call_node, ast.Call) and isinstance(call_node.func, ast.Name):
                fn = call_node.func.id
                if (
                    fn == "_load_script"
                    and call_node.args
                    and isinstance(call_node.args[0], ast.Constant)
                    and isinstance(call_node.args[0].value, str)
                ):
                    return call_node.args[0].value
                if fn in loader_modules:
                    return loader_modules[fn]
            return None

        def _py_build_local_types(node: ast.AST, scope_class: str | None) -> dict[str, str]:
            """Build name → type mapping for a function body (one-level scope)."""
            types: dict[str, str] = {}
            # If this is a function, capture typed parameters.
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = node.args
                all_args = list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
                if args.vararg:
                    all_args.append(args.vararg)
                if args.kwarg:
                    all_args.append(args.kwarg)
                for arg in all_args:
                    t = _py_extract_simple_type(getattr(arg, "annotation", None))
                    if t:
                        types[arg.arg] = t
            # Scan body for AnnAssign at this scope level (don't descend into
            # nested functions/classes — they have their own scope).
            body = getattr(node, "body", []) or []
            stack = list(body)
            while stack:
                stmt = stack.pop()
                if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    t = _py_extract_simple_type(stmt.annotation)
                    if t:
                        types[stmt.target.id] = t
                # Descend into compound statements (if/for/while/try/with).
                for field, value in ast.iter_fields(stmt):
                    if isinstance(value, list):
                        stack.extend(v for v in value if isinstance(v, ast.stmt))
                    elif isinstance(value, ast.stmt):
                        stack.append(value)
            return types

        def _py_build_module_vars(node: ast.AST) -> dict[str, str]:
            """Map local var → module name for sibling-loader assignments (1p470).

            Tracks `v = _load_script("mod")` and `v = _load_wrapper()` so
            `v.Class.method()` / `v.func()` resolve to the loaded module's
            symbols. One-level scope, mirrors `_py_build_local_types`.
            """
            mvars: dict[str, str] = {}
            body = getattr(node, "body", []) or []
            stack = list(body)
            while stack:
                stmt = stack.pop()
                if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                if (
                    isinstance(stmt, ast.Assign)
                    and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                ):
                    mod = _py_loader_module(stmt.value)
                    if mod:
                        mvars[stmt.targets[0].id] = mod
                for _field, value in ast.iter_fields(stmt):
                    if isinstance(value, list):
                        stack.extend(v for v in value if isinstance(v, ast.stmt))
                    elif isinstance(value, ast.stmt):
                        stack.append(value)
            return mvars

        class CallCollector(ast.NodeVisitor):
            def __init__(self, current_symbol: str, scope_class: str | None = None, local_types: dict[str, str] | None = None, module_vars: dict[str, str] | None = None, local_names: set[str] | None = None) -> None:
                self.current_symbol = current_symbol
                self.scope_class = scope_class
                self.local_types: dict[str, str] = local_types or {}
                self.module_vars: dict[str, str] = module_vars or {}
                # Wave 1p4ls: names bound locally in this function — a read of one is the local, not
                # a same-name constant (shadowing guard), so it never emits a reads edge.
                self.local_names: set[str] = local_names or set()
                # Wave 131bt (1319q): tuples of (source, target, receiver_resolved).
                self.calls: list[tuple[str, str, bool]] = []
                # Wave 1p4ls: (source, constant_target) reads of a same-file constant.
                self.reads: list[tuple[str, str]] = []

            def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:  # noqa: N802
                return None

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:  # noqa: N802
                return None

            def visit_ClassDef(self, node: ast.ClassDef) -> Any:  # noqa: N802
                return None

            def visit_Call(self, node: ast.Call) -> Any:  # noqa: N802
                target, receiver_resolved = self._resolve_call(node.func)
                if target:
                    self.calls.append((self.current_symbol, target, receiver_resolved))
                self.generic_visit(node)

            def visit_Name(self, node: ast.Name) -> Any:  # noqa: N802
                # Wave 1p4ls: a bare-name READ that resolves to a same-file constant → reads edge.
                if isinstance(node.ctx, ast.Load):
                    self._maybe_read(node.id)
                return None

            def visit_Attribute(self, node: ast.Attribute) -> Any:  # noqa: N802
                # Wave 1p4ls: `Owner.CONST` / `self.CONST` reads of a class constant.
                if isinstance(node.ctx, ast.Load):
                    base = node.value
                    if isinstance(base, ast.Name):
                        if base.id in ("self", "cls") and self.scope_class:
                            self._maybe_read(f"{self.scope_class}.{node.attr}", qualified=True)
                        else:
                            self._maybe_read(f"{base.id}.{node.attr}", qualified=True)
                self.generic_visit(node)

            def _maybe_read(self, name: str, qualified: bool = False) -> None:
                # Faithful: bind ONLY to a same-file constant node, never a local shadow, never a
                # coincidental same-name function/class (symbol_lookup uniqueness + const_ids kind gate).
                if not qualified and name in self.local_names:
                    return
                target = symbol_lookup.get(name)
                if target is None and self.scope_class and not qualified:
                    target = symbol_lookup.get(f"{self.scope_class}.{name}")
                if target is not None and target in const_ids and target != self.current_symbol:
                    self.reads.append((self.current_symbol, target))
                elif target is None and not qualified and name in import_aliases:
                    # Wave 1p4ls: cross-module imported-constant candidate — emit an external::
                    # reads edge; finalize() resolves it to a UNIQUE constant (kind-checked) or
                    # drops it (most imports are functions/classes → dropped; never wrong-bound).
                    self.reads.append((self.current_symbol, f"external::{import_aliases[name]}"))

            def _resolve_call(self, func: ast.AST) -> tuple[str | None, bool]:
                if isinstance(func, ast.Name):
                    name = func.id
                    if name in import_aliases:
                        target_label = import_aliases[name]
                        return f"external::{target_label}", False
                    if name in symbol_lookup:
                        return symbol_lookup[name], False
                    if self.scope_class:
                        candidate = f"{self.scope_class}.{name}"
                        if candidate in symbol_lookup:
                            return symbol_lookup[candidate], False
                    return None, False
                if isinstance(func, ast.Attribute):
                    attr = func.attr
                    value = func.value
                    if isinstance(value, ast.Name):
                        root = value.id
                        if root in ("self", "cls") and self.scope_class:
                            candidate = f"{self.scope_class}.{attr}"
                            if candidate in symbol_lookup:
                                return symbol_lookup[candidate], False
                        # Wave 131bt (1319q): receiver-type via local type
                        # table built from PEP 484 annotations.
                        if root in self.local_types:
                            receiver_type = self.local_types[root]
                            qualified = f"{receiver_type}.{attr}"
                            if qualified in symbol_lookup:
                                return symbol_lookup[qualified], True
                            return f"external::{receiver_type}.{attr}", True
                        # Wave 1p470: sibling-loader module var, e.g.
                        # `gq = _load_graph_query(); gq.some_module_func()`.
                        if root in self.module_vars:
                            return f"external::{self.module_vars[root]}.{attr}", True
                        if root in import_aliases:
                            return f"external::{import_aliases[root]}.{attr}", False
                        if root in symbol_lookup:
                            candidate = f"{root}.{attr}"
                            if candidate in symbol_lookup:
                                return symbol_lookup[candidate], False
                    # Wave 1p470: inline sibling-loader call, e.g.
                    # `_load_graph_query().load_graph()`.
                    if isinstance(value, ast.Call):
                        mod = _py_loader_module(value)
                        if mod:
                            return f"external::{mod}.{attr}", True
                    if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name):
                        root = value.value.id
                        # Wave 1p470: `gq.GraphQueryIndex.from_root()` where gq is a
                        # sibling-loader module var → graph_query.GraphQueryIndex.from_root.
                        if root in self.module_vars:
                            return f"external::{self.module_vars[root]}.{value.attr}.{attr}", True
                        if root in import_aliases:
                            return f"external::{import_aliases[root]}.{value.attr}.{attr}", False
                    # Wave 1p470: inline loader 3-level, e.g.
                    # `_load_graph_query().GraphQueryIndex.from_root()`.
                    if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Call):
                        mod = _py_loader_module(value.value)
                        if mod:
                            return f"external::{mod}.{value.attr}.{attr}", True
                    return None, False
                return None, False

        def collect_calls(body: list[ast.stmt], current_symbol: str, scope_class: str | None = None, owner_node: ast.AST | None = None) -> None:
            # Wave 131bt (1319q): build local type table for receiver-type
            # resolution when an owner function/method is provided.
            local_types: dict[str, str] = {}
            module_vars: dict[str, str] = {}
            local_names: set[str] = set()
            if owner_node is not None:
                local_types = _py_build_local_types(owner_node, scope_class)
                module_vars = _py_build_module_vars(owner_node)
                local_names = _py_local_names(owner_node)
            collector = CallCollector(current_symbol, scope_class=scope_class, local_types=local_types, module_vars=module_vars, local_names=local_names)
            for stmt in body:
                collector.visit(stmt)
                if isinstance(stmt, ast.ClassDef):
                    class_qname = f"{current_symbol.split('::', 1)[-1]}.{stmt.name}" if current_symbol else stmt.name
                    for child in stmt.body:
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            child_symbol = f"{rel_path}::{class_qname}.{child.name}"
                            collect_calls(child.body, child_symbol, scope_class=class_qname, owner_node=child)
                elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_qname = f"{current_symbol.split('::', 1)[-1]}.{stmt.name}" if current_symbol else stmt.name
                    collect_calls(stmt.body, f"{rel_path}::{func_qname}", scope_class=scope_class, owner_node=stmt)
            for src, target, receiver_resolved in collector.calls:
                confidence = "RECEIVER_RESOLVED" if receiver_resolved else "EXTRACTED"
                edges.append(_edge(src, target, "calls", confidence=confidence))
            # Wave 1p4ls: same-file constant reads (deduped per (reader, constant)).
            for src, target in dict.fromkeys(collector.reads):
                edges.append(_edge(src, target, GRAPH_READS_RELATION, confidence="EXTRACTED"))

        # Attach call edges for top-level defs and classes.
        for stmt in tree.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                collect_calls(stmt.body, f"{rel_path}::{stmt.name}", owner_node=stmt)
            elif isinstance(stmt, ast.ClassDef):
                class_qname = stmt.name
                for child in stmt.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        collect_calls(child.body, f"{rel_path}::{class_qname}.{child.name}", scope_class=class_qname, owner_node=child)

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
        source_lines = source_text.splitlines()  # Wave 1p4ls: chunker const predicates need lines
        const_node_ids: set[str] = set()  # Wave 1p4ls: this file's constant node ids (reads gate)
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

        def add_edge(
            source: str,
            target: str,
            relation: str,
            *,
            confidence: str,
            evidence: str | None = None,
            self_edge_kind: str | None = None,
        ) -> None:
            key = (source, target, relation, confidence)
            if key in edge_map:
                return
            edge_map[key] = _edge(
                source,
                target,
                relation,
                confidence=confidence,
                evidence=evidence,
                self_edge_kind=self_edge_kind,
            )

        # Wave 1p2q3 (1p2td): per-overload signature accumulator. Maps qualified
        # node id to the set of parameter signatures observed across all
        # overload definitions sharing that node id (after the per-file merge).
        overload_signatures: dict[str, set[str]] = {}
        # Wave 1p2q3 (1p2tf): per-file imported-name → resolved-target map.
        # Populated during import-edge emission; consulted by the TS/JS
        # receiver-type resolver so aliased cross-package types bind to the
        # resolved project node.
        import_targets: dict[str, str] = {}

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

        # Wave 131bt (1319o): languages that permit multiple top-level classes
        # per file need a dominance gate — merge only fires when the file has
        # exactly one top-level class declaration matching the basename.
        # Without the gate the merge would over-trigger on utility modules
        # containing several classes. Java/C#/Kotlin/Swift/Scala/PHP enforce
        # one-top-level-class-per-file via language convention so don't need
        # the gate.
        _DOMINANCE_GATE_LANGS = frozenset({"python", "javascript", "typescript"})

        # Wave 131bt (1319o): JS/TS support kebab-case file naming
        # convention (`foo-bar.js` containing `class FooBar`). Try kebab->Pascal
        # alongside the literal basename and snake->Pascal.
        _KEBAB_TO_PASCAL_LANGS = frozenset({"javascript", "typescript"})

        def _snake_to_pascal(name: str) -> str:
            if not name:
                return ""
            parts = name.split("_")
            return "".join(p[:1].upper() + p[1:] for p in parts if p)

        def _kebab_to_pascal(name: str) -> str:
            if not name:
                return ""
            parts = name.split("-")
            return "".join(p[:1].upper() + p[1:] for p in parts if p)

        _merge_kinds = _CLASS_MODULE_MERGE_KINDS_BY_LANG.get(lang_key, frozenset())
        _merge_exts = _CLASS_MODULE_MERGE_EXTS_BY_LANG.get(lang_key, ())
        _basename_raw = ""
        for _ext in _merge_exts:
            if rel_path.endswith(_ext):
                _basename_raw = rel_path.rsplit("/", 1)[-1].rsplit(_ext, 1)[0]
                break
        # Build the set of basename candidates the merge gate matches against.
        # For exact-match languages (Swift/Java/Kotlin/C#/Scala/PHP), only the
        # literal basename matches. For snake-to-Pascal languages (Rust/Ruby),
        # the literal basename and snake-to-Pascal conversion match. For JS/TS
        # (wave 131bt 1319o), the literal basename, snake-to-Pascal, AND
        # kebab-to-Pascal all match — JS/TS codebases use all three.
        _file_basename_candidates_set: set[str] = set()
        if _basename_raw:
            _file_basename_candidates_set.add(_basename_raw)
            if lang_key in _SNAKE_TO_PASCAL_LANGS:
                _file_basename_candidates_set.add(_snake_to_pascal(_basename_raw))
            if lang_key in _KEBAB_TO_PASCAL_LANGS:
                _file_basename_candidates_set.add(_kebab_to_pascal(_basename_raw))
                _file_basename_candidates_set.add(_snake_to_pascal(_basename_raw))
        _file_basename_candidates: frozenset[str] = frozenset(_file_basename_candidates_set)

        # Wave 131bt (1319o): pre-count top-level merge-eligible class
        # declarations. Used by the dominance gate for languages permitting
        # multi-class files (Python/JS/TS). Counted via tree-sitter AST walk
        # before walk_definitions; only direct children of the root program
        # node (or export wrappers) count as top-level.
        def _count_top_level_classes() -> int:
            if lang_key not in _DOMINANCE_GATE_LANGS:
                return -1  # Sentinel: gate not applied to this language.
            if not _merge_kinds:
                return -1
            root = tree.root_node
            count = 0
            for child in (getattr(root, "named_children", []) or []):
                ctype = getattr(child, "type", "") or ""
                # Direct top-level class declarations.
                if _ts_is_definition_node(ctype, mode):
                    kind = _ts_kind_for_definition(ctype, None, mode)
                    if kind in _merge_kinds:
                        count += 1
                    continue
                # JS/TS export wrappers — peek inside.
                if lang_key in ("javascript", "typescript") and ctype in (
                    "export_statement", "export_default_declaration"
                ):
                    for inner in (getattr(child, "named_children", []) or []):
                        inner_type = getattr(inner, "type", "") or ""
                        if _ts_is_definition_node(inner_type, mode):
                            inner_kind = _ts_kind_for_definition(inner_type, None, mode)
                            if inner_kind in _merge_kinds:
                                count += 1
            return count

        _top_level_class_count = _count_top_level_classes()

        def register_symbol(qname: str, kind: str, node, parent_symbol: str | None) -> str:
            # Wave 13129 (1316l/13190/1319i/1319k): merge top-level type whose
            # name matches one of the file basename candidates into the module
            # node. Candidates are the literal basename plus (for languages
            # with snake_case file convention like Rust/Ruby) the PascalCase
            # conversion of the basename.
            # Wave 131bt (1319o): dominance gate for multi-class languages.
            # Python/JS/TS permit multiple top-level classes per file; only
            # merge when exactly one such class exists AND its name matches
            # the basename.
            _dominance_gate_passes = (
                lang_key not in _DOMINANCE_GATE_LANGS
                or _top_level_class_count == 1
            )
            if (
                _file_basename_candidates
                and kind in _merge_kinds
                and qname in _file_basename_candidates
                and _dominance_gate_passes
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
            # Wave 1p4ls (delivery review B1): dedup the simple_names append. The constant
            # intercept recurses into a const declaration's OWN name-bearing child (e.g. a
            # Kotlin `const val X` → variable_declaration, an already-registered constant node),
            # which re-registers the SAME node_id here. An unconditional append makes
            # simple_names[X] length 2, so the uniqueness gate below (len == 1) skips X and its
            # same-scope read never resolves — silently producing zero reads edges for every
            # object/companion/class `const val`. Deduping a node_id under its own simple key is
            # always correct (a node appearing twice only inflates the count, never adds info).
            if simple and node_id not in simple_names.setdefault(simple, []):
                simple_names[simple].append(node_id)
            return node_id

        def register_constant(qname: str, node, value: str | None, parent_symbol: str | None) -> str:
            # Wave 1p4ls: a tree-sitter constant node (kind="constant"). Unlike register_symbol it
            # never merges with the file node (a constant is not a file-dominant type) and carries
            # an optional simple-literal value. Registered in defined_symbols/simple_names so reads
            # edges + cross-file resolution see it exactly like a function/class.
            node_id = f"{rel_path}::{qname}"
            add_node(node_id, qname.rsplit(".", 1)[-1], GRAPH_CONST_KIND, self._source_location(source_text, node.start_point[0] + 1))
            if value is not None:
                node_map[node_id]["value"] = value
            add_edge(module_id, node_id, "defines", confidence="EXTRACTED")
            if parent_symbol and parent_symbol != module_id:
                add_edge(parent_symbol, node_id, "defines", confidence="EXTRACTED")
            if node_id not in defined_symbols:
                defined_symbols.append(node_id)
            simple = _simple_name(node_id)
            if simple and node_id not in simple_names.setdefault(simple, []):  # 1p4ls B1: dedup (see register_symbol)
                simple_names[simple].append(node_id)
            return node_id

        # Wave 1p2q3 (1p2tz post-ship-4 perf): single-pass walker. The previous
        # implementation walked the tree twice — once for definitions, once for
        # calls — duplicating tree-traversal overhead. The single-pass walker
        # registers definitions inline (so symbol_lookup can be built immediately
        # after) and buffers call sites; post-walk, a single pass over the
        # buffer resolves and emits call edges using the now-complete symbol
        # table. Reduces walker wall-time ~30-40% on real codebases by avoiding
        # the duplicate AST descent.
        buffered_calls: list[tuple[str, Any, str, list[str]]] = []  # (source_symbol, call_node, node_type, scope_signatures_snapshot)
        buffered_reads: list[tuple[str, str]] = []  # Wave 1p4ls: (reader_symbol, identifier_text)
        func_locals: dict[str, set[str]] = {}  # reader_symbol -> {param/local binding names} (member-access F4 shadow guard)

        def walk_definitions(
            node,
            scope_names: list[str],
            scope_kinds: list[str],
            scope_symbols: list[str],
            scope_signatures: list[str] | None = None,
        ) -> None:
            if scope_signatures is None:
                scope_signatures = []
            node_type = str(getattr(node, "type", "") or "")
            current_scope_kind = scope_kinds[-1] if scope_kinds else None
            # Member-access F4 shadow guard: collect this function's parameter + local binding NAMES.
            # Done BEFORE the is_definition/import branches (which `return`) because some grammars (e.g.
            # Swift `parameter`) ARE definition nodes and would otherwise skip this.
            if current_scope_kind in ("function", "method") and node_type in _TS_BINDING_NODE_TYPES and scope_symbols:
                _bn = _ts_binding_names(node)
                if _bn:
                    func_locals.setdefault(scope_symbols[-1], set()).update(_bn)
            is_import = _ts_markup_import_nodes(node, source_bytes) if mode == "markup" else _ts_is_import_node(node_type, mode)
            is_definition = bool(_ts_markup_name_candidates(node, source_bytes)) if mode == "markup" else _ts_is_definition_node(node_type, mode)
            if is_import:
                source_symbol = scope_symbols[-1] if scope_symbols else module_id
                # Wave 1p4eu (AC-5): Rust `use_declaration` — emit CLEAN dotted
                # import edges (final segment = the imported type name, so
                # `imports_by_file` is consumable) with `as` aliases registered in
                # `import_aliases`, and produce NO keyword-noise edge. The generic
                # relation-candidate fallback below emitted `external::use`/`pub`/
                # `fn`/`as` junk and lossy `::`-paths for Rust; handling the
                # use-tree explicitly and returning skips that path entirely.
                if lang_key == "rust" and node_type == "use_declaration":
                    for _imp_head, _imp_target in _rust_use_imports(node, source_bytes):
                        add_edge(source_symbol, f"external::{_imp_target}", "imports", confidence="EXTRACTED")
                        if _imp_head and _imp_head != _imp_target.rsplit(".", 1)[-1]:
                            import_aliases[_imp_head] = _imp_target
                    return
                # Wave 1p2q3 (1p2tf): extract imported names BEFORE resolving so
                # we can register each name → resolved-target binding for the
                # receiver-type resolver later.
                imported_names: list[str] = []
                # Wave 1p2q3 (1p2tz post-ship-3): raw module specifier (with `./`
                # and `@scope/` prefixes preserved) so the resolver can branch
                # on import shape — `_ts_relation_candidates` clean-names away
                # the relative-path prefix and the tsconfig.paths code can't
                # tell `./events` apart from `events`.
                raw_spec = ""
                if lang_key in ("typescript", "javascript"):
                    imported_names = _ts_extract_imported_names(node, source_bytes)
                    raw_spec = _ts_extract_import_module_specifier(node, source_bytes)
                # Wave 1p4eu: this import node's `as` aliases (`X as W` → {W: X}),
                # computed once — used both to drop the redundant bare-alias-name
                # candidate (the Kotlin `external::W` cosmetic node) and registered
                # in `import_aliases` at the end of the branch.
                _node_aliases = _ts_import_aliases(node, source_bytes, mode)
                _import_candidates = _ts_relation_candidates(node, source_bytes, "import", mode)
                _import_candidate_set = set(_import_candidates)
                for target in _import_candidates:
                    # Skip the bare alias NAME (RHS of `as`) when its real target is
                    # also a candidate: the alias is captured in `import_aliases`, so
                    # an `external::<alias>` edge would be a redundant lossy node.
                    _aliased = _node_aliases.get(target)
                    if _aliased and _aliased != target and _aliased in _import_candidate_set:
                        continue
                    resolved: str | None = None
                    if lang_key in ("typescript", "javascript"):
                        # Wave 1p2q3 (1p2tz post-ship-3): try relative-path
                        # resolution first when the raw specifier starts with
                        # `.` or `/`. Intra-package callers (libs/foo/src/a.ts
                        # importing `./b`) need project-path resolution so
                        # import_targets carries the walked-through definition
                        # file rather than `external::*`. Without this, the
                        # cross-file rewrite pass promotes the edge to the
                        # right target node but keeps it at EXTRACTED.
                        if raw_spec and (raw_spec.startswith(".") or raw_spec.startswith("/")):
                            from_file = self.root / rel_path
                            resolved = _resolve_relative_ts_import(raw_spec, from_file, self.root)
                        else:
                            # Wave 1p2q3 (1p2q9 A): honor tsconfig `paths`
                            # aliases before falling through to external::*.
                            resolved = _resolve_ts_import_via_tsconfig(raw_spec or target, rel_path, self.root)
                    if resolved is None:
                        resolved = _ts_resolve_target(target, {}, import_aliases)
                    add_edge(source_symbol, resolved, "imports", confidence="EXTRACTED")
                    # Wave 1p2q3 (1p2tf): bind each imported name to the
                    # resolved target so the receiver-type resolver can
                    # promote `external::Foo.bar` to a project node when
                    # `Foo` was imported from a tsconfig.paths-aliased lib.
                    # Wave 1p2q3 (1p2tz): when the resolved target is a barrel
                    # re-export (`src/index.ts` patterns), follow the chain so
                    # the binding points at the actual definition file.
                    if lang_key in ("typescript", "javascript") and resolved and not resolved.startswith("external::"):
                        for name in imported_names:
                            walked = _resolve_through_barrel(name, resolved, self.root)
                            import_targets[name] = walked
                    else:
                        for name in imported_names:
                            import_targets[name] = resolved
                import_aliases.update(_node_aliases)
            # Wave 1p2q3 (1p2tz post-ship per Teton field validation): TS/JS
            # arrow-function / function-expression bound to a `const`.
            if lang_key in ("typescript", "javascript"):
                arrow_bindings = _ts_extract_arrow_const_bindings(node, source_bytes)
                if arrow_bindings:
                    for binding_name, declarator_node in arrow_bindings:
                        qname = ".".join([*scope_names, binding_name]) if scope_names else binding_name
                        parent_symbol = scope_symbols[-1] if scope_symbols else module_id
                        node_id = register_symbol(qname, "function", declarator_node, parent_symbol)
                        next_scope_names = [*scope_names, binding_name]
                        next_scope_kinds = [*scope_kinds, "function"]
                        next_scope_symbols = [*scope_symbols, node_id]
                        next_scope_signatures = [*scope_signatures, ""]
                        for child in (getattr(declarator_node, "named_children", []) or []):
                            walk_definitions(child, next_scope_names, next_scope_kinds, next_scope_symbols, next_scope_signatures)
                    return
            # Wave 1p4ls: intercept module-/type-level CONSTANT declarations → kind="constant"
            # per-name (+ simple-literal value), reusing the chunk-lane predicates. Replaces the
            # generic variable/function mislabel for these nodes. Function/method-body locals are
            # never reached (scope gate); a constant node never pushes scope (it is a leaf).
            if mode not in ("markup", "config", "sql") and current_scope_kind not in ("function", "method"):
                _const_decls = _ts_constant_decls(
                    lang_key, node, node_type, source_bytes, source_lines,
                    in_type_body=(current_scope_kind == "class"),
                )
                if _const_decls:
                    _parent_symbol = scope_symbols[-1] if scope_symbols else module_id
                    for _cname, _cvalue in _const_decls:
                        _cqname = ".".join([*scope_names, _cname]) if scope_names else _cname
                        const_node_ids.add(register_constant(_cqname, node, _cvalue, _parent_symbol))
                    # recurse into children WITHOUT pushing scope (initializer calls/reads attribute
                    # to the enclosing scope), then stop — the constant itself is a leaf symbol.
                    for child in getattr(node, "named_children", []):
                        walk_definitions(child, scope_names, scope_kinds, scope_symbols, scope_signatures)
                    return
            if is_definition:
                candidates = _ts_name_candidates(node, source_bytes, mode)
                name = _ts_pick_symbol_name(candidates, mode, node_type)
                # Wave 1p61v: never register a parser-artifact name (the reserved
                # word `function` from an anonymous function expression, or a
                # non-identifier route-path token like `/`). Gated to TS/JS — the
                # artifact is JS/TS-specific, and other languages have legitimate
                # non-identifier symbol names (C++ `operator==`, Rust operators,
                # Ruby `valid?`/`save!`/`<=>`) that this guard must NOT drop.
                _emittable = lang_key not in ("typescript", "javascript") or _ts_is_emittable_symbol_name(name, mode)
                if name and _emittable:
                    # Wave 1p4et: Go methods are top-level `func (r Type) Method()`
                    # — not nested in a class scope — so without this they register
                    # as bare `Method`; the resolver's `Type.method` symbol_lookup
                    # probe always misses and two types with a same-named method
                    # collide to one id. Prepend the receiver type → `Type.Method`.
                    if lang_key == "go" and node_type == "method_declaration" and not scope_names:
                        _recv = _go_method_node_receiver_type(node, source_bytes)
                        if _recv:
                            name = f"{_recv}.{name}"
                    kind = _ts_kind_for_definition(node_type, current_scope_kind, mode)
                    qname = ".".join([*scope_names, name]) if scope_names else name
                    parent_symbol = scope_symbols[-1] if scope_symbols else module_id
                    node_id = register_symbol(qname, kind, node, parent_symbol)
                    # Wave 1p4q4: TS `enum` / `const enum` — each member is a constant NODE
                    # (`Enum.Member`), child of the enum type node (which stays a class node above).
                    # Members are how TS expresses named constants.
                    if lang_key in ("typescript", "javascript") and node_type == "enum_declaration":
                        # The walker does NOT push a scope frame for a TS namespace/module
                        # (internal_module/module aren't definition nodes), so `qname` lacks the
                        # enclosing namespace. Recover it from the AST ancestor chain and prepend it
                        # to the member qname — else two same-named enums in two namespaces collide
                        # to one member node and silently clobber each other's value (review D1).
                        _nsparts: list[str] = []
                        _anc = getattr(node, "parent", None)
                        while _anc is not None:
                            if str(getattr(_anc, "type", "") or "") in ("internal_module", "module"):
                                for _c in getattr(_anc, "children", []):
                                    if str(getattr(_c, "type", "") or "") in ("identifier", "nested_identifier"):
                                        _nsparts.append(_c.text.decode().strip())
                                        break
                            _anc = getattr(_anc, "parent", None)
                        _mem_base = (".".join(reversed(_nsparts)) + "." + qname) if _nsparts else qname
                        for _eb in getattr(node, "named_children", []):
                            if str(getattr(_eb, "type", "") or "") != "enum_body":
                                continue
                            for _mem in getattr(_eb, "named_children", []):
                                _mt = str(getattr(_mem, "type", "") or "")
                                if _mt == "property_identifier":
                                    _mn, _mv = _mem.text.decode().strip(), None
                                elif _mt == "enum_assignment":
                                    _mid = next((g for g in _mem.children
                                                 if str(getattr(g, "type", "") or "") == "property_identifier"), None)
                                    if _mid is None:
                                        continue
                                    _mn, _mv = _mid.text.decode().strip(), _ts_declarator_value(_mem, source_bytes)
                                else:
                                    continue
                                if _mn:
                                    const_node_ids.add(register_constant(f"{_mem_base}.{_mn}", _mem, _mv, node_id))
                    sig = _extract_definition_signature(node, source_bytes, lang_key)
                    if sig:
                        overload_signatures.setdefault(node_id, set()).add(sig)
                    should_push = _ts_is_scope_node(node_type, kind, mode)
                    if mode == "markup":
                        return
                    next_scope_names = [*scope_names, name] if should_push else scope_names
                    next_scope_kinds = [*scope_kinds, kind] if should_push else scope_kinds
                    next_scope_symbols = [*scope_symbols, node_id] if should_push else scope_symbols
                    next_scope_signatures = [*scope_signatures, sig or ""] if should_push else scope_signatures
                    for child in getattr(node, "named_children", []):
                        walk_definitions(child, next_scope_names, next_scope_kinds, next_scope_symbols, next_scope_signatures)
                    return
            if mode == "markup" and (is_import or is_definition):
                return
            # Wave 131bt (1319v): recover ERROR-wrapped top-level class declarations.
            if (
                not scope_names
                and mode not in ("markup", "config", "sql")
                and node_type == "ERROR"
            ):
                recovered = _ts_recover_error_class(node, source_bytes, lang_key)
                if recovered is not None:
                    rname, rkind = recovered
                    rqname = rname
                    rparent = module_id
                    rnode_id = register_symbol(rqname, rkind, node, rparent)
                    next_scope_names = [rname]
                    next_scope_kinds = [rkind]
                    next_scope_symbols = [rnode_id]
                    next_scope_signatures = [""]
                    for child in getattr(node, "named_children", []):
                        walk_definitions(child, next_scope_names, next_scope_kinds, next_scope_symbols, next_scope_signatures)
                    return
            # Wave 1p2q3 (1p2tz post-ship-4 perf): buffer calls for post-walk
            # resolution. We can't emit edges yet because symbol_lookup is built
            # AFTER the walk completes.
            if _ts_is_call_node(node_type, mode, profile):
                source_symbol = scope_symbols[-1] if scope_symbols else module_id
                buffered_calls.append((source_symbol, node, node_type, list(scope_signatures)))
            # Wave 1p4ls: buffer identifier READS inside a function/method body for the `reads`
            # edge. Gated to function scope so class-body const-name identifiers and module noise
            # are not captured; resolved post-walk against the const node set (symbol_lookup
            # uniqueness = cross-module faithfulness; a coincidental twin stays unresolved).
            elif (current_scope_kind in ("function", "method") and node_type in _TS_READ_IDENT_TYPES
                  and scope_symbols and not _ts_is_member_property_leaf(node)):
                # The PROPERTY side of a member access (the trailing `.C`) is skipped here — the
                # member-access path branch below resolves `A.B.C` qualified instead, so a trailing
                # leaf can't wrong-bind a same-named constant when the head is an instance/local.
                try:
                    _ident = source_bytes[node.start_byte:node.end_byte].decode("utf-8", "replace")
                except Exception:
                    _ident = ""
                if _ident:
                    buffered_reads.append((scope_symbols[-1], _ident))
            elif current_scope_kind in ("function", "method") and node_type in _TS_MEMBER_ACCESS_TYPES and scope_symbols:
                # Member-access CONSTANT read: buffer the full qualified PATH (`Status.ACTIVE`,
                # `Outer.Inner.TOKEN`) so it resolves by EXACT qname match against a constant node.
                # This is what surfaces `graph_related.readers` for enum members + nested/type-level
                # constants accessed as `A.B.C` — including TS/JS, whose trailing `property_identifier`
                # the leaf-capture branch above never sees. Faithful by construction: the qualifier is
                # part of the key, so a same-leaf parameter / import / bare call can never match it.
                _mpath = _ts_member_access_path(node, source_bytes)
                if _mpath:
                    buffered_reads.append((scope_symbols[-1], _mpath))
            for child in getattr(node, "named_children", []):
                walk_definitions(child, scope_names, scope_kinds, scope_symbols, scope_signatures)

        walk_definitions(tree.root_node, [], [], [], [])

        symbol_lookup: dict[str, str] = {}
        for symbol_id in defined_symbols:
            symbol_lookup[symbol_id.split("::", 1)[-1]] = symbol_id
        for name, items in simple_names.items():
            if len(items) == 1:
                symbol_lookup.setdefault(name, items[0])

        # Wave 131bt (1319s): symbol kind lookup for scope-aware construction
        # resolution. Maps a simple name to the kind of the symbol it resolves
        # to (e.g. "class", "function") so the construction helper can reject
        # PascalCase callees that resolve to non-class entities.
        symbol_lookup_kinds: dict[str, str] = {}
        for name, node_id in symbol_lookup.items():
            node_info = node_map.get(node_id) or {}
            kind_val = node_info.get("kind") or ""
            if kind_val:
                symbol_lookup_kinds[name] = str(kind_val)

        # Wave 1p2q3 (1p2tz post-ship-4 perf): drain the buffered-call queue
        # using symbol_lookup + symbol_lookup_kinds. This replaces the prior
        # second AST walk (walk_calls) with a flat list traversal. The full
        # call-resolution logic (construction-resolved, per-language receiver-
        # type resolution, self-edge classification, EXTRACTED-with-import-
        # targets-promotion) runs per call exactly as before.
        for _src_symbol, _call_node, _call_node_type, _scope_signatures in buffered_calls:
            source_symbol = _src_symbol
            node = _call_node
            node_type = _call_node_type
            scope_signatures = _scope_signatures
            # Wave 131bt (1319s): construction-call resolution runs FIRST.
            construction_target = _resolve_construction_target(
                node, node_type, source_bytes, symbol_lookup, symbol_lookup_kinds, lang_key
            )
            if construction_target is not None:
                add_edge(source_symbol, construction_target, "calls", confidence="CONSTRUCTION_RESOLVED")
                continue
            # Wave 13129 (1312l + 13194): per-language receiver-type resolution.
            java_resolved_target: str | None = None
            if lang_key == "java" and node_type == "method_invocation":
                java_resolved_target = _resolve_java_call_target(node, source_bytes, symbol_lookup)
            elif lang_key == "kotlin" and node_type == "call_expression":
                java_resolved_target = _resolve_kotlin_call_target(node, source_bytes, symbol_lookup)
            elif lang_key == "csharp" and node_type == "invocation_expression":
                java_resolved_target = _resolve_csharp_call_target(node, source_bytes, symbol_lookup)
            elif lang_key == "go" and node_type == "call_expression":
                java_resolved_target = _resolve_go_call_target(node, source_bytes, symbol_lookup)
            elif lang_key == "rust" and node_type == "call_expression":
                java_resolved_target = _resolve_rust_call_target(node, source_bytes, symbol_lookup)
            elif lang_key == "scala" and node_type == "call_expression":
                java_resolved_target = _resolve_scala_call_target(node, source_bytes, symbol_lookup)
            elif lang_key == "swift" and node_type == "call_expression":
                java_resolved_target = _resolve_swift_call_target(node, source_bytes, symbol_lookup)
            elif lang_key in ("typescript", "javascript") and node_type == "call_expression":
                java_resolved_target = _resolve_ts_call_target(node, source_bytes, symbol_lookup, import_targets)
            elif lang_key == "php" and node_type in ("member_call_expression", "scoped_call_expression"):
                java_resolved_target = _resolve_php_call_target(node, source_bytes, symbol_lookup)
            if java_resolved_target is not None:
                # Wave 1p2q3 (1p2td): classify self-edges on overloadable langs.
                self_kind: str | None = None
                if (
                    lang_key in _OVERLOAD_LANGUAGES
                    and source_symbol == java_resolved_target
                ):
                    call_sig = _extract_call_signature(node, source_bytes, lang_key)
                    enclosing_sig = scope_signatures[-1] if scope_signatures else None
                    sigs_for_node = overload_signatures.get(source_symbol, set())
                    self_kind = _classify_self_edge(call_sig, enclosing_sig, sigs_for_node)
                add_edge(
                    source_symbol, java_resolved_target, "calls",
                    confidence="RECEIVER_RESOLVED", self_edge_kind=self_kind,
                )
            else:
                for target in _ts_relation_candidates(node, source_bytes, "call", mode, profile):
                    resolved = _ts_resolve_target(target, symbol_lookup, import_aliases)
                    # Wave 1p2q3 (1p2tz post-ship): direct-function-call import_targets promotion.
                    confidence_for_edge = "EXTRACTED"
                    if (
                        lang_key in ("typescript", "javascript")
                        and resolved.startswith("external::")
                        and import_targets
                    ):
                        clean_name = _ts_clean_name(target)
                        walked = import_targets.get(clean_name)
                        if walked and not walked.startswith("external::"):
                            resolved = f"{walked}::{clean_name}"
                            confidence_for_edge = "RECEIVER_RESOLVED"
                    # Wave 1p2q3 (1p2tz post-ship-5): TS/JS symbol-table promotion.
                    # When `_ts_resolve_target` bound to a project-internal node
                    # directly (intra-file binding via local symbol_lookup, or
                    # cross-file unambiguous unique simple-name match), the
                    # target is high-confidence — exactly one definition could
                    # have matched. The previous code tagged these as EXTRACTED
                    # which made them invisible to `receiver_resolved` attribution
                    # buckets. The dominant gap on arrow-const-heavy codebases:
                    # `export const foo = () => {}` and a sibling caller `foo()`
                    # in the same file both register, but the call edge landed
                    # EXTRACTED instead of RECEIVER_RESOLVED. Scoped to TS/JS
                    # because other languages already route through their own
                    # receiver resolvers + the cross-file rewrite pass; widening
                    # is a follow-up if field data warrants it.
                    elif (
                        lang_key in ("typescript", "javascript")
                        and resolved
                        and not resolved.startswith("external::")
                    ):
                        confidence_for_edge = "RECEIVER_RESOLVED"
                    self_kind = None
                    if (
                        lang_key in _OVERLOAD_LANGUAGES
                        and source_symbol == resolved
                    ):
                        call_sig = _extract_call_signature(node, source_bytes, lang_key)
                        enclosing_sig = scope_signatures[-1] if scope_signatures else None
                        sigs_for_node = overload_signatures.get(source_symbol, set())
                        self_kind = _classify_self_edge(call_sig, enclosing_sig, sigs_for_node)
                    add_edge(
                        source_symbol, resolved, "calls",
                        confidence=confidence_for_edge, self_edge_kind=self_kind,
                    )


        # Wave 1p2q3 (1p2td): surface per-overload param_signatures on the
        # merged node so consumers can inspect the full overload set directly
        # without re-parsing the source.
        for nid, sigs in overload_signatures.items():
            if nid in node_map and len(sigs) > 0:
                node_map[nid]["param_signatures"] = sorted(sigs)

        # Wave 1p4ls: resolve buffered identifier reads → `reads` edges (reader function → constant).
        # symbol_lookup uniqueness is the cross-module faithfulness gate (an ambiguous same-name
        # constant is absent → stays unresolved, never a wrong twin); const_node_ids restricts the
        # target to constants only (never a coincidental same-name function/class).
        _seen_reads: set[tuple[str, str]] = set()
        for _reader, _ident in buffered_reads:
            if "." in _ident and _ident.split(".", 1)[0] in func_locals.get(_reader, ()):
                continue  # member-access head is a function-local/param shadow → reads the local, not the const (F4)
            _target = symbol_lookup.get(_ident)
            if _target is not None and _target in const_node_ids and _target != _reader:
                # A DOTTED ident is a member-access read (`Outer.Inner.TOKEN`); it must match the
                # constant's FULL qualified name, not a `_simple_name` PARTIAL key (`config.timeout`
                # for a const `Outer.config.timeout`) — else an instance/local `owner.leaf` access
                # wrong-binds a 1-level-nested const (member-access review F1). Bare-leaf reads (no
                # dot) keep the unique-simple-name path unchanged.
                if "." in _ident and _target.split("::", 1)[-1] != _ident:
                    continue
                _key = (_reader, _target)
            elif _target is None and _ident in import_aliases:
                # Wave 1p4ls: cross-module imported-constant candidate — finalize() resolves it to a
                # unique constant (kind-checked) or drops it. Most imports are non-constant → dropped.
                _key = (_reader, f"external::{import_aliases[_ident]}")
            else:
                continue
            if _key in _seen_reads:
                continue
            _seen_reads.add(_key)
            add_edge(_key[0], _key[1], GRAPH_READS_RELATION, confidence="EXTRACTED")

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
        # Wave 1p4eq (1p4ev faithfulness fix): each C# file's DECLARED namespaces,
        # harvested from its namespace nodes (`file.cs::Namespace`, kind="module").
        # The cross-file C# membership disambiguation derives a node's namespace by
        # longest-declared-prefix against this map instead of string-stripping a
        # FIXED two qname segments — which mis-derived the namespace for a caller in
        # a NESTED class (`Acme.Web.Outer.App.Run` → wrongly `Acme.Web.Outer`) and
        # bound the wrong same-name twin (over-resolution caught by verification).
        cs_file_ns: dict[str, set[str]] = {}
        for node_id, node in node_map.items():
            if node_id.startswith("external::"):
                continue  # external endpoint nodes are not project candidates
            if "::" in node_id and node.get("kind") == "module":
                _ns_file = node_id.split("::", 1)[0]
                if _ns_file.endswith(".cs"):
                    cs_file_ns.setdefault(_ns_file, set()).add(node_id.split("::", 1)[1])
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
            else:
                # Wave 1p4ef: collapsed / basename-merged node (no "::" in id —
                # C#/Swift/Rust/Ruby emit one per class file). Its qualified name
                # IS its label (== simple). Without this bind, `qualified` retains
                # the PREVIOUS iteration's value and the dotted-form index below
                # injects a phantom candidate (`{this_module}.{prior_qualified}`)
                # under a key this node has nothing to do with — inflating a
                # genuinely-unique match to len(candidates) > 1 and silently
                # suppressing cross-file resolution.
                qualified = simple
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
        # Wave 1p47e (1p470): per-source-file import map for ambiguous-receiver
        # disambiguation. file -> { imported simple name -> import FQN }. Built
        # from the merged `imports` edges so a call whose receiver type is
        # ambiguous by simple name (multiple same-named project candidates) can
        # be disambiguated by which one the SOURCE FILE actually imported.
        # Language-agnostic: any extractor that emits `imports` edges with FQN
        # targets participates (Python from-imports, Java/Kotlin/C#/Go package
        # imports). On a last-wins collision (a file importing two names with the
        # same final segment), the later import wins — acceptable since the
        # disambiguation still requires a UNIQUE qualified_index match downstream.
        imports_by_file: dict[str, dict[str, str]] = {}
        for (e_src, e_tgt, e_rel, _e_conf) in edge_map.keys():
            if e_rel == "imports" and e_tgt.startswith("external::"):
                fqn = e_tgt[len("external::"):]
                if not fqn:
                    continue
                imports_by_file.setdefault(e_src, {})[fqn.rsplit(".", 1)[-1]] = fqn
        if simple_name_index or qualified_index:
            # Wave 1p2q3 (1p2wd post-ship 1.3.31 perf): rewrite in place
            # rather than building a separate `new_edge_map` and reassigning.
            # On Teton-scale graphs (~77K edges) the old approach allocated a
            # full duplicate dict on every build — net visible in profiling
            # as a measurable share of finalize() wall time. In-place updates
            # collect (old_key, new_key, new_edge) tuples then apply them at
            # the end, so we don't mutate `edge_map` while iterating.
            edge_replacements: list[tuple[tuple, tuple, dict[str, Any]]] = []
            rewrite_count = 0
            for key, edge in edge_map.items():
                src, tgt, rel, conf = key
                if rel != "calls" or not tgt.startswith("external::"):
                    continue
                bare = tgt[len("external::"):]
                if not bare or bare in _TS_GLOBAL_DENYLIST:
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
                # Wave 131bt (1319s): CONSTRUCTION_RESOLVED is a peer to
                # RECEIVER_RESOLVED — both mean the indexer determined the call's
                # target deterministically at graph-build time, so the simple-name
                # fallback must be blocked to prevent phantom rewrites.
                _receiver_resolved = conf in ("RECEIVER_RESOLVED", "CONSTRUCTION_RESOLVED")
                resolved: str | None = None
                # Wave 1p2q3 (1p2tz post-ship-5): track whether the rewrite
                # came from the AC-1 bare-simple-name branch (safe to promote
                # for TS/JS) vs the AC-2 qualified branch (phantom-prone on
                # unannotated locals — must preserve conf).
                rewrote_via_bare_simple = False
                if "." in bare:
                    # AC-2: qualified target — require an exact qualified-name
                    # match to a project node's post-`::` portion. The final
                    # segment must also pass the denylist (so
                    # `external::pathlib.Path` stays external even if some
                    # project file defines `Path`).
                    final_seg = bare.rsplit(".", 1)[-1]
                    if final_seg in _TS_GLOBAL_DENYLIST:
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
                        rewrote_via_bare_simple = True
                # Wave 1p4eq (1p4et faithfulness fix): Go package-qualified
                # receiver. `var h foo.Helper; h.Process()` now keys as
                # `foo.Helper.Process` (the package qualifier is preserved by
                # `_go_simple_type_name`). The qualifier is AUTHORITATIVE: resolve
                # only to a candidate whose package — the Go-convention directory
                # basename — matches `foo`. This recovers the cross-package
                # resolution the bare-name form had, AND prevents the 1p4er
                # same-directory fallback from binding a co-located same-name twin
                # in a DIFFERENT package (the wrong RECEIVER_RESOLVED edge the
                # verification caught). Stays external when no project package
                # matches `foo` (a genuinely external package, or a name collision).
                if (
                    resolved is None
                    and not candidates
                    and bare.count(".") == 2
                    and (src.split("::", 1)[0] if "::" in src else src).endswith(".go")
                ):
                    pkg_head, inner_key = bare.split(".", 1)
                    pkg_matches = []
                    for cand in qualified_index.get(inner_key, []):
                        cfile = cand.split("::", 1)[0]
                        cdir = cfile.rsplit("/", 1)[0] if "/" in cfile else ""
                        cpkg = cdir.rsplit("/", 1)[-1] if cdir else ""
                        if cpkg == pkg_head:
                            pkg_matches.append(cand)
                    if len(pkg_matches) == 1:
                        resolved = pkg_matches[0]
                # Wave 1p47e (1p470): import-edge disambiguation. When the
                # simple/qualified match above was ambiguous (the receiver's
                # name maps to MULTIPLE same-named project candidates), use the
                # SOURCE FILE's `imports` edge for the receiver's head segment to
                # pick the candidate whose defining module matches what the file
                # imported. Filtering the candidate POOL (rather than re-looking-
                # up a constructed FQN) is language-agnostic: it handles both
                # Python (`from src.a import Foo` → file-module `src.a`, FQN
                # `src.a.Foo`) and Java (`import com.foo.Helper` → file-module
                # `com.foo.Helper`, same FQN) by accepting either the FQN itself
                # or its parent module. Only fires when otherwise unresolved, and
                # requires the filter to leave exactly ONE candidate — a
                # genuinely external receiver has no project candidate to match,
                # so it stays external. The `bare`/`final_seg` denylist above
                # still applies (we never reach here for a denied name).
                if resolved is None and len(candidates) > 1:
                    src_file = src.split("::", 1)[0] if "::" in src else src
                    head = bare.split(".", 1)[0]
                    imp_fqn = imports_by_file.get(src_file, {}).get(head)
                    if imp_fqn:
                        accept = {imp_fqn}
                        if "." in imp_fqn:
                            accept.add(imp_fqn.rsplit(".", 1)[0])
                        matches = []
                        for cand in candidates:
                            cfile = cand.split("::", 1)[0]
                            cmod = re.sub(r"\.[A-Za-z0-9]+$", "", cfile).replace("/", ".").lstrip(".")
                            if cmod in accept:
                                matches.append(cand)
                        if len(matches) == 1:
                            resolved = matches[0]
                    # Wave 1p4er: same-package / same-directory fallback. Java/
                    # Kotlin/Go make same-package types visible WITHOUT an import,
                    # so `imports_by_file` has no entry for them and the import path
                    # above cannot fire (the Aceiss `JreCompat.canAccess` field
                    # miss). Resolution order is explicit-import > same-package, so
                    # this runs ONLY after the import path left it unresolved: keep
                    # the ambiguous candidate(s) whose defining file is in the
                    # SOURCE file's own directory; resolve iff exactly one is
                    # co-located (two same-dir twins, or none → stays external).
                    #
                    # Wave 1p4eq (regression fix): GATED to languages where
                    # same-directory ⇒ same-package visibility — Java/Kotlin/Go.
                    # Python/JS/TS/Rust require an EXPLICIT import for a sibling
                    # symbol to be visible, so same-directory co-location confers
                    # nothing there and must not silently resolve (the verification's
                    # regression seat). C# is also excluded: a C# namespace is not
                    # tied to the directory — its membership is handled by the
                    # `.cs`-gated namespace block below (a same-dir C# file can be a
                    # DIFFERENT namespace). For Go, only the UNQUALIFIED receiver
                    # (`Type.method`) reaches here; the package-qualified form is
                    # resolved authoritatively by the Go block above.
                    if resolved is None and src_file.endswith((".java", ".kt", ".kts", ".go")):
                        src_dir = src_file.rsplit("/", 1)[0] if "/" in src_file else ""
                        same_dir = []
                        for cand in candidates:
                            cfile = cand.split("::", 1)[0]
                            cdir = cfile.rsplit("/", 1)[0] if "/" in cfile else ""
                            if cdir == src_dir:
                                same_dir.append(cand)
                        if len(same_dir) == 1:
                            resolved = same_dir[0]
                    # Wave 1p4ev: C# namespace membership. A C# namespace can span
                    # directories (so the same-dir fallback misses it), and cross-
                    # namespace types are brought in by `using`. Keep candidates
                    # whose namespace is the source's OWN namespace or a `using`-
                    # imported one (the `using` FQNs are the values of
                    # imports_by_file; junk heads like `using` never match a real
                    # candidate namespace). Resolve iff exactly one survives —
                    # never the wrong twin (faithfulness).
                    #
                    # Wave 1p4eq (1p4ev faithfulness fix): derive a node's namespace
                    # from its file's DECLARED namespaces (`cs_file_ns`, harvested
                    # from the `file.cs::Namespace` module nodes) by longest-prefix,
                    # NOT by string-stripping a fixed two qname segments. The old
                    # strip mis-derived the namespace for a caller in a NESTED class
                    # — `app/App.cs::Acme.Web.Outer.App.Run` stripped to
                    # `Acme.Web.Outer` instead of the file's real `Acme.Web` — and
                    # bound a sibling twin whose namespace coincided with that
                    # stripped path (a wrong RECEIVER_RESOLVED edge). The declared-
                    # namespace lookup is nesting-proof: `app/App.cs` declares only
                    # `Acme.Web`, so `Run`'s namespace resolves to `Acme.Web`.
                    if resolved is None and src_file.endswith(".cs"):
                        def _cs_ns(nid: str) -> str:
                            f = nid.split("::", 1)[0]
                            qn = nid.split("::", 1)[1] if "::" in nid else ""
                            best = ""
                            for ns in cs_file_ns.get(f, ()):
                                if (qn == ns or qn.startswith(ns + ".")) and len(ns) > len(best):
                                    best = ns
                            return best
                        accept_ns = {_cs_ns(src)} | set(imports_by_file.get(src_file, {}).values())
                        accept_ns.discard("")
                        ns_matches = [c for c in candidates if _cs_ns(c) in accept_ns]
                        if len(ns_matches) == 1:
                            resolved = ns_matches[0]
                if resolved and resolved != src:
                    # Wave 1p2q3 (1p2tz post-ship-5): TS/JS bare-simple-name
                    # promotion. A bare identifier call like `foo()` rewritten
                    # to a project node via `simple_name_index` requires
                    # `len(candidates) == 1` — unambiguous in the project. No
                    # receiver type was assumed; the binding is exact-by-name.
                    # Scoped to TS/JS source files and to the AC-1 branch only:
                    # the AC-2 simple-name fallback (qualified `obj.method()`
                    # without a qualified match) is genuinely a guess about
                    # `obj`'s type and must stay EXTRACTED.
                    promoted_conf = conf
                    if (
                        conf == "EXTRACTED"
                        and rewrote_via_bare_simple
                    ):
                        src_file = src.split("::", 1)[0] if "::" in src else src
                        if src_file and src_file.lower().endswith((".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")):
                            promoted_conf = "RECEIVER_RESOLVED"
                    new_key = (src, resolved, rel, promoted_conf)
                    new_edge = dict(edge)
                    new_edge["target"] = resolved
                    if promoted_conf != conf:
                        new_edge["confidence"] = promoted_conf
                    edge_replacements.append((key, new_key, new_edge))
                    rewrite_count += 1
            # Apply rewrites: pop old keys, insert new ones (collapsing on
            # duplicates — `setdefault` preserves the first-seen edge for the
            # collapsed key, matching the previous behavior).
            for old_key, new_key, new_edge in edge_replacements:
                edge_map.pop(old_key, None)
                edge_map.setdefault(new_key, new_edge)
            if self.verbose and rewrite_count:
                print(
                    f"build_index: graph cross-file resolution rewrote {rewrite_count} external::* edges to project-internal nodes",
                    flush=True,
                )

            # Wave 1p4ls: resolve cross-module IMPORTED constant reads. An `external::` reads edge
            # (a function reading a constant imported from another module) binds ONLY to a UNIQUE
            # constant node — qualified name first, then the final simple-name segment — kind-checked
            # so it never binds a non-constant or a coincidental twin; otherwise the edge is DROPPED
            # (most imports are functions/classes → dropped, never wrong-bound). Faithfulness mirrors
            # the call rewrite's "unique-or-stay-external" discipline, but reads DROP rather than
            # persist an unresolved external:: target (a read of a stdlib/3rd-party value is not a
            # project graph fact).
            reads_replacements: list[tuple[tuple, tuple | None, dict[str, Any] | None]] = []
            for key, edge in edge_map.items():
                src, tgt, rel, conf = key
                if rel != "reads" or not tgt.startswith("external::"):
                    continue
                bare = tgt[len("external::"):]
                target = None
                if bare:
                    # Wave 1p4ls (delivery review B2): bind an imported read ONLY to a UNIQUE
                    # constant matched by the import's QUALIFIED name (the dotted module path and
                    # its suffixes — robust for relative + package imports; see the qualified_index
                    # construction above). The previous simple-name fallback bound a coincidental
                    # same-name constant in an UNRELATED module whenever the qualified import target
                    # was a non-constant project symbol (an imported FUNCTION whose const-kind
                    # filter emptied the qualified match) OR a genuinely 3rd-party module — exactly
                    # the wrong-twin bind the wave's unique-or-DROP faithfulness forbids. A read we
                    # cannot resolve to a UNIQUE qualified project constant is DROPPED, never
                    # guessed from a bare simple name (which is why the legitimate imported-constant
                    # case below still resolves: its dotted module form is a qualified_index key).
                    cands = [c for c in qualified_index.get(bare, [])
                             if (node_map.get(c) or {}).get("kind") == GRAPH_CONST_KIND]
                    if len(cands) == 1 and cands[0] != src:
                        target = cands[0]
                if target is not None:
                    reads_replacements.append((key, (src, target, "reads", conf), {**edge, "target": target}))
                else:
                    reads_replacements.append((key, None, None))  # drop unresolved external read
            for old_key, new_key, new_edge in reads_replacements:
                edge_map.pop(old_key, None)
                if new_key is not None and new_edge is not None:
                    edge_map.setdefault(new_key, new_edge)

        # Prune short internal symbols: drop code symbol nodes with labels ≤
        # _SHORT_SYMBOL_MAX_LEN chars unless some other file imports or calls them.
        # EXEMPT constants (kind=GRAPH_CONST_KIND): an enum member / named const like `Status.OK`
        # or `Dir.Up` (label `OK`/`Up`) is a meaningful value-carrying symbol, not the loop-var /
        # type-param noise this prune targets — and these short names are the wave's own canonical
        # examples. The chunk lane already keeps them (`_go_const_chunk_name`); the graph matches so
        # `code_definition("OK")` resolves (1p4q4 review D2/F1).
        short_symbols: set[str] = {
            node_id
            for node_id, node in node_map.items()
            if "::" in node_id
            and len(str(node.get("label") or "")) <= _SHORT_SYMBOL_MAX_LEN
            and node.get("kind") != GRAPH_CONST_KIND
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


# Wave 1p2q3 (1p2tz post-ship-3 perf): parallel per-file code extraction.
# Threshold-gated so small builds (tests, incremental updates) stay serial
# and don't pay the ProcessPoolExecutor spawn overhead — on macOS each worker
# spawn costs ~500ms–1s for fresh Python import + tree-sitter language load.
# Doc/seed extraction stays serial because it depends on cross-file
# `symbol_terms` built across artifacts; only code-file extraction parallelizes.
_PARALLEL_EXTRACTION_THRESHOLD = int(os.environ.get("WAVEFOUNDRY_GRAPH_PARALLEL_THRESHOLD", "100"))
# Wave 1p2q3 (1p2wd / Bug 4): parallel extraction now uses `spawn` start
# method (default) + a worker `initializer` that registers `graph_indexer`
# in each fresh worker's `sys.modules` before task unpickling. The 1.3.14
# `fork` path deadlocked on macOS after transitive C extension state
# (tree-sitter parsers, possibly objc/Foundation) initialized in the parent;
# spawn boots a clean interpreter per worker and avoids the inheritance
# hazard entirely.
#
# Worker count auto-scales by file count (set in 1.3.20). The 1.3.18→1.3.19
# default of `1` (always-serial) was conservative — small projects don't
# benefit from parallel because spawn boot (~500ms–1s × workers) exceeds
# their per-file work, but Teton-scale builds (1k+ files) leave 2-3× perf
# on the table. The scale tiers reflect break-even math for spawn boot vs.
# parallelizable extraction time:
#   - file_count <  200 → 2 workers (modest projects)
#   - file_count <  500 → 3 workers (medium monorepos)
#   - file_count >= 500 → min(cpu_count, 4) workers (Teton-shape)
# Operators can override the auto-scaled count via
# WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS (any positive int; 1 disables parallel).
# The 100-file threshold for entering the parallel path at all (set by
# WAVEFOUNDRY_GRAPH_PARALLEL_THRESHOLD) is unchanged — auto-scale only
# decides *how many* workers, never *whether* to go parallel.
_PARALLEL_EXTRACTION_WORKERS_OVERRIDE: int | None = (
    int(os.environ["WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS"])
    if "WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS" in os.environ
    else None
)

# Wave 1p2q3 (1p2wd post-ship 1.3.27): parallel-extraction backend selector.
# `threads` (default) uses `ThreadPoolExecutor` — no spawn cost, no IPC, no
# pipe machinery, no orphan workers, no pickle. Tree-sitter releases the GIL
# during parse, so the per-file hot path still parallelizes across cores.
# `processes` uses `ProcessPoolExecutor` with spawn start method + bounded-in-
# flight chunked batches — preserved for benchmarking and for workloads where
# the Python-side walker (GIL-bound) dominates parse time enough that the
# spawn overhead is amortizable. Default flipped to threads in 1.3.27 after
# 1.3.25/1.3.26 field validation on Teton's 1,542-file workload showed
# spawn-mode parallel-4 ran 1.6× slower than serial (44s/45.2s vs. 27.1s) —
# worker boot cost (re-importing tree-sitter etc. per spawn) and per-task
# pickle overhead dominated the actual extraction work.
_PARALLEL_EXTRACTION_BACKEND = os.environ.get(
    "WAVEFOUNDRY_GRAPH_PARALLEL_BACKEND", "processes"
).strip().lower()


_PERF_CORE_COUNT_CACHE: int | None = None


def _physical_perf_core_count() -> int | None:
    """Return performance-core count on macOS (Apple Silicon), or None elsewhere.

    Apple Silicon CPUs are heterogeneous: performance (P) cores run user
    code at full speed; efficiency (E) cores run at roughly 50% throughput
    and consume far less power. `os.cpu_count()` returns the total logical
    count (P + E) and gives no way to distinguish them. Running parallel
    extraction threads on E-cores when P-cores are saturated buys little —
    the bottleneck shifts to E-core throughput and IPC overhead.

    We read `hw.perflevel0.physicalcpu` via `sysctl` to get the actual
    P-core count. Cached at module level (sysctl fork+exec is cheap but
    we only need to ask once). Returns None on Linux/Windows where the
    cores are homogeneous and `os.cpu_count()` is the right answer.
    """
    global _PERF_CORE_COUNT_CACHE
    if _PERF_CORE_COUNT_CACHE is not None:
        return _PERF_CORE_COUNT_CACHE
    if sys.platform != "darwin":
        return None
    try:
        result = subprocess.run(
            ["sysctl", "-n", "hw.perflevel0.physicalcpu"],
            capture_output=True, text=True, timeout=2,
        )
        if result.returncode == 0:
            count = int(result.stdout.strip())
            if count > 0:
                _PERF_CORE_COUNT_CACHE = count
                return count
    except Exception:
        pass
    return None


def _system_cpu_cap() -> int:
    """Cap on parallel worker count based on available CPU resources.

    Prefers macOS P-core count when available — Apple Silicon's E-cores
    run at ~50% throughput and scheduling parallel-extraction workers
    onto them past the P-core ceiling doesn't help. Falls back to
    `cpu_count() // 2` on Linux/Windows, which approximates the physical-
    core count on SMT-enabled CPUs (almost all modern Intel/AMD servers).

    Wave 1p2q3 (1p2wd post-ship 1.3.30): raised to full P-core count after
    Teton field measurement showed process-8 (matching P-core count)
    matches process-6 (P-cores − 2) within noise at the fastest end of
    the curve (15.07s vs. 15.25s, both extraction ~11.4s). With the
    process backend each worker has its own GIL so the "leave headroom
    for main thread" argument that justified `P - 2` under threads
    doesn't carry — workers run independently on dedicated cores and the
    main thread does almost nothing while extraction runs. Operators on
    machines with heavy concurrent workloads can still cap manually via
    `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS=N`.
    """
    p_cores = _physical_perf_core_count()
    if p_cores is not None and p_cores > 0:
        cap = p_cores
    else:
        total = os.cpu_count() or 1
        cap = total // 2
    return max(2, cap)


def _auto_scale_worker_count(file_count: int) -> int:
    """Choose a worker count for parallel extraction.

    Operator's `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS` env var wins
    unconditionally (use `1` to disable parallel without touching the
    threshold env var). When unset, scale by `file_count`.
    """
    if _PARALLEL_EXTRACTION_WORKERS_OVERRIDE is not None:
        return _PARALLEL_EXTRACTION_WORKERS_OVERRIDE
    cpu_cap = _system_cpu_cap()
    if file_count < 200:
        return min(2, cpu_cap)
    if file_count < 500:
        return min(3, cpu_cap)
    return cpu_cap


def _worker_init_graph_indexer(graph_indexer_path: str) -> None:
    """ProcessPoolExecutor initializer for parallel extraction workers.

    Spawn-mode workers (the default since 1.3.19 / wave 1p2q3 / 1p2wd Bug 4)
    boot a fresh Python interpreter with no inherited state from the parent.
    The function reference pickled by `pool.map` resolves to
    ``graph_indexer._extract_artifact_for_worker``; since this file is loaded
    via ``importlib.util.spec_from_file_location`` (not the standard import
    system, because the framework scripts directory is not a package), a
    spawn-mode worker has no way to find the module by name unless we
    register it ourselves.

    This initializer fires once per worker process at startup, *before* the
    first task is dispatched (per the ProcessPoolExecutor contract), and
    loads this same `.py` file under the canonical ``"graph_indexer"`` name
    so subsequent task unpickling finds the function reference.
    """
    import importlib.util as _il_util
    try:
        spec = _il_util.spec_from_file_location("graph_indexer", graph_indexer_path)
        if spec is None or spec.loader is None:
            return
        module = _il_util.module_from_spec(spec)
        sys.modules["graph_indexer"] = module
        spec.loader.exec_module(module)
    except Exception:
        # If the initializer fails the worker will still attempt the task
        # and crash with a clearer ImportError than a deadlock — the parent's
        # `except Exception: ... falling back to serial` branch handles
        # whichever surface the failure takes.
        pass
    # Wave 1p2q3 (1p2wd post-ship 1.3.24 / Bug 7): macOS spawn-mode workers
    # don't self-terminate reliably when the parent dies. `multiprocessing`'s
    # `parent_sentinel` pipe is supposed to signal EOF when the parent exits,
    # but under macOS launchd's re-parenting the pipe can stay open and the
    # worker keeps running forever, idling on `call_queue.get()`. Every
    # killed build then leaks N worker processes plus the resource_tracker.
    # Mitigation: spawn a daemon thread inside each worker that polls
    # `os.getppid()` every 2s and `os._exit(0)`s as soon as the ppid changes
    # (re-parented = orphaned). Daemon thread dies with the worker so it
    # leaves no trace on clean shutdown.
    try:
        import threading as _t
        import time as _time
        import os as _os

        def _ppid_watchdog() -> None:
            try:
                orig_ppid = _os.getppid()
            except Exception:
                return
            while True:
                _time.sleep(2.0)
                try:
                    cur_ppid = _os.getppid()
                except Exception:
                    return
                if cur_ppid != orig_ppid or cur_ppid == 1:
                    try:
                        print(
                            f"build_index: [worker pid={_os.getpid()}] parent died "
                            f"(ppid {orig_ppid} -> {cur_ppid}); exiting",
                            file=sys.stderr, flush=True,
                        )
                    except Exception:
                        pass
                    _os._exit(0)

        _t.Thread(target=_ppid_watchdog, daemon=True, name="ppid-watchdog").start()
    except Exception:
        # Watchdog is best-effort; failure to start it just means the worker
        # falls back to the (broken-on-macOS-spawn) parent_sentinel behavior.
        pass


def _extract_artifacts_for_worker_batch(batch_args: list) -> list:
    """Worker entry point for a BATCH of files.

    Wave 1p2q3 (1p2wd post-ship 1.3.24 / Bug 8): per-task IPC was ~96× the
    cost of chunked IPC (`pool.map(chunksize=96)`); single-file submission
    via the bounded-in-flight pattern in 1.3.23 produced correct results but
    ran ~57× slower than serial on a 1,542-file workload because each file
    incurred a full pickle/unpickle round trip through the multiprocessing
    call queue. This batch entry processes a list of tuples in one IPC
    cycle, amortizing the pipe overhead across the whole batch.
    """
    return [_extract_artifact_for_worker(args) for args in batch_args]


def _extract_artifact_for_worker(args: tuple) -> tuple[str, dict | None]:
    """Worker entry point for parallel code-file extraction.

    Constructs a minimal `GraphIndexSession`, runs `record_file` to extract a
    single file's artifact, and returns `(rel_path, pending_code_entry)`.
    The session is discarded after extraction — only the artifact dict
    crosses the process boundary.

    Module-level (required by `spawn` start method on macOS) and self-
    contained so each worker can be a fresh Python process.
    """
    # Wave 1p2q3 (1p2wd post-ship 1.3.23 / Bug 4 part 3): worker-side
    # breadcrumb that routes through the worker's stderr -> parent's log.
    # If this never prints in a hung field run, workers literally never
    # reach Python code (the deadlock is in `Process.start()` or earlier).
    # Per-worker prints are deduplicated by pid + first-task heuristic
    # because the gate prints once per process-id.
    if os.environ.get("WAVEFOUNDRY_GRAPH_WORKER_TRACE") == "1" or not getattr(_extract_artifact_for_worker, "_logged_boot", False):
        try:
            print(f"build_index: [worker-debug pid={os.getpid()}] _extract_artifact_for_worker called", file=sys.stderr, flush=True)
        except Exception:
            pass
        try:
            _extract_artifact_for_worker._logged_boot = True  # type: ignore[attr-defined]
        except Exception:
            pass
    # Wave 1p2q3 (1p2wd post-ship 1.3.28): worker args include `shared_state`
    # (pre-loaded by parent) and `shared_gitattrs_patterns` so each per-task
    # `GraphIndexSession` construction skips the disk read + JSON parse +
    # gitattrs scan that previously serialized on the GIL across all worker
    # threads. Backwards-compatible: older 7-element tuples still work (the
    # session falls back to its own disk-load path).
    if len(args) >= 9:
        rel_path, source_text, root_str, layer, gitattrs_list, walker_version, chunker_version, shared_state, shared_gitattrs_patterns = args
    else:
        rel_path, source_text, root_str, layer, gitattrs_list, walker_version, chunker_version = args
        shared_state = None
        shared_gitattrs_patterns = None
    # Workers spawned via `spawn` re-import this module fresh; use whichever
    # GraphIndexSession is in the worker's sys.modules (registered by the
    # initializer) to avoid double-loading.
    gi = sys.modules.get("graph_indexer")
    Session = getattr(gi, "GraphIndexSession", GraphIndexSession) if gi is not None else GraphIndexSession
    root = Path(root_str)
    session = Session(
        root=root,
        index_dir=root / ".wavefoundry" / "index",
        layer=layer,
        files=[],
        current_file_meta={},
        walker_version=walker_version,
        chunker_version=chunker_version,
        verbose=False,
        state=shared_state,
    )
    # Pre-set gitattrs patterns so record_file() doesn't trigger another
    # disk read + scan on the worker's first code-file classification.
    if shared_gitattrs_patterns is not None:
        session._gitattrs_patterns = shared_gitattrs_patterns
    else:
        session._gitattrs_patterns = frozenset(gitattrs_list)
    session.record_file(rel_path, source_text)
    return rel_path, session.pending_code.get(rel_path)


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
    # Wave 1p2q3 (1p2tz post-ship-3 perf): the lru caches on path resolvers
    # (`_probe_ts_alias_target_cached`, `_resolve_relative_ts_import_cached`)
    # and the per-file declared-names cache are NOT cleared per-build by
    # design. Within a build they turn repeated lookups into O(1) hits; across
    # builds the LRU eviction policy + mtime-keyed dict (for declared-names)
    # handle staleness naturally. The cost of clearing per build dominated
    # wall-time on small-build test workloads where each test made a tiny
    # build call, with negligible benefit on real workloads where rebuilds
    # are infrequent. Stale-result risk is low: deleted files don't appear
    # in the per-build file list so they're not extracted regardless of
    # cached probe results.
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
    # Wave 1p2q3 (1p2tz post-ship-3 perf): bucket files by kind so code-file
    # extraction can parallelize; doc/seed stays serial (cross-file symbol
    # dependency makes it sequential by nature).
    #
    # Wave 1p2q3 (1p2wd post-ship 1.3.31 perf): parallelize the read loop with
    # a `ThreadPoolExecutor`. `Path.read_text` releases the GIL during the
    # syscall, so multiple threads issue concurrent reads to the page cache.
    # On SSD this cuts the parent's pre-extraction stage by ~1-2s on Teton-
    # scale (1,500+ file) workloads. Bucketing into code / doc lists stays
    # serial (and trivially fast) because it only inspects `rel` and the
    # cached `kind`. Below the parallel-extraction file-count threshold
    # the read overhead is small enough that the serial path is fine.
    code_work_items: list[tuple[str, str]] = []  # (rel_path, source_text)
    doc_work_items: list[tuple[str, str]] = []   # (rel_path, source_text)

    def _read_one(file_path: "Path") -> tuple[str, str, str] | None:
        rel = _repo_rel(file_path.relative_to(root))
        if rel not in changed_set:
            return None
        if _is_minified_file(rel):
            return None
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        return (rel, text, _kind_for_path(rel))

    if len(files) >= _PARALLEL_EXTRACTION_THRESHOLD:
        # Worker count for file reads: tuned smaller than extraction since
        # this is purely I/O-bound and the page cache saturates quickly.
        # Use `min(cpu_count, 8)` capped at the file count so we don't spawn
        # more threads than there's work for.
        from concurrent.futures import ThreadPoolExecutor as _TPool
        _read_workers = max(2, min(8, len(files), os.cpu_count() or 4))
        with _TPool(max_workers=_read_workers, thread_name_prefix="wavefoundry-read") as _pool:
            for result in _pool.map(_read_one, files):
                if result is None:
                    continue
                rel, text, kind = result
                if kind == "code":
                    code_work_items.append((rel, text))
                else:
                    doc_work_items.append((rel, text))
    else:
        for file_path in files:
            result = _read_one(file_path)
            if result is None:
                continue
            rel, text, kind = result
            if kind == "code":
                code_work_items.append((rel, text))
            else:
                doc_work_items.append((rel, text))

    worker_count = _auto_scale_worker_count(len(code_work_items))
    use_parallel = (
        worker_count > 1
        and len(code_work_items) >= _PARALLEL_EXTRACTION_THRESHOLD
    )
    if use_parallel:
        # Pre-load gitattrs once in the parent; pass to workers.
        if session._gitattrs_patterns is None:
            session._gitattrs_patterns = _load_gitattributes_generated_paths(root)
        gitattrs_list = list(session._gitattrs_patterns)
        backend = _PARALLEL_EXTRACTION_BACKEND if _PARALLEL_EXTRACTION_BACKEND in ("threads", "processes") else "threads"
        if verbose:
            print(
                f"build_index: graph extraction parallel — "
                f"{worker_count} {backend}, "
                f"{len(code_work_items)} code files (threshold "
                f"{_PARALLEL_EXTRACTION_THRESHOLD})",
                flush=True,
            )

        def _pdbg(msg: str) -> None:
            if verbose:
                try:
                    import threading as _t
                    thread_names = sorted(t.name for t in _t.enumerate())
                    thread_suffix = f" [threads={len(thread_names)}: {','.join(thread_names[:6])}{'...' if len(thread_names) > 6 else ''}]"
                except Exception:
                    thread_suffix = ""
                print(f"build_index: [parallel-debug] {msg}{thread_suffix}", flush=True)

        # Wave 1p2q3 (1p2wd post-ship 1.3.28): pass parent's pre-loaded state
        # and gitattrs patterns to every worker. With threads this is a free
        # reference share; with processes it's a per-task pickle cost the
        # operator accepts when opting into the process backend. Eliminates
        # 1,542× redundant `_load_state()` JSON parses + `.gitattributes`
        # disk reads that serialized on the GIL under thread parallelism
        # (Teton kernel-sample histogram: 43% of samples in mutex/condvar
        # waits, classic GIL thrashing from sequential Python work).
        _shared_state = session._state
        _shared_gitattrs = session._gitattrs_patterns or frozenset()
        worker_args = [
            (rel, text, str(root), layer, gitattrs_list, walker_version, chunker_version, _shared_state, _shared_gitattrs)
            for rel, text in code_work_items
        ]

        if backend == "threads":
            # Wave 1p2q3 (1p2wd post-ship 1.3.27 / Bug 4 finale): thread backend.
            # Process-mode parallel-4 ran 1.6× SLOWER than serial on Teton's
            # 1,542-file workload across both batch=24 (44.0s) and batch=128
            # (45.2s) — disproving the IPC-amortization hypothesis. The
            # dominant overhead was spawn-mode worker boot (each worker re-
            # imports tree-sitter from scratch) plus per-task pickle. Threads
            # eliminate both: shared interpreter state means tree-sitter loads
            # once in the parent; result return is a direct Python reference
            # with no pickle. Tree-sitter parsers release the GIL during
            # parse, so the per-file hot path still parallelizes across cores.
            # Theoretical ceiling ~1.3-1.5× over serial; we expect to actually
            # hit something close to that since the IPC cost we'd been
            # paying with processes is now ~zero.
            from concurrent.futures import ThreadPoolExecutor
            _pdbg(f"thread backend: constructing ThreadPoolExecutor (max_workers={worker_count})")
            try:
                with ThreadPoolExecutor(
                    max_workers=worker_count,
                    thread_name_prefix="wavefoundry-extract",
                ) as pool:
                    _pdbg("pool entered; iterating pool.map")
                    _seen = 0
                    for rel_path, entry in pool.map(_extract_artifact_for_worker, worker_args):
                        _seen += 1
                        if _seen == 1:
                            _pdbg(f"first task returned: rel_path={rel_path!r}")
                        elif _seen % 250 == 0:
                            _pdbg(f"progress: {_seen}/{len(worker_args)} tasks returned")
                        if entry is not None:
                            session.pending_code[rel_path] = entry
                    _pdbg(f"pool drained: {_seen} task results consumed")
            except Exception as exc:
                if verbose:
                    print(
                        f"build_index: parallel extraction (threads) failed "
                        f"({type(exc).__name__}: {exc}); falling back to serial",
                        flush=True,
                    )
                for rel, text in code_work_items:
                    session.record_file(rel, text)
        else:
            # Process-mode backend (opt-in via WAVEFOUNDRY_GRAPH_PARALLEL_BACKEND=processes).
            # Kept for benchmarking and for any workload where the Python-side
            # walker (GIL-bound) dominates parse time enough that spawn overhead
            # amortizes. The chunked-bounded-in-flight + spawn-mode + sys.path
            # mutation + worker initializer + per-task git-subprocess gating
            # all stay in place. See full root-cause analysis in
            # `docs/waves/1p2q3 field-feedback-round-4/1p2wd-bug parallel-
            # extraction-fork-deadlock-spawn-mode-fix.md`.
            _pdbg("step 1/8: worker_args built (process backend)")
            from concurrent.futures import ProcessPoolExecutor
            import multiprocessing as _mp
            chunksize = max(1, len(worker_args) // (worker_count * 4))
            start_method = os.environ.get("WAVEFOUNDRY_GRAPH_PARALLEL_START_METHOD", "spawn")
            _pdbg(f"step 4/8: getting mp context for start_method={start_method!r} (chunksize={chunksize})")
            try:
                mp_ctx = _mp.get_context(start_method)
            except (ValueError, RuntimeError):
                mp_ctx = None
            _pdbg(f"step 5/8: mp_ctx acquired ({type(mp_ctx).__name__ if mp_ctx is not None else 'None'})")
            graph_indexer_path = str(Path(__file__).resolve())
            graph_indexer_dir = str(Path(graph_indexer_path).parent)
            path_inserted = False
            if graph_indexer_dir not in sys.path:
                sys.path.insert(0, graph_indexer_dir)
                path_inserted = True
            _pdbg(f"step 6/8: sys.path[0]={sys.path[0]!r} (path_inserted={path_inserted})")
            try:
                if mp_ctx is None:
                    for rel, text in code_work_items:
                        session.record_file(rel, text)
                else:
                    try:
                        _pdbg(
                            f"step 7/8: constructing ProcessPoolExecutor "
                            f"(max_workers={worker_count}, initializer=_worker_init_graph_indexer)"
                        )
                        from concurrent.futures import wait as _wait, FIRST_COMPLETED
                        batch_size = max(1, min(128, len(worker_args) // (worker_count * 3)))
                        batches = [
                            worker_args[i:i + batch_size]
                            for i in range(0, len(worker_args), batch_size)
                        ]
                        _pdbg(f"batched {len(worker_args)} tasks into {len(batches)} batches of up to {batch_size}")
                        with ProcessPoolExecutor(
                            max_workers=worker_count,
                            mp_context=mp_ctx,
                            initializer=_worker_init_graph_indexer,
                            initargs=(graph_indexer_path,),
                        ) as pool:
                            _pdbg("step 8/8: pool entered; about to bounded-in-flight submit batches (workers will spawn on first submit)")
                            batch_iter = iter(batches)
                            in_flight: set = set()
                            for _ in range(worker_count):
                                try:
                                    next_batch = next(batch_iter)
                                except StopIteration:
                                    break
                                in_flight.add(pool.submit(_extract_artifacts_for_worker_batch, next_batch))
                            _pdbg(f"pre-warm: submitted {len(in_flight)} batches (one per worker); waiting for first result")
                            _seen = 0
                            while in_flight:
                                done, in_flight = _wait(in_flight, return_when=FIRST_COMPLETED)
                                for fut in done:
                                    batch_results = fut.result()
                                    for rel_path, entry in batch_results:
                                        _seen += 1
                                        if _seen == 1:
                                            _pdbg(f"first task returned: rel_path={rel_path!r} (workers confirmed spawned)")
                                        elif _seen % 250 == 0:
                                            _pdbg(f"progress: {_seen}/{len(worker_args)} tasks returned")
                                        if entry is not None:
                                            session.pending_code[rel_path] = entry
                                    try:
                                        next_batch = next(batch_iter)
                                        in_flight.add(pool.submit(_extract_artifacts_for_worker_batch, next_batch))
                                    except StopIteration:
                                        pass
                            _pdbg(f"pool drained: {_seen} task results consumed")
                    except Exception as exc:
                        if verbose:
                            print(
                                f"build_index: parallel extraction failed "
                                f"({type(exc).__name__}: {exc}); falling back to serial",
                                flush=True,
                            )
                        for rel, text in code_work_items:
                            session.record_file(rel, text)
            finally:
                if path_inserted:
                    try:
                        sys.path.remove(graph_indexer_dir)
                    except ValueError:
                        pass
    else:
        for rel, text in code_work_items:
            session.record_file(rel, text)

    # Doc/seed files always sequential (need cross-file symbol_terms).
    for rel, text in doc_work_items:
        session.record_file(rel, text)

    payload = session.finalize()
    if verbose:
        counts = payload.get("counts") or {}
        print(
            f"build_index: graph extraction wrote {layer} graph — "
            f"{counts.get('nodes', 0)} nodes, {counts.get('edges', 0)} edges",
            flush=True,
        )
    # Wave 1p2q3 (1p2tf): Nx project-structure detection — diagnostic only this
    # round. Presence at repo root surfaces in the payload so consumers can
    # report a per-build hint when investigating low TS receiver-resolved rates.
    try:
        if (root / "nx.json").is_file():
            payload["nx_project_detected"] = True
    except OSError:
        pass
    return payload


def read_graph_payload(root: Path, layer: str = "project") -> dict[str, Any]:
    # Wave 1p4ww: single project graph — the framework graph layer was removed.
    if layer not in GRAPH_FILENAMES:
        raise ValueError(f"Unsupported graph layer: {layer}")
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
