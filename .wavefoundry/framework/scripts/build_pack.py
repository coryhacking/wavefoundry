#!/usr/bin/env python3
"""Build a dated distribution zip of Wavefoundry's canonical framework tree.

Produces wavefoundry-YYYY-MM-DDx.zip at the repository root (or a
specified output directory), where x is the next lowercase letter suffix after
the highest one already present for that date (``a``, then ``b``, …; if only
``…b.zip`` exists, the next is ``c``). If ``z`` is already used, the script exits
non-zero.

Unless ``--date`` is passed, the date in the filename is **today** (local
machine calendar date in ISO form). The suffix letter is the **successor of the highest letter already present** for
that date (scan ``wavefoundry-<date><letter>.zip`` in the output
directory). If only ``…b.zip`` exists, the next build is ``…c.zip``, not
``…a.zip``. If none exist, the first build uses ``a``.

Before building the archive, writes ``framework/VERSION``
to a single line ``<YYYY-MM-DD><letter>`` so the packed tree matches the zip
name (same string as in the filename after the ``wavefoundry-``
prefix and before ``.zip``).

Usage:
    python3 build_pack.py [--output <dir>] [--date <YYYY-MM-DD>]
"""

import argparse
import importlib.util
import os
import sys
import zipfile
from datetime import date
from pathlib import Path
from typing import Optional


# Patterns excluded from the zip.
EXCLUDED_NAMES = {".DS_Store"}
EXCLUDED_DIRS = {"__pycache__", ".pytest_cache"}
# Excluded path suffix relative to the framework root (forward-slash separated).
# Tests and the test runner are development-only artifacts; downstream repos that
# vendor the pack have no use for them and seeds must not instruct them to run tests.
EXCLUDED_REL_PATHS = {"scripts/tests/tmp", "scripts/tests", "scripts/run_tests.py"}

FRAMEWORK_REL = "framework"
ZIP_PREFIX = "wavefoundry-"
SUFFIX_LETTERS = "abcdefghijklmnopqrstuvwxyz"


def find_repo_root(start: Path) -> Path:
    """Walk up from start until we find the repo root (contains AGENTS.md)."""
    current = start.resolve()
    while current != current.parent:
        if (current / "AGENTS.md").exists():
            return current
        current = current.parent
    raise RuntimeError(f"Could not locate repository root from {start}")


def next_suffix(output_dir: Path, date_str: str) -> str:
    """Return the next letter after the max suffix already used for this date.

    Fills ``a`` only when no matching pack zips exist yet. If ``…a.zip`` and
    ``…c.zip`` exist, returns ``d`` (does not backfill ``b``).
    """
    used: list[str] = []
    pattern = f"{ZIP_PREFIX}{date_str}"
    for entry in output_dir.iterdir():
        name = entry.name
        # Only count files that match the full dated-letter pattern.
        if (
            name.startswith(pattern)
            and name.endswith(".zip")
            and len(name) == len(pattern) + 1 + len(".zip")
        ):
            letter = name[len(pattern)]
            if letter in SUFFIX_LETTERS:
                used.append(letter)
    if not used:
        return "a"
    max_letter = max(used)
    idx = SUFFIX_LETTERS.index(max_letter)
    if idx + 1 >= len(SUFFIX_LETTERS):
        raise RuntimeError(
            f"No unused suffix a–z available for date {date_str} in {output_dir}"
        )
    return SUFFIX_LETTERS[idx + 1]


def should_exclude(rel_path: str, name: str) -> bool:
    """Return True if this file or directory should be excluded from the zip."""
    if name in EXCLUDED_NAMES:
        return True
    # rel_path uses forward slashes relative to the framework root.
    for excl in EXCLUDED_DIRS:
        parts = rel_path.split("/")
        if excl in parts:
            return True
    for excl_rel in EXCLUDED_REL_PATHS:
        if rel_path == excl_rel or rel_path.startswith(excl_rel + "/"):
            return True
    if name.endswith(".pyc"):
        return True
    return False


