"""The disposable work area, with identity-bound ownership and advisory failures.

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
from storage_identity import compare_identity
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
    if (not isinstance(owner, dict) or type(owner.get("schema")) is not int
            or owner["schema"] not in (1, 2) or owner.get("wave") != wave
            or not isinstance(owner.get("generation"), str)
            or not re.fullmatch(r"[0-9a-f]{32}", owner["generation"])):
        raise _Refused("work_ownership_unproven; work preserved")
    repository = owner.get("repository")
    if not isinstance(repository, str) or not Path(repository).is_absolute():
        raise _Refused("work_ownership_unproven; work preserved")
    if owner["schema"] == 2:
        # The recorded spelling is a historical locator; the root identity
        # keeps work bound to this repository after a same-filesystem rename.
        _persisted_identity(owner.get("repository_directory"), os.stat(root))
    elif repository != str(root):
        # Legacy records have no persisted root identity. An existing alias
        # must prove it names this actual directory, without case folding.
        try:
            same_root = _same(os.stat(repository), os.stat(root))
        except OSError:
            same_root = False
        if not same_root:
            raise _Refused("work_repository_unproven; work preserved; move retained work aside before retrying")
    recorded = owner.get("directory")
    _persisted_identity(recorded, directory)
    return owner


def _persisted_identity(recorded, directory) -> None:
    if (not isinstance(recorded, list) or len(recorded) != 2
            or not all(type(value) is int and value >= 0 for value in recorded)
            or recorded[1] <= 0 or directory.st_ino <= 0):
        raise _Refused("work_ownership_unproven; work preserved")
    # The caller binds the owned role. Persisted device numbers are history;
    # fresh descriptor/path comparisons within this operation remain strict.
    comparison = compare_identity(
        {"device": recorded[0], "inode": recorded[1]},
        {"device": directory.st_dev, "inode": directory.st_ino},
    )
    if not comparison["matches"] or comparison["basis"] != "path+inode":
        raise _Refused("work_ownership_unproven; work preserved")


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
                owner = ({"schema": 2, "repository": str(root), "wave": wave,
                          "repository_directory": identities[0],
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


class _Progress:
    """What one deletion has removed, and the step it is attempting.

    ``removed`` counts entries unlinked or removed (files, links and emptied
    subdirectories; the owner file only when explicit cleanup removes it).
    ``entry`` is the folder-relative
    POSIX name of the entry in flight (``.`` is the folder itself) and
    ``operation`` is one of ``open``, ``stat``, ``unlink`` or ``rmdir``. After a
    failure they name the failing entry and step.
    """

    def __init__(self) -> None:
        self.removed = 0
        self.entry: str | None = None
        self.operation: str | None = None

    def at(self, entry: str, operation: str) -> None:
        self.entry, self.operation = entry, operation

    def done(self) -> None:
        self.removed += 1


def _errno_name(exc: BaseException) -> str:
    return errno.errorcode.get(getattr(exc, "errno", None) or 0, "io_error")


def display_name(name: str, limit: int = 80) -> str:
    """An untrusted directory entry name, escaped and bounded for display."""
    text = str(name).encode("unicode_escape", "backslashreplace").decode("ascii")
    return text if len(text) <= limit else text[:limit] + "..."


def _removal_failure(key, exc, progress: _Progress, **extra) -> dict:
    """``partially_removed`` after at least one removal, else ``preserved``,
    with the removed count and the failing entry, operation and errno."""
    result = _failure(key, exc, outcome="partially_removed" if progress.removed else "preserved")
    result["removed_entries"] = progress.removed
    if progress.entry is not None:
        result["failed_entry"] = display_name(progress.entry)
        result["failed_operation"] = progress.operation
    if isinstance(exc, OSError) and exc.errno:
        result["failed_errno"] = _errno_name(exc)
    return {**result, **extra}


def _empty_directory(fd: int, verify, *, skip_owner=False, progress: _Progress | None = None,
                     prefix: str = "") -> None:
    """Remove descendants relative to pinned descriptors, never link targets.

    ``progress`` (optional) counts removals and names the step in flight, so a
    caller can report a partial removal precisely after an exception.
    """
    progress = progress if progress is not None else _Progress()
    progress.at(prefix.rstrip("/") or ".", "open")
    for name in os.listdir(fd):
        if skip_owner and name == OWNER_FILE:
            continue
        rel = prefix + name
        progress.at(rel, "stat")
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        # A link is disposable as an entry, but never opened or traversed.
        if stat.S_ISDIR(info.st_mode) and not _is_link_metadata(info):
            if info.st_dev != os.fstat(fd).st_dev:
                raise _Refused("work_filesystem_changed; work preserved")
            progress.at(rel, "open")
            child = os.open(name, _FLAGS, dir_fd=fd)
            try:
                if not _same(info, os.fstat(child)):
                    raise _Refused("work_identity_changed; work preserved")
                def verify_child():
                    verify()
                    _entry(fd, name, info)
                _empty_directory(child, verify_child, progress=progress, prefix=rel + "/")
                progress.at(rel, "rmdir")
                _checkpoint("rmdir_child")
                verify_child()
                os.rmdir(name, dir_fd=fd)
                progress.done()
            finally:
                os.close(child)
        else:
            progress.at(rel, "unlink")
            _checkpoint("unlink")
            verify()
            current = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if not _same(info, current):
                raise _Refused("work_identity_changed; work preserved")
            os.unlink(name, dir_fd=fd)
            progress.done()


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
                progress = _Progress()
                try:
                    _empty_directory(fd, verify, skip_owner=True, progress=progress)
                    progress.at(OWNER_FILE, "unlink")
                    _checkpoint("rmdir")
                    verify()
                    os.unlink(OWNER_FILE, dir_fd=fd)
                except FileNotFoundError as exc:
                    # Nothing removed yet: the established "uncertain, not
                    # absent" handling below applies unchanged.
                    if not progress.removed:
                        raise
                    return _removal_failure(key, exc, progress)
                except (OSError, ValueError, RuntimeError, _Refused) as exc:
                    # The owner file is still present: retry authority is kept.
                    return _removal_failure(key, exc, progress)
                try:
                    progress.at(".", "rmdir")
                    _anchor(root, identities, parent)
                    _entry(parent, key, directory)
                    os.rmdir(key, dir_fd=parent)
                except (OSError, _Refused) as exc:
                    # Keep retry authority after any post-unlink failure. The
                    # retained descriptor names the owned directory wherever it
                    # now is, so restore first and re-check nothing beforehand.
                    # The outcome is "preserved" (or "partially_removed" when
                    # entries were removed first), never "absent"; the
                    # restored owner file is not a removed entry.
                    restore = {}
                    try:
                        _write_owner(fd, owner)
                    except OSError as restore_exc:
                        restore = {"owner_restore": "failed:" + errno.errorcode.get(
                            restore_exc.errno or 0, "io_error")}
                    return _removal_failure(key, exc, progress, **restore)
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


# ---------------------------------------------------------------------------
# Read-only reporting of the work root (change 23phc). Nothing below writes,
# creates a directory, opens a file payload other than a bounded owner file or
# record header, follows a link or reparse point, or crosses a device boundary.
# The explicit cleanup operation builds on ``inventory_work_root`` and
# ``classify_work_keys``; automatic close cleanup does not use them.
# ---------------------------------------------------------------------------

INVENTORY_ENTRY_LIMIT = 10_000
# Loose entries (plain files and links directly in the work root) listed by
# name; the count is never capped.
LOOSE_ENTRY_LIST_CAP = 20
WORK_KEY_PATTERN = re.compile(r"[0-9a-z]{5,12}")
LEFTOVER_STATES = frozenset({"closed", "completed", "archived", "not_found_in_checkout"})
UNCLASSIFIED_STATES = frozenset({"ambiguous", "unreadable"})
CLEANUP_TOOL = "wf_cleanup_work"
_RECORD_READ_LIMIT = 1024 * 1024
_STATUS_PATTERN = re.compile(r"^Status:\s+(\S+)", re.MULTILINE)
_OWNER_READ_BY_DESCRIPTOR = hasattr(os, "O_NOFOLLOW") and os.open in os.supports_dir_fd


def not_found_note() -> str:
    """The label every output attaches to ``not_found_in_checkout``."""
    return (f"no record in this checkout; the {vocabulary_profile.tier_noun('container')} "
            "may exist on another branch or checkout")


def _work_root_state(root: Path) -> tuple[bool, str | None]:
    """``(present, refusal)`` from a no-follow ``lstat`` of each work-root component.

    An absent component is an empty work root. A link, reparse point or
    non-directory gives ``work_root_link``; any other error ``unreadable:<errno>``.
    """
    current = Path(root)
    for name in WORK_ROOT.parts:
        current = current / name
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            return False, None
        except OSError as exc:
            return False, "unreadable:" + _errno_name(exc)
        if _is_link_metadata(info) or not stat.S_ISDIR(info.st_mode):
            return False, "work_root_link"
    return True, None


def _read_record_status(path: Path) -> str | None:
    """The record's ``Status:`` value, read without following a link; ``None``
    when the record is missing, not a regular file, unreadable or has no status."""
    try:
        info = os.lstat(path)
        if _is_link_metadata(info) or not stat.S_ISREG(info.st_mode):
            return None
        if hasattr(os, "O_NOFOLLOW"):
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))
            with os.fdopen(fd, "rb") as stream:
                raw = stream.read(_RECORD_READ_LIMIT)
        else:
            with open(path, "rb") as stream:
                raw = stream.read(_RECORD_READ_LIMIT)
    except OSError:
        return None
    match = _STATUS_PATTERN.search(raw.decode("utf-8", errors="replace"))
    return match.group(1) if match else None


def _repo_rel(root: Path, path: Path) -> str:
    try:
        return Path(path).relative_to(root).as_posix()
    except ValueError:
        return Path(path).name


def classify_work_keys(root, keys) -> dict[str, dict]:
    """Map each work key to its wave state, without importing the server.

    Returns ``{key: {"state", "record", "note"}}``. ``state`` is the live
    record's status (for example ``active`` or ``closed``), ``archived``,
    ``not_found_in_checkout``, ``ambiguous`` or ``unreadable``. ``record`` is
    the repository-relative record path when exactly one live or archived
    record matched, and ``live`` says whether it is under the live record root.

    A key matches a candidate folder under the live or archive record root of
    the current vocabulary profile whose name's leading id equals the key, as
    ``_target`` derives it. ``not_found_in_checkout`` requires that no
    candidate folder exists at all; a candidate whose record file is missing,
    a link or not a regular file, or a record root that refuses, is
    ``unreadable``. Never raises.
    """
    import record_paths

    root = Path(root)
    keys = list(dict.fromkeys(keys))
    try:
        roots = record_paths.load_record_roots(root)
        live = record_paths.walk_wave_candidates(root, roots)
        archive: list[Path] = []
        archive_record = vocabulary_profile.archive_profile().RECORD_FILENAME
        if roots.archive is not None and record_paths.record_root_is_dir(roots.archive, roots.archive_rel or ""):
            archive = record_paths.walk_wave_candidates(root, roots, base=roots.archive,
                                                        record_filename=archive_record)
    except Exception:  # noqa: BLE001 - reporting never raises; the state says why
        return {key: {"state": "unreadable", "record": None, "live": False,
                      "note": "the record roots could not be read"} for key in keys}

    def index(candidates):
        found: dict[str, list[Path]] = {}
        for candidate in candidates:
            found.setdefault(candidate.name.split(" ", 1)[0], []).append(candidate)
        return found

    live_by_key, archive_by_key = index(live), index(archive)
    out: dict[str, dict] = {}
    for key in keys:
        for matches, record_name, is_live in ((live_by_key.get(key, []), vocabulary_profile.RECORD_FILENAME, True),
                                              (archive_by_key.get(key, []), archive_record, False)):
            if not matches:
                continue
            if len(matches) > 1:
                out[key] = {"state": "ambiguous", "record": None, "live": is_live,
                            "note": "the id matches " + str(len(matches)) + " folders"}
                break
            folder = matches[0]
            record = folder / record_name
            rel = _repo_rel(root, record)
            try:
                linked = _is_link_metadata(os.lstat(folder))
            except OSError:
                linked = True
            status = None if linked else _read_record_status(record)
            if status is None:
                out[key] = {"state": "unreadable", "record": rel, "live": is_live,
                            "note": "the record file is missing, a link, not a regular file or has no status"}
            else:
                out[key] = {"state": status if is_live else "archived", "record": rel, "live": is_live,
                            "note": ""}
            break
        else:
            out[key] = {"state": "not_found_in_checkout", "record": None, "live": False,
                        "note": not_found_note()}
    return out


def _owner_bytes(folder: Path, directory) -> bytes:
    """The owner file's bytes, bounded and never following a link or blocking."""
    if _OWNER_READ_BY_DESCRIPTOR:
        fd = os.open(folder, _FLAGS)
        try:
            if not _same(os.fstat(fd), directory):
                raise _Refused("work_identity_changed")
            owner_fd = os.open(OWNER_FILE, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0), dir_fd=fd)
            try:
                info = os.fstat(owner_fd)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 4096:
                    raise _Refused("work_ownership_unproven")
                return os.read(owner_fd, 4097)
            finally:
                os.close(owner_fd)
        finally:
            os.close(fd)
    # Native Windows: no descriptor-relative open. An lstat showing a regular,
    # non-reparse file, then a bounded read by path.
    path = folder / OWNER_FILE
    info = os.lstat(path)
    if _is_link_metadata(info) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 4096:
        raise _Refused("work_ownership_unproven")
    with open(path, "rb") as stream:
        return stream.read(4097)


