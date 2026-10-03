#!/usr/bin/env python3
"""Opt-in online integrity check for the vendored dashboard scripts (wave 1zls7, change 1zltw).

Reads the file table and the registry table in ``dashboard/vendor/README.md`` and, for each
package, downloads the recorded tarball from the npm registry, compares its SHA-512 (in npm's
``sha512-<base64>`` form) with the recorded ``dist.integrity``, reads the recorded source member
from the tarball in memory (nothing is extracted to disk), and compares that member's SHA-256 and
bytes with the vendored file and the file table.

Development only: this script uses the network, so it is never part of the default test suite,
setup, upgrade, packaging or the MCP server, and ``build_pack`` excludes it from the distribution.
It makes network requests only when run directly, and only to ``https://registry.npmjs.org/``.

Exit codes: 0 every check passed; 1 at least one check failed (a mismatch or a missing member),
even when another package could not be checked; 2 the check could not be made and nothing
mismatched (the README cannot be parsed, a download was refused or a download failed).

Output labels: ``refused:`` names a refusal the verifier made on purpose (a non-registry URL, a
redirect that left the registry, a tarball over the size cap), which stops a release;
``download failed:`` names a download that could not complete (network, proxy or TLS).

    python3 .wavefoundry/framework/scripts/verify_vendored_scripts.py
"""
from __future__ import annotations

import base64
import hashlib
import io
import re
import sys
import tarfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

REGISTRY_PREFIX = "https://registry.npmjs.org/"
REQUEST_TIMEOUT_SECONDS = 60
# The largest vendored tarball is a few megabytes; refuse anything far larger.
MAX_TARBALL_BYTES = 32 * 1024 * 1024

DEFAULT_VENDOR_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "vendor"

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


class FetchError(Exception):
    """A download failed or was refused (exit 2)."""


class FetchRefused(FetchError):
    """The verifier refused a download on purpose: a non-registry URL, a redirect that left the
    registry, or a body over the size cap (printed as ``refused:``)."""


class ReadmeError(Exception):
    """The vendor README cannot be parsed (exit 2)."""


@dataclass(frozen=True)
class VendoredFile:
    path: str
    package: str
    source: str
    sha256: str


@dataclass(frozen=True)
class RegistryEntry:
    package: str
    url: str
    integrity: str


