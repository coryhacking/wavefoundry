"""One definition of where wave records and plan documents live (wave 1y0gz).

Deliberately import-light (stdlib only, no project imports): the MCP server,
docs-lint, the indexer, the memory backfill, the dashboard, and the upgrade
runner all resolve the record roots here, and docs-lint must import it in
hosts that have no MCP runtime installed.

The layout is defined by the module constants below and nowhere else. A
downstream fork that keeps its records elsewhere edits these constants when it
merges the framework; nothing is read from configuration at runtime, so the
layout of a process is fixed at import and every consumer sees the same value.
The module answers two questions:

* where are the waves root and the plans root for a repository, as both a
  repo-relative POSIX string and an absolute ``Path``; and
* is the layout valid for that repository.

Validation is fail-closed: an invalid layout (an absolute or escaping root, a
root or an ancestor of it that names a file, a root that is a symlink or case
alias of another directory, equal or nested roots, a mistyped ``NESTED`` or
``MAX_DEPTH``) raises :class:`RecordLayoutInvalid` from
:func:`load_record_roots`; nothing silently falls back. For the shipped layout
the absolute paths are built exactly as the call sites built them before this
module existed (``root / "docs" / "waves"``), so cache fingerprints and every
rendered path are byte-identical.
"""
from __future__ import annotations

import errno
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

# Wave 1z8mm: the record filename is vocabulary, owned by vocabulary_profile.
import vocabulary_profile

# ---------------------------------------------------------------------------
# Fork-editable layout constants. Edit these at merge time; keep them
# repository-relative POSIX paths. ``NESTED`` enables the bounded recursive
# wave walk (wave 1y043); ``MAX_DEPTH`` counts the wave folder's own depth
# below the waves root, so ``1`` means direct children only.
# ---------------------------------------------------------------------------
WAVES_ROOT = "docs/waves"
PLANS_ROOT = "docs/plans"
NESTED = False
# Repository-wide by default; parent scope requires NESTED.
OPEN_CONTAINER_SCOPE = "repository"
MAX_DEPTH = 4
# Optional read-only archive of closed records, often frozen under an older
# vocabulary (``vocabulary_profile.ARCHIVE_PROFILE``). ``None`` disables it.
# Read by id lookup and id-collision scanning; never written (wave 1z8ts).
ARCHIVE_ROOT: "str | None" = None

MAX_DEPTH_RANGE = (1, 8)
CONSTANT_NAMES = ("WAVES_ROOT", "PLANS_ROOT", "NESTED", "MAX_DEPTH")

AMBIGUOUS_WAVE_ID_CODE = "ambiguous_wave_id"
DIAGNOSTIC_CODE = "record_layout_invalid"
RECORD_ROOT_UNREADABLE_CODE = "record_root_unreadable"
RECORD_FOLDER_UNREADABLE_CODE = "record_folder_unreadable"

# Wave 1zrak (1zu4y): an in-place reload (``upgrade_extensions._reload_in_place``,
# including the copy a v1.28.0 runner ships) re-executes this module in its own
# namespace and then rebinds only the exception classes the OLD module had. Read
# the class the old holders captured BEFORE the statement below re-defines it, so
# ``RecordRootUnreadable`` subclasses that object and every old-bound
# ``except RecordLayoutInvalid`` still catches it. ``None`` on a fresh import.
# Keep this read above the class statement: the AC-6 reload pin in
# ``tests/test_record_discovery_fail_closed.py`` fails if it moves below it.
_PRIOR_RECORD_LAYOUT_INVALID = globals().get("RecordLayoutInvalid")


class RecordLayoutInvalid(Exception):
    """The record layout is invalid for this repository; carries the diagnostics.

    Deliberately NOT a ``ValueError``: lifecycle tools map ``ValueError`` to
    ``invalid_arguments`` or path-escape diagnostics, which would hide the
    layout error behind the wrong code. Only the fail-closed decorator in the
    server handles this type."""

    def __init__(self, diagnostics: list[str]) -> None:
        super().__init__("; ".join(diagnostics))
        self.diagnostics = list(diagnostics)


class AmbiguousWaveId(Exception):
    """One wave id appears at more than one path under the waves root; carries
    the ``ambiguous_wave_id: <id> at <rel>, <rel>`` diagnostics.

    Raised by the server's wave resolver so every lifecycle tool refuses the
    same way (wave 1y043); deliberately NOT a ``ValueError`` for the same
    reason as :class:`RecordLayoutInvalid`."""

    def __init__(self, diagnostics: list[str]) -> None:
        super().__init__("; ".join(diagnostics))
        self.diagnostics = list(diagnostics)


