#!/usr/bin/env python3

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from wave_lint_lib.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