def collect_files(framework_dir: Path):
    """Yield (abs_path, zip_arcname) for every file under framework_dir."""
    for dirpath, dirnames, filenames in os.walk(framework_dir):
        dirpath = Path(dirpath)
        # Compute path relative to framework_dir using forward slashes.
        rel_dir = dirpath.relative_to(framework_dir).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir

        # Filter out excluded dirs in-place so os.walk skips them.
        dirnames[:] = [
            d for d in dirnames
            if not should_exclude(
                (rel_dir + "/" + d).lstrip("/"), d
            )
        ]

        for filename in filenames:
            rel_file = (rel_dir + "/" + filename).lstrip("/")
            if should_exclude(rel_file, filename):
                continue
            abs_path = dirpath / filename
            # arcname preserves the full path from repo root so that
            # `unzip -o zip -d <repo-root>` restores the correct layout.
            arcname = FRAMEWORK_REL + ("/" + rel_file if rel_file else "")
            yield abs_path, arcname


def write_pack_version(framework_dir: Path, date_str: str, suffix: str) -> None:
    """Stamp VERSION so the archive matches the distribution filename."""
    version_path = framework_dir / "VERSION"
    version_path.write_text(f"{date_str}{suffix}\n", encoding="utf-8")


def _load_indexer():
    script_dir = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("indexer", script_dir / "indexer.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["indexer"] = mod
    spec.loader.exec_module(mod)
    return mod


def build_framework_index(framework_dir: Path, *, verbose: bool = False) -> None:
    """Build the packaged framework docs/seed index under framework/index/."""
    indexer = _load_indexer()
    framework_dir = framework_dir.resolve()
    root = framework_dir
    include_prefixes: tuple[str, ...] = ()
    if framework_dir.parent.name == ".wavefoundry":
        root = framework_dir.parent.parent
        include_prefixes = (framework_dir.relative_to(root).as_posix(),)
    indexer.build_index(
        root,
        full=True,
        content="docs",
        index_dir=framework_dir / "index",
        include_prefixes=include_prefixes,
        respect_ignore=False,
        verbose=verbose,
    )


def build_zip(
    output_dir: Path,
    date_str: str,
    *,
    framework_dir: Optional[Path] = None,
    write_version: bool = True,
    prebuild_index: bool = False,
    verbose: bool = False,
) -> Path:
    suffix = next_suffix(output_dir, date_str)
    zip_name = f"{ZIP_PREFIX}{date_str}{suffix}.zip"
    zip_path = output_dir / zip_name

    script_dir = Path(__file__).resolve().parent
    fw = framework_dir if framework_dir is not None else script_dir.parent

    if write_version:
        write_pack_version(fw, date_str, suffix)

    if prebuild_index:
        build_framework_index(fw, verbose=verbose)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for abs_path, arcname in collect_files(fw):
            zf.write(abs_path, arcname)

    return zip_path


def main():
    parser = argparse.ArgumentParser(
        description="Build a dated distribution zip of Wavefoundry's framework tree."
    )
    parser.add_argument(
        "--output",
        metavar="DIR",
        help="Directory to write the zip into (default: repository root).",
    )
    parser.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        help=(
            "Override the date used in the filename, VERSION stamp, and suffix "
            "scan (default: today's local date)."
        ),
    )
    parser.add_argument(
        "--skip-framework-index",
        action="store_true",
        help="Skip rebuilding framework/index before packaging.",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Print index build progress")
    args = parser.parse_args()

    # Packaging date is always "today" unless explicitly overridden for tests or
    # re-issues (--date). Suffix letter still auto-increments per date in output_dir.
    date_str = args.date if args.date else date.today().isoformat()

    if args.output:
        output_dir = Path(args.output)
        if not output_dir.exists():
            print(
                f"error: output directory does not exist: {output_dir}",
                file=sys.stderr,
            )
            sys.exit(1)
        if not output_dir.is_dir():
            print(
                f"error: output path is not a directory: {output_dir}",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        script_dir = Path(__file__).resolve().parent
        try:
            output_dir = find_repo_root(script_dir)
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            sys.exit(1)

    try:
        zip_path = build_zip(
            output_dir,
            date_str,
            prebuild_index=not args.skip_framework_index,
            verbose=args.verbose,
        )
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    version_path = Path(__file__).resolve().parent.parent / "VERSION"
    stamp = version_path.read_text(encoding="utf-8").strip()
    print(zip_path)
    print(f"Stamped VERSION: {stamp}", file=sys.stderr)


if __name__ == "__main__":
    main()
