"""Project-local Python bytecode cache policy (change 1zyv1).

Stdlib-only. Framework processes keep compiled bytecode under
``<root>/.wavefoundry/cache/pycache/`` through ``sys.pycache_prefix`` instead of
recompiling on every start or writing ``__pycache__`` beside their sources.

The location is derived from this module's own path only: when this file sits in
``<root>/.wavefoundry/framework/scripts``, the cache is
``<root>/.wavefoundry/cache/pycache``. No ``--root``, current directory or
environment variable chooses it. Any other layout (a scratch copy, a pack
extraction) leaves caching off.

Call sites follow one rule:

* an entry point (a script run as a process) sets ``sys.dont_write_bytecode = True``
  before importing this module, then calls :func:`configure` when it runs as
  ``__main__``;
* a library module never turns writes on; it disables them only when no prefix is
  active (``if sys.pycache_prefix is None: sys.dont_write_bytecode = True``).

:func:`configure` never exports ``PYTHONPYCACHEPREFIX`` into ``os.environ``: every
framework script configures itself, and an exported variable would reach product,
sensor, git and uv children. Only the framework test runner passes the variable,
explicitly, to its writable warm-up only. Read-only children receive no prefix.

The prefix is process-wide: standard-library and site-packages imports also use
this repository-writable cache. Source digests and pack integrity checks do not
authenticate cached bytecode. ``-B``, ``PYTHONDONTWRITEBYTECODE``, ``read_only`` or
``WAVEFOUNDRY_DISABLE_BYTECODE_CACHE=1`` stop adopting the prefix. An externally
inherited prefix may already have supplied interpreter startup imports: unset
``PYTHONPYCACHEPREFIX`` before launching such direct invocations.

The cache is flushed whenever ``.wavefoundry/framework/VERSION`` changes (a stamp
file inside the cache records the bytes it was built for). A cache directory that
is a symlink, or on Windows a junction or other reparse point, is refused before
anything reads or writes through it. Every failure leaves caching off and is never
raised to the caller.
"""
from __future__ import annotations

import os
import secrets
import shutil
import stat
import sys
from pathlib import Path

PREFIX_ENV = "PYTHONPYCACHEPREFIX"
DISABLE_ENV = "WAVEFOUNDRY_DISABLE_BYTECODE_CACHE"
STAMP_NAME = "framework-version.stamp"
_STALE_PREFIX = "pycache.stale-"
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

# The result of the first configure() in this process: (active prefix or None,
# whether writes were enabled), re-applied by every later call.
_UNSET = object()
_configured: object = _UNSET


def layout_paths(scripts_dir: "Path | None" = None) -> "tuple[Path, Path, Path] | None":
    """``(cache_root, pycache_dir, version_file)`` for the framework layout, else ``None``.

    ``scripts_dir`` defaults to this module's own directory (absolute, links not
    resolved, so a scripts directory reached through a link keeps its spelling).
    """
    scripts = Path(os.path.abspath(scripts_dir if scripts_dir is not None else os.path.dirname(__file__)))
    framework = scripts.parent
    dot_wavefoundry = framework.parent
    if scripts.name != "scripts" or framework.name != "framework" or dot_wavefoundry.name != ".wavefoundry":
        return None
    cache_root = dot_wavefoundry / "cache"
    return cache_root, cache_root / "pycache", framework / "VERSION"


def is_linked(path: "Path | str") -> bool:
    """True when ``path`` exists and is a symlink, or on Windows a junction or other
    reparse point. ``os.lstat`` never follows the final component; the attribute check
    covers junctions (``Path.is_junction`` needs Python 3.12; the floor is 3.11).
    A missing path is not linked. Other ``OSError`` propagates to the caller."""
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(st.st_mode):
        return True
    return bool(getattr(st, "st_file_attributes", 0) & _REPARSE_POINT)


def _same_or_inside(candidate: str, base: Path) -> bool:
    try:
        cand = os.path.normcase(os.path.abspath(candidate))
    except (TypeError, ValueError):
        return False
    for spelling in {os.path.abspath(base), os.path.realpath(base)}:
        root = os.path.normcase(spelling)
        if cand == root or cand.startswith(root.rstrip("\\/") + os.sep):
            return True
    return False


def _unlink_link(path: Path) -> None:
    """Remove a link (or file) itself. A Windows directory junction or directory
    symlink is removed with ``os.rmdir``, which removes the link, not its target."""
    try:
        os.unlink(path)
    except (IsADirectoryError, PermissionError):
        os.rmdir(path)


def _remove_tree_no_follow(path: Path) -> None:
    """Remove ``path`` without following links: a link is unlinked, a directory is
    removed by ``shutil.rmtree`` (symlink-attack resistant on POSIX), errors ignored."""
    try:
        if is_linked(path) or not path.is_dir():
            _unlink_link(path)
            return
    except OSError:
        return
    shutil.rmtree(path, ignore_errors=True)