_RECORD_LAYOUT_INVALID_BASE = (
    _PRIOR_RECORD_LAYOUT_INVALID
    if isinstance(_PRIOR_RECORD_LAYOUT_INVALID, type) and issubclass(_PRIOR_RECORD_LAYOUT_INVALID, Exception)
    else RecordLayoutInvalid
)


def _cause_label(exc: BaseException) -> str:
    """The exception class and errno name, without the exception's text (the
    same form as ``lifecycle_lock._cause_label``; repeated here because this
    module imports nothing from the project but ``vocabulary_profile``)."""
    code = errno.errorcode.get(getattr(exc, "errno", None) or 0)
    return f"{type(exc).__name__} {code}" if code else type(exc).__name__


class RecordRootUnreadable(_RECORD_LAYOUT_INVALID_BASE):
    """A record root, or a folder discovery uses below it, cannot be inspected
    (wave 1zrak, change 1zu4y). Fail-closed: discovery refuses rather than
    reading the root or folder as absent, so no tool acts on a partial view.

    ``code`` is ``record_root_unreadable`` (the waves or archive root itself)
    or ``record_folder_unreadable`` (a folder below it). The text is path-free:
    the repository-relative path, the exception class and errno name, and the
    recovery; never ``strerror`` or an absolute path. Subclasses
    :class:`RecordLayoutInvalid` (reload-safe, see
    ``_PRIOR_RECORD_LAYOUT_INVALID``) so every fail-closed or observational
    handler of an invalid layout handles it unchanged."""

    def __init__(self, code: str, rel: str, cause: str, *, root_rel: "str | None" = None) -> None:
        if code == RECORD_FOLDER_UNREADABLE_CODE:
            line = (
                f"{code}: {rel}: cannot be inspected ({cause}); restore read and search access to {rel}, "
                f"or move it out of {root_rel} if it is not a wave folder, then retry"
            )
        else:
            line = f"{code}: {rel}: cannot be inspected ({cause}); restore read and search access to {rel}, then retry"
        super().__init__([line])
        self.code = code
        self.rel = rel
        self.cause = cause
        self.root_rel = root_rel
        self.diagnostic = line


def record_root_is_dir(path: Path, rel: str) -> bool:
    """Decide a record root's state with ``os.stat`` (following links, as
    ``Path.is_dir`` did): ``True`` for a directory, ``False`` when it is absent
    or not a directory. Python 3.14 ``pathlib`` predicates return ``False`` on
    ANY ``OSError``, so only ``FileNotFoundError`` and ``NotADirectoryError``
    mean absent here; every other ``OSError`` raises
    :class:`RecordRootUnreadable` naming ``rel`` (the 1zraj errno rule, as
    ``review_evidence._authority_member_lstat``)."""
    try:
        st = os.stat(path)
    except (FileNotFoundError, NotADirectoryError):
        return False
    except OSError as exc:
        raise RecordRootUnreadable(RECORD_ROOT_UNREADABLE_CODE, rel, _cause_label(exc)) from None
    return stat.S_ISDIR(st.st_mode)


def _refusal_exempt(path: Path) -> bool:
    """A dot-prefixed name or a symlink (by ``lstat``): discovery never refuses
    these (wave 1zrak, change 1zu4y, Requirement 4), so a caller that lists a
    discovered folder skips one it cannot list instead of refusing."""
    if Path(path).name.startswith("."):
        return True
    try:
        return stat.S_ISLNK(os.lstat(path).st_mode)
    except OSError:
        return False


def _scandir(path: Path) -> list:
    """The one listing seam of the discovery walk and the id mint (wave 1zrak,
    change 1zu4y): ``os.scandir`` entries, materialized. ``Path.iterdir`` and
    ``Path.glob`` are not used there because their implementation moved
    between Python 3.11 and 3.14; tests patch this function to raise for one
    target path. Raises ``OSError`` as ``os.scandir`` does."""
    with os.scandir(path) as entries:
        return list(entries)


@dataclass(frozen=True)
class RecordRoots:
    """Resolved record roots. ``waves``/``plans`` are absolute but NOT
    ``resolve()``d, matching how every call site built them before."""

    waves_rel: str
    plans_rel: str
    waves: Path
    plans: Path
    nested: bool = False
    max_depth: int = 4
    archive_rel: "str | None" = None
    archive: "Path | None" = None

    @property
    def waves_prefix(self) -> str:
        """Repo-relative prefix with a trailing slash, for ``startswith`` checks."""
        return self.waves_rel + "/"

    @property
    def plans_prefix(self) -> str:
        return self.plans_rel + "/"


