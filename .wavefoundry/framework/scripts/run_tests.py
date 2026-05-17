#!/usr/bin/env python3
"""Run Wavefoundry framework unit tests without writing __pycache__ under scripts/."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

_SCRIPT_DIR = Path(__file__).resolve().parent
_TESTS_DIR = _SCRIPT_DIR / "tests"

# Ensure scripts/ is on sys.path explicitly — tests/  __init__.py handles this
# for individual-file runs; repeat it here so run_tests.py is self-contained
# and does not rely on Python's implicit entry-point path insertion.
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))


def main() -> int:
    argv = [
        sys.argv[0],
        "discover",
        "-s",
        str(_TESTS_DIR),
        "-p",
        "test_*.py",
        "-v",
        *sys.argv[1:],
    ]
    program = unittest.main(module=None, argv=argv, exit=False)
    assert program.result is not None
    return 0 if program.result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
