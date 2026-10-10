"""Immutable cross-version inputs for tests; never fall back to checkout history.

The bundle contains bytes from three Git revisions, not runnable imported modules.
Original paths and bodies are base64 encoded so distribution text rewrites cannot
change the old implementation under test. Consumers write those unchanged bytes
to their own scratch targets and use current siblings, as the original tests did.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

BUNDLE_PATH = Path(__file__).parent / "fixtures" / "historical_sources.json"
BUNDLE_SHA256 = "dd51106bf6121ae1d22cfcdb5b2e5231200a90b334d14a0e65c403449e18671f"
MAX_BUNDLE_BYTES = 1024 * 1024


def historical_bytes(key: str, *, optional: bool = False,
                     bundle_path: Path = BUNDLE_PATH) -> bytes | None:
    """Read a pinned source; only a recorded historical absence may be optional."""
    try:
        with bundle_path.open("rb") as stream:
            raw = stream.read(MAX_BUNDLE_BYTES + 1)
    except OSError as exc:
        raise AssertionError(f"historical fixture missing or unreadable: {bundle_path}") from exc
    if len(raw) > MAX_BUNDLE_BYTES:
        raise AssertionError("historical fixture exceeds its size bound")
    if hashlib.sha256(raw).hexdigest() != BUNDLE_SHA256:
        raise AssertionError("historical fixture bundle integrity mismatch")
    bundle = json.loads(raw)
    if bundle.get("schema") != 1:
        raise AssertionError("historical fixture schema mismatch")
    entry = bundle["entries"].get(key)
    if entry is None:
        raise AssertionError(f"historical fixture entry missing: {key}")
    if entry["absent"]:
        if optional:
            return None
        raise AssertionError(f"required historical fixture was absent at its revision: {key}")
    try:
        source = base64.b64decode("".join(entry["content_b64"]), validate=True)
    except (ValueError, TypeError) as exc:
        raise AssertionError(f"historical fixture encoding invalid: {key}") from exc
    if len(source) != entry["size"] or hashlib.sha256(source).hexdigest() != entry["sha256"]:
        raise AssertionError(f"historical fixture source integrity mismatch: {key}")
    return source