def _owner_state(folder: Path, directory, live_record: str | None) -> str:
    """``valid``, ``missing`` or ``invalid`` from structural owner checks.

    The ``wave`` field is compared with ``live_record`` only when the key has
    a live record; the ``repository`` field is checked as text and never
    opened or stat'ed.
    """
    try:
        raw = _owner_bytes(folder, directory)
    except FileNotFoundError:
        return "missing"
    except (OSError, _Refused):
        return "invalid"
    try:
        owner = json.loads(raw)
    except (ValueError, UnicodeError):
        return "invalid"
    if (not isinstance(owner, dict) or type(owner.get("schema")) is not int
            or owner["schema"] not in (1, 2) or not isinstance(owner.get("wave"), str)
            or not isinstance(owner.get("generation"), str)
            or not re.fullmatch(r"[0-9a-f]{32}", owner["generation"])
            or not isinstance(owner.get("repository"), str)
            or not Path(owner["repository"]).is_absolute()):
        return "invalid"
    try:
        _persisted_identity(owner.get("directory"), directory)
    except _Refused:
        return "invalid"
    if live_record is not None and owner["wave"] != live_record:
        return "invalid"
    return "valid"


class _Budget:
    def __init__(self, limit: int) -> None:
        self.limit = max(0, int(limit))
        self.visited = 0

    def take(self) -> bool:
        if self.visited >= self.limit:
            return False
        self.visited += 1
        return True


