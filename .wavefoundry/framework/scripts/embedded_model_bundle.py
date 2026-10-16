"""Stdlib-only bounded envelope for an optional model companion in an upgrade ZIP."""
from __future__ import annotations

import hashlib
import json
import re
import stat
import zipfile
from pathlib import PurePosixPath, PureWindowsPath

DESCRIPTOR = "payload/models.json"
PREFIX = "payload/models/"
SOURCE_PROOF_ENV = "WAVEFOUNDRY_UPGRADE_SOURCE_PROOF"
MAX_DESCRIPTOR_BYTES = 16 * 1024
MAX_BUNDLE_BYTES = 4 * 1024 * 1024 * 1024
MAX_MEMBER_BYTES = 2 * 1024 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024 * 1024


def regular_member(info):
    name = info.filename
    mode = info.external_attr >> 16
    return (bool(name) and "\\" not in name and not PureWindowsPath(name).drive
            and not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts
            and not info.is_dir() and stat.S_IFMT(mode) in (0, stat.S_IFREG))


def copy_member(archive, info, destination=None, *, limit=MAX_MEMBER_BYTES):
    if not regular_member(info) or info.file_size > limit:
        raise ValueError("model archive member is unsafe or oversized")
    digest = hashlib.sha256()
    total = 0
    with archive.open(info) as source:
        while True:
            block = source.read(min(1024 * 1024, limit - total + 1))
            if not block:
                break
            total += len(block)
            if total > limit:
                raise ValueError("model archive member exceeded its byte limit")
            digest.update(block)
            if destination is not None:
                destination.write(block)
    if total != info.file_size:
        raise ValueError("model archive member size mismatch")
    return digest.hexdigest()


def read_small(archive, info, limit=MAX_DESCRIPTOR_BYTES):
    import io
    output = io.BytesIO()
    copy_member(archive, info, output, limit=limit)
    return output.getvalue()


