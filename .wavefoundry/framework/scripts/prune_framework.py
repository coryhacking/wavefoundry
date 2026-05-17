#!/usr/bin/env python3
"""Remove pack-delivered files that were dropped from a newer framework pack.

Usage (run from repo root after unzipping the new pack):

    python3 .wavefoundry/framework/scripts/prune_framework.py [--dry-run]

How it works
------------
Before upgrading, the installed `.wavefoundry/framework/MANIFEST` lists every
file that was delivered by the old pack.  After `unzip -o` the new pack, the
same path holds the new MANIFEST.  This script computes the set difference
(old - new) and deletes those files, then removes any directories that became
empty as a result.

Only files that appear in the old MANIFEST are candidates for deletion.
User-created files under `.wavefoundry/framework/` (regenerated indexes,
local overrides, etc.) are never listed in any MANIFEST and are never touched.

The old MANIFEST is passed via --old-manifest (a path you saved before unzip).
If --old-manifest is omitted or the file does not exist (upgrading from a
pre-MANIFEST pack), the script falls back to a built-in legacy list covering
all files shipped in packs 2026-04-29a through 2026-05-02d that are no longer
present in the current pack.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Legacy prune list — files/dirs shipped in packs before MANIFEST support
# (2026-04-29a through 2026-05-02d) that are no longer in the current pack.
# Paths are relative to the framework root. Entries ending with "/" are
# treated as directories and removed with shutil.rmtree.
# ---------------------------------------------------------------------------
_LEGACY_REMOVALS: list[str] = [
    "scripts/render_hooks.py",
    "scripts/build_zip.py",
    "scripts/docs-lint.py",
    "scripts/docs-gardener.py",
    "scripts/docs_lint_lib/",
    "scripts/run_tests.py",
    "scripts/tests/",
]


def _read_manifest(path: Path) -> set[str]:
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def _prune_legacy(framework_dir: Path, *, dry_run: bool = False) -> list[str]:
    """Delete known legacy paths from pre-MANIFEST packs."""
    deleted: list[str] = []
    for rel in _LEGACY_REMOVALS:
        target = framework_dir / rel.rstrip("/")
        if rel.endswith("/"):
            if target.is_dir():
                if dry_run:
                    print(f"[dry-run] would remove dir: {target}")
                else:
                    shutil.rmtree(target)
                    print(f"removed dir: {target}")
                deleted.append(str(target))
        else:
            if target.is_file():
                if dry_run:
                    print(f"[dry-run] would delete: {target}")
                else:
                    target.unlink()
                    print(f"deleted: {target}")
                deleted.append(str(target))
    return deleted


def _prune_meta_json(framework_dir: Path, removed: set[str], *, dry_run: bool = False) -> bool:
    """Remove pruned paths from framework index meta.json.

    Returns True when the file was updated.
    """
    if not removed:
        return False
    meta_path = framework_dir / "index" / "meta.json"
    if not meta_path.is_file():
        return False
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(meta, dict):
        return False

    changed = False
    for key_name in ("file_meta", "file_hashes"):
        raw = meta.get(key_name)
        if not isinstance(raw, dict) or not raw:
            continue
        kept = {}
        for path, value in raw.items():
            should_remove = any(path == rel or path.startswith(rel + "/") for rel in removed)
            if should_remove:
                changed = True
                continue
            kept[path] = value
        if changed:
            meta[key_name] = kept

    if not changed or dry_run:
        return changed

    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return True


def prune(
    framework_dir: Path,
    old_manifest_path: Path | None,
    *,
    dry_run: bool = False,
) -> list[str]:
    """Delete pack-removed files.  Returns list of deleted (or would-delete) paths.

    If old_manifest_path is None or does not exist, falls back to the built-in
    legacy removal list covering packs 2026-04-29a through 2026-05-02d.
    """
    new_manifest_path = framework_dir / "MANIFEST"
    meta_cleanup_targets: set[str] = set()

    # Fall back to legacy list when no old manifest is available.
    if old_manifest_path is None or not old_manifest_path.exists():
        if not new_manifest_path.exists():
            print(
                f"warning: {new_manifest_path} not found — "
                "pack may pre-date MANIFEST support; skipping prune",
                file=sys.stderr,
            )
            return []
        print(
            "info: no old MANIFEST found — applying legacy removal list "
            "(packs 2026-04-29a through 2026-05-02d)",
            file=sys.stderr,
        )
        deleted = _prune_legacy(framework_dir, dry_run=dry_run)
        meta_cleanup_targets = {rel.rstrip("/") for rel in _LEGACY_REMOVALS}
    else:
        if not new_manifest_path.exists():
            print(
                f"warning: {new_manifest_path} not found — "
                "pack may pre-date MANIFEST support; skipping prune",
                file=sys.stderr,
            )
            return []

        old_entries = _read_manifest(old_manifest_path)
        new_entries = _read_manifest(new_manifest_path)
        removed = old_entries - new_entries
        meta_cleanup_targets = set(removed)

        deleted = []
        for rel in sorted(removed):
            target = framework_dir / rel
            if target.exists() and target.is_file():
                if dry_run:
                    print(f"[dry-run] would delete: {target}")
                else:
                    target.unlink()
                    print(f"deleted: {target}")
                deleted.append(str(target))

        # Remove directories that became empty (bottom-up).
        if not dry_run:
            dirs_to_check: set[Path] = set()
            for rel in removed:
                dirs_to_check.add((framework_dir / rel).parent)
            for d in sorted(dirs_to_check, key=lambda p: len(p.parts), reverse=True):
                try:
                    if d.is_dir() and not any(d.iterdir()):
                        d.rmdir()
                except OSError:
                    pass

    if _prune_meta_json(framework_dir, meta_cleanup_targets, dry_run=dry_run):
        print(f"updated: {framework_dir / 'index' / 'meta.json'}", file=sys.stderr)

    return deleted


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prune pack-removed files after a framework upgrade."
    )
    parser.add_argument(
        "--old-manifest",
        metavar="PATH",
        default=None,
        help=(
            "Path to the MANIFEST saved from the old pack (before unzip). "
            "When omitted or the file does not exist, the built-in legacy "
            "removal list is used instead."
        ),
    )
    parser.add_argument(
        "--framework-dir",
        metavar="DIR",
        default=".wavefoundry/framework",
        help="Path to the framework directory (default: .wavefoundry/framework).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be deleted without deleting anything.",
    )
    args = parser.parse_args()

    framework_dir = Path(args.framework_dir)
    old_manifest = Path(args.old_manifest) if args.old_manifest else None

    deleted = prune(framework_dir, old_manifest, dry_run=args.dry_run)
    if deleted:
        label = "would delete" if args.dry_run else "deleted"
        print(f"prune: {label} {len(deleted)} item(s)", file=sys.stderr)
    else:
        print("prune: nothing to remove", file=sys.stderr)


if __name__ == "__main__":
    main()
