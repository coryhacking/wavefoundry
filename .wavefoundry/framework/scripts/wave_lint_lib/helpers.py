from __future__ import annotations

import json
from pathlib import Path

# Sibling module in the parent scripts dir (stdlib-only; wave 1y0gz). docs-lint runs in hosts without
# the MCP runtime, and `record_paths` is deliberately import-light for exactly that reason.
from record_paths import RecordLayoutInvalid, RecordRoots, layout_constants, load_record_roots


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
    _RECORD_ROOTS_CACHE.clear()


# Wave 1y0gz: per-process cache of the resolved record roots, keyed on the root and the
# layout constants (the only inputs the resolver reads) so the per-file validators (links)
# do not re-validate on every doc, while a patched layout (tests) is re-resolved.
_RECORD_ROOTS_CACHE: dict[tuple, RecordRoots | RecordLayoutInvalid] = {}


def _record_roots_cache_key(root: Path) -> tuple:
    return (Path(root), layout_constants())


def resolve_record_roots(root: Path, failures: list[str] | None = None) -> RecordRoots | None:
    """Fail-closed record-root resolver for the validators (wave 1y0gz).

    Returns the :class:`RecordRoots` for the layout constants (shipped layout ->
    ``root / "docs" / "waves"`` and ``root / "docs" / "plans"``, byte-identical to the literals the
    validators used before). When the layout is invalid the ``record_layout_invalid:`` diagnostics are appended
    to ``failures`` (when given) and ``None`` is returned: a validator must then NOT scan a
    guessed root. Never falls back to the defaults silently.
    """
    key = _record_roots_cache_key(root)
    cached = _RECORD_ROOTS_CACHE.get(key)
    if cached is None:
        try:
            cached = load_record_roots(root)
        except RecordLayoutInvalid as exc:
            cached = exc
        _RECORD_ROOTS_CACHE[key] = cached
    if isinstance(cached, RecordLayoutInvalid):
        if failures is not None:
            failures.extend(cached.diagnostics)
        return None
    return cached


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


def _is_under(path: Path, ancestor: Path) -> bool:
    try:
        path.relative_to(ancestor)
        return True
    except ValueError:
        return False


def markdown_scan_roots(root: Path) -> list[Path]:
    """The directories the docs corpus is walked from (wave 1y0gz).

    ``root / "docs"`` first, then each resolved record root (waves, plans) that
    lies OUTSIDE ``docs/``, so a relocated record layout is linted and gardened
    exactly like the shipped one. Roots inside ``docs/`` are already covered by
    the ``docs/`` walk and are not repeated. An invalid layout contributes no
    record root here (it is reported fail-closed by the validators); a missing
    directory is skipped by the walkers.
    """
    docs_root = root / "docs"
    scan_roots = [docs_root]
    roots = resolve_record_roots(root)
    if roots is not None:
        for record_root in (roots.waves, roots.plans):
            if not _is_under(record_root, docs_root) and record_root not in scan_roots:
                scan_roots.append(record_root)
    return scan_roots


def is_under_markdown_scan_root(root: Path, path: Path) -> bool:
    """True when ``path`` lies under ``docs/`` or an outside record root."""
    return any(_is_under(path, scan_root) for scan_root in markdown_scan_roots(root))


def iter_markdown_docs(root: Path):
    for scan_root in markdown_scan_roots(root):
        if not scan_root.exists():
            continue
        for path in scan_root.rglob("*.md"):
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