def inspect(archive, expected_version=None):
    infos = archive.infolist()
    names = [i.filename for i in infos]
    candidates = [i for i in infos if i.filename == DESCRIPTOR or i.filename.startswith(PREFIX)]
    if not candidates:
        return None
    if len(names) != len(set(names)) or DESCRIPTOR not in names:
        raise ValueError("embedded model descriptor is missing or duplicated")
    try:
        value = json.loads(read_small(archive, archive.getinfo(DESCRIPTOR)))
    except (UnicodeError, ValueError, RecursionError, MemoryError) as exc:
        raise ValueError("embedded model descriptor is invalid") from exc
    if not isinstance(value, dict) or set(value) != {"schema_version", "model_set_version", "member", "size_bytes", "sha256"}:
        raise ValueError("embedded model descriptor fields are invalid")
    version = value["model_set_version"]
    if (type(value["schema_version"]) is not int or value["schema_version"] != 1 or not isinstance(version, str)
            or not re.fullmatch(r"\d+(?:\.\d+)*", version)
            or expected_version is not None and version != expected_version):
        raise ValueError("embedded model set does not match selected release")
    member = PREFIX + f"wavefoundry-models-{version}.zip"
    size = value["size_bytes"]
    if (value["member"] != member or {i.filename for i in candidates} != {DESCRIPTOR, member}
            or type(size) is not int or not 0 < size <= MAX_BUNDLE_BYTES
            or not isinstance(value["sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", value["sha256"])):
        raise ValueError("embedded model identity is invalid")
    info = archive.getinfo(member)
    if not regular_member(info) or info.file_size != size:
        raise ValueError("embedded model payload is unsafe or has the wrong size")
    return value


def retain(root, source, expected_hash=None):
    """Freeze an explicitly selected archive and return its narrow ownership proof."""
    import os
    import errno
    import tempfile
    from pathlib import Path
    root = Path(root).resolve(strict=True)
    import contained_files
    directory = contained_files.ensure_contained_dir(root, (".wavefoundry", "upgrade-assets"))
    fd, name = tempfile.mkstemp(prefix="embedded-", suffix=".zip", dir=directory)
    target = Path(name)
    owned = os.fstat(fd)
    digest = hashlib.sha256()
    try:
        try:
            source_entry = Path(source).lstat()
            if (not stat.S_ISREG(source_entry.st_mode)
                    or contained_files._is_link_metadata(source_entry)):
                raise OSError(errno.ELOOP, "selected combined archive is linked or not regular")
            source_fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        except BaseException:
            os.close(fd)
            raise
        with os.fdopen(source_fd, "rb") as incoming, os.fdopen(fd, "wb") as outgoing:
            before = os.fstat(incoming.fileno())
            if (not stat.S_ISREG(before.st_mode) or before.st_size > MAX_TOTAL_BYTES
                    or _identity(before) != _identity(source_entry)):
                raise ValueError("selected combined archive is not a bounded regular file")
            total = 0
            while block := incoming.read(1024 * 1024):
                total += len(block)
                if total > MAX_TOTAL_BYTES:
                    raise ValueError("combined upgrade archive exceeds byte limit")
                digest.update(block)
                outgoing.write(block)
            after = os.fstat(incoming.fileno())
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
                raise ValueError("selected combined archive changed during read")
            outgoing.flush()
            os.fsync(outgoing.fileno())
            retained = os.fstat(outgoing.fileno())
        if expected_hash is not None and digest.hexdigest() != expected_hash:
            raise ValueError("selected combined archive hash mismatch")
        proof = {"path": str(target), "sha256": digest.hexdigest(), "identity": _identity(retained)}
        _, _, entry = _retained_path(root, proof)
        if _identity(entry) != _identity(retained):
            raise ValueError("retained combined archive changed before ownership publication")
        return proof
    except BaseException:
        try:
            contained_files.unlink_contained(root, target, expected_identity=(owned.st_dev, owned.st_ino))
        except (OSError, ValueError, NotImplementedError):
            pass  # Unproven cleanup retains the entry; never unlink by name alone.
        raise


def _identity(entry):
    # Fresh identities retain device equality for read and deletion races.
    return [entry.st_dev, entry.st_ino, entry.st_size, entry.st_mtime_ns]


def _durable_identity_matches(stored, entry):
    current = _identity(entry)
    return (isinstance(stored, list) and len(stored) == 4
            and all(type(value) is int and value > 0 for value in stored)
            and all(type(value) is int and value > 0 for value in current)
            and stored[1:] == current[1:])


def _retained_path(root, proof):
    from pathlib import Path
    import contained_files
    root = Path(root).resolve(strict=True)
    if not isinstance(proof, dict):
        raise ValueError("retained combined archive proof is missing")
    path = Path(proof.get("path", ""))
    directory = root / ".wavefoundry/upgrade-assets"
    if path.parent != directory or not path.name.startswith("embedded-"):
        raise ValueError("retained combined archive path is invalid")
    identity = proof.get("identity")
    if (not isinstance(identity, list) or len(identity) != 4
            or any(type(value) is not int or value <= 0 for value in identity)
            or not isinstance(proof.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", proof["sha256"]) is None):
        raise ValueError("retained combined archive ownership proof is unproven")
    for candidate in (directory.parent, directory, path):
        entry = candidate.lstat()
        if (contained_files._is_link_metadata(entry)
                or not candidate.resolve(strict=True).is_relative_to(root)):
            raise ValueError("retained combined archive path is linked or outside the root")
        if candidate != path and not stat.S_ISDIR(entry.st_mode):
            raise ValueError("retained combined archive parent is not a directory")
    if (not stat.S_ISREG(entry.st_mode) or entry.st_nlink != 1
            or entry.st_size > MAX_TOTAL_BYTES
            or not _durable_identity_matches(proof.get("identity"), entry)):
        raise ValueError("retained combined archive identity changed or is unproven")
    return root, path, entry


def cleanup(root, proof, *, preserve=None, on_retain=None):
    """Remove a freshly proved archive; report a reason when ownership is retained.

    The shared helper keeps descriptor anchoring where available. Its bounded
    path fallback has a residual same-user race between the final check/unlink.
    """
    def retained(reason):
        if on_retain is not None:
            on_retain(reason)
        return False
    if not isinstance(proof, dict) or proof == preserve:
        return retained("archive proof is missing or explicitly preserved")
    try:
        import contained_files
        root, path, entry = _retained_path(root, proof)
        identity = _identity(entry)
        validate_retained(root, proof)
        _, _, checked = _retained_path(root, proof)
        if _identity(checked) != identity:
            return retained("archive identity changed before cleanup")
        # Never derive the fresh deletion device from persisted proof fields.
        contained_files.unlink_contained(root, path, expected_identity=tuple(identity[:2]))
        return True
    except FileNotFoundError:
        # Absence only counts after checking the proof's owned coordinates.
        from pathlib import Path
        path = Path(proof.get("path", ""))
        directory = Path(root).resolve() / ".wavefoundry/upgrade-assets"
        if path.parent == directory and path.name.startswith("embedded-"):
            return True
        return retained("archive path ownership is unproven")
    except (OSError, ValueError, NotImplementedError, TypeError) as exc:
        detail = str(exc) if isinstance(exc, ValueError) else type(exc).__name__ + " (errno " + str(getattr(exc, "errno", None)) + ")"
        return retained("archive ownership or removal refused: " + detail)


def validate_retained(root, proof):
    """Check durable ownership, hash, and fresh same-open identity on resume."""
    import os
    import contained_files
    root, path, entry = _retained_path(root, proof)
    directory = contained_files.open_contained_dir(root, path.parent.relative_to(root).parts, refuse_reparse=True)
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = (os.open(path.name, flags, dir_fd=directory) if directory is not None else os.open(path, flags))
    finally:
        if directory is not None:
            os.close(directory)
    with os.fdopen(fd, "rb") as source:
        before = os.fstat(source.fileno())
        identity = _identity(before)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or identity != _identity(entry) or not _durable_identity_matches(proof.get("identity"), before)):
            raise ValueError("retained combined archive identity changed")
        digest = hashlib.sha256()
        while block := source.read(1024 * 1024):
            digest.update(block)
        after = os.fstat(source.fileno())
        if after.st_nlink != 1 or identity != _identity(after) or digest.hexdigest() != proof.get("sha256"):
            raise ValueError("retained combined archive bytes changed")
    _, _, final = _retained_path(root, proof)
    if _identity(final) != identity:
        raise ValueError("retained combined archive changed after read")
    return path


def source_handoff(root, selected, expected_hash, raw):
    """Validate a private wrapper hint; explicit pack identity remains required."""
    from pathlib import Path
    if not isinstance(raw, str) or len(raw) > MAX_DESCRIPTOR_BYTES:
        raise ValueError("wrapper source proof is oversized or malformed")
    try:
        proof = json.loads(raw)
    except (ValueError, RecursionError, MemoryError) as exc:
        raise ValueError("wrapper source proof is malformed") from exc
    if (not isinstance(proof, dict) or selected is None or not expected_hash
            or proof.get("sha256") != expected_hash
            or proof.get("path") != str(Path(selected))):
        raise ValueError("wrapper source proof differs from the explicitly selected pack")
    validate_retained(root, proof)
    return proof
