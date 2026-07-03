#!/usr/bin/env python3
from __future__ import annotations

import sys as _wf_sys
from pathlib import Path as _WfPath

_WF_SCRIPTS = _WfPath(__file__).resolve().parents[2] / ".wavefoundry" / "framework" / "scripts"
if _WF_SCRIPTS.is_dir() and str(_WF_SCRIPTS) not in _wf_sys.path:
    _wf_sys.path.insert(0, str(_WF_SCRIPTS))
try:
    import venv_bootstrap as _wf_venv_bootstrap

    _wf_venv_bootstrap.activate_tool_venv()
except Exception:
    pass
try:
    import cli_stdio as _wf_cli_stdio

    _wf_cli_stdio.configure_utf8_stdio()
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
    # sys.executable is the SYSTEM interpreter (after in-process activation, wave 1p802); the
    # spawned hook target self-activates the venv first-line, so it reaches the venv packages.
    # An absolute path; never re-resolve a token. Wave 1p8pe: prefer the console-free pythonw.exe
    # on Windows (this dry-run spawn is input=/redirected) so it never flashes a window; this body
    # defines no hook helpers, so resolve windowless inline with a sys.executable fallback.
    python_exec = sys.executable
    try:
        import subprocess_util as _wf_subprocess_util
        _wf_pythonw = _wf_subprocess_util.windowless_pythonw()
        if _wf_pythonw is not None:
            python_exec = _wf_pythonw
    except Exception:
        pass
    result = subprocess.run(  # wave 1p8gu: inline no-window flag so the isolation guard sees it
        [python_exec, str(target)],
        cwd=REPO_ROOT,
        input=payload,
        text=True,
        encoding="utf-8",  # wave 1p9iv: pin UTF-8 so input=payload never encodes with a cp1252 locale codepage
        errors="replace",
        check=False,
        creationflags=(getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0),
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
