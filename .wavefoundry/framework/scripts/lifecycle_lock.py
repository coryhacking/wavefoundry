"""Shared strict lifecycle/publication lock domain."""

from __future__ import annotations

import errno
import json
import os
import re
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from runtime_lock import (
    RuntimeFileLock,
    RuntimeLockBusy,
    RuntimeLockError,
    process_hold,
    process_hold_guard,
    register_process_hold,
    release_process_hold,
)
from review_evidence import PROJECT_STATE_PUBLICATION_LOCK_REL


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
    "LifecycleLockUnavailable",
    "lifecycle_mutation_lock",
    "lifecycle_publication_transaction",
    "path_free_exception_text",
    "path_free_text",
]
