"""Contained repository reads and writes (wave 200ey, change 1zyv2).

The one owner of the rule for reading and writing a file that must stay inside
a repository (or another root, such as the framework directory):

- the path's lexical form is under the root (a ``..`` component is refused);
- its fully resolved path lies inside the resolved root, so a link (a
  directory component or the final component) whose target stays inside the
  root is followed, and one that leaves it is refused;
- the resolved target is a regular file (``lstat``; on Windows also not a
  name-surrogate reparse point), so a FIFO, device, directory or dangling link
  is refused before anything opens it;
- it is not a framework runtime lock, by name or as a hard link to one;
- a read takes at most ``max_bytes`` + 1 bytes and refuses more.

Where the platform supports ``dir_fd`` (Linux, macOS, WSL2), the resolved
parent is opened one component at a time with ``O_NOFOLLOW``
(:func:`open_contained_dir`) and the file is opened, created, re-moded and
published relative to that descriptor, so a component swapped for a link after
the checks makes the open fail instead of being followed. Windows has neither
``dir_fd`` nor ``O_NOFOLLOW``: the checks run by path, the open handle's
identity must match the checked one, and the window between a directory
component check and the open or replace is a documented limit.

Writes go to an exclusive temporary file in the resolved parent, get their
mode on the descriptor, and are published with ``os.replace``, which replaces a
directory entry rather than writing through it.

A refusal raises :class:`ContainedFileRefused` (an ``OSError``, ``EPERM``)
whose text is a cause class only, never a path or file content. A missing
file raises ``FileNotFoundError``, also without a path.

Standard library only: an upgrade loads this module privately from the incoming
pack, so it can import nothing from the framework.
"""

from __future__ import annotations

import errno
import os
import secrets
import stat
import time
from pathlib import Path, PurePath

# The default read cap, equal to the member-document cap
# (``lifecycle_gate_support.MEMBER_DOC_MAX_BYTES``; a test pins the two).
DEFAULT_MAX_BYTES = 8 * 1024 * 1024

# Cause classes carried by ``ContainedFileRefused``. Several are the member-doc
# rule's own strings, so a member-doc refusal keeps its text when it delegates.
CAUSE_NOT_UNDER_ROOT = "is not under the repository"
CAUSE_OUTSIDE = "resolves outside the repository"
CAUSE_UNRESOLVED = "could not be resolved"
CAUSE_NOT_REGULAR = "not a regular file"
CAUSE_RUNTIME_LOCK = "resolves to a framework runtime lock"
CAUSE_CHANGED = "changed while being opened"
CAUSE_SIZE = "exceeds the size cap"
CAUSE_LINK_COMPONENT = "a directory component is a link"
CAUSE_NOT_DIRECTORY = "a directory component is not a directory"
CAUSE_IN_USE = "the file stayed in use by another process"
CAUSE_NO_TEMPORARY = "no temporary name was free"

# Windows only: ``os.replace`` retries after a sharing violation (antivirus
# and indexers hold files briefly). The delays total half a second.
_REPLACE_RETRY_DELAYS = (0.05, 0.1, 0.1, 0.1, 0.15)


class ContainedFileRefused(OSError):
    """A contained read or write was refused. ``EPERM``; the text is a cause
    class only (one of the ``CAUSE_*`` strings), never a path."""

    def __init__(self, cause: str) -> None:
        super().__init__(errno.EPERM, cause)

    @property
    def cause(self) -> str:
        return self.strerror or ""


def runtime_lock_identities(root: Path) -> set[tuple[int, int]]:
    """``(st_dev, st_ino)`` of every ``*.lock`` file under ``<root>/.wavefoundry/``
    (wave 1zv87, 1zuq7): the identities a hard link to a runtime lock shares.
    Only ``stat`` is used; no lock file is opened. Moved here from
    ``lifecycle_gate_support`` (which re-exports it) so the contained read and
    the server's runtime-lock refusal share one owner."""
    identities: set[tuple[int, int]] = set()
    for dirpath, _dirnames, filenames in os.walk(Path(root) / ".wavefoundry"):
        for name in filenames:
            if not os.path.normcase(name).casefold().endswith(".lock"):
                continue
            try:
                lock_stat = os.stat(os.path.join(dirpath, name))
            except OSError:
                continue
            identities.add((lock_stat.st_dev, lock_stat.st_ino))
    return identities


