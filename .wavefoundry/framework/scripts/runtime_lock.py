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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Literal, Mapping


LockStyle = Literal["flock", "record"]


class RuntimeLockError(OSError):
    """Base class for runtime-lock I/O and protocol failures."""


class RuntimeLockBusy(RuntimeLockError):
    """Raised when a non-blocking lock is already held."""


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
            # Use the host path module here instead of ``Path.parent`` so the
            # native-Windows branch can be exercised under a patched os.name
            # without pathlib attempting to manufacture a foreign path class.
            os.makedirs(os.path.dirname(os.fspath(self.path)), exist_ok=True)
            handle = self.path.open("a+b")
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
            handle.seek(self.offset)
            mode = msvcrt.LK_LOCK if self.blocking else msvcrt.LK_NBLCK
            try:
                msvcrt.locking(handle.fileno(), mode, self.length)
            except OSError as exc:
                if exc.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise RuntimeLockBusy(
                        exc.errno or errno.EACCES,
                        f"Runtime lock busy: {self.path}",
                    ) from exc
                raise RuntimeLockError(
                    exc.errno or errno.EIO,
                    f"Unable to acquire runtime lock {self.path}: {exc}",
                ) from exc
            return

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
        os.makedirs(os.path.dirname(os.fspath(target)), exist_ok=True)
        mode = "r+b" if target.exists() else "w+b"
        with target.open(mode) as handle:
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
