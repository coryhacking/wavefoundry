"""Explicit upstream text ownership for the actor census (change 204ml).

Maintainer-only update/check from the upstream tracked source tree:
  python3 -B .wavefoundry/framework/scripts/tests/framework_text_ownership.py --update
  python3 -B .wavefoundry/framework/scripts/tests/framework_text_ownership.py --check
Stage new owned files first, or name them explicitly with --include. Ordinary
framework tests read the shipped inventory and never discover checkout files.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

FRAMEWORK = Path(__file__).resolve().parents[2]
INVENTORY = FRAMEWORK / "scripts/tests/fixtures/framework-text-ownership.json"
SUFFIXES = frozenset({".py", ".md", ".json", ".toml", ".txt", ".yaml", ".yml", ".js", ".html", ".css", ".sh", ".ps1", ".cmd"})


def load_inventory(path: Path = INVENTORY) -> tuple[str, ...]:
    paths = json.loads(path.read_text(encoding="utf-8"))["paths"]
    if not isinstance(paths, list) or any(not isinstance(rel, str) or not rel
            or Path(rel).is_absolute() or ".." in Path(rel).parts for rel in paths):
        raise ValueError("invalid framework text ownership paths")
    if paths != sorted(set(paths)):
        raise ValueError("framework text ownership paths must be sorted and unique")
    return tuple(paths)


def upstream_inventory(framework: Path, includes=()) -> tuple[str, ...]:
    raw = subprocess.check_output(["git", "-C", str(framework), "ls-files", "-z", "--", "."])
    paths = set(raw.decode("utf-8").split("\0")) - {""}
    paths.update(includes)
    return tuple(sorted(rel for rel in paths if Path(rel).suffix in SUFFIXES
                        and "__pycache__" not in Path(rel).parts
                        and Path(rel).name != "test-cache.json"
                        and Path(rel).parts[0] not in {"index", "cache"}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include", action="append", default=[])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--update", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    paths = upstream_inventory(FRAMEWORK, args.include)
    if args.update:
        INVENTORY.write_text(json.dumps({"schema_version": 1, "paths": paths}, indent=2) + "\n", encoding="utf-8")
        load_inventory()
        print(f"Recorded {len(paths)} upstream-owned text files")
    elif paths != load_inventory():
        parser.error("ownership inventory differs from upstream tracked text files; run --update")
    else:
        print(f"Verified {len(paths)} upstream-owned text files")


if __name__ == "__main__":
    main()
