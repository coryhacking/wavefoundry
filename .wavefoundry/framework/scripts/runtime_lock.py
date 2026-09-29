#!/usr/bin/env python3
"""Shared mechanics for dedicated Wavefoundry runtime lock files.

This module deliberately owns only cross-platform file-lock mechanics. Resource
wrappers retain decisions about re-entrancy, abandonment, launch ordering,
stale owners, and recovery.
"""
from __future__ import annotations

import errno
import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Literal, Mapping


LockStyle = Literal["flock", "record"]


class RuntimeLockError(OSError):
    """Base class for runtime-lock I/O and protocol failures."""


_WINDOWS_LOCK_POLL_SECONDS = 0.05


class RuntimeLockBusy(RuntimeLockError):
    """Raised when a non-blocking lock is already held."""


_BOUNDARY_NAME = ".wavefoundry"


def _is_windows_link(path: str) -> bool:
    """True only on a positive finding of a name-surrogate reparse point.

    Symlinks and junctions are refused; OneDrive placeholders and deduplicated
    files are reparse points too, but not name surrogates, and must keep working.
    """
    import stat

    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return False
    link_tags = {
        getattr(stat, "IO_REPARSE_TAG_SYMLINK", 0xA000000C),
        getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003),
    }
    return stat.S_ISLNK(info.st_mode) or getattr(info, "st_reparse_tag", 0) in link_tags


_OPEN_AT_ATTEMPTS = 5


def _open_retrying(path: str, flags: int, dir_fd: int | None = None) -> int:
    """``os.open`` with ``O_CREAT``, retrying a spurious ``ENOENT``.

    Observed on macOS: when two processes create the same new file name at
    once, the loser can get ``ENOENT`` although the parent directory exists.
    A race harness reproduced it with ``openat(dir_fd, name)`` (59 of 60
    two-process trials), and one retry always succeeded; a correctly separated
    full-path harness did not reproduce it (0 of 640). The retry covers the
    full-path form defensively. A retry finds the file the winner created, and
    the attempts are bounded so a directory that was really removed still
    fails.
    """
    for attempt in range(_OPEN_AT_ATTEMPTS):
        try:
            if dir_fd is None:
                return os.open(path, flags, 0o666)
            return os.open(path, flags, 0o666, dir_fd=dir_fd)
        except FileNotFoundError:
            if attempt == _OPEN_AT_ATTEMPTS - 1:
                raise
    raise AssertionError("unreachable")


def _open_carrier(path: Path, mode: str, *, dir_fd: int | None = None) -> BinaryIO:
    """Open a lock carrier without following a symlink at its final component.

    Wave 1z822: a repository can commit a symlink at a lock path; following it
    would truncate and overwrite whatever file it names. ``mode`` is ``"a+b"``
    (lock carriers) or ``"r+b"`` (metadata rewrites); both create a missing file.
    POSIX refuses with ``O_NOFOLLOW``, which also refuses a dangling link rather
    than creating its target. Windows has no ``O_NOFOLLOW``, so it refuses only on
    a positive finding of a name-surrogate reparse point (a symlink or a junction),
    never on an identity mismatch; OneDrive placeholders and deduplicated files
    are reparse points too, and must keep working. With ``dir_fd`` (POSIX only),
    ``path`` is the carrier's name relative to that open parent directory.
    """
    if os.name == "nt":
        if _is_windows_link(os.fspath(path)):
            raise OSError(errno.ELOOP, "lock path is a symlink or junction")
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0)
    else:
        flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW
    if mode == "a+b":
        flags |= os.O_APPEND
    try:
        fd = _open_retrying(os.fspath(path), flags, dir_fd)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise OSError(errno.ELOOP, "lock path is a symlink") from exc
        raise
    return os.fdopen(fd, mode)


