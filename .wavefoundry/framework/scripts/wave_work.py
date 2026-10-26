"""Disposable wave work, with identity-bound ownership and advisory failures.

Callers serialize ``ensure_work`` and ``cleanup_work`` with the existing
lifecycle/publication transaction. Reads never create files. Cleanup requires
the generation captured before publishing closure; it cannot infer authority
from whatever directory happens to exist afterward. This is cooperative local
housekeeping, not a sandbox against processes with repository write access.
"""
from __future__ import annotations

import errno
import base64
import hashlib
import json
import os
import re
import stat
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Mapping

from contained_files import open_contained_dir, relative_parts, _is_link_metadata
import vocabulary_profile

WORK_ROOT = Path(".wavefoundry/work")
OWNER_FILE = ".owner.json"
SNAPSHOT_MAX_BYTES = 2 * 1024 * 1024
_SAFE_DELETE = (
    hasattr(os, "O_DIRECTORY") and hasattr(os, "O_NOFOLLOW")
    and {os.open, os.stat, os.mkdir, os.unlink, os.rmdir, os.rename} <= os.supports_dir_fd
    and os.listdir in os.supports_fd
)
_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)


class _Refused(Exception):
    pass


def _checkpoint(stage: str) -> None:
    """Test seam immediately before identity-sensitive operations."""


def _identity(info) -> list[int]:
    return [info.st_dev, info.st_ino]


def _same(left, right) -> bool:
    return _identity(left) == _identity(right)


def _target(root, wave_md) -> tuple[Path, str, str]:
    # Accept the explicitly configured root spelling (for example /var on
    # macOS) as well as its resolved prefix. Preserve the lexical tail so
    # in-repository links are still judged by the no-follow walk below.
    parts = relative_parts(root, wave_md)
    root = Path(root).resolve(strict=True)
    if len(parts) < 2 or parts[-1] != vocabulary_profile.RECORD_FILENAME:
        raise _Refused("wave_record_invalid")
    # The lifecycle resolver supplies the canonical wave record, not caller ID
    # text. Check its lexical parents as well: resolving alone would hide links.
    fd = open_contained_dir(root, parts[:-1], refuse_reparse=True)
    try:
        info = os.stat(parts[-1], dir_fd=fd, follow_symlinks=False) if fd is not None else os.lstat(root.joinpath(*parts))
        if _is_link_metadata(info) or not stat.S_ISREG(info.st_mode):
            raise _Refused("wave_record_invalid")
    finally:
        if fd is not None:
            os.close(fd)
    key = parts[-2].split(" ", 1)[0]
    if not re.fullmatch(r"[0-9a-z]{5,12}", key):
        raise _Refused("wave_id_invalid")
    return root, "/".join(parts), key


def _result(key: str | None, *, available=False, **extra) -> dict:
    return {"path": (WORK_ROOT / key).as_posix() if key else None,
            "available": available, **extra}


def _failure(key, exc, *, outcome=None) -> dict:
    notice = str(exc) if isinstance(exc, _Refused) else "work_io_failed"
    if isinstance(exc, OSError) and exc.errno:
        notice += ":" + errno.errorcode.get(exc.errno, "io_error")
    return _result(key, notice=notice, **({"outcome": outcome} if outcome else {}))


