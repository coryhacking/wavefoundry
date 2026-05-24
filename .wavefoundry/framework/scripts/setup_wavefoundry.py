#!/usr/bin/env python3
"""Preferred Wavefoundry bootstrap entrypoint.

Delegates to ``setup_index.py`` so operators have a clearer command name for the
shared venv bootstrap + index setup flow without breaking existing call sites.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_setup_index():
    script_path = Path(__file__).with_name("setup_index.py")
    spec = importlib.util.spec_from_file_location("wavefoundry_setup_index", script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load setup_index.py from {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    setup_index = _load_setup_index()
    return int(setup_index.main(argv))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
