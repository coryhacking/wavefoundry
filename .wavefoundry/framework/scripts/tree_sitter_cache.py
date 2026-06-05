"""Shared tree-sitter parse cache with LRU eviction and mtime-based invalidation.

Built for wave 1p3dk:
- `1p3ha` consumes this for ``code_read``'s structural enrichment block.
- `1p3hd` (follow-on, depends on `1p3ha`) consumes this from ``code_outline``,
  ``code_definition``, ``code_references``, ``code_callhierarchy``, and
  ``code_hover``.

Design:
- Cache key: ``(absolute_path_str, lang)``. ``lang`` is included because the
  same file extension could be parsed by different language grammars
  (.h as C vs C++, .sql dialects).
- Cached value: ``(mtime, parse_result)``. ``parse_result`` is whatever the
  caller's parse function returned (Tree-sitter Tree, AST, symbol index, etc.).
- Invalidation: on lookup, current file mtime is compared against the cached
  mtime. Mismatch evicts the entry. This handles in-session edits: the next
  ``get_or_parse`` after an edit sees the new mtime and reparses.
- Eviction: bounded LRU. When the cache exceeds ``maxsize``, the least-recently
  used entry is evicted. Default maxsize is 32.
- Scope: process-local (no shared state across MCP server processes). Matches
  ``lifecycle_id._last_assigned_prefix`` and other module-level caches.

Thread-safety note: the cache uses a plain ``OrderedDict`` and is not thread-safe.
The current MCP server model is serial per-process, so this is acceptable. If
concurrent access becomes a requirement, wrap operations in a ``threading.Lock``.
"""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, Optional

__all__ = [
    "TreeSitterCache",
    "default_cache",
    "DEFAULT_MAXSIZE",
]

DEFAULT_MAXSIZE = 32


class TreeSitterCache:
    """LRU cache of parse results keyed by ``(absolute_path, lang)``.

    The cache stores arbitrary parse results — Tree-sitter Tree objects,
    derived symbol indexes, or both — depending on what the caller needs.
    Invalidation is mtime-based and happens automatically on every lookup.

    Usage:
        cache = TreeSitterCache(maxsize=32)
        result = cache.get_or_parse(path, lang, parse_fn)

    ``parse_fn`` is a zero-arg callable that performs the actual parse when
    the cache misses or is stale. The cache calls it once and stores the result.

    Stats are tracked for observability (hit/miss counts, eviction count).
    """

    def __init__(self, maxsize: int = DEFAULT_MAXSIZE) -> None:
        self._store: OrderedDict[tuple[str, str], tuple[float, Any]] = OrderedDict()
        self._maxsize = maxsize
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._invalidations = 0

    @property
    def stats(self) -> dict[str, int]:
        """Return current cache statistics. Useful for tests and observability."""
        return {
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "invalidations": self._invalidations,
            "size": len(self._store),
            "maxsize": self._maxsize,
        }

    def reset_stats(self) -> None:
        """Reset hit/miss/eviction counters without clearing the cache."""
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._invalidations = 0

    def clear(self) -> None:
        """Drop all cached entries and reset stats. Useful for tests."""
        self._store.clear()
        self.reset_stats()

    def get_or_parse(
        self,
        path: Path,
        lang: str,
        parse_fn: Callable[[], Any],
    ) -> tuple[Any, bool]:
        """Return the cached parse result for ``(path, lang)`` or call ``parse_fn``.

        Returns a tuple ``(result, was_cache_hit)``.

        - Cache hit: ``path``'s mtime matches the cached mtime → return the
          cached result without calling ``parse_fn``. The entry is moved to
          the most-recently-used position.
        - Cache miss / stale: either no entry exists for ``(path, lang)`` or
          the cached mtime is stale → call ``parse_fn()``, store the result
          with the current mtime, evict the LRU entry if over capacity, and
          return the new result.
        - Stat failure (file doesn't exist or unreadable): ``parse_fn`` is
          still called; the result is NOT cached because we can't establish
          a baseline mtime to invalidate against.
        """
        try:
            current_mtime = path.stat().st_mtime
        except OSError:
            # File doesn't exist or can't be stat'd. Don't cache.
            self._misses += 1
            return parse_fn(), False

        key = (str(path), lang)
        cached = self._store.get(key)
        if cached is not None:
            cached_mtime, cached_value = cached
            if cached_mtime == current_mtime:
                # Hit. Move to MRU position.
                self._store.move_to_end(key)
                self._hits += 1
                return cached_value, True
            # Stale. Drop and reparse below.
            del self._store[key]
            self._invalidations += 1

        self._misses += 1
        result = parse_fn()
        self._store[key] = (current_mtime, result)
        # Bounded LRU eviction
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)
            self._evictions += 1
        return result, False

    def peek(self, path: Path, lang: str) -> Optional[Any]:
        """Return the cached result without mtime check or LRU update.

        Used primarily by tests. Returns ``None`` when the key is absent.
        Does not invalidate stale entries.
        """
        entry = self._store.get((str(path), lang))
        return entry[1] if entry is not None else None


# Module-level default cache. Tools share this single instance.
default_cache = TreeSitterCache(maxsize=DEFAULT_MAXSIZE)