def _boundary_components(path: str) -> tuple[str, list[str]] | None:
    """Split a lock path at its last ``.wavefoundry`` component, lexically.

    Wave 1z8ot (1z8oq): returns ``(base, names)`` where ``base`` is the directory
    holding ``.wavefoundry`` (not checked: the resolved repository root and its
    parents may legitimately be links) and ``names`` runs from ``.wavefoundry``
    down to the carrier's parent directory. ``None`` means the path has no
    ``.wavefoundry`` component and keeps the final-component check only.
    """
    head = os.path.dirname(path)
    names: list[str] = []
    while True:
        parent, tail = os.path.split(head)
        if tail == _BOUNDARY_NAME:
            names.append(tail)
            names.reverse()
            return parent or os.curdir, names
        if not tail or parent == head:
            return None
        names.append(tail)
        head = parent


def _link_refusal(component: str) -> OSError:
    return OSError(
        errno.ELOOP,
        f"lock directory {component} is a symlink or junction; replace it with a "
        "real directory (lock paths under .wavefoundry are fixed and cannot be relocated)",
    )


def _open_lock_carrier(path: Path, mode: str) -> BinaryIO:
    """Create the carrier's parents and open it, refusing links under ``.wavefoundry``.

    Wave 1z8ot (1z8oq): ``os.makedirs`` follows a symlinked directory, so a
    committed ``.wavefoundry/locks`` link would place every lock outside the
    repository. POSIX walks from ``.wavefoundry`` down with directory handles
    (``mkdir``/``open`` relative to ``dir_fd`` with ``O_NOFOLLOW``), leaving no
    window between check and use. Windows has no ``openat``, so each component
    is checked with ``lstat`` before it is created or opened; the window between
    that check and its use is a documented limit.
    """
    text = os.fspath(path)
    split = _boundary_components(text)
    if split is None:
        os.makedirs(os.path.dirname(text), exist_ok=True)
        return _open_carrier(path, mode)
    base, names = split
    os.makedirs(base, exist_ok=True)
    if os.name == "nt":
        current = base
        for name in names:
            if name == os.pardir:
                raise OSError(
                    errno.EINVAL,
                    f"lock path {text} contains a .. component below .wavefoundry",
                )
            current = os.path.join(current, name)
            if _is_windows_link(current):
                raise _link_refusal(current)
            try:
                os.mkdir(current)
            except FileExistsError:
                pass
        return _open_carrier(os.path.join(current, os.path.basename(text)), mode)

    import stat

    dir_flags = os.O_RDONLY | os.O_DIRECTORY
    fd = os.open(base, dir_flags)
    try:
        current = base
        for name in names:
            if name == os.pardir:
                raise OSError(
                    errno.EINVAL,
                    f"lock path {text} contains a .. component below .wavefoundry",
                )
            current = os.path.join(current, name)
            try:
                os.mkdir(name, dir_fd=fd)
            except FileExistsError:
                pass
            try:
                child = os.open(name, dir_flags | os.O_NOFOLLOW, dir_fd=fd)
            except OSError as exc:
                # macOS reports a symlinked directory opened with O_DIRECTORY |
                # O_NOFOLLOW as ENOTDIR, Linux as ELOOP; confirm it is a link so
                # an ordinary file in the way keeps its own error.
                if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                    try:
                        is_link = stat.S_ISLNK(
                            os.stat(name, dir_fd=fd, follow_symlinks=False).st_mode
                        )
                    except OSError:
                        is_link = False
                    if is_link:
                        raise _link_refusal(current) from exc
                raise
            os.close(fd)
            fd = child
        return _open_carrier(os.path.basename(text), mode, dir_fd=fd)
    finally:
        os.close(fd)


@dataclass(frozen=True)
class RuntimeLockProbe:
    held: bool | None
    error: str | None = None


