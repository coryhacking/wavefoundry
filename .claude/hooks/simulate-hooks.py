#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS = {
    "pre-edit": REPO_ROOT / ".claude" / "hooks" / "pre-edit.py",
    "post-edit": REPO_ROOT / ".claude" / "hooks" / "post-edit.py",
    "session-capture": REPO_ROOT / ".claude" / "hooks" / "session-capture.py",
}


def _venv_python_path() -> str:
    venv_base = os.environ.get("WAVEFOUNDRY_TOOL_VENV", str(Path.home() / ".wavefoundry" / "venv"))
    if os.name == "nt":
        return str(Path(venv_base) / "Scripts" / "python.exe")
    return str(Path(venv_base) / "bin" / "python")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: simulate-hooks.py <entrypoint> <json-payload>", file=sys.stderr)
        return 2
    hook_name, payload = argv
    target = HOOKS.get(hook_name)
    if target is None:
        print(f"unknown hook entrypoint: {hook_name}", file=sys.stderr)
        return 2
    python_exec = _venv_python_path()
    if not Path(python_exec).exists():
        python_exec = sys.executable
    result = subprocess.run(
        [python_exec, str(target)],
        cwd=REPO_ROOT,
        input=payload,
        text=True,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