@contextmanager
def _parent(root: Path, *, create=False):
    """Pin every lexical component, never following links, including parents."""
    if not _SAFE_DELETE:
        raise _Refused("safe_work_io_unsupported; work preserved")
    fd = os.open(root, _FLAGS)
    identities = [_identity(os.fstat(fd))]
    try:
        for name in WORK_ROOT.parts:
            if create:
                try:
                    os.mkdir(name, mode=0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            child = os.open(name, _FLAGS, dir_fd=fd)
            os.close(fd)
            fd = child
            identities.append(_identity(os.fstat(fd)))
        yield fd, identities
    finally:
        os.close(fd)


def _anchor(root: Path, identities: list, parent_fd: int) -> None:
    with _parent(root) as (fresh, current):
        if current != identities or not _same(os.fstat(fresh), os.fstat(parent_fd)):
            raise _Refused("work_parent_changed; work preserved")


def _entry(parent_fd: int, name: str, expected) -> None:
    info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if _is_link_metadata(info) or not _same(info, expected):
        raise _Refused("work_identity_changed; work preserved")


def _read_owner(fd: int, root: Path, wave: str, directory) -> dict:
    owner_fd = os.open(OWNER_FILE, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0), dir_fd=fd)
    try:
        info = os.fstat(owner_fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 4096:
            raise _Refused("work_ownership_unproven; work preserved")
        raw = os.read(owner_fd, 4097)
        owner = json.loads(raw)
    except (ValueError, UnicodeError):
        raise _Refused("work_ownership_unproven; work preserved") from None
    finally:
        os.close(owner_fd)
    if (not isinstance(owner, dict) or owner.get("schema") != 1
            or owner.get("repository") != str(root) or owner.get("wave") != wave
            or owner.get("directory") != _identity(directory)
            or not isinstance(owner.get("generation"), str)
            or not re.fullmatch(r"[0-9a-f]{32}", owner["generation"])):
        raise _Refused("work_ownership_unproven; work preserved")
    return owner


def _write_owner(fd: int, owner: dict, *, replace=False) -> None:
    name = ".owner-" + uuid.uuid4().hex + ".tmp" if replace else OWNER_FILE
    out = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    try:
        with os.fdopen(out, "wb") as stream:
            stream.write(json.dumps(owner, sort_keys=True).encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            os.rename(name, OWNER_FILE, src_dir_fd=fd, dst_dir_fd=fd)
    finally:
        if replace:
            try:
                os.unlink(name, dir_fd=fd)
            except FileNotFoundError:
                pass


def describe_work(root, wave_md) -> dict:
    """Return a verified shared path/generation, without creating anything."""
    key = None
    try:
        root, wave, key = _target(root, wave_md)
        with _parent(root) as (parent, identities):
            fd = os.open(key, _FLAGS, dir_fd=parent)
            try:
                directory = os.fstat(fd)
                owner = _read_owner(fd, root, wave, directory)
                _anchor(root, identities, parent)
                _entry(parent, key, directory)
                return _result(key, available=True, generation=owner["generation"])
            finally:
                os.close(fd)
    except FileNotFoundError:
        return _result(key, notice="work_missing")
    except (OSError, ValueError, RuntimeError, _Refused) as exc:
        return _failure(key, exc)


def ensure_work(root, wave_md, *, reopen=False) -> dict:
    """Lazily establish ownership; reopen rotates a verified retained generation.

    Caller holds the lifecycle/publication boundary. Existing unowned work is
    preserved even when empty; a failed ownership write never adopts it later.
    """
    key = None
    try:
        root, wave, key = _target(root, wave_md)
        with _parent(root, create=True) as (parent, identities):
            created = False
            try:
                os.mkdir(key, mode=0o700, dir_fd=parent)
                created = True
                created_identity = os.stat(key, dir_fd=parent, follow_symlinks=False)
                _checkpoint("created")
            except FileExistsError:
                pass
            fd = os.open(key, _FLAGS, dir_fd=parent)
            try:
                directory = os.fstat(fd)
                if created and not _same(created_identity, directory):
                    raise _Refused("work_identity_changed; work preserved")
                owner = ({"schema": 1, "repository": str(root), "wave": wave,
                          "directory": _identity(directory), "generation": uuid.uuid4().hex}
                         if created else _read_owner(fd, root, wave, directory))
                _checkpoint("ensure")
                _anchor(root, identities, parent)
                _entry(parent, key, directory)
                if created:
                    _write_owner(fd, owner)
                elif reopen:
                    owner["generation"] = uuid.uuid4().hex
                    _write_owner(fd, owner, replace=True)
                _anchor(root, identities, parent)
                _entry(parent, key, directory)
                return _result(key, available=True, generation=owner["generation"],
                               **({"notice": "reopened_generation; retained work preserved"}
                                  if reopen and not created else {}))
            finally:
                os.close(fd)
    except (OSError, ValueError, RuntimeError, _Refused) as exc:
        return _failure(key, exc)


def _empty_directory(fd: int, verify, *, skip_owner=False) -> None:
    """Remove descendants relative to pinned descriptors, never link targets."""
    for name in os.listdir(fd):
        if skip_owner and name == OWNER_FILE:
            continue
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        # A link is disposable as an entry, but never opened or traversed.
        if stat.S_ISDIR(info.st_mode) and not _is_link_metadata(info):
            if info.st_dev != os.fstat(fd).st_dev:
                raise _Refused("work_filesystem_changed; work preserved")
            child = os.open(name, _FLAGS, dir_fd=fd)
            try:
                if not _same(info, os.fstat(child)):
                    raise _Refused("work_identity_changed; work preserved")
                def verify_child():
                    verify()
                    _entry(fd, name, info)
                _empty_directory(child, verify_child)
                _checkpoint("rmdir_child")
                verify_child()
                os.rmdir(name, dir_fd=fd)
            finally:
                os.close(child)
        else:
            _checkpoint("unlink")
            verify()
            current = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if not _same(info, current):
                raise _Refused("work_identity_changed; work preserved")
            os.unlink(name, dir_fd=fd)


def cleanup_work(root, wave_md, *, expected_generation: str | None) -> dict:
    """Best-effort post-close cleanup. Unknown/stale generations retain work."""
    key = None
    try:
        root, wave, key = _target(root, wave_md)
        if not _SAFE_DELETE:
            # Absence needs no destructive host capability. Inspect lexical
            # parents only; never resolve a symlink to decide it is absent.
            current = root
            for name in (*WORK_ROOT.parts, key):
                current = current / name
                try:
                    info = os.lstat(current)
                except FileNotFoundError:
                    return _result(key, outcome="absent")
                if _is_link_metadata(info) or not stat.S_ISDIR(info.st_mode):
                    raise _Refused("safe_work_io_unsupported; work preserved")
            raise _Refused("safe_work_io_unsupported; work preserved")
        with _parent(root) as (parent, identities):
            fd = os.open(key, _FLAGS, dir_fd=parent)
            try:
                directory = os.fstat(fd)
                owner = _read_owner(fd, root, wave, directory)
                if expected_generation is None or owner["generation"] != expected_generation:
                    raise _Refused("cleanup_generation_unproven; work preserved")
                def verify():
                    _anchor(root, identities, parent)
                    _entry(parent, key, directory)
                    if _read_owner(fd, root, wave, directory)["generation"] != expected_generation:
                        raise _Refused("cleanup_generation_changed; work preserved")
                _checkpoint("cleanup")
                verify()
                _empty_directory(fd, verify, skip_owner=True)
                _checkpoint("rmdir")
                verify()
                os.unlink(OWNER_FILE, dir_fd=fd)
                try:
                    _anchor(root, identities, parent)
                    _entry(parent, key, directory)
                    os.rmdir(key, dir_fd=parent)
                except OSError:
                    # Keep retry authority after a late partial-I/O failure.
                    _anchor(root, identities, parent)
                    _entry(parent, key, directory)
                    _write_owner(fd, owner)
                    raise
                return _result(key, outcome="removed")
            finally:
                os.close(fd)
    except FileNotFoundError:
        # A missing owner or disappearing child is uncertainty, not proof of
        # absence. Only an absent work directory is an idempotent success.
        try:
            if key is not None:
                with _parent(root) as (parent, _):
                    os.stat(key, dir_fd=parent, follow_symlinks=False)
                return _result(key, outcome="preserved", notice="work_ownership_unproven; work preserved")
        except FileNotFoundError:
            return _result(key, outcome="absent")
        except (OSError, _Refused) as exc:
            return _failure(key, exc, outcome="preserved")
        return _result(key, outcome="preserved", notice="wave_record_unproven; work preserved")
    except (OSError, ValueError, RuntimeError, _Refused) as exc:
        return _failure(key, exc, outcome="preserved")


def _snapshot_normalizer() -> str:
    # Imported lazily: work-directory lifetime is independent of review policy.
    from review_policy import normalizer_signature
    return normalizer_signature()


def _snapshot_binding(receipt: Mapping) -> tuple[str, str, dict, dict]:
    if not isinstance(receipt, Mapping):
        raise _Refused("snapshot_receipt_invalid")
    receipt_id, digest = receipt.get("receipt_id"), receipt.get("policy_input_digest")
    if (not isinstance(receipt_id, str) or not re.fullmatch(r"review-policy-[0-9a-f]{20}", receipt_id)
            or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
        raise _Refused("snapshot_receipt_invalid")
    context = receipt.get("review_context")
    if not isinstance(context, Mapping) or type(context.get("version")) is not int or context["version"] != 1:
        raise _Refused("snapshot_metadata_unavailable; full review required")
    if context.get("normalizer_sha256") != _snapshot_normalizer():
        raise _Refused("snapshot_normalizer_mismatch; full review required")
    inputs = receipt.get("policy_inputs")
    if not isinstance(inputs, Mapping) or not isinstance(inputs.get("changes"), list):
        raise _Refused("snapshot_metadata_unavailable; full review required")
    changes = {}
    for entry in inputs["changes"]:
        if (not isinstance(entry, Mapping) or not isinstance(entry.get("change_id"), str)
                or not entry["change_id"] or not isinstance(entry.get("kind"), str)
                or not isinstance(entry.get("sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
                or entry["change_id"] in changes):
            raise _Refused("snapshot_receipt_invalid")
        changes[entry["change_id"]] = dict(entry)
    documents = context.get("documents")
    if not isinstance(documents, list):
        raise _Refused("snapshot_metadata_unavailable; full review required")
    raw_hashes = {}
    for entry in documents:
        if (not isinstance(entry, Mapping) or not isinstance(entry.get("change_id"), str)
                or entry["change_id"] in raw_hashes or not isinstance(entry.get("raw_sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", entry["raw_sha256"])):
            raise _Refused("snapshot_metadata_unavailable; full review required")
        raw_hashes[entry["change_id"]] = entry["raw_sha256"]
    if set(raw_hashes) != set(changes):
        raise _Refused("snapshot_document_identity_mismatch; full review required")
    return receipt_id, digest, changes, raw_hashes


def _verify_snapshot_documents(documents, changes, raw_hashes) -> dict[str, bytes]:
    from gardener_metadata import canonical_review_policy_body
    if not isinstance(documents, Mapping) or set(documents) != set(changes):
        raise _Refused("snapshot_document_identity_mismatch; full review required")
    total, verified = 0, {}
    for change_id, body in documents.items():
        if not isinstance(body, bytes):
            raise _Refused("snapshot_document_bytes_required")
        total += len(body)
        if total > SNAPSHOT_MAX_BYTES:
            raise _Refused("snapshot_oversized; full review required")
        if hashlib.sha256(body).hexdigest() != raw_hashes[change_id]:
            raise _Refused("snapshot_raw_integrity_mismatch; full review required")
        if hashlib.sha256(canonical_review_policy_body(body)).hexdigest() != changes[change_id]["sha256"]:
            raise _Refused("snapshot_canonical_integrity_mismatch; full review required")
        verified[change_id] = body
    return verified


@contextmanager
def _snapshot_directory(root: Path, wave: str, key: str, *, create=False):
    with _parent(root) as (parent, identities):
        fd = os.open(key, _FLAGS, dir_fd=parent)
        try:
            directory = os.fstat(fd)
            generation = _read_owner(fd, root, wave, directory)["generation"]
            def verify_work():
                _anchor(root, identities, parent)
                _entry(parent, key, directory)
                if _read_owner(fd, root, wave, directory)["generation"] != generation:
                    raise _Refused("snapshot_generation_changed; full review required")
            verify_work()
            if create:
                try:
                    os.mkdir("receipts", mode=0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            receipts_fd = os.open("receipts", _FLAGS, dir_fd=fd)
            try:
                receipts_identity = os.fstat(receipts_fd)
                def verify():
                    verify_work()
                    _entry(fd, "receipts", receipts_identity)
                verify()
                yield receipts_fd, verify
            finally:
                os.close(receipts_fd)
        finally:
            os.close(fd)


def _snapshot_result(key, receipt_id, *, available=False, notice=None, documents=None) -> dict:
    result = {"available": available, "path": (
        (WORK_ROOT / key / "receipts" / (receipt_id + ".json")).as_posix()
        if key and receipt_id else None)}
    if notice is not None:
        result["notice"] = notice
    if documents is not None:
        result["documents"] = documents
    return result


def _snapshot_failure(key, receipt_id, exc) -> dict:
    notice = str(exc) if isinstance(exc, _Refused) else "snapshot_unavailable; full review required"
    if isinstance(exc, OSError) and exc.errno:
        notice += ":" + errno.errorcode.get(exc.errno, "io_error")
    return _snapshot_result(key, receipt_id, notice=notice)


def publish_snapshot(root, wave_md, receipt: Mapping, documents: Mapping[str, bytes]) -> dict:
    """Publish exact reviewed bytes ONCE, after the caller commits a new receipt.

    The durable ledger supplies receipt membership and raw hashes. Call only on
    a newly appended receipt, never to reconstruct an old missing baseline on
    retry. Publication is exclusive and immutable; failures remain advisory.
    Both serialized JSON and decoded documents are bounded to two MiB.
    """
    key = receipt_id = None
    try:
        root, wave, key = _target(root, wave_md)
        receipt_id, digest, changes, raw_hashes = _snapshot_binding(receipt)
        documents = _verify_snapshot_documents(documents, changes, raw_hashes)
        payload = {"version": 1, "receipt_id": receipt_id, "policy_input_digest": digest,
                   "normalizer_sha256": receipt["review_context"]["normalizer_sha256"],
                   "documents": {change_id: base64.b64encode(body).decode("ascii")
                                 for change_id, body in documents.items()}}
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(raw) > SNAPSHOT_MAX_BYTES:
            raise _Refused("snapshot_oversized; full review required")
        if os.link not in os.supports_dir_fd:
            raise _Refused("safe_snapshot_publication_unsupported; full review required")
        established = ensure_work(root, wave_md)
        if not established["available"]:
            raise _Refused("snapshot_work_unavailable; full review required")
        with _snapshot_directory(root, wave, key, create=True) as (fd, verify):
            temporary = ".snapshot-" + uuid.uuid4().hex + ".tmp"
            out = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
            try:
                with os.fdopen(out, "wb") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                _checkpoint("snapshot_publish")
                verify()
                # link is an atomic exclusive publication; replace would allow
                # a retry to overwrite the baseline for an existing receipt.
                os.link(temporary, receipt_id + ".json", src_dir_fd=fd, dst_dir_fd=fd,
                        follow_symlinks=False)
                verify()
            finally:
                os.unlink(temporary, dir_fd=fd)
        return _snapshot_result(key, receipt_id, available=True)
    except FileExistsError:
        return _snapshot_result(key, receipt_id, notice="snapshot_exists; immutable baseline preserved")
    except (OSError, ValueError, RuntimeError, ImportError, _Refused) as exc:
        return _snapshot_failure(key, receipt_id, exc)


def _unique_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def read_snapshot(root, wave_md, receipt: Mapping) -> dict:
    """Read verified bytes for an actual ledger receipt; never create a baseline."""
    key = receipt_id = None
    try:
        root, wave, key = _target(root, wave_md)
        receipt_id, digest, changes, raw_hashes = _snapshot_binding(receipt)
        with _snapshot_directory(root, wave, key) as (fd, verify):
            name = receipt_id + ".json"
            source = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0), dir_fd=fd)
            try:
                info = os.fstat(source)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise _Refused("snapshot_file_unproven; full review required")
                if info.st_size > SNAPSHOT_MAX_BYTES:
                    raise _Refused("snapshot_oversized; full review required")
                chunks, count = [], 0
                while True:
                    chunk = os.read(source, min(65536, SNAPSHOT_MAX_BYTES + 1 - count))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    count += len(chunk)
                    if count > SNAPSHOT_MAX_BYTES:
                        raise _Refused("snapshot_oversized; full review required")
                payload = json.loads(b"".join(chunks), object_pairs_hook=_unique_json)
                if (not isinstance(payload, dict)
                        or set(payload) != {"version", "receipt_id", "policy_input_digest", "normalizer_sha256", "documents"}
                        or type(payload["version"]) is not int or payload["version"] != 1
                        or payload["receipt_id"] != receipt_id or payload["policy_input_digest"] != digest
                        or payload["normalizer_sha256"] != receipt["review_context"]["normalizer_sha256"]
                        or not isinstance(payload["documents"], dict)):
                    raise _Refused("snapshot_receipt_binding_mismatch; full review required")
                documents = {}
                for change_id, encoded in payload["documents"].items():
                    if not isinstance(encoded, str):
                        raise _Refused("snapshot_document_encoding_invalid; full review required")
                    documents[change_id] = base64.b64decode(encoded, validate=True)
                documents = _verify_snapshot_documents(documents, changes, raw_hashes)
                _checkpoint("snapshot_read")
                verify()
                _entry(fd, name, info)
                return _snapshot_result(key, receipt_id, available=True, documents=documents)
            finally:
                os.close(source)
    except (OSError, ValueError, RuntimeError, ImportError, _Refused) as exc:
        return _snapshot_failure(key, receipt_id, exc)
