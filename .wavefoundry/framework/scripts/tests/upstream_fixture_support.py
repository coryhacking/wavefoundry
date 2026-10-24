"""Upstream-only fixtures: skip in distributions, fail in the source repository (change 21ile).

Some tests read content that only the framework source repository hosts:
evaluation corpora under ``docs/evals/``, history under ``docs/waves/`` and
``docs/agents/history/``, and report artifacts under ``docs/reports/``. A
distribution that ships the framework without that content runs the same suite.

``upstream_fixture(path)`` takes the fixture path the test already
computes and returns it when it exists. When it is absent the outcome comes from
the source-repository opt-in ``testing.upstream_fixtures_required`` in
``docs/workflow-config.json`` under the repository root derived from this file:

- the key is ``true``: the test fails, naming the path;
- the key is absent or ``false``: the test skips with
  ``upstream-only fixture absent: <path>``;
- the config is missing, unreadable or malformed, ``testing`` is not an object,
  or the key is not a boolean: the test fails, naming the path and the cause.

A missing config fails closed, the deliberate opposite of docs-lint's
``_framework_internal_constants_enabled`` (which treats a missing config as off),
because every distribution ships the config and a silent skip here would hide a
deleted fixture.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
CONFIG_REL = "docs/workflow-config.json"
SECTION = "testing"
KEY = "upstream_fixtures_required"
SKIP_PREFIX = "upstream-only fixture absent: "


def _exists(path: Path) -> bool:
    """The existence probe, a seam so a test can make one fixture absent."""
    return path.exists()


def fixtures_required(root: "Path | None" = None) -> "tuple[bool | None, str]":
    """Return ``(required, cause)``; ``required`` is None when the config fails closed."""
    config = (REPO_ROOT if root is None else Path(root)) / CONFIG_REL
    try:
        raw = config.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, f"{CONFIG_REL} is missing"
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"{CONFIG_REL} is unreadable ({exc})"
    try:
        data = json.loads(raw)
    except ValueError as exc:
        return None, f"{CONFIG_REL} is not valid JSON ({exc})"
    if not isinstance(data, dict):
        return None, f"{CONFIG_REL} must be a JSON object"
    if SECTION not in data:
        return False, ""
    section = data[SECTION]
    if not isinstance(section, dict):
        return None, f"{CONFIG_REL}: {SECTION} must be an object"
    value = section.get(KEY, False)
    if not isinstance(value, bool):
        return None, f"{CONFIG_REL}: {SECTION}.{KEY} must be a boolean"
    return value, ""


def upstream_fixture(path: "Path | str", *, root: "Path | None" = None) -> Path:
    """Return ``path`` when present; otherwise fail or skip per the opt-in.

    It raises ``AssertionError`` or ``unittest.SkipTest`` itself, so it works in
    a test method, ``setUp`` and ``setUpClass`` alike.
    """
    fixture = Path(path)
    if _exists(fixture):
        return fixture
    required, cause = fixtures_required(root)
    if required is None:
        raise AssertionError(f"upstream-only fixture absent: {fixture} and {cause}")
    if required:
        raise AssertionError(f"upstream-only fixture absent: {fixture} "
                             f"({SECTION}.{KEY} is true in {CONFIG_REL})")
    raise unittest.SkipTest(f"{SKIP_PREFIX}{fixture}")
