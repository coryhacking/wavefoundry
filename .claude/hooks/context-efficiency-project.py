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


def main() -> int:
    try:
        try:
            sys.stdin.read()
        except Exception:
            pass
        # The owner-bound Claude launcher resolves this committed hook
        # through CLAUDE_PROJECT_DIR.  Derive the same owner from the
        # hook file itself so a host cwd outside the repository cannot
        # turn a successfully launched Stop hook into a silent no-op.
        root = Path(__file__).resolve().parents[2]
        if not (root / ".wavefoundry").is_dir():
            return 0
        script = (
            root / ".wavefoundry" / "framework" / "scripts"
            / "project_context_efficiency.py"
        )
        if not script.is_file():
            return 0
        python = sys.executable
        detached = {}
        if os.name == "nt":
            candidate = Path(sys.executable).with_name("pythonw.exe")
            if candidate.exists():
                python = str(candidate)
            detached["creationflags"] = (
                subprocess.DETACHED_PROCESS
                | subprocess.CREATE_NEW_PROCESS_GROUP
                | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
        else:
            detached["start_new_session"] = True
        subprocess.Popen(
            [python, str(script), "--root", str(root)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(root),
            close_fds=os.name != "nt",
            **detached,
        )
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