class RuntimeFileLock:
    """One persistent lock-file carrier with configurable OS-lock mechanics."""

    def __init__(
        self,
        path: Path,
        *,
        blocking: bool = False,
        offset: int = 0,
        length: int = 1,
        style: LockStyle = "flock",
    ) -> None:
        if offset < 0 or length <= 0:
            raise ValueError("lock offset must be non-negative and length must be positive")
        if style not in ("flock", "record"):
            raise ValueError(f"unsupported lock style: {style}")
        # Preserve an already-resolved concrete path class. Tests exercise the
        # native-Windows branch by patching ``os.name`` on POSIX; re-wrapping a
        # PosixPath through the abstract Path factory during that patch would
        # incorrectly construct an unusable WindowsPath.
        self.path = path if isinstance(path, Path) else Path(path)
        self.blocking = bool(blocking)
        self.offset = int(offset)
        self.length = int(length)
        self.style = style
        self.handle: BinaryIO | None = None
        self.acquired = False

    def acquire(self) -> "RuntimeFileLock":
        """Create the parent lazily, open the carrier, and acquire its OS lock."""

        if self.acquired:
            return self
        try:
            # The walk uses the host path module instead of ``Path.parent`` so
            # the native-Windows branch can be exercised under a patched os.name
            # without pathlib attempting to manufacture a foreign path class.
            handle = _open_lock_carrier(self.path, "a+b")
        except OSError as exc:
            raise RuntimeLockError(
                exc.errno or errno.EIO,
                f"Unable to open runtime lock {self.path}: {exc}",
            ) from exc
        self.handle = handle
        try:
            self._acquire_os_lock(handle)
        except BaseException:
            handle.close()
            self.handle = None
            raise
        self.acquired = True
        return self

    def _acquire_os_lock(self, handle: BinaryIO) -> None:
        if os.name == "nt":
            import msvcrt

            # Byte-zero locks require a real byte on Windows. High sentinel
            # offsets deliberately remain beyond EOF so metadata at byte zero
            # can be rewritten through a separate handle.
            if self.offset == 0:
                handle.seek(0)
                if handle.read(1) == b"":
                    handle.seek(0)
                    handle.write(b"\0")
                    handle.flush()
            # Wave 1z2m8: LK_LOCK gives up after ten one-second tries, where POSIX
            # waits. A blocking lock polls LK_NBLCK until the holder releases it.
            while True:
                # msvcrt.locking starts at the current position; seek every attempt.
                handle.seek(self.offset)
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, self.length)
                    return
                except OSError as exc:
                    if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                        raise RuntimeLockError(
                            exc.errno or errno.EIO,
                            f"Unable to acquire runtime lock {self.path}: {exc}",
                        ) from exc
                    if not self.blocking:
                        raise RuntimeLockBusy(
                            exc.errno or errno.EACCES,
                            f"Runtime lock busy: {self.path}",
                        ) from exc
                time.sleep(_WINDOWS_LOCK_POLL_SECONDS)

        import fcntl

        flags = fcntl.LOCK_EX
        if not self.blocking:
            flags |= fcntl.LOCK_NB
        try:
            if self.style == "record":
                fcntl.lockf(
                    handle.fileno(),
                    flags,
                    self.length,
                    self.offset,
                    os.SEEK_SET,
                )
            else:
                fcntl.flock(handle.fileno(), flags)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EAGAIN):
                raise RuntimeLockBusy(
                    exc.errno,
                    f"Runtime lock busy: {self.path}",
                ) from exc
            raise RuntimeLockError(
                exc.errno or errno.EIO,
                f"Unable to acquire runtime lock {self.path}: {exc}",
            ) from exc

    def write_metadata(self, payload: Mapping[str, Any]) -> None:
        """Rewrite JSON at byte zero without replacing the locked inode."""

        if self.handle is None:
            raise RuntimeLockError(errno.EBADF, f"Runtime lock is not open: {self.path}")
        try:
            raw = (json.dumps(dict(payload), sort_keys=True) + "\n").encode("utf-8")
            self.handle.seek(0)
            self.handle.truncate()
            self.handle.write(raw)
            self.handle.flush()
        except (OSError, TypeError, ValueError) as exc:
            raise RuntimeLockError(
                getattr(exc, "errno", None) or errno.EIO,
                f"Unable to write runtime lock metadata {self.path}: {exc}",
            ) from exc

    def release(self) -> None:
        """Release the OS lock and close the handle; keep the carrier on disk."""

        handle = self.handle
        if handle is None:
            return
        try:
            if self.acquired:
                if os.name == "nt":
                    import msvcrt

                    handle.seek(self.offset)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, self.length)
                else:
                    import fcntl

                    if self.style == "record":
                        fcntl.lockf(
                            handle.fileno(),
                            fcntl.LOCK_UN,
                            self.length,
                            self.offset,
                            os.SEEK_SET,
                        )
                    else:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError as exc:
            raise RuntimeLockError(
                exc.errno or errno.EIO,
                f"Unable to release runtime lock {self.path}: {exc}",
            ) from exc
        finally:
            self.acquired = False
            self.handle = None
            handle.close()

    def __enter__(self) -> "RuntimeFileLock":
        return self.acquire()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()


