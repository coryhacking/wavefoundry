"""Tag inference for Wavefoundry's controlled chunk-tag vocabulary.

Single source of truth for _infer_tags — imported by both chunker.py and
server.py. No heavy dependencies: stdlib re only.
"""
from __future__ import annotations

import re
import sys

sys.dont_write_bytecode = True

# Wave 1y0gz: the waves root comes from the stdlib-only resolver. Loaded the
# same two ways chunker.py loads THIS module (package import first, sibling
# path second) so the tag rule works in every host that can load _tag_utils.
try:
    import record_paths as _record_paths
except ImportError:  # scripts dir not on sys.path: load the sibling by path
    import importlib.util as _ilu
    from pathlib import Path as _Path

    _rp_path = _Path(__file__).resolve().with_name("record_paths.py")
    _rp_spec = _ilu.spec_from_file_location("record_paths", _rp_path)
    if _rp_spec is None or _rp_spec.loader is None:
        raise ImportError(f"cannot load record_paths from {_rp_path}")
    _record_paths = _ilu.module_from_spec(_rp_spec)
    _rp_spec.loader.exec_module(_record_paths)

_DEFAULT_WAVES_PREFIX = _record_paths.WAVES_ROOT + "/"

_TEST_RE = re.compile(
    r"(?:^|/)tests?/"
    r"|(?:^|/)test_[^/]+$"
    r"|_test\.[a-z]+$"
    r"|\.test\.[jt]sx?$"
    r"|\.spec\.[jt]sx?$",
    re.IGNORECASE,
)
_CONFIG_RE = re.compile(r"\.(ya?ml|toml|env)$", re.IGNORECASE)


def infer_tags(path: str, *, waves_prefix: str = _DEFAULT_WAVES_PREFIX) -> list[str]:
    """Return classification tags for a file path from the controlled vocabulary.

    Tags are inferred purely from path patterns — no content inspection needed.
    A file may receive zero or more tags. All chunks from the same file share
    the same tags.

    ``waves_prefix`` is the repo-relative waves root with a trailing slash
    (wave 1y0gz): callers that own a repository root pass
    ``record_paths.load_record_roots(root).waves_prefix``; the default is the
    resolver's default layout.

    Vocabulary:
      wave      — docs/waves/ subtree
      agent     — docs/prompts/agents/ or docs/agents/ subtree
      lifecycle — docs/ subtree containing lifecycle, install, or onboarding
      reference — docs/references/ subtree
      journal   — docs/agents/journals/ subtree
      prompt    — docs/prompts/ subtree or filename ending with .prompt.md
      seed      — .wavefoundry/framework/seeds/ subtree
      framework — .wavefoundry/framework/ subtree
      test      — test file conventions (test_*.py, *_test.go, *.spec.ts, /tests/, etc.)
      config    — .yaml, .yml, .toml, .env, .env.* files
    """
    p = path.replace("\\", "/")
    name = p.rsplit("/", 1)[-1]
    tags: list[str] = []

    # Doc-centric tags
    if waves_prefix in p:
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