def _is_windows_link(path: str) -> bool:
    """True only on a positive finding of a name-surrogate reparse point.

    A copy of ``runtime_lock._is_windows_link`` (this module imports nothing
    from the framework; a parity test keeps the two aligned). Symlinks and
    junctions are refused; OneDrive placeholders and deduplicated files are
    reparse points too, but not name surrogates, and must keep working.
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


# Whether the descriptor-anchored branch can run: ``open``, ``stat``, ``mkdir``,
# ``unlink`` and ``rename`` (``os.replace`` shares its dir_fd support) relative
# to a directory handle, ``O_DIRECTORY``/``O_NOFOLLOW`` and ``fchmod``. All are
# present on Linux, macOS and WSL2; ``os.supports_dir_fd`` is empty on Windows,
# which takes the path branch. Computed once at import, so a test that wraps
# ``os.open`` does not change the branch.
_DIR_FD_SUPPORTED = (
    hasattr(os, "O_DIRECTORY")
    and hasattr(os, "O_NOFOLLOW")
    and hasattr(os, "fchmod")
    and {os.open, os.stat, os.mkdir, os.unlink, os.rename} <= os.supports_dir_fd
)


def _dir_fd_supported() -> bool:
    """Whether the descriptor-anchored branch runs. Tests patch this to run
    the Windows branch on POSIX."""
    return _DIR_FD_SUPPORTED


def _windows() -> bool:
    """Whether this is native Windows (the replace retry applies only there).
    Tests patch this to simulate the Windows branch."""
    return os.name == "nt"


def _checkpoint(stage: str) -> None:
    """A no-op seam between the checks and the descriptor work that follows
    them. ``stage`` is ``"open"`` (read: after the checks, before the open) or
    ``"publish"`` (write: after the temporary file is written, before the
    replace). Tests patch it to substitute a link at that point."""
    return None


def _path_free(exc: OSError) -> OSError:
    """``exc`` without its filename fields, so no caller can echo a path."""
    if isinstance(exc, ContainedFileRefused):
        return exc
    # ``OSError(errno, strerror)`` maps to the errno's subclass
    # (``PermissionError``, ``FileNotFoundError``, ...) with no filename.
    return OSError(exc.errno, exc.strerror or os.strerror(exc.errno or 0))


def _not_found() -> FileNotFoundError:
    return FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT))


def _resolved_root(root) -> Path:
    try:
        return Path(root).resolve(strict=True)
    except (OSError, RuntimeError):
        raise ContainedFileRefused(CAUSE_UNRESOLVED) from None


def _checked_parts(parts) -> tuple[str, ...]:
    out = tuple(str(part) for part in parts)
    for name in out:
        if name in ("", os.curdir, os.pardir) or os.sep in name or (os.altsep and os.altsep in name):
            raise ContainedFileRefused(CAUSE_NOT_UNDER_ROOT)
    return out


def _lexical_parts(root, path) -> tuple[str, ...]:
    """``path``'s components below ``root``, judged lexically (no ``..``).
    A relative ``path`` is relative to ``root``; an absolute one must be under
    ``root`` as given or as resolved."""
    candidate = Path(path)
    if not candidate.is_absolute():
        if candidate.drive or candidate.root:
            raise ContainedFileRefused(CAUSE_NOT_UNDER_ROOT)
        return _checked_parts(candidate.parts)
    spellings = [Path(root)]
    try:
        spellings.append(Path(root).resolve())
    except (OSError, RuntimeError):
        pass
    for base in spellings:
        try:
            relative = candidate.relative_to(base)
        except ValueError:
            continue
        return _checked_parts(relative.parts)
    raise ContainedFileRefused(CAUSE_NOT_UNDER_ROOT)


def relative_parts(root, path) -> tuple[str, ...]:
    """``path``'s components below ``root`` under the lexical rule the read and
    write use (a relative ``path`` is relative to ``root``; an absolute one must
    be under ``root`` as given or as resolved; ``..`` is refused). For callers
    that open relative to :func:`open_contained_dir` themselves."""
    return _lexical_parts(root, path)


def _dir_parts(rel) -> tuple[str, ...]:
    if isinstance(rel, (tuple, list)):
        return _checked_parts(rel)
    candidate = PurePath(rel)
    if candidate.is_absolute() or candidate.drive or candidate.root:
        raise ContainedFileRefused(CAUSE_NOT_UNDER_ROOT)
    return _checked_parts(candidate.parts)


def _is_link_entry(path: Path, entry: os.stat_result) -> bool:
    return stat.S_ISLNK(entry.st_mode) or _is_windows_link(str(path))


def _is_runtime_lock(resolved_root: Path, resolved: Path, entry: "os.stat_result | None") -> bool:
    """A framework runtime lock: under ``<root>/.wavefoundry/`` with a name
    ending in ``.lock`` (case-folded), or a hard link sharing a lock's identity."""
    try:
        parts = resolved.relative_to(resolved_root).parts
    except ValueError:
        return False
    if len(parts) >= 2 and parts[0].casefold() == ".wavefoundry" and parts[-1].casefold().endswith(".lock"):
        return True
    if entry is not None and entry.st_nlink > 1:
        return (entry.st_dev, entry.st_ino) in runtime_lock_identities(resolved_root)
    return False


