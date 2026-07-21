"""Canonical public-contract vocabularies (wave 1seax / 1seau).

One source of truth for the public MCP vocabularies that were previously
duplicated as scattered string literals (the "two truths" defect: the indexer
CLI accepted ``docs/code/all/graph`` while the public ``index_build`` handler
also accepted ``map`` and ``fts``). Both the handlers and the docs-constants
lint check consume THIS module — never regex-parse scattered literals.

The relationship between the two content tuples is intentional, not drift:
``map`` and ``fts`` are server-native refreshes (no indexer subprocess), so
the indexer CLI legitimately accepts only its subprocess-capable subset.
"""
from __future__ import annotations

# The public MCP `index_build` content vocabulary (the full surface).
INDEX_BUILD_CONTENT_VALUES: tuple[str, ...] = (
    "docs", "code", "all", "graph", "map", "fts",
)

# The indexer CLI's subprocess-capable subset (`indexer.CONTENT_CHOICES`).
INDEXER_CLI_CONTENT_CHOICES: tuple[str, ...] = ("docs", "code", "all", "graph")

# Envelope `index_freshness` verdict states (code_ask and siblings).
INDEX_FRESHNESS_STATES: tuple[str, ...] = ("current", "stale", "unknown")

# `search_mode` / `fallback_reason` vocabularies on the search envelopes.
# (The initial draft under-enumerated this tuple from a partial grep — the
# operator review that forced handlers onto this module also forced the full
# producing-site census: hybrid is code_lexical's merged mode, live_fallback
# is the docs-search live-read path.)
SEARCH_MODES: tuple[str, ...] = (
    "semantic", "exact", "hybrid", "lexical_fallback", "live_fallback",
)
LEXICAL_FALLBACK_REASONS: tuple[str, ...] = (
    "index_not_ready", "store_absent", "query_failed",
    "model_unavailable", "index_missing",
)
