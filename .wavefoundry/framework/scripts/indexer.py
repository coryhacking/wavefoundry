#!/usr/bin/env python3
"""Build and maintain the Wavefoundry semantic index at .wavefoundry/index/."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

sys.dont_write_bytecode = True

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

INDEX_DIR_NAME = ".wavefoundry/index"
META_JSON = "meta.json"
TABLE_LOCK_NAME = ".lock"   # written inside docs.lance/ and code.lance/
LOCK_STALE_SECONDS = 60 * 60

DOCS_MODEL = "BAAI/bge-small-en-v1.5"
CODE_MODEL = "BAAI/bge-small-en-v1.5"

# Instruction prefixes required by asymmetric embedding models.
# Values include a trailing space so that `prefix + text` produces correctly
# formatted input (e.g. "search_document: " + passage_text).
# Empty strings mean no prefix (symmetric models such as bge-base).
EMBEDDING_PREFIXES: dict[str, dict[str, str]] = {
    "nomic-ai/nomic-embed-text-v1.5-Q": {
        "document": "search_document: ",
        "query": "search_query: ",
    },
    "BAAI/bge-base-en-v1.5": {
        "document": "",
        "query": "",
    },
    "BAAI/bge-small-en-v1.5": {
        "document": "",
        "query": "",
    },
    "jinaai/jina-embeddings-v2-base-code": {
        "document": "",
        "query": "",
    },
    "jinaai/jina-embeddings-v2-small-en": {
        "document": "",
        "query": "",
    },
}

# LanceDB vector index constants
# Tables are stored directly inside the index directory (e.g. .wavefoundry/index/docs.lance/).
LANCEDB_INDEX_THRESHOLD = 1000   # rows; below: flat scan; at/above: IVF_HNSW_SQ index
LANCEDB_COMPACT_THRESHOLD = 20   # fragment count threshold; triggers optimize() after add/delete
EMBED_BATCH_SIZE = 256           # chunks per embedding batch
SORT_WINDOW_SIZE = 2048          # sliding sort buffer size (8× EMBED_BATCH_SIZE)
LANCEDB_NPROBES = 20             # ANN search probes (recall vs latency)
LANCEDB_REFINE_FACTOR = 10       # reranking candidates multiplier
RERANKER_MODEL = "BAAI/bge-reranker-base"
CONTENT_CHOICES = ("docs", "code", "all")
SOURCE_CODE_EXTENSIONS = {
    ".py",
    ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs",
    ".go", ".rs", ".java", ".kt", ".swift", ".c", ".cpp", ".h", ".hpp",
    ".cs", ".rb", ".php", ".sh", ".bash", ".zsh", ".fish",
    ".yaml", ".yml", ".toml", ".json", ".jsonc",
    ".html", ".css", ".scss", ".sass",
    ".xml", ".graphql", ".gql", ".proto", ".sql",
    ".psql", ".pgsql", ".ddl", ".dml", ".tsql", ".hql",
    ".ps1", ".psm1",
    ".bat", ".cmd",
    ".tf", ".tfvars", ".hcl",
    ".tpl",
}

# Extensionless filenames treated as documentation (routed to chunk_plain_text in chunker).
# Keep in sync with chunker.py:DOCS_EXTENSIONLESS_NAMES.
DOCS_EXTENSIONLESS_NAMES = {"README", "LICENSE", "CHANGELOG", "CONTRIBUTING", "NOTICE"}

# Extensionless filenames treated as code (routed to chunk_line_window in chunker).
# Keep in sync with chunker.py:CODE_EXTENSIONLESS_NAMES.
CODE_EXTENSIONLESS_NAMES = {
    "Jenkinsfile", "Makefile", "Dockerfile", "Vagrantfile", "Brewfile",
    "Fastfile", "Appfile", "Podfile", "Gemfile", "Procfile",
}

# Plain-text extensions indexed as documentation (not code).
DOCS_TEXT_EXTENSIONS = {".txt"}
GENERATED_CODE_PREFIXES = (
    ".claude/hooks/",
    ".cursor/hooks/",
    ".github/hooks/",
    ".windsurf/",
)
FRAMEWORK_TEST_PREFIXES = (
    ".wavefoundry/framework/scripts/tests/",
)
FRAMEWORK_PACK_ARTIFACT_NAMES = {"MANIFEST", "VERSION"}
FRAMEWORK_PACK_ARTIFACT_PREFIXES = ("MANIFEST.pre-",)
# Dev-only framework paths not shipped in the distribution zip.
# These are excluded from framework/index/ so wave_index_build and build_pack
# always produce the same file set — eliminating the dev/pack index conflict.
# These files remain indexed in .wavefoundry/index/ (project layer).
FRAMEWORK_DEV_ONLY_PREFIXES = (
    ".wavefoundry/framework/scripts/benchmarks/",
)
FRAMEWORK_DEV_ONLY_EXACT_PATHS = frozenset({
    ".wavefoundry/framework/scripts/run_tests.py",
    ".wavefoundry/framework/test-cache.json",
})
TEST_DIR_NAMES = {"test", "tests", "__tests__"}

# Directories and patterns always excluded regardless of .gitignore/.aiignore
# Single directory names excluded wherever they appear in the path tree.
HARDCODED_EXCLUDE_DIRS = {
    ".git", ".hg", ".svn",
    "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".tox", ".venv", "venv", ".env", "env",
    "dist", "build", "target", "out", ".next", ".nuxt",
}

# Path prefixes (relative to repo root, forward slashes) that are always excluded.
HARDCODED_EXCLUDE_PREFIXES = (
    ".wavefoundry/index/",
    ".wavefoundry/framework/index/",
    ".wavefoundry/logs/",
)
HARDCODED_EXCLUDE_PATHS = frozenset({
    ".wavefoundry/dashboard-server.json",
    ".wavefoundry/guard-overrides.json",
})
PROJECT_INDEX_EXCLUDE_PREFIXES = (
    ".wavefoundry/framework/",
    ".wavefoundry/logs/",
)

BINARY_EXTENSIONS = frozenset({
    # Compiled / native
    ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe", ".bin", ".a", ".o", ".elf",
    # Archives
    ".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar",
    # Office / presentation
    ".pdf", ".pptx", ".docx", ".xlsx", ".xls", ".ppt", ".doc",
    # Images
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".ico", ".webp", ".tiff", ".tif",
    # Vector / design — SVG excluded from code index (no code semantics)
    ".svg", ".eps", ".ai", ".sketch", ".acorn",
    # Fonts
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    # Media
    ".mp3", ".mp4", ".wav", ".ogg", ".avi", ".mov", ".mkv", ".flv",
    # Data / ML artifacts
    ".npy", ".npz", ".pkl", ".parquet", ".h5", ".hdf5",
    # Databases / locks
    ".db", ".sqlite", ".lock",
    # Installers / packages
    ".dmg", ".pkg", ".msi", ".deb", ".rpm",
})

# Exact filenames excluded regardless of extension (generated/machine-written files).
HARDCODED_EXCLUDE_FILENAMES = frozenset({
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "prompt-surface-manifest.json",  # machine-generated metadata artifact, not useful for search
})

# Extensions for machine-generated files that are valid text but have no code semantics.
_GENERATED_EXCLUDE_EXTENSIONS = frozenset({
    ".snap",        # Vitest / Jest snapshot files
    ".excalidraw",  # Excalidraw diagram JSON
})

# All extensions we treat as known text — no null-byte sniff needed.
_KNOWN_TEXT_EXTENSIONS = frozenset(SOURCE_CODE_EXTENSIONS) | {
    ".md", ".markdown",
    ".txt",
    ".graphql", ".gql", ".proto",
    ".psql", ".pgsql", ".ddl", ".dml", ".tsql", ".hql",
    ".tf", ".tfvars", ".hcl", ".tpl",
    ".ps1", ".psm1",
    ".bat", ".cmd",
}

# Dot-directories that are always excluded from the walk.
# The blanket rule (name starts with ".") handles new tools automatically;
# only paths under .wavefoundry/ are permitted through the dot-dir filter.
_DOT_DIR_ALLOWLIST = ".wavefoundry"
_DOT_DIR_ALLOWLIST_PREFIX = ".wavefoundry/"

# Bump when walk_repo() filter logic changes (binary exclusions, generated file exclusions,
# null-byte/magic-byte sniff changes). A version mismatch forces a full rebuild so that
# files newly excluded by the filter are removed from existing indexes automatically.
WALKER_VERSION = "5"

# Environment variable used by the MCP server to tell the background indexer
# which state file to remove once the process exits.
INDEX_BUILD_STATE_PATH_ENV = "WAVEFOUNDRY_INDEX_BUILD_STATE_PATH"

# ---------------------------------------------------------------------------
# Ignore file parsing
# ---------------------------------------------------------------------------

def _load_ignore_patterns(root: Path) -> list[str]:
    patterns: list[str] = []
    for name in (".gitignore", ".aiignore"):
        p = root / name
        if p.is_file():
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
    return patterns


def _matches_ignore(rel_path: str, patterns: list[str]) -> bool:
    """Simple gitignore-style pattern matching (covers common cases)."""
    import fnmatch
    parts = rel_path.replace("\\", "/").split("/")
    for pattern in patterns:
        pattern = pattern.rstrip("/")
        # Directory-only pattern (ends with /) already stripped above
        if fnmatch.fnmatch(parts[-1], pattern):
            return True
        if fnmatch.fnmatch(rel_path.replace("\\", "/"), pattern):
            return True
        # Match any path component
        for part in parts[:-1]:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False


# ---------------------------------------------------------------------------
# File walker
# ---------------------------------------------------------------------------

def walk_repo(root: Path, *, respect_ignore: bool = True) -> list[Path]:
    """Return all indexable files under root, respecting ignore rules."""
    ignore_patterns = _load_ignore_patterns(root) if respect_ignore else []
    result: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(root):
        dir_path = Path(dirpath)
        try:
            rel_dir = dir_path.relative_to(root)
        except ValueError:
            continue

        dirnames.sort()
        filenames.sort()

        rel_dir_str = str(rel_dir).replace("\\", "/")
        keep_dirnames: list[str] = []
        for dirname in dirnames:
            if dirname in HARDCODED_EXCLUDE_DIRS:
                continue
            child_rel = dirname if rel_dir_str == "." else f"{rel_dir_str}/{dirname}"
            if not (
                child_rel == _DOT_DIR_ALLOWLIST
                or child_rel.startswith(_DOT_DIR_ALLOWLIST_PREFIX)
            ) and dirname.startswith("."):
                continue
            keep_dirnames.append(dirname)
        dirnames[:] = keep_dirnames

        for filename in filenames:
            path = dir_path / filename
            if not path.is_file():
                continue

            try:
                rel = path.relative_to(root)
            except ValueError:
                continue

            rel_str = str(rel).replace("\\", "/")

            if rel_str in HARDCODED_EXCLUDE_PATHS:
                continue

            # Check hardcoded prefix excludes
            if any(rel_str.startswith(prefix) for prefix in HARDCODED_EXCLUDE_PREFIXES):
                continue

            parts = rel_str.split("/")

            # Blanket dot-dir exclusion: skip any path component that starts with "."
            # unless the entire prefix starts with the .wavefoundry allowlist.
            if not rel_str.startswith(_DOT_DIR_ALLOWLIST_PREFIX):
                if any(part.startswith(".") for part in parts[:-1]):
                    continue

            # Check remaining hardcoded dir-name excludes (non-dot dirs like node_modules).
            # Only check directory components (parts[:-1]) so filenames like ".env" aren't
            # blocked by the ".env" virtualenv dir entry.
            if any(part in HARDCODED_EXCLUDE_DIRS for part in parts[:-1]):
                continue

            filename = parts[-1]
            suffix = path.suffix.lower()

            # .env files: allow through — chunker redacts all values, indexes variable names only.
            # Must be checked before the gitignore check and binary sniff since .env has no
            # recognised extension and is typically listed in .gitignore.
            if filename == ".env" or (filename.startswith(".env.") and len(filename) > 5):
                result.append(path)
                continue

            # Exact-filename exclusions (generated lock files)
            if filename in HARDCODED_EXCLUDE_FILENAMES:
                continue

            # Binary extensions
            if suffix in BINARY_EXTENSIONS:
                continue

            # Generated-file extension exclusions (snapshots, diagrams)
            if suffix in _GENERATED_EXCLUDE_EXTENSIONS:
                continue

            # Allow extensionless docs files (README, LICENSE, etc.) before extension check
            if not path.suffix and filename in DOCS_EXTENSIONLESS_NAMES:
                result.append(path)
                continue

            # Allow extensionless code files (Jenkinsfile, Makefile, etc.) before extension check
            if not path.suffix and filename in CODE_EXTENSIONLESS_NAMES:
                result.append(path)
                continue

            # Binary sniff for extensionless files and files with unrecognized extensions.
            # Checks magic-byte signatures first (ELF, Mach-O, PE, class files), then falls
            # back to a null-byte scan which catches most binary formats not covered above.
            if not suffix or suffix not in _KNOWN_TEXT_EXTENSIONS:
                try:
                    header = path.read_bytes()[:8192]
                    if (
                        header[:4] == b"\x7fELF"           # ELF (Linux/ARM executables)
                        or header[:4] in (b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf",
                                          b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe")  # Mach-O
                        or header[:2] == b"MZ"             # PE/COFF (.exe, .dll)
                        or header[:4] == b"\xca\xfe\xba\xbe"  # Java .class / fat Mach-O
                        or b"\x00" in header
                    ):
                        continue
                except OSError:
                    continue

            # .gitignore / .aiignore
            if _matches_ignore(rel_str, ignore_patterns):
                continue

            result.append(path)

    return sorted(result)


# ---------------------------------------------------------------------------
# Hashing and stat-cache change detection
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _build_file_hashes(files: list[Path], root: Path) -> dict[str, str]:
    """Return {relative_path: sha256_hex} for every file in *files*."""
    return {str(f.relative_to(root)).replace("\\", "/"): _sha256(f) for f in files}


def _stat_entry(path: Path) -> tuple[float, int, int]:
    """Return (mtime, size, inode) for a file.

    inode is 0 on Windows/FAT where st_ino is unsupported; callers treat 0 as
    "don't use inode in cache comparison".
    """
    st = path.stat()
    return (st.st_mtime, st.st_size, st.st_ino)


def _stat_matches(old: dict, mtime: float, size: int, inode: int) -> bool:
    """True if stored stat entry matches current stat — no read needed."""
    if old.get("mtime") != mtime or old.get("size") != size:
        return False
    # If inodes are available on this filesystem, also check inode
    old_ino = old.get("inode", 0)
    if inode and old_ino and inode != old_ino:
        return False
    return True


def _detect_changes(
    files: list[Path],
    root: Path,
    old_meta: dict[str, dict],
) -> tuple[dict[str, dict], set[str], set[str]]:
    """Return (current_file_meta, changed_paths, removed_paths).

    Uses mtime+size+inode as a cheap pre-filter: only files whose stat differs
    from stored values are read and hashed. Files that pass the stat check are
    treated as unchanged without any file I/O.

    old_meta maps rel_path -> {"hash": str, "mtime": float, "size": int, "inode": int}.
    """
    current: dict[str, dict] = {}
    changed: set[str] = set()

    for f in files:
        rel = str(f.relative_to(root)).replace("\\", "/")
        mtime, size, inode = _stat_entry(f)
        old = old_meta.get(rel)

        # Cache hit: stat matches — skip read entirely
        if old is not None and isinstance(old, dict) and _stat_matches(old, mtime, size, inode):
            current[rel] = old
            continue

        # Cache miss: read and hash
        digest = _sha256(f)
        entry: dict = {"hash": digest, "mtime": mtime, "size": size, "inode": inode}
        current[rel] = entry

        # Changed if hash differs from stored (or no prior entry)
        old_hash = old.get("hash") if old is not None else None
        if old_hash != digest:
            changed.add(rel)

    removed = set(old_meta.keys()) - set(current.keys())
    return current, changed, removed



def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _filter_by_prefixes(files: list[Path], root: Path, prefixes: tuple[str, ...]) -> list[Path]:
    if not prefixes:
        return files
    normalized = tuple(prefix.strip("/").replace("\\", "/") for prefix in prefixes)
    return [
        path for path in files
        if any(
            str(path.relative_to(root)).replace("\\", "/").startswith(prefix + "/")
            or str(path.relative_to(root)).replace("\\", "/") == prefix
            for prefix in normalized
        )
    ]


def _filter_project_index_excludes(
    files: list[Path],
    root: Path,
    include_prefixes: tuple[str, ...],
    *,
    project_include_prefixes: tuple[str, ...] = (),
) -> list[Path]:
    """Exclude framework source from the default project-local index layer."""
    if include_prefixes:
        return files
    normalized_includes = tuple(
        prefix.strip("/").replace("\\", "/")
        for prefix in project_include_prefixes
        if prefix.strip()
    )

    def _allowed_by_project_include_prefixes(rel_path: str) -> bool:
        return any(rel_path == prefix or rel_path.startswith(prefix + "/") for prefix in normalized_includes)

    return [
        path for path in files
        if _allowed_by_project_include_prefixes(str(path.relative_to(root)).replace("\\", "/"))
        or not any(
            str(path.relative_to(root)).replace("\\", "/").startswith(prefix)
            for prefix in PROJECT_INDEX_EXCLUDE_PREFIXES
        )
    ]


def _filter_framework_pack_artifacts(files: list[Path], root: Path) -> list[Path]:
    """Exclude packaging artifacts and dev-only files from the framework layer index.

    Keeps framework/index/ in sync with the distribution zip file set so that
    wave_index_build and build_pack never fight over different file sets.
    Dev-only files remain indexed in .wavefoundry/index/ (project layer).
    """
    filtered: list[Path] = []
    for path in files:
        rel = str(path.relative_to(root)).replace("\\", "/")
        name = path.name
        if name in FRAMEWORK_PACK_ARTIFACT_NAMES:
            continue
        if any(name.startswith(prefix) for prefix in FRAMEWORK_PACK_ARTIFACT_PREFIXES):
            continue
        if _is_framework_test_path(rel):
            continue
        if rel.startswith(FRAMEWORK_DEV_ONLY_PREFIXES):
            continue
        if rel in FRAMEWORK_DEV_ONLY_EXACT_PATHS:
            continue
        filtered.append(path)
    return filtered


def _normalize_prefixes(prefixes: tuple[str, ...]) -> tuple[str, ...]:
    normalized: list[str] = []
    for raw in prefixes:
        token = raw.strip().replace("\\", "/").strip("/")
        if token and token not in normalized:
            normalized.append(token)
    return tuple(normalized)


def _content_project_include_prefixes(
    content: str,
    configured_prefixes: tuple[str, ...],
) -> tuple[str, ...]:
    if not configured_prefixes:
        return ()
    if content not in CONTENT_CHOICES:
        return ()
    return _normalize_prefixes(configured_prefixes)


def _is_generated_code_path(rel_path: str) -> bool:
    return rel_path.startswith(GENERATED_CODE_PREFIXES)


def _is_test_code_path(rel_path: str) -> bool:
    parts = rel_path.split("/")
    if any(part in TEST_DIR_NAMES for part in parts[:-1]):
        return True
    filename = parts[-1]
    return filename.startswith("test_") or filename.endswith("_test.py")


def _is_framework_test_path(rel_path: str) -> bool:
    return rel_path.startswith(FRAMEWORK_TEST_PREFIXES)


def _filter_code_files(
    files: list[Path],
    root: Path,
    *,
    include_tests: bool,
    include_generated: bool,
) -> list[Path]:
    result: list[Path] = []
    for path in files:
        rel = str(path.relative_to(root)).replace("\\", "/")
        if path.suffix.lower() not in SOURCE_CODE_EXTENSIONS:
            continue
        if _is_framework_test_path(rel):
            continue
        if not include_generated and _is_generated_code_path(rel):
            continue
        if not include_tests and _is_test_code_path(rel):
            continue
        result.append(path)
    return result


# ---------------------------------------------------------------------------
# Meta I/O
# ---------------------------------------------------------------------------

def _load_meta(index_dir: Path) -> dict:
    meta_path = index_dir / META_JSON
    if meta_path.is_file():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_meta(index_dir: Path, meta: dict) -> None:
    _atomic_write_text(index_dir / META_JSON, json.dumps(meta, indent=2))


# ---------------------------------------------------------------------------
# Atomic file write helper
# ---------------------------------------------------------------------------

def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# LanceDB vector index helpers
# ---------------------------------------------------------------------------

def _auto_install_lancedb() -> None:
    """Install lancedb automatically when missing, mirroring setup_index.py install behaviour."""
    print("build_index: lancedb not installed — installing automatically ...", flush=True)
    cmd = [sys.executable, "-m", "pip", "install", "lancedb"]
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        # Retry with --break-system-packages for Homebrew / externally-managed envs (PEP 668).
        result = subprocess.run(cmd + ["--break-system-packages"], check=False)
    if result.returncode != 0:
        raise ImportError(
            "lancedb auto-install failed. "
            "Run manually: python3 .wavefoundry/framework/scripts/setup_index.py"
        )
    print("build_index: lancedb installed successfully.", flush=True)


def _get_lance_db(db_path: Path):
    try:
        import lancedb
    except ImportError:
        _auto_install_lancedb()
        import lancedb  # retry after install
    db_path.mkdir(parents=True, exist_ok=True)
    return lancedb.connect(str(db_path))


def _stream_embed_write(
    db,
    table_name: str,
    chunks: list[dict],
    embedder,
    label: str,
    verbose: bool = False,
) -> int:
    """Embed *chunks* in sliding-sort-buffer batches and write incrementally to *db*.

    Uses a SORT_WINDOW_SIZE-chunk buffer sorted by text length so each
    EMBED_BATCH_SIZE batch draws the shortest available sequences, minimising
    ONNX padding waste without buffering the full corpus in memory.

    Returns the number of rows written (== len(chunks)).
    """
    total = len(chunks)
    if total == 0:
        return 0

    # Initialise the sliding buffer with the first SORT_WINDOW_SIZE chunks.
    buf_end = min(SORT_WINDOW_SIZE, total)
    buffer: list[dict] = sorted(chunks[:buf_end], key=lambda c: len(c["text"]))
    read_pos: int = buf_end
    table = None
    written = 0

    while buffer:
        # Pop the EMBED_BATCH_SIZE shortest chunks from the sorted buffer.
        batch_chunks = buffer[:EMBED_BATCH_SIZE]
        buffer = buffer[EMBED_BATCH_SIZE:]

        # Refill from the remaining corpus and re-sort.
        refill_end = min(read_pos + EMBED_BATCH_SIZE, total)
        if read_pos < total:
            buffer.extend(chunks[read_pos:refill_end])
            read_pos = refill_end
            buffer.sort(key=lambda c: len(c["text"]))

        start = written + 1
        end = written + len(batch_chunks)
        # Always log per-batch progress — this is the primary status signal during
        # a long rebuild and should appear in index-build.log regardless of --verbose.
        print(f"build_index: embedding {label} chunks {start}–{end}/{total}", flush=True)

        vecs = _embed_texts(embedder, [c["text"] for c in batch_chunks], batch_size=EMBED_BATCH_SIZE)
        rows = _make_lance_rows(batch_chunks, vecs)

        if table is None:
            table = db.create_table(table_name, data=rows, mode="overwrite")
        else:
            table.add(rows)

        written += len(batch_chunks)

    if table is None:
        return 0

    # Create vector and FTS indexes once, after all rows are written.
    if written >= LANCEDB_INDEX_THRESHOLD:
        try:
            table.create_index(metric="cosine", index_type="IVF_HNSW_SQ", replace=True)
            if verbose:
                print(
                    f"build_index: LanceDB IVF_HNSW_SQ index created for '{table_name}' ({written} rows)",
                    flush=True,
                )
        except Exception as exc:
            print(
                f"build_index: LanceDB index creation for '{table_name}' skipped ({exc})",
                file=sys.stderr,
            )

    _create_fts_index(table, table_name, replace=False)

    return written


def _optimize_lance_table(table) -> None:
    """Compact a LanceDB table, swallowing errors (advisory)."""
    try:
        from datetime import timedelta
        table.optimize(cleanup_older_than=timedelta(seconds=0))
    except Exception as exc:
        print(f"build_index: LanceDB optimize failed ({exc})", file=sys.stderr)


def _create_fts_index(table, table_name: str, replace: bool = False) -> None:
    """Create (or rebuild) a lance-index full-text search index on the 'text' column.

    ``replace=True`` should be used after incremental writes so that newly
    added rows are included in the FTS index.  ``optimize()`` alone does NOT
    refresh Tantivy indexes; an explicit rebuild is required.

    Tokenizer: ``simple`` (splits on whitespace and punctuation) with stemming
    and stop-word removal disabled and ``max_token_length=80``.

    Why ``simple``:  punctuation like ``.`` and ``(`` acts as a token boundary,
    so ``build_pack.version`` indexes as ``build_pack`` and ``version`` — both
    independently searchable.  ``whitespace`` would keep the whole dotted string
    as one token (bad for component matching); ``raw`` treats the entire text as
    a single token (useless for search).

    Why ``stem=False, remove_stop_words=False``:  stemming mangles identifiers
    (``chunks`` → ``chunk``); stop-word removal silently drops name components
    like ``is`` or ``a`` that legitimately appear in variable names.
    ``lower_case=True`` preserves case-insensitive query matching.

    Note: underscores are punctuation under ``simple``, so compound identifiers
    (``SORT_WINDOW_SIZE``) are indexed as individual tokens (``sort``, ``window``,
    ``size``).  The dense retrieval path compensates: exact identifier queries
    that produce noisy BM25 hits are rescored by the cross-encoder reranker.
    """
    try:
        table.create_fts_index(
            "text",
            replace=replace,
            base_tokenizer="simple",
            stem=False,
            remove_stop_words=False,
            lower_case=True,
            max_token_length=80,
            with_position=True,
        )
    except Exception as exc:
        print(
            f"build_index: FTS index creation for '{table_name}' skipped ({exc})",
            file=sys.stderr,
        )


def _lance_fragment_count(table) -> int:
    """Best-effort fragment count; returns 0 on failure."""
    try:
        stats = table.stats()
        if isinstance(stats, dict):
            return int(stats.get("num_fragments", 0))
    except Exception:
        pass
    try:
        return len(table.list_versions())
    except Exception:
        pass
    return 0


def _update_lance_table(db_path: Path, table_name: str, file_path: str, new_rows: list) -> None:
    """Delete existing rows for file_path and add new_rows; compact if needed."""
    db = _get_lance_db(db_path)
    table = db.open_table(table_name)
    safe_path = file_path.replace("'", "''")
    table.delete(f"path = '{safe_path}'")
    if new_rows:
        table.add(new_rows)
    if _lance_fragment_count(table) > LANCEDB_COMPACT_THRESHOLD:
        _optimize_lance_table(table)


def _delete_lance_chunks(db_path: Path, table_name: str, file_path: str) -> None:
    """Delete all rows for file_path from a LanceDB table; compact if needed."""
    db = _get_lance_db(db_path)
    table = db.open_table(table_name)
    safe_path = file_path.replace("'", "''")
    table.delete(f"path = '{safe_path}'")
    if _lance_fragment_count(table) > LANCEDB_COMPACT_THRESHOLD:
        _optimize_lance_table(table)


def _make_lance_rows(chunks: list[dict], vecs: "np.ndarray") -> list[dict]:
    """Convert chunk dicts + vector array into LanceDB row dicts."""
    rows = []
    for chunk, vec in zip(chunks, vecs):
        row = dict(chunk)
        if isinstance(row.get("tags"), list):
            row["tags"] = " ".join(str(t) for t in row["tags"])
        # Normalize nullable string fields to "" so LanceDB always sees a non-null
        # string column type. If the first batch is all-None (e.g. Markdown-only),
        # LanceDB infers the column as Null; a later batch with a real string value
        # then raises: ValueError: cannot cast field 'language' from Utf8 to Null.
        for _nullable_str in ("language", "section"):
            if row.get(_nullable_str) is None:
                row[_nullable_str] = ""
        row["vector"] = vec.tolist()
        rows.append(row)
    return rows


def _count_chunks_for_paths(db_path: Path, table_name: str, paths: set[str]) -> int:
    """Return the number of existing chunks in table_name belonging to the given paths."""
    if not paths or not (db_path / f"{table_name}.lance").is_dir():
        return 0
    try:
        db = _get_lance_db(db_path)
        table = db.open_table(table_name)
        escaped = [p.replace("'", "''") for p in paths]
        in_clause = ", ".join(f"'{p}'" for p in escaped)
        return table.search().where(f"path IN ({in_clause})", prefilter=True).limit(None).to_pandas().shape[0]
    except Exception:
        return 0


def _lance_incremental_write(
    db_path: Path,
    stale: set[str],
    new_doc_chunks: list[dict],
    new_doc_vecs: "Optional[np.ndarray]",
    new_code_chunks: list[dict],
    new_code_vecs: "Optional[np.ndarray]",
    build_docs: bool,
    build_code: bool,
    verbose: bool = False,
) -> None:
    """Delete stale rows and add new rows to existing Lance tables."""
    db = _get_lance_db(db_path)
    for table_name, build_flag, chunks, vecs in (
        ("docs", build_docs, new_doc_chunks, new_doc_vecs),
        ("code", build_code, new_code_chunks, new_code_vecs),
    ):
        if not build_flag:
            continue
        table_dir = db_path / f"{table_name}.lance"
        with _table_lock(table_dir):
            if not table_dir.is_dir():
                # Table absent — create with new rows only (shouldn't happen after upgrade guard).
                if chunks and vecs is not None:
                    tbl = db.create_table(table_name, data=_make_lance_rows(chunks, vecs), mode="create")
                    _create_fts_index(tbl, table_name, replace=False)
                continue
            table = db.open_table(table_name)
            for file_path in stale:
                safe_path = file_path.replace("'", "''")
                table.delete(f"path = '{safe_path}'")
            if chunks and vecs is not None:
                table.add(_make_lance_rows(chunks, vecs))
            if _lance_fragment_count(table) > LANCEDB_COMPACT_THRESHOLD:
                _optimize_lance_table(table)
            _create_fts_index(table, table_name, replace=True)


@contextmanager
def _table_lock(table_dir: Path, *, create_dir: bool = False):
    """Acquire a per-table build lock at ``table_dir/.lock``.

    ``table_dir`` is the Lance table directory (e.g. ``index_dir/docs.lance``).
    Set ``create_dir=True`` for the full-rebuild path where the directory may not
    exist yet.  The incremental path should leave it False so that the caller's
    "table absent" guard still fires when the Lance dir is missing.

    The lock file contains the owning process PID; its mtime is used by server.py
    to detect stale locks older than LOCK_STALE_SECONDS.  Using ``O_CREAT | O_EXCL``
    provides the same atomic-create guarantee as ``mkdir()`` on POSIX.
    Readers see ``docs.lance/.lock`` only while their specific table is being
    written — the other table remains unlocked and fully readable.
    """
    if create_dir:
        table_dir.mkdir(parents=True, exist_ok=True)
    lock_path = table_dir / TABLE_LOCK_NAME
    # If the table directory doesn't exist and create_dir wasn't requested, skip locking —
    # the caller's "table absent" guard will handle this case.
    if not table_dir.exists():
        yield
        return
    acquired = False
    while not acquired:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, str(os.getpid()).encode())
            finally:
                os.close(fd)
            acquired = True
        except FileExistsError:
            try:
                age = time.time() - lock_path.stat().st_mtime
            except OSError:
                age = 0
            if age > LOCK_STALE_SECONDS:
                lock_path.unlink(missing_ok=True)
                continue
            time.sleep(0.2)
    try:
        yield
    finally:
        lock_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def _onnx_providers() -> list[str]:
    """Return the best available ONNX Runtime execution providers for this machine."""
    try:
        import onnxruntime as _ort
        available = set(_ort.get_available_providers())
    except Exception:
        return ["CPUExecutionProvider"]
    # CoreMLExecutionProvider is intentionally excluded: it is a no-op for INT8
    # ONNX models (ANE can't run INT8 ops) and actively hurts FP32 models by
    # fragmenting execution across ANE/CPU boundaries. Revisit when a proper
    # coremltools-converted .mlpackage is available.
    if "CUDAExecutionProvider" in available:
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    return ["CPUExecutionProvider"]


def _get_embedder(model_name: str):
    """Return a fastembed TextEmbedding instance for model_name."""
    try:
        from fastembed import TextEmbedding
    except ImportError:
        print(
            "build_index: fastembed is not installed.\n"
            "  Run: python3 .wavefoundry/framework/scripts/setup_index.py",
            file=sys.stderr,
        )
        sys.exit(1)
    return TextEmbedding(model_name=model_name, providers=_onnx_providers())


def _embed_texts(embedder, texts: list[str], batch_size: int = 256) -> "np.ndarray":
    """Embed a list of texts and return as a float32 numpy array (n, dim).

    Callers are responsible for pre-sorting inputs by text length for padding
    efficiency (ONNX pads every sequence in a batch to the longest). The full
    rebuild path uses a sliding sort buffer; the incremental path sorts per-file.
    """
    import numpy as _np
    return _np.array(
        list(embedder.embed(texts, batch_size=batch_size)),
        dtype=_np.float32,
    )


def _progress(verbose: bool, message: str) -> None:
    if verbose:
        print(message, flush=True)


# ---------------------------------------------------------------------------
# Index build helpers
# ---------------------------------------------------------------------------

def _is_docs_kind(kind: str) -> bool:
    return kind in ("doc", "seed", "prompt", "doc-summary")


# We cache the chunker module after first load
_chunker_mod = None

def _get_chunker():
    global _chunker_mod
    if _chunker_mod is None:
        import importlib.util
        chunker_path = Path(__file__).resolve().parent / "chunker.py"
        spec = importlib.util.spec_from_file_location("chunker", chunker_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["chunker"] = mod
        spec.loader.exec_module(mod)
        _chunker_mod = mod
    return _chunker_mod


def _chunks_for_file(rel_path: str, content: str) -> tuple[list[dict], list[dict]]:
    chunker = _get_chunker()
    raw = chunker.chunk_file(content, rel_path)
    doc_chunks = [c.to_dict() for c in raw if _is_docs_kind(c.kind)]
    code_chunks = [c.to_dict() for c in raw if not _is_docs_kind(c.kind)]
    return doc_chunks, code_chunks


# ---------------------------------------------------------------------------
# Core build logic
# ---------------------------------------------------------------------------

def build_index(
    root: Path,
    *,
    full: bool = False,
    content: str = "docs",
    index_dir: Optional[Path] = None,
    include_prefixes: tuple[str, ...] = (),
    respect_ignore: bool = True,
    include_tests: bool = False,
    include_generated: bool = False,
    project_include_prefixes: tuple[str, ...] = (),
    files: Optional[list[Path]] = None,
    verbose: bool = False,
    dry_run: bool = False,
) -> dict:
    index_dir = index_dir or (root / INDEX_DIR_NAME)
    if not index_dir.is_absolute():
        index_dir = root / index_dir
    index_dir.mkdir(parents=True, exist_ok=True)
    if dry_run:
        return _build_index_locked(
            root,
            full=full,
            content=content,
            index_dir=index_dir,
            include_prefixes=include_prefixes,
            respect_ignore=respect_ignore,
            include_tests=include_tests,
            include_generated=include_generated,
            project_include_prefixes=project_include_prefixes,
            files=files,
            verbose=verbose,
            dry_run=True,
        )
    return _build_index_locked(
            root,
            full=full,
            content=content,
            index_dir=index_dir,
            include_prefixes=include_prefixes,
            respect_ignore=respect_ignore,
            include_tests=include_tests,
            include_generated=include_generated,
            project_include_prefixes=project_include_prefixes,
            files=files,
            verbose=verbose,
            dry_run=dry_run,
        )


def _build_index_locked(
    root: Path,
    *,
    full: bool = False,
    content: str = "docs",
    index_dir: Optional[Path] = None,
    include_prefixes: tuple[str, ...] = (),
    respect_ignore: bool = True,
    include_tests: bool = False,
    include_generated: bool = False,
    project_include_prefixes: tuple[str, ...] = (),
    files: Optional[list[Path]] = None,
    verbose: bool = False,
    dry_run: bool = False,
) -> dict:
    """Build or incrementally update the index at root/.wavefoundry/index/.

    Returns a summary dict with counts.
    """
    try:
        import numpy as np
    except ImportError:
        print(
            "build_index: numpy is not installed.\n"
            "  Run: python3 .wavefoundry/framework/scripts/setup_index.py",
            file=sys.stderr,
        )
        sys.exit(1)

    if content not in CONTENT_CHOICES:
        raise ValueError(f"content must be one of: {', '.join(CONTENT_CHOICES)}")

    build_docs = content in ("docs", "all")
    build_code = content in ("code", "all")
    meta = {} if full else _load_meta(index_dir)
    old_file_meta: dict[str, dict] = meta.get("file_meta", {})
    old_model_versions: dict[str, str] = meta.get("model_versions", {})
    # chunker_versions tracks per-content-layer chunker version so that a
    # docs-only update does not falsely stamp the code layer as current.
    old_chunker_versions: dict[str, str] = meta.get("chunker_versions", {})
    # Legacy: scalar chunker_version written by older builds — treat as applying
    # to both layers if the new per-layer key is absent.
    _legacy_cv: str = meta.get("chunker_version", "")
    if not old_chunker_versions and _legacy_cv:
        old_chunker_versions = {"docs": _legacy_cv, "code": _legacy_cv}
    current_chunker_version: str = getattr(_get_chunker(), "CHUNKER_VERSION", "")
    # walker_version is a scalar (walk_repo applies to all layers equally).
    # Absent key means a legacy index built before walker versioning — treat as mismatch.
    old_walker_version: str = meta.get("walker_version", "")

    # Force a selected-content rebuild if models changed, chunker changed for
    # this content layer, walker filter changed, or selected index files are absent.
    model_changed = False
    chunker_changed = False
    walker_changed = old_walker_version != WALKER_VERSION
    # meta["content"] records which layers were built last time (even if 0 chunks were produced).
    previously_built_content = set(meta.get("content", []))
    if build_docs:
        model_changed = model_changed or old_model_versions.get("docs") != DOCS_MODEL
        docs_index_exists = (
            (index_dir / "docs.lance").is_dir()
            or "docs" in previously_built_content
        )
        model_changed = model_changed or not docs_index_exists
        chunker_changed = chunker_changed or (
            current_chunker_version and old_chunker_versions.get("docs") != current_chunker_version
        )
    if build_code:
        model_changed = model_changed or old_model_versions.get("code") != CODE_MODEL
        code_index_exists = (
            (index_dir / "code.lance").is_dir()
            or "code" in previously_built_content
        )
        model_changed = model_changed or not code_index_exists
        chunker_changed = chunker_changed or (
            current_chunker_version and old_chunker_versions.get("code") != current_chunker_version
        )
    if model_changed or chunker_changed or walker_changed:
        if not full and (old_model_versions or old_chunker_versions or old_walker_version):
            if walker_changed:
                reason = "walker version changed" if old_walker_version else "walker version unknown (legacy index)"
            elif chunker_changed:
                reason = "chunker version changed"
            else:
                reason = "model version changed or index missing"
            print(
                f"build_index: selected {content} index missing or {reason} — "
                "performing full rebuild",
                flush=True,
            )
        full = True
        old_file_meta = {}

    if files is None:
        # Walk repo
        files = walk_repo(root, respect_ignore=respect_ignore)
        files = [path for path in files if not _is_relative_to(path, index_dir)]
        files = _filter_by_prefixes(files, root, include_prefixes)
        if str(index_dir).replace("\\", "/").endswith("/.wavefoundry/framework/index"):
            files = _filter_framework_pack_artifacts(files, root)
        content_for_filter = "all" if build_docs and build_code else ("docs" if build_docs else "code")
        resolved_project_includes = _content_project_include_prefixes(content_for_filter, project_include_prefixes)
        files = _filter_project_index_excludes(
            files,
            root,
            include_prefixes,
            project_include_prefixes=resolved_project_includes,
        )
    else:
        normalized_files: list[Path] = []
        seen: set[str] = set()
        for path in files:
            candidate = path if path.is_absolute() else root / path
            try:
                candidate.relative_to(root)
            except ValueError:
                continue
            if not candidate.is_file():
                continue
            rel = str(candidate.relative_to(root)).replace("\\", "/")
            if rel in seen:
                continue
            seen.add(rel)
            normalized_files.append(candidate)
        files = sorted(normalized_files, key=lambda p: str(p.relative_to(root)).replace("\\", "/"))
        if str(index_dir).replace("\\", "/").endswith("/.wavefoundry/framework/index"):
            files = _filter_framework_pack_artifacts(files, root)
    files_for_content = files
    if build_code and not build_docs:
        files_for_content = _filter_code_files(
            files,
            root,
            include_tests=include_tests,
            include_generated=include_generated,
        )
    if full:
        # Full rebuild: hash everything, populate stat cache for future incremental updates
        current_file_meta = {}
        for f in files:
            rel = str(f.relative_to(root)).replace("\\", "/")
            mtime, size, inode = _stat_entry(f)
            digest = _sha256(f)
            current_file_meta[rel] = {"hash": digest, "mtime": mtime, "size": size, "inode": inode}
        changed = set(current_file_meta.keys())
        removed: set[str] = set()
    else:
        # Incremental: use stat cache — only read files with changed mtime/size/inode
        current_file_meta, changed, removed = _detect_changes(files, root, old_file_meta)
    added = changed - set(old_file_meta.keys()) if not full else changed
    updated = changed & set(old_file_meta.keys()) if not full else set()
    stale = changed | removed

    if not full and not stale:
        if verbose:
            print("build_index: index is up to date", flush=True)
        return {"files_indexed": 0, "files_total": len(files), "up_to_date": True}

    if dry_run:
        scope = "full" if full else f"{len(changed)} changed, {len(removed)} removed"
        print(f"build_index: dry-run — rebuild needed ({scope})", flush=True)
        return {"files_indexed": 0, "files_total": len(files), "up_to_date": False, "dry_run": True}

    _index_label = {"docs": "docs/seed", "code": "code", "all": "docs/seed + code"}.get(content, content)
    if full:
        print(
            f"build_index: rebuilding {_index_label} index — {len(files_for_content)} source files\n"
            "  This may take several minutes to complete.",
            flush=True,
        )
    else:
        print(
            f"build_index: updating {_index_label} index — "
            f"{len(changed)} file(s) changed, {len(removed)} removed\n"
            "  This may take several minutes to complete.",
            flush=True,
        )
    if verbose:
        if not build_code:
            print("build_index: semantic code embedding disabled (use setup_index.py --include-code to enable)", flush=True)
        elif build_code and not build_docs:
            skipped = len(files) - len(files_for_content)
            if skipped:
                print(
                    f"build_index: skipped {skipped} non-source/test/generated files "
                    "(use --include-tests or --include-generated to include them)",
                    flush=True,
                )

    # If no Lance tables exist yet (first build or upgrade from legacy), force a full rebuild
    # so tables are created from the complete corpus.
    if not full:
        has_lance = (index_dir / "docs.lance").is_dir() or (index_dir / "code.lance").is_dir()
        if not has_lance:
            print(
                "build_index: no LanceDB tables found — full rebuild to create index",
                flush=True,
            )
            full = True
            current_file_meta = {}
            for f in files:
                rel = str(f.relative_to(root)).replace("\\", "/")
                mtime, size, inode = _stat_entry(f)
                digest = _sha256(f)
                current_file_meta[rel] = {"hash": digest, "mtime": mtime, "size": size, "inode": inode}
            changed = set(current_file_meta.keys())
            removed = set()
            stale = changed

    # Chunk new/changed files
    new_doc_chunks: list[dict] = []
    new_code_chunks: list[dict] = []
    files_to_index = [
        f for f in files_for_content
        if str(f.relative_to(root)).replace("\\", "/") in changed
    ] if not full else files_for_content

    for file_path in files_to_index:
        rel = str(file_path.relative_to(root)).replace("\\", "/")
        try:
            source_text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        dc, cc = _chunks_for_file(rel, source_text)
        if build_docs:
            new_doc_chunks.extend(dc)
        if build_code:
            new_code_chunks.extend(cc)

    # Embed new chunks
    _progress(
        verbose,
        f"build_index: chunked {len(files_to_index)} files "
        f"into {len(new_doc_chunks)} new doc chunks and {len(new_code_chunks)} new code chunks",
    )
    docs_embedder = None
    if build_docs:
        _progress(verbose, f"build_index: loading docs model {DOCS_MODEL}")
        docs_embedder = _get_embedder(DOCS_MODEL)
        _progress(verbose, f"build_index: loaded docs model {DOCS_MODEL}")
    code_embedder = None
    if build_code:
        _progress(verbose, f"build_index: loading code model {CODE_MODEL}")
        code_embedder = _get_embedder(CODE_MODEL)
        _progress(verbose, f"build_index: loaded code model {CODE_MODEL}")

    def _embed_chunks(label: str, chunks: list[dict], embedder) -> Optional["np.ndarray"]:
        """Embed chunks for the incremental path; sorts by length before embedding."""
        if not chunks:
            _progress(verbose, f"build_index: no new {label} chunks to embed")
            return None
        total = len(chunks)
        print(f"build_index: embedding {total} {label} chunks", flush=True)

        # Pre-sort by text length for padding efficiency (_embed_texts no longer sorts).
        order = sorted(range(total), key=lambda i: len(chunks[i]["text"]))
        inverse = [0] * total
        for new_pos, old_pos in enumerate(order):
            inverse[old_pos] = new_pos
        sorted_texts = [chunks[i]["text"] for i in order]

        import numpy as _np
        t_start = time.monotonic()
        sorted_vecs = _embed_texts(embedder, sorted_texts)
        print(
            f"build_index: embedded {total} {label} chunks "
            f"in {time.monotonic() - t_start:.1f}s",
            flush=True,
        )
        # Restore original chunk order so vecs align with chunks list.
        return sorted_vecs[inverse]

    # Write to LanceDB — the only index format.
    lance_db_path = index_dir

    # Compute chunk deltas before the write so we can count removed chunks.
    # added_files produced new chunks; updated_files replaced existing ones; removed files had theirs deleted.
    added_files_set = added if not full else set()
    updated_files_set = updated if not full else set()
    removed_files_set = removed if not full else set()
    doc_chunks_added = sum(1 for c in new_doc_chunks if c.get("path") in added_files_set)
    doc_chunks_updated_new = sum(1 for c in new_doc_chunks if c.get("path") in updated_files_set)
    code_chunks_added = sum(1 for c in new_code_chunks if c.get("path") in added_files_set)
    code_chunks_updated_new = sum(1 for c in new_code_chunks if c.get("path") in updated_files_set)
    if not full:
        doc_chunks_removed = _count_chunks_for_paths(lance_db_path, "docs", removed_files_set | updated_files_set) if build_docs else 0
        code_chunks_removed = _count_chunks_for_paths(lance_db_path, "code", removed_files_set | updated_files_set) if build_code else 0
        doc_chunks_updated_old = _count_chunks_for_paths(lance_db_path, "docs", updated_files_set) if build_docs else 0
        code_chunks_updated_old = _count_chunks_for_paths(lance_db_path, "code", updated_files_set) if build_code else 0
        # removed = old chunks for removed files; updated shows net change
        doc_chunks_removed_net = doc_chunks_removed - doc_chunks_updated_old
        code_chunks_removed_net = code_chunks_removed - code_chunks_updated_old
    else:
        doc_chunks_removed_net = 0
        code_chunks_removed_net = 0

    try:
        import numpy as _np
        if full:
            db = _get_lance_db(lance_db_path)
            if build_docs:
                if new_doc_chunks:
                    with _table_lock(lance_db_path / "docs.lance", create_dir=True):
                        _stream_embed_write(
                            db, "docs", new_doc_chunks, docs_embedder, "doc", verbose=verbose,
                        )
                else:
                    _stream_embed_write(
                        db, "docs", [], docs_embedder, "doc", verbose=verbose,
                    )
            if build_code:
                if new_code_chunks:
                    with _table_lock(lance_db_path / "code.lance", create_dir=True):
                        _stream_embed_write(
                            db, "code", new_code_chunks, code_embedder, "code", verbose=verbose,
                        )
                else:
                    _stream_embed_write(
                        db, "code", [], code_embedder, "code", verbose=verbose,
                    )
        else:
            new_doc_vecs = _embed_chunks("doc", new_doc_chunks, docs_embedder) if build_docs else None
            new_code_vecs = _embed_chunks("code", new_code_chunks, code_embedder) if build_code else None
            _lance_incremental_write(
                lance_db_path, stale,
                new_doc_chunks, new_doc_vecs,
                new_code_chunks, new_code_vecs,
                build_docs=build_docs, build_code=build_code, verbose=verbose,
            )
        # Get total chunk counts from Lance tables for the summary.
        total_doc_chunks = 0
        total_code_chunks = 0
        try:
            db = _get_lance_db(index_dir)
            if (index_dir / "docs.lance").is_dir():
                total_doc_chunks = db.open_table("docs").count_rows()
            if (index_dir / "code.lance").is_dir():
                total_code_chunks = db.open_table("code").count_rows()
        except Exception:
            total_doc_chunks = len(new_doc_chunks)
            total_code_chunks = len(new_code_chunks)
    except Exception as exc:
        print(f"build_index: LanceDB write failed: {exc}", file=sys.stderr)
        raise

    new_model_versions = dict(old_model_versions)
    if build_docs:
        new_model_versions["docs"] = DOCS_MODEL
    if build_code:
        new_model_versions["code"] = CODE_MODEL
    new_chunker_versions = dict(old_chunker_versions)
    if build_docs and current_chunker_version:
        new_chunker_versions["docs"] = current_chunker_version
    if build_code and current_chunker_version:
        new_chunker_versions["code"] = current_chunker_version
    available_content = set(meta.get("content", []))
    if build_docs:
        available_content.add("docs")
    if build_code:
        available_content.add("code")
    new_meta = {
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_versions": new_model_versions,
        "chunker_versions": new_chunker_versions,
        "walker_version": WALKER_VERSION,
        "content": sorted(available_content),
        "file_meta": current_file_meta,
    }
    _save_meta(index_dir, new_meta)

    summary = {
        "files_indexed": len(files_to_index),
        "files_total": len(files),
        "doc_chunks": total_doc_chunks,
        "code_chunks": total_code_chunks,
        "up_to_date": False,
    }
    files_summary = f"{len(added)} added, {len(updated)} updated, {len(removed)} removed"
    if build_docs:
        if full:
            doc_chunk_summary = f"{len(new_doc_chunks)} new"
        else:
            doc_chunk_summary = f"{doc_chunks_added} added, {doc_chunks_updated_new} updated, {doc_chunks_removed_net} removed"
        print(
            f"build_index: finished docs — {files_summary} | chunks: {doc_chunk_summary}",
            flush=True,
        )
    if build_code:
        if full:
            code_chunk_summary = f"{len(new_code_chunks)} new"
        else:
            code_chunk_summary = f"{code_chunks_added} added, {code_chunks_updated_new} updated, {code_chunks_removed_net} removed"
        print(
            f"build_index: finished code — {files_summary} | chunks: {code_chunk_summary}",
            flush=True,
        )
    return summary


# ---------------------------------------------------------------------------
# Watch mode
# ---------------------------------------------------------------------------

def watch_index(root: Path, verbose: bool = False) -> None:
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print(
            "build_index --watch: watchdog is not installed.\n"
            "  Install with: pip install watchdog",
            file=sys.stderr,
        )
        sys.exit(1)

    class _Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if not event.is_directory:
                build_index(root, verbose=verbose)

        def on_created(self, event):
            if not event.is_directory:
                build_index(root, verbose=verbose)

        def on_deleted(self, event):
            if not event.is_directory:
                build_index(root, verbose=verbose)

    observer = Observer()
    observer.schedule(_Handler(), str(root), recursive=True)
    observer.start()
    print(f"build_index: watching {root} — press Ctrl+C to stop")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _discover_root() -> Path:
    """Walk up from CWD to find the repo root anchored by ``workflow-config.json``.

    Intentional differences from the copies in other scripts:
    - No ``override`` parameter (callers use ``--root`` CLI arg instead).
    - Never returns ``None`` — falls back to CWD.

    Cross-reference: ``server._discover_root``, ``lifecycle_id.discover_repo_root``,
    ``render_platform_surfaces.discover_repo_root``, ``docs_gardener.project_root``.
    A future consolidation task should unify these into a shared utility.
    """
    for env_key in ("PROJECT_ROOT", "REPO_ROOT"):
        raw = os.environ.get(env_key)
        if raw:
            candidate = Path(raw).expanduser().resolve()
            if (candidate / "docs" / "workflow-config.json").is_file():
                return candidate
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / "docs" / "workflow-config.json").is_file():
            return candidate
    return cwd


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build or update the Wavefoundry semantic index.")
    parser.add_argument("--root", type=Path, default=None, help="Repository root (default: auto-discover)")
    parser.add_argument("--full", action="store_true", help="Force a full rebuild even if index is current")
    parser.add_argument(
        "--content",
        choices=CONTENT_CHOICES,
        default="docs",
        help=(
            "Content type to index (default: docs). "
            "`all` builds docs and code in one pass (used by setup_index.py --include-code). "
            "`code` indexes code only."
        ),
    )
    parser.add_argument("--index-dir", type=Path, default=None, help="Index output directory (default: <root>/.wavefoundry/index)")
    parser.add_argument(
        "--include-prefix",
        action="append",
        default=[],
        help="Only index files under this root-relative path prefix. Repeatable.",
    )
    parser.add_argument(
        "--no-ignore-files",
        action="store_true",
        help="Do not apply .gitignore/.aiignore patterns. Intended for framework packaging.",
    )
    parser.add_argument("--include-tests", action="store_true", help="Include target test files in semantic code indexing")
    parser.add_argument("--include-generated", action="store_true", help="Include generated platform hook files in semantic code indexing")
    parser.add_argument(
        "--project-include-prefix",
        action="append",
        default=[],
        help=(
            "Allow this repo-relative prefix to bypass default project index excludes "
            "(repeatable; applies to content=code)."
        ),
    )
    parser.add_argument("--watch", action="store_true", help="Watch for file changes and rebuild incrementally (requires watchdog)")
    parser.add_argument("--dry-run", action="store_true", help="Check whether a rebuild is needed without writing anything")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print progress")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve() if args.root else _discover_root()

    try:
        if args.watch:
            watch_index(root, verbose=args.verbose)
            return 0

        build_index(
            root,
            full=args.full,
            content=args.content,
            index_dir=args.index_dir,
            include_prefixes=tuple(args.include_prefix),
            respect_ignore=not args.no_ignore_files,
            include_tests=args.include_tests,
            include_generated=args.include_generated,
            project_include_prefixes=tuple(args.project_include_prefix),
            verbose=args.verbose,
            dry_run=args.dry_run,
        )
        return 0
    finally:
        state_path = os.environ.get(INDEX_BUILD_STATE_PATH_ENV)
        if state_path:
            try:
                Path(state_path).unlink()
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
