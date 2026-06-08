#!/usr/bin/env python3
"""Build .wavefoundry/framework/scan-allowlist from the live scanner output.

Runs a full scan of the repo, collects all pending findings under
.wavefoundry/framework/, converts them into SHA256-pinned allowlist entries,
writes the allowlist, then removes those entries from scan-findings.json.

Subsequent scans will suppress framework findings via the allowlist instead of
writing them to scan-findings.json.

Usage:
    python3 .wavefoundry/framework/scripts/build_scan_allowlist.py
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from build_pack import FRAMEWORK_REL, should_exclude
from wave_lint_lib.constants import SCAN_ALLOWLIST_PATH, SCAN_FINDINGS_PATH
from wave_lint_lib.secrets_validators import (
    _hash_line,
    check_hardcoded_secrets,
    load_exceptions,
    save_exceptions,
)

FRAMEWORK_PREFIX = FRAMEWORK_REL + "/"

def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_allowlist(root: Path) -> None:
    exceptions_path = root / SCAN_FINDINGS_PATH

    # Remove stale framework entries from scan-findings.json (fresh baseline)
    existing = load_exceptions(root)
    non_framework = [e for e in existing if not e.get("file", "").startswith(FRAMEWORK_PREFIX)]
    if len(non_framework) != len(existing):
        save_exceptions(root, non_framework)
        print(f"Cleared {len(existing) - len(non_framework)} stale framework entries from scan-findings.json")

    # Temporarily clear the allowlist so the scanner sees ALL framework findings,
    # not just those missing from the previous allowlist build.
    allowlist_path = root / SCAN_ALLOWLIST_PATH
    old_allowlist = allowlist_path.read_text(encoding="utf-8") if allowlist_path.exists() else None
    allowlist_path.write_text("# (temporarily cleared for rebuild)\n", encoding="utf-8")

    print("Scanning repository…")
    try:
        check_hardcoded_secrets(root, scan_all=True)
    finally:
        if old_allowlist is not None and not allowlist_path.stat().st_size > 50:
            # Restore on unexpected failure before we write the new one
            allowlist_path.write_text(old_allowlist, encoding="utf-8")

    # Read what the scanner appended
    all_exceptions = load_exceptions(root)
    framework_entries = [e for e in all_exceptions if e.get("file", "").startswith(FRAMEWORK_PREFIX)]
    non_framework_entries = [e for e in all_exceptions if not e.get("file", "").startswith(FRAMEWORK_PREFIX)]

    if not framework_entries:
        print("No framework findings — allowlist is empty.")
        allowlist_path = root / SCAN_ALLOWLIST_PATH
        allowlist_path.write_text(
            "# wavefoundry framework scan allowlist\n"
            "# Format: <sha256>:<rel_path>:<rule_id>:<line_hash>\n",
            encoding="utf-8",
        )
        save_exceptions(root, non_framework_entries)
        return

    # Build allowlist entries from framework findings
    file_sha256_cache: dict[str, str] = {}
    allowlist_lines: list[str] = []

    seen_keys: set[str] = set()
    for entry in sorted(framework_entries, key=lambda e: (e.get("file", ""), e.get("rule_id", ""), e.get("line", 0))):
        rel = entry["file"]
        rule_id = entry["rule_id"]
        file_path = root / rel
        if not file_path.is_file():
            continue
        # Only allowlist files that will be packaged — test files, benchmarks, etc.
        # are not shipped to downstream projects so their false positives don't matter.
        framework_rel = rel[len(FRAMEWORK_PREFIX):]  # path relative to framework root
        if should_exclude(framework_rel, file_path.name):
            continue
        if rel not in file_sha256_cache:
            file_sha256_cache[rel] = _sha256_file(file_path)
        sha256 = file_sha256_cache[rel]
        # Use line_hash from the exception entry; fall back to re-hashing the line.
        line_hash = entry.get("line_hash") or _hash_line(
            file_path.read_text(encoding="utf-8", errors="replace").splitlines()[entry["line"] - 1]
        )
        key = f"{sha256}:{rel}:{rule_id}:{line_hash}"
        if key not in seen_keys:
            seen_keys.add(key)
            allowlist_lines.append(key)

    allowlist_path = root / SCAN_ALLOWLIST_PATH
    out = [
        "# wavefoundry framework scan allowlist",
        "# Format: <sha256>:<rel_path>:<rule_id>:<line_hash>",
        "# Security: each entry pins the exact file content via SHA256. If a file is",
        "# modified, its SHA256 changes and the entry no longer suppresses findings.",
        "# line_hash is MD5(stripped line)[:12] — content-based, survives line number drift.",
        "#",
        *allowlist_lines,
        "",
    ]
    allowlist_path.write_text("\n".join(out), encoding="utf-8")

    # Remove framework entries from scan-findings.json — they're now in the allowlist
    save_exceptions(root, non_framework_entries)

    print(f"Wrote {len(allowlist_lines)} entries to {allowlist_path.relative_to(root)}")
    print(f"Removed {len(framework_entries)} framework entries from scan-findings.json")


if __name__ == "__main__":
    build_allowlist(ROOT)
