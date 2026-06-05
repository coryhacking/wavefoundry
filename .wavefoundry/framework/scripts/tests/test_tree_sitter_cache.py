"""Tests for the shared tree-sitter parse cache (1p3ha foundation for 1p3hd)."""
from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

import sys
TESTS_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_ROOT.parent))

from tree_sitter_cache import TreeSitterCache, DEFAULT_MAXSIZE


class TreeSitterCacheTests(unittest.TestCase):
    """1p3ha cache primitive: LRU + mtime invalidation. Foundation for 1p3hd."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cache = TreeSitterCache(maxsize=4)
        # Use a counter to track parse-function invocations
        self.parse_call_count = 0

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _make_file(self, name: str, content: str = "x") -> Path:
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return path

    def _make_parse_fn(self, value: str):
        def parse():
            self.parse_call_count += 1
            return value
        return parse

    def test_first_lookup_is_miss(self) -> None:
        path = self._make_file("a.py")
        result, was_hit = self.cache.get_or_parse(path, "python", self._make_parse_fn("tree-a"))
        self.assertEqual(result, "tree-a")
        self.assertFalse(was_hit)
        self.assertEqual(self.parse_call_count, 1)
        self.assertEqual(self.cache.stats["misses"], 1)
        self.assertEqual(self.cache.stats["hits"], 0)

    def test_second_lookup_with_unchanged_mtime_is_hit(self) -> None:
        """AC-22 equivalent: cache hits on same (path, lang, mtime) — load-bearing
        for 1p3hd's cross-tool sharing."""
        path = self._make_file("a.py")
        self.cache.get_or_parse(path, "python", self._make_parse_fn("tree-a"))
        result, was_hit = self.cache.get_or_parse(path, "python", self._make_parse_fn("tree-b"))
        self.assertEqual(result, "tree-a",
            "hit must return the cached value, not call parse_fn again")
        self.assertTrue(was_hit)
        self.assertEqual(self.parse_call_count, 1, "parse_fn must be called exactly once")
        self.assertEqual(self.cache.stats["hits"], 1)
        self.assertEqual(self.cache.stats["misses"], 1)

    def test_mtime_change_invalidates_entry(self) -> None:
        """AC-23 equivalent: in-session edit invalidates the cache. Load-bearing
        correctness for in-session-edit workflows."""
        path = self._make_file("a.py", "v1")
        self.cache.get_or_parse(path, "python", self._make_parse_fn("tree-v1"))
        # Advance mtime by writing new content
        time.sleep(0.01)  # ensure mtime resolution catches the change
        path.write_text("v2", encoding="utf-8")
        result, was_hit = self.cache.get_or_parse(path, "python", self._make_parse_fn("tree-v2"))
        self.assertEqual(result, "tree-v2",
            "after mtime change, parse_fn must be called and new value cached")
        self.assertFalse(was_hit)
        self.assertEqual(self.parse_call_count, 2)
        self.assertEqual(self.cache.stats["invalidations"], 1)

    def test_different_lang_does_not_hit_same_file_entry(self) -> None:
        """Cache key includes lang — `.h` parsed as C should not satisfy a `.h`
        parsed as C++ (edge case in `_DECISION_LOG`)."""
        path = self._make_file("a.h", "code")
        self.cache.get_or_parse(path, "c", self._make_parse_fn("tree-as-c"))
        result, was_hit = self.cache.get_or_parse(path, "cpp", self._make_parse_fn("tree-as-cpp"))
        self.assertEqual(result, "tree-as-cpp")
        self.assertFalse(was_hit)
        self.assertEqual(self.parse_call_count, 2)

    def test_lru_eviction_when_size_exceeds_maxsize(self) -> None:
        """AC-24 equivalent: bounded LRU prevents unbounded memory growth."""
        # maxsize=4 set in setUp. Insert 5 entries.
        for i in range(5):
            path = self._make_file(f"f{i}.py")
            self.cache.get_or_parse(path, "python", self._make_parse_fn(f"tree-{i}"))
        self.assertEqual(self.cache.stats["size"], 4)
        self.assertEqual(self.cache.stats["evictions"], 1)
        # The first inserted (f0.py) should have been evicted
        first_path = self.root / "f0.py"
        self.assertIsNone(self.cache.peek(first_path, "python"))
        # The fifth inserted (f4.py) should still be there
        last_path = self.root / "f4.py"
        self.assertEqual(self.cache.peek(last_path, "python"), "tree-4")

    def test_lru_moves_recently_accessed_to_mru(self) -> None:
        """A hit on an older entry makes it survive subsequent evictions."""
        paths = [self._make_file(f"f{i}.py") for i in range(4)]
        for p in paths:
            self.cache.get_or_parse(p, "python", self._make_parse_fn(f"tree-{p.name}"))
        # Access f0 — promotes it to MRU
        self.cache.get_or_parse(paths[0], "python", self._make_parse_fn("nope"))
        # Insert one more — f1 (now LRU) should be evicted, not f0
        new_path = self._make_file("f-new.py")
        self.cache.get_or_parse(new_path, "python", self._make_parse_fn("tree-new"))
        self.assertIsNotNone(self.cache.peek(paths[0], "python"))  # survived
        self.assertIsNone(self.cache.peek(paths[1], "python"))  # evicted

    def test_missing_file_does_not_cache(self) -> None:
        """Defensive: stat failure → parse_fn called, result not cached."""
        path = self.root / "nonexistent.py"
        result, was_hit = self.cache.get_or_parse(path, "python", self._make_parse_fn("tree-x"))
        self.assertEqual(result, "tree-x")
        self.assertFalse(was_hit)
        self.assertIsNone(self.cache.peek(path, "python"))

    def test_clear_drops_all_entries_and_resets_stats(self) -> None:
        for i in range(3):
            path = self._make_file(f"f{i}.py")
            self.cache.get_or_parse(path, "python", self._make_parse_fn(f"tree-{i}"))
        self.assertEqual(self.cache.stats["size"], 3)
        self.cache.clear()
        self.assertEqual(self.cache.stats["size"], 0)
        self.assertEqual(self.cache.stats["hits"], 0)
        self.assertEqual(self.cache.stats["misses"], 0)

    def test_default_maxsize_matches_constant(self) -> None:
        cache = TreeSitterCache()
        self.assertEqual(cache.stats["maxsize"], DEFAULT_MAXSIZE)


if __name__ == "__main__":
    unittest.main()