def _stat_dir(path: Path, entry_info):
    # DirEntry metadata on native Windows carries no device or inode numbers.
    return os.lstat(path) if os.name == "nt" else entry_info


def _measure(folder: Path, folder_info, budget: _Budget) -> tuple[int, int, str | None]:
    """``(entries, logical bytes, reason)``; ``reason`` is ``None`` when complete."""
    entries = size = 0
    reason: str | None = None
    stack = [(folder, folder_info.st_dev)]
    while stack:
        directory, device = stack.pop()
        try:
            with os.scandir(directory) as listing:
                for entry in listing:
                    if not budget.take():
                        return entries, size, "entry_limit"
                    entries += 1
                    try:
                        info = entry.stat(follow_symlinks=False)
                    except OSError as exc:
                        reason = reason or "unreadable:" + _errno_name(exc)
                        continue
                    if _is_link_metadata(info):
                        continue
                    if stat.S_ISDIR(info.st_mode):
                        child = Path(entry.path)
                        try:
                            full = _stat_dir(child, info)
                        except OSError as exc:
                            reason = reason or "unreadable:" + _errno_name(exc)
                            continue
                        if _is_link_metadata(full) or not stat.S_ISDIR(full.st_mode):
                            continue
                        if full.st_dev != device:
                            reason = reason or "other_filesystem"
                            continue
                        stack.append((child, full.st_dev))
                    elif stat.S_ISREG(info.st_mode):
                        size += info.st_size
        except OSError as exc:
            reason = reason or "unreadable:" + _errno_name(exc)
    return entries, size, reason


def inventory_work_root(root, *, keys=None, measure: bool = True, entry_limit: int | None = None) -> dict:
    """Read-only inventory of ``.wavefoundry/work/``'s immediate child folders.

    ``keys`` restricts the folders reported to those exact names (byte-exact
    against the listing). ``measure=False`` lists and classifies only: no owner
    read and no sizing walk (``ownership``, ``entries`` and ``bytes`` are
    ``None``). Every listed or walked entry counts against ``entry_limit``
    (default ``INVENTORY_ENTRY_LIMIT``) for the whole call; a folder the bound
    or an unreadable directory stopped reports ``complete: false`` with
    ``reason`` ``entry_limit`` or ``unreadable:<errno>`` (``other_filesystem``
    when a directory on another device was not entered), and its counts are
    lower bounds. Logical bytes sum regular-file ``st_size`` and do not promise
    reclaimable space.

    Loose entries, the plain files and links directly in the work root, are
    reported from the same listing and count against the same bound:
    ``loose_count`` is their total (a lower bound when ``complete`` is false
    because the listing stopped) and ``loose_entries`` lists at most
    ``LOOSE_ENTRY_LIST_CAP`` of them as ``{"name", "kind", "bytes"}``, files
    largest first and then links. ``kind`` is ``file`` (any entry that is not a
    directory or link) or ``link`` (a symbolic link, junction or other reparse
    point, never followed: ``bytes`` is ``None``). A file's ``bytes`` is its
    ``st_size`` from the no-follow listing metadata, present even when
    ``measure`` is false. An entry whose metadata cannot be read is not listed
    and makes the result incomplete. ``keys`` does not restrict them.

    Returns ``{"work_root", "present", "complete", "reason", "entry_limit",
    "entries_visited", "measured", "leftovers", "live_unowned",
    "unclassified", "live_owned", "totals", "next_action", "loose_count",
    "loose_entries"}``; each folder entry
    is ``{"key", "path", "state", "state_note", "record", "ownership",
    "entries", "bytes", "complete", "reason"}``. Leftovers are folders whose
    state is ``closed``, ``completed``, ``archived`` or
    ``not_found_in_checkout``; live unowned are live not-closed folders whose
    ownership is ``missing`` or ``invalid``; unclassified are ``ambiguous`` and
    ``unreadable`` folders. Valid live folders are only counted. Never raises
    for filesystem conditions and writes nothing.
    """
    return _inventory(root, keys=keys, measure=measure, entry_limit=entry_limit)[0]


def inventory_work_folder(root, key: str, *, entry_limit: int | None = None) -> dict | None:
    """The inventory entry of one work folder whatever its category (including
    a valid live folder, which ``inventory_work_root`` only counts), or
    ``None`` when no such immediate child directory is listed. The work-root
    link check applies: a linked work root returns ``None``."""
    items = _inventory(root, keys=[key], measure=True, entry_limit=entry_limit)[1]
    return items[0] if items else None


