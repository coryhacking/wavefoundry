from __future__ import annotations

import json
from pathlib import Path


# Wave 1p9c6: transparent per-process read cache. The full docs-lint reads the same doc multiple times
# per run (a wave record is read by check_wave_docs + check_metadata + check_markdown_links). Memoize on
# (path, st_mtime_ns, st_size) so repeated reads of an unchanged file hit the cache, while an edited file
# (new mtime/size) is re-read — safe across runs even in the long-lived MCP server where this module
# persists, using the same stat-identity approach as the indexer's _detect_changes. Transparent: the
# return value is identical and no caller signature changes.
_READ_TEXT_CACHE: dict[Path, tuple[int, int, str]] = {}


def read_text_cache_clear() -> None:
    """Clear the read-text cache. Called at the start of a lint run for determinism; used by tests."""
    _READ_TEXT_CACHE.clear()


def read_text(path: Path) -> str:
    try:
        st = path.stat()
    except OSError:
        # Can't stat (missing / permission) — fall back to a direct read so the caller sees the real
        # error path unchanged, and do not cache.
        return path.read_text(encoding="utf-8", errors="replace")
    mtime_ns, size = st.st_mtime_ns, st.st_size
    cached = _READ_TEXT_CACHE.get(path)
    if cached is not None and cached[0] == mtime_ns and cached[1] == size:
        return cached[2]
    text = path.read_text(encoding="utf-8", errors="replace")
    _READ_TEXT_CACHE[path] = (mtime_ns, size, text)
    return text


def load_json(path: Path) -> tuple[dict[str, object] | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:  # pragma: no cover - exercised by fixture failures if added later
        return None, str(exc)


def iter_markdown_docs(root: Path):
    docs_root = root / "docs"
    if not docs_root.exists():
        return
    for path in docs_root.rglob("*.md"):
        if path.is_file():
            yield path


# Agent entry files that live outside docs/ but carry relative links worth checking.
_ENTRY_FILES = ("AGENTS.md", "CLAUDE.md", "WARP.md")


def iter_linkable_docs(root: Path):
    """Yield all markdown files subject to link checking.

    Covers docs/**/*.md plus the agent entry files at the repo root.
    """
    yield from iter_markdown_docs(root)
    for name in _ENTRY_FILES:
        path = root / name
        if path.is_file():
            yield path


def relative_to_root(root: Path, path: Path) -> str:
    # Wave 1p9cf: return a POSIX-style (forward-slash) relative path on ALL platforms. `str()` on a
    # WindowsPath yields backslashes, which (a) breaks the many `rel.startswith("docs/…/")` forward-slash
    # comparisons across the validators (e.g. the docs/reports & docs/waves/00000 link-check skips would
    # silently not fire on Windows — letting large historical docs get link-checked) and (b) prints `\`
    # paths in lint messages, against the standing keep-`/` operator directive. `as_posix()` is a no-op on
    # POSIX and the correct normalization on Windows/WSL2.
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return Path(path).as_posix()


def write_if_changed(path: Path, content: str) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True