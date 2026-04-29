#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GATES = (
    REPO_ROOT / ".cursor" / "hooks" / "seed-warn.py",
    REPO_ROOT / ".cursor" / "hooks" / "framework-plan-warn.py",
    REPO_ROOT / ".cursor" / "hooks" / "docs-lint.py",
)


def main() -> int:
    payload = sys.stdin.read()
    for gate in GATES:
        result = subprocess.run(
            [sys.executable, str(gate)],
            cwd=REPO_ROOT,
            input=payload,
            text=True,
            capture_output=True,
            check=False,
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode == 10:
            print(json.dumps({"continue": False, "message": output or "Cursor hook blocked the edit."}))
            return 0
        if result.returncode != 0:
            print(json.dumps({"continue": False, "message": output or "Cursor hook failed."}))
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
