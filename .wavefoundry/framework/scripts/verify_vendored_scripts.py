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

``--offline`` skips the registry entirely: it hashes each vendored file and compares it with the
SHA-256 in the file table, with no network request. Exit 0 every file matches; 1 a file differs
or is missing (each is named); 2 the README cannot be parsed. ``build_pack`` runs the same
comparison before it writes a pack.
"""
from __future__ import annotations

import base64
import hashlib
import io
import os  # noqa: F401  the confined reader's os calls, patched through here by the tests
import sys
import tarfile
import urllib.request
from pathlib import Path
from typing import Callable

# Wave 1zyb2 (1zxnt): the offline half (README parsing, the confined reader, the read cap and
# the offline comparison) lives in the shipped ``vendored_integrity`` module, defined once; its
# public names are re-exported here so ``build_pack`` and existing callers keep working. The
# read cap is not re-exported: ``vendored_integrity.MAX_VENDORED_FILE_BYTES`` is the one value,
# read at call time by every read this module makes.
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

# Change 1zyv1: bytecode goes only to the project cache (``bytecode_cache``),
# never beside the sources; writes stay off until configure() enables the cache.
if __name__ == "__main__" or sys.pycache_prefix is None:
    sys.dont_write_bytecode = True
import bytecode_cache  # noqa: E402

if __name__ == "__main__":
    bytecode_cache.configure()

from vendored_integrity import (  # noqa: E402,F401  re-exported
    ReadmeError,
    RegistryEntry,
    VendoredFile,
    VendoredFileRefused,
    _FILE_ROW_RE,
    _FILE_TABLE_HEADER,
    _REGISTRY_ROW_RE,
    _REGISTRY_TABLE_HEADER,
    _SEPARATOR_ROW_RE,
    _TABLE_LINE_RE,
    _cause,
    _read_readme,
    _read_regular,
    _readme_label,
    _row_label,
    _row_path_problem,
    _table_rows,
    offline_problems,
    parse_readme,
    read_vendored_file,
)

REGISTRY_PREFIX = "https://registry.npmjs.org/"
REQUEST_TIMEOUT_SECONDS = 60
# The largest vendored tarball is a few megabytes; refuse anything far larger.
MAX_TARBALL_BYTES = 32 * 1024 * 1024

DEFAULT_VENDOR_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "vendor"

_SCRIPT_SUFFIXES = (".js", ".mjs", ".cjs")


class FetchError(Exception):
    """A download failed or was refused (exit 2)."""


class FetchRefused(FetchError):
    """The verifier refused a download on purpose: a non-registry URL, a redirect that left the
    registry, or a body over the size cap (printed as ``refused:``)."""


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
            # The target is server-supplied, so only the refusal class is named (wave 200xy).
            raise FetchRefused("redirect left the registry")
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
                raise FetchRefused("redirect left the registry")
            body = response.read(MAX_TARBALL_BYTES + 1)
    except FetchError:
        raise
    except (OSError, ValueError) as exc:
        # The class only: an exception's text can carry server-supplied words (an HTTP reason
        # phrase), so it is never printed (wave 200xy, change 200v1).
        raise FetchError(type(exc).__name__) from exc
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
        files, registry = _read_readme(readme_path, vendor_dir)
    except ReadmeError as exc:
        print(f"error: cannot parse {_readme_label(readme_path, vendor_dir)}: {exc}")
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
                    print(f"{_row_label(f)}: missing member {f.source} in {package}")
                    failed = True
                    continue
                try:
                    vendored = read_vendored_file(vendor_dir, f.path)
                except (OSError, VendoredFileRefused) as exc:
                    print(f"{_row_label(f)}: cannot read vendored file: {_cause(exc)}")
                    failed = True
                    continue
                data = handle.read()
                member_sha = hashlib.sha256(data).hexdigest()
                vendored_sha = hashlib.sha256(vendored).hexdigest()
                if member_sha != f.sha256 or vendored_sha != f.sha256:
                    print(f"{_row_label(f)}: sha256 mismatch: recorded {f.sha256}, tarball member {member_sha}, "
                          f"vendored {vendored_sha}")
                    failed = True
                elif vendored != data:
                    print(f"{_row_label(f)}: content differs from {f.source}")
                    failed = True
                else:
                    print(f"{_row_label(f)}: ok (matches {package} {f.source})")
    # A mismatch outranks a package that could not be checked.
    if failed:
        return 1
    return 2 if unverifiable else 0


def unlisted_scripts(vendor_dir: Path) -> list[str]:
    """Every ``*.js``, ``*.mjs`` or ``*.cjs`` file under ``vendor_dir`` (recursively, any letter case
    in the suffix) that the file table does not list.

    Dotfiles such as ``.DS_Store``, the README and licence files are not scripts and are ignored.
    """
    files, _registry = _read_readme(vendor_dir / "README.md", vendor_dir)
    listed = {f.path for f in files}
    found = (
        p.relative_to(vendor_dir).as_posix()
        for p in vendor_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in _SCRIPT_SUFFIXES
    )
    return sorted(path for path in found if path not in listed)


def verify_offline(vendor_dir: Path) -> int:
    """Print one line per problem and return the offline exit code (0, 1 or 2)."""
    try:
        problems = offline_problems(vendor_dir)
    except ReadmeError as exc:
        print(f"error: cannot parse README.md: {exc}")
        return 2
    for problem in problems:
        print(problem)
    if problems:
        return 1
    print("ok: every vendored file matches its recorded SHA-256")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["--offline"]:
        return verify_offline(DEFAULT_VENDOR_DIR)
    if args:
        print(__doc__)
        return 0 if args in (["-h"], ["--help"]) else 2
    return verify(DEFAULT_VENDOR_DIR / "README.md", DEFAULT_VENDOR_DIR)


if __name__ == "__main__":
    sys.exit(main())