def open_contained_dir(root, rel) -> "int | None":
    """A directory descriptor on ``<resolved root>/rel``, or ``None`` on Windows.

    ``rel`` is relative to the resolved root (callers pass a resolved relative
    path, as a string, a path or a tuple of components). Where ``dir_fd`` is
    supported, each component is opened in turn with
    ``O_RDONLY|O_DIRECTORY|O_NOFOLLOW`` relative to the previous one, so no
    component is a link at the moment it is used; one that is raises
    :class:`ContainedFileRefused`, and the caller closes the returned
    descriptor. Without ``dir_fd`` (Windows) it returns ``None`` after checking
    that every existing component is a directory, is not a name-surrogate
    reparse point and resolves inside the root; the caller then acts by path,
    with the documented window."""
    resolved_root = _resolved_root(root)
    parts = _dir_parts(rel)
    if _dir_fd_supported():
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        try:
            fd = os.open(resolved_root, os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0))
        except OSError as exc:
            raise _path_free(exc) from None
        try:
            for name in parts:
                try:
                    child = os.open(name, flags, dir_fd=fd)
                except OSError as exc:
                    if exc.errno == errno.ENOENT:
                        raise _not_found() from None
                    try:
                        entry = os.stat(name, dir_fd=fd, follow_symlinks=False)
                    except OSError:
                        entry = None
                    if entry is not None and stat.S_ISLNK(entry.st_mode):
                        raise ContainedFileRefused(CAUSE_LINK_COMPONENT) from None
                    if entry is not None and not stat.S_ISDIR(entry.st_mode):
                        raise ContainedFileRefused(CAUSE_NOT_DIRECTORY) from None
                    raise _path_free(exc) from None
                os.close(fd)
                fd = child
            return fd
        except BaseException:
            os.close(fd)
            raise
    current = resolved_root
    for name in parts:
        current = current / name
        try:
            entry = os.lstat(current)
        except FileNotFoundError:
            return None
        except OSError:
            raise ContainedFileRefused(CAUSE_UNRESOLVED) from None
        if _is_link_entry(current, entry):
            raise ContainedFileRefused(CAUSE_LINK_COMPONENT)
        if not stat.S_ISDIR(entry.st_mode):
            raise ContainedFileRefused(CAUSE_NOT_DIRECTORY)
        try:
            resolved = current.resolve(strict=True)
        except (OSError, RuntimeError):
            raise ContainedFileRefused(CAUSE_UNRESOLVED) from None
        if not resolved.is_relative_to(resolved_root):
            raise ContainedFileRefused(CAUSE_OUTSIDE)
    return None


