#!/usr/bin/env python3
"""Version comparison check for upgrade pre-flight.

Compares the pack VERSION (installed in .wavefoundry/framework/VERSION) against
the installed framework_revision recorded in .wavefoundry/framework/MANIFEST.

Exit codes:
    0 — pack is newer or the same as installed (safe to proceed with upgrade)
    1 — pack is OLDER than installed (downgrade detected — abort)
    2 — cannot determine (missing VERSION or MANIFEST, or malformed values)

Output (stdout):
    Pack: 2026-05-19a  Installed: 2026-05-10a  → upgrade
    Pack: 2026-05-10a  Installed: 2026-05-19a  → downgrade
    Pack: 2026-05-19a  Installed: 2026-05-19a  → same

Usage:
    python3 .wavefoundry/framework/scripts/check_version.py [--root <path>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


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
    """Return 'upgrade', 'downgrade', or 'same' by lexicographic comparison.

    Version strings use format YYYY-MM-DDx (e.g. '2026-05-19a') which is
    lexicographically ordered — string comparison is correct.
    """
    if pack > installed:
        return "upgrade"
    if pack < installed:
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
