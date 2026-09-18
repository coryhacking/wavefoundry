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

import os
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

# ---------------------------------------------------------------------------
# Fork-editable layout constants. Edit these at merge time; keep them
# repository-relative POSIX paths. ``NESTED`` enables the bounded recursive
# wave walk (wave 1y043); ``MAX_DEPTH`` counts the wave folder's own depth
# below the waves root, so ``1`` means direct children only.
# ---------------------------------------------------------------------------
WAVES_ROOT = "docs/waves"
PLANS_ROOT = "docs/plans"
NESTED = False
MAX_DEPTH = 4

MAX_DEPTH_RANGE = (1, 8)
CONSTANT_NAMES = ("WAVES_ROOT", "PLANS_ROOT", "NESTED", "MAX_DEPTH")

AMBIGUOUS_WAVE_ID_CODE = "ambiguous_wave_id"
DIAGNOSTIC_CODE = "record_layout_invalid"


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

    @property
    def waves_prefix(self) -> str:
        """Repo-relative prefix with a trailing slash, for ``startswith`` checks."""
        return self.waves_rel + "/"

    @property
    def plans_prefix(self) -> str:
        return self.plans_rel + "/"


def layout_constants() -> tuple[object, object, object, object]:
    """The current constant values, read at call time. Cache keys fold this in
    so a process whose constants were patched (tests) re-resolves."""
    return (WAVES_ROOT, PLANS_ROOT, NESTED, MAX_DEPTH)


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
    return diagnostics


def load_record_roots(root: Path) -> RecordRoots:
    """Resolve the record roots for ``root``. Raises :class:`RecordLayoutInvalid`
    (fail-closed) when the layout constants are invalid for this repository."""
    root = Path(root)
    diagnostics = validate_record_layout(root)
    if diagnostics:
        raise RecordLayoutInvalid(diagnostics)
    waves_rel = "/".join(_canonical_parts(WAVES_ROOT))
    plans_rel = "/".join(_canonical_parts(PLANS_ROOT))
    return RecordRoots(
        waves_rel=waves_rel,
        plans_rel=plans_rel,
        waves=_join_rel(root, waves_rel),
        plans=_join_rel(root, plans_rel),
        nested=bool(NESTED),
        max_depth=int(MAX_DEPTH),
    )


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

def _list_subdirs(directory: Path, *, guarded: bool = True) -> list[Path]:
    """Sorted child directories. With ``guarded`` (the nested walk) symlinked
    and dot-prefixed entries are skipped; without it (the flat layout) the
    listing matches the pre-change ``iterdir`` enumeration, so a symlinked
    wave folder is still found and refused downstream by the record-writer
    path-escape guards rather than silently vanishing. Files are never
    candidates in either mode. The single walk primitive; tests instrument it
    to prove depth and call bounds."""
    try:
        entries = list(directory.iterdir())
    except OSError:
        return []
    out = []
    for entry in sorted(entries, key=lambda p: p.name):
        if guarded and entry.name.startswith("."):
            continue
        try:
            if (guarded and entry.is_symlink()) or not entry.is_dir():
                continue
        except OSError:
            continue
        out.append(entry)
    return out


def _has_wave_md(directory: Path) -> bool:
    try:
        return (directory / "wave.md").is_file()
    except OSError:
        return False


def walk_wave_candidates(root: Path, roots: RecordRoots | None = None) -> list[Path]:
    """Every directory that may hold a wave record, under the discovery guards.

    Flat layout: the waves root's child directories, exactly as ``iterdir``
    enumerated them before (content-driven validators such as the orphan-ledger
    check need directories WITHOUT a ``wave.md`` too). Nested layout: a
    bounded depth-first walk to ``max_depth`` that never enters a symlink or a
    dot-prefixed directory and never descends into a directory that holds a
    ``wave.md`` (a wave folder's own subdirectories are evidence, not waves).
    """
    roots = roots or load_record_roots(root)
    if not roots.waves.is_dir():
        return []
    if not roots.nested:
        return _list_subdirs(roots.waves, guarded=False)
    found: list[Path] = []
    stack: list[tuple[Path, int]] = [(roots.waves, 0)]
    while stack:
        directory, depth = stack.pop()
        if depth >= roots.max_depth:
            continue
        for child in reversed(_list_subdirs(directory)):
            found.append(child)
            if not _has_wave_md(child):
                stack.append((child, depth + 1))
    return sorted(found)


def discover_wave_dirs(root: Path, roots: RecordRoots | None = None) -> list[Path]:
    """Every wave folder (a directory containing ``wave.md``) under the waves
    root: immediate children when ``NESTED`` is false, otherwise the bounded
    walk of :func:`walk_wave_candidates`."""
    return [d for d in walk_wave_candidates(root, roots) if _has_wave_md(d)]


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
    "RecordLayoutInvalid",
    "AmbiguousWaveId",
    "RecordRoots",
    "layout_constants",
    "validate_record_layout",
    "load_record_roots",
    "unvalidated_record_roots",
    "walk_wave_candidates",
    "discover_wave_dirs",
    "wave_id_of",
    "ambiguous_wave_ids",
    "ambiguous_wave_id_diagnostics",
]
