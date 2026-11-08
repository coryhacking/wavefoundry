#!/usr/bin/env python3
"""Three known test children run with ``-B`` (wave 22u26, change 22qr7).

Each spawns ``sys.executable -c`` code that imports framework modules. Under a bare ``unittest``
run without ``PYTHONDONTWRITEBYTECODE`` such a child writes ``.pyc`` files beside the framework
sources. A census of every test spawn is the separate change ``22ubd-debt``.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent

# (test module, enclosing class, function holding the spawn)
SITES = (
    ("test_memory_records.py", "RealChildProcessCoherenceTests", "_child_dirty"),
    ("test_indexer.py", "EpochOrderingAndFaultTests",
     "test_fresh_process_kill_between_fence_and_finalize_fails_closed"),
    ("test_lifecycle_mutation_lock.py", "MutationLockTests", "test_contended_mutation_returns_structured_busy"),
)


def _is_sys_executable(node: ast.AST) -> bool:
    return (isinstance(node, ast.Attribute) and node.attr == "executable"
            and isinstance(node.value, ast.Name) and node.value.id == "sys")


def spawn_argv_heads(source: str, class_name: str, function_name: str) -> list[list[object]]:
    """The leading literal arguments of each ``[sys.executable, ...]`` list in that function."""
    tree = ast.parse(source)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == function_name)
    heads = []
    for node in ast.walk(fn):
        if isinstance(node, ast.List) and node.elts and _is_sys_executable(node.elts[0]):
            heads.append([e.value if isinstance(e, ast.Constant) else type(e).__name__ for e in node.elts[1:3]])
    return heads


def _guarded(head: list[object]) -> bool:
    return "-B" in head[:1]


class KnownChildSpawnGuardTests(unittest.TestCase):
    def test_each_known_child_runs_with_dash_b(self):
        for path, class_name, function_name in SITES:
            with self.subTest(site=f"{path}::{class_name}.{function_name}"):
                heads = spawn_argv_heads((TESTS / path).read_text(encoding="utf-8"), class_name, function_name)
                self.assertEqual(len(heads), 1, heads)
                self.assertTrue(_guarded(heads[0]), heads)

    def test_the_check_detects_an_unguarded_spawn(self):
        source = (
            "import subprocess, sys\n"
            "class Sample:\n"
            "    def spawn(self):\n"
            "        subprocess.run([sys.executable, '-c', 'import indexer'])\n"
            "    def guarded(self):\n"
            "        subprocess.run([sys.executable, '-B', '-c', 'import indexer'])\n"
        )
        self.assertFalse(_guarded(spawn_argv_heads(source, "Sample", "spawn")[0]))
        self.assertTrue(_guarded(spawn_argv_heads(source, "Sample", "guarded")[0]))


if __name__ == "__main__":
    unittest.main()
