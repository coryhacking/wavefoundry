"""Design-system surface-depth validators (Split B, Requirement 13).

Runs only when docs/design/ exists in the target repo. Validates:
1. WCAG contrast check (contrast-report.json)
2. Extended mode parity (borders/focus/z-index/motion token files vs light/dark modes)
3. Reduced-motion check (motion tokens require media-motion.md)
4. Icon sanity (viewBox squareness, hardcoded color values)
5. Keyboard pattern check (component keyboard interactions require keyboard.md)
6. State coverage (component states references resolve to state-patterns directories)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .helpers import relative_to_root

# ---------------------------------------------------------------------------
# Local helpers (avoid circular import from design_system_validators)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Extended token files subject to mode-parity check
# ---------------------------------------------------------------------------

_EXTENDED_TOKEN_FILES = [
    "tokens/borders.tokens.json",
    "tokens/focus.tokens.json",
    "tokens/z-index.tokens.json",
    "tokens/motion.tokens.json",
]

# Matches a literal hex color value (3, 4, 6, or 8 hex digits)
_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


# ---------------------------------------------------------------------------
# Validator 1: WCAG contrast check
# ---------------------------------------------------------------------------

def _check_wcag_contrast(design_root: Path, root: Path) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []
    report_path = design_root / "accessibility" / "contrast-report.json"
    if not report_path.exists():
        return failures, warnings

    data, err = _load_json(report_path)
    if err:
        # Not valid JSON — skip silently (not our responsibility here)
        return failures, warnings
    if not isinstance(data, dict):
        return failures, warnings

    checks = data.get("checks")
    if not isinstance(checks, list) or len(checks) == 0:
        # Empty stub — skip silently
        return failures, warnings

    rel = "docs/design/accessibility/contrast-report.json"
    for entry in checks:
        if not isinstance(entry, dict):
            continue
        if entry.get("passed") is False:
            level = entry.get("level")
            entry_id = entry.get("id", "<unknown>")
            if level in ("AA", "AAA"):
                failures.append(f"{rel}: WCAG {level} failure for '{entry_id}'")
            else:
                warnings.append(f"{rel}: contrast failure for '{entry_id}' (level: {level!r})")

    return failures, warnings


# ---------------------------------------------------------------------------
# Validator 2: Extended mode parity
# ---------------------------------------------------------------------------

def _check_extended_mode_parity(design_root: Path, root: Path) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    light_path = design_root / "tokens" / "modes" / "light.tokens.json"
    dark_path = design_root / "tokens" / "modes" / "dark.tokens.json"

    light_keys: set[str] | None = None
    dark_keys: set[str] | None = None

    if light_path.exists():
        light_data, _ = _load_json(light_path)
        if isinstance(light_data, dict):
            light_keys = _flatten_token_keys(light_data)

    if dark_path.exists():
        dark_data, _ = _load_json(dark_path)
        if isinstance(dark_data, dict):
            dark_keys = _flatten_token_keys(dark_data)

    for rel_file in _EXTENDED_TOKEN_FILES:
        ext_path = design_root / rel_file
        if not ext_path.exists():
            continue

        ext_data, _ = _load_json(ext_path)
        if not isinstance(ext_data, dict) or ext_data == {}:
            # Empty stub — skip silently
            continue

        ext_keys = _flatten_token_keys(ext_data)
        if not ext_keys:
            continue

        file_label = f"docs/design/{rel_file}"

        for key in sorted(ext_keys):
            if light_keys is not None and key not in light_keys:
                failures.append(
                    f"{file_label}: key '{key}' present but missing in light.tokens.json"
                )
            if dark_keys is not None and key not in dark_keys:
                failures.append(
                    f"{file_label}: key '{key}' present but missing in dark.tokens.json"
                )

    return failures, warnings


# ---------------------------------------------------------------------------
# Validator 3: Reduced-motion check
# ---------------------------------------------------------------------------

def _has_non_null_values(obj: object) -> bool:
    """Return True if the token tree has any leaf with a non-null $value."""
    if not isinstance(obj, dict):
        return False
    for k, v in obj.items():
        if k == "$value":
            if v is not None:
                return True
        elif isinstance(v, dict):
            if _has_non_null_values(v):
                return True
    return False


def _check_reduced_motion(design_root: Path, root: Path) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    motion_path = design_root / "tokens" / "motion.tokens.json"
    if not motion_path.exists():
        return failures, warnings

    data, _ = _load_json(motion_path)
    if not isinstance(data, dict):
        return failures, warnings

    if not _has_non_null_values(data):
        return failures, warnings

    media_motion_path = design_root / "foundations" / "media-motion.md"
    if not media_motion_path.exists():
        failures.append(
            "docs/design/tokens/motion.tokens.json: non-null motion tokens present but "
            "docs/design/foundations/media-motion.md missing "
            "(reduced-motion fallback guidance required)"
        )

    return failures, warnings


# ---------------------------------------------------------------------------
# Validator 4: Icon sanity
# ---------------------------------------------------------------------------

def _parse_viewbox(viewbox: str) -> list[float] | None:
    """Parse a viewBox string into a list of floats. Returns None on error."""
    try:
        parts = viewbox.strip().split()
        if len(parts) == 4:
            return [float(p) for p in parts]
        if len(parts) == 2:
            return [float(p) for p in parts]
        return None
    except (ValueError, AttributeError):
        return None


def _check_icon_sanity(design_root: Path, root: Path) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    index_path = design_root / "icons" / "_index.json"
    if not index_path.exists():
        return failures, warnings

    data, _ = _load_json(index_path)
    if not isinstance(data, dict) or not data:
        return failures, warnings

    icons = data.get("icons")
    if not isinstance(icons, list) or len(icons) == 0:
        return failures, warnings

    rel = "docs/design/icons/_index.json"

    for entry in icons:
        if not isinstance(entry, dict):
            continue
        icon_id = entry.get("id", "<unknown>")
        multicolor = entry.get("multicolor", False)

        # ViewBox squareness check
        viewbox = entry.get("viewBox")
        if viewbox is not None:
            parsed = _parse_viewbox(str(viewbox))
            if parsed is not None:
                if len(parsed) == 4:
                    # "x y width height" — width == height
                    w, h = parsed[2], parsed[3]
                    if w != h:
                        warnings.append(
                            f"{rel}: icon '{icon_id}' has non-square viewBox '{viewbox}'"
                        )
                elif len(parsed) == 2:
                    # "width height" two-value form
                    w, h = parsed[0], parsed[1]
                    if w != h:
                        warnings.append(
                            f"{rel}: icon '{icon_id}' has non-square viewBox '{viewbox}'"
                        )

        # Hardcoded color check (skip multicolor icons)
        if not multicolor:
            for attr in ("fill", "stroke"):
                val = entry.get(attr)
                if val is not None and isinstance(val, str) and _HEX_COLOR_RE.match(val):
                    warnings.append(
                        f"{rel}: icon '{icon_id}' uses hardcoded color '{val}' "
                        "(should use currentColor)"
                    )

    return failures, warnings


# ---------------------------------------------------------------------------
# Validator 5: Keyboard pattern check
# ---------------------------------------------------------------------------

def _check_keyboard_pattern(design_root: Path, root: Path) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    components_dir = design_root / "components"
    if not components_dir.exists():
        return failures, warnings

    triggering_component: str | None = None
    for spec_path in components_dir.rglob("spec.json"):
        spec, _ = _load_json(spec_path)
        if not isinstance(spec, dict):
            continue
        accessibility = spec.get("accessibility")
        if accessibility is None:
            continue
        if not isinstance(accessibility, dict):
            continue
        keyboard = accessibility.get("keyboard")
        if keyboard is not None and keyboard != "" and keyboard != [] and keyboard != {}:
            # Non-empty keyboard interactions declared
            triggering_component = spec.get("id") or spec_path.parent.name
            break

    if triggering_component is None:
        return failures, warnings

    keyboard_md = design_root / "accessibility" / "keyboard.md"
    if not keyboard_md.exists():
        failures.append(
            f"docs/design/accessibility/keyboard.md: required because component "
            f"'{triggering_component}' declares keyboard interactions"
        )

    return failures, warnings


# ---------------------------------------------------------------------------
# Validator 6: State coverage
# ---------------------------------------------------------------------------

def _check_state_coverage(design_root: Path, root: Path) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    components_dir = design_root / "components"
    if not components_dir.exists():
        return failures, warnings

    state_patterns_dir = design_root / "state-patterns"

    for spec_path in components_dir.rglob("spec.json"):
        spec, _ = _load_json(spec_path)
        if not isinstance(spec, dict):
            continue
        states = spec.get("states")
        if not isinstance(states, list) or len(states) == 0:
            continue

        # Get component id for the message
        comp_id = spec.get("id") or spec_path.parent.name
        rel_spec = f"docs/design/components/{comp_id}/spec.json"

        for ref in states:
            if not isinstance(ref, str):
                continue
            state_dir = state_patterns_dir / ref
            if not state_dir.is_dir():
                warnings.append(
                    f"{rel_spec}: states reference '{ref}' not found in state-patterns/"
                )

    return failures, warnings


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def check_design_surface(root: Path) -> tuple[list[str], list[str]]:
    """Return (failures, warnings) for design-system surface-depth validators.

    Only runs when docs/design/ exists; returns empty lists otherwise.
    """
    design_root = root / "docs" / "design"
    if not design_root.exists():
        return [], []

    failures: list[str] = []
    warnings: list[str] = []

    for checker in (
        _check_wcag_contrast,
        _check_extended_mode_parity,
        _check_reduced_motion,
        _check_icon_sanity,
        _check_keyboard_pattern,
        _check_state_coverage,
    ):
        f, w = checker(design_root, root)
        failures.extend(f)
        warnings.extend(w)

    return failures, warnings
