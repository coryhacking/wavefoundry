#!/usr/bin/env python3
"""Build and maintain the Wavefoundry semantic index at .wavefoundry/index/."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
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
DOCS_NPY = "docs.npy"
DOCS_JSON = "docs.json"
CODE_NPY = "code.npy"
CODE_JSON = "code.json"
META_JSON = "meta.json"
LOCK_DIR_NAME = ".build.lock"
LOCK_STALE_SECONDS = 60 * 60

DOCS_MODEL = "BAAI/bge-small-en-v1.5"
# Use one small local model for both docs and code by default. The specialized
# code model was much slower and more memory hungry for this lightweight tool.
CODE_MODEL = DOCS_MODEL
DOC_EMBED_BATCH_SIZE = 64
CODE_EMBED_BATCH_SIZE = 16
CONTENT_CHOICES = ("docs", "code", "all")
SOURCE_CODE_EXTENSIONS = {
    ".py",
    ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs",
    ".go", ".rs", ".java", ".kt", ".swift", ".c", ".cpp", ".h", ".hpp",
    ".cs", ".rb", ".php", ".sh", ".bash", ".zsh", ".fish",
    ".yaml", ".yml", ".toml", ".json", ".jsonc",
    ".html", ".css", ".scss", ".sass",
}
GENERATED_CODE_PREFIXES = (
    ".claude/hooks/",
    ".cursor/hooks/",
    ".github/hooks/",
    ".windsurf/",
)
FRAMEWORK_TEST_PREFIXES = (
    ".wavefoundry/framework/scripts/tests/",
)
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
)
PROJECT_INDEX_EXCLUDE_PREFIXES = (
    ".wavefoundry/framework/",
)

BINARY_EXTENSIONS = {
    ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe", ".bin",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".ico", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z",
    ".mp3", ".mp4", ".wav", ".ogg", ".avi", ".mov",
    ".woff", ".woff2", ".ttf", ".eot",
    ".npy", ".npz", ".pkl", ".parquet", ".h5", ".hdf5",
    ".db", ".sqlite", ".lock",
}

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

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue

        try:
            rel = path.relative_to(root)
        except ValueError:
            continue

        rel_str = str(rel).replace("\\", "/")

        # Check hardcoded prefix excludes
        if any(rel_str.startswith(prefix) for prefix in HARDCODED_EXCLUDE_PREFIXES):
            continue

        # Check hardcoded dir-name excludes against every path component
        parts = rel_str.split("/")
        if any(part in HARDCODED_EXCLUDE_DIRS for part in parts):
            continue

        # Binary extensions
        if path.suffix.lower() in BINARY_EXTENSIONS:
            continue

        # .gitignore / .aiignore
        if _matches_ignore(rel_str, ignore_patterns):
            continue

        result.append(path)

    return result


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _build_file_hashes(files: list[Path], root: Path) -> dict[str, str]:
    return {
        str(f.relative_to(root)).replace("\\", "/"): _sha256(f)
        for f in files
    }


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
) -> list[Path]:
    """Exclude framework source from the default project-local index layer."""
    if include_prefixes:
        return files
    return [
        path for path in files
        if not any(
            str(path.relative_to(root)).replace("\\", "/").startswith(prefix)
            for prefix in PROJECT_INDEX_EXCLUDE_PREFIXES
        )
    ]


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
# Chunk I/O (without numpy — for walker-only mode)
# ---------------------------------------------------------------------------

def _load_chunks(index_dir: Path, name: str) -> list[dict]:
    p = index_dir / name
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _save_chunks(index_dir: Path, name: str, chunks: list[dict]) -> None:
    _atomic_write_text(
        index_dir / name,
        json.dumps(chunks, indent=2, ensure_ascii=False),
    )


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _save_npy_atomic(index_dir: Path, name: str, array: "np.ndarray", np_module) -> None:
    path = index_dir / name
    tmp = index_dir / f".{name}.{os.getpid()}.tmp.npy"
    np_module.save(str(tmp), array)
    os.replace(tmp, path)


@contextmanager
def _index_lock(index_dir: Path):
    lock_dir = index_dir / LOCK_DIR_NAME
    acquired = False
    while not acquired:
        try:
            lock_dir.mkdir()
            (lock_dir / "pid").write_text(str(os.getpid()), encoding="utf-8")
            acquired = True
        except FileExistsError:
            try:
                age = time.time() - lock_dir.stat().st_mtime
            except OSError:
                age = 0
            if age > LOCK_STALE_SECONDS:
                shutil.rmtree(lock_dir, ignore_errors=True)
                continue
            time.sleep(0.2)
    try:
        yield
    finally:
        shutil.rmtree(lock_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def _onnx_providers() -> list[str]:
    """Return the best available ONNX Runtime execution providers for this machine."""
    import platform
    try:
        import onnxruntime as _ort
        available = set(_ort.get_available_providers())
    except Exception:
        return ["CPUExecutionProvider"]
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        if "CoreMLExecutionProvider" in available:
            return ["CoreMLExecutionProvider", "CPUExecutionProvider"]
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


def _embed_texts(embedder, texts: list[str]) -> "np.ndarray":
    """Embed a list of texts and return as a float32 numpy array (n, dim)."""
    import numpy as _np
    return _np.array(list(embedder.embed(texts)), dtype=_np.float32)


def _progress(verbose: bool, message: str) -> None:
    if verbose:
        print(message, flush=True)


# ---------------------------------------------------------------------------
# Index build helpers
# ---------------------------------------------------------------------------

def _is_docs_kind(kind: str) -> bool:
    return kind in ("doc", "seed")


def _build_chunks_for_file(rel_path: str, content: str) -> tuple[list[dict], list[dict]]:
    """Return (doc_chunks, code_chunks) for a single file."""
    # Import chunker from sibling scripts directory
    import importlib.util
    chunker_path = Path(__file__).resolve().parent / "chunker.py"
    spec = importlib.util.spec_from_file_location("chunker", chunker_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("chunker", mod)
    spec.loader.exec_module(mod)

    raw = mod.chunk_file(content, rel_path)
    doc_chunks = [c.to_dict() for c in raw if _is_docs_kind(c.kind)]
    code_chunks = [c.to_dict() for c in raw if not _is_docs_kind(c.kind)]
    return doc_chunks, code_chunks


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
    verbose: bool = False,
) -> dict:
    index_dir = index_dir or (root / INDEX_DIR_NAME)
    if not index_dir.is_absolute():
        index_dir = root / index_dir
    index_dir.mkdir(parents=True, exist_ok=True)
    with _index_lock(index_dir):
        return _build_index_locked(
            root,
            full=full,
            content=content,
            index_dir=index_dir,
            include_prefixes=include_prefixes,
            respect_ignore=respect_ignore,
            include_tests=include_tests,
            include_generated=include_generated,
            verbose=verbose,
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
    verbose: bool = False,
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
    old_hashes: dict[str, str] = meta.get("file_hashes", {})
    old_model_versions: dict[str, str] = meta.get("model_versions", {})

    # Force a selected-content rebuild if models changed or selected index files are absent.
    model_changed = False
    if build_docs:
        model_changed = model_changed or old_model_versions.get("docs") != DOCS_MODEL
        model_changed = model_changed or not (index_dir / DOCS_JSON).exists()
        if (index_dir / DOCS_JSON).exists() and _load_chunks(index_dir, DOCS_JSON):
            model_changed = model_changed or not (index_dir / DOCS_NPY).exists()
    if build_code:
        model_changed = model_changed or old_model_versions.get("code") != CODE_MODEL
        model_changed = model_changed or not (index_dir / CODE_JSON).exists()
        if (index_dir / CODE_JSON).exists() and _load_chunks(index_dir, CODE_JSON):
            model_changed = model_changed or not (index_dir / CODE_NPY).exists()
    if model_changed:
        if not full and old_model_versions:
            print(
                f"build_index: selected {content} index missing or model version changed — "
                "performing full rebuild",
                flush=True,
            )
        full = True
        old_hashes = {}

    # Walk repo
    files = walk_repo(root, respect_ignore=respect_ignore)
    files = [path for path in files if not _is_relative_to(path, index_dir)]
    files = _filter_by_prefixes(files, root, include_prefixes)
    files = _filter_project_index_excludes(files, root, include_prefixes)
    files_for_content = files
    if build_code and not build_docs:
        files_for_content = _filter_code_files(
            files,
            root,
            include_tests=include_tests,
            include_generated=include_generated,
        )
    current_hashes = _build_file_hashes(files, root)

    # Determine changed and removed files
    changed = {p for p, h in current_hashes.items() if old_hashes.get(p) != h}
    removed = set(old_hashes.keys()) - set(current_hashes.keys())
    stale = changed | removed

    if not full and not stale:
        if verbose:
            print("build_index: index is up to date", flush=True)
        return {"files_indexed": 0, "files_total": len(files), "up_to_date": True}

    if verbose:
        if full:
            print(f"build_index: full {content} rebuild — {len(files_for_content)} files", flush=True)
        else:
            print(f"build_index: incremental {content} rebuild — {len(changed)} changed, {len(removed)} removed", flush=True)
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

    # Load existing chunks (empty on full rebuild)
    existing_docs: list[dict] = [] if full else [
        c for c in _load_chunks(index_dir, DOCS_JSON)
        if c["path"] not in stale
    ]
    existing_codes: list[dict] = [] if full else [
        c for c in _load_chunks(index_dir, CODE_JSON)
        if c["path"] not in stale
    ]

    # Load existing embeddings, filtering stale rows
    def _load_npy(name: str) -> Optional["np.ndarray"]:
        p = index_dir / name
        if p.is_file():
            try:
                return np.load(str(p))
            except Exception:
                pass
        return None

    if full:
        existing_doc_vecs = None
        existing_code_vecs = None
    else:
        # We need to know which rows to keep by aligning with existing chunk lists
        all_old_docs = _load_chunks(index_dir, DOCS_JSON)
        all_old_codes = _load_chunks(index_dir, CODE_JSON)
        old_doc_vecs = _load_npy(DOCS_NPY)
        old_code_vecs = _load_npy(CODE_NPY)

        if old_doc_vecs is not None and len(old_doc_vecs) == len(all_old_docs):
            keep_doc_idx = [i for i, c in enumerate(all_old_docs) if c["path"] not in stale]
            existing_doc_vecs = old_doc_vecs[keep_doc_idx] if keep_doc_idx else None
        else:
            existing_doc_vecs = None

        if old_code_vecs is not None and len(old_code_vecs) == len(all_old_codes):
            keep_code_idx = [i for i, c in enumerate(all_old_codes) if c["path"] not in stale]
            existing_code_vecs = old_code_vecs[keep_code_idx] if keep_code_idx else None
        else:
            existing_code_vecs = None

    if not build_docs:
        existing_docs = _load_chunks(index_dir, DOCS_JSON)
        existing_doc_vecs = None
    if not build_code:
        existing_codes = []
        existing_code_vecs = None

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
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        dc, cc = _chunks_for_file(rel, content)
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
        if not chunks:
            _progress(verbose, f"build_index: no new {label} chunks to embed")
            return None
        total = len(chunks)
        _progress(verbose, f"build_index: embedding {total} {label} chunks")
        batch_size = CODE_EMBED_BATCH_SIZE if label == "code" else DOC_EMBED_BATCH_SIZE
        batches: list["np.ndarray"] = []
        for start in range(0, total, batch_size):
            batch = chunks[start:start + batch_size]
            end = min(start + batch_size, total)
            _progress(verbose, f"build_index: embedding {label} chunks {start + 1}-{end}/{total}")
            batch_start = time.monotonic()
            texts = [c["text"] for c in batch]
            batches.append(_embed_texts(embedder, texts))
            _progress(
                verbose,
                f"build_index: embedded {end}/{total} {label} chunks "
                f"in {time.monotonic() - batch_start:.1f}s",
            )
        _progress(verbose, f"build_index: embedded {len(chunks)} {label} chunks")
        return np.concatenate(batches, axis=0)

    new_doc_vecs = _embed_chunks("doc", new_doc_chunks, docs_embedder) if build_docs else None
    new_code_vecs = _embed_chunks("code", new_code_chunks, code_embedder) if build_code else None

    # Merge existing + new
    all_doc_chunks = (existing_docs + new_doc_chunks) if build_docs else existing_docs
    all_code_chunks = (existing_codes + new_code_chunks) if build_code else existing_codes

    def _concat(a: Optional["np.ndarray"], b: Optional["np.ndarray"]) -> Optional["np.ndarray"]:
        if a is None and b is None:
            return None
        if a is None:
            return b
        if b is None:
            return a
        return np.concatenate([a, b], axis=0)

    all_doc_vecs = _concat(existing_doc_vecs, new_doc_vecs)
    all_code_vecs = _concat(existing_code_vecs, new_code_vecs)

    # Write
    if build_docs:
        _save_chunks(index_dir, DOCS_JSON, all_doc_chunks)
    if build_code:
        _save_chunks(index_dir, CODE_JSON, all_code_chunks)

    if all_doc_vecs is not None:
        _progress(verbose, f"build_index: writing {DOCS_NPY}")
        _save_npy_atomic(index_dir, DOCS_NPY, all_doc_vecs, np)
    if all_code_vecs is not None:
        _progress(verbose, f"build_index: writing {CODE_NPY}")
        _save_npy_atomic(index_dir, CODE_NPY, all_code_vecs, np)

    new_model_versions = dict(old_model_versions)
    if build_docs:
        new_model_versions["docs"] = DOCS_MODEL
    if build_code:
        new_model_versions["code"] = CODE_MODEL
    available_content = set(meta.get("content", []))
    if build_docs:
        available_content.add("docs")
    if build_code:
        available_content.add("code")
    new_meta = {
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_versions": new_model_versions,
        "content": sorted(available_content),
        "file_hashes": current_hashes,
    }
    _save_meta(index_dir, new_meta)

    summary = {
        "files_indexed": len(files_to_index),
        "files_total": len(files),
        "doc_chunks": len(all_doc_chunks),
        "code_chunks": len(all_code_chunks),
        "up_to_date": False,
    }
    if verbose:
        print(
            f"build_index: done — {summary['files_indexed']} files indexed, "
            f"{summary['doc_chunks']} doc chunks, {summary['code_chunks']} code chunks",
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
        help="Content type to index (default: docs). Use code as a separate pass to avoid loading both models.",
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
    parser.add_argument("--watch", action="store_true", help="Watch for file changes and rebuild incrementally (requires watchdog)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print progress")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve() if args.root else _discover_root()

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
        verbose=args.verbose,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
