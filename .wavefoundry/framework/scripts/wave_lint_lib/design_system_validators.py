"""Design-system extraction contract validators.

Runs only when docs/design/ exists in the target repo. Validates:
- Required-path presence (core tree from 12akr)
- manifest.json required fields and canonicalRoot
- gaps.md header with summary counts
- spec.json identity fields and reserved behavioral keys
- Token dot-path naming convention
- Broken {token.path} references in semantic.tokens.json
- Orphan primitives in primitives.tokens.json
- Mode parity between light.tokens.json and dark.tokens.json
- components/_index.json <-> folder parity
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .helpers import relative_to_root

# ---------------------------------------------------------------------------
# Required paths (relative to docs/design/)
# ---------------------------------------------------------------------------

_REQUIRED_PATHS = [
    "README.md",
    "DESIGN.md",
    "AGENTS.md",
    "manifest.json",
    "VALIDATION.md",
    "gaps.md",
    "tokens/primitives.tokens.json",
    "tokens/semantic.tokens.json",
    "tokens/modes/light.tokens.json",
    "tokens/modes/dark.tokens.json",
    "tokens/README.md",
    "exports/README.md",
    "exports/css",
    "exports/tailwind",
    "exports/ts",
    "exports/json",
    "components/_index.json",
    "foundations/color.md",
    "foundations/typography.md",
    "foundations/spacing.md",
    "foundations/radius.md",
    "foundations/elevation.md",
    "foundations/motion.md",
    "accessibility/contrast-report.json",
    "accessibility/README.md",
    ".design-system/version.json",
    ".design-system/source-map.json",
    ".design-system/proposed-additions.md",
]

_MANIFEST_REQUIRED_FIELDS = {
    "schemaVersion", "extractionVersion", "extractedAt", "canonicalRoot",
    "sourceStrategy", "evidenceTypes", "artifactCounts", "modes", "validationSummary",
}

_SOURCE_STRATEGY_VALUES = {"figma-extract", "repo-evidence-only", "visual-bootstrap", "hybrid"}

_SPEC_IDENTITY_FIELDS = {
    "id", "name", "category", "status", "description",
    "figma", "codeConnect", "anatomy", "variants", "props",
    "slots", "tokens", "doNotUse", "preferOver",
}

_SPEC_BEHAVIORAL_FIELDS = {"states", "responsive", "motion", "accessibility", "content"}

# Dot-path token name: dot-separated segments. First segment must start with a
# letter; subsequent segments may be all-numeric (scale steps like 500, 4) or
# start with a letter. E.g. color.primary.500, spacing.4, radius.button.
_DOT_PATH_RE = re.compile(r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9]*|\.\d+)*$")

# {token.path} alias references in DTCG files
_TOKEN_REF_RE = re.compile(r"\{([^}]+)\}")

_GAPS_SUMMARY_RE = re.compile(
    r"^\s*-\s+(Critical|Important|Nice-to-have)\s*:", re.IGNORECASE | re.MULTILINE
)


def _load_json(path: Path) -> tuple[dict | list | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, str(exc)


def _flatten_token_keys(obj: object, prefix: str = "") -> set[str]:
    """Recursively collect all leaf token keys (dot-path) from a DTCG token tree."""
    keys: set[str] = set()
    if not isinstance(obj, dict):
        return keys
    for k, v in obj.items():
        full = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict) and "$value" in v:
            keys.add(full)
        elif isinstance(v, dict):
            keys |= _flatten_token_keys(v, full)
    return keys


def _collect_alias_refs(obj: object) -> set[str]:
    """Collect all {token.path} alias references in a DTCG token tree."""
    refs: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "$value" and isinstance(v, str):
                for m in _TOKEN_REF_RE.finditer(v):
                    refs.add(m.group(1))
            else:
                refs |= _collect_alias_refs(v)
    elif isinstance(obj, list):
        for item in obj:
            refs |= _collect_alias_refs(item)
    return refs


# ---------------------------------------------------------------------------
# Public validator
# ---------------------------------------------------------------------------

def check_design_system(root: Path) -> tuple[list[str], list[str]]:
    """Return (failures, warnings) for the design-system extraction contract.

    Only runs when docs/design/ exists; returns empty lists otherwise.
    """
    design_root = root / "docs" / "design"
    if not design_root.exists():
        return [], []

    failures: list[str] = []
    warnings: list[str] = []
    rr = lambda p: relative_to_root(root, p)

    # ------------------------------------------------------------------
    # 1. Required path presence
    # ------------------------------------------------------------------
    for rel in _REQUIRED_PATHS:
        p = design_root / rel
        if not p.exists():
            failures.append(f"docs/design/{rel}: required path missing")

    # ------------------------------------------------------------------
    # 2. manifest.json required fields and canonicalRoot
    # ------------------------------------------------------------------
    manifest_path = design_root / "manifest.json"
    if manifest_path.exists():
        data, err = _load_json(manifest_path)
        if err:
            failures.append(f"docs/design/manifest.json: invalid JSON — {err}")
        elif isinstance(data, dict):
            missing = _MANIFEST_REQUIRED_FIELDS - data.keys()
            for f in sorted(missing):
                failures.append(f"docs/design/manifest.json: required field `{f}` missing")
            canonical = data.get("canonicalRoot")
            if canonical is not None and canonical != "docs/design":
                failures.append(
                    f"docs/design/manifest.json: canonicalRoot must be 'docs/design', got '{canonical}'"
                )
            strategy = data.get("sourceStrategy")
            if strategy is not None and strategy not in _SOURCE_STRATEGY_VALUES:
                failures.append(
                    f"docs/design/manifest.json: sourceStrategy '{strategy}' not in allowed enum "
                    f"{sorted(_SOURCE_STRATEGY_VALUES)}"
                )

    # ------------------------------------------------------------------
    # 3. gaps.md header with summary counts
    # ------------------------------------------------------------------
    gaps_path = design_root / "gaps.md"
    if gaps_path.exists():
        text = gaps_path.read_text(encoding="utf-8", errors="replace")
        if not _GAPS_SUMMARY_RE.search(text):
            failures.append(
                "docs/design/gaps.md: missing severity summary lines "
                "(expected '- Critical:', '- Important:', '- Nice-to-have:' near top)"
            )

    # ------------------------------------------------------------------
    # 4. spec.json identity fields and reserved behavioral keys
    # ------------------------------------------------------------------
    components_dir = design_root / "components"
    if components_dir.exists():
        for spec_path in components_dir.rglob("spec.json"):
            spec, err = _load_json(spec_path)
            if err:
                failures.append(f"{rr(spec_path)}: invalid JSON — {err}")
                continue
            if not isinstance(spec, dict):
                failures.append(f"{rr(spec_path)}: spec.json must be a JSON object")
                continue
            for field in sorted(_SPEC_IDENTITY_FIELDS):
                if field not in spec:
                    failures.append(f"{rr(spec_path)}: identity field `{field}` missing")
            for field in sorted(_SPEC_BEHAVIORAL_FIELDS):
                if field not in spec:
                    failures.append(
                        f"{rr(spec_path)}: reserved behavioral field `{field}` missing "
                        "(must be present as null; Split B will populate)"
                    )

    # ------------------------------------------------------------------
    # 5. Token dot-path naming convention
    # ------------------------------------------------------------------
    for token_file in (design_root / "tokens").rglob("*.tokens.json") if (design_root / "tokens").exists() else []:
        data, err = _load_json(token_file)
        if err or not isinstance(data, dict):
            continue
        for key in _flatten_token_keys(data):
            if not _DOT_PATH_RE.match(key):
                failures.append(
                    f"{rr(token_file)}: token name '{key}' does not follow dot-path convention "
                    "(expected lowercase segments: e.g. color.primary.500)"
                )

    # ------------------------------------------------------------------
    # 6. Broken {token.path} references in semantic.tokens.json
    # ------------------------------------------------------------------
    primitives_path = design_root / "tokens" / "primitives.tokens.json"
    semantic_path = design_root / "tokens" / "semantic.tokens.json"
    if primitives_path.exists() and semantic_path.exists():
        primitives, _ = _load_json(primitives_path)
        semantic, _ = _load_json(semantic_path)
        if isinstance(primitives, dict) and isinstance(semantic, dict):
            primitive_keys = _flatten_token_keys(primitives)
            alias_refs = _collect_alias_refs(semantic)
            for ref in sorted(alias_refs):
                if ref not in primitive_keys:
                    failures.append(
                        f"docs/design/tokens/semantic.tokens.json: broken alias reference "
                        f"'{{{ref}}}' — key not found in primitives.tokens.json"
                    )

    # ------------------------------------------------------------------
    # 7. Orphan primitive check
    # ------------------------------------------------------------------
    if primitives_path.exists() and semantic_path.exists():
        primitives, _ = _load_json(primitives_path)
        semantic, _ = _load_json(semantic_path)
        if isinstance(primitives, dict) and isinstance(semantic, dict):
            primitive_keys = _flatten_token_keys(primitives)
            all_refs = _collect_alias_refs(semantic)
            for key in sorted(primitive_keys):
                if key not in all_refs:
                    raw, _ = _load_json(primitives_path)
                    # Check for primitive-only extension flag
                    parts = key.split(".")
                    node = raw
                    for part in parts:
                        if isinstance(node, dict):
                            node = node.get(part)
                        else:
                            node = None
                            break
                    ext = node.get("$extensions", {}) if isinstance(node, dict) else {}
                    if not ext.get("primitive-only"):
                        warnings.append(
                            f"docs/design/tokens/primitives.tokens.json: orphan primitive '{key}' "
                            "not referenced by any semantic token "
                            "(add \"$extensions\": {{\"primitive-only\": true}} to suppress)"
                        )

    # ------------------------------------------------------------------
    # 8. Mode parity: light and dark must have identical key sets
    # ------------------------------------------------------------------
    light_path = design_root / "tokens" / "modes" / "light.tokens.json"
    dark_path = design_root / "tokens" / "modes" / "dark.tokens.json"
    if light_path.exists() and dark_path.exists():
        light, _ = _load_json(light_path)
        dark, _ = _load_json(dark_path)
        if isinstance(light, dict) and isinstance(dark, dict):
            light_keys = _flatten_token_keys(light)
            dark_keys = _flatten_token_keys(dark)
            for k in sorted(light_keys - dark_keys):
                failures.append(
                    f"docs/design/tokens/modes/dark.tokens.json: key '{k}' present in "
                    "light.tokens.json but missing"
                )
            for k in sorted(dark_keys - light_keys):
                failures.append(
                    f"docs/design/tokens/modes/light.tokens.json: key '{k}' present in "
                    "dark.tokens.json but missing"
                )

    # ------------------------------------------------------------------
    # 9. components/_index.json <-> folder parity
    # ------------------------------------------------------------------
    index_path = design_root / "components" / "_index.json"
    if index_path.exists() and (design_root / "components").exists():
        index_data, err = _load_json(index_path)
        if err:
            failures.append(f"docs/design/components/_index.json: invalid JSON — {err}")
        else:
            # Collect component folder names (skip _index.json itself)
            comp_dir = design_root / "components"
            on_disk = {
                p.name for p in comp_dir.iterdir()
                if p.is_dir() and not p.name.startswith("_")
            }
            # Index entries: support both {"components": [...]} and flat list
            indexed: set[str] = set()
            if isinstance(index_data, dict):
                entries = index_data.get("components", [])
            elif isinstance(index_data, list):
                entries = index_data
            else:
                entries = []
            for entry in entries:
                if isinstance(entry, dict):
                    cid = entry.get("id") or entry.get("name")
                    if cid:
                        indexed.add(str(cid))
                elif isinstance(entry, str):
                    indexed.add(entry)

            for name in sorted(on_disk - indexed):
                failures.append(
                    f"docs/design/components/{name}/: folder exists but has no entry "
                    "in components/_index.json"
                )
            for name in sorted(indexed - on_disk):
                failures.append(
                    f"docs/design/components/_index.json: entry '{name}' has no "
                    "corresponding folder on disk"
                )

    return failures, warnings
