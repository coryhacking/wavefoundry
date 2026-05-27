#!/usr/bin/env python3
"""Version comparison check for upgrade pre-flight.

Compares the pack VERSION (installed in .wavefoundry/framework/VERSION) against
the installed framework_revision recorded in .wavefoundry/framework/MANIFEST.

Exit codes:
    0 — pack is newer or the same as installed (safe to proceed with upgrade)
    1 — pack is OLDER than installed (downgrade detected — abort)
    2 — cannot determine (missing VERSION or MANIFEST, or malformed values)

Output (stdout):
    Pack: 1.2.0+12tm5  Installed: 1.0.0+12abc  → upgrade
    Pack: 1.0.0+12abc  Installed: 1.2.0+12tm5  → downgrade
    Pack: 1.0.0+12tm5  Installed: 1.0.0+12tm5  → same

Usage:
    python3 .wavefoundry/framework/scripts/check_version.py [--root <path>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SEMVER_RE = __import__("re").compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:\+[A-Za-z0-9.-]+)?$"
)


def _to_version(s: str):
    """Convert a semver string to a precedence tuple for comparison.

    Build metadata is stripped before comparison per semver spec.

    Raises ValueError for strings that are not valid semver.
    """
    match = _SEMVER_RE.match(s)
    if not match:
        raise ValueError(
            f"Unrecognized version string: {s!r}. "
            "Expected MAJOR.MINOR.PATCH[+<build>]."
        )
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
    )


def _read_pack_version(root: Path) -> str | None:
    """Read the installed pack VERSION string."""
    p = root / ".wavefoundry" / "framework" / "VERSION"
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _read_installed_revision(root: Path) -> str | None:
    """Read framework_revision from MANIFEST."""
    p = root / ".wavefoundry" / "framework" / "MANIFEST"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        val = data.get("framework_revision", "")
        return str(val).strip() or None
    except (OSError, json.JSONDecodeError):
        return None


def compare_versions(pack: str, installed: str) -> str:
    """Return 'upgrade', 'downgrade', or 'same' using semver comparison.

    Both pack and installed must be MAJOR.MINOR.PATCH[+build] semver strings.
    """
    pack_v = _to_version(pack)
    installed_v = _to_version(installed)
    if pack_v > installed_v:
        return "upgrade"
    if pack_v < installed_v:
        return "downgrade"
    return "same"


def check_version(root: Path) -> tuple[int, str]:
    """Return (exit_code, message)."""
    pack = _read_pack_version(root)
    installed = _read_installed_revision(root)

    if pack is None:
        return 2, "Cannot determine pack version — .wavefoundry/framework/VERSION not found"
    if installed is None:
        # No installed revision — treat as "no prior installation"; upgrade is safe.
        msg = f"Pack: {pack}  Installed: (none)  → upgrade (fresh install)"
        return 0, msg

    direction = compare_versions(pack, installed)
    msg = f"Pack: {pack}  Installed: {installed}  → {direction}"
    exit_code = 1 if direction == "downgrade" else 0
    return exit_code, msg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare pack VERSION against installed framework_revision.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root (default: current directory)",
    )
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    exit_code, message = check_version(root)
    print(message)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