def _inventory(root, *, keys, measure, entry_limit) -> tuple[dict, list[dict]]:
    root = Path(root)
    limit = INVENTORY_ENTRY_LIMIT if entry_limit is None else entry_limit
    items: list[dict] = []
    result: dict = {
        "work_root": WORK_ROOT.as_posix(), "present": False, "complete": True, "reason": None,
        "entry_limit": limit, "entries_visited": 0, "measured": measure,
        "leftovers": [], "live_unowned": [], "unclassified": [], "live_owned": 0,
        "totals": {"folders": 0, "entries": 0, "bytes": 0, "leftover_bytes": 0},
        "next_action": "", "loose_count": 0, "loose_entries": [],
    }
    present, refusal = _work_root_state(root)
    if refusal is not None:
        result.update(complete=False, reason=refusal)
        return result, items
    if not present:
        return result, items
    result["present"] = True
    work = root / WORK_ROOT
    budget = _Budget(limit)
    names: list[str] = []
    loose: list[dict] = []
    try:
        work_info = os.lstat(work)
        with os.scandir(work) as listing:
            for entry in listing:
                if not budget.take():
                    result.update(complete=False, reason="entry_limit")
                    break
                try:
                    info = entry.stat(follow_symlinks=False)
                except OSError as exc:
                    result.update(complete=False, reason=result["reason"] or "unreadable:" + _errno_name(exc))
                    continue
                if _is_link_metadata(info):
                    loose.append({"name": display_name(entry.name), "kind": "link", "bytes": None})
                    continue
                if not stat.S_ISDIR(info.st_mode):
                    loose.append({"name": display_name(entry.name), "kind": "file", "bytes": info.st_size})
                    continue
                names.append(entry.name)
    except OSError as exc:
        result.update(complete=False, reason="unreadable:" + _errno_name(exc))
        result["entries_visited"] = budget.visited
        _record_loose(result, loose)
        return result, items
    _record_loose(result, loose)
    names.sort()
    if keys is not None:
        wanted = set(keys)
        names = [name for name in names if name in wanted]
    states = classify_work_keys(root, names)
    for name in names:
        classified = states[name]
        folder = work / name
        item = {"key": display_name(name), "path": WORK_ROOT.as_posix() + "/" + display_name(name),
                "state": classified["state"],
                "state_note": classified["note"], "record": classified["record"],
                "ownership": None, "entries": None, "bytes": None, "complete": True, "reason": None}
        if measure:
            try:
                folder_info = os.lstat(folder)
            except OSError as exc:
                item.update(complete=False, reason="unreadable:" + _errno_name(exc), entries=0, bytes=0)
            else:
                live_record = classified["record"] if classified.get("live") else None
                item["ownership"] = _owner_state(folder, folder_info, live_record)
                if folder_info.st_dev != work_info.st_dev:
                    entries, size, reason = 0, 0, "other_filesystem"
                else:
                    entries, size, reason = _measure(folder, folder_info, budget)
                item.update(entries=entries, bytes=size, complete=reason is None, reason=reason)
            result["totals"]["entries"] += item["entries"]
            result["totals"]["bytes"] += item["bytes"]
            if not item["complete"]:
                result["complete"] = False
        result["totals"]["folders"] += 1
        items.append(item)
        state = item["state"]
        if state in LEFTOVER_STATES:
            result["leftovers"].append(item)
            result["totals"]["leftover_bytes"] += item["bytes"] or 0
        elif state in UNCLASSIFIED_STATES:
            result["unclassified"].append(item)
        elif item["ownership"] in ("missing", "invalid"):
            result["live_unowned"].append(item)
        else:
            result["live_owned"] += 1
    result["entries_visited"] = budget.visited
    if result["leftovers"]:
        result["next_action"] = retained_work_next_action(
            result["leftovers"][0]["key"] if len(result["leftovers"]) == 1 else None)
    return result, items


def _record_loose(result: dict, loose: list[dict]) -> None:
    """Files largest first (then by name), then links by name, capped."""
    loose.sort(key=lambda item: (item["kind"] != "file", -(item["bytes"] or 0), item["name"]))
    result["loose_count"] = len(loose)
    result["loose_entries"] = loose[:LOOSE_ENTRY_LIST_CAP]


def loose_entries_message(inventory: dict) -> str:
    """The ``work_root_loose_files`` advisory text, or ``""`` with none.

    Names come from the inventory, already escaped and bounded by
    ``display_name``. The text names no deleting tool and limits action to the
    file's author; any other file is left for the operator.
    """
    count = int(inventory.get("loose_count") or 0)
    if count <= 0:
        return ""
    entries = list(inventory.get("loose_entries") or [])
    shown = ", ".join(
        f"{item['name']} ({'link' if item['kind'] == 'link' else str(item['bytes']) + ' bytes'})"
        for item in entries
    ) + (f" and {count - len(entries)} more" if count > len(entries) else "")
    container = vocabulary_profile.tier_noun("container")
    bound = "" if inventory.get("complete", True) else " (a lower bound: the listing stopped early)"
    return (
        f"{count} loose file(s) or link(s) directly in {WORK_ROOT.as_posix()}/{bound}: {shown}. "
        f"Files written for a {container} belong inside {WORK_ROOT.as_posix()}/<{container}-id>/. "
        f"An agent that wrote one of these files for a {container} moves it into that {container}'s "
        f"folder while the {container} is open, or deletes it. Any other file, including one the agent "
        f"is not sure it wrote (a name that starts with a {container} id does not prove it), is left in place and reported to the operator, who decides. An agent "
        f"never moves a file it did not write into a {container}'s folder: close removes that folder "
        "with everything in it."
    )


def cleanup_tool_registered() -> bool:
    """Whether the explicit cleanup tool is in the tool roster of this tree.

    The single seam the next-action text uses, so guidance never names a tool
    that is not registered.
    """
    try:
        import mcp_tool_roster
        return CLEANUP_TOOL in mcp_tool_roster.TOOL_TIERS
    except Exception:  # noqa: BLE001 - absent or older roster: not registered
        return False


def retained_work_next_action(key: str | None = None) -> str:
    """The recovery step for retained or leftover work on this host."""
    if not _SAFE_DELETE:
        return ("This host cannot remove work safely (no descriptor-relative deletion); review the "
                "folder and remove it yourself once nothing in it is needed. wf_audit() lists it again.")
    if cleanup_tool_registered():
        target = key if key and WORK_KEY_PATTERN.fullmatch(key) else "<key>"
        return (f"Review it with wf_audit(), then preview removal with {CLEANUP_TOOL}(work_key='{target}') "
                "and apply only when the operator directs it.")
    return "Review it with wf_audit(), then remove the folder yourself once nothing in it is needed."