def _table_rows(lines: list[str], header: str, row_re: "re.Pattern[str]", name: str) -> list["re.Match[str]"]:
    """The data rows of the one table whose header line is exactly ``header``.

    Raises :class:`ReadmeError` when the header is absent or repeated, when the separator row
    does not follow it, or when a data row does not fully match ``row_re`` (naming the line).
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
                raise ReadmeError(f"line {index + 1}: indented {name} table row: {line}")
            if "|" in line and line.strip():
                # The leading pipe is optional in a rendered table, so this is still a row.
                raise ReadmeError(f"line {index + 1}: malformed {name} table row: {line}")
            end = index
            break
        match = row_re.fullmatch(line)
        if match is None:
            raise ReadmeError(f"line {index + 1}: malformed {name} table row: {line}")
        rows.append(match)
    # A row after the table's end (past a blank line, say) would otherwise be dropped
    # silently: refuse any table-shaped line before the next ``## `` heading.
    for index in range(end, len(lines)):
        line = lines[index]
        if line.startswith("## "):
            break
        if _TABLE_LINE_RE.match(line):
            raise ReadmeError(f"line {index + 1}: {name} table row after the end of the table: {line}")
    return rows


def parse_readme(text: str) -> tuple[list[VendoredFile], dict[str, RegistryEntry]]:
    """Return the file table rows and the registry table keyed by ``name@version``."""
    lines = text.splitlines()
    files = [
        VendoredFile(m["path"], m["package"], m["source"], m["sha256"])
        for m in _table_rows(lines, _FILE_TABLE_HEADER, _FILE_ROW_RE, "file")
    ]
    registry: dict[str, RegistryEntry] = {}
    for m in _table_rows(lines, _REGISTRY_TABLE_HEADER, _REGISTRY_ROW_RE, "registry"):
        if m["package"] in registry:
            raise ReadmeError(f"duplicate registry row for {m['package']}")
        registry[m["package"]] = RegistryEntry(m["package"], m["url"], m["integrity"])
    if not files or not registry:
        raise ReadmeError("no file table rows or no registry table rows found")
    for f in files:
        if f.package not in registry:
            raise ReadmeError(f"{f.path}: package {f.package} has no registry row")
    return files, registry


def _is_registry_url(url: str) -> bool:
    return url.startswith(REGISTRY_PREFIX)


class _RegistryRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Check each redirect target before it is followed (wave 1zls7, change 1zodv).

    ``urllib`` resolves the ``Location`` header against the request URL before calling
    :meth:`redirect_request`, so the check sees the absolute target. An off-registry target is
    refused here and never contacted; a chain that leaves the registry is therefore refused at
    its first off-registry hop, even when it would return to the registry later.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        if not _is_registry_url(newurl):
            fp.close()
            raise FetchRefused(f"redirect left the registry: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open(url: str):  # noqa: ANN202
    """Open ``url`` with the default handlers (proxy, TLS) and the checking redirect handler."""
    opener = urllib.request.build_opener(_RegistryRedirectHandler)
    return opener.open(url, timeout=REQUEST_TIMEOUT_SECONDS)


def default_fetch(url: str) -> bytes:
    """Download ``url`` from the npm registry with a timeout, a size cap and the default TLS checks.

    ``urllib`` honours the standard proxy environment variables (``HTTPS_PROXY`` and so on).
    Every redirect target is checked before it is followed; the final URL is checked again
    after the response arrives, as defence in depth.
    """
    if not _is_registry_url(url):
        raise FetchRefused(f"non-registry URL {url}")
    try:
        with _open(url) as response:
            final_url = response.geturl()
            if not _is_registry_url(final_url):
                raise FetchRefused(f"redirect left the registry: {final_url}")
            body = response.read(MAX_TARBALL_BYTES + 1)
    except FetchError:
        raise
    except (OSError, ValueError) as exc:
        raise FetchError(f"{type(exc).__name__}: {exc}") from exc
    if len(body) > MAX_TARBALL_BYTES:
        raise FetchRefused(f"tarball exceeds the size cap of {MAX_TARBALL_BYTES} bytes")
    return body


def _npm_integrity(data: bytes) -> str:
    return "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode("ascii")


def verify(
    readme_path: Path,
    vendor_dir: Path,
    fetch: Callable[[str], bytes] = default_fetch,
) -> int:
    """Verify every package and file; print one line each and return the exit code."""
    try:
        files, registry = parse_readme(readme_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ReadmeError) as exc:
        print(f"error: cannot parse {readme_path}: {exc}")
        return 2
    failed = False
    unverifiable = False
    for package in sorted(registry):
        entry = registry[package]
        if not _is_registry_url(entry.url):
            print(f"{package}: refused: non-registry URL {entry.url}")
            unverifiable = True
            continue
        try:
            tarball = fetch(entry.url)
        except FetchRefused as exc:
            print(f"{package}: refused: {exc}")
            unverifiable = True
            continue
        except FetchError as exc:
            print(f"{package}: download failed: {exc}")
            unverifiable = True
            continue
        actual = _npm_integrity(tarball)
        if actual != entry.integrity:
            print(f"{package}: integrity mismatch: recorded {entry.integrity}, downloaded {actual}")
            failed = True
            continue
        print(f"{package}: ok (tarball integrity matches)")
        try:
            archive = tarfile.open(fileobj=io.BytesIO(tarball), mode="r:*")
        except (tarfile.TarError, OSError) as exc:
            print(f"{package}: cannot read tarball: {exc}")
            failed = True
            continue
        with archive:
            for f in (f for f in files if f.package == package):
                try:
                    member = archive.getmember(f.source)
                except KeyError:
                    member = None
                handle = archive.extractfile(member) if member is not None and member.isfile() else None
                if handle is None:
                    print(f"{f.path}: missing member {f.source} in {package}")
                    failed = True
                    continue
                data = handle.read()
                member_sha = hashlib.sha256(data).hexdigest()
                try:
                    vendored = (vendor_dir / f.path).read_bytes()
                except OSError as exc:
                    print(f"{f.path}: cannot read vendored file: {exc}")
                    failed = True
                    continue
                vendored_sha = hashlib.sha256(vendored).hexdigest()
                if member_sha != f.sha256 or vendored_sha != f.sha256:
                    print(f"{f.path}: sha256 mismatch: recorded {f.sha256}, tarball member {member_sha}, "
                          f"vendored {vendored_sha}")
                    failed = True
                elif vendored != data:
                    print(f"{f.path}: content differs from {f.source}")
                    failed = True
                else:
                    print(f"{f.path}: ok (matches {package} {f.source})")
    # A mismatch outranks a package that could not be checked.
    if failed:
        return 1
    return 2 if unverifiable else 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args:
        print(__doc__)
        return 0 if args in (["-h"], ["--help"]) else 2
    return verify(DEFAULT_VENDOR_DIR / "README.md", DEFAULT_VENDOR_DIR)


if __name__ == "__main__":
    sys.exit(main())