def _flush_if_stale(cache_root: Path, pycache: Path, version_file: Path) -> bool:
    """Flush the cache when its stamp differs from ``VERSION``; True when the cache is
    usable afterwards. Raises ``OSError`` on an unreadable ``VERSION`` or a failed write."""
    version = version_file.read_bytes() if version_file.exists() else b""
    stamp = pycache / STAMP_NAME
    try:
        current = stamp.read_bytes()
    except OSError:
        current = None
    if current == version and pycache.is_dir() and not is_linked(pycache):
        return True
    if pycache.exists() or is_linked(pycache):
        stale = cache_root / f"{_STALE_PREFIX}{os.getpid()}-{secrets.token_hex(4)}"
        try:
            os.rename(pycache, stale)
        except OSError:
            return False  # open handles (Windows) or a concurrent flusher: next process retries
        _remove_tree_no_follow(stale)
    # Leftovers from an interrupted flush are removed too (contained in the cache root).
    try:
        for entry in os.scandir(cache_root):
            if entry.name.startswith(_STALE_PREFIX):
                _remove_tree_no_follow(Path(entry.path))
    except OSError:
        pass
    pycache.mkdir(parents=True, exist_ok=True)
    if is_linked(cache_root) or is_linked(pycache):
        return False
    tmp = pycache / f".{STAMP_NAME}.{os.getpid()}.tmp"
    tmp.write_bytes(version)
    os.replace(tmp, stamp)
    return True


def _refuse(prefix_area: Path) -> None:
    sys.dont_write_bytecode = True
    current = sys.pycache_prefix
    if current and _same_or_inside(current, prefix_area):
        sys.pycache_prefix = None


def configure(*, runner: bool = False, read_only: bool = False,
              scripts_dir: "Path | None" = None) -> "str | None":
    """Configure this process's bytecode cache; returns the active prefix or ``None``.

    Idempotent: the first call decides, and every later call re-applies that
    decision (a nested ``__main__`` run, for example ``runpy``, sets the entry flag
    again before it calls this). In order:

    (a) disable the prefix and writes for interpreter opt-outs, ``read_only``,
        or ``WAVEFOUNDRY_DISABLE_BYTECODE_CACHE=1``, before cached decision replay;
    (b) refuse linked cache paths;
    (c) flush on a changed framework ``VERSION``;
    (d) set ``sys.pycache_prefix`` and turn writes on.

    ``runner`` is retained for callers but never overrides an opt-out. A disabled
    decision remains disabled on later calls. Startup imports precede this policy.

    ``PYTHONPYCACHEPREFIX`` is never written to ``os.environ``.
    """
    global _configured
    if _disabled(read_only):
        sys.pycache_prefix = None
        sys.dont_write_bytecode = True
        _configured = (None, False)
        return None
    if _configured is not _UNSET:
        prefix, writes = _configured  # type: ignore[misc]
        sys.pycache_prefix = prefix
        sys.dont_write_bytecode = not writes
        return prefix
    prefix = _configure(runner=runner, read_only=read_only, scripts_dir=scripts_dir)
    _configured = (prefix, prefix is not None and not sys.dont_write_bytecode)
    return prefix


def _disabled(read_only: bool) -> bool:
    return bool(sys.flags.dont_write_bytecode or read_only
                or os.environ.get("PYTHONDONTWRITEBYTECODE")
                or os.environ.get(DISABLE_ENV) == "1")


def _configure(*, runner: bool, read_only: bool, scripts_dir: "Path | None") -> "str | None":
    if _disabled(read_only):
        sys.pycache_prefix = None
        sys.dont_write_bytecode = True
        return None
    layout = layout_paths(scripts_dir)
    try:
        if layout is not None:
            cache_root, pycache, version_file = layout
            if is_linked(cache_root) or is_linked(pycache):
                _refuse(cache_root)
                return None
        if layout is None:
            sys.dont_write_bytecode = True
            sys.pycache_prefix = None
            return None
        cache_root, pycache, version_file = layout
        if not _flush_if_stale(cache_root, pycache, version_file):
            _refuse(cache_root)
            return None
        sys.pycache_prefix = str(pycache)
        sys.dont_write_bytecode = False
        return sys.pycache_prefix
    except Exception:  # noqa: BLE001 - caching is an optimization; never fail the caller
        if layout is not None:
            _refuse(layout[0])
        else:
            sys.dont_write_bytecode = True
        return None


def active_prefix() -> "str | None":
    """The prefix ``configure()`` left active in this process, or ``None``."""
    return None if _configured is _UNSET else _configured[0]  # type: ignore[index]


def mirror_dir(prefix: "Path | str", directory: "Path | str") -> Path:
    """Where ``sys.pycache_prefix`` mirrors ``directory`` (CPython's own mapping:
    the absolute path with any drive stripped, joined under the prefix)."""
    head = os.path.abspath(directory)
    if head[1:2] == ":" and head[0:1] not in ("\\", "/"):
        head = head[2:]
    return Path(prefix) / head.lstrip("\\/")


def remove_mirror(prefix: "Path | str", directory: "Path | str") -> bool:
    """Remove the cache's mirror of ``directory``, contained in ``prefix`` and without
    following links. A link met on the way down is unlinked, never descended into.
    Returns True when something was removed. Never raises."""
    try:
        base = Path(os.path.abspath(prefix))
        target = mirror_dir(base, directory)
        rel = target.relative_to(base)
    except (OSError, ValueError):
        return False
    if not rel.parts or ".." in rel.parts:
        return False
    try:
        if is_linked(base) or not base.is_dir():
            return False
        current = base
        for part in rel.parts:
            current = current / part
            if is_linked(current):
                _unlink_link(current)
                return True
            if not current.is_dir():
                return False
        shutil.rmtree(current, ignore_errors=True)
        return True
    except OSError:
        return False


def remove_temp_mirrors(prefix: "Path | str") -> list[str]:
    """Remove the mirrors of the temporary directory in both its given and resolved
    spellings (on macOS ``/var/folders/...`` and ``/private/var/folders/...``)."""
    import tempfile

    removed: list[str] = []
    given = tempfile.gettempdir()
    for spelling in dict.fromkeys((os.path.abspath(given), os.path.realpath(given))):
        if remove_mirror(prefix, spelling):
            removed.append(spelling)
    return removed
