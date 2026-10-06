"""Shared strict lifecycle/publication lock domain."""

from __future__ import annotations

import errno
import json
import os
import re
import stat
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from runtime_lock import (
    RuntimeFileLock,
    RuntimeLockBusy,
    RuntimeLockError,
    is_runtime_lock_path,
    process_hold,
    relative_parts,
    process_hold_guard,
    register_process_hold,
    release_process_hold,
)
from review_evidence import PROJECT_STATE_PUBLICATION_LOCK_REL
import record_paths


LIFECYCLE_MUTATION_LOCK_REL = Path(".wavefoundry/lifecycle-mutation.lock")
LIFECYCLE_MUTATION_LOCK_SENTINEL = 1 << 30


class _LockRefusal(RuntimeError):
    """A lock refusal with structured identity (wave 1zls7).

    ``str()`` may carry the absolute lock path for local logs; tool responses
    are built from the attributes only: ``lock_rel`` (the repository-relative
    lock path, forward slashes), ``reentry`` (the refusal is a same-process
    re-entry), ``same_thread`` (that re-entry came from the calling thread)
    and ``cause`` (the underlying exception class, plus its errno name when
    known; never its text).
    """

    def __init__(
        self,
        message: str,
        *,
        lock_rel: str | None = None,
        reentry: bool = False,
        same_thread: bool = False,
        cause: str | None = None,
    ) -> None:
        super().__init__(message)
        self.lock_rel = lock_rel
        self.reentry = reentry
        self.same_thread = same_thread
        self.cause = cause


class LifecycleLockBusy(_LockRefusal):
    pass


class LifecycleLockUnavailable(_LockRefusal):
    pass


class LifecycleLockLinkRefused(LifecycleLockUnavailable):
    """The lock was acquired, but a link to it (or an unbounded directory link)
    exists where in-process readers walk, so the hold is refused and released
    (wave 1zv8c). ``link_rel`` is the repository-relative offending entry, or
    ``None`` for a hard link (it can be anywhere on the volume)."""

    def __init__(self, message: str, *, link_rel: str | None = None, **kwargs) -> None:
        super().__init__(message, **kwargs)
        self.link_rel = link_rel


def _cause_label(exc: BaseException) -> str:
    """The exception class and errno name, without the exception's text."""
    code = errno.errorcode.get(getattr(exc, "errno", None) or 0)
    return f"{type(exc).__name__} {code}" if code else type(exc).__name__


# An absolute path inside diagnostic text: a POSIX path (a ``/`` that does not follow a word
# character, a dot or another path separator), a Windows drive path, or a backslash-led path.
_ABSOLUTE_PATH_IN_TEXT_RE = re.compile(r"(?<![\w.\\/])/[^\s'\"]|\b[A-Za-z]:[\\/]|(?<![\w.])\\[^\s'\"]")


def _root_forms(root: Path) -> set[str]:
    """The root as text in raw, resolved, JSON-escaped and backslash form."""
    forms: set[str] = set()
    try:
        candidates = {str(root), str(Path(root).resolve())}
    except (OSError, RuntimeError):
        candidates = {str(root)}
    for raw in candidates:
        for text in (raw, raw.replace("/", "\\"), raw.replace("\\", "/")):
            forms.add(text)
            forms.add(json.dumps(text)[1:-1])
    return {form for form in forms if form}


def path_free_text(text: str, root: Path) -> str | None:
    """``text`` when it names neither the root (in any form) nor another absolute
    path, else ``None`` (wave 1zls7, change 1zodv)."""
    if any(form in text for form in _root_forms(root)):
        return None
    if _ABSOLUTE_PATH_IN_TEXT_RE.search(text):
        return None
    return text


def _repo_relative_filename(filename: object, root: Path) -> str | None:
    if not isinstance(filename, (str, os.PathLike)):
        return None
    try:
        path = Path(os.fspath(filename))
    except TypeError:
        return None
    if not path.is_absolute():
        return None
    # The normalised path first, so ``root/a/../../sibling`` is not rendered as a
    # relative path that climbs out of the root; a result with ``..`` is dropped.
    for base in (Path(root), Path(root).resolve()):
        for candidate in (Path(os.path.normpath(path)), path):
            try:
                rel = candidate.relative_to(base)
            except ValueError:
                continue
            if ".." in rel.parts:
                continue
            return rel.as_posix()
    return None


