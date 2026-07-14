"""Tag inference for Wavefoundry's controlled chunk-tag vocabulary.

Single source of truth for _infer_tags — imported by both chunker.py and
server.py. No heavy dependencies: stdlib re only.
"""
from __future__ import annotations

import re
import sys

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


def infer_tags(path: str) -> list[str]:
    """Return classification tags for a file path from the controlled vocabulary.

    Tags are inferred purely from path patterns — no content inspection needed.
    A file may receive zero or more tags. All chunks from the same file share
    the same tags.

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
    if "docs/waves/" in p:
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
