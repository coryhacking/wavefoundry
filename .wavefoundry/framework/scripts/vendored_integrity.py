"""Shipped offline integrity check for the vendored dashboard scripts (wave 1zyb2, change 1zxnt).

Reads the file table and the registry table in ``dashboard/vendor/README.md`` and compares each
listed vendored file's SHA-256 with the table, as bytes, with no network request. This is the
offline half of ``verify_vendored_scripts`` moved verbatim into a module that ships in every
distribution (``verify_vendored_scripts`` holds the network check and is excluded from packs, and
re-exports these names), so ``build_pack`` and ``wf_audit`` share one reader.

Standard library only.
"""
from __future__ import annotations

import hashlib
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path

# Wave 1zxo0 (1zxns): the per-file read cap for the README and every listed vendored file. The
# largest vendored file is about 1.6 MB, so the network check's tarball cap (32 MiB) is a simple,
# generous bound; ``verify_vendored_scripts`` pins the two as equal.
MAX_VENDORED_FILE_BYTES = 32 * 1024 * 1024

# Each table is found by its exact header line (wave 1zls7, change 1zodv); every line after
# its separator row, up to the first line that does not start with ``|``, is a data row of
# that table and must fully match the table's row pattern. An indented row, or a
# table-shaped line after the table's end and before the next ``## `` heading, is refused.
_FILE_TABLE_HEADER = "| File | Package | Source in the tarball | Licence | SHA-256 |"
_REGISTRY_TABLE_HEADER = "| Package | Tarball | `dist.integrity` |"
_TABLE_LINE_RE = re.compile(r"\s*\|")
_SEPARATOR_ROW_RE = re.compile(r"\|(?:\s*:?-+:?\s*\|)+\s*")
_FILE_ROW_RE = re.compile(
    r"\| `(?P<path>[^`]+)` \| `(?P<package>[^`]+@[^`]+)` \| `(?P<source>[^`]+)` \| [^|]+ \| "
    r"`(?P<sha256>[0-9a-f]{64})` \|\s*"
)
_REGISTRY_ROW_RE = re.compile(
    r"\| `(?P<package>[^`]+@[^`]+)` \| `(?P<url>[^`]+)` \| `(?P<integrity>sha512-[A-Za-z0-9+/=]+)` \|\s*"
)


class ReadmeError(Exception):
    """The vendor README cannot be read or parsed (exit 2)."""


class VendoredFileRefused(Exception):
    """A listed vendored file (or the README) was refused before or instead of being read
    (wave 1zxo0, change 1zxns). The message is a cause class only, never a path."""


@dataclass(frozen=True)
class VendoredFile:
    path: str
    package: str
    source: str
    sha256: str
    # 1-based position in the file table, so a row refused for its spelling is
    # named by number rather than echoed (wave 1zxo0, change 1zxns).
    row: int = 0


@dataclass(frozen=True)
class RegistryEntry:
    package: str
    url: str
    integrity: str


def _table_rows(lines: list[str], header: str, row_re: "re.Pattern[str]", name: str) -> list["re.Match[str]"]:
    """The data rows of the one table whose header line is exactly ``header``.

    Raises :class:`ReadmeError` when the header is absent or repeated, when the separator row
    does not follow it, or when a data row does not fully match ``row_re``. The message names
    the line number and the cause only, never the row text, so a row carrying control
    characters or a path is not echoed to a terminal or an audit payload (wave 1zyb2).
    """
    starts = [index for index, line in enumerate(lines) if line.rstrip() == header]
    if len(starts) != 1:
        raise ReadmeError(f"expected exactly one {name} table header, found {len(starts)}")
    start = starts[0]
    if start + 1 >= len(lines) or not _SEPARATOR_ROW_RE.fullmatch(lines[start + 1]):
        raise ReadmeError(f"line {start + 2}: the {name} table header is not followed by a separator row")
    rows: list[re.Match[str]] = []
    end = len(lines)
    for index in range(start + 2, len(lines)):
        line = lines[index]
        if not line.startswith("|"):
            if line.lstrip().startswith("|"):
                raise ReadmeError(f"line {index + 1}: indented {name} table row")
            if "|" in line and line.strip():
                # The leading pipe is optional in a rendered table, so this is still a row.
                raise ReadmeError(f"line {index + 1}: malformed {name} table row")
            end = index
            break
        match = row_re.fullmatch(line)
        if match is None:
            raise ReadmeError(f"line {index + 1}: malformed {name} table row")
        rows.append(match)
    # A row after the table's end (past a blank line, say) would otherwise be dropped
    # silently: refuse any table-shaped line before the next ``## `` heading.
    for index in range(end, len(lines)):
        line = lines[index]
        if line.startswith("## "):
            break
        if _TABLE_LINE_RE.match(line):
            raise ReadmeError(f"line {index + 1}: {name} table row after the end of the table")
    return rows


