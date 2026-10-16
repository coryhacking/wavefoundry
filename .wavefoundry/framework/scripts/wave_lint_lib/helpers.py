from __future__ import annotations

import json
import os
import stat
import contained_files
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
    """Clear the read-text cache. Called at the start of a lint run for determinism; used by tests.

    Wave 200xy (200v1): also clears the record-document read cache and the per-run refusal
    registry, so each run reports exactly the refusals it observed."""
    _READ_TEXT_CACHE.clear()
    _RECORD_ROOTS_CACHE.clear()
    _RECORD_TEXT_CACHE.clear()
    _RECORD_REFUSALS.clear()
    _DOC_REFUSALS.clear()
    _DOC_BYTES_CACHE.clear()


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
        return path.read_text(encoding="utf-8", errors="replace").removeprefix("\ufeff")
    mtime_ns, size = st.st_mtime_ns, st.st_size
    cached = _READ_TEXT_CACHE.get(path)
    if cached is not None and cached[0] == mtime_ns and cached[1] == size:
        return cached[2]
    text = path.read_text(encoding="utf-8", errors="replace").removeprefix("\ufeff")
    _READ_TEXT_CACHE[path] = (mtime_ns, size, text)
    return text


# ---------------------------------------------------------------------------
# Wave 200xy (200v1): record documents. A record document is any ``*.md`` entry
# that lies, lexically, under the resolved waves root or the resolved plans
# root. Docs-lint reads every one through the member-doc read rule
# (``lifecycle_gate_support._read_member_doc_bytes``: an ``lstat`` regular
# file, contained in its folder and the repository, opened without following
# or blocking, capped), and its enumerations yield one only when ``lstat``
# shows a regular file. A refused entry is recorded once in the per-run
# registry below, which ``cli`` reports after the passes; the passes skip it.
# ---------------------------------------------------------------------------

RECORD_CAUSE_LINK = "a link or special file"
RECORD_CAUSE_OUTSIDE = "outside its folder or the repository"
RECORD_CAUSE_SIZE = "over the size cap"
RECORD_CAUSE_UNREADABLE = "could not be read"

# Repository-relative path -> cause class, in first-seen order.
_RECORD_REFUSALS: dict[str, str] = {}
_DOC_REFUSALS: dict[str, str] = {}
_DOC_BYTES_CACHE: dict = {}
# Path -> (identity, text). The identity is the entry's ``lstat`` identity
# (st_dev, st_ino, st_mtime_ns, st_size) taken before and after the read and
# required equal; the member-doc reader requires the opened file's ``fstat``
# (st_dev, st_ino) to match that ``lstat``, so the key is the opened file's
# identity too. A following ``stat`` is never consulted, so a swapped link
# cannot serve the cached content of its earlier target.
_RECORD_TEXT_CACHE: dict[Path, tuple[tuple[int, int, int, int], str]] = {}


def _identity(st: os.stat_result) -> tuple[int, int, int, int]:
    return (st.st_dev, st.st_ino, st.st_mtime_ns, st.st_size)


def is_record_document(root: Path, path: Path) -> bool:
    """True when ``path`` is a ``*.md`` entry lexically under the resolved waves or plans root.
    An invalid layout has no record roots (it is reported fail-closed elsewhere)."""
    path = Path(path)
    if path.suffix != ".md":
        return False
    roots = resolve_record_roots(root)
    if roots is None:
        return False
    return _is_under(path, roots.waves) or _is_under(path, roots.plans)


def record_refusal(root: Path, path: Path, cause: str) -> None:
    """Record a refused record document once per run (the first cause wins)."""
    _RECORD_REFUSALS.setdefault(relative_to_root(root, Path(path)), cause)


def record_refusals() -> dict[str, str]:
    """The refusals recorded since the last :func:`read_text_cache_clear`."""
    return dict(_RECORD_REFUSALS)


def record_refusal_failures() -> list[str]:
    """One blocking failure per refused record document, sorted by path. The message names
    the entry's own repository-relative path and a cause class only: never a link target, a
    byte of the target's content, or a value read from it."""
    return [
        f"{rel}: record document refused ({cause}); it was not read. "
        "Replace it with the document itself."
        for rel, cause in sorted(_RECORD_REFUSALS.items())
    ]


def record_entry_is_regular(root: Path, path: Path) -> bool:
    """The enumeration rule: ``True`` when ``lstat`` shows a regular file. A link or special
    file is recorded as refused; an entry that vanished is skipped; any other ``lstat``
    failure is recorded as unreadable. Nothing is followed or opened."""
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return False
    except OSError:
        record_refusal(root, path, RECORD_CAUSE_UNREADABLE)
        return False
    if stat.S_ISREG(st.st_mode):
        return True
    record_refusal(root, path, RECORD_CAUSE_LINK)
    return False


def _refusal_cause(exc: OSError) -> str:
    """The cause class for a ``MemberDocRefused`` (its ``strerror`` is the rule's cause)."""
    message = exc.strerror or ""
    if message in ("not a regular file", "changed while being opened",
                   "resolves to a framework runtime lock"):
        return RECORD_CAUSE_LINK
    if message == "exceeds the member document size cap":
        return RECORD_CAUSE_SIZE
    return RECORD_CAUSE_OUTSIDE


