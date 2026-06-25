#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import venv_bootstrap  # the single venv resolver (wave 1p7pl)

# Re-exec into the shared tool venv before any heavy import (wave 1p7pl). No-op when
# already in the venv or when it does not exist yet (fresh bootstrap).
venv_bootstrap.reexec_into_tool_venv()

from wave_lint_lib.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
