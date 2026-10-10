"""The single reader of the workflow-config project include-prefixes (change 2038p).

``docs/workflow-config.json`` ``indexing.project_include_prefixes`` names the
repo-relative prefixes that bypass the default project index excludes, per
layer (``{"docs": [...], "code": [...]}``) or as a top-level list that applies
to both. The indexer resolves eligibility from this reader on every launch, and
setup reports the same values in its "Workflow policy" line, so both read the
config through one coercion.

Bootstrap-safe, and nothing runs at import: setup imports this before its
dependencies are provisioned. Only the standard library and its contained_files
leaf are permitted; never pull in the indexer or tool environment.

Fail-safe coercion: only a list contributes prefixes; a string, dict or other
value yields none, and non-string items are skipped. Each token has whitespace
and leading or trailing ``/`` stripped and backslashes normalized to ``/``;
empty tokens are dropped and duplicates removed in order. A missing or
malformed file, or an ``indexing`` value that is not a dict, yields no prefixes
for either layer. The legacy ``include_framework_code_for_code_search`` boolean
maps to the framework scripts prefix only when the code list is empty.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from contained_files import DEFAULT_MAX_BYTES, read_contained_bytes

INDEXING_KEY = "indexing"
PROJECT_INCLUDE_PREFIXES_KEY = "project_include_prefixes"
LEGACY_INCLUDE_FRAMEWORK_CODE_KEY = "include_framework_code_for_code_search"
DOCS_KEY = "docs"
CODE_KEY = "code"
FRAMEWORK_SCRIPTS_PREFIX = ".wavefoundry/framework/scripts"


def normalize_prefixes(items: Iterable[object]) -> tuple[str, ...]:
    """Normalized, deduplicated prefix tokens from ``items``; non-strings are skipped."""
    out: list[str] = []
    for item in items:
        if not isinstance(item, str):
            continue
        token = item.strip().replace("\\", "/").strip("/")
        if token and token not in out:
            out.append(token)
    return tuple(out)


def coerce_prefix_list(raw: object) -> tuple[str, ...]:
    """Prefixes from one configured value: a list contributes, anything else yields none."""
    if not isinstance(raw, list):
        return ()
    return normalize_prefixes(raw)


def _empty() -> dict[str, tuple[str, ...]]:
    return {DOCS_KEY: (), CODE_KEY: ()}


def read_project_include_prefixes(root: Path) -> dict[str, tuple[str, ...]]:
    """The ``docs`` and ``code`` include-prefix tuples from ``root``'s workflow config. Never raises."""
    cfg = Path(root) / "docs" / "workflow-config.json"
    try:
        raw = read_contained_bytes(root, cfg, max_bytes=DEFAULT_MAX_BYTES)
        data = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError):
        return _empty()
    if not isinstance(data, dict):
        return _empty()
    indexing = data.get(INDEXING_KEY, {})
    if not isinstance(indexing, dict):
        return _empty()
    configured = indexing.get(PROJECT_INCLUDE_PREFIXES_KEY, {})
    docs_prefixes: tuple[str, ...] = ()
    code_prefixes: tuple[str, ...] = ()
    if isinstance(configured, list):
        docs_prefixes = code_prefixes = coerce_prefix_list(configured)
    elif isinstance(configured, dict):
        docs_prefixes = coerce_prefix_list(configured.get(DOCS_KEY))
        code_prefixes = coerce_prefix_list(configured.get(CODE_KEY))
    if not code_prefixes and bool(indexing.get(LEGACY_INCLUDE_FRAMEWORK_CODE_KEY, False)):
        code_prefixes = (FRAMEWORK_SCRIPTS_PREFIX,)
    return {DOCS_KEY: docs_prefixes, CODE_KEY: code_prefixes}