def work_key_for(root, wave_md) -> str | None:
    """The work key ``_target`` derives for a wave record, or ``None``."""
    try:
        return _target(root, wave_md)[2]
    except (OSError, ValueError, RuntimeError, _Refused):
        return None


def notice_reason(notice: str | None) -> str:
    """The stable reason token of a notice such as ``work_io_failed:EACCES``."""
    return str(notice or "").split(";", 1)[0].split(":", 1)[0].strip()


def describe_retained(root, key: str | None, cleanup: dict) -> dict:
    """``cleanup`` plus ``reason``, the folder's inventory and the next action."""
    detail = dict(cleanup)
    detail["reason"] = notice_reason(cleanup.get("notice")) or "work_preserved"
    detail.update(entries=None, bytes=None, complete=False, completeness_reason="not_measured")
    if key:
        folder = inventory_work_folder(root, key)
        if folder is not None:
            detail.update(entries=folder["entries"], bytes=folder["bytes"],
                          complete=folder["complete"], completeness_reason=folder["reason"])
    detail["next_action"] = retained_work_next_action(key)
    return detail


def find_work_path_citations(root, key: str, documents) -> dict:
    """Lines in ``documents`` that cite ``.wavefoundry/work/<key>``.

    ``documents`` is an iterable of ``(path, required)``; an absent optional
    document is skipped, while an absent required or any unreadable document
    makes ``coverage`` ``incomplete`` and is named in ``unreadable``. The
    match needs the key to end the path segment (a ``/``, the end of a token or
    punctuation follows), so another key's folder and the bare work-root text
    never match. Reads only; returns at most 50 hits.
    """
    root = Path(root)
    pattern = re.compile(re.escape(WORK_ROOT.as_posix() + "/" + key) + r"(?![0-9A-Za-z_-])")
    hits: list[dict] = []
    unreadable: list[str] = []
    for path, required in documents:
        path = Path(path)
        rel = _repo_rel(root, path)
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            if required:
                unreadable.append(rel)
            continue
        except (OSError, UnicodeError):
            unreadable.append(rel)
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if pattern.search(line) and len(hits) < 50:
                hits.append({"path": rel, "line": number})
    return {"key": key, "hits": hits, "coverage": "incomplete" if unreadable else "complete",
            "unreadable": unreadable}


# ---------------------------------------------------------------------------
# Extra files in a record folder (change 23p9t). Close reports every entry in
# the closing record's folder other than the record, its ledger and its
# admitted specs, with sizes and citation state. Reads directory metadata and
# the three kinds of text the caller passes; never reads an extra's content,
# never follows a link and never writes.
# ---------------------------------------------------------------------------

RECORD_EXTRAS_ENTRY_LIMIT = 10_000
RECORD_EXTRAS_LIST_CAP = 50
# Name characters: ASCII letters, digits, `_` and `-`. A `.` continues a path
# only when a name character follows it; `/` is a path character.
_NAME_CLASS = r"A-Za-z0-9_\-"


def _citation_pattern(target: str, folder_name: str) -> "re.Pattern[str]":
    """``target`` (a folder-relative forward-slash path) as cited text: it
    starts the text, follows a character that is neither a name nor a path
    character, or follows the record folder's own name and ``/`` (so the
    repository-relative form is cited); the next character is not a name
    character, and a ``.`` ends the path unless a name character follows."""
    left = rf"(?:(?<![{_NAME_CLASS}./])|(?<={re.escape(folder_name + '/')}))"
    right = rf"(?![{_NAME_CLASS}])(?!\.[{_NAME_CLASS}])"
    return re.compile(left + re.escape(target) + right)


def _name_pattern(name: str) -> "re.Pattern[str]":
    """A file name as a mention: the path rule, except that the name may also
    be the tail of another path (it may follow ``/`` or ``\\``)."""
    left = rf"(?<![{_NAME_CLASS}.])"
    right = rf"(?![{_NAME_CLASS}])(?!\.[{_NAME_CLASS}])"
    return re.compile(left + re.escape(name) + right)


def _cites(target: str, folder_name: str, texts, *, as_name: bool = False) -> bool:
    pattern = None
    for text in texts:
        if target not in text:  # cheap substring screen before the boundary rule
            continue
        pattern = pattern or (_name_pattern(target) if as_name else _citation_pattern(target, folder_name))
        if pattern.search(text):
            return True
    return False


def ledger_strings(ledger_text: str) -> list[str]:
    """The texts a ledger is matched against: for each JSON line, every string
    value at any depth, decoded (so ``\\n``, ``\\t``, ``\\"``, ``\\/`` and
    ``\\uXXXX`` escapes no longer hide a path); a line that does not parse is
    kept as raw text. Never raises."""
    texts: list[str] = []
    for line in (ledger_text or "").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except (ValueError, RecursionError):
            texts.append(line)
            continue
        stack = [value]
        while stack:
            item = stack.pop()
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict):
                stack.extend(item.values())
            elif isinstance(item, list):
                stack.extend(item)
    return texts


def record_citation_state(rel: str, folder_name: str, ledger_text, record_texts) -> dict:
    """Citation state of one folder-relative path, from exact text only.

    ``citation`` is ``cited_in_ledger`` when the ledger cites the path,
    ``cited_in_record`` when only the record or an admitted spec does, and
    ``not_cited`` otherwise. The ledger is matched against the decoded string
    values of its JSON lines (``ledger_text`` is the raw text, or the list
    ``ledger_strings`` returned for it); the record and spec texts are matched
    raw. ``name_in_ledger`` / ``name_in_record`` say the file name appears
    under the same boundary rule, also as the tail of another path;
    ``directory_in_ledger`` / ``directory_in_record`` say a containing
    directory's relative path and ``/`` appears as a path of its own. Neither
    kind of loose mention makes a file cited. Comparison is exact: backslashes
    or another letter case do not match."""
    record_texts = list(record_texts)
    ledger = ledger_strings(ledger_text) if isinstance(ledger_text, str) else list(ledger_text)
    parts = rel.split("/")
    name = parts[-1]
    directories = ["/".join(parts[:index]) + "/" for index in range(1, len(parts))]
    if _cites(rel, folder_name, ledger):
        citation = "cited_in_ledger"
    elif _cites(rel, folder_name, record_texts):
        citation = "cited_in_record"
    else:
        citation = "not_cited"
    return {
        "citation": citation,
        "name_in_ledger": _cites(name, folder_name, ledger, as_name=True),
        "name_in_record": _cites(name, folder_name, record_texts, as_name=True),
        "directory_in_ledger": any(_cites(d, folder_name, ledger) for d in directories),
        "directory_in_record": any(_cites(d, folder_name, record_texts) for d in directories),
    }