def parse_readme(text: str) -> tuple[list[VendoredFile], dict[str, RegistryEntry]]:
    """Return the file table rows and the registry table keyed by ``name@version``."""
    lines = text.splitlines()
    files = [
        VendoredFile(m["path"], m["package"], m["source"], m["sha256"], row)
        for row, m in enumerate(_table_rows(lines, _FILE_TABLE_HEADER, _FILE_ROW_RE, "file"), start=1)
    ]
    registry: dict[str, RegistryEntry] = {}
    for number, m in enumerate(_table_rows(lines, _REGISTRY_TABLE_HEADER, _REGISTRY_ROW_RE, "registry"), start=1):
        if m["package"] in registry:
            raise ReadmeError(f"registry row {number}: duplicate package")
        registry[m["package"]] = RegistryEntry(m["package"], m["url"], m["integrity"])
    if not files or not registry:
        raise ReadmeError("no file table rows or no registry table rows found")
    for f in files:
        if f.package not in registry:
            raise ReadmeError(f"row {f.row}: package has no registry row")
    return files, registry


def _row_path_problem(rel: str) -> str | None:
    """The lexical refusal for a file-table path, or ``None`` when the spelling is acceptable.

    Identical on every platform, so a table that passes on one OS passes on all: an absolute or
    drive-prefixed path, a backslash, an empty component, ``.`` or ``..``, or a control
    character is refused.
    """
    if any(ord(ch) < 0x20 or 0x7F <= ord(ch) < 0xA0 for ch in rel):
        return "path contains a control character"
    if not rel or rel.startswith("/") or re.match(r"[A-Za-z]:", rel):
        return "path is absolute or drive-prefixed"
    if "\\" in rel:
        return "path contains a backslash"
    if any(part in ("", ".", "..") for part in rel.split("/")):
        return "path has an empty, '.' or '..' component"
    return None


def _row_label(f: VendoredFile) -> str:
    """How a problem line names a row: its path as written when the path passes the lexical
    checks, else ``row N`` (its file-table position), so an absolute, traversing or
    control-character spelling is never echoed (wave 1zxo0, change 1zxns)."""
    if _row_path_problem(f.path) is None:
        return f.path
    return f"row {f.row}"


def _read_regular(path: Path, cap: int | None = None) -> bytes:
    """Read ``path`` only as a regular file of at most ``cap`` bytes.

    ``lstat`` must show a regular file (a link, directory, FIFO or device is refused without
    being opened). On POSIX the bytes come from an ``O_RDONLY|O_NOFOLLOW|O_NONBLOCK`` open whose
    ``fstat`` must show a regular file with the ``lstat`` identity. At most ``cap + 1`` bytes
    are read and more than ``cap`` is refused, so the ``lstat`` size is not trusted. Raises
    :class:`VendoredFileRefused` (cause class only) or ``OSError``. ``cap`` defaults to
    :data:`MAX_VENDORED_FILE_BYTES`, read at call time.
    """
    if cap is None:
        cap = MAX_VENDORED_FILE_BYTES
    before = os.lstat(path)
    if not stat.S_ISREG(before.st_mode):
        raise VendoredFileRefused("not a regular file")
    if before.st_size > cap:
        raise VendoredFileRefused(f"exceeds the size cap of {cap} bytes")
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is not None:
        flags = os.O_RDONLY | nofollow | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_CLOEXEC", 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as handle:
            after = os.fstat(handle.fileno())
            if not stat.S_ISREG(after.st_mode) or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino):
                raise VendoredFileRefused("changed between check and read")
            data = handle.read(cap + 1)
    else:
        # Windows: no O_NOFOLLOW; the lstat check above stands alone (a documented window).
        with open(path, "rb") as handle:
            data = handle.read(cap + 1)
    if len(data) > cap:
        raise VendoredFileRefused(f"exceeds the size cap of {cap} bytes")
    return data


