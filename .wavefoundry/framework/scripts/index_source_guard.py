"""Exclude automatic document writes while a builder reads source files.

The persistent carrier is separate from the build's record lock: default flock
ownership also excludes independent handles in the same process. Never probe,
unlink or replace the carrier to infer ownership. Callers retain write policy.
"""
from contextlib import contextmanager
from pathlib import Path

from runtime_lock import RuntimeFileLock, RuntimeLockBusy, RuntimeLockError


# The carrier's repository-relative path, for messages that must not carry an
# absolute path (wave 1zls7).
INDEX_SOURCE_LOCK_REL = Path(".wavefoundry/locks/index-source-mutation.lock")


@contextmanager
def index_source_guard(root: Path, *, wait: bool = True):
    """Hold source exclusion, or raise on contention/error without yielding.

    Builders acquire their build lock first, then this guard before source
    reads. Automatic writers use ``wait=False`` before any publication lock;
    they must also acquire that publication lock without waiting.
    """
    path = Path(root).resolve() / INDEX_SOURCE_LOCK_REL
    with RuntimeFileLock(path, blocking=wait):
        yield