def ensure_contained_dir(root, rel) -> Path:
    """Create ``root/rel`` where absent and return its resolved path.

    ``rel`` is lexical (it may name links). Each existing component is
    followed only when it resolves inside the resolved root and is a
    directory; a missing tail is created one component at a time, relative to
    a descriptor from :func:`open_contained_dir` where ``dir_fd`` is supported,
    by path after the same checks otherwise."""
    resolved_root = _resolved_root(root)
    parts = _dir_parts(rel)
    current = resolved_root
    missing: tuple[str, ...] = ()
    for index, name in enumerate(parts):
        candidate = current / name
        try:
            entry = os.lstat(candidate)
        except FileNotFoundError:
            missing = parts[index:]
            break
        except OSError:
            raise ContainedFileRefused(CAUSE_UNRESOLVED) from None
        if _is_link_entry(candidate, entry):
            try:
                resolved = candidate.resolve(strict=True)
            except (OSError, RuntimeError):
                raise ContainedFileRefused(CAUSE_UNRESOLVED) from None
            if not resolved.is_relative_to(resolved_root):
                raise ContainedFileRefused(CAUSE_OUTSIDE)
            if not resolved.is_dir():
                raise ContainedFileRefused(CAUSE_NOT_DIRECTORY)
            current = resolved
        elif stat.S_ISDIR(entry.st_mode):
            current = candidate
        else:
            raise ContainedFileRefused(CAUSE_NOT_DIRECTORY)
    if not missing:
        return current
    base = current.relative_to(resolved_root).parts
    if _dir_fd_supported():
        fd = open_contained_dir(resolved_root, base)
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        try:
            for name in missing:
                try:
                    os.mkdir(name, 0o777, dir_fd=fd)
                except FileExistsError:
                    pass
                except OSError as exc:
                    raise _path_free(exc) from None
                try:
                    child = os.open(name, flags, dir_fd=fd)
                except OSError as exc:
                    if exc.errno in (errno.ELOOP, errno.ENOTDIR, errno.EMLINK):
                        raise ContainedFileRefused(CAUSE_LINK_COMPONENT) from None
                    raise _path_free(exc) from None
                os.close(fd)
                fd = child
        finally:
            os.close(fd)
    else:
        walked = list(base)
        for name in missing:
            open_contained_dir(resolved_root, tuple(walked))
            target = resolved_root.joinpath(*walked, name)
            try:
                os.mkdir(target)
            except FileExistsError:
                entry = os.lstat(target)
                if _is_link_entry(target, entry):
                    raise ContainedFileRefused(CAUSE_LINK_COMPONENT) from None
                if not stat.S_ISDIR(entry.st_mode):
                    raise ContainedFileRefused(CAUSE_NOT_DIRECTORY) from None
            except OSError as exc:
                raise _path_free(exc) from None
            walked.append(name)
    return resolved_root.joinpath(*base, *missing)


def _judge_existing(resolved_root: Path, parts: tuple[str, ...]) -> "tuple[Path, os.stat_result]":
    """Resolve, contain and classify an existing target (read rule)."""
    lexical = resolved_root.joinpath(*parts)
    try:
        resolved = lexical.resolve(strict=True)
    except FileNotFoundError:
        if os.path.lexists(lexical):
            # A link whose target is missing.
            raise ContainedFileRefused(CAUSE_NOT_REGULAR) from None
        raise _not_found() from None
    except (OSError, RuntimeError):
        raise ContainedFileRefused(CAUSE_UNRESOLVED) from None
    if resolved == resolved_root or not resolved.is_relative_to(resolved_root):
        raise ContainedFileRefused(CAUSE_OUTSIDE)
    try:
        entry = os.lstat(resolved)
    except FileNotFoundError:
        raise _not_found() from None
    except OSError:
        raise ContainedFileRefused(CAUSE_UNRESOLVED) from None
    if not stat.S_ISREG(entry.st_mode) or _is_windows_link(str(resolved)):
        raise ContainedFileRefused(CAUSE_NOT_REGULAR)
    if _is_runtime_lock(resolved_root, resolved, entry):
        raise ContainedFileRefused(CAUSE_RUNTIME_LOCK)
    return resolved, entry


