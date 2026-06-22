"""Design-system bootstrap and governance validators (Requirement 13).

Runs only when docs/design-system/manifest.json exists. Validates:
- sourceStrategy enum value (incl. external-reference / adopt-in-place)
- targetSurfaces non-empty (with repo-inferred suggestion when missing)
- platformStandards referenceVersion presence
- visual-bootstrap proposal guard (proposed tokens merged into semantic)
- Deprecated component supersededBy/sunset requirement
- platformStandards overrides path existence

Also exposes ``classify_design_system_mode(design_evidence)`` — a pure,
deterministic helper that derives the design-system mode (bootstrap /
extract-mirror / adopt / ambiguous) from the agent-authored
``repo-profile.json`` ``design_system.design_evidence`` block. The seeds record
the evidence and set ``design_system.mode`` from this classifier.
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

_SOURCE_STRATEGY_ENUM = {
    "figma-extract",
    "repo-evidence-only",
    "visual-bootstrap",
    "hybrid",
    "external-reference",
}


# ---------------------------------------------------------------------------
# Design-system mode classification (interrogation C2/C3/C4)
# ---------------------------------------------------------------------------
#
# `repo-profile.json` is agent-authored (seed-030), so there is no code path
# that *generates* the design_system block. This pure function lets the agent
# (and the validator) deterministically derive the mode from the recorded
# `design_system.design_evidence` rather than rely on agent judgment.
#
# The evidence bar that separates the three real modes:
#   - bootstrap       — no design system found (no evidence) -> emit the nulls skeleton.
#   - extract-mirror  — in-repo design *evidence* (CSS custom properties, stylesheet
#                       tokens, in-repo theme files) but NO maintained external system
#                       with its own source-of-truth/build -> extract into docs/design-system/.
#   - adopt           — a DECLARED source of truth WITH its own build: a published/
#                       packaged token package, a Style-Dictionary/DTCG source dir + build,
#                       or Figma library links -> emit the thin external-reference index.
#   - ambiguous       — genuinely weak / mixed signals -> the seeds tell the agent to
#                       ask the operator (never silently adopt OR mirror on weak evidence).

# Token-package marker keys that, when set truthy in design_evidence, indicate a
# DECLARED external source-of-truth (not merely in-repo CSS).
_EXTERNAL_SOURCE_OF_TRUTH_KEYS = (
    "external_token_package",  # a published/packaged token dependency (e.g. @scope/tokens)
    "style_dictionary_build",  # a Style-Dictionary / DTCG source dir + build command
    "figma_library_links",     # Figma library/variable links declared as source of truth
)


def classify_design_system_mode(
    design_evidence: dict | None,
) -> str:
    """Deterministically classify the design-system mode from `design_evidence`.

    Returns one of: ``"bootstrap"``, ``"extract-mirror"``, ``"adopt"``,
    ``"ambiguous"``. Pure function — no filesystem or I/O. Consumed by the
    seeds (which record evidence + set ``design_system.mode``) and re-derivable
    by the validator.

    Evidence bar (interrogation C2/C4):
      - A *declared source of truth with its own build* (a published/packaged
        token package, a Style-Dictionary/DTCG source dir + build, or Figma
        library links) -> ``adopt``. CSS custom properties or a stray Tailwind
        theme do NOT qualify on their own.
      - In-repo design evidence (design tokens / token files / a methodology)
        with NO such external source -> ``extract-mirror`` (this is the
        Wavefoundry self-hosting case: in-repo ``dashboard.css`` -> extract-mirror,
        never adopt).
      - No coherent design system at all -> ``bootstrap``.
      - Genuinely weak / mixed signals -> ``ambiguous`` (seeds: ask the operator).
    """
    if not isinstance(design_evidence, dict):
        return "bootstrap"

    detected = bool(design_evidence.get("detected"))

    # Does the evidence declare an EXTERNAL maintained source of truth with its
    # own build? This is the adopt gate — it must be more than in-repo CSS.
    has_external_source = any(
        bool(design_evidence.get(key)) for key in _EXTERNAL_SOURCE_OF_TRUTH_KEYS
    )

    # In-repo design evidence: tokens / token files / a detected CSS methodology.
    token_files = design_evidence.get("token_files") or []
    has_token_files = isinstance(token_files, list) and len(token_files) > 0
    methodology = design_evidence.get("detected_methodology") or []
    has_methodology = isinstance(methodology, list) and len(methodology) > 0
    has_in_repo_evidence = (
        bool(design_evidence.get("has_design_tokens"))
        or has_token_files
        or has_methodology
        or bool(design_evidence.get("has_component_library"))
        or bool(design_evidence.get("has_typography_system"))
    )

    if has_external_source:
        return "adopt"

    if not detected and not has_in_repo_evidence:
        return "bootstrap"

    if has_in_repo_evidence:
        # In-repo evidence but no declared external source-of-truth -> mirror.
        return "extract-mirror"

    # detected is truthy but no concrete in-repo evidence and no external
    # source-of-truth: signals are genuinely weak / mixed -> ask the operator.
    return "ambiguous"


# ---------------------------------------------------------------------------
# Platform surface detection
# ---------------------------------------------------------------------------

# Filesystem markers → surface label. Checked relative to repo root.
# Ordered from most specific to least; first match wins for each surface.
_PLATFORM_MARKERS: list[tuple[str, str]] = [
    # macOS / iOS / Apple platforms
    ("*.xcodeproj", "macOS"),
    ("*.xcworkspace", "macOS"),
    ("Package.swift", "macOS"),
    ("ios/", "ios"),
    ("macOS/", "macOS"),
    ("watchOS/", "watchOS"),
    ("tvOS/", "tvOS"),
    # Android
    ("android/", "android"),
    ("app/src/main/AndroidManifest.xml", "android"),
    # Flutter
    ("pubspec.yaml", "flutter"),
    ("lib/main.dart", "flutter"),
    # React Native (check after ios/android to avoid double-counting)
    ("metro.config.js", "react-native"),
    ("metro.config.ts", "react-native"),
    # Windows
    ("App.xaml", "windows"),
    ("*.csproj", "windows"),
    # Electron / Tauri (desktop wrappers over web)
    ("electron/main.js", "desktop"),
    ("electron/main.ts", "desktop"),
    ("src-tauri/tauri.conf.json", "desktop"),
    ("tauri.conf.json", "desktop"),
    # Web (checked last — many projects have web as a secondary surface)
    ("package.json", "web"),
    ("index.html", "web"),
]


def _add(lst: list[str], item: str) -> None:
    if item not in lst:
        lst.append(item)


def _infer_target_surfaces(root: Path) -> list[str]:
    """Return a deduplicated list of surface labels inferred from the repo."""
    surfaces: list[str] = []

    # 1. Read repo-profile.json for signals already captured by seed-030.
    profile_path = root / "docs" / "repo-profile.json"
    if profile_path.exists():
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
        except Exception:
            profile = {}
        ds = profile.get("design_system", {})
        evidence = ds.get("design_evidence", {})
        ui_roots = evidence.get("ui_roots", [])
        for path_str in ui_roots:
            segs = path_str.lower().replace("\\", "/").split("/")
            if any(s in ("ios", "iphone", "ipad") for s in segs):
                _add(surfaces, "ios")
            elif any(s in ("macos", "mac", "osx") for s in segs):
                _add(surfaces, "macOS")
            elif "android" in segs:
                _add(surfaces, "android")
            elif "flutter" in segs or "lib" in segs:
                _add(surfaces, "flutter")
            elif any(s in ("web", "src", "app", "frontend") for s in segs):
                _add(surfaces, "web")

    # 2. Filesystem marker scan (glob + direct path checks).
    for marker, surface in _PLATFORM_MARKERS:
        if surface in surfaces:
            continue
        if marker.startswith("*"):
            try:
                next(root.rglob(marker))
                _add(surfaces, surface)
            except StopIteration:
                pass
        elif marker.endswith("/"):
            if (root / marker.rstrip("/")).is_dir():
                _add(surfaces, surface)
        else:
            if (root / marker).exists():
                _add(surfaces, surface)

    return surfaces


# ---------------------------------------------------------------------------
# Public validator
# ---------------------------------------------------------------------------

def check_design_governance(root: Path) -> tuple[list[str], list[str]]:
    """Return (failures, warnings) for design-system governance rules.

    Only runs when docs/design-system/manifest.json exists; returns empty lists
    otherwise.
    """
    manifest_path = root / "docs" / "design-system" / "manifest.json"
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
            f"docs/design-system/manifest.json: sourceStrategy '{source_strategy}' not in allowed enum"
        )

    # ------------------------------------------------------------------
    # 2. targetSurfaces non-empty check
    # ------------------------------------------------------------------
    if "targetSurfaces" in manifest:
        ts = manifest["targetSurfaces"]
        if isinstance(ts, list) and len(ts) == 0:
            inferred = _infer_target_surfaces(root)
            suggestion = (
                f" Detected surfaces from repo: {inferred}." if inferred else ""
            )
            warnings.append(
                "docs/design-system/manifest.json: targetSurfaces is empty — "
                f"surface-specific gap reporting will be skipped.{suggestion}"
            )
    else:
        inferred = _infer_target_surfaces(root)
        if inferred:
            suggestion = f" Detected from repo: {inferred} — set targetSurfaces accordingly."
        else:
            suggestion = " Could not detect surfaces from repo; set targetSurfaces explicitly."
        warnings.append(
            f"docs/design-system/manifest.json: targetSurfaces missing.{suggestion}"
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
                    f"docs/design-system/manifest.json: platformStandards entry for '{surface}' "
                    "missing referenceVersion (required for HIG drift tracking)"
                )

    # ------------------------------------------------------------------
    # 4. visual-bootstrap proposal guard
    # ------------------------------------------------------------------
    if source_strategy == "visual-bootstrap":
        source_map_path = root / "docs" / "design-system" / "source-map.json"
        semantic_path = root / "docs" / "design-system" / "tokens" / "semantic.tokens.json"
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
                            f"docs/design-system/tokens/semantic.tokens.json: token '{entry_id}' is "
                            "marked proposed-from-best-practices but has been merged into "
                            "semantic tokens — promotion requires explicit operator action"
                        )

    # ------------------------------------------------------------------
    # 5. Deprecated component check
    # ------------------------------------------------------------------
    index_path = root / "docs" / "design-system" / "components" / "_index.json"
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
                                f"docs/design-system/components/_index.json: deprecated component "
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
                        f"docs/design-system/manifest.json: platformStandards[{surface}].overrides "
                        f"path '{overrides_path}' does not exist"
                    )

    return failures, warnings
