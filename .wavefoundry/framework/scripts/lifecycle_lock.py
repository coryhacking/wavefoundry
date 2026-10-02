"""Shared strict lifecycle/publication lock domain."""

from __future__ import annotations

import os
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


class LifecycleLockBusy(RuntimeError):
    pass


class LifecycleLockUnavailable(RuntimeError):
    pass


def _acquire(lock: RuntimeFileLock, label: str) -> None:
    try:
        lock.acquire()
    except RuntimeLockBusy as exc:
        raise LifecycleLockBusy(f"{label} lock is held: {lock.path}") from exc
    except RuntimeLockError as exc:
        raise LifecycleLockUnavailable(
            f"cannot prove {label} lock ownership at {lock.path}: {exc}"
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
        f"(pid {os.getpid()}, {owner}): {path}"
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
                _acquire(lock, "lifecycle mutation")
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
                _acquire(publication, "project publication")
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
]