def write_json_in_place(path: Path, payload: Mapping[str, Any]) -> None:
    """Rewrite JSON through the existing inode, creating parents when absent."""

    target = path if isinstance(path, Path) else Path(path)
    try:
        with _open_lock_carrier(target, "r+b") as handle:
            raw = (json.dumps(dict(payload), indent=2) + "\n").encode("utf-8")
            handle.seek(0)
            handle.truncate()
            handle.write(raw)
            handle.flush()
    except (OSError, TypeError, ValueError) as exc:
        raise RuntimeLockError(
            getattr(exc, "errno", None) or errno.EIO,
            f"Unable to write runtime lock metadata {target}: {exc}",
        ) from exc


def probe_runtime_lock(
    path: Path,
    *,
    offset: int = 0,
    length: int = 1,
    style: LockStyle = "flock",
    create: bool = False,
) -> RuntimeLockProbe:
    """Return held state without treating I/O failure as an unlocked carrier."""

    target = Path(path)
    if not create and not target.exists():
        return RuntimeLockProbe(False)
    lock = RuntimeFileLock(
        target,
        blocking=False,
        offset=offset,
        length=length,
        style=style,
    )
    try:
        lock.acquire()
    except RuntimeLockBusy:
        return RuntimeLockProbe(True)
    except RuntimeLockError as exc:
        return RuntimeLockProbe(None, str(exc))
    try:
        lock.release()
    except RuntimeLockError as exc:
        return RuntimeLockProbe(None, str(exc))
    return RuntimeLockProbe(False)


# POSIX record locks belong to the process, and closing ANY descriptor of the
# locked file releases them, so a process holding a record lock must not open
# that file again. Holders register here and readers in the same process
# consult the registry instead of opening the file. It lives in this module,
# which an MCP reload leaves loaded (wave 1za2y).
_PROCESS_RECORD_HOLDS: dict[str, dict[str, Any]] = {}
# Serializes acquire-and-register against every in-process reader's
# check-and-open (wave 1za2y): a reader that opened the file between another
# thread's acquire and its registration would release that thread's lock.
# Re-entrant, because a refused acquire formats its message through a reader.
_PROCESS_HOLD_GUARD = threading.RLock()


def process_hold_guard() -> threading.RLock:
    """The lock held while registering a hold or while checking and opening a held file."""
    return _PROCESS_HOLD_GUARD


def _hold_key(path: os.PathLike[str] | str) -> str:
    return os.path.realpath(os.fspath(path))


def register_process_hold(path: os.PathLike[str] | str, metadata: Mapping[str, Any]) -> None:
    """Record that this process holds the record lock on ``path``."""
    _PROCESS_RECORD_HOLDS[_hold_key(path)] = dict(metadata)


def release_process_hold(path: os.PathLike[str] | str) -> None:
    """Forget this process's hold on ``path`` (before the lock is released)."""
    _PROCESS_RECORD_HOLDS.pop(_hold_key(path), None)


def process_hold(path: os.PathLike[str] | str) -> dict[str, Any] | None:
    """The metadata this process recorded for its hold on ``path``, or ``None``."""
    held = _PROCESS_RECORD_HOLDS.get(_hold_key(path))
    return dict(held) if held is not None else None
