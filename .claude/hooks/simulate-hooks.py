#!/usr/bin/env python3
from __future__ import annotations

import sys as _wf_sys
from pathlib import Path as _WfPath

_WF_SCRIPTS = _WfPath(__file__).resolve().parents[2] / ".wavefoundry" / "framework" / "scripts"
if _WF_SCRIPTS.is_dir() and str(_WF_SCRIPTS) not in _wf_sys.path:
    _wf_sys.path.insert(0, str(_WF_SCRIPTS))
try:
    import venv_bootstrap as _wf_venv_bootstrap

    _wf_venv_bootstrap.reexec_into_tool_venv()
except Exception:
    pass

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


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: simulate-hooks.py <entrypoint> <json-payload>", file=sys.stderr)
        return 2
    hook_name, payload = argv
    target = HOOKS.get(hook_name)
    if target is None:
        print(f"unknown hook entrypoint: {hook_name}", file=sys.stderr)
        return 2
    # The body re-exec'd into the tool venv (first-line bootstrap) → sys.executable IS the
    # venv Python (an absolute path); never re-resolve a token.
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
