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
    import tempfile
    from pathlib import Path
    root = Path(root).resolve(strict=True)
    directory = root / ".wavefoundry" / "upgrade-assets"
    if directory.is_symlink() or directory.parent.is_symlink():
        raise ValueError("embedded model archive retention refuses linked directories")
    directory.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="embedded-", suffix=".zip", dir=directory)
    target = Path(name)
    digest = hashlib.sha256()
    try:
        try:
            source_fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        except BaseException:
            os.close(fd)
            raise
        with os.fdopen(source_fd, "rb") as incoming, os.fdopen(fd, "wb") as outgoing:
            before = os.fstat(incoming.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_TOTAL_BYTES:
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
        if expected_hash is not None and digest.hexdigest() != expected_hash:
            raise ValueError("selected combined archive hash mismatch")
        entry = target.stat()
        return {"path": str(target), "sha256": digest.hexdigest(),
                "identity": [entry.st_dev, entry.st_ino, entry.st_size, entry.st_mtime_ns]}
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def cleanup(root, proof, *, preserve=None):
    """Remove only the unchanged retained archive described by this invocation."""
    import os
    from pathlib import Path
    if not isinstance(proof, dict) or proof == preserve:
        return False
    path = Path(proof.get("path", ""))
    directory = Path(root).resolve() / ".wavefoundry" / "upgrade-assets"
    if path.parent != directory or not path.name.startswith("embedded-") or directory.is_symlink() or directory.parent.is_symlink():
        return False
    try:
        entry = path.lstat()
        identity = [entry.st_dev, entry.st_ino, entry.st_size, entry.st_mtime_ns]
        if not stat.S_ISREG(entry.st_mode) or entry.st_nlink != 1 or identity != proof.get("identity"):
            return False
        validate_retained(root, proof)
        descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            checked = os.stat(path.name, dir_fd=descriptor, follow_symlinks=False)
            if [checked.st_dev, checked.st_ino, checked.st_size, checked.st_mtime_ns] != identity:
                return False
            os.unlink(path.name, dir_fd=descriptor)
        finally:
            os.close(descriptor)
        return True
    except FileNotFoundError:
        return True
    except (OSError, ValueError):
        return False


def validate_retained(root, proof):
    """Check the retained source binding before a resumed model handoff."""
    import os
    from pathlib import Path
    if not isinstance(proof, dict):
        raise ValueError("retained combined archive proof is missing")
    path = Path(proof.get("path", ""))
    directory = Path(root).resolve() / ".wavefoundry/upgrade-assets"
    if (path.parent != directory or not path.name.startswith("embedded-")
            or directory.is_symlink() or directory.parent.is_symlink()):
        raise ValueError("retained combined archive path is invalid")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(fd, "rb") as source:
        before = os.fstat(source.fileno())
        identity = [before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns]
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_size > MAX_TOTAL_BYTES or identity != proof.get("identity")):
            raise ValueError("retained combined archive identity changed")
        digest = hashlib.sha256()
        while block := source.read(1024 * 1024):
            digest.update(block)
        after = os.fstat(source.fileno())
        if identity != [after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns] or digest.hexdigest() != proof.get("sha256"):
            raise ValueError("retained combined archive bytes changed")
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