def layout_constants() -> tuple[object, object, object, object]:
    """The current constant values, read at call time. Cache keys fold this in
    so a process whose constants were patched (tests) re-resolves. The archive
    root is appended only when set, so the default key is unchanged."""
    values = (WAVES_ROOT, PLANS_ROOT, NESTED, MAX_DEPTH)
    if ARCHIVE_ROOT is not None:
        values += (ARCHIVE_ROOT,)
    if OPEN_CONTAINER_SCOPE != "repository":
        values += (OPEN_CONTAINER_SCOPE,)
    return values


def _canonical_parts(value: str) -> list[str]:
    """POSIX-normalized path parts: backslashes folded, empty and ``.``
    segments dropped. ``..`` is kept so validation can refuse it."""
    raw = value.replace("\\", "/").strip()
    return [part for part in raw.split("/") if part and part != "."]


def _join_rel(root: Path, rel: str) -> Path:
    path = Path(root)
    for part in _canonical_parts(rel):
        path = path / part
    return path


def _resolved_inside(root: Path, candidate: Path) -> bool:
    """True when ``candidate`` resolves inside ``root`` (symlink-aware).
    Uses ``os.path.realpath`` rather than ``Path.resolve`` so the docs-lint
    hot loop, which pins that it never calls ``Path.resolve``, stays clean."""
    try:
        Path(os.path.realpath(candidate)).relative_to(os.path.realpath(root))
        return True
    except (ValueError, OSError):
        return False


def _has_symlink_component(root: Path, parts: list[str]) -> bool:
    """True when any component of ``root/parts`` is itself a symlink."""
    path = Path(root)
    for part in parts:
        path = path / part
        try:
            if os.path.islink(path):
                return True
        except OSError:
            return False
    return False


def _exists(path: Path) -> bool:
    """``Path.exists`` that never raises (a self-looping symlink raises
    ``ELOOP`` from ``stat`` on some platforms and Python versions)."""
    try:
        return path.exists()
    except OSError:
        return False


def _lexists(path: Path) -> bool:
    """``os.path.lexists`` that never raises: True for a directory entry that
    is present even when its target is not (a dangling or looping symlink)."""
    try:
        return os.path.lexists(path)
    except OSError:
        return False


def _is_dir(path: Path) -> bool:
    try:
        return path.is_dir()
    except OSError:
        return False


def _is_dangling_link(path: Path) -> bool:
    """The entry is present but nothing is behind it: a dangling symlink, or
    a symlink loop (``lstat`` succeeds, ``stat`` does not)."""
    return _lexists(path) and not _exists(path)


def _nearest_existing(root: Path, parts: list[str]) -> tuple[Path, int]:
    """``(path, covered)``: the deepest existing path along ``root/parts`` and
    how many parts it covers (``0`` when only ``root`` exists). Walking down
    from the root stops at the first missing component, which is the same
    thing as walking up from the candidate to the first existing one.

    A dangling or looping symlink IS the nearest existing entry (the
    directory entry exists even though its target does not): it counts as
    covered so :func:`_check_root` refuses it, instead of being skipped as
    "absent" and later written through."""
    path = Path(root)
    covered = 0
    for part in parts:
        nxt = path / part
        if not _exists(nxt):
            if _lexists(nxt):
                path, covered = nxt, covered + 1
            break
        path = nxt
        covered += 1
    return path, covered


def _alias_diagnostics(prefix: str, value: object, root: Path, parts: list[str], covered: int) -> list[str]:
    """Refuse an existing root (or existing ancestor of an absent root) that is
    an alias of another directory: reached through an in-repository symlink
    (``records -> docs/waves``) or spelled in a different case on a
    case-insensitive filesystem (``Docs/waves``). Every lifecycle tool refuses
    such a root through its containment guard, so the layout refuses it too."""
    message = [f"{prefix} must resolve to the canonical in-repository directory: {value!r}"]
    existing_parts = parts[:covered]
    # Symlink alias: only a path with a symlink component can resolve
    # elsewhere, and only then is a realpath taken (never ``Path.resolve``:
    # the docs-lint hot loop pins that it makes no such call).
    if _has_symlink_component(root, existing_parts):
        existing = _join_rel(root, "/".join(existing_parts))
        try:
            canonical = os.path.join(os.path.realpath(root), *existing_parts)
            if os.path.realpath(existing) != canonical:
                return message
        except OSError:
            return []
    # Case alias: realpath never fixes case, so each spelled component must
    # be the on-disk name of its parent's entry.
    parent = Path(root)
    for part in existing_parts:
        try:
            names = os.listdir(parent)
        except OSError:
            return []
        if part not in names:
            return message
        parent = parent / part
    return []


