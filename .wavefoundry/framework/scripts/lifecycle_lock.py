"""Shared strict lifecycle/publication lock domain."""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from runtime_lock import RuntimeFileLock, RuntimeLockBusy, RuntimeLockError
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


@contextmanager
def lifecycle_mutation_lock(
    root: Path, *, strict: bool = True
) -> Iterator[None]:
    """Acquire the canonical non-blocking lifecycle lock.

    Authority-bearing paths use ``strict=True`` and never inherit the old
    yield-unlocked fallback. ``strict=False`` exists only for immutable legacy
    callers during staged upgrade compatibility.
    """

    lock = RuntimeFileLock(
        root / LIFECYCLE_MUTATION_LOCK_REL,
        blocking=False,
        offset=LIFECYCLE_MUTATION_LOCK_SENTINEL,
        style="record",
    )
    try:
        _acquire(lock, "lifecycle mutation")
    except LifecycleLockUnavailable:
        if strict:
            raise
        yield
        return
    try:
        lock.write_metadata({"pid": os.getpid(), "acquired_at": time.time()})
        yield
    finally:
        lock.release()


@contextmanager
def lifecycle_publication_transaction(root: Path) -> Iterator[None]:
    """Acquire lifecycle then publication, release in reverse order."""

    with lifecycle_mutation_lock(root, strict=True):
        publication = RuntimeFileLock(
            root / PROJECT_STATE_PUBLICATION_LOCK_REL,
            blocking=False,
        )
        _acquire(publication, "project publication")
        try:
            yield
        finally:
            publication.release()


__all__ = [
    "LIFECYCLE_MUTATION_LOCK_REL",
    "LIFECYCLE_MUTATION_LOCK_SENTINEL",
    "LifecycleLockBusy",
    "LifecycleLockUnavailable",
    "lifecycle_mutation_lock",
    "lifecycle_publication_transaction",
]
