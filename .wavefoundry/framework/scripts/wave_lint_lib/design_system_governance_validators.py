"""Design-system bootstrap and governance validators (Requirement 13).

Runs only when docs/design/manifest.json exists. Validates:
- sourceStrategy enum value
- targetSurfaces non-empty
- platformStandards referenceVersion presence
- visual-bootstrap proposal guard (proposed tokens merged into semantic)
- Deprecated component supersededBy/sunset requirement
- platformStandards overrides path existence
"""
from __future__ import annotations

import json
from pathlib import Path


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> tuple[dict | list | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, str(exc)


# ---------------------------------------------------------------------------
# Allowed enum values
# ---------------------------------------------------------------------------

_SOURCE_STRATEGY_ENUM = {"figma-extract", "repo-evidence-only", "visual-bootstrap", "hybrid"}


# ---------------------------------------------------------------------------
# Public validator
# ---------------------------------------------------------------------------

def check_design_governance(root: Path) -> tuple[list[str], list[str]]:
    """Return (failures, warnings) for design-system governance rules.

    Only runs when docs/design/manifest.json exists; returns empty lists
    otherwise.
    """
    manifest_path = root / "docs" / "design" / "manifest.json"
    if not manifest_path.exists():
        return [], []

    failures: list[str] = []
    warnings: list[str] = []

    manifest, err = _load_json(manifest_path)
    if err or not isinstance(manifest, dict):
        # Core validator already reports invalid JSON; skip governance checks.
        return failures, warnings

    # ------------------------------------------------------------------
    # 1. sourceStrategy enum check
    # ------------------------------------------------------------------
    source_strategy = manifest.get("sourceStrategy")
    if source_strategy is not None and source_strategy not in _SOURCE_STRATEGY_ENUM:
        failures.append(
            f"docs/design/manifest.json: sourceStrategy '{source_strategy}' not in allowed enum"
        )

    # ------------------------------------------------------------------
    # 2. targetSurfaces non-empty check
    # ------------------------------------------------------------------
    if "targetSurfaces" in manifest:
        ts = manifest["targetSurfaces"]
        if isinstance(ts, list) and len(ts) == 0:
            warnings.append(
                "docs/design/manifest.json: targetSurfaces is empty — "
                "surface-specific gap reporting will be skipped"
            )
    else:
        warnings.append(
            "docs/design/manifest.json: targetSurfaces missing — "
            "defaulting to web-only; set explicitly to avoid silent cross-surface gaps"
        )

    # ------------------------------------------------------------------
    # 3. platformStandards referenceVersion check
    # ------------------------------------------------------------------
    platform_standards = manifest.get("platformStandards")
    if isinstance(platform_standards, list):
        for entry in platform_standards:
            if not isinstance(entry, dict):
                continue
            surface = entry.get("surface") or entry.get("id") or "<unknown>"
            ref_ver = entry.get("referenceVersion")
            if "referenceVersion" not in entry or ref_ver is None:
                warnings.append(
                    f"docs/design/manifest.json: platformStandards entry for '{surface}' "
                    "missing referenceVersion (required for HIG drift tracking)"
                )

    # ------------------------------------------------------------------
    # 4. visual-bootstrap proposal guard
    # ------------------------------------------------------------------
    if source_strategy == "visual-bootstrap":
        source_map_path = root / "docs" / "design" / ".design-system" / "source-map.json"
        semantic_path = root / "docs" / "design" / "tokens" / "semantic.tokens.json"
        if source_map_path.exists() and semantic_path.exists():
            source_map, sm_err = _load_json(source_map_path)
            semantic, sem_err = _load_json(semantic_path)
            if (
                not sm_err
                and not sem_err
                and isinstance(source_map, list)
                and isinstance(semantic, dict)
                and semantic  # skip if empty {}
            ):
                semantic_keys = set(semantic.keys())
                for entry in source_map:
                    if not isinstance(entry, dict):
                        continue
                    entry_id = entry.get("id")
                    if entry_id is None:
                        continue
                    # Check if entry is marked as proposed
                    is_proposed = False
                    if entry.get("confidence") == "proposed":
                        is_proposed = True
                    extensions = entry.get("$extensions", {})
                    if isinstance(extensions, dict) and extensions.get("proposed-from-best-practices") is True:
                        is_proposed = True
                    if is_proposed and str(entry_id) in semantic_keys:
                        failures.append(
                            f"docs/design/tokens/semantic.tokens.json: token '{entry_id}' is "
                            "marked proposed-from-best-practices but has been merged into "
                            "semantic tokens — promotion requires explicit operator action"
                        )

    # ------------------------------------------------------------------
    # 5. Deprecated component check
    # ------------------------------------------------------------------
    index_path = root / "docs" / "design" / "components" / "_index.json"
    if index_path.exists():
        index_data, idx_err = _load_json(index_path)
        if not idx_err and isinstance(index_data, dict):
            entries = index_data.get("components", [])
            if isinstance(entries, list):
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    if entry.get("deprecated") is True:
                        comp_id = entry.get("id") or entry.get("name") or "<unknown>"
                        superseded = entry.get("supersededBy")
                        sunset = entry.get("sunset")
                        if not superseded and not sunset:
                            failures.append(
                                f"docs/design/components/_index.json: deprecated component "
                                f"'{comp_id}' must have supersededBy or sunset"
                            )

    # ------------------------------------------------------------------
    # 6. per-surface deltas files exist
    # ------------------------------------------------------------------
    if isinstance(platform_standards, list):
        for entry in platform_standards:
            if not isinstance(entry, dict):
                continue
            overrides_path = entry.get("overrides")
            if overrides_path and isinstance(overrides_path, str):
                surface = entry.get("surface") or entry.get("id") or "<unknown>"
                full_path = root / overrides_path
                if not full_path.exists():
                    failures.append(
                        f"docs/design/manifest.json: platformStandards[{surface}].overrides "
                        f"path '{overrides_path}' does not exist"
                    )

    return failures, warnings