def _check_root(name: str, value: object, root: Path) -> tuple[str | None, list[str]]:
    """Validate one root constant against ``root``. Returns (canonical_rel, diagnostics).

    ``canonical_rel`` is ``None`` when the value cannot name a root at all; an
    alias root (symlink or case) keeps its ``rel`` and carries the alias
    diagnostic so the equal/nesting checks still report alongside it."""
    prefix = f"{DIAGNOSTIC_CODE}: record_paths.{name}"
    if not isinstance(value, str) or not value.strip():
        return None, [f"{prefix} must be a non-empty string"]
    raw = value.replace("\\", "/").strip()
    if raw.startswith("/") or (len(raw) > 1 and raw[1] == ":"):
        return None, [f"{prefix} must be repository-relative, not absolute: {value!r}"]
    parts = _canonical_parts(raw)
    # Joining an embedded drive component resets a Windows path, even when
    # the whole value begins with a relative directory (docs/D:/waves).
    # Reject it before probing ancestors: missing parents cannot prove safety.
    if any(PureWindowsPath(part).drive for part in parts):
        return None, [f"{prefix} must not contain a drive-qualified component: {value!r}"]
    if any(part == ".." for part in parts):
        return None, [f"{prefix} must not contain '..': {value!r}"]
    if not parts:
        return None, [f"{prefix} must name a directory: {value!r}"]
    rel = "/".join(parts)
    # Only an existing path can be a file, escape through a symlink, or alias
    # another directory; the checks run on the nearest existing path along the
    # root (the root itself, or the ancestor a first create would write under),
    # so a bad ancestor is refused BEFORE anything is created beneath it.
    nearest, covered = _nearest_existing(root, parts)
    if covered:
        offending = "/".join(parts[:covered])
        # A dangling (or looping) symlink is refused BEFORE the directory
        # check: `is_dir()` is False for it too, but "is a file" would be a
        # false report, and a first create would otherwise write through it.
        if _is_dangling_link(nearest):
            return None, [
                f"{prefix} must name a directory, not a dangling symlink: {value!r} "
                f"({offending} is a dangling symlink)"
            ]
        if not _is_dir(nearest):
            return None, [f"{prefix} must name a directory, not a file: {value!r} ({offending} is a file)"]
        if _has_symlink_component(root, parts[:covered]) and not _resolved_inside(root, nearest):
            return None, [f"{prefix} resolves outside the repository through a symlink: {value!r}"]
        return rel, _alias_diagnostics(prefix, value, root, parts, covered)
    return rel, []


def _existing_or_ancestor(root: Path, rel: str) -> tuple[Path, bool]:
    """``(path, is_root)``: the root when it exists, otherwise its nearest
    existing ancestor (the directory a first create would write under)."""
    parts = rel.split("/")
    nearest, covered = _nearest_existing(root, parts)
    return nearest, covered == len(parts)


def _same_directory(a: Path, b: Path) -> bool:
    """True when two existing paths are one directory on disk. Compared by
    inode (``os.path.samefile``), not by spelling, so case-variant spellings
    on a case-insensitive filesystem are caught."""
    try:
        return a.exists() and b.exists() and os.path.samefile(a, b)
    except OSError:
        return False


def _nests_on_disk(inner: Path, outer: Path) -> bool:
    """True when an existing ``inner`` sits below an existing ``outer`` on
    disk (some ancestor of ``inner`` is ``outer`` by inode)."""
    try:
        if not (inner.exists() and outer.exists()):
            return False
        for ancestor in Path(os.path.realpath(inner)).parents:
            if os.path.samefile(ancestor, outer):
                return True
    except OSError:
        return False
    return False


