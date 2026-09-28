"""Tag inference for Wavefoundry's controlled chunk-tag vocabulary.

Single source of truth for chunk tags: the indexer writes them at index time
(``indexer._chunks_for_file``) and the server's live docs path does the same.
No heavy dependencies: stdlib re only.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

_TEST_RE = re.compile(
    r"(?:^|/)tests?/"
    r"|(?:^|/)test_[^/]+$"
    r"|_test\.[a-z]+$"
    r"|\.test\.[jt]sx?$"
    r"|\.spec\.[jt]sx?$",
    re.IGNORECASE,
)
_CONFIG_RE = re.compile(r"\.(ya?ml|toml|env)$", re.IGNORECASE)


def default_waves_prefix() -> str:
    """The waves prefix of the layout current at CALL time (wave 1z8ty).

    The import is function-level on purpose: importing ``server_impl`` evicts
    ``record_paths`` from ``sys.modules``, so a module reference bound when this
    module was imported can be a copy a patched layout never reaches. The
    normalization matches ``server_impl._record_prefixes``."""
    import record_paths

    prefix = record_paths.unvalidated_record_roots(Path(".")).waves_prefix
    # An empty WAVES_ROOT yields "/", which names no root (wave 1z8ty N4).
    return prefix if _is_root_prefix(prefix) else ""


def _is_root_prefix(prefix: str | None) -> bool:
    """True for a usable record-root prefix: not None, empty or only slashes."""
    return bool(prefix) and bool(prefix.strip("/"))


def infer_tags(
    path: str, *, waves_prefix: str | None = None, archive_prefix: str | None = None
) -> list[str]:
    """Return classification tags for a file path from the controlled vocabulary.

    Tags are inferred purely from path patterns — no content inspection needed.
    A file may receive zero or more tags. All chunks from the same file share
    the same tags.

    ``waves_prefix`` is the repo-relative waves root with a trailing slash
    (wave 1y0gz): callers that own a repository root pass
    ``record_paths.load_record_roots(root).waves_prefix``. Omitted, it is the
    layout current at call time (:func:`default_waves_prefix`), never a value
    captured at import (wave 1z8ty). ``archive_prefix`` is the read-only
    archive root with a trailing slash when one is configured (wave 1z8ts);
    archived records are wave records too, so they also get ``wave``.

    Vocabulary:
      wave      — the waves root subtree (docs/waves/ by default) or the archive root
      agent     — docs/prompts/agents/ or docs/agents/ subtree
      lifecycle — docs/ subtree containing lifecycle, install, or onboarding
      reference — docs/references/ subtree
      journal   — docs/agents/journals/ subtree
      prompt    — docs/prompts/ subtree or filename ending with .prompt.md
      seed      — .wavefoundry/framework/seeds/ subtree
      framework — .wavefoundry/framework/ subtree
      test      — test file conventions (test_*.py, *_test.go, *.spec.ts, /tests/, etc.)
      memory    — docs/agents/memory/ subtree
      config    — .yaml, .yml, .toml, .env, .env.* files
    """
    if waves_prefix is None:
        waves_prefix = default_waves_prefix()
    p = path.replace("\\", "/")
    name = p.rsplit("/", 1)[-1]
    tags: list[str] = []

    # Doc-centric tags
    # Paths are repo-relative, so a record root matches only as a leading
    # prefix (a substring match would tag ``src/archive/x.py`` for an
    # ``archive`` root). An empty or bare-slash prefix, which an empty root
    # constant yields, names no root and tags nothing.
    if any(_is_root_prefix(prefix) and p.startswith(prefix) for prefix in (waves_prefix, archive_prefix)):
        tags.append("wave")
    if "docs/prompts/agents/" in p or "docs/agents/" in p:
        tags.append("agent")
    if p.startswith("docs/") or "/docs/" in p:
        pl = p.lower()
        if "lifecycle" in pl or "install" in pl or "onboarding" in pl:
            tags.append("lifecycle")
    if "docs/references/" in p:
        tags.append("reference")
    if "docs/agents/journals/" in p:
        tags.append("journal")
    if "docs/agents/memory/" in p:
        tags.append("memory")
    if "docs/prompts/" in p or name.endswith(".prompt.md"):
        tags.append("prompt")
    if ".wavefoundry/framework/seeds/" in p:
        tags.append("seed")
    if ".wavefoundry/framework/" in p:
        tags.append("framework")

    # Code-centric tags
    if _TEST_RE.search(p):
        tags.append("test")
    elif _CONFIG_RE.search(name):
        tags.append("config")
    elif name.startswith(".env"):
        tags.append("config")

    return tags
