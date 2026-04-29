#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS = {
    "pre-edit": REPO_ROOT / ".claude" / "hooks" / "pre-edit.py",
    "post-edit": REPO_ROOT / ".claude" / "hooks" / "post-edit.py",
    "pycache-cleanup": REPO_ROOT / ".claude" / "hooks" / "pycache-cleanup.py",
}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: simulate-hooks.py <entrypoint> <json-payload>", file=sys.stderr)
        return 2
    hook_name, payload = argv
    target = HOOKS.get(hook_name)
    if target is None:
        print(f"unknown hook entrypoint: {hook_name}", file=sys.stderr)
        return 2
    result = subprocess.run(
        [sys.executable, str(target)],
        cwd=REPO_ROOT,
        input=payload,
        text=True,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