def validate_record_layout(root: Path) -> list[str]:
    """Diagnostics for the layout constants applied to ``root``; empty when valid.

    Every message starts with ``record_layout_invalid:`` so lint and the MCP
    tools report the same code.
    """
    root = Path(root)
    diagnostics: list[str] = []
    waves_rel, errs = _check_root("WAVES_ROOT", WAVES_ROOT, root)
    diagnostics.extend(errs)
    plans_rel, errs = _check_root("PLANS_ROOT", PLANS_ROOT, root)
    diagnostics.extend(errs)
    if not isinstance(NESTED, bool):
        diagnostics.append(f"{DIAGNOSTIC_CODE}: record_paths.NESTED must be True or False")
    if OPEN_CONTAINER_SCOPE not in ("repository", "parent"):
        diagnostics.append(f"{DIAGNOSTIC_CODE}: OPEN_CONTAINER_SCOPE must be repository or parent")
    elif OPEN_CONTAINER_SCOPE == "parent" and NESTED is not True:
        diagnostics.append(f"{DIAGNOSTIC_CODE}: parent OPEN_CONTAINER_SCOPE requires NESTED")
    low, high = MAX_DEPTH_RANGE
    if isinstance(MAX_DEPTH, bool) or not isinstance(MAX_DEPTH, int) or not (low <= MAX_DEPTH <= high):
        diagnostics.append(
            f"{DIAGNOSTIC_CODE}: record_paths.MAX_DEPTH must be an integer from {low} to {high}"
        )
    if waves_rel is None or plans_rel is None:
        return diagnostics
    waves, plans = _join_rel(root, waves_rel), _join_rel(root, plans_rel)
    # Identity is judged by spelling AND on disk. An absent root is judged by
    # its nearest existing ancestor: the directory a first create would write
    # under. ``docs/plans -> docs`` with ``docs/waves`` absent is refused as
    # nesting BEFORE the first wave is created inside the plans root.
    waves_at, waves_exists = _existing_or_ancestor(root, waves_rel)
    plans_at, plans_exists = _existing_or_ancestor(root, plans_rel)
    if waves_rel == plans_rel or (waves_exists and plans_exists and _same_directory(waves, plans)):
        diagnostics.append(
            f"{DIAGNOSTIC_CODE}: WAVES_ROOT and PLANS_ROOT must differ ({waves_rel!r}, {plans_rel!r})"
        )
    elif (
        waves_rel.startswith(plans_rel + "/")
        or plans_rel.startswith(waves_rel + "/")
        or _nests_on_disk(waves, plans)
        or _nests_on_disk(plans, waves)
        or (not waves_exists and plans_exists and (_same_directory(waves_at, plans) or _nests_on_disk(waves_at, plans)))
        or (not plans_exists and waves_exists and (_same_directory(plans_at, waves) or _nests_on_disk(plans_at, waves)))
    ):
        diagnostics.append(
            f"{DIAGNOSTIC_CODE}: WAVES_ROOT and PLANS_ROOT must not nest ({waves_rel!r}, {plans_rel!r})"
        )
    if ARCHIVE_ROOT is not None:
        archive_rel, errs = _check_root("ARCHIVE_ROOT", ARCHIVE_ROOT, root)
        diagnostics.extend(errs)
        if archive_rel is not None:
            for name, other_rel in (("WAVES_ROOT", waves_rel), ("PLANS_ROOT", plans_rel)):
                relation = _root_overlap(root, archive_rel, other_rel)
                if relation:
                    diagnostics.append(
                        f"{DIAGNOSTIC_CODE}: record_paths.ARCHIVE_ROOT and {name} must "
                        f"{'differ' if relation == 'equal' else 'not nest'} ({archive_rel!r}, {other_rel!r})"
                    )
    return diagnostics


def _root_overlap(root: Path, a_rel: str, b_rel: str) -> "str | None":
    """``'equal'``, ``'nest'`` (either direction) or ``None`` for two roots,
    judged by spelling and on disk the same way as WAVES_ROOT and PLANS_ROOT
    (an absent root by its nearest existing ancestor)."""
    a, b = _join_rel(root, a_rel), _join_rel(root, b_rel)
    a_at, a_exists = _existing_or_ancestor(root, a_rel)
    b_at, b_exists = _existing_or_ancestor(root, b_rel)
    if a_rel == b_rel or (a_exists and b_exists and _same_directory(a, b)):
        return "equal"
    if (
        a_rel.startswith(b_rel + "/")
        or b_rel.startswith(a_rel + "/")
        or _nests_on_disk(a, b)
        or _nests_on_disk(b, a)
        or (not a_exists and b_exists and (_same_directory(a_at, b) or _nests_on_disk(a_at, b)))
        or (not b_exists and a_exists and (_same_directory(b_at, a) or _nests_on_disk(b_at, a)))
    ):
        return "nest"
    return None


def load_record_roots(root: Path) -> RecordRoots:
    """Resolve the record roots for ``root``. Raises :class:`RecordLayoutInvalid`
    (fail-closed) when the layout constants are invalid for this repository."""
    root = Path(root)
    diagnostics = validate_record_layout(root)
    if diagnostics:
        raise RecordLayoutInvalid(diagnostics)
    waves_rel = "/".join(_canonical_parts(WAVES_ROOT))
    plans_rel = "/".join(_canonical_parts(PLANS_ROOT))
    archive_rel = "/".join(_canonical_parts(ARCHIVE_ROOT)) if ARCHIVE_ROOT is not None else None
    return RecordRoots(
        waves_rel=waves_rel,
        plans_rel=plans_rel,
        waves=_join_rel(root, waves_rel),
        plans=_join_rel(root, plans_rel),
        nested=bool(NESTED),
        max_depth=int(MAX_DEPTH),
        archive_rel=archive_rel,
        archive=_join_rel(root, archive_rel) if archive_rel else None,
    )


