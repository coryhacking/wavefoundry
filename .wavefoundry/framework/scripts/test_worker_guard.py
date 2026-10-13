"""Cooperative test-worker record-write guard; inert until explicitly installed.

This prevents accidental Python writes, not hostile code: native writes,
pre-opened descriptors and children that bypass the startup environment remain
outside its interception boundary. The marker does not authenticate a writer.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import threading


MARKER = "WAVEFOUNDRY_TEST_WORKER_PROTECTED_ROOTS"
_protected: set[str] = set()
_installed = False
_native_fcntl = None
_original_open = os.open
_open_context = threading.local()
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND


def _canonical(path):
    return os.path.normcase(os.path.realpath(path))


def _entries(env):
    if MARKER not in env:
        return []
    try:
        entries = json.loads(env[MARKER])
        if not isinstance(entries, list) or not entries:
            raise ValueError("expected nonempty protected-root list")
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"root", "record_dirs"}:
                raise ValueError("invalid protected-root entry")
            root, dirs = entry["root"], entry["record_dirs"]
            if not isinstance(root, str) or not os.path.isabs(root) or "\0" in root:
                raise ValueError("protected root must be absolute")
            if not isinstance(dirs, list) or not dirs:
                raise ValueError("expected nonempty record directories")
            for directory in dirs:
                if (not isinstance(directory, str) or not directory
                        or "\0" in directory or os.path.isabs(directory) or os.path.splitdrive(directory)[0]
                        or any(part in {".", ".."} for part in directory.replace("\\", "/").split("/"))):
                    raise ValueError("record directories must be repository-relative")
        return entries
    except (ValueError, TypeError) as exc:
        raise RuntimeError(f"invalid test-worker protection marker: {exc}") from exc


def worker_environment(env: dict, repo_root: Path, record_dirs) -> dict:
    """Return child environment preserving outer protection and Python path order."""
    result = dict(env)
    entries = _entries(result)
    entry = {"root": _canonical(repo_root), "record_dirs": list(record_dirs)}
    if entry not in entries:
        entries.append(entry)
    result[MARKER] = json.dumps(entries, separators=(",", ":"))
    _entries(result)  # Reject malformed new input as well as inherited input.
    bootstrap = _canonical(Path(__file__).resolve().parent / "test_worker_bootstrap")
    old_path = result.get("PYTHONPATH")
    remaining = [] if old_path is None else [
        part for part in old_path.split(os.pathsep) if part and _canonical(part) != bootstrap
    ]
    result["PYTHONPATH"] = os.pathsep.join([bootstrap, *remaining])
    return result


def refuse_publication(repo_root: Path) -> None:
    """Reject marked publication even when a child skipped site initialization."""
    entries = _entries(os.environ)
    if not entries:
        return
    root = _canonical(repo_root)
    if any(root == _canonical(entry["root"]) for entry in entries):
        raise PermissionError(f"test worker cannot publish protected repository state: {root}")


def _descriptor_path(descriptor):
    # Linux / WSL expose descriptors here. macOS supplies F_GETPATH instead.
    try:
        path = os.readlink(f"/proc/self/fd/{descriptor}")
        if os.path.isabs(path) and not path.endswith(" (deleted)"):
            return path
    except OSError:
        pass
    if _native_fcntl is not None:
        try:
            return os.fsdecode(_native_fcntl(descriptor, 50, b"\0" * 1024).split(b"\0", 1)[0])
        except OSError:
            pass
    raise PermissionError("test worker cannot resolve mutation directory descriptor")


def _check(path, dir_fd=None, *, ancestors=False):
    if isinstance(path, int):
        # Writes through descriptors opened before instrumentation are unsupported.
        return
    path = os.fsdecode(path)
    if not os.path.isabs(path) and dir_fd not in (None, -1):
        path = os.path.join(_descriptor_path(dir_fd), path)
    candidates = {os.path.normcase(os.path.abspath(path)), _canonical(path)}
    for candidate in candidates:
        for protected in _protected:
            if (candidate == protected or candidate.startswith(protected + os.sep)
                    or (ancestors and protected.startswith(candidate.rstrip(os.sep) + os.sep))):
                raise PermissionError(f"test worker cannot mutate protected record path: {path}")


def _audit(event, args):
    if event == "open":
        path, mode, flags = args
        if flags & _WRITE_FLAGS or (mode and any(char in mode for char in "wax+")):
            _check(path, getattr(_open_context, "dir_fd", None))
    elif event in {"os.rename", "os.link"}:
        source, destination, source_fd, destination_fd = args
        _check(source, source_fd, ancestors=True)
        _check(destination, destination_fd, ancestors=True)
    elif event == "os.symlink":
        source, destination, directory_fd = args
        _check(destination, directory_fd, ancestors=True)
        # Creating an alias of a protected directory cannot grant write access.
        # The destination checks and later realpath checks enforce that rule.
    elif event in {"os.remove", "os.rmdir"}:
        _check(args[0], args[1], ancestors=True)
    elif event == "os.mkdir":
        # Creating an ancestor cannot replace it; allow harmless exist_ok
        # setup for unrelated sibling docs, while protecting record roots.
        _check(args[0], args[2])
    elif event in {"os.chmod", "os.chown", "os.utime"}:
        _check(args[0], args[-1], ancestors=True)
    elif event == "os.truncate":
        _check(args[0])
    elif event == "shutil.rmtree":
        _check(args[0], args[1], ancestors=True)


def _guarded_open(path, flags, mode=0o777, *, dir_fd=None):
    # CPython's open audit event omits dir_fd; check it before delegating.
    if flags & _WRITE_FLAGS:
        _check(path, dir_fd)
    previous = getattr(_open_context, "dir_fd", None)
    _open_context.dir_fd = dir_fd
    try:
        return _original_open(path, flags, mode, dir_fd=dir_fd)
    finally:
        _open_context.dir_fd = previous


def install() -> None:
    """Install once before discovery; repeated calls may add inherited roots."""
    global _installed, _native_fcntl
    entries = _entries(os.environ)
    if not entries:
        return
    for entry in entries:
        for directory in entry["record_dirs"]:
            path = os.path.join(entry["root"], directory)
            _protected.update({os.path.normcase(os.path.abspath(path)), _canonical(path)})
    if not _installed:
        # Keep instrumentation on the host primitive when tests replace their
        # fcntl module to simulate another locking platform.
        if sys.platform == "darwin":
            from fcntl import fcntl
            _native_fcntl = fcntl
        sys.addaudithook(_audit)
        os.open = _guarded_open
        # shutil's safe rmtree capability probe uses identity membership here.
        if _original_open in os.supports_dir_fd:
            os.supports_dir_fd.add(_guarded_open)
        _installed = True