def path_free_exception_text(exc: BaseException, root: Path, *, prefix_class: bool = True) -> str:
    """An exception rendered for a tool response or a status row, with no absolute path
    (wave 1zls7, change 1zodv).

    An ``OSError`` is its class and errno name (:func:`_cause_label`), followed by its
    ``filename`` made repository-relative when it lies under ``root`` (dropped otherwise);
    its ``strerror`` is never echoed, because a ``RuntimeLockBusy`` carries the absolute
    lock path there. A message-only ``OSError`` (no errno and no filename) and any other
    exception keep their text only when :func:`path_free_text`
    accepts it (after ``<class>: `` unless ``prefix_class`` is false), otherwise the class
    name alone.
    """
    if isinstance(exc, OSError) and not (exc.errno is None and exc.filename is None):
        label = _cause_label(exc)
        rel = _repo_relative_filename(exc.filename, root)
        return f"{label} on {rel}" if rel else label
    kept = path_free_text(str(exc), root)
    if not kept:
        return type(exc).__name__
    return f"{type(exc).__name__}: {kept}" if prefix_class else kept


def _acquire(lock: RuntimeFileLock, label: str, lock_rel: Path) -> None:
    try:
        lock.acquire()
    except RuntimeLockBusy as exc:
        raise LifecycleLockBusy(
            f"{label} lock is held: {lock.path}", lock_rel=lock_rel.as_posix()
        ) from exc
    except RuntimeLockError as exc:
        raise LifecycleLockUnavailable(
            f"cannot prove {label} lock ownership at {lock.path}: {exc}",
            lock_rel=lock_rel.as_posix(),
            cause=_cause_label(exc),
        ) from exc


def _hold_metadata() -> dict:
    return {
        "pid": os.getpid(),
        "acquired_at": time.time(),
        "thread": threading.get_ident(),
    }


def _refuse_if_held_here(path: Path) -> None:
    """Refuse a second acquire while this process holds the lifecycle lock.

    Wave 1zimc: the lifecycle lock is a process-owned record lock on POSIX, so
    a second acquire in the holding process would succeed and its release
    would free the first holder's lock. Call under ``process_hold_guard()``.
    """
    held = process_hold(path)
    if held is None:
        return
    owner = (
        "the calling thread"
        if held.get("thread") == threading.get_ident()
        else "another thread"
    )
    raise LifecycleLockBusy(
        f"lifecycle mutation lock is already held by this process "
        f"(pid {os.getpid()}, {owner}): {path}",
        lock_rel=LIFECYCLE_MUTATION_LOCK_REL.as_posix(),
        reentry=True,
        same_thread=owner == "the calling thread",
    )


def _release_registered(lock: RuntimeFileLock, path: Path) -> None:
    """Forget the hold, then release the OS lock, as one step under the guard."""
    with process_hold_guard():
        try:
            release_process_hold(path)
        finally:
            lock.release()


# Wave 1zv8c: the link scan's size bound. It counts only the entries listed in
# directories reached THROUGH a followed directory link whose target the real
# walk did not already list; past it the hold is refused rather than the walk
# continuing, so a directory link that points high up the tree cannot turn each
# acquisition into a walk of the whole repository. Real directories are not
# counted: they are bounded by the repository itself.
_LINK_SCAN_ENTRY_LIMIT = 50_000
# Directories the scan never enters (root-relative parts, case-folded):
# version-control internals and a project-local virtual environment. Every
# other part of ``.wavefoundry/`` is scanned, because in-process readers under
# the lock open files throughout it (the generated index included).
_LINK_SCAN_SKIP_PARTS = ((".git",), (".wavefoundry", "venv"))
# Windows reparse tag of a junction (a directory mount point).
_IO_REPARSE_TAG_MOUNT_POINT = 0xA0000003