def _report_name(name: str) -> str:
    try:
        name.encode("utf-8")
    except UnicodeEncodeError:  # undecodable bytes in a POSIX name
        return display_name(name, limit=255)
    return name


def inventory_record_extras(folder, recognized, *, entry_limit: int | None = None) -> dict:
    """Read-only walk of a record folder for entries outside ``recognized``.

    ``recognized`` holds top-level names (the record file, the ledger and the
    admitted specs). Every other entry at any depth is an extra. Returns
    ``{"entries", "complete", "reason", "unreadable", "entries_visited",
    "entry_limit"}``; each entry is ``{"path", "bytes", "kind"}`` with a
    forward-slash folder-relative path and ``kind`` ``file``, ``link``,
    ``other`` or ``directory`` (an empty directory, so it stays visible).
    Every entry is examined with ``lstat``: a symbolic link, junction or other
    reparse point is one ``link`` entry sized by its own metadata and never
    traversed, and a directory on another device is not entered. Every listed
    entry counts against ``entry_limit``; reaching it stops the walk with
    ``complete: false`` and reason ``entry_limit``. An unreadable entry is
    named in ``unreadable`` (folder-relative) and makes coverage incomplete.
    Never raises for filesystem conditions.
    """
    folder = Path(folder)
    limit = RECORD_EXTRAS_ENTRY_LIMIT if entry_limit is None else entry_limit
    budget = _Budget(limit)
    recognized = set(recognized)
    entries: list[dict] = []
    unreadable: list[str] = []
    reason: str | None = None
    try:
        device = os.lstat(folder).st_dev
    except OSError as exc:
        return {"entries": [], "complete": False, "reason": "unreadable:" + _errno_name(exc),
                "unreadable": ["."], "entries_visited": 0, "entry_limit": limit}
    stack: list[tuple[Path, str]] = [(folder, "")]
    stopped = False
    while stack and not stopped:
        directory, prefix = stack.pop()
        children = 0
        try:
            with os.scandir(directory) as listing:
                for entry in listing:
                    if not prefix and entry.name in recognized:
                        continue
                    if not budget.take():
                        reason, stopped = "entry_limit", True
                        break
                    children += 1
                    rel = prefix + _report_name(entry.name)
                    try:
                        info = os.lstat(entry.path)
                    except OSError as exc:
                        reason = reason or "unreadable:" + _errno_name(exc)
                        unreadable.append(rel)
                        continue
                    if _is_link_metadata(info):
                        entries.append({"path": rel, "bytes": info.st_size, "kind": "link"})
                    elif stat.S_ISDIR(info.st_mode):
                        if info.st_dev != device:
                            reason = reason or "other_filesystem"
                            unreadable.append(rel)
                            continue
                        stack.append((Path(entry.path), rel + "/"))
                    elif stat.S_ISREG(info.st_mode):
                        entries.append({"path": rel, "bytes": info.st_size, "kind": "file"})
                    else:
                        entries.append({"path": rel, "bytes": 0, "kind": "other"})
        except OSError as exc:
            reason = reason or "unreadable:" + _errno_name(exc)
            unreadable.append(prefix.rstrip("/") or ".")
            continue
        if prefix and children == 0 and not stopped:
            entries.append({"path": prefix.rstrip("/"), "bytes": 0, "kind": "directory"})
    return {"entries": entries, "complete": reason is None, "reason": reason, "unreadable": unreadable,
            "entries_visited": budget.visited, "entry_limit": limit}


def record_extras_report(folder, recognized, ledger_text: str, record_texts, *,
                         folder_rel: str, unreadable_inputs=(), entry_limit: int | None = None,
                         list_cap: int = RECORD_EXTRAS_LIST_CAP) -> dict:
    """The ``record_extras_present`` detail for one record folder.

    Totals (``files``, ``bytes``, the count per citation state), coverage
    (``complete``, ``reason``, ``unreadable`` as repository-relative paths,
    ``entry_limit``), the per-file list largest first and capped at
    ``list_cap`` (``listed``, ``not_listed``), and per top-level directory
    totals (``directories``). ``unreadable_inputs`` names text inputs that
    could not be read; they make coverage incomplete. Reads no extra's
    content and never raises for filesystem conditions.
    """
    folder = Path(folder)
    walk = inventory_record_extras(folder, recognized, entry_limit=entry_limit)
    record_texts = list(record_texts)
    ledger = ledger_strings(ledger_text)  # decoded once for every file
    files: list[dict] = []
    for entry in walk["entries"]:
        files.append({**entry, **record_citation_state(entry["path"], folder.name, ledger, record_texts)})
    files.sort(key=lambda item: (-item["bytes"], item["path"]))
    counts = {state: sum(1 for item in files if item["citation"] == state)
              for state in ("cited_in_ledger", "cited_in_record", "not_cited")}
    directories: dict[str, dict] = {}
    for item in files:
        if "/" not in item["path"]:
            continue
        top = item["path"].split("/", 1)[0]
        group = directories.setdefault(top, {"path": top + "/", "files": 0, "bytes": 0, "not_cited": 0})
        group["files"] += 1
        group["bytes"] += item["bytes"]
        group["not_cited"] += item["citation"] == "not_cited"
    unreadable = [folder_rel.rstrip("/") + "/" + rel if rel != "." else folder_rel for rel in walk["unreadable"]]
    unreadable.extend(unreadable_inputs)
    reason = walk["reason"] or ("input_unreadable" if unreadable_inputs else None)
    return {
        "folder": folder_rel,
        "files": len(files),
        "bytes": sum(item["bytes"] for item in files),
        **counts,
        "complete": reason is None,
        "reason": reason,
        "unreadable": unreadable,
        "entry_limit": walk["entry_limit"],
        "list_cap": list_cap,
        "listed": files[:list_cap],
        "not_listed": max(0, len(files) - list_cap),
        "directories": sorted(directories.values(), key=lambda group: (-group["bytes"], group["path"])),
    }


# ---------------------------------------------------------------------------
# Explicit cleanup of one work folder (change 23q0s). Operator-directed, one
# exact key, preview first. It has its own verification closure binding an
# owner fingerprint instead of calling ``_read_owner``, so it reaches unowned
# and record-less folders while ``cleanup_work`` and its ownership rules stay
# unchanged. It never writes an owner file, never changes permissions and
# never follows a link.
# ---------------------------------------------------------------------------