def open_container_scope(root: Path, wave_path: Path) -> Path:
    """Return the validated activation domain; never partition publication locks.

    Parent scope uses the immediate parent of the canonical wave directory.
    Only discovered records qualify, excluding aliases, escapes and archives.
    """
    roots = load_record_roots(root)
    if OPEN_CONTAINER_SCOPE == "repository":
        return roots.waves
    path = Path(wave_path)
    if not path.is_absolute():
        path = Path(root) / path
    directories = discover_wave_dirs(root)
    if path.name != vocabulary_profile.RECORD_FILENAME or path.parent not in directories or path.is_symlink():
        raise RecordLayoutInvalid([f"{DIAGNOSTIC_CODE}: activation target must be a canonical discovered wave record"])
    return path.parent.parent


def unvalidated_record_roots(root: Path) -> RecordRoots:
    """The layout constants applied to ``root`` WITHOUT validation. For
    callers that must not fail closed (a diagnostic that reports the layout
    error, or observational ranking that must never refuse a search)."""
    root = Path(root)
    waves_rel = "/".join(_canonical_parts(WAVES_ROOT)) if isinstance(WAVES_ROOT, str) else ""
    plans_rel = "/".join(_canonical_parts(PLANS_ROOT)) if isinstance(PLANS_ROOT, str) else ""
    return RecordRoots(
        waves_rel=waves_rel,
        plans_rel=plans_rel,
        waves=_join_rel(root, waves_rel),
        plans=_join_rel(root, plans_rel),
        nested=NESTED is True,
        max_depth=MAX_DEPTH if isinstance(MAX_DEPTH, int) and not isinstance(MAX_DEPTH, bool) else 4,
    )


# ---------------------------------------------------------------------------
# Wave record discovery (1y043)
# ---------------------------------------------------------------------------

class _Walk:
    """One discovery walk's refusal context (wave 1zrak, change 1zu4y): the
    walked root, its repository-relative spelling, and the flat-layout entries
    exempt from refusal (dot-prefixed names and symlinks)."""

    def __init__(self, top: Path, top_rel: str) -> None:
        self.top = top
        self.top_rel = top_rel
        self.exempt: set[Path] = set()

    def rel(self, directory: Path) -> str:
        if directory == self.top:
            return self.top_rel
        try:
            tail = directory.relative_to(self.top).as_posix()
        except ValueError:
            return directory.name
        return f"{self.top_rel}/{tail}"

    def refusal(self, directory: Path, exc: OSError) -> RecordRootUnreadable:
        """The refusal naming ``directory``: the root code for the walked root
        itself, the folder code (with the move-it-out recovery) below it."""
        if directory == self.top:
            return RecordRootUnreadable(RECORD_ROOT_UNREADABLE_CODE, self.top_rel, _cause_label(exc))
        return RecordRootUnreadable(
            RECORD_FOLDER_UNREADABLE_CODE, self.rel(directory), _cause_label(exc), root_rel=self.top_rel
        )


def _list_subdirs(directory: Path, *, guarded: bool = True, walk: "_Walk | None" = None) -> list[Path]:
    """Sorted child directories. With ``guarded`` (the nested walk) symlinked
    and dot-prefixed entries are skipped; without it (the flat layout) the
    listing matches the pre-change ``iterdir`` enumeration, so a symlinked
    wave folder is still found and refused downstream by the record-writer
    path-escape guards rather than silently vanishing. Files are never
    candidates in either mode. The single walk primitive; tests instrument it
    to prove depth and call bounds.

    With ``walk`` (every discovery walk), a listing ``OSError`` and an entry's
    own ``lstat`` failure refuse through :class:`RecordRootUnreadable` naming
    ``directory`` (wave 1zrak, change 1zu4y): an entry's ``lstat`` fails only
    when its parent cannot be searched. Dot-prefixed names never refuse (the
    nested walk skips them before any stat); a symlink never refuses because
    of its target (the flat walk keeps its pre-change handling: a candidate
    when the target stats as a directory). Flat-layout dot-prefixed and
    symlinked candidates are recorded in ``walk.exempt``."""
    try:
        entries = _scandir(directory)
    except OSError as exc:
        if walk is not None:
            raise walk.refusal(directory, exc) from None
        return []
    out = []
    for entry in sorted(entries, key=lambda e: e.name):
        path = directory / entry.name
        dotted = entry.name.startswith(".")
        if guarded and dotted:
            continue
        try:
            entry_stat = os.lstat(path)
        except (FileNotFoundError, NotADirectoryError):
            continue  # vanished after the listing
        except OSError as exc:
            if walk is not None and not dotted:
                raise walk.refusal(directory, exc) from None
            continue
        if stat.S_ISLNK(entry_stat.st_mode):
            if guarded:
                continue
            try:
                if not stat.S_ISDIR(os.stat(path).st_mode):
                    continue
            except OSError:
                continue
            if walk is not None:
                walk.exempt.add(path)
            out.append(path)
            continue
        if not stat.S_ISDIR(entry_stat.st_mode):
            continue
        if walk is not None and dotted:
            walk.exempt.add(path)
        out.append(path)
    return out