def _is_link_entry(entry: os.DirEntry) -> bool:
    """A symlink, or on Windows a junction. ``DirEntry.is_junction`` exists only
    from Python 3.12, so the junction test reads the reparse tag of the entry's
    own (cached) ``lstat``; other reparse points (OneDrive placeholders,
    deduplicated files) are not links."""
    if entry.is_symlink():
        return True
    if os.name != "nt":
        return False
    try:
        info = entry.stat(follow_symlinks=False)
    except OSError:
        return False
    return getattr(info, "st_reparse_tag", 0) == _IO_REPARSE_TAG_MOUNT_POINT


def _link_scan_tops(root: Path) -> list[tuple[Path, bool, bool]]:
    """``(directory, recursive, record_root)`` for the scan: the record roots
    (archive included), ``docs/``, all of ``.wavefoundry/`` (except a
    project-local ``venv``, see ``_LINK_SCAN_SKIP_PARTS``), then the own entries
    (not recursive) of the repository root, where files such as ``AGENTS.md``
    are read in-process. Record roots come first so a directory they share with
    ``docs/`` is walked as a record root. A record root that resolves to the
    repository root (an unusable layout constant) is ignored."""
    roots = record_paths.unvalidated_record_roots(root)
    record_tops = [roots.waves if roots.waves_rel else None, roots.plans if roots.plans_rel else None]
    archive = record_paths.ARCHIVE_ROOT
    if isinstance(archive, str):
        parts = [part for part in archive.replace("\\", "/").split("/") if part and part != "."]
        if parts:
            record_tops.append(root.joinpath(*parts))
    tops: list[tuple[Path, bool, bool]] = [
        (top, True, True) for top in record_tops if top is not None and top != root
    ]
    tops.append((root / "docs", True, False))
    tops.append((root / ".wavefoundry", True, False))
    tops.append((root, False, False))
    return tops