CHILD_PREVIEW_LIMIT = 50
_OWNER_MAX_BYTES = 4096


def _entry_type(info) -> str:
    if _is_link_metadata(info):
        return "link"
    if stat.S_ISDIR(info.st_mode):
        return "directory"
    if stat.S_ISREG(info.st_mode):
        return "file"
    return "other"


def _owner_fingerprint(fd: int) -> str:
    """SHA-256 of the raw owner bytes, or ``absent``; one bounded, non-blocking read.

    The owner file is untrusted: its type is checked with ``fstatat`` before it
    is opened, and again with ``fstat`` of the opened descriptor. A link, FIFO,
    device, directory, second link or more than 4,096 bytes raises
    ``unsafe_owner_entry`` without opening anything that could block.
    """
    try:
        info = os.stat(OWNER_FILE, dir_fd=fd, follow_symlinks=False)
    except FileNotFoundError:
        return "absent"
    if (_is_link_metadata(info) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or info.st_size > _OWNER_MAX_BYTES):
        raise _Refused("unsafe_owner_entry")
    try:
        owner_fd = os.open(OWNER_FILE, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0), dir_fd=fd)
    except FileNotFoundError:
        return "absent"
    try:
        opened = os.fstat(owner_fd)
        if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or opened.st_size > _OWNER_MAX_BYTES
                or not _same(opened, info)):
            raise _Refused("unsafe_owner_entry")
        raw = os.read(owner_fd, _OWNER_MAX_BYTES + 1)
    finally:
        os.close(owner_fd)
    if len(raw) > _OWNER_MAX_BYTES:
        raise _Refused("unsafe_owner_entry")
    return hashlib.sha256(raw).hexdigest()


def cleanup_token(repository: str, key: str, directory: list[int], owner: str,
                  state: str, record: str | None) -> str:
    """The confirmation token: SHA-256 of the canonical JSON of the bound facts.

    It binds the resolved repository root, the key, the folder's
    ``[st_dev, st_ino]``, the owner fingerprint and the wave state with its
    record path. It does not bind contents, is not a secret and is not
    authorization; a device number change after a reboot makes it stale.
    """
    payload = {"repository": repository, "work_key": key, "directory": list(directory),
               "owner": owner, "state": state, "record": record}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _explicit_result(key, outcome: str, reason: str | None = None, **extra) -> dict:
    return {"work_key": key, "path": (WORK_ROOT / key).as_posix() if key else None,
            "outcome": outcome, "reason": reason, **extra}


def _children(listing) -> tuple[list[dict], bool]:
    """Up to ``CHILD_PREVIEW_LIMIT`` escaped child names with their types."""
    children: list[dict] = []
    truncated = False
    for entry in listing:
        if len(children) >= CHILD_PREVIEW_LIMIT:
            truncated = True
            break
        try:
            kind = _entry_type(entry.stat(follow_symlinks=False))
        except OSError:
            kind = "unreadable"
        children.append({"name": display_name(entry.name), "type": kind})
    children.sort(key=lambda child: child["name"])
    return children, truncated


def _preview(root: Path, key: str, classified: dict, *, apply_possible: bool, blockers: list[str],
             token: str | None, children: list[dict], truncated: bool, owner_entry: str) -> dict:
    folder = inventory_work_folder(root, key) or {}
    return _explicit_result(
        key, "preview", None,
        state=classified["state"], state_note=classified["note"], record=classified["record"],
        record_live=bool(classified.get("live")) if classified["record"] else None,
        ownership=folder.get("ownership"), owner_entry=owner_entry,
        entries=folder.get("entries"), bytes=folder.get("bytes"),
        complete=folder.get("complete", False), completeness_reason=folder.get("reason", "not_measured"),
        entry_limit=INVENTORY_ENTRY_LIMIT, children=children, children_truncated=truncated,
        apply_possible=apply_possible, apply_blockers=blockers, confirmation=token,
    )


def _unsupported_preview(root: Path, key: str) -> dict:
    """Preview where descriptor-relative deletion is unavailable (native Windows).

    Identity and type come from a lexical no-follow ``lstat`` of each
    component, as ``cleanup_work``'s unsupported branch reads them. Ownership
    comes from the inventory. No token: apply cannot run on this host.
    """
    current = root
    for name in WORK_ROOT.parts:
        current = current / name
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            return _explicit_result(key, "refused", "work_folder_not_found")
        if _is_link_metadata(info) or not stat.S_ISDIR(info.st_mode):
            return _explicit_result(key, "refused", "work_parent_changed")
    if key not in os.listdir(current):
        return _explicit_result(key, "refused", "work_folder_not_found")
    folder = current / key
    info = os.lstat(folder)
    if _is_link_metadata(info) or not stat.S_ISDIR(info.st_mode):
        return _explicit_result(key, "refused", "work_entry_not_directory")
    with os.scandir(folder) as listing:
        children, truncated = _children(listing)
    classified = classify_work_keys(root, [key])[key]
    blockers = ["safe_work_io_unsupported"]
    if classified["state"] not in LEFTOVER_STATES:
        blockers.append("work_state_not_cleanable")
    return _preview(root, key, classified, apply_possible=False, blockers=blockers, token=None,
                    children=children, truncated=truncated, owner_entry="not_checked")


