"""Canonical-names manifest loader.

Single source of truth for framework-shipped renames — role slugs and config
keys with their deprecated aliases and removal versions. `docs-lint`, the
renderers, and the upgrade migrator derive alias resolution from
`.wavefoundry/framework/canonical-names.json` rather than maintaining
hardcoded alias dicts in multiple places.

Schema (version 1):

    {
      "schema_version": 1,
      "role_renames": {
        "<legacy_slug>": {"canonical": "<new_slug>", "removed_in": "<semver>|null"}
      },
      "config_key_renames": {
        "<legacy_key>": {"canonical": "<new_key>", "removed_in": "<semver>|null"}
      }
    }

Each rename entry is keyed by the LEGACY name; the value carries the
canonical replacement and a `removed_in` semver string (or `null` when no
removal is scheduled). The legacy name is the lookup target — code asking
"is X a legacy spelling? what is the canonical?" reads `role_renames[X]` or
`config_key_renames[X]`.

Fail-safe behavior: a missing, malformed, or wrong-schema manifest returns
an empty rename map. Callers fall back to "no renames known" and continue
operating — `docs-lint` still runs, just without legacy-spelling warnings.
This protects partial-rollout scenarios where the consumer pack is missing
or out of sync.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

MANIFEST_REL_PATH = ".wavefoundry/framework/canonical-names.json"
SUPPORTED_SCHEMA_VERSION = 1


def manifest_path(repo_root: Path) -> Path:
    """Return the absolute manifest path for ``repo_root``."""
    return repo_root / MANIFEST_REL_PATH


def load_manifest(repo_root: Path) -> dict:
    """Read and parse the manifest. Returns an empty manifest on absent or
    malformed file. Callers should treat missing renames as "no aliases known"
    rather than as an error so `docs-lint` stays operational under partial
    rollouts (pre-1.5.0 consumer installs, manually-deleted manifest)."""
    path = manifest_path(repo_root)
    if not path.exists():
        return _empty_manifest()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty_manifest()
    if not isinstance(data, dict):
        return _empty_manifest()
    if data.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        return _empty_manifest()
    return data


def _empty_manifest() -> dict:
    return {
        "schema_version": SUPPORTED_SCHEMA_VERSION,
        "role_renames": {},
        "config_key_renames": {},
    }


def _alias_map(rename_block: object) -> dict[str, str]:
    """Extract {legacy: canonical} from a rename block. Skip malformed entries
    silently (defensive — keep operational under partial corruption)."""
    if not isinstance(rename_block, dict):
        return {}
    out: dict[str, str] = {}
    for alias, entry in rename_block.items():
        if not isinstance(alias, str):
            continue
        if not isinstance(entry, dict):
            continue
        canonical = entry.get("canonical")
        if not isinstance(canonical, str) or not canonical:
            continue
        out[alias] = canonical
    return out


def role_alias_to_canonical(repo_root: Path) -> dict[str, str]:
    """Return ``{legacy_slug: canonical_slug}`` for framework role renames."""
    manifest = load_manifest(repo_root)
    return _alias_map(manifest.get("role_renames"))


def config_key_alias_to_canonical(repo_root: Path) -> dict[str, str]:
    """Return ``{legacy_key: canonical_key}`` for `workflow-config.json` renames."""
    manifest = load_manifest(repo_root)
    return _alias_map(manifest.get("config_key_renames"))


def canonical_to_aliases(alias_to_canonical: dict[str, str]) -> dict[str, list[str]]:
    """Invert an alias map to ``{canonical: [legacy_alias, ...]}`` (sorted)."""
    out: dict[str, list[str]] = {}
    for alias, canonical in alias_to_canonical.items():
        out.setdefault(canonical, []).append(alias)
    for canonical in out:
        out[canonical].sort()
    return out


def _removed_in(rename_block: object, alias: str) -> Optional[str]:
    if not isinstance(rename_block, dict):
        return None
    entry = rename_block.get(alias)
    if not isinstance(entry, dict):
        return None
    value = entry.get("removed_in")
    if isinstance(value, str) and value:
        return value
    return None


def role_removed_in(repo_root: Path, alias: str) -> Optional[str]:
    """Return the removal version for a role alias, or ``None`` if not scheduled."""
    manifest = load_manifest(repo_root)
    return _removed_in(manifest.get("role_renames"), alias)


def config_key_removed_in(repo_root: Path, alias: str) -> Optional[str]:
    """Return the removal version for a config-key alias, or ``None`` if not scheduled."""
    manifest = load_manifest(repo_root)
    return _removed_in(manifest.get("config_key_renames"), alias)


def framework_repo_root() -> Path:
    """Resolve the wavefoundry repo root from this module's path.

    This module lives at
    ``<repo>/.wavefoundry/framework/scripts/wave_lint_lib/canonical_names.py``,
    so the repo root is four parents up from the file. Used by `constants.py`
    at import time to derive `RETIRED_ROLE_NAMES` and `WORKFLOW_REQUIRED_KEYS`
    from the manifest without each caller needing to pass a path explicitly.
    """
    return Path(__file__).resolve().parents[4]