def _refuse_lock_links(root: Path, lock: RuntimeFileLock) -> None:
    """Refuse a hold that an in-process reader could release (wave 1zv8c).

    On macOS and Linux the lifecycle lock is a POSIX record lock, released when
    the holding process closes ANY descriptor of the file, so a reader that
    follows a link to the lock file drops the lock mid-operation. Raises
    :class:`LifecycleLockLinkRefused` when the held file has more than one hard
    link (``fstat`` on the held handle; the other name can be anywhere on the
    volume); when a link in the scanned trees resolves to a runtime lock, judged
    by name below the root found by identity
    (``runtime_lock.is_runtime_lock_path``) and, for a target named ``*.lock``,
    by ``(st_dev, st_ino)`` against the held handle; when a directory link
    inside a record root leads outside the repository (its contents cannot be
    bounded); or when more than ``_LINK_SCAN_ENTRY_LIMIT`` entries are listed
    through followed directory links.

    The scan lists directories with ``os.scandir`` and resolves only link
    entries (``os.path.realpath``, plus ``stat`` of the target); no file is
    opened. It runs in two phases. Phase 1 walks every REAL directory under the
    scan tops without following directory links, checks every link entry it
    meets and defers the in-repository directory links; nothing it lists is
    counted. Phase 2 follows the deferred links (flat-layout wave discovery
    opens wave folders through them) and counts what it lists against the
    bound. Each directory is listed once, keyed by its ``(st_dev, st_ino)``, so
    a link into a tree the real walk already listed (a pnpm ``node_modules``
    layout) costs nothing, and a cycle ends whatever spelling a link uses.
    """
    rel = LIFECYCLE_MUTATION_LOCK_REL.as_posix()
    handle = getattr(lock, "handle", None)
    held = os.fstat(handle.fileno()) if handle is not None else None
    if held is not None and held.st_nlink != 1:
        raise LifecycleLockLinkRefused(
            f"lifecycle mutation lock {rel} has {held.st_nlink} hard links; remove the other "
            f"link, then delete {rel} while no process holds it so it is recreated",
            lock_rel=rel,
            cause="hard_link",
        )
    root_real = os.path.realpath(root)
    try:
        root_stat = os.stat(root_real)
    except OSError:
        root_stat = None
    visited: set[tuple[int, int]] = set()
    # (lexical path, resolved path, inside a record root, recursive, counted);
    # a real child's resolved path is its parent's plus its name.
    stack: list[tuple[str, str, bool, bool, bool]] = []
    # Phase-1 directory links, followed in phase 2:
    # (link path, resolved target, target stat, inside a record root).
    deferred: list[tuple[str, str, os.stat_result, bool]] = []
    listed_through_links = 0

    def inside(target: str) -> tuple[str, ...] | None:
        return relative_parts(root_real, target, root_stat=root_stat)

    def refuse(link_path: str, why: str, cause: str) -> LifecycleLockLinkRefused:
        try:
            link_rel = Path(link_path).relative_to(root).as_posix()
        except ValueError:
            link_rel = Path(link_path).name
        return LifecycleLockLinkRefused(
            f"lifecycle mutation lock {rel} refused: {link_rel} {why}",
            lock_rel=rel,
            link_rel=link_rel,
            cause=cause,
        )

    def push(lexical: str, real: str, info: os.stat_result, record_root: bool, counted: bool) -> None:
        key = (info.st_dev, info.st_ino)
        if key in visited:
            return
        parts = inside(real)
        if parts is None:
            return
        folded = tuple(os.path.normcase(part).casefold() for part in parts)
        if any(folded[: len(skip)] == skip for skip in _LINK_SCAN_SKIP_PARTS):
            return
        visited.add(key)
        stack.append((lexical, real, record_root, True, counted))

    def drain() -> None:
        nonlocal listed_through_links
        while stack:
            directory, directory_real, in_record_root, recursive, counted = stack.pop()
            try:
                with os.scandir(directory) as listing:
                    entries = list(listing)
            except OSError:
                continue
            if counted:
                listed_through_links += len(entries)
                if listed_through_links > _LINK_SCAN_ENTRY_LIMIT:
                    raise LifecycleLockLinkRefused(
                        f"lifecycle mutation lock {rel} refused: more than "
                        f"{_LINK_SCAN_ENTRY_LIMIT} entries are reachable through directory "
                        "links in the scanned trees (a directory link may lead high up the "
                        "tree); replace or remove that directory link",
                        lock_rel=rel,
                        cause="link_scan_limit",
                    )
            for entry in entries:
                if _is_link_entry(entry):
                    target = os.path.realpath(entry.path)
                    try:
                        target_stat = os.stat(target)
                    except OSError:
                        target_stat = None
                    if is_runtime_lock_path(root_real, target, root_stat=root_stat) or (
                        held is not None
                        and target_stat is not None
                        and os.path.normcase(os.path.basename(target)).casefold().endswith(".lock")
                        and os.path.samestat(target_stat, held)
                    ):
                        raise refuse(
                            entry.path,
                            "links to a runtime lock under .wavefoundry/; remove the "
                            "link (the lock file itself needs no change)",
                            "lock_link",
                        )
                    if not recursive or target_stat is None or not stat.S_ISDIR(target_stat.st_mode):
                        continue
                    if inside(target) is None:
                        if in_record_root:
                            raise refuse(
                                entry.path,
                                "is a directory link inside a record root that leads "
                                "outside the repository; replace it with a real directory",
                                "outside_link",
                            )
                        continue
                    if counted:
                        # Phase 2: a nested link is followed now, and counted.
                        push(entry.path, target, target_stat, in_record_root, True)
                    else:
                        deferred.append((entry.path, target, target_stat, in_record_root))
                elif recursive:
                    try:
                        if not entry.is_dir(follow_symlinks=False):
                            continue
                        info = entry.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    push(
                        entry.path, os.path.join(directory_real, entry.name), info,
                        in_record_root, counted,
                    )

    # Phase 1: the real directories under every top; no directory link followed.
    for top, recursive, record_root in _link_scan_tops(root):
        top_real = os.path.realpath(top)
        try:
            top_stat = os.stat(top_real)
        except OSError:
            continue
        if not stat.S_ISDIR(top_stat.st_mode):
            continue
        if not recursive:
            stack.append((os.fspath(top), top_real, record_root, False, False))
        else:
            # A top outside the repository is a layout error the record tools
            # report themselves; it is not turned into a lock refusal here.
            push(os.fspath(top), top_real, top_stat, record_root, False)
        drain()
    # Phase 2: deferred directory links whose target phase 1 did not list.
    for link_path, target, target_stat, record_root in deferred:
        push(link_path, target, target_stat, record_root, True)
        drain()


