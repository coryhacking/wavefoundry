"""Shared stdlib path-containment predicate; caller policy stays with callers."""

from pathlib import Path
import stat


def contained_resolved_path(root: Path, candidate: Path) -> Path | None:
    """Compare already-resolved absolute native paths without filesystem work.

    Inputs must contain no unresolved ``..``. The caller owns resolution,
    symlink policy and failure handling. Native path flavor determines case
    semantics. This helper performs no normalization, resolve, stat or lstat.
    """
    return candidate if candidate.is_relative_to(root) else None


def contained_path(root: Path, candidate: Path, *, strict: bool = False,
                   refuse_symlink_components: bool = False) -> Path | None:
    """Return the resolved candidate inside resolved root, or ``None``.

    Relative candidates are relative to root. Non-strict resolution follows
    existing prefixes physically and collapses missing tails lexically; strict
    resolution requires the candidate to exist. Root itself is contained, and
    a symlink spelling of root is supported. The optional lstat walk refuses
    every symlink below root, including links that leave and re-enter it.
    OSError, RuntimeError (including older Python symlink loops), and ValueError
    map to None. Callers with raising contracts retain their own boundaries.

    No case normalization is performed: native pathlib containment governs
    spelling (POSIX case variants refuse; Windows paths compare case-folded).
    Case aliases requiring samefile belong to caller policy. Extended Windows
    prefixes may be false rejects. Write callers must use the returned path.
    This is not a race-free open primitive. Forks should extend this owner,
    not introduce a second containment implementation.
    """
    try:
        supplied_root = Path(root)
        resolved_root = supplied_root.resolve()
        path = Path(candidate)
        if not path.is_absolute():
            path = supplied_root / path
        if refuse_symlink_components:
            # Do not resolve away links before inspecting their spelling.
            absolute = path.absolute()
            try:
                relative = absolute.relative_to(supplied_root.absolute())
                cursor = supplied_root.absolute()
            except ValueError:
                relative = absolute.relative_to(resolved_root)
                cursor = resolved_root
            for part in relative.parts:
                cursor = cursor / part
                try:
                    mode = cursor.lstat().st_mode
                except FileNotFoundError:
                    continue
                if stat.S_ISLNK(mode):
                    return None
        resolved = path.resolve(strict=strict)
        # Python 3.13 non-strict resolve leaves a loop unresolved rather than
        # raising. stat distinguishes that uncertainty from an allowed missing
        # tail without requiring missing write targets to exist.
        if not strict:
            try:
                path.stat()
            except FileNotFoundError:
                pass
        return contained_resolved_path(resolved_root, resolved)
    except (OSError, RuntimeError, ValueError):
        return None