def _open_verified(resolved_root: Path, resolved: Path, entry: os.stat_result) -> "tuple[int, os.stat_result]":
    """Open ``resolved`` for reading and check that the open descriptor is the
    regular file ``entry`` describes. Returns ``(fd, fstat)``."""
    parent = resolved.parent.relative_to(resolved_root).parts
    _checkpoint("open")
    if _dir_fd_supported():
        dir_fd = open_contained_dir(resolved_root, parent)
        try:
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
            try:
                fd = os.open(resolved.name, flags, dir_fd=dir_fd)
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.EMLINK):
                    raise ContainedFileRefused(CAUSE_CHANGED) from None
                if exc.errno == errno.ENOENT:
                    raise _not_found() from None
                raise _path_free(exc) from None
        finally:
            os.close(dir_fd)
    else:
        open_contained_dir(resolved_root, parent)
        flags = (os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0)
                 | getattr(os, "O_NONBLOCK", 0))
        try:
            fd = os.open(resolved, flags)
        except FileNotFoundError:
            raise _not_found() from None
        except OSError as exc:
            raise _path_free(exc) from None
    try:
        opened = os.fstat(fd)
        if (not stat.S_ISREG(opened.st_mode)
                or (opened.st_dev, opened.st_ino) != (entry.st_dev, entry.st_ino)):
            raise ContainedFileRefused(CAUSE_CHANGED)
    except BaseException:
        os.close(fd)
        raise
    return fd, opened


def _read_capped(fd: int, limit: int) -> bytes:
    chunks: list[bytes] = []
    remaining = limit
    while remaining > 0:
        try:
            chunk = os.read(fd, min(remaining, 1024 * 1024))
        except OSError as exc:
            raise _path_free(exc) from None
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_contained(root, path, *, max_bytes: int) -> "tuple[bytes, os.stat_result]":
    """:func:`read_contained_bytes` plus the ``fstat`` of the descriptor the
    bytes were read from (a caller's mtime or mode comes from the file read,
    never from a second, following ``stat``)."""
    resolved_root = _resolved_root(root)
    parts = _lexical_parts(root, path)
    if not parts:
        raise ContainedFileRefused(CAUSE_NOT_REGULAR)
    resolved, entry = _judge_existing(resolved_root, parts)
    fd, opened = _open_verified(resolved_root, resolved, entry)
    try:
        data = _read_capped(fd, int(max_bytes) + 1)
    finally:
        os.close(fd)
    if len(data) > max_bytes:
        raise ContainedFileRefused(CAUSE_SIZE)
    return data, opened


def read_contained_bytes(root, path, *, max_bytes: int) -> bytes:
    """Read ``path`` under the contained read rule (see the module docstring).

    Raises :class:`ContainedFileRefused` on a refusal and ``FileNotFoundError``
    when the file is missing; neither names a path."""
    return read_contained(root, path, max_bytes=max_bytes)[0]


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        view = view[written:]


def _create_temporary(name: str, mode: int, *, dir_fd: "int | None", parent: Path) -> "tuple[str, int]":
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    for _attempt in range(8):
        temporary = f".{name}.{secrets.token_hex(6)}.tmp"
        try:
            if dir_fd is not None:
                return temporary, os.open(temporary, flags, mode, dir_fd=dir_fd)
            return temporary, os.open(parent / temporary, flags, mode)
        except FileExistsError:
            continue
        except OSError as exc:
            raise _path_free(exc) from None
    raise ContainedFileRefused(CAUSE_NO_TEMPORARY)


def _remove_temporary(temporary: str, *, dir_fd: "int | None", parent: Path) -> None:
    try:
        if dir_fd is not None:
            os.unlink(temporary, dir_fd=dir_fd)
        else:
            os.unlink(parent / temporary)
    except OSError:
        pass


def _replace_by_path(source: Path, target: Path) -> None:
    """``os.replace`` by path (the Windows branch), retrying a sharing violation
    on Windows a bounded few times before a path-free refusal."""
    delays = _REPLACE_RETRY_DELAYS if _windows() else ()
    for attempt in range(len(delays) + 1):
        try:
            os.replace(source, target)
            return
        except PermissionError as exc:
            if attempt >= len(delays):
                if _windows():
                    raise ContainedFileRefused(CAUSE_IN_USE) from None
                raise _path_free(exc) from None
            time.sleep(delays[attempt])
        except OSError as exc:
            raise _path_free(exc) from None