def _has_wave_md(directory: Path, record_filename: "str | None" = None) -> bool:
    try:
        return (directory / (record_filename or vocabulary_profile.RECORD_FILENAME)).is_file()
    except OSError:
        return False


def _probe_record_file(directory: Path, record_filename: "str | None", walk: _Walk) -> bool:
    """The refusing record-file probe of a candidate the walk uses (wave
    1zrak, change 1zu4y): ``True`` for a regular record file (following links,
    as ``is_file()`` did), ``False`` when it is absent; any other ``OSError``
    refuses naming the candidate folder."""
    try:
        st = os.stat(directory / (record_filename or vocabulary_profile.RECORD_FILENAME))
    except (FileNotFoundError, NotADirectoryError):
        return False
    except OSError as exc:
        raise walk.refusal(directory, exc) from None
    return stat.S_ISREG(st.st_mode)


def _walk_top_rel(root: Path, roots: RecordRoots, top: Path) -> str:
    """The repository-relative spelling of a walked root, never absolute."""
    if top == roots.waves:
        return roots.waves_rel
    if roots.archive is not None and top == roots.archive and roots.archive_rel:
        return roots.archive_rel
    try:
        return Path(top).relative_to(Path(root)).as_posix()
    except ValueError:
        return Path(top).name


def walk_wave_candidates(root: Path, roots: RecordRoots | None = None, *,
                         base: "Path | None" = None, record_filename: "str | None" = None) -> list[Path]:
    """Every directory that may hold a wave record, under the discovery guards.

    Flat layout: the waves root's child directories, exactly as ``iterdir``
    enumerated them before (content-driven validators such as the orphan-ledger
    check need directories WITHOUT a ``wave.md`` too). Nested layout: a
    bounded depth-first walk to ``max_depth`` that never enters a symlink or a
    dot-prefixed directory and never descends into a directory that holds a
    ``wave.md`` (a wave folder's own subdirectories are evidence, not waves).

    Fail-closed (wave 1zrak, change 1zu4y): a root (or ``base``) that cannot
    be inspected, or whose listing fails, raises
    :class:`RecordRootUnreadable` (``record_root_unreadable``); below it, a
    candidate whose record-file probe fails, a nested folder the walk lists,
    and an entry whose ``lstat`` fails raise ``record_folder_unreadable``. An
    absent root still returns ``[]``.
    """
    roots = roots or load_record_roots(root)
    top = base if base is not None else roots.waves
    walk = _Walk(top, _walk_top_rel(root, roots, top))
    if not record_root_is_dir(top, walk.top_rel):
        return []
    if not roots.nested:
        candidates = _list_subdirs(top, guarded=False, walk=walk)
        for child in candidates:
            if child not in walk.exempt:
                _probe_record_file(child, record_filename, walk)
        return candidates
    found: list[Path] = []
    stack: list[tuple[Path, int]] = [(top, 0)]
    while stack:
        directory, depth = stack.pop()
        if depth >= roots.max_depth:
            continue
        for child in reversed(_list_subdirs(directory, walk=walk)):
            found.append(child)
            if not _probe_record_file(child, record_filename, walk):
                stack.append((child, depth + 1))
    return sorted(found)


def discover_wave_dirs(root: Path, roots: RecordRoots | None = None) -> list[Path]:
    """Every wave folder (a directory containing ``wave.md``) under the waves
    root: immediate children when ``NESTED`` is false, otherwise the bounded
    walk of :func:`walk_wave_candidates`."""
    return [d for d in walk_wave_candidates(root, roots) if _has_wave_md(d)]


def discover_archive_dirs(root: Path, roots: RecordRoots | None = None) -> list[Path]:
    """Every archived wave folder (wave 1z8ts): the folders under
    ``ARCHIVE_ROOT`` that hold the archive profile's record file, walked with
    the live ``NESTED``/``MAX_DEPTH``. Empty when the archive is unset or absent;
    an archive root that cannot be inspected refuses (wave 1zrak, change 1zu4y)."""
    roots = roots or load_record_roots(root)
    if roots.archive is None or not record_root_is_dir(roots.archive, roots.archive_rel or ""):
        return []
    record = vocabulary_profile.archive_profile().RECORD_FILENAME
    candidates = walk_wave_candidates(root, roots, base=roots.archive, record_filename=record)
    return [d for d in candidates if _has_wave_md(d, record)]