def read_record_text(root: Path, path: Path) -> str | None:
    """Read a record document through the member-doc rule, decoded as :func:`read_text` does
    (UTF-8, ``errors="replace"``, universal newlines). Returns ``None`` when the document is
    refused or unreadable; the refusal is recorded in the per-run registry and never raised.
    The import is function-local: ``lifecycle_gate_support`` imports from this package."""
    from lifecycle_gate_support import MemberDocRefused, _read_member_doc_bytes

    path = Path(path)
    try:
        before = os.lstat(path)
    except OSError:
        record_refusal(root, path, RECORD_CAUSE_UNREADABLE)
        return None
    if not stat.S_ISREG(before.st_mode):
        record_refusal(root, path, RECORD_CAUSE_LINK)
        return None
    identity = _identity(before)
    cached = _RECORD_TEXT_CACHE.get(path)
    if cached is not None and cached[0] == identity:
        return cached[1]
    try:
        data = _read_member_doc_bytes(path.parent, path, root=root)
    except MemberDocRefused as exc:
        record_refusal(root, path, _refusal_cause(exc))
        return None
    except OSError:
        record_refusal(root, path, RECORD_CAUSE_UNREADABLE)
        return None
    text = data.decode("utf-8", errors="replace").removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    try:
        after = os.lstat(path)
    except OSError:
        after = None
    if after is not None and stat.S_ISREG(after.st_mode) and _identity(after) == identity:
        _RECORD_TEXT_CACHE[path] = (identity, text)
    return text


def doc_refusal(root: Path, path: Path, cause: str) -> None:
    if is_record_document(root, path):
        record_refusal(root, path, cause)
    else:
        _DOC_REFUSALS.setdefault(relative_to_root(root, Path(path)), cause)


def doc_refusal_failures() -> list[str]:
    return [f"{rel}: document refused ({cause}); it was not read. Replace it with the document itself."
            for rel, cause in sorted(_DOC_REFUSALS.items())]


def doc_entry_is_regular(root: Path, path: Path) -> bool:
    try:
        parts = Path(os.path.abspath(path)).relative_to(Path(os.path.abspath(root))).parts
        parent_fd = contained_files.open_contained_dir(root, parts[:-1], refuse_reparse=True)
        try:
            entry = (os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
                     if parent_fd is not None else os.lstat(path))
        finally:
            if parent_fd is not None:
                os.close(parent_fd)
        if (not stat.S_ISREG(entry.st_mode)
                or contained_files._is_link_metadata(entry)):
            doc_refusal(root, path, RECORD_CAUSE_LINK)
            return False
        return True
    except FileNotFoundError:
        return False
    except (OSError, ValueError):
        doc_refusal(root, path, RECORD_CAUSE_UNREADABLE)
        return False


def read_doc_text(root: Path, path: Path) -> str | None:
    """Bound ordinary docs and entries without following any lexical link.

    Cache bytes only after a strict descriptor open and identity check; a
    metadata-only path check cannot establish replaced-parent read authority.
    Record documents retain their existing reader and refusal contract.
    """
    if is_record_document(root, path):
        return read_record_text(root, path)
    try:
        data = contained_files.read_contained_bytes(
            root, path, max_bytes=contained_files.DEFAULT_MAX_BYTES, follow_links=False, cache=_DOC_BYTES_CACHE)
    except contained_files.ContainedFileRefused as exc:
        cause = RECORD_CAUSE_SIZE if exc.cause == contained_files.CAUSE_SIZE else RECORD_CAUSE_LINK
        doc_refusal(root, path, cause)
        return None
    except OSError:
        doc_refusal(root, path, RECORD_CAUSE_UNREADABLE)
        return None
    return data.decode("utf-8", errors="replace").removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")


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


def archive_root(root: Path) -> Path | None:
    """The read-only archive root (wave 1z8ts), or ``None``. Live-document
    checks never run under it; only its record readability is checked."""
    roots = resolve_record_roots(root)
    return roots.archive if roots is not None else None


def is_under_archive_root(root: Path, path: Path) -> bool:
    archive = archive_root(root)
    return archive is not None and _is_under(path, archive)


def is_under_markdown_scan_root(root: Path, path: Path) -> bool:
    """True when ``path`` lies under ``docs/`` or an outside record root, and
    not under the read-only archive root."""
    if is_under_archive_root(root, path):
        return False
    return any(_is_under(path, scan_root) for scan_root in markdown_scan_roots(root))


def iter_markdown_docs(root: Path):
    archive = archive_root(root)
    for scan_root in markdown_scan_roots(root):
        try:
            parts = Path(os.path.abspath(scan_root)).relative_to(Path(os.path.abspath(root))).parts
            fd = contained_files.open_contained_dir(root, parts, refuse_reparse=True)
            if fd is not None:
                os.close(fd)
        except FileNotFoundError:
            continue
        except (OSError, ValueError):
            doc_refusal(root, scan_root, RECORD_CAUSE_UNREADABLE)
            continue
        for path in scan_root.rglob("*.md"):
            if archive is not None and _is_under(path, archive):
                continue
            if is_record_document(root, path):
                # Wave 200xy (200v1): a record document is yielded only when
                # ``lstat`` shows a regular file; a refused one is recorded.
                if record_entry_is_regular(root, path):
                    yield path
            elif doc_entry_is_regular(root, path):
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
        if doc_entry_is_regular(root, path):
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