def read_vendored_file(vendor_dir: Path, rel: str) -> bytes:
    """The one confined reader for a file-table row (wave 1zxo0, change 1zxns).

    Refuses, without reading, a row path that fails :func:`_row_path_problem`, resolves outside
    the resolved ``vendor_dir``, has a link component below ``vendor_dir``, is not a regular
    file, or exceeds :data:`MAX_VENDORED_FILE_BYTES`. Raises :class:`VendoredFileRefused` or
    ``OSError``; neither message carries an absolute path.
    """
    problem = _row_path_problem(rel)
    if problem:
        raise VendoredFileRefused(problem)
    base = Path(vendor_dir)
    cursor = base
    for part in rel.split("/"):
        cursor = cursor / part
        try:
            mode = os.lstat(cursor).st_mode
        except FileNotFoundError:
            raise VendoredFileRefused("missing") from None
        if stat.S_ISLNK(mode):
            raise VendoredFileRefused("path has a link component")
    try:
        inside = cursor.resolve(strict=True).is_relative_to(base.resolve(strict=True))
    except (OSError, RuntimeError):
        inside = False
    if not inside:
        raise VendoredFileRefused("path resolves outside the vendor folder")
    return _read_regular(cursor)


def _cause(exc: BaseException) -> str:
    """A path-free cause: a refusal's own reason, an ``OSError``'s strerror, else the class."""
    if isinstance(exc, VendoredFileRefused):
        return str(exc)
    if isinstance(exc, OSError) and exc.strerror:
        return f"{type(exc).__name__}: {exc.strerror}"
    return type(exc).__name__


def _readme_label(readme_path: Path, vendor_dir: Path | None) -> str:
    if vendor_dir is not None:
        try:
            return Path(readme_path).relative_to(vendor_dir).as_posix()
        except ValueError:
            pass
    return Path(readme_path).name


def _read_readme(readme_path: Path, vendor_dir: Path | None = None) -> tuple[list[VendoredFile], dict[str, RegistryEntry]]:
    """Read and parse the README through the regular-file and size checks.

    A read failure raises :class:`ReadmeError` naming the README relative to the vendor folder
    and the cause class only, never an absolute path or raw exception text.
    """
    try:
        text = _read_regular(Path(readme_path)).decode("utf-8")
    except (OSError, UnicodeDecodeError, VendoredFileRefused) as exc:
        raise ReadmeError(f"cannot read {_readme_label(readme_path, vendor_dir)}: {_cause(exc)}") from None
    return parse_readme(text)


def offline_problems(vendor_dir: Path) -> list[str]:
    """Compare each vendored file's SHA-256 with the file table; return one problem per file.

    Reads only ``vendor_dir/README.md`` and the files it lists, as bytes, so the result is the
    same on every platform and nothing touches the network. An empty list means every file
    matches. Raises :class:`ReadmeError` when the README cannot be read or parsed.

    Wave 1zxo0 (1zxns): every read goes through :func:`read_vendored_file`, so a row naming a
    path outside the vendor folder, through a link, or a non-regular or oversized file is a
    problem line, with nothing read and no digest printed. The line names the row's path as
    written when that path passes the lexical checks, else the row's number in the file table.
    """
    files, _registry = _read_readme(vendor_dir / "README.md", vendor_dir)
    problems: list[str] = []
    for f in files:
        try:
            actual = hashlib.sha256(read_vendored_file(vendor_dir, f.path)).hexdigest()
        except (OSError, VendoredFileRefused) as exc:
            problems.append(f"{_row_label(f)}: missing or unreadable vendored file: {_cause(exc)}")
            continue
        if actual != f.sha256:
            problems.append(f"{_row_label(f)}: sha256 mismatch: recorded {f.sha256}, vendored {actual}")
    return problems