def explicit_cleanup(root, work_key, *, apply: bool = False, confirmation: str = "") -> dict:
    """Preview, or with ``apply`` delete, one exact ``.wavefoundry/work/<key>/``.

    Returns ``outcome`` ``preview``, ``removed``, ``absent`` (apply only: the
    folder is not there), ``refused`` with ``reason`` (nothing removed) or
    ``partially_removed`` (``removed_entries``, ``failed_entry``,
    ``failed_operation``, ``failed_errno``). The caller holds the lifecycle
    and publication locks for apply. Apply proceeds only for a cleanable wave
    state (``LEFTOVER_STATES``), a safe owner entry, a folder on the work
    parent's device and a confirmation equal to the token recomputed now.
    Ownership is not required. Never raises for filesystem conditions.
    """
    key = work_key if isinstance(work_key, str) else None
    if key is None or not WORK_KEY_PATTERN.fullmatch(key):
        return _explicit_result(None, "refused", "work_key_invalid")
    try:
        root = Path(root).resolve(strict=True)
        if not _SAFE_DELETE:
            if apply:
                return _explicit_result(key, "refused", "safe_work_io_unsupported")
            return _unsupported_preview(root, key)
        with _parent(root) as (parent, identities):
            # Byte-exact against the listing: a case-insensitive file system
            # would otherwise open a differently cased folder.
            if key not in os.listdir(parent):
                return _explicit_result(key, "absent" if apply else "refused",
                                        None if apply else "work_folder_not_found")
            listed = os.stat(key, dir_fd=parent, follow_symlinks=False)
            if _is_link_metadata(listed) or not stat.S_ISDIR(listed.st_mode):
                return _explicit_result(key, "refused", "work_entry_not_directory")
            fd = os.open(key, _FLAGS, dir_fd=parent)
            try:
                # The token and the deletion use this one descriptor's fstat.
                directory = os.fstat(fd)
                same_device = directory.st_dev == os.fstat(parent).st_dev
                # A folder on another device is refused below by device; its
                # identity check then compares the inode only.
                if directory.st_ino != listed.st_ino or (same_device and not _same(directory, listed)):
                    return _explicit_result(key, "refused", "work_identity_changed")
                classified = classify_work_keys(root, [key])[key]
                try:
                    fingerprint, owner_entry = _owner_fingerprint(fd), "safe"
                except _Refused:
                    fingerprint, owner_entry = None, "unsafe"
                blockers = []
                if classified["state"] not in LEFTOVER_STATES:
                    blockers.append("work_state_not_cleanable")
                if fingerprint is None:
                    blockers.append("unsafe_owner_entry")
                if not same_device:
                    blockers.append("work_filesystem_changed")
                token = (cleanup_token(str(root), key, _identity(directory), fingerprint,
                                       classified["state"], classified["record"])
                         if fingerprint is not None else None)
                if not apply:
                    with os.scandir(fd) as listing:
                        children, truncated = _children(listing)
                    return _preview(root, key, classified, apply_possible=not blockers, blockers=blockers,
                                    token=token if not blockers else None, children=children,
                                    truncated=truncated, owner_entry=owner_entry)
                if blockers:
                    return _explicit_result(key, "refused", blockers[0], state=classified["state"])
                if not isinstance(confirmation, str) or not confirmation or confirmation != token:
                    return _explicit_result(key, "refused", "preview_stale", state=classified["state"])
                return _delete_explicit(root, key, parent, identities, fd, directory, fingerprint)
            finally:
                os.close(fd)
    except FileNotFoundError:
        return _explicit_result(key, "absent" if apply else "refused", None if apply else "work_folder_not_found")
    except _Refused as exc:
        return _explicit_result(key, "refused", notice_reason(str(exc)))
    except OSError as exc:
        # The no-follow parent walk meets a link or non-directory as ELOOP or
        # ENOTDIR: the work root is not the plain directory chain it must be.
        reason = "work_root_link" if exc.errno in (errno.ELOOP, errno.ENOTDIR) else "work_io_failed"
        return _explicit_result(key, "refused", reason, failed_errno=_errno_name(exc))
    except (ValueError, RuntimeError) as exc:
        return _explicit_result(key, "refused", "work_io_failed", failed_errno=type(exc).__name__)


def _delete_explicit(root: Path, key: str, parent: int, identities: list, fd: int, directory,
                     fingerprint: str) -> dict:
    def located():
        _anchor(root, identities, parent)
        _entry(parent, key, directory)
        if os.fstat(fd).st_dev != os.fstat(parent).st_dev:
            raise _Refused("work_filesystem_changed")

    def verify():
        # Before every unlink and rmdir: the same parent chain, the same
        # folder, the same device and the same owner bytes. Never _read_owner.
        located()
        try:
            current = _owner_fingerprint(fd)
        except _Refused:
            raise _Refused("unsafe_owner_entry") from None
        if current != fingerprint:
            raise _Refused("work_owner_changed")

    progress = _Progress()
    try:
        _checkpoint("explicit_cleanup")
        verify()
        _empty_directory(fd, verify, skip_owner=True, progress=progress)
        if fingerprint != "absent":
            progress.at(OWNER_FILE, "unlink")
            _checkpoint("unlink_owner")
            verify()
            os.unlink(OWNER_FILE, dir_fd=fd)
            progress.done()
        progress.at(".", "rmdir")
        _checkpoint("rmdir")
        located()
        os.rmdir(key, dir_fd=parent)
    except (OSError, ValueError, RuntimeError, _Refused) as exc:
        result = _removal_failure(key, exc, progress)
        reason = notice_reason(result.get("notice"))
        outcome = "partially_removed" if progress.removed else "refused"
        return _explicit_result(key, outcome, reason, **{
            field: result[field] for field in ("notice", "removed_entries", "failed_entry",
                                               "failed_operation", "failed_errno") if field in result})
    return _explicit_result(key, "removed", None, removed_entries=progress.removed)


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


def _verify_snapshot_links(fd: int, source: int) -> None:
    """Accept only the published name and its optional construction link."""
    info = os.fstat(source)
    if not stat.S_ISREG(info.st_mode):
        raise _Refused("snapshot_file_unproven; full review required")
    if info.st_nlink == 1:
        return
    matches = []
    if info.st_nlink == 2:
        for name in os.listdir(fd):
            if not re.fullmatch(r"\.snapshot-[0-9a-f]{32}\.tmp", name):
                continue
            _checkpoint("snapshot_link")
            try:
                candidate = os.stat(name, dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError:
                continue  # The active publisher may have removed its link.
            if (stat.S_ISREG(candidate.st_mode) and not _is_link_metadata(candidate)
                    and _same(candidate, info)):
                matches.append(name)
    # Recheck the name as well as the count: a publisher may unlink while a
    # different process creates an unrelated extra link during enumeration.
    if len(matches) == 1:
        _checkpoint("snapshot_link_verified")
        try:
            candidate = os.stat(matches[0], dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            matches = []
        else:
            if (_is_link_metadata(candidate) or not stat.S_ISREG(candidate.st_mode)
                    or not _same(candidate, info)):
                matches = []
    current = os.fstat(source)
    if current.st_nlink == 1 or (current.st_nlink == 2 and len(matches) == 1):
        return
    raise _Refused("snapshot_file_unproven; full review required")


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
                _verify_snapshot_links(fd, source)
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
                _verify_snapshot_links(fd, source)
                return _snapshot_result(key, receipt_id, available=True, documents=documents)
            finally:
                os.close(source)
    except (OSError, ValueError, RuntimeError, ImportError, _Refused) as exc:
        return _snapshot_failure(key, receipt_id, exc)