def write_contained_bytes(root, path, data: bytes, *, mode: "int | None" = None,
                          executable: bool = False) -> bool:
    """Write ``data`` at ``path`` under the contained write rule; returns
    whether the file's bytes changed.

    The resolution, containment and walk of the read rule apply to the target,
    so a write through a link that stays inside the root writes the link's
    target and leaves the link in place, and a link leaving the root is
    refused. Missing parent directories are created (:func:`ensure_contained_dir`).
    An existing target that is not a regular file is refused. The bytes go to an
    exclusive no-follow temporary file in the resolved parent whose mode is set
    on the descriptor (the existing target's permission bits, else ``mode``,
    else ``0o666`` less the umask; plus ``0o111`` when ``executable``), which is
    then published with ``os.replace`` relative to the parent's descriptor.
    Nothing is written or re-moded through a path that could be a link. When
    the bytes are unchanged only a differing mode is set, on a verified
    descriptor, and nothing is written."""
    data = bytes(data)
    resolved_root = _resolved_root(root)
    parts = _lexical_parts(root, path)
    if not parts:
        raise ContainedFileRefused(CAUSE_NOT_REGULAR)
    parent = ensure_contained_dir(resolved_root, parts[:-1])
    target = parent / parts[-1]
    try:
        entry: "os.stat_result | None" = os.lstat(target)
    except FileNotFoundError:
        entry = None
    except OSError:
        raise ContainedFileRefused(CAUSE_UNRESOLVED) from None
    if entry is not None and _is_link_entry(target, entry):
        try:
            target = target.resolve(strict=True)
        except FileNotFoundError:
            raise ContainedFileRefused(CAUSE_NOT_REGULAR) from None
        except (OSError, RuntimeError):
            raise ContainedFileRefused(CAUSE_UNRESOLVED) from None
        if not target.is_relative_to(resolved_root) or target == resolved_root:
            raise ContainedFileRefused(CAUSE_OUTSIDE)
        parent = target.parent
        try:
            entry = os.lstat(target)
        except OSError:
            raise ContainedFileRefused(CAUSE_UNRESOLVED) from None
    if entry is not None and (not stat.S_ISREG(entry.st_mode) or _is_windows_link(str(target))):
        raise ContainedFileRefused(CAUSE_NOT_REGULAR)
    if _is_runtime_lock(resolved_root, target, entry):
        raise ContainedFileRefused(CAUSE_RUNTIME_LOCK)
    extra = 0o111 if executable else 0
    if mode is not None:
        wanted: "int | None" = (mode & 0o7777) | extra
    elif entry is not None:
        wanted = stat.S_IMODE(entry.st_mode) | extra
    else:
        wanted = None
    can_chmod = hasattr(os, "fchmod")
    if entry is not None and entry.st_size == len(data):
        fd, opened = _open_verified(resolved_root, target, entry)
        try:
            same = _read_capped(fd, len(data) + 1) == data
            if same:
                if can_chmod and wanted is not None and stat.S_IMODE(opened.st_mode) != wanted:
                    os.fchmod(fd, wanted)
                return False
        finally:
            os.close(fd)
    parent_rel = parent.relative_to(resolved_root).parts
    create_mode = 0o666 if wanted is None else (wanted & 0o777)
    if _dir_fd_supported():
        dir_fd = open_contained_dir(resolved_root, parent_rel)
        try:
            temporary, fd = _create_temporary(target.name, create_mode, dir_fd=dir_fd, parent=parent)
            try:
                try:
                    _write_all(fd, data)
                    if wanted is not None:
                        os.fchmod(fd, wanted)
                    elif extra:
                        os.fchmod(fd, stat.S_IMODE(os.fstat(fd).st_mode) | extra)
                finally:
                    os.close(fd)
                _checkpoint("publish")
                os.replace(temporary, target.name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
            except BaseException as exc:
                _remove_temporary(temporary, dir_fd=dir_fd, parent=parent)
                if isinstance(exc, OSError):
                    raise _path_free(exc) from None
                raise
        finally:
            os.close(dir_fd)
        return True
    open_contained_dir(resolved_root, parent_rel)
    temporary, fd = _create_temporary(target.name, create_mode, dir_fd=None, parent=parent)
    try:
        try:
            _write_all(fd, data)
            if can_chmod:
                if wanted is not None:
                    os.fchmod(fd, wanted)
                elif extra:
                    os.fchmod(fd, stat.S_IMODE(os.fstat(fd).st_mode) | extra)
        finally:
            os.close(fd)
        _checkpoint("publish")
        _replace_by_path(parent / temporary, target)
    except BaseException as exc:
        _remove_temporary(temporary, dir_fd=None, parent=parent)
        if isinstance(exc, OSError):
            raise _path_free(exc) from None
        raise
    return True