@contextmanager
def lifecycle_mutation_lock(
    root: Path, *, strict: bool = True
) -> Iterator[None]:
    """Acquire the canonical non-blocking lifecycle lock.

    Authority-bearing paths use ``strict=True`` and never inherit the old
    yield-unlocked fallback. ``strict=False`` exists only for immutable legacy
    callers during staged upgrade compatibility.

    Wave 1zimc: a hold is registered in ``runtime_lock``'s in-process registry
    (acquire and register as one step under ``process_hold_guard()``), and a
    re-entry from any thread of the holding process raises
    :class:`LifecycleLockBusy` before the lock file is opened, also under
    ``strict=False``.
    """

    path = root / LIFECYCLE_MUTATION_LOCK_REL
    with process_hold_guard():
        _refuse_if_held_here(path)
    lock = RuntimeFileLock(
        path,
        blocking=False,
        offset=LIFECYCLE_MUTATION_LOCK_SENTINEL,
        style="record",
    )
    acquired = False
    metadata: dict = {}
    try:
        with process_hold_guard():
            # Checked again at acquire time, so two threads cannot both pass.
            _refuse_if_held_here(path)
            try:
                _acquire(lock, "lifecycle mutation", LIFECYCLE_MUTATION_LOCK_REL)
            except LifecycleLockUnavailable:
                if strict:
                    raise
            else:
                # Everything after a successful acquire sits inside the
                # release-protected region (registration included), so an
                # interrupt at any point still releases the OS lock.
                acquired = True
                metadata = _hold_metadata()
                register_process_hold(path, metadata)
        if not acquired:
            # The unlocked fallback yields with the guard released.
            yield
            return
        # Wave 1zv8c: refuse a hold an in-process reader could release through
        # a link to the lock file. Inside the release-protected region, outside
        # the guard (the scan reads only directory listings).
        _refuse_lock_links(root, lock)
        lock.write_metadata(metadata)
        yield
    finally:
        if acquired:
            # The carrier persists by design; stamp the release so a reader
            # can tell a finished owner from a crashed one. Best-effort: it
            # must never replace the body's outcome or skip the release.
            try:
                try:
                    lock.write_metadata({**metadata, "released_at": time.time()})
                except Exception:  # noqa: BLE001
                    pass
            finally:
                _release_registered(lock, path)


@contextmanager
def lifecycle_publication_transaction(root: Path) -> Iterator[None]:
    """Acquire lifecycle then publication, release in reverse order.

    Wave 1zimc: the publication hold is registered with its owning thread, so
    ``project_state_publication_lock`` on this thread refuses at once instead
    of waiting on its own hold.
    """

    with lifecycle_mutation_lock(root, strict=True):
        path = root / PROJECT_STATE_PUBLICATION_LOCK_REL
        publication = RuntimeFileLock(path, blocking=False)
        acquired = False
        try:
            with process_hold_guard():
                _acquire(publication, "project publication", PROJECT_STATE_PUBLICATION_LOCK_REL)
                acquired = True
                register_process_hold(path, _hold_metadata())
            yield
        finally:
            if acquired:
                _release_registered(publication, path)


__all__ = [
    "LIFECYCLE_MUTATION_LOCK_REL",
    "LIFECYCLE_MUTATION_LOCK_SENTINEL",
    "LifecycleLockBusy",
    "LifecycleLockLinkRefused",
    "LifecycleLockUnavailable",
    "lifecycle_mutation_lock",
    "lifecycle_publication_transaction",
    "path_free_exception_text",
    "path_free_text",
]