def _holds_a_file(directory: Path) -> bool:
    """Whether ``directory`` directly holds a regular file not named ``.*``.
    An unlistable folder counts as holding none; never raises. A symlinked
    file does not count, so a renamed record that is only a symlink leaves
    the advisory silent (never a false report)."""
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                try:
                    if not entry.name.startswith(".") and entry.is_file(follow_symlinks=False):
                        return True
                except OSError:
                    continue
    except OSError:
        return False
    return False


def record_discovery_mismatch(root: Path, roots: RecordRoots | None = None) -> str | None:
    """Wave 1z8mm: a message when the waves root has candidate folders but none
    holds the profile's record file; ``None`` otherwise.

    Only candidates that directly hold a file count; a folder with no files
    (empty, only subfolders, or only dot-files such as ``.gitkeep``) cannot
    hold a renamed record and is ignored (wave 1z8mm, change 1z8ql), so a fresh
    install or a root of empty grouping folders is silent. Known limits: a
    mixed state (some folders renamed) is not detected, and a grouping or
    helper folder that holds files but no record (a ``README.md``) counts.
    """
    # Advisory: a refusal (an invalid layout, or a root or candidate the walk
    # cannot inspect, wave 1zrak) is reported by the fail-closed paths, never here.
    try:
        candidates = walk_wave_candidates(root, roots)
        if any(_has_wave_md(d) for d in candidates):
            return None
    except RecordLayoutInvalid:
        return None
    candidates = [d for d in candidates if _holds_a_file(d)]
    if not candidates:
        return None
    name = vocabulary_profile.RECORD_FILENAME
    return (
        f"record_file_not_found: the waves root has {len(candidates)} folder(s) but none holds "
        f"`{name}`, the record filename in vocabulary_profile; records under another name are "
        "not found. Check vocabulary_profile.RECORD_FILENAME against the records on disk."
    )


def wave_id_of(wave_dir: Path) -> str:
    """The wave id token of a ``<id> <slug>`` folder name, lower-cased."""
    return wave_dir.name.split(" ", 1)[0].strip().lower()


def ambiguous_wave_ids(wave_dirs: list[Path]) -> dict[str, list[Path]]:
    """Wave ids that appear at more than one path, each with its paths sorted."""
    by_id: dict[str, list[Path]] = {}
    for d in wave_dirs:
        by_id.setdefault(wave_id_of(d), []).append(d)
    return {wid: sorted(paths) for wid, paths in by_id.items() if len(paths) > 1}


def _repo_rel(root: Path, path: Path) -> str:
    """Repo-relative POSIX string, tolerant of a resolved ``path`` against an
    unresolved ``root`` (``/var`` versus ``/private/var``)."""
    for base in (Path(root), Path(root).resolve()):
        for candidate in (path, path.resolve()):
            try:
                return str(candidate.relative_to(base)).replace("\\", "/")
            except (ValueError, OSError):
                continue
    return str(path).replace("\\", "/")


def ambiguous_wave_id_diagnostics(root: Path, wave_dirs: list[Path]) -> list[str]:
    """``ambiguous_wave_id: <id> at <rel>, <rel>`` per duplicated id, so the
    server and docs-lint report the same text."""
    root = Path(root)
    lines = []
    for wid, paths in sorted(ambiguous_wave_ids(wave_dirs).items()):
        rels = ", ".join(_repo_rel(root, p) for p in paths)
        lines.append(f"{AMBIGUOUS_WAVE_ID_CODE}: {wid} at {rels}")
    return lines


__all__ = [
    "WAVES_ROOT",
    "PLANS_ROOT",
    "NESTED",
    "MAX_DEPTH",
    "MAX_DEPTH_RANGE",
    "CONSTANT_NAMES",
    "DIAGNOSTIC_CODE",
    "AMBIGUOUS_WAVE_ID_CODE",
    "RECORD_ROOT_UNREADABLE_CODE",
    "RECORD_FOLDER_UNREADABLE_CODE",
    "RecordLayoutInvalid",
    "RecordRootUnreadable",
    "AmbiguousWaveId",
    "RecordRoots",
    "layout_constants",
    "record_root_is_dir",
    "validate_record_layout",
    "load_record_roots",
    "unvalidated_record_roots",
    "walk_wave_candidates",
    "discover_wave_dirs",
    "wave_id_of",
    "ambiguous_wave_ids",
    "ambiguous_wave_id_diagnostics",
]
