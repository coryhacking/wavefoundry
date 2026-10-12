"""Immutable cross-version inputs for tests; never fall back to checkout history.

The bundle contains bytes from two Git revisions, not runnable imported modules.
Original paths and bodies are base64 encoded so distribution text rewrites cannot
change the old implementation under test. Consumers write those unchanged bytes
to their own scratch targets and use current siblings, as the original tests did.

The renameable v1.22.0 upgrade runner instead lives as verbatim plaintext in
fixtures/upgrade_old_runner/upgrade_runner_v1_22_0.py.txt. Origin: revision
feaef9ac0e5bffe3bed46498340eaf5e7d191583, source
.wavefoundry/framework/scripts/upgrade_wavefoundry.py; original 269025 bytes,
SHA256 ae18d63246bc55f398bb6ae10303044f7701b68dbbf7ecff8e8e54230df0fb24.
That digest records provenance, never rejects an intentional distribution text
rename. Its old upgrade control flow is exercised by the real resume tests.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

BUNDLE_PATH = Path(__file__).parent / "fixtures" / "historical_sources.json"
BUNDLE_SHA256 = "54c36b3b6110917954bb720490be9824758f04ea51fabde2ded7d39839350537"
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
