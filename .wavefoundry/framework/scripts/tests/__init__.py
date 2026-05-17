"""Test package bootstrap — adds the scripts/ directory to sys.path.

Enables individual test files and groups to be run directly without going
through run_tests.py:

    # From the scripts/ directory:
    python3 -m unittest tests.test_server_tools
    python3 -m unittest tests.test_chunker
    python3 -m unittest discover -s tests -p "test_server_tools.py"

    # Run a single test class or method:
    python3 -m unittest tests.test_server_tools.RerankerTests
    python3 -m unittest tests.test_server_tools.RerankerTests.test_search_combined_returns_reranked_true_when_reranker_available

unittest imports this file before any test module when the tests/ directory
is treated as a package, making scripts/ available for all subsequent imports.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
